# Claude Code Task: Fix LinkedIn Analytics Collection (Echo) — Scope Gap + CSV Split

**Prepared:** 2026-07-28 · **Requested by:** Joe (via Cowork review) · **Why Claude Code, not
Cowork:** multi-file Python engineering across `agents/echo.py`, `run_analytics_batch.py`,
`run_lumen_batch.py`, and `linkedin_pipeline/xls_import.py`, plus verifying behavior by actually
running scripts against the real repo state — Cowork's review pass (this doc) only read code and
`git log`, it didn't execute anything. Do this on Joe's machine, in the `aima` repo.

## Context (verified via `git log -p` + direct code reads, 2026-07-28)

**Problem 1 — analytics can't collect at all right now, and it's a LinkedIn platform gate, not
a bug you can code around.** `agents/echo.py` (the only path `run_analytics_batch.py` actually
calls) fetches post stats via `/rest/memberCreatorPostAnalytics`, which requires OAuth scope
`r_member_postAnalytics`. That scope was removed from `linkedin_pipeline/linkedin_auth.py`'s
`SCOPES` string in commit `be88f65` (2026-07-23, message "y") with this comment left in the code:

> `r_member_postAnalytics` removed 2026-07-23: not authorized for this app (Echo analytics,
> pending LinkedIn approval). It blocked the whole OAuth flow; posting only needs the
> `w_*_social` scopes.

Requesting a scope LinkedIn hasn't approved for this app doesn't just drop that one scope — it
rejects the entire OAuth authorization request, so on 2026-07-23 it broke posting too. Removing
it fixed posting, at the cost of analytics. **Do not re-add `r_member_postAnalytics` to `SCOPES`
until LinkedIn approval is actually confirmed** — re-adding it will immediately re-break posting
the same way.

Per LinkedIn's own docs (Microsoft Learn), `r_member_postAnalytics` / the Post Statistics endpoint
sits under the **Community Management API**, and getting it requires a formal **Technical
Sign-Off**: contacting a LinkedIn Business Development point of contact and completing a live
product demo covering ~28 requirements — not a self-serve Developer Portal checkbox. That's on
Joe to pursue externally; it is not something this task can complete. Separately worth flagging:
`CLAUDE.md`'s "Pending Actions" section still claims `r_member_social` was "APPROVED June 20,
2026" and "added to SCOPES" — but the live `SCOPES` string has never actually contained
`r_member_social`, and LinkedIn's docs currently list `r_member_social` as a **closed** permission
("not accepting access requests at this time"). That pending-action note looks stale/never-
completed — verify for real (don't just trust `CLAUDE.md`) and correct it as part of this task.

**Consequence:** `post_log.json` currently has `analytics_collected: false` on 29 of 35 posts,
back to article #003 (2026-03-23), and grows by one every time Nova posts a new article, because
Echo can never succeed without the scope.

**Problem 2 — separate, code-fixable bug: the pipeline doesn't agree with itself on a filename.**
- `agents/echo.py` writes to `REPO_ROOT/linkedin_analytics.csv` (repo root). This file doesn't
  exist yet — Echo has never successfully written to it.
- `linkedin_pipeline/analytics_collector.py` (legacy — no longer called by
  `run_analytics_batch.py`, which calls `agents/echo.py` instead) and
  `linkedin_pipeline/xls_import.py` (the manual XLS-export fallback) both write to
  `linkedin_pipeline/post_analytics.csv`.
- `run_lumen_batch.py`'s `_linkedin_report()` reads **only** `linkedin_pipeline/post_analytics.csv`.
- So even in a world where Echo's API call succeeded, its output would land in a file Lumen (and
  probably the dashboard — check `article-manager.html`/`insights` dashboard fetch calls too)
  never reads. This split predates the scope removal and is independent of Problem 1 — fix it
  regardless of how the scope situation resolves.

