"""Agrega columnas de suscripcion y rol de dueño a la tabla clientes.

Uso: python scripts/migrar_suscripcion.py
"""
import logging
import sys

sys.path.insert(0, ".")

from sqlalchemy import text

from src.config.ajustes import ajustes
from src.config.base_datos import SesionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_MIGRACIONES: list[str] = [
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telegram_chat_id_dueno VARCHAR(50)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS nombre_titular_cuenta VARCHAR(200)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS fecha_vencimiento_suscripcion TIMESTAMPTZ",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS suscripcion_activa BOOLEAN NOT NULL DEFAULT FALSE",
]


def ejecutar_migracion() -> None:
    sesion = SesionLocal()
    try:
        for sentencia in _MIGRACIONES:
            sesion.execute(text(sentencia))
            logger.info("OK: %s", sentencia)
        sesion.commit()
        logger.info("Migracion completada.")
    except Exception as exc:
        sesion.rollback()
        logger.exception("Error en migracion: %s", exc)
        raise
    finally:
        sesion.close()


if __name__ == "__main__":
    if not ajustes.database_url:
        print("Error: DATABASE_URL no configurada.")
        sys.exit(1)
    ejecutar_migracion()
