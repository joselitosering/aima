"""
gs_logger.py — Log a new AIMA article to Google Sheets.

POSTs the article's GitHub Pages URL to the GAS webapp, which fetches the page,
extracts metadata (title, author, date, category, etc.) from meta tags, and
appends a row to the AIMA Google Sheet (which powers aima.productions/insights.html).

Payload:  { "url": "https://joselitosering.github.io/aima/articles/[filename]" }
Response: { "success": true }
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

# Load GS URL from secrets file (same dir as articles/)
_SECRETS_PATH = Path(__file__).parent.parent / "articles" / "aima-coworker-secrets.json"

def _get_gs_url():
    try:
        with open(_SECRETS_PATH, encoding="utf-8") as f:
            return json.load(f).get("google_sheets_webapp_url", "")
    except Exception:
        return ""

GS_URL = _get_gs_url()


class _RedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow POST redirects (GAS returns 302 on POST)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # On redirect, switch to GET — this is what browsers do for GAS
        new_req = urllib.request.Request(newurl, method="GET")
        new_req.add_header("User-Agent", "AIMA-Pipeline/1.0")
        return new_req


def log_to_google_sheets(filename, verbose=True):
    """
    POST the article's GitHub Pages URL to the GAS endpoint.
    filename: e.g. 'aima-article-ethics-theater-014.html'
    Returns True on success, False on failure (non-fatal).
    """
    if not GS_URL:
        if verbose:
            print("  GS: No URL in aima-coworker-secrets.json — skipping.")
        return False

    article_url = f"https://joselitosering.github.io/aima/articles/{filename}"
    payload = json.dumps({"url": article_url}).encode("utf-8")

    opener = urllib.request.build_opener(_RedirectHandler)
    req = urllib.request.Request(GS_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent",   "AIMA-Pipeline/1.0")

    try:
        with opener.open(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            try:
                result = json.loads(body)
                if result.get("success"):
                    if verbose:
                        print(f"  GS: logged '{filename}' → success")
                    return True
                else:
                    if verbose:
                        print(f"  GS: non-success response: {result}")
                    return False
            except json.JSONDecodeError:
                # Some GAS deployments return plain text
                if "success" in body.lower() or "ok" in body.lower():
                    if verbose:
                        print(f"  GS: logged '{filename}' (plain response: {body[:80]})")
                    return True
                if verbose:
                    print(f"  GS: unexpected response: {body[:200]}")
                return False
    except urllib.error.HTTPError as e:
        if verbose:
            print(f"  GS: HTTP {e.code} — {e.read().decode()[:200]}")
        return False
    except Exception as e:
        if verbose:
            print(f"  GS: failed (non-fatal): {e}")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python gs_logger.py <filename>")
        print("  e.g. python gs_logger.py aima-article-ethics-theater-014.html")
        sys.exit(1)
    ok = log_to_google_sheets(sys.argv[1], verbose=True)
    sys.exit(0 if ok else 1)
