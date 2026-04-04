import threading
import time
import random
from scapy.all import IP, UDP, TCP, Raw, Ether, send, getmacbyip, L3RawSocket, conf
from core.aegis_core import AegisCore

SYSTEM_NAME = "IOT_SIMULATOR"

class SimulatorEngine:
    def __init__(self, core:AegisCore, config):
        """
        config sample:
        {
            "default_device_count": 10,
            "scan_interval": 5
        }
        """
        self.core = core
        self.config = config.get("simulator",{})
        self.active_devices = []
        self.is_running = False
        self.lock = threading.Lock()

        self.gateway_ip = config.get("gateway_ip", "192.168.0.1")
        self.gateway_mac = getmacbyip((self.gateway_ip))

        self.stats = {
            "total_sent": 0,
            "device_metrics": {}
        }
        try:
            self.socket = conf.L3socket() 
        except Exception as e:
            self.core.aegis_log(f"[❌ Simulator] Socket Error: {e}", "SYSTEM")
            self.socket = None

    def _generate_random_mac(self):
        """
        Generate a fake MAC address
        """

        return "02:%02x:%02x:%02x:%02x:%02x" % (
            random.randint(0, 255), random.randint(0, 255),
            random.randint(0, 255), random.randint(0, 255),
            random.randint(0, 255)
        )

    def send_packet(self, device_info):
        src_ip = device_info["id"]
        # src_mac = device_info["mac"]
        device_type = device_info["type"]
        
        dst_ip = self.gateway_ip

        # Building the L2/L3 layer
        #base_pkt = Ether(src=src_mac, dst="ff:ff:ff:ff:ff:ff") / IP(src=src_ip, dst=dst_ip)
        base_pkt = IP(src=src_ip, dst=dst_ip)
        match(device_type):
            case "LightBulb":
                payload = f"status: on, brightness: 80%, ip: {src_ip}"
                pkt = base_pkt / TCP(dport=1883) / Raw(load=payload)
            case "IPCamera":
                payload = "X" * 1024
                pkt = base_pkt/ UDP(dport=5004) / Raw(load=payload)
            case "DDoS_Attacker":
                pkt = base_pkt / UDP(dport=random.randint(1, 65535)) / Raw(load="ATTACK_FLUX")
            case _:
                pkt = base_pkt / UDP(dport=80) / Raw(load="Hello")
        
        #send(pkt, verbose=False)
        self.socket.send(pkt)

        with self.lock:
            self.stats["total_sent"] += 1
            if src_ip not in self.stats["device_metrics"]:
                self.stats["device_metrics"][src_ip] = {"packets": 0, "bytes": 0}
            self.stats["device_metrics"][src_ip]["packets"] += 1
            self.stats["device_metrics"][src_ip]["bytes"] += len(pkt)

    def _device_behavior_loop(self, device_info):
        """
        The behavioral logic of a single virtual device (Thread operation content)
        """
        device_id = device_info["id"]
        
        # print(f"[🏡 Simulator] Device {device_id} joined the network.")
        self.core.aegis_log(f"[🏡 Simulator] Device {device_id} joined the network.", SYSTEM_NAME)

        while self.is_running:

            try:
                current_type = device_info["type"]
                self.send_packet(device_info)

                wait_time = 5 if current_type == "LightBulb" else 0.5
                time.sleep(random.uniform(wait_time * 0.8, wait_time * 1.2))

            except Exception as e:
                # print(f"[!] Device {device_id} error: {e}")
                self.core.aegis_log(f"[!] Device {device_id} error: {e}", SYSTEM_NAME)
                break

            time.sleep(random.uniform(2, 10))

        # print(f"[🏡 Simulator] Device {device_id} offline.")
        self.core.aegis_log(f"[🏡 Simulator] Device {device_id} offline.", SYSTEM_NAME)

    def trigger_infection(self, ip):
        """
        Remote commands can mutate specific devices into attackers' devices.
        """
        with self.lock:
            for dev in self.active_devices:
                if dev["id"] == ip:
                    dev["type"] = "DDoS_Attacker"
                    # print(f"[⚠️ WARNING] Device {ip} has been INFECTED!")
                    self.core.aegis_log(f"[⚠️ WARNING] Device {ip} has been INFECTED!", SYSTEM_NAME)

    def spawn_devices(self, count, device_type="LightBulb"):
        """
        Dynamically increase the number of devices
        """
        with self.lock:
            for _ in range(count):
                device_id = f"192.168.0.{len(self.active_devices) + 101}"
                device_info = {
                    "id": device_id, 
                    #"mac": self._generate_random_mac(),
                    "type": device_type
                }
                
                t = threading.Thread(target=self._device_behavior_loop, args=(device_info,))
                t.daemon = True
                t.start()
                
                device_info["thread"] = t
                self.active_devices.append(device_info)
            # print(f"[🏡 Simulator] Spawned {count} new {device_type}s.")
            self.core.aegis_log(f"[🏡 Simulator] Spawned {count} new {device_type}s.", SYSTEM_NAME)

    def start(self):
        """
        Start the engine: First, establish the initial number of devices.
        """
        self.is_running = True
        initial_count = self.config.get("default_device_count", 5)
        self.spawn_devices(initial_count)
        # print(f"[🏡 Simulator] Engine started with {initial_count} devices.")
        self.core.aegis_log(f"[🏡 Simulator] Engine started with {initial_count} devices.", SYSTEM_NAME)

    def stop(self):
        """
        Stop engine: Notify all threads to terminate.
        """
        self.is_running = False
        # print("[🏡 Simulator] Shutting down all virtual devices...")
        self.core.aegis_log("[🏡 Simulator] Shutting down all virtual devices...", SYSTEM_NAME)
        self.active_devices = []

    def get_report(self):
        report = self.stats.copy()
        report["active_devices"] = len(self.active_devices)
        return report