"""
Cross-platform OS/network helpers shared across the CLI and engines.

These are pure functions (no dependency on AegisCLI or engine state) so they
can be unit tested and reused without instantiating the full application.
"""
import re
import subprocess


def decode_console_output(raw: bytes, encodings=('cp950', 'utf-8', 'gbk', 'cp437')) -> str:
    """
    Decode subprocess byte output from a console, trying locale-specific
    encodings in order. Windows consoles report non-English locales (e.g.
    Traditional/Simplified Chinese) in codepages that aren't valid utf-8.
    """
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


def get_local_ip(os_type: str) -> str:
    """Best-effort primary local IPv4 detection for Windows/Darwin/Linux."""
    try:
        if os_type == "Darwin":
            # Equivalent to:
            # ipconfig getifaddr $(networksetup -listallhardwareports | awk '/Wi-Fi/{getline; print $2}')
            ports_out = subprocess.check_output(["networksetup", "-listallhardwareports"]).decode()
            lines = ports_out.splitlines()
            device = None
            for i, line in enumerate(lines):
                if "Wi-Fi" in line and i + 1 < len(lines):
                    parts = lines[i + 1].split()
                    if len(parts) >= 2:
                        device = parts[1]
                    break
            if not device:
                return "127.0.0.1"
            return subprocess.check_output(["ipconfig", "getifaddr", device]).decode().strip()

        if os_type == "Windows":
            raw_out = subprocess.check_output("ipconfig")
            out = decode_console_output(raw_out)
            # Generalized regex to capture IPv4 address across different Windows localizations
            ips = re.findall(r"(?:IPv4 Address|IPv4 位址)[\.\s\:]+([\d\.]+)", out)
            return ips[0] if ips else "127.0.0.1"

        if os_type == "Linux":
            out = subprocess.check_output(["hostname", "-I"]).decode().strip()
            return out.split()[0] if out else "127.0.0.1"

        return "127.0.0.1"
    except Exception:
        return "127.0.0.1"
