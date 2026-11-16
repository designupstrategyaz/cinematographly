# Emotional journey — mapping feeling across the piece, the shot and the frame

**When to read this:** you are planning a piece and can name what happens but not what it *feels*
like; a sequence is technically fine and emotionally flat; you are choosing B-roll, props, a set or
a transition and want it to do more than fill; or your reference frames keep coming back as strong
expressions on vacant faces. `script-craft.md` builds the beats, `direction.md` directs one moment,
`editing-storytelling.md` explains what a cut does, `production-design.md` and
`character-and-props.md` decide what is in frame. **This is the layer that connects them: the shape
of feeling, and which instrument moves it.**

Source tiers follow `research-quality.md`. Craft sources read **2026-08-29** from the local film
corpus; papers and vendor docs checked **2026-08-29**. ⛔ Several extractions used here are weak
(v3.0, no page markers, self-labelled "Verified" citing nothing) and are flagged inline; numbers
from those are not propagated.

---

## 0. The honest headline — film never drew this chart

**No author in the film corpus plots emotion on an axis.** Twenty-five extractions were searched.
Pope plots *tension* against time (Theory Charts #1–#4, real published figures with page numbers).
Bowen plots *shot duration*. McKee's value charge is a per-unit label, not a curve; Cowgill's is a
three-state score used as a distribution check. **Nobody plots feeling, and nobody supplies units
for it.** [PRIMARY · Pope, *Good Scripts, Bad Scripts*; McKee, *Story*; Cowgill, *The Art of
Plotting*; Bowen, *Grammar of the Edit* — via local extractions, read 2026-08-29]

The emotion curve with faces, quotes and pain points is a **service-design import** — and the loop
closes on itself: that artifact was built by importing Campbell's inner journey and Vonnegut's
"shapes of stories" into UX. Story craft → service design → back to story craft.

**Why film never needed it, and why this pipeline does.** Film assumed a human editor was *feeling*
the piece in the room — Pearlman's kinesthetic empathy, "editors perceive rhythm by mirroring the
footage's movement in their own bodies." [PRIMARY · Pearlman, *Cutting Rhythms* — via a local
extraction] A per-shot generator has no body to mirror with, and each shot is authored in isolation
from its neighbours (`shot-handoff.md` §0). **The chart is not a foreign method being imposed on
film craft; it is the part of the job the room used to do implicitly, written down because there is
no longer a room.**

⛔ **So do not ship a 1–10 emotion scale as if it were sourced.** Nothing in the literature supplies
magnitude. What is sourced is a *polarity on a named antonym pair* (McKee), a *ternary outcome
score* (Cowgill), and an *ordinal tension height* (Pope). Use those.

---

## 1. Two curves — and the easy one is the wrong one

⛔ **The emotion the character has and the emotion the viewer has are different quantities.** This
is the distinction the whole file exists to police, and it is the one a generator gets wrong by
default, because a generator can only put feeling on a face.

**The viewer's curve is the one being designed.** Glebas's seven-step model of what a viewer's mind
does — attend, perceive, read the signs, connect into meaning, **predict**, **worry about the
characters**, **feel closure** — has three steps at the end that *no character can perform*. They
are emotions only a viewer can have, and they arise from the structure of what is withheld, not
from anyone's expression. The load-bearing line is quoted in the extraction: **"Meaning
automatically evokes emotions."** [PRIMARY · Glebas, *Directing the Story* — via a local extraction,
read 2026-08-29] So **engineering understanding is engineering feeling.**

**Four documented mechanisms where the two curves diverge**, cheapest and strongest first:

| # | Mechanism | What it does |
|---|---|---|
| 1 | **Dramatic irony** | The viewer knows what the character doesn't. *"Whoever has knowledge also has power."* A calm face produces maximum dread if the viewer holds the thing the character lacks. Test (Cowgill): at each beat you can state the gap between what the audience knows and what the characters know |
| 2 | **Kuleshov** | The emotion is not in the face at all. The same neutral face reads as hunger, grief or affection depending on the next shot; *"reversing two shots inverts the emotional meaning"*. Mahaffy: meaning arises *"not within any single image"* — the push-in on an expressionless mask works because **viewers do the emotional work** |
| 3 | **Counter-emotional performance** | The character plays the opposite — *Gelsomina laughing, not crying*. Favour complex over one-note readings |
| 4 | **Withdrawal** | Remove the cue and the viewer supplies more. The *Titanic* finale where the score withdraws; the anti-pattern is cues that *"tell you how to feel"*. Test: pulling the music doesn't expose a hollow cut |

[PRIMARY · Glebas; Cowgill; Mahaffy, *Micro-Budget Methods*; Miller, *Developing the Editor's Eye*;
Hullfish, *Art of the Cut* — via local extractions, read 2026-08-29]

