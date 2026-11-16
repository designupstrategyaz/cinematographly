# Motion design — getting movement a prompt cannot describe

**When to read this:** every clip is a dolly-in, a slow push or a zoom, and the work looks static
next to the reference you were shown; a shot needs a move the model will not perform on request; you
are deciding whether a move belongs in the generation or in the cut. `cinematography-craft.md` §3 is
the *grammar* of movement — what a move means. This is the *mechanism* — how to actually obtain one.

⛔ **Read `motion-craft.md` first if the complaint is that the work looks *lame* rather than
*static*.** That file owns what a move must CONTAIN — the five animation principles a generative
model has no reason to produce, why the uncanny is a kinematics mismatch, and what "modern"
measurably is. A mechanism from this file will faithfully deliver a move that is still dead.

Checked **2026-08-29** against the account's own model roster. Prices are credits per 5s at the
stated resolution; the full matrix is `assets/higgsfield-rates.json`.

---

## 1. Why prompted motion collapses to dollies and zooms

A text prompt **biases** motion; it does not control it. "The camera moves in" has one obvious
solution and the model takes it, so a prompt-only pipeline converges on the small set of moves that
are the safest completion of a sentence: push in, pull out, slow orbit, gentle handheld drift.

This is the same wall as light. **You cannot direct a key-to-fill ratio through a prompt, only
choose a reference that already has one** (`cinematography-craft.md` §7) — and you cannot direct a
complex camera path through a prompt either. You have to **constrain it, supply it, or split it**.

⛔ And before reaching for a mechanism, check the move is the problem. Two cheaper causes come first:

- **Unmotivated movement.** A dolly that happens *to* a static subject reads as a filter over a
  photograph. Movement motivated by the subject — the camera settles because she sits, drifts
  because she crosses — reads as camera work even when the path is simple.
- **Camera motion substituting for subject motion.** "More complex motion" usually means *the frame
  is more alive*, and subject motion delivers that far more cheaply: a hand entering, a prop set
  down, a head turning to a sound, a second body crossing behind. `character-and-props.md` §6 —
  props exist to give people something to do — is a motion tool, not just an art-department one.

---

## 2. The four mechanisms, most reliable first

⛔ **Re-ordered 2026-08-30.** These were ranked cheapest-first. Cost is no longer a decision input
(`ai-generation.md` → the quality floor), and the ranking that matters is **how reliably the
mechanism delivers the move** — which happens to be roughly the same order, for a better reason:
each step down the list hands more of the outcome to the model.

### 2.1 First-and-last frame — make the path geometry, not adjectives

Author **both ends** and the model must solve the path between them. An arc, a reveal, a rise from a
table to a face, a rack from prop to person all become a *constraint satisfaction* problem rather
than a description the model can round off to a push-in.

Available only where the model's start image is a **true first frame** and it takes an end image (v2.70.0: this
table follows the call contract in `assets/higgsfield-rates.json`, and `prompt_lint.py --selftest` checks every row
against it, so the doc cannot tell you to author an end frame the lint will refuse; `prompt_lint.py --route <model>`
prints the same answer):

<!-- ffl-models: checked against call_contract by prompt_lint.py --selftest -->
| Model id | First + last frame | Why |
|---|---|---|
| `kling3_0` | yes | true first frame (measured); takes `end_image` |
| `minimax_h3` | yes, with no references in the call | true first frame (measured); frames and references cannot share a call |
<!-- /ffl-models -->

Not on it: **Seedance 2.5** (`seedance_2_5`) — its start image is a reference, never a first frame, so it has no
first or last frame and the lint refuses `end_frame:` there; its camera paths come from the scene form, or a video
reference where one exists (optional, never required). **FLUX 3** has no frames contract here. **Wan 3.0, Kling 4.0,
Gemini Omni Flash and MiniMax H3 Max** list an end role but their first frame is not measured yet. The platform also
sells dedicated **Kling Omni 3 FLF** tiers (720p 5 · 1080p 6 per 5s), a sign that the mode is a first-class path.

