import time
import yaml
from collections import defaultdict

from core.aegis_core import AegisCore

SYSTEM_NAME = "GUARDIAN_IDS"

class TrafficProfiler:
    def __init__(self, core: AegisCore, config_path='config/ids_settings.yaml'):
        self.core = core
        self.device_stats = defaultdict(lambda: {
            "bytes_sent": 0, 
            "packet_count": 0,
            "first_seen": time.time(),
            "last_seen": time.time(),
            "ports_seen": set(),
            "flow_history": []
        })

        self.config = self._load_config(config_path)
        self.thresholds = self.config.get("device_profiles", {})

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            # print(f"[!] Load config failed: {e}. Using default.")
            self.core.aegis_log(f"[!] Load config failed: {e}. Using default.", SYSTEM_NAME)
            return {}
        
    def update_profile(self, traffic_data):
        """
        Receive data from the Sniffer and update statistics
        """

        src_ip = traffic_data["src"]
        size = traffic_data["size"]
        dst_port = traffic_data.get("dport", 0)
        now = traffic_data["timestamp"]

        stats = self.device_stats[src_ip]
        stats["bytes_sent"] += size
        stats["packet_count"] += 1
        stats["last_seen"] = now

        if dst_port:
            stats["ports_seen"].add(dst_port)

        # Maintenance Sliding Windows record network size
        stats["flow_history"].append((now, size))
        if len(stats["flow_history"]) > 50:
            stats["flow_history"].pop(0)
        
    def get_recent_kbps(self, ip):
        """
        """

        stats = self.device_stats.get(ip)
        if not stats or len(stats["flow_history"]) < 10:
            return 0
        
        history = stats["flow_history"]
        time_delta = history[-1][0] - history[0][0]

        if time_delta < 0.001:
            return 0

        total_bytes = sum(item[1] for item in history)
        return (total_bytes * 8) / (time_delta * 1024)
    
    def check_threshold_violation(self, ip, device_type='Unknown'):

        recent_kbps = self.get_recent_kbps(ip)
        limit = self.thresholds.get(device_type, self.thresholds.get('Unknown', {"max_kbps": 100}))["max_kbps"]

        if recent_kbps > limit:
            return True, f"🔥 ABNORMAL TRAFFIC: {recent_kbps:.2f} Kbps > Limit {limit}"
        return False, "Normal"