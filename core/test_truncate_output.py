
import pytest
import importlib.util
import sys
import os

# Load module from file path to avoid package init dependencies
file_path = "interpreter/core/utils/truncate_output.py"
spec = importlib.util.spec_from_file_location("truncate_output", file_path)
module = importlib.util.module_from_spec(spec)
sys.modules["truncate_output_module"] = module
spec.loader.exec_module(module)
truncate_output = module.truncate_output

def test_under_limit():
    data = "a" * 100
    assert truncate_output(data, max_output_chars=200) == data

def test_over_limit():
    # Make data large enough so that even with footer it is truncated
    data = "a" * 5000
    result = truncate_output(data, max_output_chars=100)
    assert len(result) < 5000
    assert "..." in result
    assert "[Output truncated" in result

def test_with_errors_under_limit():
    data = "This is an error message"
    assert truncate_output(data, max_output_chars=200) == data

def test_with_errors_over_limit_preserves_error():
    # Construct a string with an error in the middle, and newlines to allow truncation context
    padding = ("a" * 100 + "\n") * 20 # 2020 chars with newlines
    error_msg = "CRITICAL error FOUND"
    data = padding + error_msg + padding

    # Max output small enough to require truncation
    result = truncate_output(data, max_output_chars=1000)

    # Should contain the error
    assert error_msg in result
    # Should be truncated
    assert len(result) < len(data)
    assert "[Output truncated" in result

def test_empty_string():
    assert truncate_output("", max_output_chars=100) == ""

def test_exact_limit():
    data = "a" * 100
    assert truncate_output(data, max_output_chars=100) == data

def test_no_errors_truncation_structure():
    data = "start" + ("." * 1000) + "end"
    result = truncate_output(data, max_output_chars=100)
    assert result.startswith("start")
    # assert result.endswith("end") # The footer is appended, so it won't end with "end"
    # Check that "end" is present before the footer
    assert "end" in result
    assert "..." in result
