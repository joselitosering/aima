"""run_cowork.py — Cowork-aware pipeline runner.

The standard pipeline subprocess (run.py) has no access to Cowork MCPs.
This script bridges that gap with three modes:

  --check
      Read next article spec (using dry-run stub, no CC call).
      If header images are missing or stubs (<1 KB), print a JSON manifest
      and exit 10.  Cowork reads the manifest, calls mcp__cb1bb852__generate_image
      for each prompt, then calls --save-image to land the results on disk.
      Exit 0 means images are already ready.

  --save-image --url URL --path REL_PATH [--width W] [--height H]
      Download URL, resize to 1200x630 JPG via Pillow, save to
      REPO_ROOT/REL_PATH.  Used by Cowork after image generation completes.

  (no flags / --dry-run)
      Pass-through to run.py — full pipeline or dry-run.

Exit codes:
  0   success
  1   pipeline / save error
  10  images missing (--check mode); Cowork must generate before running
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).parent


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _load_spec_stub() -> dict:
    """Get next article spec via dry-run stub — zero CC tokens."""
    from agents import base
    base.DRY_RUN = True
    from agents import priya
    return priya.run()


def _image_ready(path: str) -> bool:
    """True if file exists and is larger than a stub (>1 KB)."""
    full = REPO_ROOT / path
    return full.exists() and full.stat().st_size > 1024


def _alt_path(og_image: str) -> str:
    stem = Path(og_image).stem          # e.g. "aima-018-diagnosis-by-algorithm"
    return f"img/alt-img/{stem}-alt.jpg"


# ─────────────────────────────────────────────────────────────
# --check
# ─────────────────────────────────────────────────────────────

def cmd_check():
    spec = _load_spec_stub()
    og   = spec["og_image"]
    alt  = _alt_path(og)

    missing = []
    for role, path in [("primary", og), ("alt", alt)]:
        if not _image_ready(path):
            missing.append({"role": role, "path": path})

    if not missing:
        print(json.dumps({"status": "ready", "article_number": spec["number"]}))
        sys.exit(0)

    manifest = {
        "status": "needs_images",
        "article_number": spec["number"],
        "slug": spec["slug"],
        "title": spec["title"],
        "mood": spec.get("mood", "analytical"),
        "primary_path": og,
        "alt_path": alt,
        # Prompts for Cowork to pass to mcp__cb1bb852__generate_image
        "prompts": {
            "primary": (
                f"{spec['title']} — {spec.get('mood', 'analytical')} editorial photography, "
                "wide establishing shot, cinematic 16:9, magazine cover quality"
            ),
            "alt": (
                f"{spec['title']} — {spec.get('mood', 'analytical')} close detail composition, "
                "dramatic lighting, 16:9, editorial style"
            ),
        },
        # Recommended model: soul_2 for editorial/magazine quality
        "recommended_model": "soul_2",
        "aspect_ratio": "16:9",
    }

    # Also write to disk so Cowork can read it back if needed
    manifest_path = REPO_ROOT / "image_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    sys.exit(10)


# ─────────────────────────────────────────────────────────────
# --save-image
# ─────────────────────────────────────────────────────────────

def cmd_save_image(url: str, rel_path: str, width: int = 1200, height: int = 630):
    """Download url, resize to width×height JPG, save to REPO_ROOT/rel_path."""
    try:
        from PIL import Image
        import io
    except ImportError:
        print("[run_cowork] Pillow not installed — run: pip install Pillow --break-system-packages",
              file=sys.stderr)
        sys.exit(1)

    dest = REPO_ROOT / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"[run_cowork] downloading: {url}")
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = resp.read()

    with Image.open(io.BytesIO(data)) as img:
        img = img.convert("RGB")
        img = img.resize((width, height), Image.LANCZOS)
        img.save(dest, "JPEG", quality=90)

    print(f"[run_cowork] saved: {rel_path} ({dest.stat().st_size:,} bytes)")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cowork-aware AIMA pipeline runner")
    parser.add_argument("--check", action="store_true",
                        help="Check if article images are ready; exit 10 if not")
    parser.add_argument("--save-image", action="store_true",
                        help="Download + resize an image URL to disk")
    parser.add_argument("--url",  default="", help="Image URL (--save-image)")
    parser.add_argument("--path", default="", help="Relative dest path (--save-image)")
    parser.add_argument("--width",  type=int, default=1200)
    parser.add_argument("--height", type=int, default=630)
    parser.add_argument("--dry-run", action="store_true",
                        help="Pass-through: run pipeline in dry-run mode")
    args = parser.parse_args()

    if args.check:
        cmd_check()
        return

    if args.save_image:
        if not args.url or not args.path:
            print("[run_cowork] --save-image requires --url and --path", file=sys.stderr)
            sys.exit(1)
        cmd_save_image(args.url, args.path, args.width, args.height)
        return

    # Pass-through to standard pipeline
    from agents import base, marco
    if args.dry_run:
        base.DRY_RUN = True
    marco.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
