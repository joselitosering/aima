"""
One-shot script: fetch a fresh, non-duplicate Pexels image for article #029
and update the live article + git push.

Run from the aima repo root:
    python fix_029_image.py
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────
env_file = Path("agents/.env")
for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent))
from agents.maya import _fetch_stock_images, _save_header_image
from agents.base import REPO_ROOT

PRIMARY = "img/articles/aima-029-the-lab-that-runs-itself.jpg"
ALT     = "img/alt-img/aima-029-the-lab-that-runs-itself-alt.jpg"
ARTICLE = "articles/aima-article-the-lab-that-runs-itself-029.html"

# ── Build exclusion set (all covers EXCEPT #029) ──────────────────────────────
base = REPO_ROOT / "img/articles"
existing_hashes: dict[str, str] = {}   # hash → filename
for p in base.glob("aima-*.jpg"):
    if "029" not in p.name:
        h = hashlib.md5(p.read_bytes()).hexdigest()
        existing_hashes[h] = p.name

print(f"Excluding {len(existing_hashes)} existing cover hashes")

# ── Fetch a fresh non-duplicate image ────────────────────────────────────────
spec = {"category": "AI Science", "mood": "analytical", "slug": "the-lab-that-runs-itself"}
print("Fetching replacement image from Pexels…")
_fetch_stock_images(spec, PRIMARY, ALT, exclude_hashes=set(existing_hashes.keys()))

new_hash = hashlib.md5((REPO_ROOT / PRIMARY).read_bytes()).hexdigest()
print(f"New primary hash: {new_hash[:8]}")
if new_hash in existing_hashes:
    print(f"ERROR: still a duplicate of {existing_hashes[new_hash]}")
    sys.exit(1)
print("✓ Image is unique")

# ── Update og:image URL in the article HTML ───────────────────────────────────
article_path = REPO_ROOT / ARTICLE
html = article_path.read_text(encoding="utf-8")

# The image path in URLs is the same slug-based name — no URL change needed
# since we're replacing the file in-place. But verify og:image is wired correctly.
img_filename = Path(PRIMARY).name
if img_filename not in html:
    print(f"WARNING: {img_filename} not found in article HTML — og:image may need manual update")
else:
    print(f"✓ og:image already references {img_filename}")

# ── Stage + push ──────────────────────────────────────────────────────────────
files = [PRIMARY, ALT, ARTICLE]
subprocess.run(["git", "add"] + files, cwd=REPO_ROOT, check=True)
subprocess.run(["git", "commit", "-m",
    "fix(maya): replace duplicate #029 cover image (was identical to #026)"],
    cwd=REPO_ROOT, check=True)
subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
print("✓ Pushed — aima.productions will update within ~60s")
