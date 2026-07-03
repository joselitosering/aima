# AIMA Handoff — v2.6 (Batch & Toggle Integration)

**Date:** 2026-06-28 · **Supersedes:** AIMA-HANDOFF-2026-06-21
**Scope:** Dashboard-driven batch execution + full-pipeline stage toggles, on the `agents/` backend.

> **For agents:** read this + `CLAUDE.md` (File Map) before acting. The pipeline runs on
> **`agents/` (Marco)**. `linkedin_pipeline/pipeline.py` is **retired** — do not call or recreate it.

---

## 1. What this version is

The AIMA engine is now operable as **standalone batches** (one runnable unit per agent) **and** as a
**toggle-gated full pipeline** (Marco). Everything is triggerable from the dashboard
(`insights/` → Articles → Data → *Batch Runs* / *Full Pipeline Toggles*; or Agents → *Batch Modes*),
and any batch can be **scheduled** via Windows Task Scheduler.

Two repos:
- **`D:\Apps\DevOps\Github\aima`** — the engine (`agents/`, `run_*.py`, articles, data).
- **`D:\Apps\DevOps\Github\insights`** — the Next.js dashboard (`/api/run`, `/api/pipeline-config`, `/api/schedule`).

---

## 2. The agent roster → where each lives

| Stage | Agent | Module | Standalone batch | Cost |
|---|---|---|---|---|
| Plan / calendar | Priya | `agents/priya.py` | `run_priya_batch.py` (audit+`--fix`) | none (Python) |
| Research | Scout | `agents/scout.py` | `run_research_batch.py` | tokens (CC) |
| Trending topics | **Trend Scout** | `agents/trend_scout.py` | *(inside research/writer batches)* | tokens (CC, 12k) |
| Write (free voice) | **Writer** | `agents/writer.py` | `run_writer_batch.py` | tokens (CC) |
| Edit to spec | **Quill** | `agents/quill.py` | *(in pipeline; EDITS writer drafts — wired 2026-07-02)* | tokens (CC) |
| Design | Maya | `agents/maya.py` | `run_maya_batch.py` | Higgsfield credits |
| QC | Vera | `agents/vera.py` | `run_review_batch.py` | tokens (CC) |
| Publish | Porter | `agents/porter.py` | `run_publish_batch.py` | git push + GS |
| Market | Nova | `agents/nova.py` | `run_marketing_batch.py` | live LinkedIn |
| LinkedIn analytics | Echo | `agents/echo.py` | `run_analytics_batch.py` | none (Python) |
| Cross-platform | Lumen | `agents/lumen.py` | `run_lumen_batch.py` | tokens (CC) |
| Token governance | Cora | `agents/cora.py` | `run_token_audit.py` | none (read-only) |
| Editorial advisory | Iris | `agents/iris.py` | `run_optimization_batch.py` | tokens (CC) |
| Orchestrator | Marco | `agents/marco.py` | `run.py` (full pipeline) | — |

Shared infra: `agents/config.py` (toggles + budgets), `agents/base.py` (CC calls, file IO, git),
`agents/prompts.py` (system prompts).

---

## 3. Content flow (who hands to whom)

```
Priya (calendar → article-spec)                articles/aima-coworker-state.json + calendar
   → Scout (research)                          → articles/research/<slug>-research.json
   → Writer (free draft in persona voice)      → articles/drafts/<slug>-NNN-draft.html
   → Quill (EDITS draft to Vera's checklist)   → articles/<filename>.html      [wired 2026-07-02: picks up drafts/, else writes from scratch]
   → Maya (images; reuses handoff/ready/ by #) → img/articles/ , img/alt-img/
   → Vera (QC ASSURANCE: approve or HALT+report — never re-runs a stage)
   → Porter (push → poll aima.productions → GS canonical)   → posted_articles.json
   → Nova (LinkedIn company + personal reshare)             → post_log.json
Independent: Echo (LinkedIn metrics 48h+) → post_analytics.csv → Priya reconciles
             Lumen (LinkedIn + GA4 merge) → optimization_report.json + platform_summary.json
             Cora (token ledger) , Iris (advisory → edits calendar + CLAUDE.md)
```

**Pre-stage batches feed the full run** (cheap to prep, reused via skip-and-reuse):
Priya → Research → Writer → Maya populate `research/`, `drafts/`, `handoff/ready/`; a Full Pipeline run
reuses those cached artifacts instead of regenerating.

---

## 4. Stage toggles (`pipeline_config.json`)

Dashboard writes it; `agents/config.py:load_pipeline_config()` reads it (→ `.env` → defaults);
`marco.run()` gates every stage. **A toggled-off stage reuses the most recent cached artifact.**

