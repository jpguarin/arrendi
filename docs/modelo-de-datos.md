# Modelo de datos

Este documento es la referencia de diseño. La fuente de verdad del esquema son las migraciones de Alembic en `apps/api/migraciones/`. Si cambias el esquema, actualiza este documento en el mismo commit.

## Relaciones

```
propietarios ─┬─ inmuebles ── unidades ──┐
              │                          ├── contratos ── cuentas ─┬─ conceptos
              └─ arrendatarios ──────────┘                         ├─ pagos
                                                                   └─ notificaciones
```

El contrato es el centro: une una unidad con un arrendatario, y de él nacen las cuentas.

## Convenciones

- Claves primarias `uuid`, generadas en la base.
- Todas las tablas llevan `propietario_id`, `creado_en` y `actualizado_en` (`timestamptz`).
- El dinero se guarda en pesos enteros (`bigint`).
- Las fechas de negocio son `date`.
- Los valores cerrados (estados, usos, medios) son `text` con una restricción `check`.

## Tablas

### propietarios

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | Igual al id del usuario en Supabase Auth |
| `nombre` | text | |
| `documento` | text, nulo | Cédula o NIT |
| `correo` | text | |
| `datos_pago` | text, nulo | Texto libre que aparece en cada cuenta |
| `dia_envio` | smallint, por defecto 1 | Entre 1 y 28 |
| `recordatorio_1` | boolean, por defecto true | |
| `recordatorio_2` | boolean, por defecto true | |
| `copia_correo` | boolean, por defecto false | |
| `siguiente_consecutivo` | integer, por defecto 1 | Se incrementa al emitir |
| `acepto_tratamiento_en` | timestamptz, nulo | Autorización de datos personales |

En esta tabla, `propietario_id` es la propia columna `id`.

### inmuebles

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `propietario_id` | uuid, FK | |
| `nombre` | text | |
| `direccion` | text, nulo | |
| `ciudad` | text, nulo | |
| `tipo` | text | `casa`, `edificio`, `apartamento`, `local` |

### unidades

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `propietario_id` | uuid, FK | |
| `inmueble_id` | uuid, FK | |
| `nombre` | text | |
| `uso` | text | `vivienda`, `comercial` |

### arrendatarios

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `propietario_id` | uuid, FK | |
| `nombre` | text | |
| `documento` | text, nulo | |
| `correo` | text | Obligatorio: es el canal de envío |
| `telefono` | text, nulo | |

### contratos

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `propietario_id` | uuid, FK | |
| `unidad_id` | uuid, FK | |
| `arrendatario_id` | uuid, FK | |
| `canon` | bigint | Mayor que cero |
| `dia_pago` | smallint | Entre 1 y 28 |
| `inicio` | date | |
| `fin` | date, nulo | Posterior a `inicio` |
| `deposito` | bigint, nulo | |
| `estado` | text | `activo`, `terminado` |
| `envio_automatico` | boolean, por defecto true | |
| `documento_ruta` | text, nulo | Ruta en el almacenamiento |
| `documento_subido_en` | timestamptz, nulo | |

Restricción: índice único parcial sobre `unidad_id` donde `estado = 'activo'`.

### cuentas

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `propietario_id` | uuid, FK | |
| `contrato_id` | uuid, FK | |
| `consecutivo` | integer | |
| `origen` | text | `mensual`, `manual` |
| `periodo` | date, nulo | Primer día del mes; nulo en las manuales |
| `emision` | date | |
| `vencimiento` | date | |
| `total` | bigint | Mayor que cero |
| `estado` | text | `pendiente`, `parcial`, `pagada`, `vencida`, `anulada` |
| `pdf_ruta` | text | |
| `anulada_en` | timestamptz, nulo | |

Restricciones:

- Único `(propietario_id, consecutivo)`.
- Índice único parcial sobre `(contrato_id, periodo)` donde `origen = 'mensual'` y `estado <> 'anulada'`.
- Índice sobre `(estado, vencimiento)` para la tarea diaria.

### conceptos

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `propietario_id` | uuid, FK | |
| `cuenta_id` | uuid, FK | |
| `descripcion` | text | |
| `valor` | bigint | Mayor que cero |

En el MVP cada cuenta tiene un solo concepto. La tabla existe para admitir después servicios, mora o reparaciones.

### pagos

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `propietario_id` | uuid, FK | |
| `cuenta_id` | uuid, FK | |
| `fecha` | date | No futura |
| `valor` | bigint | Mayor que cero |
| `medio` | text | `transferencia`, `nequi`, `efectivo`, `otro` |
| `comprobante_ruta` | text, nulo | |

### notificaciones

| Columna | Tipo | Notas |
| --- | --- | --- |
| `id` | uuid, PK | |
| `propietario_id` | uuid, FK | |
| `cuenta_id` | uuid, FK | |
| `tipo` | text | `cuenta`, `recordatorio_1`, `recordatorio_2`, `recibo`, `recordatorio_manual`, `reenvio` |
| `canal` | text | `correo` en el MVP |
| `destinatario` | text | Correo al que se envió |
| `estado_envio` | text | `enviada`, `rebotada`, `fallida` |
| `id_proveedor` | text, nulo | Para cruzar los avisos de rebote |
| `enviada_en` | timestamptz | |

Restricción: índice único parcial sobre `(cuenta_id, tipo)` donde `tipo in ('cuenta', 'recordatorio_1', 'recordatorio_2')`.

## Seguridad por fila

Cada tabla tiene la seguridad por fila activada y forzada, con una política que compara `propietario_id` con una variable de sesión que fija la API.

```sql
alter table inmuebles enable row level security;
alter table inmuebles force row level security;

create policy aislamiento_propietario on inmuebles
  using (propietario_id = current_setting('app.propietario_id', true)::uuid)
  with check (propietario_id = current_setting('app.propietario_id', true)::uuid);
```

En `propietarios` la política compara la columna `id`.

La API fija la variable al abrir cada transacción de una petición:

```sql
select set_config('app.propietario_id', :propietario_id, true);
```

El tercer argumento `true` hace que el valor dure solo esa transacción. Esto es obligatorio: la API se conecta a través de un agrupador de conexiones, y un valor que durara más se filtraría a otra petición.

Si la variable no está fijada, `current_setting(..., true)` devuelve nulo y la política no deja pasar ninguna fila. Ese es el comportamiento deseado.

## Roles de base de datos

| Rol | Quién lo usa | Salta las políticas |
| --- | --- | --- |
| `arrendi_api` | Las peticiones de los propietarios | No |
| `arrendi_tareas` | La tarea diaria y los avisos del correo | Sí |

- Las migraciones se ejecutan con el usuario administrador de la base, fuera de la aplicación.
- La creación de roles y sus permisos en Supabase debe verificarse con su documentación vigente durante la etapa 1.

## Almacenamiento de archivos

Un solo contenedor privado. Las rutas empiezan por el propietario:

```
{propietario_id}/contratos/{contrato_id}/{nombre}
{propietario_id}/cuentas/{cuenta_id}.pdf
{propietario_id}/comprobantes/{pago_id}/{nombre}
```

Solo la API lee y escribe. Para mostrar un archivo, la API comprueba el propietario y devuelve un enlace temporal de pocos minutos.