⛔ **Tested 2026-08-29, and the obvious reading of this is wrong.** In a controlled A/B — same start
frame, same model, same duration — **prompt-only produced MORE camera movement than FLF.** The FLF
arm's camera did not move at all: it interpolated the *pose* and left the framing locked. The
mechanism is narrower than "author both ends and get a move":

> **FLF solves for the DIFFERENCE between the two frames. If the two frames share a framing, there
> is no camera move to solve for** — you get pose interpolation with a locked camera.

So FLF is not a camera-movement tool by nature; it is a **change interpolator**, and it yields
camera movement only when the pair genuinely encodes a different framing. That is the hard part:
asked to re-render the start frame "closer, chest-up", the image model kept the wide framing and
changed only the pose. **Authoring the second framing is the unsolved step.** The next test worth
running is authoring the end frame by *cropping and re-rendering* rather than by asking for a
reframe.

**Re-tested with the end frame built by CROPPING the start frame** (upscaled, uploaded, used as
`end_image`) — so the pair encoded a framing change and nothing else. **The camera pushed in,
continuously, for the whole clip.** The model supplied the action in the middle from the prompt.

> **The division of labour: the FRAME PAIR supplies the camera move; the PROMPT supplies the
> action.** Construct the framing delta mechanically — crop and re-render — because asking an image
> model to reframe returns a new pose at the old framing.

⛔ **And a same-framing pair does not merely fail to move — it freezes.** Measured at 12fps: the
same-framing FLF clip went near-static for **1.83 seconds, 37% of a 5-second clip**, then rushed the
action into the last second. The model finished interpolating early and had nothing left to do. The
cropped-pair clip showed **no hole at all**. So: **give the pair enough difference to spend the whole
duration on, or shorten the clip to the work available**, and run `scripts/clip_qa.py` on the result
— the defect is invisible to a contact sheet.

**What FLF did buy, measurably: continuity.** In the same test the prompt-only arm's hero prop
drifted — a small amber bottle became a larger, differently-labelled one by the midpoint — while the
FLF arm held it recognisable throughout. So the honest trade is **camera freedom for continuity**,
not "better motion" (a close-out note of 2026-08-29 on first-and-last-frame against prompted motion [studio history]).

The second frame still costs about one image (~2 credits), so it is cheap to try. Build both frames
from the same reference set so identity holds across them (`refinement-loop.md` §2), and remember
the ends are the *only* thing you control: the model chooses the easing between them, so an FLF move
arrives with the model's rhythm, not yours.

⚡ **Cross-reference (2026-10-29): endpoint pairs with measured numbers.** `move-catalogue.md` §43 (the
empty-frame entrance), §46 (the closed loop, and the freeze it risks), §55 (the exit pull, its first
frame cropped from the last), §57 (the process opener), §58 (the vertical pivot), §59 (the structure
sweep) and §61 (the pinned slider parallax) are FLF recipes with the course's or Scenario's numbers. Their
**Make it** lines apply the course's split of compound moves (course notes): moves that happen at
once become an endpoint pair, moves that follow each other become two clips joined mid-move, and roll
and focus layers go in post (§54, §60).

### 2.2 Motion transfer — supply the movement from a real clip

> This is one of six ways real material and generated material can meet, and the only one this file
> covers. The others — the composite-into-the-frame trick, the cut between real and generated
> footage, an element inside a real plate, and AI altering a plate — plus the seam taxonomy and the
> disclosure exposure, are `real-and-ai.md`.

**`motion_control` (Kling 3.0 Motion Control): a character still + a reference motion video → the
character performs that motion.** `scene_control` decides whether the background comes from the
still or from the driving clip. Priced at **720p 7 · 1080p 12 per 5s** (Kling 2.6 Motion Control is
cheaper still at 5 · 7).

This is the biggest unlock on the list for character work, and the one most people never try,
because it changes where the performance comes from: **you can shoot the reference yourself on a
phone** — the gesture, the beat, the turn, the timing — and transfer it onto the character. A
performance you can act out is a performance you can direct, iterate and repeat, which is exactly
what the [PERFORMANCE] block in `ai-generation.md` asks for and cannot otherwise enforce.

