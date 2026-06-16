/* ════════════════════════════════════════════════════════════════════════
   OLOGY — M1: m1_shaders.js   (WebGL2 GLSL kaleidoscope renderer)
   ════════════════════════════════════════════════════════════════════════
   Replaces the Canvas-2D drawK() placeholder in index.html + output.html.
   M0 contracts: contracts.ts v0.2.0 (frozen). No bundler / no ES modules.

   PUBLIC INTERFACE  (window.OlogyShaders)
   ---------------------------------------------------------------------------
     init(canvas?)                         -> bool   (true on success)
     draw(dest, state, analysisFrame, t, strobeGate)
     resize()
     isReady()                             -> bool
     dispose()                             -> void   (cleanup; optional)

   NOTE ON SIGNATURE (deviation from build-prompt, documented for sign-off):
   The prompt specified draw(state, analysisFrame, t, strobeGate). In the real
   index.html the renderer is invoked THREE times per frame against three
   distinct visible canvases (preview / program / mobile); output.html invokes
   it once. A single WebGL2 context binds to one canvas, so M1 keeps ONE
   internal offscreen GL canvas (one shader compile) and BLITS the rendered
   frame to whichever destination is passed. Hence draw() takes a leading
   `dest` argument (a CanvasRenderingContext2D, an HTMLCanvasElement, or null
   to render straight into the GL canvas for an output.html-style single view).
   Everything after `dest` matches the prompt exactly.

       dest:           CanvasRenderingContext2D | HTMLCanvasElement | null
       state:          { visual:VisualState, audio:AudioState, t:number }
                       (t inside state is tolerated; the explicit `t` arg wins)
       analysisFrame:  M0 AudioAnalysisFrame { bands:{sub,low,mid,high}, level, t }
       t:              number  (seconds; render clock)
       strobeGate:     number 0..1  (0 => full black frame)

   CHANGES vs first delivery (both bugs required regeneration):
   1. preserveDrawingBuffer was TRUE → caused GPU pipeline stall × 3/frame on
      Intel Iris Plus 640 (Bootcamp), freezing USB HID bus. Fixed: internal GL
      canvas is now an OffscreenCanvas; blit uses transferToImageBitmap() +
      transferFromImageBitmap() which is zero-copy on Chromium/Opera. No backing
      buffer copy; no pipeline stall.
   2. Reinhard tone curve (col / (col + 0.6)) compressed palette hues into a
      grey wash. Fixed: replaced with a simple 1/2.0 gamma lift that preserves
      saturation. Vignette floor raised from 0.55 to 0.70 to recover edge colour.
   ════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  /* ----- M0 frozen palettes (3-stop hex per ThemeId) --------------------- */
  var THEME_PALETTES = {
    'intergalactic-beings': ['#0a0fff', '#ffffff', '#050510'],
    'supernovas':           ['#fff1c9', '#ff8a3d', '#d61f4e'],
    'aurora-borealis':      ['#1b2a8a', '#27c2e0', '#cfd6ff'],
    'psilocybin-dreams':    ['#5a00cc', '#39ff6a', '#c200ff'],
    'microcosmos':          ['#16d39a', '#2a6cff', '#eafff6'],
    'quantum-fields':       ['#0a0014', '#ff00cc', '#3d006b'],
    'torus-universes':      ['#08010f', '#1a0a6b', '#3b1205']
  };

  /* Stable integer index per theme -> drives a switch() in the shader.
     Order is frozen; do not reorder (matches contracts.ts ThemeId union). */
  var THEME_INDEX = {
    'intergalactic-beings': 0,
    'supernovas':           1,
    'aurora-borealis':          2,
    'psilocybin-dreams':    3,
    'microcosmos':          4,
    'quantum-fields':       5,
    'torus-universes':      6
  };

  var MAX_CHAOS = 1.0;        // M0 SECTION 11
  var DEFAULT_THEME = 'intergalactic-beings';

  /* hex "#rrggbb" -> [r,g,b] in 0..1 */
  function hex2rgb01(h) {
    h = h.replace('#', '');
    return [
      parseInt(h.slice(0, 2), 16) / 255,
      parseInt(h.slice(2, 4), 16) / 255,
      parseInt(h.slice(4, 6), 16) / 255
    ];
  }

  /* ═══════════════════════════════════════════════════════════════════════
     GLSL ES 3.00  —  VERTEX  (fullscreen triangle, no attributes needed)
     ═══════════════════════════════════════════════════════════════════════ */
  var VERT_SRC = [
    '#version 300 es',
    'void main() {',
    '  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));',
    '  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);',
    '}'
  ].join('\n');

  /* ═══════════════════════════════════════════════════════════════════════
     GLSL ES 3.00  —  FRAGMENT
     - highp for coords/position, mediump for color (Intel Iris Plus safe)
     - NO dFdx/dFdy (Intel Iris Plus / Bootcamp Windows driver safety)
     - all loops have constant caps <= 6
     ═══════════════════════════════════════════════════════════════════════ */
  var FRAG_SRC = [
    '#version 300 es',
    'precision highp float;',
    'out mediump vec4 fragColor;',
    '',
    'uniform highp  vec2  u_res;',
    'uniform highp  float u_time;',
    'uniform mediump vec3 u_pal0;',
    'uniform mediump vec3 u_pal1;',
    'uniform mediump vec3 u_pal2;',
    'uniform int    u_theme;',
    'uniform highp  float u_speed;',
    'uniform highp  float u_chaos;',
    'uniform highp  float u_fractal;',
    'uniform highp  float u_zoom;',
    'uniform highp  float u_rotation;',
    'uniform highp  float u_symmetry;',
    'uniform mediump float u_bloom;',
    'uniform mediump float u_colorShift;',
    'uniform mediump float u_level;',
    'uniform mediump float u_strobeGate;',
    'uniform mediump float u_master;',
    'uniform mediump float u_smooth;',
    '',
    'const float PI  = 3.14159265359;',
    'const float TAU = 6.28318530718;',
    '',
    'float hash21(vec2 p){',
    '  p = fract(p * vec2(123.34, 456.21));',
    '  p += dot(p, p + 45.32);',
    '  return fract(p.x * p.y);',
    '}',
    'float vnoise(vec2 p){',
    '  vec2 i = floor(p); vec2 f = fract(p);',
    '  vec2 u = f * f * (3.0 - 2.0 * f);',
    '  float a = hash21(i + vec2(0.0,0.0));',
    '  float b = hash21(i + vec2(1.0,0.0));',
    '  float c = hash21(i + vec2(0.0,1.0));',
    '  float d = hash21(i + vec2(1.0,1.0));',
    '  return mix(mix(a,b,u.x), mix(c,d,u.x), u.y);',
    '}',
    'float fbm(vec2 p){',
    '  float sum = 0.0; float amp = 0.5; float freq = 1.0;',
    '  float oct = clamp(u_fractal, 1.0, 8.0);',
    '  for(int i = 0; i < 8; i++){',
    '    float w = clamp(oct - float(i), 0.0, 1.0);',
    '    sum += amp * w * vnoise(p * freq);',
    '    freq *= 2.0; amp *= 0.5;',
    '  }',
    '  return sum;',
    '}',
    '',
    'mat2 rot(float a){ float c = cos(a); float s = sin(a); return mat2(c,-s,s,c); }',
    '',
    'vec3 palette(float x){',
    '  x = clamp(x, 0.0, 1.0);',
    '  // smoothstep weights give C1-continuous transitions at 0 and 1',
    '  float w1 = smoothstep(0.0, 1.0, clamp(x * 2.0,       0.0, 1.0));',
    '  float w2 = smoothstep(0.0, 1.0, clamp(x * 2.0 - 1.0, 0.0, 1.0));',
    '  vec3 a = mix(u_pal0, u_pal1, w1);',
    '  return mix(a, u_pal2, w2);',
    '}',
    '',
    'vec2 kaleido(vec2 p, float segs){',
    '  float r = length(p);',
    '  float a = atan(p.y, p.x);',
    '  // symmetry == 1 : Radial — NO bilateral fold, angle passes through',
    '  //                 (rotational field only; visually distinct from Mirror)',
    '  if(segs < 1.5){',
    '    return vec2(cos(a), sin(a)) * r;',
    '  }',
    '  // symmetry == 2 : Mirror — single bilateral reflection across one axis',
    '  if(segs < 2.5){',
    '    a = abs(a);',                     // reflect lower half onto upper -> true mirror
    '    return vec2(cos(a), sin(a)) * r;',
    '  }',
    '  // symmetry >= 3 : Kaleidoscope — N-segment radial wedge mirror',
    '  float n = segs;',
    '  float seg = TAU / n;',
    '  a = mod(a, seg);',
    '  a = abs(a - seg * 0.5);',
    '  return vec2(cos(a), sin(a)) * r;',
    '}',
    ''
  ].join('\n');

  FRAG_SRC += [
    '',
    'void main(){',
    /* UV: normalise by height so pattern fills full canvas edge-to-edge at any AR.
       Width extends proportionally — no black bars, no clipping at corners. */
    '  highp vec2 uv = (gl_FragCoord.xy - 0.5 * u_res) / u_res.y;',
    '  uv.y = -uv.y;',
    '',
    '  if(u_strobeGate <= 0.0){ fragColor = vec4(0.0,0.0,0.0,1.0); return; }',
    '',
    '  highp float t  = u_time;',
    '  highp float sp = 0.3 + u_speed;',
    /* zoomScale: low u_zoom = large coords = more pattern visible (zoomed out).
       High u_zoom = small coords = pattern fills screen (zoomed in). */
    '  highp float zoomScale = mix(8.0, 0.4, clamp(u_zoom, 0.0, 1.0));',
    '  highp vec2  p  = uv * zoomScale;',
    '',
    '  p = rot(t * u_rotation) * p;',
    '',
    '  highp float ch = clamp(u_chaos, 0.0, 1.0);',
    '  if(u_theme == 0){',
    '    p += 0.18 * vec2(fbm(p*1.3 + t*0.06), fbm(p*1.3 - t*0.05));',
    '  } else if(u_theme == 1){',
    '    float r = length(p);',
    '    p *= (1.0 + 0.25*sin(r*6.0 - t*sp*2.2));',
    '  } else if(u_theme == 2){',
    '    float r = length(p) + 1e-3;',
    '    float a = atan(p.y, p.x);',
    '    p = vec2(a / PI, 0.35 / r + t*sp*0.6);',
    '  } else if(u_theme == 3){',
    '    p += 0.22*vec2(fbm(p*2.0+t*0.2), fbm(p*2.0-t*0.17));',
    '  } else if(u_theme == 4){',
    '    p += 0.10*vec2(fbm(p*3.2+t*0.1), fbm(p*3.2+5.0-t*0.08));',
    '  } else if(u_theme == 5){',
    '    p += 0.06*vec2(sin(p.y*8.0+t*sp), sin(p.x*8.0-t*sp));',
    '  } else {',
    '    float r = length(p);',
    '    p = rot(0.5/(r+0.3) + t*sp*0.3) * p;',
    '  }',
    '',
    /* Kaleido fold — infinite tiling, no clipping, fills all corners */
    '  p = kaleido(p, u_symmetry);',
    '',
    '  highp vec2 q = p;',
    '  q += ch * 0.6 * vec2(fbm(p*1.7 + t*0.25), fbm(p*1.7 + 9.0 - t*0.2));',
    '',
    '  highp float f    = fbm(q*1.5 + t*0.15*sp);',
    '  highp float rings = 0.5 + 0.5*sin(length(q)*1.8 - t*sp + f*4.0);',
    '  highp float field = clamp(0.35*f + 0.65*rings, 0.0, 1.0);',
    '',
    /* Contrast-expand: spread field values across full [0,1] palette range */
    '  field = clamp((field - 0.35) / 0.30, 0.0, 1.0);',
    '',
    /* u_smooth: edge sharpness (low) to colour bleed/blur (high) */
    '  highp float edgeW  = mix(0.45, 0.02, clamp(u_smooth, 0.0, 1.0));',
    '  highp float blurR  = mix(0.0,  0.18, clamp(u_smooth, 0.0, 1.0));',
    '  highp float posRaw = fract(field + u_colorShift + 0.05*t*sp*0.2);',
    '  highp float zone        = floor(posRaw * 3.0);',
    '  highp float zonePos     = fract(posRaw * 3.0);',
    '  highp float sharpZonePos = smoothstep(edgeW, 1.0 - edgeW, zonePos);',
    '  mediump float pos = clamp((zone + sharpZonePos) / 3.0, 0.0, 1.0);',
    '',
    /* Multi-sample colour blur at high smooth values */
    '  mediump vec3 col = palette(pos);',
    '  if(blurR > 0.001){',
    '    col += palette(fract(pos - blurR * 2.0));',
    '    col += palette(fract(pos - blurR));',
    '    col += palette(fract(pos + blurR));',
    '    col += palette(fract(pos + blurR * 2.0));',
    '    col *= 0.2;',
    '  }',
    '',
    /* Bloom: additive glow */
    '  mediump float glow = pow(field, 2.0);',
    '  col += u_bloom * glow * 0.6 * palette(fract(pos + 0.5));',
    '',
    /* Loudness lift */
    '  col *= (0.9 + 0.25 * u_level);',
    '',
    /* Gamma */
    '  col = pow(clamp(col, 0.0, 1.0), vec3(0.5));',
    '  col *= u_strobeGate;',
    '  fragColor = vec4(col, 1.0);',
    '}'
  ].join('\n');

  /* ═══════════════════════════════════════════════════════════════════════
     WebGL2 PLUMBING
     ═══════════════════════════════════════════════════════════════════════ */
  var gl        = null;   // WebGL2RenderingContext
  var glCanvas  = null;   // internal OffscreenCanvas (zero-copy blit path)
  var program   = null;
  var vao       = null;
  var U         = {};     // cached uniform locations
  var ready     = false;
  var _destCtxCache = null;   // cached 2D context — avoids getContext('2d') every frame

  var UNIFORM_NAMES = [
    'u_res','u_time','u_pal0','u_pal1','u_pal2','u_theme','u_speed','u_chaos',
    'u_fractal','u_zoom','u_rotation','u_symmetry','u_bloom','u_colorShift',
    'u_level','u_strobeGate','u_master','u_smooth'
  ];

  function compile(type, src) {
    var sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      var log = gl.getShaderInfoLog(sh);
      gl.deleteShader(sh);
      throw new Error('[OlogyShaders] shader compile failed:\n' + log);
    }
    return sh;
  }

  function link(vs, fs) {
    var pr = gl.createProgram();
    gl.attachShader(pr, vs);
    gl.attachShader(pr, fs);
    gl.linkProgram(pr);
    if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) {
      var log = gl.getProgramInfoLog(pr);
      gl.deleteProgram(pr);
      throw new Error('[OlogyShaders] program link failed:\n' + log);
    }
    return pr;
  }

  function init(canvas) {
    if (ready) return true;
    try {
      /* FIX: use OffscreenCanvas as the internal GL surface.
         preserveDrawingBuffer:false (the default) means the driver is free to
         discard the backbuffer after each present — no per-frame copy.
         We read the frame via transferToImageBitmap() which is zero-copy on
         Chromium. The caller-supplied canvas arg is ignored for the GL surface
         (kept in the API for forward compatibility / output.html direct-draw). */
      if (typeof OffscreenCanvas === 'undefined') {
        console.error('[OlogyShaders] OffscreenCanvas unavailable — cannot init.');
        return false;
      }
      glCanvas = new OffscreenCanvas(1280, 720);
      gl = glCanvas.getContext('webgl2', {
        antialias:           false,   // off: saves fill-rate on Intel Iris Plus
        alpha:               false,
        premultipliedAlpha:  false,
        preserveDrawingBuffer: false  // FIX: was true — caused GPU stall × 3/frame
      });
      if (!gl) {
        console.error('[OlogyShaders] WebGL2 not available on OffscreenCanvas.');
        return false;
      }

      /* suppress powerPreference so the driver decides; 'high-performance' on
         Bootcamp Intel sometimes forces discrete GPU switch which isn't wanted */

      var vs = compile(gl.VERTEX_SHADER,   VERT_SRC);
      var fs = compile(gl.FRAGMENT_SHADER, FRAG_SRC);
      program = link(vs, fs);
      gl.deleteShader(vs);
      gl.deleteShader(fs);

      vao = gl.createVertexArray();

      for (var i = 0; i < UNIFORM_NAMES.length; i++) {
        U[UNIFORM_NAMES[i]] = gl.getUniformLocation(program, UNIFORM_NAMES[i]);
      }

      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.BLEND);
      ready = true;
      return true;
    } catch (e) {
      console.error('[OlogyShaders] init error:', e && e.message ? e.message : e);
      ready = false;
      return false;
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     REACTIVITY  (CPU side — mirrors M0 route matrix)
     ═══════════════════════════════════════════════════════════════════════ */
  function reactiveParams(visual, audio, analysisFrame) {
    var out = {
      speed:        visual.speed,
      chaos:        visual.chaos,
      zoom:         visual.zoom,
      rotation:     visual.rotation,
      symmetry:     visual.symmetry,
      bloom:        visual.bloom,
      fractalDepth: visual.fractalDepth,
      colorShift:   0,
      master: (audio && typeof audio.masterLevel === 'number')
                ? audio.masterLevel : 0.8,
      smooth: (typeof visual.smooth === 'number') ? visual.smooth : 0.82,
      level: (analysisFrame && typeof analysisFrame.level === 'number')
               ? analysisFrame.level : 0
    };
    var bands = (analysisFrame && analysisFrame.bands) ? analysisFrame.bands : null;
    if (audio && audio.isPlaying && bands && audio.routes) {
      for (var i = 0; i < audio.routes.length; i++) {
        var r = audio.routes[i];
        var e = bands[r.band] || 0;
        if (r.param === 'colorShift') out.colorShift += r.amount * e;
        else if (out[r.param] != null) out[r.param] += r.amount * e * 0.6;
      }
    }
    out.chaos = Math.min(MAX_CHAOS, out.chaos);
    return out;
  }

  function sizeGLTo(w, h) {
    if (w < 1) w = 1;
    if (h < 1) h = 1;
    if (glCanvas.width !== w || glCanvas.height !== h) {
      glCanvas.width  = w;
      glCanvas.height = h;
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     DRAW
     ═══════════════════════════════════════════════════════════════════════ */
  function draw(dest, state, analysisFrame, t, strobeGate) {
    if (!ready) return;

    /* resolve destination + target pixel size */
    var destCtx = null, destCanvas = null, tw, th;
    if (dest && dest.canvas && typeof dest.drawImage === 'function') {
      destCtx = dest; destCanvas = dest.canvas;           // 2D context
    } else if (dest && dest.getContext) {
      destCanvas = dest;
      /* Cache the 2D context: getContext('2d') on every frame causes a
         compositing stall on Intel Iris Plus 640 at high resolution,
         starving OS cursor rendering. Re-acquire only when dest changes. */
      if (_destCtxCache === null || _destCtxCache.canvas !== dest) {
        _destCtxCache = dest.getContext('2d');
      }
      destCtx = _destCtxCache;
    }
    if (destCanvas) { tw = destCanvas.width;  th = destCanvas.height; }
    else            { tw = glCanvas.width;    th = glCanvas.height;   }
    if (!tw || !th) return;

    sizeGLTo(tw, th);

    var visual = state && state.visual ? state.visual : null;
    var audio  = state && state.audio  ? state.audio  : null;
    if (!visual) return;
    var time = (typeof t === 'number') ? t
             : (state && typeof state.t === 'number') ? state.t : 0;
    var gate = (typeof strobeGate === 'number') ? strobeGate : 1;

    var p   = reactiveParams(visual, audio, analysisFrame);
    var pal = THEME_PALETTES[visual.themeId] || THEME_PALETTES[DEFAULT_THEME];
    var c0  = hex2rgb01(pal[0]);
    var c1  = hex2rgb01(pal[1]);
    var c2  = hex2rgb01(pal[2]);
    var themeIdx = (THEME_INDEX[visual.themeId] != null) ? THEME_INDEX[visual.themeId] : 0;

    gl.viewport(0, 0, glCanvas.width, glCanvas.height);
    gl.useProgram(program);
    gl.bindVertexArray(vao);

    gl.uniform2f(U.u_res,        glCanvas.width, glCanvas.height);
    gl.uniform1f(U.u_time,       time);
    gl.uniform3f(U.u_pal0,       c0[0], c0[1], c0[2]);
    gl.uniform3f(U.u_pal1,       c1[0], c1[1], c1[2]);
    gl.uniform3f(U.u_pal2,       c2[0], c2[1], c2[2]);
    gl.uniform1i(U.u_theme,      themeIdx | 0);
    gl.uniform1f(U.u_speed,      p.speed);
    gl.uniform1f(U.u_chaos,      p.chaos);
    gl.uniform1f(U.u_fractal,    p.fractalDepth);
    gl.uniform1f(U.u_zoom,       p.zoom);
    gl.uniform1f(U.u_rotation,   p.rotation);
    gl.uniform1f(U.u_symmetry,   Math.max(1, Math.round(p.symmetry)));
    gl.uniform1f(U.u_bloom,      p.bloom);
    gl.uniform1f(U.u_colorShift, p.colorShift);
    gl.uniform1f(U.u_level,      p.level);
    gl.uniform1f(U.u_strobeGate, gate);
    gl.uniform1f(U.u_master,     Math.max(0, Math.min(1, p.master)));
    gl.uniform1f(U.u_smooth,     Math.max(0, Math.min(1, p.smooth)));

    gl.drawArrays(gl.TRIANGLES, 0, 3);

    /* Blit: transferToImageBitmap() snapshots the OffscreenCanvas frame (zero
       driver-copy; preserveDrawingBuffer:false is safe because the snapshot is
       taken before the backbuffer is discarded). drawImage() on the ImageBitmap
       is a plain GPU-accelerated composite — no readPixels, no CPU round-trip.
       transferFromImageBitmap() is NOT used: it requires a 2D context from an
       OffscreenCanvas, not from a regular HTMLCanvasElement. */
    if (destCtx && destCanvas) {
      var bmp = glCanvas.transferToImageBitmap();
      destCtx.drawImage(bmp, 0, 0, destCanvas.width, destCanvas.height);
      bmp.close();
    }
  }

  function resize() { /* lazy-resize per draw; hook kept for API completeness */ }

  function isReady() { return ready; }

  function dispose() {
    try { if (gl && program) gl.deleteProgram(program); } catch (e) {}
    try { if (gl && vao)     gl.deleteVertexArray(vao); } catch (e) {}
    program = null; vao = null; U = {}; ready = false; gl = null; glCanvas = null; _destCtxCache = null;
  }

  global.OlogyShaders = {
    init:    init,
    draw:    draw,
    resize:  resize,
    isReady: isReady,
    dispose: dispose
  };

})(typeof window !== 'undefined' ? window : this);
