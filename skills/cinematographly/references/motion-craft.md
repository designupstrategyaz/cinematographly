# Motion Craft — why generated movement reads as dead, and what "modern" measurably is

**When to read this:** the clips are technically clean and the film still looks lame; someone says
it "looks AI"; the work has no action in it; a shot moves and nothing happens. This is the
**substance** of movement — what a move must contain to read as alive, modern and legible.

Three files, three questions, and keeping them apart is the point:

| File | Question | Reached when |
|---|---|---|
| `cinematography-craft.md` §3 | **What does this move MEAN?** | Choosing a move |
| **`motion-craft.md`** (this) | **What must the move CONTAIN?** | The move happened and the shot is still dead |
| `motion-design.md` | **How do I OBTAIN this move?** | The model will not perform it on request |

Researched 2026-09-07. Every claim carries a tier (`research-quality.md` §2). ⛔ **The practitioner
literature on this subject is almost entirely unsourced** — the searches return prompt-guide blogs
citing each other — so this file is built from peer-reviewed measurement and from **this pipeline's
own instrumented tests**, and it says which is which. Where the two agree, that is recorded, because
it is the strongest thing in the file.

---

## 1. Why generated motion reads as dead: it has no *between*

The twelve animation principles are usually taught as a style. Five of them are not style at all —
they describe **what happens between the poses**, and they are exactly the five a generative model
has no reason to produce.

