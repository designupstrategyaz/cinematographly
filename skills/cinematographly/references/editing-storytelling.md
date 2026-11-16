# Editing as Storytelling — why a cut means something

**When to read this:** you are deciding *where* a cut goes and *why*, judging a cut you already
made, choosing between takes for performance, building a montage that has to carry an argument, or
defending a pacing decision to a client who just wants it faster.

The **mechanics** live next door: transition grammar and the installed pack library, beat markers,
colour management, the audio lanes, captions routing, Resolve at volume, and the tiering of
short-form retention practice all belong to `editing-and-audio.md` and are not repeated here. Read
that for *how to execute a cut*; read this for *what a cut does to a viewer*. `craft-cheatsheet.md`
§4 holds the working shorthand — cut on action, the pacing curve, the button — and this file is the
reasoning underneath it, so the shorthand can be broken on purpose instead of by accident.
`cinematography-craft.md` is the sibling on the shot side — what the camera does *inside* a shot,
where this file is about what the joins *between* shots do.

Source tiers follow `research-quality.md`: **[PRIMARY]** = the originator's own words or the paper
itself; **[SECONDARY]** = a reliable intermediary; **[UNVERIFIED]** = widely repeated, no source
located. All checked **2026-08-28**. **This canon is durable** — unlike the platform facts, model
rosters and prices elsewhere in this skill, it does not decay: Murch published in 1995, Eisenstein
in the 1920s, and the perceptual findings describe human vision, not an API. Re-check when a
replication lands, not on a quarterly clock. Where a book reached this file through a source quoting
it verbatim rather than through the book itself, the tag says so; repetition never upgrades a tag.
Where a book reached this file through a **local extraction of it** rather than through the book
itself, the tag says so — `— via a local extraction, read 2026-08-28` — and that layer is treated as
an intermediary with its own failure mode: a paraphrase can sharpen a hedge into a claim (§8).

**Reasoning over rules.** Every rule below arrives with the reason it exists *and* the case for
breaking it. A rule held without its reason can only be obeyed, and obedience is not editing.

---

## 1. Why a cut works

### 1.1 Murch's Rule of Six — the weights, and what they are for

[PRIMARY · Walter Murch, *In the Blink of an Eye* · checked 2026-08-28 — **the book was not read
directly**: quotations reached this file through sources reproducing them verbatim; the percentages
were corroborated across two independent reproductions with matching wording]

| Rank | Criterion | Weight |
|---|---|---|
| 1 | **Emotion** — does the cut reflect what the audience should be feeling? | **51%** |
| 2 | **Story** — does it advance the story? | **23%** |
| 3 | **Rhythm** — is it rhythmically interesting and "right"? | **10%** |
| 4 | **Eye-trace** — does it respect where audience focus is and where it is going? | **7%** |
| 5 | **Two-dimensional plane of screen** — the stage line / 180° | **5%** |
| 6 | **Three-dimensional space of action** — spatial continuity | **4%** |

Sacrifice hierarchy, in his words: *"If you have to give up something, don't ever give up emotion
before story. Don't give up story before rhythm, don't give up rhythm before eye-trace, don't give
up eye-trace before planarity, and don't give up planarity before spatial continuity."*

**The load-bearing claim everyone skips:** *"satisfying the criteria of items higher on the list
tends to obscure problems with items lower on the list, but not vice-versa."* That is **error
masking**, not taste — a cut that lands emotionally makes a spatial discontinuity perceptually
*unavailable*, while perfect spatial continuity does nothing to rescue a cut that is emotionally
inert. The asymmetry makes the list a spending plan, not a scorecard.

**The correction the canon omits.** [PRIMARY · Murch, in interview clarifying his own book · checked
2026-08-28] He calls the numbers **"somewhat facetious"**: 51% is rhetorical, a bare majority
meaning *"it's more than everything else"* combined. Reading 23% against 10% as a ratio misreads his
stated intent. He adds *"My way is not the only way,"* citing editors who work incompatibly with his
method (Richard Harris cutting scenes backwards; Dede Allen cutting dialogue without picture). **Use
the ordering, discard the arithmetic.** ⛔ Never quote the percentages to a client as measured
weights.

**Test — name the failing criterion.** When a cut feels wrong, say which of the six is failing
*before* touching the trim; if you cannot name one, the fault is upstream in script
(`script-craft.md`) or performance (`direction.md`). "Cut 4→5 fails eye-trace: incoming subject
frame-right against an outgoing frame-left exit" is workable in a `09-qa/` note; "feels choppy" is
not.

**A complementary six that checks different things.** [SECONDARY · Christopher J. Bowen, *Grammar of
the Edit*, 5th ed. — via a local partial extraction, read 2026-08-28] Bowen's teaching set asks at
every cut: **motivation** (what is the reason for cutting here), **information** (what does the
viewer know before versus after), **composition** (do the two framings survive each other),
**sound** (does audio support, contradict or carry across the join), **camera angle** (is the new
angle distinct enough), **continuity** (do action, eyeline and position match). Murch's six rank
*why a cut works* and tell you what to spend; Bowen's six are an inspection list. Only one item is
unconditional — a cut whose motivation cannot be stated is wrong before any of the other five is
consulted, which is Dmytryk's Rule 1 arriving from the textbook tradition (§3.6). **Use Murch to
decide, Bowen to audit.**

### 1.2 The blink argument — keep the metaphor, drop the mechanism

[PRIMARY · Murch relaying John Huston · checked 2026-08-28, same verbatim-reproduction caveat]
Huston: *"You blinked. Those are cuts. Your mind cut the scene."* Murch: **"every blink is a
thought. Every thought is a cut."** Two bundled claims of very different standing. **The metaphor —
keep it:** a cut is punctuation on a unit of thought, placed where the *audience* has finished with
an idea; the best sentence in the canon for deciding when a shot is over — not when the action
finishes, but when the thought does. **The literal mechanism — drop it:** [PRIMARY · Smith &
Henderson 2008] blinks coincided with **11.6%** of missed within-scene cuts vs **3.3%** of detected
ones — *marginal* (p = .051), **n = 7**, one cut category, negligible elsewhere. A weak signal, not
a mechanism.

**⛔ Canon vs research, flag #1 — saccadic suppression does not hide cuts.** [PRIMARY · Smith &
Henderson 2008] saccades coincided with **9.5%** of missed edits vs **8.7%** of detected — no
significant difference. Edit blindness is **attentional expectation**, not eye-movement blanking.
You cannot time a cut to a viewer's eye movement; you *can* build the expectation it then satisfies.

### 1.3 What the eye-tracking actually shows

**Attentional synchrony.** [PRIMARY · Smith & Mital 2013, *Journal of Vision*, n = 56] Gaze
clustering (visual angle enclosing 68% of gaze points; lower = tighter): **6.40°** dynamic
free-viewing vs **7.83°** static (t(25) = 8.802, p < .001) — but **7.40°** for dynamic scenes
**under a task instruction**, and probability of fixating people fell **0.544 → 0.306** under task.
Mean fixation duration, free-viewing dynamic: **339 ms**. Moving images do produce a narrow shared
beam you can aim — **but that is a free-viewing fact.** Give the viewer a job (find the price, read
the caption, decide whether to swipe) and it collapses. The most important caveat in this literature
for ad work, because an ad viewer is never a free viewer (§7.3).

**Centre bias.** [PRIMARY · Smith & Mital 2013] After a scene onset, mean gaze distance from centre
falls **206 px → 106 px by 1000 ms**, asymptote 153–174 px near 2000 ms; [PRIMARY · Smith, ATCC
2012] calls it a *"central tendency"* — when a character exits frame viewers *"default back to the
screen centre."* Frame centre is therefore the default landing zone for the first fraction of a
second after **every** cut, and the decision that matters is not whether the incoming frame is well
composed but **how far its point of interest sits from where the outgoing shot left the eye.** Land
near and the cut is free; land far and you spend a beat of attention on relocation — a 40-second
video has about twenty beats.

**Test — the two-frame dot check.** Freeze the outgoing last frame and the incoming first frame side
by side, mark each point of interest with a dot, measure the gap as a fraction of frame height.
Small and centre-ward on any cut meant to be invisible; where it is large, that cut had better be
one you *want* felt (§3.1).

**Edit blindness.** [PRIMARY · Smith & Henderson 2008, *Journal of Eye Movement Research* · n = 7;
5-minute excerpts from *Blade Runner*, *Citizen Kane*, *Dogville*, *October*, *Requiem for a Dream*,
*Dancer in the Dark*, *Koyaanisqatsi*; task: press a button at every edit] **15.8% of all edits went
undetected:**

| Cut type | Missed |
|---|---|
| Match on action (scene + action continuity) | **32.4%** |
| Within scene (scene continuity) | 25.1% |
| Gaze match (scene + gaze continuity) | 10.9% |
| Between scene (no continuity) | 9.4% |

Authors: *"Film editors' intuitions about the techniques that minimize viewer awareness of editing
are validated in a cut detection task."* [PRIMARY · Smith, ATCC 2012] adds Levin & Simons: only
**33%** of viewers noticed when one actor left a room and a **different actor** continued the action
in the next shot. **Caveat that does not get buried: n = 7.** Direction corroborated elsewhere,
ordering intuitive — hold the percentages loosely and never ship one as a norm.

