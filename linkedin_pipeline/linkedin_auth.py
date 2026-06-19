"""
linkedin_auth.py - One-time LinkedIn OAuth flow.
Run: python linkedin_auth.py

Scopes requested:
  openid profile email    — OIDC identity (member name/ID)
  w_member_social         — post on member's behalf (kept as fallback)
  w_organization_social   — post on AIMA company page
  rw_organization_admin   — org analytics (organizationalEntityShareStatistics)
  r_member_postAnalytics  — personal post analytics (memberCreatorPostAnalytics)
"""

import os, json, re, webbrowser, urllib.parse, urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI  = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8080/callback")
SCOPES        = "openid profile email w_member_social w_organization_social rw_organization_admin"
AUTH_URL      = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL     = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL  = "https://api.linkedin.com/v2/userinfo"

auth_code = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b"<h2>Done! Close this tab and return to the terminal.</h2>")
        elif "error" in params:
            self.send_response(400); self.end_headers()
            self.wfile.write(f"<h2>Error: {params.get('error_description',['?'])[0]}</h2>".encode())
        else:
            self.send_response(204); self.end_headers()
    def log_message(self, *a): pass

def main():
    qs = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    })
    url = f"{AUTH_URL}?{qs}"
    print(f"\nOpening browser. If it does not open, paste this URL:\n{url}\n")
    webbrowser.open(url)
    print("Waiting for LinkedIn callback...")

    server = HTTPServer(("localhost", 8080), Handler)
    while auth_code is None:
        server.handle_request()

    print("Code received. Exchanging for tokens...")
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": auth_code,
        "redirect_uri": REDIRECT_URI, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as r:
        tok = json.loads(r.read())

    token = tok["access_token"]
    expires = tok.get("expires_in", 0)

    # Use OIDC userinfo endpoint (works with openid+profile scopes)
    print("Fetching member info...")
    req2 = urllib.request.Request(USERINFO_URL)
    req2.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req2) as r:
        userinfo = json.loads(r.read())

    member_id = userinfo.get("sub", "")
    name = userinfo.get("name", "")

    print(f"\nSUCCESS")
    print(f"  Name      : {name}")
    print(f"  Member ID : {member_id}")
    print(f"  Expires   : {expires//86400} days")
    print(f"  Scopes    : {tok.get('scope', SCOPES)}")

    with open("tokens.json", "w") as f:
        json.dump({**tok, "member_id": member_id, "userinfo": userinfo}, f, indent=2)

    env = open(".env").read()
    env = re.sub(r"LINKEDIN_ACCESS_TOKEN=.*",  f"LINKEDIN_ACCESS_TOKEN={token}", env)
    env = re.sub(r"LINKEDIN_REFRESH_TOKEN=.*", f"LINKEDIN_REFRESH_TOKEN={tok.get('refresh_token','')}", env)
    if "LINKEDIN_MEMBER_ID=" in env:
        env = re.sub(r"LINKEDIN_MEMBER_ID=.*", f"LINKEDIN_MEMBER_ID={member_id}", env)
    else:
        env += f"\nLINKEDIN_MEMBER_ID={member_id}\n"
    open(".env", "w").write(env)

    print("\n.env updated with new token.")
    print("NEXT STEP: run `python pipeline.py` — articles will now post to the AIMA company page.")

if __name__ == "__main__":
    main()
