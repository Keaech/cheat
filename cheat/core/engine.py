import ctypes
import os
from ctypes import wintypes


SW_SHOW = 5
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


class TypingEngine:
    """Send keyboard input and query foreground-window state on Windows."""

    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("The keyboard engine currently requires Windows.")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        self.user32.SendInput.restype = wintypes.UINT
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.IsWindowVisible.argtypes = (wintypes.HWND,)
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.EnumWindows.argtypes = (ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM)
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
        self.user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
        self.user32.SetForegroundWindow.restype = wintypes.BOOL

    def _send(self, event: INPUT) -> None:
        sent = self.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
        if sent != 1:
            raise ctypes.WinError(ctypes.get_last_error())

    def _send_key(self, vk: int, flags: int = 0) -> None:
        self._send(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, flags, 0, 0)))

    def press_key(self, vk: int) -> None:
        self._send_key(vk)
        self._send_key(vk, KEYEVENTF_KEYUP)

    def type_unicode(self, char: str) -> None:
        """Emit Unicode as UTF-16 code units (including emoji/supplementary text)."""
        encoded = char.encode("utf-16-le", errors="strict")
        for offset in range(0, len(encoded), 2):
            unit = int.from_bytes(encoded[offset:offset + 2], "little")
            self._send(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, unit, KEYEVENTF_UNICODE, 0, 0)))
            self._send(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)))

    def type_character(self, char: str) -> None:
        if len(char) != 1:
            raise ValueError("type_character expects exactly one character")
        if char == "\r":
            return
        if char == "\n":
            self.press_key(0x0D)
        elif char == "\t":
            self.press_key(0x09)
        elif char == " ":
            self.press_key(0x20)
        else:
            self.type_unicode(char)

    def get_foreground_window_handle(self):
        """Return the active top-level HWND, or None if no window is active."""
        return self.user32.GetForegroundWindow() or None

    def is_current_process_window(self, hwnd) -> bool:
        """Prevent accidental typing into any window owned by this app process."""
        if not hwnd:
            return False
        process_id = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        return process_id.value == os.getpid()

    def get_window_title(self, hwnd) -> str:
        if not hwnd:
            return ""
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        title = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, title, length + 1)
        return title.value

    def focus_window(self, keyword: str) -> bool:
        """Try to foreground a visible window whose title contains keyword."""
        if not keyword.strip():
            return False
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd, _lparam):
            if not self.user32.IsWindowVisible(hwnd):
                return True
            if keyword.casefold() in self.get_window_title(hwnd).casefold():
                found.append(hwnd)
                return False
            return True

        self.user32.EnumWindows(callback, 0)
        if not found:
            return False
        self.user32.ShowWindow(found[0], SW_SHOW)
        self.user32.SetForegroundWindow(found[0])
        return self.get_foreground_window_handle() == found[0]
