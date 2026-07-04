"""Maya — Visual Director (CC subagent).

Receives Quill's article copy path + spec from Marco.
Sources 2 header images (currently from Pexels free stock), uses one as the
article cover and saves the other as the alt, merges copy + image into the
article skeleton, and stages the files.

Image acquisition order: canonical-on-disk → handoff/ready pickup →
Pexels stock (PEXELS_API_KEY in agents/.env) → empty stub placeholder.
AI generation (_generate_images_higgsfield) is retained but dormant —
reserved for a later "custom images" build.
"""

import re
import subprocess
from pathlib import Path

from agents.base import call_cc_agent, read_file, write_file, REPO_ROOT, log
from agents.prompts import MAYA_PROMPT


def _generate_images_stub(spec: dict, primary_path: str, alt_path: str):
    """
    Placeholder: create empty image files so the pipeline can run without
    a Higgsfield API key. Replace this block with real Higgsfield calls
    once HIGGSFIELD_API_KEY is set in agents/.env.
    """
    import os
    for p in [primary_path, alt_path]:
        full = REPO_ROOT / p
        full.parent.mkdir(parents=True, exist_ok=True)
        if not full.exists():
            full.write_bytes(b"")   # empty placeholder
            log.warning(f"[maya] stub image created: {p}")


def _generate_images_higgsfield(spec: dict, primary_path: str, alt_path: str):
    """
    Real Higgsfield image generation. Called when HIGGSFIELD_API_KEY (+ SECRET) is set.
    Generates 2 images, resizes to 1200×630 JPG via PIL.

    API reference confirmed against https://docs.higgsfield.ai (2026-07-02):
      - Base URL: https://platform.higgsfield.ai
      - Auth header: "Authorization: Key {api_key}:{api_key_secret}"
      - Submit:  POST /{model_id}  ->  {"status": "queued", "status_url": ...}
      - Poll:    GET  {status_url} ->  {"status": "completed", "images": [{"url": ...}]}
        (status also cycles through in_progress; failed/nsfw are terminal errors)

    model_id: defaults to the documented flagship "higgsfield-ai/soul/standard".
    The project's intended model is Nano Banana Pro (CLI job_set_type
    "nano_banana_2"), but its exact REST model_id path was not confirmed in the
    docs fetched for this change — run `higgsfield model list` (official CLI) or
    check the Models Gallery in the dashboard, then set HIGGSFIELD_MODEL_ID in
    agents/.env to override the default before relying on this in a live run.
    """
    import os
    import time
    import urllib.request
    import urllib.error
    import json

    api_key = os.environ.get("HIGGSFIELD_API_KEY", "")
    api_secret = os.environ.get("HIGGSFIELD_API_SECRET", "")
    if not api_key or not api_secret:
        raise RuntimeError(
            "[maya] HIGGSFIELD_API_KEY and HIGGSFIELD_API_SECRET must both be set in agents/.env"
        )

    model_id = os.environ.get("HIGGSFIELD_MODEL_ID", "higgsfield-ai/soul/standard")
    auth_header = f"Key {api_key}:{api_secret}"

    # Build the visual concept from category + mood — NOT the literal article
    # title. Feeding the title text into the prompt causes text-capable models
    # (Nano Banana especially) to render it as on-screen signage/captions,
    # which bakes article-specific text into what should be a reusable photo.
    category = spec.get("category", "technology")
    mood = spec.get("mood", "analytical")
    concept = f"{category} — {mood} mood"
    no_text = (
        "photorealistic editorial photography, no text, no captions, no typography, "
        "no signage, no on-screen UI, no readable text of any kind anywhere in the image"
    )

    prompts = [
        f"{concept}, wide establishing shot, {no_text}",
        f"{concept}, close detail composition, dramatic lighting, {no_text}",
    ]

    def _submit(prompt: str) -> dict:
        payload = json.dumps({
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "resolution": "720p",
        }).encode()
        req = urllib.request.Request(
            f"https://platform.higgsfield.ai/{model_id}",
            data=payload,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="ignore")
            raise RuntimeError(f"[maya] Higgsfield submit failed ({exc.code}): {body}") from exc

    def _poll(status_url: str, timeout_s: int = 180, interval_s: int = 5) -> dict:
        deadline = time.time() + timeout_s
        req = urllib.request.Request(
            status_url,
            headers={"Authorization": auth_header, "Accept": "application/json"},
        )
        while time.time() < deadline:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            status = data.get("status")
            if status == "completed":
                return data
            if status in ("failed", "nsfw"):
                raise RuntimeError(f"[maya] Higgsfield generation {status}: {data.get('error', '')}")
            time.sleep(interval_s)
        raise RuntimeError(f"[maya] Higgsfield generation timed out after {timeout_s}s: {status_url}")

    generated_paths = []
    for i, prompt in enumerate(prompts):
        submitted = _submit(prompt)
        if submitted.get("status") == "completed":
            result = submitted  # some models may resolve synchronously
        else:
            status_url = submitted.get("status_url")
            if not status_url:
                raise RuntimeError(f"[maya] Higgsfield response missing status_url: {submitted}")
            result = _poll(status_url)

        images = result.get("images") or []
        if not images:
            raise RuntimeError(f"[maya] Higgsfield completed with no images: {result}")
        img_url = images[0]["url"]

        # Download
        tmp_path = REPO_ROOT / f"_maya_tmp_{i}.jpg"
        urllib.request.urlretrieve(img_url, tmp_path)
        generated_paths.append(tmp_path)

    # Resize both to 1200×630 and save.
    for tmp, dest in zip(generated_paths, [primary_path, alt_path]):
        _save_header_image(tmp, dest)


