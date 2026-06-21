import html
import logging
from decimal import Decimal
from functools import partial

import httpx

from src.config.ajustes import ajustes
from src.modelos.pago import Pago
from src.servicios.reintentos import ResultadoEnvio, ejecutar_con_reintentos

logger = logging.getLogger(__name__)

_URL_FORWARDEMAIL = "https://api.forwardemail.net/v1/emails"

_PLANTILLA_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
    .tarjeta {{ background: #fff; border-radius: 8px; max-width: 480px; margin: auto;
                padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    h2 {{ color: #1a1a1a; margin: 0 0 24px; font-size: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ padding: 10px 0; border-bottom: 1px solid #f0f0f0; color: #444; font-size: 15px; }}
    td:first-child {{ color: #888; width: 40%; }}
    .monto {{ font-size: 22px; font-weight: bold; color: #2e7d32; }}
    .pie {{ margin-top: 24px; font-size: 12px; color: #aaa; text-align: center; }}
  </style>
</head>
<body>
  <div class="tarjeta">
    <h2>Nuevo pago recibido</h2>
    <table>
      <tr><td>Negocio</td><td><b>{negocio}</b></td></tr>
      <tr><td>Monto</td><td class="monto">{monto}</td></tr>
      <tr><td>De</td><td>{remitente}</td></tr>
      <tr><td>Banco</td><td>{banco}</td></tr>
      <tr><td>Fecha</td><td>{fecha}</td></tr>
    </table>
    <p class="pie">Notificacion automatica — Bot de Comprobante de Pago</p>
  </div>
</body>
</html>"""


class ErrorNotificacionCorreo(Exception):
    pass


def formatear_asunto(pago: Pago) -> str:
    monto_fmt = _formatear_monto(pago.monto)
    return f"Pago recibido — {monto_fmt} via {pago.banco_origen}"


def formatear_cuerpo_html(pago: Pago, nombre_negocio: str) -> str:
    return _PLANTILLA_HTML.format(
        negocio=html.escape(nombre_negocio),
        monto=_formatear_monto(pago.monto),
        remitente=html.escape(pago.remitente),
        banco=html.escape(pago.banco_origen),
        fecha=pago.fecha_pago.strftime("%d/%m/%Y %H:%M"),
    )


async def enviar_correo(destinatario: str, asunto: str, cuerpo_html: str) -> bool:
    auth = (ajustes.correo_remitente, ajustes.correo_clave)
    cuerpo = {
        "from": ajustes.correo_remitente,
        "to": destinatario,
        "subject": asunto,
        "html": cuerpo_html,
    }
    async with httpx.AsyncClient(timeout=15) as cliente:
        respuesta = await cliente.post(_URL_FORWARDEMAIL, json=cuerpo, auth=auth)
    if respuesta.status_code not in (200, 201):
        raise ErrorNotificacionCorreo(
            f"Forward Email API error {respuesta.status_code}: {respuesta.text[:200]}"
        )
    logger.info("Correo enviado a %s", destinatario)
    return True


async def notificar_todos(
    correos: list[str],
    pago: Pago,
    nombre_negocio: str,
) -> dict[str, ResultadoEnvio]:
    asunto = formatear_asunto(pago)
    cuerpo_html = formatear_cuerpo_html(pago, nombre_negocio)
    resultados: dict[str, ResultadoEnvio] = {}
    for destino in correos:
        resultados[destino] = await ejecutar_con_reintentos(
            fn=partial(enviar_correo, destino, asunto, cuerpo_html),
            max_intentos=ajustes.max_reintentos_notificacion,
            intervalo_segundos=ajustes.intervalo_reintento_segundos,
        )
    return resultados


def _formatear_monto(monto: Decimal) -> str:
    entero = int(monto)
    return f"${entero:,}".replace(",", ".")
