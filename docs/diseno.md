# Diseño

El sistema visual sale de los mockups. El marcado de cada pantalla está en `docs/mockups/`: úsalo como referencia de estructura, medidas y textos. Esos archivos son del editor de diseño y no se abren solos en un navegador; lo útil es el HTML con estilos en línea que contienen.

Lienzo original: <https://claude.ai/artifact/UzWBdHg2VRw3iBEHvmh9nM> (privado del fundador).

## Principios

- Pensado primero para celular (390 px de ancho) y para usar con una mano.
- La acción principal de cada pantalla va abajo, en un pie fijo.
- El estado de una cuenta siempre se dice con texto, nunca solo con color.
- Los números usan cifras tabulares para que las columnas de dinero alineen.

## Colores

Defínelos como variables de tema en Tailwind; no escribas los valores sueltos en los componentes.

shadcn/ui trae sus propias variables de tema (`background`, `foreground`, `primary`, `border`, `destructive` y otras). Los colores de la tabla que tienen equivalente llevan el nombre de esa variable, para que los componentes salgan ya con el aspecto de Arrendi. Además, `surface` se asigna también a `card` y `popover`, `alert` a `destructive`, y `primary` a `ring`. Los colores que no tienen equivalente (tintes y estados) se agregan como variables propias, con el nombre de la tabla.

shadcn/ui usa además tres parejas que el diseño no nombra. Se asignan así: `secondary` y `accent` toman `primary-tint` con texto `primary-strong` (selección), y `muted` toma el valor de `border` (fondo al pasar el cursor). Las variables de gráficas y de barra lateral de shadcn/ui no se usan y se quitaron. Cada variable tiene un valor para el tema claro y otro para el oscuro.

| Nombre | Claro | Oscuro | Uso |
| --- | --- | --- | --- |
| `background` | `#F3F5F4` | `#0F1513` | Fondo de la aplicación |
| `surface` | `#FFFFFF` | `#18201D` | Tarjetas, pie, barra de navegación |
| `foreground` | `#14201C` | `#E8EEEB` | Texto principal |
| `muted-foreground` | `#55635E` | `#A3B0AB` | Etiquetas y texto de apoyo |
| `foreground-soft` | `#3A4743` | `#C5CFCB` | Texto sobre el fondo interno de una tarjeta |
| `border` | `#E1E6E3` | `#26302C` | Borde de tarjetas y divisores |
| `input` | `#C9D1CD` | `#6B7A73` | Borde de campos y botones secundarios |
| `border-dashed` | `#8E9A95` | `#8E9A95` | Botones de agregar y subir |
| `primary` | `#0F6B4F` | `#3FB58E` | Botón principal, enlaces, selección |
| `primary-foreground` | `#FFFFFF` | `#06231A` | Texto sobre un botón primario |
| `primary-strong` | `#0A4E3A` | `#9FE0C8` | Texto sobre el tinte primario |
| `primary-tint` | `#D9EFE6` | `#143B2E` | Fondo de selección y de la etiqueta "pagada" |
| `alert` | `#8A3D06` | `#F2A66B` | Texto de "vencida" y acciones destructivas |
| `alert-tint` | `#FBE6D4` | `#40240F` | Fondo de la etiqueta "vencida" |
| `info` | `#1D4E89` | `#8DB8EC` | Texto de "parcial" |
| `info-tint` | `#DCE9F8` | `#15294A` | Fondo de la etiqueta "parcial" |
| `overlay` | `#14201C` al 50 % | negro al 65 % | Velo detrás de un diálogo de confirmación |
| `summary` | `#0F6B4F` | `#0F6B4F` | Fondo de la tarjeta resumen del inicio |
| `summary-inner` | `#0A4E3A` | `#0A4E3A` | Recuadros dentro de la tarjeta resumen |
| `summary-foreground` | `#FFFFFF` | `#FFFFFF` | Cifras sobre la tarjeta resumen |
| `summary-foreground-soft` | `#D6EDE4` | `#D6EDE4` | Texto de apoyo sobre la tarjeta resumen |

### Tema claro y oscuro

- **Tres opciones:** claro, oscuro y "igual que el sistema", que es la opción por defecto. El selector está en configuración.
- **Implementación:** `next-themes` con la clase `dark` en el elemento raíz, que es como lo espera shadcn/ui. La elección se guarda en el dispositivo.
- **Sin parpadeo:** el tema se aplica antes de pintar la página, para que no se vea un destello claro al abrir en oscuro.
- **La tarjeta resumen es igual en ambos temas:** verde con texto blanco. Es el único bloque que no se invierte.
- **En oscuro, el botón primario es verde claro con texto oscuro,** al revés que en claro. Por eso existe la variable `primary-foreground`: no escribas texto blanco fijo sobre el primario.
- **El tema oscuro no tiene mockups.** La paleta oscura se derivó de la clara; el contraste de texto se calculó y cumple AA (4,5:1 o más) en todas las combinaciones de la tabla, pero nadie la ha visto aplicada. Revísala en pantalla durante la etapa 1 y ajusta los valores aquí si algo no se ve bien.
- **PDF y correos:** siempre en claro.

