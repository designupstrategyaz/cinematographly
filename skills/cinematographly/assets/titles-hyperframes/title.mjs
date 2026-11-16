#!/usr/bin/env node
// SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
// Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
// title.mjs — render one title from the project's title card and a title spec, through HyperFrames, to a
// ProRes 4444 .mov with alpha for the track above the locked cut (references/typography-and-captions.md
// §6c). The card (00-brief/TITLE-CARD.json, `scripts/title_card.py`) carries the type, colours, scale,
// motion tokens and the kit per title kind; the spec (07-edit/titles/<id>.title.json) carries the words,
// the length and the anchor. Nothing about the look is decided here.
//
// OPTIONAL LANE, like assets/supers-gsap: it needs Node 22, the hyperframes CLI (Apache-2.0, pinned in
// package.json) and its headless Chrome. Nothing in scripts/ depends on it; scripts/title_qa.py measures
// what it renders, whichever engine rendered it.
//
// Usage (from this folder, after `npm ci && npx hyperframes browser ensure`):
//   node title.mjs --card <job>/00-brief/TITLE-CARD.json --spec <job>/07-edit/titles/T1.title.json \
//                  --format vertical-1080 --out <job>/07-edit/titles/T1.mov
//   node title.mjs ... --still 1.2 --out /tmp/T1.png          # one frame to look at first
//   node title.mjs ... --keep /tmp/T1-project                  # keep the generated HyperFrames project
//   --fps N overrides the preset's fps_default; --organic uses the looser house safe box (never for paid)
//
// Exit codes: 0 rendered · 1 refused (the spec breaks the card, a font file is missing, HyperFrames'
// check fails) · 2 usage or IO error. Telemetry is off (HYPERFRAMES_NO_TELEMETRY=1, DO_NOT_TRACK=1).
//
// WHAT IT CANNOT DO. It does not judge the title on the real picture (title_qa.py does, on the
// composite), choose the words, or check claims (claims_lint.py). It does not place the title in the edit.
import { spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FORMATS = path.join(HERE, '..', 'delivery-formats.json');
const KITS = ['hero-line', 'super', 'stat', 'price-card', 'end-card', 'lockup', 'place-time', 'main-title', 'episode-card'];
const ENTER = ['fade-rise', 'per-word', 'tracking-in', 'mask-reveal', 'blur-resolve', 'cut'];
const EXIT = ['fade', 'fade-up', 'cut'];
const STEPS = ['label', 'body', 'title', 'hero', 'display'];      // base · base·r · base·r² · base·r³ · base·r⁴
const die = (code, msg) => { console.error(msg); process.exit(code); };
const sha = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');

function args(argv) {
  const known = ['card', 'spec', 'format', 'fps', 'out', 'still', 'keep'], flags = ['organic', 'json'], a = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i].replace(/^--/, '');
    if (flags.includes(k)) { a[k] = true; continue; }
    if (!known.includes(k) || argv[i + 1] === undefined) die(2, `bad argument ${argv[i]} (flags: ${[...known, ...flags].map((x) => '--' + x).join(' ')})`);
    a[k] = argv[++i];
  }
  for (const k of ['card', 'spec', 'format', 'out']) if (!a[k]) die(2, `--${k} is required`);
  return a;
}

