"""
Per-browser-instance worker.

Each instance:
  - Owns its own Chrome profile directory (chrome-profile-<idx>/)
  - Polls its assigned URL until Select Modules appears
  - Requests a new Tor circuit (or RotatingProxy hop) before each refresh
  - Books the exam (Select Modules → checkboxes → Continue)
  - Sets success_event when it succeeds, then keeps the browser open for login
"""
import os
import shutil
import time
import logging
import threading

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from booker import run_booking
from notifier import fire_alert
from config import CHROME_VERSION, PAGE_LOAD_TIMEOUT, SELECT_MODULES_SELECTOR

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_BLOCKED_URLS = [
    "*.css", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg",
    "*.woff", "*.woff2", "*.ttf", "*.eot", "*.webp", "*.ico",
    "*google-analytics.com*", "*googletagmanager.com*",
    "*googleadservices.com*", "*google.com/rmkt*",
    "*google.com/ccm*", "*analytics.google.com*",
    "*linkedin.com*", "*usercentrics.eu*",
    "*ppcprotect.com*", "*/N_O5Ke/*",
]


_BASE_DRIVER: str | None = None


def prepare_chromedriver() -> str:
    """
    Download/patch chromedriver ONCE, before any instance starts.
    undetected_chromedriver otherwise re-writes one shared file on every launch, which kills
    the chromedriver another instance is running from. Each instance gets its own copy instead.
    """
    global _BASE_DRIVER
    from undetected_chromedriver.patcher import Patcher
    patcher = Patcher(version_main=CHROME_VERSION or 0)
    patcher.auto()
    _BASE_DRIVER = patcher.executable_path
    for name in os.listdir(_SCRIPT_DIR):            # drop stale per-instance copies
        if name.startswith("chromedriver-"):
            try:
                os.remove(os.path.join(_SCRIPT_DIR, name))
            except OSError:
                pass
    return _BASE_DRIVER


def _instance_driver(idx: int) -> str | None:
    """Private copy of the patched chromedriver for instance idx."""
    if not _BASE_DRIVER:
        return None
    dst = os.path.join(_SCRIPT_DIR, f"chromedriver-{idx}")
    if not os.path.exists(dst):
        shutil.copy2(_BASE_DRIVER, dst)
        os.chmod(dst, 0o755)
    return dst


def _profile_dir(idx: int) -> str:
    path = os.path.join(_SCRIPT_DIR, f"chrome-profile-{idx}")
    os.makedirs(path, exist_ok=True)
    return path


def _cleanup_locks(profile: str) -> None:
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"):
        p = os.path.join(profile, name)
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


def _launch_driver(idx: int, proxy: str | None):
    profile = _profile_dir(idx)
    _cleanup_locks(profile)

    opts = uc.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(f"--user-data-dir={profile}")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-background-networking")

    if proxy:
        opts.add_argument(f"--proxy-server={proxy}")

    kwargs = {"options": opts}
    if CHROME_VERSION:
        kwargs["version_main"] = CHROME_VERSION
    driver_exe = _instance_driver(idx)
    if driver_exe:
        kwargs["driver_executable_path"] = driver_exe

    drv = uc.Chrome(**kwargs)
    drv.implicitly_wait(0)
    drv.execute_cdp_cmd("Network.enable", {})
    drv.execute_cdp_cmd("Network.setBlockedURLs", {"urls": _BLOCKED_URLS})
    return drv


def _get_select_modules_btn(driver):
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, SELECT_MODULES_SELECTOR)
        visible = [b for b in btns if b.is_displayed()]
        return visible[0] if visible else None
    except WebDriverException:
        return None


def _load_page(driver, url: str, idx: int, log, tor_manager=None) -> bool:
    """Load url, optionally rotating Tor circuit first. Returns True on success."""
    try:
        if tor_manager:
            tor_manager.new_circuit(idx)
        driver.get(url)
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        driver.execute_script("window.stop();")
        return True
    except (TimeoutException, WebDriverException) as e:
        log.warning(f"Page load failed: {e}")
        return False


