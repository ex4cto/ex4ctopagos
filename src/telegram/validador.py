import hmac

from src.config.ajustes import ajustes


class ErrorTokenTelegramInvalido(Exception):
    pass


def validar_token_telegram(token_recibido: str) -> None:
    if not ajustes.telegram_webhook_secret:
        raise ErrorTokenTelegramInvalido("TELEGRAM_WEBHOOK_SECRET no configurado")
    if not hmac.compare_digest(token_recibido, ajustes.telegram_webhook_secret):
        raise ErrorTokenTelegramInvalido("Token de webhook de Telegram invalido")
