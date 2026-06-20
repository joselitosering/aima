"""
xls_import.py — Import LinkedIn Analytics XLS export into post_analytics.csv.

Usage:
  python xls_import.py path/to/linkedin_analytics.xlsx

LinkedIn Analytics XLS columns expected (post-level export):
  Post title / content snippet, Date, Impressions, Clicks, CTR,
  Likes, Comments, Shares, Engagement Rate

The script auto-matches each row to an article in post_log.json by comparing
the post content snippet against known article titles. Unmatched rows are
printed for manual review — you can pass --map to supply manual overrides.

Options:
  --map "content snippet"=article_filename.html   (repeatable)
  --dry-run   Print matches without writing anything
  --force     Re-import rows already in post_analytics.csv
"""

import os, sys, csv, json, re, argparse
from pathlib import Path
from datetime import datetime, timezone

import subprocess

try:
    import openpyxl
except ImportError:
    sys.exit("Missing dependency: pip install openpyxl --break-system-packages")

BASE          = Path(__file__).parent
POST_LOG      = BASE / "post_log.json"
ANALYTICS_CSV = BASE / "post_analytics.csv"

CSV_HEADERS = [
    "post_id", "article", "title", "persona", "posted_at",
    "collected_at", "impressions", "clicks", "likes", "comments",
    "shares", "engagement_rate", "ctr",
]

# ── git push ─────────────────────────────────────────────────────────────────

def _git_push():
    repo_root = BASE.parent
    files = [str(ANALYTICS_CSV), str(POST_LOG)]
    try:
        subprocess.run(["git", "add"] + files, cwd=repo_root, check=True, capture_output=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_root, capture_output=True)
        if diff.returncode == 0:
            print("  git: nothing to push (no changes staged)")
            return
        subprocess.run(["git", "commit", "-m", "data: import analytics from XLS"],
                       cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"],
                       cwd=repo_root, check=True, capture_output=True)
        print("  git push OK — dashboard will update on next page load")
    except Exception as e:
        print(f"  git push failed (run manually): {e}")


# ── helpers ───────────────────────────────────────────────────────────────────

