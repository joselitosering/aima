# AIMA Dispatch — Deployment Runbook

**Version:** 1.0 · 9 August 2026
**Time to complete:** ~2 hours of work, plus up to 24h waiting on DNS
**Rollback:** every phase is reversible; nothing sends until Phase 7

Work top to bottom. **Each phase ends with a gate — do not proceed until it passes.**
Skipping a gate is how you end up debugging four things at once.

---

## Preflight

| Need | Where | Notes |
|---|---|---|
| Resend account | resend.com | Free tier is fine to start |
| DNS access for `aima.productions` | your registrar / Cloudflare | You'll add 3–4 records |
| A real postal address | — | **Legally required** in every email footer (CAN-SPAM). A PO box is acceptable. |
| Google account that owns the Sheet | — | Must be the same account that deploys the Apps Script |
| `Code.gs` | agent outputs folder | ~56 KB, one file |

**Decide now:** the sending subdomain. Recommended `mail.aima.productions`
(Resend's own default convention is `send.yourdomain.com` — either is fine, just
be consistent). **Do not send from the root domain.** If newsletter reputation
ever sours, root-domain sending drags your client correspondence and Stripe
receipts down with it.

---

## Phase 0 · Resend domain + DNS

1. Resend → **Domains → Add Domain** → enter `mail.aima.productions`.
2. Pick your region (choose the one closest to most subscribers).
3. Resend shows you a record set. **Copy the exact values from your dashboard** —
   they are generated per-domain, so never copy them from a guide, including this one.
   You will get roughly:

   | Type | Host | Purpose |
   |---|---|---|
   | `MX` | `send.mail.aima.productions` | bounce handling |
   | `TXT` | `send.mail.aima.productions` | SPF |
   | `TXT` | `resend._domainkey.mail.aima.productions` | DKIM |

4. Add every record at your DNS provider. **Watch the host field** — many
   providers auto-append the domain, so pasting a fully-qualified host creates
   `send.mail.aima.productions.aima.productions`. This is the single most common
   verification failure.
5. Add DMARC at the **organisational** domain, not the subdomain:

   | Type | Host | Value |
   |---|---|---|
   | `TXT` | `_dmarc.aima.productions` | `v=DMARC1; p=none; rua=mailto:founder@aima.productions; sp=none; adkim=r; aspf=r` |

   Start at `p=none`. It is a monitoring policy — it changes nothing about
   delivery, it just makes reports flow. Move to `p=quarantine` after ~30 days of
   clean reports, then `p=reject`. Jumping straight to `p=reject` on a new setup
   will silently bin your own mail.

6. Back in Resend, hit **Verify**. Usually minutes; allow up to 24 hours.

> ### ✅ Gate 0
> Resend shows **Verified** on `mail.aima.productions`.
> If it doesn't after 24h, check your records are publicly visible with a DNS
> lookup tool and confirm they landed on the subdomain, not the root.

---

## Phase 1 · The Google Sheet

1. Create a new Google Sheet named **`AIMA_Newsletter`**.
2. **Extensions → Apps Script.** This creates a *container-bound* script —
   it must be bound to this Sheet, not standalone, or `getActiveSpreadsheet()` fails.
3. Delete the stub `myFunction`. Paste the entire contents of `Code.gs`. Save.
4. Run `bootstrapSheets` from the function dropdown.
   - First run triggers an OAuth consent screen.
   - You'll see **"Google hasn't verified this app."** That's expected — it's your
     own script. Click **Advanced → Go to AIMA_Newsletter (unsafe)**.
5. Run `makeSecret`. Copy the string it logs — you need it in Phase 2.
6. Run `seedPromoAssets`. Loads Paperboy, Rave New World and the service promos.

> ### ✅ Gate 1
> Six tabs exist: `Subscribers`, `ContentQueue`, `PromoAssets`, `SendLog`,
> `Events`, `Config`. `Config` has ~18 rows. `PromoAssets` has 6 rows.

---

## Phase 2 · Secrets and config

**Project Settings (⚙) → Script Properties → Add script property.** Three of them:

| Property | Value |
|---|---|
| `RESEND_API_KEY` | Resend → API Keys → Create. **Sending access only.** Starts `re_` |
| `HMAC_SECRET` | The string `makeSecret` logged in Phase 1 |
| `RESEND_WEBHOOK_SECRET` | Leave blank for now — filled in Phase 6 |

> **These never go in the repo.** Script Properties aren't visible to people you
> share the Sheet with, and aren't in git. If an API key ever lands in a commit,
> rotate it in Resend immediately — git history is forever.

Now edit the **`Config` tab** and replace the placeholders:

