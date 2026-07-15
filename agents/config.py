import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# -------------------------------------------------------------------
# AGENT TIERS
# CC_AGENTS  — called via Claude Code CLI (subscription-billed)
# PY_AGENTS  — pure Python, no LLM calls
# -------------------------------------------------------------------
CC_AGENTS = {"iris", "priya", "scout", "trend_scout", "maya", "vera", "lumen", "cora"}
PY_AGENTS  = {"marco", "porter", "nova", "echo", "quill"}  # quill demoted 2026-07-14 — verification gate, no LLM

# Model overrides for CC subagents.
# Leave None to use the CC default (Sonnet on Pro/Max).
# Set to "claude-opus-4-8" for Quill or Iris if quality warrants upgrade.
CC_MODEL_OVERRIDE = {
    "iris":  None,
    "priya": None,
    "scout": None,
    "trend_scout": None,
    "maya":  None,
    "vera":  None,
    # lumen: model is chosen at runtime in agents/lumen.py by credential state —
    # "claude-haiku-4-5" for the mechanical no-secrets path (GA4 + LinkedIn only),
    # CC-default (Sonnet) below for the full multi-platform synthesis path.
    "lumen": None,
    "cora":  None,
}

# Token budget per agent per run.
# These are realistic ceilings recalibrated 2026-07-13 from measured actuals
# on articles #19–#20 after the QL token explosion investigation (article #20:
# TS=143k, PR=42k, SC=450k, QL=2.9M[outlier], MY=694k, VR=604k).
# Quill demoted to pure Python 2026-07-14 (see agents/quill.py) — no longer
# in this budget at all; Writer now owns word-count enforcement directly.
# PY agents: not used (no LLM calls).
BUDGET_MAP = {
    "iris":   50_000,
    "priya":  50_000,
    "scout":  500_000,
    "trend_scout": 150_000,  # topic selection — feeds/APIs + dedup check
    "writer": 300_000,  # free-form authoring call in both full pipeline and Writer
                         # batch. Restored two-call arch (2026-07-13, reverts Direction
                         # B). Measured ~253k tok for a Dawn article — budget 300k.
    "maya":   750_000,
    "vera":   650_000,
    "lumen":  10_000,
    "cora":   5_000,
    # Pure Python — no token budget needed:
    "marco":  0,
    "porter": 0,
    "nova":   0,
    "echo":   0,
    "quill":  0,  # demoted 2026-07-14 — verification gate, no LLM call
}

# Hard cap on agentic tool-use turns per CC agent call (--max-turns N).
# Primary control against token explosions (article #20 QL: 57 turns → 2.9M tok).
# Quill no longer appears here — demoted to pure Python 2026-07-14, no CC
# call to cap. Writer gets 15: it may need extra tool turns for file reads +
# write + verify. Added 2026-07-13. To disable a cap for a specific call,
# pass max_turns=None explicitly to call_cc_agent() — it will still fall
# through to this map, so pass max_turns=0 or add a guard to bypass (not
# recommended).
MAX_TURNS_MAP = {
    "iris":       15,
    "priya":      15,
    "scout":      15,
    "trend_scout": 15,
    "maya":       15,
    "vera":       15,
    "lumen":      15,
    "cora":       15,
}

