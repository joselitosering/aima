# HANDOFF — Echo LinkedIn Analytics: CSV split + dead XLS fallback (2026-07-28)

**Scope:** two code bugs in Echo's analytics path, fixed and verified. The underlying reason
analytics can't be collected at all — a missing LinkedIn OAuth scope — **is not a code problem
and remains open**, pending Joe's external LinkedIn Business Development conversation.

**Files touched:** `agents/echo.py`, `run_analytics_batch.py`, `CLAUDE.md`,
`agent-manager.html`, `AGENT_SPEC.md`, `AIMA-SESSION-REPORT.md`, this file.
**Deliberately NOT touched:** `linkedin_pipeline/linkedin_auth.py` (`SCOPES` byte-identical —
`git diff` empty), `run_lumen_batch.py` (already read the canonical file, no change needed),
`pipeline_config.json`, and every other agent's core logic.

---

## 1. The blocker (NOT fixed here — cannot be fixed in code)

`agents/echo.py` fetches post stats from `/rest/memberCreatorPostAnalytics`, which requires the
OAuth scope **`r_member_postAnalytics`**. This app does not have it.

**Verified live 2026-07-28**, two independent ways:

- Calling the endpoint with the current token returns **HTTP 403**.
- LinkedIn's token introspection endpoint reports the token as `active` (expires
  **2026-09-21**) with granted scopes: `openid`, `profile`, `email`, `w_member_social`,
  `w_organization_social`, `r_organization_social`, `rw_organization_admin`,
  `r_organization_admin`. No `r_member_postAnalytics`, no `r_member_social`.

`r_member_postAnalytics` was removed from `SCOPES` in `be88f65` (2026-07-23) for a real reason:
**requesting a scope LinkedIn hasn't approved makes it reject the entire OAuth authorization
request**, so on 2026-07-23 it broke *posting* too. Removing it fixed posting at the cost of
analytics.

> **Do not re-add `r_member_postAnalytics` (or `r_member_social`) to `SCOPES` until LinkedIn
> approval is actually confirmed.** Re-adding it will immediately re-break posting the same way.

Getting the scope is **not a Developer Portal checkbox.** It sits under the **Community
Management API**, which requires a formal **Technical Sign-Off**: contacting a LinkedIn
Business Development point of contact and completing a live product demo covering ~28
requirements. **That is Joe's external action; no code change can close it.**

**Until then the only working path is manual:** export the LinkedIn Analytics XLS, then
`python linkedin_pipeline/xls_import.py <path-to-export.xlsx>`.

### Correction to `CLAUDE.md`'s old "Pending Actions"
It claimed `r_member_social` was "APPROVED June 20, 2026" and "added to SCOPES". **Both halves
were false.** `SCOPES` has never contained `r_member_social` (not in the file; `git log -p`
shows it never was), and introspection confirms it isn't granted. LinkedIn's docs currently
list `r_member_social` as **closed** ("not accepting access requests at this time"). The note
also referenced `/rest/socialMediaPostStatistics`, an endpoint that **does not exist** on
LinkedIn's API — every call 404'd, which is why `echo.py` already moved off it. That section
has been rewritten with the verified state.

---

## 2. CSV split — FIXED

`agents/echo.py` wrote `REPO_ROOT/linkedin_analytics.csv`. That file **has never existed**,
because Echo has never had a successful API call. Everything else uses
`linkedin_pipeline/post_analytics.csv`:

| Component | Role | File |
|---|---|---|
| `run_lumen_batch._linkedin_report()` | reader | `post_analytics.csv` |
| `marco._category_priority()` | reader (keys off `article` col) | `post_analytics.csv` |
| `article-manager.html` dashboard | reader (uses `persona`, `engagement_rate`, `collected_at`) | `post_analytics.csv` |
| `xls_import.py` | writer (manual fallback) | `post_analytics.csv` |
| `analytics_collector.py` | writer (legacy, no longer called) | `post_analytics.csv` |
| `agents/echo.py` | writer | ~~`linkedin_analytics.csv`~~ → **now `post_analytics.csv`** |

**`linkedin_pipeline/post_analytics.csv` is now canonical.** It already holds 11 real data
rows, so it was also the correct choice on data-integrity grounds — it's what backfills the
dashboard.

### The non-obvious part: the schemas differed
A bare path swap would have **corrupted the file**. Echo emitted 9 columns
(`date, slug, urn, impressions, clicks, reactions, reposts, comments, ctr`); the canonical file
has 13 (`post_id, article, title, persona, posted_at, collected_at, impressions, clicks, likes,
comments, shares, engagement_rate, ctr`). Appending Echo's old rows would have produced ragged
rows the dashboard and `marco._category_priority()` would misread.

