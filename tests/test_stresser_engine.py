from unittest.mock import MagicMock
from engines.traffic_stresser.stresser_engine import StresserEngine


def make_engine():
    core = MagicMock()
    return StresserEngine(core, {"stresser": {"packet_type": "UDP"}})


def test_parses_live_mbps_from_interval_line():
    engine = make_engine()
    engine.is_running = True
    engine.process = MagicMock()
    engine.process.stdout.readline.side_effect = [
        b"[  5]   0.00-1.00   sec   622 KBytes  5.09 Mbits/sec  39\n",
        b"",
    ]
    engine._read_output()
    assert engine.stats["current_mbps"] == 5.09


def test_parses_receiver_summary_loss_and_jitter():
    engine = make_engine()
    engine.is_running = True
    engine.process = MagicMock()
    engine.process.stdout.readline.side_effect = [
        b"[  5]   0.00-2.00 sec  1.20 MBytes  5.02 Mbits/sec  0.000 ms  0/77 (0%)  sender\n",
        b"[  5]   0.00-2.00 sec  1.20 MBytes  5.02 Mbits/sec  0.031 ms  3/77 (3.9%)  receiver\n",
        b"",
    ]
    engine._read_output()
    assert engine.stats["jitter_ms"] == 0.031
    assert engine.stats["lost_packets"] == 3
    assert engine.stats["total_packets"] == 77
    assert engine.stats["packet_loss_pct"] == 3.9


def test_sender_line_does_not_update_loss_stats():
    engine = make_engine()
    engine.is_running = True
    engine.process = MagicMock()
    engine.process.stdout.readline.side_effect = [
        b"[  5]   0.00-2.00 sec  1.20 MBytes  5.02 Mbits/sec  0.000 ms  9/77 (11%)  sender\n",
        b"",
    ]
    engine._read_output()
    assert engine.stats["lost_packets"] == 0
    assert engine.stats["total_packets"] == 0


def test_get_report_returns_new_fields():
    engine = make_engine()
    engine.stats["jitter_ms"] = 1.2
    engine.stats["packet_loss_pct"] = 2.5
    report = engine.get_report()
    assert report["jitter_ms"] == 1.2
    assert report["packet_loss_pct"] == 2.5