```
RESEARCH_ENABLED  WRITE_ENABLED  MAYA_ENABLED  PUBLISH_ENABLED  GS_ENABLED
MARKETING_ENABLED  ANALYTICS_ENABLED  LUMEN_ENABLED  CORA_ENABLED   (booleans)
QC_GATE = "human" | "auto"
```
- `QC_GATE=human` → pipeline **holds after Vera** for review (no publish/marketing, no state advance).
- `QC_GATE=auto` → proceeds end-to-end.
- `ANALYTICS_ENABLED` / `LUMEN_ENABLED` gate the **independent** Echo/Lumen runs (not inside Marco).

---

## 5. Fiduciary duty — how it stays cost-safe & autonomous

This engine is built to run **autonomously without burning budget**. Honor these invariants:

1. **Vera never iterates.** She is quality **assurance**: she checks targets the writers were given up
   front and **halts + reports to Marco/Iris** on failure. The old Vera→Quill/Maya retry loop was the
   token-burn and was **removed**. Revisions are Iris/Joe's call (quality control).
2. **Targets are set at initiation.** Word-count is range-based per persona (Joselito 1800+, Dawn
   1200–1500, Kenji 900–1200), checked as `target_words ±10%` — **never a fixed 1800 floor**.
3. **Skip-and-reuse, not re-fetch.** Scout caches research; Maya reuses `handoff/ready/` by article #;
   Quill (once wired) reuses drafts. Toggled-off stages reuse the last artifact.
