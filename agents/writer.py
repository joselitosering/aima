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

# Per-author form, length, and voice. DEMOTED-QUILL REDESIGN (2026-07-14, per
# Joe): Writer now OWNS word count AND full structure — Quill no longer trims
# or expands, it only verifies (see agents/quill.py). Writer has its own hard
# gate below (word_count vs range_min/range_max) so an off-target draft is
# caught here, before Quill/Maya/Vera ever spend a token on it. Ranges reset
# 2026-07-14: Joselito 1200-1500 (unchanged), Dawn 1000-1200→900-1200,
# Kenji 800-1000→500-1000.
AUTHOR_SPECS = {
    "joselito": {
        "name": "Joselito Sering", "persona_file": "joselito-sering.md",
        "form": "editorial", "range": "1200-1500 words",
        "range_min": 1200, "range_max": 1500, "target_words": 1350,
        "voice": "conviction-driven editorial — frames AI as a new creative instrument, not a shortcut",
    },
    "dawn": {
        "name": "Dawn Ginhaua", "persona_file": "dawn-ginhaua.md",
        "form": "investigative report", "range": "900-1200 words",
        "range_min": 900, "range_max": 1200, "target_words": 1050,
        "voice": "investigative, evidence-first, link-heavy — cite primary sources inline",
    },
    "kenji": {
        "name": "Kenji Nakamoto", "persona_file": "kenji-nakamoto.md",
        "form": "blog post", "range": "500-1000 words",
        "range_min": 500, "range_max": 1000, "target_words": 750,
        "voice": "optimistic, accessible blog — grounded in what the tech makes possible for real people",
    },
}

WRITER_PROMPT = (
    "You are an AIMA staff writer producing a COMPLETE, publication-ready article in your "
    "assigned persona's authentic voice. You own the final word count and full structure — "
    "Quill only verifies afterward; it does not rewrite you for length or add anything you "
    "left out. Use the provided research faithfully and cite sources; do not invent facts "
    "beyond the research (flag any gaps). Your target word range is a hard constraint, not a "
    "suggestion — stay inside it. Include every required structural element yourself: exactly "
    "5-6 <h2> section headings IN THE ARTICLE BODY (the body H2s are the ONLY <h2> tags in "
    "the entire file — do NOT put an <h2> inside <div class=\"glossary\"> or "
    "<div class=\"references\">; those divs have no heading), a stat grid (>=4 numeric "
    "cards), 1 pullquote, a glossary (>=6 data-term entries), and MLA references (>=6) — "
    "keep them concise rather than skipping them or blowing your word budget. Output clean, "
    "complete AIMA article HTML."
)


def _prose_word_count(content: str) -> int:
    """Count words in prose only — strips glossary and references first,
    same method used by Writer's gate and Quill's verifier."""
    prose = content
    for cls, end in [("glossary", "</dl>"), ("references", "</ol>")]:
        prose = re.sub(
            r'<div class="' + cls + r'">.*?' + re.escape(end) + r'\s*</div>',
            "", prose, flags=re.S,
        )
    return len(re.sub(r"<[^>]+>", " ", prose).split())


