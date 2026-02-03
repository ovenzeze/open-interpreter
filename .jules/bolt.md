## 2024-05-22 - [Heavyweight Package Init]
**Learning:** `interpreter/__init__.py` imports `AsyncInterpreter` which imports `shortuuid` and other dependencies. This makes it impossible to import submodules (like `interpreter.core.utils`) in isolation for unit testing without having the full environment set up.
**Action:** When testing utility modules in `interpreter/`, either use `importlib` to bypass package initialization or mock the dependencies if running within the package structure.