def load_post_log():
    if POST_LOG.exists():
        with open(POST_LOG, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_post_log(log):
    with open(POST_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def load_existing_csv():
    """Return set of post_ids already in post_analytics.csv."""
    if not ANALYTICS_CSV.exists():
        return set()
    with open(ANALYTICS_CSV, newline="", encoding="utf-8") as f:
        return {row["post_id"] for row in csv.DictReader(f) if row.get("post_id")}


def ensure_csv_headers():
    if not ANALYTICS_CSV.exists():
        with open(ANALYTICS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADERS)


def normalize(text):
    """Lowercase, strip punctuation, collapse whitespace for fuzzy match."""
    text = re.sub(r"[^\w\s]", " ", str(text).lower())
    return re.sub(r"\s+", " ", text).strip()


def score_match(content_snippet, log_title):
    """
    Simple overlap score: fraction of words in log_title found in snippet.
    Returns 0.0–1.0.
    """
    snip_words  = set(normalize(content_snippet).split())
    title_words = set(normalize(log_title).split())
    if not title_words:
        return 0.0
    common = snip_words & title_words
    return len(common) / len(title_words)


def find_best_match(content_snippet, log, threshold=0.35):
    """Return (log_entry, score) for best match, or (None, 0) if below threshold."""
    best_entry, best_score = None, 0.0
    for entry in log:
        s = score_match(content_snippet, entry.get("title", ""))
        if s > best_score:
            best_score, best_entry = s, entry
    if best_score >= threshold:
        return best_entry, best_score
    return None, best_score


# ── XLS parsing ──────────────────────────────────────────────────────────────

COLUMN_ALIASES = {
    # LinkedIn column name variants → internal key
    "post title":          "content",
    "title":               "content",
    "content":             "content",
    "post content":        "content",
    "update content":      "content",
    "date":                "date",
    "created date":        "date",
    "post date":           "date",
    "impressions":         "impressions",
    "clicks":              "clicks",
    "click through rate (ctr)": "ctr",
    "ctr":                 "ctr",
    "likes":               "likes",
    "reactions":           "likes",
    "comments":            "comments",
    "shares":              "shares",
    "reposts":             "shares",
    "engagement rate":     "engagement_rate",
    "engagement":          "engagement_rate",
    "post url":            "post_url",
    "url":                 "post_url",
    "update url":          "post_url",
    "post urn":            "post_urn",
}


def parse_xls(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        sys.exit("XLS file appears empty.")

    # Find header row (first row with recognizable column names)
    header_row_idx = None
    col_map = {}
    for i, row in enumerate(rows[:5]):
        col_map = {}
        for j, cell in enumerate(row):
            if cell is None:
                continue
            alias = COLUMN_ALIASES.get(str(cell).strip().lower())
            if alias:
                col_map[alias] = j
        if len(col_map) >= 3:
            header_row_idx = i
            break

    if header_row_idx is None:
        print("Could not auto-detect header row. First 3 rows:")
        for r in rows[:3]:
            print(" ", r)
        sys.exit("Please check the XLS format.")

    print(f"  Header row: {header_row_idx + 1}, columns mapped: {list(col_map.keys())}")

    records = []
    for row in rows[header_row_idx + 1:]:
        if all(c is None for c in row):
            continue
        def get(key, default=""):
            idx = col_map.get(key)
            return row[idx] if idx is not None and row[idx] is not None else default

        content      = str(get("content", "")).strip()
        if not content:
            continue

        # Parse numbers safely
        def num(v, default=0):
            try:
                return float(str(v).replace("%", "").replace(",", "")) if v != "" else default
            except (ValueError, TypeError):
                return default

        impressions    = int(num(get("impressions")))
        clicks         = int(num(get("clicks")))
        likes          = int(num(get("likes")))
        comments       = int(num(get("comments")))
        shares         = int(num(get("shares")))
        engagement_raw = num(get("engagement_rate"))
        # LinkedIn exports engagement as percentage (e.g. 11.63) — store as decimal
        engagement     = round(engagement_raw / 100 if engagement_raw > 1 else engagement_raw, 4)
        ctr_raw        = num(get("ctr"))
        ctr            = round(ctr_raw / 100 if ctr_raw > 1 else ctr_raw, 4)

        # Date
        date_val = get("date", "")
        try:
            if isinstance(date_val, datetime):
                posted_at = date_val.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                posted_at = str(date_val).strip()
        except Exception:
            posted_at = str(date_val)

        post_url = str(get("post_url", "")).strip()
        post_urn = str(get("post_urn", "")).strip()

        records.append({
            "content":      content,
            "date":         posted_at,
            "impressions":  impressions,
            "clicks":       clicks,
            "likes":        likes,
            "comments":     comments,
            "shares":       shares,
            "engagement_rate": engagement,
            "ctr":          ctr,
            "post_url":     post_url,
            "post_urn":     post_urn,
        })

    wb.close()
    return records


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("xls_file", help="Path to LinkedIn Analytics .xlsx export")
    parser.add_argument("--map", action="append", default=[],
                        help='"content snippet"=article_filename.html  (repeatable)')
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true",
                        help="Re-import rows already in post_analytics.csv")
    args = parser.parse_args()

    xls_path = Path(args.xls_file)
    if not xls_path.exists():
        sys.exit(f"File not found: {xls_path}")

    # Parse --map overrides
    manual_map = {}
    for m in args.map:
        if "=" not in m:
            print(f"  WARNING: ignoring malformed --map value: {m}")
            continue
        snippet, article = m.split("=", 1)
        manual_map[snippet.strip().lower()] = article.strip()

    log          = load_post_log()
    existing_ids = load_existing_csv()
    ensure_csv_headers()

    print(f"\nParsing {xls_path.name}...")
    records = parse_xls(xls_path)
    print(f"  {len(records)} data rows found.\n")

    imported   = 0
    unmatched  = []
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    for rec in records:
        content = rec["content"]

        # Determine post_id: prefer post_urn, fall back to post_url, else blank
        post_id = rec["post_urn"] or rec["post_url"] or ""

        # Skip already-imported (unless --force)
        if post_id and post_id in existing_ids and not args.force:
            print(f"  SKIP (already imported): {content[:70]}")
            continue

        # Match to article
        matched_entry  = None
        matched_source = ""

        # 1. Manual --map override
        for key, article_file in manual_map.items():
            if key in content.lower():
                # find matching log entry by article filename
                for e in log:
                    if e.get("article", "") == article_file:
                        matched_entry  = e
                        matched_source = "--map"
                        break
                if matched_entry:
                    break

        # 2. Auto fuzzy-match against post_log titles
        if not matched_entry:
            matched_entry, score = find_best_match(content, log)
            if matched_entry:
                matched_source = f"auto ({score:.0%})"

        if matched_entry:
            article_file = matched_entry.get("article", "")
            title        = matched_entry.get("title", content[:80])
            persona      = matched_entry.get("persona", "joselito")
            log_post_id  = matched_entry.get("post_id", post_id)
            final_id     = post_id or log_post_id

            print(f"  MATCH [{matched_source}]: {content[:60]}")
            print(f"         → {article_file}")
            print(f"           Imp:{rec['impressions']} Clicks:{rec['clicks']} CTR:{rec['ctr']:.1%} Eng:{rec['engagement_rate']:.2%}\n")

            if not args.dry_run:
                row = [
                    final_id, article_file, title, persona,
                    rec["date"], collected_at,
                    rec["impressions"], rec["clicks"],
                    rec["likes"], rec["comments"], rec["shares"],
                    rec["engagement_rate"], rec["ctr"],
                ]
                with open(ANALYTICS_CSV, "a", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(row)

                # Mark as collected in post_log
                for e in log:
                    if e.get("article") == article_file:
                        e["analytics_collected"] = True

                imported += 1
        else:
            unmatched.append(rec)

    if not args.dry_run and imported:
        save_post_log(log)
        print(f"\n✓ Imported {imported} row(s) → post_analytics.csv")
        print(  "  post_log.json updated (analytics_collected = true)")
        _git_push()

    if unmatched:
        print(f"\n⚠  {len(unmatched)} unmatched row(s) — use --map to assign:\n")
        for rec in unmatched:
            print(f'  --map "{rec["content"][:80]}"=article_filename.html')
            print(f"         Imp:{rec['impressions']} Clicks:{rec['clicks']} CTR:{rec['ctr']:.1%}\n")

    if args.dry_run:
        print("\n[dry-run] No files written.")


if __name__ == "__main__":
    main()
