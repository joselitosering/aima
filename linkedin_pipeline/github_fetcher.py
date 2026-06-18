"""
github_fetcher.py — Reads new HTML articles from the local AIMA articles folder.
Tracks which articles have already been posted to avoid duplicates.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ARTICLES_FOLDER = os.getenv("ARTICLES_FOLDER", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()
GITHUB_ARTICLES_SUBFOLDER = os.getenv("GITHUB_ARTICLES_SUBFOLDER", "articles").strip().strip("/")

POSTED_LOG = Path(__file__).parent / "posted_articles.json"
SKIP_FILES = {"aima-article-skeleton.html"}


def build_github_url(filename):
    if GITHUB_REPO:
        return f"https://github.com/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/{GITHUB_ARTICLES_SUBFOLDER}/{filename}"
    return ""


def load_posted_log():
    if POSTED_LOG.exists():
        with open(POSTED_LOG) as f:
            return set(json.load(f))
    return set()


def save_posted_log(posted):
    with open(POSTED_LOG, "w") as f:
        json.dump(sorted(posted), f, indent=2)


def get_new_articles():
    if not ARTICLES_FOLDER:
        raise ValueError("ARTICLES_FOLDER not set in .env")

    folder = Path(ARTICLES_FOLDER)
    if not folder.exists():
        raise FileNotFoundError(f"Articles folder not found: {ARTICLES_FOLDER}")

    posted = load_posted_log()
    new_articles = []

    for filepath in sorted(folder.glob("*.html")):
        name = filepath.name
        if name in SKIP_FILES:
            continue
        if name not in posted:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            new_articles.append({
                "name": name,
                "html_url": build_github_url(name),
                "content": content,
            })

    return new_articles, posted


def mark_as_posted(filename, posted):
    posted.add(filename)
    save_posted_log(posted)


if __name__ == "__main__":
    articles, _ = get_new_articles()
    print(f"Found {len(articles)} new article(s) ready to post:")
    for a in articles:
        print(f"  - {a['name']}")
