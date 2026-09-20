"""Ограничения локального просмотра UI без запуска серверных фоновых задач."""

from urllib.parse import urlsplit


def require_staging_tunnel(dsn):
    # Не позволяем случайно запустить локальный просмотр с production-подключением.
    try:
        target = urlsplit(dsn)
        allowed = (target.scheme in {'postgres', 'postgresql'}
                   and target.hostname == '127.0.0.1'
                   and target.port == 5433 and target.path == '/gamesales_staging')
    except (TypeError, ValueError):
        allowed = False
    if not allowed:
        raise RuntimeError('Локальный UI требует staging-туннель 127.0.0.1:5433/gamesales_staging; проверьте .env.dev')


def local_interhub_tunnel_port(environ):
    # Клиент использует тот же локальный порт, что и SSH-forward к HTTPS Интерхаба.
    try:
        port = int(environ.get('INTERHUB_TUNNEL_LOCAL_PORT', '3128'))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        raise RuntimeError('INTERHUB_TUNNEL_LOCAL_PORT должен быть числом от 1 до 65535') from None
    return port
