from unittest.mock import MagicMock
from engines.ids_guardian.anomaly_detector import AnomalyDetector


def make_detector(signatures=None):
    profiler = MagicMock()
    profiler.device_stats = {}
    return AnomalyDetector(profiler, signatures=signatures or {})


def test_abnormal_traffic_returns_category():
    detector = make_detector()
    detector.profiler.check_threshold_violation.return_value = (True, "🔥 ABNORMAL TRAFFIC: 500 > 100")

    status, reason, category = detector.evaluate("1.2.3.4")

    assert status == "CRITICAL"
    assert category == "ABNORMAL_TRAFFIC"
    assert "ABNORMAL TRAFFIC" in reason


def test_port_scan_returns_category():
    detector = make_detector(signatures={"PORT_SCAN": {"min_ports": 2, "description": "scan!"}})
    detector.profiler.check_threshold_violation.return_value = (False, "Normal")
    detector.profiler.device_stats = {"1.2.3.4": {"ports_seen": {80, 81, 82}, "packet_count": 3}}

    status, reason, category = detector.evaluate("1.2.3.4")

    assert status == "CRITICAL"
    assert category == "PORT_SCAN"
    assert reason == "scan!"


def test_clear_returns_none_category():
    detector = make_detector(signatures={"PORT_SCAN": {"min_ports": 20}})
    detector.profiler.check_threshold_violation.return_value = (False, "Normal")
    detector.profiler.device_stats = {"1.2.3.4": {"ports_seen": {80}, "packet_count": 1}}

    status, reason, category = detector.evaluate("1.2.3.4")

    assert status == "CLEAR"
    assert category is None


def test_ddos_attack_returns_category_when_over_absolute_threshold():
    detector = make_detector(signatures={
        "DDOS_ATTACK": {"min_kbps": 10000, "description": "🔥 Critical: Potential Outbound DDoS Attack"}
    })
    detector.profiler.get_recent_kbps.return_value = 15000

    status, reason, category = detector.evaluate("1.2.3.4")

    assert status == "CRITICAL"
    assert category == "DDOS_ATTACK"
    assert "DDoS" in reason
    # weaker per-device-profile check must not even be consulted
    detector.profiler.check_threshold_violation.assert_not_called()


def test_ddos_attack_does_not_fire_below_threshold():
    detector = make_detector(signatures={"DDOS_ATTACK": {"min_kbps": 10000}})
    detector.profiler.get_recent_kbps.return_value = 500
    detector.profiler.check_threshold_violation.return_value = (False, "Normal")

    status, reason, category = detector.evaluate("1.2.3.4")

    assert status == "CLEAR"
    assert category is None


def test_ddos_attack_takes_priority_over_abnormal_traffic():
    detector = make_detector(signatures={"DDOS_ATTACK": {"min_kbps": 1000}})
    detector.profiler.get_recent_kbps.return_value = 5000
    # Even if the device-profile check would also fire, DDOS_ATTACK wins.
    detector.profiler.check_threshold_violation.return_value = (True, "🔥 ABNORMAL TRAFFIC: 5000 > 100")

    status, reason, category = detector.evaluate("1.2.3.4")

    assert category == "DDOS_ATTACK"