⛔ **Putting the feeling on the face is the fifth mechanism and the weakest — and it is the one this
pipeline is worst at** (§4). Reach for 1–4 first. Every one of them is cheaper: irony is a script
decision, Kuleshov is an insert, withdrawal is a deletion in the mix.

---

## 2. The map — what actually goes on it

### 2.1 The two rows that come from a real test

Glebas's own verification test is already a two-column emotional map, and it is the closest thing in
film to the artifact: **"you can name, for each beat, the narrative question the audience is holding
and the emotion you intend."** Its sibling: **"name the intended emotion and the closure beat; if
you can't, the sequence has no destination."** [PRIMARY · Glebas — via a local extraction]

Those two rows — **open question** and **intended viewer emotion** — are the spine. Everything else
is optional detail.

### 2.2 The charge, and the flat-stretch diagnosis

**McKee's value charge**: a scene turns a value from `+` to `−` or back, on a **named antonym pair**
(trust↔doubt, worry↔relief, alone↔seen). Every level of the hierarchy turns — beat, scene, sequence,
act. Test: *the value charge at the end differs from the start.* A unit that turns nothing is a
**non-event**: cut it or rewrite it. [PRIMARY · McKee, *Story* — via a local extraction · ⛔ that
extraction is a sampled read of a scanned PDF; treat as canon-consistent, not verified against the
page]

**A flat stretch has three different causes and three different fixes** — diagnose before you fix:

| Symptom | Cause | Fix |
|---|---|---|
| Nothing turns | A non-event (exposition wearing a scene's clothes) | Cut it, or make it turn |
| Turns, but always the same way | Conflict plateauing at one intensity | Cowgill: vary the **kind** of obstacle, not the amount — she names antagonist, physical obstruction, internal conflict, fate, and says the best work uses three or four |
| Turns and varies, still flat | No cycle of build and release | Pearlman: *"the cut stops breathing"* — schedule the release (§6) |

[PRIMARY · Cowgill; Pearlman — via local extractions] Cowgill's thesis, quoted in her extraction
from Irwin Blacker: **"Plot is more than a pattern of events; it is the ordering of emotions."** And
her own instruction: for every important action, plot the character's emotional *reaction* as its
own beat — *"what do I want the reader to feel here?"*

### 2.3 The shape of the whole

Pope is the one author who draws it: tension **starts just above zero, climbs scene by scene to a
single climax, then exits fast through a short denouement.** Starting at zero or at maximum both
fail — there is nowhere to build. Two tracks, external and internal, hemstitching and resolving at
the same peak; the anti-pattern is an external climax landing while the internal arc is still open,
so **"the audience feels the story end twice."** [PRIMARY · Pope — via a local extraction]

### 2.4 ⛔ The last frame is worth as much as the hero frame

The **peak–end rule**: memory of an experience is dominated by its highest moment and its final
moment — **not by duration or average satisfaction** — and the source that imports it into journey
mapping notes the fit is not coincidental: *"The peak-end rule not at all coincidentally mirrors the
structure of a narrative arc."* [PRIMARY · Lichaw, *The User's Journey* — via a local extraction,
read 2026-08-29 · deep primary-source extraction]

For a 40–60 second ad this is the single most useful frame in the file: **what the viewer keeps is
approximately the peak plus the last frame.** Author the final frame with the care you give the
hero frame. The button is **short but non-zero** — McKee's *"brief resolution that lets the audience
absorb the change"*, against a *"long, sagging resolution"* — and its content spec is Glebas's:
end **"the way they thought but not in the way they expected."** ⛔ **No source in the corpus gives
a duration for it, in any unit.** Do not invent one.

### 2.5 The artifact

One row per shot, written at the storyboard beside the HANDOFF card (`shot-handoff.md` §5):

```
| # | FUNCTION | OPEN QUESTION (what the viewer is holding) | INTENDED VIEWER EMOTION |
|   | VALUE (pair: + / −) | CHARACTER STATE | CARRIED BY (face / body / prop / environment /
|   |                                        insert / withholding / sound / cut) |
```

⛔ **The `CARRIED BY` column is the point of the whole exercise.** If every row says "face", the
piece has one instrument and it is the weakest one (§1). A healthy map spreads across the column.

---

## 3. Inside the shot — the frame pair carries the emotional delta

⛔ **A named contradiction with this pipeline's architecture, stated before the method.** Glebas's
rule is *one idea per frame*, and **"most actions need three stages — anticipation, action,
aftermath — so a single beat becomes a small series of frames."** Test: *any single frame, read
aloud, expresses exactly one idea.* [PRIMARY · Glebas — via a local extraction] **He would say a
two-frame architecture has a two-frame budget for a three-frame beat.**

**The mapping that resolves it — flagged as synthesis, not his:**

