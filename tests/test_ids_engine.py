import time
from unittest.mock import MagicMock
from engines.ids_guardian.ids_engine import IDSEngine


def make_engine():
    core = MagicMock()
    config = {"ids": {"interface": "en0", "config_path": "/nonexistent/path.yaml"}}
    return IDSEngine(core, config)


def test_on_packet_tracks_threat_by_type():
    engine = make_engine()
    engine.detector.evaluate = MagicMock(side_effect=[
        ("CRITICAL", "port scan!", "PORT_SCAN"),
        ("CRITICAL", "too much traffic", "ABNORMAL_TRAFFIC"),
        ("CRITICAL", "port scan!", "PORT_SCAN"),
        ("CLEAR", "Normal", None),
    ])

    for i in range(4):
        engine._on_packet({"src": f"1.2.3.{i}", "size": 10, "dport": 80, "timestamp": time.time()})

    assert engine.threat_count == 3
    assert engine.threat_by_type == {"PORT_SCAN": 2, "ABNORMAL_TRAFFIC": 1}


def test_get_report_includes_threat_by_type():
    engine = make_engine()
    engine.threat_count = 2
    engine.threat_by_type = {"PORT_SCAN": 2}

    report = engine.get_report()

    assert report["threats"] == 2
    assert report["threat_by_type"] == {"PORT_SCAN": 2}
