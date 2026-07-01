import logging

import httpx

from src.config.ajustes import ajustes

logger = logging.getLogger(__name__)

_URL_BASE_API = "https://api.forwardemail.net/v1/domains"


class ErrorCrearAlias(Exception):
    pass


class ErrorActualizarAlias(Exception):
    pass


def _url_webhook_para_alias(nombre_alias: str) -> str:
    correo_dedicado = f"{nombre_alias}@{ajustes.forward_email_dominio}"
    return (
        f"{ajustes.app_url}/webhook/email"
        f"?secret={ajustes.webhook_secret}"
        f"&correo={correo_dedicado}"
    )


async def crear_alias(nombre_alias: str) -> str:
    correo_dedicado = f"{nombre_alias}@{ajustes.forward_email_dominio}"
    url_webhook = _url_webhook_para_alias(nombre_alias)
    url = f"{_URL_BASE_API}/{ajustes.forward_email_dominio}/aliases"
    auth = (ajustes.correo_clave, "")
    cuerpo = {"name": nombre_alias, "recipients": [url_webhook]}

    async with httpx.AsyncClient(timeout=15) as cliente:
        respuesta = await cliente.post(url, json=cuerpo, auth=auth)

    if respuesta.status_code not in (200, 201):
        raise ErrorCrearAlias(
            f"Forward Email API error {respuesta.status_code}: {respuesta.text[:200]}"
        )

    logger.info("Alias creado en Forward Email: %s", correo_dedicado)
    return correo_dedicado


async def _obtener_id_alias(nombre_alias: str) -> str | None:
    url = f"{_URL_BASE_API}/{ajustes.forward_email_dominio}/aliases"
    auth = (ajustes.correo_clave, "")

    async with httpx.AsyncClient(timeout=15) as cliente:
        respuesta = await cliente.get(url, auth=auth)

    if respuesta.status_code not in (200, 201):
        return None

    for entrada in respuesta.json():
        if entrada.get("name") == nombre_alias:
            return str(entrada.get("id"))

    return None


async def agregar_destinatario_confirmacion(nombre_alias: str) -> None:
    alias_id = await _obtener_id_alias(nombre_alias)
    if not alias_id:
        raise ErrorActualizarAlias(f"No se encontró el alias: {nombre_alias}")

    url_webhook = _url_webhook_para_alias(nombre_alias)
    url = f"{_URL_BASE_API}/{ajustes.forward_email_dominio}/aliases/{alias_id}"
    auth = (ajustes.correo_clave, "")
    cuerpo = {"recipients": [url_webhook, ajustes.correo_confirmacion_alias]}

    async with httpx.AsyncClient(timeout=15) as cliente:
        respuesta = await cliente.put(url, json=cuerpo, auth=auth)

    if respuesta.status_code not in (200, 201):
        raise ErrorActualizarAlias(
            f"Forward Email API error {respuesta.status_code}: {respuesta.text[:200]}"
        )

    logger.info("Destinatario de confirmacion agregado al alias: %s", nombre_alias)


async def remover_destinatario_confirmacion(nombre_alias: str) -> None:
    alias_id = await _obtener_id_alias(nombre_alias)
    if not alias_id:
        raise ErrorActualizarAlias(f"No se encontró el alias: {nombre_alias}")

    url_webhook = _url_webhook_para_alias(nombre_alias)
    url = f"{_URL_BASE_API}/{ajustes.forward_email_dominio}/aliases/{alias_id}"
    auth = (ajustes.correo_clave, "")
    cuerpo = {"recipients": [url_webhook]}

    async with httpx.AsyncClient(timeout=15) as cliente:
        respuesta = await cliente.put(url, json=cuerpo, auth=auth)

    if respuesta.status_code not in (200, 201):
        raise ErrorActualizarAlias(
            f"Forward Email API error {respuesta.status_code}: {respuesta.text[:200]}"
        )

    logger.info("Destinatario de confirmacion removido del alias: %s", nombre_alias)
