import ctypes
from ctypes import wintypes
import time
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pynput import keyboard # Required: pip install pynput

# --- Windows API Constants ---
SW_SHOW = 5
user32 = ctypes.windll.user32

class GhostTyperPro:
    def __init__(self, root):
        self.root = root
        self.root.title("👻 Ghost Typer Pro 👻")
        self.root.geometry("600x700")
        self.root.configure(bg="#1e1e1e")

        self.is_typing = False
        self.stop_requested = False

        self.setup_styles()
        self.build_ui()
        self.setup_panic_button()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", foreground="#cccccc", background="#1e1e1e", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#ffffff")

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg="#1e1e1e", padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        # Header
        header = ttk.Label(main_frame, text="👻 GHOST TYPER PRO 👻", style="Header.TLabel")
        header.pack(pady=(0, 20))

        # Text Input
        ttk.Label(main_frame, text="Input Text:").pack(anchor="w")
        self.text_area = scrolledtext.ScrolledText(
            main_frame, height=12, bg="#2d2d2d", fg="#ffffff",
            insertbackground="white", font=("Consolas", 11), borderwidth=0
        )
        self.text_area.pack(fill="both", expand=True, pady=(5, 20))

        # Settings Frame
        settings_frame = tk.LabelFrame(main_frame, text=" Settings ", bg="#1e1e1e", fg="#888888", padx=15, pady=15)
        settings_frame.pack(fill="x", pady=10)

        # WPM Setting
        wpm_frame = tk.Frame(settings_frame, bg="#1e1e1e")
        wpm_frame.pack(fill="x", pady=5)
        ttk.Label(wpm_frame, text="Words Per Minute (WPM):").pack(side="left")
        self.wpm_var = tk.StringVar(value="60")
        self.wpm_entry = ttk.Entry(wpm_frame, textvariable=self.wpm_var, width=10)
        self.wpm_entry.pack(side="right")

        # Humanization Setting
        hum_frame = tk.Frame(settings_frame, bg="#1e1e1e")
        hum_frame.pack(fill="x", pady=5)
        ttk.Label(hum_frame, text="Mistake Probability (%):").pack(side="left")
        self.mistake_var = tk.StringVar(value="2")
        self.mistake_entry = ttk.Entry(hum_frame, textvariable=self.mistake_var, width=10)
        self.mistake_entry.pack(side="right")

        # Target Window
        target_frame = tk.Frame(settings_frame, bg="#1e1e1e")
        target_frame.pack(fill="x", pady=5)
        ttk.Label(target_frame, text="Target Window Keyword:").pack(side="left")
        self.target_var = tk.StringVar(value="Notepad")
        self.target_entry = ttk.Entry(target_frame, textvariable=self.target_var, width=20)
        self.target_entry.pack(side="right")

        # Controls
        self.start_btn = tk.Button(
            main_frame, text="🚀 START TYPING", bg="#007acc", fg="white",
            font=("Segoe UI", 12, "bold"), command=self.start_typing_thread,
            relief="flat", cursor="hand2", pady=10
        )
        self.start_btn.pack(fill="x", pady=20)

        # Footer / Status
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="#666666")
        self.status_label.pack()

        ttk.Label(main_frame, text="⚠️ PANIC BUTTON: Press 'ESC' to stop instantly",
                  foreground="#ff5555", font=("Segoe UI", 9, "italic")).pack(pady=10)

    def setup_panic_button(self):
        # Run the keyboard listener in a background thread
        def on_press(key):
            if key == keyboard.Key.esc:
                self.stop_requested = True
                self.status_var.set("🛑 PANIC BUTTON PRESSED! Stopping...")

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    # --- Core Input Logic ---
    def press_key(self, vk: int):
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)

    def type_unicode(self, char: str):
        user32.keybd_event(0, ord(char), 0x0004, 0)
        user32.keybd_event(0, ord(char), 0x0004 | 0x0002, 0)

    def type_character(self, char: str):
        if char == "\n": self.press_key(0x0D)
        elif char == "\t": self.press_key(0x09)
        elif char == " ": self.press_key(0x20)
        else: self.type_unicode(char)

    def focus_window(self, keyword):
        found_hwnd = []
        def callback(hwnd, lParam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if keyword.lower() in buff.value.lower():
                    found_hwnd.append(hwnd)
                    return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(callback), 0)

        if found_hwnd:
            hwnd = found_hwnd[0]
            user32.keybd_event(0x12, 0, 0, 0) # ALT
            user32.ShowWindow(hwnd, SW_SHOW)
            user32.SetForegroundWindow(hwnd)
            user32.keybd_event(0x12, 0, 2, 0)
            return True
        return False

    # --- Execution ---
    def start_typing_thread(self):
        if self.is_typing: return

        text = self.text_area.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter some text first!")
            return

        self.stop_requested = False
        self.is_typing = True
        self.start_btn.config(text="⏹ STOPPING...", bg="#cc3300", state="disabled")

        # Start the logic in a separate thread so the GUI doesn't freeze
        threading.Thread(target=self.execution_loop, args=(text,), daemon=True).start()

    def execution_loop(self, text):
        try:
            # 1. Setup params
            wpm = float(self.wpm_var.get())
            base_delay = 60 / (wpm * 6)
            mistake_prob = float(self.mistake_var.get()) / 100
            keyword = self.target_var.get()

            # 2. Focus
            self.status_var.set(f"🔍 Finding {keyword}...")
            if not self.focus_window(keyword):
                self.status_var.set("⚠️ Window not found! Focus manually now!")

            # 3. Countdown
            for i in range(5, 0, -1):
                if self.stop_requested: break
                self.status_var.set(f"🚀 Typing begins in {i}...")
                time.sleep(1)

            # 4. Type
            self.status_var.set("⌨️ Ghost Typing Active...")
            for char in text:
                if self.stop_requested: break

                # Bursty timing (Humans type in rhythm)
                jitter = random.uniform(0.7, 1.3)
                current_delay = base_delay * jitter

                if random.random() < 0.02: # Natural pause
                    current_delay += random.uniform(0.5, 1.5)

                if char.isalpha() and random.random() < mistake_prob:
                    self.type_character(random.choice("qwertyuiopasdfghjklzxcvbnm"))
                    time.sleep(random.uniform(0.1, 0.2))
                    self.press_key(0x08) # Backspace
                    time.sleep(random.uniform(0.1, 0.2))

                self.type_character(char)
                time.sleep(current_delay)

            self.status_var.set("✅ Mission Complete!")

        except Exception as e:
            self.status_var.set(f"❌ Error: {str(e)}")
        finally:
            self.is_typing = False
            self.stop_requested = False
            self.root.after(0, lambda: self.start_btn.config(text="🚀 START TYPING", bg="#007acc", state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = GhostTyperPro(root)
    root.mainloop()
