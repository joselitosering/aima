"""run_token_audit.py — Token Audit (Cora): report the token budget ledger.

Read-only. Reports each agent's budget vs used from token_budget.json, flags
over-budget agents, and totals. No LLM tokens. The full pipeline's Cora stage
enforces guardrails per run; this batch audits the ledger on its own.

Usage: python run_token_audit.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.base import REPO_ROOT, log

AGENT_NAMES = {"IR": "Iris", "MR": "Marco", "PR": "Priya", "SC": "Scout", "QL": "Quill",
               "MY": "Maya", "VR": "Vera", "PT": "Porter", "NV": "Nova", "EC": "Echo",
               "LM": "Lumen", "CO": "Cora"}


def main():
    p = REPO_ROOT / "token_budget.json"
    if not p.exists():
        log.info("[token-audit] No token_budget.json yet — run the full pipeline to initialize it.")
        return

    data = json.loads(p.read_text(encoding="utf-8"))
    agents = data.get("agents", {})
    log.info(f"[token-audit] Ledger for article #{data.get('article_number', '?')} "
             f"(run {data.get('run_date', '?')})")

    total_b = total_u = 0
    over = []
    for code, a in agents.items():
        name = AGENT_NAMES.get(code, code)
        b, u, st = a.get("budget", 0), a.get("used", 0), a.get("status", "?")
        total_b += b
        total_u += u
        is_over = st == "over_budget" or (b and u > b)
        if is_over:
            over.append(f"{name} ({u}/{b})")
        log.info(f"[token-audit]   {name:8} {u:>7} / {b:<7} {st}{'  <-- OVER BUDGET' if is_over else ''}")

    pct = round(100 * total_u / total_b) if total_b else 0
    log.info(f"[token-audit] TOTAL {total_u} / {total_b} ({pct}%)  ·  "
             f"over-budget: {', '.join(over) if over else 'none'}")

    out = REPO_ROOT / "optimization" / "token_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "article_number": data.get("article_number"),
        "total_budget": total_b, "total_used": total_u, "pct": pct,
        "over_budget": over,
    }, indent=2), encoding="utf-8")
    log.info("[token-audit] Report -> optimization/token_audit.json")


if __name__ == "__main__":
    main()
