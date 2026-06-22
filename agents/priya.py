"""Priya — Calendar Manager.

Reads the editorial calendar and state file, then asks Claude to build
a complete article spec JSON and hand it to Marco.
"""

import json
import re

from agents.base import call_agent, read_json, read_file, log

SYSTEM = """\
You are the Calendar Manager for AIMA Magazine.
Your job is to read the editorial calendar and give
Marco a complete, accurate article spec. That's it.

READ:
- aima-editorial-calendar.md
  → row matching next_article_number
- aima-coworker-state.json
  → next_article_number, next_track, persona indexes

RESOLVE AUTHOR:
- joselito track: Joselito Sering
- trending track: rotate dawn → kenji → dawn
  Use the persona's post_count to find their next calendar slot (D1, D2... or K1, K2...).
  If the title is TBD, pick a sharp, timely AI trending topic that fits Dawn or Kenji's voice.

BUILD article spec and return it as raw JSON (no markdown, no explanation):
{
  "number": N,
  "slug": "aima-NNN-slug",
  "filename": "aima-NNN-slug.html",
  "og_image": "img/articles/aima-NNN-slug.jpg",
  "title": "...",
  "author": "...",
  "category": "...",
  "read_time": "N min",
  "publish_date": "YYYY-MM-DD",
  "tone": "...",
  "mood": "...",
  "custom_tags": ["...", "..."]
}

FIELD RULES:
- number: the next_article_number from state
- slug: aima-NNN-slug where NNN is zero-padded to 3 digits and slug is a short hyphenated version of the title (max 6 words)
- filename: slug + ".html"
- og_image: "img/articles/" + slug + ".jpg"
- read_time: from the calendar row; if missing, estimate from category
- publish_date: next_article_date from state
- tone: writing register derived from the calendar tone note (analytical, conversational, provocative, optimistic, investigative…)
- mood: emotional texture derived from the tone note (urgent, hopeful, critical, challenging, awe-inspiring…)
- custom_tags: 3-5 article-specific hashtags beyond the default AIMA set — match the article's topic precisely

Return ONLY the JSON object. No markdown fences. No explanation.\
"""


def run() -> dict:
    """Build and return the article spec for the next article."""
    state = read_json("articles/aima-coworker-state.json")
    calendar = read_file("articles/aima-editorial-calendar.md")

    user = f"""\
CURRENT STATE (aima-coworker-state.json):
{json.dumps(state, indent=2)}

EDITORIAL CALENDAR (aima-editorial-calendar.md):
{calendar}

Build and return the article spec JSON for article #{state['next_article_number']}.
"""

    log.info(f"[priya] building spec for article #{state['next_article_number']} (track={state['next_track']})")
    raw = call_agent("priya", SYSTEM, user)

    # Strip markdown fences if Claude added them
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()

    spec = json.loads(raw)
    log.info(f"[priya] spec ready: {spec.get('slug')} / author={spec.get('author')}")
    return spec
