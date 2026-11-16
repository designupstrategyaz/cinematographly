# Shot handoff — the exit, the join, and what B-roll is for

**When to read this:** a clip keeps animating past the end of its line; you are deciding how long to
generate a dialogue clip; the cuts between clips feel arbitrary; you are choosing B-roll and cannot
say what it is *for*; or you are writing a shotlist and the only thing it says about the join is
"hard cut". `editing-storytelling.md` is *why* a cut works; `timing-and-performance.md` is the shape
of motion *inside* a shot. This is the **contract between one shot and the next** — what a shot owes
its neighbour, and what has to be decided before generation because it cannot be decided after.

Source tiers follow `research-quality.md`. Craft sources read **2026-08-29** from the local film
corpus; vendor and paper sources checked **2026-08-29** with URLs in `assets/further-reading.md`.
The craft half is durable. **§1 and §8 are dated** — they describe a specific model roster.

---

## 0. Why this file exists — the structural diagnosis

An animator handed a single shot is told to *"read the script, study the animatic and storyboards,
talk to the supervisor and the animators on adjacent shots, so your shot's beat connects to the ones
around it."* The named anti-pattern is *"working a shot in isolation without knowing the surrounding
context."* [PRIMARY · Kelly & Baena, *Animation Tips & Tricks Vol. 2* — via a local extraction, read
2026-08-29]

**A per-clip video generator is structurally an animator handed one shot with no knowledge of its
neighbours.** It cannot know what came before, what comes after, where the cut lands, or what the
shot is for. Every fault in this file follows from that, and so does the remedy: the connective
tissue has to be *supplied* by the plan, because the generator has no access to it.

That is also why this is not a prompting problem. You are not trying to make the model better at
something it is bad at; you are supplying the context it structurally does not have.

---

## 1. The tail defect — lips and body still moving after the line ends

### 1.1 The symptom

A dialogue clip is generated ~1s longer than the spoken line to leave an editorial handle. Over that
extra second the character's **lips keep moving** and the body keeps drifting in unmotivated ways.
Client-reported from production, 2026-08-29.

### 1.2 ⛔ Four causes, and three of them are ours

This is not primarily a model defect. The skill's own rules built it.

| # | Cause | Where it lives |
|---|---|---|
| 1 | **The Path A recipe pads the VO with silence to the clip duration** — so there is a silent region inside an audio-conditioned generation | `ai-generation.md` → the audio-driven recipe, step 2 |
| 2 | **The `[SPEECH]` block instructs continuous mouth movement, unscoped** — *"never holds a single frozen mouth shape"* applies to the whole clip, silence included. We are **asking** for the defect | `ai-generation.md` → the audio-driven recipe, step 5 |
| 3 | **The handle rule asks for +1–2s past the line**, making that instructed-to-move silent region **20–30% of the clip** | `ai-generation.md` → "Editorial handles" |
| 4 | **The model peaks in its final second and never eases out** (measured: tail motion at 53–83% of clip peak) — so the handle is where the model is *most* active | `timing-and-performance.md` §5 |

**The first fix is therefore a deletion, not an addition.** Removing an instruction that asks for
mouth movement over silence is a different and far more reliable act than adding one that asks for
stillness — and the evidence below says the second one does not work.

### 1.3 What the model side actually supports

**Every vendor that addresses duration mismatch says the opposite of padding.**

- Sync.so exposes a `sync_mode` with a literal `silence` option — *your workflow, formalised* — and
  its own quality guidance still says: **"Match audio and video duration. For the most predictable
  results, keep audio and video durations close to each other."** [PRIMARY · sync.so docs · checked
  2026-08-29]
- Luma: keep lengths **within 20%** of each other, and `Cut Off` mode is recommended for **"clean
  endings, precise timing control."** [PRIMARY · Luma lipsync guide · checked 2026-08-29]
- Everypixel, the only vendor naming trailing silence as a *cause*: **"Trim silence from the start
  and end of your voiceover before uploading."** [PRIMARY · Everypixel Workroom lipsync
  troubleshooting · checked 2026-08-29]
- ImagineArt: *"If your script is 4 seconds of speech, selecting a 10-second model will result in
  silence or padding at the end."* [PRIMARY · ImagineArt docs · checked 2026-08-29]

**Nobody documents what the model does over the silence.** Not one provider. That is the finding, not
a gap in the search: Hedra's page was grepped for `silen`/`idle`/`pad` and returned zero hits, and
the same absence holds across Runway, Luma, Higgsfield, Wan, Seedance and Sync.

**Why the model has no idle behaviour — sourceable, as an inference.** Training corpora for this
model class are explicitly filtered to remove non-speech material:

- TalkVid: *"using transcript timings, we remove segments without speech events."* [PRIMARY ·
  TalkVid, arXiv:2508.13618 · checked 2026-08-29]
- Wan-S2V: excludes videos where *"no active speaker exists in the scene."* [PRIMARY · Wan-S2V,
  arXiv:2508.18621 · checked 2026-08-29 — the paper contains zero instances of "silence" or "pause"]

⛔ **Write it as an inference, not as the authors' claim.** What is documented is the filtering. "The
model therefore has no idle prior" is our conclusion from it — well supported, and still ours.
Corroborating from the other direction: OmniHuman-1.5 advertises characters that *"seamlessly
transition between speaking and idle states"* as a **new capability**, which is indirect evidence
that its predecessors do not. [PRIMARY · arXiv:2508.19209 · checked 2026-08-29]

