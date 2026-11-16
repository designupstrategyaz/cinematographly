# Direction — performance, blocking, coverage, and the selects pass

The skill knew how to *photograph* a scene and how to *generate* it. What it lacked was the
director's actual job: deciding **how a moment is performed**, **where everyone is in space**, and
**what coverage the editor will need** — then reviewing the takes against that intent before the
edit inherits them.

This matters more with AI actors, not less. A human actor fills an unspecified moment with craft; a
generation model fills it with its **default** — the pleasant, evenly-lit, mildly-smiling talking
head. Every direction you don't give is a decision the model makes for you, identically, in every
clip. That sameness is itself an AI tell (`realism-qa.md` V14) and, across a series, it is why
episode 12 feels exactly like episode 1.

Provenance: this file consolidates a cross-vendor production review (director/producer/editor/VFX
panel run 2026-08-28 via the model-router) with the skill's own production record; every item was
verified against how the pipeline actually works before landing here.

---

## 0b. The board — the artifact a decision is actually made on

A director does not decide from a list. `image: a bottle on a steel bench` is a sentence you agree
with; you cannot see that the bench reads as a laboratory until something is rendered, and by then
it was rendered at production cost. That is the whole failure: **credits spent discovering
something the plan already contained.**

So `scripts/board.py` builds three pages, each self-contained HTML, each answering one question:

| board | the question | when | what it costs |
|---|---|---|---|
| `look` | **is this the world?** | before the concepts | nothing — it is the photographs already sourced |
| `concepts` | **which one?** | the choice `gate.py approve concept` records | nothing, unless you buy previz |
| `shots` | **will this work?** | before `approve cast` / `approve clips` | nothing — it renders the plan |

Two properties matter more than the layout.

**Side by side beats in sequence.** Five concepts read one after another get *ratified* — the first
one sets the frame and the rest are compared to it. Five concepts seen together get *chosen
between*. That is not a presentation preference; it is the difference between a decision and an
assent, and it is why the concept board is a gate rather than a nicety.

**A stale board is not a board.** `gate.py` compares the board's mtime against the files it was
built from and refuses when a source moved. A board built before the concepts were rewritten shows
concepts nobody is approving. Existence would be a weak check — building one is a single command;
freshness is not.

### Previz, and why it is capped rather than banned

Concept art is the one generation that *saves* money, and for a while this skill refused it — which
pushed the same spend downstream into finished shots where it costs more and teaches less. Real
productions buy concept art precisely because it is a fraction of a shoot day.

`gate.py previz <job> --budget N --why "<the decision this unblocks>"` opens the lane, and every
constraint on it is doing work:

- **the look board must already be filled.** You do not generate a picture of a thing before you
  have looked at photographs of the real thing. Real references cost nothing and routinely kill the
  concept the previz would have flattered.
- **`--why` in your own words, five words or more.** "Concept art" is a label. A spend nobody can
  state a reason for is the spend the gate exists to stop.
- **a hard cap of twelve.** Past a dozen images you are not deciding, you are browsing — and the
  answer to "none of these are right" is a better brief, not more of them.
- **the quality floor is NOT relaxed.** A cheaper generation is a different picture, so cheap previz
  would mislead you about the very thing it exists to show. The cap is on *count*.
- **it closes when the concept is signed.** Previz informs the choice. After the choice a picture is
  a start frame: write the prompt, lint it, go through the frame gate. Nothing under
  `00-brief/_previz/` can be approved as a frame, at any stage.

## 0c. Reading the film as one object

Everything else in this file directs a shot. This section is the other axis, and it did not exist
until 2026-09-07: **nothing compared one shot to another.** Three faults live only there.

| fault | why no per-shot check can see it | where it surfaces now |
|---|---|---|
| the requirement nobody owns | six shots need the hero; not one of them is wrong | `breakdown.py` cast list · `gate.py approve cast` refuses |
| the same thing sourced N times | four `need: white linen apron` slots are each correct | breakdown's SOURCE-ONCE finding |
| drift | S1 green, S4 olive — both prompts are fine, the film is not | breakdown's continuity pass |

⛔ **A difference between two shots is a question, not a verdict.** A costume change between scenes
is a legitimate VARIANT and is indistinguishable from DRIFT by reading the words. What the tool
refuses to allow is the third state `series-continuity.md` names: *differing because nobody
decided*. Every row it prints is addressed to you, and the answer "yes, deliberate" closes it.

