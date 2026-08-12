from .traffic_profiler import TrafficProfiler

class AnomalyDetector:
    def __init__(self, profiler:TrafficProfiler, signatures: dict = None):
        self.profiler:TrafficProfiler = profiler
        self.signatures = signatures or {}


    def evaluate(self, ip, device_type="Unknown"):
        """
        Comprehensive assessment: Check traffic thresholds + behavioral patterns

        Returns (status, reason, category). category is the signature key
        that fired ("DDOS_ATTACK", "ABNORMAL_TRAFFIC", "PORT_SCAN"), or None
        when CLEAR - used by IDSEngine to keep a per-type threat count.
        """

        # DDOS_ATTACK is an absolute, device-type-agnostic bandwidth ceiling
        # (config: threat_signatures.DDOS_ATTACK.min_kbps) - checked first
        # since it's a stronger, more specific signal than a device merely
        # exceeding its own per-type profile limit.
        ddos_sig = self.signatures.get("DDOS_ATTACK", {})
        ddos_threshold = ddos_sig.get("min_kbps")
        if ddos_threshold is not None:
            recent_kbps = self.profiler.get_recent_kbps(ip)
            if recent_kbps > ddos_threshold:
                description = ddos_sig.get("description", "Potential DDoS Attack")
                return "CRITICAL", f"{description} ({recent_kbps:.2f} Kbps > {ddos_threshold})", "DDOS_ATTACK"

        is_threshold_violated, reason = self.profiler.check_threshold_violation(ip, device_type)
        if is_threshold_violated:
            return "CRITICAL", reason, "ABNORMAL_TRAFFIC"

        state = self.profiler.device_stats.get(ip)
        if state:
            scan_sig = self.signatures.get("PORT_SCAN", {})

            if len(state['ports_seen']) > scan_sig.get("min_ports", 20):
                return "CRITICAL", scan_sig.get("description", "Port Scanning Detected"), "PORT_SCAN"

            if state["packet_count"] > 1000:
                pass

        return "CLEAR", "Normal", None