// The title, resolved: the spec's words and timing, the card's look. Every refusal names its fix.
export function resolve(card, spec, fmt, fps, organic) {
  const kind = spec.kind, K = (card.kinds || {})[kind];
  if (!K) return { error: `"${kind}" is not on the title card — the card is the permission list (C3): add the kind to the card and have it approved, or drop the title` };
  const kit = spec.kit || K.kit;
  if (!KITS.includes(kit)) return { error: `kit "${kit}" unknown (${KITS.join(', ')})` };
  if (K.kit && spec.kit && spec.kit !== K.kit) return { error: `${kind} uses kit ${K.kit} on the card, the spec asks for ${spec.kit}` };
  const M = card.motion || {}, en = { ...(M.enter || {}), ...(K.enter || {}) }, ex = { ...(M.exit || {}), ...(K.exit || {}) };
  if (!ENTER.includes(en.family)) return { error: `entrance family "${en.family}" unknown (${ENTER.join(', ')})` };
  if (!EXIT.includes(ex.family)) return { error: `exit family "${ex.family}" unknown (${EXIT.join(', ')})` };
  for (const [n, c] of [['enter', en.ease], ['exit', ex.ease]]) {
    if (!Array.isArray(c) || c.length !== 4 || c[0] < 0 || c[0] > 1 || c[2] < 0 || c[2] > 1) return { error: `motion.${n}.ease must be a cubic-bezier [x1, y1, x2, y2] with x in [0, 1]` };
    if (c[1] > 1 || c[3] > 1 || c[1] < 0 || c[3] < 0) return { error: `motion.${n}.ease overshoots (y outside [0, 1]): no overshoot on text, numbers or UI (house rule C2, 2026-10-26)` };
  }
  if ((card.lane === 'ads') && en.family === 'blur-resolve') return { error: 'blur-resolve is not an ads entrance (no blur, glow or scramble for the 45+ phone audience)' };
  const sc = card.scale || {}, k = fmt.height / 1920, sizes = {};
  if (!(sc.base_px > 0) || !(sc.ratio > 1)) return { error: 'card.scale needs base_px > 0 and ratio > 1 (one type scale, K2)' };
  STEPS.forEach((s, i) => { sizes[s] = Math.round(sc.base_px * Math.pow(sc.ratio, i) * k); });
  const box = fmt[organic ? 'safe_zone_organic_pct' : 'safe_zone_pct'] || fmt.safe_zone_pct;
  const safe = { left: Math.round(fmt.width * box.left / 100), right: Math.round(fmt.width * box.right / 100),
                 top: Math.round(fmt.height * box.top / 100), bottom: Math.round(fmt.height * box.bottom / 100) };
  const dur = Number(spec.duration_s);
  if (!(dur > 0)) return { error: 'spec.duration_s is required (the title\'s whole time on screen, entrance and exit included)' };
  const C = card.colors || {};
  return { T: {
    kit, kind, W: fmt.width, H: fmt.height, fps, dur, safe, sizes,
    position: spec.position || K.position || 'middle', align: spec.align || K.align || 'center',
    text_case: card.text_case || 'none', tracking_em: Number(card.tracking_em || 0),
    enter: { family: en.family, s: (en.ms || 600) / 1000, ease: en.ease, stagger_s: (M.stagger_ms || 0) / 1000 },
    exit: { family: ex.family, s: ex.family === 'cut' ? 0 : (ex.ms || 300) / 1000, ease: ex.ease },
    mark_s: (M.mark_ms || 350) / 1000, count_s: (M.count_ms || 900) / 1000, rise_px: Math.round(fmt.height * 0.012),
    plate_on: !!(K.plate), page_bg: spec.page_bg || K.page_bg || 'transparent',
    content: spec.content || {} },
    colors: { fg: C.fg || '#FFFFFF', accent: C.accent || '#FFFFFF', em_fg: C.em_fg || C.fg || '#FFFFFF',
              plate: C.plate || 'rgba(0,0,0,0.6)' },
    radius: card.plate_radius_em || 0.18 };
}

function fontFaces(card, dir) {
  const out = [], status = [];
  for (const role of ['anchor', 'companion']) {
    const f = (card.fonts || {})[role];
    if (!f) continue;
    const file = f.file && path.resolve(path.dirname(card.__path), f.file);
    if (!file || !fs.existsSync(file)) die(1, `the ${role} font file is missing (${f.file || 'no file'}): a brand font must be a file, so every machine renders the same letters`);
    const dst = path.join(dir, 'fonts', `${role}${path.extname(file)}`);
    fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.copyFileSync(file, dst);
    out.push(`      @font-face { font-family: "${f.family}"; src: url("fonts/${path.basename(dst)}"); font-weight: ${f.weight || 400}; font-style: ${f.italic ? 'italic' : 'normal'}; font-display: block; }`);
    status.push({ role, family: f.family, file: f.file, sha256: sha(file) });
  }
  return { css: out.join('\n'), status };
}

