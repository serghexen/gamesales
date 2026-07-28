"""Запускает локальный SSH-туннель к proxy поставщика из .env.dev."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env.dev", override=True)


def read_port(name: str, fallback: int) -> int:
    # Проверяет порт до запуска SSH, чтобы ошибка настройки была понятна сразу.
    try:
        port = int(os.getenv(name, str(fallback)))
    except ValueError as exc:
        raise ValueError(f"{name} должен быть числом") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"{name} должен быть в диапазоне 1-65535")
    return port


def main() -> int:
    # Собирает туннель только по явным локальным настройкам, не сохраняя серверные реквизиты в Git.
    tunnel_host = str(os.getenv("INTERHUB_TUNNEL_HOST", "")).strip()
    if not tunnel_host:
        print("Укажите INTERHUB_TUNNEL_HOST в .env.dev", file=sys.stderr)
        return 2
    try:
        local_port = read_port("INTERHUB_TUNNEL_LOCAL_PORT", 3128)
        remote_port = read_port("INTERHUB_TUNNEL_REMOTE_PORT", 3128)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    command = [
        "ssh", "-N", "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
        "-L", f"127.0.0.1:{local_port}:127.0.0.1:{remote_port}",
        tunnel_host,
    ]
    print(f"InterHub tunnel: 127.0.0.1:{local_port} -> {tunnel_host}:127.0.0.1:{remote_port}")
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
