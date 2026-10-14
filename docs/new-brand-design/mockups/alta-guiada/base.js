/* Shared base of the five onboarding mocks: icons, brand, theme, sample data, the draft
   (same shape as POST /api/onboarding), fields, validation and the hash router. */

/* ---------- Icons: Lucide, stroke only ---------- */
const ICON_PATHS = {
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  plus: '<path d="M5 12h14M12 5v14"/>',
  minus: '<path d="M5 12h14"/>',
  'arrow-left': '<path d="m12 19-7-7 7-7M19 12H5"/>',
  'arrow-right': '<path d="M5 12h14m-7-7 7 7-7 7"/>',
  'chevron-down': '<path d="m6 9 6 6 6-6"/>',
  'chevron-right': '<path d="m9 18 6-6-6-6"/>',
  house: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  building: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/>',
  apartment: '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4"/>',
  store: '<path d="M3 9 5 3h14l2 6"/><path d="M3 9h18v1a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0Z"/><path d="M5 12.5V21h14v-8.5M10 21v-5h4v5"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M16 13H8M16 17H8M10 9H8"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2m-7.07-14.07 1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  pencil: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>',
  key: '<path d="m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4M21 2l-9.6 9.6"/><circle cx="7.5" cy="15.5" r="5.5"/>',
  banknote: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  send: '<path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/><path d="m21.854 2.147-10.94 10.939"/>',
  enter: '<path d="M20 4v7a4 4 0 0 1-4 4H4"/><path d="m9 10-5 5 5 5"/>',
  'map-pin': '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
  door: '<path d="M11 20H2M11 4.562v16.157a1 1 0 0 0 1.242.97L19 20V5.562a2 2 0 0 0-1.515-1.94l-4-1A2 2 0 0 0 11 4.561zM11 4H8a2 2 0 0 0-2 2v14M14 12h.01M22 20h-3"/>',
  sparkle: '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>',
  receipt: '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8M12 17.5v-11"/>',
  eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
  list: '<path d="M3 12h.01M3 18h.01M3 6h.01M8 12h13M8 18h13M8 6h13"/>',
};
const icon = (name, size = 20, extra = '') =>
  `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${ICON_PATHS[name] || ''}</svg>`;

/* ---------- Brand: the isotype of docs/new-brand-design/isotype.svg ---------- */
const ISOTYPE_HOUSE = 'M138 121.5V72.7208L82.0586 30.463L27 72.6612V121.5C27 128.956 20.9558 135 13.5 135C6.04416 135 0 128.956 0 121.5V66.0001C0 61.8004 1.95478 57.84 5.28809 55.2853L73.7881 2.78527L74.2451 2.44933C79.0215 -0.904838 85.4453 -0.815934 90.1367 2.72765L159.637 55.2276C163.014 57.779 165 61.7673 165 66.0001V121.5C165 128.956 158.956 135 151.5 135C144.044 135 138 128.956 138 121.5Z';
const ISOTYPE_WINDOWS = [[55.5, 76], [84.5, 76], [55.5, 105], [84.5, 105]];
function isotype(width = 26) {
  const wins = ISOTYPE_WINDOWS.map(([x, y]) => `<rect class="win" x="${x}" y="${y}" width="25" height="25" rx="5.5"/>`).join('');
  return `<svg width="${width}" height="${Math.round(width * 135 / 165)}" viewBox="0 0 165 135" aria-hidden="true"><path class="house" d="${ISOTYPE_HOUSE}"/>${wins}</svg>`;
}
const brand = (width = 26) => `<span class="brand">${isotype(width)}Arrendi</span>`;

/* ---------- Theme: ?theme=dark|light, otherwise the system; the floating switch toggles it ---------- */
const params = new URLSearchParams(location.search);
const EMBED = params.has('embed');
(function initTheme() {
  const forced = params.get('theme');
  const system = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  document.documentElement.dataset.theme = forced === 'dark' || forced === 'light' ? forced : system;
  if (EMBED) document.documentElement.classList.add('embedded');
})();
function themeButton() {
  const dark = document.documentElement.dataset.theme === 'dark';
  return `<button class="mock-theme" data-act="theme" aria-label="${dark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}">${icon(dark ? 'sun' : 'moon')}</button>`;
}
document.addEventListener('click', (event) => {
  if (!event.target.closest('[data-act="theme"]')) return;
  const root = document.documentElement;
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  render();
});

