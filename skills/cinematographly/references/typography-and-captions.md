# Typography & Captions — the only text this skill renders

Captions are burnt in on almost every video here, Feed placements are still often watched muted, and
any required disclosure rides in the same layer. That makes type a **primary deliverable**, not a
finishing touch — and it was the one craft this skill had no guidance on at all.

⚠️ **SUPERSEDES IN PLACE** (2026-10-21) — previously: "most viewing is muted". Meta reports 80 % of Reels
viewed with sound on [PRIMARY* · Meta "How to Reels" deck, Instagram internal data, Aug 2022 · checked
2026-10-21]; the muted-majority figure for Feed is Meta's own from February 2016, with no newer one found
[PRIMARY · Meta for Business, Feb 2016 · checked 2026-10-21]. Captions stay; the sound is built for
sound-on viewing.

Self-contained. Sources are named inline for provenance (Stocks, *Universal Principles of
Typography*; Brown & Coles, *A Pocket Guide to Combining Typefaces*; Shaw, *Design for Motion*;
Segall, *Choosing Colors*; Mahon, *Basics Advertising: Art Direction*; Crook & Beare, *Motion
Graphics: Principles and Practices from the Ground Up*) — you do not need any of them open to use
this file.

---

## 1. Two separate tests: legibility and readability

**Legibility** is whether one glyph can be told from another — `1 l I`, `0 O o`, `b d`, `p q`, and in
Romanian `ș ş`, `ț ţ`, `ă â î`. It lives in the **typeface**.

**Readability** is whether a block can be comprehended over time. It lives in the **setting** —
size, leading, measure, tracking, contrast.

You must clear the legibility floor before readability work means anything, and a legible face can
still be set unreadably. For captions on a phone, at a glance, with motion behind them, both are
tight constraints.

**The caption legibility test:** render one caption line at final resolution, view it at phone size,
at arm's length, on a bright and a dark frame. If any character is ambiguous or any diacritic is
lost, the face or the setting is wrong. Do this once per brand, not once per video.

## 2. Choosing the face

- **X-height is the lever, not point size** (Stocks). X-height is the height of the lowercase
  letters; it governs how big type *looks* and how well it reads small, independent of nominal size.
  Two faces at the same point size can look very different. **For captions, prefer a large
  x-height** — it is the single biggest readability gain at small sizes.
- **Fit for purpose.** A display face is for a title, never for a caption run. Grotesque and
  neo-grotesque sans faces with open apertures and generous x-heights are the reliable caption
  choice; condensed faces buy width at a real legibility cost and should be a deliberate decision.
  The display-face rule holds unless the job's CHECKPOINT carries the `caption-display-face` switch
  (`assets/project-switches.json`): the client's own display face for captions, with a regular weight flagged
  as a contrast risk rather than swapped; `title_qa`'s contrast check and the phone proof still apply (v2.48.0,
  switch `caption-display-face`).
- **Diacritics are a hard filter.** Many otherwise good faces have poorly drawn or badly positioned
  Romanian comma-below characters (`ș ț`), or fall back to a different font for them, which produces
  visible mismatch mid-word. **Test the target language's full character set before adopting a face**
  — this is a client-profile decision, made once.
- **Weight and width are a hierarchy toolkit** (Stocks). Prefer a family with several weights over
  pairing two families; a superfamily (sans + serif of one design) is the next-best move. **Pair two
  unrelated faces only if you must** — Brown & Coles' family-first rule.
- **When you do pair: anchor plus companion** (Brown & Coles). One face carries the identity (the
  anchor), the other supports. Compatibility runs on **weight, width, stroke contrast, x-height
  harmony and counter/aperture rhythm** — match on x-height by adjusting point size, not by setting
  both at the same nominal size.

## 3. Setting captions

| Control | Rule | Why |
|---|---|---|
| **Size** | Large. Test at phone size and arm's length, not on a desktop monitor | The whole audience is watching on a 6-inch screen at a glance |
| **Measure** (line length) | Short — roughly **20–40 characters** per line on 16:9 and 1:1, and **about 25 at most on 9:16**, well under the 45–75 of body prose (Stocks/Bringhurst). Pop captions (§3b) are 1–3 words | Video captions are read in glances between watching the picture, not scanned as a paragraph |
| **Lines** | 1–2 on screen at a time. Three is a wall | A third line pushes into the safe zone and outlives its audio |
| **Leading** | ~110–130% of size; enough that ascenders, descenders and diacritics never clash between lines (Stocks) | Romanian stacks accents; a tight default will collide |
| **Tracking** | Slightly positive at small sizes and for any all-caps run; never negative on caption text (Stocks — track inversely to size) | Small type needs air; negative tracking closes the counters that carry legibility |
| **Case** | Sentence case. **All-caps for long runs wrecks readability** even when every glyph is legible. The one use of capitals is a short hook *title* when the brand's face has no bold weight — set a little larger, never a caption run (§6c item 1) | Word-shape recognition disappears in caps |
| **Alignment** | Centred low, or left-aligned — pick one per brand and hold it | Consistency is a brand signal; mixing reads as sloppy |

⚠️ **SUPERSEDES IN PLACE** (2026-10-21) — previously, the measure: "roughly **20–40 characters** per line
for burnt-in video captions". On 9:16, 40 characters do not fit at a readable size inside the safe width:
BBC's vertical limit is about 25 characters a line [PRIMARY · BBC Subtitle Guidelines v1.2.5 · checked
2026-10-21].

## 3b. Two caption regimes — line and pop

The table above is the **line regime**: a sentence or half-sentence per caption, read in glances.
Direct-response UGC mostly runs the **pop regime** instead: one to three words at a time, synced to the
voice. Of 13 DR ads read in lab-00009, 7 ran pop captions, 5 line captions and 1 mixed the two [measured ·
lab-00009 · 2026-10-21]. Which regime a job uses is a brief and profile decision (§8), not a default.