# -------------------------------------------------------------------
# API MODEL ROUTING (OpenRouter) — added 2026-07-14
# Agents listed here call the direct OpenRouter API (base.call_api) instead of
# the `claude` CLI: ONE HTTP call, no Claude Code system-prompt/tool overhead,
# no agentic loop — ~$0-0.05 vs the ~$0.3-2 each cost via the CLI.
# NOT listed (scout, trend_scout, maya) stay on the CLI: scout/trend_scout need
# web-search tools; maya does an agentic file-write + git add. Requires
# OPENROUTER_API_KEY in agents/.env; without it, call_cc_agent falls back to the
# CLI for everyone (safe). Slugs are env-overridable (OPENROUTER_MODEL_*).
# NOTE: an agent is only safe here if its user_input INLINES all content — a
# prompt that says "Read this path" fails on the API (no tools).
# -------------------------------------------------------------------
_AUTHOR_MODEL   = os.environ.get("OPENROUTER_MODEL_AUTHOR",   "anthropic/claude-sonnet-5")
_RESEARCH_MODEL = os.environ.get("OPENROUTER_MODEL_RESEARCH", "anthropic/claude-sonnet-5:online")  # :online = web search
_EDITOR_MODEL   = os.environ.get("OPENROUTER_MODEL_EDITOR",   "openai/gpt-4o-mini")
_GATE_MODEL     = os.environ.get("OPENROUTER_MODEL_GATE",     "openai/gpt-4o-mini")  # Vera — reliable gating for ~$0
_JUDGE_MODEL    = os.environ.get("OPENROUTER_MODEL_JUDGE",    "openrouter/free")
# Fallback tried automatically (OpenRouter `models` array) when the primary
# model errors/churns/rate-limits. Sonnet is the quality safety net.
API_FALLBACK_MODEL = os.environ.get("OPENROUTER_MODEL_FALLBACK", "anthropic/claude-sonnet-5")
API_MODEL_MAP = {
    "joselito": _AUTHOR_MODEL, "dawn": _AUTHOR_MODEL, "kenji": _AUTHOR_MODEL,
    "scout": _RESEARCH_MODEL, "trend_scout": _RESEARCH_MODEL,   # Sonnet + web search
    "vera":   _GATE_MODEL,
    "cora":   _JUDGE_MODEL, "priya": _JUDGE_MODEL, "iris": _JUDGE_MODEL, "lumen": _JUDGE_MODEL,
}
# NOTE: maya is intentionally absent -> stays on the claude CLI (it does an
# agentic file-write + git add). Its skeleton merge was converted to PURE
# PYTHON 2026-07-14 (agents/maya_merge.py) — same move now applied to quill,
# which is absent here too: demoted to pure Python 2026-07-14
# (agents/quill.py), no LLM call of any kind, not CLI and not API.

# -------------------------------------------------------------------
# FULL-PIPELINE STAGE TOGGLES
# Source of truth: pipeline_config.json (written by the dashboard).
# Fallback: .env vars, then these all-on defaults.
# QC_GATE is a mode ("human" | "auto"); the rest are booleans.
# -------------------------------------------------------------------
PIPELINE_CONFIG_DEFAULTS = {
    "RESEARCH_ENABLED":  True,
    "WRITE_ENABLED":     True,
    "MAYA_ENABLED":      True,
    "QC_GATE":           "human",
    "PUBLISH_ENABLED":   True,
    "GS_ENABLED":        True,
    "MARKETING_ENABLED": True,
    "ANALYTICS_ENABLED": True,
    "LUMEN_ENABLED":     True,
    "CORA_ENABLED":      True,
}

PIPELINE_CONFIG_PATH = REPO_ROOT / "pipeline_config.json"


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def load_pipeline_config() -> dict:
    """Return the full-pipeline stage toggles.

    Priority: pipeline_config.json (dashboard) > .env vars > defaults.
    """
    cfg = dict(PIPELINE_CONFIG_DEFAULTS)

    # 1. Dashboard-owned JSON wins if present and parseable.
    if PIPELINE_CONFIG_PATH.exists():
        try:
            raw = json.loads(PIPELINE_CONFIG_PATH.read_text(encoding="utf-8"))
            for key in cfg:
                if key == "QC_GATE":
                    if raw.get("QC_GATE") in ("human", "auto"):
                        cfg["QC_GATE"] = raw["QC_GATE"]
                elif isinstance(raw.get(key), bool):
                    cfg[key] = raw[key]
            return cfg
        except Exception:
            pass  # fall through to env/defaults on malformed file

    # 2. Environment variables (documented in AGENT-WORKFLOW.md).
    for key in cfg:
        if key == "QC_GATE":
            v = os.environ.get("QC_GATE")
            if v in ("human", "auto"):
                cfg["QC_GATE"] = v
        else:
            cfg[key] = _env_bool(key, cfg[key])
    return cfg