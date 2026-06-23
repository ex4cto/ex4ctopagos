import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.modelos.cliente import Cliente
from src.repositorios.cliente_repo import (
    ErrorClienteDuplicado,
    activar_suscripcion,
    buscar_por_titular,
    crear,
    listar_por_vencer,
    listar_suscripcion_vencida,
    obtener_por_chat_id,
    renovar_suscripcion,
)


def _sesion_mock() -> MagicMock:
    sesion = MagicMock()
    sesion.add = MagicMock()
    sesion.commit = MagicMock()
    sesion.refresh = MagicMock()
    return sesion


def _cliente_activo(chat_ids: list[str] | None = None, chat_id_dueno: str | None = None) -> Cliente:
    cliente = Cliente(
        id=uuid.uuid4(),
        nombre_negocio="Negocio Test",
        correo_dedicado="test@ex4cto.co",
        telegram_chat_ids=chat_ids or [],
        telegram_chat_id_dueno=chat_id_dueno,
        correos_notificacion=[],
        token_dashboard=uuid.uuid4(),
        activo=True,
        suscripcion_activa=False,
    )
    return cliente


class TestCrearCliente:
    def test_crear_cliente_exitoso(self) -> None:
        sesion = _sesion_mock()
        with patch("src.repositorios.cliente_repo.obtener_por_correo_dedicado", return_value=None):
            cliente = crear(
                nombre_negocio="Panadería López",
                correo_dedicado="panaderia@ex4cto.co",
                telegram_chat_ids=[],
                correos_notificacion=["empleado@panaderia.com"],
                sesion=sesion,
            )
        sesion.add.assert_called_once_with(cliente)
        sesion.commit.assert_called_once()
        sesion.refresh.assert_called_once_with(cliente)

    def test_crear_cliente_con_campos_opcionales(self) -> None:
        sesion = _sesion_mock()
        with patch("src.repositorios.cliente_repo.obtener_por_correo_dedicado", return_value=None):
            cliente = crear(
                nombre_negocio="Tienda",
                correo_dedicado="tienda@ex4cto.co",
                telegram_chat_ids=["111"],
                correos_notificacion=[],
                sesion=sesion,
                telegram_chat_id_dueno="999",
                nombre_titular_cuenta="PEDRO GARCIA",
            )
        assert cliente.telegram_chat_id_dueno == "999"
        assert cliente.nombre_titular_cuenta == "PEDRO GARCIA"

    def test_crear_cliente_duplicado_lanza_error(self) -> None:
        sesion = _sesion_mock()
        existente = MagicMock(spec=Cliente)
        with patch("src.repositorios.cliente_repo.obtener_por_correo_dedicado", return_value=existente):
            with pytest.raises(ErrorClienteDuplicado):
                crear(
                    nombre_negocio="Otro negocio",
                    correo_dedicado="panaderia@ex4cto.co",
                    telegram_chat_ids=[],
                    correos_notificacion=[],
                    sesion=sesion,
                )
        sesion.add.assert_not_called()


class TestObtenerPorChatId:
    def test_encuentra_por_telegram_chat_id_dueno(self) -> None:
        cliente = _cliente_activo(chat_id_dueno="777")
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = cliente
        resultado = obtener_por_chat_id("777", sesion)
        assert resultado is cliente

    def test_encuentra_por_telegram_chat_ids_empleado(self) -> None:
        cliente = _cliente_activo(chat_ids=["888"])
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = cliente
        resultado = obtener_por_chat_id("888", sesion)
        assert resultado is cliente

    def test_retorna_none_si_no_encuentra(self) -> None:
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = None
        assert obtener_por_chat_id("999", sesion) is None


class TestBuscarPorTitular:
    def test_encuentra_titular_existente(self) -> None:
        cliente = _cliente_activo()
        cliente.nombre_titular_cuenta = "PEDRO GARCIA"
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = cliente
        resultado = buscar_por_titular("PEDRO GARCIA", sesion)
        assert resultado is cliente

    def test_retorna_none_si_no_existe(self) -> None:
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = None
        assert buscar_por_titular("DESCONOCIDO", sesion) is None


class TestRenovarSuscripcion:
    def test_renueva_y_activa(self) -> None:
        cliente = _cliente_activo()
        sesion = _sesion_mock()
        with patch("src.repositorios.cliente_repo.obtener_por_id", return_value=cliente):
            resultado = renovar_suscripcion(cliente.id, sesion)
        assert resultado is cliente
        assert cliente.suscripcion_activa is True
        assert cliente.fecha_vencimiento_suscripcion is not None
        margen = timedelta(seconds=5)
        esperado = datetime.now(timezone.utc) + timedelta(days=30)
        assert abs(cliente.fecha_vencimiento_suscripcion - esperado) < margen

    def test_retorna_none_si_cliente_no_existe(self) -> None:
        sesion = _sesion_mock()
        with patch("src.repositorios.cliente_repo.obtener_por_id", return_value=None):
            assert renovar_suscripcion(uuid.uuid4(), sesion) is None


class TestActivarSuscripcion:
    def test_activa_igual_que_renovar(self) -> None:
        cliente = _cliente_activo()
        sesion = _sesion_mock()
        with patch("src.repositorios.cliente_repo.obtener_por_id", return_value=cliente):
            resultado = activar_suscripcion(cliente.id, sesion)
        assert resultado is cliente
        assert cliente.suscripcion_activa is True


class TestListarPorVencer:
    def test_retorna_clientes_proximos_a_vencer(self) -> None:
        cliente = _cliente_activo()
        cliente.suscripcion_activa = True
        cliente.fecha_vencimiento_suscripcion = datetime.now(timezone.utc) + timedelta(days=3)
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.all.return_value = [cliente]
        resultado = listar_por_vencer(5, sesion)
        assert cliente in resultado

    def test_retorna_lista_vacia_sin_proximos(self) -> None:
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.all.return_value = []
        assert listar_por_vencer(5, sesion) == []


class TestListarSuscripcionVencida:
    def test_retorna_clientes_vencidos(self) -> None:
        cliente = _cliente_activo()
        cliente.suscripcion_activa = True
        cliente.fecha_vencimiento_suscripcion = datetime.now(timezone.utc) - timedelta(days=1)
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.all.return_value = [cliente]
        resultado = listar_suscripcion_vencida(sesion)
        assert cliente in resultado
