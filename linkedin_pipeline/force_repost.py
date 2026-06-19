#!/usr/bin/env python3
"""
force_repost.py — Backfill-posts a specific AIMA article to LinkedIn.

Usage:
  python force_repost.py --article <filename>

The script auto-discovers the articles folder via:
  1. ARTICLES_FOLDER env var (from .env, Windows or Linux path)
  2. Mount glob search for the file on Linux
"""

import sys
import os
import json
import argparse
import logging
import glob as _glob
import platform
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ───────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv
load_dotenv(SCRIPT_DIR / ".env")

LOG_FILE = SCRIPT_DIR / "force_repost.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ]
)
log = logging.getLogger(__name__)

POST_LOG = SCRIPT_DIR / "post_log.json"


# ── Path discovery ───────────────────────────────────────────────────────────

def discover_articles_folder(filename_hint=None):
    folder = os.getenv("ARTICLES_FOLDER", "").strip()

    # Direct path works (native OS or already Linux)
    if folder and Path(folder).exists():
        return Path(folder)

    # On Linux: translate Windows D:\ path to /sessions/.../mnt/...
    if platform.system() == "Linux" and "\\" in folder:
        # "D:\Apps\DevOps\Github\aima\articles" → relative parts after drive
        parts = folder.replace("\\", "/").split("/")
        # Remove drive letter part (e.g. "D:")
        parts = [p for p in parts if p and ":" not in p]
        folder_name = parts[-1]  # e.g. "articles"

        # Try exact subfolder under any session mount
        mounts = _glob.glob(f"/sessions/*/mnt/{folder_name}/")
        if mounts:
            log.info(f"Auto-discovered articles folder: {mounts[0]}")
            return Path(mounts[0])

        # Broader search
        mounts = _glob.glob(f"/sessions/*/mnt/**/{folder_name}/", recursive=True)
        if mounts:
            return Path(mounts[0])

    # Last resort: locate the hint file anywhere in mounts
    if filename_hint:
        results = _glob.glob(f"/sessions/*/mnt/**/{filename_hint}", recursive=True)
        if results:
            return Path(results[0]).parent

    raise FileNotFoundError(
        f"Cannot find articles folder. ARTICLES_FOLDER={folder!r}. "
        "Ensure the folder is mounted or set ARTICLES_FOLDER correctly."
    )


def discover_repo_root():
    # Try script's parent (one level up from linkedin_pipeline/)
    root = SCRIPT_DIR.parent
    if (root / ".git").exists():
        return root
    # Mount pattern
    mounts = _glob.glob("/sessions/*/mnt/aima/")
    if mounts:
        candidate = Path(mounts[0])
        if (candidate / ".git").exists():
            return candidate
    return root


# ── Post log ─────────────────────────────────────────────────────────────────

def load_post_log():
    if POST_LOG.exists():
        with open(POST_LOG, encoding="utf-8") as f:
            return json.load(f)
    return []


def update_post_log(filename, post_id, title):
    entries = load_post_log()
    updated = False
    for entry in entries:
        if entry.get("article") == filename and entry.get("post_id") is None:
            entry["post_id"] = post_id
            entry["posted_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            entry["analytics_collected"] = False
            entry.pop("note", None)
            updated = True
            log.info(f"  Updated null entry -> post_id={post_id}")
            break
    if not updated:
        entries.insert(0, {
            "post_id": post_id,
            "article": filename,
            "title": title,
            "persona": "joselito",
            "posted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "analytics_collected": False,
        })
        log.info(f"  Appended new entry → post_id={post_id}")
    with open(POST_LOG, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    log.info(f"  post_log.json saved.")


def git_push(message):
    import subprocess
    repo_root = discover_repo_root()
    try:
        subprocess.run(["git", "add", str(POST_LOG)], cwd=repo_root, check=True, capture_output=True)
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo_root, capture_output=True
        )
        if diff.returncode == 0:
            log.info("  Nothing staged — skipping commit.")
            return
        subprocess.run(["git", "commit", "-m", message], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True, capture_output=True)
        log.info(f"  git push OK: {message}")
    except Exception as e:
        log.warning(f"  git push failed (non-fatal): {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Backfill-post a specific AIMA article to LinkedIn."
    )
    parser.add_argument(
        "--article", required=True,
        help="HTML filename, e.g. aima-article-future-of-creative-production-001.html"
    )
    args = parser.parse_args()
    filename = args.article

    log.info("=" * 55)
    log.info(f"force_repost.py started — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Article: {filename}")

    # Discover articles folder
    try:
        articles_folder = discover_articles_folder(filename_hint=filename)
    except FileNotFoundError as e:
        log.error(str(e))
        sys.exit(1)

    filepath = articles_folder / filename
    if not filepath.exists():
        log.error(f"Article file not found: {filepath}")
        sys.exit(1)

    content = filepath.read_text(encoding="utf-8", errors="replace")

    # Build GitHub URL
    github_repo     = os.getenv("GITHUB_REPO", "joselitosering/aima")
    github_branch   = os.getenv("GITHUB_BRANCH", "main")
    github_sub      = os.getenv("GITHUB_ARTICLES_SUBFOLDER", "articles")
    html_url        = f"https://raw.githubusercontent.com/{github_repo}/{github_branch}/{github_sub}/{filename}"

    article = {"name": filename, "html_url": html_url, "content": content}

    from linkedin_poster import post_to_linkedin, extract_metadata
    try:
        post_id = post_to_linkedin(article)
        title, _, _ = extract_metadata(content, filename, html_url)
        update_post_log(filename, post_id, title)
        git_push(f"data: backfill post log {filename}")
        log.info(f"SUCCESS - Post ID: {post_id}")
        print(f"\nSUCCESS: {filename}\nPost ID: {post_id}\n")
    except Exception as e:
        log.error(f"✗ FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
