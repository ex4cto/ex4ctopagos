# Plan — Comando /verificar en Telegram

## Objetivo

El empleado escribe `/verificar` en el grupo de Telegram del negocio.
El bot responde con los pagos recibidos en los últimos 5 minutos para ese negocio.
Si no hay pagos recientes, responde que no hay ninguno.

El dueño ya no necesita notificaciones automáticas porque el banco ya le avisa.
Los empleados no ven historial acumulado — solo el pago que acaba de ocurrir.

---

## Flujo completo

```
Empleado escribe /verificar en el grupo
        ↓
Telegram envía POST /telegram/webhook (con secret token en header)
        ↓
Validar X-Telegram-Bot-Api-Secret-Token
        ↓
Detectar que es el comando /verificar
        ↓
Buscar cliente por chat_id en la BD
        ↓
Consultar pagos de los últimos 5 minutos para ese cliente
        ↓
Responder en el mismo grupo con el resultado
```

---

## Arquitectura — archivos nuevos y modificados

```
src/
├── telegram/                          NUEVO módulo
│   ├── __init__.py
│   ├── schemas.py                     Modelos Pydantic del payload de Telegram
│   ├── validador.py                   Valida X-Telegram-Bot-Api-Secret-Token
│   └── rutas.py                       POST /telegram/webhook
├── servicios/
│   └── verificar_pago.py              NUEVO — lógica del comando /verificar
├── repositorios/
│   ├── cliente_repo.py                MODIFICAR — agregar obtener_por_chat_id
│   └── pago_repo.py                   MODIFICAR — agregar listar_ultimos_minutos
└── config/
    └── ajustes.py                     MODIFICAR — agregar telegram_webhook_secret

scripts/
└── registrar_webhook_telegram.py      NUEVO — registra la URL en Telegram

tests/
└── test_verificar_pago.py             NUEVO — tests del servicio y comando

main.py                                MODIFICAR — incluir enrutador de telegram
```

---

## Fase 1 — Infraestructura del webhook de Telegram

### Parte 1.1 — Agregar `telegram_webhook_secret` a `ajustes.py`

**Archivo:** `src/config/ajustes.py`

Agregar debajo de `telegram_bot_token`:
```python
telegram_webhook_secret: str = ""
```

Agregar en Railway y en `.env` local:
```
TELEGRAM_WEBHOOK_SECRET=<string aleatorio 40+ caracteres>
```

---

### Parte 1.2 — Modelos Pydantic del payload de Telegram

**Archivo:** `src/telegram/schemas.py`

Telegram envía un objeto `Update` con un `message` que contiene `chat`, `text` y `from`.
Solo se modela lo que se usa — no todo el API de Telegram.

```python
from pydantic import BaseModel


class ChatTelegram(BaseModel):
    id: int
    type: str  # "group", "supergroup", "private"


class RemitenteTelegram(BaseModel):
    id: int
    username: str | None = None
    first_name: str = ""


class MensajeTelegram(BaseModel):
    message_id: int
    chat: ChatTelegram
    remitente: RemitenteTelegram | None = None
    texto: str | None = None

    model_config = {"populate_by_name": True}


class ActualizacionTelegram(BaseModel):
    update_id: int
    message: MensajeTelegram | None = None
```

> **Estándar:** campos en español donde son nuestros, se respetan los nombres del API
> de Telegram (snake_case inglés) solo cuando Pydantic los mapea por alias.

---

### Parte 1.3 — Validador del webhook de Telegram

**Archivo:** `src/telegram/validador.py`

Telegram envía el secret token configurado en el header `X-Telegram-Bot-Api-Secret-Token`.
Comparar con `hmac.compare_digest` igual que el webhook de correo.

```python
import hmac

from src.config.ajustes import ajustes


class ErrorTokenTelegramInvalido(Exception):
    pass


def validar_token_telegram(token_recibido: str) -> None:
    if not ajustes.telegram_webhook_secret:
        raise ErrorTokenTelegramInvalido("TELEGRAM_WEBHOOK_SECRET no configurado")
    if not hmac.compare_digest(token_recibido, ajustes.telegram_webhook_secret):
        raise ErrorTokenTelegramInvalido("Token de webhook de Telegram invalido")
```

---

### Parte 1.4 — Endpoint del webhook

**Archivo:** `src/telegram/rutas.py`

