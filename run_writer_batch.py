"""run_writer_batch.py — Writer batch: a persona writes the next (or chosen) article.

Joselito / Dawn / Kenji write a free-form HTML draft from Priya's topic+tags and
Scout's research, saved to articles/drafts/ for Quill (the editor) to refine in the
full pipeline. Writers do NOT research: if Scout has no research for the article, the
batch REPORTS it and HALTS (exit 2) instead of researching.

The calendar is one unified canonical sequence; each row's Author column names
the writer. A row still titled "TBD — Trending Topic" first gets a real topic
from agents/trend_scout.py (written back to the calendar, keyed to the row's
assigned author); the no-research HALT rule still applies afterward — run the
Research batch before the writer.

Usage:
  python run_writer_batch.py                       # next assignment (author from calendar)
  python run_writer_batch.py --author dawn          # next assignment, force author
  python run_writer_batch.py --article 25           # specific canonical row
"""

import argparse
import json
import re
import sys
import traceback
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.base import REPO_ROOT, log
from agents import writer, trend_scout
from agents.scout import _find_research_path


def _slugify(text: str, max_parts: int = 5) -> str:
    s = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")
    return "-".join(s.split("-")[:max_parts])


def _calendar_rows() -> dict:
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


def resolve_spec(article: str | None = None) -> dict | None:
    state = json.loads((REPO_ROOT / "articles" / "aima-coworker-state.json").read_text(encoding="utf-8"))
    rows = _calendar_rows()
    num = int(article) if article else int(state.get("next_article_number", 1))
    row = rows.get(num)
    if not row:
        return None

    slug = _slugify(row["title"])
    # This mechanical slugify can drift from Priya's actual CC-chosen spec slug
    # (confirmed 2026-07-04: #19 "The Persuasion Engine..." -> this function
    # produces "the-persuasion-engine-ai-social", but Priya's real spec/research
    # used "persuasion-engine"). If research already exists for this article
    # number, adopt ITS slug so the draft lands under the same canonical name
    # Marco/Quill/Maya will look for later — otherwise the writer batch either
    # HALTs on a false "no_research" or writes a draft under a slug the rest of
    # the pipeline never finds again.
    existing = _find_research_path(slug, num)
    if existing.exists() and existing.stat().st_size > 100:
        try:
            meta_slug = json.loads(existing.read_text(encoding="utf-8")).get("_meta", {}).get("slug")
        except (json.JSONDecodeError, OSError):
            meta_slug = None
        if meta_slug and meta_slug != slug:
            log.info(f"[writer-batch] slug drift: calendar-title slug '{slug}' -> "
                     f"adopting Priya's existing research slug '{meta_slug}'")
            slug = meta_slug

    return {"number": num, "slug": slug, "title": row["title"],
            "category": row["category"], "author": row["author"],
            "tone_note": row["tone_note"], "custom_tags": []}


def main():
    ap = argparse.ArgumentParser(description="AIMA writer batch")
    ap.add_argument("--author", choices=["joselito", "dawn", "kenji"],
                    help="force the writer (default: next assignment's calendar author)")
    ap.add_argument("--article", help="canonical row number (default: next assignment)")
    args = ap.parse_args()

    spec = resolve_spec(args.article)
    if not spec:
        log.error("[writer-batch] No calendar entry for the requested article. Nothing to write.")
        sys.exit(1)

    # TBD trending row? Determine the real topic first (written back to the
    # calendar, keyed to the row's assigned author). This only replaces the
    # TITLE — the no-research HALT below still applies; Scout must produce a
    # brief before anyone writes.
    spec = trend_scout.resolve_tbd_spec(spec)

    # Writers do not research — Scout's brief must already exist.
    rp = _find_research_path(spec["slug"], spec["number"])
    if not (rp.exists() and rp.stat().st_size > 100):
        log.warning(f"[writer-batch] HALT — no Scout research for #{spec['number']:03d} "
                    f"'{spec['title'][:44]}'. Run the Research batch first (writers do not research).")
        print(json.dumps({"halted": True, "reason": "no_research", "article": spec["number"]}))
        sys.exit(2)

    research = json.loads(rp.read_text(encoding="utf-8"))
    key = writer.resolve_author(spec, args.author)
    log.info(f"[writer-batch] #{spec['number']:03d} '{spec['title'][:44]}' "
             f"-> writer={writer.AUTHOR_SPECS[key]['name']} ({writer.AUTHOR_SPECS[key]['range']})")
    try:
        path = writer.run(spec, research, author=args.author)
    except Exception:
        # Full traceback now persists to pipeline.log (agents/base.py FileHandler,
        # added 2026-07-04) instead of vanishing when a scheduled/detached run's
        # console closes. Exit non-zero rather than an unhandled crash banner.
        log.error(f"[writer-batch] Writer failed for #{spec['number']:03d}:\n{traceback.format_exc()}")
        sys.exit(3)
    log.info(f"[writer-batch] Done. Draft -> {path}  (Quill edits this in the full pipeline)")


if __name__ == "__main__":
    main()
