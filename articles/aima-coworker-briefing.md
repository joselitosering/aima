# AIMA Coworker Briefing
**Auto-updated after each article. Coworker reads this instead of the full calendar.**

---

## LAST PUBLISHED

| # | Date | Author | Title | Category | File |
|---|------|--------|-------|----------|------|
| D1 | Jun 19, 2026 | Dawn Ginhaua | Your AI Ethics Board Is a Press Release | AI Ethics | aima-article-ethics-theater-014.html |
| 013 | Jun 18, 2026 | Joselito Sering | The Global South AI Gap: Who Gets Left Behind When the Future Arrives | AI Society | aima-article-global-south-ai-gap-013.html |

---

## NEXT UP (Joselito — numbered sequence)

| # | Date | Title | Category | Slug |
|---|------|-------|----------|------|
| **014** | Jun 20, 2026 | Hallucination Nation: Why AI Lies with Confidence and What It Costs Us | AI Ethics | hallucination-nation |
| 015 | Jun 22, 2026 | Machines That Compose: What AI Music Reveals About Human Creativity | AI Creative | machines-that-compose |
| 016 | Jun 24, 2026 | The Digital Nomad Economy: How Developing Nations Are Reshaping Global AI Labor | AI Society | digital-nomad-economy |
| 017 | Jun 26, 2026 | Power Hungry: The Carbon Ledger of the AI Compute Boom | AI Environment | power-hungry-carbon |
| 018 | Jun 28, 2026 | Diagnosis by Algorithm: The State of AI in Clinical Medicine, 2026 | AI Healthcare | diagnosis-by-algorithm |

## NEXT UP (Dawn — D-series)

| # | Date | Title | Category | Tone |
|---|------|-------|----------|------|
| **D2** | Jun 23, 2026 | TBD — Trending Topic | Trending | — |
| D3 | Jun 27, 2026 | TBD — Trending Topic | Trending | — |

## NEXT UP (Kenji — K-series)

| # | Date | Title | Category | Tone |
|---|------|-------|----------|------|
| **K1** | Jun 21, 2026 | TBD — Trending Topic | Trending | Optimistic deep-dive — one emerging technology, grounded in what it makes possible for real people. |
| K2 | Jun 25, 2026 | TBD — Trending Topic | Trending | — |

---

## PUBLISH PROCESS (mandatory order)

1. **Research** — gather sources, confirm facts, check what's trending
2. **Write** — save article HTML to `D:\Apps\DevOps\Github\aima\articles\` locally
3. **Push to GitHub** — `git add`, `git commit`, `git push`
4. **Wait 2 minutes** — GitHub Pages rebuilds; confirm article URL is live
5. **Update GS** — submit URL to Google Search Console (Request Indexing)
6. **Post to LinkedIn** — run `python pipeline.py --article [path]` from `linkedin_pipeline\`
7. **Update this file** — move article to LAST PUBLISHED, advance NEXT UP, update article-manager.html

**Pipeline command:**
```
cd D:\Apps\DevOps\Github\aima\linkedin_pipeline
python pipeline.py --article "D:\Apps\DevOps\Github\aima\articles\[filename].html"
```

**Article URL format:** `https://joselitosering.github.io/aima/articles/aima-article-[slug]-[number].html`

---

## BRAND RULES (condensed)

**Voice:** Investigative, morally serious, optimistic but critical. Name companies. Make the argument, then cite evidence. No bullet points in body text — information as argument.

**Audience:** Ages 13–70. Intelligent, curious, not necessarily technical. Lead with story and feeling; data arrives after the reader cares.

**Writing sequence (mandatory):**
1. Feeling first — something a 13-year-old can feel (awe, injustice, strangeness)
2. Story second — one specific human moment before any concept
3. Concept third — plain language + one analogy before the technical term
4. Evidence fourth — data and citations after the reader cares
5. Implication last — a question the reader carries out, not a conclusion

**One Twain-caliber sentence per article:** wry, precise, slightly devastating. One. Not repeated.

**Structure:** 4–7 H2 sections · at least one callout or pullquote per section · 8–15 min read · min 8 MLA 9th sources · 4–8 glossary terms

**Callout types:** `callout` cyan (insight) · `callout warning` orange (risk) · `callout success` green (win) · `callout gold` gold (policy/principle)

**Philippines / Global South:** reference only when directly and topically relevant — never forced.

**Intellectual DNA (felt, never cited):** Fuller · Sagan · Campbell · Hitchens · Bourdain · Rogers · James Allen · Napoleon Hill · Mark Twain · Bill Moyers

**Guest writer voices:**
- **Dawn Ginhaua** — Cultural Critic & Educator. Academic but human, sharp and dry. Reads: bell hooks, Naomi Klein, Arendt, Baldwin. Structure: provocation → thing nobody says → evidence → structural argument → open question.
- **Kenji** — TBD

**Categories covered so far (001–013 + D1):** AI Innovation · AI Ethics (×4) · AI Labor · AI Healthcare · AI Media · AI Philosophy · AI Environment · AI Society (×2) · AI Creative

**Category balance:** no more than 3 consecutive in same category · AI Ethics max 25% of calendar

---

## FILENAME CONVENTION
`aima-article-[short-slug]-[zero-padded-number].html` — numbered articles (Joselito)
`aima-article-[short-slug]-[D or K series number].html` → saved with 3-digit article number for file org

Example: `aima-article-hallucination-nation-014.html`
Guest example: `aima-article-ethics-theater-014.html` ← Dawn D1 used slot 014 filename; calendar tracks as D1

## SOURCE URL FORMAT
`https://joselitosering.github.io/aima/articles/aima-article-[slug]-[number].html`

---
*Last updated: June 19, 2026 — After publishing D1 (Dawn Ginhaua). Next: Joselito 014 (Hallucination Nation, Jun 20), Kenji K1 (Jun 21), Dawn D2 (Jun 23).*
