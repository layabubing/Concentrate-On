import argparse
import atexit
import ctypes
import os
import platform
import signal
import sys
import time
from pathlib import Path

BLOCK_TAG = "ConcentrateOn Host Redirector"
BLOCK_START = f"# >>> {BLOCK_TAG} START >>>"
BLOCK_END = f"# <<< {BLOCK_TAG} END <<<"


def get_hosts_path() -> Path:
    if platform.system() == "Windows":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        return Path(system_root) / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


def is_admin() -> bool:
    try:
        if platform.system() == "Windows":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def normalize_domain(raw_domain: str) -> str:
    value = raw_domain.strip().lower()
    if not value:
        return ""

    if "://" in value:
        value = value.split("://", 1)[1]

    value = value.split("/", 1)[0]
    value = value.split(":", 1)[0]
    value = value.lstrip(".")
    return value


def build_domain_list(domains: list[str], include_www: bool) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    for raw in domains:
        domain = normalize_domain(raw)
        if not domain or " " in domain:
            continue

        candidates = [domain]
        if include_www and not domain.startswith("www."):
            candidates.append(f"www.{domain}")

        for item in candidates:
            if item not in seen:
                seen.add(item)
                ordered.append(item)

    return ordered


def strip_redirect_block(lines: list[str]) -> tuple[list[str], bool]:
    cleaned: list[str] = []
    in_block = False
    removed = False

    for line in lines:
        marker = line.strip()

        if marker == BLOCK_START:
            in_block = True
            removed = True
            continue

        if marker == BLOCK_END and in_block:
            in_block = False
            continue

        if not in_block:
            cleaned.append(line)

    return cleaned, removed


def make_redirect_block(domains: list[str]) -> list[str]:
    lines = [BLOCK_START + "\n"]
    for domain in domains:
        lines.append(f"0.0.0.0 {domain}\n")
    lines.append(BLOCK_END + "\n")
    return lines


def merge_hosts_lines(base_lines: list[str], block_lines: list[str]) -> list[str]:
    merged = list(base_lines)

    if merged and not merged[-1].endswith("\n"):
        merged[-1] = merged[-1] + "\n"

    if merged and merged[-1].strip():
        merged.append("\n")

    merged.extend(block_lines)
    return merged


class HostsRedirector:
    def __init__(self, hosts_path: Path):
        self.hosts_path = hosts_path
        self._active = False

    def _read_lines(self) -> list[str]:
        return self.hosts_path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)

    def _write_lines(self, lines: list[str]) -> None:
        self.hosts_path.write_text("".join(lines), encoding="utf-8", newline="\n")

    def apply(self, domains: list[str]) -> None:
        lines = self._read_lines()
        cleaned, _ = strip_redirect_block(lines)
        block_lines = make_redirect_block(domains)
        merged = merge_hosts_lines(cleaned, block_lines)
        self._write_lines(merged)
        self._active = True

    def cleanup(self) -> bool:
        lines = self._read_lines()
        cleaned, removed = strip_redirect_block(lines)
        if removed:
            self._write_lines(cleaned)
        self._active = False
        return removed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把指定域名重定向到 0.0.0.0，程序退出后自动取消。"
    )
    parser.add_argument(
        "domains",
        nargs="*",
        help="要重定向的域名，例如: youtube.com x.com",
    )
    parser.add_argument(
        "--include-www",
        action="store_true",
        help="同时重定向 www. 前缀域名。",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="仅清理本程序写入的 hosts 规则，不启用重定向。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hosts_path = get_hosts_path()

    if not hosts_path.exists():
        print(f"[x] 未找到 hosts 文件: {hosts_path}")
        return 1

    if not is_admin():
        print("[x] 需要管理员权限才能修改 hosts 文件。")
        print("    请使用管理员权限重新运行该脚本。")
        return 1

    redirector = HostsRedirector(hosts_path)

    if args.cleanup_only:
        removed = redirector.cleanup()
        if removed:
            print("[+] 已清理重定向规则。")
        else:
            print("[*] 未发现可清理的重定向规则。")
        return 0

    domain_list = build_domain_list(args.domains, include_www=args.include_www)
    if not domain_list:
        print("[x] 请至少传入一个有效域名。")
        print("    示例: python ban_website/redirector.py youtube.com x.com --include-www")
        return 1

    try:
        redirector.apply(domain_list)
    except PermissionError:
        print("[x] 写入 hosts 失败: 权限不足。")
        return 1
    except OSError as exc:
        print(f"[x] 写入 hosts 失败: {exc}")
        return 1

    def safe_cleanup() -> None:
        try:
            if redirector.cleanup():
                print("\n[-] 已恢复 hosts，重定向已取消。")
        except Exception as exc:
            print(f"\n[x] 清理失败，请手动检查 hosts: {exc}")

    atexit.register(safe_cleanup)

    def signal_handler(signum, _frame):
        safe_cleanup()
        raise SystemExit(0)

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            signal.signal(sig, signal_handler)

    print("[+] 已启用重定向（0.0.0.0）：")
    for domain in domain_list:
        print(f"    - {domain}")
    print("[*] 程序运行中，按 Ctrl+C 结束并自动取消重定向。")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    safe_cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
