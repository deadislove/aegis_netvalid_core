import subprocess
import threading
import time
import re
import platform

from core.aegis_core import AegisCore

class MonitorEngine:
    def __init__(self, core:AegisCore, config):
        self.core = core
        self.config = config
        self.is_running = False
        self.os_type = platform.system()
        self.stats = {
            "rssi": 0,
            "noise": -95,
            "snr": 0, # Signal-to-Noise Ratio
            "tx_rate": 0.0,
            "interface": config.get("interface", "wlan0"),
            "ssid": "N/A"
        }
        self.lock = threading.Lock()

    def _get_linux_metrics(self):
        """
        Analyzing Linux's /proc/net/wireless or iwconfig
        """
        try:
            cmd = ["iwconfig", self.stats["interface"]]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')

            rssi_match = re.search(r"Signal level=(-?\d+)", output)
            rate_match = re.search(r"Bit Rate[:=](\d+\.?\d*)", output)
            ssid_match = re.search(r'ESSID:"([^"]+)"', output)

            with self.lock:
                if rssi_match:
                    self.stats["rssi"] = int(rssi_match.group(1))
                if rate_match:
                    self.stats["tx_rate"] = float(rate_match.group(1))
                if ssid_match:
                    self.stats["ssid"] = ssid_match.group(1)
                self.stats["snr"] = self.stats["rssi"] - self.stats["noise"]

        except Exception:
            try:
                with open("/proc/net/wireless", "r") as f:
                    lines = f.readlines()
                    if len(lines) > 2:
                        parts = lines[2].split()
                        # The indicators are usually in columns 3 and 4 (level, noise).
                        rssi = int(parts[3].replace(".", ""))
                        with self.lock:
                            self.stats["rssi"] = rssi
            except Exception:
                pass

    def _get_macos_metrics(self):
        """
        Parsing the airport tool for macOS
        """
        try:
            metrics_cmd = "system_profiler SPAirPortDataType"
            output = subprocess.check_output(metrics_cmd, shell=True).decode('utf-8')
        
            combined_match = re.search(r"Signal / Noise:\s+(-?\d+)\s+dBm\s+/\s+(-?\d+)\s+dBm", output)
            rssi_match = re.search(r"RSSI:\s+(-?\d+)", output)
            noise_match = re.search(r"Noise:\s+(-?\d+)", output)
            rate_match = re.search(r"Last Tx Rate:\s+(\d+)", output)
            ssid_match = re.search(r"Current Network Information:\s+(.+?):", output, re.S)
            if not ssid_match:
                ssid_match = re.search(r"SSID:\s+(.+)", output)

            with self.lock:
                if combined_match:
                    self.stats["rssi"] = int(combined_match.group(1))
                    self.stats["noise"] = int(combined_match.group(2))
                else:
                    if rssi_match:
                        self.stats["rssi"] = int(rssi_match.group(1))
                    if noise_match:
                        self.stats["noise"] = int(noise_match.group(1))
                if rate_match:
                    self.stats["tx_rate"] = float(rate_match.group(1))
                if ssid_match:
                    name = ssid_match.group(1).strip()
                    self.stats["ssid"] = "Hidden (Location Privacy)" if "<redacted>" in name else name

                if self.stats["rssi"] != 0:
                    self.stats["snr"] = self.stats["rssi"] - self.stats["noise"]
        except Exception:
            pass

    def _get_window_metrics(self):
        """
        Parsing Windows netsh wlan show interfaces
        """
        try:
            output = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], 
                                                 creationflags=subprocess.CREATE_NO_WINDOW if self.os_type == "Windows" else 0).decode('cp950', errors='ignore')

            signal_match = re.search(r"Signal\s*:\s*(\d+)%", output)
            rate_match = re.search(r"Receive rate\s*\(Mbps\)\s*:\s*(\d+)", output)
            ssid_match = re.search(r"SSID\s*:\s*(.*)", output)

            with self.lock:
                if signal_match:
                    percent = int(signal_match.group(1))
                    self.stats["rssi"] = (percent / 2) - 100
                if rate_match:
                    self.stats["tx_rate"] = float(rate_match.group(1))
                if ssid_match:
                    self.stats["ssid"] = ssid_match.group(1).strip()
                # Windows is not easy to obtain. Noise and SNR are calculated based on empirical values.
                self.stats["snr"] = self.stats["rssi"] - (-95)
        except Exception:
            pass
    
    def _monitor_loop(self):
        # print(f"[📡 Monitor] WiFi thread active on {self.os_type}")
        self.core.aegis_log("f[📡 Monitor] WiFi thread active on {self.os_type}", "wifi_monitor")
        while self.is_running:
            match(self.os_type):
                case "Windows":
                    self._get_window_metrics()
                case "Darwin":
                    self._get_macos_metrics()
                case "Linux":
                    self._get_linux_metrics()

            time.sleep(self.config.get("interval", 2))

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        # print(f"[📡 Monitor] WiFi Monitoring started on {self.os_type}")
        self.core.aegis_log(f"[📡 Monitor] WiFi Monitoring started on {self.os_type}", "wifi_monitor")

    def stop(self):
        self.is_running = False

    def get_report(self):
        with self.lock:
            return self.stats.copy()