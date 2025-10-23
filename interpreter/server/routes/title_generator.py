"""
标题生成服务路由
提供基于会话内容生成标题的功能
使用Google Gemini API进行生成
"""

import os
import json
import requests
from flask import Blueprint, jsonify, request, current_app
from flask_openapi3 import APIBlueprint
from ..errors import ValidationError, format_error_response
from ..log_config import logger

# 创建蓝图
bp = APIBlueprint('title_generator', __name__)

@bp.route('/v1/sessions/<session_id>/generate-title', methods=['POST'])
def generate_title(session_id):
    """
    为指定会话生成标题
    
    请求参数:
    - prompt (可选): 自定义提示词，用于指导标题生成
    - fields (可选): 需要生成的元数据字段列表，默认只生成title
      可选值: title, description, tags, category, language, preview
    
    返回:
    - 生成的元数据和更新后的会话信息
    """
    try:
        # 检查会话是否存在
        session = current_app.session_manager.get_session(session_id)
        if not session:
            logger.debug(f"Session not found when generating title: {session_id}")
            return jsonify({"error": "Session not found"}), 404
        
        # 获取请求数据
        data = request.get_json() or {}
        custom_prompt = data.get('prompt', '')
        fields = data.get('fields', ['title'])
        
        # 确保fields是列表
        if isinstance(fields, str):
            fields = [fields]
        
        # 验证字段
        valid_fields = ['title', 'description', 'tags', 'category', 'language', 'preview']
        fields = [field for field in fields if field in valid_fields]
        
        # 如果没有有效字段，默认生成标题
        if not fields:
            fields = ['title']
        
        # 获取会话消息
        messages = session.get('messages', [])
        
        # 限制消息数量，最多取前10条
        messages = messages[:10]
        
        # 如果没有消息，返回错误
        if not messages:
            logger.warning(f"No messages in session {session_id}, cannot generate title")
            return jsonify({"error": "Cannot generate title for empty session"}), 400
        
        # 构建提示词
        if custom_prompt:
            prompt = f"{custom_prompt}\n\n会话内容:\n"
            is_custom_prompt = True
        else:
            prompt = generate_prompt_for_fields(fields)
            prompt += "\n\n会话内容:\n"
            is_custom_prompt = False
        
        # 添加消息内容到提示词
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            prompt += f"{role}: {content}\n"
        
        # 调用Gemini API生成元数据
        metadata_text = call_gemini_api(prompt)
        
        # 添加日志记录
        logger.debug(f"Gemini API response for session {session_id}: {metadata_text}")
        
        if not metadata_text:
            return jsonify({"error": "Failed to generate metadata"}), 500
        
        # 解析生成的元数据
        generated_metadata = parse_metadata(metadata_text, fields, is_custom_prompt)
        
        # 更新会话元数据
        if 'metadata' not in session:
            session['metadata'] = {}
        
        # 将生成的元数据合并到会话元数据中
        for field, value in generated_metadata.items():
            session['metadata'][field] = value
        
        # 保存更新后的会话
        current_app.session_manager.update_session(session_id, {'metadata': session['metadata']})
        
        # 规范化会话数据
        from ..utils import normalize_session
        normalized_session = normalize_session(session)
        
        return jsonify({
            "metadata": generated_metadata,
            "session": normalized_session
        })
        
    except Exception as e:
        logger.error(f"Metadata generation failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

def generate_prompt_for_fields(fields):
    """
    根据需要生成的字段构建提示词
    
    参数:
    - fields: 需要生成的字段列表
    
    返回:
    - 构建的提示词
    """
    field_descriptions = {
        'title': "一个简短、具体且有描述性的标题，不超过20个字符",
        'description': "一段简短的描述，概括会话的主要内容，不超过100个字符",
        'tags': "3-5个与会话内容相关的关键词，以数组形式返回",
        'category': "会话所属的一个主要类别，如'技术支持'、'知识问答'、'创意写作'等",
        'language': "会话使用的主要语言，如'中文'、'英文'等",
        'preview': "会话内容的简短摘要，不超过50个字符"
    }
    
    # 构建JSON格式的示例
    json_example = "{\n"
    for field in fields:
        if field in field_descriptions:
            if field == 'tags':
                json_example += f'  "{field}": ["标签1", "标签2", "标签3"],\n'
            else:
                json_example += f'  "{field}": "{field_descriptions[field]}",\n'
    
    # 移除最后一个逗号
    if json_example.endswith(",\n"):
        json_example = json_example[:-2] + "\n"
    
    json_example += "}"
    
    # 构建提示词
    prompt = "请为以下对话生成元数据，并以JSON格式返回，使用英文字段名。\n\n"
    prompt += "需要生成的字段：\n"
    
    for field in fields:
        if field in field_descriptions:
            prompt += f"- {field}: {field_descriptions[field]}\n"
    
    prompt += f"\n请按照以下JSON格式返回结果：\n{json_example}\n"
    prompt += "\n请确保返回的是有效的JSON格式，使用英文字段名，不要包含任何额外的文本或解释。"
    
    return prompt

def parse_metadata(metadata_text, fields, is_custom_prompt=False):
    """
    解析生成的元数据文本
    
    参数:
    - metadata_text: 生成的元数据文本
    - fields: 需要解析的字段列表
    - is_custom_prompt: 是否使用了自定义提示
    
    返回:
    - 解析后的元数据字典
    """
    result = {}
    
    # 清理文本，移除可能的markdown代码块标记
    cleaned_text = metadata_text.strip()
    # 移除开头的```json或```
    if cleaned_text.startswith("```"):
        first_newline = cleaned_text.find("\n")
        if first_newline > 0:
            cleaned_text = cleaned_text[first_newline:].strip()
    
    # 移除结尾的```
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3].strip()
    
    # 首先尝试将整个文本解析为JSON
    try:
        json_data = json.loads(cleaned_text)
        # 如果成功解析为JSON，直接提取所需字段
        for field in fields:
            if field in json_data:
                result[field] = json_data[field]
        
        # 如果提取到了所有字段，直接返回结果
        if all(field in result for field in fields):
            return result
    except json.JSONDecodeError:
        # 如果不是有效的JSON，继续使用其他解析方法
        logger.debug(f"Failed to parse as JSON: {cleaned_text[:100]}...")
    
    # 如果是自定义提示，尝试更灵活的解析方式
    if is_custom_prompt:
        # 尝试解析为JSON
        try:
            # 检查文本是否包含JSON格式的数据
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned_text[json_start:json_end+1]
                json_data = json.loads(json_str)
                
                # 提取请求的字段
                for field in fields:
                    if field in json_data:
                        result[field] = json_data[field]
            else:
                # 如果不是JSON格式，尝试按行解析
                lines = cleaned_text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 尝试找到字段名和值的分隔符
                    for separator in ['：', ':', '=']:
                        if separator in line:
                            parts = line.split(separator, 1)
                            field_name = parts[0].strip().lower()
                            field_value = parts[1].strip()
                            
                            # 映射字段名
                            field_mapping = {
                                '标题': 'title',
                                'title': 'title',
                                '描述': 'description',
                                'description': 'description',
                                '标签': 'tags',
                                'tags': 'tags',
                                '分类': 'category',
                                'category': 'category',
                                '语言': 'language',
                                'language': 'language',
                                '预览': 'preview',
                                'preview': 'preview'
                            }
                            
                            if field_name in field_mapping and field_mapping[field_name] in fields:
                                mapped_field = field_mapping[field_name]
                                
                                # 特殊处理标签字段
                                if mapped_field == 'tags' and isinstance(field_value, str):
                                    # 将标签字符串转换为列表
                                    tags = [tag.strip() for tag in field_value.split(',')]
                                    result[mapped_field] = tags
                                else:
                                    result[mapped_field] = field_value
                            
                            break
        except Exception as e:
            logger.error(f"Error parsing custom prompt metadata: {str(e)}", exc_info=True)
            
        # 如果只请求了标题字段且未找到，将整个文本作为标题
        if len(fields) == 1 and fields[0] == 'title' and 'title' not in result:
            result['title'] = cleaned_text.strip()
    else:
        # 如果只生成标题，直接解析
        if len(fields) == 1 and fields[0] == 'title':
            # 尝试解析为JSON
            try:
                json_data = json.loads(cleaned_text)
                if 'title' in json_data:
                    result['title'] = json_data['title']
                    return result
            except json.JSONDecodeError:
                pass
            
            # 如果无法解析为JSON或不包含title字段，直接使用清理后的文本
            result['title'] = cleaned_text.strip()
            return result
        
        # 尝试按行解析
        lines = cleaned_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试找到字段名和值的分隔符
            for separator in ['：', ':', '=']:
                if separator in line:
                    parts = line.split(separator, 1)
                    field_name = parts[0].strip().lower()
                    field_value = parts[1].strip()
                    
                    # 映射字段名
                    field_mapping = {
                        '标题': 'title',
                        'title': 'title',
                        '描述': 'description',
                        'description': 'description',
                        '标签': 'tags',
                        'tags': 'tags',
                        '分类': 'category',
                        'category': 'category',
                        '语言': 'language',
                        'language': 'language',
                        '预览': 'preview',
                        'preview': 'preview'
                    }
                    
                    if field_name in field_mapping and field_mapping[field_name] in fields:
                        mapped_field = field_mapping[field_name]
                        
                        # 特殊处理标签字段
                        if mapped_field == 'tags' and isinstance(field_value, str):
                            # 将标签字符串转换为列表
                            tags = [tag.strip() for tag in field_value.split(',')]
                            result[mapped_field] = tags
                        else:
                            result[mapped_field] = field_value
                    
                    break
    
    # 确保所有请求的字段都有值
    for field in fields:
        if field not in result:
            # 设置默认值
            if field == 'tags':
                result[field] = []
            else:
                result[field] = ""
    
    return result