> **start frame = the anticipation · the model generates the action · end frame = the aftermath**

Three independent sources converge on prelude-and-aftermath as the two ends worth authoring:
Cowgill's *"preparations and consequences — showing a character ready for an event and then its
aftermath, to carry emotion while keeping momentum"*; Mahaffy's ellipsis — *"show the prelude and
the aftermath and trust inference to supply the cause"*; and Glebas's own three stages. [PRIMARY ·
Cowgill; Mahaffy; Glebas — via local extractions]

**And the animation model is our architecture one-to-one.** A **key pose** is *"any moment something
important changes"*, and *"remove one and the shot stops working"*; a **breakdown** is *"a pose
between extremes that defines how the motion travels"*; the discipline is that each pose is *"a
complete, self-contained drawing"*. The planning method: *"thumbnail the extreme poses, strengthen
each for silhouette and line of action, then block."* [PRIMARY · Kelly & Baena, *Animation Tips &
Tricks Vol. 2* — via a local extraction · ⛔ practitioner assertion throughout; nothing in it is
graded Verified]

⛔ **Note what that gives us and what it doesn't.** Two extremes, authored: we have those. The
**breakdown** — the pose that decides *how* the change travels — is exactly the frame we cannot
author, and our own tests confirm the model owns it (`timing-and-performance.md` §5,
`motion-design.md` §2.1). So the honest position: **we author the emotional endpoints and rent the
middle.** That is why the endpoints have to be right.

**⛔ And the gap, stated plainly: no author in the corpus discusses the emotional difference between
a shot's first and last frame.** The "moment before / moment after" as a performance-direction idea
is absent from all twenty-five extractions read. The `EMOTIONAL DELTA` field below is an invention
of this skill, built on the structural convergence above. Treat it as a working instrument, not
doctrine.

```
[EMOTIONAL DELTA — Shot N]
IN:    <the state at frame one, as a circumstance the body is in — not a feeling word>
OUT:   <the state at the last frame, likewise>
TURN:  <the value pair and its direction: "alone → seen (− → +)">
```

This is the emotional half of the `IN` / `OUT` contract in `shot-handoff.md` §5. ⛔ If IN and OUT are
the same state, the shot is a non-event and the map should say what it is *for* instead
(rest, evidence, rhythm — `shot-handoff.md` §6.2).

---

## 4. The vacant face — why "stressed" returns a mask

The complaint: reference frames prompted for *stressed*, *worried*, *angry* come back as a strong
expression with nobody behind the eyes. **Four causes, and only one of them is the model's fault.**

### 4.1 Cause 1 — the instruction is result-driven, and every tradition says so

The camera is **"an x-ray machine"** that photographs whatever the performer is actually thinking;
**result-driven notes ("be more angry") photograph as fake.** [PRIMARY · Leandro, *The Art of
Directing* — via a local extraction, read 2026-08-29] Miller, via Adler and Kazan: authenticity is
*"built from real, recognizable behavior tied to the character's actual circumstances"*, carries
*"complexity… not a single playable feeling"*, and **"acting is psychology transformed into
behavior."** The anti-pattern is *"choosing the 'obvious' emotional reading."* [PRIMARY · Miller —
via a local extraction] From animation: **"Deciding *why* a character moves reveals *how* it
moves"** → *"animate the effort, not the position"*, against a pose that reads as **"someone moved
the character"** rather than the character moving itself. [PRIMARY · Kelly & Baena — via a local
extraction]

*"Someone moved the character"* is the most exact description of a vacant generated still in the
whole corpus, written years before the models existed.

**The contradiction, and how it splits for a model.** Everyone agrees the emotion word is the
wrong instruction. They disagree on the replacement: Leandro **rejects** action-verb/objective
coaching as a theatre import that misreads a film set, and prescribes casting plus parameters plus
intention, with notes framed as questions about the character's experience. The orthodoxy he names
teaches the objective. With both sides now in the corpus, the disagreement splits cleanly
(`acting-for-the-model.md` §2): the tradition's **internal** tools (the felt want, the bare
transitive verb, substitution) are exactly what a model cannot receive, so Leandro's rejection holds
there; its **external** tools (facts and event, physical life, the outside target, the stimulus,
the obstacle) are renderable and are where every current video vendor's guidance has converged. What
survives unanimously is still the negative rule: **do not name the emotional result.**

⚠️ **SUPERSEDES IN PLACE** (2026-09-30) — previously: "the opposing side is not in this corpus at
all — so the skill cannot settle it." Weston, Donnellan, Meisner, Hagen, Chekhov, actioning and
Practical Aesthetics were researched on 2026-09-30 (`acting-for-the-model.md` §1). The split in §2
there is a synthesis nobody has tested, and it is labelled that way.

### 4.2 Cause 2 — a face at peak intensity carries arousal, not valence

