"""run_publish_batch.py — Publish batch (Porter): publish staged articles to the web.

Finds articles written on disk but not yet published (not in posted_articles.json),
stages each (article HTML + cover image), and runs Porter: git push → wait for the
page to go live on aima.productions → log the canonical URL to Google Sheets. Marks
each published so the calendar shows it Live and the Marketing batch can pick it up.

Does NOT post to LinkedIn (that's the Marketing batch). Gated: git push + GS are live.

Usage:
  python run_publish_batch.py                       # publish all staged
  python run_publish_batch.py --article aima-article-<slug>-019.html
"""

import argparse
import json
import re
import subprocess
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
from agents import porter

ART_RE = re.compile(r"aima-article-(.+)-(\d{3})\.html")


def _meta(content: str, prop: str) -> str:
    m = re.search(rf'<meta\s+property="{prop}"\s+content="([^"]+)"', content)
    return m.group(1).strip() if m else ""


def _staged() -> list:
    """Articles written on disk but not yet in posted_articles.json."""
    posted = read_json("linkedin_pipeline/posted_articles.json")
    posted = set(posted) if isinstance(posted, list) else set()
    out = []
    for p in sorted((REPO_ROOT / "articles").glob("aima-article-*.html")):
        if p.name != "aima-article-skeleton.html" and p.name not in posted:
            out.append(p.name)
    return out


def _build_spec(filename: str) -> dict:
    m = ART_RE.match(filename)
    slug, num = m.group(1), int(m.group(2))
    content = (REPO_ROOT / "articles" / filename).read_text(encoding="utf-8", errors="replace")
    og = _meta(content, "og:image")
    og_rel = og.split("/aima/", 1)[1] if "/aima/" in og else (og or f"img/articles/aima-{num:03d}-{slug}.jpg")
    return {"number": num, "slug": slug, "filename": filename,
            "title": _meta(content, "og:title") or filename, "og_image": og_rel}


def _stage(filename: str, og_image: str):
    """git add the article HTML + cover image so Porter's commit has content
    (no-op if already committed; Porter tolerates an empty commit)."""
    paths = [str(REPO_ROOT / "articles" / filename)]
    img = REPO_ROOT / og_image
    if img.exists():
        paths.append(str(img))
    subprocess.run(["git", "add", *paths], cwd=REPO_ROOT, capture_output=True)


def _mark_published(filename: str):
    p = REPO_ROOT / "linkedin_pipeline" / "posted_articles.json"
    posted = read_json("linkedin_pipeline/posted_articles.json")
    posted = posted if isinstance(posted, list) else []
    if filename not in posted:
        p.write_text(json.dumps(sorted(set(posted) | {filename}), indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="AIMA publish batch (Porter)")
    ap.add_argument("--article", help="publish only this filename (default: all staged)")
    args = ap.parse_args()

    targets = [args.article] if args.article else _staged()
    targets = [t for t in targets if ART_RE.match(t)]
    if not targets:
        log.info("[publish-batch] Nothing to publish — no staged (unpublished) articles on disk.")
        print(json.dumps({"published": 0, "reason": "none_staged"}))
        return

    log.info(f"[publish-batch] Publishing {len(targets)} staged article(s) via Porter...")
    done = 0
    for fname in targets:
        if not (REPO_ROOT / "articles" / fname).exists():
            log.error(f"[publish-batch] {fname} not on disk — skipping")
            continue
        spec = _build_spec(fname)
        log.info(f"[publish-batch] #{spec['number']:03d} '{spec['title'][:44]}'")
        try:
            _stage(fname, spec["og_image"])
            porter.run(spec, gs_enabled=True)
            _mark_published(fname)
            done += 1
        except Exception as e:
            log.error(f"[publish-batch] {fname} failed: {e}")
    log.info(f"[publish-batch] Done. {done}/{len(targets)} published. "
             "Run the Marketing batch to post them to LinkedIn.")


if __name__ == "__main__":
    main()