**⛔ And the prompt-side fix is reported not to work.** Wan2.2 issue #77 — a character *"appears to be
talking, even when the prompts explicitly instruct 'no talking' or 'mouth closed'"*; multiple prompt
variations tried, **open with zero replies**. [PRIMARY-ARTIFACT · github.com/Wan-Video/Wan2.2 issue
#77, user-authored · checked 2026-08-29] On HeyGen, a producer asking how to freeze an avatar over
muted audio had already set the calm motion style and it was insufficient. The one workaround anybody
reports having tried is from Wav2Lip: **replace the silence with a quiet vocalisation** — unconfirmed
by anyone else, and mechanically specific to retalking. [PRIMARY-ARTIFACT · Wav2Lip issue #19 ·
checked 2026-08-29]

⛔ **But our own test contradicts that report, and the difference is instructive.** Directing the
aftermath *did* close the mouth in the §1.4 test (arm D). The reporters in issue #77 were **adding a
prohibition** to a prompt that never asked for mouth movement; our arm A carried an **active
instruction to keep the mouth moving**, and arm D's first act is to take it away. Removing a harmful
instruction is a different operation from adding a hopeful one, and only the first is reliably
within a prompt's reach. **This is the evidence for "the first fix is a deletion".**

**Even so, the ordering stands: structural before verbal.** Do not create the silent region, or do
not ask the clip to cover it. A prompt that works on one model in one test is not a rule.

**A named trigger to take away: mouth-opening words (v2.49; HFF-03).** With native sound on, a word
that opens a mouth is read as speech. A festival team's character talked in a film with no dialogue
until "open-mouth smile" left the prompts; locking closed-mouth expressions fixed it
`[SECONDARY · festival study 2026-11-05]`. It is the same operation as arm D: delete the instruction
that asks for the mouth to move. Since sound is kept by default (`editing-and-audio.md` §7d) the trigger
is live on every clip, not only on dialogue:
- the words: an open mouth, laughing, shouting, yelling, screaming, gasping, cheering, singing,
  talking, speaking, muttering, whispering, a toothy grin;
- write the state through the closed face instead: a held smile, lips pressed, a breath out through the
  nose, the eyes doing the work; and say "mouth closed" in `[PERFORMANCE]` when no line is scripted;
- `prompt_lint.py` WARNs on those words in `[PERFORMANCE]`, `[ACTION TIMING]`, `[SHOTS]` and `[FIRST
  FRAME]` of a scene-form clip when sound is on and no line is scripted, unless the word is negated
  ("no talking" passes). It does not read the frame-led i2v blocks; there the rule is manual.

### 1.4 The one untested affordance worth a bake-off

Several roster models accept `start_image`, `end_image` **and** `audio_references` in the same call
— MiniMax H3, Seedance 2.0/2.5, and others. [PRIMARY · live model catalog, read
2026-08-29] So a **closed-mouth, settled end frame is expressible alongside the audio.**

Given yesterday's finding that **the frame pair supplies the geometry and the prompt supplies the
action** (`motion-design.md` §2.1), an end frame showing the mouth closed and the pose settled is the
most promising candidate fix in this file.

**✅ Tested 2026-08-29 — it works.** Four arms, same start frame, same VO, 1080×1920, 60.3 credits
(a close-out note of 2026-08-29 on the tail after a line [studio history]).

⛔ **Read the provenance before you rely on this.** The test ran on **a model that went off the
approved roster hours later** (`ai-generation.md` § The approved video-model roster). The *mechanism*
below is model-independent — a padded silent tail on a model with no idle state, plus a prompt that
asks for continuous mouth movement — and the corrected default (generate to the line) rests on vendor
guidance and craft, not on this test. But **the two fixes are verified on a model that is no longer
in use**: re-run the A-vs-C arms on `minimax_h3` or `seedance_2_5` before treating "the end frame
closes the mouth" as settled on the current roster.

| Arm | Setup | The tail, by eye at 0.25× |
|---|---|---|
| **A** | 6s, audio padded, **unscoped** `[SPEECH]` — the old default | ⛔ **The defect, reproduced.** Lips keep re-forming over the silence — pressing, tucking, corners pulling — while the head sits frozen |
| **B** | 5s, generated **to the line** | No tail to fail. The reference case |
| **D** | 6s, audio padded, **scoped** `[SPEECH]` + a directed aftermath | Mouth closed and stable; head turns away and down |
| **C** | 6s, padded, scoped + **closed-mouth end frame** | Mouth closed and stable, and the head settles into a composed end frame — the cleanest tail |

**Both fixes held.** The end frame did what §4 asks of an exit: it produced an *arrival* rather than
a stop. ⛔ But note what A actually looked like: **a frozen head with a working mouth** — the body
settled and the lips did not. That is the signature to look for, and it is worse than either fault
alone, because the stillness makes the mouth the only thing moving.

⛔ **Limits, stated plainly.** One generation per arm, one model, one line, one subject. A and D
differ in three textual respects at once (the `[MOTION] END:` beat, the `AFTER:` line, and the
scoping of `[SPEECH]`), so the test shows *directing the aftermath* works — it does **not** isolate
the deletion from the added instruction. A fifth arm carrying only the deletion would settle that.

---

## 2. The handle rule, corrected

### 2.1 ⛔ We imported an audio-post convention as a picture spec

The skill's handle rule traces to dialogue-editing practice, where a handle is:

> *"extra material before and after each cut, needed for crossfades and ADR-replacement-room
> flexibility. Standard is ~2 seconds; sometimes more."*

[PRIMARY · Purcell, *Dialogue Editing for Motion Pictures* — via a local extraction, read 2026-08-29
· ⛔ **weak provenance**: the extraction has zero page markers and self-labels every framework
"Verified" while citing nothing. Treat the 2s as a convention, not a measurement]

Read what that handle is *for*: **crossfades and ADR room.** It is a margin on an audio file so the
dialogue editor's tools have material to work with. It says nothing about what should be **visible**
in those frames, and it is not a licence for a character to keep existing on camera after the line.
**Applying it as a picture spec is a category error** — ours, not the source's.

The picture-side equivalent is a different practice with a different content requirement. Brown's
continuity-of-movement discipline: **"overlap the action — let the previous shot run past the cut
point; start the next shot before the action begins."** [PRIMARY · Blain Brown, *Cinematography:
Theory and Practice* — via a local extraction, read 2026-08-29]

