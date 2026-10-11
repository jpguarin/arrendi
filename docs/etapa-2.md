# Etapa 2: guía paso a paso

Guía de trabajo de la etapa 2 (inmuebles y contratos). Las tareas y los criterios de aceptación oficiales están en `docs/plan.md`; este documento detalla el orden, qué hace cada paso y cómo se comprueba. Se marca cada paso al terminarlo, con commit aprobado.

**Objetivo:** cargar la casa, sus unidades, los arrendatarios y los contratos, con el contrato firmado como archivo. Sin cuentas de cobro todavía.

**Criterios de aceptación**

- Completo el alta con la casa y sus 3 unidades, y creo los 3 contratos.
- Subo un contrato en PDF desde el celular y lo vuelvo a abrir.
- Otro propietario no puede abrir ese documento.

## Decisiones de esta etapa

1. **Subida directa a Storage.** Vercel limita el cuerpo de una petición a una función a 4,5 MB (documentación de Vercel, consultada el 11 de octubre de 2026) y el máximo provisional de archivos es 10 MB. La API entrega un enlace firmado de subida, el navegador envía el archivo directo a Supabase Storage y luego confirma a la API. Se mantienen los 10 MB.
2. **La clave secreta de Supabase también sirve para Storage.** Variable `SUPABASE_SECRET_KEY` en la API, usada solo por un módulo de almacenamiento que antes comprueba el propietario. Se actualiza la regla 2 de `CLAUDE.md`.
3. **Barra inferior con Inicio e Inmuebles.** Cuentas (etapa 3) y Ajustes (etapa 4) se suman cuando existan.

## Límites asumidos

- **Estado de la unidad:** sin cuentas, la API devuelve `vacant` (sin contrato activo) o `up_to_date` (con contrato). "En mora" y "Pago parcial" llegan en la etapa 5.
- **Detalle del contrato:** sin la sección "Cuentas de cobro" (etapa 3) y sin "Próximo incremento" (el incremento con IPC está fuera del MVP).
- **Arrendatario existente:** `POST /api/leases` acepta `tenant_id`, pero la web de esta etapa solo crea arrendatarios nuevos.
- **Sin borrar:** ningún rol borra inmuebles, unidades, arrendatarios ni contratos. Terminar un contrato lo pasa a `ended`.
- **Dependencias nuevas:** `httpx` en `requirements.txt` (para la API REST de Storage). En la web, por la CLI de shadcn/ui y de uno en uno: `select`, `toggle-group`, `alert-dialog`, `badge`, `switch`.

## Lo que haces tú

| Cuándo | Qué | Dónde |
| --- | --- | --- |
| Antes del paso 6 | Crear el contenedor privado `arrendi` con límite de 10 MB y solo PDF, JPG y PNG (ver `docs/modelo-de-datos.md`) | Supabase, `arrendi-dev` → Storage |
| Antes del paso 6 | Poner `SUPABASE_SECRET_KEY` (clave secreta de `arrendi-dev`) | `apps/api/.env` y variables de `arrendi-api` en Vercel. No la pegues en el chat |
| Después del paso 2 | Aplicar la migración `0002` con `alembic upgrade head` (conexión del agrupador de sesión) | `arrendi-dev`, antes de subir el código que la usa |
| Al final | Probar en el iPhone: subir un PDF, cerrarlo y volver a abrirlo | `arrendi-web.vercel.app` |

## Pasos

### [x] Paso 1. Documentos al día

- `docs/api.md`: la subida en dos pasos. `POST /api/leases/{id}/document/upload-url` devuelve el enlace firmado y la ruta; `POST /api/leases/{id}/document` confirma, valida y guarda. Estado de la unidad `vacant` o `up_to_date`.
- `docs/modelo-de-datos.md`: unicidad `(owner_id, id)` en cada tabla y claves foráneas compuestas; el bucket privado y su creación a mano.
- `CLAUDE.md` (regla 2), `docs/arquitectura.md` (variable `SUPABASE_SECRET_KEY`, bucket, guía de despliegue) y `docs/decisiones.md` (subida directa y el límite de 4,5 MB).
- **Se comprueba:** los documentos no se contradicen entre sí.

