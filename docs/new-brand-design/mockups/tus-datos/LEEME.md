# Tus datos en el alta: cinco propuestas

Mocks para pedir los datos del propietario antes de crear su primer inmueble: tipo y número de documento, datos de pago, firma y día de envío. Son los campos que hoy viven en Ajustes y salen en cada cuenta de cobro. Aquí pasan a ser obligatorios en el alta. Nada de `apps/web` ni de la API cambió.

Usan el mismo sistema que `../alta-guiada/`: cargan su `base.css` y su `base.js` (tokens, íconos, campos, validación y enrutador), más `datos.css` y `datos.js`, que agregan lo propio de esta ronda.

## Elegida

La **2 · Una pregunta a la vez** (19 oct 2026). La cuenta de cobro de la vista previa es copia de la diagramación del PDF que genera la API (`apps/api/app/pdf/bill.py`): Cobra y Debe, recuadro con «Vence» y «Pagar a», firma al pie y pie de página. El día de envío se ve en la fecha de la cuenta.

## Cómo verlos

Abre `index.html` en el navegador (doble clic; no necesita servidor). Muestra las cinco en vivo, en celular (390), tablet (820) y escritorio (1366), con un selector de pantalla y el interruptor de tema. Cada una se puede abrir completa y llenar de verdad: valida, avanza, vuelve y termina.

| Archivo | Propuesta | Idea |
| --- | --- | --- |
| `1-asi-te-veran.html` | 1 · Así te verán | Un formulario en tres bloques y, al lado, la cuenta de cobro en papel que se llena mientras escribes |
| `2-una-pregunta.html` | 2 · Una pregunta a la vez | Cuatro preguntas grandes, Enter para seguir, y una revisión con la cuenta |
| `3-la-hoja-de-siempre.html` | 3 · La hoja de siempre | El alta actual (Una sola hoja) con «Tus datos» como primera parte |
| `4-lista-de-pendientes.html` | 4 · Lista de pendientes | Tablero de cuatro tarjetas en cualquier orden; cada una abre una hoja corta |
| `5-toca-no-escribas.html` | 5 · Toca, no escribas | Lo que se puede adivinar viene puesto (nombre, día sugerido, firma escrita) y tú confirmas |

Cada pantalla tiene dirección propia (por ejemplo `#welcome`, `#data`, `#pay`, `#sign`, `#done`), y `?theme=dark` o `?theme=light` antes del `#`. Abierta directamente en un paso intermedio, la propuesta trae datos de ejemplo; recorrida desde el principio, guarda solo lo que escribes.

## Lo que es igual en las cinco

- **Solo para propietarios nuevos.** Se piden antes del primer inmueble. Quien ya tiene inmuebles no cambia (decidido el 19 oct 2026).
- **Los campos de Ajustes:** nombre (viene de la cuenta de Google), tipo y número de documento, datos de pago, firma y día de envío. Los cinco son obligatorios.
- **Datos de pago armados.** Eliges el banco o la billetera (Nequi, Daviplata), el tipo de cuenta y el número; el texto que lee el arrendatario se arma solo, con el titular. «Prefiero escribirlo yo» deja el texto libre de hoy. La API sigue guardando un solo texto.
- **Firma** dibujada con el dedo o el mouse, o una foto (PNG o JPG, 2 MB), como en Ajustes. La propuesta 5 suma una firma escrita con el nombre.
- **Día de envío** con el 1 como sugerido.
- **Al terminar** sigue el alta de hoy, en `inmueble.html`: la hoja de `../alta-guiada/4-una-sola-hoja.html` puesta al día con la app (país del inmueble, Colombia por defecto, e inventario en el primer contrato). En celular, dirección y ciudad, y arrendatario y correo, van uno debajo del otro. En la 3 es la misma hoja.

## Para decidir antes de construir

- **Firma escrita (propuesta 5):** ¿vale como firma en la cuenta de cobro una imagen hecha con el nombre en letra cursiva?
- **El día sugerido:** ¿el 1, o según el día de pago del primer contrato?
- **Dónde se exige:** la regla de negocio va en la API (`POST /api/onboarding` respondería un error si faltan datos), no solo en la web.
