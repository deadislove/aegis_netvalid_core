# 🔌 Engine Development Guide

Aegis NetValid Core is built on a "plug-and-play" philosophy. This guide explains how to develop a new engine and wire it into the running application — using the real interface every existing engine (`IDSEngine`, `SimulatorEngine`, `StresserEngine`, `MonitorEngine`, `NetworkServiceEngine`, `SoCGuardianEngine`) actually implements.

## 📋 The Engine Lifecycle
Every engine runs on its own **daemon thread** (not a separate OS process — see [Architecture](architecture.md) for why), and goes through:
1. **Construction**: `__init__` reads its slice of the app config and does any one-time setup.
2. **`start()`**: Spawns the engine's background thread and returns immediately (non-blocking).
3. **Reporting**: `get_report()` is polled on demand by `DataAggregator` — engines don't push data anywhere themselves.
4. **`stop()`**: Signals the background thread to exit.

---

## 🛠️ Step 1: Define the Engine Class
Create a new directory under `engines/your_engine_name/`. Every engine implements the same four methods, matching this real constructor signature (from `engines/wifi_monitor/monitor_engine.py`):

```python
class YourEngine:
    def __init__(self, core: AegisCore, config: dict):
        self.core = core
        # `config` is the FULL app config dict, not just your section - pull
        # out your own slice, same convention every engine follows:
        self.config = config.get("your_engine_name", {})
        self.is_running = False
        self.stats = {}  # whatever your engine measures

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.core.aegis_log("Your Engine started.", "YOUR_ENGINE")

    def stop(self):
        self.is_running = False

    def get_report(self) -> dict:
        """Polled by DataAggregator every dashboard refresh - keep it cheap."""
        return self.stats
```

Notes on things that trip people up here:
- It's `get_report()`, not `get_status()`. `DataAggregator.collect_all_metrics()` checks `hasattr(engine, "get_report")` specifically.
- There's no `data_queue` / `multiprocessing.Queue` to push to. Data flows by the Aggregator *pulling* `get_report()` from every engine each dashboard tick (`core/data_aggregator.py`).
- If your engine's monitor loop mutates `self.stats` from a background thread while `get_report()` reads it from the main thread, protect it with a `threading.Lock` (see `NetworkServiceEngine` for the pattern) — the Aggregator will call `get_report()` concurrently with your loop running.

---

## 🧪 Step 2: Implementation Example (real, working code)
`engines/wifi_monitor/monitor_engine.py` is a good minimal reference — no external hardware/library dependency beyond OS-provided CLI tools, and it already handles Windows/macOS/Linux:

```python
class MonitorEngine:
    def __init__(self, core, config):
        self.core = core
        self.config = config
        self.is_running = False
        self.os_type = platform.system()
        self.stats = {"rssi": 0, "ssid": "N/A"}
        self.lock = threading.Lock()

    def _monitor_loop(self):
        while self.is_running:
            match(self.os_type):
                case "Darwin":
                    self._get_macos_metrics()
                case "Linux":
                    self._get_linux_metrics()
                case "Windows":
                    self._get_window_metrics()
            time.sleep(self.config.get("interval", 2))

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def get_report(self):
        with self.lock:
            return self.stats.copy()
```

---

## 🔗 Step 3: Registration (both steps are required)
Registering an engine is **two separate steps** — missing the second one is a real bug this project shipped with (`NetService`/`SoC` were constructed but never started until it was fixed), so it's worth being explicit:

1.  **Construct it** — add it to `_init_engines()` in `main_aegis.py`:
    ```python
    def _init_engines(self):
        return {
            "IDS": IDSEngine(self.core, config=self.config),
            # ...existing engines...
            "YourEngine": YourEngine(self.core, self.config),
        }
    ```

2.  **Start it** — add its dict key to `priority_order` in `Orchestrator.start_all()` (`core/orchestrator.py`):
    ```python
    priority_order = ["WiFi", "NetService", "SoC", "IDS", "Simulator", "Stresser", "YourEngine"]
    ```
    An engine that's in `self.engines` but **not** in `priority_order` is constructed, shown on the dashboard, and reports `is_running = False` (i.e. `DOWN`) forever — `start()` is simply never called on it. There is no separate `register_engine()` method; the dict key is the only wiring.

3.  **(Optional) Add a dashboard row** in `AegisCLI.make_dashboard()` (`main_aegis.py`) if you want it visible in the TUI — pull your engine's fields out of `data_snapshot["engines"]["YourEngine"]`.

---

## 🛡️ Best Practices
- **Error handling**: wrap your `_monitor_loop`'s per-iteration work in `try/except` so one bad reading doesn't kill the whole background thread silently (a dead thread still reports `is_running = True` since nothing resets that flag on an unhandled exception — the row will look "OK" while quietly reporting stale data).
- **Cross-platform**: if you're shelling out to a system command, use argument lists (`subprocess.check_output([...])`), not `shell=True` — see `lib/os_helpers.py` for the pattern used elsewhere in this codebase.
- **Resource cleanup**: release sockets/handles in `stop()`.
- **Keep `get_report()` cheap**: it's called on every dashboard refresh (5 times/second) plus every Cloud sync — don't do I/O in it, only return already-computed state.
