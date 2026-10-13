# poller.py
"""
Single-session watcher.

One browser, one tab, one page — reloaded roughly once a minute until the
"Select modules" button appears. When the site pushes back (error page, 403,
high-demand interstitial) we back off exponentially instead of retrying harder.
"""
import time
import random
import logging
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import (
    SELECT_MODULES_SELECTOR,
    PAGE_LOAD_TIMEOUT,
    BACKOFF_START,
    BACKOFF_MAX,
    BURST_WINDOW,
    random_poll_interval,
    burst_interval,
)

logger = logging.getLogger(__name__)

_BLOCK_MARKERS = ("forbidden", "high demand", "too many requests", "access denied")


def get_select_modules_btn(driver):
    """Return the visible 'Select modules' button, or None if it isn't there yet."""
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, SELECT_MODULES_SELECTOR)
        visible = [b for b in btns if b.is_displayed()]
        return visible[0] if visible else None
    except WebDriverException:
        return None


def looks_blocked(driver) -> bool:
    """True if the site served an error / rate-limit page rather than the exam page."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
    except WebDriverException:
        return False
    return any(marker in body for marker in _BLOCK_MARKERS)


def _load(driver, url: str) -> bool:
    try:
        driver.get(url)
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return True
    except (TimeoutException, WebDriverException) as e:
        logger.warning(f"Load failed: {e}")
        return False


def _sleep_with_countdown(seconds: float, checks: int, burst: bool = False) -> None:
    label = "burst check" if burst else "check"
    end = time.monotonic() + seconds
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            print("\r" + " " * 70 + "\r", end="", flush=True)
            return
        print(f"\r  {label} #{checks} — not open. Next look in {int(remaining):3d}s…",
              end="", flush=True)
        time.sleep(min(1.0, remaining))


def _in_burst_window(open_at) -> bool:
    """True while we're within BURST_WINDOW seconds of the stated open time."""
    if open_at is None:
        return False
    return abs((open_at - datetime.now()).total_seconds()) <= BURST_WINDOW


def poll_until_open(driver, url: str, open_at: datetime | None = None):
    """
    Block until the 'Select modules' button shows up, then return it.

    open_at: if given, check every few seconds for BURST_WINDOW seconds either
    side of that time, then fall back to the normal pace.

    Returns the button element. Raises KeyboardInterrupt straight through so
    Ctrl+C stops the watcher cleanly.
    """
    logger.info(f"Watching: {url}")
    if open_at:
        logger.info(
            f"Open time {open_at.strftime('%H:%M')} — will check every "
            f"{int(burst_interval())}s or so for {int(BURST_WINDOW)}s either side."
        )
    logger.info("Pace outside that window: one check every 30-60s.")

    if not _load(driver, url):
        time.sleep(BACKOFF_START)
        _load(driver, url)

    checks = 0
    backoff = BACKOFF_START

    while True:
        checks += 1

        btn = get_select_modules_btn(driver)
        if btn:
            print("\r" + " " * 70 + "\r", end="", flush=True)
            logger.info(f"'Select modules' appeared on check #{checks} — booking is OPEN.")
            return btn

        if looks_blocked(driver):
            wait = backoff * random.uniform(0.8, 1.2)
            logger.warning(
                f"Site returned an error/rate-limit page. Backing off {int(wait)}s "
                f"before the next check."
            )
            _sleep_with_countdown(wait, checks)
            backoff = min(backoff * 2, BACKOFF_MAX)
        else:
            backoff = BACKOFF_START  # healthy page — reset the penalty
            burst = _in_burst_window(open_at)
            gap = burst_interval() if burst else random_poll_interval()
            _sleep_with_countdown(gap, checks, burst=burst)

        try:
            driver.refresh()
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except (TimeoutException, WebDriverException) as e:
            logger.warning(f"Refresh failed: {e} — doing a full load.")
            _load(driver, url)
