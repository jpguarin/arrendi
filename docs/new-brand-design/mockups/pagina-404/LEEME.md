# Página no encontrada: cuatro propuestas

Mocks de la página 404: lo que ve quien abre una dirección que no existe (un enlace viejo, uno mal copiado o una ruta escrita a mano). Hoy la web no tiene `app/not-found.tsx` y sale la página por defecto de Next.js, en inglés y sin la marca. Nada de `apps/web` ni de la API cambió.

Usan el mismo sistema que `../alta-guiada/`: cargan su `base.css` y su `base.js` (tokens, íconos, marca y tema), más `nf.css` y `nf.js`, que agregan lo propio de esta ronda: la dirección, el estado de la sesión, la sugerencia y los botones.

## Cómo verlos

Abre `index.html` en el navegador (doble clic; no necesita servidor). Muestra las cuatro en vivo, en celular (390), tablet (820) y escritorio (1366), con un selector de sesión, uno de dirección y el interruptor de tema.

| Archivo | Propuesta | Idea |
| --- | --- | --- |
| `1-columna-sobria.html` | 1 · Columna sobria | La columna de «Sin conexión» con un 404 grande en contorno |
| `2-aqui-no-vive-nadie.html` | 2 · Aquí no vive nadie | El isotipo con las ventanas apagadas; la dirección en una placa |
| `3-dentro-de-la-app.html` | 3 · Dentro de la app | La página dentro del riel, con «¿Buscabas Cuentas?» y las cuatro secciones |
| `4-cuenta-anulada.html` | 4 · La cuenta N.º 404 | Una cuenta en papel con el sello «No existe», como una anulada |

Cada propuesta tiene dos estados: `#in` (con sesión) y `#out` (sin sesión). La dirección que no existe se cambia con `?path=`, por ejemplo `?path=/inmuebles`; sin él es `/cuentas`. También aceptan `?theme=dark` o `?theme=light`.

## Lo que es igual en las cuatro

- **La dirección a la vista,** tal cual y sin interpretarla.
- **Una salida clara.** Con sesión: «Ir al resumen» y «Volver». Sin sesión: «Iniciar sesión» y «Crear cuenta».
- **Solo interfaz.** Es `app/not-found.tsx` de Next, que no es una ruta de API ni lleva reglas de negocio.
- **Accesible:** un `h1`, botones de 44 px o más, contraste AA en claro y oscuro, dibujo decorativo con `aria-hidden` y movimiento que respeta «reducir movimiento».

## Para decidir antes de construir

- **¿Con o sin el riel?** Mostrar el riel (propuesta 3) exige saber si hay sesión al pintar la página. La alternativa es un `not-found.tsx` dentro de `(app)/(shell)` para las rutas de la app y otro en la raíz, en columna, para lo demás.
- **La sugerencia por palabra en español** (propuesta 3) se puede sumar a cualquiera de las otras. ¿Vale la pena, o mejor redirigir `/cuentas` a `/bills` directamente?
- **Un recurso que no existe** (`/bills/999`, o una cuenta de otro propietario) no pasa por esta página: la API responde 404 y la pantalla muestra `LoadError` en el panel. ¿Debe ese caso tener el mismo tono?
