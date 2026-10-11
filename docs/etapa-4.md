# Etapa 4: guía paso a paso

Guía de trabajo de la etapa 4 (correo y tarea diaria). Las tareas y los criterios de aceptación oficiales están en `docs/plan.md`; este documento detalla el orden, qué hace cada paso y cómo se comprueba. Se marca cada paso al terminarlo.

**Objetivo:** que las cuentas y los recordatorios salgan solos.

**Criterios de aceptación**

- La tarea genera y envía las cuentas del mes, y el correo llega con el PDF.
- Una cuenta sin pagar recibe su recordatorio al día siguiente del vencimiento, una sola vez.
- En local y en vista previa, ningún correo llega a un arrendatario real.

## Decisiones de esta etapa

Tomadas el 11 de octubre de 2026:

1. **Proveedor: Resend.** Por su API HTTP, sin SDK: se usa `httpx2`, como con Storage. El plan gratuito (unos 3.000 correos al mes y 100 al día, según páginas de terceros) sobra para el piloto; las cifras y la API se confirman en su documentación antes de configurar.
2. **Todo al buzón de pruebas hasta la etapa 6, también en Producción.** Mientras `EMAIL_TEST_INBOX` tenga valor, todo correo va a ese buzón, con el destinatario real en el asunto. Fuera de producción la variable es obligatoria: sin ella no se envía nada. En la etapa 6, con el dominio propio, se quita de Producción. Hasta entonces el remitente es el de pruebas de Resend, que solo entrega al correo de la cuenta de Resend: ese debe ser el buzón de pruebas.
3. **Lo generado a mano no se envía solo.** La cuenta que generas desde el contrato o como manual queda sin enviar, con el botón "Enviar" en su detalle. Solo la tarea diaria envía sola, y solo si el contrato tiene envío automático.

## Límites asumidos

Dime si alguno no te sirve antes de empezar.

- **Estado `pending` en las notificaciones.** `docs/modelo-de-datos.md` solo tiene `sent`, `bounced` y `failed`. Hace falta uno más para apartar el envío antes de hacerlo: la fila se crea `pending` dentro de la transacción (el índice único impide el duplicado), el correo sale después de confirmar, y la fila pasa a `sent` o `failed`.
- **Reintentos:** la tarea diaria reintenta los correos automáticos que quedaron `failed` o `pending` de una ejecución anterior. El id de la notificación viaja como clave de idempotencia, si Resend la admite, para que un reintento no duplique el correo.
- **Recordatorios solo de cuentas enviadas.** Una cuenta que el arrendatario nunca recibió (contrato sin envío automático y que no has enviado) no genera recordatorios.
- **Un recordatorio por cuenta en cada ejecución.** Si la tarea se atrasó y una cuenta ya merece los dos, sale `reminder_1` hoy y `reminder_2` en la siguiente ejecución.
- **Copia al propietario:** con `email_copy`, vas en copia oculta. Mientras todo se desvíe al buzón de pruebas, la copia no se envía.
- **Remitente:** "Tu nombre vía Arrendi", con `Reply-To` a tu correo.
- **Recibo:** se construye la plantilla (está en la lista de esta etapa), pero el envío llega con los pagos en la etapa 5.
- **Rebotes:** se registran en la notificación y se ven en la actividad de la cuenta. El aviso en el inicio llega en la etapa 5. Con todo desviado a tu buzón no habrá rebotes reales: se prueba con avisos simulados.
- **Texto del correo:** la pantalla `/settings/email` del mapa de pantallas no está en las tareas de la etapa; no se construye.
- **Avisos en la web:** "Cuenta enviada" se muestra con `FormMessage`, sin agregar Sonner todavía.
- **Dependencia nueva:** `jinja2` en `apps/api/requirements.txt`, para las plantillas de correo (`docs/arquitectura.md` ya lo prevé).

## Lo que haces tú

| Cuándo | Qué | Dónde |
| --- | --- | --- |
| Antes del paso 3 | Crear la cuenta de Resend con el correo que será tu buzón de pruebas, y una clave de API | resend.com |
| Antes del paso 3 | `EMAIL_API_KEY`, `EMAIL_SENDER` (el remitente de pruebas de Resend) y `EMAIL_TEST_INBOX` | `apps/api/.env` y las variables de `arrendi-api` en Vercel, en los tres entornos. No las pegues en el chat |
| Después del paso 2 | `alembic upgrade head` (migración `0005`) | `arrendi-dev` |
| Antes del paso 6 | Activar el acceso del rol `arrendi_tasks` si no lo hiciste (`alter role ... with login password`) y poner `DATABASE_URL_TASKS` | Editor SQL de `arrendi-dev`; `.env` y Vercel |
| Antes del paso 7 | Generar `CRON_SECRET` (16 caracteres o más) | `.env` y Vercel, en Producción |
| Antes del paso 8 | Crear el webhook de Resend hacia `/api/webhooks/email` con el evento de rebote, y poner `EMAIL_WEBHOOK_SECRET` | resend.com; `.env` y Vercel |
| Al final | Ver llegar a tu buzón la cuenta con su PDF y, al día siguiente del vencimiento, el recordatorio | Tu correo |

