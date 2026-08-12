from core.aegis_core import AegisCore


def test_get_self_resource_usage_returns_sane_values():
    core = AegisCore({})
    try:
        usage = core.get_self_resource_usage()
        assert usage["cpu_percent"] >= 0
        assert usage["memory_mb"] > 0
    finally:
        core.close_log()
