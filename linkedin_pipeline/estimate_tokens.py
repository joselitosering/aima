"""
estimate_tokens.py — Estimates token usage from output file sizes and updates token_budget.json.

Since the pipeline uses Claude Code CLI (subscription-billed) and doesn't expose
exact token counts, this script derives approximate usage from:
  - SC (Scout):  research JSON file size
  - QL (Quill):  article HTML file size (generated copy)
  - MY (Maya):   article HTML final size (merged with images)
  - IR (Iris):   not yet wired — estimated flat
  - PR (Priya):  spec output is small — estimated flat
  - VR (Vera):   reads article + outputs verdict — estimated from article size
  - CO (Cora):   reads article + research — estimated from both
  - LM (Lumen):  not yet wired — estimated flat
  - MR/PT/NV/EC: pure Python or not yet built — 0

Chars-per-token approximation: 3.8 for HTML/JSON content (mixed prose + markup).

Run: python linkedin_pipeline/estimate_tokens.py
"""

import json, os
from pathlib import Path

REPO_ROOT  = Path(__file__).parent.parent
BUDGET_FILE = REPO_ROOT / "token_budget.json"
ARTICLES   = REPO_ROOT / "articles"
RESEARCH   = REPO_ROOT / "articles" / "research"

CHARS_PER_TOKEN = 3.8  # conservative mixed prose/markup estimate


def file_tokens(path: Path) -> int:
    """Return estimated token count for a file based on its size."""
    if not path.exists():
        return 0
    size = path.stat().st_size
    return max(0, int(size / CHARS_PER_TOKEN))


def estimate_for_article(article_number: int) -> dict:
    """
    Find the research + article files for a given article number
    and estimate per-agent token consumption.
    """
    padded = str(article_number).zfill(3)

    # Find research JSON
    research_files = list(RESEARCH.glob(f"*-{padded}-research.json"))
    # fallback: any research file mentioning the number
    if not research_files:
        research_files = list(RESEARCH.glob(f"*{padded}*research*.json"))
    research_path = research_files[0] if research_files else None
    research_tokens = file_tokens(research_path) if research_path else 0

    # Find final article HTML
    article_files = list(ARTICLES.glob(f"aima-article-*-{padded}.html"))
    article_path  = article_files[0] if article_files else None
    article_tokens = file_tokens(article_path) if article_path else 0

    if research_path:
        print(f"  Research: {research_path.name} ({research_tokens:,} est. tokens)")
    else:
        print(f"  Research: not found for article {padded}")

    if article_path:
        print(f"  Article:  {article_path.name} ({article_tokens:,} est. tokens)")
    else:
        print(f"  Article:  not found for article {padded}")

    # Per-agent estimates
    # Scout generates the research JSON (input + output overhead)
    sc_tokens = int(research_tokens * 1.4)   # generation overhead ~40%
    # Quill writes the article HTML from research + spec
    ql_tokens = int((research_tokens * 0.5) + (article_tokens * 1.2))
    # Maya merges images into the article (reads article, writes final)
    my_tokens = int(article_tokens * 0.6)
    # Priya builds the spec (small prompt + JSON output)
    pr_tokens = 1200
    # Vera reads article + spec and outputs a verdict
    vr_tokens = int(article_tokens * 0.3) + 400
    # Cora reads article + research + budget
    co_tokens = int((article_tokens * 0.3) + (research_tokens * 0.2)) + 500
    # Iris, Lumen — not yet wired into pipeline
    ir_tokens = 0
    lm_tokens = 0

    return {
        "IR": ir_tokens,
        "PR": pr_tokens,
        "SC": sc_tokens,
        "QL": ql_tokens,
        "MY": my_tokens,
        "VR": vr_tokens,
        "PT": 0,
        "NV": 0,
        "EC": 0,
        "LM": lm_tokens,
        "CO": co_tokens,
        "MR": 0,
    }


def update_token_budget(estimates: dict):
    """Write estimated token usage back into token_budget.json."""
    if not BUDGET_FILE.exists():
        print(f"ERROR: token_budget.json not found at {BUDGET_FILE}")
        return

    with open(BUDGET_FILE, encoding="utf-8") as f:
        budget = json.load(f)

    agents = budget.get("agents", {})
    total_used = 0

    for code, used_est in estimates.items():
        if code in agents:
            agents[code]["used"]   = used_est
            agents[code]["status"] = "complete" if used_est > 0 else "idle"
            b = agents[code].get("budget", 0)
            if b > 0 and used_est > b:
                agents[code]["status"] = "over_budget"
        total_used += used_est

    budget["agents"] = agents
    budget["estimated"] = True   # flag so dashboard can show "~" prefix

    with open(BUDGET_FILE, "w", encoding="utf-8") as f:
        json.dump(budget, f, indent=2)

    print(f"\n  token_budget.json updated — total estimated: {total_used:,} tokens")
    print(f"  (flagged as estimated=true; values are approximations from file sizes)")


def print_budget_summary(estimates: dict):
    """Print a table of estimates vs budget."""
    if not BUDGET_FILE.exists():
        return
    with open(BUDGET_FILE, encoding="utf-8") as f:
        budget = json.load(f)
    agents = budget.get("agents", {})

    print(f"\n{'='*55}")
    print(f"Token Budget — Article #{budget.get('article_number')} ({budget.get('run_date')})")
    print(f"{'='*55}")
    print(f"  {'Agent':6} {'Budget':>8} {'Est. Used':>10} {'%':>6}  Status")
    print(f"  {'-'*6} {'-'*8} {'-'*10} {'-'*6}  {'-'*12}")
    for code, a in agents.items():
        b = a.get("budget", 0)
        u = a.get("used", 0)
        pct = f"{u/b*100:.0f}%" if b > 0 else "n/a"
        status = a.get("status", "idle")
        if b == 0 and u == 0:
            continue  # skip unbudgeted idle agents
        flag = " <<< OVER" if status == "over_budget" else ""
        print(f"  {code:6} {b:>8,} {u:>10,} {pct:>6}  {status}{flag}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    if not BUDGET_FILE.exists():
        print(f"token_budget.json not found at {BUDGET_FILE}")
        exit(1)

    with open(BUDGET_FILE, encoding="utf-8") as f:
        budget = json.load(f)

    article_number = budget.get("article_number", 0)
    print(f"Estimating token usage for article #{article_number}...")

    estimates = estimate_for_article(article_number)
    update_token_budget(estimates)
    print_budget_summary(estimates)
