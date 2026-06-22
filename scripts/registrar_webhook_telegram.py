"""Registra la URL del webhook en Telegram. Ejecutar una vez por despliegue."""
import asyncio
import sys

sys.path.insert(0, ".")

import httpx

from src.config.ajustes import ajustes

_URL_SET_WEBHOOK = "https://api.telegram.org/bot{token}/setWebhook"


async def registrar() -> None:
    url_webhook = f"{ajustes.app_url}/telegram/webhook"
    payload = {
        "url": url_webhook,
        "secret_token": ajustes.telegram_webhook_secret,
        "allowed_updates": ["message"],
    }
    url_api = _URL_SET_WEBHOOK.format(token=ajustes.telegram_bot_token)
    print(f"Registrando webhook: {url_webhook}")
    async with httpx.AsyncClient(timeout=10) as cliente:
        respuesta = await cliente.post(url_api, json=payload)
    print(f"Estado HTTP: {respuesta.status_code}")
    print(respuesta.json())


asyncio.run(registrar())
