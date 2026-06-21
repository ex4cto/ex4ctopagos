from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.templating import Jinja2Templates


def _formato_peso(monto: Decimal) -> str:
    entero = int(monto)
    return f"${entero:,}".replace(",", ".")


def _formato_fecha(fecha: datetime) -> str:
    hora_colombia = fecha.astimezone(timezone(timedelta(hours=-5)))
    return hora_colombia.strftime("%d/%m/%Y %H:%M")


templates = Jinja2Templates(directory="src/dashboard/templates")
templates.env.filters["formato_peso"] = _formato_peso
templates.env.filters["formato_fecha"] = _formato_fecha
