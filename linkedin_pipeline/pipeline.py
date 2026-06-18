"""
pipeline.py — Fetches new AIMA articles and posts them to LinkedIn.
Run manually: python pipeline.py
"""

import sys
import logging
from datetime import datetime
from github_fetcher import get_new_articles, mark_as_posted
from linkedin_poster import post_to_linkedin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log"),
    ]
)
log = logging.getLogger(__name__)


def run():
    log.info("=" * 50)
    log.info(f"Pipeline started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
            try:
                post_to_linkedin(article)
                mark_as_posted(article["name"], posted)
                success_count += 1
            except Exception as e:
                log.error(f"  Failed: {article['name']} — {e}")

        log.info(f"Done. {success_count}/{len(articles)} posted successfully.")

    except Exception as e:
        log.error(f"Pipeline error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
