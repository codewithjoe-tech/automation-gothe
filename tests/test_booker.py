# tests/test_booker.py
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import TimeoutException
from booker import click_select_modules, run_booking


def test_run_booking_true_when_module_page_reached():
    with patch("booker.click_select_modules", return_value=True):
        assert run_booking(MagicMock()) is True


def test_run_booking_false_when_checkboxes_missing():
    with patch("booker.click_select_modules", return_value=False):
        assert run_booking(MagicMock()) is False


def test_click_select_modules_true_when_checkboxes_appear():
    driver = MagicMock()
    with patch("booker.WebDriverWait") as wait:
        wait.return_value.until.return_value = True
        assert click_select_modules(driver) is True


def test_click_select_modules_false_when_checkboxes_never_appear():
    driver = MagicMock()
    with patch("booker.WebDriverWait") as wait:
        wait.return_value.until.side_effect = [MagicMock(), TimeoutException("no checkboxes")]
        assert click_select_modules(driver) is False
