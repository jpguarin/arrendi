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
| PWA | Serwist y el manifiesto de Next.js | |
| Cliente de la API | Tipos generados desde OpenAPI (`openapi-typescript`) | La web falla al compilar si la API cambia |
| Base de datos | PostgreSQL en Supabase | Seguridad por fila para aislar a cada propietario |
| Autenticación | Supabase Auth, con Google y con correo y contraseña; FastAPI verifica el token | Acceso con Google, registro, confirmación y recuperación ya resueltos |
| Archivos | Supabase Storage, privado | Enlaces temporales |
| Correo | Proveedor transaccional (por elegir) | Dominio propio y aviso de rebotes |
| PDF | ReportLab | Python puro: se instala con pip |
| Tema | `next-themes`, claro y oscuro | Sigue al sistema y recuerda la elección |
| Monorepo | Turborepo con pnpm | Un solo comando para levantar, probar y compilar todo |
| Tareas programadas | Cron Job de Vercel | Una ejecución diaria |
| Hosting | Vercel, dos proyectos | Sin servidores ni Docker |
| Pruebas | pytest y Playwright | |
| Monitoreo | Sentry | |

## Autenticación

Hay dos formas de entrar, ambas gestionadas por Supabase Auth:

- **Con Google:** botón "Continuar con Google". Es la opción principal en la pantalla de acceso.
- **Con correo y contraseña:** con confirmación del correo y recuperación de contraseña.

Para la API no hay diferencia: en ambos casos recibe el mismo tipo de token.

1. La web usa el cliente de Supabase para el acceso con Google, el registro con correo, el inicio de sesión y la recuperación de contraseña.
2. Supabase entrega un token de acceso. La web lo envía en `Authorization: Bearer ...` en cada llamada a `/api`.
3. FastAPI valida la firma y la vigencia del token en una dependencia común, y de él obtiene el id del usuario, que es el `propietario_id`.
4. Esa misma dependencia abre la transacción y fija `app.propietario_id`.

Verifica en la documentación vigente de Supabase cómo se validan hoy sus tokens (clave pública por JWKS o secreto compartido) antes de implementar el paso 3.

### Acceso con Google

- Se configura como proveedor en Supabase Auth, con un cliente OAuth creado en Google Cloud. Las credenciales de Google se guardan en Supabase, no en este repositorio.
- Solo se piden los permisos básicos: correo, nombre y foto. Arrendi no lee el Gmail del propietario ni envía correos desde su cuenta.
- La primera vez que alguien entra con Google, `GET /api/yo` crea su fila en `propietarios` con el nombre y el correo que trae el token.
- Quien entra con Google no tiene que confirmar el correo: Google ya lo verificó.
- La autorización de tratamiento de datos se pide igual, en el primer ingreso, antes del alta.
- **Misma persona, dos métodos:** si alguien se registró con correo y contraseña y después entra con Google usando ese mismo correo, debe llegar a la misma cuenta, no a una nueva. Verifica cómo vincula Supabase las identidades y cúbrelo con una prueba manual.
- **En la PWA instalada:** el acceso con Google sale a una página de Google y vuelve. Hay que probarlo con la aplicación instalada en Android y en iPhone, donde el regreso a la aplicación es el punto delicado.
- **Entornos:** las direcciones de retorno permitidas incluyen local, vistas previas y producción.

## Conexión a la base de datos

- La API corre en funciones, que no mantienen conexiones abiertas entre peticiones.
- Se conecta a través del agrupador de conexiones de Supabase, sin reserva propia de conexiones en SQLAlchemy (`NullPool`).
- `app.propietario_id` se fija con alcance de transacción. Es obligatorio con un agrupador: ver `docs/modelo-de-datos.md`.
- Las migraciones se ejecutan con la conexión directa, desde el computador del desarrollador.

## Despliegue en Vercel

Dos proyectos conectados a este repositorio, cada uno con su carpeta raíz dentro del monorepo:

| Proyecto | Carpeta raíz | Qué es |
| --- | --- | --- |
| `web` | `apps/web/` | Next.js |
| `api` | `apps/api/` | FastAPI, como una sola función de Vercel |

