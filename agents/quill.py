"""Quill — EDITOR (CC subagent).

Receives spec + research from Marco. When a free-form writer draft exists
(articles/drafts/, produced by the standalone writer batch), Quill EDITS it
into Vera-checklist-compliant copy-only HTML, preserving the author's voice.

When no draft exists, Quill AUTHORS then EDITS in one CC call (two phases:
write freely in the row author's persona voice, then edit that draft to the QC
checklist). This is the Direction B merge (2026-07-04): the full pipeline no
longer spends a separate cold `claude` subprocess on the Writer stage plus a
second one here — it collapses both into this single call for from-scratch
articles, removing one cold-start per article while keeping the write/edit
separation intact. The standalone Writer batch (run_writer_batch.py →
writer.run()) is unchanged and still pre-stages drafts that this EDIT path reuses.
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

    # Context-by-path (2026-07-04): pass the big context (research, format guide,
    # persona, and any writer draft) as FILE PATHS for the agent to Read, instead
    # of inlining their full text into user_input. Inlined text sits in the prompt
    # prefix that is re-processed as cache_read on every tool turn — the dominant
    # token term in a merged authoring call. A small user_input shrinks the initial
    # cache-creation and lets the agent read only what it needs (same "pass the
    # path, not the content" pattern Maya already uses for the article file).
    persona_file = f"articles/personas/{_persona_filename(author)}"
    format_guide_path = "articles/aima-coworker-prompt.md"

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
        # Direction B (2026-07-04): no pre-staged Writer draft exists, so rather
        # than spend one cold `claude` subprocess on the Writer stage and a
        # SECOND one here on Quill, this single call AUTHORS then EDITS in two
        # phases. That preserves the deliberate write-freely / edit-to-checklist
        # separation the two stages had — it just no longer pays two cold-starts
        # (see HANDOFF.md 2026-07-04, recommended fix #2). The author's form,
        # length, and voice come from the Writer stage's own persona spec so the
        # authored draft matches what the standalone Writer batch would produce.
        wa = AUTHOR_SPECS[resolve_author(spec)]
        task_section = f"""\
NO WRITER DRAFT EXISTS — author AND edit in one pass, in two phases:

PHASE 1 — WRITE (as {wa['name']}, {wa['form']}, ~{wa['range']}):
Draft the article freely in this persona's authentic voice. Voice: {wa['voice']}.
Use the RESEARCH file faithfully and cite sources inline; do NOT invent facts
beyond it — flag any gap rather than filling it.

PHASE 2 — EDIT your own Phase-1 draft into the final copy-only article HTML:
- PRESERVE the voice, argument, and best lines you just wrote — you are now the editor.
- Enforce the QC structure: 5-6 H2 sections, stat grid (>= 4 numeric cards),
  1 pullquote, >= 6 glossary terms (data-term), >= 6 MLA references.
- Keep every fact/citation consistent with the RESEARCH file; cut anything it can't support.
- Hit the word target below (trim or expand as needed)."""

    user_input = f"""\
ARTICLE SPEC:
{json.dumps(spec, indent=2)}

READ THESE FILES FIRST with your Read tool (on disk; do NOT skip any):
- FORMAT GUIDE (AIMA article HTML structure to follow): {format_guide_path}
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

    mode = f"editing draft {draft_path}" if draft_path else "authoring+editing in one call (Writer merged)"
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