**This is the finding that reframes the problem.** Professional tennis players were photographed at
the peak of winning and losing points — real, unposed, maximum-intensity emotion. Shown the full
image, the body alone, or the face alone:

> "During peak intensities of emotion, positive and negative situations were successfully
> discriminated from isolated bodies but not faces."

Face alone: **no valence discrimination at all** (p > .3), and the pattern actually *reversed* —
faces from winning moments were rated more negative than faces from losing. Body alone and
face+body: p < .0001. Faces did convey **intensity** (p < .0001). [PRIMARY · Aviezer, Trope &
Todorov, *Science* 338(6111):1225–1229 (2012) · checked 2026-08-29]

**A face-only crop at peak arousal delivers intensity without valence** — a strong expression that
does not tell you what state it belongs to. That is "a strong expression with nobody home", and it
happens with *real photographs of real emotion*. ⛔ **Part of what the model is being blamed for is
a property of the crop.**

### 4.3 Cause 3 — a still is intrinsically bad at authenticity

Judging whether a person is *feeling* an emotion: dynamic displays separated genuine from posed at
**75% vs 31%**; static peak frames collapsed that to **66% vs 59%**. [PRIMARY · Namba, Kabir,
Miyatani & Nakao, *Frontiers in Psychology* 9:672 (2018) · checked 2026-08-29] Consistent with the
authenticity discrimination being *"impaired for static compared with dynamic displays"*. [PRIMARY ·
Krumhuber & Manstead, *Emotion* 9(6) (2009) · checked 2026-08-29]

⛔ **And do not build on "genuine emotion shows in the eye muscles."** The same paper's headline is
that Duchenne smiles *can* be feigned, and Ekman's own organisation concedes the cue is weak in
practice — *"most of the time we are easily fooled by broad smiles that are fabrication."*
[PRIMARY · Paul Ekman Group · checked 2026-08-29] See `timing-and-performance.md` §3.4.

**The consequence for the pipeline: the reference still is being asked to do a job that stills are
measurably bad at.** Some of the authenticity legitimately only arrives at the animation step. The
still is a **pose to move from**, not a performance.

### 4.4 Cause 4 — the model over-drives it, and these are the hardest emotions

AI-generated emotional faces are rated **significantly more intense** than posed human photographs
(mean 6.40 vs 5.77; F(1,98) = 241.49, p < .001, η²p = 0.71), with the exaggeration visible at the
action-unit level — *all* synthetic surprise images used AU27 (mouth stretch) rather than AU26 (jaw
drop), described as *"more extreme AU activation."* [PRIMARY · Kramer, Javorková & Clark, *Journal
of Nonverbal Behavior* 50:1–17 (2026) · checked 2026-08-29]

And the emotions in question are the hardest to carry: fear and disgust are the most
resolution-hungry, worst at *every* resolution and near chance when small [PRIMARY · Du & Martinez,
*Journal of Vision* 11(13):24 (2011)]; and expressions differ in signalling range — happiness is
*distal*, fear and sadness *proximal*, i.e. built for close range. [PRIMARY · Smith & Schyns,
*Psychological Science* 20(10):1202–1208 (2009)] Both checked 2026-08-29.

⛔ **Nobody has studied why generated angry faces look vacant.** The phenomenon is un-named in the
literature; the four causes above are what exists around it.

### 4.5 ⛔ CORRECTED 2026-08-29 — the answer is the reference, not the amplitude

**This section first said "exaggerate the face for attention, carry the valence in posture, hands
and context." That was wrong, and the client corrected it:** *"It's not about exaggeration, but
about taking as reference genuine happy people, which are not stressed, very angry or stiff."*

The error was resolving a tension by splitting the difference. There was a real counter-case — the
same study that found AI faces more intense found them **recognised more accurately than posed human
photographs, 91% vs 84%** (η²p = 0.54), linking the two: higher intensity *"may contribute to their
more accurate categorisation."* [PRIMARY · Kramer et al. 2026 · checked 2026-08-29] From that I
concluded *push the face*. **The legibility premise is sound and I applied it in the wrong
direction**, because the evidence already gathered in §4.4 says which expressions are legible — and
it is not the ones being briefed.

**The corrected rule:**

> **Reference frames are cast, not coached. Cast a genuine, moderate, positive-or-neutral state —
> and let circumstance, structure and the cut carry the negative.**

**Four pieces of evidence, all already in this file, all pointing the same way:**

1. **Positive expressions are the only ones that survive the medium.** Happiness is a **distal**
   signal — good across a wide range of viewing distances — while fear and sadness are **proximal**,
   built for close range. [PRIMARY · Smith & Schyns 2009] And happiness is among the least
   resolution-hungry, where fear and disgust are worst at *every* resolution and near chance when
   small. [PRIMARY · Du & Martinez 2011] ⛔ **At 9:16 on a phone, a briefed negative state is the
   expression least able to transmit — and pushing its amplitude does not fix that**, because
   amplitude was never the missing variable; spatial frequency was.
