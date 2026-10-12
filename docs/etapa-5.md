# Etapa 5: guía paso a paso

Guía de trabajo de la etapa 5 (pagos e inicio). Las tareas y los criterios de aceptación oficiales están en `docs/plan.md`; este documento detalla el orden, qué hace cada paso y cómo se comprueba. Se marca cada paso al terminarlo.

**Objetivo:** cerrar el ciclo de cobro.

**Criterios de aceptación**

- Registro un abono y la cuenta queda parcial; registro el resto y queda pagada.
- El inicio muestra recaudado, pendiente y unidades en mora, y coincide con el listado.
- Registro un pago desde el inicio en dos toques.

## Decisiones de esta etapa

Tomadas el 11 de octubre de 2026:

1. **Playwright corre todo en local, con dobles.** Levanta la web, la API contra un PostgreSQL local (base `arrendi_e2e`, aparte de la de pytest) y dos servidores falsos pequeños: uno de acceso, que firma tokens de prueba y publica su clave por JWKS, y uno de almacenamiento. No toca Supabase ni `arrendi-dev`, y no usa Docker.
2. **"Por cobrar" muestra toda la deuda.** En el inicio, las cifras (esperado, recaudado, pendiente) son del mes; la lista "Por cobrar" trae todo lo que te deben, de cualquier mes, con lo vencido primero, y una línea aparte dice cuánto viene de meses anteriores.

## Límites asumidos

Dime si alguno no te sirve antes de empezar.

- **A qué mes pertenece el dinero.** "Recaudado" es lo pagado sobre las cuentas de ese mes, no lo recibido durante el mes. Es lo que hace que el inicio coincida con el listado: un pago hecho en noviembre a la cuenta de octubre cuenta en octubre.
- **Recálculo del estado**, en la misma transacción del pago o de su eliminación: sin saldo, `paid`; con saldo y vencimiento anterior a hoy, `overdue`; con saldo y algún pago, `partial`; si no, `pending`. Una cuenta anulada no cambia. Eliminar el pago de una cuenta `paid` la devuelve al estado que le corresponda.
- **Pago mayor al saldo:** se rechaza, como dice la decisión provisional. Dos pagos simultáneos no pueden sumar más que el saldo: la cuenta se bloquea mientras se registra.
- **Eliminar un pago** es el primer borrado real de la aplicación: `arrendi_api` recibe permiso de borrar solo en `payments`. Se borra también su comprobante del almacenamiento.
- **Comprobante:** se sube igual que el contrato, en dos pasos (`upload-url` y confirmación), con los mismos tipos y tamaño. La ruta lleva una carpeta por subida, como la del contrato.
- **Recibo:** sale después de confirmar la transacción, con la plantilla de la etapa 4, y queda como notificación `receipt`. Si falla, queda `failed` en la actividad y no se reintenta solo; puedes volver a registrar o avisar al arrendatario por tu cuenta.
- **Estado de la unidad:** `overdue` ("En mora") si su contrato activo tiene alguna cuenta vencida; si no, `partial` ("Pago parcial") si tiene alguna parcial; si no, `up_to_date`.
- **Inicio sin selector de inmueble ni campana.** El mockup los trae, pero `GET /api/summary` es por propietario y las notificaciones push están fuera del MVP. Los correos rebotados se muestran como un aviso en el inicio, con enlace a la cuenta.
- **Navegar entre meses:** el inicio muestra el mes en curso. `month` existe en la API, pero la web no trae selector de mes en esta etapa.
- **Correo en Playwright:** la API corre sin proveedor configurado, así que el recibo queda "no se pudo enviar" y la prueba no lo marca. El correo ya está cubierto por pytest.
- **Dependencia nueva:** `@playwright/test` en `apps/e2e` (la prueba de extremo a extremo).

## Lo que haces tú

| Cuándo | Qué | Dónde |
| --- | --- | --- |
| Después del paso 2 | `alembic upgrade head` (migración `0006`), antes de hacer push | `arrendi-dev` |
| Una vez, antes del paso 10 | Crear la base local: `createdb arrendi_e2e` | Tu computador |
| Al final | Recorrer los criterios de aceptación en local y en el iPhone | `arrendi-web.vercel.app` |

No hay variables nuevas ni nada que configurar en Supabase, Resend o Vercel.

## Pasos

En los pasos 2 y 3 la prueba va primero.

### [x] Paso 1. Documentos al día

- `docs/reglas-de-negocio.md`: el recálculo, a qué mes pertenece el dinero y la deuda de meses anteriores en el inicio.
- `docs/api.md`: pagos, comprobante en dos pasos, `summary`, y los estados `overdue` y `partial` de la unidad.
- `docs/modelo-de-datos.md` (permiso de borrado y ruta del comprobante), `docs/arquitectura.md` (cómo corre Playwright), `docs/decisiones.md`, `docs/diseno.md` y `CLAUDE.md` (esta guía, `pnpm e2e` y la sección de pruebas).

### [x] Paso 2. Migración `0006` y modelo

- `payments`, con `0005_notifications.py` como molde: clave foránea compuesta a `bills`, `amount > 0`, `check` de `method`. `arrendi_api`: select, insert, update y delete. `arrendi_tasks`: select.
- `app/models/payment.py`; `OWNED_TABLES` de `tests/conftest.py`.
- **Se comprueba:** `tests/test_payment_tables.py`: restricciones, política, permisos y cruce entre propietarios.

### [x] Paso 3. Registrar y eliminar pagos

