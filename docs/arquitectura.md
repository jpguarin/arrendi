# Arquitectura

## Componentes

```
Propietario (PWA o navegador) ─┐
                               ├──> Web: Next.js ──/api──> API: FastAPI ──┬──> PostgreSQL (Supabase)
Cron Job de Vercel ────────────┘                                          ├──> Archivos privados (Supabase Storage)
                                                                          └──> Proveedor de correo ──> Arrendatario
```

Solo la API toca la base de datos, los archivos y el correo. La única excepción es el inicio de sesión, que la web hace directamente contra Supabase Auth.

## Stack

| Capa | Elección | Motivo |
| --- | --- | --- |
| Lenguajes | Python en la API y TypeScript en la web | Python abre la puerta a lectura de comprobantes y análisis más adelante |
| API | FastAPI con Pydantic | Valida los datos y documenta la API sola con OpenAPI |
| Acceso a datos | SQLAlchemy 2 con migraciones en Alembic | Cambios de esquema versionados y repetibles |
| Web | Next.js con React | Interfaz instalable sin tiendas de aplicaciones |
| Estilos y componentes | Tailwind CSS y shadcn/ui | Componentes accesibles cuyo código queda en el repositorio y se adapta al diseño |
| PWA | Serwist (`@serwist/turbopack`) y el manifiesto de Next.js | |
| Cliente de la API | Tipos generados desde OpenAPI (`openapi-typescript`), usados con `openapi-fetch` | La web falla al compilar si la API cambia |
| Base de datos | PostgreSQL en Supabase | Seguridad por fila para aislar a cada propietario |
| Autenticación | Supabase Auth, con Google y con correo y contraseña; FastAPI verifica el token | Acceso con Google, registro, confirmación y recuperación ya resueltos |
| Archivos | Supabase Storage, privado | Enlaces temporales |
| Correo | Proveedor transaccional (por elegir) | Dominio propio y aviso de rebotes |
| PDF | ReportLab | Python puro: se instala con pip |
| Tema | `next-themes`, claro y oscuro | Sigue al sistema y recuerda la elección |
| Monorepo | Turborepo con pnpm | Un solo comando para levantar, probar y compilar todo |
| Tareas programadas | Cron Job de Vercel | Una ejecución diaria |
| Hosting | Vercel, dos proyectos | Sin servidores ni Docker |
| Pruebas | pytest contra un PostgreSQL local; Playwright desde la etapa 5 | |
| Monitoreo | Sentry | |

## Autenticación

Hay dos formas de entrar, ambas gestionadas por Supabase Auth:

- **Con Google:** botón "Continuar con Google". Es la opción principal en la pantalla de acceso.
- **Con correo y contraseña:** con confirmación del correo y recuperación de contraseña.

Para la API no hay diferencia: en ambos casos recibe el mismo tipo de token.

1. La web usa el cliente de Supabase para el acceso con Google, el registro con correo, el inicio de sesión y la recuperación de contraseña.
2. Supabase entrega un token de acceso. La web lo envía en `Authorization: Bearer ...` en cada llamada a `/api`.
3. FastAPI valida la firma y la vigencia del token en una dependencia común, y de él obtiene el id del usuario (`sub`), que es el `owner_id`.
4. Esa misma dependencia abre la transacción y fija `app.owner_id`.

### Validación del token

Consultado en la documentación de Supabase el 10 de octubre de 2026:

- Los proyectos deben usar **claves de firma asimétricas** (ES256). Se activan en la configuración de JWT del panel de Supabase, en cada proyecto.
- La API descarga las claves públicas de `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, las guarda en memoria unos minutos y verifica la firma localmente.
- Comprueba además `exp` y que `iss` sea `{SUPABASE_URL}/auth/v1`.
- No se usa el secreto compartido (HS256): Supabase lo desaconseja. Si el proyecto no tiene claves asimétricas, el JWKS sale vacío y la API rechaza todos los tokens.

### Sesión en la web

- La web usa `@supabase/ssr`, con la sesión en cookies.
- `apps/web/proxy.ts` refresca la sesión en cada petición con `getClaims()` y manda a `/login` a quien no la tiene. En Next.js 16 este archivo reemplaza a `middleware.ts`.
- Hay dos rutas de Next que solo completan el acceso, sin reglas de negocio: `/auth/callback` (regreso de Google) y `/auth/confirm` (enlace del correo de confirmación o de recuperación).
- El registro con correo pide el nombre y lo guarda en los metadatos del usuario de Supabase, para que el token lo traiga igual que con Google.
- El cliente de la API (`apps/web/lib/api/client.ts`) agrega el token a cada llamada. Si la API responde 401, cierra la sesión y vuelve a `/login`.

### Configuración de Supabase Auth

Se hace a mano en el panel, en cada proyecto de Supabase:

1. **Claves de firma asimétricas:** activarlas en la configuración de JWT.
2. **URL del sitio y direcciones de retorno:** la URL del sitio es la de la aplicación en ese entorno. En las direcciones de retorno permitidas van `http://localhost:3000/**`, el dominio de producción y el patrón de las vistas previas de Vercel.
3. **Plantillas de correo:** cambiar el enlace de dos plantillas para que apunten a `/auth/confirm` con el código de un solo uso. Así el enlace funciona aunque se abra en otro navegador, que es lo normal al abrir el correo en el celular.
   - Confirmar registro: `{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=email`
   - Recuperar contraseña: `{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=recovery`

   Con las plantillas por defecto el enlace solo funciona en el mismo navegador donde se pidió.
