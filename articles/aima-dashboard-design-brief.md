# AIMA Dashboard — Design Brief & Build Requirements
**For:** Claude Design / UI Redesign
**Live URL:** https://joselitosering.github.io/aima/aima-dashboard.html
**Type:** Single-page HTML dashboard, self-contained, no framework

---

## 1. Purpose

Private editorial operations dashboard for AIMA Productions. Tracks a three-writer LinkedIn publishing pipeline, displays post analytics, shows editorial calendar, and surfaces weekly improvement suggestions. Used daily by one person (Joselito Sering, Editor-in-Chief).

---

## 2. Current Tech Stack

- Single `.html` file — no build system, no framework
- Chart.js 4.4.1 (CDN) for bar and doughnut charts
- Vanilla JS, CSS custom properties
- Data loaded via `fetch()` from same GitHub Pages origin
- `localStorage` for manual stat persistence across sessions

---

## 3. Current Design System

### Color Palette (CSS variables)
```
--bg:       #0a0a0f   (page background — near black)
--surface:  #13131a   (sidebar, topbar)
--card:     #1a1a24   (card backgrounds)
--border:   #2a2a3a   (borders, dividers)
--cyan:     #00d4ff   (primary accent, Joselito color)
--orange:   #ff7a00   (warnings, unsaved state, CTR)
--green:    #00c97a   (success, engagement)
--gold:     #f5c518   (Kenji color, star metrics)
--red:      #ff4466   (errors)
--purple:   #9b59f5   (Dawn color, secondary accent)
--text:     #e8e8f0   (body text)
--muted:    #888899   (labels, secondary text)
```

### Typography
- Font: `'Segoe UI', system-ui, sans-serif`
- Page title: 18px / 700
- Card title: 11px / 700 / uppercase / letter-spacing 0.8px
- KPI value: 30px / 800
- Body: 12–13px / 400–600
- Badge: 10px / 700 / uppercase

### Writer Color Coding
- **Joselito Sering** — cyan `#00d4ff` (Editor-in-Chief, primary voice)
- **Dawn Ginhaua** — purple `#9b59f5` (academic/critical, AI ethics)
- **Kenji Nakamoto** — gold `#f5c518` (tech enthusiast, innovation)

---

## 4. Page Structure & Navigation

### Sidebar (220px, sticky, dark)
```
AIMA logo (cyan/orange)
─ Dashboard
  📊 Overview
─ Content
  📅 Calendar
  📝 Post Log
─ Intelligence
  📈 Analytics
  🏆 Performance
  💡 Suggestions
─ Setup
  🗄️ Load Data
─ Writer legend (bottom)
```

### Topbar (sticky)
- Left: current page title
- Right: last-updated timestamp + "Load Data" button

### Save Bar (fixed bottom, orange)
- Appears when editorial calendar has unsaved changes
- Contains: unsaved changes message + Discard + Save & Export buttons

---

## 5. Pages & Data Mapping

### 5.1 Overview
**Purpose:** At-a-glance health of the publishing pipeline

**KPI Cards (4-up grid):**
| Card | Data Source | Field |
|------|-------------|-------|
| Total Posts | `post_log.json` | `length` of array |
| Avg Impressions | `post_analytics.csv` | avg of `impressions` col |
| Avg CTR | `post_analytics.csv` | avg of `ctr` col |
| Articles Remaining | `CALENDAR` (built-in JS array) | unpublished entries count |

**Charts (2-up):**
- Impressions Over Time — line chart, x=posted_at date, y=impressions, color-coded by persona
- Avg Impressions by Writer — bar chart, x=persona name, y=avg impressions

**Cards (2-up):**
- Top Post — highest impressions entry from analytics CSV
- Next Scheduled — next unpublished CALENDAR entry with date + writer badge

**Insight strip:**
- This Week's Insight — single text string generated from analytics patterns

---

### 5.2 Editorial Calendar
**Purpose:** Manage the full publishing schedule for articles 001–038 + Dawn/Kenji slots

**Two views (toggle button):**

**List View** — sortable table with inline editing
Columns: Date | # | Writer | Title | Tone/Mood Note | Category | Read Time | Status

