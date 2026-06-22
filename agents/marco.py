"""Marco — Pipeline Orchestrator (Pure Python, no LLM calls).

Calls all CC subagents in sequence via call_cc_agent().
Owns every handoff. Nothing moves without Marco.

Stage sequence:
  1  Priya  → article spec
  2  Scout  → research JSON
  3  Quill  → copy-only HTML
  4  Maya   → merged article (images + skeleton)
  5  Format check (Marco validates before Vera)
  6  Vera   → QC verdict (retry Quill or Maya on fail)
  7  Porter → git commit + push + deploy guard + GS log
  8  Nova   → LinkedIn company post + personal reshare
  9  Log    → optimization_report.json + state update
"""

import json
import logging
import sys
from datetime import date, datetime, timezone

from agents.base import (
    read_json, write_json, read_file, write_file,
    append_optimization_report, REPO_ROOT, log,
)
from agents import priya, scout, quill, maya, vera, porter, nova, cora

MAX_QUILL_REVISIONS = 2
MAX_MAYA_REVISIONS = 2


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
    """Advance next_article_number and next_track in state file."""
    state = read_json("articles/aima-coworker-state.json")
    state["next_article_number"] = spec["number"] + 1
    state["last_run"] = date.today().isoformat()

    # Rotate track
    current_track = state.get("next_track", "trending")
    if current_track == "trending":
        state["next_track"] = "joselito"
    else:
        state["next_track"] = "trending"

    write_json("articles/aima-coworker-state.json", state)
    log.info(f"[marco] state updated: next_article={state['next_article_number']} track={state['next_track']}")


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

    log.info("=" * 55)
    log.info("[marco] AIMA pipeline starting")
    log.info(f"[marco] dry_run={dry_run}")
    log.info("=" * 55)

    # ── Stage 1: Priya → spec ────────────────────────────────
    log.info("[marco] Stage 1: Priya — building article spec")
    spec = priya.run()
    stages.append("priya")
    log.info(f"[marco] Spec: #{spec['number']} '{spec['title']}' by {spec['author']}")

    # ── Stage 2: Scout → research ────────────────────────────
    log.info("[marco] Stage 2: Scout — researching article")
    research = scout.run(spec)
    stages.append("scout")

    # ── Stage 3: Quill → copy HTML ───────────────────────────
    log.info("[marco] Stage 3: Quill — writing article copy")
    article_path = quill.run(spec, research)
    stages.append("quill")

    # ── Stage 4: Maya → merged article ───────────────────────
    log.info("[marco] Stage 4: Maya — generating images + merging")
    article_path = maya.run(article_path, spec)
    stages.append("maya")

    # ── Stage 5: Format check ────────────────────────────────
    log.info("[marco] Stage 5: Format pre-check")
    format_issues = _format_check(article_path, spec)
    if format_issues:
        flags.extend([f"format_check: {i}" for i in format_issues])
        log.warning(f"[marco] Format issues: {format_issues}")

    # ── Stage 6: Vera → QC (with retry) ─────────────────────
    log.info("[marco] Stage 6: Vera — QC check")
    vera_result = vera.run(article_path, spec)

    while vera_result["verdict"] != vera.VERDICT_APPROVED:
        verdict = vera_result["verdict"]
        notes = vera_result["notes"]

        if verdict == vera.VERDICT_COPY:
            revisions["quill"] += 1
            if revisions["quill"] > MAX_QUILL_REVISIONS:
                msg = f"Quill exceeded max revisions ({MAX_QUILL_REVISIONS}). Halting pipeline."
                log.error(f"[marco] {msg}")
                flags.append(f"quill_max_revisions: {revisions['quill']}")
                _write_failure_to_claude_md(spec, msg, notes)
                sys.exit(1)

            log.info(f"[marco] Vera: copy revision #{revisions['quill']} — re-running Quill")
            flags.append(f"quill_revision_{revisions['quill']}")
            revision_notes = "\n".join(notes)
            article_path = quill.run(spec, research)
            vera_result = vera.run(article_path, spec)

        elif verdict == vera.VERDICT_VISUAL:
            revisions["maya"] += 1
            if revisions["maya"] > MAX_MAYA_REVISIONS:
                msg = f"Maya exceeded max revisions ({MAX_MAYA_REVISIONS}). Halting pipeline."
                log.error(f"[marco] {msg}")
                flags.append(f"maya_max_revisions: {revisions['maya']}")
                _write_failure_to_claude_md(spec, msg, notes)
                sys.exit(1)

            log.info(f"[marco] Vera: visual revision #{revisions['maya']} — re-running Maya")
            flags.append(f"maya_revision_{revisions['maya']}")
            article_path = maya.run(article_path, spec)
            vera_result = vera.run(article_path, spec)

        else:
            # Unknown verdict — stop for human review
            msg = f"Vera returned unknown verdict: {verdict}"
            log.error(f"[marco] {msg}")
            _write_failure_to_claude_md(spec, msg, notes)
            sys.exit(1)

    stages.append("vera")
    log.info("[marco] Vera: approved")

    # ── Stage 7: Porter → deploy ─────────────────────────────
    log.info("[marco] Stage 7: Porter — commit + push + deploy guard")
    porter_result = porter.run(spec, dry_run=dry_run)
    stages.append("porter")

    # ── Stage 8: Nova → LinkedIn ─────────────────────────────
    log.info("[marco] Stage 8: Nova — LinkedIn post + reshare")
    nova_result = nova.run(spec, porter_result["live_url"], dry_run=dry_run)
    stages.append("nova")

    # ── Cora: governance check ───────────────────────────────
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

    # ── Stage 9: Log run ─────────────────────────────────────
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
