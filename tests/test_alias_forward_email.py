from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.servicios.alias_forward_email import (
    ErrorActualizarAlias,
    ErrorCrearAlias,
    _obtener_id_alias,
    agregar_destinatario_confirmacion,
    crear_alias,
    remover_destinatario_confirmacion,
)


def _mock_ajustes_base(mock_ajustes: MagicMock) -> None:
    mock_ajustes.forward_email_dominio = "tudominio.com"
    mock_ajustes.app_url = "http://localhost:8000"
    mock_ajustes.webhook_secret = "secreto123"
    mock_ajustes.correo_remitente = "bot@tudominio.com"
    mock_ajustes.correo_clave = "clave123"
    mock_ajustes.correo_confirmacion_alias = "confirmacion@example.com"


class TestCrearAlias:
    @pytest.mark.asyncio
    async def test_crear_alias_exitoso(self) -> None:
        respuesta_mock = MagicMock()
        respuesta_mock.status_code = 201

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.post.return_value = respuesta_mock
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            resultado = await crear_alias("panaderia")

        assert resultado == "panaderia@tudominio.com"
        llamada = mock_http.post.call_args
        cuerpo = llamada.kwargs["json"]
        assert cuerpo["name"] == "panaderia"
        assert "panaderia@tudominio.com" in cuerpo["recipients"][0]
        assert llamada.kwargs["auth"] == ("clave123", "")

    @pytest.mark.asyncio
    async def test_crear_alias_error_api(self) -> None:
        respuesta_mock = MagicMock()
        respuesta_mock.status_code = 422
        respuesta_mock.text = "Alias ya existe"

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.post.return_value = respuesta_mock
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ErrorCrearAlias):
                await crear_alias("panaderia")


class TestObtenerIdAlias:
    @pytest.mark.asyncio
    async def test_obtener_id_encontrado(self) -> None:
        respuesta_mock = MagicMock()
        respuesta_mock.status_code = 200
        respuesta_mock.json.return_value = [
            {"name": "otro", "id": "111"},
            {"name": "panaderia", "id": "999"},
        ]

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_mock
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            resultado = await _obtener_id_alias("panaderia")

        assert resultado == "999"

    @pytest.mark.asyncio
    async def test_obtener_id_no_encontrado(self) -> None:
        respuesta_mock = MagicMock()
        respuesta_mock.status_code = 200
        respuesta_mock.json.return_value = [{"name": "otro", "id": "111"}]

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_mock
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            resultado = await _obtener_id_alias("panaderia")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_obtener_id_error_api_retorna_none(self) -> None:
        respuesta_mock = MagicMock()
        respuesta_mock.status_code = 500

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_mock
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            resultado = await _obtener_id_alias("panaderia")

        assert resultado is None


class TestAgregarDestinatarioConfirmacion:
    @pytest.mark.asyncio
    async def test_agregar_destinatario_exitoso(self) -> None:
        respuesta_get = MagicMock()
        respuesta_get.status_code = 200
        respuesta_get.json.return_value = [{"name": "panaderia", "id": "999"}]

        respuesta_put = MagicMock()
        respuesta_put.status_code = 200

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_get
            mock_http.put.return_value = respuesta_put
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            await agregar_destinatario_confirmacion("panaderia")

        llamada_put = mock_http.put.call_args
        destinatarios = llamada_put.kwargs["json"]["recipients"]
        assert len(destinatarios) == 2
        assert "panaderia@tudominio.com" in destinatarios[0]
        assert destinatarios[1] == "confirmacion@example.com"

    @pytest.mark.asyncio
    async def test_agregar_destinatario_alias_no_encontrado(self) -> None:
        respuesta_get = MagicMock()
        respuesta_get.status_code = 200
        respuesta_get.json.return_value = []

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_get
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ErrorActualizarAlias):
                await agregar_destinatario_confirmacion("panaderia")

    @pytest.mark.asyncio
    async def test_agregar_destinatario_error_put(self) -> None:
        respuesta_get = MagicMock()
        respuesta_get.status_code = 200
        respuesta_get.json.return_value = [{"name": "panaderia", "id": "999"}]

        respuesta_put = MagicMock()
        respuesta_put.status_code = 500
        respuesta_put.text = "Internal Server Error"

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_get
            mock_http.put.return_value = respuesta_put
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ErrorActualizarAlias):
                await agregar_destinatario_confirmacion("panaderia")


class TestRemoverDestinatarioConfirmacion:
    @pytest.mark.asyncio
    async def test_remover_destinatario_exitoso(self) -> None:
        respuesta_get = MagicMock()
        respuesta_get.status_code = 200
        respuesta_get.json.return_value = [{"name": "panaderia", "id": "999"}]

        respuesta_put = MagicMock()
        respuesta_put.status_code = 200

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_get
            mock_http.put.return_value = respuesta_put
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            await remover_destinatario_confirmacion("panaderia")

        llamada_put = mock_http.put.call_args
        destinatarios = llamada_put.kwargs["json"]["recipients"]
        assert len(destinatarios) == 1
        assert "panaderia@tudominio.com" in destinatarios[0]

    @pytest.mark.asyncio
    async def test_remover_destinatario_alias_no_encontrado(self) -> None:
        respuesta_get = MagicMock()
        respuesta_get.status_code = 200
        respuesta_get.json.return_value = []

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_get
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ErrorActualizarAlias):
                await remover_destinatario_confirmacion("panaderia")

    @pytest.mark.asyncio
    async def test_remover_destinatario_error_put(self) -> None:
        respuesta_get = MagicMock()
        respuesta_get.status_code = 200
        respuesta_get.json.return_value = [{"name": "panaderia", "id": "999"}]

        respuesta_put = MagicMock()
        respuesta_put.status_code = 422
        respuesta_put.text = "Unprocessable Entity"

        with patch("src.servicios.alias_forward_email.ajustes") as mock_ajustes, \
             patch("src.servicios.alias_forward_email.httpx.AsyncClient") as mock_cliente:
            _mock_ajustes_base(mock_ajustes)

            mock_http = AsyncMock()
            mock_http.get.return_value = respuesta_get
            mock_http.put.return_value = respuesta_put
            mock_cliente.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cliente.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ErrorActualizarAlias):
                await remover_destinatario_confirmacion("panaderia")
