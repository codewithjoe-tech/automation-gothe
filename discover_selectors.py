# discover_selectors.py
# Run this script to capture the fully JS-rendered page and discover real selectors.
# Usage: .venv\Scripts\python.exe discover_selectors.py
#
# Step 1: Loads the Goethe B2 page with Selenium (JS executes fully)
# Step 2: Saves rendered HTML to page_rendered.html for manual inspection
# Step 3: Prints all interactive elements found on the page
# Step 4: Optionally walks through the booking flow and saves each step

import time
import json
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TARGET_URL = "https://www.goethe.de/ins/in/en/spr/prf/gzb2.cfm"


def save_html(driver, filename: str):
    """Save the current fully-rendered page source to a file."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    logger.info(f"Saved rendered HTML → {filename}")


def dump_interactive_elements(driver) -> dict:
    """Find and print all interactive elements on the current page."""
    results = {
        "checkboxes": [],
        "submit_buttons": [],
        "links_with_booking": [],
        "all_inputs": [],
        "all_forms": [],
    }

    # --- Checkboxes ---
    checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
    for cb in checkboxes:
        info = {
            "tag": "input[checkbox]",
            "id": cb.get_attribute("id"),
            "name": cb.get_attribute("name"),
            "value": cb.get_attribute("value"),
            "class": cb.get_attribute("class"),
            "checked": cb.is_selected(),
            "visible": cb.is_displayed(),
        }
        results["checkboxes"].append(info)

    # --- Submit buttons ---
    submits = driver.find_elements(
        By.CSS_SELECTOR,
        "input[type='submit'], button[type='submit'], button"
    )
    for btn in submits:
        info = {
            "tag": btn.tag_name,
            "id": btn.get_attribute("id"),
            "name": btn.get_attribute("name"),
            "value": btn.get_attribute("value"),
            "text": btn.text.strip(),
            "class": btn.get_attribute("class"),
            "type": btn.get_attribute("type"),
            "visible": btn.is_displayed(),
        }
        results["submit_buttons"].append(info)

    # --- Links that look booking-related ---
    all_links = driver.find_elements(By.CSS_SELECTOR, "a")
    booking_keywords = ["anm", "book", "buchen", "register", "termin", "slot", "date"]
    for link in all_links:
        href = link.get_attribute("href") or ""
        text = link.text.strip()
        if any(kw in href.lower() or kw in text.lower() for kw in booking_keywords):
            info = {
                "text": text,
                "href": href,
                "id": link.get_attribute("id"),
                "class": link.get_attribute("class"),
                "visible": link.is_displayed(),
            }
            results["links_with_booking"].append(info)

    # --- All input elements ---
    all_inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
    for inp in all_inputs:
        info = {
            "tag": inp.tag_name,
            "type": inp.get_attribute("type"),
            "id": inp.get_attribute("id"),
            "name": inp.get_attribute("name"),
            "value": inp.get_attribute("value"),
            "class": inp.get_attribute("class"),
            "visible": inp.is_displayed(),
        }
        results["all_inputs"].append(info)

    # --- Forms ---
    forms = driver.find_elements(By.CSS_SELECTOR, "form")
    for form in forms:
        info = {
            "id": form.get_attribute("id"),
            "action": form.get_attribute("action"),
            "method": form.get_attribute("method"),
            "class": form.get_attribute("class"),
        }
        results["all_forms"].append(info)

    return results


def print_results(results: dict):
    print("\n" + "=" * 60)
    print("DISCOVERED ELEMENTS")
    print("=" * 60)

    print(f"\n[CHECKBOXES] ({len(results['checkboxes'])} found)")
    for i, cb in enumerate(results["checkboxes"], 1):
        print(f"  {i}. name={cb['name']!r}  id={cb['id']!r}  value={cb['value']!r}  class={cb['class']!r}  visible={cb['visible']}")

    print(f"\n[SUBMIT BUTTONS] ({len(results['submit_buttons'])} found)")
    for i, btn in enumerate(results["submit_buttons"], 1):
        print(f"  {i}. tag={btn['tag']!r}  type={btn['type']!r}  text={btn['text']!r}  value={btn['value']!r}  id={btn['id']!r}  class={btn['class']!r}  visible={btn['visible']}")

    print(f"\n[BOOKING-RELATED LINKS] ({len(results['links_with_booking'])} found)")
    for i, link in enumerate(results["links_with_booking"], 1):
        print(f"  {i}. text={link['text']!r}  href={link['href']!r}  class={link['class']!r}  visible={link['visible']}")

    print(f"\n[ALL INPUT ELEMENTS] ({len(results['all_inputs'])} found)")
    for i, inp in enumerate(results["all_inputs"], 1):
        print(f"  {i}. tag={inp['tag']!r}  type={inp['type']!r}  name={inp['name']!r}  id={inp['id']!r}  visible={inp['visible']}")

    print(f"\n[FORMS] ({len(results['all_forms'])} found)")
    for i, form in enumerate(results["all_forms"], 1):
        print(f"  {i}. id={form['id']!r}  action={form['action']!r}  method={form['method']!r}")

    print("\n" + "=" * 60)


def walk_booking_flow(driver):
    """
    Phase 2: After slots are visible, click through the booking journey
    and save the HTML at each step so you can capture all selectors.

    Run this manually when you can see booking links on the page.
    """
    print("\n[WALK MODE] Click on a booking link in Chrome, then press ENTER here...")
    input("Press ENTER after navigating to the booking/registration page...")

    save_html(driver, "page_booking_step1.html")
    results = dump_interactive_elements(driver)
    print_results(results)

    with open("selectors_step1.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Saved selectors → selectors_step1.json")

    print("\n[WALK MODE] Continue through the form (fill details if needed), then press ENTER...")
    input("Press ENTER after reaching the next page/step...")

    save_html(driver, "page_booking_step2.html")
    results2 = dump_interactive_elements(driver)
    print_results(results2)

    with open("selectors_step2.json", "w") as f:
        json.dump(results2, f, indent=2)
    logger.info("Saved selectors → selectors_step2.json")


def main():
    logger.info("Launching Chrome for selector discovery...")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)
    driver.implicitly_wait(5)

    try:
        # --- Phase 1: Load the main B2 page ---
        logger.info(f"Loading {TARGET_URL} ...")
        driver.get(TARGET_URL)

        # Wait for JS to render
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)  # extra wait for dynamic content to load

        # Save rendered HTML
        save_html(driver, "page_rendered.html")

        # Dump all interactive elements
        results = dump_interactive_elements(driver)
        print_results(results)

        # Save to JSON for easy reference
        with open("selectors_main.json", "w") as f:
            json.dump(results, f, indent=2)
        logger.info("Saved selectors → selectors_main.json")

        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("  1. Open page_rendered.html in a browser to inspect the DOM")
        print("  2. If booking links are visible above, note their hrefs")
        print("  3. To walk through the booking flow, press ENTER below")
        print("  4. To exit, press Ctrl+C")
        print("=" * 60)

        choice = input("\nWalk through booking flow? (y/n): ").strip().lower()
        if choice == "y":
            walk_booking_flow(driver)

        input("\nDone. Press ENTER to close Chrome...")

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
