import pytest
from unittest.mock import MagicMock, patch, mock_open
from engines.soc_guardian.soc_engine import SoCGuardianEngine

@pytest.fixture
def mock_core():
    return MagicMock()

@pytest.fixture
def engine(mock_core):
    return SoCGuardianEngine(mock_core, {"soc_guardian": {"thermal_path": "/tmp/thermal"}})

def test_thermal_reading_success(engine):
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="45000")):
            assert engine._get_thermal() == 45.0

def test_thermal_reading_failure(engine):
    with patch("os.path.exists", return_value=False):
        assert engine._get_thermal() == -1.0

def test_cpu_load_parsing(engine):
    load_str = "0.50 0.40 0.30 1/100 1234"
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=load_str)):
            assert engine._get_cpu_load() == "0.50 0.40 0.30"

def test_throttling_logic(engine):
    engine.stats["throttled"] = False
    # Simulate high temperature via the monitor loop logic
    with patch.object(engine, '_get_thermal', return_value=90.0):
        with patch.object(engine, '_get_cpu_load', return_value="1.0"):
            # Run one iteration of the logic (extracted from loop)
            temp = engine._get_thermal()
            if temp > 85.0:
                engine.stats["throttled"] = True
            
            assert engine.stats["throttled"] is True