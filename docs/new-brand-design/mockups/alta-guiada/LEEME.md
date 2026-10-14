# Alta guiada: cinco propuestas

Mocks para rehacer el alta guiada (inmueble, unidades y primer contrato) antes de cerrar la etapa 6. Usan el sistema de diseño actual: los tokens de `base.css` tienen los mismos nombres y valores que `apps/web/app/globals.css` (`docs/diseno.md`). Nada de `apps/web` cambió.

## Cómo verlos

Abre `index.html` en el navegador (doble clic; no necesita servidor). Muestra las cinco propuestas en vivo, en celular y escritorio, con un selector de pantalla y el interruptor de tema. Cada una se puede abrir completa y llenar de verdad: valida los campos, avanza, vuelve y termina.

| Archivo | Propuesta | Idea |
| --- | --- | --- |
| `1-libro-en-vivo.html` | 1 · Libro en vivo | Los tres pasos de hoy, pulidos; en escritorio, Inmuebles se arma al lado |
| `2-la-casa-se-arma.html` | 2 · La casa se arma | La casa del isotipo con una ventana por unidad; el contrato se elige tocando la ventana |
| `3-una-pregunta.html` | 3 · Una pregunta a la vez | Conversación: una pregunta por pantalla, Enter para seguir y revisión al final |
| `4-una-sola-hoja.html` | 4 · Una sola hoja | Checkout: las tres partes en una página, con resumen fijo |
| `5-tu-primera-cuenta.html` | 5 · Tu primera cuenta | La cuenta de cobro se llena en vivo mientras escribes |

Cada pantalla tiene dirección propia: `#welcome`, `#property`, `#units`, `#lease` y `#done`, y `?theme=dark` o `?theme=light` antes del `#`. Abierta directamente en un paso intermedio, la propuesta trae datos de ejemplo; recorrida desde el principio, guarda solo lo que escribes.

## Lo que es igual en las cinco

- La misma llamada: `POST /api/onboarding` con inmueble, unidades (1 a 50) y un contrato opcional. Sin rutas ni reglas nuevas.
- Los campos y mensajes de error de `PropertyForm` y `LeaseForm`. Nada se guarda hasta el final.
- Bienvenida y cierre, que hoy no existen.
- El contrato siempre se puede dejar para después.

## Archivos

- `base.css`: tokens y componentes (campos, botones, grupos de opciones, interruptor, mensajes), en claro y oscuro.
- `base.js`: íconos de Lucide, el isotipo, el tema, los datos de ejemplo, el borrador, la validación y el enrutador por `#`.
