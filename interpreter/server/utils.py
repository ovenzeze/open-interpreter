"""Utility functions for Open Interpreter HTTP Server"""

import json
import uuid
import time
import logging
import platform
import psutil
import sys
from typing import Any, Dict, List, Union, Optional, Tuple, Generator, cast
from datetime import datetime
from .message import Message, StreamingChunk
from .errors import ValidationError
from pathlib import Path
import socket

logger = logging.getLogger(__name__)


def convert_openai_to_interpreter(messages: List[Dict[str, str]]) -> List[Message]:
    """Convert OpenAI format messages to Open Interpreter format."""
    interpreter_messages = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        msg_type = msg.get('type', 'message')  # Default message type
        recipient = msg.get('recipient', 'assistant' if role == 'user' else 'user')

        # Role mapping
        interpreter_role = role
        if role == 'system':
            interpreter_role = 'assistant'  # System messages treated as assistant
            logger.info("Converting 'system' role to 'assistant'")
        elif role in ['function', 'tool', 'developer']:
            interpreter_role = 'computer'  # These roles treated as computer
            logger.info(f"Converting '{role}' role to 'computer'")
        elif role not in ['user', 'assistant', 'computer']:
            interpreter_role = 'user'  # Unknown roles default to user
            logger.warning(f"Unknown role '{role}', converting to 'user'")

        # Handle code blocks in assistant messages
        if interpreter_role == 'assistant' and '```' in content:
            code_blocks = content.split('```')
            for i, block in enumerate(code_blocks):
                if i % 2 == 0:  # Non-code block
                    if block.strip():
                        interpreter_messages.append(Message(
                            role='assistant',
                            type='message',
                            content=block.strip(),
                            recipient=recipient
                        ))
                else:  # Code block
                    lang, code = 'python', block
                    if '\n' in block:
                        first_line = block.split('\n', 1)[0].strip()
                        if first_line in ['python', 'javascript', 'shell', 'html']:
                            lang = first_line
                            code = block.split('\n', 1)[1] if '\n' in block else ''
                        interpreter_messages.append(Message(
                            role='assistant',
                            type='code',
                            format=lang,
                            content=code.strip(),
                            recipient=recipient
                        ))
        else:
            # Regular message handling
            interpreter_messages.append(Message(
                role=interpreter_role,
                type=msg_type,
                content=content,
                recipient=recipient
            ))
    return interpreter_messages


def convert_interpreter_to_openai(messages: List[Message], session_id: Optional[str] = None, model: str = "gpt-4") -> List[Dict[str, str]]:
    """Convert Open Interpreter format messages to OpenAI format."""
    openai_messages = []
    current_message = None

    for msg in messages:
        if not isinstance(msg, Message):
            msg = Message.from_dict(msg)

        # OpenAI不支持'computer'角色，将其转换为'function'或'assistant'
        if msg.role == 'computer':
            if msg.type == 'console' and msg.format == 'output':
                new_message = {
                    'role': 'function',
                    'name': 'execute',
                    'content': str(msg.content) if not isinstance(msg.content, str) else msg.content
                }
                openai_messages.append(new_message)
                continue
            elif msg.type in ['confirmation', 'message', 'code']:
                new_message = {
                    'role': 'assistant',
                    'content': str(msg.content) if not isinstance(msg.content, str) else msg.content
                }
                openai_messages.append(new_message)
                continue
            else:
                # 对于其他类型，默认转换为assistant
                new_message = {
                    'role': 'assistant',
                    'content': str(msg.content) if not isinstance(msg.content, str) else msg.content
                }
                openai_messages.append(new_message)
                continue
        else:
            openai_role = msg.role
            if openai_role in ['user', 'assistant']:
                if current_message and (
                    current_message['role'] != openai_role or
                    msg.type != 'message'
                ):
                    openai_messages.append(current_message)
                    current_message = None

                if msg.type == 'message':
                    if current_message is None:
                        current_message = {
                            'role': openai_role,
                            'content': str(msg.content) if not isinstance(msg.content, str) else msg.content
                        }
                    else:
                        current_message['content'] += '\n' + str(msg.content)
                elif msg.type == 'code':
                    openai_messages.append({
                        'role': 'assistant',
                        'content': '',
                        'function_call': {
                            'name': 'execute',
                            'arguments': json.dumps({
                                'language': msg.format or 'python',
                                'code': str(msg.content) if not isinstance(msg.content, str) else msg.content
                            })
                        }
                    })
                elif msg.type == 'image':
                    openai_messages.append({
                        'role': openai_role,
                        'content': [{
                            'type': 'image_url',
                            'image_url': {
                                'url': f"data:image/{msg.format or 'png'};base64,{msg.content}"
                            }
                        }]
                    })

    if current_message:
        openai_messages.append(current_message)
    return openai_messages


def format_stream_chunk(chunk: Union[StreamingChunk, Dict]) -> str:
    """Format a message chunk for SSE streaming."""
    if isinstance(chunk, dict):
        chunk = StreamingChunk.from_dict(chunk)
    if not isinstance(chunk, StreamingChunk):
        return ""

    data = chunk.to_dict()
    return f"data: {json.dumps(data)}\n\n"


