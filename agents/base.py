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

# ─────────────────────────────────────────────────────────────
# DRY-RUN STUB MODE
# Set DRY_RUN = True in run.py when --dry-run is passed.
# call_cc_agent() returns stub responses — no real claude CLI
# calls, no tokens consumed. Validates orchestration only.
# ─────────────────────────────────────────────────────────────
DRY_RUN = False


def _build_dry_run_priya_spec() -> str:
    """Build Priya stub spec from state.json + existing article files."""
    state_path = REPO_ROOT / "articles" / "aima-coworker-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    number = int(state.get("next_article_number", 1))
    padded = str(number).zfill(3)

    import re as _re
    articles_dir = REPO_ROOT / "articles"
    matches = sorted(articles_dir.glob(f"aima-article-*-{padded}.html"),
                     key=lambda p: p.stat().st_size, reverse=True)
    if matches:
        filename = matches[0].name
        m = _re.match(r"aima-article-(.+)-\d{3}\.html", filename)
        slug = m.group(1) if m else f"article-{padded}"
    else:
        slug = f"article-{padded}"
        filename = f"aima-article-{slug}-{padded}.html"

    og_image = f"img/articles/aima-{padded}-{slug}.jpg"
    # Author comes from the calendar row's Author column (one canonical
    # sequence — next_track rotation retired 2026-07-02, DECISION-LOG.md).
    author = "Joselito Sering"
    cal = REPO_ROOT / "articles" / "aima-editorial-calendar.md"
    if cal.exists():
        for line in cal.read_text(encoding="utf-8").splitlines():
            if _re.match(rf"\s*\|\s*{number}\s*\|\s*[\d-]+\s*\|", line):
                cells = [c.strip() for c in line.split("|")]
                if len(cells) > 7 and cells[7]:
                    author = cells[7]
                break

    return json.dumps({
        "number": number,
        "slug": slug,
        "filename": filename,
        "og_image": og_image,
        "title": f"[DRY RUN] Article #{number}: {slug.replace('-', ' ').title()}",
        "author": author,
        "category": "AI Society",
        "read_time": "8 min",
        "publish_date": state.get("next_article_date", "2026-06-28"),
        "tone": "analytical",
        "mood": "thoughtful",
        "custom_tags": ["#AI", "#AIMA"],
        "target_words": 1600,
    })


_DRY_RUN_STUBS = {
    # priya: built dynamically — see call_cc_agent
    "scout": "",          # scout has its own cache check; fallback empty is fine
    "quill": "",          # quill reuses existing file when force_rewrite=False
    "maya":  "",          # maya checks file on disk; return value not used
    "vera":  "approved",  # always approve in dry-run
    "cora":  "dry_run_ok",
    "lumen": "dry_run_ok",
    "iris":  "dry_run_ok",
}

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
    from agents.config import CC_MODEL_OVERRIDE

    model = model_override or CC_MODEL_OVERRIDE.get(name)

    if _CLAUDE_BIN is None:
        raise RuntimeError(
            "claude CLI not found. Run 'where.exe claude' in PowerShell to diagnose. "
            "Install Claude Code or add it to your PATH."
        )

    # --dangerously-skip-permissions: CC agents need tools (WebSearch, Write, Bash)
    # and cannot respond to interactive permission prompts when stdin is piped.
    # Safe here — we control every agent's system prompt and user input.
    # --system-prompt sets the role; user_input is piped via stdin.
    cmd = [_CLAUDE_BIN, "--print", "--dangerously-skip-permissions",
           "--system-prompt", system_prompt]
    if model:
        cmd += ["--model", model]

    # ── Dry-run stub: skip real CC call entirely ─────────────
    if DRY_RUN:
        stub = _build_dry_run_priya_spec() if name == "priya" else _DRY_RUN_STUBS.get(name, "dry_run_ok")
        log.info(f"[{name.upper()}] DRY RUN — returning stub (no CC call)")
        return stub

    log.info(f"[{name.upper()}] calling CC subagent")
    try:
        result = subprocess.run(cmd, input=user_input, capture_output=True,
                                encoding="utf-8", cwd=REPO_ROOT, timeout=1800)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"CC agent [{name}] timed out after 1800s (30 min). "
            "Check Claude Code subscription status and network connectivity."
        )

    if result.returncode != 0:
        stdout_snippet = result.stdout[:500] if result.stdout else "(empty)"
        raise RuntimeError(
            f"CC agent [{name}] failed (exit {result.returncode}):\n"
            f"STDERR: {result.stderr or '(empty)'}\n"
            f"STDOUT (first 500): {stdout_snippet}"
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
