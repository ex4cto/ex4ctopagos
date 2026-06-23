import html
import logging
from datetime import datetime, timezone
from decimal import Decimal
from functools import partial

from sqlalchemy.orm import Session

from src.config.ajustes import ajustes
from src.modelos.cliente import Cliente
from src.notificador import correo as correo_notificador
from src.notificador.telegram import enviar_mensaje
from src.repositorios import cliente_repo
from src.servicios.reintentos import ResultadoEnvio, ejecutar_con_reintentos
from src.webhook.schemas import PagoExtraido

logger = logging.getLogger(__name__)

_DIAS_AVISO_VENCIMIENTO: int = 5


def _formatear_monto(monto: int) -> str:
    return f"${monto:,}".replace(",", ".")


def _formatear_fecha(cliente: Cliente) -> str:
    if not cliente.fecha_vencimiento_suscripcion:
        return "—"
    return cliente.fecha_vencimiento_suscripcion.strftime("%d/%m/%Y")


def _asunto_renovacion(nombre_negocio: str) -> str:
    return f"Suscripción renovada — {html.escape(nombre_negocio)}"


def _cuerpo_renovacion(cliente: Cliente) -> str:
    monto = _formatear_monto(ajustes.precio_suscripcion_cop)
    fecha = _formatear_fecha(cliente)
    return (
        f"<p>Tu suscripción al sistema de comprobante de pago fue renovada exitosamente.</p>"
        f"<p><b>Negocio:</b> {html.escape(cliente.nombre_negocio)}</p>"
        f"<p><b>Monto pagado:</b> {monto}</p>"
        f"<p><b>Próximo vencimiento:</b> {fecha}</p>"
    )


def _asunto_aviso_vencimiento(nombre_negocio: str, dias: int) -> str:
    return f"Tu suscripción vence en {dias} día{'s' if dias != 1 else ''} — {html.escape(nombre_negocio)}"


def _cuerpo_aviso_vencimiento(cliente: Cliente, dias: int) -> str:
    monto = _formatear_monto(ajustes.precio_suscripcion_cop)
    llave = html.escape(ajustes.llave_cobro_operador)
    fecha = _formatear_fecha(cliente)
    return (
        f"<p>Tu suscripción vence en <b>{dias} día{'s' if dias != 1 else ''}</b> ({fecha}).</p>"
        f"<p>Para renovar, realizá una transferencia de <b>{monto}</b> a la llave <b>{llave}</b>.</p>"
        f"<p>El sistema detectará el pago automáticamente y renovará tu acceso.</p>"
    )


async def procesar_pago_suscripcion(pago: PagoExtraido, sesion: Session) -> None:
    precio_esperado = Decimal(ajustes.precio_suscripcion_cop)
    if pago.monto != precio_esperado:
        logger.info(
            "Pago de suscripcion ignorado — monto %s no coincide con precio %s",
            pago.monto,
            precio_esperado,
        )
        return

    cliente = cliente_repo.buscar_por_titular(pago.remitente, sesion)
    if not cliente:
        logger.warning(
            "Pago de suscripcion sin titular registrado — remitente: %s",
            pago.remitente,
        )
        return

    cliente_repo.renovar_suscripcion(cliente.id, sesion)
    sesion.refresh(cliente)

    fecha = _formatear_fecha(cliente)
    await enviar_mensaje(
        ajustes.operador_telegram_chat_id,
        f"✅ Suscripción renovada — {html.escape(cliente.nombre_negocio)} — vence {fecha}",
    )

    correos: list[str] = cliente.correos_notificacion or []
    for destino in correos:
        await ejecutar_con_reintentos(
            fn=partial(
                correo_notificador.enviar_correo,
                destino,
                _asunto_renovacion(cliente.nombre_negocio),
                _cuerpo_renovacion(cliente),
            ),
            max_intentos=ajustes.max_reintentos_notificacion,
            intervalo_segundos=ajustes.intervalo_reintento_segundos,
        )

    logger.info("Suscripcion renovada — cliente: %s", cliente.nombre_negocio)


async def notificar_vencimientos_proximos(sesion: Session) -> None:
    proximos = cliente_repo.listar_por_vencer(_DIAS_AVISO_VENCIMIENTO, sesion)
    for cliente in proximos:
        if not cliente.fecha_vencimiento_suscripcion:
            continue
        dias = (cliente.fecha_vencimiento_suscripcion - datetime.now(timezone.utc)).days

        await enviar_mensaje(
            ajustes.operador_telegram_chat_id,
            f"⚠️ Suscripción por vencer — {html.escape(cliente.nombre_negocio)} — {dias} día{'s' if dias != 1 else ''}",
        )

        correos: list[str] = cliente.correos_notificacion or []
        for destino in correos:
            await ejecutar_con_reintentos(
                fn=partial(
                    correo_notificador.enviar_correo,
                    destino,
                    _asunto_aviso_vencimiento(cliente.nombre_negocio, dias),
                    _cuerpo_aviso_vencimiento(cliente, dias),
                ),
                max_intentos=ajustes.max_reintentos_notificacion,
                intervalo_segundos=ajustes.intervalo_reintento_segundos,
            )

        logger.info(
            "Aviso de vencimiento enviado — cliente: %s, dias: %d",
            cliente.nombre_negocio,
            dias,
        )


async def desactivar_vencidos(sesion: Session) -> None:
    vencidos = cliente_repo.listar_suscripcion_vencida(sesion)
    for cliente in vencidos:
        cliente.suscripcion_activa = False
        logger.warning(
            "Suscripcion desactivada por vencimiento — cliente: %s",
            cliente.nombre_negocio,
        )
    if vencidos:
        sesion.commit()
