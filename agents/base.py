import json
import os
import shutil
import subprocess
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

REPO_ROOT = Path(__file__).parent.parent

log = logging.getLogger("aima")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Resolve the claude CLI path once at import time.
# On Windows, subprocess cannot find executables via PATH without shell=True
# unless the full path is provided. shutil.which() resolves it correctly.
_CLAUDE_BIN = shutil.which("claude") or shutil.which("claude.cmd")
if _CLAUDE_BIN is None:
    log.warning(
        "claude CLI not found in PATH. "
        "Install Claude Code and ensure 'claude' is on your PATH."
    )


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
    model = model_override or CC_MODEL_OVERRIDE.get(name)

    cmd = ["claude", "--print", "--max-tokens", str(tokens), full_prompt]
    if model:
        cmd = ["claude", "--print", "--model", model,
               "--max-tokens", str(tokens), full_prompt]

    if _CLAUDE_BIN is None:
        raise RuntimeError(
            "claude CLI not found. Run 'where.exe claude' in PowerShell to diagnose. "
            "Install Claude Code or add it to your PATH."
        )

    # Replace "claude" with the resolved full path so Windows subprocess
    # can find it without needing shell=True.
    cmd[0] = _CLAUDE_BIN

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
