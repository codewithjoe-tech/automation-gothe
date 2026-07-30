"""
Diagnostic tool — captures live page HTML + screenshot.

Run this FIRST to verify/fix selectors.

Usage:
    python capture_html.py

It will:
  1. Open Chrome on the URL you paste
  2. Wait 5 s for Vue to finish rendering
  3. Save page_source.html + page_screenshot.png in this folder
  4. Tell you which selectors to search for in the HTML

If the selectors shown below don't exist in the saved HTML, update
SELECT_MODULES_SELECTOR / CHECKBOX_SELECTOR / CONTINUE_BUTTON_SELECTOR in config.py.
"""
import sys
import time
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import CHROME_VERSION, SELECT_MODULES_SELECTOR, CHECKBOX_SELECTOR, CONTINUE_BUTTON_SELECTOR

url = input("Paste exam URL to capture: ").strip()
if not url or not url.startswith("http"):
    print("Invalid URL.")
    sys.exit(1)

print("\nLaunching Chrome (no profile, clean session)…")
opts = uc.ChromeOptions()
opts.add_argument("--start-maximized")
opts.add_argument("--disable-blink-features=AutomationControlled")

kwargs = {"options": opts}
if CHROME_VERSION:
    kwargs["version_main"] = CHROME_VERSION

driver = uc.Chrome(**kwargs)

try:
    print(f"Loading: {url}")
    driver.get(url)
    WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("Waiting 5 s for Vue to render…")
    time.sleep(5)

    out = os.path.dirname(os.path.abspath(__file__))

    html_path = os.path.join(out, "page_source.html")
    with open(html_path, "w", encoding="utf-8", errors="replace") as f:
        f.write(driver.page_source)
    print(f"\nHTML saved  → {html_path}")

    png_path = os.path.join(out, "page_screenshot.png")
    driver.save_screenshot(png_path)
    print(f"Screenshot → {png_path}")

    # Quick selector check
    print("\n── Selector check ───────────────────────────────────────────")
    for label, sel in [
        ("SELECT_MODULES_SELECTOR",  SELECT_MODULES_SELECTOR),
        ("CHECKBOX_SELECTOR",        CHECKBOX_SELECTOR),
        ("CONTINUE_BUTTON_SELECTOR", CONTINUE_BUTTON_SELECTOR),
    ]:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        status = f"FOUND ({len(els)})" if els else "NOT FOUND"
        print(f"  {label:30s}  {sel:40s}  →  {status}")

    print("\nIf any selector shows NOT FOUND, open page_source.html in a browser,")
    print("inspect the booking button, and update config.py accordingly.")
    input("\nPress Enter to close Chrome…")

finally:
    driver.quit()