2. **Exaggeration has a measured cost, and it is the cost that matters here.** Facial motion scaled
   to 140% of recorded magnitude read as **"fidgety and anxious"**; damped motion read *calmer* and
   *more respectful*. [PRIMARY · Hyde et al. 2016 · `timing-and-performance.md` §4] **Pushing the
   face does not buy warmth. It buys agitation** — which is the same defect under a different name.
3. **What reads as genuine is a held apex, not a big one.** Longer apex durations correlate with
   higher genuineness ratings; the felt register is *slower onset + sustained apex*, the performed
   one is *fast + big + brief*. [PRIMARY · Krumhuber & Manstead 2009; Schmidt et al. 2006/2009 ·
   `timing-and-performance.md` §2.2] **Amplitude is not the dial. Duration is** — and a still has no
   duration, which is exactly why the still should not be asked to carry the emotion at all (§4.3).
4. **The doctrine already said this and I buried it under the wrong headline.** *"If you want an
   intense performance, cast an intense actor"*; truth is **cast, not coached**. [PRIMARY · Leandro
   — via a local extraction] And: **no performer is asked for behaviour outside their demonstrated
   range** — if the model reliably returns vacant high-arousal faces, that is outside its range, so
   *change the target, do not push harder*. [PRIMARY · Mahaffy — via a local extraction]

### 4.5a Three different failures, wearing one complaint

The client named three, and they do not share a cause:

| Symptom | What it actually is | Fix |
|---|---|---|
| **Stressed / worried** | A **register** error — a proximal, resolution-hungry expression briefed into a distal, low-resolution medium, then rendered at peak where the face carries arousal without valence | Change the state you brief. The negative goes into circumstance, structure and the cut (§4.5b) |
| **Very angry** | A **peak-intensity** error — the face is at maximum, which is exactly where valence stops being readable (Aviezer) and where the model over-drives hardest (Kramer) | Brief the state *before* or *after* the peak. A face at 30% of an emotion is more legible than one at 100% |
| **Stiff** | Not an emotion problem at all — the **uncanny-valley checklist**: slack or mirror-perfect face, no eye jitter, eyes moving only with the head, static head, uncoordinated face and body | `timing-and-performance.md` §4 and `realism-qa.md` V2/V5b. Asymmetry, an eyeline anchor, and hands with a job |

### 4.5b Where the negative goes instead

The brief still has a problem state to convey. It is carried by **everything except the face**:

- **Circumstance** — the sink of last night's dishes, the alarm snoozed twice, the coat still on
  indoors. Checkable in the frame, where "overwhelmed" is not (§5).
- **Structure** — dramatic irony. The viewer holds what the character doesn't, and a calm face
  produces the dread (§1, mechanism 1). This is free and it is the strongest instrument available.
- **The cut** — Kuleshov. The insert assigns the feeling to the adjacent face (§1, mechanism 2).
- **The body** — posture, hands, weight. Where valence actually lives (§4.2).

⛔ **And the reverse failure, which is just as bad.** Do not swap an anguished mask for a beaming
one. The **default pleasant face** is already a retake candidate in this skill (`direction.md` §1,
`realism-qa.md` V2) and a grinning stock model is its own AI tell. *Genuine* means moderate
amplitude, engaged eyes, mild asymmetry, and hands doing something — a person mid-life, not a person
performing contentment.

**One adjacency worth naming.** Over-briefing the problem state is also where **manufactured fear**
enters at the image level — the ethics gate in `persuasion-psychology.md` §6 is usually read against
the script, and it should be read against the reference frames too. A "before" state is legitimate
advertising; a face performing suffering to sell a supplement is the thing the gate exists to catch.
The craft argument and the ethics gate point the same way here, which is usually a sign the craft
argument is right.

⛔ **One honest residue of the discarded rule.** Kramer's recognition result stands: viewers *do*
categorise the exaggerated version more accurately. But recognition is not the objective — the study
never rated authenticity — and buying recognition of a state whose valence the face cannot carry
anyway is buying the wrong thing. Where legibility genuinely is the binding constraint (a
one-second thumbnail beat), the answer is a **positive or neutral** state, which is legible at
distance by construction, not a louder negative one.

### 4.6 The fixes, ranked

0. ⛔ **Cast the state before you prompt anything.** The reference frame is a **genuine, moderate,
   positive-or-neutral** state — a person mid-life, not a person performing an emotion. The negative
   is carried by circumstance, structure, the body and the cut (§4.5b). This sits at zero because
   every fix below it is a refinement of a target chosen here, and none of them rescues the wrong
   target. **Truth is cast, not coached** (§4.5, item 4).
