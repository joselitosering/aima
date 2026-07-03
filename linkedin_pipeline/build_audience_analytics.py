"""
build_audience_analytics.py
Parse AggregateAnalytics XLS into audience_analytics.json
Run once: python build_audience_analytics.py <path-to-xlsx>
"""
import sys, json
from pathlib import Path
from datetime import datetime

try:
    import openpyxl
except ImportError:
    print("pip install openpyxl --break-system-packages")
    sys.exit(1)

XLS = Path(r"C:\Users\ShadowMonkey\Downloads\AggregateAnalytics_Joselito Sering_2026-03-29_2026-06-26.xlsx")
OUT = Path(__file__).parent / "audience_analytics.json"


def parse_date(raw):
    """Normalise M/D/YYYY or YYYY-MM-DD -> YYYY-MM-DD string."""
    if not raw:
        return ""
    raw = str(raw).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw


def load_sheet(wb, name):
    ws = wb[name]
    return [[cell.value for cell in row] for row in ws.iter_rows()]


wb = openpyxl.load_workbook(XLS, data_only=True)

# ── DISCOVERY ────────────────────────────────────────────────────────────────
disc = load_sheet(wb, "DISCOVERY")
discovery = {}
for row in disc:
    if row and str(row[0]).strip() == "Impressions":
        discovery["total_impressions"] = int(row[1])
    elif row and str(row[0]).strip() == "Members reached":
        discovery["members_reached"] = int(row[1])

# ── ENGAGEMENT ───────────────────────────────────────────────────────────────
eng_rows = load_sheet(wb, "ENGAGEMENT")
engagement_daily = []
for row in eng_rows:
    if not row or str(row[0]).strip() == "Date":
        continue
    engagement_daily.append({
        "date":        parse_date(row[0]),
        "impressions": int(row[1]) if row[1] is not None else 0,
        "engagements": int(row[2]) if row[2] is not None else 0,
    })

# ── FOLLOWERS ────────────────────────────────────────────────────────────────
fol_rows = load_sheet(wb, "FOLLOWERS")
total_followers = 0
followers_daily = []
for row in fol_rows:
    if not row:
        continue
    cell0 = str(row[0]).strip() if row[0] else ""
    if "Total followers" in cell0:
        total_followers = int(row[1]) if row[1] else 0
        continue
    if cell0 == "Date" or cell0 == "":
        continue
    followers_daily.append({
        "date":          parse_date(row[0]),
        "new_followers": int(row[1]) if row[1] is not None else 0,
    })

# ── DEMOGRAPHICS ─────────────────────────────────────────────────────────────
demo_rows = load_sheet(wb, "DEMOGRAPHICS")
demographics = {}
for row in demo_rows:
    if not row or str(row[0]).strip() == "Top Demographics":
        continue
    category = str(row[0]).strip() if row[0] else ""
    name     = str(row[1]).strip() if row[1] else ""
    pct      = str(row[2]).strip() if row[2] else ""
    if not category or not name:
        continue
    key = category.lower().replace(" ", "_")
    demographics.setdefault(key, []).append({"name": name, "percentage": pct})

# ── TOP POSTS ────────────────────────────────────────────────────────────────
top_rows = load_sheet(wb, "TOP POSTS")
by_eng = []
by_imp = []
for row in top_rows:
    if not row or not row[0]:
        pass  # allow partial rows with impressions-only
    # Columns 0-2: engagements side; Columns 4-6: impressions side
    if row[0] and str(row[0]).startswith("http"):
        by_eng.append({
            "url":         str(row[0]).strip(),
            "date":        parse_date(row[1]),
            "engagements": int(row[2]) if row[2] else 0,
        })
    if len(row) > 4 and row[4] and str(row[4]).startswith("http"):
        by_imp.append({
            "url":         str(row[4]).strip(),
            "date":        parse_date(row[5]),
            "impressions": int(row[6]) if row[6] else 0,
        })

# ── BUILD JSON ────────────────────────────────────────────────────────────────
data = {
    "report_period": "2026-03-29 to 2026-06-26",
    "generated_at":  "2026-06-26",
    "source_file":   XLS.name,
    "discovery":     discovery,
    "followers": {
        "total":           total_followers,
        "total_as_of":     "2026-06-26",
        "daily":           followers_daily,
    },
    "engagement": {
        "total_impressions": discovery.get("total_impressions", 0),
        "members_reached":   discovery.get("members_reached", 0),
        "daily":             engagement_daily,
    },
    "demographics": demographics,
    "top_posts": {
        "by_engagements": by_eng,
        "by_impressions": by_imp,
    },
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Done: {OUT}")
print(f"  Engagement days:  {len(engagement_daily)}")
print(f"  Follower days:    {len(followers_daily)}")
print(f"  Total followers:  {total_followers}")
print(f"  Demo categories:  {list(demographics.keys())}")
print(f"  Top by eng:       {len(by_eng)} posts")
print(f"  Top by imp:       {len(by_imp)} posts")
