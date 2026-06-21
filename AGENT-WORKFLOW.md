# AIMA Magazine — Agent Workflow Handoff Document

**Version:** 1.0 · June 21, 2026  
**Purpose:** Define the automation pipeline for AIMA Magazine article production, publishing, and distribution. Each agent is independently invokable. Stages can be enabled or disabled individually to economize tokens and batch work.

---

## 1. System Architecture

```
TRIGGER
   │
   ▼
[PRODUCT MANAGER] ─── reads state, sets context, opens run log
   │
   ▼
[EDITORIAL CALENDAR] ─── resolves next article: number, title, author, tone, tags
   │
   ▼
[RESEARCH AGENT] ─── fetches sources, statistics, expert quotes → research brief
   │                 (can run autonomously; output cached for writer)
   ▼
[AUTHOR AGENT] ─── reads persona + research brief → writes full article HTML
   │
   ▼
[QC GATE] ─── human toggle: ON = pause for review | OFF = auto-proceed
   │
   ▼
[PUBLISHER AGENT] ─── git push → deploy guard (2 min) → Google Sheets
   │
   ▼
[MARKETING AGENT] ─── LinkedIn company page post → personal reshare
   │
   ▼
[METRICS AGENT] ─── collects analytics 48h post-publish → logs to CSV
   │
   ▼
[PRODUCT MANAGER] ─── closes run log, updates state file, flags next run
```

---

## 2. Batch / Token Economy Modes

Each agent can run in isolation. This allows batching:

| Mode | Agents Active | Use Case |
|------|--------------|----------|
| **Research Batch** | Research only | Queue 6 research briefs overnight |
| **Write Batch** | Author only | Write 6 articles from existing briefs |
| **Review Day** | QC Gate only | Human reviews all staged articles |
| **Publish Batch** | Publisher only | Push all approved articles at once |
| **Marketing Batch** | Marketing only | Post all queued articles to LinkedIn |
| **Full Pipeline** | All agents | Single article end-to-end |
| **Analytics Run** | Metrics only | Collect stats for all 48h+ posts |

**Example economy:** Run Research + Author for 6 articles (6 days of content in one session). QC offline. Then one Publisher + Marketing session to ship everything.

### Stage Toggles

Set these in `.env` or pass as CLI flags to any agent:

```
RESEARCH_ENABLED=true
WRITE_ENABLED=true
QC_GATE=human          # human | auto
PUBLISH_ENABLED=true
GS_ENABLED=true        # Google Sheets logging
MARKETING_ENABLED=true
ANALYTICS_ENABLED=true
```

---

## 3. Shared State & Communication Files

All agents read and write through these files. No agent-to-agent direct calls.

| File | Owner | Purpose |
|------|-------|---------|
| `articles/aima-coworker-state.json` | Product Manager | Tracks next article number, track, author rotation, last run |
| `articles/aima-editorial-calendar.md` | Editorial Calendar | Source of truth: article titles, authors, categories, read time |
| `articles/aima-coworker-prompt.md` | All agents | Master writing instructions, persona rules, HTML structure |
| `articles/personas/` | Author Agent | Persona profiles: voice, tone, backstory per writer |
| `articles/research/` | Research Agent | Research briefs (JSON) — one per article, named by slug |
| `linkedin_pipeline/posted_articles.json` | Marketing Agent | Tracks which articles have been posted to LinkedIn |
| `linkedin_pipeline/post_log.json` | Marketing + Metrics | Post IDs with timestamps for 48h analytics collection |
| `linkedin_pipeline/pipeline.log` | Product Manager | Execution log for all agent runs |
| `CLAUDE.md` | Product Manager | Project memory — approved workflows, current state, decisions |

---

## 4. Node Definitions

---

### NODE 1 — TRIGGER

**What fires it:** Cowork scheduled task (`aima-article-coworker`, daily) or manual invocation.