| Column | Editable | Data |
|--------|----------|------|
| Date | Yes (date input) | `CALENDAR[n].date` |
| # | No | `CALENDAR[n].num` |
| Writer | No | `CALENDAR[n].persona` — color-coded badge |
| Title | Yes (text input) | `CALENDAR[n].title` |
| Tone/Mood | Yes (text input) | `CALENDAR[n].tone` |
| Category | No | `CALENDAR[n].cat` |
| Read Time | No | `CALENDAR[n].read` |
| Status | No | Published (green) / Scheduled (muted) badge |

Row color coding by writer (left border):
- Joselito rows — cyan left border
- Dawn rows — purple left border
- Kenji rows — gold left border
- Published rows — 70% opacity

**Month View** — standard month grid
- 7-column calendar grid
- Each day cell shows: article title (9px) + writer badge
- Cell border color = writer color
- Today highlighted with orange outline

**Dirty State System:**
- Any edit triggers orange bottom save bar
- `beforeunload` warning if navigating away
- Save & Export button downloads updated `aima-editorial-calendar.md`
- Discard button reverts all changes

---

### 5.3 Post Log
**Purpose:** Full history of published LinkedIn posts

**Filter tabs:** All Writers | Joselito | Dawn | Kenji

**Table columns:**
| Column | Source |
|--------|--------|
| Posted | `post_log.json[n].posted_at` |
| Writer | `post_log.json[n].persona` — badge |
| Title | `post_log.json[n].title` |
| Post ID | `post_log.json[n].post_id` (truncated) |
| Analytics | `post_log.json[n].analytics_collected` — Collected / Pending badge |

Empty state: shown when post_log.json not yet fetched

---

### 5.4 Analytics
**Purpose:** LinkedIn engagement data for all posted articles

**KPI Cards (4-up):**
| Card | Source |
|------|--------|
| Total Impressions | sum of `impressions` col in CSV |
| Total Clicks | sum of `clicks` col |
| Total Likes | sum of `likes` col |
| Avg Engagement | avg of `engagement_rate` col |

**Charts (2-up):**
- CTR by Post — bar chart, color-coded by persona
- Engagement Breakdown — doughnut (Likes / Comments / Shares / Clicks)

**Table:** All Analytics Records
Columns: Title | Writer | Posted | Impressions | Clicks | Likes | Comments | Shares | CTR | Engagement Rate
Sorted by impressions descending

**aima.productions Traffic Section** (below table):
- 4 KPI cards: Total Site Clicks | LinkedIn Referrals | Top Article Source | Avg Session Duration
- Traffic list from GA4 export (manual upload, optional)
- Manual click entry form (date + source + clicks) → stored in localStorage

---

### 5.5 Performance
**Purpose:** Per-writer and per-category performance analysis

**Writer Cards (3-up, one per writer):**
Each card: writer name + color dot + post count badge
Stats grid inside: Avg Impressions | Avg CTR

**Category Performance:**
- Horizontal bar chart (CSS progress bars)
- Category name + badge + avg impressions + post count
- Bars fill proportionally to best-performing category

**Reaction/Repost Patterns:**
- Best posting day (by avg impressions)
- Most-reposted article
- Most-reacted article
- Average CTR vs LinkedIn benchmark (0.5%)

**Top 5 Posts by Impressions:**
- Ranked list with writer badge, impressions, CTR, likes, reposts

**aima.productions Site Performance Section:**
- LinkedIn → Site Conversion % (GA4 data)
- Best Click-Through Posts ranked list (GA4 + analytics CSV)
- Tracking Pixel Status (GA4, Meta Pixel, TikTok Pixel — always shown as active)

---

### 5.6 Weekly Suggestions
**Purpose:** AI-generated improvement recommendations from analytics patterns

**Generated from:** `post_analytics.csv` data patterns

**Suggestion card types:**
- Default (cyan) — key insight
- Warning (orange) — risk/underperformance
- Good (green) — positive pattern
- Idea (purple) — content recommendation

**Suggestions generated (when data available):**
1. Best performing category recommendation
2. Underperforming post analysis
3. Best posting day reminder
4. Tone/format patterns that correlate with high engagement
5. CTR improvement tip if below benchmark
6. Next week's content priority

**Refresh button** — regenerates suggestions from latest data

---

### 5.7 Load Data
**Purpose:** Manual data file management + status display

**Upload zones (3-up):**
- Post Log (`post_log.json`) — auto-fetched; upload zone is fallback
- Analytics CSV (`post_analytics.csv`) — auto-fetched; upload zone is fallback
- GA4 Traffic CSV — always manual (exported from Google Analytics)

