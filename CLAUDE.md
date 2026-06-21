# AIMA Project Memory

## Pending Actions

### LinkedIn Marketing API — Development Tier Approval
- **Status:** APPROVED June 20, 2026 (Advertising API, app id 253440006)
- **SCOPES updated:** `r_member_social` added to `linkedin_pipeline/linkedin_auth.py`
- **NEXT STEP:** Run `python linkedin_pipeline/linkedin_auth.py` to get a new token with `r_member_social`
- Then test: `python linkedin_pipeline/analytics_collector.py`
- **analytics_collector.py is ready** — already uses `/rest/socialMediaPostStatistics`, no code changes needed after token refresh

---

## LinkedIn Pipeline — Current State (as of June 21, 2026)

### APPROVED POST-PUBLISH WORKFLOW
After every article is written, pushed, and live on GitHub Pages:
1. `git push` — publishes article to `joselitosering.github.io/aima`
2. `python linkedin_pipeline/pipeline.py` — runs the full sequence automatically:
   - Posts to **AIMA company page** with cover image + article hook + hashtags + **persona byline** (name credit)
   - Immediately **reshares to Joselito's personal profile** with persona-tailored intro + **TL;DR** + CTA
   - Logs post IDs to `post_log.json` for 48h analytics collection
   - Google Sheets logging is also triggered inside the pipeline (Step 8 can be skipped manually if pipeline runs)

This workflow was tested and approved June 21, 2026.

### Technical State
- **Company page posting:** Working. `linkedin_poster.py` posts as `urn:li:organization:{ORG_ID}` with direct image upload via Assets API. Byline appears at end of commentary.
- **Personal reshare:** Working. `reshare_to_personal()` uses `/rest/posts` with `reshareContext`. Commentary built by `build_personal_commentary()` — persona-aware hook + TL;DR + CTA.
- **Scopes required:** `w_organization_social` (company page) + `w_member_social` (personal reshare)
- **Analytics:** Approved for `r_member_social` June 20, 2026. Needs token refresh: `python linkedin_pipeline/linkedin_auth.py`. Then test: `python linkedin_pipeline/analytics_collector.py`
- **Analytics fallback:** `xls_import.py` to import from LinkedIn Analytics XLS export until token refreshed.

---

## article-manager.html Dashboard — Current State (as of June 20, 2026)

- **GA4 auto-load:** `ga4_traffic.csv` fetched on load via `autoLoadGA4()` — no manual upload needed
- **Analytics page:** Two-pane layout — Content Analytics (left) · Site Traffic (right)
- **Performance page:** Flat row grid — each row aligns left/right independently
  - Row 1: titles
  - Row 2: persona cards | Site Conversion + Tracking Pixels
  - Row 3: Top 5 Posts | Best Click-Through Posts
  - Row 4: Best Performing Categories | What Drives Reactions & Reposts
- **Overview page:** 8 KPI cards in `card-grid-8` (4-2-1 responsive)
  - Row 1: Total Posts · Avg Impressions · LI Profile Traffic · Company Page Reach
  - Row 2: Avg CTR · Articles Remaining · Top Writer · Top Category
- **Security:** `aima-analytics-92f4d1344f7a.json` removed from git history — keep in `.gitignore`
- **Manual Entry section:** Removed from Analytics right pane

---

## AIMA Article Pipeline — Current State

- **Last article written:** #016 — "The Digital Nomad Economy: How Developing Nations Are Reshaping Global AI Labor" (June 21, 2026)
- **Next article:** #017 — Track: trending — Author: Dawn Ginhaua
- **Scheduled:** Daily via Cowork task `aima-article-coworker`
- **State file:** `articles/aima-coworker-state.json`
- **Note:** Article #014 (Hallucination Nation) was skipped in sequence — write it before publishing article #016 if strict numbering matters.
