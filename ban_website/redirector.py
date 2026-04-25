from __future__ import annotations

import atexit
import ctypes
import os
import platform
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

TARGET_DOMAIN = "baidu.com"
REDIRECT_IP = "127.0.0.1"
TAG = "# Added by ConcentrateOn"


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
    cleaned = cleaned.strip(".")
    return cleaned


@dataclass
class BlockerStatus:
    active_domains: list[str]
    hosts_path: str
    is_admin: bool


class WebsiteBlocker:
    def __init__(self, redirect_ip: str = REDIRECT_IP, tag: str = TAG) -> None:
        self.redirect_ip = redirect_ip
        self.tag = tag
        self.hosts_path = Path(get_hosts_path())

    def status(self) -> BlockerStatus:
        return BlockerStatus(
            active_domains=self.active_domains(),
            hosts_path=str(self.hosts_path),
            is_admin=is_admin(),
        )

    def active_domains(self) -> list[str]:
        if not self.hosts_path.exists():
            return []

        domains: list[str] = []
        for line in self.hosts_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if self.tag not in line:
                continue
            parts = line.split()
            if len(parts) >= 2:
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
            new_lines.append(f"{self.redirect_ip} {domain} {self.tag}")
            new_lines.append(f"{self.redirect_ip} www.{domain} {self.tag}")

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

    print(f"[*] Redirecting {TARGET_DOMAIN} to {blocker.redirect_ip}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    finally:
        cleanup()


if __name__ == "__main__":
    run_redirector()
