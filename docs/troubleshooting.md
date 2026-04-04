# 🔍 Troubleshooting Guide

This document provides solutions to common issues encountered while setting up and running Aegis NetValid Core, especially those related to network permissions and dependencies.

---

## ❌ Common Errors & Solutions

### 1. `Permission Denied` or `Operation Not Permitted` for Network Operations (Scapy)

Aegis relies heavily on `Scapy` for raw packet injection and sniffing, which often requires elevated privileges.

#### **Linux / macOS**

**Error Message Examples:**
- `OSError: [Errno 1] Operation not permitted`
- `WARNING: No route found for IPv6 destination ff02::1. This may impact IPv6 traffic analysis.`
- `Permission denied (1)` when trying to capture packets.

**Solution:**
Aegis **must be run with root privileges** (or `sudo` on Linux/macOS) for full network functionality.

```bash
sudo python main_aegis.py
```

Additionally, ensure your user is part of the `npcap` group (or equivalent) if you're working with specific packet capture tools, though `sudo` usually bypasses this for Scapy.

#### **Windows**

**Error Message Examples:**
- `scapy.error.Scapy_Exception: WinPcap is not installed or not running.`
- `PermissionError: [WinError 5] Access is denied`

**Solution:**
1.  **Install Npcap:** Download and install `Npcap` (the modern successor to WinPcap) from the official website: [https://nmap.org/npcap/](https://nmap.org/npcap/)
2.  **Enable "WinPcap API-compatible Mode":** During Npcap installation, make sure to check the option for "Install Npcap in WinPcap API-compatible Mode". Scapy relies on this compatibility.
3.  **Run as Administrator:** Right-click your terminal (Command Prompt or PowerShell) and select "Run as administrator". Then run Aegis.

```powershell
# Open PowerShell as Administrator
python main_aegis.py
```

---

### 2. Network Interface Not Found

**Error Message Examples:**
- `ValueError: No such device (interface)`
- `Error: Interface 'wlan0' not found.`

**Solution:**
1.  **Verify Interface Name:** Use `ifconfig` (Linux/macOS) or `ipconfig` (Windows) to find the correct network interface name (e.g., `eth0`, `en0`, `Wi-Fi`).
2.  **Update Configuration:**
    -   **CLI Override:** Launch Aegis with the `--interface` argument:
        ```bash
        sudo python main_aegis.py --interface en0
        ```
    -   **Dynamic Update:** In the TUI, use the `set` command:
        ```
        Aegis CMD > set interface en0
        ```

---

### 3. Firewall Blocking Traffic

If you suspect traffic is being dropped even with correct permissions, your firewall might be interfering.

**Solution:**
-   **Temporarily Disable Firewall:** For testing purposes, you might temporarily disable your operating system's firewall (e.g., `ufw disable` on Linux, disabling Windows Defender Firewall). **Remember to re-enable it after testing.**
-   **Add Rules:** Configure your firewall to allow incoming and outgoing traffic on the specific ports and protocols Aegis uses (e.g., UDP for the stresser, ICMP for pings, etc.).

---

### 4. Python Environment Issues

**Error Message Examples:**
- `ModuleNotFoundError: No module named 'scapy'`
- `AttributeError: module 'scapy' has no attribute 'all'`

**Solution:**
Ensure all dependencies are correctly installed in your current Python environment.

```bash
pip install -r requirements.txt
```

---

## 💡 General Debugging Tips
-   **Check Logs:** Review the real-time logs in the TUI or the `outputs/logs/` directory for any additional error messages or warnings.
-   **Isolate Components:** If a specific engine fails, try running other engines separately (if possible) to isolate the problem.
-   **Consult Scapy Documentation:** For advanced network issues, the official Scapy documentation is an invaluable resource.