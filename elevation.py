from __future__ import annotations

import ctypes
import platform
import sys
from pathlib import Path

from paths import PROJECT_ROOT

def elevated_argv() -> list[str]:
    args = list(sys.argv[1:])
    result: list[str] = []
    skip_next = False
    saw_port = False
    was_headless = False

    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg == "--headless":
            was_headless = True
            continue
        if arg == "--port":
            result.extend(["--port", "0"])
            skip_next = True
            saw_port = True
            continue
        if arg.startswith("--port="):
            result.append("--port=0")
            saw_port = True
            continue
        result.append(arg)

    if not saw_port:
        result.extend(["--port", "0"])
    if was_headless and "--browser" not in result:
        result.append("--browser")
    return result


def launch_elevated_instance() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, "当前系统不支持从界面直接申请提权，请使用管理员/root 权限重新启动应用。"

    executable = sys.executable
    script = Path(sys.argv[0]).resolve()
    args = " ".join([f'"{script}"', *(f'"{arg}"' for arg in elevated_argv())])
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        args,
        str(PROJECT_ROOT),
        1,
    )
    if int(result) <= 32:
        return False, "提权请求未能启动，可能是用户取消了授权。"
    return True, "已发起管理员权限请求，请在系统弹窗中确认；授权后会打开新的管理员权限窗口。"
