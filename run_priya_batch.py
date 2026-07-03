"""run_priya_batch.py — Priya batch: editorial-calendar audit & reconciliation.

Priya is the calendar manager. This solo batch cross-checks the editorial calendar
against every downstream source of truth and REPORTS all bugs. It is read-only and
costs no tokens — it does not edit the calendar/state (those reconciliations need an
Iris/Joe decision); it writes a structured report to optimization/priya_audit.json.

What she checks (and the files she reads):
  - Sequencing : aima-editorial-calendar.md vs articles/aima-article-*-NNN.html
  - Status     : research/ (Scout) · *.html (Quill) · img/articles + handoff/ready (Maya)
                 · posted_articles.json (Porter) · post_log.json (Nova) · post_analytics.csv (Echo)
  - Dates      : chronology + past-due upcoming articles
  - Authors    : calendar section vs state.articles_written vs post_log persona
  - Categories : presence
  - Tags       : category -> Scout source tags (agents.scout._CATEGORY_TAG_MAP)
  - Analytics  : post_log analytics_collected=false & 48h+ old -> Echo overdue
  - Readiness  : next 3 upcoming articles ready for Scout / Quill / Maya?

Usage: python run_priya_batch.py
"""

import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# Force UTF-8 on stdout/stderr so calendar titles (em-dashes, accents) and the
# report stream cleanly to the dashboard instead of mojibake. Must run before
# agents.base configures logging on stderr.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.base import REPO_ROOT, log
from agents.scout import _CATEGORY_TAG_MAP

LP = REPO_ROOT / "linkedin_pipeline"
KNOWN_AUTHORS = {"joselito sering", "dawn ginhaua", "kenji nakamoto"}
UPCOMING_READINESS = 3

bugs: list[dict] = []


def _bug(category: str, severity: str, ref: str, message: str, autofixable: bool = False):
    bugs.append({"category": category, "severity": severity, "ref": ref,
                 "message": message, "autofixable": autofixable})


def _slugify(text: str, max_parts: int = 6) -> str:
    s = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")
    return "-".join(s.split("-")[:max_parts])


_STOP = {"the", "a", "an", "of", "and", "to", "in", "is", "how", "what", "why",
         "for", "on", "ai", "with", "your", "i", "we", "it", "its"}


def _title_tokens(text: str) -> set:
    """Significant word tokens from a full title (no truncation)."""
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _STOP}


_ART_RE = re.compile(r"aima-article-.*-\d{3}\.html")


def _file_title(fname: str) -> str:
    """Read the article's real title (og:title, else <title>) from its HTML."""
    try:
        html = (REPO_ROOT / "articles" / fname).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    m = (re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
         or re.search(r"<title>([^<]+)</title>", html))
    return m.group(1).strip() if m else ""


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_calendar() -> list[dict]:
    """Parse the unified editorial calendar table (one canonical sequence;
    Author is the last column — a per-row attribute, not a track)."""
    md = (REPO_ROOT / "articles" / "aima-editorial-calendar.md").read_text(encoding="utf-8")
    entries, author = [], "unknown"
    for line in md.splitlines():
        h = re.match(r"^##\s+(.+)", line)
        if h:  # legacy per-author sections — fallback only
            author = re.sub(r"\(.*?\)", "", h.group(1)).strip()
            continue
        m = re.match(r"\s*\|\s*([A-Za-z]?\d+)\s*\|\s*([\d-]+)?\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|", line)
        if not m:
            continue
        key, dt, title, category, read = m.group(1), (m.group(2) or "").strip(), m.group(3).strip(), m.group(4).strip(), m.group(5).strip()
        cells = [c.strip() for c in line.split("|")]
        row_author = cells[7] if len(cells) > 7 and cells[7] else author
        num = int(key) if key.isdigit() else None
        entries.append({
            "key": key, "number": num, "author": row_author, "date": dt,
            "title": title, "category": category, "read": read,
            "is_tbd": title.upper().startswith("TBD"),
        })
    return entries


