"""Nova — Marketing Agent (Pure Python, no LLM calls).

Posts a published article to the AIMA company page + reshares it to Joselito's
personal profile via linkedin_pipeline/linkedin_poster.py, then logs the post to
post_log.json for Echo's analytics. (pipeline.py was retired — Nova posts directly.)
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

from agents.base import REPO_ROOT, read_json, log


def _head_ok(url: str) -> bool:
    """Return True if URL responds with HTTP 200."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError):
        return False


def _log_post(post_id, filename, title, persona, reshare_id=None):
    """Append the new post to post_log.json so Echo can collect analytics later."""
    p = REPO_ROOT / "linkedin_pipeline" / "post_log.json"
    entries = read_json("linkedin_pipeline/post_log.json")
    if not isinstance(entries, list):
        entries = []
    entry = {
        "post_id": post_id,
        "article": filename,
        "title": title,
        "persona": persona or "joselito",
        "posted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "analytics_collected": False,
    }
    if reshare_id:
        entry["reshare_id"] = reshare_id
    entries.append(entry)
    p.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    log.info("[nova] logged to post_log.json for Echo analytics")


def run(spec: dict, live_url: str, dry_run: bool = False) -> dict:
    """
    Post one published article to the AIMA company page + personal reshare via
    linkedin_poster, then log it to post_log.json.

    Returns: { "company_urn": "...", "reshare_urn": "..." }
    Raises RuntimeError on failure.
    """
    filename = spec["filename"]
    og_image_url = f"https://joselitosering.github.io/aima/{spec['og_image']}"

    if dry_run:
        log.info(f"[nova] DRY RUN — would post {filename} to LinkedIn (company + reshare)")
        log.info(f"[nova] DRY RUN — article live at: {live_url}")
        return {"company_urn": "urn:li:share:DRY_RUN", "reshare_urn": "urn:li:share:DRY_RUN"}

    # Dedup guard — block accidental double-posts within a 10-minute window.
    # Intentional reposts (bad post deleted + rerun) are older than 10 min and pass through.
    entries = read_json("linkedin_pipeline/post_log.json")
    if isinstance(entries, list):
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        for e in entries:
            if e.get("article") != filename:
                continue
            try:
                posted_at = datetime.fromisoformat(e["posted_at"]).replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                continue
            if posted_at >= cutoff:
                raise RuntimeError(
                    f"[nova] dedup block: {filename} was already posted {int((datetime.now(timezone.utc) - posted_at).total_seconds())}s ago "
                    f"(post_id={e.get('post_id')}). Delete the LinkedIn post first, then rerun after 10 min."
                )

    # Pre-check 1 — article must be live (Porter confirms deploy first)
    if not _head_ok(og_image_url):
        raise RuntimeError(
            f"[nova] Article image not live yet: {og_image_url}\n"
            "       Porter should have confirmed deploy before Nova runs."
        )
    # Pre-check 2 — LinkedIn credentials
    if not (REPO_ROOT / "linkedin_pipeline" / ".env").exists():
        raise RuntimeError("[nova] linkedin_pipeline/.env not found — LinkedIn credentials missing.")

    article_path = REPO_ROOT / "articles" / filename
    if not article_path.exists():
        raise RuntimeError(f"[nova] Article not found on disk: {article_path}")
    content = article_path.read_text(encoding="utf-8", errors="replace")
    article = {"name": filename, "html_url": live_url, "content": content}

    # Post directly via linkedin_poster (lazy import — it loads creds at import time).
    sys.path.insert(0, str(REPO_ROOT / "linkedin_pipeline"))
    from linkedin_poster import (
        post_to_linkedin, reshare_to_personal, extract_metadata,
        extract_persona, add_utm, build_personal_commentary,
    )

    log.info(f"[nova] posting to company page: {filename}")
    company_urn = post_to_linkedin(article)

    title, description, source_url = extract_metadata(content, filename, live_url)
    persona = extract_persona(content)
    source_url_reshare = add_utm(source_url, filename, content="personal_reshare")
    commentary = build_personal_commentary(
        title, description, source_url_reshare, persona or "joselito", html_content=content
    )
    reshare_urn = reshare_to_personal(company_urn, title, commentary=commentary)
    if reshare_urn:
        log.info(f"[nova] personal reshare: {reshare_urn}")

    _log_post(company_urn, filename, title, persona, reshare_urn)
    log.info(f"[nova] done: company={company_urn} reshare={reshare_urn}")
    return {"company_urn": company_urn, "reshare_urn": reshare_urn}
