# AIMA V12 Documentation Suite
**AI Media Agency · Monkey Matters LLC · San Francisco, CA**  
**Version:** 12.x · **Status:** 🟢 Active Production · **Updated:** April 2026

---

> This suite replaces all V10 and V11 documentation.  
> V11 project-gallery template (`projects-gallery-template-v11_5.html`) remains active — skip V11 for all other page types.

---

# DOCUMENT INDEX

| # | Document | Purpose |
|---|----------|---------|
| 1 | README_V12 | Quick start overview |
| 2 | V12_MASTER_SUMMARY | Complete system inventory and architecture |
| 3 | ARTICLE_DEPLOYMENT_CHECKLIST | Pre-deployment verification (all page types) |
| 4 | AIMA_TEMPLATE_USAGE_GUIDE | Step-by-step authoring guide per template |

---

---

# 1 · README_V12

## What Is AIMA V12?

AIMA V12 is the current locked production system for **AI Media Agency** (`joselitosering.github.io/aima/`). It is a static GitHub Pages site backed by Google Sheets + Google Apps Script for dynamic content, with zero runtime build steps.

V12 consolidates all template types under a single brand system and a single deployment workflow.

---

## Brand System (Locked — Do Not Alter)

| Token | Value |
|-------|-------|
| Cyan | `#00D9F5` |
| Orange | `#FF5E20` |
| Gold | `#C8A84B` |
| Dark | `#060810` |
| Display font | Anton |
| Body font | DM Sans |
| Mono font | Courier Prime |

**Logo rule:** `<span class="fb-wordmark"><span class="ai">AI</span><span class="ma">MA</span></span>` — both spans inside one parent, no flex gap.

**Nav rule:** `rgba(6,8,16,0.60)` + `backdrop-filter:blur(20px)` — always-on, no scroll toggling.  
**Nav order:** Home · Services · Rates · Work · Process · About · Insights · Gallery

**Footer:** `aima-footer-v12` — 4-column grid: Brand | Services | Company | Legal.  
Copyright line: `© 2026 AIMA · AI Media Agency · A Monkey Matters LLC Production · Wyoming LLC`  
Version stamp: `v12.0 · aima.media`

---

## Template Inventory

| Template File | Page Type | Data Source |
|---------------|-----------|-------------|
| `homepage-v12_5.html` | Homepage / index | Static + GAS |
| `article-template-v12_1.html` | Articles / Insights posts | Static meta tags |
| `projects-template-v12.html` | Project / case study pages | Google Sheets via GAS |
| `project-music-template-v12_2.html` | AIRA Music Label releases | Google Sheets via GAS |
| `projects-gallery-template-v11_5.html` | Gallery index | Google Sheets via GAS |
| `careers.html` | Careers / EP Partner Program | GAS form → Google Sheet |
| `aima-all-articles.html` | Insights index | Google Sheets via GAS |

---

## Hosting & Infrastructure

| Layer | Tool |
|-------|------|
| Hosting | GitHub Pages — `joselitosering.github.io/aima/` |
| Data backend | Google Sheets + Google Apps Script Web Apps |
| Images | Google Drive thumbnails (`thumbnail?id=FILE_ID&sz=w1200`) |
| Audio | GitHub raw URLs or Dropbox `?dl=1` (NOT Google Drive direct) |
| Automation | n8n (zero-touch content pipelines) |

---

## Quick Start

```
1. Pick the correct template from the table above.
2. Duplicate the template file.
3. Replace all {{PLACEHOLDER}} values (meta tags first).
4. For Sheets-driven pages: deploy a new GAS Web App, paste the /exec URL.
5. Validate with Python len() + '</body>' in h + '</html>' in h.
6. Push to GitHub /aima root or /articles/ or /projects/ subdirectory.
7. Wait ~2 min for GitHub Pages to build.
8. Test all links, images, and nav on mobile + desktop.
```

---

---

# 2 · V12_MASTER_SUMMARY

## Architecture Overview

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
    ├── Articles sheet          → insights.html + article nav cards
    ├── Projects sheet          → project pages + gallery
    ├── Audio Projects sheet    → music project pages
    └── EP Applications sheet   → careers form submissions

