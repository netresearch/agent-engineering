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

# Structures the two language pages describe in parallel, and that llms.txt
# also counts. Prose drift is invisible to a structural gate, but a count is
# not: a card added to one page or to the pages but not to llms.txt shows up
# here as a number that no longer matches.
COUNTED_STRUCTURES = (
    ("destination cards", r'<article class="destination"'),
    ("system-map steps", r'<article class="map-card"><span class="num">'),
    ("loop cards", r'<article class="map-card"><h3>'),
    ("principle steps", r"<div><strong>\d+\."),
    ("memory forms", r'<div class="source-row memory-row">'),
)

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}

REQUIRED_META = (
    (r'<meta name="description" content="[^"]+"', "meta description"),
    (r'<meta name="twitter:card"', "twitter:card"),
    (r'<script type="application/ld\+json">', "JSON-LD"),
)

# Canonical URL, og-image and document language differ per language version;
# a page missing here fails the build rather than passing half-checked.
PAGE_EXPECTATIONS = {
    "index.html": {"canonical": BASE_URL, "og_image": f"{BASE_URL}og-image.png", "lang": "de"},
    "en/index.html": {"canonical": f"{BASE_URL}en/", "og_image": f"{BASE_URL}og-image-en.png", "lang": "en"},
}

HREFLANGS = (("de", BASE_URL), ("en", f"{BASE_URL}en/"), ("x-default", BASE_URL))

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

    for expected_page in PAGE_EXPECTATIONS:
        if not (PUBLIC / expected_page).exists():
            errors.append(f"missing public/{expected_page}")

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

        expected = PAGE_EXPECTATIONS.get(name)
        if expected is None:
            errors.append(f"{name}: page not listed in PAGE_EXPECTATIONS")
        else:
            if f'<link rel="canonical" href="{expected["canonical"]}">' not in html:
                errors.append(f"{name}: canonical is not {expected['canonical']}")
            if f'<meta property="og:image" content="{expected["og_image"]}">' not in html:
                errors.append(f"{name}: og:image is not {expected['og_image']}")
            if not re.search(r'<html\b[^>]*\blang="' + expected["lang"] + '"', html):
                errors.append(f"{name}: <html> lang is not \"{expected['lang']}\"")
        for lang_code, target in HREFLANGS:
            if f'hreflang="{lang_code}" href="{target}"' not in html:
                errors.append(f"{name}: missing hreflang {lang_code} → {target}")

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
    # promises must exist on BOTH language versions, and its URLs must match.
    llms = (PUBLIC / "llms.txt").read_text(encoding="utf-8") if (PUBLIC / "llms.txt").exists() else ""
    if (PUBLIC / "llms.txt").exists() and not llms.strip():
        # An empty file satisfies the existence check below while making every
        # `if llms` guard fall through, so the whole contract would pass vacuously.
        errors.append("llms.txt is empty — every check against it would pass without measuring anything")
    for page_name in PAGE_EXPECTATIONS:
        if not (PUBLIC / page_name).exists():
            continue
        html = (PUBLIC / page_name).read_text(encoding="utf-8")
        ids = set(re.findall(r'\sid="([^"]+)"', html))
        for section in re.findall(r"^- #([a-z-]+) —", llms, flags=re.M):
            if section not in ids:
                errors.append(f"llms.txt promises section #{section}, {page_name} has no such id")
    for required_url in (BASE_URL, f"{BASE_URL}en/"):
        if llms and required_url not in llms:
            errors.append(f"llms.txt does not name {required_url}")

    # Counted structures: identical on both language pages, and the destination
    # list in llms.txt has to carry the same number of entries as the pages
    # render — the case that went undetected once already.
    counts: dict[str, dict[str, int]] = {}
    for page_name in PAGE_EXPECTATIONS:
        if not (PUBLIC / page_name).exists():
            continue
        html = (PUBLIC / page_name).read_text(encoding="utf-8")
        counts[page_name] = {
            label: len(re.findall(pattern, html))
            for label, pattern in COUNTED_STRUCTURES
        }
        # A count of zero is never a legitimate state here, and without this
        # floor a stale pattern makes the parity comparison 0 == 0 — the gate
        # would report success while measuring nothing.
        for label, count in counts[page_name].items():
            if count == 0:
                errors.append(
                    f"{page_name}: no {label} matched — the pattern in COUNTED_STRUCTURES "
                    "no longer fits the markup, so this check is measuring nothing"
                )
    if len(counts) > 1:
        reference, *others = counts
        for label, _ in COUNTED_STRUCTURES:
            for other in others:
                if counts[other][label] != counts[reference][label]:
                    errors.append(
                        f"{label}: {reference} has {counts[reference][label]}, "
                        f"{other} has {counts[other][label]} — the language versions must match"
                    )

    heading = re.search(r"^## The (\w+) retro destinations\s*$", llms, flags=re.M)
    if llms and not heading:
        errors.append("llms.txt has no '## The <number> retro destinations' heading")
    elif heading:
        bullets = re.findall(
            r"^- [a-z-]+:", llms[heading.end():].split("\n##", 1)[0], flags=re.M
        )
        written = heading.group(1).lower()
        promised = int(written) if written.isdigit() else NUMBER_WORDS.get(written)
        if promised is None:
            errors.append(f"llms.txt destinations heading: unknown number word {heading.group(1)!r}")
        elif promised != len(bullets):
            errors.append(
                f"llms.txt announces {promised} destinations but lists {len(bullets)}"
            )
        for page_name, page_counts in counts.items():
            if page_counts["destination cards"] != len(bullets):
                errors.append(
                    f"llms.txt lists {len(bullets)} destinations, "
                    f"{page_name} renders {page_counts['destination cards']} destination cards"
                )

    sitemap = (PUBLIC / "sitemap.xml").read_text(encoding="utf-8") if (PUBLIC / "sitemap.xml").exists() else ""
    for required_url in (BASE_URL, f"{BASE_URL}en/"):
        if f"<loc>{required_url}</loc>" not in sitemap:
            errors.append(f"sitemap.xml does not list {required_url}")
    robots = (PUBLIC / "robots.txt").read_text(encoding="utf-8") if (PUBLIC / "robots.txt").exists() else ""
    if f"Sitemap: {BASE_URL}sitemap.xml" not in robots:
        errors.append("robots.txt does not point at the sitemap under the base URL")

    for required in ("sitemap.xml", "robots.txt", "llms.txt", ".nojekyll",
                     "og-image.png", "og-image-en.png", "favicon.svg"):
        if not (PUBLIC / required).exists():
            errors.append(f"missing public/{required}")

    for message in errors:
        print(f"ERROR {message}", file=sys.stderr)

    print(f"\nverify_site: {len(pages)} pages checked, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
