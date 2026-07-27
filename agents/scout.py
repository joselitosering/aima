"""Scout — Research Agent (CC subagent).

Receives article spec from Marco. Priority order:
  1. Return immediately if articles/research/{slug}-research.json already exists
  2. List pre-cached files in articles/research/ for Scout to ingest
  3. Pass only topic-filtered feeds/APIs from scout-sources.json (not all 63KB)
  4. Web search only for gaps the local library can't fill
"""

import json
import re
from pathlib import Path

from agents.base import call_cc_agent, read_json, write_json, REPO_ROOT, log
from agents.prompts import SCOUT_PROMPT


def _scout_budget_remaining() -> tuple[int, int]:
    """Return (budget_ceiling, tokens_remaining) for Scout from token_budget.json.

    Used to inject a hard token guardrail into Scout's user_input BEFORE the
    CC call fires — so Scout knows its ceiling before it picks up a single tool.
    Returns (0, 0) if the budget file is absent or unreadable (fail-open).
    """
    try:
        b = json.loads((REPO_ROOT / "token_budget.json").read_text(encoding="utf-8"))
        sc = b.get("agents", {}).get("SC", {})
        ceiling = int(sc.get("budget", 0))
        used    = int(sc.get("used",   0))
        remaining = max(0, ceiling - used)
        return ceiling, remaining
    except Exception:
        return 0, 0

# Rough mapping from article category keywords → scout-sources topic tags
_CATEGORY_TAG_MAP = {
    "health":       {"medicine", "health_data", "ai", "science", "neuroscience"},
    "medicine":     {"medicine", "health_data", "science", "neuroscience"},
    "tech":         {"technology", "ai", "science", "research"},
    "ai":           {"ai", "technology", "research", "science"},
    "economy":      {"economy", "labor", "trade", "economic_data", "statistics"},
    "policy":       {"society", "global_affairs", "humanity", "ai"},
    "finance":      {"finance", "markets", "fintech", "economy"},
    "governance":   {"society", "global_affairs", "humanity", "ai", "technology"},
    "labor":        {"labor", "economy", "society", "trade"},
    "society":      {"society", "humanity", "psychology", "sociology"},
    "science":      {"science", "research", "neuroscience", "statistics"},
    "culture":      {"culture", "art", "philosophy", "sociology"},
    "global":       {"global_affairs", "trade", "economy", "demographics"},
    "media":        {"generative_media", "ai", "culture", "technology"},
    "climate":      {"science", "global_affairs", "society", "economics"},
}


def _topic_tags_for_spec(spec: dict) -> set:
    """Derive topic tags from article category + custom_tags."""
    tags = set()
    category = spec.get("category", "").lower()
    for keyword, mapped_tags in _CATEGORY_TAG_MAP.items():
        if keyword in category:
            tags.update(mapped_tags)

    for tag in spec.get("custom_tags", []):
        cleaned = tag.lstrip("#").lower().replace(" ", "_").replace("-", "_")
        tags.add(cleaned)

    title_lower = spec.get("title", "").lower()
    for keyword, mapped_tags in _CATEGORY_TAG_MAP.items():
        if keyword in title_lower:
            tags.update(mapped_tags)

    return tags or {"ai", "technology", "research", "science"}


def _filtered_sources(sources_config: dict, topic_tags: set) -> dict:
    """Return a compact source list: only feeds/APIs matching topic_tags."""
    feeds = [
        f for f in sources_config.get("rss_feeds", [])
        if any(t in topic_tags for t in f.get("topic_tags", []))
    ]
    apis = [
        a for a in sources_config.get("apis", [])
        if any(t in topic_tags for t in a.get("topic_tags", []))
    ]
    return {
        "rss_feeds": feeds[:12],
        "apis": apis[:6],
        "local_data_paths": sources_config.get("local_data_paths", []),
    }


