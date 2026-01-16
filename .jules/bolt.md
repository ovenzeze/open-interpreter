## 2025-10-23 - Check Constraints Before Operations
**Learning:** Always check cheap constraints (like string length) before performing expensive operations (like regex searches) in utility functions.
**Action:** In `truncate_output`, moving `len(data) <= max_output_chars` before regex compilation/search significantly reduced overhead for short strings (0.0196s for 100k iterations).
