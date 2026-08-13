# Newsletter confirm-link fix — session report (2026-08-09)

## Final state: working, verified end to end

Confirmed three ways, in this order: a server-side simulation (`testFullFlow`),
a real Execution log showing `PASS — row 2 is now active`, and a real signup
through the Subscribe button on a live article page.

- **Signup capture** — name + email write to the `Subscribers` tab as `pending`.
- **Double opt-in confirm** — clicking the emailed link flips the row to
  `active` and sends the welcome email.
- **Endpoint alignment** — `docs/aima-newsletter.js` and the `WEBAPP_URL`
  Script Property both point at the same deployment:
  `https://script.google.com/macros/s/AKfycbxrhyPAizj-y5kHevgR79NRTsKJ1EPqFdWxEHUEpWvEHcJcjrsnywZ9I1vnGp4zvsFVXw/exec`
- **Email branding** — logo is now a real Anton wordmark (`img/email/aima-logo-light.png`
  / `-dark.png`, extracted from the existing `img/AIMA LOGO.jpg` and recoloured
  per theme), swapped via `prefers-color-scheme`. Confirmed live at 200 OK.

## What was actually broken, and the real root cause

**"That link didn't work" was our own `newsletter/expired.html` page**, not a
Google error, not a multi-account browser issue. `confirm_()` in `Code.gs`
looks up the subscriber row *before* it checks the token, and sends you to
`expired.html` if the row isn't found — regardless of whether the token is
valid.

`testEmail()` — the function used to test all day — only calls
`sendConfirm_()`. It never writes a row to `Subscribers`. Every confirm link
built from a `testEmail()` send pointed at a row that never existed, so every
click failed the same way, on every URL, every browser, every account. That
is the entire explanation; there was no browser or account bug.

I floated a "multiple Google accounts" theory from a web search before
checking the actual code path. That was a real mistake — it wasted a round
trip and wasn't grounded in this codebase. Flagging it here so the next
session doesn't repeat it: **when a link/redirect fails in this project,
check `confirm_()` / `unsubscribe_()` / `goTo_()` in `Code.gs` first**, not
generic Apps Script behavior.

## Other real bugs fixed this session (in `Code.gs`)

1. **`baseUrl_()` trusted `getUrl()`**, which returns the `/dev` URL when
   called from the editor (confirmed against Google's own docs). Any
   `testEmail()` run from the editor mailed a dead `/dev` link. Fixed:
   `baseUrl_()` now only trusts a stored `/exec` URL; `getUrl()` is a
   fallback only when it's unambiguously `/exec`. Added `setWebAppUrl()` to
   make setting that URL a deliberate, validated step.
2. **`goTo_()` used `<meta refresh>`**, which only navigates the sandboxed
   iframe Apps Script serves HtmlOutput inside — could leave a visitor on a
   blank Google shell after a successful confirm. Fixed: navigates
   `window.top` via script, with a real `target="_top"` link as fallback.
3. **Two live deployments existed simultaneously** with different `/exec`
   URLs (`AKfycby9FgDX…` and `AKfycbxrhyPAizj…`) — the signup forms and the
   email links were pointing at different ones. Both answered `{"ok":true}`
   on health checks, so nothing looked broken until traced. Aligned to the
   one the user confirmed is current (`AKfycbxrhyPAizj…`).
4. **My own diagnostic was worthless**: an early self-test only checked
   HTTP status code on the confirm URL. Apps Script wraps *both* the
   success redirect and the expired-page redirect in the same sandboxed
   HTML shell, so a `200` proved nothing about which page a visitor
   actually lands on. Replaced with `testFullFlow()`, which checks the
   actual row status after simulating a real click — a real PASS/FAIL, not
   a proxy signal.

## Added to `Code.gs` for next time

- `showLinks()` — prints the exact confirm/unsubscribe URLs and which URL
  source (stored / live / constant) is being used, without sending mail.
- `testFullFlow()` — creates or resets a real pending row, builds the actual
  link, runs it through `confirm_()` exactly as the deployed app would, and
  asserts the row flips to `active`. This is the right function to run
  after any future change to `confirm_`, `token_`, or `findRow_` — not
  `testEmail()`, which only proves mail sends, not that the link works.

## Deploying code changes — the trap to avoid

Saving in the Apps Script editor does **not** update the live `/exec`
endpoint. Editor runs (like `testFullFlow`) always use the latest saved
code; the deployed URL runs whatever version was active when the deployment
was created. To push a code change to the *same* URL: **Deploy → Manage
deployments → pencil icon on the active deployment → Version: New version →
Deploy.** Using "New deployment" instead mints a different `/exec` URL and
reproduces the exact mismatch bug from this session.

## Not yet tested

- **`unsubscribe_()`** — same shape as `confirm_()` (row lookup, then token
  check), never exercised this session. Same class of bug is possible in
  principle; not verified.
- **`sendWeekly()` / the actual weekly send** — `installWeeklyTrigger()` has
  not been run. No trigger is installed. Nothing will send on a schedule
  until that's done deliberately.
- **Bot resistance** — honeypot + timing gate exist in
  `docs/aima-newsletter.js` but haven't been tested against real bot
  traffic.

## Known gaps, not addressed this session

- **`POSTAL` in `Code.gs` is still a placeholder** (`'AIMA · a Monkey
  Matters LLC production · San Francisco, CA, USA'`), not a real street
  address. CAN-SPAM requires a real physical mailing address in every
  commercial email before sending to anyone beyond test addresses.
- **`Code.gs` is not in git.** It lives only in the Apps Script project
  editor (pasted directly by the user) and in this session's scratch
  outputs — there is no committed copy of the current backend in the
  `aima` repo. Worth deciding whether that's intentional or whether it
  should be added, since right now there's no version history or diff
  trail for the file that runs the entire newsletter backend.
- **One real subscriber row exists** — the test row for
  `joselitovsering@gmail.com`, `source: selftest`, now `active`. Fine to
  leave, relabel, or delete before real subscribers accumulate.
- The repo has ~250 unrelated modified files (agent pipeline, articles,
  etc.) pre-existing from other work — untouched this session, noted here
  only so it isn't mistaken for something this session caused.

## Commits pushed this session

- `d7484b4` — logo PNGs (light + dark) added to `img/email/`
- `64690fd` — signup endpoint pointed at a deployment URL (later found to
  be the wrong one of the two live deployments)
- `2e0ee4f` — signup endpoint corrected to the deployment the user
  confirmed is current

`Code.gs` itself was never committed — see "Known gaps" above.
