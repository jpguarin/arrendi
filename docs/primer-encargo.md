# Cómo empezar con Claude Code

## Antes de abrir Claude Code

Esto lo haces tú, porque requiere tus cuentas:

1. Crea un repositorio vacío en GitHub llamado `arrendi` y clónalo en tu computador.
2. Copia dentro el contenido de este paquete y haz el primer commit.
3. Instala Python 3.12, Node.js en su versión LTS y pnpm.
4. Crea dos proyectos en Supabase: `arrendi-dev` y `arrendi-prod`.
5. Crea una cuenta en Vercel y conéctala a GitHub. Los proyectos se crean en la etapa 1.
6. Para el acceso con Google, crea un proyecto en Google Cloud con una pantalla de consentimiento y un cliente OAuth de tipo web, y registra sus credenciales como proveedor Google en Supabase Auth, en los dos proyectos. Claude Code te puede guiar paso a paso en la etapa 1, pero las credenciales las creas tú.
7. Copia `apps/api/.env.example` a `apps/api/.env` y `apps/web/.env.example` a `apps/web/.env.local`, y llena los valores de `arrendi-dev`.

No pegues claves en la conversación con Claude Code. Deja los valores en los archivos `.env`, que el repositorio ignora.

## Primer encargo

Abre Claude Code en la carpeta del repositorio y pega esto:

```
Vamos a empezar la etapa 1 de Arrendi.

Lee CLAUDE.md, docs/plan.md (etapa 1), docs/arquitectura.md y docs/modelo-de-datos.md.

Antes de escribir código:
1. Dime qué entendiste del objetivo de la etapa 1 en pocas líneas.
2. Consulta la documentación vigente de Turborepo, de Vercel (FastAPI y proyectos en monorepo),
   de Supabase (validación de tokens, acceso con Google, roles y agrupador de conexiones), de Serwist
   con Next.js y de shadcn/ui. Dime qué encontraste que cambie algo de lo escrito en docs/.
3. Propón el plan: archivos que vas a crear y en qué orden, en pasos pequeños
   que yo pueda revisar uno por uno.
4. Hazme las preguntas que necesites.

No escribas código hasta que yo apruebe el plan.
```

## Encargos siguientes

Para cada tarea de la etapa:

```
Sigue con la siguiente tarea sin marcar de la etapa N en docs/plan.md.
Escribe primero la prueba si la tarea toca consecutivo, estados, tarea diaria o aislamiento.
Al terminar, ejecuta las pruebas y el lint, marca la casilla y resume qué cambió.
```

Para cerrar una etapa:

```
Revisa los criterios de aceptación de la etapa N en docs/plan.md.
Dime cuáles se cumplen, cómo lo comprobaste y cuáles tengo que probar yo a mano.
No marques la etapa como terminada hasta que yo confirme.
```

Cuando cambies de opinión sobre una regla:

```
Quiero cambiar esta regla: [regla]. Actualiza primero docs/reglas-de-negocio.md
y docs/decisiones.md, muéstrame el cambio, y después ajusta el código y las pruebas.
```

## Recomendaciones

- **Una sesión por tarea.** Las sesiones cortas mantienen a Claude Code enfocado; el contexto que importa está en `CLAUDE.md` y `docs/`.
- **Revisa cada cambio antes de aceptarlo,** sobre todo migraciones y políticas de seguridad.
- **Haz commit al cerrar cada tarea.** Así siempre puedes volver atrás.
- **Si algo aprendido debe recordarse,** pídele que lo escriba en `CLAUDE.md` o en `docs/`. Lo que no queda escrito se pierde entre sesiones.
- **Prueba tú mismo los criterios de aceptación** en el celular. Las pruebas automáticas no reemplazan usar la aplicación.
