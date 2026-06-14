from __future__ import annotations

import time
import webbrowser
from typing import Any

from runtime import AppRuntime

try:
    import webview

    HAS_WEBVIEW = True
except ImportError:
    webview = None
    HAS_WEBVIEW = False

if HAS_WEBVIEW:
    from floating_widget.floating_widget import create_floating_window, register_desktop_actions
else:
    create_floating_window = None

    def register_desktop_actions(actions: Any | None) -> None:
        return None

DESKTOP_WINDOW_MANAGER: "DesktopWindowManager | None" = None

class DesktopBridgeAPI:
    def focus_session_started(self) -> None:
        if DESKTOP_WINDOW_MANAGER is not None:
            DESKTOP_WINDOW_MANAGER.show_floating_widget()

    def focus_session_stopped(self) -> None:
        if DESKTOP_WINDOW_MANAGER is not None:
            DESKTOP_WINDOW_MANAGER.restore_main_window()

    def show_main_window(self) -> None:
        if DESKTOP_WINDOW_MANAGER is not None:
            DESKTOP_WINDOW_MANAGER.restore_main_window()


class DesktopWindowManager:
    def __init__(self, runtime: AppRuntime) -> None:
        self.runtime = runtime
        self.main_window: webview.Window | None = None
        self.floating_window: webview.Window | None = None
        self.allow_floating_close = False

    def create_windows(self) -> bool:
        register_desktop_actions(self)

        self.main_window = webview.create_window(
            "ConcentrateOn",
            self.runtime.address,
            js_api=DesktopBridgeAPI(),
            width=1320,
            height=900,
            min_size=(800, 600),
        )
        if self.main_window is None:
            register_desktop_actions(None)
            return False

        self.floating_window = create_floating_window(minimized=True) if create_floating_window else None
        self.main_window.events.closed += self._on_main_window_closed

        if self.floating_window is not None:
            self.floating_window.events.closing += self._on_floating_window_closing

        return True

    def show_floating_widget(self) -> None:
        if self.main_window is not None:
            try:
                self.main_window.minimize()
            except Exception:
                pass

        if self.floating_window is not None:
            try:
                self.floating_window.show()
            except Exception:
                pass
            try:
                self.floating_window.restore()
            except Exception:
                pass

    def restore_main_window(self) -> None:
        if self.floating_window is not None:
            try:
                self.floating_window.minimize()
            except Exception:
                pass

        if self.main_window is not None:
            try:
                self.main_window.show()
            except Exception:
                pass
            try:
                self.main_window.restore()
            except Exception:
                pass

    def _on_floating_window_closing(self) -> bool:
        if self.allow_floating_close:
            return True

        self.restore_main_window()
        return False

    def _on_main_window_closed(self) -> None:
        register_desktop_actions(None)
        if self.floating_window is None:
            return

        self.allow_floating_close = True
        try:
            self.floating_window.destroy()
        except Exception:
            pass


def open_browser(runtime: AppRuntime) -> None:
    webbrowser.open(runtime.address)
    print(f"已在浏览器中打开：{runtime.address}")


def run_desktop_window(runtime: AppRuntime) -> bool:
    if not HAS_WEBVIEW:
        return False

    global DESKTOP_WINDOW_MANAGER

    DESKTOP_WINDOW_MANAGER = DesktopWindowManager(runtime)
    if not DESKTOP_WINDOW_MANAGER.create_windows():
        DESKTOP_WINDOW_MANAGER = None
        return False

    print(f"桌面应用已启动：{runtime.address}")
    webview.start()
    DESKTOP_WINDOW_MANAGER = None
    register_desktop_actions(None)
    return True


def run_service_loop(runtime: AppRuntime, launch_browser: bool = False) -> None:
    if launch_browser:
        open_browser(runtime)

    print(f"服务运行中：{runtime.address}")
    print("按 Ctrl+C 退出。")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
