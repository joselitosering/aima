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
      