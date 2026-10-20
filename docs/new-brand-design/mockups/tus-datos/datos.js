/* What the five "tus datos" mocks add to ../alta-guiada/base.js: the owner's part of the
   draft (same fields as PATCH /api/settings plus the signature), its validation, and the
   pieces every proposal composes: document, payment builder, send day, signature pad and
   the bill on paper that shows where each piece ends up. Load it after base.js. */

/* ---------- More icons (Lucide) ---------- */
Object.assign(ICON_PATHS, {
  'id-card': '<path d="M16 10h2M16 14h2M6.17 15a3 3 0 0 1 5.66 0"/><circle cx="9" cy="11" r="2"/><rect x="2" y="5" width="20" height="14" rx="2"/>',
  landmark: '<path d="M10 18v-7M11.12 2.198a2 2 0 0 1 1.76.006l7.866 3.847c.476.233.31.949-.22.949H3.474c-.53 0-.695-.716-.22-.949zM14 18v-7M18 18v-7M3 22h18M6 18v-7"/>',
  signature: '<path d="m21 17-2.156-1.868A.5.5 0 0 0 18 15.5v.5a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1c0-2.545-3.991-3.97-8.5-4a1 1 0 0 0 0 5c4.153 0 4.745-11.295 5.708-13.5a2.5 2.5 0 1 1 3.31 3.284"/><path d="M3 21h18"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
  eraser: '<path d="m7 21-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6c1 1 1 2.5 0 3.4L13 21M22 21H7M5 11l9 9"/>',
  type: '<path d="M12 4v16M4 7V5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v2M9 20h6"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  'calendar-check': '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18m-12 6 2 2 4-4"/>',
  wallet: '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
  'list-checks': '<path d="m3 17 2 2 4-4M3 7l2 2 4-4M13 6h8M13 12h8M13 18h8"/>',
});

/* ---------- The owner in the draft: what Ajustes keeps, plus how the pieces were made ---------- */
const DOC_TYPES = [{ value: 'cc', label: 'Cédula' }, { value: 'nit', label: 'NIT' }];
const docShort = (t) => (t === 'nit' ? 'NIT' : 'C.C.');
const BANKS = ['Bancolombia', 'Davivienda', 'Banco de Bogotá', 'BBVA', 'Banco Popular', 'Colpatria', 'Nequi', 'Daviplata', 'Otro'];
const WALLETS = ['Nequi', 'Daviplata'];
const ACCOUNT_TYPES = [{ value: 'Ahorros', label: 'Ahorros' }, { value: 'Corriente', label: 'Corriente' }];
const SEND_CHIPS = [1, 5, 10, 15, 25];
const RECOMMENDED_DAY = '1';
// A signature drawn once for the sample, so a screen opened directly has one to show.
const DEMO_SIGNATURE = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 90"><path d="M12 64c18-40 30-52 34-38s-14 44-4 40 22-38 30-34-6 28 2 28 18-30 26-26-4 22 4 22 14-18 22-16 2 14 8 14 16-22 28-24 6 30 20 26 30-20 52-24 38 4 46 2" fill="none" stroke="#14264C" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg>');

draft.owner = {
  // From the sign-up (Google gives it): the owner only confirms it.
  name: 'Carolina Gómez',
  email: 'carolina.gomez@gmail.com',
  document_type: 'cc',
  document_number: '',
  payment: { bank: '', type: 'Ahorros', number: '', other: '' },
  payment_details: '',
  // True once the owner writes the text by hand: the builder stops rewriting it.
  payment_by_hand: false,
  signature: null, // { kind: 'drawn' | 'photo' | 'typed', url }
  send_day: '',
};
const DEMO_OWNER = {
  document_number: '52.814.337',
  payment: { bank: 'Bancolombia', type: 'Ahorros', number: '123-456789-01', other: '' },
  signature: { kind: 'drawn', url: DEMO_SIGNATURE },
  send_day: '1',
};
/** Levels: 0 nothing but the name, 1 document, 2 payment, 3 signature, 4 everything. */
function prefillOwner(level) {
  const o = draft.owner;
  if (level >= 1 && !o.document_number) o.document_number = DEMO_OWNER.document_number;
  if (level >= 2 && !o.payment.bank) { o.payment = { ...DEMO_OWNER.payment }; o.payment_details = composePayment(); }
  if (level >= 3 && !o.signature) o.signature = { ...DEMO_OWNER.signature };
  if (level >= 4 && !o.send_day) o.send_day = DEMO_OWNER.send_day;
}
// The router fills the sample by level; here the level is the owner's.
prefill = prefillOwner;

