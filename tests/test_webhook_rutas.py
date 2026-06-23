import json
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.webhook.rutas import recibir_email
from src.webhook.schemas import PagoExtraido


def _request_mock(correo: str, body: dict) -> MagicMock:
    request = MagicMock()
    request.headers = {}
    request.json = AsyncMock(return_value=body)
    return request


def _background_tasks_mock() -> MagicMock:
    bt = MagicMock()
    bt.add_task = MagicMock()
    return bt


_BODY_BANCOLOMBIA = {
    "messageId": "msg-001",
    "from": {"value": [{"address": "noreply@notificacionesbancolombia.com"}]},
    "subject": "Transferencia recibida",
    "html": "<p>Recibiste $50.000</p>",
    "text": "Recibiste $50.000",
}

_PAGO_MOCK = PagoExtraido(
    monto=Decimal("50000"),
    remitente="PEDRO GARCIA",
    banco_origen="Bancolombia",
    fecha_pago=datetime.now(timezone.utc),
)


class TestWebhookSuscripcion:
    @pytest.mark.asyncio
    async def test_alias_suscripcion_no_llama_pago_repo_crear(self) -> None:
        request = _request_mock("suscripciones@ex4cto.co", _BODY_BANCOLOMBIA)
        bt = _background_tasks_mock()
        sesion = MagicMock()

        with patch("src.webhook.rutas.ajustes") as mock_ajustes, \
             patch("src.webhook.rutas.validar_secret"), \
             patch("src.webhook.rutas.parsear_pago_email", return_value=None), \
             patch("src.webhook.rutas.pago_repo") as mock_pago_repo:
            mock_ajustes.alias_suscripciones = "suscripciones"
            mock_ajustes.forward_email_dominio = "ex4cto.co"
            await recibir_email(
                request=request,
                background_tasks=bt,
                secret="",
                correo="suscripciones@ex4cto.co",
                sesion=sesion,
            )

        mock_pago_repo.crear.assert_not_called()

    @pytest.mark.asyncio
    async def test_alias_suscripcion_agrega_tarea_background(self) -> None:
        request = _request_mock("suscripciones@ex4cto.co", _BODY_BANCOLOMBIA)
        bt = _background_tasks_mock()
        sesion = MagicMock()

        with patch("src.webhook.rutas.ajustes") as mock_ajustes, \
             patch("src.webhook.rutas.validar_secret"), \
             patch("src.webhook.rutas.parsear_pago_email", return_value=_PAGO_MOCK), \
             patch("src.webhook.rutas.suscripcion") as mock_suscripcion:
            mock_ajustes.alias_suscripciones = "suscripciones"
            mock_ajustes.forward_email_dominio = "ex4cto.co"
            mock_suscripcion.procesar_pago_suscripcion = AsyncMock()
            await recibir_email(
                request=request,
                background_tasks=bt,
                secret="",
                correo="suscripciones@ex4cto.co",
                sesion=sesion,
            )

        bt.add_task.assert_called_once()
        args = bt.add_task.call_args[0]
        assert args[1] is _PAGO_MOCK

    @pytest.mark.asyncio
    async def test_alias_cliente_no_llama_servicio_suscripcion(self) -> None:
        request = _request_mock("panaderia@ex4cto.co", _BODY_BANCOLOMBIA)
        bt = _background_tasks_mock()
        sesion = MagicMock()

        with patch("src.webhook.rutas.ajustes") as mock_ajustes, \
             patch("src.webhook.rutas.validar_secret"), \
             patch("src.webhook.rutas.pago_repo") as mock_pago_repo, \
             patch("src.webhook.rutas.cliente_repo") as mock_cliente_repo, \
             patch("src.webhook.rutas.suscripcion") as mock_suscripcion:
            mock_ajustes.alias_suscripciones = "suscripciones"
            mock_ajustes.forward_email_dominio = "ex4cto.co"
            mock_pago_repo.existe_token.return_value = False
            mock_cliente_repo.obtener_por_correo_dedicado.return_value = None
            await recibir_email(
                request=request,
                background_tasks=bt,
                secret="",
                correo="panaderia@ex4cto.co",
                sesion=sesion,
            )

        mock_suscripcion.procesar_pago_suscripcion.assert_not_called()
