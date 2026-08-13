/**
 * Renders public/og-image.png from scripts/og-template.html.
 *
 * The PNG is committed: og:image must resolve as a plain file and the card
 * should only change when someone edits the template on purpose. Re-run after
 * editing the template:
 *
 *   node scripts/render-og.mjs
 */

import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import puppeteer from 'puppeteer';

const here = dirname(fileURLToPath(import.meta.url));
const template = join(here, 'og-template.html');
const target = join(here, '..', 'public', 'og-image.png');

const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage'] });
const page = await browser.newPage();
// deviceScaleFactor 1: og:image consumers expect exactly 1200x630 pixels.
await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
await page.goto(`file://${template}`, { waitUntil: 'networkidle0' });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: target, clip: { x: 0, y: 0, width: 1200, height: 630 } });
await browser.close();
console.log(`Wrote ${target}`);
