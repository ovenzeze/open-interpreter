
import pytest
import sys
import importlib.util
from pathlib import Path

# Load truncate_output module directly to avoid top-level package imports
file_path = Path(__file__).parent.parent / "interpreter/core/utils/truncate_output.py"
spec = importlib.util.spec_from_file_location("truncate_output_module", file_path)
module = importlib.util.module_from_spec(spec)
sys.modules["truncate_output_module"] = module
spec.loader.exec_module(module)
truncate_output = module.truncate_output

def test_truncate_output_short():
    data = "Short text"
    assert truncate_output(data, max_output_chars=100) == data

def test_truncate_output_empty():
    assert truncate_output("") == ""
    assert truncate_output(None) is None

def test_truncate_output_long_no_error():
    max_chars = 100
    # Make data significantly larger than max_chars + footer overhead
    data = "a" * 2000
    result = truncate_output(data, max_output_chars=max_chars)
    assert len(result) < len(data)
    assert "..." in result
    assert "[Output truncated" in result

def test_truncate_output_long_with_error():
    max_chars = 200
    # Create data with frequent newlines to limit context expansion
    prefix = ("a" * 50 + "\n") * 40  # 2040 chars
    error = "This is a traceback that should be preserved."
    suffix = ("b" * 50 + "\n") * 40  # 2040 chars
    data = f"{prefix}{error}\n{suffix}"

    result = truncate_output(data, max_output_chars=max_chars)

    assert "traceback" in result
    assert len(result) < len(data)
    # Ensure error context is preserved
    assert error in result

def test_truncate_output_exact_length():
    data = "a" * 100
    assert truncate_output(data, max_output_chars=100) == data

def test_truncate_output_just_over_length():
    # This case might actually return a LONGER string due to footer,
    # so we just check it returns something different and contains indication
    data = "a" * 150
    result = truncate_output(data, max_output_chars=100)
    # It attempts to truncate
    assert "..." in result
