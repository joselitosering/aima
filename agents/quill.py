"""Quill — Senior Writer (CC subagent).

Receives spec + research from Marco, reads the persona profile
and format guide, then writes copy-only article HTML.
"""

import json
from pathlib import Path

from agents.base import call_cc_agent, read_json, read_file, REPO_ROOT, log
from agents.prompts import QUILL_PROMPT


def _persona_filename(author: str) -> str:
    """Convert author display name to persona profile filename."""
    return author.lower().replace(" ", "-") + ".md"


def _find_previous_article(spec: dict) -> tuple[str, str]:
    """Return (prev_url, prev_title) for the article before this one."""
    articles_dir = REPO_ROOT / "articles"
    number = spec.get("number", 1)
    prev_number = number - 1
    if prev_number < 1:
        return "", ""

    pattern = f"aima-{prev_number:03d}-*.html"
    matches = sorted(articles_dir.glob(pattern))
    if not matches:
        return "", ""

    prev_html = matches[-1].read_text(encoding="utf-8")
    # Extract title from <title> tag
    import re
    title_match = re.search(r"<title>([^<]+)</title>", prev_html)
    prev_title = title_match.group(1).strip() if title_match else ""
    prev_url = f"articles/{matches[-1].name}"
    return prev_url, prev_title


def run(spec: dict, research: dict) -> str:
    """
    Write the article HTML (copy only — no images, no skeleton).
    Returns the path to the saved article file (relative to repo root).
    """
    slug = spec["slug"]
    filename = spec["filename"]
    author = spec["author"]

    persona_file = f"articles/personas/{_persona_filename(author)}"
    try:
        persona = read_file(persona_file)
    except FileNotFoundError:
        persona = f"[Persona profile not found at {persona_file} — write in a neutral, analytical voice.]"

    try:
        format_guide = read_file("articles/aima-coworker-prompt.md")
    except FileNotFoundError:
        format_guide = "[Format guide not found — use standard AIMA article structure.]"

    prev_url, prev_title = _find_previous_article(spec)

    user_input = f"""\
ARTICLE SPEC:
{json.dumps(spec, indent=2)}

RESEARCH:
{json.dumps(research, indent=2)}

FORMAT GUIDE (aima-coworker-prompt.md):
{format_guide}

AUTHOR PERSONA ({persona_file}):
{persona}

PREVIOUS ARTICLE:
  prev-url: {prev_url}
  prev-title: {prev_title}

Write the article HTML (copy only). Save it to: articles/{filename}
Return the file path: articles/{filename}\
"""

    log.info(f"[quill] writing article: {filename} ({spec.get('target_words', 1600)} words)")
    call_cc_agent("quill", QUILL_PROMPT, user_input)

    article_path = f"articles/{filename}"
    log.info(f"[quill] article saved: {article_path}")
    return article_path
