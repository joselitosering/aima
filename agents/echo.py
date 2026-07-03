"""Echo — LinkedIn Analytics Agent (Pure Python, no LLM calls).

Runs daily. Reads post_log.json, fetches LinkedIn post statistics
for posts where analytics_collected=false and posted_at > 48h ago,
appends rows to linkedin_analytics.csv, then reports to Lumen.
"""

import csv
import json
import os
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from agents.base import REPO_ROOT, read_json, write_json, log

load_dotenv(dotenv_path=REPO_ROOT / "linkedin_pipeline" / ".env")

LINKEDIN_API_BASE = "https://api.linkedin.com"
POST_LOG_PATH = "linkedin_pipeline/post_log.json"
ANALYTICS_CSV = "linkedin_analytics.csv"
ANALYTICS_WINDOW_HOURS = 48


def _get_token() -> str:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("[echo] LINKEDIN_ACCESS_TOKEN not set in linkedin_pipeline/.env")
    return token


def _entity_param(urn: str) -> str:
    """
    Build the Rest.li 2.0 `entity` query value memberCreatorPostAnalytics
    expects, e.g. "(share:urn%3Ali%3Ashare%3A1234567890)" for a share URN or
    "(ugc:urn%3Ali%3AugcPost%3A1234567890)" for a ugcPost URN. Only the URN's
    own colons are percent-encoded — the surrounding parens and "share:"/
    "ugc:" prefix are literal Rest.li structural syntax (per LinkedIn's own
    sample request), not something urllib.parse.quote should touch.
    """
    encoded = urn.replace(":", "%3A")
    kind = "ugc" if ":ugcPost:" in urn else "share"
    return f"({kind}:{encoded})"


# memberCreatorPostAnalytics returns exactly one metric per call — there is
# no combined "all stats in one response" mode (the old socialMediaPostStatistics
# endpoint this used to call doesn't actually exist on LinkedIn's API at all,
# which is why every request 404'd). Map our field names to LinkedIn's
# queryType values so _fetch_post_stats can make one call per metric.
_METRIC_QUERY_TYPES = {
    "impressions": "IMPRESSION",
    "clicks": "LINK_CLICKS",
    "reactions": "REACTION",
    "reposts": "RESHARE",
    "comments": "COMMENT",
}


def _fetch_metric(token: str, entity_param: str, query_type: str) -> int:
    """GET /rest/memberCreatorPostAnalytics for one post, one metric. Requires r_member_postAnalytics scope (3-legged member token)."""
    url = (
        f"{LINKEDIN_API_BASE}/rest/memberCreatorPostAnalytics"
        f"?q=entity&entity={entity_param}&queryType={query_type}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": "202401",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    elements = raw.get("elements", [])
    return int(elements[0].get("count", 0)) if elements else 0


def _fetch_post_stats(token: str, urn: str) -> dict:
    """
    Fetch impressions/clicks/reactions/reposts/comments for a single post
    URN via memberCreatorPostAnalytics (one API call per metric — see
    _METRIC_QUERY_TYPES) and compute CTR from the results.
    """
    entity_param = _entity_param(urn)
    stats = {"urn": urn}
    for field, query_type in _METRIC_QUERY_TYPES.items():
        stats[field] = _fetch_metric(token, entity_param, query_type)
    stats["ctr"] = round(stats["clicks"] / stats["impressions"], 4) if stats["impressions"] else 0.0
    return stats


def _append_to_csv(row: dict):
    """Append a stats row to linkedin_analytics.csv."""
    csv_path = REPO_ROOT / ANALYTICS_CSV
    fieldnames = [
        "date", "slug", "urn", "impressions", "clicks",
        "reactions", "reposts", "comments", "ctr",
    ]
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def _is_eligible(entry: dict) -> bool:
    """True if post is uncollected and > 48h old."""
    if entry.get("analytics_collected", False):
        return False
    posted_at = entry.get("posted_at", "")
    if not posted_at:
        return False
    try:
        posted_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    # posted_at is written by nova.py / force_repost.py as
    # datetime.now(timezone.utc).strftime(...) — real UTC, but strftime
    # strips the offset, so fromisoformat parses it back as naive. Attach
    # UTC explicitly (same fix already applied in
    # linkedin_pipeline/analytics_collector.py) or the comparison below
    # raises "can't compare offset-naive and offset-aware datetimes".
    if posted_dt.tzinfo is None:
        posted_dt = posted_dt.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ANALYTICS_WINDOW_HOURS)
    return posted_dt < cutoff


def run() -> dict:
    """
    Collect LinkedIn stats for eligible posts.
    Returns an Echo report dict for Lumen.
    """
    token = _get_token()
    post_log = read_json(POST_LOG_PATH)
    entries = post_log if isinstance(post_log, list) else []

    eligible = [e for e in entries if _is_eligible(e)]
    log.info(f"[echo] {len(eligible)} post(s) eligible for analytics collection")

    collected = []
    today = datetime.now(timezone.utc).date().isoformat()

    for entry in eligible:
        urn = entry.get("urn") or entry.get("company_urn") or entry.get("post_id", "")
        slug = entry.get("slug") or entry.get("article", "")
        if not urn:
            log.warning(f"[echo] entry missing URN: {entry}")
            continue

        try:
            stats = _fetch_post_stats(token, urn)
        except Exception as exc:
            log.warning(f"[echo] API error for {urn}: {exc} — skipping")
            # Fallback: attempt xls_import if available
            try:
                import importlib.util
                spec_path = REPO_ROOT / "linkedin_pipeline" / "xls_import.py"
                if spec_path.exists():
                    subprocess.run(
                        ["python", "linkedin_pipeline/xls_import.py"],
                        cwd=REPO_ROOT, check=False,
                    )
            except Exception:
                pass
            continue

        row = {
            "date": today,
            "slug": slug,
            **stats,
        }
        _append_to_csv(row)
        entry["analytics_collected"] = True
        collected.append(stats)
        log.info(f"[echo] collected: {slug} — impressions={stats['impressions']} ctr={stats['ctr']}")

    # Persist updated post_log
    write_json(POST_LOG_PATH, entries)

    # Push post_log.json update (Echo is a daily runner, not the article pipeline)
    try:
        subprocess.run(
            ["git", "add", "linkedin_pipeline/post_log.json"],
            cwd=REPO_ROOT, check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"echo: mark analytics_collected {today}"],
            cwd=REPO_ROOT, check=True,
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=REPO_ROOT, check=True,
        )
    except subprocess.CalledProcessError as exc:
        log.warning(f"[echo] git push skipped: {exc}")

    # Build Lumen report
    avg_impressions = (
        int(sum(s["impressions"] for s in collected) / len(collected))
        if collected else 0
    )
    avg_ctr = (
        f"{round(sum(s['ctr'] for s in collected) / len(collected) * 100, 1)}%"
        if collected else "0%"
    )
    top = max(collected, key=lambda s: s["impressions"]) if collected else {}

    report = {
        "date": today,
        "platform": "linkedin",
        "posts_collected": len(collected),
        "avg_impressions": avg_impressions,
        "avg_ctr": avg_ctr,
        "top_post": {"urn": top.get("urn", ""), "impressions": top.get("impressions", 0)},
        "flags": [],
    }
    log.info(f"[echo] report: {report}")
    return report
