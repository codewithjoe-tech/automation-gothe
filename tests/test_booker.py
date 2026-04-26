# tests/test_booker.py
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from booker import all_modules_available, click_continue


def _make_checkbox(disabled: bool, id_val: str = "mod"):
    cb = MagicMock()
    cb.get_attribute.side_effect = lambda attr: id_val if attr == "id" else ("disabled" if disabled else None)
    return cb


def test_all_available_when_none_disabled():
    driver = MagicMock()
    driver.find_elements.return_value = [
        _make_checkbox(False, " reading "),
        _make_checkbox(False, " listening "),
        _make_checkbox(False, " writing "),
        _make_checkbox(False, " speaking "),
    ]
    assert all_modules_available(driver) is True


def test_not_available_when_some_disabled():
    driver = MagicMock()
    driver.find_elements.return_value = [
        _make_checkbox(False, " reading "),
        _make_checkbox(False, " listening "),
        _make_checkbox(True, " writing "),
        _make_checkbox(True, " speaking "),
    ]
    assert all_modules_available(driver) is False


def test_not_available_when_fewer_than_4():
    driver = MagicMock()
    driver.find_elements.return_value = [_make_checkbox(False), _make_checkbox(False)]
    assert all_modules_available(driver) is False


def test_click_continue_returns_true_on_success():
    driver = MagicMock()
    mock_btn = MagicMock()
    with patch("booker.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.return_value = mock_btn
        result = click_continue(driver)
    assert result is True
    driver.execute_script.assert_called_once()


def test_click_continue_returns_false_on_timeout():
    driver = MagicMock()
    with patch("booker.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.side_effect = TimeoutException()
        result = click_continue(driver)
    assert result is False
