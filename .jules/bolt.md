## 2024-05-22 - Regex Optimization in truncate_output
**Learning:** `truncate_output` was performing expensive regex searches on the entire string *before* checking if the string even needed truncation. For strings within the limit (common case), this introduced unnecessary overhead.
**Action:** Always check simple conditions (like string length) before performing expensive operations (like regex). Also, precompile regex patterns at the module level to avoid recompilation overhead.
