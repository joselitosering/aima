# Ology — Audio-Reactive Kaleidoscope · Beta v1.5.1

**Endless audio-reactive kaleidoscope for meditation, neuroplasticity, and live performance.**  
Built by Joselito Sering · Published under AIMA Productions · aima.productions

---

## Quick Start

```bash
npm install    # one time
npm start      # serves on http://localhost:8080
```

| Page | URL | Purpose |
|---|---|---|
| Desktop Stage | `http://localhost:8080/web.html` | Full control panel + audio engine |
| Mobile Stage | `http://localhost:8080/mobile.html` | Mobile control panel + audio engine |
| OBS Canvas | `http://localhost:8080/output.html` | Video-only program canvas for OBS |
| Help Guide | `http://localhost:8080/ology_help.html` | Full user documentation |

Change the port: `PORT=9000 npm start`

---

## What Ology Is

Ology generates an infinite, never-repeating fractal visual driven by an internally synthesized audio engine. No sample files, no installation, no cloud services. Open the URL and the experience begins.

Three use contexts:
- **Therapeutic sessions** — grief processing, anxiety relief, focus recovery, inner journeying. Visuals and entrainment drones are paired by emotional and neurological intent.
- **Neuroplasticity work** — structured sessions using binaural, isochronic, and monaural entrainment targeting specific EEG frequency bands.
- **Live performance** — DJ visuals, podcast backdrops, OBS broadcast content. The two-page architecture keeps audio and video cleanly separated for the OBS bus.

---

## File Structure

```
ology-output/
├── web.html             # Desktop Stage — full control panel + audio engine
├── mobile.html          # Mobile Stage — full control panel + audio engine (phone/tablet)
├── output.html          # OBS video canvas — video-only, no AudioContext
├── ology_help.html      # Help Guide — Beta v1.5, responsive, 14 sections
├── m1_shaders.js        # M1 — GLSL shader library (7 themes, kaleidoscope engine)
├── m2_audio.js          # M2 — Audio engine (13 drones, 6 beds, 3 entrainment modes)
├── contracts.ts         # M0 — Shared TypeScript types, drone library, theme presets v0.2.2
├── server.js            # Express static server
├── package.json
└── README.md
```

---

## Module Status

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
| Mobile | `mobile.html` | ✅ Built · Beta v1.5.1 |
| Help | `ology_help.html` | ✅ Built · Beta v1.5.1 |

`m4_ui.js` — remains in repo, not loaded at runtime. Cleanup deferred to v2.

---

## OBS Setup

Ology sends video and audio to OBS as two **separate sources**. This is required — a single Browser Source would create two drone signals causing phase interference and destroying binaural stereo.

### Step 1 — Open the output window
1. In `web.html`, open the **Output** tab in the right panel.
2. Select your aspect ratio (default: 16:9).
3. Click **Open output window** — a popup opens and requests fullscreen. Allow it.

### Step 2 — Add video source in OBS
1. Sources → **+** → **Window Capture**
2. Select the Ology output window (e.g. `Opera - Ology`)
3. Check **Client Area** to remove the OS border

### Step 3 — Add audio source in OBS
1. Sources → **+** → **Application Audio Capture** (Windows) or **Desktop Audio** (Mac)
2. Set to capture from the browser running `web.html` or `mobile.html`
3. Verify drone waveform appears in the OBS audio mixer when playing

### Aspect ratios
| Selection | Canvas viewer | output.html |
|---|---|---|
| 16:9 · 1:1 · 4:3 | Fits side to side | Landscape / square canvas |
| 9:16 | Fits top to bottom | Portrait canvas |

---

## Audio Engine

All audio is generated algorithmically — no sample files, no recordings.

**13 drone presets** across Delta (1–3 Hz), Theta (4–7.83 Hz), Alpha (8–10 Hz), Beta (16 Hz), Gamma (40 Hz), and Solfeggio carriers (528 / 852 / 963 Hz).

