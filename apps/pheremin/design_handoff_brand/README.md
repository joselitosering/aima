# Pheremin Brand Guidelines Handoff

## Overview
Pheremin is a webcam gesture FM synthesizer by AIMA Productions. Players perform music using hand gestures and facial expressions captured via webcam — no keys, no cables. The brand is **neon-on-void**: deep near-black violet backgrounds lit by glowing fuchsia, violet, and cyan. The aesthetic is part science demo, part chic performance toy — synesthesia you can perform.

> **These files are design references** created as HTML prototypes. Use them as specifications for implementing the brand in your target environment (React, native, web, etc.) — do not ship the HTML directly.

---

## Brand Positioning

| Attribute | Value |
|---|---|
| **Product** | Gesture FM synthesizer — webcam instrument |
| **Studio** | AIMA Productions |
| **Tagline** | Play sound with your hands and face |
| **Tone** | Chic · Precise · Mysterious · Playful |
| **Pillars** | Real-time motion capture · FM synthesis · Synesthesia · Gesture-first UI |
| **Aesthetic** | Neon light-writing on infinite void |

---

## Logo Assets

All logo files are in the `assets/` folder.

### Wordmark
| File | Use |
|---|---|
| `assets/pheremin-logo-cropped.png` | **Primary wordmark** — approved, tightly cropped, transparent background. Neon light-writing aesthetic. Use on dark (void) backgrounds only. Size at ≥48px tall. Apply `drop-shadow(0 0 14px rgba(232,121,249,.55))` for the neon glow effect. |
| `assets/pheremin-logo-knockout.png` | Full-canvas wordmark with glow bleed (600×443). Use when you need the full soft glow zone. |

### Circle Icons
| File | Use |
|---|---|
| `assets/pheremin-icon-large.png` | Large use — app icons, hero placements, splash screens |
| `assets/pheremin-icon-small.png` | Small use — favicons, 32–64px contexts |

### Parent Brand
| File | Use |
|---|---|
| `assets/aima-logo-noborder.png` | AIMA Productions parent brand — use in footers, about pages, colophons |

### Backdrop
| File | Use |
|---|---|
| `assets/web-cover.png` | **Signature backdrop** — persistent throughout the experience. Use as hero/splash background, `background-size: cover`, centered. |

### Logo Clearspace
- Maintain at minimum 1× the wordmark height as clearspace on all sides.
- Never place the wordmark on light or busy backgrounds.
- Never recolor, outline, or add drop shadows other than the approved neon glow.

---

## Color Tokens

### Void (Base Surfaces)
```css
--void-900: #060410   /* absolute backdrop — behind everything */
--void-800: #0a0712   /* page background */
--void-700: #0d0a16   /* stage / app shell */
--void-600: #120c20   /* raised panel */
--void-500: #170f26   /* panel inner / inputs */
--void-400: #1e152f   /* hovered surface */
```

### Neon Brand Spectrum
```css
/* Fuchsia — PRIMARY: wordmark, active glow, accent */
--fuchsia-300: #f5b8ff
--fuchsia-400: #e879f9   ← primary accent
--fuchsia-500: #d633e6
--fuchsia-600: #b21fc4

/* Violet — SECONDARY: knobs, callouts, focus rings */
--violet-300: #c8a8ff
--violet-400: #a064ff   ← secondary accent
--violet-500: #8b3df0
--violet-600: #6d28d9

/* Cyan — TERTIARY: info, version tags, eye nodes */
--cyan-400: #22d3ee   ← info accent
--cyan-500: #0bb6d6
```

### Signal (Live / Record)
```css
--signal-400: #ff4d4d   /* hand skeleton nodes, LIVE pulse */
--signal-500: #ef3b3b
--signal-rose: #f43f5e
--stop-700:   #7f1d1d   /* STOP button fill */
--stop-600:   #a32626
```

### Text
```css
--text-1: #e6dcf5   /* primary — lavender-white */
--text-2: #b7a9d4   /* secondary labels */
--text-3: #7d6fa0   /* muted / axis labels */
--text-4: #51466b   /* faint / disabled */
```

### Lines & Borders
```css
--line-1: rgba(160,100,255,0.14)   /* hairline panel border */
--line-2: rgba(160,100,255,0.32)   /* emphasized border */
--line-3: rgba(232,121,249,0.55)   /* active / focus border */
```

### Semantic Aliases
```css
--accent:        var(--fuchsia-400)
--accent-2:      var(--violet-400)
--accent-info:   var(--cyan-400)
--accent-live:   var(--signal-400)
--bg-page:       var(--void-800)
--bg-stage:      var(--void-700)
--surface-panel: var(--void-600)
--surface-input: var(--void-500)
--surface-hover: var(--void-400)
```

