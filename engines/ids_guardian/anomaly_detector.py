from .traffic_profiler import TrafficProfiler

class AnomalyDetector:
    def __init__(self, profiler:TrafficProfiler, signatures: dict = None):
        self.profiler:TrafficProfiler = profiler
        self.signatures = signatures or {}


    def evaluate(self, ip, device_type="Unknown"):
        """
        Comprehensive assessment: Check traffic thresholds + behavioral patterns
        """
        
        is_threshold_violated, reason = self.profiler.check_threshold_violation(ip, device_type)
        if is_threshold_violated:
            return "CRITICAL", reason
        
        state = self.profiler.device_stats.get(ip)
        if state:
            scan_sig = self.signatures.get("PORT_SCAN", {})

            if len(state['ports_seen']) > scan_sig.get("min_ports", 20):
                return "CRITICAL", scan_sig.get("description", "Port Scanning Detected")
            
            if state["packet_count"] > 1000:
                pass

        return "CLEAR", "Normal"