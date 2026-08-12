import time
import socket
import subprocess
import threading
import platform
import re
from core.aegis_core import AegisCore

class NetworkServiceEngine:
    def __init__(self, core: AegisCore, config: dict):
        self.core = core
        self.config = config.get("network_service", {})
        # NOTE: gateway_ip lives at the root of the app config (set by
        # AegisCLI's gateway detection), not under "network_service" - read
        # it from there, same convention SimulatorEngine already uses. This
        # also lets AegisCLI.update_config_cmd's existing
        # `if hasattr(engine, 'gateway_ip')` live-update hook reach this
        # engine when the user runs `set gateway_ip ...`.
        self.gateway_ip = config.get("gateway_ip", "192.168.0.1")
        self.target_ip = config.get("stresser", {}).get("target_ip")
        self.is_running = False
        self.stats = {
            "dns_latency": 0,
            "dhcp_status": "Unknown",
            "gateway_reachable": False,
            "gateway_rtt_ms": None,
            "target_rtt_ms": None,
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

    def _ping(self, host, timeout_s=1):
        """
        Sends a single ICMP echo and returns the round-trip time in ms,
        or None if there was no reply (host unreachable / ping unavailable).
        """
        if not host:
            return None

        os_type = platform.system()
        try:
            if os_type == "Windows":
                cmd = ["ping", "-n", "1", "-w", str(int(timeout_s * 1000)), host]
            elif os_type == "Darwin":
                # -W is milliseconds on macOS
                cmd = ["ping", "-c", "1", "-W", str(int(timeout_s * 1000)), host]
            else:
                # -W is seconds on Linux (iputils)
                cmd = ["ping", "-c", "1", "-W", str(timeout_s), host]

            output = subprocess.check_output(cmd, timeout=timeout_s + 2).decode(errors="replace")
        except Exception:
            return None

        match = re.search(r"time[=<]\s*([\d.]+)\s*ms", output)
        return float(match.group(1)) if match else None

    def _check_gateway(self):
        return self._ping(self.gateway_ip)

    def _check_target(self):
        return self._ping(self.target_ip) if self.target_ip else None

    def _monitor_loop(self):
        while self.is_running:
            dns_res = self._check_dns()
            gw_rtt = self._check_gateway()
            target_rtt = self._check_target()
            routes = self._check_routes()

            with self.lock:
                self.stats["dns_latency"] = dns_res
                self.stats["gateway_reachable"] = gw_rtt is not None
                self.stats["gateway_rtt_ms"] = gw_rtt
                self.stats["target_rtt_ms"] = target_rtt
                self.stats["route_count"] = routes
                # Can be extended to monitor dhcpcd/NetworkManager status
                self.stats["dhcp_status"] = "Bound" if gw_rtt is not None else "Searching"

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
            gw_rtt = self.stats["gateway_rtt_ms"]
            target_rtt = self.stats["target_rtt_ms"]
            return {
                "dns_ms": f"{self.stats['dns_latency']:.2f}" if self.stats['dns_latency'] > 0 else "ERR",
                "dhcp": self.stats["dhcp_status"],
                "gw_link": "UP" if self.stats["gateway_reachable"] else "DOWN",
                "gw_rtt_ms": f"{gw_rtt:.2f}" if gw_rtt is not None else "N/A",
                "target_rtt_ms": f"{target_rtt:.2f}" if target_rtt is not None else "N/A",
                "routes": self.stats["route_count"]
            }