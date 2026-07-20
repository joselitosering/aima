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

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
log = logging.getLogger("aima")
log.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)

# Persistent file logging — added 2026-07-04 after a scheduled run (schtasks,
# no stdout/stderr redirection) died silently mid-pipeline with zero record of
# why. Console-only logging is invisible once Task Scheduler's console window
# closes. This appends every run (interactive or scheduled) to pipeline.log so
# a crash is always diagnosable afterward. See CLAUDE.md / HANDOFF.md
# "Pipeline Scheduled-Run Silent Failure" for the incident this fixes.
if not any(isinstance(h, logging.FileHandler) for h in log.handlers):
    _file_handler = logging.FileHandler(REPO_ROOT / "pipeline.log", encoding="utf-8")
    _file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    log.addHandler(_file_handler)

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

# Maps call_cc_agent's `name` argument to the two-letter code used in
# token_budget.json. Added 2026-07-04 alongside real usage capture — see
# _record_token_usage(). Writer personas (joselito/dawn/kenji) all post to
# one "WR" bucket since token_budget.json tracks by pipeline stage, not by
# individual persona. Unmapped names fall back to their own upper-cased
# initials in _record_token_usage() rather than being silently dropped.
_AGENT_CODE_MAP = {
    "iris": "IR", "priya": "PR", "scout": "SC", "trend_scout": "TS",
    "quill": "QL", "maya": "MY", "vera": "VR", "lumen": "LM", "cora": "CO",
    "joselito": "WR", "dawn": "WR", "kenji": "WR",
}


def _record_token_usage(name: str, tokens: int, cost_usd: float | None):
    """Add real usage from one CC call into token_budget.json.

    Added 2026-07-04 — this is the fix for the gap Cora flagged CRITICAL on
    article #19: token_budget.json previously only ever had `used: 0`
    written by cora.init_budget(); nothing ever incremented it, because
    call_cc_agent() ran the CLI in plain-text (--print) mode, which returns
    no usage data at all. There is nothing to parse in that mode — the fix
    is capturing the numbers the CLI already reports in --output-format
    json (usage.input_tokens / output_tokens / cache_*_tokens,
    total_cost_usd — see https://code.claude.com/docs/en/headless), not a
    smarter guess. This function is best-effort: a failure here must never
    take down a pipeline run over an accounting nicety, so it swallows its
    own errors after logging.
    """
    code = _AGENT_CODE_MAP.get(name, name.upper()[:2])
    budget_path = REPO_ROOT / "token_budget.json"
    try:
        budget = json.loads(budget_path.read_text(encoding="utf-8")) if budget_path.exists() else {"agents": {}}
        agents = budget.setdefault("agents", {})
        entry = agents.setdefault(code, {"budget": 0, "used": 0, "status": "idle"})
        entry["used"] = entry.get("used", 0) + tokens
        cap = entry.get("budget", 0)
        entry["status"] = (
            "over_budget" if cap and entry["used"] > cap else
            "warning" if cap and entry["used"] / cap >= 0.8 else
            "used"
        )
        if cost_usd is not None:
            entry["last_call_cost_usd"] = cost_usd
            entry["cumulative_cost_usd"] = round(entry.get("cumulative_cost_usd", 0.0) + cost_usd, 6)
        budget_path.write_text(json.dumps(budget, indent=2), encoding="utf-8")
        log.info(f"[token] {code} +{tokens} tokens (call cost=${cost_usd if cost_usd is not None else '?'}) "
                 f"— cumulative used={entry['used']}" + (f"/{cap}" if cap else ""))
    except Exception as exc:
        log.warning(f"[token] could not record usage for {name} ({code}): {exc}")