**That is overlap OF THE ACTION, not padding after it.** A live-action handle contains continuing
performance the camera happened to record. A generated handle contains whatever the model invents.
The two are not the same object, and the rule transferred by analogy rather than by mechanism —
exactly the error class that produced the FLF mistake.

### 2.2 The corrected decision

**Default: generate the dialogue clip to the length of the line, and get the handle somewhere else.**

Where the handle is genuinely needed, ranked by reliability:

| # | Where the handle comes from | Cost | Notes |
|---|---|---|---|
| 1 | **The next shot's head** — cut in early on the incoming clip | free | Every i2v clip already opens with ~0.4s of near-static settle you were trimming anyway (`timing-and-performance.md` §5) |
| 2 | **A J- or L-cut** — the next clip's audio starts under the outgoing picture, or this line runs under the incoming picture | free | The tail is never seen. §7 |
| 3 | **A cutaway or insert** | one cheap B-roll clip | What B-roll is *for* in a dialogue sequence (§6) |
| 4 | **A separate silent settle/reaction clip** | one short silent generation | No audio conditioning at all, so no invented speech. Also buys the listener coverage the coverage floor already asks for |
| 5 | **A designed aftermath inside the clip** (§3) | +1s of generation | Only where the beat genuinely belongs to this shot — and only with the `[SPEECH]` block scoped |
| 6 | **A tail ramp or freeze-settle in the edit** | edit time | `timing-and-performance.md` §7 |

⛔ **Only options 5 and 6 involve the model in the tail at all**, and only 5 costs generation credits.
The first four are the ones to reach for.

**Where a dissolve or pack transition genuinely needs frames on both sides** (`editing-and-audio.md`
Transitions), the handle requirement is real — but it should be satisfied by a **silent** clip, a
B-roll insert, or a designed aftermath, never by extending an audio-conditioned dialogue clip past
its line.

---

## 3. The aftermath — the word the shotlist was missing

> *"Most actions need three stages — **anticipation, action, aftermath** — so a single beat
> ('someone picked something up') becomes a small series of frames."*

[PRIMARY · Glebas, *Directing the Story* — via a local extraction, read 2026-08-29]

**Aftermath** is the only term in the craft corpus that names post-beat frames as a *plannable stage*
rather than leftover time. It replaces "handle" in the vocabulary of this skill, because it is
something a generator can be told to render and a reviewer can be told to check.

Pearlman supplies the same shape at the level of movement: the unit is a **movement phrase** — *"a
span of movement with a shape — a beginning, a build, and a resolution"* — and the named anti-pattern
is *"cutting mid-phrase without intent, leaving movements unresolved and the cut feeling 'off'."*
[PRIMARY · Pearlman, *Cutting Rhythms* — via a local extraction, read 2026-08-29]

**So the tail is the resolution of a phrase, not dead space with a body in it.**

### 3.1 What an aftermath contains

One beat, silent, motivated, and belonging to *this* character in *this* moment:

- the mouth **closes and stays closed**
- a breath out, or a swallow
- the gaze moves once — to the object, to the other character, down and away
- a settle: weight shifts back, shoulders drop, the hand comes to rest
- a prop action that finishes the thought — setting the bottle down, closing the folder

Written into the prompt as the `[MOTION] END:` beat and the new `AFTER:` line of the performance card
(`direction.md` §1). ⛔ **Name it as content and register, never as a duration** — no roster model
honours a frame count (`timing-and-performance.md` §6A).

### 3.2 What an aftermath is not

- **Not "held motion".** The skill previously said the handle could be "+1–2s of held motion". With
  a talking-head prior, "held" does not mean "not talking" — that is precisely the gap the model
  fills with invented speech.
- **Not silence on the audio track.** Purcell's continuity standard: *"Continuity of room tone — the
  ambient sound of the room is consistent across cuts. **Gaps that don't have room tone read as
  'dropped out'.**"* [PRIMARY · Purcell — via a local extraction, read 2026-08-29 · weak provenance
  per §2.1] A tail delivered as digital silence is a second defect on top of the first. Room tone
  under the aftermath is an edit-side requirement (`editing-and-audio.md`).
