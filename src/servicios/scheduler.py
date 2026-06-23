import asyncio
import logging

from src.config.base_datos import SesionLocal
from src.servicios import suscripcion

logger = logging.getLogger(__name__)

_SEGUNDOS_DIA: int = 86400


async def tarea_suscripciones_diaria() -> None:
    while True:
        await asyncio.sleep(_SEGUNDOS_DIA)
        sesion = SesionLocal()
        try:
            await suscripcion.notificar_vencimientos_proximos(sesion)
            await suscripcion.desactivar_vencidos(sesion)
        except Exception:
            logger.exception("Error en tarea diaria de suscripciones")
        finally:
            sesion.close()
