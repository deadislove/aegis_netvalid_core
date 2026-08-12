# 🔌 Hardware Integration Guide

This document describes how Aegis NetValid Core interfaces with physical hardware and embedded drivers. For installation, the CLI dashboard, and general usage, see the main [README](../README.md) and the [User Guide](user_guide.md).

## 1. SoC Thermal & Power (I2C/PoE)
The `SoCGuardianEngine` monitors hardware health through the Linux kernel's `sysfs` and `procfs` interfaces. **This engine is Linux-only by design** — on macOS/Windows the sysfs paths below don't exist, so it will report placeholder values (`-1.0°C`, `0MHz`, `N/A` load) rather than an error. It's meant to run on the embedded Linux device under test, not on the host running Aegis. (For the host's own resource usage, see the "Aegis Process" row covered in the [User Guide](user_guide.md).)

### Thermal Monitoring
By default, Aegis reads from `/sys/class/thermal/thermal_zone0/temp`. If your SoC uses a different path (e.g., Rockchip or i.MX8), override it via the `thermal_path` key under the engine's `soc_guardian` config section.

The throttling flag (`🔥 HOT` on the dashboard) is currently a **hardcoded 85°C threshold** in `engines/soc_guardian/soc_engine.py` — it is not yet read from config, so setting a `thermal_threshold` value in YAML has no effect today.

### PoE & I2C Power Monitoring
`SoCGuardianEngine._check_poe()` currently returns a fixed placeholder string (`"Normal (54V)"` or `"Disabled"`) — it does not yet perform a real I2C/PMIC read. Extending it to do so is a natural next step for hardware that supports PoE (Power over Ethernet):
- **Library**: `smbus2` for Python-based I2C communication.
- **Example**: Reading a PMIC register to verify current draw during a 100Mbps stress test.

## 2. GPIO & Interrupts
During bring-up, verifying GPIO stability under network load is critical. This is not yet implemented in Aegis, but is a natural extension point:
- **Path**: `/sys/class/gpio/`
- **Validation idea**: Monitor interrupt frequency in `/proc/interrupts` to check whether network driver activity is starving hardware interrupts.

## 3. Bluetooth Low Energy (BLE)
Also not yet implemented, but a natural extension point for validating BLE-to-WiFi co-existence:
- **Tooling**: `hcitool` or `bluetoothctl`.
- **Metric idea**: RSSI stability of BLE beacons while the Traffic Stresser is saturating the 2.4GHz WiFi band.

## 4. Hardware Reference Table
| Interface | Linux Driver/Module | Validation Method | Status |
|-----------|---------------------|--------------------|--------|
| Thermal   | `thermal_zone0`     | sysfs read         | Implemented (Linux-only) |
| CPU Freq  | `cpufreq`           | sysfs read         | Implemented (Linux-only) |
| I2C/PoE   | `i2c-dev`           | Register Read/Write| Extension point, not implemented |
| GPIO      | `gpio-sysfs`        | State Polling      | Extension point, not implemented |
| BLE       | `bluez`             | RSSI/Scan Latency  | Extension point, not implemented |