GAS Web Apps (API layer)
    ├── articles-api.gs         → doGet returns JSON article list
    ├── aima-sheets-api.gs      → doGet returns project/gallery data
    └── aima-ep-applications.gs → doPost saves EP partner applications
```

---

## Component Inventory

### Navigation (all pages)
- Fixed, always-on frosted glass: `rgba(6,8,16,0.60)` + `backdrop-filter:blur(20px)`
- Mobile hamburger: `padding-top:var(--nav-h,72px)` + `overflow-y:auto`
- Nav items: Home · Services · Rates · Work · Process · About · Insights · Gallery
- No scroll toggling. No dynamic class changes on scroll.

### Footer (all pages — `aima-footer-v12`)
- 4-column grid: Brand | Services | Company | Legal
- Back to Top: `window.scrollTo({top:0,behavior:'smooth'})` — NOT `getElementById('home')`
- Copyright + version stamp in `.footer-bottom`
- Music pages use: `© 2026 AIMA · AI Media Agency · AIRA Music Label · A Monkey Matters LLC Production · Wyoming LLC` and `v12.3 · aira.music`

### Floating Sidebars (articles and projects)
- **Left** `#share-sidebar` — 5 FAB share buttons (Facebook, Twitter/X, LinkedIn, Email, Copy Link)
- **Right** `#toc-sidebar` — sticky table of contents, section links

### SEO Block (all page types)
All four core templates carry a complete SEO block:

| Page Type | JSON-LD Schema |
|-----------|---------------|
| Homepage | `Organization` + `WebSite` + `WebPage` + `SearchAction` |
| Article | `Article` with `mainEntityOfPage`, `ImageObject`, `dateModified` |
| Project | `CreativeWork` |
| Music project | `MusicAlbum` with `byArtist`, `recordLabel`, `contributor` |

Open Graph + Twitter Card tags are present on all templates.

### Article-Specific Components
- `.article-lead` — bold hook paragraph, larger font
- `h2[id="section-*"]` — section anchors for TOC
- `.callout` — info (💡) / warning (⚠️) / success (✓) / gold (🎙️)
- `.pullquote` → `.pullquote-text` + `.pullquote-attribution`
- `.glossary-term` + `#glossary-[term]` — bidirectional anchor links
- Article nav cards: `#art-prev-card` / `#art-next-card` (hidden if `tbd`)
- Read time: `ceil(word_count / 200)` minutes

### Project-Specific Components
- Data loaded via `doGet` from GAS Web App on page load
- BTS grid: `4-col, 9:16 ratio`
- Testimonials grid
- Project nav cards: `#proj-prev-card` / `#proj-next-card`
- Mosaic gallery: all images rendered to DOM upfront; `data-idx >= 8` hidden, toggled via JS

### Music Project Additional Components
- Audio embed: GitHub raw URL or Dropbox `?dl=1` in `<audio>` tag
- `MusicAlbum` JSON-LD with `byArtist`, `recordLabel`, `contributor`
- Logistics grid: 3-col recording industry phases
- Ambient tags: `.amb-tag.cyan`, `.amb-platform`

### Careers Page
- EP Partner Program: Bronze / Silver / Gold tiers
- Royalty structure: up to 20% markup at point of sale + 10–15% perpetual royalty
- Form POSTs to GAS (`aima-ep-applications.gs`) → Google Sheet
- `showSuccess` must be in the same `<script>` block as `handleSubmit`
- FAQ accordion: JS syntax must be validated with `node --check`

### Gallery / Insights Index Pages
- Category pill filters: slot preserved with `data-cat-key` — activate at 13+ articles
- Mosaic grid: remove `#mosaic-grid[data-filtered]` block if any filter active breaks layout
- Cards with missing images: `:has(img[src=""])` suppresses broken layout
- `.m-card.hidden { display:none }` required for filter hide-class

---

## GAS Rules (apply to all deployments)

- `doOptions()` must return `ContentService.createTextOutput('')` for CORS preflight
- After any GAS code change: Deploy → Manage Deployments → Edit → New Version
- `UrlFetchApp` requires installable trigger (not simple `onEdit`) for external fetching
- Drive images: `https://drive.google.com/thumbnail?id=FILE_ID&sz=w1200`
- Never HTML-escape Drive URLs — `&` → `&amp;` breaks query parameters
- Static JSON workflow: update Sheet → open Web App URL → save JSON → upload to GitHub (avoids 15+ sec live API load)