**[PRIMARY · Lasseter, "Principles of Traditional Animation Applied to 3D Computer Animation",
*Computer Graphics* 21(4), SIGGRAPH '87 · verified 2026-09-07]** — and ⛔ note that **Lasseter
enumerates eleven, not twelve**: he merges Timing with Motion and drops Solid Drawing as
3D-irrelevant. A source citing "Lasseter 1987" for twelve principles has not read it.
**[NOT VERIFIED · Thomas & Johnston, *The Illusion of Life*, 1981]** — the canonical twelve-item
list could not be read at source; every "12 principles" page found was a marketing blog.

| The principle | What it specifies about motion | What its absence looks like |
|---|---|---|
| **Anticipation** | A preparatory counter-move *opposite* the main action | The action **teleports into existence** — nothing gathers before it |
| **Slow in / slow out** | Spacing between frames: ease in, ease out, settle | Linear interpolation. Reads as robotic — and linear is precisely what a model solving between two states defaults to |
| **Arcs** | Limbs and camera sweep along curves, never straight lines | Straight-line travel. The other half of "floaty" |
| **Follow-through / overlapping** | Parts stop at *different* times; hair, cloth, straps continue past the stop | Everything halts on the same frame. The rigid, dead look |
| **Secondary action** | A subordinate move supporting the main one — a glance, a sleeve tug, a weight shift | Single-channel mannequin motion: one thing moves, nothing else lives |

> **This is the mechanical explanation for "floaty" and "lame".** A model given a start state — and
> at best an end state — is solving an interpolation. Anticipation, easing, arcs, follow-through and
> secondary action are all information that exists *nowhere in either endpoint*. Nothing in the
> problem statement asks for them, so nothing produces them.

### ⛔ This pipeline already measured the prediction coming true

`timing-and-performance.md` §5 and `motion-design.md` §3, from this account's own instrumented test:
**[PRIMARY · own testing, three clips · 2026-08-29]** *every one peaked in its final second and
ended mid-motion — the model blocks the anticipation and the action and never the settle.*

That is **slow-out and follow-through, absent, measured**, before anyone here had read Lasseter. The
literature predicts the exact defect the tool found. Treat that convergence as the strongest
evidence in this file, and treat `clip_qa.py --landing` as the instrument that detects it.

---

## 2. The uncanny is a MISMATCH — and it has two exits, not one

**[PRIMARY · Saygin, Chaminade, Ishiguro, Driver & Frith, "The thing that should not be: predictive
coding and the uncanny valley…", *Social Cognitive and Affective Neuroscience* 7(4), 2012 · fMRI
repetition suppression, N = 20 · verified 2026-09-07]** Viewers watched a human, an android (human
appearance, mechanical kinematics), and the same robot stripped to mechanical appearance. **Only the
android** produced the large response, in bilateral anterior intraparietal sulcus. The authors'
account:

> "When an agent looks like a human… the brain generates a prediction that this appearance will be
> associated with a particular kind of behavior (e.g. movement kinematics). When the behavior of the
> agent violates the prediction, an error is generated."

**That is exactly this pipeline's failure mode**: photoreal appearance, wrong kinematics. And it
means there are **two exits, and the skill has only ever offered one**:

1. **Raise motion fidelity** — everything in §1 and §6, plus the mechanisms in `motion-design.md`.
2. ⛔ **Lower appearance realism.** Stylise, and the human-motion prediction is never generated, so
   there is nothing for the kinematics to violate. A deliberately illustrated, graphic or stylised
   treatment is not a retreat from quality; on this evidence it is the *other* principled solution
   to the same problem, and it is cheaper and more reliable than chasing kinematics. Route it as a
   real option at concept stage (`ideation.md`), not as a fallback after the photoreal attempt fails.

### And motion beats the picture when they disagree

**[PRIMARY · Troje, "Biological motion perception" (2008), on Johansson's point-light walkers ·
verified 2026-09-07]** Fewer than 10 dots and 150 ms are enough to see a whole articulated body —
and *"if pit against one another, the information provided by dynamic features clearly dominates the
role of static features."*

⛔ **A beautiful start frame does not rescue wrong motion.** This skill's pipeline is frame-first by
construction — the frame gate is its most expensive checkpoint — and this finding says the frame is
the *weaker* channel of the two. It does not make the frame gate wrong; it means **approving a frame
is not approving a shot**, and the motion spec deserves the same care the frame gets.

⛔ **Mori's 1970 essay contains no experiment, no data and no participants** — the famous curve is a
hand-drawn illustration of an intuition **[PRIMARY · Mori 1970, authorised translation, *IEEE
Robotics & Automation Magazine* 19(2), 2012 · verified 2026-09-07]**. Cite Mori for the idea, never
for evidence. The motion-mismatch version got real support 42 years later, above.

---

## 3. What "modern" measurably is: short **and** busy, *together*

This is the answer to "nothing modern", and it is measured rather than argued.

**[PRIMARY · Cutting, Brunick, DeLong, Iricinschi & Candan, "Quicker, Faster, Darker: Changes in
Hollywood Film over 75 Years", *i-Perception* 2(6), 2011 · 160 films, 1935–2010 · verified
2026-09-07]**
- Average shot length fell from **~10 s in the 1930s–40s to under 4 s after 2000** (r = −.75,
  t(158) = 14.3, p < .0001).
- **Motion magnitude rose** — a Visual Activity Index (correlate next-adjacent frames; VAI = 1 −
  median r) rose at r = .583, t(153) = 9.02, p < .0001. Whole-film mean 0.05; *Barry Lyndon* (1975)
  0.008; *Toy Story 3* (2010) 0.122.
- ⛔ **And the two got coupled**: the correlation between shot length and motion strengthened over
  time to **r = −.46** — short shots increasingly carry proportionately *more* movement. **That
  relationship did not exist in older films.**

**[PRIMARY · Cutting & Candan, "Shot Durations, Shot Classes, and the Increased Pace of Popular
Movies", *Projections* 9(2), 2015 · 9,400 English-language films 1912–2013 · verified 2026-09-07]**
English-language films 2000–2013 average **4.7 s** per shot (non-English 10.9 s). And the pace did
not come from clever shot selection: **~25%** from a shift toward shot classes that were always
shorter, **~8%** from closer framing, and the remainder from **uniformly trimming every shot**.

> ### ⛔ The house rule this produces
> **A short shot that is not busy is not modern; it is a slideshow.** Short-and-static is the
> pipeline's *default output* — a 5-second generation of a slow push-in, cut to two seconds — and it
> is precisely the combination that no era of film ever produced. Modern grammar is short **and**
> high-motion in the same shot. `clip_qa.py --motion-profile` measures the coupling across a whole
> job and says whether your film has any motion dynamic range at all.

**[PRIMARY · Bordwell, "Intensified Continuity: Visual Style in Contemporary American Film", *Film
Quarterly* 55.3 (2002) · verified by verbatim quotation in Shaviro, "Post-Continuity", *Post-Cinema*
(REFRAME, open access), and by UC Press's own TOC for *The Way Hollywood Tells It* · the Film
Quarterly article itself returned 403 and was NOT read at source]** — the four techniques of
intensified continuity: *"more rapid editing… bipolar extremes of lens lengths… more close framings
in dialogue scenes… [and] a free-ranging camera."* Bordwell's own ASL ranges: 8–11 s before 1960,
**2–4 s contemporary**, and he stresses this is *"not just action movies."* His claim is
intensification, **not rupture** — classical continuity, accelerated.

### ⛔ Blacklist from this section
- **"Modern films average about 2.5 seconds per shot."** The two largest measured datasets say under
  4 s (160 films) and 4.7 s (9,400 films). The real number is **4–5 s**. Cutting a 40-second piece to
  2.5 s average because "that's modern" is over-cutting on a number nobody measured.
- ⛔ **"Hollywood evolved to match the 1/f rhythm of human attention."** This is Cutting's own
  framing and it is repeated everywhere as established. His actual figure is **r = .19** — under 4%
  of variance — and in his own data **films with more 1/f structure were not better liked** (slope
  vs IMDb rating r = −.089, n.s.). It is the most seductive weak claim in this literature precisely
  because a video skill would most want it to be true. Use his shot-length and motion numbers
  freely; do not use this story.

---

## 4. Action and storytelling: cut on the ACTION, not on space or time

This is the answer to "no action, no storytelling", and one measured finding does most of the work.

**[PRIMARY · Magliano & Zacks, "The Impact of Continuity Editing in Narrative Film on Event
Segmentation", *Cognitive Science* 35(8), 2011 · event-boundary segmentation of *The Red Balloon*,
211 edits, N = 41 and N = 24 · verified 2026-09-07]**
- **Action-discontinuity** edits strongly drove perceived event boundaries (weight **0.96**,
  t(1,40) = 5.99, p < .001).
- **Spatial and temporal discontinuity produced a *negative* effect** (−0.28, t = −2.99, p = .004).

> **Jump space and time as freely as you like. Never cut mid-gesture.**
> Viewers do not track your geography; they track actions starting and finishing. For a 40-second
> piece this is liberating in one direction and strict in the other — and it gives the clip spec its
> single most important line: **one complete action per shot, begun and finished inside it.**

**[PRIMARY · Smith, "The Attentional Theory of Cinematic Continuity", *Projections* 6(1), 2012 ·
theoretical synthesis with eye-tracking evidence · verified 2026-09-07]**
- *"Sudden onsets of movement within a shot draw attention to the screen location of the movement"*
  — so **a cut placed on a motion onset at a matching screen position reads as seamless.** This is
  why fast cutting survives at all, and it is a cutting instruction, not a theory.
- Viewers are strikingly blind to continuity violations: on a **second** viewing they caught 2 of 9
  planted changes, and only 33% noticed an actor substituted across a matched exit/entrance.
- ⛔ **The 180° rule is a cost-of-reacquisition rule, not a taboo.** Cross the line and the viewer
  must *"saccade in the opposite direction to find the speaker"*. Budget it as friction that
  compounds, not as catastrophe. (`direction.md` still owns where the line goes; this is what
  crossing it actually costs.)

**Storytelling, stated as a test the motion has to pass:** a shot's movement must **change the
situation** — reveal something, transfer something, resolve or raise a question. Movement that
merely decorates a static situation is the thing `motion-design.md` §1 already calls *a filter over
a photograph*. If you cannot say what is different at the end of the clip from the beginning, the
clip has no action in it, however much the camera moved.

### ⛔ Declared gaps — say these out loud rather than filling them
- **Nobody has measured viewer comprehension of action sequences as a function of cutting rate.** The
  entire "chaos cinema" argument is unmeasured on both sides. ⛔ **Do not cite Stork's "Chaos
  Cinema" (2011)** — it is a video essay with no sample, no measurement and no comprehension data;
  Bordwell's reply is likewise argument. His *"pause/burst/pause"* structure for legible action is a
  well-argued primary statement by the field's leading stylistician and **nothing more**; use it as
  a craft heuristic and never as evidence.
- **No decades-spanning measurement of CAMERA-movement magnitude** separate from total on-screen
  motion. Cutting's VAI conflates subject and camera motion, so it cannot tell you modern films move
  the *camera* more — only that more moves.

---

## 5. Frame rate and shutter: two pieces of production folklore that the evidence contradicts

⛔ **The "180-degree shutter rule" has no perceptual evidence behind it.** Two controlled studies
varying shutter angle across 180°/270°/358° found **no significant effect** on realism, blur/clarity
or preference — in naive viewers (N = 51) and imaging professionals (N = 40) alike. And the one
psychophysical result that bears on it points the *opposite* way from the folklore: **larger shutter
angles reduce judder.**
**[PRIMARY · Wilcox, Allison, Helliker, Dunk & Anthony, *ACM TAP* 12(4), 2015 · N = 51 · verified
2026-09-07]** · **[PRIMARY · Allison, Wilcox, Anthony, Helliker & Dunk, *J. Imaging Sci. Tech.* /
Electronic Imaging 29(5), 2016 · N = 40 professionals · verified 2026-09-07]** · **[PRIMARY · Daly,
Xu, Crenshaw & Zunjarrao (Dolby/Microsoft), *SMPTE Motion Imaging Journal* 124(7), 2015 · observer
count NOT VERIFIED — full text paywalled]**

⛔ **"24 fps is more cinematic; HFR destroys the magic."** Both naive and expert viewers preferred
48 and 60 fps over 24 (p < .0001), rated them **more realistic**, and showed **no soap-opera
penalty and no bias toward the film look**; 60 was preferred over 48 for action. *Scope, stated
honestly:* short stereoscopic clips, attribute ratings and paired preference, one lab with
overlapping authorship — strong evidence that HFR is not disliked, not evidence about how a feature
plays. Note also that the "soap opera effect" people invoke is TV motion **interpolation**, a
different artefact from native high-frame-rate capture; the two are constantly conflated.

**What this changes here:** do not spend prompt words, retakes or argument chasing a "24 fps
cinematic look", and if a roster model offers a higher frame rate, the evidence does not say it will
look cheap. Delivery fps stays a `delivery-format.md` decision; this section exists so nobody trades
quality for a rule with nothing under it.

---

## 6. Writing the MOTION block — the spec that comes out of all this

`prompting-craft.md` owns the block format; this is what belongs *inside* it for a clip.

0. **Start from the intent, when a person acts** (§6b): why they do it, and the manner that forces.
   The person leads every line; the material is the consequence.
1. ⛔ **One complete action, begun and finished in the shot** (§4). If the action cannot finish,
   the shot is too short or the action is too big — split it (`motion-design.md` §2.4), do not
   truncate it.
2. **Name the anticipation.** *"She sets down the glass, then reaches"* — the counter-move before
   the move. This is the single cheapest thing that stops motion teleporting into existence (§1).
3. **Name the settle, or plan it for the edit.** The model will not produce one — measured here,
   three clips out of three (§1). `timing-and-performance.md` §7 is where the tail ramp lives, and
   `clip_qa.py --landing` decides which shots actually have to land.
4. **Name one secondary action.** A glance, a weight shift, a sleeve, steam, a curtain. One
   subordinate move is the difference between a mannequin and a person (§1).
5. **Say the path is an arc** where it is one — *"sweeps up and across"*, not *"moves up"* (§1).
6. ⛔ **Give it something other than the camera to move.** A MOTION block whose only verbs are
   camera verbs is a filter over a photograph (`motion-design.md` §1), and it is the exact shape of
   short-and-static (§3). `prompt_lint.py` warns on it.
7. **Say what is DIFFERENT at the end.** If nothing is, the shot has no action in it (§4).
8. **Do not re-describe the picture** — the approved frame settled that; §11 item 1 of
   `ai-generation.md` and the clip/frame fork in `prompting-craft.md`.

---

## 6b. ⚡ Intent — every movement is a decision, and the shot shows the decision

Author, 2026-10-26, relaying a direct-response agency's brief: *"make everything with intent. So if the subject throws
away sugar, it's not about focusing on how sugar pours even if that is part of the shot, but about the
human being quick to do so, planned hand movement, shaking of cup etc."*, then *"Most generations seem
to have boring movements"*, and *"it can be about other shots too in their own ways"*.

**Why this is not taste.** People read intention off movement before they read anything else:
observers described two triangles and a circle on a plain screen as chasing, bullying and hiding
`[PRIMARY · Heider & Simmel, *American Journal of Psychology* 57(2), 1944]`. The reach for a bottle is
shaped differently, before the hand even touches it, depending on whether the next act is to pour,
throw, place or pass it `[PRIMARY · Ansuini et al., *Experimental Brain Research* 185:111–119, 2008]`,
and observers can tell the intention from those kinematics alone `[PRIMARY (abstract) · Cavallo, Koul,
Ansuini, Capozzi & Becchio, *Scientific Reports* 6:37036, 2016]`. So an audience reads *what the person
wants* from *how the hand moves*. A clip that shows the sugar and not the decision has spent its
seconds on the part nobody watches. Kling's own motion guide asks for "the reason for the movement",
says gestures "carry emotion and intent", and blames stiffness on "an over-reliance on generic verbs"
`[PRIMARY · VENDOR · Kling blog, motion prompts guide, 2026-07-03]`.

**Why generated movement comes out boring.** Each of these was seen in this pipeline or is named above:

| Shape | What it looks like | What it costs |
|---|---|---|
| **No motive** | the hand moves at one gentle speed, centred, as if for the lens | the model fills the empty manner with its default: even, soft, presented |
| **The material leads** | "sugar cascades from the jar in a glittering stream" | the writer's eye went to the fluid, so the model renders fluid slow-motion and the person becomes a hand-shaped stand |
| **No preparation, no follow-through** | the action starts at full speed and stops dead | §1: no *between*, so it teleports. Kling's guide rebuilds a bad move as preparation, main action, follow-through |
| **Presented, not done** | the label turned square to the lens, the bottle lifted for a look | staging for the camera instead of the task. A person's hand serves their goal, and the camera finds the label |
| **One energy everywhere** | every clip in the film moves at the same calm pace | no contrast across the cut (`sequence-grammar.md` §2b) |

**The method: four things, decided in this order, written before the prompt.**

1. **INTENT:** why this person does this, now, as an attitude toward the object or the goal. One
   clause: *"done with sugar for good"*, *"her daily habit"*, *"she isn't supposed to, and she wants it"*.
2. **MANNER:** the movement the intent forces: tempo and its **one change**, force, path, and where
   the eyes are. Use the bundles below, or `acting-for-the-model.md` §4 when the intent is an emotion.
3. **MECHANICS:** preparation, then the action, then the follow-through. The hand either knows where it
   is going (no search: habit, decision) or it does not (hesitation, which is then the point of the shot).
4. **CONSEQUENCE:** what the objects do *because of* that force: the jar knocks the rim, the sugar drops
   in a clump, the cup rattles on the saucer, the chair scrapes. Written as a clause after the
   person's verb, never as the subject of the line.

The camera serves the same intent: it catches the decision (the hand and, where it fits, the face) and
it reacts to the force (a handheld UGC frame takes a small knock on impact). It does not admire the
material. A slow push-in on everything is the generated default, not a choice: the 2026-10-21 direct-response
research (lab-00009 R3) lists the "default slow push-in" among the AI tells `[SECONDARY · practitioner]`.

⚡ **Cross-reference (2026-10-29), additive.** The measured knock of a real operator on a fight's contact
(8–11 % of the width in the blow's direction, 1–2 blurred frames, 0.7–1.6 s back) is
`move-catalogue.md` §51, drama and action only; the six measured feel bands a camera's texture sits in
(locked < 0.8 · float 0.8–2.5 · controlled handheld 2.5–5 · calm handheld 5–12 · agitated 12–25 ·
frantic 25–65 %/s of jitter) are `motion-design.md` §2.5.

**The bundles for task actions** `[opinion · built on acting-for-the-model.md §4 and the four steps
above; not measured here]`. Pick the one the intent names, then write it in plain words:

| Intent | Tempo, and its one change | Force and path | Preparation / follow-through | Eyes | What the objects do |
|---|---|---|---|---|---|
| **Rejecting, done with it** | fast from the start, a hard stop at the end | strong, direct: a flip, a dump, a toss | short reach, two hard shakes, lets go | off the thing once it's gone | the jar knocks the rim; contents drop in a clump |
| **Habit, routine** | quick and economical, no search | light, direct, one continuous motion | none visible; flows into the next task | elsewhere: the phone, the kettle | the cap clicks; the bottle rocks once and settles |
| **Temptation** | a stop short, then a burst | the reach halts, then a quick grab | a glance away first, checking | to the door, then the thing | the wrapper crackles; the fridge light |
| **Struggle, failing** | effort, a second try harder, then a drop | strong but held in; repeated | a breath in before; hands fall after | down at the problem, then away | the button slips; the fabric snaps back |
| **Self-scrutiny** | slow to start, held too long, abrupt let-go | a grab, a hold, a small push away | turns side-on first | the mirror, then down | the skin rebounds |
| **Care, precious** | slow *and* precise, with a last small adjustment | light, direct, small | the hand settles before it touches | on the object | nothing else moves |
| **Relief, energy (the after)** | quicker than the before, rhythmic | free, light, rising | bounces into the next step | up and forward | — |

**The same shot, without and with intent** (the owner's example):

```
✗  START: the sugar jar in her hand over the bin
   MID:   the sugar pours out slowly in a glittering stream
   END:   the last grains settle in the bin

✓  INTENT: done with sugar for good: she gets rid of it fast, no second thought
   START: her hand grabs the sugar jar off the counter without looking
   MID:   in one quick motion she flips it over the bin and shakes it twice, hard; the sugar drops in a clump
   END:   she sets the empty jar down with a tap and turns away, a few grains still falling
```

**The other shots, in their own ways:**
- **A capsule from the bottle** (routine, so it reads as easy to keep doing): the thumb flicks the cap
  open in the same move as the pick-up, two capsules tipped out with one shake, the bottle back down
  with a light tap, label facing out where it lands. Not lifted for a look.
- **Jeans that will not close** (struggle): she sucks in, pulls the two sides together, the button slips
  out, a second harder try, then her hands drop. The intent is in the second try and the drop.
- **The late-night fridge** (temptation): the reach stops short, a glance over the shoulder, then a quick
  grab. The hesitation is the story, so it gets the time.
- **A 3D mechanism with no person** (the cause the viewer must grasp): the motion is built as cause and
  effect, with the tempo change on the cause: the fluid backs up and stalls, the valve opens, it drains
  in a rush. The swirl is not the point; the change is.
- **The presenter pointing at the anatomy** (proof): the finger goes straight to the spot and taps it
  twice. It does not hover.

**In the prompt.** Lead each line with the person and a verb that carries speed and force (*flicks,
snaps, dumps, tips, taps, yanks, tosses, sets it down with a tap*). Write the tempo change as an order
of events (*"stops short, then grabs"*, *"in one quick motion"*, *"without looking"*), not as *"begins
to"* (`prompting-craft.md`). Use *slowly*, *gently* or *in slow motion* only when the intent is slow,
and then give it a stop or a change. The `INTENT:` line goes first in `[MOTION]`. `prompt_lint.py`
warns when a person acts and there is no `INTENT:`, when the intent names no manner, when a line leads
with the material, and when the motion is only slow and even. Warnings: a human decides.

**Verification.** Show the contact strip to someone who has not read the script and ask what the person
wants. If they describe the sugar, the shot failed. `motion_track.py` gives the measured speed
profile: a human action that measures as one constant speed is the floaty default, whatever the prompt
said.

**What comes next.** Three models proposed and then judged what follows from this section
(the intent and emotion proposal of 2026-10-26 [studio history]; the author: all four packages adopted). The start
frame is §6c below. The timing in the edit is `editing-and-audio.md` §"Action points" and
`scripts/action_points.py`. The energy plan is `sequence-grammar.md` §2d. What stays out of the ads
lane is §7b. Motion written into a clip so it carries across the cut to the next shot is
`shot-handoff.md` §4b.

---

## 6c. ⚡ The start frame is made for its motion

The jury's two highest-ranked proposals, both about the still, not the clip
(the intent and emotion proposal of 2026-10-26 [studio history], M2 and M12):

- **Caught, not at rest.** An action shot's approved still is caught at the anticipation peak of the
  clip's action, or already in it: the wrist cocked, the jar tipped 20° over the bin, the weight on the
  front foot. A still composed at rest makes the model invent the energy from zero, and it drifts
  (§1: no *between*). The clip then only has to complete the action. Write it in the frame prompt as
  `caught:`, and read it off the clip's `INTENT:`: the peak is the moment just before the manner shows.
- **Composed for the path.** Leave room on the side the action travels to; prefer a path toward or
  away from the lens, or a diagonal, over a flat move across the frame; plan the end composition (the
  true end frame on Kling 3.0). Write the direction as `travel:`.

`prompt_lint.py` reads the sibling clip prompt: when it has a person acting and is not a dialogue clip,
the frame is warned without `caught:` or `travel:`, and a `[SUBJECT]` that reads as a rest pose is
warned too. ⚠️ A caught frame can carry a little motion blur on the moving part; keep the face and the
product sharp, because the frame gate reads them.

---

## 7. ⛔ Blacklist — motion claims that do not survive their own trail

| Claim | What the trail actually ends in |
|---|---|
| **"Human attention span is 8 seconds, shorter than a goldfish"** | A 2015 Microsoft Canada infographic → "Statistic Brain" → an unverifiable bundle of organisations who later said they could not verify it, plus one real 2008 study of **web dwell time in 25 participants** that never mentions goldfish or attention span. No primary source exists |
| **"Modern films average 2.5s per shot"** | Contradicted by both large measured datasets: under 4 s and 4.7 s (§3) |
| **"The 180° shutter rule is essential to a cinematic look"** | Two controlled studies found no effect; judder work points the other way (§5). Near-universal in production advice, with nothing under it |
| **"24 fps looks more cinematic than HFR"** | Naive and expert viewers preferred HFR and rated it more realistic (§5) |
| **"The uncanny valley is a measured curve"** | Mori 1970 has no experiment, no data, no participants (§2) |
| **"Lasseter's twelve principles"** | Lasseter enumerates **eleven** (§1). A source citing him for twelve has not read him |
| **"Films evolved to match the 1/f rhythm of attention"** | r = .19, and more 1/f was **not** better liked in the same authors' data (§3) |
| **Stork, "Chaos Cinema" (2011)** | A video essay: no sample, no measurement, no comprehension data. The whole debate is unmeasured (§4) |

---

## 7b. ⛔ Out of the ads lane — techniques that read as AI

Judged on 2026-10-26 by three models (Opus 5.5, Sonnet 5.5, GLM 5.3 Flash) for impact, how obtainable
they are from image-to-video models, and how cheesy they look; adopted by the owner. An ads job must
pass as real footage, so these stay out of it. In a drama each needs the owner's sign-off per shot,
and a strip check before it is kept.

| Technique | Why it is out of the ads lane (the jury) |
|---|---|
| **The environment mirrors the emotion:** shadows pulse with her rhythm, dust speeds up, the air vibrates, clothes move against an invisible force | all three: surreal and uncontrollable; renders as warping and pulsing artefacts |
| **A world-state change inside the shot:** a stain spreads, moss grows, the texture turns dreamlike or painterly | all three: morphing and texture shifts look like AI artefacts. A real prop change belongs to §6b's consequence, cut at the change |
| **Reflections as a mirror of the inner state:** a rippling or shattering reflection | all three: models fail at reflections, and the symbolism reads as cheesy |
| **The slow orbit for "scrutiny", the emotional drift** | Opus: orbits warp the geometry and read as AI. Keep a small motivated push that reacts to the action |
| **The foreground wipe as a reveal; escalating micro-gestures** | Sonnet: unreliable from the models and a stylised trope; in an ad they look staged |

`prompt_lint.py` warns on the first three in any `[MOTION]` block. It cannot tell an ads job from a
drama, so the warning names both lanes.

⚡ **Cross-reference (2026-10-29), additive — nothing here changes the table above.** The measured forms
of the last two rows — the course's standing-subject parallax, counter-walk arc, low parallax and
3D-orbit spin, Scenario's slow product orbits, and the foreground reveals — are held in
`move-catalogue.md` Appendix P (P10, P11) until the house rules. The course notes put two readings to the
owner, neither adopted: that this table governs *generated* moves, so a reveal built in the edit from two
clips with a real occluder frame would be allowed in ads; and that a lateral background drift of
≤ 2 %/s and ≤ 25 % of the width per clip is a slight, motivated arc rather than an orbit (the course
notes, course notes; sources as in the legend before `move-catalogue.md` §34).

The foreground-wipe row holds for every job unless its CHECKPOINT carries the `lens-smear` switch
(`assets/project-switches.json`): on a real shoot and outside the ads lane, a smear passed across the lens may
be used as a join, cut inside the smear. No mask is drawn to follow anything, and the ads lane stays closed to
it (v2.48.0, switch `lens-smear`).

---

**Cross-references:** `motion-design.md` (how to obtain a move the prompt cannot describe — read it
second, once you know what the move must contain) · `cinematography-craft.md` §3 (what a move
means) · `timing-and-performance.md` §5, §7 (the settle, measured here) · `editing-storytelling.md`
(where the cut goes) · `direction.md` §3 (the line, coverage floor) · `photorealism-physics.md`
(the still-frame half of "looks AI") · `scripts/clip_qa.py` (`--landing`, `--motion-profile`) ·
`scripts/prompt_lint.py` (the camera-only MOTION warning).