### Glow Recipes (box-shadow / drop-shadow)
```css
--glow-fuchsia: 0 0 16px rgba(232,121,249,0.55), 0 0 38px rgba(214,51,230,0.30)
--glow-violet:  0 0 14px rgba(160,100,255,0.50), 0 0 30px rgba(139,61,240,0.28)
--glow-cyan:    0 0 12px rgba(34,211,238,0.55)
--glow-signal:  0 0 14px rgba(255,77,77,0.6),   0 0 30px rgba(239,59,59,0.30)
```

---

## Typography

### Font Families
Load from Google Fonts:
```
https://fonts.googleapis.com/css2?family=Shadows+Into+Light&family=Marcellus&family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap
```

| Token | Family | Role |
|---|---|---|
| `--font-script` | Shadows Into Light | Wordmark only — long-exposure light-writing aesthetic |
| `--font-display` | Outfit | UI chrome, buttons, headings, section labels |
| `--font-mono` | JetBrains Mono | Telemetry, axis labels, readouts, body copy |
| `--font-serif` | Marcellus | Editorial accent — marketing, pull quotes |

### Type Scale
| Token | Size | Usage |
|---|---|---|
| `--fs-micro` | 9px | Axis ticks, version chips |
| `--fs-label` | 11px | Uppercase section labels (letter-spacing: 0.18em) |
| `--fs-tag` | 12px | Callout body text |
| `--fs-body` | 14px | Default body (JetBrains Mono) |
| `--fs-readout` | 16px | Knob / channel readouts |
| `--fs-h3` | 20px | Subsection headings |
| `--fs-h2` | 28px | Section headings |
| `--fs-h1` | 40px | Page headings |
| `--fs-display` | 64px | Hero / display |

### Label Convention
Uppercase mono labels are a core brand pattern:
```css
font-family: var(--font-mono);
font-size: 9–11px;
letter-spacing: 0.16–0.32em;
text-transform: uppercase;
color: var(--text-2) or var(--text-3);
```

---

## Spacing & Layout

### Spacing Scale (4px base)
```css
--space-1: 4px   --space-2: 8px    --space-3: 12px
--space-4: 16px  --space-5: 20px   --space-6: 24px
--space-8: 32px  --space-10: 40px  --space-12: 48px
--space-16: 64px
```

### Border Radii
```css
--radius-xs:   4px    /* tight chips */
--radius-sm:   6px    /* inputs, toggles */
--radius-md:   10px   /* buttons, cards */
--radius-lg:   14px   /* panels */
--radius-pill: 999px  /* nav bar, switches */
```

### Elevation / Shadows
```css
--shadow-panel: 0 8px 40px rgba(0,0,0,0.55), inset 0 1px 0 rgba(180,150,230,0.04)
--shadow-pop:   0 8px 40px rgba(0,0,0,0.7),  0 0 20px rgba(160,100,255,0.20)
--shadow-nav:   0 4px 24px rgba(0,0,0,0.6)
```

### Motion
```css
--ease-glide: cubic-bezier(0.4, 0, 0.2, 1)   /* standard — calm, no bounce */
--ease-out:   cubic-bezier(0.16, 1, 0.3, 1)  /* callout rise */
--dur-fast:   0.2s
--dur-base:   0.35s
--dur-slow:   0.5s
```

---

## Background Patterns
- **Page backdrop**: deep void `#060410`–`#0a0712` with subtle radial violet/fuchsia gradients at corners.
- **Signature backdrop**: `assets/web-cover.png` — fractal-geometric dark image, used persistently throughout the full experience.
- **Stage surfaces**: avoid pure black; use `--void-700` / `--void-600` for depth layering.

---

## Dos & Don'ts

| ✅ Do | ❌ Don't |
|---|---|
| Use the approved knockout wordmark PNG | Re-typeset "pheremin" in any font |
| Apply neon glows to active/focused elements | Use glows on inactive or background elements |
| Use void surfaces as backgrounds | Use white or light backgrounds |
| Use uppercase mono labels at 9–11px | Use title-case or lowercase for UI labels |
| Keep the signature backdrop consistent | Swap the backdrop per screen |
| Pair fuchsia (primary) with violet (secondary) | Introduce new brand colors |

---

## Files in This Package

| File | Contents |
|---|---|
| `README.md` | This document |
| `assets/pheremin-logo-cropped.png` | Approved wordmark (transparent) |
| `assets/pheremin-logo-knockout.png` | Full-canvas wordmark with glow |
| `assets/pheremin-icon-large.png` | Circle icon — large use |
| `assets/pheremin-icon-small.png` | Circle icon — small use |
| `assets/aima-logo-noborder.png` | AIMA Productions parent brand |
| `assets/web-cover.png` | Signature backdrop |
| `tokens/colors.css` | Full color token definitions |
| `tokens/typography.css` | Font imports + type tokens |
| `tokens/spacing.css` | Spacing, radii, shadows, motion |
