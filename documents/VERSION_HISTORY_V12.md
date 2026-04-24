# AIMA Template System — Version History

## v12 (CURRENT — April 2026) 🟢 Active Production

**Status:** Active | Multi-Template System | Full SEO | GAS-Driven

### Overview
Full site template system. Seven templates covering every AIMA page type. Complete SEO stack on all templates. Meta tag–driven navigation. GAS-powered dynamic content on five page types. Article generator skill v1.1.

### Templates in V12

| Template | Sub-version | Lines | Size |
|----------|-------------|-------|------|
| Homepage | 12.5 | 3,335 | 188 KB |
| Article | 12.1 | 1,155 | 73 KB |
| Project (standard) | 12.0 | 1,574 | 97 KB |
| Music Project | 12.2 | 145 | 7 KB |
| Gallery | 11.5 (locked) | 1,109 | ~65 KB |
| Careers | 12.0 | 1,277 | ~78 KB |
| Insights Index | 12.0 | 1,161 | ~70 KB |

### Key Additions vs V10

**SEO & Structured Data**
- Full SEO block on every page type (previously partial or absent)
- `Article` JSON-LD with `mainEntityOfPage`, `ImageObject`, `dateModified`
- `Organization` + `WebSite` + `WebPage` + `SearchAction` `@graph` on homepage
- `CreativeWork` JSON-LD on project pages
- `MusicAlbum` JSON-LD with `byArtist`, `recordLabel`, `contributor`
- Open Graph and Twitter Card tags on all page types

**Article Template (v12.1)**
- Meta tag count: 12 (up from 8 in v10)
- Prev/next driven by `article:prev-url`, `article:prev-title`, `article:next-url`, `article:next-title` meta tags
- Nav cards auto-hide when values are empty or `tbd`
- Floating share sidebar (`#share-sidebar`, left, 5 buttons)
- Floating TOC sidebar (`#toc-sidebar`, right panel)
- File naming convention: `aima-article-[slug].html`
- Gold callout variant 🎙️ added
- Unsplash image param: `?w=1920` (removed `&q=80`)

**Project Templates (v12.0 / v12.2)**
- 7 `aima:*` meta tags for gallery scraper compatibility
- All content loaded via GAS `doGet` / `doOptions`
- `doOptions()` CORS preflight fix implemented
- Music template: audio embed, logistics grid, AIRA footer variant
- Music template: `og:type` = `music.album`

**Navigation & Layout**
- Always-on frosted-glass nav: `rgba(6,8,16,0.60)` + `backdrop-filter:blur(20px)` — no scroll toggling
- Mobile menu: `padding-top:var(--nav-h,72px)` + `overflow-y:auto` — clears fixed nav
- Mobile fade-in fix: CSS `opacity:1 !important` + 800ms `setTimeout` fallback
- Back to Top corrected: `window.scrollTo({top:0,behavior:'smooth'})` throughout

**New Page Types**
- Homepage (`homepage-v12_5.html`) — full brand page with locked section IDs
- Gallery index (`projects-gallery-template-v11_5.html`) — Sheets-driven, V11.5 locked
- Careers (`careers.html`) — EP Partner Program with GAS form backend
- Insights index (`aima-all-articles.html`) — article listing, category filter slot

**Tooling**
- Article generator skill v1.1 (`aima-article-generator_skill.md`)
- Python file integrity validation block
- `node --check` JS validation workflow documented
- Static JSON fallback workflow for gallery and insights

### Changelog

#### v12.5 — Homepage (April 2026)
- **ADDED:** `SearchAction` in JSON-LD `@graph`
- **ADDED:** `og:locale` and `og:site_name`
- **FIXED:** Section ID lock documented
- **UPDATED:** `dateModified` field

#### v12.2 — Music Project Template (March 2026)
- **ADDED:** `MusicAlbum` JSON-LD with `byArtist`, `recordLabel`, `contributor`
- **ADDED:** `og:type` = `music.album`
- **ADDED:** Audio embed pattern (GitHub raw / Dropbox `?dl=1`)
- **ADDED:** Logistics grid (3-col, recording phases)
- **ADDED:** AIRA footer variant (`v12.3 · aira.music`)

