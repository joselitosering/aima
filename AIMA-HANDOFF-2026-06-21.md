# AIMA PROJECT — SESSION HANDOFF
**Date:** 2026-06-21  
**Prepared by:** Claude (Cowork session ending)  
**For:** Next Claude session — continue without re-deriving context

---

## CRITICAL: SOURCE OF TRUTH

**THE CALENDAR IS `article-manager.html` → `const CALENDAR = [...]`**  
This is the only source of truth for article parameters. When Joe edits title, tone,
category, persona, or date in the dashboard, those values are what the coworker must use.
The coworker prompt currently reads from a GitHub raw markdown URL — that is WRONG and
must be fixed. See OPEN ISSUES below.

---

## REPO STRUCTURE

```
D:\Apps\DevOps\Github\aima\
  article-manager.html          ← dashboard + CALENDAR source of truth
  articles/
    aima-article-skeleton.html  ← template for new articles
    aima-coworker-state.json    ← pipeline state file
    aima-coworker-prompt.md     ← instructions read by scheduled task
    aima-editorial-calendar.md  ← STALE — not the source of truth
    personas/
      dawn-ginhaua.md
      kenji-nakamoto.md
    aima-article-*-NNN.html     ← published articles (15 exist, see below)
  linkedin_pipeline/
    pipeline.py
    post_log.json               ← WARNING: currently has JSON parse error (unterminated string at char 5528)
    post_analytics.csv
    ga4_traffic.csv
    linkedin_auth.py            ← has r_member_social scope added
    analytics_collector.py
  img/
    author-joselito.png         ← fixed this session (was .PNG uppercase)
    author-dawn.png
    author-kenji.png
```

Live site: **https://aima.productions/articles/**

---

## THE THREE-TRACK PUBLISHING SCHEDULE

| Track | Author | Cadence |
|-------|--------|---------|
| A | Joselito Sering | Every 2 days (even calendar days) |
| B | Dawn Ginhaua | Every 2 days (odd days, alternating w/ Kenji) |
| C | Kenji Nakamoto | Every 2 days (odd days, alternating w/ Dawn) |

Together = one article per day.

### CALENDAR data vs. display vs. filenames

**Internal `item.num` field** — identifiers in the CALENDAR array data only:
- Joselito entries: numeric (1, 2, 3 … 38)
- Dawn entries: 'D1', 'D2' … 'D13' (internal only, never displayed)
- Kenji entries: 'K1', 'K2' … 'K12' (internal only, never displayed)

**Dashboard display** — uses `seqIdMap` (line 1770 in article-manager.html):
```js
const seqIdMap = new Map(sorted.map((item, i) => [item, String(i+1).padStart(3,'0')]));
```
All entries sorted by date, numbered 001, 002, 003... sequentially.
D1/K1 labels are NOT shown anywhere in the UI.

**Article filenames** — all authors use the same canonical format:
`aima-article-[slug]-[NNN].html`
NNN comes from `next_article_number` in aima-coworker-state.json,
increments for every article regardless of author.
`aima-article-ethics-theater-014.html` = Dawn's article, correctly numbered 014.

---

## ARTICLES — CURRENT STATUS

### Published (15 articles on disk)
| File | CALENDAR num | Persona | Published |
|------|-------------|---------|-----------|
| future-of-creative-production-001.html | 1 | joselito | ✓ |
| 5k-music-video-blueprint-002.html | 2 | joselito | ✓ |
| n8n-content-pipeline-003.html | 3 | joselito | ✓ |
| boycott-or-bigotry-004.html | 4 | joselito | ✓ |
| ai-workforce-005.html | 5 | joselito | ✓ |
| ethics-and-ai-006.html | 6 | joselito | ✓ |
| rogue-ai-agents-007.html | 7 | joselito | ✓ |
| ai-in-medicine-008.html | 8 | joselito | ✓ |
| future-of-media-009.html | 9 | joselito | ✓ |
| anthropomorphization-trap-010.html | 10 | joselito | ✓ |
| token-bill-011.html | 11 | joselito | ✓ |
| algorithm-of-atrocity-012.html | 12 | joselito | ✓ |
| global-south-ai-gap-013.html | 13 | joselito | ✓ |
| ethics-theater-014.html | (internal: 'D1', display seq by date) | dawn | ✓ |
| machines-that-compose-015.html | 15 | joselito | ✓ |

### Naming convention — all articles, all authors
**All articles use the same canonical format regardless of author:**
`aima-article-[slug]-[zero-padded-number].html`

The number comes from `next_article_number` in aima-coworker-state.json and increments
sequentially for every article — Joselito, Dawn, and Kenji alike.

`aima-article-ethics-theater-014.html` is correctly named. It is Dawn's article (CALENDAR
internal label D1) and received sequential number 014. The CALENDAR identifiers D1–D13
and K1–K12 are dashboard display labels only — they are NOT filenames.

CALENDAR num:14 field = "Hallucination Nation" (Joselito) — this article has NOT been
written yet. The syncPublished() match on numeric suffix `014` will incorrectly mark
CALENDAR num:14 as published. This still needs to be fixed in syncPublished() —
it should match against a slug or the article's own metadata, not just the numeric suffix.

### Not yet written
- **num:14** — "Hallucination Nation: Why AI Lies with Confidence and What It Costs Us" (Joselito)
- **K1** — TBD Trending Topic / Kenji — was scheduled for TODAY (2026-06-21) but no task exists
- **D2, K2, D3...** — all future trending articles (TBD titles)
- **num:16** — "The Digital Nomad Economy..." — next Joselito article, date 2026-06-24