/* ---------- Payment details: the builder writes the text the bill shows ---------- */
function composePayment() {
  const o = draft.owner;
  const p = o.payment;
  if (!p.bank || !p.number.trim()) return '';
  const bank = p.bank === 'Otro' ? (p.other.trim() || 'Banco') : p.bank;
  const account = WALLETS.includes(p.bank) ? `${bank} al ${p.number.trim()}` : `${bank} · ${p.type} N.º ${p.number.trim()}`;
  const holder = [o.name.trim(), o.document_number.trim() && `${docShort(o.document_type)} ${o.document_number.trim()}`].filter(Boolean).join(', ');
  return holder ? `${account}\nA nombre de ${holder}` : account;
}

/* ---------- Validation: required, with the tone of the current forms ---------- */
function validateOwner(only) {
  const o = draft.owner;
  const e = {};
  const want = (k) => !only || only.includes(k);
  if (want('name') && !o.name.trim()) e['owner.name'] = 'Escribe tu nombre como debe salir en la cuenta.';
  if (want('document_number')) {
    const n = o.document_number.replace(/\D/g, '');
    if (!n) e['owner.document_number'] = o.document_type === 'nit' ? 'Escribe el NIT.' : 'Escribe tu número de cédula.';
    else if (n.length < 5 || n.length > 11) e['owner.document_number'] = 'Revisa el número: parece incompleto.';
  }
  if (want('payment_details')) {
    if (!o.payment_by_hand && o.payment.bank && !o.payment.number.trim()) e['owner.payment.number'] = WALLETS.includes(o.payment.bank) ? 'Escribe el celular de la cuenta.' : 'Escribe el número de la cuenta.';
    else if (!o.payment_details.trim()) e['owner.payment_details'] = 'Cuéntale a tu arrendatario cómo pagarte.';
  }
  if (want('signature') && !o.signature) e['owner.signature'] = 'Firma con el dedo, sube una foto de tu firma o escríbela.';
  if (want('send_day') && !o.send_day) e['owner.send_day'] = 'Elige el día en que salen tus cuentas.';
  return e;
}
const ownerReady = (keys) => Object.keys(validateOwner(keys)).length === 0;

/* ---------- Pieces ---------- */
function documentFields() {
  const nit = draft.owner.document_type === 'nit';
  return `${toggleGroup({ path: 'owner.document_type', label: 'Tipo de documento', options: DOC_TYPES })}
    ${field({ path: 'owner.document_number', label: nit ? 'NIT' : 'Número de cédula', inputmode: 'numeric', placeholder: nit ? '900.123.456-7' : '52.814.337', help: 'Sale en la cuenta de cobro, junto a tu nombre.' })}`;
}
function textareaField({ path, label, help = '', placeholder = '' }) {
  const id = path.replaceAll('.', '-');
  return `<div class="field">
    <label for="${id}">${esc(label)}</label>
    <textarea class="textarea" id="${id}" data-bind="${path}" placeholder="${esc(placeholder)}" ${invalid(path)}>${esc(getPath(path) ?? '')}</textarea>
    ${help && !errors[path] ? `<p class="help">${help}</p>` : ''}${errorText(path)}
  </div>`;
}
/** Pick the bank, the kind of account and its number; the text writes itself and stays editable. */
let payByHandOpen = false;
function paymentBuilder({ compact = false } = {}) {
  const p = draft.owner.payment;
  if (payByHandOpen) {
    return `<div class="stack" style="gap:12px">
      ${textareaField({ path: 'owner.payment_details', label: 'Cómo te pagan', placeholder: 'Transferencia a Bancolombia, ahorros N.º …\nO en efectivo el día 5', help: 'Escríbelo como quieres que lo lean tus arrendatarios.' })}
      <button type="button" class="btn-link" style="align-self:flex-start" data-act="pay-builder">Mejor elegir el banco</button>
    </div>`;
  }
  const wallet = WALLETS.includes(p.bank);
  return `<div class="stack" style="gap:16px">
    <fieldset class="field">
      <legend class="legend" style="margin-bottom:6px">¿Dónde te consignan?</legend>
      <div class="banks" role="radiogroup">${BANKS.map((b) => `<button type="button" class="bank" role="radio" aria-checked="${p.bank === b}" data-pick="owner.payment.bank" data-value="${b}">${b}</button>`).join('')}</div>
      ${errorText('owner.payment.bank')}
    </fieldset>
    ${p.bank === 'Otro' ? field({ path: 'owner.payment.other', label: 'Nombre del banco', placeholder: 'Banco de Occidente' }) : ''}
    ${p.bank ? `<div class="${wallet || compact ? 'stack' : 'pay-row'}" style="gap:12px">
      ${wallet ? '' : `<fieldset class="field"><legend class="legend" style="margin-bottom:6px">Tipo de cuenta</legend><div class="toggle-group cols-2" role="radiogroup">${ACCOUNT_TYPES.map((t) => `<button type="button" class="toggle" role="radio" aria-checked="${p.type === t.value}" data-pick="owner.payment.type" data-value="${t.value}">${t.label}</button>`).join('')}</div></fieldset>`}
      ${field({ path: 'owner.payment.number', label: wallet ? 'Celular' : 'Número de cuenta', inputmode: 'numeric', placeholder: wallet ? '300 123 4567' : '123-456789-01' })}
    </div>` : ''}
    <div class="written" id="pay-written" ${draft.owner.payment_details ? '' : 'hidden'}><span class="lbl">Así lo leerá tu arrendatario</span><p>${esc(draft.owner.payment_details)}</p></div>
    ${errorText('owner.payment_details')}
    <button type="button" class="btn-link" style="align-self:flex-start" data-act="pay-by-hand">Prefiero escribirlo yo (efectivo, otra forma…)</button>
  </div>`;
}
const sendHelp = () => (draft.owner.send_day
  ? `El ${draft.owner.send_day} de cada mes Arrendi genera las cuentas de tus contratos y se las envía por correo a tus arrendatarios.`
  : 'Cada mes, ese día, Arrendi genera las cuentas y las envía solas.');