---

## Article ID Sequence
Next available ID as of April 2026: **005**  
Format: zero-padded 3-digit integer — `001`, `002`, `003`...

---

## Outstanding Tasks (as of April 2026)
- [ ] Upload `logo.png` to repo root
- [ ] Create `assets/aima-og-cover.jpg` (1200×630px)
- [ ] Create per-project Twitter Card images
- [ ] Implement visitor counter (post-launch, uses existing GAS infrastructure)
- [ ] Activate category pill filters on `insights.html` at 13 articles

---

---

# 3 · ARTICLE_DEPLOYMENT_CHECKLIST

Use this checklist for every new page before pushing to GitHub. Sections marked **[ALL]** apply to every page type. Sections marked by page type apply only to that template.

---

## PRE-AUTHORING

- [ ] Correct template selected from inventory
- [ ] File duplicated — original template untouched
- [ ] File renamed: `aima-article-[slug].html` (articles) or `[project-name].html` (projects)
- [ ] [Articles] Article ID assigned — next sequential, zero-padded (`005`, `006`...)
- [ ] [Sheets-driven] New GAS Web App deployed; `/exec` URL on hand

---

## META TAGS [ALL]

- [ ] `<title>` — unique, descriptive, under 60 chars
- [ ] `<meta name="description">` — 150–160 chars
- [ ] `<meta name="keywords">` — 5–8 relevant terms
- [ ] `<link rel="canonical">` — full absolute URL to live page
- [ ] Open Graph: `og:title`, `og:description`, `og:image`, `og:url`, `og:type`
- [ ] Twitter Card: `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`
- [ ] JSON-LD block present and correct schema type for this page

### Article-specific meta
- [ ] `article:id` — matches assigned ID
- [ ] `article:title` — matches `<title>`
- [ ] `article:description` — matches `<meta name="description">`
- [ ] `article:author` — `Joselito Sering`
- [ ] `article:publish-date` — `YYYY-MM-DD` format
- [ ] `article:read-time` — `ceil(word_count / 200)` whole number
- [ ] `article:category` — one of: Technology · Business · Creative · Social Impact
- [ ] `article:header-image` — valid Unsplash URL (`https://images.unsplash.com/photo-[ID]?w=1920`)
- [ ] `article:prev-url` — full URL or omitted if first article
- [ ] `article:prev-title` — matching title or omitted
- [ ] `article:next-url` — full URL or omitted if latest article
- [ ] `article:next-title` — matching title or omitted

---

## NAVIGATION [ALL]

- [ ] Nav bar present — frosted glass, always-on
- [ ] Nav order correct: Home · Services · Rates · Work · Process · About · Insights · Gallery
- [ ] All nav links resolve (no 404s)
- [ ] Mobile hamburger opens and closes
- [ ] Mobile menu clears fixed nav (no overlap): `padding-top:var(--nav-h,72px)`
- [ ] `overflow-y:auto` on mobile menu

---

## FOOTER [ALL]

- [ ] 4-column grid: Brand | Services | Company | Legal
- [ ] Logo rendered correctly — `AI` white + `MA` cyan, no gap
- [ ] Back to Top uses `window.scrollTo({top:0,behavior:'smooth'})`
- [ ] Copyright line correct for page type (AIRA music pages use extended copyright)
- [ ] Version stamp present (`v12.0 · aima.media` or `v12.3 · aira.music`)
- [ ] All footer links resolve

---

## ARTICLE CONTENT CHECKLIST [Articles only]

- [ ] `.article-lead` paragraph present (hook + thesis, larger font)
- [ ] 4–6 `<h2>` sections, each with `id="section-[slug]"`
- [ ] Key phrase in each `<h2>` wrapped in `<span class="accent">`
- [ ] TOC sidebar links match `h2` ids exactly
- [ ] Share sidebar present (5 buttons)
- [ ] 2–3 callout boxes, mixed types (💡 ⚠️ ✓ 🎙️)
- [ ] 1–2 pull quotes (`.pullquote`)
- [ ] Article footer CTA (`.article-footer`) customised for this article
- [ ] Author card populated
- [ ] Services card text customised for this article topic

