from __future__ import annotations

from argparse import ArgumentParser, Namespace

from desktop import run_desktop_window, run_service_loop
from runtime import start_runtime

def parse_args() -> Namespace:
    parser = ArgumentParser(description="启动 ConcentrateOn Web UI 应用。")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--browser", action="store_true", help="在浏览器中打开，而不是桌面窗口。")
    parser.add_argument("--headless", action="store_true", help="仅启动本地服务，不自动打开界面。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime = start_runtime(args.host, args.port)

    try:
        if args.headless:
            run_service_loop(runtime, launch_browser=False)
            return

        if args.browser:
            run_service_loop(runtime, launch_browser=True)
            return

        if run_desktop_window(runtime):
            return

        print("未检测到可用的桌面 WebView，已自动回退到浏览器模式。")
        run_service_loop(runtime, launch_browser=True)
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    main()
