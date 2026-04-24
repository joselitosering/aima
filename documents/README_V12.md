# AIMA Template System v12 🚀

**Production-Ready | Multi-Template | Google Sheets–Driven**

---

## 📦 What's Included

```
homepage-v12_5.html                     ← Homepage / index (3,335 lines | 188 KB)
article-template-v12_1.html             ← Articles / Insights posts (1,155 lines | 73 KB)
projects-template-v12.html              ← Project / case study pages (1,574 lines | 97 KB)
project-music-template-v12_2.html       ← AIRA Music Label releases (145 lines | 7 KB)
projects-gallery-template-v11_5.html    ← Gallery index — V11.5, current active (1,109 lines)
careers.html                            ← Careers / EP Partner Program (1,277 lines)
aima-all-articles.html                  ← Insights index (1,161 lines)
README_V12.md                           ← This file
AIMA_TEMPLATE_USAGE_GUIDE_V12.md        ← Step-by-step authoring guide
ARTICLE_DEPLOYMENT_CHECKLIST_V12.md     ← Pre-deployment verification
V12_MASTER_SUMMARY.md                   ← Complete system inventory
VERSION_HISTORY_V12.md                  ← Changelog v10 → v12
```

> **Note on Gallery:** `projects-gallery-template-v11_5.html` is the current locked version.
> All other V11 templates are superseded by V12.

---

## ✨ What's New in V12

### Added Across All Templates
- ✓ Full SEO block on every page type (Open Graph + Twitter Card + JSON-LD)
- ✓ Schema.org structured data — schema type varies by page (see Master Summary)
- ✓ `article:prev-url` / `article:prev-title` / `article:next-url` / `article:next-title` meta tags
- ✓ Nav cards auto-hide when prev/next value is empty or `tbd`
- ✓ Always-on frosted-glass nav — `rgba(6,8,16,0.60)` + `backdrop-filter:blur(20px)` (no scroll toggling)
- ✓ Mobile menu: `padding-top:var(--nav-h,72px)` + `overflow-y:auto` — clears fixed nav
- ✓ Mobile fade-in fix: CSS `opacity:1 !important` override + 800ms `setTimeout` fallback
- ✓ `window.scrollTo({top:0,behavior:'smooth'})` on Back to Top (not `getElementById`)
- ✓ Footer version stamp: `v12.0 · aima.media` (music pages: `v12.3 · aira.music`)
- ✓ AIMA article generator skill v1.1 (`aima-article-generator_skill.md`)

### Article Template (v12.1)
- ✓ 12 meta tags in `<head>` (up from 8 in v10)
- ✓ Prev/next sourced from meta tags — no hardcoded HTML editing required
- ✓ `Article` JSON-LD with `mainEntityOfPage`, `ImageObject`, `dateModified`
- ✓ Floating share sidebar (`#share-sidebar`, left, 5 buttons)
- ✓ Floating TOC sidebar (`#toc-sidebar`, right panel)
- ✓ File naming convention: `aima-article-[slug].html`
- ✓ Callout gold variant `💡 ⚠️ ✓ 🎙️`

### Project Templates (v12)
- ✓ `aima:project_id`, `aima:client`, `aima:category`, `aima:tools`, `aima:date`, `aima:status`, `aima:deliverables`, `aima:duration` meta tags
- ✓ `CreativeWork` JSON-LD (standard projects)
- ✓ `MusicAlbum` JSON-LD with `byArtist`, `recordLabel`, `contributor` (music projects)
- ✓ Audio embed via GitHub raw URL or Dropbox `?dl=1` (music projects)
- ✓ All content Sheets-driven via GAS `doGet` / `doOptions`

### Homepage (v12.5)
- ✓ `Organization` + `WebSite` + `WebPage` + `SearchAction` in one `@graph`
- ✓ Section IDs locked (do not rename)
- ✓ Latest articles and project cards wired to Sheets API

### Careers (new in V12 cycle)
- ✓ EP Partner Program: Bronze / Silver / Gold tiers
- ✓ GAS form backend (`aima-ep-applications.gs`)
- ✓ Royalties survive program exit indefinitely

---

## 🎯 Quick Start

### 1. Pick Your Template

| Page Type | Template File |
|-----------|--------------|
| Homepage | `homepage-v12_5.html` |
| Article / Blog Post | `article-template-v12_1.html` |
| Project / Case Study | `projects-template-v12.html` |
| Music Release | `project-music-template-v12_2.html` |
| Gallery Index | `projects-gallery-template-v11_5.html` |
| Careers | `careers.html` |
| Insights Index | `aima-all-articles.html` |

### 2. Duplicate — Never Edit the Master
```bash
cp article-template-v12_1.html articles/aima-article-your-slug-005.html
cp projects-template-v12.html  projects/your-project-name.html
```

### 3. Fill the Meta Tags
- Articles: update the 12 `article:*` meta tags in `<head>`
- Projects: update the 7 `aima:*` meta tags + OG tags in `<head>`
- All pages: update `<title>`, canonical URL, `og:image`, JSON-LD

### 4. Sheets-Driven Pages — Deploy GAS
```
1. Copy the relevant .gs script into a new Apps Script project
2. Run the setup function once to create the sheet tab
3. Deploy → New Deployment → Web App
   Execute as: Me  |  Access: Anyone
4. Paste the /exec URL into the HTML SHEETS_API_URL constant
```

### 5. Validate Before Pushing
```python
with open('yourfile.html', encoding='utf-8') as f:
    h = f.read()
checks = {
    'length > 10000':   len(h) > 10000,
    'closing </body>':  '</body>' in h,
    'closing </html>':  '</html>' in h,
    'canonical tag':    'rel="canonical"' in h,
    'og:image':         'og:image' in h,
    'json-ld':          'application/ld+json' in h,
}
for label, ok in checks.items():
    print(f"{'✅' if ok else '❌'} {label}")
```

