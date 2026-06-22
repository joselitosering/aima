"""Vera — Quality Gate (CC subagent).

Receives the fully merged article from Marco and runs
the 11-point QC checklist. Returns a structured verdict.
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

    user_input = f"""\
ARTICLE PATH: {article_path}
COVER IMAGE:  {og_image}
ALT IMAGE:    {alt_image}
AUTHOR:       {spec.get('author')}

ARTICLE HTML:
{article_html}

Run all 11 QC checks. Return your verdict on the first line as exactly one of:
  approved
  needs_revision: copy
  needs_revision: visual

Then list each check result and any specific line-level notes for failures.\
"""

    log.info(f"[vera] running QC on: {article_path}")
    raw = call_cc_agent("vera", VERA_PROMPT, user_input)

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
