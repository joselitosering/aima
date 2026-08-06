"""Exa search backend — pure-Python wrapper around the Exa MCP server.

WHY THIS EXISTS
---------------
`scout` and `trend_scout` are LIVE_RESEARCH_AGENTS (agents/base.py): they must
survey what is actually out there right now, so base.py deliberately refuses to
fall back to the tool-less Anthropic Messages API for them and raises
LiveResearchUnavailableError instead. That carve-out is correct — but it means
an expired Claude Code OAuth token halts the whole pipeline at Scout, which is
what happened five times on 2026-07-22.

Exa is reachable over plain HTTP through the locally-installed `mcporter` CLI,
with **no API key and no Claude Code session**. That makes it the one search
backend that keeps working precisely when CC OAuth is dead. This module is the
Python-side primitive for it.

SCOPE — read this before extending
----------------------------------
This module ONLY retrieves real sources. It does NOT synthesise a research
brief, and it is deliberately NOT wired into base.py's LiveResearchUnavailableError
carve-out. Grounding a tool-less model on these results would be a legitimate way
to lift that halt, but that is a guardrail change and needs an explicit decision
(see DECISION-LOG.md) — not a side effect of importing this file.

Installed 2026-08-01 via Agent Reach 1.5.0. Registered in scout-sources.json as
`search_backends[exa_mcp_search]` / `[exa_mcp_fetch]`.

Usage:
    from agents.exa_search import search, fetch, available
    print(search("peer-reviewed studies on self-driving materials labs"))

CLI:
    python -m agents.exa_search "describe the ideal page here"
    python -m agents.exa_search --fetch https://example.com/article
"""

import json
import shutil
import subprocess
import sys

from agents.base import log

# Exa's hosted MCP endpoint is free but undocumented on limits. Scout's
# STEP 3 budget allows at most 3 calls per research run — keep it that way.
DEFAULT_NUM_RESULTS = 5
DEFAULT_MAX_CHARACTERS = 8_000
CALL_TIMEOUT = 120


class ExaUnavailableError(RuntimeError):
    """mcporter is missing, or the `exa` server is not registered with it.

    Recoverable operator condition, not a code defect. Fix:
        npm install -g mcporter
        mcporter config add exa https://mcp.exa.ai/mcp --scope home
    """


def _mcporter() -> str:
    """Return the mcporter executable path, or raise ExaUnavailableError."""
    exe = shutil.which("mcporter")
    if not exe:
        raise ExaUnavailableError(
            "mcporter not found on PATH. Install it with:\n"
            "  npm install -g mcporter\n"
            "  mcporter config add exa https://mcp.exa.ai/mcp --scope home"
        )
    return exe


def available() -> bool:
    """True if an Exa call can be attempted. Cheap — does not hit the network."""
    if not shutil.which("mcporter"):
        return False
    try:
        cfg = subprocess.run(
            [_mcporter(), "config", "list"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=30,
        )
        return "exa" in (cfg.stdout or "")
    except (subprocess.SubprocessError, OSError):
        return False


def _call(tool: str, **params) -> str:
    """Run `mcporter call exa.<tool> k=v ...` and return stdout as text.

    Values are JSON-encoded for anything that isn't a plain string, which is how
    mcporter expects list/number arguments (e.g. urls='["https://…"]').
    """
    args = [_mcporter(), "call", f"exa.{tool}"]
    for key, value in params.items():
        encoded = value if isinstance(value, str) else json.dumps(value)
        args.append(f"{key}={encoded}")

    # ASCII only — this Windows console is cp1252 and mangles non-ASCII log output.
    log.info(f"[exa] {tool}({', '.join(params)})")
    try:
        result = subprocess.run(
            args, capture_output=True, encoding="utf-8",
            errors="replace", timeout=CALL_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExaUnavailableError(
            f"[exa] {tool} timed out after {CALL_TIMEOUT}s — endpoint may be rate-limiting."
        ) from exc

    if result.returncode != 0:
        raise ExaUnavailableError(
            f"[exa] {tool} failed (exit {result.returncode}):\n"
            f"{(result.stderr or result.stdout or '(no output)')[:500]}"
        )
    return (result.stdout or "").strip()


def search(query: str, num_results: int = DEFAULT_NUM_RESULTS) -> str:
    """Semantic web search. Returns clean extracted text with URLs and dates.

    Exa is SEMANTIC, not keyword-based: describe the ideal page
    ("blog post comparing React and Vue performance"), not keywords
    ("React vs Vue"). Prefix with `category:people` or `category:company` to
    search profiles/companies specifically.
    """
    if not query.strip():
        raise ValueError("[exa] search query must not be empty")
    return _call("web_search_exa", query=query, numResults=num_results)


def fetch(url: str, max_characters: int = DEFAULT_MAX_CHARACTERS) -> str:
    """Read one URL as clean markdown.

    Replaces Jina Reader (https://r.jina.ai/URL), which returns HTTP 401 from
    this network — anonymous queries are blocked on AS7018 reputation.

    ALWAYS keep max_characters capped. An uncapped fetch of a long page is the
    easiest way to blow Scout's 60k working budget.
    """
    return _call("web_fetch_exa", urls=[url], maxCharacters=max_characters)


def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    try:
        if argv[0] == "--fetch":
            if len(argv) < 2:
                print("usage: python -m agents.exa_search --fetch <url>")
                return 2
            print(fetch(argv[1]))
        else:
            print(search(" ".join(argv)))
    except (ExaUnavailableError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
