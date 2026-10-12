# Etapa 7: guía paso a paso

Guía de trabajo de la etapa 7 (piloto). Las tareas y los criterios de aceptación oficiales están en `docs/plan.md`; este documento detalla el orden, qué hace cada paso y cómo se comprueba. Se marca cada paso al terminarlo.

**Estado:** plan propuesto el 11 de octubre de 2026. No se ha empezado: falta la aprobación del fundador y el nombre del dominio.

**Objetivo:** usar Arrendi con los 3 arrendatarios reales durante al menos un ciclo de cobro.

**Criterios de aceptación**

- Un ciclo mensual completo sin intervención manual fuera de registrar los pagos.
- Los tres arrendatarios recibieron su cuenta en la bandeja de entrada, no en spam.

Esta etapa es distinta a las anteriores: la mitad es configuración en tus cuentas (Supabase, Vercel, Resend, el dominio), que haces tú con mi guía. El código es poco: política y autorización, Sentry, la copia de seguridad y lo que salga de la revisión de accesibilidad.

## Decisiones de esta etapa

Tomadas el 11 de octubre de 2026:

1. **Vercel: Hobby durante el piloto, Pro antes de vender.** Vercel limita Hobby a uso personal no comercial (consultado hoy en sus lineamientos de uso). El piloto es solo tuyo y no le cobra a nadie por la aplicación. Antes de abrir el registro a otros propietarios hay que pasar a Pro. Puedes confirmar tu caso con el soporte de Vercel.
2. **Supabase gratuito, con copia propia.** El plan gratuito no trae copias automáticas, y ningún plan respalda los archivos de Storage. Un script del repositorio exporta la base y descarga los archivos a una carpeta tuya.
3. **Dominio propio, que ya tienes.** Para la aplicación y, en un subdominio, para el correo. Falta que me digas cuál es.
4. **`arrendi-prod` empieza limpio.** Haces el alta de nuevo con los datos reales; los consecutivos empiezan en 1.

## Lo que no se resuelve con código

Son tuyas y están pendientes en `docs/decisiones.md`. Ninguna bloquea el arranque, pero conviene cerrarlas antes de mandar la primera cuenta real:

- **Contador:** confirmar que basta la cuenta de cobro y no hace falta factura electrónica.
- **Marca:** verificar el registro de "Arrendi" ante la SIC.
- **Política de tratamiento de datos:** yo redacto una base según la Ley 1581 de 2012; el texto final debe revisarlo alguien que sepa de protección de datos. No soy abogado.

## Límites asumidos

Dime si alguno no te sirve antes de empezar.

- **Autorización de datos:** se pide una vez a cada propietario, al registrarse con correo o al entrar por primera vez con Google, y se guarda en `owners.data_consent_at`, que ya existe. Sin aceptarla no se puede usar la aplicación. La política se publica en `/privacy`, abierta a todos.
- **Datos de los arrendatarios:** tú, como propietario, eres el responsable de tener su autorización; Arrendi los trata por encargo tuyo. La política lo dice así. Los correos al arrendatario no llevan enlace para darse de baja: son cobros, no publicidad.
- **Correos de acceso (confirmar registro, recuperar contraseña):** hoy los envía Supabase con su servicio de pruebas, que tiene un límite muy bajo y no es para producción. En `arrendi-prod` se configuran para salir por Resend con tu dominio.
- **Sentry:** plan gratuito, solo en Producción y en vista previa, sin datos personales en los reportes (ni correos, ni nombres, ni el contenido de las peticiones).
- **Copia de seguridad a mano:** el script lo corres tú; no queda programado. Recomiendo correrlo después de cada generación mensual y antes de cualquier migración.
- **Accesibilidad:** además de la revisión manual, se agrega una comprobación automática a Playwright en las pantallas principales, en ambos temas.
- **`arrendi-dev` queda para local y vistas previas.** Al pasar Producción a `arrendi-prod`, la tarea diaria deja de correr contra `arrendi-dev`.
- **Dependencias nuevas:** `@sentry/nextjs` en la web y `sentry-sdk` en la API (monitoreo de errores), y `@axe-core/playwright` en `apps/e2e` (accesibilidad automática).

## Pasos

Los pasos 2 a 5 son código y no tocan producción. Los pasos 6 a 9 cambian tus cuentas y los haces tú, uno por uno, con mi guía.

### [ ] Paso 1. Documentos al día

- `docs/decisiones.md`: las cuatro decisiones y lo verificado sobre Vercel y Supabase. `docs/arquitectura.md`: entornos, variables nuevas y la guía de paso a producción. `docs/producto.md` y `docs/api.md`: la autorización. `CLAUDE.md`: esta guía en la tabla.

### [ ] Paso 2. Política y autorización

La prueba va primero.

- API: `GET /api/me` dice si el propietario ya autorizó (`data_consent`), y `POST /api/me/consent` guarda la fecha. Las demás rutas responden 403 `consent_required` mientras falte.
- Web: página pública `/privacy` con la política; casilla obligatoria en el registro con correo; pantalla de autorización al entrar por primera vez con Google, antes del alta. Enlace a la política en Ajustes.
- `docs/politica-de-datos.md`: el texto base, marcado como borrador hasta que lo revisen.
- **Se comprueba:** sin autorización no se llega a ninguna pantalla con datos; aceptar una vez basta; aislamiento. La prueba de Playwright pasa por la autorización.

### [ ] Paso 3. Sentry

- Consulto antes la documentación vigente de Sentry para Next.js 16 con Turbopack y para FastAPI.
- API: `sentry-sdk` en `app/main.py`, activo solo si existe `SENTRY_DSN`. Los errores que hoy solo quedan en el registro (un correo que falla, un contrato que la tarea no pudo procesar) llegan a Sentry.
- Web: `@sentry/nextjs`, activo solo si existe `NEXT_PUBLIC_SENTRY_DSN`. Las respuestas de `/api` siguen sin pasar por el service worker.
- **Se comprueba:** en local, sin las variables, nada cambia. En vista previa, un error provocado a propósito aparece en Sentry sin datos personales.