⛔ Untested in this pipeline. Before it enters a client batch: verify identity survives the transfer
(the character still is the identity source, but transfer is a second sampling), and check the
licence position of any driving clip that is not yours — `stock-sourcing.md` §5's rule holds, and a
motion reference of a recognisable person is still a recognisable person.

⚡ **Cross-reference (2026-10-29).** Scenario's recast method — the driving clip framed square and
locked, the performer about half the frame height with the whole body inside, and every actor's
picture placed where the performer stands before the transfer — is `move-catalogue.md` Appendix P (P5,
the reserved §40). It waits on decisions M1–M3.

### 2.3 Video references — motion as an example, not an instruction

**MiniMax H3 takes 3 video references** (alongside 9 images and 3 audio) and its prompt addresses
them by index — *"Video 1"* (`prompting-craft.md` §6b). Seedance 2.5's `omni_reference` mode takes
video references too. Different from §2.2: motion transfer *replaces* the performance; a video
reference *informs* it, and sits alongside the image references carrying identity.

For this pipeline the practical use is the `_reference/motion/` folder the project schema already
defines (`pm-workflow.md`): a clip of the pace and texture of movement you want — an unhurried
morning, a distracted scroll, a tired sit-down — supplied rather than adjectivised.

**The second use, adopted by house decision 2026-10-23: a grey 3D blocking render as the video
reference.** It carries the camera path, the cut times and where everyone stands, built from a spec
that code checks before anything renders. The whole stage is `blocking.md`. Whether each model
follows it is the bake-off's question (lab-00011).

⚡ **Cross-reference (2026-10-29).** `move-catalogue.md` §38 (the let-go crane, blocking `let_go_crane`)
and §61 are moves whose reference is the blocking render; their prompts follow the five-block reference
order, describe what the render shows and say which input wins on framing.

### 2.4 Split the move — multi-shot, extension, and the cut

Ways to get past the fact that a single generation is 4–15 seconds on most of the roster (up to 30 on
Seedance 2.5) and degrades as the move gets ambitious:

- **Multi-shot in one generation — planned, as its own clip type.** One job yields a *sequence*
  rather than a take (Seedance 2.5 up to 30 s; Kling 3.0 and the Cinema Studio model's
  `multi_shots` / `multi_shot_mode` / `multi_prompt` too). Adopted by house decision with a cut list,
  a blocking render, approved frames and a stage plan behind it: `multishot.md`. Every internal cut is
  final, so it suits a sequence whose edit is decided, not one that will be found in the edit.
  ⚠️ **SUPERSEDES IN PLACE** (2026-10-25) — previously: "Unverified here; worth one test because it
  removes a conform step." The owner adopted the planned form without the test; it is still
  unmeasured here, and `multishot.md` §10 names what the first jobs measure.
- **Extension / continuation.** Seedance 2.5 has a `video_extension` mode (forward *and* backward)
  and FLUX 3 does continuation. This is how a move outgrows the duration cap without a visible join.
- **Video edit (v2v)** — keep a real plate and change one thing in it. `[VENDOR · Seedance 2.5 Prompt
  Writer, file dated 2026-10-22; Part 2 deck p.3 — not measured here]`:
  - the source runs **at least 4 s** (pad a shorter one with a freeze on its last frame) and, per the
    deck, under 20 s, with 1–5 images;
  - the generation's duration **matches the source**, or the model invents past the end of it;
  - the source is declared master for camera, framing, motion, timing, background and light, and the
    prompt states the one edit;
  - if the same defect comes back across batches, the action has no anchor in the source: switch to
    i2v from a frame of the plate rather than batching again;
  - where takes will be joined in the edit, plan **1–2 s of the empty location** — a clean cut point a
    generated take otherwise never gives you.
- **The cut — and this is usually the right answer.** A complex move in real filmmaking is often
  three shots, not one crane. Two simple moves cut on movement read as more dynamic than one
  elaborate move, cost less, and fail less: cut inside the motion and the viewer's prediction
  carries them across the join (`editing-storytelling.md`). At 40 seconds on a phone, **the edit is
  the motion system** — the generator only has to supply pieces good enough to cut.

