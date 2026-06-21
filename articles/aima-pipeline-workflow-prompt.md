# AIMA ARTICLE PIPELINE
## Workflow Diagram Prompt — Complete Specification
### Version 1.1.0 · 2026-06-20 · Author: Joselito Sering

---

## HOW TO USE THIS DOCUMENT

Paste the **DIAGRAM PROMPT** section (at the bottom) directly into Eraser AI, Lucidchart AI,
Mermaid Live, or any AI diagramming tool. The sections above it are the structured source-of-truth
data used to build that prompt — keep them for version control and retrospective updates.

---

## SECTION 1 — SYSTEM OVERVIEW

**System Name:** AIMA Article Pipeline  
**Type:** Automated content production and distribution pipeline  
**Cadence:** Scheduled daily (06:00 trigger) + on-demand  
**Actors:** Human (editorial decisions, QA), AI Agent (research, drafting, commentary), APIs (GitHub, LinkedIn, GA4)  
**Output:** Static HTML article live on aima.productions + LinkedIn post published  
**Loop:** Agile retrospective feeds back into editorial calendar after every post cycle  

### Processing Model
- **Serial:** Phases run in strict sequence — each phase output is the next phase input
- **Parallel Fork (Phase 3):** After git push, GitHub Pages deploy and LinkedIn Pipeline run simultaneously
- **Parallel Within LinkedIn:** HTML fetch, hook extraction, and persona commentary run concurrently
- **Parallel (Phase 4):** post_log write and analytics collection run simultaneously
- **Join:** Both parallel tracks must complete before advancing

---

## SECTION 2 — NODE DEFINITIONS WITH DATA POINTS

### SUBSYS-01: IDEATION

---

