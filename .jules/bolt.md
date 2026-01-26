## 2024-10-24 - Regex optimization in truncate_output
**Learning:** `re.finditer` was running on every string, even when truncation wasn't needed. Checking string length *before* regex operations yielded a ~438x speedup for strings within limits.
**Action:** Always check simple conditions (like string length) before running expensive operations (like regex). Pre-compile regex patterns at module level.
