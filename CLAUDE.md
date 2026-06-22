# AIMA Project Memory

## Pending Actions

### LinkedIn Marketing API — Development Tier Approval
- **Status:** APPROVED June 20, 2026 (Advertising API, app id 253440006)
- **SCOPES updated:** `r_member_social` added to `linkedin_pipeline/linkedin_auth.py`
- **NEXT STEP:** Run `python linkedin_pipeline/linkedin_auth.py` to get a new token with `r_member_social`
- Then test: `python linkedin_pipeline/analytics_collector.py`
- **analytics_collector.py is ready** — already uses `/rest/socialMediaPostStatistics`, no code changes needed after token refresh

---

## LinkedIn Pipeline — Current State (as of June 21, 2026)

### APPROVED POST-PUBLISH WORKFLOW
After every article is written, pushed, and live on GitHub Pages:
1. `git push` — publishes article to `joselitosering.github.io/aima`
2. `python linkedin_pipeline/pipeline.py` — runs the full sequence automatically:
   - Posts to **AIMA company page** with cover image + article hook + hashtags + **persona byline** (name credit)
   - Immediately **reshares to Joselito's personal profile** with persona-tailored intro + **TL;DR** + CTA
   - Logs post IDs to `post_log.json` for 48h analytics collection
   - Google Sheets logging is also triggered inside the pipeline (Step 8 can be skipped manually if pipeline runs)

This workflow was tested and approved June 21, 2026.

### Technical State
- **Company page posting:** Working. `linkedin_poster.py` posts as `urn:li:organization:{ORG_ID}` with direct image upload via Assets API. Byline appears at end of commentary.
- **Personal reshare:** Working. `reshare_to_personal()` uses `/rest/posts` with `reshareContext`. Commentary built by `build_personal_commentary()` — persona-aware hook + TL;DR + CTA.
- **Scopes required:** `w_organization_social` (company page) + `w_member_social` (personal reshare)
- **Analytics:** Approved for `r_member_social` June 20, 2026. Needs token refresh: `python linkedin_pipeline/linkedin_auth.py`. Then test: `python linkedin_pipeline/analytics_collector.py`
- **Analytics fallback:** `xls_import.py` to import from LinkedIn Analytics XLS export until token refreshed.

---

## article-manager.html Dashboard — Current State (as of June 20, 2026)

- **GA4 auto-load:** `ga4_traffic.csv` fetched on load via `autoLoadGA4()` — no manual upload needed
- **Analytics page:** Two-pane layout — Content Analytics (left) · Site Traffic (right)
- **Performance page:** Flat row grid — each row aligns left/right independently
  - Row 1: titles
  - Row 2: persona cards | Site Conversion + Tracking Pixels
  - Row 3: Top 5 Posts | Best Click-Through Posts
  - Row 4: Best Performing Categories | What Drives Reactions & Reposts
- **Overview page:** 8 KPI cards in `card-grid-8` (4-2-1 responsive)
  - Row 1: Total Posts · Avg Impressions · LI Profile Traffic · Company Page Reach
  - Row 2: Avg CTR · Articles Remaining · Top Writer · Top Category
- **Security:** `aima-analytics-92f4d1344f7a.json` removed from git history — keep in `.gitignore`
- **Manual Entry section:** Removed from Analytics right pane

---

## Echo Agent — Scope (LinkedIn only)

Echo stays narrowly scoped to **LinkedIn post metrics only**. She does not aggregate other platforms.

- Collects impressions, clicks, CTR, reactions, reposts, comments via `/rest/socialMediaPostStatistics`
- Reads `linkedin_pipeline/post_log.json` — posts where `analytics_collected: false` + posted_at > 48h
- Writes to `linkedin_analytics.csv`
- Credentials: `linkedin_pipeline/.env`

---

## Maya Agent — Planned (as of June 21, 2026)

**Maya** (`MY`) is the dedicated Visual Director. She slots between Quill and Vera. Marco hands off Quill's copy-only HTML + Priya's spec; Maya owns all visual work before QC.

### Role
- Generate **2 header images** via Higgsfield AI (nano_banana_pro, 16:9) — vary the visual angle between both
- Resize both to 1200×630 JPG via PIL
- **Select the stronger image** for the article based on visual clarity, relevance, and composition
- Save primary image → `img/articles/aima-[NNN]-[slug].jpg` (path set by Priya in spec; Maya saves to this exact path)
- Save alternate image → `img/alt-img/aima-[NNN]-[slug]-alt.jpg` (stored for future reuse, no further action)
- Merge copy HTML + primary image into article skeleton
- Set `og:image` in article meta to the primary image path from the spec
- `git add` both images + merged article HTML — NO push
- Return merged article path to Marco

