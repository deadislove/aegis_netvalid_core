from scapy.all import sniff, IP, TCP, UDP, conf
import threading
import time
import platform

from core.aegis_core import AegisCore

SYSTEM_NAME = "GUARDIAN_IDS"

class PacketSniffer:
    def __init__(self, core: AegisCore, interface="lo"): # "lo" is the local loop, commonly used in simulation environments.
        # self.interface = interface
        self.core = core
        self.os_type = platform.system()
        if interface is None:
            self.interface = self._get_default_interface()
        else:
            self.interface = interface

        self.is_running = False
        self.packet_count = 0
        # Used to send the analysis results back to the Detector
        self.callback = None

    def _get_default_interface(self):
        if self.os_type == "Linux":
            return "eth0"
        elif self.os_type == "Darwin":
            return "en0"
        elif self.os_type == "Windows":
            return conf.iface
        return None

    def _process_packet(self, packet):
        """
        Core callback function: parses each captured packet
        """

        if not packet.haslayer(IP):
            return
        
        src_ip = packet[IP].src
        dst_ip = packet[IP].dst
        proto = "OTHER"
        size = len(packet)

        if packet.haslayer(TCP):
            proto = "TCP"
            port = packet[TCP].dport
        elif packet.haslayer(UDP):
            proto = "UDP"
            port = packet[UDP].dport

        # inital network flow data
        traffic_data = {
            "timestamp": time.time(),
            "src": src_ip,
            "dst": dst_ip,
            "proto": proto,
            "port": port if 'port' in locals() else None,
            "size": size
        }
        
        # Trigger analysis logic (if a callback has been registered)
        if self.callback:
            self.callback(traffic_data)
        
        self.packet_count += 1

    def start_sniffing(self, filter_str="ip"):
        """
        Start background listening thread
        filter_str: Use BPF syntax (e.g., "tcp and port 80")
        """
        self.is_running = True
        # print(f"[*] Starting Guardian-IDS Sniffer on {self.interface}...")
        self.core.aegis_log(f"[*] Starting Guardian-IDS Sniffer on {self.interface}...", SYSTEM_NAME)

        current_filter = filter_str

        #checking OS
        if self.os_type == "Darwin" and self.interface == "lo0":
            # print("[!] macOS Loopback detected. Disabling BPF filter for compatibility.")
            self.core.aegis_log("[!] macOS Loopback detected. Disabling BPF filter for compatibility.", SYSTEM_NAME)
            current_filter = None

        def _sniff_thread():
            sniff(
                iface=self.interface,
                prn=self._process_packet,
                filter=current_filter,
                store=0, # It is not stored in memory to prevent long-term execution from causing an OOM (Out of Memory) error.
                stop_filter=lambda x: not self.is_running,
            )

        thread = threading.Thread(target=_sniff_thread, daemon=True)
        thread.start()

    def stop(self):
        self.is_running = False
        # print(f"[*] Sniffer stopped. Total packets captured: {self.packet_count}")
        self.core.aegis_log(f"[*] Sniffer stopped. Total packets captured: {self.packet_count}", SYSTEM_NAME)

# Test port
if __name__ == "__main__":
    sniffer = PacketSniffer()
    # Define a simple monitoring callback
    sniffer.callback = lambda d: print(f"[{d['proto']}] {d['src']} -> {d['dst']} ({d['size']} bytes)")

    sniffer.start_sniffing()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sniffer.stop()