# Production Design — art direction, the room, the wardrobe, the props, the palette

`craft-cheatsheet.md` covers how to *photograph* a scene: shot size, lens, lighting logic, rhythm.
This file covers **what is in front of the lens in the first place**, and the art-direction judgement
that decides it. For AI-generated work that gap matters more than on a live set, because everything
in frame has to be *specified* before it exists: a room you didn't describe gets invented, and the
model invents the generic version.

**`character-and-props.md` is the companion file**: character design as staging (silhouette,
proportion, what survives at phone size in 9:16), costume as characterisation, props and
specifically their *placement*, and the translation layer for holding a character, a wardrobe and a
hero prop consistent across generated shots. This file owns the room; that one owns who is in it
and what they are holding.

**In UGC it is the whole ballgame.** The room is the authenticity signal. A viewer decides "real
person" or "ad" from the set dressing, before a word is spoken.

Self-contained. Sources named inline for provenance (Mahon, *Basics Advertising: Art Direction*;
Perryman, *The Colour Bible*; Segall, *The Complete Guide to Choosing Colors*; Neufert, *Architects'
Data*; Rumsey & Harcourt, *The Oxford Handbook of the Psychology of Appearance*; Bruce & Green,
*Visual Perception*; Davies, *Composition for Artists*).

---

> **Before the stance:** a set is an emotional instrument, not a backdrop. The environment is the
> *circumstance* a performance reacts to — which matters doubly here, because "name the circumstance,
> not the emotion" is the fix for vacant generated faces (`emotional-journey.md` §4 and §5). ⛔ And a
> room that contradicts the beat's value charge quietly cancels it.

## 0. The art-direction stance

Before any specific decision, four rules from Mahon that govern all of them:

- **Art direction is transport, not destination.** "Art direction can only be the transport, it can't
  be the whole journey." The idea comes first; the visual craft serves it. A beautifully dressed
  frame that obscures the point is a failure, not a compromise.
- **One element dominates; everything else is counterpoint.** If the image is loud, the type is
  quiet, and vice versa. Both shouting produces a busy frame with no entry point. In video this bites
  harder than in print, because the picture is already moving.
- **Subtraction, not addition.** Crop, remove, use depth of field, exploit the power of omission.
  Once a frame is designed, ask what can be taken out — and the test is that removing anything
  remaining would damage the message. Generated frames tempt the opposite: it costs nothing to ask
  for more stuff, and more stuff is usually worse.
- **Four frames.** A commercial's idea should be legible in about four key frames — opening, closing,
  and roughly two for the action between. **If the idea can't be told in four frames it is probably
  too complicated**, and a full storyboard will hide that rather than fix it. Use this as a gate
  before Stage 2, not as a drawing exercise.

## 1. The environment brief — five things, every scene

A scene description that omits any of these will have it invented for you:

| # | Field | Why it can't be skipped |
|---|-------|------------------------|
| 1 | **Room type and its function** | Determines furniture, scale, and what plausibly sits on a surface |
| 2 | **Era and economic register** | The biggest silent tell. "Kitchen" gets a showroom; "a rented flat's kitchen, laminate worktop, one good pan" gets a life |
| 3 | **The named light source, with Kelvin and direction** | Without it the model returns flat ambient — tell V9 in `realism-qa.md` |
| 4 | **Three specific objects** | Specificity is what makes a set read as inhabited. Name three; the model fills coherently around them |
| 5 | **The imperfection** | One thing out of place — a mug, a cable, a coat over a chair. The cheapest realism upgrade in the skill |
| 6 | **The practical, as an object in the list** | Field 3 names the light; this one puts the *fixture* among the nouns so the light has an in-frame alibi. Different instruction, different failure fixed |
| 7 | **The near-plane object, when the shot needs depth** | A doorway, a window jamb, a shelf edge, a hand — what the camera shoots *through*. Occludes the competing background instead of toning it down, and it is promptable where "figure/ground separation" is not |

