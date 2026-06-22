import anthropic
import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

REPO_ROOT = Path(__file__).parent.parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("aima")


def call_agent(name: str, system: str, user: str, max_tokens: int = None) -> str:
    from agents.config import MODEL_MAP, BUDGET_MAP
    model = MODEL_MAP[name]
    tokens = max_tokens or BUDGET_MAP[name]
    log.info(f"[{name}] calling model={model} max_tokens={tokens}")
    response = client.messages.create(
        model=model,
        max_tokens=tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def read_json(path: str) -> dict:
    p = REPO_ROOT / path
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def write_json(path: str, data):
    p = REPO_ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def append_optimization_report(entry: dict):
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
