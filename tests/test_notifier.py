# tests/test_notifier.py
from unittest.mock import patch, MagicMock
from notifier import alert, notify_desktop


def test_alert_calls_winsound():
    """Alert should call winsound.Beep at least once."""
    with patch("notifier.winsound.Beep") as mock_beep:
        alert()
        assert mock_beep.called


def test_alert_beeps_multiple_times():
    """Alert should beep 3 times for urgency."""
    with patch("notifier.winsound.Beep") as mock_beep:
        alert()
        assert mock_beep.call_count == 3


def test_notify_desktop_calls_plyer():
    """Desktop notification should call plyer.notification.notify."""
    with patch("notifier.notification.notify") as mock_notify:
        notify_desktop("Test title", "Test message")
        mock_notify.assert_called_once()


def test_notify_desktop_passes_title_and_message():
    """Notification must include the given title and message."""
    with patch("notifier.notification.notify") as mock_notify:
        notify_desktop("Slots Open!", "Booking now...")
        call_kwargs = mock_notify.call_args[1]
        assert call_kwargs["title"] == "Slots Open!"
        assert call_kwargs["message"] == "Booking now..."
