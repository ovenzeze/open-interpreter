import pytest
from interpreter.core.utils.truncate_output import truncate_output

def test_truncate_no_truncation():
    """Test that short strings are returned as is."""
    data = "Short string"
    assert truncate_output(data, max_output_chars=100) == data

def test_truncate_with_errors():
    """Test that error context is preserved even when truncating."""
    data = "Start\n" + "x" * 1000 + "\nError: something went wrong\n" + "y" * 1000 + "\nEnd"

    # Use a large enough limit to include error context but small enough to trigger truncation
    truncated = truncate_output(data, max_output_chars=5000)
    assert "Error: something went wrong" in truncated

def test_truncate_without_errors():
    """Test truncation of long strings without errors."""
    data = "x" * 10000
    truncated = truncate_output(data, max_output_chars=100)

    assert len(truncated) < 10000
    assert "..." in truncated
    assert "[Output truncated" in truncated

def test_truncate_boundary():
    """Test boundary condition where length equals limit."""
    data = "x" * 100
    assert truncate_output(data, max_output_chars=100) == data

def test_empty_input():
    """Test handling of empty or None input."""
    assert truncate_output("") == ""
    assert truncate_output(None) is None
