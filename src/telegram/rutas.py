import logging

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.config.base_datos import obtener_sesion
from src.servicios.verificar_pago import procesar_actualizacion
from src.telegram.schemas import ActualizacionTelegram
from src.telegram.validador import ErrorTokenTelegramInvalido, validar_token_telegram

logger = logging.getLogger(__name__)

enrutador = APIRouter(prefix="/telegram", tags=["telegram"])

_RESPUESTA_OK: dict[str, str] = {"estado": "ok"}


@enrutador.post("/webhook", response_model=None)
async def recibir_actualizacion(
    actualizacion: ActualizacionTelegram,
    x_telegram_bot_api_secret_token: str = Header(default=""),
    sesion: Session = Depends(obtener_sesion),
) -> dict[str, str] | JSONResponse:
    try:
        validar_token_telegram(x_telegram_bot_api_secret_token)
    except ErrorTokenTelegramInvalido as error:
        logger.warning("Webhook Telegram rechazado: %s", error)
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    await procesar_actualizacion(actualizacion, sesion)
    return _RESPUESTA_OK
