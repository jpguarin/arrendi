# Modelo de datos

Este documento es la referencia de diseño. La fuente de verdad del esquema son las migraciones de Alembic en `apps/api/migrations/`. Si cambias el esquema, actualiza este documento en el mismo commit.

## Vocabulario

El código va en inglés y la interfaz en español. Esta tabla fija cómo se llama cada concepto del dominio en el código.

| En el producto | En el código |
| --- | --- |
| Propietario | `owner` |
| Inmueble | `property` |
| Unidad | `unit` |
| Arrendatario | `tenant` |
| Contrato | `lease` |
| Cuenta de cobro | `bill` |
| Concepto | `bill_item` |
| Pago | `payment` |
| Comprobante del pago | `proof` |
| Recibo (correo al arrendatario) | `receipt` |
| Notificación | `notification` |
| Consecutivo | `number` |
| Canon | `rent` |
| Alta guiada | `onboarding` |
| Configuración | `settings` |
| Tarea diaria | `daily task` |

La cuenta de cobro se llama `bill` y no `invoice` a propósito: no es una factura, y la factura electrónica puede llegar después como un concepto distinto.

## Relaciones

```
owners ─┬─ properties ── units ──┐
        │                        ├── leases ─┬─ bills ─┬─ bill_items
        └─ tenants ──────────────┘                    ├─ payments
                                                      └─ notifications
```

El contrato es el centro: une una unidad con un arrendatario, y de él nacen las cuentas.

## Convenciones

- Claves primarias `uuid`, generadas en la base.
- Todas las tablas llevan `owner_id`, `created_at` y `updated_at` (`timestamptz`). Un disparador (`set_updated_at`) mantiene `updated_at` al día en cada modificación.
- El dinero se guarda en pesos enteros (`bigint`).
- Las fechas de negocio son `date`.
- Los valores cerrados (estados, usos, medios) son `text` con una restricción `check`.
- **Las claves foráneas llevan el propietario.** Una clave foránea no pasa por la seguridad por fila, así que una fila podría apuntar a la de otro propietario con solo conocer su id. Para impedirlo, cada tabla que se referencia tiene `unique (owner_id, id)` y cada clave foránea es compuesta: `foreign key (owner_id, property_id) references properties (owner_id, id)`, y lo mismo para `unit_id`, `tenant_id`, `lease_id` y `bill_id`. La base rechaza el cruce aunque la API tuviera un error.

## Tablas

### owners

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | Igual al id del usuario en Supabase Auth |
| `name` | text | |
| `document_type` | text, por defecto `cc` | `cc` (cédula) o `nit`: qué es `document_number` |
| `document_number` | text, nulo | Cédula o NIT |
| `email` | text | |
| `payment_details` | text, nulo | Texto libre con los datos de pago. Es el valor por defecto: un contrato o una cuenta pueden llevar los suyos |
| `signature_path` | text, nulo | Ruta de la firma en el almacenamiento: un PNG que la API guarda ya recortado y reducido |
| `send_day` | smallint, por defecto 1 | Entre 1 y 28 |
| `reminder_1` | boolean, por defecto true | |
| `reminder_2` | boolean, por defecto true | |
| `email_copy` | boolean, por defecto false | |
| `next_number` | integer, por defecto 1 | Siguiente consecutivo; se incrementa al emitir |
| `data_consent_at` | timestamptz, nulo | Autorización de datos personales |

En esta tabla, `owner_id` es la propia columna `id`.

### properties

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `name` | text | |
| `address` | text, nulo | |
| `city` | text, nulo | |
| `type` | text | `house`, `building`, `apartment`, `shop` |

### units

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `property_id` | uuid, FK | |
| `name` | text | |
| `use` | text | `residential`, `commercial` |

### tenants

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `name` | text | |
| `document_type` | text, por defecto `cc` | `cc` (cédula) o `nit`: qué es `document_number` |
| `document_number` | text, nulo | |
| `email` | text | Obligatorio: es el canal de envío |
| `phone` | text, nulo | |

### leases

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `unit_id` | uuid, FK | |
| `tenant_id` | uuid, FK | |
| `rent` | bigint | Canon. Mayor que cero |
| `due_day` | smallint | Día de pago. Entre 1 y 28 |
| `start_date` | date | |
| `end_date` | date, nulo | Posterior a `start_date` |
| `deposit` | bigint, nulo | Cero o más |
| `charge_deposit` | boolean, por defecto false | Si la primera cuenta mensual cobra el depósito. La API lo enciende en los contratos nuevos, salvo que el propietario diga que no; los anteriores a esta columna quedaron en false |
| `status` | text | `active`, `ended` |
| `auto_send` | boolean, por defecto true | |
| `cc_emails` | text[], por defecto vacío | Correos que reciben en copia visible todo lo que recibe el arrendatario. Hasta 3, sin repetidos y sin el del arrendatario |
| `late_fee_enabled` | boolean, por defecto false | Si pagar tarde el canon genera recargo por mora |
| `late_fee_percent` | numeric(5,2), nulo | Porcentaje del canon. Mayor que 0, hasta 100. Obligatorio con el recargo activo; se conserva al apagarlo |
| `late_fee_grace_days` | smallint, por defecto 0 | Días después del vencimiento antes de que aplique. Entre 0 y 30 |
| `payment_details` | text, nulo | Datos de pago propios del contrato. Nulo: sus cuentas usan los del propietario |
| `document_path` | text, nulo | Ruta en el almacenamiento |
| `document_uploaded_at` | timestamptz, nulo | |

