# API

La API es FastAPI. Su contrato exacto es el esquema OpenAPI que publica en `/openapi.json`, con documentación interactiva en `/docs`. Este documento describe la intención de cada ruta; si cambias una, actualízalo.

## Generalidades

- **Prefijo:** todas las rutas empiezan por `/api`.
- **Formato:** JSON, salvo la subida de archivos (`multipart/form-data`).
- **Autenticación:** `Authorization: Bearer <token de Supabase>`. La API valida el token y de él obtiene el propietario.
- **Dinero:** enteros, en pesos. **Fechas:** `AAAA-MM-DD`.
- **Errores:** `{"detalle": "mensaje legible", "codigo": "codigo_estable"}`.

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
| `GET /api/yo` | Devuelve el propietario y si completó el alta. Crea su fila si es la primera vez. |
| `PATCH /api/configuracion` | Actualiza nombre, documento, datos de pago, día de envío, recordatorios y copia |
| `GET /api/configuracion` | Devuelve la configuración |
| `POST /api/alta` | Crea inmueble, unidades y, opcionalmente, arrendatario y contrato, en una transacción |

## Inmuebles y unidades

| Ruta | Qué hace |
| --- | --- |
| `GET /api/inmuebles` | Lista los inmuebles con sus unidades, y por unidad el contrato activo y su estado (al día, en mora, pago parcial, vacía) |
| `POST /api/inmuebles` | Crea un inmueble |
| `PATCH /api/inmuebles/{id}` | Edita un inmueble |
| `POST /api/inmuebles/{id}/unidades` | Agrega una unidad |
| `PATCH /api/unidades/{id}` | Edita una unidad |

## Contratos

| Ruta | Qué hace |
| --- | --- |
| `POST /api/contratos` | Crea el arrendatario (o usa uno existente) y el contrato. 409 si la unidad ya tiene contrato activo |
| `GET /api/contratos/{id}` | Devuelve contrato, arrendatario, unidad y sus últimas cuentas |
| `PATCH /api/contratos/{id}` | Edita canon, día de pago, fechas, depósito, envío automático y datos del arrendatario |
| `POST /api/contratos/{id}/terminar` | Pasa el contrato a terminado |
| `POST /api/contratos/{id}/documento` | Sube o reemplaza el documento firmado |
| `GET /api/contratos/{id}/documento` | Devuelve un enlace temporal al documento |

## Cuentas de cobro

| Ruta | Qué hace |
| --- | --- |
| `GET /api/cuentas` | Lista cuentas. Filtros: `unidad_id`, `estado` (`por_cobrar`, `pagadas`, `anuladas`), `desde`, `hasta` |
| `POST /api/cuentas` | Crea una cuenta manual sobre un contrato: descripción, valor, vencimiento |
| `GET /api/cuentas/{id}` | Devuelve la cuenta con conceptos, pagos, saldo y notificaciones |
| `GET /api/cuentas/{id}/pdf` | Devuelve un enlace temporal al PDF |
| `POST /api/cuentas/{id}/enviar` | Envía o reenvía la cuenta por correo |
| `POST /api/cuentas/{id}/recordar` | Envía un recordatorio manual. 400 si no tiene saldo |
| `POST /api/cuentas/{id}/anular` | Anula la cuenta. 400 si tiene pagos |

El filtro `por_cobrar` reúne `pendiente`, `parcial` y `vencida`. Sin filtro de estado, las anuladas no se incluyen.

## Pagos

| Ruta | Qué hace |
| --- | --- |
| `POST /api/cuentas/{id}/pagos` | Registra un pago: valor, fecha, medio, `enviar_recibo`. Recalcula el estado |
| `POST /api/pagos/{id}/comprobante` | Sube el comprobante del pago |
| `GET /api/pagos/{id}/comprobante` | Devuelve un enlace temporal al comprobante |
| `DELETE /api/pagos/{id}` | Elimina un pago registrado por error y recalcula el estado |

## Inicio

| Ruta | Qué hace |
| --- | --- |
| `GET /api/resumen?mes=AAAA-MM` | Esperado, recaudado y pendiente del mes; unidades en mora; cuentas por cobrar y pagadas; correos rebotados |

## Sistema

Estas rutas no usan el token del propietario.

| Ruta | Quién la llama | Protección |
| --- | --- | --- |
| `GET /api/cron/diario` | El Cron Job de Vercel | Secreto en la cabecera `Authorization` |
| `POST /api/webhooks/correo` | El proveedor de correo | Firma del proveedor |
| `GET /api/salud` | Monitoreo | Ninguna; no expone datos |

## Subida de archivos

- Tipos permitidos: PDF, JPG y PNG. El tipo real se valida leyendo el contenido, no solo la extensión.
- Tamaño máximo: 10 MB (decisión provisional, ver `docs/decisiones.md`).
- Vercel limita el tamaño del cuerpo de una petición a una función. Verifica el límite vigente antes de implementar la subida; si 10 MB lo supera, la alternativa es que la API entregue un enlace firmado de subida y el navegador envíe el archivo directo al almacenamiento.
