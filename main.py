# main.py
import logging
import sys
import undetected_chromedriver as uc

from config import GOETHE_B2_URL
from poller import poll_until_slots
from booker import book_all_cities, check_all_boxes, click_submit
from notifier import fire_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log"),
    ]
)
logger = logging.getLogger(__name__)


def launch_driver():
    """Launch a visible undetected Chrome instance."""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options)
    driver.implicitly_wait(5)
    return driver


def run():
    logger.info("=" * 50)
    logger.info("Goethe B2 Booking Bot — Starting")
    logger.info(f"Target: {GOETHE_B2_URL}")
    logger.info("Press Ctrl+C to stop at any time.")
    logger.info("=" * 50)

    driver = launch_driver()

    try:
        # Step 1: Poll until slots appear
        booking_links = poll_until_slots(driver)

        # Step 2: Alert user immediately
        fire_alert()

        # Step 3: Open tabs and book all available cities
        if booking_links:
            book_all_cities(driver, booking_links)
        else:
            # Slots detected but no specific city links found —
            # fall back to booking directly from current page
            logger.warning("Slots detected but no city links extracted.")
            logger.warning("Attempting to book from current page...")
            check_all_boxes(driver)
            click_submit(driver)

        logger.info("=" * 50)
        logger.info("AUTOMATION COMPLETE.")
        logger.info("Chrome is staying open — log in manually to complete booking.")
        logger.info("Check all open tabs. Close this terminal when done.")
        logger.info("=" * 50)

        # Keep script alive so Chrome stays open
        input("\nPress ENTER to close Chrome and exit...\n")

    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    finally:
        # Do NOT call driver.quit() — user needs Chrome to stay open
        pass


if __name__ == "__main__":
    run()
