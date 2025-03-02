"""
消息处理工具类
"""

import time
import uuid
from flask import current_app
from .message import Message, StreamingChunk
from .errors import ValidationError

class MessageProcessor:
    """消息处理工具类"""
    
    @staticmethod
    def process_response(response, session_manager=None, session_id=None):
        """处理非流式响应"""
        content = ''
        try:
            # 检查会话中是否已有消息，避免重复添加
            existing_messages = []
            if session_manager and session_id:
                existing_messages = session_manager.get_messages(session_id) or []
                existing_contents = [msg.get('content', '') for msg in existing_messages 
                                    if msg.get('role') == 'assistant' and msg.get('type') == 'message']
            
            for chunk in response:
                try:
                    chunk = Message.from_dict(chunk)
                    if chunk.type == 'message' and chunk.role == 'assistant':
                        if content:
                            content += '\n'
                        content += chunk.content
                        
                        # 保存消息到会话，但避免重复添加
                        if session_manager and session_id:
                            # 检查消息内容是否已存在
                            if chunk.content not in existing_contents:
                                session_manager.add_message(session_id, chunk.to_dict())
                                # 更新已存在的内容列表，防止在同一响应中有多个相同内容的块
                                existing_contents.append(chunk.content)
                except Exception as e:
                    current_app.logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
                    continue
                    
            return {
                "id": f"chatcmpl-{str(uuid.uuid4())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": current_app.interpreter_instance.llm.model,
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
            current_app.logger.error(f"Error processing response: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def validate_messages(messages):
        """验证消息格式"""
        if not messages:
            raise ValidationError("Messages array is required")
        return [Message.from_dict(msg) if isinstance(msg, dict) else msg for msg in messages] 