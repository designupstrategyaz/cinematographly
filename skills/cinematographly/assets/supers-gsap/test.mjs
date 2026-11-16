#!/usr/bin/env node
// SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
// Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
// test.mjs — proves the lane does what render.mjs claims, on real output: `npm test` in this folder.
// Needs `npm ci`, `npx playwright install chromium-headless-shell` and ffmpeg/ffprobe on PATH.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { bezier, check } from './render.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'supers-'));
const EXAMPLE = JSON.parse(fs.readFileSync(path.join(HERE, 'examples', 'super.json'), 'utf8'));
let passed = 0;
const test = async (name, fn) => { await fn(); passed++; console.log('ok  ', name); };
const render = (spec, ...extra) => {
  const f = path.join(TMP, crypto.randomUUID() + '.json'); fs.writeFileSync(f, JSON.stringify(spec));
  return spawnSync('node', [path.join(HERE, 'render.mjs'), '--spec', f, '--format', 'vertical-1080', ...extra], { encoding: 'utf8' });
};
const sha = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const alphaMax = (png) => {   // the highest alpha value in a PNG, read by ffmpeg
  const r = spawnSync('ffmpeg', ['-v', 'error', '-i', png, '-vf', 'alphaextract,signalstats,metadata=print:file=-', '-f', 'null', '-'], { encoding: 'utf8' });
  return Number(/lavfi\.signalstats\.YMAX=(\d+)/.exec(r.stdout)[1]);
};
const full = (o) => ({ ...EXAMPLE, ...o });

await test('refuses overshoot on legal text', () => {
  const c = check(full({ legal: true, curves: { enter: [0.34, 1.56, 0.64, 1], exit: [0.4, 0, 1, 1] } }));
  assert.match(c.errors.join(), /never overshoots/);
});
await test('refuses any overshoot on text, on every kind (house rule C2)', () => {
  assert.ok(bezier([0.34, 1.2, 0.64, 1]).overshoot > 0 && bezier([0.34, 1.2, 0.64, 1]).overshoot < 0.09);
  for (const kind of ['super', 'price', 'title', 'endcard']) {
    const c = check(full({ kind, curves: { enter: [0.34, 1.2, 0.64, 1], exit: [0.4, 0, 1, 1] } }));
    assert.match(c.errors.join(), /text never overshoots/, kind);
  }
});
await test('refuses dwell below the §5 floor and names the duration that fixes it', () => {
  const c = check(full({ voiced: false, durationS: 3.5 }));   // 5 words unvoiced need 5 s held
  assert.match(c.errors.join(), /need 5\.0 s fully in and still.*set durationS ≥ 5\.93/);
});
await test('refuses a curve whose x leaves [0, 1]', () => {
  assert.match(check(full({ curves: { enter: [1.2, 0, 0.3, 1], exit: [0.4, 0, 1, 1] } })).errors.join(), /x values must be in \[0, 1\]/);
});

const out = path.join(TMP, 'seq'), mov = path.join(TMP, 'super.mov');
await test('renders round(durationS × fps) frames and a ProRes 4444 file with alpha', () => {
  const r = render(EXAMPLE, '--out', out, '--prores', mov);
  assert.equal(r.status, 0, r.stderr);
  const frames = fs.readdirSync(out).filter((f) => f.endsWith('.png'));
  assert.equal(frames.length, Math.round(EXAMPLE.durationS * 24));
  const p = spawnSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,profile,pix_fmt,r_frame_rate,nb_frames', '-of', 'json', mov], { encoding: 'utf8' });
  const s = JSON.parse(p.stdout).streams[0];
  assert.equal(s.codec_name, 'prores'); assert.equal(s.profile, '4444'); assert.match(s.pix_fmt, /^yuva444/);
  assert.equal(s.r_frame_rate, '24/1'); assert.equal(Number(s.nb_frames), frames.length);
});
await test('frame 0 is fully transparent; a held frame is fully opaque where the text is', () => {
  assert.equal(alphaMax(path.join(out, '00000.png')), 0);
  assert.equal(alphaMax(path.join(out, '00048.png')), 255);   // 2.0 s: in, still, not yet leaving
});
await test('the same instant renders the same pixels: a fresh --still equals the sequence frame', () => {
  const r = render(EXAMPLE, '--out', path.join(TMP, 'still'), '--still', '0.25');
  assert.equal(r.status, 0, r.stderr);
  assert.equal(sha(path.join(TMP, 'still', 'still-0.25s.png')), sha(path.join(out, '00006.png')));   // 0.25 s × 24 fps = frame 6
});
await test('a seek lands exactly on the token curve (position within 0.5 px)', async () => {
  const m = await import(pathToFileURL(createRequire(path.join(HERE, 'package.json')).resolve('playwright')).href);
  const browser = await (m.chromium ?? m.default.chromium).launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  const F = { width: 1080, height: 1920, fps: 24, safe: { top: 288, bottom: 672, left: 119, right: 302 } };
  await page.addInitScript(([s, f]) => { window.__SPEC = s; window.__FORMAT = f; }, [EXAMPLE, F]);
  await page.goto(pathToFileURL(path.join(HERE, 'super.html')).href);
  await page.waitForFunction(() => window.__ready);
  const dist = await page.evaluate(() => window.__info.dist);
  const { yAt } = bezier(EXAMPLE.curves.enter);
  for (const [t, i] of [[0.1, 0], [0.25, 0], [0.25, 1], [0.5, 1]]) {
    const x = await page.evaluate(([t, i]) => { window.__seek(t); return new DOMMatrix(getComputedStyle(document.querySelectorAll('.item')[i]).transform).m41; }, [t, i]);
    const p = Math.min(1, Math.max(0, (t - i * EXAMPLE.ms.stagger / 1000) / (EXAMPLE.ms.enter / 1000)));
    const expected = -dist * (1 - yAt(p));
    assert.ok(Math.abs(x - expected) < 0.5, `t=${t} item ${i}: x ${x.toFixed(2)} vs ${expected.toFixed(2)}`);
  }
  await browser.close();
});
await test('refuses text that leaves the safe box', () => {
  const r = render(full({ lines: ['A line far too long to sit inside the vertical safe box'], durationS: 20 }), '--out', path.join(TMP, 'wide'));
  assert.equal(r.status, 1); assert.match(r.stderr, /leaves the strict safe box/);
});
await test('refuses a brand font file that does not load', () => {
  const r = render(full({ font: { family: 'Brand', src: 'missing.woff2', weight: 700, sizePctOfHeight: 3.6 } }), '--out', path.join(TMP, 'font'));
  assert.equal(r.status, 1); assert.match(r.stderr, /did not load/);
});
await test('refuses an unknown format and lists the valid ones', () => {
  const f = path.join(TMP, 'x.json'); fs.writeFileSync(f, JSON.stringify(EXAMPLE));
  const r = spawnSync('node', [path.join(HERE, 'render.mjs'), '--spec', f, '--format', 'cinema-4k', '--out', TMP], { encoding: 'utf8' });
  assert.equal(r.status, 2); assert.match(r.stderr, /vertical-1080/);
});

fs.rmSync(TMP, { recursive: true, force: true });
console.log(`\n${passed} passed`);
