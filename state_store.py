from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from models import ActiveSession, AppState, SessionRecord, Settings, TaskItem

class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppState:
        if not self.path.exists():
            return AppState()

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        settings_payload = payload.get("settings", {})
        settings = Settings(
            **{key: value for key, value in settings_payload.items() if key in Settings.__dataclass_fields__}
        )
        current_payload = payload.get("current_session")
        current_session = (
            ActiveSession(
                **{key: value for key, value in current_payload.items() if key in ActiveSession.__dataclass_fields__}
            )
            if current_payload
            else None
        )
        history = [
            SessionRecord(**{key: value for key, value in item.items() if key in SessionRecord.__dataclass_fields__})
            for item in payload.get("history", [])
        ]
        tasks = [
            TaskItem(**{key: value for key, value in item.items() if key in TaskItem.__dataclass_fields__})
            for item in payload.get("tasks", [])
        ]
        return AppState(settings=settings, current_session=current_session, history=history, tasks=tasks)

    def save(self, state: AppState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            "settings": asdict(state.settings),
            "current_session": asdict(state.current_session) if state.current_session else None,
            "history": [asdict(item) for item in state.history[-100:]],
            "tasks": [asdict(item) for item in state.tasks],
        }
        self.path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
