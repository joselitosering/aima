# AIMA LinkedIn Pipeline — Modification Plan
**Date:** 2026-06-26  
**Scope:** Post-audit findings and prioritized fixes for the LinkedIn posting + analytics workflow

---

## Workflow Verification

### ✅ What Works

| Step | Status | Evidence |
|------|--------|---------|
| Post to company page (`urn:li:organization:111540594`) | ✅ WORKING | 14 posts confirmed on org page via `/rest/posts?q=author` |
| Author credit in commentary byline | ✅ WORKING | Byline in post_log entries: "Joselito Sering · Editor-in-Chief, AIMA" / "Dawn Ginhaua · Cultural Critic & Educator, AIMA" |
| Personal reshare via `reshareContext.parent` | ✅ WORKING | `reshare_id` logged in post_log for 5 entries (articles posted after fix was added) |
| Cover image upload + asset URN | ✅ WORKING | All recent posts use IMAGE mode with `urn:li:image:` assets |
| Persona-aware commentary on reshare | ✅ WORKING | `build_personal_commentary()` dispatches by persona key |

### ❌ What Does Not Work

| Issue | Root Cause | Impact |
|-------|-----------|--------|
| Per-post engagement stats | `r_member_social` permanently closed (LinkedIn FAQ + SO confirmed); stats endpoint returns aggregate only | `analytics_collected` stays `false` for all 23 entries |
| Correct share URN resolution | Race condition in `_resolve_share_urn()` | 2+ entries in post_log have wrong `post_id` (wrong article's URN) |
| Duplicate post prevention | No dedup check before posting | 3 articles posted 2–3× each (9 duplicate entries in post_log) |
| Token budget tracking | `cora.init_budget()` writes zeros; nothing writes actual usage back | Dashboard shows all zeros |
| Personal reshare for old posts | Reshare was added mid-pipeline; earlier 18 entries lack `reshare_id` | No personal profile visibility for most content |

---

## LinkedIn API Reality Check

Tested 2026-06-26 with `r_organization_social` token:

| Endpoint | Result |
|----------|--------|
| `GET /rest/posts?q=author&author=org_urn` | ✅ Returns 14 org posts — content/metadata only, **no engagement data** |
| `GET /v2/organizationalEntityShareStatistics` | Returns 1 element (aggregate org totals): 533 impressions, 41 clicks, 5 likes, 7 shares |
| `GET /rest/socialMetrics?entityUrn=...` | HTTP 404 |
| `r_member_social` scope | Permanently closed — LinkedIn not accepting applications per official FAQ |

**Conclusion:** Per-post engagement stats require either the LinkedIn Marketing Developer Platform (separate application) or manual export from LinkedIn Analytics (Creator Studio → Post analytics → Export CSV).

---

## Bug Details

### Bug 1: `_resolve_share_urn` Race Condition (Critical)

**File:** `linkedin_poster.py` lines ~350–375

**Current behavior:**
```python
def _resolve_share_urn(ugc_id):
    time.sleep(2)
    # Queries most-recently-modified org post — WRONG if any other post was recently touched
    url = f"...?q=author&author={org_urn}&count=3&sortBy=LAST_MODIFIED"
    return elements[0].get("id")   # grabs first result, not the post we just created
```

**Evidence of breakage:**
- post_log `7461827804377260032` (05-16, Future of Media) ≠ org page `7461826263243169792` at same timestamp — two different posts
- post_log `7460154618765828097` (05-12, AI Medicine) ≠ org page `7460153271274405888` at same timestamp
- Both were during a period when multiple posts existed on the org page near the same time

**What this means:** For those entries, `reshare_to_personal()` reshared the WRONG article's URN. The personal reshare points to a different post than intended.

### Bug 2: No Duplicate Post Guard

**File:** `pipeline.py`

Multiple articles were posted more than once:
- n8n pipeline: entries at 2026-06-19T20:30:02 AND 2026-06-19T20:30:33 (same article, 31 sec apart)
- $5K Music Video: entries at 2026-06-19T19:30:02 AND 2026-06-19T19:30:31
- Ethics Theater (dawn): posted as 3 separate entries at 20:13, 20:22, and 20:27

The org page shows only the latest URN for each article. Earlier duplicates were likely overwritten or the reshare pointed to the wrong one.

### Bug 3: `ugc_id` Discarded After Posting

**File:** `linkedin_poster.py` `post_to_linkedin()`

```python
ugc_id    = result.get("id", "")    # e.g. urn:li:ugcPost:7474564350000000000
share_urn = _resolve_share_urn(ugc_id)
return share_urn or ugc_id          # ugc_id is never stored anywhere
```

The `ugcPost` URN (direct API response) is discarded. Only the resolved `share` URN is returned and logged. If resolution is wrong, there is no fallback reference.

---

## Modification Plan

### Fix 1 — `_resolve_share_urn`: Direct Lookup (Priority: CRITICAL)

**Why:** Eliminates the race condition permanently. Instead of fetching "most recent post," look up the exact post by its ugcPost URN.

**Replace in `linkedin_poster.py`:**

```python
def _resolve_share_urn(ugc_id):
    """
    Direct lookup of the ugcPost by ID via GET /rest/posts/{encoded_urn}.
    No race condition — we look up exactly the post we just created.
    Falls back to ugc_id if the REST endpoint is unavailable.
    """
    import time, urllib.parse
    time.sleep(2)   # allow LinkedIn to index the post
    encoded = urllib.parse.quote(ugc_id, safe="")
    url = f"https://api.linkedin.com/rest/posts/{encoded}"
    req = urllib.request.Request(url)
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("LinkedIn-Version",          "202506")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data      = json.loads(resp.read())
            share_urn = data.get("id", ugc_id)
            print(f"  Resolved share URN: {share_urn}")
            return share_urn
    except Exception as e:
        print(f"  Warning: could not resolve share URN ({e}) — using ugcPost URN")
        return ugc_id
```

**Also update `post_to_linkedin()` to return both:**
```python
# Return tuple so pipeline.py can store both
return share_urn, ugc_id    # (resolved share URN, original ugcPost URN)
```

---

### Fix 2 — Store `ugc_id` in post_log.json (Priority: CRITICAL)

**File:** `pipeline.py` — update `log_post()` and the call site.

```python
# pipeline.py — updated log_post signature
def log_post(post_id, reshare_id=None, ugc_id=None, article=None, title=None, persona=None):
    entry = {
        "ugc_id":              ugc_id,   # NEW: raw ugcPost URN from POST response
        "post_id":             post_id,  # resolved share URN (or ugcPost if resolution failed)
        "article":             article,
        "title":               title,
        "persona":             persona,
        "posted_at":           datetime.utcnow().isoformat(),
        "analytics_collected": False,
    }
    ...
```

**Call site update:**
```python
share_urn, ugc_id = post_to_linkedin(article)
reshare_id = reshare_to_personal(share_urn, ...)
log_post(post_id=share_urn, reshare_id=reshare_id, ugc_id=ugc_id, ...)
```

---

### Fix 3 — Duplicate Post Guard (Priority: HIGH)

**File:** `pipeline.py` — add before posting.

```python
def _already_posted(article_name, log_path="linkedin_pipeline/post_log.json"):
    """True if this article filename is already in post_log."""
    try:
        with open(log_path) as f:
            log = json.load(f)
        return any(e.get("article") == article_name for e in log)
    except Exception:
        return False

# In the posting flow:
if _already_posted(article["name"]):
    print(f"  SKIP: {article['name']} already in post_log — use --force to re-post")
    return
```

Add `--force` flag to bypass guard for intentional reposts.

---

### Fix 4 — `analytics_collector.py`: Pivot to Verification + Aggregate (Priority: HIGH)

Per-post engagement stats are not available via API. Pivot the collector to do what IS possible:

```python
def collect_pending_analytics():
    """
    1. Fetch all org post URNs to verify post presence on the company page.
    2. Update org aggregate stats (org_stats.json).
    3. Mark unverifiable entries with informative note.
    Per-post stats require manual LinkedIn Analytics export → xls_import.py.
    """
    log       = _load_post_log()
    org_posts = _fetch_org_post_ids()   # set of URNs from /rest/posts
    changed   = False

    for entry in log:
        post_id  = entry.get("post_id", "")
        ugc_id   = entry.get("ugc_id", "")
        on_page  = post_id in org_posts or ugc_id in org_posts

        entry["verified_on_org_page"] = on_page
        if not entry.get("analytics_collected"):
            entry["analytics_note"] = (
                "Per-post stats not available via API. "
                "Export from LinkedIn Creator Studio → Analytics → Post analytics."
            )
        changed = True

    # Always refresh org aggregate
    _save_org_aggregate_stats()

    if changed:
        _save_post_log(log)
        print("  Verification complete. Updated post_log.json with org-page status.")
```

Add `_fetch_org_post_ids()` helper:
```python
def _fetch_org_post_ids():
    """Return set of all share/ugcPost URNs on the org page."""
    # paginate /rest/posts?q=author with count=50 until paging.total exhausted
    ...
    return {el["id"] for el in all_elements}
```

---

### Fix 5 — XLS Import: Map LinkedIn Export to post_log (Priority: MEDIUM)

LinkedIn CSV export (Creator Studio → Analytics → Post analytics) columns:
- `Post title`, `Post date`, `Impressions`, `Unique impressions`, `Clicks`, `Likes`, `Comments`, `Shares`, `Engagement rate`

**`xls_import.py` update — matching strategy:**

1. Primary match: post_log `posted_at` date == export `Post date` (YYYY-MM-DD)
2. Secondary match: post_log `title` fuzzy-match against export `Post title`
3. Update matched entry with `impressions`, `clicks`, `likes`, `comments`, `shares`, `engagement_rate`, `analytics_collected: true`

```python
def import_linkedin_export(csv_path, log_path="linkedin_pipeline/post_log.json"):
    import csv
    from datetime import datetime
    
    log = _load_post_log(log_path)
    
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    
    matched = 0
    for row in rows:
        export_date  = row.get("Post date", "")[:10]   # "2026-06-21"
        export_title = row.get("Post title", "").lower().strip()
        
        for entry in log:
            log_date  = entry.get("posted_at", "")[:10]
            log_title = entry.get("title", "").lower().strip()
            
            if log_date == export_date or (export_title and export_title in log_title):
                entry["impressions"]       = int(row.get("Impressions", 0) or 0)
                entry["unique_impressions"]= int(row.get("Unique impressions", 0) or 0)
                entry["clicks"]            = int(row.get("Clicks", 0) or 0)
                entry["likes"]             = int(row.get("Likes", 0) or 0)
                entry["comments"]          = int(row.get("Comments", 0) or 0)
                entry["shares"]            = int(row.get("Shares", 0) or 0)
                entry["engagement_rate"]   = float(row.get("Engagement rate", 0) or 0)
                entry["analytics_collected"]   = True
                entry["analytics_source"]      = "linkedin_export"
                entry["analytics_imported_at"] = datetime.utcnow().isoformat()
                matched += 1
                break
    
    _save_post_log(log, log_path)
    print(f"  Imported analytics for {matched}/{len(rows)} posts.")
```

---

### Fix 6 — Token Budget Write-Back (Priority: MEDIUM)

**File:** `agents/marco.py` — call `estimate_tokens.py` after all agents complete.

```python
# At end of marco.py run(), after all agent calls:
import subprocess, sys
result = subprocess.run(
    [sys.executable, "estimate_tokens.py", str(spec["number"])],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("  Token estimates written to token_budget.json")
else:
    print(f"  Token estimate failed: {result.stderr}")
```

Update `estimate_tokens.py` to accept article number as CLI arg:
```python
if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    run(n)
```

---

### Fix 7 — Dashboard: Show Org Aggregate Stats (Priority: LOW)

**File:** `insights` Next.js app — expose `org_stats.json` via API route.

Create `src/app/api/linkedin-stats/route.ts`:
```typescript
import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  const p = path.join(process.cwd(), "../aima/linkedin_pipeline/org_stats.json");
  try {
    const data = JSON.parse(fs.readFileSync(p, "utf8"));
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ error: "org_stats.json not found" }, { status: 404 });
  }
}
```

Display on dashboard: aggregate impressions (533), clicks (41), engagement rate (9.94%) alongside per-post table.

---

## Backlog: Fix Wrong URNs in Existing post_log.json

5 entries have suspected wrong `post_id` due to the race condition bug. To correct them:

1. Run `/rest/posts?q=author&author=org_urn&count=20` and get all 14 org post URNs with `createdAt` timestamps
2. For each post_log entry where `post_id` is NOT in the org post set, find the closest `createdAt` match
3. Update `post_id` to the matching org URN and set `post_id_corrected: true`

This is a one-time data repair script. Given that 5 of 14 potentially affected entries also lack `reshare_id`, the reshare itself may need to be redone for those articles.

---

## Implementation Order

| # | Change | File(s) | Effort |
|---|--------|---------|--------|
| 1 | Fix `_resolve_share_urn` direct lookup | `linkedin_poster.py` | 30 min |
| 2 | Return and store `ugc_id` | `linkedin_poster.py`, `pipeline.py` | 30 min |
| 3 | Add duplicate post guard | `pipeline.py` | 15 min |
| 4 | Pivot `analytics_collector.py` to verification mode | `analytics_collector.py` | 45 min |
| 5 | Update `xls_import.py` with CSV mapping | `xls_import.py` | 1 hr |
| 6 | Wire `estimate_tokens.py` into marco.py | `agents/marco.py`, `estimate_tokens.py` | 20 min |
| 7 | Add `/api/linkedin-stats` route to insights | `insights/src/app/api/linkedin-stats/route.ts` | 30 min |
| 8 | One-time post_log URN correction script | new `scripts/repair_post_log.py` | 1 hr |

**Total estimated:** ~5 hrs for all 8 items.

---

## Not Fixable Without LinkedIn API Tier Upgrade

- **Per-post impressions/clicks/likes via API** → requires Marketing Developer Platform access
- **Personal reshare engagement stats** → requires `r_member_social` (currently closed)
- **Historical post stats (posts before 2026-04)** → not in any accessible endpoint

To apply for Marketing Developer Platform: https://www.linkedin.com/developers/apps → your app → Products → Request "Marketing Developer Platform"
