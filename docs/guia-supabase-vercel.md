# Guía: Supabase y Vercel, pruebas y producción

Paso a paso para crear `arrendi-prod` en Supabase y apuntar a ella solo el ambiente de Producción en Vercel. Complementa la "Guía de despliegue" de `docs/arquitectura.md` y es el paso 6 de `docs/etapa-7.md`. Los pasos en los paneles los hace el fundador en sus cuentas.

Menús y datos de Supabase y Vercel consultados en su documentación el 13 de octubre de 2026. Los nombres de los menús cambian con frecuencia: si no ves el que dice la guía, busca la sección por su nombre.

Fuentes: <https://supabase.com/docs/guides/database/connecting-to-postgres>, <https://supabase.com/docs/guides/api/api-keys>, <https://supabase.com/docs/guides/auth/redirect-urls>, <https://supabase.com/docs/guides/auth/jwts>, <https://vercel.com/docs/environment-variables> y <https://vercel.com/docs/deployment-protection>.

## Qué se configura

En este proyecto "pruebas" son dos cosas, y la que está en la nube ya existe:

| Ambiente | Web y API | Base de datos |
| --- | --- | --- |
| Pruebas automáticas (`pytest`, `pnpm e2e`) | El computador | PostgreSQL local. Nada que configurar en la nube. |
| Pruebas en la nube (`pnpm dev` y vistas previas de Vercel) | El computador y Vercel Preview | `arrendi-dev` (ya existe) |
| Producción | Vercel Production | `arrendi-prod` (por crear) |

El trabajo es crear `arrendi-prod` y hacer que solo Producción apunte a ella.

## Paso 0: poner al día `arrendi-dev`

Hazlo primero. Cada etapa con migraciones nuevas deja `arrendi-dev` atrás, y las vistas previas y `pnpm dev` la usan. Si Vercel desplegó `main` con Producción apuntando a `arrendi-dev`, la API falla al leer las columnas nuevas.

```
cd apps/api && source .venv/bin/activate
alembic current
alembic upgrade head
```

Antes, comprueba que el `DATABASE_URL_MIGRATIONS` de `apps/api/.env` sea el de `arrendi-dev` y no otro.

## Supabase: crear `arrendi-prod`

1. **Proyecto nuevo.**
   - Nombre `arrendi-prod`.
   - Región **East US (North Virginia)**, la misma en la que corre la API en Vercel.
   - Contraseña de la base: larga y **solo letras y números**, así no hay que codificarla en las URL. Guárdala en un gestor de contraseñas.
   - Si hay otros proyectos en el plan gratuito, verifica el límite de proyectos activos antes de crearlo.
2. **Copiar estos valores** a un gestor de contraseñas, nunca al repositorio ni al chat:
   - **URL del proyecto** (`https://<ref>.supabase.co`) y el `ref`.
   - **Settings → API Keys:** la clave publicable (`sb_publishable_…`) y la secreta (`sb_secret_…`). No se usan las antiguas `anon` y `service_role`, que Supabase retira a finales de 2026.
   - **Botón Connect:** la cadena del *Transaction pooler* (puerto 6543) y la del *Session pooler* (puerto 5432). El servidor se copia de ahí y no se arma a mano: lleva un número de grupo.
3. **Claves de firma asimétricas.** Abrir `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`. Debe mostrar una clave `ES256`. Si responde `{"keys":[]}`, la API rechazaría todos los tokens: activar las claves asimétricas en la configuración de JWT del proyecto y volver a abrir la dirección.
4. **Authentication → URL Configuration.**
   - *Site URL:* la URL de producción de `arrendi-web` (en Vercel, en Domains).
   - *Redirect URLs:* `https://<esa URL>/**`.
   - Supabase recomienda rutas exactas en producción y `/**` es amplio. Se deja `/**`, como en la guía de `docs/arquitectura.md`, y se ajusta al terminar las pruebas.
5. **Plantillas de correo** de confirmar registro y recuperar contraseña, iguales a las de `arrendi-dev`:
   - Confirmar registro: `{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=email`
   - Recuperar contraseña: `{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=recovery`

   La confirmación del correo queda activa.
6. **Google.**
   - En Google Cloud, en el cliente OAuth, agregar la URI de redirección autorizada `https://<ref-prod>.supabase.co/auth/v1/callback`.
   - En Supabase, activar el proveedor Google en `arrendi-prod` y pegar el id y el secreto del cliente.
   - Si la pantalla de consentimiento está en "Testing", agregar el correo del fundador como usuario de prueba.
