# PRD — Bot de Verificación de Pagos Bancarios

**Versión:** 2.0  
**Fecha:** 2026-06-21  
**Estado:** MVP completo — en producción  

---

## 1. Contexto y Problema

Negocios colombianos reciben pagos por transferencia bancaria (Bancolombia, Nequi). El correo de confirmación del banco llega únicamente al correo personal del dueño del negocio. Los empleados no tienen visibilidad del pago en tiempo real, lo que genera el siguiente proceso manual:

1. Cliente realiza transferencia
2. Empleado solicita foto del comprobante al cliente o espera confirmación verbal
3. Empleado toma foto con su celular y la envía por WhatsApp al dueño
4. Dueño verifica manualmente en su banco o correo
5. Dueño aprueba verbalmente o por WhatsApp

**Consecuencias:** proceso lento, propenso a errores, dependiente de una sola persona, no escalable y sin trazabilidad.

---

## 2. Solución

Sistema SaaS que intercepta automáticamente el correo de confirmación bancaria, extrae la información del pago y notifica en tiempo real a los canales configurados del negocio (Telegram y/o correo electrónico), eliminando la intervención manual del dueño.

El sistema está diseñado para ser completamente estandarizado: agregar un nuevo negocio cliente solo requiere registrar su configuración en la base de datos y darle instrucciones para configurar el reenvío automático en su correo.

---

## 3. Actores del Sistema

| Actor | Descripción |
|---|---|
| **Operador** | Administrador del SaaS (dueño del bot). Configura y mantiene el sistema. Accede al dashboard de operador. |
| **Negocio cliente** | Dueño del negocio que recibe pagos. Configura el reenvío automático de su correo bancario. Accede a su dashboard. |
| **Empleado/Admin del negocio** | Recibe notificaciones de pagos vía Telegram y/o correo electrónico. |

---

## 4. Flujo de Datos Completo

```
[Banco: Bancolombia / Nequi]
        ↓ email de confirmación de pago
[Correo personal del dueño del negocio: Gmail]
        ↓ filtro automático de Gmail
          (reenvío al correo dedicado del cliente)
[Correo dedicado del cliente: negocioX@ex4cto.co]
        ↓ Forward Email recibe el email → dispara webhook POST
[FastAPI — endpoint POST /webhook/email?secret=...&correo=negocioX@ex4cto.co]
        ↓ 1. Validación del webhook secret
        ↓ 2. Verificación de messageId único (anti-replay)
        ↓ 3. Detección del banco por dominio del remitente
        ↓ 4. Parseo del email → extracción de campos
[Campos extraídos]
        → monto
        → nombre del remitente
        → banco de origen
        → fecha y hora del pago
        ↓ guardado en PostgreSQL
[Notificaciones en background (BackgroundTasks)]
        → Telegram: bot único → chat_ids configurados del negocio
        → Correo: Forward Email REST API → correos configurados del negocio
        ↓ registro de resultado en logs_notificaciones
[Dashboard negocio] ← /dashboard/{token_dashboard}
[Dashboard operador] ← /operador/dashboard
```

---

## 5. Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.13 + FastAPI |
| Base de datos | PostgreSQL (Railway) |
| ORM | SQLAlchemy 2.0 + Alembic |
| Validación de datos | Pydantic v2 |
| Inbound email | Forward Email (alias por cliente en ex4cto.co) |
| Notificaciones Telegram | Telegram Bot API (httpx) |
| Notificaciones correo | Forward Email REST API (httpx, puerto 443) |
| Dashboard | FastAPI + Jinja2 + Bootstrap 5.3 |
| Sesiones operador | Starlette SessionMiddleware (cookies firmadas) |
| Hosting | Railway |
| Variables de entorno | Pydantic Settings + Railway env vars |

---

## 6. Estructura de Módulos

```
src/
├── webhook/
│   ├── rutas.py              # Endpoint POST /webhook/email
│   ├── validador.py          # Validación del webhook secret
│   └── schemas.py            # PayloadEmail, PagoExtraido (Pydantic)
├── parser/
│   ├── base.py               # Clase base abstracta + detección de banco
│   ├── bancolombia.py        # Parser emails Bancolombia
│   ├── nequi.py              # Parser emails Nequi
│   └── fabrica.py            # Fábrica de parsers por banco
├── notificador/
│   ├── telegram.py           # Envío de mensajes Telegram (HTML parse mode)
│   └── correo.py             # Envío de correos via Forward Email REST API
├── modelos/
│   ├── cliente.py            # Modelo SQLAlchemy Cliente
│   ├── pago.py               # Modelo SQLAlchemy Pago
│   └── log_notificacion.py   # Modelo SQLAlchemy LogNotificacion
├── repositorios/
│   ├── cliente_repo.py       # Queries de clientes
│   ├── pago_repo.py          # Queries de pagos + métricas
│   └── log_repo.py           # Queries de logs
├── servicios/
│   ├── procesar_pago.py      # Orquesta: parseo → guardar → notificar
│   └── reintentos.py         # Lógica de reintentos con backoff
├── dashboard/
│   ├── rutas_negocio.py      # Dashboard por token UUID (sin login)
│   ├── rutas_operador.py     # Dashboard operador (login + rate limiting)
│   ├── jinja.py              # Templates compartidos + filtros formato_peso/fecha
│   └── templates/            # HTML Jinja2 + Bootstrap 5.3
├── config/
│   ├── ajustes.py            # Pydantic Settings — variables de entorno
│   └── base_datos.py         # Sesión y engine SQLAlchemy
└── main.py                   # FastAPI app + middlewares
```

