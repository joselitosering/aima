# OLOGY — App Blueprint & White Paper
### Endless audio-reactive kaleidoscope for meditation, neuroplasticity, and live performance
**Version:** 1.5.1 (Beta) · **Brand:** AIMA Productions · **Owner:** Joe  
**Supersedes:** v1.3. Changes this version: **`index.html` renamed `web.html`**; **`mobile.html` introduced** as the dedicated mobile Stage; **theme renamed** `Intergalactic Beings` (was `Interdimensional Beings` in v1.4 session — reverted); **default load theme** both PREVIEW and PROGRAM set to `Intergalactic Beings` on page load; **9:16 canvas viewer portrait fix** — `display:block` + `calc(100% - 24px)` height pattern; **help guide shipped as `ology_help.html` v1.5** — responsive, mobile-safe, annotated SVG UI diagrams, Isochronic flash warning; **Safe Mode (strobe gate) shipped in v1.5.1** — NULL_ANALYSIS frame substitution across all three files, topbar indicator dot, localStorage persistence. **Locked as Beta v1.5.1.**

---

## 0. Read This First
This is the **orchestrator document**. It defines the vision, the UX, the architecture, the module contracts, and the build order. Each numbered module is its **own artifact**, edited independently so changes to one never re-emit the others.

**v1.5 / v1.5.1 (Beta) changes at a glance:**

- **`web.html` is the Stage file.** `index.html` was renamed `web.html`. All references to `index.html` in previous blueprint versions now read `web.html`. `output.html` is unchanged.
- **`mobile.html` introduced.** Dedicated mobile Stage page. Full audio + visual engine. Three-column layout on desktop/tablet; stacked column layout on phone (≤430 px). Five nav tabs: Visuals, Audio, Output, Presets, Help. Sticky GO bar at bottom on phone. iOS speaker unlock on first tap.
- **Theme name: `Intergalactic Beings`.** The display name and id `intergalactic-beings` are canonical. A session rename to `Interdimensional Beings` was trialled and reverted — both `web.html` and `mobile.html` use `intergalactic-beings` / `Intergalactic Beings` throughout.
- **Default load theme.** Both PREVIEW (`PREV.th`) and PROGRAM (`PROG.th`) default to index `0` = `Intergalactic Beings` on page load.
- **9:16 portrait canvas viewer.** When the Output tab AR selector is set to `9:16`, the canvas viewer switches to `display:block` with `height:calc(100% - 24px)` so the canvas fits top-to-bottom without cropping. 16:9 / 1:1 / 4:3 remain side-constrained.
- **Help guide `ology_help.html` v1.5.** Responsive sidebar + content layout. Off-canvas slide-in nav drawer on mobile (☰ toggle). Safe-area-inset padding for iPhone notch/home bar. Two annotated SVG UI diagrams (desktop 3-col, phone portrait). Isochronic flash-sensitivity warning in Audio Tab and Safety section. All 14 sections including Session Recipes, OBS Setup, Drone Library, Frequency Guide.
- **Safe Mode (strobe gate) shipped in v1.5.1.** NULL_ANALYSIS frame substitution — all audio reactivity bands zeroed when Safe Mode is On. Gate implemented across web.html, mobile.html, and output.html. Topbar `●` indicator dot (green=On, red=Off). State persisted in `ology_strobe` localStorage key. Default On (safe).
- **Param overlay color fixes in v1.5.1.** Quantum Fields: bright yellow `#ffe600`. Intergalactic Beings: white with shadow. All other themes: auto-computed 88% lightness theme-tinted color. Global text-shadow restored in `#paramOverlay` CSS.

**v1.3 (Beta) changes (retained):**
- Output tab UI cleaned — resolution/fps buttons removed; Browser Source URL field removed; OBS workflow is Window/Display Capture
- `output.html` `#readout` removed; param overlay font responsive (`clamp(9px,1.2vw,15px)`)
- Overlay toggle label "Param overlay on output" → "On"
- `m4_ui.js` confirmed not loaded

