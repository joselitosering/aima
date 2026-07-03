# AIMA Decision Log

Running log of editorial-engine decisions. Newest first. (This file was
referenced by the calendar header before it existed — earlier decisions live
in AIMA-DECISIONS-2026-06-27.md and SESSION_LOG.md.)

---

## 2026-07-02 — Slot-label tracking retired; one canonical number sequence; author is a per-row attribute

**Decided by:** Joe. **Standing rule — do not reintroduce slot labels.**

1. **Article tracking is by canonical number only.** The per-author calendar
   sections and slot labels (`D1`–`D13`, `K1`–`K12`) are retired. The calendar
   is ONE table: `| # | Date | Title | Category | Read | Tone Note | Author |`.
2. **Author is an attribute, not a track.** Any writer can hold any row; Joe
   may reassign a row's author for a different mood by editing the Author cell.
   Nothing keys off "the Dawn table" / "the Kenji table" anymore.
3. **Trend determination follows the row's author.** `agents/trend_scout.py`
   reads the Author column, loads that writer's persona file from
   `articles/personas/<slugified-name>.md` (generic AIMA beat if none exists),
   and picks the topic for that writer — it is NOT hardcoded to Dawn/Kenji.
4. **Numbering scheme** (mirrors the insights dashboard convention already in
   `src/app/api/article-data/route.ts:buildCalendar`, adopted per Joe:
   "article numbers should not be tied to joselito… I should be able to find
   the articles in sequential order"):
   - Published rows keep their real `article:id` — this resolved the three
     known desyncs: row 14 is now Dawn's "Your AI Ethics Board Is a Press
     Release" (real #014), "Machines That Compose" renumbered 14→15 (real
     #015), and #017 "The Résumé Filter" got its missing calendar row.
   - Unpublished rows are numbered 19–64 in date order across ALL authors
     (same-date rows ordered by scheduled post time where noted).
5. **TBD placeholder is author-agnostic:** rows read `TBD — Trending Topic`;
   the Author column says who writes it once the topic is determined.

**Old slot → new canonical number mapping:**

| Old | New | | Old | New | | Old | New |
|-----|-----|-|-----|-----|-|-----|-----|
| D1 | 14 (published #014) | | K1 | 23 | | old 14 | 15 |
| D2 | 25 | | K2 | 26 | | old 15 | 24 |
| D3 | 28 | | K3 | 29 | | old 17 | 27 |
| D4 | 31 | | K4 | 20 | | old 19 | 30 |
| D5 | 22 | | K5 | 37 | | old 20 | 19 |
| D6 | 41 | | K6 | 32 | | old 22 | 34 |
| D7 | 35 | | K7 | 39 | | old 23 | 38 |
| D8 | 43 | | K8 | 45 | | old 24 | 42 |
| D9 | 47 | | K9 | 49 | | old 25 | 33 |
| D10 | 51 | | K10 | 53 | | old 26 | 36 |
| D11 | 55 | | K11 | 57 | | old 27 | 40 |
| D12 | 59 | | K12 | 61 | | old 28 | 44 |
| D13 | 63 | | | | | old 29 | 46 |

(Joselito rows 30–38 shifted to 48/50/52/54/56/58/60/62/64 respectively;
rows 1–13, 16, 18, 21 unchanged; row 17 "The Résumé Filter" newly added.)

**Code touched:** `agents/trend_scout.py` (author-driven persona resolution,
persist by row number), `run_research_batch.py` + `run_writer_batch.py`
(unified parser, `--article N` targeting), `run_maya_batch.py` (skip TBD rows
— no cover art for placeholders), `run_priya_batch.py` (author from column),
`agents/prompts.py` (Priya resolves author from the Author column),
insights `src/app/api/article-data/route.ts` (unified parse) and
`ArticleManagerDashboard.tsx:buildCalendarMd` (unified export, preserves
canonical numbers).

**Consequence to know:** `next_article_number` (19) now walks the true
date-ordered sequence — next up is #19 "The Persuasion Engine" (2026-07-02),
and TBD trending rows enter the default research/writer batch walk (Trend
Scout fires automatically when one is next in line).

---

## 2026-07-02 — Overdue backlog reschedule (recorded retroactively)

9 overdue rows rescheduled to 07/06–07/10 at 2/day; 5 already-queued rows
bumped to 07/13–07/17ff to preserve the 2/day cap. (This entry predates this
file; the calendar header referenced it — before/after detail is in the git
history of `articles/aima-editorial-calendar.md`.)