---

## 7. Base de Datos

### `clientes`
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID | Identificador único |
| nombre_negocio | VARCHAR | Nombre del negocio |
| correo_dedicado | VARCHAR | Alias Forward Email asignado (negocioX@ex4cto.co) |
| telegram_chat_ids | JSONB | Lista de chat_ids de Telegram |
| correos_notificacion | JSONB | Lista de correos a notificar |
| token_dashboard | UUID | Token único para acceso al dashboard |
| activo | BOOLEAN | Si el cliente está activo |
| fecha_creacion | TIMESTAMP | Fecha de alta |

### `pagos`
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID | Identificador único |
| cliente_id | UUID | FK → clientes |
| monto | NUMERIC | Monto del pago |
| remitente | VARCHAR | Nombre de quien transfirió |
| banco_origen | VARCHAR | Bancolombia / Nequi |
| fecha_pago | TIMESTAMP | Fecha y hora del pago según el banco |
| fecha_recibido | TIMESTAMP | Fecha en que el sistema lo procesó |
| email_raw | TEXT | Email original completo (para debug) |
| notificado_telegram | BOOLEAN | Si se notificó por Telegram |
| notificado_correo | BOOLEAN | Si se notificó por correo |
| token_idempotencia | VARCHAR | messageId de Forward Email (anti-duplicado) |

### `logs_notificaciones`
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID | Identificador único |
| pago_id | UUID | FK → pagos |
| canal | VARCHAR | 'telegram' / 'correo' |
| destinatario | VARCHAR | chat_id o email destino |
| estado | VARCHAR | 'exitoso' / 'fallido' |
| intentos | INTEGER | Número de intentos realizados |
| error | TEXT | Mensaje de error si falló |
| fecha | TIMESTAMP | Fecha del intento |

---

## 8. Seguridad

| Mecanismo | Implementación |
|---|---|
| Webhook secret | Query param `?secret=` o header `X-Webhook-Secret`, comparado con `hmac.compare_digest` |
| Anti-replay | `messageId` del email guardado como `token_idempotencia` — duplicados descartados |
| Sesión operador | Starlette SessionMiddleware, `same_site=strict`, `https_only` en producción, `max_age=3600` |
| Rate limiting login | 5 intentos por IP cada 5 minutos |
| XSS en email/Telegram | `html.escape()` en todos los campos de usuario antes de interpolar |
| Detección de banco | Comparación exacta de dominio del remitente (no subcadena) |
| Validación arranque | Falla si `SECRET_KEY` es el valor default en producción |
| Security headers | X-Frame-Options: DENY, X-Content-Type-Options: nosniff, HSTS, Referrer-Policy |
| Docs API | `/docs` solo disponible en ambiente `desarrollo` |
| Logs sensibles | Montos y nombres de remitentes solo en nivel DEBUG |

---

## 9. Reintentos y Deduplicación

**Deduplicación:** el `messageId` del email de Forward Email se guarda como `token_idempotencia`. Si llega un webhook con el mismo ID, se descarta silenciosamente.

**Reintentos de notificación:**
- Máximo 3 intentos por canal (Telegram / correo)
- Intervalo entre intentos: 30 segundos
- Las notificaciones corren en `BackgroundTasks` — el webhook responde 200 OK inmediatamente

---

## 10. Formato de Notificación

### Telegram
```
Nuevo pago recibido

Negocio: Tienda El Centro
Monto:   $150.000
De:      Juan Pérez
Banco:   Bancolombia
Fecha:   20/06/2026 10:32
```

### Correo electrónico
- **Remitente:** `notificaciones@ex4cto.co` (via Forward Email REST API)
- **Asunto:** `Pago recibido — $150.000 via Bancolombia`
- **Cuerpo:** tarjeta HTML con la misma información

---

## 11. Bancos Soportados

| Banco | Estado | Dominio del remitente |
|---|---|---|
| Bancolombia | ✅ Activo | `an.notificacionesbancolombia.com` |
| Nequi | ✅ Activo | `nequi.com.co` |
| Otros bancos colombianos | Roadmap | — |

El parser usa clase base abstracta — agregar un banco nuevo solo requiere un archivo nuevo en `src/parser/`.

---

## 12. Dashboards

### Dashboard del Negocio
- **Acceso:** URL única `/dashboard/{token_dashboard}` — sin login
- **Contenido:** métricas hoy/semana/mes + historial de pagos con estado de notificaciones