| Key | Set to |
|---|---|
| `FROM_EMAIL` | `dispatch@mail.aima.productions` |
| `POSTAL_ADDRESS` | **Your real street address.** Currently a placeholder. |
| `ADMIN_EMAIL` | Where send summaries and failure alerts go |
| `REPLY_TO` | A monitored human inbox — replies improve sender reputation |

Leave the tuning keys (`BATCH_SIZE`, `THROTTLE_MS`, `SUNSET_DAYS`, …) alone
unless you have a reason.

> ### ✅ Gate 2
> Three Script Properties exist. `POSTAL_ADDRESS` contains a real address with
> no angle brackets left in it.

---

## Phase 3 · Deploy the web app

1. **Deploy → New deployment → ⚙ → Web app.**
2. Settings — both matter:
   - **Execute as:** `Me`
   - **Who has access:** `Anyone`  ← *not* "Anyone with Google account". Your
     subscribers aren't logged into Google.
3. Deploy. Copy the **Web app URL** — it ends in `/exec`.

> **Every time you edit `Code.gs`, you must Deploy → New deployment (or Manage
> deployments → edit → New version).** Saving alone does nothing to the live URL.
> Silently serving stale code is the most common "why isn't my fix working".

> ### ✅ Gate 3
> Paste `<YOUR_EXEC_URL>?action=health` into a browser.
> You should see `{"ok":true,"ts":"2026-..."}`.

---

## Phase 4 · Wire the endpoint into the site

**One file.** This is the whole point of the shared-script refactor.

Open `docs/aima-newsletter.js`, line ~30:

```js
var AIMA_ENDPOINT =
  'https://script.google.com/macros/s/REPLACE_WITH_DEPLOYMENT_ID/exec';
```

Replace with your real `/exec` URL. Commit and push.

That single value now serves: all 40 article signup forms, `/newsletter/index.html`,
`/newsletter/preferences.html`, and `/newsletter/goodbye.html`.

> ### ✅ Gate 4
> `grep -rl REPLACE_WITH_DEPLOYMENT_ID .` returns **nothing**.
> GitHub Pages has rebuilt (check the Actions tab).

---

## Phase 5 · Smoke test the full loop

Do this with your own address, on the live site, in order.

| # | Action | Expect |
|---|---|---|
| 1 | Open any article, scroll to the card beside the author bio | Form renders: first name + email + consent |
| 2 | Submit **without** ticking consent | "One box left" — no row written |
| 3 | Submit `notanemail` | "That address looks incomplete" |
| 4 | Submit your real address, consent ticked | Form collapses to "Check your inbox" |
| 5 | Check the `Subscribers` tab | One row · `first_name` filled · `status=pending` · `cadence=weekly` · `source=article_end` |
| 6 | Check your inbox | Confirmation email, AIMA branded, from your subdomain |
| 7 | Click the confirm link | Lands on `/newsletter/confirmed.html`; row flips to `status=active`, `confirmed_at` filled |
| 8 | Check inbox again | Welcome email arrives |
| 9 | Click "Get fewer emails" in the welcome footer | `/newsletter/preferences.html` loads with your address shown |
| 10 | Tick "Pause everything", Save | "Saved" · `status` flips to `paused` |
| 11 | Click "Unsubscribe instantly" | `/newsletter/goodbye.html`; row flips to `unsubscribed` |
| 12 | Sign up again with the same address | Works — row reactivates to `pending` |

**Also check the spam folder on step 6.** If it landed there, stop and fix
deliverability before going further — do not start sending volume into spam.

> ### ✅ Gate 5
> All 12 pass. Delete your test row from `Subscribers` before launch, or leave it
> — it's a fine canary.

---

## Phase 6 · Webhooks (bounces and complaints)

Without this, hard bounces and spam complaints never suppress, and your domain
reputation erodes with no visible cause.

1. Resend → **Webhooks → Add Webhook**.
2. Endpoint: `<YOUR_EXEC_URL>?action=webhook`
3. Events: `email.sent`, `email.delivered`, `email.bounced`, `email.complained`,
   `email.opened`, `email.clicked`
4. Copy the **Signing Secret** (starts `whsec_`) into the `RESEND_WEBHOOK_SECRET`
   Script Property from Phase 2.
5. Resend → **Send test event**.

> ### ✅ Gate 6
> A row appears in the `Events` tab. If nothing appears, the signature check is
> rejecting it — confirm the secret was pasted whole, including the `whsec_` prefix.

---

## Phase 7 · First send and warm-up

### Install the triggers

Run `installTriggers` in the Apps Script editor. Creates three:
`sendWeeklyDigest` (Thu 08:00 PT) · `rollupEngagement` (hourly) ·
`hygieneSweep` (03:00 PT daily).