**NODE: EDITORIAL CALENDAR**  
Type: START · Human Decision  
Color: Amber (#f5a623)  
Shape: Rounded Rectangle (start terminal)

Data Schema:
```
article_id        : INT        — sequential, 3-digit zero-padded (e.g., 014)
title             : STRING     — working title (editable pre-draft)
topic             : STRING     — subject/angle of the article
persona           : ENUM       — joselito | dawn | kenji
category          : ENUM       — AI Ethics | AI Tools | Creative AI | Strategy | Emerging Tech
tone              : ENUM       — investigative | educational | provocative | analytical | inspirational
mood              : ENUM       — urgent | contemplative | optimistic | critical | visionary
scheduled_date    : ISO8601    — target publish date
estimated_read    : INT (min)  — 3–10 min range
target_audience   : STRING     — primary reader persona description
notes             : STRING     — optional editorial notes
state_file        : PATH       — articles/aima-coworker-state.json
```

Output signal: `ARTICLE_PARAMS_JSON → COWORK_TRIGGER`

---

**NODE: COWORK TRIGGER**  
Type: AUTOMATED · Scheduled Task  
Color: Cyan (#00d9f5)  
Shape: Rectangle with gear icon

Data Schema:
```
trigger_id        : UUID       — unique session identifier
trigger_time      : ISO8601    — scheduled execution time (06:00 default)
state_file_path   : PATH       — articles/aima-coworker-state.json
agent_model       : STRING     — claude-sonnet-4-6
session_id        : UUID       — Cowork session reference
params_loaded     : BOOL       — confirms state.json parsed successfully
retry_count       : INT        — max 3 before alert
```

Output signal: `TRIGGER_CONTEXT → TOPIC_RESEARCH`

---

**NODE: WRITER PERSONA**  
Type: HUMAN DECISION · Config  
Color: Amber (#f5a623)  
Shape: Rectangle with person icon

Data Schema:
```
persona_id        : ENUM       — joselito | dawn | kenji
brand_color_hex   : STRING     — joselito=00D9F5 | dawn=9B59F5 | kenji=F5C518
photo_path        : PATH       — ../img/author-{persona}.png
bmac_url          : URL        — https://www.buymeacoffee.com/{persona}
bmac_button_color : STRING     — hex without # (matches brand_color)
voice_descriptor  : STRING     — investigative/reflective | ethical/philosophical | technical/precise
commentary_style  : STRING     — persona-specific LinkedIn voice prompt template
article_meta_tag  : STRING     — <meta name="article:persona" content="{persona_id}"/>
```

Output signal: `PERSONA_CONFIG → LINKEDIN_PIPELINE (async reference)`

---

### SUBSYS-02: CONTENT GENERATION

---

**NODE: TOPIC RESEARCH** *(Parallel: Web Search ∥ AI Synthesis)*  
Type: AUTOMATED · Parallel Processing  
Color: Cyan (#00d9f5)  
Shape: Rectangle with parallel bars (∥)

Sub-process A — Web Search:
```
tool              : WebSearch
queries           : STRING[]   — 3–5 targeted queries derived from topic
sources_fetched   : INT        — target ≥ 8
citations         : ARRAY      — [{title, url, date, relevance_score}]
date_range        : STRING     — prefer sources < 18 months old
```

Sub-process B — AI Synthesis:
```
input             : citations + article_params
output_brief      : {
  key_arguments   : STRING[5]  — ranked by impact
  structure       : STRING[]   — proposed section headings
  hook_candidates : STRING[3]  — potential opening lines
  word_count_est  : INT        — target 1200–2000 words
  evidence_gaps   : STRING[]   — flagged for human review
}
```

Join output: `RESEARCH_BRIEF_JSON → AI_ARTICLE_DRAFT`

---

**NODE: AI ARTICLE DRAFT**  
Type: AUTOMATED  
Color: Cyan (#00d9f5)  
Shape: Rectangle with document icon

Input: `RESEARCH_BRIEF_JSON + ARTICLE_PARAMS + PERSONA_CONFIG`

Output schema — `article-{slug}-{id}.html`:
```
META TAGS:
  article:id          : INT
  article:title       : STRING
  article:author      : STRING    — persona display name
  article:persona     : ENUM
  article:category    : STRING
  article:header-image: PATH
  article:prev-url    : URL | ""
  article:prev-title  : STRING | ""
  article:next-url    : URL | ""
  article:next-title  : STRING | ""

HTML STRUCTURE:
  #hero               : header image + title + meta bar
  #hook               : opening paragraph (from hook_candidates[best])
  #body               : n sections (h2 + paragraphs + optional pull quotes)
  #cta                : call to action block
  #author-card        : persona photo + bio + BMAC button
  #nav-cards          : prev/next article navigation (GAS-driven)
  #back-to-top        : scroll helper

JAVASCRIPT BLOCKS:
  applyNav()          : GAS fetch → live prev/next from Google Sheets
  authorPhoto()       : loads ../img/author-{persona}.png
  fadeIn()            : opacity transition on load
  closeMobile()       : mobile nav toggle

QUALITY METRICS (auto-computed):
  word_count          : INT    — target 1200–2000
  section_count       : INT    — target 4–7 H2 sections
  image_refs          : INT    — ≥ 1
  meta_completeness   : FLOAT  — 0.0–1.0 (all tags filled = 1.0)
  html_valid          : BOOL   — </html> present, UTF-8 clean
```

Output signal: `HTML_DRAFT → QUALITY_GATE`

---

### GATEWAY-01: QUALITY GATE

Type: HUMAN DECISION · Exclusive Gateway (XOR)  
Color: Amber (#f5a623)  
Shape: Diamond ◇

**Checklist — all items must pass for YES:**
```
QG-01  article:id is next in sequence (no gaps, no duplicates)
QG-02  All meta tags present and non-empty
QG-03  persona matches requested writer (joselito/dawn/kenji)
QG-04  BMAC button color matches persona brand_color
QG-05  Author avatar loads (../img/author-{persona}.png resolves)
QG-06  Prev/next nav meta tags consistent with neighboring articles
QG-07  HTML validates: </html> present, no truncation, UTF-8 clean
QG-08  Word count in target range (1000–2500)
QG-09  At least one H2 section heading present
QG-10  No placeholder text (TODO, [FILL IN], undefined)
```

**Gateway Conditions:**
```
PASS  (all 10 checks green) → git commit + push
FAIL  (any check red)       → return to AI_ARTICLE_DRAFT with failure_flags[]
```

**Failure handling:**
```
failure_flags    : STRING[]  — list of failed check IDs (QG-01 … QG-10)
revision_notes   : STRING    — human-written correction instructions
max_revisions    : INT       — 3 (after 3rd failure → ESCALATE to human edit)
```

---

### SUBSYS-03: PUBLISH (SERIAL → PARALLEL FORK)

---

**NODE: GIT COMMIT + PUSH**  
Type: AUTOMATED  
Color: Green (#00f088)  
Shape: Rectangle with git icon

Data Schema:
```
commit_hash       : SHA256    — auto-generated
commit_message    : STRING    — "Article {id}: {title}"
branch            : STRING    — main
files_changed     : STRING[]  — [articles/{filename}.html, img/ if new assets]
timestamp         : ISO8601
deploy_triggered  : BOOL      — true (GitHub Actions auto-deploy)
estimated_live_at : ISO8601   — timestamp + 60s
```

Output: **PARALLEL FORK** → [GITHUB_PAGES, LINKEDIN_PIPELINE] simultaneously

---

**FORK NODE: PARALLEL SPLIT**  
Type: AUTOMATED · Parallel Gateway (AND-split)  
Color: Gray (#3a6090)  
Shape: Thick bar with two outgoing arrows

Spawns two independent tracks:
- Track A: `DEPLOY_EVENT → GITHUB_PAGES`
- Track B: `ARTICLE_PARAMS + PERSONA_CONFIG → LINKEDIN_PIPELINE`

---

**NODE: GITHUB PAGES** *(Track A)*  
Type: LIVE / PUBLISHED  
Color: Green (#00f088)  
Shape: Cloud/Server rectangle

Data Schema:
```
live_url          : URL       — https://aima.productions/articles/{slug}-{id}.html
cdn_status        : ENUM      — DEPLOYING | LIVE | ERROR
deploy_latency_s  : INT       — typically 30–90s
cache_ttl_s       : INT       — 300 (5 min CDN TTL)
gas_nav_status    : ENUM      — SYNCED | PENDING | ERROR
  gas_url         : URL       — Google Apps Script exec URL
  gas_action      : STRING    — ?action=all
  nav_updated_at  : ISO8601
robots_indexed    : BOOL      — true (sitemap auto-updated)
```

Track A completes → **waits at JOIN node**

---

**NODE: LINKEDIN PIPELINE** *(Track B — entry)*  
Type: AUTOMATED  
Color: Cyan (#00d9f5)  
Shape: Rectangle with LinkedIn icon

Data Schema:
```
pipeline_session  : UUID
persona           : ENUM      — inherits from ARTICLE_PARAMS
article_url       : URL       — from git commit deploy URL
oauth_scope       : STRING    — w_member_social
token_valid       : BOOL      — checked before proceeding
token_expiry      : ISO8601
state             : ENUM      — INIT | FETCHING | BUILDING | POSTING | DONE | ERROR
```

Triggers **inner PARALLEL SPLIT** → [FETCH_HTML, EXTRACT_HOOK, PERSONA_COMMENTARY]

---

**INNER FORK: LinkedIn Parallel Processing**  
Type: AUTOMATED · Parallel Gateway (AND-split)  
Color: Gray (#3a6090)

Three sub-processes run simultaneously:

**Sub-node A: FETCH ARTICLE HTML**
```
tool              : github_fetcher.py
input             : article_url
output            : {
  raw_html        : STRING    — full HTML content
  parsed_meta     : OBJECT    — all article:* meta tag values
  title           : STRING
  persona         : STRING
  category        : STRING
  word_count      : INT
  fetch_latency_ms: INT
}
```

**Sub-node B: EXTRACT HOOK (NLP)**
```
tool              : extract_hook()
input             : raw_html → first H2 section text
output            : {
  hook_sentence   : STRING    — 1–2 sentences, high-impact opening
  char_count      : INT       — target 100–200 chars
  confidence      : FLOAT     — 0.0–1.0
  fallback        : STRING    — article title if confidence < 0.6
}
```

**Sub-node C: PERSONA COMMENTARY**
```
tool              : build_personal_commentary()
input             : parsed_meta + persona_config + article summary
output            : {
  commentary_text : STRING    — 200–500 chars, persona voice
  char_count      : INT
  hashtags        : STRING[]  — 3–5 relevant hashtags
  cta_line        : STRING    — closing call-to-action
}
```

Inner JOIN → continues to IMAGE_UPLOAD

---

**NODE: DIRECT IMAGE UPLOAD**  
Type: AUTOMATED  
Color: Cyan (#00d9f5)  
Shape: Rectangle with image icon

Data Schema:
```
source_image      : URL       — article header-image meta tag value
upload_endpoint   : URL       — LinkedIn media upload API
content_type      : STRING    — image/jpeg | image/png
file_size_bytes   : INT       — max 5MB enforced
output            : {
  asset_urn       : STRING    — urn:li:digitalmediaAsset:{id}
  upload_status   : ENUM      — PROCESSING | AVAILABLE | FAILED
  poll_interval_s : INT       — 2s polling until AVAILABLE
}
```

---

**GATEWAY-02: IMAGE UPLOAD SUCCESS?**  
Type: AUTOMATED · Exclusive Gateway  
Color: Cyan (#00d9f5)  
Shape: Diamond ◇

```
SUCCESS           → proceed to UGC_POSTS_API (with asset_urn)
FAILED            → post without image (text-only fallback)
TIMEOUT (>30s)    → post without image + log warning
```

---

**NODE: UGC POSTS API**  
Type: AUTOMATED → LIVE  
Color: Green (#00f088)  
Shape: Rectangle with send icon

Input payload:
```
author            : STRING    — urn:li:person:{member_id}
lifecycleState    : STRING    — PUBLISHED
specificContent:
  ugcPost:
    shareCommentary:
      text        : STRING    — hook_sentence + "

" + commentary_text + "

" + hashtags[]
    shareMediaCategory: ARTICLE | IMAGE
    media[0]:
      status      : READY
      description.text: STRING — article title
      originalUrl : URL       — live_url
      title.text  : STRING
      thumbnails[0].url: URL  — asset_urn (if available)
visibility:
  memberNetworkVisibility: PUBLIC
```

Output:
```
post_urn          : STRING    — urn:li:ugcPost:{id}
share_urn         : STRING    — urn:li:share:{id}
share_url         : URL       — https://www.linkedin.com/feed/update/{share_urn}
posted_at         : ISO8601
http_status       : INT       — 201 = success
char_count        : INT       — post text length (LinkedIn limit: 3000)
```

---

**GATEWAY-03: POST SUCCESS?**  
Type: AUTOMATED · Exclusive Gateway  
Color: Green (#00f088)  
Shape: Diamond ◇

```
201 CREATED       → advance to JOIN node
400 BAD REQUEST   → log + alert human → MANUAL_POST endpoint
401 UNAUTHORIZED  → trigger token_refresh → retry once → MANUAL_POST
429 RATE LIMITED  → wait 60s → retry once → MANUAL_POST
5xx SERVER ERROR  → wait 30s → retry twice → MANUAL_POST
```

---

**JOIN NODE: PARALLEL MERGE**  
Type: AUTOMATED · Parallel Gateway (AND-join)  
Color: Gray (#3a6090)  
Shape: Thick bar with two incoming arrows

Waits for:
- Track A: `GITHUB_PAGES.cdn_status = LIVE`
- Track B: `UGC_POSTS_API.http_status = 201` (or MANUAL_POST fallback)

Both resolved → `→ POST_OUTPUT`

---

**NODE: POST OUTPUT** *(Terminal — Happy Path)*  
Type: LIVE / PUBLISHED · END NODE  
Color: Green (#00f088)  
Shape: Stadium/Rounded Rectangle (terminal)

State record:
```
article_id        : INT
article_url       : URL       — aima.productions/articles/{slug}-{id}.html
linkedin_url      : URL       — linkedin.com/feed/update/{share_urn}
post_urn          : STRING    — urn:li:ugcPost:{id}
share_urn         : STRING    — urn:li:share:{id}
persona           : ENUM
posted_at         : ISO8601
calendar_status   : STRING    → PUBLISHED (syncPublished() auto-updates dashboard)
```

→ PARALLEL FORK → [POST_LOG_JSON, ANALYTICS_COLLECTION]

---

### SUBSYS-04: ANALYTICS + FEEDBACK QA

---

**PARALLEL SPLIT — Analytics Collection**

**Sub-node A: POST LOG JSON**
```
file              : post_log.json
append_entry      : {
  article         : STRING    — filename (e.g., aima-article-ethics-theater-014.html)
  post_id         : STRING    — share_urn
  persona         : ENUM
  posted_at       : ISO8601
  analytics_collected: BOOL   — false (updated by analytics job)
}
drives            : syncPublished() in article-manager.html
```

**Sub-node B: ANALYTICS COLLECTION**
```
GA4 Events:
  page_view         : {page_url, session_id, timestamp, referrer, device}
  coffee_click      : {article_id, persona, button_color, timestamp}
  scroll_depth      : {article_id, depth_pct: 25|50|75|90|100, timestamp}
  time_on_page      : {article_id, duration_s, timestamp}
  nav_click         : {article_id, direction: prev|next, target_id}

LinkedIn Analytics (post-48h collection):
  impressions       : INT
  unique_views      : INT
  clicks            : INT
  ctr               : FLOAT     — clicks / impressions
  reactions         : INT       — total (like + celebrate + insightful + etc.)
  reaction_breakdown: OBJECT    — {like, celebrate, insightful, support, funny, love}
  comments          : INT
  reposts           : INT
  engagement_rate   : FLOAT     — (reactions + comments + reposts) / impressions

Collection method:
  primary           : /rest/socialMediaPostStatistics (r_member_social scope)
  fallback          : xls_import.py (manual LinkedIn Analytics XLS export)

Output:
  ga4_traffic.csv   : appended row
  post_analytics.csv: appended row
```

**GATEWAY-04: ANALYTICS COMPLETE?**
```
COMPLETE          → advance to DASHBOARD
PARTIAL           → flag analytics_collected = partial, advance with warning
MISSING (>7 days) → escalate to human review, advance with MISSING flag
```

Analytics JOIN → `→ DASHBOARD_KPIS`

---

**NODE: DASHBOARD / KPIs**  
Type: DATA · Analytics  
Color: Purple (#9966ff)  
Shape: Rectangle with chart icon

File: `article-manager.html`

Data Sources auto-loaded:
```
post_log.json     → syncPublished() → CALENDAR published status
ga4_traffic.csv   → autoLoadGA4() → site traffic metrics
post_analytics.csv→ analytics section → LinkedIn performance
```

KPI Card Definitions (8-card overview):
```
KPI-01  Total Posts Published    : COUNT(post_log entries)
KPI-02  Avg Impressions          : MEAN(post_analytics.impressions)
KPI-03  LI Profile Traffic       : SUM(ga4.referrer = linkedin.com, last_30d)
KPI-04  Company Page Reach       : SUM(post_analytics.unique_views, last_30d)
KPI-05  Avg CTR                  : MEAN(post_analytics.ctr)
KPI-06  Articles Remaining       : COUNT(CALENDAR where published=false and scheduled_date <= today+30)
KPI-07  Top Writer               : PERSONA with MAX(heat_score)
KPI-08  Top Category             : CATEGORY with MAX(avg_engagement_rate)
```

Heat Score Formula (composite metric):
```
heat_score = (
  (impressions     / BASELINE_IMPRESSIONS)   * 0.20 +
  (ctr             / BASELINE_CTR)           * 0.25 +
  (engagement_rate / BASELINE_ENGAGEMENT)    * 0.25 +
  (coffee_clicks   / BASELINE_COFFEE)        * 0.15 +
  (scroll_depth_75 / TOTAL_SESSIONS)         * 0.15
)
* recency_multiplier(days_since_post)

Recency multiplier:
  0–7 days    : 1.0
  8–30 days   : 0.85
  31–90 days  : 0.70
  90+ days    : 0.50
```

Baseline values (updated quarterly):
```
BASELINE_IMPRESSIONS : 500
BASELINE_CTR         : 0.030  (3%)
BASELINE_ENGAGEMENT  : 0.040  (4%)
BASELINE_COFFEE      : 2
```

---

### SUBSYS-05: OPTIMIZE + AGILE ITERATE

---

**NODE: OPTIMIZE + ITERATE**  
Type: OPTIMIZE / ITERATE · Loop Back  
Color: Red-Orange (#ff6644)  
Shape: Rectangle with loop arrow

Retrospective Input Data:
```
lookback_window   : INT       — last 4 articles (rolling)
per_article       : {
  heat_score
  top_reaction_type
  best_performing_section (from scroll_depth)
  most_clicked_nav
  coffee_click_rate
  linkedin_ctr
  avg_read_time_s
}
```

**GATEWAY-05: OPTIMIZATION THRESHOLD**  
Type: AUTOMATED + Human Review · Exclusive Gateway  
Shape: Diamond ◇

```
heat_score > 1.2      CONTINUE   — current approach working, minor tune
heat_score 0.8–1.2    ADJUST     — tune 1–2 variables (topic, tone, persona)
heat_score < 0.8      PIVOT      — major calendar revision + persona A/B test
heat_score < 0.5      ESCALATE   — human editorial review required
```

Actions per gate:
```
CONTINUE:
  ─ Reinforce top persona and top category in next 2 articles
  ─ Minor hook style adjustment
  ─ git tag v1.x.x (version stamp)

ADJUST:
  ─ Swap underperforming persona for 1 article
  ─ Revise tone/mood on next scheduled topic
  ─ Update persona voice prompts in skeleton.html
  ─ Log adjustment in OPTIMIZATION_HISTORY

PIVOT:
  ─ Pause 2 scheduled articles, re-evaluate topics
  ─ Run A/B test: same topic, 2 different personas
  ─ Revise skeleton.html template structure
  ─ Human editorial calendar review
  ─ Update BASELINE values in dashboard

ESCALATE:
  ─ Human writes next article manually (bypass AI draft)
  ─ Full pipeline audit
  ─ Consider category expansion
```

Optimization History log:
```
optimization_log.json entries:
  {
    date              : ISO8601
    articles_reviewed : INT[]
    gate_result       : ENUM    — CONTINUE | ADJUST | PIVOT | ESCALATE
    actions_taken     : STRING[]
    heat_score_before : FLOAT
    heat_score_target : FLOAT
  }
```

Output: → LOOP BACK → EDITORIAL_CALENDAR (with optimization_flags[])

---

## SECTION 3 — ENDPOINT DEFINITIONS

```
ENDPOINT-01  START        : EDITORIAL_CALENDAR (article scheduled → trigger fires)
ENDPOINT-02  HAPPY PATH   : POST_OUTPUT (article live + LinkedIn posted)
ENDPOINT-03  QA FAIL LOOP : QUALITY_GATE → AI_ARTICLE_DRAFT (max 3 revisions)
ENDPOINT-04  MANUAL POST  : Human posts LinkedIn manually (API failure fallback)
ENDPOINT-05  QUARANTINE   : Article fails QG-01–10 after 3 revisions → human edit
ENDPOINT-06  AGILE LOOP   : OPTIMIZE → EDITORIAL_CALENDAR (new cycle begins)
```

---

## SECTION 4 — GUARDRAILS

### G-01: Token / OAuth Guardrail
```
Check     : OAuth token expiry before any LinkedIn API call
Condition : token_expiry > now() + 5min
Action    : PASS → proceed | FAIL → refresh token → retry 1x → MANUAL_POST
Scope     : w_member_social (posting) · r_member_social (analytics)
```

### G-02: Meta Completeness Guardrail
```
Check     : All article:* meta tags present and non-empty before git push
Fields    : id, title, author, persona, category, header-image
Action    : PASS → proceed | FAIL → return to AI_ARTICLE_DRAFT with flag
```

### G-03: Article ID Sequence Guardrail
```
Check     : article:id == MAX(existing_ids) + 1
Condition : No gaps, no duplicates, 3-digit zero-padded
Action    : PASS → proceed | FAIL → block QA gate, alert human
```

### G-04: LinkedIn Character Limit Guardrail
```
Check     : post_text.length <= 3000 chars (LinkedIn hard limit)
Fields    : hook_sentence + commentary_text + hashtags
Action    : PASS → proceed | FAIL → trim commentary_text to fit, flag for review
Priority  : hook_sentence preserved first, then commentary, hashtags last
```

### G-05: Image Format + Size Guardrail
```
Check     : image format (JPEG/PNG only) and size (≤ 5MB)
Action    : PASS → proceed | FAIL → use text-only post (no image)
Log       : image_guardrail_violations.log
```

### G-06: UTF-8 File Integrity Guardrail
```
Check     : HTML file decodes cleanly as UTF-8, </html> present, not truncated
Tool      : Python open(path, 'r', encoding='utf-8') + raw.decode('utf-8')
Action    : PASS → proceed | FAIL → restore from git HEAD, re-apply patches
Note      : NEVER use sed -i on article files (causes UTF-8 truncation on mounted FS)
```

### G-07: Rate Limit Guardrail
```
Check     : LinkedIn API call frequency ≤ 1 post per 10 minutes
Action    : PASS → proceed | EXCEEDED → queue with exponential backoff (60s, 120s, 240s)
```

### G-08: Analytics Data Freshness Guardrail
```
Check     : analytics collection within 48h of post_date
Action    : COMPLETE → load normally | STALE → flag in dashboard with ⚠️ indicator
```

### G-09: Duplicate Post Guardrail
```
Check     : post_log.json has no entry for this article_id
Action    : CLEAN → proceed | DUPLICATE DETECTED → halt, alert human, do not re-post
```

### G-10: Agile Loop Rate Guardrail
```
Check     : Optimization review triggered no more than weekly
Action    : THROTTLE if loop fires faster than 7 days (prevents micro-optimization churn)
```

---

## SECTION 5 — METRICS EVALUATION FRAMEWORK

### Primary Metrics (post-level, collected per article)
```
METRIC              SOURCE          TARGET      ALERT THRESHOLD
impressions         LinkedIn API    ≥ 500       < 200 (3 consecutive)
unique_views        LinkedIn API    ≥ 300       —
clicks              LinkedIn API    ≥ 20        —
ctr                 Calculated      ≥ 3.0%      < 1.5%
reactions           LinkedIn API    ≥ 15        < 5 (3 consecutive)
engagement_rate     Calculated      ≥ 4.0%      < 2.0%
reposts             LinkedIn API    ≥ 2         —
comments            LinkedIn API    ≥ 1         —
```

### Secondary Metrics (site-level, GA4)
```
METRIC              SOURCE          TARGET      ALERT THRESHOLD
page_views          GA4             ≥ 100/30d   —
coffee_click_rate   GA4             ≥ 0.5%      —
scroll_75pct        GA4             ≥ 40%       < 20%
avg_time_on_page_s  GA4             ≥ 180s      < 60s
bounce_rate         GA4             ≤ 60%       > 80%
linkedin_referral   GA4             ≥ 30%       —
```

### Composite Score
```
heat_score          Calculated      ≥ 1.0       < 0.8 (triggers ADJUST gate)
```

### Evaluation Cadence
```
REAL-TIME     : LinkedIn post published → impression counter starts
+2h           : First engagement snapshot (early signal)
+24h          : Primary analytics pull (reactions, CTR)
+48h          : Full analytics collection (final numbers)
+7d           : Weekly retrospective → OPTIMIZATION_GATEWAY
+30d          : Monthly roll-up → BASELINE calibration review
+90d          : Quarterly BASELINE update + pipeline version bump
```

### A/B Test Framework
```
Trigger       : OPTIMIZATION_GATEWAY result = ADJUST or PIVOT
Variable      : persona | tone | category | hook_style | post_length
Control       : previous article (same category)
Variant       : next article (modified variable)
Measurement   : heat_score delta after 48h
Decision rule : Variant wins if heat_score_delta > 0.15
Minimum tests : 3 articles per variable before declaring winner
```

---

## SECTION 6 — DIAGRAM PROMPT

*Paste this entire block into Eraser AI, Lucidchart AI, or any AI diagramming tool.*

---

```
DIAGRAM: AIMA Article Pipeline — Serial + Parallel Workflow
STYLE: Dark blueprint engineering diagram. Navy background (#070c1a).
Fine crosshatch grid. Monospace fonts. Chamfered rectangle nodes.
Orthogonal routing only (no diagonal lines). Small port squares at
connection endpoints. Color-coded by node type (see LEGEND).

LEGEND:
  Amber  (#f5a623) = HUMAN DECISION
  Cyan   (#00d9f5) = AUTOMATED PROCESS
  Green  (#00f088) = LIVE / PUBLISHED
  Purple (#9966ff) = ANALYTICS / DATA
  Red    (#ff6644) = OPTIMIZE / ITERATE
  Gray   (#3a6090) = PARALLEL FORK / JOIN BAR

NODE SHAPES:
  Stadium (rounded ends)  = START / END terminals
  Chamfered rectangle     = Process nodes
  Diamond ◇               = Gateway (decision point)
  Dashed border rectangle = Parallel sub-step
  Thick horizontal bar    = Fork / Join parallel gateway

--- SUBSYSTEM 01: IDEATION ---

[START] EDITORIAL CALENDAR
  Type: Human Decision (amber)
  Data: article_id · title · topic · persona · category · tone · date
  Out → [signal: ARTICLE_PARAMS_JSON] → COWORK TRIGGER

COWORK TRIGGER
  Type: Automated (cyan)
  Data: trigger_time=06:00 · state_file=aima-coworker-state.json · model=claude-sonnet-4-6
  Out → [signal: TRIGGER_CONTEXT] → TOPIC RESEARCH

WRITER PERSONA [parallel config node, feeds LinkedIn Pipeline later]
  Type: Human Decision (amber)
  Data: persona_id · brand_color · photo_path · voice_model · bmac_url
  Out → [async signal] → LINKEDIN PIPELINE

--- SUBSYSTEM 02: CONTENT GENERATION ---

TOPIC RESEARCH [∥ WEB SEARCH + AI SYNTHESIS — parallel]
  Type: Automated Parallel (cyan, parallel bars icon)
  Sub-A: WebSearch → citations[] · sources_fetched≥8
  Sub-B: AI Synthesis → key_arguments[5] · structure_outline · hook_candidates[3]
  Join → [signal: RESEARCH_BRIEF_JSON] → AI ARTICLE DRAFT

AI ARTICLE DRAFT
  Type: Automated (cyan)
  Data: skeleton.html → meta_tags{id,title,author,persona,category,header-image,prev-url,next-url}
        + sections{hook,body[],cta,author_card} + applyNav() GAS + authorPhoto() JS
        + QC: word_count · meta_completeness · html_valid · no_placeholder_text
  Out → [signal: HTML_DRAFT] → ◇ QUALITY GATE

◇ QUALITY GATE [GATEWAY-01]
  Type: Human Decision (amber diamond)
  Checklist: QG-01 id_sequence · QG-02 meta_complete · QG-03 persona_match
             QG-04 bmac_color · QG-05 avatar_loads · QG-06 nav_consistent
             QG-07 html_valid · QG-08 word_count · QG-09 has_h2 · QG-10 no_placeholders
  YES (all pass) → GIT COMMIT + PUSH
  NO  (any fail) → return to AI ARTICLE DRAFT [max 3 revisions]
  ESCALATE (3rd fail) → [END: QUARANTINE — human manual edit]

--- SUBSYSTEM 03: PUBLISH ---

GIT COMMIT + PUSH
  Type: Automated (green)
  Data: commit_hash · message="Article {id}: {title}" · branch=main
        estimated_live_at = now()+60s
  Out → [PARALLEL FORK ═══════════════]
                         ↙             ↘
              Track A (green)      Track B (cyan)

Track A: GITHUB PAGES
  Type: Live/Published (green)
  Data: live_url=aima.productions/articles/{slug}-{id}.html
        cdn_status=LIVE · gas_nav_status=SYNCED
  Wait at JOIN

Track B: LINKEDIN PIPELINE
  Type: Automated (cyan)
  Data: oauth_scope=w_member_social · token_valid=checked
  Out → [INNER PARALLEL FORK ══════════════════]
                 ↙            ↓             ↘
        FETCH HTML       EXTRACT HOOK    COMMENTARY
        (dashed cyan)    (dashed cyan)   (dashed cyan)

  FETCH HTML: github_fetcher.py → raw_html · parsed_meta{}
  EXTRACT HOOK: extract_hook() NLP → hook_sentence · confidence≥0.6
  COMMENTARY: build_personal_commentary() → commentary_text · hashtags[] · cta_line

  [INNER JOIN ══════════════════]
  ↓
  DIRECT IMAGE UPLOAD
    Type: Automated (cyan)
    Data: source=header-image meta · output=urn:li:digitalmediaAsset
    ◇ [GATEWAY-02: IMAGE SUCCESS?]
      SUCCESS → include asset_urn in post
      FAILED  → text-only fallback

  UGC POSTS API
    Type: Automated→Live (green)
    Data: payload={author_urn, shareCommentary=hook+commentary+hashtags,
                   shareMediaCategory=ARTICLE, media[0].originalUrl=live_url}
          char_count ≤ 3000 (GUARDRAIL G-04)
    ◇ [GATEWAY-03: POST SUCCESS?]
      201 CREATED        → JOIN
      401/429/5xx        → retry → [END: MANUAL POST fallback]

[FINAL JOIN ═══════════════════════════════]
Track A (GitHub Pages LIVE) + Track B (UGC 201) both resolve
↓

[END: ✓ POST OUTPUT]
  Type: Live/Published (green terminal)
  Data: article_url · linkedin_url · post_urn · share_urn · posted_at
        calendar_status → PUBLISHED (auto via syncPublished())

Out → [PARALLEL FORK ═══════════════]
               ↙                    ↘
    POST LOG JSON              GA4 + LI ANALYTICS
    (dashed purple)            (dashed purple)
    post_log.json append       ga4_traffic.csv + post_analytics.csv
    drives syncPublished()     collected after 48h

◇ [GATEWAY-04: ANALYTICS COMPLETE?]
  COMPLETE → DASHBOARD
  PARTIAL  → DASHBOARD (with warning flag)
  MISSING  → DASHBOARD (with alert, human review)

[ANALYTICS JOIN ═══════════════════]
↓

--- SUBSYSTEM 04: ANALYTICS ---

DASHBOARD / KPIs
  Type: Data/Analytics (purple)
  Data: article-manager.html · 8-KPI overview
        heat_score = weighted composite (impressions 20% + ctr 25% + engagement 25% + coffee 15% + scroll 15%)
        baselines: impressions=500 · ctr=3% · engagement=4% · coffee=2
        writer cards · category rankings · coffee_click leaderboard

--- SUBSYSTEM 05: OPTIMIZE ---

OPTIMIZE + ITERATE ↺
  Type: Optimize/Iterate (red)
  Data: lookback=last_4_articles · optimization_log.json

◇ [GATEWAY-05: OPTIMIZATION THRESHOLD]
  heat > 1.2   CONTINUE  → reinforce top persona + category · git tag v1.x.x
  0.8–1.2      ADJUST    → swap persona · revise tone · update voice prompts
  0.5–0.8      PIVOT     → A/B test · revise skeleton.html · editorial review
  < 0.5        ESCALATE  → human manual write · pipeline audit

Output → [AGILE LOOP BACK ↺] → EDITORIAL CALENDAR
  (loop carries: optimization_flags[] + top_persona + top_category + adjusted_baselines)

--- GUARDRAILS (annotate on diagram as red warning badges) ---

G-01  OAuth token check before ANY LinkedIn call
G-02  Meta completeness gate before git push
G-03  Article ID sequence validation (no gaps/duplicates)
G-04  LinkedIn 3000-char post text limit
G-05  Image format/size ≤ 5MB (JPEG/PNG only)
G-06  UTF-8 file integrity — never use sed -i on article files
G-07  LinkedIn API rate limit — max 1 post per 10 min
G-08  Analytics freshness — flag stale data > 48h
G-09  Duplicate post detection — block re-post of same article_id
G-10  Agile loop throttle — max 1 optimization review per 7 days

--- ENDPOINTS ---

START-01   : Editorial Calendar (article scheduled)
HAPPY      : ✓ POST OUTPUT (article live + LinkedIn posted)
FALLBACK-01: MANUAL POST (API failure, human posts LinkedIn)
FALLBACK-02: QUARANTINE (QA fails 3x, human edits article)
LOOP       : OPTIMIZE → EDITORIAL CALENDAR (agile cycle continues)
```

---

*End of prompt block.*

---

## SECTION 7 — VERSION HISTORY

```
v1.0.0  2026-06-19  Initial pipeline operational (articles 001–013)
v1.1.0  2026-06-20  GAS nav · author photo · analytics sync · blueprint diagram
v1.1.1  [next]      r_member_social token · automated analytics collection
```

---

*AIMA Article Pipeline — Workflow Diagram Prompt*  
*© 2026 Joselito Sering · aima.productions*
