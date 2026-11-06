import os
import sys
import threading
import time
import tkinter as tk

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
    """Adds accurate pacing and a foreground-window safety guard."""

    def __init__(self, root: tk.Tk):
        # The existing dashboard's Start handler expects this setting, although
        # the current UI does not render a target-window field.
        self.target_var = tk.StringVar(master=root, value="")
        super().__init__(root)
        self._esc_listener = keyboard.Listener(on_press=self._on_emergency_key)
        self._esc_listener.start()

    def _on_emergency_key(self, key):
        if key == keyboard.Key.esc and self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.pause_event.set()
            self.status_queue.put(("status", "Emergency stop requested (Esc)…"))

    def _typing_worker(self, text, offset, wpm, sentence_pause, paragraph_pause, _target=""):
        """Type only while the intended external window remains foreground.

        Speed uses deadline-based scheduling to limit drift from per-character
        processing overhead. Changing WPM takes effect on the next character.
        """
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
                self.status_queue.put(("status", f"Typing into {title}. Switch back to this window to pause; Esc stops."))
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
                    pause = self.pacer.get_pause_after(text, index, sentence_pause, paragraph_pause)
                    deadline += pause
                    wait_for = max(0.0, deadline - time.monotonic())
                    if self.stop_event.wait(wait_for):
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