**Fetch:**
- `articles/aima-coworker-state.json` — read `next_article_number`, `next_track`, `next_article_date`, `last_run`
- `articles/aima-coworker-prompt.md` — load master instructions
- Current date

**Execute:**
- Determine which stage(s) to run based on toggle flags
- Hand off context to Product Manager

**Output:**
- Run context object: `{ article_number, track, date, stages_enabled }`

---

### NODE 2 — PRODUCT MANAGER AGENT

**Role:** Orchestrator. Reads state, sets run context, checks quality at each stage gate, writes to log, updates state file at end of run.

**Fetch:**
- `articles/aima-coworker-state.json`
- `linkedin_pipeline/pipeline.log` (last 20 lines — check for errors)
- `linkedin_pipeline/post_log.json` (pending analytics check)
- `CLAUDE.md` (project memory)

**Process:**
- Validate that required files exist before invoking each downstream agent
- After each stage: check output exists and is non-empty; log pass/fail
- On failure: log error, halt pipeline, surface to human

**Execute at start:**
- Open a run log entry: `{ run_id, date, article_number, stages_planned }`

**Execute at end:**
- Update `aima-coworker-state.json`: increment `next_article_number`, advance `next_track`, set `last_run`
- Write run summary to `CLAUDE.md` Pending Actions if any blockers exist
- Mark completed stages in log

**Quality checks at each gate:**
- Research brief: has sources, statistics, expert quotes, >500 words
- Article HTML: has all required meta tags, >1800 words, valid prev/next links, cover image URL resolves
- Published: og:image returns HTTP 200, Google Sheets row confirmed
- LinkedIn: company post ID logged, reshare ID logged

---

### NODE 3 — EDITORIAL CALENDAR AGENT

**Role:** Resolve the next article assignment from the calendar and state file.

**Fetch:**
- `articles/aima-editorial-calendar.md` — full calendar table
- `articles/aima-coworker-state.json` — `next_article_number`, `next_track`, persona rotation indexes

**Process:**
- Look up row `next_article_number` in calendar
- Resolve author: if track = `joselito`, use calendar index `joselito.next_calendar_index`; if track = `trending`, use `trending.next_persona` (rotate dawn → kenji → dawn)
- Extract: title, category, read_time, publish_date, tone notes

**Output (article spec JSON):**
```json
{
  "number": 17,
  "slug": "dawn-ginhaua-ai-gender-gap",
  "title": "...",
  "author": "dawn",
  "category": "AI Society",
  "read_time": 10,
  "publish_date": "2026-06-26",
  "tone": "critical, feminist, globally-minded",
  "tags": ["#AIEthics", "#GenderEquity", "#AIMA"]
}
```

**Does NOT:** fetch research, write article, or update state.

---

### NODE 4 — RESEARCH AGENT

**Role:** Autonomous research gatherer. Runs independently of author. Caches output as a research brief.

**Inputs:** Article spec from Editorial Calendar node.

**Fetch (web search + web fetch):**
- 3–5 primary sources: studies, reports, institutional data (IMF, World Bank, academic papers)
- 2–3 expert quotes or named sources with affiliation
- Current statistics (with dates): percentages, dollar figures, population counts
- Contrarian or dissenting perspectives (for balance)
- Related recent news or events (last 6 months)

**Process:**
- Verify each statistic has a named source and publication date
- Flag any source that cannot be verified (do not include unverified claims)
- Group findings into: Background, Current State, Key Data, Expert Views, Counterarguments, Implications

**Execute:**
- Save research brief to `articles/research/[slug]-research.json`

**Output format:**
```json
{
  "article_number": 17,
  "slug": "...",
  "researched_at": "2026-06-21",
  "sources": [
    { "title": "...", "url": "...", "publisher": "...", "date": "...", "key_stat": "..." }
  ],
  "key_statistics": ["..."],
  "expert_quotes": [{ "name": "...", "affiliation": "...", "quote": "..." }],
  "background": "...",
  "current_state": "...",
  "counterarguments": "...",
  "implications": "..."
}
```

