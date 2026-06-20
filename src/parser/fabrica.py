from src.parser.bancolombia import ParserBancolombia
from src.parser.base import BANCO_BANCOLOMBIA, BANCO_NEQUI, ErrorParseoBanco, ParserBanco
from src.parser.nequi import ParserNequi

_PARSERS: dict[str, ParserBanco] = {
    BANCO_BANCOLOMBIA: ParserBancolombia(),
    BANCO_NEQUI: ParserNequi(),
}


def obtener_parser(banco: str) -> ParserBanco:
    if banco not in _PARSERS:
        raise ErrorParseoBanco(f"Banco no soportado: '{banco}'")
    return _PARSERS[banco]
