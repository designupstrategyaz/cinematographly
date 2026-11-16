# Multi-shot clips — several shots in one generation, planned before a credit is spent

**The house decision (2026-10-25).** Asked whether to keep one action per clip or to run the
multi-shot bake-off first, the owner chose neither: *"Multi shot but planned at senior level, with
reference videos, start and end frames etc"*. So a **planned multi-shot clip** is now a clip type in
this pipeline, beside the single-action clip, and this file is what "planned at senior level" means:
the edit decided before the take, a blocking render as the clip's video reference, approved frames at
both ends where the model can honour them, every reference bound to one subject, and a stage plan the
lint checks (`prompt_lint.py`, `form: multishot`).

It reverses a rule that was measured, so the measurement stays on the page beside the decision:
- 12 real clips gave a **57.6 % yield**, and **5 of 12 peaked on their own last frame**. A cut needs
  handles, and **handles have to be generated** (SKILL.md §3) `[measured 2026-09-07]`.
- **A cut made inside a generation has no handles and cannot be re-cut.** Every internal cut of a
  multi-shot clip is final the moment the take is accepted. That is the price of the form, and the
  reason the cut list is locked before anything else (§2).

The vendor side `[VENDOR · Higgsfield, Seedance 2.5 Prompt Writer, supplied 2026-10-22; Seedance 2.5
"New capabilities (Part 2)" deck, supplied 2026-10-25]`:
- one Seedance 2.5 generation runs **up to 30 s** (`assets/higgsfield-rates.json` measures 4–30 s);
- **"Use stages by default. Timestamps are a point reinforcement"**;
- time ranges are **"budgets, not cuts"**; actions land **"slightly before or after a boundary —
  never frame-accurate"**.

The last point is the one that matters for the edit: a planned boundary is where a cut will land
**roughly**, not on the frame. Measure it (§7).

**How this form relates to the scene form (v2.49).** Since 2.49 a Seedance 2.5 clip is written as
`form: scene` by default (`prompting-craft.md` §12): approved sheets, no start frame, the vendor's block
order, one continuous take unless `[FORMAT MODE]` says it cuts. The two forms split by **who owns the cuts**:

| | `form: scene` | `form: multishot` |
|---|---|---|
| Approval point | the reference sheets (`character:`, `prop:`, `world:`) | an approved start frame, and an end frame where the model can honour one (§3) |
| Cuts inside the take | none by default; a short `[SHOTS]` list the lint does not check | the locked cut list, one stage per internal shot, every cut typed (§2, §5) |
| What the lint holds | the nine required blocks, the references, 2,500–20,000 characters, the sound lines | stages tiling the duration, end states, cut types, one camera move per stage, ≤ 3,900 characters |
| Use when | one scene, one camera behaviour, the cut made in the edit | the edit depends on where the internal cuts land (§1) |

A clip that would need more than a cut or two inside it, or whose internal cuts must survive the edit, is a
multi-shot clip. Everything else on Seedance starts as a scene clip. The scene form's `[LOCATION MAP]`,
`[OPTICS]` and `[POSITIVE LOCKS]` blocks are worth carrying into a multi-shot clip's `[WHERE]` and
`[CONSISTENCY]` too.

---

## 1. When a multi-shot clip earns its place — and when it does not

| Use a multi-shot clip when | Keep single-action clips when |
|---|---|
| Continuity is the content: one light source keeping its rhythm across cuts, one geography, one prop passed hand to hand, a performance arc across three angles | The EDIT must own the cut: dialogue intercut with reactions you will choose between, a cut timed to a VO line or a music hit you have not heard yet |
| A match cut, a whip, an occlusion cut or a hidden cut that only works if both sides come from the same camera move | The shot needs a **true first frame** on a model that has none (Seedance: §3) |
| A montage at music beats where every shot is short and the beats are known | Path A voice-first lipsync (the line is audio in, one speaker, one clip) |
| A oner with several beats (the stage is a beat, not a shot) | A product hero frame that must be exact: generate it as its own clip with its own approved frames |

A multi-shot clip does not remove the shot table: every shot in it is still a row of
`sequence-grammar.md` with its size, height, move and job. It removes the conform step, and it
removes the editor's choice at every internal cut.

## 2. The plan — what exists before the prompt is written

Senior-level means the decisions are made by a person, in this order, and written down:

