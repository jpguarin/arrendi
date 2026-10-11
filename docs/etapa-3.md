# Etapa 3: guía paso a paso

Guía de trabajo de la etapa 3 (cuentas de cobro). Las tareas y los criterios de aceptación oficiales están en `docs/plan.md`; este documento detalla el orden, qué hace cada paso y cómo se comprueba. Se marca cada paso al terminarlo.

**Objetivo:** generar cuentas con consecutivo y PDF, a mano, sin correo ni pagos todavía.

**Criterios de aceptación**

- Genero la cuenta del mes de cada contrato y los consecutivos son seguidos.
- El PDF muestra mis datos, los del arrendatario, el concepto, el total, el vencimiento y los datos de pago.
- Anulo una cuenta y genero otra del mismo mes con consecutivo nuevo.

## Decisiones de esta etapa

Tomadas el 11 de octubre de 2026, porque los documentos no las cubrían:

1. **Cuenta mensual a mano.** Ruta nueva `POST /api/leases/{id}/bills`, que genera la del mes en curso con el mismo servicio que usará la tarea diaria.
2. **Ajustes mínimo, adelantado.** El PDF necesita tus datos y los de pago, así que `GET` y `PATCH /api/settings` y la pantalla `/settings` llegan en esta etapa solo con nombre, documento y datos de pago. Día de envío, recordatorios, copia y tema siguen en la etapa 4.
3. **Vencimiento ya pasado.** Una cuenta cuyo vencimiento es anterior a hoy nace `overdue`.

## Límites asumidos

- **Sin pagos ni notificaciones:** esas tablas llegan en las etapas 4 y 5. El detalle de la cuenta devuelve `balance` (igual al total) y no trae `payments` ni `notifications` hasta entonces.
- **Anulación sin tabla de pagos:** se permite solo desde `pending` u `overdue`; desde `partial` o `paid` responde 400 `bill_has_payments`. La prueba "no se anula una cuenta con pagos" fuerza el estado `partial` desde el administrador. La etapa 5 agrega la comprobación contra `payments`.
- **Web sin "Registrar pago" ni "Reenviar":** el pie del detalle solo tiene "Descargar PDF" y "Anular". La actividad muestra solo "Generada" y "Anulada".
- **Vista del documento:** como en el mockup, es HTML armado con los datos de la cuenta, no el PDF incrustado. Usa tus datos actuales; el PDF guardado es el inmutable.
- **Listado:** agrupa por `period`; la manual, por el mes de su vencimiento. `from` y `to` filtran esa misma fecha. El encabezado del mes muestra solo el total (el "recaudado de" llega con los pagos) y las pastillas no llevan contador. Pastillas: Todas, Por cobrar, Pagadas, Anuladas.
- **Fuente del PDF:** Helvetica, incluida en ReportLab. No se empaqueta Figtree.
- **Dependencias nuevas:** `reportlab` en `apps/api/requirements.txt` (genera el PDF) y el componente `textarea` de shadcn/ui (datos de pago en varias líneas).

## Lo que haces tú

| Cuándo | Qué | Dónde |
| --- | --- | --- |
| Después del paso 2 | Aplicar la migración `0003` con `alembic upgrade head` | `arrendi-dev`, antes de subir el código que la usa |
| Antes de generar cuentas | Cargar nombre, cédula y datos de pago | Ajustes |
| Al final | Generar las 3 cuentas del mes, abrir un PDF en el iPhone, anular una y generarla de nuevo | `arrendi-web.vercel.app` |

El contenedor `arrendi` ya admite PDF; no cambia nada en Storage.

## Pasos

En los pasos 2, 5 y 7 la prueba va primero.

### [x] Paso 1. Documentos al día

- `docs/api.md`: `POST /api/leases/{id}/bills`; alcance de `settings` en esta etapa; campos del detalle; códigos `bill_already_exists` (409), `lease_not_active` (400), `bill_has_payments` y `bill_already_voided` (400).
- `docs/reglas-de-negocio.md`: la cuenta con vencimiento pasado nace `overdue`; la mensual se puede generar a mano.
- `docs/decisiones.md`, `docs/diseno.md` (pestañas Cuentas y Ajustes, diferencias con los mockups), `docs/plan.md` (Ajustes mínimo en la etapa 3) y `CLAUDE.md` (este documento en la tabla).
- **Se comprueba:** los documentos no se contradicen entre sí.

### [x] Paso 2. Migración `0003` y modelos

- `apps/api/migrations/versions/0003_bills.py`, con `0002` como molde: `bills` y `bill_items`, claves foráneas compuestas con `owner_id`, `unique (owner_id, id)`, `check` de `origin`, `status` y `total > 0`, único `(owner_id, number)`, índice único parcial `(lease_id, period) where origin = 'monthly' and status <> 'voided'`, índice `(status, due_date)`, y `check` de que `period` existe solo en las mensuales.
- Seguridad por fila, disparador y revocación a los roles de Supabase. `arrendi_api`: select, insert, update. `arrendi_tasks`: select, insert y update en `bills`; select e insert en `bill_items`.
- `app/models/bill.py` y `bill_item.py`; `OWNED_TABLES` de `tests/conftest.py`.
- **Se comprueba:** `tests/test_bill_tables.py`: restricciones, política, permisos, y que una cuenta no puede apuntar al contrato de otro propietario.

### [x] Paso 3. Ajustes mínimo en la API

- `app/schemas/settings.py`, `app/services/owners.py` y `app/routes/settings.py`: `GET` y `PATCH /api/settings` con `name`, `document_number` y `payment_details`.
- **Se comprueba:** solo cambian los campos enviados; aislamiento.

