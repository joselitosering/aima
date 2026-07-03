"""Trend Scout — trending-topic determination (CC subagent).

Runs BEFORE Scout whenever a calendar row's title is still the literal
"TBD — Trending Topic" placeholder. Picks a real, current topic suited to
the row's ASSIGNED AUTHOR (whoever that is — author is a per-row calendar
attribute, not a fixed Dawn/Kenji track), dedups it against everything
already written/planned, and writes the real title + category back into
the row in aima-editorial-calendar.md so the decision is durable and
idempotent (a re-run sees a real title and skips straight to Scout).

Fiduciary trace: every selection is logged to
articles/research/[slug]-topic-selection.json (rationale + sources) and
appended to optimization/optimization_report.json for Iris.

This step only replaces the TITLE — writers still HALT without a Scout
brief; Scout still has to run and produce real research afterward.
"""

import json
import re
from datetime import date

from agents.base import (call_cc_agent, read_json, write_json,
                         append_optimization_report, REPO_ROOT, log)
from agents.prompts import TREND_SCOUT_PROMPT
from agents.scout import _filtered_sources

CALENDAR_PATH = REPO_ROOT / "articles" / "aima-editorial-calendar.md"
STATE_PATH = REPO_ROOT / "articles" / "aima-coworker-state.json"
PERSONAS_DIR = REPO_ROOT / "articles" / "personas"
RESEARCH_DIR = REPO_ROOT / "articles" / "research"

TBD_PREFIX = "TBD"          # matched together with "Trending Topic" below

# scout-sources topic tags per persona (keyed by persona-file slug). Authors
# without an entry fall back to the default set — any author can take a
# trending row; their persona .md file supplies the beat.
_TREND_TAGS = {
    "dawn-ginhaua": {"ai", "society", "technology", "labor", "economy",
                     "humanity", "policy", "culture"},
    "kenji-nakamoto": {"ai", "technology", "science", "research", "robotics",
                       "space", "machine_learning", "biotechnology", "blockchain"},
    "joselito-sering": {"ai", "technology", "society", "culture",
                        "generative_media", "economy", "science"},
}
_DEFAULT_TREND_TAGS = {"ai", "technology", "science", "society", "research"}


def is_tbd_title(title: str) -> bool:
    """True if the calendar title is still the trending-topic placeholder."""
    t = (title or "").strip()
    return t.startswith(TBD_PREFIX) and "Trending Topic" in t


def _slugify(text: str, max_parts: int = 5) -> str:
    slug = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")
    return "-".join(slug.split("-")[:max_parts])


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _persona_slug(author: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", author.lower())).strip("-")


def _persona_beat(author: str) -> tuple[str, str]:
    """Return (persona_slug, beat_text) for any author. The beat is the
    author's persona profile from articles/personas/ — trend selection is
    driven by whoever the calendar row assigns, not a hardcoded roster."""
    slug = _persona_slug(author)
    profile = PERSONAS_DIR / f"{slug}.md"
    if profile.exists():
        return slug, profile.read_text(encoding="utf-8")[:7000]
    log.warning(f"[trend-scout] no persona profile for '{author}' "
                f"({profile.name}) — using the general AIMA beat")
    return slug, (f"[No persona profile on file.] Write for {author}, an AIMA "
                  "Magazine staff writer covering what matters in AI right now "
                  "for a thoughtful general-tech readership.")


def _existing_titles() -> list[str]:
    """Everything already planned or written: calendar titles,
    articles_written[] titles, and research-file slugs."""
    titles = []
    if CALENDAR_PATH.exists():
        for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*\|\s*\d+\s*\|\s*[\d-]+\s*\|\s*(.+?)\s*\|", line)
            if m and not is_tbd_title(m.group(1)):
                titles.append(m.group(1).strip())
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}
    for a in state.get("articles_written", []):
        if a.get("title"):
            titles.append(a["title"])
    return titles


def _research_slugs() -> set[str]:
    if not RESEARCH_DIR.exists():
        return set()
    return {p.stem for p in RESEARCH_DIR.iterdir() if p.suffix == ".json"}