7. **Storage.** Crear el contenedor `arrendi`: privado, límite de 10 MB, tipos `application/pdf, image/jpeg, image/png`, **sin políticas**.
8. **Migraciones** desde el computador, con la conexión *Session pooler*: la conexión directa solo es IPv6 y la red del fundador no la tiene. Antes, `unset HISTFILE` para que la contraseña no quede en el historial. Revisar que el `ref` sea el de producción:
   ```
   cd apps/api && source .venv/bin/activate
   DATABASE_URL_MIGRATIONS='postgresql://postgres.<ref-prod>:<clave>@<servidor-session-pooler>:5432/postgres' alembic upgrade head
   ```
   La variable escrita así tiene prioridad sobre `apps/api/.env`, que no se toca.
9. **Contraseñas de los roles.** Las migraciones crean `arrendi_api` y `arrendi_tasks` sin acceso y sin contraseña. Las contraseñas las inventa el fundador: Supabase no las genera.
   1. **Generar dos contraseñas distintas**, con el gestor de contraseñas o en la terminal:
      ```
      openssl rand -hex 16
      openssl rand -hex 16
      ```
      Cada comando imprime 32 caracteres, solo letras de la a a la f y números. Así no hay nada que codificar en la URL ni comillas que rompan el SQL.
   2. **Guardarlas** en el gestor de contraseñas con una etiqueta que las distinga, por ejemplo `arrendi-prod arrendi_api` y `arrendi-prod arrendi_tasks`. Se necesitan otra vez en Vercel.
   3. **Ejecutarlas en la base.** En el *SQL Editor* de `arrendi-prod`, cambiando solo el texto entre comillas simples. Debe responder "Success":
      ```sql
      alter role arrendi_api with login password '<primera-contraseña>';
      alter role arrendi_tasks with login password '<segunda-contraseña>';
      ```
   4. **Usarlas en Vercel**, dentro de las dos URL de la base (ver "Vercel"):
      ```
      DATABASE_URL        postgresql://arrendi_api.<ref-prod>:<primera>@<servidor-transaction-pooler>:6543/postgres
      DATABASE_URL_TASKS  postgresql://arrendi_tasks.<ref-prod>:<segunda>@<servidor-transaction-pooler>:6543/postgres
      ```

   Cuidados:
   - **Después del paso 8.** Los roles los crea la migración: si el SQL se ejecuta antes, falla porque el rol no existe.
   - **Que no se repitan.** Distintas entre sí y distintas de la contraseña del usuario `postgres`. `arrendi_tasks` salta la seguridad por fila, así que es la más delicada.
   - **Si se pierde una**, no se recupera: se vuelve a ejecutar el `alter role` con una nueva y se actualiza la variable en Vercel.
   - **Ninguna va al repositorio ni al chat.**
   
10. **Comprobar** en el mismo editor: `select version_num from alembic_version;` devuelve la última migración (hoy `0012`).

## Vercel

Una variable puede tener un valor distinto por ambiente. Solo se cambia el de **Producción**: el de Preview sigue con `arrendi-dev`. Las variables nuevas aplican solo a despliegues nuevos, así que hay que redesplegar.

**`arrendi-api` → Settings → Environment Variables**, ambiente Production:

| Variable | Valor |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | `postgresql://arrendi_api.<ref-prod>:<clave>@<servidor-transaction-pooler>:6543/postgres` |
| `DATABASE_URL_TASKS` | igual, con `arrendi_tasks.<ref-prod>` y su clave |
| `SUPABASE_URL` | la URL de `arrendi-prod` |
| `SUPABASE_SECRET_KEY` | `sb_secret_…` de `arrendi-prod` |
| `STORAGE_BUCKET` | `arrendi` |
| `CRON_SECRET` | uno nuevo, con `openssl rand -hex 32`. Sin él, la tarea diaria rechaza a todos. |
| `EMAIL_TEST_INBOX` | el correo del propio fundador. No se quita hasta el paso 7 de la etapa 7. |

- Las que son secretos se marcan como *Secret*: las dos URL de base, la clave secreta y `CRON_SECRET`.
- `EMAIL_API_KEY`, `EMAIL_SENDER` y `EMAIL_WEBHOOK_SECRET` quedan vacías hasta configurar Resend. Sin proveedor, el envío falla con aviso, pero las cuentas se generan igual.
- `DATABASE_URL_MIGRATIONS` no va en Vercel: las migraciones se corren desde el computador.

