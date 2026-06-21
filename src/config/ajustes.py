from pydantic_settings import BaseSettings, SettingsConfigDict


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Forward Email — inbound webhook
    webhook_secret: str = ""

    # Mailgun (inbound routing — solo MAILGUN_DOMINIO para crear direcciones por cliente)
    mailgun_dominio: str = ""

    # Telegram
    telegram_bot_token: str = ""

    # Base de datos
    database_url: str = ""

    # Correo saliente (Forward Email REST API)
    correo_remitente: str = ""
    correo_clave: str = ""

    # Dashboard operador
    operador_clave: str = ""
    secret_key: str = "cambia-esto-en-produccion"

    # Seguridad
    webhook_token_expiracion_minutos: int = 5
    max_reintentos_notificacion: int = 3
    intervalo_reintento_segundos: int = 30

    # App
    ambiente: str = "desarrollo"


ajustes = Ajustes()
