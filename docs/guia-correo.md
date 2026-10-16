# Guía: correo con dominio propio

Paso a paso de lo que se hizo para que Arrendi envíe correo desde un dominio propio, con Resend, y cómo se comprobó. Es el paso 7 de `docs/etapa-7.md` (puntos 2 a 4) y sirve para repetirlo cuando Arrendi tenga su dominio definitivo. Los pasos en los paneles los hace el fundador en sus cuentas.

Hecho el 15 de octubre de 2026. Menús y datos de Resend y Supabase consultados en su documentación ese día. Los nombres de los menús cambian con frecuencia: si no ves el que dice la guía, busca la sección por su nombre.

Fuentes: <https://resend.com/docs/dashboard/domains/introduction>, <https://resend.com/docs/add-a-domain>, <https://resend.com/docs/dashboard/domains/dmarc>, <https://resend.com/docs/dashboard/domains/custom-return-path>, <https://resend.com/docs/send-with-supabase-smtp> y <https://supabase.com/docs/guides/auth/auth-smtp>.

## Qué correos salen y por dónde

Arrendi manda dos tipos de correo, por caminos distintos:

| Correo | Lo envía | Remitente |
| --- | --- | --- |
| Cuentas de cobro, recordatorios y recibos | La API, por la API HTTP de Resend (`apps/api/app/email/sender.py`) | `<nombre del propietario> vía Arrendi <cuentas@arrendi.jpgstudio.net>`, con respuesta al correo del propietario (`reply_to`) |
| Confirmar registro y recuperar contraseña | Supabase Auth, por el SMTP de Resend | `Arrendi <no-reply@arrendi.jpgstudio.net>` |

## Datos

| Dato | Valor |
| --- | --- |
| Dominio | `jpgstudio.net`, provisional, del fundador (`docs/decisiones.md`) |
| DNS | AWS Route 53, zona `jpgstudio.net` |
| Producción | `https://arrendi.jpgstudio.net`, con `arrendi-prod` (`izgnyyhlfotpfqieifit`) |
| Vista previa de `develop` | `https://arrendi-dev.jpgstudio.net`, con `arrendi-dev` (`qbbljaontjbudtqkesah`) |
| Dominio verificado en Resend | `arrendi.jpgstudio.net`, región `us-east-1` |

**Por qué el correo sale de `arrendi.jpgstudio.net` y no de `jpgstudio.net`:** Resend recomienda un subdominio para que la reputación del correo quede aparte. Así, lo que pase con los envíos de Arrendi no afecta a `jpgstudio.net`. Se usa el mismo subdominio de la aplicación porque no choca con su CNAME a Vercel: Resend pone sus registros en nombres de más abajo (`resend._domainkey.arrendi`, `send.arrendi`, `rsend.arrendi`) y no en `arrendi` mismo.

## Paso 1: dominio en Resend

1. Resend → **Domains** → **Add domain** → `arrendi.jpgstudio.net`.
2. Región **us-east-1**, la más cercana a Colombia.
3. Ruta de retorno: la que propone Resend.
4. Seguimiento de aperturas y de clics **apagado**. En correos de cobro no aporta y aumenta el riesgo de caer en spam.

Resend muestra los registros que hay que crear en la pestaña **Records**.

## Paso 2: registros en Route 53

Route 53 → Hosted zones → `jpgstudio.net` → **Create record**, uno por cada registro de Resend. Los valores se **copian y pegan** tal como los muestra Resend; no se escriben a mano.

Quedaron así:

| Nombre en Route 53 | Tipo | Valor | Para qué |
| --- | --- | --- | --- |
| `resend._domainkey.arrendi` | TXT | `"p=MIGf…"`, la clave pública de Resend | DKIM: firma los correos a nombre de `arrendi.jpgstudio.net` |
| `send.arrendi` | CNAME | `send.forge.rmta.net` | Ruta de retorno y SPF |
| `rsend.arrendi` | CNAME | `rsend.forge.rmta.net` | Ruta de retorno y SPF; es la que aparece en el `Return-Path` de los correos |
| `_dmarc.arrendi` | TXT | `"v=DMARC1; p=none; rua=mailto:jpguarin@gmail.com"` | DMARC (paso 4) |

Además, en el dominio raíz quedó `_dmarc.jpgstudio.net` con `"v=DMARC1; p=none;"`. Para `arrendi.jpgstudio.net` manda su propio registro.

Detalles de Route 53:

- **Nombre:** solo el prefijo (`resend._domainkey.arrendi`). Route 53 agrega `.jpgstudio.net` solo.
- **TXT:** el valor va entre comillas dobles. Si es muy largo, se parte en dos cadenas entre comillas en la misma línea: `"parte1" "parte2"`.
- **MX**, si Resend lo pidiera: prioridad y servidor en el mismo campo, por ejemplo `10 servidor.ejemplo.com`.

