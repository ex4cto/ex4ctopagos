"""Inserta un nuevo cliente en la BD. Uso: python scripts/insertar_cliente.py"""
import sys
import uuid

sys.path.insert(0, ".")

from src.config.ajustes import ajustes
from src.config.base_datos import SesionLocal
from src.modelos.cliente import Cliente


def insertar_cliente(
    nombre_negocio: str,
    correo_dedicado: str,
    telegram_chat_ids: list[str],
    correos_notificacion: list[str],
) -> None:
    sesion = SesionLocal()
    try:
        existente = sesion.query(Cliente).filter(
            Cliente.correo_dedicado == correo_dedicado
        ).first()
        if existente:
            print(f"Ya existe un cliente con correo '{correo_dedicado}'")
            print(f"  ID: {existente.id}")
            print(f"  Token dashboard: {existente.token_dashboard}")
            return

        cliente = Cliente(
            nombre_negocio=nombre_negocio,
            correo_dedicado=correo_dedicado,
            telegram_chat_ids=telegram_chat_ids,
            correos_notificacion=correos_notificacion,
            token_dashboard=uuid.uuid4(),
            activo=True,
        )
        sesion.add(cliente)
        sesion.commit()
        sesion.refresh(cliente)

        print("Cliente creado exitosamente:")
        print(f"  Negocio:          {cliente.nombre_negocio}")
        print(f"  Correo dedicado:  {cliente.correo_dedicado}")
        print(f"  Telegram IDs:     {cliente.telegram_chat_ids}")
        print(f"  Correos:          {cliente.correos_notificacion}")
        print(f"  ID:               {cliente.id}")
        print(f"  Token dashboard:  {cliente.token_dashboard}")
        print()
        print("URL del dashboard:")
        print(f"  {ajustes.app_url}/dashboard/{cliente.token_dashboard}")
    finally:
        sesion.close()


if __name__ == "__main__":
    insertar_cliente(
        nombre_negocio="Negocio Prueba",
        correo_dedicado="negocio1@ex4cto.co",
        telegram_chat_ids=["5870211102"],
        correos_notificacion=["encierraculo@gmail.com"],
    )
