# Instagram Poster (posts / carousels / reels)

Watches three drop folders and posts new items to Instagram automatically, with
an AI-generated caption + hashtags. Plain Python + Windows Task Scheduler,
self-contained module matching the `linkedin_pipeline/` pattern (its own `.env`,
no shared repo-root config).

```
inbox/
  posts/<name>.jpg          → one single-image post (just drop the file in)
  carousels/<set-name>/     → one carousel, 2-10 images (drop a folder in)
  reels/<name>.mp4          → one Reel / video (just drop the file in)
```

**No manual grouping for posts or reels** — each file dropped in is one post.
**Carousels stay folders on purpose** — which photos belong together is a real
curation choice, not something the pipeline should guess at.

Per item:

```
detect new file/folder → normalize images (PNG→JPEG, IG-legal aspect, ≤1440px)
  → upload to Cloudinary (public https URL — required by the Graph API)
  → caption + hashtags via OpenRouter (or use a caption override, see below)
  → create the right container (single image / carousel / Reels video)
  → publish immediately (IG_AUTO_PUBLISH=true, the configured default)
             + archive the source file(s)
  → (set IG_AUTO_PUBLISH=false instead to get a PENDING/--approve review gate)
```

**Posting mode: fully unattended.** Runs publish immediately; review happens on
Instagram itself after the fact, not before. Flip `IG_AUTO_PUBLISH=false` in `.env`
to switch back to the review-gate (`--list-pending` / `--approve` / `--reject`).

**Schedule: every 6 hours** (~4 runs/day). Change the interval in
`register-task.ps1` if you want it more or less frequent.

## Why the moving parts exist (not optional)

- **Cloudinary:** the Instagram Graph API fetches media from **public https
  URLs** only, and images must be **JPEG**. A localhost path or a Google Drive
  share link will not work. Midjourney exports PNG, so conversion + hosting are
  both mandatory for posts/carousels.
- **Meta app + Instagram professional account:** publishing requires the
  `instagram_business_content_publish` permission. For your *own* account this
  works in Development mode with no App Review — App Review is only required to
  publish to *other people's* accounts.
- **Reels take longer to process** than images — the code waits up to 5 minutes
  for Meta to finish processing an uploaded video before publishing.

## Auth path: Instagram API with Instagram Login

Uses the app's **Instagram API → API setup with Instagram login** page — no
Facebook Page needed, no App Review for your own account.

1. **Instagram → Business/Creator account** (IG app → Settings → Account type).
2. Meta app → **Instagram API** product → **Permissions and features**: enable
   `instagram_business_basic` + `instagram_business_content_publish`.
3. **API setup with Instagram login** page → add your IG account as an
   **Instagram Tester** (Roles tab) and accept the tester invite from the
   Instagram app itself → back on the setup page, click **Generate token**.
4. Copy the **Instagram app secret** (Show button, same page) and the generated
   token into `instagram_pipeline/.env` as `IG_APP_SECRET` / `IG_GENERATED_TOKEN`.
5. Run `python get_ig_token.py` — resolves `IG_USER_ID` and writes
   `IG_ACCESS_TOKEN` to `.env`.
6. **Cloudinary** account → Dashboard → copy cloud name + API key + API secret.