```python
import logging

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.config.base_datos import obtener_sesion
from src.servicios.verificar_pago import procesar_actualizacion
from src.telegram.schemas import ActualizacionTelegram
from src.telegram.validador import ErrorTokenTelegramInvalido, validar_token_telegram

logger = logging.getLogger(__name__)

enrutador = APIRouter(prefix="/telegram", tags=["telegram"])

_RESPUESTA_OK: dict[str, str] = {"estado": "ok"}


@enrutador.post("/webhook", response_model=None)
async def recibir_actualizacion(
    actualizacion: ActualizacionTelegram,
    x_telegram_bot_api_secret_token: str = Header(default=""),
    sesion: Session = Depends(obtener_sesion),
) -> dict[str, str] | JSONResponse:
    try:
        validar_token_telegram(x_telegram_bot_api_secret_token)
    except ErrorTokenTelegramInvalido as error:
        logger.warning("Webhook Telegram rechazado: %s", error)
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    await procesar_actualizacion(actualizacion, sesion)
    return _RESPUESTA_OK
```

---

### Parte 1.5 — Registrar en `main.py`

```python
from src.telegram.rutas import enrutador as enrutador_telegram
aplicacion.include_router(enrutador_telegram)
```

---

### Parte 1.6 — Script para registrar el webhook en Telegram

**Archivo:** `scripts/registrar_webhook_telegram.py`

```python
"""Registra la URL del webhook en Telegram. Ejecutar una sola vez por despliegue."""
import asyncio
import sys

sys.path.insert(0, ".")

import httpx

from src.config.ajustes import ajustes

_URL_SET_WEBHOOK = "https://api.telegram.org/bot{token}/setWebhook"


async def registrar() -> None:
    url_webhook = f"{ajustes.app_url}/telegram/webhook"
    payload = {
        "url": url_webhook,
        "secret_token": ajustes.telegram_webhook_secret,
        "allowed_updates": ["message"],
    }
    url_api = _URL_SET_WEBHOOK.format(token=ajustes.telegram_bot_token)
    async with httpx.AsyncClient(timeout=10) as cliente:
        respuesta = await cliente.post(url_api, json=payload)
    print(f"Estado: {respuesta.status_code}")
    print(respuesta.json())


asyncio.run(registrar())
```

> Ejecutar desde Railway CLI o localmente con el `.env` de producción cargado.

---

## Fase 2 — Repositorio

### Parte 2.1 — `cliente_repo.obtener_por_chat_id`

**Archivo:** `src/repositorios/cliente_repo.py`

Busca el cliente activo que tenga el `chat_id` en su lista JSONB `telegram_chat_ids`.
Usa el operador `@>` de PostgreSQL para buscar dentro del array JSONB.

```python
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB

def obtener_por_chat_id(chat_id: str, sesion: Session) -> Cliente | None:
    return (
        sesion.query(Cliente)
        .filter(
            Cliente.activo.is_(True),
            Cliente.telegram_chat_ids.op("@>")(cast([chat_id], JSONB)),
        )
        .first()
    )
```

---

### Parte 2.2 — `pago_repo.listar_ultimos_minutos`

**Archivo:** `src/repositorios/pago_repo.py`

```python
from datetime import timedelta

def listar_ultimos_minutos(
    cliente_id: uuid.UUID,
    minutos: int,
    ahora: datetime,
    sesion: Session,
) -> list[Pago]:
    desde = ahora - timedelta(minutes=minutos)
    return (
        sesion.query(Pago)
        .filter(Pago.cliente_id == cliente_id, Pago.fecha_recibido >= desde)
        .order_by(Pago.fecha_recibido.desc())
        .all()
    )
```

> Se usa `fecha_recibido` (cuándo lo procesó el sistema) y no `fecha_pago`
> (cuándo ocurrió en el banco) para cubrir el caso de emails con delay.

---

## Fase 3 — Servicio de verificación

**Archivo:** `src/servicios/verificar_pago.py`

Orquesta: detectar comando → buscar cliente → consultar pagos → enviar respuesta.
Es la única capa con lógica de negocio — las rutas y repos no toman decisiones.

```python
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.modelos.pago import Pago
from src.notificador.telegram import enviar_mensaje
from src.repositorios import cliente_repo, pago_repo
from src.telegram.schemas import ActualizacionTelegram

logger = logging.getLogger(__name__)

_COMANDO_VERIFICAR = "/verificar"
_VENTANA_MINUTOS = 5


def _es_comando_verificar(texto: str | None) -> bool:
    if not texto:
        return False
    return texto.strip().lower().startswith(_COMANDO_VERIFICAR)


def _formatear_respuesta(pagos: list[Pago]) -> str:
    if not pagos:
        return f"Sin pagos en los ultimos {_VENTANA_MINUTOS} minutos."

    lineas = [f"Pagos recibidos (ultimos {_VENTANA_MINUTOS} min):\n"]
    for pago in pagos:
        minutos_transcurridos = int(
            (datetime.now(timezone.utc) - pago.fecha_recibido).total_seconds() / 60
        )
        lineas.append(
            f"✓ <b>{_formatear_monto(pago.monto)}</b> de {pago.remitente}"
            f" — hace {minutos_transcurridos} min"
        )
    return "\n".join(lineas)


def _formatear_monto(monto) -> str:
    return f"${int(monto):,}".replace(",", ".")


async def procesar_actualizacion(
    actualizacion: ActualizacionTelegram,
    sesion: Session,
) -> None:
    mensaje = actualizacion.message
    if not mensaje:
        return
    if not _es_comando_verificar(mensaje.texto):
        return

    chat_id = str(mensaje.chat.id)
    ahora = datetime.now(timezone.utc)

    cliente = cliente_repo.obtener_por_chat_id(chat_id, sesion)
    if not cliente:
        logger.warning("Comando /verificar desde chat_id desconocido: %s", chat_id)
        return

    pagos = pago_repo.listar_ultimos_minutos(cliente.id, _VENTANA_MINUTOS, ahora, sesion)
    respuesta = _formatear_respuesta(pagos)

    await enviar_mensaje(chat_id, respuesta)
    logger.info("Comando /verificar respondido — cliente: %s, pagos: %d", cliente.nombre_negocio, len(pagos))
```

