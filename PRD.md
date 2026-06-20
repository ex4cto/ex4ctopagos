# PRD — Bot de Verificación de Pagos Bancarios

**Versión:** 1.0  
**Fecha:** 2026-06-20  
**Estado:** En desarrollo — MVP  

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
[Correo personal del dueño del negocio: Gmail / Outlook]
        ↓ filtro automático configurado por el operador
          (reenvío con etiqueta/regla al correo dedicado)
[Correo dedicado del cliente: negocio-xyz@pagos.dominio.com]
        ↓ Mailgun recibe el email → dispara webhook POST
[FastAPI — endpoint /webhook/email/{cliente_id}]
        ↓ 1. Validación de firma Mailgun (HMAC-SHA256)
        ↓ 2. Verificación de timestamp (máx 5 min)
        ↓ 3. Verificación de token único (anti-replay)
        ↓ 4. Parseo del email → extracción de campos
[Campos extraídos]
        → monto
        → nombre del remitente
        → banco de origen
        → fecha y hora del pago
        ↓ guardado en PostgreSQL (pago + email raw)
[Notificaciones paralelas]
        → Telegram: bot único → grupos/chats configurados del negocio
        → Correo: lista de correos configurados del negocio
        ↓ registro de resultado en logs_notificaciones
[Dashboard negocio] ← consulta PostgreSQL
[Dashboard operador] ← consulta PostgreSQL
```

---

## 5. Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+ + FastAPI |
| Base de datos | PostgreSQL (Railway) |
| ORM | SQLAlchemy + Alembic (migraciones) |
| Validación de datos | Pydantic v2 |
| Inbound email | Mailgun (rutas por cliente) |
| Notificaciones Telegram | Telegram Bot API (httpx directo) |
| Notificaciones correo | SMTP / SendGrid |
| Dashboard | FastAPI + Jinja2 + Bootstrap 5 |
| Hosting | Railway |
| Variables de entorno | python-dotenv + Railway env vars |

---

## 6. Estructura de Módulos

```
src/
├── webhook/
│   ├── rutas.py              # Endpoints FastAPI del webhook
│   └── validador.py          # Validación de firma Mailgun
├── parser/
│   ├── base.py               # Clase base abstracta del parser
│   ├── bancolombia.py        # Parser emails Bancolombia
│   └── nequi.py              # Parser emails Nequi
├── notificador/
│   ├── telegram.py           # Envío de mensajes Telegram
│   └── correo.py             # Envío de correos electrónicos
├── modelos/
│   ├── cliente.py            # Modelo SQLAlchemy Cliente
│   ├── pago.py               # Modelo SQLAlchemy Pago
│   └── log_notificacion.py   # Modelo SQLAlchemy LogNotificacion
├── repositorios/
│   ├── cliente_repo.py       # Queries de clientes
│   ├── pago_repo.py          # Queries de pagos
│   └── log_repo.py           # Queries de logs
├── servicios/
│   ├── procesar_pago.py      # Orquesta: parseo → guardar → notificar
│   └── metricas.py           # Lógica de métricas para dashboards
├── dashboard/
│   ├── rutas_negocio.py      # Rutas del dashboard del negocio
│   ├── rutas_operador.py     # Rutas del dashboard del operador
│   └── templates/            # HTML Jinja2 + Bootstrap
├── config/
│   ├── ajustes.py            # Carga y expone variables de entorno
│   └── base_datos.py         # Sesión y engine de SQLAlchemy
└── main.py                   # Punto de entrada FastAPI
```

---

## 7. Base de Datos

### `clientes`
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID | Identificador único |
| nombre_negocio | VARCHAR | Nombre del negocio |
| correo_dedicado | VARCHAR | Email Mailgun asignado (negocio-xyz@pagos.dominio.com) |
| telegram_chat_ids | JSONB | Lista de chat_ids de Telegram (grupos + empleados) |
| correos_notificacion | JSONB | Lista de correos a notificar |
| token_dashboard | UUID | Token único para acceso al dashboard sin login |
| activo | BOOLEAN | Si el cliente está activo en el sistema |
| fecha_creacion | TIMESTAMP | Fecha de alta |

### `pagos`
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID | Identificador único |
| cliente_id | UUID | FK → clientes |
| monto | NUMERIC | Monto del pago |
| remitente | VARCHAR | Nombre de quien transfirió |
| banco_origen | VARCHAR | Bancolombia / Nequi / etc. |
| fecha_pago | TIMESTAMP | Fecha y hora del pago según el banco |
| fecha_recibido | TIMESTAMP | Fecha en que el sistema lo procesó |
| email_raw | TEXT | Email original completo (para debug) |
| notificado_telegram | BOOLEAN | Si se notificó por Telegram |
| notificado_correo | BOOLEAN | Si se notificó por correo |
| token_idempotencia | VARCHAR | Token único de Mailgun (anti-duplicado) |

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

## 8. Seguridad — Validación del Webhook

Cada request de Mailgun incluye tres campos que deben validarse antes de procesar:

| Campo | Descripción |
|---|---|
| `timestamp` | Unix timestamp del envío |
| `token` | String aleatorio único por request |
| `signature` | HMAC-SHA256 de (timestamp + token) con la Webhook Signing Key |

**Pasos de validación (todos deben pasar):**

1. Calcular `HMAC-SHA256(timestamp + token, MAILGUN_WEBHOOK_SIGNING_KEY)`
2. Comparar con `signature` usando `hmac.compare_digest()` — previene timing attacks
3. Verificar que `timestamp` no tenga más de 5 minutos — previene replay attacks
4. Verificar que el `token` no haya sido procesado antes (guardado en BD) — previene replay exacto
5. Si cualquier paso falla → responder `403 Forbidden`, no procesar

---

## 9. Reintentos y Deduplicación

**Deduplicación:** cada pago tiene un `token_idempotencia` (el campo `token` de Mailgun). Si llega un webhook con el mismo token, se descarta silenciosamente.

**Reintentos de notificación:**
- Máximo 3 intentos por canal (Telegram / correo)
- Intervalo entre intentos: 30 segundos
- Si los 3 intentos fallan → estado `fallido` en `logs_notificaciones`
- El operador puede ver los fallos en su dashboard

---

## 10. Formato de Notificación

### Telegram
```
💳 Pago recibido

