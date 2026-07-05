"""Marco — Pipeline Orchestrator (Pure Python, no LLM calls).

Calls all CC subagents in sequence via call_cc_agent().
Owns every handoff. Nothing moves without Marco.

Stage sequence:
  1  Priya  → article spec (Trend Scout resolves TBD trending rows first)
  2  Scout  → research JSON
  3a Draft   → reuse a pre-staged Writer-batch draft if one exists (else none)
  3b Quill   → EDITS the draft to Vera's targets, OR authors+edits in one call
               when no draft exists (Direction B: Writer stage merged into Quill
               to save one cold `claude` subprocess per from-scratch article)
  4  Maya   → merged article (images + skeleton)
  5  Format check (Marco validates before Vera)
  6  Vera   → QC ASSURANCE verdict (halt + report on fail — no retry loop)
  7  Porter → git commit + push + deploy guard + GS log
  8  Nova   → LinkedIn company post + personal reshare
  9  Log    → optimization_report.json + state update
"""

import json
import logging
import os
import sys
import traceback
from datetime import date, datetime, timezone

from agents.base import (
    read_json, write_json, read_file, write_file,
    append_optimization_report, REPO_ROOT, log,
)
from agents.config import load_pipeline_config
from agents import base, priya, scout, writer, quill, maya, vera, porter, nova, cora


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

        # ── Stage 3: author + edit → final copy (WRITE_ENABLED) ──────────────
        # Direction B (2026-07-04, see HANDOFF.md recommended fix #2): the Writer
        # stage no longer spends its OWN cold `claude` subprocess inside the full
        # pipeline. Skip-and-reuse is preserved — if the standalone Writer batch
        # (run_writer_batch.py) has already pre-staged a free-form draft, Quill
        # EDITS it exactly as before. When no draft exists, Quill AUTHORS then
        # EDITS in one call (two-phase: write in the author's persona voice, then
        # edit to Vera's checklist), collapsing the old Writer(cold) + Quill(cold)
        # two-launch sequence into a single cold-start per from-scratch article.
        # writer.run() is untouched and still drives the Writer batch.
        current_stage = "quill"
        if cfg["WRITE_ENABLED"]:
            # Article length follows the row author's (lowered 2026-07-04) persona
            # range, capping Priya's generic target so the finished article — merged
            # authoring or edited draft — doesn't balloon back past persona length.
            # Priya may still go SHORTER for a specific goal; the persona is the
            # ceiling, not the floor. min() keeps that direction.
            persona_target = writer.AUTHOR_SPECS[writer.resolve_author(spec)]["target_words"]
            spec["target_words"] = min(spec.get("target_words") or persona_target, persona_target)

            quill_params = cora.prepare_quill_call(spec)
            spec["target_words"] = quill_params["target_words"]   # enforce ceiling in spec

            draft_path = writer.find_draft(spec)
            if draft_path:
                log.info(f"[marco] Stage 3a: reusing pre-staged Writer-batch draft: {draft_path}")
                flags.append("writer_draft_reused")
            else:
                log.info(f"[marco] Stage 3a: no pre-staged draft — Quill authors+edits "
                         f"in one call as {spec['author']} (Writer stage merged)")
                flags.append("writer_merged_into_quill")

            log.info(f"[marco] Stage 3b: Quill — "
                     f"{'editing draft to targets' if draft_path else 'authoring+editing'} "
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


def _write_crash_to_claude_md(spec: dict, stage: str, exc: Exception):
    """Append an unhandled-crash note (full traceback) to CLAUDE.md.

    Added 2026-07-04: a scheduled run previously died mid-Stage-3 with an
    uncaught RuntimeError and left no trace anywhere (no CLAUDE.md note, no
    persisted log — see HANDOFF.md "Diagnosed silent pipeline failure").
    run()'s top-level try/except now calls this on ANY unhandled exception
    from any stage, so a crash is always surfaced here even if pipeline.log
    is never read. Distinct from _write_failure_to_claude_md, which is for
    Vera's designed QC halt, not an unexpected crash.
    """
    try:
        claude_md = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        claude_md = ""

    article = f"#{spec.get('number')} '{spec.get('title', '?')}'" if spec else "(spec not yet built)"
    entry = (
        f"\n\n### Pipeline CRASH — {article} — stage '{stage}' "
        f"({date.today().isoformat()})\n"
        f"- **Error:** {exc}\n"
        f"- **Traceback:**\n```\n{traceback.format_exc()}\n```\n"
        f"- Full run log: pipeline.log\n"
    )
    (REPO_ROOT / "CLAUDE.md").write_text(claude_md + entry, encoding="utf-8")
    log.info(f"[marco] Crash at stage '{stage}' written to CLAUDE.md — surface to Joe")