## Tipografía

- **Familia:** Figtree (Google Fonts), pesos 400, 500, 600 y 700.
- **Cifras:** `font-variant-numeric: tabular-nums` en toda la aplicación.

| Uso | Tamaño | Peso |
| --- | --- | --- |
| Cifra principal del inicio | 34 px | 700 |
| Título del alta guiada | 26 px | 700 |
| Título de pantalla | 22 px | 700 |
| Título con botón de volver | 18 px | 700 |
| Texto de fila y de botón | 15 a 16 px | 600 |
| Encabezado de sección | 15 px | 600 |
| Texto de apoyo | 13 px | 400 |
| Etiqueta de estado | 12 px | 600 |

## Medidas

- Margen lateral de pantalla: 20 px.
- Radio: 16 px en tarjetas, 12 a 14 px en botones y campos, 8 px en etiquetas, 22 px en botones redondos y filtros.
- Altura de campos: 48 px. Botón principal: 52 px. Botón secundario: 44 a 48 px.
- Objetivo táctil mínimo: 44 px.

## Componentes

Los componentes se construyen sobre shadcn/ui (con Radix como librería base), ajustando sus variantes y medidas a este diseño. La columna "Base" indica de qué componente de shadcn/ui parte cada uno; "propio" significa que se arma con Tailwind.

| Componente | Base en shadcn/ui | Descripción |
| --- | --- | --- |
| `StatusBadge` | `Badge` | Pastilla con texto: Pagada, Parcial, Vencida, Al día, En mora, Activo, Anulada. `Badge` tiene cuatro tonos: `positive` (Pagada, Al día, Activo), `alert` (Vencida, En mora), `info` (Parcial) y `neutral` (Vacía, Terminado, Anulada) |
| `Card` | `Card` | Superficie blanca con borde y radio de 16 px |
| `BillRow` | propio | Unidad y arrendatario a la izquierda; valor y estado a la derecha; toda la fila es un enlace |
| `SummaryCard` | `Card` y `Progress` | Bloque primario con recaudado, esperado, barra de avance y dos cifras |
| `PrimaryButton` | `Button` | Fondo primario, 52 px de alto, ancho completo |
| `SecondaryButton` | `Button`, variante `outline` | Borde, fondo blanco |
| `DashedButton` | `Button`, variante propia | Borde punteado; para agregar o subir |
| `FormField` | `Field`, `Label` e `Input` | Etiqueta arriba, campo de 48 px, ayuda opcional debajo |
| `MoneyField` | `FormField` | Campo de pesos: muestra `$950.000` y solo acepta dígitos |
| `SelectField` | `Field`, `Label` y `Select` | Etiqueta arriba y desplegable de 48 px |
| Desplegables | `Select` | Unidad, uso, día de pago, día de envío |
| Casillas e interruptores | `Checkbox` y `Switch` | Recordatorios, enviar recibo, envío automático |
| `OptionPicker` | `ToggleGroup` | Cuadrícula de botones con uno seleccionado (tipo de inmueble, medio de pago) |
| `FilterChips` | `ToggleGroup` | Pastillas de 44 px con una activa |
| Confirmaciones | `AlertDialog` | Anular cuenta, terminar contrato, eliminar pago |
| Avisos | `Sonner` | "Pago guardado", "Cuenta enviada", errores |
| Carga | `Skeleton` | Mientras llegan los datos |
| `BottomNav` | propio | Cuatro pestañas: Inicio, Cuentas, Inmuebles, Ajustes. Solo muestra las pantallas que ya existen: Inicio e Inmuebles en la etapa 2 |
| `Header` | propio | Título, con botón de volver o acción a la derecha |
| `ActionFooter` | propio | Franja blanca inferior con la acción principal |
| `FormScreen` | propio | Marco de una pantalla que edita una cosa: volver, el formulario y "guardar" en el pie |
| `FormMessage` | propio | Mensaje sobre toda la pantalla, con tres tonos: `error`, `success` e `info` |
| `OnboardingSteps` | propio | "Paso N de 3" y barra de tres segmentos |