function sendDayChips() {
  const d = draft.owner.send_day;
  const other = d && !SEND_CHIPS.includes(+d);
  return `<fieldset class="field">
    <legend class="legend" style="margin-bottom:6px">Día de envío</legend>
    <div class="chips" role="radiogroup" ${errors['owner.send_day'] ? 'aria-describedby="owner.send_day-error"' : ''}>
      ${SEND_CHIPS.map((n) => `<button type="button" class="chip" role="radio" aria-checked="${d === String(n)}" data-pick="owner.send_day" data-value="${n}">Día ${n}${String(n) === RECOMMENDED_DAY ? '<span class="tag">Sugerido</span>' : ''}</button>`).join('')}
      <label class="sr-only" for="owner-send-other">Otro día</label>
      <select class="select" id="owner-send-other" style="width:auto;height:44px;border-radius:999px" data-bind="owner.send_day">
        <option value="" ${other ? '' : 'selected'}>Otro día</option>
        ${Array.from({ length: 28 }, (_, i) => i + 1).filter((n) => !SEND_CHIPS.includes(n)).map((n) => `<option value="${n}" ${d === String(n) ? 'selected' : ''}>Día ${n}</option>`).join('')}
      </select>
    </div>
    <p class="help" id="send-help">${sendHelp()}</p>${errorText('owner.send_day')}
  </fieldset>`;
}
function sendDayMonth() {
  const d = draft.owner.send_day;
  return `<fieldset class="field">
    <legend class="legend" style="margin-bottom:6px">Toca el día del mes</legend>
    <div class="month" role="radiogroup">${Array.from({ length: 28 }, (_, i) => i + 1).map((n) => `<button type="button" role="radio" aria-checked="${d === String(n)}" aria-label="Día ${n}${String(n) === RECOMMENDED_DAY ? ', sugerido' : ''}" class="${String(n) === RECOMMENDED_DAY ? 'rec' : ''}" data-pick="owner.send_day" data-value="${n}">${n}</button>`).join('')}</div>
    <p class="help" id="send-help">${sendHelp()}</p>${errorText('owner.send_day')}
  </fieldset>`;
}

