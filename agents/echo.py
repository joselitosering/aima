"""Echo — LinkedIn Analytics Agent (Pure Python, no LLM calls).

Runs daily. Reads post_log.json, fetches LinkedIn post statistics
for posts where analytics_collected=false and posted_at > 48h ago,
appends rows to linkedin_pipeline/post_analytics.csv, then reports to Lumen.

CANONICAL ANALYTICS FILE (settled 2026-07-28): every producer and consumer of
LinkedIn post metrics uses `linkedin_pipeline/post_analytics.csv`. Echo used to
write its own `linkedin_analytics.csv` at the repo root in a different, narrower
column schema — a file nothing ever read (Lumen's run_lumen_batch._linkedin_report,
marco._category_priority, xls_import.py and the article-manager dashboard all read
post_analytics.csv). Echo now writes the same 13-column schema as xls_import.py so
API-collected and XLS-imported rows are interchangeable in one file.

SCOPE GAP (open, external): the memberCreatorPostAnalytics endpoint below needs the
`r_member_postAnalytics` OAuth scope, which this app does not have — it sits behind
LinkedIn's Community Management API Technical Sign-Off. Until that is granted, every
fetch here fails with 401/403 and the only working path is the manual XLS export →
`python linkedin_pipeline/xls_import.py <export.xlsx>`. Echo detects that condition
and says so once, rather than hammering the API post by post.
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
ANALYTICS_CSV = "linkedin_pipeline/post_analytics.csv"
ANALYTICS_WINDOW_HOURS = 48

# Canonical column order — must stay identical to xls_import.py's CSV_HEADERS and
# analytics_collector.py's CSV_HEADERS. The dashboard reads `persona`,
# `engagement_rate` and `collected_at`; marco._category_priority() keys off
# `article`. Changing this list means changing all four readers.
CSV_HEADERS = [
    "post_id", "article", "title", "persona", "posted_at",
    "collected_at", "impressions", "clicks", "likes", "comments",
    "shares", "engagement_rate", "ctr",
]

# One-line operator instruction printed whenever posts are stuck uncollected.
XLS_FALLBACK_HINT = (
    "export LinkedIn Analytics XLS and run: "
    "python linkedin_pipeline/xls_import.py <path-to-export.xlsx>"
)


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
            "LinkedIn-Version": "202607",
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


def _build_csv_row(entry: dict, stats: dict, collected_at: str) -> dict:
    """
    Map one post_log entry + one API stats dict onto the canonical
    post_analytics.csv schema. LinkedIn's metric names differ from the CSV's
    (REACTION -> likes, RESHARE -> shares), and engagement_rate is not returned
    by the API at all — it is derived the same way xls_import.py stores it
    (a 0-1 decimal, not a percentage).
    """
    impressions = stats.get("impressions", 0)
    likes = stats.get("reactions", 0)
    comments = stats.get("comments", 0)
    shares = stats.get("reposts", 0)
    engagement_rate = (
        round((likes + comments + shares) / impressions, 4) if impressions else 0.0
    )
    return {
        "post_id": stats.get("urn", ""),
        "article": entry.get("article", ""),
        "title": entry.get("title", ""),
        "persona": entry.get("persona", ""),
        "posted_at": entry.get("posted_at", ""),
        "collected_at": collected_at,
        "impressions": impressions,
        "clicks": stats.get("clicks", 0),
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "engagement_rate": engagement_rate,
        "ctr": stats.get("ctr", 0.0),
    }


def _append_to_csv(row: dict):
    """Append a stats row to the canonical linkedin_pipeline/post_analytics.csv."""
    csv_path = REPO_ROOT / ANALYTICS_CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS, extrasaction="ignore")
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
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    scope_blocked = False

    for entry in eligible:
        urn = entry.get("urn") or entry.get("company_urn") or entry.get("post_id", "")
        slug = entry.get("slug") or entry.get("article", "")
        if not urn:
            log.warning(f"[echo] entry missing URN: {entry}")
            continue

        try:
            stats = _fetch_post_stats(token, urn)
        except urllib.error.HTTPError as exc:
            # 401/403 is the scope gate, not a per-post problem: the token simply
            # lacks r_member_postAnalytics, so every remaining post would fail the
            # same way (5 API calls each). Stop the loop on the first one instead
            # of hammering LinkedIn 5x per uncollected post.
            if exc.code in (401, 403):
                scope_blocked = True
                log.warning(
                    f"[echo] LinkedIn returned HTTP {exc.code} for {urn} — the access "
                    "token lacks the 'r_member_postAnalytics' scope, so API collection "
                    "cannot work for ANY post. Halting API collection for this run."
                )
                break
            log.warning(f"[echo] API error for {urn}: HTTP {exc.code} — skipping")
            continue
        except Exception as exc:
            log.warning(f"[echo] API error for {urn}: {exc} — skipping")
            continue

        _append_to_csv(_build_csv_row(entry, stats, collected_at))
        entry["analytics_collected"] = True
        collected.append(stats)
        log.info(f"[echo] collected: {slug} — impressions={stats['impressions']} ctr={stats['ctr']}")

    # Persist updated post_log (only meaningful if something was actually collected)
    if collected:
        write_json(POST_LOG_PATH, entries)

    # The XLS import is a human-in-the-loop action — LinkedIn has no pull API for the
    # analytics export without the missing scope, so there is nothing to auto-invoke
    # here. (Echo used to shell out to `python linkedin_pipeline/xls_import.py` with no
    # arguments on every failure; xls_import requires a positional xls_file, so that
    # call always exited 2 and did nothing.) Tell the operator once instead.
    uncollected = sum(1 for e in entries if not e.get("analytics_collected", False))
    if uncollected:
        reason = (
            "LinkedIn API blocked (missing 'r_member_postAnalytics' scope, pending "
            "LinkedIn Community Management approval)"
            if scope_blocked else
            "not collected via API"
        )
        log.warning(
            f"[echo] {uncollected} post(s) awaiting analytics — {reason}. "
            f"To import them manually: {XLS_FALLBACK_HINT}"
        )

    # Push post_log.json + post_analytics.csv (Echo is a daily runner, not the
    # article pipeline). Skipped entirely when nothing was collected — there is no
    # change to commit, and a no-op commit just raises and logs noise.
    if collected:
        try:
            subprocess.run(
                ["git", "add", "linkedin_pipeline/post_log.json", ANALYTICS_CSV],
                cwd=REPO_ROOT, check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"echo: LinkedIn analytics {today}"],
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

    flags = []
    if scope_blocked:
        flags.append(
            "linkedin_api_scope_missing: r_member_postAnalytics not granted to this app "
            "(Community Management Technical Sign-Off pending) — API collection impossible; "
            f"manual path: {XLS_FALLBACK_HINT}"
        )

    report = {
        "date": today,
        "platform": "linkedin",
        "source": ANALYTICS_CSV,
        "posts_collected": len(collected),
        "posts_awaiting_analytics": uncollected,
        "avg_impressions": avg_impressions,
        "avg_ctr": avg_ctr,
        "top_post": {"urn": top.get("urn", ""), "impressions": top.get("impressions", 0)},
        "flags": flags,
    }
    log.info(f"[echo] report: {report}")
    return report
