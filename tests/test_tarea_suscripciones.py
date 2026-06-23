import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.servicios.scheduler import tarea_suscripciones_diaria


class TestTareaSuscripcionesDiaria:
    @pytest.mark.asyncio
    async def test_llama_notificar_y_desactivar(self) -> None:
        sesion_mock = MagicMock()
        with patch("src.servicios.scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("src.servicios.scheduler.SesionLocal", return_value=sesion_mock), \
             patch("src.servicios.scheduler.suscripcion") as mock_suscripcion:
            mock_suscripcion.notificar_vencimientos_proximos = AsyncMock()
            mock_suscripcion.desactivar_vencidos = AsyncMock()
            mock_sleep.side_effect = [None, asyncio.CancelledError()]

            with pytest.raises(asyncio.CancelledError):
                await tarea_suscripciones_diaria()

        mock_suscripcion.notificar_vencimientos_proximos.assert_called_once_with(sesion_mock)
        mock_suscripcion.desactivar_vencidos.assert_called_once_with(sesion_mock)
        sesion_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_sobrevive_excepcion_y_cierra_sesion(self) -> None:
        sesion_mock = MagicMock()
        with patch("src.servicios.scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("src.servicios.scheduler.SesionLocal", return_value=sesion_mock), \
             patch("src.servicios.scheduler.suscripcion") as mock_suscripcion, \
             patch("src.servicios.scheduler.logger") as mock_logger:
            mock_suscripcion.notificar_vencimientos_proximos = AsyncMock(
                side_effect=RuntimeError("fallo de red")
            )
            mock_suscripcion.desactivar_vencidos = AsyncMock()
            mock_sleep.side_effect = [None, asyncio.CancelledError()]

            with pytest.raises(asyncio.CancelledError):
                await tarea_suscripciones_diaria()

        mock_logger.exception.assert_called_once()
        sesion_mock.close.assert_called_once()