### [ ] Paso 4. Copia de seguridad

- `apps/api/scripts/backup.py` (fuera del paquete de Vercel): exporta la base con `pg_dump` y descarga los archivos del contenedor a una carpeta con fecha, fuera del repositorio. `app/storage.py` gana un método para listar archivos.
- `apps/api/scripts/restore_check.py`: restaura esa copia en una base local nueva y compara cuántos propietarios, contratos, cuentas y pagos hay, y que cada archivo referenciado exista en la copia.
- `docs/arquitectura.md`: cómo correr la copia, cómo restaurar de verdad, y qué no incluye (las contraseñas de los roles).
- **Se comprueba:** copia de `arrendi-dev` restaurada en local, con los mismos conteos y todos los archivos.

### [ ] Paso 5. Accesibilidad

- `@axe-core/playwright` sobre inicio, cuentas, detalle de cuenta, registrar pago, inmuebles, contrato y ajustes, en tema claro y oscuro.
- Revisión manual: recorrer con teclado el ciclo de la prueba de extremo a extremo (orden del foco, foco visible, diálogos que atrapan y devuelven el foco) y con VoiceOver las pantallas principales.
- Se corrige lo que salga. `docs/diseno.md` anota lo revisado y lo que quede pendiente.
- **Se comprueba:** `pnpm e2e` pasa con las comprobaciones de accesibilidad; la lista de hallazgos queda cerrada o anotada.

### [ ] Paso 6. `arrendi-prod` y Producción en Vercel (tú)

Sigue la guía de despliegue de `docs/arquitectura.md`:

1. Crear el proyecto `arrendi-prod` en Supabase, en la misma región que la API.
2. Acceso: Google, correo con confirmación, las dos plantillas de correo y las direcciones de retorno.
3. Contenedor privado `arrendi`, con el límite de 10 MB y los tres tipos.
4. `alembic upgrade head` con la conexión de `arrendi-prod`, y activar el acceso de `arrendi_api` y `arrendi_tasks` con contraseñas nuevas.
5. Variables de Producción en `arrendi-api` y `arrendi-web`, con los valores de `arrendi-prod`. Las de vista previa siguen con `arrendi-dev`.
6. Redesplegar y comprobar `/api/health` y el registro de un usuario.

- **Se comprueba:** entras a Producción con una cuenta nueva y la aplicación te lleva al alta; en `arrendi-dev` no aparece nada nuevo.

### [ ] Paso 7. Dominio y correo real (tú)

1. Dominio de la aplicación en `arrendi-web`, con sus registros DNS, y las direcciones de retorno de Supabase y de Google actualizadas.
2. Subdominio de correo en Resend, con SPF, DKIM y DMARC. Consulto la documentación vigente de Resend para los registros exactos.
3. Correos de acceso de `arrendi-prod` por Resend.
4. `EMAIL_SENDER` con una dirección del dominio; webhook de rebotes de Producción con su secreto; publicar la pantalla de consentimiento de Google para usuarios externos.
5. **Prueba con un arrendatario falso:** un contrato cuyo correo es otro buzón tuyo. Solo cuando esa cuenta llegue a la bandeja de entrada, y no a spam, se quita `EMAIL_TEST_INBOX` de Producción.

- **Se comprueba:** la cuenta de prueba llega a un buzón de Gmail y a uno de Outlook, en la bandeja de entrada, con SPF, DKIM y DMARC aprobados en las cabeceras.

### [ ] Paso 8. Datos reales

- El alta con la casa y las 3 unidades; los 3 contratos con sus documentos; tus datos y los de pago; el día de envío.
- Decide con qué contratos empiezas con envío automático: recomiendo apagarlo el primer mes y enviar tú cada cuenta después de revisarla.
- Primera copia de seguridad de `arrendi-prod`, restaurada en local con el script del paso 4.
- **Se comprueba:** la copia restaurada tiene tus 3 contratos y sus documentos.

### [ ] Paso 9. El ciclo del piloto

- Un mes completo: generación el día de envío, recordatorios si hacen falta, pagos y recibos.
- Confirmar con cada arrendatario que la cuenta llegó a su bandeja de entrada.
- `docs/piloto.md`: lo que salga del uso real, priorizado.

### [ ] Paso 10. Cierre

- `pnpm lint`, `pnpm test`, `pnpm build` y `pnpm e2e`; casillas de la etapa 7 en `docs/plan.md`.

## Riesgos

- **El cambio a `arrendi-prod` cierra tu sesión** y tu cuenta actual no existe allá: te registras de nuevo. La aplicación instalada en el celular pedirá entrar otra vez.
- **Entrega del correo:** un dominio recién configurado puede caer en spam los primeros envíos. Por eso la prueba con buzones tuyos va antes de escribirle a un arrendatario, y el primer mes conviene enviar a mano.
- **Quitar `EMAIL_TEST_INBOX` es el paso sin vuelta atrás:** desde ahí, la tarea diaria le escribe a personas reales. Va de último y solo en Producción.
- **Plan gratuito de Supabase:** un proyecto sin actividad se puede pausar. La tarea diaria lo mantiene activo, pero conviene revisar el panel la primera semana.
- **Sentry con Turbopack y Serwist** no lo he probado en este proyecto; si su integración choca con el service worker, la web queda con el reporte de errores del navegador solamente y lo anoto.
- **La copia depende de `pg_dump` local**, que debe ser de una versión igual o más nueva que la del servidor de Supabase.
