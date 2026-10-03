# UmaAutoclicker

Autoclicker for Roblox Kick an Uma

## Project Structure

```text
UmaAutoclicker/
├── README.md
├── images/       # Sprite templates used by image recognition
├── requirements.txt
└── app/
    ├── controller.py     # Clicks once at a matched screen position
    ├── image_matcher.py  # Matches captured frames to sprite templates
    ├── main.py           # Desktop UI and F6 hotkey entry point
    └── screen_capture.py  # Captures frames and emits them to a callback
```

The UI currently lives in `app/main.py`; a separate `ui.py` is not needed until the interface grows enough to justify splitting it out. Pressing Start or F6 creates and starts the screen-capture, matcher, and click-controller pipeline. `ScreenCapture` sends each captured BGR frame and its screen origin to `ImageMatcher.on_frame` every two seconds. The matcher compares the frame against the alpha-masked templates in `images/`, and calls `ClickController.on_match(x, y)` once for the strongest match whose confidence is strictly greater than the configured threshold (default `0.85`). The match center is converted to absolute screen coordinates before clicking. Pressing Stop or F6 stops and joins the capture thread before returning to the stopped state; closing the window also stops capture.

## Run the UI

On Windows with Python and Tkinter installed, install the project packages and run:

```powershell
python -m pip install -r requirements.txt
python app/main.py
```
