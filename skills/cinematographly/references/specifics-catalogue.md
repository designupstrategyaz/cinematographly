# The specifics catalogue — dramaturgy, sequences, props, lines and transitions that worked

⛔ **What this file is for, and why it exists.** `move-catalogue.md` holds the specific *camera
moves* that were shot and kept. The owner named six categories worth learning from breakdowns —
**dramaturgy, sequences, prop design, scripting, moves, transitions** — and the move catalogue
covers exactly one of them. This file is the home for the other five.

⚡ **The rule this file exists to enforce on its author: record the SPECIFIC, not the rule derived
from it.** Twice now a supplied corpus has been converted into doctrine (lints, gates, principles)
while the actual fragment that worked — the line, the prop description, the shot chain, the light
that carried a cut — was discarded as an intermediate step. A rule is a formula; you can generate a
hundred of them and none of them will tell a director what to type. **The fragment is the asset.**

**The format.** Every entry describes one specific, in our own words and concretely enough to type
(what it locked, in what order, which number), says what it did, and names where it came from. Until
v2.63.0 the entries were quoted word for word; third-party course and corpus text does not ship, so
they are described instead. If a specific cannot be described that concretely, it belongs in the
reference file that owns the rule, and this file links to it.

⚠️ **Evidence bar, stated.** `[SECONDARY · production corpus]` on every entry. "Worked" means the
author shot it, looked at it, and kept it — nothing here is measured against an outcome.

---

## 0. Provenance, and the honest hole in this file

Every entry below is described in our own words, and the kind of source is named on each entry. No
caption, prompt or transcript passage is reproduced, and no source production's story, characters or
settings are retold: characters are A and B, element names are generic (`@hero`, `@object_sheet`),
settings, objects and actions are given only as generic geometry or categories, and where an example
helps it is our own invention and says so. Short technical tokens (numbers with units, shot sizes,
labels of a few words) are kept as they are.

| Corpus | Source text available? | Specifics described here |
|---|---|---|
| **course notes** — a paid course's scene builds and sheet prompts | ✅ yes | §1–§5 below, in our own words |
| **practitioner production corpus** from the same platform as the course — several multi-part sequences | ⛔ **no — lost to a context compaction** | only what survived into `move-catalogue.md` §1–§25 and `prompting-craft.md` §11b–§11e as fragments |
| **course build with rejected takes** | ⛔ **no — same** | `move-catalogue.md` §1–§13 |
| **Seedance 2.0 4K practitioner corpus** — creature, transformation, product and game-cinematic prompts | ✅ yes | §6–§7 below |

⛔ **This hole is real and it is mine.** Those three corpora were read, converted into rules, and
the specifics were not kept anywhere in the skill — so the rules survive and the specifics do not.
The fix going forward is this file: **a corpus is described here FIRST, in our own words with its
source named on each entry, and doctrine is derived second.** For the three above, the cheapest
recovery is a re-send; they will be mined for specifics, not for principles.

---

## 1. Dramaturgy — the beat structures that worked

`[SECONDARY · course notes and the practitioner corpora listed in §0 · described in our own words]` — the source of every entry below that does not name its own.

### 1.1 The payoff is a LOCATION, not a line

*Provenance: course notes. 10 seconds, four cuts.*

The beat structure, described with two generic characters, A and B:

| Beat | What happens | The mechanism |
|---|---|---|
| 1 | A asks B something harmless | directed as keen interest with a quiet irony under it — someone enjoying the build-up to a small private plan |
| 2 | B answers **suspiciously**, not informatively: she repeats the key word back and asks what he means | directed as curious but guarded, sure there is a trick behind the question — she does not answer the question, she interrogates it |
| 3 | A delivers the turn, offhand: a thrown-away admission | directed as light and dismissive, on an out-breath, deadpan, brushed aside as if it were nothing |
| 4 | ⚡ **No dialogue.** Cut to a POV of what lies ahead: the thing the admission makes a problem, approaching | the audience assembles the joke themselves, a half-second before the characters do |

⚡ **The specific worth stealing: the punchline is delivered by a POV shot of what is coming.**
Nobody explains what the admission means — the geography does. This is why the scene is funny at
10 seconds: the verbal exchange is *entirely setup*, and the payoff costs one shot with no
performance in it at all, which is also the cheapest shot in the scene to generate.

**Breaks when.** The payoff shot is a reaction instead of the consequence. A cut back to B's face
after the admission explains the joke, which is the one thing that kills it. It also breaks if the
consequence appears earlier — it must not be visible during the setup, which is what forces it into
a POV rather than a wide establishing shot.

**The transferable shape:** *innocuous question → suspicious non-answer → the turn, thrown away →
the consequence, shown not said.* The third beat has to be **underplayed**; the course directs it as
a shrug and explicitly asks for restraint.

### 1.2 The rejected read is named FOUR ways, and replaced by a positive state

*Provenance: course notes, iterations one to four of the same shot.*

Iteration one failed because B read as **annoyed** rather than rattled. The correction
does not say "less annoyed". It first asks for a natural, understated, warm and sympathetic read,
then rules the rejected read out with **four separate words for it** — displeasure, annoyance,
irritation, sourness — and extends the ban to both her face and her voice.

Four synonyms for one rejected read — because a single negation leaves most of the space open, and
the model will land somewhere else inside it. Then the positive replacement, as a **physical
state**, not an adjective. The correction specified one item per body channel:

- posture, stated against what supports her body
- shoulder height
- hand grip, and when it tightens
- breathing rate and depth
- gaze, with a **count** of glances away and back
- one discrete involuntary event, counted (once)

And the state is **bounded at both ends**: the nervousness must be plainly present in her body and
breathing, yet held under control, with an explicit upper limit that it **stops short of panic**. ⚡ A
one-sided instruction produces a one-sided overshoot — which is exactly what iteration two did to
A.

### 1.3 Emotion is located anatomically, and the rest of the face is explicitly held still

*Provenance: course notes, the correction to A's read.* What the direction assigned, feature by feature:

| Feature | State specified |
|---|---|
| Mouth | neutral, relaxed, closed; an open smile explicitly forbidden |
| Eyes and brows | carry all of the engagement and the irony |
| Brows | a comic knit of **moderate** strength — visibly pulled together but soft |
| One brow | set a little higher than the other, giving a dry, half-questioning look; the asymmetry graded as **moderate** |
| Outer eye corners | a slight amused crease |

Three specifics in one sentence: (a) the emotion is assigned to **named features**, (b) the features
that must *not* carry it are named and given a state, (c) the asymmetry is given a **degree**
("moderate"), not just a direction. Without (b) the model smiles; a smile is the default reading of
"ironic" and it flattens the whole performance into comedy.

### 1.4 Intensity is a number with a manifest attached

*Provenance: course notes.* The direction rates one physical condition on a performer at **9/10
intensity** and then places it, location by location — **seven named locations** on the body, each
given its own visible form (a sheen, a running line, a gathering at one spot).

The number alone does nothing; the number plus **seven named locations** does. Note the last clause
of the direction, which requires the condition to stay clearly visible through every change of light
— a durability instruction, which is what stops the effect from existing only in the first frame.

