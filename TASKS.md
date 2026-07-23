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

- [ ] **Inline glossary-term linking is partial** — 2 of 7 terms linked on #25. Root cause: short-form references ("AVM") miss full-form definitions ("Automated Valuation Model (AVM)"). Fuzzy/partial matching or a small model call needed — not worth it yet.
- [ ] **Format pre-check false positive** — "TODO/PLACEHOLDER/lorem ipsum" warning fires on merged articles even when placeholders are confirmed gone. Non-blocking WARNING only. Root in marco.py format-check logic — not yet read/diagnosed.
- [ ] **Stat-grid citation gaps** — content-accuracy issue (Writer asserting stats without in-text sources). Per-article editorial review, not a pipeline bug. #25 had the 90% employer AI-screening stat uncited.
- [ ] **Scout (SC) over-budget** — SC used 750,238 tokens vs. 500,000 budget on #26 run (cost $1.02). Consider raising SC budget ceiling or investigating turn-loop efficiency.
- [ ] **Cora (CO) over-budget** — CO used 61,093 tokens vs. 5,000 budget (cost $0.34). Budget ceiling is too low for real governance calls — needs upward adjustment.
- [ ] **Priya cost investigation** — $0.20-0.45/call, ~150-215K tokens. Never diagnosed for turn-loop efficiency. May have "re-reads context every turn" pattern. Not urgent but flagged.
- [ ] **`[persona]` risk in maya_merge.py** — blunt str.replace near inline JS is dangerous. Any new `[token]` must be vetted against skeleton `<script>`/<style> before adding to the loop. Document/enforce via comment or validator.

## ✅ Completed (recent)

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
