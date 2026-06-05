from __future__ import annotations

import atexit
import ctypes
import os
import platform
import re
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

TARGET_DOMAIN = "baidu.com"
BLOCK_IP = "0.0.0.0"
REDIRECT_IP = BLOCK_IP
TAG = "# Added by ConcentrateOn"
DOMAIN_PATTERN = re.compile(r"^(?!-)[a-z0-9-]+(?<!-)(\.(?!-)[a-z0-9-]+(?<!-))+$")


def get_hosts_path() -> str:
    if platform.system() == "Windows":
        return r"C:\Windows\System32\drivers\etc\hosts"
    return "/etc/hosts"


def is_admin() -> bool:
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        return os.geteuid() == 0
    except Exception:
        return False


def elevate_privileges() -> None:
    if platform.system() == "Windows":
        executable = sys.executable
        script = os.path.abspath(sys.argv[0])
        params = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            executable,
            f'"{script}" {params}',
            None,
            1,
        )
        if int(ret) <= 32:
            print("[x] Failed to elevate privileges.")
        sys.exit(0)

    os.execvp("sudo", ["sudo", sys.executable, *sys.argv])


def normalize_domain(value: str) -> str:
    cleaned = value.strip().lower()
    if "://" in cleaned:
        cleaned = cleaned.split("://", 1)[1]
    cleaned = cleaned.split("/", 1)[0]
    cleaned = cleaned.split("?", 1)[0]
    cleaned = cleaned.split("#", 1)[0]
    cleaned = cleaned.rsplit("@", 1)[-1]
    cleaned = cleaned.removeprefix("*.").removeprefix("www.").strip(".")
    if ":" in cleaned:
        host, port = cleaned.rsplit(":", 1)
        if port.isdigit():
            cleaned = host
    if not cleaned or any(char.isspace() for char in cleaned):
        return ""
    if not DOMAIN_PATTERN.fullmatch(cleaned):
        return ""
    return cleaned


@dataclass
class BlockerStatus:
    active_domains: list[str]
    hosts_path: str
    is_admin: bool
    block_ip: str


class WebsiteBlocker:
    def __init__(
        self,
        block_ip: str = BLOCK_IP,
        tag: str = TAG,
        hosts_path: str | Path | None = None,
        redirect_ip: str | None = None,
    ) -> None:
        if redirect_ip is not None:
            block_ip = redirect_ip
        self.block_ip = block_ip
        self.redirect_ip = block_ip
        self.tag = tag
        self.hosts_path = Path(hosts_path) if hosts_path is not None else Path(get_hosts_path())

    def status(self) -> BlockerStatus:
        return BlockerStatus(
            active_domains=self.active_domains(),
            hosts_path=str(self.hosts_path),
            is_admin=is_admin(),
            block_ip=self.block_ip,
        )

    def active_domains(self) -> list[str]:
        if not self.hosts_path.exists():
            return []

        domains: list[str] = []
        for line in self.hosts_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if self.tag not in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0] == self.block_ip:
                domains.append(parts[1].removeprefix("www."))

        return sorted(set(domains))

    def clear(self) -> None:
        self._write_domains([])

    def apply(self, domains: list[str]) -> list[str]:
        cleaned = self._prepare_domains(domains)
        self._write_domains(cleaned)
        return cleaned

    def _prepare_domains(self, domains: list[str]) -> list[str]:
        result: list[str] = []
        for domain in domains:
            normalized = normalize_domain(domain)
            if normalized and normalized not in result:
                result.append(normalized)
        return result

    def _write_domains(self, domains: list[str]) -> None:
        if not is_admin():
            raise PermissionError("Administrator privileges are required to edit the hosts file.")

        existing_lines: list[str] = []
        if self.hosts_path.exists():
            existing_lines = self.hosts_path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()

        kept_lines = [line for line in existing_lines if self.tag not in line]
        new_lines = list(kept_lines)
        for domain in domains:
            new_lines.append(f"{self.block_ip} {domain} {self.tag}")
            new_lines.append(f"{self.block_ip} www.{domain} {self.tag}")

        content = "\n".join(new_lines).rstrip()
        if content:
            content += "\n"
        self.hosts_path.write_text(content, encoding="utf-8")


def run_redirector() -> None:
    blocker = WebsiteBlocker()
    if not is_admin():
        elevate_privileges()

    def cleanup() -> None:
        try:
            blocker.clear()
        except Exception:
            pass

    def handle_signal(_signum, _frame) -> None:
        cleanup()
        sys.exit(0)

    cleanup()
    blocker.apply([TARGET_DOMAIN])
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"[*] Blocking {TARGET_DOMAIN} via hosts -> {blocker.block_ip}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    finally:
        cleanup()


if __name__ == "__main__":
    run_redirector()
