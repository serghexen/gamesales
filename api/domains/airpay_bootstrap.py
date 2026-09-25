"""Подключение Airpay целиком либо отказ только его маршрутов, без fallback."""
from urllib.parse import urlsplit


def mount_airpay_isolated(app, *, get_current_user, environ, connect, get_secret, code_secret, local_ui, offline):
    # Сначала собираем отдельный набор маршрутов: ошибка не оставляет работающий наполовину Airpay.
    from fastapi import FastAPI
    backend = environ.get('AIRPAY_BACKEND', 'crm').strip().lower()
    if backend not in {'crm', 'hub'}:
        raise ValueError('Invalid Airpay backend')
    candidate = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    candidate.router.lifespan_context = app.router.lifespan_context
    if backend == 'hub':
        # Неверная конфигурация Hub никогда не переключает платежи на прямой CRM.
        target = urlsplit(environ.get('AIRPAY_HUB_URL', ''))
        if (target.scheme not in {'http', 'https'} or not target.hostname or target.username or target.password
                or target.query or target.fragment or (target.port is not None and not 1 <= target.port <= 65535)
                or not environ.get('AIRPAY_HUB_CLIENT_ID', '').strip()
                or len(environ.get('AIRPAY_HUB_CLIENT_KEY', '').strip()) < 32):
            raise ValueError('Invalid Airpay Hub configuration')
        from domains.airpay_hub_client import mount_airpay_hub_proxy
        mount_airpay_hub_proxy(candidate, get_current_user=get_current_user, environ=environ,
                              restricted=local_ui or offline, legacy_connect=connect, legacy_secret=code_secret)
    else:
        # Импорты необязательного поставщика не должны происходить при загрузке всего приложения CRM.
        from domains.airpay_service import build_airpay_service
        from domains.airpay_repository import AirpayRepository
        from domains.airpay_jobs import AirpayJobStore
        from domains.airpay_api import mount_airpay_routes
        mount_airpay_routes(candidate, get_current_user=get_current_user,
                            service=build_airpay_service(environ, local_ui=local_ui), get_secret=get_secret,
                            offline=offline, repository=AirpayRepository(connect, code_secret=code_secret),
                            job_store=AirpayJobStore(connect))
    # Публикуем маршруты и lifecycle только после успешной сборки, сохраняя прежние обработчики CRM.
    app.router.routes.extend(candidate.router.routes)
    app.user_middleware.extend(candidate.user_middleware)
    app.router.lifespan_context = candidate.router.lifespan_context
    app.state.airpay_backend = backend
