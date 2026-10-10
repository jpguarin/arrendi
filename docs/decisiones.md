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

- Cómo valida Supabase sus tokens hoy (clave pública o secreto).
- Cómo se configura Google como proveedor en Supabase Auth y cómo vincula dos identidades con el mismo correo.
- Requisitos de Google para publicar la pantalla de consentimiento a usuarios externos.
- Cómo crear roles con y sin salto de políticas en Supabase.
- Cadena de conexión del agrupador de Supabase y su modo.
- Duración máxima y tamaño máximo de cuerpo de una función de Vercel.
- Cómo protege Vercel las llamadas de un Cron Job.
- Configuración vigente de Turborepo y cómo desplegar en Vercel dos proyectos de un monorepo, uno de ellos en Python.
- Configuración actual de Serwist con la versión de Next.js instalada.
- Instalación de shadcn/ui con la versión de Next.js y de Tailwind instaladas, y los nombres vigentes de sus componentes.
- Cómo se enlazan dos proyectos de Vercel del mismo repositorio en las vistas previas.
