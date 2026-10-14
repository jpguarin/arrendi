# Flujo de trabajo con Git

Cómo se crean features, se arreglan bugs y se publican hotfix. Hay dos ambientes independientes y cada uno sigue una rama:

| Rama | Ambiente | Base de datos |
| --- | --- | --- |
| `main` | Producción (Vercel Production) | `arrendi-prod` |
| `develop` | Pruebas (Vercel Preview, dominio `arrendi-dev`) | `arrendi-dev` |

La configuración de esos ambientes está en `docs/guia-supabase-vercel.md`.

## Resumen

```
feat/<nombre> ──PR──► develop ──PR (promoción)──► main
fix/<nombre>  ──PR──►    │                          ▲
docs/<nombre> ──PR──►    │                          │
                         └◄── PR (vuelta) ◄── hotfix/<nombre> (sale de main)
```

| Tipo | Sale de | Entra a | Cuándo |
| --- | --- | --- | --- |
| `feat/<nombre>` | `develop` | `develop` | Funcionalidad nueva (el pedido dice "new feature") |
| `fix/<nombre>` | `develop` | `develop` | Bug que no es urgente. Viaja con la siguiente promoción |
| `docs/<nombre>` | `develop` | `develop` | Documentación y cambios sin riesgo |
| `hotfix/<nombre>` | `main` | `main`, y después `develop` | Bug que ya rompe producción y no puede esperar |

## Reglas

1. **Nadie sube directo** a `main` ni a `develop`. Todo entra por PR, aunque lo fusione el mismo fundador.
2. **Un PR de feature, fix o docs apunta a `develop`.** Al fusionarlo, Vercel despliega el ambiente de pruebas y ahí se prueba.
3. **A `main` solo llegan promociones desde `develop`, y hotfix.** Lo que está en `develop` es lo que se publica: si algo no debe salir todavía, no se fusiona en `develop`.
4. **Se fusiona con commit de fusión** (*Create a merge commit*) en todos los PR. Nunca *squash*, y menos en la promoción o el hotfix: `main` y `develop` divergerían y cada promoción traería conflictos.
5. **Commits** pequeños, en español, un cambio lógico por commit.
6. **La rama se borra al fusionar.**
7. **Antes de abrir un PR** pasan `pnpm lint`, `pnpm test` y `pnpm build`. El CI (ver abajo) lo comprueba en cada PR.

## Feature (nuevo)

```
git checkout develop && git pull
git checkout -b feat/<nombre-corto>
# trabajo y commits
git push -u origin feat/<nombre-corto>
```

Se abre un PR hacia `develop`. Tras fusionarlo, se prueba en el ambiente de pruebas.

## Bug que no es urgente

Igual que un feature, con rama `fix/<nombre-corto>`. Si el bug está en producción pero puede esperar a la siguiente promoción, se arregla en `develop`.

## Hotfix

Para un bug en producción que no puede esperar a la siguiente promoción. Sale de `main`, no de `develop`, porque `develop` puede tener cosas sin probar.

```
git checkout main && git pull
git checkout -b hotfix/<nombre-corto>
# arreglo mínimo y su prueba, commits
git push -u origin hotfix/<nombre-corto>
```

1. PR hacia `main`. Al fusionarlo, se despliega producción. Comprobar el arreglo ahí.
2. **Llevarlo a `develop`** enseguida, para que no se pierda ni choque con la siguiente promoción: PR de `main` hacia `develop`. Si hay conflictos, se resuelven en ese PR.
3. Si el hotfix lleva una migración, sigue la regla de migraciones y se aplica a las dos bases (producción primero).

Un hotfix lleva solo el arreglo: sin mejoras ni limpieza aprovechando el viaje.

## Promoción (`develop` → `main`)

PR de `develop` hacia `main`, con este checklist en la descripción:

- [ ] `pnpm lint`, `pnpm test` y `pnpm build` pasan.
- [ ] Lo que cambia se probó en el ambiente de pruebas.
- [ ] ¿Hay migraciones nuevas?
  - [ ] Son compatibles con el código que hoy corre en producción (ver abajo).
  - [ ] Aplicadas a `arrendi-prod` con `alembic upgrade head` **antes** de fusionar.
  - [ ] `select version_num from alembic_version;` en `arrendi-prod` devuelve la última.
- [ ] ¿Variables de entorno nuevas? Ya cargadas en Vercel, ambiente Production.
- [ ] Documentos actualizados.

Después de fusionar, se comprueba `https://<web-prod>/api/health`.

## Migraciones con dos ambientes

Las migraciones se aplican a mano desde el computador, a cada base por separado:

- **`arrendi-dev`:** al fusionar en `develop`, antes de probar.
- **`arrendi-prod`:** justo antes de fusionar la promoción en `main`.

Como la base de producción se migra antes de desplegar el código nuevo, durante unos minutos el código viejo corre contra el esquema nuevo. Por eso **toda migración debe ser compatible hacia atrás**:

- Sí: tablas nuevas, columnas nuevas nulas o con valor por defecto, índices.
- No en un solo paso: renombrar o borrar una columna, volverla obligatoria sin valor por defecto. Se hace en dos promociones: primero el código deja de usarla, y en la siguiente se borra.

Si una migración no puede ser compatible, se avisa en el PR y se hace en un momento en que no haya uso.

Una migración ya aplicada a una base compartida no se edita: se crea otra.

## Protección en GitHub

Se configura a mano en GitHub, en Settings → Branches (o Rulesets), para `main` y `develop`:

- Exigir PR antes de fusionar, con 0 aprobaciones (trabaja una sola persona).
- Exigir que pase el check `ci` del workflow CI. GitHub solo lo ofrece en la lista después de que haya corrido una vez.
- Bloquear los *force push* y el borrado de la rama.
- En Settings → General: permitir solo *merge commits* y activar el borrado automático de la rama al fusionar.
- En Settings → General → Default branch: **`develop` como rama por defecto.** Así cada PR nuevo apunta a `develop` desde el inicio. Solo la promoción y el hotfix cambian la base a `main` a mano. Con `main` por defecto, un PR de feature termina fusionado en producción sin pasar por pruebas si se olvida cambiar la base.

Si el plan de GitHub no impone reglas en repositorios privados, el flujo queda por convención. Se confirma en su documentación vigente.

## CI

`.github/workflows/ci.yml` corre en GitHub Actions en cada PR hacia `develop` y `main`. También se puede lanzar a mano desde la pestaña Actions. Un push nuevo al mismo PR cancela la ejecución anterior.

Pasos, en una máquina Linux limpia:

1. Instala Node 22 con pnpm (la versión de `packageManager`) y Python 3.12, con caché de las dependencias.
2. `pnpm install` y un `apps/api/.venv` con `requirements.txt` y `requirements-dev.txt`, igual que en el computador.
3. `pnpm lint`, `pnpm test` y `pnpm build`.
4. `pnpm gen:api` y comprueba que no cambie nada: si se cambió una ruta o un esquema sin regenerar los tipos, falla.

Detalles:

- **Base de pruebas:** un PostgreSQL 17 de servicio, que vive solo durante la ejecución. `TEST_DATABASE_URL` apunta a él; nunca a Supabase.
- **`turbo.json`** deja pasar `TEST_DATABASE_URL` a la tarea `test` (`passThroughEnv`). Sin eso, Turborepo la filtra y pytest no la ve.
- **Sin secretos.** La compilación de la web recibe valores falsos de `NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`: solo necesita que existan.
- **Fuera:** Playwright (`pnpm e2e`), las migraciones a las bases de la nube y el despliegue, que sigue haciendo Vercel.

Para reproducirlo en local antes de abrir un PR: `pnpm lint && pnpm test && pnpm build`.

## Quién hace qué

- Claude crea la rama, escribe y confirma los cambios y propone la descripción del PR.
- El push y la fusión los pide o los hace el fundador. Claude no sube ni fusiona sin que se lo pidan.
