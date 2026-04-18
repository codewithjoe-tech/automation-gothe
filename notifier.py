# notifier.py
import winsound
import time
from plyer import notification


def alert():
    """Play 3 urgent beep tones to alert the user."""
    for _ in range(3):
        winsound.Beep(1000, 400)  # 1000 Hz, 400ms
        time.sleep(0.1)


def notify_desktop(title: str, message: str):
    """Show a Windows desktop toast notification."""
    notification.notify(
        title=title,
        message=message,
        app_name="Goethe Booking Bot",
        timeout=10,
    )


def fire_alert():
    """Fire both the sound alert and desktop notification together."""
    alert()
    notify_desktop(
        title="SLOTS OPEN — Goethe B2",
        message="Booking now! Check Chrome tabs."
    )