**v1.1 (Beta) changes (retained):** M9 inline presets; PREVIEW-stage apply; M7 `load-preset` wire; Help Guide shipped.

**v0.4.2 changes (retained):** M7 serverless WebRTC DataChannel (`OlogyLink`), Path C QR/paste SDP signaling.

**v0.4.1 changes (retained):** M6 built — `output.html` param overlay + Output-tab toggle. Real-time audio param sync.

---

## 1. Vision

Ology generates an **infinite, never-repeating kaleidoscope** driven by live sonic frequency analysis. Fractal geometry + chaos modulation + thematic colour grading respond in real time to an internally generated soundbed (drones + binaural/isochronic/monaural entrainment tones + ambient texture beds). The output is tuned for two jobs:

1. **Therapeutic / neuroplastic** — meditative sessions for grief, calm, focus, and inner journeying. Visuals + entrainment drones work together.
2. **Performance** — live DJ visuals and podcast/YouTube backdrops, output cleanly to OBS.

**Design principle:** *Calm by default, intense on demand.* Therapeutic presets bias toward slow, smooth, low-contrast motion; performance presets unlock chaos and visual density.

---

## 2. Two Pages, One Engine

| | **Stage — Desktop (`web.html`)** | **Stage — Mobile (`mobile.html`)** | **Output (`output.html`)** |
|---|---|---|---|
| Purpose | Desktop control surface + audio engine | Mobile control surface + audio engine | OBS video canvas |
| Renders visuals? | Yes (PREVIEW + PROGRAM canvases) | Yes (PREVIEW + PROGRAM canvases) | Yes (PROGRAM canvas only) |
| Generates audio? | **Yes** | **Yes** | **No** — video-only by design |
| OBS source | Window Capture (audio separately) | Window Capture (audio separately) | Window Capture (video only) |
| Key features | Full tab panel, dual monitors, GO button | Three-column/stacked layout, 5 tabs, sticky GO | Full-bleed canvas, param overlay, localStorage sync |

**Dual AudioContext rule (FROZEN):** `output.html` must never instantiate an AudioContext. Two identical drone signals on the OBS bus cause phase interference and destroy binaural L/R channel separation.

---

## 3. UX / UI Map

### 3.1 Desktop Stage (`web.html`) layout
```
┌─────────────────────────────────────────────────────────────────────┐
│  TOPBAR: [OLOGY logo] [grow] [❚❚ Running]                           │
├────────────────┬──────────────────────────────────┬─────────────────┤
│  LEFT SIDEBAR  │         CENTER MONITORS           │   RIGHT PANEL   │
│  (nav tabs)    │  ┌─────────────┐ ┌─────────────┐ │  (active tab)   │
│                │  │  PREVIEW    │ │  PROGRAM    │ │                 │
│  👁 Visuals ◀  │  │  (blue)     │ │  (red·LIVE) │ │  Sliders,       │
│  🔊 Audio      │  └─────────────┘ └─────────────┘ │  dropdowns,     │
│  📤 Output     │                                   │  controls       │
│  💾 Presets    │                                   │                 │
│  ❓ Help       │                                   │  [GO]           │
└────────────────┴──────────────────────────────────┴─────────────────┘
```

### 3.2 Mobile Stage (`mobile.html`) layout — phone portrait
```
┌───────────────────────────────────┐
│  TOPBAR: [logo] [OLOGY] [Running] │  ← fixed 44px
├───────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐   │
│  │  PREVIEW   │ │  PROGRAM   │   │  ← fixed ~38vh
│  │  (blue)    │ │ (red·LIVE) │   │
│  └────────────┘ └────────────┘   │
├───────────────────────────────────┤
│  👁 VISUALS │ 🔊 AUDIO │ 📤 │ 💾  │  ← tab strip
├───────────────────────────────────┤
│  Control panel (scrollable)       │  ← fills remaining height
│  Sliders, dropdowns, settings     │
│                                   │
│              [GO]                 │  ← sticky bottom bar
└───────────────────────────────────┘
```