def _new_ip(proxy_server, log) -> None:
    """Drop open proxy tunnels so the next request opens a new connection (= new IP)."""
    if proxy_server:
        n = proxy_server.drop_connections()
        log.debug(f"Dropped {n} tunnel(s) for a fresh IP.")
        time.sleep(0.1)  # let Chrome notice its pooled sockets are gone


def _poll_loop(driver, url: str, idx: int, log,
               tor_manager, stop_event: threading.Event,
               already_loaded: bool, proxy_server=None) -> bool:
    """
    Keep refreshing until Select Modules button appears.
    Returns True when found, False when stop_event fires.
    """
    if not already_loaded:
        while not stop_event.is_set():
            _new_ip(proxy_server, log)
            if _load_page(driver, url, idx, log, tor_manager):
                break
            time.sleep(2)

    checks = 0
    while not stop_event.is_set():
        checks += 1
        btn = _get_select_modules_btn(driver)
        if btn:
            log.info(f"SELECT MODULES found on check #{checks} — OPEN!")
            return True

        log.info(f"#{checks} Not open — refreshing…")
        try:
            if tor_manager:
                tor_manager.new_circuit(idx)
            _new_ip(proxy_server, log)
            driver.refresh()
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            driver.execute_script("window.stop();")
        except (TimeoutException, WebDriverException) as e:
            log.warning(f"Refresh failed: {e} — doing full load")
            _new_ip(proxy_server, log)
            _load_page(driver, url, idx, log, tor_manager)

    return False  # stop_event fired


def run_instance(
    idx: int,
    url: str,
    proxy: str | None,
    stop_event: threading.Event,
    success_event: threading.Event,
    tor_manager=None,
    proxy_server=None,
) -> None:
    log = logging.getLogger(f"instance.{idx}")
    log.info(f"Starting  url={url}  proxy={proxy or 'direct'}")

    driver = None
    for attempt in range(1, 4):
        try:
            driver = _launch_driver(idx, proxy)
            break
        except Exception as e:
            log.warning(f"Chrome launch attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                time.sleep(3)

    if driver is None:
        log.error("Chrome failed to launch after 3 attempts — this instance exiting.")
        return

    try:
        # Pre-load page so it's ready when booking opens
        log.info("Pre-loading page…")
        driver.get(url)

        first_attempt = True
        while not stop_event.is_set():
            if success_event.is_set():
                log.info("Another instance already booked — stopping.")
                break

            # Phase 1 — poll
            found = _poll_loop(
                driver, url, idx, log,
                tor_manager, stop_event,
                already_loaded=first_attempt,
                proxy_server=proxy_server,
            )
            first_attempt = False

            if not found or stop_event.is_set():
                break

            if success_event.is_set():
                log.info("Another instance already booked — stopping.")
                break

            # Background: the beeps take ~1.5 s and must not delay the booking click.
            threading.Thread(target=fire_alert, daemon=True).start()

            # Re-enable full resources so checkout pages render
            driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": []})
            log.info("Resource blocking lifted.")

            # Phase 2 — book
            success = run_booking(driver)

            if success:
                log.info("=" * 50)
                log.info(f"MODULE PAGE REACHED on instance #{idx}!")
                log.info("The bot is done — choose modules and continue manually in this Chrome window.")
                log.info("=" * 50)
                success_event.set()
                # Stay alive while the user completes the booking by hand
                while not stop_event.is_set():
                    time.sleep(5)
                break

            # False — checkboxes not detected → back to the user's URL, repoll
            log.warning("Checkboxes not detected — going back to the provided URL and re-polling…")
            driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": _BLOCKED_URLS})
            # No driver.get here: _poll_loop (already_loaded=False) switches IP, then loads the URL.
            continue

    except Exception as e:
        if stop_event.is_set():
            log.info("Stopping — browser closed while a command was running.")
        else:
            log.error(f"Fatal error: {e}", exc_info=True)
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        log.info("Instance stopped.")
