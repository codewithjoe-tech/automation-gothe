# config.py
import os
import random
from dotenv import load_dotenv

load_dotenv()

# ── Selectors (verified against the live page) ────────────────────────────────
SELECT_MODULES_SELECTOR  = "a[onclick*='gotoExamDetail']"
CHECKBOX_SELECTOR        = "input.cs-checkbox__input"
CONTINUE_BUTTON_SELECTOR = "button.cs-button--arrow_next"

# ── Timeouts (seconds) ────────────────────────────────────────────────────────
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))
ELEMENT_TIMEOUT   = int(os.getenv("ELEMENT_TIMEOUT",   "15"))

# ── Polling (watcher) ─────────────────────────────────────────────────────────
# Human-paced: one look per minute-ish. Used by poller.py / the watcher.
POLL_MIN = float(os.getenv("POLL_MIN", "30"))
POLL_MAX = float(os.getenv("POLL_MAX", "60"))

# Backoff when the site errors or rate-limits us.
BACKOFF_START = float(os.getenv("BACKOFF_START", "120"))
BACKOFF_MAX   = float(os.getenv("BACKOFF_MAX",   "900"))

# ── Burst window around a known open time ─────────────────────────────────────
# Checks faster for a short window either side of OPEN_TIME, the way a person
# refreshing at a known release time does. Rate tuning only.
BURST_WINDOW = float(os.getenv("BURST_WINDOW", "120"))   # seconds either side
BURST_MIN    = float(os.getenv("BURST_MIN",    "3"))
BURST_MAX    = float(os.getenv("BURST_MAX",    "6"))

# ── Optional phone push (https://ntfy.sh) ─────────────────────────────────────
# Leave blank to disable. Pick a hard-to-guess topic name, subscribe to it in
# the ntfy app, and set NTFY_TOPIC to the same string. Only "slots open" and the
# exam URL are ever sent.
NTFY_TOPIC  = os.getenv("NTFY_TOPIC", "").strip()
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")

# ── Chrome ────────────────────────────────────────────────────────────────────
# Blank = let the driver auto-detect the installed Chrome. Only undetected-
# chromedriver needs this pinned; plain Selenium resolves it via Selenium Manager.
_cv = os.getenv("CHROME_VERSION", "").strip()
CHROME_VERSION = int(_cv) if _cv else None

# ── Run defaults ──────────────────────────────────────────────────────────────
EXAM_URL  = os.getenv("EXAM_URL", "").strip()
OPEN_TIME = os.getenv("OPEN_TIME", "").strip()

# ── Legacy: multi-instance / proxy / Tor ──────────────────────────────────────
# Read by instance.py, proxy.py, rotating_proxy.py and tor_manager.py, which are
# kept in the tree but are NOT on the watcher's run path. See RUNNING.md.
INSTANCES = int(os.getenv("INSTANCES", "1"))
EXAM_URLS = [u.strip() for u in os.getenv("EXAM_URLS", "").split(",") if u.strip()]

PROXY_MODE       = os.getenv("PROXY_MODE", "none").lower().strip()
DATAIMPULSE_HOST = os.getenv("DATAIMPULSE_HOST", "proxy.dataimpulse.com")
DATAIMPULSE_PORT = int(os.getenv("DATAIMPULSE_PORT", "823"))
DATAIMPULSE_USER = os.getenv("DATAIMPULSE_USER", "")
DATAIMPULSE_PASS = os.getenv("DATAIMPULSE_PASS", "")

TOR_PATH         = os.getenv("TOR_PATH", "").strip()
TOR_CONTROL_PASS = os.getenv("TOR_CONTROL_PASS", "").strip()


def random_poll_interval() -> float:
    """Jittered gap between checks, so the rhythm isn't robotically uniform."""
    return random.uniform(POLL_MIN, POLL_MAX)


def burst_interval() -> float:
    return random.uniform(BURST_MIN, BURST_MAX)
