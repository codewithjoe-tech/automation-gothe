# config.py
import random

# Polling interval (seconds) — randomised to avoid bot detection
POLL_MIN = 2
POLL_MAX = 4

# Timeouts
PAGE_LOAD_TIMEOUT = 20
ELEMENT_TIMEOUT   = 15

# ── Selectors ────────────────────────────────────────────────────────────────
# "Select modules" green button on the exam detail page
SELECT_MODULES_SELECTOR = "a[onclick*='gotoExamDetail']"

# Checkboxes on the coe/options module-selection page
CHECKBOX_SELECTOR = "input.cs-checkbox__input"

# Continue button on the module-selection page
CONTINUE_BUTTON_SELECTOR = "button.cs-button--arrow_next"


def random_poll_interval() -> float:
    return random.uniform(POLL_MIN, POLL_MAX)
