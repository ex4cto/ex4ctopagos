# Bot Comprobante de Pago

Sistema SaaS de notificaciones de pago para pequeños negocios en Colombia. Cuando un cliente paga por transferencia bancaria, el correo de confirmación del banco le llega solo al dueño del negocio. Este sistema intercepta esos correos automáticamente, extrae los datos del pago y envía notificaciones instantáneas al grupo de Telegram del negocio y a los correos configurados — sin intervención manual.

## Funcionalidades

**Para cada negocio cliente:**
- Dirección de correo dedicada para recibir notificaciones bancarias
- Alertas de pago instantáneas por Telegram y correo
- Dashboard tokenizado con métricas del día/semana/mes e historial completo — sin login

**Para el operador (dueño del SaaS):**
- Bot de Telegram con asistente `/nuevo_cliente` para registrar nuevos clientes paso a paso
- Dashboard del operador con métricas globales y pagos recientes de todos los clientes
- Tarea de fondo diaria que envía recordatorios de renovación 5 días antes del vencimiento y desactiva suscripciones vencidas
- Gestión de aliases vía Forward Email REST API

**Bancos soportados:**
- Bancolombia
- Nequi

## Requisitos

- Python 3.13+
- PostgreSQL
- Cuenta en [Forward Email](https://forwardemail.net) (webhooks entrantes + gestión de aliases)
- Token de bot de Telegram desde [BotFather](https://t.me/BotFather)

## Instalación

```bash
git clone https://github.com/ex4cto/ex4ctopagos.git
cd ex4ctopagos

python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

Copiá `.env.example` a `.env` y completá los valores:

```bash
cp .env.example .env
```

Ejecutá las migraciones de base de datos:

```bash
alembic upgrade head
```

## Configuración

| Variable | Requerida | Descripción |
|---|---|---|
| `WEBHOOK_SECRET` | ✅ | Secreto para validar webhooks entrantes de Forward Email (40+ caracteres) |
| `TELEGRAM_BOT_TOKEN` | ✅ | Token del bot desde BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | ✅ | Secreto para validar llamadas del webhook de Telegram |
| `DATABASE_URL` | ✅ | Cadena de conexión PostgreSQL (`postgresql://user:pass@host/db`) |
| `OPERADOR_CLAVE` | ✅ | Contraseña del dashboard del operador (40+ caracteres) |
| `SECRET_KEY` | ✅ | Clave para firmar cookies de sesión (64+ caracteres) |
| `CORREO_REMITENTE` | — | Dirección de correo para enviar notificaciones salientes |
| `CORREO_CLAVE` | — | Clave de la API REST de Forward Email |
| `CORREO_CONFIRMACION_ALIAS` | — | Correo que recibe los enlaces de confirmación de aliases |
| `OPERADOR_TELEGRAM_CHAT_ID` | — | Chat ID de Telegram del operador — requerido para `/nuevo_cliente` |
| `FORWARD_EMAIL_DOMINIO` | — | Dominio para aliases de clientes (ej. `pagos.tudominio.com`) |
| `LLAVE_COBRO_OPERADOR` | — | Llave de pago mostrada a clientes para renovaciones |
| `PRECIO_SUSCRIPCION_COP` | — | Precio mensual de suscripción en COP (por defecto: `50000`) |
| `APP_URL` | — | URL pública de la app (por defecto: `http://localhost:8000`) |
| `AMBIENTE` | — | Usar `desarrollo` para habilitar `/docs` y desactivar cookies HTTPS-only |

## Ejecución

**Desarrollo local:**

```bash
uvicorn src.main:aplicacion --reload
```

**Producción (Railway):**

```bash
alembic upgrade head && uvicorn src.main:aplicacion --host 0.0.0.0 --port $PORT
```

## Webhooks

Después de desplegar, registrá el webhook de Telegram:

```bash
python scripts/registrar_webhook_telegram.py
```

Configurá Forward Email para hacer POST de correos entrantes a:

```
https://tu-app-url/webhook/email
```

## Scripts de utilidad

| Script | Propósito |
|---|---|
| `scripts/insertar_cliente.py` | Registrar un nuevo negocio cliente en la BD |
| `scripts/ver_cliente.py` | Consultar y opcionalmente actualizar un cliente |
| `scripts/probar_smtp.py` | Probar el envío de correo saliente |
| `scripts/registrar_webhook_telegram.py` | Registrar la URL del webhook de Telegram |

## Arquitectura

```
ruta → servicio → repositorio → modelo
```

```
src/
├── main.py                     # App FastAPI, middlewares, validación al inicio
├── config/                     # Variables de entorno y sesión de base de datos
├── webhook/                    # Webhook entrante de correo (Forward Email)
├── telegram/                   # Webhook entrante de Telegram
├── parser/                     # Parsers de correos bancarios (Bancolombia, Nequi)
├── notificador/                # Envío de mensajes por Telegram y correo
├── modelos/                    # Modelos SQLAlchemy (clientes, pagos, logs)
├── repositorios/               # Consultas a la base de datos
├── servicios/                  # Lógica de negocio (pagos, suscripciones, aliases)
└── dashboard/                  # Templates Jinja2 + rutas para negocios y operador
```

**Flujo de pago:** Forward Email recibe el correo de confirmación del banco → POST webhook → FastAPI valida el secreto, deduplica por `messageId`, detecta el banco, ejecuta el parser → guarda el registro de pago → envía notificaciones por Telegram y correo con hasta 3 reintentos → registra cada intento en logs.

## Agregar un nuevo banco

1. Crear `src/parser/<banco>.py` implementando la interfaz `ParserBase`
2. Registrar el dominio del remitente en `src/parser/base.py`
3. Agregar el parser a la fábrica en `src/parser/fabrica.py`

## Tests

```bash
pytest
```

## Licencia

MIT