**Known unresolved issue — token lifetime.** The dashboard "Generate token" value
does **not** exchange via `ig_exchange_token` (`get_ig_token.py` logs "exchange
skipped" and falls back to using it as-is) — Meta returns error 452/"session key
invalid" for this token type, and it isn't documented whether dashboard tokens
are already long-lived or genuinely short-lived. Unverified until observed: if
scheduled runs start failing at the Graph call, the fix is to regenerate the
token from that same dashboard page and re-run `get_ig_token.py`.

## `instagram_pipeline/.env` keys (self-contained — not shared with the repo root)

| Key | Required | Default | Notes |
|---|---|---|---|
| `IG_APP_SECRET` | ✅ | — | Instagram app secret (for `get_ig_token.py`) |
| `IG_GENERATED_TOKEN` | ✅ | — | dashboard "Generate token" value (for `get_ig_token.py`) |
| `IG_USER_ID` | auto | — | written by `get_ig_token.py` |
| `IG_ACCESS_TOKEN` | auto | — | written by `get_ig_token.py` |
| `GRAPH_API_VERSION` | | `v21.0` | |
| `CLOUDINARY_CLOUD_NAME` | ✅ | — | |
| `CLOUDINARY_API_KEY` | ✅ | — | |
| `CLOUDINARY_API_SECRET` | ✅ | — | |
| `OPENROUTER_API_KEY` | ✅ | — | own copy for caption generation (not shared with insights) |
| `OPENROUTER_MODEL_DEFAULT` | | `openrouter/auto` | |
| `IG_AUTO_PUBLISH` | | `true` (configured) | `false` = switch to the PENDING/`--approve` review gate |
| `IG_INBOX_DIR` | | `instagram_pipeline/inbox` | root containing `posts/`, `carousels/`, `reels/` |
| `IG_POSTS_DIR` / `IG_CAROUSELS_DIR` / `IG_REELS_DIR` | | `inbox/posts` etc. | override any one individually |
| `IG_FIT` | | `pad` | `pad` (letterbox, never crops art) or `crop` (center-crop) |
| `IG_AUDIENCE` | | generic | your niche/audience, steers the caption |
| `IG_BRAND_HASHTAG` | | `aimaproductions` | always the 5th hashtag, guaranteed present regardless of model output |
| `IG_BIO_LINK` | | `http://aima.productions` | shown in the `!! BIO LINK` reminder — not written into captions (see below) |

## Folder convention

- **`inbox/posts/<name>.jpg`** — one file = one single-image post.
- **`inbox/carousels/<set-name>/`** — one subfolder = one carousel (2–10 images,
  ordered alphabetically). Drop `paris-trip/`, `set-01/`, etc.
- **`inbox/reels/<name>.mp4`** — one file = one Reel. (`.mov` / `.m4v` also
  accepted; no aspect/duration processing is done — Instagram's own Reels specs
  apply, e.g. vertical 9:16 is recommended.)
- Optional caption control, same-stem sibling files for `posts/`/`reels/`, or
  inside the subfolder for `carousels/`:
  - `<name>.brief.txt` (or `carousels/<set>/brief.txt`) — steers the AI caption.
  - `<name>.caption.txt` (or `carousels/<set>/caption.txt`) — used **verbatim**,
    skips AI generation.
  - `<name>.affiliate.txt` (or `carousels/<set>/affiliate.txt`) — names the
    product being promoted in this post. When present, the caption naturally
    references it and ends with "link in bio" (captions aren't clickable —
    only the bio link is), and the run prints/logs a `!! BIO LINK` reminder to
    manually point your bio at that offer while the post is live. No ad
    disclosure is added automatically — that's on you.
- On publish, the source (file or folder, plus any sibling brief/caption/
  affiliate files) moves to `instagram_pipeline/archive/<kind>/` — flat, e.g.
  `archive/posts/<name>.png`, `archive/carousels/<set-name>/` — automatically
  (auto-publish mode). In review-gate mode, pending items stay put until
  approved or rejected. **Deliberately flat, not `archive/<kind>/<name>/<name>`**
  — nesting under a same-named subfolder duplicated long Midjourney filenames
  in the path and exceeded Windows' 260-char `MAX_PATH` (a real crash hit on
  the first live post — see the caveat below).

## Caption structure

Every AI-generated caption follows a fixed skeleton (theme varies per `brief.txt`,
structure doesn't): a keyword-led hook tied to what's actually in the frame, one
sentence naming the real human decision behind the AI-generated piece (2026
platform trend rewards a visible human layer over AI-perfect visuals), a casual
comment/save/share prompt, and exactly **5 hashtags** (broad/niche/niche/
community/branded — the branded tag is guaranteed by code, not left to the
model). Alt text is generated too and sent via the Graph API's `alt_text` field
for accessibility/search. `caption.txt` overrides skip all of this and are used
verbatim.

## Usage

```powershell
pip install -r requirements.txt

# Cheap dry test — captions only, no Cloudinary/IG, no cost beyond a few tiny OpenRouter calls:
python instagram_carousel.py --dry-run

# Real run — scans all three folders and, with IG_AUTO_PUBLISH=true, uploads,
# captions, creates the container, publishes, and archives every new item:
python instagram_carousel.py

# If IG_AUTO_PUBLISH=false instead:
python instagram_carousel.py --list-pending
python instagram_carousel.py --approve posts/sunset
python instagram_carousel.py --approve carousels/paris-trip
python instagram_carousel.py --approve reels/clip1
python instagram_carousel.py --approve-all
python instagram_carousel.py --reject posts/sunset      # discard instead

# Schedule every 6 hours (elevated, once):
powershell -NoProfile -ExecutionPolicy Bypass -File register-task.ps1
```

## Notes / limits

- Instagram publishing limit: **50 posts / 24h** per account (posts, carousels,
  and Reels all count against the same limit).
- Carousel: **2–10** images per set. A subfolder with 0–1 images is skipped
  (logged, not an error) until you add more.
- Logs: `runner-log.jsonl` (the PS runner) + `carousel_log.jsonl`
  (prepared/published/rejected/error events, all tagged with `kind`). In
  auto-publish mode, check these (or Instagram itself) after each run since
  nothing waits for your review first.
- Token upkeep: see the unresolved lifetime issue above — watch for Graph-call
  failures in the log as the practical signal to regenerate.
- **Verified live** (2026-07-15): a single-image post ran the full real path —
  Cloudinary upload, Graph API container + publish — successfully against
  `@aimaproductions`. The archive step crashed right after (Windows path-length
  bug, since fixed — see Folder convention above); the publish itself was
  unaffected. If a run ever exits with a leftover `state/<kind>__<name>.json`
  after a `PUBLISHED` log line, the post already went out — don't re-run it,
  just clean up the stale state file and finish the archive move by hand.
