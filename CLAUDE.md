# Arrendi

Arrendi es una PWA para que un arrendador pequeño (2 a 10 unidades) genere sus cuentas de cobro cada mes, las envíe por correo y sepa quién le debe. El primer usuario es el propio fundador, con una casa dividida en 3 unidades.

El proyecto está en construcción. La etapa en curso y lo que falta están en `docs/plan.md`.

## Documentos del proyecto

Lee el documento que corresponda antes de tocar esa parte del sistema. Si el código y un documento se contradicen, detente y pregunta.

| Documento | Contenido |
| --- | --- |
| `docs/producto.md` | Alcance del MVP, pantallas y flujos |
| `docs/reglas-de-negocio.md` | Estados de la cuenta, consecutivo, pagos, correos y tarea diaria |
| `docs/modelo-de-datos.md` | Tablas, restricciones, seguridad por fila |
| `docs/api.md` | Rutas de la API y su contrato |
| `docs/arquitectura.md` | Stack, autenticación, despliegue en Vercel, variables de entorno |
| `docs/diseno.md` | Colores, tipografía, componentes y mapa de pantallas |
| `docs/plan.md` | Etapas, tareas y criterios de aceptación |
| `docs/etapa-2.md` | Guía paso a paso de la etapa 2 (inmuebles y contratos), ya cerrada. Sirve de registro de lo decidido |
| `docs/etapa-3.md` | Guía paso a paso de la etapa 3 (cuentas de cobro), ya cerrada. Sirve de registro de lo decidido |
| `docs/etapa-4.md` | Guía paso a paso de la etapa 4 (correo y tarea diaria), ya cerrada. Sirve de registro de lo decidido |
| `docs/etapa-5.md` | Guía paso a paso de la etapa 5 (pagos e inicio), ya cerrada. Sirve de registro de lo decidido |
| `docs/etapa-7.md` | Plan de la etapa 7 (piloto), propuesto y sin empezar |
| `docs/new-brand-design/` | Marca nueva: colores, fuentes, logo y los mocks de la etapa 6. La propuesta elegida es `mockups/propuesta-b-libro.html` |
| `docs/decisiones.md` | Decisiones tomadas, provisionales y pendientes |
| `docs/mockups/` | Marcado de las 10 pantallas diseñadas, como referencia visual |

## Stack

- **API:** Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic.
- **Web:** Next.js (App Router), React, TypeScript, Tailwind CSS, shadcn/ui para los componentes, TanStack Query para los datos de la API, Serwist para la PWA.
- **Datos:** PostgreSQL en Supabase, con seguridad por fila. Supabase Storage para archivos.
- **Acceso:** Supabase Auth, con Google y con correo y contraseña.
- **PDF:** ReportLab. **Correo:** Resend, con plantillas en Jinja2.
- **Pruebas:** pytest en la API, contra un PostgreSQL local instalado con Homebrew. En la web, las funciones puras de `lib/` se prueban con el ejecutor de pruebas de Node (`node --test`), sin dependencias. Playwright de extremo a extremo en `apps/e2e`, todo en local: la web, la API contra la base `arrendi_e2e` y un servidor que hace de Supabase (acceso y almacenamiento).
- **Monorepo:** Turborepo con pnpm.
- **Despliegue:** Vercel, dos proyectos (`arrendi-web` y `arrendi-api`) desde este repositorio. Sin Docker. La guía está en `docs/arquitectura.md`.

## Estructura

Es un monorepo con Turborepo y espacios de trabajo de pnpm. Cada aplicación vive en `apps/`.

```
arrendi/
  apps/
    api/                 FastAPI (proyecto "arrendi-api" en Vercel)
      app/
        main.py          punto de entrada: la instancia `app`
        routes/          una por recurso
        models/          SQLAlchemy
        schemas/         Pydantic
        services/        reglas de negocio
        tasks/           tarea diaria
        email/           envío y plantillas
        pdf/             generación de la cuenta de cobro
      migrations/        Alembic
      tests/             pytest
      package.json       solo scripts, para que Turborepo ejecute la API
      requirements.txt
      vercel.json
    web/                 Next.js (proyecto "arrendi-web" en Vercel)
      app/               pantallas
      components/ui/     componentes de shadcn/ui, adaptados al tema
      components/        componentes propios de Arrendi
      lib/api/           cliente y tipos generados desde OpenAPI
    e2e/                 Playwright
      tests/             las pruebas de extremo a extremo
      fakes/             servidor que hace de Supabase Auth y Storage
      reset_db.py        deja vacía y migrada la base arrendi_e2e
  docs/
  package.json           scripts de la raíz
  pnpm-workspace.yaml
  turbo.json
```

- La API es Python: sus dependencias se instalan con pip en `apps/api/.venv`, no con pnpm. Su `package.json` no tiene dependencias, solo scripts que llaman a ese entorno.
- No crees una carpeta `packages/` hasta que dos aplicaciones necesiten compartir código de verdad.

## Comandos

Estos comandos se crean en la etapa 1. Si alguno cambia, actualiza esta sección en el mismo commit.

```bash
# Preparación, una sola vez (desde la raíz)
pnpm install
cd apps/api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pnpm --filter e2e exec playwright install chromium   # el navegador de las pruebas de extremo a extremo

# Todo el proyecto, con Turborepo (desde la raíz)
pnpm dev             # web en :3000 y API en :8000; la web redirige /api a la API (sin service worker)
pnpm lint            # ruff en la API, eslint en la web
pnpm test            # pytest en la API (necesita el PostgreSQL local encendido) y las pruebas de la web
pnpm build           # compila la web
pnpm e2e             # Playwright: levanta todo en local, en puertos propios (necesita el PostgreSQL local)
pnpm gen:api         # regenera apps/web/lib/api desde el OpenAPI de la API

# Una sola aplicación
pnpm --filter web dev
pnpm --filter api test
pnpm --filter api preview:email   # abre en el navegador los correos con datos de ejemplo

# Migraciones (desde apps/api, con el entorno activado)
alembic upgrade head
alembic revision --autogenerate -m "descripcion"
```

