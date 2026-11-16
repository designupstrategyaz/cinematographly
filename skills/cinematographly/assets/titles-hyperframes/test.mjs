#!/usr/bin/env node
// SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
// Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
// test.mjs — the title lane's own test. First the refusals in resolve(), which need no render. Then, when
// the HyperFrames CLI and its Chrome are installed (`npm ci && npx hyperframes browser ensure`), a still of
// every kit, two full renders checked as ProRes 4444 with alpha and an exact length, and a refusal through
// the CLI. `npm test` · `node test.mjs --full` renders all nine kits as .mov.
//
// The fonts are the machine's own (Inter, Arial or DejaVu): a test needs letters, not the brand's.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resolve } from './title.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FULL = process.argv.includes('--full');
const lanes = JSON.parse(fs.readFileSync(path.join(HERE, '..', 'title-lanes.json'), 'utf8')).lanes;
const fmts = JSON.parse(fs.readFileSync(path.join(HERE, '..', 'delivery-formats.json'), 'utf8')).formats;
const V = fmts['vertical-1080'];
let fails = 0;
const check = (name, ok, info = '') => { console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}${ok ? '' : `  — ${String(info).slice(0, 600)}`}`); if (!ok) fails++; };
const skip = (name, why) => console.log(`  [SKIP] ${name} — ${why}`);

function findFont(names) {
  const roots = ['/usr/share/fonts', '/Library/Fonts', '/System/Library/Fonts', path.join(os.homedir(), 'Library', 'Fonts')];
  const walk = (d, depth) => {
    let out = [];
    try { for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory() && depth < 4) out = out.concat(walk(p, depth + 1)); else if (e.isFile()) out.push(p);
    } } catch { /* unreadable */ }
    return out;
  };
  const all = roots.flatMap((r) => walk(r, 0));
  for (const n of names) { const hit = all.find((p) => path.basename(p) === n); if (hit) return hit; }
  return null;
}

function cardFor(lane, fonts) {
  const L = JSON.parse(JSON.stringify(lanes[lane]));
  const fill = (v) => (v === 'BRAND' ? (lane === 'ads' ? '#E8432E' : '#B08D57') : v);
  for (const k of Object.keys(L.colors)) L.colors[k] = fill(L.colors[k]);
  for (const k of Object.values(L.kinds)) if (k.page_bg) k.page_bg = k.page_bg === 'BRAND' ? '#111111' : k.page_bg;
  return { job: 'test', lane, ...L, fonts };
}

// ── 1. resolve(): the refusals, and the sizes from one scale ───────────────────────────────────────────
const ads = cardFor('ads', {});
const hero = { id: 'T1', kind: 'hero', duration_s: 3, content: { lines: ['Sleep through', 'the night'], emphasis: 'night', mark: 'bar' } };
const ok = resolve(ads, hero, V, 30, false);
check('a hero line resolves: one scale (base·r³ at 1920 px), the strict safe box, the card\'s colours',
  !ok.error && ok.T.sizes.hero === Math.round(40 * 1.333 ** 3) && ok.T.safe.left === Math.round(V.width * V.safe_zone_pct.left / 100)
  && ok.colors.accent === '#E8432E', JSON.stringify(ok).slice(0, 400));
check('a kind the card does not name is refused — the card is the permission list (C3)',
  /permission list/.test(resolve(ads, { ...hero, kind: 'lockup' }, V, 30).error || ''));
const bounce = JSON.parse(JSON.stringify(ads)); bounce.motion.enter.ease = [0.34, 1.56, 0.64, 1];
check('an overshooting ease is refused — no overshoot on text (C2)', /overshoots/.test(resolve(bounce, hero, V, 30).error || ''));
const blur = JSON.parse(JSON.stringify(ads)); blur.motion.enter.family = 'blur-resolve';
check('blur is not an ads entrance', /blur-resolve is not an ads entrance/.test(resolve(blur, hero, V, 30).error || ''));
check('a title with no length is refused', /duration_s/.test(resolve(ads, { ...hero, duration_s: undefined }, V, 30).error || ''));
check('a spec that asks for another kit than the card\'s is refused', /uses kit/.test(resolve(ads, { ...hero, kit: 'super' }, V, 30).error || ''));
const flat = JSON.parse(JSON.stringify(ads)); flat.scale.ratio = 1;
check('a card with no type scale is refused', /scale/.test(resolve(flat, hero, V, 30).error || ''));

// ── 2. the renders (needs the CLI and its Chrome) ──────────────────────────────────────────────────────
const HF = path.join(HERE, 'node_modules', '.bin', 'hyperframes');
const heavy = findFont(['InterDisplay-ExtraBold.otf', 'Inter-Bold.otf', 'Arial Bold.ttf', 'DejaVuSans-Bold.ttf', 'LiberationSans-Bold.ttf']);
const reg = findFont(['Inter-Regular.otf', 'Arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']);
const serif = findFont(['Lora-Variable.ttf', 'Georgia.ttf', 'DejaVuSerif.ttf', 'LiberationSerif-Regular.ttf']) || heavy;
const hasFfprobe = spawnSync('ffprobe', ['-version']).status === 0;
if (!fs.existsSync(HF)) skip('the renders', 'the hyperframes CLI is not installed here (npm ci)');
else if (!heavy || !reg) skip('the renders', 'no system font found to render with');
else {
  const td = fs.mkdtempSync(path.join(os.tmpdir(), 'cine-title-test-'));
  const fam = (f) => path.basename(f).replace(/[-_ ]?(ExtraBold|Bold|Regular|Variable|Medium)?\.(otf|ttf)$/i, '').replace(/([a-z])([A-Z])/g, '$1 $2');
  const fonts = { anchor: { family: `T ${fam(heavy)}`, file: heavy, weight: 700 }, companion: { family: `T ${fam(reg)}`, file: reg, weight: 400 } };
  const cards = { ads: cardFor('ads', fonts), brand: cardFor('brand', { ...fonts, anchor: { family: `T ${fam(serif)}`, file: serif, weight: 500 } }),
                  drama: cardFor('drama', { ...fonts, anchor: { family: `T ${fam(serif)}`, file: serif, weight: 500 } }) };
  const cardPath = {};
  for (const [k, c] of Object.entries(cards)) { cardPath[k] = path.join(td, `card-${k}.json`); fs.writeFileSync(cardPath[k], JSON.stringify(c)); }
  let logo = null;
  if (spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=white:s=240x80', '-frames:v', '1', path.join(td, 'logo.png')]).status === 0) logo = 'logo.png';
  const specs = [
    ['ads', 'hero-line', hero],
    ['ads', 'stat', { id: 'T2', kind: 'stat', duration_s: 3.2, content: { value: 87, suffix: '%', label: 'slept longer in week one', label_pos: 'below' } }],
    ['ads', 'price-card', { id: 'T3', kind: 'price', duration_s: 3, content: { kicker: 'Today only', price: '$49', was: '$89', note: 'Free returns' } }],
    ['ads', 'end-card', { id: 'T4', kind: 'endcard', duration_s: 3, content: { ...(logo ? { logo } : {}), line: 'Try it for 100 nights', url: 'example.com' } }],
    ['brand', 'lockup', { id: 'B1', kind: 'lockup', duration_s: 4, content: { kicker: 'The collection', lines: ['Inherited.', 'Not bought.'], rule: true, label: 'example.com' } }],
    ['brand', 'super', { id: 'B2', kind: 'super', duration_s: 3, content: { lines: ['Made by hand', 'in Porto'] } }],
    ['drama', 'place-time', { id: 'D1', kind: 'place', duration_s: 3.5, content: { place: 'Lagos, Nigeria', time: '1987' } }],
    ['drama', 'main-title', { id: 'D2', kind: 'main', duration_s: 4, content: { title: 'Adrift', subtitle: 'A short film' } }],
    ['drama', 'episode-card', { id: 'D3', kind: 'episode', duration_s: 3.5, content: { kicker: 'Episode 3', title: 'The Crossing' } }]];
  const runT = (lane, spec, out, extra = []) => {
    const sp = path.join(td, `${spec.id}.title.json`); fs.writeFileSync(sp, JSON.stringify(spec));
    return spawnSync(process.execPath, [path.join(HERE, 'title.mjs'), '--card', cardPath[lane], '--spec', sp, '--format', 'vertical-1080', '--out', out, ...extra],
      { encoding: 'utf8', maxBuffer: 1 << 26 });
  };
  const probe = (f) => { const r = spawnSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,pix_fmt,width,height:format=duration', '-of', 'json', f], { encoding: 'utf8' });
    try { const d = JSON.parse(r.stdout); return { ...d.streams[0], duration: Number(d.format.duration) }; } catch { return {}; } };
  const pre = runT('ads', hero, path.join(td, 'preflight.png'), ['--still', '1']);
  if (pre.status !== 0 && /no headless Chrome/.test(pre.stderr)) {
    skip('the renders', 'HyperFrames has no headless Chrome here (npx hyperframes browser ensure)');
    fs.rmSync(td, { recursive: true, force: true });
    console.log('-'.repeat(60));
    console.log(fails ? `FAILED — ${fails}` : 'OK — the refusals; the renders were skipped (no browser)');
    process.exit(fails ? 1 : 0);
  }
  const failedStills = [];
  const tail = (r) => (r.stderr || '').split('\n').filter((l) => !/check: /.test(l)).join('\n').slice(-500);
  for (const [lane, kit, spec] of specs) {
    const r = runT(lane, spec, path.join(td, `${kit}.png`), ['--still', String(Math.min(spec.duration_s - 0.6, 2.2))]);
    if (r.status !== 0 || !fs.existsSync(path.join(td, `${kit}.png`))) failedStills.push(`${kit}: ${tail(r)}`);
  }
  check(`a still of every kit (${specs.length}) renders through HyperFrames' check`, !failedStills.length, failedStills.join('\n'));
  const movs = FULL ? specs : specs.filter(([, kit]) => ['hero-line', 'price-card'].includes(kit));
  for (const [lane, kit, spec] of movs) {
    const out = path.join(td, `${kit}.mov`), r = runT(lane, spec, out);
    const p = hasFfprobe && r.status === 0 ? probe(out) : {};
    const side = fs.existsSync(out + '.render.json') ? JSON.parse(fs.readFileSync(out + '.render.json', 'utf8')) : {};
    check(`${kit}: ProRes 4444 with alpha at 1080×1920, ${spec.duration_s} s to the frame, the render sidecar beside it`,
      r.status === 0 && (!hasFfprobe || (p.codec_name === 'prores' && /^yuva444/.test(p.pix_fmt || '') && p.width === 1080 && p.height === 1920
        && Math.abs(p.duration - spec.duration_s) <= 1 / 30 + 0.01)) && side.output_sha256 && side.fonts?.length === 2,
      r.status !== 0 ? (r.stderr || r.stdout).slice(-600) : JSON.stringify(p));
  }
  if (!hasFfprobe) skip('the codec, alpha and length', 'ffprobe is not installed');
  const r = runT('ads', { ...hero, kind: 'lockup' }, path.join(td, 'nope.mov'));
  check('a title the card does not permit is refused by the CLI (exit 1, REFUSED)', r.status === 1 && /REFUSED/.test(r.stderr), r.stderr);
  const wide = runT('brand', { id: 'B9', kind: 'lockup', duration_s: 4, content: { line: 'Inherited, never bought, always kept.' } }, path.join(td, 'wide.png'), ['--still', '2.5']);
  check('a lockup line too wide for 9:16 is refused in its own terms: two lines, never a smaller size',
    wide.status === 1 && /past the frame/.test(wide.stderr) && /content\.lines/.test(wide.stderr), wide.stderr.slice(-600));
  const nofont = JSON.parse(JSON.stringify(cards.ads)); nofont.fonts.anchor.file = path.join(td, 'gone.otf');
  fs.writeFileSync(path.join(td, 'card-nofont.json'), JSON.stringify(nofont)); cardPath.nofont = path.join(td, 'card-nofont.json');
  const r2 = runT('nofont', hero, path.join(td, 'nope2.mov'));
  check('a card whose font file is missing is refused (a brand font must be a file)', r2.status === 1 && /font file is missing/.test(r2.stderr), r2.stderr);
  fs.rmSync(td, { recursive: true, force: true });
}
console.log('-'.repeat(60));
console.log(fails ? `FAILED — ${fails}` : 'OK — the title lane: refusals (permission, overshoot, ads blur, length, kit, scale), the kits rendered, ProRes 4444 alpha to the frame');
process.exit(fails ? 1 : 0);
