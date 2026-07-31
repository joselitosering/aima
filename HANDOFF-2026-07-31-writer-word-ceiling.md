# HANDOFF — Writer word-count ceiling, self-enforced bounds

**Date:** 2026-07-31
**File changed:** `agents/writer.py` (only) — 69 insertions, 8 deletions
**Status:** patched, dry-verified ($0), **uncommitted**
**Trigger:** article #33 breached 1800 words; recurring for Joselito (#26, #27, #33)

---

## 1. Diagnosis correction

The task brief assumed the 1800-word ceiling was absent from enforcement. It was not.
`agents/writer.py:228` (pre-patch) already computed `ceiling = int(a["range_max"] * 1.2)`
= 1800 for Joselito, and the gate fired correctly:

```
pipeline.log:2890
2026-07-30 12:41:38,224 [ERROR] [marco] CRASHED at stage 'writer':
  [writer] Word count gate: 1816 words outside acceptable 1020-1800
```

So #33 did **not** ship at 1816w. The gate caught it, killed the run, and the cost was:

| Event | Cost |
|---|---|
| 2026-07-30 12:37 Writer call, rejected at 1816w | $0.63 |
| Manual trim to 1488w | human time |
| 2026-07-31 14:27 re-run — crashed again at Quill (`Draft incomplete`) | run lost |
| 2026-07-31 14:33 re-run — published | $0.76 |

**Actual root cause:** the gate knew about 1800; the **prompt never did**. The writer had
no number to steer against, so overshoot was uncorrectable rather than merely unlucky.
The fix prevents *wasted runs*, not bad publishes.

**Second root cause (not in the original brief):** `find_draft()` checked the floor only —
`if wc < floor`. Marco reuses a pre-staged Writer-batch draft at Stage 3a **without**
calling `writer.run()`, so an over-ceiling draft accepted by `find_draft()` bypassed the
word-count gate entirely. That is the path #33's 14:27 re-run took
(`pipeline.log:2914  Stage 3a: reusing pre-staged Writer-batch draft`).

Two drafts on disk today prove the bypass was live: `hallucination-nation-024` (1818w)
and `data-broker-state-022` (1933w) were both reusable under the old floor-only check.
Both are now rejected.

---

## 2. Changes applied

### 2.1 Explicit per-persona `ceiling` key
Replaces implicit `range_max * 1.2` math buried in `run()`.

| Persona | min | target | max | ceiling |
|---|---|---|---|---|
| joselito | 1200 | 1350 | 1500 | **1800** |
| dawn | 900 | 1050 | 1200 | **1440** |
| kenji | 500 | 750 | 1000 | **1200** |

### 2.2 New `_bounds(a) -> (floor, ceiling)` helper
Single source of truth, consumed by both `run()`'s gate and `find_draft()`'s reuse check.
Falls back to the old implicit math if a future persona omits `ceiling`, so behaviour
cannot silently drift. Verified identical to the pre-patch values for all three personas.

### 2.3 `WRITER_PROMPT` — self-enforcement clause
New paragraph: word count is self-enforced across all three numbers; under-minimum is as
much a failure as over-maximum; the ceiling is a **rejection threshold, not a target and
not permission to write longer**; count prose words before saving; if research overflows,
cut to the strongest thread rather than running long.

### 2.4 Per-call assignment block — the three numbers, rendered
`TARGET LENGTH: {range} — THIS IS A HARD CONSTRAINT` replaced with an explicit
MINIMUM / TARGET / MAXIMUM / CEILING table plus a pre-save self-check instruction.
Glossary and references are stated as excluded from every figure, matching how
`_prose_word_count()` actually measures.

### 2.5 `find_draft()._valid()` — ceiling check added
```python
if wc > ceiling:
    log.warning(f"[writer] find_draft: skipping OVERSIZE {p.name} ({wc}w > ceiling ...")
    return False
```
**Behavioural consequence:** an oversize pre-staged draft now forces a fresh Writer call
instead of passing through. This costs a Writer call (~$0.65) in that case. Intended —
an oversize draft should never reach publish just because it was written earlier.

---

## 3. Verification

Dry render, no LLM calls, **$0**. All checks passed; `python -m py_compile agents/writer.py`
exit 0.

