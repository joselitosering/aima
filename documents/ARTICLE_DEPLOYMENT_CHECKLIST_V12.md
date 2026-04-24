# AIMA Template System v12 — Pre-Deployment Checklist

## Before pushing any page to GitHub, verify all applicable items.

Sections marked **[ALL]** apply to every template.  
Sections marked by name apply only to that page type.

---

## ✅ File Setup [ALL]

- [ ] Correct template selected (see README_V12.md for template-to-page-type map)
- [ ] Template duplicated — master file untouched
- [ ] File renamed correctly:
  - Articles: `aima-article-[slug].html` (slug = lowercase, hyphens, no special chars)
  - Projects: `[project-name].html`
  - Music: `[release-name].html`
- [ ] Saved to correct directory:
  - Articles → `articles/`
  - Projects + Music → `projects/`
  - Homepage, Gallery, Insights, Careers → root `/`

---

## ✅ Meta Tags — Base [ALL]

- [ ] `<title>` — unique, under 60 chars, format: `Your Title — AIMA Magazine` (articles) or `Project Name — AIMA` (projects)
- [ ] `<meta name="description">` — 150–160 chars
- [ ] `<meta name="keywords">` — 5–8 relevant terms
- [ ] `<link rel="canonical">` — full absolute URL (`https://joselitosering.github.io/aima/...`)

---

## ✅ Meta Tags — Open Graph [ALL]

- [ ] `og:title` — matches `<title>`
- [ ] `og:description` — matches meta description
- [ ] `og:image` — valid image URL, tested in browser
- [ ] `og:url` — full absolute URL, matches canonical
- [ ] `og:type`:
  - Homepage / Gallery / Insights: `website`
  - Articles: `article`
  - Standard projects: `website`
  - Music projects: `music.album`

---

## ✅ Meta Tags — Twitter Card [ALL]

- [ ] `twitter:card` — `summary_large_image`
- [ ] `twitter:title` — matches `<title>`
- [ ] `twitter:description` — matches meta description
- [ ] `twitter:image` — matches `og:image`

---

## ✅ Structured Data (JSON-LD) [ALL]

- [ ] JSON-LD `<script type="application/ld+json">` block present
- [ ] Correct `@type` for this page:
  - Homepage: `@graph` with `Organization` + `WebSite` + `WebPage` + `SearchAction`
  - Article: `Article`
  - Project: `CreativeWork`
  - Music Project: `MusicAlbum`
- [ ] `url` field matches canonical
- [ ] `name` / `headline` matches `<title>`
- [ ] `description` matches meta description
- [ ] `image` URL valid
- [ ] `datePublished` in `YYYY-MM-DD` format
- [ ] `dateModified` updated to today

---

## ✅ Meta Tags — Articles Only

- [ ] `article:id` — sequential, zero-padded (`001`, `002`... next available: **005**)
- [ ] `article:title` — matches `<title>`
- [ ] `article:description` — matches meta description
- [ ] `article:author` — `Joselito Sering`
- [ ] `article:publish-date` — `YYYY-MM-DD`
- [ ] `article:read-time` — `ceil(word_count / 200)`, whole number only
- [ ] `article:category` — one of: Technology · Business · Creative · Social Impact · Innovation
- [ ] `article:header-image` — `https://images.unsplash.com/photo-[ID]?w=1920`
- [ ] `article:prev-url` — full URL or empty string (empty = card hidden)
- [ ] `article:prev-title` — matching title or empty string
- [ ] `article:next-url` — full URL, `tbd`, or empty string
- [ ] `article:next-title` — matching title, `tbd`, or empty string
- [ ] `JSON-LD Article` block: `mainEntityOfPage`, `ImageObject` with width/height, `dateModified`

---

## ✅ Meta Tags — Projects Only

- [ ] `aima:project_id` — sequential integer
- [ ] `aima:client` — client or studio name
- [ ] `aima:category` — one of: Brand Film · Ad Campaign · Documentary · Social Content · Corporate Explainer · Music Production · Audio Post · Sound Design
- [ ] `aima:tools` — comma-separated AI tool names
- [ ] `aima:date` — `YYYY-MM-DD`
- [ ] `aima:status` — `Live`, `In Production`, or `Draft`
- [ ] `aima:deliverables` — short descriptor e.g. `12 Assets` or `Hero Film + 4 Cut-downs`
- [ ] [Music only] `aima:duration` — production window e.g. `14 Days`
- [ ] [Music only] `og:type` set to `music.album`
- [ ] [Music only] `MusicAlbum` JSON-LD: `byArtist`, `recordLabel`, `contributor` populated

---

## ✅ Navigation [ALL]

