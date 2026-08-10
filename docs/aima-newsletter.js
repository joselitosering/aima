/* ============================================================================
 * AIMA DISPATCH — newsletter signup client
 * ----------------------------------------------------------------------------
 * THE ONLY FILE THAT HOLDS THE ENDPOINT. Article pages ship markup only, so
 * redeploying the Apps Script means editing this one line, not 40 files.
 *
 * Usage on any page:
 *   <script src="/docs/aima-newsletter.js" defer></script>
 * and anywhere in the body:
 *   <form data-aima-subscribe data-source="article_end"> … </form>
 *
 * WEEKLY ONLY.
 *
 * The form must contain:
 *   input[name=first_name] asked for on every form
 *   input[name=last_name]  asked for on every form
 *   input[name=email]      required
 *   input[name=consent]    required checkbox   (never pre-checked — GDPR)
 *   input[name=website]    honeypot, visually hidden
 *   [data-aima-msg]        empty div for status messages
 *
 * Captured per signup → Google Sheet `Subscribers`:
 *   email (A) · first_name (B) · last_name (C) · status (D) · source (E)
 *
 * Nothing is ever mailed to an address until the subscriber clicks the
 * one-time confirmation link — that is what moves them pending → active.
 * ==========================================================================*/
(function () {
  'use strict';

  /* ── Replace after deploying Code.gs. This is the only occurrence. ──────── */
  var AIMA_ENDPOINT =
    'https://script.google.com/macros/s/AKfycbxrhyPAizj-y5kHevgR79NRTsKJ1EPqFdWxEHUEpWvEHcJcjrsnywZ9I1vnGp4zvsFVXw/exec';

  /* Exported so /newsletter/goodbye.html can reuse the same value. */
  window.AIMA_ENDPOINT = AIMA_ENDPOINT;

  var MIN_FILL_MS = 2500;
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/;

  var MSG = {
    pending:      { t:'ok',   h:'Check your inbox',
                    b:'We sent a confirmation link to <strong>{email}</strong>. Click it and you&rsquo;re in. It expires in 7 days.' },
    invalid:      { t:'err',  h:'That address looks incomplete',
                    b:'Check for a missing domain &mdash; e.g. <em>you@studio.com</em>' },
    consent:      { t:'err',  h:'One box left',
                    b:'Please tick the consent box so we have a record of your opt-in.' },
    rate_limited: { t:'info', h:'Too many attempts',
                    b:'Give it an hour, or email <a href="mailto:founder@aima.productions">founder@aima.productions</a> and we&rsquo;ll add you manually.' },
    network:      { t:'err',  h:'Couldn&rsquo;t reach the server',
                    b:'Your address wasn&rsquo;t saved. Try once more.' }
  };

  function esc(x) {
    return String(x).replace(/[&<>"']/g, function (c) {
      return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c];
    });
  }

  function show(form, key, email) {
    var box = form.querySelector('[data-aima-msg]');
    if (!box) return;
    var m = MSG[key] || MSG.network;
    box.setAttribute('data-tone', m.t);
    box.innerHTML =
      '<span class="nl-msg-ico">' +
      (m.t === 'ok' ? '&#10003;' : m.t === 'info' ? '&#8987;' : '!') +
      '</span><span><b>' + m.h + '</b>' +
      m.b.replace('{email}', esc(email || '')) + '</span>';
    box.hidden = false;
    box.setAttribute('role', m.t === 'err' ? 'alert' : 'status');
  }

  /* Collapse the form on success. Leaving it submittable is the most common
     way one person ends up with two pending rows and two confirmation emails. */
  function collapse(form, email) {
    var keep = form.querySelector('[data-aima-msg]');
    Array.prototype.slice.call(form.children).forEach(function (el) {
      if (el !== keep && !el.hasAttribute('data-aima-keep')) el.remove();
    });
    show(form, 'pending', email);
  }

  function wire(form) {
    if (form.dataset.aimaWired) return;      // guard against double-binding
    form.dataset.aimaWired = '1';
    form.dataset.rendered = String(Date.now());

    /* Impression event, fired once when the module is actually seen. */
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            if (window.dataLayer) {
              window.dataLayer.push({
                event: 'newsletter_view',
                source: form.dataset.source || 'unknown'
              });
            }
            io.unobserve(e.target);
          }
        });
      }, { threshold: 0.5 });
      io.observe(form);
    }

    form.addEventListener('submit', function (ev) {
      ev.preventDefault();

      var btn      = form.querySelector('button[type="submit"]');
      var emailEl  = form.querySelector('input[name="email"]');
      var email    = (emailEl.value || '').trim().toLowerCase();
      var consent  = form.querySelector('input[name="consent"]');
      var honeypot = form.querySelector('input[name="website"]');
      var nameEl   = form.querySelector('input[name="first_name"]');
      var lastEl   = form.querySelector('input[name="last_name"]');

      /* Bot gates fail SILENTLY and look exactly like success — telling a bot
         it was caught only teaches the operator what to fix. */
      if (honeypot && honeypot.value) { collapse(form, email); return; }
      if (Date.now() - Number(form.dataset.rendered) < MIN_FILL_MS) {
        collapse(form, email); return;
      }

      if (!EMAIL_RE.test(email)) {
        emailEl.setAttribute('aria-invalid', 'true');
        emailEl.focus();
        show(form, 'invalid');
        return;
      }
      emailEl.removeAttribute('aria-invalid');

      if (consent && !consent.checked) { show(form, 'consent'); consent.focus(); return; }

      var original = btn ? btn.innerHTML : '';
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="nl-spin"></span>Confirming…';
      }
      function restore() { if (btn) { btn.disabled = false; btn.innerHTML = original; } }

      var payload = {
        email:        email,
        first_name:   nameEl ? nameEl.value.trim() : '',
        last_name:    lastEl ? lastEl.value.trim() : '',
        source:       form.dataset.source || 'unknown',
        t:            Number(form.dataset.rendered)
      };

      /* text/plain avoids a CORS preflight, which Apps Script web apps do not
         answer. Do NOT "fix" this to application/json — it will start failing. */
      fetch(AIMA_ENDPOINT + '?action=subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: JSON.stringify(payload),
        redirect: 'follow'
      })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.ok) {
          if (window.dataLayer) {
            window.dataLayer.push({
              event: 'newsletter_submit',
              source: payload.source
            });
          }
          collapse(form, email);
        } else {
          restore();
          if (res && res.error === 'invalid_email') {
            emailEl.setAttribute('aria-invalid', 'true');
            show(form, 'invalid');
          } else {
            show(form, res && res.error === 'rate_limited' ? 'rate_limited' : 'network');
          }
        }
      })
      .catch(function () { restore(); show(form, 'network'); });
    });
  }

  function init() {
    document.querySelectorAll('[data-aima-subscribe]').forEach(wire);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
