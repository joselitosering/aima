"""maya_merge.py — PURE-PYTHON skeleton merge (no LLM).

Replaces Maya's CC-agent merge call. Deterministically wires Quill's copy body
into the full article skeleton + fills every head/header placeholder. This is
mechanical work — no model needed — so it costs $0 and can't hallucinate or
disobey. Image *sourcing* (Pexels/Higgsfield) stays in maya.py; this is only the
skeleton merge (former Step 2).

EXTENDED 2026-07-14 (per Joe, after AGENT-WORKFLOW.md review + Vera's #25
findings): the skeleton has dedicated <section id="glossary"> / <section
id="references"> blocks with specific markup, plus a TOC sidebar that needs
real H2 ids, plus inline glossary-term links at first mention. The committed
(git HEAD) Maya was a real Sonnet CC call with Read access to the skeleton —
it did this placement via model judgment, undocumented anywhere as an explicit
step. This pure-python version didn't replicate it, which is why #25's
glossary/references landed as ad-hoc divs inside <main> instead of in the
skeleton's real sections. This extension replicates that placement
deterministically: Writer still owns the CONTENT (real terms, real
citations); this file owns ROUTING that content into the skeleton's exact
structure.
"""

import html
import re
from datetime import datetime

from agents.base import read_file, write_file, REPO_ROOT, log

SKELETON = "articles/aima-article-skeleton.html"
GITHUB_BASE = "https://joselitosering.github.io/aima"
PUBLIC_BASE = "https://aima.productions"

# Per-persona byline (avatar initials + role), matching existing published articles.
_PERSONA = {
    "Joselito Sering": {"avatar": "JS", "role": "Editor-in-Chief · AIMA", "persona": "joselito"},
    "Dawn Ginhaua":    {"avatar": "DG", "role": "Cultural Critic & Educator · AIMA", "persona": "dawn"},
    "Kenji Nakamoto":  {"avatar": "KN", "role": "Technology Writer & Explorer · AIMA", "persona": "kenji"},
}


def _fmt_date(iso: str) -> str:
    """'2026-07-06' -> 'July 6, 2026' (Windows-safe, no %-d)."""
    try:
        dt = datetime.strptime((iso or "")[:10], "%Y-%m-%d")
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    except Exception:
        return iso or ""


def _slugify(text: str, maxlen: int = 40) -> str:
    """Plain text -> url-safe slug, e.g. 'The Law They Filed' -> 'the-law-they-filed'."""
    s = re.sub(r"<[^>]+>", "", text)          # strip any inner tags
    s = html.unescape(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:maxlen].rstrip("-") or "section"


def _extract_body(copy_html: str) -> str:
    """Return the article body from Quill's/Writer's output — inner <main>, else inner
    <body>, else the whole thing (minus a leading HTML comment)."""
    m = re.search(r'<main class="article-content[^"]*">(.*?)</main>', copy_html, re.S)
    if m:
        return m.group(1).strip()
    m = re.search(r'<body[^>]*>(.*?)</body>', copy_html, re.S)
    if m:
        return m.group(1).strip()
    return re.sub(r'^\s*<!--.*?-->\s*', '', copy_html, flags=re.S).strip()


def _extract_and_strip(body: str, class_name: str, end_tag: str) -> tuple[str, str]:
    """Pull out <div class="{class_name}">...{end_tag}</div> and return
    (inner_content, body_with_block_removed). end_tag is the last real closing
    tag before </div> (e.g. '</dl>' or '</ol>') — more robust than counting
    nested divs. Returns ("", body) unchanged if no block is found."""
    pat = re.compile(
        r'<div class="' + re.escape(class_name) + r'">(.*?' + re.escape(end_tag) + r')\s*</div>',
        re.S,
    )
    m = pat.search(body)
    if not m:
        return "", body
    return m.group(1), (body[:m.start()] + body[m.end():])


