/* What the 404 mocks add to ../alta-guiada/base.js: the address that was not found
   (?path=), the session state (#in or #out), a guess from Spanish words, and the actions. */

Object.assign(ICON_PATHS, {
  dashboard: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  'log-in': '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5"/><path d="M15 12H3"/>',
  unlink: '<path d="m18.84 12.25 1.72-1.71h-.02a5.004 5.004 0 0 0-.12-7.07 5.006 5.006 0 0 0-6.95 0l-1.72 1.71"/><path d="m5.17 11.75-1.71 1.71a5.004 5.004 0 0 0 .12 7.07 5.006 5.006 0 0 0 6.95 0l1.71-1.71"/><path d="M8 2v3M2 8h3M16 19v3M19 16h3"/>',
  'shield-check': '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
});

const PATH = params.get('path') || '/cuentas';
const signedIn = () => location.hash.slice(1) !== 'out';
const TODAY_404 = '20 oct 2026';

// The four sections of the app (docs/diseno.md, "Secciones").
const SECTIONS = [
  { key: 'home', label: 'Resumen', href: '/', icon: 'dashboard', hint: 'Cuánto falta por cobrar este mes' },
  { key: 'bills', label: 'Cuentas', href: '/bills', icon: 'receipt', hint: 'Todas tus cuentas de cobro, por mes' },
  { key: 'properties', label: 'Inmuebles', href: '/properties', icon: 'building', hint: 'Unidades, contratos y arrendatarios' },
  { key: 'settings', label: 'Ajustes', href: '/settings', icon: 'settings', hint: 'Tus datos, firma y día de envío' },
];

// The interface is in Spanish and the routes in English, so someone who types the address
// by hand writes "/cuentas". The first word of the path is enough to suggest the section.
const SPANISH_WORDS = {
  resumen: 'home', inicio: 'home', cuentas: 'bills', cuenta: 'bills', cobros: 'bills', pagos: 'bills',
  inmuebles: 'properties', inmueble: 'properties', unidades: 'properties', contratos: 'properties',
  ajustes: 'settings', configuracion: 'settings', perfil: 'settings',
};
function guess(path = PATH) {
  const word = (path.split('/').filter(Boolean)[0] || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  return SECTIONS.find((s) => s.key === SPANISH_WORDS[word]);
}

const pathChip = (label = 'Dirección') =>
  `<p class="path"><span>${label}</span><code>${esc(PATH)}</code></p>`;

function actions({ primaryLabel = 'Ir al resumen' } = {}) {
  if (!signedIn()) {
    return `<div class="actions">
      <a class="btn btn-primary" href="/login" data-to="Iniciar sesión">${icon('log-in')}Iniciar sesión</a>
      <a class="btn btn-outline" href="/signup" data-to="Crear cuenta">Crear cuenta</a>
    </div>`;
  }
  return `<div class="actions">
    <a class="btn btn-primary" href="/" data-to="Resumen">${icon('dashboard')}${primaryLabel}</a>
    <button class="btn btn-outline" data-act="back">${icon('arrow-left')}Volver</button>
  </div>`;
}

// Links are real anchors (keyboard, middle click); in the mock they only say where they go.
document.addEventListener('click', (event) => {
  const link = event.target.closest('[data-to]');
  if (link) { event.preventDefault(); toast(`En la app, esto lleva a ${link.dataset.to}`); return; }
  if (event.target.closest('[data-act="back"]')) {
    if (EMBED || history.length <= 1) toast('En la app, esto vuelve a la página anterior');
    else history.back();
  }
});
addEventListener('hashchange', () => render());
