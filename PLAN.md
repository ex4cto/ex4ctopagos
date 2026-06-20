# Plan de Ejecución — Bot de Verificación de Pagos

**Versión:** 1.0  
**Fecha:** 2026-06-20  
**Referencia:** PRD.md  

Convención de estado: `[ ]` pendiente · `[→]` en progreso · `[x]` completo

---

## Fase 1 — Fundamentos del Proyecto
*Objetivo: proyecto corriendo localmente con BD conectada y webhook recibiendo requests.*

### Parte 1.1 — Estructura y entorno
- [x] Crear estructura de carpetas según PRD sección 6
- [x] Crear y activar entorno virtual Python 3.13 (`venv`)
- [x] Crear `requirements.txt` con versiones fijas
- [x] Crear `.env` con todas las variables definidas en PRD sección 13 (valores vacíos)
- [x] Crear `.gitignore`
- [ ] Crear `README.md` mínimo con instrucciones de setup

### Parte 1.2 — Configuración global

- [x] Crear `src/config/ajustes.py` — Pydantic BaseSettings, instancia global `ajustes`
- [x] Crear `src/config/base_datos.py` — Engine, SesionLocal, obtener_sesion, Base

### Parte 1.3 — Modelos de base de datos
- [x] Crear `src/modelos/cliente.py` — tabla `clientes`
- [x] Crear `src/modelos/pago.py` — tabla `pagos`
- [x] Crear `src/modelos/log_notificacion.py` — tabla `logs_notificaciones`
- [x] Inicializar Alembic y configurar `alembic/env.py`
- [ ] Generar primera migración con las 3 tablas
- [ ] Aplicar migración y verificar tablas en PostgreSQL

### Parte 1.4 — Repositorios

- [x] Crear `src/repositorios/cliente_repo.py`
- [x] Crear `src/repositorios/pago_repo.py`
- [x] Crear `src/repositorios/log_repo.py`
  - `listar_fallos_recientes() -> list[LogNotificacion]`

### Parte 1.5 — FastAPI base y punto de entrada

- [x] Crear `src/main.py` — FastAPI con título, versión, docs solo en desarrollo, endpoint `/salud`
- [x] Verificar que importa sin errores (`FastAPI OK`)

---

## Fase 2 — Recepción y Validación del Webhook
*Objetivo: recibir emails de Mailgun, validar firma y extraer payload correctamente.*

### Parte 2.1 — Validador de firma Mailgun
- [ ] Crear `src/webhook/validador.py`:
  - Función `validar_firma_mailgun(timestamp: str, token: str, signature: str) -> bool`
  - HMAC-SHA256 de `(timestamp + token)` con `MAILGUN_WEBHOOK_SIGNING_KEY`
  - Comparación con `hmac.compare_digest()`
  - Verificación de timestamp (máx `WEBHOOK_TOKEN_EXPIRACION_MINUTOS` minutos)
  - Verificación de token no usado antes (consulta `pago_repo.existe_token()`)
- [ ] Crear excepción propia `ErrorFirmaInvalida(Exception)`
- [ ] Escribir tests unitarios del validador con firmas correctas e incorrectas

### Parte 2.2 — Schemas de entrada del webhook
- [ ] Crear `src/webhook/schemas.py`:
  - Modelo Pydantic `PayloadMailgun` con todos los campos que envía Mailgun
  - Campos: `timestamp`, `token`, `signature`, `sender`, `recipient`, `subject`, `body_html`, `body_plain`
  - Modelo `PagoExtraido` con: `monto`, `remitente`, `banco_origen`, `fecha_pago`

### Parte 2.3 — Endpoint del webhook
- [ ] Crear `src/webhook/rutas.py`:
  - `POST /webhook/email` — recibe Form data de Mailgun
  - Llama al validador → si falla retorna `403`
  - Identifica el cliente por `recipient` (correo dedicado) → si no existe retorna `200` silencioso
  - Pasa el payload al servicio `procesar_pago`
  - Retorna `200` siempre que el request sea válido (Mailgun no reintenta en 2xx)
