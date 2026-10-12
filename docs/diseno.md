# Diseño

El sistema visual sale de la marca (`docs/new-brand-design/brand-design.md`) y de la propuesta elegida en la etapa 6: «Libro», en `docs/new-brand-design/mockups/propuesta-b-libro.html`. Ese mock se abre en el navegador y es la referencia de estructura; este documento fija los valores.

Los mockups anteriores (`docs/mockups/`) quedan como registro y ya no guían el diseño.

## Principios

- Un libro de cobro: todo es lista y detalle. Al abrir una cuenta o un contrato, la lista sigue a la vista.
- Sobrio: superficies claras, navy en la navegación y en los títulos, y color casi solo en los estados.
- El estado siempre se dice con ícono y texto, nunca solo con color.
- Funciona en celular, tablet y escritorio. Cambia la composición, no solo el ancho.
- Los números usan cifras tabulares para que las columnas de dinero alineen.

## Marca

| Color | Valor | Uso |
| --- | --- | --- |
| Navy | `#14264C` | Riel, texto, botón principal |
| Verde | `#28B779` | Ventanas del isotipo y marca de la sección activa. Nunca como texto sobre claro |
| Amarillo | `#FFC857` | Foco en tema oscuro. Nunca como texto |
| Marfil | `#F4F1E8` | Texto sobre navy, texto del tema oscuro |

El logo tiene dos archivos en `docs/new-brand-design/`: `arrendi-logo.svg` (navy, para fondo claro) y `arrendi-logo-blanco.svg` (blanco, para fondo oscuro). Solo cambian de color; el trazo es el mismo. `components/Brand.tsx` dibuja ese trazo: `Brand` es el logo completo y `BrandMark` el isotipo solo. Por defecto siguen al tema (navy en claro, blanco en oscuro); con `tone="white"` quedan blancos, como en el riel. El PDF dibuja el isotipo navy con el trazo de `isotype.svg` (`app/pdf/logo.py`).

## Colores

Son variables de tema en `app/globals.css`; los componentes usan los nombres de Tailwind, nunca los valores. Las que tienen equivalente en shadcn/ui llevan su nombre, para que sus componentes salgan con el aspecto de Arrendi. `secondary` y `accent` son la selección (fila abierta); `muted` es el fondo al pasar el cursor y el de los encabezados de grupo.

| Nombre | Claro | Oscuro | Uso |
| --- | --- | --- | --- |
| `background` | `#F5F6F9` | `#0A1122` | Fondo de la aplicación |
| `card` | `#FFFFFF` | `#111B33` | Tarjetas, tablas, panel de detalle |
| `foreground` | `#14264C` | `#F4F1E8` | Texto principal |
| `muted-foreground` | `#55607A` | `#A9B3CC` | Etiquetas y texto de apoyo |
| `foreground-soft` | `#33456E` | `#CFD6E6` | Texto sobre el fondo interno de una tarjeta |
| `muted` | `#EEF0F5` | `#18243F` | Cursor encima, encabezado de grupo, pista de una barra |
| `accent` | `#E9EDF7` | `#1D2B4D` | Fila abierta en el panel |
| `border` | `#DFE3EC` | `#26345A` | Borde de tarjetas y divisores |
| `input` | `#B8C0D2` | `#53648F` | Borde de campos y botones secundarios |
| `border-dashed` | `#8A93A8` | `#7C87A3` | Botones de agregar y subir |
| `primary` | `#14264C` | `#F4F1E8` | Botón principal, selección |
| `primary-foreground` | `#F4F1E8` | `#14264C` | Texto sobre el primario |
| `destructive` | `#A3321E` | `#FF9D88` | Campo con error |
| `ring` | `#2F4A94` | `#FFC857` | Anillo de foco |
| `overlay` | navy al 45 % | casi negro al 70 % | Velo detrás de un diálogo |
| `rail` | `#14264C` | `#0E1830` | Riel y barra inferior |
| `rail-foreground`, `rail-muted` | `#F4F1E8`, `#A9B3CC` | igual | Sección activa y las demás |
| `chart-bar` | `#14264C` | `#8FA6E6` | Barra de lo recaudado |

### Estados

Cada estado tiene tres variables: el nombre solo rellena una marca (barra de la fila, punto de la leyenda, tramo de una gráfica), `-ink` es el texto y `-tint` su fondo.

| Tono | Relleno claro / oscuro | Texto claro / oscuro | Se usa en |
| --- | --- | --- | --- |
| `positive` | `#1FA36C` / `#25A870` | `#14734B` / `#6BDDAA` | Pagada, Al día, Activo, mensajes de éxito |
| `warning` | `#D4951A` / `#C08618` | `#7A5200` / `#FFC857` | Parcial, Pago parcial |
| `info` | `#4C6FC4` / `#6485DA` | `#2F4A94` / `#A9BEF5` | Pendiente, avisos |
| `alert` | `#D2513A` / `#E05F47` | `#A3321E` / `#FF9D88` | Vencida, En mora, errores, acciones destructivas |
| `neutral` | `#8A90A0` / `#7C87A3` | `muted-foreground` | Anulada, Vacía, Terminado |

