# Shotlist / Storyboard — <PROJECT>

One row per shot. Take the shot count from the runtime and the pace in `references/sequence-grammar.md` §2c (dialogue-led scenes run slower, about 3.3–5.5 s a shot); no fixed count. Establish → intimate, honoring the 180° line and
eyelines. **One dialogue line = one clip; two speakers in a scene = two clips.** Start frames in
the profile's start-frame model, animate in the clip model; write each clip's prompt in the block
format from `../references/ai-generation.md` and collect them in `MASTER-image-prompts-all-scenes.md`.

| # | Time | Scene | Shot size | Description / action | Camera move / end-frame | Carries (line / TEXT) | AI-gen prompt |
|---|------|-------|-----------|----------------------|-------------------------|-----------------------|---------------|
| 1 | 0:00–0:06 | INTRO | Wide/CU | the hook beat (~6s, not 3) | static | hook line / TEXT record | … |
| 2 | 0:06–0:13 | S1 | Wide | establish location | slow push in | <char B> line A | … |
| 3 | 0:13–0:19 | S1 | MCU | <char B> reacts | static, eyeline L→R | <char B> line A | … |
| 4 | 0:19–0:27 | S2 | Medium | <char A> explains | static | <char A> line | … |
| 5 | 0:27–0:35 | S2B | Insert | B-roll (product/worksite) | drone / pan | TEXT: „…" | … |
| 6 | 0:35–0:45 | S3 | CU | the benefit beat | to-camera, palm to viewer | <char B> line | … |
| 7 | 0:45–0:55 | S4 | Medium→ECU | office → handshake | match cut | <char A> resolve | … |
| 8 | 0:55–1:05 | CTA | Medium | the resolved state, in-world branding | hold | CTA line | … |
| 9 | 1:05–1:08 | S5 | MCU | a filmed shot · source: real · fps: <rate> · lens: <mm> · stop: <f/n or Tn> · nd: <stops or density> · shutter: <1/n or deg°> · iso: <n> · wb: <n>K · focus: <mode> | static | <char A> tag line | — (filmed, no prompt) |

> **Filmed shots.** A shot filmed on a real camera, not generated, carries `source: real`
> and `fps: <rate>` in its row — the Description cell is the usual place. The frame rate is written on
> each shot, not on the job. Valid rates: 23.976 · 24 · 25 · 29.97 · 30 · 47.952 · 48 · 50 · 59.94 · 60 ·
> 100 · 119.88 · 120. `scripts/shotlist.py <job> --check` WARNs on a filmed shot with no `fps:` and FAILs
> a rate not on that list. A row with no `source:` is generated: it carries no frame rate and is not
> checked. There is no default rate; choose one per shot, for that shot's job.
>
> **Camera settings on a filmed shot.** The same row may carry what the camera was set to,
> read off the camera, beside `fps:`: `lens: <n>` or `<n>mm` · `stop: f/<n>` or `T<n>` ·
> `shutter: 1/<n>` or `<deg>°` · `iso: <n>` · `nd: <n> stops`, a density written with its point
> (`0.<n>`), or `none` · `wb: <n>K` · `focus: manual` (`mf`), `af-c`, `af-s` or `af-a`. Write `nd:` and
> `stop:` as a pair; they change together. Every field is optional and none has a default:
> `--check` notes a missing one (info, never a WARN), FAILs one it cannot read, with a hint, and only
> notes them on a row with no `source: real`. **Of these, only the lens millimetres also go into a
> frame prompt**: a frame generated to match or cut with this shot carries the mm in its [CAMERA]
> block (`../references/cinematography-craft.md` §7.1). Stop, shutter, ISO, ND, white balance and
> focus mode are not prompt controls (§7.0). The white balance goes to the grade, as the Kelvin on
> the blocking card's LIGHT line does (`../references/ai-generation.md`, "Motivated lighting in nouns").
<!-- [PRACTITIONER · course notes] One practitioner's choices on a real shoot, recorded as claims and NOT as
defaults: speaking lines (openings and asks) at 24; coverage at 30, slowed to about 80 % in
the edit; 60 for real slow motion or a whip. The course's camera cards read 23.976 or 59.94. -->

## Blocking card (one per scene — fill BEFORE prompting any start frame; `../references/direction.md` §2)
```
[BLOCKING — Scene N]
GEOGRAPHY: <room + anchor: "kitchen; window camera-left, table centre">
POSITIONS: <who is where, facing which way>
THE LINE:  <where the 180° axis runs; which side cameras stay>
EYELINES:  <who looks where, and slightly up or down>
PROPS:     <what is in whose hand, WHICH hand, where it rests>
LIGHT:     <source + side, matching the Kelvin spec>
```

