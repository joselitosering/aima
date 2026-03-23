# Article Template Pre-Deployment Checklist

## Before you upload your article to GitHub, verify these items:

### ✅ Meta Tags (Lines 8-15)
- [ ] `article:id` - Unique ID (e.g., "001", "002")
- [ ] `article:title` - Your article title
- [ ] `article:description` - SEO description (under 160 chars)
- [ ] `article:author` - Author name (default: Joselito Sering)
- [ ] `article:publish-date` - Format: YYYY-MM-DD
- [ ] `article:read-time` - Number only (e.g., "8" for 8 minutes)
- [ ] `article:category` - Category name
- [ ] `article:header-image` - Full Unsplash URL with `?w=1920&q=80`

### ✅ Page Title (Line 18)
- [ ] Update to match your article title
- [ ] Format: "Your Title — AIMA Magazine"

### ✅ Open Graph / Social (Lines 24-28)
- [ ] `og:title` - Match article title
- [ ] `og:description` - Match article description
- [ ] `og:image` - Match header image URL

### ✅ Structured Data (Lines 37-60)
- [ ] Update `@id` to match article ID
- [ ] Update `headline` to match title
- [ ] Update `description`
- [ ] Update `image` URL
- [ ] Update `author.name`
- [ ] Update `datePublished` (YYYY-MM-DD format)
- [ ] Update `articleSection` (category)

### ✅ Article Header Display (Lines 1444-1481)
- [ ] Line 1444: Category display text
- [ ] Line 1445-1447: Article title (can include `<span class="highlight">` for emphasis)
- [ ] Line 1457: Author name display
- [ ] Line 1466: Publish date display (will be formatted by meta tag)
- [ ] Line 1473: Read time display (will be formatted by meta tag)
- [ ] Line 1480: Category value display

### ✅ Article Content (Lines 1514-1809)
- [ ] Replace sample content with your article
- [ ] Update all H2 headings with proper IDs (e.g., `id="section-topic"`)
- [ ] Update H3 headings where needed
- [ ] Add/remove callout boxes as needed
- [ ] Add/remove pull quotes as needed
- [ ] Verify all internal links work

### ✅ Glossary Section (Lines 1711-1809)
- [ ] Update glossary terms or remove section entirely if not needed
- [ ] Each term needs matching ID: `id="glossary-termname"`
- [ ] In-text links need: `class="glossary-term" id="mention-termname" href="#glossary-termname"`
- [ ] Verify bidirectional linking (term → text, text → term)

### ✅ Navigation Cards (Lines 1895-1913)
**Previous Article (Line 1895):**
- [ ] Update `href` with full URL to previous article
- [ ] Update title in `<div class="nav-card-title">`
- [ ] If this is the FIRST article, change href to: `href="http://joselitosering.github.io/aima/index.html#home"` and title to: "Back to Home"

**Next Article (Line 1909):**
- [ ] Update `href` with full URL to next article
- [ ] Update title in `<div class="nav-card-title">`
- [ ] If this is the LAST article, change href to: `href="http://joselitosering.github.io/aima/index.html#contact"` and title to: "Get in Touch"

### ✅ About the Author (Lines 1922-1957)
- [ ] Update author bio if needed
- [ ] Verify Bitcoin address: `333avr5LEQBkft7p9YC3Hi4PCEwvZt8bnM`
- [ ] Update LinkedIn URL if needed
- [ ] Update portfolio URL if needed

### ✅ File Naming
- [ ] File saved as: `article-your-slug-###.html`
- [ ] Slug is lowercase, hyphen-separated
- [ ] Number matches `article:id` meta tag

### ✅ Final Checks
- [ ] All URLs use full paths: `http://joselitosering.github.io/aima/...`
- [ ] No broken internal links
- [ ] Header image URL is valid (test in browser)
- [ ] No placeholder text like "Lorem ipsum" or "Your content here"
- [ ] Navigation active state shows "Insights" (line 1424)

---

## Quick Test After Upload

1. **Wait 1-2 minutes** for GitHub Pages to build
2. Visit your article URL
3. Test these features:
   - [ ] Header image loads correctly
   - [ ] Mobile menu works (if on mobile/small screen)
   - [ ] Previous/Next navigation links work
   - [ ] Social share buttons work
   - [ ] Back to top button appears on scroll
   - [ ] All internal anchor links work
   - [ ] Glossary links work both ways
   - [ ] Bitcoin tip jar link opens blockchain.com

---

## Common Mistakes to Avoid

❌ **Don't** leave `href="javascript:void(0);"` in navigation cards
❌ **Don't** forget to update BOTH the meta tag AND the display text
❌ **Don't** use relative URLs like `../articles/` - use full URLs
❌ **Don't** forget to update the structured data JSON-LD
❌ **Don't** leave "Loading..." text in navigation cards
❌ **Don't** forget to update the page `<title>` tag
❌ **Don't** use image URLs without `?w=1920&q=80` parameters

---

## Example URLs to Use

**Homepage:** `http://joselitosering.github.io/aima/index.html`
**All Articles:** `http://joselitosering.github.io/aima/articles/allarticles.html`
**Legal:** `http://joselitosering.github.io/aima/legal.html`
**Gallery:** `http://joselitosering.github.io/aima/gallery.html`
**Insights:** `http://joselitosering.github.io/aima/insights.html`

**Article Pattern:** `http://joselitosering.github.io/aima/articles/article-slug-###.html`

---

## You're Ready When...

✓ All checkboxes above are checked
✓ File is saved with correct naming
✓ You've done a visual scan for placeholder text
✓ Navigation links point to real articles (or home/contact)
✓ Header image URL works when pasted in browser

**Then upload and test!** 🚀