### References
- [ ] Minimum 6 real, verifiable sources
- [ ] MLA 9th edition format, numbered `[1]...[N]`
- [ ] All URLs tested — no 404s
- [ ] Mix of source types (journal, news, official, book, etc.)
- [ ] `data-number` attribute on each reference `<li>`

### Glossary
- [ ] Minimum 6 technical terms defined
- [ ] Each term linked on first mention only: `<a href="#glossary-[term]" class="glossary-term" id="mention-[term]">`
- [ ] Each glossary entry has back-link: `<a href="#mention-[term]" class="back-link">↑ Back to text</a>`
- [ ] No term linked more than once in body
- [ ] Glossary entries in alphabetical order

### Article Navigation Cards
- [ ] `#art-prev-card` — hidden if no previous article
- [ ] `#art-next-card` — hidden if no next article
- [ ] Both card titles populated from meta tags
- [ ] "All Articles" card links to `https://joselitosering.github.io/aima/insights.html`

---

## PROJECT PAGE CHECKLIST [projects-template-v12 and project-music-template-v12_2]

- [ ] `SHEETS_API_URL` replaced with new deployment `/exec` URL
- [ ] GAS Web App deployed as: Execute as Me / Access Anyone
- [ ] `doGet` and `doOptions` both present in GAS script
- [ ] Content loads correctly in browser (check console — no CORS errors)
- [ ] Hero image loads (Drive thumbnail format)
- [ ] BTS grid renders (9:16 ratio, 4-col)
- [ ] Testimonials grid: placeholder shown if no data
- [ ] Mosaic gallery: all images rendered upfront; extras hidden not removed
- [ ] `#proj-prev-card` and `#proj-next-card` hidden if URLs not provided
- [ ] [Music only] Audio player functional — GitHub raw or Dropbox `?dl=1` URL
- [ ] [Music only] `MusicAlbum` JSON-LD populated correctly

---

## GALLERY / INSIGHTS INDEX [gallery.html and insights.html]

- [ ] GAS API URL configured
- [ ] Cards load from Sheets data
- [ ] Filter slot (`data-cat-key`) preserved even if filters inactive
- [ ] `.m-card.hidden { display:none }` CSS present
- [ ] `#mosaic-grid[data-filtered]` block removed (prevents mosaic breakage)
- [ ] `:has(img[src=""])` rule present (suppresses broken cards)

---

## CAREERS PAGE [careers.html]

- [ ] GAS endpoint (`aima-ep-applications.gs`) deployed and URL correct
- [ ] Form `handleSubmit` and `showSuccess` in same `<script>` block
- [ ] FAQ accordion JS validated (`node --check`)
- [ ] Fade-in fix present: `@media (max-width:768px) { .fade-in { opacity:1 !important; } }` + 800ms setTimeout fallback
- [ ] TOC displays correctly
- [ ] Hero text aligned correctly

---

## JAVASCRIPT VALIDATION [ALL]

- [ ] Extract all `<script>` blocks, write to `/tmp/check.js`, run `node --check /tmp/check.js`
- [ ] No apostrophes inside single-quoted strings
- [ ] No stray `};` lines
- [ ] No HTML inside `<script>` tags
- [ ] No orphaned variables from removed features
- [ ] IntersectionObserver fade-in: `@media (max-width:768px)` override + 800ms fallback present

---

## FILE INTEGRITY VALIDATION [ALL]

Run this Python check before pushing:

```python
with open('filename.html', encoding='utf-8') as f:
    h = f.read()

checks = {
    'file length > 10000':     len(h) > 10000,
    'closing body tag':        '</body>' in h,
    'closing html tag':        '</html>' in h,
    'nav bar present':         'backdrop-filter:blur' in h,
    'footer present':          'aima-footer' in h or 'footer-bottom' in h,
    'canonical tag':           'rel="canonical"' in h,
    'og:image present':        'og:image' in h,
    'json-ld present':         'application/ld+json' in h,
}

for label, result in checks.items():
    print(f"{'✅' if result else '❌'} {label}")
```

