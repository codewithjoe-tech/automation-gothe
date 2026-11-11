# config.py
import os
import random
from dotenv import load_dotenv

load_dotenv()

# ── Selectors ─────────────────────────────────────────────────────────────────
SELECT_MODULES_SELECTOR  = "a[onclick*='gotoExamDetail']"
CHECKBOX_SELECTOR        = "input.cs-checkbox__input"
CONTINUE_BUTTON_SELECTOR = "button.cs-button--arrow_next"

# ── Timeouts (seconds) ────────────────────────────────────────────────────────
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "20"))
ELEMENT_TIMEOUT   = int(os.getenv("ELEMENT_TIMEOUT",   "15"))

# ── Polling ───────────────────────────────────────────────────────────────────
POLL_MIN = float(os.getenv("POLL_MIN", "2"))
POLL_MAX = float(os.getenv("POLL_MAX", "4"))

# ── Chrome ────────────────────────────────────────────────────────────────────
# None = let undetected_chromedriver auto-detect your installed Chrome version
_cv = os.getenv("CHROME_VERSION", "").strip()
CHROME_VERSION: int | None = int(_cv) if _cv else None

# ── Proxy ─────────────────────────────────────────────────────────────────────
PROXY_MODE       = os.getenv("PROXY_MODE", "none").lower().strip()
DATAIMPULSE_HOST = os.getenv("DATAIMPULSE_HOST", "proxy.dataimpulse.com")
DATAIMPULSE_PORT = int(os.getenv("DATAIMPULSE_PORT", "823"))
DATAIMPULSE_USER = os.getenv("DATAIMPULSE_USER", "")
DATAIMPULSE_PASS = os.getenv("DATAIMPULSE_PASS", "")

# Premium plan, used when RUN_MODE=booking (DATAIMPULSE_* above is the test plan, e.g. Residential).
# Host/port fall back to the test plan's if left blank.
DATAIMPULSE_BOOKING_HOST = os.getenv("DATAIMPULSE_BOOKING_HOST", "").strip() or DATAIMPULSE_HOST
DATAIMPULSE_BOOKING_PORT = int(os.getenv("DATAIMPULSE_BOOKING_PORT", "").strip() or DATAIMPULSE_PORT)
DATAIMPULSE_BOOKING_USER = os.getenv("DATAIMPULSE_BOOKING_USER", "").strip()
DATAIMPULSE_BOOKING_PASS = os.getenv("DATAIMPULSE_BOOKING_PASS", "").strip()
RUN_MODE         = os.getenv("RUN_MODE", "test").lower().strip()   # test | booking

# ── Tor ───────────────────────────────────────────────────────────────────────
TOR_PATH         = os.getenv("TOR_PATH", "").strip()
TOR_CONTROL_PASS = os.getenv("TOR_CONTROL_PASS", "").strip()

# ── Multi-instance defaults ───────────────────────────────────────────────────
INSTANCES  = int(os.getenv("INSTANCES", "1"))
EXAM_URLS  = [u.strip() for u in os.getenv("EXAM_URLS", "").split(",") if u.strip()]
OPEN_TIME  = os.getenv("OPEN_TIME", "").strip()


def random_poll_interval() -> float:
    return random.uniform(POLL_MIN, POLL_MAX)
