import os
import sys
import tkinter as tk

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from ui.dashboard import BentoDashboard
except ImportError as exc:
    print(f"\nImport error: {exc}")
    print("Install dependencies with: python -m pip install -r requirements.txt")
    input("Press Enter to exit...")
    raise SystemExit(1)


def main():
    try:
        root = tk.Tk()
        app = BentoDashboard(root)
        # The dashboard's start handler reads target_var, but its UI did not
        # create that variable. That exception happened before enabling Stop.
        # Empty means do not force-focus a named app: the user focuses Word,
        # Google Docs, or another intended field during the visible countdown.
        if not hasattr(app, "target_var"):
            app.target_var = tk.StringVar(master=root, value="")
        root.mainloop()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
