"""run_maya_batch.py — Maya batch: pre-design the next 2 titles in line.

Looks at the next 2 articles from the editorial calendar (starting at the state
file's next_article_number), generates their header images, and stages them in
handoff/ready/ so the visuals are ready before the pipeline writes the copy.

- Resolves titles from articles/aima-editorial-calendar.md + aima-coworker-state.json
- Skips any title whose images are already staged (no wasted Higgsfield credits)
- Real generation needs HIGGSFIELD_API_KEY in agents/.env; otherwise writes stubs

Usage: python run_maya_batch.py
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import os
from agents.base import REPO_ROOT, log
from agents import maya

HANDOFF_DIR = "handoff/ready"   # relative to repo root
BATCH_SIZE = 2                  # design the next 2 titles in line


def _slugify(text: str, max_parts: int = 5) -> str:
    slug = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")
    return "-".join(slug.split("-")[:max_parts])


def _read_calendar_titles() -> dict:
    """Parse the editorial calendar markdown table -> {number: title}."""
    md = (REPO_ROOT / "articles" / "aima-editorial-calendar.md").read_text(encoding="utf-8")
    titles = {}
    for line in md.splitlines():
        # | N | YYYY-MM-DD | Title | Category | read time | notes |
        m = re.match(r"\s*\|\s*(\d+)\s*\|\s*[\d-]+\s*\|\s*(.+?)\s*\|", line)
        if m:
            titles[int(m.group(1))] = m.group(2).strip()
    return titles


def resolve_next_titles(n: int = BATCH_SIZE) -> list:
    """Return minimal specs for the next n calendar titles starting at
    state.next_article_number. Output images target handoff/ready/."""
    state = json.loads((REPO_ROOT / "articles" / "aima-coworker-state.json").read_text(encoding="utf-8"))
    start = int(state.get("next_article_number", 1))
    titles = _read_calendar_titles()

    specs = []
    num = start
    while len(specs) < n and num < start + 30:
        title = titles.get(num)
        if title and title.startswith("TBD") and "Trending Topic" in title:
            # Unresolved trending row — no cover art for a placeholder title.
            # Trend Scout fills the real title via the research/writer batch.
            log.info(f"[maya-batch] #{num:03d} is an unresolved TBD trending row — skipping")
            num += 1
            continue
        if title:
            slug = _slugify(title)
            padded = str(num).zfill(3)
            specs.append({
                "number": num,
                "slug": slug,
                "title": title,
                "mood": "analytical",
                "og_image": f"{HANDOFF_DIR}/aima-{padded}-{slug}.jpg",
            })
        num += 1
    return specs


def main():
    (REPO_ROOT / HANDOFF_DIR).mkdir(parents=True, exist_ok=True)

    specs = resolve_next_titles()
    if not specs:
        log.info("[maya-batch] No upcoming titles found in the calendar. Nothing to do.")
        return

    have_key = bool(os.environ.get("HIGGSFIELD_API_KEY"))
    log.info(f"[maya-batch] Designing {len(specs)} upcoming title(s) -> {HANDOFF_DIR}/  "
             f"(Higgsfield={'on' if have_key else 'STUB — set HIGGSFIELD_API_KEY for real images'})")

    designed = 0
    for spec in specs:
        primary = spec["og_image"]
        alt = f"{HANDOFF_DIR}/{Path(primary).stem}-alt.jpg"
        pf, af = REPO_ROOT / primary, REPO_ROOT / alt
        label = f"#{spec['number']:03d} '{spec['title'][:48]}'"

        # Skip-and-reuse — don't re-spend credits on already-staged images.
        if pf.exists() and pf.stat().st_size > 1024 and af.exists() and af.stat().st_size > 1024:
            log.info(f"[maya-batch] {label} — already staged, skipping")
            continue

        log.info(f"[maya-batch] {label} — generating")
        if have_key:
            maya._generate_images_higgsfield(spec, primary, alt)
        else:
            maya._generate_images_stub(spec, primary, alt)
        log.info(f"[maya-batch] {label} — staged -> {primary}")
        designed += 1

    log.info(f"[maya-batch] Done. {designed} generated, {len(specs) - designed} already staged.")


if __name__ == "__main__":
    main()
