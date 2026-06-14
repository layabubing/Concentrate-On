from __future__ import annotations

import json
import threading
from dataclasses import dataclass

from ban_website.redirector import WebsiteBlocker
from focus_service import FocusService
from http_server import ConcentrateHTTPServer
from models import now_iso
from paths import DATA_ROOT, RUNTIME_FILE, STATE_FILE
from state_store import StateStore

@dataclass
class AppRuntime:
    service: FocusService
    server: ConcentrateHTTPServer
    thread: threading.Thread
    address: str

    def shutdown(self) -> None:
        clear_runtime_file(self.address)
        self.server.shutdown()
        self.server.server_close()
        self.service.shutdown()


def write_runtime_file(address: str) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "address": address,
        "updated_at": now_iso(),
    }
    RUNTIME_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_runtime_file(address: str) -> None:
    if not RUNTIME_FILE.exists():
        return

    try:
        payload = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        payload = None

    if not isinstance(payload, dict) or payload.get("address") == address:
        try:
            RUNTIME_FILE.unlink()
        except FileNotFoundError:
            pass


def start_runtime(host: str, port: int) -> AppRuntime:
    service = FocusService(StateStore(STATE_FILE), WebsiteBlocker())
    server = ConcentrateHTTPServer((host, port), service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = f"http://{server.server_address[0]}:{server.server_address[1]}"
    write_runtime_file(address)
    return AppRuntime(service=service, server=server, thread=thread, address=address)
