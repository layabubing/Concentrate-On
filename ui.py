from __future__ import annotations

import atexit
import json
import mimetypes
import threading
import time
import webbrowser
from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ban_website.redirector import WebsiteBlocker

try:
    import webview

    HAS_WEBVIEW = True
except ImportError:
    webview = None
    HAS_WEBVIEW = False

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PROJECT_ROOT / "webui"
DATA_ROOT = PROJECT_ROOT / ".concentrateon"
STATE_FILE = DATA_ROOT / "state.json"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def sanitize_domain_list(raw_domains: list[str] | str | None) -> list[str]:
    if raw_domains is None:
        return []

    if isinstance(raw_domains, str):
        candidates = raw_domains.replace("\r", "").replace(",", "\n").split("\n")
    else:
        candidates = [str(item) for item in raw_domains]

    domains: list[str] = []
    for candidate in candidates:
        cleaned = candidate.strip().lower()
        if not cleaned:
            continue
        if "://" in cleaned:
            cleaned = cleaned.split("://", 1)[1]
        cleaned = cleaned.split("/", 1)[0]
        cleaned = cleaned.split("?", 1)[0]
        cleaned = cleaned.strip(".")
        if cleaned and cleaned not in domains:
            domains.append(cleaned)
    return domains


@dataclass
class Settings:
    blocked_domains: list[str] = field(default_factory=lambda: ["baidu.com"])
    session_minutes: int = 45


@dataclass
class SessionRecord:
    started_at: str
    ended_at: str
    duration_seconds: int
    blocked_domains: list[str]


@dataclass
class ActiveSession:
    started_at: str
    planned_minutes: int
    blocked_domains: list[str]
    blocking_active: bool
    blocking_message: str | None = None


@dataclass
class AppState:
    settings: Settings = field(default_factory=Settings)
    current_session: ActiveSession | None = None
    history: list[SessionRecord] = field(default_factory=list)


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppState:
        if not self.path.exists():
            return AppState()

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        settings = Settings(**payload.get("settings", {}))
        current_payload = payload.get("current_session")
        current_session = ActiveSession(**current_payload) if current_payload else None
        history = [SessionRecord(**item) for item in payload.get("history", [])]
        return AppState(settings=settings, current_session=current_session, history=history)

    def save(self, state: AppState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            "settings": asdict(state.settings),
            "current_session": asdict(state.current_session) if state.current_session else None,
            "history": [asdict(item) for item in state.history[-100:]],
        }
        self.path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class FocusService:
    def __init__(self, store: StateStore, blocker: WebsiteBlocker) -> None:
        self.store = store
        self.blocker = blocker
        self.lock = threading.Lock()
        self.state = store.load()
        self._recover_previous_session()
        atexit.register(self.shutdown)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return self._build_snapshot()

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            domains = payload.get("blocked_domains", self.state.settings.blocked_domains)
            session_minutes = payload.get("session_minutes", self.state.settings.session_minutes)
            session_minutes = max(5, min(int(session_minutes), 240))

            self.state.settings = Settings(
                blocked_domains=sanitize_domain_list(domains),
                session_minutes=session_minutes,
            )

            if self.state.current_session is not None:
                self.state.current_session.planned_minutes = session_minutes
                self.state.current_session.blocked_domains = list(self.state.settings.blocked_domains)
                self._refresh_blocking()

            self.store.save(self.state)
            return self._build_snapshot()

    def start_focus(self) -> dict[str, Any]:
        with self.lock:
            if self.state.current_session is not None:
                return self._build_snapshot()

            session = ActiveSession(
                started_at=now_iso(),
                planned_minutes=self.state.settings.session_minutes,
                blocked_domains=list(self.state.settings.blocked_domains),
                blocking_active=False,
                blocking_message=None,
            )
            self.state.current_session = session
            self._refresh_blocking()
            self.store.save(self.state)
            return self._build_snapshot()

    def stop_focus(self) -> dict[str, Any]:
        with self.lock:
            if self.state.current_session is None:
                return self._build_snapshot()

            session = self.state.current_session
            started_at = parse_datetime(session.started_at)
            ended_at = datetime.now()
            duration_seconds = max(0, int((ended_at - started_at).total_seconds()))
            self.state.history.append(
                SessionRecord(
                    started_at=session.started_at,
                    ended_at=ended_at.isoformat(timespec="seconds"),
                    duration_seconds=duration_seconds,
                    blocked_domains=list(session.blocked_domains),
                )
            )

            self.state.current_session = None
            self._disable_blocking()
            self.store.save(self.state)
            return self._build_snapshot()

    def shutdown(self) -> None:
        with self.lock:
            self._disable_blocking()
            self.store.save(self.state)

    def _recover_previous_session(self) -> None:
        if self.state.current_session is None:
            return

        session = self.state.current_session
        duration_seconds = max(0, int((datetime.now() - parse_datetime(session.started_at)).total_seconds()))
        self.state.history.append(
            SessionRecord(
                started_at=session.started_at,
                ended_at=now_iso(),
                duration_seconds=duration_seconds,
                blocked_domains=list(session.blocked_domains),
            )
        )
        self.state.current_session = None
        self._disable_blocking()
        self.store.save(self.state)

    def _refresh_blocking(self) -> None:
        session = self.state.current_session
        if session is None:
            return

        if not session.blocked_domains:
            session.blocking_active = False
            session.blocking_message = "当前没有配置需要屏蔽的网站。"
            return

        try:
            self.blocker.apply(session.blocked_domains)
            session.blocking_active = True
            session.blocking_message = None
        except PermissionError:
            session.blocking_active = False
            session.blocking_message = "专注已开始，但当前没有管理员权限，网站屏蔽未生效。"
        except Exception as exc:
            session.blocking_active = False
            session.blocking_message = f"网站屏蔽启动失败：{exc}"

    def _disable_blocking(self) -> None:
        try:
            self.blocker.clear()
        except Exception:
            pass

    def _build_snapshot(self) -> dict[str, Any]:
        current = self.state.current_session
        total_seconds = sum(item.duration_seconds for item in self.state.history)
        today = datetime.now().date()
        today_sessions = [
            item
            for item in self.state.history
            if parse_datetime(item.ended_at).date() == today
        ]
        blocker_status = self.blocker.status()

        response: dict[str, Any] = {
            "settings": asdict(self.state.settings),
            "current_session": None,
            "stats": {
                "total_sessions": len(self.state.history),
                "total_focus_seconds": total_seconds,
                "today_sessions": len(today_sessions),
                "today_focus_seconds": sum(item.duration_seconds for item in today_sessions),
            },
            "recent_sessions": [asdict(item) for item in reversed(self.state.history[-8:])],
            "blocker": {
                "is_admin": blocker_status.is_admin,
                "hosts_path": blocker_status.hosts_path,
            },
        }

        if current is not None:
            response["current_session"] = {
                **asdict(current),
                "elapsed_seconds": max(
                    0,
                    int((datetime.now() - parse_datetime(current.started_at)).total_seconds()),
                ),
            }

        return response


class ConcentrateHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], service: FocusService) -> None:
        super().__init__(server_address, ConcentrateRequestHandler)
        self.service = service


class ConcentrateRequestHandler(BaseHTTPRequestHandler):
    server: ConcentrateHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._send_json(self.server.service.snapshot())
            return

        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self._read_json_body()

        if parsed.path == "/api/focus/start":
            self._send_json(self.server.service.start_focus())
            return

        if parsed.path == "/api/focus/stop":
            self._send_json(self.server.service.stop_focus())
            return

        if parsed.path == "/api/settings":
            self._send_json(self.server.service.update_settings(body))
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}

        raw = self.rfile.read(content_length).decode("utf-8")
        if not raw.strip():
            return {}
        return json.loads(raw)

    def _serve_static(self, route_path: str) -> None:
        file_path = self._resolve_static_path(route_path)
        if file_path is None or not file_path.exists() or not file_path.is_file():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        mime_type, _ = mimetypes.guess_type(file_path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def _resolve_static_path(self, route_path: str) -> Path | None:
        if route_path in {"", "/"}:
            return WEB_ROOT / "index.html"

        relative = route_path.lstrip("/")
        if relative.startswith("assets/"):
            candidate = PROJECT_ROOT / relative
        else:
            candidate = WEB_ROOT / relative

        try:
            candidate.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            return None
        return candidate

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)


@dataclass
class AppRuntime:
    service: FocusService
    server: ConcentrateHTTPServer
    thread: threading.Thread
    address: str

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.service.shutdown()


def start_runtime(host: str, port: int) -> AppRuntime:
    service = FocusService(StateStore(STATE_FILE), WebsiteBlocker())
    server = ConcentrateHTTPServer((host, port), service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = f"http://{server.server_address[0]}:{server.server_address[1]}"
    return AppRuntime(service=service, server=server, thread=thread, address=address)


def open_browser(runtime: AppRuntime) -> None:
    webbrowser.open(runtime.address)
    print(f"已在浏览器中打开：{runtime.address}")


def run_desktop_window(runtime: AppRuntime) -> bool:
    if not HAS_WEBVIEW:
        return False

    window = webview.create_window(
        "ConcentrateOn",
        runtime.address,
        width=1320,
        height=900,
        min_size=(1100, 760),
    )

    print(f"桌面应用已启动：{runtime.address}")
    webview.start()
    return window is not None


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
