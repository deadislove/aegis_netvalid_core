import time
import threading
import os
import json
import subprocess
import platform
import re
import sys
import argparse
import logging
import yaml
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from scapy.all import conf

from engines.ids_guardian.ids_engine import IDSEngine
from engines.iot_simulator.simulator_engine import SimulatorEngine
from engines.traffic_stresser.stresser_engine import StresserEngine
from engines.wifi_monitor.monitor_engine import MonitorEngine
from engines.network_service.service_engine import NetworkServiceEngine
from engines.soc_guardian.soc_engine import SoCGuardianEngine

from core.aegis_core import AegisCore
from core.cloud_validator import CloudValidator
from core.aegis_report_core import AegisReportCore
from core.orchestrator import Orchestrator
from core.data_aggregator import DataAggregator

sys.stderr = open(os.devnull, 'w')
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
conf.verb = 0

console = Console()
TEMP_DIR = "temp"
LAST_CONFIG_FILE = os.path.join(TEMP_DIR, "last_config.json")

class AegisCLI:
    def __init__(self):
        self.args = self._parse_args()
        self.os_type = platform.system()
        self.running = True
        self._setup_config()
        self.core = AegisCore(self.config)

        # initial engines
        self.engines = self._init_engines()
        
        # Initialize core controllers
        self.orchestrator = Orchestrator(self.core, self.engines)
        self.data_aggregator = DataAggregator(self.engines)
        
        # Initialize Cloud Validator
        try:
            self.cloud_validator = CloudValidator(self.core, self.config)
        except Exception as e:
            self.core.aegis_log(f"CloudValidator failed to load: {e}", "System")
            self.cloud_validator = None
        self.last_cloud_sync = 0

        # Initialize report manager
        self.report_manager = AegisReportCore(
            self.core, 
            self.engines["Stresser"], 
            self.engines["IDS"]
        )

    def _parse_args(self):
        parser = argparse.ArgumentParser(description="Aegis NetValid Core - Network Security & Stress Tool")
        parser.add_argument("--gateway", help="Override Gateway IP")
        parser.add_argument("--interface", help="Override Network Interface")
        parser.add_argument("--target", help="Override Stresser Target IP")
        parser.add_argument("--dev-count", type=int, help="Default IoT device count")
        return parser.parse_args()

    def _setup_config(self):
        """
        Integrating file configuration and command line parameters
        """
        base_config = self._load_initial_config()
        
        # Use CLI parameters to override persistent configuration
        if self.args.gateway:
            base_config["gateway_ip"] = self.args.gateway
        if self.args.interface:
            base_config["interface"] = self.args.interface
            base_config["ids"]["interface"] = self.args.interface
        if self.args.target:
            base_config["stresser"]["target_ip"] = self.args.target
        if self.args.dev_count:
            base_config["default_device_count"] = self.args.dev_count
            base_config["simulator"]["device_count"] = self.args.dev_count

        self.config = base_config

    def show_help(self):
        """
        Display instruction description table
        """
        help_table = Table(title="Available Commands", box=None)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")
        
        help_table.add_row("help", "Show this help menu")
        help_table.add_row("set <path> <val>", "Update config (e.g., set ids.rules.threat_signatures.PORT_SCAN.min_ports 50)")
        help_table.add_row("set cloud.enabled true/false", "Enable or disable AWS CloudWatch synchronization")
        help_table.add_row("stress start/stop", "Control the traffic stresser engine")
        help_table.add_row("spawn", "Spawn 5 more simulated IoT devices")
        help_table.add_row("infect <IP>", "Trigger infection simulation on target IP")
        help_table.add_row("back / exit", "Return to the real-time dashboard")
        help_table.add_row("quit", "Shut down Aegis and exit")
        console.print(help_table)

    def _get_default_gateway(self):
        try:
            match(self.os_type):
                case "Windows":
                    raw_out = subprocess.check_output("ipconfig", shell=True)
                    # Attempt to decode with multiple encodings to support international systems
                    out = ""
                    for enc in ['cp950', 'utf-8', 'gbk', 'cp437']:
                        try:
                            out = raw_out.decode(enc)
                            break
                        except UnicodeDecodeError: continue
                    # Support international locales by matching keywords and extracting IPv4
                    match = re.search(r"(?:Default Gateway|Gateway|預設閘道).*: ([\d\.]+)", out)
                    return match.group(1) if match else "192.168.0.1"
                case "Darwin":
                    try:
                        cmd = "system_profiler SPAirPortDataType"
                        out = subprocess.check_output(cmd, shell=True).decode()

                        match = re.search(r"Router:\s+([\d\.]+)", out)
                        if match:
                            gateway = match.group(1)
                            return gateway
                        return "192.168.0.1"
                    except Exception:
                        return "192.168.0.1"
                case "Linux":
                    try:
                        with open("/proc/net/route", "r") as f:
                            for line in f.readlines()[1:]:
                                parts = line.split()

                                if parts[1] == '00000000':
                                    gw_hex = parts[2]
                                    return ".".join([str(int(gw_hex[i:i+2], 16)) for i in range(6, -2, -2)])
                    except Exception:
                        pass
                    return "192.168.0.1"
        except Exception:
            return "192.168.1.1" # Fallback to common alternative gateway
        
    def get_local_ip(self):
        os_type = platform.system()
        try:
            if os_type == "Darwin":
                # return subprocess.check_output(["ipconfig", "getifaddr", "en0"]).decode().strip()
                
                return subprocess.check_output("ipconfig getifaddr $(networksetup -listallhardwareports | awk '/Wi-Fi/{getline; print $2}')", shell=True).decode().strip()

            elif os_type == "Windows":
                raw_out = subprocess.check_output("ipconfig")
                out = ""
                for enc in ['cp950', 'utf-8', 'gbk', 'cp437']:
                    try:
                        out = raw_out.decode(enc)
                        break
                    except UnicodeDecodeError: continue
                # Generalized regex to capture IPv4 address across different Windows localizations
                ips = re.findall(r"(?:IPv4 Address|IPv4 位址)[\.\s\:]+([\d\.]+)", out)
                return ips[0] if ips else "127.0.0.1"
            elif os_type == "Linux":
                # Using a more robust method to get IP if hostname -I fails
                return subprocess.check_output("hostname -I | awk '{print $1}'", shell=True).decode().strip() or "127.0.0.1"

        except Exception:
            return "127.0.0.1"
        
    def _load_initial_config(self):
        if not os.path.exists(TEMP_DIR):
            os.mkdir(TEMP_DIR)

        base_path = os.path.dirname(os.path.abspath(__file__))
        temp_ids_path = os.path.join(TEMP_DIR, "last_ids_settings.yaml")
        default_ids_path = os.path.join(base_path, "config/ids_settings.yaml")

        # 1. Working copy of IDS rules
        ids_rules = {}
        if os.path.exists(temp_ids_path):
            # Prioritize user settings in temp
            with open(temp_ids_path, 'r', encoding='utf-8') as f:
                ids_rules = yaml.safe_load(f)
        elif os.path.exists(default_ids_path):
            # Otherwise, initialize from the standard config.
            with open(default_ids_path, 'r', encoding='utf-8') as f:
                ids_rules = yaml.safe_load(f)
            # Save a copy to temp immediately
            with open(temp_ids_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(ids_rules, f)

        # 2. Handle the last_config.json
        if os.path.exists(LAST_CONFIG_FILE):
            with open(LAST_CONFIG_FILE, 'r') as f:
                conf = json.load(f)
                # Force update the ids path and rules to memory to ensure synchronization with the temp file.
                if "ids" not in conf:
                    conf["ids"] = {}
                conf["ids"]["config_path"] = temp_ids_path
                conf["ids"]["rules"] = ids_rules
                
                # Ensure 'cloud' key exists for backward compatibility
                if "cloud" not in conf:
                    conf["cloud"] = {
                        "enabled": False,
                        "region": "us-east-1",
                        "sync_interval": 60,
                        "namespace": "Aegis/NetValid"
                    }
                return conf
            
        # 3. If even last_config.json doesn't exist, create a completely new preset.
        conf = {
            "gateway_ip": self._get_default_gateway(),
            "inet": self.get_local_ip(),
            "default_device_count": 5,
            "scan_interval": 2,
            "interface": "wlan0" if self.os_type == "Linux" else "en0",
            "stresser": {
                "target_ip": self.get_local_ip(),
                "threads": 10,
                "packet_type": "UDP",
                "duration": 60,
                "bandwidth": "100M",
                "parallel": 4
            },
            "simulator": {
                "device_count": 5,
                "default_device_count": 10,
                "scan_interval": 5,
                "prefix": "IoT_Dev_"
            },
            "ids": {
                "interface": "en0",
                "config_path": temp_ids_path,
                "rules": ids_rules
                },
            "cloud": {
                "enabled": False,
                "region": "us-east-1",
                "sync_interval": 60,
                "namespace": "Aegis/NetValid"
            }
        }
        self._save_config(conf)
        return conf
    
    def _save_config(self, conf):
        with open(LAST_CONFIG_FILE, 'w') as f:
            json.dump(conf, f, indent=4)

    def _init_engines(self):
        return {
            "IDS": IDSEngine(self.core, config=self.config),
            "Simulator": SimulatorEngine(self.core, self.config),
            "Stresser": StresserEngine(self.core, self.config),
            "WiFi": MonitorEngine(self.core, self.config),
            "NetService": NetworkServiceEngine(self.core, self.config),
            "SoC": SoCGuardianEngine(self.core, self.config)
        }

    def update_config_cmd(self, key_path, value):
        """
        Support hierarchical path updates (e.g. ids.rules.threat_signatures.PORT_SCAN.min_ports)
        """
        parts = key_path.split('.')
        
        # Type conversion
        if value.isdigit():
            value = int(value)
        elif value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False

        # DFS Key
        target = self.config
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                console.print(f"[red]Path {key_path} not found.[/red]")
                return
            target = target[part]

        if parts[-1] not in target:
            console.print(f"[red]Key '{parts[-1]}' not found in '{'.'.join(parts[:-1])}'.[/red]")
            return

        target[parts[-1]] = value
        self._save_config(self.config)

        # If the modification involves an IDS rule, it should be synchronously written back to the YAML file.
        if parts[0] == "ids" and "rules" in self.config["ids"]:
            try:
                with open(self.config["ids"]["config_path"], 'w') as f:
                    yaml.safe_dump(self.config["ids"]["rules"], f)
            except Exception as e:
                console.print(f"[red]Failed to sync IDS rules to YAML: {e}[/red]")

        # Notify the engine of global changes (such as Gateway)
        if key_path == "gateway_ip":
            for engine in self.engines.values():
                if hasattr(engine, 'gateway_ip'):
                    engine.gateway_ip = value

        # React to Cloud Configuration changes
        if key_path.startswith("cloud."):
            if self.cloud_validator:
                self.cloud_validator.refresh_config(self.config)
            else:
                console.print("[yellow]Warning: CloudValidator is not initialized (check logs for errors). AWS sync unavailable.[/yellow]")

        console.print(f"[green]Config Updated: {key_path} = {value}[/green]")

    def make_dashboard(self) -> Table:
        """
        Build real-time data table
        """

        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)

        sys_info = f"OS: [bold cyan]{self.os_type}[/bold cyan] | Gateway: [bold yellow]{self.config['gateway_ip']}[/bold yellow] | Interface: {self.config['interface']}"
        grid.add_row(Panel(sys_info, title="🛡️ Aegis System Status", border_style="blue"))

        table = Table(title="🛡️ Aegis NetValid Core - Real-time Dashboard", show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Engine", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Key Metrics", style="magenta")

        # Use Aggregator to get unified data
        data_snapshot = self.data_aggregator.collect_all_metrics()
        engine_data = data_snapshot.get("engines", {})
        health = self.orchestrator.get_system_health()

        # 1. WiFi Data
        try:
            w = engine_data.get("WiFi", {})
            table.add_row("WiFi Monitor", health.get("WiFi", "??"), f"SSID: {w.get('ssid')} | RSSI: {w.get('rssi')}dBm | SNR: {w.get('snr')}")
        except Exception:
            table.add_row("WiFi Monitor", "[yellow]WARN[/yellow]", "Data Error")

        # 2. Simulator Data
        try:
            s = engine_data.get("Simulator", {})
            table.add_row("IoT Simulator", health.get("Simulator", "??"), f"Devices: {s.get('active_devices', 0)} | Total Packets: {s.get('total_sent', 0)}")
        except Exception:
            table.add_row("IoT Simulator", "[yellow]WARN[/yellow]", "Data Error")

        # 3. Stresser Data
        try:
            st = engine_data.get("Stresser", {})
            table.add_row("Traffic Stresser", health.get("Stresser", "??"), f"Current: {st.get('current_mbps', 0)} Mbps")
        except Exception:
            table.add_row("Traffic Stresser", "[yellow]WARN[/yellow]", "Data Error")

        # 4. IDS Data
        try:
            i = engine_data.get("IDS", {})
            threat_style = "[red]" if i.get('threats', 0) > 0 else "[white]"
            table.add_row("IDS Guardian", health.get("IDS", "??"), f"Threats: {threat_style}{i.get('threats', 0)}[/] | Score: {i.get('score', 100)}")
        except Exception:
            table.add_row("IDS Guardian", "[red]ERR[/red]", "Data Error")

        # 5. Network Service Data
        try:
            ns = engine_data.get("NetService", {})
            table.add_row("Net Services", health.get("NetService", "??"), f"DNS: {ns.get('dns_ms')}ms | GW: {ns.get('gw_link')} | Routes: {ns.get('routes')}")
        except Exception:
            table.add_row("Net Services", "[yellow]WARN[/yellow]", "Data Error")

        # 6. SoC Health Data
        try:
            soc = engine_data.get("SoC", {})
            table.add_row("SoC Guardian", health.get("SoC", "??"), f"Temp: {soc.get('temp')} | Load: {soc.get('load')} | PoE: {soc.get('poe')}")
        except Exception:
            table.add_row("SoC Guardian", "[yellow]WARN[/yellow]", "Data Error")

        grid.add_row(table)
        return grid
    
    def make_log_panel(self):
        logs = list(self.core.message_log)[-15:]
        
        while len(logs) < 15:
            logs.insert(0, "")

        content = "\n".join(logs)

        return Panel(
            content,
            title="[bold white]💬 Real-time Logs[/bold white]",
            border_style="cyan", 
            height=18,
            padding=(0, 1)
        )
    
    def handle_commands(self, live):
        """
        Loop for handling user input
        """
        while self.running:

            input()

            live.stop()
            while self.running:
                console.print("\n[bold yellow]─── Command Mode ───────────────────────────────────[/bold yellow]")
                cmd_raw = console.input("[bold yellow]Aegis CMD > [/bold yellow]").strip()

                if not cmd_raw:
                    break

                parts = cmd_raw.split()
                cmd = parts[0].lower()
                
                if cmd == "quit":
                    self.stop_all()
                    return
                elif cmd in ["back", "exit"]:
                    break
                elif cmd == "help" or cmd == "?":
                    self.show_help()
                elif cmd == "set" and len(parts) == 3:
                    self.update_config_cmd(parts[1], parts[2])
                elif cmd == "infect" and len(parts) > 1:
                    target_ip = parts[1]
                    self.engines["Simulator"].trigger_infection(target_ip)
                elif cmd == "stress" and len(parts) > 1:
                    if parts[1] == "start":
                        self.orchestrator.start_engine("Stresser")
                    elif parts[1] == "stop":
                        self.orchestrator.stop_engine("Stresser")
                elif cmd == "spawn":
                    self.engines["Simulator"].spawn_devices(5)
                else:
                    console.print(f"[red]Unknown command: {cmd}[/red] (Try: help, set cloud.enabled true, stress start, back)")

            if self.running:
                console.print("[dim]Returning to Dashboard...[/dim]")
                time.sleep(0.5)
                live.start()

    def start_all(self):
        self.orchestrator.start_all()
        
    def stop_all(self):
        self.running = False
        self.orchestrator.stop_all()

        self.core.fix_log_permissions()
        console.print("[bold red]Aegis Core Shutting Down...[/bold red]")

    def run(self):
        self.is_inputting = False
        self.start_all()

        self.report_manager.start_auto_sampling(interval=1)
        
        layout = Layout()
        layout.split_column(
            Layout(name="body", ratio=1),
            Layout(name="log_area", ratio=2),
            Layout(name="footer", size=3)
        )

        live = Live(layout, refresh_per_second=4, screen=True)
        live.start()

        cmd_thread = threading.Thread(target=self.handle_commands, args=(live,), daemon=True)
        cmd_thread.start()

        try:
            while self.running:
                if live.is_started:
                    layout["body"].update(self.make_dashboard())
                    layout["log_area"].update(self.make_log_panel())
                layout["footer"].update(Panel(
                    "[bold cyan]Press ENTER to input command[/bold cyan]", 
                    title="System Status", border_style="blue"
                ))
                
                # Cloud Sync Logic
                current_time = time.time()
                cloud_conf = self.config.get("cloud", {})
                if self.cloud_validator and current_time - self.last_cloud_sync >= cloud_conf.get("sync_interval", 60):
                    self.cloud_validator.sync_to_cloud(self.data_aggregator.get_latest_summary())
                    self.last_cloud_sync = current_time
                    
                time.sleep(0.2)
        except KeyboardInterrupt:
            self.running = False
        finally:
            live.stop()

            if hasattr(self, 'report_manager'):
                self.report_manager.stop_event.set()
                # console.print("[yellow]📊 Generating final visual report...[/yellow]")
                self.core.aegis_log("[yellow]📊 Generating final visual report...[/yellow]", "Main")
                self.report_manager.generate_visual_report()

            self.stop_all()

if __name__ == "__main__":
    try:
        #print("DEBUG: Initializing Core...")
        
        app = AegisCLI()
        app.run()
    except Exception as e:
        print(f"❌ Python Error: {e}")
    except KeyboardInterrupt:
        print("\nStopping...")
    except BaseException as be:
        print(f"❌ System Level Error: {be}")
    finally:
        print("DEBUG: Process Terminated.")