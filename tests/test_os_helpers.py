from unittest.mock import patch, mock_open, MagicMock
import socket
from lib import os_helpers


def test_decode_console_output_prefers_first_valid_encoding():
    raw = "台灣".encode("cp950")
    assert os_helpers.decode_console_output(raw) == "台灣"


def test_decode_console_output_falls_back_when_no_encoding_matches():
    # Invalid byte sequence for every candidate encoding
    raw = b"\xff\xfe\x00\x01"
    result = os_helpers.decode_console_output(raw)
    assert isinstance(result, str)


def test_get_default_gateway_linux_parses_proc_net_route():
    route_contents = (
        "Iface\tDestination\tGateway\tFlags\n"
        "en0\t00000000\t0101A8C0\t0003\n"
    )
    with patch("builtins.open", mock_open(read_data=route_contents)):
        gateway = os_helpers.get_default_gateway("Linux")
    assert gateway == "192.168.1.1"


def test_get_default_gateway_unknown_os_returns_fallback():
    assert os_helpers.get_default_gateway("Plan9") == "192.168.0.1"


def _snic(address, family=socket.AF_INET):
    return MagicMock(family=family, address=address)


def _snicstats(isup=True):
    return MagicMock(isup=isup)


def test_get_local_ip_picks_first_up_non_loopback_ipv4():
    addrs = {
        "lo0": [_snic("127.0.0.1")],
        "en0": [_snic("192.168.1.42")],
    }
    stats = {"lo0": _snicstats(isup=True), "en0": _snicstats(isup=True)}
    with patch("psutil.net_if_addrs", return_value=addrs), patch("psutil.net_if_stats", return_value=stats):
        assert os_helpers.get_local_ip() == "192.168.1.42"


def test_get_local_ip_skips_down_interfaces():
    addrs = {
        "en0": [_snic("192.168.1.42")],
        "en5": [_snic("10.0.0.5")],
    }
    stats = {"en0": _snicstats(isup=False), "en5": _snicstats(isup=True)}
    with patch("psutil.net_if_addrs", return_value=addrs), patch("psutil.net_if_stats", return_value=stats):
        assert os_helpers.get_local_ip() == "10.0.0.5"


def test_get_local_ip_skips_link_local_addresses():
    addrs = {"en0": [_snic("169.254.1.1"), _snic("192.168.1.42")]}
    stats = {"en0": _snicstats(isup=True)}
    with patch("psutil.net_if_addrs", return_value=addrs), patch("psutil.net_if_stats", return_value=stats):
        assert os_helpers.get_local_ip() == "192.168.1.42"


def test_get_local_ip_falls_back_when_nothing_found():
    with patch("psutil.net_if_addrs", return_value={}), patch("psutil.net_if_stats", return_value={}):
        assert os_helpers.get_local_ip() == "127.0.0.1"
