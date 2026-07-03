# AIMA Pipeline v2.5 — Decision & Consolidation Log

**Session:** 2026-06-27 → 06-28
**Scope:** Dashboard batch wiring (`insights/`) + agent pipeline refactor (`aima/agents/`)

---

## 1. Backend standardization
- **Decision:** The full pipeline runs on **`agents/` (Marco)**, not the legacy `linkedin_pipeline/`.
- **`linkedin_pipeline/pipeline.py` was RETIRED** (deleted). Its publish/marketing/collect logic was a duplicate of the agent versions.
- Rationale: one backend = no drift. The agents already persist + reuse artifacts (Scout caches research, Quill writes the draft, Maya reuses images), which is exactly the "skip and reuse" primitive both toggles and standalone batches need.
- Dashboard "Run Full Pipeline" → `python run.py` → Marco.

## 2. Publish / Marketing split (Porter vs Nova)
- **Publish = Porter** (`agents/porter.py`): git push → wait 60s → poll `aima.productions/articles/<file>.html` every 10s until `og:title` present → log the **canonical** URL (`joselitosering.github.io/aima/...`) to Google Sheets. **No LinkedIn.**
- **Marketing = Nova** (`agents/nova.py`): LinkedIn company post + personal reshare.
- Corrected the live URL: `/insights/articles/` 404s; real path is **`/articles/`**. GS keeps the github.io canonical ("stick with canonical").

## 3. Stage toggles (full-pipeline config)
- **`pipeline_config.json`** (dashboard-owned) drives which stages run: `RESEARCH / WRITE / MAYA / PUBLISH / GS / MARKETING / ANALYTICS / LUMEN / CORA _ENABLED` (bools) + `QC_GATE` (`human` | `auto`).
- `agents/config.py:load_pipeline_config()` reads it (→ `.env` → defaults). `marco.run()` gates each stage; **a skipped stage reuses the most recent cached artifact**.
- `QC_GATE=human` → pipeline **holds after Vera** for review (no publish/marketing, no state advance). `auto` → proceeds.
- Dashboard: Articles → Data → **Full Pipeline Toggles** panel.

## 4. Vera = Quality ASSURANCE, not Control  ⚑ (token-burn fix)
- **Removed** Marco's Vera→Quill/Maya retry loop. It re-ran Quill/Maya up to 2× each on a QC rejection — this is what burned the token budget.
- New behavior: Vera runs **once**; on any non-approved verdict Marco **halts + reports** (`halted_for_review`), never re-runs a stage. Revisions are Iris/Joe's call (quality control).
- Vera's word-count check is now **range-based** (`spec["target_words"] ±10%`), not a fixed `>=1800` floor — shorter article types (e.g. 1200) are intentional.
- Targets are assignment params set at initiation; Scout/Quill/Maya get them up front, Vera just checks them off.

## 5. Pre-stage batches (feed the full run)
- **Maya batch** (`run_maya_batch.py`): pre-designs the next 2 calendar titles → `handoff/ready/`. A pipeline run's Maya picks them up **by article number** (`maya._pickup_from_handoff`) and moves them into `img/articles/`, else generates. Skips already-staged (no wasted Higgsfield credits). Created `handoff/ready/`.
- **Research batch** (`run_research_batch.py`): Scout pre-researches the next 2 titles → `articles/research/`. Cached briefs reused automatically by the pipeline.
- Both confirm-gated (credits/tokens), bounded to 2.

## 6. Priya batch (calendar manager — audit & reconcile)
- **`run_priya_batch.py`**: read-only audit + **safe fixes** (`--fix`). Cross-checks the editorial calendar against Scout/Quill/Maya artifacts + Porter/Nova/Echo logs across: sequencing, status, dates, authors, categories, tags, analytics, and downstream readiness.
- **Report-first** (like Vera): writes the full report to `optimization/priya_audit.json`; **surfaces** contingent issues for Iris/Joe sign-off; **auto-fixes only** the safe, reversible category — strips non-article entries from `posted_articles.json`.
- Decision-needing items (errors + warns) are **upserted into `optimization/optimization_report.json`** so Iris prioritizes them against everything else (next step: weigh against token cost).
- Autofix cost: deterministic, **one-time, no tokens, no loop**, git-reversible.

## 7. Applied fixes this session
- `posted_articles.json`: removed 2 non-article entries (`aima-pipeline-blueprint.html`, `aima-pipeline-diagram.html`) → 18 → 16.
- File maps updated in **CLAUDE.md** + the dashboard **File Map** tab (added `agents/`, run scripts, `pipeline_config.json`, `handoff/`; removed retired `pipeline.py`; Vera = assurance; Porter = aima.productions; Nova ≠ pipeline.py).

## 8. Dashboard batch row (final)
GA4 · LI Analytics · **Priya Audit+Fix** · **Research** · **Maya** · **Full Pipeline**
(collectors are non-gated; Priya/Research/Maya/Pipeline are confirm-gated; Full Pipeline honors the toggles.)

---

## OPEN — needs your decision (surfaced, deferred)
1. **3 title/number desyncs** (#014, #015, #017) — calendar title ≠ actual file's `og:title`. Needs the canonical title↔number mapping. *(Fix deferred until prioritized vs. token cost.)*
   - #014 calendar "Machines That Compose" vs file "Your AI Ethics Board Is a Press Release" (`ethics-theater-014`)
   - #015 calendar "Hallucination Nation" vs file "Machines That Compose" (`machines-that-compose-015`)
   - #017 calendar "Power Hungry" vs file "The Résumé Filter" (`resume-filter-017`)
2. **#017 author** — calendar "Joselito Sering" vs state "Dawn Ginhaua" (entangled with the #017 desync).
3. **11 Echo-overdue analytics** — operational: run the LI Analytics batch (Echo), not a calendar edit.
4. **Untagged categories** (Innovation, Production Blueprint, Automation, Industry Analysis, Trending) — Scout falls back to generic sources; fixable by extending `agents/scout.py:_CATEGORY_TAG_MAP`.
5. **Token-cost analysis** — to rank the above against other backlog items.
