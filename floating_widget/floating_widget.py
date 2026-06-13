from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import webview


ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "index.html"
PROJECT_ROOT = ROOT.parent
DATA_ROOT = PROJECT_ROOT / ".concentrateon"
STATE_FILE = DATA_ROOT / "state.json"
RUNTIME_FILE = DATA_ROOT / "runtime.json"
WINDOW_WIDTH = 320
WINDOW_HEIGHT = 220
WINDOW: webview.Window | None = None


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def now_seconds() -> int:
    return int(datetime.now().timestamp())


class FloatingWidgetAPI:
    def fetch_snapshot(self) -> dict[str, Any]:
        snapshot = self._fetch_runtime_snapshot()
        if snapshot is None:
            snapshot = self._load_state_snapshot()

        return self._normalize_snapshot(snapshot)

    def close(self) -> None:
        if WINDOW is not None:
            WINDOW.destroy()

    def _fetch_runtime_snapshot(self) -> dict[str, Any] | None:
        runtime = self._read_json(RUNTIME_FILE)
        if not isinstance(runtime, dict):
            return None

        address = str(runtime.get("address", "")).strip().rstrip("/")
        if not address:
            return None

        request = Request(
            f"{address}/api/state",
            headers={
                "User-Agent": "ConcentrateOnFloatingWidget/1.0",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urlopen(request, timeout=1.5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
            return None

        if isinstance(payload, dict):
            payload["_source"] = "runtime"
            payload["_address"] = address
            return payload
        return None

    def _load_state_snapshot(self) -> dict[str, Any]:
        payload = self._read_json(STATE_FILE)
        if not isinstance(payload, dict):
            return {"_source": "offline"}

        payload["_source"] = "state"
        return payload

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        return payload if isinstance(payload, dict) else None

    def _normalize_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        session = snapshot.get("current_session")
        settings = snapshot.get("settings") if isinstance(snapshot.get("settings"), dict) else {}
        source = str(snapshot.get("_source", "offline"))

        if not isinstance(session, dict):
            default_minutes = int(settings.get("session_minutes", 45) or 45)
            return {
                "connected": source == "runtime",
                "source": source,
                "session_active": False,
                "session_type": "focus",
                "planned_minutes": default_minutes,
                "elapsed_seconds": 0,
                "remaining_seconds": default_minutes * 60,
                "progress_percent": 0,
                "title": "等待专注开始",
                "status_text": "在主窗口开始一次专注后，这里会实时显示进度。",
            }

        planned_minutes = max(1, int(session.get("planned_minutes", settings.get("session_minutes", 45)) or 45))
        started_at = str(session.get("started_at", "")).strip()
        elapsed_seconds = int(session.get("elapsed_seconds", 0) or 0)
        if started_at and source != "runtime":
            try:
                elapsed_seconds = max(0, int((datetime.now() - parse_datetime(started_at)).total_seconds()))
            except ValueError:
                elapsed_seconds = max(0, elapsed_seconds)

        planned_seconds = planned_minutes * 60
        remaining_seconds = max(0, planned_seconds - elapsed_seconds)
        progress_percent = min(100, max(0, int((min(elapsed_seconds, planned_seconds) / planned_seconds) * 100)))
        session_type = str(session.get("session_type", "focus"))

        return {
            "connected": source == "runtime",
            "source": source,
            "session_active": True,
            "session_type": session_type,
            "planned_minutes": planned_minutes,
            "elapsed_seconds": elapsed_seconds,
            "remaining_seconds": remaining_seconds,
            "progress_percent": progress_percent,
            "title": self._session_label(session_type),
            "status_text": "正在与主程序同步。" if source == "runtime" else "主程序未连接，使用本地状态估算。",
            "started_at": started_at,
            "synced_at": now_seconds(),
        }

    def _session_label(self, session_type: str) -> str:
        labels = {
            "focus": "专注中",
            "pomodoro": "番茄钟中",
            "short_break": "短休息中",
            "long_break": "长休息中",
        }
        return labels.get(session_type, "专注中")


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