**Field 6 is not a duplicate of field 3, and the difference is the whole point.** Field 3 goes in
the lighting block and describes the light. Field 6 goes in the **object list** and describes a
lamp: a thing with a location, a shade, a colour and a switch. *"Have the art department add a lamp
to the room and turn it on, and you've motivated any additional light you need"* — in this pipeline
the art department is the `[ENVIRONMENT]` block, so the instruction is literally to add the noun
[SECONDARY · StudioBinder, *Film Lighting*, 2023]. A frame whose light has a visible source passes
tell V9 at the frame gate rather than being argued about after the clip is paid for
(`cinematography-craft.md` §1.5).

**Field 7 buys depth by subtraction.** In 9:16 there is no lateral room to separate a subject from
its background, so the near plane is where depth comes from; and unlike almost every other
composition control it survives as prompt text — "shot through the kitchen doorway" is a sentence
that appears under real photographs. Keep the near plane **darker and softer** than the subject or
it becomes the subject, and make it an **upright** shape in vertical — a horizontal letterbox eats
the only axis with room in it (`cinematography-craft.md` §5.3, §5.10).

**Anti-pattern: the adjective stack.** "A beautiful modern cozy kitchen." Adjectives compound toward
the mean. Nouns and numbers don't.

**An exterior's brief is its world card** (`world-design.md`, since v2.42). These seven fields are written for a
room. Outdoors, the things the model invents are the sky, the sun, the wind, the depth, the land, the water and
whatever moves in the background. So they are decided once, in `00-brief/world/<LOC>.world.json`, and approved
before the first frame (`gate.py approve world:<LOC>`). Every exterior frame and clip names the card
(`world: <LOC>`) and is linted against it.

## 2. Space that reads as real

Spatial standards exist because bodies are a fixed size, and a room that violates them reads as wrong
even to a viewer who couldn't say why (Neufert: anthropometrics and building-type programs).

- **Anchor the frame to a body.** A room described without a human reference drifts in scale —
  worktops at chest height, doors two metres wide. Put a person, a chair or a door in frame, or state
  a dimension.
- **Circulation reads as truth.** Real rooms have paths through them. Furniture pushed to the walls
  with an empty middle reads as a set, because that is what a set is.
- **Standards are a starting point, not a cage.** A slightly-too-small kitchen with a real cook's
  clutter beats a correctly proportioned empty one.
- **Period settings need the negative list.** Positive description alone does not suppress the modern
  default — name the specific modern things to exclude (steel, glass, poured concrete, park benches,
  cars, power lines, wristwatches, sneakers), as a noun list in `[SUPPRESS]` or, on a model with no
  negative field, `[CONSTRAINTS]`. The failure and its fix are in `ai-generation.md`'s guardrail table.

## 3. Colour — build it as a system, once

The palette is decided once per brand and then held. Colour has measurable perceptual,
psychological, cultural and **material** properties.

**Start from one hue** (Segall). "All colour palettes begin with one single colour." Pick the primary
from the emotional target, then derive everything from it. Assembling several colours in parallel and
reconciling them afterwards is how palettes end up muddy.

**Four intent questions before the palette exists:** what should the viewer feel, what does the
category expect, what does the brand already own, and what must the product read as on camera.

**Relationships** (Perryman). Complementary = contrast and tension. Analogous = harmony and calm.
Triadic = balanced energy. Split-complementary = contrast without the harshness. Monochromatic = one
hue at varying value — the most cohesive, and the easiest to hold across an episode series. The
orange–teal pair everyone reaches for is just the complementary rule with warm skin.

**Specify all three properties** — hue *and* saturation *and* value. "Blue" is not a specification.
Saturation reads as energy (desaturated = documentary and real; saturated = stylised and
advertised). Value reads as mood (high-key optimistic, low-key serious). **For UGC, lower saturation
and higher value than instinct suggests** — phone footage in a real room is flatter than a graded
promo, and matching that flatness is what lets a generated clip sit next to archive footage.

