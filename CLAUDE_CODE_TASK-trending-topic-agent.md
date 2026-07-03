# Claude Code Task: Trending-Topic Determination for Dawn/Kenji Writer Batches

**Prepared:** 2026-07-02 · **Requested by:** Joe · **Why Claude Code, not Cowork:** this is a
multi-file engineering change to `agents/`/`run_*.py` that needs to be written, run, and
iterated against the real `claude` CLI (`agents/base.py:call_cc_agent`, subscription-billed) —
that's Claude Code's native execution model, not a sandboxed dashboard session. Paste the
prompt below into Claude Code in the `aima` repo.

---

## Prompt to paste into Claude Code

```
Read CLAUDE.md and AIMA-HANDOFF-v2.6.md first, then implement trending-topic
determination for Dawn and Kenji's writer batch.

THE PROBLEM
Dawn and Kenji's calendar rows (aima-editorial-calendar.md, "## Dawn Ginhaua" and
"## Kenji Nakamoto" sections, slot labels D1-D13 / K1-K12) are almost all still
literally titled "TBD — Trending Topic (Dawn)" / "TBD — Trending Topic (Kenji)".
There is currently NO code anywhere that turns a TBD slot into a real topic:

- agents/scout.py's run(spec) does research SUPPORT for a title it's given — it
  does not invent topics.
- run_research_batch.py's _read_calendar_rows() and run_writer_batch.py's
  _calendar_rows() both parse the calendar with a regex that only matches
  numeric slot labels (\|\s*(\d+)\s*\|) — they literally cannot see D1/K1-style
  rows at all today. Dawn/Kenji rows never enter either batch script's specs.
- aima-coworker-state.json has a "trending": { "topic_queue": [] } field that
  looks like it was designed for exactly this, but it's empty and there is zero
  code in agents/*.py that reads or writes it.
- Confirmed by checking git history: the old, retired linkedin_pipeline/pipeline.py
  never had this logic either — it was purely a fetch-and-post-to-LinkedIn
  pipeline (today's Porter+Nova equivalent), no research/topic logic at all.
- Historically, both trending articles written so far (#014 "Your AI Ethics
  Board Is a Press Release" and #017 "The Résumé Filter") were written as
  manual one-offs outside the calendar-row system entirely (they don't match
  any calendar.md row by title). This confirms trending topics have never been
  automated — always a human decision.

WHAT TO BUILD
1. A trending-topic-determination step, run BEFORE Scout, triggered whenever
   the resolved calendar row's title is literally "TBD — Trending Topic (...)".
   Suggest making this a new function in agents/scout.py (e.g.
   determine_trending_topic(persona: str, category_hint: str | None = None) -> dict)
   or a new agents/trend_scout.py module if you think the separation is
   cleaner — your call, but keep it a CC_AGENT-tier call (uses call_cc_agent,
   same pattern as scout.run()) since this needs live judgment, not just
   fetch-and-filter.

2. Source material for candidate topics — use what's actually configured today
   (do not assume Reddit/X/Statista exist; they're aspirational per CLAUDE.md's
   "Scout Agent — Planned Enhancements" section, not present in
   scout-sources.json as of this writing):
   - News APIs already in scout-sources.json: guardian, nyt, newsapi, gnews,
     currents, mediastack, event_registry
   - google_trends (pytrends, unofficial, rate-limited — see the entry's notes)
   - The 115 RSS feeds, filtered by topic_tags relevant to each persona's beat
     (check articles/personas/dawn-ginhaua.md and articles/personas/
     kenji-nakamoto.md for each persona's actual beat/tone — Dawn = press-release
     skepticism / corporate accountability per her D1 tone note, Kenji =
     optimistic deep-dives per his K1 tone note)
   - WebSearch as a fallback for anything the above can't surface (Scout
     already does this for research; reuse the same pattern)
   Feel free to add real, working API/RSS sources to scout-sources.json if you
   find better ones for "what's trending in AI right now" — that file is
   meant to grow.

3. Dedup — before finalizing a candidate topic, check it isn't already
   covered: compare against all titles in aima-editorial-calendar.md, all
   titles in aima-coworker-state.json's articles_written[], and all files in
   articles/research/ (slug match). Re-roll or pick the next-best candidate on
   collision.

4. Once a topic is chosen, WRITE THE REAL TITLE BACK into
   aima-editorial-calendar.md, replacing "TBD — Trending Topic (Dawn)" (or
   Kenji) with the real title and a real category, in place, same row/slot.
   This is important: it makes the decision durable (visible in the calendar
   for humans and for the insights dashboard) and idempotent (re-running the
   batch on an already-resolved slot should just see a real title now and skip
   straight to Scout, not re-roll a new topic every run).

5. Fix the two batch scripts' calendar regex so Dawn/Kenji rows are visible at
   all: run_research_batch.py's _read_calendar_rows() and
   run_writer_batch.py's _calendar_rows() both need to also match D\d+/K\d+
   slot labels, not just \d+, and need to track which track/persona owns each
   row (Kenji vs Dawn vs Joselito) the way _calendar_rows() already tracks
   "author" from the ## heading.

6. Wire it in: when run_writer_batch.py (or run_research_batch.py) resolves a
   spec whose title starts with "TBD — Trending Topic", call the new
   determine_trending_topic() step first, get back a real title/category,
   persist it to the calendar (step 4), then continue with Scout research +
   writer draft using the real title — same flow as any other article from
   that point on.

GUARDRAILS (per CLAUDE.md)
- This is a CC_AGENT call (real tokens/subscription usage) — add it to
  agents/config.py's CC_AGENTS set, CC_MODEL_OVERRIDE, and BUDGET_MAP (Scout's
  own budget is 50,000; this step should probably get its own smaller budget
  since it's topic selection, not full research — suggest ~10,000-15,000,
  but use your judgment).
- Writers still do not research and still HALT without a Scout brief — don't
  let this new step bypass that rule; it only replaces the TITLE, Scout still
  has to run and produce real research afterward.
- Follow the existing fiduciary rule: report/log what topic was chosen and
  why (a short rationale + the 1-2 sources that surfaced it), the same way
  Scout's output already cites sources — don't have this step silently
  mutate the calendar with no trace of its reasoning. A good place for this
  log is a new field alongside the Tone Note column, or a
  articles/research/[slug]-topic-selection.json sidecar — your call.
- Do not touch Priya, Vera, Quill, Marco, Maya, Porter, or Nova's logic.
- Do not recreate or call linkedin_pipeline/pipeline.py (retired).

TEST PLAN
- Dry-run against the 6 currently-TBD rows in aima-editorial-calendar.md
  (Dawn: D2 [2026-07-07], D3 [2026-07-08], D4 [2026-07-10]; Kenji: K1
  [2026-07-06], K2 [2026-07-07], K3 [2026-07-09]) without necessarily
  spending a full batch run on all 6 — one Dawn + one Kenji row is enough to
  prove the flow end to end (topic chosen -> dedup check -> calendar updated
  -> Scout research produced -> writer draft produced).
- Confirm re-running the batch on an already-resolved slot does NOT re-roll a
  new topic (idempotency check from requirement 4).
- Confirm the two calendar-regex fixes (requirement 5) don't change any
  existing behavior for Joselito's numeric rows — run the existing test/
  smoke path for a numeric row (e.g. --article 19) and confirm it's unaffected.

When done, report back: which files changed, the exact topics chosen for the
two test rows and why, and update AIMA-HANDOFF-v2.6.md / CLAUDE.md with a
short note on the new capability (per this repo's existing convention of
documenting agent behavior there).
```
