# OLOGY PROJECT — Design Decisions Log

**Purpose:** Frozen design decisions. Prevent re-debates across sessions.  
**Format:** Tab-separated, one decision per line.  
**Rule:** Any new decision requires Joe's approval before a build session starts.

---

| Timestamp | Module | Decision | Rationale | Approved By | Status |
|-----------|--------|----------|-----------|-------------|--------|
| 2026-06-09 | M0 | TypeScript, strict ES2020, full type contracts | Type safety, contract-first architecture, no runtime surprises | Joe | FROZEN |
| 2026-06-09 | M1 | GLSL fragment shader, domain folding kaleidoscope per theme | Psychedelic visual requirement, GPU efficiency, theme diversity | Joe | FROZEN ✓ validated |
| 2026-06-09 | M1 | No Tone.js in M1 (shaders only); audio synthesis in M2 | Separation of concerns; M1 is render-only | Joe | FROZEN ✓ validated |
| 2026-06-09 | v1 | No Voice/TTS layer; no audio upload; no line-in in v1 | Scope containment; features move to v2 | Joe | FROZEN |
| 2026-06-09 | v1 | Audio reactivity driven ONLY by internal drone generator (M2) | Simplicity, determinism, repeatable sessions | Joe | FROZEN |
| 2026-06-09 | v1 | OBS integration: Window/Display Capture (video) + App Audio Capture (audio) — NOT Browser Source | Dual AudioContext rule: output.html must never instantiate AudioContext; Browser Source URL approach removed in v1.3 | Joe | FROZEN |
| 2026-06-09 | v1 | 1080p target, 4K deferred to v2 | Performance baseline, GPU budget | Joe | FROZEN |
| 2026-06-09 | v1 | Presets: localStorage + JSON export/import, no Google Drive in v1 | Simplify v1, local-first | Joe | FROZEN |
| 2026-06-10 | M0 | AmbientBedId: replace enchanted-forest+asmr with forest+ocean; bump CONTRACTS_VERSION to 0.2.1 | v0.3 scope alignment; generative recipes for forest and ocean are cleaner | Joe | FROZEN |
| 2026-06-10 | M2 | Web Audio API (no Tone.js) | Native, simpler, faster, no CDN dependency risk | Joe | FROZEN ✓ validated |
| 2026-06-10 | M2 | All 13 drones from DRONE_LIBRARY (no retune) | Contract fidelity | Joe | FROZEN ✓ validated |
| 2026-06-10 | M2 | 3 entrainment modes (binaural/isochronic/monaural), all 6 ambient beds | Blueprint §4.2 spec | Joe | FROZEN ✓ validated |
| 2026-06-10 | M2 | Analyser on master bus (both drone + bed) | Unified audio reactivity | Joe | FROZEN ✓ validated |
| 2026-06-10 | M3 | output.html is permanently video-only — no AudioContext ever | Dual drone signals on OBS bus cause phase interference and destroy binaural L/R separation | Joe | FROZEN |
| 2026-06-10 | v1 | index.html renamed to web.html | Clearer naming — web.html is the desktop Stage; output.html is the OBS canvas; mobile.html is the mobile Stage | Joe | FROZEN |
| 2026-06-10 | mobile | mobile.html introduced as dedicated mobile Stage | Full audio + visual engine on mobile; three-column layout desktop/tablet; stacked layout phone (≤430px); 5 tabs; sticky GO bar | Joe | FROZEN |
| 2026-06-10 | themes | Theme id and display name: `intergalactic-beings` / `Intergalactic Beings` (canonical) | A session rename to `Interdimensional Beings` was trialled and reverted — `intergalactic-beings` is the canonical id in contracts, THEMES array, THEME_PRESETS, and all HTML labels | Joe | FROZEN |
| 2026-06-10 | themes | Default load theme: PREV.th = 0, PROG.th = 0 = Intergalactic Beings on every page load | Consistent starting state for both preview and program monitors; avoids operator confusion on cold start | Joe | FROZEN |
| 2026-06-10 | M3/M4 | 9:16 portrait canvas viewer: `display:block; height:calc(100% - 24px); width:auto; aspect-ratio:9/16` on `.mon-screen` when `data-portrait='1'` | `flex:1` competed with `aspect-ratio` and won, ignoring the AR constraint. `display:block` + explicit calc height gives the browser a clean anchor to derive width from | Joe | FROZEN |
| 2026-06-10 | v1.6 | Strobe gate (Option C) parked to v1.6 | Audio broke on mobile and output.html reactivity did not correctly sync during v1.5 implementation; needs isolated clean build with full test across all three files | Joe | FROZEN — implement in v1.6 |
| 2026-06-10 | v1.6 | `ology_strobe` localStorage key reserved | Key name locked for v1.6 strobe gate; must not be written or read in v1.5 code | Joe | FROZEN |
| 2026-06-10 | safety | Isochronic mode flash-sensitivity warning required in all public-facing materials | Isochronic pulses audio on/off at beat frequency (1–40 Hz); with audio reactivity active this can produce visual luminance pulses at same rate; photosensitive users must be warned | Joe | FROZEN |

---

## Legend
- **FROZEN:** Decision locked in. Do not re-propose unless explicitly approved for change.
- **PENDING:** Awaiting module build session for finalization.
- **✓ validated:** Module built and passed validation.

## Process for Adding New Decisions
1. Before a build session, identify any NEW design decisions needed.
2. Propose in this log with "PENDING" status.
3. Get Joe's approval (set Status to approved date).
4. Only then start the build session.
5. After module validation, mark "✓ validated".
