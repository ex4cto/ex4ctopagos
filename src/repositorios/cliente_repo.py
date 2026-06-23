import uuid

from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from src.modelos.cliente import Cliente


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
            Cliente.telegram_chat_ids.op("@>")(cast([chat_id], JSONB)),
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


def crear(
    nombre_negocio: str,
    correo_dedicado: str,
    telegram_chat_ids: list[str],
    correos_notificacion: list[str],
    sesion: Session,
) -> Cliente:
    if obtener_por_correo_dedicado(correo_dedicado, sesion):
        raise ErrorClienteDuplicado(correo_dedicado)
    cliente = Cliente(
        nombre_negocio=nombre_negocio,
        correo_dedicado=correo_dedicado,
        telegram_chat_ids=telegram_chat_ids,
        correos_notificacion=correos_notificacion,
        token_dashboard=uuid.uuid4(),
        activo=True,
    )
    sesion.add(cliente)
    sesion.commit()
    sesion.refresh(cliente)
    return cliente
