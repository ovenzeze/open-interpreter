## 2024-10-24 - Unnecessary Regex in Output Truncation
**Learning:** The `truncate_output` utility was running an O(N) regex search on every output string, even those well below the truncation limit. For high-frequency small outputs (common in LLM streaming/tool use), this adds significant overhead.
**Action:** Always check `len(data) <= limit` before performing expensive content scanning or regex operations in truncation utilities. Pre-compile regex patterns at module level.