**The core claim, and the most useful single finding here.** [PRIMARY · Smith, *The Attentional
Theory of Cinematic Continuity*, Projections 2012] *"Viewers do not and should not construct a
detailed spatiotemporal representation of the depicted scenes."* Continuity works by *"enabling the
viewer to shift their attention to the audiovisual details currently relevant"*; and the prediction:
*"If a cut occurs that the viewer is not expecting the visual transients... will capture attention
and a discontinuity will be perceived. The continuity editing rules minimize this by cuing viewer
attention across the cut."* The expectations carried across a cut are *"minimal and prioritize basic
object information such as location on the screen, orientation and direction of action."* **So the
viewer tracks three things: where on screen, facing which way, moving which direction.** Furniture,
hands, mugs and background dressing sit below the resolution of what is tracked — the perceptual
licence behind §3.5, and why `realism-qa.md` gates identity, eyeline and lighting drift while a
moved prop is only a note.

**⛔ Canon vs research, flag #2 — eye-trace is underweighted.** Murch ranks it 4th at 7%; the
attentional work puts screen-location continuity near the centre of why cuts work at all. [SECONDARY
· Toczyński, No Film School 2018, with TV editor Jeff Bartsch · checked 2026-08-28] argues for a
higher weighting on fast-paced small-screen content — Bartsch: *"in a very fast-paced montage, the
eye-trace may even be a single most important factor when choosing the next edit."* Blog-level
argument, not research — **but it points at something the empirical work supports.** For this
format, promote eye-trace to third, above rhythm (§7.2).

### 1.4 The expectation mechanism — one account that covers the rest

[SYNTHESIS · assembled locally, published as a synthesis by nobody — **treat the joins as argument
and the parts as sourced**] The parts: [PRIMARY · Siu-Lan Tan, Peter Pfordresher & Rom Harré,
*Psychology of Music* — via a local extraction, read 2026-08-28] on musical expectation; [PRIMARY ·
Karen Pearlman, *Cutting Rhythms* — via a local extraction, read 2026-08-28] on tension and release;
[SECONDARY · Elizabeth Styles, *The Psychology of Attention* — reaching this file through that
synthesis rather than through Styles, read 2026-08-28] on attentional limits.

**The claim: a moment feels right when the perceiver was already holding an expectation, the event
lands where it satisfies or deliberately delays that expectation, and the exchange fits inside what
attention can process.** Three components, each doing separate work, and each with its own failure.

**Expectation is the raw material.** Tan's account is that musical experience is built not from the
physics of individual notes but from anticipation — a listener forms an expectation of what comes
next and when, and the music meets, delays or breaks it; the feeling lives in the gap. A suspension
that resolves late satisfies *because* the delay created the wanting. Transposed: **the rightness of
a cut is not a property of the cut. It is a property of the relation between the cut and the
expectation the viewer was already holding.** No expectation, no payoff — which is why a cut into a
sequence that set nothing up cannot be rescued by moving it.

**Editing runs the same loop.** [PRIMARY · Pearlman] a cut lands when it resolves, or productively
withholds, a tension the viewer is already feeling; the craft form is **cut on the movement, not on
the pause.** The mechanism is the useful part: when a hand reaches across a table the eye is already
following the motion and predicting where it lands, so a cut inside the movement is carried across
by the viewer's own prediction — while a cut on the static frame has **no prediction to ride**, and
the seam shows. That is §3.1 stated from the viewer's side rather than the screen's, and it
converges with [SECONDARY · Bowen] *"cut to the audience's anticipation — if you can predict the
cut, the editor was probably right."*

**Attention sets the speed limit.** [SECONDARY · Styles, via the synthesis] the **attentional
blink**: having detected one target in a fast stream, a second target arriving roughly **200–500
ms** later is frequently missed outright, because attention is still occupied with the first. There
is a refractory period in human processing. **You cannot stack two must-see beats inside half a
second and expect both to register** — one disappears, and the viewer never knows it was there.
Styles supplies the other half of cutting-on-movement as well: selective attention follows motion,
so the cut hidden inside a movement is hidden because attention was on the movement and not on the
seam. The craft trick and the laboratory finding are one fact.

**Test — diagnose a wrong-feeling cut in three questions, in order.** (1) Was there an expectation
to pay off, or does the sequence set nothing up? (2) Does the event land in the wrong place relative
to that expectation — a frame early, a beat late? (3) Did two beats collide inside the blink so that
one was eaten? Each has a different fix and only the second is a trim. Pearlman's three tools (§4)
address the first two; the third is structural and cannot be solved at the cut point.

⛔ **The blink figure is the weakest-sourced number in this file.** It arrives through a local
synthesis citing a survey text — two removes — and the 200–500 ms range is a laboratory finding on
rapid serial visual presentation, not on edited film. Use it as a floor to argue with, never as a
figure to quote.

---

## 2. Montage as meaning-making

### 2.1 The Kuleshov effect — the honest version

**The original demonstration is not evidence.** [SECONDARY, and this matters] **The footage is
lost**; [PRIMARY · Barratt et al. 2016, *Perception* 45(8):847–874] call it *"film mythology."* The standard
account — **Ivan Mosjoukine's** neutral face intercut with soup, a child in a coffin, a woman on a
divan — reaches us largely through **Pudovkin's 1929 retelling**, not Kuleshov's own contemporaneous
documentation, and the inserts vary between tellings.

| Study | n | Result |
|---|---|---|
| Prince & Hensley 1992, *Cinema Journal* | — | Recreation; **contested the effect's validity**; no categorical effect [SECONDARY — abstract only, paywalled: conclusion known, method and figures not] |
| Barratt et al. 2016, *Perception* 45(8) | 36 | Replicated **modestly**; prior attempts gave *"either conflicting or unreliable results"* [PRIMARY] |
| Calbi et al. 2017, *Frontiers in Psychology* | — | Context effects found [SECONDARY — cited by others, not read directly] |
| PLOS One 2019, still photographs | 44 | Labelling replicated (ηp² = .11); valence **partial** (pleasant context did nothing); **arousal contradicted prediction** — faces rated *calmer* after unpleasant context (ηp² = .02) [PRIMARY] |
| PLOS One 2024, authentic films + fMRI | 59 + 31 | **Strong replication.** Valence ηp² = .642 behavioural, .667 in scanner; fearful −0.45, happy +0.27, neutral +0.07 [PRIMARY] |
| Szaszkó & Loebus 2026, *i-Perception* | 32 | **Valence yes, categorization no.** Valence χ²(2) = 37.50, p < .001 but tiny effects (d = 0.05 / −0.08); categorization χ²(8) = 9.62, **p = .293, null** [PRIMARY] |

The synthesis is more useful than either the myth or the debunking. **Valence transfer is real and
robust** — preceding context reliably shifts how *pleasant or unpleasant* a neutral face is judged,
across labs, stimulus types, and a 10.2-second delay. **The categorical effect is fragile and
conditional**, and [PRIMARY · Szaszkó & Loebus 2026] give the authors' own diagnosis of the split:
studies **with continuity editing** (Barratt 2016; Calbi 2017, 2019) got categorical effects;
studies **without** it (Prince & Hensley 1992; their own dyadic design) did not. So **the effect is
not a property of juxtaposition alone — it is juxtaposition *plus continuity cueing*.** Two shots
slammed together shift valence; two shots *edited* — matched eyelines, matched screen geometry,
matched implied space — shift interpretation.

⚠️ **SUPERSEDES IN PLACE** (2026-09-30) — previously: "Barratt et al. 2016, *i-Perception*", twice
in this section. The paper is in *Perception* 45(8):847–874. The same abstract adds a detail the
table did not carry: viewers picked the congruent emotion, but their eye movements showed none of
the expected differences between conditions `[PRIMARY (abstract) · checked 2026-09-30]`. How to use
the effect when chaining shots is `sequence-grammar.md` §4.4: give the face a slight, readable
expression rather than relying on the context shot.

**A live disagreement about how settled this is.** [SECONDARY · Karel Reisz & Gavin Millar, *The
Technique of Film Editing* — via a local partial extraction, read 2026-08-28] The canonical textbook
transmits the effect as foundational, and the extraction rates it *"replicated many times in
experimental film research."* **That is a confidence the table above does not support** — the
categorical effect is the fragile half, and its strongest replication is 2024. Keep the disagreement
visible, because it is the general case rather than a one-off: the editing textbooks carry Kuleshov
as settled, and a reader who trusts them will over-promise what a juxtaposition buys.

**What that buys.** No free performance from cutting a neutral face next to a product. You reliably
get **valence transfer**: the face reads warmer or colder. To make an audience attribute a specific
*mental state* you must build the scaffolding saying the two shots share one space and one moment —
expensive at 40 seconds. Budget for it at the storyboard or settle for valence.

**Test — the isolation check.** Play the reaction shot alone and write down what the face is doing,
then play it in the cut. If the descriptions differ, the meaning is coming from the juxtaposition,
not the performance — often the plan, but it means a client note on "her expression" is really a
note on the shot before it.

### 2.2 Eisenstein's categories — which remain operative

[PRIMARY · Eisenstein, "Methods of Montage" in *Film Form* · typology confirmed 2026-08-28 —
**verified through an encyclopedic secondary source; Eisenstein's own text was not read directly.**
Definitions are standard and uncontested; the wording is secondary.]

