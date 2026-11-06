# Text Entry Assistant

A local Windows desktop app for user-directed text entry. It offers configurable typing speed and sentence/paragraph pauses, a live progress dashboard, global keyboard shortcuts, text-file import, local autosave/recovery, and session history.

## Run

On Windows with Python 3.10+ and Tkinter installed, from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python .\\cheat\\main.py
```

During the three-second countdown, focus the intended document window (for example Word or Google Docs). The app captures that external foreground window and types only while that same window remains active. Switching to another application pauses typing until you return to the target; Escape stops immediately. Windows exposes browser tabs as one window, so switching tabs within the same browser window cannot always be distinguished from the target document. Keep the document editor focused, or use a browser extension for reliable tab/editor-level focus protection.

Pacing is scheduled against monotonic time to reduce drift; the requested WPM is approximate and depends on system scheduling, Unicode handling, and any configured sentence/paragraph pauses. Current throughput includes time spent in those pauses. The dashboard text editor itself is never used as the typing target.

Drafts, session recovery, and history are stored locally under `~/.text_entry_assistant`; drafts include your input text. Keep that folder private or delete it if it contains sensitive material.
