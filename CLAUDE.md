# AIMA Project Memory

### Echo analytics: CSV split + dead XLS fallback — FIXED (2026-07-28)
Two code bugs fixed; the underlying **LinkedIn scope gap remains open and is not fixable in
code** (see Pending Actions). Full write-up: [HANDOFF-2026-07-28-echo-analytics.md](HANDOFF-2026-07-28-echo-analytics.md).

1. **CSV split.** `agents/echo.py` wrote `REPO_ROOT/linkedin_analytics.csv` — a file that has
   never existed, because Echo has never had a successful API call. Every *reader* uses
   `linkedin_pipeline/post_analytics.csv` instead: `run_lumen_batch._linkedin_report()`,
   `marco._category_priority()`, and `article-manager.html`; the two other *writers*
   (`xls_import.py`, legacy `analytics_collector.py`) also write there. So even a working Echo
   would have written into a file nothing reads. **`linkedin_pipeline/post_analytics.csv` is
   now the single canonical file.** Note the non-obvious part: the two schemas differed (Echo
   emitted `date,slug,urn,…,reactions,reposts`; the canonical file is
   `post_id,article,title,persona,posted_at,collected_at,…,likes,shares,engagement_rate`), so a
   bare path swap would have appended ragged rows into a file with 11 live data rows and
   corrupted the dashboard's backfill. Echo now maps onto the canonical 13-column schema
   (`REACTION`→`likes`, `RESHARE`→`shares`, `engagement_rate` derived as
   `(likes+comments+shares)/impressions`) via a new `_build_csv_row()`. `run_lumen_batch.py`
   needed **no change** — it already read the canonical file.
2. **Dead `xls_import.py` auto-call.** On API failure Echo ran
   `subprocess.run(["python","linkedin_pipeline/xls_import.py"], check=False)`. `xls_import`
   requires a positional `xls_file`, so this exited 2 and did nothing — verified by running it
   (`error: the following arguments are required: xls_file`). With `check=False` the failure was
   swallowed, so Echo *appeared* to have a fallback while spawning one wasted subprocess per
   uncollected post per run. Removed. The LinkedIn analytics export is a human action with no
   pull API, so nothing can be auto-invoked; Echo now logs the real command once per run.
3. **Scope-gate short-circuit (new).** A 401/403 is a token-wide condition, not a per-post one.
   Echo now stops the loop on the first one instead of firing 5 API calls × 26 eligible posts
   (130 doomed requests) every run.

**Verified against the live API 2026-07-28:** real HTTP 403, halt after exactly 1 attempt,
correct operator message, no `post_log.json` write and no git push when nothing is collected.
Backlog is unchanged at **28 of 35** uncollected (26 currently past the 48h window) — code
cannot reduce this while the scope is missing.

### find_draft stale-stub bypass — FIXED (2026-07-17)
Root cause: `writer.find_draft()` only checked `stat().st_size > 200` bytes. A partial/failed Writer CC run that wrote a 104-word skeleton to disk left a stub that easily passed that check. On the next pipeline run Marco called `find_draft()`, got the stub back, skipped `writer.run()` entirely, and passed the bad draft straight to Quill — causing repeated Quill halts for the same draft that Writer had already rejected. Fix: `find_draft()` now runs the same prose word-count gate (`range_min * 0.85` floor) Writer's `run()` uses. Stubs below the floor are logged and skipped; Marco calls `writer.run()` fresh instead. Also added `_prose_word_count()` helper (shared logic, glossary+refs stripped before counting).

### Scout token overspend — FIXED (2026-07-17)
Root cause (3 compounding issues): (1) `_list_cached_research()` returned ALL 18+ files in `articles/research/` with no topic filter — Scout would read whichever it judged relevant, including 65KB files costing ~16k tokens each, before any real research started. (2) No budget guardrail in Scout's prompt — it had no awareness of its 500k ceiling before firing tools. (3) `MAX_TURNS_MAP["scout"]` was 15, allowing unbounded context accumulation across turns.

Fix: (a) `_list_cached_research()` now accepts `topic_tags` and `max_files=5`, filtering by tag keyword match on filename and sorting by size ascending (cheapest first). Topic-selection files excluded. Falls back to all candidates if filter is too aggressive. (b) `run()` reads `token_budget.json` before building `user_input` and injects a hard budget guardrail block at the top — ceiling, remaining tokens, and strict per-category limits (≤3 reads, ≤4 feeds, ≤3 web searches, stop at 4 stats + 2 quotes). (c) `MAX_TURNS_MAP["scout"]` reduced 15→8 (3 reads + 4 fetches + 1 write). Expected cost reduction: $0.90→$0.30–0.40 per article. Validate on article #28.

### Cora token tracking — FIXED (2026-07-04)
Root cause: `call_cc_agent()` ran the `claude` CLI in plain `--print` text mode, which returns no usage data at all — `token_budget.json`'s `used` field was never incremented anywhere in the codebase (only ever zero-initialized by `cora.init_budget()`). Cora's prompt was asking the model to guess a `total_tokens_used` number with no real data in front of it.

Fix: `agents/base.py::call_cc_agent()` now runs with `--output-format json` and extracts `result` (text), `usage.{input,output,cache_creation_input,cache_read_input}_tokens`, and `total_cost_usd` from the CLI's own JSON envelope (verified live against a real trivial CC call — schema matches https://code.claude.com/docs/en/headless exactly). New `_record_token_usage()` writes real per-call totals + cost into `token_budget.json`. `cora.init_budget()` is now idempotent per run_date+article_number (a resumed run no longer wipes usage already recorded); `marco.py` now inits the budget *before* Priya's own CC call too, so her usage has somewhere real to land. Also closed two silent gaps: Trend Scout ("TS") and the Writer stage ("WR", all three personas share one bucket) had no budget entry at all before this fix — they were invisible to Cora even after tracking is fixed for everyone else. Not yet validated inside a real full pipeline run — first real run after this change is the actual test; check `token_budget.json` after for non-zero `used` values before trusting Cora's next governance report's numbers.

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

### LinkedIn analytics scope — BLOCKED on LinkedIn, not on code (verified 2026-07-28)

**Corrects the previous note here**, which claimed `r_member_social` was "APPROVED June 20,
2026" and "added to SCOPES". Both halves were false and are retracted — verified two ways on
2026-07-28: (a) the live `SCOPES` string in `linkedin_pipeline/linkedin_auth.py` has never
contained `r_member_social` (it isn't in the file, and `git log -p` shows it never was), and
(b) LinkedIn's own token introspection endpoint reports the granted scopes on the current
active token as exactly `openid profile email w_member_social w_organization_social
r_organization_social rw_organization_admin r_organization_admin` — no `r_member_social`.
LinkedIn's docs now list `r_member_social` as a **closed** permission ("not accepting access
requests at this time"). The old note also pointed at `/rest/socialMediaPostStatistics`, an
endpoint that does not exist on LinkedIn's API (every call 404'd — see `agents/echo.py`).

**Actual current state:**
- **Posting works.** Token is `active` (expires 2026-09-21), and both posting scopes
  (`w_member_social`, `w_organization_social`) are granted. Nova is unaffected.
- **Analytics collection cannot work.** `agents/echo.py` calls
  `/rest/memberCreatorPostAnalytics`, which requires **`r_member_postAnalytics`**. That scope
  is not granted to this app. Confirmed live 2026-07-28: the endpoint returns **HTTP 403**.
- `r_member_postAnalytics` was removed from `SCOPES` in `be88f65` (2026-07-23) for a real
  reason: **requesting an unapproved scope makes LinkedIn reject the entire OAuth
  authorization request**, which broke posting too. **Do not re-add it** until approval is
  actually confirmed — re-adding it will immediately re-break posting the same way.
