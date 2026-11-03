# Resumen: meses anteriores y total acumulado

Tres propuestas para la pantalla de inicio: un selector de mes con flechas ‹ › y un widget con el total acumulado. Nada de `apps/web` ni de la API cambió.

## Decisiones ya tomadas

- **Total:** acumulado histórico (facturado, cobrado y pendiente de todas las cuentas no anuladas). No cambia al mover el mes.
- **Selector:** flechas anterior y siguiente junto al título del mes. La flecha derecha se desactiva en el mes en curso.
- **Mes pasado:** cambian las cifras del mes, «Cómo va el mes» y «Pagadas». «Por cobrar» sigue mostrando la deuda real de hoy, con «Recordar» y «Registrar pago».

## Cómo verlas

Abre `index.html` en el navegador (doble clic; no necesita servidor). Arriba se cambia entre las tres propuestas y el tema claro u oscuro. Los datos son de ejemplo: una casa de 3 unidades con arriendo de $1.200.000 y hoy simulado el 3 nov 2026.

| Propuesta | Idea |
| --- | --- |
| A · Tarjeta arriba | El total va primero, en una tarjeta oscura con lo pendiente en grande |
| B · Franja | El total es una línea discreta bajo «Cómo va el mes» |
| C · Lateral | Columna lateral en escritorio y panel plegable en celular |

## Elegida

La **A · Tarjeta arriba** (3 nov 2026), en `apps/web/components/HomeScreen.tsx`. El saludo va encima del mes, con las flechas y el título debajo.
