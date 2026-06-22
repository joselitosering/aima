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
