from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.servicios.alias_forward_email import ErrorCrearAlias, crear_alias


class TestCrearAlias:
    @pytest.mark.asyncio
    async def test_crear_alias_exitoso(self) -> None:
        respuesta_mock = MagicMock()
        respuesta_mock.status_code = 201

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            mock_ajustes.forward_email_dominio = "ex4cto.co"
            mock_ajustes.app_url = "https://ex4ctopagos-production.up.railway.app"
            mock_ajustes.webhook_secret = "secreto123"
            mock_ajustes.correo_remitente = "bot@ex4cto.co"
            mock_ajustes.correo_clave = "clave123"

            mock_http = AsyncMock()
            mock_http.post.return_value = respuesta_mock
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            resultado = await crear_alias("panaderia")

        assert resultado == "panaderia@ex4cto.co"
        llamada = mock_http.post.call_args
        cuerpo = llamada.kwargs["json"]
        assert cuerpo["name"] == "panaderia"
        assert "panaderia@ex4cto.co" in cuerpo["recipients"][0]

    @pytest.mark.asyncio
    async def test_crear_alias_error_api(self) -> None:
        respuesta_mock = MagicMock()
        respuesta_mock.status_code = 422
        respuesta_mock.text = "Alias ya existe"

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            mock_ajustes.forward_email_dominio = "ex4cto.co"
            mock_ajustes.app_url = "https://ex4ctopagos-production.up.railway.app"
            mock_ajustes.webhook_secret = "secreto123"
            mock_ajustes.correo_remitente = "bot@ex4cto.co"
            mock_ajustes.correo_clave = "clave123"

            mock_http = AsyncMock()
            mock_http.post.return_value = respuesta_mock
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ErrorCrearAlias):
                await crear_alias("panaderia")
