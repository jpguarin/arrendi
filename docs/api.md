# API

La API es FastAPI. Su contrato exacto es el esquema OpenAPI que publica en `/openapi.json`, con documentación interactiva en `/docs`. Este documento describe la intención de cada ruta; si cambias una, actualízalo.

## Generalidades

- **Prefijo:** todas las rutas empiezan por `/api`.
- **Formato:** JSON, salvo la subida de archivos (`multipart/form-data`).
- **Autenticación:** `Authorization: Bearer <token de Supabase>`. La API valida el token y de él obtiene el propietario.
- **Dinero:** enteros, en pesos. **Fechas:** `AAAA-MM-DD`.
- **Nombres:** rutas, parámetros y campos van en inglés, según el vocabulario de `docs/modelo-de-datos.md`.
- **Errores:** `{"detail": "mensaje legible, en español", "code": "stable_code"}`. El mensaje se le muestra al propietario; el código es estable y va en inglés.

| Código HTTP | Cuándo |
| --- | --- |
| 400 | La petición rompe una regla de negocio |
| 401 | Falta el token o no es válido |
| 404 | El recurso no existe o es de otro propietario |
| 409 | Conflicto: por ejemplo, la unidad ya tiene contrato activo |
| 422 | Los datos no pasan la validación |

Un recurso de otro propietario siempre responde 404, nunca 403, para no revelar que existe.

## Propietario y alta

| Ruta | Qué hace |
| --- | --- |
| `GET /api/me` | Devuelve el propietario y si completó el alta (`onboarding_complete`). Crea su fila si es la primera vez. En la etapa 1 `onboarding_complete` es siempre `false`; se calcula desde la etapa 2. |
| `PATCH /api/settings` | Actualiza nombre, documento, datos de pago, día de envío, recordatorios y copia |
| `GET /api/settings` | Devuelve la configuración |
| `POST /api/onboarding` | Crea inmueble, unidades y, opcionalmente, arrendatario y contrato, en una transacción |

## Inmuebles y unidades

| Ruta | Qué hace |
| --- | --- |
| `GET /api/properties` | Lista los inmuebles con sus unidades, y por unidad el contrato activo y su estado (al día, en mora, pago parcial, vacía) |
| `POST /api/properties` | Crea un inmueble |
| `PATCH /api/properties/{id}` | Edita un inmueble |
| `POST /api/properties/{id}/units` | Agrega una unidad |
| `PATCH /api/units/{id}` | Edita una unidad |

## Contratos

| Ruta | Qué hace |
| --- | --- |
| `POST /api/leases` | Crea el arrendatario (o usa uno existente) y el contrato. 409 si la unidad ya tiene contrato activo |
| `GET /api/leases/{id}` | Devuelve contrato, arrendatario, unidad y sus últimas cuentas |
| `PATCH /api/leases/{id}` | Edita canon, día de pago, fechas, depósito, envío automático y datos del arrendatario |
| `POST /api/leases/{id}/end` | Pasa el contrato a terminado |
| `POST /api/leases/{id}/document` | Sube o reemplaza el documento firmado |
| `GET /api/leases/{id}/document` | Devuelve un enlace temporal al documento |

## Cuentas de cobro

| Ruta | Qué hace |
| --- | --- |
| `GET /api/bills` | Lista cuentas. Filtros: `unit_id`, `status` (`receivable`, `paid`, `voided`), `from`, `to` |
| `POST /api/bills` | Crea una cuenta manual sobre un contrato: descripción, valor, vencimiento |
| `GET /api/bills/{id}` | Devuelve la cuenta con conceptos, pagos, saldo y notificaciones |
| `GET /api/bills/{id}/pdf` | Devuelve un enlace temporal al PDF |
| `POST /api/bills/{id}/send` | Envía o reenvía la cuenta por correo |
| `POST /api/bills/{id}/remind` | Envía un recordatorio manual. 400 si no tiene saldo |
| `POST /api/bills/{id}/void` | Anula la cuenta. 400 si tiene pagos |

El filtro `receivable` reúne `pending`, `partial` y `overdue`. Sin filtro de estado, las anuladas no se incluyen.

## Pagos

| Ruta | Qué hace |
| --- | --- |
| `POST /api/bills/{id}/payments` | Registra un pago: valor, fecha, medio, `send_receipt`. Recalcula el estado |
| `POST /api/payments/{id}/proof` | Sube el comprobante del pago |
| `GET /api/payments/{id}/proof` | Devuelve un enlace temporal al comprobante |
| `DELETE /api/payments/{id}` | Elimina un pago registrado por error y recalcula el estado |

## Inicio

| Ruta | Qué hace |
| --- | --- |
| `GET /api/summary?month=AAAA-MM` | Esperado, recaudado y pendiente del mes; unidades en mora; cuentas por cobrar y pagadas; correos rebotados |

## Sistema

Estas rutas no usan el token del propietario.

| Ruta | Quién la llama | Protección |
| --- | --- | --- |
| `GET /api/cron/daily` | El Cron Job de Vercel | Secreto en la cabecera `Authorization` |
| `POST /api/webhooks/email` | El proveedor de correo | Firma del proveedor |
| `GET /api/health` | Monitoreo | Ninguna; no expone datos |

## Subida de archivos

- Tipos permitidos: PDF, JPG y PNG. El tipo real se valida leyendo el contenido, no solo la extensión.
- Tamaño máximo: 10 MB (decisión provisional, ver `docs/decisiones.md`).
- Vercel limita el tamaño del cuerpo de una petición a una función. Verifica el límite vigente antes de implementar la subida; si 10 MB lo supera, la alternativa es que la API entregue un enlace firmado de subida y el navegador envíe el archivo directo al almacenamiento.
