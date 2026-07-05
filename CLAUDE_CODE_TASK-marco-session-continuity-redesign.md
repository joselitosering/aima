# Claude Code Task: Redesign Marco for Session Continuity (Cost Reduction)

**Prepared:** 2026-07-04 · **Requested by:** Joe · **Why Claude Code + Opus, not Cowork:**
this is a multi-file architecture change touching every agent module, has to preserve
several non-obvious guardrails (Vera's halt-don't-iterate rule, Cora's budget gating, the
crash-logging added today), and needs deliberate design reasoning rather than ad hoc edits.
Per this repo's own CLAUDE.md rule ("if a task is better suited for Opus in Claude Code,
tell me so we can port it over") — Joe asked for this to be ported.

**Note on token budget:** this redesign does NOT dodge Joe's Claude subscription session
limit — Claude Code and Cowork draw from the same account/session pool (confirmed 2026-07-04:
a Cowork-invoked `claude` CLI call hit "You've hit your session limit" the same way a
standalone terminal call would). Work this incrementally, verify with the cheapest possible
real calls, and don't loop/retry expensively — see "Session-limit discipline" below.

## Context — why this task exists

Today (2026-07-04), across a long session, we:

1. Diagnosed and fixed two real bugs in the pipeline (slug-drift between Priya's chosen slug
   and mechanical `_slugify()`; a silent uncaught-crash-with-no-log path). Both fixed and
   verified — see the "Pipeline CRASH" and "RESOLVED" entries in this file below this task.
2. Found and fixed a bigger bug: `token_budget.json`'s `used` field was NEVER incremented
   anywhere in the codebase — `call_cc_agent()` ran the `claude` CLI in plain `--print` text
   mode, which returns no usage data at all. Fixed by switching to `--output-format json` and
   parsing the CLI's own `usage`/`total_cost_usd` fields (see "Cora token tracking — FIXED"
   entry below). This is what makes real cost measurement possible for the rest of this task.
3. Ran article #19 to completion end-to-end (published + LinkedIn posted) after a session-limit
   crash blocked it earlier in the day.
4. Joe raised an architectural point: Marco's docstring says he's the orchestrator, but
   nothing about Marco actually **carries context across stages** — every stage (Priya,
   Trend Scout, Scout, Writer, Quill, Maya, Vera, Cora) is a **separate cold `claude --print`
   subprocess call**, each paying its own system-prompt/tool-context overhead. The *original*
   `aima-article-coworker` Cowork scheduled task (now disabled, built on the retired
   `next_track` model) did the whole job in **one continuous session** and was structurally
   cheaper — but has none of Marco's QC/governance rigor (no Vera, no Quill edit pass, no
   Maya dual-image generation, no Cora, no Trend Scout).
