# Costos de la infraestructura

Cuánto cuesta cada mes la infraestructura de Arrendi con los servicios que usa hoy, y cuánto costaría al cobrar por el producto y al crecer. Sirve para decidir el paso a los planes pagos (pendiente en `docs/decisiones.md`: el uso comercial en Vercel y los precios de los planes).

Hecho el 21 de octubre de 2026. Las cifras son de sitios de terceros con fechas entre julio y septiembre de 2026, que no coinciden en todos los detalles. Antes de cambiar de plan, confírmalas en <https://vercel.com/pricing>, <https://supabase.com/pricing> y <https://resend.com/pricing>. Los valores están en dólares.

Fuentes: <https://makerkit.dev/blog/saas/vercel-cost>, <https://deploycloud-shopify.devcloudsoftware.com/blog/vercel-pricing>, <https://dev.to/nayankyada/vercel-pricing-2026-what-you-actually-pay-for-a-real-nextjs-project-33md>, <https://www.jetadmin.io/blog/supabase-pricing-2026-guide-to-plans-limits-and-real-world-costs/>, <https://schematichq.com/blog/supabase-pricing>, <https://makerkit.dev/blog/saas/supabase-pricing>, <https://www.usecarly.com/blog/resend-pricing/>, <https://automationatlas.io/answers/resend-free-tier-explained-2026/> y <https://wpmailsmtp.com/resend-review/>.

## Servicios y plan actual

| Servicio | Para qué | Plan | Costo hoy |
| --- | --- | --- | --- |
| Vercel | `arrendi-web`, `arrendi-api` y el Cron Job de la tarea diaria | Hobby | $0 |
| Supabase | `arrendi-dev` y `arrendi-prod`: base, acceso y archivos | Free (2 proyectos activos, justo los que hay) | $0 |
| Resend | Correos de la API y SMTP de Supabase Auth | Free: 3.000 correos al mes y 100 al día | $0 |
| Route 53 | DNS de `jpgstudio.net` | Zona alojada | ~$0,50 al mes, que ya se pagaba antes de Arrendi |
| Google Cloud (OAuth) | Entrar con Google | Gratis | $0 |
| GitHub Actions | Tarea diaria de vista previa (`preview-cron.yml`) | Gratis | $0 |

## Escenarios

| Escenario | Vercel | Supabase | Resend | Total al mes |
| --- | --- | --- | --- | --- |
| Piloto: el fundador, 3 unidades | $0 | $0 | $0 | ~$0 |
| Cobro por el producto | $20 | $25 a $35 | $0 | ~$45 a $55 |
| Más propietarios (más de 100 correos al día) | $20 | $25 a $35 | $20 | ~$65 a $75 |

### Piloto

Unas decenas de correos al mes y pocos MB de base y archivos. Todo cabe en los planes gratuitos con mucho margen.

### Cobro por el producto

- **Vercel Pro, $20 al mes por usuario**, no por proyecto: un usuario cubre `arrendi-web` y `arrendi-api`. El plan Hobby no admite uso comercial. Pro incluye $20 de uso, que con este tráfico no se agotan.
- **Supabase Pro, $25 al mes por organización**, con el cómputo de un proyecto (Micro) incluido. Si `arrendi-dev` queda en la misma organización suma unos $10 al mes. Falta verificar si puede quedar en una organización gratuita aparte. Pro también trae la protección contra contraseñas filtradas, aceptada como pendiente en `docs/decisiones.md`.
- **Resend** sigue en el plan gratuito.

### Más propietarios

Resend Pro cuesta $20 al mes por 50.000 correos. El límite que llega primero es el de **100 correos al día**, no el de 3.000 al mes:

- Cada destinatario cuenta: una cuenta al arrendatario con 3 correos en copia son 4 envíos.
- La tarea diaria envía juntas las cuentas que vencen el mismo día.
- Unos 25 contratos con copias y el mismo día de corte ya llenan el cupo.

## Otros costos

- **Dominio propio de Arrendi:** entre $15 y $40 al año, según la extensión (`.com` o `.co`).

## Qué vigilar

- **Pausa de Supabase Free:** pausa los proyectos con una semana sin actividad. La tarea diaria mantiene activo `arrendi-prod` y el workflow de GitHub mantiene activo `arrendi-dev`.
- **Gastos inesperados:** Supabase Pro trae un tope de gasto activo por defecto. En Vercel Pro conviene configurar una alerta de gasto.