- **Punto de entrada de la API:** Vercel detecta la instancia `app` en `apps/api/app/main.py`.
- **Un solo dominio:** Next.js redirige `/api/:ruta*` hacia el proyecto `api` con una regla `rewrites`. El navegador nunca ve dos orígenes, así que no hace falta CORS.
- **Vistas previas:** cada rama genera un despliegue de vista previa en ambos proyectos. La web de vista previa debe apuntar a la API de vista previa y a la base de datos de desarrollo.
- **Tarea diaria:** un Cron Job en `apps/api/vercel.json` llama a `/api/cron/diario` a las 11:00 UTC, que son las 6:00 a. m. en Colombia.
- **Tiempo máximo:** cada llamada tiene un límite de duración, configurable en `vercel.json`. La tarea diaria procesa por lotes.

### Límites conocidos

Consultados en la documentación de Vercel el 10 de octubre de 2026:

- En el plan Hobby, un Cron Job solo puede correr una vez al día y arranca con hasta 59 minutos de margen.
- El paquete de la API puede pesar hasta 500 MB.

Por verificar: si el plan Hobby admite uso comercial, la duración máxima por llamada y el tamaño máximo del cuerpo de una petición.

Fuentes: <https://vercel.com/docs/frameworks/backend/fastapi> y <https://vercel.com/docs/cron-jobs/usage-and-pricing>.

## Entornos

| Entorno | Web y API | Base de datos | Correo |
| --- | --- | --- | --- |
| Local | En el computador, cada una con su comando | Proyecto Supabase de desarrollo | Desviado a un buzón de pruebas |
| Vista previa | Vercel, por rama | Proyecto Supabase de desarrollo | Desviado a un buzón de pruebas |
| Producción | Vercel | Proyecto Supabase de producción | Real |

Fuera de producción, la API nunca envía correo a arrendatarios reales: todo destinatario se reemplaza por el buzón de pruebas.

## Variables de entorno

### API (`apps/api/.env`)

| Variable | Para qué |
| --- | --- |
| `ENTORNO` | `local`, `preview` o `produccion` |
| `DATABASE_URL` | Conexión de `arrendi_api` por el agrupador |
| `DATABASE_URL_TAREAS` | Conexión de `arrendi_tareas` por el agrupador |
| `DATABASE_URL_MIGRACIONES` | Conexión directa, solo para Alembic |
| `SUPABASE_URL` | URL del proyecto |
| `SUPABASE_SERVICE_ROLE_KEY` | Acceso al almacenamiento desde la API |
| `SUPABASE_JWT_SECRET` | Validación del token, si aplica el método de secreto |
| `STORAGE_BUCKET` | Nombre del contenedor privado |
| `CORREO_API_KEY` | Clave del proveedor de correo |
| `CORREO_REMITENTE` | Dirección de envío |
| `CORREO_BUZON_PRUEBAS` | Destinatario forzado fuera de producción |
| `CORREO_WEBHOOK_SECRETO` | Firma de los avisos del proveedor |
| `CRON_SECRET` | Secreto de la tarea diaria |
| `SENTRY_DSN` | Monitoreo |

### Web (`apps/web/.env.local`)

| Variable | Para qué |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | URL del proyecto |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clave pública de Supabase |
| `API_URL` | Destino de la redirección de `/api` |
| `NEXT_PUBLIC_SENTRY_DSN` | Monitoreo |

Solo las variables con prefijo `NEXT_PUBLIC_` llegan al navegador. La clave de servicio nunca va en la web.

## PWA

- **Instalable:** manifiesto con nombre, íconos y colores, y apertura a pantalla completa.
- **Service worker:** guarda la estructura de la aplicación para que abra rápido y muestre una pantalla clara sin conexión.
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
- Plantillas en Jinja2 dentro de `apps/api/app/correo/plantillas/`, con versión HTML y de texto.
- El proveedor se oculta tras una interfaz (`enviar(correo) -> id_proveedor`) para poder cambiarlo y para usar un doble en las pruebas.
