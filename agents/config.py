import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# -------------------------------------------------------------------
# AGENT TIERS
# CC_AGENTS  — called via Claude Code CLI (subscription-billed)
# PY_AGENTS  — pure Python, no LLM calls
# -------------------------------------------------------------------
CC_AGENTS = {"iris", "priya", "scout", "trend_scout", "quill", "maya", "vera", "lumen", "cora"}
PY_AGENTS  = {"marco", "porter", "nova", "echo"}

# Model overrides for CC subagents.
# Leave None to use the CC default (Sonnet on Pro/Max).
# Set to "claude-opus-4-8" for Quill or Iris if quality warrants upgrade.
CC_MODEL_OVERRIDE = {
    "iris":  None,
    "priya": None,
    "scout": None,
    "trend_scout": None,
    "quill": None,   # → "claude-opus-4-8" if article quality plateaus
    "maya":  None,
    "vera":  None,
    "lumen": None,
    "cora":  None,
}

# Token budget per agent per run (informational — for future --max-budget-usd mapping).
# PY agents: not used (no LLM calls).
BUDGET_MAP = {
    "iris":   8_000,
    "priya":  5_000,
    "scout":  50_000,
    "trend_scout": 12_000,  # topic selection only — not full research (that's Scout's 50k)
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
