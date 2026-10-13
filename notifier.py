# notifier.py
"""Alerting: make sure a human finds out within seconds, wherever they are."""
import time
import logging
import urllib.request

from config import NTFY_TOPIC, NTFY_SERVER

logger = logging.getLogger(__name__)

try:
    import winsound
except ImportError:  # non-Windows
    winsound = None

try:
    from plyer import notification
except ImportError:
    notification = None


def alert_sound(rounds: int = 6) -> None:
    """Loud, repeated beeps — meant to wake someone in the next room."""
    if winsound is None:
        print("\a" * rounds, flush=True)
        return
    for _ in range(rounds):
        winsound.Beep(1200, 350)
        winsound.Beep(900, 350)
        time.sleep(0.1)


def notify_desktop(title: str, message: str) -> None:
    if notification is None:
        return
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Goethe Slot Watcher",
            timeout=30,
        )
    except Exception as e:
        logger.warning(f"Desktop toast failed: {e}")


def notify_phone(title: str, message: str) -> None:
    """Push to the user's own ntfy topic. No-op unless NTFY_TOPIC is set."""
    if not NTFY_TOPIC:
        return
    try:
        req = urllib.request.Request(
            f"{NTFY_SERVER}/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": "urgent", "Tags": "rotating_light"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        logger.info("Phone push sent.")
    except Exception as e:
        logger.warning(f"Phone push failed: {e}")


def fire_alert(url: str = "") -> None:
    """Sound + desktop toast + optional phone push, all at once."""
    title = "SLOTS OPEN — Goethe B2"
    message = "Booking is open. Switch to the Chrome window and book now."
    notify_desktop(title, message)
    notify_phone(title, f"{message}\n{url}".strip())
    alert_sound()
