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

_RESPUESTA_OK = {"estado": "ok"}


@enrutador.post("/email")
async def recibir_email(
    request: Request,
    secret: str = Query(default=""),
    sesion: Session = Depends(obtener_sesion),
):
    try:
        validar_secret(secret)
    except ErrorSecretInvalido as error:
        logger.warning("Webhook rechazado — secret invalido: %s", error)
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    datos = await request.json()

    # Forward Email envia JSON con estructura mailparser
    from_values = datos.get("from", {}).get("value", [{}])
    remitente_email = from_values[0].get("address", "") if from_values else ""

    # Usar envelope.to para obtener la direccion real de entrega.
    # Cuando Gmail reenvía un correo, el header "to" conserva el destinatario
    # original (ej. soydavidalarcon1@gmail.com) en lugar de negocio1@ex4cto.co.
    envelope_to = datos.get("envelope", {}).get("to", [])
    if isinstance(envelope_to, list) and envelope_to:
        correo_destinatario = envelope_to[0]
    else:
        to_values = datos.get("to", {}).get("value", [{}])
        correo_destinatario = to_values[0].get("address", "") if to_values else ""
    message_id = datos.get("messageId", "")

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

    logger.info(
        "Email recibido — de: %s, cliente: %s",
        remitente_email,
        cliente.nombre_negocio,
    )

    try:
        await procesar_pago(payload, cliente, sesion)
    except Exception as error:
        logger.exception("Error inesperado procesando pago: %s", error)

    return _RESPUESTA_OK
