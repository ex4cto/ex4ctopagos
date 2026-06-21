import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.config.base_datos import obtener_sesion
from src.repositorios import cliente_repo, pago_repo
from src.servicios.procesar_pago import procesar_pago
from src.webhook.schemas import PayloadEmail
from src.webhook.validador import ErrorSecretInvalido, validar_secret

logger = logging.getLogger(__name__)

enrutador = APIRouter(prefix="/webhook", tags=["webhook"])

_RESPUESTA_OK: dict[str, str] = {"estado": "ok"}


def _extraer_remitente(datos: dict) -> str:
    from_values = datos.get("from", {}).get("value", [{}])
    return from_values[0].get("address", "") if from_values else ""


def _extraer_correo_destinatario(datos: dict) -> str:
    # envelope.to tiene la dirección real de entrega; el header "to" preserva
    # el destinatario original cuando Gmail reenvía el correo al alias.
    envelope_to = datos.get("envelope", {}).get("to", [])
    if isinstance(envelope_to, list) and envelope_to:
        return envelope_to[0]
    to_values = datos.get("to", {}).get("value", [{}])
    return to_values[0].get("address", "") if to_values else ""


@enrutador.post("/email")
async def recibir_email(
    request: Request,
    secret: str = Query(default=""),
    sesion: Session = Depends(obtener_sesion),
) -> JSONResponse | dict[str, str]:
    try:
        validar_secret(secret)
    except ErrorSecretInvalido as error:
        logger.warning("Webhook rechazado — secret invalido: %s", error)
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    datos = await request.json()
    remitente_email = _extraer_remitente(datos)
    correo_destinatario = _extraer_correo_destinatario(datos)
    message_id: str = datos.get("messageId", "")

    if not message_id:
        logger.warning("Email sin messageId — ignorado")
        return _RESPUESTA_OK

    if pago_repo.existe_token(message_id, sesion):
        logger.info("Email duplicado ignorado — messageId: %s", message_id)
        return _RESPUESTA_OK

    cliente = cliente_repo.obtener_por_correo_dedicado(correo_destinatario, sesion)
    if not cliente:
        logger.warning("Cliente no encontrado para correo '%s'", correo_destinatario)
        return _RESPUESTA_OK

    payload = PayloadEmail(
        message_id=message_id,
        remitente_email=remitente_email,
        correo_destinatario=correo_destinatario,
        asunto=datos.get("subject", ""),
        cuerpo_html=datos.get("html", "") or "",
        cuerpo_texto=datos.get("text", "") or "",
    )

    logger.info("Email recibido — de: %s, cliente: %s", remitente_email, cliente.nombre_negocio)

    try:
        await procesar_pago(payload, cliente, sesion)
    except Exception as error:
        logger.exception("Error inesperado procesando pago: %s", error)

    return _RESPUESTA_OK
