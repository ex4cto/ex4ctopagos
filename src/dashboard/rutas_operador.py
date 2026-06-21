import hmac
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.config.ajustes import ajustes
from src.config.base_datos import obtener_sesion
from src.dashboard.jinja import templates
from src.repositorios import cliente_repo, pago_repo
from src.repositorios.pago_repo import MetricasCliente

enrutador = APIRouter(prefix="/operador", tags=["operador"])

_SESION_KEY = "operador_auth"


def _autenticado(request: Request) -> bool:
    return request.session.get(_SESION_KEY) is True


def _verificar_clave(clave: str) -> bool:
    if not ajustes.operador_clave:
        return False
    return hmac.compare_digest(clave.encode(), ajustes.operador_clave.encode())


def _metricas_globales(filas: list[dict]) -> dict[str, Decimal | int]:
    return {
        "pagos_hoy": sum(f["metricas"].pagos_hoy for f in filas),
        "pagos_mes": sum(f["metricas"].pagos_mes for f in filas),
        "monto_hoy": sum(f["metricas"].monto_hoy for f in filas),
        "monto_mes": sum(f["metricas"].monto_mes for f in filas),
    }


@enrutador.get("/login", response_class=HTMLResponse)
def get_login(request: Request) -> HTMLResponse:
    if _autenticado(request):
        return RedirectResponse("/operador/dashboard", status_code=302)
    return templates.TemplateResponse(
        "operador/login.html", {"request": request, "error": None}
    )


@enrutador.post("/login")
def post_login(
    request: Request, clave: str = Form(...)
) -> HTMLResponse | RedirectResponse:
    if _verificar_clave(clave):
        request.session[_SESION_KEY] = True
        return RedirectResponse("/operador/dashboard", status_code=302)
    return templates.TemplateResponse(
        "operador/login.html",
        {"request": request, "error": "Clave incorrecta."},
        status_code=401,
    )


@enrutador.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/operador/login", status_code=302)


@enrutador.get("/dashboard", response_class=HTMLResponse)
def dashboard_operador(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
) -> HTMLResponse | RedirectResponse:
    if not _autenticado(request):
        return RedirectResponse("/operador/login", status_code=302)

    ahora = datetime.now(timezone.utc)
    clientes = cliente_repo.listar_activos(sesion)
    filas = [
        {"cliente": c, "metricas": pago_repo.calcular_metricas(c.id, ahora, sesion)}
        for c in clientes
    ]
    pagos_recientes = pago_repo.listar_recientes_global(sesion)

    return templates.TemplateResponse(
        "operador/dashboard.html",
        {
            "request": request,
            "filas": filas,
            "pagos_recientes": pagos_recientes,
            "globales": _metricas_globales(filas),
            "total_clientes": len(clientes),
        },
    )