4. **Confirmación del correo:** activada, para que el registro con correo exija confirmar.
5. **Google como proveedor:**
   - En Google Cloud, crear la pantalla de consentimiento (solo correo, perfil y `openid`) y un cliente OAuth de tipo "aplicación web".
   - En ese cliente, la URI de redirección autorizada es la de Supabase: `https://<ref>.supabase.co/auth/v1/callback`. No es la de Arrendi.
   - En Supabase, activar el proveedor Google y pegar el id y el secreto del cliente. El secreto vive en Supabase, no en este repositorio.
   - La web vuelve de Google por `/auth/callback`, que ya está cubierta por las direcciones de retorno del punto 2.

### Acceso con Google

- Se configura como proveedor en Supabase Auth, con un cliente OAuth creado en Google Cloud. Las credenciales de Google se guardan en Supabase, no en este repositorio.
- Solo se piden los permisos básicos: correo, nombre y foto. Arrendi no lee el Gmail del propietario ni envía correos desde su cuenta.
- La primera vez que alguien entra con Google, `GET /api/me` crea su fila en `owners` con el nombre y el correo que trae el token.
- Quien entra con Google no tiene que confirmar el correo: Google ya lo verificó.
- La autorización de tratamiento de datos se pide igual, en el primer ingreso, antes del alta.
- **Misma persona, dos métodos:** si alguien se registró con correo y contraseña y después entra con Google usando ese mismo correo, debe llegar a la misma cuenta, no a una nueva. Supabase vincula la identidad de Google a la cuenta existente de forma automática, siempre que el correo esté verificado. Se cubre con una prueba manual.
- **En la PWA instalada:** el acceso con Google sale a una página de Google y vuelve. Hay que probarlo con la aplicación instalada en Android y en iPhone, donde el regreso a la aplicación es el punto delicado.
- **Entornos:** las direcciones de retorno permitidas incluyen local, vistas previas y producción.

## Conexión a la base de datos

- La API corre en funciones, que no mantienen conexiones abiertas entre peticiones.
- Se conecta a través del agrupador de conexiones de Supabase en **modo transacción** (puerto 6543), sin reserva propia de conexiones en SQLAlchemy (`NullPool`).
- El modo transacción no admite sentencias preparadas: el driver (`psycopg`) se configura con ellas desactivadas.
- Un rol propio se conecta por el agrupador con el usuario `arrendi_api.<ref-del-proyecto>`. El servidor del agrupador se copia del panel de Supabase.
- `app.owner_id` se fija con alcance de transacción. Es obligatorio con un agrupador: ver `docs/modelo-de-datos.md`.
- Las migraciones se ejecutan con la conexión directa, desde el computador del desarrollador. La conexión directa es solo IPv6; si la red no lo tiene, se usa el agrupador en modo sesión (puerto 5432).
- La API usa SQLAlchemy de forma síncrona.

## Despliegue en Vercel

Dos proyectos conectados a este repositorio, cada uno con su carpeta raíz dentro del monorepo:

| Proyecto | Carpeta raíz | Qué es |
| --- | --- | --- |
| `web` | `apps/web/` | Next.js |
| `api` | `apps/api/` | FastAPI, como una sola función de Vercel |

- **Punto de entrada de la API:** Vercel detecta la instancia `app` en `apps/api/app/main.py`.
- **Un solo dominio:** Next.js redirige `/api/:ruta*` hacia el proyecto `api` con una regla `rewrites`. El navegador nunca ve dos orígenes, así que no hace falta CORS.
- **Vistas previas:** cada rama genera un despliegue de vista previa en ambos proyectos. La web de vista previa apunta a la API de la misma rama mediante "Related Projects" de Vercel: `relatedProjects` en `apps/web/vercel.json` y el paquete `@vercel/related-projects`. `API_URL` es el valor por defecto, para local. Ambas usan la base de datos de desarrollo.
- **Proyectos sin cambios:** Vercel omite el despliegue del proyecto que un commit no toca. Requiere que cada aplicación tenga un `package.json` con nombre único; el de `apps/api` lo cumple.
- **Tarea diaria:** un Cron Job en `apps/api/vercel.json` llama a `/api/cron/daily` a las 11:00 UTC, que son las 6:00 a. m. en Colombia.
- **Tiempo máximo:** cada llamada tiene un límite de duración, configurable en `vercel.json` con la clave `functions` y la entrada `app/main.py`. La tarea diaria procesa por lotes.

