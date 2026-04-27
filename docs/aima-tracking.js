/**
 * aima-tracking.js
 * AIMA Centralized Analytics & Event Tracking
 * Covers: GA4 (G-VCTF4DKBD5), Meta Pixel (941204972168187), TikTok Pixel (D7NFLLRC77UB8JB2C5N0)
 * Version: 1.0.0
 * Auto-fires correct events per page. No manual event code needed per page.
 */

(function () {
  'use strict';

  // ─── PAGE MAP ────────────────────────────────────────────────────────────────
  // Maps URL path patterns to page metadata and which events to fire.

  const PAGE_MAP = [
    {
      match: /^\/$|\/index\.html/,
      id: 'homepage',
      name: 'AIMA Homepage',
      events: ['ViewContent', 'ClickButton']
    },
    {
      match: /\/services/,
      id: 'services',
      name: 'AIMA Services',
      events: ['ViewContent', 'ClickButton']
    },
    {
      match: /\/rates/,
      id: 'rates',
      name: 'AIMA Rates',
      events: ['ViewContent', 'ClickButton']
    },
    {
      match: /\/gallery/,
      id: 'gallery',
      name: 'AIMA Project Gallery',
      events: ['ViewContent', 'Search']
    },
    {
      match: /\/insights/,
      id: 'insights',
      name: 'AIMA Insights',
      events: ['ViewContent', 'Search']
    },
    {
      match: /\/careers/,
      id: 'careers',
      name: 'AIMA Careers & EP Program',
      events: ['ViewContent', 'ClickButton', 'Lead']
    },
    {
      match: /\/contact/,
      id: 'contact',
      name: 'AIMA Contact',
      events: ['ViewContent', 'ClickButton', 'Lead']
    },
    {
      match: /\/aima-article-/,
      id: 'article',
      name: 'AIMA Article',
      events: ['ViewContent']
    },
    {
      match: /\/(apophis|bellicose|pain|voltx|ravenewworld|[a-z]+-project)/,
      id: 'project',
      name: 'AIMA Project',
      events: ['ViewContent', 'ClickButton']
    }
  ];

  // ─── UTILITIES ───────────────────────────────────────────────────────────────

  /**
   * SHA-256 hash using Web Crypto API (async, returns hex string).
   * Used for PII before passing to ttq.identify.
   */
  async function sha256(str) {
    if (!str) return '';
    const buffer = await crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(str.trim().toLowerCase())
    );
    return Array.from(new Uint8Array(buffer))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }

  /**
   * Resolve current page config from PAGE_MAP.
   * Falls back to generic if no match.
   */
  function resolvePage() {
    const path = window.location.pathname;

    // Check for article slug in meta tag first (most specific)
    const metaId   = document.querySelector('meta[name="article:id"]')?.content;
    const metaName = document.querySelector('meta[name="article:title"]')?.content
                  || document.querySelector('meta[property="og:title"]')?.content;

    for (const page of PAGE_MAP) {
      if (page.match.test(path)) {
        return {
          id:     metaId   || page.id,
          name:   metaName || page.name,
          events: page.events
        };
      }
    }

    // Generic fallback
    return {
      id:     'page-' + path.replace(/\//g, '-').replace(/^-/, '') || 'unknown',
      name:   metaName || document.title || 'AIMA Page',
      events: ['ViewContent']
    };
  }

  /**
   * Safe GA4 event wrapper.
   */
  function gaEvent(eventName, params) {
    if (typeof gtag === 'function') {
      gtag('event', eventName, params);
    }
  }

  /**
   * Safe Meta Pixel event wrapper.
   */
  function fbEvent(eventName, params) {
    if (typeof fbq === 'function') {
      fbq('track', eventName, params);
    }
  }

  /**
   * Safe TikTok event wrapper.
   */
  function ttEvent(eventName, params) {
    if (typeof ttq !== 'undefined' && typeof ttq.track === 'function') {
      ttq.track(eventName, params);
    }
  }

  // ─── EVENT HANDLERS ──────────────────────────────────────────────────────────

  /**
   * ViewContent — fires on page load for content pages.
   */
  function fireViewContent(page) {
    const payload = {
      contents: [{
        content_id:   page.id,
        content_type: 'product',
        content_name: page.name
      }]
    };

    // GA4
    gaEvent('view_item', {
      items: [{ item_id: page.id, item_name: page.name }]
    });

    // Meta Pixel
    fbEvent('ViewContent', {
      content_ids:  [page.id],
      content_name: page.name,
      content_type: 'product'
    });

    // TikTok
    ttEvent('ViewContent', payload);
  }

  /**
   * ClickButton — attaches to all elements with [data-track-cta] or .aima-cta class.
   * Usage: <a class="aima-cta" data-cta-id="cta-hero" data-cta-label="Get Started">
   */
  function bindClickButtons(page) {
    const ctaSelectors = [
      '[data-track-cta]',
      '.aima-cta',
      '.btn-primary',
      '.cta-btn',
      'a[href*="calendly"]',
      'a[href*="contact"]',
      'a[href*="rates"]'
    ];

    document.querySelectorAll(ctaSelectors.join(',')).forEach(el => {
      // Prevent double-binding
      if (el.dataset.trackingBound) return;
      el.dataset.trackingBound = 'true';

      el.addEventListener('click', function () {
        const ctaId    = this.dataset.ctaId    || this.dataset.trackCta || page.id + '-cta';
        const ctaLabel = this.dataset.ctaLabel || this.innerText?.trim() || 'CTA';

        const payload = {
          contents: [{
            content_id:   ctaId,
            content_type: 'product',
            content_name: ctaLabel
          }]
        };

        // GA4
        gaEvent('select_content', {
          content_type: 'cta',
          item_id:      ctaId,
          item_name:    ctaLabel
        });

        // Meta Pixel
        fbEvent('Lead', { content_name: ctaLabel, content_category: 'CTA' });

        // TikTok
        ttEvent('ClickButton', payload);
      });
    });
  }

  /**
   * Search — hooks into filter/search inputs.
   * Looks for inputs with [data-track-search] or common filter patterns.
   */
  function bindSearch(page) {
    const searchSelectors = [
      '[data-track-search]',
      '.filter-btn',
      '.category-filter',
      '#search-input',
      'input[type="search"]'
    ];

    // Debounce helper
    let searchTimer;
    function debounce(fn, delay) {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(fn, delay);
    }

    // Input fields
    document.querySelectorAll('input[type="search"], [data-track-search]').forEach(el => {
      if (el.dataset.trackingBound) return;
      el.dataset.trackingBound = 'true';

      el.addEventListener('input', function () {
        const query = this.value?.trim();
        if (!query) return;
        debounce(() => fireSearch(page, query), 800);
      });
    });

    // Filter buttons (click)
    document.querySelectorAll('.filter-btn, .category-filter').forEach(el => {
      if (el.dataset.trackingBound) return;
      el.dataset.trackingBound = 'true';

      el.addEventListener('click', function () {
        const query = this.dataset.filter || this.innerText?.trim() || 'filter';
        fireSearch(page, query);
      });
    });
  }

  function fireSearch(page, query) {
    const payload = {
      contents: [{
        content_id:   page.id,
        content_type: 'product',
        content_name: page.name
      }],
      search_string: query
    };

    // GA4
    gaEvent('search', { search_term: query });

    // Meta Pixel
    fbEvent('Search', { search_string: query, content_category: page.name });

    // TikTok
    ttEvent('Search', payload);
  }

  /**
   * Lead — fires on successful form submission.
   * Triggered by calling window.aimaTrackLead(formId, formName) from your form handler.
   * Also auto-detects forms with [data-track-lead].
   */
  function bindLead(page) {
    // Auto-detect forms
    document.querySelectorAll('form[data-track-lead], [data-track-lead]').forEach(el => {
      if (el.dataset.trackingBound) return;
      el.dataset.trackingBound = 'true';

      el.addEventListener('submit', function (e) {
        const formId   = this.dataset.formId   || page.id + '-form';
        const formName = this.dataset.formName || page.name + ' Form';
        fireLead(formId, formName);
      });
    });
  }

  function fireLead(formId, formName) {
    const payload = {
      contents: [{
        content_id:   formId,
        content_type: 'product',
        content_name: formName
      }]
    };

    // GA4
    gaEvent('generate_lead', {
      form_id:   formId,
      form_name: formName
    });

    // Meta Pixel
    fbEvent('Lead', {
      content_name:     formName,
      content_category: 'Form Submission'
    });

    // TikTok
    ttEvent('Lead', payload);
  }

  /**
   * ttq.identify — fires only on form pages when PII is available.
   * Call window.aimaIdentify({ email, phone, id }) from your form success handler.
   * Hashes all values automatically with SHA-256.
   */
  async function aimaIdentify({ email = '', phone = '', id = '' } = {}) {
    const [hashedEmail, hashedPhone, hashedId] = await Promise.all([
      sha256(email),
      sha256(phone),
      sha256(id)
    ]);

    if (typeof ttq !== 'undefined' && typeof ttq.identify === 'function') {
      ttq.identify({
        email:       hashedEmail   || undefined,
        phone_number: hashedPhone  || undefined,
        external_id: hashedId      || undefined
      });
    }
  }

  // ─── PUBLIC API ──────────────────────────────────────────────────────────────
  // Expose manual triggers for use in form handlers across AIMA pages.

  window.aimaTrackLead     = fireLead;
  window.aimaTrackSearch   = fireSearch;
  window.aimaIdentify      = aimaIdentify;

  // ─── INIT ────────────────────────────────────────────────────────────────────

  function init() {
    const page = resolvePage();

    // Always fire ViewContent if in event list
    if (page.events.includes('ViewContent')) {
      fireViewContent(page);
    }

    // Bind CTA buttons
    if (page.events.includes('ClickButton')) {
      bindClickButtons(page);
    }

    // Bind search/filter
    if (page.events.includes('Search')) {
      bindSearch(page);
    }

    // Bind lead forms
    if (page.events.includes('Lead')) {
      bindLead(page);
    }
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
