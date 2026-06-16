/**
 * OLOGY — M0: contracts.ts
 * ============================================================================
 * The single source of truth for all shared types, IDs, and service interfaces.
 * Every other module (M1 shader, M2 audio, M3 canvas, M4 UI, M6 output,
 * M7 mobile, M9 shell) imports from here and NEVER invents its own shapes.
 *
 * Blueprint: v0.4 (voice removed; audio = drone generator only; OBS output is
 * video-only via output.html, audio captured separately from index.html). If a
 * contract must change, edit THIS file plus only the affected modules — never a
 * full rewrite.
 *
 * v0.2.1 — ambient bed ids revised: 'enchanted-forest'→'forest', 'asmr'→'ocean'
 * (M2 build alignment).
 * v0.2.2 — VisualState.smooth (0..1 edge/blur) added to match M1's runtime
 * consumption (M1 reads visual.smooth → u_smooth). defaultVisualState.smooth=0.82.
 * Patch-level per project convention: non-breaking field add (M1 already
 * fallbacks to 0.82), consistent with 0.2.1's patch-level contract alignment.
 *
 * FROZEN once approved. Version stamp below gates compatibility.
 * ============================================================================
 */

export const CONTRACTS_VERSION = '0.2.2' as const;

/* ===========================================================================
 * SECTION 1 — BRAINWAVE BANDS & ENTRAINMENT
 * Standard EEG bands: delta 0.5–4, theta 4–8, alpha 8–13, beta 13–30, gamma >30.
 * A binaural beat is the perceived difference of two tones (one per ear); it
 * requires headphones. On speakers, use isochronic (pulsed single tone) or
 * monaural. Effects are experiential/meditative, not medical claims.
 * =========================================================================== */

export type BrainwaveBand = 'delta' | 'theta' | 'alpha' | 'beta' | 'gamma';

/** Inclusive lower bound, exclusive upper bound (Hz). Frozen reference ranges. */
export const BRAINWAVE_BANDS: Readonly<Record<BrainwaveBand, { minHz: number; maxHz: number }>> = {
  delta: { minHz: 0.5, maxHz: 4 },
  theta: { minHz: 4, maxHz: 8 },
  alpha: { minHz: 8, maxHz: 13 },
  beta: { minHz: 13, maxHz: 30 },
  gamma: { minHz: 30, maxHz: 100 },
} as const;

/** How the beat is rendered. Binaural REQUIRES headphones to take effect. */
export type EntrainmentMode = 'binaural' | 'isochronic' | 'monaural';

/** Library grouping for UI and for the optional "About frequencies" info link. */
export type DroneCategory = 'brainwave' | 'solfeggio';

/**
 * A single drone definition. `carrierHz` is the audible base tone; `beatHz` is
 * the entrainment target (the perceived beat for binaural/isochronic). For
 * pure-tone Solfeggio drones, `beatHz` may be 0 (no beat) or an optional layer.
 */
export interface DroneSpec {
  id: DroneId;
  name: string;
  category: DroneCategory;
  carrierHz: number;
  beatHz: number;
  /** Auto-classified band for `beatHz`; null when beatHz is 0 (no beat). */
  band: BrainwaveBand | null;
  /** Default render mode; user can override in AudioState. */
  defaultMode: EntrainmentMode;
  /** Plain-language, non-medical description shown in the UI. */
  attributedEffect: string;
}

export type DroneId =
  | 'delta-deep-healing'
  | 'delta-regeneration'
  | 'theta-dreamgate'
  | 'theta-vision-quest'
  | 'theta-intuition'
  | 'schumann-earth-pulse'
  | 'alpha-calm-mind'
  | 'alpha-serenity'
  | 'beta-focus'
  | 'gamma-insight'
  | 'solfeggio-transformation'
  | 'solfeggio-awaken-intuition'
  | 'solfeggio-crown-pineal';

