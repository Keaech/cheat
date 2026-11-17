# Text Entry Assistant

A local Windows desktop app for user-directed text entry. It offers configurable typing speed and sentence/paragraph pauses, a live progress dashboard, global keyboard shortcuts, text-file import, local autosave/recovery, and session history.

## Run the app

On Windows with Python 3.10+ and Tkinter installed, from the repository root in PowerShell:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python .\\cheat\\main.py
```

During the three-second countdown, focus the intended document window (for example Word or Google Docs). The app captures that foreground window and types only while that same window remains active. Switching to another application pauses typing until you return to the target. Windows exposes browser tabs as one window, so the app cannot reliably detect switching between tabs; keep the intended Docs tab active. The app’s WPM timing is approximate and can vary with system scheduling, the target app, and configured pauses.

## Preview-only typo simulation

To demonstrate nearby-key mistakes and delayed corrections without sending input to another app, run this separate preview:

```powershell
python .\\cheat\\typo_preview.py
```

Enter sample text, choose a mistake probability (20% by default) and a correction delay in words, then select **Run preview**. The preview shows the simulated mistakes and local corrections; it never types into Word, Google Docs, or another window.

## Shortcuts and privacy

The main app supports pause/resume, stop, speed controls, and Escape emergency stop. Global shortcuts may conflict with other software. Drafts, recovery progress, preferences, and session history are stored locally under `~/.text_entry_assistant`; drafts contain your text. Keep that folder private. This is a desktop app, not a SaaS.
