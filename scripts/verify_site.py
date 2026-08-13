#!/usr/bin/env python3
"""Build gate for the static landing page.

Checks what visitors and crawlers actually receive. Exit code 1 fails the build.

    python3 scripts/verify_site.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_accessibility import check_accessibility  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

BASE_URL = "https://netresearch.github.io/agent-engineering/"

errors: list[str] = []

PLACEHOLDERS = ("Loading…", "Loading...", "TBD", "Lorem ipsum")

REQUIRED_META = (
    (r'<link rel="canonical" href="' + re.escape(BASE_URL) + '"', "canonical (base URL)"),
    (r'<meta name="description" content="[^"]+"', "meta description"),
    (r'<meta property="og:image" content="' + re.escape(BASE_URL) + r'og-image\.png"', "og:image (base URL)"),
    (r'<meta name="twitter:card"', "twitter:card"),
    (r'<script type="application/ld\+json">', "JSON-LD"),
)

# The page argues for source-of-truth discipline and ships self-contained: a
# third-party font, script or image request contradicts its own text.
ALLOWED_ASSET_PREFIXES = ("https://netresearch.github.io/",)


def strip_markup(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>.*?</script\b[^>]*>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b[^>]*>.*?</style\b[^>]*>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def main() -> int:
    pages = sorted(PUBLIC.rglob("index.html"))
    if not pages:
        print("verify_site: no public/index.html", file=sys.stderr)
        return 1

    for page in pages:
        name = page.relative_to(PUBLIC).as_posix()
        html = page.read_text(encoding="utf-8")
        text = strip_markup(html)

        for placeholder in PLACEHOLDERS:
            if placeholder in text:
                errors.append(f"{name}: placeholder text in the initial HTML: {placeholder!r}")

        for pattern, label in REQUIRED_META:
            if not re.search(pattern, html):
                errors.append(f"{name}: no {label}")

        for block in re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', html):
            try:
                parsed = json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f"{name}: invalid JSON-LD: {exc}")
                continue
            for node in parsed.get("@graph", [parsed]):
                if "@type" not in node:
                    errors.append(f"{name}: JSON-LD node without @type")

        # Accessibility and semantics decidable from the markup alone.
        for problem in check_accessibility(html):
            errors.append(f"{name}: {problem}")

        # The logo is an inline SVG; it must still appear exactly once.
        logos = re.findall(r"<title>Netresearch DTT GmbH</title>", html)
        if len(logos) != 1:
            errors.append(f"{name}: the logo appears {len(logos)} times, expected exactly once")

        # Every in-page anchor must resolve — a landing page whose table of
        # contents points nowhere fails silently for every visitor.
        ids = set(re.findall(r'\sid="([^"]+)"', html))
        for anchor in set(re.findall(r'href="#([^"]+)"', html)):
            if anchor and anchor not in ids:
                errors.append(f"{name}: broken internal link: #{anchor}")

        for asset in re.findall(r'<(?:script|link|img)[^>]+(?:src|href)="(https?://[^"]+)"', html):
            if not asset.startswith(ALLOWED_ASSET_PREFIXES):
                errors.append(f"{name}: loads a third-party asset: {asset}")

    # llms.txt is the machine-readable contract for the page: every section it
    # promises must exist, and its canonical URL must match.
    llms = (PUBLIC / "llms.txt").read_text(encoding="utf-8") if (PUBLIC / "llms.txt").exists() else ""
    html = pages[0].read_text(encoding="utf-8")
    ids = set(re.findall(r'\sid="([^"]+)"', html))
    for section in re.findall(r"^- #([a-z-]+) —", llms, flags=re.M):
        if section not in ids:
            errors.append(f"llms.txt promises section #{section}, index.html has no such id")
    if llms and BASE_URL not in llms:
        errors.append("llms.txt does not name the canonical page URL")

    sitemap = (PUBLIC / "sitemap.xml").read_text(encoding="utf-8") if (PUBLIC / "sitemap.xml").exists() else ""
    if f"<loc>{BASE_URL}</loc>" not in sitemap:
        errors.append("sitemap.xml does not list the canonical URL")
    robots = (PUBLIC / "robots.txt").read_text(encoding="utf-8") if (PUBLIC / "robots.txt").exists() else ""
    if f"Sitemap: {BASE_URL}sitemap.xml" not in robots:
        errors.append("robots.txt does not point at the sitemap under the base URL")

    for required in ("sitemap.xml", "robots.txt", "llms.txt", ".nojekyll", "og-image.png", "favicon.svg"):
        if not (PUBLIC / required).exists():
            errors.append(f"missing public/{required}")

    for message in errors:
        print(f"ERROR {message}", file=sys.stderr)

    print(f"\nverify_site: {len(pages)} pages checked, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
