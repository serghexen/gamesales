from fastapi import Depends


def mount_interhub_routes(
    app,
    *,
    get_current_user,
    UserOut,
    InterHubServiceListOut,
    interhub_get_services,
):
    @app.get("/integrations/interhub/services", response_model=InterHubServiceListOut)
    def list_interhub_services(user: UserOut = Depends(get_current_user)):
        # Отдаём нормализованный каталог только авторизованным пользователям приложения.
        _ = user
        items = interhub_get_services()
        return InterHubServiceListOut(total=len(items), items=items)
