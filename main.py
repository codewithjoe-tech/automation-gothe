# main.py
"""
Goethe B2 slot watcher.

One ordinary Chrome window, signed in and parked on the exam page. The moment
the "Select modules" button appears you get a beep, a desktop toast and
(optionally) a push on your phone — then you book it yourself in the window
that's already open and already logged in.

Ctrl+C shuts everything down, Chrome included.
"""
import sys
import os
import time
import signal
import atexit
import argparse
import logging
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import undetected_chromedriver as uc
from selenium.common.exceptions import WebDriverException

from config import EXAM_URL, OPEN_TIME, NTFY_TOPIC, BURST_WINDOW, CHROME_VERSION
from poller import poll_until_open
from booker import run_booking
from notifier import fire_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROFILE_DIR = os.path.join(_SCRIPT_DIR, "chrome-profile")

# Single live driver, so the shutdown hooks can always reach it.
_driver = None
_keep_browser = False


# ── Shutdown ──────────────────────────────────────────────────────────────────

def shutdown() -> None:
    """Close Chrome and its chromedriver. Safe to call more than once."""
    global _driver
    drv, _driver = _driver, None
    if drv is None or _keep_browser:
        return
    try:
        drv.quit()
        logger.info("Chrome closed.")
    except Exception:
        # quit() can raise if Chrome already died; kill the service directly.
        try:
            drv.service.stop()
        except Exception:
            pass


def _on_signal(signum, _frame):
    print("\n\n  Shutting down…")
    shutdown()
    sys.exit(130)


# ── Time handling ─────────────────────────────────────────────────────────────

def parse_open_time(raw: str):
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            t = datetime.strptime(raw, fmt)
            now = datetime.now()
            target = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target
        except ValueError:
            continue
    return None


def wait_until(target: datetime, label: str) -> None:
    while True:
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 0:
            print(f"\r  {label} — starting now.{' ' * 30}")
            return
        mins, secs = divmod(int(remaining), 60)
        hrs, mins = divmod(mins, 60)
        print(f"\r  {label} at {target.strftime('%H:%M')} — "
              f"{hrs:02d}:{mins:02d}:{secs:02d} remaining…", end="", flush=True)
        time.sleep(1)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="watch",
        description="Watch a Goethe exam page and alert when slots open.",
    )
    p.add_argument("--url", default=None,
                   help="Exam URL (with examId). Overrides EXAM_URL and the prompt.")
    p.add_argument("--open-time", default=None, metavar="HH:MM",
                   help="When slots drop. Watching starts 5 min before.")
    p.add_argument("--no-login-wait", action="store_true",
                   help="Skip the 'press Enter once logged in' pause.")
    p.add_argument("--keep-browser", action="store_true",
                   help="Leave Chrome open after Ctrl+C (default: close it).")
    return p.parse_args(argv)


def resolve_url(args) -> str:
    url = args.url or EXAM_URL
    if not url:
        url = input("  Paste the exam URL: ").strip()
    elif not args.url:
        val = input(f"  Exam URL [{url}]: ").strip()
        url = val or url
    if not url.startswith("http"):
        print("  That doesn't look like a URL (must start with https://).")
        sys.exit(1)
    return url


def resolve_open_time(args) -> str:
    if args.open_time is not None:
        return args.open_time
    hint = OPEN_TIME or "start watching immediately"
    val = input(f"  Booking opens at HH:MM (24h) [{hint}]: ").strip()
    return val or OPEN_TIME


# ── Browser ───────────────────────────────────────────────────────────────────

