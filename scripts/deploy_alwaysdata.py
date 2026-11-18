"""Загрузка CookieKub backend на Alwaysdata по SFTP/SSH."""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import paramiko

HOST = "ssh-cookiekub.alwaysdata.net"
USER = "cookiekub"
REMOTE_ROOT = "/home/cookiekub/cookiekub"
PASSWORD = Path(r"F:\CodeProject\.secrets\alwaysdata.txt").read_text(encoding="utf-8").strip()
LOCAL = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}


def ensure_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    parts = []
    for part in Path(path).parts:
        if part == "/":
            parts = ["/"]
            continue
        parts.append(part)
        current = "/".join(parts).replace("//", "/")
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def upload_tree(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    ensure_dir(sftp, remote)
    for item in sorted(local.iterdir()):
        if item.name in SKIP_DIRS or item.name.endswith(".pyc"):
            continue
        target = f"{remote}/{item.name}"
        if item.is_dir():
            upload_tree(sftp, item, target)
        elif item.is_file():
            sftp.put(str(item), target)
            print("uploaded", target)


def main() -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30, banner_timeout=30, auth_timeout=30)
    sftp = client.open_sftp()
    upload_tree(sftp, LOCAL / "backend", f"{REMOTE_ROOT}/backend")
    sftp.put(str(LOCAL / "requirements.txt"), f"{REMOTE_ROOT}/requirements.txt")
    sftp.close()
    commands = [
        "python3 --version",
        f"mkdir -p {REMOTE_ROOT}",
        f"cd {REMOTE_ROOT} && test -d /home/cookiekub/venv || python3 -m venv /home/cookiekub/venv",
        f"cd {REMOTE_ROOT} && /home/cookiekub/venv/bin/pip install --quiet -r requirements.txt",
        f"cd {REMOTE_ROOT} && /home/cookiekub/venv/bin/python -c 'import flask, psycopg; print(flask.__version__, psycopg.__version__)'",
    ]
    for command in commands:
        print("$", command)
        _stdin, stdout, stderr = client.exec_command(command, timeout=180)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        code = stdout.channel.recv_exit_status()
        print(out.strip())
        if err.strip():
            print("STDERR:", err.strip())
        if code != 0:
            print("FAILED with", code)
            client.close()
            return code
    client.close()
    print("ALWAYSDATA UPLOAD OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
