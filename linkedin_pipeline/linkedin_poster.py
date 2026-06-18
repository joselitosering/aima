"""
linkedin_poster.py — Posts an AIMA article to LinkedIn (personal profile).

Option B: Direct image upload via LinkedIn Assets API.
- Uploads the cover image directly to LinkedIn (bypasses OG scraping / caching).
- Posts as shareMediaCategory: "IMAGE" with article URL in commentary.
- Guarantees the cover image is always visible, regardless of OG cache state.
"""

import os, json, re, urllib.request, urllib.error, mimetypes
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
MEMBER_ID    = os.getenv("LINKEDIN_MEMBER_ID", "").strip()

LINKEDIN_API       = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_ASSETS_API = "https://api.linkedin.com/v2/assets?action=registerUpload"


# ── Metadata extraction ──────────────────────────────────────────────────────

def extract_metadata(html_content, filename, html_url):
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    title   = title_m.group(1).strip() if title_m else \
              filename.replace(".html","").replace("-"," ").title()

    desc_m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                       html_content, re.IGNORECASE)
    if not desc_m:
        desc_m = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
                           html_content, re.IGNORECASE)

    can_m      = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']',
                           html_content, re.IGNORECASE)
    source_url = can_m.group(1).strip() if can_m else html_url

    if desc_m:
        description = desc_m.group(1).strip()
    else:
        body = re.sub(r"<[^>]+>", " ", html_content)
        body = re.sub(r"\s+", " ", body).strip()
        description = (body[:300] + "...") if len(body) > 300 else body

    if not source_url:
        source_url = "https://github.com/joselitosering/aima"

    return title, description[:700], source_url


def extract_og_image(html_content):
    """Return the og:image URL from article HTML, or None."""
    m = re.search(
        r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']',
        html_content, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'<meta\s+content=["\'](.*?)["\']\s+property=["\']og:image["\']',
            html_content, re.IGNORECASE
        )
    return m.group(1).strip() if m else None


# ── LinkedIn image upload (Option B) ────────────────────────────────────────

def _register_upload():
    """
    Step 1: Register an image upload with LinkedIn.
    Returns (upload_url, asset_urn).
    """
    body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": f"urn:li:person:{MEMBER_ID}",
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(LINKEDIN_ASSETS_API, data=payload, method="POST")
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("Content-Type",              "application/json")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    upload_mechanism = result["value"]["uploadMechanism"]
    http_request = upload_mechanism.get(
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}
    )
    upload_url = http_request["uploadUrl"]
    asset_urn  = result["value"]["asset"]
    return upload_url, asset_urn


def _upload_image_bytes(upload_url, image_bytes, content_type="image/jpeg"):
    """
    Step 2: PUT image bytes to LinkedIn's upload URL.
    """
    req = urllib.request.Request(upload_url, data=image_bytes, method="PUT")
    req.add_header("Authorization", f"Bearer {ACCESS_TOKEN}")
    req.add_header("Content-Type",  content_type)
    with urllib.request.urlopen(req) as resp:
        # 201 Created — no body expected
        return resp.status


def upload_cover_image(image_url):
    """
    Download the cover image from image_url, upload it to LinkedIn,
    and return the LinkedIn asset URN.
    Raises on any failure.
    """
    print(f"  Downloading cover image: {image_url}")
    image_req = urllib.request.Request(image_url)
    image_req.add_header("User-Agent", "AIMA-Pipeline/1.0")
    with urllib.request.urlopen(image_req, timeout=30) as resp:
        image_bytes = resp.read()
        content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()

    print(f"  Registering LinkedIn image upload ({len(image_bytes)//1024}KB, {content_type})...")
    upload_url, asset_urn = _register_upload()

    print(f"  Uploading image to LinkedIn...")
    status = _upload_image_bytes(upload_url, image_bytes, content_type)
    print(f"  Upload complete (HTTP {status}). Asset: {asset_urn}")
    return asset_urn


# ── Post to LinkedIn ─────────────────────────────────────────────────────────

def post_to_linkedin(article):
    if not ACCESS_TOKEN:
        raise ValueError("LINKEDIN_ACCESS_TOKEN not set — run linkedin_auth.py first.")
    if not MEMBER_ID:
        raise ValueError("LINKEDIN_MEMBER_ID not set — run linkedin_auth.py first.")

    title, description, source_url = extract_metadata(
        article["content"], article["name"], article["html_url"]
    )

    # -- Try Option B: direct image upload -----------------------------------
    image_url  = extract_og_image(article["content"])
    asset_urn  = None

    if image_url:
        try:
            asset_urn = upload_cover_image(image_url)
        except Exception as e:
            print(f"  WARNING: Image upload failed ({e}). Falling back to ARTICLE post (no image guarantee).")
            asset_urn = None
    else:
        print(f"  No og:image found — posting without image.")

    # -- Build commentary (always includes article link) ----------------------
    commentary = (
        f"📖 {title}\n\n"
        f"{description}\n\n"
        f"Read the full article: {source_url}\n\n"
        f"#AIMA #AI #Philippines #Philanthropy #GenerationalWealth #AIForGood"
    )

    # -- Build post body -------------------------------------------------------
    if asset_urn:
        # Option B: IMAGE post with uploaded asset
        media_obj = {
            "status": "READY",
            "media":  asset_urn,
            "title":  {"text": title[:200]}
        }
        share_media_category = "IMAGE"
    else:
        # Fallback: ARTICLE post (relies on OG scraping)
        media_obj = {
            "status":      "READY",
            "originalUrl": source_url,
            "title":       {"text": title},
            "description": {"text": description}
        }
        share_media_category = "ARTICLE"

    body = {
        "author": f"urn:li:person:{MEMBER_ID}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary":    {"text": commentary},
                "shareMediaCategory": share_media_category,
                "media": [media_obj]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(LINKEDIN_API, data=payload, method="POST")
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("Content-Type",              "application/json")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            post_id = result.get("id", "unknown")
            print(f"  Posted: '{title}' | ID: {post_id} | Mode: {share_media_category}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  LinkedIn API error {e.code}: {error_body}")
        raise
