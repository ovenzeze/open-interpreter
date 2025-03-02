"""
Utility functions for Open Interpreter HTTP Server
"""

import json
import uuid
import time
import logging
import platform
import psutil
import sys
from typing import Any, Dict, List, Union, Optional
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
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        msg_type = msg.get('type', 'message')  # 获取消息类型，默认为message
        recipient = msg.get('recipient', 'assistant' if role == 'user' else 'user')
        
        # 角色映射
        interpreter_role = role
        if role == 'system':
            interpreter_role = 'assistant'  # 系统消息在解释器中视为助手消息
            logger.info("Converting 'system' role to 'assistant'")
        elif role in ['function', 'tool', 'developer']:
            interpreter_role = 'computer'  # 这些角色在解释器中视为计算机消息
            logger.info(f"Converting '{role}' role to 'computer'")
        elif role not in ['user', 'assistant', 'computer']:
            interpreter_role = 'user'  # 默认将未知角色当作用户消息
            logger.warning(f"Unknown role '{role}', converting to 'user'")
        
        # 处理助手消息中的代码块
        if interpreter_role == 'assistant' and '```' in content:
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
            # 对于普通消息，使用已转换的角色和指定的类型
            interpreter_messages.append(Message(
                role=interpreter_role,
                type=msg_type,
                content=content,
                recipient=recipient
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

def get_system_info() -> Dict[str, Any]:
    """Safely gather system information"""
    info = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "platform": platform.system(),
            "version": platform.release(),
            "python": sys.version,
            "hostname": platform.node()
        }
    }
    
    try:
        memory = psutil.virtual_memory()
        info["memory"] = {
            "total": memory.total,
            "available": memory.available,
            "used_percent": memory.percent
        }
        
        disk = psutil.disk_usage('/')
        info["disk"] = {
            "total": disk.total,
            "free": disk.free,
            "used_percent": disk.percent
        }
    except Exception:
        pass  # Silently handle any hardware info gathering errors
        
    return info

def format_size(bytes: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f}{unit}"
        bytes /= 1024
    return f"{bytes:.2f}PB"

def normalize_session_batch(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量规范化会话数据，确保所有会话数据都符合模型定义
    
    Args:
        sessions: 会话数据列表
        
    Returns:
        规范化后的会话数据列表
    """
    normalized_sessions = []
    
    for session in sessions:
        normalized = normalize_session(session)
        normalized_sessions.append(normalized)
    
    return normalized_sessions

def normalize_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    规范化单个会话数据，确保所有字段符合模型定义
    
    Args:
        session_data: 会话数据
        
    Returns:
        规范化后的会话数据
    """
    normalized = session_data.copy()
    
    # 确保基本字段存在
    if 'session_id' not in normalized:
        normalized['session_id'] = str(uuid.uuid4())
    
    if 'created_at' not in normalized:
        normalized['created_at'] = datetime.now().isoformat()
    
    # 确保 last_active 是 ISO 格式字符串
    if 'last_active' in normalized and isinstance(normalized['last_active'], (int, float)):
        # 将时间戳转换为 ISO 格式
        normalized['last_active'] = datetime.fromtimestamp(normalized['last_active']).isoformat()
    elif 'last_active' not in normalized:
        normalized['last_active'] = datetime.now().isoformat()
    
    # 确保 messages 字段存在且为列表
    if 'messages' not in normalized:
        normalized['messages'] = []
    
    # 规范化每条消息
    normalized_messages = []
    for msg in normalized['messages']:
        normalized_msg = msg.copy()
        
        # 确保消息有 id
        if 'id' not in normalized_msg:
            normalized_msg['id'] = str(uuid.uuid4())
        
        # 确保消息有 created_at
        if 'created_at' not in normalized_msg:
            normalized_msg['created_at'] = datetime.now().isoformat()
        
        # 确保消息有 role 和 type
        if 'role' not in normalized_msg:
            normalized_msg['role'] = 'assistant'  # 默认为助手
        
        if 'type' not in normalized_msg:
            normalized_msg['type'] = 'message'  # 默认为消息类型
            
        # 确保 content 字段存在
        if 'content' not in normalized_msg:
            normalized_msg['content'] = ""
            
        normalized_messages.append(normalized_msg)
    
    normalized['messages'] = normalized_messages
    
    # 确保 metadata 字段存在且为字典
    if 'metadata' not in normalized:
        normalized['metadata'] = {}
    elif not isinstance(normalized['metadata'], dict):
        normalized['metadata'] = {}
    
    # 规范化元数据
    metadata = normalized['metadata']
    
    # 设置默认值（如果不存在）
    if 'safe_mode' not in metadata:
        metadata['safe_mode'] = True
    
    # 其他可选元数据字段，如果需要默认值可以在这里设置
    optional_fields = {
        'title': '',
        'description': '',
        'tags': [],
        'model': '',
        'preview': '',
        'language': '',
        'is_starred': False,
        'status': 'active',
        'turn_count': len(normalized['messages']) // 2,  # 粗略估计对话轮次
        'category': 'general',
        'last_modified': datetime.now().isoformat(),
        'context_window': 0,
        'max_tokens': 0
    }
    
    # 只设置不存在的字段
    for field, default_value in optional_fields.items():
        if field not in metadata:
            metadata[field] = default_value
    
    return normalized

def get_session_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取会话摘要信息，用于列表展示
    
    Args:
        session: 会话数据
        
    Returns:
        会话摘要信息
    """
    summary = {
        'session_id': session['session_id'],
        'created_at': session['created_at'],
        'last_active': session['last_active'],
        'message_count': len(session.get('messages', [])),
        'metadata': session.get('metadata', {})
    }
    
    # 添加标题（如果存在）
    metadata = session.get('metadata', {})
    if metadata.get('title'):
        summary['title'] = metadata['title']
    
    # 添加最后一条消息预览（如果存在）
    messages = session.get('messages', [])
    if messages:
        last_message = messages[-1]
        if last_message.get('role') == 'assistant' and last_message.get('type') == 'message':
            content = last_message.get('content', '')
            summary['last_message_preview'] = content[:100] + '...' if len(content) > 100 else content
    
    return summary