
import pytest
from .truncate_output import truncate_output

def test_no_truncation_needed():
    data = "Short string"
    assert truncate_output(data, max_output_chars=100) == data

def test_empty_string():
    assert truncate_output("", max_output_chars=100) == ""

def test_truncation_no_errors():
    # Add newlines so truncation logic works as expected
    data = ("a" * 50 + "\n") * 20 # 1020 chars
    truncated = truncate_output(data, max_output_chars=100)

    assert len(truncated) < len(data)
    assert "..." in truncated

def test_preserves_error_context():
    # Construct a string with an error in the middle and newlines
    prefix = ("a" * 50 + "\n") * 100
    error = "Error: Critical failure"
    suffix = ("b" * 50 + "\n") * 100
    data = prefix + error + "\n" + suffix

    truncated = truncate_output(data, max_output_chars=1000)

    # Check that error is preserved
    assert "Error: Critical failure" in truncated
    # Check that it is truncated
    assert len(truncated) < len(data)

def test_multiple_errors():
    error1 = "Error: First"
    error2 = "Warning: Second"
    data = ("x" * 50 + "\n") * 100 + error1 + "\n" + ("y" * 50 + "\n") * 100 + error2 + "\n" + ("z" * 50 + "\n") * 100

    truncated = truncate_output(data, max_output_chars=1000)

    assert error1 in truncated
    assert error2 in truncated
    assert len(truncated) < len(data)

def test_exact_limit():
    data = "a" * 100
    assert truncate_output(data, max_output_chars=100) == data
