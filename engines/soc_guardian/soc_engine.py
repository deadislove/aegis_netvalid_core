import os
import threading
import time
from core.aegis_core import AegisCore

class SoCGuardianEngine:
    """
    Focused on Embedded Linux & SoC Health during Bring-up.
    Monitors Thermal, CPU scaling, and GPIO states.
    """
    def __init__(self, core: AegisCore, config: dict):
        self.core = core
        self.config = config.get("soc_guardian", {})
        self.is_running = False
        self.stats = {
            "temp": 0.0,
            "load": "0.0 0.0 0.0",
            "throttled": False,
            "poe_status": "N/A"
        }
        self.lock = threading.Lock()

    def _get_thermal(self):
        # Standard Linux thermal zone path
        # Allow override from config for different SoC vendors
        thermal_path = self.config.get("thermal_path", "/sys/class/thermal/thermal_zone0/temp")
        if os.path.exists(thermal_path):
            try:
                with open(thermal_path, "r") as f:
                    return int(f.read().strip()) / 1000.0
            except (IOError, ValueError, PermissionError) as e:
                self.core.aegis_log(f"Thermal read error: {e}", "SoC")
        return -1.0

    def _get_cpu_load(self):
        try:
            if os.path.exists("/proc/loadavg"):
                with open("/proc/loadavg", "r") as f:
                    return " ".join(f.read().split()[:3]) or "N/A"
        except Exception as e:
            self.core.aegis_log(f"Error reading CPU load: {e}", "SoC")
        return "N/A"

    def _check_poe(self):
        # Placeholder for PoE monitoring via I2C or specific driver sysfs
        # Example: reading from a PMIC or PSE controller
        return "Normal (54V)" if self.config.get("monitor_poe", False) else "Disabled"

    def _monitor_loop(self):
        while self.is_running:
            temp = self._get_thermal()
            load = self._get_cpu_load()
            poe = self._check_poe()

            with self.lock:
                self.stats["temp"] = temp
                self.stats["load"] = load
                self.stats["poe_status"] = poe
                # Simple logic for SoC Throttling detection
                if temp > 85.0:
                    self.stats["throttled"] = True
                    self.core.aegis_log(f"⚠️ SoC Thermal Throttling detected: {temp}°C", "SoC")
                else:
                    self.stats["throttled"] = False

            time.sleep(self.config.get("interval", 2))

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.core.aegis_log("SoC Guardian Engine started.", "SoC")

    def stop(self):
        self.is_running = False

    def get_report(self):
        with self.lock:
            status = "🔥 HOT" if self.stats["throttled"] else "COLD"
            return {
                "temp": f"{self.stats['temp']}°C",
                "load": self.stats["load"],
                "status": status,
                "poe": self.stats["poe_status"]
            }
