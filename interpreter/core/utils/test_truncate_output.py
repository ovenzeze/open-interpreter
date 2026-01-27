
import unittest
import importlib.util
import sys
import os

# Dynamic import to avoid top-level package issues
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'truncate_output.py')
spec = importlib.util.spec_from_file_location("truncate_output_module", file_path)
module = importlib.util.module_from_spec(spec)
sys.modules["truncate_output_module"] = module
spec.loader.exec_module(module)
truncate_output = module.truncate_output

class TestTruncateOutput(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(truncate_output(""), "")

    def test_short_string(self):
        text = "Short text"
        self.assertEqual(truncate_output(text), text)

    def test_exact_length(self):
        text = "x" * 100
        self.assertEqual(truncate_output(text, max_output_chars=100), text)

    def test_long_string_no_error(self):
        length = 1000
        limit = 100
        text = "x" * length
        result = truncate_output(text, max_output_chars=limit)
        self.assertLess(len(result), length)
        self.assertIn("...", result)
        self.assertIn("Output truncated", result)

    def test_long_string_with_error(self):
        # Construct a long string with an error in the middle, and LOTS of newlines
        prefix = ("a" * 50 + "\n") * 50 # 2550 chars
        error_msg = "Critical error occurred"
        suffix = ("b" * 50 + "\n") * 50 # 2550 chars
        text = f"{prefix}\n{error_msg}\n{suffix}"

        limit = 1000
        result = truncate_output(text, max_output_chars=limit)

        # The result should contain the error message
        self.assertIn(error_msg, result)

        if len(result) < len(text):
             # It was truncated
             self.assertIn("Output truncated", result)
        else:
             # Logic decided to return everything (or more)
             pass

if __name__ == '__main__':
    unittest.main()