| Method | Definition | Status here |
|---|---|---|
| **Metric** | Cut on shot *length* alone regardless of content; simple beat structures (3:4, 2:4, 1:4) for a physiological response | **Operative — it is what beat-matching already is** (`editing-and-audio.md`). Its limit is Eisenstein's own: arousal, not meaning |
| **Rhythmic** | Movement *within* frame weighs equally with duration; content sets length | **Operative and undertaught.** Why a correctly beat-matched cut still feels wrong: you matched the beat and ignored the internal motion vector |
| **Tonal** | Cut on the affective quality of the shot, beyond time and movement | **Operative.** Murch's "emotion" criterion from another tradition |
| **Overtonal** | Synthesis of metric + rhythmic + tonal into a compound effect | **Operative, rarely nameable in practice** — mostly theoretical closure |
| **Intellectual** | Collision producing a *concept* present in neither shot (eye + water = crying) | **Partly historical in narrative** — dated and didactic. **Alive in advertising**, which is structurally an argument |

**Collision vs linkage.** [SECONDARY · checked 2026-08-28] Eisenstein's montage is **collision** —
ideas explode out of conflict between shots; Pudovkin's is **linkage** — shots build additively. A
live choice at every join: *accumulating* (problem, problem, problem, solution) or *colliding*
(problem / solution, no bridge)? Accumulation earns credibility and costs seconds; collision is
cheap and can read as a stunt. `modes/narrative-promo.md` usually wants linkage; a hook in
`modes/ugc-volume.md` usually wants collision.

⚠ **Two of the five are not discussed above and are named here so nobody reads "montage" as one thing.** **Metric** — cut length set by a fixed frame count regardless of content — is what beat-matched cutting already is (`editing-and-audio.md`), so this skill does it under another name. **Rhythmic** — cut length driven by the movement *inside* the frame — is the one that survives best at 40 seconds, and it is the same instruction as cut-on-action read from the other end.

### 2.3 Juxtaposition as argument

**Meaning is created between shots, not within them.** A shot is a proposition; a cut is an
operator. The set an ad actually uses: **A then B = because of A, B** (causal — the default reading
when nothing contradicts it, and why product-then-smile reads as *causation* without anyone
asserting it); **A / B unbridged = A is B** (equation — brand beside aspiration); **A, A′, A″ =
accumulation** (linkage — three variations make a problem read as general rather than anecdotal);
**A vs B = contradiction** (before/after, them/us — the most common ad structure and the most
abused).

**Pudovkin's five relational techniques — the other operator set.** [PRIMARY · Michael R. Miller,
*Developing the Editor's Eye*, 2026 — via a local full-text extraction, read 2026-08-28, reporting
Pudovkin's *Film Technique and Film Acting*] Miller frames these as observed regularities rather
than commandments — Newton on gravity, not Moses on tablets — which is the correct standing for
them.

| Technique | What it does | Where it earns its place at 40 seconds |
|---|---|---|
| **Contrast** | Cut between drastically unlike shots to force comparison | The before/after spine of most ads — *A vs B* above, with a name |
| **Parallelism** | Unite things separate in time or space by formal or thematic match | Cheapest way to say "this problem, everywhere" without a line of copy |
| **Symbolism** | A juxtaposition that makes a metaphor | Runs straight into the claims lint below: a metaphor is an assertion |
| **Simultaneity** | Crosscut concurrent actions in different places | Compresses time, costs shots — rare under a minute |
| **Leitmotif** | A repeated image tied to a theme | Survives best: a returning object is a brand asset the edit builds |

**Four toolkits, not one.** [SECONDARY · Reisz & Millar — via a local partial extraction, read
2026-08-28] The canon they assemble is four schools, each leaving one permanent tool: **Griffith**
(dramatic emphasis — parallel action, the close-up), **Pudovkin** (constructive editing — meaning
built additively), **Eisenstein** (intellectual montage — meaning by collision), **Hollywood
continuity** (the invisible cut). ⚠ Note the collision of terms: "the invisible cut" here is a
SCHOOL, not the technique of hiding a join behind a whip pan or an object wipe — that one is
`editing-and-audio.md` § "The techniques the grammar table does not name", and on generated footage
it is the more useful of the two. Their argument is that an editor who knows one school has one
toolbox and reaches for it unconsciously. In practice that default is continuity — and it is the
wrong default for an ad, which is an argument before it is a story.

**⛔ The ethical edge is specific to this work.** The Kuleshov literature establishes that
juxtaposition transfers valence *without the viewer being aware of the transfer* — an assertion the
audience absorbs and cannot audit. **Anything a cut asserts, you have asserted.** If a juxtaposition
would not survive being written as a sentence and run through the claims lint (`compliance.md`), do
not build it in the edit instead; the ethics gate in `persuasion-psychology.md` §6 governs montage
as it governs copy.

---

## 3. The continuity system and its deliberate violations

**3.1 Match on action** — *cut mid-movement; the action begun in A completes in B.* **Why:**
[PRIMARY · Smith, ATCC 2012] *"Sudden onsets of movement... draw attention to the screen location of
the movement and its future trajectory"*, and a cut *"timed to coincide with the onset of the
action"* showing the same action at the same screen location satisfies that expectation. **Standing:
the strongest in the canon** — 32.4% missed vs 9.4% for between-scene [Smith & Henderson 2008].
[PRIMARY · Dmytryk, Rule 3] *"Whenever possible cut 'in movement'"*; [Rule 5] *"All scenes should
begin and end with continuing action."* **Where exactly in the movement — an unresolved
disagreement, and it is operational.** [SECONDARY · Bowen — via a local partial extraction, read
2026-08-28] says cut at the **mid-point** of the action, "not at the start or end," because the
mid-point is maximum carry: start-of-action cuts feel premature, end-of-action cuts feel late.
[PRIMARY · Edward Dmytryk, *On Film Editing*, 1984 — via a local full-depth extraction, read
2026-08-28] says cut on the **action initiator** — the frame the body commits to the movement, the
start of the turn, the first frame of the step — with the vector continuing and the speed matching
across the join. **These are different frames and both are taught as the rule.** Nothing located
resolves it, and the empirical work (§1.3) constrains only screen location and direction, not the
phase of the movement. Treat it as a two-candidate search rather than a rule; note that the
initiator cut buys a longer incoming shot, which at 2-second scenes is not nothing. [PRIMARY ·
Pearlman] supplies the criterion that decides between them: the frame that **completes the movement
phrase's shape** — phrase being her unit, a movement with a beginning, a build and a resolution.
Cutting mid-phrase without intent is what leaves a cut feeling unresolved.

**Break it when you want the cut seen** — a smash cut, a tonal reversal, the arrival of the offer.
Invisibility hides structural seams; it works against you wherever the viewer is meant to register a
turn.

**3.2 Eyeline match** — *cut to what A sees, from a position consistent with the gaze.* **Why:**
[PRIMARY · Smith, ATCC 2012] viewers hold *"attentional pointers for each character... relative to
where they are expected to appear on the screen"*, and eyelines *"meet on the screen"*; when a
character speaks, attention starts shifting to his previous screen location **~200 ms after speech
onset** — the empirical basis for audio-leading-picture (§6). **Break it** for false eyelines that
withhold or mislead; and note that in single-performer vertical content the convention degrades to
"look at the lens or don't," carrying no information at all.

**POV is built, not shot, and it changes who the audience forgives.** [PRIMARY · Michael R. Miller —
via a local full-text extraction, read 2026-08-28] Cinematic first person is a look followed by a
**clean** shot of exactly what the character sees — never an over-the-shoulder, because *"no one
peers ahead and sees their own shoulder."* Sustained, it makes the viewer inhabit the character, and
Miller's claim is that this is how unsympathetic protagonists become sympathetic: you cannot judge
harshly a person through whose eyes you are looking (his readings of *The Graduate* and *Psycho*).
His own case is the strongest evidence he offers — *Ghost World* tested at 55%, was re-cut for
sustained clean POV, including resizing shots to crop an intruding shoulder out of dirty coverage,
and recovered. **Standing: a documented single-case craft result, not a controlled finding.** For an
ad the move is exact and cheap: cut from the performer's look to a clean shot of the product or the
result, never an over-shoulder, and the viewer is placed inside the wanting instead of watching
someone else want. The failure is mixing POV modes carelessly — the mode has to be chosen and held.

**3.3 Screen direction / the 180° line** — *stay one side of the axis.* **Why:** [PRIMARY · Smith,
ATCC 2012] crossing means the screen direction *"would have reversed and the second shot would no
longer be analogous with our normal head rotation or our covert shift of attention off-screen
right."* **A cut is modelled by the viewer as a shift of their own attention, and attention shifts
have a direction** — reverse it and you contradict their implied movement. Murch ranks it 5th at 5%.
**Break it** for disorientation as content: [SECONDARY] *The Shining* breaks the line to produce
exactly the unease it wants. In an ad, a deliberate axis break marks a hard tonal division
(problem-world vs product-world) more economically than any transition effect, precisely *because*
the viewer feels it without being able to name it. The axis is chosen at the shotlist, not at the
timeline: the staging half of this decision is `cinematography-craft.md` §4.

