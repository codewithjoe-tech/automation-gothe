# main.py
import sys
import time
import logging
import os
from datetime import datetime, timedelta
import undetected_chromedriver as uc

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from poller import poll_until_open
from booker import run_booking
from notifier import fire_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_open_time(raw: str) -> datetime | None:
    """Parse a time string like '10:00' or '14:35' into a datetime for today."""
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            t = datetime.strptime(raw, fmt)
            now = datetime.now()
            target = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            # If the time has already passed today, assume tomorrow
            if target <= now:
                target += timedelta(days=1)
            return target
        except ValueError:
            continue
    return None


def wait_until(target: datetime):
    """Sleep until target time, showing a live in-place countdown."""
    while True:
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 0:
            print(f"\r  Starting now!{' ' * 30}")
            break
        mins, secs = divmod(int(remaining), 60)
        print(f"\r  Waiting until {target.strftime('%H:%M')} — {mins:02d}:{secs:02d} remaining…", end="", flush=True)
        time.sleep(1)


def get_inputs():
    print("\n" + "=" * 55)
    print("  Goethe B2 Booking Bot")
    print("=" * 55)
    url = input("Paste exam URL: ").strip()
    if not url:
        print("URL cannot be empty.")
        sys.exit(1)
    if not url.startswith("http"):
        print("Invalid URL — must start with https://  (did you paste the full link?)")
        sys.exit(1)
    open_time = input("Booking opens at (e.g. 10:00 or 14:35) [optional]: ").strip()
    return url, open_time


PROFILE_DIR = os.path.join(os.path.dirname(__file__), "chrome-profile")


def launch_driver():
    opts = uc.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    drv = uc.Chrome(options=opts, version_main=147)
    drv.implicitly_wait(0)  # must be 0 — any value > 0 makes find_elements wait that long on every miss

    # Block everything we don't need — speeds up each page load significantly
    drv.execute_cdp_cmd("Network.enable", {})
    drv.execute_cdp_cmd("Network.setBlockedURLs", {"urls": [
        # Assets
        "*.css", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg",
        "*.woff", "*.woff2", "*.ttf", "*.eot", "*.webp", "*.ico",
        # Trackers & ads (all confirmed from network capture)
        "*google-analytics.com*", "*googletagmanager.com*",
        "*googleadservices.com*", "*google.com/rmkt*",
        "*google.com/ccm*", "*analytics.google.com*",
        "*linkedin.com*", "*usercentrics.eu*",
        "*ppcprotect.com*", "*/N_O5Ke/*",
    ]})
    logger.info("Resource blocking enabled — images/trackers/CSS will be skipped.")
    return drv


def run():
    url, open_time = get_inputs()

    logger.info("=" * 55)
    logger.info("Goethe B2 Booking Bot — Starting")
    logger.info(f"Target: {url}")

    target_dt = None
    if open_time:
        target_dt = parse_open_time(open_time)
        if target_dt:
            logger.info(f"Will start polling at {target_dt.strftime('%H:%M')} (today/tomorrow)")
        else:
            logger.warning(f"Could not parse '{open_time}' — starting immediately.")

    logger.info("Press Ctrl+C to stop at any time.")
    logger.info("=" * 55)

    CHROME_WARMUP = 30  # seconds before open time to launch Chrome

    if target_dt:
        warmup_at = target_dt - timedelta(seconds=CHROME_WARMUP)
        if warmup_at > datetime.now():
            wait_until(warmup_at)
        print()  # newline after live countdown

    logger.info("Launching Chrome so it's ready at open time…")
    driver = launch_driver()
    logger.info("Chrome ready — loading page now.")
    driver.get(url)  # load page during warmup so it's ready at open time

    if target_dt:
        poll_start = target_dt - timedelta(seconds=5)
        remaining = (poll_start - datetime.now()).total_seconds()
        if remaining > 0:
            wait_until(poll_start)
            print()

    try:
        # Phase 1: page already loaded — just refresh until button appears
        poll_until_open(driver, url, already_loaded=True)
        fire_alert()

        # Re-enable all resources so checkout pages render properly for manual use
        driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": []})
        logger.info("Resource blocking lifted — full page rendering restored.")

        # Phase 2: click through to Continue (button re-found fresh to avoid stale element)
        success = run_booking(driver)

        if success:
            logger.info("=" * 55)
            logger.info("SUCCESS — reached CONTINUE.")
            logger.info("Complete login manually in the Chrome window.")
            logger.info("Press Ctrl+C when done to close the browser.")
            logger.info("=" * 55)
        else:
            logger.warning("Booking incomplete — check Chrome and act manually.")

        # Keep browser open for manual login
        while True:
            time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    run()