- **Not a second emotional beat.** One beat per clip still holds (`direction.md` §1). An aftermath
  that introduces a new state is a new shot.

---

## 4. The exit — what a shot owes the next one

⛔ **Honest finding first: the craft literature has almost no doctrine treating a shot's final frames
as a designed object.** Fourteen extractions were searched. Every author frames the exit
*bilaterally*, as a property of the join, with one exception. Do not expect this section to be
richer than it is, and do not invent the missing half.

**The one genuine exit doctrine is Ward's, and it is about camera movement:**

> *"Movement must start and stop on the action and be motivated, **or it reads as restless**."*

with the test that the move *"is invisible — it starts and ends on action, holds its pivot, and
**arrives at a composed end frame**"*, and the instruction to *"anticipate the final frame before the
move ends."* The named anti-pattern is continuous small reframes to cover unrehearsed action — *"an
irritant that detracts from content."* [PRIMARY · Ward, *Picture Composition for Film and Television*
— via a local extraction, read 2026-08-29]

**"Motivated, or it reads as restless" is the diagnosis of §1 in the literature's own words** — and
it was written about a camera operator, not a model. *Arrives at a composed end frame* is exactly
what an audio-conditioned clip generated past its line does not do.

**The itemised join checklist — the only one in the corpus**, and written to be satisfied *at the
moment of recording*, which is the part of the process this pipeline actually controls:

> every shot is conceived in relation to its intended preceding and succeeding shots, and the
> conditions for an unobtrusive cut are **met at the moment of recording**. A cut is unobtrusive when
> intercut shots match in **size, headroom, looking space, lens angle and height**, are
> **colour-matched**, carry **continuity of action and movement**, and show a **significant change of
> angle/size or content** when cutting on the same subject.

[PRIMARY · Ward — via a local extraction, read 2026-08-29] Ward's summary of the failure: *"garbage
in equals garbage out."*

And the director's obligation, stated as a deliverable — a coherent **"kit of parts"**: performances
with the words in order, shots that tell the story and the geography, **clear entrances and exits**,
and the inserts that let the editor point things out. Shot selection *"should imply a cutting order
even if the editor departs from it."* [PRIMARY · Leandro, *The Art of Directing* — via a local
extraction, read 2026-08-29]

**⛔ What no source specifies** — so the skill does not either: where a subject should be *looking* in
a shot's last frames as a designed handoff; an energy value written onto an outgoing shot; and any
number for how many frames after the last word a cut should land. Screen-direction and eyeline
doctrine is abundant and unanimous, but it governs continuity *across* the cut, not the exit itself.

---

## 4b. ⚡ Motion planned for the cut — a shot generated to hand off

Author, 2026-10-26: *"We can also plan motion in one shot, to naturally enhance the transition."* §4
says the literature treats the exit as a property of the join. In this pipeline the join cannot be
found later in the footage, because there is no coverage to find it in. So the motion that carries
the join is **written into both clips before either is generated**, and measured before lock.

**Three optional fields on the clip prompt** (the template in `prompt_lint.py --template clip`):

| Field | On | What it says | Example |
|---|---|---|---|
| `exit:` | the outgoing clip | the screen direction of what is still moving in its last frames | `right, the jar leaving frame` |
| `enter:` | the incoming clip | the screen direction of what moves in its first moments after the lead-in | `from left, the hand in` |
| `join:` | the outgoing clip | how it hands off | `motion-match` · `match-on-action` · `whip` · `graphic-match` · `camera-carry` · `flip` |
| `prelap:` (3.2.0) | the outgoing clip | the next shot's sound starts this early, before the cut (0.25–1.0 s), named by its event's read word or id in the next shot's read | `0.5s, knock, side=right` |

They are §5's IN / OUT / JOIN written as data, so a script can check them. A direction is screen
direction: left, right, up, down, toward or away from the lens.

**The hand-offs, and what each clip must be generated to carry:**

- **Motion match** (vector continuity, Dmytryk in §7). A's subject is still moving in its last
  frames, and B's subject is already moving the same way at frame one. A's MOTION `END:` keeps the
  movement running ("still sliding right as the clip ends"), not a settle. B's start frame is caught
  mid-movement (`caught:` and `travel:`, `motion-craft.md` §6c) with room ahead in the direction of
  travel. The cut lands while both are moving.
- **Match on action.** One action is split across two sizes or angles: A carries the anticipation
  and the commit, and B carries the contact and the consequence. The cut frame is chosen in the edit
  from `action_points.py`'s commit point (`editing-and-audio.md`, Action points), not written in the
  prompt. B's start frame is the action's mid-point at the new size, the same pose and the same hand.
- **Whip.** A ends on a fast camera move and B starts on the same move in the same direction, and the
  cut goes inside the blur. ⛔ **[UNTESTED on this roster]**: whether today's image-to-video models
  render a clean whip from a still has not been measured here. Try one pair before you plan a sequence
  on it.
- **Graphic match.** A's last composition and B's first share a shape at the same screen position.
  B's frame prompt places its subject where A's ends. `shot_graph.py` measures the eye jump across the
  cut, so a mismatch shows up as a jump.
