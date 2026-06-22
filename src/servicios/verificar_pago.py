import html
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from src.modelos.pago import Pago
from src.notificador.telegram import enviar_mensaje
from src.repositorios import cliente_repo, pago_repo
from src.telegram.schemas import ActualizacionTelegram

logger = logging.getLogger(__name__)

_COMANDO_VERIFICAR_PAGO = "/verificar_pago"
_VENTANA_MINUTOS = 5


def _es_comando_verificar_pago(texto: str | None) -> bool:
    if not texto:
        return False
    # En grupos Telegram añade @botname al comando: /verificar_pago@mibot
    comando = texto.strip().lower().split("@")[0]
    return comando == _COMANDO_VERIFICAR_PAGO


def _formatear_monto(monto: Decimal) -> str:
    return f"${int(monto):,}".replace(",", ".")


def _formatear_respuesta(pagos: list[Pago], ahora: datetime) -> str:
    if not pagos:
        return f"Sin pagos en los ultimos {_VENTANA_MINUTOS} minutos."

    lineas = [f"<b>Pagos recibidos (ultimos {_VENTANA_MINUTOS} min):</b>\n"]
    for pago in pagos:
        segundos = int((ahora - pago.fecha_recibido).total_seconds())
        tiempo = f"{segundos // 60} min" if segundos >= 60 else f"{segundos} seg"
        lineas.append(
            f"✓ <b>{_formatear_monto(pago.monto)}</b>"
            f" de {html.escape(pago.remitente)}"
            f" — hace {tiempo}"
        )
    return "\n".join(lineas)


async def procesar_actualizacion(
    actualizacion: ActualizacionTelegram,
    sesion: Session,
) -> None:
    mensaje = actualizacion.message
    if not mensaje or not _es_comando_verificar_pago(mensaje.texto):
        return

    chat_id = str(mensaje.chat.id)
    ahora = datetime.now(timezone.utc)

    cliente = cliente_repo.obtener_por_chat_id(chat_id, sesion)
    if not cliente:
        logger.warning("Comando /verificar_pago desde chat_id desconocido: %s", chat_id)
        return

    pagos = pago_repo.listar_ultimos_minutos(cliente.id, _VENTANA_MINUTOS, ahora, sesion)
    respuesta = _formatear_respuesta(pagos, ahora)

    await enviar_mensaje(chat_id, respuesta)
    logger.info(
        "Comando /verificar_pago respondido — cliente: %s, pagos: %d",
        cliente.nombre_negocio,
        len(pagos),
    )