def _parse_glossary(block: str) -> list[tuple[str, str]]:
    """<dt[ data-term="..."]>Term</dt><dd>Definition</dd> pairs, in order.
    data-term is optional — Writer output has been observed both with and
    without it; the *text inside <dt>* is the source of truth either way."""
    pairs = re.findall(
        r'<dt(?:\s+data-term="[^"]*")?\s*>(.*?)</dt>\s*<dd>(.*?)</dd>',
        block, re.S | re.I,
    )
    out = []
    for term, definition in pairs:
        term_clean = re.sub(r"<[^>]+>", "", term).strip()
        if term_clean:
            out.append((term_clean, definition.strip()))
    return out


def _parse_references(block: str) -> list[str]:
    """Each <li>...inner html...</li> as-is — Writer already formats these
    reasonably (authors/title/em-publication/date/link); we re-wrap rather
    than re-derive, since re-parsing citation components is unnecessary risk
    for something already correct."""
    return [li.strip() for li in re.findall(r'<li[^>]*>(.*?)</li>', block, re.S) if li.strip()]


def _inject_h2_ids(body: str) -> tuple[str, list[tuple[str, str]]]:
    """Add id="section-[slug]" to every <h2>, return (new_body, [(slug, title), ...])
    in document order. Skips H2s that already carry an id (idempotent)."""
    toc: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _sub(m: re.Match) -> str:
        attrs, inner = m.group(1), m.group(2)
        title_text = re.sub(r"<[^>]+>", "", inner).strip()
        if 'id="' in attrs:
            existing = re.search(r'id="([^"]*)"', attrs)
            slug = existing.group(1).replace("section-", "") if existing else _slugify(title_text)
        else:
            slug = _slugify(title_text)
            base, n = slug, 2
            while slug in seen:
                slug = f"{base}-{n}"; n += 1
            attrs = f' id="section-{slug}"' + attrs
        seen.add(slug)
        toc.append((slug, title_text))
        return f"<h2{attrs}>{inner}</h2>"

    new_body = re.sub(r"<h2([^>]*)>(.*?)</h2>", _sub, body, flags=re.S)
    return new_body, toc


def _link_first_mentions(body: str, terms: list[tuple[str, str]]) -> str:
    """Wrap the FIRST occurrence of each glossary term's text in running prose
    with the skeleton's mention-link pattern. Best-effort: a term that never
    appears verbatim in the body is silently skipped (its glossary entry's
    back-link will just have no matching anchor — degraded, not broken)."""
    for term, _ in terms:
        word = _slugify(term, maxlen=30)
        # Avoid re-linking inside existing tags/attributes; only match plain text runs.
        pat = re.compile(r'(?<![>\w])(' + re.escape(term) + r')(?!\w)', re.I)
        def _wrap(m: re.Match, _word=word) -> str:
            return f'<a href="#glossary-{_word}" class="glossary-term" id="mention-{_word}">{m.group(1)}</a>'
        new_body, n = pat.subn(_wrap, body, count=1)
        if n:
            body = new_body
    return body


def _build_glossary_section(terms: list[tuple[str, str]]) -> str:
    items = []
    for term, definition in terms:
        word = _slugify(term, maxlen=30)
        items.append(
            f'<div class="glossary-item" id="glossary-{word}">\n'
            f'<div class="glossary-term-title">\n{html.escape(term)}\n'
            f'<a href="#mention-{word}" class="back-link">↑ Back to text</a>\n</div>\n'
            f'<p class="glossary-definition">{definition}</p>\n</div>'
        )
    return (
        '<section class="glossary-section" id="glossary">\n'
        '<h2 class="section-heading">Glossary</h2>\n'
        '<div class="glossary-list">\n' + "\n".join(items) + "\n</div>\n</section>"
    )


