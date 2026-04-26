# find_api.py
# Intercepts every XHR/fetch call the Vue app makes and prints them.
# Run this once to find the slot-status API endpoint.
# Usage: python find_api.py

import time
import json
import os
import sys
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "chrome-profile")

print("\n" + "=" * 60)
print("  API Endpoint Finder")
print("=" * 60)
url = input("Paste exam URL: ").strip()
if not url.startswith("http"):
    print("Invalid URL.")
    sys.exit(1)

# JS injected before page load — monkey-patches XHR + fetch to log every call
INTERCEPTOR_JS = """
window._apiLog = [];

const _origXHROpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(method, url) {
    window._apiLog.push({ type: 'XHR', method: method, url: String(url) });
    return _origXHROpen.apply(this, arguments);
};

const _origFetch = window.fetch;
window.fetch = function(input, init) {
    const u = (typeof input === 'string') ? input : input.url;
    const m = (init && init.method) ? init.method : 'GET';
    window._apiLog.push({ type: 'Fetch', method: m, url: String(u) });
    return _origFetch.apply(this, arguments);
};
"""

print("\nLaunching Chrome…")
opts = uc.ChromeOptions()
opts.add_argument("--start-maximized")
opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
driver = uc.Chrome(options=opts, version_main=147)

# Inject interceptor so it runs before any page script
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": INTERCEPTOR_JS})

print(f"Loading page…")
driver.get(url)
WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
time.sleep(4)  # let Vue finish initial API calls

def dump_log(label: str):
    entries = driver.execute_script("return window._apiLog || [];")
    driver.execute_script("window._apiLog = [];")  # clear for next round
    seen = set()
    results = []
    for e in entries:
        key = f"{e['method']} {e['url']}"
        if key not in seen:
            seen.add(key)
            results.append(e)
    print(f"\n{'='*60}")
    print(f"  {label} — {len(results)} unique call(s):")
    print("=" * 60)
    for e in results:
        print(f"  [{e['type']:5} {e['method']:6}] {e['url']}")
    return results

dump_log("Initial page load")

print("\nRefreshing page to capture calls on reload…")
driver.refresh()
time.sleep(4)
dump_log("After refresh")

print("\n" + "="*60)
print("  Done. Look for calls to .cfm, /api/, /coe/, or similar.")
print("  These are the endpoints to poll directly.")
print("="*60)
print("\nPress Ctrl+C to close Chrome.")
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    driver.quit()
