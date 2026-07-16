#!/usr/bin/env python3
"""cloudinary_smoketest.py — verify the Cloudinary account works end-to-end.

Reads credentials from this module's own .env (CLOUDINARY_CLOUD_NAME / _API_KEY /
_API_SECRET) — NOT hardcoded, so nothing sensitive lands in a tracked file.

Run:  python cloudinary_smoketest.py
"""
from pathlib import Path

import cloudinary
import cloudinary.api
import cloudinary.uploader
from dotenv import load_dotenv
import os

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

# 1. Configure from .env (fail loudly if the secret wasn't filled in).
secret = os.environ.get("CLOUDINARY_API_SECRET", "")
if not secret or secret == "REPLACE_WITH_YOUR_API_SECRET":
    raise SystemExit("Set CLOUDINARY_API_SECRET in instagram_pipeline/.env first.")
cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=secret,
    secure=True,
)

# 2. Upload one of Cloudinary's public demo images into THIS account.
result = cloudinary.uploader.upload(
    "https://res.cloudinary.com/demo/image/upload/sample.jpg",
    public_id="ig_carousel_smoketest",
    overwrite=True,
)
print("secure_url:", result["secure_url"])
print("public_id: ", result["public_id"])

# 3. Fetch details back via the Admin API (this also proves the secret is valid).
info = cloudinary.api.resource(result["public_id"])
print(f"details:    {info['width']}x{info['height']} "
      f"{info['format']} {info['bytes']} bytes")

# 4. Build an optimized delivery URL:
#      f_auto = pick the best format per browser (e.g. AVIF/WebP instead of JPEG)
#      q_auto = pick the best quality/compression automatically (smaller file)
optimized = cloudinary.CloudinaryImage(result["public_id"]).build_url(
    fetch_format="auto", quality="auto")
print("\nDone! Click link below to see the optimized version of the image.")
print("Check the size and the format:")
print(optimized)