def _build_references_section(refs: list[str]) -> str:
    items = []
    for i, ref_html in enumerate(refs, 1):
        items.append(f'<li class="reference-item" data-number="[{i}]">{ref_html}</li>')
    publishers = sorted(set(re.findall(r"<em>([^<]+)</em>", " ".join(refs))))
    notice = ", ".join(publishers[:8]) if publishers else "sources cited above"
    return (
        '<section class="references-section" id="references">\n'
        '<h2 class="section-heading">References</h2>\n'
        '<ol class="reference-list">\n' + "\n".join(items) + "\n</ol>\n"
        '<div class="copyright-notice"><strong>Copyright Acknowledgements:</strong> '
        f'Sources cited per MLA 9th edition: {html.escape(notice)}. '
        f'URLs verified as accessible at time of publication.</div>\n</section>'
    )


def _build_toc_links(toc: list[tuple[str, str]]) -> str:
    return "\n".join(
        f'<a href="#section-{slug}" class="toc-link">{html.escape(title)}</a>'
        for slug, title in toc
    )


def _set_meta(text: str, key: str, value: str) -> str:
    """Set the content of every <meta name|property="key" content="..."/>."""
    pat = re.compile(r'(<meta (?:name|property)="' + re.escape(key) + r'"\s+content=")[^"]*(")')
    return pat.sub(lambda m: m.group(1) + html.escape(value, quote=True) + m.group(2), text)


def _set_by_id(text: str, tag: str, elem_id: str, inner: str) -> str:
    """Replace inner content of <tag ... id="elem_id" ...>...</tag> (first match)."""
    pat = re.compile(r'(<' + tag + r'[^>]*id="' + re.escape(elem_id) + r'"[^>]*>).*?(</' + tag + r'>)', re.S)
    return pat.sub(lambda m: m.group(1) + inner + m.group(2), text, count=1)


def _styled_title(title: str) -> str:
    """Approximate the brand <h1> styling: uppercase the pre-colon phrase and
    accent its last word (cyan); accent the tail of the subtitle (orange)."""
    t = title.strip()
    if ":" in t:
        left, right = t.split(":", 1)
        lw = left.strip().split()
        if len(lw) > 1:
            left_html = html.escape(" ".join(lw[:-1])).upper() + " " + \
                f'<span class="highlight">{html.escape(lw[-1]).upper()}</span>'
        else:
            left_html = f'<span class="highlight">{html.escape(lw[0]).upper()}</span>' if lw else ""
        rw = right.strip().split()
        n = 2 if len(rw) > 3 else 1
        head = html.escape(" ".join(rw[:-n]))
        tail = html.escape(" ".join(rw[-n:]))
        return f'{left_html}: {head} <span class="highlight-orange">{tail}</span>'.strip()
    words = t.split()
    if len(words) > 1:
        return html.escape(" ".join(words[:-1])).upper() + \
            f' <span class="highlight">{html.escape(words[-1]).upper()}</span>'
    return f'<span class="highlight">{html.escape(t).upper()}</span>'


def _prev_link(number: int) -> tuple[str, str]:
    """(url, title) of article number-1 on disk, for the static nav fallback
    (the runtime GS-load overrides this anyway). Empty if none."""
    prev = number - 1
    if prev < 1:
        return "", ""
    for p in sorted((REPO_ROOT / "articles").glob(f"aima-article-*-{prev:03d}.html")):
        h = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'property="og:title"\s+content="([^"]*)"', h)
        return f"./{p.name}", (m.group(1) if m else "")
    return "", ""


