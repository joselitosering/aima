"""run_lumen_batch.py — Lumen run: merge LinkedIn analytics + GA4 into Lumen's report.

Takes the LinkedIn analytics Echo already fetched (post_analytics.csv) plus GA4 traffic
(ga4_traffic.csv) and has Lumen aggregate them cross-platform into optimization_report.json
+ platform_summary.json. Run the Analytics (Echo) batch and the GA4 collector first.
Lumen is a CC agent — this uses Claude Code tokens.

Usage: python run_lumen_batch.py [--force]

--force bypasses the per-day dedup for an on-demand intra-day refresh: it runs
the (paid) CC call even if today's entry already exists, and replaces that
entry with the fresh result. Without it, a same-day re-run short-circuits with
no CC call.
"""

import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.base import REPO_ROOT, log
from agents import lumen


def _linkedin_report() -> dict:
    """Build an Echo-style report from the LinkedIn analytics already on disk."""
    f = REPO_ROOT / "linkedin_pipeline" / "post_analytics.csv"
    rows = []
    if f.exists():
        with open(f, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    imps = [int(r.get("impressions", 0) or 0) for r in rows]
    return {
        "source": "post_analytics.csv",
        "posts_collected": len(rows),
        "avg_impressions": round(sum(imps) / len(imps)) if imps else 0,
        "rows": rows[-25:],  # cap payload to the latest entries
    }


def main():
    force = "--force" in sys.argv[1:]
    report = _linkedin_report()
    log.info(f"[lumen-batch] LinkedIn analytics: {report['posts_collected']} row(s) from post_analytics.csv")
    if force:
        log.info("[lumen-batch] --force set: bypassing per-day dedup, refreshing today's entry")
    log.info("[lumen-batch] Lumen: merging LinkedIn + GA4 (ga4_traffic.csv) -> optimization_report.json")
    try:
        entry = lumen.run(report, force=force)
    except Exception as e:
        log.error(f"[lumen-batch] Lumen failed: {e}")
        sys.exit(1)
    log.info(f"[lumen-batch] Done. Lumen entry written (flags: {entry.get('flags', [])})")


if __name__ == "__main__":
    main()