### 3.3 Tab contents

**Visuals tab** — Theme selector (7 themes, default `Intergalactic Beings`), Intensity (0–1), Speed (0.1×–3×), Chaos (0–1), Rotation (0–1), Zoom, Segments (2–24), Bloom (0–1), Smooth (0–1, default 0.82), Symmetry type (Radial / Mirror / Kaleidoscope). All changes stage to PREVIEW; GO commits to PROGRAM.

**Audio tab** — Transport (Stop/Play), Drone preset dropdown (13 presets), Carrier Hz, Beat Hz, Entrainment mode (Binaural / Isochronic / Monaural), Brain-tickle (0–1), Slowness (0–1), Ambient Bed (6 beds), Drone↔Bed blend, Loop mode, Master volume. Audio changes are immediate — no GO required.

**Output tab** — AR selector (16:9 · 9:16 · 1:1 · 4:3, default 16:9). 9:16 fits canvas top-to-bottom in viewer; others fit side-to-side. Param overlay toggle (On/Off). Open output window button. Mobile pairing panel (web.html only).

**Presets tab** — Save / Load (into PREVIEW) / Favorite / Delete / Export JSON / Import JSON.

**Help tab / Help item** — Links to `ology_help.html`.

---

## 4. Themes & Drone Library

### 4.1 Visual Themes (7)

| # | id | Display Name | Default Drone |
|---|---|---|---|
| 0 | `intergalactic-beings` | **Intergalactic Beings** ★ | Theta — Intuition (6 Hz) |
| 1 | `supernovas` | Supernovas | Gamma — Insight (40 Hz) |
| 2 | `aurora-borealis` | Aurora Borealis | Schumann — Earth Pulse (7.83 Hz) |
| 3 | `psilocybin-dreams` | Psilocybin Dreams | Theta — Vision Quest (4.5 Hz) |
| 4 | `microcosmos` | Microcosmos | Alpha — Serenity (10 Hz) |
| 5 | `quantum-fields` | Quantum Fields | Beta — Focus (16 Hz) |
| 6 | `torus-universes` | Torus Universes | Delta — Deep Healing (2 Hz) |

★ Default load theme — both PREV.th and PROG.th = 0 on page load.

### 4.2 Drone Library (13)

**Brainwave entrainment (10):**

| Drone | Carrier | Beat | Band |
|---|---|---|---|
| Delta — Deep Healing | ~100 Hz | 2 Hz | Delta |
| Delta — Regeneration | ~100 Hz | 3 Hz | Delta |
| Theta — Dreamgate | ~120 Hz | 4 Hz | Theta |
| Theta — Vision Quest | ~120 Hz | 4.5 Hz | Theta |
| Theta — Intuition | ~136.1 Hz | 6 Hz | Theta |
| Schumann — Earth Pulse | ~136.1 Hz | 7.83 Hz | Theta/Alpha |
| Alpha — Calm Mind | ~210 Hz | 8.4 Hz | Alpha |
| Alpha — Serenity | ~200 Hz | 10 Hz | Alpha |
| Beta — Focus | ~250 Hz | 16 Hz | Beta |
| Gamma — Insight | ~300 Hz | 40 Hz | Gamma |

**Solfeggio / Spiritual carriers (3):**

| Drone | Carrier | Optional beat |
|---|---|---|
| Solfeggio — Transformation | 528 Hz | +7.83 Hz |
| Solfeggio — Awaken Intuition | 852 Hz | +6 Hz Theta |
| Solfeggio — Crown / Pineal | 963 Hz | +7.83 Hz |

### 4.3 Ambient Beds (6)
`womb` · `waterfall` · `jungle` · `forest` · `whales` · `ocean`

All beds are generative — synthesized entirely from oscillators and filters. No recordings.

---

## 5. Architecture

### 5.1 Module map

