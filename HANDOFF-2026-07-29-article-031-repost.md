# Handoff — Article #031 LinkedIn Repost + Marketing-Batch Diagnosis (2026-07-29)

## What happened

Joe ran the marketing batch on Pipeline (his machine) for article #031 ("The
Clause That Broke the Contract: What Anthropic's Refusal to Arm the Pentagon
Reveals About Who Really Governs AI"). It returned a positive
confirmation, but checking LinkedIn directly showed no post on either the
AIMA company page or his personal profile.

## Diagnosis (from `aima` repo state, no live LinkedIn access from this
session — see Constraint below)

1. **Pipeline's own records say #031 already posted successfully once, the
   day before** (2026-07-28T19:39 UTC / 12:39pm PT), via the *original*
   full-pipeline publish run (Porter → Nova), not the marketing batch Joe
   ran today:
   - `last-run-status.json`: `"outcome": "published", "success": true`,
     `company_urn: urn:li:share:7487954809149628416`,
     `reshare_urn: urn:li:share:7487954822025924608`.
   - `linkedin_pipeline/post_log.json` has a matching entry, persona
     `dawn`, same two URNs.
   - `linkedin_poster.py`'s `post_to_linkedin()` only returns a URN after a
     real 2xx response from LinkedIn's API and raises on `HTTPError`
     otherwise — so this wasn't a silent/simulated success in the code path
     itself.
2. **Today's marketing batch ran second, found nothing to do, for a
   separate reason than "already posted":** `run_marketing_batch.py`'s
   `find_unmarketed()` computes `posted_articles.json ∩ not-in-post_log`.
   `posted_articles.json` hasn't been updated since **#026** (~6 days stale
   as of the #031 run) — it's missing #027, #028, #029, #030, #031 entirely.
   So #031 was never eligible to be picked up by that script regardless of
   whether it needed (re)posting. This is a real bug (dead/stale tracking
   file), but a separate one from why the LinkedIn post itself isn't
   visible.
3. **Most likely explanation for "posted successfully per our records, but
   not visible on LinkedIn":** the post was created (API returned success)
   and then removed afterward — LinkedIn does this post-hoc for some
   automated-posting / sensitive-topic content — rather than never having
   been created. Not confirmed with certainty; see Constraint below.

## Constraint hit this session

Could not verify directly or execute the fix from Claude's cloud/Cowork
session:
- `curl` to `api.linkedin.com` from the device-bridge VM returns
  `403 from proxy after CONNECT` — same allowlist block already documented
  for Pexels/Higgsfield CDN in [[maya-image-dedup-and-persona-repetition-fix]].
- `WebFetch` on both post permalinks
  (`linkedin.com/feed/update/urn:li:share:...`) returns
  `ROBOTS_DISALLOWED` — LinkedIn blocks it.
- Claude-in-Chrome browser extension is not connected this session.
- `computer_*` desktop-control tools can only grant browsers **read**
  access (screenshot-only, no click/type) — confirmed via
  `computer_resolve_access` on Microsoft Edge.

So this had to be handed off as a ready-to-run script again, same pattern
as the #029 image fix and #031's own `fix_031_image.py`.

## Fix delivered

`repost_031.py` (repo root, mirrors the already-proven `repost_029.py`
pattern):
1. Deletes the two existing #031 URNs via the `v2/ugcPosts` DELETE API
   (non-fatal if they're already gone — that's expected if LinkedIn already
   pulled them).
2. Strips #031 out of `post_log.json` (and `posted_articles.json`, harmless
   no-op since it was never there).
3. Runs `nova.run()` fresh — posts to the AIMA company page + Joselito's
   personal reshare, using the **already-fixed, non-duplicate** cover image
   (`img/articles/aima-031-the-clause-that-broke-the.jpg` — confirmed this
   file's local mtime is *after* `fix_031_image.py`'s own mtime, i.e. that
   fix already ran and pushed before this).

**Run it:** open a terminal in the aima repo root, `python repost_031.py`.
Nova's own pre-check will fail loudly (not silently) if the fixed image
somehow isn't live yet on GitHub Pages.

## Still open / recommended next steps

- **`posted_articles.json` staleness (#027-#031 missing)** — low severity in
  practice since `post_log.json` is the file that actually gates
  `find_unmarketed()`'s dedup, but it's dead/misleading state that should
  either be kept in sync or retired. Small, mechanical fix.
- **No post-hoc verification anywhere in the pipeline.** Nova/`post_to_linkedin`
  is fire-and-forget: it trusts the 2xx response and never re-checks that the
  post is still up minutes/hours later. This is the actual capability gap
  that let "Pipeline says success" and "nothing on LinkedIn" both be true
  with no alarm raised. Given this is precise, multi-file, testable
  engineering (add a delayed re-check call, decide what to do on a
  disappeared post — flag vs. auto-repost), **recommend porting to Claude
  Code/Opus** rather than doing it here, per project convention (same as
  the Echo analytics scope/CSV-split handoff).
- Confirm after running `repost_031.py` that both new permalinks actually
  render content when opened logged out/incognito, not just that the API
  returned 2xx — that's the only way to be sure this repost doesn't
  silently repeat the same failure mode.

See also: [[pipeline-scheduled-run-silent-failure]] (general "Pipeline said
yes, nothing happened" triage order), [[maya-image-dedup-and-persona-repetition-fix]]
(the #031 image bug this repost inherits the *fix* for, and the sandbox
network-allowlist precedent).
