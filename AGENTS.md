# AGENTS.md

Static GitHub Pages site describing the Netresearch Agent Engineering System —
the learning/enforcement loop behind retro-skill, skill-repo-skill,
automated-assessment-skill and agent-harness-skill.

Live: https://netresearch.github.io/agent-engineering/

## Project Structure

- `public/index.html` — the complete German page: styles, search, theme
  switching, JSON-LD, local Chrome `LanguageModel` Q&A with deterministic
  search fallback. No build step; edit it directly.
- `public/en/index.html` — the English version, same structure. **Content
  changes must land in both languages in the same commit**; `verify_site.py`
  pins per-page canonical/og-image/lang and the shared section anchors, but it
  cannot see missing prose — keep the translation in sync yourself. It does
  count the parallel structures (destination cards, system-map and loop cards,
  principle steps) and fails when the two pages disagree or when `llms.txt`
  names a different number of destinations than the pages render. When a
  content model changes, grep the whole of `public/` for the **old** vocabulary
  rather than re-reading the sections you remember — `llms.txt`, the JSON-LD
  answers and the arrow diagram in the `code-block` of the `#learning-loop`
  section all encode it too. `llms.txt` carries one format the gate depends on:
  the destinations heading must read `## The <number> retro destinations`, with
  the number as a word or a digit, followed by one `- name: …` bullet per
  destination.
- `public/og-image.png` / `public/og-image-en.png` — committed social
  previews, rendered from `scripts/og-template.html` /
  `scripts/og-template-en.html` via `node scripts/render-og.mjs`. Never edit
  the PNGs directly; edit the template and re-render. A fresh checkout has no
  `node_modules`, so the render aborts with `Cannot find package 'puppeteer'`;
  run `npm ci` first. Keep any ad-hoc Puppeteer script **inside** the checkout,
  because Node resolves packages upwards from the script's own directory, not
  from the working directory.
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
