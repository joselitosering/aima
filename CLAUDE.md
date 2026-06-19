# AIMA Project Memory

## Pending Actions

### LinkedIn Marketing API — Development Tier Approval
- **Status:** Application submitted June 19, 2026
- **Check by:** June 24, 2026 (mid-week)
- **Reminder scheduled:** Cowork task `linkedin-api-approval-check` fires Wed June 24 at 9 AM PDT
- **On approval:**
  1. Edit `linkedin_pipeline/linkedin_auth.py` → change `SCOPES` to include `r_member_social`:
     ```
     SCOPES = "openid profile email w_member_social r_member_social"
     ```
  2. Re-run `python linkedin_pipeline/linkedin_auth.py` to refresh the token
  3. Update `analytics_collector.py` → replace deprecated `v2/shareStatistics` endpoint with current LinkedIn REST API format (`/rest/socialMediaPostStatistics`)
  4. Test analytics collection: `python linkedin_pipeline/analytics_collector.py`

---

## LinkedIn Pipeline — Current State (as of June 19, 2026)

- **Posting:** Working. Uses `w_member_social` scope via UGC Posts API with direct image upload.
- **Analytics:** Blocked — LinkedIn `shareStatistics` API deprecated + missing `r_member_social` scope.
- **Backfill posts scheduled today:**
  - 12:30 PM — Article 002 ($5K Music Video Blueprint)
  - 1:30 PM  — Article 003 (n8n Content Pipeline)
  - 2:30 PM  — Article 007 (Rogue AI Agents)
  - 3:30 PM  — Article 012 (Algorithm of Atrocity)
- **Already posted:** Article 001 (Future of Creative Production) — `urn:li:share:7473803142543863808`

---

## AIMA Article Pipeline — Current State

- **Next article:** #014 — "Hallucination Nation: Why AI Lies with Confidence and What It Costs Us"
- **Scheduled:** June 20, 2026 at 6 AM (Cowork task: `aima-article-coworker`)
- **Track:** Joselito Sering (editorial calendar, index 1)
- **State file:** `articles/aima-coworker-state.json`
