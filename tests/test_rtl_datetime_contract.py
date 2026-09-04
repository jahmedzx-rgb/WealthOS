from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GLOBAL_CSS = (ROOT / "frontend/src/index.css").read_text(encoding="utf-8")


def test_all_native_date_and_time_inputs_follow_rtl_direction():
    for input_type in ("date", "datetime-local", "time"):
        selector = f"[dir='rtl'] input[type='{input_type}']"
        assert selector in GLOBAL_CSS
    assert "direction: rtl" in GLOBAL_CSS
    assert "text-align: right" in GLOBAL_CSS
    assert "::-webkit-datetime-edit" in GLOBAL_CSS
    assert "::-webkit-calendar-picker-indicator" in GLOBAL_CSS


def test_english_date_and_time_inputs_remain_ltr():
    for input_type in ("date", "datetime-local", "time"):
        selector = f"[dir='ltr'] input[type='{input_type}']"
        assert selector in GLOBAL_CSS
    assert "direction: ltr" in GLOBAL_CSS
    assert "text-align: left" in GLOBAL_CSS
