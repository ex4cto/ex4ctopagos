import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.modelos.pago import Pago


@dataclass
class PagoCrear:
    cliente_id: uuid.UUID
    monto: Decimal
    remitente: str
    banco_origen: str
    fecha_pago: datetime
    email_raw: str
    token_idempotencia: str


@dataclass
class MetricasCliente:
    pagos_hoy: int
    pagos_semana: int
    pagos_mes: int
    monto_hoy: Decimal
    monto_semana: Decimal
    monto_mes: Decimal


def crear(datos: PagoCrear, sesion: Session) -> Pago:
    pago = Pago(
        cliente_id=datos.cliente_id,
        monto=datos.monto,
        remitente=datos.remitente,
        banco_origen=datos.banco_origen,
        fecha_pago=datos.fecha_pago,
        email_raw=datos.email_raw,
        token_idempotencia=datos.token_idempotencia,
    )
    sesion.add(pago)
    sesion.commit()
    sesion.refresh(pago)
    return pago


def obtener_por_id(pago_id: uuid.UUID, sesion: Session) -> "Pago | None":
    return sesion.get(Pago, pago_id)


def existe_token(token: str, sesion: Session) -> bool:
    return sesion.query(Pago).filter(Pago.token_idempotencia == token).first() is not None


def listar_por_cliente(
    cliente_id: uuid.UUID,
    desde: datetime,
    hasta: datetime,
    sesion: Session,
    limite: int = 50,
    offset: int = 0,
) -> list[Pago]:
    return (
        sesion.query(Pago)
        .filter(Pago.cliente_id == cliente_id, Pago.fecha_pago >= desde, Pago.fecha_pago <= hasta)
        .order_by(Pago.fecha_pago.desc())
        .limit(limite)
        .offset(offset)
        .all()
    )


def listar_ultimos_minutos(
    cliente_id: uuid.UUID,
    minutos: int,
    ahora: datetime,
    sesion: Session,
) -> list[Pago]:
    desde = ahora - timedelta(minutes=minutos)
    return (
        sesion.query(Pago)
        .filter(Pago.cliente_id == cliente_id, Pago.fecha_recibido >= desde)
        .order_by(Pago.fecha_recibido.desc())
        .all()
    )


def listar_recientes_global(sesion: Session, limite: int = 50) -> list[Pago]:
    return (
        sesion.query(Pago)
        .options(joinedload(Pago.cliente))
        .order_by(Pago.fecha_recibido.desc())
        .limit(limite)
        .all()
    )


def calcular_metricas(cliente_id: uuid.UUID, ahora: datetime, sesion: Session) -> MetricasCliente:
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = inicio_semana.replace(day=inicio_semana.day - inicio_semana.weekday())
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _totales(desde: datetime) -> tuple[int, Decimal]:
        resultado = sesion.query(func.count(Pago.id), func.coalesce(func.sum(Pago.monto), 0)).filter(
            Pago.cliente_id == cliente_id, Pago.fecha_pago >= desde
        ).one()
        return resultado[0], Decimal(str(resultado[1]))

    cantidad_hoy, monto_hoy = _totales(inicio_hoy)
    cantidad_semana, monto_semana = _totales(inicio_semana)
    cantidad_mes, monto_mes = _totales(inicio_mes)

    return MetricasCliente(
        pagos_hoy=cantidad_hoy,
        pagos_semana=cantidad_semana,
        pagos_mes=cantidad_mes,
        monto_hoy=monto_hoy,
        monto_semana=monto_semana,
        monto_mes=monto_mes,
    )
