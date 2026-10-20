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
| `GET /api/me` | Devuelve el propietario, si completó el alta (`onboarding_complete`) y si sus datos de cobro están completos (`profile_complete`: número de documento, datos de pago y firma). Crea su fila si es la primera vez. `onboarding_complete` es verdadero cuando el propietario tiene al menos un inmueble. El nombre y el correo salen del token solo al crear la fila; después manda lo que el propietario guardó. Si el token no trae nombre se usa el correo, y sin correo responde 400 (`email_required`). |
| `PATCH /api/settings` | Actualiza nombre, tipo de documento (`document_type`: `cc` o `nit`), documento y datos de pago (`name`, `document_number`, `payment_details`). Los datos de pago son el valor por defecto de las cuentas. Solo cambian los campos enviados. También día de envío (`send_day`, 1 a 28), recordatorios (`reminder_1`, `reminder_2`) y copia (`email_copy`) |
| `POST /api/settings/signature/upload-url` | Primer paso para subir la firma. Recibe `filename`, `content_type` (`image/png` o `image/jpeg`) y `size` (hasta 2 MB); devuelve el enlace firmado de subida y la ruta. 422 `unsupported_file_type` o `file_too_large` |
| `POST /api/settings/signature` | Segundo paso. Recibe `path`. Valida la imagen, separa la tinta del papel (una foto de la firma sobre una hoja queda con fondo transparente), la recorta a sus trazos, la reduce a 600×200 px como máximo y la guarda como PNG en una carpeta aparte de las subidas; borra lo que subió el navegador y la firma anterior si ninguna cuenta la usa. Devuelve los ajustes. 404 si la ruta no es de la carpeta del propietario; 400 `document_not_uploaded`; 422 `invalid_image` si no se puede leer, está en blanco o es demasiado grande para abrirla |
| `GET /api/settings/signature` | Enlace temporal a la firma (`url`, `name` y `expires_in`, 5 minutos). 404 `signature_not_found` |
| `DELETE /api/settings/signature` | Quita la firma. Las cuentas ya emitidas conservan la suya. Devuelve los ajustes |
| `GET /api/settings` | Devuelve la configuración. `has_signature` dice si hay firma; la imagen tiene su propia ruta |
| `POST /api/onboarding` | Crea el primer inmueble (`property`, con los mismos campos que `POST /api/properties`, como `country`), sus unidades (`units`, de 1 a 50) y, opcionalmente, el arrendatario y el contrato (`lease`, que señala la unidad con `unit_index` y acepta los mismos campos que `POST /api/leases`, como `cc_emails`), en una transacción. 409 `onboarding_already_complete` si el propietario ya tiene un inmueble; 409 `profile_incomplete` si le falta el número de documento, los datos de pago o la firma (el mensaje dice cuáles) |

## Inmuebles y unidades

| Ruta | Qué hace |
| --- | --- |
| `GET /api/properties` | Lista los inmuebles con sus unidades, y por unidad el contrato activo y su `status`. `vacant` (sin contrato activo), `overdue` (alguna cuenta vencida), `partial` (alguna parcial) o `up_to_date` |
| `POST /api/properties` | Crea un inmueble, sin unidades. `country` es un código ISO 3166-1 alfa-2 (`CO`, `PA`…); si no se envía, `CO`. Un código que no existe da 422. Responde 201 |
| `PATCH /api/properties/{id}` | Edita un inmueble. Solo cambian los campos enviados; `address` y `city` se borran con `null`. `country` se cambia, no se borra: `null` da 422 |
| `POST /api/properties/{id}/units` | Agrega una unidad. Responde 201 |
| `PATCH /api/units/{id}` | Edita una unidad |

## Contratos