def format_openai_stream_chunk(chunk: Union[StreamingChunk, Dict]) -> str:
    """Format a message chunk for OpenAI-compatible SSE streaming."""
    if isinstance(chunk, dict):
        chunk = StreamingChunk.from_dict(chunk)
    if not isinstance(chunk, StreamingChunk):
        return ""

    openai_role = 'assistant' if chunk.role == 'computer' else chunk.role

    # 确保 JSON 转换为单行，避免多行导致的解析问题
    def to_single_line_json(obj):
        try:
            # 确保生成的JSON不包含实际换行符，使用紧凑模式
            return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
        except Exception as e:
            logger.error(f"JSON serialization error: {str(e)}")
            # 提供一个安全的回退方案
            return json.dumps({"error": str(e)})

    try:
        current_time = int(float(time.time()))  # 确保time.time()返回值被转换为int
        chunk_id = f'chatcmpl-{str(uuid.uuid4())}'
        
        # 控制台输出特殊处理 - 改进代码块格式处理
        if chunk.type == 'console' and chunk.role == 'computer':
            content_str = str(chunk.content) if not isinstance(chunk.content, str) else chunk.content
            # 替换可能导致问题的字符
            content_str = content_str.replace('\r', '').replace('\0', '')
            
            # 处理控制台输出的不同阶段 - 统一使用markdown代码块格式
            if chunk.start:
                # 控制台输出开始 - 使用明确的shell标记
                response = {
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': current_time,
                    'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'content': "\n```shell\n"  # 使用shell标记明确指示这是控制台输出
                        },
                        'finish_reason': None
                    }]
                }
            elif chunk.end:
                # 控制台输出结束
                response = {
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': current_time,
                    'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'content': "\n```\n"
                        },
                        'finish_reason': None
                    }]
                }
            else:
                # 控制台输出内容 - 直接传递内容
                response = {
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': current_time,
                    'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'content': content_str
                        },
                        'finish_reason': None
                    }]
                }
            return f"data: {to_single_line_json(response)}\n\n"

        # 代码块特殊处理 - 改进代码块的格式处理
        if chunk.type == 'code':
            content = str(chunk.content) if not isinstance(chunk.content, str) else chunk.content
            # 清理内容中可能导致问题的字符
            content = content.replace('\r', '').replace('\0', '')
            
            # 如果是代码块开始 - 使用更明确的语言标记
            if chunk.start:
                # 确保有语言标记，如果没有则默认为text
                lang = chunk.format or 'python'  # 默认使用python作为更常见的选择
                response = {
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': current_time,
                    'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'content': f"\n```{lang}\n"  # 明确的语言标记
                        },
                        'finish_reason': None
                    }]
                }
            # 如果是代码块结束
            elif chunk.end:
                response = {
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': current_time,
                    'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'content': "\n```\n"
                        },
                        'finish_reason': None
                    }]
                }
            # 普通代码内容
            else:
                response = {
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': current_time,
                    'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'content': content
                        },
                        'finish_reason': None
                    }]
                }
            return f"data: {to_single_line_json(response)}\n\n"

        # 普通消息内容处理
        content = str(chunk.content) if not isinstance(chunk.content, str) else chunk.content
        # 清理内容中可能导致问题的字符
        content = content.replace('\r', '').replace('\0', '')
        
        # 根据消息块类型构建响应
        # 如果是消息起始块
        if chunk.start:
            response = {
                'id': chunk_id,
                'object': 'chat.completion.chunk',
                'created': current_time,
                'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                'choices': [{
                    'index': 0,
                    'delta': {
                        'role': openai_role,
                        'content': content
                    },
                    'finish_reason': None
                }]
            }
        # 如果是消息结束块
        elif chunk.end:
            # 发送一个含有内容的chunk（如果有内容）
            if content:
                content_response = {
                    'id': chunk_id,
                    'object': 'chat.completion.chunk',
                    'created': current_time,
                    'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                    'choices': [{
                        'index': 0,
                        'delta': {
                            'role': openai_role,
                            'content': content
                        },
                        'finish_reason': None
                    }]
                }
                # 如果结束块有内容，先发送内容，再发送一个空的结束块
                result = f"data: {to_single_line_json(content_response)}\n\n"
            else:
                result = ""
            
            # 然后发送一个内容为空的带有finish_reason的结束块
            final_response = {
                'id': chunk_id,
                'object': 'chat.completion.chunk',
                'created': int(current_time),  # 确保current_time是整数
                'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                'choices': [{
                    'index': 0,
                    'delta': {
                        'content': ""  # 确保内容为空
                    },
                    'finish_reason': 'stop'
                }]
            }
            result += f"data: {to_single_line_json(final_response)}\n\n"
            result += "data: [DONE]\n\n"
            return result
        # 普通内容块
        else:
            response = {
                'id': chunk_id,
                'object': 'chat.completion.chunk',
                'created': current_time,
                'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
                'choices': [{
                    'index': 0,
                    'delta': {
                        'role': openai_role,
                        'content': content
                    },
                    'finish_reason': None
                }]
            }
        
        return f"data: {to_single_line_json(response)}\n\n"
            
    except Exception as e:
        # 记录错误但避免中断流式响应
        logger.error(f"Error formatting stream chunk: {str(e)}", exc_info=True)
        # 返回一个简单但有效的响应
        error_response = {
            'id': f'chatcmpl-error-{str(uuid.uuid4())}',
            'object': 'chat.completion.chunk',
            'created': int(float(time.time())),  # 确保time.time()返回值被转换为int
            'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
            'choices': [{
                'index': 0,
                'delta': {
                    'content': f"[Error: {str(e)}]"
                },
                'finish_reason': None
            }]
        }
        return f"data: {to_single_line_json(error_response)}\n\n"