def load_disk_articles() -> dict:
    """{number: filename} for articles/aima-article-*-NNN.html on disk."""
    out = {}
    for p in (REPO_ROOT / "articles").glob("aima-article-*.html"):
        m = re.match(r"aima-article-(.+)-(\d{3})\.html", p.name)
        if m:
            out[int(m.group(2))] = p.name
    return out


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_analytics_articles() -> set:
    out = set()
    f = LP / "post_analytics.csv"
    if not f.exists():
        return out
    with open(f, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("article"):
                out.add(row["article"].strip())
    return out


def _num_of(filename: str):
    m = re.search(r"-(\d{3})\.html$", filename)
    return int(m.group(1)) if m else None


def _days_since(date_str: str):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return (datetime.now() - datetime.strptime(date_str[:19], fmt)).days
        except ValueError:
            continue
    return None


# ── Audit ─────────────────────────────────────────────────────────────────────

def audit():
    cal = load_calendar()
    disk = load_disk_articles()
    state = load_json(REPO_ROOT / "articles" / "aima-coworker-state.json", {})
    posted = load_json(LP / "posted_articles.json", [])
    post_log = load_json(LP / "post_log.json", [])
    analytics_articles = load_analytics_articles()
    has_research = {_num_of(p.name) for p in (REPO_ROOT / "articles" / "research").glob("*-research.json")}
    has_image = set()
    for d in [REPO_ROOT / "img" / "articles", REPO_ROOT / "handoff" / "ready"]:
        for p in d.glob("aima-*.jpg"):
            mm = re.search(r"aima-(\d{3})-", p.name)
            if mm:
                has_image.add(int(mm.group(1)))

    numbered = [e for e in cal if e["number"] is not None]
    cal_by_num = {e["number"]: e for e in numbered}
    log_by_article = {e.get("article"): e for e in post_log}
    state_authors = {a.get("number"): (a.get("author") or "").strip().lower() for a in state.get("articles_written", [])}

    # 1 — SEQUENCING: gaps, dupes, calendar-title vs on-disk-file mismatch
    nums = sorted(cal_by_num)
    seen = set()
    for e in numbered:
        if e["number"] in seen:
            _bug("sequencing", "error", f"#{e['number']:03d}", f"duplicate calendar number for '{e['title'][:40]}'")
        seen.add(e["number"])
    if nums:
        for n in range(min(nums), max(nums) + 1):
            if n not in cal_by_num:
                _bug("sequencing", "warn", f"#{n:03d}", "missing from calendar (number gap)")
    for n, fname in sorted(disk.items()):
        ce = cal_by_num.get(n)
        if not ce:
            _bug("sequencing", "warn", f"#{n:03d}", f"file {fname} on disk has no calendar entry")
            continue
        # Compare against the file's REAL title (og:title), full tokens — avoids
        # false positives from short thematic slugs / long truncated titles.
        file_title = _file_title(fname)
        cal_tok = _title_tokens(ce["title"])
        file_tok = _title_tokens(file_title) if file_title else \
            _title_tokens(re.match(r"aima-article-(.+)-\d{3}\.html", fname).group(1).replace("-", " "))
        if cal_tok and file_tok and not (cal_tok & file_tok):
            _bug("sequencing", "error", f"#{n:03d}",
                 f"title/file desync: calendar '{ce['title'][:38]}' vs file '{(file_title or fname)[:38]}'")

    # 2 — STATUS consistency
    posted_articles = {p for p in posted if _ART_RE.match(p)}
    for p in posted:
        if not _ART_RE.match(p):
            _bug("hygiene", "warn", p,
                 "non-article entry in posted_articles.json (pollutes publish tracker) — safe to remove",
                 autofixable=True)
    for fname in posted_articles:
        n = _num_of(fname)
        if n is not None and n not in disk:
            _bug("status", "error", fname, "marked published but no HTML file on disk")
    for art, e in log_by_article.items():
        if not art or not _ART_RE.match(art):
            continue  # non-article LinkedIn posts (blueprint/diagram) aren't Porter's tracker concern
        if e.get("post_id") and art not in posted_articles:
            _bug("status", "warn", art, "posted to LinkedIn (Nova) but missing from posted_articles.json (Porter)")

    # 3 — DATES: chronology + past-due upcoming
    today = date.today()
    prev = None
    for e in numbered:
        if not e["date"]:
            _bug("dates", "warn", f"#{e['number']:03d}", "missing date")
            continue
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except ValueError:
            _bug("dates", "warn", f"#{e['number']:03d}", f"unparseable date '{e['date']}'")
            continue
        if prev and d < prev[1]:
            _bug("dates", "warn", f"#{e['number']:03d}", f"date {e['date']} is before #{prev[0]:03d} ({prev[1]})")
        prev = (e["number"], d)
        if e["number"] not in disk and d < today:
            _bug("dates", "warn", f"#{e['number']:03d}", f"scheduled {e['date']} is past but not yet written")

    # 4 — AUTHORS
    for e in numbered:
        if e["author"].lower() not in KNOWN_AUTHORS:
            _bug("authors", "warn", f"#{e['number']:03d}", f"unknown author '{e['author']}'")
        sa = state_authors.get(e["number"])
        if sa and sa not in e["author"].lower() and e["author"].lower() not in sa:
            _bug("authors", "warn", f"#{e['number']:03d}", f"author mismatch: calendar '{e['author']}' vs state '{sa}'")

    # 5/6 — CATEGORIES + TAGS
    for e in cal:
        if not e["category"]:
            _bug("categories", "warn", e["key"], "missing category")
            continue
        cat = e["category"].lower()
        if not any(k in cat for k in _CATEGORY_TAG_MAP):
            _bug("tags", "info", e["key"], f"category '{e['category']}' maps to no Scout source tags (generic fallback)")

    # 7 — ANALYTICS (Echo)
    for e in post_log:
        art = e.get("article", "?")
        ds = _days_since(e.get("posted_at", ""))
        if not e.get("analytics_collected") and ds is not None and ds >= 2:
            _bug("analytics", "warn", art, f"analytics not collected, posted {ds}d ago (Echo overdue)")
        if e.get("analytics_collected") and art not in analytics_articles:
            _bug("analytics", "info", art, "flagged collected but no row in post_analytics.csv")

    # 8 — READINESS of next upcoming articles (for Scout/Quill/Maya)
    start = int(state.get("next_article_number", 1))
    readiness = []
    for n in [x for x in nums if x >= start][:UPCOMING_READINESS]:
        e = cal_by_num[n]
        cat_ok = bool(e["category"]) and any(k in e["category"].lower() for k in _CATEGORY_TAG_MAP)
        r = {
            "number": n, "title": e["title"][:60],
            "scout_ready": (n in has_research) or cat_ok,
            "quill_ready": e["author"].lower() in KNOWN_AUTHORS and bool(e["read"]),
            "maya_ready": n in has_image,
        }
        readiness.append(r)
        for agent, ok in [("Scout", r["scout_ready"]), ("Quill", r["quill_ready"]), ("Maya", r["maya_ready"])]:
            if not ok:
                _bug("readiness", "info", f"#{n:03d}", f"not {agent}-ready "
                     + ("(run research batch)" if agent == "Scout" else
                        "(missing author/read-time)" if agent == "Quill" else "(no staged image — run maya batch)"))
    return readiness


def apply_safe_fixes() -> list:
    """Apply ONLY safe, deterministic, reversible fixes that restore calendar
    health. Currently: strip non-article entries from posted_articles.json
    (+ dedupe + sort). Title/number/author desyncs are NOT touched — those need
    an Iris/Joe decision. Returns human-readable descriptions of fixes applied.
    """
    fixes = []
    path = LP / "posted_articles.json"
    posted = load_json(path, [])
    cleaned = sorted({p for p in posted if _ART_RE.match(p)})
    removed = sorted(set(posted) - set(cleaned))
    if removed or cleaned != posted:
        path.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
        if removed:
            fixes.append(f"posted_articles.json: removed {len(removed)} non-article entr(ies): {', '.join(removed)}")
        else:
            fixes.append("posted_articles.json: deduped + sorted")
    return fixes


def _surface_to_optimization(entry: dict):
    """Upsert Priya's audit summary into optimization/optimization_report.json so
    Marco/Iris see calendar issues alongside every other item when prioritizing.
    Replaces any prior priya calendar_audit entry (keeps the report from bloating)."""
    p = REPO_ROOT / "optimization" / "optimization_report.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = load_json(p, [])
    if not isinstance(data, list):
        data = []
    data = [e for e in data if not (isinstance(e, dict)
            and e.get("source") == "priya" and e.get("type") == "calendar_audit")]
    data.append(entry)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main():
    do_fix = "--fix" in sys.argv

    log.info("[priya-batch] Auditing editorial calendar against all sources...")
    readiness = audit()

    by_sev = {"error": 0, "warn": 0, "info": 0}
    for b in bugs:
        by_sev[b["severity"]] = by_sev.get(b["severity"], 0) + 1

    fixable = [b for b in bugs if b.get("autofixable")]
    surfaced = [b for b in bugs if not b.get("autofixable")]

    log.info(f"[priya-batch] {len(bugs)} issue(s): "
             f"{by_sev['error']} error · {by_sev['warn']} warn · {by_sev['info']} info  "
             f"({len(fixable)} auto-fixable · {len(surfaced)} surfaced)")
    for b in bugs:
        tag = "FIX" if b.get("autofixable") else "   "
        log.info(f"[priya-batch]  {tag} [{b['severity'].upper():5}] {b['category']:11} {b['ref']:34} {b['message']}")

    # ── Apply safe fixes (deterministic, reversible, no tokens) ──
    fixes_applied = []
    if do_fix and fixable:
        fixes_applied = apply_safe_fixes()
        for f in fixes_applied:
            log.info(f"[priya-batch] FIXED: {f}")
    elif fixable:
        log.info(f"[priya-batch] {len(fixable)} safe fix(es) available — re-run with --fix to apply.")
    log.info(f"[priya-batch] SURFACED for review (contingent — need sign-off): {len(surfaced)} issue(s).")

    log.info("[priya-batch] Upcoming readiness:")
    for r in readiness:
        log.info(f"[priya-batch]   #{r['number']:03d} {r['title'][:48]:48} "
                 f"Scout={'Y' if r['scout_ready'] else 'N'} "
                 f"Quill={'Y' if r['quill_ready'] else 'N'} "
                 f"Maya={'Y' if r['maya_ready'] else 'N'}")

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "fix" if do_fix else "audit",
        "summary": {"total": len(bugs), **by_sev,
                    "auto_fixable": len(fixable), "surfaced": len(surfaced)},
        "fixes_applied": fixes_applied,
        "bugs": bugs,
        "upcoming_readiness": readiness,
        "note": "Safe fixes auto-resolve only posted_articles.json hygiene. "
                "Title/number/author desyncs are surfaced for Iris/Joe sign-off.",
    }
    out = REPO_ROOT / "optimization" / "priya_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info(f"[priya-batch] Report written -> optimization/priya_audit.json")

    # Surface decision-needing items (errors + warns) into Marco's optimization
    # report so Iris can prioritize them against everything else.
    decision_items = [b for b in surfaced if b["severity"] in ("error", "warn")]
    _surface_to_optimization({
        "source": "priya",
        "type": "calendar_audit",
        "date": date.today().isoformat(),
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": {"errors": by_sev["error"], "warnings": by_sev["warn"],
                    "needs_decision": len(decision_items)},
        "fixes_applied": fixes_applied,
        "needs_decision": [{"severity": b["severity"], "category": b["category"],
                            "ref": b["ref"], "message": b["message"]} for b in decision_items],
        "report": "optimization/priya_audit.json",
    })
    log.info(f"[priya-batch] Surfaced {len(decision_items)} decision item(s) -> "
             f"optimization_report.json (for Iris prioritization)")


if __name__ == "__main__":
    main()