- [ ] Configurar Mailgun para apuntar webhook a este endpoint
- [ ] Probar con un request manual (Postman/curl) con firma válida

---

## Fase 3 — Parseo de Emails Bancarios
*Objetivo: extraer monto, remitente, fecha y banco de correos de Bancolombia y Nequi.*

### Parte 3.1 — Base del parser
- [ ] Crear `src/parser/base.py`:
  - Clase abstracta `ParserBanco` con método abstracto:
    `def parsear(self, html: str, texto: str) -> PagoExtraido`
  - Función `detectar_banco(remitente_email: str) -> str | None`
    - Detecta por dominio del remitente (`@bancolombia.com.co`, `@nequi.com.co`, etc.)
  - Función `obtener_parser(banco: str) -> ParserBanco`
    - Retorna el parser correcto según el banco detectado

### Parte 3.2 — Parser Bancolombia
- [ ] Revisar imágenes reales de correos Bancolombia (el operador las provee)
- [ ] Crear `src/parser/bancolombia.py`:
  - Clase `ParserBancolombia(ParserBanco)`
  - Extraer `monto` — identificar el patrón del campo en el HTML/texto
  - Extraer `remitente` — nombre de quien transfirió
  - Extraer `fecha_pago` y `hora_pago` — parsear al formato datetime
  - Manejar variaciones de formato si existen
- [ ] Tests unitarios con HTML de ejemplo del correo real

### Parte 3.3 — Parser Nequi
- [ ] Revisar imágenes reales de correos Nequi (el operador las provee)
- [ ] Crear `src/parser/nequi.py`:
  - Clase `ParserNequi(ParserBanco)`
  - Misma extracción: monto, remitente, fecha_pago
- [ ] Tests unitarios con HTML de ejemplo del correo real

### Parte 3.4 — Servicio orquestador
- [ ] Crear `src/servicios/procesar_pago.py`:
  - Función `procesar_pago(payload: PayloadMailgun, cliente: Cliente, sesion: Session) -> None`
  - Paso 1: detectar banco y seleccionar parser
  - Paso 2: parsear email → obtener `PagoExtraido`
  - Paso 3: guardar pago en BD con `token_idempotencia`
  - Paso 4: lanzar notificaciones en paralelo (Telegram + correo)
  - Paso 5: actualizar estado de notificaciones en BD

---

## Fase 4 — Notificaciones
*Objetivo: enviar notificaciones a Telegram y correo con reintentos.*

### Parte 4.1 — Notificador Telegram
- [ ] Crear bot en Telegram con BotFather → guardar token en `.env`
- [ ] Crear `src/notificador/telegram.py`:
  - Función `formatear_mensaje(pago: Pago, nombre_negocio: str) -> str`
    - Genera el mensaje con el formato definido en PRD sección 10
  - Función `enviar_mensaje(chat_id: str, mensaje: str) -> bool`
    - POST a `api.telegram.org/bot{TOKEN}/sendMessage` con `httpx`
    - Retorna `True` si exitoso
  - Función `notificar_todos(chat_ids: list[str], pago: Pago, nombre_negocio: str) -> dict`
    - Itera sobre todos los chat_ids del cliente
    - Aplica lógica de reintentos (`MAX_REINTENTOS_NOTIFICACION`)
    - Retorna resultado por cada chat_id
- [ ] Crear excepción propia `ErrorNotificacionTelegram(Exception)`

### Parte 4.2 — Notificador correo
- [ ] Crear `src/notificador/correo.py`:
  - Función `formatear_asunto(pago: Pago) -> str`
  - Función `formatear_cuerpo_html(pago: Pago, nombre_negocio: str) -> str`
    - Template HTML limpio y profesional con Bootstrap inline
  - Función `enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> bool`
    - Conexión SMTP con credenciales de `.env`
    - Retorna `True` si exitoso
  - Función `notificar_todos(correos: list[str], pago: Pago, nombre_negocio: str) -> dict`
    - Itera sobre todos los correos del cliente
    - Aplica lógica de reintentos
    - Retorna resultado por cada correo
