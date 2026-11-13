"""Standalone, clearly labeled typo/correction preview.

This demo edits only its own preview widgets. It does not send keys to Word,
Google Docs, browsers, or any other application.
"""

import random
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from core.typo_simulator import simulate_typos


BG = "#4A4A4A"
PANEL = "#333333"
PINK = "#E2B4BD"
CREAM = "#FFF5F5"
MUTED = "#D3C3C4"


class TypoPreview:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Typing Mistake Simulation — Preview Only")
        root.geometry("900x760")
        root.minsize(650, 540)
        root.configure(bg=BG)

        outer = tk.Frame(root, bg=BG, padx=16, pady=14)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)
        outer.rowconfigure(4, weight=1)

        tk.Label(
            outer,
            text="TYPO SIMULATION — PREVIEW ONLY",
            bg=BG,
            fg=CREAM,
            font=("Belisio", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            outer,
            text="This demo shows nearby-key mistakes and later, local corrections. It never types into another app.",
            bg=BG,
            fg=MUTED,
            wraplength=850,
            justify="left",
            font=("Belisio", 10),
        ).grid(row=1, column=0, sticky="ew", pady=(4, 10))

        self.source = scrolledtext.ScrolledText(
            outer, height=7, wrap="word", bg=PANEL, fg=CREAM,
            insertbackground=PINK, font=("Belisio", 11), padx=8, pady=7,
        )
        self.source.grid(row=2, column=0, sticky="nsew")
        self.source.insert("1.0", "Type a sample sentence here to preview simulated nearby-key mistakes and corrections.")

        settings = tk.Frame(outer, bg=BG, pady=10)
        settings.grid(row=3, column=0, sticky="ew")
        tk.Label(settings, text="Mistake probability (0–100%):", bg=BG, fg=CREAM, font=("Belisio", 10)).pack(side="left")
        self.probability = tk.StringVar(value="20")
        ttk.Entry(settings, textvariable=self.probability, width=7).pack(side="left", padx=(8, 18))
        tk.Label(settings, text="Correct after this many words:", bg=BG, fg=CREAM, font=("Belisio", 10)).pack(side="left")
        self.delay = tk.StringVar(value="3")
        ttk.Entry(settings, textvariable=self.delay, width=5).pack(side="left", padx=(8, 18))
        tk.Button(settings, text="Run preview", command=self.run_preview, bg=PINK, fg=BG, relief="flat", padx=12, pady=6).pack(side="left")

        timeline_frame = tk.Frame(outer, bg=PANEL, padx=8, pady=8)
        timeline_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 10))
        timeline_frame.rowconfigure(1, weight=1)
        timeline_frame.columnconfigure(0, weight=1)
        tk.Label(timeline_frame, text="Simulation timeline", bg=PANEL, fg=PINK, font=("Belisio", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.timeline = scrolledtext.ScrolledText(
            timeline_frame, wrap="word", state="disabled", bg=PANEL,
            fg=CREAM, font=("Consolas", 9), padx=6, pady=6,
        )
        self.timeline.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        final_frame = tk.Frame(outer, bg=PANEL, padx=8, pady=8)
        final_frame.grid(row=5, column=0, sticky="ew")
        final_frame.columnconfigure(0, weight=1)
        tk.Label(final_frame, text="Final corrected preview", bg=PANEL, fg=PINK, font=("Belisio", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.final = tk.Text(final_frame, height=4, wrap="word", state="disabled", bg=PANEL, fg=CREAM, font=("Belisio", 11), padx=6, pady=6)
        self.final.grid(row=1, column=0, sticky="ew", pady=(5, 0))

    def run_preview(self) -> None:
        try:
            probability = float(self.probability.get()) / 100
            delay = int(self.delay.get())
            if not 0 <= probability <= 1:
                raise ValueError("Mistake probability must be between 0 and 100 percent.")
            if delay < 1:
                raise ValueError("Correction delay must be at least one word.")
        except ValueError as exc:
            messagebox.showerror("Invalid setting", str(exc) or "Enter valid numbers.", parent=self.root)
            return

        text = self.source.get("1.0", "end-1c")
        result = simulate_typos(text, probability, delay, rng=random.Random())
        self.timeline.configure(state="normal")
        self.timeline.delete("1.0", "end")
        if not result.corrections:
            self.timeline.insert("end", "No mistakes were selected for this run. Try a higher probability or another sample.\n")
        else:
            self.timeline.insert("end", "Initially typed with simulated mistakes:\n")
            self.timeline.insert("end", result.initial_text + "\n\n")
            for event in result.timeline:
                if "corrected character" in event.description:
                    self.timeline.insert("end", event.description + "\n")
                    self.timeline.insert("end", event.text + "\n\n")
        self.timeline.configure(state="disabled")
        self.final.configure(state="normal")
        self.final.delete("1.0", "end")
        self.final.insert("1.0", result.corrected_text)
        self.final.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    TypoPreview(root)
    root.mainloop()


if __name__ == "__main__":
    main()
