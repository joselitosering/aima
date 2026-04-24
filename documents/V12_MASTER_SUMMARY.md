# 🎬 AIMA Template System v12 — MASTER SUMMARY

**Status:** 🟢 Active Production | Multi-Template System  
**Date:** April 2026  
**Versions:** Homepage 12.5 · Article 12.1 · Project 12.0 · Music 12.2 · Gallery 11.5 (locked) · Careers 12.0 · Insights 12.0

---

## 📦 Complete Template Inventory

### 1. `homepage-v12_5.html` (3,335 lines | 188 KB)
The site's primary page. Most complex file in the system.
- Full AIMA brand system (nav, footer, all sections)
- `Organization` + `WebSite` + `WebPage` + `SearchAction` JSON-LD `@graph`
- Section IDs locked — never rename
- Latest articles + project cards wired to Sheets API
- Surgical edits only — do not restructure

### 2. `article-template-v12_1.html` (1,155 lines | 73 KB)
Base for all `/articles/aima-article-[slug].html` files.
- 12 `article:*` meta tags drive all dynamic content
- Floating share sidebar (left, 5 buttons)
- Floating TOC sidebar (right panel)
- `Article` JSON-LD with `mainEntityOfPage`, `ImageObject`, `dateModified`
- Prev/next nav cards auto-hide when tag is empty
- Paired with `aima-article-generator_skill.md` v1.1

### 3. `projects-template-v12.html` (1,574 lines | 97 KB)
Base for all `/projects/[name].html` standard case study pages.
- 7 `aima:*` meta tags for gallery scraper compatibility
- All hero/BTS/testimonial content loaded via GAS `doGet`
- `CreativeWork` JSON-LD
- 4-col BTS grid (9:16 ratio), mosaic gallery, testimonials grid
- Prev/next project nav cards (hidden when URLs absent)

### 4. `project-music-template-v12_2.html` (145 lines | 7 KB)
Extension of Project template for AIRA Music Label releases.
- `music.album` OG type + `MusicAlbum` JSON-LD
- `byArtist`, `recordLabel`, `contributor` fields
- Audio embed via GitHub raw or Dropbox `?dl=1`
- Logistics grid (3-col, recording industry phases)
- Extended footer copyright includes AIRA Music Label
- Footer version stamp: `v12.3 · aira.music`

### 5. `projects-gallery-template-v11_5.html` (1,109 lines | ~65 KB) — V11 LOCKED
Gallery index page. V11.5 is the current authoritative version — do not replace with a V12 build.
- All project cards Sheets-driven via `CONFIG.SHEETS_API_URL`
- Category pill filter slot (`data-cat-key`) preserved — activate at 13+ projects
- Mosaic grid, expand toggle via JS (not CSS nth-child)
- `.m-card.hidden { display:none }` required

### 6. `careers.html` (1,277 lines | ~78 KB)
EP Partner Program page and application form.
- EP tiers: Bronze / Silver / Gold
- Markup: up to 20% at point of sale
- Royalty: 10–15% perpetual (survives program exit)
- GAS form backend: `aima-ep-applications.gs` → Google Sheet
- `showSuccess` and `handleSubmit` must be in the same `<script>` block
- FAQ accordion: validate JS with `node --check`

### 7. `aima-all-articles.html` (1,161 lines | ~70 KB)
Insights index page — lists all published articles.
- Article cards loaded from Articles Sheets API
- Category filter slot preserved (activate at 13 articles)
- Static JSON fallback: update Sheet → fetch Web App URL → save JSON → upload

---

## 🎯 What Makes V12 Different from V10

### V10 Was
- Single template (articles only)
- 2,142 lines, 76 KB, zero dependencies
- Hardcoded prev/next nav in HTML
- No SEO structured data
- No floating sidebars
- No GAS integration
- No mobile fade-in fix
- No article generator skill

### V12 Is
- 7-template system covering every page type
- Full SEO block on every template (OG + Twitter Card + JSON-LD)
- Meta tag–driven prev/next (no HTML editing for nav)
- Floating share sidebar + TOC sidebar on articles and projects
- GAS-driven dynamic content on projects, gallery, insights, careers
- Always-on frosted-glass nav (no scroll toggling)
- Mobile fade-in fix baked into all templates
- Article generator skill v1.1 for automated article production
- AIRA Music Label template with audio embed and `MusicAlbum` schema

