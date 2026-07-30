# booker.py
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from config import SELECT_MODULES_SELECTOR, CHECKBOX_SELECTOR, CONTINUE_BUTTON_SELECTOR, ELEMENT_TIMEOUT

logger = logging.getLogger(__name__)

# URL fragment that identifies the "high demand" error page
_ERROR_PAGE_MARKER = "wicket/page"


def is_error_page(driver) -> bool:
    """Return True if the browser hit a known bad page (high-demand or 403 Forbidden)."""
    if _ERROR_PAGE_MARKER in driver.current_url:
        return True
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        if "Forbidden" in body or "forbidden" in body:
            return True
    except Exception:
        pass
    return False


def click_select_modules(driver) -> bool:
    """Re-find and JS-click the Select Modules button, then wait for the module-selection page."""
    try:
        # Re-query fresh — the element from poller may be stale after Vue re-renders
        btn = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECT_MODULES_SELECTOR))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        driver.execute_script("arguments[0].click();", btn)

        # Wait until either the checkboxes appear OR the error page loads (whichever comes first)
        try:
            WebDriverWait(driver, ELEMENT_TIMEOUT).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, CHECKBOX_SELECTOR) or is_error_page(d)
            )
        except TimeoutException:
            pass  # fall through to the error-page check below

        if is_error_page(driver):
            logger.warning(f"'High demand' error page detected — will navigate back and retry. URL: {driver.current_url}")
            return False

        logger.info(f"Module-selection page loaded: {driver.current_url}")
        return True
    except (TimeoutException, WebDriverException) as e:
        if is_error_page(driver):
            logger.warning(f"'High demand' error page detected (exception path). URL: {driver.current_url}")
            return False
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


def run_booking(driver):
    """
    Full booking sequence on the existing driver.
    Returns:
      True  — Continue clicked (all modules were available)
      None  — partial availability; browser left on module page for user to choose manually
      False — error page / couldn't reach module page; caller should repoll
    """
    if not click_select_modules(driver):
        return False
    checkboxes = driver.find_elements(By.CSS_SELECTOR, CHECKBOX_SELECTOR)
    if not checkboxes:
        logger.warning("No checkboxes found on module page — treating as error, will repoll.")
        return False
    if all_modules_available(driver):
        return click_continue(driver)
    logger.info("Some modules unavailable — leaving browser on module page for manual selection.")
    return None