- It is **not a self-serve Developer Portal checkbox.** `r_member_postAnalytics` / the Post
  Statistics endpoint sit under the **Community Management API**, which requires a formal
  **Technical Sign-Off**: contacting a LinkedIn Business Development point of contact and
  completing a live product demo against ~28 requirements.

- **NEXT STEP (Joe, external — cannot be closed by code):** pursue the LinkedIn Community
  Management API Technical Sign-Off for `r_member_postAnalytics`. Only after approval is
  confirmed: re-add the scope to `SCOPES`, re-run `python linkedin_pipeline/linkedin_auth.py`,
  then `python run_analytics_batch.py`.
- **Meanwhile the working path is manual:** export the LinkedIn Analytics XLS and run
  `python linkedin_pipeline/xls_import.py <path-to-export.xlsx>`. Echo prints this exact
  instruction on every run while posts remain uncollected.

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

- Collects impressions, clicks, CTR, reactions, reposts, comments via
  `/rest/memberCreatorPostAnalytics` (one API call per metric — there is no combined-stats
  mode). **Currently returns HTTP 403** — see the analytics-scope entry under Pending Actions.
- Reads `linkedin_pipeline/post_log.json` — posts where `analytics_collected: false` + posted_at > 48h
- Writes to **`linkedin_pipeline/post_analytics.csv`** — the ONE canonical LinkedIn analytics
  file (2026-07-28). Echo previously wrote `linkedin_analytics.csv` at the repo root in its own
  narrower schema; nothing read that file. Echo now emits the same 13-column schema as
  `xls_import.py` / `analytics_collector.py`, so API rows and XLS-imported rows are
  interchangeable. Readers: `run_lumen_batch._linkedin_report()`,
  `marco._category_priority()` (keys off the `article` column), `article-manager.html`.
  **Any change to that column list must change all four readers.**
- On failure Echo does **not** shell out to `xls_import.py` (that call was a no-op — see the
  2026-07-28 entry below). It logs the manual import command once per run instead.
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


### Pipeline CRASH — #19 'The Persuasion Engine: AI, Social Media, and the Death of Shared Reality' — stage 'quill' (2026-07-04)
<!-- aima-failure-key: 2026-07-04|quill|CC agent [quill] failed (exit 1): -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** CC agent [quill] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): You've hit your session limit · resets 3:50pm (America/Los_Angeles)

- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 176, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 143, in run
    raw_html = call_cc_agent("quill", QUILL_PROMPT, user_input)
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 162, in call_cc_agent
    raise RuntimeError(
    ...<3 lines>...
    )
RuntimeError: CC agent [quill] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): You've hit your session limit · resets 3:50pm (America/Los_Angeles)


