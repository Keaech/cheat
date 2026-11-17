import os
import sys
import tkinter as tk
from tkinter import messagebox

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from pynput import keyboard
    from ui.dashboard import BentoDashboard
except ImportError as exc:
    print(f"\nImport error: {exc}")
    print("Install dependencies with: python -m pip install -r requirements.txt")
    input("Press Enter to exit...")
    raise SystemExit(1)


class SafeDashboard(BentoDashboard):
    """Adds focus-safe typing and convenient text-editor actions."""

    def __init__(self, root: tk.Tk):
        # The dashboard's Start handler expects this setting, although the
        # current UI does not render a target-window field.
        self.target_var = tk.StringVar(master=root, value="")
        super().__init__(root)
        self._add_text_actions()
        self._esc_listener = keyboard.Listener(on_press=self._on_emergency_key)
        self._esc_listener.start()

    def _add_text_actions(self) -> None:
        """Add explicit selection and clear controls below the existing editor."""
        editor = self.text_area.master
        toolbar = tk.Frame(editor, bg=COLORS["panel"])
        toolbar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(5, 0))

        tk.Label(
            toolbar,
            text="Select text by dragging, or use Shift + arrow keys. Then press Delete/Backspace or use:",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 9),
        ).pack(side="left", padx=(2, 8))
        tk.Button(
            toolbar,
            text="Delete selection",
            command=self.delete_selected_text,
            bg=COLORS["track"],
            fg=COLORS["cream"],
            activebackground=COLORS["pink"],
            relief="flat",
            padx=9,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=3)
        tk.Button(
            toolbar,
            text="Clear all",
            command=self.clear_all_text,
            bg=COLORS["danger"],
            fg=COLORS["cream"],
            activebackground=COLORS["pink"],
            relief="flat",
            padx=9,
            pady=4,
            cursor="hand2",
        ).pack(side="left", padx=3)

    def delete_selected_text(self) -> None:
        """Delete only the selected text and retain the rest of the draft."""
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Typing in progress", "Stop or pause the typing session before editing the text.")
            return
        if not self.text_area.tag_ranges("sel"):
            messagebox.showinfo("Nothing selected", "Select a section of text first, then choose Delete selection.")
            return
        self.text_area.delete("sel.first", "sel.last")
        self.text_area.focus_set()

    def clear_all_text(self) -> None:
        """Clear the complete editor after an explicit confirmation."""
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Typing in progress", "Stop or pause the typing session before clearing the text.")
            return
        if not self.text_area.get("1.0", "end-1c"):
            return
        if not messagebox.askyesno("Clear all text?", "Delete all text in the editor? This cannot be undone after the app closes."):
            return
        self.text_area.delete("1.0", "end")
        self._text = ""
        self._typed_chars = 0
        self._recovery_offset = 0
        self.text_area.focus_set()

    def _on_emergency_key(self, key):
        if key == keyboard.Key.esc and self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.pause_event.set()
            self.status_queue.put(("status", "Emergency stop requested (Esc)…"))

    def _typing_worker(self, text, offset, wpm, sentence_pause, paragraph_pause, _target=""):
        """Type at an average WPM cadence, guarded by foreground focus."""
        failure = None
        typed = offset
        active_started = None
        active_seconds = 0.0
        target_hwnd = None
        try:
            for remaining in range(3, 0, -1):
                if self.stop_event.is_set():
                    break
                self.status_queue.put(("status", f"Typing begins in {remaining} seconds — focus the target document now."))
                if self.stop_event.wait(1):
                    break

            if not self.stop_event.is_set():
                target_hwnd = self.engine.get_foreground_window_handle()
                if not target_hwnd or self.engine.is_current_process_window(target_hwnd):
                    raise RuntimeError("No external target is focused. Start again and focus the document during the countdown.")
                title = self.engine.get_window_title(target_hwnd) or "the selected window"
                self.status_queue.put(("status", f"Typing into {title}. Switching apps pauses typing; Esc stops."))
                deadline = time.monotonic()

                for index in range(offset, len(text)):
                    while not self.stop_event.is_set():
                        if not self.pause_event.wait(0.1):
                            continue
                        if self.engine.get_foreground_window_handle() == target_hwnd:
                            break
                        self.status_queue.put(("status", "Paused for focus protection — return to the target document to resume."))
                        if self.stop_event.wait(0.15):
                            break
                    if self.stop_event.is_set():
                        break

                    if active_started is None:
                        active_started = time.monotonic()
                    char = text[index]
                    self.engine.type_character(char)
                    typed = index + 1
                    self._typed_chars = typed

                    now = time.monotonic()
                    elapsed = active_seconds + (now - active_started)
                    chars_this_run = max(0, typed - offset)
                    actual_wpm = (chars_this_run / 5) * 60 / elapsed if elapsed > 0 else float(wpm)
                    if index % 20 == 0 or typed == len(text):
                        self.status_queue.put(("progress", (typed, elapsed, text, actual_wpm)))
                    self._persist_progress(typed)

                    interval = 60.0 / (max(1.0, min(600.0, self._current_wpm)) * 5)
                    deadline = max(deadline + interval, now)
                    deadline += self.pacer.get_pause_after(text, index, sentence_pause, paragraph_pause)
                    if self.stop_event.wait(max(0.0, deadline - time.monotonic())):
                        break

                if active_started is not None:
                    active_seconds += time.monotonic() - active_started
        except Exception as exc:
            failure = str(exc)

        elapsed = active_seconds
        if failure:
            outcome = ("Error", failure)
        elif self.stop_event.is_set():
            outcome = ("Ready", f"Stopped. {typed} of {len(text)} characters typed; draft saved for recovery.")
        else:
            outcome = ("Completed", "Text entry finished.")
            self._persist_progress(len(text))
        self.status_queue.put(("done", (outcome, typed, elapsed, text)))

    def close(self):
        self.stop_event.set()
        self.pause_event.set()
        if getattr(self, "_esc_listener", None):
            self._esc_listener.stop()
        super().close()


def main():
    try:
        root = tk.Tk()
        SafeDashboard(root)
        root.mainloop()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
