"""Capture desktop frames and pass them to an image-processing callback."""

import logging
import threading
from dataclasses import dataclass
from typing import Callable

import mss
import numpy as np


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CapturedFrame:
    """A BGR screenshot and the screen coordinate of its top-left pixel."""

    image: np.ndarray
    screen_origin: tuple[int, int]


class ScreenCapture:
    """Capture a monitor periodically and synchronously deliver each frame."""

    def __init__(
        self,
        on_frame: Callable[[CapturedFrame], object],
        interval_seconds: float = 2.0,
        monitor_index: int = 0,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        if monitor_index < 0:
            raise ValueError("monitor_index cannot be negative")

        self.on_frame = on_frame
        self.interval_seconds = interval_seconds
        self.monitor_index = monitor_index
        self.on_error = on_error
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start capture on a background thread; repeated starts are ignored."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="screen-capture",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop capture and wait for the active frame callback to finish."""
        self._stop_event.set()
        if self._thread is not None and threading.current_thread() is not self._thread:
            self._thread.join()

    def _capture_loop(self) -> None:
        try:
            with mss.MSS() as capture:
                if self.monitor_index >= len(capture.monitors):
                    raise ValueError(
                        f"Monitor index {self.monitor_index} is unavailable"
                    )
                monitor = capture.monitors[self.monitor_index]
                origin = (monitor["left"], monitor["top"])

                while not self._stop_event.is_set():
                    screenshot = capture.grab(monitor)
                    # MSS returns BGRA; OpenCV matchers expect BGR.
                    image = np.asarray(screenshot, dtype=np.uint8)[:, :, :3].copy()
                    self.on_frame(CapturedFrame(image=image, screen_origin=origin))
                    self._stop_event.wait(self.interval_seconds)
        except Exception as error:
            logger.exception("Screen capture stopped after an error")
            if self.on_error is not None:
                self.on_error(error)