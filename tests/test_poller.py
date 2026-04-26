# tests/test_poller.py
from unittest.mock import MagicMock
from selenium.common.exceptions import WebDriverException
from poller import get_select_modules_btn


def _make_btn(displayed: bool):
    btn = MagicMock()
    btn.is_displayed.return_value = displayed
    return btn


def test_returns_none_when_no_buttons():
    driver = MagicMock()
    driver.find_elements.return_value = []
    assert get_select_modules_btn(driver) is None


def test_returns_none_when_all_hidden():
    driver = MagicMock()
    driver.find_elements.return_value = [_make_btn(False), _make_btn(False)]
    assert get_select_modules_btn(driver) is None


def test_returns_first_visible_button():
    driver = MagicMock()
    b1 = _make_btn(False)
    b2 = _make_btn(True)
    b3 = _make_btn(True)
    driver.find_elements.return_value = [b1, b2, b3]
    assert get_select_modules_btn(driver) is b2


def test_returns_none_on_webdriver_exception():
    driver = MagicMock()
    driver.find_elements.side_effect = WebDriverException("stale")
    assert get_select_modules_btn(driver) is None
