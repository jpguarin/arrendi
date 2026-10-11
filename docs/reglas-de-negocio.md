# Reglas de negocio

Estas reglas se implementan en `apps/api/app/services/` y cada una tiene su prueba.

## Cuenta de cobro

### Fechas de una cuenta mensual

- **Periodo:** el mes que se cobra, guardado como el primer día de ese mes (`2026-10-01`).
- **Emisión:** el día en que se genera.
- **Vencimiento:** el `due_day` del contrato dentro del mes del periodo. El día de pago va de 1 a 28, así que siempre existe.
- **Total:** el canon del contrato en el momento de generar. Un cambio posterior del canon no altera cuentas ya emitidas.

### Estados

| Estado | Significado |
| --- | --- |
| `pending` | Emitida, sin pagos y sin vencer |
| `partial` | Tiene pagos, pero la suma es menor al total, y no ha vencido |
| `paid` | La suma de los pagos iguala el total |
| `overdue` | Tiene saldo y ya pasó su vencimiento |
| `voided` | Anulada por el propietario |

### Transiciones

| Desde | Hacia | Qué la provoca |
| --- | --- | --- |
| (nueva) | `pending` | Se emite con vencimiento hoy o después |
| (nueva) | `overdue` | Se emite con el vencimiento ya pasado |
| `pending` | `partial` | Un pago menor al saldo |
| `pending` | `paid` | Un pago igual al total |
| `partial` | `paid` | Un pago que completa el saldo |
| `pending` | `overdue` | La tarea diaria, al día siguiente del vencimiento |
| `partial` | `overdue` | La tarea diaria, al día siguiente del vencimiento |
| `overdue` | `paid` | Un pago que completa el saldo |
| `pending` | `voided` | El propietario la anula |
| `overdue` | `voided` | El propietario la anula, si no tiene pagos |

- Un abono sobre una cuenta `overdue` no cambia su estado: sigue vencida hasta cubrir el saldo.
- `paid` y `voided` son estados finales.
- El **saldo** nunca se guarda: es el total menos la suma de los pagos.

### Reglas

- **Inmutable:** una cuenta emitida no se edita. Si hay un error, se anula y se genera otra con consecutivo nuevo.
- **Anulación:** solo si la cuenta no tiene pagos. La cuenta anulada conserva su consecutivo y su PDF.
- **Consecutivo:** uno por propietario, creciente y sin saltos. Se asigna en la misma transacción que crea la cuenta, bloqueando la fila del propietario (`select ... for update`).
- **Una por periodo:** no puede haber dos cuentas mensuales no anuladas del mismo contrato y periodo. Si se anula la del mes, se puede generar otra.
- **Mensual a mano:** además de la tarea diaria, el propietario puede generar la cuenta del mes en curso de un contrato activo. Es la misma cuenta, con las mismas reglas.
- **Nace vencida:** si al emitir la cuenta su vencimiento es anterior a hoy (en `America/Bogota`), nace `overdue` en lugar de `pending`. Es lo mismo que haría la tarea diaria a la mañana siguiente.
- **Cuenta manual:** el propietario puede crear una cuenta extra sobre un contrato activo, con descripción, valor y vencimiento propios. No tiene periodo.
- **PDF:** se genera al emitir y se guarda, dentro de la misma transacción: si no se puede guardar, la cuenta no se crea. Reenviar o descargar usa ese mismo archivo. Al anular, se reemplaza por una versión marcada "ANULADA" después de confirmar la transacción.

## Pagos

- Una cuenta admite varios pagos.
- El valor debe ser mayor que cero.
- No se aceptan pagos sobre cuentas `paid` o `voided`.
- **Decisión provisional:** un pago mayor al saldo se rechaza con un mensaje claro. Ver `docs/decisiones.md`.
- La fecha del pago no puede ser futura.
- Medios: `transfer`, `nequi`, `cash`, `other`.
- El comprobante es opcional.
- Al guardar un pago se recalcula el estado en la misma transacción.
- Un pago no se edita. Si hubo un error, se elimina y se registra de nuevo; al eliminarlo se recalcula el estado.