| Module | File | Status |
|---|---|---|
| M0 | `contracts.ts` v0.2.2 | ✅ Frozen |
| M1 | `m1_shaders.js` | ✅ Built · validated |
| M2 | `m2_audio.js` | ✅ Built · validated |
| M3 | `output.html` render loop | ✅ Built · validated |
| M4 | Inline UI in `web.html` | ✅ Built · live |
| M6 | Param overlay + toggle | ✅ Built · validated |
| M7 | `window.OlogyLink` WebRTC | ✅ Built · pending LAN test |
| M9 | Inline presets in `web.html` | ✅ Built · pending validation |
| Help | `ology_help.html` | ✅ Built · Beta v1.5.1 |
| Mobile | `mobile.html` | ✅ Built · Beta v1.5.1 |

`m4_ui.js` — confirmed not loaded at runtime. Remains in repo; cleanup/archive deferred to v2.

### 5.2 localStorage keys

| Key | Written by | Read by | Purpose |
|---|---|---|---|
| `ology_prog` | `web.html` / `mobile.html` | `output.html` | Live PROG state sync |
| `ology_frame` | `web.html` / `mobile.html` | `output.html` | Live AudioAnalysisFrame sync |
| `ology_overlay` | `web.html` / `mobile.html` | `output.html` | Param overlay on/off |
| `ology_presets_v1` | `web.html` | `web.html` | Preset library |
| `ology_strobe` | `web.html` / `mobile.html` | `output.html` | Safe Mode gate state ('1'=on, '0'=off; absent=on) |

### 5.3 Dual AudioContext rule (FROZEN)
`output.html` is permanently video-only. It must never instantiate an AudioContext. Two drone signals on the OBS bus cause phase interference and destroy binaural L/R separation. Audio is captured by OBS separately via Application/Desktop Audio Capture from the browser running `web.html` or `mobile.html`.

### 5.4 PREVIEW / PROGRAM model
All visual parameter changes (theme, speed, chaos, zoom, segments, bloom, smooth, intensity) stage into PREVIEW only. GO commits PREVIEW → PROGRAM and updates `output.html` via `ology_prog` localStorage. Audio parameters (drone, mode, carrier Hz, beat Hz, bed, blend, volume) take effect immediately — no GO required.

---

## 6. Canvas Viewer AR Behaviour

| AR selection | Viewer behaviour |
|---|---|
| 16:9 · 1:1 · 4:3 | Canvas constrained by width — fits side to side |
| 9:16 | Canvas constrained by height — fits top to bottom. Implemented via `display:block; height:calc(100% - 24px); width:auto; aspect-ratio:9/16` on `.mon-screen` when `data-portrait='1'` is set on `.monitors`. |

---

## 7. OBS Setup

**Video source:** Window Capture pointed at the `output.html` popup (open via Output tab → Open output window button).

**Audio source:** Application Audio Capture (Windows) or Desktop Audio (Mac) from the browser running `web.html` or `mobile.html`.

**Why separate sources:** Prevents dual-AudioContext phase interference. output.html is video-only by architectural lock.

**Param overlay:** Toggle On/Off in the Output tab. Displays theme, drone, carrier/beat Hz, mode, bed, tickle, slowness. Stays visible even when the Stage engine is paused — confirms the output canvas is live.

---

## 8. Anti-Bug Plan (v1.5)