| Control | Pop regime | Source |
|---|---|---|
| **Chunk** | 2–3 words by default; 1 word only for a punch word (a number, the product name); never more than 4. Break at phrase boundaries, never inside article + noun, preposition + phrase, or a verb | [PRIMARY · BBC Subtitle Guidelines §3.4 · checked 2026-10-21]; the measured chunks were 1–3 words, median 2 |
| **Presentation** | Show the whole chunk at once; a colour highlight may move word to word. Never build a chunk up one word at a time | Word-by-word accumulation was the worst of four conditions [PRIMARY* · Rajendran et al. 2013, *Perspectives* 21(1) · checked 2026-10-21] |
| **Timing** | In on the first word's speech onset, at most 2 frames early; out when the next chunk replaces it. At least 0.5 s a chunk (merge a shorter one into its neighbour); 0.6 s in claim passages for a 65+ audience | Derived from first-fixation and per-word gaze times (lab-00009 R2 §1); the measured chunks held 0.33–0.72 s, median 0.63 s, over 8 ads |
| **Rate** | The speech rate: about 2.5–3.0 words a second for a 45+ audience. TikTok's 5–10 words a second is for text overlays, not synced captions | [PRIMARY · TikTok, Creative best practices · checked 2026-10-21]; BBC's 160–180 words a minute |
| **Size** | 80–88 px heavy sans at 1080 wide, with a 6–8 px dark stroke; never under about 67 px | 67 px is derived from BBC's 9:16 sizing; the stroke is [VENDOR · practitioner and vendor guides, lab-00009 R2 §1 · 2026-10-21] |
| **Contrast** | At least 4.5:1 against the actual pixels behind the text (§4) | [PRIMARY · WCAG 2.2 SC 1.4.3 · checked 2026-10-21] |
| **Motion** | One entrance of 3–5 frames (opacity, or scale 0.9 → 1.0), then static while it is read. No bounce loops, no per-letter effects, no flashes | §6; flashing screens are banned in Meta ads [SECONDARY · lab-00009 R2, quoting Meta's ad standards · checked 2026-10-21] |

**Claims, numbers, prices, disclaimers and review quotes leave the pop stream.** They go in a boxed
sentence caption the viewer can re-read: at most 2 lines of about 25 characters, held at least 0.33 s a
word [PRIMARY · BBC Subtitle Guidelines · checked 2026-10-21], inside the safe box (§5b). These are the
lines a viewer has to be able to check, and a pop stream takes the re-read away.

**Build pop captions from the final VO's word timings** (forced alignment, Whisper word timestamps, or the
TTS engine's own), and rebuild them after every VO change. Never spread a line's duration evenly across
its words. `scripts/build_srt.py` writes line-regime cues from the locked script; it does not write
word-timed chunks yet.

**In either regime, a caption leaves with the shot it sits on.** A cue edge a frame or a few off a
picture cut flashes across the cut: move the edge onto the cut wherever that keeps the cue inside its
regime's timing (a pop chunk no more than 2 frames before its speech; any cue on screen until its
audio ends, §5); where it cannot, the voice wins. Keep a place name or a short phrase on one line,
and merge a stub left over into its neighbour — the pop regime's 0.5 s merge is the same move.
`srt_qa.py` warns when a cue edge falls 1–8 frames off a picture cut in the timeline dump.
[PRACTITIONER · course notes] the pass costs about an extra half hour a film.

⚠ **One bounded exception to the tracking row.** The motion-graphics literature reports the opposite
instinct for type *in motion*: letter-spacing that reads fine standing still looks loose once the
type is travelling, so moving display type often wants **tighter** tracking [SECONDARY · Crook &
Beare, *Motion Graphics: Principles and Practices from the Ground Up* — via a local extraction, read
2026-08-29]. That genuinely disagrees with the row above, and it resolves by regime rather than by
preference — their case is large display type moving across frame, the row above is small static
caption type where positive tracking buys back legibility the size is costing. **Caption tracking
never goes negative. A large moving hero title may** — decided by eye at phone size, like everything
else here.

## 4. Contrast — the failure that actually happens

**Contrast is tonal, not chromatic** (Segall). Two different hues at similar brightness leave text
unreadable, and this is the most common caption failure in generated footage, because the background
is *moving* — a caption that is legible in frame 1 sits on a bright sky by frame 40.

Fixes, in order of robustness:

1. **A backing plate** — a semi-opaque rounded box behind the caption. Ugly to designers, reliable
   for viewers. The default choice when footage is uncontrolled.
2. **A drop shadow or outline** on the type. Cheaper visually, weaker on busy backgrounds.
3. **Reserving a caption band** in the composition — keep the lower third of every generated frame
   visually quiet, as a shot-design constraint. Best-looking, requires discipline at the prompt stage
   (`production-design.md`).
4. **Never** rely on the footage staying dark. Check the caption against the **brightest** frame it
   sits on, not a representative one.

The order holds unless the job's CHECKPOINT carries the `caption-shadow-first` switch
(`assets/project-switches.json`): an enlarged, softened drop shadow first, and a faint dark gradient behind the
type only where it still sinks. The contrast gate still measures the result, and in the ads lane the gradient
is a vignette, so it also needs `finish-texture` (v2.48.0, switch `caption-shadow-first`).

## 5. Placement and safe zones

- **Read the safe zones off the format preset** (`assets/delivery-formats.json`), not from memory —
  they differ by aspect and platform, and a derived re-crop inherits none of the master's margins.
- Captions sit **above** the platform's bottom furniture, clear of the right-hand action rail on
  vertical placements.
- **A required disclosure is not a caption — it is a first-frame obligation.** It appears from frame
  one, at caption prominence or larger, inside the safe zone, and it does not scroll away with the
  dialogue. See `compliance.md` §2: a disclosure covered by platform UI is not a disclosure.
- Hold each line caption long enough to read: about **0.3 s per word**, and never shorter than the audio
  it captions [PRIMARY · BBC Subtitle Guidelines, "around 0.3 seconds per word" · checked 2026-10-21].
  A static card keeps a 1 s base on top of that. Pop chunks follow §3b.

  ⚠️ **SUPERSEDES IN PLACE** (2026-10-21) — previously: "a rough floor is **~1 second plus ~0.3s per
  word**". The 1 s base had no source, and BBC's rule has none. On speech-synced captions it makes a
  three-word chunk spoken in 1.1 s hold 1.9 s, so every chunk lands about 0.8 s further behind the voice.
- ⚠ **That floor is for text the audio is already saying. Text the audio does *not* say needs far
  longer.** Motion-graphics practice puts on-screen reading at **1–2 seconds per word for content
  that matters, ~0.5s per word for text meant only to be skimmed** [SECONDARY · Crook & Beare,
  *Motion Graphics: Principles and Practices from the Ground Up* — via a local extraction, read
  2026-08-29] — three to six times this file's caption floor. The two rules do not agree, and **both
  are kept, by regime.** A caption is *redundant* with the voice: the viewer is confirming words
  they are already hearing, so the short floor holds. A **hero title, a stat, a price, a line the VO
  never speaks, or a disclosure** is the *sole* carrier of its content and gets the slower rate. The
  practical consequence is one-directional: **non-redundant on-screen text is almost always on
  screen too briefly**, and the fix is Crook & Beare's own — *fewer words, longer dwell*, never
  smaller type to fit more in.

## 5b. What the four platforms actually constrain

Everything above is craft. This is the part that is documented, and it decides more of the layout
than taste does.

