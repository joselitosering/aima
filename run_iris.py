"""run_iris.py — Weekly strategic review runner.

Usage:
    python run_iris.py

Runs Iris, who reads optimization_report.json, updates the editorial
calendar, and writes strategic decisions to CLAUDE.md.
Run weekly or manually after several articles have been published.
"""

import json
import sys
import logging

log = logging.getLogger("aima")


def main():
    print("=== AIMA Strategic Review (Iris) ===")

    from agents.iris import run as iris_run
    try:
        decisions = iris_run()
    except Exception as exc:
        print(f"[ERROR] Iris failed: {exc}")
        sys.exit(1)

    print(f"\nDecisions ({len(decisions.get('decisions', []))}):")
    for d in decisions.get("decisions", []):
        print(f"  • {d}")

    if decisions.get("calendar_changes"):
        print(f"\nCalendar changes:")
        for c in decisions["calendar_changes"]:
            print(f"  • {c}")

    if decisions.get("prompt_recommendations"):
        print(f"\nPrompt recommendations:")
        for agent, rec in decisions["prompt_recommendations"].items():
            print(f"  {agent}: {rec}")

    if decisions.get("budget_recommendations"):
        print(f"\nBudget recommendations:")
        for agent, rec in decisions["budget_recommendations"].items():
            print(f"  {agent}: {rec}")

    if decisions.get("flags"):
        print(f"\nFlags: {decisions['flags']}")

    print("\n=== Iris review complete ===")


if __name__ == "__main__":
    main()
