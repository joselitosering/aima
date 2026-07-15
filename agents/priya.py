"""Priya — Calendar Manager (CC subagent).

Reads the editorial calendar and state file, then builds
a complete article spec JSON for Marco.
"""

import json
import re

from agents.base import call_cc_agent, read_json, read_file, log
from agents.prompts import PRIYA_PROMPT


def _slugify(text: str, max_parts: int = 5) -> str:
    slug = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")
    return "-".join(slug.split("-")[:max_parts])


def _normalize_spec(raw: dict, state: dict) -> dict:
    """
    Map whatever the CC agent returned to the schema Marco expects.
    Handles both the prompt-specified schema and the calendar-row schema
    the agent sometimes returns instead.
    """
    number = int(
        raw.get("number") or
        raw.get("article_number") or
        state.get("next_article_number", 1)
    )
    padded = str(number).zfill(3)

    title = raw.get("title", "")
    if not title or title.upper().startswith("TBD"):
        raise ValueError(
            f"Priya returned a TBD title — cannot build spec. "
            f"Raw keys: {list(raw.keys())}"
        )

    # Slug: use what the agent returned if it's not TBD, else derive from title.
    slug_raw = raw.get("slug", "")
    if not slug_raw or slug_raw.upper().startswith("TBD"):
        slug_raw = _slugify(title)

    # File naming follows existing convention:
    #   articles/aima-article-{slug}-{NNN}.html
    #   img/articles/aima-{NNN}-{slug}.jpg
    filename = raw.get("filename") or f"aima-article-{slug_raw}-{padded}.html"
    og_image = raw.get("og_image") or f"img/articles/aima-{padded}-{slug_raw}.jpg"

    publish_date = (
        raw.get("publish_date") or
        raw.get("scheduled_date") or
        raw.get("date") or
        state.get("next_article_date", "")
    )

    return {
        "number": number,
        "slug": slug_raw,
        "filename": filename,
        "og_image": og_image,
        "title": title,
        "author": raw.get("author", ""),
        "category": raw.get("category", ""),
        "read_time": raw.get("read_time", "10 min"),
        "publish_date": publish_date,
        "tone": raw.get("tone", "analytical"),
        "mood": raw.get("mood", "thoughtful"),
        "custom_tags": raw.get("custom_tags", []),
        "target_words": int(raw.get("target_words", 1600)),
        # Pass through any extra fields (research_brief, profile_file, etc.)
        **{k: v for k, v in raw.items() if k not in {
            "number", "article_number", "article_id", "slug", "filename",
            "og_image", "title", "author", "category", "read_time",
            "publish_date", "scheduled_date", "date", "tone", "mood",
            "custom_tags", "target_words",
        }},
    }


def _parse_calendar_row(number: int) -> dict | None:
    """Read canonical calendar row `number` (pure Python).
    Layout: | # | Date | Title | Category | Read | Tone Note | Author |"""
    calendar = read_file("articles/aima-editorial-calendar.md")
    for line in calendar.splitlines():
        if not re.match(rf"\s*\|\s*{number}\s*\|\s*[\d-]+\s*\|", line):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 6:
            return None
        return {
            "publish_date": cells[2],
            "title":        cells[3],
            "category":     cells[4],
            "read_time":    cells[5] if len(cells) > 5 and cells[5] else "10 min",
            "tone_note":    cells[6] if len(cells) > 6 else "",
            "author":       cells[7] if len(cells) > 7 and cells[7] else "Joselito Sering",
        }
    return None


def _resolve_slug(title: str, number: int) -> str:
    """Deterministic slug from the title, but adopt the CANONICAL research file's
    slug for this article number if one exists — so a freshly-built spec lines up
    with research/drafts/article already on disk (prevents slug-drift that breaks
    skip-and-reuse). Authoritative on _meta.article_number, NOT on a mechanical
    name match: a stale duplicate research file saved under the mechanical slug
    must not win over the canonical one (this bit #25 — both existed on disk)."""
    from agents.base import REPO_ROOT
    mech = _slugify(title)
    research_dir = REPO_ROOT / "articles" / "research"
    if research_dir.exists():
        for p in sorted(research_dir.glob("*-research.json")):
            if p.stat().st_size <= 100:
                continue
            try:
                meta = json.loads(p.read_text(encoding="utf-8")).get("_meta", {})
            except (json.JSONDecodeError, OSError):
                continue
            if meta.get("article_number") == number and meta.get("slug"):
                if meta["slug"] != mech:
                    log.info(f"[priya] adopting canonical research slug '{meta['slug']}' "
                             f"for #{number} (mechanical was '{mech}')")
                return meta["slug"]
    return mech


def run() -> dict:
    """Build and return the article spec — DETERMINISTIC pure Python, no LLM call.

    Demoted from a CC call 2026-07-14 (per Joe): reading the canonical calendar row
    and mapping it to a spec is entirely mechanical, and the LLM version could return
    malformed JSON that broke the pipeline at stage 1. $0 and reliable now. The one
    genuine judgment upstream — resolving a TBD trending row — still runs as
    trend_scout's own CC call before this (below), so Priya always reads a real title.
    """
    state = read_json("articles/aima-coworker-state.json")
    number = state["next_article_number"]

    # TBD trending row? Resolve it first (trend_scout's own CC call). No-op for
    # a row that already has a real title. Skipped entirely in DRY_RUN.
    from agents import base, trend_scout
    if base.DRY_RUN:
        log.info("[priya] DRY RUN — skipping trend_scout TBD check")
    elif trend_scout.resolve_tbd_row(number):
        log.info(f"[priya] trend_scout resolved TBD row #{number} — calendar updated")

    row = _parse_calendar_row(number)
    if not row:
        raise ValueError(f"[priya] no calendar row found for article #{number}")
    if not row["title"] or row["title"].upper().startswith("TBD"):
        raise ValueError(
            f"[priya] row #{number} title still TBD/empty after trend_scout: {row['title']!r}"
        )

    # target_words follows the row author's persona range (the same source
    # writer/quill/marco use), so the whole pipeline agrees on length.
    from agents.writer import AUTHOR_SPECS, resolve_author
    target_words = AUTHOR_SPECS[resolve_author({"author": row["author"]})]["target_words"]

    raw_spec = {
        "number":       number,
        "slug":         _resolve_slug(row["title"], number),
        "title":        row["title"],
        "author":       row["author"],
        "category":     row["category"],
        "read_time":    row["read_time"],
        "publish_date": row["publish_date"],
        "tone":         "analytical",
        "mood":         "thoughtful",
        "custom_tags":  [],
        "target_words": target_words,
    }
    spec = _normalize_spec(raw_spec, state)
    log.info(f"[priya] spec (python): #{spec['number']} '{spec['title'][:50]}' "
             f"by {spec['author']} -> {spec['filename']} ({spec['target_words']}w)")
    return spec
