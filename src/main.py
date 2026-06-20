from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config.ajustes import ajustes

aplicacion = FastAPI(
    title="Bot Comprobante de Pago",
    version="1.0.0",
    docs_url="/docs" if ajustes.ambiente == "desarrollo" else None,
    redoc_url=None,
)


@aplicacion.get("/salud")
def verificar_salud() -> dict[str, str]:
    return {"estado": "ok", "ambiente": ajustes.ambiente}
