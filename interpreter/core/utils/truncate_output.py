import re

def truncate_output(data, max_output_chars=5000, add_scrollbars=False):
    """
    Truncate output data while preserving error context.
    
    Args:
        data: The input string to truncate
        max_output_chars: Maximum number of characters to keep (default 5000)
        add_scrollbars: Whether to add scrollbar support (default False)
    """
    if not data:
        return data

    # Preserve critical error information
    error_pattern = r'\b(error|warning|exception|traceback)\b'
    error_matches = list(re.finditer(error_pattern, data, re.IGNORECASE))
    
    # If no truncation needed, return original
    if len(data) <= max_output_chars:
        return data
        
    # Collect error context with improved ranges
    error_context = []
    for match in error_matches:
        # Capture more context around errors
        start = max(0, match.start() - 200)  # Increased from 100
        end = min(len(data), match.end() + 800)  # Increased from 500
        # Get complete lines containing the error
        while start > 0 and data[start] != '\n':
            start -= 1
        while end < len(data) and data[end] != '\n':
            end += 1
        error_context.append(data[start:end])
    
    # Basic truncation showing both start and end
    if error_context:
        # With errors, show error context and remaining space
        error_content = '\n'.join(error_context)
        available_chars = max_output_chars - len(error_content) - 100  # Buffer for messages
        if available_chars > 0:
            start_portion = data[:available_chars//3]
            end_portion = data[-available_chars*2//3:]
            truncated = f"{start_portion}\n...\n{error_content}\n...\n{end_portion}"
        else:
            truncated = error_content
    else:
        # Without errors, show beginning and end of content
        start_portion = data[:max_output_chars//3]
        end_portion = data[-max_output_chars*2//3:]
        truncated = f"{start_portion}\n...\n{end_portion}"
    
    # Add truncation notification
    if len(truncated) < len(data):
        total_lines = data.count('\n') + 1
        shown_lines = truncated.count('\n') + 1
        message = f"\n\n[Output truncated from {total_lines} to {shown_lines} lines. Total characters: {len(data)}, Shown: {len(truncated)}]"
        message += "\n[Use output redirection (>) or paging (|less) for full content]"
        truncated += message

    return truncated
