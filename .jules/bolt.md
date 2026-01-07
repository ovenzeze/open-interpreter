# Bolt's Journal ⚡

## 2026-01-07 - [Optimization: Remove Busy-Wait in Wait Loop]
**Learning:** `interpreter.wait()` was using a polling loop with `time.sleep(0.2)`, causing up to 200ms of unnecessary latency and CPU wake-ups.
**Action:** Replaced busy-wait with `threading.Event()` for efficient synchronization. This allows `wait()` to return immediately when the chat is done.