- ceilings == `range_max * 1.2` for all three personas
- `_bounds()` output identical to pre-patch implicit math (no drift)
- rendered assignment block contains min, max and ceiling for each persona
- `WRITER_PROMPT` contains the self-enforcement language
- `find_draft` uses `_bounds()`, rejects `wc > ceiling`, still rejects `wc < floor`

The end-to-end check in the original brief (`python run_writer_batch.py --article 35`)
**cannot run**: there is no `articles/research/*-035-*.json`, so the batch halts at exit 2
(`no_research`) before Writer is ever invoked. Run the Research batch for #35 first if a
live check is wanted; otherwise the next scheduled cycle exercises this for free.

The verification script was not left in the repo — it is not covered by `.gitignore` and
would have been swept into Porter's next article commit. Reproduce from section 6 below
if needed.

---

## 4. Open items

1. **Uncommitted.** `agents/writer.py` is modified in the working tree. Porter's next run
   does `git add`/commit and will sweep it into an article commit unless committed
   deliberately first. Recommend a standalone commit.
2. **`agents/cora.py:23` hardcodes `ceiling = 1800` flat for all personas** — wrong for
   Dawn (1440) and Kenji (1200). Currently harmless: Quill was demoted to pure Python
   2026-07-14 and no longer authors, so `prepare_quill_call()`'s `extra_instruction` is
   not steering a model. Should read from `writer.AUTHOR_SPECS[...]["ceiling"]` if Quill
   ever authors again. Not changed this session — out of scope.
3. **Overshoot is systematic, not incidental.** Article #034 (written 14:39 today, before
   this patch) came in at **1512w** — 12 over Joselito's 1500 max, inside the 1800
   ceiling, so it passed silently. The gate only catches ceiling breaches; the *max* is
   currently prompt-enforced only. Watch the next 2-3 Joselito drafts: if they still land
   above 1500, the next lever is tightening the gate to `range_max` rather than
   `range_max * 1.2`.
4. **Untracked artifacts** predating this session: `articles/drafts/*-033-*.html`,
   `*-034-*.html` and the matching research JSONs are untracked and will be swept by
   Porter. Pre-existing behaviour, flagged only.

---

## 5. Draft inventory at time of patch

Measured with `_prose_word_count()`, evaluated against Joselito's bounds (1020-1800):

```
data-broker-state-022-draft.html                      1933w  REJECTED  (Dawn: also > 1440)
data-centers-in-orbit-why-026-draft.html               906w  REJECTED
government-brief-algorithm-025-draft.html              854w  REJECTED
hallucination-nation-024-draft.html                   1818w  REJECTED  (was reusable pre-patch)
persuasion-engine-019-draft.html                      4738w  REJECTED
power-hungry-the-carbon-ledger-027-draft.html         1512w  reusable
robot-beside-you-023-draft.html                       1762w  reusable
the-brain-computer-interface-horizon-033-draft.html   1488w  reusable  (post manual trim)
the-clause-that-broke-the-031-draft.html              1192w  reusable
the-ghost-workers-hidden-human-034-draft.html         1512w  reusable
the-lab-that-runs-itself-029-draft.html                670w  REJECTED
the-living-battery-how-bioengineered-032-draft.html    994w  REJECTED
the-termination-algorithm-how-token-028-draft.html    1000w  REJECTED
who-owns-the-output-the-030-draft.html                1436w  reusable
```

---

## 6. Regression check (recreate as `_verify_writer_ceiling.py`, delete after use)

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from agents import writer

fail = 0
def check(label, ok):
    global fail
    if not ok: fail += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

for key, a in writer.AUTHOR_SPECS.items():
    check(f"{key} ceiling", a.get("ceiling") == int(a["range_max"] * 1.2))
    floor, ceiling = writer._bounds(a)
    check(f"{key} _bounds no drift",
          (floor, ceiling) == (int(a["range_min"]*0.85), int(a["range_max"]*1.2)))

src = Path(writer.__file__).read_text(encoding="utf-8")
fd = src[src.index("def find_draft"):src.index("def resolve_author")]
check("find_draft rejects oversize", "wc > ceiling" in fd)
check("find_draft rejects stub", "wc < floor" in fd)
check("prompt self-enforces", "WORD COUNT IS SELF-ENFORCED" in writer.WRITER_PROMPT)

print("ALL PASSED" if not fail else f"{fail} FAILED")
sys.exit(1 if fail else 0)
```
