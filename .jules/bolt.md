## 2025-05-15 - Optimize Truncate Output
**Learning:** Checking simple conditions (like string length) before expensive operations (like regex searching) can yield massive performance gains (20x+) for common paths.
**Action:** Always verify if an expensive operation is strictly necessary before executing it. Pre-compile regex patterns at the module level when used frequently.
