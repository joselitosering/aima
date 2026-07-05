# Claude Code Task: Verify Article #19 Writer Stage (post-fix)

**Prepared:** 2026-07-04 · **Requested by:** Joe · **Why Claude Code, not Cowork:** Cowork's
bash tool runs in an isolated sandbox with its own unauthenticated `claude` CLI — every
verification attempt there fails immediately at `agents/base.py:call_cc_agent()` with
"Not logged in · Please run /login", regardless of what's actually broken in the pipeline
code. This needs to run where `claude` is logged in as Joe, i.e. this machine, via Claude Code.

## Context

The scheduled full-pipeline run (`AIMA_pipeline_...`, daily 23:55) died silently last night
partway through article #19 ("The Persuasion Engine: AI, Social Media, and the Death of
Shared Reality"). A Cowork session diagnosed and fixed two confirmed bugs today (2026-07-04,
uncommitted — see `git status`, there's other unrelated WIP in this repo too):

1. **Slug drift** (`agents/scout.py:_find_research_path()`, `run_writer_batch.py:resolve_spec()`) —
   a caller's mechanically-slugified title (`the-persuasion-engine-ai-social`) could miss
   Priya's actual CC-chosen research slug (`persuasion-engine`), causing a false
   `no_research` HALT even when research existed. Fixed with a `_meta.article_number` scan.
2. **Silent crash, no log** (`agents/base.py`, `agents/marco.py`) — `call_cc_agent()` raises
   an uncaught `RuntimeError` and nothing in `marco.py`'s stage sequence caught it, so a
   scheduled run's console (opened/closed by Task Scheduler) took the traceback to the grave.
   Fixed: `agents/base.py` now has a persistent `FileHandler` → `pipeline.log`; `marco.py`'s
   `run()` wraps every stage in one try/except with a `current_stage` tracker and writes a
   `### Pipeline CRASH` note (stage + full traceback) to `CLAUDE.md` on any unhandled exception.

**Both fixes are verified working as far as Cowork's sandbox allows** — `run_writer_batch.py
--article 19` no longer false-HALTs, and a real (non-dry-run) `python run.py` had its crash
caught, logged, and cleanly reported instead of dying. But every one of those test runs still
failed at the actual `claude` CLI call (sandbox auth), so **what really broke Stage 3 (Writer)
last night is still unknown** — Priya and Scout both worked fine on this machine that night
(their outputs exist: `articles/research/persuasion-engine-research.json`), so it's specifically
somewhere in Writer/Quill.

## What to do

1. Read `CLAUDE.md` and `HANDOFF.md` (insights repo) for full context on both fixes above.
2. Run `python repro_writer_019.py` (repo root — a throwaway repro script from today's Cowork
   session, safe to delete once #19 has a real draft) OR `python run_writer_batch.py --article 19`.
   Both should now get PAST the research-lookup step (already verified) and reach the real
   `claude` CLI call for the Writer stage.
3. **If it succeeds:** great — the two fixes above were sufficient. Confirm a draft landed at
   `articles/drafts/persuasion-engine-019-draft.html`, spot-check it's coherent AIMA article
   HTML in Joselito Sering's voice, then run `python run.py` (real, not `--dry-run`) to carry
   #19 through Quill → Maya → Vera. Given `pipeline_config.json` has `QC_GATE: "human"`, it
   will correctly HALT after Vera for your review — that's intentional, not a bug (see
   `HANDOFF.md`). Report back what happened at each stage.
4. **If it fails with a NEW error** (not the sandbox auth message) — that's the real root
   cause of last night's failure. Diagnose and fix it, following the same standard as the two
   fixes above: read the actual code, don't guess, and update `CLAUDE.md`/`HANDOFF.md`
   documenting what broke and why, per this repo's existing convention (see the entries dated
   2026-07-04 in `insights/HANDOFF.md` for the format/tone to match).
5. Also worth a quick look while you're in there: the schtasks command in
   `insights/src/app/api/schedule/route.ts` (`const tr = ...`) still has no stdout/stderr
   redirection for NEW schedules created going forward — the existing `AIMA_pipeline_...`
   task in Windows Task Scheduler was created before today's `pipeline.log` fix and won't
   pick it up unless it's deleted and recreated via the dashboard's Schedule panel. Consider
   whether that redirection is still worth adding there as defense-in-depth (Marco's own
   `pipeline.log` should cover most cases now, but an import-time crash before logging is
   configured — e.g. a missing dependency — would still be invisible).

## Guardrails (per CLAUDE.md)

- Do not touch Priya, Scout, Maya, Porter, Nova, Cora, Echo, Lumen, Trend Scout unless the
  real Stage-3 bug turns out to live in one of them too — confirm with evidence first.
- `QC_GATE: "human"` is intentional (confirmed with Joe 2026-07-04) — do not change it or
  auto-publish/auto-post as part of this task.
- Don't commit the rest of this repo's unrelated pending WIP (`git status` shows a lot) —
  scope your commit to just the files this task touches.
- `articles/research/persuasion-engine-research.json` and `repro_writer_019.py` should stay
  until #19 has a real draft — needed to resume this cleanly.

When done, report: what actually broke Stage 3 (if anything new), what you changed, and
whether article #19 now has a real draft ready for Vera/human review.
