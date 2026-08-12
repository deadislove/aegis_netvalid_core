import subprocess
import threading
import re

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
        self.is_running = False
        self.process = None
        self.stats = {
            "current_mbps": 0.0,
            "total_bytes_sent": 0,
            "error_count": 0,
            # Only populated for UDP tests (-u): iperf3 only reports jitter
            # and loss in the final "receiver" summary line, not per-interval,
            # so these stay at their default until the test/interval ends.
            "jitter_ms": 0.0,
            "packet_loss_pct": 0.0,
            "lost_packets": 0,
            "total_packets": 0,
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
                # Receiver-side stats are authoritative for loss: the sender
                # can't know a packet was dropped in transit.
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

    def stop(self):
        """
        Stop engine
        """
        self.is_running = False
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