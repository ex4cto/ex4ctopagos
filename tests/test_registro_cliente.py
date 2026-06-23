import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.repositorios.cliente_repo import ErrorClienteDuplicado
from src.servicios.alias_forward_email import ErrorCrearAlias
from src.servicios.registro_cliente import (
    _sesiones_registro,
    es_comando_nuevo_cliente,
    procesar_mensaje_operador,
)


def _limpiar_sesiones() -> None:
    _sesiones_registro.clear()


def _sesion_mock() -> MagicMock:
    return MagicMock()


def _cliente_mock() -> MagicMock:
    cliente = MagicMock()
    cliente.id = uuid.uuid4()
    cliente.token_dashboard = uuid.uuid4()
    return cliente


class TestEsComandoNuevoCliente:
    def test_detecta_comando_exacto(self) -> None:
        assert es_comando_nuevo_cliente("/nuevo_cliente") is True

    def test_detecta_con_sufijo_bot(self) -> None:
        assert es_comando_nuevo_cliente("/nuevo_cliente@mibot") is True

    def test_rechaza_otro_comando(self) -> None:
        assert es_comando_nuevo_cliente("/verificar_pago") is False

    def test_rechaza_none(self) -> None:
        assert es_comando_nuevo_cliente(None) is False


class TestProcesarMensajeOperador:
    def setup_method(self) -> None:
        _limpiar_sesiones()

    @pytest.mark.asyncio
    async def test_inicia_flujo_con_comando(self) -> None:
        respuesta = await procesar_mensaje_operador("111", "/nuevo_cliente", _sesion_mock())
        assert respuesta is not None
        assert "nombre" in respuesta.lower()
        assert "111" in _sesiones_registro

    @pytest.mark.asyncio
    async def test_ignorar_mensaje_sin_sesion_sin_comando(self) -> None:
        respuesta = await procesar_mensaje_operador("222", "hola", _sesion_mock())
        assert respuesta is None

    @pytest.mark.asyncio
    async def test_alias_invalido_pide_de_nuevo(self) -> None:
        await procesar_mensaje_operador("333", "/nuevo_cliente", _sesion_mock())
        await procesar_mensaje_operador("333", "Tienda Xyz", _sesion_mock())
        respuesta = await procesar_mensaje_operador("333", "alias invalido con espacios", _sesion_mock())
        assert "inválido" in respuesta
        assert _sesiones_registro["333"]["paso"] == "alias"

    @pytest.mark.asyncio
    async def test_correos_notificacion_ninguno(self) -> None:
        cliente = _cliente_mock()
        with patch("src.servicios.registro_cliente.cliente_repo.crear", return_value=cliente) as mock_crear, \
             patch("src.servicios.registro_cliente.alias_forward_email.crear_alias", new_callable=AsyncMock):
            await procesar_mensaje_operador("444", "/nuevo_cliente", _sesion_mock())
            await procesar_mensaje_operador("444", "Mi Tienda", _sesion_mock())
            await procesar_mensaje_operador("444", "mitienda", _sesion_mock())
            await procesar_mensaje_operador("444", "ninguno", _sesion_mock())
        _, kwargs = mock_crear.call_args
        assert kwargs["correos_notificacion"] == [] or mock_crear.call_args[0][3] == []

    @pytest.mark.asyncio
    async def test_flujo_completo_exitoso(self) -> None:
        cliente = _cliente_mock()
        with patch("src.servicios.registro_cliente.cliente_repo.crear", return_value=cliente) as mock_crear, \
             patch("src.servicios.registro_cliente.alias_forward_email.crear_alias", new_callable=AsyncMock) as mock_alias, \
             patch("src.servicios.registro_cliente.ajustes") as mock_ajustes:
            mock_ajustes.forward_email_dominio = "ex4cto.co"
            mock_ajustes.app_url = "https://ex4ctopagos-production.up.railway.app"

            await procesar_mensaje_operador("555", "/nuevo_cliente", _sesion_mock())
            await procesar_mensaje_operador("555", "Panadería López", _sesion_mock())
            await procesar_mensaje_operador("555", "panaderia", _sesion_mock())
            sesion = _sesion_mock()
            respuesta = await procesar_mensaje_operador("555", "empleado@panaderia.com", sesion)

        mock_crear.assert_called_once()
        mock_alias.assert_called_once_with("panaderia")
        assert "registrado" in respuesta.lower()
        assert str(cliente.token_dashboard) in respuesta
        assert "555" not in _sesiones_registro

    @pytest.mark.asyncio
    async def test_correo_duplicado_retorna_error(self) -> None:
        with patch("src.servicios.registro_cliente.cliente_repo.crear", side_effect=ErrorClienteDuplicado("test@ex4cto.co")):
            await procesar_mensaje_operador("666", "/nuevo_cliente", _sesion_mock())
            await procesar_mensaje_operador("666", "Tienda", _sesion_mock())
            await procesar_mensaje_operador("666", "tienda", _sesion_mock())
            respuesta = await procesar_mensaje_operador("666", "ninguno", _sesion_mock())
        assert "Ya existe" in respuesta
        assert "666" not in _sesiones_registro

    @pytest.mark.asyncio
    async def test_timeout_sesion_expirada(self) -> None:
        await procesar_mensaje_operador("777", "/nuevo_cliente", _sesion_mock())
        _sesiones_registro["777"]["timestamp"] = time.time() - 700
        respuesta = await procesar_mensaje_operador("777", "Tienda", _sesion_mock())
        assert respuesta is None
        assert "777" not in _sesiones_registro
