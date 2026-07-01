"""Muestra y opcionalmente actualiza los datos de un cliente."""
import sys

sys.path.insert(0, ".")

from src.config.base_datos import SesionLocal
from src.modelos.cliente import Cliente


def ver_y_corregir_cliente(
    correo_dedicado: str,
    correos_notificacion: list[str] | None = None,
    telegram_chat_ids: list[str] | None = None,
) -> None:
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

        actualizado = False
        if correos_notificacion is not None:
            cliente.correos_notificacion = correos_notificacion
            actualizado = True
        if telegram_chat_ids is not None:
            cliente.telegram_chat_ids = telegram_chat_ids
            actualizado = True

        if actualizado:
            sesion.commit()
            print("\n--- Actualizado ---")
            if correos_notificacion is not None:
                print(f"correos_notificacion: {correos_notificacion}")
            if telegram_chat_ids is not None:
                print(f"telegram_chat_ids:    {telegram_chat_ids}")


if __name__ == "__main__":
    ver_y_corregir_cliente(
        correo_dedicado="negocio-ejemplo@tudominio.com",
        # correos_notificacion=["nuevo@correo.com"],
        # telegram_chat_ids=["-123456789"],
    )
