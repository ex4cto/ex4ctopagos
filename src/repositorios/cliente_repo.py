import uuid

from sqlalchemy.orm import Session

from src.modelos.cliente import Cliente


def obtener_por_correo_dedicado(correo: str, sesion: Session) -> Cliente | None:
    return sesion.query(Cliente).filter(Cliente.correo_dedicado == correo, Cliente.activo.is_(True)).first()


def obtener_por_id(id_cliente: uuid.UUID, sesion: Session) -> Cliente | None:
    return sesion.query(Cliente).filter(Cliente.id == id_cliente, Cliente.activo.is_(True)).first()


def obtener_por_token_dashboard(token: uuid.UUID, sesion: Session) -> Cliente | None:
    return sesion.query(Cliente).filter(Cliente.token_dashboard == token, Cliente.activo.is_(True)).first()


def listar_activos(sesion: Session) -> list[Cliente]:
    return sesion.query(Cliente).filter(Cliente.activo.is_(True)).order_by(Cliente.fecha_creacion.desc()).all()