#### v12.1 — Article Template (March 2026)
- **ADDED:** `article:prev-url`, `article:prev-title`, `article:next-url`, `article:next-title` meta tags
- **ADDED:** Auto-hide logic for empty nav cards
- **ADDED:** Floating `#share-sidebar` (left) and `#toc-sidebar` (right)
- **ADDED:** Gold callout variant (`.callout.gold`)
- **ADDED:** `Article` JSON-LD with `mainEntityOfPage` and `ImageObject`
- **CHANGED:** File naming to `aima-article-[slug].html`
- **CHANGED:** Header image param from `?w=1920&q=80` to `?w=1920`
- **FIXED:** Mobile fade-in: CSS override + 800ms setTimeout

#### v12.0 — Project, Careers, Insights, Gallery (March 2026)
- **ADDED:** `aima:*` meta tag block for gallery scraper
- **ADDED:** `CreativeWork` JSON-LD
- **ADDED:** `doOptions()` CORS preflight fix across all GAS scripts
- **ADDED:** Static JSON fallback workflow
- **ADDED:** EP Partner Program tiers and GAS form backend
- **ADDED:** Category pill filter slot (deferred activation)
- **FIXED:** Back to Top: `window.scrollTo` replaces `getElementById('home')`
- **FIXED:** Mosaic expand: JS toggle, all images pre-rendered to DOM
- **FIXED:** `.m-card.hidden { display:none }` required rule documented
- **FIXED:** `#mosaic-grid[data-filtered]` `grid-column:span 1` removed

---

## v11 (February–March 2026) — Superseded

**Status:** Archived | Replaced by V12 (except gallery — see note)

> ⚠️ `projects-gallery-template-v11_5.html` remains active and locked.
> All other V11 templates are superseded by V12.

### Overview
First multi-template attempt. Introduced project pages, gallery index, and GAS integration. Article template rebuilt with AIMA nav and footer. No structured data. Navigation still partially hardcoded.

### Key Features Added in V11
- Project page template (first version)
- Gallery index template (v11.5 is current locked)
- GAS `doGet` integration for project data
- Floating share sidebar (articles)
- TOC sidebar (articles)
- `aima-article-generator_skill.md` v1.0
- Article file naming: `aima-article-[slug].html`

### Issues Resolved in V12
- No JSON-LD structured data
- Prev/next nav still partially hardcoded
- No `doOptions()` CORS preflight in GAS
- No mobile fade-in fix
- Back to Top used `getElementById('home')` in some templates
- No `aima:*` meta tags for gallery scraper

### V11 Sub-versions
| Sub-version | Template | Notes |
|-------------|----------|-------|
| v11.5 | Gallery | 🔒 Locked, current active |
| v11.3 | Music project | Superseded by v12.2 |
| v11.0 | Article | Superseded by v12.1 |
| v11.0 | Project | Superseded by v12.0 |

---

## v10 (March 22, 2026) — Archived

**Status:** Archived | Article template only | Replaced by v12.1

### Overview
Complete, stable article template with AIMA branding. Zero external dependencies. Hardcoded navigation. No SEO structured data. Single-template scope — articles only.

### Key Features
- Full AIMA navigation and footer (articles only)
- AIMA wordmark, Gallery link, pulse animation
- Hardcoded prev/next navigation (edit HTML directly)
- Header image auto-loaded from meta tag
- 8 `article:*` meta tags
- Callout boxes (info, warning, success)
- Pull quotes, glossary, TOC
- Bitcoin tip jar
- Zero external dependencies

### File Stats
- Lines: 2,142
- Size: 76 KB
- Dependencies: 0

### What V10 Lacked (resolved in V12)
- ✗ JSON-LD structured data
- ✗ Floating share sidebar
- ✗ Floating TOC sidebar
- ✗ Meta tag–driven prev/next nav
- ✗ Mobile fade-in fix
- ✗ Prev/next meta tags (4 of 12 were missing)
- ✗ Project, gallery, careers, insights, homepage templates
- ✗ Article generator skill
- ✗ GAS integration