- [ ] Crear excepción propia `ErrorNotificacionCorreo(Exception)`

### Parte 4.3 — Lógica de reintentos
- [ ] Crear `src/servicios/reintentos.py`:
  - Función genérica `ejecutar_con_reintentos(funcion, max_intentos: int, intervalo_segundos: int) -> bool`
  - Registra cada intento en `logs_notificaciones`
  - Maneja excepciones sin propagar al caller

---

## Fase 5 — Dashboard del Negocio
*Objetivo: página web accesible por token donde el negocio ve sus métricas.*

### Parte 5.1 — Servicio de métricas
- [ ] Crear `src/servicios/metricas.py`:
  - Función `metricas_negocio(cliente_id: UUID, sesion: Session) -> MetricasNegocio`
    - Total pagos y monto: hoy, semana, mes
    - Historial de pagos paginado
    - Estado de últimas notificaciones

### Parte 5.2 — Rutas del dashboard
- [ ] Crear `src/dashboard/rutas_negocio.py`:
  - `GET /dashboard/{token}` → valida token, carga cliente, renderiza template
  - `GET /dashboard/{token}/pagos` → endpoint JSON para tabla paginada (opcional AJAX)
- [ ] Crear sistema de validación de token:
  - Si token no existe → 404 con página de error amigable

### Parte 5.3 — Templates y estilos
- [ ] Crear `src/dashboard/templates/base.html`:
  - Bootstrap 5 CDN
  - Navbar con nombre del negocio
  - Estructura base de bloques Jinja2
- [ ] Crear `src/dashboard/templates/negocio/inicio.html`:
  - Tarjetas de métricas: pagos hoy / semana / mes y montos
  - Tabla historial: fecha, hora, monto, remitente, banco, estado notificación
  - Paginación
- [ ] Crear `src/dashboard/templates/error.html`:
  - Página de error genérica para token inválido o error inesperado

---

## Fase 6 — Dashboard del Operador
*Objetivo: vista global del sistema para el operador con login simple.*

### Parte 6.1 — Autenticación del operador
- [ ] Crear `src/dashboard/autenticacion.py`:
  - Función `verificar_clave_operador(clave: str) -> bool`
    - Compara con `OPERADOR_CLAVE` de `.env`
  - Dependency de FastAPI `operador_autenticado` que valida sesión o retorna 401
  - Sesión simple con cookie firmada (no JWT complejo — MVP)

### Parte 6.2 — Rutas del operador
- [ ] Crear `src/dashboard/rutas_operador.py`:
  - `GET /operador/login` → formulario de login
  - `POST /operador/login` → valida clave, crea cookie de sesión
  - `GET /operador` → dashboard principal (requiere autenticación)
  - `GET /operador/clientes` → lista de clientes activos
  - `GET /operador/logs` → logs de notificaciones fallidas recientes
  - `POST /operador/logout` → destruye sesión

### Parte 6.3 — Templates del operador
- [ ] Crear `src/dashboard/templates/operador/login.html`
- [ ] Crear `src/dashboard/templates/operador/inicio.html`:
  - Resumen global: pagos procesados hoy / semana / mes
  - Lista de clientes activos con su último pago
  - Alertas de notificaciones fallidas
- [ ] Crear `src/dashboard/templates/operador/logs.html`:
  - Tabla de logs fallidos: cliente, canal, destinatario, error, fecha, intentos

---

## Fase 7 — Pruebas con Banco Real
*Objetivo: validar el flujo completo end-to-end con transacciones reales.*

### Parte 7.1 — Setup de pruebas
- [ ] Configurar un cliente de prueba en BD con los datos del operador
- [ ] Crear correo dedicado en Mailgun para pruebas
- [ ] Configurar filtro de reenvío en Gmail del operador hacia Mailgun
- [ ] Crear grupo de Telegram de prueba y agregar el bot → obtener `chat_id`

