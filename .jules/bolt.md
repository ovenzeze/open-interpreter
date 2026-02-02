## 2025-05-18 - Early Exit in String Processing
**Learning:** `truncate_output` was running expensive regex searches on *every* string, even short ones that didn't need truncation.
**Action:** Always check the "no-op" condition (e.g., length check) *before* performing expensive processing (regex, parsing) in utility functions.
