import subprocess
import threading
import re
import random
import time

from core.aegis_core import AegisCore

class StresserEngine:
    def __init__(self, core:AegisCore, config):
        """
        config sample:
        {
            "target_ip": "192.168.0.1",
            "duration": 60,
            "bandwidth": "100M", # Limit test bandwidth
            "parallel": 4        # Number of parallel streams
        }
        """
        self.core = core
        self.config = config.get("stresser", {})
        self.demo_mode = config.get("demo_mode", False)
        self.is_running = False
        self.process = None
        self.demo_thread = None
        self.stats = {
            "current_mbps": 0.0,
            "total_bytes_sent": 0,
            "error_count": 0,
            # UDP-only (-u); stays at default until the final summary line
            "jitter_ms": 0.0,
            "packet_loss_pct": 0.0,
            "lost_packets": 0,
            "total_packets": 0,
            "demo": False,
        }
        self.lock = threading.Lock()

    def _read_output(self):
        """
        Real-time parsing of iperf3's standard output (Text Mode)
        """
        #print("[⚡ Stresser] Monitoring iperf3 output...")
        self.core.aegis_log("[⚡ Stresser] Monitoring iperf3 output...", "traffic stresser")
    
        pattern = re.compile(r"(\d+\.?\d*)\s+Mbits/sec")
        # Final "receiver" summary line (UDP only), e.g.:
        # [  5]   0.00-2.00 sec  1.20 MBytes  5.02 Mbits/sec  0.031 ms  0/77 (0%)  receiver
        loss_pattern = re.compile(r"([\d.]+)\s+ms\s+(\d+)/(\d+)\s+\(([\d.]+)%\)")

        while self.is_running and self.process:
            line = self.process.stdout.readline()
            if not line:
                break

            line_str = line.decode('utf-8').strip()

            if "Mbits/sec" not in line_str:
                continue

            if "sender" not in line_str and "receiver" not in line_str:
                match = pattern.search(line_str)
                if match:
                    try:
                        current_val = float(match.group(1))

                        if "parallel" in self.config and self.config["parallel"] > 1:
                            if "[SUM]" in line_str:
                                with self.lock:
                                    self.stats["current_mbps"] = current_val
                        else:
                            with self.lock:
                                self.stats["current_mbps"] = current_val

                    except ValueError:
                        pass
            elif "receiver" in line_str:
                # receiver-side loss stats are authoritative, not sender-side
                loss_match = loss_pattern.search(line_str)
                if loss_match:
                    try:
                        with self.lock:
                            self.stats["jitter_ms"] = float(loss_match.group(1))
                            self.stats["lost_packets"] = int(loss_match.group(2))
                            self.stats["total_packets"] = int(loss_match.group(3))
                            self.stats["packet_loss_pct"] = float(loss_match.group(4))
                    except ValueError:
                        pass

    def start(self):
        if self.demo_mode:
            self._start_demo()
            return

        target = self.config.get("target_ip", "127.0.0.1")
        duration = self.config.get("duration", 10)
        bw = self.config.get("bandwidth", "50M")
        parallel = self.config.get("parallel", 1)

        cmd = [
            "iperf3", "-c", target, 
            "-t", str(duration), 
            "-b", bw, 
            "-P", str(parallel),
            "-i", "1",
        ]

        if self.config.get("packet_type") == "UDP":
            cmd.append("-u")

        try:
            self.is_running = True
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                bufsize=1
            )
            
            # Start listening thread
            self.monitor_thread = threading.Thread(target=self._read_output)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            #print(f"[⚡ Stresser] Stress test started against {target} ({bw})")
            self.core.aegis_log(f"[⚡ Stresser] Stress test started against {target} ({bw})", "traffic stresser")
            
        except FileNotFoundError:
            #print("[❌ Error] iperf3 is not installed on this system.")
            self.core.aegis_log("[❌ Error] iperf3 is not installed on this system.", "traffic stresser")
            self.is_running = False

    def _start_demo(self):
        target = self.config.get("target_ip", "127.0.0.1")
        self.is_running = True
        with self.lock:
            self.stats["demo"] = True
        self.core.aegis_log(f"[⚡ Stresser] Demo mode: simulating traffic against {target} (no packets sent, iperf3 not required)", "traffic stresser")
        self.demo_thread = threading.Thread(target=self._demo_loop, daemon=True)
        self.demo_thread.start()

    def _demo_loop(self):
        bw_match = re.search(r"[\d.]+", self.config.get("bandwidth", "50M"))
        target_mbps = float(bw_match.group()) if bw_match else 50.0
        current = target_mbps * 0.5

        while self.is_running:
            current += random.uniform(-target_mbps * 0.15, target_mbps * 0.15)
            current = max(0.0, min(current, target_mbps))
            loss_pct = max(0.0, min(random.gauss(0.2, 0.3), 5.0))

            with self.lock:
                self.stats["current_mbps"] = round(current, 2)
                self.stats["jitter_ms"] = round(max(0.0, random.gauss(0.5, 0.2)), 3)
                self.stats["packet_loss_pct"] = round(loss_pct, 2)
                self.stats["total_packets"] += 10
                self.stats["lost_packets"] += 1 if loss_pct > 2.0 else 0

            time.sleep(1)

    def stop(self):
        """
        Stop engine
        """
        self.is_running = False
        if self.demo_mode:
            return
        if self.process:
            self.process.terminate()
            # print("[⚡ Stresser] iperf3 process terminated.")
            self.core.aegis_log("[⚡ Stresser] iperf3 process terminated.", "traffic stresser")
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def get_report(self):
        with self.lock:
            return self.stats