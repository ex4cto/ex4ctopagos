# Bot Comprobante de Pago

SaaS payment notification system for Colombian small businesses. When a customer pays by bank transfer, the bank's confirmation email goes only to the business owner. This system intercepts those emails automatically, parses the payment data, and instantly pushes notifications to the business's Telegram group and configured email addresses — with no manual intervention.

## Features

**For each business client:**
- Dedicated inbound email address for receiving bank notifications
- Instant payment alerts delivered to Telegram and email
- Tokenized dashboard with today/week/month metrics and full payment history — no login required

**For the operator (SaaS owner):**
- Telegram bot with `/nuevo_cliente` wizard to onboard new clients step-by-step
- Operator dashboard with global metrics and all clients' recent payments
- Daily background task that sends renewal reminders 5 days before expiry and deactivates expired subscriptions
- Alias management via Forward Email REST API

**Banks supported:**
- Bancolombia
- Nequi

## Requirements

- Python 3.13+
- PostgreSQL
- [Forward Email](https://forwardemail.net) account (inbound webhooks + alias management)
- Telegram bot token from [BotFather](https://t.me/BotFather)

## Installation

```bash
git clone https://github.com/ex4cto/ex4ctopagos.git
cd ex4ctopagos

python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Run database migrations:

```bash
alembic upgrade head
```

## Configuration

| Variable | Required | Description |
|---|---|---|
| `WEBHOOK_SECRET` | ✅ | Secret for validating inbound Forward Email webhooks (40+ chars) |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | ✅ | Secret for validating Telegram webhook calls |
| `DATABASE_URL` | ✅ | PostgreSQL connection string (`postgresql://user:pass@host/db`) |
| `OPERADOR_CLAVE` | ✅ | Operator dashboard password (40+ chars) |
| `SECRET_KEY` | ✅ | Session cookie signing key (64+ chars) |
| `CORREO_REMITENTE` | — | Outbound notification email address |
| `CORREO_CLAVE` | — | Forward Email REST API key |
| `CORREO_CONFIRMACION_ALIAS` | — | Email address that receives alias confirmation links |
| `OPERADOR_TELEGRAM_CHAT_ID` | — | Operator's Telegram chat ID — required for `/nuevo_cliente` |
| `FORWARD_EMAIL_DOMINIO` | — | Domain for client aliases (e.g. `pagos.tudominio.com`) |
| `LLAVE_COBRO_OPERADOR` | — | Payment key shown to clients for subscription renewals |
| `PRECIO_SUSCRIPCION_COP` | — | Monthly subscription price in COP (default: `50000`) |
| `APP_URL` | — | Public URL of the app (default: `http://localhost:8000`) |
| `AMBIENTE` | — | Set to `desarrollo` to enable `/docs` and disable HTTPS-only cookies |

## Running

**Local development:**

```bash
uvicorn src.main:aplicacion --reload
```

**Production (Railway):**

```bash
alembic upgrade head && uvicorn src.main:aplicacion --host 0.0.0.0 --port $PORT
```

## Webhooks

After deploying, register the Telegram webhook:

```bash
python scripts/registrar_webhook_telegram.py
```

Configure Forward Email to POST inbound emails to:

```
https://your-app-url/webhook/email
```

## Utility scripts

| Script | Purpose |
|---|---|
| `scripts/insertar_cliente.py` | Register a new business client in the DB |
| `scripts/ver_cliente.py` | Inspect and optionally update a client record |
| `scripts/probar_smtp.py` | Test outbound email delivery |
| `scripts/registrar_webhook_telegram.py` | Register the Telegram webhook URL |

## Architecture

```
route → service → repository → model
```

```
src/
├── main.py                     # FastAPI app, middlewares, startup validation
├── config/                     # Env vars and database session
├── webhook/                    # Inbound email webhook (Forward Email)
├── telegram/                   # Inbound Telegram webhook
├── parser/                     # Bank email parsers (Bancolombia, Nequi)
├── notificador/                # Outbound Telegram messages and emails
├── modelos/                    # SQLAlchemy models (clientes, pagos, logs)
├── repositorios/               # Database queries
├── servicios/                  # Business logic (payment processing, subscriptions, aliases)
└── dashboard/                  # Jinja2 templates + routes for business and operator views
```

**Payment flow:** Forward Email receives bank confirmation email → POST webhook → FastAPI validates secret, deduplicates by `messageId`, detects bank, runs parser → saves payment record → sends Telegram + email notifications with up to 3 retries → logs each attempt.

## Adding a new bank

1. Create `src/parser/<bank>.py` implementing the `ParserBase` interface
2. Register the sender domain in `src/parser/base.py`
3. Add the parser to the factory in `src/parser/fabrica.py`

## Tests

```bash
pytest
```

## License

MIT