1. **The cut list, locked.** Mark every cut in the sequence as **internal** (made by the model, final)
   or **external** (made in the edit, needs handles). Name each internal cut's type and its reason:
   - hard cut;
   - match cut on an action;
   - whip;
   - occlusion / hidden cut;
   - foreground wipe.

   The clip's own first and last moments are external cuts, so they get handles:
   - **Stage 1 opens at least ~1 s before the cut-in point** (enter on an action already under way,
     `sequence-grammar.md` §9 item 8).
   - **The last stage holds 1–2 s past the cut-out.** That is the aftermath, or an empty-frame pause
     where takes will be stitched `[VENDOR · Seedance 2.5 Prompt Writer]`.
2. **Blocking.** `blocking.py` takes the same shot plan (its shots tile the duration and cut unless
   one says `"cut": false`, `blocking.md` §3a). Its render is the clip's **video reference** for camera
   path, positions and timing. Its top-down map is code-drawn, so it is allowed as a placement
   reference (`character-and-props.md` §8.7b); an image model's drawing of a map is not.
   ⚠ One festival team found a blocking render weak for two subjects moving in different directions,
   and worse with a non-human body, but fine for one subject at an exact camera speed (`blocking.md` §1,
   HFF-04; unmeasured here). A multi-shot clip with two people crossing gets its first take checked
   against the render stage by stage before a second is bought.
3. **Frames.** The **start frame** is approved at the frame gate like any clip's. The **end frame** is
   approved wherever the clip must land on a known picture: the handoff into the next clip, a product
   end frame, the composition a cut-out needs. What the model does with them is §3, and it decides
   the route.
4. **References, bound one subject per line** (§4), inside the model's slot limits.
5. **Stages** (§5): one per internal shot, or per beat of a oner.
6. **Lines.** One canonical list. Each line is spoken once, inside one stage, and never across a cut
   (§6). Speech inside a multi-shot clip is native audio, so the audio gate applies (`gate.py` refuses
   generated sound until `audio` is approved).
7. **The consistency block** (§5): identity count, clothing, prop ownership, seats, screen direction,
   the light source.

## 3. Which model can honour which lock — the route is decided here

`[PRIMARY · assets/higgsfield-rates.json → call_contract, measured 2026-08-29 to 2026-10-23]`. The
price of each row is `rate_card.py table`; the route is a cost decision too.

| Model | Longest take | True first frame | End frame | References | Frames + references in one call |
|---|---|---|---|---|---|
| `seedance_2_5` | 30 s | ⛔ no — `start_image` becomes a reference (corr 0.53 / 0.96) | ⛔ no | images, videos, audio — up to 30 / 10 / 10 `[VENDOR · Part 2 deck]` | frames only as references |
| `kling3_0` | 15 s | ✅ measured | ✅ | none | — |
| `kling4_0` | 30 s | not measured | schema lists it | images, videos | separate modes (`image-to-video` vs `reference-to-video`): treated as no |
| `wan3_0` | 30 s | not measured | schema lists it | images, videos, audio | no `mode` parameter, so the schema allows it — **not measured** |
| `minimax_h3` | 15 s | ✅ when alone | ✅ when alone | images, videos, audio | ⛔ 422 — measured |

So the owner's "reference videos AND start and end frames" is one call only on a model whose
contract allows both, and on this roster that is **`wan3_0`, unmeasured**. The gate treats an
unmeasured `mix` as false (`prompt_lint.call_shape`), so today a `wan3_0` clip with references binds
its start still as a reference and refuses the end frame. Running the combination is a lab job: the
owner approves setting `call_contract.wan3_0.mix` to true for it, and the take measures
- the opening frame's correlation to the approved start;
- the closing frame's correlation to the approved end;
- whether the call is accepted at all.

Write all three back as the model's `mix` and `evidence`. Until then, pick by the lock that matters
most:
- **Frames must be exact** (a handoff, a product end frame): `kling3_0` (≤15 s, no references, so the
  camera path is written in words and checked against the blocking afterwards) or `kling4_0` in
  `image-to-video`.
- **The blocking render and the cast must steer it** (camera path, positions, several characters,
  props): `seedance_2_5` or `kling4_0` in `reference-to-video`. The approved start and end frames then
  go in as **references with a stated job**, not as frames: write *"@Image 1 is the first frame of
  Stage 1 — match its composition"* and *"@Image 2 is the final frame of the last stage"*. The start
  still binds as `@Image 1` by itself (`call_shape`); the end still is declared in `refs:` as
  `what: endframe` with the approved media id, and the gate refuses it unless it IS the approved end
  frame. The first and last frames will be close, not exact: measure them (§7).

