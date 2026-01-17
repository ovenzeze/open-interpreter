# Bolt's Journal

## 2024-05-23 - [Regex Compilation and Early Returns]
**Learning:** Performance-critical paths involving regex should always compile patterns at the module level. Furthermore, simple length checks should precede complex logic like regex searching to allow for O(1) early returns on happy paths.
**Action:** Always check for opportunities to move lightweight checks before heavy operations and pre-compile regex patterns.
