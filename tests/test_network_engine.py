import pytest
from unittest.mock import MagicMock, patch
from engines.network_service.service_engine import NetworkServiceEngine

@pytest.fixture
def mock_core():
    core = MagicMock()
    return core

@pytest.fixture
def engine(mock_core):
    config = {
        "network_service": {
            "gateway_ip": "192.168.1.1",
            "interval": 1
        }
    }
    return NetworkServiceEngine(mock_core, config)

def test_dns_check_success(engine):
    with patch("socket.gethostbyname", return_value="8.8.8.8"):
        latency = engine._check_dns()
        assert latency >= 0

def test_dns_check_failure(engine):
    with patch("socket.gethostbyname", side_effect=Exception("Timeout")):
        latency = engine._check_dns()
        assert latency == -1

def test_gateway_check(engine):
    with patch("subprocess.check_output") as mock_ping:
        # Mock successful ping
        mock_ping.return_value = b"1 packets transmitted, 1 received"
        assert engine._check_gateway() is True
        
        # Mock failed ping
        mock_ping.side_effect = Exception("Host Unreachable")
        assert engine._check_gateway() is False

def test_report_generation(engine):
    engine.stats["dns_latency"] = 45.5
    engine.stats["dhcp_status"] = "Bound"
    engine.stats["gateway_reachable"] = True
    
    report = engine.get_report()
    assert report["dns_ms"] == "45.50"
    assert report["gw_link"] == "UP"
    assert report["dhcp"] == "Bound"