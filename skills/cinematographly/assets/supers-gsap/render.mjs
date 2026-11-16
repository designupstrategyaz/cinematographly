#!/usr/bin/env node
// SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
// Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
// render.mjs — render one super, hero title or end card from the brand's motion system
// (references/typography-and-captions.md §6b) to a transparent PNG sequence and, with --prores, a
// ProRes 4444 .mov with alpha, ready to lay over the locked cut in Resolve.
//
// WHY THIS EXISTS. §6b rule 10 bakes supers in the finish so every cut-down carries the same motion.
// Keying that by hand in Fusion is redone per aspect ratio. This lane builds the move once from the
// brand's tokens (curves, durations, stagger) and renders it frame-accurately for any preset in
// assets/delivery-formats.json: a paused GSAP timeline is seeked to i / fps for every frame, so frame
// 37 is the same pixels on every run and every machine with the same font.
//
// OPTIONAL. This kit sits outside scripts/ because it needs Node, Playwright and GSAP, which the scripts
// charter (scripts/README.md rule 1) excludes. Fusion stays the default; use this lane when one super
// must ship in several formats, or a series must move identically across episodes.
//
// Usage (from this folder, after `npm ci && npx playwright install chromium-headless-shell`):
//   node render.mjs --spec examples/super.json --format vertical-1080 --out out/super-9x16
//   node render.mjs --spec examples/super.json --format feed-4x5 --fps 30 --out out/super-4x5 --prores out/super-4x5.mov
//   node render.mjs --spec examples/super.json --format vertical-1080 --still 1.5 --out out/check   # one frame to look at
//   add --organic for the looser house safe box (no platform source; never for paid or a disclosure)
//   add --json for a machine-readable summary
//
// Exit codes: 0 rendered · 1 refused (a rule below, a font that failed to load) · 2 usage or IO error.
// Refuses, with the number that fixes it:
//   - dwell below §5's floor: the text must be fully in and still for 1 s + 0.3 s per word when the VO
//     says it ("voiced": true), 1 s per word when it is the only carrier (the default);
//   - any overshoot, on any kind: every one of them is text (house rule C2, 2026-10-26: "No overshoot on
//     text" — §6b rule 5), measured from the entrance curve itself;
//   - a curve whose x values leave [0, 1], or text that leaves the format's safe box (fewer words,
//     never smaller type: §5).
// Warns (doesn't refuse) outside §6b's duration tiers, on an exit slower than the entrance (the sources
// disagree, rule 3), and on a system font (it renders differently on another machine).
//
// WHAT IT CANNOT DO. It does not judge legibility on the real picture: run the caption QA card
// (§9) on the composite, on the brightest background. It does not place the super in time: the edit
// decides where it lands (§6b rule 8, not in the half-second after a hard cut). It does not check
// claims: a price or stat on a super still goes through claims_lint.py and the compliance gate.
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FORMATS = path.join(HERE, '..', 'delivery-formats.json');
const DEFAULTS = { kind: 'super', position: 'lower-left', from: 'left', voiced: false, legal: false,
  color: '#FFFFFF', plate: { color: '#000000', alpha: 0.6 },
  curves: { enter: [0.16, 1, 0.3, 1], exit: [0.4, 0, 1, 1] },          // §6b rule 1: the lab's pair
  ms: { enter: 600, exit: 300, stagger: 25 } };                         // §6b rules 2–4
const TIERS = { super: [450, 760], price: [450, 760], title: [800, 1300], endcard: [800, 1300] };
// ⛔ C2 (2026-10-26): no overshoot on any text, number or UI. Until then a super or price could overshoot
// 9 % and a title or end card 42 %; every kind here is text, so every band is now zero.
const OVERSHOOT_MAX = { super: 0, price: 0, title: 0, endcard: 0 };

const die = (code, msg) => { console.error(msg); process.exit(code); };

function args(argv) {
  const known = ['spec', 'format', 'fps', 'out', 'prores', 'still'], flags = ['organic', 'json'], a = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i].replace(/^--/, '');
    if (flags.includes(k)) { a[k] = true; continue; }
    if (!known.includes(k) || argv[i + 1] === undefined || argv[i + 1].startsWith('--')) die(2, `bad argument ${argv[i]} (flags: ${[...known, ...flags].map((x) => '--' + x).join(' ')})`);
    a[k] = argv[++i];
  }
  for (const k of ['spec', 'format', 'out']) if (!a[k]) die(2, `--${k} is required`);
  return a;
}