```

**RESOLVED 2026-07-04 17:33.** Re-ran `python run.py` after the 3:50pm PT session-limit reset. Marco correctly resumed from cache — Priya rebuilt the spec (only new CC call needed), Scout/Writer both hit cached artifacts (no CC calls), Quill succeeded clean on retry (0 revisions). Pipeline ran all the way through Porter (published, GS row 20) and Nova (LinkedIn company post + personal reshare) — QC_GATE was `auto` for this run per Joe's explicit instruction. Full resume wall-clock: ~25.8 min (17:07:23–17:33:11).

**New finding from Cora's governance report (article #19, CRITICAL):** `token_budget.json` usage tracking is broken — `used=0` for every agent across two consecutive runs (#018 and #019). Cora flagged this HIGH after #018 and it wasn't actioned; now flagged CRITICAL with a recommendation to hold the pipeline at #020 until per-agent token usage is actually wired into each agent's completion callback. Until fixed, no real token/cost numbers exist for any pipeline run — budgets in `token_budget.json` are ceilings only, not measurements. Also flagged: 2 MEDIUM hallucination-risk stats in #19 (WEF 70%/64% survey figures — source blocked HTTP 403, Quill disclosed the limitation inline; Europol 90% synthetic-content projection — original report URL unconfirmed, framed as a projection not a measurement). Both mitigated in the published copy but flagged for follow-up verification before re-citation elsewhere.
- Full run log: pipeline.log

### Marco cost redesign — Direction B: Writer merged into Quill (2026-07-04)
**What & why.** Marco's real cost driver is the number of *distinct cold `claude`
subprocess launches* per article (each pays its own system-prompt cache-creation
event), not lack of `--resume` context-carrying (a live 3-call test confirmed
`--resume` chaining does NOT help — see the task file). Direction B collapses the
two most-mergeable cold starts: the **Writer** stage no longer spends its own
subprocess inside the full pipeline. When no pre-staged draft exists, **Quill now
AUTHORS then EDITS in one call** (two phases: write freely in the row author's
persona voice using the Writer stage's own form/length/voice spec, then edit that
draft to Vera's checklist). One cold-start removed per from-scratch article.

**Files.** `agents/quill.py` (two-phase authoring in the no-draft branch, imports
`writer.AUTHOR_SPECS`/`resolve_author`), `agents/marco.py` Stage 3 (drops the
separate `writer.run()` cold call; keeps `writer.find_draft()` reuse), `agents/
config.py` (QL budget 22k→42k so Cora's 80% threshold doesn't trip now that one QL
call carries authoring+editing; WR documented as standalone-batch-only in the
merged pipeline). `writer.run()` and `run_writer_batch.py` are UNCHANGED — the
standalone Writer batch still pre-stages drafts, which the merged Quill EDIT path
reuses exactly as before.

**Real measured cost (not an estimate).** `measure_writer_quill_merge.py` ran 3
real CC calls on cached #19 research (Dawn persona, target 1400w), reading each
call's real `total_cost_usd` from `token_budget.json` deltas:
- OLD: Writer $0.9016 (253,880 tok) + Quill-edit $0.6283 (75,230 tok) = **$1.5299**
- NEW: merged author+edit **$0.8719** (139,067 tok) — cheaper than the old Writer
  call *alone*.
- **Savings: $0.658/article = 43%** on the Writer+Quill stages, ~58% fewer tokens.
(Probe corroboration: even a trivial one-word CC call cost $0.0584 with 8,962
cache-creation tokens — the fixed per-cold-start overhead the merge eliminates.)

**Guardrails — all verified preserved:** Vera still halts+reports (Stage 6
untouched); Writer no-research HALT in the batch untouched + merged prompt keeps
"don't invent beyond the research, flag gaps"; skip-and-reuse intact for research /
pre-staged draft / final article (crash-recovery via final-article skip preserved);
all `pipeline_config.json` toggles honored (only Stage 3 internals changed under
`WRITE_ENABLED`); Trend Scout remains the SOLE calendar mutator (I deliberately did
NOT merge Trend Scout→Priya — that would spread calendar-write permission); one
canonical calendar sequence (merged path uses the row's Author attribute via
`resolve_author`, no track logic); Cora attribution stays real (one call = one
honest bucket, no fabricated split).

**Open item — output quality not yet end-to-end verified.** The A/B harness deletes
its throwaway outputs, and the merged call's stdout-fallback capture was much
shorter (6,421 chars) than the old path's (44,878) — likely a harness artifact
(direct Write-tool file vs stdout capture) rather than a real truncation, but
UNCONFIRMED. Confirm equivalent article quality on the next real `python run.py`:
the merged Quill output still routes through Maya + **Vera's QC gate**, which HALTS
a too-short/under-structured article (word-count + 5-6 H2 + stat-grid checks) — so a
quality regression cannot silently publish, it surfaces as a Vera halt. Deliberately
NOT changed beyond the merge: Maya (its only CC call *is* the skeleton merge —
nothing to collapse), Priya/Scout/Vera/Cora voices and quality bars.

### Marco cost redesign — round 2 tuning: context-by-path + lower persona lengths (2026-07-04)
Follow-up to the Direction B merge above, both aimed at getting the merged authoring
call below ~125k tokens. Joe asked; will be confirmed on the next real run.
- **Context-by-path.** `agents/writer.py` and `agents/quill.py` no longer INLINE the
  full research JSON (~6.8k tok), format guide `aima-coworker-prompt.md` (~4.7k tok),
  persona (~1.2k tok), or writer draft into `user_input`. They now pass those as FILE
  PATHS for the agent to Read with its own tool. Measured effect on the initial prompt:
  writer `user_input` ~50,000 → **1,301 chars**; quill ~50,000 → **1,911 chars**. That
  slashes the one-time cache-creation and, more importantly, stops the big context from
  sitting in the prompt prefix that gets re-charged as `cache_read` on every tool turn
  (the dominant token term). Same "pass the path, not the content" pattern Maya uses.
  Safety: if no research file is on disk, the passed dict is still inlined so the
  no-fabrication guardrail keeps something to check against.
- **Lower persona lengths (Joe).** `AUTHOR_SPECS` in `agents/writer.py`: Joselito
  1800+→1200-1500 (target 1350), Dawn 1200-1500→1000-1200 (1100), Kenji 900-1200→
  800-1000 (900). `agents/marco.py` Stage 3 now caps the article word target to the
  row author's persona `target_words` via `min(priya_target, persona_target)` — the
  persona is the ceiling (Priya may still go shorter), so the finished article can't
  balloon back past persona length and undo the saving. Vera's word-count check is
  `target_words ±10%`, so it auto-adapts — no guardrail change.
- **Caveat:** word count is the *smaller* lever (output is only ~15-22k of the 139k);
  context-by-path is the bigger one. Re-measure with `measure_writer_quill_merge.py` or
  read `token_budget.json` after the next real `python run.py` for the true landing number.


### Pipeline CRASH — (spec not yet built) — stage 'priya' (2026-07-13)
<!-- aima-failure-key: 2026-07-13|priya|CC agent [trend_scout] failed (exit 1): -->
- **Occurrences:** 2
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** CC agent [trend_scout] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): {"type":"result","subtype":"success","is_error":true,"api_error_status":null,"duration_ms":315,"duration_api_ms":0,"num_turns":1,"result":"Not logged in · Please run /login","stop_reason":"stop_sequence","session_id":"3536e76d-21cd-4b08-82c5-99fab516c2c3","total_cost_usd":0,"usage":{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral
- **Traceback:**
```
Traceback (most recent call last):
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/marco.py", line 146, in run
    spec = priya.run()
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/priya.py", line 93, in run
    elif trend_scout.resolve_tbd_row(number):
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/trend_scout.py", line 284, in resolve_tbd_row
    chosen = determine_trending_topic(
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/trend_scout.py", line 172, in determine_trending_topic
    raw = call_cc_agent("trend_scout", TREND_SCOUT_PROMPT, user_input).strip()
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/base.py", line 222, in call_cc_agent
    raise RuntimeError(
RuntimeError: CC agent [trend_scout] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): {"type":"result","subtype":"success","is_error":true,"api_error_status":null,"duration_ms":315,"duration_api_ms":0,"num_

### Pipeline CRASH — (spec not yet built) — stage 'priya' (2026-07-13)
<!-- aima-failure-key: 2026-07-13|priya|Expecting ',' delimiter: line 52 column 43 (char 1149) -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** Expecting ',' delimiter: line 52 column 43 (char 1149)
- **Traceback:**
```
Traceback (most recent call last):
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/marco.py", line 143, in run
    log.info("[marco] Stage 1: Priya — building article spec")
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/cora.py", line 54, in init_budget
    existing = read_json("token_budget.json")
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/base.py", line 259, in read_json
    text_output = raw_stdout
  File "/usr/lib/python3.10/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
  File "/usr/lib/python3.10/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
  File "/usr/lib/python3.10/json/decoder.py", line 353, in raw_decode
    obj, end = self.scan_once(s, idx)
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 52 column 43 (char 1149)

```
- Full run log: pipeline.log


### Pipeline CRASH — #25 'The Government Filed a Brief for the Algorithm: How the DOJ Killed America's First AI Antidiscrimination Law' — stage 'scout' (2026-07-14)
<!-- aima-failure-key: 2026-07-14|scout|API agent [scout] HTTP 402: {"error":{"message":"This request requires more credits, or fe -->
- **Occurrences:** 2
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** API agent [scout] HTTP 402: {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 8000 tokens, but can only afford 3990. To increase, visit https://openrouter.ai/settings/credits and upgrade to a paid account","code":402,"metadata":{"provider_name":null,"previous_errors":[{"code":402,"message":"This request requires more credits, or fewer max_tokens. You requested up to 8000 tokens, but can only afford 3990. To increase, visit https://openrouter.ai/settings/credits and upgrade to
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 347, in call_api
    with urllib.request.urlopen(req, timeout=300) as resp:
         ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 187, in urlopen
    return opener.open(url, data, timeout)
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 493, in open
    response = meth(req, response)
  File "C:\Python314\Lib\urllib\request.py", line 602, in http_response
    response = self.parent.error(
        'http', request, response, code, msg, hdrs)
  File "C:\Python314\Lib\urllib\request.py", line 531, in error
    return self._call_chain(*args)
           ~~~~~~~~~~~~~~~~^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 464, in _call_chain
    result = func(*args)
  File "C:\Python314\Lib\urllib\request.py", line 611, in http_error_default
    raise HTTPError(req.full_url, code, msg, hdrs, fp)
urllib.error.HTTPError: HTTP Error 402: Payment Required

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 292, in run
    research = scout.run(spec)
  File "D:\Apps\DevOps\Github\aima\agents\scout.py", line 206, in run
    raw = call_cc_agent("scout", SCOUT_PROMPT, user_input)
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 197, in call_cc_agent
    return call_api(name, system_prompt, user_input,
                    model=model_override or API_MODEL_MAP[name],
                    fallback=API_FALLBACK_MODEL)
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 351, in call_api
    raise RuntimeError(f"API agent [{name}] HTTP {exc.code}: {body}")
RuntimeError: API agent [scout] HTTP 402: {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 8000 tokens, but can only afford 3990. To increase, visit https://openrouter.ai/settings/credits and upgrade to a paid account","code":402,"metadata":{"provider_name":null,"previous_errors":[{"code":402,"message":"This request requires more credits, or fewer max_tokens. You requested up to 8000 tokens, but can only afford 3990. To increase, visit https://openrouter.ai/settings/credits and upgrade to

```
- Full run log: pipeline.log


### Pipeline CRASH — #25 'The Government Filed a Brief for the Algorithm: How the DOJ Killed America's First AI Antidiscrimination Law' — stage 'quill' (2026-07-14)
<!-- aima-failure-key: 2026-07-14|quill|[quill] Word count gate: 2912 words exceeds hard ceiling (1980 = 1100 × 1.8). Article NOT  -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [quill] Word count gate: 2912 words exceeds hard ceiling (1980 = 1100 × 1.8). Article NOT saved. Check QUILL_PROMPT word target instruction and --max-turns cap.
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 332, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 202, in run
    raise RuntimeError(
    ...<3 lines>...
    )
RuntimeError: [quill] Word count gate: 2912 words exceeds hard ceiling (1980 = 1100 × 1.8). Article NOT saved. Check QUILL_PROMPT word target instruction and --max-turns cap.

```
- Full run log: pipeline.log


### Pipeline CRASH — #25 'The Government Filed a Brief for the Algorithm: How the DOJ Killed America's First AI Antidiscrimination Law' — stage 'quill' (2026-07-14)
<!-- aima-failure-key: 2026-07-14|quill|[quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word co -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word count 1830 outside acceptable 765-1440 (persona range 900-1200). Draft at: articles/drafts/government-brief-algorithm-025-draft.html
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 332, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 93, in run
    raise RuntimeError(
    ...<2 lines>...
    )
RuntimeError: [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word count 1830 outside acceptable 765-1440 (persona range 900-1200). Draft at: articles/drafts/government-brief-algorithm-025-draft.html

```
- Full run log: pipeline.log


### Pipeline CRASH — #25 'The Government Filed a Brief for the Algorithm: How the DOJ Killed America's First AI Antidiscrimination Law' — stage 'quill' (2026-07-14)
<!-- aima-failure-key: 2026-07-14|quill|[quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 0 gloss -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 0 glossary terms (need >=6). Draft at: articles/drafts/government-brief-algorithm-025-draft.html
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 332, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 93, in run
    raise RuntimeError(
    ...<2 lines>...
    )
RuntimeError: [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 0 glossary terms (need >=6). Draft at: articles/drafts/government-brief-algorithm-025-draft.html

```
- Full run log: pipeline.log


### Pipeline Failure — Article #25 (2026-07-14)
- **Error:** Vera halted the article (verdict=needs_revision: copy). Reported to Marco for Iris/human review — no auto-revision (publish/marketing skipped).
- **Notes:**
  - **Structure**
  - - H2 count: 5 top-level sections ("The Law They Filed a Brief to Kill," "Corporate Litigation, Federal Co-Counsel," "The Constitutional Argument, Turned Inside Out," "The Harm That Needed No Law to Document," "What the Replacement Law Does") — within the 5–6 range. PASS.
  - - None of the 5 `<h2>` tags carry an `id` attribute (checklist requires `id="section-[slug]"` on each). The TOC sidebar still points to placeholder anchors `#section-[slug-1]` through `#section-[slug-5]` with literal unfilled labels `[Section 1 Title]`…`[Section 5 Title]` — these were never wired to the real sections. FAIL (broken in-page navigation, unfinished copy integration).
  - **Word count**
  - - JSON-LD declares `"wordCount": "1191"`. Manually counting the actual running prose (lead + 5 section bodies + closing paragraph, excluding stat-grid/pullquote) comes to roughly **840–900 words**, not ~1191. Author is Dawn Ginhaua, persona target 1100 (acceptable band ~990–1210 per Vera's ±10% gate). The real count appears to fall below the floor — this article has a documented history of repeated word-count gate failures (#25 crashed twice already for word count in the log above); this draft's declared count looks inflated relative to actual body text. FLAG for re-verification/revision.
  - **Stat grid / Pullquote**
  - - Stat grid present, 4 cards (26%, ~40,000, $2.3M, 90%). PASS.
  - - Pullquote present and on-topic. PASS.
  - - Note: the "90%" stat ("of U.S. employers use AI screening tools") has no matching in-text citation or reference number anywhere in the prose or reference list — it's asserted only in the stat card. Traceability gap / possible unsourced stat.
  - **Glossary**
  - - A glossary of 7 terms exists (Disparate Impact, Reasonable Care Standard, Equal Protection Clause, High-Risk AI System, Demographic-Conscious Engineering, AI Litigation Task Force, ADMT) — count clears the ≥6 minimum, but it's built as an ad-hoc `<dl>/<dt>/<dd>` block stuffed inside `.article-content`, not in the templated `#glossary` section with `.glossary-item`/`.glossary-term-title` markup.
  - - The actual `#glossary` section (the one the TOC and footer nav point to) still contains **unfilled skeleton placeholder text**: `[Term Name]`, `id="glossary-[word]"`, `[Plain-language definition, 3–5 sentences...]`. FAIL — the real glossary never replaced the placeholder in its intended location.
  - - No inline `<span class="glossary-term">` links appear anywhere in the body copy (checklist requires glossary-term links in the running text pointing readers to definitions). FAIL.
  - **References**
  - - 8 real, properly-sourced citations (DOJ, Colorado Sun, National Law Review, Norton Rose Fulbright, Stanford HAI, Leadership Conference on Civil and Human Rights, Crowell & Moring, White House EO 14365) meet the ≥6/8+ minimum and appear to trace consistently to the in-text parenthetical citations — content itself is not fabricated as far as can be judged.
  - - However, like the glossary, these are dumped into an ad-hoc `<div class="references"><ol>` inside `.article-content` instead of replacing the templated `#references` section. The actual `#references` section still contains **unfilled skeleton placeholder text** ("Lastname, Firstname," `"Web Article With Author."`, `[URL]`, etc.) for all 5 example slots plus a placeholder copyright notice `[List institutions... as of [Month YYYY]]`. FAIL — the canonical references section a reader or the TOC would land on is fake boilerplate, not the real bibliography.
  - **Summary of blocking issues**
  - 1. Word count likely below Dawn's acceptable floor despite a higher declared count — re-verify actual word count.
  - 2. Required `#glossary` and `#references` templated sections were left as unfilled placeholder copy; real content was misplaced into non-conforming ad-hoc divs earlier in the article.
  - 3. TOC sidebar section links and H2 ids were never resolved from placeholders — broken navigation copy.
  - 4. No inline glossary-term links in body copy.
  - 5. One stat-grid figure (90% employer AI-screening adoption) lacks a traceable in-text source.

### Pipeline Failure — Article #25 (2026-07-14)
- **Error:** Vera halted the article (verdict=needs_revision: copy). Reported to Marco for Iris/human review — no auto-revision (publish/marketing skipped).
- **Notes:**
  - **Structure (H2 count + TOC/id alignment)**
  - - 5 top-level H2 sections ("The Law They Filed a Brief to Kill," "Corporate Litigation, Federal Co-Counsel," "The Constitutional Argument, Turned Inside Out," "The Harm That Needed No Law to Document," "What the Replacement Law Does") — within the 5–6 range. PASS.
  - - All 5 H2 `id` attributes now match the TOC sidebar hrefs exactly (`#section-the-law-they-filed-a-brief-to-kill`, `#section-corporate-litigation-federal-co-counsel`, `#section-the-constitutional-argument-turned-insid`, `#section-the-harm-that-needed-no-law-to-document`, `#section-what-the-replacement-law-does`), plus `#references`/`#glossary`. PASS — this resolves the broken-TOC issue from the prior halt on this article.
  - **Word count — FAIL**
  - - JSON-LD declares `"wordCount": "856"`. Manually counting the actual running prose (lead + 5 section bodies, excluding stat-grid captions and pullquote, consistent with prior Vera methodology on this same article) comes to approximately **747 words**.
  - - Author is Dawn Ginhaua; per CLAUDE.md's round-2 tuning her persona target is 1100 words (band 1000–1200), and Vera's gate is target ±10% (~990–1210). Both the declared JSON-LD figure (856) and the actual measured count (~747) fall **below the floor**, with the real count roughly 25% short. This is the same word-count-inflation pattern flagged as unresolved in this article's prior halt — still not fixed in this draft.
  - **Stat grid**
  - - 4 cards present (26%, ~40,000, $2.3M, 90%). Structurally correct. PASS on format.
  - - The "90%" card ("of U.S. employers use AI screening tools") still has no matching in-text citation or reference number — same unsourced-stat gap flagged previously. FLAG.
  - **Pullquote**
  - - Present, on-topic, thematically tied to the article's Fourteenth Amendment argument. PASS.
  - **Glossary**
  - - 7 terms in the proper templated `#glossary` section using correct `glossary-item`/`glossary-term-title` markup (fixes the earlier placeholder-skeleton failure). Count clears ≥6 minimum. PASS on placement/count.
  - - Only 2 of 7 terms ("Equal Protection Clause," "demographic-conscious engineering") have a corresponding inline `<span/a class="glossary-term">` link in the running text. The other 5 ("Disparate Impact," "Reasonable Care Standard," "High-Risk AI System," "AI Litigation Task Force," "Automated Decision-Making Technology (ADMT)") are never linked from — and in the case of "Disparate Impact" and "ADMT," never even mentioned in — body copy. Improvement over the prior draft (which had zero inline links) but still incomplete. FLAG.
  - **References**
  - - 8 real, properly sourced MLA-formatted citations in the correct templated `#references` section (fixes the earlier placeholder-boilerplate failure). Meets ≥6/8+ minimum. PASS.
  - - All 8 sources trace to matching in-text parenthetical citations (Leadership Conference, Norton Rose Fulbright/National Law Review, U.S. DOJ, White House, Stanford HAI, Crowell & Moring, Colorado Sun). No fabrication apparent. PASS.
  - **Summary of blocking issues**
  - 1. Actual word count (~747) is materially below Dawn's acceptable floor (~990) despite a higher declared JSON-LD count (856) — this is a recurrence of the exact word-count-inflation problem already logged against this article; Writer/Quill need to add substance, not just re-declare a bigger number.
  - 2. Stat-grid "90%" figure remains uncited.
  - 3. 5 of 7 glossary terms have no inline `glossary-term` link anchoring them to the body text.

### Invisible article body (#25) — pure-python Maya replaced [persona] inside JS (2026-07-15)
**Symptom:** #25's article page rendered blank in the body — the full prose was in the
DOM but `<main class="article-content fade-in">` was stuck at `opacity:0`.
**Root cause:** `agents/maya_merge.py`'s placeholder-replacement loop did
`out.replace("[persona]", p["persona"])`. In the skeleton, `[persona]` appears ONLY as
real JavaScript — `var _btnColor=_authorColors[persona]||'00D9F5';` (a lookup by the
`persona` JS var), never as placeholder text. The replace turned it into
`_authorColorsdawn` (undefined) → ReferenceError → the whole inline `<script>` stopped
executing, including the IntersectionObserver + 800ms fallback that add `.visible` to
`.fade-in` elements. No `.visible` → body stays hidden. Older articles (#24) predate this
pure-python replacement, so their JS was intact — which is why "it worked before."
**Fix:** removed the `[persona]` replacement (persona is delivered via
`<meta property="article:persona">`, which that JS reads). `[slug]`/`[num]` only appear in
URLs/ids, so they're safe. Re-merged #25 → `_authorColors[persona]` intact, reveal script
runs, `main` gets `.visible` → opacity:1. Committed 3b9a4ce, pushed, verified live at
aima.productions. **Lesson:** maya_merge's blunt `str.replace` on `[token]` tokens is
dangerous near inline JS/CSS — a token that doubles as JS bracket-access (`obj[var]`) gets
corrupted. Any new token must be checked against the skeleton's `<script>`/`<style>` before
being added to that loop.


### Pipeline CRASH — #26 'Data Centers in Orbit: Why Big Tech Wants to Move AI's Power Problem to Space' — stage 'writer' (2026-07-16)
<!-- aima-failure-key: 2026-07-16|writer|[writer] Word count gate: 211 words outside acceptable 425-1200 (persona range 500-1000 wo -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [writer] Word count gate: 211 words outside acceptable 425-1200 (persona range 500-1000 words). Draft NOT accepted: articles/drafts/data-centers-in-orbit-why-026-draft.html. Re-run Writer, or adjust the persona range if this topic genuinely needs more room.
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 323, in run
    draft_path = writer.run(spec, research)
  File "D:\Apps\DevOps\Github\aima\agents\writer.py", line 195, in run
    raise RuntimeError(
    ...<4 lines>...
    )
RuntimeError: [writer] Word count gate: 211 words outside acceptable 425-1200 (persona range 500-1000 words). Draft NOT accepted: articles/drafts/data-centers-in-orbit-why-026-draft.html. Re-run Writer, or adjust the persona range if this topic genuinely needs more room.

```
- Full run log: pipeline.log


### Pipeline CRASH — #26 'Data Centers in Orbit: Why Big Tech Wants to Move AI's Power Problem to Space' — stage 'scout' (2026-07-16)
<!-- aima-failure-key: 2026-07-16|scout|CC agent [scout] failed (exit 1): -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** CC agent [scout] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): {"type":"result","subtype":"success","is_error":true,"api_error_status":529,"duration_ms":198894,"duration_api_ms":1380,"num_turns":1,"result":"API Error: 529 Overloaded. This is a server-side issue, usually temporary — try again in a moment. If it persists, check https://status.claude.com.","stop_reason":"stop_sequence","session_id":"47503b6c-ef74-4467-87f7-9f270243bb97","total_cost_usd":0.004776,"usage":{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_token
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 292, in run
    research = scout.run(spec)
  File "D:\Apps\DevOps\Github\aima\agents\scout.py", line 216, in run
    raw = call_cc_agent("scout", SCOUT_PROMPT, user_input)
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 261, in call_cc_agent
    raise RuntimeError(
    ...<3 lines>...
    )
RuntimeError: CC agent [scout] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): {"type":"result","subtype":"success","is_error":true,"api_error_status":529,"duration_ms":198894,"duration_api_ms":1380,"num_turns":1,"result":"API Error: 529 Overloaded. This is a server-side issue, usually temporary — try again in a moment. If it persists, check https://status.claude.com.","stop_reason":"stop_sequence","session_id":"47503b6c-ef74-4467-87f7-9f270243bb97","total_cost_usd":0.004776,"usage":{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_token

```
- Full run log: pipeline.log


### Pipeline CRASH — #26 'Data Centers in Orbit: Why Big Tech Wants to Move AI's Power Problem to Space' — stage 'quill' (2026-07-16)
<!-- aima-failure-key: 2026-07-16|quill|[quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word co -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word count 1217 outside acceptable 425-1200 (persona range 500-1000). Draft at: articles/drafts/data-centers-in-orbit-why-026-draft.html
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 332, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 93, in run
    raise RuntimeError(
    ...<2 lines>...
    )
RuntimeError: [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word count 1217 outside acceptable 425-1200 (persona range 500-1000). Draft at: articles/drafts/data-centers-in-orbit-why-026-draft.html

```
- Full run log: pipeline.log


### Pipeline CRASH — #26 'Data Centers in Orbit: Why Big Tech Wants to Move AI's Power Problem to Space' — stage 'porter' (2026-07-16)
<!-- aima-failure-key: 2026-07-16|porter|Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 1. -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 1.
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 417, in run
    porter_result = porter.run(spec, dry_run=dry_run, gs_enabled=cfg["GS_ENABLED"])
  File "D:\Apps\DevOps\Github\aima\agents\porter.py", line 103, in run
    git_push()
    ~~~~~~~~^^
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 408, in git_push
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\subprocess.py", line 577, in run
    raise CalledProcessError(retcode, process.args,
                             output=stdout, stderr=stderr)
subprocess.CalledProcessError: Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 1.

```
- Full run log: pipeline.log


### Pipeline CRASH — #27 'Power Hungry: The Carbon Ledger of the AI Compute Boom' — stage 'writer' (2026-07-17)
<!-- aima-failure-key: 2026-07-17|writer|[writer] Word count gate: 104 words outside acceptable 1020-1800 (persona range 1200-1500  -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [writer] Word count gate: 104 words outside acceptable 1020-1800 (persona range 1200-1500 words). Draft NOT accepted: articles/drafts/power-hungry-the-carbon-ledger-027-draft.html. Re-run Writer, or adjust the persona range if this topic genuinely needs more room.
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 323, in run
    draft_path = writer.run(spec, research)
  File "D:\Apps\DevOps\Github\aima\agents\writer.py", line 195, in run
    raise RuntimeError(
    ...<4 lines>...
    )
RuntimeError: [writer] Word count gate: 104 words outside acceptable 1020-1800 (persona range 1200-1500 words). Draft NOT accepted: articles/drafts/power-hungry-the-carbon-ledger-027-draft.html. Re-run Writer, or adjust the persona range if this topic genuinely needs more room.

```
- Full run log: pipeline.log


### Pipeline CRASH — #27 'Power Hungry: The Carbon Ledger of the AI Compute Boom' — stage 'quill' (2026-07-17)
<!-- aima-failure-key: 2026-07-17|quill|[quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word co -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word count 104 outside acceptable 1020-1800 (persona range 1200-1500); 2 H2 sections (need 5-6); 0 stat cards (need >=4); no pullquote found. Draft at: articles/drafts/power-hungry-the-carbon-ledger-027-draft.html
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 332, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 102, in run
    raise RuntimeError(
    ...<2 lines>...
    )
RuntimeError: [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word count 104 outside acceptable 1020-1800 (persona range 1200-1500); 2 H2 sections (need 5-6); 0 stat cards (need >=4); no pullquote found. Draft at: articles/drafts/power-hungry-the-carbon-ledger-027-draft.html

```
- Full run log: pipeline.log


### Pipeline CRASH — #27 'Power Hungry: The Carbon Ledger of the AI Compute Boom' — stage 'quill' (2026-07-17)
<!-- aima-failure-key: 2026-07-17|quill|[quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 8 H2 se -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 8 H2 sections (need 5-6). Draft at: articles/drafts/power-hungry-the-carbon-ledger-027-draft.html
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 332, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 102, in run
    raise RuntimeError(
    ...<2 lines>...
    )
RuntimeError: [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 8 H2 sections (need 5-6). Draft at: articles/drafts/power-hungry-the-carbon-ledger-027-draft.html

```
- Full run log: pipeline.log


### Pipeline CRASH — #27 'Power Hungry: The Carbon Ledger of the AI Compute Boom' — stage 'porter' (2026-07-20)
<!-- aima-failure-key: 2026-07-20|porter|Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 1. -->
- **Occurrences:** 2
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 1.
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 417, in run
    porter_result = porter.run(spec, dry_run=dry_run, gs_enabled=cfg["GS_ENABLED"])
  File "D:\Apps\DevOps\Github\aima\agents\porter.py", line 103, in run
    git_push()
    ~~~~~~~~^^
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 408, in git_push
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\subprocess.py", line 577, in run
    raise CalledProcessError(retcode, process.args,
                             output=stdout, stderr=stderr)
subprocess.CalledProcessError: Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 1.

```
- Full run log: pipeline.log


### Pipeline CRASH — #28 'The Termination Algorithm: How 'Token Consumption' Became a Layoff Metric' — stage 'quill' (2026-07-21)
<!-- aima-failure-key: 2026-07-21|quill|[quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 8 H2 se -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 8 H2 sections (need 5-6). Draft at: articles/drafts/the-termination-algorithm-how-token-028-draft.html
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 332, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 93, in run
    raise RuntimeError(
    ...<2 lines>...
    )
RuntimeError: [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): 8 H2 sections (need 5-6). Draft at: articles/drafts/the-termination-algorithm-how-token-028-draft.html

```
- Full run log: pipeline.log


### Pipeline CRASH — (spec not yet built) — stage 'priya' (2026-07-22)
<!-- aima-failure-key: 2026-07-22|priya|CC agent [trend_scout] failed (exit 1): -->
- **Occurrences:** 1
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** CC agent [trend_scout] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): {"type":"result","subtype":"success","is_error":true,"api_error_status":null,"duration_ms":2049,"duration_api_ms":0,"num_turns":1,"result":"Failed to authenticate: OAuth session expired and could not be refreshed","stop_reason":"stop_sequence","session_id":"e29481be-2ba1-4bbe-9fa6-580e2bee854c","total_cost_usd":0,"usage":{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier"
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 280, in run
    spec = priya.run()
  File "D:\Apps\DevOps\Github\aima\agents\priya.py", line 145, in run
    elif trend_scout.resolve_tbd_row(number):
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "D:\Apps\DevOps\Github\aima\agents\trend_scout.py", line 284, in resolve_tbd_row
    chosen = determine_trending_topic(
        row["author"],
    ...<2 lines>...
        number=number,
    )
  File "D:\Apps\DevOps\Github\aima\agents\trend_scout.py", line 172, in determine_trending_topic
    raw = call_cc_agent("trend_scout", TREND_SCOUT_PROMPT, user_input).strip()
          ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 261, in call_cc_agent
    raise RuntimeError(
    ...<3 lines>...
    )
RuntimeError: CC agent [trend_scout] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): {"type":"result","subtype":"success","is_error":true,"api_error_status":null,"duration_ms":2049,"duration_api_ms":0,"num_turns":1,"result":"Failed to authenticate: OAuth session expired and could not be refreshed","stop_reason":"stop_sequence","session_id":"e29481be-2ba1-4bbe-9fa6-580e2bee854c","total_cost_usd":0,"usage":{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier"

```
- Full run log: pipeline.log


### Pipeline CRASH — (spec not yet built) — stage 'priya' (2026-07-22)
<!-- aima-failure-key: 2026-07-22|priya|CC agent [trend_scout] failed: Claude Code OAuth expired. -->
- **Occurrences:** 4
- **First seen:** (backfilled — predates dedup)
- **Last seen:** (backfilled — predates dedup)
- **Error:** CC agent [trend_scout] failed: Claude Code OAuth expired.
Fix options (pick one):
  1. Re-authenticate now: open a terminal, run 'claude', complete OAuth.
     (Token lasts weeks — if this expires daily, Task Scheduler may be
      running as SYSTEM instead of your user account. Fix the task's
      'Run As' setting to use your Windows login.)
  2. Add ANTHROPIC_API_KEY=<key> to agents/.env for headless fallback.
     Get a key at https://console.anthropic.com/settings/keys
     Cost: ~$0.10-0.50/article (only charged when OAuth is expired).
  3. Fund OpenRouter + uncomment OPENROUTER_API_KEY in agents/.env.
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 280, in run
    spec = priya.run()
  File "D:\Apps\DevOps\Github\aima\agents\priya.py", line 145, in run
    elif trend_scout.resolve_tbd_row(number):
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "D:\Apps\DevOps\Github\aima\agents\trend_scout.py", line 284, in resolve_tbd_row
    chosen = determine_trending_topic(
        row["author"],
    ...<2 lines>...
        number=number,
    )
  File "D:\Apps\DevOps\Github\aima\agents\trend_scout.py", line 172, in determine_trending_topic
    raw = call_cc_agent("trend_scout", TREND_SCOUT_PROMPT, user_input).strip()
          ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 326, in call_cc_agent
    raise RuntimeError(
    ...<10 lines>...
    )
RuntimeError: CC agent [trend_scout] failed: Claude Code OAuth expired.
Fix options (pick one):
  1. Re-authenticate now: open a terminal, run 'claude', complete OAuth.
     (Token lasts weeks — if this expires daily, Task Scheduler may be
      running as SYSTEM instead of your user account. Fix the task's
      'Run As' setting to use your Windows login.)
  2. Add ANTHROPIC_API_KEY=<key> to agents/.env for headless fallback.
     Get a key at https://console.anthropic.com/settings/keys
     Cost: ~$0.10-0.50/article (only charged when OAuth is expired).
  3. Fund OpenRouter + uncomment OPENROUTER_API_KEY in agents/.env.

```
- Full run log: pipeline.log


### Pipeline HALT (recoverable) — #29 'The Lab That Runs Itself: How Autonomous Labs Are Compressing Materials Discovery From Years to Days' — stage 'scout' (2026-07-22)
<!-- aima-failure-key: 2026-07-22|scout|[scout] needs a SEARCH-CAPABLE backend and none is available. -->
- **Occurrences:** 3
- **First seen:** 2026-07-22T15:03:36
- **Last seen:** 2026-07-22T17:55:23
- **What happened:** scout/trend_scout had no search-capable backend, so the run stopped cleanly rather than fabricating research from a tool-less fallback.
- **Not a code bug.** No state advanced, no calendar row changed, nothing published.
- **Fix:**
```
[scout] needs a SEARCH-CAPABLE backend and none is available.
Claude Code OAuth is expired, so the CLI (with WebSearch/WebFetch) cannot run.
Deliberately NOT falling back to the direct Anthropic API: it has no tools, so scout would invent trends/statistics from training data instead of surveying real sources. A clean halt beats fabricated research.
This is a RECOVERABLE operator condition, not a code bug. Fix by:
  1. Re-authenticate the CLI: open a terminal, run 'claude', complete OAuth. (Best option — restores real search, subscription-billed.)
  2. Resolve the work by hand: for trend_scout, put a real title in the calendar row; for scout, pre-stage a research brief in articles/research/.
  3. Fund OpenRouter and set OPENROUTER_API_KEY — its ':online' models keep real web search, so it IS an acceptable backend for scout. (Joe's call — currently commented out in agents/.env on purpose.)
```
- Full run log: pipeline.log


### Scheduled-run OAuth hardening — Task Scheduler theory FALSIFIED (2026-07-22)

**The premise was wrong: there is no scheduled task.** Five identical `priya`-stage crashes
on 2026-07-22 were attributed to a scheduled run (`AIMA_pipeline_...`) running under the
wrong identity. Checked the actual machine: **no Windows scheduled task runs this pipeline
at all.** The only AIMA-related tasks are `AIMA-Backfill-002/003/007/012` (one-shot LinkedIn
`post_0NN.bat` backfills) and `InstapostAIMA`/`_Story` (a different project) — all already
running as `ShadowMonkey` / Interactive / Limited, none of them touching `run.py`. There is
also no Claude Code cron job and no cloud scheduled task. **The 5 runs were manual/dashboard-
triggered** (13:50, 13:57, 14:02, 14:02 — a retry cluster, consistent with hitting the same
wall each time).

**So the "Run As = SYSTEM" hypothesis that has been sitting in `base.py`'s error text across
multiple incidents is dead — do not re-derive it.** The real cause is simpler and dumber:
the `claude` CLI's OAuth token is genuinely expired for Joe's own interactive login. Proof —
running the canary directly in a normal PowerShell session as ShadowMonkey:

```
PS> claude --print "ping"
Failed to authenticate: OAuth session expired and could not be refreshed   (exit 1)
```

No task identity is involved. **Fix is a human action: open a terminal, run `claude`,
complete OAuth.** It cannot be done headlessly, and nothing in this repo can work around it
for the live-research agents (see next section for why we no longer try).

**The `base.py` error text was corrected** to stop asserting the Task-Scheduler theory.

### Live-research agents refuse the tool-less fallback (2026-07-22)

`call_anthropic_api()` (Tier B) is a plain Messages API call — **no tools, no web search**.
`scout` and `trend_scout` exist *only* to survey what is actually out there right now
(`scout-sources.json` feeds/APIs + WebSearch). If an OAuth expiry silently fell through to
Tier B, they would answer from training data and emit confident "trending" topics and
"research" stats with plausible-looking, unverified sources — a direct violation of the
zero-hallucination rule and strictly worse than the crash, because a crash is at least honest.

- `agents/base.py`: new `LIVE_RESEARCH_AGENTS = ("scout", "trend_scout")` +
  `LiveResearchUnavailableError`. In `call_cc_agent()`'s auth-failure branch these two now
  raise that error **instead of** Tier B, *even when `ANTHROPIC_API_KEY` is set*. Tier A
  (OpenRouter) is deliberately still allowed for them — its `:online` models keep real search,
  so it is an acceptable backend. **Every other CC agent (`iris`, `cora`, `lumen`, writers)
  keeps Tier B unchanged** — governance/synthesis work doesn't need live facts, so that's an
  acceptable trade there.
- `agents/marco.py`: `run()` catches `LiveResearchUnavailableError` *before* the generic
  `except Exception`, so it never lands in the `crashed` bucket. Returns
  `trend_scout_unavailable: True` + `halted_stage`. **No state advance, no calendar mutation,
  nothing published** — the catch is above Stage 9, so `_update_state()` never runs.
- `agents/marco.py`: new `_write_halt_to_claude_md()` writes a short, traceback-free
  `### Pipeline HALT (recoverable)` block. The point is that "go re-auth the CLI" no longer
  looks identical to "a genuine new bug needs debugging" in this file.
- `run.py`: `_classify()` gained the `trend_scout_unavailable` outcome (+ `halted_stage` in
  the status file) so alerting can distinguish the two.

**OpenRouter was NOT enabled** — `OPENROUTER_API_KEY` stays commented out in `agents/.env`
per Joe (DECISION-LOG.md). Funding it is the one path that would give `scout`/`trend_scout`
a tool-capable fallback without OAuth; that remains Joe's call.

### CLAUDE.md crash-log dedup (2026-07-22)

`_write_crash_to_claude_md()` appended a full traceback block unconditionally on every call.
Today that wrote the *same* traceback 5 times and pushed this file past 76KB. Both failure
writers now go through `_append_or_bump_claude_md()`, keyed on
`date | stage | error-first-line` via a `<!-- aima-failure-key: ... -->` marker: a same-day
repeat bumps `Occurrences:` / `Last seen:` on the existing entry instead of appending.
Verified live — two consecutive halted runs produced **one** block reading `Occurrences: 2`
with distinct first/last-seen timestamps. Already-duplicated historical blocks were
retro-compacted the same way (24 → 18 CRASH blocks, 76,817 → 67,983 bytes).

### Article #29 unblocked — row resolved without a CC call (2026-07-22)

Row 29 was still the literal `TBD — Trending Topic` for Kenji Nakamoto, and every run called
`trend_scout` to resolve it, which is exactly where all 5 crashes landed. `trend_scout`'s CC
path is unavailable, so the topic was surveyed live with Claude Code's own WebSearch and
persisted through `trend_scout.persist_topic_to_calendar()` — the sanctioned mutator, so the
"Trend Scout is the sole calendar writer" rule is preserved.

- **#29 = "The Lab That Runs Itself: How Autonomous Labs Are Compressing Materials Discovery
  From Years to Days"** (AI Science) — self-driving labs, squarely Kenji's beat.
- Two higher-ranked candidates were **rejected on dedup**: humanoid-robot production
  deployment (collides with #20 *Robots Go Public* and #23 *The Robot Beside You*) and the
  BCI trial split (collides with #33 *The Brain-Computer Interface Horizon*).
- Fiduciary trace: `articles/research/the-lab-that-runs-itself-topic-selection.json`
  (marked `resolved_by: claude_code_manual`, honest about not being a CC-agent selection)
  + `optimization/optimization_report.json`. Cost: $0.00.

**Confirmed by a real `python run.py`:** Priya now builds the #29 spec and gets past
Trend Scout cleanly; the run then halts at Scout with the new recoverable-halt path
(`outcome=trend_scout_unavailable`, cost $0.00) instead of crashing. **The pipeline will keep
halting at Scout until someone runs `claude` and completes OAuth** — that is the one
remaining blocker, and it is a human action.


### Pipeline CRASH — #29 'The Lab That Runs Itself: How Autonomous Labs Are Compressing Materials Discovery From Years to Days' — stage 'porter' (2026-07-23)
<!-- aima-failure-key: 2026-07-23|porter|Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 128. -->
- **Occurrences:** 1
- **First seen:** 2026-07-23T12:01:53
- **Last seen:** 2026-07-23T12:01:53
- **Error:** Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 128.
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 418, in run
    porter_result = porter.run(spec, dry_run=dry_run, gs_enabled=cfg["GS_ENABLED"])
  File "D:\Apps\DevOps\Github\aima\agents\porter.py", line 103, in run
    git_push()
    ~~~~~~~~^^
  File "D:\Apps\DevOps\Github\aima\agents\base.py", line 612, in git_push
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\subprocess.py", line 577, in run
    raise CalledProcessError(retcode, process.args,
                             output=stdout, stderr=stderr)
subprocess.CalledProcessError: Command '['git', 'push', 'origin', 'main']' returned non-zero exit status 128.

```
- Full run log: pipeline.log


### Pipeline CRASH — #29 'The Lab That Runs Itself: How Autonomous Labs Are Compressing Materials Discovery From Years to Days' — stage 'porter' (2026-07-23)
<!-- aima-failure-key: 2026-07-23|porter|HTTP Error 403: Forbidden -->
- **Occurrences:** 1
- **First seen:** 2026-07-23T12:12:21
- **Last seen:** 2026-07-23T12:12:21
- **Error:** HTTP Error 403: Forbidden
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 418, in run
    porter_result = porter.run(spec, dry_run=dry_run, gs_enabled=cfg["GS_ENABLED"])
  File "D:\Apps\DevOps\Github\aima\agents\porter.py", line 139, in run
    response = _post_to_gas(gas_endpoint, live_url)
  File "D:\Apps\DevOps\Github\aima\agents\porter.py", line 48, in _post_to_gas
    with urllib.request.urlopen(req, timeout=15) as resp:
         ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 187, in urlopen
    return opener.open(url, data, timeout)
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 493, in open
    response = meth(req, response)
  File "C:\Python314\Lib\urllib\request.py", line 602, in http_response
    response = self.parent.error(
        'http', request, response, code, msg, hdrs)
  File "C:\Python314\Lib\urllib\request.py", line 531, in error
    return self._call_chain(*args)
           ~~~~~~~~~~~~~~~~^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 464, in _call_chain
    result = func(*args)
  File "C:\Python314\Lib\urllib\request.py", line 611, in http_error_default
    raise HTTPError(req.full_url, code, msg, hdrs, fp)
urllib.error.HTTPError: HTTP Error 403: Forbidden

```
- Full run log: pipeline.log


### Pipeline CRASH — #29 'The Lab That Runs Itself: How Autonomous Labs Are Compressing Materials Discovery From Years to Days' — stage 'nova' (2026-07-23)
<!-- aima-failure-key: 2026-07-23|nova|HTTP Error 401: Unauthorized -->
- **Occurrences:** 1
- **First seen:** 2026-07-23T12:14:41
- **Last seen:** 2026-07-23T12:14:41
- **Error:** HTTP Error 401: Unauthorized
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 428, in run
    nova_result = nova.run(spec, porter_result["live_url"], dry_run=dry_run)
  File "D:\Apps\DevOps\Github\aima\agents\nova.py", line 106, in run
    company_urn = post_to_linkedin(article)
  File "D:\Apps\DevOps\Github\aima\linkedin_pipeline\linkedin_poster.py", line 403, in post_to_linkedin
    with urllib.request.urlopen(req, timeout=30) as resp:
         ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 187, in urlopen
    return opener.open(url, data, timeout)
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 493, in open
    response = meth(req, response)
  File "C:\Python314\Lib\urllib\request.py", line 602, in http_response
    response = self.parent.error(
        'http', request, response, code, msg, hdrs)
  File "C:\Python314\Lib\urllib\request.py", line 531, in error
    return self._call_chain(*args)
           ~~~~~~~~~~~~~~~~^^^^^^^
  File "C:\Python314\Lib\urllib\request.py", line 464, in _call_chain
    result = func(*args)
  File "C:\Python314\Lib\urllib\request.py", line 611, in http_error_default
    raise HTTPError(req.full_url, code, msg, hdrs, fp)
urllib.error.HTTPError: HTTP Error 401: Unauthorized

```
- Full run log: pipeline.log


### Pipeline CRASH — #30 'Who Owns the Output? The Intellectual Property Crisis in Generative AI' — stage 'scout' (2026-07-27)
<!-- aima-failure-key: 2026-07-27|scout|[scout] No research JSON found in CC output or on disk for 'who-owns-the-output-the'. Pars -->
- **Occurrences:** 1
- **First seen:** 2026-07-27T12:22:19
- **Last seen:** 2026-07-27T12:22:19
- **Error:** [scout] No research JSON found in CC output or on disk for 'who-owns-the-output-the'. Parser error: Expecting value: line 30 column 14 (char 1243)
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\scout.py", line 297, in run
    research = json.loads(raw[start:end])
  File "C:\Python314\Lib\json\__init__.py", line 346, in loads
    return _default_decoder.decode(s)
           ~~~~~~~~~~~~~~~~~~~~~~~^^^
  File "C:\Python314\Lib\json\decoder.py", line 345, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
               ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\json\decoder.py", line 363, in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 30 column 14 (char 1243)

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 293, in run
    research = scout.run(spec)
  File "D:\Apps\DevOps\Github\aima\agents\scout.py", line 300, in run
    raise RuntimeError(
    ...<2 lines>...
    ) from exc
RuntimeError: [scout] No research JSON found in CC output or on disk for 'who-owns-the-output-the'. Parser error: Expecting value: line 30 column 14 (char 1243)

```
- Full run log: pipeline.log


### Pipeline CRASH — #33 'The Brain-Computer Interface Horizon: Where Mind Meets Machine' — stage 'writer' (2026-07-30)
<!-- aima-failure-key: 2026-07-30|writer|[writer] Word count gate: 1816 words outside acceptable 1020-1800 (persona range 1200-1500 -->
- **Occurrences:** 1
- **First seen:** 2026-07-30T12:41:38
- **Last seen:** 2026-07-30T12:41:38
- **Error:** [writer] Word count gate: 1816 words outside acceptable 1020-1800 (persona range 1200-1500 words). Draft NOT accepted: articles/drafts/the-brain-computer-interface-horizon-033-draft.html. Re-run Writer, or adjust the persona range if this topic genuinely needs more room.
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 324, in run
    draft_path = writer.run(spec, research)
  File "D:\Apps\DevOps\Github\aima\agents\writer.py", line 230, in run
    raise RuntimeError(
    ...<4 lines>...
    )
RuntimeError: [writer] Word count gate: 1816 words outside acceptable 1020-1800 (persona range 1200-1500 words). Draft NOT accepted: articles/drafts/the-brain-computer-interface-horizon-033-draft.html. Re-run Writer, or adjust the persona range if this topic genuinely needs more room.

```
- Full run log: pipeline.log


### Pipeline CRASH — #33 'The Brain-Computer Interface Horizon: Where Mind Meets Machine' — stage 'quill' (2026-07-31)
<!-- aima-failure-key: 2026-07-31|quill|[quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word co -->
- **Occurrences:** 1
- **First seen:** 2026-07-31T14:27:08
- **Last seen:** 2026-07-31T14:27:08
- **Error:** [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word count 1816 outside acceptable 1020-1800 (persona range 1200-1500). Draft at: articles/drafts/the-brain-computer-interface-horizon-033-draft.html
- **Traceback:**
```
Traceback (most recent call last):
  File "D:\Apps\DevOps\Github\aima\agents\marco.py", line 333, in run
    article_path = quill.run(spec, research,
                             extra_instruction=quill_params["extra_instruction"],
                             draft_path=draft_path)
  File "D:\Apps\DevOps\Github\aima\agents\quill.py", line 95, in run
    raise RuntimeError(
    ...<2 lines>...
    )
RuntimeError: [quill] Draft incomplete, HALTING (Writer must fix — Quill does not auto-rewrite): word count 1816 outside acceptable 1020-1800 (persona range 1200-1500). Draft at: articles/drafts/the-brain-computer-interface-horizon-033-draft.html

```
- Full run log: pipeline.log