- [ ] Nav bar present with frosted glass: `backdrop-filter:blur(20px)` confirmed in CSS
- [ ] Nav is always-on — no scroll-toggled class changes
- [ ] Nav order correct: Home · Services · Rates · Work · Process · About · Insights · Gallery
- [ ] All nav links resolve (no 404s)
- [ ] Active state correct for this page type (e.g., Insights active on article pages)
- [ ] Mobile hamburger opens and closes correctly
- [ ] Mobile menu container has `padding-top:var(--nav-h,72px)`
- [ ] Mobile menu has `overflow-y:auto`
- [ ] Mobile menu does not overlap nav bar

---

## ✅ Footer [ALL]

- [ ] 4-column grid present: Brand | Services | Company | Legal
- [ ] Logo renders correctly — `AI` (white) + `MA` (cyan), both in one parent span
- [ ] Pulse animation present on logo
- [ ] Back to Top uses `window.scrollTo({top:0,behavior:'smooth'})` — NOT `getElementById`
- [ ] All footer links resolve
- [ ] Copyright line:
  - Standard pages: `© 2026 AIMA · AI Media Agency · A Monkey Matters LLC Production · Wyoming LLC`
  - Music pages: adds `· AIRA Music Label` to copyright
- [ ] Version stamp:
  - Standard: `v12.0 · aima.media`
  - Music: `v12.3 · aira.music`

---

## ✅ Article Content [Articles only]

- [ ] `.article-lead` paragraph present (hook + thesis, larger font)
- [ ] 4–6 `<h2>` sections, each with unique `id="section-[slug]"`
- [ ] Each `<h2>` has a key phrase wrapped in `<span class="accent">`
- [ ] `#toc-sidebar` link `href` values match all `h2` ids exactly
- [ ] `#share-sidebar` present (left, 5 buttons)
- [ ] 2–3 callout boxes, mixed types: 💡 ⚠️ ✓ 🎙️
- [ ] 1–2 pull quotes (`.pullquote` → `.pullquote-text` + `.pullquote-attribution`)
- [ ] Article footer CTA (`.article-footer`) customised for this article
- [ ] Author card present (standard JS — no changes needed)
- [ ] Services card text customised for this article topic
- [ ] No placeholder content (`Lorem ipsum`, `Your content here`, `Loading...`)

---

## ✅ References [Articles only]

- [ ] Minimum 6 real, verifiable sources
- [ ] MLA 9th edition format, numbered `[1]` through `[N]`
- [ ] `data-number` attribute on each `<li>` matches number
- [ ] All URLs live-tested in browser — no 404s
- [ ] Mix of source types (journal, news outlet, official site, book, etc.)

---

## ✅ Glossary [Articles only]

- [ ] Minimum 6 technical terms
- [ ] Each term linked on **first mention only** in body:
  ```html
  <a href="#glossary-[term]" class="glossary-term" id="mention-[term]">term</a>
  ```
- [ ] Each glossary entry has matching `id="glossary-[term]"` and back-link:
  ```html
  <a href="#mention-[term]" class="back-link">↑ Back to text</a>
  ```
- [ ] No term linked more than once in body
- [ ] Glossary entries in alphabetical order

---

## ✅ Article Navigation Cards [Articles only]

- [ ] `#art-prev-card` — hidden (class `hidden`) if no previous article
- [ ] `#art-next-card` — hidden (class `hidden`) if no next article
- [ ] Both card titles populated via JS from meta tags
- [ ] "All Articles" card links to `https://joselitosering.github.io/aima/insights.html`
- [ ] Do NOT use `href="javascript:void(0);"` in nav cards
- [ ] Do NOT leave "Loading..." text visible

---

## ✅ Project Data & GAS [Projects and Music only]

- [ ] `SHEETS_API_URL` replaced with new deployment `/exec` URL
- [ ] GAS Web App deployed: Execute as Me / Access: Anyone
- [ ] `doGet` and `doOptions` both present in GAS script
- [ ] Page loads data correctly in browser (console: no CORS errors, no 404s)
- [ ] Hero image loads (Drive thumbnail format: `sz=w1200`)
- [ ] BTS grid renders (9:16 ratio, 4-column)
- [ ] Testimonials grid: placeholder shown if no data, hidden if sheet empty
- [ ] Mosaic gallery: all images rendered to DOM upfront; extras hidden via `style="display:none"` not removed
- [ ] `#proj-prev-card` hidden if prev URL absent
- [ ] `#proj-next-card` hidden if next URL absent
- [ ] [Music only] Audio player functional — test play/pause

---

## ✅ Gallery Page [gallery.html]

