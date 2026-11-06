# Text Entry Assistant

A local Windows desktop app for user-directed text entry. It offers configurable typing speed and sentence/paragraph pauses, a live progress dashboard, global keyboard shortcuts, text-file import, local autosave/recovery, and session history. It types into the focused window; use only where you are authorized and automation is permitted.

## Requirements and launch

- Windows, Python 3.10+, and Tkinter
- Belisio font is optional; the system font is used if it is unavailable

From the repository root in PowerShell:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python .\cheat\main.py
```

The app supports an optional target-window title match (default Notepad), then waits three seconds before typing. Confirm the intended field is focused before start. Press Escape or Stop to cancel. Local autosave and session history are stored under `~/.text_entry_assistant`; the draft contains your input text, so protect or delete that directory if it contains sensitive material.

## Dashboard and shortcuts

The dashboard shows character/word/paragraph counts, progress, words remaining, estimated time, approximate current WPM, and characters typed. Start/pause, stop, and speed changes can be triggered globally. Defaults are Ctrl+Alt+Space (start/pause), Ctrl+Alt+X (stop), Ctrl+Alt+Up (faster), and Ctrl+Alt+Down (slower). Use **Hotkeys** to customize them in pynput format; global shortcut registration can vary by operating system and may conflict with other software.

Import supports UTF-8 text files. Session history and drafts are local only; no text is sent to a service. Recovery records progress periodically, so a sudden shutdown may repeat a small number of recent characters. Verify target focus and cursor position before resuming.
