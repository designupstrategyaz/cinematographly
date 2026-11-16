# supers-gsap — supers, hero titles and end cards rendered from the brand's motion tokens

**Optional, and only with a recorded reason.** Fusion is the default for supers
(`references/typography-and-captions.md` §6b rule 10; house rule C7, 2026-10-27: *"it should defrult to Resolve or
Fusion native elements. Not create outside for no reason"*). A spec rendered here carries `"engine": "gsap"` and an
`"engine_reason"` — one of `scripts/native.py reasons`, and for a look Fusion cannot make, the owner's words
(`{"code": "owner", "why": "…", "quote": "…"}`). `scripts/shell_gate.py` stops `node render.mjs` on a spec without
them, and `title_card.py titles` refuses the title. You build the move once from the brand's curves and durations, and the lane renders
it frame-accurately for any preset in `assets/delivery-formats.json`. The output is a transparent PNG
sequence and a ProRes 4444 `.mov` that goes on a track above the locked cut.

It lives in `assets/`, not `scripts/`, because it needs Node, Playwright and GSAP. The scripts charter
(`scripts/README.md` rule 1) allows only stdlib Python and ffmpeg, and that rule stands.

## Setup (once, in this folder)

```bash
npm ci
npx playwright install chromium-headless-shell
npm test        # 11 checks on real output; needs ffmpeg and ffprobe on PATH
```

## Render

```bash
node render.mjs --spec examples/super.json --format vertical-1080 --out out/super-9x16 --prores out/super-9x16.mov
node render.mjs --spec examples/super.json --format feed-4x5 --fps 30 --out out/super-4x5 --prores out/super-4x5.mov
node render.mjs --spec examples/super.json --format vertical-1080 --still 1.5 --out out/check   # one frame to look at first
```

Size, frame rate and the safe box come from the preset. `--organic` uses the looser house box, which
has no platform source, so never use it for anything that runs paid or carries a disclosure.

## The spec (one JSON file per super)

| Field | Default | Rule it carries |
|---|---|---|
| `kind` | `super` | `super`, `price`, `title` (per-letter stagger, the one hero title only, §6) or `endcard` |
| `lines` | required | 1–2 lines; text that leaves the safe box is refused (fewer words, never smaller type, §5) |
| `voiced` | `false` | `true` when the voiceover says the same words: the dwell floor is then 1 s + 0.3 s per word, otherwise 1 s per word (§5) |
| `durationS` | required | Total time on screen, entrance and exit included |
| `legal` | `false` | `true` for legal text or a disclosure: any overshoot is refused (§6b rule 5) |
| `position`, `from` | `lower-left`, `left` | Enter from the side the picture travels toward (§6b rule 7); the exit keeps that direction |
| `font` | required | `family`, `weight`, `sizePctOfHeight`, optional `trackingEm`; give the brand font file as `src` (a system font only warns, because another machine may render it differently) |
| `color`, `plate` | white on 60 % black | From the brand's type block (§8) |
| `curves.enter`, `curves.exit` | the lab's `[0.16, 1, 0.3, 1]` and `[0.4, 0, 1, 1]` | One curve family per brand (§6b rule 1); x values must be in [0, 1] |
| `ms.enter`, `ms.exit`, `ms.stagger` | 600, 300, 25 | Duration tiers and stagger (§6b rules 2–4); outside a tier only warns |

## What it refuses, and what it can't do

It **refuses** a hold shorter than §5's floor, and names the `durationS` that fixes it. It also refuses:
- any overshoot, on any kind — every one is text (house rule C2, 2026-10-26; until then a super or
  price could overshoot 9 % and a title or end card 42 %), measured from the entrance curve itself;
- text outside the safe box;
- a brand font file that doesn't load.

It **can't**:
- judge legibility on the real picture: run the caption QA card (§9) on the composite;
- decide where the super lands in the edit (§6b rule 8: not in the half-second after a hard cut);
- check claims: a price or stat still goes through `scripts/claims_lint.py` and the compliance gate.

## Into Resolve

Import the `.mov` and put it on a video track above the cut. PNG carries straight (unpremultiplied)
alpha, and so does the ProRes made from it. If the edges look dark or haloed, set Clip Attributes ▸
Alpha mode to Straight.

## Why the frames are exact

The page builds a paused GSAP timeline, and the renderer seeks it to `i / fps` before each
screenshot, so nothing depends on real time.

- **Same instant, same pixels:** a frame rendered alone with `--still` is byte-identical to the same
  frame in the sequence.
- **Exact curve:** positions match the token curve within 0.5 px.
- **Tests that can fail:** swapping the token curve for a stock ease made `npm test` fail, 17 px off
  at 0.1 s (checked 2026-10-11, GSAP 3.15.0, Playwright 1.64).

GSAP is free under Webflow's no-charge licence. That licence only restricts tools that let users
build visual animations without code, which this lane is not.