**The box is much tighter at the bottom than UGC convention assumes.** The evidenced 9:16 safe box
is **top 15% / bottom 35% / left 11% / right 28%** (`delivery-format.md` §3 — measured from TikTok's
and Google's own template files). Standard UGC caption placement is around 70–80% of frame height:
**inside the keep-out.** Two consequences:

- **Captions sit lower-middle, roughly 55–62% of frame height** — visually higher than the
  convention, and correct. Anything below ~65% is under the platform's own caption, CTA and
  profile furniture on a paid placement.
- **The right margin is 28%, not 6%**, because of the action rail. Centre-set captions absorb this
  for free; left-aligned blocks running full width do not.
- **Measured against DR practice:** the three 9:16 DR examples in lab-00009 centre their captions at
  63.7–66.1 % of frame height, at the edge of that keep-out [measured · lab-00009 · 2026-10-21]. To match
  the look without crossing it, keep the chunk's bottom edge at or above y 1248 on 1920: at 88 px, a
  one-line chunk centred no lower than about 62 % and a two-line one no lower than about 60 %.

**When a 9:16 master must also survive a 4:5 Feed crop**, keep key text and faces inside the centred
1080 × 1350 box (y 285–1635 on 1920). Intersected with the platform boxes, the area safe everywhere is
x 120–960 and y 285–1248, with the TikTok rail notch at x 780–960 below y 840 [derived · Meta's 14 % /
35 % / 6 %, TikTok's in-feed template scaled to 1080 × 1920, lab-00009 R2 §2 · 2026-10-21]. No Meta page
defines a 4:5 area inside 9:16: the box is a geometric guard against Feed cropping, and a client's own
guide (a 4:5 box drawn on its template) wins.

**When a 9:16 master will also show as a 1:1 Feed crop**, keep key text and faces inside the centred
1080 × 1080 square (y 420–1500 on 1920). Intersected with the same platform boxes, the area safe
everywhere is x 120–960 and y 420–1248, with the TikTok rail notch at x 780–960 below y 840 [derived ·
the square computed on 1080 × 1920, the platform boxes as for 4:5 above · 2026-11-03]. The eye line at
30–40 % of frame height (y 576–768, `cinematography-craft.md` §5.10) and the caption band above already
sit inside it; a disclosure set at the very top of the 9:16 box (from y 288) does not, so on such a
master it sits at or below y 420. A client's own square guide wins here too. [PRACTITIONER · course notes] a
16:9 in-stream crop of a vertical is rare and ruins the frame.

**TikTok publishes the only pacing figure any of the four gives:** *"We recommend displaying
**5-10 words per second** when using text"* **[PRIMARY · ads.tiktok.com/help/article/creative-best-practices
· 2026-09-08]**. Read against §5's dwell floors, that is a *ceiling on density*, not permission to go
fast: it is compatible with the redundant-caption floor and flatly incompatible with the
non-redundant rate. A hero line or a disclosure at 8 words/second is unreadable on every platform.

⛔ **Only two of the four accept a caption sidecar, so on the other two every word is burned in.**
YouTube takes SRT/VTT/TTML; Facebook takes SRT only, named `<file>.en_US.srt`, ≤200 K, via the Graph
API. **TikTok and Instagram accept none.** That is why the safe box is binding rather than advisory —
there is no fallback layer the platform can render outside the picture.

**Instagram caps how much of the frame text may occupy:** a recommendation-eligible reel is one
*"where text does not cover the majority of the screen"* (`discovery-and-search.md` §4). Combined
with TikTok's pacing ceiling, the documented direction is consistent: **the presence of text helps;
the density is what gets penalised.** Fewer words, longer dwell — which is §5's conclusion arrived
at from the platforms' side.

**Facebook demotes hashtag-stuffed and unrelated captions** — that is *post copy*, not on-screen
type, but it is the one caption rule Facebook publishes and it runs opposite to Instagram's
keyword advice. The post copy is written per platform; the burned-in type is not
(`discovery-and-search.md` §4b).

---

## 6. Type in motion

From Shaw, *Design for Motion* — text animates differently from objects:

- **Opacity fades for body/caption text**; position moves are harder to read.
- **Letter-spacing shifts** read better than position shifts when you want movement.
- **Staggered character reveal** draws attention — reserve it for a single hero title, never for captions.
- **Never animate weight or size in rapid succession** — it reads as janky.
- **Nothing should move linearly.** Ease-out (fast → slow) for entrances and arrivals, ~200–400ms;
  ease-in for exits, ~300–600ms. Under 200ms is imperceptible; over 1s is a cinematic statement and
  wrong for a caption.
- **Typography is content, not decoration** — motion must amplify legibility, never obstruct it.

**For this skill specifically:** line captions do not animate; they cut in and out with the line. Pop
captions (§3b) take one short entrance and are static while they are read. Motion beyond that on caption
type is a tell of over-production and costs legibility for nothing.

⚠️ **SUPERSEDES IN PLACE** (2026-10-21) — previously: "captions do not animate. They cut in and out with
the line." No study found shows a brief entrance hurting reading. The evidenced harms are building a
chunk up word by word [PRIMARY* · Rajendran et al. 2013 · checked 2026-10-21] and flashing, so those are
what §3b forbids.

## 6b. ⚡ Motion for supers, titles and end cards — a working system

`[PRIMARY · kinetic-motion-lab.vercel.app — source read, frames captured with Playwright at 1440×900 and 390×844, measured 2026-10-04]`, cross-checked with `[PRIMARY · IBM Carbon, Motion overview, carbondesignsystem.com/elements/motion/overview · checked 2026-10-06]`.

Captions still do not animate (§6). This is for the few text elements that may move: one hero title, a
price or stat card, the end-card lock-up. The figures come from a motion lab built with unusual
discipline (one curve family, one damping scale, every exit faster than its entrance) and from a design
system's published tokens. They are a house system to adopt, not a law.

1. **One curve family per brand, written into its type block (§8).** An entrance that decelerates — the
   lab's `cubic-bezier(0.16, 1, 0.3, 1)`, Carbon's expressive entrance `cubic-bezier(0, 0, 0.3, 1)`; an
   exit that accelerates — the lab's `cubic-bezier(0.4, 0, 1, 1)`, Carbon's expressive exit
   `cubic-bezier(0.4, 0.14, 1, 1)`; and one in-out curve for a whole-frame "scene" move — the lab's
   `cubic-bezier(0.87, 0, 0.13, 1)`. Every super in a series then moves the same way, which is what makes
   a series read as one brand.
2. **Three duration tiers.** Micro 200–350 ms (an underline, a highlight) · component 450–760 ms (a super
   or price card arriving) · choreography 800–1,300 ms (an end-card lock-up assembling). Carbon's tokens
   run shorter (70–700 ms) because they serve an interface, not a film; on video the component tier is the
   default for a super.
3. **Exit no slower than the entrance.** The lab exits in roughly half its entrance time (a panel 480 →
   260 ms; a dialog 760 → 560 ms), all on the one accelerating curve. Shaw's figures in §6 put exits
   *longer* (300–600 ms) — the sources disagree. For a super, prefer the fast exit or a straight cut: by the
   time it leaves, the eye has moved to the next shot (this file's reasoning, not a measurement).
4. **Stagger 15–35 ms per element.** The lab's hero letters rise 32 ms apart over 1.3 s; its layout tiles
   14 ms apart. Per-letter stagger is for the one hero title (§6), never a caption.
5. **⛔ Text lands and stops: no overshoot on any text, number or UI** — a hero line, a super, a price, a
   stat, a disclosure (house rule C2, 2026-10-26: *"No overshoot on text"*; all three council models
   agreed, and HyperFrames' own motion rules say the same — titles land and stop dead, no bounce on text or
   numbers). A damped overshoot is allowed only on a non-text brand shape (a logo mark, a plate's edge),
   and only when the project's title card allows it. `title.mjs`, `supers-gsap` and `title_card.py lint`
   refuse an overshooting curve; `title_qa.py` measures it on the pixels.
   ⚠️ **SUPERSEDES IN PLACE** (2026-10-26) — previously: "Overshoot is a damping decision, not a style.
   Functional pieces — a super, a price — sit at damping ratio ≈ 0.6–0.77, overshooting 2–9 %; playful
   brand moments at ≈ 0.3–0.45, overshooting 24–42 %." Those bands were measured on a web motion lab's
   interface pieces; on a 9:16 ad read by a 45+ viewer the bounce costs the moment the eye needs to read.
6. **The leading edge moves first.** Something that travels or stretches moves its front first and lets
   the back follow about 80 ms later; it reads as weight instead of a slide.
7. **Enter from the side the picture is travelling.** A pan or dolly pulls the eye in its direction of
   travel `[PRIMARY · Bruckert, Christie & Le Meur 2021, arXiv 2102.13378 · checked 2026-10-04]`; a super
   that arrives from that side is found, one that arrives against it is hunted for.
8. **Dwell starts when the text is legible, not when the move starts.** The animation is extra time on
   top of §5's reading floor and the end card's Clearcast hold (`sequence-grammar.md` §2c, item 11). Do
   not land a super in the half-second after a hard cut or straight after the peak (§2c, item 12).
9. **Key both ends of every move.** The lab's notification entrance was written with only a start state;
   the engine treated it as the end state and the toast played backwards, sinking and fading before it
   snapped into place. In Fusion or After Effects the same mistake is a single keyframe — set the start and
   the end explicitly.
10. **Bake the motion in the edit.** Supers are animated in the finish, never left to a platform's text
    tool, so every cut-down and aspect ratio carries the same motion. **Fusion is the default** — the card's
    Fusion title **generated from these tokens** (`fusion_titles.py build`, v2.45: the curves as the keyframes' own Bézier
    handles, so no overshoot; the exit folded onto the clip's last frames), placed in Resolve by computer control,
    never through the API (v2.49, house rule 8; §6c item 5; `editing-and-audio.md` § Captions and titles, The
    generated titles). Nobody keys a template by hand: the motion is in the generated file. The optional
    lane `assets/supers-gsap/` renders a super from the brand's curves and durations (rules 1–4), for every
    delivery preset, as ProRes 4444 with alpha for the track above the cut — **only with a recorded reason**
    (house rule C7, 2026-10-27; the spec's `engine: gsap` and `engine_reason`, §6c item 5). It refuses a hold below §5's floor, any overshoot
    (rule 5), and text outside the format's safe box. It needs Node, so it sits outside `scripts/`; its
    README has the setup and the evidence. The project's other titles — a hero line, a stat, a lockup, a
    main title — go through §6c.

The full teardown — every interaction with its trigger, properties, timings, curves and 16 reusable
recipes — is kept in lab record lab-00007 (not shipped).

## 6c. ⚡ The project's titles — the title card, the kits, the gate

Author, 2026-10-26: *"we need to create far better titles, suitable to each project"*. Research and a
three-model council (lab record lab-00015 (not shipped); the titles and motion proposal of 2026-10-26 [studio history])
ranked the ideas; the owner chose all four packages — *"A: Title card + type system, B: HyperFrames + the
legibility gate, C: Lane kits + review loop, D: Transitions + ramps"* — and ruled on the conflicts (C1–C6). Owner,
2026-10-27: *"Claude keeps insisting in creating mp4s of captions etc outside resolve, it should defrult to Resolve
or Fusion native elements. Not create outside for no reason."* That is ruling **C7**: it amends C6 (item 5).

**1. The title card** — `00-brief/TITLE-CARD.json`, from `title_card.py propose <job> --lane
ads|brand|drama|captions-only`, filled from the client profile's type block (§8) and approved with the
storyboard. One per project. It carries the anchor face and its companion **as font files**; one type
scale (`base_px` and one ratio: label · body · title · hero · display); case, tracking, the colour pair and
the plate; the motion tokens (an entrance and an exit, each a family, a duration and a curve; the stagger;
the mark and count times); the kinds of title the film may have, each with its kit, position, word and
count caps and hold; and the transition and ramp budgets (`editing-and-audio.md`, the transition grammar).
`title_card.py lint` reads the font files themselves and refuses a placeholder, a missing file, a faux
weight or italic (a style the file does not have — Stocks), a pair that differs on neither weight, width
nor stroke contrast (Brown, Coles & Gregory), no single scale, more than 5 durations or 3 curves (Shaw), an
overshoot (§6b rule 5), blur in ads (lifted per job by the `blur-titles` switch), a hero line over 4 words, more than 2 accents or 2 ramps. **Picture lock
refuses without a card that lints clean** (`gate.py approve lock`). When the brand's face has no bold weight, the
honest fallback for a short hook line is capitals set a little larger, recorded on the card — never a faked bold, and
never on a caption run (§3).

**2. ⛔ The card is the permission list (house rule C3: *"Yes, the card is the permission"*).** Captions
stay on regardless. A title whose kind is not on the card is not made (`title.mjs` refuses, `fusion_titles.py`
writes no template for it, and nothing is placed) and not
approved (`title_card.py titles` refuses). A captions-only card is a real card: it says the film has no
titles, and it is still approved.

**3. Per-lane defaults** (`assets/title-lanes.json`; the three council models converged; every number
[assumed] until approved ads calibrate it):
- **Ads:** captions stay; a hero line of ≤ 4 words in a heavy display sans with one highlighted key word; a
  stat that counts up and holds, or a price card; a large end card held ≥ 2.5 s; opacity or rise moves
  only; no blur, glow or scramble. The blur ban holds unless the job's CHECKPOINT carries the `blur-titles`
  switch (`assets/project-switches.json`): a brand line, a closing lockup or a small mark — never the hook card — may enter with a blur that clears to
  sharp while it fades up and rises, mirrored out, still a native Resolve title on the lane's durations and
  curves (v2.48.0, switch `blur-titles`) — when and where: `editing-and-audio.md` § Finishing looks, and the
  blur-in block below.
- **Brand:** one lockup per film — a display serif anchor with a sans companion, tracking-in or a mask
  reveal; the end lockup held ≥ 2 s.
- **Drama:** a main title, place-and-time supers, an episode card; one calm style across 9:16 and 16:9.

An explainer's step chips have no lane yet and wait on Q2 (`modes/editorial-explainer.md`), unless the job's
CHECKPOINT carries the `step-lower-thirds` switch (`assets/project-switches.json`): a native Text+ lower third
on the shot each step or tip names, with no leader line (v2.48.0, switch `step-lower-thirds`).

**Blur-in titles — when, where and how much (v2.48.0, switch `blur-titles`).** The ads lane's no-blur rule above
holds by default. This block is what binds once the switch is on; the decision rule is in `editing-and-audio.md`
§ Finishing looks. The switch covers a brand line, a closing lockup or a small mark (the `hero-line` and `lockup` kinds); never the hook card. The lint lifts by kind and cannot tell a hook from a brand line, so a blurred hook is a finding at review. Nearly
all the timing evidence comes from web-UI component libraries, so it is weak.
- **When.** A calm, premium single line: a brand line, a logo lockup or a closing statement of a few words, once
  per film [SECONDARY · iArt.ai; Aimran UI library]. A narrative or music-video title card, where tone matters more
  than speed, as in trailers [SECONDARY · Codrops 2013]. The course's ad gives its text graphic and a
  small location mark one blur-and-rise preset, and its own end cards leave through a blurred frame
  [PRACTITIONER · course notes · read off the course frames]. The keynote style the device is credited to teaches restraint,
  not blur: in Apple's "Don't Blink" each word holds 5–7 frames [PRACTITIONER · Justin Cone, Motionographer 2016].
- **Not when.** The hook card, the first title a viewer sees. TikTok wants the proposition inside the first 3 s
  [PRIMARY · ads.tiktok.com/help/article/creative-best-practices] and Meta the brand and key message [SECONDARY ·
  Terrads, quoting Meta], and every blurred frame there delays the read [INFERENCE]. Prices, offers, legal lines,
  disclosures, CTAs, instructions and body copy [SECONDARY · MotionKit]. Captions, ever: a blurred caption spends
  the reading time it is owed (§5; Netflix sets at least 20 frames on screen and up to 20 characters a second
  [PRIMARY · Netflix Timed Text Style Guide]). Busy or moving backgrounds [SECONDARY · FontsCompare]. Blur stacked
  with a stagger, a wipe or a glow on one line: pick one driver [SECONDARY · iArt.ai]. A reveal that makes the
  viewer wait to read [PRACTITIONER · Aurora Harley, NN/g].
- **Where.** The switch lets `title_card.py lint` pass a `blur-resolve` entrance on the `hero-line` and `lockup`
  kinds only. The lint cannot tell a hook from a brand line, so a hero line used as the hook stays sharp, and a
  blurred hook is a review finding. The `end-card` kind, which usually carries the offer, the URL or the CTA, is not
  lifted and stays sharp. Use it once per film, on the anchor its spec names (item 4), and on the whole line rather than per
  character for a clear message [PRACTITIONER · School of Motion]. The end state sits inside the safe box (§5b); an
  entrance from off-frame can cross a UI zone on the way [SECONDARY · AffRoom]. Native only (C7): `fusion_titles.py`
  already builds `blur-resolve` as Text+ into a Fusion Blur whose size runs to 0 over the entrance, on the card's
  curve (item 5). By hand, keyframe each Text+ shading element's Softness from high to zero with its opacity; or
  run Text+ → Blur → Transform in Fusion; or put a Blur Dissolve into the title on the Edit page [PRIMARY · Resolve
  21 manual, ch. 55–56; Fusion manual, Text+]. Look in the Effects Library first, because Resolve 21's new
  motion-graphics effects were not checked one by one. A per-word stagger uses the Follower modifier; confirm in
  Resolve 21 that Softness animates there before relying on it.
- **How much.** There is no reliable video number. Web-UI sources put the whole reveal at about 0.5–0.8 s with an
  ease-out and a small blur that ends at exactly zero [SECONDARY · iArt.ai; MotionKit; vawe.dev]. Their pixel values
  do not transfer to video, so scale the blur to the type and judge it at phone size [INFERENCE]. The course runs a
  blur from 50 to 0 with opacity 0 to 100 and a short rise, mirrored out [PRACTITIONER · course notes], on another
  NLE's scale, so no number carries over. The ads lane's entrance is 450 ms (`assets/title-lanes.json`)
  and `fusion_titles.py` starts the blur at a size of 10; both are [assumed]. The blur clears inside the entrance,
  and item 4's reading floors count from the frame it reaches zero [INFERENCE from Netflix's subtitle timing].
- **Delivery.** Hold the title static and fully sharp after the reveal, so the encoder gets identical frames to
  build detail on. The soft halo bands on dark or gradient grounds after a re-encode [INFERENCE from codec
  behaviour; PRACTITIONER · Gerald Undone]. A baked-in blur ignores the viewer's reduce-motion setting, so keep it
  short and small [INFERENCE; PRIMARY · W3C 2.3.3, whose erratum counts blur as motion, for web animation a user
  triggers]. `title_qa` runs its whole gate on the title as usual (item 6).
- **Tells it is cheap.** Every line blurs in, the preset look; blur is stacked with stagger, wipe and glow; the
  reveal takes longer than the read; a residual softness never clears; the easing is linear; a clear headline is
  revealed per character [SECONDARY · iArt.ai; MotionKit; PRACTITIONER · NN/g; School of Motion; Hlib Trazanov 2026].

**4. The title spec** — `07-edit/titles/<id>.title.json`: the kind, `duration_s`, the words (`content`),
`said_by_vo`, and the **anchor**: the picture event it starts on (a cut, the settle, a beat, a join) and its
`at_s`. `title_card.py titles <job>` holds each spec to the card: the kind is on it, the kit, the word and
count caps, the reading time by regime (0.3 s a word when the VO says it, 1 s a word when it does not, the
kind's `min_hold_s`), the anchor in the cut — **after the clip's 0.4 s head settle** unless the spec
declares `masks_settle` (house rule C1) — and never across a non-cut transition or a ramp (read from
`07-edit/timeline-dump.json` and the ramps' `cut_in`/`cut_out`).

**5. The engines — Resolve first (house rule C7, 2026-10-27, amending C6's "1+3").**
- ⚠️ **SUPERSEDES IN PLACE** (2026-10-27) — previously: "**Resolve's installed title templates** (marketplace packs
  included) are for **16:9 openers only** until the `FUSION_TITLE_SPIKE` toggle in `resolve-production-console.py`
  proves a template's text can be set by script and read back", with HyperFrames listed first as the engine (C6).

- ⚠️ **SUPERSEDES IN PLACE** (2026-10-29) — previously: "The look lives in the brand's Fusion title: a Text+ (or an
  installed template) styled once with the card's faces, scale, colours and motion tokens, dragged from the timeline into
  the media pool and named as the card's `native.template`." That manual step was never done on a real job, so every
  title went outside (v2.45; the author: *"It keeps making mp4s which it imports"*; the author's research notes).
- **Resolve, by default — generated from the card.** A spec with no `engine` is `resolve`. `fusion_titles.py build
  <job>` writes one Fusion title per kind on the card: the anchor face and its Style (the weight as a name, 700 → Bold),
  the style frame's size for the kind, the ink, the tracking, the plate (`colors.plate`) on a plate kind, the end card's
  page, and the entrance and exit as keyframes from the motion tokens. `native.py console <job>` rebuilds it if the card
  changed (a stale template refuses). **Placing it is computer control** (v2.49, house rule 8: native titles,
  Fusion and Fairlight are never done through the API): in Resolve's own interface, install the `.drfx`, lock every
  track but the target, drag each spec's template onto its named track (Titles, Supers, Disclosure) at the spec's
  `at_s` for its `duration_s`, and type the words per tool (a field — `price`, `was`, `url` — on the tool of that
  name). Then check it on screen at full size, frame 0 and the last frame included, and let the API **read it back**:
  the words, the face as Resolve has it (`CHECK_FONTS`; a face missing from Resolve is installed by hand from the
  card's files), the card's hash and the fold. A row that cannot be placed **stops**: report it, never render the
  title elsewhere to get past it. What the generated title does not make yet (per-word, stagger, a stat's count, the
  one-word highlighter) is a WARN in `title_card.py titles` — the owner's call.
  ⚠️ **SUPERSEDES IN PLACE** (2026-11-05) — previously: "its `PLACE_TITLES` inserts each spec by the template's
  installed name, or as a stock Text+ with the generated comp imported, moves it onto its named track … writes the
  words per tool". The owner, on the API route for titles, Fusion and Fairlight: *"It fails all the time."*
- **The brand's own packs** (Background Reveal, JTechWP, Video Editor Studio …) are mapped to the kinds by
  `resolve_library.py scan` (`editing-and-audio.md` § The installed library); a pack title is placed by computer
  control the same way, its words typed and read back, its layout checked at 9:16.
- **Outside Resolve, only with a reason.** **HyperFrames** — `assets/titles-hyperframes/` (Apache-2.0, Node 22): nine
  kits as ProRes 4444 with alpha for the track above the cut, each through HyperFrames' own lint, layout, motion and
  contrast check; the sizes are the card's scale steps and are **never shrunk to fit**. **supers-gsap** for a plain
  super. A spec names `engine: hyperframes` or `gsap` and an `engine_reason` — one of `native.py reasons`; for a look
  Fusion cannot make, that is the owner's words (`{"code": "owner", "why": "…", "quote": "…"}`). `title_card.py
  titles` refuses an outside engine with no reason, and `shell_gate.py` stops `title.mjs` or `render.mjs` on such a
  spec before it runs.
- **⛔ A title is never a movie you import** (v2.45). `title_card.py titles` refuses a spec made in Resolve with a rendered
  movie beside it (`<id>.mov`, `<id>_*.mov`, `<id>.optN.mov` — naming what made it, e.g. HyperFrames 0.8.204); `approve
  titles` and `approve export` refuse a title-folder movie sitting on the timeline (from the timeline dump). An old
  render goes to `07-edit/titles/_superseded/`.

**6. The legibility gate** — on the composite, over the whole dwell. A title made in Resolve: render the cut as
usual and again with `render-mp4.py TITLES_OFF` (same settings), then `title_qa.py native <job> --title <id> --with
<the render> --without <the titles-off render>` — the difference is the title, the off render the picture behind
it. One rendered outside: `title_qa.py check <job> --title <id> --plate <the locked cut>`. Either way: the ink inside the format's safe box (strict for paid); the time it is in
and still against the reading floor; no edge passing its resting place (C2, measured); contrast against the
**worst** frame behind it (3:1 large, 4.5:1 small — WCAG, used for video [assumed]); a **phone proof** at
390 px wide (the thinnest stroke ≥ 1.2 px, the cap height ≥ 14 px large or 9 px small — a FAIL in ads and
for 45+); no collision with the captions (the SRT and the caption band), a face or the product (`--avoid`);
no more than 3 flashes a second; no text cut at the frame's edge; a centred title centred on the **frame**, not the
safe box (WARN past 2 % of the width, FAIL past 4 %) — and the frame is the delivery preset's: `render-mp4.py` refuses a
timeline of another shape than the preset, because it moves the centre every graphic is placed on (the same shape at
another size is a scale at render, and is named); and on an opaque card, a WARN when the largest empty rectangle
covers over half the safe box. It writes `<id>.native.qa.json` (or `<id>.mov.qa.json`) and a review strip.

**7. The review loop — inside Resolve** (v2.45). A hero title may get up to three options (`<id>.opt1.title.json` …).
For a title made in Resolve they are placed on a **duplicate** of the cut, one `Titles opt<N>` track each, by computer
control (v2.49, rule 8; the API's `PLACE_TITLE_OPTIONS` placement is retired with `PLACE_TITLES`), and after the
duplicate the comps' media ranges are re-checked (a duplicate once shifted one by a frame). They are reviewed as
**Resolve's own stills** — `Timeline.ExportFrame`
at entrance · legible · mid · exit · gone, each option alone and with every title track off — then `title_qa.py
strip-native <job> --title <id>` sets them side by side and runs what a still pair can answer (safe box, worst-moment
contrast, frame edge, centre, the phone proof). Motion (dwell, overshoot, flash) is read from every frame
(`OPTION_FRAMES = "all"` → `title_qa.py native --with-frames … --without-frames …`). Nothing renders outside, and the
cut is never touched. An outside option (with its reason) is rendered over the plate as before (`title_qa.py strip`).
The owner picks one in chat (`title_card.py pick <job> <id> --option N` — for a native title it copies the spec and
records the stills, and refuses a movie beside it); two revisions at most. **One designed hero
beat** per video, two at most: a ramp, a motion-matched join and the stat landing on the settle, planned
together at the storyboard rather than found in the edit.

**8. The stage.** `gate.py approve titles` comes after picture lock: every title on the card measured and passing
`title_qa` on those exact bytes — Resolve's two renders and the spec as it is, or the outside render
(`title_card.py check`). Export checks it again, so a title re-rendered or re-worded after approval is caught.

**9. ⚡ The style frame — agreed before any title is built** (a supplement ad job, 2026-10-28: titles and cards took about six
design rounds, and almost every round fixed something a rule could have set up front — white outlined text on cream
paper, names at H5 then H1). One approved still sets, as tokens on the card (`style_frame`):
- the typeface (the font name Resolve shows, and its style);
- the type scale as Text+ Size, a share of the frame width: H1 0.125 · H2 0.10 · body 0.07 · caption 0.06 ·
  disclosure 0.042 (the values that worked on that job [measured on one job]);
- the ink on paper and on footage (two colours, never one for both);
- the alignment and the left margin (x 0.115 on that job);
- **one emphasis device** for the whole film — the highlighter, a colour, a weight or an underline. On that job the
  yellow highlighter on the checklist, the supers, the ingredient pills and the certificate rows is what made the ad
  feel designed.

Render the still in Resolve — place one title per kind by computer control on a scratch timeline over a plate frame
(v2.49, rule 8); export each one's still (`Timeline.ExportFrame`, a read the API may still do) to `09-qa/stills/` —
show it with the storyboard, then
`title_card.py style-frame <job> --still <png> --by … --quote "…" [tokens]`. A title made in Resolve waits for it
(`title_card.py check`). `fusion_titles.py` writes the tokens into every generated title (size, colour, alignment, the
face's Style, the plate or the highlighter on element 3), and re-generates them — with a new hash in every name — when
the style frame changes.
- **Centre on the frame, not on the safe box.** Cards centred at x 447, the middle of the 11–72 % paid box, looked off
  centre. Visual weight centres on x 540; the safe box only limits where load-bearing text may reach.
- **Make the words fit before rendering.** `title_card.py fit <job>` sets every title's lines at its style-frame size
  in the anchor font and measures them against the width the safe box leaves. Ingredient names came out cut on
  that job ("RUTI", "FUCI") and were found only in the render. The fix is a line break or fewer words — never smaller
  type.
- **Use the client's own assets where they exist.** A badge redrawn from the brand's own icon was approved
  at once; the version drawn here was not.
- **When titles go native, rewrite their specs from the timeline.** `title_card.py check` went on judging S01 by an
  old animated .mov ("needs 2.56 s") after the title moved into Resolve. Dump the timeline (`DUMP_TIMELINE_JSON`, which
  now carries each title's words), then `native.py sync-specs <job> --write`.

**10. Cards — the product card that worked.** ⛔ Never paste an image over a blurred, stretched copy of itself — the
owner called it "cheap PS". On one job this was approved: the same paper backdrop as the other cards; the product in
a rounded image card with a soft shadow; a 7-frame settle, then a slow push; the content kept clear of the caption
band. Every card also gets the negative-space look: a tick alone in the middle of a card read as unfinished
(`title_qa` warns when one empty region covers over half the safe box). A card that moves is a sound event: its sound
goes into the placement in the same pass (`editing-and-audio.md` §7f). The blurred-copy ban above holds unless the
job's CHECKPOINT carries the `blurred-fill` switch (`assets/project-switches.json`): a too-tight shot may fill a
vertical frame over a blurred, enlarged copy of the same clip, for a shot on screen about two seconds; swapping the
clip is still the first answer (v2.48.0, switch `blurred-fill`) — when and where: `editing-and-audio.md` § Finishing
looks, and the blurred-fill block below.

**The blurred fill — when, where and how much (v2.48.0, switch `blurred-fill`).** The ban above holds by default.
This block is what binds once the switch is on; the decision rule is in `editing-and-audio.md` § Finishing looks.
- **When.** The last resort, for one too-tight shot in a vertical frame, after every other answer:
  - another shot (still the first answer);
  - a reframe by hand, or Smart Reframe, in the 9:16 timeline (`editing-and-audio.md` § Resolve at volume);
  - a split screen for two speakers [PRIMARY · BBC Arts social video spec];
  - a designed or brand-colour plate.

  It earns its place where a crop would destroy information: a two-person interview, a screen recording or a slide,
  a talking head who gestures [SECONDARY · Make Vertical; Crisp]. Blackmagic built Blanking Fill to make blanking
  less intrusive in news and documentary [PRIMARY · Resolve 21 manual, ch. 165].
- **Not when.** A paid 9:16 placement where a native version is possible. Meta reports a 15 % lower cost per result
  for 9:16 with sound than for non-9:16 without [PRIMARY · Meta Reels Ads Guide]. Google serves horizontal ads in
  Shorts with blurred bands top and bottom [PRIMARY · Google Ads Help · support.google.com/google-ads/answer/16041697],
  so a hand-built fill looks like the platform's own fallback, a sign the ad was not made for the placement
  [INFERENCE]. A single centred subject that would crop cleanly [SECONDARY · Make Vertical; Crisp]. A delivery spec
  that asks for a bespoke edit per shape [PRIMARY · BBC Arts]. A face or product that repeats as a giant ghost in the
  fill [PRACTITIONER · Joseph Lipsen]. Any timeline-wide default.
- **Where.** Shot by shot, never the whole film [SECONDARY · MediaScaleUp]: one shot, on screen about two seconds
  (the switch's own limit, from HR-03). The geometry for 16:9 in 1080×1920: the fitted band is 1080×608 at y 656–1264, 31.6 % of the height.
  Its bottom edge sits 16 px inside the bottom 35 %. That is the house box's bottom and the one Meta figure the house
  accepts (`delivery-format.md` §3), so on a paid placement nothing below the band is usable. Captions keep their
  §5b position (55–62 % of the height), which falls on the band; titles go on the band or above it (y 288–656),
  never over the busy fill [SECONDARY · Disabled World; AAA Presets]. The research's looser per-platform strips below
  the band do not override the house box. In Resolve, use Resolve FX Stylize › Blanking Fill on the clip, with Zoom
  Mode, Blur Background, Fade Amount and Fade Color, Blend Edges and Drop Shadow [PRIMARY · ch. 165 ·
  docs.imaster.org/davinci-resolve-21-manual/part-12-resolve-fx-overview/ch.-165-resolve-fx-stylize]. Or build two
  layers: the clip zoomed to cover (about 3.16×) on V1 under a Gaussian Blur and a darker, desaturated grade, and
  the fitted clip on V2 [SECONDARY · Make Vertical; PRIMARY · Smart Reframe docs, for the Mismatched resolution
  setting]. The course crops its under-layer a little top and bottom and feathers the edge [PRACTITIONER · course notes]. The
  plate is the same effect at Fade Amount 1.0 in the brand colour, never white on TikTok, whose UI text is white
  [SECONDARY · Oposto]. The shot gets no Film Look Creator Halation or Film Gate (`editing-and-audio.md` § Finishing
  looks). A plate and a fill both leave the picture as a band, which `discovery-and-search.md` §6's no-letterbox
  check flags on a post meant for discovery. If a job ships a shape the placement does not take natively, check the
  platforms' own auto-fit, or the platform makes its own fill: Google's Video Enhancements are on by default
  [PRIMARY · Google Ads Help 13652431], and Meta has video touch-ups [SECONDARY · Adlio].
- **How much.** Blur until no shape in the fill reads, and darken it a little so it never competes [SECONDARY ·
  Make Vertical]. Fix the geometry first (Zoom to Timeline before Stretch), and add Blend Edges only if a seam shows
  [SECONDARY · videomontazher]. An encoder recipe and an API template give numbers (a radius-8 box blur at quarter
  resolution with brightness −0.06; 75 % opacity) [SECONDARY]; neither is adopted. No source gives a hold time after
  which a fill tires viewers: about two seconds is this plugin's own limit from HR-03, not a finding. The course's
  crop of 4 or 5 is its crop control, not pixels [PRACTITIONER · course notes]. If the format block allows a 4:5
  deliverable, the same band fills about 45 % of 1080×1350 [INFERENCE · arithmetic]. That is the client's format
  decision (`delivery-format.md` §1), never the fill's.
- **Delivery.** A moving blurred fill costs bits a flat one does not, and the frame shares one budget, so the sharp
  band loses detail; a darker, heavier blur leaves it more [SECONDARY · Make Vertical; PRACTITIONER · Gerald Undone;
  INFERENCE]. A large soft field bands after the re-encode, and fine grain helps [PRACTITIONER · Rich Young]. Never
  stretch the foreground [SECONDARY · Crisp]. Stabilise shaky handheld first, or the full-frame copy spreads the
  shake across the whole screen [INFERENCE].
- **Tells it is low-effort.** Ghost faces or products in the fill; a fill as bright or saturated as the subject; a
  hard seam or a visible stretch; a fill on every shot, so the ad reads as a file made for another frame and never
  reworked [PRACTITIONER · Lipsen; SECONDARY · Make Vertical; videomontazher; Sutrahaus].

## 7. Type as tone of voice

Type carries brand character before a word is read (Mahon). Two rules that matter more than taste:

- **One dominant element** (Mahon). If the frame is busy, the type is quiet; if the frame is quiet,
  the type can carry weight. Both shouting is the classic busy-ad failure, and in video it is worse
  because the picture is already moving.
- **Subtraction, not addition** (Mahon). Ask what can be removed. In this skill that principle is
  already policy — captions are the only on-screen text by default; every other title is one the
  project's approved title card names (§6c, house rule C3), and overlay windows and watermarks stay off
  (`editing-and-audio.md`).
- **Motion is a hierarchy channel, and this skill has deliberately given it up — so dwell is what is
  left.** In motion graphics the most important text element earns the most striking motion or the
  longest time on screen [SECONDARY · Crook & Beare, *Motion Graphics: Principles and Practices from
  the Ground Up* — via a local extraction, read 2026-08-29]; because §6 rules that captions do not
  animate, the only hierarchy levers remaining in this skill's text layer are **time on screen**,
  size and weight. That is a feature rather than a loss: it puts hierarchy in the script (which line
  deserves to linger) instead of in an effects panel. But it has a cost worth stating — **a hero
  line given the same dwell as every caption around it is not, to the viewer, a hero line.**

## 8. The brand's type block — decide once, in the client profile

Goes in `clients/<brand>.md` §6 (Visual Bible):

- **Caption regime**: line or pop (§3b), and the accent colour if the pop regime highlights words
- **Caption face** + weight, and the fallback if it is unavailable on the edit machine
- **Size, leading, tracking, case, alignment** at the delivery format's resolution
- **Contrast treatment**: plate / shadow / reserved band — and its exact values
- **Colour**: caption fill and plate, as hex, checked for tonal contrast
- **Disclosure treatment**: size relative to captions, position, duration
- **Motion** (only if the brand animates supers, §6b): the entrance and exit curves as cubic-bezier
  values, the duration tier and the stagger. `assets/supers-gsap/` reads exactly these fields
- **Title faces** (§6c): the anchor display face and its companion **as font files** with their weights,
  the type scale's ratio, the accent and the end card's background — what `title_card.py propose` fills
  each project's title card from (`--anchor`, `--companion`, `--accent`, `--page-bg`)
- **Character-set check**: confirmed for the target language's full diacritics

## 9. Caption QA — add to the export gate

- [ ] Legible at phone size, arm's length, on the **brightest** frame each caption sits on
- [ ] Every diacritic correct and drawn by the same font as the rest of the word
- [ ] Line regime: 1–2 lines, ~20–40 characters per line (about 25 at most on 9:16). Pop regime (§3b):
      1–3 words a chunk, the whole chunk shown at once, at least 0.5 s each. No clashing extenders
- [ ] Claims, numbers, prices and disclaimers in a boxed sentence caption, not in the pop stream
- [ ] Inside the format's safe zones, clear of platform UI
- [ ] Every caption holds long enough to read and never shorter than its audio — **and any
      on-screen text the VO does *not* speak** (hero line, stat, price, disclosure) is held at §5's
      slower non-redundant rate, not the caption floor
- [ ] Any required disclosure present from frame one, at prominence, not scrolling away
- [ ] Built from the locked script, never a fresh transcription (`build_srt.py`)
- [ ] Burn-in actually happened — a subtitle track does not composite by itself, and an accepted render setting
      is not a burned caption: `srt_qa.py burned` finds every cue in the delivery file's pixels (house rule C7)

Since v2.41 the timing items are **measured**: `srt_qa.py check 08-captions/<slug>.srt` refuses broken timing,
overlaps and a pop chunk under 0.5 s, and warns at over 20 characters a second, over 2 lines, a line over 42
characters, and a line caption under 0.3 s a word (long-form norms, [assumed] for social — each warning signed
off with `srt_qa.py accept`). `approve export` reads the report (`sound-off-story.md` §5).

**Cross-refs:** `editing-and-audio.md` (the subtitle track, the burn-in setting, the render) ·
`compliance.md` §2 (disclosure prominence) · `production-design.md` (the palette and the reserved
caption band) · `delivery-format.md` (safe zones per format) · `brand-system.md` (type as a token) ·
`clients/<brand>.md` §6 (where the brand's type block lives).
