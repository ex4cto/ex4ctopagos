from pydantic_settings import BaseSettings, SettingsConfigDict


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Forward Email — inbound webhook
    webhook_secret: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    # Base de datos
    database_url: str = ""

    # Correo saliente (Forward Email REST API)
    correo_remitente: str = ""
    correo_clave: str = ""
    correo_confirmacion_alias: str = ""

    # Dashboard operador
    operador_clave: str = ""
    secret_key: str = ""

    # Seguridad
    webhook_token_expiracion_minutos: int = 5
    max_reintentos_notificacion: int = 3
    intervalo_reintento_segundos: int = 30

    # Operador
    operador_telegram_chat_id: str = ""

    # Forward Email — gestión de aliases
    forward_email_dominio: str = ""

    # Suscripciones
    precio_suscripcion_cop: int = 50000
    llave_cobro_operador: str = ""
    alias_suscripciones: str = "suscripciones"

    # App
    ambiente: str = "produccion"
    app_url: str = "http://localhost:8000"


ajustes = Ajustes()
