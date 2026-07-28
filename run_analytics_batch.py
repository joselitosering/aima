"""run_analytics_batch.py — Analytics run: fetch LinkedIn analytics (Echo) and report.

Echo collects LinkedIn metrics for posts 48h+ old into post_analytics.csv and marks
them collected in post_log.json. The summary is reported here for Priya, who reconciles
analytics on her audit run (run_priya_batch.py). This does NOT aggregate GA4 — that is
the separate Lumen run (run_lumen_batch.py). Echo is pure Python (no LLM tokens).

Usage: python run_analytics_batch.py
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.base import log
from agents import echo


def main():
    log.info("[analytics-batch] Echo: fetching LinkedIn analytics for posts 48h+ old...")
    try:
        report = echo.run()
    except Exception as e:
        log.error(f"[analytics-batch] Echo failed: {e}")
        sys.exit(1)

    log.info(f"[analytics-batch] posts_collected={report.get('posts_collected', 0)} "
             f"awaiting={report.get('posts_awaiting_analytics', 0)} "
             f"avg_impressions={report.get('avg_impressions', 0)} "
             f"avg_ctr={report.get('avg_ctr', '0%')}")
    for flag in report.get("flags", []):
        log.warning(f"[analytics-batch] FLAG: {flag}")
    log.info("[analytics-batch] Reported to linkedin_pipeline/post_analytics.csv. "
             "Priya reconciles analytics on her audit run; Lumen merges with GA4 on the Lumen run.")


if __name__ == "__main__":
    main()
