"""
Tests for Open Interpreter HTTP Server utilities
"""

import json

from interpreter.server.utils import (
    convert_interpreter_to_openai,
    convert_openai_to_interpreter,
    format_openai_stream_chunk,
    format_stream_chunk,
)
from interpreter.server.message import Message


def test_convert_openai_to_interpreter():
    """Test conversion from OpenAI format to Interpreter format"""
    openai_messages = [
        {
            'role': 'user',
            'content': 'Hello'
        },
        {
            'role': 'assistant',
            'content': 'Hi there!'
        }
    ]
    
    result = convert_openai_to_interpreter(openai_messages)
    
    # 检查返回的是Message对象列表
    assert len(result) == 2
    assert isinstance(result[0], Message)
    assert isinstance(result[1], Message)
    
    # 检查Message对象的属性
    assert result[0].role == 'user'
    assert result[0].type == 'message'
    assert result[0].content == 'Hello'
    
    assert result[1].role == 'assistant'
    assert result[1].type == 'message'
    assert result[1].content == 'Hi there!'


def test_convert_interpreter_to_openai():
    """Test conversion from Interpreter format to OpenAI format"""
    # 创建Message对象列表
    interpreter_messages = [
        Message(role='user', type='message', content='Hello'),
        Message(role='assistant', type='message', content='Hi there!'),
        Message(role='assistant', type='code', content='print("Hello")', format='python')
    ]
    
    result = convert_interpreter_to_openai(interpreter_messages)
    
    # 现在我们期望code类型的消息也被转换为带有Markdown代码块的消息
    assert len(result) == 3
    
    assert result[0]['role'] == 'user'
    assert result[0]['content'] == 'Hello'
    
    assert result[1]['role'] == 'assistant'
    assert result[1]['content'] == 'Hi there!'
    
    assert result[2]['role'] == 'assistant'
    assert result[2]['content'] == '```python\nprint("Hello")\n```'


def test_format_stream_chunk():
    """Test formatting of stream chunks"""
    # Test assistant message chunk
    chunk = {
        'role': 'assistant',
        'type': 'message',
        'content': 'Hello'
    }
    result = format_stream_chunk(chunk)
    
    # 检查返回的是JSON字符串
    assert isinstance(result, str)
    
    # 尝试解析JSON
    try:
        data = json.loads(result)
        assert data['role'] == 'assistant'
        assert data['type'] == 'message'
        assert data['content'] == 'Hello'
    except json.JSONDecodeError:
        assert False, "Result is not valid JSON"
    
    # Test computer console chunk
    chunk = {
        'role': 'computer',
        'type': 'console',
        'content': 'Output text'
    }
    result = format_stream_chunk(chunk)
    
    # 检查返回的是JSON字符串
    assert isinstance(result, str)
    
    # 尝试解析JSON
    try:
        data = json.loads(result)
        assert data['role'] == 'computer'
        assert data['type'] == 'console'
        assert data['content'] == 'Output text'
    except json.JSONDecodeError:
        assert False, "Result is not valid JSON"


def test_format_openai_stream_chunk():
    """Test formatting of OpenAI-compatible stream chunks"""
    # Test assistant message chunk
    chunk = {
        'role': 'assistant',
        'type': 'message',
        'content': 'Hello'
    }
    result = format_openai_stream_chunk(chunk)
    
    # 检查返回的是SSE格式
    assert result.startswith('data: ')
    assert result.endswith('\n\n')
    
    # 解析JSON数据
    data = json.loads(result.replace('data: ', '').strip())
    assert 'choices' in data
    assert len(data['choices']) == 1
    assert data['choices'][0]['delta']['content'] == 'Hello'
    
    # Test code chunk
    chunk = {
        'role': 'assistant',
        'type': 'code',
        'content': 'print("Hello")',
        'format': 'python'
    }
    result = format_openai_stream_chunk(chunk)
    
    # 检查返回的是SSE格式
    assert result.startswith('data: ')
    assert result.endswith('\n\n')
    
    # 解析JSON数据
    data = json.loads(result.replace('data: ', '').strip())
    assert 'choices' in data
    assert len(data['choices']) == 1
    assert data['choices'][0]['delta']['content'] == '\n```python\nprint("Hello")\n```'
    
    # Test console chunk
    chunk = {
        'role': 'computer',
        'type': 'console',
        'content': 'Output text'
    }
    result = format_openai_stream_chunk(chunk)
    
    # 检查返回的是SSE格式
    assert result.startswith('data: ')
    assert result.endswith('\n\n')
    
    # 解析JSON数据
    data = json.loads(result.replace('data: ', '').strip())
    assert 'choices' in data
    assert len(data['choices']) == 1
    assert data['choices'][0]['delta']['content'] == '\n```\nOutput text\n```'
    assert data['choices'][0]['delta']['type'] == 'console_output' 