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


def run() -> dict:
    """Build and return the article spec for the next article."""
    state = read_json("articles/aima-coworker-state.json")
    number = state["next_article_number"]

    # ── TBD trending row? Resolve the real topic BEFORE the CC run ──────────
    # Trend Scout picks a topic for the row's assigned author and writes the
    # title+category back into the calendar, so Priya reads a real row below.
    # No-op (no CC call) when the row already has a real title.
    from agents import base, trend_scout
    if base.DRY_RUN:
        log.info("[priya] DRY RUN — skipping trend_scout TBD check")
    elif trend_scout.resolve_tbd_row(number):
        log.info(f"[priya] trend_scout resolved TBD row #{number} — calendar updated")

    calendar = read_file("articles/aima-editorial-calendar.md")

    user_input = f"""\
CURRENT STATE (aima-coworker-state.json):
{json.dumps(state, indent=2)}

EDITORIAL CALENDAR (aima-editorial-calendar.md):
{calendar}

Build and return the article spec JSON for article #{number}.
Resolve the author from the calendar row's Author column (last column).
The output JSON MUST use exactly these keys:
  number, slug, filename, og_image, title, author, category,
  read_time, publish_date, tone, mood, custom_tags, target_words

Return ONLY the JSON object. No markdown fences. No explanation.\
"""

    log.info(f"[priya] building spec for article #{number}")
    raw_text = call_cc_agent("priya", PRIYA_PROMPT, user_input)

    # Strip markdown fences if the CC CLI added them
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"```[a-z]*\n?", "", raw_text).strip().rstrip("`").strip()

    # Extract JSON object if surrounded by prose
    start = raw_text.index("{")
    end = raw_text.rindex("}") + 1
    raw_spec = json.loads(raw_text[start:end])

    log.info(f"[priya] raw spec keys: {list(raw_spec.keys())}")
    spec = _normalize_spec(raw_spec, state)

    log.info(f"[priya] spec ready: #{spec['number']} '{spec['title']}' → {spec['filename']}")
    return spec
