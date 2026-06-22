"""Priya — Calendar Manager (CC subagent).

Reads the editorial calendar and state file, then builds
a complete article spec JSON for Marco.
"""

import json
import re

from agents.base import call_cc_agent, read_json, read_file, log
from agents.prompts import PRIYA_PROMPT


def run() -> dict:
    """Build and return the article spec for the next article."""
    state = read_json("articles/aima-coworker-state.json")
    calendar = read_file("articles/aima-editorial-calendar.md")

    user_input = f"""\
CURRENT STATE (aima-coworker-state.json):
{json.dumps(state, indent=2)}

EDITORIAL CALENDAR (aima-editorial-calendar.md):
{calendar}

Build and return the article spec JSON for article #{state['next_article_number']}.
Return ONLY the JSON object. No markdown fences. No explanation.\
"""

    log.info(f"[priya] building spec for article #{state['next_article_number']} (track={state.get('next_track')})")
    raw = call_cc_agent("priya", PRIYA_PROMPT, user_input)

    # Strip markdown fences if the CC CLI added them
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()

    # Extract JSON object if surrounded by prose
    start = raw.index("{")
    end = raw.rindex("}") + 1
    spec = json.loads(raw[start:end])

    log.info(f"[priya] spec ready: {spec.get('slug')} / author={spec.get('author')}")
    return spec
