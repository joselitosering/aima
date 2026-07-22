"""Marco — Pipeline Orchestrator (Pure Python, no LLM calls).

Calls all CC subagents in sequence via call_cc_agent().
Owns every handoff. Nothing moves without Marco.

Stage sequence:
  1  Priya  → article spec (Trend Scout resolves TBD trending rows first)
  2  Scout  → research JSON
  3a Writer → free-form draft in author's voice (skipped if batch pre-staged one)
  3b Quill  → EDITS the draft to Vera's targets (copy-only HTML)
  4  Maya   → merged article (images + skeleton)
  5  Format check (Marco validates before Vera)
  6  Vera   → QC ASSURANCE verdict (halt + report on fail — no retry loop)
  7  Porter → git commit + push + deploy guard + GS log
  8  Nova   → LinkedIn company post + personal reshare
  9  Log    → optimization_report.json + state update
"""

import csv
import json
import logging
import os
import re
import sys
import traceback
from datetime import date, datetime, timezone

from agents.base import (
    read_json, write_json, read_file, write_file,
    append_optimization_report, REPO_ROOT, log,
    LiveResearchUnavailableError,
)
from agents.config import load_pipeline_config
from agents import base, priya, scout, writer, quill, maya, vera, porter, nova, cora


# ─────────────────────────────────────────────────────────────
# Category prioritization matrix
# Ranks categories by avg impressions from post_analytics.csv,
# joined to calendar by title-slug overlap. Written into the
# state file before priya.run() so the CC model sees it.
# ─────────────────────────────────────────────────────────────