**3.4 The 30° rule** — *successive shots of one subject differ by ≥30°.* **Why:** a change *"neither
subtle nor total"* reads as a glitch rather than a viewpoint — below threshold the brain sees
unintended apparent motion of the subject rather than a new camera position. **Standing: weakest of
the four — no experimental validation located** [SECONDARY · encyclopedic reference explicitly
noting no empirical support cited · checked 2026-08-28]; Smith's ATCC cites Anderson (1996) and
Hochberg & Brooks (1978) on apparent motion but **does not derive the rule attentionally**, and
classical practice already exempts **axial cuts**. **Break it constantly here** — the jump cut is
native short-form grammar and reads as *compression*, not error. The rule was formed for a viewer
who had no such convention. Two further textbooks reached in this pass assert it as canon and
neither supplies evidence [SECONDARY · Reisz & Millar; SECONDARY · Bowen — both via local
extractions, read 2026-08-28], which raises the count of confident assertions without moving the
evidence at all. **Repetition is not corroboration**; the row in §8 stands.

**3.5 The meta-rule, from the editors themselves.** [PRIMARY · Dmytryk, Rule 6] **"Cut for proper
values rather than proper matches."** [PRIMARY · Thelma Schoonmaker] *"The priority is absolutely on
the best take for performance"* — worry about *"the humor of a line, as opposed to trying to make
sure a coffee cup is in the right place."* Both say in craft vocabulary what §1.3 says in data:
**prop continuity is a production-department anxiety, not a perceptual fact.** ⛔ Do not spend a
regeneration credit on a prop mismatch nobody is tracking; spend it on identity, eyeline or lighting
drift, which they are (`realism-qa.md` §1). *(Dmytryk's rules are verified verbatim, but the source
obtained gives **no reasoning for any of them** — these glosses are inference from context, not from
Dmytryk. **A second source now supplies his reasoning: §3.6.**)*

**The strongest form of the same rule is a deliberate inversion of §3.1.** [PRIMARY · Michael R.
Miller — via a local full-text extraction, read 2026-08-28] reports the principle he took from
director Andrei Konchalovsky as **"Don't cut on motion — cut on e-motion"**: choose the moment with
the greatest emotional truth even when it will not match, because *"audiences watch faces and
feeling"* rather than whether a prop moved. His standing examples are the *Goodfellas* cigar
mismatch and the *Godfather Part II* Fredo close-up, both kept for performance against visible
discontinuity. **Note what this collides with.** §3.1 and Dmytryk's Rule 3 say cut *in* movement,
and Miller's slogan is built to invert that exact phrasing; the grammar textbooks (Bowen; Reisz &
Millar) treat the continuity system as the load-bearing default, which Miller subordinates. The
collision is narrower than the slogan — he is ranking selection above matching, not denying that
action cuts are invisible — but he does put the emotional take ahead of the clean join **every time
they compete**, and they do compete. **Both positions are in this file on purpose.** Where they
conflict, this format follows Murch's ordering (§1.1), which says the same thing as Miller in a
different vocabulary.

**3.6 Dmytryk's reasoning, recovered.** [PRIMARY · Edward Dmytryk, *On Film Editing: An Introduction
to the Art of Film Construction*, 1984 — via a local full-depth extraction, read 2026-08-28. The
rules are his; **the reasoning below is that extraction's report of his chapters, not verbatim
Dmytryk** — a real upgrade on "no reasoning at all", and still not his sentences.] Rules 1–7 above
arrived as bare imperatives. What they were for:

**Rule 1, "never make a cut without a positive reason," is a list rather than a slogan.** Valid
reasons: new information the viewer needs next; a change of emotional register; a pacing demand;
**performance preservation** — getting out of a take that is not landing into one that is; and
continuity necessity. Invalid reasons, named as such: **habit** ("I always cut every two seconds"),
**coverage anxiety** ("we have it, so let's use it"), and **reluctance to commit** — cutting away
from an emotional moment to avoid sitting in it. The third is the diagnostic worth keeping: an
editor cutting away from the offer, or off a performer's face at the moment of the claim, is usually
flinching rather than pacing.

**Rule 6, "cut for proper values rather than proper matches," is the chapter "You Can't Make It
Smooth, Make It Right."** Its three sub-implications: do not sacrifice performance to matching
coverage; do not sacrifice meaning to continuity, because the continuity rules exist to *enable*
invisible storytelling and stop earning their keep the moment they fight it; do not sacrifice rhythm
to symmetry, because symmetric pacing creates dead air. Dmytryk holds a dual standard deliberately —
smoothness as the default discipline, roughness when the scene needs it — with the ordering **master
smoothness first, then earn the right to break it.** That is §6's "invisibility is the default, not
the virtue" arriving from 1984.

**The audience-protocol rule, which has no number here and deserves one.** Audiences hold shared
comprehension protocols — what a genre, a length and a format have trained them to expect of pacing,
information density and emotional cadence — and the editor's job is to know them and decide
deliberately when to meet and when to break them. Dmytryk's own example is that **mid-century
American audiences expected a pace that reads as slow today**: cuts that were fast in 1950 are slow
in 2026. This is Bordwell's intensification argument (§4) stated as a working instruction thirty
years earlier, and it is the cleanest statement in the canon of why importing a feature ASL into a
40-second ad is a category error rather than a difference of taste.

**3.7 The continuity system has an audio half, and it is stricter.** [PRIMARY · John Purcell,
*Dialogue Editing for Motion Pictures: A Guide to the Invisible Art*, 2007 — via a local full-depth
extraction, read 2026-08-28] The unconscious standard an audience holds across a dialogue cut is
four-part: **continuity of room tone** (a gap without room tone reads as a dropout, not as silence),
**continuity of voice texture** (proximity, off-axis colour, breathiness), **continuity of
presence** (the speaker's apparent position in the room stays put), and **no transient artefacts**.
The tools are a crossfade at every cut — **4 to 24 frames** by context — room-tone fill in every
gap, and take selection matched by mic perspective. **Why this belongs in a file about meaning:**
the visual continuity system is forgiving because viewers track only three things (§1.3), and the
audio system is not. A viewer who cannot say what is wrong with a scene is very often hearing the
join rather than seeing it. Purcell's rule — audition every dialogue cut in isolation, and if it is
detectable it is not finished — is the audio counterpart of the two-frame dot check.

**And the hard limit on re-pitching a performance.** [PRIMARY · Purcell] ADR is the last resort
because it rarely matches production sound completely and replaced performances *"often lose energy
and naturalism"* — but he names one case where it is the **only** fix: a take whose **emotion** is
wrong. Production-sound problems are recoverable; a wrong emotional reading is not. §5 argues that a
finished performance exists in no single take; this is the boundary of that claim on the sound side,
and it bites harder on generated footage, where baked audio cannot be replaced at all
(`editing-and-audio.md`). An emotionally wrong line read is therefore a **regeneration**, not a fix.

---

## 4. Rhythm, pace, and the shape of a sequence

📖 **Measured sequence shapes from five festival AI shorts** — the threshold, the reaction ring,
the montage, institution against individual, the four-channel tone break, the intimacy hold and
the bookend, each printable as a skeleton with `film_db.py run` — are in
`specifics-catalogue.md` §12, with the cross-category rules that hold inside every film.
Where the beats land on the clock (hook, threshold, low point, climax, resolution) and how far a
setup sits from its payoff, measured across the same five films: §14. How the performances change
inside a shot and how long those shots are held: §13.

🔗 **The chaining grammar — what shot B has to do because of shot A** (the scene arc, size and angle
across a cut, the stimulus→reaction unit, intensity as a ladder, the key and the palette held per
scene, and one table that combines every channel per beat) is `sequence-grammar.md`, built from the
research on shot order and from what `film_db.py chain` measured across the five films
(`specifics-catalogue.md` §15).

**Pace vs rhythm** (assembled — but see Pearlman immediately below, who does state it this cleanly
and supplies a third term the assembly was missing). **Pace** is rate — shots
per unit time, measurable, external, what beat-matching operates on. **Rhythm** is the pattern of
tension and release, including movement *inside* shots and the variation between cutting rates. Two
sequences can share a pace and have opposite rhythms, which is why a timeline that hits every
downbeat can still feel dead. [PRIMARY · Reisz & Millar, *The Technique of Film Editing* — **only
the early historical chapters were accessible; the systematic chapters on dialogue and rhythm were
not**] Their Griffith analysis: shots run **2–3 feet** at some moments and **11 feet** at others
*"to control tension and guide viewer focus"*, cut *"for dramatic reasons"* rather than physical
necessity — **timing flows from content, not formulas.** [PRIMARY · Schoonmaker] *"Each shot has its
own life"*, an explicit warning against cutting *"every three seconds"* for its own sake; [PRIMARY ·
Menke] *"Nothing is simply connected for the sake of connecting."*

**Where this bites hardest in this pipeline.** Generated clips arrive with a build and no release:
measured 2026-08-29, all three test clips peaked in their *final second* and ended mid-motion. That
is a **trajectory-phrasing** defect in Pearlman's sense, and it is fixed the way phrasing always is
— by where you cut and how you retime, not by regenerating. It also means most of those clips cut
*invisibly* (mid-action), so the defect only costs you on a shot that has to land
(`timing-and-performance.md` §5 and §7).

