"""Quill — EDITOR (CC subagent).

Receives spec + research + a Writer draft from Marco. Edits the draft into
Vera-checklist-compliant copy-only HTML, preserving the author's voice.

Marco always provides a draft_path (Writer.run() runs before Quill in the full
pipeline since 2026-07-13 revert of Direction B). If draft_path is None, Quill
falls back to authoring from scratch — but this path should not occur in normal
full-pipeline runs. The standalone Writer batch (run_writer_batch.py) can also
pre-stage drafts that Quill edits without a fresh Writer CC call.
"""

import json
from pathlib import Path

from agents.base import call_cc_agent, read_json, read_file, write_file, REPO_ROOT, log
from agents.prompts import QUILL_PROMPT
from agents.writer import AUTHOR_SPECS, resolve_author
from agents.scout import _find_research_path


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

    # Context-by-path: pass big context as FILE PATHS for the agent to Read.
    # Removed aima-coworker-prompt.md (18KB HTML template) from Quill's context
    # entirely — that's Maya's job. Quill's job is edit-to-spec, which only
    # needs the persona voice and the research to verify citations against.
    # (2026-07-13, part of Direction B revert + format guide removal.)
    persona_file = f"articles/personas/{_persona_filename(author)}"

    research_path = _find_research_path(spec["slug"], spec.get("number", 0))
    if research_path.exists() and research_path.stat().st_size > 100:
        research_ref = ("- RESEARCH (verify every stat/quote against this file): "
                        f"{research_path.relative_to(REPO_ROOT).as_posix()}")
    else:
        # No research file on disk — inline whatever dict we were handed so the
        # no-fabrication guardrail still has something to check against.
        research_ref = ("RESEARCH (none on disk — use ONLY what is inlined here; "
                        "flag every gap, do not invent):\n" + json.dumps(research, indent=2))

    prev_url, prev_title = _find_previous_article(spec)

    # Confirm the draft file is really on disk before telling the agent to read it.
    if draft_path and not (REPO_ROOT / draft_path).exists():
        log.warning(f"[quill] draft_path given but missing: {draft_path} — authoring from scratch")
        draft_path = None

    # Direction B removed (2026-07-13): Quill is now EDIT-ONLY. Marco always
    # runs Writer first, so draft_path should always be present in the full
    # pipeline. The no-draft fallback is kept as a safety net but should not
    # normally trigger.
    if draft_path:
        task_section = f"""\
WRITER DRAFT to EDIT — read it with your Read tool; do NOT write from scratch: {draft_path}

YOUR TASK — EDIT that draft into the final copy-only article HTML:
- PRESERVE the author's voice, argument, and best lines — you are the editor,
  not a second author.
- Enforce the QC structure: 5-6 H2 sections, stat grid (>= 4 numeric cards),
  1 pullquote, >= 6 glossary terms (data-term), >= 6 MLA references.
- Keep every fact/citation consistent with the RESEARCH file; cut anything
  the research cannot support.
- Hit the word target below (trim or expand as needed)."""
    else:
        # Fallback only — should not occur in full-pipeline runs (Marco runs Writer first).
        wa = AUTHOR_SPECS[resolve_author(spec)]
        task_section = f"""\
NO WRITER DRAFT EXISTS (fallback) — write AND edit in one pass as {wa['name']}:
Voice: {wa['voice']}. Form: {wa['form']}. Range: {wa['range']}.
Use the RESEARCH file faithfully; do NOT invent — flag gaps.
Enforce QC structure: 5-6 H2 sections, stat grid (>= 4 numeric cards),
1 pullquote, >= 6 glossary terms (data-term), >= 6 MLA references.
Hit the word target below."""

    user_input = f"""\
ARTICLE SPEC:
{json.dumps(spec, indent=2)}

READ THESE FILES FIRST with your Read tool (on disk; do NOT skip any):
- AUTHOR PERSONA (fully adopt this voice): {persona_file}
{research_ref}

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

    mode = f"editing draft {draft_path}" if draft_path else "authoring+editing (no draft — fallback)"
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

    # Word count gate (Task #4, 2026-07-13): reject articles that are
    # massively over the persona's word ceiling before saving. Quill wrote
    # 3,718 words vs a 900-word target on article #20 — no mechanical check
    # caught it. This gate uses a 1.5× multiplier (soft) to catch outliers
    # without triggering on normal ±10% Vera variance. Hard ceiling is 1.8×
    # so even a generous overrun is caught before it reaches Vera / Porter.
    # We count visible words by stripping HTML tags — close enough for a gate.
    import re as _re2
    text_only = _re2.sub(r"<[^>]+>", " ", raw_html)
    word_count = len(text_only.split())
    target = spec.get("target_words", 1600)
    hard_ceiling = int(target * 1.8)
    if word_count > hard_ceiling:
        raise RuntimeError(
            f"[quill] Word count gate: {word_count} words exceeds hard ceiling "
            f"({hard_ceiling} = {target} × 1.8). Article NOT saved. "
            f"Check QUILL_PROMPT word target instruction and --max-turns cap."
        )
    log.info(f"[quill] word count: {word_count} (target={target}, ceiling={hard_ceiling}) — OK")

    write_file(article_path, raw_html)
    log.info(f"[quill] article saved from stdout: {article_path} ({len(raw_html)} chars)")
    return article_path
                                                                                                                                                                                                                                               