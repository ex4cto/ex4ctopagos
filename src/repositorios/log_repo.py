import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.modelos.log_notificacion import LogNotificacion

ESTADO_EXITOSO = "exitoso"
ESTADO_FALLIDO = "fallido"


@dataclass
class LogCrear:
    pago_id: uuid.UUID
    canal: str
    destinatario: str
    estado: str
    intentos: int
    error: str | None = None


def crear(datos: LogCrear, sesion: Session) -> LogNotificacion:
    log = LogNotificacion(
        pago_id=datos.pago_id,
        canal=datos.canal,
        destinatario=datos.destinatario,
        estado=datos.estado,
        intentos=datos.intentos,
        error=datos.error,
    )
    sesion.add(log)
    sesion.commit()
    sesion.refresh(log)
    return log


def listar_fallos_recientes(sesion: Session, limite: int = 50) -> list[LogNotificacion]:
    return (
        sesion.query(LogNotificacion)
        .filter(LogNotificacion.estado == ESTADO_FALLIDO)
        .order_by(LogNotificacion.fecha.desc())
        .limit(limite)
        .all()
    )