## Contratos y unidades

- Una unidad tiene como máximo un contrato `active`.
- Una unidad sin contrato activo está **vacía** y no genera cuentas.
- Terminar un contrato lo pasa a `ended`: deja de generar cuentas, pero conserva su historial y sus saldos.
- Una unidad está **en mora** cuando su contrato activo tiene al menos una cuenta `overdue`.
- El correo del arrendatario es obligatorio.
- **Decisión provisional:** un contrato que pasa su fecha de fin sigue activo hasta que el propietario lo termine. La aplicación lo avisa en la pantalla del contrato.
- **Decisión provisional:** no hay prorrateo. Un contrato que empieza a mitad de mes genera su primera cuenta completa en el siguiente día de envío.

## Correos

| Correo | Cuándo sale | Contenido | Adjunto |
| --- | --- | --- | --- |
| `bill` | Al generar, si el contrato tiene envío automático; o cuando el propietario la envía | Periodo, valor, vencimiento y datos de pago | PDF de la cuenta |
| `reminder_1` | Al día siguiente del vencimiento, si hay saldo | Saldo pendiente y datos de pago | PDF de la cuenta |
| `reminder_2` | A los 7 días del vencimiento, si hay saldo | Saldo pendiente y días de atraso | PDF de la cuenta |
| `receipt` | Al registrar un pago, si el propietario lo marca | Valor recibido, fecha, medio y saldo restante | Ninguno |
| `manual_reminder` | Cuando el propietario lo pide | Saldo pendiente y datos de pago | PDF de la cuenta |

- Remitente con el nombre del propietario; las respuestas van al correo del propietario (`Reply-To`).
- El propietario puede activar o desactivar cada recordatorio automático y recibir copia de cada correo.
- Cada envío crea una fila en `notifications`.
- Los correos automáticos (`bill`, `reminder_1`, `reminder_2`) salen una sola vez por cuenta. Los manuales y los reenvíos no tienen ese límite.
- Si el proveedor avisa de un rebote, la notificación queda `bounced` y el inicio lo muestra.
- El correo se envía después de confirmar la transacción.

## Tarea diaria

Corre una vez al día, en la mañana de Colombia. "Hoy" es la fecha en `America/Bogota`.

1. **Generar cuentas.** Para cada propietario, si su día de envío ya llegó en el mes en curso, se genera la cuenta del periodo actual de cada contrato activo que aún no la tenga. Si el contrato tiene envío automático, se envía; si no, queda sin enviar a la espera del propietario.
2. **Marcar vencidas.** Las cuentas `pending` o `partial` con vencimiento anterior a hoy pasan a `overdue`.
3. **Enviar recordatorios.** `reminder_1` a las cuentas vencidas cuyo vencimiento fue hace 1 día o más y no lo tienen; `reminder_2` a las que vencieron hace 7 días o más y no lo tienen. Solo si el propietario tiene activo ese recordatorio.

Condiciones:

- **Idempotente:** las restricciones únicas de `bills` y `notifications` impiden duplicados aunque se ejecute dos veces.
- **Se recupera sola:** las condiciones son "ya llegó" y "hace N días o más", no "es exactamente hoy". Si la tarea falla un día, la siguiente ejecución procesa lo pendiente.
- **Por lotes:** procesa los contratos en bloques para no exceder el tiempo máximo de la función.
- **Un fallo no detiene el resto:** un error con un contrato se registra y la tarea sigue con los demás.
- **Registro:** cada ejecución deja cuántas cuentas generó, cuántos correos envió y cuántos errores hubo.

## Alta guiada

- Crea el inmueble, sus unidades y, si se completó el paso 3, el arrendatario y el contrato, en una sola transacción.
- Exige al menos una unidad.
- Se hace una sola vez. Si el propietario ya tiene un inmueble, el alta se rechaza: los demás inmuebles se crean desde la pantalla de inmuebles. Así un doble toque en el botón no crea el inmueble dos veces.
- El alta se considera completa cuando el propietario tiene al menos un inmueble. Hasta entonces, la aplicación lo lleva al alta.