def launch_browser():
    """
    Stealth Chrome (undetected-chromedriver) with a persistent profile.

    Persistent profile → your login and the warmed Akamai session survive
    restarts. undetected-chromedriver → no `navigator.webdriver` flag and no
    'controlled by automated test software' banner, which is what got the plain
    Selenium browser 403'd. This is the single logged-in session — NOT the old
    Tor/multi-instance stack.
    """
    os.makedirs(_PROFILE_DIR, exist_ok=True)

    opts = uc.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument(f"--user-data-dir={_PROFILE_DIR}")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")

    kwargs = {"options": opts}
    if CHROME_VERSION:
        kwargs["version_main"] = CHROME_VERSION

    driver = uc.Chrome(**kwargs)
    driver.implicitly_wait(0)
    return driver


def booking_outcome_message(result) -> str:
    """Human-readable summary of what run_booking() did."""
    if result is True:
        return ("Auto-selected all modules and clicked Continue. Switch to "
                "Chrome and FINISH the payment/login steps now.")
    if result is None:
        return ("Some modules were unavailable — the browser is on the module "
                "page. Pick the modules you want manually, then continue.")
    return ("Couldn't reach the module page — likely an Akamai block or error "
            "page. Book manually in the Chrome window.")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(argv=None) -> None:
    global _driver, _keep_browser

    args = parse_args(argv)
    _keep_browser = args.keep_browser

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)
    atexit.register(shutdown)

    print("\n" + "=" * 64)
    print("  Goethe B2 Slot Watcher")
    print("  Watches one page and alerts you. You do the booking.")
    print("=" * 64 + "\n")

    url = resolve_url(args)
    open_time = resolve_open_time(args)
    target = parse_open_time(open_time) if open_time else None
    if open_time and target is None:
        logger.warning(f"Couldn't parse '{open_time}' — watching immediately.")

    push_state = "on" if NTFY_TOPIC else "off — set NTFY_TOPIC to enable"
    ctrlc_state = "Chrome stays open" if _keep_browser else "Chrome closes too"
    print(f"\n  Phone push: {push_state}")
    if target:
        print(f"  Open time:  {target.strftime('%H:%M')} "
              f"(fast checks for {int(BURST_WINDOW)}s either side)")
    print(f"  On Ctrl+C:  {ctrlc_state}")
    print("  Opening Chrome…\n")

    try:
        _driver = launch_browser()
    except WebDriverException as e:
        logger.error(f"Chrome failed to launch: {e}")
        sys.exit(1)

    try:
        _driver.get(url)
    except WebDriverException as e:
        logger.warning(f"Initial load failed ({e}) — the watcher will retry.")

    if not args.no_login_wait:
        print("\n" + "-" * 64)
        print("  LOG IN NOW in the Chrome window that just opened.")
        print("  A logged-in session is the single biggest speed-up there is —")
        print("  it takes the login step off the critical path entirely.")
        print("-" * 64)
        input("\n  Press Enter once you're logged in and on the exam page… ")

    if target:
        watch_from = target - timedelta(minutes=5)
        if watch_from > datetime.now():
            print()
            wait_until(watch_from, "Watching starts")
            print()

    poll_until_open(_driver, url, open_at=target)

    # Slots open — alert, then immediately try to grab the modules in the same
    # already-logged-in, warmed session (its Akamai cookie is the best shot at
    # getting the automated clicks through).
    fire_alert(url)
    logger.info("Slots open — auto-booking in the logged-in session…")

    try:
        result = run_booking(_driver)
    except Exception as e:
        logger.error(f"Auto-booking raised: {e}", exc_info=True)
        result = False

    message = booking_outcome_message(result)
    logger.info(message)

    print("\n" + "=" * 64)
    print("  SLOTS ARE OPEN — auto-booking attempted")
    print()
    print(f"  {message}")
    print()
    if not _keep_browser:
        print("  Ctrl+C closes Chrome — don't press it mid-booking.")
        print("  Use --keep-browser next time if you'd rather it stayed open.")
    print("=" * 64 + "\n")

    logger.info("Alert firing every 30s for 2.5 min so you can finish. Ctrl+C to stop.")
    for _ in range(5):
        time.sleep(30)
        fire_alert(url)


if __name__ == "__main__":
    run()