| Ruta | Qué hace |
| --- | --- |
| `POST /api/leases` | Crea el contrato de una unidad. Recibe `tenant` (arrendatario nuevo, con `document_type` `cc` o `nit` y `document_number` opcionales) o `tenant_id` (uno existente), nunca los dos. Acepta `payment_details` (opcional, hasta 500 caracteres): los datos de pago propios del contrato. Acepta `charge_deposit` (por defecto `true`): si la primera cuenta mensual cobra el depósito. Acepta `cc_emails` (hasta 3): correos que reciben en copia todo lo que recibe el arrendatario; los repetidos y el del arrendatario se descartan. Acepta `items` (hasta 10, cada uno con `description` y `amount`): lo que cobra cada mes además del canon. Acepta el recargo por mora: `late_fee_enabled`, `late_fee_percent` (hasta dos decimales, obligatorio si está activo) y `late_fee_grace_days` (0 a 30). 409 `unit_has_active_lease` si la unidad ya tiene contrato activo; 422 `invalid_lease_dates` si la fecha de fin no es posterior a la de inicio |
| `GET /api/leases/{id}` | Devuelve contrato, arrendatario, unidad con su inmueble y el nombre del documento. Trae sus conceptos fijos en `items`. También sus últimas cuentas, en `recent_bills` (hasta 6, de la más nueva a la más vieja, incluidas las anuladas) |
| `PATCH /api/leases/{id}` | Edita canon, día de pago, fechas, depósito, si se cobra en la primera cuenta (`charge_deposit`), conceptos fijos (`items`: enviarlos reemplaza la lista completa, y una lista vacía los quita), recargo por mora (`late_fee_enabled`, `late_fee_percent`, `late_fee_grace_days`; 422 `late_fee_percent_required` si queda activo sin porcentaje), envío automático, correos en copia (`cc_emails`: enviarlos reemplaza la lista, y una lista vacía los quita), datos de pago propios (`payment_details`; vacío o `null` vuelve a los de Ajustes) y datos del arrendatario (en `tenant`). Solo cambian los campos enviados. También se puede editar un contrato terminado, para corregir el correo del arrendatario si quedó con saldo |
| `POST /api/leases/{id}/end` | Pasa el contrato a terminado. 400 `lease_already_ended` si ya lo estaba |
| `POST /api/leases/{id}/bills` | Genera la cuenta mensual del contrato para el mes en curso (hora de Colombia), sin cuerpo. Sus `items` son el canon, los conceptos fijos del contrato, el recargo por mora de cada cuenta anterior atrasada y, si es la primera y el contrato lo cobra, el depósito; el `total` es la suma. `late_fee` trae las condiciones de recargo de esta cuenta (`amount`, `deadline`, `status`: `on_time`, `pending`, `waived` o `charged`, `charged_on` con la cuenta que lo cobró y `notice`, la frase que lleva el PDF), o `null` si no tiene. `charges_late_fee` dice si la cuenta trae el recargo de una anterior. Responde 201. 409 `signature_unreadable` si el propietario tiene firma y no se puede dibujar; 503 `storage_unavailable` si no se puede leer. 400 `lease_not_active` si el contrato está terminado; 409 `bill_already_exists` si ya hay una cuenta no anulada de ese mes |
| `POST /api/leases/{id}/document/upload-url` | Primer paso de la subida. Recibe `filename`, `content_type` y `size`; devuelve el enlace firmado de subida y la ruta del objeto |
| `POST /api/leases/{id}/document` | Segundo paso. Confirma la subida: valida el archivo guardado, lo asocia al contrato y borra el anterior si lo reemplaza |
| `GET /api/leases/{id}/document` | Devuelve un enlace temporal al documento (`url`, `name` y `expires_in`, 5 minutos). 404 `document_not_found` si el contrato no tiene |
| `POST /api/leases/{id}/inventory/upload-url` | Igual que el del documento, para el inventario de la unidad. Va a su propia carpeta |
| `POST /api/leases/{id}/inventory` | Confirma el inventario: lo valida, lo asocia al contrato y borra el anterior si lo reemplaza. No toca el contrato firmado |
| `GET /api/leases/{id}/inventory` | Enlace temporal al inventario. 404 `inventory_not_found` si el contrato no tiene |

## Cuentas de cobro

| Ruta | Qué hace |
| --- | --- |
| `GET /api/bills` | Lista cuentas. Filtros: `unit_id`, `status` (`receivable`, `paid`, `voided`), `from`, `to` |
| `POST /api/bills` | Crea una cuenta manual sobre un contrato activo: `lease_id`, `items` (de 1 a 10, cada uno con `description` y `amount`) y `due_date`, una sola para toda la cuenta. El `total` es la suma de los conceptos. Acepta `payment_details` (opcional, hasta 500 caracteres), solo para esa cuenta. Responde 201. 400 `lease_not_active` si el contrato está terminado |
| `GET /api/bills/{id}` | Devuelve la cuenta con conceptos, saldo (`balance`), unidad, arrendatario y los datos del propietario que muestra el documento. Trae sus pagos (`payments`) y sus notificaciones (`notifications`), de lo más nuevo a lo más viejo |
| `GET /api/bills/{id}/pdf` | Devuelve un enlace temporal al PDF (`url`, `name` y `expires_in`, 5 minutos) |
| `POST /api/bills/{id}/send` | Envía la cuenta por correo, o la reenvía si ya se había enviado. 400 `bill_voided` si está anulada |
| `POST /api/bills/{id}/remind` | Envía un recordatorio manual. 400 `bill_has_no_balance` si no tiene saldo; 400 `bill_voided` si está anulada |
| `POST /api/bills/{id}/void` | Anula la cuenta. 400 `bill_has_payments` si tiene pagos; 400 `bill_already_voided` si ya estaba anulada; 400 `late_fee_charged_elsewhere` si su recargo por mora ya se cobró en otra cuenta |
| `POST /api/bills/{id}/late-fee/waive` | El propietario decide no cobrar el recargo por mora de esa cuenta: ninguna cuenta posterior lo incluirá. Responde con la cuenta. 400 `bill_has_no_late_fee` si no tiene recargo (o está anulada); 400 `late_fee_already_charged` si ya salió en otra cuenta |
| `POST /api/bills/{id}/late-fee/restore` | Deshace lo anterior: la siguiente cuenta del mes lo cobra. Mismos errores |

