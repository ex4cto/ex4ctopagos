"""Envia un correo de prueba para verificar la API de Resend."""
import asyncio
import sys

sys.path.insert(0, ".")

from src.notificador.correo import enviar_correo
from src.config.ajustes import ajustes


async def main() -> None:
    destinatario = "encierraculo@gmail.com"
    asunto = "Prueba Resend API — Ex4cto Pagos"
    cuerpo = """
    <h2>Conexion Resend API funcionando</h2>
    <p>Este correo confirma que <strong>notificaciones@ex4cto.co</strong>
    puede enviar notificaciones correctamente via Resend.</p>
    """

    print(f"Enviando desde: {ajustes.correo_remitente}")
    print(f"Hacia: {destinatario}")

    try:
        await enviar_correo(destinatario, asunto, cuerpo)
        print("Correo enviado exitosamente")
    except Exception as e:
        print(f"Error: {e}")


asyncio.run(main())