Los cuatro rellenos se validaron como paleta (separación para daltonismo y contraste) en claro y en oscuro. El ámbar tiene poco contraste contra el fondo claro: por eso nunca va sin etiqueta.

### Tema claro y oscuro

- **Tres opciones:** claro, oscuro y "igual que el sistema", que es la opción por defecto. El selector está en Ajustes.
- **Implementación:** `next-themes` con la clase `dark` en el elemento raíz. La elección se guarda en el dispositivo y se aplica antes de pintar.
- **El riel es navy en los dos temas.**
- **En oscuro, el botón primario es marfil con texto navy,** al revés que en claro. No escribas texto fijo sobre el primario: usa `primary-foreground`.
- **PDF y correos:** siempre en claro.

## Tipografía

- **Inter** (400, 500, 600): interfaz, tablas, formularios.
- **Red Hat Display** (700, 800, 900): títulos y cifras destacadas. Es la clase `font-heading`; todo `h1` la lleva.
- **Cifras:** `font-variant-numeric: tabular-nums` en toda la aplicación.

| Clase | Tamaño | Uso |
| --- | --- | --- |
| `text-figure` | 34 px | Saldo de una cuenta |
| `text-title-onboarding` | 26 px | Título del alta guiada |
| `text-title` | 24 px | Título de sección |
| `text-kpi` | 22 px | Cifra del resumen |
| `text-title-back` | 18 px | Título de un detalle, nombre de un inmueble |
| `text-body` | 16 px | Campos y botón principal |
| `text-section` | 15 px | Filas, encabezados de sección |
| `text-support` | 13 px | Texto de apoyo |
| `text-badge` | 12 px | Etiqueta de estado, encabezado de columna |

## Medidas

- Margen lateral: 16 px en celular, 24 px en tablet, 32 px en escritorio. Dentro del panel, 20 px.
- Radio: 14 px en tarjetas y tablas, 10 px en botones y campos, completo en etiquetas.
- Altura de campos y botón principal: 48 px. Botón secundario: 44 px.
- Objetivo táctil mínimo: 44 px. La única excepción es el botón `sm` de una fila, que con ratón mide 36 px.

## Estructura

| Ancho | Navegación | Lista y detalle |
| --- | --- | --- |
| Celular (menos de 768 px) | Cabecera con el isotipo y el nombre, y barra inferior navy con las cuatro secciones. Las dos se ocultan al abrir un detalle | El detalle ocupa toda la pantalla; "volver" regresa a la lista |
| Tablet (768 px o más) | Riel navy de 68 px a la izquierda | Lista y panel de 360 px lado a lado |
| Escritorio (1280 px o más) | Igual | El panel mide 408 px |

- **Secciones:** Resumen (`/`), Cuentas, Inmuebles y Ajustes. La sección activa lleva una marca verde.
- **Panel:** en Cuentas e Inmuebles, toda ruta que no sea la lista se dibuja en el panel: el detalle de una cuenta, registrar un pago, el contrato y todos los formularios. Las rutas no cambiaron; lo hace el `layout` de cada sección con `ListDetail`.
- **Desde el resumen,** abrir una cuenta lleva a Cuentas con esa cuenta en el panel.
- **Fuera de la estructura:** acceso, alta guiada y la pantalla sin conexión van en una columna centrada de 480 px (`Column`).
- **Tablas que se adaptan solas:** una tabla acomoda sus filas según su propio ancho (consultas de contenedor), no el de la ventana. Por eso la misma tabla sirve a todo el ancho y apretada junto al panel: con menos de 600 px cada fila se apila en dos líneas.

## Componentes

Se construyen sobre shadcn/ui (con Radix), ajustando variantes y medidas a este diseño. "Propio" significa que se arma con Tailwind.

| Componente | Base | Descripción |
| --- | --- | --- |
| `AppShell` | propio | Riel o barra inferior, y el contenido |
| `ListDetail`, `ListMain` | propio | Lista y panel de detalle; el cuerpo de una lista |
| `Column` | propio | Columna centrada de las pantallas fuera de la estructura |
| `Brand`, `BrandMark` | propio | Isotipo, solo o con el nombre |
| `Header` | propio | Título de sección con su acción, o título de un detalle con "volver" |
| `BillTable`, `BillGroup`, `BillRow` | propio | Tabla de cuentas: encabezados, grupo por mes y fila con barra de estado. La fila abierta queda resaltada. Admite botones por fila |
| `BillStatusBadge`, `UnitStatusBadge` | `Badge` | Estado con ícono y texto |
| `Badge` | `Badge` | Pastilla con cinco tonos: `positive`, `warning`, `info`, `alert`, `neutral` |
| `Button` | `Button` | Tamaños `default` (48 px), `md` (44 px), `sm` (44 px; 36 px con ratón) e `icon`. Variantes `default`, `outline`, `dashed`, `ghost`, `destructive` y `link` |
| `FormField`, `TextareaField`, `MoneyField`, `SelectField` | `Field`, `Input`, `Select` | Etiqueta arriba, campo de 48 px, ayuda debajo |
| `ToggleGroup` | `ToggleGroup` | Opciones con una elegida (tipo de inmueble, medio de pago). En Cuentas, como control segmentado para el filtro de estado |
| `Switch` | `Switch` | Enviar recibo, envío automático |
| `AlertDialog` | `AlertDialog` | Anular cuenta, terminar contrato, eliminar pago |
| `FormScreen` | propio | Marco de un formulario: volver, el formulario y "guardar" en el pie |
| `ActionFooter` | propio | Franja inferior fija con la acción principal de un detalle |
| `FormMessage` | propio | Mensaje con tres tonos: `error`, `success` e `info` |
| `Loading`, `LoadError` | propio | Carga y error de una pantalla |

