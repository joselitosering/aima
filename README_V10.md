# AIMA Article Template v10 🚀

**Production-Ready | Self-Contained | Zero Dependencies**

---

## 📦 What's Included

```
article-template-v10.html           ← Main template file (2,155 lines)
AIMA_TEMPLATE_USAGE_GUIDE.md        ← Step-by-step usage instructions
ARTICLE_DEPLOYMENT_CHECKLIST.md    ← Pre-deployment verification
VERSION_HISTORY.md                  ← Complete version changelog
README_V10.md                       ← This file
```

---

## ✨ Features

### AIMA Branding
- ✓ Full homepage navigation with mobile menu
- ✓ AIMA wordmark (AI/MA split styling)
- ✓ Complete footer matching homepage
- ✓ Mobile hamburger menu with legal links
- ✓ Gallery link in navigation
- ✓ Pulse animation on logo

### Article Layout
- ✓ Large hero header with background image
- ✓ Article metadata (author, date, read time, category)
- ✓ Left sidebar with social sharing
- ✓ Main content area with full article
- ✓ Callout boxes (info, warning, success)
- ✓ Pull quotes
- ✓ Glossary with bidirectional linking
- ✓ Table of contents with scroll highlighting
- ✓ Article navigation footer (prev/all/next)
- ✓ Back to top button
- ✓ Bitcoin tip jar
- ✓ About the author section

### Technical
- ✓ Self-contained HTML (no external dependencies)
- ✓ Mobile responsive
- ✓ Semantic HTML5
- ✓ Structured data (JSON-LD)
- ✓ Open Graph meta tags
- ✓ Twitter Card support
- ✓ Auto-loading header images

---

## 🎯 Quick Start

### 1. Copy Template
```bash
cp article-template-v10.html article-your-topic-001.html
```

### 2. Edit Meta Tags
Open the file and update lines 8-15:
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

### 3. Replace Article Content
Update the article body starting at line 1514

### 4. Update Navigation
Edit prev/next links at lines 1895-1913

### 5. Save & Deploy
Upload to `joselitosering.github.io/aima/articles/`

---

## 📝 Key Sections to Edit

| Section | Lines | What to Update |
|---------|-------|----------------|
| Meta Tags | 8-15 | Article metadata |
| Page Title | 18 | Browser tab title |
| Open Graph | 24-28 | Social media preview |
| Structured Data | 37-60 | SEO schema |
| Category Display | 1444 | Category tag |
| Article Title | 1445-1447 | H1 headline |
| Author Info | 1457 | Byline |
| Publish Date | 1466 | Date display |
| Read Time | 1473 | Reading estimate |
| Article Body | 1514-1809 | Main content |
| Glossary | 1711-1809 | Term definitions |
| Prev Article | 1895-1899 | Previous link |
| Next Article | 1909-1913 | Next link |

---

## 🔧 Configuration

### Header Image
Set in meta tag (line 15):
```html
<meta name="article:header-image" content="https://images.unsplash.com/photo-xxx?w=1920&q=80"/>
```

JavaScript automatically loads it on page load.

### Navigation Cards
**Previous Article (Line 1895):**
```html
<a href="http://joselitosering.github.io/aima/articles/article-slug-000.html" 
   class="nav-card">
  <div class="nav-card-title">Previous Article Title</div>
</a>
```

**Next Article (Line 1909):**
```html
<a href="http://joselitosering.github.io/aima/articles/article-slug-002.html" 
   class="nav-card">
  <div class="nav-card-title">Next Article Title</div>
</a>
```

### Bitcoin Tip Jar
Address: `333avr5LEQBkft7p9YC3Hi4PCEwvZt8bnM`
Update at line 1941 if needed.

---

## 🎨 Customization