## Performance cards (one per dialogue/reaction clip; becomes the [PERFORMANCE] prompt block — card v2, `../references/direction.md` §1)
| Clip | STATE (transition) | STIMULUS (what, when) | TARGET (who/what, where) | BEAT (before held, then one change) | BODY (MS or wider) | FACE (said as a state) | GAZE |
|------|--------------------|-----------------------|--------------------------|-------------------------------------|--------------------|---------------------------|------|
| S1-C1 | skeptical → curious | <char A>'s claim, line A | <char A>, camera-left | listens, still; then leans in on the second phrase | — (MCU) | smile holds at a half-smile; the head stays still | on <char A>, the whole clip |
| S1-R | curious → convinced | the meter reading (S2B) | the meter, below frame | reads it, still; then a small nod | weight comes forward, hands open | brows lift once, mouth still | down to the meter, back up to <char A> |

> Every cell names something the camera can see (`../references/acting-for-the-model.md` §2). STIMULUS may be
> "none — <char> starts it"; it may not be blank. BODY is required at MS or wider — the face is read slowly there.

## Sequence chain (one row per shot, in cut order — `../references/sequence-grammar.md` §8; check with `scripts/sequence_lint.py`)
| Shot | Scene | Beat | Size | Height | Tilt | Move | Key | Colour | Int. | Turn | Target | Dur | Energy | To camera | Break |
|------|-------|------|------|--------|------|------|-----|--------|------|------|--------|-----|--------|-----------|-------|
| 2 | S1 | orient | WS | eye | level | crane | left | warm | 0 | - | - | 4.0 | 2 | no | - |
| S1-C1 | S1 | exchange | MCU | eye | level | locked | left | warm | 1 | late: leans in | <char A> | 3.5 | 3 | no | - |
| S2B | S1 | stimulus | INSERT | eye | down 60 | rack | left | warm | - | - | - | 1.5 | 4 | no | - |
| S1-R | S1 | reaction | CU | eye | level | push | left | warm | 2 | late: the nod | the meter | 3.0 | 1 | no | the piece's one approach move |
| 8 | CTA | resolution | MS | eye | level | pull | front | cool | 1 | - | the lens | 4.0 | 3 | yes | - |

Contrast: movement: still → kinetic; size: wide → tight

Beat: orient · reorient · exchange · stimulus · reaction · dilemma · decision · release · montage · climax · resolution · insert.
Size: EWS WS MWS MS MCU CU XCU INSERT. Height: ground knee hip shoulder eye above overhead aerial. Tilt: level · up <deg> ·
down <deg> · top-down · dutch. Move: locked · push · pull · pan · tilt · track · crane · orbit · handheld · whip · rack · drift ·
roll — a move needs a job, a hold needs a reason. Key: left right front back top under silhouette flat none. Int.: 0–3, or -
with no performer. Turn: - · early: … · late: … · through: …. Dur: seconds on screen in the cut, not the generated clip length (sequence-grammar.md §2c). Energy: 1–5, the shot's energy in the sequence, planned like music (sequence-grammar.md §2d). To camera: yes/no. Break: - or the baseline this
shot breaks on purpose. Contrast: one or two of movement · rhythm · size · space · tone · colour · line, each `a → b`
(`../references/sequence-grammar.md` §2b).
> ⚡ **Continuity protects geography and identity; contrast makes the peak.** Every chain carries a Contrast line and at least
> one deliberate Break (`../references/sequence-grammar.md` §2b).
> ⛔ **The key side and the colour family hold inside a scene and change only at a Scene boundary**; under, top and
> silhouette are allowed once, on a reveal. ⚡ **Intensity climbs one step at a time; a jump of two cuts tighter going
> up and wider coming down.** ⛔ **Anyone talking to camera is at eye height, level.**

## Their sketches (stage 3 — `../references/storyboarding.md` §2; read by `board.py storyboard` and `gate.py approve storyboard`)
Ask the person for a sketch or a phone photo for the three to five shots that carry the film. One line per picture,
saved under `01-script/storyboard/their/`; their words after the path are optional. Or record a skip in their words.
<!-- - <SHOT>: 01-script/storyboard/their/<file>.jpg: "<their words>"
     skipped: "<their words>" -->

## Emotional journey map (write this FIRST — the STATE fields below are read off it; `../references/emotional-journey.md` §2)
| # | Open question the viewer is holding | Intended VIEWER emotion | Value pair & direction | Character state | CARRIED BY |
|---|-------------------------------------|-------------------------|------------------------|-----------------|------------|
| 1 | "Is this going to be another ad?" | curiosity | ignored → seen (− → +) | matter-of-fact | environment (the 11pm kitchen) |
| 5 | "Does it actually work?" | scepticism easing | doubt → trust (− → +) | unchanged | insert (the meter reading) |
> ⛔ **If every row of CARRIED BY says "face", the piece has one instrument and it is the weakest
> one.** Irony, an insert, an object, a withheld fact or a join should carry at least a third.
> ⛔ **No emotion word ever reaches a prompt** — it is converted to a circumstance and a physical
> action first (§4). ⛔ **Reference frames are cast genuine, moderate, positive-or-neutral** — a
> briefed "stressed" or "angry" face returns a vacant mask and pushing the amplitude makes it worse
> (§4.5). The negative belongs in the CARRIED BY column, not on the face.
> ⛔ **The last frame is authored as carefully as the hero frame** (peak–end).

