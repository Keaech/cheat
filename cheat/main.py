import sys
import os
import tkinter as tk

# --- PATH FIXER ---
# This ensures that 'core' and 'ui' folders are recognized as packages
# regardless of how the script is launched.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from ui.dashboard import BentoDashboard
except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    print("\n💡 This usually happens if pynput is not installed.")
    print("Try running: pip install pynput")
    input("\nPress Enter to exit...")
    sys.exit(1)

def main():
    try:
        root = tk.Tk()
        # Bootloader logic
        app = BentoDashboard(root)
        root.mainloop()
    except Exception as e:
        print(f"\n💥 Fatal Crash: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