---

## 📊 Key Statistics

```
Total templates:     7 files
Total lines:         9,756 lines across all templates
Largest file:        homepage-v12_5.html (3,335 lines | 188 KB)
Smallest file:       project-music-template-v12_2.html (145 lines | 7 KB)
External APIs:       Google Sheets (via GAS Web Apps)
Build process:       None — static HTML + GAS
GitHub Pages ready:  All templates
Mobile responsive:   All templates
Next article ID:     005
```

---

## 🏗️ System Architecture

```
GitHub Pages (static HTML)
    │
    ├── index.html              ← homepage-v12_5.html base
    ├── insights.html           ← aima-all-articles.html base
    ├── gallery.html            ← projects-gallery-template-v11_5.html base
    ├── careers.html            ← careers.html (static + GAS form)
    │
    ├── articles/
    │   └── aima-article-[slug].html   ← article-template-v12_1.html base
    │
    └── projects/
        ├── [project].html      ← projects-template-v12.html base
        └── [music].html        ← project-music-template-v12_2.html base

Google Sheets (data layer)
    ├── Articles sheet     → insights.html + article nav cards
    ├── Projects sheet     → project pages + gallery
    ├── Audio sheet        → music project pages
    └── EP Applications    → careers form submissions

GAS Web Apps (API layer)
    ├── articles-api-v10.gs        → returns JSON article list
    ├── aima-sheets-api.gs         → returns project / gallery data
    └── aima-ep-applications.gs    → saves EP partner applications
```

---

## 🔩 Component Inventory

### Navigation (all pages)
```css
/* Always-on — never toggled by scroll */
background: rgba(6,8,16,0.60);
backdrop-filter: blur(20px);
```
- Order: Home · Services · Rates · Work · Process · About · Insights · Gallery
- Mobile hamburger: `padding-top:var(--nav-h,72px)` + `overflow-y:auto`

### Footer (`aima-footer-v12`, all pages)
- 4-column grid: Brand | Services | Company | Legal
- Logo: `<span class="ai">AI</span><span class="ma">MA</span>` — one parent span, no flex gap
- Back to Top: `window.scrollTo({top:0,behavior:'smooth'})` only
- Standard: `© 2026 AIMA · AI Media Agency · A Monkey Matters LLC Production · Wyoming LLC` · `v12.0 · aima.media`
- Music: adds `· AIRA Music Label` to copyright · `v12.3 · aira.music`

### SEO Block (all pages)

| Page | JSON-LD Schema |
|------|---------------|
| Homepage | `Organization` + `WebSite` + `WebPage` + `SearchAction` (`@graph`) |
| Article | `Article` with `mainEntityOfPage`, `ImageObject`, `dateModified` |
| Project | `CreativeWork` |
| Music Project | `MusicAlbum` with `byArtist`, `recordLabel`, `contributor` |
| Gallery / Insights / Careers | `WebPage` |

### Article Meta Tags (12 total)
```html
<meta name="article:id"           content="005"/>
<meta name="article:title"        content=""/>
<meta name="article:description"  content=""/>
<meta name="article:author"       content="Joselito Sering"/>
<meta name="article:publish-date" content="YYYY-MM-DD"/>
<meta name="article:read-time"    content="N"/>
<meta name="article:category"     content=""/>
<meta name="article:header-image" content="https://images.unsplash.com/photo-ID?w=1920"/>
<meta name="article:prev-url"     content=""/>
<meta name="article:prev-title"   content=""/>
<meta name="article:next-url"     content=""/>
<meta name="article:next-title"   content=""/>
```
Nav cards auto-hide when prev/next values are empty or `tbd`.

### Project Meta Tags (7 AIMA-specific)
```html
<meta name="aima:project_id"   content=""/>
<meta name="aima:client"       content=""/>
<meta name="aima:category"     content=""/>
<meta name="aima:tools"        content=""/>
<meta name="aima:date"         content="YYYY-MM-DD"/>
<meta name="aima:status"       content="Live"/>
<meta name="aima:deliverables" content=""/>
```