## Pasos

En los pasos 2, 5 y 6 la prueba va primero.

### [x] Paso 1. Documentos al día

- `docs/decisiones.md`: Resend, el desvío hasta la etapa 6 y el envío a mano; salen de "Pendientes" el proveedor y el dominio de envío (este pasa a la etapa 6).
- `docs/reglas-de-negocio.md`: lo generado a mano no se envía solo; recordatorios solo de cuentas enviadas; reintentos.
- `docs/modelo-de-datos.md` (estado `pending`), `docs/api.md` (enviar, recordar, `settings` completo, tarea y aviso de rebotes), `docs/arquitectura.md` (entornos y variables de correo) y `CLAUDE.md` (este documento en la tabla).

### [x] Paso 2. Migración `0005` y modelo

- `notifications`, con `0003_bills.py` como molde: clave foránea compuesta a `bills`, `check` de `type`, `channel` y `delivery_status`, índice único parcial `(bill_id, type)` para `bill`, `reminder_1` y `reminder_2`, e índice sobre `provider_id`.
- Seguridad por fila y revocación a los roles de Supabase. `arrendi_api` y `arrendi_tasks`: select, insert y update.
- `app/models/notification.py`; `OWNED_TABLES` de `tests/conftest.py`.
- **Se comprueba:** `tests/test_notification_tables.py`: restricciones, política, permisos y cruce entre propietarios.

### [x] Paso 3. Envío de correo detrás de una interfaz

- `app/email/sender.py`: el protocolo `send(message) -> provider_id`, la implementación de Resend con `httpx2` y un doble en `tests/conftest.py`, inyectable como `get_storage` en `app/dependencies.py`. Consulto la documentación vigente de Resend (envío, adjuntos, idempotencia).
- El desvío vive aquí, en un solo lugar: reemplaza el destinatario por el buzón de pruebas, quita la copia y anota el destinatario real en el asunto. Sin buzón y fuera de producción, se niega a enviar.
- `app/storage.py`: método `download`, para adjuntar el PDF guardado.
- **Se comprueba:** la petición a Resend contra un servidor simulado; fuera de producción ningún destinatario real sale, con o sin buzón configurado.

### [x] Paso 4. Plantillas

- `app/email/templates/` en Jinja2, en HTML y en texto: `bill`, `reminder_1`, `reminder_2`, `manual_reminder` y `receipt`. En claro, legibles si el cliente de correo las oscurece. Reutilizan `app/pdf/format.py` para dinero y fechas.
- **Se comprueba:** cada plantilla trae lo que pide `docs/reglas-de-negocio.md` (periodo, valor, vencimiento, saldo, días de atraso, datos de pago); el texto de usuario va escapado en el HTML.

### [x] Paso 5. Enviar, reenviar y recordar

- `app/services/notifications.py`: aparta la notificación en la transacción y envía después de confirmarla, con `BackgroundTasks`, como la anulación en `app/services/bills.py`.
- `POST /api/bills/{id}/send`: `bill` la primera vez y `resend` después. `POST /api/bills/{id}/remind`: `manual_reminder`; 400 si no tiene saldo. Ninguna de las dos sobre cuentas anuladas.
- `GET /api/bills/{id}`: campo `notifications`.
- **Se comprueba:** el correo sale después de confirmar y nunca si la transacción falla; el adjunto es el PDF guardado; un fallo del proveedor deja la notificación `failed`; aislamiento en las dos rutas.

### [x] Paso 6. Tarea diaria

`app/tasks/daily.py`, con la conexión de `arrendi_tasks` y "hoy" en `America/Bogota` (`app/dates.py`):

1. **Generar.** Por cada propietario cuyo `send_day` ya llegó este mes, la cuenta del periodo de cada contrato activo que no la tenga, con el servicio de emisión de la etapa 3 (`app/services/bills.py`). Una transacción por contrato. Si el contrato tiene envío automático, se envía.
2. **Marcar vencidas.** `pending` y `partial` con vencimiento anterior a hoy pasan a `overdue`.
3. **Recordar.** `reminder_1` desde 1 día después del vencimiento y `reminder_2` desde 7, si el propietario lo tiene activo.