def _save_header_image(tmp_path, dest_rel: str):
    """Resize a downloaded image to the 1200×630 header size and save it as
    JPEG at dest_rel (repo-relative), then delete the temp file."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("[maya] Pillow not installed — run: pip install Pillow")
    dest = REPO_ROOT / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(tmp_path) as img:
        img = img.convert("RGB").resize((1200, 630), Image.LANCZOS)
        img.save(dest, "JPEG", quality=90)
    Path(tmp_path).unlink(missing_ok=True)


def _fetch_stock_images(spec: dict, primary_path: str, alt_path: str):
    """
    Source 2 header images from Pexels (free stock photography) based on the
    article's category + mood, then resize + save them to primary_path (used
    as the article cover) and alt_path (saved alternate). Same "grab 2, use 1,
    save 1" contract as generation — only the acquisition method differs.

    Requires PEXELS_API_KEY in agents/.env (free key: https://www.pexels.com/api/).
    Raises on any failure so the caller can fall back to stub placeholders.
    """
    import os
    import json
    import urllib.request
    import urllib.parse
    import urllib.error

    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        raise RuntimeError("[maya] PEXELS_API_KEY not set in agents/.env")

    category = spec.get("category", "technology")
    mood = spec.get("mood", "")
    query = f"{category} {mood}".strip() or "technology"

    # A real User-Agent is required — Pexels sits behind Cloudflare, which
    # bans the default "Python-urllib" signature (403 / error 1010).
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Pull a small pool so the primary and alt are visually distinct.
    params = urllib.parse.urlencode({
        "query": query,
        "orientation": "landscape",
        "per_page": 15,
        "size": "large",
    })
    req = urllib.request.Request(
        f"https://api.pexels.com/v1/search?{params}",
        headers={"Authorization": api_key, "User-Agent": ua},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="ignore")
        raise RuntimeError(f"[maya] Pexels search failed ({exc.code}): {body}") from exc

    photos = data.get("photos") or []
    if len(photos) < 2:
        raise RuntimeError(
            f"[maya] Pexels returned <2 photos for query '{query}' — cannot fill primary + alt"
        )

    # Primary = top hit; alt = the next distinct photo in the pool.
    for i, (photo, dest) in enumerate(zip([photos[0], photos[1]], [primary_path, alt_path])):
        src = photo.get("src", {})
        img_url = src.get("large2x") or src.get("large") or src.get("original")
        if not img_url:
            raise RuntimeError(f"[maya] Pexels photo {photo.get('id')} has no usable src URL")
        tmp_path = REPO_ROOT / f"_maya_stock_tmp_{i}.jpg"
        dl = urllib.request.Request(img_url, headers={"User-Agent": ua})
        with urllib.request.urlopen(dl, timeout=60) as r, open(tmp_path, "wb") as fh:
            fh.write(r.read())
        _save_header_image(tmp_path, dest)
        log.info(
            f"[maya] stock image #{i} from Pexels (photo id {photo.get('id')}, "
            f"query '{query}') -> {dest}"
        )


def _pickup_from_handoff(number: int, og_image: str, alt_image: str) -> bool:
    """Move any pre-staged images for this article from handoff/ready/ into their
    canonical locations, so a pipeline run reuses what the Maya batch already made
    instead of regenerating. Matches by article number (slug-agnostic); only moves
    real images (>1KB), so empty stubs are ignored. Returns True if anything moved.
    """
    import shutil
    ready_dir = REPO_ROOT / "handoff" / "ready"
    if not ready_dir.exists():
        return False

    padded = str(number).zfill(3)
    moved = False

    # Primary cover: handoff/ready/aima-NNN-*.jpg (excluding the -alt variant)
    primaries = [p for p in ready_dir.glob(f"aima-{padded}-*.jpg")
                 if not p.stem.endswith("-alt") and p.stat().st_size > 1024]
    if primaries:
        dest = REPO_ROOT / og_image
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(primaries[0]), str(dest))
        log.info(f"[maya] handoff pickup: {primaries[0].name} -> {og_image}")
        moved = True

    # Alt image: handoff/ready/aima-NNN-*-alt.jpg
    alts = [p for p in ready_dir.glob(f"aima-{padded}-*-alt.jpg") if p.stat().st_size > 1024]
    if alts:
        dest = REPO_ROOT / alt_image
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(alts[0]), str(dest))
        log.info(f"[maya] handoff pickup: {alts[0].name} -> {alt_image}")
        moved = True

    return moved


def run(article_path: str, spec: dict) -> str:
    """
    Generate images, select best, have CC agent merge into article skeleton.
    Stages img files + merged HTML (no push).
    Returns the merged article path.
    """
    slug = spec["slug"]
    number = spec.get("number", 0)
    og_image = spec["og_image"]
    title = spec["title"]
    mood = spec.get("mood", "analytical")

    # Derive alt image path from og_image
    og_stem = Path(og_image).stem           # e.g. "aima-017-slug"
    alt_image = f"img/alt-img/{og_stem}-alt.jpg"

    # Verify article copy exists before anything else
    if not (REPO_ROOT / article_path).exists():
        raise RuntimeError(f"[maya] Article copy not found at: {article_path}")

    # ── Step 1: Image acquisition (canonical → handoff → Pexels stock → stub) ─
    import os
    _primary_full = REPO_ROOT / og_image
    _alt_full     = REPO_ROOT / alt_image

    def _both_ready() -> bool:
        return (
            _primary_full.exists() and _primary_full.stat().st_size > 1024 and
            _alt_full.exists()     and _alt_full.stat().st_size > 1024
        )

    if _both_ready():
        log.info("[maya] real images already on disk — skipping generation")
    else:
        # Reuse anything the Maya batch pre-staged in handoff/ready/ before paying
        # for generation.
        if _pickup_from_handoff(number, og_image, alt_image):
            log.info(f"[maya] used pre-staged image(s) from handoff/ready for #{number:03d}")

        if _both_ready():
            log.info("[maya] images ready (canonical/handoff) — skipping generation")
        elif os.environ.get("PEXELS_API_KEY"):
            log.info("[maya] sourcing stock header images via Pexels")
            try:
                _fetch_stock_images(spec, og_image, alt_image)
            except Exception as exc:
                log.warning(f"[maya] stock fetch failed ({exc}) — using stub placeholders")
                _generate_images_stub(spec, og_image, alt_image)
        else:
            log.info("[maya] PEXELS_API_KEY not set — using stub placeholder images")
            _generate_images_stub(spec, og_image, alt_image)

    # ── Step 2: CC agent merges copy into full article skeleton ──
    # Pass the file path — not inline content — to keep user_input small.
    # Maya's CC agent has --dangerously-skip-permissions so it can Read the file.
    publish_date = spec.get("publish_date", "")
    category = spec.get("category", "")
    author = spec.get("author", "")
    description = spec.get("description", title)   # fallback to title

    user_input = f"""\
ARTICLE_PATH: {article_path}
OG_IMAGE: {og_image}
ALT_IMAGE: {alt_image}

SPEC:
  slug={slug}  number={number}
  title="{title}"
  author="{author}"
  publish_date="{publish_date}"
  category="{category}"
  og:description="{description}"
  mood="{mood}"

Images are already saved to disk. Do not generate new images.
Read ARTICLE_PATH, build the complete merged HTML, write it to ARTICLE_PATH.\
"""

    article_full = REPO_ROOT / article_path

    log.info(f"[maya] calling CC agent to merge article skeleton: {slug}")
    call_cc_agent("maya", MAYA_PROMPT, user_input)

    # Check merge success: og:image tag must be wired (not just file size growth)
    merged_ok = False
    if article_full.exists():
        content = article_full.read_text(encoding="utf-8", errors="ignore")
        merged_ok = og_image in content and "og:image" in content
    if merged_ok:
        log.info(f"[maya] merge complete (og:image wired): {article_path}")
    else:
        log.warning(
            f"[maya] CC agent did not wire og:image into article — "
            f"skeleton merge may be incomplete for {article_path}"
        )

    log.info(f"[maya] merge complete: {article_path}")

    # ── Step 3: Stage files (no push) ────────────────────────
    files_to_stage = [og_image, alt_image, article_path]
    try:
        subprocess.run(
            ["git", "add"] + files_to_stage,
            cwd=REPO_ROOT, check=True,
        )
        log.info(f"[maya] staged: {files_to_stage}")
    except subprocess.CalledProcessError as exc:
        log.warning(f"[maya] git add failed (non-fatal): {exc}")

    return article_path