All checks must show ✅ before pushing.

---

## POST-DEPLOY VERIFICATION [ALL]

- [ ] Page loads at live URL (wait ~2 min after push)
- [ ] Header image displays correctly
- [ ] No broken image icons
- [ ] All internal links work (nav, footer, article/project nav cards)
- [ ] All external links open (references, social shares)
- [ ] Mobile view tested (320px minimum width)
- [ ] No horizontal scroll on mobile
- [ ] Console: zero errors, zero CORS failures
- [ ] Share buttons functional
- [ ] Back to top works
- [ ] Floating sidebars visible on desktop, hidden/collapsed on mobile

---

---

# 4 · AIMA_TEMPLATE_USAGE_GUIDE

## Overview

This guide covers how to author a new page using each V12 template. Follow the section for the page type you are creating.

---

## A · Homepage (`homepage-v12_5.html`)

**Base file:** `/mnt/project/homepage-v12_5.html`  
**Live page:** `https://joselitosering.github.io/aima/index.html`

The homepage is the most complex file (~183K chars). **Never restructure it.** Surgical edits only.

### Section IDs (do not rename)
`#home` · `#services` · `#rates` · `#work` · `#process` · `#about` · `#insights` · `#gallery` · `#contact` · `#tos` · `#privacy` · `#refund` · `#licensing` · `#cookies`

### What changes per update
- Hero headline and subtext
- Featured project cards in `#work`
- Latest article cards in `#insights` (pull from Sheets API or update manually)
- Rates table values
- Team/about copy

### SEO block
Schema: `Organization` + `WebSite` + `WebPage` + `SearchAction` in one `@graph` array.  
Update: `dateModified` field each time the page changes.

### Editing rules
1. Open `homepage-v12_5.html` from project.
2. Make a working copy; do not edit the project file directly.
3. Use `str.replace(old, new, 1)` with `assert old in h` guard.
4. After edit, run Python validation block.
5. Verify with `node --check` on extracted script blocks.

---

## B · Articles (`article-template-v12_1.html`)

**Base file:** `/mnt/project/article-template-v12_1.html`  
**Output pattern:** `articles/aima-article-[slug].html`  
**Skill file:** `/mnt/project/aima-article-generator_skill.md`

### Command format
```
write an article on [TOPIC] · category [CATEGORY] · id [NNN] · points: [1. x 2. y 3. z] · tone [TONE] · prev [TITLE | URL] · next [TITLE | URL]
```

**Tone options:** analytical · persuasive · instructional · editorial · narrative  
**If prev/next unknown:** use `tbd` — nav card hidden automatically.

### Authoring sequence
1. Parse command — extract all fields first.
2. Web-search the topic (minimum 3 sources, prioritise recency).
3. Write full article following Content Rules.
4. Proofread: clarity, consistency, accuracy, tone, brand voice (humane technology).
5. Generate MLA 9th references + bidirectional glossary.
6. Build complete HTML from skill shell.
7. Run Validation Checklist (Section 3 above).
8. Output as `aima-article-[slug].html`.

### The 12 meta tags to fill
```html
<meta name="article:id"           content="005"/>
<meta name="article:title"        content="Your Title Here"/>
<meta name="article:description"  content="150–160 char description."/>
<meta name="article:author"       content="Joselito Sering"/>
<meta name="article:publish-date" content="2026-04-23"/>
<meta name="article:read-time"    content="8"/>
<meta name="article:category"     content="Technology"/>
<meta name="article:header-image" content="https://images.unsplash.com/photo-ID?w=1920"/>
<meta name="article:prev-url"     content="https://joselitosering.github.io/aima/articles/prev.html"/>
<meta name="article:prev-title"   content="Previous Article Title"/>
<meta name="article:next-url"     content="tbd"/>
<meta name="article:next-title"   content="tbd"/>
```

### Content structure (mandatory order)
1. `.article-lead` — hook + thesis, 2–3 glossary links
2. 4–6 `<h2 id="section-[slug]">` sections
3. 2–3 callout boxes (mixed types)
4. 1–2 pull quotes
5. Article footer CTA (`.article-footer`)
6. References (MLA 9th, `[1]...[N]`, `data-number` attribute)
7. Glossary (bidirectional links, alphabetical)
8. Author card (standard JS — no changes)
9. Services card (customise text per article)