## 4. References — one subject per line, grouped, scoped

`[VENDOR · Part 2 deck p.5–14]`, consistent with what this skill already enforces (`what:` and `not:`,
`prompting-craft.md` §6b, §11d):

- **Bind each subject on its own line**:
  - `Mika corresponds to @Image 2. Use only the appearance, hairstyle, and clothing.`
  - Never `@Images 1 through 4 define four characters respectively` — the deck's own DO NOT, and the
    lint refuses a range binding.
  - Write names plainly. The deck's `<Name>` is its notation, and the lint reads `<…>` as an unfilled
    placeholder.
- **Group by type, each group with its rule:**

  | Group | Rule |
  |---|---|
  | `[Characters]` | appearance, hairstyle, clothing — plus *"Do not interchange the characters' appearances, clothing, actions, positions, or dialogue"* |
  | `[Props]` | each prop belongs to exactly one owner: *"The phone corresponds to @Image 4 and belongs only to Mika"* |
  | `[Scenes]` | space, materials and lighting — never the people in the plate |
  | `[Motion and Audio]` | a video defines motion only, *"not the person or scene from the video"*; an audio clip defines a voice and its line |

- **A subject profile** for a character who carries several references across several stages: one
  block that collects them — appearance, the fixed prop, the locations, the motion references, and
  what is NOT theirs (*"Do not give this character the Record Board"*).
- **Positional tags follow the order of the `medias` list** that `gate.py preflight` emits:
  - on a model that takes the start still as a reference, **`@Image 1` is the approved start frame**,
    then the image references in the order `refs:` lists them;
  - `@Video N` is the N-th video reference, `@Audio N` the N-th audio;
  - `prompt_lint.py` prints the map it computed;
  - `gate.py` refuses a call that binds the same pictures in another order, or leaves one out,
    whenever the linted prompt uses a positional tag. Send `gate.py preflight <SHOT> --kind clip`
    verbatim.

  Higgsfield's own Ad Multiplier workflow addresses its inputs the same way `[PRIMARY · Higgsfield
  MCP, ad-multiplier workflow, read 2026-10-24]`.
- **An @tag only goes in a stage where that subject is present.** The model will try to force it into
  frame `[VENDOR · Seedance 2.5 Prompt Writer]`.
- **Slot limits on Seedance 2.5** `[VENDOR · Part 2 deck p.2–3]`:
  - up to 30 images, each no larger than 4K;
  - 10 videos and 10 audio clips, each kind capped at 30 s combined;
  - recommended: 1–8 distinct subjects, 5–10 s per subject video;
  - for a video edit, a source under 20 s with 1–5 images.

  ⚠ The deck's VIDEOS row literally says "audio clips", a copy error on their side.
- **Several views of one character** (`character-and-props.md` §8.3b owns the sheet, §8.3f the rules for
  this route) `[VENDOR · Part 2 deck p.7–9]`. One image per view (front, back, face neutral, face
  in a strong emotion for the teeth and the facial dynamics), each declared as *"the same <A>"*, closed
  with *"All four images define one <A>. The output must contain only one such person throughout."*
  Each view spends one slot; past five characters the deck switches to a sheet plus a subject profile.
  - ⚠ The deck contradicts itself: p.7 says never combine angles into one grid image, while its p.12
    example binds *"the three views in @Image3"*.
  - ⚠ The deck claims this fusion is unique to 2.5. It is a claim: the first job that uses it checks
    that identity holds across stages and that the emotion frame does not leak its expression into
    neutral shots.
  - Generated views are allowed only as identity locks approved at the frame gate (§8.7b).

## 5. Stages — the prompt's spine

`[VENDOR · Part 2 deck p.14–20]`. One stage per internal shot (or per beat of a oner). Each stage
declares what it uses, **one** primary state change, and the state that must be visible when it
closes:

```
[STAGES]
Stage 1 | 0–6 s | MS, 35 mm, eye level, slow push-in
Use: Mika, @Image 1, @Image 4, @Video 1
Event: Mika lifts the phone and reads the screen.
End state: phone in Mika's right hand, screen toward her; Jenny at her left, still seated.
Cut: match cut on the tap

