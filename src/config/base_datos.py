from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config.ajustes import ajustes


class Base(DeclarativeBase):
    pass


motor = create_engine(ajustes.database_url, echo=ajustes.ambiente == "desarrollo")

SesionLocal = sessionmaker(bind=motor, autocommit=False, autoflush=False)


def obtener_sesion() -> Generator[Session, None, None]:
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()
