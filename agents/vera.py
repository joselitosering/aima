"""Vera — Quality Gate (PURE PYTHON, no LLM).

DEMOTED 2026-07-14 (per Joe): every one of Vera's QC checks is structural /
mechanical (meta tags, counts, file existence, placeholder scan) — there is no
semantic judgment in the checklist, so a deterministic Python gate does the same
job for $0, can't rate-limit or flake during an unattended run, and gives a
reproducible verdict. The one genuinely-semantic check (do the article's stats
actually match the research?) lives in Cora, which stays an LLM call.

Vera runs on the MERGED article (after Maya), so it verifies the things Quill's
pre-merge gate cannot: head meta tags, the og:image file on disk, and that the
structure survived the skeleton merge. Guardrail preserved: Vera HALTS + reports
(returns a needs_revision verdict); it never rewrites or re-runs anything.
"""

import re
from pathlib import Path

from agents.base import read_file, REPO_ROOT, log
from agents.writer import AUTHOR_SPECS, resolve_author

# Possible verdicts Vera returns (unchanged interface for Marco)
VERDICT_APPROVED = "approved"
VERDICT_COPY = "needs_revision: copy"
VERDICT_VISUAL = "needs_revision: visual"

# 9 required meta tags (property= or name=), each must be present + non-empty.
_REQUIRED_META = [
    "og:title", "og:description", "og:image", "og:url",
    "article:author", "article:published_time", "article:persona",
    "twitter:title", "twitter:image",
]


def _n(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, re.I))


def run(article_path: str, spec: dict) -> dict:
    """Run the 10-point structural QC on the merged article. Returns
    {"verdict", "notes", "raw"} — same shape Marco already consumes."""
    author = spec.get("author", "")
    og_image = spec.get("og_image", "")

    try:
        html = read_file(article_path)
    except FileNotFoundError:
        raise RuntimeError(f"[vera] Article not found at: {article_path}")

    copy_fail: list[str] = []    # text/copy target failures
    visual_fail: list[str] = []  # image/meta/layout target failures
    passed: list[str] = []

    # 1 — 9 required meta tags present + non-empty (+ canonical link)
    for m in _REQUIRED_META:
        if re.search(r'(?:property|name)="' + re.escape(m) + r'"\s+content="[^"]+"', html):
            passed.append(f"meta {m}")
        else:
            visual_fail.append(f"missing/empty meta tag: {m}")
    if re.search(r'rel="canonical"\s+href="[^"]+"', html):
        passed.append("canonical link")
    else:
        visual_fail.append("missing/empty canonical link")

    # 2 — 5-6 H2 body sections (maya tags body H2s with id="section-…"; the
    #     Glossary/References <h2 class="section-heading"> are excluded).
    section_h2 = _n(r'<h2[^>]*id="section-', html)
    if section_h2 == 0:  # fallback for layouts that don't id every H2
        section_h2 = _n(r"<h2[\s>]", html) - _n(r'<h2[^>]*class="section-heading"', html)
    if 5 <= section_h2 <= 6:
        passed.append(f"{section_h2} H2 sections")
    else:
        copy_fail.append(f"{section_h2} H2 body sections (need 5-6)")

    # 3 — stat grid, >= 4 numeric cards
    stat_cards = _n(r'class="stat-card"', html)
    (passed if stat_cards >= 4 else copy_fail).append(
        f"stat grid {stat_cards} cards" + ("" if stat_cards >= 4 else " (need >=4)"))

    # 4 — at least one pullquote
    pq = _n(r'class="pullquote"', html) or _n(r"<blockquote", html)
    (passed if pq >= 1 else copy_fail).append(
        "pullquote present" if pq >= 1 else "no pullquote found")

    # 5 — >= 6 glossary terms (draft uses data-term; merged uses glossary-item)
    gloss = _n(r'data-term="', html) + _n(r'class="glossary-item"', html)
    (passed if gloss >= 6 else copy_fail).append(
        f"{gloss} glossary terms" + ("" if gloss >= 6 else " (need >=6)"))

    # 6 — >= 6 references
    refs = _n(r'class="reference-item"', html)
    if refs == 0:
        rm = re.search(r'class="references?[^"]*".*?</(?:ol|section)>', html, re.S | re.I)
        refs = _n(r"<li", rm.group(0)) if rm else 0
    (passed if refs >= 6 else copy_fail).append(
        f"{refs} references" + ("" if refs >= 6 else " (need >=6)"))

    # 7 — no TODO / PLACEHOLDER / lorem ipsum / leftover skeleton tokens
    # Note: PLACEHOLDER is checked case-sensitively (uppercase only) to avoid false positives
    # on legitimate HTML placeholder= attributes and CSS ::placeholder pseudo-class in the
    # newsletter form boilerplate. Skeleton tokens are always uppercase; HTML attrs are lowercase.
    if (re.search(r"\bTODO\b|lorem ipsum|\[FULL TITLE\]|\[CATEGORY\]|\[Section", html, re.I)
            or "PLACEHOLDER" in html):
        copy_fail.append("contains TODO / PLACEHOLDER / lorem / leftover skeleton token")
    else:
        passed.append("no placeholders/leftover tokens")

    # 8 — og:image file exists on disk (real image, not an empty stub) + wired in
    if og_image:
        p = REPO_ROOT / og_image
        if p.exists() and p.stat().st_size > 1024:
            passed.append("og:image file exists")
        else:
            visual_fail.append(f"og:image missing/empty on disk: {og_image}")
        if Path(og_image).name in html:
            passed.append("og:image wired into HTML")
        else:
            visual_fail.append("og:image not referenced in article HTML")

    # 9 — persona meta matches the spec's author
    persona_m = re.search(r'article:persona"\s+content="([^"]*)"', html)
    if persona_m:
        want = resolve_author({"author": author})  # joselito/dawn/kenji
        if want in persona_m.group(1).lower():
            passed.append("persona meta matches author")
        else:
            visual_fail.append(f"persona meta '{persona_m.group(1)}' != author '{author}'")

    # 10 — body word count within the row author's persona range (SAME thresholds
    #      as Quill's gate, so the two stages never contradict each other).
    m = re.search(r'<main class="article-content[^"]*">(.*?)</main>', html, re.S)
    if m:
        body = m.group(1)
        for cls, end in [("glossary", "</dl>"), ("references", "</ol>")]:
            body = re.sub(r'<div class="' + cls + r'">.*?' + re.escape(end) + r"\s*</div>",
                          "", body, flags=re.S)
        wc = len(re.sub(r"<[^>]+>", " ", body).split())
        a = AUTHOR_SPECS[resolve_author({"author": author})]
        floor, ceiling = int(a["range_min"] * 0.85), int(a["range_max"] * 1.2)
        if floor <= wc <= ceiling:
            passed.append(f"word count {wc}")
        else:
            copy_fail.append(f"word count {wc} outside {floor}-{ceiling} ({a['range']})")

    notes = [f"PASS: {p}" for p in passed] + \
            [f"FAIL (copy): {f}" for f in copy_fail] + \
            [f"FAIL (visual): {f}" for f in visual_fail]

    if copy_fail:
        verdict = VERDICT_COPY
    elif visual_fail:
        verdict = VERDICT_VISUAL
    else:
        verdict = VERDICT_APPROVED

    log.info(f"[vera] python QC: {verdict} — {len(passed)} pass, "
             f"{len(copy_fail)} copy-fail, {len(visual_fail)} visual-fail")
    return {"verdict": verdict, "notes": notes, "raw": "\n".join(notes)}