// y of a CSS cubic-bezier at the x where it reaches progress p; and the curve's peak y (overshoot).
export function bezier([x1, y1, x2, y2]) {
  const c = (a, b, t) => 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3;
  const yAt = (p) => { let lo = 0, hi = 1; for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; c(x1, x2, m) < p ? (lo = m) : (hi = m); } return c(y1, y2, (lo + hi) / 2); };
  let peak = 0; for (let i = 0; i <= 1000; i++) peak = Math.max(peak, c(y1, y2, i / 1000));
  return { yAt, overshoot: Math.max(0, peak - 1) };
}

export function check(spec) {
  const errors = [], warnings = [];
  const words = spec.lines.join(' ').split(/\s+/).filter(Boolean).length;
  for (const [name, c] of Object.entries(spec.curves)) {
    if (!(Array.isArray(c) && c.length === 4 && c.every(Number.isFinite))) errors.push(`curve ${name} is not four numbers`);
    else if (c[0] < 0 || c[0] > 1 || c[2] < 0 || c[2] > 1) errors.push(`curve ${name} ${JSON.stringify(c)}: x values must be in [0, 1]`);
  }
  if (!TIERS[spec.kind]) errors.push(`kind "${spec.kind}" is not one of ${Object.keys(TIERS).join(', ')}`);
  if (errors.length) return { errors, warnings };
  const { overshoot } = bezier(spec.curves.enter);
  if (spec.legal && overshoot > 0) errors.push(`legal text or a disclosure never overshoots (§6b rule 5); the entrance curve overshoots ${(overshoot * 100).toFixed(1)} %`);
  else if (overshoot > OVERSHOOT_MAX[spec.kind]) errors.push(`text never overshoots (house rule C2, §6b rule 5) — a ${spec.kind} lands and stops; this curve overshoots ${(overshoot * 100).toFixed(1)} %: use an ease-out whose y stays in [0, 1], e.g. [0.16, 1, 0.3, 1]`);
  const enterEnd = (spec.ms.enter + spec.ms.stagger * Math.max(0, (spec.kind === 'title' ? spec.lines.join('').length : spec.lines.length) - 1)) / 1000;
  const hold = spec.durationS - spec.ms.exit / 1000 - enterEnd;
  const floor = spec.voiced ? 1 + 0.3 * words : 1.0 * words;
  if (hold < floor) errors.push(`${words} words need ${floor.toFixed(1)} s fully in and still (§5, ${spec.voiced ? 'voiced' : 'not voiced'}); this holds ${hold.toFixed(2)} s: set durationS ≥ ${(Math.ceil((spec.durationS + floor - hold) * 100 - 1e-9) / 100).toFixed(2)} or use fewer words`);   // round a requirement up, never down
  const [lo, hi] = TIERS[spec.kind];
  const assembly = enterEnd * 1000;
  if (assembly < lo || assembly > hi) warnings.push(`entrance ${Math.round(assembly)} ms is outside §6b's ${spec.kind} tier (${lo}–${hi} ms)`);
  if (spec.ms.exit > spec.ms.enter) warnings.push(`exit ${spec.ms.exit} ms is slower than the entrance ${spec.ms.enter} ms (§6b rule 3 prefers a fast exit; the sources disagree)`);
  if (!spec.font.src) warnings.push(`font "${spec.font.family}" is a system font: another machine may render it differently; give the brand font file as font.src`);
  return { errors, warnings, words, overshoot, hold, floor, enterEnd };
}