Two design notes worth carrying to anything similar. Continuity compares **only attributes the
reference plan declares** — scraping block words for an attribute no shot ever asked for
manufactures findings, which is how a checker starts costing more attention than it saves. And two
shots **bound to the same reference** are never flagged for wording differently: the pixels are the
agreement, and punishing that would punish the fix.

## 1. The performance card — direct the moment, not the line

For **every dialogue or reaction clip**, before generation, write the card. It becomes the
`[PERFORMANCE]` block of the prompt (`ai-generation.md`), the counterpart to `[SPEECH]` and
`[MOTION]`. **Version 2 (2026-09-30)** adds STIMULUS, TARGET and BODY — the external half of the
acting tradition that a model can render (`acting-for-the-model.md` §1–§2, §7):

```
[PERFORMANCE]
STATE:    <the emotional state, as a transition: "defensive → conspiratorial", not "happy">
STIMULUS: <what they react to, outside them, and when: "his line" · "the phone buzzes at 1 s" ·
           "none — she starts it">
TARGET:   <who or what they play towards, and where: "the guest, camera-left" · "the lens">
BEAT:     <the before, held>, then <the one change>: "listens, still; then leans in on the second phrase">
BODY:     <MS or wider: one bundle in plain words: "weight forward, shoulders open, hands still">
FACE:     <what the face does, said as a state: "smile stays, eyes drop; the head stays still">
GAZE:     <where the eyes are and when they move: "on the guest, the whole clip">
AFTER:    <the aftermath — the ONE silent beat the shot ends on, and where motion comes to
           rest: "mouth closes, breath out, gaze drops to the bottle" (`shot-handoff.md` §3)>
```

Rules:

- ⚡ **Every line must name something the camera can see.** That is the test that separates the
  half of actor training a model can use from the half it cannot (`acting-for-the-model.md` §2). A
  line that only makes sense inside the performer's head is not a direction.
- **STIMULUS before the reaction; TARGET outside the performer.** A reaction with no written cause
  reads as random (Swain; Meisner), and a gaze with no target drifts into the vacant look. "None —
  she starts it" is a valid STIMULUS; leaving it blank is not.
- **BODY is the channel in a medium shot or wider.** The face is read slowly at that size; write
  three or four plain-language qualities from one bundle (`acting-for-the-model.md` §4). All 18 peak
  shots in the five reference films are either body-and-touch or MCU-and-closer
  (`specifics-catalogue.md` §13.5a).

- **State is a transition, not an adjective.** A clip is 3–6 seconds; a static emotion is a
  wallpaper. "Skeptical → curious" gives the model an arc to animate and gives QA something to
  verify.
- **One beat per clip.** Two emotional events in four seconds reads as twitching. If the line
  genuinely turns twice, it is two clips (same rule as two speakers).
- ⚡ **Land the BEAT in the second half of the clip.** Measured across 934 performer shots in five
  festival AI shorts (`specifics-catalogue.md` §13): when a feeling changes inside a shot it changes
  **late — 112 times against 17 early**, late ahead of early in every film — and a shot that carries a
  change runs **1.15–1.89× longer** than one that does not. Write the first half of the clip as the
  STATE's *before*, and put the change on BEAT after a "then" — one "then", one change.
  `film_db.py card <FILM#N>` prints any reference shot in exactly that form. And default the register to **restrained** — eyes and mouth
  only: 1.9 % of those 934 shots are a full release.
- **Write the stillness as a state.** Models over-animate: constant head motion, brow flutter,
  over-smiling. "The head stays still", "the smile holds at a half-smile", "hands rest on the table" is
  often the strongest direction on the card. On a model with a negative field the over-animation can
  also go in `[SUPPRESS]` as nouns ("head bobbing, brow flutter, widening smile"); on one without, the positive
  state is all there is, because anatomy is never named inside the prompt (`ai-generation.md`, the guardrails,
  v2.71.0).
- **Name the aliveness beats as content, never as timing.** A blink, a glance down to the label and
  back, a swallow, a weight shift — two or three of them, named. Frame counts, milliseconds and
  easing words are not honoured by any model on the roster and crowd out the words that are
  (`timing-and-performance.md` §6A and §9). What you *can* direct is the register:
  **slower onset and a held apex read as felt; fast, big and brief reads as performed** — so
  "a small smile that grows slowly and holds" is a direction, and "she smiles warmly" is not.
- **Prompt the body before the face.** In a medium shot or wider the acting is in the shoulders,
  the weight and the hands; the face is the layer the model smooths away hardest
  (`timing-and-performance.md` §4).
