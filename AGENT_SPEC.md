# AIMA Agent Build Spec
**Handoff document for Claude Code · June 2026**

> Read this file first. It contains everything needed to build the AIMA agent pipeline from scratch. All agent prompts, data schemas, file structure, model assignments, environment requirements, and build order are defined here.

---

## Model Recommendation

**Claude Code subagents use whatever model Claude Code defaults to on your subscription plan.** You do not specify a model string in Python code — the CC CLI uses the subscription's default (currently Sonnet). Model selection for CC subagents is controlled in the CC settings or by passing `--model` to the CLI if needed.

**Pure Python agents make no LLM calls** — model strings are irrelevant for Marco, Porter, Nova, and Echo.

| Agent | Tier | Default Model | Notes |
|-------|------|--------------|-------|
| Iris  | CC subagent | Subscription default (Sonnet) | Upgrade to Opus via `--model claude-opus-4-8` if calendar reasoning feels shallow |
| Marco | Pure Python | N/A | Orchestration only — no LLM |
| Priya | CC subagent | Subscription default (Sonnet) | Spec building — Sonnet is sufficient |
| Scout | CC subagent | Subscription default (Sonnet) | Web research — Sonnet performs well |
| Quill | CC subagent | Subscription default (Sonnet) | **Upgrade path:** pass `--model claude-opus-4-8` if article quality plateaus |
| Maya  | CC subagent | Subscription default (Sonnet) | Image judgment + HTML merge |
| Vera  | CC subagent | Subscription default (Sonnet) | 11-point checklist — fast, low token use |
| Porter | Pure Python | N/A | git + deploy guard — no LLM |
| Nova  | Pure Python | N/A | Calls `pipeline.py` — no LLM |
| Echo  | Pure Python | N/A | API calls + CSV — no LLM |
| Lumen | CC subagent | Subscription default (Sonnet) | Cross-platform data synthesis |
| Cora  | CC subagent | Subscription default (Sonnet) | Token budget + hallucination monitoring |

**To override model for a specific CC subagent**, pass `--model MODEL_STRING` in the `call_cc_agent()` invocation in Marco. Only do this for Quill or Iris if quality warrants it.

---

## Architecture

### Implementation: Hybrid Python + Claude Code

The pipeline uses two distinct implementation tiers. The choice is driven by cost: Claude Code Pro/Max subscription covers Claude Code subagent calls with no per-token billing. Direct Anthropic API calls bill per token.

```
┌─────────────────────────────────────────────────────────┐
│  TIER 1 — Claude Code Subagents (subscription-billed)   │
│  Priya · Scout · Quill · Maya · Vera · Lumen · Cora     │
│  Iris (weekly runner)                                    │
│  Called by Marco via subprocess → claude CLI            │
└─────────────────────────────────────────────────────────┘
           ▲                              │
           │ reads files                 │ writes files
           ▼                             ▼
┌─────────────────────────────────────────────────────────┐
│  TIER 2 — Pure Python (no LLM calls)                    │
│  Marco (orchestrator) · Porter · Nova · Echo            │
│  subprocess, file I/O, git, API calls only              │
└─────────────────────────────────────────────────────────┘
```

**Why this split:**

| Agent type | Implementation | Billing |
|-----------|----------------|---------|
| AI reasoning (Priya, Scout, Quill, Maya, Vera, Lumen, Cora, Iris) | Claude Code CLI subagent | Pro/Max subscription |
| Mechanical (Marco, Porter, Nova, Echo) | Pure Python — no LLM | Free |

**Critical:** Do NOT set `ANTHROPIC_API_KEY` in your shell environment or system env. If that variable is present, Claude Code routes to API billing and bypasses the subscription. Keep it absent or unset when running the pipeline.

---

### Pipeline Flow

Sequential. Nothing runs in parallel during article production. Marco owns every handoff.

```
Marco (Python) calls CC subagents in order:

  Priya → Marco → Scout → Marco → Quill → Marco → Maya → Marco → Vera
                                                                    │
                                                fail (copy) ────────┤
                                                fail (visual) ──────┤
                                                                    │ pass
                                                               Porter → Nova → Marco logs
  (daily async, separate runner)
  Echo → Lumen → optimization_report.json
  Cora (monitors throughout each run)

  (weekly, separate runner)
  Iris reads optimization_report.json
```

**Pub/sub reporting:** Marco, Lumen, and Cora each append JSON entries to `optimization/optimization_report.json` with a `"source"` field. Iris reads the file — no direct calls.

---

## File & Folder Structure

