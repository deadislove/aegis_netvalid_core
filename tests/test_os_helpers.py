from unittest.mock import patch, mock_open
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


def test_get_local_ip_windows_extracts_ipv4():
    fake_output = "Ethernet adapter:\n   IPv4 Address. . . . . . . . . . . : 10.0.0.5\n".encode("utf-8")
    with patch("subprocess.check_output", return_value=fake_output):
        assert os_helpers.get_local_ip("Windows") == "10.0.0.5"


def test_get_local_ip_linux_takes_first_address():
    with patch("subprocess.check_output", return_value=b"192.168.1.20 172.17.0.1\n"):
        assert os_helpers.get_local_ip("Linux") == "192.168.1.20"


def test_get_local_ip_unknown_os_returns_fallback():
    assert os_helpers.get_local_ip("Plan9") == "127.0.0.1"
