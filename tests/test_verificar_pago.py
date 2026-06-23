from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.notificador.correo import formatear_asunto_resumen, formatear_cuerpo_html_resumen
from src.servicios.verificar_pago import (
    _es_comando_verificar_pago,
    _formatear_monto,
    _formatear_respuesta,
    procesar_actualizacion,
)
from src.telegram.schemas import ActualizacionTelegram, ChatTelegram, MensajeTelegram


# --- Tests del detector de comando ---

class TestEsComandoVerificarPago:
    def test_detecta_comando_exacto(self) -> None:
        assert _es_comando_verificar_pago("/verificar_pago") is True

    def test_detecta_mayusculas(self) -> None:
        assert _es_comando_verificar_pago("/VERIFICAR_PAGO") is True

    def test_detecta_con_sufijo_bot(self) -> None:
        assert _es_comando_verificar_pago("/verificar_pago@mibot") is True

    def test_rechaza_otro_comando(self) -> None:
        assert _es_comando_verificar_pago("/start") is False

    def test_rechaza_texto_libre(self) -> None:
        assert _es_comando_verificar_pago("verificar_pago") is False

    def test_rechaza_none(self) -> None:
        assert _es_comando_verificar_pago(None) is False

    def test_rechaza_vacio(self) -> None:
        assert _es_comando_verificar_pago("") is False


# --- Tests del formateador de monto ---

class TestFormatearMonto:
    def test_formatea_miles(self) -> None:
        assert _formatear_monto(Decimal("50000")) == "$50.000"

    def test_formatea_millones(self) -> None:
        assert _formatear_monto(Decimal("1500000")) == "$1.500.000"

    def test_formatea_sin_decimales(self) -> None:
        assert _formatear_monto(Decimal("100.50")) == "$100"


# --- Tests del formateador de respuesta ---

class TestFormatearRespuesta:
    def test_sin_pagos(self) -> None:
        ahora = datetime.now(timezone.utc)
        resultado = _formatear_respuesta([], ahora)
        assert "Sin pagos" in resultado

    def test_con_un_pago(self) -> None:
        ahora = datetime.now(timezone.utc)
        pago = MagicMock()
        pago.monto = Decimal("80000")
        pago.remitente = "Juan Perez"
        pago.fecha_recibido = ahora
        resultado = _formatear_respuesta([pago], ahora)
        assert "$80.000" in resultado
        assert "Juan Perez" in resultado

    def test_escapa_html_en_remitente(self) -> None:
        ahora = datetime.now(timezone.utc)
        pago = MagicMock()
        pago.monto = Decimal("10000")
        pago.remitente = "<script>alert(1)</script>"
        pago.fecha_recibido = ahora
        resultado = _formatear_respuesta([pago], ahora)
        assert "<script>" not in resultado
        assert "&lt;script&gt;" in resultado


# --- Tests del procesador de actualizacion ---

