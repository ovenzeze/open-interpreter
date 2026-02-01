## 2025-02-12 - Regex Performance on Large Strings
**Learning:** Regex operations (even pre-compiled) on large strings can be significant bottlenecks if executed frequently. In `truncate_output`, performing regex search before checking string length caused unnecessary overhead for strings that didn't need truncation.
**Action:** Always check cheap conditions (like string length) before performing expensive operations like regex. Move regex compilation to module level constants.
