from main_aegis import sparkline


def test_sparkline_empty():
    assert sparkline([]) == ""


def test_sparkline_flat_values():
    assert sparkline([5, 5, 5]) == "▁▁▁"


def test_sparkline_spans_full_character_range():
    result = sparkline([0, 25, 50, 75, 100])
    assert result[0] == "▁"
    assert result[-1] == "█"
    assert len(result) == 5


def test_sparkline_respects_width():
    values = list(range(30))
    result = sparkline(values, width=10)
    assert len(result) == 10
    # only the last `width` values should be considered
    assert result == sparkline(values[-10:], width=10)