/* ---------- Signature: draw it, upload a photo of it, or (one proposal) write it ---------- */
let signMode = 'draw';
function signaturePad({ big = false, typed = false } = {}) {
  const s = draft.owner.signature;
  const modes = [['draw', 'Dibujar'], ['photo', 'Subir foto'], ...(typed ? [['typed', 'Escribir']] : [])];
  if (s && s.kind !== signMode) signMode = s.kind;
  let sheet;
  if (signMode === 'draw') sheet = `<canvas data-sign aria-label="Hoja para firmar con el dedo o el mouse"></canvas><span class="baseline"></span>${s ? '' : '<span class="hint">Firma aquí con el dedo o el mouse</span>'}`;
  else if (signMode === 'photo') sheet = s ? `<img src="${s.url}" alt="Tu firma">` : `<label class="sign-upload">${icon('image')}<b>Elegir una foto de tu firma</b><span>Sobre papel blanco · JPG o PNG, hasta 2 MB</span><input class="sr-only" type="file" accept="image/png,image/jpeg" data-sign-file></label>`;
  else sheet = `<span class="sign-typed">${esc(draft.owner.name || 'Tu nombre')}</span><span class="baseline"></span>`;
  return `<div class="field sign-pad">
    <span class="legend">Tu firma</span>
    <div class="segmented sign-tabs" role="group" aria-label="Cómo quieres firmar">${modes.map(([k, l]) => `<button type="button" aria-pressed="${signMode === k}" data-sign-mode="${k}">${l}</button>`).join('')}</div>
    <div class="sign-sheet${big ? ' big' : ''}" ${errors['owner.signature'] ? 'aria-invalid="true"' : ''}>${sheet}</div>
    <div class="sign-tools">
      <p class="help">${signMode === 'typed' ? 'Usamos tu nombre en letra cursiva, como firma.' : 'Sale al pie de cada cuenta de cobro.'}</p>
      ${signMode === 'typed' && !s ? '<button type="button" class="btn btn-outline btn-sm" data-act="sign-typed">Usar esta firma</button>' : ''}
      ${s ? `<button type="button" class="btn btn-ghost btn-sm" data-act="sign-clear">${icon('eraser', 16)}Borrar</button>` : ''}
    </div>
    ${errorText('owner.signature')}
  </div>`;
}
function setSignature(value) {
  draft.owner.signature = value;
  if (value) { delete errors['owner.signature']; document.querySelector('.sign-sheet')?.removeAttribute('aria-invalid'); document.querySelector('.sign-pad .error')?.remove(); }
  onDraftChange('owner.signature');
}
/** Hooks up the canvas after each render: ink is the bill's, on paper in both themes. */
function mountSignature() {
  const canvas = document.querySelector('canvas[data-sign]');
  if (!canvas) return;
  const ratio = window.devicePixelRatio || 1;
  const box = canvas.getBoundingClientRect();
  canvas.width = box.width * ratio;
  canvas.height = box.height * ratio;
  const ctx = canvas.getContext('2d');
  ctx.scale(ratio, ratio);
  ctx.lineWidth = 2.6; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--ink').trim();
  const s = draft.owner.signature;
  if (s && s.kind === 'drawn') {
    const img = new Image();
    img.onload = () => { const h = box.height - 40; const w = Math.min(box.width - 40, h * (img.width / img.height || 3)); ctx.drawImage(img, 20, 8, w, h); };
    img.src = s.url;
  }
  let drawing = false;
  const at = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  canvas.addEventListener('pointerdown', (e) => {
    drawing = true; canvas.setPointerCapture(e.pointerId);
    canvas.parentElement.querySelector('.hint')?.remove();
    ctx.beginPath(); ctx.moveTo(...at(e));
  });
  canvas.addEventListener('pointermove', (e) => { if (!drawing) return; ctx.lineTo(...at(e)); ctx.stroke(); });
  const end = () => { if (!drawing) return; drawing = false; setSignature({ kind: 'drawn', url: trimmed(canvas) }); refreshSignTools(); };
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', end);
}
/** The ink alone, without the empty sheet around it: on the bill it sits right on the name. */
function trimmed(canvas) {
  const { width, height } = canvas;
  const data = canvas.getContext('2d').getImageData(0, 0, width, height).data;
  let top = height, left = width, right = -1, bottom = -1;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (data[(y * width + x) * 4 + 3] === 0) continue;
      if (x < left) left = x; if (x > right) right = x;
      if (y < top) top = y; if (y > bottom) bottom = y;
    }
  }
  if (right < 0) return canvas.toDataURL('image/png');
  const pad = 6 * (window.devicePixelRatio || 1);
  left = Math.max(0, left - pad); top = Math.max(0, top - pad);
  right = Math.min(width - 1, right + pad); bottom = Math.min(height - 1, bottom + pad);
  const out = document.createElement('canvas');
  out.width = right - left + 1; out.height = bottom - top + 1;
  out.getContext('2d').drawImage(canvas, left, top, out.width, out.height, 0, 0, out.width, out.height);
  return out.toDataURL('image/png');
}
// After the first stroke the "Borrar" button appears, without redrawing the canvas.
function refreshSignTools() {
  const tools = document.querySelector('.sign-tools');
  if (tools && !tools.querySelector('[data-act="sign-clear"]')) tools.insertAdjacentHTML('beforeend', `<button type="button" class="btn btn-ghost btn-sm" data-act="sign-clear">${icon('eraser', 16)}Borrar</button>`);
}
function typedSignature() {
  const c = document.createElement('canvas');
  c.width = 600; c.height = 180;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#14264C';
  ctx.font = '72px Caveat, "Segoe Script", cursive';
  ctx.textBaseline = 'middle';
  ctx.fillText(draft.owner.name || 'Firma', 16, 90, 568);
  return c.toDataURL('image/png');
}
document.addEventListener('click', (event) => {
  const mode = event.target.closest('[data-sign-mode]');
  if (mode) { if (draft.owner.signature?.kind !== mode.dataset.signMode) draft.owner.signature = null; signMode = mode.dataset.signMode; render(); onDraftChange('owner.signature'); return; }
  const act = event.target.closest('[data-act]')?.dataset.act;
  if (act === 'sign-clear') { draft.owner.signature = null; render(); onDraftChange('owner.signature'); }
  if (act === 'sign-typed') { setSignature({ kind: 'typed', url: typedSignature() }); render(); }
  if (act === 'pay-by-hand') { payByHandOpen = true; draft.owner.payment_by_hand = true; render(); document.getElementById('owner-payment_details')?.focus(); }
  if (act === 'pay-builder') { payByHandOpen = false; draft.owner.payment_by_hand = false; draft.owner.payment_details = composePayment(); render(); onDraftChange('owner.payment_details'); }
});
document.addEventListener('change', (event) => {
  const input = event.target.closest('[data-sign-file]');
  if (!input?.files?.[0]) return;
  const reader = new FileReader();
  reader.onload = () => { setSignature({ kind: 'photo', url: reader.result }); render(); };
  reader.readAsDataURL(input.files[0]);
});

