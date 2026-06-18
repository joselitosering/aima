"""
analytics_collector.py — Collects LinkedIn post statistics 48h after posting.

Reads post_log.json for pending posts, fetches engagement data from the
LinkedIn shareStatistics API, and appends results to post_analytics.csv.

Run automatically by pipeline.py, or manually: python analytics_collector.py
"""

import os, json, csv, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN           = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
COLLECTION_DELAY_HOURS = 48   # wait this long before pulling stats

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


# ── LinkedIn statistics API ───────────────────────────────────────────────────

def fetch_share_statistics(post_id):
    """
    Fetch engagement stats for a post via LinkedIn shareStatistics API.
    post_id: e.g. urn:li:share:7473451995576549376
    Returns a stats dict, or None on failure.
    """
    encoded_id = urllib.parse.quote(post_id, safe="")
    url = f"https://api.linkedin.com/v2/shareStatistics?q=shares&shares[0]={encoded_id}"

    req = urllib.request.Request(url)
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data     = json.loads(resp.read())
            elements = data.get("elements", [])
            if not elements:
                return None
            stats = elements[0].get("totalShareStatistics", {})
            return {
                "impressions":     stats.get("impressionCount", 0),
                "clicks":          stats.get("clickCount", 0),
                "likes":           stats.get("likeCount", 0),
                "comments":        stats.get("commentCount", 0),
                "shares":          stats.get("shareCount", 0),
                "engagement_rate": round(stats.get("engagement", 0.0), 4),
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"    Stats API error {e.code}: {body}")
        # 403 usually means missing r_member_social scope — log and skip
        if e.code == 403:
            print("    → Missing r_member_social OAuth scope. Re-run linkedin_auth.py to add it.")
        return None
    except Exception as e:
        print(f"    Stats fetch failed: {e}")
        return None


# ── Main collection pass ─────────────────────────────────────────────────────

def collect_pending_analytics(verbose=True):
    """
    Iterate post_log.json. For posts that are >48h old and not yet collected,
    fetch stats and append a row to post_analytics.csv.
    """
    log = load_post_log()
    if not log:
        return 0

    ensure_csv_headers()
    now      = datetime.now(timezone.utc)
    collected = 0

    for entry in log:
        if entry.get("analytics_collected"):
            continue

        try:
            posted_at = datetime.fromisoformat(entry["posted_at"]).replace(tzinfo=timezone.utc)
        except Exception:
            continue

        age_hours = (now - posted_at).total_seconds() / 3600
        if age_hours < COLLECTION_DELAY_HOURS:
            if verbose:
                remaining = COLLECTION_DELAY_HOURS - age_hours
                print(f"  Skipping '{entry['title'][:60]}' — {remaining:.1f}h until analytics ready")
            continue

        if verbose:
            print(f"  Collecting analytics: '{entry['title'][:60]}' ({age_hours:.0f}h old)")

        stats = fetch_share_statistics(entry["post_id"])
        if stats is None:
            if verbose:
                print("    No data returned — will retry next run.")
            continue

        impressions = stats["impressions"]
        clicks      = stats["clicks"]
        ctr         = round(clicks / impressions, 4) if impressions > 0 else 0.0
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
                f"    ✓ Impressions: {impressions:,} | Clicks: {clicks:,} | "
                f"Likes: {stats['likes']} | Comments: {stats['comments']} | "
                f"CTR: {ctr:.1%} | Engagement: {stats['engagement_rate']:.2%}"
            )

        entry["analytics_collected"] = True
        collected += 1

    if collected:
        save_post_log(log)
        if verbose:
            print(f"  Analytics collected for {collected} post(s). Saved to post_analytics.csv.")

    return collected


def print_summary():
    """Print a quick performance summary from post_analytics.csv."""
    if not ANALYTICS_CSV.exists():
        print("No analytics data yet.")
        return

    rows = []
    with open(ANALYTICS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("No analytics data yet.")
        return

    print(f"\n{'='*60}")
    print(f"AIMA LinkedIn Post Analytics — {len(rows)} post(s)")
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

    by_persona = {}
    for row in rows:
        p = row.get("persona", "unknown")
        if p not in by_persona:
            by_persona[p] = {"imp": [], "ctr": []}
        by_persona[p]["imp"].append(int(row.get("impressions", 0)))
        by_persona[p]["ctr"].append(float(row.get("ctr", 0)))

    print("\n  By persona:")
    for persona, data in sorted(by_persona.items()):
        avg_p_imp = sum(data["imp"]) / len(data["imp"])
        avg_p_ctr = sum(data["ctr"]) / len(data["ctr"])
        print(f"    {persona:10s}: {avg_p_imp:,.0f} avg impressions | {avg_p_ctr:.1%} avg CTR ({len(data['imp'])} posts)")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("Collecting LinkedIn post analytics...")
    n = collect_pending_analytics(verbose=True)
    print_summary()
