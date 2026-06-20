import hmac

from src.config.ajustes import ajustes


class ErrorSecretInvalido(Exception):
    pass


def validar_secret(secret_recibido: str) -> None:
    if not ajustes.webhook_secret:
        raise ErrorSecretInvalido("WEBHOOK_SECRET no esta configurado en el entorno")
    if not hmac.compare_digest(secret_recibido, ajustes.webhook_secret):
        raise ErrorSecretInvalido("Secret invalido")
