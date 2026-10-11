# Plan de construcción

Seis etapas, en orden. Cada una termina con sus criterios de aceptación cumplidos y sus casillas marcadas. No se empieza una etapa sin cerrar la anterior.

**Etapa en curso: 1**

---

## Etapa 1. Base

Objetivo: un repositorio que se despliega, con acceso y aislamiento funcionando, sin funcionalidad de negocio todavía.

- [x] Documentos al día: código en inglés y hallazgos de la documentación vigente.
- [ ] Monorepo con Turborepo y pnpm según `CLAUDE.md`: `pnpm-workspace.yaml`, `turbo.json` y los scripts `dev`, `lint`, `test`, `build` y `gen:api` en la raíz.
- [ ] `apps/api/package.json` con scripts que ejecutan la API, las pruebas y el lint desde su entorno de Python.
- [ ] API: FastAPI con `GET /api/health`, configuración por variables de entorno, `ruff` y `pytest`.
- [ ] API: conexión a PostgreSQL con SQLAlchemy, sin reserva de conexiones.
- [ ] API: Alembic configurado y primera migración con la tabla `owners`, su política de seguridad por fila y los roles de base de datos.
- [ ] API: dependencia que valida el token de Supabase, abre la transacción y fija `app.owner_id`.
- [ ] API: `GET /api/me`, que crea la fila del propietario en la primera llamada.
- [ ] Web: Next.js con TypeScript y Tailwind, tema de colores y tipografía de `docs/diseno.md`.
- [ ] Web: shadcn/ui inicializado, con sus variables de tema asignadas a los colores de Arrendi y los componentes base de acceso (`Button`, `Input`, `Label`, `Card`) ajustados a las medidas del diseño.
- [ ] Web: tema claro y oscuro con `next-themes`, siguiendo al sistema por defecto, con las dos paletas de `docs/diseno.md`.
- [ ] Web: acceso con Google mediante Supabase Auth.
- [ ] Web: registro, inicio de sesión, recuperación de contraseña y cierre de sesión con correo y contraseña.
- [ ] Web: redirección de `/api` hacia la API y cliente con tipos generados (`pnpm gen:api`).
- [ ] Web: PWA instalable, con manifiesto, service worker y pantalla sin conexión.
- [ ] Prueba de aislamiento, contra un PostgreSQL local: con dos propietarios, ninguno ve la fila del otro.
- [ ] Despliegue de los dos proyectos en Vercel.

**Criterios de aceptación**

- Entro con Google en el despliegue de Vercel y veo mi nombre traído de `GET /api/me`.
- Me registro con correo y contraseña, confirmo el correo, inicio sesión y veo mi nombre.
- Si entro con Google usando el mismo correo con el que me registré, llego a la misma cuenta.
- Puedo instalar la aplicación en el celular y entrar con Google desde la aplicación instalada.
- `pnpm dev` levanta la web y la API con un solo comando.
- La aplicación se ve bien en tema claro y en tema oscuro, y recuerda mi elección.
- `pnpm lint`, `pnpm test` y `pnpm build` pasan.

---

## Etapa 2. Inmuebles y contratos

Objetivo: cargar la casa, sus unidades, los arrendatarios y los contratos.

- [ ] Migración: `properties`, `units`, `tenants`, `leases`, con políticas y restricciones.
- [ ] API: rutas de inmuebles, unidades y contratos de `docs/api.md`, incluida `POST /api/onboarding`.
- [ ] API: subida y consulta del documento del contrato, con validación de tipo y tamaño.
- [ ] Web: alta guiada en tres pasos.
- [ ] Web: pantalla de inmuebles y unidades, con estado vacío.
- [ ] Web: pantalla de contrato, y crear, editar y terminar contrato.
- [ ] Web: barra de navegación inferior.
- [ ] Pruebas: una unidad no admite dos contratos activos; aislamiento en todas las rutas nuevas.

**Criterios de aceptación**

- Completo el alta con la casa y sus 3 unidades, y creo los 3 contratos.
- Subo un contrato en PDF desde el celular y lo vuelvo a abrir.
- Otro propietario no puede abrir ese documento.

---

## Etapa 3. Cuentas de cobro

Objetivo: generar cuentas con consecutivo y PDF, a mano, sin correo todavía.

