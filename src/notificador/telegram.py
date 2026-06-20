import logging
from decimal import Decimal

import httpx

from src.config.ajustes import ajustes
from src.modelos.pago import Pago

logger = logging.getLogger(__name__)

_URL_API = "https://api.telegram.org/bot{token}/sendMessage"


class ErrorNotificacionTelegram(Exception):
    pass


def formatear_mensaje(pago: Pago, nombre_negocio: str) -> str:
    monto_fmt = _formatear_monto(pago.monto)
    fecha_fmt = pago.fecha_pago.strftime("%d/%m/%Y %H:%M")
    return (
        f"<b>Nuevo pago recibido</b>\n\n"
        f"<b>Negocio:</b> {nombre_negocio}\n"
        f"<b>Monto:</b> {monto_fmt}\n"
        f"<b>De:</b> {pago.remitente}\n"
        f"<b>Banco:</b> {pago.banco_origen}\n"
        f"<b>Fecha:</b> {fecha_fmt}"
    )


async def enviar_mensaje(chat_id: str, mensaje: str) -> bool:
    url = _URL_API.format(token=ajustes.telegram_bot_token)
    async with httpx.AsyncClient(timeout=10) as cliente:
        respuesta = await cliente.post(
            url,
            json={"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"},
        )
    if respuesta.status_code == 200:
        return True
    logger.error(
        "Telegram error %d para chat_id %s: %s",
        respuesta.status_code,
        chat_id,
        respuesta.text,
    )
    raise ErrorNotificacionTelegram(f"HTTP {respuesta.status_code}: {respuesta.text[:200]}")


async def notificar_todos(
    chat_ids: list[str],
    pago: Pago,
    nombre_negocio: str,
) -> dict[str, "ResultadoEnvio"]:
    from src.servicios.reintentos import ResultadoEnvio, ejecutar_con_reintentos

    mensaje = formatear_mensaje(pago, nombre_negocio)
    resultados: dict[str, ResultadoEnvio] = {}
    for chat_id in chat_ids:
        resultados[chat_id] = await ejecutar_con_reintentos(
            fn=lambda cid=chat_id: enviar_mensaje(cid, mensaje),
            max_intentos=ajustes.max_reintentos_notificacion,
            intervalo_segundos=ajustes.intervalo_reintento_segundos,
        )
    return resultados


def _formatear_monto(monto: Decimal) -> str:
    entero = int(monto)
    return f"${entero:,}".replace(",", ".")
