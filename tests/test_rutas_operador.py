import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.modelos.cliente import Cliente
from src.dashboard.rutas_operador import _estado_suscripcion


def _cliente_base() -> Cliente:
    return Cliente(
        id=uuid.uuid4(),
        nombre_negocio="Test",
        correo_dedicado="test@ex4cto.co",
        telegram_chat_ids=[],
        correos_notificacion=[],
        token_dashboard=uuid.uuid4(),
        activo=True,
        suscripcion_activa=False,
    )


class TestEstadoSuscripcion:
    def test_activa(self) -> None:
        cliente = _cliente_base()
        cliente.suscripcion_activa = True
        cliente.fecha_vencimiento_suscripcion = datetime.now(timezone.utc) + timedelta(days=10)
        ahora = datetime.now(timezone.utc)
        assert _estado_suscripcion(cliente, ahora) == "activa"

    def test_por_vencer(self) -> None:
        cliente = _cliente_base()
        cliente.suscripcion_activa = True
        cliente.fecha_vencimiento_suscripcion = datetime.now(timezone.utc) + timedelta(days=3)
        ahora = datetime.now(timezone.utc)
        assert _estado_suscripcion(cliente, ahora) == "por_vencer"

    def test_exactamente_en_limite_es_por_vencer(self) -> None:
        cliente = _cliente_base()
        cliente.suscripcion_activa = True
        cliente.fecha_vencimiento_suscripcion = datetime.now(timezone.utc) + timedelta(days=5)
        ahora = datetime.now(timezone.utc)
        assert _estado_suscripcion(cliente, ahora) == "por_vencer"

    def test_inactiva_por_flag(self) -> None:
        cliente = _cliente_base()
        cliente.suscripcion_activa = False
        cliente.fecha_vencimiento_suscripcion = datetime.now(timezone.utc) + timedelta(days=10)
        ahora = datetime.now(timezone.utc)
        assert _estado_suscripcion(cliente, ahora) == "inactiva"

    def test_inactiva_sin_fecha(self) -> None:
        cliente = _cliente_base()
        cliente.suscripcion_activa = True
        cliente.fecha_vencimiento_suscripcion = None
        ahora = datetime.now(timezone.utc)
        assert _estado_suscripcion(cliente, ahora) == "inactiva"
