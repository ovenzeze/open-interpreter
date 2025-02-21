"""
Utility functions for Open Interpreter HTTP Server
"""

import json
import uuid
import time
import logging
from typing import Any, Dict, List, Union
from datetime import datetime
from .message import Message, StreamingChunk

logger = logging.getLogger(__name__)

def convert_openai_to_interpreter(messages: List[Dict[str, str]]) -> List[Message]:
    """
    Convert OpenAI format messages to Open Interpreter format
    
    Args:
        messages: List of messages in OpenAI format
        
    Returns:
        List of messages in Open Interpreter format
    """
    interpreter_messages = []
    
    for msg in messages:
        role = msg.get('role')
        content = msg.get('content', '')
        msg_type = msg.get('type', 'message')  # 获取消息类型，默认为message
        recipient = msg.get('recipient', 'assistant' if role == 'user' else 'user')
        
        if role in ['user', 'assistant']:
            # 检查是否包含代码块
            if role == 'assistant' and '```' in content:
                # 提取代码块
                code_blocks = content.split('```')
                for i, block in enumerate(code_blocks):
                    if i % 2 == 0:  # 非代码块部分
                        if block.strip():
                            interpreter_messages.append(Message(
                                role='assistant',
                                type='message',  # 明确指定类型
                                content=block.strip(),
                                recipient=recipient
                            ))
                    else:  # 代码块部分
                        # 支持多种语言检测
                        lang, code = 'python', block
                        if '\n' in block:
                            first_line = block.split('\n', 1)[0].strip()
                            if first_line in ['python', 'javascript', 'shell', 'html']:
                                lang = first_line
                                code = block.split('\n', 1)[1] if '\n' in block else ''
                        
                        interpreter_messages.append(Message(
                            role='assistant',
                            type='code',  # 明确指定类型
                            format=lang,
                            content=code.strip(),
                            recipient=recipient
                        ))
            else:
                # 对于普通消息，使用默认类型
                interpreter_messages.append(Message(
                    role=role,
                    type=msg_type,  # 使用消息中指定的类型或默认值
                    content=content,
                    recipient=recipient
                ))
        elif role == 'system':
            # 系统消息转换为assistant消息
            interpreter_messages.append(Message(
                role='assistant',
                type='message',  # 明确指定类型
                content=content,
                recipient='user'  # 系统消息总是发给用户
            ))
            
    return interpreter_messages

def convert_interpreter_to_openai(messages: List[Message]) -> List[Dict[str, str]]:
    """
    Convert Open Interpreter format messages to OpenAI format
    
    Args:
        messages: List of messages in Open Interpreter format
        
    Returns:
        List of messages in OpenAI format
    """
    openai_messages = []
    current_message = None
    
    for msg in messages:
        if not isinstance(msg, Message):
            msg = Message.from_dict(msg)
            
        if msg.role in ['user', 'assistant']:
            # 如果有未完成的消息，先添加到结果列表
            if current_message and (
                current_message['role'] != msg.role or
                msg.type != 'message'  # 使用属性而不是get方法
            ):
                openai_messages.append(current_message)
                current_message = None
            
            # 处理不同类型的消息
            if msg.type == 'message':
                if not current_message:
                    current_message = {
                        'role': msg.role,
                        'content': msg.content
                    }
                else:
                    current_message['content'] += msg.content
                    
            elif msg.type == 'code':
                if not current_message:
                    current_message = {
                        'role': msg.role,
                        'content': ''
                    }
                # 添加代码块
                if msg.content:
                    if current_message['content']:
                        current_message['content'] += '\n'
                    current_message['content'] += f"```{msg.format or 'python'}\n{msg.content}\n```"
    
    # 添加最后一个未完成的消息
    if current_message:
        openai_messages.append(current_message)
        
    return openai_messages

def format_stream_chunk(chunk: Union[StreamingChunk, Dict]) -> str:
    """
    Format a message chunk for SSE streaming
    
    Args:
        chunk: Message chunk to format
        
    Returns:
        Formatted SSE data string
    """
    if isinstance(chunk, dict):
        # 确保包含所有必要字段
        if 'type' not in chunk:
            chunk['type'] = 'message'
        if 'format' not in chunk and chunk['type'] in ['code', 'image', 'console']:
            chunk['format'] = 'python' if chunk['type'] == 'code' else 'output'
        if 'recipient' not in chunk:
            chunk['recipient'] = 'user' if chunk.get('role') == 'assistant' else 'assistant'
            
        chunk = StreamingChunk.from_dict(chunk)
    
    if not isinstance(chunk, StreamingChunk):
        return None
        
    try:
        return json.dumps(chunk.to_dict())
    except Exception as e:
        logger.error(f"Error formatting chunk: {e}")
        return None

def format_openai_stream_chunk(chunk: Union[StreamingChunk, Dict]) -> str:
    """
    Format a message chunk for OpenAI-compatible SSE streaming
    
    Args:
        chunk: Message chunk to format
        
    Returns:
        Formatted SSE data string in OpenAI format
    """
    if isinstance(chunk, dict):
        chunk = StreamingChunk.from_dict(chunk)
    
    if not isinstance(chunk, StreamingChunk):
        return None
        
    # 添加对代码执行输出的处理
    if chunk.type == 'console' and chunk.role == 'computer':
        output_block = f"\n```\n{chunk.content}\n```"
        response = {
            'id': f'chatcmpl-{str(uuid.uuid4())}',
            'object': 'chat.completion.chunk',
            'created': int(time.time()),
            'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
            'choices': [{
                'index': 0,
                'delta': {
                    'content': output_block,
                    'type': 'console_output'
                },
                'finish_reason': None
            }]
        }
        return f"data: {json.dumps(response)}\n\n"
    
    # 统一处理消息内容
    content = chunk.content
    if chunk.type == 'code':
        content = f"\n```{chunk.format or 'python'}\n{content}\n```"
    
    response = {
        'id': f'chatcmpl-{str(uuid.uuid4())}',
        'object': 'chat.completion.chunk',
        'created': int(time.time()),
        'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
        'choices': [{
            'index': 0,
            'delta': {
                'role': chunk.role,
                'content': content
            },
            'finish_reason': 'stop' if chunk.end else None
        }]
    }
    
    return f"data: {json.dumps(response)}\n\n"

class MessageProcessor:
    """消息处理工具类"""
    
    @staticmethod
    def process_response(response, session_manager=None, session_id=None):
        """处理非流式响应"""
        content = ''
        try:
            for chunk in response:
                try:
                    if isinstance(chunk, dict):
                        chunk = Message.from_dict(chunk)
                    if chunk.type == 'message' and chunk.role == 'assistant':
                        if content:
                            content += '\n'
                        content += chunk.content
                        # 保存消息到会话
                        if session_manager and session_id:
                            session_manager.add_message(session_id, chunk.to_dict())
                except Exception as e:
                    logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
                    continue
                    
            return {
                "id": f"chatcmpl-{str(uuid.uuid4())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",  # 使用固定的模型名称
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def validate_messages(messages):
        """验证消息格式"""
        if not messages:
            raise ValidationError("Messages array is required")
        return [Message.from_dict(msg) if isinstance(msg, dict) else msg for msg in messages]