/* ---------- Keeping the pieces in step: each proposal calls this from onDraftChange ---------- */
function ownerChanged(path) {
  const o = draft.owner;
  if (path === 'owner.payment_details') o.payment_by_hand = payByHandOpen;
  if (!o.payment_by_hand && (path.startsWith('owner.payment.') || path === 'owner.name' || path.startsWith('owner.document'))) {
    o.payment_details = composePayment();
    const written = document.getElementById('pay-written');
    if (written) { written.hidden = !o.payment_details; written.querySelector('p').textContent = o.payment_details; }
    if (o.payment_details) { delete errors['owner.payment_details']; }
  }
  // The bank's own fields appear once it is picked.
  if (path === 'owner.payment.bank') { render(); return; }
  if (path === 'owner.document_type') { const lbl = document.querySelector('label[for="owner-document_number"]'); if (lbl) lbl.textContent = o.document_type === 'nit' ? 'NIT' : 'Número de cédula'; }
  if (path === 'owner.send_day') {
    document.querySelectorAll('#send-help').forEach((h) => { h.textContent = sendHelp(); });
    const other = document.getElementById('owner-send-other');
    if (other && SEND_CHIPS.includes(+o.send_day)) other.value = '';
    if (other && !SEND_CHIPS.includes(+o.send_day)) other.closest('.chips')?.querySelectorAll('.chip').forEach((c) => c.setAttribute('aria-checked', 'false'));
  }
  refreshBill();
}