**Pearlman's three tools, and the third is the one nobody has a name for.** [PRIMARY · Karen
Pearlman, *Cutting Rhythms: Shaping the Film Edit*, 2009 — via a local full-text extraction, read
2026-08-28] Rhythm decomposes into three controls, and every rhythm problem is locatable to exactly
one of them:

| Tool | What it controls | The question it answers | The failure it produces |
|---|---|---|---|
| **Timing** | the cut frame; when an event happens | "On which frame, at which moment?" | A cut a few frames wrong — feels off, survives a trim |
| **Pacing** | rate and shot duration | "How fast, how long held?" | Drone or breathlessness — what clients call "pacing" |
| **Trajectory phrasing** | the arc of energy across a phrase | "What shape does the energy take?" | Correctly timed, correctly paced, and dead |

**Why the third matters here:** it names the failure this file otherwise has no vocabulary for — the
timeline that hits every beat marker and still feels flat. That is not a timing error and not a
pacing error; it is an unshaped arc, and the fix is at sequence level, not at the cut point. ⛔ The
commonest wrong move is adjusting shot length (pacing) when the fault is the cut frame (timing) or
the arc (trajectory). **Test — before trimming anything, name which of the three is wrong.** With
the §1.1 test on Murch's six, that is two questions which between them locate most bad cuts without
touching the timeline.

**Three rhythms running at once.** [PRIMARY · Pearlman] The editor shapes **physical** rhythm (the
movement of bodies, objects and camera), **emotional** rhythm (the rise and fall of feeling) and
**event** rhythm (the delivery of story information) simultaneously, and the finished cut is the
layered result of deciding where they **align** (reinforcement) and where they **offset**
(counterpoint — accelerate the physical while holding the emotional beat and you get friction). The
diagnostic value is that a sequence can be well paced on one axis and slack on another: **cutting
only for information delivery, with the physical and emotional rhythms unattended, is the standard
failure of explainer and product video.** Note the caveat the extraction states against its own
source — Pearlman's framework was built for movement-led narrative, so in talking-head or
montage-of-stills work physical rhythm is thin and the other two carry the load.

**Tension and release, which is where §1.4 attaches.** [PRIMARY · Pearlman] rhythm works as cycles
of building and releasing tension **synchronised to the spectator's anticipation**; uniform
unrelieved tension, or uniform release, is a cut that has stopped breathing. Event rhythm is the
macro form of the same thing: **withhold-and-reveal is a rhythmic decision, not merely a logical
one**, and scene order is chosen for tempo as much as for sense. At 40 seconds that is the entire
hook-and-payoff structure, stated as rhythm instead of as copy.

