#!/usr/bin/env python3
"""instagram_carousel.py — post to Instagram from inbox/posts/ (single images).

  inbox/posts/<name>.jpg          -> one single-image post

STREAMLINED (2026-07-16): carousels and Reels are paused on purpose while we
prove the single-post path is seamless over a week of real unattended runs.
The carousel/Reel functions (prepare_carousel, prepare_reel, and their Graph
API helpers) are still in this file, just unreferenced from scan()/main() —
re-enabling them later is a scan()/main() change, not a rewrite.

Posting cadence is NOT "run N times a day": each invocation checks a
persisted schedule (state/schedule.json) and does nothing at all unless it's
actually due. After every successful publish, the next slot is re-rolled:
1-2 days later (IG_MIN_GAP_DAYS/IG_MAX_GAP_DAYS), at a random time inside one
of IG_POST_WINDOWS (default 11:00-15:00 or 18:00-21:00, America/Los_Angeles).
The OS task can fire every 15 min all day — nearly every check is a no-op
local timestamp comparison, no network calls, so frequent checks cost nothing
and just tighten how close to the rolled time the post actually goes out.

Drag files into inbox/posts/ (or let the schedule do it) — each file dropped
in is one post, no manual grouping needed.

Per-item caption overrides (optional, same-stem sibling files):
  <name>.brief.txt    — steers the AI caption for that one item
  <name>.caption.txt  — used verbatim, skips AI generation
(For carousels these live *inside* the set subfolder as brief.txt/caption.txt,
 unchanged from before.)

Why each step is mandatory:
  * The Instagram Graph API fetches media from PUBLIC https URLs only, and
    images must be JPEG. Midjourney exports PNG on localhost -> Cloudinary
    hosting + JPEG conversion are both required, not optional.
  * A carousel is a 3-call flow: N child containers -> 1 carousel container ->
    publish. A single post or Reel is 2 calls: 1 container -> publish.
    Containers EXPIRE ~24h after creation, so pending items must be approved
    same-day (only relevant if IG_AUTO_PUBLISH=false).

Commands:
  python instagram_carousel.py                    # scan all 3 folders, prepare new items
  python instagram_carousel.py --dry-run          # caption only (no upload/IG)
  python instagram_carousel.py --list-pending     # show items awaiting approval
  python instagram_carousel.py --approve KIND/NAME   # e.g. posts/sunset, reels/clip1
  python instagram_carousel.py --approve-all
  python instagram_carousel.py --reject KIND/NAME

Env: this module's own .env (instagram_pipeline/.env) — see README.md.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageOps

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# AI-generated captions routinely include emoji; Windows' console codepage
# (cp1252) can't encode them and print() would crash mid-run. Force UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# --- paths & config -------------------------------------------------------
HERE = Path(__file__).resolve().parent
MODULE_ROOT = HERE               # instagram_pipeline/ is flat under the aima repo
load_dotenv(MODULE_ROOT / ".env")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v"}
MAX_CAROUSEL = 10                    # Instagram hard limit
GRAPH = "https://graph.instagram.com"
IG_ASPECT_MIN = 0.8                  # 4:5  portrait  (feed lower bound)
IG_ASPECT_MAX = 1.91                 # 1.91:1 landscape (feed upper bound)
MAX_EDGE = 1440                      # px; IG downsamples anything larger anyway


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.environ.get(name, default)
    if required and not val:
        sys.exit(f"[FATAL] missing required env var: {name}")
    return val


def cfg() -> dict:
    inbox = Path(env("IG_INBOX_DIR", str(MODULE_ROOT / "inbox")))
    return {
        "inbox": inbox,
        "posts": Path(env("IG_POSTS_DIR", str(inbox / "posts"))),
        "carousels": Path(env("IG_CAROUSELS_DIR", str(inbox / "carousels"))),
        "reels": Path(env("IG_REELS_DIR", str(inbox / "reels"))),
        "archive": Path(env("IG_ARCHIVE_DIR", str(MODULE_ROOT / "archive"))),
        "rejected": Path(env("IG_REJECTED_DIR", str(MODULE_ROOT / "rejected"))),
        "failed": Path(env("IG_FAILED_DIR", str(MODULE_ROOT / "failed"))),
        "state": MODULE_ROOT / "state",
        "work": MODULE_ROOT / ".work",
        "log": MODULE_ROOT / "carousel_log.jsonl",
        "ig_user_id": env("IG_USER_ID", required=True),
        "ig_token": env("IG_ACCESS_TOKEN", required=True),
        "graph_version": env("GRAPH_API_VERSION", "v21.0"),
        "auto_publish": env("IG_AUTO_PUBLISH", "true").lower() == "true",
        "fit": env("IG_FIT", "pad").lower(),          # pad | crop
        "audience": env("IG_AUDIENCE", "a general Instagram audience"),
        "brand_hashtag": env("IG_BRAND_HASHTAG", "aimaproductions"),
        "bio_link": env("IG_BIO_LINK", "http://aima.productions"),
        "cli_model": env("IG_CLI_MODEL", "haiku"),  # claude CLI model alias
        # cadence: "N per day" is deliberately NOT how this works — see
        # schedule_path()/roll_next_slot() below.
        "timezone": env("IG_TIMEZONE", "America/Los_Angeles"),
        "post_windows": env("IG_POST_WINDOWS", "11:00-15:00,18:00-21:00"),
        "min_gap_days": int(env("IG_MIN_GAP_DAYS", "1")),
        "max_gap_days": int(env("IG_MAX_GAP_DAYS", "2")),
        "quarantine_after": int(env("IG_QUARANTINE_AFTER", "3")),
    }


def log_event(c: dict, **fields) -> None:
    c["log"].parent.mkdir(parents=True, exist_ok=True)
    fields["ts"] = datetime.now(timezone.utc).astimezone().isoformat()
    with open(c["log"], "a", encoding="utf-8") as f:
        f.write(json.dumps(fields, ensure_ascii=False) + "\n")


# --- image normalization --------------------------------------------------
def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def normalize(src: Path, dst: Path, target_ratio: float, fit: str,
              bg=(255, 255, 255)) -> None:
    """Convert to RGB JPEG, force width/height ratio to target_ratio, and cap
    the longest edge."""
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    w, h = im.size
    cur = w / h
    if fit == "crop":
        if cur > target_ratio:                 # too wide -> trim sides
            nw = round(h * target_ratio)
            left = (w - nw) // 2
            im = im.crop((left, 0, left + nw, h))
        elif cur < target_ratio:               # too tall -> trim top/bottom
            nh = round(w / target_ratio)
            top = (h - nh) // 2
            im = im.crop((0, top, w, top + nh))
    else:                                       # pad (default; never crops art)
        if cur > target_ratio:
            nh = round(w / target_ratio)
            canvas = Image.new("RGB", (w, nh), bg)
            canvas.paste(im, (0, (nh - h) // 2))
            im = canvas
        elif cur < target_ratio:
            nw = round(h * target_ratio)
            canvas = Image.new("RGB", (nw, h), bg)
            canvas.paste(im, ((nw - w) // 2, 0))
            im = canvas
    w, h = im.size
    longest = max(w, h)
    if longest > MAX_EDGE:
        s = MAX_EDGE / longest
        im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "JPEG", quality=90, optimize=True)


def target_ratio_for(first: Path) -> float:
    im = ImageOps.exif_transpose(Image.open(first)).convert("RGB")
    w, h = im.size
    return _clamp(w / h, IG_ASPECT_MIN, IG_ASPECT_MAX)


# --- Cloudinary -----------------------------------------------------------
def cloudinary_init() -> None:
    cloudinary.config(
        cloud_name=env("CLOUDINARY_CLOUD_NAME", required=True),
        api_key=env("CLOUDINARY_API_KEY", required=True),
        api_secret=env("CLOUDINARY_API_SECRET", required=True),
        secure=True,
    )


def upload_image(path: Path, folder: str) -> str:
    res = cloudinary.uploader.upload(str(path), folder=f"instagram/{folder}",
                                     resource_type="image")
    return res["secure_url"]


def upload_video(path: Path, folder: str) -> str:
    res = cloudinary.uploader.upload(str(path), folder=f"instagram/{folder}",
                                     resource_type="video")
    return res["secure_url"]


# --- caption generation (Claude Code CLI, headless, tapping the subscription) --
# Structure (not just "write something catchy"): a real keyword-led hook tied
# to what's actually in the frame, one line of genuine human curation/process
# (2026 platform trend rewards a visible human layer over AI-perfect visuals —
# relevant here since the source images are AI-generated), a casual save/share
# trigger, and exactly 5 hashtags (broad/niche/niche/community/branded) — not
# 20-30. Hashtag volume stopped helping; a caption-only link is a dead weight,
# so the CTA stays casual and never leads with a link.
#
# Runs `claude -p` headlessly instead of an API. Deliberately invoked with cwd
# set OUTSIDE the aima repo (a neutral temp dir) — running it from inside the
# repo auto-loads the full CLAUDE.md/memory context into a Sonnet-priced cache
# write on every single call (measured ~$0.34 vs ~$0.055 from a neutral dir).
CAPTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"},
                    "minItems": 5, "maxItems": 5},
        "alt_text": {"type": "string"},
    },
    "required": ["caption", "hashtags", "alt_text"],
}


def generate_caption(c: dict, brief: str, kind_label: str,
                     affiliate: str | None = None,
                     image_path: Path | None = None) -> tuple[str, str]:
    link_note = (
        f"This post promotes a specific affiliate product via the bio link: "
        f"{affiliate}. Weave a natural, low-pressure mention of it into the CTA "
        f'line, ending with "link in bio". Do not write out any URL. Do not add '
        f"any disclosure/ad label yourself — that is handled separately."
        if affiliate else
        "No specific product to promote here — if you reference the project at "
        'all, a light "link in bio" mention is enough, not required every time.'
    )
    # The image is copied into a fresh temp dir that becomes the subprocess's
    # cwd (below), so it's referenced here by bare filename, already inside
    # the default allowed working directory -- no --add-dir grant needed
    # (that combined with --permission-mode was proving unreliable headless).
    # NOTE (2026-07-16): the previous phrasing here ("Your FIRST action,
    # before anything else, MUST be...") was intermittently triggering the
    # CLI's own prompt-injection caution -- confirmed via IG_CLI_DEBUG=1 on
    # three real failures, where the model explicitly declined, named the
    # phrasing as looking injected, and asked for confirmation instead of
    # emitting JSON (headless has no way to answer, so that's a guaranteed
    # failure). Not a bug to route around -- rewritten below to read as an
    # ordinary task brief instead of an imperative command, which is the
    # actual fix (reduces the false-positive rate; doesn't force compliance).
    first_step = (
        f"There's an image saved as {image_path.name} in this working "
        "directory. Please look at it with the Read tool before writing the "
        "caption below -- it needs to describe what the photo actually "
        "shows: subject, gender/appearance, setting, pose, clothing, colors. "
        "Don't guess these from the brief text; if the image contradicts the "
        "brief, go with what's in the image. If something isn't clearly "
        "visible, describe it vaguely rather than inventing a detail.\n"
        if image_path else
        "No image is available for this item (e.g. a video) — write from the "
        "brief alone, and keep any visual claims general rather than specific.\n"
    )
    prompt = (
        f"{first_step}"
        "This runs headlessly with no one available to answer follow-up "
        "questions, so please use your best judgment on any smaller open "
        "questions below and produce the JSON output directly rather than "
        "pausing to ask.\n\n"
        "You are a social media copywriter writing an Instagram caption. Follow "
        "this exact structure:\n"
        "1. Hook line — lead with the real subject/keyword plainly, tied to "
        "what's actually visible. No clickbait, no keyword stuffing.\n"
        "2. One sentence of genuine human process/curation — what was kept, "
        "changed, or noticed after generating this piece. This is an "
        "AI-generated visual; naming the human decision behind it is the "
        "point, not something to hide.\n"
        "3. A casual line that invites a comment, save, or share (e.g. a "
        'question). If a link is relevant at all, write the plain words '
        '"link in bio" as normal sentence text — never write out a raw URL, '
        "and never prefix it with # or treat it as a hashtag. Keep it one "
        "throwaway phrase, not the caption's purpose.\n\n"
        f"Audience/niche: {c['audience']}\n"
        f"This is {kind_label}.\n"
        f"Branded hashtag to use as the 5th tag (no '#'): {c['brand_hashtag']}\n"
        f"{link_note}\n"
        f"Creative brief (context only — the image, if attached, is the "
        f"source of truth for anything visual): {brief}\n\n"
        "Output exactly 5 hashtags in broad/niche/niche/community/branded "
        "order, no '#' in the array, no banned/spammy tags. alt_text is a "
        "plain factual description for accessibility/search — not marketing "
        "copy. Caption under 1800 chars."
    )

    # subprocess.run's list form doesn't resolve Windows .cmd/.ps1 shims the
    # way a shell does (claude is npm-installed -> claude.cmd) -> resolve the
    # real executable path via shutil.which first.
    claude_exe = shutil.which("claude") or "claude"
    # bypassPermissions is safe here: --allowedTools is locked to Read only
    # (no Bash/Edit/Write) — headless mode has no TTY to approve an
    # interactive read prompt, so without this every call silently returns a
    # plain-text refusal instead of the JSON envelope.
    cmd = [claude_exe, "-p", prompt, "--model", c["cli_model"],
          "--output-format", "json", "--json-schema", json.dumps(CAPTION_JSON_SCHEMA),
          "--allowedTools", "Read", "--permission-mode", "bypassPermissions"]

    run_cwd = tempfile.gettempdir()
    tmp_img_dir = None
    if image_path:
        # NOTE (2026-07-16): tempfile.mkdtemp()'s randomly-named directory
        # was getting flagged by the CLI's own "suspicious Windows path
        # pattern" permission check and silently blocked -- confirmed via
        # IG_CLI_DEBUG=1: the model reported being unable to get the Read
        # approved, every time, regardless of prompt wording. bypassPermissions
        # does not override that check. Fix: a FIXED, human-named, reused
        # staging dir -- still outside the aima repo (avoids the CLAUDE.md
        # auto-load cost) but not a randomly-generated temp path.
        tmp_img_dir = Path.home() / ".ig_pipeline_cli_staging"
        tmp_img_dir.mkdir(parents=True, exist_ok=True)
        for old in tmp_img_dir.iterdir():
            old.unlink(missing_ok=True)
        shutil.copy2(image_path, tmp_img_dir / image_path.name)
        run_cwd = str(tmp_img_dir)

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=run_cwd)
    finally:
        if tmp_img_dir:
            for f in tmp_img_dir.iterdir():
                f.unlink(missing_ok=True)

    if os.environ.get("IG_CLI_DEBUG"):
        print("DEBUG cmd:", cmd)
        print("DEBUG returncode:", r.returncode)
        print("DEBUG stdout:", repr(r.stdout[:3000]))
        print("DEBUG stderr:", repr(r.stderr[:3000]))
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI exited {r.returncode}: {r.stderr[:500]}")
    envelope = json.loads(r.stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude CLI error: {envelope.get('result')}")
    cost = envelope.get("total_cost_usd", 0)
    print(f"    (caption cost: ${cost:.4f})")
    data = envelope["structured_output"]

    tags = _clean_hashtags(data.get("hashtags", []), c["brand_hashtag"])
    tagline = " ".join(f"#{t}" for t in tags)
    caption = f"{data['caption'].strip()}\n\n.\n.\n.\n{tagline}".strip()
    alt_text = data.get("alt_text", "").strip()
    return caption, alt_text


def _clean_hashtag(raw: str) -> str:
    """Instagram hashtags allow only letters/digits/underscore, no spaces or
    punctuation. Models sometimes emit multi-word or comma-joined 'tags' —
    take just the first token and strip anything else out."""
    first = raw.strip().lstrip("#").split(",")[0].strip()
    first = first.split()[0] if first.split() else first
    return re.sub(r"[^A-Za-z0-9_]", "", first)


def _clean_hashtags(raw_tags: list[str], brand_hashtag: str) -> list[str]:
    cleaned = [_clean_hashtag(t) for t in raw_tags]
    cleaned = [t for t in cleaned if t]
    seen: set[str] = set()
    deduped = []
    for t in cleaned:
        if t.lower() not in seen:
            seen.add(t.lower())
            deduped.append(t)
    tags = deduped[:4]
    brand = _clean_hashtag(brand_hashtag)
    if brand and brand.lower() not in {t.lower() for t in tags}:
        tags.append(brand)
    return tags[:5]


# --- Instagram Graph API --------------------------------------------------
def _graph_post(c: dict, path: str, **params) -> dict:
    params["access_token"] = c["ig_token"]
    r = requests.post(f"{GRAPH}/{c['graph_version']}/{path}", data=params, timeout=90)
    if not r.ok:
        raise RuntimeError(f"Graph POST {path} -> {r.status_code}: {r.text}")
    return r.json()


def _wait_finished(c: dict, container_id: str, tries: int, delay: int) -> None:
    for _ in range(tries):
        r = requests.get(f"{GRAPH}/{c['graph_version']}/{container_id}",
                         params={"fields": "status_code",
                                 "access_token": c["ig_token"]}, timeout=30)
        code = r.json().get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id} status={code}")
        time.sleep(delay)
    raise TimeoutError(f"container {container_id} not FINISHED in time")


def create_carousel_container(c: dict, urls: list[str], caption: str,
                              alt_text: str = "") -> str:
    children = []
    for u in urls:
        kwargs = {"image_url": u, "is_carousel_item": "true"}
        if alt_text:
            kwargs["alt_text"] = alt_text
        child = _graph_post(c, f"{c['ig_user_id']}/media", **kwargs)["id"]
        _wait_finished(c, child, tries=20, delay=3)
        children.append(child)
    parent = _graph_post(c, f"{c['ig_user_id']}/media",
                        media_type="CAROUSEL",
                        children=",".join(children), caption=caption)["id"]
    _wait_finished(c, parent, tries=20, delay=3)
    return parent


def create_single_image_container(c: dict, url: str, caption: str,
                                   alt_text: str = "") -> str:
    kwargs = {"image_url": url, "caption": caption}
    if alt_text:
        kwargs["alt_text"] = alt_text
    container = _graph_post(c, f"{c['ig_user_id']}/media", **kwargs)["id"]
    _wait_finished(c, container, tries=20, delay=3)
    return container


def create_reel_container(c: dict, url: str, caption: str) -> str:
    container = _graph_post(c, f"{c['ig_user_id']}/media",
                            media_type="REELS", video_url=url, caption=caption)["id"]
    # video processing is much slower than image processing -> wait longer
    _wait_finished(c, container, tries=60, delay=5)
    return container


def publish(c: dict, container_id: str) -> str:
    return _graph_post(c, f"{c['ig_user_id']}/media_publish",
                       creation_id=container_id)["id"]


# --- shared item helpers ---------------------------------------------------
def state_key(kind: str, name: str) -> str:
    return f"{kind}__{name}"


def state_path(c: dict, kind: str, name: str) -> Path:
    return c["state"] / f"{state_key(kind, name)}.json"


def item_brief(c: dict, ref: Path, kind_label: str, name: str) -> str:
    brief_f = ref.with_name(ref.stem + ".brief.txt") if ref.is_file() else ref / "brief.txt"
    if brief_f.exists():
        return brief_f.read_text(encoding="utf-8").strip()
    return f"A {kind_label} for {c['audience']}. Infer the subject from the name '{name}'."


def item_caption_override(ref: Path) -> str | None:
    cap_f = ref.with_name(ref.stem + ".caption.txt") if ref.is_file() else ref / "caption.txt"
    return cap_f.read_text(encoding="utf-8").strip() if cap_f.exists() else None


def item_affiliate(ref: Path) -> str | None:
    aff_f = ref.with_name(ref.stem + ".affiliate.txt") if ref.is_file() else ref / "affiliate.txt"
    return aff_f.read_text(encoding="utf-8").strip() if aff_f.exists() else None


def finish_prepared(c: dict, kind: str, name: str, container: str, item_count: int,
                    caption: str, source_paths: list[Path],
                    affiliate: str | None = None) -> None:
    c["state"].mkdir(parents=True, exist_ok=True)
    state_path(c, kind, name).write_text(json.dumps({
        "kind": kind, "name": name,
        "sources": [str(p) for p in source_paths],
        "caption": caption, "container_id": container, "affiliate": affiliate,
        "created": datetime.now(timezone.utc).astimezone().isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    log_event(c, event="prepared", kind=kind, name=name, container=container,
              items=item_count, affiliate=affiliate)
    if affiliate:
        print(f"    !! BIO LINK: point {c['bio_link']} at this offer before/while "
              f"it's live — \"{affiliate}\"")
    if c["auto_publish"]:
        publish_item(c, kind, name)
    else:
        print(f"    PENDING — review, then: --approve {kind}/{name}   (expires ~24h)")


def archive_sources(c: dict, dest_root: Path, kind: str,
                    source_paths: list[Path]) -> None:
    # Flat: dest_root/kind/<original name>. NOT dest_root/kind/<name>/<name> --
    # nesting under a same-named subfolder duplicated long Midjourney filenames
    # in the path and blew past Windows' 260-char MAX_PATH (WinError 3), and
    # for carousel folders it silently double-nested (dest already existed as
    # a dir, so shutil.move put the folder *inside* itself one level deeper).
    dest = dest_root / kind
    dest.mkdir(parents=True, exist_ok=True)
    for p in source_paths:
        if not p.exists():
            continue
        shutil.move(str(p), str(dest / p.name))
        if p.is_file():
            for suffix in (".brief.txt", ".caption.txt", ".affiliate.txt"):
                sib = p.with_name(p.stem + suffix)
                if sib.exists():
                    shutil.move(str(sib), str(dest / sib.name))


def publish_item(c: dict, kind: str, name: str) -> None:
    sp = state_path(c, kind, name)
    if not sp.exists():
        print(f"  no pending item '{kind}/{name}'")
        return
    st = json.loads(sp.read_text(encoding="utf-8"))
    media_id = publish(c, st["container_id"])
    print(f"  PUBLISHED {kind}/{name} -> media {media_id}")
    log_event(c, event="published", kind=kind, name=name, media_id=media_id)
    archive_sources(c, c["archive"], kind, [Path(p) for p in st["sources"]])
    shutil.rmtree(c["work"] / kind / name, ignore_errors=True)
    sp.unlink()


def reject_item(c: dict, kind: str, name: str) -> None:
    sp = state_path(c, kind, name)
    sources: list[Path] = []
    if sp.exists():
        st = json.loads(sp.read_text(encoding="utf-8"))
        sources = [Path(p) for p in st["sources"]]
        sp.unlink()
    else:
        # not prepared yet (e.g. dry-run) — best effort: locate by name under each kind dir
        for base in (c["posts"], c["reels"]):
            for ext in (IMAGE_EXTS if kind == "posts" else VIDEO_EXTS):
                cand = base / f"{name}{ext}"
                if cand.exists():
                    sources = [cand]
        if kind == "carousels" and (c["carousels"] / name).exists():
            sources = [c["carousels"] / name]
    if sources:
        archive_sources(c, c["rejected"], kind, sources)
    shutil.rmtree(c["work"] / kind / name, ignore_errors=True)
    log_event(c, event="rejected", kind=kind, name=name)
    print(f"  rejected {kind}/{name}")


def list_pending(c: dict) -> None:
    if not c["state"].exists() or not any(c["state"].glob("*.json")):
        print("no pending items")
        return
    for sp in sorted(c["state"].glob("*.json")):
        st = json.loads(sp.read_text(encoding="utf-8"))
        first = st["caption"].splitlines()[0]
        print(f"- {st['kind']}/{st['name']}  (prepared {st['created']})")
        print(f"    {first}")


# --- per-kind preparation ---------------------------------------------------
def prepare_post(c: dict, img: Path, dry_run: bool) -> None:
    name = img.stem
    print(f"  [posts/{name}] 1 image")

    # Normalize first (local, no network) so the caption model can actually
    # SEE the photo — captions used to be generated from the filename/brief
    # alone and would confidently guess wrong details (e.g. subject's gender)
    # that were never grounded in the actual image.
    work = c["work"] / "posts" / name
    work.mkdir(parents=True, exist_ok=True)
    dst = work / "post.jpg"
    normalize(img, dst, target_ratio_for(img), c["fit"])

    override = item_caption_override(img)
    if override:
        caption, alt_text = override, ""
    else:
        caption, alt_text = generate_caption(
            c, item_brief(c, img, "single Instagram photo", name), "a single-photo Instagram post",
            affiliate=item_affiliate(img), image_path=dst)
    print("    " + caption.replace("\n", "\n    "))
    if dry_run:
        return

    url = upload_image(dst, name)
    container = create_single_image_container(c, url, caption, alt_text)
    finish_prepared(c, "posts", name, container, 1, caption, [img], affiliate=item_affiliate(img))


def prepare_reel(c: dict, vid: Path, dry_run: bool) -> None:
    name = vid.stem
    print(f"  [reels/{name}] 1 video")
    override = item_caption_override(vid)
    if override:
        caption = override
    else:
        caption, _alt_text = generate_caption(
            c, item_brief(c, vid, "Instagram Reel (video)", name), "a video Reel",
            affiliate=item_affiliate(vid))
    print("    " + caption.replace("\n", "\n    "))
    if dry_run:
        return

    url = upload_video(vid, name)
    container = create_reel_container(c, url, caption)
    finish_prepared(c, "reels", name, container, 1, caption, [vid], affiliate=item_affiliate(vid))


def prepare_carousel(c: dict, set_dir: Path, dry_run: bool) -> None:
    name = set_dir.name
    imgs = sorted(p for p in set_dir.iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGE_EXTS)[:MAX_CAROUSEL]
    if not imgs:
        print(f"  skip carousels/{name}: no images")
        return
    print(f"  [carousels/{name}] {len(imgs)} image(s)")

    # Normalize first (local, no network) so the caption model can see the
    # actual photos rather than guessing from the brief/filename alone.
    ratio = target_ratio_for(imgs[0])
    work = c["work"] / "carousels" / name
    if work.exists():
        shutil.rmtree(work)
    jpgs = []
    for i, src in enumerate(imgs):
        dst = work / f"{i:02d}.jpg"
        normalize(src, dst, ratio, c["fit"])
        jpgs.append(dst)

    override = item_caption_override(set_dir)
    if override:
        caption, alt_text = override, ""
    else:
        caption, alt_text = generate_caption(
            c, item_brief(c, set_dir, f"{len(imgs)}-photo Instagram carousel", name),
            f"a {len(imgs)}-photo carousel", affiliate=item_affiliate(set_dir),
            image_path=jpgs[0])  # first image only -- one Read call, not one per photo
    print("    " + caption.replace("\n", "\n    "))
    if dry_run:
        return

    urls = [upload_image(j, name) for j in jpgs]
    container = create_carousel_container(c, urls, caption, alt_text)
    finish_prepared(c, "carousels", name, container, len(imgs), caption, [set_dir],
                    affiliate=item_affiliate(set_dir))


# --- posting schedule -------------------------------------------------------
# Cadence lives here, not in the OS task: the task can fire as often as it
# wants (every 15 min, all day) and 95%+ of those firings do nothing but
# compare two timestamps. The actual "when" is a randomly-rolled slot 1-2
# days out, inside one of IG_POST_WINDOWS, re-rolled fresh after every
# publish -- so the pattern an outside observer sees is "roughly every day
# or two, at a different time each time," not a metronome.
def _parse_windows(spec: str) -> list[tuple[int, int, int, int]]:
    out = []
    for part in spec.split(","):
        start, end = part.strip().split("-")
        sh, sm = (int(x) for x in start.split(":"))
        eh, em = (int(x) for x in end.split(":"))
        out.append((sh, sm, eh, em))
    return out


def _random_time_in_window(base_date: datetime, window: tuple[int, int, int, int],
                           tz: ZoneInfo) -> datetime:
    sh, sm, eh, em = window
    start = base_date.replace(hour=sh, minute=sm, second=0, microsecond=0, tzinfo=tz)
    end = base_date.replace(hour=eh, minute=em, second=0, microsecond=0, tzinfo=tz)
    return start + timedelta(seconds=random.uniform(0, (end - start).total_seconds()))


def roll_next_slot(c: dict, after: datetime) -> datetime:
    tz = ZoneInfo(c["timezone"])
    after = after.astimezone(tz)
    gap = random.randint(c["min_gap_days"], c["max_gap_days"])
    window = random.choice(_parse_windows(c["post_windows"]))
    return _random_time_in_window(after + timedelta(days=gap), window, tz)


def schedule_path(c: dict) -> Path:
    return c["state"] / "schedule.json"


def save_schedule(c: dict, next_post_at: datetime, anchor: datetime) -> None:
    c["state"].mkdir(parents=True, exist_ok=True)
    schedule_path(c).write_text(json.dumps({
        "anchor": anchor.isoformat(), "next_post_at": next_post_at.isoformat(),
    }, indent=2), encoding="utf-8")


def _last_published_at(c: dict) -> datetime | None:
    """Seed cadence from real history on first run under this scheduler, not
    from a blank slate -- avoids either firing immediately after a post that
    already went out today, or waiting a full extra gap for no reason."""
    if not c["log"].exists():
        return None
    last = None
    with open(c["log"], encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("event") == "published":
                ts = datetime.fromisoformat(rec["ts"])
                if last is None or ts > last:
                    last = ts
    return last


def load_or_init_schedule(c: dict) -> datetime:
    sp = schedule_path(c)
    if sp.exists():
        return datetime.fromisoformat(json.loads(sp.read_text(encoding="utf-8"))["next_post_at"])
    anchor = _last_published_at(c) or datetime.now(timezone.utc)
    next_at = roll_next_slot(c, anchor)
    save_schedule(c, next_at, anchor)
    return next_at


# --- failure tracking / quarantine ------------------------------------------
def _failcounts_path(c: dict) -> Path:
    return c["state"] / "failcounts.json"


def record_failure(c: dict, kind: str, name: str) -> int:
    fp = _failcounts_path(c)
    data = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
    key = state_key(kind, name)
    data[key] = data.get(key, 0) + 1
    c["state"].mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data[key]


def clear_failure(c: dict, kind: str, name: str) -> None:
    fp = _failcounts_path(c)
    if not fp.exists():
        return
    data = json.loads(fp.read_text(encoding="utf-8"))
    if data.pop(state_key(kind, name), None) is not None:
        fp.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --- scanning ---------------------------------------------------------------
def already_pending(c: dict, kind: str, name: str) -> bool:
    return state_path(c, kind, name).exists()


def scan(c: dict, dry_run: bool = False) -> None:
    """Posts-only while carousels/Reels are paused (see module docstring).
    Real runs (dry_run=False) publish AT MOST ONE item and stop -- cadence is
    enforced by the schedule gate in main(), not by "process everything you
    find." A failing item doesn't block the run: it's logged, its failure
    count goes up, and the scan moves on to the next file; three strikes
    (IG_QUARANTINE_AFTER) and it's moved to failed/posts/ instead of retrying
    forever. dry_run keeps the old "preview everything in the folder"
    behavior since that's a testing aid, not a live posting run."""
    found_any = False
    if not c["posts"].exists():
        print("nothing new in posts/")
        return

    for f in sorted(c["posts"].iterdir()):
        if not f.is_file() or f.suffix.lower() not in IMAGE_EXTS:
            continue
        found_any = True
        if already_pending(c, "posts", f.stem):
            print(f"  skip posts/{f.stem}: already pending")
            continue
        try:
            prepare_post(c, f, dry_run)
            if not dry_run:
                clear_failure(c, "posts", f.stem)
                now = datetime.now(timezone.utc)
                save_schedule(c, roll_next_slot(c, now), now)
                break  # one publish per run, by design
        except Exception as e:
            print(f"  ERROR posts/{f.stem}: {e}")
            log_event(c, event="error", kind="posts", name=f.stem, error=str(e))
            if not dry_run:
                n = record_failure(c, "posts", f.stem)
                if n >= c["quarantine_after"]:
                    archive_sources(c, c["failed"], "posts", [f])
                    clear_failure(c, "posts", f.stem)
                    log_event(c, event="quarantined", kind="posts", name=f.stem, attempts=n)
                    print(f"  quarantined posts/{f.stem} after {n} failures -> failed/posts/")

    if not found_any:
        print("nothing new in posts/")