/* ---------- Toast ---------- */
function toast(text) {
  let el = document.getElementById('toast');
  if (!el) { el = document.createElement('div'); el.id = 'toast'; el.setAttribute('role', 'status'); document.body.append(el); }
  el.textContent = text;
  el.classList.add('on');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove('on'), 2600);
}

/* ---------- Format: money as $1.450.000, dates as 5 oct 2026 ---------- */
const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const pesos = (n) => '$' + String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
const digits = (n) => (n ? String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.') : '');
const fullDate = (d) => (d ? `${+d.slice(8)} ${MONTHS[+d.slice(5, 7) - 1].slice(0, 3)} ${d.slice(0, 4)}` : '');
const monthYear = (d) => `${MONTHS[+d.slice(5, 7) - 1]} ${d.slice(0, 4)}`;
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const TODAY = '2026-10-14';

/* ---------- Labels (apps/web/lib/labels.ts) ---------- */
const PROPERTY_TYPES = [
  { value: 'house', label: 'Casa', icon: 'house' },
  { value: 'building', label: 'Edificio', icon: 'building' },
  { value: 'apartment', label: 'Apartamento', icon: 'apartment' },
  { value: 'shop', label: 'Local', icon: 'store' },
];
const UNIT_USES = [
  { value: 'residential', label: 'Vivienda' },
  { value: 'commercial', label: 'Comercial' },
];
const typeLabel = (v) => PROPERTY_TYPES.find((t) => t.value === v)?.label ?? '';
const useLabel = (v) => UNIT_USES.find((t) => t.value === v)?.label ?? '';
const DUE_DAYS = Array.from({ length: 28 }, (_, i) => ({ value: String(i + 1), label: `${i + 1} del mes` }));

/* ---------- Sample data and the draft ---------- */
const OWNER = { first: 'Carolina' };
const DEMO = {
  property: { name: 'Casa La Soledad', address: 'Cra 24 # 39-18, La Soledad', city: 'Bogotá', type: 'house' },
  units: [
    { name: 'Apto 101', use: 'residential' },
    { name: 'Apto 201', use: 'residential' },
    { name: 'Local 1', use: 'commercial' },
  ],
  lease: { unit: 0, tenant_name: 'Marta Ríos', tenant_email: 'marta.rios@correo.co', rent: 1450000, due_day: '5', start_date: '2026-11-01', end_date: '2027-10-31', file: 'Contrato Apto 101.pdf' },
};
const emptyDraft = () => ({
  property: { name: '', address: '', city: '', type: '' },
  units: [{ name: '', use: 'residential' }],
  lease: { unit: 0, tenant_name: '', tenant_email: '', rent: null, due_day: '', start_date: '', end_date: '', file: null },
  withLease: true,
});
let draft = emptyDraft();
/** Fills the draft with the sample up to `level` (1 property, 2 units, 3 lease), so a screen opened directly has something to show. */
function prefill(level) {
  if (level >= 1 && !draft.property.name) draft.property = { ...DEMO.property };
  if (level >= 2 && !draft.units[0].name) draft.units = DEMO.units.map((u) => ({ ...u }));
  if (level >= 3 && !draft.lease.tenant_name) draft.lease = { ...DEMO.lease };
}
/** A unit name that follows the pattern of the others: Apto 1, Apto 2… or Local 1. */
function suggestUnitName(use, units) {
  const prefix = use === 'commercial' ? 'Local' : 'Apto';
  const taken = units.filter((u) => u.name.startsWith(prefix)).length;
  return `${prefix} ${taken + 1}`;
}

/* ---------- Get and set by path: "lease.tenant_name", "units.2.name" ---------- */
function getPath(path) { return path.split('.').reduce((o, k) => (o == null ? o : o[k]), draft); }
function setPath(path, value) {
  const keys = path.split('.');
  const last = keys.pop();
  keys.reduce((o, k) => o[k], draft)[last] = value;
}

/* ---------- Validation: the messages of the current forms ---------- */
let errors = {};
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
function validate(part) {
  const e = {};
  if (part === 'property' || part === 'all') {
    if (!draft.property.name.trim()) e['property.name'] = 'Escribe un nombre para el inmueble.';
    if (!draft.property.type) e['property.type'] = 'Elige el tipo de inmueble.';
  }
  if (part === 'units' || part === 'all') {
    draft.units.forEach((u, i) => { if (!u.name.trim()) e[`units.${i}.name`] = 'Escribe el nombre de la unidad.'; });
  }
  if ((part === 'lease' || part === 'all') && draft.withLease) Object.assign(e, validateLease());
  errors = e;
  return Object.keys(e).length === 0;
}
function validateLease(only) {
  const l = draft.lease;
  const e = {};
  const want = (k) => !only || only.includes(k);
  if (want('tenant_name') && !l.tenant_name.trim()) e['lease.tenant_name'] = 'Escribe el nombre del arrendatario.';
  if (want('tenant_email') && !EMAIL_RE.test(l.tenant_email.trim())) e['lease.tenant_email'] = 'Escribe un correo válido.';
  if (want('rent') && !(l.rent > 0)) e['lease.rent'] = 'Escribe el canon mensual.';
  if (want('due_day') && !l.due_day) e['lease.due_day'] = 'Elige el día de pago.';
  if (want('start_date') && !l.start_date) e['lease.start_date'] = 'Elige la fecha de inicio.';
  if (want('end_date') && l.end_date && l.start_date && l.end_date <= l.start_date) e['lease.end_date'] = 'Debe ser posterior a la fecha de inicio.';
  return e;
}
const errorText = (path) => (errors[path] ? `<p class="error" id="${path}-error">${icon('alert', 16)}${esc(errors[path])}</p>` : '');
const invalid = (path) => (errors[path] ? `aria-invalid="true" aria-describedby="${path}-error"` : '');

/* ---------- Fields: same anatomy as FormField, MoneyField, SelectField, ToggleGroup ---------- */
function field({ path, label, type = 'text', placeholder = '', help = '', optional = false, autocomplete = 'off', inputmode = '', big = false }) {
  const id = path.replaceAll('.', '-');
  return `<div class="field">
    <label for="${id}">${esc(label)}${optional ? ' <span class="opt">(opcional)</span>' : ''}</label>
    <input class="input${big ? ' input-big' : ''}" id="${id}" type="${type}" data-bind="${path}" value="${esc(getPath(path) ?? '')}" placeholder="${esc(placeholder)}" autocomplete="${autocomplete}" ${inputmode ? `inputmode="${inputmode}"` : ''} ${invalid(path)}>
    ${help && !errors[path] ? `<p class="help">${help}</p>` : ''}${errorText(path)}
  </div>`;
}
function moneyField({ path, label, help = '', big = false }) {
  const id = path.replaceAll('.', '-');
  return `<div class="field">
    <label for="${id}">${esc(label)}</label>
    <div class="money"><input class="input${big ? ' input-big' : ''}" id="${id}" inputmode="numeric" data-money="${path}" value="${digits(getPath(path))}" placeholder="0" autocomplete="off" ${invalid(path)}></div>
    ${help && !errors[path] ? `<p class="help">${help}</p>` : ''}${errorText(path)}
  </div>`;
}
function selectField({ path, label, options, placeholder = 'Elige una opción', optional = false }) {
  const id = path.replaceAll('.', '-');
  const value = String(getPath(path) ?? '');
  return `<div class="field">
    <label for="${id}">${esc(label)}${optional ? ' <span class="opt">(opcional)</span>' : ''}</label>
    <select class="select" id="${id}" data-bind="${path}" ${invalid(path)}>
      <option value="" ${value ? '' : 'selected'} disabled>${esc(placeholder)}</option>
      ${options.map((o) => `<option value="${o.value}" ${String(o.value) === value ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}
    </select>${errorText(path)}
  </div>`;
}
function toggleGroup({ path, label, options, cols = 2, withIcons = false }) {
  const value = getPath(path);
  return `<fieldset class="field">
    <legend class="legend" style="margin-bottom:6px">${esc(label)}</legend>
    <div class="toggle-group cols-${cols}" role="radiogroup" ${errors[path] ? `aria-describedby="${path}-error"` : ''}>
      ${options.map((o) => `<button type="button" class="toggle" role="radio" aria-checked="${o.value === value}" data-pick="${path}" data-value="${o.value}">${withIcons && o.icon ? icon(o.icon, 18) : ''}${esc(o.label)}</button>`).join('')}
    </div>${errorText(path)}
  </fieldset>`;
}
function documentPicker(path = 'lease.file') {
  const file = getPath(path);
  return file
    ? `<div class="dropzone has-file"><span class="ic">${icon('file')}</span><span style="flex:1;min-width:0"><b style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(file)}</b><small>PDF · 1,2 MB</small></span><button type="button" class="icon-btn" data-act="clear-file" aria-label="Quitar el documento">${icon('x')}</button></div>`
    : `<button type="button" class="dropzone" data-act="pick-file"><span class="ic">${icon('upload')}</span><span><b>Subir el contrato firmado</b><small>Opcional · PDF, JPG o PNG, hasta 10 MB</small></span></button>`;
}

/* ---------- Binding: inputs write to the draft; proposals hook `onDraftChange` to refresh live parts ---------- */
let onDraftChange = () => {};
document.addEventListener('input', (event) => {
  const el = event.target;
  if (el.dataset.bind) {
    setPath(el.dataset.bind, el.value);
    clearError(el.dataset.bind, el);
    onDraftChange(el.dataset.bind);
  } else if (el.dataset.money) {
    const n = Number(el.value.replace(/\D/g, '').slice(0, 12)) || null;
    setPath(el.dataset.money, n);
    const caretFromEnd = el.value.length - el.selectionStart;
    el.value = digits(n);
    el.setSelectionRange(el.value.length - caretFromEnd, el.value.length - caretFromEnd);
    clearError(el.dataset.money, el);
    onDraftChange(el.dataset.money);
  }
});
document.addEventListener('change', (event) => {
  const el = event.target;
  if (el.tagName === 'SELECT' && el.dataset.bind) { setPath(el.dataset.bind, el.value); clearError(el.dataset.bind, el); onDraftChange(el.dataset.bind); }
});
document.addEventListener('click', (event) => {
  const pick = event.target.closest('[data-pick]');
  if (pick) {
    const path = pick.dataset.pick;
    const raw = pick.dataset.value;
    setPath(path, /^\d+$/.test(raw) && path.endsWith('unit') ? Number(raw) : raw);
    pick.parentElement.querySelectorAll('[data-pick]').forEach((b) => b.setAttribute('aria-checked', String(b === pick)));
    clearError(path, pick);
    onDraftChange(path);
    return;
  }
  const act = event.target.closest('[data-act]')?.dataset.act;
  if (act === 'pick-file') { draft.lease.file = 'Contrato firmado.pdf'; onDraftChange('lease.file'); render(); }
  if (act === 'clear-file') { draft.lease.file = null; onDraftChange('lease.file'); render(); }
});
/** Removes a field's error as soon as it is corrected, without re-rendering the screen. */
function clearError(path, el) {
  if (!errors[path]) return;
  delete errors[path];
  const box = el.closest('.field, fieldset');
  box?.querySelector('.error')?.remove();
  box?.querySelectorAll('[aria-invalid]').forEach((i) => i.removeAttribute('aria-invalid'));
}
/** After a failed "Continuar": render with the errors and put the focus on the first one. */
function focusFirstError() {
  const first = document.querySelector('[aria-invalid="true"], .error');
  const target = first?.matches('input, select') ? first : first?.closest('.field, fieldset')?.querySelector('input, select, button');
  target?.focus();
  target?.scrollIntoView({ block: 'center', behavior: 'smooth' });
}

/* ---------- Router: one screen per hash; `screens` and `render` come from each proposal ---------- */
let current = null;
let direction = 'forward';
function go(screen) { direction = 'forward'; location.hash = screen; }
function back(screen) { direction = 'back'; location.hash = screen; }
function startRouter(order, levels) {
  // Only a screen opened directly (a link, the gallery) gets the sample; moving through
  // the flow keeps exactly what was typed.
  let first = true;
  const route = () => {
    const name = location.hash.slice(1) || order[0];
    const index = order.indexOf(name);
    current = index === -1 ? order[0] : name;
    if (first) prefill(levels[current] ?? 0);
    first = false;
    errors = {};
    render();
    window.scrollTo(0, 0);
    const heading = document.querySelector('h1');
    if (heading && index > 0) { heading.setAttribute('tabindex', '-1'); heading.focus({ preventScroll: true }); }
    direction = 'forward';
  };
  addEventListener('hashchange', route);
  route();
}
const enterClass = () => (direction === 'back' ? 'enter-back' : 'enter');
