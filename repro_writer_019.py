"""
Diagnostic repro script — 2026-07-04.

Reproduces exactly what agents/marco.py's Stage 3a (Writer) would have done
last night for article #19, using Priya's ACTUAL slug ("persuasion-engine")
straight from the cached research file's _meta block — NOT run_writer_batch.py's
independent _slugify() (which mis-derives "the-persuasion-engine-ai-social"
from the calendar title and can't find the research file; that's a separate,
real bug in run_writer_batch.py's standalone slug resolution, but it's not
what killed last night's full-pipeline run, since marco.py threads the same
spec/slug object from Priya through Scout and Writer without re-deriving it).

Safe to delete once the real Stage-3 failure is fixed and article #19 has a
draft.
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.base import REPO_ROOT, log
from agents import writer

research_path = REPO_ROOT / "articles/research/persuasion-engine-research.json"
research = json.loads(research_path.read_text(encoding="utf-8"))
meta = research["_meta"]

spec = {
    "number": meta["article_number"],
    "slug": meta["slug"],
    "filename": meta["filename"],
    "title": meta["title"],
    "author": meta["author"],
    "category": meta["category"],
    "og_image": f"img/articles/aima-{meta['article_number']:03d}-{meta['slug']}.jpg",
}

log.info(f"[repro] Calling writer.run() with spec={json.dumps(spec)}")
try:
    path = writer.run(spec, research)
    log.info(f"[repro] SUCCESS — draft written to {path}")
    print(json.dumps({"ok": True, "draft_path": path}))
except Exception as exc:
    import traceback
    log.error(f"[repro] FAILED: {exc}")
    traceback.print_exc()
    print(json.dumps({"ok": False, "error": str(exc)}))
    sys.exit(1)