It also deletes any dangling `sendDailyDispatch` trigger from an install predating
the weekly-only change — that function no longer exists and would throw on fire.

### Queue an issue

Add one row to `ContentQueue`:

| Column | Value |
|---|---|
| `issue_id` | `W-2026-W33` |
| `send_date` | the Thursday you want it to go |
| `cadence` | `weekly` (the only value) |
| `status` | `scheduled` |
| `subject` | ≤ 45 characters |
| `preheader` | 40–90 chars, **not** a repeat of the subject |
| `article_title` / `article_dek` / `article_url` | from the article |
| `hero_image_url` / `hero_alt` | 1200×630, alt text is required |
| `read_time` / `category` | e.g. `12 min read` / `AI Science` |
| `promo_slot_1` | `book_paperboy` |
| `promo_slot_2` | `auto` (weighted rotation) or a specific `promo_id` |

Leave `sent_at`, `recipients` and `cursor` empty — the
script owns those.

> **Weekly only.** There is one send job, one template, one list. The `cadence`
> column is retained and always reads `weekly`, so a second tier could be added
> later without a schema migration — but nothing in the UI offers a choice and
> no daily trigger exists.

### Warm up — do not skip

A cold domain that blasts 1,000 messages on day one gets filtered, and the
reputation damage takes weeks to undo.

| Days | Max recipients/day | Watch |
|---|---|---|
| 1–3 | 50 | bounce rate |
| 4–7 | 150 | bounce rate |
| 8–14 | 500 | complaint rate |
| 15–21 | 1,500 | complaint rate |
| 22+ | full list | weekly review |

The product is weekly by design. If you ever want a daily tier, it is a content-supply
problem before it is a technical one — bank ~20 issues first.

> ### ✅ Gate 7
> First send: check `SendLog` for one row per recipient with `status=sent`, and
> confirm the admin summary email arrived.

---

## Kill switch

Set `KILL_SWITCH` = `TRUE` in the `Config` tab. Every send aborts at the next
trigger cycle. No deploy, no code edit, takes effect within the hour.

Use it if: complaint rate spikes above 0.1%, an issue goes out with an error, or
you see anything you don't understand in `SendLog`.

To resume: set it back to `FALSE`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Form spins forever | Endpoint still the placeholder, or deployment not "Anyone" | Check Gate 3 and Gate 4 |
| `?action=health` returns HTML not JSON | Deployment access is "Anyone with Google account" | Redeploy with `Anyone` |
| Confirmation email never arrives | Domain unverified, or `FROM_EMAIL` doesn't match the verified domain | Gate 0; check Resend → Emails for the failure |
| Confirm link → `expired.html` | Link older than 7 days, already used, or `HMAC_SECRET` changed | Rotating `HMAC_SECRET` invalidates every outstanding token — never rotate casually |
| Code change has no effect | Saved but not redeployed | Deploy → New deployment |
| Send stops partway | 6-minute Apps Script ceiling | Normal — `resumeSend` self-schedules in 1 min. Check `cursor`. |
| `SendLog` shows `failed` | Resend 4xx/5xx | Read the `error` column; 402 = out of credits |
| Landed in spam | Warm-up skipped, or DMARC misconfigured | Pause, verify Gate 0, restart warm-up |

---

## Weekly, after launch

- **Resend dashboard** — complaint rate. Below 0.1%. Never at 0.3%.
- **Google Postmaster Tools** — add `mail.aima.productions`. Domain reputation and one-click unsubscribe health.
- **`Subscribers` tab** — `bounced` and `complained` counts trending flat, not up.
- **`ContentQueue`** — anything stuck at `sending` or `failed`.

---

## Still open

- **`assets/aima-og-cover.jpg` is missing.** `index.html` and `careers.html` both
  point `og:image` at it, so every link preview of your homepage renders blank.
  Unrelated to the newsletter; noted so it isn't lost.
- **Five articles link to `http://joselitosering.github.io/...`** — insecure scheme
  and the non-canonical domain.
- **Home page article grid is hand-maintained.** Four cards: one pinned, one
  recent per author. They go stale when someone publishes.
- **Album artwork** for the two music rows in `PromoAssets` is blank.

---

## Sources

Resend. "Verified Domains." *Resend Docs*, https://resend.com/docs/dashboard/domains/introduction.

Resend. "What If My Domain Is Not Verifying?" *Resend Docs*, https://resend.com/docs/knowledge-base/what-if-my-domain-is-not-verifying.

Google. "Quotas for Google Services." *Apps Script Documentation*, https://developers.google.com/apps-script/guides/services/quotas.

Red Sift. "2026 Bulk Email Sender Requirements Checklist." *Red Sift Guides*, 2026, https://redsift.com/guides/bulk-email-sender-requirements.
