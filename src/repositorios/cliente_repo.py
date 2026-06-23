import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from src.modelos.cliente import Cliente

logger = logging.getLogger(__name__)

_DIAS_SUSCRIPCION: int = 30


class ErrorClienteDuplicado(Exception):
    pass


def obtener_por_correo_dedicado(correo: str, sesion: Session) -> Cliente | None:
    return sesion.query(Cliente).filter(Cliente.correo_dedicado == correo, Cliente.activo.is_(True)).first()


def obtener_por_id(id_cliente: uuid.UUID, sesion: Session) -> Cliente | None:
    return sesion.query(Cliente).filter(Cliente.id == id_cliente, Cliente.activo.is_(True)).first()


def obtener_por_token_dashboard(token: uuid.UUID, sesion: Session) -> Cliente | None:
    return sesion.query(Cliente).filter(Cliente.token_dashboard == token, Cliente.activo.is_(True)).first()


def obtener_por_chat_id(chat_id: str, sesion: Session) -> Cliente | None:
    return (
        sesion.query(Cliente)
        .filter(
            Cliente.activo.is_(True),
            (
                Cliente.telegram_chat_ids.op("@>")(cast([chat_id], JSONB))
                | (Cliente.telegram_chat_id_dueno == chat_id)
            ),
        )
        .first()
    )


def listar_activos(sesion: Session) -> list[Cliente]:
    return sesion.query(Cliente).filter(Cliente.activo.is_(True)).order_by(Cliente.fecha_creacion.desc()).all()


def rotar_token(id_cliente: uuid.UUID, sesion: Session) -> Cliente | None:
    cliente = obtener_por_id(id_cliente, sesion)
    if not cliente:
        return None
    cliente.token_dashboard = uuid.uuid4()
    sesion.commit()
    sesion.refresh(cliente)
    return cliente


def buscar_por_titular(nombre: str, sesion: Session) -> Cliente | None:
    return (
        sesion.query(Cliente)
        .filter(
            Cliente.activo.is_(True),
            func.lower(Cliente.nombre_titular_cuenta) == nombre.lower().strip(),
        )
        .first()
    )


def renovar_suscripcion(id_cliente: uuid.UUID, sesion: Session) -> Cliente | None:
    cliente = obtener_por_id(id_cliente, sesion)
    if not cliente:
        return None
    cliente.fecha_vencimiento_suscripcion = datetime.now(timezone.utc) + timedelta(days=_DIAS_SUSCRIPCION)
    cliente.suscripcion_activa = True
    sesion.commit()
    sesion.refresh(cliente)
    return cliente


def activar_suscripcion(id_cliente: uuid.UUID, sesion: Session) -> Cliente | None:
    return renovar_suscripcion(id_cliente, sesion)


def listar_por_vencer(dias: int, sesion: Session) -> list[Cliente]:
    ahora = datetime.now(timezone.utc)
    limite = ahora + timedelta(days=dias)
    return (
        sesion.query(Cliente)
        .filter(
            Cliente.activo.is_(True),
            Cliente.suscripcion_activa.is_(True),
            Cliente.fecha_vencimiento_suscripcion >= ahora,
            Cliente.fecha_vencimiento_suscripcion <= limite,
        )
        .all()
    )


def listar_suscripcion_vencida(sesion: Session) -> list[Cliente]:
    ahora = datetime.now(timezone.utc)
    return (
        sesion.query(Cliente)
        .filter(
            Cliente.activo.is_(True),
            Cliente.suscripcion_activa.is_(True),
            Cliente.fecha_vencimiento_suscripcion < ahora,
        )
        .all()
    )


def agregar_chat_id_empleado(
    id_cliente: uuid.UUID,
    chat_id: str,
    sesion: Session,
) -> Cliente | None:
    cliente = obtener_por_id(id_cliente, sesion)
    if not cliente:
        return None
    if chat_id in cliente.telegram_chat_ids:
        logger.info("chat_id %s ya existe en cliente %s — sin cambios", chat_id, id_cliente)
        return cliente
    cliente.telegram_chat_ids = [*cliente.telegram_chat_ids, chat_id]
    sesion.commit()
    sesion.refresh(cliente)
    return cliente


def remover_chat_id_empleado(
    chat_id: str,
    sesion: Session,
) -> Cliente | None:
    cliente = (
        sesion.query(Cliente)
        .filter(
            Cliente.activo.is_(True),
            Cliente.telegram_chat_ids.op("@>")(cast([chat_id], JSONB)),
        )
        .first()
    )
    if not cliente:
        return None
    cliente.telegram_chat_ids = [x for x in cliente.telegram_chat_ids if x != chat_id]
    sesion.commit()
    sesion.refresh(cliente)
    return cliente


def crear(
    nombre_negocio: str,
    correo_dedicado: str,
    telegram_chat_ids: list[str],
    correos_notificacion: list[str],
    sesion: Session,
    telegram_chat_id_dueno: str | None = None,
    nombre_titular_cuenta: str | None = None,
) -> Cliente:
    if obtener_por_correo_dedicado(correo_dedicado, sesion):
        raise ErrorClienteDuplicado(correo_dedicado)
    cliente = Cliente(
        nombre_negocio=nombre_negocio,
        correo_dedicado=correo_dedicado,
        telegram_chat_ids=telegram_chat_ids,
        telegram_chat_id_dueno=telegram_chat_id_dueno,
        correos_notificacion=correos_notificacion,
        nombre_titular_cuenta=nombre_titular_cuenta,
        token_dashboard=uuid.uuid4(),
        activo=True,
    )
    sesion.add(cliente)
    sesion.commit()
    sesion.refresh(cliente)
    return cliente