1. **Never name the emotion — give the circumstance and the physical action.** Vendor-documented,
   and the sentence is the best on this problem anywhere: *"Style must be visible: **'tense' becomes
   rigid posture, shallow breathing, and a slow push-in**."* [PRIMARY · Black Forest Labs, published
   agent skills, `flux-3-cinematic-inserts` · read 2026-08-29] The same repo states the epistemics:
   adjectives are unfalsifiable — *"nothing in the output can confirm or refute them"* — where a
   named physical artifact can be checked in the frame. ⛔ **That vendor contradicts itself:** its
   *still-image* guidance teaches naming the emotion (*"Change the expression to a warm genuine
   smile"*). Follow the video guidance.
2. **Put the body in the frame.** The valence lives there (§4.2). A head-and-shoulders crop of an
   emotional state is the framing least able to carry it.
3. **Run the cover-the-face test on every reference frame.** Kelly's is stated for a shot — *"mute
   the shot and hide the face — the emotion and intent still read from the body alone"* — and
   converts directly to a still: **crop the head out. If the pose says nothing, the image is a face
   wearing an expression, not a person in a circumstance.** Reject and re-author the circumstance.
4. **Ask for a second layer.** *"Not a single playable feeling"* (§4.1). One emotion at maximum
   intensity with nothing underneath is what performers are trained *not* to do.
5. **Fix the eyes by circumstance, not by adjective.** A working headshot photographer's documented
   position: when people feel uncertain *"their eyes open wider. It's automatic"*, and in photographs
   *"those wide eyes read as anxious or distracted no matter how composed the rest of the face is."*
   His remedy — the **squinch** — is stated anatomically (*"narrow the distance between your lower
   eyelid and your pupil… the upper eyelid barely moves"*) and instructed as a **circumstance**: the
   look of someone *"genuinely engaged in a conversation and locked in on what the other person is
   saying."* [PRIMARY · Peter Hurley · checked 2026-08-29] ⛔ *Stressed* and *overwhelmed* push a
   model toward exactly the wide-aperture configuration he names as reading vacant. ⛔ And the honest
   gap: **no study exists on whether catchlights, pupil or iris detail make a rendered eye read as
   alive.** That is craft convention, not evidence.
6. **Cast the mode to the range you have.** *"Any mode is compelling when applied consistently and
   with control; authentic emotion, not naturalism, is what reads as real"*, with the test that **no
   performer is asked for behaviour outside their demonstrated range.** [PRIMARY · Mahaffy — via a
   local extraction] If the model reliably returns vacant high-intensity faces, asking it for
   naturalism at intensity 10 is asking outside its range: **change the mode, don't push harder.**
   ⛔ This is item 0 restated at the level of the whole piece — and the fact that the same rule
   arrives twice, from casting doctrine and from performance-mode doctrine, is why it was promoted
   to the top of the list on 2026-08-29 (§4.5).
7. **Treat the still like mocap** — a foundation to re-time and push, not a finished performance;
   untouched mocap reads *"dead, stiff, creepy."* [PRIMARY · Kelly & Baena — via a local extraction]
8. ⛔ **Stop re-rolling adjectives.** *"After two structurally similar misses, change the concept or
   the production method, not the adjectives."* [PRIMARY · Black Forest Labs skills · read
   2026-08-29] This is `refinement-loop.md`'s three-attempts rule, from a vendor.

**Worth knowing before you go looking:** of eight image vendors' current prompting documentation,
**seven say essentially nothing about emotional expression** — Midjourney gives one checklist word,
Google's Imagen and Gemini guides are silent, Ideogram, Recraft, OpenAI and Higgsfield/Soul likewise.
There is no established practice to copy here. [PRIMARY · vendor docs · checked 2026-08-29]

---

## 5. Props and environment — the circumstance IS the emotional instruction

`production-design.md` and `character-and-props.md` decide *what* goes in frame. This section is
*why it moves the curve* — and it follows directly from §4, because the fix there was **name the
circumstance, not the emotion**, and a circumstance is made of objects and a place.

⛔ **Honest first: no author in the corpus gives an emotional taxonomy of props or sets.** The five
functions below are assembled from adjacent doctrine. They are a working instrument, not received
craft.

| Function | What the object or place does | Grounded in |
|---|---|---|
| **Externalise** | Gives an internal state a body to live in: the mug held with two hands, the phone face-down, the blister pack half empty, the laptop still open at midnight. **The valence lives in the body, and the body's state is legible mainly through what it is doing with things** | Aviezer 2012 (§4.2); `character-and-props.md` — props exist to give people something to do |
| **Instruct** | The insert *assigns* the feeling to the adjacent face. An object shot is not decoration; it is the Kuleshov half of the sentence | Glebas; Mahaffy; Leandro — all at their extractions' highest confidence |
| **Withhold** | Frame an **absence** and the viewer builds it for free — the empty chair, the unopened box, the one place setting. Test: *"the withheld element is clearly framed as absent (the viewer feels the gap), not merely missing by accident"* | Mahaffy, offscreen space |
| **Date and place the beat** | Season, time of day, wear, clutter — the environment carries the *when* and *how long this has been going on*, which is what turns a state into a story | `production-design.md` |
| **Set the mode** | The room decides which performance register is even available. A styled set asks for a styled performance; a real kitchen at 11pm gets naturalism for free | Mahaffy, performance modes (§4.6 item 6) |

### 5.1 How this changes a prompt

**Write the circumstance; let the model infer the face.** A sink of last night's dishes, an alarm
already snoozed twice, a coat still on indoors — none of these name a feeling, all of them produce
one, and every one of them is *checkable in the returned frame* where "overwhelmed" is not.

- **Prompt the object's state, not just its presence.** Half-empty, unopened, worn at the grip,
  face-down, still warm. State is what carries time, and time is what carries feeling.
- **Give the hands a job.** A hand doing nothing is the fastest route to §4's vacant pose; it is
  also the failure the generation guardrails already flag (`realism-qa.md` V6).
- **One hero object per beat.** More than one and the insert stops assigning anything
  (`character-and-props.md` — the category audit).
- ⛔ **Do not let the environment argue with the value charge.** A tidy, beautifully-lit room under
  a `−` beat reads as an ad about being fine. The set is on the map's `CARRIED BY` column or it is
  working against it.

### 5.2 How this changes a script

Cowgill's instruction, applied: for every important action, the *reaction* is its own beat — and in
a 40-second ad the reaction beat is usually **an object, not a line**. That is cheaper to generate,
cheaper to shoot, and it is the one place a script can move the viewer's curve without asking a
generated face to do it. When a line and an object say the same thing, **cut the line.**

---

## 6. Transitions — where the feeling is scheduled

The grammar and the pack library live in `editing-and-audio.md`; what a cut *means* is
`editing-storytelling.md` §6; how a shot hands over is `shot-handoff.md`. This is what a join does
to feeling.

### 6.1 ⛔ The channel split — the one rule to get right

- **The speaker's face is the information channel.** Plot-critical lines — the offer, the price, the
  guarantee, the CTA — stay on the face saying them, *"even at rhythmic cost"*, because audiences
  attend to the emotion of a reacting listener and **will miss key information delivered over a
  reaction shot.**
- **The insert, the reaction and the B-roll are the emotion channel.** They assign feeling
  (Kuleshov), instruct it (Dmytryk), or frame an absence (Mahaffy).
- ⛔ **Using B-roll to carry information is the documented error**, and it is the one that surfaces
  later as "the ad didn't land."

[PRIMARY · Hullfish — via a local extraction, corroborated across two editors in the source] Also
`shot-handoff.md` §6.3, where this is a hard prohibition on the shotlist.

### 6.2 The instruments

- **The cut itself is emotional before it is spatial.** *"Don't cut on motion — cut on e-motion"* —
  *"audiences watch faces and feeling, not whether a cigar matches from shot to shot."* [PRIMARY ·
  Miller, quoting Konchalovsky — via a local extraction] ⛔ This sits against Bowen, Dmytryk, Katz
  and Pearlman, who all make cutting on movement the invisible-cut workhorse. The disagreement is
  live and this skill does not resolve it (`editing-storytelling.md`).
- **The reaction, and its hold length, is the dial.** A cut to the listener tells the audience **how
  to feel about what was just said**. *"A reaction held too short is wasted; a reaction held too long
  becomes self-conscious"*, and the working instruction is *"hold the reaction beyond what feels
  natural. Test multiple durations."* [PRIMARY · Dmytryk — via a local extraction · ⛔ weak
  extraction, no page markers; the practice is well attested, an accompanying unsourced percentage
  in that file was discarded]
