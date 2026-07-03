# Claude Code Task: Lumen Run — Cost & Efficiency Fixes

**Prepared:** 2026-07-03 · **Requested by:** Joe · **Why Claude Code, not Cowork:** this is a
multi-file engineering change to `agents/lumen.py` / `agents/prompts.py` / `run_lumen_batch.py`
that needs to be written and smoke-tested against the real `claude` CLI
(`agents/base.py:call_cc_agent`, subscription-billed) — Claude Code's native execution model,
not a sandboxed dashboard session. Paste the prompt below into Claude Code in the `aima` repo.

Context: the July 3 Lumen run (triggered from the Pipeline dashboard's Analytics tab) succeeded
(exit 0) but ran long. Investigation during that session found three concrete inefficiencies —
all confirmed by reading the current code, not guessed.

---

## Prompt to paste into Claude Code

```
Read CLAUDE.md and AIMA-HANDOFF-v2.6.md first, then fix three cost/efficiency
issues in the Lumen batch run (agents/lumen.py, agents/prompts.py,
run_lumen_batch.py, agents/config.py).

THE PROBLEMS (confirmed by reading current code as of 2026-07-03)

1. DEDUP CHECK RUNS TOO LATE — real cost bug.
   agents/lumen.py's run() calls call_cc_agent() FIRST (the paid, subscription
   -billed CC call), and only AFTER that checks optimization_report.json for
   an existing same-day "lumen" entry, skipping just the append if one exists.
   Re-running Lumen twice in a day pays for the full CC call twice and
   discards the second result. Move the "already_written" dedup check to
   BEFORE call_cc_agent — read optimization_report.json, check for a
   same-day lumen entry, and short-circuit (return the existing entry,
   log a skip, no CC call) if found.

2. PROMPT ASKS FOR 3 PLATFORMS WITH NO CREDENTIALS, EVERY RUN.
   lumen_secrets.json does not exist in the repo. LUMEN_PROMPT
   (agents/prompts.py) unconditionally instructs the agent to collect from
   Meta Graph API, TikTok Business API, and Buy Me a Coffee API regardless.
   The agent burns tokens/tool-calls discovering it can't authenticate to
   any of the three, every single run. Fix: in run_lumen_batch.py, check
   whether lumen_secrets.json exists before building the prompt.
   - If it doesn't exist: build a reduced prompt that only asks for GA4 +
     the LinkedIn report already passed in, and have it write a static
     "meta/tiktok/bmc: skipped, no lumen_secrets.json" flag into its
     entry instead of letting the live agent rediscover that each run.
   - If it does exist: keep today's full multi-platform prompt as-is.
   Implement this as a prompt-builder function (e.g. build_lumen_prompt
   (has_secrets: bool) -> str) rather than a hardcoded string, so it's
   easy to extend once real Meta/TikTok/BMC credentials land.

3. WRONG MODEL TIER FOR WHAT'S LEFT.
   agents/config.py's CC_MODEL_OVERRIDE["lumen"] = None, which defaults to
   Sonnet. Once #2 is fixed, a no-secrets run is mechanical: read two CSVs,
   compute totals/averages, write JSON matching a fixed schema — no
   judgment call comparable to Scout's research or Quill's writing. Change
   CC_MODEL_OVERRIDE["lumen"] to "claude-haiku-4-5" for the no-secrets path.
   If you keep the full multi-platform path when secrets exist, use your
   judgment on whether that path should stay on Sonnet (it involves
   synthesizing across 4 live data sources into flags/recommendations,
   which may warrant it) — but the common case today (no secrets) should
   run on Haiku.

GUARDRAILS (per CLAUDE.md)
- Do not touch Echo, GA4 collection, Marco, Priya, Scout, Quill, Vera,
  Maya, Porter, Nova, Cora, or Trend Scout's logic.
- Lumen's budget stays ~10,000 tokens (agents/config.py BUDGET_MAP) unless
  you have a specific reason to change it — note the reason if you do.
- Keep the existing fiduciary trace: Lumen's entry must still say what it
  did and did not collect (the "meta/tiktok/bmc: skipped" flag from #2
  IS this trace for the skipped platforms — don't silently drop them from
  the report, mark them as skipped with a reason).
- Don't remove the 1800s subprocess timeout in agents/base.py — that's
  shared infra used by all CC agents, out of scope here.

TEST PLAN
- Run run_lumen_batch.py twice in a row same day. First run should call
  the CC agent and write an entry. Second run should log a dedup skip and
  make NO CC call (confirm via added log line, e.g. "[lumen-batch] entry
  already exists for today — skipping CC call").
- With lumen_secrets.json absent (today's real state), run once and
  confirm: (a) the CC call completes noticeably faster than the July 3
  baseline, (b) the written entry has a clear "skipped: no credentials"
  flag for meta/tiktok/bmc, (c) GA4 + LinkedIn data in the entry is
  unchanged in quality from before.
- Confirm CC_MODEL_OVERRIDE change is actually picked up (log which model
  string is passed to the claude CLI invocation).

When done, report back: which files changed, before/after wall-clock time
for a no-secrets run if you can measure it, and update AIMA-HANDOFF-v2.6.md
/ CLAUDE.md with a short note under the Lumen Agent section documenting
the dedup-before-call and no-secrets-prompt behavior, per this repo's
existing convention.
```
