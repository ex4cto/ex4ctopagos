import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.base_datos import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_negocio: Mapped[str] = mapped_column(String(200), nullable=False)
    correo_dedicado: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    telegram_chat_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    correos_notificacion: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_dashboard: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4, unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
