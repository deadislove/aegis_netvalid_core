import threading
import time
from .traffic_profiler import TrafficProfiler
from .anomaly_detector import AnomalyDetector
from .packet_sniffer import PacketSniffer

from core.aegis_core import AegisCore

SYSTEM_NAME = "GUARDIAN_IDS"

class IDSEngine:
    def __init__(self, core: AegisCore, config):
        self.core = core
        self.config = config.get("ids", {})
        self.profiler = TrafficProfiler(self.core, config_path=self.config.get('config_path'))
        signatures = self.profiler.config.get("threat_signatures", {})
        self.detector = AnomalyDetector(self.profiler, signatures=signatures)
        self.sniffer = None
        self.is_running = False

        self.threat_count = 0
        self.last_status = "Safe"

        self.alert_history = {}
        

    def _on_packet(self, data):
        """
        Captch the network package.
        """
        src_ip = data.get("src", "Unknown")
        self.profiler.update_profile(data)
        status, reason = self.detector.evaluate(data["src"], device_type="Unknown")

        self.last_status = status

        if status == "CRITICAL":
            # print(f"[🛡️ IDS Engine] ALERT: {reason}")
            self.threat_count +=1

            current_time = time.time()
            last_alert_time = self.alert_history.get(src_ip, 0)
            if current_time - last_alert_time > 5:
                self.core.aegis_log(f"[🛡️ IDS Engine] ALERT: {reason}", SYSTEM_NAME)
                self.alert_history[src_ip] = current_time
            # self.core.aegis_log(f"[🛡️ IDS Engine] ALERT: {reason}", SYSTEM_NAME)

    def start(self):
        """
        Start engine
        """

        if self.is_running:
            return
        
        # print("[🛡️ IDS Engine] Initializing Sniffer...")
        self.core.aegis_log("[🛡️ IDS Engine] Initializing Sniffer...", SYSTEM_NAME)
        self.sniffer = PacketSniffer(self.core, interface=self.config.get('interface'))
        self.sniffer.callback = self._on_packet
        
        self.is_running = True
        # Use Threads to avoid blocking the Aegis main process
        self.thread = threading.Thread(target=self.sniffer.start_sniffing, kwargs={'filter_str': "ip"})
        self.thread.daemon = True
        self.thread.start()
        # print("[🛡️ IDS Engine] Monitoring active.")
        self.core.aegis_log("[🛡️ IDS Engine] Monitoring active.", SYSTEM_NAME)

    def stop(self):
        """
        Stop engine
        """
        self.is_running = False
        if self.sniffer:
            self.sniffer.stop()
        # print("[🛡️ IDS Engine] Stopped.")
        self.core.aegis_log("[🛡️ IDS Engine] Stopped.")

    def get_report(self):
        status_color = "[green]NORMAL[/green]"
        if self.last_status == "CRITICAL":
            status_color = "[red]CRITICAL[/red]"
        elif self.last_status == "WARNING":
            status_color = "[yellow]WARNING[/yellow]"

        return {
            "engine": "IDS Guardian",
            "status": "MONITORING" if self.is_running else "IDLE",
            "threats": self.threat_count,
            "score": status_color
        }