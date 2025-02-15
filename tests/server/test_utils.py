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
    
    expected = [
        {
            'role': 'user',
            'type': 'message',
            'content': 'Hello'
        },
        {
            'role': 'assistant',
            'type': 'message',
            'content': 'Hi there!'
        }
    ]
    
    result = convert_openai_to_interpreter(openai_messages)
    assert result == expected


def test_convert_interpreter_to_openai():
    """Test conversion from Interpreter format to OpenAI format"""
    interpreter_messages = [
        {
            'role': 'user',
            'type': 'message',
            'content': 'Hello'
        },
        {
            'role': 'assistant',
            'type': 'message',
            'content': 'Hi there!'
        },
        {
            'role': 'assistant',
            'type': 'code',
            'content': 'print("Hello")'
        }
    ]
    
    expected = [
        {
            'role': 'user',
            'content': 'Hello'
        },
        {
            'role': 'assistant',
            'content': 'Hi there!'
        }
    ]
    
    result = convert_interpreter_to_openai(interpreter_messages)
    assert result == expected


def test_format_stream_chunk():
    """Test formatting of stream chunks"""
    # Test assistant message chunk
    chunk = {
        'role': 'assistant',
        'type': 'message',
        'content': 'Hello'
    }
    result = format_stream_chunk(chunk)
    assert result.startswith('data: ')
    assert result.endswith('\n\n')
    data = json.loads(result.replace('data: ', '').strip())
    assert data['content'] == 'Hello'
    
    # Test non-message chunk
    chunk = {
        'role': 'assistant',
        'type': 'code',
        'content': 'print("Hello")'
    }
    result = format_stream_chunk(chunk)
    assert result == ''
    
    # Test non-assistant chunk
    chunk = {
        'role': 'user',
        'type': 'message',
        'content': 'Hello'
    }
    result = format_stream_chunk(chunk)
    assert result == ''


def test_format_openai_stream_chunk():
    """Test formatting of OpenAI-compatible stream chunks"""
    # Test assistant message chunk
    chunk = {
        'role': 'assistant',
        'type': 'message',
        'content': 'Hello'
    }
    result = format_openai_stream_chunk(chunk)
    assert result.startswith('data: ')
    assert result.endswith('\n\n')
    data = json.loads(result.replace('data: ', '').strip())
    assert 'choices' in data
    assert len(data['choices']) == 1
    assert data['choices'][0]['delta']['content'] == 'Hello'
    
    # Test non-message chunk
    chunk = {
        'role': 'assistant',
        'type': 'code',
        'content': 'print("Hello")'
    }
    result = format_openai_stream_chunk(chunk)
    assert result == ''
    
    # Test non-assistant chunk
    chunk = {
        'role': 'user',
        'type': 'message',
        'content': 'Hello'
    }
    result = format_openai_stream_chunk(chunk)
    assert result == '' 