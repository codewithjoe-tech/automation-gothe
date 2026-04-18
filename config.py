# config.py
import random

# Target URL
GOETHE_B2_URL = "https://www.goethe.de/ins/in/en/spr/prf/gzb2.cfm"

# Polling interval bounds (seconds)
POLL_MIN = 10
POLL_MAX = 30

# Page load wait timeout (seconds)
PAGE_LOAD_TIMEOUT = 20


# Element wait timeout (seconds)
ELEMENT_TIMEOUT = 10

# Text present on page when NO slots are available
NO_SLOTS_TEXTS = [
    "cannot be displayed temporarily",
    "dates cannot be displayed",
    "try again later",
    "keine Termine",  # German fallback
]

# CSS selectors / XPaths for booking elements
# NOTE: These are best-guess selectors based on Goethe site structure.
# Inspect the live page when slots open and update if needed.
BOOKING_LINK_SELECTOR = "a[href*='anm'], a[href*='booking'], a[href*='buchen'], .booking-link, td a"
CHECKBOX_SELECTORS = [
    "input[type='checkbox'][name*='skill']",
    "input[type='checkbox'][name*='modul']",
    "input[type='checkbox'][name*='pruefung']",
    "input[type='checkbox']",  # fallback: all checkboxes
]
SUBMIT_BUTTON_SELECTOR = "input[type='submit'], button[type='submit'], .submit-btn, input[value*='Book'], input[value*='Proceed']"

# Cities to target (all India locations)
TARGET_CITIES = [
    "bangalore",
    "chennai",
    "kolkata",
    "mumbai",
    "new delhi",
    "pune",
    "chandigarh",
    "coimbatore",
    "hyderabad",
    "trivandrum",
    "kochi",
]


def random_poll_interval():
    """Return a random interval between POLL_MIN and POLL_MAX seconds."""
    return random.uniform(POLL_MIN, POLL_MAX)


def random_click_delay():
    """Return a small human-like delay between actions (0.3–0.8s)."""
    return random.uniform(0.3, 0.8)