/** Canonical, frozen drone library. M2 plays these; M4 lists them; M9 references by id. */
export const DRONE_LIBRARY: readonly DroneSpec[] = [
  { id: 'delta-deep-healing',        name: 'Delta — Deep Healing',        category: 'brainwave', carrierHz: 100,   beatHz: 2,    band: 'delta', defaultMode: 'binaural',   attributedEffect: 'Deep dreamless sleep, physical recovery' },
  { id: 'delta-regeneration',        name: 'Delta — Regeneration',        category: 'brainwave', carrierHz: 100,   beatHz: 3,    band: 'delta', defaultMode: 'binaural',   attributedEffect: 'Restorative rest' },
  { id: 'theta-dreamgate',           name: 'Theta — Dreamgate',           category: 'brainwave', carrierHz: 120,   beatHz: 4,    band: 'theta', defaultMode: 'binaural',   attributedEffect: 'Deep meditation, REM-like imagery' },
  { id: 'theta-vision-quest',        name: 'Theta — Vision Quest',        category: 'brainwave', carrierHz: 120,   beatHz: 4.5,  band: 'theta', defaultMode: 'binaural',   attributedEffect: 'Shamanic / visualization states' },
  { id: 'theta-intuition',           name: 'Theta — Intuition',           category: 'brainwave', carrierHz: 136.1, beatHz: 6,    band: 'theta', defaultMode: 'binaural',   attributedEffect: 'Intuition, inner journeying' },
  { id: 'schumann-earth-pulse',      name: 'Schumann — Earth Pulse',      category: 'brainwave', carrierHz: 136.1, beatHz: 7.83, band: 'theta', defaultMode: 'isochronic', attributedEffect: 'Grounding, calm, sense of oneness' },
  { id: 'alpha-calm-mind',           name: 'Alpha — Calm Mind',           category: 'brainwave', carrierHz: 210,   beatHz: 8.4,  band: 'alpha', defaultMode: 'binaural',   attributedEffect: 'Pre-sleep, stress release' },
  { id: 'alpha-serenity',            name: 'Alpha — Serenity',            category: 'brainwave', carrierHz: 200,   beatHz: 10,   band: 'alpha', defaultMode: 'binaural',   attributedEffect: 'Relaxed focus, flow' },
  { id: 'beta-focus',                name: 'Beta — Focus',                category: 'brainwave', carrierHz: 250,   beatHz: 16,   band: 'beta',  defaultMode: 'isochronic', attributedEffect: 'Alertness, concentration' },
  { id: 'gamma-insight',             name: 'Gamma — Insight',             category: 'brainwave', carrierHz: 300,   beatHz: 40,   band: 'gamma', defaultMode: 'isochronic', attributedEffect: 'Peak cognition, heightened perception' },
  { id: 'solfeggio-transformation',  name: 'Solfeggio — Transformation',  category: 'solfeggio', carrierHz: 528,   beatHz: 7.83, band: 'theta', defaultMode: 'isochronic', attributedEffect: 'Tradition-attributed "repair/transformation"' },
  { id: 'solfeggio-awaken-intuition',name: 'Solfeggio — Awaken Intuition',category: 'solfeggio', carrierHz: 852,   beatHz: 6,    band: 'theta', defaultMode: 'isochronic', attributedEffect: 'Tradition-attributed "inner sight"' },
  { id: 'solfeggio-crown-pineal',    name: 'Solfeggio — Crown / Pineal',  category: 'solfeggio', carrierHz: 963,   beatHz: 7.83, band: 'theta', defaultMode: 'isochronic', attributedEffect: 'Tradition-attributed "higher connection"' },
] as const;

/** Classify any beat frequency into its band, or null if 0 (no beat). */
export function bandForBeat(beatHz: number): BrainwaveBand | null {
  if (beatHz <= 0) return null;
  for (const band of Object.keys(BRAINWAVE_BANDS) as BrainwaveBand[]) {
    const { minHz, maxHz } = BRAINWAVE_BANDS[band];
    if (beatHz >= minHz && beatHz < maxHz) return band;
  }
  return beatHz >= BRAINWAVE_BANDS.gamma.minHz ? 'gamma' : null;
}

/* ===========================================================================
 * SECTION 2 — AMBIENT TEXTURE BEDS  (built-in generative layers; no uploads)
 * =========================================================================== */

export type AmbientBedId =
  | 'none'
  | 'womb'
  | 'waterfall'
  | 'jungle'
  | 'forest'
  | 'whales'
  | 'ocean';

export const AMBIENT_BEDS: readonly { id: AmbientBedId; name: string }[] = [
  { id: 'none',             name: 'None' },
  { id: 'womb',             name: 'Womb' },
  { id: 'waterfall',        name: 'Waterfall' },
  { id: 'jungle',           name: 'Jungle' },
  { id: 'forest',           name: 'Forest' },
  { id: 'whales',           name: 'Whales' },
  { id: 'ocean',            name: 'Ocean' },
] as const;