For example (ours, not the source's): a cold glass rated 9/10 for condensation, then placed on the
rim, the shoulder, the label edge, a run down one side and a ring at the base.

---

### 1.5 The reaction arrives one shot BEFORE its cause

*Provenance: course notes. Seven shots, six cuts.*

| Shot | What the prompt specified |
|---|---|
| **5** | `@character_b`, framed close, in the middle of a movement; something out of frame catches her attention, she slows, frowns slightly in puzzlement and tilts her head. The prompt states outright that only she is in frame — **the object is not shown** |
| **6** | frontal close-up of `@prop_reveal`, the object she noticed, which reveals something about a character she has just met |
| **7** | `@character_b` again, frontal close-up: she understands |

⚡ **Three shots to land one idea, and the middle one is the object.** The order is
reaction → cause → realization, not cause → reaction. Withholding the object for one shot is what
makes shot 6 a reveal instead of an illustration; the audience leans in during shot 5 specifically
because they were denied.

**Breaks when.** Shot 5 shows any part of the object. The explicit instruction that keeps it out
of frame is doing the work — without it a generator will helpfully include what she is looking at,
because that is the more obvious composition.

### 1.6 The scene ends on an action BEHIND the character

*Provenance: course notes, the same scene.* At that same moment an off-screen event happens behind
her — something fast passing in the background, seen as a blur, with a loud sound cue — and she
spins round toward the noise.

⚡ The last beat is **off her face and in the background**, and she is turned away from camera by the
final frame. The button is an event she reacts to, not an expression she performs — which is why it
cuts hard and why it works on a model that cannot hold a subtle expression for a full second.

### 1.7 The interruption is written as an interruption, from both sides

*Provenance: course notes.* A's line is directed as calm and wry, and written as an unfinished
exclamation that ends in trailing dots and a dash. Then the cut. Then B's direction: she interrupts
him before he can finish the word, speaking between quick breaths.

⚡ The unfinished line is written **with its trailing dots in the dialogue itself**, and the
interruption is *restated as a direction on the other character*. One without the other produces a
pause where the overlap should be: the model will finish his line politely and then start hers.

### 1.8 The silent second IS the dramatic event, and it is choreographed

*Provenance: course notes.* What the direction specified, in order:

1. He explicitly does **not** answer at once: a full second of visible, silent deliberation before he decides.
2. His eyes leave the other character and drift down and to one side.
3. His brows draw in very slightly.
4. One slow, thoughtful blink.
5. A slight shift of the jaw while he weighs it.
6. The decision: his eyes come back **up** and settle on her, a small flicker of resolve, the bemusement giving way to calm confidence with a dry, ironic edge.
7. Only after that does he speak.

Five physical events inside one second of silence: **gaze off → down and aside → brows → blink →
jaw → gaze back up**. ⚡ A pause described as "a pause" is dead air; a pause described as a *route
the eyes travel* is a performance. Note the closing clause, which places the line explicitly after
the decision — it orders the beat against the line rather than leaving the model to choose.

And the sound design carries it: the SFX-only list includes **a brief stretch of near-silence
during his pause**. ⚡ **Silence is specified as a sound cue.** If it is not in the SFX list it will
be scored over.

### 1.9 ⚡ Hide what the model cannot hold

*Provenance: course notes; stated here as a general technique with our own example.*

Identity drift is the dominant failure of a multi-cut sequence. When a returning element is expensive to
hold and is not doing narrative work in that sequence, the strongest fix is to design it **out of
legibility**: give the model a physical reason the element cannot be read, and restate that reason in
the element's definition, in the body of the prompt and in every cut.

Our example: a figure behind a rain-streaked shop window at night. The element definition says the
figure is barely visible behind the glass; the body describes the window as a mirror of the lit street;
each cut restates the reflection and only a faint shape behind it. The concealment is specified as a
**property of the surface with a cause** (bright light on glass), not as an absence, and it is paired
with a positive — the glass shows the street — so the frame is not empty where the face would be.

**The general form:** when a returning element is expensive to hold and is not doing narrative work
in this sequence, **write a physical reason it cannot be seen** — reflection, backlight, silhouette,
depth of field, an occluding foreground — rather than hoping it holds. Compare `move-catalogue.md`
§6 (the doorway silhouette), which does this for a person, and `move-catalogue.md` §31, which does
it for a whole enclosed space.

**Breaks when.** The concealment is written as an absence (*"his face is not visible"*) rather than
as a presence (*"the glass shows a hard reflection of the surroundings"*). An absence gives the model
nothing to render and it will fill the space with a face.

## 2. Sequences — the shot chains that held together

`[SECONDARY · course notes and the practitioner corpora listed in §0 · described in our own words]` — the source of every entry below that does not name its own.

### 2.1 The four-cut enclosed space: inside → inside → outside-through-glass → POV

*Provenance: course notes, one 10-second multi-cut clip.*

| Cut | Camera | Why it is where it is |
|---|---|---|
| 1 | inside the space, **at B's position behind A, facing forward to A** | establishes the geometry from her position, so her shot is already motivated |
| 2 | **reverse onto B** | the reverse, taken from the space cut 1 was shot from |
| 3 | ⚡ **outside the space, frontal, filming A through the glass** | breaks out of the interior and **re-establishes the space in the world** — without this the POV in cut 4 has no ground |
| 4 | **first-person POV**, looking ahead along the direction of travel | the payoff (§1.1) |

How the prompt phrased each camera position, in substance: cut 1 places the camera inside
`@object_sheet` at B's position, looking toward A's; cut 2 simply switches to B; cut 3 cuts to a
frontal angle with the camera outside, filming `@hero` through the glass; cut 4 cuts to the moving
space's own first-person view ahead.

⚡ **The specific: cut 3 leaves the space.** Three interior angles then a POV reads as a jump; going
outside for one beat rebuilds the exterior geography so the POV lands as *this space's view* rather
than as a stock plate.

### 2.2 The physical constant is RESTATED in every cut

*Provenance: course notes, the same clip.* **The same stated speed, as a number with units, appears
in all four cuts.** So does the camera behaviour, near-verbatim each time:

| Cut | Camera behaviour specified |
|---|---|
| 1 | static frame with a handheld feel, camera locked in place, any camera move ruled out, the only motion being the moving space's own vibration at the stated speed, under the stated weather |
| 2 | the same three locks (static, locked position, no move), the only motion being the space's natural shake at the stated speed |
| 4 | the camera travels forward with the space at the stated speed |

⚡ In a multi-cut prompt the model does **not** carry a physical condition across a cut — each cut is
a fresh negotiation. A speed, a weather state, a time of day, a subject in motion: restate it, in
the same words, in every cut. Cheap in characters, and the failure it prevents (a moving subject
that is stationary in one angle) is unfixable in post.

### 2.3 The light event is restated too — and that is what makes four angles read as one moment

*Provenance: course notes, the same clip.*

| Cut | Light specified, from that camera's position |
|---|---|
| 1 | warm sun entering through the openings; bright patches moving over the interior surfaces and A's face as the space travels; soft flares flickering off the glass |
| 2 | sun coming in at the opening behind B; warm shafts travelling over her face; the bright exterior flickering at her back |
| 3 | sun falling on A through the glass; reflections and warm flares travelling over the glass and over his face |

Same sun, same behaviour (*sliding / sweeping / gliding*), described from each camera's position.
⚡ **Continuity of light is what a viewer reads as continuity of time.** Four separately generated
angles agree because the same light event is happening in all of them — not because anything locked
them together technically. This is the cheapest continuity instrument in the file.

---

### 2.4 The shot count is a HARD NUMBER in the technical block

*Provenance: course notes, a seven-shot scene.* The technical block demands exactly seven
shots and exactly six cuts, and rules out both more and fewer, and any added insert. The prompt
body then opens by repeating the count: seven shots, six cuts.

⚡ Three defences in one sentence: the count of shots, the count of cuts (which forbids a wraparound),
and the ban on extra inserts (which forbids the model's favourite move — adding a decorative cutaway that
breaks your continuity because you never specified it). Stated twice, in two places, because the
technical block and the prompt body are read with different weight.

### 2.5 Cut durations are assigned UNEVENLY, in the prompt head

*Provenance: course notes, the fast four-cut sequence (§1.9).* The opening line of the prompt
names the piece and its cut count, **four cuts**, gives the first a quick **3-second** beat, and
sets the other three at **about 4 seconds** each.

⚡ The uneven first beat is the point: a 3-second opener against three 4-second shots reads as
acceleration into the piece. Left unspecified, a model divides the runtime evenly, which is the one
rhythm that never feels authored. Note the approximate figure on the three that do not matter, and
an exact number on the one that does.

### 2.6 One speed change per oner — and it IS the hook

*Provenance: practitioner corpus (Seedance 2.0), a single-take action prompt.*

What the prompt specified: the hook is a near-collision between two moving subjects, held in
**extreme slow motion**, after which normal speed returns. The whole take is a **single uncut
oner**, the camera pursuing the action, and the prompt states that the slow-motion pass is **the
only change of speed** in it.

⚡ In a take with no cuts, the **speed change is the only edit you have**, so it is spent once and
spent on the hook. The same discipline appears in the first-person ride (§7.4) and in both game
cinematics: one sets no slow motion by default and allows a **speed ramp only on two named action
peaks**; the other forbids slow motion entirely and holds **constant full speed**.

### 2.7 One stylized transition per piece; everything else is a hard cut

*Provenance: practitioner corpus (Seedance 2.0), a product spot.*

What the prompt specified, in three places:

- **Style line**: the piece gets exactly one stylised transition, a FILM BURN, between two named sections; every other cut is a hard match-cut on action, sharp and instant.
- **The section itself**, specced in **frames**: the burn at one stated timecode, lasting a stated range of frames, with an abrupt start and end. Physically: a colour, the edge of frame it starts from, how it spreads, the film-material details that show while it burns, and how it ends by burning through into the next section.
- **POSITIVE LOCKS**: every internal cut is a hard match-cut; the burn happens once only, at its stated timecode.

⚡ Stated **three times** — in the style line, in the section itself, and in the locks. A transition
effect is the thing a model will most happily repeat, and a spot with four film burns is a student
film. Note also that the burn is given a **physical description** (its material behaviour, start
and end) rather than a name, because "film burn" alone resolves to an orange flash.

### 2.8 Field of view in DEGREES, per cut

*Provenance: practitioner corpus (Seedance 2.0), a six-cut action prompt.* The OPTICS block, as a table:

| Cut | Size | Horizontal angle | What the cut shows |
|---|---|---|---|
| 1 | ECU | **the narrowest value but one** | macro on one detail |
| 2 | ECU | **narrower than cut 1** | an abrupt, quick zoom in on the same detail as it changes |
| 3 | WS | **a wide value, W°** | slow-motion action, camera low |
| 4 | MS | **a medium value** | handheld, with an artefact on the lens |
| 5 | WS | **W° again** | the main action |
| 6 | EWS | **the widest value** | wide on the whole action |

Shot size **plus** the horizontal angle of view, as a number, for every cut. ⚡ Two things this buys:
the two wides are *the same* number of degrees so they cut together, and the zoom in cut 2 is
legible as a zoom because the number drops from cut 1 to cut 2 — a stated change rather than an
adjective. This is the cleanest answer in any corpus here to "how do I stop shot sizes drifting
between cuts" — give them numbers and reuse them.

⚠️ Degrees, not millimetres. `cinematography-craft.md` §7.1 carries the focal-length row; a
millimetre figure means nothing without a sensor size, and a generator has no sensor.

### 2.9 The whole sequence is bound by one repeated physical LAW

*Provenance: course notes, the fast four-cut sequence (§1.9).*

A boundary rule is stated once globally and then re-asserted inside two of the four cuts:

- **Global**: every moving element, the hero included, stays on its own side of one visible painted boundary line and out of the zones reserved for others, and those zones are stated to be occupied.
- **Cut 1**: the rule is restated, and the prompt states that nothing crosses the line. The hero makes a **single** sideways move, and the prompt specifies it lands **still on its own side** of the boundary.
- **Cut 4**: the hero passes a slower element **while staying wholly on its own side**; the passed element leaves through one side of frame; the hero then returns cleanly to its line; and the boundary stays **in view and is never touched**, out at the far frame edge, for the whole cut.

⚡ This is what "make complex motion readable" actually costs: a rule that is **physically checkable
in the frame** (a painted line nobody crosses), applied to *every* moving element including the
hero, and repeated at each cut where a manoeuvre could break it. Without it, generated movers drift
across the boundary and the shot reads as chaos rather than speed — and no amount of "realistic
motion" fixes it, because that is a vibe and this is a line in the frame.

**The general form:** find the one **visible geometric invariant** of your scene — a painted line,
the horizon, the touchline, the shelf edge — and forbid crossing it, by name, in every cut.

### 2.10 The light is locked three times, and the default is named and refused

*Provenance: course notes, the fast four-cut sequence (§1.9).* What each layer specified:

| Where | Light specified |
|---|---|
| Location reference | a **clock time**; a **sun elevation in degrees**; a **colour temperature in kelvin**, hard and neutral; a **shadow behaviour** (length, and where shadows sit); then an explicit ban on golden hour, sunset warmth and any orange cast |
| Prompt body | the same sun elevation, colour temperature and shadow behaviour, with golden-hour warmth and orange cast both set to zero |
| Every shot | the sun's direction on the hero, stated per shot: high and to the side, cleanly, or from behind as a crisp contre-jour rim |

⚡ Golden hour is the **default a model reaches for** on any reflective hero exterior, so it is
negated by name, twice, and replaced with four positive numbers: a time, a sun elevation, a colour
temperature, and a shadow behaviour. A negation alone ("not golden hour") leaves the whole rest of
the day open.

## 3. Prop design — the objects, as written

`[SECONDARY · course notes and the practitioner corpora listed in §0 · described in our own words]` — the source of every entry below that does not name its own.

### 3.1 A branded object locked by GEOMETRY, not by brand name

*Provenance: course notes.* A close-detail element (`@object_detail`) specifies the detail's
material and finish, a mark given by **colour, shape, point count and position on the object**, what
sits behind it, and the tone of the surrounding space. Its scope suffix restricts it to the detail
and its mark, and it closes on "Reference."

The technical block on the same prompt says **`NON-IP`**. The mark is nonetheless completely
specified — colour, shape, point count, position — because a **geometric description is
not a trademark**. ⚡ This is how a product spot gets a consistent mark in every cut without
naming its owner: describe the mark's shape, count, colour and position, and never its owner.

Applies to any hero object with a logo: a bottle cap, a laptop lid, a jersey crest. Compliance rules
in `compliance.md` still govern whether the resemblance is acceptable — this is a technique for
locking a mark, not a licence to imitate one.

### 3.2 ⚡ The SAME object gets a short sheet or a long one, depending on whether it is the subject

The course writes one object's sheet (`@object_sheet`) two different ways in the same film, and the
difference is not an inconsistency — it tracks what the object is doing in the scene.

**Short form**, used in the dialogue scenes where the object is a location: a colour · a type and
silhouette · one repeated component · one surface treatment; scope suffix limiting it to the
object's appearance.

Four attributes: colour · silhouette · component · surface.

**Long form**, used in the fast sequence where the object IS the shot:

| Attribute | Specified as |
|---|---|
| Finish | a named colour and finish |
| Form | type, part count and outline |
| Front-facing features (two) | each by shape, colour or type |
| Mark | small, described by shape, placed in two named positions |
| Repeated component | finish and pattern |
| Rear-facing features (two) | one by count, one by shape and how it wraps the corners |
| Scope suffix | escalated: an exact design reference, with form, finish, mark and components all required to match |

Eight attributes, every one of them a **feature a camera will be close to** (the front features,
the mark in both positions, the rear features) — plus a scope suffix that has been escalated from a
limit into an **imperative**: the named features must match.

⚠️ **SUPERSEDES IN PLACE** (2026-09-17) — previously: "The object sheet is FOUR attributes, not a
paragraph." That drew a general rule from a single scene type; the fast sequence uses eight
attributes on the same object. The honest finding:

> **Sheet length tracks the closest shot the object will get.** An object seen past the actors in a
> dialogue scene needs four attributes; the same object in an orbiting medium shot pinned on one of
> its features needs that feature described. ⚡ **List the attributes a lens will resolve, and no
> others** — an attribute nobody will see is an attribute a later prompt can contradict for free.

Compare the **character** entries, which are long in both scenes — because a face is resolved at
every shot size, and there is no framing at which it stops being evidence.

### 3.3 The prop designed for the scene that DESTROYS it

One piece of a character's look is built at sheet time as **an explicitly fake, removable prop**,
because a scene forty shots later takes it off. The course gives the reason inside the sheet itself,
as a design instruction: the piece is to be made obviously false and detachable, since a later scene
removes it.

⚡ The specific is the *timing*: the second state was designed before the first state was approved.
⚠️ Only this one instruction from that sheet was captured — the full sheet prompt is among
the text lost per §0, so the geometry of the "removable" design (how the join was described) is not
recorded. Doctrine in `character-and-props.md` §8.3d.

### 3.4 The scope suffix, as it appears on every element

*Provenance: course notes.* Every element ends in a scope clause followed by the word
"Reference." on its own. The forms used, as templates:

- `— character appearance only. Reference.` (people)
- `— object appearance only. Reference.` (objects)
- `— <object> reference, interior detail only. Reference.` (a close detail and its mark)
- `— location and mood reference. Reference.` (locations)

Note that the word **"Reference."** terminates every entry as its own sentence, after the scope
clause. Doctrine in `character-and-props.md` §8.3c.

---

### 3.5 Invented brands are how you get LEGIBLE TEXT under NON-IP

*Provenance: course notes, a character sheet with a branded costume.*

What the sheet specified for the costume: fictional branding only, every mark invented and
**spelled out in quotes**, each one placed:

| Mark | Text | Placement |
|---|---|---|
| Main wordmark | one invented name, in quotes | two named positions on the garment |
| Secondary marks | four invented names, each in quotes | each given a named position |
| Number | a two-digit number, in quotes | one named position |

It then closes with a blanket refusal: every logo and every letter is an original invention, and no
real brand, organisation or existing logo may appear.

⚡ A branded costume (a uniform, a sports kit) with no branding reads as fancy dress; with real
branding it is unusable. The move is to **invent the brands and spell them**, because a named, quoted string is the only way to
get stable text out of a generator (`prompting-craft.md` on verbatim words + a hold). Four secondary
names, one wordmark, one number, each **placed** at a named position on the garment, then the
blanket refusal.

This also supplies the continuity: the same six strings are what make costume shots cut together.
`compliance.md` still governs whether an invented mark resembles a real one too closely.

### 3.6 The location sheet locks geography STRUCTURE BY STRUCTURE

*Provenance: course notes.* What `@loc_wide` specified:

| Part | Specified as |
|---|---|
| Viewpoint | the kind of district, and the height of the vantage point |
| Ground plane | its width and layout, divided by **one visible painted boundary line** |
| Left of frame | two structures, each given a material, a colour and a surface pattern |
| Mid-frame | two more, specified the same way |
| Closing the view | a fifth structure, given by colour |
| Edges and sky | the state of the ground plane's edges and their planting; the sky and cloud; the shadow quality |
| Scope suffix | architecture and layout only |

⚡ Five structures, each with **a material, a colour and a position in frame**, and a named object
that closes the view. That is a *map*, not a mood — which is what lets four cuts at different
angles read as one place. Note the boundary line is introduced here, in the location, before any
shot uses it (§2.9).

⚠️ The scope suffix on this one is unusually long because it carries the light too: after the
architecture-and-layout scope it continues straight into the lighting instruction (§2.10).
A location reference generated at a different hour is still usable if the suffix overrides its
light — which is cheaper than regenerating the plate.

### 3.7 Negative space written INTO the location reference

*Provenance: course notes, a scene with a stationary hero object — after the motion test showed
similar background objects cloning into the hero (`production-design.md` §5b).*

What `@loc_exterior` specified: the edges of the space **completely EMPTY**, with no object like the
hero at rest anywhere in view, and only the occasional one passing **in motion**; scope suffix
limiting it to the environment seen from inside the hero, plus lighting and colour mood.

⚡ The fix for a mutating background element is not a suppression term in the shot — it is an
**absence written into the reference definition**, so every shot that binds the location inherits it.
Note the replacement clause: similar objects *in motion* are allowed, because a moving one in the
deep background is cheap and a stationary one invites a duplicate of the hero.

### 3.8 A still used as a POSITION lock

*Provenance: course notes, the same scene.* What `@image_1` specified: an elevated wide shot
establishing the same location; the hero object **on its own** at its spot, seen from a rear
three-quarter angle and pointing toward a named feature of the location; the space around it empty,
nothing like it anywhere. Its suffix turns it into an **exact lock on where the object stands and
which way it faces**, and states that it stays exactly so for the whole scene.

⚡ A reference that carries **where a thing is**, not what it looks like. The object sheet says what
the object is; this says where it stands and which way it points, for a whole scene of coverage shot
from inside it. Without it, an inside angle can imply the object facing the other way, and the light
through its openings will fight the exterior.

This is the second job a generated still can do (`move-catalogue.md` §27 is the first: pulling
agreeing frames from one motion source). **Name the frame for its job** — the course's own advice,
in substance: label the position still as the blocking frame and the close-detail still as the
detail-continuity frame, and never keep an unlabelled pile of screenshots.

### 3.9 The scope suffix escalated into an IMPERATIVE

*Provenance: course notes.* `@object_detail_2` repeats the description of `@object_detail`
(§3.1) unchanged, but its suffix becomes a **detail lock**: it orders that this exact detail and its
surround be used in every shot in which the detail can be seen, and it still closes on
"Reference."

Compare §3.4's suffix form (`interior detail only`), which **limits** what the element supplies.
This one **compels** its use, and scopes the compulsion to a condition (only the shots where the
detail is in view). ⚡ Two different jobs, and the course needed both: the limit stops the reference
leaking its background into the shot; the imperative stops the shot ignoring the reference. A
sub-reference created *because* a detail was drifting (§3.1 lineage) needs the second form.

### 3.10 A prop reference that carries a CONTINUITY ASSERTION about another element

*Provenance: course notes, the same scene as §1.5.* What `@prop_reveal` specified: an object that
depicts a person, described by appearance, pose and expression; **other similar objects placed on
either side of it**. The suffix marks it as a prop reference and asserts that **the person depicted
has another character's face**, with named parts of that character's current look removed.

⚡ The definition states a relationship to a *different* element. It is the entire reveal of the
scene (§1.5) compressed into a reference line, and it means the assertion travels with the prop
rather than living in whichever shot happens to reveal it. Note the similar neighbours on either
side — the prop is given neighbours so it reads as one of many, which is what makes the character
noticing it a discovery rather than a signpost.

### 3.11 Background life is CAST, not described as "background life"

*Provenance: course notes, a busy interior.* What the prompt cast in the background: a count of
**3–4 people**, each busy with their own affairs, and **three separate pieces of business**, each a
named action — framed as lively, natural activity filling the wide.

For example (ours, not the source's), in a library: two people whispering over one open book, one
person reshelving, one asleep at a desk.

Three specific pieces of business with a count on them. ⚡ "A busy room" produces either an empty
room or a crowd; three named actions produce a room. **The same rule now covers animals, vehicles and vessels**
(`world-design.md` §4): each is cast in the world card with a species, a count, a behaviour, a heading, a speed
and the shots it carries into, and anything uncast is refused by the prompt lint. The same technique appears in the fast
sequence as a foreground layer: a thick, defocused foreground of named passing elements, each one
listed, all streaking past as heavy motion blur.

## 4. Scripting — the lines, and what changed about them

`[SECONDARY · course notes and the practitioner corpora listed in §0 · described in our own words]` — the source of every entry below that does not name its own.

### 4.1 The exchange, as shot

- **A** asks B a harmless question.
- **B** echoes its key word back as a question, holds a beat, then asks a one-word question of her own.
- **A** answers with the offhand turn.

Nine words of dialogue carrying a complete setup-and-turn. B's line is **not an answer**
— it is the question repeated back, which is what buys the beat.

### 4.2 The beat is written as STAGE BUSINESS between the two halves, not as an ellipsis

The direction splits her line in two. The echoed word is drawn out slowly, as if she is testing it
and cross-examining him; then comes a short pause in which **her eyes stay narrowed and keep reading
his face**; then the second word arrives fast and light.

⚡ An ellipsis produces a pause of unpredictable length. A described *action* inside the pause
produces a pause the length of that action — and gives the model something to animate, so the beat
reads as thinking rather than as latency.

### 4.3 Line length is a function of the character's BREATH

The iteration-four correction cut B's reply from three words to two.

— because the same pass changed her physical state: pressed back, out of breath, mildly
shocked. ⚡ **A breathless character cannot say a four-word line.** When you change a performer's
physical state, re-check every line they have; a line written for the old state will be delivered
in the old state.

This is the one dependency that makes a performance note and a line rewrite **one variable rather
than two** (`refinement-loop.md` §1b, and `prompt_lint.py --against` implements it).

### 4.4 Delivery is written as rhythm + subtext + a simile

A's delivery note asks for a quick, clipped, slightly rushed reading; underneath it, genuine
eagerness to hear her answer; on top, a flat face with a dry, mischievous undercurrent; and it closes
on a **simile that names what he is about to do**.

Three layers: **tempo** (quick, clipped, a little rushed), **surface vs subtext** (a straight face
over private mischief), and a **simile that names the intention**. The simile is doing real work —
it tells the model what the character *wants*, which neither the tempo nor the subtext does. For
example (ours, not the source's): "like someone hiding a gift behind their back".

### 4.5 A second delivery note on the same line, for the physical state

Her note keeps the suspicious-but-curious colour from the previous beat and adds that **her breathing
is still slightly ragged from the physical condition of the scene**.

The environmental condition is carried into the *voice*, not just the body. A line delivered in
fast motion and the same line delivered at rest are different takes, and saying so costs a handful
of words.

---

### 4.6 ⚡ The "one change" sheet edit — the correction loop, as a PROMPT structure

*Provenance: course notes; stated here as a general technique with our own example.*

A sheet edit that changes one thing works when the prompt brackets the change with preservation. Our
example: an approved character sheet, edited to remove a pair of glasses. The prompt lists what must stay
identical (face structure, each feature, skin, hair), announces **one** alteration, states the result
both ways (no glasses, no frame marks on the nose, the eyes unobstructed) and closes by restating that
everything else matches the reference.

Four moves in one paragraph, in this order:

1. **Enumerate what is preserved** — named features, not "his face".
2. **Announce the delta and its count** — one alteration, and it says so.
3. **State the change positively AND negatively** — the positive end state, each variant named as
   absent, and the resulting surface at each location, because a single positive word leaves the
   partial versions open.
4. **Re-assert the preservation after the change** — the rest of the face is declared unchanged.

For example (ours, not the source's), removing a pair of glasses: "no glasses, no frames, no lens
reflections, no marks on the bridge of the nose; every other feature matches the reference".

⚡ This is `refinement-loop.md` §1b written as a prompt rather than as a note. Step 4 is the one
people drop, and it is the one that stops the model treating the named change as licence to
renegotiate the face around it.

The same shape drives a second edit on the same sheet. The face must match image_1's close-up panel
exactly (1:1); **only one feature is allowed to change**: one element is removed so the surface under
it is bare, and **one existing element is kept but intensified a little**, then immediately capped
by two named refusals of overshoot.

Note the "a little more" instruction bounded at once by the two refusals — §1.2's two-sided bound
applied to a prop rather than to a performance.

### 4.7 The face-swap preservation manifest

The swap prompt opens by **declaring Image 1 the untouchable base** and itemising it: the
composition, the framing angle, the pose, the wardrobe, the backdrop with its out-of-focus detail,
two effects elements in the air, and the lighting. It ends that list with **the head as the sole
permitted edit**.

Seven named things preserved before the change is named. ⚡ A bare "leave it as it is" is not a
manifest — the list is, and the list is what a later dispute is settled against.

### 4.8 A swap must inherit the plate's OPTICS, not just its geometry

The next paragraph has the incoming face adapt to the plate's conditions: the plate's camera angle,
the head angle the pose needs, a re-specified expression, and the plate's own light, glints and haze
on the skin. It then **names the optical match explicitly — Image 1's light direction, grade, grain
and sharpness — so the seam where the neck meets the wardrobe disappears**.

⚡ Four optical properties named explicitly — **lighting direction, colour grade, grain, sharpness** —
plus the seam that must survive (where the neck meets the wardrobe). This is the compositing half
of `real-and-ai.md` §3: an identity pass that matches the face and not the film stock produces a head
that is obviously newer than the shot it sits in.

Note also that the *performance* is re-specified for the new face — it does not inherit the
expression, it is told to make it, feature by feature (mouth, teeth, eyes).

### 4.9 The micro-beat cascade for a realization

The prompt writes her moment of recognition as a short chain: a small visible start, **eyes opening
wider, brows going up, lips parting for a moment, a quick intake of breath, a stunned blink** as she
works out what she has just seen. Then the surprise is told to **ease** into an almost
invisible smile — **the mouth corners rising by about a millimetre** — a hint of knowing, and it
explicitly stops there.

Five events, then a named transition (the surprise easing), then a sixth event with a **measurement
on it** (a millimetre) and an upper limit (nothing beyond that). ⚡ A realization is a two-state beat —
surprise, then what the surprise resolves into — and writing only the first state produces a face
stuck in a gasp for two seconds.

### 4.10 Delivery bounded by three refusals

B's urgent line is directed as spoken between short breaths, quietly and with restraint —
courteous, controlled urgency, out of breath but gentle — and then **three refusals: not
authoritative, not theatrical, no lifted volume**. The line itself is three short fragments ending
on a double dot.

Three refusals against the model's default reading of an urgent line. ⚡ Urgency reads as volume
unless you say it does not — and the line itself is written in **three short fragments with a
trailing double-dot**, which is the punctuation doing the same work the direction does.

### 4.11 The technical block carries PERFORMANCE MECHANICS, not just format

The film's technical block ends with four standing orders: **lip-sync must be accurate on every line;
every character blinks naturally and irregularly in every shot; facial reactions fire on the same
frame as the physical action that causes them; and when two characters look at each other, each
gaze lands precisely on the other's eyes.**

Four standing instructions, in the block that every shot inherits, each aimed at a **known generator
failure**: dead lip-sync, the unblinking stare, the reaction that arrives a beat after its cause, and
the eyeline that lands past the other actor's shoulder. ⚡ These are cheap, they are the same in every
dialogue film, and they belong in the block rather than in a shot — a per-shot version fails at the
shot that forgets (§3.4's argument, applied to performance).

An earlier scene's block carries a fifth: a demand for very fine micro-expression detail in
the faces.

## 5. Transitions — how one shot handed to the next

`[SECONDARY · course notes and the practitioner corpora listed in §0 · described in our own words]` — the source of every entry below that does not name its own.

### 5.1 The eyeline handoff into a POV

Cut 3 (§2.1) ends with A's gaze settling calmly back onto what lies ahead. Cut 4 is that view.
⚡ The POV is **motivated by the last thing the previous shot does** — the eyeline is written into
the outgoing shot specifically so the incoming shot is read as his view. Without it, cut 4 is a
stock plate; with it, cut 4 is his POV, and the payoff lands on him.

**Two more transitions live elsewhere, one home per named thing.** ⚡ **The same light carrying the
cut** is §2.3 above — the sun sliding / sweeping / gliding across three different cameras is the
transition device, with no effect, no dissolve and no match-cut. **The bridge shot** (and why it
must not show the destination) is `move-catalogue.md` §26.

---

## 6. Video-to-video — the transformation prompts, as written

*Provenance: practitioner corpus (Seedance 2.0).*

### 6.1 ⚡ The INPUT LOCK — two closed lists, preserved and added

The prompt opens with an `INPUT LOCK` header stating that <<<video_1>>> is matched 100% and that
**the whole source clip stays as it is**. It then lists what that means, object by object — each
object in frame by name, down to the smallest items and a reflection in a dark surface — then the
room itself, its light, the grade, and the exact camera move. **Four operations are banned by name —
re-grading, re-timing, smoothing and re-framing — and a closed list of allowed additions follows**:
the added element, the light it gives off and throws, its contact shadows, the residue it leaves
behind, and a small physical give in the object it touches.

Two enumerated lists and nothing between them: **nine preserved items** (named down to the smallest
object and a reflection) and **five permitted additions**. Plus four named operations that are
forbidden outright — *re-grade, re-time, smooth, re-frame* — which are exactly the four things a v2v
model does silently and which destroy the match.

⚡ The additions list is the part people omit, and it is what makes the result composite rather than
pasted: the added element is allowed to **emit light, cast contact shadows, leave a residue, and make
the object it touches react**. An addition with none of those is a decal. See `real-and-ai.md` §3b — this is the
generated seam, handled at the prompt.

And the anti-decal instruction is stated as a definition: the surface the addition passes through
is declared physical and membrane-like, explicitly not a flat sticker. The membrane is then given
physics throughout — stretching around whatever pushes through it, and elsewhere bulging outward.

### 6.2 A transformation is an ORDERED ASSEMBLY anchored on a real feature of the plate

Several different transformations were run on **one** source clip. All of them begin at the same
place: a distinctive feature already visible on the subject.

- **Variant one.** The anchor feature changes first, with a faint glow. The surface then opens in
  stages, **section by section**, folding back. Components seat **individually**, each with its own
  small visible event. Hard plates unfold along the subject **plate by plate**. The effect reaches
  the extremity and encases it **one segment after another**, and the anchor re-forms as part of the
  new material.
- **Variant two.** Again the anchor first: thin glowing cracks open along it and then spread outward
  through the surface.
- **Variant three.** A gradual build from the anchor: it shimmers and goes see-through, and then the
  surrounding surface turns glass-like and bends the light.

⚡ **The anchor is a feature that already exists in the footage**, so the effect has a believable
origin and a believable path (from the anchor outward to the extremity, segment by segment). The
first prompt says "one at a time" or an equivalent four times: an effect described as a state
arrives as a cut; an effect described as an **ordered sequence of seatings** arrives as an animation.

Each variant also ends with the same two guarantees: the rest of the subject and the setting are
left as they were, and **the subject's face and identity do not change**.

### 6.3 The SFX list is the transformation's timeline

Variant one's sound line is effects-only and follows the build event by event: a quiet tone that
rises, one small sound per opening seam, one per seating component, one per locking segment,
**ending on a sustained resonant tone**; under it all, the plate's own room tone.

The sound list is in the **same order as the assembly**, and it names the arrival (the tone settling
into a steady note). Compare variant two — opening sounds, a deep rumble, small discrete pops, then
a swell at the extremity — the same route, anchor to extremity, in sound. ⚡ Writing the SFX in event
order is a free second pass on whether the visual sequence is actually ordered.

---

## 7. The structured-block format — Seedance 2.0, as written

`[SECONDARY · practitioner corpus (Seedance 2.0, §0) · described in our own words]` — the source of every entry below that does not name its own.

### 7.1 The named blocks, in the order the corpus uses them

`STYLE` · `LIGHTING` · `COLOR` · `CAMERA` · `MATERIAL` · `ACTING` · `PHYSICS` ·
`CHARACTER DESIGN` · `CONTINUITY` · `TECHNICAL` · `AUDIO` · `SCENE CONTEXT` · `FORMAT MODE` ·
`OPTICS` · `ACTION` · `POSITIVE LOCKS`

Three of these have no equivalent in this skill's own block set and are worth stealing:

- **`MATERIAL`** — in one prompt it asks for realism at the level of surfaces: each surface named
  with its wetness, texture or sheen, how the medium around the subject refracts and breaks up, and
  droplets that stick to and run down the lens. Surfaces as their own block, separate from lighting.
- **`FORMAT MODE`** — one prompt declares six cuts with no timecodes; another declares timed
  multishot with hard cuts on action. The **editorial contract**, stated before any shot.
- **`POSITIVE LOCKS`** — see §7.2.

### 7.2 ⚡ POSITIVE LOCKS — the constraints restated as things that ARE true

The closing `POSITIVE LOCKS` block asserts that each subject and the setting are **identical in
every cut**; that the detail shown in CUT 1 **is the same detail** that changes and is pushed into in
CUT 2; that the action **remains on one named plane** for the whole film — four movements relative to
that plane are permitted by name, and the subjects **at no point** leave it upward; and that one
named colour leads the palette, with the main subject **as** the saturated one.

A closing block that repeats, as assertions, everything the shot must not get wrong. ⚡ Note the shape
of the hardest one: **the positive is stated first and at length, and the negative rides on the end**
— the action stays on its plane, four allowed behaviours are listed, **and only then** comes the
ban on leaving it. Four permitted behaviours are enumerated so that the refusal has somewhere to
send the model.

The same construction appears in a game cinematic — a subject's size is given as a ratio to a
person's height, and then the oversized wrong answer is refused by name — a ratio to a human, then
the wrong answer named.

### 7.3 Colour as a 60:30:10 split with the accent assigned to an object

The `COLOR` line in one prompt splits the palette **60:30:10**: two named hues as the 60% base;
three as the 30% secondary; and one contrasting hue as the 10% accent, **tied to one named object in
the frame**.

⚡ The accent is given a **source object**. A 10% accent with no home spreads across the frame as a
tint; an accent that lives on a named object is a light in the world. `production-design.md` §3 owns
the palette system — this is the prompt-side notation for it.

### 7.4 The speed ramp is written with timecodes AND frame rates AND its sound

The ramp is laid out in four segments, each given its own timecode range:

| Segment | Picture | Rate |
|---|---|---|
| 1 | fast first-person movement at real speed | **the base rate, stated** |
| 2 | the impact: the camera jolts slightly, and time slows almost to a stop | — |
| 3 | macro shot, almost frozen | **a high rate, stated as a number** |
| 4 | an instant ramp back up to normal speed | **the base rate again** |

The audio follows the same clock: at the impact **a sharp intake of breath**; through the slow
section the ambient rush falls away into a muffled near-silence and is replaced by a low rhythmic
pulse and a heartbeat; normal time returns with a whoosh.

⚡ **The slow-motion is defined by what you hear.** Ambient rush → vacuum → pulse and heartbeat →
whoosh. A ramp that only exists in the picture reads as a stutter; the audio is what tells the
viewer it was a choice. Note the camera's own reaction — the small jolt at the impact — which gives
the ramp a cause, and the `CAMERA` block's standing note that the camera is never static.

### 7.5 The HUD as a pinned screen-space layer, with a hex value

The `HUD LAYER` instruction tells the model to reproduce @image_1's HUD precisely: a flat 2D interface in screen space, in **one colour given as a hex value**, sharp vector icons, partly see-through panels.
**The layer is pinned in every shot; numbers are allowed to change, the layout is not.** It then
gives nine named interface elements, each pinned to a named screen position (top centre, top right,
down the right edge, bottom centre, just below centre, and so on).

⚡ Letting the values move while freezing the layout is the whole trick — it grants the one kind of
change that makes a HUD look live and forbids the kind that makes it look generated. The hex value
is what makes it the same colour in every cut. Recorded as a move in `move-catalogue.md` §25; the
specifics are here.

The second game variant adds live values with ranges: each gauge is given a screen corner and the
**range its number may move within**.

### 7.6 "Style reference, not a keyframe"

In one game prompt's `CONSTRAINTS`, image1 is declared **a style reference rather than a first
frame**, and the model is told to reproduce its listed contents, interface, lighting and palette in
motion. The other game prompt does the same under `LOCATION`, marking @image_1 as a style reference
and telling the model to **build the world out beyond it** while the subject moves through the space.

⚡ One clause that distinguishes *"start here"* from *"look like this"*. Without it a supplied image
is treated as frame one and the shot spends its first second escaping the still.

### 7.7 The render look refused by name

One style line asks for a high-resolution, cinematic, photoreal look, then **rules out a 3D-render
look, a game-engine look and a cutscene look**, and names what to imitate instead: **practical,
physically built effects**. The surface is specified **down to the pores**, layer by layer —
wetness, translucency, what shows beneath it, how it catches the light. Physics: real weight,
gravity and momentum, proper contact shadows, **nothing hovering**.

Three refusals, then a **positive tradition to imitate** (practical effects), then the two tells
that decide it: surface at pore level, and contact shadows with no floating. ⚡ Refusing a look
without naming the one to replace it leaves the model where it started.

⚠️ And the inverse, from the game cinematics, where the CG look is the goal: the style asks for
hyperreal images that are **clearly rendered by a game engine, and rules out live action and film**.
The same instruction, pointed the other way — which is the evidence that it is the *naming* that
works, not the direction.

### 7.8 A montage asks for coverage in the style line

The animated montage's style line describes a multi-shot 3D feature-film montage and **forbids
staying on a single angle or in a single cut**.

⚡ A default generator answer to a multi-beat prompt is one long take from one angle. The refusal goes
in the style line, where it governs everything. The shots then each carry their own size and their
own line: Shot 2, for instance, is a **close-up** with one piece of business, one reaction and one
whispered line.

### 7.9 The 4K claim, in our own summary

The corpus claims that crowded wide shots with many moving elements were where 720p and 1080p used to
break down — objects morphing partway through the shot or locking into rigid poses — and that at
native 4K this failure largely goes away, because the higher resolution leaves the model enough room
to keep detail stable across a busy frame rather than blurring it.

⚠️ Filed here because it is one half of an **unresolved tension** — the course holds
that a failing busy frame is corrected by framing tighter, not by buying pixels. Recorded as an open
question with a proposed study (`assets/creative-benchmarks.json`
→ `_the_resolution_vs_framing_question`, `lab-00003`) and discussed at `production-design.md` §5c.
⛔ Do not quietly apply one of these and forget the other.

---

## 9. From a production job — measured

*Provenance: a close-out note of 2026-09-19 from one production job, an 8-second checkpoint shot for a
product brand. One episode — these are specifics with an
outcome, not rules.*

### 9.1 ⚡ Ambient particulate words on a low camera become the SHOT

The prompt added a texture note: an ambient particulate word, rising behind the moving camera. On a
low dolly the model (MiniMax S3a v1, the 0.8–2.5 s window) turned that into a 1.7 s plunge through a
particulate cloud that covered the lower frame entirely, and the client rejected it.

A texture note at eye level is atmosphere; the same words with the lens a foot off the ground put
the particulate **between the camera and everything else**, and the model follows it in. Any
airborne particulate — grains, droplets, vapour, smoke: on a low camera it is foreground, and
foreground is the subject.

### 9.2 Name the ONE coloured element, or they all take the colour

The defect: the design called for a single accent-coloured line among several similar graphic lines,
and the accent colour leaked onto the neighbouring lines. The fix: name the one line that carries the
colour and say only that one does.

A colour attached to a *family* of shapes spreads to the family. The fix is the word *only* and the
one member named — the same exclusivity construction as §7.2's positive locks.

### 9.3 ⚡ Author the motion as an EDIT, then re-generate it

The client approved the camera move in take v1 and the background in take v2. The studio built a
split composite: v1 for the lower part of the frame, v2 for the upper part, joined by a soft
horizontal seam at 67 % of frame height with a 3 % feather. After a second round of notes, v2's upper
half was frozen on a still frame until v1's dolly finished (frame 86), and the horizon drift in v1 (75 px at full resolution) was removed with a uniform zoom centred on the horizon (at most 1.105×). That
composite went to MiniMax as `video_references`, with the approved end-frame plate as
`image_references`, and the first generation produced the take that was kept (1 of 2).

When two takes each got half of it right, **cut the two halves together yourself** — crude seam,
still frames, a stabilising zoom — and hand that to the model as a *motion* reference with the
approved plate as the *picture* reference. The composite does not need to be good; it needs to
carry the timing and the move. It is the director's cut of the motion, in the model's own language.
Proposed for `motion-design.md` §2.3; one success is not yet doctrine.

### 9.4 One mover at a time

The client's note asked that no background structure or graphic element move, and that neither the
camera nor the ground drop, until the camera had finished travelling to its end position. The studio
turned that into a rule: only one thing moves at once — the set stays still during the camera's
travel, and the camera has come to rest before anything in the set starts moving.

Compare the move catalogue's §30, where the *subject* swerves and the camera never breaks its glide:
the same idea from the other side. A frame where the camera and the world both move has no fixed
point, and the viewer reads it as instability rather than as either motion.

### 9.5 An effect was cut for what it SAYS, not how it looks

A visual effect behind the product was dropped and replaced by a rising glow from a hidden light
source — light, not the effect. Two reasons were recorded: that effect next to that product implied
a hazard the ad did not intend, and it had never been part of the approved concept.

Two reasons, and both are worth keeping: a **category connotation** (the effect next to the product
read as a safety claim the ad did not mean to make) and **scope** (it was never approved). The
replacement keeps the visual job — warmth, a swell — in a form with no connotation: light.

## 10. Five AI short films, measured end to end

`[measured 2026-09-30 · film_breakdown.py · 1,122 shots across 3,459 s]` — five AI short films
(2026), named in this file only by code: **F1–F5**. All 24 fps; three in 2.35:1 scope. Every shot is
a row in `assets/reference-shots.jsonl` — query it with `film_db.py`. Only numbers and categories are
recorded here; what happens in the films is not.

⚠️ **Read §10.7 before citing any of this.** Five films by four teams is a sample, not a law — and
the measuring tool was corrected three times while producing these numbers, twice reversing a
finding.

📖 **§10 is what the pixels gave up. §11 is what had to be looked at** — light and performance in
every shot, read off the contact sheets and reported by `film_db.py facets`.

### 10.1 The cutting rate: a median shot of 2.0–3.4 seconds

`[measured 2026-09-30 · film_breakdown.py · 1,122 shots]`

| Film | Runtime | Shots | Median | Longest reliable |
|---|---|---|---|---|
| F2 | 612 s | 236 | 2.04 s | 12.5 s |
| F3 | 678 s | 248 | 2.08 s | 23.5 s |
| F1 | 559 s | 169 | 2.46 s | 15.2 s |
| F5 | 711 s | 250 | 2.69 s | 8.4 s |
| F4 | 899 s | 219 | 3.42 s | 18.3 s |

⚠️ **SUPERSEDES IN PLACE** (2026-09-30) — previously the "longest reliable" column read F2
**15.2 s**, F1 **32.3 s**, F5 **23.5 s**. All three were wrong in the way the column existed to
prevent. F2's and F1's are shots `film_breakdown.py` had flagged `split_suspect` — and
`film_db.py build` **dropped the flag**, so they reached this table as reliable. Read at
IN/MID/OUT, F1's 32.3 s `#159` opens in one setting and ends in another: at least two shots. F5's
23.5 s is a credit, not a scene. `[measured 2026-09-30 · film_db.py · split_suspect restored on 90
rows]`

⚡ **A ten-minute AI short is 170–250 shots** — call it one shot every 2 to 3.5 seconds. That is the
production number to quote, and it is far above what "a short film" sounds like.

⛔ **Shot counts here are a LOWER BOUND.** 8–30 shots per film still split further when the detector
is made more sensitive, so they are flagged `split_suspect` in the database and excluded from the
"longest" column. An earlier version of this section claimed that every film holds at least one
shot past 20 s, so the 5–10 s clip habit is a tooling limit rather than a storytelling one. That
claim came from a 44.5-second "shot" in F4 which, looked at frame by frame, was **five shots in
three different locations**. The claim is withdrawn: §10.7.

### 10.2 ⚡ They open SLOW and end SLOWER — the fast cutting is in the middle

`[measured 2026-09-30 · film_breakdown.py · first 30 s and last 60 s vs each film's own mean]`

Five of five open slower than they run; five of five end slower — **on the mean**. F1's opening
runs **1.15×** its own mean shot, F2's **1.15×**; their closings run **2.6× and 2.9×**.

⚠️ **SUPERSEDES IN PLACE** (2026-09-30) — previously: "F1's opening runs 1.7× its own mean shot,
F2's 1.8×; their closings run 3–5×. **Not one of these films opens on a fast cut.**" Those ratios
were measured at 997 shots, before the re-split in §10.7 cut every long "shot" into its real parts
and before the 30-shot sponsor tail was identified. Re-measured `[measured 2026-09-30 · film_db.py ·
film shots only]`, the direction survives on the **mean** in all five films but the magnitudes
shrink by a third to a half — and on the **median** it does not survive at all: F1 (0.89×) and F2
(0.94×) open *faster* than they run, and F5 ends faster (0.95×). The mean is carried by exactly the
long shots the detector under-splits, so read this section as *the last minute holds its longest
shots*, not as *every film opens slow*. §12.3 has the fuller curve. ⚠️ F1's 2.6× closing is carried
by `#159`, the 32.3 s "shot" that is at least two; with the flagged shots out it is **1.56×** on the
mean and **1.93×** on the median.

⛔ **This is the opposite of the short-form hook reflex, and the scope is the reason.**
`hook-craft.md` is about a scroll in the first two seconds; a short film has a seated audience
and spends its opening buying belief in a world. Do not carry the number into an ad. Do carry the
shape: **pace is a curve, not a setting**, and these films slow down exactly where the viewer is
deciding whether to enter and how to leave.

### 10.3 About half of every film is a locked-off camera

`[measured 2026-09-30 · film_breakdown.py · 767 reliably-solved shots of 1,122]`

Locked off is the largest class in four of the five films (F2 78, F4 87, F5 85, F1 74 shots);
drift — movement under the threshold — is the next. ⚡ **Roughly six shots in ten carry no
deliberate camera move at all.** The exception is F3, the one action-led film: handheld 65, locked
off 34.

⚠️ **SUPERSEDES IN PLACE** (2026-10-24) — previously: "F4 86, F5 82 … handheld 60". The
camera-move words were re-derived from the stored solves after two `film_breakdown.py` defects were
fixed (§10.7): a zoom or a roll about the frame centre had leaked into a spurious pan and tilt, and
once it was removed 23 shots filed as deliberate moves had no move above threshold at all.
`[measured 2026-10-24 · the author's lab scripts (not shipped) over BREAKDOWN-*.json]`

This is the most useful corrective in the file for how this skill writes prompts. The move catalogue
runs to 33 named moves; these films mostly **hold the frame and let the performance move**, and the
two most static films are the two most emotionally legible.

⚠️ **A corrective, not a default.** Six in ten held means four in ten moved. Applied as a rule to every
shot, this section produced a 97 % locked camera across 20 skill-written ads
(`[measured 2026-10-03 · lab-00005 · metrics.py]`; the figures are in `cinematography-craft.md` §3.8).
Plan the mix per sequence (`sequence-grammar.md` §2b).

### 10.4 Hard cuts carry the films; dissolves are a dialect

`[measured 2026-09-30 · film_breakdown.py · 1,117 classified boundaries]`

| Film | cut | dissolve | fade |
|---|---|---|---|
| F4 | 200 | 9 | 9 |
| F2 | 197 | 29 | 9 |
| F5 | 208 | 30 | 11 |
| F1 | 141 | 12 | 15 |
| F3 | 141 | **98** | 8 |

⚡ **Four of five cut hard 85–92 % of the time.** The fifth — F3, the action-led film — dissolves on
39 % of its boundaries, which is a genre choice, not a house style. Fades are rare everywhere
(5–9 %) and in F1 they do structural work: it has the most fades and the fewest hard cuts, because
its structure keeps returning to one recurring setting.

### 10.5 ⚡ Speech coverage is the clearest signature of a film's architecture

`[measured 2026-09-30 · film_breakdown.py + faster-whisper · share of shots carrying speech]`

| Film | Shots with speech | What that buys |
|---|---|---|
| F1 | **62 %** | a dialogue-led film — faces answering each other |
| F4 | 32 % | narration over images, speech clustered in the framing scenes |
| F5 | 16 % | sparse — speech marks the turns, images carry the rest |
| F3 | 7 % | action-led; the events are physical |
| F2 | **0 %** | ⚡ **no intelligible speech at all.** Ten minutes, 236 shots, music and image only |

⚡ **This is the number to decide FIRST**, because it prices the film. A 62 %-speech film is a
lip-sync and voice pipeline; a 0 %-speech film needs none of that and spends the budget on pictures.
⛔ And it is not a quality axis: F2 and F1 sit at opposite ends and both were selected by the same
jury. ⚠️ Speech is stored in the database as a COUNT — the lines themselves are not kept; they are
someone else's script.

### 10.6 Two structural answers to the consistency problem, read off the frames

`[measured 2026-09-30 · film_breakdown.py · sequence sheets and IN/MID/OUT strips]`

- **F1 — one recurring setting as a frame.** A single setting under flat, even light, MS/MCU, eye
  level, locked off — intercut with one-off inserts in many different genres and settings. ⚡ **The
  frame setting carries all the continuity and costs almost nothing to hold; the inserts carry the
  variety and need no continuity because each appears once.** A production architecture, not a
  style.
- **F4 — one face, held.** A single protagonist across the film in CU/MCU, muted naturalistic
  palette, the highest locked-off share and the longest median shot of the five. Its structure
  alternates two registers: **cool shots (short, locked, connective)** and **warm shots (longer,
  developing camera)**, with narration linking one to the next. Its opening two shots are a lesson
  on their own: **shot 1** is a near-top-down aerial with the credits held over it; **shot 2**
  travels WS → MS → MCU in 8.4 seconds, so one shot delivers the place, the scale and the
  protagonist's face.

Both work. Between them they bracket the choice: **spend your consistency budget on one room, or on
one face.**

### 10.7 ⛔ What to distrust in §10 — including two findings that reversed

`[measured 2026-09-30 · film_breakdown.py · gates, failure rates and three corrections]`

- ⛔ **Every pan and tilt the tool named before 2026-10-24 was backwards, and half of them were not
  pans.** `film_breakdown.py` named the PICTURE's shift as the camera's move — a known pan right read
  *"pan left 22 %W"*, a tilt down *"tilt up"* — and took the shift at the frame's top-left corner, so
  a pure x1.15 push-in about the centre was filed as *"push in x1.15 + pan left 8 %W + tilt up 7 %H"*.
  Both are fixed and pinned by selftests on synthetic pans, tilts and a centred push-in; the 174 rows
  of `reference-shots.jsonl` that named a pan or tilt were re-derived from the stored numbers (174
  re-worded; deliberate-move classes 175 → 152). `[measured 2026-10-24 · synthetic crops]`

- ⛔ **A 44.5-second "shot" was five shots.** The scene detector's default threshold misses soft and
  low-contrast cuts. Raising the sensitivity took the five films from 997 shots to **1,122**, cut
  every median, and destroyed the long-shot claim §10.1 used to make. 8–30 shots per film still
  split at a lower threshold again — so the counts above are a floor, and the tool now flags
  `split_suspect` rather than reporting a long shot in silence.
- ⛔ **The first motion run produced the OPPOSITE of §10.3's companion finding** — subject motion at
  three times the camera's. That run fitted optical flow between frames **seconds apart**, which the
  method does not support, and had no inlier test, so it reported *"tilt down 288 %H, roll −105.9°"*
  and a static test pattern moving ten frame-widths per second. ⚡ **A motion number with no inlier
  test is not a measurement** — and it was confident, plausible, and wrong in the direction of the
  doctrine it was about to confirm.
- **32 % of shots are still not solved** for camera move. They read UNRELIABLE, never zero. Every
  percentage in §10.3 is a share of the solved 767.
- **The size column is empty.** This OpenCV build ships no face cascade, so the shot sizes named in
  §10.6 were read off contact sheets by eye, not measured.
  ⚠️ **SUPERSEDES IN PLACE** (2026-09-30) — previously this bullet ended: "so the shot sizes named
  in §10.6 were read off contact sheets by eye, not measured." That is still true of *how* the sizes
  were obtained, but they are no longer only in §10.6: **every one of the 1,122 rows now carries a
  size, an angle, a light and a performance line**, read the same way. `§11` reports them and
  `§11.7` states what a by-eye reading is worth.
- **Trailing packaging** (a ~5.3 s card and a ~1.5 s sting) is excluded from §10.1–§10.2.
- **F2's transcript is a hallucination.** With voice-activity filtering off, the transcriber
  emitted Russian subtitle-credit boilerplate over music — a known failure on non-speech. The
  correct reading is *no speech*, and the database stores zero segments for it rather than the
  invented text.

## 11. The same five films, READ — light and performance in every shot

`[measured 2026-09-30 · film_db.py facets · 1,092 film shots; 30 sponsor/promo shots excluded]` —
§10 is what a machine could measure off the pixels. §11 is what had to be **looked at**: all 1,122
rows now carry a shot size, a camera angle, a one-line lighting description and a one-line note on
what the performer actually does. The numbers below come out of `film_db.py facets`, whose buckets
are ordered keyword rules printed with every result — change a rule and every figure here has to be
re-derived.

⚠️ **Read §11.7 before citing any of this.** The readings are one pass of one pair of eyes over
contact sheets, not a measurement.

### 11.1 ⚡ Eye level is not a choice in these films — it is the default

`[measured 2026-09-30 · film_db.py facets]`

| Angle | Shots | Share |
|---|---|---|
| eye | 988 | 90.5 % |
| low | 55 | 5.0 % |
| high | 48 | 4.4 % |
| aerial | 1 | 0.1 % |

Nine shots in ten are at eye height. Put that next to §10.3 — about **42 % of every film is a
locked-off camera** — and the house style of the whole cohort is one sentence: *the camera stands
still, at the height of a person's head, and lets the scene happen in front of it.* The low and high
angles are not spread evenly either; they cluster on inserts (hands, objects, floors) and on the
two shots per film that are meant to feel wrong.

⚡ **Eye level is the baseline height; the camera's behaviour is planned per sequence, not
defaulted.** In 1,092 shots there is exactly **one** aerial, and nine in ten are at eye height — but
only about four in ten are locked off, so "locked off" was never this cohort's default.

⚠️ **SUPERSEDES IN PLACE** (2026-10-04) — previously: "Write `eye level, locked off` as the default
line in a shot spec and spend the exceptions deliberately." The eye-level half is what the cohort
measured. The locked-off half overstated §10.3, which measured locked-off at about 42 %, and as an
instruction it contributed to the 97 % frozen camera in lab-00005 (`cinematography-craft.md` §3.8).

### 11.2 A third of every film is a face, and the establishing wide is rare

`[measured 2026-09-30 · film_db.py facets]`

| Size | Shots | Share |
|---|---|---|
| MS | 380 | 34.8 % |
| WS | 263 | 24.1 % |
| MCU | 248 | 22.7 % |
| CU | 97 | 8.9 % |
| insert | 50 | 4.6 % |
| EWS | 27 | 2.5 % |
| XCU | 15 | 1.4 % |
| MWS | 12 | 1.1 % |

MCU + CU + XCU = **360 shots, 33.0 %**. The extreme wide — the shot people reach for first when
asked to "establish" — is **2.5 %**, and more than half of those are CG environment plates in F2
and F3.

⚡ **Budget a third of the shot list for faces before you budget anything for scale.** These films
spend their length on people's expressions, not on how big the world is.

### 11.3 ⚡ Nearly half of all shots are keyed by a light you can see in the frame

`[measured 2026-09-30 · film_db.py facets]`

**501 of 1,092 shots (45.9 %)** name a practical as the key — a window, a lamp, a screen, a
headlight, a neon sign, a candle, a beacon. Per film:

| Film | Keyed by a source in the scene |
|---|---|
| F3 | 65.3 % |
| F5 | 61.7 % |
| F2 | 53.9 % |
| F4 | 25.7 % |
| F1 | 8.1 % |

And the commonest quality across all five is **soft, 388 shots (35.5 %)**, ahead of
hard/directional (242, 22.2 %) and flat/even (175, 16.0 %).

⚡ **Name the source, not the mood.** "Warm cinematic lighting" is what the default output already
looks like; "*a single bedside lamp, warm, everything past two feet falls to black*" is a shot. Both
films that read hardest as photographed rather than generated — F5 and F3 — are the two that put a
nameable source in nearly two thirds of their frames.

### 11.4 ⚡ The screen-as-only-key, used at the same story beat in two different films

Three shots, two films, one idea — a character receives information, and the only light on their
face comes from the source delivering it:

- `F1#131` (5.4 s), and `F1#136`, which holds the same uplight for the reaction.
- `F5#148` (2.0 s).

All are **MCU, eye level, uplight, cold white, everything else black**. Neither film cuts away to
the screen and back for the beat itself; the screen is off-frame or in the foreground and the
information arrives on the face.
`[measured 2026-09-30 · film_db.py card · the shots' read fields in assets/reference-shots.jsonl]`

⚡ **When a character receives news from an object, make the object the key light.** It removes the
need for a reaction cut and it dates the shot to the moment, not the scene.

### 11.5 Colour is a chapter marker, not a grade

`[measured 2026-09-30 · film_db.py facets]`

| Film | warm | cool | neutral | saturated |
|---|---|---|---|---|
| F5 | 70.2 % | 21.0 % | 5.6 % | 0.8 % |
| F2 | 60.9 % | 31.3 % | 4.3 % | 1.7 % |
| F3 | 50.6 % | 17.2 % | 7.5 % | 10.9 % |
| F4 | 23.8 % | 45.8 % | 30.4 % | — |
| F1 | 5.0 % | 40.4 % | 44.7 % | 3.1 % |

The splits are not house styles, they are structure:

- **F4** runs cool for its connective register, warm for the other, and spends its last act in flat
  **neutral** daylight. The grade tells you which world you are in before anybody speaks.
- **F2** is cold teal for its recurring settings and warm window light from `F2#54` onward in one
  setting. Its warmest run — `F2#145`–`F2#175` — is its intimate two-performer stretch (§12.4 T6).
- **F3** carries the only real **saturated** share (10.9 %): magenta and cyan accents. At its tone
  break (`F3#213`) the colour drains and the last thirty shots are flat grey.

⚡ **Assign the palette to the chapter, then stay inside it.** In all five films the colour changes
at a story boundary and nowhere else.

### 11.6 ⚡ Stillness is a performance choice, and it is measurable

`[measured 2026-09-30 · film_db.py facets]`

| Film | performer holds still | nobody in frame | performer acts |
|---|---|---|---|
| F4 | 22.0 % | 16.4 % | 61.7 % |
| F1 | 17.4 % | 10.6 % | 72.0 % |
| F2 | 9.1 % | 21.3 % | 69.6 % |
| F5 | 7.3 % | 8.5 % | 84.3 % |
| F3 | 2.5 % | 14.6 % | 82.8 % |

Across all five, **120 shots (11.0 %) are a performer deliberately not moving**, and **157 (14.4 %)
have no performer at all** — one shot in seven is an object, a room or a landscape.

F4 sets the dial highest and spends it: its performance setup and payoff (§14.2, `F4#11` →
`F4#205`) is a held face that finally moves. F3's 2.5 % is a film in constant motion. The number is
a dial, and these directors set it per film.

⚡ **Write the stillness down.** "Stands still, gaze held off-camera, no blink beat" is a direction;
leaving the performance field empty is how you get a model's default idle fidget in every shot.

### 11.6a Two ensemble structures worth stealing outright

`[measured 2026-09-30 · film_db.py card · rows in assets/reference-shots.jsonl]`

- **One performer, a ring of separate reaction singles.** `F5#116`–`F5#124`: the performer is cut
  against five *individually framed* listeners (`#119`, `#120`, `#121` among them), each 1.8–3.0 s,
  each eye level, each soft-keyed. No group wide carries the emotion; the one wide of the room
  (`#123`) is used once, to close it.
- **One identical wide, repeated, as the voice of an institution.** `F2#107`, `#109`, `#116`,
  `#118`, `#121`: the same locked-off group shot, flat shadowless light, performers motionless,
  intercut five times with singles of one other performer. Nothing in the frame changes between
  the repeats, and the repetition *is* the characterisation.

### 11.7 ⛔ What to distrust in §11

- ⛔ **These are readings, not measurements.** Every size, angle, light and performance line was
  written by eye from 1,500-px contact sheets at 25 frames to a sheet. A face at the back of a wide
  is a judgement call; so is "soft" versus "flat".
- ⛔ **The buckets are keyword rules, and the order decides the answer.** `facets` prints its rule
  order with every result for exactly this reason. 32 shots (2.9 %) fall through to `other`.
- **Only the first frame of each shot was read.** A shot that starts wide and pushes to an MCU is
  filed by where it starts; the move is in the measured `move` field, not in the size.
- **30 shots across the five files are sponsor and festival packaging** — a promo card, a product
  demo and an unrelated clip. They are tagged `NOT A FILM SHOT` in the `vfx` field and `facets`
  drops them by default. Any figure quoted from `stats` (which does not drop them) will be a few
  tenths off the figures here.
- **F5's longest hold is a credit.** Its 23.5 s "shot" is a credit card, not a scene. §10.1's
  "longest reliable" column does not distinguish them; §11 does.
- ⛔ **Do not hand the angle or size read to a machine.** On the ShotBench benchmark (NeurIPS 2025)
  GPT-4o named the camera angle correctly **58.2 %** of the time and the shot size **69.3 %**, and
  took a medium shot for a medium close-up **36.2 %** of the time; the best model averaged under 60 %
  across all eight dimensions, so both reads are unreliable, not uniquely so `[PRIMARY* · Liu et al., arXiv:2506.21356, fetch-tool summary · checked 2026-09-30]`. These
  reads were made by eye, but by a model's eye; the MS/MCU boundary in the tables above is the one to
  doubt first. Camera height can be checked without judgement: the horizon sits at lens height
  (`sequence-grammar.md` §3.4).

## 12. How the pieces combine — sequences, and the interactions that hold in every film

`[measured 2026-09-30 · film_db.py seq / run / cross · 1,092 film shots read IN ORDER]` — §10
measured shots and §11 read them, but both are censuses: they count what a shot looks like and
cannot see an **assembly**. A montage, a threshold and a repeated-frame sequence all dissolve into
the same per-shot averages. §12 reads the rows in order and asks what follows what, and which
categories move together. Everything here is re-derivable: `seq` prints chapters, cadence and runs;
`run` prints any range as a shot-by-shot skeleton; `cross A:B` prints a contingency table with lift.

⚠️ **Read §12.5 first.** One interaction that looked like the strongest finding in the cohort
exists in none of the five films. ⛔ **Replicate the shape, never the content** — the lengths, sizes,
light and order are craft; these films' settings, characters and compositions are theirs
(`compliance.md`).

### 12.1 ⚡ The interactions — nine hold in every film, four have one exception, three are false

`[measured 2026-09-30 · film_db.py cross · each lift re-computed inside every film, not only pooled]`

Lift is how much more often B turns up with A than across the whole film: 2.0 is twice as likely,
0.5 half. A pooled lift is **not** reported here unless it points the same way inside each film
that has enough shots to test it.

**Hold in every film tested — use these as rules:**

| When the shot is… | …it is | Lift, film by film |
|---|---|---|
| a CU | soft-lit | 1.3 – 4.3 (5/5) |
| a WS | flat/even-lit | 1.6 – 3.1 (5/5) |
| an MCU | soft-lit | 1.0 – 1.9 (5/5; F1 level — its faces are lit flat and shadowless) |
| a WS | often empty of performers | 1.6 – 2.5 (5/5) |
| an MCU | **never** empty | 0.0 – 0.1 (5/5) |
| low-angle | an MS | 1.6 – 2.4 (4/4) |
| speaking | longer than 5 s | 1.2 – 3.4 (4/4; F2 has no speech) |
| speaking | **never** 1.2 s or shorter | 0.0 – 0.4 (4/4) |
| keyed by a practical | **never** neutral-coloured | 0.0 – 0.4 (5/5) |

Read together they are one grammar: **light gets softer as the frame gets tighter; the wide
carries the world and the close carries the person; a line of dialogue needs time; and neutral
light is daylight nobody is holding.**

**Hold with one named exception — use with the exception in mind:**

- A high angle is an **insert** — 9.7 to 17.2 in three films, a hand or an object seen from above.
  **F2 is the exception**: its high angles are CG establishing plates.
- An insert is lit by a **single source** — 1.7 to 7.3 in three films; **F4 is the exception**,
  whose inserts share the same even light as everything else in it.
- A CU is **short** (1.2 s or less) — 1.4 to 2.5 in four films; **F1 is the exception**.
- A practical key is **warm** — 1.0 to 2.1 in four films; **F1 is the exception**, whose
  practicals are cold screens.

**False — pooled, they look like findings; inside the films they are not:**

- ⛔ **A dissolve marks a change of world.** Pooled across 1,092 shots the lift is **1.6** and it
  was the strongest interaction in the table. Inside the films it is 0.2 (F2), 0.9 (F1), 1.1 (F5),
  1.3 (F3), 1.7 (F4, on two shots). It is a **Simpson's paradox**: F3 alone carries 95 of the 167
  dissolves *and* a palette that changes colour every few shots, so pooling manufactures a link that
  no director in the set used. In F4, **29 of its 32 palette changes happen on a hard cut.**
- An insert is short — 2 of 4 films.
- A low-key shot is short — 2 of 3 films.

### 12.2 A chapter is a run of one palette, and the palette changes at a story boundary

`[measured 2026-09-30 · film_db.py seq · a chapter = 6+ consecutive shots in one colour bucket]`

F4 is the clearest worked example — eleven chapters, and the grade tells you which world you are in
before anyone speaks:

| Shots | Length | Palette | Median shot | Note |
|---|---|---|---|---|
| #1–8 | 44 s | cool | 5.3 s | |
| #12–19 | 37 s | cool | 3.9 s | speech in every shot |
| #29–52 | 154 s | **warm** | 4.9 s | |
| #53–61 | 26 s | cool | 2.4 s | |
| #63–82 | 72 s | cool | 2.8 s | |
| #91–97 | 63 s | **warm** | 10.4 s | the slowest chapter |
| #103–109, #113–123 | 65 s | cool | 2.4 – 4.0 s | |
| #126–146 | 59 s | cool | 2.0 s | |
| **#147–200** | **175 s** | **neutral** | 2.9 s | **the longest chapter** |
| #204–213 | 49 s | neutral | 4.5 s | |

Chapters detected per film: F4 11, F5 13, F2 15, F1 9, F3 **3** — and that last number is a limit
of the detector, not a finding: F3's palette churns between warm, saturated and "other" every few
shots, so the colour-run rule cannot see its chapters.

⚡ **Plan chapters as palettes before you plan shots.** Each chapter in these films is one colour
family held for 6–54 shots, and the film's thesis gets the longest one.

### 12.3 Cadence is a curve, and each film draws a different one

`[measured 2026-09-30 · film_db.py seq · median shot length in each fifth of the film's shots]`

| Film | 1st | 2nd | 3rd | 4th | 5th | Shape |
|---|---|---|---|---|---|---|
| F2 | 1.2 | 1.6 | 1.8 | 2.8 | 2.8 | fastest open in the set, then decelerates steadily |
| F4 | 4.2 | 2.8 | 3.5 | 3.5 | 2.4 | slow open, quickens, holds, quickens again |
| F5 | 3.0 | 2.4 | 2.4 | 2.8 | 2.5 | almost flat — the pace never becomes the event |
| F1 | 2.9 | 2.2 | 3.2 | 1.8 | 2.5 | alternates fifth by fifth |
| F3 | 2.0 | 2.6 | 1.9 | 1.7 | **3.4** | accelerates, then halves at the tone break (§12.4 T5) |

Put this next to §10.2 as corrected: the **last minute** of every film holds its longest shots, but
the last **fifth** is not uniformly slow — F4, F5 and F1 end their final fifth *faster* than their
first. The slowing is a final-minute event, not an act-length one.

⚡ **Draw the cadence curve on the shotlist before choosing lengths.** F2 and F3 have almost
identical medians (2.06 s and 2.12 s) and opposite shapes; the median is not the pace.

### 12.4 ⚡ Seven sequence templates, measured

`[measured 2026-09-30 · film_db.py run · each range printable as a shot-by-shot skeleton]`

Each is a **shape** — lengths, sizes, light families, transitions and the order they come in. Print
any of them with `film_db.py run <range>` and build your own subject into the skeleton.

**T1 · The threshold** — `F4#26-31`, `#54-60`, `#101-105`, `#138-149`; `F1#13-17`

Five to twelve shots, 13–32 s, in this order, read off the five ranges listed above:

1. **The threshold, empty** — WS or insert, nobody in frame (`F4#26`, `#54`, `#138`).
2. **The performers facing it, held still** — MWS (`#55`).
3. **The next world's light arrives before anyone crosses** — silhouette, backlight or a hard
   contrast across the frame (`#29`, `#145`). This is the step that sells it.
4. **The crossing** — low-angle legs and feet (`#146`, `#59`). 13 of the cohort's 35 low-angle MS
   shots are feet and legs like these.
5. **The new world**, in its own palette — and the first shot in it is often the longest of the
   sequence (`#31`, **18.3 s**).

⚡ **Let the new light into the old room one shot before the cut.** The palette change then reads
as arrival, not as a jump — and the cut itself can stay hard.

**T2 · The reaction ring** — `F5#112-125`

14 shots, 47.2 s, median 2.85 s — **all 14 hard cuts, no speech in any of the 14, 13 of 14 warm**. Its
longest shot is a *witness* shot (`#115`, 8.4 s), and it comes before a single listener has been
shown. (`#114`, 7.1 s, is flagged `split_suspect` and may be two shots.) Then the performer (MS, CU)
alternates with **separately framed listeners**, one per shot, 1.5–3.5 s each. The only wide of the
listening room (`#123`) closes it.

⚡ **Give each witness their own frame.** A group wide shares the reaction out; a ring of singles
makes every face a separate event.

⚠️ **SUPERSEDES IN PLACE** (2026-09-30) — previously: "all 14 hard cuts, all 14 silent". The
database measures SPEECH (`has_speech`, words from the transcript), not sound: "silent" claimed a
quiet soundtrack that nobody measured. What was measured is that nobody speaks. Music and effects
under these shots are unknown.

**T3 · The montage** — 11 runs in four films · `F2#26-50`, `F5#46-53`, `F3#10-19`

`[measured · 11 runs of 4+ shots at 1.2 s or less · 64 shots]` — **nobody speaks in any of the 64.**
Two kinds, and they are framed differently:

- **Process montage** — hands on a task, mostly CU and insert (`F5#46-53` 5 of 8 tight;
  `F3#10-14` 4 of 5). F5 runs its process at **0.3–0.5 s a shot on dissolves** (time
  compressed); F2 runs its at **0.6–2.1 s on mostly hard cuts** (21 of 25 — mechanical repetition).
- **Action montage** — bodies in motion, MS and WS (`F1#143-151` 2 of 9 tight; `F2#89-92` 0 of 4).

⚠️ **SUPERSEDES IN PLACE** (2026-09-30) — previously: "every one of the 64 is silent." The field is
speech, not sound. In Hollywood practice a run like this is usually carried by a bed rather than sync
dialogue: Cutting (2019) finds sequences defined partly by shared sound coverage — music, voiceover
or pervasive sound (`sequence-grammar.md` §5) — and "silent" read as the opposite claim. These runs
have **no sync speech**; whether a bed carries them was not measured.

Two structural details repeat: F3 **brackets its fast inserts with two long holds** (6.2 s and
6.1 s), and F2's 25-shot run **breathes twice** — `#28` (2.1 s) and `#39` (1.5 s) — in a run whose
median is 0.92 s.

⚡ **Drop the dialogue for the montage and put a held beat inside it.**

**T4 · Institution against individual** — `F2#107-121`

One locked-off group MS repeated **five times, identically** (`#107`, `#109`, `#116`, `#118`,
`#121`), **all five shadowless**, intercut with one performer's singles, **all soft**. The light
family separates the power from the person *inside one sequence* — the §12.1 rule that faces are
soft, used as a statement.

⚡ **Light the institution shadowless and the person soft, and repeat the institution's frame
without changing it.**

**T5 · The tone break, on four channels at once** — `F3#205-230`

26 shots, 113.5 s. Every variable turns together:

| Channel | Before the break | At the break |
|---|---|---|
| Cadence | film median 2.12 s | **4.25 s — 2.0× slower** (excluding the one flagged shot) |
| Palette | warm, saturated magenta and cyan | **neutral, all of the last 13 shots** |
| Light | hard, practical, neon | **flat** |
| Speech | 6 speaking shots in the 185 before it (#20–204) | **5 speaking shots in these 26** |

Its last shot holds **10.4 s** (`#230`), the longest unflagged shot since `#80`.

⚡ **Break the tone on every channel in the same cut.** Change the palette alone and it reads as a
grade; change all four and it reads as the truth arriving.

**T6 · The intimacy hold — every variable constant except the faces** — `F2#144-175`

32 shots, 104 s, median **3.04 s — 1.5× the film's 2.06 s** (excluding the one flagged shot). **32 of 32 hard cuts, 30 warm, 28 soft,
19 MCU or CU.** Nothing in the image changes but the two performers.

⚡ **When the scene is two faces, freeze everything else** — one colour, one light, one transition
type, one pace.

**T7 · The bookend and the bracket**

- **Three of five films return to an image from their opening**: F4 (`#7` → `#214`), F5 (`#7` →
  `#173`), F1 (`#2` → the first half of `#159`).
- F1's ending is a **0.4–0.9 s montage** (`#144`–`#151`) between two long holds — `#126`, and the
  return to its opening image (`#159`). ⛔ **Both holds are flagged `split_suspect`**, and `#159` is
  confirmed as at least two shots (two different setups), so their lengths are not quoted here; the
  order is.

⚡ **End on the film's opening image, changed.**

### 12.5 ⛔ What to distrust in §12

`[measured 2026-09-30 · film_db.py cross · per-film re-check of every pooled lift]`

- ⛔ **A pooled interaction is not a finding until it holds inside the films.** The strongest pooled
  lift in the table (§12.1, dissolve × world change) exists in none of them. Every rule above was
  re-checked film by film; any new one must be.
- **Everything in §11.7 applies** — sizes, lights and performances were read by eye off one frame
  per shot.
- **The thresholds are choices.** A montage is 4+ shots at 1.2 s or less, a chapter is 6+ shots in
  one colour bucket, a sustained run is 3+ shots of 5 s or more. `seq` prints them with every
  result; move one and the counts move.
- **The seven templates were found by reading, then measured** — not discovered by the tool. The
  tool confirms their shape; it did not pick them, and there are certainly others in these films.
- **Chapter detection fails on a churning palette** — F3's 3 chapters understate its structure.

## 13. Performance and timing — every performer shot read at IN, MID and OUT

`[measured 2026-09-30 · film_db.py · 934 performer shots, three frames each at 15 / 50 / 85 % of the shot]`
— §11's acting column was one line read off one frame, and a performance lives in how a shot
*changes*, which one frame cannot show. Every shot with a performer in it was re-read as a three-frame
strip and coded on a codebook fixed before the read: `expr` (one word from a closed list),
`intensity` (0 blank · 1 restrained, only the eyes or mouth carry it · 2 open, the face moves ·
3 peak, full release) and `turn` (what changes inside the shot, and whether it lands early, late or
continuously). `film_db.py card` now prints all three, and writes a late turn into the MOTION block as
*hold, then change*.

⚠️ **Read §13.8 first.** One reader, three frames a shot. It sees a turn; it cannot time one to the
frame.

### 13.1 These films are not expressive in the stage sense

`[measured 2026-09-30 · film_db.py · codebook counts]`

| Film | Blank (0) | Restrained (1) | Open (2) | Peak (3) | Modal |
|---|---|---|---|---|---|
| F1 | 5.6 % | 57.6 % | 33.3 % | 3.5 % | 1 |
| F4 | 28.1 % | 50.6 % | 16.3 % | 5.1 % | 1 |
| F3 | 29.4 % | 46.6 % | 22.5 % | 1.5 % | 1 |
| F5 | 12.8 % | 78.0 % | 8.8 % | 0.4 % | 1 |
| F2 | 47.0 % | 36.5 % | 16.6 % | 0.0 % | 0 |

**18 of 934 performer shots (1.9 %) are a full release.** The working register in four films is
*restrained* — only the eyes or the mouth carry the feeling. F2 goes further: nearly half its
performer shots are **blank**, and its open feeling is concentrated in one stretch (§11.5, §12.4 T6).

⚡ **Default the performance to intensity 1 and spend 2 and 3 as punctuation.** A generated face that
emotes in every shot reads as the model, not the character.

### 13.2 ⚡ The expression is in the change, not in the size of it

`[measured 2026-09-30 · film_db.py · split_suspect shots excluded]`

| Film | Shots that change inside the shot | early | late | continuous |
|---|---|---|---|---|
| F4 | 41 % | 9 | 21 | 42 |
| F1 | 46 % | 5 | 27 | 32 |
| F5 | 53 % | 3 | 27 | 83 |
| F2 | 53 % | 0 | 22 | 68 |
| F3 | 55 % | 0 | 15 | 86 |

**Around half of every film's performer shots end in a different state from the one they start in.**
That is where these films put their expressiveness: not in how big a face gets, but in the fact that
it moves from one thing to another while the camera watches.

### 13.3 ⚡ Put the change late — in all five films, late beats early

`[measured 2026-09-30 · film_db.py · turn timing]`

When a feeling changes inside a shot, it changes in the **second half** — 21 against 9, 27 against 5,
27 against 3, 22 against 0, 15 against 0. The head of the shot establishes the state; the tail
breaks it; the cut lands on the new state. Examples to print with `film_db.py card`, with their
codebook values: `F4#116` (4.0 s, grief, 3), `F4#120` (grief, 2), `F5#172` (resolve, 2), `F1#19`
(joy, 2), `F2#168` (tender, 1).

⚡ **Write a turn as hold-then-change.** `card` now does this: for a late turn the MID line reads *the
state holds*, and the change goes on the END line. A prompt that asks for the change "during" the
shot gets it in the middle, where these films almost never put it.

### 13.4 ⚡ Hold the change, not the peak

`[measured 2026-09-30 · film_db.py · median shot length, split_suspect excluded]`

A shot with a turn in it runs **1.15× to 1.89× longer** than a shot without one, in all five films
(F5 1.15 · F2 1.32 · F4 1.64 · F3 1.68 · F1 1.89). A change needs time to be seen changing.

The obvious rule — *hold the big emotion longer* — does **not** hold: intensity-2 shots run longer than
intensity-1 shots in two films and shorter in three.

⚡ **Give the time to the turn.** A face that is already crying can cut fast; a face that is about to
needs the room.

### 13.5 Big emotion goes tight — in every film

`[measured 2026-09-30 · film_db.py · share of intensity 2–3 shots in MCU / CU / XCU]`

| Film | High-intensity shots in face sizes | All performer shots in face sizes |
|---|---|---|
| F5 | 95 % | 43 % |
| F2 | 70 % | 46 % |
| F3 | 70 % | 31 % |
| F4 | 61 % | 34 % |
| F1 | 50 % | 35 % |

The exceptions are bodies, not faces: in F4 and F1 the high-intensity shots outside face sizes are
whole-body joy and fear, played full-length.

### 13.5a ⚡ At the peak, either the body carries it or the frame is tight

`[measured 2026-09-30 · film_db.py query --intensity 3 · all 18 peak shots, each read]`

Of the **18** shots coded 3 (full release), **12 carry the peak in the body or in touch** — contact
or whole-body action (an embrace, a grab, a reach, a run), among them `F4#73` (a WS), `F4#213` and
`F3#212` (an MS). The other **6 are face-only, and all 6 are MCU or CU** (`F1#29`, `#45`; `F3#125`;
`F4#116`, `#118`; `F5#148`). No shot in the five films plays a peak on the face alone in a frame
wider than MCU.

⚡ **Choose the channel with the frame.** A peak in a medium or wide shot is written as a body action
with contact; a peak on the face is written for an MCU or closer. `acting-for-the-model.md` §3 turns
this into the card's BODY line.

### 13.6 ⚡ The strongest performance is not at the climax

`[measured 2026-09-30 · film_db.py · rolling five-shot mean intensity; film_db.py structure]`

| Film | Most intense five-shot run | Climax beat | Climax played at |
|---|---|---|---|
| F4 | 19 % | 87 % | no performer |
| F1 | 28 % | 91 % | 2 |
| F5 | 36 % | 74 % | 0 |
| F2 | 61 % | 79 % | 1 |
| F3 | 80 % | 77 % | 2 |

**In four of five films the most intense run of performance comes before the climax.** **No climax
is played at intensity 3.** And in all five, the intensity after the climax is **equal to or higher
than** anything in the stretch before it: the action lands, then the release comes (`F4#213` at
98 %, `F3#212` at 81 %).

⚡ **Spend the big performance early to buy belief; play the climax as an action; let the release
come after it.**

### 13.7 A turn vocabulary — one change, one feature

`[measured 2026-09-30 · film_db.py card]`

Eight turns kept as models — `F3#125`, `F2#190`, `F5#117`, `F1#116`, `F4#208`, `F3#238`, `F5#121`,
`F4#75` — one at intensity 3, four at 2, three at 1. Each names **one** change, carried by **one**
feature — the eyes, the mouth, the hands. Write it in that form, in your own subject's terms: a
starting state, the one feature that moves, the state it ends in (for example *the gaze drops and
stays down*). That is the unit a generation model can deliver in one shot. Two changes in one line
is two shots.

### 13.8 ⛔ What to distrust in §13

`[measured 2026-09-30 · film_db.py lint · split_suspect restored on 90 rows]`

- ⛔ **Three frames per shot see that a change happened, not when to the frame.** "Late" means the
  change is visible between the 50 % and 85 % frames.
- ⛔ **Reading at IN/MID/OUT corrected the one-frame read of §11 in several rows** — `F2#220` had been
  filed with an action the three-frame strip contradicts. The corrected lines are in the database;
  the §11 counts are unaffected because the size, angle and light fields were not changed.
- **A shot whose IN, MID and OUT show different setups is a missed cut or a move**, and the database
  now says so in its `notes` — 18 such rows were found in the read, among them the 32.3 s `F1#159`,
  confirmed as at least two shots. The detector's `split_suspect` flag had caught it; `film_db.py build`
  had been dropping the flag. It is carried now, and a selftest pins it.
- **Intensity is one reader's scale**, fixed before the read and applied to all 934 shots in one pass
  — consistent with itself, not with anyone else's.

## 14. Story structure — where the beats land, and what pays off

`[measured 2026-09-30 · film_db.py structure · beats pinned to shot numbers, % recomputed from the rows]`
— The beats below are a reading: which shot is the threshold, the low point, the climax is a
judgement. But each is pinned to a **shot number**, and `film_db.py structure` recomputes every
position from the database, so a beat cannot drift from the film it describes. The asset is
`assets/reference-structure.json`; it stores no percentages at all.

### 14.1 The five films on one clock

`[measured 2026-09-30 · film_db.py structure]`

| Beat | F4 | F1 | F5 | F2 | F3 | Range |
|---|---|---|---|---|---|---|
| hook | 0.4 % | 1.3 % | 2.1 % | 3.6 % | 4.3 % | **all in the first 5 %** |
| threshold | 13.6 % | 4.7 % | 10.8 % | 16.1 % | 31.2 % | 5 – 31 % |
| low point | 67.1 % | 84.0 % | 55.1 % | 70.6 % | 84.0 % | 55 – 84 % |
| climax | 86.7 % | 91.2 % | 74.3 % | 78.8 % | 77.0 % | **74 – 91 %** |
| final peak | 97.8 % | 98.0 % | 80.5 % | 85.8 % | 93.9 % | 81 – 98 % |
| resolution | 99.0 % | 92.1 % | 96.0 % | 92.6 % | 98.1 % | **92 – 99 %** |
| title card | 0.0 % | 10.6 % | 1.3 % | 18.1 % | 98.9 % | no rule |

Three positions are tight enough to plan with: **the hook inside the first 5 %, the climax between
74 % and 91 %, the resolution after 92 %.** The threshold varies with how much world the film needs
to build first — F3 spends 31 % building its world before the threshold, and that investment is
what its ending cashes.

⚡ **On a 60-second promo the same clock is a hook by 3 s, a climax at 45–55 s and a resolution in
the last 5 s.** The cut-down arithmetic is the skill's own (`beat_plan.py`); these films are the
evidence that the proportions hold at ten minutes too.

### 14.2 ⚡ Plant early, pay late — twenty setups, measured

`[measured 2026-09-30 · film_db.py structure · 20 pairs]`

| Film | Setup | → | Payoff | Carried by |
|---|---|---|---|---|
| F4 | `#2` 0.4 % | → | `#185` 87.2 % | image |
| F4 | `#21` 10.5 % | → | `#119` 61.9 % | object |
| F4 | `#11` 5.5 % | → | `#205` 94.0 % | performance |
| F5 | `#7` 2.4 % | → | `#173` 66.5 % | image |
| F5 | `#25` 10.8 % | → | `#133` 53.1 % | performance |
| F5 | `#98` 40.3 % | → | `#194` 76.3 % | object |
| F2 | `#12` 3.6 % | → | `#94` 31.1 % | object |
| F2 | `#94` 31.1 % | → | `#198` 78.8 % | object |
| F2 | `#66` 23.0 % | → | `#148` 53.1 % | object |
| F3 | `#9` 4.3 % | → | `#232` 96.0 % | object |
| F3 | `#44` 16.8 % | → | `#228` 92.8 % | object |
| F3 | `#102` 46.2 % | → | `#221` 87.3 % | object |
| F1 | `#2` 1.3 % | → | `#129` 76.2 % | object |

…and seven more in `film_db.py structure`. Across all twenty:

- **Setups sit at a median 8 % of runtime — twelve of twenty in the first 11 %.**
- **Payoffs sit at a median 77.6 %** — nineteen of twenty in the second half.
- The median gap is **57.7 points of runtime**. The payoff is almost never in the same act.
- **Twelve of twenty are carried by an object.** Four by an image returning, four by a performance.

⚡ **Give the ending an object to land on, and put that object in the first tenth.** An object is the
cheapest setup there is to generate and the easiest to keep consistent: a prop sheet, not a
character sheet.

### 14.3 ⚡ The same object, changed by the story, is the payoff

`[measured 2026-09-30 · film_db.py card · read fields]`

The strongest pairs repeat the object **with one thing about it changed**:

- `F2#94` (31 %) → `F2#198` (79 %): the same object and the same kind of action, accidental the
  first time and deliberate the second. Same object, same action, the opposite meaning.
- `F3#44` (17 %) → `F3#228` (93 %): the same object, its context turned from light to grave.
- `F4#21` (10.5 %) → `F4#119` (61.9 %): the same kind of object, first on display, then discarded.

⚡ **Repeat the object; change its context, never its design.** The design is what makes the
audience recognise it 60 points of runtime later.

### 14.4 ⛔ What to distrust in §14

`[measured 2026-09-30 · film_db.py structure · positions only]`

- ⛔ **Every beat and every pair is one reader's interpretation.** The tool guarantees that the
  positions match the shots; it does not guarantee that the shot is the climax.
- **Five films is a sample.** The tight ranges in §14.1 describe these films; they are a starting
  proportion for a shotlist, not a law.
- **The pairs were found by watching, not searched for.** There are certainly setups in these films
  that this list misses, and the "twelve of twenty are objects" figure is a count of what was noticed.

## 15. Chaining — what a cut does to performance, size, angle and time

`[measured 2026-09-30 · film_db.py chain · every consecutive pair of film shots, sponsor tail dropped]`
§12 measured which categories travel together *inside* a shot; this measures what happens to each
of them *across a cut*. Performance is compared between consecutive **performer** shots: an insert
between two faces is skipped, not treated as a break. Timing leaves `split_suspect` shots out. Every
figure below prints from `python3 scripts/film_db.py chain`.

### 15.1 ⚡ Performance moves one step at a time

`[measured 2026-09-30 · film_db.py chain · intensity 0–3 from §13]`

| Film | Same | ±1 | ±2 | ±3 | Cuts between performer shots |
|---|---|---|---|---|---|
| F1 | 59 % | 36 % | 5 % | 0 % | 143 |
| F2 | 69 % | 28 % | 3 % | 0 % | 180 |
| F3 | 43 % | 43 % | 13 % | 0 % (1 cut) | 203 |
| F4 | 44 % | 47 % | 7 % | 2 % (3 cuts) | 177 |
| F5 | 64 % | 33 % | 4 % | 0 % | 226 |

**86–97 % of cuts between two performers keep the intensity or move it by one step.** A jump of two
steps or more is 3–13 % of cuts, and a jump across the whole scale (0 to 3, or back) happens four
times in all: three in F4, one in F3 (`F3#123→125`).

⚡ **Plan intensity as a ladder, not a switch.** If shot 5 needs a 3, shots 3 and 4 should be
climbing towards it, or §15.2 has to carry the jump.

### 15.2 ⚡ When the performance jumps, the frame jumps with it

`[measured 2026-09-30 · film_db.py chain · a jump UP counts when the cut goes tighter, DOWN when it goes wider]`

| Film | Jumps of 2+ | Frame moves with the jump | Frame moves with a step of 1 | Jumps at a colour-family change | …all performer cuts |
|---|---|---|---|---|---|
| F1 | 7 | 5 of 7 | 29 of 52 | 6 of 7 (86 %) | 28 % |
| F2 | 6 | 3 of 5 | 26 of 50 | 3 of 6 (50 %) | 8 % |
| F3 | 28 | 21 of 25 | 49 of 82 | 18 of 28 (64 %) | 53 % |
| F4 | 16 | 12 of 16 | 54 of 81 | 2 of 16 (12 %) | 14 % |
| F5 | 8 | 5 of 7 | 49 of 73 | 2 of 8 (25 %) | 27 % |

**Frame size is what carries a performance jump in all five films; colour carries it in only two.**
46 of the 60 jumps whose two sizes are both on the ladder cut in the matching direction (60–84 % by
film), against 52–67 % for a step of one. If framing ignored the performance, the figure would sit
near a third: size is unchanged on 23–36 % of cuts (§15.3), and a frame that does move would go the
matching way half the time. That chance figure is this file's arithmetic, not a measurement. Colour
is different. F1 and F2 put their jumps at a colour-family change far above their base rate, but F4
and F5 sit **at** it (12 % vs 14 %, 25 % vs 27 %), so "a jump needs a palette change" holds in two
films and fails in two.

What the up-jumps look like, by shot number, intensity and size:

- `F4#115→116`, 1→3, MS→MCU.
- `F5#166→167`, 0→2, MS→XCU.
- `F4#109→110→111`, 0→3→1, WS→MCU→WS, the middle shot 10.0 s. The one full release in that
  stretch is framed tight **between two wides**.

⚡ **Go tight to go up, and go wide to come down.** The wide after the peak is where the next shot
begins its own climb, which is §15.1's ladder restarting.

### 15.3 Shot size: no step rule

`[measured 2026-09-30 · film_db.py chain · consecutive shots with a size on the EWS…XCU ladder]`

| Film | Same size | 1 step | 2 steps | 3+ steps | In / out |
|---|---|---|---|---|---|
| F1 | 36 % | 24 % | 20 % | 20 % | 48 / 52 |
| F2 | 35 % | 23 % | 24 % | 18 % | 68 / 74 |
| F3 | 23 % | 23 % | 30 % | 24 % | 85 / 86 |
| F4 | 31 % | 31 % | 25 % | 13 % | 70 / 74 |
| F5 | 27 % | 23 % | 32 % | 18 % | 83 / 88 |

No film holds a minimum step. A quarter to a third of cuts **keep** the size, and these are the
cuts that change the subject, the angle or the place instead. Cuts in and cuts out are nearly
balanced in every film. The circulating rule "change size by at least two steps" appears in none of
the editing texts that could be searched (`sequence-grammar.md` §3.1).

### 15.4 ⚡ An off-eye angle is almost never answered

`[measured 2026-09-30 · film_db.py chain · a low shot followed by a high one, or the reverse]`

Of **102** shots at a low or high angle across the five films (F1–F5: 10 · 21 · 24 · 34 · 13),
**6** are followed by the opposite angle (0 · 0 · 1 · 5 · 0). Kraft's experiment, the clearest one
on low angle and power, paired a low shot of one character with a high shot of the other, and
Sevenants found the effect only when the pictures ran in story order (`sequence-grammar.md` §3.3).
These films almost never build that pair. §12.1 shows what they use angle for instead: **high is an
insert** (a hand or an object seen from above) and **low is an MS**, mostly feet and legs crossing a
threshold. That is angle used for geography and point of view, not a statement about power. The
read records "low", not whether the camera was tilted up or only placed low.

⚡ **If an angle has to mean power, give it its partner.** A single low shot does move perceived
height (Thomas & Pemstein), but the power reading needs story context; in these films a lone low
shot is a camera position, and nothing more.

### 15.5 The hold is inside the turn, not after it

`[measured 2026-09-30 · film_db.py chain · median length of the shot that follows a turn shot]`

| Film | Shot after a turn | Film median |
|---|---|---|
| F1 | 2.71 s | 2.54 s |
| F2 | 2.04 s | 2.06 s |
| F3 | 2.54 s | 2.12 s |
| F4 | 3.60 s | 3.50 s |
| F5 | 2.75 s | 2.69 s |

The shot after a change runs at the film's normal length, within half a second everywhere. Together with
§13.4, where the shot that carries the change runs 1.15–1.89× longer than one that does not, it
places the time a change needs **inside the change shot**. Nobody adds a lingering aftermath shot.

### 15.6 ⛔ What to distrust in §15

`[measured 2026-09-30 · film_db.py chain · limits of the reads above]`

- ⛔ **Intensity is one reader's 0–3 code** (§13.8). A step of one is inside that reader's
  disagreement with himself; the 2+ jumps are the robust part.
- **"Colour family" is read, not measured.** It is the bucket `COLOUR_RULES` assigns to the `light`
  line, not the measured `palette`. A cut between two warm shots of different warmth counts as "same".
- **Inserts are not on the size ladder**, so the frame test in §15.2 covers 60 of the 65 jumps.
- **Five AI short films, not ads.** The direction of each finding is consistent across the films
  that have enough cuts; the ranges are these films, not a norm.

## 16. Real ads — 38 measured, every cut confirmed by hand (lab-00006)

`[measured 2026-10-04 · analyze.py (lab-00006) · 38 ads, 44.7 min, 1,331 shots]`
§10–§15 are five festival AI shorts. This section is the first measurement of real advertising: 24 Cannes Lions
and D&AD film winners (2018–2026) and 14 strong spots, taken from trade sites, measured with
`film_breakdown.py` and a 4 fps timestamped strip, then read shot by shot by hand against one codebook
(lab record lab-00006 (not shipped)). The videos were deleted after measuring; the reads
are kept (lab record lab-00006 (not shipped)). Doctrine drawn from it: `sequence-grammar.md` §2c.

### 16.1 The corpus

`[measured 2026-10-04 · analyze.py (lab-00006) · moving % = live shots not locked; "—" = split-screen throughout]`

| ID | Ad | s | Shots | Mean shot | Moving | Structure |
|---|---|---|---|---|---|---|
| A01 | Claude (Anthropic) · Can I Get a Six Pack Quickly? | 60 | 11 | 5.47 | 30 % | dialogue scene |
| A03 | Life360 · I Think of You (Dying) | 85 | 51 | 1.68 | 31 % | mixed |
| A05 | Orange · WoMen's Football | 116 | 83 | 1.40 | 87 % | mixed |
| A06 | Squarespace · A Tale As Old As Websites | 37 | 21 | 1.77 | 15 % | vignettes |
| A07 | Renault Argentina · Historias Argentinas | 90 | 57 | 1.58 | 54 % | montage |
| A08 | Apple · R.I.P. Leon | 38 | 8 | 4.76 | 14 % | one scene |
| A09 | Apple · The Greatest | 141 | 87 | 1.62 | 38 % | vignettes |
| A10 | Nike · You Can't Stop Us | 90 | 41 | 2.20 | — | montage |
| A11 | Starbucks UK · What's Your Name | 60 | 31 | 1.94 | 73 % | vignettes |
| A12 | Dove · Reverse Selfie | 60 | 31 | 1.94 | 17 % | montage |
| A13 | Kia America · Robo Dog | 60 | 43 | 1.40 | 40 % | one scene |
| A14 | LEGO · Rebuild the World | 103 | 85 | 1.21 | 48 % | one scene |
| A15 | KFC Thailand · Let There Be Cake | 150 | 66 | 2.27 | 38 % | mixed |
| A16 | Bodyform / Libresse · #WombStories | 199 | 98 | 2.03 | 50 % | vignettes |
| A17 | Burberry · Festive | 108 | 10 | 10.80 | 100 % | one scene |
| A18 | Lacoste · Crocodile Inside | 97 | 33 | 2.94 | 91 % | one scene |
| A19 | Apple · Privacy on iPhone — Data Auction | 95 | 48 | 1.97 | 45 % | one scene |
| A20 | Mattress Firm · We've Got a Problem, America | 90 | 47 | 1.92 | 55 % | montage |
| A21 | The Farmer's Dog · Forever | 60 | 49 | 1.23 | 58 % | montage |
| A24 | Tide · It's a Tide Ad | 45 | 17 | 2.65 | 38 % | vignettes |
| S01 | Coinbase · Your Way Out | 60 | 17 | 3.53 | 71 % | mixed |
| S02 | Mattress Firm · Unjunk Your Sleep | 60 | 25 | 2.41 | 88 % | vignettes |
| S03 | Starburst · Vertical Salon (9:16) | 30 | 12 | 2.51 | 9 % | one scene |
| S04 | Vattenfall · Industrial Emissions Face Mist | 60 | 15 | 4.00 | 71 % | mixed |
| S05 | Hapvida NotreDame Intermédica · Zico | 60 | 18 | 3.34 | 88 % | dialogue scene |
| S07 | Nike · Winning Isn't Comfortable | 30 | 14 | 2.15 | 57 % | montage |
| S08 | Vaseline · A Real Nigerian Prince | 50 | 15 | 3.34 | 46 % | dialogue scene |
| S09 | Progressive · Letting Go | 50 | 14 | 3.58 | 20 % | vignettes |
| S11 | Renault · Renault Care Service | 60 | 39 | 1.54 | 84 % | montage |
| S12 | Temptations · DJ Cat | 30 | 20 | 1.50 | 11 % | one scene |
| S13 | Telstra · The Shoemaker | 60 | 35 | 1.71 | 26 % | vignettes |
| S14 | Rocket Mortgage × Redfin · America Needs Neighbors Like You | 60 | 37 | 1.62 | 46 % | mixed |
| S15 | Cartier · Tank Française | 60 | 36 | 1.67 | 65 % | mixed |
| S16 | LEGO · Everyone Wants a Piece | 60 | 41 | 1.46 | 24 % | one scene |
| S17 | Icelandair · The Polite Tourist Bouncer Returns (1:1) | 43 | 19 | 2.24 | 44 % | mixed |
| S18 | Life360 × Tile · Coffin | 45 | 30 | 1.51 | 23 % | one scene |
| S19 | Salesforce × MrBeast (9:16) | 48 | 26 | 1.83 | 72 % | mixed |
| S20 | IKEA · Awake | 30 | 1 | 30.06 | 100 % | single take |

### 16.2 ⚡ Pace — about twice as fast as the festival films

`[measured 2026-10-04 · analyze.py (lab-00006) · graphic end-card rows excluded from per-ad means]`

- Mean shot per ad: p10 1.45 s · p25 1.52 · **median 1.84** · p75 2.62 · p90 3.58 s. One shot: median 1.5 s, p10
  0.67 s, p90 3.6 s. About 15 shots per 30 s.
- The slow end is dialogue and deadpan: A01 5.5 s, A08 4.8, S04 4.0, S09 3.6, S01 3.5, S05 and S08 3.3.
- Lengths are uneven in every ad: coefficient of variation median 0.64, lowest 0.36.
- The last third is faster than the first in 18 of 36 ads, slower in 12, even in 6. The shortest fifth of
  shots sits at a median 55 % of the running time (IQR 38–74 %).
- The first shot runs longer than the average shot: median 2.8 s (2.6 s in the 26 ads of 62 s or less).

### 16.3 ⚡ Camera — half the shots move, and long holds are normal

`[measured 2026-10-04 · analyze.py (lab-00006) · 1,138 live / found-footage / mixed shots]`

- Shots that move: 51 % pooled; median per ad **46 %** (IQR 30–71 %). 5 of 36 ads move under 1 shot in 5
  (locked comic tableaux: A06, A08, A12, S03, S12); 6 move over 4 in 5 (A05, A17, A18, S02, S05, S11).
- Of 615 move components: push 19 %, track 16 %, drift 15 %, handheld 14 %, pan 12 %, pull 7 %, zoom 6 %,
  tilt 5 %, whip 2 %, crane 1 %, orbit and roll under 1 %. Handheld on 7.5 % of shots; no ad is push-only.
- Longest run of locked shots per ad: p25 2 · median 5 · p75 8 · p90 11 · max 15. 24 of 36 hold four or more
  in a row.
- Speed: normal for nearly every shot that could be read; slow motion on 5.

### 16.4 ⚡ Frame — show the place, stay near eye level

`[measured 2026-10-04 · analyze.py (lab-00006) · 1,283 non-graphic shots]`

| Size | WS | MS | MCU | insert | CU | MWS | EWS | XCU |
|---|---|---|---|---|---|---|---|---|
| Share | 32 % | 22 % | 15 % | 12 % | 10 % | 7 % | 2 % | 0.5 % |

- Wide (WS/EWS) per ad: p10 16 % · median 32 % · p90 50 %. Angle: eye 75 %, low 16 %, high 8 %, aerial 2 %;
  eye level per ad p10 44 %, median 77 %.
- Across a cut (both sizes on the face ladder): same size 25 %, one step 25 %, two or more 49 %.
- Subject centred in the first frame of 72 % of shots; a person addresses the lens in 3.7 %.
- The size changes inside the shot (a move or the subject reframes it) in 7.7 % of shots.

### 16.5 ⚡ Cuts — straight, on motion, into action already under way

`[measured 2026-10-04 · analyze.py (lab-00006) · 1,293 cuts]`

| How the cut is made | Share | What the cut lands on | Share |
|---|---|---|---|
| straight cut | 96.8 % | action already under way | 45 % |
| match on action | 1.3 % | a look | 13 % |
| fade / dissolve / graphic wipe | 1.2 % | establishing | 9 % |
| jump / whip / smash / graphic match | 0.8 % | reaction | 9 % |
| | | at rest | 7 % |
| | | reveal, product, text, POV | 4 · 4 · 3 · 2 % |
| | | the start of an action | 2 % |

- Relation: a new angle on the same scene 45 %, a new place or time 33 %, back to a setup already seen 11 %,
  an insert from the same scene 6.5 %, a graphic card 4 %.
- Cue in the outgoing shot: motion 36 %, a look 11 %, a sound 2.5 %, none 50 %.
- What changes: usually subject and size, often angle; place at 34 % of cuts; **emotion at 1.2 %**; place,
  subject and emotion together at 2 cuts.
- Per 30 s (per ad): edits median 8.6; cuts to a new place or time median 4.4 (IQR 0.6–8.0). Over 10 per 30 s:
  A07, A10, A16, A21, S14 — all music-led montages.

### 16.6 Beat — real ads do not cut on it

`[measured 2026-10-04 · process_ad.py + analyze.py (lab-00006) · librosa beats on the full mix; a hit = cut within 0.08 s]`

Across 37 ads with a detectable beat, a median 31 % of cuts hit a beat against 32 % for random cut times
with the same count. Two ads clearly cut on the beat (A08, S08); a single passage can lock (A15's chase: 62 %).

### 16.7 ⚡ Brand and end card — the award winners brand late

`[measured 2026-10-04 · analyze.py (lab-00006) · in-picture brand only; corner bugs excluded]`

- Product first on screen: median 17 % of the running time (28 ads show a product; by 5 s in 10).
- Brand first legible: median **76 %** of the running time; by 5 s in 6 ads; only in the last 15 % in 15.
- Brand runs: one in 16 ads, two in 11, three or more in 11.
- End card: median 4.0 s (IQR 3.0–5.5), 7 % of the running time.
- Text on 16 % of shots, the product on 18 %. Music carries 26 ads, dialogue 10, voiceover 17.

### 16.8 ⚡ The same measures on the skill's own scripts

`[measured 2026-10-04 · compare.py (lab-00006) · lab-00005 outputs, 20 briefs per arm]`

| | Real ads | Claude v2.13 | Claude v2.14 | Claude bare | Kimi v2.14 + lint |
|---|---|---|---|---|---|
| Mean shot | 1.85 s | 3.98 s | 3.73 s | 3.70 s | 3.34 s |
| Shots that move | 46 % | 0 % | 36 % | 40 % | 38 % |
| Wide (WS/EWS) | 34 % | 16 % | 21 % | 13 % | 21 % |
| Close (MCU/CU/XCU) | 25 % | 29 % | 38 % | 34 % | 34 % |
| Eye level | 75 % | 51 % | 47 % | 39 % | 52 % |
| Same-size cuts | 25 % | 22 % | 17 % | 12 % | 13 % |
| Longest held run | 5 | 9 | 3 | 3 | 3 |

The scripts hold every shot twice as long as an ad does, frame tighter and spread height more. That is
the measured half of the "stale" complaint.

### 16.9 ⛔ What to distrust in §16

`[measured 2026-10-04 · analyze.py (lab-00006) · limits of the reads above]`

- **One reader per ad**, 13 readers on one codebook, with shared decisions between batches. Moves were read
  from 4 fps stills plus feature matching; speed could not be read on 15 % of shots.
- **Vertical is not measured:** 35 of 38 are landscape (S03 and S19 are 9:16, S17 1:1).
- **Award films are big-budget craft**; 12 of 38 run over 62 s. The brand timing in §16.7 is craft practice,
  not performance optimisation (`sequence-grammar.md` §2c, item 11).
- The cut detector found 76 % of the true cuts before correction; every figure here is after correction.
- Beats were detected on the full mix; trade-site files may be recuts of the aired version.

### 16.10 ⚡ The revise loop — the director's review, then the card (lab-00008)

`[measured 2026-10-06 · compare_loop.py + run_judge_lab8.py / summarize_lab8.py (lab-00008) · 20 lab-00005 briefs, Claude (17 revised) and Kimi K3 (20), blind GLM-5.3-flash + Qwen3.8-27B judges, 2 judgements a brief per pass]`

The question: can the skill's scripts be brought to real-ad numbers by revising them against the
`sequence_lint.py --baseline` card (§16 bands), and does that make better ads? Four ways to revise the same
first drafts (Claude v2.15, Kimi v2.15b) were compared: the card alone for up to three rounds; one free review
pass with the same rules and the §2c baseline in prose but no numbers; and the review followed by the card.

**The numbers — baseline-card measures OUT (outside 8 ads in 10), summed over the scripts:**

| | First draft | Card r1 | Card r2 | Card r3 | Review only | Review → card r2 | Review → card r3 |
|---|---|---|---|---|---|---|---|
| Claude (17 scripts) | 33 | **1** | — | — | 28 | **0** | — |
| Kimi K3 (20 scripts) | 61 | 33 | 18 | 14 | 56 | 40 | 34 |

**The judges — mean change against the first draft, same brief, same judging context (1–10 scale):**

| | Sequence variety | Action | Imagery | Clarity / fit | Producibility | Ranked above the first draft |
|---|---|---|---|---|---|---|
| Claude, card r1 (two passes) | +0.18 / +0.41 | +0.03 / +0.24 | 0.00 / +0.24 | −0.09 / +0.15 | −0.12 / −0.12 | 18 / 24 of 34 |
| Claude, review only (two passes) | +0.76 / +0.85 | +0.62 / +0.71 | +0.35 / +0.41 | +0.18 / +0.26 | −0.12 / −0.29 | 30 / 27 of 34 |
| Claude, review → card r2 | **+1.24** | **+1.03** | **+0.74** | +0.32 | −0.29 | **29 of 34** |
| Kimi, card r1 / r3 | +0.45 / +0.88 | +0.17 / +0.38 | +0.07 / +0.23 | +0.10 / +0.10 | −0.10 / −0.28 | 22 / 22 of 40 |
| Kimi, review only | +0.80 | +0.35 | +0.03 | −0.33 | −0.60 | 30 of 40 |
| Kimi, review → card r2 | +0.95 | +0.57 | +0.20 | −0.05 | −0.20 | 29 of 40 |
| Kimi, review → card r3 (vs r2 in one context) | +0.90 (r2 +0.88) | +0.38 (r2 +0.38) | +0.07 | −0.03 | −0.28 | 23 of 40 (r2 28) |

**What the scripts became (median of scripts, the §16.8 measures):**

| | Mean shot | Move | Wide | Close | Eye | Same-size cuts | 2+ jumps | Shots | Length |
|---|---|---|---|---|---|---|---|---|---|
| Real ads (38) | 1.85 s | 46 % | 34 % | 25 % | 75 % | 25 % | 49 % | — | — |
| Claude first draft | 2.6 s | 31 % | 26 % | 37 % | 62 % | 17 % | 65 % | 13 | 34.0 s |
| Claude review → card r2 | 2.4 s | 35 % | 28 % | 32 % | 68 % | 21 % | 52 % | 15 | 35.3 s |
| Kimi first draft | 3.0 s | 21 % | 18 % | 34 % | 69 % | 7 % | 62 % | 10 | 29.8 s |
| Kimi card r3 | 2.5 s | 37 % | 27 % | 32 % | 81 % | 18 % | 52 % | 12.5 | 29.0 s |
| Kimi review → card r2 | 2.2 s | 31 % | 22 % | 33 % | 76 % | 9 % | 66 % | 12 | 26.9 s |

**Reading:**
- ⚡ **The card fixes numbers; the review makes the ad.** Alone, the card's revisions were mostly one-size
  swaps (MS → MWS, CU → MS) that cleared the card and moved the judges little. The review rewrote what the
  judges see — something happening in the shot, the place shown, the proof on screen — and left the numbers
  out. In that order, the card then cleared the numbers without undoing the review's gains.
- **Claude converges in one card round, a router model does not.** Kimi needed three card rounds to get from
  61 to 14 OUT; its third round fixed 7 measures and broke 3 pieces. After the review, a third round brought
  no judged gain.
- ⛔ **The card can be gamed by relabelling.** Three writers met the eye-height band by re-coding heights rather
  than moving the camera (a child's eye line written as "knee" one round and "eye" the next). The ads were
  coded against the subject's eyes; the chain's Height is the camera's height (`sequence-grammar.md` §3.4),
  so a film at a child's or animal's eye line reads low by construction and is kept in Break, not relabelled.
- ⛔ **Every revision cost producibility** (more shots and moves to generate), and Kimi's revised scripts ran
  short (median 26.9 s on 30–45 s briefs): the running time is re-checked every round.
- ⛔ **What to distrust:** scripts were judged, not cut films; two inexpensive judge models, and the same
  version re-scored in a new context moved by up to 0.25 (Claude card r1 sequence variety +0.18 vs +0.41);
  17–20 briefs; the review pass had freedom the card pass did not, so part of its gain is freedom, not the
  absence of numbers. The lab record is lab record lab-00008 (not shipped).

## 8. How this file grows

1. **A supplied corpus is filed HERE first**, described in our own words with its source named,
   before any rule is written from it. The entry is the specific plus what it did. Doctrine comes
   after, and links back. Third-party text is never pasted in (course and corpus wording stays with
   the source).
2. An entry earns a **⚡** only when it is a technique the next director can type, not an
   observation.
3. When an entry is used on a real job and the numbers come back, the result goes to
   `memory/episodes/` and the entry gets a measurement line.
4. ⛔ **Do not add an entry you cannot SOURCE or MEASURE.** A rule restated in general words is a
   rule wearing a specific's clothes, and this file exists because that substitution happened twice:
   an entry keeps the concrete detail (the order, the number, the object). It names its source with a
   tag (`[SECONDARY · …]`, in the entry or its section's opening), or it stands on a number and carries
   `[measured <date> · <tool>.py · <n>]` so anyone can re-run it. `skill_audit.py` check 9b enforces
   one or the other.

**Cross-refs:** `move-catalogue.md` (camera moves) · `prompting-craft.md` §11b–§11e (the prompt
mechanics these fragments are instances of) · `character-and-props.md` §8.3b–§8.3e (sheets,
sub-references, scope suffixes) · `refinement-loop.md` §1b (the correction loop these iterations
came from) · `production-design.md` §5b (plate hygiene).
