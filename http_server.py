from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse

from elevation import launch_elevated_instance
from focus_service import FocusService
from paths import PROJECT_ROOT, WEB_ROOT
from quote import fetch_daily_quote

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

        if parsed.path == "/api/yiyan":
            try:
                self._send_json({"quote": fetch_daily_quote()})
            except (URLError, TimeoutError, ValueError, OSError) as exc:
                self._send_json(
                    {"quote": "", "error": f"每日一言获取失败：{exc}"},
                    status=HTTPStatus.BAD_GATEWAY,
                )
            return

        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self._read_json_body()

        if parsed.path == "/api/focus/start":
            self._send_json(self.server.service.start_focus(body))
            return

        if parsed.path == "/api/focus/stop":
            self._send_json(self.server.service.stop_focus())
            return

        if parsed.path == "/api/settings":
            self._send_json(self.server.service.update_settings(body))
            return

        if parsed.path == "/api/elevate":
            launched, message = launch_elevated_instance()
            self._send_json(
                {"launched": launched, "message": message},
                status=HTTPStatus.OK if launched else HTTPStatus.BAD_REQUEST,
            )
            return

        if parsed.path == "/api/tasks":
            self._send_json(self.server.service.add_task(body))
            return

        if parsed.path.startswith("/api/tasks/"):
            task_id = parsed.path.rsplit("/", 1)[-1]
            if body.get("_delete"):
                self._send_json(self.server.service.delete_task(task_id))
            else:
                self._send_json(self.server.service.update_task(task_id, body))
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