export type LoopBehavior = 'crossfade' | 'evolving' | 'one-shot';
export type MusicalKey = 'C' | 'C#' | 'D' | 'D#' | 'E' | 'F' | 'F#' | 'G' | 'G#' | 'A' | 'A#' | 'B';
export type MusicalScale = 'major' | 'minor' | 'pentatonic' | 'dorian' | 'phrygian' | 'lydian';

/* ===========================================================================
 * SECTION 3 — REACTIVITY  (drone FFT → visual params)
 * M2 produces an AudioAnalysisFrame each render tick; M3 reads it; the
 * ReactivityRoute matrix decides which band drives which visual parameter.
 * =========================================================================== */

export type FrequencyBand = 'sub' | 'low' | 'mid' | 'high';
export const FREQUENCY_BANDS: readonly FrequencyBand[] = ['sub', 'low', 'mid', 'high'] as const;

/** Visual parameters that audio reactivity is allowed to modulate. */
export type ReactiveParam =
  | 'speed'
  | 'chaos'
  | 'fractalDepth'
  | 'zoom'
  | 'rotation'
  | 'bloom'
  | 'colorShift';

/** One routing entry: a normalized [0..1] amount that `band` adds to `param`. */
export interface ReactivityRoute {
  band: FrequencyBand;
  param: ReactiveParam;
  amount: number; // 0..1
}

/** Live per-frame analysis emitted by M2 and consumed by M3. All values 0..1. */
export interface AudioAnalysisFrame {
  /** Normalized energy per frequency band. */
  bands: Readonly<Record<FrequencyBand, number>>;
  /** Overall RMS loudness, 0..1. */
  level: number;
  /** Monotonic timestamp (performance.now() ms) of this frame. */
  t: number;
}

/* ===========================================================================
 * SECTION 4 — AUDIO STATE  (the complete, serializable audio config)
 * =========================================================================== */

export interface AudioState {
  /** Selected drone from DRONE_LIBRARY. */
  droneId: DroneId;
  /** User overrides; if null, fall back to the DroneSpec defaults. */
  carrierHz: number | null;
  beatHz: number | null;
  mode: EntrainmentMode;

  /** 0..1 amount of high-frequency "brain-tickle" accents over the drone. */
  brainTickleAmount: number;
  /** 0..1 — higher = slower, more glacial movement. */
  slowness: number;
  key: MusicalKey;
  scale: MusicalScale;

  /** Ambient texture bed layered under the drone. */
  ambientBed: AmbientBedId;
  /** 0..1 blend of the ambient bed against the drone. */
  ambientBlend: number;

  loop: LoopBehavior;

  /** Reactivity matrix (which band drives which visual param, and how much). */
  routes: ReactivityRoute[];

  /** 0..1 master output level. */
  masterLevel: number;
  /** Transport. Audio is suspended until the first user gesture (autoplay policy). */
  isPlaying: boolean;
}

/* ===========================================================================
 * SECTION 5 — VISUAL STATE  (themes, kaleidoscope, palette, resolution)
 * =========================================================================== */

export type ThemeId =
  | 'intergalactic-beings'
  | 'supernovas'
  | 'aurora-borealis'
  | 'psilocybin-dreams'
  | 'microcosmos'
  | 'quantum-fields'
  | 'torus-universes';

export interface ColorStop {
  /** Position along the gradient, 0..1. */
  pos: number;
  /** Hex color, e.g. "#7A5CFF". */
  hex: string;
}

export interface Palette {
  /** Exactly three stops for the custom 3-stop gradient. */
  stops: [ColorStop, ColorStop, ColorStop];
}

/** Long-edge baseline (landscape) / width (vertical). 4K is v2; 1080 is v1 default. */
export type ResolutionTier = '720' | '1080' | '1440' | '4K';

export interface VisualState {
  themeId: ThemeId;

  speed: number;        // 0..2  (1 = nominal)
  chaos: number;        // 0..1
  fractalDepth: number; // 1..12 iterations
  zoom: number;         // 0..1  (0 = far, 1 = near)
  rotation: number;     // radians/sec base spin
  /** Kaleidoscope segments, 2..24. */
  symmetry: number;
  bloom: number;        // 0..1 glow amount