async function main() {
  const a = args(process.argv.slice(2));
  let spec;
  try { spec = JSON.parse(fs.readFileSync(a.spec, 'utf8')); } catch (e) { die(2, `${a.spec}: ${e.message}`); }
  spec = { ...DEFAULTS, ...spec, curves: { ...DEFAULTS.curves, ...spec.curves }, ms: { ...DEFAULTS.ms, ...spec.ms } };
  if (!Array.isArray(spec.lines) || !spec.lines.length || !spec.durationS || !spec.font?.family) die(2, 'the spec needs lines, durationS and font.family (see examples/super.json)');
  if (spec.font.src) spec.font.src = pathToFileURL(path.resolve(path.dirname(a.spec), spec.font.src)).href;

  const formats = JSON.parse(fs.readFileSync(FORMATS, 'utf8')).formats;
  const fmt = formats[a.format];
  if (!fmt || !fmt.width) die(2, `unknown format "${a.format}"; video presets: ${Object.keys(formats).filter((k) => formats[k].width).join(', ')}`);
  const fps = a.fps ? Number(a.fps) : fmt.fps_default;
  if (!fmt.fps_options.includes(fps)) die(2, `${a.format} delivers at ${fmt.fps_options.join(', ')} fps, not ${fps}`);
  const box = fmt[a.organic ? 'safe_zone_organic_pct' : 'safe_zone_pct'] || fmt.safe_zone_pct;
  const F = { width: fmt.width, height: fmt.height, fps, safe: {
    top: Math.round(fmt.height * box.top / 100), bottom: Math.round(fmt.height * box.bottom / 100),
    left: Math.round(fmt.width * box.left / 100), right: Math.round(fmt.width * box.right / 100) } };

  const c = check(spec);
  for (const w of c.warnings) console.error('warning: ' + w);
  if (c.errors.length) { for (const e of c.errors) console.error('refused: ' + e); process.exit(1); }

  let chromium;
  try { const m = await import(pathToFileURL(createRequire(path.join(HERE, 'package.json')).resolve('playwright')).href); chromium = m.chromium ?? m.default?.chromium; } catch {}
  if (!chromium) die(2, 'Playwright is not installed here: run `npm ci && npx playwright install chromium-headless-shell` in this folder');
  if (!fs.existsSync(path.join(HERE, 'node_modules', 'gsap', 'dist', 'CustomEase.min.js'))) die(2, 'GSAP is not installed here: run `npm ci` in this folder');
  if (a.prores && spawnSync('ffmpeg', ['-version']).status !== 0) die(2, '--prores needs ffmpeg on PATH');

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: F.width, height: F.height }, deviceScaleFactor: 1 });
  await page.addInitScript(([s, f]) => { window.__SPEC = s; window.__FORMAT = f; }, [spec, F]);
  await page.goto(pathToFileURL(path.join(HERE, 'super.html')).href);
  await page.waitForFunction(() => window.__ready, null, { timeout: 30000 });
  const info = await page.evaluate(() => window.__info);
  const fail = async (msg) => { await browser.close(); console.error('refused: ' + msg); process.exit(1); };
  if (info.fontStatus.startsWith('failed')) await fail(`font ${spec.font.src} did not load (${info.fontStatus})`);
  const b = info.block, s = F.safe;
  if (b.left < s.left - 0.5 || b.top < s.top - 0.5 || b.right > F.width - s.right + 0.5 || b.bottom > F.height - s.bottom + 0.5)
    await fail(`the text leaves the ${a.organic ? 'organic' : 'strict'} safe box of ${a.format} (text ${Math.round(b.left)},${Math.round(b.top)}–${Math.round(b.right)},${Math.round(b.bottom)}; box ${s.left},${s.top}–${F.width - s.right},${F.height - s.bottom}): fewer words, never smaller type (§5)`);

  fs.mkdirSync(a.out, { recursive: true });
  const times = a.still !== undefined ? [Number(a.still)] : Array.from({ length: Math.round(spec.durationS * fps) }, (_, i) => i / fps);
  for (let i = 0; i < times.length; i++) {
    await page.evaluate((t) => window.__seek(t), times[i]);
    await page.screenshot({ path: path.join(a.out, a.still !== undefined ? `still-${times[i]}s.png` : `${String(i).padStart(5, '0')}.png`), omitBackground: true });
  }
  await browser.close();

  if (a.prores && a.still === undefined) {
    const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-framerate', String(fps), '-i', path.join(a.out, '%05d.png'),
      '-c:v', 'prores_ks', '-profile:v', '4', '-pix_fmt', 'yuva444p10le', '-vendor', 'apl0', a.prores], { encoding: 'utf8' });
    if (r.status !== 0) die(2, `ffmpeg failed: ${r.stderr}`);
  }
  const summary = { format: a.format, width: F.width, height: F.height, fps, frames: times.length, durationS: spec.durationS,
    words: c.words, holdS: +c.hold.toFixed(3), floorS: +c.floor.toFixed(3), overshootPct: +(c.overshoot * 100).toFixed(2),
    font: info.fontStatus, out: a.out, prores: a.prores || null, warnings: c.warnings };
  console.log(a.json ? JSON.stringify(summary) : `rendered ${summary.frames} frame${summary.frames === 1 ? '' : 's'} at ${F.width}×${F.height} ${fps} fps → ${a.out}${a.prores ? ` and ${a.prores}` : ''} (hold ${summary.holdS} s ≥ floor ${summary.floorS} s; overshoot ${summary.overshootPct} %)`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) main();
