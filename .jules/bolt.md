## 2024-05-22 - [Heavy Init Dependencies Block Isolation]
**Learning:** `interpreter/__init__.py` imports heavyweight dependencies (like `shortuuid` via `AsyncInterpreter`) which may be missing in test environments. This makes `from interpreter.core.utils import X` fail even if `X` has no dependencies.
**Action:** Use `importlib` to load internal modules by file path when writing isolated unit tests or benchmarks, bypassing the package initialization.