class TestProcesarActualizacion:
    def _crear_actualizacion(self, texto: str, chat_id: int = -123456789) -> ActualizacionTelegram:
        return ActualizacionTelegram(
            update_id=1,
            message=MensajeTelegram(
                message_id=1,
                chat=ChatTelegram(id=chat_id, type="group"),
                text=texto,
            ),
        )

    @pytest.mark.asyncio
    async def test_operador_enrutado_a_registro(self) -> None:
        actualizacion = self._crear_actualizacion("/nuevo_cliente", chat_id=999999999)
        sesion = MagicMock()
        with patch("src.servicios.verificar_pago.ajustes") as mock_ajustes, \
             patch("src.servicios.verificar_pago.registro_cliente") as mock_registro, \
             patch("src.servicios.verificar_pago.enviar_mensaje", new_callable=AsyncMock) as mock_enviar, \
             patch("src.servicios.verificar_pago.cliente_repo") as mock_repo:
            mock_ajustes.operador_telegram_chat_id = "999999999"
            mock_registro.procesar_mensaje_operador = AsyncMock(return_value="¿Cuál es el nombre?")
            await procesar_actualizacion(actualizacion, sesion)
            mock_registro.procesar_mensaje_operador.assert_called_once()
            mock_enviar.assert_called_once_with("999999999", "¿Cuál es el nombre?")
            mock_repo.obtener_por_chat_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_operador_ignora_enrutamiento(self) -> None:
        actualizacion = self._crear_actualizacion("/nuevo_cliente", chat_id=-123456789)
        sesion = MagicMock()
        with patch("src.servicios.verificar_pago.ajustes") as mock_ajustes, \
             patch("src.servicios.verificar_pago.registro_cliente") as mock_registro, \
             patch("src.servicios.verificar_pago.cliente_repo") as mock_repo:
            mock_ajustes.operador_telegram_chat_id = ""
            mock_repo.obtener_por_chat_id.return_value = None
            await procesar_actualizacion(actualizacion, sesion)
            mock_registro.procesar_mensaje_operador.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignora_mensaje_sin_comando(self) -> None:
        actualizacion = self._crear_actualizacion("hola")
        sesion = MagicMock()
        with patch("src.servicios.verificar_pago.ajustes") as mock_ajustes, \
             patch("src.servicios.verificar_pago.enviar_mensaje") as mock_enviar:
            mock_ajustes.operador_telegram_chat_id = ""
            await procesar_actualizacion(actualizacion, sesion)
            mock_enviar.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignora_chat_id_desconocido(self) -> None:
        actualizacion = self._crear_actualizacion("/verificar_pago")
        sesion = MagicMock()
        with patch("src.servicios.verificar_pago.cliente_repo") as mock_repo:
            mock_repo.obtener_por_chat_id.return_value = None
            with patch("src.servicios.verificar_pago.enviar_mensaje") as mock_enviar:
                await procesar_actualizacion(actualizacion, sesion)
                mock_enviar.assert_not_called()

    @pytest.mark.asyncio
    async def test_responde_sin_pagos_recientes(self) -> None:
        actualizacion = self._crear_actualizacion("/verificar_pago")
        sesion = MagicMock()
        cliente_mock = MagicMock()
        cliente_mock.nombre_negocio = "Negocio Test"
        cliente_mock.correos_notificacion = []
        with patch("src.servicios.verificar_pago.cliente_repo") as mock_cliente_repo, \
             patch("src.servicios.verificar_pago.pago_repo") as mock_pago_repo, \
             patch("src.servicios.verificar_pago.enviar_mensaje", new_callable=AsyncMock) as mock_enviar:
            mock_cliente_repo.obtener_por_chat_id.return_value = cliente_mock
            mock_pago_repo.listar_ultimos_minutos.return_value = []
            await procesar_actualizacion(actualizacion, sesion)
            mock_enviar.assert_called_once()
            assert "Sin pagos" in mock_enviar.call_args[0][1]

    @pytest.mark.asyncio
    async def test_envia_correo_resumen_con_pagos(self) -> None:
        actualizacion = self._crear_actualizacion("/verificar_pago")
        sesion = MagicMock()
        cliente_mock = MagicMock()
        cliente_mock.nombre_negocio = "Negocio Test"
        cliente_mock.correos_notificacion = ["empleado@negocio.com"]
        pago_mock = MagicMock()
        pago_mock.monto = Decimal("75000")
        pago_mock.remitente = "Ana Gomez"
        pago_mock.fecha_recibido = datetime.now(timezone.utc)
        with patch("src.servicios.verificar_pago.cliente_repo") as mock_cliente_repo, \
             patch("src.servicios.verificar_pago.pago_repo") as mock_pago_repo, \
             patch("src.servicios.verificar_pago.enviar_mensaje", new_callable=AsyncMock), \
             patch("src.servicios.verificar_pago.correo_notificador") as mock_correo:
            mock_correo.notificar_resumen = AsyncMock()
            mock_cliente_repo.obtener_por_chat_id.return_value = cliente_mock
            mock_pago_repo.listar_ultimos_minutos.return_value = [pago_mock]
            await procesar_actualizacion(actualizacion, sesion)
            mock_correo.notificar_resumen.assert_called_once_with(
                ["empleado@negocio.com"], [pago_mock], "Negocio Test", 5
            )

    @pytest.mark.asyncio
    async def test_no_envia_correo_si_sin_pagos_recientes(self) -> None:
        actualizacion = self._crear_actualizacion("/verificar_pago")
        sesion = MagicMock()
        cliente_mock = MagicMock()
        cliente_mock.nombre_negocio = "Negocio Test"
        cliente_mock.correos_notificacion = ["empleado@negocio.com"]
        with patch("src.servicios.verificar_pago.cliente_repo") as mock_cliente_repo, \
             patch("src.servicios.verificar_pago.pago_repo") as mock_pago_repo, \
             patch("src.servicios.verificar_pago.enviar_mensaje", new_callable=AsyncMock), \
             patch("src.servicios.verificar_pago.correo_notificador") as mock_correo:
            mock_correo.notificar_resumen = AsyncMock()
            mock_cliente_repo.obtener_por_chat_id.return_value = cliente_mock
            mock_pago_repo.listar_ultimos_minutos.return_value = []
            await procesar_actualizacion(actualizacion, sesion)
            mock_correo.notificar_resumen.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_envia_correo_si_cliente_sin_correos(self) -> None:
        actualizacion = self._crear_actualizacion("/verificar_pago")
        sesion = MagicMock()
        cliente_mock = MagicMock()
        cliente_mock.nombre_negocio = "Negocio Test"
        cliente_mock.correos_notificacion = []
        with patch("src.servicios.verificar_pago.cliente_repo") as mock_cliente_repo, \
             patch("src.servicios.verificar_pago.pago_repo") as mock_pago_repo, \
             patch("src.servicios.verificar_pago.enviar_mensaje", new_callable=AsyncMock), \
             patch("src.servicios.verificar_pago.correo_notificador") as mock_correo:
            mock_correo.notificar_resumen = AsyncMock()
            mock_cliente_repo.obtener_por_chat_id.return_value = cliente_mock
            mock_pago_repo.listar_ultimos_minutos.return_value = []
            await procesar_actualizacion(actualizacion, sesion)
            mock_correo.notificar_resumen.assert_not_called()


