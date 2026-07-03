"""Quill — EDITOR (CC subagent).

Receives spec + research from Marco. When a free-form writer draft exists
(articles/drafts/, produced by the Writer stage or the writer batch), Quill
EDITS it into Vera-checklist-compliant copy-only HTML, preserving the
author's voice. When no draft exists, Quill falls back to writing the copy
from scratch (persona profile + format guide).
"""

import json
from pathlib import Path

from agents.base import call_cc_agent, read_json, read_file, write_file, REPO_ROOT, log
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


def run(spec: dict, research: dict, extra_instruction: str = "",
        force_rewrite: bool = False, draft_path: str | None = None) -> str:
    """
    Produce the article HTML (copy only — no images, no skeleton).
    EDIT mode when draft_path points to a writer draft; otherwise writes
    from scratch. Returns the saved article path (relative to repo root).
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

    draft_html = ""
    if draft_path:
        try:
            draft_html = read_file(draft_path)
        except FileNotFoundError:
            log.warning(f"[quill] draft_path given but missing: {draft_path} — writing from scratch")
            draft_path = None

    if draft_path:
        task_section = f"""\
WRITER DRAFT ({draft_path}) — EDIT THIS, do not write from scratch:
{draft_html}

YOUR TASK — EDIT the draft into the final copy-only article HTML:
- PRESERVE the author's voice, argument, and best lines — you are the editor,
  not a second author.
- Enforce the QC structure: 5-6 H2 sections, stat grid (>= 4 numeric cards),
  1 pullquote, >= 6 glossary terms (data-term), >= 6 MLA references.
- Keep every fact/citation consistent with the RESEARCH above; cut anything
  the research cannot support.
- Hit the word target below (trim or expand as needed)."""
    else:
        task_section = "Write the article HTML (copy only)."

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

WORD COUNT ENFORCEMENT (from Cora):
{extra_instruction if extra_instruction else f"Write {spec.get('target_words', 1600)} words (±50). Hard ceiling: 1800 words."}

{task_section}
Output ONLY the raw HTML — start with <!DOCTYPE html> or <html>.
Do NOT include any prose, explanation, or markdown fences before or after the HTML.
Do NOT git add, commit, or push — Marco handles file I/O.\
"""

    article_path = f"articles/{filename}"
    article_full = REPO_ROOT / article_path

    if not force_rewrite:
        # Skip CC call if article already exists (exact match or same article number).
        # Handles the case where Priya returned a different slug on a previous run.
        if article_full.exists() and article_full.stat().st_size > 1000:
            log.info(f"[quill] reusing existing article (skipping CC call): {filename}")
            return article_path

        padded = str(spec.get("number", 0)).zfill(3)
        matches = sorted(
            (REPO_ROOT / "articles").glob(f"aima-article-*-{padded}.html"),
            key=lambda p: p.stat().st_size, reverse=True,
        )
        if matches and matches[0].stat().st_size > 1000:
            found = f"articles/{matches[0].name}"
            log.info(f"[quill] reusing existing article by number (skipping CC call): {matches[0].name}")
            return found

    import time as _time
    call_start = _time.time()

    mode = f"editing draft {draft_path}" if draft_path else "writing from scratch"
    log.info(f"[quill] {mode} -> {filename} ({spec.get('target_words', 1600)} words)")
    raw_html = call_cc_agent("quill", QUILL_PROMPT, user_input)

    # CC subagents can write files directly with their Write tool.
    # Verify by mtime >= call_start so a pre-existing Maya file doesn't
    # fool us into thinking the CC agent wrote the revision.
    if (article_full.exists() and article_full.stat().st_size > 500
            and article_full.stat().st_mtime >= call_start):
        log.info(f"[quill] CC agent wrote article directly: {filename}")
        return article_path

    # Fallback: strip any accidental markdown fences and save stdout
    import re as _re
    raw_html = raw_html.strip()
    if raw_html.startswith("```"):
        raw_html = _re.sub(r"```[a-z]*\n?", "", raw_html).strip().rstrip("`").strip()

    if len(raw_html) < 500:
        raise RuntimeError(
            f"[quill] CC output too short to be an article ({len(raw_html)} chars). "
            f"First 300 chars: {raw_html[:300]}"
        )

    write_file(article_path, raw_html)
    log.info(f"[quill] article saved from stdout: {article_path} ({len(raw_html)} chars)")
    return article_path