def call_cc_agent(name: str, system_prompt: str, user_input: str,
                  max_tokens: int = None, model_override: str = None,
                  max_turns: int = None, single_shot: bool = False) -> str:
    """
    Invoke a Claude Code subagent via the 'claude' CLI.
    Subscription-billed — do NOT set ANTHROPIC_API_KEY in env.

    Returns the agent's text output (the CLI's `result` field).
    Raises RuntimeError on non-zero exit code.

    Runs with --output-format json (added 2026-07-04) so real per-call
    token usage and cost can be captured into token_budget.json via
    _record_token_usage() — previously this ran in plain --print text mode,
    which returns no usage data at all, so token_budget.json's `used` field
    was permanently stuck at 0 (flagged CRITICAL by Cora on article #19).

    max_turns: hard cap on agentic tool-use turns (--max-turns N passed to
    the CLI). Without a cap, a verbose agent can run 50+ turns and blow up
    cost via cache_read re-processing on every turn. Quill is capped at 8;
    most other agents at 15. Added 2026-07-13 after QL used 2.9M tokens /
    $2.52 on article #20 from ~57 tool turns. Caller can override per-call;
    otherwise the per-agent default from MAX_TURNS_MAP in config.py is used.
    """
    # ── Route to the direct OpenRouter API for agents that don't need CLI tools ──
    # (config.API_MODEL_MAP). ONE HTTP call, no Claude Code overhead/loop. Falls
    # through to the CLI below if there's no OPENROUTER_API_KEY or the agent isn't
    # mapped (scout/trend_scout/maya need CLI tools). single_shot/max_turns are
    # CLI-only concepts and simply don't apply on the API path.
    from agents.config import API_MODEL_MAP, API_FALLBACK_MODEL
    if os.environ.get("OPENROUTER_API_KEY") and name in API_MODEL_MAP:
        return call_api(name, system_prompt, user_input,
                        model=model_override or API_MODEL_MAP[name],
                        fallback=API_FALLBACK_MODEL)

    from agents.config import CC_MODEL_OVERRIDE, MAX_TURNS_MAP

    model = model_override or CC_MODEL_OVERRIDE.get(name)
    # Per-agent turn cap: caller can override; otherwise use the config map.
    turns = max_turns if max_turns is not None else MAX_TURNS_MAP.get(name)

    if _CLAUDE_BIN is None:
        raise RuntimeError(
            "claude CLI not found. Run 'where.exe claude' in PowerShell to diagnose. "
            "Install Claude Code or add it to your PATH."
        )

    # --dangerously-skip-permissions: CC agents need tools (WebSearch, Write, Bash)
    # and cannot respond to interactive permission prompts when stdin is piped.
    # Safe here — we control every agent's system prompt and user input.
    # --system-prompt sets the role; user_input is piped via stdin.
    # --output-format json: structured envelope with `result` (text) + `usage`
    # + `total_cost_usd` — see https://code.claude.com/docs/en/headless.
    # single_shot: ONE turn, NO tools — for agents that receive all content
    # inlined and return text/JSON directly (Cora, Quill, Vera). This avoids the
    # multi-turn agentic loop (Read file -> Read file -> Write file over 8-15
    # turns) that re-ingests the whole context every turn, which is what made
    # Cora burn 906K tokens and Quill 2.55M on a single article (2026-07-14).
    if single_shot:
        # ONE turn, tools NOT enabled: for agents that receive everything inlined
        # and return text/JSON. Do NOT pass --disallowedTools or --dangerously-
        # skip-permissions — with tools "present but denied" the model retries a
        # Write every turn and never emits text (error_max_turns). Plain -p with
        # --max-turns 1 makes it generate directly. This replaces the 8-15 turn
        # agentic loop that burned Cora 906K / Quill 2.55M tokens on ONE article.
        cmd = [_CLAUDE_BIN, "--print", "--output-format", "json",
               "--max-turns", "1",
               "--system-prompt", system_prompt]
    else:
        cmd = [_CLAUDE_BIN, "--print", "--dangerously-skip-permissions",
               "--output-format", "json",
               "--system-prompt", system_prompt]
        if turns is not None:
            cmd += ["--max-turns", str(turns)]
    if model:
        cmd += ["--model", model]

    # ── Dry-run stub: skip real CC call entirely ─────────────
    if DRY_RUN:
        stub = _build_dry_run_priya_spec() if name == "priya" else _DRY_RUN_STUBS.get(name, "dry_run_ok")
        log.info(f"[{name.upper()}] DRY RUN — returning stub (no CC call)")
        return stub

    log.info(f"[{name.upper()}] calling CC subagent (model={model or 'CC-default'})")
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

    raw_stdout = result.stdout.strip()
    try:
        payload = json.loads(raw_stdout)
        text_output = payload.get("result", raw_stdout)
        usage = payload.get("usage") or {}
        total_tokens = (
            usage.get("input_tokens", 0)
            + usage.get("output_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
        )
        cost_usd = payload.get("total_cost_usd")
        _record_token_usage(name, total_tokens, cost_usd)
    except (json.JSONDecodeError, AttributeError, TypeError) as exc:
        # Fall back to treating stdout as plain text — matches the old
        # behavior exactly, just without usage capture for this one call.
        # Never let an accounting parse failure take down the pipeline.
        log.warning(f"[{name.upper()}] --output-format json did not parse ({exc}) — "
                    f"using raw stdout, usage not recorded this call")
        text_output = raw_stdout

    return text_output


# ─────────────────────────────────────────────────────────────
# TIER 1b — Direct model API (OpenRouter, OpenAI-compatible)
# Drop-in alternative to call_cc_agent: ONE HTTP call, no Claude Code
# system-prompt/tool overhead, no agentic loop. This is the cost fix —
# a lean API call is ~$0.03-0.10 (or $0 on free models) vs the ~$0.15+
# floor every `claude` CLI cold-start pays. Same (name, system, user)
# interface so agents can switch with a one-line change.
# ─────────────────────────────────────────────────────────────

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_api(name: str, system_prompt: str, user_input: str,
             model: str = None, fallback: str = None, max_tokens: int = 8000) -> str:
    """Call an LLM via OpenRouter's OpenAI-compatible endpoint. Returns text.

    If `fallback` is set (and differs from `model`), OpenRouter's native `models`
    array is used so it transparently falls back to `fallback` when the primary
    model errors, is unavailable (free-model churn), or rate-limits.
    """
    import urllib.request
    import urllib.error

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set — add it to agents/.env")
    model = model or os.environ.get("OPENROUTER_MODEL_DEFAULT", "openrouter/free")

    if DRY_RUN:
        stub = _build_dry_run_priya_spec() if name == "priya" else _DRY_RUN_STUBS.get(name, "dry_run_ok")
        log.info(f"[{name.upper()}] DRY RUN — returning stub (no API call)")
        return stub

    body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "max_tokens": max_tokens,
        "usage": {"include": True},   # OpenRouter: return real cost in usage
    }
    if fallback and fallback != model:
        body["models"] = [model, fallback]   # OpenRouter tries these in order
    else:
        body["model"] = model
    payload = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_URL, data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://aima.productions",
                 "X-Title": "AIMA pipeline"},
    )
    log.info(f"[{name.upper()}] calling API (model={model})")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"API agent [{name}] HTTP {exc.code}: {body}")

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"API agent [{name}] returned no choices: {json.dumps(data)[:400]}")
    text = choices[0]["message"]["content"] or ""
    usage = data.get("usage") or {}
    cost = usage.get("cost")
    _record_token_usage(name, usage.get("total_tokens", 0), cost)
    log.info(f"[api] {name} model={model} tokens={usage.get('total_tokens')} cost=${cost}")
    return text


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
    # Stash unstaged changes so rebase doesn't abort, then restore them.
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    stashed = False
    if status:
        subprocess.run(["git", "stash", "-u"], cwd=REPO_ROOT, check=True)
        stashed = True
    try:
        subprocess.run(["git", "pull", "--rebase", "origin", "main"],
                       cwd=REPO_ROOT, check=True)
    finally:
        if stashed:
            subprocess.run(["git", "stash", "pop"], cwd=REPO_ROOT, check=False)
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
