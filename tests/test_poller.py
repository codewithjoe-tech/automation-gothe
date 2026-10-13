# tests/test_poller.py
from unittest.mock import MagicMock
from selenium.common.exceptions import WebDriverException
from poller import get_select_modules_btn


def _make_btn(displayed: bool):
    btn = MagicMock()
    btn.is_displayed.return_value = displayed
    return btn


def test_returns_none_when_no_buttons():
    driver = MagicMock()
    driver.find_elements.return_value = []
    assert get_select_modules_btn(driver) is None


def test_returns_none_when_all_hidden():
    driver = MagicMock()
    driver.find_elements.return_value = [_make_btn(False), _make_btn(False)]
    assert get_select_modules_btn(driver) is None


def test_returns_first_visible_button():
    driver = MagicMock()
    b1 = _make_btn(False)
    b2 = _make_btn(True)
    b3 = _make_btn(True)
    driver.find_elements.return_value = [b1, b2, b3]
    assert get_select_modules_btn(driver) is b2


def test_returns_none_on_webdriver_exception():
    driver = MagicMock()
    driver.find_elements.side_effect = WebDriverException("stale")
    assert get_select_modules_btn(driver) is None


# ── looks_blocked ─────────────────────────────────────────────────────────────

from poller import looks_blocked  # noqa: E402


def _driver_with_body(text: str):
    driver = MagicMock()
    driver.find_element.return_value.text = text
    return driver


def test_looks_blocked_detects_forbidden():
    assert looks_blocked(_driver_with_body("403 Forbidden")) is True


def test_looks_blocked_detects_high_demand():
    assert looks_blocked(_driver_with_body("Due to HIGH DEMAND, please retry")) is True


def test_looks_blocked_false_on_normal_page():
    assert looks_blocked(_driver_with_body("Goethe-Zertifikat B2 — exam dates")) is False


def test_looks_blocked_false_when_body_unreachable():
    driver = MagicMock()
    driver.find_element.side_effect = WebDriverException("no body")
    assert looks_blocked(driver) is False


# ── burst window ──────────────────────────────────────────────────────────────

from datetime import datetime, timedelta  # noqa: E402
from poller import _in_burst_window  # noqa: E402


def test_no_burst_without_an_open_time():
    assert _in_burst_window(None) is False


def test_burst_active_just_before_open_time():
    assert _in_burst_window(datetime.now() + timedelta(seconds=30)) is True


def test_burst_active_just_after_open_time():
    assert _in_burst_window(datetime.now() - timedelta(seconds=30)) is True


def test_burst_inactive_well_before_open_time():
    assert _in_burst_window(datetime.now() + timedelta(minutes=30)) is False


def test_burst_inactive_well_after_open_time():
    assert _in_burst_window(datetime.now() - timedelta(minutes=30)) is False


# ── countdown sleep ───────────────────────────────────────────────────────────

from poller import _sleep_with_countdown  # noqa: E402


def test_sleep_with_countdown_accepts_burst_flag():
    # poll_until_open calls this as _sleep_with_countdown(gap, checks, burst=...).
    # The signature must accept `burst`, or the watcher crashes on the first
    # non-blocked check. seconds=0 returns immediately (no real sleep).
    assert _sleep_with_countdown(0, 1, burst=True) is None
    assert _sleep_with_countdown(0, 1, burst=False) is None