- **Dual AudioContext:** `output.html` must never instantiate an AudioContext. Any PR touching output.html must grep for `new AudioContext` and `new webkitAudioContext` — zero hits required.
- **`m4_ui.js` not loaded:** `web.html` must not reference `m4_ui.js`. The `patchToM1State` monkey-patch (ll.738–770) and duplicate preset block remain contained by non-loading.
- **PREVIEW-only visual changes:** The `draw()` call for PROGRAM canvas in `web.html`/`mobile.html` passes `gateFrame` — `NULL_ANALYSIS` when Safe Mode is On, live `frame` when Off. PREVIEW always gets `NULL_ANALYSIS` (staging, never live). Do not pass live `frame` to PREVIEW.
- **Theme id consistency:** `intergalactic-beings` is the canonical id. Any rename attempt must update THEMES array `.id`, THEME_PRESETS `.themeId`, flatToVisualState fallback, and all HTML label references in one atomic edit.
- **localStorage sync:** `ology_prog` is written flat on every `saveProg()` call. `output.html` reads it on `storage` event and on init. Any new key added to PROG shape must be mirrored in `output.html`'s `toM1State` adapter.
- **Safe Mode gate (v1.5.1 — shipped):** `ology_strobe` key: '1'=on, '0'=off, absent=on (default). Never set `strobeGate` (5th arg to `OlogyShaders.draw`) to 0 — the shader outputs `vec4(0,0,0,1)` (full black). Gate exclusively via `NULL_ANALYSIS` frame substitution. `strobeGate` stays `1` always.
- **Isochronic / photosensitivity:** All public-facing materials must note that Isochronic mode can produce visual luminance pulses when audio reactivity is active. Warning is present in `ology_help.html` Audio Tab and Safety sections.
- **Safety:** strobe/flash limiter ON by default (Smooth ≥ 0.7 default); max-chaos cap; physician advisory for photosensitive users in help guide.
- **Browser target matrix:** Chrome/Edge/Opera (primary), OBS embedded browser, mobile Safari/Chrome. Intel Iris Plus 640: `preserveDrawingBuffer:true` causes pipeline stalls — use OffscreenCanvas with `preserveDrawingBuffer:false` + `transferToImageBitmap()` blit.

---

## 9. Connected Apps

| App / Service | Role in Ology v1.5.1 |
|---|---|
| **localStorage + JSON export/import** | Preset library (M9), session save/load, output sync |
| **GitHub Pages** | Deployment target (`aima-productions/ology-output`) |
| **OBS Studio** | Window Capture (video) + App Audio Capture (audio) |
| **Notion** | *(Optional)* preset/theme catalog |
| **Eraser** | *(Optional)* architecture & data-flow diagrams |

---

## 10. Phasing & Roadmap

### 10.1 v1.5.1 Beta — Current locked build
`web.html` (Desktop Stage) + `mobile.html` (Mobile Stage) + `output.html` (OBS canvas) + `ology_help.html` (Help Guide v1.5.1). Intergalactic Beings default theme. 9:16 portrait canvas viewer. Responsive help guide with mobile-safe layout. All 8 active modules built. Safe Mode gate + param overlay color fixes shipped.

**Remaining to exit beta:**
1. M9 validation pass (save/apply/GO/favorite/delete/export/import/migration/M7-wire)
2. M7 live LAN pairing test (laptop ↔ phone, real Wi-Fi)
3. Full OBS re-confirmation with presets in the loop
4. Path fix: `<script src="/m*.js">` → `./m*.js` in `web.html` and `output.html`
5. GitHub Pages deploy + smoke test

### 10.2 v1.6 — Bug Fixes + Validation
- Bug fixes from v1.5.1 beta test pass.
- M9 validation pass (save/apply/GO/favorite/delete/export/import/migration/M7-wire).
- M7 live LAN pairing test (laptop ↔ phone, real Wi-Fi).
- Cursor flicker investigation (desktop + output at full resolution).

### 10.3 v1.2 — Shader Expansion (post-beta patch)
New GLSL themes added to M1. Requires M0 contract patch (new `themeId` values + `THEME_PRESETS` entries).

### 10.4 v2 — Agent + Audio Input + Visual Expansion + 4K
- **Phase A:** Audio line-in (M10) — `getUserMedia`/desktop capture feeding existing AnalyserNode.
- **Phase B:** Ology Agent — Claude API sequences guided journeys via M7 ControlMessage transport. Voice narration (ElevenLabs) returns under Agent umbrella.
- **Phase C:** Visual effects expansion — Mandelbrot/Julia, blur passes, eye-morph shaders.
- **Phase D:** 4K delivery — Apple Silicon or dGPU target; adaptive resolution scaler.
- **Phase E:** Connectivity — TURN server, preset cloud sync, PWA manifest.
- **Phase F:** Backend auth — subscription tiers (free / premium / pro); output.html gated to premium/pro post-v2.

