import logging

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.config.ajustes import ajustes
from src.dashboard.rutas_negocio import enrutador as enrutador_dashboard
from src.dashboard.rutas_operador import enrutador as enrutador_operador
from src.webhook.rutas import enrutador as enrutador_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

_CLAVE_SESION_DEFAULT = "cambia-esto-en-produccion"

if ajustes.ambiente == "produccion" and ajustes.secret_key == _CLAVE_SESION_DEFAULT:
    raise RuntimeError(
        "SECRET_KEY no configurada con valor seguro — no se puede arrancar en produccion"
    )

aplicacion = FastAPI(
    title="Bot Comprobante de Pago",
    version="1.0.0",
    docs_url="/docs" if ajustes.ambiente == "desarrollo" else None,
    redoc_url=None,
)

aplicacion.add_middleware(
    SessionMiddleware,
    secret_key=ajustes.secret_key,
    https_only=ajustes.ambiente == "produccion",
    same_site="strict",
    max_age=3600,
)


class _CabecerasSeguridad(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        respuesta = await call_next(request)
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if ajustes.ambiente == "produccion":
            respuesta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return respuesta


aplicacion.add_middleware(_CabecerasSeguridad)

aplicacion.include_router(enrutador_webhook)
aplicacion.include_router(enrutador_dashboard)
aplicacion.include_router(enrutador_operador)


@aplicacion.get("/salud")
def verificar_salud() -> dict[str, str]:
    return {"estado": "ok"}
