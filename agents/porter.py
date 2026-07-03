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

GITHUB_PAGES_BASE = "https://joselitosering.github.io/aima"   # canonical (logged to GS)
PUBLIC_BASE = "https://aima.productions/articles/"            # live page (polled for liveness)
INITIAL_PROPAGATION_WAIT = 60   # seconds — wait before the first liveness check
PAGE_POLL_INTERVAL = 10         # seconds between liveness polls thereafter
PAGE_WAIT_LIMIT = 360           # seconds — max total wait for the page to go live


def _page_live_with_meta(url: str) -> bool:
    """Return True if URL responds 200 and the page carries og metadata."""
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "AIMA-Pipeline/1.0")
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                return False
            body = resp.read().decode("utf-8", errors="replace")
            return "og:title" in body
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


def run(spec: dict, dry_run: bool = False, gs_enabled: bool = True) -> dict:
    """
    Commit, push, wait for the live page to deploy, log canonical URL to GAS.

    Deploy guard: wait 60s for propagation, then poll the public page every 10s
    until it returns 200 with og metadata.

    Returns:
      { "live_url": "https://...", "gs_row": N, "deploy_timestamp": "ISO8601" }
    Raises RuntimeError if the page never goes live.
    """
    number = spec["number"]
    title = spec["title"]
    filename = spec["filename"]

    live_url = f"{GITHUB_PAGES_BASE}/articles/{filename}"   # canonical → GS
    page_url = f"{PUBLIC_BASE}{filename}"                   # public → liveness poll
    commit_msg = f"Article {number:03d}: {title}"

    if dry_run:
        log.info(f"[porter] DRY RUN — would commit: '{commit_msg}'")
        log.info(f"[porter] DRY RUN — would push origin main")
        log.info(f"[porter] DRY RUN — would wait {INITIAL_PROPAGATION_WAIT}s then poll: {page_url}")
        log.info(f"[porter] DRY RUN — would POST to GAS: {live_url} (gs_enabled={gs_enabled})")
        return {
            "live_url": live_url,
            "gs_row": -1,
            "deploy_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Steps 1+2 — commit & push. Tolerate "nothing to commit/push" so an
    # already-committed article (e.g. a standalone Publish batch re-run) still
    # proceeds to the deploy guard + GS log instead of erroring out.
    try:
        log.info(f"[porter] committing: {commit_msg}")
        git_commit(commit_msg)
        log.info("[porter] pushing to origin main")
        git_push()
    except subprocess.CalledProcessError:
        log.info("[porter] nothing new to commit/push — article already on origin; confirming deploy")

    # Step 3 — deploy guard: wait for propagation, then poll the public page
    log.info(f"[porter] waiting {INITIAL_PROPAGATION_WAIT}s for page to propagate: {page_url}")
    time.sleep(INITIAL_PROPAGATION_WAIT)
    elapsed = INITIAL_PROPAGATION_WAIT
    while elapsed <= PAGE_WAIT_LIMIT:
        if _page_live_with_meta(page_url):
            log.info(f"[porter] deploy confirmed — page live with metadata ({elapsed}s)")
            break
        log.info(f"[porter] not live yet, retrying in {PAGE_POLL_INTERVAL}s ({elapsed}/{PAGE_WAIT_LIMIT}s)")
        time.sleep(PAGE_POLL_INTERVAL)
        elapsed += PAGE_POLL_INTERVAL
    else:
        raise RuntimeError(
            f"[porter] Deploy timed out after {PAGE_WAIT_LIMIT}s. "
            f"Page never returned 200 with metadata: {page_url}"
        )

    deploy_ts = datetime.now(timezone.utc).isoformat()

    # Step 4 — log canonical URL to GAS (skippable via GS_ENABLED toggle)
    gas_endpoint = os.environ.get("GAS_ENDPOINT", "")
    gs_row = -1
    if not gs_enabled:
        log.info("[porter] GS_ENABLED=false — skipping Google Sheets log")
    elif gas_endpoint:
        log.info(f"[porter] posting canonical to GAS: {live_url}")
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
