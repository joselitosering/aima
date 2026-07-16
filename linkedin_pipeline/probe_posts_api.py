"""
probe_posts_api.py — Test what /rest/posts?q=author returns for the AIMA org.
Run: python probe_posts_api.py
"""
import os, json, urllib.request, urllib.error, urllib.parse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN     = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
ORG_ID           = os.getenv("LINKEDIN_ORG_ID", "").strip()
LINKEDIN_VERSION = "202607"

org_urn = urllib.parse.quote(f"urn:li:organization:{ORG_ID}", safe="")
url = f"https://api.linkedin.com/rest/posts?q=author&author={org_urn}&count=5&sortBy=LAST_MODIFIED"

req = urllib.request.Request(url)
req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
req.add_header("LinkedIn-Version",          LINKEDIN_VERSION)
req.add_header("X-Restli-Protocol-Version", "2.0.0")

print(f"GET {url}\n")
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        print(json.dumps(data, indent=2)[:4000])
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:500]}")
except Exception as e:
    print(f"Error: {e}")
