"""Quill — VERIFICATION GATE (pure Python, no LLM).

DEMOTED 2026-07-14 (per Joe): Writer now owns word count, voice, AND full
structure (5-6 H2, stat grid >=4, pullquote, glossary >=6, references >=6) —
Writer has its own hard gate for all of this (agents/writer.py). Quill no
longer authors, rewrites, trims, or expands. Its only job is to verify
Writer's draft still meets spec and pass it through as the final article
copy, unchanged.

No CC call in the normal path — $0, always. If a draft is genuinely
incomplete, Quill HALTS and reports (same philosophy Vera already uses:
report to Marco/Iris/Joe, do not silently rewrite or auto-iterate).

Why pure Python and not Haiku: article #25's rejected Writer draft (still on
disk in articles/drafts/ at the time of this rewrite) already contained every
required structural element — 5 H2s, 6 stat cards, 1 pullquote, 8 glossary
terms, 9 references. A properly-gated Writer reliably produces complete
output; there was no real evidence a generative patch step is needed. If
that changes in practice (halts become frequent for missing-but-fixable
pieces), a narrow Haiku patch call is the next lever — not built here,
not needed yet.

Previously a Sonnet CC call costing ~$1.30-1.96/article. Article #20 hit
2.9M tokens/$2.52 in a 57-turn loop; article #25's attempt hit 2912 words
against a 1100 target because the old prompt explicitly permitted "trim or
expand as needed."
"""

import re

from agents.base import read_file, write_file, REPO_ROOT, log
from agents.writer import AUTHOR_SPECS, resolve_author


def run(spec: dict, research: dict, extra_instruction: str = "",
        force_rewrite: bool = False, draft_path: str | None = None) -> str:
    """
    Verify Writer's draft meets spec (word count + structure) and save it as
    the final article copy, unchanged. Returns the saved article path
    (relative to repo root).

    Raises RuntimeError if the draft is incomplete — Quill reports problems,
    it does not fix them. extra_instruction is accepted for call-signature
    compatibility with Marco but is not used (nothing left to instruct).
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

    text_only = re.sub(r"<[^>]+>", " ", draft_content)
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