- **Join by opposites.** Dark→light, warm→cool, wide→tight, left-moving→right-moving. The meaning
  comes from the pairing, not the shots. Anti-pattern: cutting between two visually identical frames.
  [PRIMARY · Miller — via a local extraction] For a batch this doubles as the antidote to template
  sameness (`realism-qa.md` V14).
- **Ellipsis is the cheapest emotional device available.** Cut the cause: *the killer approaches,
  cut, then the body*. Show the prelude and the aftermath and let inference supply what happened.
  [PRIMARY · Mahaffy — via a local extraction] It is also free, which matters at this pipeline's
  per-second pricing.
- **The J- and L-cut is an emotional pre-lap.** Audio leading picture means **the next feeling
  arrives before its image** — the viewer is already in the new state when they see it. It is also
  what removes the need for a picture handle (`shot-handoff.md` §7).
- **Breath is scheduled at the joins.** *"Uniform, unrelieved tension (or all release) with no
  cyclical structure — the cut stops breathing."* [PRIMARY · Pearlman — via a local extraction] The
  release beat is usually an insert; ⛔ note that attaching *breath* to *B-roll* is this skill's
  inference — the sources say the sequence needs breath, not that the breath must be an insert.
- **Dissolves and fades carry time and mood** — and in this pipeline they carry a constraint:
  a dissolve needs frames on both sides, and ⛔ **a dialogue clip may not be extended past its line
  to provide them** (`shot-handoff.md` §2). An emotional dissolve is planned onto a silent settle
  clip or a B-roll insert, at the storyboard, or it does not happen.

