"""run_optimization_batch.py — Optimization run (Iris advisory).

Iris reads the consolidated optimization report (Marco, Lumen, Cora, Priya
contributions in optimization/optimization_report.json) plus the editorial calendar,
produces editorial decisions + advisory, and updates the calendar + CLAUDE.md.

Iris is the decision authority (quality control). Gated: she is a CC agent (tokens)
and edits source-of-truth (calendar + CLAUDE.md).

Usage: python run_optimization_batch.py
"""

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

from agents.base import REPO_ROOT, read_json, log
from agents import iris


def main():
    report = read_json("optimization/optimization_report.json")
    entries = report if isinstance(report, list) else []
    by_source = {}
    for e in entries:
        by_source[e.get("source", "?")] = by_source.get(e.get("source", "?"), 0) + 1
    log.info(f"[optimization] Inputs in optimization_report.json: "
             f"{', '.join(f'{k}={v}' for k, v in by_source.items()) or 'none'}")

    log.info("[optimization] Iris: producing editorial decisions + advisory from the reports...")
    try:
        decisions = iris.run()
    except Exception as e:
        log.error(f"[optimization] Iris failed: {e}")
        sys.exit(1)

    n = len(decisions.get("decisions", [])) if isinstance(decisions, dict) else 0
    log.info(f"[optimization] Done. Iris produced {n} decision(s); calendar + CLAUDE.md updated.")
    print(json.dumps({"decisions": n}))


if __name__ == "__main__":
    main()
