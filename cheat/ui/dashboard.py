import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from core.engine import TypingEngine
from core.humanizer import Humanizer
from pynput import keyboard

class BentoDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Ghost Typer Pro")
        self.root.geometry("900x600")
        self.root.configure(bg="#0f0f0f")

        self.engine = TypingEngine()
        self.humanizer = Humanizer()
        self.is_typing = False
        self.stop_requested = False

        self.setup_styles()
        self.build_bento_grid()
        self.setup_panic_button()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Base styles
        self.style.configure("TFrame", background="#0f0f0f")
        self.style.configure("Bento.TFrame", background="#1a1a1a", relief="flat")
        self.style.configure("TLabel", background="#1a1a1a", foreground="#aaaaaa", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background="#1a1a1a", foreground="#ffffff", font=("Segoe UI", 14, "bold"))
        self.style.configure("Accent.TButton", background="#3d5afe", foreground="white", font=("Segoe UI", 11, "bold"))

    def create_bento_card(self, parent, title, row, col, rowspan=1, colspan=1):
        card = tk.Frame(parent, bg="#1a1a1a", padx=15, pady=15, highlightbackground="#333333", highlightthickness=1)
        card.grid(row=row, column=col, rowspan=rowspan, colspan=colspan, sticky="nsew", padx=10, pady=10)

        header = tk.Label(card, text=title, bg="#1a1a1a", fg="#ffffff", font=("Segoe UI", 12, "bold"))
        header.pack(anchor="w", pady=(0, 10))

        return card

    def build_bento_grid(self):
        self.main_container = tk.Frame(self.root, bg="#0f0f0f", padx=20, pady=20)
        self.main_container.pack(expand=True, fill="both")

        # Configure grid weights for responsiveness
        for i in range(3): self.main_container.columnconfigure(i, weight=1)
        for i in range(3): self.main_container.rowconfigure(i, weight=1)

        # Card 1: Text Input (Large - Top Left)
        self.input_card = self.create_bento_card(self.main_container, "📝 SOURCE TEXT", 0, 0, rowspan=2, colspan=2)
        self.text_area = scrolledtext.ScrolledText(
            self.input_card, bg="#252525", fg="#ffffff", insertbackground="white",
            font=("Consolas", 11), borderwidth=0, highlightthickness=0
        )
        self.text_area.pack(expand=True, fill="both")

        # Card 2: Target Window (Small - Top Right)
        self.target_card = self.create_bento_card(self.main_container, "🎯 TARGET", 0, 2)
        self.target_var = tk.StringVar(value="Notepad")
        self.target_entry = tk.Entry(self.target_card, textvariable=self.target_var, bg="#252525", fg="white", borderwidth=0, font=("Segoe UI", 11))
        self.target_entry.pack(fill="x", pady=5)

        # Card 3: WPM / Speed (Small - Middle Right)
        self.speed_card = self.create_bento_card(self.main_container, "⚡ SPEED", 1, 2)
        self.wpm_var = tk.StringVar(value="60")
        self.wpm_entry = tk.Entry(self.speed_card, textvariable=self.wpm_var, bg="#252525", fg="white", borderwidth=0, font=("Segoe UI", 11))
        self.wpm_entry.pack(fill="x", pady=5)

        # Card 4: Humanization (Small - Bottom Left)
        self.human_card = self.create_bento_card(self.main_container, "🧠 HUMANITY", 2, 0)
        self.mistake_var = tk.StringVar(value="2")
        self.mistake_entry = tk.Entry(self.human_card, textvariable=self.mistake_var, bg="#252525", fg="white", borderwidth=0, font=("Segoe UI", 11))
        self.mistake_entry.pack(fill="x", pady=5)

        # Card 5: Status (Small - Bottom Middle)
        self.status_card = self.create_bento_card(self.main_container, "📊 STATUS", 2, 1)
        self.status_var = tk.StringVar(value="IDLE")
        self.status_label = tk.Label(self.status_card, textvariable=self.status_var, bg="#1a1a1a", fg="#00ff00", font=("Segoe UI", 12, "bold"))
        self.status_label.pack(expand=True)

        # Card 6: Action (Small - Bottom Right)
        self.action_card = self.create_bento_card(self.main_container, "🕹️ CONTROL", 2, 2)
        self.start_btn = tk.Button(
            self.action_card, text="START", bg="#3d5afe", fg="white",
            font=("Segoe UI", 12, "bold"), command=self.start_typing,
            relief="flat", cursor="hand2"
        )
        self.start_btn.pack(expand=True, fill="both")

    def setup_panic_button(self):
        def on_press(key):
            if key == keyboard.Key.esc:
                self.stop_requested = True
                self.status_var.set("🛑 PANIC STOPPED")

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    def start_typing(self):
        if self.is_typing: return

        text = self.text_area.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Error", "Please enter text!")
            return

        self.stop_requested = False
        self.is_typing = True
        self.start_btn.config(text="STOPPING...", bg="#ff5252")

        threading.Thread(target=self.execution_loop, args=(text,), daemon=True).start()

    def execution_loop(self, text):
        try:
            wpm = float(self.wpm_var.get())
            base_delay = 60 / (wpm * 6)
            mistake_prob = float(self.mistake_var.get()) / 100
            keyword = self.target_var.get()

            self.status_var.set(f"🔍 FINDING {keyword}...")
            if not self.engine.focus_window(keyword):
                self.status_var.set("⚠️ FOCUS MANUALLY!")

            for i in range(5, 0, -1):
                if self.stop_requested: break
                self.status_var.set(f"🚀 STARTING IN {i}...")
                time.sleep(1)

            self.status_var.set("⌨️ TYPING...")
            for char in text:
                if self.stop_requested: break

                delay = self.humanizer.get_delay(base_delay)

                if self.humanizer.should_make_mistake(char, mistake_prob):
                    self.engine.type_character(self.humanizer.get_random_char())
                    time.sleep(random.uniform(0.1, 0.3))
                    self.engine.press_key(0x08)
                    time.sleep(random.uniform(0.1, 0.3))

                self.engine.type_character(char)
                time.sleep(delay)

            self.status_var.set("✅ DONE")

        except Exception as e:
            self.status_var.set(f"❌ ERROR: {str(e)}")
        finally:
            self.is_typing = False
            self.stop_requested = False
            self.root.after(0, lambda: self.start_btn.config(text="START", bg="#3d5afe"))

if __name__ == "__main__":
    root = tk.Tk()
    app = BentoDashboard(root)
    root.mainloop()
