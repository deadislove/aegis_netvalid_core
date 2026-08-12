"""
Cross-platform OS/network helpers shared across the CLI and engines.
"""
import re
import socket
import subprocess

import psutil


def decode_console_output(raw: bytes, encodings=('cp950', 'utf-8', 'gbk', 'cp437')) -> str:
    """Decode console output, trying locale-specific encodings in order."""
    for enc in encodings:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace')


def get_default_gateway(os_type: str) -> str:
    """Best-effort default gateway detection for Windows/Darwin/Linux."""
    try:
        if os_type == "Windows":
            raw_out = subprocess.check_output(["ipconfig"])
            out = decode_console_output(raw_out)
            # Support international locales by matching keywords and extracting IPv4
            match = re.search(r"(?:Default Gateway|Gateway|預設閘道).*: ([\d\.]+)", out)
            return match.group(1) if match else "192.168.0.1"

        if os_type == "Darwin":
            try:
                out = subprocess.check_output(["system_profiler", "SPAirPortDataType"]).decode()
                match = re.search(r"Router:\s+([\d\.]+)", out)
                return match.group(1) if match else "192.168.0.1"
            except Exception:
                return "192.168.0.1"

        if os_type == "Linux":
            try:
                with open("/proc/net/route", "r") as f:
                    for line in f.readlines()[1:]:
                        parts = line.split()
                        if parts[1] == '00000000':
                            gw_hex = parts[2]
                            return ".".join(str(int(gw_hex[i:i + 2], 16)) for i in range(6, -2, -2))
            except Exception:
                pass
            return "192.168.0.1"

        return "192.168.0.1"
    except Exception:
        return "192.168.1.1"  # Fallback to common alternative gateway


def get_local_ip() -> str:
    """
    Best-effort primary local IPv4 detection, cross-platform via psutil -
    not tied to any particular interface name (previously Wi-Fi-only on
    macOS, which returned 127.0.0.1 on Ethernet-only Macs).
    """
    try:
        stats = psutil.net_if_stats()
        for iface, addrs in psutil.net_if_addrs().items():
            if iface not in stats or not stats[iface].isup:
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith(("127.", "169.254.")):
                    return addr.address
    except Exception:
        pass
    return "127.0.0.1"
