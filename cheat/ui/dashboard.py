import queue
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from core.engine import TypingEngine
from core.humanizer import Humanizer
from pynput import keyboard


# Requested typeface. Tkinter uses the system's fallback if Belisio is not
# installed; install the Belisio font on Windows for the intended appearance.
FONT_FAMILY = "Belisio"
COLORS = {
    "charcoal": "#4A4A4A",
    "panel": "#333333",
    "pink": "#E2B4BD",
    "soft_pink": "#F7D6D0",
    "cream": "#FFF5F5",
    "muted": "#D3C3C4",
    "danger": "#9E5865",
}


def _rounded_points(width: int, height: int, radius: int = 16) -> list[int]:
    """Return polygon points for a rounded rectangle drawn on a Canvas."""
    radius = max(4, min(radius, width // 3, height // 3))
    points: list[int] = []
    corners = (
        (radius, radius, 180, 270),
        (width - radius, radius, 270, 360),
        (width - radius, height - radius, 0, 90),
        (radius, height - radius, 90, 180),
    )
    for cx, cy, start, end in corners:
        for step in range(7):
            angle = (start + (end - start) * step / 6) * 3.141592653589793 / 180
            points.extend((int(cx + radius * __import__("math").cos(angle)),
                           int(cy + radius * __import__("math").sin(angle))))
    return points


class RoundedPanel(tk.Canvas):
    """A lightweight rounded panel made with Tk Canvas; no extra packages."""

    def __init__(self, parent: tk.Widget, *, background: str, outline: str | None = None, **kwargs):
        super().__init__(
            parent,
            background=parent.cget("background"),
            highlightthickness=0,
            borderwidth=0,
            **kwargs,
        )
        self.panel_color = background
        self.outline_color = outline or background
        self.body = tk.Frame(self, background=background, borderwidth=0)
        self._body_window = self.create_window(3, 3, anchor="nw", window=self.body)
        self.bind("<Configure>", self._redraw)
        self._redraw()

    def _redraw(self, _event=None) -> None:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        self.delete("panel")
        self.create_polygon(
            _rounded_points(width - 1, height - 1),
            smooth=False,
            fill=self.panel_color,
            outline=self.outline_color,
            width=1,
            tags="panel",
        )
        self.tag_lower("panel")
        self.itemconfigure(self._body_window, width=max(1, width - 6), height=max(1, height - 6))


class BentoDashboard:
    """Premium-styled Windows UI for user-directed text entry."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Text Entry Assistant")
        self.root.geometry("900x700")
        self.root.minsize(660, 560)
        self.root.configure(bg=COLORS["charcoal"])

        self.engine = TypingEngine()
        self.pacer = Humanizer()
        self.stop_event = threading.Event()
        self.status_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self._closed = False

        self._configure_styles()
        self._build_ui()
        self.listener = keyboard.Listener(on_press=self._on_global_key)
        self.listener.start()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_status)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Pink.Vertical.TScrollbar",
            background=COLORS["pink"],
            troughcolor=COLORS["panel"],
            bordercolor=COLORS["panel"],
            arrowcolor=COLORS["cream"],
            relief="flat",
        )
        style.map("Pink.Vertical.TScrollbar", background=[("active", COLORS["soft_pink"])])
        style.configure(
            "Pink.TEntry",
            fieldbackground=COLORS["charcoal"],
            foreground=COLORS["cream"],
            insertcolor=COLORS["cream"],
            bordercolor=COLORS["pink"],
            lightcolor=COLORS["pink"],
            darkcolor=COLORS["pink"],
            padding=(9, 7),
            relief="flat",
        )

    def _build_ui(self) -> None:
        base_font = (FONT_FAMILY, 10)
        title_font = (FONT_FAMILY, 17, "bold")
        label_font = (FONT_FAMILY, 10)
        small_font = (FONT_FAMILY, 9)

        container = tk.Frame(self.root, bg=COLORS["charcoal"], padx=24, pady=20)
        container.pack(expand=True, fill="both")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        header = tk.Frame(container, bg=COLORS["charcoal"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        tk.Label(
            header,
            text="🪶",
            bg=COLORS["charcoal"],
            fg=COLORS["pink"],
            font=(FONT_FAMILY, 19),
        ).pack(side="left", padx=(0, 9))
        tk.Label(
            header,
            text="TEXT ENTRY ASSISTANT",
            bg=COLORS["charcoal"],
            fg=COLORS["cream"],
            font=title_font,
        ).pack(side="left")

        self.input_panel = RoundedPanel(
            container, background=COLORS["panel"], outline=COLORS["pink"]
        )
        self.input_panel.grid(row=1, column=0, sticky="nsew", pady=(0, 14))
        self.input_panel.body.rowconfigure(0, weight=1)
        self.input_panel.body.columnconfigure(0, weight=1)
        text_wrap = tk.Frame(self.input_panel.body, bg=COLORS["panel"], padx=12, pady=10)
        text_wrap.grid(row=0, column=0, sticky="nsew")
        text_wrap.rowconfigure(0, weight=1)
        text_wrap.columnconfigure(0, weight=1)
        self.text_area = tk.Text(
            text_wrap,
            bg=COLORS["panel"],
            fg=COLORS["cream"],
            insertbackground=COLORS["soft_pink"],
            selectbackground=COLORS["pink"],
            selectforeground=COLORS["charcoal"],
            font=(FONT_FAMILY, 12),
            wrap="word",
            borderwidth=0,
            padx=8,
            pady=8,
            undo=True,
        )
        self.text_area.grid(row=0, column=0, sticky="nsew")
        self.text_scrollbar = ttk.Scrollbar(
            text_wrap,
            orient="vertical",
            command=self.text_area.yview,
            style="Pink.Vertical.TScrollbar",
        )
        self.text_scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.text_area.configure(yscrollcommand=self.text_scrollbar.set)

        settings = RoundedPanel(container, background=COLORS["panel"])
        settings.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        settings.body.columnconfigure((0, 1, 2), weight=1, uniform="setting")
        setting_specs = (
            ("⚡", "Speed (words/minute)", "60", "wpm_var"),
            ("✦", "Pause after sentences (seconds)", "0.8", "sentence_pause_var"),
            ("✿", "Pause between paragraphs (seconds)", "1.5", "paragraph_pause_var"),
        )
        for column, (icon, label, default, variable_name) in enumerate(setting_specs):
            field = tk.Frame(settings.body, bg=COLORS["panel"], padx=12, pady=12)
            field.grid(row=0, column=column, sticky="ew")
            field.columnconfigure(0, weight=1)
            tk.Label(
                field,
                text=f"{icon}  {label}",
                bg=COLORS["panel"],
                fg=COLORS["soft_pink"],
                font=small_font,
                anchor="w",
                wraplength=220,
                justify="left",
            ).grid(row=0, column=0, sticky="ew", pady=(0, 7))
            variable = tk.StringVar(value=default)
            setattr(self, variable_name, variable)
            ttk.Entry(field, textvariable=variable, style="Pink.TEntry", font=base_font).grid(
                row=1, column=0, sticky="ew"
            )

        target_row = tk.Frame(settings.body, bg=COLORS["panel"], padx=12, pady=(0, 12))
        target_row.grid(row=1, column=0, columnspan=3, sticky="ew")
        target_row.columnconfigure(1, weight=1)
        tk.Label(
            target_row,
            text="⌕  Target window (optional)",
            bg=COLORS["panel"],
            fg=COLORS["soft_pink"],
            font=small_font,
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.target_var = tk.StringVar(value="Notepad")
        ttk.Entry(target_row, textvariable=self.target_var, style="Pink.TEntry", font=base_font).grid(
            row=0, column=1, sticky="ew"
        )

        footer = tk.Frame(container, bg=COLORS["charcoal"])
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(1, weight=1)
        self.start_btn = tk.Button(
            footer,
            text="▶  START",
            command=self.start_typing,
            bg=COLORS["pink"],
            fg=COLORS["charcoal"],
            activebackground=COLORS["soft_pink"],
            activeforeground=COLORS["charcoal"],
            font=(FONT_FAMILY, 11, "bold"),
            relief="flat",
            bd=0,
            padx=22,
            pady=11,
            cursor="hand2",
        )
        self.start_btn.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 16))
        self.start_btn.bind("<Enter>", self._button_hover)
        self.start_btn.bind("<Leave>", self._button_leave)
        self.start_btn.bind("<ButtonPress-1>", self._button_press)
        self.start_btn.bind("<ButtonRelease-1>", self._button_release)

        self.status_panel = RoundedPanel(footer, background=COLORS["panel"])
        self.status_panel.grid(row=0, column=1, rowspan=2, sticky="ew")
        status_body = self.status_panel.body
        status_body.columnconfigure(1, weight=1)
        self.status_icon = tk.Label(
            status_body,
            text="●",
            bg=COLORS["panel"],
            fg=COLORS["pink"],
            font=(FONT_FAMILY, 14),
        )
        self.status_icon.grid(row=0, column=0, rowspan=2, padx=(14, 9), pady=10)
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            status_body,
            textvariable=self.status_var,
            bg=COLORS["panel"],
            fg=COLORS["cream"],
            font=(FONT_FAMILY, 11, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(9, 0))
        self.detail_var = tk.StringVar(value="Focus your intended text field before starting.")
        tk.Label(
            status_body,
            textvariable=self.detail_var,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=small_font,
            anchor="w",
            wraplength=600,
            justify="left",
        ).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(2, 9))

        tk.Label(
            container,
            text="Types into the currently focused window. Press Esc or click Stop to cancel.",
            bg=COLORS["charcoal"],
            fg=COLORS["muted"],
            font=small_font,
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", pady=(10, 0))

    def _button_hover(self, _event=None) -> None:
        if self.worker and self.worker.is_alive():
            self.start_btn.configure(bg=COLORS["danger"])
        else:
            self.start_btn.configure(bg=COLORS["soft_pink"])

    def _button_leave(self, _event=None) -> None:
        if self.worker and self.worker.is_alive():
            self.start_btn.configure(bg=COLORS["danger"])
        else:
            self.start_btn.configure(bg=COLORS["pink"])

    def _button_press(self, _event=None) -> None:
        self.start_btn.configure(pady=9)

    def _button_release(self, _event=None) -> None:
        self.start_btn.configure(pady=11)

    def _set_status(self, state: str, detail: str) -> None:
        """Render status states consistently; Paused is styled for future use."""
        colors = {
            "Ready": COLORS["pink"],
            "Typing...": COLORS["soft_pink"],
            "Paused": COLORS["pink"],
            "Completed": COLORS["soft_pink"],
            "Cancelled": COLORS["muted"],
            "Error": COLORS["danger"],
        }
        self.status_var.set(state)
        self.detail_var.set(detail)
        self.status_icon.configure(fg=colors.get(state, COLORS["pink"]))

    def _on_global_key(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """The listener thread signals cancellation; it never touches Tk widgets."""
        if key == keyboard.Key.esc and self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.status_queue.put(("status", "Stop requested…"))

    def start_typing(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.start_btn.config(state="disabled", text="STOPPING…")
            self._set_status("Typing...", "Stop requested…")
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
        target_keyword = self.target_var.get().strip()
        self.stop_event.clear()
        self.start_btn.config(text="■  STOP", state="normal", bg=COLORS["danger"])
        self._set_status("Ready", "Focus your intended text field before starting.")
        self.worker = threading.Thread(
            target=self._typing_worker,
            args=(text, delay, sentence_pause, paragraph_pause, target_keyword),
            daemon=True,
        )
        self.worker.start()

    def _typing_worker(
        self,
        text: str,
        delay: float,
        sentence_pause: float,
        paragraph_pause: float,
        target_keyword: str,
    ) -> None:
        failure: str | None = None
        try:
            if target_keyword and not self.engine.focus_window(target_keyword):
                self.status_queue.put(("status", "Window not found — focus the intended field during countdown."))

            for remaining in range(3, 0, -1):
                if self.stop_event.is_set():
                    break
                self.status_queue.put(("status", f"Typing begins in {remaining} seconds…"))
                if self.stop_event.wait(1):
                    break

            if not self.stop_event.is_set():
                self.status_queue.put(("status", "Typing…"))
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
                outcome = ("Error", failure)
            elif self.stop_event.is_set():
                outcome = ("Cancelled", "Typing was cancelled.")
            else:
                outcome = ("Completed", "Text entry finished.")
            self.status_queue.put(("done", "|".join(outcome)))

    def _poll_status(self) -> None:
        if self._closed:
            return
        try:
            while True:
                kind, message = self.status_queue.get_nowait()
                if kind == "status":
                    self._set_status("Typing...", message)
                elif kind == "done":
                    state, detail = message.split("|", 1)
                    self._set_status(state, detail)
                    self.start_btn.config(text="▶  START", state="normal", bg=COLORS["pink"])
                    self.worker = None
        except queue.Empty:
            pass
        self.root.after(100, self._poll_status)

    def close(self) -> None:
        self._closed = True
        self.stop_event.set()
        self.listener.stop()
        self.root.destroy()