**Sobre `rmta.net`:** la documentación de Resend dice que usa registros TXT y "MX o CNAME", pero no nombra `rmta.net`. Se comprobó con un envío real que es infraestructura de Resend: el SPF que publica `rsend.forge.rmta.net` autorizó la IP de Amazon SES desde la que salió el correo, y Gmail dio `spf=pass`.

## Paso 3: comprobar el DNS y verificar

Antes de pulsar **Verify** en Resend, comprobar que los registros se ven desde afuera, en el DNS público y en los servidores de Route 53:

```
d=arrendi.jpgstudio.net
for s in 8.8.8.8 ns-37.awsdns-04.com; do
  dig +short resend._domainkey.$d TXT @$s
  dig +short send.$d CNAME @$s
  dig +short rsend.$d CNAME @$s
  dig +short _dmarc.$d TXT @$s
done
```

Después, en Resend, **Verify**. Suele tardar unos 15 minutos y puede llegar a 72 horas. Si a las 72 horas no ha verificado, Resend tiene un botón para reiniciar la verificación.

## Paso 4: DMARC

Va después de verificar el dominio. Se empieza con `p=none`, que solo observa y no cambia la entrega:

```
_dmarc.arrendi   TXT   "v=DMARC1; p=none; rua=mailto:jpguarin@gmail.com"
```

- Un correo pasa DMARC si pasa SPF o DKIM alineado con el dominio del remitente.
- **Reportes:** como `gmail.com` es otro dominio y no autoriza recibir reportes ajenos, varios proveedores no los mandarán. No afecta la entrega; para el piloto basta con mirar las cabeceras.
- **Pendiente:** cuando todos los envíos muestren `dmarc=pass`, subir a `p=quarantine` y, más adelante, a `p=reject`.

## Paso 5: claves de API

En Resend → **API Keys**, las claves para Arrendi llevan permiso **Sending access** y van limitadas al dominio `arrendi.jpgstudio.net`. Así no pueden leer ni borrar nada de la cuenta, y se puede revocar una sin tumbar las demás.

Lo recomendado es una por uso: `arrendi-prod-api`, `arrendi-prod-supabase` y las equivalentes de `arrendi-dev`. **Por ahora los dos ambientes comparten la misma configuración** (decisión del fundador del 15 de octubre de 2026). Es seguro, porque la vista previa mantiene el desvío al buzón de pruebas, pero revocar una clave afecta a ambos.

Las claves no entran al repositorio ni al chat: van a un gestor de contraseñas y a las variables de Vercel.

## Paso 6: SMTP de Supabase

En cada proyecto (`arrendi-prod` y `arrendi-dev`): Supabase → **Authentication → Emails → SMTP Settings** → *Enable custom SMTP*:

| Campo | Valor |
| --- | --- |
| Sender email | `no-reply@arrendi.jpgstudio.net` |
| Sender name | `Arrendi` |
| Host | `smtp.resend.com` |
| Port | `465` |
| Username | `resend` |
| Password | La clave de API de Resend |

- Al activarlo, Supabase limita los correos de acceso a 30 por hora. Para el piloto sobra; se cambia en Authentication → Rate Limits.
- En la misma sección de Authentication, revisar:
  - **URL Configuration:** *Site URL* y *Redirect URLs* del dominio de ese ambiente (`https://arrendi.jpgstudio.net/**` en `arrendi-prod`; `https://arrendi-dev.jpgstudio.net/**` y `http://localhost:3000/**` en `arrendi-dev`).
  - **Emails → Templates:** las plantillas de confirmar registro y recuperar contraseña de `docs/guia-supabase-vercel.md`, paso 5. Con las plantillas por defecto, en inglés, el enlace solo funciona en el mismo navegador donde se pidió.

## Paso 7: aviso de rebotes

En Resend → **Webhooks** → *Add endpoint*:

- URL: `https://arrendi.jpgstudio.net/api/webhooks/email`. La web redirige `/api` a la API.
- Evento: solo `email.bounced`. La API ignora los demás (`apps/api/app/routes/system.py`).
- El *Signing secret* (`whsec_…`) va a `EMAIL_WEBHOOK_SECRET`.

Resend manda a cada webhook los avisos de toda la cuenta. Con un solo secreto compartido, el webhook apunta a Producción; en `develop` los rebotes no quedan marcados.

## Paso 8: variables de `arrendi-api` en Vercel

| Variable | Valor |
| --- | --- |
| `EMAIL_API_KEY` | La clave de Resend |
| `EMAIL_SENDER` | `cuentas@arrendi.jpgstudio.net` |
| `EMAIL_WEBHOOK_SECRET` | El `whsec_…` del paso 7 |
| `EMAIL_TEST_INBOX` | `jpguarin@gmail.com`, en Production y en Preview. En Production se quita solo al final del paso 7.5 de `docs/etapa-7.md` |

