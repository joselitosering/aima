# AIMA Project Memory

## Agents — start here (v2.6, Batch & Toggle Integration)

**Read [AIMA-HANDOFF-v2.6.md](AIMA-HANDOFF-v2.6.md) first**, then this File Map. Routing:
- **Run the pipeline:** `python run.py` → `agents/marco.py` (honors `pipeline_config.json` toggles).
- **Run one stage on its own:** the `run_<batch>.py` at repo root (see File Map). Dashboard buttons hit
  these via `insights/ /api/run`.
- **Stage on/off + QC mode:** `pipeline_config.json` (dashboard-owned) → `agents/config.py:load_pipeline_config()`.
- **Per-agent code:** `agents/<name>.py`. Shared infra: `agents/base.py`, `agents/config.py`, `agents/prompts.py`.
- **Fiduciary rule:** Vera halts+reports (never iterates); writers halt without research; skip-and-reuse
  cached artifacts; gate token/credit/live batches; report calendar bugs, don't auto-mutate the calendar (only Iris does —
  plus the one sanctioned exception: Trend Scout fills a still-TBD trending row's title+category, with a logged rationale).
- **Calendar is ONE canonical sequence (2026-07-02, per Joe — see DECISION-LOG.md):** single table, rows numbered 1–64;
  Author is a per-row attribute (last column) that Joe can reassign freely — never a track, never slot labels (D#/K# retired).
- **Retired:** `linkedin_pipeline/pipeline.py` — do not call/recreate. Publish=Porter, Marketing=Nova.

## File Map (updated June 28, 2026 — v2.6)

The article pipeline runs on **`agents/`** (Marco orchestrator). `linkedin_pipeline/`
is now collectors + LinkedIn API only — **`pipeline.py` is retired**.

```
run.py                      full pipeline entry → Marco · python run.py [--dry-run]
run_priya_batch.py          Priya audit · calendar bug report (+ --fix: safe posted_articles hygiene) → optimization/priya_audit.json
run_research_batch.py       Research batch · Scout pre-researches next 2 titles → articles/research/
run_writer_batch.py         Writer batch · persona writes next assignment → articles/drafts/ (halts if no research)
run_marketing_batch.py      Marketing batch · Nova posts published-but-unmarketed → LinkedIn (reports if none)
run_analytics_batch.py      Analytics run · Echo fetches LinkedIn analytics → post_analytics.csv (for Priya; no tokens)
run_lumen_batch.py          Lumen run · merge LinkedIn analytics + GA4 → optimization report (CC tokens)
run_token_audit.py          Token Audit (Cora) · token ledger report → optimization/token_audit.json (read-only)
run_review_batch.py         Review Day (Vera) · QC staged articles → articles/review_day.json (CC tokens)
run_optimization_batch.py   Optimization (Iris) · advisory from Marco/Lumen/Cora/Priya · edits calendar + CLAUDE.md (CC tokens)
run_maya_batch.py           Maya batch · pre-designs next 2 calendar titles → handoff/ready/
run_publish_batch.py        Publish batch · Porter publishes staged articles (push + GS, no LinkedIn)
run_echo.py / run_iris.py   standalone Echo (LinkedIn analytics) / Iris runners
pipeline_config.json        stage toggles · dashboard writes · Marco reads (load_pipeline_config)
agents/
  marco.py     orchestrator · gates each stage on pipeline_config; skipped stage reuses cached artifact
  priya.py     plan · next article spec from calendar       scout.py   research → articles/research/[slug]-research.json (+load_cached)
  trend_scout.py  trending-topic determination · turns "TBD — Trending Topic" calendar rows into real titles for the
               row's ASSIGNED AUTHOR (any writer — reads Author column + articles/personas/<name>.md, not a fixed roster)
               (runs BEFORE Scout · writes title+category back to the calendar row · logs rationale+sources to
               articles/research/[slug]-topic-selection.json + optimization_report.json · idempotent: resolved rows skip it)
  writer.py    free-form persona authors (Joselito/Dawn/Kenji) → articles/drafts/  [Quill is now the EDITOR of these]
  quill.py     EDITOR · refines writer drafts to Vera's checklist  maya.py    design · handoff/ready pickup by #NNN, else generate
  vera.py      QC ASSURANCE · checks targets, HALTS+reports to Marco (never re-runs Quill/Maya)
  porter.py    publish · push → poll aima.productions → GS canonical (gs_enabled)
  nova.py      marketing · LinkedIn company post + personal reshare
  echo.py      LinkedIn analytics 48h+ (independent)        lumen.py   aggregate GA4/Meta/TikTok/BMC
  cora.py      token audit · budgets + guardrails           iris.py    editorial decisions
  config.py    load_pipeline_config() + model/budget maps   base.py    CC calls · file IO · git · agents/.env
  prompts.py   per-agent system prompts (Vera checklist = ranges, not fixed 1800)
articles/      aima-coworker-state.json · aima-editorial-calendar.md · research/ · personas/
handoff/ready/ Maya batch staging — pipeline Maya moves matching #NNN images into img/articles/
img/articles/  primary covers (Maya)        img/alt-img/  alternates
optimization/  optimization_report.json (Iris/Marco/Cora/Lumen)
linkedin_pipeline/  linkedin_poster.py (Nova) · github_fetcher.py · gs_logger.py (Porter) ·
                    analytics_collector.py (Echo) · ga4_collector.py · xls_import.py ·
                    posted_articles.json (calendar de-dupe) · post_log.json · .env
token_budget.json   Cora per-agent budget + live usage
```

**Stage toggles** (`pipeline_config.json`): `RESEARCH/WRITE/MAYA/PUBLISH/GS/MARKETING/ANALYTICS/LUMEN/CORA_ENABLED`
(bools) + `QC_GATE` (`human` = hold after Vera for review · `auto` = proceed). Dashboard panel: Articles → Data → Full Pipeline Toggles.

## Pending Actions

### LinkedIn Marketing API — Development Tier Approval
- **Status:** APPROVED June 20, 2026 (Advertising API, app id 253440006)
- **SCOPES updated:** `r_member_social` added to `linkedin_pipeline/linkedin_auth.py`
- **NEXT STEP:** Run `python linkedin_pipeline/linkedin_auth.py` to get a new token with `r_member_social`
- Then test: `python linkedin_pipeline/analytics_collector.py`
- **analytics_collector.py is ready** — already uses `/rest/socialMediaPostStatistics`, no code changes needed after token refresh

---

## LinkedIn Pipeline — Current State (as of June 21, 2026)

### POST-PUBLISH WORKFLOW (now run by Marco / agents)
> **`linkedin_pipeline/pipeline.py` was RETIRED June 27, 2026.** The full pipeline is
> `python run.py` → `agents/marco.py`, which honors the stage toggles in
> `pipeline_config.json`. Publish = **Porter** (`agents/porter.py`), Marketing = **Nova**
> (`agents/nova.py`). The steps below describe Porter + Nova:
1. **Porter** — `git push` → wait 60s → poll `aima.productions/articles/<file>` every 10s
   for `og:title` → log the **canonical** URL (`joselitosering.github.io/aima/...`) to Google Sheets.
2. **Nova** — posts to the **AIMA company page** (cover image + hook + hashtags + **persona byline**),
   then **reshares to Joselito's personal profile** with persona-tailored intro + **TL;DR** + CTA,
   and logs post IDs to `post_log.json` for 48h analytics collection.

The company-page + reshare logic still lives in `linkedin_pipeline/linkedin_poster.py`
(called by Nova). Tested/approved June 21, 2026.

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

### Runtime behavior (cost/efficiency, added July 3, 2026)
- **Dedup before the CC call.** `lumen.run()` checks `optimization_report.json`
  for a same-day `source:"lumen"` entry *before* invoking `call_cc_agent`. If
  one exists it logs `entry already exists for <date> — skipping CC call` and
  returns the existing entry — no subscription-billed call. (Re-running Lumen
  twice in a day used to pay for the full call twice.)
- **`--force` for intra-day refresh.** The dedup is per calendar day, so a
  same-day re-run won't pick up sources that updated later that day. Pass
  `python run_lumen_batch.py --force` (→ `lumen.run(report, force=True)`) to
  bypass the dedup: it runs the paid CC call even if today's entry exists and
  **replaces** that entry with the fresh result (no stale duplicate left behind).
- **No-secrets prompt + model.** When `lumen_secrets.json` is absent (today's
  state), Lumen runs the reduced `LUMEN_PROMPT_NO_SECRETS` (GA4 + LinkedIn
  only) on `claude-haiku-4-5` and writes a `meta/tiktok/bmc: skipped, no
  lumen_secrets.json` flag as the fiduciary trace for the uncredentialed
  platforms. It still writes `ga4_analytics.csv` + a GA4-only
  `platform_summary.json` so the dashboard's unified view keeps refreshing.
  When secrets exist, the full multi-platform `LUMEN_PROMPT` runs on the CC
  default (Sonnet). Prompt selection lives in
  `prompts.build_lumen_prompt(has_secrets)`; model is chosen in `lumen.run()`.

### Badge
- Code: `LM` · Color: purple · Type: Autonomous

---

## Trend Scout — Trending-Topic Determination (added July 2, 2026)

Trending calendar rows start life as the literal "TBD — Trending Topic"
placeholder. **`agents/trend_scout.py`** turns a TBD row into a real topic;
before this, trending topics were always a manual human decision (#014, #017
were one-offs outside the calendar system).

- **Author-agnostic (per Joe, 2026-07-02):** the topic is chosen for the row's
  ASSIGNED AUTHOR — read from the calendar's Author column, beat loaded from
  `articles/personas/<slugified-name>.md` (generic AIMA beat if no profile).
  NOT hardcoded to Dawn/Kenji; reassign a row's author and Trend Scout follows.
- **Trigger:** any resolved spec whose title is still the TBD placeholder —
  happens automatically in the default batch walk AND in the full pipeline
  (`priya.run()` calls `trend_scout.resolve_tbd_row()` before her CC run;
  skipped under `--dry-run`), or target a row explicitly:
  `run_research_batch.py --article 26` / `run_writer_batch.py --article 26`.
- **How:** CC_AGENT call (`trend_scout`, budget 12,000 — topic selection, not research).
  Surveys beat-filtered feeds/APIs from `scout-sources.json` (news APIs +
  google_trends + tagged RSS; WebSearch fallback), returns 3 ranked candidates.
- **Dedup:** candidates are checked against all calendar titles, `articles_written[]`
  in `aima-coworker-state.json`, and `articles/research/` slugs; collisions fall
  through to the next candidate.
- **Durability/idempotency:** the chosen title+category is written back into the
  calendar row in place (matched by canonical row number). A re-run sees a real
  title and skips straight to Scout — no re-roll.
- **Fiduciary trace:** rationale + surfacing sources go to
  `articles/research/[slug]-topic-selection.json` and `optimization_report.json`.
- **Guardrails intact:** only the TITLE is replaced — writers still HALT without
  a Scout brief; Scout still runs and produces real research afterward. The Maya
  batch skips TBD rows (no cover art for placeholders).

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
