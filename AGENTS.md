# AGENTS.md

Static GitHub Pages site describing the Netresearch Agent Engineering System —
the learning/enforcement loop behind retro-skill, skill-repo-skill,
automated-assessment-skill and agent-harness-skill.

Live: https://netresearch.github.io/agent-engineering/

## Project Structure

- `public/index.html` — the complete page: styles, search, theme switching,
  JSON-LD, local Chrome `LanguageModel` Q&A with deterministic search fallback.
  No build step; edit it directly.
- `public/og-image.png` — committed social preview, rendered from
  `scripts/og-template.html` via `node scripts/render-og.mjs`. Never edit the
  PNG directly; edit the template and re-render.
- `public/llms.txt`, `public/robots.txt`, `public/sitemap.xml` — machine-facing
  contract; `scripts/verify_site.py` cross-checks them against the page.
- `.github/workflows/pages.yml` publishes `public/` through GitHub Pages.

## Gates (run before every push)

```
python3 scripts/verify_site.py     # meta, JSON-LD, a11y semantics, links, llms.txt contract
npm ci --ignore-scripts && npm run axe   # WCAG 2.1 AA in a real browser, light + dark
```

Both run in CI on every push to `main`; a red gate blocks the deploy.

## Guidelines

- Keep the page static and self-contained: no third-party font, script,
  analytics or CSS request. `verify_site.py` enforces this.
- The base URL `https://netresearch.github.io/agent-engineering/` appears in
  `index.html` (canonical/OG/JSON-LD), `robots.txt`, `sitemap.xml` and
  `llms.txt`; if the repo ever moves, change all of them together —
  `verify_site.py` pins them.
- Preserve Netresearch brand colors, logo usage, and footer link.
- Do not add secrets or deployment credentials to the repository.

## Deployment & Git

- `main` is the **deploy branch**: every push to `main` triggers
  `.github/workflows/pages.yml` and publishes within ~3–4 minutes.
- This is a single-maintainer static site, so committing **directly to `main`**
  is the accepted flow here — a deliberate, repo-scoped exception to the usual
  "feature branches only" rule. No PR overhead is required for site edits.
- Sign off every commit (`git commit -s`).
- Pin all GitHub Actions to full commit SHAs (org policy enforces it);
  netresearch-owned reusable workflows stay on `@main`.
