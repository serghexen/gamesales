"""Отдельный SSH-forward к Airpay, совместимый с запущенным туннелем Interhub."""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


def build_tunnel_command(environ):
    # Используем тот же SSH-сервер, но отдельный локальный порт и HTTPS-адрес Airpay.
    host = (environ.get('AIRPAY_TUNNEL_HOST') or environ.get('INTERHUB_TUNNEL_HOST') or '').strip()
    if not host:
        raise ValueError('Укажите AIRPAY_TUNNEL_HOST или INTERHUB_TUNNEL_HOST в .env.dev')
    try:
        port = int(environ.get('AIRPAY_TUNNEL_LOCAL_PORT', '3129'))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('AIRPAY_TUNNEL_LOCAL_PORT должен быть числом от 1 до 65535') from None
    endpoint = urlsplit(environ.get('AIRPAY_API_URL', 'https://api.airpay.kz/AirPayService/api/v20'))
    if endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password:
        raise ValueError('AIRPAY_API_URL должен быть HTTPS-адресом поставщика без реквизитов')
    return ['ssh', '-N', '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30',
            '-o', 'ServerAliveCountMax=3', '-L',
            f'127.0.0.1:{port}:{endpoint.hostname}:{endpoint.port or 443}', host]


def main():
    # Читаем локальные настройки только при запуске команды, не открывая туннель при импорте.
    load_dotenv(Path(__file__).resolve().parents[2] / '.env.dev', override=True)
    try:
        command = build_tunnel_command(os.environ)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print('Airpay HTTPS tunnel: запуск SSH-forward', flush=True)
    return subprocess.run(command, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
