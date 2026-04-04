import time
from typing import Dict, Any

class DataAggregator:
    def __init__(self, engines: Dict[str, Any]):
        self.engines = engines
        self.history = []

    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Data is collected from all running engines and labeled with a uniform timestamp.
        """
        timestamp = time.time()
        snapshot = {
            "timestamp": timestamp,
            "engines": {}
        }

        for name, engine in self.engines.items():
            try:
                if hasattr(engine, "get_report"):
                    snapshot["engines"][name] = engine.get_report()
                else:
                    snapshot["engines"][name] = {"status": "no_report_available"}
            except Exception as e:
                snapshot["engines"][name] = {"error": str(e)}

        # Keep a simple historical record for trend analysis
        self.history.append(snapshot)
        if len(self.history) > 100:
            self.history.pop(0)
            
        return snapshot

    def get_latest_summary(self):
        if not self.history:
            return {}
        return self.history[-1]