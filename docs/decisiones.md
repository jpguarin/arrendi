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
| Proveedor de correo y dominio de envío | Etapa 4 |
| Plan de Vercel: confirmar si el gratuito admite uso comercial | Etapa 6 |
| Verificar dominio y registro de marca de Arrendi ante la SIC | Etapa 6 |
| Confirmar con un contador si basta la cuenta de cobro o hará falta factura electrónica | Etapa 6 |
| Texto de la política de tratamiento de datos | Etapa 6 |
| Precios y límites de los planes | Después del MVP |

## Por verificar en documentación vigente

No son decisiones de producto, sino datos técnicos que cambian y que este repositorio no fija:

- Requisitos de Google para publicar la pantalla de consentimiento a usuarios externos.
- Que el usuario administrador de Supabase puede crear un rol con `bypassrls` (se comprueba al crear `arrendi_tasks`).
- Duración máxima y tamaño máximo de cuerpo de una función de Vercel.
- Cómo protege Vercel las llamadas de un Cron Job.
- Si la protección de despliegues de Vercel bloquea la redirección de la web hacia la API de vista previa.

### Verificado el 10 de octubre de 2026

El detalle está en `docs/arquitectura.md` y `docs/modelo-de-datos.md`.

- Supabase valida sus tokens con claves asimétricas publicadas por JWKS.
- Supabase vincula sola la identidad de Google a una cuenta con el mismo correo verificado.
- El agrupador de Supabase se usa en modo transacción, sin sentencias preparadas.
- Supabase retira las claves `anon` y `service_role` a finales de 2026.
- Vercel detecta la instancia `app` de FastAPI en `app/main.py` y enlaza las vistas previas con "Related Projects".
- Turborepo usa la clave `tasks` y filtra las variables de entorno por defecto.
- Serwist con Turbopack sirve el service worker desde una ruta de Next.
- En Next.js 16, `middleware.ts` se llama `proxy.ts`.