### Floating Sidebars (articles and projects)
- `#share-sidebar` — left FABs: Facebook · Twitter/X · LinkedIn · Email · Copy Link
- `#toc-sidebar` — right sticky panel: section anchor links

### Mobile Fade-in Fix (all templates — must be present)
```css
@media (max-width:768px) { .fade-in { opacity:1 !important; } }
```
```javascript
setTimeout(() => {
  document.querySelectorAll('.fade-in').forEach(el => el.style.opacity = '1');
}, 800);
```

### Article Content Structure (mandatory order)
1. `.article-lead` — hook + thesis, 2–3 glossary links
2. 4–6 `<h2 id="section-[slug]">` — `<span class="accent">` on key phrase
3. 2–3 callouts: info 💡 / warning ⚠️ / success ✓ / gold 🎙️
4. 1–2 pull quotes (`.pullquote`)
5. Article footer CTA (`.article-footer`)
6. References — MLA 9th, `[1]...[N]`, `data-number` attribute, all URLs live
7. Glossary — bidirectional links, alphabetical, min 6 terms
8. Author card (standard JS — do not change)
9. Services card (customise text per article)

### Read Time
`ceil(word_count / 200)` — always a whole number.

---

## 🗄️ GAS Rules

| Rule | Detail |
|------|--------|
| CORS preflight | `doOptions()` must return `ContentService.createTextOutput('')` |
| Redeploy | After any code change: Deploy → Manage Deployments → Edit → New Version (URL unchanged) |
| External fetch | `UrlFetchApp` requires installable trigger — not simple `onEdit` |
| Drive images | `https://drive.google.com/thumbnail?id=FILE_ID&sz=w1200` |
| Drive URL escaping | Never HTML-escape Drive URLs — `&` → `&amp;` breaks query parameters |
| Audio | GitHub raw URL or Dropbox `?dl=1` — Google Drive direct does not work in `<audio>` |
| Static JSON | Sheet → fetch Web App URL → save JSON → upload (avoids 15+ sec live API load) |

---

## 🖼️ Image Rules

| Use | Format |
|-----|--------|
| Drive thumbnails | `https://drive.google.com/thumbnail?id=FILE_ID&sz=w1200` |
| Article headers | `https://images.unsplash.com/photo-[ID]?w=1920` |
| OG cover | `assets/aima-og-cover.jpg` (1200×630px — pending creation) |
| Logo | `logo.png` at repo root (pending upload) |
| MidJourney params | `--ar 16:9 --v 6.1 --style raw --q 2` |

---

## 📝 Article Generator Skill v1.1

**File:** `aima-article-generator_skill.md`  
**Trigger:**
```
write an article on [TOPIC] · category [CATEGORY] · id [NNN] · 
points: [1. x 2. y 3. z] · tone [TONE] · prev [TITLE | URL] · next [TITLE | URL]
```
**Sequence:** Parse → Research (3+ sources) → Write → Proofread → References → Glossary → Build HTML → Validate → Output  
**Output:** `aima-article-[slug].html` — production-ready, upload immediately  
**Next ID:** 005

---

## ✅ What's Included vs V10

| Feature | v10 | v12 |
|---------|-----|-----|
| **Templates** | | |
| Homepage template | ✗ | ✓ |
| Article template | ✓ | ✓ (rebuilt) |
| Project template | ✗ | ✓ |
| Music project template | ✗ | ✓ |
| Gallery template | ✗ | ✓ (v11.5) |
| Careers template | ✗ | ✓ |
| Insights index template | ✗ | ✓ |
| **SEO** | | |
| Open Graph tags | Partial | ✓ All pages |
| Twitter Card tags | Partial | ✓ All pages |
| JSON-LD structured data | ✗ | ✓ All pages, typed per template |
| Article schema | ✗ | ✓ `Article` with `ImageObject` |
| Homepage schema | ✗ | ✓ `Organization` + `WebSite` + `SearchAction` |
| Music schema | ✗ | ✓ `MusicAlbum` |
| **Navigation** | | |
| Hardcoded prev/next HTML | ✓ | ✗ (meta tags only) |
| Meta tag–driven prev/next | ✗ | ✓ |
| Auto-hide empty nav cards | ✗ | ✓ |
| Always-on frosted nav | ✗ | ✓ |
| **Layout** | | |
| Floating share sidebar | ✗ | ✓ |
| Floating TOC sidebar | ✗ | ✓ |
| Mobile fade-in fix | ✗ | ✓ |
| Gold callout variant 🎙️ | ✗ | ✓ |
| **Data / API** | | |
| Google Sheets integration | ✗ | ✓ (projects, gallery, insights, careers) |
| GAS `doOptions` CORS fix | ✗ | ✓ |
| Static JSON fallback | ✗ | ✓ |
| **Production** | | |
| Article generator skill | ✗ | ✓ v1.1 |
| Python file validation block | ✗ | ✓ |
| JS `node --check` workflow | ✗ | ✓ |
| EP Partner Program | ✗ | ✓ |
| AIRA Music Label | ✗ | ✓ |

