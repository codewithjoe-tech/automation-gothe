# tests/test_poller.py
from unittest.mock import MagicMock, patch
from poller import slots_available, get_booking_links


def make_driver(page_text: str) -> MagicMock:
    """Helper: create a mock Selenium driver returning given page text."""
    driver = MagicMock()
    driver.page_source = page_text
    return driver


def test_slots_not_available_when_no_dates_message():
    """Returns False when the 'cannot be displayed' message is present."""
    driver = make_driver("<p>Sorry, our dates cannot be displayed temporarily.</p>")
    assert slots_available(driver) is False


def test_slots_not_available_when_try_again_message():
    """Returns False when 'try again later' is on the page."""
    driver = make_driver("<p>Please try again later.</p>")
    assert slots_available(driver) is False


def test_slots_available_when_no_error_message():
    """Returns True when neither 'no slots' message is present."""
    driver = make_driver("<table><tr><td>2026-06-01</td><td><a href='/book'>Book</a></td></tr></table>")
    assert slots_available(driver) is True


def test_get_booking_links_returns_list():
    """get_booking_links returns a list (empty or populated)."""
    driver = MagicMock()
    driver.find_elements.return_value = []
    result = get_booking_links(driver)
    assert isinstance(result, list)


def test_get_booking_links_returns_href_and_text():
    """get_booking_links returns dicts with 'href' and 'text' keys."""
    mock_el = MagicMock()
    mock_el.get_attribute.return_value = "/ins/in/en/spr/anm.cfm?city=mumbai"
    mock_el.text = "Mumbai - 2026-06-01"
    driver = MagicMock()
    driver.find_elements.return_value = [mock_el]
    result = get_booking_links(driver)
    assert len(result) == 1
    assert "href" in result[0]
    assert "text" in result[0]