def _collides(title: str, existing_norm: set[str], research_slugs: set[str]) -> bool:
    if _norm_title(title) in existing_norm:
        return True
    slug = _slugify(title)
    return any(s.startswith(slug) for s in research_slugs)


def determine_trending_topic(author: str, category_hint: str | None = None,
                             tone_note: str | None = None,
                             number: int | None = None) -> dict:
    """Pick a real trending topic for the given author's TBD calendar row.

    CC_AGENT-tier call (live judgment). Works for ANY author with (or
    without) a persona file — the row's Author column decides whose beat
    to scout. Returns {"title", "category", "rationale", "sources", "slug"}
    — deduped against the calendar, articles_written[], and
    articles/research/. Raises RuntimeError if all candidates collide.
    """
    persona_slug, beat = _persona_beat(author)
    tags = _TREND_TAGS.get(persona_slug, _DEFAULT_TREND_TAGS)

    sources_config = read_json("scout-sources.json")
    filtered = _filtered_sources(sources_config, tags)
    existing = _existing_titles()
    existing_norm = {_norm_title(t) for t in existing}
    research_slugs = _research_slugs()

    log.info(f"[trend-scout] determining topic for {author}"
             f"{f' (row #{number})' if number else ''} — "
             f"{len(filtered['rss_feeds'])} feeds, {len(filtered['apis'])} APIs, "
             f"{len(existing)} existing titles for dedup")

    user_input = f"""\
TODAY: {date.today().isoformat()}

ASSIGNED AUTHOR: {author}
PERSONA PROFILE / BEAT (choose a topic THIS writer would own):
{beat}

TONE NOTE FOR THIS ROW: {tone_note or "(none)"}
CATEGORY HINT: {category_hint or "(none — pick the best-fitting AIMA category)"}

SOURCES (curated for this author's beat — fetch feeds, call APIs with keys
from agents/.env, prefer no-key sources; WebSearch only for gaps):
{json.dumps(filtered, indent=2)}

ALREADY COVERED — your candidates must NOT duplicate or closely paraphrase
any of these titles:
{json.dumps(existing, indent=2)}

Survey what is genuinely trending in AI RIGHT NOW for this author's beat and
return exactly 3 ranked candidate topics as JSON (best first):

{{
  "candidates": [
    {{
      "title": "Compelling AIMA-style article title",
      "category": "e.g. AI Ethics / AI Science / AI Labor",
      "rationale": "1-2 sentences: why this is trending now and why it fits this author",
      "sources": [{{"name": "source that surfaced it", "url": "https://..."}}]
    }}
  ]
}}

Return ONLY the JSON. Do not write any files.\
"""

    raw = call_cc_agent("trend_scout", TREND_SCOUT_PROMPT, user_input).strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        payload = json.loads(raw[start:end])
        candidates = payload["candidates"]
        assert candidates and all(c.get("title") for c in candidates)
    except (ValueError, KeyError, AssertionError, json.JSONDecodeError) as exc:
        log.error(f"[trend-scout] CC output (first 500 chars):\n{raw[:500]}")
        raise RuntimeError(f"[trend-scout] no valid candidates JSON in CC output: {exc}") from exc

    chosen, rejected = None, []
    for c in candidates:
        if _collides(c["title"], existing_norm, research_slugs):
            log.info(f"[trend-scout] dedup collision, skipping: '{c['title'][:60]}'")
            rejected.append({**c, "rejected_reason": "dedup_collision"})
        elif chosen is None:
            chosen = c
        else:
            rejected.append({**c, "rejected_reason": "lower_rank"})
    if chosen is None:
        raise RuntimeError(
            f"[trend-scout] all {len(candidates)} candidates collided with "
            "existing titles/research — re-run or widen sources")

    chosen = {
        "title": chosen["title"].strip(),
        "category": (chosen.get("category") or "Trending").strip(),
        "rationale": chosen.get("rationale", ""),
        "sources": chosen.get("sources", []),
    }
    chosen["slug"] = _slugify(chosen["title"])

    # ── Fiduciary trace: sidecar log + optimization report ────
    selection_log = {
        "row": number,
        "author": author,
        "persona": persona_slug,
        "date": date.today().isoformat(),
        "chosen": {k: chosen[k] for k in ("title", "category", "rationale", "sources")},
        "rejected_candidates": rejected,
    }
    write_json(f"articles/research/{chosen['slug']}-topic-selection.json", selection_log)
    append_optimization_report({
        "source": "trend_scout",
        "date": date.today().isoformat(),
        "row": number,
        "author": author,
        "title": chosen["title"],
        "category": chosen["category"],
        "rationale": chosen["rationale"],
        "sources": chosen["sources"],
    })
    log.info(f"[trend-scout] chose '{chosen['title']}' ({chosen['category']}) — "
             f"{chosen['rationale']}")
    return chosen


