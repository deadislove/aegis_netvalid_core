# 🚀 SoC Bring-up & Validation Guide

Aegis NetValid Core is designed to be a "stability hammer" for new silicon and embedded boards. For installation, the CLI dashboard, and general usage, see the main [README](../README.md) and the [User Guide](user_guide.md). For the underlying hardware interfaces, see [Hardware Integration](hardware_integration.md).

## 1. Validation Workflow
1.  **Baseline Health**: Start Aegis with the Stresser idle and let `SoCGuardian` run for a few minutes to establish idle temperature and load average (`SoC Guardian` row on the dashboard).
2.  **Network Saturation**: Run `stress start` at a moderate bandwidth (e.g. `set stresser.bandwidth 50M`) and watch for connectivity issues in the `Net Services` row (DNS latency, gateway RTT).
3.  **Thermal Stress**: Scale up (`set stresser.bandwidth 500M`). Watch the `SoC Guardian` row for a `🔥 HOT` status — this flips once the SoC's reported temperature crosses **85°C**, which is currently a hardcoded threshold in `engines/soc_guardian/soc_engine.py`, not a configurable value.
4.  **Service Stability**: Confirm `Net Services` (DNS/gateway/target RTT) stays responsive while the SoC is under load.

Remember: `SoCGuardian` only produces real numbers on a Linux device with the expected `sysfs`/`procfs` paths (see [Hardware Integration](hardware_integration.md)) — running this workflow against the machine hosting Aegis itself (macOS/Windows) will just show placeholder values.

## 2. Detecting Driver Issues
Things worth watching for during bring-up, using what Aegis currently reports:
- **High load without matching throughput**: rising `Load` in the `SoC Guardian` row while `Traffic Stresser`'s Mbps stays flat can indicate an inefficient or misbehaving driver.
- **Packet loss under load**: watch `Loss`/`Jitter` on the `Traffic Stresser` row (UDP tests only) alongside SoC load — loss that tracks with CPU load rather than bandwidth often points at a driver-side bottleneck, not a network one.
- **Gateway RTT degradation under thermal stress**: if `Net Services`' gateway RTT climbs as the SoC heats up, that's worth investigating as a hardware-level symptom, not just a software one.

Long-duration memory-leak or interrupt-storm investigation (`/proc/meminfo`, `/proc/interrupts`) is not yet automated by Aegis — see [Hardware Integration](hardware_integration.md#2-gpio--interrupts) for the manual approach today.

## 3. Example Test Configuration
For a standard ARMv8 SoC, a reasonable starting scenario:
```yaml
stresser:
  bandwidth: "500M"
  parallel: 4
  packet_type: "UDP"
soc_guardian:
  interval: 1
  thermal_path: "/sys/class/thermal/thermal_zone0/temp"
```
