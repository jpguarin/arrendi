# Decisiones

## Tomadas

| Decisión | Detalle |
| --- | --- |
| Nombre | Arrendi |
| Cliente inicial | Propietario particular con 2 a 10 unidades |
| Canal | Solo correo en el MVP |
| Plataforma | PWA |
| Backend | FastAPI (Python) |
| Frontend | Next.js (TypeScript), con Tailwind CSS y shadcn/ui |
| Datos, acceso y archivos | Supabase |
| Formas de entrar | Google, y correo con contraseña |
| Despliegue | Todo en Vercel, sin Docker |
| Repositorio | Monorepo con Turborepo y pnpm: `apps/api/`, `apps/web/` y `apps/e2e/` |
| Tema | Claro y oscuro; sigue al sistema por defecto |
| Desarrollo | El fundador, con Claude Code |
| Idioma del código | Inglés: archivos, carpetas, identificadores, tablas, columnas, rutas de la API y de la web, campos JSON y variables de entorno. En español quedan los textos de la interfaz, los correos, el PDF, el mensaje de error que ve el propietario, los documentos y los commits |
| Base de las pruebas | PostgreSQL local con Homebrew; nunca un proyecto de Supabase |
| Componentes | shadcn/ui sobre Radix, inicializado dentro de `apps/web` (sin `packages/ui`) |
| Rutas en Next.js | Solo las que no tienen reglas de negocio: service worker, regreso de Google y confirmación de correo |
| Playwright | Se agrega en la etapa 5, no en la 1 |
| Next.js | Versión 16.4, con Turbopack. Sin `cacheComponents` ni `partialPrefetching`, que la plantilla trae activos: todas las pantallas son privadas y por propietario, y esas opciones obligan a aislar cada lectura de la sesión |
| Suscripción y límites por plan | Fuera del MVP |
| Documento del contrato | Se puede subir el contrato firmado y el inventario de la unidad, un archivo de cada uno por contrato. Se suben al crear el contrato o desde su detalle; se reemplazan, no se borran |
| Subida de archivos | Directa al almacenamiento con un enlace firmado que entrega la API, porque Vercel limita el cuerpo de una petición a 4,5 MB. La API valida el tipo real al confirmar |
| Clave secreta de Supabase | Solo en el módulo de almacenamiento de la API, además de la tarea diaria, para crear enlaces firmados |
| Cliente HTTP de la API | `httpx2`, el mismo paquete que ya usaban las pruebas; pasa a `requirements.txt` para hablar con Storage. No se usa el SDK de Supabase en la API |
| Datos en la web | TanStack Query con `openapi-react-query`, sobre el cliente con tipos generados. Guarda en memoria lo que respondió la API: al volver a una pantalla se muestra al instante y se refresca por detrás. Solo en memoria, nunca en el dispositivo, y se vacía al cambiar de sesión. Se descartó un almacén global (Zustand, Redux): lo que se guarda son datos del servidor, no estado de la interfaz |
| Barra de navegación | Muestra solo las pantallas que ya existen. Desde la etapa 3 están las cuatro: Inicio, Cuentas, Inmuebles y Ajustes |
| Cuenta mensual a mano | `POST /api/leases/{id}/bills` genera la del mes en curso, con el mismo servicio que usa la tarea diaria |
| Ajustes mínimo en la etapa 3 | Nombre, documento y datos de pago se adelantan a la etapa 3, porque el PDF los necesita. El resto de la configuración sigue en la etapa 4 |
| Cuenta con vencimiento pasado | Nace `overdue`, sin esperar a la tarea diaria |
| Varios conceptos por cuenta | Una cuenta es la suma de sus conceptos. El contrato guarda conceptos fijos (tabla `lease_items`) que salen en todas sus cuentas mensuales, después del canon; la cuenta manual lleva los que se le escriban. Hasta 10 en cada caso. Un solo vencimiento por cuenta. El canon sigue siendo un campo aparte del contrato. En el registro inicial no se piden: se agregan al editar el contrato |
| Recargo por mora | Por contrato: un interruptor, un porcentaje del canon (hasta dos decimales) y días de gracia. Se cobra una sola vez, como concepto de la cuenta del mes siguiente, para no editar la cuenta atrasada. Se descartó emitir una cuenta aparte por el recargo y subir el saldo de la misma cuenta. Cuenta lo pagado en la fecha límite según la fecha de cada pago. El propietario lo puede perdonar cuenta por cuenta. Una cuenta emitida después de su propia fecha límite no lleva recargo. Una cuenta que trae un recargo no se envía sola, porque un pago que llegó a tiempo y aún no se registró lo volvería un error difícil de deshacer. Si el contrato termina no hay cuenta siguiente: se cobra con una cuenta manual. La aplicación cobra lo configurado; los topes legales de la mora en vivienda son responsabilidad del propietario |
| Firma en la cuenta | Una sola por propietario, en Ajustes: se sube (PNG o JPG, hasta 2 MB) o se dibuja en pantalla. La API separa la tinta del papel, así una foto de la firma sobre una hoja queda con fondo transparente, y la guarda como PNG recortado a sus trazos, de 600×200 px como máximo, para que cada PDF pese poco. Las firmas guardadas viven en una carpeta distinta de la de subida (`signatures` y `signature`), para que ninguna pueda confirmarse como subida nueva y borrarse. Pillow queda fijado en `requirements.txt` porque la API ya lo usa directamente. Va a la izquierda, al final de la última hoja: firma, nombre, documento. Cada cuenta guarda la firma con la que se emitió. Es una imagen pegada, no una firma electrónica certificada, y el PDF no dice otra cosa. Se descartó una firma por contrato y poner ciudad y fecha |
| Cuántos conceptos caben en una hoja | Con el bloque de firma, el canon y siete conceptos más caben en una hoja con datos de pago de dos líneas. Con más, la cuenta sigue en otra |
| Encabezado de la cuenta | "Cuenta de cobro" a la izquierda y el número a la derecha; debajo, la fecha de emisión y, en la manual, la unidad. Luego dos renglones con etiqueta, "Cobra" (propietario) y "Debe" (arrendatario), a todo el ancho: el nombre ocupa las líneas que necesite y el documento va debajo. Se eligió entre cinco propuestas porque un nombre largo se montaba sobre el título. Igual en el PDF y en la vista previa |
| Concepto en el correo | El primer concepto de la cuenta, tal como se escribió, y cuántos más hay: "Canon de arrendamiento y 2 conceptos más". El PDF adjunto los trae todos. En medio de una frase pierde la mayúscula inicial, salvo que la primera palabra vaya en mayúsculas, como "IVA" |
| Dónde dice la cuenta de qué unidad es | La mensual lo dice bajo el canon, su primer concepto: "Octubre 2026 · Apto 2". La manual no tiene canon, así que la unidad va en el encabezado, después de la fecha, y ningún concepto la repite. Igual en el PDF y en la vista previa. Los PDF ya guardados no cambian |
| PDF de más de una página | Si los conceptos y los datos de pago no caben, la cuenta sigue en otra hoja, que arriba dice el número de la cuenta, el propietario y la página. Los datos de pago también se reparten entre hojas. La más llena posible con descripciones cortas (canon, 10 conceptos y depósito) cabe en una |
| Depósito en la primera cuenta | El depósito del contrato se cobra una sola vez, como concepto aparte en la primera cuenta mensual, y el total es la suma. Un interruptor en el contrato lo apaga si el arrendatario ya lo pagó por fuera. Los contratos que existían antes quedaron apagados: su depósito se da por cobrado. En el inicio cuenta como cualquier cobro, dentro del total de la cuenta |
| Datos de pago por contrato y por cuenta | Los de Ajustes son el valor por defecto. Un contrato puede llevar los suyos, al crearlo o al editarlo, y una cuenta manual los suyos. La cuenta guarda los que resultan al emitir (cuenta, contrato, Ajustes) y no cambian después. Las cuentas emitidas antes de esto quedaron con los de Ajustes de ese día |
| Proveedor de correo | Resend, por su API HTTP con `httpx2`, sin SDK |
| Dominio de la aplicación y del correo | Provisional: `jpgstudio.net`, del fundador, con el DNS en Route 53. La aplicación en `arrendi.jpgstudio.net` y el correo desde el mismo subdominio, verificado en Resend: así la reputación del correo no toca `jpgstudio.net`. Remitente `cuentas@arrendi.jpgstudio.net`; las respuestas van al propietario por `reply_to`. Se cambia cuando Arrendi tenga dominio propio |
| Correos en copia por contrato | Hasta 3 por contrato, en copia visible (CC), y reciben todo lo que recibe el arrendatario: cuenta, reenvío, recordatorios y recibo. Decidido el 16 de octubre de 2026, durante el piloto. Resend avisa un rebote por envío y no por destinatario: si rebota una copia, la notificación queda `bounced` aunque el arrendatario lo haya recibido |
| Correos hasta la etapa 7 | Todos van al buzón de pruebas (`EMAIL_TEST_INBOX`), también en Producción, con el destinatario real en el asunto. Con el dominio propio, la variable se quita de Producción |
| Cuenta generada a mano | No se envía sola: queda con el botón "Enviar". Solo la tarea diaria envía sola |
| Recordatorios | Solo de cuentas que ya se enviaron, y uno por cuenta en cada ejecución de la tarea |
| Playwright | Corre todo en local: la web, la API contra la base `arrendi_e2e` de PostgreSQL y dos servidores falsos (acceso y almacenamiento). Nunca contra Supabase |
| Deuda de meses anteriores | El inicio la lista en "Por cobrar" y la suma aparte; las cifras del mes no la incluyen |
| Marca y diseño (etapa 6) | Marca de `docs/new-brand-design`. De tres propuestas de interfaz se eligió la B, "Libro": riel de secciones, tablas y panel de detalle. `docs/diseno.md` se reescribió con ese sistema |
| Datos del propietario en el alta | Antes del primer inmueble se piden número de documento, datos de pago y firma, y se confirma el día de envío. Solo para propietarios nuevos; quien ya tiene inmuebles no cambia. Una pregunta por pantalla (propuesta 2 de `docs/new-brand-design/mockups/tus-datos/`), cada respuesta se guarda al continuar y la API rechaza el alta sin ellos |
| Datos de pago armados | En el alta se eligen con toques: Bancolombia, Davivienda, Banco de Bogotá, BBVA, Banco Popular, Colpatria, Nequi, Daviplata u otro, el tipo de cuenta y el número. La web escribe el texto, con el titular; la API sigue guardando un solo texto, que también se puede escribir a mano |
| Día de envío sugerido | El 1 de cada mes |
| Vista previa de la cuenta | En papel, igual en los dos temas, como el PDF: en el detalle de la cuenta y en el alta. Sin la franja ni el pie del PDF |
| Panel redimensionable | Desde tablet, arrastrando su borde o con el teclado, entre 360 y 720 px y dejando 360 px a la lista. El ancho se guarda en el navegador, igual para Cuentas e Inmuebles. Componente propio, sin dependencias |
| Panel de detalle | Se conservan las rutas: el `layout` de Cuentas y el de Inmuebles dibujan la lista y, al lado, la ruta abierta. Desde el resumen, una cuenta se abre en Cuentas. Se descartó un panel sobre cualquier pantalla con un parámetro en la dirección, que cambiaba los enlaces |
| Fuente del PDF | Sigue Helvetica, aunque la marca pide Inter: no viaja ningún archivo de fuente con la API |
| Gráficas | Hechas con Tailwind, sin librería: una barra de composición y barras por mes no la justifican |
| Mes de un pago | El de su cuenta, no el de la fecha en que se recibió |
| Eliminar un pago | Borrado real, con su comprobante. Junto con `lease_items`, cuya lista se reemplaza al editar el contrato, son las únicas tablas donde la API borra |
| PDF | ReportLab con Helvetica, que ya trae; no se empaqueta Figtree |
| Flujo de Git | `main` es producción y `develop` es pruebas. Features y bugs salen de `develop` y vuelven por PR; `develop` se promueve a `main` por PR; el hotfix sale de `main` y se lleva de vuelta a `develop`. Todo se fusiona con commit de fusión, nunca *squash*, para que las dos ramas no diverjan. Detalle en `docs/flujo-de-trabajo-git.md` |
| Identificador de ambiente | Franja de color arriba de todas las pantallas ("ENV · develop" o "ENV · local"), emoji en el título de la pestaña y favicon con un punto: ámbar en pruebas, azul en local, nada en producción. El ambiente sale de `VERCEL_ENV` al compilar, no de una variable a mano, para que producción nunca pueda mostrarlo |
| País del inmueble | Se guarda el código ISO 3166-1 alfa-2, no un texto libre, para que un mismo país no quede escrito de varias formas. Obligatorio, Colombia por defecto; los inmuebles anteriores quedaron en Colombia. La web tiene los nombres en español escritos en `lib/countries.ts`, no pedidos a `Intl`, y su tipo la obliga a tener los mismos códigos que la API. El país solo se muestra fuera del formulario cuando no es Colombia |
| Migraciones entre ambientes | Manuales, con checklist en el PR de promoción: a `arrendi-dev` al fusionar en `develop` y a `arrendi-prod` antes de fusionar en `main`. Siempre compatibles hacia atrás, porque el código viejo corre un rato contra el esquema nuevo |

