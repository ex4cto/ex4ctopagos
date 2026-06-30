import logging

import httpx

from src.config.ajustes import ajustes

logger = logging.getLogger(__name__)

_URL_BASE_API = "https://api.forwardemail.net/v1/domains"


class ErrorCrearAlias(Exception):
    pass


async def crear_alias(nombre_alias: str) -> str:
    correo_dedicado = f"{nombre_alias}@{ajustes.forward_email_dominio}"
    url_webhook = (
        f"{ajustes.app_url}/webhook/email"
        f"?secret={ajustes.webhook_secret}"
        f"&correo={correo_dedicado}"
    )
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
