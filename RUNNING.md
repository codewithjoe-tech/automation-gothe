# Goethe B2 Booking Bot — How to Run

## Prerequisites
- Python 3.10+
- Google Chrome installed
- uv installed (`pip install uv`)

## Setup (first time only)
```bash
uv pip install -r requirements.txt
```

## How to Run on Booking Day

1. Open a terminal in this folder
2. Run the bot a few minutes before booking opens:
   ```bash
   .venv\Scripts\python.exe main.py
   ```
3. Chrome will open and start refreshing the Goethe B2 page
4. When slots appear: sound alert fires, tabs open per city automatically
5. Log in on whichever tab you want and complete the booking manually

## If Checkboxes Aren't Found
The selectors in `config.py` are best-guess. On booking day:
1. Press F12 in Chrome → open DevTools
2. Click the inspector icon → click a checkbox
3. Copy its CSS selector
4. Update `CHECKBOX_SELECTORS` in `config.py`
5. Same for the submit button → update `SUBMIT_BUTTON_SELECTOR`

## Stop the Bot
Press `Ctrl+C` in the terminal at any time.
