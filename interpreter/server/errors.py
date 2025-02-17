"""
Error handling for Open Interpreter HTTP Server
"""

from typing import Dict, Tuple, Union

class InterpreterError(Exception):
    """Base exception class for Open Interpreter errors"""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class ValidationError(InterpreterError):
    """Raised when request validation fails"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class ConfigurationError(InterpreterError):
    """Raised when there's an error in configuration"""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class ExecutionError(InterpreterError):
    """Raised when code execution fails"""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

def format_error_response(error: Union[InterpreterError, Exception]) -> Tuple[Dict, int]:
    """
    Format error response for API endpoints
    
    Args:
        error: Exception instance
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    if isinstance(error, InterpreterError):
        status_code = error.status_code
        message = error.message
    else:
        status_code = 500
        message = str(error)
    
    return {
        "error": {
            "message": message,
            "type": error.__class__.__name__
        }
    }, status_code 