## 2025-05-15 - Regex Performance in Hot Paths
**Learning:** Performing regex searches (even simple ones) on every output chunk before checking if truncation is even necessary caused significant overhead (~300ms vs ~2ms for 10k calls).
**Action:** Always check conditions that would obviate the need for expensive operations (like regex) first. Pre-compile regexes at module level.
