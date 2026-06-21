import logging
import uuid

from sqlalchemy.orm import Session

from src.modelos.cliente import Cliente
from src.notificador import correo as correo_notificador
from src.notificador import telegram as tg_notificador
from src.parser.base import ErrorParseoBanco, detectar_banco
from src.parser.fabrica import obtener_parser
from src.repositorios import log_repo, pago_repo
from src.repositorios.log_repo import ESTADO_EXITOSO, ESTADO_FALLIDO, LogCrear
from src.repositorios.pago_repo import PagoCrear
from src.servicios.reintentos import ResultadoEnvio
from src.webhook.schemas import PayloadEmail

logger = logging.getLogger(__name__)


async def procesar_pago(
    payload: PayloadEmail,
    cliente: Cliente,
    sesion: Session,
) -> None:
    banco = detectar_banco(payload.remitente_email)
    if not banco:
        logger.warning(
            "Banco no reconocido para remitente '%s' — email ignorado",
            payload.remitente_email,
        )
        return

    logger.info("Contenido texto plano: %.500s", payload.cuerpo_texto)
    logger.info("Contenido html: %.500s", payload.cuerpo_html)

    try:
        pago_extraido = obtener_parser(banco).parsear(
            payload.cuerpo_html,
            payload.cuerpo_texto,
        )
    except ErrorParseoBanco as error:
        logger.error("Error parseando email de %s: %s", banco, error)
        return

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
    logger.info(
        "Pago %s guardado — monto: %s, remitente: %s",
        pago.id,
        pago.monto,
        pago.remitente,
    )

    chat_ids: list[str] = cliente.telegram_chat_ids or []
    if chat_ids:
        resultados_tg = await tg_notificador.notificar_todos(chat_ids, pago, cliente.nombre_negocio)
        for chat_id, resultado in resultados_tg.items():
            _guardar_log(pago.id, "telegram", chat_id, resultado, sesion)
        if any(r.exito for r in resultados_tg.values()):
            pago.notificado_telegram = True

    correos: list[str] = cliente.correos_notificacion or []
    if correos:
        resultados_email = await correo_notificador.notificar_todos(correos, pago, cliente.nombre_negocio)
        for correo, resultado in resultados_email.items():
            _guardar_log(pago.id, "correo", correo, resultado, sesion)
        if any(r.exito for r in resultados_email.values()):
            pago.notificado_correo = True

    sesion.commit()


def _guardar_log(
    pago_id: uuid.UUID,
    canal: str,
    destinatario: str,
    resultado: ResultadoEnvio,
    sesion: Session,
) -> None:
    log_repo.crear(
        LogCrear(
            pago_id=pago_id,
            canal=canal,
            destinatario=destinatario,
            estado=ESTADO_EXITOSO if resultado.exito else ESTADO_FALLIDO,
            intentos=resultado.intentos,
            error=resultado.error,
        ),
        sesion,
    )
