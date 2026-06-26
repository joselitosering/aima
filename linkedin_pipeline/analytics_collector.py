"""
analytics_collector.py — Collects LinkedIn post statistics 48h after posting.

Reads post_log.json for pending posts, fetches engagement data from the
LinkedIn organizationalEntityShareStatistics API (company page), and appends
results to post_analytics.csv.

Requires scopes: rw_organization_admin, r_organization_social
Run automatically by pipeline.py, or manually: python analytics_collector.py
"""

import os, json, csv, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN           = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
ORG_ID                 = os.getenv("LINKEDIN_ORG_ID", "").strip()
COLLECTION_DELAY_HOURS = 48   # wait this long before pulling stats
LINKEDIN_VERSION       = "202506"   # bump quarterly

POST_LOG      = Path(__file__).parent / "post_log.json"
ANALYTICS_CSV = Path(__file__).parent / "post_analytics.csv"

CSV_HEADERS = [
    "post_id", "article", "title", "persona", "posted_at",
    "collected_at", "impressions", "clicks", "likes", "comments",
    "shares", "engagement_rate", "ctr",
]


# ── File helpers ─────────────────────────────────────────────────────────────

def load_post_log():
    if POST_LOG.exists():
        with open(POST_LOG, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_post_log(log):
    with open(POST_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def ensure_csv_headers():
    if not ANALYTICS_CSV.exists():
        with open(ANALYTICS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADERS)


# ── LinkedIn Organization Share Statistics API ────────────────────────────────

_ORG_STATS_CACHE = None  # loaded once per run

def _load_all_org_stats():
    """
    Fetch ALL organizationalEntityShareStatistics for the company page in one pass
    (paginated). Returns dict keyed by share/ugcPost URN -> stats dict.
    LinkedIn does not support per-share filtering via shares[0] on this endpoint.
    """
    global _ORG_STATS_CACHE
    if _ORG_STATS_CACHE is not None:
        return _ORG_STATS_CACHE

    if not ORG_ID:
        print("    ERROR: LINKEDIN_ORG_ID not set in .env")
        _ORG_STATS_CACHE = {}
        return _ORG_STATS_CACHE

    org_urn = f"urn:li:organization:{ORG_ID}"
    result  = {}
    start   = 0
    count   = 50

    while True:
        params = urllib.parse.urlencode({
            "q":                    "organizationalEntity",
            "organizationalEntity": org_urn,
            "count":                count,
            "start":                start,
        })
        url = f"https://api.linkedin.com/rest/organizationalEntityShareStatistics?{params}"
        req = urllib.request.Request(url)
        req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
        req.add_header("LinkedIn-Version",          LINKEDIN_VERSION)
        req.add_header("X-Restli-Protocol-Version", "2.0.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data     = json.loads(resp.read())
                elements = data.get("elements", [])
                for el in elements:
                    urn   = el.get("share") or el.get("ugcPost") or ""
                    stats = el.get("totalShareStatistics", {})
                    imp   = stats.get("impressionCount", 0)
                    clk   = stats.get("clickCount", 0)
                    result[urn] = {
                        "impressions":     imp,
                        "clicks":          clk,
                        "likes":           stats.get("likeCount", 0),
                        "comments":        stats.get("commentCount", 0),
                        "shares":          stats.get("shareCount", 0),
                        "engagement_rate": round(stats.get("engagement", 0.0), 4),
                        "unique_impressions": stats.get("uniqueImpressionsCount", 0),
                    }
                paging = data.get("paging", {})
                total  = paging.get("total", 0)
                if start + count >= total or not elements:
                    break
                start += count
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"    Org stats fetch error {e.code}: {body[:300]}")
            break
        except Exception as e:
            print(f"    Org stats fetch failed: {e}")
            break

    _ORG_STATS_CACHE = result
    print(f"  Org stats loaded: {len(result)} posts found on company page")
    if result:
        for urn in list(result.keys())[:3]:
            print(f"    Sample URN: {urn}")
    return result


def fetch_org_share_statistics(post_id):
    """
    Per-post stats via socialMediaPostStatistics.
    Requires r_member_social scope — not yet approved.
    Returns None (skips gracefully) until that scope is available.
    Use xls_import.py to import data from LinkedIn Analytics XLS export instead.
    """
    # r_member_social not approved yet — skip API call to avoid noise
    print(f"    API analytics not available (r_member_social pending). Use xls_import.py.")
    return None


def _fetch_org_share_statistics_UNUSED(post_id):
    """KEPT FOR REFERENCE — shares[0] param not supported by LinkedIn REST API."""
    if not ORG_ID:
        print("    ERROR: LINKEDIN_ORG_ID not set in .env")
        return None

    org_urn   = f"urn:li:organization:{ORG_ID}"
    share_urn = post_id

    params = urllib.parse.urlencode({
        "q":                    "organizationalEntity",
        "organizationalEntity": org_urn,
        "shares[0]":            share_urn,
    })
    url = f"https://api.linkedin.com/rest/organizationalEntityShareStatistics?{params}"

    req = urllib.request.Request(url)
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("LinkedIn-Version",          LINKEDIN_VERSION)
    req.add_header("X-Restli-Protocol-Version", "2.0.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data     = json.loads(resp.read())
            elements = data.get("elements", [])
            if not elements:
                return None
            stats = elements[0].get("totalShareStatistics", {})
            impressions = stats.get("impressionCount", 0)
            clicks      = stats.get("clickCount", 0)
            return {
                "impressions":     impressions,
                "clicks":          clicks,
                "likes":           stats.get("likeCount", 0),
                "comments":        stats.get("commentCount", 0),
                "shares":          stats.get("shareCount", 0),
                "engagement_rate": round(stats.get("engagement", 0.0), 4),
                "unique_impressions": stats.get("uniqueImpressionsCount", 0),
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"    Stats API error {e.code}: {body[:300]}")
        if e.code == 403:
            print(
                "    403 Forbidden — token may be missing 'rw_organization_admin' scope.\n"
                "    Re-run linkedin_auth.py to get a new token with org scopes."
            )
        elif e.code == 404:
            print("    404 — share URN not found on org page. Post may have been made from personal profile.")
        return None
    except Exception as e:
        print(f"    Stats fetch failed: {e}")
        return None


# ── Main collection pass ─────────────────────────────────────────────────────

def collect_pending_analytics(verbose=True):
    """
    Iterate post_log.json. For posts >48h old and not yet collected,
    fetch org share stats and append a row to post_analytics.csv.
    """
    log = load_post_log()
    if not log:
        return 0

    ensure_csv_headers()
    now       = datetime.now(timezone.utc)
    collected = 0

    # Load ALL org stats once (one API call covers every post on the company page)
    org_stats = _load_all_org_stats()
    if verbose:
        if org_stats:
            print(f"  Org stats loaded: {len(org_stats)} posts on company page")
        else:
            print("  Org stats: 0 posts returned (check token/scopes)")

    for entry in log:
        if entry.get("analytics_collected"):
            continue

        try:
            posted_at = datetime.fromisoformat(entry["posted_at"]).replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if not entry.get("post_id"):
            if verbose:
                print(f"  Skipping '{entry.get('title','')[:60]}' — no post_id yet")
            continue

        age_hours = (now - posted_at).total_seconds() / 3600
        if age_hours < COLLECTION_DELAY_HOURS:
            if verbose:
                remaining = COLLECTION_DELAY_HOURS - age_hours
                print(f"  Skipping '{entry['title'][:60]}' — {remaining:.1f}h until analytics ready")
            continue

        if verbose:
            print(f"  Collecting analytics: '{entry['title'][:60]}' ({age_hours:.0f}h old)")

        # Look up this post's URN in the org stats cache
        post_id = entry.get("post_id", "")
        stats = org_stats.get(post_id)
        if stats is None:
            if verbose:
                print(f"    URN not in org stats: {post_id}")
                print("    Post may be from personal profile. Use xls_import.py for personal posts.")
            continue

        impressions  = stats["impressions"]
        clicks       = stats["clicks"]
        ctr          = round(clicks / impressions, 4) if impressions > 0 else 0.0
        collected_at = now.strftime("%Y-%m-%dT%H:%M:%S")

        row = [
            entry["post_id"],
            entry.get("article", ""),
            entry.get("title", ""),
            entry.get("persona", ""),
            entry.get("posted_at", ""),
            collected_at,
            impressions,
            clicks,
            stats["likes"],
            stats["comments"],
            stats["shares"],
            stats["engagement_rate"],
            ctr,
        ]

        with open(ANALYTICS_CSV, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

        if verbose:
            print(
                f"    Impressions: {impressions:,} | Clicks: {clicks:,} | "
                f"Likes: {stats['likes']} | Comments: {stats['comments']} | "
                f"Shares: {stats['shares']} | CTR: {ctr:.1%} | Eng: {stats['engagement_rate']:.2%}"
            )

        entry["analytics_collected"] = True
        collected += 1

    if collected:
        save_post_log(log)
        if verbose:
            print(f"  Analytics collected for {collected} post(s). Saved to post_analytics.csv.")
        _git_push_data()

    return collected


def _git_push_data():
    """Commit and push post_log.json + post_analytics.csv to GitHub Pages."""
    import subprocess
    repo_root = Path(__file__).parent.parent
    files = [
        str(Path(__file__).parent / "post_log.json"),
        str(Path(__file__).parent / "post_analytics.csv"),
    ]
    try:
        subprocess.run(["git", "add"] + files, cwd=repo_root, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo_root, capture_output=True
        )
        if result.returncode == 0:
            return  # nothing staged
        subprocess.run(
            ["git", "commit", "-m", "data: update analytics"],
            cwd=repo_root, check=True, capture_output=True
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True, capture_output=True)
        print("  git push OK: analytics data updated on GitHub")
    except Exception as e:
        print(f"  git push failed (non-fatal): {e}")


def print_summary():
    """Print a quick performance summary from post_analytics.csv."""
    if not ANALYTICS_CSV.exists():
        print("No analytics data yet.")
        return

    rows = []
    with open(ANALYTICS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No analytics data yet.")
        return

    print(f"\n{'='*60}")
    print(f"AIMA LinkedIn Post Analytics -- {len(rows)} post(s)")
    print(f"{'='*60}")

    for row in rows:
        imp = int(row.get("impressions", 0))
        clk = int(row.get("clicks", 0))
        ctr = float(row.get("ctr", 0))
        eng = float(row.get("engagement_rate", 0))
        print(
            f"  [{row.get('persona','?'):8s}] {row.get('title','')[:50]:50s} | "
            f"Imp: {imp:>6,} | Clicks: {clk:>4} | CTR: {ctr:.1%} | Eng: {eng:.2%}"
        )

    avg_ctr = sum(float(r.get("ctr", 0)) for r in rows) / len(rows)
    avg_imp = sum(int(r.get("impressions", 0)) for r in rows) / len(rows)
    print(f"\n  Averages: {avg_imp:,.0f} impressions | {avg_ctr:.1%} CTR")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("Collecting LinkedIn post analytics (AIMA company page)...")
    n = collect_pending_analytics(verbose=True)
    print_summary()