Por lotes, con un límite de tiempo por ejecución; lo que no alcance queda para la siguiente. Un fallo con un contrato se registra y la tarea sigue. Al final deja en el registro cuántas cuentas generó, cuántos correos envió y cuántos errores hubo.

- **Se comprueba:** ejecutada dos veces el mismo día no duplica cuentas ni correos; tras un día perdido procesa lo pendiente; a las 03:00 UTC todavía es "ayer" en Colombia; un contrato que falla no detiene a los demás; contratos terminados y `send_day` futuro no generan; los consecutivos siguen sin saltos.

### [x] Paso 7. Ruta y Cron Job

- `GET /api/cron/daily` en `app/routes/system.py`: exige `Authorization: Bearer <CRON_SECRET>` (así la llama Vercel, verificado el 11 de octubre de 2026) y responde 401 sin él o si el secreto no está configurado.
- `apps/api/vercel.json`: `crons` con `0 11 * * *` (6:00 a. m. en Colombia; en el plan Hobby arranca en cualquier momento de esa hora) No se fija la duración máxima de la función: la tarea se corta sola a los 50 segundos, por debajo del límite más corto de Vercel, y deja el resto para la siguiente ejecución.
- **Se comprueba:** la ruta sin secreto o con uno errado no ejecuta nada. En Vercel, lanzar el Cron Job a mano desde el panel y ver su registro.

### [x] Paso 8. Aviso de rebotes

- `POST /api/webhooks/email`: valida la firma de Resend con `EMAIL_WEBHOOK_SECRET` (formato exacto según su documentación vigente), busca la notificación por `provider_id` y la deja `bounced`. Usa el rol de tareas, porque no hay propietario en la petición.
- **Se comprueba:** firma inválida o vencida responde 401 y no cambia nada; un aviso repetido no rompe nada; un `provider_id` desconocido responde bien sin hacer nada.

### [x] Paso 9. Configuración completa en la API

- `PATCH /api/settings`: `send_day` (1 a 28), `reminder_1`, `reminder_2` y `email_copy`.
- `pnpm gen:api`.
- **Se comprueba:** validación y aislamiento.

### [x] Paso 10. Web: actividad y envíos en la cuenta

- `components/bills/BillScreen.tsx`: la actividad lista las notificaciones (enviada, recordatorio, rebotó, falló); botón principal "Enviar al arrendatario" si no se ha enviado, y "Reenviar" y "Recordar" después. Aviso si la cuenta sigue sin enviar.
- `lib/api/queries.ts`: `useSendBill` y `useRemindBill`.

### [x] Paso 11. Web: configuración

- `components/settings/SettingsScreen.tsx`: sección "Envíos por correo" (día de envío, dos recordatorios, copia) y "Apariencia", con el selector de tema que hoy está en el inicio provisional.
- `components/leases/LeaseScreen.tsx`: el texto de "Enviar cuentas automáticamente" menciona el día de envío.
- **Se comprueba:** ambos temas.

### [ ] Paso 12. Cierre

- `pnpm lint`, `pnpm test` y `pnpm build` pasan (11 de octubre de 2026).
- Falta lo de "Lo que haces tú" (Resend, variables, migración `0005`, rol de tareas, webhook) y revisar en el navegador, en ambos temas, el detalle de cuenta y Ajustes. Hasta entonces las casillas de la web en `docs/plan.md` quedan sin marcar.
- Casillas de la etapa 4 en `docs/plan.md`. La etapa pasa a 5 cuando confirmes los criterios de aceptación.

## Verificación de extremo a extremo

- **En local:** enviar una cuenta desde su detalle y verla llegar a tu buzón con el PDF y el destinatario real en el asunto; llamar a `/api/cron/daily` con el secreto dos veces seguidas y comprobar que la segunda no hace nada.
- **En Vercel:** lanzar el Cron Job desde el panel; al día siguiente del vencimiento de una cuenta enviada, ver llegar un solo recordatorio.
- **Rebote:** enviar a Resend un aviso de prueba desde su panel y ver la notificación como rebotada.

## Riesgos

- **La tarea corre contra tus datos reales.** Producción usa `arrendi-dev`: desde que el Cron Job exista, cada mañana generará las cuentas de tus contratos con consecutivos reales. Los correos irán solo a tu buzón.
- **Límite del plan gratuito de Resend** (100 al día): con 3 unidades no se alcanza; un fallo por límite deja la notificación `failed` y se reintenta al día siguiente.
- **Duración de la función:** con pocos contratos la tarea termina en segundos. El corte por tiempo existe para cuando haya más propietarios.
- **Un correo `pending` tras una caída** puede haberse enviado o no. La clave de idempotencia evita el duplicado si Resend la admite; si no, el reintento podría repetir ese correo.
