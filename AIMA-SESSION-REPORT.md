# AIMA Build Session Report
**Date:** June 22, 2026  
**Scope:** Agent pipeline architecture, token governance, and Scout research library

---

## 1. Agent Structure

### Pipeline Overview

The AIMA pipeline is **sequential**. Marco orchestrates every handoff. Nothing runs in parallel during article production.

```
Priya → Marco → Scout → Marco → Quill → Marco → Maya → Marco → Vera
                                                                  │
                                         fail (copy) ────────────┤
                                         fail (visual) ───────────┤
                                                                  │ pass
                                                               Porter → Nova → Marco logs
```

**Async agents** (run independently of the article pipeline):

| Agent | Trigger | Runs |
|-------|---------|------|
| Echo | 48h after article posts | Collects LinkedIn analytics |
| Lumen | After Echo | Collects GA4, Meta, TikTok, BMC analytics |
| Cora | Throughout every run | Cross-cutting token governance |
| Iris | Weekly | Reads optimization_report.json, sets editorial calendar |

---

### Agent Roster (12 agents)

| Code | Agent | Role | Type | Model |
|------|-------|------|------|-------|
| IR | **Iris** | Strategic Director | Autonomous · weekly | Sonnet 4.6 |
| MR | **Marco** | Pipeline Orchestrator | Autonomous · daily | Sonnet 4.6 |
| PR | **Priya** | Article Spec Builder | Autonomous | Sonnet 4.6 |
| SC | **Scout** | Research Agent | Autonomous | Sonnet 4.6 |
| QL | **Quill** | Writer | Autonomous | Sonnet 4.6 (→ Opus upgrade path) |
| MY | **Maya** | Visual Director | Autonomous | Sonnet 4.6 |
| VR | **Vera** | QC Checker | Autonomous | Haiku 4.5 |
| PT | **Porter** | Git Publisher | Mechanical | Haiku 4.5 |
| NV | **Nova** | LinkedIn Publisher | Mechanical | Haiku 4.5 |
| EC | **Echo** | LinkedIn Analytics | Mechanical | Haiku 4.5 |
| LM | **Lumen** | Cross-Platform Analytics | Autonomous | Sonnet 4.6 |
| CO | **Cora** | Token Resource Manager | Autonomous | Sonnet 4.6 |

---

### Agent Roles (detail)

**Iris** — Reads `optimization/optimization_report.json` at run start. Entries written by Marco (run summaries), Lumen (analytics), and Cora (token/quality). Sets editorial calendar and writes improvement decisions back to `CLAUDE.md`.

**Marco** — Python orchestrator. Calls each agent in sequence via `call_agent()`. Owns all handoffs, logs outcomes, appends run summary to `optimization_report.json`.

**Priya** — Reads `articles/aima-coworker-state.json`, persona files, and editorial calendar. Builds the article spec JSON including `target_words` based on article goal.

**Scout** — Reads `scout-sources.json` → filters sources by topic tags matching article brief → fetches RSS/APIs → distills 8–12 research excerpts → writes `articles/research/brief-NNN.json`.

**Quill** — Receives spec + research brief. Writes article HTML in persona voice to `spec.target_words` ± 50. Hard ceiling: 1,800 words. Cora enforces via `max_tokens=22,000`.

**Maya** — Generates 2 header images via Higgsfield AI (nano_banana_pro, 16:9), resizes to 1200×630 JPG via PIL, selects the stronger image, merges copy HTML + image into article skeleton, saves both images, `git add`s — no push.

**Vera** — Runs 11-point QC checklist on merged article. Returns PASS or FAIL with specific flags for Marco.

**Porter** — `git commit` + `git push` on PASS. No LLM reasoning needed.

**Nova** — Calls `linkedin_pipeline/pipeline.py` which posts to company page + reshares to personal profile + logs to `post_log.json`.

**Echo** — Reads `post_log.json` for posts where `analytics_collected: false` and `posted_at > 48h`. Calls `/rest/socialMediaPostStatistics`. Writes to `linkedin_analytics.csv`.

