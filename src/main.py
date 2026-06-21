import logging

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from src.config.ajustes import ajustes
from src.dashboard.rutas_negocio import enrutador as enrutador_dashboard
from src.dashboard.rutas_operador import enrutador as enrutador_operador
from src.webhook.rutas import enrutador as enrutador_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

aplicacion = FastAPI(
    title="Bot Comprobante de Pago",
    version="1.0.0",
    docs_url="/docs" if ajustes.ambiente == "desarrollo" else None,
    redoc_url=None,
)

aplicacion.add_middleware(SessionMiddleware, secret_key=ajustes.secret_key)

aplicacion.include_router(enrutador_webhook)
aplicacion.include_router(enrutador_dashboard)
aplicacion.include_router(enrutador_operador)


@aplicacion.get("/salud")
def verificar_salud() -> dict[str, str]:
    return {"estado": "ok", "ambiente": ajustes.ambiente}