def _build_category_priority() -> list:
    """
    Return categories ranked by avg LinkedIn impressions (desc).
    Categories with no analytics data append last (calendar order).
    Returns [] if analytics CSV is absent -- Priya falls back to date order.
    """
    analytics_path = REPO_ROOT / "linkedin_pipeline" / "post_analytics.csv"
    if not analytics_path.exists():
        log.info("[marco] post_analytics.csv absent -- no category priority injected")
        return []

    slug_impressions = {}
    try:
        with open(analytics_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                article = row.get("article", "")
                if not article:
                    continue
                slug = re.sub(r"[^a-z0-9]+", "-",
                              article.lower().replace(".html", "")).strip("-")
                try:
                    imp = float(row.get("impressions", 0) or 0)
                except (ValueError, TypeError):
                    imp = 0.0
                slug_impressions.setdefault(slug, []).append(imp)
    except Exception as exc:
        log.warning("[marco] post_analytics.csv read error: %s", exc)
        return []

    avg_by_slug = {s: sum(v) / len(v) for s, v in slug_impressions.items()}

    try:
        calendar_text = read_file("articles/aima-editorial-calendar.md")
    except Exception:
        return []

    cat_impressions = {}
    for line in calendar_text.splitlines():
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 6 or not cols[1].strip().isdigit():
            continue
        title = cols[3].strip()
        category = cols[4].strip()
        if not category or category == "Category":
            continue
        t_words = set(
            re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-").split("-")
        )
        cat_impressions.setdefault(category, [])
        for slug, avg in avg_by_slug.items():
            if len(t_words & set(slug.split("-"))) >= 3:
                cat_impressions[category].append(avg)
                break

    if not cat_impressions:
        return []

    ranked = sorted(
        cat_impressions.items(),
        key=lambda kv: (0 if kv[1] else 1, -(sum(kv[1]) / len(kv[1])) if kv[1] else 0),
    )
    result = [cat for cat, _ in ranked]
    log.info("[marco] category priority: %s", result)
    return result


# ─────────────────────────────────────────────────────────────
# Stage 5 — Format pre-check (Marco, before Vera)
# ─────────────────────────────────────────────────────────────

def _format_check(article_path: str, spec: dict) -> list[str]:
    """
    Quick structural check before sending to Vera.
    Returns a list of issues (empty = pass).
    """
    issues = []
    try:
        html = read_file(article_path)
    except FileNotFoundError:
        return [f"Article file not found: {article_path}"]

    og_image = spec.get("og_image", "")
    if og_image and og_image not in html:
        issues.append(f"og:image path '{og_image}' not found in HTML")

    if "TODO" in html or "PLACEHOLDER" in html or "lorem ipsum" in html.lower():
        issues.append("Article contains TODO / PLACEHOLDER / lorem ipsum")

    h2_count = html.lower().count("<h2")
    if h2_count < 5:
        issues.append(f"Only {h2_count} H2 sections (need 5-6)")

    return issues


# ─────────────────────────────────────────────────────────────
# Stage 9 — State + report update
# ─────────────────────────────────────────────────────────────

def _update_state(spec: dict):
    """Advance next_article_number in the state file.

    Track rotation is retired (2026-07-02, DECISION-LOG.md): the calendar is
    one canonical sequence and each row's Author column names the writer —
    there is no next_track to rotate."""
    state = read_json("articles/aima-coworker-state.json")
    state["next_article_number"] = spec["number"] + 1
    state["last_run"] = date.today().isoformat()
    state.pop("next_track", None)   # legacy field — retired

    write_json("articles/aima-coworker-state.json", state)
    log.info(f"[marco] state updated: next_article={state['next_article_number']}")


def _log_run(spec: dict, porter_result: dict, nova_result: dict,
             stages: list, flags: list, revisions: dict):
    append_optimization_report({
        "source": "marco",
        "date": date.today().isoformat(),
        "article_number": spec["number"],
        "live_url": porter_result.get("live_url", ""),
        "gs_row": porter_result.get("gs_row", -1),
        "company_urn": nova_result.get("company_urn", ""),
        "reshare_urn": nova_result.get("reshare_urn", ""),
        "stages_completed": stages,
        "flags": flags,
        "revisions": revisions,
    })


# ─────────────────────────────────────────────────────────────
# Run-level cost ceiling (added 2026-07-14)
# --max-turns caps a single CC call; this caps the WHOLE run. Checked before
# the big downstream stages (Maya, Vera) so a runaway authoring/QC spend can't
# push one run to unbounded cost — it halts like a Vera failure (report to
# CLAUDE.md, no publish) instead. Ceiling: env AIMA_RUN_COST_CEILING_USD
# (default $12; set 0 to disable). A normal run is ~$5–6.
# ─────────────────────────────────────────────────────────────

def _cumulative_cost_usd() -> float:
    """Sum recorded per-agent cost from token_budget.json for this run."""
    try:
        b = read_json("token_budget.json")
        return round(sum(float(a.get("cumulative_cost_usd", 0.0))
                         for a in b.get("agents", {}).values()), 4)
    except Exception:
        return 0.0


def _cost_ceiling_usd() -> float:
    try:
        return float(os.environ.get("AIMA_RUN_COST_CEILING_USD", "12.0"))
    except (TypeError, ValueError):
        return 12.0


def _over_cost_ceiling(before_stage: str, spec: dict, stages: list,
                       flags: list, revisions: dict):
    """Return a halt result dict if cumulative run cost exceeds the ceiling, else None."""
    ceiling = _cost_ceiling_usd()
    total = _cumulative_cost_usd()
    if ceiling and total > ceiling:
        msg = (f"Run cost ${total:.2f} exceeded ceiling ${ceiling:.2f} before stage "
               f"'{before_stage}'. Halting to prevent runaway spend (publish/marketing skipped).")
        log.warning(f"[marco] {msg}")
        flags.append(f"cost_ceiling_halt:${total:.2f}>${ceiling:.2f}")
        _write_failure_to_claude_md(spec, msg, [])
        return {
            "spec": spec, "porter": {}, "nova": {},
            "stages": stages, "flags": flags, "revisions": revisions,
            "halted_for_review": True, "cost_halt": True,
            "cost_usd": total, "cost_ceiling_usd": ceiling,
        }
    return None


# ─────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────

def run(dry_run: bool = False):
    """
    Execute the full AIMA article pipeline.
    dry_run=True skips git push and LinkedIn post.
    """
    stages: list[str] = []
    flags: list[str] = []
    revisions = {"quill": 0, "maya": 0}
    spec: dict = {}
    # Tracks which stage is in flight so a crash can be attributed correctly —
    # added 2026-07-04 after a scheduled run died silently between Scout and
    # Vera with zero record of where or why (see HANDOFF.md "Diagnosed silent
    # pipeline failure" + "Reproduced the Stage-3 crash mechanism").
    current_stage = "init"

    try:
        # ── Load stage toggles (dashboard → .env → defaults) ─────
        cfg = load_pipeline_config()
        # Expose QC_GATE to Vera's CC prompt, which references it.
        os.environ["QC_GATE"] = cfg["QC_GATE"]

        log.info("=" * 55)
        log.info("[marco] AIMA pipeline starting")
        log.info(f"[marco] dry_run={dry_run}")
        log.info(f"[marco] toggles: {cfg}")
        log.info("=" * 55)

        # ── Init token budget BEFORE Priya's CC call ──────────────
        # Moved ahead of Stage 1 on 2026-07-04: cora.init_budget() used to
        # run only after priya.run() returned, so Priya's own CC call had
        # no token_budget.json to record its usage into yet — the file
        # either didn't exist or belonged to the previous run's article
        # number. next_article_number is already authoritative in the
        # state file (Priya just re-confirms it via her own CC call), so
        # it's safe to init here. init_budget() re-runs again below once
        # spec['number'] is confirmed; it's idempotent for the same
        # run_date + article_number, so this doesn't double-reset anything.
        current_stage = "priya"
        _state_preview = read_json("articles/aima-coworker-state.json")
        cora.init_budget(_state_preview.get("next_article_number", 0))

        # ── Inject category priority before Priya reads state ──────────────────
        # Ranks categories by avg LinkedIn impressions so overdue articles in
        # high-performing categories are picked first within the same date tier.
        # Written to state -- Priya's CC prompt already injects the full state JSON.
        _cat_priority = _build_category_priority()
        if _cat_priority:
            _state_preview["category_priority"] = _cat_priority
            _state_preview["category_priority_note"] = (
                "Ranked by avg LinkedIn impressions (post_analytics.csv). "
                "Pick the next article whose category ranks highest here, "
                "then by oldest scheduled date within that category tier."
            )
            write_json("articles/aima-coworker-state.json", _state_preview)
            log.info("[marco] injected %d categories into state priority", len(_cat_priority))

        log.info("[marco] Stage 1: Priya — building article spec")
        spec = priya.run()
        stages.append("priya")
        log.info(f"[marco] Spec: #{spec['number']} '{spec['title']}' by {spec['author']}")

        # ── Confirm token budget matches Priya's returned number ─
        cora.init_budget(spec["number"])
        log.info(f"[marco] token_budget.json initialized for article #{spec['number']}")

        # ── Stage 2: Scout → research (RESEARCH_ENABLED) ─────────
        current_stage = "scout"
        if cfg["RESEARCH_ENABLED"]:
            log.info("[marco] Stage 2: Scout — researching article")
            research = scout.run(spec)
            stages.append("scout")
        else:
            log.info("[marco] Stage 2: Research disabled — reusing cached research")
            research = scout.load_cached(spec)
            flags.append("research_skipped" + ("" if research else "_no_artifact"))

        # ── Stage 3: Writer → Quill → final copy (WRITE_ENABLED) ───────────────
        # Restored two-call architecture (2026-07-13, reverts Direction B):
        # Direction B merged Writer+Quill to save a cold-start, but measured
        # cost was $2.15/article vs $1.53 two-call. Now: when no pre-staged
        # draft exists, Writer.run() writes free-form first (cold call #1),
        # then Quill.run() edits to QC targets (cold call #2). Skip-and-reuse
        # preserved — a Writer-batch pre-staged draft skips Writer.run().
        current_stage = "writer"
        if cfg["WRITE_ENABLED"]:
            # Article length follows the row author's persona range, capping
            # Priya's generic target so the finished article doesn't balloon.
            persona_target = writer.AUTHOR_SPECS[writer.resolve_author(spec)]["target_words"]
            spec["target_words"] = min(spec.get("target_words") or persona_target, persona_target)

            quill_params = cora.prepare_quill_call(spec)
            spec["target_words"] = quill_params["target_words"]   # enforce ceiling in spec

            draft_path = writer.find_draft(spec)
            if draft_path:
                log.info(f"[marco] Stage 3a: reusing pre-staged Writer-batch draft: {draft_path}")
                flags.append("writer_draft_reused")
            else:
                log.info(f"[marco] Stage 3a: no pre-staged draft — Writer writing "
                         f"free-form draft as {spec['author']}")
                draft_path = writer.run(spec, research)
                stages.append("writer")
                flags.append("writer_ran")

        current_stage = "quill"
        if cfg["WRITE_ENABLED"]:
            log.info(f"[marco] Stage 3b: Quill editing draft "
                     f"(target={quill_params['target_words']} words, "
                     f"ceiling={quill_params['ceiling']})")
            article_path = quill.run(spec, research,
                                     extra_instruction=quill_params["extra_instruction"],
                                     draft_path=draft_path)
            stages.append("quill")
        else:
            article_path = f"articles/{spec['filename']}"
            log.info(f"[marco] Stage 3: Write disabled — reusing existing draft: {article_path}")
            flags.append("write_skipped")
            if not (REPO_ROOT / article_path).exists():
                flags.append("write_skipped_no_artifact")
                log.warning(f"[marco] No existing draft at {article_path} — downstream stages may fail")

        # ── Cost ceiling: halt before the expensive Maya/Vera stages ──
        _halt = _over_cost_ceiling("maya", spec, stages, flags, revisions)
        if _halt:
            return _halt

        # ── Stage 4: Maya → merged article (MAYA_ENABLED) ────────
        current_stage = "maya"
        if cfg["MAYA_ENABLED"]:
            log.info("[marco] Stage 4: Maya — generating images + merging")
            article_path = maya.run(article_path, spec)
            stages.append("maya")
        else:
            log.info("[marco] Stage 4: Design disabled — reusing existing layout")
            flags.append("maya_skipped")

        # ── Stage 5: Format check ────────────────────────────────
        current_stage = "format_check"
        log.info("[marco] Stage 5: Format pre-check")
        format_issues = _format_check(article_path, spec)
        if format_issues:
            flags.extend([f"format_check: {i}" for i in format_issues])
            log.warning(f"[marco] Format issues: {format_issues}")

        # ── Stage 6: Vera → QC ASSURANCE (check-off only, no iteration) ──────────
        # Vera verifies the article against the assignment targets that Scout/Quill/
        # Maya were given up front. She is quality ASSURANCE, not quality control:
        # if something fails she HALTS the article and reports to Marco for review —
        # she never triggers a Quill/Maya re-run. Revision decisions belong to
        # Iris/Joe (quality control), not the pipeline.
        _halt = _over_cost_ceiling("vera", spec, stages, flags, revisions)
        if _halt:
            return _halt

        current_stage = "vera"
        log.info("[marco] Stage 6: Vera — QC assurance check")
        vera_result = vera.run(article_path, spec)
        verdict = vera_result.get("verdict")
        notes = vera_result.get("notes", [])

        if verdict != vera.VERDICT_APPROVED:
            msg = (f"Vera halted the article (verdict={verdict}). Reported to Marco for "
                   f"Iris/human review — no auto-revision (publish/marketing skipped).")
            log.warning(f"[marco] {msg}")
            flags.append(f"vera_halt:{verdict}")
            _write_failure_to_claude_md(spec, msg, notes)
            return {
                "spec": spec, "porter": {}, "nova": {},
                "stages": stages, "flags": flags, "revisions": revisions,
                "vera_verdict": verdict, "vera_notes": notes,
                "halted_for_review": True,
            }

        stages.append("vera")
        log.info("[marco] Vera: approved")

        # ── QC gate: human mode holds the run before publishing ──
        if cfg["QC_GATE"] == "human":
            log.info("[marco] QC_GATE=human — approved and HELD for human review. "
                     "Publish/marketing skipped; ship it with the Publish batch when ready.")
            flags.append("held_for_human_review")
            return {
                "spec": spec, "porter": {}, "nova": {},
                "stages": stages, "flags": flags, "revisions": revisions,
                "held_for_human_review": True,
            }

        porter_result: dict = {}
        nova_result: dict = {}

        # ── Stage 7: Porter → deploy (PUBLISH_ENABLED) ───────────
        current_stage = "porter"
        if cfg["PUBLISH_ENABLED"]:
            log.info("[marco] Stage 7: Porter — commit + push + deploy guard")
            porter_result = porter.run(spec, dry_run=dry_run, gs_enabled=cfg["GS_ENABLED"])
            stages.append("porter")
        else:
            log.info("[marco] Stage 7: Publish disabled — skipping Porter")
            flags.append("publish_skipped")

        # ── Stage 8: Nova → LinkedIn (MARKETING_ENABLED) ─────────
        current_stage = "nova"
        if cfg["MARKETING_ENABLED"] and porter_result.get("live_url"):
            log.info("[marco] Stage 8: Nova — LinkedIn post + reshare")
            nova_result = nova.run(spec, porter_result["live_url"], dry_run=dry_run)
            stages.append("nova")
        elif not cfg["MARKETING_ENABLED"]:
            log.info("[marco] Stage 8: Marketing disabled — skipping Nova")
            flags.append("marketing_skipped")
        else:
            log.info("[marco] Stage 8: No live URL (publish skipped) — skipping Nova")
            flags.append("marketing_skipped_no_url")

        # ── Cora: governance check (CORA_ENABLED) ────────────────
        current_stage = "cora"
        if cfg["CORA_ENABLED"]:
            log.info("[marco] Cora — governance + hallucination check")
            try:
                run_summary = {
                    "stages": stages,
                    "flags": flags,
                    "revisions": revisions,
                    "porter": porter_result,
                    "nova": nova_result,
                }
                cora.run(spec, article_path, run_summary)
                stages.append("cora")
            except Exception as exc:
                log.warning(f"[marco] Cora check failed (non-fatal): {exc}")
                flags.append(f"cora_error: {exc}")
        else:
            log.info("[marco] Cora disabled — skipping governance check")
            flags.append("cora_skipped")

        # ── Stage 9: Log run ─────────────────────────────────────
        current_stage = "log_run"
        log.info("[marco] Stage 9: logging run")
        _update_state(spec)
        _log_run(spec, porter_result, nova_result, stages, flags, revisions)

        log.info("=" * 55)
        log.info(f"[marco] Pipeline complete: #{spec['number']} '{spec['title']}'")
        log.info(f"[marco] Live URL: {porter_result.get('live_url')}")
        log.info(f"[marco] Company URN: {nova_result.get('company_urn')}")
        log.info("=" * 55)

        return {
            "spec": spec,
            "porter": porter_result,
            "nova": nova_result,
            "stages": stages,
            "flags": flags,
            "revisions": revisions,
        }
    except LiveResearchUnavailableError as exc:
        # EXPECTED, RECOVERABLE — not a bug. scout/trend_scout have no
        # search-capable backend (CC OAuth expired, no funded OpenRouter key),
        # and we refuse to fabricate research from a tool-less fallback.
        # Halt cleanly: no state advance (_update_state only runs at Stage 9),
        # no calendar mutation, no traceback dump in CLAUDE.md. Added 2026-07-22.
        _write_halt_to_claude_md(spec, current_stage, exc)
        log.warning(
            f"[marco] HALTED at stage '{current_stage}' — live research unavailable. "
            f"This is a recoverable operator condition, not a crash. Details:\n{exc}"
        )
        return {
            "spec": spec, "porter": {}, "nova": {},
            "stages": stages, "flags": flags + ["live_research_unavailable"],
            "revisions": revisions,
            "trend_scout_unavailable": True,
            "halted_stage": current_stage, "error": str(exc),
        }
    except Exception as exc:
        _write_crash_to_claude_md(spec, current_stage, exc)
        log.error(f"[marco] CRASHED at stage '{current_stage}': {exc}", exc_info=True)
        return {
            "spec": spec, "porter": {}, "nova": {},
            "stages": stages, "flags": flags, "revisions": revisions,
            "crashed": True, "crashed_stage": current_stage, "error": str(exc),
        }


def _write_failure_to_claude_md(spec: dict, message: str, notes: list):
    """Append a pipeline failure note to CLAUDE.md."""
    try:
        claude_md = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        claude_md = ""

    entry = (
        f"\n\n### Pipeline Failure — Article #{spec.get('number')} "
        f"({date.today().isoformat()})\n"
        f"- **Error:** {message}\n"
        f"- **Notes:**\n"
        + "\n".join(f"  - {n}" for n in notes)
    )
    (REPO_ROOT / "CLAUDE.md").write_text(claude_md + entry, encoding="utf-8")
    log.info("[marco] Failure written to CLAUDE.md — surface to Joe")


def _dedup_key(stage: str, exc: Exception) -> str:
    """Stable same-day identity for a failure: date | stage | error prefix.

    Only the error's FIRST line (truncated) is used, so a repeat of the same
    failure matches even when the tail of the message varies (timestamps,
    session ids, byte offsets).
    """
    first_line = str(exc).strip().splitlines()[0] if str(exc).strip() else "(no message)"
    first_line = first_line.replace("-->", "--").replace("|", "/")[:90]
    return f"{date.today().isoformat()}|{stage}|{first_line}"


def _append_or_bump_claude_md(key: str, entry: str, what: str):
    """Write `entry` to CLAUDE.md — or, if an entry with the same `key` was
    already written today, just bump its Occurrences / Last seen counters.

    Added 2026-07-22. Before this, _write_crash_to_claude_md appended a full
    traceback block unconditionally on every call: five identical scheduled-run
    failures on 2026-07-22 appended the SAME traceback five times and pushed
    CLAUDE.md past 76KB. Repeats are now one entry with a count, which also
    makes "this has happened N times" visible at a glance instead of requiring
    the reader to notice duplicate blocks.
    """
    path = REPO_ROOT / "CLAUDE.md"
    try:
        claude_md = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        claude_md = ""

    marker = f"<!-- aima-failure-key: {key} -->"
    ts = datetime.now().isoformat(timespec="seconds")

    if marker in claude_md:
        start = claude_md.index(marker)
        end = claude_md.find("\n### ", start)
        if end == -1:
            end = len(claude_md)
        block = claude_md[start:end]
        bumped, n_sub = re.subn(
            r"- \*\*Occurrences:\*\* (\d+)",
            lambda m: f"- **Occurrences:** {int(m.group(1)) + 1}",
            block, count=1,
        )
        if n_sub:   # legacy entries without the counter fall through to append
            bumped = re.sub(r"- \*\*Last seen:\*\* .*", f"- **Last seen:** {ts}",
                            bumped, count=1)
            path.write_text(claude_md[:start] + bumped + claude_md[end:], encoding="utf-8")
            count = re.search(r"- \*\*Occurrences:\*\* (\d+)", bumped).group(1)
            log.info(f"[marco] {what} is a repeat of an existing CLAUDE.md entry "
                     f"— bumped to {count} occurrences (no duplicate block appended)")
            return

    path.write_text(claude_md + entry, encoding="utf-8")
    log.info(f"[marco] {what} written to CLAUDE.md — surface to Joe")


def _write_crash_to_claude_md(spec: dict, stage: str, exc: Exception):
    """Append an unhandled-crash note (full traceback) to CLAUDE.md.

    Added 2026-07-04: a scheduled run previously died mid-Stage-3 with an
    uncaught RuntimeError and left no trace anywhere (no CLAUDE.md note, no
    persisted log — see HANDOFF.md "Diagnosed silent pipeline failure").
    run()'s top-level try/except now calls this on ANY unhandled exception
    from any stage, so a crash is always surfaced here even if pipeline.log
    is never read. Distinct from _write_failure_to_claude_md, which is for
    Vera's designed QC halt, not an unexpected crash.

    Deduped same-day since 2026-07-22 — see _append_or_bump_claude_md.
    """
    key = _dedup_key(stage, exc)
    article = f"#{spec.get('number')} '{spec.get('title', '?')}'" if spec else "(spec not yet built)"
    ts = datetime.now().isoformat(timespec="seconds")
    entry = (
        f"\n\n### Pipeline CRASH — {article} — stage '{stage}' "
        f"({date.today().isoformat()})\n"
        f"<!-- aima-failure-key: {key} -->\n"
        f"- **Occurrences:** 1\n"
        f"- **First seen:** {ts}\n"
        f"- **Last seen:** {ts}\n"
        f"- **Error:** {exc}\n"
        f"- **Traceback:**\n```\n{traceback.format_exc()}\n```\n"
        f"- Full run log: pipeline.log\n"
    )
    _append_or_bump_claude_md(key, entry, f"Crash at stage '{stage}'")


def _write_halt_to_claude_md(spec: dict, stage: str, exc: Exception):
    """Record a clean, EXPECTED halt (live research unavailable) in CLAUDE.md.

    Deliberately short and traceback-free: this is a known operator condition
    with a known fix, not a defect needing a stack trace. Keeping it visually
    distinct from '### Pipeline CRASH' is the whole point — before 2026-07-22
    an OAuth expiry and a genuine new bug looked identical in this file, so a
    reader had to parse a traceback to tell "go run 'claude'" from "debug me".
    """
    key = _dedup_key(stage, exc)
    article = f"#{spec.get('number')} '{spec.get('title', '?')}'" if spec else "(spec not yet built)"
    ts = datetime.now().isoformat(timespec="seconds")
    entry = (
        f"\n\n### Pipeline HALT (recoverable) — {article} — stage '{stage}' "
        f"({date.today().isoformat()})\n"
        f"<!-- aima-failure-key: {key} -->\n"
        f"- **Occurrences:** 1\n"
        f"- **First seen:** {ts}\n"
        f"- **Last seen:** {ts}\n"
        f"- **What happened:** scout/trend_scout had no search-capable backend, so the run "
        f"stopped cleanly rather than fabricating research from a tool-less fallback.\n"
        f"- **Not a code bug.** No state advanced, no calendar row changed, nothing published.\n"
        f"- **Fix:**\n```\n{exc}\n```\n"
        f"- Full run log: pipeline.log\n"
    )
    _append_or_bump_claude_md(key, entry, f"Recoverable halt at stage '{stage}'")