- **Camera carry.** The camera move continues across the cut, with the same kind, direction and
  speed. Plan it with the same `[CAMERA]` wording on both clips. `shot_graph.py camera_path` measures
  both.
- **Flip.** A deliberate reversal: join by opposites, left-moving to right-moving (Miller in §7).
  `join: flip` says it is meant, so neither the lint nor the check flags it.

⛔ **Not planned in the ads lane:** foreground wipes (an object crossing the lens to hide the cut).
The 2026-10-26 jury killed them as unreliable from image-to-video (M13 in
the intent and emotion proposal of 2026-10-26 [studio history]), and the alternative is roto, which this
skill does not do. In drama they need the owner's sign-off per shot.

**What the checks do:**

- `prompt_lint.py` warns when a motion `join:` has no `exit:`, when an `exit:` or `enter:` names no
  screen direction, and when a motion hand-off's `END:` line settles.
- `motion_qa.py clip` measures each clip's subject direction as it enters and exits, its main
  action's direction, and its camera, and reports where they differ from `enter:`, `exit:`, the frame's
  `travel:` and `[CAMERA]`. With `cut:` on the prompt it reads the in point and the cut inside the
  clip (lead-in, then lead-in + cut), not the clip's own ends.
- **A particular object** (the jar, the cup) is followed when the director boxes it on the start
  frame: `track: jar=0.42,0.55,0.12,0.20` on the clip prompt, or `--track` on the command. The box is
  fractions of the frame from the top-left. The report gives the object's path, its direction, where it
  is at the cut, and whether it leaves the frame. Across a planned motion or graphic match, `motion_qa.py
  cut` names an object that jumps more than a quarter of the frame or reverses. This is a tracker, not
  roto: it gives a position, not a matte.
- `motion_qa.py cut` measures every join of the assembled cut (`shot_graph.py`: screen direction kept
  or flipped, the eye jump, colour, exposure). It reports a planned hand-off whose directions disagree
  without `join: flip`, and a motion hand-off that flips on screen.
- `gate.py approve lock` **refuses** while any shot in the cut has no current motion report, or the
  newest cut has no joins report. This was the house decision, 2026-10-26: *"Refuse picture lock
  without it"*.

⛔ **What a finding is.** A finding is a question for the director, not a verdict. The direction
threshold is [assumed]. On a moving camera, a large subject can be taken for the camera, and when the
whole clip reads locked the camera is held at zero for this reason. A model may also ignore `exit:`,
so watch the clip before you cut it. Only a missing or stale report refuses lock. A finding never
does.

---

## 5. The handoff contract — the fields that go in the shotlist

Four fields per shot, decided at the storyboard, because they are generation instructions and cannot
be added later.

```
[HANDOFF — Shot N]
FUNCTION: <what this shot does for the sequence — from the enum in §6 for inserts;
           for dialogue: carries line X / reacts to line X / lands the claim>
IN:       <state at frame one: pose, gaze, energy; what it inherits from shot N-1>
OUT:      <state at the last frame: the composed end frame — pose, gaze, where motion
           has come to rest, and for a dialogue clip the AFTERMATH beat (§3)>
JOIN:     <how N connects to N+1: hard cut on action / J-cut (audio leads) /
           L-cut (audio trails) / cutaway / dissolve — and what carries across:
           motion vector, gaze direction, screen position, energy>
```

**Why these four and not more.** They are the fields the literature actually specifies. Ward gives
the match list for IN/OUT; Leandro makes entrances and exits a deliverable; Reisz/Millar and Dmytryk
supply the FUNCTION gate (§6); the JOIN palette is §7.

⛔ **Durations are deliberately absent from this contract.** The best-triangulated pacing finding in
the corpus is an argument *against* fixed numeric cut rules: *"it's not math, it's poetry"*, with the
named anti-pattern of *"trying to cut to a fixed rule (e.g., always on beat four, or **always X
frames**) instead of to the felt rhythm and the performance."* [PRIMARY · Hullfish, *Art of the Cut* —
via a local extraction, read 2026-08-29] The skill specifies **function, motivation and exit state**,
which the literature does specify, and leaves durations to the cut.

**Where this is decided is itself contested, and the disagreement is kept:**

- **On paper, before anything rolls.** *"Most filmmaking problems are solved on paper… before any
  camera rolls"*; the anti-pattern is *"we'll figure it out on the day"*; and the thesis: *"instinct
  without the grammar produces footage that won't cut."* [PRIMARY · Katz, *Film Directing Shot by
  Shot* — via a local extraction, read 2026-08-29]
- **In the cut, and it cannot be pre-specified.** Pearlman insists the edit's rhythm is discovered in
  the cutting room and *cannot be fully pre-specified*; Hullfish's whole thesis is that *"editing is
  the final rewrite."* [PRIMARY · Pearlman; Hullfish — via local extractions, read 2026-08-29]
- **In pre-production, jointly with the editor** — the minority position, and the one this pipeline
  resembles: *"Editors are sometimes assigned, during pre-production, to design such transitions with
  the cinematographer and director."* [PRIMARY · Miller, *Developing the Editor's Eye* — via a local
  extraction, read 2026-08-29]

⛔ **Do not resolve this in the skill's favour.** The honest position: **this pipeline has no
cutting-room option for anything that must be generated**, so the exit and the join move upstream by
necessity, not because Katz is right and Pearlman is wrong. What genuinely stays in the edit — cut
frame, shot length, rhythm — should stay there, and §5's contract deliberately does not touch it.

