from unittest.mock import MagicMock, patch
from core.cloud_validator import CloudValidator


def make_validator(enabled=True):
    core = MagicMock()
    config = {"cloud": {"enabled": enabled, "region": "us-east-1", "namespace": "Test/NS"}}
    with patch("core.cloud_validator.boto3") as mock_boto3:
        mock_boto3.client.return_value = MagicMock()
        validator = CloudValidator(core, config)
    return validator


def test_initial_status_never_synced():
    validator = make_validator()

    status = validator.get_status()

    assert status["enabled"] is True
    assert status["last_sync_status"] == "NEVER"
    assert status["last_sync_time"] is None


def test_successful_sync_updates_status():
    validator = make_validator()
    snapshot = {"engines": {"Stresser": {"current_mbps": 42}}}

    validator.sync_to_cloud(snapshot)

    status = validator.get_status()
    assert status["last_sync_status"] == "OK"
    assert status["last_sync_time"] is not None
    assert status["last_sync_error"] is None
    validator.cw.put_metric_data.assert_called_once()


def test_failed_sync_updates_status_without_clobbering_last_success_time():
    validator = make_validator()
    snapshot = {"engines": {"Stresser": {"current_mbps": 42}}}

    validator.sync_to_cloud(snapshot)  # succeeds, records last_sync_time
    first_success_time = validator.last_sync_time

    validator.cw.put_metric_data.side_effect = Exception("boom")
    validator.sync_to_cloud(snapshot)  # now fails

    status = validator.get_status()
    assert status["last_sync_status"] == "ERROR"
    assert status["last_sync_error"] == "boom"
    assert status["last_sync_time"] == first_success_time


def test_disabled_validator_never_syncs():
    validator = make_validator(enabled=False)
    snapshot = {"engines": {"Stresser": {"current_mbps": 42}}}

    validator.sync_to_cloud(snapshot)

    status = validator.get_status()
    assert status["enabled"] is False
    assert status["last_sync_status"] == "NEVER"