- [ ] `CONFIG.SHEETS_API_URL` set to deployed GAS `/exec` URL
- [ ] Project cards load from Sheets
- [ ] `.m-card.hidden { display:none }` CSS present
- [ ] `#mosaic-grid[data-filtered]` `grid-column:span 1` block **removed**
- [ ] `:has(img[src=""])` rule present to suppress broken card layout
- [ ] Expand button toggles `.mi-extra` via JS (not CSS nth-child)
- [ ] Category filter slot (`data-cat-key`) preserved — do not activate until 13+ projects

---

## ✅ Careers Page [careers.html]

- [ ] GAS endpoint URL correct in form submit handler
- [ ] `handleSubmit` and `showSuccess` in the **same** `<script>` block
- [ ] FAQ accordion JS validated with `node --check`
- [ ] EP tier table: Bronze / Silver / Gold — all three tiers present
- [ ] Royalty language: `10–15% perpetual` + `survives program exit`
- [ ] Form submits without console errors

---

## ✅ JavaScript Validation [ALL]

- [ ] Extract all `<script>` content to `/tmp/check.js`
- [ ] Run: `node --check /tmp/check.js` — zero errors
- [ ] Check for: apostrophes inside single-quoted strings
- [ ] Check for: stray `};` lines
- [ ] Check for: HTML tags inside `<script>` blocks
- [ ] Check for: variables declared but never used (from removed features)
- [ ] Mobile fade-in CSS fix present:
  ```css
  @media (max-width:768px) { .fade-in { opacity:1 !important; } }
  ```
- [ ] Mobile fade-in JS fallback present:
  ```javascript
  setTimeout(() => {
    document.querySelectorAll('.fade-in').forEach(el => el.style.opacity = '1');
  }, 800);
  ```

---

## ✅ File Integrity Validation [ALL]

Run before every push:

```python
with open('yourfile.html', encoding='utf-8') as f:
    h = f.read()

checks = {
    'file length > 10000 chars': len(h) > 10000,
    'closing </body> tag':        '</body>' in h,
    'closing </html> tag':        '</html>' in h,
    'nav bar present':            'backdrop-filter:blur' in h,
    'footer present':             'footer-bottom' in h,
    'canonical tag':              'rel="canonical"' in h,
    'og:image present':           'og:image' in h,
    'json-ld present':            'application/ld+json' in h,
}

for label, result in checks.items():
    print(f"{'✅' if result else '❌'} {label}")
```

All 8 checks must show ✅.

---

## ✅ Post-Deploy Verification [ALL]

Run after GitHub Pages builds (~2 min after push):

- [ ] Page loads at live URL without errors
- [ ] Header image displays correctly
- [ ] No broken image icons
- [ ] All nav links resolve (no 404s)
- [ ] Footer links resolve
- [ ] Article / project nav cards correct
- [ ] Mobile view tested (320px minimum)
- [ ] No horizontal scroll on mobile
- [ ] Browser console: zero errors, zero CORS failures
- [ ] Share buttons functional
- [ ] Back to Top works
- [ ] Floating sidebars visible on desktop, collapsed on mobile
- [ ] [Articles] Glossary links work both ways
- [ ] [Articles] TOC links scroll to correct sections
- [ ] [Projects] Data loads from Sheets (not placeholder)
- [ ] [Music] Audio plays

---

## Common Mistakes to Avoid

❌ **Don't** edit the master template — always duplicate first  
❌ **Don't** hardcode prev/next titles in HTML — use meta tags  
❌ **Don't** use relative URLs like `../articles/` — use full `https://` paths  
❌ **Don't** HTML-escape Drive image URLs — `&amp;` breaks thumbnails  
❌ **Don't** use Google Drive direct links in `<audio>` tags  
❌ **Don't** use `getElementById('home')` for Back to Top  
❌ **Don't** skip `node --check` — JS errors are silent in browsers  
❌ **Don't** forget to redeploy GAS after any script change  
❌ **Don't** activate category filters until 13+ items are published  
❌ **Don't** use `?w=1920&q=80` for Unsplash — use `?w=1920` only  

---

## Reference URLs

| Page | URL |
|------|-----|
| Homepage | `https://joselitosering.github.io/aima/index.html` |
| Insights | `https://joselitosering.github.io/aima/insights.html` |
| Gallery | `https://joselitosering.github.io/aima/gallery.html` |
| Careers | `https://joselitosering.github.io/aima/careers.html` |
| Article pattern | `https://joselitosering.github.io/aima/articles/aima-article-[slug].html` |
| Project pattern | `https://joselitosering.github.io/aima/projects/[name].html` |

---

## You're Ready When...

✓ All applicable checkboxes are checked  
✓ Python validation block shows 8 × ✅  
✓ `node --check` passes with zero errors  
✓ No placeholder text anywhere in the file  
✓ All image URLs tested in browser  
✓ GAS Web App deployed (if Sheets-driven page)  

**Push and watch it go live. 🚀**
