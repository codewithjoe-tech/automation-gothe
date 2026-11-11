# booker.py
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import SELECT_MODULES_SELECTOR, CHECKBOX_SELECTOR, ELEMENT_TIMEOUT

logger = logging.getLogger(__name__)


def click_select_modules(driver) -> bool:
    """
    JS-click the Select Modules button and wait for the module checkboxes.
    Returns True if checkboxes appeared, False otherwise (caller goes back to the user's URL).
    """
    try:
        # Re-query fresh — the element from poller may be stale after Vue re-renders
        btn = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECT_MODULES_SELECTOR))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        driver.execute_script("arguments[0].click();", btn)

        WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, CHECKBOX_SELECTOR)
        )
        logger.info(f"Module-selection page loaded: {driver.current_url}")
        return True
    except (TimeoutException, WebDriverException) as e:
        logger.warning(f"Checkboxes not detected after Select Modules ({driver.current_url}): {e}")
        return False


def run_booking(driver) -> bool:
    """
    Click Select Modules and wait for the module-selection page (the checkboxes).
    Returns True once that page is reached: the bot's job ends there and the user takes over
    in this window, whatever modules are available.
    Returns False when the checkboxes don't show up; the caller goes back to the user's URL
    and polls again.
    """
    return click_select_modules(driver)
