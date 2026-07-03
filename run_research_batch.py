"""run_research_batch.py — Research batch: pre-research the next 2 titles in line.

Runs Scout for the next 2 articles from the editorial calendar so their research
briefs are cached in articles/research/ before the pipeline writes the copy.

- Resolves titles + categories from aima-editorial-calendar.md + aima-coworker-state.json
- Scout skips any article whose research is already cached (no wasted tokens)
- Each brief lands at articles/research/[slug]-research.json (Scout's canonical path),
  which a pipeline run reuses automatically (Scout cache / scout.load_cached).
- The calendar is one unified canonical sequence (author is a per-row attribute).
  A row still titled "TBD — Trending Topic" first gets a real topic from
  agents/trend_scout.py (CC call, keyed to the row's assigned author), which
  writes the title back to the calendar before Scout researches it.

Usage:
  python run_research_batch.py                 # next 2 rows from next_article_number
  python run_research_batch.py --article 25 26 # specific canonical rows
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from agents.base import REPO_ROOT, log
from agents import scout, trend_scout

BATCH_SIZE = 2   # research the next 2 titles in line


def _slugify(text: str, max_parts: int = 5) -> str:
    slug = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")
    return "-".join(slug.split("-")[:max_parts])


def _read_calendar_rows() -> dict:
    """Parse the unified editorial calendar table
    -> {number: {title, category, author, tone_note}}.
    Layout: | # | Date | Title | Category | Read | Tone Note | Author |"""
    md = (REPO_ROOT / "articles" / "aima-editorial-calendar.md").read_text(encoding="utf-8")
    rows = {}
    for line in md.splitlines():
        m = re.match(r"\s*\|\s*(\d+)\s*\|\s*[\d-]+\s*\|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 6:
            continue
        rows[int(m.group(1))] = {
            "title": cells[3], "category": cells[4],
            "tone_note": cells[6] if len(cells) > 6 else "",
            "author": cells[7] if len(cells) > 7 and cells[7] else "Joselito Sering",
        }
    return rows


def resolve_next_specs(n: int = BATCH_SIZE) -> list:
    """Return minimal Scout specs for the next n calendar titles starting at
    state.next_article_number."""
    state = json.loads((REPO_ROOT / "articles" / "aima-coworker-state.json").read_text(encoding="utf-8"))
    start = int(state.get("next_article_number", 1))
    rows = _read_calendar_rows()

    specs = []
    num = start
    while len(specs) < n and num < start + 30:
        row = rows.get(num)
        if row:
            specs.append(_spec_from_row(num, row))
        num += 1
    return specs


def _spec_from_row(num: int, row: dict) -> dict:
    return {
        "number": num,
        "slug": _slugify(row["title"]),
        "title": row["title"],
        "category": row["category"],
        "author": row["author"],
        "tone_note": row["tone_note"],
        "custom_tags": [],
    }


def resolve_article_specs(numbers: list[str]) -> list:
    """Build Scout specs for explicit canonical row numbers."""
    rows = _read_calendar_rows()
    specs = []
    for n in numbers:
        row = rows.get(int(n))
        if not row:
            log.error(f"[research-batch] row #{n} not found in the calendar — skipping")
            continue
        specs.append(_spec_from_row(int(n), row))
    return specs


def main():
    ap = argparse.ArgumentParser(description="AIMA research batch (Scout)")
    ap.add_argument("--article", nargs="+", metavar="N",
                    help="canonical row number(s) to research, e.g. --article 25 26 "
                         "(TBD trending rows get a real topic first via trend_scout)")
    args = ap.parse_args()

    specs = resolve_article_specs(args.article) if args.article else resolve_next_specs()
    if not specs:
        log.info("[research-batch] No upcoming titles found in the calendar. Nothing to do.")
        return

    log.info(f"[research-batch] Researching {len(specs)} upcoming title(s) -> articles/research/")
    done = 0
    for spec in specs:
        label = f"#{spec['number']:03d} '{spec['title'][:48]}'"
        log.info(f"[research-batch] {label}")
        try:
            # TBD trending row? Determine the real topic first (writes it back
            # to the calendar — idempotent: resolved rows skip straight to Scout).
            spec = trend_scout.resolve_tbd_spec(spec)
            scout.run(spec)   # Scout returns cached research if it already exists (no tokens)
            done += 1
        except Exception as e:
            log.error(f"[research-batch] {label} -- failed: {e}")
    log.info(f"[research-batch] Done. {done}/{len(specs)} processed (cached briefs skipped inside Scout).")


if __name__ == "__main__":
    main()
