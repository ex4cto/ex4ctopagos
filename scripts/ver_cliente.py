"""Muestra y opcionalmente actualiza los datos de un cliente."""
import sys

sys.path.insert(0, ".")

from src.config.base_datos import SesionLocal
from src.modelos.cliente import Cliente


def ver_y_corregir_cliente(correo_dedicado: str, correos_notificacion: list[str] | None = None) -> None:
    with SesionLocal() as sesion:
        cliente = sesion.query(Cliente).filter(Cliente.correo_dedicado == correo_dedicado).first()
        if not cliente:
            print(f"No se encontro cliente con correo '{correo_dedicado}'")
            return

        print("=== Cliente encontrado ===")
        print(f"ID:                    {cliente.id}")
        print(f"Nombre:                {cliente.nombre_negocio}")
        print(f"Correo dedicado:       {cliente.correo_dedicado}")
        print(f"Telegram IDs:          {cliente.telegram_chat_ids}")
        print(f"Correos notificacion:  {cliente.correos_notificacion}")
        print(f"Token dashboard:       {cliente.token_dashboard}")
        print(f"Activo:                {cliente.activo}")

        if correos_notificacion is not None:
            cliente.correos_notificacion = correos_notificacion
            sesion.commit()
            print(f"\nActualizado — correos_notificacion: {correos_notificacion}")


if __name__ == "__main__":
    ver_y_corregir_cliente(
        correo_dedicado="negocio1@ex4cto.co",
        correos_notificacion=["encierraculo@gmail.com"],
    )
