## 2025-10-24 - Regex Overhead in Streaming Outputs
**Learning:** The `truncate_output` utility is called frequently during streaming operations (e.g. `_respond_and_store`). Doing expensive regex searches on the full string *before* checking if truncation is even needed causes significant overhead, especially as the string grows.
**Action:** Always check simple conditions (like string length) before invoking expensive operations like regex, especially in hot paths like streaming loops. Pre-compile regexes at module level.