---

## SCHEDULED TASKS — CURRENT STATE

Only ONE task exists:

```
taskId:        aima-article-coworker
cron:          0 6 2/2 * *  (06:00 AM, even days of month only)
last ran:      2026-06-20 06:06 AM
next run:      2026-06-22 06:06 AM
enabled:       true
```

**MISSING:** No scheduled task for Dawn/Kenji on odd days.
K1 was supposed to run today (June 21) — it didn't because the task doesn't exist.
The next gap will be June 23 (D2), June 25 (K2), etc.

**What needs to be created:**
A second scheduled task running on odd days (`0 6 1/2 * *`) using the same
aima-coworker-prompt.md — which already contains Track B logic reading `next_track`
from state.json. When Joselito runs, it flips next_track to "trending". The odd-day
task picks that up and runs Dawn or Kenji.

---

## aima-coworker-state.json — CURRENT VALUES

```json
{
  "next_article_number": 16,
  "next_track": "joselito",
  "next_article_date": "2026-06-24",
  "joselito": {
    "next_calendar_index": 3,
    "post_count": 15,
    "last_topic": "Machines That Compose..."
  },
  "trending": {
    "next_persona": "dawn",
    "dawn": { "post_count": 0, "last_topic": null },
    "kenji": { "post_count": 0, "last_topic": null }
  },
  "last_run": "2026-06-20"
}
```

Issues to fix:
- `next_track` says "joselito" but K1 (Kenji) was today. When the missing task is
  created it needs to fire with next_track="trending" first.
- `next_article_date` says 2026-06-24 but the cron fires 2026-06-22. These are out of sync.
- Dawn's post_count=0 even though D1 "Ethics Theater" is published. Needs +1.

---

## OPEN ISSUES (do not ignore)

### 1. Coworker prompt reads wrong calendar source
`aima-coworker-prompt.md` Step A1 says:
> Fetch `https://raw.githubusercontent.com/.../aima-editorial-calendar.md`

Joe's instruction: **the CALENDAR in article-manager.html is the single source of truth.**
Parameters set there (title, tone, category, read time, persona) are the guardrails for
the generated article. The prompt must be updated to read from article-manager.html
instead of the GitHub raw markdown file.

Fix: Either (a) export CALENDAR as a JSON file that the coworker reads, or (b) update
the prompt to read and parse the CALENDAR array directly from article-manager.html.

### 2. Missing Dawn/Kenji scheduled task
Create: `aima-article-trending-coworker` with cron `0 6 1/2 * *`
Same SKILL.md pattern as aima-article-coworker (reads aima-coworker-prompt.md).
The prompt already handles Track B — just needs the task to fire it.

### 3. post_log.json has a JSON parse error
`/aima/linkedin_pipeline/post_log.json` — unterminated string at char 5528.
File needs to be repaired before syncPublished() or analytics will fail silently.

### 4. syncPublished() false match on num:14
`ethics-theater-014.html` is Dawn's article correctly numbered 014.
CALENDAR num:14 is Joselito's "Hallucination Nation" (not yet written).
syncPublished() extracts `14` from the filename and marks CALENDAR num:14 published — wrong.
Fix syncPublished() to look up by article slug or metadata rather than numeric suffix alone,
OR store the CALENDAR num (which may be non-numeric like 'D1') in post_log.json so the
match is unambiguous.

### 5. aima-coworker-state.json is stale
`next_article_date: "2026-06-24"` conflicts with cron firing June 22.
Dawn post_count should be 1 (D1 published).
next_track should probably be "trending" so K1 runs next (but task doesn't exist yet).

---

## WHAT WAS FIXED IN THE PREVIOUS SESSION(S)

- Articles 006, 007, 009, 010, 012, 014 — restored from git after sed truncation
- Article 013 — repaired missing tail (was truncated in git)
- All 15 articles — patched with GAS-driven applyNav() nav block
- All 15 articles — AUTHOR PHOTO block with persona-driven photo + BMAC color
- article-manager.html — syncPublished() from post_log.json (not localStorage)
- article-manager.html — removed published field from restoreCalendar()
- img/author-joselito.png — fixed case (was .PNG, case-sensitive on GitHub Pages)
- LinkedIn API — r_member_social scope added, Development Tier approved 2026-06-20
- Diagrams created: aima-pipeline-diagram.html, aima-pipeline-blueprint.html
- Workflow prompt doc: aima-pipeline-workflow-prompt.md

---

## GUARDRAILS — DO NOT VIOLATE

1. **Never use `sed -i` on article HTML files** — causes UTF-8 truncation on mounted FS.
   Always use Python with `encoding='utf-8', newline=''`.
2. **Never run `git push`** — Joe does all git pushes manually from PowerShell.
3. **Never post to LinkedIn without explicit user instruction.**
4. **Never change files unless asked.** Do not propagate fixes across files without approval.
5. **aima-analytics-92f4d1344f7a.json** is in .gitignore — never commit it.
6. **Source of truth for article parameters = CALENDAR in article-manager.html**, not
   aima-editorial-calendar.md and not aima-coworker-state.json.

---

## NEXT ACTIONS (in priority order)

1. Fix post_log.json parse error
2. Decide on article 014/D1 filename conflict
3. Update aima-coworker-prompt.md to read CALENDAR from article-manager.html
4. Create aima-article-trending-coworker scheduled task (odd days, 06:00)
5. Correct aima-coworker-state.json (dawn post_count, next_article_date)
6. Write K1 — Kenji's first trending article (was due today June 21)
7. Write num:14 — "Hallucination Nation" (Joselito, skipped)
