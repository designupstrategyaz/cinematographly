# Delivery Format — decided by the client and the channel, never by the skill

**The skill has no house aspect ratio.** Resolution, aspect, frame rate, duration window, safe zones
and loudness target are a **client × platform** decision, and they belong in `clients/<brand>.md` §5.
Everything downstream reads them from there.

This file exists because the opposite was true for a long time: vertical 9:16 1080×1920 was written
into prose, prompts, file names, QC defaults and a script's *filename*, because the only account was
a vertical short-form account. That is how a skill quietly stops being brand-agnostic — the default
of the first client becomes an unexamined law, and the second client gets confidently wrong work.

Presets live in `assets/delivery-formats.json`; the scripts read them by name.

---

## 1. The format block — settle it at intake, before anything else

Six values. Get them from the client or the channel, never assume them:

| Value | Why it can't be a default |
|---|---|
| **Aspect** | Changes composition, blocking, how many people fit in frame, and whether a wide establishing shot is even usable |
| **Resolution** | Sets the generation target and whether an upscale step exists at all |
| **Frame rate** | 24 filmic, 25 for EU/PAL and broadcast, 30 for a lot of social, 60 for motion-heavy. Model output often differs and must be conformed |
| **Duration window** | Drives the script length, the clip count, and the cost estimate |
| **Safe zones** | Where captions, disclosures and action can live without platform UI covering them |
| **Loudness target** | −14 LUFS is a **house convention, not a platform spec** — ⛔ none of TikTok, YouTube, Facebook or Instagram publishes a loudness target for uploads, and the figure migrated in from music streaming. **−23 LUFS (EBU R128) for EU broadcast** IS a real spec. Hold −14 for consistency across a batch; never quote it to a client as a requirement |

**Frame rate on a real shoot is per shot.** The block's rate is the delivery's; the rate a real shoot
records is written on each shot, not on the job — a filmed row in the shot list carries `source: real` and
an `fps:`, and `shotlist.py --check` warns a real shot with none.
The course's readings (24 for speaking lines, 30 for coverage, 60 for slow motion or a whip; the
cards print 23.976 and 59.94) are [PRACTITIONER · course notes] choices, not defaults.

**One brief can carry more than one format.** A campaign running on Reels *and* YouTube *and* in-feed
needs 9:16, 16:9 and 4:5 — which is a `modes/repurpose.md` job (re-crop and re-check safe zones per
format), not three separate shoots. Decide up front which is the **master format** and which are
derived, because that decides how you frame: shoot for the tightest crop, protect the widest. A
website film cut from the same shoot is its own row in the block, with its own shape and length, not
a by-product of the ad.

## 2. Aspect changes the craft, not just the export

Reframing is not a delivery step you bolt on at the end.

- **Vertical (9:16)** — one subject, close. Wide establishing shots mostly fail: the useful area is a
  tall slot, so a landscape-composed wide reads as a distant subject with dead air above and below.
  Two-shots are hard; this is part of why one-line-one-clip works so well here.
- **Portrait (4:5)** — the forgiving middle. Takes both a subject and some environment. Often the
  right master when a campaign spans feed and Reels.
- **Square (1:1)** — centre-weighted; rule-of-thirds composition fights the frame. Good for product,
  weak for two-person dialogue.
- **Landscape (16:9)** — environment, scale, two-shots, and the 180° line actually reading. Editorial
  and explainer work is usually better here than forced vertical.

**Practical rule:** if a piece must exist in both vertical and landscape, **compose for vertical and
protect for landscape** — keep the action inside the vertical slot, keep the sides clean enough to
open up. The reverse (shooting landscape and cropping to vertical) throws away the subject's head or
the product, every time.

**On a real shoot that must deliver two shapes,** turn on both frame guides in the camera, record the
full sensor so the second shape is a reframe inside the picture rather than a scale-up, and cut the
second shape on its own timeline from the locked master (`editing-and-audio.md`, Resolve at volume).
The claim that a vertical crop of a 7K frame is still close to 4K is [PRACTITIONER · course notes] and was
not measured.

## 3. Safe zones are per platform, and they move

⛔ **Until 2026-09-08 the 9:16 margins in this skill were house guesses, and the bottom one was
understated by about fifteen points.** Two platforms publish real geometry — not in prose, but inside
downloadable template files — and both put the keep-out at roughly a **third of the frame height**:

| Source | Top | Bottom | Left | Right |
|---|---|---|---|---|
| **TikTok**, In-Feed Standard template PNG (720×1280 grid) inside the ZIP linked from its auction in-feed ad specs — page updated **June 2026**, file dated **2025-04-15** | 12.5% | **34.4%** | 11.1% | 11.1%, widening to **27.8%** where the action rail sits |
| **YouTube/Google**, the safe-zone SVG referenced by Google Ads Help 9128498, labelled 1080×1920 | 15.0% | **35.0%** | 4.4% | 17.8% |
| **the box that survives both** (max of each margin) | **15%** | **35%** | **11%** | **28%** |

**[PRIMARY-DERIVED · measured from the platforms' own template files, 2026-09-08 — TikTok has never
written these digits in prose, and Google's are label text inside an image. Cite them as *measured
from the template*, never as a published number.]**

⚠ **Meta publishes nothing you can check.** Its own page — *About text overlays and the Safe Zone for
ads in Stories and Reels*, `facebook.com/business/help/980593475366490` — is the arbiter and is not
machine-fetchable; it has to be opened in a browser. The only Meta-owned corroboration found is the
**35% bottom** figure in the title of a Meta for Business video, which agrees with the other two.
⛔ The ubiquitous **"14% top / 20% bottom"** and its newer **"14 / 35 / 6"** replacement both trace to
blogs citing no Meta URL. Do not use either.

