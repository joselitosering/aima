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

DRAFTS_DIR = "articles/drafts"

# Per-author form, length, and voice. Length drives the writer; Quill (editor)
# later trims/expands to Vera's checklist.
AUTHOR_SPECS = {
    "joselito": {
        "name": "Joselito Sering", "persona_file": "joselito-sering.md",
        "form": "editorial", "range": "1800+ words", "target_words": 1900,
        "voice": "conviction-driven editorial — frames AI as a new creative instrument, not a shortcut",
    },
    "dawn": {
        "name": "Dawn Ginhaua", "persona_file": "dawn-ginhaua.md",
        "form": "investigative report", "range": "1200-1500 words", "target_words": 1350,
        "voice": "investigative, evidence-first, link-heavy — cite primary sources inline",
    },
    "kenji": {
        "name": "Kenji Nakamoto", "persona_file": "kenji-nakamoto.md",
        "form": "blog post", "range": "900-1200 words", "target_words": 1050,
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

    try:
        persona = read_file(f"articles/personas/{a['persona_file']}")
    except FileNotFoundError:
        persona = f"[Persona profile not found — write as {a['name']}: {a['voice']}.]"
    try:
        format_guide = read_file("articles/aima-coworker-prompt.md")
    except FileNotFoundError:
        format_guide = "[Format guide not found — use the standard AIMA article HTML structure.]"

    user_input = f"""\
WRITER ASSIGNMENT — write as {a['name']} ({a['form']}).
You are the WRITER, not the editor. Write freely in your own voice to make great
reading material. Do NOT optimize for the strict QC checklist — Quill (the editor)
refines it afterward.

TARGET LENGTH: {a['range']} ({a['form']}).
VOICE: {a['voice']}

ARTICLE SPEC (topic + tags from Priya's calendar):
{json.dumps(spec, indent=2)}

RESEARCH (from Scout — use these sources/stats/quotes; cite inline):
{json.dumps(research, indent=2)}

PERSONA PROFILE:
{persona}

HTML FORMAT REFERENCE (produce the AIMA article HTML; the editor will refine):
{format_guide}

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
    return draft_path
