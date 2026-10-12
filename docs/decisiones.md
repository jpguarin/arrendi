# Decisiones

## Tomadas

| Decisión | Detalle |
| --- | --- |
| Nombre | Arrendi |
| Cliente inicial | Propietario particular con 2 a 10 unidades |
| Canal | Solo correo en el MVP |
| Plataforma | PWA |
| Backend | FastAPI (Python) |
| Frontend | Next.js (TypeScript), con Tailwind CSS y shadcn/ui |
| Datos, acceso y archivos | Supabase |
| Formas de entrar | Google, y correo con contraseña |
| Despliegue | Todo en Vercel, sin Docker |
| Repositorio | Monorepo con Turborepo y pnpm: `apps/api/`, `apps/web/` y `apps/e2e/` |
| Tema | Claro y oscuro; sigue al sistema por defecto |
| Desarrollo | El fundador, con Claude Code |
| Idioma del código | Inglés: archivos, carpetas, identificadores, tablas, columnas, rutas de la API y de la web, campos JSON y variables de entorno. En español quedan los textos de la interfaz, los correos, el PDF, el mensaje de error que ve el propietario, los documentos y los commits |
| Base de las pruebas | PostgreSQL local con Homebrew; nunca un proyecto de Supabase |
| Componentes | shadcn/ui sobre Radix, inicializado dentro de `apps/web` (sin `packages/ui`) |
| Rutas en Next.js | Solo las que no tienen reglas de negocio: service worker, regreso de Google y confirmación de correo |
| Playwright | Se agrega en la etapa 5, no en la 1 |
| Next.js | Versión 16.4, con Turbopack. Sin `cacheComponents` ni `partialPrefetching`, que la plantilla trae activos: todas las pantallas son privadas y por propietario, y esas opciones obligan a aislar cada lectura de la sesión |
| Suscripción y límites por plan | Fuera del MVP |
| Documento del contrato | Se puede subir; un archivo por contrato |
| Subida de archivos | Directa al almacenamiento con un enlace firmado que entrega la API, porque Vercel limita el cuerpo de una petición a 4,5 MB. La API valida el tipo real al confirmar |
| Clave secreta de Supabase | Solo en el módulo de almacenamiento de la API, además de la tarea diaria, para crear enlaces firmados |
| Cliente HTTP de la API | `httpx2`, el mismo paquete que ya usaban las pruebas; pasa a `requirements.txt` para hablar con Storage. No se usa el SDK de Supabase en la API |
| Datos en la web | TanStack Query con `openapi-react-query`, sobre el cliente con tipos generados. Guarda en memoria lo que respondió la API: al volver a una pantalla se muestra al instante y se refresca por detrás. Solo en memoria, nunca en el dispositivo, y se vacía al cambiar de sesión. Se descartó un almacén global (Zustand, Redux): lo que se guarda son datos del servidor, no estado de la interfaz |
| Barra de navegación | Muestra solo las pantallas que ya existen. Desde la etapa 3 están las cuatro: Inicio, Cuentas, Inmuebles y Ajustes |
| Cuenta mensual a mano | `POST /api/leases/{id}/bills` genera la del mes en curso, con el mismo servicio que usa la tarea diaria |
| Ajustes mínimo en la etapa 3 | Nombre, documento y datos de pago se adelantan a la etapa 3, porque el PDF los necesita. El resto de la configuración sigue en la etapa 4 |
| Cuenta con vencimiento pasado | Nace `overdue`, sin esperar a la tarea diaria |
| Proveedor de correo | Resend, por su API HTTP con `httpx2`, sin SDK |
| Correos hasta la etapa 7 | Todos van al buzón de pruebas (`EMAIL_TEST_INBOX`), también en Producción, con el destinatario real en el asunto. Con el dominio propio, la variable se quita de Producción |
| Cuenta generada a mano | No se envía sola: queda con el botón "Enviar". Solo la tarea diaria envía sola |
| Recordatorios | Solo de cuentas que ya se enviaron, y uno por cuenta en cada ejecución de la tarea |
| Playwright | Corre todo en local: la web, la API contra la base `arrendi_e2e` de PostgreSQL y dos servidores falsos (acceso y almacenamiento). Nunca contra Supabase |
| Deuda de meses anteriores | El inicio la lista en "Por cobrar" y la suma aparte; las cifras del mes no la incluyen |
| Marca y diseño (etapa 6) | Marca de `docs/new-brand-design`. De tres propuestas de interfaz se eligió la B, "Libro": riel de secciones, tablas y panel de detalle. `docs/diseno.md` se reescribió con ese sistema |
| Panel de detalle | Se conservan las rutas: el `layout` de Cuentas y el de Inmuebles dibujan la lista y, al lado, la ruta abierta. Desde el resumen, una cuenta se abre en Cuentas. Se descartó un panel sobre cualquier pantalla con un parámetro en la dirección, que cambiaba los enlaces |
| Fuente del PDF | Sigue Helvetica, aunque la marca pide Inter: no viaja ningún archivo de fuente con la API |
| Gráficas | Hechas con Tailwind, sin librería: una barra de composición y barras por mes no la justifican |
| Mes de un pago | El de su cuenta, no el de la fecha en que se recibió |
| Eliminar un pago | Borrado real, con su comprobante. Es la única tabla donde la API borra |
| PDF | ReportLab con Helvetica, que ya trae; no se empaqueta Figtree |

