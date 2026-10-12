# Mockups con la marca nueva

Tres propuestas de UI/UX para Arrendi, hechas con los colores y las fuentes de `../brand-design.md`. Son para elegir una dirección antes de tocar la aplicación: nada de `apps/web` cambió.

## Cómo verlos

Abre `index.html` en el navegador (doble clic; no necesita servidor ni instalación). Muestra las tres propuestas en vivo, en marcos de celular, tablet y escritorio, con un selector de pantalla y el interruptor de tema.

Para probar una propuesta de verdad, ábrela completa y cambia el ancho de la ventana:

| Archivo | Propuesta | Idea |
| --- | --- | --- |
| `propuesta-a-ventanas.html` | A · Ventanas | La casa del logo es la interfaz: cada unidad es una ventana encendida según su estado |
| `propuesta-b-libro.html` | B · Libro | Un libro de cobro: lista y detalle lado a lado, pago en el mismo panel |
| `propuesta-c-hoy.html` | C · Hoy | La app dice qué hacer hoy, en orden; cobrar es una pantalla completa con teclado |

Necesitan conexión solo para cargar las fuentes de Google Fonts.

## Qué incluye cada una

- Cinco pantallas navegables: Inicio, Cuentas, Detalle de cuenta, Registrar pago e Inmuebles.
- Tema claro y oscuro.
- Tres tamaños: celular (375), tablet (768) y escritorio (1280). Cambia la navegación y la composición, no solo el ancho.
- Los mismos datos de ejemplo: 2 inmuebles, 6 unidades y las cuentas de agosto a octubre de 2026, con una vencida, una parcial y una pendiente.

Registrar un pago funciona: la cuenta cambia de estado y el resumen se recalcula. Al recargar la página vuelve al inicio. Lo que está fuera de las cinco pantallas (crear cuenta, ajustes, contratos, anular) responde con un aviso.

Cada pantalla tiene dirección propia, útil para compartir una vista exacta: `#home`, `#bills`, `#bill/43`, `#pay/43`, `#properties`, y `?theme=dark` o `?theme=light` antes del `#`.

La propuesta B, la elegida, tiene además el panel de unidad y contrato (`#unit/u2`, o `#unit/u5` para una unidad sin contrato), el botón para editar cada inmueble y el historial de la cuenta con hora.

## Qué mirar

- **Inicio:** ¿entiendes en tres segundos cuánto falta y a quién cobrarle?
- **Registrar pago:** ¿cuántos toques desde el inicio hasta «Guardar»?
- **Escritorio:** ¿aprovecha el espacio o es un celular estirado?
- **Tema oscuro:** ¿los estados siguen distinguiéndose?

## Lo que es igual en las tres

- Colores de marca: navy `#14264C`, verde `#28B779`, amarillo `#FFC857`, marfil `#F4F1E8`. El verde y el amarillo nunca van como texto sobre claro.
- Fuentes: Red Hat Display en títulos y cifras, Inter en la interfaz.
- Colores de estado derivados de la marca (pagada, parcial, pendiente, vencida, anulada), con su versión oscura. Siempre van con ícono y etiqueta.
- Solo usan datos que la API ya entrega.

## Notas

- El logotipo se dibuja con el isotipo de `../arrendi-logo.svg` y el nombre en Red Hat Display 900; no es el archivo final del logo.
- Los archivos son autónomos: estilos, datos e íconos van dentro de cada HTML.
