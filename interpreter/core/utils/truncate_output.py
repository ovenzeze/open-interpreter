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

    # 1. Early return optimization:
    # If data is within limits, return immediately.
    # This avoids expensive regex searches on the common path.
    if len(data) <= max_output_chars:
        return data

    # Preserve critical error information
    error_pattern = r'\b(error|warning|exception|traceback)\b'
    error_matches = list(re.finditer(error_pattern, data, re.IGNORECASE))
    
    error_context = []
    if error_matches:
        # 2. Context Merging and Efficient Extraction
        # Collect all desired ranges
        ranges = []
        for match in error_matches:
            # Capture context around errors (-200 to +800)
            start_index = max(0, match.start() - 200)
            end_index = min(len(data), match.end() + 800)

            # Expand to full lines efficiently using rfind/find
            # Find newline before start_index
            line_start = data.rfind('\n', 0, start_index)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1 # Start after the newline

            # Find newline after end_index
            line_end = data.find('\n', end_index)
            if line_end == -1:
                line_end = len(data)

            ranges.append((line_start, line_end))

        # Merge overlapping ranges
        if ranges:
            ranges.sort()
            merged = [ranges[0]]
            for current_start, current_end in ranges[1:]:
                last_start, last_end = merged[-1]
                if current_start <= last_end: # Overlap or adjacent
                    # Merge
                    merged[-1] = (last_start, max(last_end, current_end))
                else:
                    merged.append((current_start, current_end))

            # Extract content from merged ranges
            for start, end in merged:
                error_context.append(data[start:end])
    
    # Basic truncation showing both start and end
    if error_context:
        # With errors, show error context and remaining space
        error_content = '\n'.join(error_context)
        available_chars = max_output_chars - len(error_content) - 100  # Buffer for messages

        # If errors take up too much space, we still prioritize showing them,
        # but we might need to be careful not to return a huge string if many errors exist.
        # However, preserving errors is the priority.
        # The original implementation allowed overflow for errors, so we stick to that.

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
