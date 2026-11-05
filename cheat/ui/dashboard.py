import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from core.engine import TypingEngine
from core.humanizer import Humanizer
from pynput import keyboard


class BentoDashboard:
    """Simple Windows UI for user-directed, predictable text entry."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Text Entry Assistant")
        self.root.geometry("860x600")
        self.root.minsize(640, 450)
        self.root.configure(bg="#0f0f0f")

        self.engine = TypingEngine()
        self.pacer = Humanizer()
        self.stop_event = threading.Event()
        self.status_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.listener = keyboard.Listener(on_press=self._on_global_key)
        self.listener.start()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_status)

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#1a1a1a", foreground="#dddddd", font=("Segoe UI", 10))

        container = tk.Frame(self.root, bg="#0f0f0f", padx=18, pady=18)
        container.pack(expand=True, fill="both")
        container.rowconfigure(1, weight=1)
        container.columnconfigure(0, weight=1)

        tk.Label(
            container,
            text="TEXT ENTRY ASSISTANT",
            bg="#0f0f0f",
            fg="white",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.text_area = scrolledtext.ScrolledText(
            container,
            bg="#252525",
            fg="white",
            insertbackground="white",
            font=("Consolas", 11),
            wrap="word",
            borderwidth=0,
        )
        self.text_area.grid(row=1, column=0, sticky="nsew")

        controls = tk.Frame(container, bg="#0f0f0f", pady=12)
        controls.grid(row=2, column=0, sticky="ew")

        tk.Label(controls, text="Speed (words/minute):", bg="#0f0f0f", fg="#dddddd").grid(row=0, column=0, sticky="w")
        self.wpm_var = tk.StringVar(value="60")
        ttk.Entry(controls, textvariable=self.wpm_var, width=8).grid(row=0, column=1, padx=(8, 18), sticky="w")

        tk.Label(controls, text="Pause after sentences (seconds):", bg="#0f0f0f", fg="#dddddd").grid(row=0, column=2, sticky="w")
        self.sentence_pause_var = tk.StringVar(value="0.8")
        ttk.Entry(controls, textvariable=self.sentence_pause_var, width=7).grid(row=0, column=3, padx=(8, 18), sticky="w")

        tk.Label(controls, text="Pause between paragraphs (seconds):", bg="#0f0f0f", fg="#dddddd").grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.paragraph_pause_var = tk.StringVar(value="1.5")
        ttk.Entry(controls, textvariable=self.paragraph_pause_var, width=7).grid(row=1, column=2, sticky="w", pady=(10, 0))

        self.start_btn = tk.Button(
            controls,
            text="START",
            command=self.start_typing,
            bg="#3d5afe",
            fg="white",
            activebackground="#536dfe",
            relief="flat",
            padx=18,
            pady=8,
        )
        self.start_btn.grid(row=1, column=3, sticky="e", pady=(10, 0))
        controls.columnconfigure(4, weight=1)

        self.status_var = tk.StringVar(value="Ready — focus your intended text field before starting.")
        tk.Label(
            container,
            textvariable=self.status_var,
            bg="#0f0f0f",
            fg="#bdbdbd",
            anchor="w",
            wraplength=800,
        ).grid(row=3, column=0, sticky="ew", pady=(4, 0))
        tk.Label(
            container,
            text="Types into the currently focused window. Press Esc or click Stop to cancel.",
            bg="#0f0f0f",
            fg="#ffcc80",
            anchor="w",
            wraplength=800,
        ).grid(row=4, column=0, sticky="ew", pady=(6, 0))

    def _on_global_key(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """The listener thread signals cancellation; it never touches Tk widgets."""
        if key == keyboard.Key.esc and self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.status_queue.put(("status", "Stop requested…"))

    def start_typing(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.status_var.set("Stop requested…")
            self.start_btn.config(state="disabled", text="STOPPING…")
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
            messagebox.showerror(
                "Invalid settings",
                str(exc) if str(exc) else "Enter valid numbers for speed and pauses.",
            )
            return

        delay = 60.0 / (wpm * 5)
        self.stop_event.clear()
        self.start_btn.config(text="STOP", state="normal", bg="#c62828")
        self.status_var.set("Switch to your intended text field. Typing starts in 3 seconds…")
        self.worker = threading.Thread(
            target=self._typing_worker,
            args=(text, delay, sentence_pause, paragraph_pause),
            daemon=True,
        )
        self.worker.start()

    def _typing_worker(
        self,
        text: str,
        delay: float,
        sentence_pause: float,
        paragraph_pause: float,
    ) -> None:
        failure: str | None = None
        try:
            for remaining in range(3, 0, -1):
                if self.stop_event.is_set():
                    break
                self.status_queue.put(("status", f"Typing begins in {remaining} seconds…"))
                if self.stop_event.wait(1):
                    break

            if not self.stop_event.is_set():
                self.status_queue.put(("status", "Typing — press Esc or Stop to cancel."))
                for index, char in enumerate(text):
                    if self.stop_event.is_set():
                        break
                    self.engine.type_character(char)
                    if (index + 1) % 100 == 0:
                        self.status_queue.put(("status", f"Typed {index + 1} of {len(text)} characters…"))

                    wait_time = self.pacer.get_delay(delay, char)
                    wait_time += self.pacer.get_pause_after(text, index, sentence_pause, paragraph_pause)
                    if self.stop_event.wait(wait_time):
                        break
        except Exception as exc:
            failure = str(exc)
        finally:
            if failure:
                outcome = f"Error: {failure}"
            elif self.stop_event.is_set():
                outcome = "Cancelled."
            else:
                outcome = "Complete."
            self.status_queue.put(("done", outcome))

    def _poll_status(self) -> None:
        try:
            while True:
                kind, message = self.status_queue.get_nowait()
                if kind == "status":
                    self.status_var.set(message)
                elif kind == "done":
                    self.status_var.set(message)
                    self.start_btn.config(text="START", state="normal", bg="#3d5afe")
                    self.worker = None
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(100, self._poll_status)

    def close(self) -> None:
        self.stop_event.set()
        self.listener.stop()
        self.root.destroy()
