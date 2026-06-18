"""
pipeline.py — Fetches new AIMA articles and posts them to LinkedIn.
Run manually: python pipeline.py

On each run:
  1. Collects analytics for any posts that are 48h+ old (non-blocking)
  2. Deploy-guard: verifies og:image URL is live before posting
  3. Posts new articles via direct LinkedIn image upload (Option B)
  4. Logs post IDs to post_log.json for later analytics collection
"""

import sys
import re
import time
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from github_fetcher import get_new_articles, mark_as_posted
from linkedin_poster import post_to_linkedin, extract_metadata, extract_persona
from analytics_collector import collect_pending_analytics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log"),
    ]
)
log = logging.getLogger(__name__)

IMAGE_WAIT_LIMIT     = 120   # seconds — max wait for og:image to go live
IMAGE_RETRY_INTERVAL = 30    # seconds between checks
POST_LOG             = Path(__file__).parent / "post_log.json"


# ── Post log helpers ──────────────────────────────────────────────────────────

def load_post_log():
    if POST_LOG.exists():
        with open(POST_LOG, encoding="utf-8") as f:
            return json.load(f)
    return []


def log_post(post_id, article, title, persona):
    """Append a newly published post to post_log.json for later analytics."""
    entries = load_post_log()
    entries.append({
        "post_id":             post_id,
        "article":             article,
        "title":               title,
        "persona":             persona or "joselito",
        "posted_at":           datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "analytics_collected": False,
    })
    with open(POST_LOG, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    _git_push("post_log.json", f"data: log post {article}")


def _git_push(filepath, message):
    """Stage, commit, and push a data file so GitHub Pages serves fresh data."""
    import subprocess
    repo_root = Path(__file__).parent.parent
    rel = Path(__file__).parent / filepath
    try:
        subprocess.run(["git", "add", str(rel)], cwd=repo_root, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo_root, capture_output=True
        )
        if result.returncode == 0:
            return  # nothing staged — skip commit
        subprocess.run(["git", "commit", "-m", message], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True, capture_output=True)
        log.info(f"  git push OK: {message}")
    except Exception as e:
        log.warning(f"  git push failed (non-fatal): {e}")


# ── Deploy guard ──────────────────────────────────────────────────────────────

def extract_og_image(html_content):
    """Return the og:image URL from article HTML, or None."""
    m = re.search(
        r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']',
        html_content, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'<meta\s+content=["\'](.*?)["\']\s+property=["\']og:image["\']',
            html_content, re.IGNORECASE
        )
    return m.group(1).strip() if m else None


def wait_for_image(image_url, article_name):
    """
    Poll image_url until it returns HTTP 200, or IMAGE_WAIT_LIMIT is reached.
    Returns True if image is live, False if timed out.
    """
    elapsed = 0
    while elapsed <= IMAGE_WAIT_LIMIT:
        try:
            req = urllib.request.Request(image_url, method="HEAD")
            req.add_header("User-Agent", "LinkedInBot/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    log.info(f"  og:image live ({elapsed}s elapsed): {image_url}")
                    return True
        except Exception:
            pass

        if elapsed < IMAGE_WAIT_LIMIT:
            log.info(f"  og:image not yet live, retrying in {IMAGE_RETRY_INTERVAL}s... ({elapsed}/{IMAGE_WAIT_LIMIT}s)")
            time.sleep(IMAGE_RETRY_INTERVAL)
            elapsed += IMAGE_RETRY_INTERVAL
        else:
            break

    log.warning(f"  og:image did not become live within {IMAGE_WAIT_LIMIT}s — posting anyway.")
    return False


# ── Main run ──────────────────────────────────────────────────────────────────

def run():
    log.info("=" * 50)
    log.info(f"Pipeline started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1 — collect analytics for any posts that are 48h+ old
    log.info("Checking for pending post analytics...")
    try:
        n = collect_pending_analytics(verbose=False)
        if n:
            log.info(f"  Analytics collected for {n} post(s). See post_analytics.csv.")
        else:
            log.info("  No analytics ready to collect yet.")
    except Exception as e:
        log.warning(f"  Analytics collection failed (non-fatal): {e}")

    # Step 2 — find and post new articles
    try:
        log.info("Scanning articles folder...")
        articles, posted = get_new_articles()

        if not articles:
            log.info("No new articles found. Nothing to post.")
            return

        log.info(f"Found {len(articles)} new article(s). Posting to LinkedIn...")
        success_count = 0

        for article in articles:
            log.info(f"  Posting: {article['name']}")

            # Deploy guard — verify og:image is live before posting
            image_url = extract_og_image(article["content"])
            if image_url:
                log.info(f"  Checking og:image: {image_url}")
                wait_for_image(image_url, article["name"])
            else:
                log.warning(f"  No og:image found in {article['name']} — skipping image check.")

            try:
                post_id = post_to_linkedin(article)
                mark_as_posted(article["name"], posted)

                # Log post ID for analytics collection in 48h
                title, _, _ = extract_metadata(
                    article["content"], article["name"], article.get("html_url", "")
                )
                persona = extract_persona(article["content"])
                log_post(post_id, article["name"], title, persona)
                log.info(f"  Logged to post_log.json for analytics.")

                success_count += 1
            except Exception as e:
                log.error(f"  Failed: {article['name']} — {e}")

        log.info(f"Done. {success_count}/{len(articles)} posted successfully.")

    except Exception as e:
        log.error(f"Pipeline error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