---

## 6. B-roll — a function, or it does not get made

### 6.1 The gate

> *"Any rough cut should be assessable for what editing has added. **If the answer is 'the shots are
> in order,' the editing work hasn't started.**"*

[PRIMARY · Reisz & Millar, *The Technique of Film Editing* — via a local extraction, read 2026-08-29
· ⛔ partial extraction, zero page markers]

And Dmytryk names our exact failure mode in his list of **invalid** reasons to cut: **"coverage
anxiety — 'We have it so let's use it.'"** His rule: *"for every cut in your timeline, articulate the
reason in one sentence. **Cuts whose reason is 'I don't know' are wrong cuts.**"* [PRIMARY · Dmytryk,
*On Film Editing* — via a local extraction, read 2026-08-29 · ⛔ zero page markers]

**The house rule: every insert carries a FUNCTION from the enum below, written at the storyboard. An
insert whose function is "there was a hole in the timeline" is not made.**

### 6.2 The function enum

Assembled from five authors; no single source supplies a taxonomy.

| Function | What it does | Source |
|---|---|---|
| **Evidence** | Shows the thing the line claims — the product working, the meter, the bill | House (the ad case of "manage information release") |
| **Compress time** | Removes the connective tissue between two moments | Reisz & Millar |
| **Construct space** | Builds a geography no single shot contains | Reisz & Millar |
| **Manage information release** | Controls *when* the viewer learns something | Reisz & Millar |
| **Contrast** | Cutting between drastically different shots forces a comparison | Miller (Pudovkin) |
| **Parallelism** | Unites elements separate in time or space by formal or thematic match | Miller (Pudovkin) |
| **Symbolism** | A cut that creates a metaphor | Miller (Pudovkin) |
| **Crosscut / simultaneity** | Alternates concurrent actions | Miller (Pudovkin) |
| **Leitmotif** | A repeated visual bound to a theme — the series-level tool | Miller (Pudovkin) |
| **Hide-to-reveal** | Replaces an expensive on-screen event with its reaction, sound or consequence. Test: *"the withheld element is clearly framed as absent (the viewer feels the gap), not merely missing by accident"* | Mahaffy |
| **Ellipsis** | Cuts the scene between two compositions and lets the viewer fill it. Test: *"viewers can reconstruct the skipped event from the framing on either side"* | Mahaffy |
| **Extend or compress the question** | Delays a resolution to escalate, or answers early to shock and re-raise | Mahaffy |
| **Re-cross the line** | The only legitimate axis-cross without a neutral move | Katz · Glebas |
| **POV object** | The second half of glance → object → reaction. Anti-pattern: an object shot whose direction contradicts the glance | Katz |
| **Rest** | A beat of visual quiet after a dense line — rhythm, not information | Miller (rhythm ≠ pace) |

[PRIMARY · Miller; Mahaffy, *Micro-Budget Methods*; Katz; Glebas; Reisz & Millar — via local
extractions, read 2026-08-29]

### 6.3 ⛔ The hard prohibition — never put the claim over B-roll

> If a piece of information is essential to the story, **play it on the character actually saying the
> line**, because audiences attend to the emotion of a reacting listener and **will miss key plot
> information delivered over a reaction shot**… *"take the hit and stay with the reason you're
> looking at them."*

Anti-pattern: playing a turning-point line over a secondary character's reaction *"to be inclusive,"*
so the audience never registers it. Triangulated across two editors in the source.
[PRIMARY · Hullfish, *Art of the Cut* — via a local extraction, read 2026-08-29]

**For an ad this is the offer, the price, the guarantee and the CTA.** Keep them on the speaker's
face. This outranks cutting rhythm, and it outranks the B-roll coverage floor: a sequence that hides
its own claim under a pretty insert has bought texture with the only line that had to land. It also
outranks the temptation to cover a weak speaking clip with an insert — that is a retake, not a
cutaway (`refinement-loop.md`).

### 6.4 ⛔ A contradiction left standing

**Brown and Rabiger licence exactly the hole-filling this file bans.** Brown's master-scene workflow:
*"shoot cutaways — alternative footage for cutting around problems"*, with the anti-pattern being
*under*-coverage: *"without inserts and cutaways the editor can't cut around continuity errors,
performance variations, or pacing issues."* Rabiger: *"under-coverage forces editors into bad cuts."*
[PRIMARY · Brown; Rabiger — via local extractions, read 2026-08-29]

Against Dmytryk's "coverage anxiety" and Leandro's *"chopping pictures together… like infinite
monkeys at typewriters"*. [PRIMARY · Leandro — via a local extraction, read 2026-08-29]

Both positions are canonical and the skill does not reconcile them. The line that may survive — **not
stated by any of them** — is between *shooting* a cutaway as insurance and *choosing* it in the cut
for no reason. The coverage floor in `direction.md` §3 sits on the Brown/Rabiger side (generate the
insurance); §6.1 here sits on the Dmytryk/Leandro side (justify the cut). Holding both is
deliberate, and it is why the FUNCTION field is required at the **storyboard**, where it is cheap,
rather than at the cut, where it becomes an argument.

---

## 7. The join palette

