# booker.py
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from config import SELECT_MODULES_SELECTOR, CHECKBOX_SELECTOR, CONTINUE_BUTTON_SELECTOR, ELEMENT_TIMEOUT

logger = logging.getLogger(__name__)


def click_select_modules(driver) -> bool:
    """Re-find and JS-click the Select Modules button, then wait for the module-selection page."""
    try:
        # Re-query fresh — the element from poller may be stale after Vue re-renders
        btn = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECT_MODULES_SELECTOR))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        driver.execute_script("arguments[0].click();", btn)
        WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CHECKBOX_SELECTOR))
        )
        logger.info(f"Module-selection page loaded: {driver.current_url}")
        return True
    except (TimeoutException, WebDriverException) as e:
        logger.error(f"Failed to reach module-selection page: {e}")
        return False


def all_modules_available(driver) -> bool:
    """
    Return True only when all 4 checkboxes (reading, listening, writing, speaking)
    are present and none are disabled (disabled = fully booked).
    """
    checkboxes = driver.find_elements(By.CSS_SELECTOR, CHECKBOX_SELECTOR)
    if len(checkboxes) < 4:
        logger.warning(f"Only {len(checkboxes)} checkbox(es) found — expected 4.")
        return False
    disabled = [cb for cb in checkboxes if cb.get_attribute("disabled")]
    if disabled:
        ids = [cb.get_attribute("id").strip() for cb in disabled]
        logger.warning(f"Fully booked modules: {ids}")
        return False
    logger.info("All 4 modules available!")
    return True


def click_continue(driver) -> bool:
    """Click the CONTINUE button. Returns True on success."""
    try:
        btn = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, CONTINUE_BUTTON_SELECTOR))
        )
        driver.execute_script("arguments[0].click();", btn)
        logger.info(f"CONTINUE clicked → {driver.current_url}")
        return True
    except (TimeoutException, NoSuchElementException) as e:
        logger.error(f"CONTINUE button not found: {e}")
        return False


def run_booking(driver) -> bool:
    """
    Full booking sequence on the existing driver:
      1. Click 'Select Modules' (re-found fresh to avoid stale element)
      2. Verify all 4 modules are available
      3. Click 'Continue'
    Returns True if Continue was clicked successfully.
    """
    if not click_select_modules(driver):
        return False
    if not all_modules_available(driver):
        logger.warning("Not all modules available — browser left open for manual action.")
        return False
    return click_continue(driver)