### 10.5 Therapeutic mission alignment (v2+)
Agent + voice phase enables AI-authored guided journeys (grief, calm, focus) with entrainment audio and matched visuals, deliverable as recorded sessions or live streams. Foundation/philanthropy distribution (free therapeutic session library) is a v2+ packaging decision.

---

## 11. v1.5.1 Beta Status

**Build status:**
- M0 (`contracts.ts` v0.2.2): ✅ Frozen
- M1 (`m1_shaders.js`): ✅ Built · validated (Intel Iris Plus confirmed)
- M2 (`m2_audio.js`): ✅ Built · validated (13 drones, 6 beds, 3 modes)
- M3 (`output.html` render loop): ✅ Built · validated in-browser and OBS
- M4 (inline UI in `web.html`): ✅ Built · live
- M6 (param overlay + toggle): ✅ Built · validated · responsive font · color fixes v1.5.1
- M7 (`window.OlogyLink`): ✅ Built · `load-preset` wired — pending LAN test
- M9 (inline presets in `web.html`): ✅ Built — pending validation pass
- Safe Mode gate: ✅ Built · v1.5.1 · web.html + mobile.html + output.html
- Mobile (`mobile.html`): ✅ Built · Beta v1.5.1
- Help (`ology_help.html`): ✅ Built · Beta v1.5.1

**Beta exit gates (in order):**
1. M9 validation pass
2. M7 live LAN pairing test
3. Full OBS re-confirmation with presets
4. Relative path fix (`/m*.js` → `./m*.js`)
5. GitHub Pages deploy + smoke test

**Post-beta queue:** v1.6 bug fixes → v1.2 shader expansion → v2.

---

## 12. Technical References (MLA)
- "Web Audio API." *MDN Web Docs*, Mozilla, developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API.
- "AnalyserNode." *MDN Web Docs*, Mozilla, developer.mozilla.org/en-US/docs/Web/API/AnalyserNode.
- "WebGL2RenderingContext." *MDN Web Docs*, Mozilla, developer.mozilla.org/en-US/docs/Web/API/WebGL2RenderingContext.
- "Window: localStorage Property." *MDN Web Docs*, Mozilla, developer.mozilla.org/en-US/docs/Web/API/Window/localStorage.
- "WebRTC API." *MDN Web Docs*, Mozilla, developer.mozilla.org/en-US/docs/Web/API/WebRTC_API.
- "RTCPeerConnection." *MDN Web Docs*, Mozilla, developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection.
- "RTCDataChannel." *MDN Web Docs*, Mozilla, developer.mozilla.org/en-US/docs/Web/API/RTCDataChannel.
- Ingendoh, Roben C., et al. "Binaural Beats to Entrain the Brain? A Systematic Review." *PMC*, US National Library of Medicine, pmc.ncbi.nlm.nih.gov.
- Pérez, Herta, et al. "Personalized Theta and Beta Binaural Beats for Brain Entrainment." *Frontiers in Psychology*, 2021, frontiersin.org/articles/10.3389/fpsyg.2021.764068/full.
- Taylor, Richard P. "Reduction of Physiological Stress Using Fractal Art and Architecture." *Leonardo*, vol. 39, no. 3, 2006, pp. 245–251. MIT Press.
- "What Is the Schumann Resonance Frequency: 7.83 Hz." *ScienceInsights*, scienceinsights.org/what-is-the-schumann-resonance-frequency-7-83-hz/.

> **Status (v1.5.1 Beta):** All 8 active v1 modules built (M0–M4, M6, M7, M9) + Help Guide v1.5.1 + mobile.html. Safe Mode gate shipped (NULL_ANALYSIS frame substitution, topbar indicator, localStorage). Param overlay color fixes. `web.html` is the canonical desktop Stage file. `Intergalactic Beings` is the default load theme. Remaining: M9 validation, M7 LAN test, OBS re-confirm, path fix, GitHub Pages deploy.
