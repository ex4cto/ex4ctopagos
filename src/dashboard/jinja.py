from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi.templating import Jinja2Templates


def _formato_peso(monto: Decimal) -> str:
    entero = int(monto)
    return f"${entero:,}".replace(",", ".")


def _formato_fecha(fecha: datetime) -> str:
    hora_colombia = fecha.astimezone(timezone(timedelta(hours=-5)))
    return hora_colombia.strftime("%d/%m/%Y %H:%M")


def _formato_fecha_corta(fecha: datetime) -> str:
    hora_colombia = fecha.astimezone(timezone(timedelta(hours=-5)))
    return hora_colombia.strftime("%d/%m/%Y")


templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.filters["formato_peso"] = _formato_peso
templates.env.filters["formato_fecha"] = _formato_fecha
templates.env.filters["formato_fecha_corta"] = _formato_fecha_corta
