# Estadísticas de desarrollo

Registro del tiempo y de los tokens usados al construir Arrendi con Claude Code. Los datos salen del registro de cada sesión.

## Sesión 1: etapas 1 y 2

Del 10 de octubre de 2026, 6:53 p. m., al 11 de octubre de 2026, 3:14 a. m. (hora de Colombia). Cubre la etapa 1 (base) y la etapa 2 (inmuebles y contratos) completas.

### Tiempo

| Medida | Horas |
| --- | --- |
| De principio a fin | 8,4 |
| Tiempo activo, sin pausas de más de 15 minutos | 5,9 |
| Tiempo activo, sin pausas de más de 5 minutos | 3,7 |

El trabajo real está entre 4 y 6 horas. El resto son esperas: las pruebas del fundador en Vercel, Supabase y el iPhone.

Fueron 75 mensajes del fundador y 345 respuestas de Claude.

### Tokens

| Modelo | Entrada nueva | Escritura en caché | Lectura de caché | Salida | Total |
| --- | --- | --- | --- | --- | --- |
| Opus 5.5 | 594 | 1.410.372 | 72.025.089 | 404.468 | 73,8 millones |
| Sonnet 5.5 | 214 | 495.061 | 13.471.004 | 84.928 | 14,1 millones |
| **Total** | 808 | 1.905.433 | 85.496.093 | 489.396 | **87,9 millones** |

El 97 % son lecturas de caché: en cada turno se relee la conversación acumulada, y eso se cobra a una fracción del precio normal. Lo escrito por el modelo fueron unos 490.000 tokens.

### Costo

Sin calcular. No se tenían las tarifas vigentes de los dos modelos al cerrar la sesión.

- El comando `/cost` de Claude Code muestra el costo de una sesión con las tarifas reales.
- Con un plan de suscripción (Pro o Max) no se paga por token: la sesión consume cuota, no dinero adicional.

Para calcularlo a mano, se multiplica cada columna de la tabla por su tarifa por millón de tokens (entrada, escritura en caché, lectura de caché y salida) de cada modelo.

### Qué se entregó

- **Etapa 1:** monorepo, API con FastAPI, acceso con Google y con correo, aislamiento por propietario, PWA instalable y despliegue en Vercel.
- **Etapa 2:** inmuebles, unidades, arrendatarios y contratos; alta guiada; documento del contrato con subida directa a Storage; caché de datos en la web con TanStack Query.
- 277 pruebas en la API y 9 en la web.