# --- Tests de formateadores de resumen de correo ---

class TestFormatearAsuntoResumen:
    def test_con_pagos(self) -> None:
        pago = MagicMock()
        pago.monto = Decimal("50000")
        pago2 = MagicMock()
        pago2.monto = Decimal("30000")
        asunto = formatear_asunto_resumen([pago, pago2], "Mi Negocio")
        assert "Mi Negocio" in asunto
        assert "2 pagos" in asunto
        assert "$80.000" in asunto

    def test_sin_pagos(self) -> None:
        asunto = formatear_asunto_resumen([], "Mi Negocio")
        assert "Mi Negocio" in asunto
        assert "Sin pagos" in asunto

    def test_un_pago_singular(self) -> None:
        pago = MagicMock()
        pago.monto = Decimal("10000")
        asunto = formatear_asunto_resumen([pago], "Tienda")
        assert "1 pago" in asunto
        assert "pagos" not in asunto


class TestFormatearCuerpoHtmlResumen:
    def test_escapa_html_en_remitente(self) -> None:
        pago = MagicMock()
        pago.monto = Decimal("10000")
        pago.remitente = "<script>alert(1)</script>"
        pago.banco_origen = "Bancolombia"
        pago.fecha_pago = datetime.now(timezone.utc)
        cuerpo = formatear_cuerpo_html_resumen([pago], "Negocio", 5)
        assert "<script>" not in cuerpo
        assert "&lt;script&gt;" in cuerpo

    def test_sin_pagos_muestra_mensaje(self) -> None:
        cuerpo = formatear_cuerpo_html_resumen([], "Negocio", 5)
        assert "Sin pagos" in cuerpo

    def test_con_pagos_muestra_monto(self) -> None:
        pago = MagicMock()
        pago.monto = Decimal("99000")
        pago.remitente = "Carlos"
        pago.banco_origen = "Nequi"
        pago.fecha_pago = datetime.now(timezone.utc)
        cuerpo = formatear_cuerpo_html_resumen([pago], "Negocio", 5)
        assert "$99.000" in cuerpo
