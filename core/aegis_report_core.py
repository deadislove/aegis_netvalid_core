import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import time
import os
import threading
from .aegis_core import AegisCore
from engines.traffic_stresser.stresser_engine import StresserEngine
from engines.ids_guardian.ids_engine import IDSEngine

class AegisReportCore:
    def __init__(self, core:AegisCore, stresser:StresserEngine, ids:IDSEngine):
        self._core = core
        self._stresser = stresser
        self._ids = ids

        self.history = []
        self.stop_event = threading.Event()
        self._sampler_thread = None

    def record_snapshot(self):
        snapshot = {
            "time": len(self.history),
            "mbps": self._stresser.stats.get("current_mbps", 0),
            "threats": self._ids.threat_count
        }
        self.history.append(snapshot)

    def start_auto_sampling(self, interval = 1):
        def _loop():
            while not self.stop_event.is_set():
                self.record_snapshot()
                time.sleep(interval)
        
        self._sampler_thread = threading.Thread(target=_loop, daemon=True)
        self._sampler_thread.start()

    def generate_visual_report(self, stats_history = None):
        """
            stats_history: example [{'time': 1, 'mbps': 45.2}, {'time': 2, 'mbps': 48.1}, ...]
        """

        if stats_history:
            self.history = stats_history

        report_dir = f"outputs/reports/report_{int(time.time())}"
        os.makedirs(report_dir, exist_ok=True)

        # 1. Draw a bandwidth trend chart.
        times = [x['time'] for x in self.history]
        mbps = [x['mbps'] for x in self.history]
        threats = [x['threats'] for x in self.history]

        plt.figure(figsize=(10, 6))

        # Draw Mbps
        plt.subplot(2, 1, 1)
        plt.plot(times, mbps, color='#00aaff', linewidth=2, label="Bandwidth (Mbps)")
        plt.fill_between(times, mbps, color='#00aaff', alpha=0.3)
        plt.title("Network Performance & Security Analysis")
        plt.ylabel("Mbps")
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()

        # Drawing cumulative threat numbers
        plt.subplot(2, 1, 2)
        plt.step(times, threats, color='#ff4444', linewidth=2, label="Total Threats")
        plt.ylabel("Threat Count")
        plt.xlabel("Test Duration (s)")
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()

        chart_path = f"{report_dir}/bandwidth_chart.png"
        plt.savefig(chart_path)
        plt.close()

        # 2. Produce a Markdown summary report.
        report_md = f"""
# Aegis NetValid Test Report
**Generated Time**: {time.strftime("%Y-%m-%d %H:%M:%S")}
**Gateway**: {self._core.config.get('gateway_ip', 'Unknown')}

## 1. Traffic Statistics Charts
![Bandwidth Chart](bandwidth_chart.png)

## 2. Threat Detection Summary
- **Final Threat Count**: {self._ids.threat_count}
- **Current Security Status**: {getattr(self._ids, 'last_status', 'N/A')}

## 3. System Statistics
- **Total Samples Collected**: {len(self.history)}
- **Peak Bandwidth**: {max(mbps) if mbps else 0} Mbps
"""
        
#         if hasattr(self._core, 'simulator_engine'):
#             sim = self._core.simulator_engine
#             report_md += f"""
# ## 4. IoT Simulation Details
# - **Active Devices**: {len(sim.active_devices)}
# - **Total Packets Sent**: {sim.stats.get('total_sent', 0)}
# """

        with open(f"{report_dir}/summary.md", "w", encoding="utf-8") as f:
            f.write(report_md)

        with open(f"{report_dir}/data.json", "w") as f:
            json.dump(self.history, f, indent=4)

        # self._core.aegis_log(f"📊 Report generated at: {report_dir}", "SYSTEM")

        # Automatically return permissions to regular users.
        try:
            real_uid = int(os.environ.get('SUDO_UID', os.getuid()))
            real_gid = int(os.environ.get('SUDO_GID', os.getgid()))

            for root, dirs, files in os.walk(report_dir):
                for momo in dirs + files:
                    os.chown(os.path.join(root, momo), real_uid, real_gid)

            os.chown(report_dir, real_uid, real_gid)
        except Exception as e:
            self._core.aegis_log(f"⚠️ Failed to fix permissions: {e}", "SYSTEM")

        self._core.aegis_log(f"📊 Report generated at: {report_dir}", "SYSTEM")