### Límites conocidos

Consultados en la documentación de Vercel el 10 de octubre de 2026:

- En el plan Hobby, un Cron Job solo puede correr una vez al día y arranca con hasta 59 minutos de margen.
- El paquete de la API puede pesar hasta 500 MB.

Por verificar: si el plan Hobby admite uso comercial, la duración máxima por llamada, el tamaño máximo del cuerpo de una petición, y si la protección de despliegues bloquea la redirección de la web hacia la API de vista previa.

Fuentes: <https://vercel.com/docs/frameworks/backend/fastapi>, <https://vercel.com/docs/monorepos> y <https://vercel.com/docs/cron-jobs/usage-and-pricing>.

## Entornos

| Entorno | Web y API | Base de datos | Correo |
| --- | --- | --- | --- |
| Local | En el computador, con `pnpm dev` | Proyecto Supabase de desarrollo | Desviado a un buzón de pruebas |
| Pruebas | pytest en el computador | PostgreSQL local, con Homebrew | Doble de pruebas |
| Vista previa | Vercel, por rama | Proyecto Supabase de desarrollo | Desviado a un buzón de pruebas |
| Producción | Vercel | Proyecto Supabase de producción | Real |

Fuera de producción, la API nunca envía correo a arrendatarios reales: todo destinatario se reemplaza por el buzón de pruebas.

## Variables de entorno

### API (`apps/api/.env`)

| Variable | Para qué |
| --- | --- |
| `ENVIRONMENT` | `local`, `preview` o `production` |
| `DATABASE_URL` | Conexión de `arrendi_api` por el agrupador |
| `DATABASE_URL_TASKS` | Conexión de `arrendi_tasks` por el agrupador |
| `DATABASE_URL_MIGRATIONS` | Conexión directa, solo para Alembic |
| `TEST_DATABASE_URL` | PostgreSQL local para las pruebas, con un usuario que pueda crear roles |
| `SUPABASE_URL` | URL del proyecto |
| `SUPABASE_SECRET_KEY` | Clave secreta (`sb_secret_...`), para el almacenamiento desde la API |
| `STORAGE_BUCKET` | Nombre del contenedor privado |
| `EMAIL_API_KEY` | Clave del proveedor de correo |
| `EMAIL_SENDER` | Dirección de envío |
| `EMAIL_TEST_INBOX` | Destinatario forzado fuera de producción |
| `EMAIL_WEBHOOK_SECRET` | Firma de los avisos del proveedor |
| `CRON_SECRET` | Secreto de la tarea diaria |
| `SENTRY_DSN` | Monitoreo |

### Web (`apps/web/.env.local`)

| Variable | Para qué |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | URL del proyecto |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Clave publicable de Supabase (`sb_publishable_...`) |
| `API_URL` | Destino de la redirección de `/api` |
| `NEXT_PUBLIC_SENTRY_DSN` | Monitoreo |

Solo las variables con prefijo `NEXT_PUBLIC_` llegan al navegador. La clave secreta nunca va en la web.

Supabase retira las claves antiguas `anon` y `service_role` a finales de 2026; por eso se usan la publicable y la secreta.

## PWA

- **Instalable:** manifiesto con nombre, íconos y colores, y apertura a pantalla completa.
- **Service worker:** guarda la estructura de la aplicación para que abra rápido y muestre una pantalla clara sin conexión. Con Turbopack, Serwist no lo compila a un archivo en `public/`: lo sirve una ruta de Next (`app/serwist/[path]/route.ts`) en `/serwist/sw.js`. Esa ruta no tiene reglas de negocio.
- **Sin conexión:** se puede abrir la aplicación, pero consultar y registrar requiere conexión.
- **Nada sensible en el dispositivo:** las respuestas de `/api` y los archivos no se guardan en caché.
- **Tema:** el color de la barra del sistema (`theme-color`) cambia con el tema claro u oscuro.
- **Cámara:** el comprobante y el contrato se adjuntan desde la cámara o los archivos del celular.
- **Actualizaciones:** al publicar una versión nueva, la aplicación avisa y se recarga.

## PDF

- Una sola plantilla, construida con ReportLab. Siempre en claro: el PDF no depende del tema de la aplicación.
- Contiene: consecutivo, fecha de emisión, datos del propietario y del arrendatario, conceptos, total, vencimiento y datos de pago.
- Se genera al emitir la cuenta y se guarda en el almacenamiento.
- Al anular, se genera una segunda versión con la marca "ANULADA" y reemplaza al archivo.

## Correo

- Dominio propio con SPF, DKIM y DMARC.
- Los correos se diseñan en claro y deben seguir siendo legibles si el cliente de correo los oscurece.
- Plantillas en Jinja2 dentro de `apps/api/app/email/templates/`, con versión HTML y de texto.
- El proveedor se oculta tras una interfaz (`send(message) -> provider_id`) para poder cambiarlo y para usar un doble en las pruebas.
