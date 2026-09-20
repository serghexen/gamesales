"""Прокладывает SSH-туннель непосредственно к HTTPS поставщика с IP сервера."""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

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


def build_tunnel_command():
    # SSH сам подключается к поставщику; на сервере не нужен слушающий порт proxy.
    tunnel_host = str(os.getenv("INTERHUB_TUNNEL_HOST", "")).strip()
    if not tunnel_host:
        raise ValueError('Укажите INTERHUB_TUNNEL_HOST в .env.dev')
    local_port = read_port('INTERHUB_TUNNEL_LOCAL_PORT', 3128)
    endpoint = urlsplit(os.getenv('INTERHUB_API_URL', ''))
    if endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password:
        raise ValueError('INTERHUB_API_URL должен быть HTTPS-адресом поставщика без реквизитов')
    remote_port = endpoint.port or 443
    return [
        "ssh", "-N", "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
        "-L", f"127.0.0.1:{local_port}:{endpoint.hostname}:{remote_port}",
        tunnel_host,
    ]


def main() -> int:
    # Ошибки настройки показываем до запуска, чтобы SSH не оставил бесполезный локальный порт.
    try:
        command = build_tunnel_command()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f'InterHub HTTPS tunnel: {command[-2]} via {command[-1]}', flush=True)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
