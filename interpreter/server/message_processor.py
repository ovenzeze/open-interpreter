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
            for chunk in response:
                try:
                    chunk = Message.from_dict(chunk)
                    if chunk.type == 'message' and chunk.role == 'assistant':
                        if content:
                            content += '\n'
                        content += chunk.content
                        # 保存消息到会话
                        if session_manager and session_id:
                            session_manager.add_message(session_id, chunk.to_dict())
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