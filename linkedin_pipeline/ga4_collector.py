"""
ga4_collector.py — Pull per-article traffic from Google Analytics 4.

Queries the GA4 Data API for the last 90 days of sessions, pageviews,
and LinkedIn referral traffic per article URL. Writes ga4_traffic.csv
and pushes to GitHub so the dashboard auto-fetches it.

Run manually:  python ga4_collector.py
Also called by pipeline.py on each run.

Requires:
  pip install google-analytics-data
  GA4_PROPERTY_ID and GA4_CREDENTIALS_JSON in .env
"""

import os, csv, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROPERTY_ID   = os.getenv("GA4_PROPERTY_ID", "").strip()
CREDENTIALS   = os.getenv("GA4_CREDENTIALS_JSON", "").strip()
BASE          = Path(__file__).parent
GA4_CSV       = BASE / "ga4_traffic.csv"

CSV_HEADERS = [
    "article_slug", "page_path", "sessions", "pageviews",
    "engaged_sessions", "avg_engagement_seconds",
    "linkedin_sessions", "linkedin_pageviews",
    "collected_at",
]


def collect(days=90, verbose=True):
    if not PROPERTY_ID:
        print("GA4_PROPERTY_ID not set in .env — skipping GA4 collection.")
        return 0
    if not CREDENTIALS or not Path(CREDENTIALS).exists():
        print(f"GA4_CREDENTIALS_JSON not found: {CREDENTIALS}")
        return 0

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Dimension, Metric, DateRange, FilterExpression,
            Filter, FilterExpressionList,
        )
        from google.oauth2 import service_account
    except ImportError:
        print("Missing: pip install google-analytics-data google-auth")
        return 0

    creds  = service_account.Credentials.from_service_account_file(
        CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=creds)

    date_range = DateRange(start_date=f"{days}daysAgo", end_date="today")

    # ── Query 1: all article traffic ────────────────────────────────────────
    req_all = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="engagedSessions"),
            Metric(name="userEngagementDuration"),
        ],
        date_ranges=[date_range],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.CONTAINS,
                    value="/articles/aima-article-",
                ),
            )
        ),
        limit=200,
    )

    # ── Query 2: LinkedIn referral traffic per article ───────────────────────
    req_li = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
        ],
        date_ranges=[date_range],
        dimension_filter=FilterExpression(
            and_group=FilterExpressionList(
                expressions=[
                    FilterExpression(
                        filter=Filter(
                            field_name="pagePath",
                            string_filter=Filter.StringFilter(
                                match_type=Filter.StringFilter.MatchType.CONTAINS,
                                value="/articles/aima-article-",
                            ),
                        )
                    ),
                    FilterExpression(
                        filter=Filter(
                            field_name="sessionSource",
                            string_filter=Filter.StringFilter(
                                match_type=Filter.StringFilter.MatchType.CONTAINS,
                                value="linkedin",
                            ),
                        )
                    ),
                ]
            )
        ),
        limit=200,
    )

    if verbose:
        print(f"Querying GA4 property {PROPERTY_ID} (last {days} days)...")

    resp_all = client.run_report(req_all)
    resp_li  = client.run_report(req_li)

    # Build LinkedIn lookup by page path
    li_lookup = {}
    for row in resp_li.rows:
        path = row.dimension_values[0].value
        li_lookup[path] = {
            "sessions":  int(row.metric_values[0].value or 0),
            "pageviews": int(row.metric_values[1].value or 0),
        }

    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    rows = []

    for row in resp_all.rows:
        path     = row.dimension_values[0].value
        sessions = int(row.metric_values[0].value or 0)
        views    = int(row.metric_values[1].value or 0)
        engaged  = int(row.metric_values[2].value or 0)
        eng_secs = round(float(row.metric_values[3].value or 0) / max(sessions, 1), 1)

        # Extract article slug from path
        slug = path.split("/")[-1].replace(".html", "")

        li = li_lookup.get(path, {"sessions": 0, "pageviews": 0})

        rows.append({
            "article_slug":           slug,
            "page_path":              path,
            "sessions":               sessions,
            "pageviews":              views,
            "engaged_sessions":       engaged,
            "avg_engagement_seconds": eng_secs,
            "linkedin_sessions":      li["sessions"],
            "linkedin_pageviews":     li["pageviews"],
            "collected_at":           collected_at,
        })

        if verbose:
            print(
                f"  {slug[:50]:50s} | "
                f"Sessions:{sessions:>5} Views:{views:>5} "
                f"LI:{li['sessions']:>4}"
            )

    # Write CSV
    with open(GA4_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        w.writeheader()
        w.writerows(rows)

    if verbose:
        print(f"\n✓ {len(rows)} articles written to ga4_traffic.csv")

    _git_push()
    return len(rows)


def _git_push():
    repo_root = BASE.parent
    try:
        subprocess.run(["git", "add", str(GA4_CSV)],
                       cwd=repo_root, check=True, capture_output=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"],
                              cwd=repo_root, capture_output=True)
        if diff.returncode == 0:
            return
        subprocess.run(["git", "commit", "-m", "data: update GA4 traffic"],
                       cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"],
                       cwd=repo_root, check=True, capture_output=True)
        print("  git push OK — dashboard will reflect updated traffic data")
    except Exception as e:
        print(f"  git push failed (run manually): {e}")


if __name__ == "__main__":
    collect(days=90, verbose=True)
