# AIMA Article Template — Final Version

## File: `article-template-aima.html`

### ✅ Complete Feature Set

#### AIMA Branding
- ✓ Full AIMA navigation with mobile menu
- ✓ AIMA wordmark (AI/MA split styling)
- ✓ Complete footer matching homepage
- ✓ All AIMA design tokens and colors
- ✓ Mobile hamburger menu with legal links
- ✓ Gallery link added to navigation
- ✓ Pulse animation on logo

#### Article Layout (from v9)
- ✓ Large hero header with background image
- ✓ Article metadata (author avatar, publish date, read time, category)
- ✓ Left sidebar with social sharing
- ✓ Main content area with full article
- ✓ Callout boxes (regular, warning, success)
- ✓ Pull quotes
- ✓ Glossary with bidirectional linking
- ✓ Table of contents
- ✓ Article navigation footer
- ✓ Back to top button
- ✓ Bitcoin tip jar
- ✓ About the author section

#### Removed Features
- ✗ Google Sheets API integration (completely removed)
- ✗ URL parameter loading (completely removed)
- ✗ Dynamic navigation from external data

#### What's Hardcoded Now
- Navigation prev/next cards (edit HTML directly)
- Article metadata (edit meta tags in `<head>`)
- Article content (edit HTML directly)
- Header image (loaded from meta tag automatically)

---

## How To Use

### 1. Edit Meta Tags (Lines 8-15)
```html
<meta name="article:id" content="001"/>
<meta name="article:title" content="Your Article Title"/>
<meta name="article:description" content="Your description"/>
<meta name="article:author" content="Joselito Sering"/>
<meta name="article:publish-date" content="2026-03-22"/>
<meta name="article:read-time" content="8"/>
<meta name="article:category" content="AI Innovation"/>
<meta name="article:header-image" content="https://images.unsplash.com/..."/>
```

### 2. Edit Article Content
- **Line 1444**: Category display
- **Line 1445**: Article title (in header)
- **Line 1457**: Author name
- **Line 1466**: Publish date
- **Line 1473**: Read time
- **Line 1480**: Category value
- **Lines 1514+**: Article body content

### 3. Edit Navigation Cards (Lines 1895-1913)
```html
<!-- Previous Article - EDIT HREF AND TITLE -->
<a href="http://joselitosering.github.io/aima/articles/article-intro-000.html" 
   class="nav-card" id="prev-article-card">
  <span class="nav-card-icon">←</span>
  <div class="nav-card-label">Previous Article</div>
  <div class="nav-card-title">Introduction to AIMA Magazine</div>
</a>

<!-- Next Article - EDIT HREF AND TITLE -->
<a href="http://joselitosering.github.io/aima/articles/article-voice-002.html" 
   class="nav-card" id="next-article-card">
  <span class="nav-card-icon">→</span>
  <div class="nav-card-label">Next Article</div>
  <div class="nav-card-title">Voice Cloning Ethics: Best Practices for 2026</div>
</a>
```

**Note:** These are now fully hardcoded. No JavaScript populates them. Edit the HTML directly for each article.

### 4. Edit Glossary (Lines 1711-1809)
Add/remove terms and their definitions. Each term needs:
- Entry in glossary section with `id="glossary-term"`
- Link in article text with `class="glossary-term" id="mention-term" href="#glossary-term"`

### 5. Save & Deploy
- Save as: `article-your-slug-###.html`
- Upload to: `joselitosering.github.io/aima/articles/`
- Wait 1-2 minutes for GitHub Pages to deploy
- Test all links and navigation

---

## JavaScript Functions Included

### Social Sharing
- `shareOnFacebook()` - Facebook share
- `shareOnTwitter()` - Twitter share  
- `shareOnLinkedIn()` - LinkedIn share
- `shareViaEmail()` - Email share

### Navigation
- `updateNav()` - Scroll effect on nav
- `toggleMobile()` - Open/close mobile menu
- `closeMobile()` - Close mobile menu

### UI
- `updateActiveSection()` - Table of contents highlighting
- Header image auto-loader from meta tag
- Back to top button with scroll threshold

---

## File Structure

```
Lines 1-64:    Meta tags, Open Graph, structured data
Lines 65-1409: Complete CSS (AIMA design system)
Lines 1410-1432: Mobile menu + navigation HTML
Lines 1434-1809: Article content (header, meta, content, glossary)
Lines 1889-1916: Article navigation footer (prev/all/next - HARDCODED)
Lines 1920-1980: About author + services sections
Lines 1982-2038: AIMA footer
Lines 2040-2155: JavaScript (social, TOC, nav, header image, mobile menu)
```

---

## Ready to Use!

This template is:
- ✅ Self-contained (no external dependencies)
- ✅ Mobile responsive
- ✅ AIMA branded
- ✅ Production ready
- ✅ Easy to edit
- ✅ No API required

Just edit, save, and deploy!
