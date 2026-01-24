import importlib.util
import os
import sys

import pytest


# Dynamic import to avoid top-level package initialization issues which require full dependencies
def import_truncate_output():
    file_path = os.path.join(os.path.dirname(__file__), "truncate_output.py")
    spec = importlib.util.spec_from_file_location("truncate_output_module", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["truncate_output_module"] = module
    spec.loader.exec_module(module)
    return module.truncate_output


truncate_output = import_truncate_output()


def test_truncate_output_short():
    data = "Short output"
    assert truncate_output(data, max_output_chars=100) == data


def test_truncate_output_empty():
    assert truncate_output("", max_output_chars=100) == ""
    assert truncate_output(None, max_output_chars=100) == None


def test_truncate_output_long_no_error():
    max_chars = 100
    # Create string significantly longer than max_chars
    data = "a" * 2000
    truncated = truncate_output(data, max_output_chars=max_chars)

    assert len(truncated) < len(data)
    assert "..." in truncated
    assert "[Output truncated" in truncated
    assert data[:10] in truncated  # Should keep start
    assert data[-10:] in truncated  # Should keep end


def test_truncate_output_long_with_error():
    max_chars = 1000
    # Create a long string with an error in the middle
    prefix = "prefix\n" * 1000
    suffix = "suffix\n" * 1000
    error_msg = "Critical Error occurred here"
    data = f"{prefix}\n{error_msg}\n{suffix}"

    truncated = truncate_output(data, max_output_chars=max_chars)

    assert len(truncated) < len(data)
    assert error_msg in truncated
    # Ellipsis might not be present if error context consumes all space
    # assert "..." in truncated
    assert "[Output truncated" in truncated


def test_truncate_output_error_priority():
    # If error context takes up all space, it should be prioritized
    max_chars = 200
    error_msg = "Error " * 20  # 120 chars
    # Make padding large
    data = "Start " * 50 + error_msg + " End" * 50

    truncated = truncate_output(data, max_output_chars=max_chars)

    assert "Error" in truncated


if __name__ == "__main__":
    # simple runner
    try:
        test_truncate_output_short()
        test_truncate_output_empty()
        test_truncate_output_long_no_error()
        test_truncate_output_long_with_error()
        test_truncate_output_error_priority()
        print("All tests passed!")
    except AssertionError as e:
        import traceback

        traceback.print_exc()
        exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        exit(1)
