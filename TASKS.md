# AIMA Tasks

_Last updated: 2026-07-22 (pipeline hardened for #29; machine compromise contained)_

## 🚨 SECURITY — do this before anything else (2026-07-22)

- [ ] **Rotate ALL credentials from a DIFFERENT, clean machine.** A PyArmor-obfuscated
  payload (`C:\ProgramData\CoffeeFolder\`) + a Deno `-A` all-permissions loader
  (HKCU Run key `5e9292cd` → `…\Roaming\5e9292cd.js`) ran as ShadowMonkey for ~5 months
  (payloads dated 2026-02-15 and 2026-04-17), beaconing to C2 domains
  (`lavrentiyberia.com`, `admiralkolchak.com`, `annaionovna.com`, `popopopopi.com`).
  Assume every secret this account can read was stolen: GitHub token, LinkedIn tokens
  (`linkedin_pipeline/.env`), `agents/.env` keys (Anthropic/OpenRouter), GA4 service-account
  JSON, email, financial. Rotating from the infected box just leaks the new secrets too.
- [ ] **Do NOT re-auth `claude` on this machine until it's cleaned** (see next section — this
  is what's blocking the pipeline, but security comes first).
- [ ] **Run Microsoft Defender OFFLINE scan**, then seriously weigh a clean OS reinstall
  (two independent persistence mechanisms + months of dwell = reinstall is the only certain fix).
- [ ] Malware already CONTAINED this session: processes killed, task `pythonw.exe` unregistered,
  Run key removed, both payloads quarantined to `C:\Users\ShadowMonkey\Quarantine_20260722\`
  (kept intact for VirusTotal — SHA256 hashes in that folder + in the handoff doc).

## 🔥 Hot / In Progress

- [ ] **Re-authenticate `claude` CLI, then run the pipeline** — THIS is the only thing blocking
  article #29 from posting. `claude`'s OAuth is expired (`claude --print "ping"` →
  "OAuth session expired"). Fix: run `claude` in a terminal, complete login, then
  `python run.py`. Row #29 is already resolved, so it will go straight through Trend Scout.
  **Gated behind the security cleanup above** — don't do this on the compromised box.
- [ ] **Fund OpenRouter account** — HTTP 402 on real calls; OPENROUTER_API_KEY currently commented out in agents/.env. All agents fall back to CC CLI (working). Decision needed: fund for cost routing or drop that layer. NOTE: OpenRouter `:online` is now the ONLY tool-capable fallback for scout/trend_scout when CC OAuth is down (Tier B/direct-Anthropic is deliberately blocked for them — see 2026-07-22 hardening).
- [ ] **LinkedIn token refresh** — `r_member_social` scope approved June 20, 2026 but token not refreshed. Run `python linkedin_pipeline/linkedin_auth.py` then test `python linkedin_pipeline/analytics_collector.py`. (Will need redoing anyway after the credential rotation above.)

## 📋 Next Article

- [ ] **Article #29** — "The Lab That Runs Itself: How Autonomous Labs Are Compressing Materials Discovery From Years to Days" (Kenji, AI Science). Row already resolved from TBD (2026-07-22). Just needs the `claude` re-auth above, then `python run.py`. QC_GATE is `auto` (standing default per Joe).

## 🐛 Known Issues / Open Items

- [ ] **Action needed: finish the #031 image swap.** Code is fixed (see Completed below)
  and `fix_031_image.py` is sitting in the repo root, but nothing could actually be
  committed/pushed from the Cowork sandbox — both the cloud sandbox and the local
  device-bridge VM sit behind a network allowlist that blocks api.pexels.com AND
  the Higgsfield CDN (`X-Proxy-Error: blocked-by-allowlist`). Run `python
  fix_031_image.py` from a real terminal in this repo root to download the two
  already-generated replacement images, verify they're non-duplicate, and commit+push.
  It only touches the two image files (not the article HTML — og:image path is
  unchanged). NOTE: your working tree currently has ~244 modified/untracked files
  (line-ending churn across most articles, `pipeline_build/*`, uncommitted research
  files) — worth a separate cleanup pass so future one-off fixes don't risk sweeping
  in unrelated changes.
- [ ] **Review + commit the Maya/LinkedIn dedup fixes.** `agents/maya.py` and
  `linkedin_pipeline/linkedin_poster.py` were edited in place (2026-07-28) but not
  committed — same sandbox network restriction meant git operations were left for a
  real terminal too. `git diff agents/maya.py linkedin_pipeline/linkedin_poster.py`
  to review, then commit. Root cause + rationale below under Completed.
- [ ] **Inline glossary-term linking is partial** — 2 of 7 terms linked on #25. Root cause: short-form references ("AVM") miss full-form definitions ("Automated Valuation Model (AVM)"). Fuzzy/partial matching or a small model call needed — not worth it yet.
- [ ] **Format pre-check false positive** — "TODO/PLACEHOLDER/lorem ipsum" warning fires on merged articles even when placeholders are confirmed gone. Non-blocking WARNING only. Root in marco.py format-check logic — not yet read/diagnosed.
- [ ] **Stat-grid citation gaps** — content-accuracy issue (Writer asserting stats without in-text sources). Per-article editorial review, not a pipeline bug. #25 had the 90% employer AI-screening stat uncited.
- [ ] **Scout (SC) over-budget** — SC used 750,238 tokens vs. 500,000 budget on #26 run (cost $1.02). Consider raising SC budget ceiling or investigating turn-loop efficiency.
- [ ] **Cora (CO) over-budget** — CO used 61,093 tokens vs. 5,000 budget (cost $0.34). Budget ceiling is too low for real governance calls — needs upward adjustment.
- [ ] **Priya cost investigation** — $0.20-0.45/call, ~150-215K tokens. Never diagnosed for turn-loop efficiency. May have "re-reads context every turn" pattern. Not urgent but flagged.
- [ ] **`[persona]` risk in maya_merge.py** — blunt str.replace near inline JS is dangerous. Any new `[token]` must be vetted against skeleton `<script>`/<style> before adding to the loop. Document/enforce via comment or validator.

## ✅ Completed (recent)

- [x] **Root-caused why duplicate cover images keep recurring despite the #027/#029
  "fixes" — both were one-off patches, not fixes to the code path that actually
  causes it.** (2026-07-28, Cowork investigation) Article #031 shipped with its
  primary cover byte-identical to #019 AND #025's covers (which were already
  duplicates of each other, uncaught), and its alt image identical to #024's alt.
  Root cause: `_fetch_stock_images()`'s `exclude_hashes` dedup hashed the RAW,
  just-downloaded Pexels file and compared it against hashes of files in
  `img/articles/` — but every file there has already been through
  `_save_header_image()`'s resize-to-1200×630/JPEG-quality-90 pipeline. Raw bytes
  vs. processed bytes can never match, even for the literal same source photo, so
  the "exclude existing covers" guard was a silent no-op for every first-time
  fetch. The broader `_is_any_duplicate()` gate (added in the #029 fix, commit
  921a85d) only protects RE-runs of an article that already has a file on disk —
  it never fires on a brand-new article's first fetch, which is exactly the #031
  case. Separately, `_pickup_from_handoff()` (the handoff/ready pre-stage path)
  had zero duplicate checking at all. Fixed in `agents/maya.py`: added
  `_processed_hash()` so the comparison is apples-to-apples, added a post-save
  verification safety net, and added duplicate checking to the handoff pickup
  path. See "Action needed" above — the code fix is done but not yet committed.
- [x] **Fixed the personal-profile-reshare repetition** — `build_personal_commentary()`
  in `linkedin_pipeline/linkedin_poster.py` had Dawn's persona ALWAYS opening with
  the literal line "I've been sitting with this one." and Kenji's ALWAYS opening
  with "This is the story nobody's telling about what's actually possible." — 100%
  static on every single post for those two bylines (only Joselito's branch
  rotated). Their TL;DR lines were also hardcoded, identical, topic-generic claims
  regardless of the actual article. Gave Dawn and Kenji their own 5-opener pools,
  selected the same deterministic-per-article way Joselito's pattern rotation
  works, and switched both personas' TL;DR to the same content-derived
  `_article_tldr()` Joselito already uses. Also fixed the pattern-index hashing
  itself: it used Python's builtin `hash()`, which is process-salted
  (PYTHONHASHSEED) and NOT actually stable across a crash-retry despite being
  commented as such — replaced with an md5-based stable hash so retries land on
  the same variant instead of reshuffling. Not yet committed — see above.
- [x] **Pipeline hardened against CC OAuth expiry** (commit 408bd94) — scout/trend_scout raise a clean recoverable halt (`LiveResearchUnavailableError` → `trend_scout_unavailable`) instead of crashing or fabricating research via the tool-less fallback; CLAUDE.md crash-log deduped; Task Scheduler theory falsified (no such task exists). (2026-07-22)
- [x] **Article #29 row resolved** — TBD → real Kenji title via the sanctioned `persist_topic_to_calendar()` path; verified `python run.py` clears Priya + Trend Scout. (2026-07-22)
- [x] **Machine compromise contained** — obfuscated malware killed/quarantined, persistence removed. (2026-07-22) See handoff doc + Quarantine folder.
- [x] Article #26 published — "Data Centers in Orbit: Why Big Tech Wants to Move AI's Power Problem to Space" — live at aima.productions. Cost: $1.61. Flag: `writer_draft_reused`. (2026-07-16)
- [x] Article #25 published (Joe override, Vera needs_revision) — "The Government Filed a Brief for the Algorithm" — live + LinkedIn. (2026-07-14)
- [x] Maya's skeleton merge rewritten (maya_merge.py) — glossary/references now route into real `<section>` blocks; H2 ids and TOC wired correctly. Vera-verified. (2026-07-14)
- [x] Quill demoted to pure-Python verification gate — no more LLM call, no more token-blowout risk. $0 always. (2026-07-14)
- [x] Writer word-count gate added — strips glossary/references before counting, matching Vera's methodology. (2026-07-14)
- [x] Vera word-count check removed (now Writer's job). (2026-07-14)
- [x] QC_GATE changed to `auto` as standing default. (2026-07-14)
- [x] Cora token tracking fixed — `call_cc_agent()` now runs `--output-format json` and writes real per-call usage to token_budget.json. (2026-07-04)
- [x] Marco cost redesign (Direction B) — Writer merged into Quill in full pipeline; 43% cost reduction on WR+QL stages. (2026-07-04)
- [x] Context-by-path optimization — writer/quill pass file paths instead of inlining content; user_input ~50k chars → ~1.3k chars. (2026-07-04)
- [x] OpenRouter bypassed (insufficient credits); all agents on CC CLI. (2026-07-14)
- [x] `[persona]` JS corruption bug in maya_merge.py fixed (commit 3b9a4ce). (2026-07-15)
- [x] LinkedIn API Development Tier approved (app id 253440006) + `r_member_social` added. (2026-06-20)