**Problem 3 — Echo's "fallback" to `xls_import.py` is dead code.** On API failure, `agents/echo.py`
runs:
```python
subprocess.run(["python", "linkedin_pipeline/xls_import.py"], cwd=REPO_ROOT, check=False)
```
`xls_import.py`'s `main()` requires a positional `xls_file` argument (`argparse`, no default).
Called with zero arguments, it will immediately error out (`the following arguments are required:
xls_file`, exit code 2) and do nothing. Because `check=False`, `echo.py` swallows this silently —
so right now Echo *appears* to have a fallback path in the code, but it's a no-op that also spawns
a wasted subprocess once per uncollected post on every run. Verify this behavior actually happens
(run it) before fixing.

## What to do (priority order)

1. **Fix the CSV split (Problem 2) first** — it's real, independent of the LinkedIn scope
   question, and blocks the manual fallback too. Recommend one canonical file: keep
   `linkedin_pipeline/post_analytics.csv` since that's what Lumen (and probably the dashboard)
   already reads, and make `agents/echo.py` write there instead of a new root-level file. Before
   changing anything, grep the whole repo for `linkedin_analytics.csv` and `post_analytics.csv`
   (including `article-manager.html` / `insights.html` / any dashboard JS) so nothing else is
   silently assuming the current split.

2. **Replace the dead `xls_import.py` auto-call (Problem 3) with something real.** LinkedIn's
   analytics export is a manual, human-in-the-loop action (there's no pull API for it without the
   missing scope) — so an automatic subprocess call with no file path can never work. Default fix
   unless Joe says otherwise: remove the auto-call, and instead have Echo log one clear line per
   run when posts are stuck uncollected, e.g. "N post(s) awaiting analytics — export LinkedIn
   Analytics XLS and run `python linkedin_pipeline/xls_import.py <path>` to import them." Don't
   build a fancier `--watch`/folder-drop mode unless asked; that's scope creep for this task.

3. **Do NOT touch `linkedin_auth.py`'s `SCOPES`** to re-add `r_member_postAnalytics` — see Problem
   1. This is a hard LinkedIn platform constraint (Technical Sign-Off pending), not something to
   route around in code.

4. **Correct `CLAUDE.md`'s "Pending Actions" section.** The `r_member_social` "APPROVED June 20,
   2026 / added to SCOPES" note doesn't match the actual `SCOPES` string in
   `linkedin_pipeline/linkedin_auth.py` (never contained it) or LinkedIn's current documentation
   (lists `r_member_social` as closed to new applications). Replace that stale note with an
   accurate one, and fold in the actual current state of the `r_member_postAnalytics`/Community
   Management situation from this task.

5. Update `CLAUDE.md` / add a new `HANDOFF-2026-07-28-*.md` per the repo's existing convention
   (see recent entries for tone/format) documenting exactly what changed, and that the analytics
   scope gap remains open pending Joe's external LinkedIn Business Development conversation — that
   part cannot be closed by code.

## Guardrails

- Do not touch Priya's, Scout's, Writer's, Quill's, Maya's, Vera's, Porter's, Nova's, Cora's, or
  Lumen's core logic beyond the specific CSV-path fix in `run_lumen_batch.py`'s reader (if the
  canonical filename changes) — confirm with evidence first if you think a fix belongs elsewhere.
- Do not re-add `r_member_postAnalytics` (or `r_member_social`) to `SCOPES` under any
  circumstance in this task — that decision is external to this repo (LinkedIn approval), not a
  code change.
- `pipeline_config.json` stage toggles are dashboard-owned — do not change them.
- Don't commit unrelated pending WIP in this repo (`git status` will show plenty) — scope your
  commit to the files this task touches.
- If the dashboard (or anything else) turns out to also read/write one of these CSVs in a way
  that makes "just pick post_analytics.csv" the wrong call, stop and report back rather than
  guessing — this is data-integrity-adjacent (whichever file becomes canonical is what backfills
  the dashboard).

## When done, report

- Which file is now canonical for LinkedIn analytics, and every place that was updated to agree
  on it (list files touched).
- What Echo actually does now when a post can't be collected (exact log message / behavior).
- Confirmation that `SCOPES` in `linkedin_auth.py` is unchanged (still missing
  `r_member_postAnalytics`) and posting still works.
- The corrected `CLAUDE.md` Pending Actions text.
- Current `post_log.json` backlog count (how many `analytics_collected: false` remain) — this
  won't drop from code changes alone (still blocked on LinkedIn approval), but confirm the count
  wasn't accidentally made worse.