**Can run when:** Writer is off, Publisher is off, Marketing is off. Research runs ahead.

---

### NODE 5 — AUTHOR AGENT

**Role:** Writes the full article HTML using persona voice, research brief, and HTML skeleton pattern.

**Inputs:**
- Article spec (from Editorial Calendar node)
- Research brief (from `articles/research/[slug]-research.json`)

**Fetch:**
- `articles/personas/[persona]-profile.md` — voice, tone, style, backstory
- `articles/aima-coworker-prompt.md` — HTML structure rules, meta tag requirements
- Previous article HTML — to extract `prev-url` and update `next-url` after writing
- Cover image — generate via Higgsfield AI (`nano_banana_pro`, 16:9), download, resize to 1200×630 JPG, save to `img/articles/`

**Process:**
- Write in persona voice (not generic AI tone)
- Target word count: 1800–2500 words
- Structure: lead paragraph → 5–6 H2 sections → stat grid → pullquote → glossary → references
- All statistics must cite a source from the research brief
- MLA 9th edition citations in references section
- Embed 6+ glossary terms with `data-term` attributes

**Execute:**
- Write full article HTML to `articles/aima-article-[slug]-[number].html`
- Update previous article's `article:next-url` and `article:next-title` meta tags
- Stage both files: `git add articles/aima-article-[slug]-[number].html articles/aima-article-[prev-slug].html`
- Do NOT push (publisher's job)

**Required meta tags (all must be present — QC gate checks these):**
```html
<meta name="article:id" content="[number padded to 3 digits]"/>
<meta name="article:persona" content="[joselito|dawn|kenji]"/>
<meta name="article:publish-date" content="YYYY-MM-DD"/>
<meta name="article:read-time" content="[N]"/>
<meta name="article:category" content="[category]"/>
<meta name="article:header-image" content="[higgsfield CDN url]"/>
<meta name="article:prev-url" content="./[prev-filename].html"/>
<meta name="article:next-url" content=""/>
<meta property="og:image" content="https://joselitosering.github.io/aima/img/articles/[slug].jpg"/>
```

**Can run when:** Publisher is off, Marketing is off. Article files staged locally.

---

### NODE 6 — QC GATE

**Toggle:** `QC_GATE=human` (pause for review) | `QC_GATE=auto` (proceed if all checks pass).

**When human:** Pipeline pauses. Cowork surfaces the article file and QC report to the user. User approves or requests revision.

**When auto:** QC checks run programmatically; if all pass, pipeline proceeds.

**Fetch:**
- The staged article HTML file

**Checks (all must pass):**

| Check | Pass Condition |
|-------|---------------|
| Meta tags | All 9 required meta tags present and non-empty |
| Word count | Body text ≥ 1800 words |
| H2 sections | 5–6 H2 headings present |
| Stat grid | At least 4 stat cards with numeric values |
| Pullquote | One `<blockquote class="pullquote">` present |
| Glossary | ≥ 6 terms with `data-term` attribute |
| References | ≥ 6 MLA citations in references section |
| Cover image URL | `og:image` URL matches file saved to `img/articles/` |
| Prev link | `article:prev-url` points to an existing file |
| Persona match | Author name in byline matches persona in meta tag |
| No placeholder text | No instances of "TODO", "PLACEHOLDER", "lorem ipsum" |

**Output:**
- QC report: `articles/qc/[slug]-qc.json` — list of checks with pass/fail
- Signal: `approved` or `needs_revision` with specific failure notes

**On revision:** Return to Author Agent with QC report. Author corrects and resubmits.

---

### NODE 7 — PUBLISHER AGENT

**Role:** Pushes approved article to GitHub Pages, waits for deploy, logs to Google Sheets.

**Inputs:** Approved article HTML + QC approval signal.

**Fetch:**
- Confirm `git status` shows the article file staged and ready
- `articles/aima-coworker-secrets.json` — Google Sheets webapp URL

**Execute (in order):**

1. `git commit -m "Article [number]: [title]"` — commit staged article + prev-article update + cover image
2. `git push origin main` — triggers GitHub Pages deploy
3. Wait 120 seconds (deploy guard polling loop)
4. Poll `og:image` URL (HEAD request) until HTTP 200 or 120s timeout
5. On image live: POST canonical URL to Google Sheets GAS endpoint → column 1
6. Confirm GS row number in log

**Output:**
- Live URL: `https://aima.productions/articles/[filename].html`
- GS confirmation: row number
- Deploy timestamp

**Can run when:** Marketing is off. Publisher confirms article is live and GS is updated; Marketing runs later.

---

### NODE 8 — MARKETING AGENT

**Role:** Posts article to AIMA LinkedIn company page and reshares to Joselito's personal profile.

**Inputs:** Live URL + article HTML content.

**Fetch:**
- Article HTML (from local file — already committed)
- `linkedin_pipeline/.env` — `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_ORG_ID`, `LINKEDIN_MEMBER_ID`
- Cover image from `https://joselitosering.github.io/aima/img/articles/[slug].jpg`

**Execute (in order):**

1. Download cover image bytes
2. Register image upload with LinkedIn Assets API
3. PUT image bytes to upload URL
4. Build company page commentary:
   - Article hook (2 sentences from lead paragraph)
   - CTA + source URL
   - Hashtags (generated from category + title keywords)
   - Persona byline: `By [Full Name] · [Role], AIMA`
5. POST to `/v2/ugcPosts` as `urn:li:organization:[ORG_ID]` — IMAGE mode
6. Wait 2 seconds, resolve `urn:li:share:` URN via `/rest/posts`
7. Build personal reshare commentary:
   - Hook (3 punchy lines, paragraph-separated)
   - TL;DR (article-specific)
   - CTA (article-specific)
   - Hashtags (same as company page)
8. POST reshare to `/rest/posts` as `urn:li:person:[MEMBER_ID]` with `reshareContext`
9. Log both post URNs to `post_log.json`
10. `git push` the updated `post_log.json`

**Can run when:** Article is already live on GitHub Pages. Does not require other agents to be active.

**Token refresh reminder:** If `r_member_social` scope needed for analytics, run `python linkedin_pipeline/linkedin_auth.py` first.

---

### NODE 9 — METRICS AGENT

**Role:** Collects LinkedIn analytics for posts that are 48h+ old.

**Runs:** Independently, on schedule or at start of any pipeline run.

**Fetch:**
- `linkedin_pipeline/post_log.json` — find entries where `analytics_collected: false` and `posted_at` > 48h ago
- LinkedIn `/rest/socialMediaPostStatistics` API (requires `r_member_social` scope)
- Fallback: `linkedin_pipeline/xls_import.py` if API token lacks scope

**Process:**
- For each eligible post: fetch impressions, clicks, reactions, reposts, comments
- Calculate CTR = clicks / impressions

**Execute:**
- Append row to `linkedin_pipeline/post_analytics.csv`
- Mark `analytics_collected: true` in `post_log.json`
- Update `post_log.json` via git push

**Output:**
- `post_analytics.csv` updated
- Summary logged: `N posts collected, avg impressions: X, avg CTR: Y%`

**Can run autonomously:** Yes — entirely independent of all other agents.

---

## 5. Agent Prompts

These are the system prompts / task descriptions for invoking each agent.

---

### PROMPT: Product Manager

```
You are the Product Manager for AIMA Magazine's automated publishing pipeline.

Your job is to orchestrate a single pipeline run from trigger to completion.

STATE: Read articles/aima-coworker-state.json to understand where the pipeline is.
MEMORY: Read CLAUDE.md for approved workflows, current decisions, and blockers.
LOG: Read the last 20 lines of linkedin_pipeline/pipeline.log to check for errors.

ACTIVE STAGES (check toggles before invoking):
- Research: [RESEARCH_ENABLED]
- Write: [WRITE_ENABLED]
- QC Gate: [QC_GATE]
- Publish: [PUBLISH_ENABLED]
- Marketing: [MARKETING_ENABLED]
- Analytics: [ANALYTICS_ENABLED]

FOR EACH STAGE:
1. Confirm required inputs exist before starting
2. Invoke the stage
3. Confirm outputs exist and pass quality check
4. Log result (pass/fail + timestamp)
5. On failure: stop pipeline, write blocker to CLAUDE.md, surface to human

AT END OF RUN:
- Update aima-coworker-state.json (next_article_number, next_track, last_run)
- Write run summary to CLAUDE.md if any decisions were made
- Report: articles written, published, posted, analytics collected

Do not skip steps. Do not proceed past a failed quality check.
```

---

### PROMPT: Editorial Calendar Agent

```
You are the Editorial Calendar Agent for AIMA Magazine.

Your job is to resolve the next article assignment and output a complete article spec.

READ:
- articles/aima-coworker-state.json → get next_article_number, next_track, persona indexes
- articles/aima-editorial-calendar.md → look up the row for next_article_number

RESOLVE AUTHOR:
- If next_track = "joselito": author = Joselito Sering; use joselito.next_calendar_index
- If next_track = "trending": author = trending.next_persona (dawn or kenji, rotating)

OUTPUT a JSON article spec with:
{
  "number": N,
  "slug": "[url-safe title slug]",
  "filename": "aima-article-[slug]-[NNN].html",
  "title": "...",
  "author": "[joselito|dawn|kenji]",
  "category": "...",
  "read_time": N,
  "publish_date": "YYYY-MM-DD",
  "tone": "...",
  "tags": ["...", "..."]
}

Do not write the article. Do not fetch research. Output spec only.
```

---

### PROMPT: Research Agent

```
You are the Research Agent for AIMA Magazine. You gather sources and data for a
specific article before the author writes it.

INPUT: Article spec JSON (number, title, author, category, tone)

YOUR JOB:
1. Search for 5+ primary sources: academic papers, institutional reports,
   government data, major journalism. No blogs or unverified opinion pieces.
2. Extract 4–6 key statistics with source name, publication date, and URL.
3. Find 2–3 expert quotes with full name and affiliation.
4. Identify the strongest counterargument to the article's implied thesis.
5. Note 1–2 recent news events (last 6 months) relevant to the topic.

QUALITY BAR:
- Every statistic must have a named source and year
- Prefer primary sources (original research) over secondary (news coverage)
- Flag any claim you cannot verify — do not include it

SAVE output to articles/research/[slug]-research.json using the standard schema.

Do not write prose. Do not generate the article. Research and cite only.
```

---

### PROMPT: Author Agent

```
You are the Author Agent for AIMA Magazine.

Your job is to write a complete, production-ready article HTML file.

READ IN ORDER:
1. articles/aima-coworker-prompt.md — master writing instructions and HTML structure
2. articles/personas/[persona]-profile.md — voice, tone, style for this writer
3. articles/research/[slug]-research.json — all verified sources and statistics
4. The previous article HTML — to extract the correct prev-url value
5. The article skeleton pattern from an existing recent article

WRITE:
- Target: 1800–2500 words of body text
- Voice: match the persona exactly — not generic AI prose
- Structure: lead paragraph → 5–6 H2 sections → stat grid (4 cards) →
  pullquote → glossary (6+ terms) → 6+ MLA 9th edition references
- Every statistic used must trace back to the research brief
- Embed all required meta tags (see QC gate checklist)

COVER IMAGE:
- Generate via Higgsfield AI: model nano_banana_pro, 16:9 ratio
- Download PNG, resize to 1200x630 JPG via Python PIL
- Save to img/articles/aima-[NNN]-[slug].jpg
- Set og:image meta to GitHub Pages URL for that file
- Set article:header-image meta to Higgsfield CDN URL

AFTER WRITING:
- Update the previous article's article:next-url and article:next-title meta tags
- Stage both files: git add [new article] [prev article] img/articles/[cover]
- Do NOT commit or push — that is the Publisher Agent's job

OUTPUT: Staged files ready for QC Gate.
```

---

### PROMPT: QC Gate

```
You are the QC Gate for AIMA Magazine. You verify that a written article
meets all production standards before it is published.

INPUT: The staged article HTML filename

RUN ALL CHECKS:
[ ] 9 required meta tags present and non-empty (article:id, article:persona,
    article:publish-date, article:read-time, article:category,
    article:header-image, article:prev-url, og:image, og:description)
[ ] Body word count ≥ 1800
[ ] 5–6 H2 section headings
[ ] Stat grid with ≥ 4 cards containing numeric values
[ ] 1 pullquote (<blockquote class="pullquote">)
[ ] ≥ 6 glossary terms with data-term attribute
[ ] ≥ 6 MLA 9th edition references
[ ] og:image URL matches a file in img/articles/
[ ] article:prev-url points to an existing file in articles/
[ ] Persona name in byline matches article:persona meta tag value
[ ] No instances of TODO, PLACEHOLDER, lorem ipsum, or [BRACKET] templates
[ ] All statistics in body text are cited in the references section

OUTPUT:
- If all pass and QC_GATE=auto: signal "approved", pipeline continues
- If QC_GATE=human: present QC report to user, await approval
- If any fail: signal "needs_revision" with specific failures listed;
  return to Author Agent with failure notes
```

---

### PROMPT: Publisher Agent

```
You are the Publisher Agent for AIMA Magazine.

Your job is to push an approved article to GitHub Pages and confirm it is live.

PRE-CHECK:
- Confirm git status shows the article file and cover image staged
- Confirm QC Gate approved the article

EXECUTE IN ORDER:
1. git commit -m "Article [NNN]: [Title]"
2. git push origin main
3. Start 120-second deploy guard polling loop:
   - Every 30 seconds: HEAD request to og:image URL
   - On HTTP 200: article is live — proceed
   - On timeout (120s): log warning, proceed anyway
4. POST canonical article URL to Google Sheets GAS endpoint:
   Payload: { "url": "https://joselitosering.github.io/aima/articles/[filename]" }
   Confirm: response contains { "success": true, "row": N }
5. Log: live URL, GS row number, deploy timestamp

OUTPUT:
- Confirmation: "Article [NNN] live at [URL] · GS row [N]"
- Pass live URL and article content to Marketing Agent queue

Do not post to LinkedIn. That is the Marketing Agent's job.
```

---

### PROMPT: Marketing Agent

```
You are the Marketing Agent for AIMA Magazine.

Your job is to post a live article to the AIMA LinkedIn company page
and reshare it to Joselito's personal profile.

PRE-CHECK:
- Confirm article og:image URL returns HTTP 200 (article must be live)
- Confirm LINKEDIN_ACCESS_TOKEN is set in linkedin_pipeline/.env

EXECUTE via python linkedin_pipeline/pipeline.py:
The pipeline script handles the full sequence automatically:
1. Downloads cover image from GitHub Pages
2. Uploads image to LinkedIn Assets API
3. Posts to AIMA company page (urn:li:organization:[ORG_ID]) with IMAGE mode
4. Resolves share URN via /rest/posts
5. Builds persona-aware personal commentary (hook → TL;DR → CTA → hashtags)
6. Reshares to Joselito's personal profile (urn:li:person:[MEMBER_ID])
7. Logs both post IDs to post_log.json with timestamp for 48h analytics

VERIFY:
- Company page post ID logged in post_log.json
- Personal reshare ID logged in post_log.json
- post_log.json pushed to GitHub

OUTPUT:
- Company page post URN: urn:li:share:...
- Personal reshare URN: urn:li:share:...
- Confirm: "Article [NNN] posted to LinkedIn · company + personal"

If pipeline.py is off: queue the article in posted_articles.json exclusion
list removal — run pipeline.py manually when ready.
```

---

## 6. Separation of Concerns — What Each Agent Owns

| Concern | Owner | Never Touches |
|---------|-------|--------------|
| Article assignment | Editorial Calendar | Article content, publishing |
| Source gathering | Research Agent | Writing, HTML, publishing |
| Article writing | Author Agent | Git push, LinkedIn API |
| Quality assurance | QC Gate | Writing, publishing |
| Git & deploy | Publisher Agent | LinkedIn API, writing |
| Google Sheets | Publisher Agent | LinkedIn API, writing |
| LinkedIn posts | Marketing Agent | Git, Google Sheets, writing |
| Analytics | Metrics Agent | Everything else |
| State file updates | Product Manager | Article content, APIs |
| CLAUDE.md memory | Product Manager | Article content, APIs |

---

## 7. Optimization Loop

After each publish cycle, the Product Manager reviews:

1. **Impressions:** Did the article hit average or above? (`post_analytics.csv`)
2. **CTR:** Click-through rate vs. site average?
3. **Category performance:** Which categories drive the most engagement?
4. **Hook performance:** Which personal reshare hook style drove most clicks?
5. **Publish time:** Did time of day affect reach?

Feed findings back into:
- `CLAUDE.md` — update what's working / what's not
- Editorial calendar — weight toward high-performing categories
- `linkedin_poster.py` → `_personal_hook()`, `_personal_tldr()`, `_personal_cta()` — refine copy

---

## 8. Current Pipeline Status (June 21, 2026)

| Stage | Status | Notes |
|-------|--------|-------|
| Research | Manual | No dedicated research brief cache yet |
| Editorial Calendar | Working | `aima-editorial-calendar.md` + state file |
| Author | Working | Via `aima-article-coworker` Cowork task |
| QC Gate | Manual (human) | No automated checker yet |
| Publisher | Working | `git push` + deploy guard + GS logging |
| Marketing | Working | `python linkedin_pipeline/pipeline.py` |
| Metrics | Partially working | Needs token refresh for `r_member_social` |
| Product Manager | Manual | Cowork session context |

**Next to build:** Automated QC Gate checker script + research brief cache system.

---

## 9. Key File Paths

```
D:\Apps\DevOps\Github\aima\
├── CLAUDE.md                          ← project memory
├── AGENT-WORKFLOW.md                  ← this document
├── articles/
│   ├── aima-coworker-state.json       ← pipeline state
│   ├── aima-coworker-prompt.md        ← master writing instructions
│   ├── aima-editorial-calendar.md     ← article schedule
│   ├── research/                      ← research briefs (to build)
│   ├── qc/                            ← QC reports (to build)
│   └── personas/
│       ├── dawn-ginhaua.md
│       └── kenji-nakamoto.md
├── img/articles/                      ← cover images (1200x630 JPG)
└── linkedin_pipeline/
    ├── pipeline.py                    ← main marketing runner
    ├── linkedin_poster.py             ← company page + personal reshare
    ├── github_fetcher.py              ← article picker (aima-article-*.html only)
    ├── gs_logger.py                   ← Google Sheets logging
    ├── analytics_collector.py         ← LinkedIn metrics
    ├── xls_import.py                  ← analytics fallback (XLS export)
    ├── posted_articles.json           ← LinkedIn posting tracker
    ├── post_log.json                  ← post IDs for analytics
    ├── pipeline.log                   ← execution log
    └── .env                           ← tokens and IDs (gitignored)
```