```
aima/
├── agents/
│   ├── __init__.py
│   ├── base.py              # shared: CC CLI invoker, file utils, git helpers, logger
│   ├── config.py            # CC_AGENTS, PY_AGENTS, CC_MODEL_OVERRIDE, BUDGET_MAP
│   ├── prompts.py           # all CC subagent system prompts as module constants
│   │
│   ├── marco.py             # [PURE PYTHON] Pipeline Orchestrator — calls CC subagents
│   ├── porter.py            # [PURE PYTHON] git commit + push + deploy guard
│   ├── nova.py              # [PURE PYTHON] calls linkedin_pipeline/pipeline.py
│   ├── echo.py              # [PURE PYTHON] LinkedIn API calls + CSV append
│   │
│   ├── iris.py              # [CC SUBAGENT] Strategic Director — run_iris.py calls this
│   ├── priya.py             # [CC SUBAGENT] Calendar Manager
│   ├── scout.py             # [CC SUBAGENT] Research Agent
│   ├── quill.py             # [CC SUBAGENT] Senior Writer
│   ├── maya.py              # [CC SUBAGENT] Visual Director
│   ├── vera.py              # [CC SUBAGENT] Quality Gate
│   ├── lumen.py             # [CC SUBAGENT] Analytics Aggregator
│   └── cora.py              # [CC SUBAGENT] Token & Quality Governor
│
├── run.py                   # CLI entry point: `python run.py` kicks off Priya → Marco
├── run_iris.py              # Run Iris manually: `python run_iris.py`
├── run_echo.py              # Run Echo+Lumen daily: `python run_echo.py`
│
├── agents/config.py         # MODEL_MAP dict, BUDGET_MAP dict, env constants
│
├── optimization/
│   └── optimization_report.json   # append-only JSON array — Marco/Lumen/Cora write, Iris reads
│
├── token_budget.json        # Cora writes per-agent per-run budget + spend
├── token_log.csv            # Cora appends per-run history
│
├── articles/
│   ├── aima-coworker-state.json   # pipeline state: next_number, next_track, last_run
│   ├── aima-editorial-calendar.md # Iris reads + updates
│   ├── aima-coworker-prompt.md    # Quill reads: article format rules
│   ├── personas/
│   │   ├── dawn-ginhaua.md
│   │   ├── joselito-sering.md
│   │   └── kenji-nakamoto.md
│   └── research/
│       └── [slug]-research.json   # Scout writes here
│
├── img/
│   ├── articles/            # Maya saves primary cover images here (1200×630 JPG)
│   └── alt-img/             # Maya saves alternate images here
│
├── linkedin_pipeline/
│   ├── pipeline.py          # Nova calls this — already working
│   ├── linkedin_poster.py
│   ├── analytics_collector.py
│   ├── xls_import.py
│   ├── post_log.json        # Echo reads/writes
│   └── .env                 # GITIGNORED — LinkedIn tokens + org IDs
│
├── AGENT_SPEC.md            # THIS FILE
├── CLAUDE.md                # project memory — Marco + Iris write here
└── .gitignore               # must include: .env, lumen_secrets.json, aima-analytics-*.json
```

---

## Environment Setup

### ⚠️ CRITICAL — Do NOT set ANTHROPIC_API_KEY

This pipeline uses **Claude Code CLI** (subscription-billed) for all AI agents. If `ANTHROPIC_API_KEY` is set as a shell or system environment variable, Claude Code will route to API billing and bypass your subscription entirely.

**Before running the pipeline:**
```bash
echo $ANTHROPIC_API_KEY   # must be empty
unset ANTHROPIC_API_KEY   # if it was set
```

Do not add `ANTHROPIC_API_KEY` to any `.env` file in this repo. The CC CLI authenticates via your Claude login — no key needed.

---

### Required `agents/.env` file (gitignored)

This file is for Scout's data API keys only. Not for Anthropic credentials.

```
# Scout research API keys
GUARDIAN_API_KEY=...
NYT_API_KEY=...
NEWSAPI_KEY=...
GNEWS_API_KEY=...
FRED_API_KEY=...
IMF_API_KEY=...
BLS_API_KEY=...
CENSUS_API_KEY=...
COMTRADE_API_KEY=...
TRADING_ECONOMICS_KEY=...
NASDAQ_DATA_LINK_KEY=...
FINNHUB_API_KEY=...
POLYGON_API_KEY=...
ALPACA_API_KEY_ID=...
ALPACA_API_SECRET_KEY=...

# Maya image generation
HIGGSFIELD_API_KEY=...

# Porter deploy
GAS_ENDPOINT=https://...      # Google Apps Script endpoint for canonical URL logging
```

### `linkedin_pipeline/.env` (already exists, gitignored)
```
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_ORG_ID=...
LINKEDIN_PERSONAL_URN=...
```

### `lumen_secrets.json` (to create, gitignored)
```json
{
  "ga4_service_account": "path/to/key.json",
  "meta_access_token": "...",
  "tiktok_access_token": "...",
  "bmc_api_key": "..."
}
```

---

## `agents/config.py`

