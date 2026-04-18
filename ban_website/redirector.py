import atexit
import ctypes
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

# Change this if needed.
TARGET_DOMAIN = "baidu.com"
REDIRECT_IP = "127.0.0.1"
TAG = "# Added by Python Redirector"

HOSTS_MODIFIED = False


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
            None, "runas", executable, f'"{script}" {params}', None, 1
        )
        if int(ret) <= 32:
            print("[x] Failed to elevate privileges.")
        sys.exit(0)
    os.execvp("sudo", ["sudo", sys.executable, *sys.argv])


def remove_hosts_entry(domain: str) -> None:
    hosts_path = get_hosts_path()
    try:
        with open(hosts_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        with open(hosts_path, "w", encoding="utf-8") as f:
            for line in lines:
                if not (domain in line and TAG in line):
                    f.write(line)

        print(f"[-] Removed hosts entries for: {domain}")
    except Exception as exc:
        print(f"[x] Failed to cleanup hosts: {exc}")


def add_hosts_entry(domain: str, ip: str = REDIRECT_IP) -> bool:
    global HOSTS_MODIFIED

    hosts_path = get_hosts_path()
    entries = [
        f"{ip} {domain} {TAG}\n",
        f"{ip} www.{domain} {TAG}\n",
    ]

    try:
        with open(hosts_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        with open(hosts_path, "w", encoding="utf-8") as f:
            for line in lines:
                if not (domain in line and TAG in line):
                    f.write(line)
            for entry in entries:
                f.write(entry)

        print(f"[+] Hosts updated: {domain} -> {ip}")
        HOSTS_MODIFIED = True
        return True
    except PermissionError:
        print("[x] Permission denied when writing hosts.")
        return False
    except Exception as exc:
        print(f"[x] Failed to update hosts: {exc}")
        return False


def cleanup() -> None:
    global HOSTS_MODIFIED
    if HOSTS_MODIFIED:
        remove_hosts_entry(TARGET_DOMAIN)
        HOSTS_MODIFIED = False


def handle_signal(_signum, _frame) -> None:
    cleanup()
    sys.exit(0)


def start_watchdog() -> None:
    watchdog_path = Path(__file__).with_name("watchdog.py")
    if not watchdog_path.exists():
        return

    env = os.environ.copy()
    env["PARENT_PID"] = str(os.getpid())
    subprocess.Popen(
        [sys.executable, str(watchdog_path)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run_redirector() -> None:
    if not is_admin():
        elevate_privileges()

    remove_hosts_entry(TARGET_DOMAIN)
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if not add_hosts_entry(TARGET_DOMAIN, REDIRECT_IP):
        sys.exit(1)

    start_watchdog()
    print(f"[*] Redirecting {TARGET_DOMAIN} to {REDIRECT_IP}. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    finally:
        cleanup()


if __name__ == "__main__":
    run_redirector()