def _list_cached_research(topic_tags: set = None, max_files: int = 5) -> list[str]:
    """Return relative paths of topic-relevant cached research files.

    Filters by topic_tags keywords appearing in the filename (same tag logic
    used for feeds/APIs). Caps at max_files, sorted by file size ascending so
    Scout reads the smallest (cheapest) relevant files first.

    Guardrail added 2026-07-17: previously returned ALL files unfiltered —
    Scout would list 18+ files (some 65KB each) and read whichever it judged
    relevant, burning 50k+ tokens on cache reads before any real research.
    """
    research_dir = REPO_ROOT / "articles" / "research"
    if not research_dir.exists():
        return []

    candidates = [
        p for p in research_dir.iterdir()
        if p.suffix in {".json", ".csv"} and p.stat().st_size > 100
        and "-topic-selection" not in p.name  # topic-selection files are not research
    ]

    # Topic filter: keep files whose stem contains at least one tag keyword.
    # IMPORTANT: exclude "research" from tag_words — every file is named
    # *-research.json so "research" matches everything and makes the filter a no-op.
    if topic_tags:
        tag_words = {t.replace("_", "") for t in topic_tags} - {"research"}
        def _relevant(p: Path) -> bool:
            stem = p.stem.lower().replace("-", "").replace("_", "")
            return any(word in stem for word in tag_words)
        filtered = [p for p in candidates if _relevant(p)]
        # Fall back to all candidates if topic filter is too aggressive
        candidates = filtered if filtered else candidates

    # Sort by size ascending (smallest = fewest tokens to read)
    candidates.sort(key=lambda p: p.stat().st_size)
    candidates = candidates[:max_files]

    return [f"articles/research/{p.name}" for p in candidates]


def _find_research_path(slug: str, number: int):
    """
    Return the first existing research file for this article, or the canonical path.
    Checks slug-keyed paths first, then a _meta.article_number scan (handles a
    caller's slug drifting from Priya's actual chosen slug — e.g.
    run_writer_batch.py's mechanical title-slugify vs. Priya's CC-picked
    "persuasion-engine" for #19, confirmed 2026-07-04), then falls back to a
    glob on the article number appearing in the filename itself.
    """
    padded = str(number).zfill(3)
    candidates = [
        REPO_ROOT / f"articles/research/{slug}-research.json",
        REPO_ROOT / f"articles/research/{slug}-{padded}-research.json",
    ]
    for p in candidates:
        if p.exists() and p.stat().st_size > 100:
            return p

    research_dir = REPO_ROOT / "articles" / "research"
    if research_dir.exists():
        # Metadata scan: authoritative match on article_number regardless of
        # slug drift. Every research file's _meta.article_number is the
        # canonical row number, so this is safe even if the slug text differs.
        for p in sorted(research_dir.glob("*-research.json")):
            if p.stat().st_size <= 100:
                continue
            try:
                meta = json.loads(p.read_text(encoding="utf-8")).get("_meta", {})
            except (json.JSONDecodeError, OSError):
                continue
            if meta.get("article_number") == number:
                log.info(f"[scout] found existing research via _meta.article_number scan: {p.name}")
                return p

        # Glob fallback: any research file containing the article number in its filename.
        # Guard: padded must appear as an isolated segment (split on - or _) so that
        # e.g. "2026" in a filename doesn't falsely match article 026.
        for p in sorted(research_dir.glob(f"*{padded}*research*.json")):
            if p.stat().st_size > 100:
                import re as _re
                stem_parts = _re.split(r"[-_]", p.stem)
                if padded not in stem_parts:
                    log.warning(
                        f"[scout] number glob skipped {p.name!r}: "
                        f"'{padded}' is not an isolated segment"
                    )
                    continue
                log.info(f"[scout] found existing research via number glob: {p.name}")
                return p

    return candidates[0]  # canonical path — will be created on first run


def load_cached(spec: dict) -> dict:
    """Return cached research for this spec, or {} if none exists.

    Used when the Research stage is toggled off (skip-and-reuse the most
    recent artifact) — no CC call, no tokens.
    """
    path = _find_research_path(spec["slug"], spec["number"])
    if path.exists() and path.stat().st_size > 100:
        log.info(f"[scout] load_cached: using {path.name}")
        return json.loads(path.read_text(encoding="utf-8"))
    log.warning(f"[scout] load_cached: no research artifact found for #{spec['number']}")
    return {}