**Distribute it 60/30/10** (Segall). Roughly 60% primary, 30% secondary, 10% accent. It controls
*weight*, not which colours. In a frame that means: the dominant environmental tone, the supporting
tone, and the small accent reserved for the thing the eye must find — the product, the panel, the
brand mark. Weighting everything equally produces noise with no focal point.

**Build the base first, accents last** (Segall). Establish the 60/30 relationship, prove it holds,
then add the 10% pops. Front-loading accents multiplies failure points before the base is proven.

**Contrast is tonal, not chromatic** (Segall). Two different *hues* at similar brightness do not
contrast. This is why captions vanish over footage and why a product disappears into a background
that is "a different colour" — judge on brightness difference. See `typography-and-captions.md` §4.

**Psychological association is real but not universal** (Perryman). Western defaults: red urgency,
orange warmth, yellow optimism/caution, green nature and health, blue calm and trust, purple luxury,
brown earthy, white clean, black sophisticated. **The cultural inversions are the trap** — white is
mourning in parts of East Asia, red is luck in China, purple is mourning in Thailand. Industry
convention layers on: finance defaults to blue, healthcare to green. Check the target audience
before borrowing an association, especially on a localized series.

**Colour depends on light and surface** (Perryman). The same nominal colour shifts under daylight
(~5600K), tungsten (~3200K) and fluorescent; it shifts with intensity, with direction, and with what
sits next to it (simultaneous contrast). Matte diffuses and evens; gloss adds speculars and
intensifies; texture mutes. **So the grade's white balance must match the Kelvin specified in the
prompt** — set both from one number and every clip shares a base before the creative grade.

**Reproducibility.** Brand colours get named in every system that will touch them — hex for captions
and graphics, plus whatever the brand book uses. They live in the client profile as tokens
(`brand-system.md` §2), not in a prompt you'll rewrite next week.

## 4. Wardrobe and appearance — a system, not a costume

Appearance carries more social information than any other element in frame, and it is judged fast
and largely automatically. Treat it as a designed subsystem with its own tokens.

**What wardrobe is doing, mechanically:**

