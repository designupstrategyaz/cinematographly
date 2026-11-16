# titles-hyperframes — the project's titles, rendered from its title card

**Optional lane**, beside `assets/supers-gsap`. It renders one title at a time (a hero line, a stat, a
price card, an end card, a brand lockup, a super, a place-and-time super, a main title, an episode card)
as ProRes 4444 with alpha, for the track above the locked cut. Owner's choice, 2026-10-26: *"A: Title
card + type system, B: HyperFrames + the legibility gate, C: Lane kits + review loop, D: Transitions +
ramps"* (the titles and motion proposal of 2026-10-26 [studio history]).

**Not the default since 2026-10-27.** Author: *"Claude keeps insisting in creating mp4s of captions etc outside
resolve, it should defrult to Resolve or Fusion native elements. Not create outside for no reason."* (ruling C7,
amending C6). Titles are made in Resolve: the brand's Fusion template placed by the console's `PLACE_TITLES`
(`scripts/native.py console <job>`) and measured with `title_qa.py native`. A title rendered here carries
`"engine": "hyperframes"` and an `"engine_reason"` — one of `scripts/native.py reasons`, and for a kit look Fusion
cannot make, the owner's words. `scripts/shell_gate.py` stops `node title.mjs` on a spec without them, and
`title_card.py titles` refuses the title.

Nothing about the look is decided here. The **title card** (`00-brief/TITLE-CARD.json`, made by
`scripts/title_card.py propose` and approved with the storyboard) carries the fonts, the scale, the
colours, the motion tokens and which kinds of title the film may have at all (C3: the card is the
permission list). The **title spec** (`07-edit/titles/<id>.title.json`) carries the words, the length
and the picture event the title is anchored to. `scripts/title_qa.py` then judges the render on the
real composite: safe box, worst-frame contrast, cap height and stroke on a 390 px phone, dwell,
captions, faces, flashes. `references/typography-and-captions.md` §6c is the whole procedure.

It lives in `assets/`, not `scripts/`, because it needs Node 22 and a headless Chrome. The scripts
charter (`scripts/README.md` rule 1: stdlib Python and ffmpeg) stands.

## Setup (once, in this folder)

```bash
npm ci
npx hyperframes browser ensure      # HyperFrames' own headless Chrome
npm test                            # the refusals, a still of all nine kits, two .mov renders (~1.5 min)
```

## Render

```bash
node title.mjs --card <job>/00-brief/TITLE-CARD.json --spec <job>/07-edit/titles/T1.title.json \
               --format vertical-1080 --out <job>/07-edit/titles/T1.mov
node title.mjs ... --still 1.2 --out /tmp/T1.png       # one frame to look at first
node title.mjs ... --keep /tmp/T1-project               # keep the generated project and HyperFrames' report
python3 ../../scripts/title_qa.py check <job> --title T1 --plate <the locked cut>   # the legibility gate
```

`examples/` has a card and two specs to copy. Each render writes `<out>.render.json` beside it (the
card's and the spec's hashes, the fonts, the engine version). `title_card.py check <job>` then wants,
per spec, its `<id>.mov` and a passing `title_qa` report on those exact bytes.

## What it refuses (exit 1, the reason printed)

- a kind of title the card does not name (C3), or a spec that asks for another kit than the card's;
- an ease that overshoots, on anything (C2: no overshoot on text, numbers or UI);
- a blurred entrance in ads (the 45+ phone audience);
- a card with no type scale, a spec with no length, a font that is not a file;
- whatever HyperFrames' own check fails, named in the title's terms — a line too wide for the frame is
  set on two lines (`content.lines`), never shrunk: the sizes are the card's scale steps.

## The kits

| Kit | Kinds (per lane) | Content |
|---|---|---|
| `hero-line` | ads `hero` | `lines` (≤ 4 words), `emphasis` (the one key word), `mark` bar/underline |
| `stat` | ads `stat` | `value`, `from`, `decimals`, `prefix`, `suffix`, `label`, `label_pos` — counts up, then holds |
| `price-card` | ads `price` | `kicker`, `price`, `was` (struck through after the price lands), `note` |
| `end-card` | ads, brand `endcard` | `logo` (a file beside the spec), `line`, `url` |
| `lockup` | brand `lockup` | `kicker`, `line` or `lines`, `rule`, `label` |
| `super` | brand `super` | `lines`, `plate`, `face` |
| `place-time` | drama `place` | `place`, `time` |
| `main-title` | drama `main` | `title`, `subtitle` |
| `episode-card` | drama `episode` | `kicker`, `title` |

A title enters after the clip's 0.4 s head settle unless its spec says it masks the settle (C1), and it
never spans a non-cut transition or a ramp (`title_card.py check`).

Licences: `NOTICE` (HyperFrames is Apache-2.0; GSAP is GreenSock's no-charge licence, not open source).