## Provisionales

Se tomaron para no bloquear el desarrollo. Impleméntalas así, de forma que cambiarlas después sea fácil, y no las extiendas por tu cuenta.

| Tema | Decisión provisional | Alternativa |
| --- | --- | --- |
| Pago mayor al saldo | Se rechaza | Guardarlo como saldo a favor del mes siguiente |
| Prorrateo | No hay; la primera cuenta es completa | Cobrar proporcional el mes incompleto |
| Contrato que llega a su fecha de fin | Sigue activo hasta que el propietario lo termine | Renovación o terminación automática |
| Cuentas anuladas en el listado | Ocultas, visibles con un filtro | Siempre visibles |
| Tamaño máximo de archivos | 10 MB | Otro valor, según el límite de Vercel |
| Día de pago | Entre 1 y 28 | Admitir 29 a 31 con ajuste al último día |
| Envío de cuentas | Día fijo del mes por propietario; aprobación previa por contrato | Opción "N días antes del vencimiento" |
| PDF de cuenta anulada | Se reemplaza por una versión marcada "ANULADA" | Conservar ambas versiones |

## Pendientes

Hay que resolverlas antes de la etapa indicada.

| Decisión | Antes de |
| --- | --- |
| Plan de Vercel: confirmar si el gratuito admite uso comercial | Etapa 7 |
| Verificar dominio y registro de marca de Arrendi ante la SIC | Etapa 7 |
| Confirmar con un contador si basta la cuenta de cobro o hará falta factura electrónica | Etapa 7 |
| Texto de la política de tratamiento de datos | Etapa 7 |
| Precios y límites de los planes | Después del MVP |