**3 entrainment modes:**
- **Binaural** — requires stereo headphones; different frequency each ear; brain perceives the difference
- **Isochronic** — single tone pulsed on/off at beat rate; works on speakers; safe for OBS/broadcast
- **Monaural** — two tones mixed in one channel; physical amplitude modulation; works on speakers

**6 ambient beds:** womb · waterfall · jungle · forest · whales · ocean — all synthesized from oscillators and filters.

**Audio reactivity:** Live FFT analysis routes four frequency bands to visual parameters — sub→bloom, low→zoom, mid→chaos, high→colour shift.

> ⚠️ **Isochronic mode:** Pulses audio on/off at 1–40 Hz. With audio reactivity active this can produce corresponding visual luminance pulses. Users with photosensitive epilepsy should use Binaural or Monaural mode instead.

---

## PREVIEW / PROGRAM Model

Ology uses a broadcast-style two-bus model:

- **PREVIEW** (blue border) — staging area. All slider and theme changes go here first. Safe to audition without interrupting the live output.
- **PROGRAM** (red border · LIVE) — the live output, visible to OBS and the audience.
- **GO** — commits all current PREVIEW settings to PROGRAM instantly.

Audio changes (drone, mode, bed, volume) take effect immediately without GO.

---

## Presets

A preset captures the complete session state — all visual parameters, all audio parameters, theme, drone, entrainment mode, bed blend, and loop mode — in a single named JSON object stored in `localStorage`.

- **Load** always stages into PREVIEW, never directly into PROGRAM. Press GO to go live.
- **Export JSON** / **Import JSON** for backup and sharing.

---

## Safety

- **Smooth ≥ 0.7 recommended** for therapeutic contexts — limits rapid luminance changes.
- **Binaural mode** requires stereo headphones. On speakers the psychoacoustic effect is not delivered.
- **Isochronic mode** can produce visual luminance pulses via audio reactivity. Warn photosensitive participants.
- Do not use during driving, operating machinery, or any situation requiring active attention.
- Not a medical device. Frequency-to-state mappings are experiential meditation tools, not clinical protocols.

---

## Development

```bash
npm install        # express + typescript
npm start          # http://localhost:8080
```

TypeScript contracts validation (no build output needed for browser):
```bash
npx tsc --noEmit contracts.ts
```

**Runtime:** Vanilla JS, no bundler, no ES modules. WebGL2 (mediump fragment precision for Intel Iris Plus). Web Audio API.

**Browser targets:** Chrome / Edge / Opera (primary), OBS embedded browser, mobile Safari / Chrome.

**Intel Iris Plus note:** `preserveDrawingBuffer:true` causes GPU pipeline stalls. M1 uses OffscreenCanvas with `preserveDrawingBuffer:false` + `transferToImageBitmap()` blit.

---

## Roadmap

| Version | Scope |
|---|---|
| **v1.5** | `web.html` + `mobile.html` + `output.html` + help guide. Default theme: Intergalactic Beings. 9:16 portrait viewer. |
| **v1.5.1** *(current)* | Safe Mode toggle (audio reactivity gate via NULL_ANALYSIS frame). Engine light indicator in topbar. Param overlay color fixes. |
| **v1.6** | Bug fixes from v1.5.1 test pass. Cursor flicker investigation. |
| **v1.2** | Shader expansion — new GLSL themes added to M1. |
| **v2** | Agent (Claude API) + audio line-in + visual expansion + 4K + backend auth + subscription tiers. |
| **v3** | Print products (Odorama / prayer kits). |

---

## References

- Blueprint: `Ology___App_Blueprint___White_Paper_v1_5.md`
- Design Decisions: `DESIGN_DECISIONS.md`
- Help Guide: `ology_help.html`
- Web Audio API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API
- WebGL2: https://developer.mozilla.org/en-US/docs/Web/API/WebGL2RenderingContext
- WebRTC: https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API
- OBS Window Capture: https://obsproject.com/wiki/Sources-Guide
