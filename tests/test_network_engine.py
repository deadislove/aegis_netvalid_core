import pytest
from unittest.mock import MagicMock, patch
from engines.network_service.service_engine import NetworkServiceEngine

@pytest.fixture
def mock_core():
    core = MagicMock()
    return core

@pytest.fixture
def engine(mock_core):
    # gateway_ip/stresser live at the root of the app config, same as the
    # real AegisCLI config - not nested under "network_service".
    config = {
        "gateway_ip": "192.168.1.1",
        "stresser": {"target_ip": "10.0.0.5"},
        "network_service": {
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

def test_gateway_check_returns_rtt_from_ping_reply(engine):
    with patch("subprocess.check_output") as mock_ping:
        mock_ping.return_value = b"64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=2.50 ms"
        assert engine._check_gateway() == 2.5

        mock_ping.side_effect = Exception("Host Unreachable")
        assert engine._check_gateway() is None


def test_gateway_uses_root_level_gateway_ip(engine):
    with patch("subprocess.check_output") as mock_ping:
        mock_ping.return_value = b"64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=1.0 ms"
        engine._check_gateway()
        called_cmd = mock_ping.call_args[0][0]
        assert "192.168.1.1" in called_cmd


def test_target_check_returns_rtt(engine):
    with patch("subprocess.check_output") as mock_ping:
        mock_ping.return_value = b"64 bytes from 10.0.0.5: icmp_seq=0 ttl=64 time=8.25 ms"
        assert engine._check_target() == 8.25


def test_target_check_none_when_no_target_configured(mock_core):
    engine = NetworkServiceEngine(mock_core, {"gateway_ip": "192.168.1.1"})
    assert engine._check_target() is None


def test_report_generation(engine):
    engine.stats["dns_latency"] = 45.5
    engine.stats["dhcp_status"] = "Bound"
    engine.stats["gateway_reachable"] = True
    engine.stats["gateway_rtt_ms"] = 3.14
    engine.stats["target_rtt_ms"] = None

    report = engine.get_report()
    assert report["dns_ms"] == "45.50"
    assert report["gw_link"] == "UP"
    assert report["dhcp"] == "Bound"
    assert report["gw_rtt_ms"] == "3.14"
    assert report["target_rtt_ms"] == "N/A"