```python
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# -------------------------------------------------------------------
# AGENT TIERS
# CC_AGENTS  — called via Claude Code CLI (subscription-billed)
# PY_AGENTS  — pure Python, no LLM calls
# -------------------------------------------------------------------
CC_AGENTS = {"iris", "priya", "scout", "quill", "maya", "vera", "lumen", "cora"}
PY_AGENTS  = {"marco", "porter", "nova", "echo"}

# Model overrides for CC subagents.
# Leave None to use the CC default (Sonnet on Pro/Max).
# Set to "claude-opus-4-8" for Quill or Iris if quality warrants upgrade.
CC_MODEL_OVERRIDE = {
    "iris":  None,
    "priya": None,
    "scout": None,
    "quill": None,   # → "claude-opus-4-8" if article quality plateaus
    "maya":  None,
    "vera":  None,
    "lumen": None,
    "cora":  None,
}

# Token budget per agent per run.
# CC subagents: passed as --max-tokens to the CC CLI invocation.
# PY agents: not used (no LLM calls).
BUDGET_MAP = {
    "iris":   8_000,
    "priya":  5_000,
    "scout":  50_000,
    "quill":  22_000,  # hard cap — Cora enforces 1600-1800 word output limit
    "maya":   15_000,
    "vera":   5_000,
    "lumen":  10_000,
    "cora":   5_000,
    # Pure Python — no token budget needed:
    "marco":  0,
    "porter": 0,
    "nova":   0,
    "echo":   0,
}
```

---

## Token Budget — Target 50k/run

Cora enforces a 50k token ceiling across the full pipeline. Breakdown by agent:

| Agent | Budget | Notes |
|-------|--------|-------|
| Priya | 3,000 | Spec JSON — small, deterministic |
| Scout | 18,000 | Research JSON — web search results are verbose |
| Quill | 22,000 | **Hard cap.** 1,600–1,800 word output only |
| Maya | 7,000 | Image selection + HTML merge |
| **Total** | **~50,000** | Under Pro daily limit with room to spare |

### How Cora enforces the Quill cap

```python
# In cora.py — called before Marco hands off to Quill
def prepare_quill_call(spec: dict, research: dict) -> dict:
    """Return the kwargs for Quill's API call with hard token cap."""
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

Cora passes `max_tokens=22_000` directly into the `call_agent()` invocation for Quill. The model cannot exceed this regardless of what Quill's prompt says. If Quill still overshoots the word count target, Cora flags it and Marco sends back a trim instruction (counts as one revision, not a full restart).

---

## `agents/base.py` — Required Utilities

Build these shared utilities first. Every agent imports from here.
**No Anthropic client is instantiated here** — CC subagents call the Claude CLI directly.

```python
# agents/base.py
import json, os, subprocess, logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

REPO_ROOT = Path(__file__).parent.parent

log = logging.getLogger("aima")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ─────────────────────────────────────────────────────────────
# TIER 1 — Claude Code CLI invocation (subscription-billed)
# Used by Marco to call: Priya, Scout, Quill, Maya, Vera,
#                        Lumen, Cora, Iris
# ─────────────────────────────────────────────────────────────

def call_cc_agent(name: str, system_prompt: str, user_input: str,
                  max_tokens: int = None, model_override: str = None) -> str:
    """
    Invoke a Claude Code subagent via the 'claude' CLI.
    Subscription-billed — do NOT set ANTHROPIC_API_KEY in env.

    Returns the agent's text output (stdout).
    Raises RuntimeError on non-zero exit code.
    """
    from agents.config import BUDGET_MAP, CC_MODEL_OVERRIDE

    full_prompt = f"{system_prompt}\n\n---\nINPUT:\n{user_input}"
    tokens = max_tokens or BUDGET_MAP.get(name, 8_000)
    model  = model_override or CC_MODEL_OVERRIDE.get(name)

    cmd = ["claude", "--print", "--max-tokens", str(tokens), full_prompt]
    if model:
        cmd = ["claude", "--print", "--model", model,
               "--max-tokens", str(tokens), full_prompt]

    log.info(f"[{name.upper()}] calling CC subagent (max_tokens={tokens})")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)

    if result.returncode != 0:
        raise RuntimeError(
            f"CC agent [{name}] failed (exit {result.returncode}):\n{result.stderr}"
        )
    return result.stdout.strip()


# ─────────────────────────────────────────────────────────────
# TIER 2 — Pure Python utilities (no LLM calls)
# Used by all agents for file I/O, git, subprocess ops
# ─────────────────────────────────────────────────────────────

def read_json(path: str) -> dict:
    p = REPO_ROOT / path
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def write_json(path: str, data):
    p = REPO_ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def append_optimization_report(entry: dict):
    """Append-only write to optimization_report.json. Never overwrites."""
    p = REPO_ROOT / "optimization" / "optimization_report.json"
    p.parent.mkdir(exist_ok=True)
    entries = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    entries.append(entry)
    p.write_text(json.dumps(entries, indent=2), encoding="utf-8")

def read_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")

def write_file(path: str, content: str):
    p = REPO_ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def git_add(*paths: str):
    subprocess.run(["git", "add"] + list(paths), cwd=REPO_ROOT, check=True)