### Parte 7.2 — Ejecución de pruebas
- [ ] Realizar transferencia de prueba vía Nequi
- [ ] Verificar que el email llega al correo dedicado de Mailgun
- [ ] Verificar que Mailgun dispara el webhook
- [ ] Verificar que el parser extrae los campos correctamente
- [ ] Verificar notificación en Telegram
- [ ] Verificar notificación por correo
- [ ] Verificar que el pago aparece en el dashboard del negocio
- [ ] Realizar transferencia de prueba vía Bancolombia y repetir verificaciones
- [ ] Probar envío duplicado del mismo email → verificar que no se notifica dos veces

### Parte 7.3 — Ajustes post-prueba
- [ ] Corregir parsers si los campos no se extraen correctamente
- [ ] Ajustar formato de notificaciones si es necesario
- [ ] Documentar cualquier variación en el formato del correo bancario

---

## Fase 8 — Auditoría de Ciberseguridad
*Objetivo: validar que el sistema es seguro antes de salir a producción con clientes reales.*

### Parte 8.1 — Revisión de código
- [ ] Auditar endpoint webhook: ¿qué pasa con inputs malformados?
- [ ] Verificar que la validación HMAC es correcta e irrompible
- [ ] Revisar que no hay datos sensibles en logs
- [ ] Revisar que `.env` nunca aparece en código ni en git history
- [ ] Ejecutar `pip audit` sobre `requirements.txt`

### Parte 8.2 — Pruebas de seguridad
- [ ] Test de request con firma inválida → debe retornar 403
- [ ] Test de replay attack (mismo token dos veces) → debe ignorar el segundo
- [ ] Test de timestamp expirado → debe retornar 403
- [ ] Test de SQL injection en campos del email parseado
- [ ] Test de acceso al dashboard con token inválido → debe retornar 404
- [ ] Test de acceso al dashboard del operador sin login → debe retornar 401

### Parte 8.3 — Headers y configuración de seguridad
- [ ] Agregar headers HTTP de seguridad (CSP, X-Content-Type-Options, X-Frame-Options)
- [ ] Verificar que HTTPS está forzado en Railway
- [ ] Revisar configuración de CORS (solo orígenes necesarios)

---

## Fase 9 — Despliegue en Railway
*Objetivo: sistema corriendo en producción, estable y monitoreable.*

### Parte 9.1 — Preparación
- [ ] Crear `Procfile` o configuración de Railway para `uvicorn`
- [ ] Verificar que todas las variables de entorno están en Railway (no en código)
- [ ] Crear `runtime.txt` con versión de Python
- [ ] Verificar que Alembic corre migraciones al desplegar

### Parte 9.2 — Despliegue
- [ ] Crear proyecto en Railway
- [ ] Conectar repositorio de GitHub
- [ ] Agregar PostgreSQL como servicio de Railway
- [ ] Configurar todas las variables de entorno en Railway dashboard
- [ ] Primer despliegue y verificación del endpoint `/salud`
- [ ] Correr migraciones de Alembic en producción

### Parte 9.3 — Verificación post-despliegue
- [ ] Repetir prueba end-to-end en producción con datos reales
- [ ] Verificar que Mailgun apunta al dominio de Railway
- [ ] Verificar dashboard accesible vía URL de Railway
- [ ] Verificar logs de Railway sin errores

---

## Resumen de Fases

| Fase | Descripción | Hito PRD |
|---|---|---|
| 1 | Fundamentos: estructura, BD, FastAPI base | Hito 2 |
| 2 | Webhook Mailgun: recepción y validación | Hito 3 |
| 3 | Parser de emails bancarios | Hito 4 |
| 4 | Notificadores Telegram y correo | Hitos 5 y 6 |
| 5 | Dashboard del negocio | Hito 7 |
| 6 | Dashboard del operador | Hito 9 |
| 7 | Pruebas con banco real | Hito 8 |
| 8 | Auditoría de ciberseguridad | Hito 10 |
| 9 | Despliegue en Railway | Hito 11 |