### Mobile fix (baked into shell — verify present)
```css
@media (max-width:768px) { .fade-in { opacity:1 !important; } }
```
```javascript
setTimeout(() => {
  document.querySelectorAll('.fade-in').forEach(el => el.style.opacity = '1');
}, 800);
```

### Google Sheets sync (after upload)
1. Add article GitHub URL to Column B in Articles sheet.
2. Run `updateArticleFromUrl(rowNumber)` in GAS — metadata auto-fills.
3. Manually set prev/next in adjacent rows.
4. Copy generated full URL from Column O.

---

## C · Project Pages (`projects-template-v12.html`)

**Base file:** `/mnt/project/projects-template-v12.html`  
**Output pattern:** `projects/[project-name].html`

### Setup sequence
1. Copy `projects-template-v12.html` → rename `projects/[name].html`.
2. Replace `SHEETS_API_URL` constant at top of script block with new `/exec` URL.
3. Deploy new GAS script (copy `aima-sheets-api.gs`, create new Apps Script project).
4. Deploy as Web App: Execute as Me / Access Anyone.
5. Populate Google Sheet with project data (all columns).
6. Push HTML to GitHub.
7. Test: open page, check console for successful data load.

### What is Sheets-driven (do not hardcode)
Hero image · project title · client · year · deliverables · budget · timeline · BTS images · testimonials · prev/next project URLs and titles.

### Sections and their IDs
`#overview` · `#brief` · `#process` · `#deliverables` · `#bts` · `#gallery` · `#testimonials` · `#contact`

### BTS grid
4-column, 9:16 aspect ratio. Images from Drive thumbnails.  
Format: `https://drive.google.com/thumbnail?id=FILE_ID&sz=w1200`

### Mosaic gallery
Render all images to DOM on load. Hide `data-idx >= 8` via `style="display:none"`. Toggle via JS (not CSS `nth-child` patterns).  
Do not use `#mosaic-grid[data-filtered]` with `grid-column:span 1`.

### Display filters
Auto-hide empty BTS / gallery / testimonial sections when Sheets data is absent — controlled by `populateProject()`.

### JSON-LD schema
`CreativeWork` — update `name`, `description`, `url`, `image`, `dateCreated`, `producer`.

---

## D · Music Project Pages (`project-music-template-v12_2.html`)

**Base file:** `/mnt/project/project-music-template-v12_2.html`  
**Output pattern:** `projects/[release-name].html`

### All rules from Section C apply, plus:

### Audio embed
```html
<audio controls>
  <source src="https://raw.githubusercontent.com/.../track.mp3" type="audio/mpeg">
</audio>
```
Use GitHub raw URL or Dropbox `?dl=1`. Google Drive direct links do not work in `<audio>`.

### Footer variant
```html
<p>© 2026 AIMA · AI Media Agency · AIRA Music Label · A Monkey Matters LLC Production · Wyoming LLC</p>
<span>v12.3 · aira.music</span>
```

### JSON-LD schema
`MusicAlbum` with:
```json
{
  "@type": "MusicAlbum",
  "byArtist": { "@type": "MusicGroup", "name": "Artist Name" },
  "recordLabel": { "@type": "Organization", "name": "AIRA Music Label" },
  "contributor": [...]
}
```

### Additional components
- Logistics grid: 3-col, recording industry phases (`.logistics-card` — cyan / orange / gold / green)
- Timeline: `.tl-row` with `.tl-phase`, `.tl-task`, `.tl-detail`
- Ambient tags: `.amb-tag.cyan` + `.amb-platform`

---

## E · Gallery (`projects-gallery-template-v11_5.html`)

**Base file:** `/mnt/project/projects-gallery-template-v11_5.html`  
**Note:** V11_5 is the current active version — do not replace with V12.

### GAS configuration
Replace `CONFIG.SHEETS_API_URL` with deployed `/exec` URL.  
All project cards are Sheets-driven — populate the Projects sheet first.

### Filter system
Category pill filters use `data-cat-key` attributes.  
Activate only when 13+ projects are live. Do not remove the slot — it is preserved in markup.

