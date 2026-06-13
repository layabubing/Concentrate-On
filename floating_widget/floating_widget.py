from __future__ import annotations

from pathlib import Path

import webview


ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "index.html"
WINDOW_WIDTH = 320
WINDOW_HEIGHT = 220
WINDOW: webview.Window | None = None


class FloatingWidgetAPI:
    def close(self) -> None:
        if WINDOW is not None:
            WINDOW.destroy()


def main() -> None:
    global WINDOW

    api = FloatingWidgetAPI()
    WINDOW = webview.create_window(
        title="ConcentrateOn Float",
        url=str(HTML_FILE),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        x=80,
        y=80,
        frameless=True,
        easy_drag=True,
        resizable=False,
        on_top=True,
        transparent=True,
        background_color="#000000",
        shadow=True,
    )
    if WINDOW is None:
        raise RuntimeError("Failed to create floating window.")

    webview.start()


if __name__ == "__main__":
    main()
