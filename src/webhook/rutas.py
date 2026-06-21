import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.config.base_datos import obtener_sesion
from src.repositorios import cliente_repo, pago_repo
from src.servicios.procesar_pago import guardar_pago, notificar_background
from src.webhook.schemas import PayloadEmail
from src.webhook.validador import ErrorSecretInvalido, validar_secret

logger = logging.getLogger(__name__)

enrutador = APIRouter(prefix="/webhook", tags=["webhook"])

_RESPUESTA_OK: dict[str, str] = {"estado": "ok"}

# Claves del payload JSON de Forward Email webhook
_CLAVE_FROM = "from"
_CLAVE_VALUE = "value"
_CLAVE_ADDRESS = "address"
_CLAVE_MESSAGE_ID = "messageId"
_CLAVE_SUBJECT = "subject"
_CLAVE_HTML = "html"
_CLAVE_TEXT = "text"


def _extraer_remitente(datos: dict) -> str:
    from_values = datos.get(_CLAVE_FROM, {}).get(_CLAVE_VALUE, [{}])
    return from_values[0].get(_CLAVE_ADDRESS, "") if from_values else ""


@enrutador.post("/email", response_model=None)
async def recibir_email(
    request: Request,
    background_tasks: BackgroundTasks,
    secret: str = Query(default=""),
    correo: str = Query(default=""),
    sesion: Session = Depends(obtener_sesion),
) -> JSONResponse | dict[str, str]:
    # Preferir header sobre query param — el header no queda en logs del proxy
    secret_efectivo = request.headers.get("X-Webhook-Secret", secret)
    try:
        validar_secret(secret_efectivo)
    except ErrorSecretInvalido as error:
        logger.warning("Webhook rechazado — secret invalido: %s", error)
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    if not correo:
        logger.warning("Webhook sin parametro correo — ignorado")
        return _RESPUESTA_OK

    try:
        datos = await request.json()
    except Exception:
        logger.warning("Webhook con body JSON invalido — ignorado")
        return _RESPUESTA_OK
    remitente_email = _extraer_remitente(datos)
    message_id: str = datos.get(_CLAVE_MESSAGE_ID, "")

    if not message_id:
        logger.warning("Email sin messageId — ignorado")
        return _RESPUESTA_OK

    if pago_repo.existe_token(message_id, sesion):
        logger.info("Email duplicado ignorado — messageId: %s", message_id)
        return _RESPUESTA_OK

    cliente = cliente_repo.obtener_por_correo_dedicado(correo, sesion)
    if not cliente:
        logger.warning("Cliente no encontrado para correo '%s'", correo)
        return _RESPUESTA_OK

    payload = PayloadEmail(
        message_id=message_id,
        remitente_email=remitente_email,
        correo_destinatario=correo,
        asunto=datos.get(_CLAVE_SUBJECT, ""),
        cuerpo_html=datos.get(_CLAVE_HTML, "") or "",
        cuerpo_texto=datos.get(_CLAVE_TEXT, "") or "",
    )

    logger.info("Email recibido — de: %s, cliente: %s", remitente_email, cliente.nombre_negocio)

    try:
        pago = await guardar_pago(payload, cliente, sesion)
    except Exception as error:
        logger.exception("Error inesperado guardando pago: %s", error)
        return _RESPUESTA_OK

    if pago is not None:
        background_tasks.add_task(notificar_background, pago.id, cliente.id)

    return _RESPUESTA_OK
