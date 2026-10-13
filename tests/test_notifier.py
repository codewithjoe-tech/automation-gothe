# tests/test_notifier.py
from unittest.mock import patch

import notifier
from notifier import alert_sound, notify_desktop, notify_phone


def test_alert_sound_calls_winsound():
    """Alert should call winsound.Beep at least once."""
    with patch("notifier.winsound.Beep") as mock_beep:
        alert_sound()
        assert mock_beep.called


def test_alert_sound_respects_rounds():
    """Each round plays two tones, so N rounds == 2N beeps."""
    with patch("notifier.winsound.Beep") as mock_beep, patch("notifier.time.sleep"):
        alert_sound(rounds=3)
        assert mock_beep.call_count == 6


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


def test_notify_desktop_survives_plyer_failure():
    """A broken toast backend must never crash the watcher."""
    with patch("notifier.notification.notify", side_effect=RuntimeError("no backend")):
        notify_desktop("t", "m")  # must not raise


def test_notify_phone_is_noop_without_topic():
    """No NTFY_TOPIC configured means nothing leaves the machine."""
    with patch.object(notifier, "NTFY_TOPIC", ""), \
         patch("notifier.urllib.request.urlopen") as mock_open:
        notify_phone("t", "m")
        mock_open.assert_not_called()


def test_notify_phone_posts_when_topic_set():
    with patch.object(notifier, "NTFY_TOPIC", "my-secret-topic"), \
         patch.object(notifier, "NTFY_SERVER", "https://ntfy.sh"), \
         patch("notifier.urllib.request.urlopen") as mock_open:
        notify_phone("Title", "Body")
        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        assert req.full_url == "https://ntfy.sh/my-secret-topic"
        assert req.data == b"Body"


def test_notify_phone_survives_network_failure():
    with patch.object(notifier, "NTFY_TOPIC", "topic"), \
         patch("notifier.urllib.request.urlopen", side_effect=OSError("offline")):
        notify_phone("t", "m")  # must not raise
