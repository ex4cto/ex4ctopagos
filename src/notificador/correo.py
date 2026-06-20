import asyncio
import logging
import smtplib
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config.ajustes import ajustes
from src.modelos.pago import Pago

logger = logging.getLogger(__name__)


class ErrorNotificacionCorreo(Exception):
    pass


def formatear_asunto(pago: Pago) -> str:
    monto_fmt = _formatear_monto(pago.monto)
    return f"Pago recibido — {monto_fmt} via {pago.banco_origen}"


def formatear_cuerpo_html(pago: Pago, nombre_negocio: str) -> str:
    monto_fmt = _formatear_monto(pago.monto)
    fecha_fmt = pago.fecha_pago.strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
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
      <tr><td>Negocio</td><td><b>{nombre_negocio}</b></td></tr>
      <tr><td>Monto</td><td class="monto">{monto_fmt}</td></tr>
      <tr><td>De</td><td>{pago.remitente}</td></tr>
      <tr><td>Banco</td><td>{pago.banco_origen}</td></tr>
      <tr><td>Fecha</td><td>{fecha_fmt}</td></tr>
    </table>
    <p class="pie">Notificacion automatica — Bot de Comprobante de Pago</p>
  </div>
</body>
</html>"""


async def enviar_correo(destinatario: str, asunto: str, cuerpo_html: str) -> bool:
    await asyncio.to_thread(_enviar_smtp, destinatario, asunto, cuerpo_html)
    return True


def _enviar_smtp(destinatario: str, asunto: str, cuerpo_html: str) -> None:
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = ajustes.smtp_usuario
    mensaje["To"] = destinatario
    mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    with smtplib.SMTP(ajustes.smtp_host, ajustes.smtp_puerto, timeout=15) as servidor:
        servidor.starttls()
        servidor.login(ajustes.smtp_usuario, ajustes.smtp_clave)
        servidor.sendmail(ajustes.smtp_usuario, [destinatario], mensaje.as_string())
        logger.info("Correo enviado a %s", destinatario)


async def notificar_todos(
    correos: list[str],
    pago: Pago,
    nombre_negocio: str,
) -> dict[str, "ResultadoEnvio"]:
    from src.servicios.reintentos import ResultadoEnvio, ejecutar_con_reintentos

    asunto = formatear_asunto(pago)
    cuerpo_html = formatear_cuerpo_html(pago, nombre_negocio)
    resultados: dict[str, ResultadoEnvio] = {}
    for correo in correos:
        resultados[correo] = await ejecutar_con_reintentos(
            fn=lambda dest=correo: enviar_correo(dest, asunto, cuerpo_html),
            max_intentos=ajustes.max_reintentos_notificacion,
            intervalo_segundos=ajustes.intervalo_reintento_segundos,
        )
    return resultados


def _formatear_monto(monto: Decimal) -> str:
    entero = int(monto)
    return f"${entero:,}".replace(",", ".")
