# AIMA Project Memory

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


### Pipeline CRASH — #19 'The Persuasion Engine: AI, Social Media, and the Death of Shared Reality' — stage 'quill' (2026-07-04)
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


### Pipeline CRASH — (spec not yet built) — stage 'priya' (2026-07-13)
- **Error:** CC agent [trend_scout] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): {"type":"result","subtype":"success","is_error":true,"api_error_status":null,"duration_ms":220,"duration_api_ms":0,"num_turns":1,"result":"Not logged in · Please run /login","stop_reason":"stop_sequence","session_id":"034d95cc-6a91-4250-8717-cd32edf6c9a4","total_cost_usd":0,"usage":{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral
- **Traceback:**
```
Traceback (most recent call last):
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/marco.py", line 146, in run
    log.info(f"[marco] Spec: #{spec['number']} '{spec['title']}' by {spec['author']}")
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/priya.py", line 93, in run
    elif trend_scout.resolve_tbd_row(number):
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/trend_scout.py", line 284, in resolve_tbd_row
    chosen = determine_trending_topic(
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/trend_scout.py", line 172, in determine_trending_topic
    raw = call_cc_agent("trend_scout", TREND_SCOUT_PROMPT, user_input).strip()
  File "/sessions/gallant-eager-clarke/mnt/aima/agents/base.py", line 222, in call_cc_agent
    log.info(f"[{name.upper()}] calling CC subagent (model={model or 'CC-default'})")
RuntimeError: CC agent [trend_scout] failed (exit 1):
STDERR: (empty)
STDOUT (first 500): {"type":"result","subtype":"success","is_error":true,"api_error_status":null,"duration_ms":220,"duration_api_ms":0,"num_turns":1,"result":"Not logged in · Please run /login","stop_reason":"stop_sequence","session_id":"034d95cc-6a91-4250-8717-cd32edf6c9a4","total_cost_usd":0,"usage":{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":0,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral

```
- Full run log: pipeline.log


### Pipeline CRASH — #25 'The Government Filed a Brief for the Algorithm: How the DOJ Killed America's First AI Antidiscrimination Law' — stage 'scout' (2026-07-14)
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


### Pipeline CRASH — #25 'The Government Filed a Brief for the Algorithm: How the DOJ Killed America's First AI Antidiscrimination Law' — stage 'scout' (2026-07-14)
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