- **The attractiveness halo is real, and in UGC it works against you** (Rumsey & Harcourt: "what is
  beautiful is good"). A conventionally beautiful presenter picks up an unearned competence and
  trustworthiness bonus — and the viewer's read flips from "person like me" to "model in an ad."
  **Cast toward ordinary for peer authenticity; the halo is an asset for authority formats.** Decide
  which you're buying.
- **Social comparison is the mechanism behind that flip.** Viewers place themselves against people on
  screen automatically; a presenter far above the audience's register creates distance, not
  aspiration, in a peer format.
- **Condition beats cut.** A slightly worn, slightly wrong-fitting garment reads as owned. Crisp and
  new reads as costume. This is the wardrobe equivalent of §1's imperfection rule.
- **Silhouette before detail.** At phone size, on a moving frame, the viewer reads shape and value —
  not fabric. Get the silhouette and the tonal value right first; texture and detail are a second-order
  gain that only lands in close-ups.
- **Wardrobe must survive the palette.** A garment that shares value with the background loses the
  figure–ground separation the whole frame depends on (§6). Check wardrobe *against* the set's 60/30/10,
  not in isolation.

**The wardrobe token block** — verbatim in every prompt, versioned in the client profile:

```
<character/persona>.wardrobe:
  garment(s)      <specific: "navy quilted gilet over a grey marl crew, sleeves pushed up">
  colour + value  <hex or named, plus light/mid/dark — must separate from the set>
  condition       <new / worn / creased / faded — say it, don't imply it>
  identifying     <the one repeatable detail: a badge, a chipped watch, a particular scarf>
  never           <what this character never wears — the negative list>
```

- **The identifying detail is the cheapest continuity lock you have.** One specific object that
  appears in every episode does more for recognition than a paragraph of description, and it survives
  regeneration better because it is concrete.
- **Three reference angles, not one** — 3/4, profile, full-body, in the same clothing — for any
  character who turns. Interpolation invents wardrobe; references constrain it.
- **Wardrobe drift is tell V12** in `realism-qa.md`. One variable per regeneration, and check
  wardrobe explicitly on the QA card rather than assuming the reference held.

**The ethical line:** do not build a video's persuasion on appearance anxiety. Appearance-related
motivation is a real lever and a flagged one (Rumsey & Harcourt treat it as "use with caution"). A
script whose engine is making the viewer feel worse about their body fails the ethics gate in
`persuasion-psychology.md` §7 regardless of how well it converts.

## 5. Props and the product

- **A prop the character touches is a physics risk.** Contact points are where clipping and broken
  grips happen. Prefer held-still or set-down over tossed, poured or squeezed; state the object is
  SOLID at a fixed position and that motion stops at its surface.
- **The product must be the real product.** Composite the actual pack shot or logo onto the start
  frame before generation. Never ask a model to render a brand mark or legible text.
- **A product in a stylised or historical world needs a bespoke redesign, not a hedge.** "Subtly
  integrated, bronze-toned" does not stop a model returning the generic modern object; replace every
  modern material cue by name. Worked example in `ai-generation.md`'s guardrail table.
- **Three objects, one story.** Every prop should answer a question about the person: what they do,
  what they can afford, what they care about. A prop that answers nothing is set dressing you paid
  credits for.

## 5b. ⚡ Plate hygiene — every background detail is a FAILURE INVITATION until you clear it

`[SECONDARY · practitioner course]`

A plate that looks finished as a still is not finished. The corpus's dirty gas-station plate read
perfectly as an image and then, in motion, **mutated its signage text and turned its distant parked
cars into copies of the red hero car**. Nothing in the still predicted that. What predicted it was
that the plate contained two classes of thing a video model cannot leave alone: **small rendered
text**, and **background objects of the same class as the hero**.

**The pass: label every element in the plate.**

| Label | Meaning | What to do |
|---|---|---|
| ✅ **Safe** | it can drift and nobody notices — foliage, sky, road surface, generic texture | leave it |
| ⚠️ **Risky** | it will be re-rendered every frame and may mutate — **any legible text**, logos, faces in the middle ground, repeated geometry, anything in the hero's own object class | either commit to it as a locked element with its own reference, or remove it |
| ⛔ **Unnecessary** | it is not doing narrative or compositional work | **remove it** — it is pure downside |

⚡ The third column is the whole discipline: **a detail that is not earning something is not neutral,
it is a lottery ticket against you.** In a live-action plate an unnecessary background car costs
nothing. In a generated one it is another object the model gets to re-invent 24 times a second, and
the hero car is exactly what it will re-invent it *into*, because the hero car is what the prompt
spent its attention on.

> ⛔ **Test the plate IN MOTION before declaring it finished.** One cheap clip on the plate, before
> it becomes a named location element that forty shots inherit. This is the plate-stage equivalent
> of screening a character sheet on light (`character-and-props.md` §8.3b): the cost of finding it
> here is one clip; the cost of finding it later is every shot built on the location.

**5c. The correction is a smaller visible problem, not a longer list of instructions.**
When a frame keeps failing, the reflex is to add clauses. The corpus's move is the opposite:
**reframe tighter.** A wide frame is a frame with many dependencies — every one of them is a thing
that can go wrong and a thing competing for the model's attention. A tight frame has fewer
dependencies and a more readable action, and it usually says the same story beat.

> **Wide frame = many dependencies. Tight frame = readable action.** Before adding a sixth sentence
> to a failing prompt, ask what the shot would be at half the field of view.

⚠️ **This sits in real tension with the 4K finding** `[SECONDARY · Seedance 2.0 corpus, supplied
2026-09-16]`, which holds that native high resolution is what lets a busy frame hold together. One
says *buy resolution*, the other says *frame the problem out*. Both are observations from working
productions and neither has been tested against the other here. **The honest reading:** resolution
buys detail retention in a frame that is *correctly specified and busy*; tight framing buys you out
of a frame that is *over-specified and failing*. They address different failures, and if you are
reaching for resolution to rescue a shot that keeps coming back wrong, you are probably in the
second case. This is an open question, not a settled rule — logged in `self-evolution.md` for a
test rather than resolved at the desk.

**5d. Neutral grey isolates the product before it becomes a named element.**
Before a product joins a scene it gets the same treatment as a character sheet: **plain neutral
grey, even light, no set.** Not because grey is beautiful, but because every pixel that is not the
product is an attribute the element will carry into every shot that binds it (§8.3c's scope suffix
is the second half of this). Dress the product only after its identity is locked.

## 6. Guiding the eye

Composition decides what the viewer sees, and the eye is not neutral about it (Bruce & Green;
Davies).

- **One focal point.** Davies' rule of emphasis: a frame with two competing subjects has none. This
  is Mahon's dominant-element rule arriving from the fine-art side — when two disciplines converge
  on it, treat it as settled.
- **Value contrast is the primary emphasis tool** (Davies) — brightness difference, before colour,
  before size. If the subject isn't reading, fix value first.
- **Figure–ground must be decided, not left** (Bruce & Green). If subject and background share value
  and saturation, the frame has no subject. Separate with light, depth of field, or value.
- **Grouping is automatic** (Gestalt). Proximity, similarity and continuation group elements whether
  you intended it or not — an accidental line of three bright objects reads as a group and pulls
  focus off the face.
- **Breathing space is active** (Davies). Negative space is a compositional element, not leftover.
  In vertical framing it is also where captions live, so it is a functional reserve (§ typography).
- **Faces are processed configurally, not part-by-part** (Bruce & Green). Small facial-geometry
  errors read as "off" instantly while an equally wrong doorframe goes unnoticed — which is why face
  frames deserve the closest QA attention in the clip.
- **Social meaning comes from very sparse motion cues.** A few points of animate motion are enough
  for viewers to read intent and emotion, so subtly wrong movement reads as a wrong *character*, not
  a wrong animation.

## 7. The Visual Bible — write it once per brand

Everything above becomes tokens in the client profile so it stops being re-decided per video. Full
token list and the governance around it: `brand-system.md`. Minimum:

- Palette: brand hexes, the held grade, saturation/value register, the 60/30/10 assignment, the accent.
- Type: the caption block (`typography-and-captions.md` §8).
- Per character/persona: the verbatim wardrobe block, reference image paths, the identifying detail.
- Environment set: 3–5 approved settings, each with light source, Kelvin, prop list, and the imperfection.
- **Per environment, the practical inventory and the scenario cell**: which fixtures are in that
  room, which are switched on, and which of the four cells it belongs to (day/night × int/ext —
  `craft-cheatsheet.md` §3). Fixing this per *setting* rather than per *video* is what makes every
  clip shot in that room arrive pre-motivated and pre-consistent: contrast bought as a continuity
  budget at the design stage instead of in the grade (`cinematography-craft.md` §6.2).
- Product: the real asset files and the composite method.
- The negative list: what never appears in frame for this brand.
- **The "right kind of wrongness"**: the deliberate break from the category template that makes this
  brand recognisable (`brand-system.md` §7).

**Cross-refs:** `craft-cheatsheet.md` (how to shoot it) · `ai-generation.md` (how to prompt and lock
it) · `typography-and-captions.md` (the text layer) · `brand-system.md` (tokens and drift) ·
`realism-qa.md` (the tells this file prevents) · `persuasion-psychology.md` (why the frame is
arranged this way) · `clients/<brand>.md` §6.
