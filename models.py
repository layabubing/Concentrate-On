from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)

@dataclass
class Settings:
    blocked_domains: list[str] = field(default_factory=lambda: ["baidu.com"])
    session_minutes: int = 45
    pomodoro_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    long_break_every: int = 4
    theme_mode: str = "light"
    color_scheme: str = "blue"
    daily_quote_enabled: bool = True


@dataclass
class SessionRecord:
    started_at: str
    ended_at: str
    duration_seconds: int
    blocked_domains: list[str]
    session_type: str = "focus"
    task_id: str | None = None
    task_ids: list[str] = field(default_factory=list)


@dataclass
class ActiveSession:
    started_at: str
    planned_minutes: int
    blocked_domains: list[str]
    blocking_active: bool
    session_type: str = "focus"
    task_id: str | None = None
    task_ids: list[str] = field(default_factory=list)
    blocking_message: str | None = None


@dataclass
class TaskItem:
    id: str
    title: str
    completed: bool = False
    created_at: str = field(default_factory=now_iso)
    pomodoros: int = 0


@dataclass
class AppState:
    settings: Settings = field(default_factory=Settings)
    current_session: ActiveSession | None = None
    history: list[SessionRecord] = field(default_factory=list)
    tasks: list[TaskItem] = field(default_factory=list)
