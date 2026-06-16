/**
 * OLOGY — M4: Control Panel UI (Desktop)
 * ============================================================================
 * Standalone IIFE. Load via <script src="/m4_ui.js"></script> after index.html.
 * Contracts: M0 v0.2.1
 * ============================================================================
 */
(function () {
  'use strict';

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 0);
  }

  /* ══════════════════════════════════════════════════════════════════════
   * DATA  (from M0 contracts.ts v0.2.1)
   * ══════════════════════════════════════════════════════════════════════ */

  const DRONE_LIBRARY = [
    { id: 'delta-deep-healing',         name: 'Delta — Deep Healing',         category: 'brainwave', carrierHz: 100,   beatHz: 2,    band: 'delta', defaultMode: 'binaural',   effect: 'Deep dreamless sleep, physical recovery' },
    { id: 'delta-regeneration',         name: 'Delta — Regeneration',         category: 'brainwave', carrierHz: 100,   beatHz: 3,    band: 'delta', defaultMode: 'binaural',   effect: 'Restorative rest' },
    { id: 'theta-dreamgate',            name: 'Theta — Dreamgate',            category: 'brainwave', carrierHz: 120,   beatHz: 4,    band: 'theta', defaultMode: 'binaural',   effect: 'Deep meditation, REM-like imagery' },
    { id: 'theta-vision-quest',         name: 'Theta — Vision Quest',         category: 'brainwave', carrierHz: 120,   beatHz: 4.5,  band: 'theta', defaultMode: 'binaural',   effect: 'Shamanic / visualization states' },
    { id: 'theta-intuition',            name: 'Theta — Intuition',            category: 'brainwave', carrierHz: 136.1, beatHz: 6,    band: 'theta', defaultMode: 'binaural',   effect: 'Intuition, inner journeying' },
    { id: 'schumann-earth-pulse',       name: 'Schumann — Earth Pulse',       category: 'brainwave', carrierHz: 136.1, beatHz: 7.83, band: 'theta', defaultMode: 'isochronic', effect: 'Grounding, calm, sense of oneness' },
    { id: 'alpha-calm-mind',            name: 'Alpha — Calm Mind',            category: 'brainwave', carrierHz: 210,   beatHz: 8.4,  band: 'alpha', defaultMode: 'binaural',   effect: 'Pre-sleep, stress release' },
    { id: 'alpha-serenity',             name: 'Alpha — Serenity',             category: 'brainwave', carrierHz: 200,   beatHz: 10,   band: 'alpha', defaultMode: 'binaural',   effect: 'Relaxed focus, flow' },
    { id: 'beta-focus',                 name: 'Beta — Focus',                 category: 'brainwave', carrierHz: 250,   beatHz: 16,   band: 'beta',  defaultMode: 'isochronic', effect: 'Alertness, concentration' },
    { id: 'gamma-insight',              name: 'Gamma — Insight',              category: 'brainwave', carrierHz: 300,   beatHz: 40,   band: 'gamma', defaultMode: 'isochronic', effect: 'Peak cognition, heightened perception' },
    { id: 'solfeggio-transformation',   name: 'Solfeggio — Transformation',   category: 'solfeggio', carrierHz: 528,   beatHz: 7.83, band: 'theta', defaultMode: 'isochronic', effect: 'Tradition-attributed "repair/transformation"' },
    { id: 'solfeggio-awaken-intuition', name: 'Solfeggio — Awaken Intuition', category: 'solfeggio', carrierHz: 852,   beatHz: 6,    band: 'theta', defaultMode: 'isochronic', effect: 'Tradition-attributed "inner sight"' },
    { id: 'solfeggio-crown-pineal',     name: 'Solfeggio — Crown / Pineal',   category: 'solfeggio', carrierHz: 963,   beatHz: 7.83, band: 'theta', defaultMode: 'isochronic', effect: 'Tradition-attributed "higher connection"' },
  ];

  const AMBIENT_BEDS = [
    { id: 'none',      name: 'None' },
    { id: 'womb',      name: 'Womb' },
    { id: 'waterfall', name: 'Waterfall' },
    { id: 'jungle',    name: 'Jungle' },
    { id: 'forest',    name: 'Forest' },
    { id: 'whales',    name: 'Whales' },
    { id: 'ocean',     name: 'Ocean' },
  ];

  const FREQ_BANDS    = ['sub', 'low', 'mid', 'high'];
  const REACT_PARAMS  = ['bloom', 'zoom', 'chaos', 'colorShift', 'speed'];

  /* ══════════════════════════════════════════════════════════════════════
   * CSS
   * ══════════════════════════════════════════════════════════════════════ */
  const CSS = `
/* Voice tab hidden — removed in v0.2 */
.nav-item[data-tab=voice] { display: none !important; }

/* Drone dropdown */
#m4-drone-sel {
  width: 100%;
  background: rgba(0,0,0,.35);
  border: 1px solid var(--stroke);
  border-radius: 8px;
  color: var(--txt);
  padding: 8px 10px;
  font-size: 11px;
  margin-bottom: 8px;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
}
#m4-drone-sel:focus { outline: 2px solid var(--acc); }
.m4-drone-effect {
  font-size: 9.5px;
  color: var(--faint);
  line-height: 1.5;
  margin-bottom: 10px;
  font-style: italic;
}

/* Reactivity matrix */
#m4-react-matrix {
  display: grid;
  grid-template-columns: 38px repeat(5, 1fr);
  gap: 3px;
  margin-bottom: 4px;
}
.m4-rm-hdr {
  color: var(--faint);
  text-align: center;
  font-size: 8px;
  letter-spacing: .6px;
  text-transform: uppercase;
  padding: 3px 1px;
}
.m4-rm-band {
  color: var(--dim);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .5px;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 4px;
}
.m4-rm-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.m4-rm-cell input[type=range] {
  appearance: slider-vertical;
  -webkit-appearance: slider-vertical;
  writing-mode: vertical-lr;
  direction: rtl;
  width: 22px;
  height: 44px;
  accent-color: var(--acc);
}
.m4-rm-val {
  font-size: 8px;
  color: var(--acc2);
  font-variant-numeric: tabular-nums;
}

/* Preset list */
#m4-preset-list { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; }
.m4-preset-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 9px;
  border: 1px solid var(--stroke);
  background: rgba(255,255,255,.025);
  cursor: pointer;
  transition: .15s;
  min-height: 44px;
}
.m4-preset-row:hover { border-color: rgba(168,117,255,.3); background: rgba(168,117,255,.06); }
.m4-preset-row.flash { border-color: var(--acc); background: rgba(168,117,255,.12); }
.m4-preset-star { font-size: 12px; cursor: pointer; flex-shrink: 0; }
.m4-preset-name { flex: 1; font-size: 11px; color: var(--txt); }
.m4-preset-meta { font-size: 9px; color: var(--faint); white-space: nowrap; }
.m4-preset-del  { font-size: 11px; color: var(--faint); cursor: pointer; padding: 4px 6px; border-radius: 4px; transition: .12s; }
.m4-preset-del:hover { color: var(--red); background: rgba(255,78,106,.12); }

/* Agent notice */
.m4-agent-notice {
  background: rgba(168,117,255,.08);
  border: 1px solid rgba(168,117,255,.2);
  border-radius: 10px;
  padding: 12px 13px;
  margin-bottom: 14px;
}
.m4-agent-notice p { font-size: 10.5px; color: var(--dim); line-height: 1.6; margin: 0; }
.m4-agent-notice strong { color: var(--acc); }

/* Focus ring */
:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
`;

  /* ══════════════════════════════════════════════════════════════════════
   * INIT
   * ══════════════════════════════════════════════════════════════════════ */
  function init() {
    injectCSS();
    patchSidebar();
    patchVisualPane();
    buildAudioPane();
    buildPresetsPane();
    buildAgentPane();
    loadPresetsFromStorage();
    console.log('[M4] wired.');
  }

  function injectCSS() {
    const el = document.createElement('style');
    el.id = 'm4-css';
    el.textContent = CSS;
    document.head.appendChild(el);
  }

  /* ══════════════════════════════════════════════════════════════════════
   * SIDEBAR — hide Voice tab (removed in v0.2)
   * ══════════════════════════════════════════════════════════════════════ */
  function patchSidebar() {
    document.querySelectorAll('.nav-item').forEach(function (ni) {
      if (ni.textContent.trim().toLowerCase().includes('voice')) {
        ni.setAttribute('data-tab', 'voice');
      }
    });
  }

  /* ══════════════════════════════════════════════════════════════════════
   * VISUALS PANE — wire bloom (exists in HTML but had no oninput id)
   * ══════════════════════════════════════════════════════════════════════ */
  function patchVisualPane() {
    const pane = document.querySelector('[data-pane="visuals"]');
    if (!pane) return;

    pane.querySelectorAll('.row').forEach(function (row) {
      const label = row.querySelector('label');
      const inp   = row.querySelector('input[type=range]');
      const rval  = row.querySelector('.rval');
      if (!label || !inp) return;
      if (label.textContent.trim().toLowerCase() === 'bloom') {
        inp.addEventListener('input', function () {
          if (typeof window.SP === 'function') window.SP('bloom', +inp.value);
          if (rval) rval.textContent = (+inp.value / 100).toFixed(2);
        });
        inp.value = window.PREV ? Math.round((window.PREV.bloom || 0.65) * 100) : 65;
      }
    });
  }

  /* ══════════════════════════════════════════════════════════════════════
   * AUDIO PANE
   * ══════════════════════════════════════════════════════════════════════ */
  function buildAudioPane() {
    const pane = document.querySelector('[data-pane="audio"]');
    if (!pane) return;
    pane.innerHTML = '';

    // ── Transport ──────────────────────────────────────────────────────
    const transport = el('div', 'section');
    transport.innerHTML = `
      <h4>Transport</h4>
      <div class="transport">
        <button class="tp-btn stop on" id="tp-stop" data-tp="stop"
                onclick="window.setTransport('stop')"><span class="e">■</span>Stop</button>
        <button class="tp-btn" id="tp-play" data-tp="play"
                onclick="window.setTransport('play')"><span class="e">▶</span><span id="tp-play-lbl">Play</span></button>
      </div>`;
    pane.appendChild(transport);

    // ── Drone Preset (dropdown) ────────────────────────────────────────
    const droneSection = el('div', 'section');
    const activeDroneId = (window.PROG && window.PROG.audio) ? window.PROG.audio.droneId : 'theta-intuition';

    let optionsHTML = '';
    // Group: brainwave then solfeggio
    ['brainwave', 'solfeggio'].forEach(function (cat) {
      const group = DRONE_LIBRARY.filter(function (d) { return d.category === cat; });
      const label = cat === 'brainwave' ? 'Brainwave' : 'Solfeggio';
      optionsHTML += `<optgroup label="${label}">`;
      group.forEach(function (d) {
        const sel = d.id === activeDroneId ? ' selected' : '';
        optionsHTML += `<option value="${d.id}"${sel}>${d.name} · ${d.carrierHz} Hz / ${d.beatHz} Hz</option>`;
      });
      optionsHTML += '</optgroup>';
    });

    droneSection.innerHTML = `
      <h4>Drone Preset</h4>
      <select id="m4-drone-sel" aria-label="Drone preset">${optionsHTML}</select>
      <div class="m4-drone-effect" id="m4-drone-effect"></div>`;
    pane.appendChild(droneSection);

    // Sync effect text on load
    updateDroneEffect(activeDroneId);

    document.getElementById('m4-drone-sel').addEventListener('change', function () {
      const id = this.value;
      const drone = DRONE_LIBRARY.find(function (d) { return d.id === id; });
      if (!drone) return;
      updateDroneEffect(id);
      // Sync carrier/beat sliders
      const cs = document.getElementById('m4-carrier-slider');
      const bs = document.getElementById('m4-beat-slider');
      if (cs) { cs.value = drone.carrierHz; safeText('m4-carrier-ro', Math.round(drone.carrierHz)); }
      if (bs) { bs.value = drone.beatHz;    safeText('m4-beat-ro', drone.beatHz.toFixed(1)); }
      syncModeSeg(drone.defaultMode);
      // Fire M2
      if (typeof window.uiDrone === 'function') window.uiDrone(id, this);
      else if (window.OlogyAudio) window.OlogyAudio.setDrone(id);
    });

    // ── Carrier / Beat ─────────────────────────────────────────────────
    const freqSection = el('div', 'section');
    const initDrone = DRONE_LIBRARY.find(function (d) { return d.id === activeDroneId; }) || DRONE_LIBRARY[4];
    freqSection.innerHTML = `
      <h4>Frequency Override</h4>
      <div class="row">
        <label>Carrier (Hz)</label>
        <input type="range" id="m4-carrier-slider" min="60" max="1000"
               value="${initDrone.carrierHz}" style="width:100px">
        <span class="rval" id="m4-carrier-ro">${Math.round(initDrone.carrierHz)}</span>
      </div>
      <div class="row">
        <label>Beat (Hz)</label>
        <input type="range" id="m4-beat-slider" min="0.5" max="40" step="0.1"
               value="${initDrone.beatHz}" style="width:100px">
        <span class="rval" id="m4-beat-ro">${initDrone.beatHz.toFixed(1)}</span>
      </div>
      <div class="note" id="droneInfo" style="margin-top:2px"></div>`;
    pane.appendChild(freqSection);

    document.getElementById('m4-carrier-slider').addEventListener('input', function () {
      safeText('m4-carrier-ro', Math.round(+this.value));
      if (typeof window.uiCarrier === 'function') window.uiCarrier(+this.value);
      else if (window.OlogyAudio) window.OlogyAudio.setCarrier(+this.value);
    });
    document.getElementById('m4-beat-slider').addEventListener('input', function () {
      safeText('m4-beat-ro', (+this.value).toFixed(1));
      if (typeof window.uiBeat === 'function') window.uiBeat(+this.value);
      else if (window.OlogyAudio) window.OlogyAudio.setBeat(+this.value);
    });

    // ── Entrainment Mode ───────────────────────────────────────────────
    const modeSection = el('div', 'section');
    modeSection.innerHTML = `
      <h4>Entrainment Mode</h4>
      <div class="seg" id="m4-mode-seg">
        <button data-mode="binaural" class="${initDrone.defaultMode === 'binaural' ? 'on' : ''}">Binaural</button>
        <button data-mode="isochronic" class="${initDrone.defaultMode === 'isochronic' ? 'on' : ''}">Isochronic</button>
        <button data-mode="monaural" class="${initDrone.defaultMode === 'monaural' ? 'on' : ''}">Monaural</button>
      </div>`;
    pane.appendChild(modeSection);

    document.getElementById('m4-mode-seg').querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        syncModeSeg(btn.getAttribute('data-mode'));
        if (typeof window.uiMode === 'function') window.uiMode(btn.getAttribute('data-mode'), btn);
        else if (window.OlogyAudio) window.OlogyAudio.setMode(btn.getAttribute('data-mode'));
      });
    });

    // ── Ambient Bed ────────────────────────────────────────────────────
    const bedSection = el('div', 'section');
    const activeBed = (window.PROG && window.PROG.audio) ? window.PROG.audio.ambientBed : 'womb';
    const activeBlend = (window.PROG && window.PROG.audio) ? Math.round(window.PROG.audio.ambientBlend * 100) : 30;

    let bedChips = '';
    AMBIENT_BEDS.forEach(function (b) {
      bedChips += `<span class="chip${b.id === activeBed ? ' on' : ''}" data-bed="${b.id}">${b.name}</span>`;
    });
    bedSection.innerHTML = `
      <h4>Ambient Bed</h4>
      <div class="chips" id="m4-bed-chips">${bedChips}</div>
      <div class="row" style="margin-top:8px">
        <label>Blend</label>
        <input type="range" id="m4-blend-slider" min="0" max="100"
               value="${activeBlend}" style="width:100px">
        <span class="rval" id="m4-blend-ro">${(activeBlend / 100).toFixed(2)}</span>
      </div>`;
    pane.appendChild(bedSection);

    document.getElementById('m4-bed-chips').querySelectorAll('.chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        document.getElementById('m4-bed-chips').querySelectorAll('.chip').forEach(function (c) { c.classList.remove('on'); });
        chip.classList.add('on');
        const id = chip.getAttribute('data-bed');
        if (typeof window.uiBed === 'function') window.uiBed(id, chip);
        else if (window.OlogyAudio) window.OlogyAudio.setBed(id);
      });
    });
    document.getElementById('m4-blend-slider').addEventListener('input', function () {
      safeText('m4-blend-ro', (+this.value / 100).toFixed(2));
      if (typeof window.uiBlend === 'function') window.uiBlend(+this.value);
      else if (window.OlogyAudio) window.OlogyAudio.setBedBlend(+this.value / 100);
    });

    // ── Loop ───────────────────────────────────────────────────────────
    const loopSection = el('div', 'section');
    loopSection.innerHTML = `
      <h4>Loop Behavior</h4>
      <div class="seg" id="loopSeg">
        <button class="on" data-loop="evolving"  onclick="window.uiLoop&&window.uiLoop('evolving',this)">Evolving</button>
        <button data-loop="crossfade" onclick="window.uiLoop&&window.uiLoop('crossfade',this)">Crossfade</button>
        <button data-loop="one-shot"  onclick="window.uiLoop&&window.uiLoop('one-shot',this)">One-shot</button>
      </div>`;
    pane.appendChild(loopSection);

    // ── Modulation & Master ────────────────────────────────────────────
    const modSection = el('div', 'section');
    const audio = (window.PROG && window.PROG.audio) || {};
    modSection.innerHTML = `
      <h4>Modulation &amp; Master</h4>
      <div class="row">
        <label>Brain-tickle</label>
        <input type="range" id="m4-tickle-slider" min="0" max="100"
               value="${Math.round((audio.brainTickleAmount || 0.2) * 100)}" style="width:100px">
        <span class="rval" id="tickleRO">${(audio.brainTickleAmount || 0.2).toFixed(2)}</span>
      </div>
      <div class="row">
        <label>Slowness</label>
        <input type="range" id="m4-slow-slider" min="0" max="100"
               value="${Math.round((audio.slowness || 0.6) * 100)}" style="width:100px">
        <span class="rval" id="slowRO">${(audio.slowness || 0.6).toFixed(2)}</span>
      </div>
      <div class="row">
        <label>Master Vol</label>
        <input type="range" id="m4-master-slider" min="0" max="100"
               value="${Math.round((audio.masterLevel || 0.8) * 100)}" style="width:100px">
        <span class="rval" id="masterRO">${(audio.masterLevel || 0.8).toFixed(2)}</span>
      </div>`;
    pane.appendChild(modSection);

    document.getElementById('m4-tickle-slider').addEventListener('input', function () {
      safeText('tickleRO', (+this.value / 100).toFixed(2));
      if (typeof window.uiTickle === 'function') window.uiTickle(+this.value);
      else if (window.OlogyAudio) window.OlogyAudio.setTickle(+this.value / 100);
    });
    document.getElementById('m4-slow-slider').addEventListener('input', function () {
      safeText('slowRO', (+this.value / 100).toFixed(2));
      if (typeof window.uiSlow === 'function') window.uiSlow(+this.value);
      else if (window.OlogyAudio) window.OlogyAudio.setSlowness(+this.value / 100);
    });
    document.getElementById('m4-master-slider').addEventListener('input', function () {
      safeText('masterRO', (+this.value / 100).toFixed(2));
      if (typeof window.uiMaster === 'function') window.uiMaster(+this.value);
      else if (window.OlogyAudio) window.OlogyAudio.setMaster(+this.value / 100);
    });

    // ── Reactivity Matrix ──────────────────────────────────────────────
    buildReactivityMatrix(pane);
  }

  function updateDroneEffect(id) {
    const drone = DRONE_LIBRARY.find(function (d) { return d.id === id; });
    safeText('m4-drone-effect', drone ? drone.effect : '');
  }

  function syncModeSeg(mode) {
    const seg = document.getElementById('m4-mode-seg');
    if (!seg) return;
    seg.querySelectorAll('button').forEach(function (b) {
      b.classList.toggle('on', b.getAttribute('data-mode') === mode);
    });
  }

  function buildReactivityMatrix(pane) {
    const section = el('div', 'section');
    section.innerHTML = '<h4>Reactivity · Band → Visual</h4>';

    const matrix = document.createElement('div');
    matrix.id = 'm4-react-matrix';

    // Header row
    const corner = document.createElement('div');
    corner.className = 'm4-rm-hdr';
    matrix.appendChild(corner);
    REACT_PARAMS.forEach(function (p) {
      const h = document.createElement('div');
      h.className = 'm4-rm-hdr';
      h.textContent = p === 'colorShift' ? 'CLR' : p.toUpperCase().slice(0, 4);
      matrix.appendChild(h);
    });

    // Default route amounts from PROG
    const routes = (window.PROG && window.PROG.audio && window.PROG.audio.routes) || [];
    function defaultAmt(band, param) {
      const r = routes.find(function (x) { return x.band === band && x.param === param; });
      return r ? Math.round(r.amount * 100) : 0;
    }

    FREQ_BANDS.forEach(function (band) {
      const bandCell = document.createElement('div');
      bandCell.className = 'm4-rm-band';
      bandCell.textContent = band.toUpperCase();
      matrix.appendChild(bandCell);

      REACT_PARAMS.forEach(function (param) {
        const cell = document.createElement('div');
        cell.className = 'm4-rm-cell';
        const v = defaultAmt(band, param);

        const inp = document.createElement('input');
        inp.type = 'range';
        inp.min = '0'; inp.max = '100'; inp.value = v;
        inp.setAttribute('aria-label', band + '→' + param);

        const valEl = document.createElement('div');
        valEl.className = 'm4-rm-val';
        valEl.textContent = (v / 100).toFixed(2);

        inp.addEventListener('input', function () {
          valEl.textContent = (+inp.value / 100).toFixed(2);
          const synth = { value: +inp.value, parentNode: { querySelector: function () { return valEl; } } };
          if (typeof window.uiRoute === 'function') window.uiRoute(band, param, synth);
          else if (window.OlogyAudio) window.OlogyAudio.setRoute(band, param, +inp.value / 100);
        });

        cell.appendChild(inp);
        cell.appendChild(valEl);
        matrix.appendChild(cell);
      });
    });

    section.appendChild(matrix);
    pane.appendChild(section);
  }

  /* ══════════════════════════════════════════════════════════════════════
   * PRESETS PANE
   * ══════════════════════════════════════════════════════════════════════ */
  const PRESETS_KEY = 'ology_presets_v1';
  let _presets = [];

  function loadPresetsFromStorage() {
    try {
      const raw = localStorage.getItem(PRESETS_KEY);
      if (raw) _presets = JSON.parse(raw);
    } catch (e) { _presets = []; }
    if (_presets.length === 0) {
      _presets = [
        { id: 'seed-grief',    name: 'Grief Journey',    visual: null, audio: null, createdAt: new Date().toISOString(), favorite: true  },
        { id: 'seed-dj',       name: 'Supernova DJ',     visual: null, audio: null, createdAt: new Date().toISOString(), favorite: false },
        { id: 'seed-sleep',    name: 'Womb Sleep Drift', visual: null, audio: null, createdAt: new Date().toISOString(), favorite: true  },
        { id: 'seed-podcast',  name: 'Podcast BG',       visual: null, audio: null, createdAt: new Date().toISOString(), favorite: false },
      ];
    }
    renderPresetList();
  }

  function savePresetsToStorage() {
    try { localStorage.setItem(PRESETS_KEY, JSON.stringify(_presets)); } catch (e) {}
  }

  function buildPresetsPane() {
    const pane = document.querySelector('[data-pane="presets"]');
    if (!pane) return;
    pane.innerHTML = '';

    // List
    const listSection = el('div', 'section');
    listSection.innerHTML = '<h4>Saved Sessions</h4><div id="m4-preset-list"></div>';
    pane.appendChild(listSection);

    // Recents dropdown
    const recentSection = el('div', 'section');
    recentSection.innerHTML = `
      <h4>Load Recent</h4>
      <select id="m4-recents-sel" style="width:100%;background:rgba(0,0,0,.35);border:1px solid var(--stroke);border-radius:8px;color:var(--txt);padding:8px 10px;font-size:11px;cursor:pointer" aria-label="Load recent preset">
        <option value="">— Select —</option>
      </select>`;
    pane.appendChild(recentSection);

    // Actions
    const actSection = el('div', 'section');

    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn-p';
    saveBtn.textContent = '💾 Save current session';
    saveBtn.addEventListener('click', function () {
      const name = prompt('Preset name:', 'Session ' + new Date().toLocaleTimeString());
      if (!name) return;
      _presets.unshift({
        id: 'p-' + Date.now(),
        name: name,
        visual: window.PROG ? Object.assign({}, window.PROG) : null,
        audio:  window.PROG && window.PROG.audio ? Object.assign({}, window.PROG.audio) : null,
        createdAt: new Date().toISOString(),
        favorite: false,
      });
      savePresetsToStorage();
      renderPresetList();
    });

    const exportBtn = document.createElement('button');
    exportBtn.className = 'btn-g';
    exportBtn.textContent = '↓ Export JSON';
    exportBtn.addEventListener('click', function () {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([JSON.stringify(_presets, null, 2)], { type: 'application/json' }));
      a.download = 'ology-presets-' + Date.now() + '.json';
      a.click();
    });

    const importBtn = document.createElement('button');
    importBtn.className = 'btn-g';
    importBtn.textContent = '↑ Import JSON';
    importBtn.addEventListener('click', function () {
      const inp = document.createElement('input');
      inp.type = 'file'; inp.accept = '.json,application/json';
      inp.onchange = function () {
        const reader = new FileReader();
        reader.onload = function (e) {
          try {
            const data = JSON.parse(e.target.result);
            if (Array.isArray(data)) { _presets = data.concat(_presets); savePresetsToStorage(); renderPresetList(); }
            else alert('Not a valid preset file.');
          } catch (err) { alert('Parse error: ' + err.message); }
        };
        reader.readAsText(inp.files[0]);
      };
      inp.click();
    });

    actSection.appendChild(saveBtn);
    actSection.appendChild(exportBtn);
    actSection.appendChild(importBtn);
    pane.appendChild(actSection);
  }

  function renderPresetList() {
    const list = document.getElementById('m4-preset-list');
    if (!list) return;
    list.innerHTML = '';

    const sorted = _presets.slice().sort(function (a, b) {
      if (a.favorite !== b.favorite) return a.favorite ? -1 : 1;
      return new Date(b.createdAt) - new Date(a.createdAt);
    });

    sorted.forEach(function (preset) {
      const row = document.createElement('div');
      row.className = 'm4-preset-row';
      row.setAttribute('tabindex', '0');
      const dateStr = new Date(preset.createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      row.innerHTML = `
        <span class="m4-preset-star">${preset.favorite ? '⭐' : '☆'}</span>
        <span class="m4-preset-name">${preset.name}</span>
        <span class="m4-preset-meta">${dateStr}</span>
        <button class="m4-preset-del" title="Delete">✕</button>`;

      function load() {
        if (!preset.visual || !window.PREV) return;
        Object.assign(window.PREV, preset.visual);
        if (preset.audio && window.PROG && window.PROG.audio) Object.assign(window.PROG.audio, preset.audio);
        row.classList.add('flash');
        setTimeout(function () { row.classList.remove('flash'); }, 500);
      }
      row.addEventListener('click', function (e) {
        if (!e.target.classList.contains('m4-preset-star') && !e.target.classList.contains('m4-preset-del')) load();
      });
      row.addEventListener('keydown', function (e) { if (e.key === 'Enter') load(); });

      row.querySelector('.m4-preset-star').addEventListener('click', function (e) {
        e.stopPropagation();
        preset.favorite = !preset.favorite;
        savePresetsToStorage(); renderPresetList();
      });
      row.querySelector('.m4-preset-del').addEventListener('click', function (e) {
        e.stopPropagation();
        if (!confirm('Delete "' + preset.name + '"?')) return;
        _presets = _presets.filter(function (p) { return p.id !== preset.id; });
        savePresetsToStorage(); renderPresetList();
      });

      list.appendChild(row);
    });

    if (sorted.length === 0) {
      list.innerHTML = '<p class="note" style="padding:6px 0">No presets yet.</p>';
    }

    // Sync recents dropdown
    const sel = document.getElementById('m4-recents-sel');
    if (!sel) return;
    sel.innerHTML = '<option value="">— Select —</option>';
    _presets.slice(0, 10).forEach(function (p) {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = (p.favorite ? '⭐ ' : '') + p.name;
      sel.appendChild(opt);
    });
    sel.onchange = function () {
      const p = _presets.find(function (x) { return x.id === sel.value; });
      if (p && p.visual && window.PREV) {
        Object.assign(window.PREV, p.visual);
        if (p.audio && window.PROG && window.PROG.audio) Object.assign(window.PROG.audio, p.audio);
      }
      sel.value = '';
    };
  }

  /* ══════════════════════════════════════════════════════════════════════
   * AGENT PANE  (inert v1)
   * ══════════════════════════════════════════════════════════════════════ */
  function buildAgentPane() {
    const pane = document.querySelector('[data-pane="agent"]');
    if (!pane) return;
    pane.innerHTML = '';

    const notice = el('div', 'm4-agent-notice');
    notice.innerHTML = `<p><strong>Ology Agent — Phase 2</strong><br>
      Autonomously sequences themes, drones, and beds for a guided journey
      within your guardrails. Service interface is already shaped in M0
      contracts — no refactor needed when v2 arrives.</p>`;
    pane.appendChild(notice);

    const enableSection = el('div', 'section');
    enableSection.innerHTML = `
      <h4>Autonomy</h4>
      <div class="row">
        <label>Enable Agent</label>
        <div class="tog" id="m4-agent-tog" role="switch" aria-checked="false" tabindex="0"><b></b></div>
        <span class="rval" id="m4-agent-status" style="color:var(--faint)">off</span>
      </div>`;
    pane.appendChild(enableSection);

    const tog = document.getElementById('m4-agent-tog');
    tog.addEventListener('click', function () {
      const on = tog.classList.toggle('on');
      tog.setAttribute('aria-checked', on ? 'true' : 'false');
      safeText('m4-agent-status', on ? 'enabled (v2)' : 'off');
      if (window.PROG) window.PROG.agentEnabled = on;
    });
    tog.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tog.click(); }
    });

    const guardrailSection = el('div', 'section');
    guardrailSection.innerHTML = `
      <h4>Guardrails</h4>
      <div class="row">
        <label>Chaos cap</label>
        <input type="range" min="0" max="100" value="60" style="width:100px"
               oninput="this.nextElementSibling.textContent=(this.value/100).toFixed(2)">
        <span class="rval">0.60</span>
      </div>
      <div class="row">
        <label>Session max</label>
        <input type="range" min="5" max="120" step="5" value="20" style="width:100px"
               oninput="this.nextElementSibling.textContent=this.value+'m'">
        <span class="rval">20m</span>
      </div>
      <div class="row">
        <label>Strobe ceiling</label>
        <input type="range" min="1" max="3" step="0.5" value="3" style="width:100px"
               oninput="this.nextElementSibling.textContent=Math.min(3,+this.value)+' Hz'">
        <span class="rval">3 Hz</span>
      </div>`;
    pane.appendChild(guardrailSection);
  }

  /* ══════════════════════════════════════════════════════════════════════
   * FIX E — isPlaying gate in index.html toM1State
   *
   * toM1State() hardcodes audio.isPlaying:false (index.html line ~546).
   * This kills all audio reactivity routes in M1's reactiveParams().
   * Fix: wrap toM1State after it is defined and patch the audio block
   * to read the live value from PROG.audio.isPlaying instead.
   * ══════════════════════════════════════════════════════════════════════ */
  (function patchToM1State() {
    // Wait one tick to ensure index.html's IIFE has fully run
    setTimeout(function () {
      // toM1State is a closure-private function inside index.html's IIFE.
      // We cannot directly patch it. Instead we patch the render loop's
      // frame argument: override window.OlogyShaders.draw so that before
      // every call we fix the isPlaying flag on the state object passed in.
      if (!window.OlogyShaders || typeof window.OlogyShaders.draw !== 'function') {
        // M1 not loaded yet — retry once more
        setTimeout(patchToM1State, 200);
        return;
      }
      const _origDraw = window.OlogyShaders.draw.bind(window.OlogyShaders);
      window.OlogyShaders.draw = function (dest, state, analysisFrame, t, strobeGate) {
        // Inject the live isPlaying value so reactiveParams() gates correctly
        if (state && state.audio && window.PROG && window.PROG.audio) {
          state.audio.isPlaying = window.PROG.audio.isPlaying;
          // Also carry live routes so matrix edits take effect immediately
          if (window.PROG.audio.routes && window.PROG.audio.routes.length) {
            state.audio.routes = window.PROG.audio.routes;
          }
        }
        return _origDraw(dest, state, analysisFrame, t, strobeGate);
      };
      console.log('[M4] isPlaying gate patched on OlogyShaders.draw.');
    }, 50);
  })();

  /* ══════════════════════════════════════════════════════════════════════
   * UTILITIES
   * ══════════════════════════════════════════════════════════════════════ */
  function el(tag, className) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    return e;
  }

  function safeText(id, text) {
    const e = document.getElementById(id);
    if (e) e.textContent = text;
  }

})();
