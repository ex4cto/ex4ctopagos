import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from src.parser.base import ErrorParseoBanco, ParserBanco
from src.webhook.schemas import PagoExtraido

# Patrón real confirmado con correo de Bancolombia:
# "BRYAN, recibiste una transferencia de ALEJANDRO ARAQUE GONZALEZ por $81,000.00
#  en tu cuenta *7488 conectada a la llave 1047487553 el 19/06/26 a las 03:27."
_PATRON_RECIBIDO = re.compile(
    r'recibiste una transferencia de (.+?) por \$([\d,]+(?:\.\d{2})?)'
    r'.+?el (\d{2}/\d{2}/\d{2,4}) a las (\d{2}:\d{2})',
    re.IGNORECASE | re.DOTALL,
)


class ParserBancolombia(ParserBanco):
    def parsear(self, cuerpo_html: str, cuerpo_texto: str) -> PagoExtraido:
        coincidencia = _PATRON_RECIBIDO.search(cuerpo_texto)
        if not coincidencia:
            raise ErrorParseoBanco("No se encontro patron de pago recibido en email Bancolombia")

        remitente = coincidencia.group(1).strip()
        monto = _parsear_monto(coincidencia.group(2))
        fecha_pago = _parsear_fecha_hora(coincidencia.group(3), coincidencia.group(4))

        return PagoExtraido(
            monto=monto,
            remitente=remitente,
            banco_origen="Bancolombia",
            fecha_pago=fecha_pago,
        )


def _parsear_monto(texto: str) -> Decimal:
    sin_comas = texto.replace(",", "")
    try:
        return Decimal(sin_comas)
    except InvalidOperation as error:
        raise ErrorParseoBanco(f"Monto invalido Bancolombia: '{texto}'") from error


def _parsear_fecha_hora(fecha_str: str, hora_str: str) -> datetime:
    for formato in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(
                f"{fecha_str} {hora_str}", f"{formato} %H:%M"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ErrorParseoBanco(f"Fecha/hora invalida Bancolombia: '{fecha_str} {hora_str}'")
