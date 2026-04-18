# poller.py
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import (
    GOETHE_B2_URL,
    NO_SLOTS_TEXTS,
    BOOKING_LINK_SELECTOR,
    PAGE_LOAD_TIMEOUT,
    random_poll_interval,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def slots_available(driver) -> bool:
    """
    Return True if booking slots are visible on the current page.
    Checks page_source for known 'no slots' messages.
    """
    page_text = driver.page_source.lower()
    for msg in NO_SLOTS_TEXTS:
        if msg.lower() in page_text:
            return False
    return True


def get_booking_links(driver) -> list[dict]:
    """
    Find all booking anchor elements on the page.
    Returns list of dicts: [{'href': str, 'text': str}, ...]
    """
    elements = driver.find_elements(By.CSS_SELECTOR, BOOKING_LINK_SELECTOR)
    links = []
    for el in elements:
        href = el.get_attribute("href") or ""
        text = el.text.strip()
        if href:
            links.append({"href": href, "text": text})
    return links


def load_page(driver) -> bool:
    """
    Navigate to the Goethe B2 page and wait for it to load.
    Returns True on success, False on timeout/error.
    """
    try:
        driver.get(GOETHE_B2_URL)
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return True
    except (TimeoutException, WebDriverException) as e:
        logger.error(f"Page load failed: {e}")
        return False


def poll_until_slots(driver) -> list[dict]:
    """
    Continuously refresh the page until slots are available.
    Returns the list of booking links once slots appear.
    """
    logger.info("Starting poll loop. Waiting for slots to open...")
    while True:
        loaded = load_page(driver)
        if not loaded:
            interval = random_poll_interval()
            logger.warning(f"Page failed to load. Retrying in {interval:.1f}s...")
            time.sleep(interval)
            continue

        if slots_available(driver):
            links = get_booking_links(driver)
            logger.info(f"SLOTS DETECTED! Found {len(links)} booking link(s).")
            return links
        else:
            interval = random_poll_interval()
            logger.info(f"No slots yet. Next check in {interval:.1f}s...")
            time.sleep(interval)