**Finding the cut when analysis has failed.** [PRIMARY · Pearlman] Her account of rhythmic intuition
is that it is a **trainable perceptual skill and not a mystery**: editors perceive rhythm by
mirroring the footage's movement in their own bodies — kinesthetic empathy — and the instruction is
to move with the action, breathe with it, or **"sing the rhythm"** (vocalise the scene's pulse)
rather than scrub frames. **A genuine disagreement, preserved.** [PRIMARY · Steve Hullfish, *Art of
the Cut*, 2017 — via a local full-text extraction, read 2026-08-28] records Jeffrey Ford arguing the
opposite: an innate sense of rhythm *"is the one thing that limits people from becoming editors"*
and *"you can't learn that."* Pearlman says trainable, Ford says selected-for; nothing located
settles it, and the practical difference is real — one view says drill it, the other says hire for
it.

**Pacing as musicality, from fifty working editors.** [PRIMARY · Hullfish] That book is a curated
roundtable of more than fifty feature and TV editors, so its authority is **craft consensus, not
evidence** (§7.4), and it should be read at that weight. The consensus: a stream of identical-length
shots is monotonous, so the editor varies shot length to supply both rhythm and relief — anchored
explicitly in Gary Provost's *"vary the sentence length, and I create music"*, the same rule this
house already applies to prose. On finding the frame: Ford's **"it's not math, it's poetry"**, Dan
Zimmerman's **"internal clock"**, and the operational form worth keeping — **change the shot at the
moment it ceases to pique your interest.** ⛔ Named as an anti-pattern by these editors: mechanically
cutting on every musical beat, which is what a beat-matched timeline does by default
(`editing-and-audio.md`).

**The most useful rhythmic heuristic for short-form** is Murch's energy model: each shot *receives*
energy from the previous one and responds — swinging with it, hitting back, or dissipating it. Every
cut therefore **adds**, **redirects**, or **absorbs**. **Test — label every join a/r/s down the
timeline.** Three consecutive *adds* is where ads become exhausting, and a string of letters shows
it long before a review does.

**Intensified continuity.** [PRIMARY · Bordwell, "Intensified Continuity," *Film Quarterly* 55:3,
2002] Four tactics: rapid editing; bipolar lens lengths (wide and long, avoiding mid-range); tight
framings replacing two-shots and establishers; constant camera mobility. ASL by era: **8–11 s**
(1930–60) → 4–8 s (1960s–70s) → 5–7 s (1980s) → **3–6 s** (1990s–2000); outliers *Dark City* 1.8 s,
*Armageddon* 2.3 s. **The transferable part is the argument, not the numbers:** this is
*"traditional continuity amped up, raised to a higher pitch of emphasis"* — **intensification, not
rupture.** The 180° rule, eyelines and spatial coherence persist underneath. At 40 seconds the
grammar does not dissolve; it compresses.

**A hard negative result, because it is constantly misquoted.** [PRIMARY · Cutting, DeLong &
Nothelfer, *Psychological Science* 2010; 150 films, 1935–2005] Shot lengths have grown increasingly
clustered in packets of similar length, approaching a **1/f** distribution — the spectral signature
of human attention fluctuation (autoregressive index vs year r = .43, p < .0001; global slope r =
.19, p < .01; film noir 0.09, Hitchcock 0.53, *Star Wars* 0.98–1.14; only post-1980 films generally
approach it). **Three caveats the authors state themselves and nearly every write-up omits:** slope
was **uncorrelated with how much anyone liked the film** (IMDb r = −.089, n.s.); the structure is
**not intentional**, described as *"emergent, self-organizing"* across 500+ filmmakers; and success
needs *"balancing of constraints at multiple scales."* ⛔ It describes what edited film became — it
is not a prescription, and it supports nothing about structuring shot lengths in 1/f packets.

**Accelerating toward the climax.** Craft basis old and strong: [PRIMARY · Reisz & Millar on
Griffith] *"The cutting rate was invariably increased towards the climax, giving the impression that
the excitement was steadily mounting"* — 1958 describing 1915, the oldest continuously held rhythmic
principle in the medium. Empirical basis real but bounded: [PRIMARY · Lang, LC4MP] cuts are
**orienting-eliciting structural features** triggering an orienting response (visible as cardiac
deceleration), and information presented *after* one is **encoded and retrieved at higher rates** —
cuts are memory anchors. **But** the model predicts an **inverted-U** between resource availability
and recognition memory and **supplies no cuts-per-minute threshold** [PRIMARY — a stated absence]. ⛔
Anyone quoting an optimal cut rate is not citing this literature; `editing-and-audio.md` already
quarantines the circulating numbers, and this is why they cannot be rescued.

**Why a first cut is always too long — the mechanism, not the complaint.** [PRIMARY · Michael R.
Miller — via a local full-text extraction, read 2026-08-28, reporting Randy Thom's essay] **the 100%
theory**: every department independently does 100% of the work of making the point — the actor plays
it, the camera frames it, the design states it, the temp music underlines it — so an honest assembly
**over-tells everything**. The bloat is arithmetic, not failure, and the response is deletion. Mike
Nichols's rule, via Miller: **"if you can cut it out, you must cut it out"**, the test being whether
an audience would miss the element had it never existed. **This is the most transferable single
principle in these books for 40-second work**, where four departments each making the point once
produces a video that makes it four times in forty seconds.

**The counter-rule, from the same tradition.** [PRIMARY · Miller, reporting Dede Allen] **"pace
doesn't always mean faster"** — she restored a scene to *Dog Day Afternoon* to slow it, on the
principle that mechanically speeding everything flattens rhythm and drains the moments that were
supposed to land. Hold that against §7.1, where shorter scenes measured *higher* attentional
synchrony: **the craft tradition and the ad-measurement literature genuinely disagree about the
limit of deletion, and this file does not resolve it.** What both agree on is which material goes
first — **shoe leather**, footage whose only job is moving someone from one place to another.

**Vary the cutting pattern, not only the shot length.** [PRIMARY · Miller] Because an editor cuts to
their own internal tempo one beat at a time, a first assembly drifts toward uniform texture; the fix
is to alternate **patterns** at scene level — a cut-dense montage followed by an unbroken moving
master, a dialogue passage followed by a silent one. Shot-length variance is the micro version of
this and pattern variance the macro one; a 40-second piece has room for roughly two patterns, which
makes the choice of which two a structural decision rather than a polish one.

**Craft duration bands, recorded as convention and not as evidence.** [SECONDARY · Reisz & Millar —
via a local partial extraction, read 2026-08-28] dialogue ~2–4 s per shot, action ~0.5–2 s,
reflective ~5–15 s; [SECONDARY · Bowen] under 2 s raises energy, 8 s and over grounds it. Also
[SECONDARY · Reisz & Millar] **"cut before the audience is ready, not after"** — late cuts feel
dead, slightly early cuts feel propulsive, which is §1.4's expectation mechanism stated as craft
heuristic. ⛔ **None of this rescues the §8 row on cuts-per-minute optima.** They are convention
ranges from textbooks with no outcome measure attached, and the JAMS median of 2.12 s (§7.1) is a
measurement of what ads *do*, not an optimum either. Quote them as norms, never as targets.

**Music-video shot lengths, beside those bands** [PRACTITIONER · course notes]: our capture of a music-video
course gives medians of about 1.5–2.9 s a shot across five lessons. They are medians per shot, while the
measured ad baseline's 1.8 s (`sequence-grammar.md` §2c) is a mean per ad, so the two are not one
measure. Re-derive them with `film_breakdown.py` before use (one lesson's 0.16 s looks like scrubbing
read as cuts), and quote them as data, never as a cutting target: music-led cutting is `move-catalogue.md`
Appendix P, P12.

---

## 5. Performance in the cut

**Take selection is a behavioural judgement.** [PRIMARY · Schoonmaker] *"The priority is absolutely
on the best take for performance."* [PRIMARY · Michael Kahn] *"Editing is not a mechanical
process... it's all up here [head] and in here [heart]"*, quoting Dede Allen approvingly: **"You cut
with your gut."** [PRIMARY · Menke] *"I approach the footage in a detailed way, looking at
mannerisms as much as I listen to the dialogue."* [PRIMARY · Dmytryk, Rule 7] **"Substance first —
then Form"**; [Rule 4] **"The fresh is preferable to the stale"** — prefer the take with life over
the technically cleanest, and distrust the take a performer has worn smooth. This maps onto the
selects pass (`direction.md` §4): the clip that delivers its performance card beats the clip that
renders cleanly, which is why `realism-qa.md` makes "technically clean, default pleasant face" a
retake candidate.

**The instrument is the editor's own reaction, and it is trainable.** [PRIMARY · Michael R. Miller —
via a local full-text extraction, read 2026-08-28] Take selection is **"mining for gold"**: sifting
dailies for the rare takes carrying real feeling, the decisive instrument being what the editor
actually felt while watching. Performance outranks lighting, composition, sound fidelity and
continuity *"every time"* — his founding anecdote is Sandy Morse using a take with a visible lens
bloom because the performance was in it. Two refinements make this operational rather than pious.
**Authenticity over polish:** Kazan's *"acting is psychology transformed into behavior"* — look for
specific, lived behaviour tied to the character's actual circumstances, not a generically played
emotion. **Complexity over legibility:** prefer the take carrying more than one feeling at once to
the clean single-note reading — which is the opposite of what a selects pass optimises for by
default, and the opposite of what a generation prompt tends to produce. Miller's own caution is the
necessary one: **"cut on emotion" works because gold takes are rare**, and it is misapplied by
editors who over-trust ordinary footage.

**And the moment that moves you can still be wrong.** [PRIMARY · Miller] Robert Wise's dictum to
Dede Allen — *"the three most important things in editing are story, story and story"* — is the
check on all of the above: Allen cut a Paul Newman scene from *The Hustler* because it did not
advance the narrative, however well it played. Selection by emotional response finds the candidates;
story decides which survive. That is Murch's ordering (emotion 51%, story 23%) read from the other
end, and the two only appear to contradict: Murch is ranking what a *cut* must satisfy, Wise and
Miller are ranking what a *scene* must earn.

**A finished performance exists in no single take.** [PRIMARY · Kahn] *"I could maneuver the film to
do what I wanted, to change the mood and the feelings"*; *"A film isn't going anyplace until its
boundaries and values are established in the cutting room."* [PRIMARY · Schoonmaker] *"We do love to
capitalize on those accidental things."* A look from take 3, a line from take 7, a reaction shot
from another day against a different eyeline — the ordinary condition of screen acting, not a trick.
**§2.1 is the licence:** valence transfers reliably, so a fragment pitched slightly wrong can be
re-pitched by what surrounds it. Generated footage adds one constraint — a baked-audio clip cannot
be re-pitched by slipping sound (`editing-and-audio.md`), so the re-pitch has to come from the
*neighbouring shot*.

**A moment that killed in dailies often has no place in the scene.** [PRIMARY · Steve Hullfish — via
a local full-text extraction, read 2026-08-28] Andy Weisblum's formulation is **"that's the dailies,
and this is the scene"** — performance reads differently against what surrounds it, so a take must
be auditioned against the adjacent reactions and pacing rather than in isolation, and re-calibrated
whenever the cut, the score or the neighbouring shots change. That is §2.1's valence transfer
observed from inside the cutting room. It also sets the tolerance: these editors report that
**mis-timing a performance by a few frames makes it "not ring true"**, and name directors (Lumet,
Forman) who notice 8–10 frames. ⛔ Against a 2-second scene, 8 frames is about **6%** of the shot —
the margin this work is actually operating in, and the reason "close enough" on a performance beat
is not close enough.

**Covering a performance you cannot fix.** [PRIMARY · Hullfish] The editors' standard move for a
weak performer is to **play their line over the reacting face of a strong one**, and to cut to
actors' eyes (Anne Coates on toning down over-the-top playing by cutting away from it). For
generated footage this is the most useful transfer in the book: where a clip's performance is inert
but its audio is usable, the fix is a neighbouring reaction rather than a regeneration — the same
budget argument as §2.1, and it is why §3.7's wrong-emotion case is the one that genuinely forces a
re-render.

**The reaction shot, and when cutting to the listener is wrong.** The reliable part: the reaction
shot tells the audience *how to feel* about what was just said — tonal montage applied to
performance. It also solves problems; [PRIMARY · Schoonmaker] on cutting away from unnecessary
business: *"That hard cut jumps the film forward, it keeps the energy up in the scene."* But the
aphorism **"cut to the person receiving, not the person speaking" is [UNVERIFIED]** — the practice
is thoroughly attested; no primary source in which a named editor states it as a rule could be
located. **That gap is now closed — by sources that do not entirely agree with each other.**
[PRIMARY · Edward Dmytryk — via a local full-depth extraction, read 2026-08-28] states it in his own
right: **the listener carries the scene more than the speaker**, because a reaction reveals how the
audience should feel about what was said, what the listener will do next, and subtext the speaker is
unaware of. His claim is that most fixable dialogue-edit problems are reaction-shot problems, and
that the editor's real controls are *when* to cut to the listener and *how long* to hold — held too
short is wasted, held too long turns self-conscious. [SECONDARY · Reisz & Millar — via a local
partial extraction, read 2026-08-28] concur, and add the qualifier this file arrived at
independently: *lead the audience to where the meaning is* — sometimes the speaker, sometimes the
listener, sometimes an off-screen reaction. **So the rule has a named editor behind it after all,
and the four failure cases below stand unchanged**: Dmytryk supplies the doctrine, not a defence of
applying it mechanically. It is wrong more often than it is taught: **(1)** when the speaker's face
*is* the event — cutting away donates a revelation to someone with less at stake; **(2)** when there
is no reaction worth cutting to — a listener merely listening is a dead frame, the commonest failure
of the principle applied mechanically; **(3)** in single-performer vertical content, where no
listener exists and B-roll manufactured to stand in reads as evasion; **(4)** when it breaks
eye-trace for no gain — [PRIMARY · Smith & Mital 2013] faces are strong attractors (p = .544 of
fixations, free-viewing dynamic), so cutting between two faces at different screen positions costs a
reorientation. **Better formulation: cut to whoever the *next* piece of information belongs to** —
sometimes the listener, sometimes the speaker, frequently in ads neither: the object.

**A hard counter-rule from the working editors, and it is the most operational thing in this
section.** [PRIMARY · Hullfish] Eddie Hamilton and Lee Smith state it independently: **play
plot-critical information on the speaker.** The mechanism is attentional and it is §1.3's —
audiences attend to a reacting listener's *emotion* and will miss *information* delivered over a
reaction shot, so a turning-point line played on someone else's face does not land and surfaces
later as a story problem nobody can locate. Hamilton's instruction is to accept the rhythmic cost:
*"take the hit and stay with the reason you're looking at them."* **The decision rule that falls
out: sort every line into plot or emotion.** Emotion-carrying lines may play off-screen over a
reaction; plot-carrying lines stay on whoever is saying them. ⛔ **For an ad, that is the offer.**
The price, the claim, the qualifying condition and the call to action are plot — they belong on the
speaking face or the on-screen text, and never over a cutaway, however much better the cutaway
looks.

---

## 6. Transitions as meaning (the grammar itself lives in `editing-and-audio.md`)

- **Match cut** — the *narrative* claim that two things are the same thing. It works by satisfying
  Smith's minimal expectation set (screen location, orientation, direction of action) while
  contradicting everything else; that contradiction **is** the meaning.
- **Graphic match** — the weaker formal cousin: shape, colour or composition carries across. Reads
  as association rather than assertion and costs no story time, which makes it cheap in short-form.
- **L/J cuts** — [PRIMARY · Smith, ATCC 2012] attention starts shifting toward a speaking
  character's screen location **~200 ms after speech onset**, so audio arriving before picture
  *pre-commits* the eye to a shot that does not exist yet; the picture cut lands on a viewer already
  looking for it. **The best-evidenced transition technique here, and nearly free. Test — audit
  every dialogue join for whether audio precedes picture wherever the join is meant to be
  invisible.** Dmytryk's own name for it is the **overlap**, and he supplies a figure the research
  does not: the new speaker's voice starts over the outgoing picture, and the picture cuts **6–12
  frames** later [PRIMARY · Dmytryk — via a local full-depth extraction, read 2026-08-28]. At 24 fps
  that is **250–500 ms**, landing just past Smith's ~200 ms attentional-shift onset — the craft
  prescription sits a beat *after* the eye has already begun moving, which is what you would want if
  the mechanism is real. **Two traditions converging independently on one window is the strongest
  single result in this file**, and it costs nothing to apply. His default is more aggressive than
  this file's: overlap **at least every other cut** in any dialogue scene.
- **Smash cut** — deliberate maximal violation, inverting everything match-on-action does. Its power
  is *directly proportional* to how invisible you have been until then; a smash cut inside a run of
  jump cuts is just another cut.
- **Dissolve** — [PRIMARY · Dmytryk] a dissolve says *passage of time*, or *mood / place shift*,
  **and almost nothing else**; length codes magnitude (12–24 frames for a small shift, 48+ for a
  major one). ⛔ The rule worth importing wholesale: **never dissolve to mask a weak cut** — a bad
  cut plus a dissolve is a bad dissolve, and the softening advertises the join instead of hiding it.
  Audit every dissolve by asking whether a straight cut would lose meaning; if not, cut.
- **Joining of opposites** — [PRIMARY · Miller, reporting Eisenstein's contrast principle]
  scene-to-scene joins read as crisp and motivated when the frames are antithetical: dark to light,
  warm to cool, interior to exterior, wide to tight, left-moving to right-moving. The stated
  anti-pattern is cutting between two near-identical frames, which reads as flat or as an error.
  **Standing: craft convention derived from observation** — but it converges with §3.4 from the
  other direction, since it is the *near*-match, neither subtle nor total, that the visual system
  reads as a glitch.
- **Sound hides picture cuts, and you can measure how much.** [PRIMARY · Hullfish] the interviewed
  editors were unanimous that sound sells and even conceals cuts, and their test is portable: **play
  the sequence muted.** What falls apart muted is what the sound was carrying, and cuts that felt
  jarring in silence frequently play once the track is laid. Mechanics live in
  `editing-and-audio.md`; the point here is that a cut cannot be judged on picture alone, so a
  silent QA pass is diagnosing a different film from the one shipping. That is why the sound-off test
  (`sound-off-story.md`) judges only whether the **story** reads, and the sound-on master gate stays.
- **Invisibility is the default, not the virtue.** [PRIMARY · Schoonmaker] **"A lot of people think
  editing should be invisible, but we've never felt that way"** and **"We always like to slap the
  audience in the face if it's required"**, against her *"You're not supposed to see a lot of it.
  You're supposed to feel that a film has pace and rhythm and drama."* The resolution: **continuity
  is a baseline you establish so that departures register.** An ad invisible throughout has spent
  its most powerful tool on nothing.

---

## 7. What transfers to a 35–55s vertical ad — and what does not

Be sceptical here. **Almost every source above was formed on feature-length narrative**, watched by
a seated, free-viewing audience who chose the film. None of that describes a scrolling viewer
deciding in one second whether to keep watching. The canon is not useless — but it has to be sorted,
not imported.

### 7.1 The best evidence found, and it is directly on point

[PRIMARY · "The dynamic effects of visual complexity and scene cuts on viewer attention," *Journal
of the Academy of Marketing Science*, 2025 · checked 2026-08-28 — **the fetch returned no full
author list; cite by title until confirmed**] 42 public service announcements of **25–30 s** (Dutch
Ministry of Health); 30 participants viewing all videos twice = **2,520 viewing experiences**;
eye-tracking at 60 Hz; all **32,392 frames** analysed by computer vision (Deep Gaze II saliency for
complexity, Azure Video Indexer for cuts). Outcomes: narrative immersion, ad liking, and **delayed
recognition at 48–72 hours**. Findings: **median scene duration 2.12 s**, a real measured figure for
professionally produced short ads; **cuts boost attention** (shorter scenes → higher synchrony,
converging with LC4MP); **visual complexity has a *delayed, negative* effect** on synchrony, the
cost landing after the frame appears because of processing lag; **no inverted-U for complexity** —
the relationship was **linear and negative**, simpler beating more complex at every level tested,
which **contradicts** optimal-complexity theories; **synchrony → immersion → liking → recognition**
held through to memory two to three days later; and their stated guidance — present important brand
elements **centrally, without visual distractors, for ≥1 second uninterrupted**, at the start or at
a scene transition.

**Why it outranks everything else here:** peer-reviewed, ads of almost exactly this duration, an
outcome that is not a vanity metric, and two mutually reinforcing headline findings — *cut often,
keep frames simple.* **Its limits, plainly:** n = 30, forced-exposure lab viewing rather than scroll
context, horizontal PSAs rather than vertical commerce ads, and a PSA is not a product.

### 7.2 What transfers — and what matters MORE at 40 seconds

- **Murch's error-masking principle.** At 40 seconds there is no budget for spatial continuity. The
  doctrine saying you may *spend* it, provided emotion and story are intact, is exactly the
  permission structure this format needs.
- **Eye-trace, promoted to third** (§1.3 flag #2). Vertical frames are narrow, viewing distance
  short, and at ~2 s scenes against a **339 ms** mean fixation the viewer gets roughly **five
  fixations per shot**. There is no time to search the frame: where the eye lands on shot entry is
  most of what they see of it.
- **Centre bias.** Gaze sits at centre for the first second after every change (206 → 106 px) — half
  the life of a 2 s shot. **The empirical case for centre-weighted vertical composition**,
  converging independently with the JAMS brand-element guidance; the framing consequences are
  `cinematography-craft.md` §4.
- **Match on action** (32.4% missed) — the cheapest invisibility available. Spend it on the
  structural seams so the cuts you *want* felt stay felt.
- **J-cuts** (~200 ms lead) — free, and disproportionately valuable where the sound track carries
  more than usual.
- **Tonal and intellectual montage.** Eisenstein's least-used narrative category is the most used in
  advertising, because an ad is an argument.
- **[PRIMARY · Dmytryk, Rule 1] "Never make a cut without a positive reason"** — more binding at 40
  seconds than at 100 minutes, since each cut is a far larger fraction of the whole; §3.6 now
  supplies his list of what counts as a positive reason, and the three that do not.
- **Kuleshov valence transfer** — robust, cheap, native to the two-shot juxtapositions short-form is
  made of.
- **The attentional blink as a hard floor** (§1.4). At a 2.12 s median scene there is room for
  roughly one *registered* beat per shot, and **two must-see beats inside 200–500 ms will cost you
  one of them.** ⛔ The concrete failure mode: the offer line and the logo reveal landing within half
  a second of each other, or a price supered over the exact frame of a visual payoff. Separate them
  by a shot, not by frames. [SECONDARY, via a local synthesis — §1.4 states why this is the weakest
  number in the file.]
- **Hit the beat early** — [PRIMARY · Hullfish] the editors' structural rule is to find the moment
  the audience emotionally dials in and reach it as fast as feasible, re-ordering scenes if needed.
  It is explicitly **not** a fixed timestamp, which is exactly what separates it from the
  3-second-hook folklore (§7.4): same instinct, no number, and the version without the number is the
  honest one.
- **Build the opening last** — [PRIMARY · Miller] openings are routinely constructed late in post
  out of material never scripted as an opening, because the piece has become a different piece than
  the script. For a 40-second ad whose hook carries the whole retention strategy, that argues
  against locking the first three seconds at storyboard: **shoot for it, choose it in the edit**,
  from everything you have.
- **Deletion outranks compression** — [PRIMARY · Miller] "if you can cut it out, you must cut it
  out", against the 100% theory (§4): four departments each making the point once is four statements
  of the point in forty seconds. Speeding that up does not fix it; removing three of them does.

**Transfers with modification.** Import Bordwell's *argument* (intensification, not rupture), not
his numbers — a 3–6 s feature ASL is *slow* against the JAMS median of 2.12 s. Accelerating toward a
climax is structurally sound, but at 40 seconds there is room for roughly **one** acceleration, so
spending it early leaves nowhere to go. The 30° rule is effectively suspended (§3.4).

### 7.3 What does NOT survive the format

1. **The Rule of Six as a ranking below position two.** Criteria 5 and 6 are effectively zero at 40
   seconds and eye-trace outranks rhythm. Emotion and story survive intact; the tail does not.
2. **The 1/f finding.** A statistical property of ~2-hour works — a 40-second piece has too few
   shots to *have* a power spectrum, and it predicted nothing about liking anyway (r = −.089, n.s.).
3. **Schoonmaker's "each shot has its own life," in its strong form.** Her argument against cutting
   every three seconds is an argument for a feature's breathing room; [JAMS 2025] points the other
   way — shorter scenes produced *higher* synchrony, and synchrony predicted recall. **A genuine
   canon/evidence conflict, and for this format the evidence wins.** What survives is the narrower
   claim: don't cut on a *metronome* — which is also `editing-and-audio.md`'s beat-marker rule and
   `craft-cheatsheet.md`'s varied pacing curve.
4. **Reaction-shot doctrine in single-performer content** — no listener exists (§5).
5. **Attentional synchrony as a free good.** Task instruction collapsed synchrony (6.40° → 7.40°)
   and nearly halved fixation on people (.544 → .306). **A scrolling viewer deciding whether to keep
   watching is a viewer under task.** Every synchrony figure in this file was measured on free
   viewers and is therefore an **upper bound** here — optimistic by an unknown margin.
6. **Establishing shots and spatial orientation as an apparatus.** If viewers *"do not and should
   not construct a detailed spatiotemporal representation"*, the geography you would spend six
   seconds establishing is not being stored. Spend those seconds on the face or the object.
   **But the working editors dissent, loudly.** [PRIMARY · Hullfish] Lee Smith: *"I believe in
   geography"* — the audience must always know who is where and who is looking at whom, and the
   consensus in that book is that losing spatial relationships is the standard failure of fast
   cutting rather than an acceptable cost of it. **A real conflict with Smith's ATCC, unresolved
   here.** The reconciliation that fits both: what viewers do not store is *survey* geography, a map
   of the room, while what they do track is **relational** — who is where relative to whom, and who
   is looking at what — which is precisely the three things §1.3 says they carry across a cut. On
   that reading you may drop the establisher and still owe the viewer consistent relative positions.
   The ordering for this format stands; the licence is not permission for incoherent staging.

### 7.4 Telling evidence from folklore — the filter, not another list

`editing-and-audio.md` already quarantines the circulating retention claims as UNVERIFIED; this
section exists to make that call reproducible rather than to add to the pile.

| Claim | Support |
|---|---|
| Cuts recruit attention and improve encoding of what follows | [PRIMARY · Lang LC4MP; JAMS 2025] |
| Simpler frames sustain shared attention; complexity fragments it, with a lag | [PRIMARY · JAMS 2025] — **linear**, not inverted-U |
| Brand element, centre frame, uncluttered, ≥1 s → better delayed recognition | [PRIMARY · JAMS 2025] |
| Gaze goes to centre first after any change | [PRIMARY · Smith & Mital 2013] |
| Audio leading picture pre-commits attention (~200 ms) | [PRIMARY · Smith, ATCC 2012] |
| Match-on-action cuts are frequently not perceived at all | [PRIMARY · Smith & Henderson 2008, n = 7] |
| Preceding context shifts the perceived valence of a neutral face | [PRIMARY · multiple, 1992–2026] |

**A third tier the filter has to accommodate: craft consensus.** The books added in this pass are
neither research nor agency content. When fifty working feature editors independently say the same
thing (Hullfish), or a founding-generation practitioner states a rule three later textbooks repeat
(Dmytryk), that is **evidence about what experienced people do** — a real thing to know, and not the
same as evidence about what viewers do. ⛔ The filter question does not change — *what is the outcome
variable?* — and craft consensus almost always answers "the film worked," which is unfalsifiable.
Use it to generate hypotheses and to break ties the research does not reach; never upgrade it to a
finding, and never let its confident tone (§2.1) borrow authority it has not earned.

**Vendor research — directionally interesting, methodologically opaque, not established.**
[SECONDARY · MNTN Research aggregation, 2026 · checked 2026-08-28] cites TVision (~⅓ of viewers paid
equal attention to 15/30/60 s ads; 15 s captured 48% of total ad attention vs 36% and 19%), WARC
(shorter ads are more *"attentionally efficient"*), and MediaScience/Ehrenberg-Bass (7-second ads
performed better as *reminders* after a 30-second exposure than shown alone). **None publish sample
sizes or methods in the accessible write-ups.** The reminder finding is the most interesting and the
most worth chasing to source.

**Folklore — the search returned agency blogs only, and that absence is itself the finding.**
Nothing locatable supports: the **"3-second hook"** (or 1.5 s, or 2 s) as a *measured* threshold;
any optimal cuts-per-minute or cuts-per-second figure; "a cut every N seconds maintains retention";
pattern-interrupt timing prescriptions; any claim that a platform's algorithm rewards a specific
edit rate.

**⛔ The filter is one question: what is the outcome variable?** A supported claim names a mechanism
(orienting response, attentional synchrony, expectation violation), reports a sample and a measure,
and specifies an outcome measured **at a delay** — JAMS measured recognition at 48–72 hours.
Folklore names a number, attributes it to a platform or to "studies," and measures nothing beyond
the first two seconds of a watch curve, which is the thing it is optimising and therefore cannot
validate. Ask that question before repeating any retention claim to a client and it will sort almost
all of them without further research.

---

## 8. What this file cannot settle

**Rules widely repeated, with no support found — do not teach these as facts:**

| "Rule" | Status |
|---|---|
| Saccadic suppression hides cuts | **Actively contradicted** (9.5% vs 8.7%, n.s.) — §1.2 |
| "Cut on the blink" / audiences blink at cuts | Murch's own intuition; strongest data marginal (11.6% vs 3.3%, p = .051, n = 7, one cut type) — §1.2 |
| The 30-degree rule | **No empirical validation located anywhere**; craft convention with a plausible rationale and an exception (axial cuts) that undercuts the specific angle — §3.4 |
| Any specific cuts-per-minute optimum | LC4MP predicts an inverted-U and **explicitly supplies no threshold** — §4 |
| "Structure shot lengths in 1/f patterns" | Real and descriptive; authors **deny intentionality**, and slope was uncorrelated with liking — §4 |
| The "3-second hook" | Zero peer-reviewed support located; agency content only — §7.4 |
| "Optimal visual complexity" | **Contradicted for ads** — linear negative, no threshold [JAMS 2025] — §7.1 |
| Murch's percentages as literal weights | He calls them **"somewhat facetious"**; almost every secondary treatment reports them straight — §1.1 |

**One row left this table in this pass.** *"Cut to the person receiving, not the speaker"* was
carried here as [UNVERIFIED]; a named editor stating it as a rule has now been located — Dmytryk,
with Reisz & Millar concurring — so it moves into §5 with its source, its counter-rule (play
plot-critical lines on the speaker) and its four failure cases intact. **Nothing else moved.**
Hullfish's "hit the beat early" does not rescue the 3-second hook and the craft duration bands in §4
do not rescue the cuts-per-minute row: both supply convention without an outcome measure, which is
the filter in §7.4.

**Verification gaps, stated so nobody re-derives confidence this file does not have.** Not read
directly: Murch's *In the Blink of an Eye* (quotes via verbatim reproductions; the six percentages
corroborated across two); Eisenstein's *Film Form* (typology via an encyclopedic secondary source);
Prince & Hensley 1992 (abstract only); Calbi et al. 2017/2019 (cited by others only). Dmytryk's
rules are verbatim but the source **gives no reasoning for any of them** — every gloss here is
inference (**superseded in part**: a second source supplies his reasoning, §3.6 and below). Reisz &
Millar was reached only in its historical chapters (**partly superseded**: their rhythm and dialogue
chapters now reach this file at second hand, below). Blocked outright: Smith's *Match-Action*
(*Media Psychology* 2017), the study most likely to sharpen the match-on-action and audio figures
and **worth chasing**, and Smith's PhD thesis, which holds the experimental detail behind ATCC.
Never reached: Nelson-Field / Amplified Intelligence, the most credible commercial ad-attention
programme and **the largest remaining gap in §7**. No statement from Michael Kahn on the
listener/speaker question was found.

**Added in this pass, and what its standing is.** Seven editing books reached this file through
**local extractions of them, not through the books themselves**: Pearlman, *Cutting Rhythms*;
Dmytryk, *On Film Editing*; Hullfish, *Art of the Cut*; Miller, *Developing the Editor's Eye*;
Purcell, *Dialogue Editing for Motion Pictures* (full-depth extractions); Reisz & Millar and Bowen
(partial, prioritised chapters only). **That layer is an intermediary with its own failure mode** —
a paraphrase can sharpen a hedge into a claim, visible in this pass where the Reisz & Millar
extraction calls the Kuleshov effect *"replicated many times"* against the record in §2.1. Where an
extraction reports a book's own load-bearing framework it is tagged PRIMARY-via-extraction above;
where it is partial, thin or interpretive it is tagged SECONDARY. **Two gaps closed:** Dmytryk's
reasoning, absent from the first source, is recorded in §3.6; and Reisz & Millar's rhythm and
dialogue chapters, previously unreachable, are represented at second hand in §4 and §5 — still not
read directly. **Gaps unchanged:** Murch, Eisenstein, Prince & Hensley, Calbi, Smith's
*Match-Action*, Smith's thesis, Nelson-Field. **One gap opened:** the attentional-blink figure in
§1.4 rests on a survey text reached through a synthesis essay — two removes, and the only number in
this file at that distance.

**⛔ The structural limitation of §7, and it is not small: no vertical-format eye-tracking study was
located.** Every gaze figure in this file comes from horizontal displays. The centre-bias and
reorientation arguments — which carry most of the weight of §7.2 — have not been replicated in a
9:16 frame at phone viewing distance. Treat them as the best available inference, not as measured
fact for this format, and say so in a client deliverable if they are ever load-bearing there.
