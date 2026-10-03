"""Move the mouse to a matched sprite and click its center once."""

from pynput.mouse import Button, Controller


class ClickController:
    def __init__(self) -> None:
        self._mouse = Controller()

    def on_match(self, x: int, y: int) -> None:
        """Click once at the matched bounding box's screen-coordinate center."""
        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError("Match coordinates must be integers")

        self._mouse.position = (x, y)
        self._mouse.click(Button.left, 1)