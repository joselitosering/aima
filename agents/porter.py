"""Porter — Publisher (Pure Python, no LLM calls).

Commits the article, pushes to main, waits for GitHub Pages to go live,
then logs the canonical URL to the Google Apps Script endpoint.
"""

import os
import subprocess
import time
import urllib.request
import urllib.error
import json
import logging
from datetime import datetime, timezone

from agents.base import REPO_ROOT, git_commit, git_push, log

GITHUB_PAGES_BASE = "https://joselitosering.github.io/aima"
DEPLOY_POLL_INTERVAL = 30   # seconds between HEAD checks
DEPLOY_TIMEOUT = 120        # seconds before giving up


def _head_ok(url: str) -> bool:
    """Return True if URL responds with HTTP 200."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError):
        return False


def _post_to_gas(gas_endpoint: str, url: str) -> dict:
    """POST canonical URL to Google Apps Script and return the response."""
    payload = json.dumps({"url": url}).encode("utf-8")
    req = urllib.request.Request(
        gas_endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(spec: dict, dry_run: bool = False) -> dict:
    """
    Commit, push, wait for deploy, log to GAS.

    Returns:
      {
        "live_url": "https://...",
        "gs_row": N,
        "deploy_timestamp": "ISO8601"
      }
    Raises RuntimeError if deploy times out.
    """
    number = spec["number"]
    title = spec["title"]
    filename = spec["filename"]
    og_image = spec["og_image"]

    live_url = f"{GITHUB_PAGES_BASE}/articles/{filename}"
    image_url = f"{GITHUB_PAGES_BASE}/{og_image}"
    commit_msg = f"Article {number:03d}: {title}"

    if dry_run:
        log.info(f"[porter] DRY RUN — would commit: '{commit_msg}'")
        log.info(f"[porter] DRY RUN — would push origin main")
        log.info(f"[porter] DRY RUN — would poll: {image_url}")
        log.info(f"[porter] DRY RUN — would POST to GAS: {live_url}")
        return {
            "live_url": live_url,
            "gs_row": -1,
            "deploy_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Step 1 — commit
    log.info(f"[porter] committing: {commit_msg}")
    git_commit(commit_msg)

    # Step 2 — push
    log.info("[porter] pushing to origin main")
    git_push()

    # Step 3 — deploy guard: poll until og:image URL is live
    log.info(f"[porter] waiting for GitHub Pages deploy: {image_url}")
    deadline = time.time() + DEPLOY_TIMEOUT
    while time.time() < deadline:
        if _head_ok(image_url):
            log.info("[porter] deploy confirmed — article is live")
            break
        remaining = int(deadline - time.time())
        log.info(f"[porter] not live yet, retrying in {DEPLOY_POLL_INTERVAL}s ({remaining}s remaining)")
        time.sleep(DEPLOY_POLL_INTERVAL)
    else:
        raise RuntimeError(
            f"[porter] Deploy timed out after {DEPLOY_TIMEOUT}s. "
            f"Image URL never returned 200: {image_url}"
        )

    deploy_ts = datetime.now(timezone.utc).isoformat()

    # Step 4 — log canonical URL to GAS
    gas_endpoint = os.environ.get("GAS_ENDPOINT", "")
    gs_row = -1
    if gas_endpoint:
        log.info(f"[porter] posting to GAS: {live_url}")
        response = _post_to_gas(gas_endpoint, live_url)
        gs_row = response.get("row", -1)
        log.info(f"[porter] GAS confirmed: row={gs_row}")
    else:
        log.warning("[porter] GAS_ENDPOINT not set — skipping GAS log")

    result = {
        "live_url": live_url,
        "gs_row": gs_row,
        "deploy_timestamp": deploy_ts,
    }
    log.info(f"[porter] Article {number:03d} live · GS row {gs_row}")
    return result
