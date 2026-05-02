import time
import socket
import subprocess
import threading
from core.aegis_core import AegisCore

class NetworkServiceEngine:
    def __init__(self, core: AegisCore, config: dict):
        self.core = core
        self.config = config.get("network_service", {})
        self.is_running = False
        self.stats = {
            "dns_latency": 0,
            "dhcp_status": "Unknown",
            "gateway_reachable": False,
            "route_count": 0
        }
        self.lock = threading.Lock()

    def _check_routes(self):
        """Verify Routing Table (Networking Fundamentals)"""
        try:
            # Parse /proc/net/route or use 'ip route'
            output = subprocess.check_output(["ip", "route", "show"], timeout=2).decode()
            return len(output.strip().split('\n'))
        except Exception:
            return 0

    def _check_dns(self):
        start = time.time()
        try:
            # Specifically testing DNS resolution
            socket.gethostbyname("google.com")
            return (time.time() - start) * 1000
        except Exception:
            return -1

    def _check_gateway(self):
        gw = self.config.get("gateway_ip", "192.168.0.1")
        try:
            # Simple ping check
            subprocess.check_output(["ping", "-c", "1", "-W", "1", gw], timeout=2)
            return True
        except Exception:
            return False

    def _monitor_loop(self):
        while self.is_running:
            dns_res = self._check_dns()
            gw_res = self._check_gateway()
            routes = self._check_routes()
            
            with self.lock:
                self.stats["dns_latency"] = dns_res
                self.stats["gateway_reachable"] = gw_res
                self.stats["route_count"] = routes
                # Can be extended to monitor dhcpcd/NetworkManager status
                self.stats["dhcp_status"] = "Bound" if gw_res else "Searching"
            
            time.sleep(self.config.get("interval", 5))

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.core.aegis_log("Network Service Engine started.", "NET_SVC")

    def stop(self):
        self.is_running = False

    def get_report(self):
        with self.lock:
            return {
                "dns_ms": f"{self.stats['dns_latency']:.2f}" if self.stats['dns_latency'] > 0 else "ERR",
                "dhcp": self.stats["dhcp_status"],
                "gw_link": "UP" if self.stats["gateway_reachable"] else "DOWN",
                "routes": self.stats["route_count"]
            }