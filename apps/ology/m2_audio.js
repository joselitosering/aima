/* ============================================================================
 * OLOGY — M2: m2_audio.js  (audio engine)
 * ----------------------------------------------------------------------------
 * Self-contained vanilla-JS IIFE. Window export: window.OlogyAudio.
 * Web Audio API only; no third-party audio library. Online AudioContext; graph reaches
 * AC.destination so OBS Browser Source can capture page audio.
 *
 * Built against M0 contracts.ts v0.2.1:
 *   - 13 DroneIds, exact carrier/beat Hz (DRONE_LIBRARY below)
 *   - 7 AmbientBedIds: none, womb, waterfall, jungle, forest, whales, ocean
 *   - 3 EntrainmentModes: binaural, isochronic, monaural
 *   - M2 receives the AudioState by reference and mutates it in place.
 *
 * Signal graph:
 *   [droneVoices] -+
 *   [bedSource ]  | -> mixBus -> masterGain -> analyser -> AC.destination
 *   [brainTickle] -+
 * Exactly one AnalyserNode (fftSize 2048, smoothing 0.8) on the master bus.
 * ========================================================================== */
(function () {
  'use strict';

  var CONTRACTS_VERSION = '0.2.1';

  /* --- Frozen drone library (carrier/beat Hz mirror M0; do NOT retune) ----- */
  var DRONE_LIBRARY = {
    'delta-deep-healing':         { carrierHz: 100,   beatHz: 2,    defaultMode: 'binaural'   },
    'delta-regeneration':         { carrierHz: 100,   beatHz: 3,    defaultMode: 'binaural'   },
    'theta-dreamgate':            { carrierHz: 120,   beatHz: 4,    defaultMode: 'binaural'   },
    'theta-vision-quest':         { carrierHz: 120,   beatHz: 4.5,  defaultMode: 'binaural'   },
    'theta-intuition':            { carrierHz: 136.1, beatHz: 6,    defaultMode: 'binaural'   },
    'schumann-earth-pulse':       { carrierHz: 136.1, beatHz: 7.83, defaultMode: 'isochronic' },
    'alpha-calm-mind':            { carrierHz: 210,   beatHz: 8.4,  defaultMode: 'binaural'   },
    'alpha-serenity':             { carrierHz: 200,   beatHz: 10,   defaultMode: 'binaural'   },
    'beta-focus':                 { carrierHz: 250,   beatHz: 16,   defaultMode: 'isochronic' },
    'gamma-insight':              { carrierHz: 300,   beatHz: 40,   defaultMode: 'isochronic' },
    'solfeggio-transformation':   { carrierHz: 528,   beatHz: 7.83, defaultMode: 'isochronic' },
    'solfeggio-awaken-intuition': { carrierHz: 852,   beatHz: 6,    defaultMode: 'isochronic' },
    'solfeggio-crown-pineal':     { carrierHz: 963,   beatHz: 7.83, defaultMode: 'isochronic' }
  };

  var BED_IDS = ['none', 'womb', 'waterfall', 'jungle', 'forest', 'whales', 'ocean'];

  function clamp01(x) { x = +x; if (isNaN(x)) return 0; return x < 0 ? 0 : x > 1 ? 1 : x; }
  function now() { return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now(); }

  /* ========================================================================
   * MODULE STATE
   * ====================================================================== */
  var AC = null;            // AudioContext
  var S = null;             // AudioState reference (mutated in place)

  // Bus nodes
  var mixBus = null;        // sums drone + bed + tickle
  var masterGain = null;    // master level
  var analyser = null;      // the ONE analyser
  var slownessGain = null;  // gentle swell applied at mixBus input

  // Live node sets (torn down/rebuilt on changes)
  var droneNodes = [];      // oscillators / gains / panners / lfos for entrainment
  var tickleNodes = [];     // brain-tickle accent
  var bedNodes = [];        // ambient bed
  var slownessLfo = [];     // slowness swell lfo
  var loopTimers = [];      // setTimeout/interval handles for loop behavior
  var droneGain = null;     // persistent submix for drone + tickle (crossfade A side)
  var bedGain = null;       // persistent submix for ambient bed   (crossfade B side)

  // Analysis
  var freqData = null;      // Uint8Array(analyser.frequencyBinCount)
  var liveFrame = {         // mutated in place every updateAnalysis()
    bands: { sub: 0, low: 0, mid: 0, high: 0 },
    level: 0,
    t: 0
  };

  /* ========================================================================
   * HELPERS
   * ====================================================================== */
  function spec() {
    var d = DRONE_LIBRARY[S.droneId] || DRONE_LIBRARY['theta-intuition'];
    return d;
  }
  function effCarrier() { return (S.carrierHz != null) ? S.carrierHz : spec().carrierHz; }
  function effBeat()    { return (S.beatHz    != null) ? S.beatHz    : spec().beatHz; }

  function makeNoiseBuffer(seconds) {
    var len = Math.floor(AC.sampleRate * seconds);
    var buf = AC.createBuffer(1, len, AC.sampleRate);
    var data = buf.getChannelData(0);
    for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    return buf;
  }

  function noiseSource(seconds) {
    var src = AC.createBufferSource();
    src.buffer = makeNoiseBuffer(seconds || 2);
    src.loop = true;
    return src;
  }

  // Slow sine LFO modulating a target AudioParam around `base` by +/- `depth`.
  function attachLfo(targetParam, base, depth, hz, store) {
    var osc = AC.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = hz;
    var g = AC.createGain();
    g.gain.value = depth;
    osc.connect(g);
    g.connect(targetParam);
    targetParam.value = base;
    osc.start();
    store.push(osc, g);
    return osc;
  }

  function stopNodes(arr) {
    for (var i = 0; i < arr.length; i++) {
      var n = arr[i];
      try { if (n.stop) n.stop(); } catch (e) {}
      try { if (n.disconnect) n.disconnect(); } catch (e) {}
    }
    arr.length = 0;
  }

  function clearTimers() {
    for (var i = 0; i < loopTimers.length; i++) {
      clearTimeout(loopTimers[i]); clearInterval(loopTimers[i]);
    }
    loopTimers.length = 0;
  }

  /* ========================================================================
   * DRONE GRAPH (entrainment) — rebuilt on drone/mode/carrier/beat change
   * ====================================================================== */
  function buildDrone() {
    stopNodes(droneNodes);
    var carrier = effCarrier();
    var beat = effBeat();
    var mode = S.mode;

    if (mode === 'binaural') {
      // Two oscillators, hard-panned L/R; requires headphones for true beat.
      var oscL = AC.createOscillator(); oscL.type = 'sine'; oscL.frequency.value = carrier;
      var oscR = AC.createOscillator(); oscR.type = 'sine'; oscR.frequency.value = carrier + beat;
      var panL = AC.createStereoPanner(); panL.pan.value = -1;
      var panR = AC.createStereoPanner(); panR.pan.value = 1;
      var g = AC.createGain(); g.gain.value = 0.5;
      oscL.connect(panL); oscR.connect(panR);
      panL.connect(g); panR.connect(g);
      g.connect(droneGain);
      oscL.start(); oscR.start();
      droneNodes.push(oscL, oscR, panL, panR, g);

    } else if (mode === 'isochronic') {
      // Single tone, amplitude gated by a square LFO at beatHz.
      var osc = AC.createOscillator(); osc.type = 'sine'; osc.frequency.value = carrier;
      var gate = AC.createGain(); gate.gain.value = 0.5;
      var lfo = AC.createOscillator(); lfo.type = 'square'; lfo.frequency.value = beat;
      var lfoDepth = AC.createGain(); lfoDepth.gain.value = 0.5; // square -> 0..1 envelope
      lfo.connect(lfoDepth); lfoDepth.connect(gate.gain);
      osc.connect(gate); gate.connect(droneGain);
      osc.start(); lfo.start();
      droneNodes.push(osc, gate, lfo, lfoDepth);

    } else { // monaural
      // Two tones summed in mono (center); beat perceived as amplitude variation.
      var mL = AC.createOscillator(); mL.type = 'sine'; mL.frequency.value = carrier;
      var mR = AC.createOscillator(); mR.type = 'sine'; mR.frequency.value = carrier + beat;
      var mg = AC.createGain(); mg.gain.value = 0.4;
      mL.connect(mg); mR.connect(mg);
      mg.connect(droneGain);
      mL.start(); mR.start();
      droneNodes.push(mL, mR, mg);
    }
    applyLoopBehavior(carrier);
  }

  /* ========================================================================
   * BRAIN-TICKLE ACCENT — octave-up shimmer, gain = amount * 0.15
   * ====================================================================== */
  function buildTickle() {
    stopNodes(tickleNodes);
    var amt = clamp01(S.brainTickleAmount);
    if (amt <= 0) return;
    var osc = AC.createOscillator(); osc.type = 'sine'; osc.frequency.value = effCarrier() * 2;
    var g = AC.createGain(); g.gain.value = amt * 0.15;
    osc.connect(g); g.connect(droneGain);
    osc.start();
    tickleNodes.push(osc, g);
  }

  /* ========================================================================
   * SLOWNESS — gentle swell on the mixBus input gain.
   * lfoHz = 0.3 - (slowness * 0.25)  -> 0.05..0.3 Hz
   * ====================================================================== */
  function buildSlowness() {
    stopNodes(slownessLfo);
    if (!slownessGain) return;
    var slow = clamp01(S.slowness);
    var lfoHz = 0.3 - (slow * 0.25);
    var depth = 0.1 + slow * 0.15; // deeper swell when slower
    attachLfo(slownessGain.gain, 1.0 - depth * 0.5, depth, lfoHz, slownessLfo);
  }

  /* ========================================================================
   * AMBIENT BEDS (generative — Web Audio only, no sample files)
   * Bed intrinsic level. Blend (drone↔bed crossfade) is handled by bedGain via
   * applyBlend(); master volume by masterGain. This is just the bed's own level.
   * ====================================================================== */
  function bedGainValue() {
    return 0.6;
  }

  function buildBed() {
    stopNodes(bedNodes);
    var id = S.ambientBed;
    if (id === 'none') return;

    var out = AC.createGain();
    out.gain.value = bedGainValue();
    out.connect(bedGain);
    bedNodes.push(out);

    if (id === 'womb') {
      var n = noiseSource(2);
      var lp = AC.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 180; lp.Q.value = 0.8;
      var g = AC.createGain(); g.gain.value = 0.85;
      n.connect(lp); lp.connect(g); g.connect(out);
      n.start();
      attachLfo(g.gain, 0.85, 0.15, 0.08, bedNodes); // slow ±0.15 swell
      bedNodes.push(n, lp, g);

    } else if (id === 'waterfall') {
      var nw = noiseSource(2);
      var bp = AC.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 800; bp.Q.value = 0.4;
      var hp = AC.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 400;
      var gw = AC.createGain(); gw.gain.value = 0.7;
      nw.connect(bp); bp.connect(hp); hp.connect(gw); gw.connect(out);
      nw.start();
      bedNodes.push(nw, bp, hp, gw);

    } else if (id === 'jungle') {
      // Pink-ish: white noise shaped by 3 peaking filters; AM LFO at 1.8 Hz.
      var nj = noiseSource(2);
      var p1 = AC.createBiquadFilter(); p1.type = 'peaking'; p1.frequency.value = 400;  p1.Q.value = 1; p1.gain.value = 6;
      var p2 = AC.createBiquadFilter(); p2.type = 'peaking'; p2.frequency.value = 1200; p2.Q.value = 1; p2.gain.value = -4;
      var p3 = AC.createBiquadFilter(); p3.type = 'peaking'; p3.frequency.value = 3000; p3.Q.value = 1; p3.gain.value = 3;
      var gj = AC.createGain(); gj.gain.value = 0.6;
      nj.connect(p1); p1.connect(p2); p2.connect(p3); p3.connect(gj); gj.connect(out);
      nj.start();
      attachLfo(gj.gain, 0.6, 0.25, 1.8, bedNodes); // AM 1.8 Hz depth 0.25
      bedNodes.push(nj, p1, p2, p3, gj);

    } else if (id === 'forest') {
      var nf = noiseSource(2);
      var lpf = AC.createBiquadFilter(); lpf.type = 'lowpass'; lpf.frequency.value = 600;
      var gf = AC.createGain(); gf.gain.value = 0.5;
      nf.connect(lpf); lpf.connect(gf); gf.connect(out);
      nf.start();
      // 432 Hz sine with slow vibrato (0.12 Hz, ±2 Hz), gain 0.03
      var tone = AC.createOscillator(); tone.type = 'sine'; tone.frequency.value = 432;
      var tg = AC.createGain(); tg.gain.value = 0.03;
      tone.connect(tg); tg.connect(out);
      tone.start();
      attachLfo(tone.frequency, 432, 2, 0.12, bedNodes);
      bedNodes.push(nf, lpf, gf, tone, tg);

    } else if (id === 'whales') {
      // Sine sweeping 80->200->80 Hz over 18s, looped via setValueCurveAtTime.
      var wo = AC.createOscillator(); wo.type = 'sine';
      var wg = AC.createGain(); wg.gain.value = 0.4;
      wo.connect(wg); wg.connect(out);
      wo.start();
      var curve = new Float32Array(64);
      for (var i = 0; i < 64; i++) {
        var ph = i / 63;                 // 0..1
        var tri = ph < 0.5 ? ph * 2 : (1 - ph) * 2; // 0..1..0
        curve[i] = 80 + tri * 120;       // 80..200..80
      }
      var DUR = 18;
      function scheduleSweep() {
        var t0 = AC.currentTime + 0.01;
        try { wo.frequency.cancelScheduledValues(t0); } catch (e) {}
        try { wo.frequency.setValueCurveAtTime(curve, t0, DUR); } catch (e) {}
        loopTimers.push(setTimeout(scheduleSweep, DUR * 1000));
      }
      scheduleSweep();
      bedNodes.push(wo, wg);

    } else if (id === 'ocean') {
      // Three sines 55/110/165 Hz, each with independent slow gain LFO.
      var freqs = [55, 110, 165];
      var lfoHz = [0.04, 0.065, 0.09];
      var depth = [0.2, 0.28, 0.35];
      var sum = AC.createGain(); sum.gain.value = 0.3;
      sum.connect(out);
      bedNodes.push(sum);
      for (var k = 0; k < 3; k++) {
        var o = AC.createOscillator(); o.type = 'sine'; o.frequency.value = freqs[k];
        var og = AC.createGain(); og.gain.value = depth[k];
        o.connect(og); og.connect(sum);
        o.start();
        attachLfo(og.gain, depth[k], depth[k] * 0.6, lfoHz[k], bedNodes);
        bedNodes.push(o, og);
      }
    }
  }

  /* ========================================================================
   * LOOP BEHAVIOR
   *   crossfade: every ~12s, drift to a new oscillator set (±0.5 Hz) over 2s
   *   evolving:  slow carrier drift ±2 Hz over 30s via setTargetAtTime
   *   one-shot:  play 60s then stop()
   * ====================================================================== */
  function applyLoopBehavior(carrier) {
    if (S.loop === 'evolving') {
      // Gentle continuous detune on the primary drone oscillator(s).
      var targets = droneNodes.filter(function (n) { return n.frequency; });
      function drift() {
        var t = AC.currentTime;
        for (var i = 0; i < targets.length; i++) {
          var base = targets[i].frequency.value;
          var dest = base + (Math.random() * 4 - 2); // ±2 Hz
          try { targets[i].frequency.setTargetAtTime(dest, t, 10); } catch (e) {}
        }
        loopTimers.push(setTimeout(drift, 30000));
      }
      loopTimers.push(setTimeout(drift, 30000));

    } else if (S.loop === 'crossfade') {
      function cyc() {
        // Nudge carrier ±0.5 Hz; full teardown/rebuild would click, so detune.
        var t = AC.currentTime;
        var targets2 = droneNodes.filter(function (n) { return n.frequency; });
        for (var i = 0; i < targets2.length; i++) {
          var dest = targets2[i].frequency.value + (Math.random() - 0.5);
          try { targets2[i].frequency.setTargetAtTime(dest, t, 2); } catch (e) {}
        }
        loopTimers.push(setTimeout(cyc, 12000));
      }
      loopTimers.push(setTimeout(cyc, 12000));

    } else if (S.loop === 'one-shot') {
      loopTimers.push(setTimeout(function () { api.stop(); }, 60000));
    }
  }

  /* ========================================================================
   * FFT BAND EXTRACTION — call once per rAF tick.
   * binHz = AC.sampleRate / analyser.fftSize
   * ====================================================================== */
  function bandAvg(lo, hi, binHz) {
    var i0 = Math.max(0, Math.floor(lo / binHz));
    var i1 = Math.min(freqData.length - 1, Math.ceil(hi / binHz));
    var sum = 0, c = 0;
    for (var i = i0; i <= i1; i++) { sum += freqData[i]; c++; }
    return c ? (sum / c) / 255 : 0;
  }

  function updateAnalysis() {
    if (!analyser || !freqData) return;
    analyser.getByteFrequencyData(freqData);
    var binHz = AC.sampleRate / analyser.fftSize;
    liveFrame.bands.sub  = bandAvg(20,   120,  binHz);
    liveFrame.bands.low  = bandAvg(120,  500,  binHz);
    liveFrame.bands.mid  = bandAvg(500,  2000, binHz);
    liveFrame.bands.high = bandAvg(2000, 8000, binHz);
    // RMS over the whole spectrum
    var sq = 0;
    for (var i = 0; i < freqData.length; i++) { var v = freqData[i]; sq += v * v; }
    liveFrame.level = Math.sqrt(sq / freqData.length) / 255;
    liveFrame.t = now();
  }

  /* ========================================================================
   * GRAPH ASSEMBLY
   * ====================================================================== */
  function buildBus() {
    slownessGain = AC.createGain(); slownessGain.gain.value = 1.0;
    mixBus = AC.createGain(); mixBus.gain.value = 1.0;
    droneGain = AC.createGain();
    bedGain = AC.createGain();
    masterGain = AC.createGain(); masterGain.gain.value = clamp01(S.masterLevel);
    analyser = AC.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.8;
    freqData = new Uint8Array(analyser.frequencyBinCount);

    // drone/bed submixes -> mixBus -> slownessGain -> masterGain -> analyser -> destination
    droneGain.connect(mixBus);
    bedGain.connect(mixBus);
    mixBus.connect(slownessGain);
    slownessGain.connect(masterGain);
    masterGain.connect(analyser);
    analyser.connect(AC.destination);
    applyBlend();
  }

  /* Equal-power crossfade: blend 0 = all drone, 1 = all bed, 0.5 = balanced.
     cos/sin keeps perceived loudness flat through the center. */
  function applyBlend() {
    if (!droneGain || !bedGain) return;
    var b = clamp01(S.ambientBlend);
    droneGain.gain.value = Math.cos(b * Math.PI / 2);
    bedGain.gain.value   = Math.sin(b * Math.PI / 2);
  }

  function rebuildVoices() {
    buildDrone();
    buildTickle();
    buildBed();
    buildSlowness();
  }

  /* ========================================================================
   * PUBLIC INTERFACE
   * ====================================================================== */
  function init(audioState) {
    try {
      S = audioState;
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return false;
      AC = new Ctx();
      buildBus();
      /* Do NOT call rebuildVoices() here — oscillators must not start until
         the user explicitly calls start(). AC may already be running when
         navigated from index.html (gesture carried across location.replace),
         so osc.start() on a running AC plays immediately. Voices are built
         in start() instead. */
      try { AC.suspend(); } catch (e) {}
      S.isPlaying = false;
      return true;
    } catch (e) {
      return false;
    }
  }

  function start() {
    if (!AC) return;
    try { AC.resume(); } catch (e) {}
    if (!mixBus) { buildBus(); }
    rebuildVoices();
    S.isPlaying = true;
  }

  function stop() {
    if (!AC) return;
    try { AC.suspend(); } catch (e) {}
    // Stop tears down and rebuilds the voice fresh (per spec: stop rebuilds).
    clearTimers();
    rebuildVoices();
    S.isPlaying = false;
  }

  function setDrone(droneId) {
    if (!DRONE_LIBRARY[droneId]) return;
    S.droneId = droneId;
    S.carrierHz = null; S.beatHz = null; // revert overrides to spec defaults
    clearTimers();
    buildDrone(); buildTickle();
  }

  function setMode(mode) {
    if (mode !== 'binaural' && mode !== 'isochronic' && mode !== 'monaural') return;
    S.mode = mode;
    clearTimers();
    buildDrone();
  }

  function setCarrier(hz) {
    if (isNaN(hz)) return;
    S.carrierHz = hz;
    clearTimers();
    buildDrone(); buildTickle();
  }

  function setBeat(hz) {
    if (isNaN(hz)) return;
    S.beatHz = hz;
    clearTimers();
    buildDrone();
  }

  function setTickle(v) {
    S.brainTickleAmount = clamp01(v);
    // Live-update gain if the accent is already running; else (re)build.
    // tickleNodes layout: [osc, gain].
    if (tickleNodes.length >= 2 && tickleNodes[1] && tickleNodes[1].gain && S.brainTickleAmount > 0) {
      tickleNodes[1].gain.value = S.brainTickleAmount * 0.15;
    } else {
      buildTickle(); // handles 0 -> teardown and 0 -> on rebuild
    }
  }

  function setSlowness(v) {
    S.slowness = clamp01(v);
    // Rate + depth are baked at build time; rebuild the swell LFO.
    buildSlowness();
  }

  function setBed(bedId) {
    if (BED_IDS.indexOf(bedId) === -1) return;
    S.ambientBed = bedId;
    buildBed();
  }

  function setBedBlend(v) {
    S.ambientBlend = clamp01(v);
    // 0 = all drone, 1 = all bed, 0.5 = balanced (equal-power).
    applyBlend();
  }

  function setLoop(behavior) {
    if (behavior !== 'crossfade' && behavior !== 'evolving' && behavior !== 'one-shot') return;
    S.loop = behavior;
    clearTimers();
    applyLoopBehavior(effCarrier());
  }

  function setMaster(v) {
    S.masterLevel = clamp01(v);
    if (masterGain) masterGain.gain.value = S.masterLevel;
  }

  function setRoute(band, param, amount) {
    if (!S.routes) S.routes = [];
    for (var i = 0; i < S.routes.length; i++) {
      if (S.routes[i].band === band) {
        S.routes[i].param = param;
        S.routes[i].amount = clamp01(amount);
        return;
      }
    }
    S.routes.push({ band: band, param: param, amount: clamp01(amount) });
  }

  function getAnalysisFrame() { return liveFrame; }

  function isReady() {
    return !!(AC && mixBus && analyser && AC.destination);
  }

  function dispose() {
    clearTimers();
    stopNodes(droneNodes); stopNodes(tickleNodes);
    stopNodes(bedNodes); stopNodes(slownessLfo);
    try { if (analyser) analyser.disconnect(); } catch (e) {}
    try { if (masterGain) masterGain.disconnect(); } catch (e) {}
    try { if (slownessGain) slownessGain.disconnect(); } catch (e) {}
    try { if (droneGain) droneGain.disconnect(); } catch (e) {}
    try { if (bedGain) bedGain.disconnect(); } catch (e) {}
    try { if (mixBus) mixBus.disconnect(); } catch (e) {}
    try { if (AC) AC.close(); } catch (e) {}
    AC = mixBus = masterGain = analyser = slownessGain = droneGain = bedGain = freqData = null;
  }

  var api = {
    init: init, start: start, stop: stop,
    setDrone: setDrone, setMode: setMode,
    setCarrier: setCarrier, setBeat: setBeat,
    setTickle: setTickle, setSlowness: setSlowness,
    setBed: setBed, setBedBlend: setBedBlend,
    setLoop: setLoop, setMaster: setMaster, setRoute: setRoute,
    updateAnalysis: updateAnalysis, getAnalysisFrame: getAnalysisFrame,
    isReady: isReady, dispose: dispose,
    CONTRACTS_VERSION: CONTRACTS_VERSION
  };

  window.OlogyAudio = api;

  /* --- Window aliases for existing index.html onclick/oninput handlers ---- */
  window.selectDrone  = function (id) { window.OlogyAudio.setDrone(id); };
  window.selectMode   = function (m)  { window.OlogyAudio.setMode(m); };
  window.setCarrierHz = function (hz) { window.OlogyAudio.setCarrier(parseFloat(hz)); };
  window.setBeatHz    = function (hz) { window.OlogyAudio.setBeat(parseFloat(hz)); };
  window.selectBed    = function (id) { window.OlogyAudio.setBed(id); };
  window.setBedBlend  = function (v)  { window.OlogyAudio.setBedBlend(parseFloat(v)); };
  window.setMasterVol = function (v)  { window.OlogyAudio.setMaster(parseFloat(v)); };
  window.audioStart   = function ()   { window.OlogyAudio.start(); };
  window.audioStop    = function ()   { window.OlogyAudio.stop(); };

})();