**Lumen** — Collects GA4, Meta, TikTok, and Buy Me a Coffee analytics. Writes per-platform CSVs and `platform_summary.json`. Appends to `optimization_report.json`.

**Cora** — Monitors token spend per agent per run. Enforces Quill word count cap. Alerts Marco at 80% per-agent threshold. Logs to `token_budget.json` and `token_log.csv`. Appends to `optimization_report.json`.

---

### Architecture Decision: Hybrid Python + Claude Code

Two implementation tiers were established:

**Claude Code subagents** (subscription-covered, no API billing) — AI reasoning agents: Iris, Priya, Scout, Quill, Maya, Vera, Lumen, Cora.

**Pure Python** (no LLM calls) — Mechanical agents: Marco (orchestration shell), Porter (git), Nova (calls existing `pipeline.py`), Echo (API + CSV append).

> **Critical:** Do NOT set `ANTHROPIC_API_KEY` as an environment variable when using Claude Code. If that env var is present, Claude Code routes to API billing instead of the subscription plan.

---

### Shared Files

| File | Owner(s) | Purpose |
|------|----------|---------|
| `articles/aima-coworker-state.json` | Marco (write) · Priya (read) | Pipeline state — next article number, track, persona queue |
| `articles/research/brief-NNN.json` | Scout (write) · Quill (read) | Research brief per article |
| `optimization/optimization_report.json` | Marco · Lumen · Cora (append) · Iris (read) | Cross-pipeline ops pub/sub |
| `token_budget.json` | Cora | Per-agent budget + live usage |
| `token_log.csv` | Cora | Per-run history, errors, guardrails |
| `linkedin_pipeline/post_log.json` | Nova (write) · Echo (read) | Post IDs for analytics collection |
| `linkedin_analytics.csv` | Echo | LinkedIn metrics per post |
| `platform_summary.json` | Lumen | Cross-platform analytics per article |
| `scout-sources.json` | Static config · Scout (read) | Research source library |
| `CLAUDE.md` | Iris (write) · all agents (read) | Project memory and editorial decisions |

---

### Build Order (6 phases)

| Phase | Agents | Deliverable |
|-------|--------|-------------|
| 1 | — | `agents/base.py`, `agents/config.py`, `agents/run.py` |
| 2 | Priya, Scout, Quill, Maya, Vera | Core article pipeline |
| 3 | Porter, Nova | Publishing pipeline |
| 4 | Marco | Full orchestration shell |
| 5 | Echo, Lumen, Cora, `run_echo.py` | Analytics + governance |
| 6 | Iris, `run_iris.py` | Strategic loop |

---

## 2. Token Structure

### Target: 50,000 tokens per article run

| Agent | Budget | Notes |
|-------|--------|-------|
| Priya | 5,000 | Spec building — structured, low generation |
| Scout | 50,000 | Web + RSS fetch; most budget is context ingestion, not generation |
| Quill | **22,000** | Hard cap enforced by Cora |
| Maya | 15,000 | Image judgment + HTML merge |
| Vera | 5,000 | Checklist matching — Haiku, very fast |
| Marco | 10,000 | Orchestration logic between agents |
| Iris | 8,000 | Weekly, not daily |
| Echo | 5,000 | Haiku + API calls |
| Lumen | 10,000 | Cross-platform synthesis |
| Cora | 5,000 | Budget monitoring throughout run |

**Estimated production cost (Sonnet 4.6 pricing — $3/M input · $15/M output):**

| Scenario | Tokens | Cost |
|----------|--------|------|
| Python pipeline (no conversation overhead) | ~50,000 | ~$0.15–0.25/run |
| Cowork session equivalent | ~90,000–120,000 | ~$0.30–0.45/run |
| Daily (365 runs, Python) | ~18M/year | ~$54–90/year |

Claude Code Pro/Max subscription covers Claude Code subagent calls with no per-token billing.

---

### Cora Enforcement — Quill Word Count Cap

