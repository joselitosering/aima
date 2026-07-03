"""run_marketing_batch.py — Marketing batch: post published-but-unmarketed articles.

Finds articles Porter published (in posted_articles.json) that Nova hasn't yet
marketed (no post_id in post_log.json), and posts each to the AIMA company page +
personal reshare via Nova. Logs to post_log.json for Echo. HALTS with a report if
there is nothing to market.

Usage:
  python run_marketing_batch.py                       # market all published-but-unmarketed
  python run_marketing_batch.py --article aima-article-<slug>-019.html
"""

import argparse
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
from agents import nova

GITHUB_PAGES = "https://joselitosering.github.io/aima"
ART_RE = re.compile(r"aima-article-(.+)-(\d{3})\.html")


def _meta(content: str, prop: str) -> str:
    m = re.search(rf'<meta\s+property="{prop}"\s+content="([^"]+)"', content)
    return m.group(1).strip() if m else ""


def find_unmarketed() -> list:
    """Published (posted_articles.json) minus already-marketed (post_log post_id)."""
    posted = read_json("linkedin_pipeline/posted_articles.json")
    posted = posted if isinstance(posted, list) else []
    post_log = read_json("linkedin_pipeline/post_log.json")
    post_log = post_log if isinstance(post_log, list) else []
    marketed = {e.get("article") for e in post_log if e.get("post_id")}
    return [a for a in posted if ART_RE.match(a) and a not in marketed]


def build_spec(filename: str) -> dict:
    m = ART_RE.match(filename)
    slug, num = m.group(1), int(m.group(2))
    path = REPO_ROOT / "articles" / filename
    content = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    og = _meta(content, "og:image")
    og_rel = og.split("/aima/", 1)[1] if "/aima/" in og else (og or f"img/articles/aima-{num:03d}-{slug}.jpg")
    return {"number": num, "slug": slug, "filename": filename,
            "title": _meta(content, "og:title"), "og_image": og_rel}


def main():
    ap = argparse.ArgumentParser(description="AIMA marketing batch")
    ap.add_argument("--article", help="market only this filename (default: all unmarketed)")
    args = ap.parse_args()

    targets = [args.article] if args.article else find_unmarketed()
    targets = [t for t in targets if ART_RE.match(t)]
    if not targets:
        log.info("[marketing-batch] Nothing to market — every published article is already on LinkedIn.")
        print(json.dumps({"marketed": 0, "reason": "none_pending"}))
        return

    log.info(f"[marketing-batch] Marketing {len(targets)} published article(s) to LinkedIn...")
    done = 0
    for fname in targets:
        if not (REPO_ROOT / "articles" / fname).exists():
            log.error(f"[marketing-batch] {fname} not on disk — skipping")
            continue
        spec = build_spec(fname)
        live_url = f"{GITHUB_PAGES}/articles/{fname}"
        log.info(f"[marketing-batch] #{spec['number']:03d} '{spec['title'][:44]}'")
        try:
            nova.run(spec, live_url)
            done += 1
        except Exception as e:
            log.error(f"[marketing-batch] {fname} failed: {e}")
    log.info(f"[marketing-batch] Done. {done}/{len(targets)} marketed to LinkedIn.")


if __name__ == "__main__":
    main()
