"""run.py — AIMA pipeline entry point.

Usage:
    python run.py              # full pipeline run
    python run.py --dry-run    # no git push, no LinkedIn post
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="AIMA article pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip git push and LinkedIn post")
    args = parser.parse_args()

    print("=== AIMA Pipeline ===")

    try:
        from agents import marco
        marco.run(dry_run=args.dry_run)
    except ImportError:
        print("[run.py] Marco (Phase 4) not yet built — pipeline not wired.")
        print("         Run each agent individually during development:")
        print("           python -c \"from agents.priya import run; print(run())\"")
        sys.exit(0)


if __name__ == "__main__":
    main()