- [ ] Migración: `bills` y `bill_items`, con sus índices únicos.
- [ ] API: servicio que genera la cuenta mensual de un contrato, con consecutivo transaccional.
- [ ] API: generación del PDF con ReportLab y guardado en el almacenamiento.
- [ ] API: rutas de cuentas de `docs/api.md`, salvo enviar y recordar.
- [ ] API: anulación.
- [ ] Web: listado de cuentas con filtros.
- [ ] Web: detalle de cuenta con vista del documento y descarga del PDF.
- [ ] Web: crear cuenta manual.
- [ ] Pruebas: consecutivo sin saltos con generación concurrente; una cuenta mensual por contrato y periodo; no se anula una cuenta con pagos.

**Criterios de aceptación**

- Genero la cuenta del mes de cada contrato y los consecutivos son seguidos.
- El PDF muestra mis datos, los del arrendatario, el concepto, el total, el vencimiento y los datos de pago.
- Anulo una cuenta y genero otra del mismo mes con consecutivo nuevo.

---

## Etapa 4. Correo y tarea diaria

Objetivo: que las cuentas y los recordatorios salgan solos.

- [ ] Migración: `notifications`, con su índice único.
- [ ] API: envío de correo detrás de una interfaz, con el proveedor elegido y un doble para pruebas.
- [ ] API: plantillas de cuenta, dos recordatorios y recibo, en HTML y texto.
- [ ] API: enviar, reenviar y recordatorio manual.
- [ ] API: desvío de todos los correos al buzón de pruebas fuera de producción.
- [ ] API: tarea diaria con sus tres pasos, por lotes, y la ruta `/api/cron/daily` protegida.
- [ ] API: aviso de rebotes del proveedor.
- [ ] Cron Job en `apps/api/vercel.json`.
- [ ] Web: actividad en el detalle de cuenta; botones de reenviar y recordar.
- [ ] Web: configuración de día de envío, recordatorios, copia y selector de tema (claro, oscuro, sistema).
- [ ] Pruebas: la tarea ejecutada dos veces el mismo día no duplica cuentas ni correos; se recupera de un día perdido; las fechas se calculan en hora de Colombia.

**Criterios de aceptación**

- La tarea genera y envía las cuentas del mes, y el correo llega con el PDF.
- Una cuenta sin pagar recibe su recordatorio al día siguiente del vencimiento, una sola vez.
- En local y en vista previa, ningún correo llega a un arrendatario real.

---

## Etapa 5. Pagos e inicio

Objetivo: cerrar el ciclo de cobro.

- [ ] Migración: `payments`.
- [ ] API: registrar y eliminar pagos, con recálculo de estado.
- [ ] API: comprobante del pago.
- [ ] API: correo de recibo.
- [ ] API: `GET /api/summary`.
- [ ] Web: pantalla de registrar pago.
- [ ] Web: pantalla de inicio.
- [ ] Web: estado de cada unidad en inmuebles.
- [ ] Playwright en `apps/e2e/` y el script `pnpm e2e`.
- [ ] Prueba de extremo a extremo: alta, generación de cuenta, pago parcial y pago del saldo.
- [ ] Pruebas: transiciones de estado de `docs/reglas-de-negocio.md`, una por una.

**Criterios de aceptación**

- Registro un abono y la cuenta queda parcial; registro el resto y queda pagada.
- El inicio muestra recaudado, pendiente y unidades en mora, y coincide con el listado.
- Registro un pago desde el inicio en dos toques.

---

## Etapa 6. Piloto

Objetivo: usarlo con los 3 arrendatarios reales durante al menos un ciclo de cobro.

- [ ] Dominio propio para la aplicación y para el correo, con SPF, DKIM y DMARC.
- [ ] Política de tratamiento de datos y autorización en el registro.
- [ ] Datos reales cargados en producción.
- [ ] Sentry activo en web y API.
- [ ] Copia de seguridad de la base de datos verificada con una restauración de prueba.
- [ ] Revisión de accesibilidad: teclado, contraste en ambos temas y lector de pantalla en las pantallas principales.
- [ ] Lista de ajustes surgidos del uso real, priorizada.

**Criterios de aceptación**

- Un ciclo mensual completo sin intervención manual fuera de registrar los pagos.
- Los tres arrendatarios recibieron su cuenta en la bandeja de entrada, no en spam.

---

## Después del MVP

Ver la hoja de ruta en `docs/producto.md`. La primera función es suscripción y límites por plan, necesaria antes de abrir el registro al público.
