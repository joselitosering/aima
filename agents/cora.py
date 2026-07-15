"""Cora — Token & Quality Governor (CC subagent).

Called by Marco after each pipeline run. Analyzes token usage,
checks for hallucinations in the article, and flags reversions.
Appends governance report to optimization_report.json.
"""

import json
import re
from datetime import date

from agents.base import call_cc_agent, read_json, write_json, append_optimization_report, log
from agents.prompts import CORA_PROMPT
from agents.config import BUDGET_MAP


def prepare_quill_call(spec: dict) -> dict:
    """
    Enforce the hard word-count ceiling before Marco hands off to Quill.
    Returns a dict with extra_instruction to inject into Quill's user_input.
    Called by Marco — not Quill itself.
    """
    ceiling = 1800
    target = spec.get("target_words", 1600)
    clamped = min(target, ceiling)

    return {
        "target_words": clamped,
        "ceiling": ceiling,
        "extra_instruction": (
            f"Write exactly {clamped} words (±50). "
            f"Hard ceiling: {ceiling} words — stop when the idea is complete. "
            "Do NOT pad to hit a number."
        ),
    }


def init_budget(article_number: int) -> dict:
    """
    Write the initial token_budget.json for a new pipeline run.
    Called by Marco at the start of each run — and again right after Priya
    returns, in case Priya's CC call revised the article number.

    Idempotent as of 2026-07-04: if token_budget.json already exists for
    this exact run_date + article_number, it is returned unchanged instead
    of being zeroed out. Before this fix, a resumed/retried run (e.g.
    crashing at Quill and re-running python run.py the same day) would call
    init_budget() again and silently wipe out any usage the earlier stages
    (Priya, Scout, Writer) had just recorded for the SAME article — which
    also means Marco must call this before Priya's own CC call now, not
    only after, so Priya's usage has somewhere real to land.
    """
    today = date.today().isoformat()
    existing = read_json("token_budget.json")
    # Preserve only if SAME date AND SAME article — a new article always gets a clean slate.
    # Different article on same day (e.g. two articles in one day) must reset used/cost.
    # Same article same day (crash-retry) preserves usage already recorded.
    if existing.get("run_date") == today and existing.get("article_number") == article_number:
        log.info(f"[cora] token_budget.json already initialized for #{article_number} today — preserving usage")
        return existing
    # New article or new day — zero out used/cost for all agents, keep budgets from BUDGET_MAP.
    log.info(f"[cora] resetting token_budget.json for #{article_number} ({today})")

    budget = {
        "run_date": today,
        "article_number": article_number,
        "agents": {
            "IR":  {"budget": BUDGET_MAP["iris"],        "used": 0, "status": "idle"},
            "PR":  {"budget": BUDGET_MAP["priya"],       "used": 0, "status": "idle"},
            "SC":  {"budget": BUDGET_MAP["scout"],       "used": 0, "status": "idle"},
            "TS":  {"budget": BUDGET_MAP["trend_scout"], "used": 0, "status": "idle"},
            "WR":  {"budget": BUDGET_MAP["writer"],      "used": 0, "status": "idle"},
            "QL":  {"budget": BUDGET_MAP["quill"],       "used": 0, "status": "idle"},
            "MY":  {"budget": BUDGET_MAP["maya"],        "used": 0, "status": "idle"},
            "VR":  {"budget": BUDGET_MAP["vera"],        "used": 0, "status": "idle"},
            "PT":  {"budget": 0,                          "used": 0, "status": "idle"},
            "NV":  {"budget": 0,                          "used": 0, "status": "idle"},
            "EC":  {"budget": 0,                          "used": 0, "status": "idle"},
            "LM":  {"budget": BUDGET_MAP["lumen"],       "used": 0, "status": "idle"},
            "CO":  {"budget": BUDGET_MAP["cora"],        "used": 0, "status": "idle"},
            "MR":  {"budget": 0,                          "used": 0, "status": "idle"},
        },
    }
    write_json("token_budget.json", budget)
    return budget


def run(spec: dict, article_path: str, run_summary: dict) -> dict:
    """
    Analyze token usage, check article for hallucinations,
    and write governance report to optimization_report.json.

    spec         — article spec dict from Priya
    article_path — path to final merged article HTML
    run_summary  — dict with stages, flags, revisions from Marco
    """
    from agents.base import read_file

    try:
        article_html = read_file(article_path)
    except FileNotFoundError:
        article_html = "[Article file not found]"

    try:
        research = read_json(f"articles/research/{spec['slug']}-research.json")
    except Exception:
        research = {}

    budget = read_json("token_budget.json")
    today = date.today().isoformat()

    user_input = f"""\
TODAY: {today}
ARTICLE: #{spec.get('number')} — {spec.get('title')}
SLUG: {spec.get('slug')}

TOKEN BUDGET (token_budget.json):
{json.dumps(budget, indent=2)}

RUN SUMMARY FROM MARCO:
{json.dumps(run_summary, indent=2)}

RESEARCH JSON (used to verify article claims):
{json.dumps(research, indent=2)}

ARTICLE HTML (for hallucination check — first 8000 chars):
{article_html[:8000]}

TASKS:
1. Review token usage vs budget. Flag any agent that exceeded 80%.
2. Check article stats against research JSON — flag any stat without a named source+year.
3. Check for quotes without named, verifiable individuals.
4. Check for scope violations (e.g., Quill editing images, Maya editing copy).
5. Do NOT write, read, or touch any file — Marco saves your report. Return ONLY the JSON below.

Return your governance report as JSON:
{{
  "source": "cora",
  "date": "{today}",
  "total_tokens_used": N,
  "by_agent": {{ "SC": N, "QL": N, "MY": N }},
  "hallucination_flags": [],
  "reversion_flags": [],
  "budget_alerts": [],
  "guardrails_applied": []
}}
No markdown fences.\
"""

    log.info(f"[cora] running governance check: article #{spec.get('number')}")
    raw = call_cc_agent("cora", CORA_PROMPT, user_input, single_shot=True)

    # Strip markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        entry = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        log.warning("[cora] could not parse JSON from output")
        entry = {
            "source": "cora",
            "date": today,
            "total_tokens_used": 0,
            "by_agent": {},
            "hallucination_flags": [],
            "reversion_flags": [],
            "budget_alerts": [],
            "guardrails_applied": ["parse_error: JSON not found in CC output"],
        }

    entry["source"] = "cora"

    # Append to optimization_report.json
    append_optimization_report(entry)
    log.info(f"[cora] governance report appended — flags: {entry.get('hallucination_flags', [])}")

    # Alert Marco if hallucinations detected
    if entry.get("hallucination_flags"):
        log.warning(f"[cora] HALLUCINATION FLAGS: {entry['hallucination_flags']}")
    if entry.get("budget_alerts"):
        log.warning(f"[cora] BUDGET ALERTS: {entry['budget_alerts']}")

    return entry