- `app/services/payments.py` y `app/routes/payments.py`: `POST /api/bills/{id}/payments` y `DELETE /api/payments/{id}`. Bloquea la cuenta (`select ... for update`), valida (valor mayor que cero y no mayor al saldo, fecha no futura en `America/Bogota`, cuenta ni `paid` ni `voided`) y recalcula el estado.
- El saldo deja de ser igual al total: `app/services/bills.py` lo calcula con los pagos en el listado, el detalle, los correos y los recordatorios. La anulación comprueba los pagos de verdad. `GET /api/bills/{id}` trae `payments`.
- **Se comprueba:** cada transición de `docs/reglas-de-negocio.md`, una por una; pago mayor al saldo, fecha futura y cuenta pagada o anulada se rechazan; dos pagos simultáneos no superan el saldo; eliminar recalcula; no se anula una cuenta con pagos; aislamiento.

### [x] Paso 4. Comprobante y recibo

- Comprobante: `POST /api/payments/{id}/proof/upload-url`, `POST /api/payments/{id}/proof` y `GET /api/payments/{id}/proof`, reutilizando la validación de `app/services/documents.py` (tipo real, tamaño, ruta entregada por la API).
- Recibo: con `send_receipt`, el pago aparta una notificación `receipt` y el correo sale después de confirmar, por `app/services/notifications.py`.
- **Se comprueba:** un archivo falso o demasiado grande se rechaza; el comprobante ajeno responde 404; el recibo dice valor, fecha, medio y saldo restante, y no sale si el pago se rechaza.

### [x] Paso 5. Resumen e inmuebles

- `GET /api/summary?month=AAAA-MM` en `app/services/summary.py`: esperado, recaudado y pendiente del mes; unidades en mora sobre el total; "por cobrar" de cualquier mes con lo vencido primero y cuánto viene de meses anteriores; pagadas del mes; correos rebotados.
- `GET /api/properties`: estado `overdue` y `partial` por unidad (`app/services/properties.py`).
- `pnpm gen:api`.
- **Se comprueba:** las cifras coinciden con las del listado del mismo mes; una deuda de un mes anterior aparece en "por cobrar" y no en el esperado; aislamiento.

### [x] Paso 6. Web: registrar pago

- `/bills/[id]/payment` (mockup `Pago`): valor prellenado con el saldo, fecha de hoy, medio con `ToggleGroup`, comprobante opcional con `components/leases/DocumentPicker.tsx` y "Enviar recibo".
- `lib/api/queries.ts`: `useRegisterPayment` y `useDeletePayment`, que actualizan la cuenta y marcan viejos el listado, el resumen, el contrato y los inmuebles.

### [x] Paso 7. Web: pagos en la cuenta y en el listado

- `components/bills/BillScreen.tsx`: "Registrar pago" como acción principal, saldo, pagos en la actividad con "ver comprobante" y eliminar con `AlertDialog`.
- `components/bills/BillsScreen.tsx` y `BillRow.tsx`: "recaudado de total" en cada mes, y "saldo" y "pagó el" en cada fila.

### [x] Paso 8. Web: inicio

- `components/HomeScreen.tsx` (mockup `Main`): `SummaryCard` con recaudado, esperado, barra de avance, pendiente y en mora; "Por cobrar" con "Enviar recordatorio" y "Registrar pago" en la primera fila vencida; "Pagadas"; aviso de correos rebotados; estado vacío. El cierre de sesión pasa a Ajustes.
- La barra de avance es propia, con Tailwind; no se agregó `progress` de shadcn/ui. "Enviar recibo" usa el interruptor que ya existía, no `checkbox`.

### [x] Paso 9. Web: estado de cada unidad

- `components/properties/PropertiesScreen.tsx`: "En mora" y "Pago parcial".
- **Se comprueba (pasos 6 a 9):** ambos temas; el pago desde el inicio toma dos toques.

### [ ] Paso 10. Playwright

- `apps/e2e/`: `playwright.config.ts`, los dos servidores falsos (`fakes/auth.ts`, `fakes/storage.ts`) y la preparación de la base `arrendi_e2e` con las migraciones. Script `pnpm e2e` en la raíz y en `turbo.json`.
- Consulto antes la documentación vigente de Playwright (`webServer`) y de `@supabase/ssr` (qué rutas de acceso llama el navegador).
- Prueba: alta, generación de la cuenta, pago parcial y pago del saldo, comprobando el estado en cada paso y las cifras del inicio.
- **Se comprueba:** `pnpm e2e` pasa dos veces seguidas desde una base limpia.

### [ ] Paso 11. Cierre

- `pnpm lint`, `pnpm test`, `pnpm build` y `pnpm e2e`; casillas de la etapa 5 en `docs/plan.md`. La etapa pasa a 6 cuando confirmes los criterios de aceptación.

## Verificación de extremo a extremo

- **En local:** registrar un abono y ver la cuenta parcial, con el saldo en el listado, en el inicio y en el contrato; registrar el resto y verla pagada; eliminar un pago y ver que vuelve a su estado; adjuntar un comprobante y abrirlo; recibir el recibo en tu buzón.
- **Inicio contra listado:** las cifras del mes en el inicio son las mismas del encabezado de ese mes en Cuentas.
- **Con otra cuenta:** un pago y su comprobante ajenos responden 404.

## Riesgos

- **El servidor falso de acceso** imita solo lo que la web usa de Supabase Auth. Si `@supabase/ssr` llama algo más de lo previsto, habrá que ampliarlo; si resulta frágil, la alternativa es reducir la prueba a partir de una sesión ya iniciada.
- **El saldo cambia en varios lugares a la vez** (listado, detalle, correos, recordatorios, anulación). Las pruebas de la etapa 3 y 4 que asumían saldo igual al total se ajustan en el paso 3.
- **Primer borrado real.** Eliminar un pago no deja rastro. Si más adelante quieres historial, habría que anularlo en vez de borrarlo, y eso cambia el modelo.