class MessageProcessor:
    """Message processing utility class."""

    @staticmethod
    def process_response(response, session_manager=None, session_id=None):
        """Process non-streaming response."""
        content = ''
        try:
            for chunk in response:
                try:
                    if isinstance(chunk, dict):
                        chunk = Message.from_dict(chunk)
                    if chunk.type == 'message' and chunk.role == 'assistant':
                        if content:
                            content += '\n'
                        chunk_content = str(chunk.content) if not isinstance(chunk.content, str) else chunk.content
                        content += chunk_content

                        if session_manager and session_id:
                            session_manager.add_message(session_id, chunk.to_dict())
                except Exception as e:
                    logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
                    continue

            return {
                "id": f"chatcmpl-{str(uuid.uuid4())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
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
        """Validate message format and return processed messages."""
        if not messages:
            raise ValidationError("Messages array is required")
        return [Message.from_dict(msg) if isinstance(msg, dict) else msg for msg in messages]


def get_system_info() -> Dict[str, Any]:
    """Gather system information safely."""
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
        pass  # Silently handle hardware info gathering errors
    return info


def format_size(bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f}{unit}"
        bytes /= 1024
    return f"{bytes:.2f}PB"


def normalize_session_batch(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch normalize session data to match model definition."""
    normalized_sessions = []
    for session in sessions:
        normalized = normalize_session(session)
        normalized_sessions.append(normalized)
    return normalized_sessions


def normalize_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize single session data to match model definition."""
    normalized = session_data.copy()

    if 'session_id' not in normalized:
        normalized['session_id'] = str(uuid.uuid4())
    if 'created_at' not in normalized:
        normalized['created_at'] = datetime.now().isoformat()

    if 'last_active' in normalized and isinstance(normalized['last_active'], (int, float)):
        normalized['last_active'] = datetime.fromtimestamp(normalized['last_active']).isoformat()
    elif 'last_active' not in normalized:
        normalized['last_active'] = datetime.now().isoformat()

    if 'messages' not in normalized:
        normalized['messages'] = []

    normalized_messages = []
    for msg in normalized['messages']:
        normalized_msg = msg.copy()
        if 'id' not in normalized_msg:
            normalized_msg['id'] = str(uuid.uuid4())
        if 'created_at' not in normalized_msg:
            normalized_msg['created_at'] = datetime.now().isoformat()
        if 'role' not in normalized_msg:
            normalized_msg['role'] = 'assistant'
        if 'type' not in normalized_msg:
            normalized_msg['type'] = 'message'
        if 'content' not in normalized_msg:
            normalized_msg['content'] = ""
        normalized_messages.append(normalized_msg)

    normalized['messages'] = normalized_messages

    if 'metadata' not in normalized:
        normalized['metadata'] = {}
    elif not isinstance(normalized['metadata'], dict):
        normalized['metadata'] = {}

    metadata = normalized['metadata']
    if 'safe_mode' not in metadata:
        metadata['safe_mode'] = True

    optional_fields = {
        'title': '',
        'description': '',
        'tags': [],
        'model': '',
        'preview': '',
        'language': '',
        'is_starred': False,
        'status': 'active',
        'turn_count': len(normalized['messages']) // 2,
        'category': 'general',
        'last_modified': datetime.now().isoformat(),
        'context_window': 0,
        'max_tokens': 0
    }

    for field, default_value in optional_fields.items():
        if field not in metadata:
            metadata[field] = default_value

    return normalized


def get_session_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    """Get session summary for list display."""
    summary = {
        'session_id': session['session_id'],
        'created_at': session['created_at'],
        'last_active': session['last_active'],
        'message_count': len(session.get('messages', [])),
        'metadata': session.get('metadata', {})
    }

    metadata = session.get('metadata', {})
    if metadata.get('title'):
        summary['title'] = metadata['title']

    messages = session.get('messages', [])
    if messages:
        last_message = messages[-1]
        if last_message.get('role') == 'assistant' and last_message.get('type') == 'message':
            content = last_message.get('content', '')
            summary['last_message_preview'] = content[:100] + '...' if len(content) > 100 else content

    return summary