⚡ **Cross-reference (2026-10-29): joins measured.** The whip join (`move-catalogue.md` §1's amendment:
a 0.10–0.15 s ramp, 0.5–0.8 s of blur across the cut, the same direction and size both sides) and the
counter dive (§36: accelerate into a dark or solid opening and open the next clip on it, which also hides
the incoming clip's settle head).

### 2.5 Texture after the path — the measured feel bands

⚡ **Added 2026-10-29** from our capture of the a cinematography course (course notes;
the legend before `move-catalogue.md` §34). A path says where the camera goes; texture says who is
holding it. These are the course's real rigs measured in its own units: **jitter** is the frame-to-frame
residual of the camera's motion in % of the frame per second, read on the background. They are targets
for post texture on a generated clip and the classes a `motion_qa` texture finding would report. ⚠️ They
are not `shot_graph.py`'s shake ratio (`TH["shake"]` 0.55, uncalibrated), and the two are not reconciled
(`shot-relationships.md` §8): re-measure the fixtures with the plugin's own tools before any band
becomes a gate. `[PRACTITIONER · course notes · measured from a 360p decode]`

| Feel | Jitter %/s | Measured on real rigs |
|---|---|---|
| **Locked** | < 0.8 | tripod A-roll 0.48–0.8; image stabilisation on, standing still, 0.10–0.13; a monopod held 0.10–0.30; the release wide after a fight 0.64–0.85 |
| **Float** | 0.8–2.5 | gimbal arcs at motor strength 1, 1.4–1.7; Glidecam walking arcs and circles 1.8–2.8 (its pushes and pulls sit lower, 0.3–0.9); operated monopod pans 1.6–2.3 |
| **Controlled handheld** | 2.5–5 | a peel push 3.4–4.0; an overhead turn 4.2; a monopod dragged on a stiff head 3.5–4.4 |
| **Calm handheld** | 5–12 | product prep moves (median 8.2); a walking follow 7.7; drama presence close-ups 8.3–9.0 |
| **Agitated** | 12–25 | handheld wides in a fight 24–25; an 85 mm near-still frame 12.65 |
| **Frantic** | 25–65 | fights at MS–CU 27–64 (the finished cut 44–68); a gym clip 13–57 |
| **Shaky, unusable** | over 65 sustained beyond about 1 s; or 25 and over held past about 2.5 s with no contact driving it; or over 12 on a calm beat | — |

How to read them:
- **By shot size.** The same operator reads about 50 at MS–CU and about 25 at FS/WS. Where the lens is
  known, report it per degree of view too: 12.65 %/s at 85 mm is 3.0 °/s; 1.42 %/s at 24 mm is 1.05 °/s.
- **Masked.** Subject motion, a near occluder, candle flicker and parallax all count as jitter: an orbit
  with no shake read 16–18, and a steady slider behind playing hands 12.4. Read the background, outside
  the person box and saturated highlights; when parallax is high and the speed is over about 10 %/s,
  don't class the shot.
- **Too clean is a finding too.** A clip planned as handheld that moves (pan or tilt ≥ 2 %/s, or scale
  ≥ 3 %/s) but reads under 0.8 has come back as a gimbal: `realism-qa.md` V10, measured.

Where they are used: post texture for a calm product move at 3–8 while moving and 2.5 or less on hero
holds (course notes); an action beat as a base walk of 5–10 plus impulses on the contacts
(`move-catalogue.md` §51, drama and action only — the ads lane bans camera shake, `product-video.md`
§2.5). The word "handheld" never goes in a prompt (`cinematography-craft.md` §3.8): the texture comes
from post or motion transfer.

**Move speed by family, beside the feel bands** `[PRACTITIONER · course notes · measured from a 360p decode]`.
Our capture of the course's commercial and transition lessons puts the camera rows' median speed at about
4.3–18.6 %/s for coverage and spot families (the product family's 18.6 is the outlier) and about
0.6–3.4 %/s for presenters and hosts. In an instructional or explainer film the movement and the shake
sit on the example, not on the person explaining it. These are speeds, not jitter, and they are not
reconciled with `shot_graph.py` either: re-measure before any gate (`move-catalogue.md`, the legend
before §34).

**A music-video family, beside those** `[PRACTITIONER · course notes · measured from a 360p decode]`. The same
capture of a course puts performance coverage at medians of about 2.9–12.9 %/s and
behind-the-scenes coverage at about 3.1–4.9 %/s. Lessons with as few as 2 camera rows are weak evidence,
and the 12.9 comes from 11 rows. Speeds, not jitter, and not reconciled with `shot_graph.py`: re-measure
before any gate (`move-catalogue.md`, Move speed by family).

---

## 3. Speed, not path

Much of what reads as "complex motion" is **ramping**, not geometry. The Cinema Studio model exposes
a `speedramp` parameter (`slowmo`, `speedup`, `impact`, `linear`), and the same effect is available
in the edit on any clip. A held beat that drops into slow motion on the product reveal, or a snap
speed-up across a transition, restructures the rhythm of a shot whose camera path is a plain push.

This is also the cheapest fix in the file: it costs nothing at generation time and is a Resolve
retime (`editing-and-audio.md`).

**And it is how you get an ease-out at all.** Measured 2026-08-29 across three clips: every one
peaked in its *final second* and ended mid-motion — the model blocks the anticipation and the action
and never the settle. A ramp on the tail is the only way to manufacture the landing, and a shot that
merely cuts does not need one. The measurement, the mechanism and the eight remedies are
`timing-and-performance.md` §5 and §7; `scripts/clip_qa.py --landing` decides which of your shots
actually has to land.

⚡ **Cross-reference (2026-10-29).** Where a slow motion has to come from (a 60 fps source or an
optical-flow retime) is `move-catalogue.md` §24's amendment; reversing a clip at 100 % so it ends on the
approved frame is §47; the snap zoom's ramp in the edit is §49.

---

## 4. What the presets actually are

The platform advertises "250+ presets for camera control, framing and VFX", and the preset library
is worth knowing — but read it honestly. What the API returns is overwhelmingly **scenario and VFX
templates** (ORBIT 360, FLOAT SPIN, EARTH ZOOM, ACTION FIGURE, STICKER PEEL, CGI BREAKDOWN…), built
for viral formats rather than wellness or home UGC. Three or four are genuine camera-path presets
worth borrowing (**ORBIT 360**, **FLOAT SPIN**, the EARTH ZOOM in/out pair); the rest will fight the
register of a sleep or homeware ad and should be treated as a different product.

⛔ A preset also takes the shot's look with it. Check it against the client's Visual Bible before it
reaches a batch (`brand-system.md`).

---

## 5. The order to work in

1. **Is the move motivated?** If not, fix the blocking before the mechanism (§1).
2. **Would subject motion serve better than camera motion?** Usually yes, and it is free (§1).
3. **Can the move be stated as two frames, on a model in the §2.1 table?** Then FLF it — one extra image, and
   the path stops being the model's choice (§2.1). On Seedance, write the path in the scene form instead.
4. **Is it a performance rather than a camera path?** Shoot the reference and transfer it (§2.2).
5. **Is it longer or more compound than one generation can hold?** Split it: multi-shot, extension,
   or — most often — cut it (§2.4).
6. **Is the problem rhythm rather than path?** Ramp it, in the edit (§3).
7. **Does the shot have to LAND?** Then the move needs a settle the model will not generate — plan
   the tail ramp or the freeze-settle into the edit, not into another regeneration
   (`timing-and-performance.md` §7).

Log which mechanism produced each shot in the manifest (`shot_manifest.py --note`), because the
retake economics of FLF and motion transfer are not yet measured here and the first ten shots are
the measurement.

---

## 6. What this file cannot tell you

- **Motion transfer, multi-shot, extension and v2v are all UNVERIFIED in this pipeline.** They are
  read from the live model roster, the tool contracts and vendor guides, not from shots that shipped.
  Treat the first use of each as a bake-off with a named comparison, per `ai-generation.md`'s
  adoption rule — the planned multi-shot clip included: it is adopted by house decision, and its yield
  is still the first jobs' measurement (`multishot.md` §10).
- Prices decay; the matrix is dated. Re-preflight before quoting a batch built on any of these.
- Nothing here fixes a shot that is boring because the *idea* is boring. A more complex camera move
  on a weak beat is a more expensive weak beat (`ideation.md`).
