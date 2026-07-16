#!/usr/bin/env python3
"""get_ig_token.py — finish setup for the "Instagram API with Instagram Login"
path (App dashboard: Instagram API > API setup with Instagram login). Turns the
dashboard-generated token into the two values the poster needs: IG_USER_ID +
a durable IG_ACCESS_TOKEN.

Reads from this module's own .env (instagram_pipeline/.env):
  IG_APP_SECRET       — Instagram app secret ("Show" button on the setup page)
  IG_GENERATED_TOKEN  — token from that page's "Generate token" button (starts IGAA...)
  GRAPH_API_VERSION   — optional, default v21.0
Writes IG_USER_ID + IG_ACCESS_TOKEN back into .env. The token is NEVER printed
(only a masked confirmation), so it stays out of any log.
"""
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ENV = HERE / ".env"
load_dotenv(ENV)
V = os.environ.get("GRAPH_API_VERSION", "v21.0")
HOST = "https://graph.instagram.com"

secret = os.environ.get("IG_APP_SECRET")
generated = os.environ.get("IG_GENERATED_TOKEN")
missing = [k for k, v in {"IG_APP_SECRET": secret,
                          "IG_GENERATED_TOKEN": generated}.items()
           if not v or str(v).startswith("REPLACE_")]
if missing:
    sys.exit("Fill these in instagram_pipeline/.env first: " + ", ".join(missing))

# 1. short-lived -> long-lived (60-day) Instagram user token.
#    If the token is already long-lived, Meta returns an error we tolerate and
#    fall back to using the generated token as-is.
token = generated
r = requests.get(f"{HOST}/access_token", params={
    "grant_type": "ig_exchange_token",
    "client_secret": secret,
    "access_token": generated}, timeout=30)
if r.ok and "access_token" in r.json():
    token = r.json()["access_token"]
    days = round(r.json().get("expires_in", 0) / 86400)
    print(f"[1/2] exchanged for long-lived token (~{days} days): OK")
else:
    print(f"[1/2] exchange skipped ({r.status_code}); using generated token as-is")

# 2. Resolve the Instagram user id used for publishing.
r = requests.get(f"{HOST}/{V}/me", params={
    "fields": "user_id,username", "access_token": token}, timeout=30)
if not r.ok:
    sys.exit(f"/me failed: {r.status_code} {r.text}")
me = r.json()
ig_id, ig_user = me["user_id"], me.get("username", "?")
print(f"[2/2] ig=@{ig_user}  IG_USER_ID={ig_id}")

# Write back to .env (replace or append) WITHOUT printing the token.
def upsert(text: str, key: str, val: str) -> str:
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    line = f"{key}={val}"
    return pat.sub(line, text) if pat.search(text) else text.rstrip() + "\n" + line + "\n"

txt = ENV.read_text(encoding="utf-8")
txt = upsert(txt, "IG_USER_ID", str(ig_id))
txt = upsert(txt, "IG_ACCESS_TOKEN", token)
ENV.write_text(txt, encoding="utf-8")
masked = token[:6] + "…" + token[-4:]
print(f"      wrote IG_USER_ID + IG_ACCESS_TOKEN to .env (token {masked}, not shown).")
print("Done. Re-run this any time you regenerate the token.")
