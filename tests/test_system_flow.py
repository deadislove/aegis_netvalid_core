import pytest
import time
from unittest.mock import MagicMock
from core.orchestrator import Orchestrator
from core.data_aggregator import DataAggregator

class MockEngine:
    def __init__(self):
        self.is_running = False
    def start(self):
        self.is_running = True
    def stop(self):
        self.is_running = False
    def get_report(self):
        return {"status": "ok"}

def test_orchestrator_lifecycle():
    mock_core = MagicMock()
    engines = {
        "WiFi": MockEngine(),
        "IDS": MockEngine()
    }
    
    orch = Orchestrator(mock_core, engines)
    
    # Test Start All
    orch.start_all()
    assert engines["WiFi"].is_running is True
    assert engines["IDS"].is_running is True
    
    # Test Health Check
    health = orch.get_system_health()
    assert health["WiFi"] == "OK"
    
    # Test Data Aggregation
    aggregator = DataAggregator(engines)
    snapshot = aggregator.collect_all_metrics()
    assert "WiFi" in snapshot["engines"]
    assert snapshot["engines"]["WiFi"]["status"] == "ok"
    
    # Test Stop All
    orch.stop_all()
    assert engines["WiFi"].is_running is False
    assert engines["IDS"].is_running is False