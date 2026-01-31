## 2024-05-23 - truncate_output Performance and Logic
**Learning:** `re.finditer` and regex compilation are significant bottlenecks (500x slower) even on relatively short strings if called frequently. Always check conditions that obviate the need for regex (like string length) *before* executing the regex.
**Action:** In performance-critical string processing, order operations by cost: simple length checks -> compiled regex -> complex logic.

**Learning:** `truncate_output`'s context expansion logic (`truncate_output.py`) naively expands to newlines. If input lacks frequent newlines (e.g., long single-line output), it expands to the full string, effectively negating truncation and potentially duplicating content.
**Action:** When implementing context-aware truncation, implement hard limits on context expansion to prevent "truncation" from actually increasing output size.
