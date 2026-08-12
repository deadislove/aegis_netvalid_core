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

### 5. `sudo aegis` Doesn't Reflect Code Changes You Just Made

**Symptoms:**
- You edited the source (e.g. fixed a bug, pulled a new commit), but `sudo aegis` still behaves like the old version.
- Engines that should be running show `DOWN` on the dashboard even though the code looks right.
- The TUI feels less responsive than you remember it being after a fix.

**Cause:**
If you installed with `pip install .` (a regular, non-editable install), pip **copies** `main_aegis.py` and the `core/`/`engines/`/`lib/` packages into `venv/lib/pythonX.Y/site-packages/` at install time. The `aegis` command (`venv/bin/aegis`) imports from that copy — not from your working directory — so any edit you make to the repo afterward has **zero effect** on `sudo aegis` until you reinstall.

**Solution:**
Reinstall in **editable mode** so the installed command always points at your working tree:
```bash
pip install -e .
```
This only needs to be done once; after that, `sudo aegis` picks up source changes immediately, with no reinstall step. If you already have a stale regular install, running `pip install -e .` again will replace it.

To check which one you have:
```bash
python -c "import main_aegis; print(main_aegis.__file__)"
```
If the printed path is under `venv/lib/.../site-packages/`, you have a stale copy — reinstall with `-e`. If it points into your repo checkout, you're on the editable install.

---

## 💡 General Debugging Tips
-   **Check Logs:** Review the real-time logs in the TUI or the `outputs/logs/` directory for any additional error messages or warnings.
-   **Isolate Components:** If a specific engine fails, try running other engines separately (if possible) to isolate the problem.
-   **Consult Scapy Documentation:** For advanced network issues, the official Scapy documentation is an invaluable resource.