## Provisionales

Se tomaron para no bloquear el desarrollo. Impleméntalas así, de forma que cambiarlas después sea fácil, y no las extiendas por tu cuenta.

| Tema | Decisión provisional | Alternativa |
| --- | --- | --- |
| Pago mayor al saldo | Se rechaza | Guardarlo como saldo a favor del mes siguiente |
| Prorrateo | No hay; la primera cuenta es completa | Cobrar proporcional el mes incompleto |
| Contrato que llega a su fecha de fin | Sigue activo hasta que el propietario lo termine | Renovación o terminación automática |
| Cuentas anuladas en el listado | Ocultas, visibles con un filtro | Siempre visibles |
| Tamaño máximo de archivos | 10 MB | Otro valor, según el límite de Vercel |
| Día de pago | Entre 1 y 28 | Admitir 29 a 31 con ajuste al último día |
| Envío de cuentas | Día fijo del mes por propietario; aprobación previa por contrato | Opción "N días antes del vencimiento" |
| PDF de cuenta anulada | Se reemplaza por una versión marcada "ANULADA" | Conservar ambas versiones |

## Pendientes

Hay que resolverlas antes de la etapa indicada.

| Decisión | Antes de |
| --- | --- |
| Dominio de envío del correo | Etapa 7 |
| Plan de Vercel: confirmar si el gratuito admite uso comercial | Etapa 7 |
| Verificar dominio y registro de marca de Arrendi ante la SIC | Etapa 7 |
| Confirmar con un contador si basta la cuenta de cobro o hará falta factura electrónica | Etapa 7 |
| Texto de la política de tratamiento de datos | Etapa 7 |
| Precios y límites de los planes | Después del MVP |

## Por verificar en documentación vigente

No son decisiones de producto, sino datos técnicos que cambian y que este repositorio no fija:

- Requisitos de Google para publicar la pantalla de consentimiento a usuarios externos.
- Si la protección de despliegues de Vercel bloquea la redirección de la web hacia la API de vista previa.

### Verificado el 11 de octubre de 2026

- Vercel llama al Cron Job con `Authorization: Bearer <CRON_SECRET>`, no reintenta si falla y puede, rara vez, llamar dos veces o ninguna: la tarea debe ser idempotente y recuperarse sola.
- Resend, comprobado de extremo a extremo contra `arrendi-dev`: un correo a `bounced@resend.dev` (su dirección para simular rebotes) genera el aviso `email.bounced`, la API desplegada verifica su firma y la notificación queda `bounced`. El panel de Resend no tiene un botón para enviar un evento de prueba.
- El Cron Job de Vercel, lanzado a mano desde el panel, responde 200 en `arrendi-api`.
- Resend: `POST https://api.resend.com/emails` con adjuntos en Base64 y cabecera `Idempotency-Key` (vale 24 horas). Sus avisos llegan firmados con las cabeceras `svix-id`, `svix-timestamp` y `svix-signature`.
- Supabase Storage acepta desde el navegador el `PUT` de subida con `Content-Type` (CORS: cualquier origen), comprobado con la petición previa contra `arrendi-dev`.
- Supabase Storage, probado contra `arrendi-dev`: el enlace firmado de subida acepta un `PUT` con el archivo como cuerpo y sin claves; no sirve para sobrescribir un archivo que ya existe; el contenedor rechaza tipos no permitidos y más de 10 MB; un archivo de 7 MB sube bien; sin enlace no hay acceso.
- Una función de Vercel admite un cuerpo de petición de hasta 4,5 MB (error 413 si lo supera) y, con Fluid compute, hasta 300 s de duración en el plan Hobby.

### Verificado el 10 de octubre de 2026

El detalle está en `docs/arquitectura.md` y `docs/modelo-de-datos.md`.

- Supabase valida sus tokens con claves asimétricas publicadas por JWKS.
- Supabase vincula sola la identidad de Google a una cuenta con el mismo correo verificado.
- El usuario `postgres` de Supabase puede crear un rol con `bypassrls` (`arrendi_tasks`).
- El agrupador de Supabase se usa en modo transacción, sin sentencias preparadas.
- Supabase retira las claves `anon` y `service_role` a finales de 2026.
- Vercel detecta la instancia `app` de FastAPI en `app/main.py` y enlaza las vistas previas con "Related Projects".
- Turborepo usa la clave `tasks` y filtra las variables de entorno por defecto.
- Serwist con Turbopack sirve el service worker desde una ruta de Next.
- En Next.js 16, `middleware.ts` se llama `proxy.ts`.