  /**
   * Edge character: 0 = crisp, hard-edged color zones; 1 = soft, blurred,
   * bleeding color. Read by the M1 shader (drives u_smooth edge/blur uniforms).
   * Added in contracts 0.2.2 to match M1's runtime consumption.
   */
  smooth: number;       // 0..1

  /** Photosensitivity guard. Default ON; caps flash rate at MAX_SAFE_FLASH_HZ. */
  strobeLimiterOn: boolean;

  palette: Palette;
  /** 0..1 — how strongly audio reactivity shifts color. */
  reactivityToColorAmount: number;

  /**
   * Optional user-supplied reference image (data URL or object URL) that seeds
   * palette + texture. No AI generation — user upload / phone capture only.
   */
  referenceImage: string | null;

  resolution: ResolutionTier;
  /** Adaptive scaler auto-drops resolution to hold target FPS. Built into M3. */
  adaptive: boolean;
}

/* ===========================================================================
 * SECTION 6 — THEME PRESETS  (theme → defaults), canonical & frozen
 * =========================================================================== */

export interface ThemePreset {
  themeId: ThemeId;
  name: string;
  /** Default drone paired with this theme. */
  defaultDroneId: DroneId;
  /** Partial visual defaults applied when the theme is selected. */
  visualDefaults: Partial<VisualState>;
}

export const THEME_PRESETS: readonly ThemePreset[] = [
  { themeId: 'intergalactic-beings', name: 'Intergalactic Beings', defaultDroneId: 'theta-intuition',      visualDefaults: { symmetry: 8,  speed: 0.6, chaos: 0.3 } },
  { themeId: 'supernovas',           name: 'Supernovas',           defaultDroneId: 'gamma-insight',        visualDefaults: { symmetry: 12, speed: 1.1, chaos: 0.6 } },
  { themeId: 'aurora-borealis',       name: 'Aurora Borealis',      defaultDroneId: 'schumann-earth-pulse', visualDefaults: { symmetry: 6,  speed: 0.9, zoom: 0.8 } },
  { themeId: 'psilocybin-dreams',    name: 'Psilocybin Dreams',    defaultDroneId: 'theta-vision-quest',   visualDefaults: { symmetry: 10, speed: 0.7, chaos: 0.7 } },
  { themeId: 'microcosmos',          name: 'Microcosmos',          defaultDroneId: 'alpha-serenity',       visualDefaults: { symmetry: 16, speed: 0.5, zoom: 0.9 } },
  { themeId: 'quantum-fields',       name: 'Quantum Fields',       defaultDroneId: 'beta-focus',           visualDefaults: { symmetry: 4,  speed: 1.0, chaos: 0.5 } },
  { themeId: 'torus-universes',      name: 'Torus Universes',      defaultDroneId: 'delta-deep-healing',   visualDefaults: { symmetry: 8,  speed: 0.4, chaos: 0.2 } },
] as const;

/* ===========================================================================
 * SECTION 7 — SESSION / PRESET  (full serializable session = visual + audio)
 * =========================================================================== */

export interface SessionPreset {
  id: string;
  name: string;
  contractsVersion: typeof CONTRACTS_VERSION;
  visual: VisualState;
  audio: AudioState;
  createdAt: string; // ISO 8601
  favorite?: boolean;
}

/* ===========================================================================
 * SECTION 8 — OUTPUT  (OBS Browser Source; output only — no WebSocket control)
 * Mirrors the real output.html URL params: ar, res, fps, obs.
 * =========================================================================== */

export type AspectRatio = '16:9' | '9:16' | '1:1' | '4:3';
export type OutputFps = 24 | 30 | 60; // metadata label only; real FPS set in OBS

export interface OutputConfig {
  aspect: AspectRatio;
  resolution: ResolutionTier;
  fps: OutputFps;
  /** Hide on-screen dimension readout (the &obs=1 flag). */
  hideReadout: boolean;
}

/** Build the OBS Browser Source URL from an OutputConfig. */
export function buildOutputUrl(base: string, cfg: OutputConfig): string {
  const ar = encodeURIComponent(cfg.aspect);
  const res = cfg.resolution === '4K' ? '2160' : cfg.resolution;
  const obs = cfg.hideReadout ? '&obs=1' : '';
  return `${base}/output.html?ar=${ar}&res=${res}&fps=${cfg.fps}${obs}`;
}

