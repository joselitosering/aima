"""Quill — PURE PYTHON VERIFICATION GATE.

Demoted from LLM editor to a pure Python gate 2026-07-14 (per Joe) after the
article #20 QL token explosion (2.9M tok, $2.52, 57 turns). The "Restored as
LLM editor 2026-07-17" note in earlier versions of this docstring was stale —
the API fix path was never implemented. Quill does NOT call any LLM.

Design contract (2026-07-14, confirmed 2026-07-21):
- Writer owns structure and word count. It must deliver a correct draft.
- Quill verifies the draft against Vera's checklist in pure Python, $0.
- If the draft fails: Quill halts and Marco surfaces the problem. No auto-fix.
- Only catastrophically empty drafts (< MIN_FIXABLE_WORDS) are even worth
  halting on — clean drafts pass through unchanged.

Structural errors (wrong H2 count, missing stat grid, etc.) are Writer prompt
failures. Fix them in Writer's prompt and user_input, not here.
"""

import re

from agents.base import read_file, write_file, REPO_ROOT, log
from agents.writer import AUTHOR_SPECS, resolve_author

MIN_FIXABLE_WORDS = 200  # below this Quill cannot patch — Writer must rerun


def run(spec: dict, research: dict, extra_instruction: str = "",
        force_rewrite: bool = False, draft_path: str | None = None) -> str:
    """
    Verify Writer's draft meets spec (word count + structure) in pure Python
    and save it as the final article copy, unchanged. Returns the saved article
    path (relative to repo root).

    Raises RuntimeError if the draft fails any check. Structural failures are
    Writer prompt failures — fix them in agents/writer.py, not here.
    extra_instruction is accepted for call-signature compatibility with Marco
    but is not used.
    """
    filename = spec["filename"]
    article_path = f"articles/{filename}"
    article_full = REPO_ROOT / article_path

    if not force_rewrite and article_full.exists() and article_full.stat().st_size > 1000:
        log.info(f"[quill] reusing existing article (skipping verification): {filename}")
        return article_path

    if not draft_path or not (REPO_ROOT / draft_path).exists():
        raise RuntimeError(
            f"[quill] No draft_path provided or file missing: {draft_path}. "
            "Quill no longer authors from scratch — Writer must run first."
        )

    draft_content = read_file(draft_path)

    # Strip glossary and references before counting — matches writer.py's
    # prose-only gate. Without this, glossary+refs add ~300 words and cause
    # Quill to reject drafts that Writer already accepted as in-range.
    prose_only = draft_content
    for cls, end in [("glossary", "</dl>"), ("references", "</ol>")]:
        prose_only = re.sub(
            r'<div class="' + cls + r'">.*?' + re.escape(end) + r'\s*</div>',
            "", prose_only, flags=re.S,
        )
    text_only = re.sub(r"<[^>]+>", " ", prose_only)
    word_count = len(text_only.split())

    h2_count = len(re.findall(r"<h2[\s>]", draft_content, re.I))
    stat_cards = len(re.findall(r'class="stat-card"', draft_content, re.I))
    has_pullquote = 'class="pullquote"' in draft_content
    glossary_terms = len(re.findall(r'data-term="', draft_content, re.I))
    refs_section = re.search(r'<div class="references">.*?<ol>(.*?)</ol>',
                             draft_content, re.I | re.S)
    ref_count = len(re.findall(r"<li>", refs_section.group(1), re.I)) if refs_section else 0

    wa = AUTHOR_SPECS[resolve_author(spec)]
    range_min, range_max = wa["range_min"], wa["range_max"]
    floor, ceiling = int(range_min * 0.85), int(range_max * 1.2)

    problems = []
    if not (floor <= word_count <= ceiling):
        problems.append(f"word count {word_count} outside acceptable {floor}-{ceiling} "
                        f"(persona range {range_min}-{range_max})")
    if not (5 <= h2_count <= 6):
        problems.append(f"{h2_count} H2 sections (need 5-6)")
    if stat_cards < 4:
        problems.append(f"{stat_cards} stat cards (need >=4)")
    if not has_pullquote:
        problems.append("no pullquote found")
    if glossary_terms < 6:
        problems.append(f"{glossary_terms} glossary terms (need >=6)")
    if ref_count < 6:
        problems.append(f"{ref_count} references (need >=6)")

    if problems:
        raise RuntimeError(
            f"[quill] Draft incomplete, HALTING (Writer must fix — Quill does not "
            f"auto-rewrite): {'; '.join(problems)}. Draft at: {draft_path}"
        )

    write_file(article_path, draft_content)
    log.info(f"[quill] verified clean ({word_count}w, {h2_count} H2, {stat_cards} stat "
             f"cards, {glossary_terms} glossary terms, {ref_count} refs) — "
             f"passed through unchanged, $0")
    return article_path
