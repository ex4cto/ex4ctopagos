from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.parser.bancolombia import ParserBancolombia
from src.parser.base import ErrorParseoBanco, detectar_banco, BANCO_BANCOLOMBIA, BANCO_NEQUI
from src.parser.fabrica import obtener_parser
from src.parser.nequi import ParserNequi

# Texto real extraido del correo de Bancolombia (recepcion de pago)
TEXTO_BANCOLOMBIA_RECIBIDO = (
    "Bancolombia: BRYAN, recibiste una transferencia de ALEJANDRO ARAQUE GONZALEZ "
    "por $81,000.00 en tu cuenta *7488 conectada a la llave 1047487553 el 19/06/26 "
    "a las 03:27. Con llaves es de una y gratis. Dudas al 018000912345."
)

# Mismo contenido pero con saltos de linea como llega en el cuerpo texto del webhook
TEXTO_BANCOLOMBIA_MULTILINEA = (
    "Bancolombia: BRYAN, recibiste una\n"
    "transferencia de BRYAN DAVID CASTRO ALARCON por $100.00 en tu cuenta *7488\n"
    "conectada a la llave 1047487553 el 20/06/26 a las 22:38. Con llaves es de una y\n"
    "gratis. Dudas al 018000912345."
)

# Texto real extraido del correo Nequi (Bre-B recibido)
TEXTO_NEQUI_RECIBIDO = (
    "¡Hola, BRYAN CASTRO!\n\n"
    "Recibiste 50.000 de Andrés Camilo de la Puente Rubio el 29 de abril de 2026 "
    "a las 4:27 p.m, desde el banco Nubank. Revisa el detalle en los movimientos "
    "de tu app o descarga el comprobante si lo necesitas."
)


class TestDeteccionBanco:
    def test_detecta_bancolombia(self) -> None:
        email = "alertasynotificaciones@an.notificacionesbancolombia.com"
        assert detectar_banco(email) == BANCO_BANCOLOMBIA

    def test_detecta_nequi(self) -> None:
        email = "notificaciones@nequi.com.com"
        assert detectar_banco(email) == BANCO_NEQUI

    def test_banco_desconocido_retorna_none(self) -> None:
        email = "notificaciones@davivienda.com.co"
        assert detectar_banco(email) is None


class TestParserBancolombia:
    def test_parsea_monto_correctamente(self) -> None:
        parser = ParserBancolombia()
        resultado = parser.parsear("", TEXTO_BANCOLOMBIA_RECIBIDO)
        assert resultado.monto == Decimal("81000.00")

    def test_parsea_remitente_correctamente(self) -> None:
        parser = ParserBancolombia()
        resultado = parser.parsear("", TEXTO_BANCOLOMBIA_RECIBIDO)
        assert resultado.remitente == "ALEJANDRO ARAQUE GONZALEZ"

    def test_parsea_fecha_correctamente(self) -> None:
        parser = ParserBancolombia()
        resultado = parser.parsear("", TEXTO_BANCOLOMBIA_RECIBIDO)
        assert resultado.fecha_pago == datetime(2026, 6, 19, 3, 27, tzinfo=timezone.utc)

    def test_parsea_banco_origen(self) -> None:
        parser = ParserBancolombia()
        resultado = parser.parsear("", TEXTO_BANCOLOMBIA_RECIBIDO)
        assert resultado.banco_origen == "Bancolombia"

    def test_parsea_texto_con_saltos_de_linea(self) -> None:
        parser = ParserBancolombia()
        resultado = parser.parsear("", TEXTO_BANCOLOMBIA_MULTILINEA)
        assert resultado.monto == Decimal("100.00")
        assert resultado.remitente == "BRYAN DAVID CASTRO ALARCON"

    def test_falla_con_texto_invalido(self) -> None:
        parser = ParserBancolombia()
        with pytest.raises(ErrorParseoBanco):
            parser.parsear("", "Este correo no tiene informacion de pago")


class TestParserNequi:
    def test_parsea_monto_correctamente(self) -> None:
        parser = ParserNequi()
        resultado = parser.parsear("", TEXTO_NEQUI_RECIBIDO)
        assert resultado.monto == Decimal("50000.00")

    def test_parsea_remitente_correctamente(self) -> None:
        parser = ParserNequi()
        resultado = parser.parsear("", TEXTO_NEQUI_RECIBIDO)
        assert resultado.remitente == "Andrés Camilo de la Puente Rubio"

    def test_parsea_fecha_correctamente(self) -> None:
        parser = ParserNequi()
        resultado = parser.parsear("", TEXTO_NEQUI_RECIBIDO)
        assert resultado.fecha_pago == datetime(2026, 4, 29, 16, 27, tzinfo=timezone.utc)

    def test_parsea_banco_origen(self) -> None:
        parser = ParserNequi()
        resultado = parser.parsear("", TEXTO_NEQUI_RECIBIDO)
        assert resultado.banco_origen == "Nequi"


class TestFabrica:
    def test_retorna_parser_bancolombia(self) -> None:
        parser = obtener_parser(BANCO_BANCOLOMBIA)
        assert isinstance(parser, ParserBancolombia)

    def test_retorna_parser_nequi(self) -> None:
        parser = obtener_parser(BANCO_NEQUI)
        assert isinstance(parser, ParserNequi)

    def test_banco_no_soportado_lanza_error(self) -> None:
        with pytest.raises(ErrorParseoBanco):
            obtener_parser("Davivienda")