### Callout Boxes
```html
<!-- Info Box -->
<div class="callout">
  <span class="callout-icon">💡</span>
  <div class="callout-title">Key Insight</div>
  <div class="callout-content">Your content here</div>
</div>

<!-- Warning Box -->
<div class="callout warning">
  <span class="callout-icon">⚠️</span>
  <div class="callout-title">Common Pitfall</div>
  <div class="callout-content">Your warning here</div>
</div>

<!-- Success Box -->
<div class="callout success">
  <span class="callout-icon">✓</span>
  <div class="callout-title">Success Metric</div>
  <div class="callout-content">Your success story here</div>
</div>
```

### Pull Quotes
```html
<div class="pullquote">
  <p class="pullquote-text">Your quote here</p>
  <span class="pullquote-attribution">— Source</span>
</div>
```

### Glossary Terms
```html
<!-- In article text -->
<a href="#glossary-ai" class="glossary-term" id="mention-ai">artificial intelligence</a>

<!-- In glossary section -->
<dt id="glossary-ai">
  Artificial Intelligence (AI)
  <a href="#mention-ai" class="back-link">↑ First Use</a>
</dt>
<dd>Definition goes here</dd>
```

---

## 🚀 Deployment

### GitHub Pages
1. Upload to `/articles/` folder
2. Wait 1-2 minutes for build
3. Visit: `http://joselitosering.github.io/aima/articles/your-file.html`

### Testing Checklist
- [ ] Header image loads
- [ ] Mobile menu works
- [ ] Social share buttons work
- [ ] Prev/next navigation works
- [ ] All internal links work
- [ ] Glossary links work both ways
- [ ] Back to top appears on scroll

---

## 📊 Browser Support

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers (iOS/Android)

---

## 🔒 What's Locked in v10

### No External Dependencies
- ✗ No Google Sheets API
- ✗ No URL parameters
- ✗ No external scripts
- ✗ No build process
- ✗ No configuration files

### Everything is Hardcoded
- ✓ Navigation links
- ✓ Article metadata
- ✓ Content structure
- ✓ Prev/next buttons

**This is intentional for maximum stability and portability.**

---

## 📖 Documentation

- **Usage Guide:** See `AIMA_TEMPLATE_USAGE_GUIDE.md`
- **Deployment Checklist:** See `ARTICLE_DEPLOYMENT_CHECKLIST.md`
- **Version History:** See `VERSION_HISTORY.md`

---

## 🐛 Troubleshooting

### Header Image Not Loading
- Check meta tag has correct URL
- Verify URL works in browser
- Must include `?w=1920&q=80` parameters

### Navigation Links Broken
- Use full URLs: `http://joselitosering.github.io/aima/...`
- Don't use relative paths: `../articles/...`

### Mobile Menu Not Working
- Verify JavaScript is enabled
- Check browser console for errors

---

## 🆚 Version Comparison

| Feature | v9 (API) | v10 (Hardcoded) |
|---------|----------|-----------------|
| Google Sheets | ✓ | ✗ |
| AIMA Branding | ✗ | ✓ |
| Self-Contained | ✗ | ✓ |
| Easy Deployment | ✗ | ✓ |
| Auto Updates | ✓ | ✗ |

**Choose v10 for:** Simplicity, stability, no external dependencies  
**Choose v9 for:** Centralized content management, auto-updates

---

## 📜 License

Part of the AIMA (AI Media Agency) website ecosystem.  
© 2026 Monkey Matters LLC · Wyoming LLC

---

## 🤝 Support

For issues or questions:
1. Check `ARTICLE_DEPLOYMENT_CHECKLIST.md`
2. Review `AIMA_TEMPLATE_USAGE_GUIDE.md`
3. Verify all URLs are correct
4. Test in browser developer tools

---

## 🎯 Version Info

- **Version:** 10.0.0
- **Status:** Stable ✅
- **Released:** March 22, 2026
- **Lines:** 2,155
- **File Size:** ~183 KB
- **Dependencies:** None

---

**Ready to create amazing articles! 🚀**