def merge(article_path: str, og_image: str, alt_image: str, spec: dict) -> bool:
    """Build the complete article HTML from the skeleton + Writer/Quill's copy.
    Overwrites article_path. Returns True on a structurally-complete merge."""
    num = int(spec.get("number", 0))
    slug = spec.get("slug", "")
    filename = spec.get("filename") or f"aima-article-{slug}-{num:03d}.html"
    title = spec.get("title", "")
    author = spec.get("author", "Joselito Sering")
    category = spec.get("category", "")
    description = spec.get("description") or title
    publish_date = spec.get("publish_date", "")
    read_time = str(spec.get("read_time", "") or spec.get("read", "") or "10").split()[0]
    tags = spec.get("custom_tags") or spec.get("topic_tags") or []
    keywords = "AI, " + ", ".join(list(tags)[:6] + [category]) + ", AIMA" if tags else f"AI, {category}, AIMA"

    p = _PERSONA.get(author, {"avatar": "".join(w[0] for w in author.split()[:2]).upper() or "AI",
                              "role": "Contributor · AIMA", "persona": "joselito"})
    img_url = f"{GITHUB_BASE}/{og_image.lstrip('/')}"
    canonical = f"{GITHUB_BASE}/articles/{filename}"
    og_url = f"{PUBLIC_BASE}/articles/{filename}"

    out = read_file(SKELETON)

    # Strip the skeleton's authoring-checklist comment — it is dev scaffolding
    # that must NOT ship. It literally contains the line "□ <title> tag", which
    # made the LinkedIn poster's <title>…</title> regex start matching inside the
    # comment and run to the real </title>, posting the whole checklist as the
    # article title (garbled #25 post, 2026-07-14). Removed from the merged
    # OUTPUT only; the skeleton file keeps the comment as its own documentation.
    out = re.sub(r'<!--(?:(?!-->).)*?AIMA ARTICLE SKELETON(?:(?!-->).)*?-->\s*',
                 '', out, count=1, flags=re.S)

    body = _extract_body(read_file(article_path))

    # ── NEW: pull glossary/references out of the ad-hoc copy, parse, remove ──
    glossary_block, body = _extract_and_strip(body, "glossary", "</dl>")
    references_block, body = _extract_and_strip(body, "references", "</ol>")
    terms = _parse_glossary(glossary_block)
    refs = _parse_references(references_block)

    # ── NEW: H2 ids (for TOC + anchors) ──
    body, toc_entries = _inject_h2_ids(body)

    # ── NEW: inline glossary-term first-mention links (best-effort) ──
    body = _link_first_mentions(body, terms)

    # ── head meta ──
    for key, val in [
        ("article:id", f"{num:03d}"), ("article:title", title),
        ("article:description", description), ("article:author", author),
        ("article:publish-date", publish_date), ("article:read-time", read_time),
        ("article:category", category), ("article:section", category),
        ("article:header-image", img_url), ("article:persona", p["persona"]),
        ("article:published_time", f"{publish_date}T00:00:00Z"),
        ("article:modified_time", f"{publish_date}T00:00:00Z"),
        ("og:title", title), ("og:description", description), ("og:image", img_url),
        ("og:url", og_url), ("twitter:title", title),
        ("twitter:description", description), ("twitter:image", img_url),
        ("description", description), ("keywords", keywords),
    ]:
        out = _set_meta(out, key, val)

    # _set_meta only EDITS existing <meta> tags. The skeleton is missing an
    # article:persona tag, so it never got set — shipped articles had no persona
    # meta (caught 2026-07-14 by the pure-python Vera). Inject any required meta
    # the skeleton lacks, before </head>, so the value actually lands.
    for key, val in [("article:persona", p["persona"])]:
        # Anchor on an actual <meta ...> element — NOT a bare attribute match,
        # which would false-positive on the skeleton's JS
        # (document.querySelector('meta[name="article:persona"]')) and skip injection.
        if not re.search(r'<meta [^>]*(?:property|name)="' + re.escape(key) + r'"', out):
            tag = f'<meta property="{key}" content="{html.escape(val, quote=True)}">\n'
            out = out.replace("</head>", tag + "</head>", 1)

    # nav (static fallback; runtime GS-load overrides)
    pu, pt = _prev_link(num)
    out = _set_meta(out, "article:prev-url", pu)
    out = _set_meta(out, "article:prev-title", pt)
    out = _set_meta(out, "article:next-url", "")
    out = _set_meta(out, "article:next-title", "")

    # canonical link
    out = re.sub(r'(<link rel="canonical" href=")[^"]*(")',
                 lambda m: m.group(1) + canonical + m.group(2), out, count=1)

    # ── header + byline ──
    out = _set_by_id(out, "title", "pageTitle", html.escape(f"{title} — AIMA Magazine"))
    out = _set_by_id(out, "span", "articleCategory", html.escape(category))
    out = _set_by_id(out, "h1", "articleTitle", "\n" + _styled_title(title) + "\n")
    out = _set_by_id(out, "div", "authorAvatar", html.escape(p["avatar"]))
    out = _set_by_id(out, "div", "authorName", html.escape(author))
    out = re.sub(r'(<div class="author-role">)[^<]*(</div>)',
                 lambda m: m.group(1) + html.escape(p["role"]) + m.group(2), out, count=1)
    out = _set_by_id(out, "div", "publishDate", html.escape(_fmt_date(publish_date)))
    out = _set_by_id(out, "div", "readTime", html.escape(f"{read_time} min read"))
    out = _set_by_id(out, "div", "categoryValue", html.escape(category))
    out = _set_by_id(out, "span", "printCategoryHook", html.escape(category))

    # ── body copy into <main> (glossary/references already stripped out) ──
    out = re.sub(r'(<main class="article-content[^"]*">).*?(</main>)',
                 lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), out, flags=re.S, count=1)

    # ── NEW: TOC sidebar — replace the 5 placeholder section links ──
    out = re.sub(
        r'(<!-- REPLACE with actual section slugs matching H2 id attributes -->\s*).*?(\s*<!-- Fixed entries)',
        lambda m: m.group(1) + _build_toc_links(toc_entries) + m.group(2),
        out, flags=re.S, count=1,
    )

    # ── NEW: real #glossary and #references sections replace the skeleton stubs ──
    if terms:
        out = re.sub(r'<section class="glossary-section" id="glossary">.*?</section>',
                     lambda m: _build_glossary_section(terms), out, flags=re.S, count=1)
    if refs:
        out = re.sub(r'<section class="references-section" id="references">.*?</section>',
                     lambda m: _build_references_section(refs), out, flags=re.S, count=1)

    # JSON-LD block + any other descriptive placeholders. wc now measures body
    # AFTER glossary/references were stripped out — narrative prose only, which
    # is what Vera's manual count expects (was inflated before this fix).
    wc = len(re.sub(r"<[^>]+>", " ", body).split())
    for tok, val in [
        ("[FULL TITLE]", title), ("[SEO description]", description),
        ("[header image URL]", img_url), ("[Higgsfield or Unsplash URL]", img_url),
        ("[Category string]", category), ("[CATEGORY]", category), ("[Category]", category),
        ("[YYYY-MM-DD]", publish_date), ("[Month DD, YYYY]", _fmt_date(publish_date)),
        ("[word count — approx 2000–3750]", str(wc)),
        ("[topic keywords]", ", ".join(list(tags)[:5])),
        ("[slug]", slug), ("[num]", f"{num:03d}"),
        # NOTE: do NOT replace "[persona]". In the skeleton it only ever appears as
        # legitimate JavaScript — `_authorColors[persona]` (line ~755), a lookup by
        # the `persona` JS variable — NOT as placeholder text. Replacing it turned
        # that into `_authorColorsdawn` (undefined var) → ReferenceError → the whole
        # inline script (incl. the fade-in reveal) stopped running → article body
        # stuck at opacity:0 / invisible on #25 (2026-07-14). Persona is delivered
        # via the <meta property="article:persona"> tag, which that JS reads.
    ]:
        out = out.replace(tok, val)
    out = out.replace('"name": "Joselito Sering"', f'"name": "{author}"')  # JSON-LD author

    write_file(article_path, out)
    ok = (img_url in out and "og:image" in out and 'id="articleTitle"' in out
          and body[:40] in out and "[FULL TITLE]" not in out
          and (not terms or all(f'id="glossary-{_slugify(t, 30)}"' in out for t, _ in terms))
          and (not refs or 'data-number="[1]"' in out))
    log.info(f"[maya] pure-python merge {'OK' if ok else 'INCOMPLETE'}: {article_path} "
             f"(glossary={len(terms)}, refs={len(refs)}, sections={len(toc_entries)}, wc={wc})")
    return ok