Restricción: índice único parcial sobre `unit_id` donde `status = 'active'`. Decide la base, no el código, cuál gana si dos peticiones crean a la vez un contrato para la misma unidad.

### lease_items

Lo que el contrato cobra cada mes además del canon, como la administración.

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `lease_id` | uuid, FK | |
| `description` | text | |
| `amount` | bigint | Mayor que cero |
| `position` | smallint | Orden dentro de la cuenta, desde 0, después del canon. Único por contrato |

Hasta 10 por contrato; el límite lo pone la API. Editar el contrato reemplaza la lista completa: la API borra e inserta, nunca modifica. Lo ya cobrado vive en `bill_items` y no cambia.

Permisos: `arrendi_api` lee, crea y borra; `arrendi_tasks` solo lee, para generar la cuenta del mes.

### bills

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `lease_id` | uuid, FK | |
| `number` | integer | Consecutivo |
| `origin` | text | `monthly`, `manual` |
| `period` | date, nulo | Primer día del mes; nulo en las manuales |
| `issue_date` | date | |
| `due_date` | date | |
| `total` | bigint | Mayor que cero |
| `status` | text | `pending`, `partial`, `paid`, `overdue`, `voided` |
| `payment_details` | text, nulo | Datos de pago con los que se emitió. Se fijan al emitir y no cambian |
| `late_fee_amount` | bigint, nulo | Lo que cuesta pagar tarde esta cuenta, fijado al emitir. Nulo si el contrato no tenía recargo: nunca lo genera |
| `late_fee_deadline` | date, nulo | Último día para pagarla sin recargo: vencimiento más días de gracia |
| `late_fee_waived_at` | timestamptz, nulo | Cuándo el propietario decidió no cobrarlo |
| `signature_path` | text, nulo | Firma del propietario con la que se emitió. Nulo si no tenía. El archivo no se borra mientras una cuenta lo use |
| `pdf_path` | text | |
| `voided_at` | timestamptz, nulo | |

Restricciones:

- Único `(owner_id, number)`.
- Índice único parcial sobre `(lease_id, period)` donde `origin = 'monthly'` y `status <> 'voided'`.
- Índice sobre `(status, due_date)` para la tarea diaria.
- `period` existe solo en las mensuales y es siempre el primer día del mes.
- `voided_at` existe solo en las anuladas.

Permisos: `arrendi_api` y `arrendi_tasks` leen, crean y modifican cuentas (la tarea diaria las genera y las marca vencidas).

### bill_items

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `bill_id` | uuid, FK | |
| `description` | text | |
| `amount` | bigint | Mayor que cero |
| `position` | smallint, por defecto 0 | Orden del concepto dentro de la cuenta, desde 0 |
| `late_fee_of_bill_id` | uuid, FK, nulo | La cuenta atrasada de la que este concepto es el recargo. La clave foránea lleva el propietario |

Los conceptos de una cuenta emitida no cambian: ningún rol puede modificarlos, solo leerlos y crearlos.

Una cuenta tiene uno o más conceptos y su `total` es la suma. La mensual lleva el canon, los conceptos del contrato (`lease_items`) y, si es la primera y el contrato lo cobra, el depósito. La manual lleva los que el propietario le ponga, hasta 10.

### payments

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `bill_id` | uuid, FK | |
| `payment_date` | date | No futura |
| `amount` | bigint | Mayor que cero |
| `method` | text | `transfer`, `nequi`, `cash`, `other` |
| `proof_path` | text, nulo | Comprobante |

Permisos: `arrendi_api` lee, crea, modifica y borra pagos; es la única tabla donde un rol borra. `arrendi_tasks` solo lee, para el saldo de los recordatorios.

### notifications

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `bill_id` | uuid, FK | |
| `type` | text | `bill`, `reminder_1`, `reminder_2`, `receipt`, `manual_reminder`, `resend` |
| `channel` | text | `email` en el MVP |
| `recipient` | text | Correo al que se envió |
| `delivery_status` | text | `pending` (apartada, aún sin enviar), `sent`, `bounced`, `failed` |
| `provider_id` | text, nulo | Para cruzar los avisos de rebote |
| `sent_at` | timestamptz, nulo | Cuándo salió; nulo mientras no haya salido |

Restricción: índice único parcial sobre `(bill_id, type)` donde `type in ('bill', 'reminder_1', 'reminder_2')`. Índice sobre `provider_id`, para los avisos de rebote.

