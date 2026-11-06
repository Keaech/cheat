# Text Entry Assistant

Text Entry Assistant is a **Windows desktop app** that enters text into another app, such as Microsoft Word or a Google Docs document. You choose the text and speed, then focus the document before typing starts.

> **Important:** It types into the active window. Check where your cursor is before starting. Use it only where you have permission to automate text entry.

## What it can do

- Set typing speed in words per minute (WPM).
- Add pauses after sentences and between paragraphs.
- Show typing progress, characters typed, words remaining, estimated time, and approximate current speed.
- Pause, resume, or stop a session from the dashboard or with global keyboard shortcuts.
- Press **Esc** for an emergency stop.
- Import a UTF-8 `.txt` file.
- Save drafts and session progress locally, and show recent session history.
- Use the Belisio font if it is installed; otherwise, Windows uses a fallback font.

## Requirements

- Windows 10 or later
- Python 3.10 or later
- Tkinter (included with most Python installers for Windows)
- The dependency listed in `requirements.txt`

## Install and run in VS Code

1. Download or clone this repository and open its folder in VS Code.
2. Open **Terminal → New Terminal**. Make sure the terminal is at the repository root—the folder containing `requirements.txt`.
3. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. Run the tests:

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

5. Launch the app:

   ```powershell
   .\.venv\Scripts\python.exe .\cheat\main.py
   ```

If you do not want to use a virtual environment, you can install the dependency with `python -m pip install -r requirements.txt` and launch with `python .\cheat\main.py`.

## Enter text into Word or Google Docs

1. Open a document and put the cursor where the text should go.
2. Enter or import text in Text Entry Assistant.
3. Choose WPM and any sentence or paragraph pauses.
4. Click **Start**. During the three-second countdown, switch to the document and click in its editing area.
5. Keep the document as the active window while typing.

The app captures the foreground window after the countdown. If you switch to another application, it pauses for focus protection and resumes when you return to that same window. It will not intentionally type into the Text Entry Assistant window.

**Browser limitation:** Google Docs runs inside a browser. Windows exposes the browser window, not a dependable identity for each tab or web editor. This app cannot reliably tell whether the active browser tab is still the intended Google Docs document. Avoid switching browser tabs while typing. A browser extension would be needed for reliable tab-level targeting.

## Controls and shortcuts

- **Start / Pause:** use the dashboard buttons or the configured start/pause shortcut.
- **Stop:** click **Stop** or press **Esc**. Escape is intended as an emergency stop while a session is running.
- **Change speed:** use the configured faster/slower shortcuts while typing.
- **Customize shortcuts:** open **Hotkeys** in the app and enter shortcut strings in `pynput` format. Defaults are:
  - Start/pause: ` <ctrl>+<alt>+<space>`
  - Stop: `<ctrl>+<alt>+x`
  - Faster: `<ctrl>+<alt>+<up>`
  - Slower: `<ctrl>+<alt>+<down>`

Global shortcuts may conflict with Windows or other apps. Choose combinations carefully. Escape is a separate emergency-stop shortcut and is not customizable in the current version.

## How speed works

WPM is an estimate based on the common convention that one word is five characters. The app schedules key events against a clock to reduce timing drift. Actual speed can differ because of operating-system scheduling, text characters, configured pauses, and the receiving application. The dashboard's current WPM is an approximate live measurement, not a guarantee of exact speed.

## Local files and privacy

Drafts, recovery progress, preferences, and session history are stored on your computer in:

```text
~/.text_entry_assistant
```

Draft files contain the text you entered. Keep this folder private, and remove it if you no longer want the saved drafts or history. The app currently has no accounts, cloud service, or payment features; it is **not a SaaS**.

## Troubleshooting

- **The app does not open:** run it from VS Code's terminal using the command above so Python errors remain visible. Confirm that you are in the repository root and installed `requirements.txt`.
- **It does not type:** during the countdown, focus the intended document window and click inside its editing area. Confirm that the app did not pause because another window is active.
- **Escape does not stop:** ensure the app is running and the typing session has started. Global keyboard monitoring may be restricted by system settings or security software.
- **Google Docs behaves unexpectedly:** keep the correct Docs tab active and the browser in the foreground; this app cannot reliably identify individual tabs.

The app has not been verified on every Windows configuration or target application. Test with a short, non-sensitive phrase in a safe document before using longer text.
