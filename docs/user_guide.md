# 📖 User Guide

A practical, day-to-day manual for running Aegis NetValid Core. For system design see [Architecture](architecture.md); for adding a new engine see [Engine Development](engine_development.md); for AWS setup see [Cloud Validation](cloud_validation.md); for embedded/SoC work see [Hardware Integration](hardware_integration.md) and [SoC Bring-up](soc_bringup_guide.md); if something's broken see [Troubleshooting](troubleshooting.md).

## 1. Install

```bash
git clone https://github.com/da-weilin/Aegis_NetValid_Core.git
cd Aegis_NetValid_Core
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -e .
```

Use `-e` (editable install). A plain `pip install .` copies the source into `venv/lib/.../site-packages/` at install time — later edits or `git pull`s won't take effect until you reinstall. See [Troubleshooting #5](troubleshooting.md#5-sudo-aegis-doesnt-reflect-code-changes-you-just-made) if `sudo aegis` ever seems to be running old code.

**Prerequisites:** Python 3.10+, and for packet capture: `libpcap` (Linux, usually preinstalled on macOS), or [Npcap](https://nmap.org/npcap/) in "WinPcap API-compatible Mode" (Windows). The Traffic Stresser also needs `iperf3` on your `PATH`.

## 2. First Run

```bash
sudo aegis
```

Root/Administrator is required for raw packet capture (the IDS sniffer, in particular). Without it, Aegis still runs — you'll see a warning at startup, the IDS/Simulator engines will log permission errors for the raw-socket parts, but the rest of the dashboard (NetService, SoC, Stresser, Cloud, Trends, Aegis Process) works normally.

**No root, no `iperf3`, nothing installed beyond the Python deps?** Use `--demo`:
```bash
python main_aegis.py --demo
```
The Simulator still runs its full device-behavior logic but hands packets to the IDS in-memory instead of sending them on the wire, so `infect <IP>` still triggers a real detected threat. The Stresser simulates a plausible Mbps/loss/jitter series (tagged `(demo)` on the dashboard) instead of launching `iperf3`. Everything else (WiFi, NetService, SoC, Cloud, Trends, Aegis Process) behaves exactly as in a normal run.

On first launch, Aegis auto-detects your gateway IP, local IP, and network interface, and writes them to `temp/last_config.json`. Override any of them at launch:

```bash
sudo aegis --gateway 192.168.1.1 --interface en0 --target 192.168.1.50 --dev-count 10 --demo
```

Press **Enter** at any time to drop into command mode; press Enter again on an empty line (or type `back`) to return to the live dashboard.

## 3. Dashboard Reference

Each row polls its engine's `get_report()` on every refresh. The **Status** column reflects whether the engine's background thread is alive (`OK`/`DOWN`) — it does *not* mean the data being shown is meaningful (see the SoC caveat below).

| Row | What it shows | Notes |
|---|---|---|
| **WiFi Monitor** | SSID, RSSI (dBm), SNR | Read via OS-native tools (`system_profiler` on macOS, `iwconfig`/`/proc/net/wireless` on Linux, `netsh` on Windows). |
| **IoT Simulator** | Active device count, breakdown by type (e.g. `LightBulb:8, DDoS_Attacker:2`), total packets sent | Devices spawn via `spawn`, mutate via `infect <IP>`. |
| **Traffic Stresser** | Current Mbps; once a UDP test's final summary lands, also Loss % and Jitter (ms) | Loss/Jitter only appear for `packet_type: UDP` and only after iperf3 emits its end-of-test "receiver" line — expect them blank for the first few seconds of a run, and never for TCP tests. In `--demo` mode the row is tagged `(demo)` and the numbers are simulated, not from real `iperf3` traffic. |
| **IDS Guardian** | Total threat count, breakdown by signature (`PORT_SCAN`, `ABNORMAL_TRAFFIC`, `DDOS_ATTACK`) | `DDOS_ATTACK` fires on an absolute per-device bandwidth ceiling (`threat_signatures.DDOS_ATTACK.min_kbps`, default 10000); `ABNORMAL_TRAFFIC` fires on a per-device-type profile limit (`device_profiles.<type>.max_kbps`) — DDoS is checked first since it's the stronger signal. |
| **Net Services** | DNS resolution latency, gateway reachability + RTT, route count, RTT to the Stresser's target (once configured) | Route count is Linux-only today (`ip route show`); shows `0` elsewhere. |
| **SoC Guardian** | Temp, CPU frequency, load average | **Linux-only by design** — reads `/sys/class/thermal/...`, `/proc/loadavg`. On macOS/Windows (or the host running Aegis in general) this will show placeholder values (`-1.0°C`, `0MHz`, `N/A`) even though the row says `OK` — it's meant for the embedded device under test, not the Aegis host. For the Aegis host's own usage, see "Aegis Process" below. |
| **Cloud Sync** | Whether CloudWatch sync is enabled, and the outcome/age of the last attempt | States: `N/A` (CloudValidator failed to init), `IDLE` (disabled), `??` (enabled, no sync attempted yet), `OK` (last sync succeeded, with age), `ERR` (last sync failed, with the error — the last *successful* sync time is preserved, not overwritten by a failed attempt). |
| **Trends** | Unicode sparkline of recent Mbps and threat-count samples | Sourced from the report generator's 1-second sampling history; shows "Collecting samples..." for the first couple of seconds. |
| **Aegis Process** | CPU% and memory (MB) of the Aegis process itself | This is the host machine running Aegis — cross-platform via `psutil`, unrelated to SoC Guardian. |

## 4. Commands

Available once you press Enter to open command mode:

| Command | Action |
|---|---|
| `help` / `?` | Show the command list |
| `set <path> <value>` | Update config at a dotted path, e.g. `set ids.rules.threat_signatures.PORT_SCAN.min_ports 50` |
| `set cloud.enabled true` | Turn on AWS CloudWatch sync (see [Cloud Validation](cloud_validation.md) for IAM setup) |
| `set gateway_ip 10.0.0.1` | Change the gateway - propagates live to every engine that tracks it |
| `stress start` / `stress stop` | Start/stop the Traffic Stresser engine on demand |
| `spawn` | Add 5 more simulated IoT devices |
| `infect <IP>` | Flip a simulated device to `DDoS_Attacker` behavior (simulation-only — see [SECURITY.md](../SECURITY.md), this does not affect real devices) |
| `back` / `exit` | Return to the live dashboard |
| `quit` | Stop all engines, flush the visual report, and exit |

`set` accepts any dotted path into the live config dict; `int`/`true`/`false` values are parsed automatically, everything else stays a string. Changes to `ids.*` are also written back to the working IDS rules YAML immediately.

## 5. Scenario Files

Automated multi-step sequences live under `config/scenarios/`:

```yaml
name: "IoT DDoS Defense Validation"
steps:
  - action: "start_engine"
    target: "Simulator"
  - action: "wait"
    duration: 15
  - action: "trigger_infection"
    target: "192.168.0.105"
  - action: "stress_start"
```

## 6. Output

- **Logs**: `outputs/logs/aegis_<timestamp>.log` — one file per run, flushed on every message.
- **Reports**: `outputs/reports/report_<timestamp>/` — written on `quit`, containing `bandwidth_chart.png`, `summary.md`, and `data.json`. If this directory (or `outputs/` itself) was previously created while running under `sudo`, a later non-root run may fail to write a new report with a `Permission denied` error logged (not a crash) — reclaim ownership with `sudo chown -R $(whoami) outputs/`.