Permisos: `arrendi_api` y `arrendi_tasks` leen, crean y modifican notificaciones.

## Seguridad por fila

Cada tabla tiene la seguridad por fila activada y forzada, con una política que compara `owner_id` con una variable de sesión que fija la API.

```sql
alter table properties enable row level security;
alter table properties force row level security;

create policy owner_isolation on properties
  using (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid)
  with check (owner_id = nullif(current_setting('app.owner_id', true), '')::uuid);
```

En `owners` la política compara la columna `id`.

La API fija la variable al abrir cada transacción de una petición:

```sql
select set_config('app.owner_id', :owner_id, true);
```

El tercer argumento `true` hace que el valor dure solo esa transacción. Esto es obligatorio: la API se conecta a través de un agrupador de conexiones, y un valor que durara más se filtraría a otra petición.

Si la variable no está fijada, `current_setting(..., true)` devuelve nulo y la política no deja pasar ninguna fila. Ese es el comportamiento deseado. En una conexión que ya la fijó en una transacción anterior, devuelve una cadena vacía en lugar de nulo; por eso la política usa `nullif`, para que ese caso tampoco deje pasar filas en vez de fallar.

## Roles de base de datos

| Rol | Quién lo usa | Salta las políticas |
| --- | --- | --- |
| `arrendi_api` | Las peticiones de los propietarios | No |
| `arrendi_tasks` | La tarea diaria y los avisos del correo | Sí (`bypassrls`) |

- Las migraciones se ejecutan con el usuario administrador de la base, fuera de la aplicación.
- **La migración crea los roles sin acceso y sin contraseña.** Los roles son globales del servidor y una contraseña en una migración sería un secreto en el repositorio. En cada proyecto de Supabase, el fundador activa el acceso a mano en el editor SQL:

  ```sql
  alter role arrendi_api with login password '...';
  alter role arrendi_tasks with login password '...';
  ```

- Cada migración da a cada rol, de forma explícita, los permisos mínimos sobre las tablas que crea. No hay permisos por defecto para tablas futuras. En `owners`, `arrendi_api` puede leer, crear y modificar, y `arrendi_tasks` leer y modificar; ningún rol borra propietarios.
- **La API de datos de Supabase no llega a estas tablas.** Cada migración revoca todos los permisos de los roles `anon`, `authenticated` y `service_role` sobre las tablas que crea, de modo que ni la clave publicable ni la secreta sirven para leerlas por esa vía. Solo FastAPI accede a los datos.
- Por el agrupador de Supabase, un rol propio se conecta con el usuario `arrendi_api.<ref-del-proyecto>`.

Comprobado el 10 de octubre de 2026 en `arrendi-dev`: el usuario administrador de Supabase (`postgres`) sí puede crear un rol con `bypassrls`, y la migración `0001` se aplicó sin cambios.

## Base de datos de las pruebas

Las pruebas de la API corren contra un PostgreSQL local, instalado con Homebrew, y nunca contra un proyecto de Supabase. Al empezar, las pruebas vacían la base, aplican las migraciones (lo que crea los roles) y se conectan como `arrendi_api` para comprobar el aislamiento con las mismas políticas que producción. La base de pruebas imita a Supabase creando los roles `anon`, `authenticated` y `service_role` con acceso a toda tabla nueva, para comprobar que las migraciones se lo quitan.

## Almacenamiento de archivos

Un solo contenedor privado. Las rutas empiezan por el propietario:

```
{owner_id}/leases/{lease_id}/{upload_id}/{nombre}
{owner_id}/bills/{bill_id}.pdf
{owner_id}/proofs/{payment_id}/{upload_id}/{nombre}
```

Cada subida va a una carpeta nueva (`upload_id`): así el archivo que se reemplaza sigue intacto hasta que el nuevo se confirma, y un enlace de subida nunca puede sobrescribir un archivo ya asociado. El nombre se limpia: solo letras sin tilde, números, guiones y la extensión que corresponde al tipo.

Solo la API da acceso. Para subir, la API comprueba el propietario y devuelve un enlace firmado de subida para esa ruta; para mostrar, devuelve un enlace temporal de pocos minutos. Con esos enlaces, el navegador sube y descarga directo del almacenamiento: el archivo no pasa por la API, porque Vercel limita el cuerpo de una petición a 4,5 MB. El flujo está en `docs/api.md`.

El contenedor se crea a mano en cada proyecto de Supabase, antes de la etapa 2:

- Nombre `arrendi` (variable `STORAGE_BUCKET`), **privado**, con límite de tamaño de 10 MB y tipos permitidos `application/pdf`, `image/jpeg` e `image/png`.
- Sin políticas sobre `storage.objects`: ningún usuario accede por la API de Storage con su sesión. Solo la API, con la clave secreta, crea los enlaces.
- La API vuelve a validar tamaño y tipo real al confirmar, porque el límite del contenedor no revisa el contenido.