def call_gemini_api(prompt):
    """
    调用Google Gemini API生成元数据
    
    参数:
    - prompt: 提示词
    
    返回:
    - 生成的元数据文本
    """
    try:
        # 从环境变量获取API密钥
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            return None
        
        # 添加格式化指令
        formatted_prompt = prompt + "\n\n请严格按照以下要求返回：\n1. 只返回JSON格式数据，不要包含任何其他文本\n2. 不要使用markdown代码块标记(```)包裹JSON\n3. 确保JSON格式正确，可以被解析\n4. 使用JSON.stringify格式化输出结果"
        
        # Gemini API端点
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        # 构建请求体
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": formatted_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 32,
                "topP": 0.95,
                "maxOutputTokens": 100,
                "stopSequences": []
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        # 记录请求内容
        logger.debug(f"Gemini API request: {formatted_prompt[:100]}...")
        
        # 发送请求
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        # 检查响应状态
        if response.status_code != 200:
            logger.error(f"Gemini API error: {response.status_code} - {response.text}")
            return None
        
        # 解析响应
        response_data = response.json()
        
        # 记录完整响应
        logger.debug(f"Gemini API full response: {response_data}")
        
        # 提取生成的文本
        if 'candidates' in response_data and response_data['candidates']:
            candidate = response_data['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                parts = candidate['content']['parts']
                if parts and 'text' in parts[0]:
                    return parts[0]['text'].strip()
        
        logger.error(f"Failed to extract metadata from Gemini API response: {response_data}")
        return None
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}", exc_info=True)
        return None 