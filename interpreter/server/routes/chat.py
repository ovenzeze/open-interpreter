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
    """Chat endpoint that handles both streaming and non-streaming responses"""
    # 初始化lock_acquired变量，确保在所有执行路径中都有定义
    lock_acquired = False
    session_id = None
    
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        stream = data.get('stream', False)
        session_id = data.get('session_id')
        
        # 获取请求数据
        current_app.logger.debug(f"Received request data: {data}")
        
        if data is None:
            current_app.logger.error("Invalid request: empty data")
            raise ValidationError("Invalid request data")
            
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
        
        # 如果提供了模型，更新interpreter配置
        if 'model' in data:
            interpreter_instance.llm.model = data['model']
            current_app.logger.debug(f"Updated model to {data['model']} for session {session_id}")
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
        response = interpreter_instance.chat(
            last_message_content,
            stream=False,  # 这里改为 False 以便收集所有消息
            display=False
        )
        
        response_messages = []
        # 用于收集代码和执行结果
        code_messages = []
        
        # 遍历生成的所有消息
        for msg in interpreter_instance.messages:
            if msg["role"] in ["assistant", "computer"]:
                if msg["type"] == "message":
                    response_messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })
                elif msg["type"] == "code":
                    code_messages.append({
                        "role": "assistant",
                        "type": "code",
                        "content": msg["content"],
                        "format": msg.get("format", "python")
                    })
                elif msg["type"] == "console" and msg["role"] == "computer":
                    code_messages.append({
                        "role": "computer",
                        "type": "console",
                        "content": msg["content"]
                    })
        
        # 构造最终响应
        chat_response = {
            "id": f"chatcmpl-{session_id}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": getattr(interpreter_instance, "model", "gpt-4"),
            "choices": [{
                "index": 0,
                "messages": code_messages + response_messages,  # 先显示代码和执行结果，再显示总结
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
        current_app.logger.debug(f"Returning chat response with {len(code_messages)} code messages and {len(response_messages)} text messages")
        return jsonify(chat_response)
        
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