**J- and L-cuts are the tail's replacement.** Audio leads or trails picture: *"the workhorses of
smooth sound editing."* [PRIMARY · Bowen, *Grammar of the Edit* — via a local extraction, read
2026-08-29 · partial extraction] If the next clip's audio starts under the outgoing picture, **the
defective tail is never seen** — which makes this the cheapest fix in the whole file and the reason
the Transition Plan in the shotlist template already has a J-cut row.

Dmytryk's overlap, the only quantified version: old speaker finishes on their shot → new speaker
begins (audio only) → **~6–12 frames later** the picture cuts → picture and audio sync. His
application: *"for any dialogue scene, default to overlapping at least every other cut"*, with the
anti-pattern *"cutting picture and audio simultaneously on every speaker change… the scene's pace
drags."* [PRIMARY · Dmytryk — via a local extraction, read 2026-08-29] ⛔ **Treat 6–12 frames as
[UNVERIFIED]** — it is the corpus's only J-cut number, from an uncited extraction with no page
marker, and it could not be corroborated. The *practice* is well attested; the number is not.

**Join by opposites — the only rule naming a motion vector.**

> Cut between opposites — dark to light, warm to cool, interior to exterior, wide to tight,
> **left-moving to right-moving action**… the meaning comes from the editorial pairing, not the shots
> themselves.

Anti-pattern: *"cutting between two visually identical frames, producing a flat or jarring join."*
[PRIMARY · Miller — via a local extraction, read 2026-08-29] For a 9:16 batch this is also the
antidote to V14 (identical framing across the batch, `realism-qa.md`).

**Vector continuity for the mid-motion cut.** Since generated clips end mid-motion by default
(`timing-and-performance.md` §5), the outgoing vector is live at every join: *match the angle of the
action — the movement's vector should continue across the cut, not reverse.* [PRIMARY · Dmytryk —
via a local extraction, read 2026-08-29]

**The sequence has a shape, and it is plottable.** Plot shot durations on a timeline and look at it:
**flat = monotonous · random = chaotic · shaped (rises to a climax, releases to rest) = effective.**
[PRIMARY · Bowen — via a local extraction, read 2026-08-29 · ⛔ the accompanying second-count bands
are extractor-stated; use the shape, not the numbers] And the mechanism that makes this a *generator*
problem specifically: *"a first assembly tends toward a uniform flow"* because each beat is made in
isolation to an internal tempo — *"the fix is to deliberately vary cutting patterns."* [PRIMARY ·
Miller — via a local extraction, read 2026-08-29] A per-clip generator with a fixed default duration
produces uniform flow **by construction**.

---

## 7b. ⚡ The lock catalogue — the continuity failures worth naming before they happen

`[SECONDARY · Higgsfield production prompt corpus, supplied 2026-09-18 · derived from what a working
house style spent whole blocks preventing]`

Every prompt in that corpus ends with a block of invariants, and the same handful recur across
unrelated scenes. That recurrence is the evidence: these are **the drifts a model commits often
enough to be worth a named counter**. Two rules of form, before the list:

- **State the lock POSITIVELY — the desired state, not the forbidden one.** "Exactly three riders"
  beats "not two and not four"; "the case stays flat on the sand, lid closed, button unpressed"
  beats "he does not press the button". A negative names the thing (`prompting-craft.md` §5).
- **A lock costs a demand** (§2.2 there). Four restatements of one invariant is four demands buying
  one. Pick the two or three that this shot can actually break.

| Lock | What drifts without it | The form that works |
|---|---|---|
| **HEADCOUNT** | crowds breed; a three-rider pack arrives with four, or two | *"exactly THREE riders on exactly THREE ostriches — three in the hollow, three in the launch, three exiting frame, the same three in every shot"* — the count, then the count again per beat |
| **DIRECTION / AXIS** | the 180° line flips between cuts and two people stop facing each other | name the line and which side the camera lives on: *"every camera stays on the TV-wall side of the A–B line; A always reads looking frame right, B toward frame left"*. Tie the run direction to the sightline: *"his run direction is identical to his binocular sightline"* |
| **STATE / WARDROBE** | a change reverts between frames — statelessness, `character-and-props.md` §8.4 | ⛔ **this one is not a lock, it is an asset.** Author the AFTER state as its own reference (`prompting-craft.md` §11d); the timeline is the record, the asset is the enforcement. A lock alone does not hold it — the corpus proved that four ways and then switched to an asset |
| **OUTCOME / ORDER** | the model resolves a withheld outcome in the hero's favour — the hand reaches the prize | fix the order AND give the mechanism: *"the storm reaches the man BEFORE the man reaches the case … his dive launches from eight meters out and covers two"* |
| **OBJECT IDENTITY** | a drawn map, a label, a logo re-invents itself per frame | *"the drawing stays identical in every frame: red X on the two-palm island, dashed line from the drawn ship, compass cross top-left"* — name the marks, not "the same map" |
| **PROP POSITION** | an object moves when nobody moved it | *"every object keeps a stable shape and identity across frames, moving only when his hands move it"* |
| **ONER** | an unrequested cut appears inside a continuous take | *"ONE CONTINUOUS SHOT with zero internal cuts; the first cut lands exactly at 12.0s"* — and say the camera does not cut on its own |
| **OPENING** | the reveal happens before the establishing beat; a subject appears in frame one | gate it on the state, not the clock: *"the crest is EMPTY the entire reveal; the hand enters only after the air has cleared"* |
| **CONSEQUENCE** | a physical event implies contamination the shot does not want — sand in a mouth, water on a lens | name where the effect goes and where it does not: *"sand falls only from the outside of his clothing; every cough and the scream release only clear air"* |
| **PRESENCE** | a live element quietly vanishes when it stops being the subject | *"the macaw stays perched on the dome — visible, alive, feathers ruffling, never flying off and never absent — in every shot where the cage is visible"* |
| **SCALE** | a hand prop grows to the size of the hand holding it | give it in centimetres AND in relation: *"palm-sized, roughly 8 × 8 × 4 cm, its full footprint resting within her open palm"* |