def persist_topic_to_calendar(number: int, title: str, category: str) -> bool:
    """Replace the TBD title + category of canonical row `number` in
    aima-editorial-calendar.md, in place, same row. Returns True on success."""
    lines = CALENDAR_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        m = re.match(rf"\s*\|\s*{number}\s*\|", line)
        if not m:
            continue
        cells = line.rstrip("\n").split("|")
        # ['', ' 25 ', ' 2026-07-07 ', ' TBD — … ', ' Trending ', ' 8 min ', ' note ', ' Author ', '']
        if len(cells) < 6 or not is_tbd_title(cells[3]):
            log.warning(f"[trend-scout] row #{number} is not a TBD row — not touching it")
            return False
        cells[3] = f" {title} "
        cells[4] = f" {category} "
        lines[i] = "|".join(cells) + "\n"
        CALENDAR_PATH.write_text("".join(lines), encoding="utf-8")
        log.info(f"[trend-scout] calendar updated: #{number} -> '{title}' ({category})")
        return True
    log.warning(f"[trend-scout] row #{number} not found in calendar")
    return False


def _calendar_row(number: int) -> dict | None:
    """Parse one row of the unified calendar
    (| # | Date | Title | Category | Read | Tone Note | Author |)."""
    if not CALENDAR_PATH.exists():
        return None
    for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines():
        if not re.match(rf"\s*\|\s*{number}\s*\|\s*[\d-]+\s*\|", line):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 6:
            return None
        return {
            "title": cells[3], "category": cells[4],
            "tone_note": cells[6] if len(cells) > 6 else "",
            "author": cells[7] if len(cells) > 7 and cells[7] else "Joselito Sering",
        }
    return None


def resolve_tbd_row(number: int) -> bool:
    """Full-pipeline hook (called by Priya before her CC run): if calendar row
    `number` is still the TBD placeholder, determine a real topic for the
    row's author and persist it. Returns True if the calendar was updated.
    No-op (and no CC call) when the row already has a real title."""
    row = _calendar_row(number)
    if not row or not is_tbd_title(row["title"]):
        return False
    log.info(f"[trend-scout] row #{number} is a TBD trending row — "
             f"determining topic for {row['author']} before Priya builds the spec")
    chosen = determine_trending_topic(
        row["author"],
        category_hint=row["category"] if row["category"].lower() != "trending" else None,
        tone_note=row["tone_note"],
        number=number,
    )
    return persist_topic_to_calendar(number, chosen["title"], chosen["category"])


def resolve_tbd_spec(spec: dict) -> dict:
    """If spec's title is the TBD trending placeholder, determine a real topic
    for the row's assigned author, persist it to the calendar, and return the
    updated spec. No-op (and no CC call) for already-resolved titles —
    idempotent by construction."""
    if not is_tbd_title(spec.get("title", "")):
        return spec

    author = (spec.get("author") or "").strip()
    if not author:
        raise RuntimeError(f"[trend-scout] TBD spec has no author: {spec}")

    number = spec.get("number")
    chosen = determine_trending_topic(
        author,
        category_hint=spec.get("category") if spec.get("category", "").lower() != "trending" else None,
        tone_note=spec.get("tone_note"),
        number=number,
    )
    if number:
        persist_topic_to_calendar(number, chosen["title"], chosen["category"])

    updated = dict(spec)
    updated.update(title=chosen["title"], category=chosen["category"],
                   slug=chosen["slug"])
    return updated
