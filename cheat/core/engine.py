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
    """Send keyboard input through the Windows API."""

    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Text Entry Assistant's keyboard engine currently requires Windows.")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        self.user32.SendInput.restype = wintypes.UINT

    def _send_key(self, vk: int, flags: int = 0) -> None:
        event = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, flags, 0, 0))
        sent = self.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
        if sent != 1:
            raise ctypes.WinError(ctypes.get_last_error())

    def press_key(self, vk: int) -> None:
        self._send_key(vk)
        self._send_key(vk, KEYEVENTF_KEYUP)

    def type_unicode(self, char: str) -> None:
        """Emit Unicode as UTF-16 code units, including supplementary characters."""
        encoded = char.encode("utf-16-le", errors="strict")
        for offset in range(0, len(encoded), 2):
            code_unit = int.from_bytes(encoded[offset:offset + 2], "little")
            down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, code_unit, KEYEVENTF_UNICODE, 0, 0))
            up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, code_unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0))
            for event in (down, up):
                sent = self.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
                if sent != 1:
                    raise ctypes.WinError(ctypes.get_last_error())

    def type_character(self, char: str) -> None:
        if len(char) != 1:
            raise ValueError("type_character expects exactly one character")
        if char in ("\r",):
            return  # CRLF text is handled by the following newline.
        if char == "\n":
            self.press_key(0x0D)
        elif char == "\t":
            self.press_key(0x09)
        elif char == " ":
            self.press_key(0x20)
        else:
            self.type_unicode(char)

    def focus_window(self, keyword: str) -> bool:
        """Try to foreground a visible window whose title contains keyword.

        Windows may deny foreground activation depending on focus policy. The
        caller should treat False as a request for the user to focus the target.
        """
        if not keyword.strip():
            return False

        found_hwnd = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd, _lparam):
            if not self.user32.IsWindowVisible(hwnd):
                return True
            length = self.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            title = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, title, length + 1)
            if keyword.casefold() in title.value.casefold():
                found_hwnd.append(hwnd)
                return False
            return True

        self.user32.EnumWindows(callback, 0)
        if not found_hwnd:
            return False

        hwnd = found_hwnd[0]
        self.user32.ShowWindow(hwnd, SW_SHOW)
        self.user32.SetForegroundWindow(hwnd)
        return self.user32.GetForegroundWindow() == hwnd