⛔ **The lock is the last line of defence, not the first.** Anything a reference can carry should be
carried by a reference; anything the edit can fix should be fixed in the edit. A lock is for what
only the prompt can hold — count, direction, order and presence — and every one you write is a
demand you are not spending on the picture.

## 8. What to do on this roster, today

1. **Generate dialogue clips to the length of the line.** Not longer. The vendor consensus, the
   craft reading of what a handle is, and the client-reported defect all point the same way.
2. **Scope the `[SPEECH]` block to the spoken window** and stop instructing continuous mouth
   movement across the whole clip (§1.2 cause 2). This is a deletion, it is free, and it **measured
   as effective** in the §1.4 test — which does not make it a substitute for item 1.
3. **Take the handle from the join, not from the generation** — §2.2, options 1–4.
4. **Write the four HANDOFF fields at the storyboard** (§5), including an AFTERMATH beat for any
   clip that genuinely needs one.
5. **Give every insert a FUNCTION** from §6.2, and keep the claim on the speaker's face (§6.3).
6. **Where a shot must land**, manufacture the settle in the edit — `timing-and-performance.md` §7.
7. **Supply a closed-mouth end frame** on any clip that must carry an aftermath — tested and the
   cleanest result of the four (§1.4). It costs one image and it is the only arm that produced a
   composed end frame rather than a stop. ⛔ Re-check it on any other model before assuming it
   transfers; it is one test on a since-retired model.

**Note on why these are easy to adopt:** items 1–5 need no extra generation — item 1 *removes*
generated seconds. ⛔ That is a convenience, not the argument. The argument is that a padded tail
produces invented lip movement over silence; the fix would be right at twice the price
(`ai-generation.md` → the quality floor).

---

## 9. QA and tooling

`scripts/clip_qa.py --line-ends SECONDS` (or `--auto-line-end`, which finds the last speech using
ffmpeg `silencedetect` on the clip's own audio) measures the post-line window and reports how much
motion is in it.

⛔ **It does not catch this defect, and the test proved it.** On arm A — the clip with visibly
working lips — the post-line window measured **15.4% of clip peak** and the tool called it
`SETTLES`; it flagged only a dead zone, which was the *head* freezing. Restricting the same measure
to a mouth crop, with and without global-motion compensation, did not separate the arms either.
**Whole-frame motion energy cannot see a lip.** The gate finds a *busy* tail, which is a different
and also real fault. The mouth is an eye check at 0.25×, and nothing in this skill replaces it.

Add to the per-clip card in `realism-qa.md` §6:

- [ ] **Clip length matches the line** — or the extra seconds carry a *designed aftermath*, not a
      handle
- [ ] **Mouth is closed and still after the final word** — checked at 0.25×, not from a contact sheet
- [ ] The last frame is a **composed end frame**: pose settled, gaze placed, motion at rest (Ward)
- [ ] The shot's **HANDOFF card** is satisfied — FUNCTION, IN, OUT, JOIN (§5)
- [ ] `motion_qa.py clip` has measured the selected take, and every finding is answered (§4b). Picture
      lock refuses without the reports.
- [ ] Every insert in the sequence has a **FUNCTION** from §6.2, and no claim plays over B-roll

---

## 10. What this file cannot tell you

- **How long a handle should be.** The only figure in the corpus is Purcell's ~2s, it is an *audio
  conform* convention, and it comes from the weakest-provenance file in the set. **If you ship a
  number here it is yours, not the literature's.**
- **How many frames after the last word a cut should land.** No source, anywhere. The corpus contains
  seven numeric claims in total and not one is about the tail after a line.
- **What physically happens in the frames after a spoken line ends.** No breaths, no mouth closing,
  no settle — the concept is genuinely absent from the craft literature. §3 assembles it from
  Glebas's "aftermath" and Pearlman's phrase resolution; that assembly is ours.
- **Whether the closed-mouth end frame works** (§1.4). Untested, and the prompt-side equivalent is
  reported not to work.
- **What any model does over silence.** No vendor documents it. The training-filter inference is
  well-supported and still an inference.
- **Whether Kling's own lip-sync documentation says anything** — its docs are client-rendered and
  could not be read; the roster facts come from the live catalog and from schema mirrors.
- **Short-form calibration for any of the craft above.** Five separate extractions flag this as an
  open question in their own words; nothing in the corpus is calibrated to a 5–6 second clip.
- **The load-bearing absence:** Murch's *In the Blink of an Eye* is cited by ten books in the corpus
  and extracted by none. This skill has Murch second-hand in `editing-storytelling.md` §1; the
  primary is the highest-value acquisition for exactly this problem.