Stage 2 | 6–12 s | MS, 35 mm, eye level, the push-in continuing
…
```

- **Budgets, not cuts.** Ranges are consecutive, start at 0, end at the clip's duration, and do not
  overlap. They are a time budget, never an edit point, and a boundary lands within roughly half a
  second either side. Plan the internal cuts to survive that.
- **Fill the budget.** Too little content gives the model freedom; too much causes extra cuts or
  dropped events. A stage under ~2 s is usually merged or dropped. The Short Drama Screenwriter plans
  one shot per 2–5 s `[VENDOR]`.
- **Exact time points only for one or two critical beats per clip** (an entrance, a handoff, the cut
  frame): *"At 5 seconds, the camera whip-pans left."* Anchor a reaction to its cause, not to the
  clock: *"Two seconds after Fox sees the flowers…"*.
- **No frequencies.** Never *"three actions in one second"* — the deck's rule, and the lint refuses it.
- **One camera behaviour per stage**: the single-action rule moves down a level, it does not go away.
- **Each stage's shot is self-contained.** Write camera → who is where in THIS frame → `BACKGROUND:`
  what is behind them from this angle → the action → the light. `BACKGROUND:` per stage is the
  cheapest way to make seats stick `[SECONDARY · higgsfield-timed-prompts skill, 2026-10-06]`.
- **The consistency block closes the prompt**: identity and the number of characters, clothing, prop
  ownership, seats, screen direction, the light source — positively, once each.

**Where everyone is.** For two or more people, a `[WHERE]` block fixes the seats per location for the
whole clip:
- clock-face positions (the empty side of the table is 6 o'clock), or screen-left / centre / right
  from a named camera side;
- then one line per location: what is behind each of them.

People swapping seats between shots is the failure it prevents
`[SECONDARY · higgsfield-timed-prompts skill §2, §7]`. The positions come from the blocking spec, so
the words and the render agree.

## 6. Lines, sound and the transitions inside one take

- **One canonical list** in `[SOUND]`:
  `Lines, each spoken exactly once and nothing else:` then `<start–end s> <Name>: "<line>"`.
  - Times agree with the stages.
  - A line never spills across a cut unless the transition depends on it.
  - *"No added words, interjections, laughter or humming."*
- **Delivery per line**: tempo, emotion, and where the eyes are while it is spoken. An interruption
  starts inside the other speaker's gesture. Voice spec for clean dialogue: dry, close, no room.
- **Ambience changes on the cut frame**; diegetic music only from an established source.
- **Match cut on an action** (the tap that changes the world):
  - same lens, same angle, same face size, same pose, the same camera move continuing at the same speed;
  - the world changes on the action frame;
  - the reaction to the new world comes only after the cut, with its own time.
- **Hidden cut under full occlusion**: the camera passes behind a near shoulder until fabric fills
  every corner, and the world changes inside the occlusion. It **drifts more often than a match cut**.
- **Foreground wipe**: an opaque silhouette crosses and the next place appears round its edges.
- **Objects that vanish with the world** are written to go *"only with the world change, never before
  the cut"*.

(All of this list: `[SECONDARY · higgsfield-timed-prompts skill §4–§5, 2026-10-06]`.)

## 7. QA — measure the take against the plan

- **Boundaries.** Run `film_breakdown.py` on the take and compare the cut times with the stage
  boundaries. A miss of more than ~0.5 s `[assumed]` on an internal cut the edit depends on fails the
  take.
- **The camera.** Run `motion_track.py` per stage and compare the move, its direction and its easing
  with the blocking render's camera.
- **End states.** Build a contact sheet with each stage's last frame against its `End state:` (who is
  where, who holds what). Check the identity count per stage.
- **Frames.** Compare the opening and closing frames with the approved stills (the same correlation as
  the 2026-09-19 measurements). Record the result in `call_contract.<model>.evidence` the first time.
- **Lines.** Listen: each line once, in its stage, nothing added.
- **What a multi-shot take cannot be given afterwards:** handles at an internal cut, a different cut
  point, a re-timed stage. If one stage fails, the take fails. Plan two takes for a hero sequence;
  the selects pass needs something to select between (`prompt_lint.py` warns on single-take dialogue
  for the same reason).

## 8. Cost

Rates live in one place (`assets/higgsfield-rates.json → rate_table`), so this file only gives the
arithmetic:
- a take costs its duration × the model's per-second rate at the delivery resolution;
- `rate_card.py lookup --model <model> --res <resolution> --seconds <take>` prices one take, and
  `rate_card.py compare --seconds <take>` prices the same take across every roster model that can
  deliver it — and quote the LIST price unless the discount is the client's (`rate_card.py` says which);
- plan **two takes** of a hero sequence (§7), so the quote is twice the single take;
- the spread across the roster is wide, which is why the route in §3 is also a budget decision.

A failed stage costs the whole take, so the per-usable-second price of a multi-shot clip is the rate
divided by the take's yield. That yield has not been measured here. Probe each call with `get_cost`
like any clip, and reconcile after.

## 9. The prompt file — `form: multishot`

```
---
shot: S4
kind: clip
form: multishot
type: sequence
model: seedance_2_5
resolution: 1080p
duration: 24
aspect: 9:16
start_frame: 02-startframes/S4_open_v2.png     # approved; on Seedance it binds as @Image 1, a reference
payload: the viewer knows the app changed where they are eating, and that Mika chose it
refs:
  - role: video_references, what: blocking, file: 03-blocking/S4.mp4, manifest: 03-blocking/S4.json, not: mannequins, flat colours, floor grid
  - role: image_references, what: character, value: <media id>, not: sheet background, panel layout
  - role: image_references, what: prop, value: <media id>, owner: Mika, not: studio background
  - role: image_references, what: environment, value: <media id>, not: people in the plate
  - role: image_references, what: endframe, value: <the approved end frame's media id>
