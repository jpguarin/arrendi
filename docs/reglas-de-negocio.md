# Reglas de negocio

Estas reglas se implementan en `apps/api/app/services/` y cada una tiene su prueba.

## Cuenta de cobro

### Fechas de una cuenta mensual

- **Periodo:** el mes que se cobra, guardado como el primer día de ese mes (`2026-10-01`).
- **Emisión:** el día en que se genera.
- **Vencimiento:** el `due_day` del contrato dentro del mes del periodo. El día de pago va de 1 a 28, así que siempre existe.
- **Total:** la suma de sus conceptos, cada uno con su valor. Un cambio posterior del canon o de los conceptos del contrato no altera cuentas ya emitidas.
- **Conceptos:** primero el canon del contrato en el momento de generar; después los conceptos fijos del contrato (por ejemplo, la administración), en su orden, que salen en todas las cuentas mensuales; al final el depósito, si aplica. Los conceptos no tienen fecha propia: el vencimiento es de la cuenta.
- **Depósito:** si el contrato tiene depósito mayor que cero y `charge_deposit` encendido, su primera cuenta mensual lo cobra como un concepto aparte, después del canon. "Primera" quiere decir que el contrato no tiene otra cuenta mensual sin anular: si esa cuenta se anula, la que la reemplaza vuelve a cobrarlo. Las cuentas manuales no lo cobran ni cuentan como primera. Vale igual para la cuenta generada a mano y para la de la tarea diaria.

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
- `paid` y `voided` son estados finales, salvo que se elimine un pago de una cuenta `paid`: vuelve al estado que le corresponda.
- El **saldo** nunca se guarda: es el total menos la suma de los pagos.

### Reglas

- **Recargo por mora:** si el contrato lo tiene activo, la cuenta mensual guarda al emitirse lo que cuesta pagarla tarde (el porcentaje sobre su canon, redondeado al peso) y su fecha límite (vencimiento más días de gracia). Esas condiciones no cambian aunque después cambie el contrato. La cuenta está atrasada si, pasada la fecha límite, los pagos con fecha hasta ese día no cubren su total: pagarla completa pero tarde también genera recargo. El recargo nunca se suma a la cuenta atrasada: la siguiente cuenta mensual del contrato lo trae como un concepto, "Recargo por mora de octubre 2026", después de los conceptos fijos y antes del depósito, una sola vez. Si la cuenta que lo cobró se anula, la que la reemplaza vuelve a traerlo. El propietario puede perdonarlo, y deshacerlo, mientras no se haya cobrado. Una cuenta anulada no genera recargo. El PDF y el correo de la cuenta avisan del recargo desde que se emite.
- **Cuenta manual:** lleva de 1 a 10 conceptos, los que el propietario escriba, y un solo vencimiento. No cobra los conceptos fijos del contrato ni el depósito, y no genera ni cobra recargo por mora.
- **Firma:** al emitir, la cuenta guarda la firma que el propietario tiene en ese momento. El PDF termina, al final de su última hoja, con la firma, el nombre del propietario y su documento; si no hay firma, deja una línea para firmar a mano. Subir, cambiar o quitar la firma después no altera las cuentas ya emitidas, tampoco su PDF de anulada. Si la firma no se puede leer del almacenamiento o no se puede dibujar en el PDF, la cuenta no se emite y no gasta consecutivo: nunca queda una cuenta marcada como firmada sin estarlo. Anular sí funciona en ese caso, y el PDF de anulada sale con la línea de firma.
- **Inmutable:** una cuenta emitida no se edita. Si hay un error, se anula y se genera otra con consecutivo nuevo.
- **Datos de pago:** al emitir, la cuenta toma los suyos si es manual y los trae; si no, los del contrato; si no, los de Ajustes. Quedan guardados en la cuenta: el PDF, la pantalla y todos sus correos muestran esos, aunque después cambien Ajustes o el contrato. La cuenta mensual, a mano o por la tarea diaria, empieza por los del contrato.
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
- Al guardar un pago se recalcula el estado en la misma transacción, con la cuenta bloqueada: dos pagos simultáneos no pueden sumar más que el saldo.
- **Recálculo:** sin saldo, `paid`; con saldo y vencimiento anterior a hoy, `overdue`; con saldo y algún pago, `partial`; si no, `pending`. Una cuenta anulada no cambia.
- Un pago no se edita. Si hubo un error, se elimina y se registra de nuevo; al eliminarlo se recalcula el estado, también si la cuenta estaba `paid`. Eliminar es un borrado real: el pago y su comprobante desaparecen.
- **A qué mes pertenece el dinero:** un pago cuenta en el mes de su cuenta (su `period`, o el mes de su vencimiento si es manual), no en el mes en que se recibió. Así el inicio y el listado dan las mismas cifras.
- **Recibo:** si el propietario lo marca, sale después de confirmar la transacción. Si falla, la notificación queda `failed` y no se reintenta sola.

## Contratos y unidades

- Una unidad tiene como máximo un contrato `active`.
- Una unidad sin contrato activo está **vacía** y no genera cuentas.
- Terminar un contrato lo pasa a `ended`: deja de generar cuentas, pero conserva su historial y sus saldos.
- Una unidad está **en mora** cuando su contrato activo tiene al menos una cuenta `overdue`. Si no, está en **pago parcial** cuando tiene alguna `partial`. Si no, está al día.
- El correo del arrendatario es obligatorio.
- **Decisión provisional:** un contrato que pasa su fecha de fin sigue activo hasta que el propietario lo termine. La aplicación lo avisa en la pantalla del contrato.
- **Decisión provisional:** no hay prorrateo. Un contrato que empieza a mitad de mes genera su primera cuenta completa en el siguiente día de envío.

