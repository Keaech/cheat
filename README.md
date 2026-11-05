# Text Entry Assistant

A small Windows desktop utility for entering text into a window you select and focus yourself. It uses a fixed, user-selected typing speed and includes a countdown and cancellation controls. It does not add simulated typos or random timing intended to make automation look like a person.

## Intended use and limitations

Use this only where you are authorized to enter the text and where automated input is permitted. It sends keystrokes to whichever window currently has focus; check the target carefully before starting. Press **Esc** or **Stop** to cancel. The application does not identify or switch target windows.

This is currently a local desktop application, not a SaaS: it has no accounts, server, payments, or cloud storage. Do not enter sensitive information unless you understand the behavior of your operating system and target application.

## Requirements

- Windows (the input engine uses the Windows API)
- Python 3.10 or later
- Tkinter, usually included with the standard Windows Python installer

Install the third-party dependency and run:

```powershell
python -m pip install -r requirements.txt
cd cheat
python main.py
```

Enter text, set a speed from 1 to 600 WPM, focus the intended text field, and click **Start**. The app waits three seconds before entering text. Escape or the Stop button requests cancellation.

## Development

Run the unit tests from the repository root:

```powershell
python -m unittest discover -s tests -v
```

The pacing helper is deterministic and can be tested without sending keystrokes. Keep tests for UI-independent logic separate from tests that would interact with real windows.
