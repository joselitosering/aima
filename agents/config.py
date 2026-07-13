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
# QL is capped at 500k: with --max-turns 8 the 57-turn outlier cannot recur.
# PY agents: not used (no LLM calls).
BUDGET_MAP = {
    "iris":   50_000,
    "priya":  50_000,
    "scout":  500_000,
    "trend_scout": 150_000,  # topic selection — feeds/APIs + dedup check
    "writer": 20_000,   # standalone Writer batch only (Direction B: authoring cost
                         # lands in QL in the full pipeline — see quill.py).
    "quill":  500_000,  # authoring + editing merged (Direction B). Hard turn cap
                         # (MAX_TURNS_MAP below) prevents the 2.9M outlier; 500k is
                         # a safe ceiling for an 8-turn call writing ~1k-word article.
    "maya":   750_000,
    "vera":   650_000,
    "lumen":  10_000,
    "cora":   5_000,
    # Pure Python — no token budget needed:
    "marco":  0,
    "porter": 0,
    "nova":   0,
    "echo":   0,
}

# Hard cap on agentic tool-use turns per CC agent call (--max-turns N).
# This is the primary mechanical control against token explosions from runaway
# multi-turn loops (e.g. article #20 QL: 57 turns → 2.9M tokens / $2.52).
# Quill is set to 8: read 3 context files (1), write article (2), verify/fix
# length issues (3-4), handle edge cases (5-8). All other CC agents default 15.
# Added 2026-07-13. To disable a cap for a specific call, pass max_turns=None
# explicitly to call_cc_agent() — it will still fall through to this map,
# so pass max_turns=0 or add a guard to bypass (not recommended).
MAX_TURNS_MAP = {
    "quill":       8,
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