### Dashboard del Operador
- **Acceso:** `/operador/login` con `OPERADOR_CLAVE` del `.env`
- **Contenido:** métricas globales, tabla de clientes con métricas individuales, últimos 50 pagos de todos los clientes

---

## 13. Variables de Entorno (`.env`)

```env
# Webhook
WEBHOOK_SECRET=<string aleatorio 40+ caracteres>

# Telegram
TELEGRAM_BOT_TOKEN=<token del BotFather>

# Base de datos
DATABASE_URL=postgresql://...

# Correo saliente (Forward Email REST API)
CORREO_REMITENTE=notificaciones@ex4cto.co
CORREO_CLAVE=<clave API de Forward Email>

# Dashboard operador
OPERADOR_CLAVE=<string aleatorio 40+ caracteres>
SECRET_KEY=<string aleatorio 64+ caracteres>

# App
AMBIENTE=produccion
APP_URL=https://ex4ctopagos-production.up.railway.app
```

---

## 14. Estándares de Código

### Nomenclatura
| Tipo | Convención | Ejemplo |
|---|---|---|
| Variables y funciones | snake_case español | `monto_pago`, `procesar_webhook()` |
| Clases | PascalCase español | `ParserBancolombia`, `ErrorParseoBanco` |
| Constantes | UPPER_SNAKE_CASE | `BANCO_BANCOLOMBIA`, `_MAX_INTENTOS_LOGIN` |
| Archivos/módulos | snake_case español | `procesar_pago.py` |
| Tablas BD | snake_case español plural | `clientes`, `logs_notificaciones` |

### Reglas generales
- Type hints completos en todos los parámetros y retornos
- Sin `Any` sin justificación documentada
- Funciones máximo ~25 líneas, una responsabilidad por función
- Sin hardcoding — constantes o variables de entorno
- Sin comentarios que expliquen el QUÉ (solo el POR QUÉ no obvio)
- Logging estructurado, nunca `print()` en código de aplicación
- Excepciones propias tipadas

### Arquitectura en capas
```
ruta → servicio → repositorio → modelo
```

---

## 15. Testing

- 20 tests unitarios pasando (`pytest`)
- Parsers probados con texto real de emails de Bancolombia y Nequi
- Pruebas de integración manuales end-to-end con pagos reales

---

## 16. Onboarding de un Cliente Nuevo

Ver **GUIA_ONBOARDING.md** para el paso a paso detallado.

**Resumen de pasos:**
1. Crear alias en Forward Email para el cliente
2. Registrar el cliente en la BD con `scripts/insertar_cliente.py`
3. Configurar filtro de Gmail en el correo del dueño del negocio
4. Agregar el bot de Telegram al grupo del negocio y obtener el `chat_id`
5. Actualizar el cliente en BD con el `chat_id` real
6. Compartir la URL del dashboard al dueño del negocio

---

## 17. Privacidad y Retención de Datos

- La información de pagos es confidencial por cliente — ningún cliente ve datos de otro
- El email raw se guarda para debug del operador únicamente
- Los datos se eliminan a petición del cliente
- El token del dashboard es único e irrepetible por cliente

---

## 18. Hitos de Desarrollo

| Hito | Descripción | Estado |
|---|---|---|
| 1 | PRD completo y aprobado | ✅ Completo |
| 2 | Setup del proyecto: estructura, BD, FastAPI base | ✅ Completo |
| 3 | Webhook Forward Email: recepción y validación | ✅ Completo |
| 4 | Parser Bancolombia + Nequi | ✅ Completo |
| 5 | Notificador Telegram | ✅ Completo |
| 6 | Notificador correo (Forward Email REST API) | ✅ Completo |
| 7 | Dashboard del negocio | ✅ Completo |
| 8 | Pruebas end-to-end con pagos reales | ✅ Completo |
| 9 | Dashboard del operador | ✅ Completo |
| 10 | Auditoría de ciberseguridad | ✅ Completo |
| 11 | Despliegue en Railway (producción) | ✅ Completo |

---

## 19. Auditoría de Ciberseguridad

Completada. Vulnerabilidades corregidas:
- XSS en email y Telegram (html.escape)
- Rate limiting en login del operador
- Flags seguros en cookies de sesión (https_only, same_site=strict, max_age)
- Security headers HTTP (HSTS, X-Frame-Options, nosniff, Referrer-Policy)
- Comparación exacta de dominio bancario (no subcadena)
- Validación de arranque para SECRET_KEY en producción
- Webhook secret aceptado también por header (no solo query param)

Limitación conocida: Forward Email no soporta headers personalizados en webhooks, por lo que el secret viaja en la URL. Riesgo mitigado por acceso restringido a logs de Railway y alta entropía del secret.

---

## 20. Roadmap Futuro

- Soporte para más bancos (Davivienda, BBVA)
- Notificaciones por WhatsApp (Meta Business API)
- Self-service onboarding para nuevos clientes
- Autenticación con usuario/contraseña para dashboards de negocio
- Alertas de montos inusuales o pagos duplicados
- API pública para integraciones de terceros
