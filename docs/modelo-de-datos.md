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
        │                        ├── leases ── bills ─┬─ bill_items
        └─ tenants ──────────────┘                    ├─ payments
                                                      └─ notifications
```

El contrato es el centro: une una unidad con un arrendatario, y de él nacen las cuentas.

## Convenciones

- Claves primarias `uuid`, generadas en la base.
- Todas las tablas llevan `owner_id`, `created_at` y `updated_at` (`timestamptz`).
- El dinero se guarda en pesos enteros (`bigint`).
- Las fechas de negocio son `date`.
- Los valores cerrados (estados, usos, medios) son `text` con una restricción `check`.

## Tablas

### owners

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | Igual al id del usuario en Supabase Auth |
| `name` | text | |
| `document_number` | text, nulo | Cédula o NIT |
| `email` | text | |
| `payment_details` | text, nulo | Texto libre que aparece en cada cuenta |
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
| `deposit` | bigint, nulo | |
| `status` | text | `active`, `ended` |
| `auto_send` | boolean, por defecto true | |
| `document_path` | text, nulo | Ruta en el almacenamiento |
| `document_uploaded_at` | timestamptz, nulo | |

Restricción: índice único parcial sobre `unit_id` donde `status = 'active'`.

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
| `pdf_path` | text | |
| `voided_at` | timestamptz, nulo | |

Restricciones:

- Único `(owner_id, number)`.
- Índice único parcial sobre `(lease_id, period)` donde `origin = 'monthly'` y `status <> 'voided'`.
- Índice sobre `(status, due_date)` para la tarea diaria.

### bill_items

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `bill_id` | uuid, FK | |
| `description` | text | |
| `amount` | bigint | Mayor que cero |

En el MVP cada cuenta tiene un solo concepto. La tabla existe para admitir después servicios, mora o reparaciones.

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

### notifications

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `owner_id` | uuid, FK | |
| `bill_id` | uuid, FK | |
| `type` | text | `bill`, `reminder_1`, `reminder_2`, `receipt`, `manual_reminder`, `resend` |
| `channel` | text | `email` en el MVP |
| `recipient` | text | Correo al que se envió |
| `delivery_status` | text | `sent`, `bounced`, `failed` |
| `provider_id` | text, nulo | Para cruzar los avisos de rebote |
| `sent_at` | timestamptz | |

Restricción: índice único parcial sobre `(bill_id, type)` donde `type in ('bill', 'reminder_1', 'reminder_2')`.

## Seguridad por fila

Cada tabla tiene la seguridad por fila activada y forzada, con una política que compara `owner_id` con una variable de sesión que fija la API.

```sql
alter table properties enable row level security;
alter table properties force row level security;

create policy owner_isolation on properties
  using (owner_id = current_setting('app.owner_id', true)::uuid)
  with check (owner_id = current_setting('app.owner_id', true)::uuid);
```

En `owners` la política compara la columna `id`.

La API fija la variable al abrir cada transacción de una petición:

```sql
select set_config('app.owner_id', :owner_id, true);
```

El tercer argumento `true` hace que el valor dure solo esa transacción. Esto es obligatorio: la API se conecta a través de un agrupador de conexiones, y un valor que durara más se filtraría a otra petición.

Si la variable no está fijada, `current_setting(..., true)` devuelve nulo y la política no deja pasar ninguna fila. Ese es el comportamiento deseado.

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

- La migración da a cada rol los permisos mínimos sobre las tablas (`select`, `insert`, `update`, `delete`) y fija permisos por defecto para las tablas futuras.
- **La API de datos de Supabase no llega a estas tablas.** La migración revoca todos los permisos de los roles `anon` y `authenticated` sobre las tablas de Arrendi, de modo que la clave publicable no sirve para leerlas. Solo FastAPI accede a los datos.
- Por el agrupador de Supabase, un rol propio se conecta con el usuario `arrendi_api.<ref-del-proyecto>`.

Por comprobar al crear los roles en `arrendi-dev`: que el usuario administrador de Supabase puede crear un rol con `bypassrls`. La página de roles de Supabase no lo documenta para roles propios.

## Base de datos de las pruebas

Las pruebas de la API corren contra un PostgreSQL local, instalado con Homebrew, y nunca contra un proyecto de Supabase. Al empezar, las pruebas aplican las migraciones sobre una base vacía (lo que crea los roles) y se conectan como `arrendi_api` para comprobar el aislamiento con las mismas políticas que producción.

## Almacenamiento de archivos

Un solo contenedor privado. Las rutas empiezan por el propietario:

```
{owner_id}/leases/{lease_id}/{nombre}
{owner_id}/bills/{bill_id}.pdf
{owner_id}/proofs/{payment_id}/{nombre}
```

Solo la API lee y escribe. Para mostrar un archivo, la API comprueba el propietario y devuelve un enlace temporal de pocos minutos.