## Por verificar en documentación vigente

No son decisiones de producto, sino datos técnicos que cambian y que este repositorio no fija:

- Requisitos de Google para publicar la pantalla de consentimiento a usuarios externos.
- Si la protección de despliegues de Vercel bloquea la redirección de la web hacia la API de vista previa.

### Verificado el 11 de octubre de 2026

- Vercel llama al Cron Job con `Authorization: Bearer <CRON_SECRET>`, no reintenta si falla y puede, rara vez, llamar dos veces o ninguna: la tarea debe ser idempotente y recuperarse sola.
- Resend, comprobado de extremo a extremo contra `arrendi-dev`: un correo a `bounced@resend.dev` (su dirección para simular rebotes) genera el aviso `email.bounced`, la API desplegada verifica su firma y la notificación queda `bounced`. El panel de Resend no tiene un botón para enviar un evento de prueba.
- El Cron Job de Vercel, lanzado a mano desde el panel, responde 200 en `arrendi-api`.
- Resend: `POST https://api.resend.com/emails` con adjuntos en Base64 y cabecera `Idempotency-Key` (vale 24 horas). Sus avisos llegan firmados con las cabeceras `svix-id`, `svix-timestamp` y `svix-signature`.
- Supabase Storage acepta desde el navegador el `PUT` de subida con `Content-Type` (CORS: cualquier origen), comprobado con la petición previa contra `arrendi-dev`.
- Supabase Storage, probado contra `arrendi-dev`: el enlace firmado de subida acepta un `PUT` con el archivo como cuerpo y sin claves; no sirve para sobrescribir un archivo que ya existe; el contenedor rechaza tipos no permitidos y más de 10 MB; un archivo de 7 MB sube bien; sin enlace no hay acceso.
- Una función de Vercel admite un cuerpo de petición de hasta 4,5 MB (error 413 si lo supera) y, con Fluid compute, hasta 300 s de duración en el plan Hobby.

### Verificado el 10 de octubre de 2026

El detalle está en `docs/arquitectura.md` y `docs/modelo-de-datos.md`.

- Supabase valida sus tokens con claves asimétricas publicadas por JWKS.
- Supabase vincula sola la identidad de Google a una cuenta con el mismo correo verificado.
- El usuario `postgres` de Supabase puede crear un rol con `bypassrls` (`arrendi_tasks`).
- El agrupador de Supabase se usa en modo transacción, sin sentencias preparadas.
- Supabase retira las claves `anon` y `service_role` a finales de 2026.
- Vercel detecta la instancia `app` de FastAPI en `app/main.py` y enlaza las vistas previas con "Related Projects".
- Turborepo usa la clave `tasks` y filtra las variables de entorno por defecto.
- Serwist con Turbopack sirve el service worker desde una ruta de Next.
- En Next.js 16, `middleware.ts` se llama `proxy.ts`.
