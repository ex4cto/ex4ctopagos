import pytest

from src.config.ajustes import ajustes
from src.webhook.validador import ErrorSecretInvalido, validar_secret

SECRET_PRUEBA = "secret-de-prueba-abc123"


def test_secret_valido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ajustes, "webhook_secret", SECRET_PRUEBA)
    validar_secret(SECRET_PRUEBA)


def test_secret_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ajustes, "webhook_secret", SECRET_PRUEBA)
    with pytest.raises(ErrorSecretInvalido):
        validar_secret("secret-completamente-incorrecto")


def test_secret_vacio_rechazado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ajustes, "webhook_secret", SECRET_PRUEBA)
    with pytest.raises(ErrorSecretInvalido):
        validar_secret("")


def test_webhook_secret_no_configurado_rechaza_todo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ajustes, "webhook_secret", "")
    with pytest.raises(ErrorSecretInvalido):
        validar_secret(SECRET_PRUEBA)
