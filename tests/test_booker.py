# tests/test_booker.py
from unittest.mock import MagicMock, patch, call
from booker import open_tab, check_all_boxes, click_submit, book_city


def make_driver():
    driver = MagicMock()
    driver.window_handles = ["tab0"]
    driver.current_window_handle = "tab0"
    return driver


def test_open_tab_executes_window_open():
    """open_tab should call execute_script with window.open."""
    driver = make_driver()
    open_tab(driver)
    driver.execute_script.assert_called_with("window.open('');")


def test_open_tab_switches_to_new_handle():
    """open_tab should switch to the newest window handle."""
    driver = make_driver()
    driver.window_handles = ["tab0", "tab1"]
    open_tab(driver)
    driver.switch_to.window.assert_called_with("tab1")


def test_check_all_boxes_checks_unchecked_boxes():
    """check_all_boxes should click each unchecked checkbox."""
    driver = MagicMock()
    cb1 = MagicMock()
    cb1.is_selected.return_value = False
    cb2 = MagicMock()
    cb2.is_selected.return_value = True  # already checked
    cb3 = MagicMock()
    cb3.is_selected.return_value = False
    driver.find_elements.return_value = [cb1, cb2, cb3]

    count = check_all_boxes(driver)

    cb1.click.assert_called_once()
    cb2.click.assert_not_called()  # already selected, skip
    cb3.click.assert_called_once()
    assert count == 2  # 2 boxes were clicked


def test_check_all_boxes_returns_zero_when_none_found():
    """check_all_boxes returns 0 if no checkboxes on page."""
    driver = MagicMock()
    driver.find_elements.return_value = []
    count = check_all_boxes(driver)
    assert count == 0


def test_click_submit_returns_true_on_success():
    """click_submit returns True when submit button is found and clicked."""
    driver = MagicMock()
    mock_btn = MagicMock()
    driver.find_element.return_value = mock_btn
    result = click_submit(driver)
    assert result is True
    mock_btn.click.assert_called_once()


def test_click_submit_returns_false_when_not_found():
    """click_submit returns False when no submit button exists."""
    from selenium.common.exceptions import NoSuchElementException
    driver = MagicMock()
    driver.find_element.side_effect = NoSuchElementException("no button")
    result = click_submit(driver)
    assert result is False