Negocio: Tienda El Centro
Monto:   $150.000
De:      Juan Pérez
Vía:     Nequi
Fecha:   20 jun 2026 — 10:32 am
```

### Correo electrónico
- **Asunto:** `Pago recibido — $150.000 de Juan Pérez`
- **Cuerpo:** misma información en formato HTML limpio con colores del negocio (configurable a futuro)

---

## 11. Bancos Soportados (MVP)

| Banco | Estado |
|---|---|
| Bancolombia (transferencia) | MVP |
| Nequi | MVP |
| Otros bancos colombianos | Futuro |

El parser está diseñado con clase base abstracta para agregar nuevos bancos sin modificar el código existente.

---

## 12. Dashboards

### Dashboard del Negocio
- **Acceso:** URL única con token (`/dashboard/{token_dashboard}`) — sin login
- **Contenido:**
  - Total de pagos recibidos: hoy / semana / mes
  - Monto total acumulado: hoy / semana / mes
  - Historial de pagos (tabla paginada): fecha, hora, monto, remitente, banco, canales notificados
  - Estado de últimas notificaciones

### Dashboard del Operador
- **Acceso:** `/operador/login` con contraseña configurada en `.env`
- **Contenido:**
  - Lista de clientes activos y su estado
  - Actividad global: pagos procesados hoy / semana / mes
  - Logs de notificaciones fallidas
  - Últimos pagos procesados en tiempo real

---

## 13. Variables de Entorno (`.env`)

```env
# Mailgun
MAILGUN_API_KEY=
MAILGUN_WEBHOOK_SIGNING_KEY=
MAILGUN_DOMINIO=

# Telegram
TELEGRAM_BOT_TOKEN=

# Base de datos
DATABASE_URL=

# Correo saliente
SMTP_HOST=
SMTP_PUERTO=
SMTP_USUARIO=
SMTP_CLAVE=

# Dashboard operador
OPERADOR_CLAVE=

