import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_ERROR_RETORNO_FALSE = "Funcion retorno False sin excepcion"


@dataclass
class ResultadoEnvio:
    exito: bool
    intentos: int
    error: str | None = None


async def ejecutar_con_reintentos(
    fn: Callable[[], Awaitable[bool]],
    max_intentos: int,
    intervalo_segundos: float,
) -> ResultadoEnvio:
    ultimo_error: str | None = None
    for intento in range(1, max_intentos + 1):
        try:
            if await fn():
                return ResultadoEnvio(exito=True, intentos=intento)
            ultimo_error = _ERROR_RETORNO_FALSE
        except Exception as error:
            ultimo_error = str(error)
            logger.warning("Intento %d/%d fallido: %s", intento, max_intentos, error)
        if intento < max_intentos:
            await asyncio.sleep(intervalo_segundos)
    return ResultadoEnvio(exito=False, intentos=max_intentos, error=ultimo_error)