### [x] Paso 2. Migración `0002` y modelos

Pruebas primero.

- `apps/api/migrations/versions/0002_properties_units_tenants_leases.py`: las cuatro tablas de `docs/modelo-de-datos.md`, con `check` en los valores cerrados, `rent > 0`, `due_day` de 1 a 28, `end_date > start_date` e índice único parcial `leases(unit_id) where status = 'active'`.
- **Claves foráneas compuestas** `(owner_id, property_id)`, `(owner_id, unit_id)` y `(owner_id, tenant_id)`, con `unique (owner_id, id)` en cada tabla padre. Las claves foráneas saltan la seguridad por fila: sin esto, un propietario podría apuntar a la unidad de otro con solo conocer su id.
- Seguridad por fila activada y forzada, política `owner_isolation` por tabla, disparador `set_updated_at`. `arrendi_api` con select, insert y update; `arrendi_tasks` con select; `revoke` a `anon`, `authenticated` y `service_role`. Mismo patrón que `0001_owners.py`.
- Modelos `app/models/{property,unit,tenant,lease}.py`, exportados en `models/__init__.py`.
- Pruebas en `apps/api/tests/`: `test_properties_tables.py` (restricciones, política, permisos, revocación) y aislamiento con `two_owners`: ni leer, ni modificar, ni apuntar a filas ajenas.
- **Se comprueba:** `pnpm test` y `pnpm lint`. Luego aplicas la migración a `arrendi-dev` y repito la comprobación de aislamiento como `arrendi_api`, como en la etapa 1.

### [x] Paso 3. Inmuebles y unidades en la API

- `app/schemas/{property,unit}.py`, `app/services/properties.py` y `app/routes/properties.py`: `GET` y `POST /api/properties`, `PATCH /api/properties/{id}`, `POST /api/properties/{id}/units` y `PATCH /api/units/{id}`. Se registran en `app/main.py`.
- `GET /api/me`: `onboarding_complete` es verdadero cuando hay al menos un inmueble.
- Reutiliza `OwnerSession`, `AppError` y `ErrorResponse`. Un recurso ajeno responde 404.
- **Se comprueba:** cada ruta nueva con su prueba de aislamiento (fixtures `api`, `make_token` y `two_owners` de `tests/conftest.py`).

### [x] Paso 4. Contratos en la API

Pruebas primero.

- `app/schemas/lease.py`, `app/services/leases.py` y `app/routes/leases.py`: `POST /api/leases`, `GET` y `PATCH /api/leases/{id}`, y `POST /api/leases/{id}/end`.
- 409 `unit_has_active_lease` con mensaje en español. Terminar un contrato ya terminado es 400.
- **Se comprueba:** una unidad no admite dos contratos activos, ni siquiera con dos peticiones simultáneas (lo decide el índice único, no el código); tras terminar, se puede crear otro; aislamiento.

### [ ] Paso 5. Alta guiada en la API

- `POST /api/onboarding` en `app/routes/onboarding.py` y `app/services/onboarding.py`: inmueble, unidades (mínimo una) y, opcionalmente, arrendatario y contrato, en una transacción.
- **Se comprueba:** todo o nada (si el contrato falla, no queda nada creado), sin unidades es 422, aislamiento.

### [ ] Paso 6. Documento del contrato

Antes de empezar: bucket creado y `SUPABASE_SECRET_KEY` puesta (ver "Lo que haces tú").

- `app/storage.py`: una interfaz con la implementación de Supabase Storage (`httpx` y la clave secreta) y un doble para pruebas, inyectable como `get_db_engine` en `dependencies.py`. Consulto la documentación vigente de Storage al implementarlo.
- Ruta del objeto: `{owner_id}/leases/{lease_id}/{nombre}`, con el nombre saneado.
- `upload-url`: comprueba el contrato (seguridad por fila), el tipo declarado y el tamaño (hasta 10 MB), y devuelve el enlace.
- `POST document`: lee del objeto el tamaño y los primeros bytes, valida el tipo real (PDF, JPG o PNG por contenido), guarda `document_path` y `document_uploaded_at`, y borra el archivo anterior al reemplazar. Si no valida, borra el objeto y responde 422.
- `GET document`: comprueba el propietario y devuelve un enlace temporal de pocos minutos.
- **Se comprueba:** un archivo `.pdf` falso, un archivo demasiado grande, el reemplazo, y que otro propietario recibe 404 en las tres rutas.

