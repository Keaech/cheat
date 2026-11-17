import json
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core.engine import TypingEngine
from core.humanizer import Humanizer
from pynput import keyboard

FONT_FAMILY = "Belisio"
COLORS = {
    "charcoal": "#4A4A4A",
    "panel": "#333333",
    "pink": "#E2B4BD",
    "soft_pink": "#F7D6D0",
    "cream": "#FFF5F5",
    "muted": "#D3C3C4",
    "danger": "#9E5865",
    "track": "#62575A",
}
DATA_DIR = Path.home() / ".text_entry_assistant"
SESSION_FILE = DATA_DIR / "session.json"
HISTORY_FILE = DATA_DIR / "history.json"
DEFAULT_HOTKEYS = {
    "toggle": "<ctrl>+<alt>+<space>",
    "stop": "<ctrl>+<alt>+x",
    "faster": "<ctrl>+<alt>+<up>",
    "slower": "<ctrl>+<alt>+<down>",
}


class BentoDashboard:
    """Progress dashboard for transparent, user-directed text entry."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Text Entry Assistant")
        self.root.geometry("1120x790")
        self.root.minsize(760, 650)
        self.root.configure(bg=COLORS["charcoal"])

        self.engine = TypingEngine()
        self.pacer = Humanizer()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # set means the worker is allowed to type
        self.status_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.hotkey_listener = None
        self._closed = False
        self._suppress_autosave = False
        self._autosave_after_id = None
        self._text = ""
        self._typed_chars = 0
        self._started_at: float | None = None
        self._initial_wpm = 60.0
        self._current_wpm = 60.0
        self._last_progress_emit = 0.0

        self._configure_styles()
        self._build_ui()
        self._load_preferences()
        self._restore_session()
        self._register_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_status)
        self.root.bind("<Configure>", self._resize_status_text)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Pink.Vertical.TScrollbar", background=COLORS["pink"],
            troughcolor=COLORS["panel"], bordercolor=COLORS["panel"],
            arrowcolor=COLORS["cream"], relief="flat",
        )
        style.map("Pink.Vertical.TScrollbar", background=[("active", COLORS["soft_pink"])])
        style.configure(
            "Pink.TEntry", fieldbackground=COLORS["charcoal"],
            foreground=COLORS["cream"], insertcolor=COLORS["cream"],
            bordercolor=COLORS["pink"], lightcolor=COLORS["pink"],
            darkcolor=COLORS["pink"], padding=(8, 6), relief="flat",
        )
        style.configure(
            "Pink.Horizontal.TProgressbar", troughcolor=COLORS["track"],
            background=COLORS["pink"], bordercolor=COLORS["track"],
            lightcolor=COLORS["pink"], darkcolor=COLORS["pink"], thickness=9,
        )

    def _build_ui(self) -> None:
        self.container = tk.Frame(self.root, bg=COLORS["charcoal"], padx=20, pady=16)
        self.container.pack(expand=True, fill="both")
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(1, weight=1)

        header = tk.Frame(self.container, bg=COLORS["charcoal"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        tk.Label(header, text="🪶", bg=COLORS["charcoal"], fg=COLORS["pink"], font=(FONT_FAMILY, 22)).pack(side="left", padx=(0, 10))
        title_box = tk.Frame(header, bg=COLORS["charcoal"])
        title_box.pack(side="left")
        tk.Label(title_box, text="TEXT ENTRY ASSISTANT", bg=COLORS["charcoal"], fg=COLORS["cream"], font=(FONT_FAMILY, 18, "bold")).pack(anchor="w")
        tk.Label(title_box, text="Type. Automate. Be Productive.", bg=COLORS["charcoal"], fg=COLORS["muted"], font=(FONT_FAMILY, 10)).pack(anchor="w")
        tk.Button(header, text="History", command=self.show_history, bg=COLORS["panel"], fg=COLORS["cream"], activebackground=COLORS["track"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right", padx=(8, 0))
        tk.Button(header, text="Import TXT", command=self.import_text, bg=COLORS["panel"], fg=COLORS["cream"], activebackground=COLORS["track"], relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right")

        editor = tk.Frame(self.container, bg=COLORS["panel"], highlightbackground=COLORS["pink"], highlightthickness=1, padx=10, pady=8)
        editor.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        editor.rowconfigure(0, weight=1)
        editor.columnconfigure(0, weight=1)
        self.text_area = tk.Text(
            editor, bg=COLORS["panel"], fg=COLORS["cream"], insertbackground=COLORS["soft_pink"],
            selectbackground=COLORS["pink"], selectforeground=COLORS["charcoal"],
            font=(FONT_FAMILY, 12), wrap="word", borderwidth=0, padx=10, pady=8, undo=True,
        )
        self.text_area.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(editor, orient="vertical", command=self.text_area.yview, style="Pink.Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_area.configure(yscrollcommand=scrollbar.set)
        self.text_area.bind("<<Modified>>", self._text_changed)

        self.count_var = tk.StringVar(value="0 characters  •  0 words  •  0 paragraphs")
        tk.Label(editor, textvariable=self.count_var, bg=COLORS["panel"], fg=COLORS["muted"], font=(FONT_FAMILY, 9)).grid(row=1, column=0, sticky="w", padx=8, pady=(6, 0))

        settings = tk.Frame(self.container, bg=COLORS["charcoal"])
        settings.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        for col in range(3):
            settings.columnconfigure(col, weight=1, uniform="setting")
        setting_specs = (
            ("⚡  Speed (words/minute)", "60", "wpm_var"),
            ("◷  Pause after sentences (seconds)", "0.8", "sentence_pause_var"),
            ("☰  Pause between paragraphs (seconds)", "1.5", "paragraph_pause_var"),
        )
        for col, (label, default, attr) in enumerate(setting_specs):
            card = tk.Frame(settings, bg=COLORS["panel"], padx=10, pady=9, highlightbackground=COLORS["track"], highlightthickness=1)
            card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 5, 5 if col < 2 else 0))
            tk.Label(card, text=label, bg=COLORS["panel"], fg=COLORS["soft_pink"], font=(FONT_FAMILY, 9), anchor="w", wraplength=280).pack(fill="x", pady=(0, 6))
            variable = tk.StringVar(value=default)
            setattr(self, attr, variable)
            ttk.Entry(card, textvariable=variable, style="Pink.TEntry", font=(FONT_FAMILY, 10)).pack(fill="x")

        dashboard = tk.Frame(self.container, bg=COLORS["panel"], padx=12, pady=10, highlightbackground=COLORS["track"], highlightthickness=1)
        dashboard.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        for col in range(5):
            dashboard.columnconfigure(col, weight=1, uniform="stat")
        self.stat_vars = {}
        stats = (
            ("Progress", "0%"), ("Words remaining", "0"), ("Estimated time", "—"),
            ("Current speed", "0 WPM"), ("Characters typed", "0"),
        )
        for col, (label, value) in enumerate(stats):
            box = tk.Frame(dashboard, bg=COLORS["panel"])
            box.grid(row=0, column=col, sticky="ew", padx=6)
            tk.Label(box, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=(FONT_FAMILY, 9), anchor="w").pack(fill="x")
            var = tk.StringVar(value=value)
            self.stat_vars[label] = var
            tk.Label(box, textvariable=var, bg=COLORS["panel"], fg=COLORS["cream"], font=(FONT_FAMILY, 12, "bold"), anchor="w").pack(fill="x", pady=(3, 0))
        self.progress = ttk.Progressbar(dashboard, maximum=100, style="Pink.Horizontal.TProgressbar")
        self.progress.grid(row=1, column=0, columnspan=5, sticky="ew", padx=6, pady=(10, 0))

        lower = tk.Frame(self.container, bg=COLORS["charcoal"])
        lower.grid(row=4, column=0, sticky="ew")
        lower.columnconfigure(1, weight=1)
        self.start_button = tk.Button(lower, text="▶  START", command=self.start_typing, bg=COLORS["pink"], fg=COLORS["charcoal"], activebackground=COLORS["soft_pink"], font=(FONT_FAMILY, 11, "bold"), relief="flat", padx=18, pady=9, cursor="hand2")
        self.start_button.grid(row=0, column=0, sticky="w", padx=(0, 7))
        self.pause_button = tk.Button(lower, text="Ⅱ  PAUSE", command=self.toggle_pause, bg=COLORS["panel"], fg=COLORS["cream"], activebackground=COLORS["track"], font=(FONT_FAMILY, 10), relief="flat", padx=14, pady=9, cursor="hand2", state="disabled")
        self.pause_button.grid(row=0, column=1, sticky="w", padx=7)
        self.stop_button = tk.Button(lower, text="■  STOP", command=self.stop_typing, bg=COLORS["panel"], fg=COLORS["muted"], activebackground=COLORS["danger"], font=(FONT_FAMILY, 10), relief="flat", padx=14, pady=9, cursor="hand2", state="disabled")
        self.stop_button.grid(row=0, column=2, sticky="w", padx=7)
        tk.Button(lower, text="Hotkeys ⚙", command=self.show_hotkeys, bg=COLORS["panel"], fg=COLORS["cream"], activebackground=COLORS["track"], relief="flat", padx=12, pady=9, cursor="hand2").grid(row=0, column=3, sticky="e", padx=(7, 0))

        self.status_var = tk.StringVar(value="Ready")
        self.detail_var = tk.StringVar(value="Focus your intended text field before starting.")
        status = tk.Frame(self.container, bg=COLORS["panel"], padx=12, pady=9, highlightbackground=COLORS["track"], highlightthickness=1)
        status.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        status.columnconfigure(1, weight=1)
        self.status_icon = tk.Label(status, text="●", bg=COLORS["panel"], fg=COLORS["pink"], font=(FONT_FAMILY, 13))
        self.status_icon.grid(row=0, column=0, rowspan=2, padx=(0, 9))
        tk.Label(status, textvariable=self.status_var, bg=COLORS["panel"], fg=COLORS["cream"], font=(FONT_FAMILY, 11, "bold"), anchor="w").grid(row=0, column=1, sticky="ew")
        tk.Label(status, textvariable=self.detail_var, bg=COLORS["panel"], fg=COLORS["muted"], font=(FONT_FAMILY, 9), anchor="w").grid(row=1, column=1, sticky="ew", pady=(2, 0))
        tk.Label(self.container, text="Types into the currently focused window. Press Esc or click Stop to cancel.", bg=COLORS["charcoal"], fg=COLORS["soft_pink"], font=(FONT_FAMILY, 9), anchor="w").grid(row=6, column=0, sticky="ew", pady=(8, 0))

    def _resize_status_text(self, event=None) -> None:
        # Tk's wrapping can use a fixed max width; window layout remains resizable.
        pass

    def _text_changed(self, _event=None) -> None:
        if self.text_area.edit_modified():
            self.text_area.edit_modified(False)
            self._update_word_counter()
            if not self._suppress_autosave:
                if self._autosave_after_id:
                    self.root.after_cancel(self._autosave_after_id)
                self._autosave_after_id = self.root.after(700, self._save_draft)

    def _update_word_counter(self) -> None:
        text = self.text_area.get("1.0", "end-1c")
        words = len(text.split())
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])
        self.count_var.set(f"{len(text)} characters  •  {words} words  •  {paragraphs} paragraphs")

    def _save_draft(self) -> None:
        self._autosave_after_id = None
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            current_text = self.text_area.get("1.0", "end-1c")
            existing = self._read_json(SESSION_FILE, {})
            payload = {
                "text": current_text,
                "typed_chars": min(int(existing.get("typed_chars", 0)), len(current_text)) if current_text == self._text else 0,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
            SESSION_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            self._set_status("Ready", f"Could not autosave draft: {exc}")

    def _persist_progress(self, typed_chars: int) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            SESSION_FILE.write_text(json.dumps({
                "text": self._text,
                "typed_chars": typed_chars,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def _read_json(path: Path, fallback):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return fallback

    def _restore_session(self) -> None:
        saved = self._read_json(SESSION_FILE, {})
        text = saved.get("text", "")
        if not isinstance(text, str) or not text:
            return
        self._suppress_autosave = True
        self.text_area.insert("1.0", text)
        self.text_area.edit_modified(False)
        self._suppress_autosave = False
        self._update_word_counter()
        typed = saved.get("typed_chars", 0)
        try:
            typed = max(0, min(int(typed), len(text)))
        except (TypeError, ValueError):
            typed = 0
        if typed:
            self._text = text
            self._typed_chars = typed
            self._set_status("Ready", f"Recovered draft. {typed} characters were previously entered. Review the target and use Resume recovered text if appropriate.")
            self._update_stats(typed, 0, text, 60)
            if messagebox.askyesno("Recover interrupted session", f"A previous session stopped after {typed} characters. Resume the remaining text from that point?\n\nConfirm that the target field is positioned correctly before resuming."):
                self._recovery_offset = typed
            else:
                self._recovery_offset = 0
        else:
            self._recovery_offset = 0

    def _load_preferences(self) -> None:
        prefs = self._read_json(DATA_DIR / "preferences.json", {})
        hotkeys = prefs.get("hotkeys", {}) if isinstance(prefs, dict) else {}
        self.hotkeys = {**DEFAULT_HOTKEYS, **(hotkeys if isinstance(hotkeys, dict) else {})}

    def _save_preferences(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            (DATA_DIR / "preferences.json").write_text(json.dumps({"hotkeys": self.hotkeys}, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Settings not saved", str(exc))

    def _register_hotkeys(self) -> None:
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        callbacks = {
            self.hotkeys["toggle"]: self._hotkey_toggle,
            self.hotkeys["stop"]: self._hotkey_stop,
            self.hotkeys["faster"]: self._hotkey_faster,
            self.hotkeys["slower"]: self._hotkey_slower,
        }
        if len(set(callbacks)) != len(callbacks):
            raise ValueError("Each global shortcut must be unique.")
        listener = keyboard.GlobalHotKeys(callbacks)
        listener.start()
        self.hotkey_listener = listener

    def _hotkey_toggle(self) -> None:
        self.status_queue.put(("command", "toggle"))

    def _hotkey_stop(self) -> None:
        self.status_queue.put(("command", "stop"))

    def _hotkey_faster(self) -> None:
        self.status_queue.put(("command", "faster"))

    def _hotkey_slower(self) -> None:
        self.status_queue.put(("command", "slower"))

    def show_hotkeys(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Customize global hotkeys")
        window.configure(bg=COLORS["charcoal"])
        window.resizable(False, False)
        tk.Label(window, text="Global shortcuts (pynput format)", bg=COLORS["charcoal"], fg=COLORS["cream"], font=(FONT_FAMILY, 12, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(window, text="Examples: <ctrl>+<alt>+<space>, <ctrl>+<alt>+x, <f8>", bg=COLORS["charcoal"], fg=COLORS["muted"], font=(FONT_FAMILY, 9)).pack(anchor="w", padx=16, pady=(0, 8))
        variables = {}
        labels = (("toggle", "Start / pause"), ("stop", "Stop immediately"), ("faster", "Increase speed"), ("slower", "Decrease speed"))
        for key, label in labels:
            row = tk.Frame(window, bg=COLORS["charcoal"])
            row.pack(fill="x", padx=16, pady=4)
            tk.Label(row, text=label, width=19, anchor="w", bg=COLORS["charcoal"], fg=COLORS["soft_pink"], font=(FONT_FAMILY, 10)).pack(side="left")
            var = tk.StringVar(value=self.hotkeys[key])
            variables[key] = var
            ttk.Entry(row, textvariable=var, style="Pink.TEntry", width=24).pack(side="left")
        tk.Label(window, text="Global hotkeys may conflict with other apps. Choose combinations you have checked.", bg=COLORS["charcoal"], fg=COLORS["muted"], font=(FONT_FAMILY, 9), wraplength=430, justify="left").pack(anchor="w", padx=16, pady=8)

        def apply() -> None:
            candidate = {key: var.get().strip().lower() for key, var in variables.items()}
            if not all(candidate.values()) or len(set(candidate.values())) != len(candidate):
                messagebox.showerror("Invalid shortcuts", "Shortcuts must be non-empty and unique.", parent=window)
                return
            old = self.hotkeys
            self.hotkeys = candidate
            try:
                self._register_hotkeys()
            except (ValueError, KeyError) as exc:
                self.hotkeys = old
                self._register_hotkeys()
                messagebox.showerror("Shortcut unavailable", f"Could not register those shortcuts: {exc}", parent=window)
                return
            self._save_preferences()
            window.destroy()

        tk.Button(window, text="Apply shortcuts", command=apply, bg=COLORS["pink"], fg=COLORS["charcoal"], relief="flat", padx=14, pady=7).pack(anchor="e", padx=16, pady=(2, 14))

    def import_text(self) -> None:
        filename = filedialog.askopenfilename(title="Import text", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if not filename:
            return
        try:
            text = Path(filename).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", text)
        self._text_changed()

    def _update_stats(self, typed: int, elapsed: float, text: str, current_wpm: float) -> None:
        total_chars = len(text)
        progress = (100.0 * typed / total_chars) if total_chars else 0.0
        remaining_text = text[typed:]
        words_remaining = len(remaining_text.split())
        eta_seconds = words_remaining * 60 / current_wpm if current_wpm > 0 else 0
        if eta_seconds < 60:
            eta = f"{int(eta_seconds + 0.5)} sec"
        elif eta_seconds < 3600:
            eta = f"{int(eta_seconds // 60)} min {int(eta_seconds % 60)} sec"
        else:
            eta = f"{int(eta_seconds // 3600)} hr {int((eta_seconds % 3600) // 60)} min"
        self.stat_vars["Progress"].set(f"{progress:.1f}%")
        self.stat_vars["Words remaining"].set(str(words_remaining))
        self.stat_vars["Estimated time"].set("—" if not typed and elapsed <= 0 else eta)
        self.stat_vars["Current speed"].set(f"{current_wpm:.1f} WPM")
        self.stat_vars["Characters typed"].set(str(typed))
        self.progress["value"] = progress

    def start_typing(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        text = self.text_area.get("1.0", "end-1c")
        if not text:
            messagebox.showwarning("Text required", "Enter text before starting.")
            return
        try:
            wpm = float(self.wpm_var.get())
            sentence_pause = float(self.sentence_pause_var.get())
            paragraph_pause = float(self.paragraph_pause_var.get())
            if not 1 <= wpm <= 600:
                raise ValueError("Speed must be between 1 and 600 WPM.")
            if not 0 <= sentence_pause <= 30 or not 0 <= paragraph_pause <= 60:
                raise ValueError("Sentence pause must be 0–30 seconds and paragraph pause 0–60 seconds.")
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc) or "Enter valid numbers.")
            return

        offset = getattr(self, "_recovery_offset", 0)
        if text != self._text:
            offset = 0
        offset = max(0, min(offset, len(text)))
        self._text = text
        self._typed_chars = offset
        self._initial_wpm = wpm
        self._current_wpm = wpm
        self._started_at = time.monotonic()
        self.stop_event.clear()
        self.pause_event.set()
        target = self.target_var.get().strip()
        self.start_button.configure(state="disabled", text="▶  START")
        self.pause_button.configure(state="normal")
        self.stop_button.configure(state="normal")
        self._set_status("Typing...", "Focus your intended text field before starting.")
        self._update_stats(offset, 0, text, wpm)
        self.worker = threading.Thread(target=self._typing_worker, args=(text, offset, wpm, sentence_pause, paragraph_pause, target), daemon=True)
        self.worker.start()

    def _typing_worker(self, text: str, offset: int, wpm: float, sentence_pause: float, paragraph_pause: float, target: str) -> None:
        failure = None
        started = time.monotonic()
        try:
            if target and not self.engine.focus_window(target):
                self.status_queue.put(("warning", "Target window not found. Confirm the intended field is focused."))
            for remaining in range(3, 0, -1):
                if self.stop_event.is_set():
                    break
                self.status_queue.put(("status", f"Typing begins in {remaining} seconds…"))
                if self.stop_event.wait(1):
                    break
            for index in range(offset, len(text)):
                while not self.stop_event.is_set() and not self.pause_event.wait(0.1):
                    pass
                if self.stop_event.is_set():
                    break
                char = text[index]
                self.engine.type_character(char)
                typed = index + 1
                self._typed_chars = typed
                elapsed = max(time.monotonic() - started, 0.01)
                actual_wpm = max(0.1, ((typed - offset) / 5) / elapsed * 60)
                self._persist_progress(typed)
                now = time.monotonic()
                if now - self._last_progress_emit >= 0.2 or typed == len(text):
                    self._last_progress_emit = now
                    self.status_queue.put(("progress", (typed, elapsed, text, actual_wpm)))
                wait_time = self.pacer.get_delay(60 / (self._current_wpm * 5), char)
                wait_time += self.pacer.get_pause_after(text, index, sentence_pause, paragraph_pause)
                if self.stop_event.wait(wait_time):
                    break
        except Exception as exc:
            failure = str(exc)
        elapsed = max(time.monotonic() - started, 0)
        self._record_history(text, offset, self._typed_chars, elapsed, failure)
        if failure:
            outcome = ("Error", failure)
        elif self.stop_event.is_set():
            outcome = ("Ready", f"Stopped. {self._typed_chars} of {len(text)} characters typed; draft saved for recovery.")
        else:
            outcome = ("Completed", "Text entry finished.")
            self._persist_progress(len(text))
        self.status_queue.put(("done", (outcome, self._typed_chars, elapsed, text)))

    def toggle_pause(self) -> None:
        if not self.worker or not self.worker.is_alive():
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text="▶  RESUME")
            self._set_status("Paused", "Typing is paused. Use Resume or the configured start/pause hotkey.")
        else:
            self.pause_event.set()
            self.pause_button.configure(text="Ⅱ  PAUSE")
            self._set_status("Typing...", "Typing resumed.")

    def stop_typing(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.pause_event.set()
            self._set_status("Typing...", "Stop requested…")

    def _adjust_speed(self, change: float) -> None:
        if not self.worker or not self.worker.is_alive():
            return
        self._current_wpm = max(1.0, min(600.0, self._current_wpm + change))
        self.wpm_var.set(f"{self._current_wpm:g}")
        self.detail_var.set(f"Speed changed to {self._current_wpm:g} WPM.")

    def _set_status(self, state: str, detail: str) -> None:
        color = COLORS["pink"] if state in ("Ready", "Paused") else COLORS["soft_pink"]
        if state == "Error":
            color = COLORS["danger"]
        self.status_var.set(state)
        self.detail_var.set(detail)
        self.status_icon.configure(fg=color)

    def _record_history(self, text: str, offset: int, typed: int, elapsed: float, failure: str | None) -> None:
        if typed <= offset and not failure:
            return
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            history = self._read_json(HISTORY_FILE, [])
            if not isinstance(history, list):
                history = []
            history.insert(0, {
                "date": datetime.now().isoformat(timespec="seconds"),
                "characters": typed - offset,
                "words": len(text[offset:typed].split()),
                "duration_seconds": round(elapsed, 1),
                "result": "error" if failure else ("stopped" if self.stop_event.is_set() else "completed"),
                "preview": text[:100],
            })
            HISTORY_FILE.write_text(json.dumps(history[:50], ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def show_history(self) -> None:
        history = self._read_json(HISTORY_FILE, [])
        window = tk.Toplevel(self.root)
        window.title("Typing history")
        window.geometry("540x360")
        window.configure(bg=COLORS["charcoal"])
        tk.Label(window, text="Recent sessions", bg=COLORS["charcoal"], fg=COLORS["cream"], font=(FONT_FAMILY, 14, "bold")).pack(anchor="w", padx=14, pady=12)
        listbox = tk.Listbox(window, bg=COLORS["panel"], fg=COLORS["cream"], selectbackground=COLORS["pink"], font=(FONT_FAMILY, 10), borderwidth=0)
        listbox.pack(expand=True, fill="both", padx=14, pady=(0, 14))
        for item in history if isinstance(history, list) else []:
            listbox.insert("end", f"{item.get('date', '')}  |  {item.get('result', '')}  |  {item.get('words', 0)} words, {item.get('characters', 0)} chars  |  {item.get('preview', '')}")
        if not listbox.size():
            listbox.insert("end", "No typing sessions recorded yet.")

    def _poll_status(self) -> None:
        if self._closed:
            return
        try:
            while True:
                kind, payload = self.status_queue.get_nowait()
                if kind == "status":
                    self.detail_var.set(str(payload))
                elif kind == "warning":
                    self._set_status("Ready", str(payload))
                elif kind == "progress":
                    typed, elapsed, text, current_wpm = payload
                    self._update_stats(typed, elapsed, text, current_wpm)
                    self.detail_var.set(f"Typing… {typed} of {len(text)} characters. Focus your intended text field before starting.")
                elif kind == "command":
                    if payload == "toggle":
                        if self.worker and self.worker.is_alive():
                            self.toggle_pause()
                        else:
                            self.start_typing()
                    elif payload == "stop":
                        self.stop_typing()
                    elif payload == "faster":
                        self._adjust_speed(5)
                    elif payload == "slower":
                        self._adjust_speed(-5)
                elif kind == "done":
                    (state, detail), typed, elapsed, text = payload
                    self._update_stats(typed, elapsed, text, self._current_wpm)
                    self._set_status(state, detail)
                    self.start_button.configure(state="normal", text="▶  START")
                    self.pause_button.configure(state="disabled", text="Ⅱ  PAUSE")
                    self.stop_button.configure(state="disabled")
                    self.worker = None
                    self._recovery_offset = typed if state == "Ready" else 0
        except queue.Empty:
            pass
        self.root.after(100, self._poll_status)

    def close(self) -> None:
        self._closed = True
        self.stop_event.set()
        self.pause_event.set()
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        if self._autosave_after_id:
            self.root.after_cancel(self._autosave_after_id)
        try:
            if self.text_area.get("1.0", "end-1c"):
                self._save_draft()
        except tk.TclError:
            pass
        self.root.destroy()
