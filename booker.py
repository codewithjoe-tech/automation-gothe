# booker.py
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

from config import (
    CHECKBOX_SELECTORS,
    SUBMIT_BUTTON_SELECTOR,
    ELEMENT_TIMEOUT,
    random_click_delay,
)

logger = logging.getLogger(__name__)


def open_tab(driver) -> str:
    """
    Open a new browser tab and switch to it.
    Returns the handle of the new tab.
    """
    driver.execute_script("window.open('');")
    new_handle = driver.window_handles[-1]
    driver.switch_to.window(new_handle)
    return new_handle


def check_all_boxes(driver) -> int:
    """
    Find all checkboxes on the page and check any that are unchecked.
    Tries each selector in CHECKBOX_SELECTORS until boxes are found.
    Returns the number of boxes that were clicked.
    """
    checkboxes = []
    for selector in CHECKBOX_SELECTORS:
        checkboxes = driver.find_elements(By.CSS_SELECTOR, selector)
        if checkboxes:
            break

    clicked = 0
    for cb in checkboxes:
        try:
            if not cb.is_selected():
                time.sleep(random_click_delay())
                cb.click()
                clicked += 1
        except WebDriverException as e:
            logger.warning(f"Could not click checkbox: {e}")

    logger.info(f"Checked {clicked} checkbox(es) out of {len(checkboxes)} found.")
    return clicked


def click_submit(driver) -> bool:
    """
    Find and click the submit/proceed button.
    Returns True on success, False if not found.
    """
    try:
        btn = driver.find_element(By.CSS_SELECTOR, SUBMIT_BUTTON_SELECTOR)
        time.sleep(random_click_delay())
        btn.click()
        logger.info("Submit button clicked.")
        return True
    except NoSuchElementException:
        logger.warning("Submit button not found — leaving tab open for manual action.")
        return False


def book_city(driver, booking_url: str, city_label: str):
    """
    Open a new tab, navigate to booking_url, check all boxes, and submit.
    Tab stays open regardless of outcome.
    """
    logger.info(f"Booking city: {city_label} → {booking_url}")
    handle = open_tab(driver)

    try:
        driver.get(booking_url)
        WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        checked = check_all_boxes(driver)
        if checked == 0:
            logger.warning(f"No checkboxes found on {city_label} tab — manual action needed.")
        click_submit(driver)
    except (TimeoutException, WebDriverException) as e:
        logger.error(f"Error booking {city_label}: {e} — tab left open.")

    return handle


def book_all_cities(driver, booking_links: list[dict]):
    """
    Open one tab per booking link and run the booking flow in each.
    Returns list of tab handles opened.
    """
    handles = []
    for link in booking_links:
        handle = book_city(driver, link["href"], link.get("text", link["href"]))
        handles.append(handle)

    logger.info(f"Booking complete. {len(handles)} tab(s) open at login screen.")
    return handles