Las variables nuevas solo entran con un despliegue nuevo: **Redeploy** después de cambiarlas.

## Paso 9: pruebas

### Envío directo con la API de Resend

Con la clave en una variable de la terminal, para que no quede en el historial:

```
curl -s https://api.resend.com/emails \
  -H "Authorization: Bearer $RESEND_KEY" -H "Content-Type: application/json" \
  -d '{"from":"Arrendi <cuentas@arrendi.jpgstudio.net>","to":["jpguarin@gmail.com"],"subject":"Prueba de dominio","text":"Hola"}'
```

### Leer las cabeceras

- **Gmail:** abrir el correo → ⋮ → **Mostrar original**.
- **Outlook web:** abrir el correo → ⋯ → **Ver** → **Ver detalles del mensaje**.

| Qué buscar | Debe decir |
| --- | --- |
| `Authentication-Results` | `spf=pass`, `dkim=pass header.i=@arrendi.jpgstudio.net`, `dmarc=pass … header.from=arrendi.jpgstudio.net` |
| En Outlook, además | `compauth=pass`. Es la comprobación propia de Microsoft; si falla, el correo suele ir a no deseado |
| `Return-Path` | `…@rsend.arrendi.jpgstudio.net` |
| Correos de acceso: `X-Pm-Metadata-Project-Ref` | El `ref` del proyecto de Supabase que lo envió. Así se sabe si salió de `arrendi-prod` o de `arrendi-dev` |
| Cuentas de cobro: `Reply-To` | El correo del propietario |
| Cuentas de cobro desviadas: asunto | `[Para <destinatario real>] …` |

### Resultados del 15 de octubre de 2026

| Prueba | Resultado |
| --- | --- |
| Envío directo a Gmail | ✅ SPF, DKIM y DMARC `pass` |
| Recuperar contraseña desde `develop` | ✅ SPF, DKIM y DMARC `pass`, desde `no-reply@arrendi.jpgstudio.net`. ⚠️ Salió de `arrendi-dev` con la plantilla por defecto y un enlace a `localhost` (ver pendientes) |
| Cuenta de cobro desde `develop`, desviada a Gmail | ✅ SPF, DKIM y DMARC `pass`, `Reply-To` del propietario, prefijo `[Para …]` |
| Cuenta de cobro desde local, desviada a Outlook | ✅ Bandeja de entrada, todas las comprobaciones `pass` |

## Probar en local

Fuera de Producción, la API no envía si falta `EMAIL_TEST_INBOX`: responde `EMAIL_TEST_INBOX is not set outside production` (`apps/api/app/email/sender.py`). Es a propósito: una variable olvidada nunca termina en un correo a un arrendatario real.

- **Para que llegue a otro buzón**, por ejemplo uno de Outlook, se cambia el valor de `EMAIL_TEST_INBOX` en `apps/api/.env`; no se quita.
- **Para ver el correo tal como sale en Producción**, al destinatario real y sin prefijo, se usa el paso 7.5 de `docs/etapa-7.md`, en Producción, con un arrendatario falso cuyo correo es otro buzón tuyo.
- No se recomienda poner `ENVIRONMENT=production` en local para saltarse el desvío: la base local es `arrendi-dev`, y cualquier cuenta enviada le llegaría al correo que tenga ese contrato.

## Pendientes

- [ ] Recuperar contraseña desde `https://arrendi.jpgstudio.net`: debe salir con `X-Pm-Metadata-Project-Ref: izgnyyhlfotpfqieifit`, la plantilla en español y el enlace al dominio de Producción.
- [ ] `arrendi-dev`: restaurar las plantillas de correo y agregar `https://arrendi-dev.jpgstudio.net/**` a las direcciones de retorno.
- [ ] Webhook de rebotes de Producción y su `EMAIL_WEBHOOK_SECRET`.
- [ ] Paso 7.5 de `docs/etapa-7.md`: arrendatario falso y, si llega bien, quitar `EMAIL_TEST_INBOX` de Production.
- [ ] Subir DMARC a `p=quarantine` cuando todos los envíos pasen.
- [ ] Claves separadas por ambiente, si se quiere poder revocar una sin afectar la otra.

## Al cambiar al dominio definitivo de Arrendi

1. Repetir los pasos 1 a 4 con el dominio nuevo, en un subdominio.
2. Crear claves nuevas limitadas a ese dominio y cambiar `EMAIL_SENDER`, el SMTP de los dos proyectos de Supabase y la URL del webhook.
3. Repetir las pruebas del paso 9 en Gmail y en Outlook antes de escribirle a un arrendatario.
4. Dejar el dominio viejo verificado unas semanas, por si quedan correos en camino, y después borrarlo de Resend y sus registros de Route 53.
5. Actualizar `docs/decisiones.md` y esta guía.