### [x] Paso 4. PDF y subida al almacenamiento

- `app/pdf/bill.py`: función pura que devuelve los bytes del PDF, con consecutivo, emisión, propietario, arrendatario, concepto, total, vencimiento, datos de pago, pie "Arrendi" y marca "ANULADA" opcional. Fechas largas y pesos en `app/pdf/format.py`.
- `app/storage.py`: método `upload`, que reemplaza el archivo si existe.
- `app/dates.py`: `today_in_bogota()`, que las pruebas pueden fijar.
- **Se comprueba:** el PDF empieza por `%PDF-` y contiene los textos esperados; formatos de fecha y dinero.

### [x] Paso 5. Servicio de emisión

`app/services/bills.py`, en la transacción de la petición:

1. `select ... for update` sobre la fila del propietario; toma `next_number` y lo incrementa.
2. Inserta `bills` (id generado en Python, para conocer `pdf_path = {owner_id}/bills/{bill_id}.pdf`) y su `bill_items`. Estado `overdue` si el vencimiento es anterior a hoy en Colombia; si no, `pending`. El índice único decide el duplicado: 409 `bill_already_exists`.
3. Genera el PDF y lo sube. Si falla, 503 y la transacción se deshace: el consecutivo no se gasta.

La mensual: contrato activo, periodo del mes en curso, vencimiento en `due_day`, total igual al canon, concepto "Canon de arrendamiento". La manual: contrato activo, descripción, valor y vencimiento; sin periodo.

- **Se comprueba:** consecutivos 1..N sin saltos ni repetidos con N emisiones simultáneas; una emisión que falla no deja hueco; una mensual por contrato y periodo, también con dos peticiones a la vez; tras anular se puede generar otra; nace `overdue` o `pending` según la fecha; cambiar el canon después no altera la cuenta.

### [x] Paso 6. Rutas de cuentas

- `app/schemas/bill.py` y `app/routes/bills.py`: `POST /api/leases/{id}/bills`, `POST /api/bills`, `GET /api/bills` (filtros `unit_id`, `status`, `from`, `to`), `GET /api/bills/{id}` y `GET /api/bills/{id}/pdf` (enlace de 5 minutos).
- `GET /api/leases/{id}`: campo `recent_bills`.
- **Se comprueba:** cada ruta, y aislamiento en todas (404 con cuentas y contratos ajenos).

### [ ] Paso 7. Anulación

- `POST /api/bills/{id}/void`: pasa a `voided` con `voided_at` y conserva el consecutivo. El PDF marcado "ANULADA" reemplaza al anterior después de confirmar la transacción.
- **Se comprueba:** no se anula con pagos, ni dos veces; aislamiento; el PDF queda marcado.

### [ ] Paso 8. Tipos y base de la web

- `pnpm gen:api`.
- `lib/format.ts` con pruebas: número de cuenta (`N.º 0031`) y mes (`Octubre 2026`). `lib/labels.ts`: estado de cuenta con su tono de `Badge`.
- `components/bills/BillRow.tsx`; `textarea` de shadcn/ui adaptado al tema; `BottomNav.tsx` con Cuentas y Ajustes.
- `lib/api/queries.ts`: lecturas y escrituras de cuentas y ajustes, cada escritura con lo que actualiza en memoria.

### [ ] Paso 9. Ajustes en la web

- `/settings`: nombre, documento y datos de pago.

### [ ] Paso 10. Listado y cuenta manual

- `/bills` (mockup `Cuentas`): filtro de unidad, pastillas de estado, grupos por mes, estados vacío, de carga y de error.
- `/bills/new`: contrato activo, descripción, valor y vencimiento.

### [ ] Paso 11. Detalle y contrato

- `/bills/[id]` (mockup `Cuenta`): vista del documento, actividad, "Descargar PDF" y "Anular" con confirmación.
- Contrato: sección "Cuentas de cobro" con las últimas, "Ver todas" y el botón "Generar cuenta del mes". Aviso con enlace a Ajustes si faltan los datos de pago.
- **Se comprueba:** ambos temas en cada pantalla.

### [ ] Paso 12. Cierre

- `pnpm lint`, `pnpm test` y `pnpm build`; casillas de la etapa 3 en `docs/plan.md`. La etapa pasa a 4 cuando confirmes los criterios de aceptación.

## Verificación de extremo a extremo

- **En local, con `pnpm dev`:** cargar los datos en Ajustes; generar la cuenta del mes de los 3 contratos y ver consecutivos seguidos; abrir el PDF y revisar tus datos, el arrendatario, el concepto, el total, el vencimiento y los datos de pago; anular una, generar otra del mismo mes y ver el consecutivo siguiente; el PDF de la anulada dice "ANULADA"; crear una cuenta manual; filtros del listado; tema claro y oscuro.
- **Con otra cuenta:** una cuenta ajena y su PDF responden 404.
- **En `arrendi-web.vercel.app`:** el mismo recorrido desde el iPhone.

## Riesgos

- **Bloqueo durante la subida:** la fila del propietario queda bloqueada mientras el PDF sube (hasta 10 s). Solo frena otras emisiones del mismo propietario, y es lo que garantiza que no haya saltos.
- **PDF de anulada sin marca:** si la subida posterior a la confirmación falla, la cuenta queda anulada con el PDF original. No se deshace la anulación.
- **Vista y PDF pueden diferir** si cambias tus datos después de emitir. Guardar una copia de esos datos en la cuenta cambiaría el modelo; no se hace sin que lo decidas.