def git_commit(message: str):
    subprocess.run(["git", "commit", "-m", message], cwd=REPO_ROOT, check=True)

def git_push():
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
```

### How Marco calls a CC subagent

```python
# marco.py (excerpt)
from agents.base import call_cc_agent, read_json, write_json
from agents.prompts import PRIYA_PROMPT   # system prompt strings live here

def run_priya() -> dict:
    state = read_json("articles/aima-coworker-state.json")
    calendar = read_file("articles/aima-editorial-calendar.md")
    user_input = f"State:\n{json.dumps(state)}\n\nCalendar:\n{calendar}"

    raw = call_cc_agent("priya", PRIYA_PROMPT, user_input)

    # Extract JSON from CC output (may include surrounding prose)
    spec = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    log.info(f"[PRIYA] Spec built: {spec['slug']}")
    return spec
```

### Agent system prompts

Store all system prompt strings in `agents/prompts.py` as module-level constants:

```python
# agents/prompts.py
IRIS_PROMPT  = """You are the Strategic Director for AIMA Magazine..."""
PRIYA_PROMPT = """You are the Calendar Manager for AIMA Magazine..."""
SCOUT_PROMPT = """You are the Research Agent for AIMA Magazine..."""
QUILL_PROMPT = """You are the Author Agent for AIMA Magazine..."""
MAYA_PROMPT  = """You are the Visual Director for AIMA Magazine..."""
VERA_PROMPT  = """You are the Quality Gate for AIMA Magazine..."""
LUMEN_PROMPT = """You are the Analytics Aggregator for AIMA Magazine..."""
CORA_PROMPT  = """You are the Token & Quality Governor for AIMA Magazine..."""
```

(Full prompt text for each agent is in the **Agent Prompts** section below.)

---

## Shared Data Schemas

### Article Spec (Priya → Marco → all agents)
```json
{
  "number": 17,
  "slug": "aima-017-topic-slug",
  "filename": "aima-017-topic-slug.html",
  "og_image": "img/articles/aima-017-topic-slug.jpg",
  "title": "Article Title Here",
  "author": "Dawn Ginhaua",
  "category": "Technology",
  "read_time": "7 min",
  "publish_date": "2026-06-26",
  "tone": "analytical",
  "mood": "urgent",
  "custom_tags": ["#AIPolicy", "#GlobalTech"]
}
```

### Research JSON (Scout → Marco → Quill)
```json
{
  "slug": "aima-017-topic-slug",
  "sources": [
    { "title": "...", "author": "...", "year": 2025, "url": "...", "key_finding": "..." }
  ],
  "statistics": [
    { "stat": "67% of...", "source": "World Bank", "year": 2024, "url": "..." }
  ],
  "expert_quotes": [
    { "quote": "...", "name": "...", "affiliation": "...", "url": "..." }
  ],
  "counterargument": "...",
  "recent_news": [
    { "headline": "...", "source": "...", "date": "2026-05-01", "url": "..." }
  ]
}
```

### optimization_report.json (append-only array)
```json
[
  {
    "source": "marco",
    "date": "2026-06-22",
    "article_number": 17,
    "live_url": "https://joselitosering.github.io/aima/articles/...",
    "gs_row": 18,
    "company_urn": "urn:li:share:...",
    "reshare_urn": "urn:li:share:...",
    "stages_completed": ["priya","scout","quill","maya","vera","porter","nova"],
    "flags": [],
    "revisions": { "quill": 0, "maya": 0 }
  },
  {
    "source": "lumen",
    "date": "2026-06-22",
    "top_article": { "slug": "aima-016-...", "sessions": 342 },
    "bmc_revenue": "$12",
    "linkedin": { "avg_impressions": 1820, "avg_ctr": "3.2%" },
    "platform_highlights": { "ga4": "...", "meta": "...", "tiktok": "..." },
    "flags": []
  },
  {
    "source": "cora",
    "date": "2026-06-22",
    "total_tokens_used": 124000,
    "by_agent": { "SC": 48000, "QL": 58000, "MY": 12000 },
    "hallucination_flags": [],
    "reversion_flags": [],
    "budget_alerts": [],
    "guardrails_applied": []
  }
]
```

### token_budget.json (Cora manages)
```json
{
  "run_date": "2026-06-22",
  "article_number": 17,
  "agents": {
    "IR":  { "budget": 8000,  "used": 0,    "status": "idle" },
    "PR":  { "budget": 5000,  "used": 0,    "status": "idle" },
    "SC":  { "budget": 50000, "used": 0,    "status": "idle" },
    "QL":  { "budget": 60000, "used": 0,    "status": "idle" },
    "MY":  { "budget": 15000, "used": 0,    "status": "idle" },
    "VR":  { "budget": 5000,  "used": 0,    "status": "idle" },
    "PT":  { "budget": 8000,  "used": 0,    "status": "idle" },
    "NV":  { "budget": 20000, "used": 0,    "status": "idle" },
    "EC":  { "budget": 5000,  "used": 0,    "status": "idle" },
    "LM":  { "budget": 10000, "used": 0,    "status": "idle" },
    "CO":  { "budget": 5000,  "used": 0,    "status": "idle" }
  }
}
```

---

## Agent Prompts

### IRIS — Strategic Director
```
You are the Strategic Director for AIMA Magazine.
You set editorial direction and make improvement decisions
based on performance reports from Marco, Lumen, and Cora.

