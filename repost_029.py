"""Delete old #029 LinkedIn posts and repost with the new image."""
import os, sys, json, urllib.request, urllib.error
sys.path.insert(0, '.')
for l in open('agents/.env'):
    l = l.strip()
    if l and '=' in l and not l.startswith('#'):
        k, v = l.split('=', 1); os.environ[k.strip()] = v.strip()
for l in open('linkedin_pipeline/.env'):
    l = l.strip()
    if l and '=' in l and not l.startswith('#'):
        k, v = l.split('=', 1); os.environ.setdefault(k.strip(), v.strip())

token = os.environ['LINKEDIN_ACCESS_TOKEN']
v2_headers = {
    'Authorization': f'Bearer {token}',
    'X-Restli-Protocol-Version': '2.0.0',
}

# -- 1. Delete reshare then company post via v2 ugcPosts API -------------
# share URN numeric suffix maps directly to ugcPost URN
for label, share_urn in [
    ('reshare', 'urn:li:share:7486145746811920384'),
    ('company post', 'urn:li:share:7486145733163675648'),
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
        print(f'Delete {label} HTTP {e.code}: {e.read().decode()[:200]}')

import urllib.parse

# -- 2. Remove #029 from post_log.json so Nova treats it as unposted -----
log_path = 'linkedin_pipeline/post_log.json'
posts = json.load(open(log_path))
posts = [p for p in posts if '029' not in p.get('article', '')]
json.dump(posts, open(log_path, 'w'), indent=2)
print('Removed #029 from post_log.json')

# -- 3. Remove from posted_articles.json if present ----------------------
pa_path = 'linkedin_pipeline/posted_articles.json'
try:
    pa = json.load(open(pa_path))
    pa2 = [p for p in pa if '029' not in p.get('filename', '')]
    json.dump(pa2, open(pa_path, 'w'), indent=2)
    print('Removed #029 from posted_articles.json')
except Exception:
    pass

# -- 4. Run Nova repost --------------------------------------------------
print('Running Nova...')
from agents import nova
from agents.config import load_pipeline_config

spec = {
    'number': 29,
    'slug': 'the-lab-that-runs-itself',
    'title': "The Lab That Runs Itself: How Autonomous Labs Are Compressing Materials Discovery From Years to Days",
    'filename': 'aima-article-the-lab-that-runs-itself-029.html',
    'og_image': 'img/articles/aima-029-the-lab-that-runs-itself.jpg',
    'author': 'Kenji Nakamoto',
    'persona': 'kenji',
    'category': 'AI Science',
}
live_url = 'https://joselitosering.github.io/aima/articles/aima-article-the-lab-that-runs-itself-029.html'
result = nova.run(spec, live_url, dry_run=False)
print(f'Nova result: {result}')