**Data status cards (3-up):**
- Post Log status (loaded count or "Not loaded")
- Analytics CSV status (loaded count or "Not loaded")
- Editorial Calendar status (always "Built-in 001–038 ✓")

**File location reference** (for manual uploads):
```
Post log:  D:\Apps\DevOps\Github\aima\linkedin_pipeline\post_log.json
Analytics: D:\Apps\DevOps\Github\aima\linkedin_pipeline\post_analytics.csv
GA4:       Google Analytics → Reports → Export as CSV
```

---

## 6. Data Structures

### post_log.json
```json
[
  {
    "post_id": "urn:li:share:7473451995576549376",
    "article": "aima-article-global-south-ai-gap-013.html",
    "title": "The Global South AI Gap: Who Gets Left Behind When the Future Arrives",
    "persona": "joselito",
    "posted_at": "2026-06-18T12:10:06",
    "analytics_collected": false,
    "note": "optional — for entries with unknown post_id"
  }
]
```

### post_analytics.csv headers
```
post_id, article, title, persona, posted_at, collected_at,
impressions, clicks, likes, comments, shares, engagement_rate, ctr
```

### CALENDAR (built-in JS array, 50+ entries)
```js
{
  date: "2026-06-18",
  num: 13,
  persona: "joselito",        // "joselito" | "dawn" | "kenji"
  title: "The Global South AI Gap...",
  cat: "AI Society",
  read: "10 min",
  published: true,
  tone: ""                    // editable tone/mood note
}
```

---

## 7. Interactions & States

| Interaction | Trigger | Behavior |
|-------------|---------|----------|
| Page navigation | Nav click | Shows page, hides others, calls render function |
| Calendar edit | Type in title/date/tone input | Marks row orange, shows save bar |
| Save & Export | Save bar button | Downloads updated .md file |
| Discard | Save bar button | Reverts calendar to original state |
| Unsaved leave | Navigate away | `confirm()` dialog warning |
| Auto-fetch | DOMContentLoaded | Fetches post_log.json + post_analytics.csv |
| Manual upload | File input change | Parses file, updates data, re-renders |
| Add manual stat | Form submit | Appends to localStorage, re-renders list |
| Refresh suggestions | Button click | Regenerates from current analyticsData |
| Calendar toggle | Toggle button | Switches between list and month view |
| Post log filter | Tab click | Filters table by persona |

---

## 8. Design Issues to Fix in Redesign

1. **Typography hierarchy is flat** — KPI values, card titles, and body text blend together
2. **Calendar list view is cramped** — 8-column grid on a 220px sidebar layout leaves little breathing room for title editing
3. **Empty states are too uniform** — all look the same; need differentiation between "loading" and "no data yet"
4. **Charts lack labels/context** — no axis labels, no benchmark lines, no tooltips styling
5. **Mobile is broken** — no responsive layout; 4-col KPI grids collapse badly
6. **Save bar competes with content** — fixed orange bar at bottom obscures last table rows
7. **Suggestions page feels sparse** — when no data, just an empty icon; needs better onboarding state
8. **Load Data page** — upload zones take up too much space; should be more compact now that auto-fetch handles the primary flow
9. **Writer legend in sidebar** is decorative only — could be interactive (filter by writer across all views)
10. **No loading state** — auto-fetch has no spinner; page appears empty briefly on load

---

## 9. Non-Negotiables

- Must remain a **single self-contained `.html` file** (no separate CSS/JS files)
- Chart.js must be loaded from `cdnjs.cloudflare.com` CDN only
- No `localStorage` for main data — only for manual GA4 stat entries
- No `localStorage` for session state — data reloads from GitHub on every open
- `.env` and `aima-coworker-secrets.json` must never be referenced or exposed
- All writer color coding must use the exact hex values in Section 3
- Editorial calendar export must produce valid markdown compatible with `aima-editorial-calendar.md` format

---

## 10. Brand Context

AIMA Productions is a Philippines-based AI media company focused on human kindness, philanthropy, and the intersection of technology and the arts. The aesthetic should feel like a **premium editorial ops tool** — dark, precise, data-forward — not a generic SaaS dashboard. Think newsroom meets mission control.

The three writers are:
- **Joselito Sering** — Editor-in-Chief, primary voice, AI for human kindness
- **Dawn Ginhaua** — Academic, sharp, AI ethics and labor
- **Kenji Nakamoto** — Tech enthusiast, innovation and aerospace
