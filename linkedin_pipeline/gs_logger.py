"""
gs_logger.py -- Log a new AIMA article to Google Sheets.

POSTs the article GitHub Pages URL to the GAS webapp. GAS fetches the page,
extracts metadata from meta tags, and appends a row to the AIMA Google Sheet
(which powers aima.productions/insights.html).

Payload:  { "url": "https://joselitosering.github.io/aima/articles/[filename]" }
Response: { "success": true, "row": N, "message": "..." }

GAS redirect behaviour: POST to /exec -> 302 -> GET on googleusercontent.com.
urllib default redirect handling (POST->GET) matches Invoke-RestMethod behaviour
and is correct -- GAS processes doPost before issuing the redirect.
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

_SECRETS_PATH = Path(__file__).parent.parent / "articles" / "aima-coworker-secrets.json"


def _get_gs_url():
    try:
        with open(_SECRETS_PATH, encoding="utf-8") as f:
            return json.load(f).get("google_sheets_webapp_url", "")
    except Exception:
        return ""

GS_URL = _get_gs_url()


def log_to_google_sheets(filename, verbose=True):
    """
    POST the article GitHub Pages URL to the GAS endpoint.
    filename: e.g. 'aima-article-ethics-theater-014.html'
    Returns True on success, False on failure (non-fatal).
    """
    if not GS_URL:
        if verbose:
            print("  GS: No URL in aima-coworker-secrets.json -- skipping.")
        return False

    article_url = "https://joselitosering.github.io/aima/articles/" + filename
    payload = json.dumps({"url": article_url}).encode("utf-8")

    # Use default urllib opener -- it converts POST->GET on 302, matching
    # Invoke-RestMethod behaviour, which is what GAS expects.
    req = urllib.request.Request(GS_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent",   "AIMA-Pipeline/1.0")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                result = json.loads(body)
                if result.get("success"):
                    row = result.get("row", "?")
                    if verbose:
                        print("  GS: logged " + filename + " -> row " + str(row))
                    return True
                else:
                    if verbose:
                        print("  GS: non-success: " + str(result))
                    return False
            except Exception:
                if "success" in body.lower() or "ok" in body.lower():
                    if verbose:
                        print("  GS: logged " + filename)
                    return True
                if verbose:
                    print("  GS: unexpected response: " + body[:300])
                return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if verbose:
            print("  GS: HTTP " + str(e.code) + " -- " + body[:200])
        return False
    except Exception as e:
        if verbose:
            print("  GS: failed (non-fatal): " + str(e))
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python gs_logger.py <filename>")
        print("  e.g. python gs_logger.py aima-article-ethics-theater-014.html")
        sys.exit(1)
    ok = log_to_google_sheets(sys.argv[1], verbose=True)
    sys.exit(0 if ok else 1)
