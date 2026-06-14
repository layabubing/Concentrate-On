from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PROJECT_ROOT / "webui"
DATA_ROOT = PROJECT_ROOT / ".concentrateon"
STATE_FILE = DATA_ROOT / "state.json"
RUNTIME_FILE = DATA_ROOT / "runtime.json"
DAILY_QUOTE_URL = "https://v.api.aa1.cn/api/yiyan/index.php"