## Handoff cards (one per shot — the join is a GENERATION instruction; `../references/shot-handoff.md` §5)
| Shot | FUNCTION | IN (frame one · inherits) | OUT (composed end frame · aftermath) | JOIN → next |
|------|----------|---------------------------|--------------------------------------|-------------|
| S1-C1 | carries line A | settled, gaze on <char>, low energy | mouth closes, breath out, gaze drops to bottle; motion at rest | J-cut — line B leads under this picture; gaze L→R continues |
| S2B | evidence (the meter reading) | tight on the display, static | hand withdraws, frame settles | hard cut on action; vector continues R |
> ⛔ **Durations are deliberately not a field here** — function, motivation and exit state are what
> the literature specifies; shot length belongs to the cut. And ⛔ **a dialogue clip is generated to
> its line**: seconds past the line are an *aftermath* you designed, never an undirected handle.

## Coverage floor (per dialogue exchange — `../references/direction.md` §3)
- [ ] Speaker clip (audio-driven) · [ ] **Listener reaction** (silent, cheap — the edit's insurance)
- [ ] One insert (hands/prop/product) · [ ] Scene B-roll ≥ dialogue clips (+2)
- **A filmed song or dance performance**, beside the dialogue floor: [ ] a wide of the
  place · [ ] the group or pair together · [ ] each face · [ ] the hands, with the edit coming back
  to the performer between cutaways. Take slates (TAKE 2, TAKE 3 …) are coverage of one room, not new
  places, and a replay pair counts once. For a generated performance each size is a paid generation
  through `gate.py`, and §3's "don't over-cover" still applies.

## Transition plan (decided HERE, not at the cut point — `../references/editing-and-audio.md` § Transitions)
| Join | Type (from the mode/brand palette) | Pack asset (exact name) or built-in | Handles needed | Motivation |
|------|-----------------------------------|--------------------------------------|----------------|------------|
| S1→S2 | hard cut | — | no | default |
| S2→S2B | J-cut (VO leads) | — | audio overlap only | continuity into the insert |
| S3→S4 | dissolve | built-in Cross Dissolve | **1–2s both sides — tell generation** | scene/time shift |
> Every non-hard-cut join here is a generation instruction: its clips get handles. A pack asset is
> named exactly or it isn't planned.

## Consistency locks
- <Character A> character block: <paste identical description used in every prompt>
- <Character B> character block: <paste identical description used in every prompt>
- Grade / look: warm natural documentary-cinematic; orange-teal; hold across all shots
- Seed / reference frames: <note the locked seed and hero-frame files>

## B-roll (cut ≥ one per dialogue clip, ideally +2 for options)
**FUNCTION is required and comes from the enum** (`../references/shot-handoff.md` §6.2): evidence ·
compress time · construct space · manage information release · contrast · parallelism · symbolism ·
crosscut · leitmotif · hide-to-reveal · ellipsis · extend-or-compress the question · re-cross the
line · POV object · rest. ⛔ An insert whose function is "there was a hole in the timeline" is not
made. ⛔ And **never play the offer, price, guarantee or CTA over B-roll** — those stay on the
speaker's face (§6.3).

| # | Insert | FUNCTION (from the enum) | AI-gen prompt |
|---|--------|--------------------------|---------------|
| S0B | intro / establishing drone | construct space | … |
| B1 | product in use (worksite) | evidence | … |
| B2 | drone over location | rest (a beat after the dense line) | … |
| B3 | the benefit (meter/bill/etc.) | evidence | … |
| … | (add until ≥ dialogue-clip count, +2) | variety + lipsync cover | … |

## Notes
- Keep action clear of the **format's** safe zones — read them from the client's format preset
  (`assets/delivery-formats.json`), not from memory; they differ per aspect and per platform, and a
  derived re-crop inherits none of the master's margins.
- Captions (target language) added in the edit, not generated in-image. Overlay windows and CTA
  cards are off by default — `TEXT:` cells are a record of the approved format, not a render task.
  Any required disclosure IS rendered, from frame one (see `../references/compliance.md`).
- Tag END FRAME only where the shot lands on a specific composed end state; simple dolly/zoom/pan = text-only, no end-frame image (saves credits).
- Run `../scripts/estimate_duration.py` on the script for the clip count this shotlist must cover.
