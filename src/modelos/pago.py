import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.base_datos import Base


class Pago(Base):
    __tablename__ = "pagos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    remitente: Mapped[str] = mapped_column(String(200), nullable=False)
    banco_origen: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_pago: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_recibido: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    email_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    notificado_telegram: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notificado_correo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_idempotencia: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    cliente: Mapped["Cliente"] = relationship("Cliente")  # type: ignore[name-defined]
