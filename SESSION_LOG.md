# AIMA Pipeline — Session Log

---

## Session: 2026-06-25 (continued from prior context)

### Completed

**1. `--dry-run` stub system (`agents/base.py`)**
- `base.DRY_RUN = False` flag
- `_build_dry_run_priya_spec()` — reads state.json + disk, returns real article spec
- `_DRY_RUN_STUBS` — per-agent stubs: vera→"approved", others→"dry_run_ok"
- Stub check at top of `call_cc_agent()` — returns stub immediately, zero CC tokens
- `timeout=1800` + `TimeoutExpired` handler added

**2. `run.py` wired**
- Sets `base.DRY_RUN = True` when `--dry-run` flag passed

**3. `MAYA_PROMPT` rewritten (`agents/prompts.py`)**
- Removed all Higgsfield image generation instructions (Python handles it)
- CC agent focuses only on skeleton merge: wire Quill's copy into full HTML
- Must write file unconditionally; return only ARTICLE_PATH

**4. `agents/maya.py` — two fixes**
- Real-image-exists check: if `og_image > 1024 bytes` → skip generation
- Merge check: `og_image in content and "og:image" in content` (replaced size heuristic)

**5. `agents/.env` created**
- `HIGGSFIELD_API_KEY=` (empty placeholder, instructions in comment)

**6. `run_cowork.py` created (Cowork-aware wrapper)**
- `--check` mode: reads next article spec via dry-run stub; outputs JSON manifest + exits 10 if images missing
- `--save-image --url URL --path REL_PATH`: downloads + Pillow-resizes to 1200×630 JPG, saves to REPO_ROOT
- Pass-through (no flags): calls `marco.run()`
- Tested: `--check` exits 10 correctly for article #19 with both image paths + prompts

### Dry-run test result

```
All 9 pipeline stages: PASS
Duration: ~0.3 seconds
CC tokens consumed: 0
State advanced: next_article_number → 19, next_track → trending
```

---

## Cowork → Pipeline image generation workflow

```
Step 1: python run_cowork.py --check
        → exit 10 + manifest.json with:
            primary_path, alt_path, prompts.primary, prompts.alt
            recommended_model: "soul_2", aspect_ratio: "16:9"

Step 2: [Cowork session]
        mcp__cb1bb852__generate_image(
            model="soul_2",
            prompt=manifest.prompts.primary,
            aspect_ratio="16:9"
        )
        → job_id → job_display → get URL

Step 3: python run_cowork.py --save-image \
            --url <PRIMARY_URL> \
            --path img/articles/aima-NNN-slug.jpg

Step 4: Repeat Step 2–3 for alt image
        --path img/alt-img/aima-NNN-slug-alt.jpg

Step 5: python run.py
        Maya: images already on disk → skip generation
        CC agent: skeleton merge only
```

---

## Open tasks (W-series, insights repo)

| ID  | Task                              | Status  |
|-----|-----------------------------------|---------|
| W1  | POST /api/pipeline/toggles        | pending |
| W2  | POST /api/pipeline/run + SSE      | pending |
| W3  | Schedule button → scheduled task  | pending |
| W4  | POST /api/token-budget/update     | pending |
| W5  | Bottlenecks persistence + UX      | pending |
| W6  | POST /api/calendar/update         | pending |
| W7  | POST /api/article-data/upload     | pending |
| W8  | Decisions: Prisma schema + seed   | pending |
| W10 | Confirm ZAI_API_KEY in .env       | pending |

---

## Architecture reminders

- **No `ANTHROPIC_API_KEY`** — CC billing via Pro/Max subscription only
- **`claude --print --dangerously-skip-permissions`** — how CC subagents are called
- **Cowork MCP `cb1bb852`** — only available in Cowork sessions; NOT in `claude --print` subprocesses
- **`mcp__cb1bb852__generate_image` required param**: `model` (e.g. `soul_2`, `nano_banana_pro`)
- Maya CC agent receives: ARTICLE_PATH, OG_IMAGE, ALT_IMAGE, spec fields — writes merged HTML