def run(spec: dict) -> dict:
    """
    Research the article defined by spec.
    Saves research to articles/research/[slug]-research.json.
    Returns the research dict.
    """
    slug = spec["slug"]
    number = spec.get("number", 0)
    research_path = _find_research_path(slug, number)

    # ── Priority 1: return cached result immediately ──────────
    if research_path.exists() and research_path.stat().st_size > 100:
        log.info(f"[scout] using cached research: {research_path.name}")
        return json.loads(research_path.read_text(encoding="utf-8"))

    # ── Priority 2: build filtered source list ────────────────
    sources_config = read_json("scout-sources.json")
    topic_tags = _topic_tags_for_spec(spec)
    filtered = _filtered_sources(sources_config, topic_tags)
    cached_files = _list_cached_research(topic_tags=topic_tags, max_files=5)

    # ── Budget guardrail: read BEFORE building user_input ────
    budget_ceiling, budget_remaining = _scout_budget_remaining()
    # Cap the working budget shown to Scout at 60k regardless of the full ceiling.
    # Showing the real remaining (often 490k+) signals "plenty of room" and the
    # model ignores the per-action limits. 60k is enough for 3 cached reads +
    # 2 web searches + 1 write; anything over that is overspend.
    SCOUT_WORKING_BUDGET = 60_000
    if budget_ceiling:
        working_budget = min(budget_remaining, SCOUT_WORKING_BUDGET)
        budget_note = (
            f"TOKEN BUDGET HARD LIMIT: {working_budget:,} tokens for this research task. "
            f"(Full subscription ceiling is larger — ignore it. Your working budget is {working_budget:,}.)\n"
            f"STRICT RULES — stop the moment these are met:\n"
            f"  - Read AT MOST 3 cached files (skim, do not read every word)\n"
            f"  - Fetch AT MOST 3 RSS feeds or API calls total\n"
            f"  - Run AT MOST 2 web searches — prefer snippets, avoid full-page fetches\n"
            f"  - Stop as soon as you have 4 statistics + 2 quotes\n"
            f"  - Write the JSON file and return immediately. No review pass.\n"
            f"Exceeding {working_budget:,} tokens triggers a Cora escalation."
        )
    else:
        budget_note = "No token budget data available — proceed with maximum frugality: 3 sources, 2 searches, stop at 4 stats + 2 quotes."

    log.info(f"[scout] topic_tags: {sorted(topic_tags)}")
    log.info(f"[scout] {len(filtered['rss_feeds'])} feeds, "
             f"{len(filtered['apis'])} APIs, {len(cached_files)} cached files "
             f"(budget: {budget_remaining:,}/{budget_ceiling:,} remaining)")

    cache_section = (
        "\n".join(f"  - {f}" for f in cached_files)
        if cached_files else "  (none yet)"
    )

    user_input = f"""\
⚠ {budget_note}

ARTICLE SPEC:
{json.dumps(spec, indent=2)}

RESEARCH PRIORITY ORDER — follow this exactly:

STEP 1 — READ LOCAL CACHE FIRST (fastest, free, no API calls)
Up to 3 topic-relevant cached files (already filtered for you — read all of these):
{cache_section}

STEP 2 — USE THESE TOPIC-FILTERED SOURCES (curated for this article)
{json.dumps(filtered, indent=2)}

Fetch RSS feeds (no key required) and call APIs with keys from agents/.env.
Prefer no-key sources if keys are unavailable. Stop after 4 feeds.

STEP 3 — WEB SEARCH (only for gaps the above cannot fill)
Use WebSearch only if local cache + feeds/APIs don't provide enough statistics,
expert quotes, or recent news. Maximum 3 searches. Prefer primary sources.

OUTPUT REQUIREMENTS:
- 4-6 statistics, each with source name + year + URL
- 2-3 expert quotes with name + affiliation + URL
- 1 strongest counterargument
- 1-2 recent news items (last 6 months)
- Flag any claim you cannot verify

Save output to: articles/research/{slug}-research.json
Then return the complete research JSON to stdout. Stop immediately after writing.\
"""

    log.info(f"[scout] calling CC subagent for: {slug}")
    raw = call_cc_agent("scout", SCOUT_PROMPT, user_input)

    # ── Check filesystem (CC agent may have written the file) ─
    # Re-probe: CC agent may have saved with or without article number in name.
    research_path = _find_research_path(slug, number)
    if research_path.exists() and research_path.stat().st_size > 100:
        log.info(f"[scout] CC agent wrote research file directly: {research_path.name}")
        return json.loads(research_path.read_text(encoding="utf-8"))

    # ── Fallback: parse JSON from stdout ─────────────────────
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        research = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError) as exc:
        log.error(f"[scout] CC output (first 500 chars):\n{raw[:500]}")
        raise RuntimeError(
            f"[scout] No research JSON found in CC output or on disk for '{slug}'. "
            f"Parser error: {exc}"
        ) from exc

    write_json(f"articles/research/{slug}-research.json", research)
    log.info(f"[scout] research saved from stdout: articles/research/{slug}-research.json")
    return research
