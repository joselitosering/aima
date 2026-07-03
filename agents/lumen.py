"""Lumen — Analytics Aggregator (CC subagent).

Receives Echo's LinkedIn report, collects GA4/Meta/TikTok/BMC data,
consolidates everything, and appends to optimization_report.json.
"""

import json
import re

from agents.base import call_cc_agent, read_json, write_json, append_optimization_report, log
from agents.prompts import LUMEN_PROMPT


def run(echo_report: dict) -> dict:
    """
    Aggregate cross-platform analytics and write to optimization_report.json.
    Returns the Lumen analytics entry.
    """
    # Read lumen credentials if available
    try:
        secrets = read_json("lumen_secrets.json")
    except Exception:
        secrets = {}

    user_input = f"""\
ECHO LINKEDIN REPORT:
{json.dumps(echo_report, indent=2)}

LUMEN CREDENTIALS (lumen_secrets.json):
{json.dumps(secrets, indent=2)}

Collect analytics from all platforms (GA4, Meta, TikTok, BMC).
Read ga4_traffic.csv if available.
Write per-platform CSVs and platform_summary.json.
Append your consolidated analytics entry to optimization/optimization_report.json.
Return your analytics entry as JSON (no markdown fences).\
"""

    log.info("[lumen] aggregating cross-platform analytics")
    raw = call_cc_agent("lumen", LUMEN_PROMPT, user_input)

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()

    # Extract JSON object
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        entry = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        log.warning("[lumen] could not parse JSON from output — using raw report")
        entry = {
            "source": "lumen",
            "date": echo_report.get("date", ""),
            "linkedin": echo_report,
            "flags": ["parse_error: JSON not found in CC output"],
        }

    # Ensure source field is set
    entry["source"] = "lumen"

    # CC agent may have appended to optimization_report.json directly.
    # Check for a lumen entry from today before appending again.
    existing = read_json("optimization/optimization_report.json")
    existing_entries = existing if isinstance(existing, list) else []
    already_written = any(
        e.get("source") == "lumen" and e.get("date") == entry.get("date")
        for e in existing_entries
    )
    if not already_written:
        append_optimization_report(entry)
        log.info("[lumen] appended to optimization_report.json")
    else:
        log.info("[lumen] entry already in optimization_report.json — skipping duplicate")

    return entry
