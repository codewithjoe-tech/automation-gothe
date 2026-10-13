# tests/test_main.py
from unittest.mock import MagicMock, patch

import main


def _fresh_driver():
    main._driver = MagicMock()
    main._keep_browser = False
    return main._driver


def test_shutdown_quits_the_driver():
    drv = _fresh_driver()
    main.shutdown()
    drv.quit.assert_called_once()


def test_shutdown_is_idempotent():
    drv = _fresh_driver()
    main.shutdown()
    main.shutdown()
    drv.quit.assert_called_once()  # not called twice
    assert main._driver is None


def test_shutdown_falls_back_to_service_stop_when_quit_raises():
    """Chrome already dead: quit() raises, so kill the chromedriver service."""
    drv = _fresh_driver()
    drv.quit.side_effect = RuntimeError("already gone")
    main.shutdown()
    drv.service.stop.assert_called_once()


def test_shutdown_never_raises_even_if_everything_fails():
    drv = _fresh_driver()
    drv.quit.side_effect = RuntimeError("boom")
    drv.service.stop.side_effect = RuntimeError("also boom")
    main.shutdown()  # must not raise


def test_keep_browser_leaves_chrome_running():
    drv = _fresh_driver()
    main._keep_browser = True
    try:
        main.shutdown()
        drv.quit.assert_not_called()
    finally:
        main._keep_browser = False


def test_signal_handler_shuts_down_and_exits_130():
    drv = _fresh_driver()
    with patch("main.sys.exit") as mock_exit:
        main._on_signal(2, None)
    drv.quit.assert_called_once()
    mock_exit.assert_called_once_with(130)


# ── CLI ───────────────────────────────────────────────────────────────────────

def test_url_flag_skips_the_prompt():
    args = main.parse_args(["--url", "https://example.com/exam?examId=1"])
    with patch("builtins.input", side_effect=AssertionError("should not prompt")):
        assert main.resolve_url(args) == "https://example.com/exam?examId=1"


def test_open_time_flag_skips_the_prompt():
    args = main.parse_args(["--open-time", "10:30"])
    with patch("builtins.input", side_effect=AssertionError("should not prompt")):
        assert main.resolve_open_time(args) == "10:30"


def test_bad_url_exits():
    args = main.parse_args(["--url", "not-a-url"])
    try:
        main.resolve_url(args)
    except SystemExit as e:
        assert e.code == 1
    else:
        raise AssertionError("expected SystemExit")


def test_keep_browser_defaults_off():
    assert main.parse_args([]).keep_browser is False
    assert main.parse_args(["--keep-browser"]).keep_browser is True


# ── auto-booking outcome ────────────────────────────────────────────────────────

def test_booking_outcome_message_success():
    msg = main.booking_outcome_message(True)
    assert "modules" in msg.lower()
    assert "payment" in msg.lower() or "finish" in msg.lower()


def test_booking_outcome_message_partial():
    msg = main.booking_outcome_message(None)
    assert "manual" in msg.lower() or "pick" in msg.lower()


def test_booking_outcome_message_blocked():
    msg = main.booking_outcome_message(False)
    assert "block" in msg.lower() or "manual" in msg.lower()
