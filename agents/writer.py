"""Writer — free-form persona authors (CC subagents).

Joselito / Dawn / Kenji write a full article in their own voice and natural length
from Priya's topic + Scout's research. Output is the AIMA HTML draft, saved to
articles/drafts/ for Quill (the EDITOR) to pick up and refine in the full pipeline.

Writers do NOT research (that's Scout) and do NOT edit to Vera's checklist (that's
Quill). They write great reading material — a 'pure journal' in the author's voice.
"""

import json
import re
from pathlib import Path

from agents.base import call_cc_agent, read_file, write_file, REPO_ROOT, log
from agents.scout import _find_research_path

DRAFTS_DIR = "articles/drafts"

# Per-author form, length, and voice. Length drives the writer; Quill (editor)
# later trims/expands to Vera's checklist.
# Per-author form, length, and voice. Ranges lowered 2026-07-04 (Joe) to cut
# per-article tokens: Joselito 1800+→1200-1500, Dawn 1200-1500→1000-1200,
# Kenji 900-1200→800-1000. The finished-article length that these drive is also
# what Marco caps the merged/edit word target to (agents/marco.py Stage 3), so
# articles no longer balloon back past persona length.
AUTHOR_SPECS = {
    "joselito": {
        "name": "Joselito Sering", "persona_file": "joselito-sering.md",
        "form": "editorial", "range": "1200-1500 words", "target_words": 1350,
        "voice": "conviction-driven editorial — frames AI as a new creative instrument, not a shortcut",
    },
    "dawn": {
        "name": "Dawn Ginhaua", "persona_file": "dawn-ginhaua.md",
        "form": "investigative report", "range": "1000-1200 words", "target_words": 1100,
        "voice": "investigative, evidence-first, link-heavy — cite primary sources inline",
    },
    "kenji": {
        "name": "Kenji Nakamoto", "persona_file": "kenji-nakamoto.md",
        "form": "blog post", "range": "800-1000 words", "target_words": 900,
        "voice": "optimistic, accessible blog — grounded in what the tech makes possible for real people",
    },
}

WRITER_PROMPT = (
    "You are an AIMA staff writer producing a free-form article in your assigned persona's "
    "authentic voice. Your job is GREAT READING MATERIAL, not QC compliance — the editor "
    "(Quill) will trim, expand, and on-brand it later. Use the provided research faithfully "
    "and cite sources; do not invent facts beyond the research (flag any gaps). Hit the target "
    "length and form for your persona. Output clean AIMA article HTML."
)


def find_draft(spec: dict) -> str | None:
    """Return the repo-relative path of an existing free-form draft for this
    spec, or None. Checked by slug+number, then number, then slug — used by
    Marco's WRITE stage (skip-and-reuse: an existing draft is never re-written)."""
    drafts = REPO_ROOT / DRAFTS_DIR
    if not drafts.exists():
        return None
    padded = str(spec.get("number", 0)).zfill(3)
    exact = drafts / f"{spec['slug']}-{padded}-draft.html"
    if exact.exists() and exact.stat().st_size > 200:
        return f"{DRAFTS_DIR}/{exact.name}"
    for pattern in (f"*-{padded}-draft.html", f"{spec['slug']}-*draft.html"):
        for p in sorted(drafts.glob(pattern)):
            if p.stat().st_size > 200:
                return f"{DRAFTS_DIR}/{p.name}"
    return None


def resolve_author(spec: dict, author: str | None = None) -> str:
    """Pick the writer key: explicit --author, else map the spec's assigned author
    name to a key, else default to joselito."""
    if author and author.lower() in AUTHOR_SPECS:
        return author.lower()
    name = (spec.get("author") or "").lower()
    for key, a in AUTHOR_SPECS.items():
        if a["name"].lower() in name or key in name:
            return key
    return "joselito"


def run(spec: dict, research: dict, author: str | None = None) -> str:
    """Write a free-form HTML draft in the author's voice. Returns the draft path
    (relative to repo root). Caller must ensure research exists — writers do not research."""
    key = resolve_author(spec, author)
    a = AUTHOR_SPECS[key]
    slug = spec["slug"]
    padded = str(spec.get("number", 0)).zfill(3)
    draft_path = f"{DRAFTS_DIR}/{slug}-{padded}-draft.html"

    # Context-by-path: pass big context as FILE PATHS for the agent to Read
    # rather than inlining text. Removed aima-coworker-prompt.md (18KB HTML
    # template — Maya's job, not Writer's). Inline 10-line structure spec
    # instead so Writer knows the shape without loading the full skeleton.
    # (2026-07-13, part of Direction B revert + format guide removal.)
    persona_file = f"articles/personas/{a['persona_file']}"
    research_path = _find_research_path(spec["slug"], spec.get("number", 0))
    if research_path.exists() and research_path.stat().st_size > 100:
        research_ref = ("- RESEARCH (use these sources/stats/quotes; cite inline): "
                        f"{research_path.relative_to(REPO_ROOT).as_posix()}")
    else:
        # No research file on disk — inline whatever we were handed so the
        # no-fabrication rule still has something to check against.
        research_ref = ("RESEARCH (none on disk — use ONLY what is inlined here; "
                        "flag every gap, do not invent):\n" + json.dumps(research, indent=2))

    user_input = f"""\
WRITER ASSIGNMENT — write as {a['name']} ({a['form']}).
You are the WRITER, not the editor. Write freely in your own voice to make great
reading material. Do NOT optimize for the strict QC checklist — Quill (the editor)
refines it afterward.

TARGET LENGTH: {a['range']} ({a['form']}).
VOICE: {a['voice']}

ARTICLE SPEC (topic + tags from Priya's calendar):
{json.dumps(spec, indent=2)}

READ THESE FILES FIRST with your Read tool (on disk; do NOT skip any):
- PERSONA PROFILE (fully adopt this voice): {persona_file}
{research_ref}

STRUCTURE (Quill enforces; aim for this order so edits are minimal):
lead → 5-6 H2 sections → stat grid (>=4 numeric cards) → pullquote → glossary (>=6 data-term) → MLA references (>=6)
Output copy HTML only — no full skeleton, no og:image, no image tags.

Write the complete article HTML now and save it to: {draft_path}
Then return the HTML to stdout.\
"""

    log.info(f"[writer] {a['name']} writing #{padded} '{spec.get('title','')[:40]}' "
             f"({a['form']}, {a['range']}) -> {draft_path}")
    raw = call_cc_agent(key, WRITER_PROMPT, user_input)

    full = REPO_ROOT / draft_path
    if full.exists() and full.stat().st_size > 200:
        log.info(f"[writer] draft saved by agent: {draft_path}")
        return draft_path

    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()
    write_file(draft_path, raw)
    log.info(f"[writer] draft saved from stdout: {draft_path} ({len(raw)} chars)")
    r