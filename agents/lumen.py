"""Lumen — Analytics Aggregator (CC subagent).

Receives Echo's LinkedIn report, collects GA4/Meta/TikTok/BMC data,
consolidates everything, and appends to optimization_report.json.
"""

import json
import re
from datetime import date

from agents.base import (
    REPO_ROOT, call_cc_agent, read_json, write_json,
    append_optimization_report, log,
)
from agents.prompts import build_lumen_prompt

NO_SECRETS_FLAG = "meta/tiktok/bmc: skipped, no lumen_secrets.json"


def _existing_lumen_entry(report_date: str) -> dict | None:
    """Return today's already-written lumen entry, or None if none exists."""
    existing = read_json("optimization/optimization_report.json")
    entries = existing if isinstance(existing, list) else []
    for e in entries:
        if e.get("source") == "lumen" and e.get("date") == report_date:
            return e
    return None


def run(echo_report: dict, force: bool = False) -> dict:
    """
    Aggregate cross-platform analytics and write to optimization_report.json.
    Returns the Lumen analytics entry.

    force=True bypasses the per-day dedup for an on-demand intra-day refresh:
    it runs the (paid) CC call even if today's entry exists and REPLACES that
    entry with the fresh result, so data display reflects the latest gather.
    """
    report_date = echo_report.get("date") or date.today().isoformat()

    # ── DEDUP BEFORE the paid CC call ────────────────────────────────
    # call_cc_agent is subscription-billed. If a lumen entry for today is
    # already in the report, re-running would pay for the full call again
    # and discard the result. Short-circuit here — no CC call — unless the
    # caller explicitly forces an intra-day refresh.
    already = _existing_lumen_entry(report_date)
    if already is not None and not force:
        log.info(f"[lumen] entry already exists for {report_date} — skipping CC call")
        return already
    if already is not None and force:
        log.info(f"[lumen] entry exists for {report_date} but --force set — refreshing")

    # Credentials gate: with no lumen_secrets.json we can't authenticate
    # Meta/TikTok/BMC, so run the reduced GA4 + LinkedIn prompt on a cheaper
    # model instead of paying Sonnet to rediscover it can't auth, every run.
    has_secrets = (REPO_ROOT / "lumen_secrets.json").exists()
    secrets = read_json("lumen_secrets.json") if has_secrets else {}
    prompt = build_lumen_prompt(has_secrets)
    # No-secrets path is mechanical (read CSVs → totals → fixed-schema JSON):
    # Haiku is sufficient. Full multi-platform synthesis stays on CC default.
    model = None if has_secrets else "claude-haiku-4-5"

    if has_secrets:
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
    else:
        user_input = f"""\
ECHO LINKEDIN REPORT:
{json.dumps(echo_report, indent=2)}

NO lumen_secrets.json — Meta / TikTok / BMC are UNAVAILABLE this run.
Collect GA4 only: read ga4_traffic.csv if available.
Write ga4_analytics.csv and platform_summary.json (GA4 columns only — the
dashboard reads platform_summary.json, so write it even with GA4 alone).
Append your consolidated analytics entry to optimization/optimization_report.json,
marking meta/tiktok/bmc as skipped with reason "{NO_SECRETS_FLAG}".
Return your analytics entry as JSON (no markdown fences).\
"""

    log.info(
        f"[lumen] aggregating analytics for {report_date} "
        f"(secrets={'yes' if has_secrets else 'no'}, model={model or 'CC-default'})"
    )
    raw = call_cc_agent("lumen", prompt, user_input, model_override=model)

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
            "date": report_date,
            "linkedin": echo_report,
            "flags": ["parse_error: JSON not found in CC output"],
        }

    # Ensure source + date fields are set (date drives the dedup check).
    entry["source"] = "lumen"
    entry.setdefault("date", report_date)

    # Fiduciary trace: on the no-secrets path the report must still say the
    # three uncredentialed platforms were skipped, even if the agent's JSON
    # omitted the flag. Never silently drop them.
    if not has_secrets:
        flags = entry.setdefault("flags", [])
        if not any("lumen_secrets.json" in str(f) for f in flags):
            flags.append(NO_SECRETS_FLAG)

    # Write the entry back to optimization_report.json.
    existing = read_json("optimization/optimization_report.json")
    existing_entries = existing if isinstance(existing, list) else []
    same_day = {report_date, entry.get("date")}

    if force:
        # Intra-day refresh: drop any same-day lumen entry (including one the
        # CC agent may have appended directly) and replace with this result,
        # so the report/display shows the latest gather — not a stale duplicate.
        filtered = [
            e for e in existing_entries
            if not (e.get("source") == "lumen" and e.get("date") in same_day)
        ]
        filtered.append(entry)
        write_json("optimization/optimization_report.json", filtered)
        log.info("[lumen] replaced today's entry in optimization_report.json (force)")
    else:
        # CC agent may have appended to optimization_report.json directly.
        # Check for a lumen entry from today before appending again.
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
