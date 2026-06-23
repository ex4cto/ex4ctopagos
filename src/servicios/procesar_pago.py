import logging
import uuid

from sqlalchemy.orm import Session

from src.modelos.cliente import Cliente
from src.modelos.pago import Pago
from src.parser.base import ErrorParseoBanco, detectar_banco
from src.parser.fabrica import obtener_parser
from src.repositorios import pago_repo
from src.repositorios.pago_repo import PagoCrear
from src.webhook.schemas import PagoExtraido, PayloadEmail

logger = logging.getLogger(__name__)


def parsear_pago_email(payload: PayloadEmail) -> PagoExtraido | None:
    banco = detectar_banco(payload.remitente_email)
    if not banco:
        logger.warning(
            "Banco no reconocido para remitente '%s' — email ignorado",
            payload.remitente_email,
        )
        return None
    try:
        return obtener_parser(banco).parsear(payload.cuerpo_html, payload.cuerpo_texto)
    except ErrorParseoBanco as error:
        logger.error("Error parseando email de %s: %s", banco, error)
        return None


async def guardar_pago(
    payload: PayloadEmail,
    cliente: Cliente,
    sesion: Session,
) -> Pago | None:
    pago_extraido = parsear_pago_email(payload)
    if not pago_extraido:
        return None

    pago = pago_repo.crear(
        PagoCrear(
            cliente_id=cliente.id,
            monto=pago_extraido.monto,
            remitente=pago_extraido.remitente,
            banco_origen=pago_extraido.banco_origen,
            fecha_pago=pago_extraido.fecha_pago,
            email_raw=payload.cuerpo_texto,
            token_idempotencia=payload.message_id,
        ),
        sesion,
    )
    logger.debug(
        "Pago %s guardado — monto: %s, remitente: %s",
        pago.id,
        pago.monto,
        pago.remitente,
    )
    return pago


async def notificar_background(pago_id: uuid.UUID, cliente_id: uuid.UUID) -> None:
    # Función reservada para futuros canales de notificación automática.
    # Actualmente el correo se envía desde /verificar_pago, no aquí.
    pass