## Reglas que no se rompen

1. **La lógica de negocio vive solo en FastAPI.** En Next.js no se crean rutas de API ni acciones de servidor con reglas de negocio. Next.js dibuja la interfaz y llama a `/api`. Las únicas rutas de Next son las de infraestructura listadas en `docs/decisiones.md` (service worker y regreso del acceso).
2. **Aislamiento por propietario.** Toda tabla lleva `owner_id` y una política de seguridad por fila. Cada transacción de una petición fija `app.owner_id` antes de consultar. El rol que salta las políticas solo se usa en la tarea diaria y en los avisos del correo. La clave secreta de Supabase solo se usa en el módulo de almacenamiento de la API (`app/storage.py`), que antes comprueba el propietario.
3. **Toda funcionalidad nueva incluye la prueba de aislamiento:** un propietario no puede leer ni modificar datos de otro.
4. **El dinero son pesos enteros** (`bigint` en la base, `int` en Python). Nunca decimales ni `float`.
5. **Una cuenta emitida no se edita.** Se anula y se genera otra. Una cuenta con pagos no se anula.
6. **El consecutivo se asigna dentro de una transacción** que bloquea la fila del propietario. Sin saltos ni duplicados.
7. **La tarea diaria es idempotente.** Ejecutarla dos veces el mismo día no crea cuentas ni envía correos repetidos.
8. **Los correos se envían después de confirmar la transacción,** nunca dentro de ella.
9. **Los archivos son privados.** El bucket no tiene acceso público ni políticas para los usuarios. Solo la API lo gobierna: entrega enlaces temporales de subida y de lectura, siempre tras comprobar el propietario.
10. **Los secretos no entran al repositorio.** Van en `.env` (ignorado) y en las variables de Vercel.
11. **Sin Docker.**
12. **Fuera del MVP:** suscripción y límites por plan, WhatsApp, portal del arrendatario, reparto de servicios, pagos en línea, notificaciones push, modo sin conexión con escritura. No los construyas ni dejes código a medias para ellos.

## Convenciones

- **Idioma:** todo el código va en inglés: archivos, carpetas, identificadores, tablas, columnas, rutas de la API y de la web, campos JSON, códigos de error y variables de entorno. Usa los nombres del vocabulario de `docs/modelo-de-datos.md`. En español van los textos de la interfaz, los correos, el PDF, los documentos y los commits.
- **Nombres:** `snake_case` en Python y en la base; tablas en plural; componentes de React en `PascalCase`.
- **Interfaz:** español de Colombia, trato de "tú". Dinero como `$1.000.000`, fechas como `5 oct 2026`.
- **Fechas:** las de negocio son `date`. "Hoy" siempre se calcula en `America/Bogota`, nunca en UTC.
- **Validación:** en la API con Pydantic. La web usa los tipos generados; no se escriben a mano.
- **Datos en la web:** las pantallas leen y escriben con los ganchos de `apps/web/lib/api/queries.ts` (TanStack Query), no con `fetch` ni `useEffect`. Una escritura nueva decide ahí qué actualiza en memoria.
- **Errores de la API:** `{"detail": "mensaje legible, en español", "code": "stable_code"}` con el código HTTP correcto.
- **Componentes:** parte de shadcn/ui (sobre Radix) antes de crear uno desde cero. Se agregan con su CLI, uno por uno y solo cuando hacen falta. Su código queda en `components/ui/` y se adapta al tema de `docs/diseno.md`; no se usan con el aspecto por defecto.
- **Estilos:** solo Tailwind, con las variables del tema. Sin colores ni medidas sueltas en los componentes, y sin otra librería de estilos.
- **Tema claro y oscuro:** toda pantalla y todo componente debe verse bien en ambos. Usa siempre las variables del tema; un color escrito a mano rompe el tema oscuro. Revisa los dos temas antes de dar una pantalla por terminada.
- **Accesibilidad:** controles táctiles de 44 px o más, `label` en cada campo, contraste AA.
- **Commits:** pequeños, en español, un cambio lógico por commit.

## Forma de trabajo

- Trabaja **una etapa a la vez**, en el orden de `docs/plan.md`. No adelantes etapas.
- Antes de escribir código en una etapa, **propón el plan** de archivos y pasos, y espera confirmación.
- En lo delicado (consecutivo, estados, tarea diaria, aislamiento) **escribe primero la prueba**.
- Las pruebas nunca se conectan a un proyecto de Supabase: usan `TEST_DATABASE_URL`, que apunta al PostgreSQL local.
- Una tarea está terminada cuando pasan `pnpm lint`, `pnpm test` y `pnpm build`, y su casilla queda marcada en `docs/plan.md`.
- Si cambias una ruta o un esquema, **regenera los tipos** (`pnpm gen:api`) en el mismo commit.
- Si falta una decisión de producto, **pregunta**. No inventes reglas. Las decisiones provisionales están en `docs/decisiones.md`.
- Antes de configurar Vercel, Supabase o Serwist, **consulta su documentación vigente**: la configuración exacta cambia con frecuencia y este repositorio no la fija.
- No instales dependencias nuevas sin decir para qué sirven.
