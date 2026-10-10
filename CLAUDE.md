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
| `docs/decisiones.md` | Decisiones tomadas, provisionales y pendientes |
| `docs/mockups/` | Marcado de las 10 pantallas diseñadas, como referencia visual |

## Stack

- **API:** Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic.
- **Web:** Next.js (App Router), React, TypeScript, Tailwind CSS, shadcn/ui para los componentes, Serwist para la PWA.
- **Datos:** PostgreSQL en Supabase, con seguridad por fila. Supabase Storage para archivos.
- **Acceso:** Supabase Auth, con Google y con correo y contraseña.
- **PDF:** ReportLab. **Correo:** proveedor transaccional (por elegir).
- **Pruebas:** pytest en la API, Playwright de extremo a extremo.
- **Monorepo:** Turborepo con pnpm.
- **Despliegue:** Vercel, dos proyectos (`web` y `api`) desde este repositorio. Sin Docker.

## Estructura

Es un monorepo con Turborepo y espacios de trabajo de pnpm. Cada aplicación vive en `apps/`.

```
arrendi/
  apps/
    api/                 FastAPI (proyecto "api" en Vercel)
      app/
        main.py          punto de entrada: la instancia `app`
        rutas/           una por recurso
        modelos/         SQLAlchemy
        esquemas/        Pydantic
        servicios/       reglas de negocio
        tareas/          tarea diaria
        correo/          envío y plantillas
        pdf/             generación de la cuenta de cobro
      migraciones/       Alembic
      pruebas/           pytest
      package.json       solo scripts, para que Turborepo ejecute la API
      requirements.txt
      vercel.json
    web/                 Next.js (proyecto "web" en Vercel)
      app/               pantallas
      components/ui/     componentes de shadcn/ui, adaptados al tema
      components/        componentes propios de Arrendi
      lib/api/           cliente y tipos generados desde OpenAPI
    e2e/                 Playwright
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

# Todo el proyecto, con Turborepo (desde la raíz)
pnpm dev             # web en :3000 y API en :8000; la web redirige /api a la API
pnpm lint            # ruff en la API, eslint en la web
pnpm test            # pytest en la API
pnpm build           # compila la web
pnpm gen:api         # regenera apps/web/lib/api desde el OpenAPI de la API
pnpm e2e             # Playwright

# Una sola aplicación
pnpm --filter web dev
pnpm --filter api test

# Migraciones (desde apps/api, con el entorno activado)
alembic upgrade head
alembic revision --autogenerate -m "descripcion"
```

## Reglas que no se rompen

1. **La lógica de negocio vive solo en FastAPI.** En Next.js no se crean rutas de API ni acciones de servidor con reglas de negocio. Next.js dibuja la interfaz y llama a `/api`.
2. **Aislamiento por propietario.** Toda tabla lleva `propietario_id` y una política de seguridad por fila. Cada transacción de una petición fija `app.propietario_id` antes de consultar. La clave de servicio y el rol que salta las políticas solo se usan en la tarea diaria y en los avisos del correo.
3. **Toda funcionalidad nueva incluye la prueba de aislamiento:** un propietario no puede leer ni modificar datos de otro.
4. **El dinero son pesos enteros** (`bigint` en la base, `int` en Python). Nunca decimales ni `float`.
5. **Una cuenta emitida no se edita.** Se anula y se genera otra. Una cuenta con pagos no se anula.
6. **El consecutivo se asigna dentro de una transacción** que bloquea la fila del propietario. Sin saltos ni duplicados.
7. **La tarea diaria es idempotente.** Ejecutarla dos veces el mismo día no crea cuentas ni envía correos repetidos.
8. **Los correos se envían después de confirmar la transacción,** nunca dentro de ella.
9. **Los archivos son privados.** Solo la API lee y escribe en el almacenamiento, y entrega enlaces temporales tras comprobar el propietario.
10. **Los secretos no entran al repositorio.** Van en `.env` (ignorado) y en las variables de Vercel.
11. **Sin Docker.**
12. **Fuera del MVP:** suscripción y límites por plan, WhatsApp, portal del arrendatario, reparto de servicios, pagos en línea, notificaciones push, modo sin conexión con escritura. No los construyas ni dejes código a medias para ellos.

## Convenciones

- **Idioma:** el dominio va en español (tablas, columnas, rutas, esquemas, textos de la interfaz). Los nombres técnicos genéricos pueden ir en inglés.
- **Nombres:** `snake_case` en Python y en la base; tablas en plural; componentes de React en `PascalCase`.
- **Interfaz:** español de Colombia, trato de "tú". Dinero como `$1.000.000`, fechas como `5 oct 2026`.
- **Fechas:** las de negocio son `date`. "Hoy" siempre se calcula en `America/Bogota`, nunca en UTC.
- **Validación:** en la API con Pydantic. La web usa los tipos generados; no se escriben a mano.
- **Errores de la API:** `{"detalle": "mensaje legible", "codigo": "codigo_estable"}` con el código HTTP correcto.
- **Componentes:** parte de shadcn/ui antes de crear uno desde cero. Se agregan con su CLI, uno por uno y solo cuando hacen falta. Su código queda en `components/ui/` y se adapta al tema de `docs/diseno.md`; no se usan con el aspecto por defecto.
- **Estilos:** solo Tailwind, con las variables del tema. Sin colores ni medidas sueltas en los componentes, y sin otra librería de estilos.
- **Tema claro y oscuro:** toda pantalla y todo componente debe verse bien en ambos. Usa siempre las variables del tema; un color escrito a mano rompe el tema oscuro. Revisa los dos temas antes de dar una pantalla por terminada.
- **Accesibilidad:** controles táctiles de 44 px o más, `label` en cada campo, contraste AA.
- **Commits:** pequeños, en español, un cambio lógico por commit.

## Forma de trabajo

- Trabaja **una etapa a la vez**, en el orden de `docs/plan.md`. No adelantes etapas.
- Antes de escribir código en una etapa, **propón el plan** de archivos y pasos, y espera confirmación.
- En lo delicado (consecutivo, estados, tarea diaria, aislamiento) **escribe primero la prueba**.
- Una tarea está terminada cuando pasan `pnpm lint`, `pnpm test` y `pnpm build`, y su casilla queda marcada en `docs/plan.md`.
- Si cambias una ruta o un esquema, **regenera los tipos** (`pnpm gen:api`) en el mismo commit.
- Si falta una decisión de producto, **pregunta**. No inventes reglas. Las decisiones provisionales están en `docs/decisiones.md`.
- Antes de configurar Vercel, Supabase o Serwist, **consulta su documentación vigente**: la configuración exacta cambia con frecuencia y este repositorio no la fija.
- No instales dependencias nuevas sin decir para qué sirven.