Cora intercepts the Quill call and injects a dynamic constraint:

```python
def prepare_quill_call(spec: dict, research: dict) -> dict:
    target = spec.get("target_words", 1600)
    ceiling = min(target + 200, 1800)   # never exceed 1800 regardless of spec
    return {
        "max_tokens": BUDGET_MAP["quill"],   # 22,000 — hard ceiling
        "extra_instruction": (
            f"Write {target} words (±50). "
            f"Hard ceiling: {ceiling} words. "
            "Stop when the idea is complete — do not pad."
        )
    }
```

---

### Word Count Strategy — `target_words` in Article Spec

Priya sets `target_words` in the spec based on each article's goal. Quill writes to that target; Cora enforces the ceiling.

| Goal | Target | Rationale |
|------|--------|-----------|
| SEO-priority | 1,800 | Depth for ranking + keyword coverage |
| LinkedIn/social-first | 1,400 | Scannable, high shareability |
| Lead generation | 1,500 | Trust-building + clear CTA space |
| Default (unset) | 1,600 | Safe overlap of all three goals |

Research basis: optimal range for social shares is 1,000–1,800 words; SEO is 1,500–2,500. Overlap is **1,500–1,800** — AIMA sweet spot.

---

### Cora Error + Misbehavior Protocol

- **Round 1:** Identify root cause → implement prompt-level guardrail → re-run → log outcome
- **Round 2 (same issue, same agent):** Flag to Marco + append to `CLAUDE.md` → recommend re-scope, re-allocate, or dismissal

---

## 3. Research Structure

### scout-sources.json

Located at repo root. Scout reads this file at the start of every run, filters sources by topic tags matching the article brief, and fetches only relevant sources — never all of them.

**Total sources: ~120** across 14 thematic sections.

---

### Source Inventory by Section

| Section | Type | Count | Key Sources |
|---------|------|-------|-------------|
| Science & Technology | RSS | 13 | NASA, ESA, ScienceDaily, Nature, Phys.org, MIT Tech Review, Wired, Ars Technica, IEEE Spectrum, arXiv (3 feeds) |
| Global & Society | RSS | 8 | The Conversation, Aeon, BBC Future, UN News, Al Jazeera, The Intercept, Project Syndicate, PLOS ONE |
| Finance & Markets | RSS | 15 | Reuters, MarketWatch, CNBC, Bloomberg, Yahoo Finance, Seeking Alpha, Investopedia, FXStreet, DailyFX, Benzinga, ZeroHedge, ForexLive, StockCharts, TA Stocks & Commodities, Financial Times |
| Art & Visual Culture | RSS | 5 | Artsy, Hyperallergic, Colossal, Juxtapoz, The Art Newspaper |
| Music | RSS | 5 | Pitchfork, NME, Billboard, Stereogum, Rolling Stone |
| Film, TV & Entertainment | RSS | 5 | Variety, Hollywood Reporter, IndieWire, Deadline, Screen Rant |
| Theater | RSS | 2 | Playbill, TheaterMania |
| Culture & Lifestyle | RSS | 6 | BBC Culture, Guardian Culture, NYT Arts, Open Culture, Highsnobiety, Dazed |
| Travel & Luxury | RSS | 6 | Atlas Obscura, Condé Nast Traveler, Travel + Leisure, Lonely Planet, The Points Guy, Robb Report |
| World Literature | RSS | 4 | Words Without Borders, LitHub, Guardian Books, World Literature Today |
| Philosophy | RSS | 2 | Daily Nous, APA Blog |
| Psychology | RSS | 4 | BPS Digest, Psychology Today, APS Observer, ScienceDaily Mind & Brain |
| Sociology | RSS | 3 | The Society Pages, Contexts Magazine, Everyday Sociology Blog |
| Anthropology & Indigenous | RSS | 7 | SAPIENS, Anthrodendum, EurekAlert Anthropology, Leakey Foundation, Cultural Survival, Indian Country Today, Survival International |
| Medicine & Global Health | RSS | 6 | Medical News Today, STAT News, WHO, NIH, NEJM, The Lancet |
| News Aggregator APIs | API | 6 | Guardian, NYT, NewsAPI, GNews, Currents, MediaStack, Event Registry |
| Scholarly APIs | API | 3 | arXiv, PubMed, Crossref |
| Statistical Data APIs | API | 14 | World Bank, IMF, FRED, UN SDG, UN Comtrade, OECD, Eurostat, Google Trends (pytrends), Our World in Data, Trading Economics, Nasdaq Data Link, BLS, US Census, Data.gov, CDC WONDER |
| Financial Data APIs | API | 4 | Finnhub, IEX Cloud, Polygon.io, Alpaca Markets News |

