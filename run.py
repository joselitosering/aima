"""run.py — AIMA pipeline entry point.

Usage:
    python run.py              # full pipeline run
    python run.py --dry-run    # no git push, no LinkedIn post

On completion writes last-run-status.json (a compact, machine-readable outcome)
so the scheduled runner can alert on failures. See scripts/full-post-cowork/.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOCK_FILE = Path(__file__).parent / "pipeline.lock"
STATUS_FILE = Path(__file__).parent / "last-run-status.json"


def _classify(result: dict) -> dict:
    """Reduce marco.run()'s return dict to a compact status for the runner."""
    spec = result.get("spec") or {}
    porter = result.get("porter") or {}
    nova = result.get("nova") or {}
    if result.get("crashed"):
        outcome = "crash"
    elif result.get("trend_scout_unavailable"):
        # Expected + recoverable: scout/trend_scout had no search-capable
        # backend (CC OAuth expired / no funded OpenRouter key) and we refuse
        # to fabricate research from a tool-less fallback. Kept OUT of the
        # "crash" bucket on purpose so alerting can tell "go re-auth the CLI"
        # apart from "a genuine new bug needs debugging". Added 2026-07-22.
        outcome = "trend_scout_unavailable"
    elif result.get("cost_halt"):
        outcome = "cost_halt"
    elif result.get("halted_for_review"):
        outcome = "vera_halt"
    elif result.get("held_for_human_review"):
        outcome = "held"
    elif porter.get("live_url"):
        outcome = "published"
    else:
        outcome = "completed_no_publish"
    try:
        from agents import marco
        cost = marco._cumulative_cost_usd()
    except Exception:
        cost = None
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
        "success": outcome == "published",
        "article_number": spec.get("number"),
        "title": spec.get("title"),
        "live_url": porter.get("live_url"),
        "company_urn": nova.get("company_urn"),
        "reshare_urn": nova.get("reshare_urn"),
        "cost_usd": cost,
        "cost_ceiling_usd": result.get("cost_ceiling_usd"),
        "crashed_stage": result.get("crashed_stage"),
        "halted_stage": result.get("halted_stage"),
        "error": result.get("error"),
        "vera_verdict": result.get("vera_verdict"),
        "flags": result.get("flags"),
    }


def _write_status(status: dict):
    try:
        STATUS_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"[run.py] could not write status file: {exc}")
    print(f"[run.py] RESULT outcome={status['outcome']} "
          f"article=#{status.get('article_number')} cost=${status.get('cost_usd')}")


def main():
    parser = argparse.ArgumentParser(description="AIMA article pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip git push and LinkedIn post")
    args = parser.parse_args()

    # ── Pipeline lock: prevent concurrent runs ────────────────────────────────
    if LOCK_FILE.exists():
        existing_pid = LOCK_FILE.read_text().strip()
        print(f"[run.py] ABORT: pipeline.lock exists (PID {existing_pid}). "
              f"Another run is active. Delete pipeline.lock manually if that "
              f"process is dead.")
        sys.exit(1)

    LOCK_FILE.write_text(str(os.getpid()))
    try:
        print("=== AIMA Pipeline ===")
        from agents import base, marco
        if args.dry_run:
            base.DRY_RUN = True
        result = marco.run(dry_run=args.dry_run)
        _write_status(_classify(result or {}))
    except ImportError as exc:
        print("[run.py] Marco not yet built — pipeline not wired.")
        _write_status({"ts": datetime.now(timezone.utc).isoformat(),
                       "outcome": "import_error", "success": False, "error": str(exc)})
        sys.exit(0)
    finally:
        # Always release lock, even on crash
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()


if __name__ == "__main__":
    main()