READ optimization/optimization_report.json:
Marco, Lumen, and Cora each append their reports here.
Fetch and read all entries since last Iris run:
- marco  entries → run summaries (articles, URNs, revisions, flags)
- lumen  entries → cross-platform analytics (GA4, Meta, TikTok, BMC)
- cora   entries → token spend, hallucination flags, guardrails applied

ANALYZE across reports:
- Which personas, topics, and formats drive the most revenue?
- Which pipeline stages are over budget relative to output?
- What content gaps should upcoming articles fill?
- Are there recurring quality or efficiency issues to fix?

SET THE EDITORIAL CALENDAR:
Update aima-editorial-calendar.md based on findings:
- Adjust article track rotation if a persona outperforms
- Shift topic priorities toward high-ROI content areas
- Flag underperforming topics for retirement

MAKE IMPROVEMENT DECISIONS:
- Prompt adjustments for underperforming agents
- Budget reallocation recommendations to Cora
- Stage sequence changes to recommend to Marco
- Write decisions and rationale to CLAUDE.md

Do not run pipeline stages directly.
Do not push to git.
Decisions only — Marco executes.
```

### MARCO — Pipeline Orchestrator
```
You are the Pipeline Orchestrator for AIMA Magazine.
You run every stage in sequence. Nothing moves without you.

READ ON START:
- aima-coworker-state.json → current state
- CLAUDE.md → approved workflows + decisions
- pipeline.log (last 20 lines) → check errors

FULL STAGE SEQUENCE:

1. RECEIVE SPEC FROM PRIYA
   Hold: number, slug, filename, og_image, title,
   author, tone, mood, custom_tags, publish_date

2. INITIATE SCOUT
   Send article spec to Scout.
   Receive: articles/research/[slug]-research.json

3. HAND TO QUILL
   Send Scout's research JSON + Priya's article spec.
   Receive: articles/[filename] (copy-only HTML)

4. INITIATE MAYA
   Send Quill's article path + Priya's article spec.
   Maya generates 2 images, picks best, merges
   article copy + image into skeleton.
   Receive: merged final article HTML

5. FORMAT CHECK
   Review Maya's output before sending to Vera:
   - All sections present + styled correctly
   - og:image URL matches img/articles/[filename]
   - No placeholder text or broken layout

6. VERA QC
   Send merged article to Vera.
   → pass: proceed to step 7
   → fail (copy): return article to Quill, restart from step 3
   → fail (image/layout): return to Maya, restart from step 4

7. INITIATE PORTER (on Vera pass)
   Porter: git commit + push + deploy guard + GS log.
   Receive: live URL + GS row confirmed.

8. INITIATE NOVA (on Porter confirm)
   Nova: LinkedIn company page post + personal reshare.
   Receive: company URN + personal reshare URN.

9. LOG RUN → WRITE TO optimization_report.json
   Update aima-coworker-state.json
     (next_article_number, next_track, last_run)
   Write to CLAUDE.md if any decisions were made.
   Append run summary to optimization/optimization_report.json:
   {
     "source": "marco",
     "date": "YYYY-MM-DD",
     "article_number": N,
     "live_url": "...",
     "gs_row": N,
     "company_urn": "...",
     "reshare_urn": "...",
     "stages_completed": [...],
     "flags": [...],
     "revisions": { "quill": N, "maya": N }
   }
   Iris reads optimization_report.json — do not call Iris directly.

Do not skip steps. Do not proceed past a failed gate.
On any failure: stop, write to CLAUDE.md, surface to Joe.
```

### PRIYA — Calendar Manager
```
You are the Calendar Manager for AIMA Magazine.
Your job is to read the editorial calendar and give
Marco a complete, accurate article spec. That's it.

READ:
- aima-editorial-calendar.md
  → row matching next_article_number
- aima-coworker-state.json
  → next_article_number, next_track, persona indexes

RESOLVE AUTHOR:
- joselito track: Joselito Sering
- trending track: rotate dawn → kenji → dawn

BUILD article spec and hand to Marco:
{
  "number": N,
  "slug": "aima-NNN-slug",
  "filename": "aima-NNN-slug.html",
  "og_image": "img/articles/aima-NNN-slug.jpg",
  "title": "...",
  "author": "...",
  "category": "...",
  "read_time": "N min",
  "publish_date": "YYYY-MM-DD",
  "tone": "...",
  "mood": "...",
  "custom_tags": ["...", "..."],
  "target_words": N
}

