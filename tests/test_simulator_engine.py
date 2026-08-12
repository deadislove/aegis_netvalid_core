from unittest.mock import MagicMock, patch
from engines.iot_simulator.simulator_engine import SimulatorEngine


def make_engine():
    core = MagicMock()
    with patch("engines.iot_simulator.simulator_engine.getmacbyip", return_value="aa:bb:cc:dd:ee:ff"), \
         patch("engines.iot_simulator.simulator_engine.conf") as mock_conf:
        mock_conf.L3socket.return_value = MagicMock()
        engine = SimulatorEngine(core, {"gateway_ip": "192.168.0.1"})
    return engine


def test_get_report_breaks_down_by_device_type():
    engine = make_engine()
    engine.active_devices = [
        {"id": "192.168.0.101", "type": "LightBulb"},
        {"id": "192.168.0.102", "type": "LightBulb"},
        {"id": "192.168.0.103", "type": "IPCamera"},
        {"id": "192.168.0.104", "type": "DDoS_Attacker"},
    ]

    report = engine.get_report()

    assert report["active_devices"] == 4
    assert report["device_type_counts"] == {"LightBulb": 2, "IPCamera": 1, "DDoS_Attacker": 1}


def test_get_report_empty_devices():
    engine = make_engine()

    report = engine.get_report()

    assert report["active_devices"] == 0
    assert report["device_type_counts"] == {}


def test_trigger_infection_reflected_in_breakdown():
    engine = make_engine()
    engine.active_devices = [
        {"id": "192.168.0.101", "type": "LightBulb"},
        {"id": "192.168.0.102", "type": "LightBulb"},
    ]

    engine.trigger_infection("192.168.0.101")
    report = engine.get_report()

    assert report["device_type_counts"] == {"LightBulb": 1, "DDoS_Attacker": 1}


def test_demo_mode_skips_real_socket_and_arp():
    core = MagicMock()
    with patch("engines.iot_simulator.simulator_engine.getmacbyip") as mock_getmac, \
         patch("engines.iot_simulator.simulator_engine.conf") as mock_conf:
        engine = SimulatorEngine(core, {"gateway_ip": "192.168.0.1", "demo_mode": True})

    mock_getmac.assert_not_called()
    mock_conf.L3socket.assert_not_called()
    assert engine.socket is None


def test_demo_mode_send_packet_calls_callback_instead_of_socket():
    core = MagicMock()
    with patch("engines.iot_simulator.simulator_engine.getmacbyip"), \
         patch("engines.iot_simulator.simulator_engine.conf"):
        engine = SimulatorEngine(core, {"gateway_ip": "192.168.0.1", "demo_mode": True})

    received = []
    engine.on_packet_sent = lambda data: received.append(data)

    engine.send_packet({"id": "192.168.0.101", "type": "IPCamera"})

    assert len(received) == 1
    assert received[0]["src"] == "192.168.0.101"
    assert received[0]["dport"] == 5004
    assert engine.stats["total_sent"] == 1
