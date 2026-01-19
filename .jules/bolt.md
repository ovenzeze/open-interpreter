## 2024-10-24 - Regex on Full String for Truncation
**Learning:** Checking string length before performing expensive regex operations for truncation significantly improves performance for non-truncated strings (150x speedup observed).
**Action:** Always verify if an expensive operation is actually needed based on simple properties (like length) before executing it. Pre-compile regex patterns at module level.