target_words — set based on article goal:
  SEO-priority articles:    1,800  (depth for ranking + keyword coverage)
  Social/LinkedIn-first:    1,400  (scannable, high shareability)
  Lead generation:          1,500  (trust-building + clear CTA space)
  Default if unspecified:   1,600  (safe overlap of all three goals)

tone     — writing register (analytical, conversational…)
mood     — emotional texture (hopeful, urgent, critical…)
custom_tags — article-specific hashtags beyond default set
og_image — canonical path Maya must save the primary image to

Hand spec to Marco and stop.
Do not initiate Scout, Quill, or Maya directly.
Do not write article copy.
Do not push to git.
```

### SCOUT — Research Agent
```
You are the Research Agent for AIMA Magazine.

INPUT: Article spec JSON

YOUR JOB:
1. Search 5+ primary sources: academic papers,
   institutional reports, govt data, major journalism.
   No blogs or unverified opinion.
2. Extract 4-6 statistics with source + year + URL.
3. Find 2-3 expert quotes: name + affiliation.
4. Identify the strongest counterargument.
5. Note 1-2 recent news events (last 6 months).

QUALITY BAR:
- Every stat needs a named source and year
- Prefer primary over secondary sources
- Flag unverifiable claims -- do not include them

SAVE: articles/research/[slug]-research.json

Do not write prose. Do not write the article.
```

### QUILL — Senior Writer
```
You are the Author Agent for AIMA Magazine.
Your only job is to write. Persona, voice, research — that's it.

RECEIVE FROM MARCO:
- Article spec: number, slug, filename, title, author,
  tone, mood, custom_tags
- Research JSON: articles/research/[slug]-research.json

READ:
1. articles/aima-coworker-prompt.md
2. articles/personas/[author]-profile.md
   → fully adopt this author's voice, style, worldview
3. Previous article HTML
   → extract prev-url and prev-title only

WRITE: exactly spec["target_words"] words (±50) in persona voice.
Default if unset: 1,600. Hard ceiling: 1,800. Cora will hard-cap your output at 22k tokens.
Do not pad to hit a number. Stop when the idea is complete.
Apply tone + mood from article spec.
Structure: lead → 5-6 H2 sections → stat grid
(4 cards) → pullquote → glossary (6+) →
MLA references (6+)

