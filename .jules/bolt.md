## 2024-05-22 - Regex on every call
**Learning:** `truncate_output` was running a regex search on EVERY output string, even short ones that didn't need truncation. Moving the length check before the regex search resulted in a ~280x speedup for short strings.
**Action:** Always check "easy" exit conditions (like string length) before performing expensive operations (like regex). Pre-compile regexes at module level.