5. Tested the obvious fix — chaining Marco's separate calls together via `claude --resume
   <session_id>` with a different `--system-prompt` per stage (confirmed via
   https://code.claude.com/docs/en/cli-reference that system-prompt flags apply per
   invocation, so this is mechanically possible) — **and it did not help.** Real numbers from
   a live 3-call test tonight:

   | Call | cache_creation | cache_read | cost |
   |---|---|---|---|
   | Fresh, cold (1st call of the batch) | 21,937 | 0 | $0.1323 |
   | Resumed, different system prompt | 9,711 | 13,237 | $0.0623 |
   | Fresh, NOT resumed (control) | 8,774 | 13,237 | $0.0572 |

   The control (no resume at all) was *cheaper* than the resumed call. Both resumed and
   non-resumed calls got the same cache_read benefit — that's Anthropic's server-side prompt
   caching on the shared repo/tool-definition prefix, which kicks in for ANY calls made close
   together in time regardless of `--resume`. Chaining sessions added a little overhead
   (larger conversation payload to reprocess) for no measurable benefit.

## The actual conclusion (don't relitigate this without new evidence)

**`--resume` chaining is not the fix. Do not design around it.** The original coworker's
cost advantage came from being **one continuous interactive session that never spun up a new
CLI subprocess per stage** — not from any session-resume trick. Marco's real cost driver is
the **number of distinct cold subprocess launches** (each with its own system prompt = its
own cache-creation event that must be paid at least once), not lack of context-carrying via
`--resume`.

This reframes the goal: don't try to preserve Marco's current "9 separate `claude --print`
calls, chained via --resume." Instead, **collapse the pipeline into meaningfully fewer**
**distinct cold-start events** — ideally one continuous session/context that performs all
stages as in-session reasoning steps or `Task`-tool subagent calls (which run inside the
same billed session, not as separate OS subprocesses), while preserving every stage's
distinct role, guardrails, and quality bar.

## Goal

Redesign Marco (`agents/marco.py` + how it's invoked) so that a full article run costs
meaningfully less than today's ~9-cold-subprocess-call pipeline, **without losing any
existing guardrail or quality gate**, and ideally without losing the ability to run any
single stage standalone (the `run_<batch>.py` scripts at repo root — dashboard buttons hit
these via `/api/run`).

### Two candidate directions — evaluate both, pick one, document why

**Direction A — true single-session coworker.** Rebuild the daily driver as one continuous
Claude Code session (interactive agent loop, not `--print` one-shots) that walks through
Priya → Trend Scout → Scout → Writer → Quill → Maya → Vera → Porter → Nova → Cora as
in-context reasoning steps, using the `Task` tool for genuine subagent isolation only where
it earns its cost (Vera's "fresh eyes" QC review is the strongest candidate — she should
arguably NOT share the writing process's context, to keep her check honest; the CLAUDE.md
guardrail "Vera halts+reports, never iterates" must survive this exactly as-is). This is
architecturally what `articles/aima-coworker-prompt.md` did, rebuilt on the CURRENT canonical
calendar model (`DECISION-LOG.md`, 2026-07-02: one canonical numbered sequence, Author is a
per-row attribute, `next_track` retired) instead of the old track-rotation model, and with
the QC/governance stages the old coworker never had.

**Direction B — stage consolidation within Marco's current architecture.** Lower-risk,
smaller change: merge adjacent CC calls that don't need independence. The clearest candidate
is Writer+Quill — today Writer drafts freely, then a SEPARATE cold call (Quill) edits that
draft to Vera's checklist. Merging these into one call (write, then in the same turn edit to
target length/structure) removes one full cold-start per article. Evaluate whether
Trend-Scout-into-Priya and Maya's image-generation-into-merge are similarly mergeable without
losing their distinct guardrails.

**Recommendation for you to validate, not assume:** try Direction B first — it's a much
smaller diff, is easy to A/B against today's per-agent budgets in `token_budget.json` (now
real, thanks to the tracking fix), and de-risks the bigger Direction A rebuild. Only invest in
Direction A once Direction B's real savings are measured and Joe decides it's not enough.

## Guardrails that MUST survive this redesign unchanged

These are load-bearing rules from this repo's `CLAUDE.md` — treat violating any of them as a
regression, not a simplification:

- **Vera halts+reports, never iterates.** If QC fails, the pipeline stops and reports to
  Marco/Joe for human or Iris review. Vera must never trigger a re-run of Quill or Maya
  herself. If Direction A makes Vera an in-session step instead of a subagent, this rule is
  easy to accidentally violate (the temptation to "just fix it and retry" in one continuous
  session is exactly the failure mode to avoid) — keep Vera's verdict a hard stop.
- **Writers halt without research.** No stage should ever fabricate research to keep moving.
- **Skip-and-reuse cached artifacts.** Existing research JSON / drafts / merged articles must
  still be detected and reused rather than regenerated — this is how today's Marco resumes
  cleanly after a crash (see the `_find_research_path()` / `find_draft()` / Quill's
  file-exists-skip logic in the current code — study these before changing anything, they're
  intentionally defensive against the exact slug-drift and mid-run-crash scenarios that bit
  us today).
- **Gate token/credit/live batches** — no design should make it easier to accidentally
  auto-publish or auto-post; `pipeline_config.json`'s `QC_GATE` (`human`/`auto`),
  `PUBLISH_ENABLED`, `MARKETING_ENABLED` etc. must remain honored exactly as they are today,
  regardless of which direction you take.
- **Report calendar bugs, don't auto-mutate the calendar** — except the one sanctioned
  exception: Trend Scout fills a still-TBD trending row's title+category with a logged
  rationale (`agents/trend_scout.py`). Don't extend calendar-mutation permissions to any other
  stage as a side effect of this redesign.
- **Calendar is ONE canonical sequence** (2026-07-02 decision, `DECISION-LOG.md`) — rows
  numbered 1–64, Author is a per-row attribute, never a track. Don't reintroduce
  `next_track`/track-rotation logic even if you're borrowing structure from the old
  `aima-coworker-prompt.md` — that file is a useful reference for the "one continuous session"
  *pattern*, not for its (retired) data model.
- **Cora's budget/hallucination governance must remain meaningful.** Now that real per-call
  usage is captured (see below), whatever design you land on needs a real way to attribute
  token/cost usage per logical stage, even if stages are no longer separate OS processes —
  don't regress token_budget.json back to being decorative.

## What's already fixed today — don't rediscover these

- **Slug-drift bug** (`agents/scout.py::_find_research_path()`, `run_writer_batch.py::resolve_spec()`):
  a caller's mechanically-slugified title could miss Priya's actual CC-chosen slug. Fixed
  with a `_meta.article_number` scan. Verified working.
- **Silent-crash-no-log bug**: `agents/base.py` now has a persistent `FileHandler` →
  `pipeline.log`. `agents/marco.py::run()` wraps every stage in one try/except with a
  `current_stage` tracker and writes a `### Pipeline CRASH` note (stage + full traceback) to
  `CLAUDE.md` on any unhandled exception. Verified working (see the RESOLVED entry for
  article #19 below).
- **Token tracking (today's big fix)**: `agents/base.py::call_cc_agent()` now runs with
  `--output-format json` and calls a new `_record_token_usage()` that writes real
  `usage.{input,output,cache_creation_input,cache_read_input}_tokens` and `total_cost_usd`
  into `token_budget.json`, keyed by a new `_AGENT_CODE_MAP`. `agents/cora.py::init_budget()`
  is now idempotent per run_date+article_number (won't wipe usage from a resumed run) and
  Marco now calls it *before* Priya's own CC call, not just after. Two previously-invisible
  buckets were added: `TS` (Trend Scout) and `WR` (Writer — Joselito/Dawn/Kenji share one
  bucket). **This is the instrumentation you should build the cost comparison on** — after
  any change you make, run one real article through both the old and new path and diff
  `token_budget.json` + `total_cost_usd` for a real before/after number, not an estimate.

## Session-limit discipline (important given Joe's account is close to its weekly cap)

- Don't loop verification calls. Every real `claude` CLI call costs real budget from the same
  pool Joe uses everywhere else (Cowork included). Design and code-review as much as possible
  by reading, not by running.
- When you do need to run something real, run the smallest possible probe first (a trivial
  system-prompt + one-word response, like the 3-call test above cost $0.25 total) before a
  full article run.
- If a call fails with `"You've hit your session limit · resets <time>"`, stop — don't retry,
  don't work around it, report the reset time and wait or hand off.
- Prefer reading `token_budget.json` / `optimization_report.json` after a real run over
  re-running things to "double check."

## Files to read before changing anything

- `agents/marco.py` — current orchestration sequence, the crash-handling added today, stage
  toggles.
- `agents/base.py` — `call_cc_agent()`, now with the JSON-output + token-recording fix. This
  is the seam you're most likely to change for Direction A (replacing subprocess-per-stage
  with an in-session model changes what this function even means).
- `agents/config.py` — `CC_AGENTS`/`PY_AGENTS` split, `BUDGET_MAP`, `CC_MODEL_OVERRIDE`,
  `pipeline_config.json` loader.
- `agents/priya.py`, `agents/trend_scout.py`, `agents/scout.py`, `agents/writer.py`,
  `agents/quill.py`, `agents/maya.py`, `agents/vera.py`, `agents/cora.py` — every CC-calling
  stage's current prompt-building and skip-and-reuse logic.
- `agents/porter.py`, `agents/nova.py` — pure-Python stages (no CC calls, don't need
  redesigning, but Marco's sequencing around them matters).
- `pipeline_config.json` — dashboard-owned stage toggles; must keep working.
- `articles/aima-coworker-prompt.md` — the OLD single-session coworker's prompt. Useful
  reference for the "one continuous session" pattern (Direction A). Do NOT reuse its
  `next_track` references — retired.
- `C:\Users\ShadowMonkey\Claude\Scheduled\aima-article-coworker\SKILL.md` (on Joe's machine,
  Cowork scheduled task config, currently `enabled: false`) — shows how the old coworker was
  actually invoked (reads and executes the prompt file above in one Cowork session).
- `DECISION-LOG.md` — the 2026-07-02 canonical-calendar decision; don't violate it.
- `CLAUDE.md` (this file) — read top-to-bottom, especially the fiduciary rules near the top
  and every dated entry below this task; they're the project's living memory and several are
  directly relevant guardrails, not just history.
- `token_budget.json` — now real (see fix above). Use it to measure, not estimate.

## Deliverable / success criteria

1. A working redesign (Direction A or B, your evidence-based call) that produces
   equivalent-quality article output to today's Marco pipeline.
2. A real, measured cost comparison — run one article through the old path and one through
   the new path (or the same article idempotently re-run if cache/skip logic allows), and
   diff actual `total_cost_usd` sums from `token_budget.json`. Not an estimate — Joe
   explicitly does not want guessed numbers here.
3. Every guardrail in the list above still verifiably true (write a short checklist and
   confirm each one, don't just assert it).
4. `pipeline_config.json` toggles all still honored.
5. Update `CLAUDE.md` and `insights/HANDOFF.md` with what changed and the real before/after
   cost numbers, per this repo's existing convention (see the dated entries in both files for
   format/tone to match).
6. Report back: which direction you took, why, the measured $ savings per article, and
   anything you deliberately chose NOT to change and why.

## Non-goals

- Don't change Priya/Scout/Writer/Quill/Vera's actual voice, quality bar, or persona content
  beyond what the architecture change requires.
- Don't touch `linkedin_pipeline/` (Porter/Nova's publish+marketing logic) — out of scope.
- Don't re-enable the old `aima-article-coworker` Cowork scheduled task as-is — it's missing
  guardrails this task exists to preserve, not to reintroduce.
- Don't revert or "clean up" the token-tracking fix from today — build on it.