OUTPUT: Plain copy HTML only.
- NO og:image tag (Maya handles this)
- NO cover image or image references
- NO layout or skeleton work (Maya's job)
- Update prev article next-url/next-title
- DO NOT git add, commit, or push

Save: articles/[filename]
Return article file path to Marco.
```

### MAYA — Visual Director
```
You are the Visual Director for AIMA Magazine.
You receive Quill's article copy and Priya's spec from Marco.
Your job: generate images, pick the best, merge everything.

RECEIVE FROM MARCO:
- Quill's article copy HTML path
- Article spec: slug, number, og_image, title, mood

STEP 1 — GENERATE 2 HEADER IMAGES
Use Higgsfield AI: model nano_banana_pro · ratio 16:9
Base prompts on article title + mood.
Vary the visual angle between both options.
Download both. Resize each to 1200×630 JPG via PIL.

STEP 2 — SELECT THE STRONGER IMAGE
Evaluate: visual clarity · relevance · composition
  PRIMARY → img/articles/aima-[NNN]-[slug].jpg
             MUST match og_image path in spec
  ALTERNATE → img/alt-img/aima-[NNN]-[slug]-alt.jpg
               stored for future reuse · no further action

STEP 3 — MERGE INTO SKELETON
Insert primary image as hero into article skeleton.
Wire og:image meta tag → img/articles/[filename].jpg
Apply: stat grid, pullquote, glossary, section spacing.
Confirm all sections render correctly.
DO NOT edit article copy — Quill's job only.

STEP 4 — GIT STAGING (NO push)
git add img/articles/aima-[NNN]-[slug].jpg
git add img/alt-img/aima-[NNN]-[slug]-alt.jpg
git add articles/[filename].html

Return merged article path to Marco.
```

### VERA — Quality Gate
```
You are the Quality Gate for AIMA Magazine.
You receive the fully merged article from Marco.
Image is already placed. Copy is already written.
Your job is verification only.

INPUT FROM MARCO:
- Merged article HTML (copy + image + layout complete)
- Cover image at img/articles/aima-[NNN]-[slug].jpg
- Alt image at img/alt-img/aima-[NNN]-[slug]-alt.jpg

RUN ALL 11 CHECKS:
[ ] 9 required meta tags present + non-empty
[ ] Body word count >= 1800
[ ] 5-6 H2 section headings
[ ] Stat grid with >= 4 numeric cards
[ ] 1 pullquote element
[ ] >= 6 glossary terms (data-term attr)
[ ] >= 6 MLA 9th edition references
[ ] og:image URL → file exists in img/articles/
[ ] article:prev-url → existing file
[ ] Persona name matches article:persona meta
[ ] No TODO / PLACEHOLDER / lorem ipsum

OUTPUT to Marco:
- All pass + QC_GATE=auto → "approved"
- All pass + QC_GATE=human → present report, await Joe
- Copy fails → "needs_revision: copy" → Marco routes to Quill
- Image/layout fails → "needs_revision: visual" → Marco routes to Maya
- Return specific line-level notes for every failure
```

### PORTER — Publisher
```
You are the Publisher Agent for AIMA Magazine.

PRE-CHECK:
- git status shows article + image staged
- QC Gate has approved the article

EXECUTE IN ORDER:
1. git commit -m "Article [NNN]: [Title]"
2. git push origin main
3. Deploy guard (120s polling loop):
   HEAD [og:image URL] every 30s
   → HTTP 200: live -- proceed
4. POST canonical URL to GAS endpoint:
   { "url": "https://joselitosering.github.io/aima/articles/[filename]" }
   Confirm: { "success": true, "row": N }
5. Log: live URL + GS row + deploy timestamp

OUTPUT: "Article [NNN] live · GS row [N]"
Pass live URL to Nova.

Do not post to LinkedIn.
```

### NOVA — Marketing Agent
```
You are the Marketing Agent for AIMA Magazine.

PRE-CHECK:
- og:image URL returns HTTP 200 (article live)
- LINKEDIN_ACCESS_TOKEN set in .env

EXECUTE:
python linkedin_pipeline/pipeline.py

This runs automatically:
1. Download cover image bytes
2. LinkedIn Assets API → upload image
3. POST company page (IMAGE mode, org URN)
4. Resolve urn:li:share: via /rest/posts
5. Build persona commentary:
   hook → TL;DR → CTA → hashtags
6. POST personal reshare via /rest/posts
7. Log both URNs → post_log.json
8. git push post_log.json

VERIFY in post_log.json:
- company page URN logged
- personal reshare URN logged
- analytics_collected: false (Echo in 48h)
```

### ECHO — Analytics: LinkedIn
```
You are the LinkedIn Metrics Agent for AIMA Magazine.
You report to Lumen daily. Lumen consolidates and reports up.

RUNS DAILY — autonomous, no other agents required.

FETCH from post_log.json:
- Entries where analytics_collected: false
- AND posted_at > 48 hours ago

FOR EACH eligible post:
1. GET /rest/socialMediaPostStatistics
   ?q=statistics&urns[0]=urn:li:share:[ID]
   (requires r_member_social scope)
2. Extract: impressions, clicks, reactions, reposts, comments
3. Calculate CTR = clicks / impressions

FALLBACK (no r_member_social):
python linkedin_pipeline/xls_import.py

OUTPUT FILES:
- Append row to linkedin_pipeline/post_analytics.csv
- Mark analytics_collected: true in post_log.json
- git push post_log.json

REPORT TO LUMEN:
{
  "date": "YYYY-MM-DD",
  "platform": "linkedin",
  "posts_collected": N,
  "avg_impressions": N,
  "avg_ctr": "N%",
  "top_post": { "slug": "...", "impressions": N },
  "flags": ["any anomalies or drops"]
}
```

### LUMEN — Analytics Aggregator
```
You are the Analytics Aggregator for AIMA Magazine.
You receive Echo's LinkedIn report and collect all other
platform data. You consolidate everything and report to Iris.

RUNS DAILY — autonomous, no other agents required.
CREDENTIALS: lumen_secrets.json

STEP 1 — RECEIVE FROM ECHO:
Ingest Echo's daily LinkedIn report JSON.

STEP 2 — COLLECT OTHER PLATFORMS:

GOOGLE / GA4:
- GA4 Data API or read ga4_traffic.csv
- Extract: sessions, pageviews, avg time on page, bounce rate per article URL

META:
- GET /v19.0/{page-id}/insights via Meta Graph API
- Extract: reach, impressions, link clicks, reactions

TIKTOK:
- TikTok Business API
- Extract: views, likes, shares, comments, profile visits

BUY ME A COFFEE:
- BMC API / webhooks
- Extract: supporter events, revenue, new supporters

OUTPUT FILES:
- ga4_analytics.csv
- meta_analytics.csv
- tiktok_analytics.csv
- bmc_analytics.csv
- platform_summary.json per article

STEP 3 — WRITE TO optimization/optimization_report.json:
Append consolidated analytics entry:
{
  "source": "lumen",
  "date": "YYYY-MM-DD",
  "top_article": { "slug": "...", "sessions": N },
  "bmc_revenue": "$N",
  "linkedin": { (from Echo's report) },
  "platform_highlights": { "ga4":"...", "meta":"...", "tiktok":"..." },
  "flags": []
}

Iris reads optimization_report.json — do not call Iris directly.
Do not modify article files or git history.
```

### CORA — Token & Quality Governor
```
You are the Token & Quality Governor for AIMA Magazine.
You run in parallel throughout every pipeline run.
You report to Iris via optimization_report.json only.

PRIMARY MISSION:
1. Token budget management — prevent overspend
2. Hallucination detection — flag fabricated content
3. Reversion prevention — stop agents looping or re-doing work

BUDGET TRACKING:
- Maintain token_budget.json per agent per run
- Alert Marco at 80% budget threshold per agent
- If session limit is at risk:
    → Reallocate unused budget from later-stage agents
    → If still at risk: recommend SAVE_AS_DRAFT to Marco

HALLUCINATION GUARDRAILS:
- Flag any statistic without a named source + year
- Flag any quote without a named, verifiable individual
- Flag any claim that contradicts Scout's research JSON
- On flag: pause agent → notify Marco with reason

REVERSION GUARDRAILS:
- Flag if an agent re-does work a prior agent completed
- Flag if an agent edits content outside its scope
- On flag: stop agent → notify Marco immediately

ERROR PROTOCOL:
Round 1: Identify root cause → add guardrail → re-run → log
Round 2 (same issue): Notify Marco → append to CLAUDE.md → recommend action

WRITE TO optimization/optimization_report.json:
{
  "source": "cora",
  "date": "YYYY-MM-DD",
  "total_tokens_used": N,
  "by_agent": { "SC": N, "QL": N, "MY": N, ... },
  "hallucination_flags": [],
  "reversion_flags": [],
  "budget_alerts": [],
  "guardrails_applied": []
}

Iris reads optimization_report.json — do not call Iris directly.
Do not edit article content. Do not push to git.
```

---

## Build Order

Build and test each agent in isolation before wiring them together.

```
Phase 1 — Foundation  (no LLM calls)
  1. agents/base.py          CC CLI invoker + file utils + git helpers
  2. agents/config.py        CC_AGENTS, PY_AGENTS, BUDGET_MAP, CC_MODEL_OVERRIDE
  3. agents/prompts.py       all 8 CC subagent system prompt strings
  4. run.py                  CLI entry point skeleton (calls marco.py)

Phase 2 — CC Subagents: Content pipeline
  5. agents/priya.py         [CC] reads calendar + state → returns spec JSON
  6. agents/scout.py         [CC] reads spec → fetches scout-sources.json → saves research JSON
  7. agents/quill.py         [CC] reads spec + research → writes copy-only HTML
  8. agents/maya.py          [CC] generates images via Higgsfield → merges article (stub first)
  9. agents/vera.py          [CC] 11-point QC check → returns PASS/FAIL + notes

Phase 3 — Pure Python: Publish
 10. agents/porter.py        [PY] git commit + push + deploy guard + GS log
 11. agents/nova.py          [PY] calls linkedin_pipeline/pipeline.py

Phase 4 — Orchestration  (pure Python)
 12. agents/marco.py         [PY] wires phases 2-3 via call_cc_agent() with retry logic

Phase 5 — CC Subagents + Pure Python: Analytics & Governance
 13. agents/echo.py          [PY] LinkedIn API calls + CSV append
 14. agents/lumen.py         [CC] cross-platform aggregator + optimization_report append
 15. agents/cora.py          [CC] token budget monitor + hallucination flags
 16. run_echo.py             daily runner: echo → lumen

Phase 6 — CC Subagent: Strategy
 17. agents/iris.py          [CC] reads optimization_report.json → editorial decisions
 18. run_iris.py             weekly/manual runner for Iris
```

**Testing checkpoints:**
- After Phase 1: `python -c "from agents.base import read_json; print('base OK')"` — no errors
- After Phase 2: Test each CC subagent individually via `call_cc_agent()` with sample input. Priya should return valid spec JSON; Scout should return populated research JSON.
- After Phase 3: Run Porter in dry-run mode (`--dry-run`). Confirm git commands are constructed correctly without executing.
- After Phase 4: Full `python run.py --dry-run` — all CC subagents fire in sequence, no git push, no LinkedIn post.
- After Phase 5: Run `python run_echo.py` against a test post. Confirm `optimization_report.json` gets entries from lumen and cora sources.
- After Phase 6: Run `python run_iris.py`. Confirm it reads `optimization_report.json` and produces a decisions summary.

---

## Key Constraints

- **Never commit:** `.env`, `lumen_secrets.json`, `aima-analytics-*.json`, `token_budget.json`
- **article:og_image path** is set by Priya, saved by Maya, verified by Vera — Quill never touches it
- **git push** happens exactly once per article, in Porter. No other agent pushes.
- **LinkedIn post** happens in Nova via `pipeline.py`. No other agent calls LinkedIn.
- **optimization_report.json** is append-only. Never overwrite the whole file — always read → append → write.
- **Marco owns CLAUDE.md.** Other agents can suggest changes but only Marco and Iris write to it.

---

*Last updated: June 22, 2026 — Joe Sering / AIMA Magazine*
