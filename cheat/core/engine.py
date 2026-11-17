import ctypes
from ctypes import wintypes

SW_SHOW = 5
user32 = ctypes.WinDLL("user32", use_last_error=True)

# Declare pointer-sized Windows API signatures explicitly. Without these,
# ctypes can assume C int arguments/return values and truncate HWND values
# on 64-bit Windows.
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
user32.keybd_event.restype = None

class TypingEngine:
    """Handles low-level Windows API interactions for input simulation."""

    def __init__(self):
        self.user32 = user32

    def press_key(self, vk: int):
        self.user32.keybd_event(vk, 0, 0, 0)
        self.user32.keybd_event(vk, 0, 2, 0)

    def type_unicode(self, char: str):
        # 0x0004 = KEYEVENTF_UNICODE
        self.user32.keybd_event(0, ord(char), 0x0004, 0)
        self.user32.keybd_event(0, ord(char), 0x0004 | 0x0002, 0)

    def type_character(self, char: str):
        if char == "\n": self.press_key(0x0D)
        elif char == "\t": self.press_key(0x09)
        elif char == " ": self.press_key(0x20)
        else: self.type_unicode(char)

    def focus_window(self, keyword: str) -> bool:
        found_hwnd = []

        def callback(hwnd, lParam):
            length = self.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buff, length + 1)
                if keyword.lower() in buff.value.lower():
                    found_hwnd.append(hwnd)
                    return False
            return True

        self.user32.EnumWindows(WNDENUMPROC(callback), 0)

        if found_hwnd:
            hwnd = found_hwnd[0]
            self.user32.keybd_event(0x12, 0, 0, 0) # ALT
            self.user32.ShowWindow(hwnd, SW_SHOW)
            self.user32.SetForegroundWindow(hwnd)
            self.user32.keybd_event(0x12, 0, 2, 0)
            return True
        return False
