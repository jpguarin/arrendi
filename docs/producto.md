# Producto

## Resumen

Arrendi es una aplicación web instalable (PWA) para que un arrendador pequeño genere sus cuentas de cobro cada mes, las envíe por correo y sepa quién le debe.

- **Cliente:** propietario particular con 2 a 10 unidades (casas subdivididas, apartaestudios, locales) que administra él mismo, sin inmobiliaria.
- **Promesa:** cobrar los arriendos sin perseguir a nadie. Las cuentas salen solas y la cartera siempre está al día.
- **Primer usuario:** el fundador, con una casa dividida en 3 unidades arrendadas.
- **Canal del MVP:** solo correo electrónico.
- **Modelo:** varios propietarios aislados entre sí desde el primer día. El cobro de la suscripción se construye después del MVP.

## Alcance del MVP

### Entra

- Registro e inicio de sesión con Google o con correo y contraseña, con los datos de cada propietario aislados.
- Alta guiada en una sola hoja de tres partes: inmueble, unidades y primer contrato.
- Inmuebles, unidades, arrendatarios y contratos, con el contrato firmado como archivo adjunto.
- Generación mensual de la cuenta de cobro en PDF, con consecutivo.
- Envío por correo y dos recordatorios de vencimiento.
- Registro de pagos totales o parciales, con comprobante adjunto y recibo al arrendatario.
- Panel de inicio: esperado, recaudado, pendiente y quién está en mora.
- Listado de cuentas con filtros por unidad y estado, y orden por vencimiento o por estado.
- Configuración de datos del propietario, datos de pago, firma y envíos.

### Queda fuera

- Cobro de la suscripción y límites por plan.
- WhatsApp y cualquier canal distinto al correo.
- Portal del arrendatario.
- Reparto de servicios públicos.
- Pagos en línea y conciliación automática.
- Cálculo automático del incremento anual y de intereses de mora.
- Plantillas de contrato y firma electrónica.
- Facturación electrónica ante la DIAN.
- Reportes, certificados y registro de gastos.
- Aplicación nativa en tiendas, notificaciones push y escritura sin conexión.

## Pantallas

Las diez pantallas diseñadas están en `docs/mockups/` y descritas en `docs/diseno.md`.

| Pantalla | Para qué sirve | Acciones principales |
| --- | --- | --- |
| Inicio | Ver el mes de un vistazo: recaudado, pendiente y en mora | Enviar recordatorio, registrar pago, abrir una cuenta |
| Listado de cuentas | Consultar todas las cuentas, agrupadas por mes | Filtrar por unidad y estado, ordenar por vencimiento o por estado (en pantalla ancha), crear cuenta manual con uno o varios conceptos |
| Detalle de cuenta | Ver el documento, su historial de envíos y el estado de su recargo por mora | Registrar pago, reenviar, descargar PDF, anular, perdonar el recargo o volver a cobrarlo |
| Registrar pago | Anotar un pago en pocos toques | Valor, fecha, medio, comprobante, enviar recibo |
| Inmuebles y unidades | Ver cada inmueble con sus unidades y su estado | Agregar inmueble o unidad, abrir el contrato |
| Contrato | Ver condiciones, lo que se cobra cada mes, documento, correos en copia y cuentas del contrato | Editar (también los conceptos fijos del mes, como la administración, el recargo por mora y los correos en copia), terminar, ver o reemplazar el documento, activar envío automático |
| Configuración | Definir datos del propietario, de pago, la firma, de envío y el tema | Editar datos, subir o dibujar la firma que cierra cada cuenta, verla y quitarla, elegir día de envío y recordatorios, cambiar entre tema claro, oscuro o el del sistema |
| Alta 1: inmueble | Crear el primer inmueble | Nombre, dirección, ciudad, tipo |
| Alta 2: unidades | Definir los espacios que se cobran por separado | Nombre y uso de cada unidad |
| Alta 3: primer contrato | Crear el primer contrato | Arrendatario, correo, correos en copia, canon, día de pago, fechas, subir contrato |

### Pantallas y estados sin diseñar

Hay que construirlos siguiendo el mismo sistema visual:

- Acceso: botón "Continuar con Google" como opción principal y, debajo, correo y contraseña; registro y recuperación de contraseña.
- Crear una cuenta de cobro manual.
- Editar el texto del correo.
- Crear y editar contrato fuera del alta.
- Unidad vacía y contrato sin documento adjunto.
- Estados vacíos (sin inmuebles, sin cuentas), de carga y de error.
- Pantalla sin conexión.

## Flujos principales

### Alta guiada

1. El propietario entra con Google, o se registra con correo y contraseña y confirma su correo.
2. Crea su primer inmueble.
3. Define las unidades del inmueble.
4. Crea el primer contrato y, si quiere, sube el documento firmado. Este paso se puede saltar.
   Las tres partes van en una sola hoja: cada una se confirma con «Continuar» y se puede volver a abrir antes de crear. Nada se guarda hasta «Crear inmueble»; recargar la página no borra lo escrito.
5. Ve qué quedó creado y los siguientes pasos, y llega al inicio. Los demás contratos se agregan desde cada unidad.

### Ciclo mensual de cobro

1. El día configurado, el sistema genera una cuenta por cada contrato activo.
2. Envía la cuenta por correo al arrendatario, con el PDF adjunto.
3. Si la cuenta sigue sin pagar al día siguiente del vencimiento, envía el primer recordatorio.
4. Si sigue sin pagar a los 7 días, envía el segundo.
5. El propietario registra el pago cuando lo recibe.
6. El sistema envía el recibo al arrendatario y actualiza el inicio.

### Registro de un pago

1. El propietario abre la cuenta desde el inicio o el listado.
2. El valor viene prellenado con el saldo; lo cambia si fue un abono.
3. Indica fecha y medio de pago, y adjunta el comprobante si lo tiene.
4. Al guardar, la cuenta queda pagada o parcial según el valor.

## Requisitos no funcionales

- **Aislamiento:** ningún propietario puede ver ni modificar datos de otro. Se valida en el servidor y en la base de datos.
- **Archivos privados:** contratos y comprobantes sin acceso público. Formatos: PDF, JPG y PNG.
- **Datos personales:** aplica la Ley 1581 de 2012. Hacen falta política de tratamiento y autorización desde el registro.
- **Plataforma:** PWA instalable en el celular, usable con una mano.
- **Tema:** claro y oscuro. Por defecto sigue al sistema; el propietario puede fijar uno en configuración.
- **Formato local:** pesos colombianos sin decimales, fechas en español y zona horaria de Colombia.
- **PDF inmutable:** cada cuenta se guarda como archivo al emitirse.

## Hoja de ruta posterior al MVP

1. Suscripción y límites por plan (necesaria antes de vender a otros propietarios).
2. Reparto de servicios públicos.
3. Incremento anual del canon con el IPC.
4. Intereses de mora y paz y salvos.
5. Reportes y certificado para la declaración de renta.
6. Portal del arrendatario.
7. WhatsApp como segundo canal.
8. Pago en línea y conciliación automática.
9. Gastos del inmueble.
10. Contratos con plantilla y firma electrónica.
11. Facturación electrónica.
