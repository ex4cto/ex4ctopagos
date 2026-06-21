from abc import ABC, abstractmethod

from src.webhook.schemas import PagoExtraido

BANCO_BANCOLOMBIA = "Bancolombia"
BANCO_NEQUI = "Nequi"

_DOMINIOS_BANCOLOMBIA = frozenset([
    "notificacionesbancolombia.com",
    "bancolombia.com.co",
    "an.notificacionesbancolombia.com",
])

_DOMINIOS_NEQUI = frozenset([
    "nequi.com.co",
])


class ErrorParseoBanco(Exception):
    pass


class ParserBanco(ABC):
    @abstractmethod
    def parsear(self, cuerpo_html: str, cuerpo_texto: str) -> PagoExtraido:
        pass


def detectar_banco(remitente_email: str) -> str | None:
    dominio = remitente_email.lower().split("@")[-1]
    if dominio in _DOMINIOS_BANCOLOMBIA:
        return BANCO_BANCOLOMBIA
    if dominio in _DOMINIOS_NEQUI:
        return BANCO_NEQUI
    return None