- `cn` se importa siempre de `@/lib/utils`, que conoce los tamaños de letra propios.
- El dinero y las fechas se muestran con `lib/format.ts`, nunca con `Intl` directo. `formatDateHour` da fecha y hora de Colombia: `5 oct 2026 · 3:42 p. m.`.
- Los formularios usan React Hook Form con Zod solo para validar la forma; las reglas de negocio se validan en la API.
- Los íconos son de Lucide, de trazo, sin relleno.
- Antes de agregar un componente de shadcn/ui, confirma en su documentación vigente que existe con ese nombre.

### Gráficas

Solo en el resumen, hechas con Tailwind, sin librería.

- **Cómo va el mes:** una barra con lo esperado repartido en recaudado, saldo de abonos, por vencer y vencido. Debajo, la leyenda con etiqueta, valor y porcentaje de cada tramo.
- **Recaudo por mes:** hasta seis meses; la pista es lo esperado y la barra, lo recaudado, con su valor encima. Se calcula del listado de cuentas.
- Un solo eje, sin doble escala. Los colores de estado no se usan para otra cosa.

### Historial de una cuenta

Línea de tiempo, de lo más antiguo a lo más reciente: generada, cada correo, cada pago y la anulación. Cada evento lleva ícono, texto, y fecha y hora. Un correo que falló o rebotó se marca en tono `alert`.

## Mapa de pantallas

| Ruta | Pantalla | Dónde se dibuja |
| --- | --- | --- |
| `/login`, `/signup`, `/reset-password`, `/update-password` | Acceso | Columna |
| `/onboarding/property`, `/onboarding/units`, `/onboarding/lease` | Alta guiada | Columna |
| `/` | Resumen | Sección |
| `/bills` | Cuentas | Sección (lista) |
| `/bills/new` | Cuenta manual | Panel de Cuentas |
| `/bills/[id]` | Detalle de cuenta | Panel de Cuentas |
| `/bills/[id]/payment` | Registrar pago | Panel de Cuentas |
| `/properties` | Inmuebles | Sección (lista) |
| `/properties/new`, `/properties/[id]/edit` | Crear y editar un inmueble | Panel de Inmuebles |
| `/properties/[id]/units/new`, `/units/[id]/edit` | Agregar y editar una unidad | Panel de Inmuebles |
| `/leases/new?unit=...` | Crear el contrato de una unidad vacía | Panel de Inmuebles |
| `/leases/[id]` | Contrato | Panel de Inmuebles |
| `/leases/[id]/edit` | Editar contrato | Panel de Inmuebles |
| `/settings` | Ajustes | Sección |

## Diferencias entre el mock y lo que se construye

- Los nombres, valores y fechas del mock son datos de ejemplo.
- El mock abre la cuenta en un panel sobre cualquier pantalla. En la aplicación el panel pertenece a su sección: desde el resumen, la cuenta se abre en Cuentas.
- El panel de la unidad del mock es, en la aplicación, la pantalla del contrato. Una unidad vacía abre directamente "Crear contrato".
- Cada fila de unidad tiene además un lápiz para editarla; "Editar unidad" también está al final del contrato, entre "Editar contrato" y "Terminar contrato".
- El detalle de cuenta conserva lo que el mock no trae: la vista previa del documento, la sección "Pagos" con comprobante y eliminar, y los botones "Enviar" o "Reenviar", "Recordar", "Descargar PDF" y "Anular" en el pie.
- El contrato conserva "Generar cuenta del mes", "Cobrar otro concepto" y el depósito.
- En Cuentas, el filtro de estado no lleva contador y tiene "Anuladas" en lugar de "Vencidas".
- En el resumen, una línea dice cuánto se debe de meses anteriores y los correos rebotados salen como aviso. En celular, los botones de cada cuenta por cobrar van bajo la fila, para registrar un pago en dos toques.
- El PDF sigue en Helvetica, que trae todo lector de PDF: así no viaja ningún archivo de fuente con la API. Lleva la paleta de la marca, una franja navy arriba y el isotipo en el pie, sin el nombre, igual que los correos.
- Los correos llevan la paleta de la marca, sin cabecera: son del arrendador. Al pie va el isotipo, centrado. Viaja dentro del correo como imagen incrustada (PNG de `isotype.svg`, en `app/email/assets/`), porque los lectores de correo no dibujan SVG. La versión de texto plano no nombra a Arrendi.