---

## Fase 4 — Tests

**Archivo:** `tests/test_verificar_pago.py`

### Tests del detector de comando
```python
def test_detecta_comando_verificar():
    assert _es_comando_verificar("/verificar") is True
    assert _es_comando_verificar("/VERIFICAR") is True
    assert _es_comando_verificar("/verificar pago") is True
    assert _es_comando_verificar("/otro") is False
    assert _es_comando_verificar(None) is False
    assert _es_comando_verificar("") is False
```

### Tests del formateador de respuesta
```python
def test_respuesta_sin_pagos():
    assert "Sin pagos" in _formatear_respuesta([])

def test_respuesta_con_pagos():
    # Crear pago mock con monto y remitente
    # Verificar que aparece el monto formateado y el nombre
```

### Test del endpoint
```python
# POST /telegram/webhook con header X-Telegram-Bot-Api-Secret-Token
# sin el token → 403
# con token válido pero sin /verificar → 200 sin efecto
# con token válido y /verificar → 200, enviar_mensaje llamado
```

---

## Fase 5 — Configuración final

### Paso 5.1 — Agregar `TELEGRAM_WEBHOOK_SECRET` a Railway

En Railway → Variables:
```
TELEGRAM_WEBHOOK_SECRET=<string aleatorio 40+ caracteres>
```

### Paso 5.2 — Ejecutar el script de registro

Una vez desplegado en Railway:
```bash
python scripts/registrar_webhook_telegram.py
```

Verificar que Telegram responde `{"ok": true}`.

### Paso 5.3 — Actualizar la guía de onboarding

Agregar en `GUIA_ONBOARDING.md` que los grupos de Telegram ya no reciben
notificaciones automáticas — el empleado usa `/verificar` cuando necesita confirmar
un pago.

---

## Resumen de archivos por fase

| Fase | Archivos | Acción |
|---|---|---|
| 1 | `src/config/ajustes.py` | Agregar `telegram_webhook_secret` |
| 1 | `src/telegram/schemas.py` | NUEVO |
| 1 | `src/telegram/validador.py` | NUEVO |
| 1 | `src/telegram/rutas.py` | NUEVO |
| 1 | `src/main.py` | Registrar enrutador |
| 1 | `scripts/registrar_webhook_telegram.py` | NUEVO |
| 2 | `src/repositorios/cliente_repo.py` | Agregar `obtener_por_chat_id` |
| 2 | `src/repositorios/pago_repo.py` | Agregar `listar_ultimos_minutos` |
| 3 | `src/servicios/verificar_pago.py` | NUEVO |
| 4 | `tests/test_verificar_pago.py` | NUEVO |
| 5 | Railway + script de registro | Configuración |

---

## Notas técnicas importantes

**¿Por qué `fecha_recibido` y no `fecha_pago` en la ventana de tiempo?**
El banco puede tardar minutos en enviar el correo. Si el empleado escribe
`/verificar` 3 minutos después del pago, `fecha_pago` podría quedar fuera de la
ventana de 5 minutos aunque el sistema lo procesó ahora.

**¿Por qué `chat_id` como string en `telegram_chat_ids`?**
Los IDs de grupos son números negativos grandes (ej. `-1001234567890`).
Se guardan como strings en el JSONB para consistencia y porque la API de Telegram
los usa como strings en algunos contextos.

**¿Qué pasa si el bot no está en el grupo?**
Telegram no envía el webhook. El bot debe ser miembro del grupo.

**Notificaciones automáticas — ¿se eliminan?**
No se eliminan del código — se vuelven opt-in. El cliente que quiera
notificaciones automáticas deja el grupo en `telegram_chat_ids`. El cliente
que prefiera privacidad lo deja vacío y usa `/verificar`.
