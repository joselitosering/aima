"""Scout — Research Agent (CC subagent).

Receives article spec from Marco, fetches scout-sources.json,
then builds a structured research JSON and saves it.
"""

import json
import re

from agents.base import call_cc_agent, read_json, write_json, log
from agents.prompts import SCOUT_PROMPT


def run(spec: dict) -> dict:
    """
    Research the article defined by spec.
    Saves research to articles/research/[slug]-research.json.
    Returns the research dict.
    """
    slug = spec["slug"]
    sources_config = read_json("scout-sources.json")

    user_input = f"""\
ARTICLE SPEC:
{json.dumps(spec, indent=2)}

SCOUT SOURCES CONFIG (scout-sources.json):
{json.dumps(sources_config, indent=2)}

Research this article. Check the scout-sources.json feeds and APIs first,
then supplement with web search. Save your output to:
  articles/research/{slug}-research.json

Return the research JSON object directly (no markdown fences, no explanation).\
"""

    log.info(f"[scout] researching: {slug}")
    raw = call_cc_agent("scout", SCOUT_PROMPT, user_input)

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()

    # Extract JSON object
    start = raw.index("{")
    end = raw.rindex("}") + 1
    research = json.loads(raw[start:end])

    # Persist (Scout may have already saved it; write ensures consistency)
    write_json(f"articles/research/{slug}-research.json", research)
    log.info(f"[scout] research saved: articles/research/{slug}-research.json")
    return research
