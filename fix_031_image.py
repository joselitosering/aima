"""
One-shot script: replace article #031's duplicate cover + alt image with
freshly Higgsfield-generated art, then commit + push.

Why Higgsfield instead of Pexels: both #019/#025 (primary) and #024 (alt)
already have a duplicate on disk pointing at the same Pexels stock photo,
and Pexels/api.pexels.com wasn't reachable from the sandboxes used to
diagnose this, so the two replacement images below were generated directly
via Higgsfield (soul_location model) instead — precedent for this exact
fallback exists in this repo: see commit 7f1508d "chore(#027): replace
duplicate cover image with Higgsfield-generated art".

The two source images were generated 2026-07-28 (job IDs
c993bbf7-7a40-4b1e-b75b-bd6549e914c5 primary /
cfa0fec6-f3be-41a0-9e30-3b08b06727c0 alt) and are hosted at the CloudFront
URLs below — download+resize happens here so this script needs a normal
open internet connection (not the sandboxed one this was diagnosed from).

Run from the aima repo root:
    python fix_031_image.py

This stages + commits the two image files only (NOT the article HTML —
og:image points at the same filename, so no text needs to change, and the
article file already has an unrelated uncommitted diff in your working
tree that this script deliberately leaves alone). Review the diff before
it pushes if you want to double check; git push is the last line.
"""
import hashlib
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agents.maya import _existing_cover_hashes, _processed_hash
from agents.base import REPO_ROOT

PRIMARY = "img/articles/aima-031-the-clause-that-broke-the.jpg"
ALT     = "img/alt-img/aima-031-the-clause-that-broke-the-alt.jpg"

PRIMARY_SRC_URL = (
    "https://d8j0ntlcm91z4.cloudfront.net/user_36MQcEUxIQpwGb05N2qQDbQLpZ3/"
    "hf_20260728_201003_c993bbf7-7a40-4b1e-b75b-bd6549e914c5.png"
)
ALT_SRC_URL = (
    "https://d8j0ntlcm91z4.cloudfront.net/user_36MQcEUxIQpwGb05N2qQDbQLpZ3/"
    "hf_20260728_201006_cfa0fec6-f3be-41a0-9e30-3b08b06727c0.png"
)

primary_full = REPO_ROOT / PRIMARY
alt_full     = REPO_ROOT / ALT

# ── Build exclusion set (all covers EXCEPT #031's own, about to be replaced) ─
existing_hashes = _existing_cover_hashes(exclude=primary_full)
print(f"Excluding {len(existing_hashes)} existing cover hashes")

# ── Download the two generated images ────────────────────────────────────────
def _download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".src.png")
    urllib.request.urlretrieve(url, tmp)
    return tmp

print("Downloading Higgsfield-generated replacement images...")
primary_tmp = _download(PRIMARY_SRC_URL, primary_full)
alt_tmp     = _download(ALT_SRC_URL, alt_full)

# ── Verify neither is a duplicate BEFORE saving over the live files ─────────
primary_hash = _processed_hash(primary_tmp)
alt_hash     = _processed_hash(alt_tmp)
if primary_hash in existing_hashes:
    print("ERROR: generated primary image hashes as a duplicate of an existing cover — aborting.")
    sys.exit(1)
if alt_hash in existing_hashes or alt_hash == primary_hash:
    print("ERROR: generated alt image hashes as a duplicate — aborting.")
    sys.exit(1)
print("Both images verified unique against every other cover in img/articles/.")

# ── Resize to the standard 1200x630 header size and save in place ───────────
from PIL import Image
for tmp, dest in [(primary_tmp, primary_full), (alt_tmp, alt_full)]:
    with Image.open(tmp) as img:
        img = img.convert("RGB").resize((1200, 630), Image.LANCZOS)
        img.save(dest, "JPEG", quality=90)
    tmp.unlink(missing_ok=True)

print(f"Saved: {PRIMARY}")
print(f"Saved: {ALT}")

# ── Stage + commit + push (image files only — see module docstring) ────────
files = [PRIMARY, ALT]
subprocess.run(["git", "add"] + files, cwd=REPO_ROOT, check=True)
subprocess.run(["git", "commit", "-m",
    "fix(maya): replace duplicate #031 cover + alt image (was identical to #019/#025 and #024) "
    "with Higgsfield-generated art"],
    cwd=REPO_ROOT, check=True)
subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
print("Pushed — aima.productions will update within ~60s")
