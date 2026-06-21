"""Envia un correo de prueba para verificar la API de Forward Email."""
import asyncio
import sys

sys.path.insert(0, ".")

from src.config.ajustes import ajustes
from src.notificador.correo import enviar_correo

_DESTINATARIO = "encierraculo@gmail.com"
_ASUNTO = "Prueba Forward Email API — Ex4cto Pagos"
_CUERPO = """
<h2>Conexion Forward Email API funcionando</h2>
<p>Este correo confirma que <strong>notificaciones@ex4cto.co</strong>
puede enviar notificaciones correctamente via Forward Email.</p>
"""


async def main() -> None:
    print(f"Enviando desde: {ajustes.correo_remitente}")
    print(f"Hacia: {_DESTINATARIO}")
    try:
        await enviar_correo(_DESTINATARIO, _ASUNTO, _CUERPO)
        print("Correo enviado exitosamente")
    except Exception as error:
        print(f"Error: {error}")


asyncio.run(main())