---

## 🔒 Locked Assets

| Asset | Status |
|-------|--------|
| Brand color tokens | 🔒 Locked |
| Brand fonts | 🔒 Locked |
| Nav order | 🔒 Locked |
| Footer structure | 🔒 Locked |
| Logo rendering rule | 🔒 Locked |
| Gallery template (v11.5) | 🔒 Locked at V11 |
| Homepage section IDs | 🔒 Locked |

---

## 📋 Outstanding Tasks (April 2026)

- [ ] Upload `logo.png` to repo root
- [ ] Create `assets/aima-og-cover.jpg` (1200×630px)
- [ ] Create per-project Twitter Card images
- [ ] Implement visitor counter post-launch (GAS + Sheets infrastructure ready)
- [ ] Activate category pill filters on `insights.html` at 13 articles
- [ ] Activate category pill filters on `gallery.html` at 13 projects

---

## 💡 Pro Tips

1. **Never edit master templates** — always duplicate first
2. **Validate every file** — run the Python check block before every push
3. **JS errors are silent** — always run `node --check` on `<script>` blocks
4. **Drive images break on `&amp;`** — never HTML-escape Drive URLs
5. **GAS changes need a new version** — redeploy after every code edit
6. **Static JSON beats live API** — use the save-JSON workflow for gallery/insights
7. **Mobile fade-in** — if opacity is stuck, the CSS + setTimeout fix is missing
8. **Back to Top** — must use `window.scrollTo`, never `getElementById('home')`

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Header image not loading | Verify URL in browser; check `?w=1920` present |
| Drive thumbnail broken | Check `&` is not `&amp;` |
| Audio not playing | Use GitHub raw or Dropbox `?dl=1` |
| Nav cards not hiding | Empty string or `tbd` in meta tag triggers auto-hide |
| Mobile menu overlaps content | `padding-top:var(--nav-h,72px)` on menu container |
| Fade-in stuck on mobile | CSS override + 800ms setTimeout both required |
| GAS returns CORS error | `doOptions()` must return `ContentService.createTextOutput('')` |
| JS behaves unexpectedly | `node --check` — apostrophes, stray `};`, HTML in `<script>` |
| File silently truncated | Python: `len(h)`, `'</body>' in h`, `'</html>' in h` |
| Mosaic breaks when filtered | Remove `#mosaic-grid[data-filtered]` `grid-column:span 1` block |

---

## 📚 Documentation Index

1. **README_V12.md** — Start here (quick overview)
2. **AIMA_TEMPLATE_USAGE_GUIDE_V12.md** — Step-by-step per template
3. **ARTICLE_DEPLOYMENT_CHECKLIST_V12.md** — Pre-deployment verification
4. **VERSION_HISTORY_V12.md** — Changelog v5 → v12
5. **This file** — Complete system summary

---

## ✨ Final Notes

V12 is a **complete, production-ready, multi-template system** for AI Media Agency.

Everything you need is included:
- ✓ 7 template files
- ✓ Article generator skill (v1.1)
- ✓ GAS scripts for all data layers
- ✓ Full SEO on every page type
- ✓ Brand system locked and consistent
- ✓ Documentation suite

**Build fast. Build consistently. Build for the long term.**

---

**System Version:** 12.x  
**Status:** 🟢 Active Production  
**Last Updated:** April 2026  
**Next Article ID:** 005  

**🎬 Ready to produce.**
