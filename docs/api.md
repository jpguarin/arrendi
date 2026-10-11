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
| `GET /api/me` | Devuelve el propietario y si completó el alta (`onboarding_complete`). Crea su fila si es la primera vez. `onboarding_complete` es verdadero cuando el propietario tiene al menos un inmueble. El nombre y el correo salen del token solo al crear la fila; después manda lo que el propietario guardó. Si el token no trae nombre se usa el correo, y sin correo responde 400 (`email_required`). |
| `PATCH /api/settings` | Actualiza nombre, tipo de documento (`document_type`: `cc` o `nit`), documento y datos de pago (`name`, `document_number`, `payment_details`). Solo cambian los campos enviados. Desde la etapa 4, también día de envío, recordatorios y copia |
| `GET /api/settings` | Devuelve la configuración |
| `POST /api/onboarding` | Crea el primer inmueble (`property`), sus unidades (`units`, de 1 a 50) y, opcionalmente, el arrendatario y el contrato (`lease`, que señala la unidad con `unit_index`), en una transacción. 409 `onboarding_already_complete` si el propietario ya tiene un inmueble |

## Inmuebles y unidades

| Ruta | Qué hace |
| --- | --- |
| `GET /api/properties` | Lista los inmuebles con sus unidades, y por unidad el contrato activo y su `status`. Hasta la etapa 5 el estado es `vacant` (sin contrato activo) o `up_to_date` (con contrato activo); desde entonces también `overdue` y `partial`, calculados con las cuentas |
| `POST /api/properties` | Crea un inmueble, sin unidades. Responde 201 |
| `PATCH /api/properties/{id}` | Edita un inmueble. Solo cambian los campos enviados; `address` y `city` se borran con `null` |
| `POST /api/properties/{id}/units` | Agrega una unidad. Responde 201 |
| `PATCH /api/units/{id}` | Edita una unidad |

## Contratos

| Ruta | Qué hace |
| --- | --- |
| `POST /api/leases` | Crea el contrato de una unidad. Recibe `tenant` (arrendatario nuevo) o `tenant_id` (uno existente), nunca los dos. 409 `unit_has_active_lease` si la unidad ya tiene contrato activo; 422 `invalid_lease_dates` si la fecha de fin no es posterior a la de inicio |
| `GET /api/leases/{id}` | Devuelve contrato, arrendatario, unidad con su inmueble y el nombre del documento. También sus últimas cuentas, en `recent_bills` (hasta 6, de la más nueva a la más vieja, incluidas las anuladas) |
| `PATCH /api/leases/{id}` | Edita canon, día de pago, fechas, depósito, envío automático y datos del arrendatario (en `tenant`). Solo cambian los campos enviados. También se puede editar un contrato terminado, para corregir el correo del arrendatario si quedó con saldo |
| `POST /api/leases/{id}/end` | Pasa el contrato a terminado. 400 `lease_already_ended` si ya lo estaba |
| `POST /api/leases/{id}/bills` | Genera la cuenta mensual del contrato para el mes en curso (hora de Colombia), sin cuerpo. Responde 201. 400 `lease_not_active` si el contrato está terminado; 409 `bill_already_exists` si ya hay una cuenta no anulada de ese mes |
| `POST /api/leases/{id}/document/upload-url` | Primer paso de la subida. Recibe `filename`, `content_type` y `size`; devuelve el enlace firmado de subida y la ruta del objeto |
| `POST /api/leases/{id}/document` | Segundo paso. Confirma la subida: valida el archivo guardado, lo asocia al contrato y borra el anterior si lo reemplaza |
| `GET /api/leases/{id}/document` | Devuelve un enlace temporal al documento (`url`, `name` y `expires_in`, 5 minutos). 404 `document_not_found` si el contrato no tiene |

## Cuentas de cobro

| Ruta | Qué hace |
| --- | --- |
| `GET /api/bills` | Lista cuentas. Filtros: `unit_id`, `status` (`receivable`, `paid`, `voided`), `from`, `to` |
| `POST /api/bills` | Crea una cuenta manual sobre un contrato activo: `lease_id`, `description`, `amount` y `due_date`. Responde 201. 400 `lease_not_active` si el contrato está terminado |
| `GET /api/bills/{id}` | Devuelve la cuenta con conceptos, saldo (`balance`), unidad, arrendatario y los datos del propietario que muestra el documento. Los pagos llegan en la etapa 5 y las notificaciones en la 4 |
| `GET /api/bills/{id}/pdf` | Devuelve un enlace temporal al PDF (`url`, `name` y `expires_in`, 5 minutos) |
| `POST /api/bills/{id}/send` | Envía o reenvía la cuenta por correo |
| `POST /api/bills/{id}/remind` | Envía un recordatorio manual. 400 si no tiene saldo |
| `POST /api/bills/{id}/void` | Anula la cuenta. 400 `bill_has_payments` si tiene pagos; 400 `bill_already_voided` si ya estaba anulada |

El filtro `receivable` reúne `pending`, `partial` y `overdue`. Sin filtro de estado, las anuladas no se incluyen.

El listado va de la más nueva a la más vieja. `from` y `to` (fechas, inclusive) filtran por el mes al que pertenece la cuenta: el `period` de la mensual y el vencimiento de la manual.

La cuenta mensual y la manual se crean con el PDF ya guardado. Si el almacenamiento falla, responden 503 `storage_unavailable` y no se crea nada: el consecutivo no se gasta.

Hasta la etapa 5 no hay tabla de pagos: una cuenta "tiene pagos" cuando su estado es `partial` o `paid`.

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
- **Subida directa al almacenamiento.** Vercel limita el cuerpo de una petición a una función a 4,5 MB (consultado el 11 de octubre de 2026), así que los archivos no pasan por la API. El flujo, igual para el contrato y, en la etapa 5, para el comprobante del pago:
  1. La web pide a la API un enlace firmado de subida (`.../upload-url`), indicando nombre, tipo y tamaño. La API comprueba que el recurso es del propietario y que el tipo y el tamaño están permitidos, y devuelve el enlace y la ruta del objeto. El enlace sirve para esa ruta y vence en pocas horas.
  2. El navegador envía el archivo directo a Supabase Storage con ese enlace.
  3. La web confirma a la API (`POST .../document`). La API lee del objeto su tamaño real y sus primeros bytes, valida el tipo por contenido, guarda la ruta en la base y borra el archivo anterior. Si no valida, borra el objeto y responde 422.
  Errores: 422 `unsupported_file_type` y 422 `file_too_large` (al pedir el enlace o al confirmar), 400 `document_not_uploaded` (se confirma sin haber subido) y 503 `storage_unavailable`. La confirmación solo acepta una ruta que la API haya entregado para ese mismo contrato; cualquier otra responde 404.
  Un archivo subido y nunca confirmado queda huérfano en el almacenamiento; no se asocia a nada y no se puede abrir desde la API.