### [ ] Paso 7. Tipos y base de la web

- `pnpm gen:api`, con los tipos nuevos en `apps/web/lib/api/schema.d.ts`.
- Componentes de shadcn/ui por la CLI y adaptados al tema, con `cn` desde `@/lib/utils`: `select`, `toggle-group`, `alert-dialog`, `badge` (variantes de `StatusBadge`) y `switch`.
- `apps/web/lib/format.ts`: pesos como `$1.000.000` y fechas como `5 oct 2026`, con pruebas, y un campo de dinero que acepta solo dígitos.
- `components/BottomNav.tsx` (Inicio e Inmuebles), un `Header` y el diseño de la aplicación con la barra.
- **Se comprueba:** `pnpm lint` y `pnpm build`; los componentes en tema claro y oscuro.

### [ ] Paso 8. Alta guiada en la web

- `/onboarding/property`, `/onboarding/units` y `/onboarding/lease` (mockups `Alta1`, `Alta2` y `Alta3`), con `OnboardingSteps` y `ActionFooter`. React Hook Form y Zod solo para la forma.
- El estado de los tres pasos vive en el diseño de `/onboarding` y se envía al final con `POST /api/onboarding`. "Agregar los contratos después" lo envía sin contrato. Si hay contrato y archivo, el archivo se sube después de crear (paso 9).
- El inicio lleva al alta mientras `onboarding_complete` sea falso.
- **Se comprueba:** el alta completa en local, en tema claro y oscuro, con una mano en el celular (controles de 44 px o más).

### [ ] Paso 9. Inmuebles y contratos en la web

- `/properties` (mockup `Inmuebles`), con estado vacío y la tarjeta por inmueble: unidades ocupadas y canon total. Además `/properties/new`, `/properties/[id]/edit`, `/properties/[id]/units/new` y `/units/[id]/edit`.
- `/leases/new?unit=...` y `/leases/[id]` (mockup `Contrato`): editar, terminar con `AlertDialog`, aviso si pasó la fecha de fin, y el documento (subir o reemplazar por enlace firmado, y ver con enlace temporal).
- Estados vacío, de carga y de error en cada pantalla. `docs/diseno.md`: se agregan estas rutas al mapa de pantallas.
- **Se comprueba:** en local y en `arrendi-web.vercel.app`, el alta con 3 unidades y 3 contratos; un archivo de más de 4,5 MB sube bien (prueba la subida directa); en el iPhone, subir un PDF, cerrarlo y volver a abrirlo; con otra cuenta, el documento no abre.

### [ ] Paso 10. Cierre

- `pnpm lint`, `pnpm test` y `pnpm build`.
- Casillas de la etapa 2 en `docs/plan.md`. La etapa pasa a 3 solo cuando confirmes los criterios de aceptación.

## Piezas que se reutilizan

- **API:** `app/dependencies.py` (`OwnerSession`, `CurrentUser`), `app/errors.py` (`AppError`, `ErrorResponse`), `app/db.py` (`set_owner_id`), `migrations/versions/0001_owners.py` como molde, y `tests/conftest.py` (`api`, `two_owners`, `make_token`, `bearer`, `admin_engine`).
- **Web:** `lib/api/client.ts` (cliente con token), `components/FormField.tsx`, `components/FormMessage.tsx`, `components/ui/button.tsx` (tamaños 52, 48 y 44), `lib/validation.ts` y `components/auth/AuthScreen.tsx` como referencia de pantalla.

## Riesgos

- La API REST de Storage y la firma de subida se verifican contra la documentación vigente en el paso 6. Si algo difiere, se ajusta `storage.py` sin tocar las rutas.
- La barra inferior y el alta cambian la pantalla de inicio provisional de la etapa 1; el inicio definitivo llega en la etapa 5.
