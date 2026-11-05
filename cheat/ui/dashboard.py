import queue
import threading
import time
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
        self.root.geometry("820x560")
        self.root.minsize(620, 420)
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
        style.configure("TFrame", background="#0f0f0f")
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
        tk.Label(controls, text="Speed (words/minute):", bg="#0f0f0f", fg="#dddddd").pack(side="left")
        self.wpm_var = tk.StringVar(value="60")
        self.wpm_entry = ttk.Entry(controls, textvariable=self.wpm_var, width=8)
        self.wpm_entry.pack(side="left", padx=(8, 16))

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
        self.start_btn.pack(side="left")

        self.status_var = tk.StringVar(value="Ready — focus your intended text field before starting.")
        tk.Label(
            container,
            textvariable=self.status_var,
            bg="#0f0f0f",
            fg="#bdbdbd",
            anchor="w",
            wraplength=760,
        ).grid(row=3, column=0, sticky="ew", pady=(4, 0))
        tk.Label(
            container,
            text="Types into the currently focused window. Press Esc or click Stop to cancel.",
            bg="#0f0f0f",
            fg="#ffcc80",
            anchor="w",
            wraplength=760,
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
            if not 1 <= wpm <= 600:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid speed", "Enter a speed from 1 to 600 words per minute.")
            return

        # Standard typing-speed convention: one word is five characters.
        delay = 60.0 / (wpm * 5)
        self.stop_event.clear()
        self.start_btn.config(text="STOP", state="normal", bg="#c62828")
        self.status_var.set("Switch to your intended text field. Typing starts in 3 seconds…")
        self.worker = threading.Thread(target=self._typing_worker, args=(text, delay), daemon=True)
        self.worker.start()

    def _typing_worker(self, text: str, delay: float) -> None:
        try:
            for remaining in range(3, 0, -1):
                if self.stop_event.is_set():
                    break
                self.status_queue.put(("status", f"Typing begins in {remaining} seconds…"))
                if self.stop_event.wait(1):
                    break

            if not self.stop_event.is_set():
                self.status_queue.put(("status", "Typing — press Esc or Stop to cancel."))
                for index, char in enumerate(text, start=1):
                    if self.stop_event.is_set():
                        break
                    self.engine.type_character(char)
                    if index % 100 == 0:
                        self.status_queue.put(("status", f"Typed {index} of {len(text)} characters…"))
                    if self.stop_event.wait(self.pacer.get_delay(delay, char)):
                        break
        except Exception as exc:
            self.status_queue.put(("error", str(exc)))
        finally:
            outcome = "Cancelled." if self.stop_event.is_set() else "Complete."
            self.status_queue.put(("done", outcome))

    def _poll_status(self) -> None:
        try:
            while True:
                kind, message = self.status_queue.get_nowait()
                if kind == "status":
                    self.status_var.set(message)
                elif kind == "error":
                    self.status_var.set(f"Error: {message}")
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