El filtro `receivable` reúne `pending`, `partial` y `overdue`. Sin filtro de estado, las anuladas no se incluyen.

El listado va de la más nueva a la más vieja. `from` y `to` (fechas, inclusive) filtran por el mes al que pertenece la cuenta: el `period` de la mensual y el vencimiento de la manual.

La cuenta mensual y la manual se crean con el PDF ya guardado. Si el almacenamiento falla, responden 503 `storage_unavailable` y no se crea nada: el consecutivo no se gasta.

Enviar y recordar responden con la cuenta y la notificación recién creada en estado `pending`: el correo sale después de responder. Si el proveedor falla, la notificación queda `failed` y se ve en la actividad de la cuenta.

## Pagos

| Ruta | Qué hace |
| --- | --- |
| `POST /api/bills/{id}/payments` | Registra un pago: `amount`, `payment_date`, `method` y `send_receipt`. Recalcula el estado y responde 201 con la cuenta. 400 `bill_voided`, `bill_already_paid`, `payment_exceeds_balance` o `payment_date_in_future` |
| `POST /api/payments/{id}/proof/upload-url` | Primer paso del comprobante: devuelve el enlace firmado de subida y la ruta |
| `POST /api/payments/{id}/proof` | Segundo paso: valida el archivo y lo asocia al pago. Responde con la cuenta |
| `GET /api/payments/{id}/proof` | Devuelve un enlace temporal al comprobante. 404 `document_not_found` si no tiene |
| `DELETE /api/payments/{id}` | Elimina un pago registrado por error, borra su comprobante y recalcula el estado. Responde con la cuenta |

## Inicio

| Ruta | Qué hace |
| --- | --- |
| `GET /api/summary?month=AAAA-MM` | Del mes (`expected`, `collected`, `pending`); unidades en mora (`units_overdue` de `units_total`); cuentas por cobrar de cualquier mes, con lo vencido primero (`receivable`), y cuánto viene de meses anteriores (`previous_pending`); pagadas del mes (`paid`); correos rebotados (`bounced`). Sin `month`, el mes en curso en Colombia |

## Sistema

Estas rutas no usan el token del propietario.

| Ruta | Quién la llama | Protección |
| --- | --- | --- |
| `GET /api/cron/daily` | El Cron Job de Vercel | `Authorization: Bearer <CRON_SECRET>`. Responde cuántas cuentas generó, cuántas marcó vencidas, cuántos correos envió y cuántos errores hubo |
| `POST /api/webhooks/email` | Resend | Firma en las cabeceras `svix-*`, con `EMAIL_WEBHOOK_SECRET`. Un rebote deja la notificación `bounced` |
| `GET /api/health` | Monitoreo | Ninguna; no expone datos |

## Subida de archivos

- Tipos permitidos: PDF, JPG y PNG. El tipo real se valida leyendo el contenido, no solo la extensión.
- Tamaño máximo: 10 MB (decisión provisional, ver `docs/decisiones.md`).
- **Subida directa al almacenamiento.** Vercel limita el cuerpo de una petición a una función a 4,5 MB (consultado el 11 de octubre de 2026), así que los archivos no pasan por la API. El flujo, igual para el contrato, su inventario y, en la etapa 5, para el comprobante del pago:
  1. La web pide a la API un enlace firmado de subida (`.../upload-url`), indicando nombre, tipo y tamaño. La API comprueba que el recurso es del propietario y que el tipo y el tamaño están permitidos, y devuelve el enlace y la ruta del objeto. El enlace sirve para esa ruta y vence en pocas horas.
  2. El navegador envía el archivo directo a Supabase Storage con ese enlace.
  3. La web confirma a la API (`POST .../document` o `POST .../inventory`). La API lee del objeto su tamaño real y sus primeros bytes, valida el tipo por contenido, guarda la ruta en la base y borra el archivo anterior. Si no valida, borra el objeto y responde 422.
  Errores: 422 `unsupported_file_type` y 422 `file_too_large` (al pedir el enlace o al confirmar), 400 `document_not_uploaded` (se confirma sin haber subido) y 503 `storage_unavailable`. La confirmación solo acepta una ruta que la API haya entregado para ese mismo contrato; cualquier otra responde 404.
  Un archivo subido y nunca confirmado queda huérfano en el almacenamiento; no se asocia a nada y no se puede abrir desde la API.