---

## v9 (March 21, 2026) — Archived

**Status:** Archived | Replaced by v10

### Overview
Dynamic article template with Google Sheets API and URL parameter fallback. Complex deployment. No AIMA branding.

### Issues Resolved in V10
- Required Google Sheets Web App configuration
- Two-mode loading system (API vs URL params) was fragile
- No AIMA navigation or footer
- High deployment complexity

---

## v8 (March 21, 2026) — Archived

**Status:** Archived | Replaced by v9

### Overview
Removed hardcoded navigation titles. Added API loading priority fix.

### Issues
- Still had Sheets dependency
- Navigation event listener bug

---

## v6 (March 21, 2026) — Archived

**Status:** Archived | Replaced by v8

### Overview
Initial dynamic navigation implementation.

### Issues
- Hardcoded navigation titles
- Legal links incorrect
- Cloudflare scripts included

---

## v5 (March 20, 2026) — Archived

**Status:** Archived | First version

### Overview
First bidirectional sync attempt with Google Sheets.  
First article metadata system.

---

## Version Comparison Matrix

| Feature | v5 | v6 | v8 | v9 | v10 | v11 | v12 |
|---------|----|----|----|----|-----|-----|-----|
| Google Sheets API | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| AIMA Navigation | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| AIMA Footer | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| JSON-LD SEO | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Meta tag prev/next | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Floating sidebars | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| Mobile fade-in fix | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Project templates | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| Music template | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Gallery template | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ (v11.5) |
| Careers template | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Insights index | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Article skill | ✗ | ✗ | ✗ | ✗ | ✗ | v1.0 | v1.1 |
| Self-contained | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | Partial |
| CORS preflight fix | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| MusicAlbum schema | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Production Ready | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |

---

## Migration Guide

### V10 Articles → V12

If you have published articles built on v10 (`article-template-v10.html`):

**Option 1: Keep Using V10 Articles**
V10 articles remain valid HTML. No migration required unless you want floating sidebars or JSON-LD SEO.

**Option 2: Migrate to V12.1**
1. Open your v10 article
2. Copy article body content (`.article-content` block)
3. Open `article-template-v12_1.html`
4. Paste body content into the v12 shell
5. Update all 12 meta tags (4 new tags: prev/next URL + title)
6. Replace hardcoded nav card HTML with empty meta tag values (auto-hidden)
7. Add floating sidebars if not present
8. Run Python validation + `node --check`
9. Rename to `aima-article-[slug].html`
10. Push and test

**What You Gain**
- ✓ JSON-LD structured data for Google Search
- ✓ Floating share sidebar
- ✓ Floating TOC sidebar
- ✓ Meta tag–driven prev/next (no HTML editing per article)
- ✓ Mobile fade-in fix
- ✓ Gold callout variant

**What You Lose**
- Nothing functional. V12 is a superset of V10 article features.

---

### V11 Projects → V12

1. Copy `projects-template-v12.html`
2. Replace `SHEETS_API_URL` with your existing GAS `/exec` URL
3. Add `doOptions()` to your GAS script if absent — redeploy as new version
4. Push and test

---

## Future Roadmap

### Planned
- [ ] `logo.png` upload to repo root
- [ ] `assets/aima-og-cover.jpg` (1200×630px)
- [ ] Per-project Twitter Card images
- [ ] Visitor counter (GAS + Sheets infrastructure in place)
- [ ] Category pill filters at 13+ articles / projects
- [ ] Article generator skill v1.2

### Under Consideration
- [ ] Reading progress indicator
- [ ] Print stylesheet (articles)
- [ ] Related articles section
- [ ] Newsletter signup integration
- [ ] Author profile pages
- [ ] Series / collection grouping
- [ ] n8n zero-touch article publishing pipeline

---

**Current Version:** 12.x  
**Status:** 🟢 Active Production  
**Last Updated:** April 2026