**Two boxes, and the presets file now carries both.** `safe_zone_pct` is the evidenced box above;
`safe_zone_organic_pct` is the older looser house convention, which has **no** platform source
because neither TikTok nor YouTube publishes a safe zone for organic posts at all. `srt_qa.py burned`,
`title_qa.py` and `build_captions.py` (when a reason sends a burn outside Resolve) use the strict one by default and
take `--organic` to opt out.

Three rules that don't drift:

1. ⛔ **Any required disclosure sits inside the STRICT box, from frame one — never the organic one.**
   A disclosure covered by a platform's UI is not a disclosure (`compliance.md` §2b.3). The
   disclosure goes **top**, which is also where the FTC's guidance points, and is the margin least
   contested between the two published files.
2. **Anything that will run paid uses the strict box for all key creative**, not just the disclosure.
   Both published files are *ad* safe zones — they budget for the caption, the CTA button and the
   profile row, which is exactly the furniture a paid placement adds.
3. **Re-check per format, not once per campaign.** A derived 16:9 cut inherits none of the vertical
   version's margins, and this is the most common repurposing defect (`modes/repurpose.md` rule 5).
   A 9:16 master that will also show as a 1:1 feed crop keeps type and faces inside the centred
   square as well — y 420–1500 on 1920; `typography-and-captions.md` §5b intersects it with the
   boxes above — and a placement tool's suggestion to trim it for a short placement does not cut a
   finished film: its length is the format block's decision (§1).

## 4. Generation resolution ≠ delivery resolution

Separate decisions. The generation target is a **stack** question; the delivery target is a **client**
question.

- **Some stacks require generating at exactly the delivery size.** If a model inherits its output
  dimensions from the reference image you feed it, a reference at any other size comes back the wrong
  shape and costs a regeneration — which is more expensive than the resolution saving. **A profile's hard locks /
  Higgsfield account is in this category** (the client profile §6, standing rule 2026-08-13: generate
  at exactly 1080×1920). That rule is *theirs*, not the skill's.
- ⛔ **Generating below delivery and upscaling is retired (2026-08-30).** It assumed a lower-tier
  generation previews the higher-tier one. It does not — **re-running returns a different take**, so
  the cheap pass approves a video you will not ship (`ai-generation.md` → the quality floor).
  **Floor: generate at 1080p minimum, at the model's 2K/4K tier where it exists.**
  Reference *images* are the exception that survives: they never need to be high-res, because the
  video model re-renders them.
- **1080p is a floor, not a target — some deliveries still need an upscale.** Upscale to meet a spec
  above the generation tier, or to recover pixels a crop spent; ⛔ never to rescue a soft generation,
  and once on the final rather than per clip.
- **The delivered file matches its preset** (`export_qc.py --format`; in the UGC lane, delivery at the
  format's resolution, `realism-qa.md` V15). V15 holds unless the job's CHECKPOINT carries the `upload-master`
  switch (`assets/project-switches.json`): one extra upload copy of the same shape at a larger size (e.g. 2160p
  from a 1080 delivery), checked with `export_qc.py --upload-master`, every other check unchanged; the delivered
  file itself still matches its preset (v2.48.0, switch `upload-master`). Name the copy by its size (`<slug>_2160.mp4`), never with "master" in the name: native.py and soundoff.py read a file named *master* as a textless master and would skip its captions check.
- **Record which regime a client is in, in the profile,** and price accordingly. Getting this wrong
  in either direction is a real cost: unnecessary premium generation, or a batch of unusable clips.
- **Frame rate is its own trap.** A model that emits 30 fps into a 24 fps timeline must be conformed
  before import (`ai-generation.md` Step 4). Check the model's actual output rate; don't assume it
  matches your timeline.
- **A file-size ceiling is a bitrate cut.** When a delivery names a maximum file size, it goes in the
  preset as `max_mb`, and `export_qc.py` FAILs a file above it. Lower the target bitrate until the
  estimate fits, and record in the delivery note that the file is compressed harder. No size or
  bitrate is a default: set one only when a delivery names a ceiling.

## 5. What reads the format

| Consumer | How |
|---|---|
| Script + shotlist | Aspect and duration window in the header; safe zones in the shot notes |
| Generation prompts | Aspect and generation resolution per §4 |
| Edit + captions | Safe zones for caption and disclosure placement |
| File naming | The format's `filename_token` — `<SLUG>-v<N>-final_<token>.mp4` (`pm-workflow.md`) |
| `export_qc.py` | `--format <preset>` checks resolution, fps, duration and loudness against it, and the file size against `max_mb` when the preset sets one |
| `slop_check.py` | `--format <preset>` checks a batch against the target, not just internal consistency |
| The Resolve render script | `WIDTH`/`HEIGHT`/`FPS` in its CONFIG block |

**If a client needs a format the presets file doesn't have, add it there** — one JSON block — rather
than passing raw numbers around. That is what keeps the format single-sourced.

## 6. The intake question to actually ask

> "Where is this running, and in what shape — vertical for Reels and Shorts, in-feed, landscape for
> YouTube, or more than one? And is anything going anywhere other than social?"

The last clause matters more than it looks. "Also a cutdown for the trade-show screen" or "the
client wants a TV version" changes the loudness target by 9 LU and the frame rate by a whole
standard, and neither is something you can fix after the master is signed off.

**Cross-refs:** `assets/delivery-formats.json` (the presets) · `clients/_TEMPLATE.md` §5 (where a
brand's format lives) · `references/ai-generation.md` §4 (generation resolution and fps conforming) ·
`references/editing-and-audio.md` (export and loudness) · `references/pm-workflow.md` (naming) ·
`modes/repurpose.md` (derived formats) · `references/compliance.md` §2 (disclosure inside the safe zone).
