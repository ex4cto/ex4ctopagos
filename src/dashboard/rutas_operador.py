import hmac
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from time import monotonic

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.config.ajustes import ajustes
from src.config.base_datos import obtener_sesion
from src.dashboard.jinja import templates
from src.modelos.cliente import Cliente
from src.repositorios import cliente_repo, log_repo, pago_repo
from src.repositorios.pago_repo import MetricasCliente

enrutador = APIRouter(prefix="/operador", tags=["operador"])

_SESION_KEY = "operador_auth"
_DIAS_AVISO_VENCIMIENTO: int = 5
_MAX_INTENTOS_LOGIN = 5
_VENTANA_LOGIN_SEGUNDOS = 300.0
_intentos_login: dict[str, list[float]] = defaultdict(list)


def _obtener_ip(request: Request) -> str:
    return request.client.host if request.client else "desconocido"


def _limite_login_excedido(ip: str) -> bool:
    ahora = monotonic()
    _intentos_login[ip] = [t for t in _intentos_login[ip] if ahora - t < _VENTANA_LOGIN_SEGUNDOS]
    return len(_intentos_login[ip]) >= _MAX_INTENTOS_LOGIN


def _registrar_intento_fallido(ip: str) -> None:
    _intentos_login[ip].append(monotonic())


def _autenticado(request: Request) -> bool:
    return request.session.get(_SESION_KEY) is True


def _verificar_clave(clave: str) -> bool:
    if not ajustes.operador_clave:
        return False
    return hmac.compare_digest(clave.encode(), ajustes.operador_clave.encode())


def _estado_suscripcion(cliente: Cliente, ahora: datetime) -> str:
    if not cliente.suscripcion_activa:
        return "inactiva"
    if not cliente.fecha_vencimiento_suscripcion:
        return "inactiva"
    dias = (cliente.fecha_vencimiento_suscripcion - ahora).days
    if dias <= _DIAS_AVISO_VENCIMIENTO:
        return "por_vencer"
    return "activa"


def _metricas_globales(filas: list[dict]) -> dict[str, Decimal | int]:
    return {
        "pagos_hoy": sum(f["metricas"].pagos_hoy for f in filas),
        "pagos_mes": sum(f["metricas"].pagos_mes for f in filas),
        "monto_hoy": sum(f["metricas"].monto_hoy for f in filas),
        "monto_mes": sum(f["metricas"].monto_mes for f in filas),
    }


@enrutador.get("/login", response_class=HTMLResponse, response_model=None)
def get_login(request: Request) -> HTMLResponse | RedirectResponse:
    if _autenticado(request):
        return RedirectResponse("/operador/dashboard", status_code=302)
    return templates.TemplateResponse(
        "operador/login.html", {"request": request, "error": None}
    )


@enrutador.post("/login", response_model=None)
def post_login(
    request: Request, clave: str = Form(...)
) -> HTMLResponse | RedirectResponse:
    ip = _obtener_ip(request)
    if _limite_login_excedido(ip):
        return templates.TemplateResponse(
            "operador/login.html",
            {"request": request, "error": "Demasiados intentos. Espere 5 minutos."},
            status_code=429,
        )
    if _verificar_clave(clave):
        request.session[_SESION_KEY] = True
        return RedirectResponse("/operador/dashboard", status_code=302)
    _registrar_intento_fallido(ip)
    return templates.TemplateResponse(
        "operador/login.html",
        {"request": request, "error": "Clave incorrecta."},
        status_code=401,
    )


@enrutador.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/operador/login", status_code=302)


@enrutador.post("/clientes/{id_cliente}/rotar-token", response_model=None)
def rotar_token_cliente(
    id_cliente: uuid.UUID,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
) -> RedirectResponse:
    if not _autenticado(request):
        return RedirectResponse("/operador/login", status_code=302)
    cliente_repo.rotar_token(id_cliente, sesion)
    return RedirectResponse("/operador/dashboard", status_code=303)


@enrutador.post("/clientes/{id_cliente}/activar-suscripcion", response_model=None)
def activar_suscripcion_cliente(
    id_cliente: uuid.UUID,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
) -> RedirectResponse:
    if not _autenticado(request):
        return RedirectResponse("/operador/login", status_code=302)
    cliente_repo.activar_suscripcion(id_cliente, sesion)
    return RedirectResponse("/operador/dashboard", status_code=303)


@enrutador.get("/dashboard", response_class=HTMLResponse, response_model=None)
def dashboard_operador(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
) -> HTMLResponse | RedirectResponse:
    if not _autenticado(request):
        return RedirectResponse("/operador/login", status_code=302)

    ahora = datetime.now(timezone.utc)
    clientes = cliente_repo.listar_activos(sesion)
    filas = [
        {
            "cliente": c,
            "metricas": pago_repo.calcular_metricas(c.id, ahora, sesion),
            "estado_suscripcion": _estado_suscripcion(c, ahora),
            "fecha_vencimiento": c.fecha_vencimiento_suscripcion,
        }
        for c in clientes
    ]
    pagos_recientes = pago_repo.listar_recientes_global(sesion)
    fallos_recientes = log_repo.listar_fallos_recientes(sesion)

    return templates.TemplateResponse(
        "operador/dashboard.html",
        {
            "request": request,
            "filas": filas,
            "pagos_recientes": pagos_recientes,
            "fallos_recientes": fallos_recientes,
            "globales": _metricas_globales(filas),
            "total_clientes": len(clientes),
        },
    )