### 6.3 The anti-pattern

*"Unjustified cutting out of proportion to the stakes"* — the fifteen-cuts-in-five-seconds fence hop
— *"makes the editing call attention to itself."* [PRIMARY · Mahaffy — via a local extraction] Cut
rate is not emotion. A held shot with a turning value beats six shots that turn nothing.

---

## 7. What this adds to the shotlist

Three additions, all at the storyboard, none at the cut:

1. **The map** (§2.5) — one row per shot: open question · intended viewer emotion · value pair and
   direction · character state · **carried by**.
2. **The emotional delta** (§3) — `IN` / `OUT` / `TURN` on each shot's HANDOFF card.
3. **The carrier named per beat** — which object, which environmental fact, which insert, which
   join. That is what makes §5 and §6 executable rather than admired.

---

## 8. QA

- [ ] Every shot row names an **open question** and an **intended viewer emotion**; a row that
      cannot is a non-event — cut it or give it a function
- [ ] The `CARRIED BY` column is **not all "face"** — irony, an insert, an object, a withholding or
      a join carries at least a third of the rows
- [ ] Each shot's `IN` and `OUT` differ, or the shot is explicitly rest/evidence/rhythm
- [ ] No plot-critical line plays over B-roll (§6.1)
- [ ] The value charge turns at least once per sequence, on a **named antonym pair**
- [ ] **The last frame is authored as carefully as the hero frame** (§2.4), and the button is short
- [ ] **Every reference frame passes the cover-the-face test** (§4.6 item 3)
- [ ] ⛔ **No reference frame was briefed as a negative emotional state.** The cast state is genuine,
      moderate, positive-or-neutral; the negative lives in the circumstance, the structure, the body
      and the cut (§4.5). And it is not a beaming stock smile either — that is the default pleasant
      face, already a retake
- [ ] No prompt anywhere names an emotion as its instruction (§4.6 item 1)
- [ ] The environment does not contradict the beat's value charge (§5.1)

---

## 9. What this file cannot tell you

- **There are no units for emotion.** Not in film, not anywhere the corpus reaches. Polarity on a
  named pair, a ternary outcome score, and an ordinal tension height are the whole toolkit. ⛔ A
  1–10 emotional intensity scale would be invented, and inventing one and then treating its numbers
  as findings is the failure mode this skill is built to avoid.
- **No duration for the button**, in any unit, from any source.
- **No emotional typology of the insert exists.** §5 and §6's function lists are assembled from
  adjacent doctrine; the taxonomy is this skill's.
- **No author discusses the emotional difference between a shot's first and last frame.** §3's
  `EMOTIONAL DELTA` is an invention resting on a structural convergence, not on doctrine.
- **Nobody has studied why generated high-arousal faces read as vacant.** The four causes in §4 are
  what exists *around* the problem; the phenomenon itself is un-named in the literature.
- **No evidence that catchlights, pupils or iris detail make a rendered eye read as alive.** Craft
  convention only — do not cite it as research. The nearest evidence is live-action: with a
  catchlight, viewers' attention reached the eyes 49 % faster and more of them found the emotion
  easy to read (Swenberg et al. 2022, abstract only; `sequence-grammar.md` §6.2). Whether that
  transfers to a rendered eye is the open part.
- **The Leandro-vs-orthodoxy disagreement is split, not settled** (§4.1): the split in
  `acting-for-the-model.md` §2 is a synthesis, and no study compares audiences' ratings of the
  approaches.

⚠️ **SUPERSEDES IN PLACE** (2026-09-30) — previously: "cannot be settled here, because only one side
is in the corpus (§4.1)." Both sides are in the corpus now; what remains unsettled is empirical, not
a missing source.
- **Three re-extraction targets would materially improve this file**, in order: Rabiger's
  actor-direction material (the missing side of that argument); Glebas Ch. 4, which contains a named
  **four-way emotion taxonomy for poses** and was consolidated away; and Glebas Ch. 13 on genre
  emotional engines. A Disney story artist writing about drawing emotion into a still pose is
  exactly this problem, and the library does not currently hold it.