- Los nombres de los componentes de shadcn/ui cambian entre versiones. Antes de agregar uno, confirma en su documentación vigente que existe con ese nombre y cómo se instala.
- Los tamaños por defecto de shadcn/ui son más pequeños que los de este diseño. Ajusta las variantes de `Button`, `Input` y `Select` a las alturas de la sección "Medidas", en lugar de sobrescribirlas en cada uso.
- `Button` tiene los tamaños `default` (52 px, acción principal), `md` (48 px), `sm` (44 px) e `icon` (44 px, redondo), y las variantes `default`, `outline` (secundario), `dashed` (agregar o subir), `ghost`, `destructive` y `link`. No hay tamaños menores a 44 px.
- Los tamaños de letra de la tabla de tipografía son clases de Tailwind: `text-figure`, `text-title-onboarding`, `text-title`, `text-title-back`, `text-body`, `text-section`, `text-support` y `text-badge`.
- `cn` se importa siempre de `@/lib/utils`, que conoce esos tamaños de letra. Los componentes de shadcn/ui llegan importándolo del paquete `cn`: cámbialo al agregarlos (el lint lo exige).
- `Select`, `ToggleGroup`, `AlertDialog`, `Badge` y `Switch` ya están adaptados: el desplegable mide 48 px como un campo, las opciones de `ToggleGroup` 48 px, el interruptor 48 por 28 px con área táctil de 44 px, y el diálogo pone la acción arriba y "Cancelar" debajo, a todo el ancho.
- El dinero y las fechas se muestran con `formatPesos` y `formatDate` de `lib/format.ts`, nunca con `Intl` ni `toLocaleString` directo: su resultado para Colombia cambia entre navegadores.
- Los formularios usan React Hook Form con Zod solo para la validación de forma en el navegador (campo vacío, correo mal escrito). Las reglas de negocio se validan en la API.

Los íconos son de Lucide, que es la librería que usa shadcn/ui: de trazo, de 2 px, sin relleno.

## Mapa de pantallas

| Ruta | Pantalla | Mockup |
| --- | --- | --- |
| `/login`, `/signup`, `/reset-password` | Acceso | Sin diseñar |
| `/update-password` | Contraseña nueva, al llegar desde el correo de recuperación | Sin diseñar |
| `/onboarding/property` | Alta 1 | `Alta1.dc.html` |
| `/onboarding/units` | Alta 2 | `Alta2.dc.html` |
| `/onboarding/lease` | Alta 3 | `Alta3.dc.html` |
| `/` | Inicio | `Main.dc.html` |
| `/bills` | Listado de cuentas | `Cuentas.dc.html` |
| `/bills/new` | Cuenta manual | Sin diseñar |
| `/bills/[id]` | Detalle de cuenta | `Cuenta.dc.html` |
| `/bills/[id]/payment` | Registrar pago | `Pago.dc.html` |
| `/properties` | Inmuebles y unidades | `Inmuebles.dc.html` |
| `/properties/new`, `/properties/[id]/edit` | Crear y editar un inmueble | Sin diseñar; sigue a Alta 1 |
| `/properties/[id]/units/new`, `/units/[id]/edit` | Agregar y editar una unidad | Sin diseñar |
| `/leases/new?unit=...` | Crear el contrato de una unidad vacía | Sin diseñar; sigue a Alta 3 |
| `/leases/[id]` | Contrato | `Contrato.dc.html` |
| `/leases/[id]/edit` | Editar contrato | Sin diseñar; sigue a Alta 3 |
| `/settings` | Configuración | `Ajustes.dc.html` |
| `/settings/email` | Texto del correo | Sin diseñar |

## Diferencias entre los mockups y lo que se construye

- Los nombres, valores y fechas de los mockups son datos de ejemplo.
- En configuración, el desplegable "Enviar las cuentas" del mockup ofrece tres opciones. En el MVP es un selector del día del mes (1 a 28); la aprobación previa se controla por contrato con "Enviar cuentas automáticamente".
- En el escritorio, el contenido se centra en una columna de 480 px como máximo. No hay diseño de escritorio propio en el MVP.
- Los mockups solo muestran el tema claro.
- El selector de tema en configuración no aparece en el mockup; va como una sección más, "Apariencia".
- En el contrato, la sección "Cuentas de cobro" del mockup llega en la etapa 3, y "Próximo incremento" no se construye: el incremento anual está fuera del MVP.
- En inmuebles, cada fila de unidad tiene además un botón de lápiz para editarla, que el mockup no trae. Una unidad vacía dice "Crear contrato" y lleva a crearlo.
- En el contrato, el texto bajo "Enviar cuentas automáticamente" no menciona el día de envío hasta que exista la configuración (etapa 4).
- La marca visible es el nombre "Arrendi" en texto, en el acceso y en el pie del PDF. No hay logo todavía. El ícono de la aplicación instalada es provisional: una "A" blanca sobre el verde primario.