/* ---------- The bill on paper: a copy of the PDF, showing where each piece ends up ---------- */
let liveSlot = null;
// The send day is the bill's date: the day it is issued and goes out.
const SLOT_OF = { 'owner.name': 'who', 'owner.document_type': 'who', 'owner.document_number': 'who', 'owner.payment_details': 'pay', 'owner.signature': 'sign', 'owner.send_day': 'send' };
const sendDay = () => +(draft.owner.send_day || RECOMMENDED_DAY);
function billPaper({ sample = true } = {}) {
  const o = draft.owner;
  const slot = (k, html) => `<span class="slot${liveSlot === k ? ' live' : ''}" data-slot="${k}">${html}</span>`;
  const doc = o.document_number ? `${docShort(o.document_type)} ${esc(o.document_number)}` : '';
  // A sample tenant pays the 5th, or a few days after the bill if it goes out later.
  const due = Math.min(28, Math.max(5, sendDay() + 4));
  const date = o.send_day ? `${o.send_day} de noviembre de 2026` : '<span class="blank" style="width:120px"></span>';
  return `<article class="bill" aria-label="Así se verá tu cuenta de cobro"><div class="bill-band"></div><div class="bill-in">
    <div class="bill-head"><h3>Cuenta de cobro</h3><p class="no">N.º 0001</p></div>
    <p class="bill-date">${slot('send', date)}</p>
    <hr>
    <dl class="bill-parties">
      <dt>Cobra</dt><dd>${slot('who', `<b>${esc(o.name) || '<span class="blank" style="width:140px"></span>'}</b><small>${doc || '<span class="blank" style="width:90px"></span>'}</small>`)}</dd>
      <dt>Debe</dt><dd><b>Marta Ríos</b><small>C.C. 1.020.334.556</small></dd>
    </dl>
    <hr>
    <div class="bill-line"><p>Canon de arrendamiento<small>Noviembre 2026 · Apto 101</small></p><b>$1.450.000</b></div>
    <hr>
    <div class="bill-total"><span>Total a pagar</span><b>$1.450.000</b></div>
    <p class="bill-box">Vence el ${due} de noviembre de 2026${slot('pay', o.payment_details ? `\nPagar a: ${esc(o.payment_details)}` : '\nPagar a: <span class="blank" style="width:55%"></span>')}</p>
    <div class="bill-sign">${slot('sign', o.signature ? `<img src="${o.signature.url}" alt="Tu firma">` : '<span class="sign-empty"></span>')}<b>${esc(o.name)}</b><small>${doc}</small></div>
    <div class="bill-foot"><span>N.º 0001 · ${o.send_day ? `${o.send_day} nov 2026` : 'nov 2026'}</span><span>Página 1 de 1</span></div>
    <div class="bill-logo">${isotype(18)}</div>
    ${sample ? '<p class="bill-sample">El arrendatario y el canon son de ejemplo.</p>' : ''}
  </div></article>`;
}
function refreshBill() {
  document.querySelectorAll('[data-bill]').forEach((el) => { el.innerHTML = billPaper(); });
}
// The spot of the bill that the focused field fills lights up.
function lightSlot(path) {
  const k = SLOT_OF[path] || (path?.startsWith('owner.payment') ? 'pay' : null);
  if (k === liveSlot) return;
  liveSlot = k;
  document.querySelectorAll('.bill .slot').forEach((s) => s.classList.toggle('live', s.dataset.slot === k));
}
document.addEventListener('focusin', (e) => { const p = e.target.dataset?.bind || e.target.dataset?.pick; if (p?.startsWith('owner.')) lightSlot(p); else if (e.target.closest('.sign-pad')) lightSlot('owner.signature'); });

/* ---------- Shared screens: welcome and the hand-off to the property ---------- */
function savedList() {
  const o = draft.owner;
  return `<ul class="saved">
    <li>${icon('check')}<p><b>${esc(o.name)}</b><span>${docShort(o.document_type)} ${esc(o.document_number)}</span></p></li>
    <li>${icon('check')}<p><b>Cómo te pagan</b><span>${esc(o.payment_details)}</span></p></li>
    <li>${icon('check')}<p><b>Tu firma</b>${o.signature ? `<img src="${o.signature.url}" alt="Tu firma">` : ''}</p></li>
    <li>${icon('check')}<p><b>Día de envío</b><span>El ${esc(o.send_day)} de cada mes</span></p></li>
  </ul>`;
}
function handoffScreen() {
  return `<div class="page"><div class="top">${brand(24)}</div>
    <div class="hello ${enterClass()}">
      <div class="copy">
        <div class="ok">${icon('check')}</div>
        <p class="greet">Listo, ${OWNER.first}</p>
        <h1 class="font-heading">Tus cuentas ya saben quién cobra</h1>
        <p class="lead">Guardamos tus datos. Si sales ahora, al volver sigues desde tu inmueble. Los cambias cuando quieras en Ajustes.</p>
        <a class="btn btn-primary" style="align-self:flex-start" href="inmueble.html${EMBED ? '?embed=1&theme=' + document.documentElement.dataset.theme : ''}#property">Seguir con mi inmueble ${icon('arrow-right')}</a>
      </div>
      <div class="card" style="padding:20px">${savedList()}</div>
    </div></div>`;
}
