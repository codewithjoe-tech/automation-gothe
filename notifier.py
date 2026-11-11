# notifier.py
import sys
import time
from types import SimpleNamespace
from plyer import notification

try:
    import winsound
except ImportError:  # not Windows — terminal bell instead
    def _bell(freq: int, ms: int) -> None:
        sys.stdout.write("\a")
        sys.stdout.flush()

    winsound = SimpleNamespace(Beep=_bell)


def alert():
    """Play 3 urgent beep tones to alert the user."""
    for _ in range(3):
        winsound.Beep(1000, 400)  # 1000 Hz, 400ms
        time.sleep(0.1)


def notify_desktop(title: str, message: str):
    """Show a Windows desktop toast notification."""
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Goethe Booking Bot",
            timeout=10,
        )
    except Exception:  # no notification backend (e.g. no dbus) — never block booking on it
        pass


def fire_alert():
    """Fire both the sound alert and desktop notification together."""
    alert()
    notify_desktop(
        title="SLOTS OPEN — Goethe B2",
        message="Booking now! Check Chrome tabs."
    )
