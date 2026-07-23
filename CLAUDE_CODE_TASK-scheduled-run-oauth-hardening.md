# Claude Code Task: Harden Scheduled Pipeline Against OAuth Failures (for good)

**Prepared:** 2026-07-22 · **Requested by:** Joe (via Cowork review) · **Why Claude Code, not
Cowork:** this needs (a) precise multi-file Python engineering across `marco.py`/`base.py`/
`trend_scout.py`, and (b) a live check against Windows Task Scheduler and the actual `claude`
CLI credential store on this machine — Cowork's sandbox has its own unauthenticated `claude`
CLI and cannot verify anything auth-related here. Do this on Joe's machine.

## Context

The scheduled full-pipeline run (`AIMA_pipeline_...`) has crashed identically **5 times today**
(2026-07-22), all logged in `CLAUDE.md`, all at the same choke point:

```
priya.run() → trend_scout.resolve_tbd_row(29) → determine_trending_topic()
            → call_cc_agent("trend_scout", ...) → RuntimeError: CC OAuth expired
```

Article **#29** (`articles/aima-editorial-calendar.md`, row 29) is still the literal
`TBD — Trending Topic` placeholder, assigned to Kenji Nakamoto. Every scheduled fire calls
`trend_scout` to resolve it, which requires the `claude` CLI, which is failing OAuth in that
execution context. Every retry hits the identical wall because nothing changes between
retries — the row stays TBD, the crash repeats verbatim.

**Two prior (Cowork) diagnoses already on file, do not re-derive:**
- `articles/../CLAUDE.md` "Pipeline Scheduled-Run Silent Failure" section — logging/crash-catch
  infra already fixed 2026-07-04 (persistent `FileHandler` → `pipeline.log`, `marco.py`'s
  top-level try/except + `_write_crash_to_claude_md`). That part is working correctly — it's
  *why* we have clean crash records for all 5 of today's failures instead of silence.
- `agents/base.py:call_cc_agent()` already has a 3-tier auth fallback ladder built in
  (2026-07-14ish): OpenRouter (Tier A, only for agents in `config.API_MODEL_MAP`) → direct
  Anthropic API (Tier B, `ANTHROPIC_API_KEY`) → raise with the 3-option fix-me message you're
  currently seeing. `trend_scout` is **not** in `API_MODEL_MAP`'s always-on set in a way that
  reaches it safely (see problem 2 below), and `ANTHROPIC_API_KEY` isn't set at all, so it falls
  straight through to the raise.

## The actual problems (in priority order)

**1. `trend_scout`'s job cannot survive on the existing Tier B fallback — don't just add the key blindly.**
`call_anthropic_api()` (`agents/base.py` ~line 442) is a plain Messages API call: no tools, no
web search. `trend_scout`'s entire value is surveying live RSS/API sources
(`scout-sources.json`) for what's *actually* trending right now (`agents/trend_scout.py`,
`determine_trending_topic()`). If OAuth failure silently falls through to Tier B, trend_scout
will fabricate a "trending" topic from training data with fake-looking sources — a direct
violation of this project's zero-hallucination rule, and worse than the current crash (a crash
is at least honest). **Do not let `trend_scout` (or `scout`) resolve via `call_anthropic_api`.**
Either: (a) exclude them from the Tier B fallback path explicitly (raise a distinct,
clearly-labeled error instead), or (b) if Tier A (OpenRouter `:online`) is enabled in the
future, only that tier is acceptable for these two agents since it preserves real search.