**`arrendi-web` → Production:** `NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, de `arrendi-prod`. `API_URL` no se define. Si el proyecto no existe aún, se importa con carpeta raíz `apps/web` (paso 4 de la guía de `docs/arquitectura.md`). Estas variables se incrustan al compilar: hay que rehacer el despliegue.

**Protección de despliegues de `arrendi-api`:** en "ninguna", como indica `docs/arquitectura.md`. La protección estándar ya deja abiertos los dominios de producción, pero bloquearía las vistas previas, donde la web llama a la API de servidor a servidor. La API exige igual el token de Supabase en todo lo que tiene datos.

**Redesplegar** `arrendi-api` y `arrendi-web`: Deployments → ⋯ → Redeploy.

## `arrendi-dev` para las vistas previas

En `arrendi-dev`, las direcciones de retorno deben incluir `http://localhost:3000/**` y el patrón `https://*-<slug-de-vercel>.vercel.app/**`. El slug es el de `vercel.com/<slug>`.

### Tarea diaria en vista previa

Vercel solo ejecuta los Cron Jobs en Producción. En vista previa, el workflow `.github/workflows/preview-cron.yml` llama a `/api/cron/daily` de la rama `develop` a las 11:00 UTC, con el mismo secreto que exige la API.

1. **Antes de activarlo**, comprobar que `EMAIL_TEST_INBOX` está definida en `arrendi-api` para Preview. Sin ella, la tarea en pruebas les escribe a los arrendatarios que haya en `arrendi-dev`.
2. En GitHub, **Settings → Secrets and variables → Actions**:
   - Variable `PREVIEW_API_URL`: el dominio fijo de `develop` en `arrendi-api`, sin barra final (el alias de rama `https://arrendi-api-git-develop-<slug>.vercel.app`, o el dominio propio si `develop` tiene uno). No es el de un despliegue concreto: ese cambia con cada commit.
   - Secreto `PREVIEW_CRON_SECRET`: el valor de `CRON_SECRET` de `arrendi-api` en Preview.
3. **Comprobar:** Actions → "Daily task (Preview)" → *Run workflow*. Debe terminar en verde y mostrar el JSON de la tarea. Con 401, el secreto no coincide; con 500, revisar `DATABASE_URL_TASKS` de Preview.

Cuidados:
- GitHub solo programa el workflow que está en la rama por defecto del repositorio: empieza a correr solo cuando el archivo llega a ella.
- GitHub puede retrasar los `schedule` varios minutos en horas de carga, y desactiva los programados de un repositorio público tras 60 días sin actividad.
- Si falla, el workflow queda en rojo y GitHub avisa por correo a quien lo activó.
- Depende de que la protección de despliegues de `arrendi-api` siga en "ninguna".

## Cómo comprobar que quedó bien

1. `https://<web-prod>/api/health` responde `{"status":"ok"}`.
2. Se entra a la web de producción con una cuenta nueva y se llega al alta. En `arrendi-prod` aparece la fila en `owners`, y en `arrendi-dev` no aparece nada nuevo.
3. Se crea un contrato con documento y se genera una cuenta. El PDF abre: eso prueba Storage y la clave secreta.
4. Al día siguiente, en los *Logs* de `arrendi-api`, aparece `/api/cron/daily` con 200. Corre a las 6:00 a. m. de Colombia, con hasta 59 minutos de margen en el plan Hobby.

## Cuidados

- **Producción arranca vacía**, como se decidió en la etapa 7: el alta se hace de nuevo y los consecutivos empiezan en 1.
- **Antes de usar datos reales** con los arrendatarios, faltan la política de datos con la autorización (paso 2 de la etapa 7) y la copia de seguridad (paso 4). Sentry y la accesibilidad pueden esperar, pero conviene cerrarlas antes de cobrar de verdad.
- **El plan gratuito de Supabase puede pausar proyectos inactivos.** La tarea diaria genera actividad cada día, pero hay que verificarlo en su documentación de precios.
- **Ningún secreto va al repositorio:** ni las contraseñas de la base, ni `sb_secret_…`, ni `CRON_SECRET`. Viven en el gestor de contraseñas y en las variables de Vercel.
