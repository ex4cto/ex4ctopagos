# Guía de Onboarding — Nuevo Cliente

Tiempo estimado: **15 minutos por cliente**.

---

## Lo que necesitas pedirle al cliente antes de empezar

- Acceso a su Gmail (para configurar el filtro de reenvío)
- El nombre de su negocio
- Correo(s) donde quiere recibir las notificaciones de pago
- Si quiere notificaciones por Telegram: que cree un grupo con sus empleados

---

## Paso 1 — Crear el alias en Forward Email

1. Entra a [forwardemail.net](https://forwardemail.net) → **Dominios** → **ex4cto.co** → **Alias**
2. Haz clic en **Alias +**
3. En **Nombre** pon el identificador del negocio (sin espacios, minúsculas). Ejemplo: `negocio2`
4. En **Destinatarios de reenvío** pega esta URL (cambia `negocio2` por el nombre que elegiste, y `TU_WEBHOOK_SECRET_AQUI` por el valor de `WEBHOOK_SECRET` en Railway):

```
https://ex4ctopagos-production.up.railway.app/webhook/email?secret=TU_WEBHOOK_SECRET_AQUI&correo=negocio2@ex4cto.co
```

   > **Nota de seguridad:** Forward Email no soporta headers personalizados, por lo que el secret viaja en la URL. Esto es una limitación conocida de la plataforma. Si el secret se expone, rotarlo en Railway y actualizar esta URL en todos los alias activos.

5. Haz clic en **Actualizar alias** (o **Crear alias**)

El cliente tendrá asignado el correo `negocio2@ex4cto.co`.

---

## Paso 2 — Registrar el cliente en la base de datos

Abre el archivo `scripts/insertar_cliente.py` y edita el bloque final con los datos del cliente:

```python
if __name__ == "__main__":
    insertar_cliente(
        nombre_negocio="Nombre del Negocio",
        correo_dedicado="negocio2@ex4cto.co",   # el alias que creaste en el paso 1
        telegram_chat_ids=[],                    # lo llenamos en el paso 4
        correos_notificacion=["correo@cliente.com"],
    )
```

Luego ejecuta desde la raíz del proyecto:

```bash
python scripts/insertar_cliente.py
```

La consola mostrará algo así:

```
Cliente creado exitosamente:
  Negocio:          Nombre del Negocio
  Correo dedicado:  negocio2@ex4cto.co
  ID:               xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Token dashboard:  yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy

URL del dashboard:
  https://ex4ctopagos-production.up.railway.app/dashboard/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
```

Guarda esa URL — se la darás al cliente al final.

---

## Paso 3 — Configurar el filtro de Gmail del cliente

El cliente debe hacer esto en **su Gmail personal** (el que recibe los correos del banco):

1. Abrir Gmail → ícono de ajustes (⚙️) → **Ver todos los ajustes**
2. Ir a la pestaña **Filtros y direcciones bloqueadas**
3. Hacer clic en **Crear un filtro nuevo**
4. En el campo **De**, pegar exactamente:

```
@notificacionesbancolombia.com OR @nequi.com.co
```

5. Hacer clic en **Crear filtro**
6. Marcar la opción **Reenviar a** y poner `negocio2@ex4cto.co`
7. También marcar **Omitir la Bandeja de entrada (archivarlo)** (opcional pero recomendado)
8. Hacer clic en **Crear filtro**

> Gmail puede pedir confirmar el correo de reenvío. Revisar la bandeja de `negocio2@ex4cto.co` o los logs de Railway para ver si llega la confirmación.

---

## Paso 4 — Configurar Telegram (si el cliente lo quiere)

El cliente debe hacer esto:

1. Buscar el bot `@ex4ctopagosbot` en Telegram (o el nombre de tu bot)
2. Agregar el bot al grupo de empleados del negocio
3. Escribir `/start` en el grupo

Tú debes obtener el `chat_id` del grupo. Abre en el navegador:

```
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
```

Busca en la respuesta JSON el campo `"chat": {"id": -xxxxxxxxxx}`. El número negativo es el `chat_id` del grupo.

Luego actualiza el cliente en la BD. Edita `scripts/ver_cliente.py`:

```python
if __name__ == "__main__":
    ver_y_corregir_cliente(
        correo_dedicado="negocio2@ex4cto.co",
        telegram_chat_ids=["-xxxxxxxxxx"],    # el chat_id que encontraste
    )
```

> **Nota:** `ver_cliente.py` actualmente solo actualiza `correos_notificacion`. Si necesitas actualizar `telegram_chat_ids`, edita el campo directamente en el script o usa la consola de Railway con `python scripts/ver_cliente.py`.

---

## Paso 5 — Hacer una prueba

Pide al cliente que haga una transferencia de prueba (puede ser $1.000) hacia su cuenta Bancolombia.

Verifica en Railway logs que:
1. Llega el webhook (`Email recibido`)
2. Se parsea correctamente (`Pago guardado`)
3. Llega el mensaje a Telegram
4. Llega el correo de notificación

---

## Paso 6 — Entregarle el dashboard al cliente

Comparte con el cliente la URL del dashboard que obtuviste en el Paso 2:

```
https://ex4ctopagos-production.up.railway.app/dashboard/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
```

Esta URL es privada — solo quienes la tengan pueden ver los pagos del negocio. El cliente puede guardarla como marcador en su navegador.

---

## Resumen rápido

| Paso | Quién lo hace | Tiempo |
|---|---|---|
| 1. Crear alias en Forward Email | Operador | 2 min |
| 2. Registrar cliente en BD | Operador | 1 min |
| 3. Filtro de Gmail | Cliente (con tu ayuda) | 5 min |
| 4. Telegram (opcional) | Cliente + Operador | 5 min |
| 5. Prueba de pago | Cliente | 2 min |
| 6. Entregar URL del dashboard | Operador | 1 min |

---

## Seguridad — recordatorios operativos

- **WEBHOOK_SECRET:** rotar en Forward Email si se sospecha que fue expuesto. Actualizar la variable en Railway inmediatamente después.
- **TOKEN_DASHBOARD de clientes:** el token de acceso al dashboard no expira. Si la URL de un cliente se filtra, actualiza `token_dashboard` en la base de datos manualmente y entrega la nueva URL al cliente.
- **TELEGRAM_BOT_TOKEN:** rotar en @BotFather si se sospecha compromiso. Volver a registrar el webhook con `/scripts/registrar_webhook_telegram.py`.
- **`AMBIENTE` en Railway DEBE ser `produccion`** — en ningún otro valor. Esto desactiva el logging SQL y las rutas `/docs`.

---

## Solución de problemas frecuentes

**No llega el webhook:**
- Verificar que el filtro de Gmail esté activo y el reenvío confirmado
- Verificar en Forward Email que el alias existe y tiene la URL correcta
- Revisar logs de Railway

**El parser no reconoce el pago:**
- Verificar que el correo del banco llegue desde `@notificacionesbancolombia.com` o `@nequi.com.co`
- Revisar en los logs el texto del email y comparar con el patrón del parser

**No llega la notificación de Telegram:**
- El bot debe ser **administrador** del grupo o el cliente debe haberle enviado `/start`
- El `chat_id` debe estar guardado correctamente en la BD (número negativo para grupos)

**No llega el correo de notificación:**
- Verificar `CORREO_REMITENTE` y `CORREO_CLAVE` en Railway
- Revisar logs de Railway para el error exacto de la API de Forward Email
