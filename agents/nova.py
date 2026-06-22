"""Nova — Marketing Agent (Pure Python, no LLM calls).

Calls linkedin_pipeline/pipeline.py to post to the AIMA company page
and reshare to Joselito's personal profile. Reads URNs back from post_log.json.
"""

import json
import os
import subprocess
import urllib.request
import urllib.error
import logging

from agents.base import REPO_ROOT, read_json, log


def _head_ok(url: str) -> bool:
    """Return True if URL responds with HTTP 200."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError):
        return False


def run(spec: dict, live_url: str, dry_run: bool = False) -> dict:
    """
    Post to LinkedIn via linkedin_pipeline/pipeline.py.

    Returns:
      {
        "company_urn": "urn:li:share:...",
        "reshare_urn": "urn:li:share:..."
      }
    Raises RuntimeError on failure.
    """
    og_image_url = f"https://joselitosering.github.io/aima/{spec['og_image']}"

    # Pre-check 1 — article must be live
    if not _head_ok(og_image_url):
        raise RuntimeError(
            f"[nova] Article image not live yet: {og_image_url}\n"
            "       Porter should have confirmed deploy before Nova runs."
        )

    # Pre-check 2 — LinkedIn token must be set
    linkedin_env = REPO_ROOT / "linkedin_pipeline" / ".env"
    if not linkedin_env.exists():
        raise RuntimeError(
            "[nova] linkedin_pipeline/.env not found — LinkedIn credentials missing."
        )

    if dry_run:
        log.info(f"[nova] DRY RUN — would run: python linkedin_pipeline/pipeline.py")
        log.info(f"[nova] DRY RUN — article live at: {live_url}")
        return {
            "company_urn": "urn:li:share:DRY_RUN",
            "reshare_urn": "urn:li:share:DRY_RUN",
        }

    log.info(f"[nova] running linkedin_pipeline/pipeline.py")
    result = subprocess.run(
        ["python", "linkedin_pipeline/pipeline.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"[nova] pipeline.py failed (exit {result.returncode}):\n{result.stderr}"
        )

    log.info(f"[nova] pipeline.py output:\n{result.stdout}")

    # Read URNs from post_log.json (pipeline.py writes these)
    post_log = read_json("linkedin_pipeline/post_log.json")

    # post_log.json is a list — find the most recent entry for this article
    entries = post_log if isinstance(post_log, list) else []
    slug = spec.get("slug", "")

    company_urn = ""
    reshare_urn = ""

    # Try to find the entry matching this article's slug
    for entry in reversed(entries):
        if entry.get("slug") == slug or not company_urn:
            company_urn = entry.get("company_urn", entry.get("urn", ""))
            reshare_urn = entry.get("reshare_urn", "")
            if entry.get("slug") == slug:
                break

    if not company_urn:
        log.warning("[nova] Could not find company URN in post_log.json")
    if not reshare_urn:
        log.warning("[nova] Could not find reshare URN in post_log.json")

    log.info(f"[nova] company_urn={company_urn} reshare_urn={reshare_urn}")
    return {
        "company_urn": company_urn,
        "reshare_urn": reshare_urn,
    }
