# Netresearch Agent Engineering

Static, no-build landing page for the Netresearch Agent Engineering System —
how real agent sessions become durable, verifiable, distributable engineering
knowledge (retro → skills → checkpoints → harness → distribution).

**Live:** https://netresearch.github.io/agent-engineering/

## Files

- `public/index.html` — complete page, styles, search, theme switching,
  JSON-LD, local Chrome `LanguageModel` Q&A and deterministic search fallback
- `public/og-image.png` — social preview, rendered from
  `scripts/og-template.html` (`npm run og`)
- `public/robots.txt`, `public/sitemap.xml`
- `public/llms.txt` — compact machine-readable knowledge summary

No external JavaScript, CSS, analytics, tracking or font request. The CSS
declares Netresearch's Raleway/Open Sans typography with system fallbacks.

## Local AI behavior

The Q&A feature uses `globalThis.LanguageModel` when Chrome exposes the
built-in Prompt API. It checks `availability()` without creating a model
session; a session is created only after a visitor submits a question. The
system prompt contains a compact extraction of this page and requires answers
to use that source only. If the API or model is unavailable, the UI does not
fake an AI response — it returns the highest-scoring relevant sections of the
same page instead.

## Verification

```
python3 scripts/verify_site.py          # markup-decidable gate
npm ci --ignore-scripts && npm run axe  # WCAG 2.1 AA, real browser, light + dark
```

`verify_site.py` checks: one `h1`, heading order, unique IDs, accessible
controls, canonical/OG/JSON-LD, no broken internal links, no third-party
requests, and that `robots.txt`, `sitemap.xml` and `llms.txt` agree with the
page about the base URL and section anchors.

## Deploy

Every push to `main` runs both gates and publishes `public/` via
`.github/workflows/pages.yml` (org-reusable pages-build/pages-deploy
workflows). A red gate blocks the deploy.