- ⛔ **`AFTER:` is not optional on a clip that runs past its line.** Glebas's three stages are
  anticipation, action and **aftermath**; the model renders the first two and invents the third. An
  undirected tail on an audio-driven clip is where the lips keep moving after the line ends — the
  defect, its four causes and the fix are `shot-handoff.md` §1. On a clip generated *to* the line,
  `AFTER:` is still worth writing, because it tells you what the last frame should be and therefore
  what the next shot inherits.
- ⛔ **STATE is derived from the map, not authored per shot.** Adler's rule, via Miller: *the whole
  text — not the local stage direction — dictates how a character behaves.* A performance card
  written in isolation IS the local stage direction. Write the piece's emotional journey first
  (`emotional-journey.md` §2), then read each shot's STATE off it. And ⛔ **never let STATE reach a
  prompt as an emotion word** — it is converted to a circumstance and a physical action on the way
  in (`emotional-journey.md` §4).
- **The arc lives across cards.** The series-level arc (skeptical → weary → interested → convinced —
  the profile's tonal locks) is delivered by the *sequence* of per-clip states. Write the episode's
  state ladder first, then the cards, so clip 4's state follows clip 3's. ⚡ **Across cards the
  intensity climbs one step at a time** — 86–97 % of cuts in the reference films keep it or move it
  one step — and when it has to jump two, the frame jumps with it: tighter going up, wider coming
  down (`sequence-grammar.md` §4.2, `specifics-catalogue.md` §15.2). That is the baseline, not the
  goal: the chain carries a contrast plan and at least one deliberate break, so the piece has a peak
  in its pictures as well as in its story (`sequence-grammar.md` §2b). The chain is written as a table
  before the cards (`assets/shotlist-template.md`, *Sequence chain*) and checked by
  `scripts/sequence_lint.py`.
- **Locked-audio clients:** the performance card is fully open even when the words are locked — it
  is exactly the "delivery direction" lever `script-craft.md` §5 names. Same approved line, different
  card, different scene.

**QA hook:** the per-clip QA card (`realism-qa.md` §6) checks the clip **against its performance
card**, not against "looks fine." A technically clean clip with the default pleasant face is a
retake candidate, and at the selects pass (§4) that is exactly what gets caught.

## 2. The blocking card — decide the space once, per scene

The 180° rule and eyeline matching were already in the craft file. What was missing is the artifact
that makes them enforceable when every shot is generated independently: a **blocking card** per
scene, in the shotlist, before any start frame is prompted.

```
[BLOCKING — Scene N]
GEOGRAPHY: <the room in one line, with the anchor: "kitchen; window camera-left, table centre">
POSITIONS: <who is where: "A stands left of table facing right; B seated right, facing left">
THE LINE:  <where the 180° axis runs: "along the table; cameras stay on the window side">
EYELINES:  <who looks where: "A → B slightly down; B → A slightly up">
PROPS:     <what is in whose hand, which hand, where it rests: "contract in B's left hand">
LIGHT:     <the source and side, consistent with the Kelvin spec: "window key, camera-left">
```

- **Every start-frame prompt in the scene quotes the card.** Position, facing, eyeline direction and
  light side go into each prompt verbatim — that is how five independently generated shots come back
  cuttable.
- **Reverse angles are derived, not re-imagined.** The reverse of "A left facing right" is "B
  right facing left, same window side" — write both into the card so the model never invents a
  mirrored room.
- **Props are continuity's sharpest edge.** Which hand holds the object is the thing that flips
  between generations. Name it, and check it on the QA card.
- A two-line overhead sketch in the shotlist notes is worth doing for any scene with two characters
  or a camera move. Ugly is fine; ambiguous is not.

## 2b. ⚡ The shot event card — the check that costs nothing and was running too late

The blocking card decides **where things are**. It does not ask **what happens**, and until
2026-09-08 nothing in this skill did — at the plan. The payload test existed (`cinematography-craft.md`
§3.3, and F11 in §8: *"last frame against first — the audience learned nothing across the move"*)
but F11 runs at the **clip gate**, which is after the clip is generated and paid for. The skill
prices the frame gate at ~10× leverage and then put its single most important motion question
downstream of it.

⛔ **This was found the expensive way.** A hook shot was written as "a bare mattress, and only dust
moves." It passed `prompt_lint` — the only-camera-verbs rule did not fire, because *dust drifts* is
not a camera verb — and it was defended twice as deliberate restraint before anyone asked the one
question that kills it: at the end of six seconds, what does the viewer know that they did not know
at the start? **Nothing.** That is a dead shot, and no amount of rewriting the motion prompt fixes
it, because the fault is in the shot, not the sentence.

**One card per shot, three lines, written before any start frame is authored:**

```
[EVENT — <SHOT>]
HAPPENS:  <the one thing that occurs, as a completed action with a subject that is not the camera>
AT START: <what the viewer knows / can see in frame 1>
AT END:   <what they know / can see in the last frame — and it must NOT be the same sentence>
```

⛔ **If AT START and AT END say the same thing, the shot is cut or redesigned. Not re-prompted.**
This is the F11 test moved to where it costs a sentence instead of a generation, and it is the
cheapest check in this file.

**Three failure shapes it catches, all of which look fine in a prompt:**

| Shape | Looks like | Why it is dead |
|---|---|---|
| **The reveal of a static thing** | a light crawls across an object; a slow push arrives at it | the object was always there; the viewer learns the frame, not the world. Legitimate ONCE per film, as an establisher — never as a hook |
| **Ambient-only motion** | dust drifting, steam rising, a curtain breathing, water rippling | atmosphere is not an event. It reads as a still photograph someone left running, which is exactly what it is |
| **The camera-only clip** | any MOTION block whose verbs all belong to the camera | a filter over a photograph (`motion-craft.md` §6 item 6). `prompt_lint.py` already refuses this one |

`prompt_lint.py` enforces the card: a clip prompt carries a **`payload:`** line in its frontmatter —
one sentence naming what the viewer knows at the end that they did not at the start — and a clip
whose `END:` line *asserts* that nothing changed is refused outright.

**Three optional lines that charge the event** (adopted 2026-10-26 from the three-model jury,
the intent and emotion proposal of 2026-10-26 [studio history]), written as clip frontmatter:

```
tell:      <the decision before the action: "eyes to the jar, a breath">
obstacle:  <the one resistance the intent beats: "the wet sugar sticks; she raps it on the rim">
witness:   <the prop that holds the state and the action changes: "the full sugar jar on the counter">
```

The tell is strongest in drama, where it carries the decision; the obstacle shows the intent in how the
person beats it; the witness lets the start frame hold the "before" so the action has something to
change (§6c of `motion-craft.md`: put it in the still). Use one obstacle at most. Whether a shot that
proves a claim may carry one depends on the script and the director (2026-10-26: *"Depends on the
script and director's decision"*), so `prompt_lint.py` warns on an `obstacle:` there, and does not refuse it.

⚠️ **The honest exception.** A held, eventless frame is sometimes exactly right — Deakins builds
*Sicario*'s tension by holding (`cinematography-craft.md` §3.5), and §3.8's second lever is the world
moving through a static frame. The card does not forbid stillness. It forbids stillness *that the
viewer learns nothing from*. A held frame where a face changes, or where the viewer is waiting for
something they have been told is coming, has an enormous payload and passes on the first line.

---

## 2c. ⛔ Five shots, then kill four — the divergence step that was missing entirely

`ideation.md` §3–§6 demands ten concepts before evaluating any, structured divergence, and kill
rounds. **All of it operates at CONCEPT level.** There was no equivalent at shot level, and the
consequence is specific: a shot arrives as **n = 1**, and a first idea then gets defended instead of
compared. A shot is not boring because the writer lacked vocabulary. It is boring because nothing
was ever put next to it.

**For any shot carrying real weight — the hook, the turn, the button — write five events before
choosing one.** Not five prompts: five answers to "what happens here". Then kill four, one line each
on why. The killed four go in the shotlist under the card; they are the cheapest retake plan you
will ever have, because when the chosen shot comes back wrong you already have the next four.

**Force spread rather than five flavours of one idea** — the same trap the angle grid solves at
concept level (`ideation.md` §4). One from each row is a working default:

| Row | The event is… | Example, for a hook that must say "this surface fails" |
|---|---|---|
| **A person acts** | someone does something and the world answers | a hand presses the foam; the dent stays |
| **An object changes state** | no person; the thing itself transforms | a sheet is stripped away and what is underneath is revealed |
| **A comparison arrives** | two things enter the same frame | a second, fresh mattress edge slides in beside the first |
| **Time is compressed** | the same frame, later | the same hollow, a year of mornings, one dissolve |
| **The expectation breaks** | a pattern is set and then interrupted | a row of identical beds, and the camera stops at the one that sags |

⛔ **Rank them by PAYLOAD, not by how they sound.** The winner is the one whose AT END sentence is
furthest from its AT START sentence, subject to being generatable at all (`cinematography-craft.md`
§3.8's per-move ruling, and the failure classes in `realism-qa.md`). A beautiful event you cannot
generate is a killed row, not a chosen one.

---

## 3. Coverage — generate choices, not just "the shot"

One line = one clip is the generation rule, not an editorial plan. A scene generated as exactly its
dialogue clips gives the editor **no choices**: nothing to cut away to when a syllable floats,
nothing to vary pacing with, nothing to react with. Coverage is how a director protects the edit.

**Minimum coverage set per dialogue exchange:**

| Element | What it is | Cost note |
|---|---|---|
| The speaker clip | The line, per the performance card | The expensive one (audio-driven) |
| **The listener reaction** | 3–5s of the *other* character listening, per their own performance card | Cheap: silent generation, no lipsync — and it is the single most valuable insurance in the set |
| One insert | Hands, prop, product, detail relevant to the line | Cheap; reusable across episodes |
| The scene's B-roll (already required) | ≥ dialogue clips, +2 | Unchanged |

- **Reactions are the story.** The skeptic's face turning is the value turn made visible
  (`craft-cheatsheet.md`); it is also the lipsync-rescue cutaway and the pacing valve. **A dialogue
  scene with no reaction coverage is under-shot** — treat it as a gate at the storyboard stage.
- **Reactions are cheap by design:** silent, no audio reference, short, and highly reusable within
  an episode (a good listening loop covers several lines). Budget them as B-roll-tier, not
  dialogue-tier.
- **Don't over-cover.** This is not a film set; every extra angle is credits. The minimum set above
  is the floor; go past it only where the beat is the episode's climax.

**Minimum coverage for a filmed song or dance performance**, beside the dialogue floor: a wide of the
place, the group or pair together, each performer's face, and the hands, all before the story cut; the
edit then comes back to the performer between cutaways. Take slates are coverage of one room, not new
places, and a shot that replays counts once. For a generated performance each size is a paid generation
through `gate.py`, and "don't over-cover" still applies.

## 4. The selects pass — a director's gate between generation and edit

The pipeline had a *technical* QA gate (on-model, no artifacts, lipsync verified). It lacked the
**directorial** one: are these the right takes?

After generation QA passes and **before anything is filed for the edit**, run the selects pass over
the whole scene's clips together, against the storyboard and the performance cards:

- [ ] Does each clip deliver its **card** — the state transition, the beat, the gaze?
- [ ] Do adjacent clips **cut** — eyelines opposed, positions per the blocking card, light on the
      same side?
- [ ] Watched **in script order as a silent sequence**: does the scene's emotional arc read with the
      sound off? (If the arc doesn't read silent, the performances are flat, whatever the audio says.)
      The same question is asked of the locked film before export — T2 in `sound-off-story.md`.
- [ ] Is there a usable reaction for every exchange?
- [ ] Which clips are *selects*, which are *usable backups*, which are **retakes** — decided now,
      while the budget and the generation context still exist, not discovered in the edit where a
      retake costs a re-sync and a re-cut.

Mark results in the shot manifest (`shot_manifest.py status --set select/retake/backup`), and run
`scripts/contact_sheet.py --project <dir> --glob "S<n>-*"` first — the silent-sequence read and the
blocking check happen on a frame grid, not from memory of having watched the clips. The retake decision itself then follows the
economics tree in `ai-generation.md` — the selects pass decides *that* a clip fails intent; the tree
decides what to do about it.

## 5. The tone bible — one page that stops series drift

For any recurring series, write one page into the client profile (§6, beside the Visual Bible) that
answers what no shot-level spec can: **how does this world behave?**

- The comedic/dramatic register, stated plainly: deadpan? warm? slightly absurd? Never mean?
- What the world permits: do characters address camera? does physics bend for a joke? how big can a
  reaction be before it breaks the register?
- Each character's **want** and **counter-want** across the series (she wants the deal *and* his
  respect; he wants to be right *and* to be helped).
- Three touchstone moments from shipped episodes that got the tone exactly right — named clips, so
  "like that" has a referent.
- What the series never does. The negative list for tone.

Episode 3 drifts from episode 1 in ways a client notices but can't articulate; the tone bible is
what you check the drift against — at the script stage and again at the selects pass.

**Cross-refs:** `ai-generation.md` (the `[PERFORMANCE]` block in the prompt; retake economics) ·
`craft-cheatsheet.md` (the arc, the 180° line this file operationalises) · `realism-qa.md` §6 (the
QA card the performance card plugs into) · `script-craft.md` §5 (delivery direction on locked lines) ·
`assets/shotlist-template.md` (where the cards live) · `pm-workflow.md` (the shot manifest and the
selects pass in the board) · `brand-system.md` (the tone bible as a Visual Bible section).
