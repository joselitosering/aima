"""measure_writer_quill_merge.py — real cost A/B for the Direction B merge.

Measures the ACTUAL claude-CLI cost of:
  OLD path  = Writer (cold call) + Quill edits the draft (cold call)   [2 calls]
  NEW path  = Quill authors + edits in one call (Writer merged)        [1 call]

on ONE article that ALREADY has cached Scout research, so no Scout call is paid.
Per-call cost is read from the real numbers agents/base.py::_record_token_usage()
writes into token_budget.json (last_call_cost_usd / used), captured as a delta
around each call — these are the CLI's own usage/total_cost_usd fields, not an
estimate.

To avoid clobbering any real/published article, every call writes to throwaway
filenames under a MEASURE slug; the harness deletes them afterward.

Session-limit discipline: if any call raises the CLI "session limit" RuntimeError,
the harness stops immediately and prints whatever it measured so far. It never
retries. Total real CC calls when it runs clean: 3.

Usage:
  python measure_writer_quill_merge.py --research persuasion-engine
  python measure_writer_quill_merge.py --research persuasion-engine --author dawn
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.base import REPO_ROOT, log, read_json
from agents import writer, quill, cora

MEASURE_SLUG = "measure-abtest"


def _cost(code: str) -> float:
    """Current cumulative cost recorded for a token_budget.json agent code."""
    return read_json("token_budget.json").get("agents", {}).get(code, {}).get("cumulative_cost_usd", 0.0)


def _cleanup(spec: dict, draft_path: str | None):
    for rel in filter(None, [f"articles/{spec['filename']}", draft_path]):
        p = REPO_ROOT / rel
        if p.exists():
            p.unlink()
            log.info(f"[measure] cleaned up {rel}")


def main():
    ap = argparse.ArgumentParser(description="Direction B merge cost A/B")
    ap.add_argument("--research", required=True,
                    help="slug of an existing articles/research/<slug>-research.json")
    ap.add_argument("--author", default="Dawn Ginhaua",
                    help="persona display name for the throwaway spec")
    args = ap.parse_args()

    research_path = REPO_ROOT / f"articles/research/{args.research}-research.json"
    if not (research_path.exists() and research_path.stat().st_size > 100):
        log.error(f"[measure] no research at {research_path} — pick a slug that has cached research")
        sys.exit(1)
    research = json.loads(research_path.read_text(encoding="utf-8"))

    # Throwaway spec — real research, disposable output filenames.
    spec = {
        "number": 999, "slug": MEASURE_SLUG,
        "filename": f"aima-article-{MEASURE_SLUG}-999.html",
        "og_image": f"img/articles/aima-999-{MEASURE_SLUG}.jpg",
        "title": "[MEASURE] Direction B A/B", "author": args.author,
        "category": "AI Society", "read_time": "8 min",
        "publish_date": "2026-07-04", "tone": "analytical", "mood": "thoughtful",
        "custom_tags": [], "target_words": 1400,
    }
    qp = cora.prepare_quill_call(spec)
    spec["target_words"] = qp["target_words"]

    result = {"research_slug": args.research, "author": args.author}
    draft_path = None
    try:
        # ── OLD path, call 1: Writer authors a free-form draft ──────────────
        log.info("[measure] OLD path call 1/2 — Writer authoring free draft")
        c0 = _cost("WR")
        draft_path = writer.run(spec, research)
        result["old_writer_cost_usd"] = round(_cost("WR") - c0, 6)

        # ── OLD path, call 2: Quill edits that draft to the checklist ───────
        log.info("[measure] OLD path call 2/2 — Quill editing draft")
        c0 = _cost("QL")
        quill.run(spec, research, extra_instruction=qp["extra_instruction"],
                  draft_path=draft_path, force_rewrite=True)
        result["old_quill_cost_usd"] = round(_cost("QL") - c0, 6)
        result["old_total_cost_usd"] = round(result["old_writer_cost_usd"]
                                              + result["old_quill_cost_usd"], 6)

        # ── NEW path: Quill authors + edits in one call (no draft) ──────────
        log.info("[measure] NEW path 1/1 — Quill authoring+editing in one call")
        c0 = _cost("QL")
        quill.run(spec, research, extra_instruction=qp["extra_instruction"],
                  draft_path=None, force_rewrite=True)
        result["new_merged_cost_usd"] = round(_cost("QL") - c0, 6)

        result["savings_usd"] = round(result["old_total_cost_usd"]
                                      - result["new_merged_cost_usd"], 6)
        result["savings_pct"] = (round(100 * result["savings_usd"]
                                       / result["old_total_cost_usd"], 1)
                                 if result["old_total_cost_usd"] else None)
        result["status"] = "complete"
    except RuntimeError as exc:
        result["status"] = "aborted"
        result["error"] = str(exc)[:300]
        if "session limit" in str(exc).lower():
            result["error_kind"] = "session_limit"
            log.warning("[measure] hit session limit — stopping, not retrying")
    finally:
        _cleanup(spec, draft_path)

    print("\n=== MEASUREMENT RESULT ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