---

### Topic Tag Index

Scout uses 30 topic tags to route article briefs to the right source clusters:

`ai` · `space` · `robotics` · `blockchain` · `fintech` · `economy` · `generative_media` · `society` · `global_affairs` · `humanity` · `science` · `technology` · `research` · `finance` · `markets` · `technical_analysis` · `algorithmic_trading` · `forex` · `commodities` · `art` · `music` · `film` · `tv` · `theater` · `culture` · `luxury` · `travel` · `design` · `fashion` · `literature` · `philosophy` · `psychology` · `neuroscience` · `sociology` · `anthropology` · `indigenous` · `medicine` · `statistics` · `demographics` · `economic_data` · `trade` · `labor` · `health_data`

---

### Scout Run Behavior

1. Read `scout-sources.json`
2. Match article brief keywords → topic tags → source IDs
3. Fetch only matching sources (typically 8–15 per run)
4. Read `articles/research/` for any pre-cached local files
5. Distill to 8–12 curated excerpts with source attribution
6. Call statistical data APIs if article needs quantitative backing
7. Write `articles/research/brief-NNN.json`
8. Return brief path to Marco

**Web search is the fallback** — used only for breaking news and niche intersections not covered by the library.

---

### Local Research Cache

`articles/research/` — Pre-cached CSVs and JSONs are read automatically by Scout before any external fetch. Supports webhook outputs, manual research drops, and pre-loaded datasets.

---

### Key API Credentials Needed

All keys stored in `agents/.env` (gitignored):

| Key Env Var | Source | Free Tier |
|-------------|--------|-----------|
| `GUARDIAN_API_KEY` | open-platform.theguardian.com | 5,000 req/day |
| `NYT_API_KEY` | developer.nytimes.com | 500 req/day |
| `NEWSAPI_KEY` | newsapi.org | 100 req/day |
| `GNEWS_API_KEY` | gnews.io | 100 req/day |
| `FRED_API_KEY` | fred.stlouisfed.org | 120 req/min |
| `WORLD_BANK` | No key needed | — |
| `IMF_API_KEY` | dataservices.imf.org | Generous |
| `UN_SDG` | No key needed | — |
| `OECD` | No key needed | — |
| `EUROSTAT` | No key needed | — |
| `FINNHUB_API_KEY` | finnhub.io | 60 calls/min |
| `POLYGON_API_KEY` | polygon.io | 5 calls/min |
| `ALPACA_API_KEY_ID` + `ALPACA_API_SECRET_KEY` | alpaca.markets | Unlimited (paper account) |
| `BLS_API_KEY` | data.bls.gov | 500 req/day |
| `CENSUS_API_KEY` | api.census.gov | High |

---

## Summary of Files Changed This Session

| File | Status | Change |
|------|--------|--------|
| `AGENT_SPEC.md` | Updated | Added hybrid architecture, token budget section, dynamic `target_words`, Cora enforcement code, Maya corrected to sequential pipeline |
| `CLAUDE.md` | Updated | Maya section corrected, Scout implementation steps 1 & 2 marked complete |
| `scout-sources.json` | Created | 120+ sources, 14 sections, 43 topic tags, topic tag index |

---

*Report generated June 22, 2026 · AIMA Pipeline v0.1 (pre-build)*