def main() -> None:
    ap = argparse.ArgumentParser(description="Instagram posts/carousels/reels poster")
    ap.add_argument("--dry-run", action="store_true",
                    help="caption only; no Cloudinary/IG calls")
    ap.add_argument("--list-pending", action="store_true")
    ap.add_argument("--approve", metavar="KIND/NAME")
    ap.add_argument("--approve-all", action="store_true")
    ap.add_argument("--reject", metavar="KIND/NAME")
    args = ap.parse_args()

    c = cfg()

    def split_kind_name(spec: str) -> tuple[str, str]:
        if "/" not in spec:
            sys.exit(f"expected KIND/NAME (e.g. posts/sunset), got: {spec}")
        kind, name = spec.split("/", 1)
        if kind not in ("posts", "carousels", "reels"):
            sys.exit(f"unknown kind '{kind}' (expected posts, carousels, or reels)")
        return kind, name

    if args.list_pending:
        list_pending(c)
        return
    if args.approve:
        publish_item(c, *split_kind_name(args.approve))
        return
    if args.approve_all:
        for sp in sorted(c["state"].glob("*.json")):
            st = json.loads(sp.read_text(encoding="utf-8"))
            publish_item(c, st["kind"], st["name"])
        return
    if args.reject:
        reject_item(c, *split_kind_name(args.reject))
        return

    for d in (c["posts"], c["carousels"], c["reels"]):
        d.mkdir(parents=True, exist_ok=True)

    if not args.dry_run:
        # Schedule gate: this is what makes "every 15 min" on the OS task
        # side turn into "roughly every 1-2 days" in reality. --dry-run skips
        # this on purpose -- it's a caption preview tool, not a posting run.
        next_at = load_or_init_schedule(c)
        now = datetime.now(timezone.utc)
        if now < next_at:
            local = next_at.astimezone(ZoneInfo(c["timezone"]))
            print(f"not due yet — next post ~{local.strftime('%a %Y-%m-%d %I:%M %p %Z')}")
            return
        cloudinary_init()
    print(f"inbox: {c['inbox']}  |  auto_publish={c['auto_publish']}  fit={c['fit']}")
    scan(c, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
