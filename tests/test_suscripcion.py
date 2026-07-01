import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modelos.cliente import Cliente
from src.servicios.suscripcion import (
    desactivar_vencidos,
    notificar_vencimientos_proximos,
    procesar_pago_suscripcion,
)
from src.webhook.schemas import PagoExtraido


def _pago(monto: Decimal = Decimal("50000"), remitente: str = "PEDRO GARCIA") -> PagoExtraido:
    return PagoExtraido(
        monto=monto,
        remitente=remitente,
        banco_origen="Bancolombia",
        fecha_pago=datetime.now(timezone.utc),
    )


def _cliente(nombre: str = "Panadería", correos: list[str] | None = None) -> Cliente:
    cliente = Cliente(
        id=uuid.uuid4(),
        nombre_negocio=nombre,
        correo_dedicado="pan@ex4cto.co",
        telegram_chat_ids=[],
        correos_notificacion=correos or [],
        token_dashboard=uuid.uuid4(),
        activo=True,
        suscripcion_activa=True,
        fecha_vencimiento_suscripcion=datetime.now(timezone.utc) + timedelta(days=30),
    )
    return cliente


class TestProcesarPagoSuscripcion:
    @pytest.mark.asyncio
    async def test_monto_incorrecto_no_renueva(self) -> None:
        sesion = MagicMock()
        pago = _pago(monto=Decimal("30000"))
        with patch("src.servicios.suscripcion.ajustes") as mock_ajustes, \
             patch("src.servicios.suscripcion.cliente_repo") as mock_repo:
            mock_ajustes.precio_suscripcion_cop = 50000
            await procesar_pago_suscripcion(pago, sesion)
            mock_repo.buscar_por_titular.assert_not_called()
            mock_repo.renovar_suscripcion.assert_not_called()

    @pytest.mark.asyncio
    async def test_titular_desconocido_no_renueva(self) -> None:
        sesion = MagicMock()
        pago = _pago()
        with patch("src.servicios.suscripcion.ajustes") as mock_ajustes, \
             patch("src.servicios.suscripcion.cliente_repo") as mock_repo, \
             patch("src.servicios.suscripcion.enviar_mensaje", new_callable=AsyncMock):
            mock_ajustes.precio_suscripcion_cop = 50000
            mock_repo.buscar_por_titular.return_value = None
            await procesar_pago_suscripcion(pago, sesion)
            mock_repo.renovar_suscripcion.assert_not_called()

    @pytest.mark.asyncio
    async def test_pago_exitoso_renueva_y_notifica(self) -> None:
        sesion = MagicMock()
        cliente = _cliente(correos=["dueno@negocio.com"])
        pago = _pago()
        with patch("src.servicios.suscripcion.ajustes") as mock_ajustes, \
             patch("src.servicios.suscripcion.cliente_repo") as mock_repo, \
             patch("src.servicios.suscripcion.enviar_mensaje", new_callable=AsyncMock) as mock_telegram, \
             patch("src.servicios.suscripcion.ejecutar_con_reintentos", new_callable=AsyncMock):
            mock_ajustes.precio_suscripcion_cop = 50000
            mock_ajustes.operador_telegram_chat_id = "111"
            mock_ajustes.max_reintentos_notificacion = 3
            mock_ajustes.intervalo_reintento_segundos = 30
            mock_repo.buscar_por_titular.return_value = cliente
            mock_repo.renovar_suscripcion.return_value = cliente
            await procesar_pago_suscripcion(pago, sesion)
            mock_repo.renovar_suscripcion.assert_called_once_with(cliente.id, sesion)
            mock_telegram.assert_called_once()
            assert "Panadería" in mock_telegram.call_args[0][1]


class TestNotificarVencimientosProximos:
    @pytest.mark.asyncio
    async def test_envia_telegram_y_correo_por_cliente(self) -> None:
        cliente = _cliente(correos=["empleado@negocio.com"])
        cliente.fecha_vencimiento_suscripcion = datetime.now(timezone.utc) + timedelta(days=3)
        sesion = MagicMock()
        with patch("src.servicios.suscripcion.ajustes") as mock_ajustes, \
             patch("src.servicios.suscripcion.cliente_repo") as mock_repo, \
             patch("src.servicios.suscripcion.enviar_mensaje", new_callable=AsyncMock) as mock_telegram, \
             patch("src.servicios.suscripcion.ejecutar_con_reintentos", new_callable=AsyncMock):
            mock_ajustes.operador_telegram_chat_id = "111"
            mock_ajustes.precio_suscripcion_cop = 50000
            mock_ajustes.llave_cobro_operador = "3001234567"
            mock_ajustes.max_reintentos_notificacion = 3
            mock_ajustes.intervalo_reintento_segundos = 30
            mock_repo.listar_por_vencer.return_value = [cliente]
            await notificar_vencimientos_proximos(sesion)
            mock_telegram.assert_called_once()
            assert "Panadería" in mock_telegram.call_args[0][1]

    @pytest.mark.asyncio
    async def test_sin_proximos_no_envia(self) -> None:
        sesion = MagicMock()
        with patch("src.servicios.suscripcion.cliente_repo") as mock_repo, \
             patch("src.servicios.suscripcion.enviar_mensaje", new_callable=AsyncMock) as mock_telegram:
            mock_repo.listar_por_vencer.return_value = []
            await notificar_vencimientos_proximos(sesion)
            mock_telegram.assert_not_called()


class TestDesactivarVencidos:
    @pytest.mark.asyncio
    async def test_marca_suscripcion_inactiva(self) -> None:
        cliente = _cliente()
        cliente.suscripcion_activa = True
        sesion = MagicMock()
        with patch("src.servicios.suscripcion.cliente_repo") as mock_repo:
            mock_repo.listar_suscripcion_vencida.return_value = [cliente]
            await desactivar_vencidos(sesion)
        assert cliente.suscripcion_activa is False
        sesion.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sin_vencidos_no_hace_commit(self) -> None:
        sesion = MagicMock()
        with patch("src.servicios.suscripcion.cliente_repo") as mock_repo:
            mock_repo.listar_suscripcion_vencida.return_value = []
            await desactivar_vencidos(sesion)
        sesion.commit.assert_not_called()