Echo now maps onto the canonical schema via a new `_build_csv_row()`:
`REACTION`→`likes`, `RESHARE`→`shares`, `post_id`←URN, `article`/`title`/`persona`/`posted_at`
carried from the `post_log.json` entry, and `engagement_rate` derived as
`(likes + comments + shares) / impressions` (a 0–1 decimal, matching how `xls_import.py`
stores it — the API does not return this field). `CSV_HEADERS` in `echo.py` is asserted
identical to `xls_import.py`'s. API-collected and XLS-imported rows are now interchangeable.

---

## 3. Dead `xls_import.py` auto-call — FIXED

On API failure Echo ran:

```python
subprocess.run(["python", "linkedin_pipeline/xls_import.py"], cwd=REPO_ROOT, check=False)
```

`xls_import.main()` requires a positional `xls_file`. **Reproduced:** exit code 2,
`error: the following arguments are required: xls_file`. Because `check=False`, Echo swallowed
it — so Echo *looked* like it had a fallback while doing nothing, and spawned one wasted
subprocess per uncollected post on every run.

The LinkedIn analytics export is a human-in-the-loop action with no pull API (that's the
missing scope), so **nothing can be auto-invoked here.** The call is removed. Echo now logs one
clear line per run:

```
[echo] 28 post(s) awaiting analytics — LinkedIn API blocked (missing 'r_member_postAnalytics'
scope, pending LinkedIn Community Management approval). To import them manually: export
LinkedIn Analytics XLS and run: python linkedin_pipeline/xls_import.py <path-to-export.xlsx>
```

When posts are uncollected for reasons other than the scope gate, the middle clause reads
`not collected via API` instead. Per the task, no `--watch`/folder-drop mode was built.

---

## 4. Scope-gate short-circuit (new, small)

A 401/403 is a **token-wide** condition, not a per-post one. Echo previously would have fired 5
API calls (one per metric) × 26 eligible posts = **130 doomed requests** per run. It now halts
the loop on the first 401/403 and reports once. Other HTTP errors still skip just that post.

Related: `write_json(post_log)` and the git add/commit/push block now run **only if something
was actually collected** — previously a fully-failed run rewrote `post_log.json` identically and
then logged a spurious "nothing to commit" `CalledProcessError` warning. The git add now
includes `post_analytics.csv` alongside `post_log.json`, so Echo's output reaches the dashboard
the same way `xls_import.py`'s does.

Echo's report to Lumen gained `posts_awaiting_analytics`, `source`, and a populated `flags[]`
entry when the scope gate trips; `run_analytics_batch.py` logs the backlog count and surfaces
flags as warnings.

---

## 5. Verification performed

- **Schema agreement:** `echo.CSV_HEADERS == xls_import.CSV_HEADERS ==` the live
  `post_analytics.csv` header row. Asserted.
- **Round-trip:** appended a row to a copy of the real CSV, re-read it through Lumen's exact
  expression (`[int(r.get("impressions", 0) or 0) for r in rows]`) and confirmed 12 well-formed
  rows, correct `persona`/`engagement_rate`, and a computable `avg_impressions`.
- **Live API:** ran Echo against the real LinkedIn API with git/write side effects intercepted.
  Result: genuine **HTTP 403**, halt after **exactly 1** fetch attempt, correct operator
  message, `posts_collected: 0`, `posts_awaiting_analytics: 28`, scope flag set.
- **Dead call:** ran `python linkedin_pipeline/xls_import.py` bare → exit 2, confirming the
  removed call was a no-op.
- **`SCOPES` untouched:** `git diff linkedin_pipeline/linkedin_auth.py` is empty; posting scopes
  `w_member_social` + `w_organization_social` present and granted on an active token.

## 6. Backlog

**28 of 35 posts** in `post_log.json` have `analytics_collected: false` (26 are past the 48h
eligibility window). This is **unchanged** by these fixes and cannot drop until either the
LinkedIn scope is granted or someone runs the manual XLS import. Confirmed not made worse — no
run in this session wrote to `post_log.json`.

## 7. Open — needs Joe

**Pursue the LinkedIn Community Management API Technical Sign-Off for
`r_member_postAnalytics`.** Only after approval is confirmed: re-add the scope to `SCOPES`,
re-run `python linkedin_pipeline/linkedin_auth.py`, then `python run_analytics_batch.py`.
Until then, use the XLS import to keep the dashboard fed.
