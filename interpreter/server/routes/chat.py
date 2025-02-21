"""
聊天相关的路由处理模块
包含原生聊天接口和OpenAI兼容接口
"""

import json
import uuid
import time
from flask import Blueprint, jsonify, request, Response, stream_with_context, current_app
from ..message import Message, StreamingChunk
from ..errors import ValidationError, format_error_response
from ..log_config import log_error
from ..utils import (
    convert_interpreter_to_openai,
    convert_openai_to_interpreter,
    format_openai_stream_chunk,
    format_stream_chunk,
)
from ..message_processor import MessageProcessor

bp = Blueprint('chat', __name__)

@bp.route('/v1/chat', methods=['POST'])
def chat():
    """
    处理聊天请求，支持流式和非流式响应
    
    Request Body:
        {
            "messages": [消息数组],
            "stream": bool,
            "session_id": str (可选)
        }
    
    Returns:
        流式响应或JSON响应
    """
    if not request.is_json:
        current_app.logger.error("Invalid content type: not application/json")
        raise ValidationError("Content-Type must be application/json")
        
    lock_acquired = False
    session_id = None
    try:
        # 获取请求数据
        data = request.get_json()
        current_app.logger.debug(f"Received request data: {data}")
        
        if data is None:
            current_app.logger.error("Invalid request: empty data")
            raise ValidationError("Invalid request data")
            
        messages = data.get('messages', [])
        if not messages:
            current_app.logger.error("Invalid request: empty messages array")
            raise ValidationError("Messages array is required")
            
        # 转换消息为Message对象
        validated_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                msg = msg.copy()  # 创建副本以不修改原始数据
                msg.pop('start', None)
                msg.pop('end', None)
            validated_messages.append(Message.from_dict(msg) if isinstance(msg, dict) else msg)
        messages = validated_messages
            
        stream = data.get('stream', False)
        session_id = data.get('session_id')
        
        # 获取会话管理器
        session_manager = current_app.session_manager
        
        # 如果没有提供session_id，创建新会话
        if not session_id:
            current_app.logger.info("No session_id provided, creating new session")
            session = session_manager.create_session()
            session_id = session['session_id']
            current_app.logger.debug(f"Created new session: {session_id}")
        
        # 尝试获取会话锁
        if not session_manager.acquire_session_lock(session_id, timeout=5.0):
            current_app.logger.warning(f"Chat request blocked by another ongoing request in session {session_id}")
            return jsonify({
                "error": {
                    "message": "会话正忙，请稍后再试",
                    "code": "session_busy",
                    "details": {
                        "retry_after": 5,
                        "status": "locked",
                        "session_id": session_id
                    }
                }
            }), 423
        
        # 标记锁已被获取
        lock_acquired = True
        current_app.logger.info(f"Session lock acquired for session {session_id}")
        
        current_app.logger.info(f"Processing chat request with {len(messages)} messages for session {session_id}")
        
        # 加载会话消息
        session_messages = session_manager.get_messages(session_id)
        if session_messages:
            current_app.logger.debug(f"Loaded {len(session_messages)} messages from session")
            # 确保所有消息都是字典格式
            session_messages = [msg.to_dict() if isinstance(msg, Message) else msg for msg in session_messages]
            messages = [msg.to_dict() if isinstance(msg, Message) else msg for msg in messages]
            messages = session_messages + messages
        else:
            # 如果没有历史消息，确保当前消息是字典格式
            messages = [msg.to_dict() if isinstance(msg, Message) else msg for msg in messages]
        
        # 获取interpreter实例
        interpreter_instance = session_manager.get_interpreter(session_id)
        if not interpreter_instance:
            current_app.logger.error(f"No interpreter instance found for session {session_id}")
            return jsonify({
                "error": {
                    "message": "会话已过期或不存在",
                    "code": "session_expired",
                    "details": {
                        "session_id": session_id
                    }
                }
            }), 404
        
        # 准备消息
        last_message = messages[-1]
        if isinstance(last_message, dict):
            last_message_content = last_message.get('content', '')
        elif isinstance(last_message, Message):
            last_message_content = last_message.content
        else:
            last_message_content = str(last_message)
            
        # 设置历史消息
        if len(messages) > 1:  # 如果有历史消息
            interpreter_instance.messages = []  # 先清空
            for msg in messages[:-1]:
                if isinstance(msg, str):
                    msg_dict = {
                        'role': 'user',
                        'type': 'message',
                        'content': msg
                    }
                elif isinstance(msg, dict):
                    msg_dict = msg
                elif isinstance(msg, Message):
                    msg_dict = msg.to_dict()
                else:
                    msg_dict = {
                        'role': 'user',
                        'type': 'message',
                        'content': str(msg)
                    }
                interpreter_instance.messages.append(msg_dict)
        
        current_app.logger.debug("Starting chat with interpreter")
        response = interpreter_instance.chat(last_message_content, stream=stream)
        current_app.logger.debug("Got response from interpreter")
        
        if not stream:
            content = ''
            for chunk in response:
                try:
                    chunk = Message.from_dict(chunk)
                    if chunk.type == 'message' and chunk.role == 'assistant':
                        if content:
                            content += '\n'
                        content += chunk.content
                        # 保存消息到会话
                        session_manager.add_message(session_id, chunk.to_dict())
                except Exception as e:
                    current_app.logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
                    continue
            
            return jsonify({
                "id": f"chatcmpl-{str(uuid.uuid4())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": interpreter_instance.llm.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,  # 暂时不计算 token
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            })
        
        def generate():
            """生成流式响应"""
            try:
                current_app.logger.debug("Starting stream generation")
                current_message = None
                
                for chunk in response:
                    try:
                        chunk = StreamingChunk.from_dict(chunk)
                        current_app.logger.debug(f"Processing chunk: {chunk}")
                        
                        # 处理确认消息
                        if chunk.type == 'confirmation':
                            current_app.logger.debug("Confirmation message detected")
                            yield f"data: {format_stream_chunk(chunk)}\n\n"
                            continue
                        
                        # 处理消息开始
                        if chunk.start:
                            current_app.logger.debug("Message start detected")
                            current_message = Message(
                                role=chunk.role,
                                type=chunk.type,
                                content='',
                                format=chunk.format,
                                recipient=chunk.recipient
                            )
                            
                        # 处理消息内容
                        if chunk.content is not None and current_message:
                            current_app.logger.debug(f"Adding content to message: {chunk.content}")
                            # 确保内容为字符串类型
                            content_str = str(chunk.content) if chunk.content is not None else ""
                            current_message.content += content_str
                        
                        # 处理消息结束
                        if chunk.end:
                            current_app.logger.debug("Message end detected")
                            if current_message:
                                # 保存所有类型的完整消息到会话
                                if current_message.role in ['user', 'assistant']:
                                    session_manager.add_message(session_id, current_message.to_dict())
                                current_message = None
                        
                        # 格式化并发送块
                        formatted_chunk = format_stream_chunk(chunk)
                        if formatted_chunk:
                            current_app.logger.debug(f"Sending formatted chunk: {formatted_chunk}")
                            yield f"data: {formatted_chunk}\n\n"
                            current_app.logger.debug("Chunk sent successfully")
                        
                    except Exception as chunk_error:
                        current_app.logger.error(f"Error processing chunk: {str(chunk_error)}", exc_info=True)
                        error_chunk = StreamingChunk(
                            role='assistant',
                            type='error',
                            content=str(chunk_error),
                            recipient='user'
                        )
                        yield f"data: {format_stream_chunk(error_chunk)}\n\n"
                        continue
                
                # 发送结束标记
                final_chunk = StreamingChunk(
                    role='assistant',
                    type='message',
                    content='',
                    end=True,
                    recipient='user'
                )
                yield f"data: {format_stream_chunk(final_chunk)}\n\n"
                yield f"event: done\n\n"
                current_app.logger.debug("Final chunk sent")
                
            except Exception as e:
                current_app.logger.error(f"Stream generation error: {str(e)}", exc_info=True)
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content=str(e),
                    recipient='user'
                )
                yield f"data: {format_stream_chunk(error_chunk)}\n\n"
            finally:
                # 释放锁
                if lock_acquired and session_id:
                    current_app.logger.info(f"Releasing session lock for session {session_id}")
                    session_manager.release_session_lock(session_id)
        
        current_app.logger.info("Starting streaming response")
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
            
    except Exception as e:
        # 确保在发生异常时也释放锁
        if lock_acquired and session_id:
            current_app.logger.info(f"Releasing session lock for session {session_id} due to exception")
            session_manager.release_session_lock(session_id)
        current_app.logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code
    finally:
        # 确保在流式响应结束时释放锁
        if not stream and lock_acquired and session_id:
            current_app.logger.info(f"Releasing session lock for session {session_id}")
            session_manager.release_session_lock(session_id)

@bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """
    OpenAI兼容的聊天完成接口
    
    Request Body:
        {
            "messages": [OpenAI格式的消息数组],
            "stream": bool,
            "model": str (可选),
            "session_id": str (可选)
        }
    
    Returns:
        OpenAI格式的响应
    """
    if not request.is_json:
        raise ValidationError("Content-Type must be application/json")
        
    try:
        data = request.get_json()
        if data is None:
            raise ValidationError("Invalid request data")
            
        messages = data.get('messages', [])
        messages = MessageProcessor.validate_messages(messages)
            
        stream = data.get('stream', False)
        session_id = data.get('session_id')
        
        # 获取会话管理器
        session_manager = current_app.session_manager
        
        # 如果没有提供session_id，创建新会话
        if not session_id:
            session = session_manager.create_session()
            session_id = session['session_id']
        
        # 获取interpreter实例
        interpreter_instance = session_manager.get_interpreter(session_id)
        if not interpreter_instance:
            current_app.logger.error(f"No interpreter instance found for session {session_id}")
            return jsonify({
                "error": {
                    "message": "会话已过期或不存在",
                    "code": "session_expired",
                    "details": {
                        "session_id": session_id
                    }
                }
            }), 404
        
        # 如果提供了模型，更新interpreter配置
        if 'model' in data:
            interpreter_instance.llm.model = data['model']
        
        current_app.logger.info(f"Processing chat completions request with {len(messages)} messages for session {session_id}")
        
        # 加载会话消息
        session_messages = session_manager.get_messages(session_id)
        if session_messages:
            if isinstance(session_messages, dict):
                session_messages = [session_messages]
            elif not isinstance(session_messages, list):
                session_messages = []
            messages = session_messages + (messages if isinstance(messages, list) else [messages])
        
        # 转换消息格式并发送请求
        interpreter_messages = convert_openai_to_interpreter(messages)
        interpreter_instance.messages = [msg.to_dict() for msg in interpreter_messages[:-1]]  # 加载历史消息
        response = interpreter_instance.chat(interpreter_messages[-1].content, stream=stream)
        
        if not stream:
            result = MessageProcessor.process_response(response, session_manager, session_id)
            return jsonify(result)
        
        def generate_stream():
            """生成OpenAI格式的流式响应"""
            try:
                for chunk in response:
                    chunk = StreamingChunk.from_dict(chunk)
                    if chunk.type == 'message':
                        session_manager.add_message(session_id, Message(
                            role=chunk.role,
                            type=chunk.type,
                            content=chunk.content,
                            format=chunk.format
                        ).to_dict())
                    yield format_openai_stream_chunk(chunk)
            except Exception as e:
                current_app.logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content=str(e),
                    recipient='user'
                )
                yield format_openai_stream_chunk(error_chunk)
        
        return Response(
            stream_with_context(generate_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
            
    except Exception as e:
        current_app.logger.error(f"Error processing chat completions request: {str(e)}", exc_info=True)
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code 