---
[GOAL]  [REFERENCES]  [WHERE]  [STAGES]  [SOUND]  [CONSISTENCY]  ([CONSTRAINTS] on Seedance; [SUPPRESS] on a model with a negative field)
```

`prompt_lint.py --template multishot` prints the full shape. What the lint holds:
- **FAILs:**
  - the stage budgets do not tile the duration;
  - a stage has no `Event:` or `End state:`;
  - a stage names two camera moves;
  - a cut type is missing between stages;
  - an `@Image N` or `@Video N` points past what `refs:` declares;
  - a range binding;
  - a frequency demand;
  - a line spoken twice;
  - the duration is outside the model's range;
  - a prompt over 3,900 characters — the ceiling Higgsfield's own Ad Multiplier workflow validates a
    Seedance 2.5 prompt against `[PRIMARY · ad-multiplier workflow v1.5, read 2026-10-24]`. It is a
    workflow's validator, not the model's cap: since v2.49 the scene form runs to 20,000 on the same model
    (`prompting-craft.md` §12), and this form keeps 3,900 until a long multi-shot prompt is tested (§10).
- **WARNs:**
  - a prop with no owner, or an environment or motion reference with no `not:`;
  - more than two exact time points;
  - a stage under 2 s;
  - a line that crosses a stage boundary;
  - a reference that no line binds;
  - two or more characters and no `[WHERE]`;
  - a prompt over 2,500 characters (past the measured single-clip band; multi-shot length is
    unmeasured).

On a model with a true end frame (`kling3_0`), `end_frame:` stays a frame, approved and bound as
`end_image` exactly as on a single clip.

What the gate holds at the call (`gate.py`, 2026-10-25):
- a `what: endframe` reference must be the approved `endframe:<SHOT>` media id, and there is only one;
  `status` asks for that approval as it does for an `end_frame:`;
- with any positional tag in the linted prompt, the call's `medias` must be in the linted order, with
  nothing missing;
- a clip whose `[SOUND]` lists lines is a clip with speech: the audio gate applies whatever its
  `type:` says.

**A correction is one variable here too** (`prompt_lint.py NEW --against OLD`). `[STAGES]` is compared
field by field: a header carries TIMING and CAMERA, `Cut:` is TRANSITIONS, and `Use:` / `Event:` /
`End state:` count against the one character they name — so one character fixed in two stages is one
variable, and a hand-off that names two people is one variable of that stage. Adding or removing a
stage is STAGE PLAN: the cut list re-opened, not a correction. A reference swap that re-words only its
own binding line in `[REFERENCES]` is one ground moving.

## 10. What this file cannot tell you yet

- **The yield of a multi-shot take on this pipeline.** The 57.6 % measured for single clips does not
  transfer either way. The first three multi-shot jobs are the measurement: count the usable stages.
- **Whether `wan3_0` honours frames and references together.** It is the only roster model whose
  contract would allow it, and nobody has run it here.
- **How far a boundary drifts.** The deck says "slightly"; §7 measures it.
- **Whether a long structured prompt helps a multi-shot clip.** The festival winners' prompts ran a
  median of about 6,400 characters; this form is capped at 3,900. One planned multi-shot clip with a long
  prompt in the scene form's block order settles it (HFF-12).
