import logging

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.config.ajustes import ajustes
from src.dashboard.rutas_negocio import enrutador as enrutador_dashboard
from src.dashboard.rutas_operador import enrutador as enrutador_operador
from src.telegram.rutas import enrutador as enrutador_telegram
from src.webhook.rutas import enrutador as enrutador_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

_SECRETS_REQUERIDOS: list[tuple[str, str]] = [
    ("webhook_secret", "WEBHOOK_SECRET"),
    ("telegram_bot_token", "TELEGRAM_BOT_TOKEN"),
    ("telegram_webhook_secret", "TELEGRAM_WEBHOOK_SECRET"),
    ("database_url", "DATABASE_URL"),
    ("secret_key", "SECRET_KEY"),
    ("operador_clave", "OPERADOR_CLAVE"),
]

_faltantes = [nombre_env for atributo, nombre_env in _SECRETS_REQUERIDOS if not getattr(ajustes, atributo)]
if _faltantes:
    raise RuntimeError(
        f"Variables de entorno requeridas no configuradas: {', '.join(_faltantes)}"
    )

logger.warning(
    "Rate limiter de login en memoria — no escalar a multiples instancias sin migrar a Redis"
)

if not ajustes.operador_telegram_chat_id:
    logger.warning("OPERADOR_TELEGRAM_CHAT_ID no configurado — comando /nuevo_cliente deshabilitado")

if not ajustes.forward_email_dominio:
    logger.warning("FORWARD_EMAIL_DOMINIO no configurado — creacion de aliases deshabilitada")

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
aplicacion.include_router(enrutador_telegram)
aplicacion.include_router(enrutador_dashboard)
aplicacion.include_router(enrutador_operador)


@aplicacion.get("/salud")
def verificar_salud() -> dict[str, str]:
    return {"estado": "ok"}
