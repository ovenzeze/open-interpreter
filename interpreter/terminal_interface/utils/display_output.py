import base64
import os
import platform
import subprocess
import tempfile

from .in_jupyter_notebook import in_jupyter_notebook
from ...core.utils.truncate_output import truncate_output


def display_output(output):
    """
    Display output content with proper formatting and truncation.
    
    Args:
        output: Dictionary containing output type and content
    """
    if not isinstance(output, dict) or "type" not in output:
        return "Invalid output format"

    # Process content before display
    if output["type"] == "console":
        content = output["content"]
        max_output = output.get("max_output", 5000)  # Increased default limit
        
        # Apply truncation if needed
        if len(content) > max_output:
            content = truncate_output(
                content,
                max_output_chars=max_output,
                add_scrollbars=False
            )
            output["content"] = content  # Update the content
    
    # Display based on environment
    if in_jupyter_notebook():
        _display_jupyter(output)
    else:
        _display_cli(output)

    return "Content displayed successfully"


def _display_jupyter(output):
    """Handle Jupyter notebook display"""
    from IPython.display import HTML, Image, Javascript, display

    if output["type"] == "console":
        print(output["content"])
    elif output["type"] == "image":
        if "base64" in output["format"]:
            image_data = base64.b64decode(output["content"])
            display(Image(image_data))
        elif output["format"] == "path":
            display(Image(filename=output["content"]))
    elif "format" in output and output["format"] == "html":
        display(HTML(output["content"]))
    elif "format" in output and output["format"] == "javascript":
        display(Javascript(output["content"]))


def _display_cli(output):
    """Handle CLI display"""
    if output["type"] == "console":
        print(output["content"])
    elif output["type"] == "image":
        _handle_image_output(output)
    elif "format" in output:
        _handle_formatted_output(output)


def _handle_image_output(output):
    """Handle image output in CLI"""
    if "base64" in output["format"]:
        extension = output["format"].split(".")[-1] if "." in output["format"] else "png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp_file:
            image_data = base64.b64decode(output["content"])
            tmp_file.write(image_data)
            open_file(tmp_file.name)
    elif output["format"] == "path":
        open_file(output["content"])


def _handle_formatted_output(output):
    """Handle formatted output (HTML/JS) in CLI"""
    suffix = ".html" if output["format"] == "html" else ".js"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="w") as tmp_file:
        tmp_file.write(output["content"])
        open_file(tmp_file.name)


def open_file(file_path):
    """Open a file with the system's default application"""
    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", file_path])
        else:  # Linux and other Unix-like
            subprocess.run(["xdg-open", file_path])
    except Exception as e:
        print(f"Error opening file: {e}")