function main() {
  const a = args(process.argv.slice(2));
  const card = JSON.parse(fs.readFileSync(a.card, 'utf8')); card.__path = path.resolve(a.card);
  const spec = JSON.parse(fs.readFileSync(a.spec, 'utf8'));
  const fmts = JSON.parse(fs.readFileSync(FORMATS, 'utf8')).formats, fmt = fmts[a.format];
  if (!fmt || !fmt.width) die(2, `unknown --format ${a.format} (${Object.keys(fmts).filter((k) => fmts[k].width).join(', ')})`);
  const fps = Number(a.fps || fmt.fps_default || 24);
  const R = resolve(card, spec, fmt, fps, a.organic);
  if (R.error) die(1, `REFUSED: ${R.error}`);
  const dir = a.keep ? path.resolve(a.keep) : fs.mkdtempSync(path.join(os.tmpdir(), 'cine-title-'));
  fs.mkdirSync(dir, { recursive: true });
  const ff = fontFaces(card, dir);
  if (R.T.content.logo) {
    const src = path.resolve(path.dirname(path.resolve(a.spec)), R.T.content.logo);
    if (!fs.existsSync(src)) die(1, `the logo file is missing: ${R.T.content.logo}`);
    fs.mkdirSync(path.join(dir, 'assets'), { recursive: true });
    const dst = path.join('assets', 'logo' + path.extname(src)); fs.copyFileSync(src, path.join(dir, dst)); R.T.content.logo = dst;
  }
  const F = card.fonts || {}, tokens = [
    `--t-font-anchor: "${(F.anchor || {}).family || 'sans-serif'}";`, `--t-weight-anchor: ${(F.anchor || {}).weight || 700};`,
    `--t-font-companion: "${(F.companion || F.anchor || {}).family || 'sans-serif'}";`, `--t-weight-companion: ${(F.companion || F.anchor || {}).weight || 400};`,
    `--t-fg: ${R.colors.fg};`, `--t-accent: ${R.colors.accent};`, `--t-em-fg: ${R.colors.em_fg};`, `--t-plate: ${R.colors.plate};`,
    `--t-plate-radius: ${Math.round(R.radius * R.T.sizes.body)}px;`, `--t-rule: ${Math.max(2, Math.round(fmt.height / 640))}px;`].map((s) => '        ' + s).join('\n');
  const res = { '1080x1920': 'portrait', '1920x1080': 'landscape', '2160x3840': 'portrait-4k', '3840x2160': 'landscape-4k', '1080x1080': 'square' }[`${fmt.width}x${fmt.height}`] || 'custom';
  const html = fs.readFileSync(path.join(HERE, 'kits', 'base.html'), 'utf8')
    .replaceAll('__W__', String(fmt.width)).replaceAll('__H__', String(fmt.height)).replaceAll('__FPS__', String(fps))
    .replaceAll('__DUR__', String(R.T.dur)).replace('__RESOLUTION__', res).replaceAll('__PAGE_BG__', R.T.page_bg)
    .replace('__FONTFACES__', ff.css).replace('__TOKENS__', tokens)
    .replace('__TITLE_JSON__', JSON.stringify(R.T).replace(/</g, '\\u003c'))
    .replace('__KITS_JS__', fs.readFileSync(path.join(HERE, 'kits', 'kits.js'), 'utf8'));
  fs.writeFileSync(path.join(dir, 'index.html'), html);
  fs.copyFileSync(path.join(HERE, 'node_modules', 'gsap', 'dist', 'gsap.min.js'), path.join(dir, 'gsap.min.js'));
  fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ id: `cine-title-${spec.id || 'x'}`, name: spec.id || 'title' }));
  const env = { ...process.env, HYPERFRAMES_NO_TELEMETRY: '1', DO_NOT_TRACK: '1', HYPERFRAMES_SKIP_SKILLS: '1' };
  const HF = path.join(HERE, 'node_modules', '.bin', 'hyperframes');
  const chk = spawnSync(HF, ['check', dir, '--json'], { env, encoding: 'utf8', maxBuffer: 1 << 26 });
  let check = null; try { check = JSON.parse(chk.stdout); } catch { /* text output */ }
  if (check && check.browserSkipped) die(1, `REFUSED: HyperFrames found no headless Chrome, so nothing was checked or rendered — run \`npx hyperframes browser ensure\` in ${HERE} (on Linux ARM64 there is no Chrome Headless Shell: install Chromium and set HYPERFRAMES_BROWSER_PATH)`);
  if (chk.status !== 0) {
    // name each error in the title's own terms; the full report stays in the kept project
    const why = [];
    for (const sec of Object.values(check || {})) for (const f of (sec && sec.findings) || []) {
      if (f.severity !== 'error') continue;
      if (f.code === 'text_box_overflow') {
        const px = Math.round(Math.max(0, ...Object.values(f.overflow || {})));
        why.push(`a line runs ${px} px past the frame from ${f.firstSeen ?? f.time} s — set it on two lines (content.lines) or shorten it: the size is the card's scale step and is never shrunk to fit`);
      } else why.push(`${f.code}: ${f.message}${f.text ? ` ("${f.text}")` : ''}${f.fixHint ? ` — ${f.fixHint}` : ''}`);
    }
    die(1, `REFUSED: HyperFrames' check failed on the generated title${a.keep ? ` (${dir})` : ' (--keep <dir> keeps the project and its report)'}:\n  - `
      + (why.length ? why.join('\n  - ') : `${(chk.stdout || '').slice(-1500)}${(chk.stderr || '').slice(-800)}`));
  }
  const out = path.resolve(a.out); fs.mkdirSync(path.dirname(out), { recursive: true });
  let r;
  if (a.still !== undefined) {
    const snaps = path.join(dir, 'stills');
    r = spawnSync(HF, ['snapshot', dir, '--at', String(a.still), '--no-end', '-o', snaps], { env, encoding: 'utf8', maxBuffer: 1 << 26 });
    const pngs = fs.existsSync(snaps) ? fs.readdirSync(snaps).filter((f) => f.endsWith('.png')) : [];
    if (r.status !== 0 || !pngs.length) die(1, `snapshot failed:\n${(r.stdout || '').slice(-800)}${(r.stderr || '').slice(-800)}`);
    fs.copyFileSync(path.join(snaps, pngs[0]), out);
  } else {
    r = spawnSync(HF, ['render', dir, '--format', 'mov', '--fps', String(fps), '--quiet', '-o', out], { env, encoding: 'utf8', maxBuffer: 1 << 26 });
    if (r.status !== 0 || !fs.existsSync(out)) die(1, `render failed:\n${(r.stdout || '').slice(-1500)}${(r.stderr || '').slice(-800)}`);
  }
  const side = { tool: 'assets/titles-hyperframes/title.mjs', engine: `hyperframes ${JSON.parse(fs.readFileSync(path.join(HERE, 'node_modules', 'hyperframes', 'package.json'), 'utf8')).version}`,
    spec: path.resolve(a.spec), spec_sha256: sha(a.spec), card: card.__path, card_sha256: sha(a.card), format: a.format, fps,
    safe_box: a.organic ? 'organic' : 'strict', fonts: ff.status, resolved: R.T, check_summary: check ? (check.summary || check.status || null) : 'text',
    rendered: new Date().toISOString(), output: out, output_sha256: sha(out) };
  fs.writeFileSync(out + '.render.json', JSON.stringify(side, null, 1));
  if (!a.keep) fs.rmSync(dir, { recursive: true, force: true });
  if (a.json) console.log(JSON.stringify(side)); else console.log(`${out} — ${R.T.kit}, ${R.T.dur}s at ${fps} fps, ${a.format}${a.still !== undefined ? ` (still at ${a.still}s)` : ''}`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) main();