### 6. Push to GitHub
```
articles/   → aima-article-[slug].html
projects/   → [project-name].html
root/       → index.html, gallery.html, insights.html, careers.html
```
Wait ~2 minutes for GitHub Pages to build.

---

## 📝 Article Command Format (Skill v1.1)

```
write an article on [TOPIC] · category [CATEGORY] · id [NNN] · 
points: [1. point 2. point 3. point] · 
tone [TONE] · prev [TITLE | URL] · next [TITLE | URL]
```

**Tone options:** analytical · persuasive · instructional · editorial · narrative  
**Next article ID:** 005  
**File name:** `aima-article-[slug].html`

---

## 📊 Template Statistics

```
Homepage:          3,335 lines  |  188 KB  |  GAS + Static
Article:           1,155 lines  |   73 KB  |  Static meta tags
Project:           1,574 lines  |   97 KB  |  Google Sheets via GAS
Music Project:       145 lines  |    7 KB  |  Google Sheets via GAS
Gallery (v11.5):   1,109 lines  |  ~65 KB  |  Google Sheets via GAS
Careers:           1,277 lines  |  ~78 KB  |  GAS form → Sheets
Insights Index:    1,161 lines  |  ~70 KB  |  Google Sheets via GAS
```

---

## 🔧 Key Technical Rules

| Rule | Value |
|------|-------|
| Nav background | `rgba(6,8,16,0.60)` + `backdrop-filter:blur(20px)` |
| Nav behaviour | Always-on — no scroll toggling |
| Nav order | Home · Services · Rates · Work · Process · About · Insights · Gallery |
| Back to Top | `window.scrollTo({top:0,behavior:'smooth'})` |
| Drive images | `thumbnail?id=FILE_ID&sz=w1200` |
| Audio files | GitHub raw URL or Dropbox `?dl=1` (not Google Drive direct) |
| JS validation | `node --check /tmp/file.js` on all script blocks |
| GAS CORS | `doOptions()` must return `ContentService.createTextOutput('')` |
| GAS redeploy | After any code change: Edit → New Version (URL stays same) |

---

## 🎨 Brand Tokens (Locked)

```css
--cyan:   #00D9F5   /* AIMA primary */
--orange: #FF5E20   /* accent */
--gold:   #C8A84B   /* premium / AIRA */
--dark:   #060810   /* background */
--font-display: 'Anton', sans-serif
--font-body:    'DM Sans', sans-serif
--font-mono:    'Courier Prime', monospace
```

Logo rule: `<span class="ai">AI</span><span class="ma">MA</span>` — both inside one parent span, no flex gap.

---

## 🚀 Hosting & Infrastructure

| Layer | Tool |
|-------|------|
| Hosting | GitHub Pages · `joselitosering.github.io/aima/` |
| Data backend | Google Sheets + Google Apps Script Web Apps |
| Images | Google Drive thumbnails (`sz=w1200`) |
| Audio | GitHub raw URLs or Dropbox `?dl=1` |
| Automation | n8n (zero-touch content pipelines) |
| AI tools | MidJourney · Kling AI · Higgsfield · Suno v5 · ElevenLabs · Runway Gen-3 |

---

## 📖 Documentation

- **Master Summary:** See `V12_MASTER_SUMMARY.md`
- **Usage Guide:** See `AIMA_TEMPLATE_USAGE_GUIDE_V12.md`
- **Deployment Checklist:** See `ARTICLE_DEPLOYMENT_CHECKLIST_V12.md`
- **Version History:** See `VERSION_HISTORY_V12.md`

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Header image not loading | Verify Unsplash URL works in browser; use `?w=1920` not `?w=1920&q=80` |
| Drive thumbnail broken | Check `&` not encoded as `&amp;` |
| Audio not playing | Use GitHub raw URL or Dropbox `?dl=1` — never Google Drive direct |
| Nav overlaps mobile menu | Add `padding-top:var(--nav-h,72px)` to mobile menu |
| Fade-in stuck on mobile | Add `@media (max-width:768px) { .fade-in { opacity:1 !important; } }` + 800ms setTimeout |
| GAS CORS error | Ensure `doOptions()` returns `ContentService.createTextOutput('')` |
| JS silent error | Extract `<script>` block → `node --check /tmp/check.js` |
| Navigation broken | Use full absolute URLs — no relative paths |
| File truncated silently | Validate with Python `len()`, `'</body>' in h`, `'</html>' in h` |

---

## 📜 Legal

Part of the AIMA (AI Media Agency) website ecosystem.  
© 2026 AIMA · AI Media Agency · A Monkey Matters LLC Production · Wyoming LLC

---

## 🎯 Version Info

| Template | Version | Status | Lines | Size |
|----------|---------|--------|-------|------|
| Homepage | 12.5 | 🟢 Active | 3,335 | 188 KB |
| Article | 12.1 | 🟢 Active | 1,155 | 73 KB |
| Project | 12.0 | 🟢 Active | 1,574 | 97 KB |
| Music Project | 12.2 | 🟢 Active | 145 | 7 KB |
| Gallery | 11.5 | 🟢 Active (V11 locked) | 1,109 | ~65 KB |
| Careers | 12.0 | 🟢 Active | 1,277 | ~78 KB |
| Insights Index | 12.0 | 🟢 Active | 1,161 | ~70 KB |

**Last Updated:** April 2026

---

**Ready to create. 🎬**
