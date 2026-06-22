"""Iris — Strategic Director (CC subagent).

Reads optimization_report.json (written by Marco, Lumen, Cora),
updates the editorial calendar, and writes strategic decisions to CLAUDE.md.
Run weekly via run_iris.py.
"""

import json
import re
from datetime import date

from agents.base import call_cc_agent, read_json, read_file, write_file, REPO_ROOT, log
from agents.prompts import IRIS_PROMPT


def run() -> dict:
    """
    Read all optimization reports, produce editorial decisions,
    update aima-editorial-calendar.md, and write decisions to CLAUDE.md.
    Returns a decisions summary dict.
    """
    report_entries = read_json("optimization/optimization_report.json")
    if not isinstance(report_entries, list):
        report_entries = []

    try:
        calendar = read_file("articles/aima-editorial-calendar.md")
    except FileNotFoundError:
        calendar = "[Editorial calendar not found]"

    try:
        claude_md = read_file("CLAUDE.md")
    except FileNotFoundError:
        claude_md = ""

    today = date.today().isoformat()

    # Separate entries by source for clarity
    marco_entries = [e for e in report_entries if e.get("source") == "marco"]
    lumen_entries = [e for e in report_entries if e.get("source") == "lumen"]
    cora_entries  = [e for e in report_entries if e.get("source") == "cora"]

    user_input = f"""\
TODAY: {today}

OPTIMIZATION REPORT — MARCO ENTRIES ({len(marco_entries)} runs):
{json.dumps(marco_entries[-10:], indent=2)}

OPTIMIZATION REPORT — LUMEN ENTRIES ({len(lumen_entries)} analytics):
{json.dumps(lumen_entries[-10:], indent=2)}

OPTIMIZATION REPORT — CORA ENTRIES ({len(cora_entries)} governance):
{json.dumps(cora_entries[-10:], indent=2)}

CURRENT EDITORIAL CALENDAR (aima-editorial-calendar.md):
{calendar}

CURRENT CLAUDE.md (last 2000 chars):
{claude_md[-2000:]}

TASKS:
1. Analyze which personas, topics, and formats drive the most engagement and revenue.
2. Identify pipeline stages that are over budget relative to output.
3. Update aima-editorial-calendar.md if any rotations or topic shifts are warranted.
4. Write strategic decisions to CLAUDE.md (append, do not overwrite).
5. List any prompt adjustments or budget reallocation recommendations.

Return your decisions summary as JSON:
{{
  "date": "{today}",
  "calendar_changes": ["description of any changes made"],
  "decisions": ["decision 1", "decision 2", ...],
  "prompt_recommendations": {{}},
  "budget_recommendations": {{}},
  "flags": []
}}
No markdown fences.\
"""

    log.info("[iris] running strategic review")
    raw = call_cc_agent("iris", IRIS_PROMPT, user_input)

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        decisions = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        log.warning("[iris] could not parse JSON from output — using raw text")
        decisions = {
            "date": today,
            "calendar_changes": [],
            "decisions": [raw[:500]] if raw else [],
            "prompt_recommendations": {},
            "budget_recommendations": {},
            "flags": ["parse_error: JSON not found in CC output"],
        }

    log.info(f"[iris] decisions: {len(decisions.get('decisions', []))} items")
    if decisions.get("calendar_changes"):
        log.info(f"[iris] calendar changes: {decisions['calendar_changes']}")

    return decisions
