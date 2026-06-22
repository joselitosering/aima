"""run.py — AIMA pipeline entry point.

Usage:
    python run.py              # full pipeline run
    python run.py --dry-run    # no git push, no LinkedIn post
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="AIMA article pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip git push and LinkedIn post")
    args = parser.parse_args()

    from agents.priya import run as priya_run

    print("=== AIMA Pipeline ===")

    # Stage 1 — Priya builds the article spec
    print("[1/9] Priya: building article spec...")
    spec = priya_run()
    print(f"      Spec: {spec.get('slug')} — {spec.get('title')}")
    print(f"      Author: {spec.get('author')} | {spec.get('publish_date')}")
    print()
    print("Spec JSON:")
    print(json.dumps(spec, indent=2))

    # Stages 2-9 will be wired here as Marco is built (Phase 4)
    print("\n[Phase 1 complete — Marco not yet wired. Spec above is ready for handoff.]")

    return spec


if __name__ == "__main__":
    main()