### What she does NOT do
- Edit article copy (Quill's job only)
- Push to git (Porter's job)
- Call any APIs beyond image generation

### Directories
- `img/articles/` — primary cover images (1200×630 JPG)
- `img/alt-img/` — alternate generated images for future reuse

---

## Cora Agent — Planned (as of June 21, 2026)

**Cora** (`CO`) is the Token Resource Manager. She runs in parallel with Marco throughout every pipeline run — not a sequential stage but a cross-cutting governance layer.

### Role
- Monitor token consumption per agent per run via `token_budget.json`
- Alert Marco at 80% budget threshold per agent
- Reallocate unused budget from later-stage agents if needed
- Recommend `SAVE_AS_DRAFT` if session limit is at risk

### Error + Misbehavior Protocol
- **Round 1:** Identify root cause → implement prompt-level guardrail → re-run agent → log outcome
- **Round 2 (same issue, same agent):** Flag to Marco + append to `CLAUDE.md` → recommend re-scope, re-allocate, or dismissal

### Files
- `token_budget.json` — per-agent budget + live usage
- `token_log.csv` — per-run history + error events + guardrail actions

### Optimization Folder
- `optimization/optimization_report.json` — cross-pipeline ops report · Iris reads at run start · Iris · Marco · Cora · Lumen write here after Optimization batch run

---

## Lumen Agent — Planned (as of June 21, 2026)

**Lumen** (`LM`) is a new dedicated cross-platform analytics aggregator. Echo handles LinkedIn; Lumen handles everything else.

### Role
Collect pixel and API analytics from all non-LinkedIn platforms and produce a unified per-article performance summary.

### Target platforms
- **Google / GA4** — GA4 Data API or `ga4_traffic.csv` auto-export
- **Meta** — Meta Graph API (Facebook + Instagram Insights)
- **TikTok** — TikTok Business API
- **Buy Me a Coffee** — BMC API / webhooks for supporter events and revenue data

### Output
- Per-platform CSVs: `ga4_analytics.csv`, `meta_analytics.csv`, `tiktok_analytics.csv`, `bmc_analytics.csv`
- Unified `platform_summary.json` per article — cross-platform reach, engagement, revenue
- All outputs feed into `article-manager.html` dashboard

### Credentials (owned by Lumen, not Marco)
- `lumen_secrets.json` — GA4 service account, Meta token, TikTok token, BMC API key

### Badge
- Code: `LM` · Color: purple · Type: Autonomous

---

## Scout Agent — Planned Enhancements (as of June 21, 2026)

Scout's research routine should be extended to ingest structured external data sources before falling back to live web search:

- **`scout-sources.json`** — config file listing trusted RSS feeds and API endpoints Scout checks first each run
- **RSS feeds** — news aggregators, journal feeds, think-tank blogs, government data releases
- **APIs** — World Bank, IMF, UN, OECD, Google Trends, Statista, Reddit, X/Twitter, and any domain-specific sources
- **Pre-cached data files** — CSVs or JSONs dropped into `articles/research/` that Scout picks up automatically
- **Webhooks** — push fresh data to a local file that Scout reads before each run

### Implementation steps
1. ✅ `articles/research/` directory created (June 22, 2026)
2. ✅ `scout-sources.json` created in repo root (June 22, 2026) — 31 RSS feeds + 9 APIs + topic tag index
3. Update Scout's prompt to: check `scout-sources.json` first → ingest available feeds/APIs → supplement with web search → write brief JSON

This makes Scout fully pre-loadable — she can run on her own schedule to cache briefs for the next 3–5 articles before Quill needs them.

---

## AIMA Article Pipeline — Current State

- **Last article written:** #016 — "The Digital Nomad Economy: How Developing Nations Are Reshaping Global AI Labor" (June 21, 2026)
- **Next article:** #017 — Track: trending — Author: Dawn Ginhaua
- **Scheduled:** Daily via Cowork task `aima-article-coworker`
- **State file:** `articles/aima-coworker-state.json`
- **Note:** Article #014 (Hallucination Nation) was skipped in sequence — write it before publishing article #016 if strict numbering matters.