/** Full program state pushed to the output view (matches window.__ology_setProgram). */
export interface ProgramState {
  visual: VisualState;
  audio: AudioState;
}

/* ===========================================================================
 * SECTION 9 — CONTROL MESSAGES  (WebRTC DataChannel: phone ↔ stage, and
 * controller → output sync). Discriminated union — exhaustive by `type`.
 * =========================================================================== */

export type ControlMessage =
  | { type: 'hello'; room: string; role: 'stage' | 'controller' }
  | { type: 'welcome'; room: string }
  | { type: 'ping'; t: number }
  | { type: 'pong'; t: number }
  | { type: 'set-theme'; themeId: ThemeId }
  | { type: 'set-visual'; patch: Partial<VisualState> }
  | { type: 'set-audio'; patch: Partial<AudioState> }
  | { type: 'set-drone'; droneId: DroneId }
  | { type: 'transport'; play: boolean }
  | { type: 'load-preset'; presetId: string }
  | { type: 'program'; state: ProgramState };

/* ===========================================================================
 * SECTION 10 — SERVICE INTERFACES  (mock-first; real keys wired at integration)
 * v0.2: Google Drive preset store ONLY. No Claude / ElevenLabs / Higgsfield.
 * =========================================================================== */

export interface PresetStore {
  list(): Promise<SessionPreset[]>;
  load(id: string): Promise<SessionPreset | null>;
  save(preset: SessionPreset): Promise<void>;
  remove(id: string): Promise<void>;
}

/* ===========================================================================
 * SECTION 11 — SAFETY CONSTANTS  (photosensitivity; always enforced in M1/M3)
 * =========================================================================== */

/** Hard cap on full-frame flash rate when the strobe limiter is ON. */
export const MAX_SAFE_FLASH_HZ = 3;
/** Upper bound on chaos a preset/agent may request. */
export const MAX_CHAOS = 1.0;
/** Default session length guard (minutes); 0 = no auto-stop. */
export const DEFAULT_SESSION_LIMIT_MIN = 0;

/* ===========================================================================
 * SECTION 12 — DEFAULT FACTORIES  (so every module starts from identical state)
 * =========================================================================== */

export function defaultPalette(): Palette {
  return {
    stops: [
      { pos: 0,   hex: '#7A5CFF' },
      { pos: 0.5, hex: '#16C2C2' },
      { pos: 1,   hex: '#FFC247' },
    ],
  };
}

export function defaultVisualState(): VisualState {
  return {
    themeId: 'intergalactic-beings',
    speed: 0.6,
    chaos: 0.3,
    fractalDepth: 6,
    zoom: 0.4,
    rotation: 0.05,
    symmetry: 8,
    bloom: 0.4,
    smooth: 0.82,
    strobeLimiterOn: true,
    palette: defaultPalette(),
    reactivityToColorAmount: 0.4,
    referenceImage: null,
    resolution: '1080',
    adaptive: true,
  };
}

export function defaultAudioState(): AudioState {
  return {
    droneId: 'theta-intuition',
    carrierHz: null,
    beatHz: null,
    mode: 'binaural',
    brainTickleAmount: 0.2,
    slowness: 0.6,
    key: 'C',
    scale: 'minor',
    ambientBed: 'womb',
    ambientBlend: 0.3,
    loop: 'evolving',
    routes: [
      { band: 'sub',  param: 'bloom',      amount: 0.5 },
      { band: 'low',  param: 'zoom',       amount: 0.3 },
      { band: 'mid',  param: 'chaos',      amount: 0.4 },
      { band: 'high', param: 'colorShift', amount: 0.5 },
    ],
    masterLevel: 0.8,
    isPlaying: false,
  };
}

export function defaultProgramState(): ProgramState {
  return { visual: defaultVisualState(), audio: defaultAudioState() };
}

/** Resolve a drone's effective carrier/beat/band given user overrides. */
export function resolveDrone(state: AudioState): { carrierHz: number; beatHz: number; band: BrainwaveBand | null } {
  const spec = DRONE_LIBRARY.find((d) => d.id === state.droneId) ?? DRONE_LIBRARY[0];
  const carrierHz = state.carrierHz ?? spec.carrierHz;
  const beatHz = state.beatHz ?? spec.beatHz;
  return { carrierHz, beatHz, band: bandForBeat(beatHz) };
}