# Seguridad
WEBHOOK_TOKEN_EXPIRACION_MINUTOS=5
MAX_REINTENTOS_NOTIFICACION=3
INTERVALO_REINTENTO_SEGUNDOS=30
```

---

## 14. Estándares de Código

### Nomenclatura
| Tipo | Convención | Ejemplo |
|---|---|---|
| Variables y funciones | snake_case español | `monto_pago`, `procesar_webhook()` |
| Clases | PascalCase español | `ClientePago`, `NotificadorTelegram` |
| Constantes | UPPER_SNAKE_CASE español | `MAX_REINTENTOS`, `TIEMPO_ESPERA` |
| Archivos/módulos | snake_case español | `procesador_pagos.py` |
| Tablas BD | snake_case español plural | `clientes`, `logs_notificaciones` |

### Reglas generales
- Type hints en todos los parámetros y retornos de funciones
- Modelos Pydantic para datos entrantes (webhook payload, config)
- Sin `Any` salvo justificación documentada
- Funciones de máximo ~25 líneas, una responsabilidad por función
- Sin abreviaciones — nombres descriptivos completos
- Sin código comentado
- Sin números mágicos — todo en constantes o variables de entorno
- Logging estructurado, nunca `print()`
- Excepciones propias tipadas (`class ErrorParseoBanco(Exception)`)
- Nunca capturar y silenciar excepciones

### Arquitectura en capas (estricta)
```
ruta (router) → servicio (service) → repositorio (repository) → modelo (model)
```
- Cero lógica de negocio en rutas
- Cero queries de BD en servicios
- Un archivo por responsabilidad

### Archivos y configuración
- `.env` siempre en `.gitignore` — nunca sube a GitHub
- `requirements.txt` con versiones fijas
- Config por cliente en BD, credenciales globales en `.env`

### Commits

- Commits atómicos: un commit = un cambio lógico completo y autocontenido
- El mensaje describe el QUÉ y el POR QUÉ, no el cómo
- Nunca mezclar refactors, features y fixes en un mismo commit
- Cada commit debe dejar el proyecto en estado funcional

---

## 15. Testing

- Testing con banco y correos reales del operador
- Se crearán correos mock (emails de prueba) que simulen el formato de Bancolombia y Nequi para pruebas unitarias del parser
- El operador mostrará imágenes de correos bancarios reales al inicio del desarrollo para ajustar los parsers

---

## 16. Onboarding de un Cliente Nuevo

El operador realiza estos pasos manualmente:

1. Registrar el cliente en la tabla `clientes` con su configuración
2. Crear ruta en Mailgun para su correo dedicado (`negocio-xyz@pagos.dominio.com`)
3. Dar instrucciones al dueño para configurar el filtro de reenvío en su Gmail/Outlook
4. Dar instrucciones al negocio para agregar el bot de Telegram a su grupo y obtener el `chat_id`
5. Compartir la URL del dashboard al dueño del negocio

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
| 2 | Setup del proyecto: estructura, BD, FastAPI base | Pendiente |
| 3 | Webhook Mailgun: recepción y validación de firma | Pendiente |
| 4 | Parser Bancolombia + Nequi | Pendiente |
| 5 | Notificador Telegram | Pendiente |
| 6 | Notificador correo electrónico | Pendiente |
| 7 | Dashboard del negocio | Pendiente |
| 8 | Pruebas con banco y correos reales | Pendiente |
| 9 | Dashboard del operador | Pendiente |
| 10 | Auditoría de ciberseguridad | Pendiente |
| 11 | Despliegue en Railway (producción) | Pendiente |

---

## 19. Auditoría de Ciberseguridad (Post-MVP)

Se realizará una auditoría completa antes de salir a producción con clientes reales. Cubrirá:

- Penetration testing del webhook endpoint
- Revisión de manejo de secretos y variables de entorno
- Verificación de que no hay datos sensibles expuestos en logs
- Revisión de accesos al dashboard (tokens, login del operador)
- Protección del email raw almacenado
- Headers de seguridad HTTP (CORS, CSP, HSTS)
- Revisión de dependencias con vulnerabilidades conocidas (pip audit)
- Validación de que la verificación HMAC es correcta e irrompible
- Test de replay attacks

---

## 20. Roadmap Futuro (Post-MVP)

- Self-service onboarding para nuevos clientes
- Dashboard del operador con UI completa
- Autenticación con usuario/contraseña para dashboards de negocio
- Soporte para más bancos colombianos (Davivienda, BBVA, BRE)
- Notificaciones por WhatsApp (Meta Business API)
- Alertas de montos inusuales o pagos duplicados
- Dominio propio (`pagos.dominio.com`) para correos dedicados
- API pública para integraciones de terceros