## Correos

| Correo | Cuándo sale | Contenido | Adjunto |
| --- | --- | --- | --- |
| `bill` | Cuando la tarea diaria la genera, si el contrato tiene envío automático; o cuando el propietario la envía | Periodo, valor, vencimiento y datos de pago | PDF de la cuenta |
| `reminder_1` | Al día siguiente del vencimiento, si hay saldo | Saldo pendiente y datos de pago | PDF de la cuenta |
| `reminder_2` | A los 7 días del vencimiento, si hay saldo | Saldo pendiente y días de atraso | PDF de la cuenta |
| `receipt` | Al registrar un pago, si el propietario lo marca | Valor recibido, fecha, medio y saldo restante | Ninguno |
| `manual_reminder` | Cuando el propietario lo pide | Saldo pendiente y datos de pago | PDF de la cuenta |
| `resend` | Cuando el propietario reenvía una cuenta ya enviada | Lo mismo que `bill` | PDF de la cuenta |

- Remitente con el nombre del propietario; las respuestas van al correo del propietario (`Reply-To`).
- El propietario puede activar o desactivar cada recordatorio automático y recibir copia de cada correo.
- Cada envío crea una fila en `notifications`.
- Los correos automáticos (`bill`, `reminder_1`, `reminder_2`) salen una sola vez por cuenta. Los manuales y los reenvíos no tienen ese límite.
- Si el proveedor avisa de un rebote, la notificación queda `bounced` y el inicio lo muestra.
- El correo se envía después de confirmar la transacción.
- **A mano no se envía solo:** la cuenta que el propietario genera a mano (la mensual desde el contrato o una manual) queda sin enviar hasta que él la envía, aunque el contrato tenga envío automático.
- **Recordatorios solo de cuentas enviadas:** una cuenta que nunca se le envió al arrendatario no recibe recordatorios automáticos.
- **Una cuenta anulada no se envía ni se recuerda.**
- **Envío en dos tiempos:** la notificación se crea `pending` dentro de la transacción y, tras confirmarla, el correo sale y la notificación pasa a `sent` o `failed`. La tarea diaria reintenta los correos automáticos que quedaron `pending` o `failed`.
- **Desvío:** mientras exista un buzón de pruebas configurado, todo correo va a ese buzón y no al arrendatario. Ver `docs/arquitectura.md`.

## Tarea diaria

Corre una vez al día, en la mañana de Colombia. "Hoy" es la fecha en `America/Bogota`.

1. **Generar cuentas.** Para cada propietario, si su día de envío ya llegó en el mes en curso, se genera la cuenta del periodo actual de cada contrato activo que aún no la tenga. Si el contrato tiene envío automático, se envía; si no, queda sin enviar a la espera del propietario.
2. **Marcar vencidas.** Las cuentas `pending` o `partial` con vencimiento anterior a hoy pasan a `overdue`.
3. **Enviar recordatorios.** `reminder_1` a las cuentas vencidas cuyo vencimiento fue hace 1 día o más y no lo tienen; `reminder_2` a las que vencieron hace 7 días o más y no lo tienen. Solo si el propietario tiene activo ese recordatorio y la cuenta ya se envió. Como mucho un recordatorio por cuenta en cada ejecución: si una cuenta merece los dos, `reminder_2` sale en la siguiente.

Condiciones:

- **Idempotente:** las restricciones únicas de `bills` y `notifications` impiden duplicados aunque se ejecute dos veces.
- **Se recupera sola:** las condiciones son "ya llegó" y "hace N días o más", no "es exactamente hoy". Si la tarea falla un día, la siguiente ejecución procesa lo pendiente.
- **Con límite de tiempo:** procesa los contratos uno a uno, cada cual en su transacción, y se detiene antes de exceder el tiempo máximo de la función. Lo que no alcance queda para la siguiente ejecución.
- **Un fallo no detiene el resto:** un error con un contrato se registra y la tarea sigue con los demás.
- **Registro:** cada ejecución deja cuántas cuentas generó, cuántos correos envió y cuántos errores hubo.

## Inicio

- **Cifras del mes:** esperado es la suma de las cuentas no anuladas del mes; recaudado, lo pagado sobre ellas; pendiente, la diferencia.
- **Por cobrar:** todas las cuentas con saldo, de cualquier mes, con lo vencido primero. Lo que viene de meses anteriores se suma aparte y no entra en las cifras del mes.
- **Pagadas:** las del mes.
- **En mora:** unidades en mora sobre el total de unidades.

## Alta guiada

- Crea el inmueble, sus unidades y, si se completó el paso 3, el arrendatario y el contrato, en una sola transacción.
- Exige al menos una unidad.
- Se hace una sola vez. Si el propietario ya tiene un inmueble, el alta se rechaza: los demás inmuebles se crean desde la pantalla de inmuebles. Así un doble toque en el botón no crea el inmueble dos veces.
- El alta se considera completa cuando el propietario tiene al menos un inmueble. Hasta entonces, la aplicación lo lleva al alta.
