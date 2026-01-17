import os
import sys
import time

import pytest

try:
    from interpreter.core.utils.truncate_output import truncate_output
except ImportError:
    import importlib.util

    # Dynamic import to bypass package-level imports
    def import_truncate_output():
        file_path = os.path.join(
            os.path.dirname(__file__), "../interpreter/core/utils/truncate_output.py"
        )
        spec = importlib.util.spec_from_file_location(
            "truncate_output_module", file_path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["truncate_output_module"] = module
        spec.loader.exec_module(module)
        return module.truncate_output

    truncate_output = import_truncate_output()


def test_truncate_output_short():
    """Test that short strings are returned as is."""
    data = "Short string"
    assert truncate_output(data) == data


def test_truncate_output_long_no_error():
    """Test that long strings without errors are truncated."""
    max_chars = 100
    # Make data large enough so even with the appended message, it is shorter
    data = "a" * 1000
    result = truncate_output(data, max_output_chars=max_chars)

    assert len(result) < len(data)
    assert "..." in result
    assert "[Output truncated" in result


def test_truncate_output_with_error():
    """Test that error context is preserved."""
    max_chars = 100
    # Add newlines so the context extractor doesn't grab everything
    prefix = ("a" * 50 + "\n") * 20  # 1000+ chars with newlines
    error_msg = "Error: something went wrong"
    suffix = ("b" * 50 + "\n") * 20  # 1000+ chars with newlines
    data = f"{prefix}\n{error_msg}\n{suffix}"

    result = truncate_output(data, max_output_chars=max_chars)

    # Should contain the error message
    assert error_msg in result
    # Should be truncated
    assert len(result) < len(data)
    # Should have the truncation message
    assert "[Output truncated" in result


def test_no_data():
    assert truncate_output(None) is None
    assert truncate_output("") == ""
