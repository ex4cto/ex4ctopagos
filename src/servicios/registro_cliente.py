import html
import logging
import re
import time

from sqlalchemy.orm import Session

from src.config.ajustes import ajustes
from src.repositorios import cliente_repo
from src.repositorios.cliente_repo import ErrorClienteDuplicado
from src.servicios import alias_forward_email
from src.servicios.alias_forward_email import ErrorCrearAlias

logger = logging.getLogger(__name__)

_TIMEOUT_SESION_SEGUNDOS = 600
_COMANDO_NUEVO_CLIENTE = "/nuevo_cliente"
_COMANDO_MI_DASHBOARD = "/mi_dashboard"
_COMANDO_DASHBOARD = "/dashboard"
_RE_ALIAS_VALIDO = re.compile(r"^[a-z0-9][a-z0-9\-]{0,61}[a-z0-9]$|^[a-z0-9]$")
_RE_CHAT_ID_VALIDO = re.compile(r"^\d+$")

_sesiones_registro: dict[str, dict] = {}


def _detectar_comando(texto: str | None, comando: str) -> bool:
    if not texto:
        return False
    return texto.strip().lower().split("@")[0] == comando


def es_comando_nuevo_cliente(texto: str | None) -> bool:
    return _detectar_comando(texto, _COMANDO_NUEVO_CLIENTE)


def es_comando_mi_dashboard(texto: str | None) -> bool:
    return _detectar_comando(texto, _COMANDO_MI_DASHBOARD)


def es_comando_dashboard(texto: str | None) -> bool:
    return _detectar_comando(texto, _COMANDO_DASHBOARD)


def responder_mi_dashboard() -> str:
    return f"🔗 Tu panel de operador:\n{ajustes.app_url}/operador/dashboard"


def responder_dashboard_cliente(chat_id: str, sesion: Session) -> str | None:
    cliente = cliente_repo.obtener_por_chat_id(chat_id, sesion)
    if not cliente:
        return None
    url = f"{ajustes.app_url}/dashboard/{cliente.token_dashboard}"
    return f"🔗 Dashboard de {html.escape(cliente.nombre_negocio)}:\n{url}"


def _sesion_expirada(sesion: dict) -> bool:
    return time.time() - sesion["timestamp"] > _TIMEOUT_SESION_SEGUNDOS


def _limpiar_sesion(chat_id: str) -> None:
    _sesiones_registro.pop(chat_id, None)


def _formatear_confirmacion(
    nombre_negocio: str,
    correo_dedicado: str,
    token_dashboard: object,
) -> str:
    dominio = ajustes.forward_email_dominio
    url_dashboard = f"{ajustes.app_url}/dashboard/{token_dashboard}"
    return (
        f"✅ Cliente registrado.\n"
        f"📧 Alias: {html.escape(correo_dedicado)}\n"
        f"🔗 Dashboard: {url_dashboard}\n\n"
        f"📋 Filtro Gmail (el dueño debe hacer esto):\n"
        f"1. Gmail → Ajustes → Filtros y direcciones bloqueadas → Crear filtro\n"
        f"2. Campo <b>De</b>: @notificacionesbancolombia.com OR @nequi.com.co\n"
        f"3. Acción: Reenviar a <b>{html.escape(correo_dedicado)}</b>\n"
        f"4. Guardar filtro"
    )


async def procesar_mensaje_operador(
    chat_id: str,
    texto: str,
    sesion: Session,
) -> str | None:
    estado = _sesiones_registro.get(chat_id)

    if estado and _sesion_expirada(estado):
        _limpiar_sesion(chat_id)
        estado = None

    if estado is None:
        if es_comando_mi_dashboard(texto):
            return responder_mi_dashboard()
        if not es_comando_nuevo_cliente(texto):
            return None
        _sesiones_registro[chat_id] = {"paso": "nombre", "datos": {}, "timestamp": time.time()}
        return "¿Cuál es el nombre del negocio?"

    estado["timestamp"] = time.time()
    paso = estado["paso"]

    if paso == "nombre":
        estado["datos"]["nombre_negocio"] = texto.strip()
        estado["paso"] = "alias"
        dominio = ajustes.forward_email_dominio or "ex4cto.co"
        return f"¿Cuál es el identificador del alias? (ej: panaderia → panaderia@{dominio})"

    if paso == "alias":
        alias = texto.strip().lower()
        if not _RE_ALIAS_VALIDO.match(alias):
            return "Alias inválido. Usá solo letras minúsculas, números y guiones (sin espacios ni caracteres especiales). Intentá de nuevo."
        estado["datos"]["alias"] = alias
        estado["paso"] = "nombre_titular"
        return "¿Nombre completo del titular de la cuenta bancaria? (como aparece en transferencias — ej: PEDRO GARCIA LOPEZ)"

    if paso == "nombre_titular":
        estado["datos"]["nombre_titular_cuenta"] = texto.strip()
        estado["paso"] = "telegram_dueno"
        return "¿Chat ID de Telegram del dueño del negocio? (solo números — escribe «ninguno» si no aplica)"

    if paso == "telegram_dueno":
        texto_limpio = texto.strip().lower()
        if texto_limpio != "ninguno" and not _RE_CHAT_ID_VALIDO.match(texto.strip()):
            return "Chat ID inválido. Debe contener solo números. Intentá de nuevo o escribí «ninguno»."
        estado["datos"]["telegram_chat_id_dueno"] = None if texto_limpio == "ninguno" else texto.strip()
        estado["paso"] = "correos_notificacion"
        return "¿Correos de notificación del empleado? (separados por coma, o escribe «ninguno»)"

    if paso == "correos_notificacion":
        texto_limpio = texto.strip().lower()
        correos = [] if texto_limpio == "ninguno" else [c.strip() for c in texto.split(",") if c.strip()]
        datos = estado["datos"]
        alias = datos["alias"]
        correo_dedicado = f"{alias}@{ajustes.forward_email_dominio}"

        try:
            cliente = cliente_repo.crear(
                nombre_negocio=datos["nombre_negocio"],
                correo_dedicado=correo_dedicado,
                telegram_chat_ids=[],
                correos_notificacion=correos,
                sesion=sesion,
                telegram_chat_id_dueno=datos.get("telegram_chat_id_dueno"),
                nombre_titular_cuenta=datos.get("nombre_titular_cuenta"),
            )
        except ErrorClienteDuplicado:
            _limpiar_sesion(chat_id)
            return f"❌ Ya existe un cliente con el correo {html.escape(correo_dedicado)}. Usá otro alias."

        try:
            await alias_forward_email.crear_alias(alias)
        except ErrorCrearAlias as exc:
            logger.warning(
                "Cliente creado (id=%s) pero alias Forward Email falló: %s",
                cliente.id,
                exc,
            )
            _limpiar_sesion(chat_id)
            return (
                f"⚠️ Cliente registrado en BD pero el alias no se creó automáticamente.\n"
                f"Creá el alias manualmente en Forward Email para: {html.escape(correo_dedicado)}\n"
                f"🔗 Dashboard: {ajustes.app_url}/dashboard/{cliente.token_dashboard}"
            )

        _limpiar_sesion(chat_id)
        return _formatear_confirmacion(datos["nombre_negocio"], correo_dedicado, cliente.token_dashboard)

    return None
