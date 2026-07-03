"""run_review_batch.py — Review Day (Vera): QC all staged (unpublished) articles.

Vera checks each article that's written on disk but not yet published against the
assignment targets and reports a verdict. ASSURANCE only — she reports verdicts and
notes; she never edits (Iris/Joe decide). Gated: Vera is a CC agent (tokens). Reports
'nothing to review' if no staged articles.

Usage: python run_review_batch.py
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.base import REPO_ROOT, read_json, log
from agents import vera

ART_RE = re.compile(r"aima-article-(.+)-(\d{3})\.html")


def _meta(content: str, prop: str) -> str:
    m = re.search(rf'<meta\s+property="{prop}"\s+content="([^"]+)"', content)
    return m.group(1).strip() if m else ""


def _staged() -> list:
    """Article HTML files on disk that are not yet published (not in posted_articles.json)."""
    posted = read_json("linkedin_pipeline/posted_articles.json")
    posted = set(posted) if isinstance(posted, list) else set()
    out = []
    for p in sorted((REPO_ROOT / "articles").glob("aima-article-*.html")):
        if p.name == "aima-article-skeleton.html":
            continue
        if p.name not in posted:
            out.append(p.name)
    return out


def _build_spec(filename: str) -> dict:
    m = ART_RE.match(filename)
    slug, num = m.group(1), int(m.group(2))
    content = (REPO_ROOT / "articles" / filename).read_text(encoding="utf-8", errors="replace")
    og = _meta(content, "og:image")
    og_rel = og.split("/aima/", 1)[1] if "/aima/" in og else (og or f"img/articles/aima-{num:03d}-{slug}.jpg")
    return {"number": num, "slug": slug, "filename": filename,
            "title": _meta(content, "og:title"),
            "author": _meta(content, "article:persona") or "Joselito Sering",
            "og_image": og_rel, "target_words": 1600}


def main():
    staged = _staged()
    if not staged:
        log.info("[review-batch] Nothing to review — no staged (unpublished) articles on disk.")
        print(json.dumps({"reviewed": 0, "reason": "none_staged"}))
        return

    log.info(f"[review-batch] Vera reviewing {len(staged)} staged article(s)...")
    results = []
    for fname in staged:
        spec = _build_spec(fname)
        try:
            v = vera.run(f"articles/{fname}", spec)
            verdict, notes = v.get("verdict"), v.get("notes", [])
        except Exception as e:
            verdict, notes = f"error: {e}", []
        results.append({"article": fname, "verdict": verdict, "notes": notes})
        log.info(f"[review-batch]   #{spec['number']:03d} {fname[:44]:44} -> {verdict} ({len(notes)} note(s))")

    out = REPO_ROOT / "articles" / "review_day.json"
    out.write_text(json.dumps({"reviewed": len(results), "results": results}, indent=2), encoding="utf-8")
    approved = sum(1 for r in results if r["verdict"] == "approved")
    log.info(f"[review-batch] Done. {approved}/{len(results)} approved. Report -> articles/review_day.json "
             "(Vera reports only — Iris/Joe decide revisions).")


if __name__ == "__main__":
    main()
