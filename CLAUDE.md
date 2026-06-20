# AIMA Project Memory

## Pending Actions

### LinkedIn Marketing API — Development Tier Approval
- **Status:** APPROVED June 20, 2026 (Advertising API, app id 253440006)
- **SCOPES updated:** `r_member_social` added to `linkedin_pipeline/linkedin_auth.py`
- **NEXT STEP:** Run `python linkedin_pipeline/linkedin_auth.py` to get a new token with `r_member_social`
- Then test: `python linkedin_pipeline/analytics_collector.py`
- **analytics_collector.py is ready** — already uses `/rest/socialMediaPostStatistics`, no code changes needed after token refresh

---

## LinkedIn Pipeline — Current State (as of June 19, 2026)

- **Posting:** Working. Uses `w_member_social` scope via UGC Posts API with direct image upload.
- **Analytics:** API path exhausted — `organizationalEntityShareStatistics` only returns org-level aggregate (1 element); `shares[0]` filter returns 400 (unsupported); `r_member_social` not included in Advertising API approval. **Use `xls_import.py`** to import from LinkedIn Analytics XLS export. Apply for Marketing Developer Platform separately to get `r_member_social`.
- **Backfill posts scheduled today:**
  - 12:30 PM — Article 002 ($5K Music Video Blueprint)
  - 1:30 PM  — Article 003 (n8n Content Pipeline)
  - 2:30 PM  — Article 007 (Rogue AI Agents)
  - 3:30 PM  — Article 012 (Algorithm of Atrocity)
- **Already posted:** Article 001 (Future of Creative Production) — `urn:li:share:7473803142543863808`

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

- **Next article:** #014 — "Hallucination Nation: Why AI Lies with Confidence and What It Costs Us"
- **Scheduled:** June 20, 2026 at 6 AM (Cowork task: `aima-article-coworker`)
- **Track:** Joselito Sering (editorial calendar, index 1)
- **State file:** `articles/aima-coworker-state.json`
