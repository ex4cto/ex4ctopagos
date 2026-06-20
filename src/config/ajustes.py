from pydantic_settings import BaseSettings, SettingsConfigDict


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Mailgun
    mailgun_api_key: str = ""
    mailgun_webhook_signing_key: str = ""
    mailgun_dominio: str = ""

    # Telegram
    telegram_bot_token: str = ""

    # Base de datos
    database_url: str = ""

    # Correo saliente
    smtp_host: str = ""
    smtp_puerto: int = 587
    smtp_usuario: str = ""
    smtp_clave: str = ""

    # Dashboard operador
    operador_clave: str = ""

    # Seguridad
    webhook_token_expiracion_minutos: int = 5
    max_reintentos_notificacion: int = 3
    intervalo_reintento_segundos: int = 30

    # App
    ambiente: str = "desarrollo"


ajustes = Ajustes()
