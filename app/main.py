import ctypes
import queue
import threading
import tkinter as tk
from ctypes import wintypes
from tkinter import messagebox

from controller import ClickController
from image_matcher import ImageMatcher
from screen_capture import ScreenCapture

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000
VK_F6 = 0x75
HOTKEY_ID = 1

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.RegisterHotKey.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    wintypes.UINT,
    wintypes.UINT,
]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = ctypes.c_int
user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostThreadMessageW.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.restype = wintypes.DWORD


class GlobalF6Hotkey:
    def __init__(self, events):
        self.events = events
        self.ready = threading.Event()
        self.thread_id = None
        self.error = None
        self.thread = threading.Thread(target=self._message_loop, daemon=True)

    def start(self):
        self.thread.start()
        self.ready.wait()
        return self.error is None

    def stop(self):
        if self.thread_id is not None:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            self.thread.join(timeout=1)

    def _message_loop(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_NOREPEAT, VK_F6):
            self.error = ctypes.get_last_error()
            self.ready.set()
            return

        self.ready.set()
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                self.events.put("toggle")

        user32.UnregisterHotKey(None, HOTKEY_ID)


class Autoclicker:
    def __init__(self, on_error):
        self._capture = None
        self.on_error = on_error

    @property
    def is_running(self):
        return self._capture is not None

    def start(self):
        if self.is_running:
            return

        controller = ClickController()
        matcher = ImageMatcher(controller)
        capture = ScreenCapture(
            on_frame=matcher.on_frame,
            on_error=self.on_error,
        )
        capture.start()
        self._capture = capture

    def stop(self):
        if self._capture is None:
            return

        self._capture.stop()
        self._capture = None


def main():
    root = tk.Tk()
    root.title("UmaAutoclicker")
    root.geometry("220x90")
    root.resizable(False, False)

    events = queue.SimpleQueue()
    autoclicker = Autoclicker(lambda error: events.put(("error", error)))

    def toggle():
        try:
            if autoclicker.is_running:
                autoclicker.stop()
            else:
                autoclicker.start()
        except Exception as error:
            messagebox.showerror("Autoclicker error", str(error), parent=root)
        button.config(
            text="Stop (F6) " if autoclicker.is_running else "Start (F6)"
        )

    button = tk.Button(root, text="Start (F6)", command=toggle, font=("Segoe UI", 14))
    button.pack(expand=True, fill="both", padx=12, pady=12)

    hotkey = GlobalF6Hotkey(events)
    if not hotkey.start():
        messagebox.showerror(
            "F6 unavailable",
            f"Could not register the global F6 hotkey (Windows error {hotkey.error}).",
            parent=root,
        )

    def process_hotkey_events():
        while not events.empty():
            event = events.get()
            if event == "toggle":
                toggle()
            else:
                autoclicker.stop()
                button.config(text="Start (F6)")
                messagebox.showerror(
                    "Autoclicker stopped",
                    str(event[1]),
                    parent=root,
                )
        if root.winfo_exists():
            root.after(50, process_hotkey_events)

    def close():
        autoclicker.stop()
        hotkey.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.after(50, process_hotkey_events)
    root.mainloop()


if __name__ == "__main__":
    main()