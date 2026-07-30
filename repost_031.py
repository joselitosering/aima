"""Delete #031's LinkedIn posts (if still present) and repost fresh.

Context: Pipeline's own records (post_log.json / last-run-status.json) show
article #031 ("The Clause That Broke the Contract...") posted successfully
to the AIMA company page + personal reshare on 2026-07-28 19:39 UTC, with
real-looking share URNs returned by the LinkedIn API. Joe checked LinkedIn
directly and neither post is visible. Most likely explanation: the posts
were created (API returned success) and then removed afterward — LinkedIn
does this post-hoc for some automated/sensitive-topic content — rather than
never having been created at all. This script does not assume which case
it is: the delete calls below simply no-op (print an HTTP error, non-fatal)
if the old posts are already gone, then Nova posts #031 fresh regardless.

Run from the aima repo root:
    python repost_031.py

Needs a normal internet connection (LinkedIn's API is not reachable from
Claude's cloud/device-bridge sandboxes — confirmed blocked by the allowlist
proxy during diagnosis), so this must run from your own machine/terminal.
"""
import os, sys, json, urllib.request, urllib.error, urllib.parse
sys.path.insert(0, '.')

for envfile in ('agents/.env', 'linkedin_pipeline/.env'):
    for l in open(envfile):
        l = l.strip()
        if l and '=' in l and not l.startswith('#'):
            k, v = l.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

token = os.environ['LINKEDIN_ACCESS_TOKEN']
v2_headers = {
    'Authorization': f'Bearer {token}',
    'X-Restli-Protocol-Version': '2.0.0',
}

# -- 1. Delete the old #031 company post + personal reshare (non-fatal if gone) --
for label, share_urn in [
    ('reshare (personal)', 'urn:li:share:7487954822025924608'),
    ('company post', 'urn:li:share:7487954809149628416'),
]:
    num = share_urn.split(':')[-1]
    ugc_urn = f'urn:li:ugcPost:{num}'
    encoded = urllib.parse.quote(ugc_urn, safe='')
    req = urllib.request.Request(
        f'https://api.linkedin.com/v2/ugcPosts/{encoded}',
        method='DELETE', headers=v2_headers,
    )
    try:
        urllib.request.urlopen(req)
        print(f'Deleted {label}: {ugc_urn}')
    except urllib.error.HTTPError as e:
        print(f'Delete {label} HTTP {e.code} (ok if already gone): {e.read().decode()[:200]}')

# -- 2. Remove #031 from post_log.json so Nova/Echo don't double-count -----------
log_path = 'linkedin_pipeline/post_log.json'
posts = json.load(open(log_path))
posts = [p for p in posts if '031' not in p.get('article', '')]
json.dump(posts, open(log_path, 'w'), indent=2)
print('Removed #031 from post_log.json')

# -- 3. Remove from posted_articles.json if present (it currently isn't — the
#       file has been stale since #026, a separate Pipeline bug flagged
#       alongside this fix) ------------------------------------------------------
pa_path = 'linkedin_pipeline/posted_articles.json'
try:
    pa = json.load(open(pa_path))
    pa2 = [p for p in pa if '031' not in (p if isinstance(p, str) else p.get('filename', ''))]
    json.dump(pa2, open(pa_path, 'w'), indent=2)
    print('Removed #031 from posted_articles.json (no-op if it was never there)')
except Exception as e:
    print(f'posted_articles.json cleanup skipped: {e}')

# -- 4. Run Nova fresh -------------------------------------------------------------
print('Running Nova...')
from agents import nova

spec = {
    'number': 31,
    'slug': 'the-clause-that-broke-the',
    'filename': 'aima-article-the-clause-that-broke-the-031.html',
    'og_image': 'img/articles/aima-031-the-clause-that-broke-the.jpg',
}
live_url = 'https://joselitosering.github.io/aima/articles/aima-article-the-clause-that-broke-the-031.html'
result = nova.run(spec, live_url, dry_run=False)
print(f'Nova result: {result}')
print('Company post + personal reshare URNs above — open them to confirm they render before trusting this run either.')