4. **Writers halt without research.** `run_writer_batch.py` reports and **exits** if Scout has no brief
   (it never researches — that's Scout).
5. **Gate the expensive/irreversible.** Token/credit/LinkedIn batches require confirmation in the
   dashboard (`gated`); read-only ones (Token Audit, GA4) run free. Cora's `token_budget.json` is the
   ledger — `run_token_audit.py` flags over-budget agents (read-only, no tokens).
6. **Report, don't auto-mutate source-of-truth.** Priya surfaces calendar bugs to
   `optimization_report.json` for Iris to prioritize, and auto-fixes only the safe, reversible
   `posted_articles.json` hygiene. Iris is the only agent that edits the calendar (she's the authority).

---

## 6. Dashboard control surface (`insights/`)

- **`/api/run`** (SSE) — one POST `{script, confirmed?}` per batch; `gated` targets need `confirmed:true`.
  Streams `data:{line}` then `data:{done,exitCode}`. cwd = the script's dir.
- **`/api/pipeline-config`** — GET/POST the toggles → `pipeline_config.json`.
- **`/api/schedule`** — POST `{script, when, recurrence}` creates a real **Windows Task Scheduler** task
  (`schtasks`) running the batch script; GET lists; DELETE removes. Persists to `schedule.json`.
  Recurrence: `ONCE | DAILY | WEEKLY`. Scheduled runs fire even when the dashboard is closed.
- UI: **Articles → Data** = toggles + batch buttons (live "▶ Fired…" log on click).
  **Agents → Batch Modes** = Run Engine (Run Now / ⏱ Schedule) + **File Map** tab.

Live URLs: poll **`https://aima.productions/articles/<file>.html`** for liveness;
log the **canonical** **`https://joselitosering.github.io/aima/articles/<file>.html`** to Google Sheets.

---

## 6b. Trending-topic determination + unified calendar (added 2026-07-02)

**The calendar is ONE canonical sequence (per Joe — see DECISION-LOG.md):** a single
table `| # | Date | Title | Category | Read | Tone Note | Author |`, rows 1–64.
Slot labels (D1–D13/K1–K12) and per-author sections are retired. Published rows keep
their real `article:id` (this resolved the §7 #014/#015/#017 desyncs); unpublished
rows are numbered 19+ in date order across all authors. Author is a per-row attribute
Joe can reassign for a different mood — nothing tracks by author anymore.

"TBD — Trending Topic" rows are resolved automatically by **`agents/trend_scout.py`**
(new CC agent, budget 12k): it reads the row's **Author column**, loads that writer's
persona file (any author works — generic beat if no profile), surveys beat-filtered
sources from `scout-sources.json`, dedups against calendar + `articles_written[]` +
`articles/research/`, writes the chosen title+category **back into the calendar row**
(durable + idempotent — re-runs see the real title and skip straight to Scout), and
logs rationale + sources to `articles/research/[slug]-topic-selection.json` and
`optimization_report.json`. TBD rows now enter the default research/writer batch walk;
target one explicitly via `--article N`. Writers still HALT without a Scout brief —
Trend Scout only replaces the title. The Maya batch skips TBD rows (no cover art for
placeholders). NOTE: `next_article_number` (19) now walks the date-ordered sequence —
next up is #19 "The Persuasion Engine".

---

## 7. Open items (next session — planned 2026-07-02 10:30 PM)

**Target flow (per Joe):** Scout tier resolves TBD trending assignments (Trend Scout
picks the topic for the row's author → Scout collects the research) → **author writes**
the draft → hands to **Quill** to edit into Vera's requirements → **Maya** designs, with
the real title already logged in the calendar for **Priya**. Concretely:

0. **Resume the paused live proof** (no re-roll expected — titles already persisted):
   `python run_research_batch.py --article 23` (Scout research for Kenji's Robot row —
   the earlier run was stopped mid-call, row 25's research is already cached), then
   `python run_writer_batch.py --article 25` and `--article 23` (drafts), then the
   idempotency spot-check: `python run_research_batch.py --article 25` must use the
   cached brief with zero CC calls.
1. ~~Wire Trend Scout + Scout into the FULL pipeline path~~ — **DONE 2026-07-02:**
   `priya.run()` calls `trend_scout.resolve_tbd_row(next_article_number)` BEFORE her CC
   run — a TBD row gets its real title persisted to the calendar, then Priya reads the
   updated row. No-op (zero CC) for real titles; skipped under `--dry-run`.
2. ~~Quill-as-editor wiring~~ — **DONE 2026-07-02:** Marco's WRITE stage is now
   3a Writer (reuses a cached `articles/drafts/` draft, else the row's author drafts
   in persona voice) → 3b Quill (EDITS the draft to Vera targets / word ceiling;
   writes from scratch only when no draft). `writer.find_draft()` matches by
   slug+number, number, then slug. QUILL_PROMPT reframed editor-first.
3. ~~State hygiene~~ — **DONE 2026-07-02:** `next_track` and `trending.topic_queue`
   removed from `aima-coworker-state.json` (and from marco/priya/base code — Marco no
   longer rotates tracks; the dry-run stub reads the row's Author column).
   `next_article_number=19` = "The Persuasion Engine" (date-ordered next).
4. **Commit checkpoint** — done this session (see git log, both repos).

Carried-over items:

1. ~~Quill-as-editor wiring~~ — **DONE 2026-07-02** (see item 2 in the planned block above).
2. ~~**3 title/number desyncs** (#014/#015/#017)~~ — **RESOLVED 2026-07-02** by the unified
   canonical renumbering (§6b / DECISION-LOG.md): row 14 = Dawn's #014, "Machines That
   Compose" renumbered to 15, #017 "The Résumé Filter" row added.
3. **Batch & toggle live tests** — exercise each button + each toggle combo (user to run).
4. **Social arm (planned):** Instagram, YouTube, TikTok. Lumen already aggregates Meta/TikTok/BMC in
   its prompt; add per-platform poster agents alongside Nova and per-platform collectors feeding Lumen.

---

## 8. Quick reference — run a batch from the CLI

```
python run.py [--dry-run]              # full pipeline (Marco, honors toggles)
python run_priya_batch.py [--fix]      # calendar audit (+ safe fixes)
python run_research_batch.py           # Scout researches next 2 rows (TBD rows: Trend Scout resolves the title first)
python run_research_batch.py --article 26 29   # specific canonical rows
python run_writer_batch.py [--author joselito|dawn|kenji] [--article N]
python run_maya_batch.py               # design next 2 covers → handoff/ready/
python run_publish_batch.py            # Porter publishes staged articles (push + GS, no LinkedIn)
python run_review_batch.py             # Vera QC of staged articles
python run_marketing_batch.py          # Nova posts published-but-unmarketed
python run_analytics_batch.py          # Echo: LinkedIn metrics → post_analytics.csv
python run_lumen_batch.py [--force]    # merge LinkedIn + GA4 → optimization report
#   ↳ dedups before the CC call (skips if a same-day lumen entry exists);
#     --force bypasses the dedup and REPLACES today's entry (intra-day refresh).
#     no lumen_secrets.json ⇒ reduced GA4+LinkedIn prompt on claude-haiku-4-5,
#     writes ga4_analytics.csv + GA4-only platform_summary.json for the dashboard,
#     + "meta/tiktok/bmc: skipped" trace. See CLAUDE.md → Lumen Agent.
python run_token_audit.py              # Cora: token ledger report
python run_optimization_batch.py       # Iris advisory (edits calendar + CLAUDE.md)
```