**2. No isolation between "expected, recoverable" failures and "unknown, needs a human" failures.**
Right now ANY uncaught exception in ANY stage look identical in `CLAUDE.md`: a full traceback
dump. An OAuth expiry on a TBD-row resolution is a known, recoverable condition (per this
task) — it should produce a short, clearly labeled, actionable note ("TBD row #N unresolved —
trend_scout needs a live CC session, scheduled run skipped cleanly") rather than being
indistinguishable from a genuine new bug.

**3. `CLAUDE.md` crash-log duplication.** `agents/marco.py:_write_crash_to_claude_md()`
(~line 505) unconditionally appends a full traceback block on every call, no dedup. Today it
appended the *same* traceback 5 times (`CLAUDE.md` is now 76,945+ bytes and growing). Add a
same-day + same-stage + same-error-prefix dedup: bump an `occurrences: N` / `last_seen: <ts>`
field on the existing entry instead of appending a new block.

**4. Task Scheduler root-cause is still unverified, not confirmed.** The raised error message's
own suggestion ("Task Scheduler may be running as SYSTEM instead of your user account") is a
hypothesis written into the code, not a diagnosed fact. Verify it for real:
   - Check the `AIMA_pipeline_...` task's Properties → General → "Run as" account.
   - Check whether "Run whether user is logged on or not" is set, and whether a password is
     stored (unchecking "Do not store password" may be required for the profile — and thus the
     `claude` CLI's credential store — to load under a non-interactive logon).
   - Confirm empirically: have the scheduled task run `claude --print "ping"` as a canary step
     before the real pipeline and log whether *that* succeeds under the task's actual identity.
     If the canary fails too, the Task-Scheduler-identity theory is confirmed; if the canary
     succeeds but the pipeline still fails, look elsewhere (e.g. concurrent `claude.exe`
     processes sharing one account's session budget — see the 2026-07-04 "session limit"
     incident already in `CLAUDE.md`, a different but related failure mode).

## What to do

1. **Unblock article #29 immediately** (independent of everything else, do this first): either
   replace row 29's `TBD — Trending Topic` in `articles/aima-editorial-calendar.md` with a real
   title for Kenji, or run `trend_scout.resolve_tbd_row(29)` once interactively from a terminal
   where `claude` is confirmed logged in (`claude --print "ping"` should succeed first). This
   alone stops tonight's scheduled run from hitting this exact wall again, regardless of what
   else you fix below.

2. **Verify the Task Scheduler identity** per point 4 above. Report what you actually find — do
   not assume the code's own guess is correct without checking.

3. **Harden `trend_scout`'s failure mode** (`agents/trend_scout.py`, `agents/base.py`,
   `agents/marco.py`):
   - In `call_cc_agent()` (`agents/base.py` ~line 191), when the auth-failure branch is hit
     (`_is_cc_auth_error`) for `name in ("trend_scout", "scout")`, do NOT fall through to
     `call_anthropic_api` even if `ANTHROPIC_API_KEY` is set — raise a distinct exception type
     (e.g. `TrendScoutUnavailableError` or similar) with a message that's explicit this is a
     recoverable/skip condition, not a code bug.
   - In `marco.py`, catch that specific exception around the `priya.run()` call (which is where
     `trend_scout.resolve_tbd_row` fires) and return a clean, distinctly-flagged halt result
     (new outcome type, e.g. `"trend_scout_unavailable"` — thread it through `run.py`'s
     `_classify()` too) instead of falling into the generic `crashed` bucket. This should NOT
     advance `next_article_number` and should NOT touch the calendar.
   - It's fine (better, even) for `ANTHROPIC_API_KEY` to remain a valid Tier B fallback for
     every OTHER CC agent (`iris`, `lumen`, `cora` are governance/synthesis, not live-fact
     agents — Tier B is an acceptable trade there). Just carve out `trend_scout`/`scout`.

4. **Fix the `CLAUDE.md` dedup** in `_write_crash_to_claude_md()` per point 3 above.

5. **Do NOT unilaterally enable OpenRouter.** `agents/.env` has `OPENROUTER_API_KEY` explicitly
   commented out with a note "not funding OpenRouter" (see `DECISION-LOG.md` and
   `agents/.env` line 19). OpenRouter's `:online` tier is the only path that would give
   `trend_scout`/`scout` a tool-capable fallback without OAuth — but funding it is Joe's call,
   not yours. Flag it as an option in your final report; don't turn it on.

6. Update `CLAUDE.md` / `HANDOFF-*.md` with what you found and changed, per this repo's existing
   convention (see the 2026-07-04 entries for format/tone to match) — including the real answer
   to the Task Scheduler identity question from step 2, since that's been an open hypothesis
   across multiple incidents now.

## Guardrails (per CLAUDE.md / project rules)

- Do not touch Priya's, Scout's, Maya's, Porter's, Nova's, Cora's, Echo's, or Lumen's core
  logic beyond the specific `trend_scout`/`scout` fallback carve-out in point 3 — confirm with
  evidence first if you think the bug lives somewhere else.
- `QC_GATE` and stage toggles in `pipeline_config.json` are dashboard-owned — do not change
  them as part of this task.
- Do not enable OpenRouter (`OPENROUTER_API_KEY`) — see point 5.
- Don't commit unrelated pending WIP in this repo (`git status` will show plenty) — scope your
  commit to the files this task touches.
- This is billing/infra-adjacent (Task Scheduler identity, API key fallback tiers) — be
  conservative; if something is ambiguous (e.g. whether a given agent's fallback loses too much
  quality), stop and ask rather than guessing.

## When done, report

- What the Task Scheduler "Run as" account actually was, and whether changing it (if needed)
  resolved the canary check.
- What you changed in `base.py` / `marco.py` / `trend_scout.py`, and why.
- Whether article #29 has a real title now and the pipeline can run past `priya` cleanly.
- Confirm `CLAUDE.md` no longer duplicates identical crash blocks on repeat failures.
