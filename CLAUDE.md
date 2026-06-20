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

## AIMA Article Pipeline — Current State

- **Next article:** #014 — "Hallucination Nation: Why AI Lies with Confidence and What It Costs Us"
- **Scheduled:** June 20, 2026 at 6 AM (Cowork task: `aima-article-coworker`)
- **Track:** Joselito Sering (editorial calendar, index 1)
- **State file:** `articles/aima-coworker-state.json`
