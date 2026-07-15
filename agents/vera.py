"""Vera — Quality Gate (CC subagent).

Receives the fully merged article from Marco and runs
the 10-point QC checklist (word count removed 2026-07-14 —
Writer now gates its own persona range). Returns a structured verdict.
"""

import json
import re

from agents.base import call_cc_agent, read_file, log
from agents.prompts import VERA_PROMPT


# Possible verdicts Vera returns
VERDICT_APPROVED = "approved"
VERDICT_COPY = "needs_revision: copy"
VERDICT_VISUAL = "needs_revision: visual"


def run(article_path: str, spec: dict) -> dict:
    """
    Run the 11-point QC check on the merged article.

    Returns a dict:
      {
        "verdict": "approved" | "needs_revision: copy" | "needs_revision: visual",
        "notes": [...],
        "raw": "full Vera output"
      }
    """
    slug = spec["slug"]
    og_image = spec["og_image"]
    number = spec.get("number", 0)
    alt_image = f"img/alt-img/aima-{number:03d}-{slug.replace(f'aima-{number:03d}-', '')}-alt.jpg"

    try:
        article_html = read_file(article_path)
    except FileNotFoundError:
        raise RuntimeError(f"[vera] Article not found at: {article_path}")

    # Inline the FULL article: single-shot is one pass (no re-reading), so the old
    # 12K truncation — which existed to bound multi-turn token bloat — would now
    # just hide the article's back half (refs, later sections) and cause false
    # "needs_revision" flags. Cap at 60K chars only as an extreme-outlier guard.
    html_excerpt = article_html[:60_000]

    user_input = f"""\
You have NO tools. Everything you need is inlined below — do NOT try to Read any
file. Judge the ARTICLE HTML given here and reply with text only.

EXPECTED COVER IMAGE REF (verify the HTML contains it): {og_image}
EXPECTED ALT IMAGE REF (verify the HTML contains it):   {alt_image}
AUTHOR: {spec.get('author')}

ARTICLE HTML (complete):
{html_excerpt}

IMAGES are verified separately by the pipeline (Marco's format check + Porter's
deploy guard, which confirms the live page renders with its og:image). You CANNOT
see the image files, so do NOT flag visual/image issues. Judge COPY ONLY:
structure (5-6 H2), word count, stat grid, pullquote, glossary (>=6), MLA
references (>=6), citations trace to sources, no fabrication. Return your verdict
on the FIRST LINE as exactly one of:
  approved
  needs_revision: copy

Then list each copy check result and any specific line-level notes for failures.\
"""

    log.info(f"[vera] running QC on: {article_path}")
    # single_shot: the article HTML is inlined above and Vera only returns a text
    # verdict (no file I/O) — same shape as Cora. Was an 8-15 turn agentic loop
    # re-reading the article each turn (1.46M tokens / $1.04); now one pass.
    raw = call_cc_agent("vera", VERA_PROMPT, user_input, single_shot=True)

    # Parse verdict from first non-empty line
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    verdict_line = lines[0].lower() if lines else ""

    if "approved" in verdict_line:
        verdict = VERDICT_APPROVED
    elif "copy" in verdict_line:
        verdict = VERDICT_COPY
    elif "visual" in verdict_line:
        verdict = VERDICT_VISUAL
    else:
        # Default: treat ambiguous output as needing human review
        verdict = VERDICT_COPY

    notes = lines[1:] if len(lines) > 1 else []
    log.info(f"[vera] verdict: {verdict} ({len(notes)} notes)")

    return {
        "verdict": verdict,
        "notes": notes,
        "raw": raw,
    }
