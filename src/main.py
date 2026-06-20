from fastapi import FastAPI

from src.config.ajustes import ajustes
from src.dashboard.rutas_negocio import enrutador as enrutador_dashboard
from src.webhook.rutas import enrutador as enrutador_webhook

aplicacion = FastAPI(
    title="Bot Comprobante de Pago",
    version="1.0.0",
    docs_url="/docs" if ajustes.ambiente == "desarrollo" else None,
    redoc_url=None,
)

aplicacion.include_router(enrutador_webhook)
aplicacion.include_router(enrutador_dashboard)


@aplicacion.get("/salud")
def verificar_salud() -> dict[str, str]:
    return {"estado": "ok", "ambiente": ajustes.ambiente}