### Layout fixes (must be present)
```css
.m-card.hidden { display: none; }
```
Remove any CSS block that targets `#mosaic-grid[data-filtered]` with `grid-column:span 1`.  
Add `:has(img[src=""])` rule to suppress broken card layout.

### Expand button
Toggle `.mi-extra` class via JS. Render all items to DOM upfront. Do not use CSS `nth-child` hide patterns.

---

## F · Insights Index (`aima-all-articles.html`)

**Base file:** `/mnt/project/aima-all-articles.html`  
**Live page:** `https://joselitosering.github.io/aima/insights.html`

### Data source
Articles API (GAS Web App from `articles-api-v10.gs`).  
Static JSON fallback: update Sheet → fetch Web App URL → save JSON → upload to GitHub.

### Article card fields (from Sheets)
Title · Description · Category · Author · Publish Date · Read Time · Header Image · Article URL

### Category filter slot
`data-cat-key` on each card. Filter UI slot preserved.  
Activate at 13 articles — do not activate early.

### Visitor counter
Deferred post-launch. Infrastructure (GAS + Sheets) already in place.

---

## G · Careers (`careers.html`)

**Base file:** `/mnt/project/careers.html`  
**Live page:** `https://joselitosering.github.io/aima/careers.html`

### Form backend
GAS script: `aima-ep-applications.gs`  
Form POSTs to Google Forms backend with `mode:'no-cors'`.  
`showSuccess` must live in the same `<script>` block as `handleSubmit` — do not separate.

### EP Partner Program tiers

| Tier | Requirement | Markup | Royalty |
|------|-------------|--------|---------|
| Bronze | Entry | Up to 20% | 10% perpetual |
| Silver | Volume threshold | Up to 20% | 12% perpetual |
| Gold | Top tier | Up to 20% | 15% perpetual |

Royalties survive program exit indefinitely.

### Known fixes (must be present)
```css
/* Fade-in mobile fix */
@media (max-width:768px) { .fade-in { opacity:1 !important; } }
```
```javascript
// FAQ accordion — validate with node --check after any change
// setTimeout fallback for fade-in
setTimeout(() => {
  document.querySelectorAll('.fade-in').forEach(el => el.style.opacity='1');
}, 800);
```

---

## General Engineering Rules (apply everywhere)

### File editing
- Always validate large HTML with Python: `len()`, `'</body>' in h`, `'</html>' in h`
- `str.replace(old, new, 1)` with `assert old in h` guard — never silent failures
- `create_file` with full content is more reliable than bash heredocs for files ~190KB+
- `re.compile` with `re.DOTALL` and section ID matching for reordering HTML sections

### JavaScript debugging
- Always run `node --check` on extracted script blocks when JS behaviour is broken
- Common silent killers: apostrophe inside single-quoted strings · stray `};` · HTML inside `<script>` · orphaned variables

### Image embeds
- Drive thumbnail: `https://drive.google.com/thumbnail?id=FILE_ID&sz=w1200`
- Never pass Drive URLs through HTML-escaping — `&` → `&amp;` breaks parameters
- Audio: GitHub raw or Dropbox `?dl=1` only

### CSS patterns
- ep-prefixed class names prevent namespace collision with homepage components
- Back-to-top: `window.scrollTo({top:0,behavior:'smooth'})` — not `getElementById('home')`
- IntersectionObserver fade-in mobile fix: CSS override + 800ms setTimeout fallback

---

## Article Generator Skill — Quick Reference

Full skill file: `/mnt/project/aima-article-generator_skill.md`

**Trigger:**
```
write an article on [TOPIC] · category [CATEGORY] · id [NNN] · points: [1. 2. 3.] · tone [TONE] · prev [TITLE | URL] · next [TITLE | URL]
```

**Output:** `aima-article-[slug].html` — production-ready, no editing needed before upload.

**Sequence:** Parse → Research (web search, 3+ sources) → Write → Proofread → References → Glossary → Build HTML → Validate → Output.

**Next article ID:** 005

---

*End of AIMA V12 Documentation Suite*  
*© 2026 AIMA · AI Media Agency · A Monkey Matters LLC Production*  
*v12.0 · aima.media*
