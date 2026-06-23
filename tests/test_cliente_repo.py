import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.repositorios.cliente_repo import ErrorClienteDuplicado, crear
from src.modelos.cliente import Cliente


class TestCrearCliente:
    def _sesion_mock(self) -> MagicMock:
        sesion = MagicMock()
        sesion.add = MagicMock()
        sesion.commit = MagicMock()
        sesion.refresh = MagicMock()
        return sesion

    def test_crear_cliente_exitoso(self) -> None:
        sesion = self._sesion_mock()
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

    def test_crear_cliente_duplicado_lanza_error(self) -> None:
        sesion = self._sesion_mock()
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