def find_draft(spec: dict) -> str | None:
    """Return the repo-relative path of an existing free-form draft for this
    spec that passes Writer's prose word-count floor, or None.

    Checked by slug+number, then number, then slug. Stale stubs from failed
    Writer runs are skipped — a file must hit the author's range_min * 0.85
    floor to be considered valid (same gate Writer's run() applies).
    """
    drafts = REPO_ROOT / DRAFTS_DIR
    if not drafts.exists():
        return None
    key = resolve_author(spec)
    a = AUTHOR_SPECS[key]
    floor = int(a["range_min"] * 0.85)

    def _valid(p: Path) -> bool:
        if not p.exists() or p.stat().st_size <= 200:
            return False
        wc = _prose_word_count(p.read_text(encoding="utf-8", errors="replace"))
        if wc < floor:
            log.info(f"[writer] find_draft: skipping stub {p.name} ({wc}w < floor {floor})")
            return False
        return True

    padded = str(spec.get("number", 0)).zfill(3)
    exact = drafts / f"{spec['slug']}-{padded}-draft.html"
    if _valid(exact):
        return f"{DRAFTS_DIR}/{exact.name}"
    for pattern in (f"*-{padded}-draft.html", f"{spec['slug']}-*draft.html"):
        for p in sorted(drafts.glob(pattern)):
            if _valid(p):
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

    # Inline persona + research CONTENT (2026-07-14) so Writer runs as one call
    # (API or CLI) instead of an agentic Read loop. Was "context-by-path".
    persona_file = f"articles/personas/{a['persona_file']}"
    try:
        persona_content = read_file(persona_file)
    except FileNotFoundError:
        persona_content = f"(persona file missing — write in {a['name']}'s voice: {a['voice']})"
    research_path = _find_research_path(spec["slug"], spec.get("number", 0))
    if research_path.exists() and research_path.stat().st_size > 100:
        research_content = read_file(research_path.relative_to(REPO_ROOT).as_posix())
    else:
        research_content = json.dumps(research, indent=2)

    user_input = f"""\
WRITER ASSIGNMENT — write as {a['name']} ({a['form']}).
You are producing the FINAL article, not a rough draft. Write freely in your own
voice, and hit the target length AND include every required structural element
yourself — Quill only verifies afterward; it will not rewrite you for length or
add anything missing.

TARGET LENGTH: {a['range']} ({a['form']}) — THIS IS A HARD CONSTRAINT. Stay inside it.
VOICE: {a['voice']}

ARTICLE SPEC (topic + tags from Priya's calendar):
{json.dumps(spec, indent=2)}

PERSONA PROFILE (fully adopt this voice):
{persona_content}

RESEARCH (use these sources/stats/quotes; cite inline; do NOT invent — flag gaps):
{research_content}

STRUCTURE — YOU must include all of these in this exact HTML, or Quill's
verification gate will reject the draft (it does not add missing pieces):
1. Lead paragraph.
2. 5-6 <h2> section headings IN THE ARTICLE BODY ONLY. These are the ONLY <h2>
   tags in the file. Do NOT use <h2> inside <div class="glossary"> or
   <div class="references"> — those divs have no heading element at all.
3. Stat grid, >=4 cards: <div class="stat-grid"><div class="stat-card">...</div>...</div>
4. Exactly one: <blockquote class="pullquote">...</blockquote>
5. Glossary, >=6 entries — EVERY <dt> MUST carry data-term="Term Name" (this
   exact attribute, not optional, not just descriptive text):
   <div class="glossary"><dl><dt data-term="Term Name">Term Name</dt><dd>Definition.</dd>...</dl></div>
   EACH glossary term MUST also appear, WORDED THE SAME WAY, somewhere in the body
   prose — only define terms you actually use in the article, so each one can be
   linked back to where it's discussed. Do not add glossary terms that never appear
   in the text.
6. >=6 references: <div class="references"><ol><li>...</li>...</ol></div>
   Where you have a source URL from the research, include it in the reference (MLA
   puts the URL at the end); the pipeline also wires Scout's source links in.

Use the Write tool to save the complete article HTML to: {draft_path}
Copy HTML only — no full skeleton, no og:image, no image tags, no markdown fences.
After the Write call succeeds, output only the single word: DRAFT_SAVED\
"""

    log.info(f"[writer] {a['name']} writing #{padded} '{spec.get('title','')[:40]}' "
             f"({a['form']}, {a['range']}) -> {draft_path}")
    raw = call_cc_agent(key, WRITER_PROMPT, user_input)

    full = REPO_ROOT / draft_path
    if full.exists() and full.stat().st_size > 200:
        log.info(f"[writer] draft saved by agent: {draft_path}")
        saved_content = full.read_text(encoding="utf-8")
    else:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()
        write_file(draft_path, raw)
        log.info(f"[writer] draft saved from stdout: {draft_path} ({len(raw)} chars)")
        saved_content = raw

    # Word-count gate (2026-07-14, per Joe): Writer is now the primary
    # enforcement point for its own persona's word range — an off-target
    # draft is rejected HERE, before Quill/Maya/Vera ever spend a token
    # verifying/merging/QC-ing it. Mirrors the pattern Quill's own (now
    # removed) gate used to use. Article #25's Writer draft ran 2912 words
    # against a 1100 target with no gate at all to catch it.
    #
    # REVISED same day, second pass: count PROSE ONLY. The first version of
    # this gate counted the whole document — glossary (7 terms x 1-3
    # sentences) and references (8 full MLA citations) add several hundred
    # words of text that isn't prose. That let a genuinely-short draft
    # (actual narrative ~747-856w per Vera's manual count) register as
    # 1191w and pass the gate, which is why word count was STILL Vera's
    # #1 blocking issue even after the gate existed. Strip glossary/
    # references before counting — same end-markers (</dl>, </ol>) Maya's
    # merge already uses successfully for the same extraction.
    prose_only = saved_content
    for cls, end in [("glossary", "</dl>"), ("references", "</ol>")]:
        prose_only = re.sub(
            r'<div class="' + cls + r'">.*?' + re.escape(end) + r'\s*</div>',
            "", prose_only, flags=re.S,
        )
    text_only = re.sub(r"<[^>]+>", " ", prose_only)
    word_count = len(text_only.split())
    floor, ceiling = int(a["range_min"] * 0.85), int(a["range_max"] * 1.2)
    if not (floor <= word_count <= ceiling):
        raise RuntimeError(
            f"[writer] Word count gate: {word_count} words outside acceptable "
            f"{floor}-{ceiling} (persona range {a['range']}). Draft NOT accepted: "
            f"{draft_path}. Re-run Writer, or adjust the persona range if this "
            f"topic genuinely needs more room."
        )
    log.info(f"[writer] word count: {word_count} (range {a['range']}, "
             f"acceptable {floor}-{ceiling}) — OK")
    return draft_path
