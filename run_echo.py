"""run_echo.py — Daily analytics runner.

Usage:
    python run_echo.py

Runs Echo (LinkedIn stats collection) → Lumen (cross-platform aggregation).
Designed to run daily, independently of the article pipeline.
"""

import sys
import logging

log = logging.getLogger("aima")


def main():
    print("=== AIMA Analytics Runner ===")

    # Stage 1 — Echo: collect LinkedIn post stats
    print("[1/2] Echo: collecting LinkedIn analytics...")
    from agents.echo import run as echo_run
    try:
        echo_report = echo_run()
        print(f"      Posts collected: {echo_report.get('posts_collected', 0)}")
        print(f"      Avg impressions: {echo_report.get('avg_impressions', 0)}")
        print(f"      Avg CTR: {echo_report.get('avg_ctr', '0%')}")
    except Exception as exc:
        print(f"      [ERROR] Echo failed: {exc}")
        sys.exit(1)

    # Stage 2 — Lumen: aggregate all platforms + write optimization_report.json
    print("[2/2] Lumen: aggregating cross-platform analytics...")
    from agents.lumen import run as lumen_run
    try:
        lumen_entry = lumen_run(echo_report)
        print(f"      optimization_report.json updated (source=lumen)")
        flags = lumen_entry.get("flags", [])
        if flags:
            print(f"      Flags: {flags}")
    except Exception as exc:
        print(f"      [ERROR] Lumen failed: {exc}")
        sys.exit(1)

    print("\n=== Analytics run complete ===")


if __name__ == "__main__":
    main()
