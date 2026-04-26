# poller.py
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import SELECT_MODULES_SELECTOR, PAGE_LOAD_TIMEOUT

logger = logging.getLogger(__name__)


def get_select_modules_btn(driver):
    """Return the visible 'Select modules' button element, or None."""
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, SELECT_MODULES_SELECTOR)
        visible = [b for b in btns if b.is_displayed()]
        return visible[0] if visible else None
    except WebDriverException:
        return None


def _load(driver, url: str) -> bool:
    try:
        driver.get(url)
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        driver.execute_script("window.stop();")
        return True
    except (TimeoutException, WebDriverException) as e:
        logger.warning(f"Load failed: {e}")
        return False


def poll_until_open(driver, url: str, already_loaded: bool = False):
    """
    Refresh as fast as the page loads until 'Select modules' button appears.
    No artificial sleep — page load time is the only bottleneck.
    """
    if not already_loaded:
        logger.info(f"Loading: {url}")
        while not _load(driver, url):
            time.sleep(2)
    else:
        logger.info("Page pre-loaded — polling started.")

    checks = 0
    while True:
        checks += 1
        btn = get_select_modules_btn(driver)
        if btn:
            logger.info(f"'Select modules' button found on check #{checks} — booking is open!")
            return btn

        logger.info(f"[#{checks}] Not open. Refreshing…")
        try:
            driver.refresh()
            # Wait only until body is parsed — then stop loading remaining assets
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            driver.execute_script("window.stop();")
        except (TimeoutException, WebDriverException) as e:
            logger.warning(f"Refresh failed: {e} — falling back to full load…")
            _load(driver, url)
