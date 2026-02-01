
import pytest
from interpreter.core.utils.truncate_output import truncate_output

def test_truncate_output_no_truncation():
    """Test that short output is not truncated."""
    data = "Short output"
    result = truncate_output(data, max_output_chars=100)
    assert result == data

def test_truncate_output_truncation_no_error():
    """Test that long output is truncated correctly when no errors present."""
    data = "a" * 1000
    # max_output_chars=100
    # It keeps 1/3 at start, 2/3 at end. 100 // 3 = 33 start, 200 // 3 = 66 end.
    # Total chars shown = 99 + message.
    result = truncate_output(data, max_output_chars=100)
    assert len(result) < len(data)
    assert "Output truncated" in result
    assert result.startswith("a" * 33)
    assert result.endswith("]") # End of message

def test_truncate_output_preserves_error():
    """Test that error context is preserved."""
    # We need newlines so that error context doesn't capture the entire string
    lines = ["line" for _ in range(1000)]
    lines.insert(500, "error: something went wrong")
    data = "\n".join(lines)

    result = truncate_output(data, max_output_chars=2000)

    assert "error: something went wrong" in result
    assert "Output truncated" in result
    assert len(result) < len(data)

def test_truncate_output_boundary():
    """Test boundary condition where length equals max_output_chars."""
    data = "a" * 100
    result = truncate_output(data, max_output_chars=100)
    assert result == data

def test_truncate_output_empty():
    """Test empty input."""
    assert truncate_output("") == ""
    assert truncate_output(None) is None
