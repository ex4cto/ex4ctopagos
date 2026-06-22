# Estándares del proyecto

## Nomenclatura

- Variables y funciones: snake_case español (`monto_pago`, `procesar_webhook`)
- Clases: PascalCase español (`ClientePago`, `NotificadorTelegram`)
- Constantes: UPPER_SNAKE_CASE español (`MAX_REINTENTOS`)
- Archivos: snake_case español (`procesador_pagos.py`)
- Tablas BD: snake_case español plural (`clientes`, `logs_notificaciones`)

## Código

- Type hints en todos los parámetros y retornos
- Pydantic v2 para datos entrantes
- Sin `Any` salvo justificación explícita
- Funciones de máximo ~25 líneas, una sola responsabilidad
- Nombres descriptivos completos, sin abreviaciones
- Sin código comentado
- Sin números mágicos
- Logging estructurado, nunca `print()`
- Excepciones propias tipadas
- Nunca capturar y silenciar excepciones

## Arquitectura en capas (estricta)

```
ruta → servicio → repositorio → modelo
```

- Cero lógica de negocio en rutas
- Cero queries en servicios

## Configuración

- `.env` para credenciales globales — nunca a GitHub
- Config de clientes en tabla BD
- `requirements.txt` con versiones fijas

## Commits

Un commit = un cambio lógico completo y autocontenido. Nunca mezclar features, fixes y refactors en el mismo commit. Cada commit debe dejar el proyecto en estado funcional y los tests en verde.

Formato del mensaje:
```
tipo: descripción corta en español

Cuerpo opcional explicando el POR QUÉ si no es obvio.
```

Tipos válidos: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `security`.
