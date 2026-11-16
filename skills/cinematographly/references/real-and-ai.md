# Real footage + AI — the hybrid pipeline

**When to read this:** you are cutting phone-shot or client-supplied footage together with generated
clips; putting a generated element into a real plate; or deciding what to shoot and what to
generate. ⛔ **Read §5 before you shoot anything** — hybrid work changes the legal exposure, and it
changes it in a direction most people guess wrong.

Checked **2026-08-29**, web sources only. ⛔ Two of the four questions this file was built to answer
turned out to be genuinely undocumented — there is **no published minimum plate-capture standard for
a solo phone shooter** and **no credible published shoot-vs-generate decision rule**. Everything
located on both was vendor marketing. Where this file answers them anyway, it says the answer is
ours.

---

## 0. What the skill already covers — and what it does not

Six ways real material and generated material can meet. The pipeline already does three of them,
one of them verified.

| # | Mode | Status |
|---|---|---|
| **A** | **Real asset composited into the start frame**, then animated — the real logo, the real product | ✅ **Covered and verified.** `realism-qa.md` V13, `ai-generation.md`. Never ask a model to render a brand mark or legible text |
| **B** | **Real footage as a motion driver** (motion transfer) | ✅ Covered, ⛔ **UNVERIFIED in this pipeline** — `motion-design.md` §2.2 |
| **C** | **Real audio, generated picture** — the whole Path A lipsync spine | ✅ Covered and in production |
| **D** | **Real footage cut alongside generated footage** in one timeline | ⛔ **Not covered.** The main gap, and the cheapest hybrid there is (§3) |
| **E** | **A generated element inside a real plate** | ⛔ **Not covered.** The expensive one |
| **F** | **A real plate extended or altered by AI** — outpaint, background removal, reframe, upscale | ⛔ **Not covered as doctrine**, though the tools are on the roster. And it is the mode with the sharpest disclosure consequences (§5) |

So the honest answer to *"is it covered?"* is: **the composite-into-the-frame trick is, the cut is
not.** This file adds D, E and F.

---

## 1. The integration problem — making two sources read as one camera

### 1.1 The order of operations, as practitioners state it

> *"Start with matching the exposure… apply a colour correction… match the saturation… correct any
> gamma differences… match the black levels."* Then *"apply chromatic aberration"*, *"apply the
> lens-distortion from your actual lens"*, **soften** the synthetic element so it is not *"too sharp
> and clean"*, and extract grain as *"the difference between your denoised plate and your original"*,
> then *"merge this plate over your entire shot."*

[SECONDARY · Vulto, "Integrating CGI Into a Live-Action Plate", The Rookies · checked 2026-08-29]

**Four things in that ordering are easy to get wrong and worth stating separately:**

1. **Colour, exposure and black level come first.** Everything downstream is judged against a wrong
   reference if they are not settled.
2. **Softening is a step, not an accident.** Generated footage arrives too clean; matching *"level of
   detail"* is named as a parameter in its own right by a working supervisor. [SECONDARY · LBBOnline,
   quoting Genevieve Camilleri, Alt VFX · checked 2026-08-29] For this pipeline that is the most
   likely tell — a clean 1080p generation next to a phone plate.
3. **Grain goes over the whole frame, last** — the plate is degrained and regrained with everything
   else. ⛔ So *"match the AI to the plate"* is right as a direction but wrong as a literal
   description: in a finished comp the plate is the reference, not the untouched master.
4. **Chromatic aberration is itself a tell if overdone** — *"an infamous cg 'tell'"*, alongside lens
   flares. [SECONDARY · König, Blender Foundation *Tears of Steel* · checked 2026-08-29]

### 1.2 ⛔ Which mismatch actually matters — an unresolved contradiction

**Practitioners say lighting, especially lighting direction.** *"Lighting, colour and edges"* are the
core factors; a lighting-direction mismatch creates obvious disconnects *"as it affects where shadows
would fall"*. [SECONDARY · Nick Whiteley, VFX & Compositing Supervisor, The Embassy, via LBBOnline ·
checked 2026-08-29]

**The perceptual research says viewers barely use those cues.** Across seven experiments: *"people do
not readily make use of shadow and reflection cues to help determine the authenticity of images"* —
shadow-error detection ran well below acceptable levels with a bias toward accepting shadows as
consistent, and reflection detection was **near chance** when vanishing points were distant. [PRIMARY ·
Nightingale, Wade, Farid & Watson (2019), *Attention, Perception, & Psychophysics* 81(8):2917–2943 ·
checked 2026-08-29]

**What viewers do track is image statistics.** Measuring 4,126 composites, the strongest
foreground/background correlations were **luminance, colour temperature, saturation and local
contrast** — saturation strongest at **r = 0.811** in the highlight zone — while hue correlated weakly
(below r = 0.4). And: *"luminance matches better between foreground and background in the highlights
and shadows than in the mid-range."* [PRIMARY · Xue, Agarwala, Dorsey & Rushmeier (2012), *ACM TOG*
31(4), Art. 84 · checked 2026-08-29]

⛔ **Left unresolved.** The plausible shape — **flagged as inference, not a finding** — is that these
measure different things: a supervisor rejects a hero shot held on screen under client scrutiny,
where lighting direction is the fault that gets named; the psychophysics measures ordinary viewers
making forced-choice judgements. For a 30-second vertical ad played once at phone size, the second
frame is arguably the operative one. **Do not use that to excuse a lighting mismatch on the hero
shot** — use it to decide what to spend the match pass on when time is short.

**One directly actionable consequence:** luminance matching is naturally tighter in highlights and
shadows than in mid-tones, so **the mid-tones are where a mismatch does most damage**. Grade there
first.

### 1.3 Grain

Derive it from **your own plate**, not a stock library: denoise the plate, subtract, and you have the
grain that camera actually produced. [SECONDARY · The Rookies] Grain is *"density dependent"* and
should be applied per luminance band rather than as one flat overlay, and desaturated because film
grain is *"mainly luma driven"* — ⛔ but that source **sells grain tools**, and the claim could not be
corroborated independently. [VENDOR-ADJACENT · FilmMatch · checked 2026-08-29] Software defaults put
the most grain in blue (R 0.3 / G 0.4 / B 0.5). [PRIMARY · Foundry Nuke ScannedGrain docs — ⛔ Foundry
sells Nuke · checked 2026-08-29]

⛔ **No rule for matching grain *size* was located anywhere.** That is the weakest-sourced parameter.

### 1.4 ⛔ Motion blur — and a claim this skill will not make

Blur *centring* is documented: a real camera's blur is *"more or less centred on the frame"* while
naively rendered blur trails or leads, and the fix is sampling 0.25 frames either side for a 180°
shutter. [SECONDARY · practitioner blog · checked 2026-08-29]

**But the specific claim that generated footage's synthetic motion blur reads as a tell when cut next
to real footage has no credible source.** Searches returned only content farms and tool vendors. It
is widely asserted by creators and it may well be true — **[UNVERIFIED]**, and this skill will not
repeat it as fact. The one documented temporal problem in generated footage is different: clips
arriving *"mysteriously generated in slow motion despite no such request"* and needing retiming.
[SECONDARY · fxguide, on the *Air Head* production · checked 2026-08-29]

---

## 2. Capture — what to get at the shoot

**The full professional list**, for a plate that will carry a synthetic element: hero plate ·
reference plate with a **physical stand-in** · HDRI · **grey ball** (light direction, intensity,
shadow) · **chrome ball** (reflections, light positions, camera location) · **Macbeth colour chart**
(exposure and white balance, so matching is measurement not guesswork) · **lens-distortion grid** ·
interaction plates. Keep charts clean — handle them by the edges. [SECONDARY · The Rookies; CAVE
Academy · checked 2026-08-29]

⛔ **There is no published minimum-viable version for one person with a phone.** Searched
specifically; found nothing credible from any VFX authority, trade publication or school. **[UNVERIFIED]**
The highest-value document in this area — the **VES On-Set VFX Data Collection and Usage Guide**,
published 30 April 2026, free under CC-BY at ves-on-set-data.org — is JavaScript-rendered and could
not be read. [PRIMARY · VES press release · checked 2026-08-29] ⛔ **Open it in a browser and mine it;
it is the one obvious gap in this file.**

**So the kit below is ours, not received practice.** Ninety seconds, before you shoot anything:

- **A colour chart in one frame** at the head of every setup — even a cheap one. This converts the
  entire §1.1 colour stage from taste into measurement.
- **A grey card, or a grey ball if you own one**, in the same frame.
- **Ten seconds of the empty scene, locked off** — your clean plate and your grain source.
- **A note of the focal length and the phone's stabilisation state.** Write it down; you will not
  remember, and stabilisation changes the lens character mid-clip.
- **A stand-in** where the synthetic element will go — even a water bottle. It gives you the shadow,
  the contact point and the scale reference.
- ⛔ **Shoot flat/log if the phone offers it, and never with a beauty filter.** You can add character;
  you cannot remove a baked-in one.

**On a real commercial day — the order and the sound.** [PRACTITIONER · course notes] One practitioner's
working order, recorded as that, not as received practice:

- **Words first, pictures last.** Record the openings, then the asks, then the body read as wild
  sound while the mics are still live, even though nobody is in frame for it; the pictures come
  last. The practitioner's opening is the first 5 s; `hook-craft.md` §3's six seconds is a
  platform's prescription. Both numbers stand.
- **One clock, before the first take.** Every camera and every recorder shares one timecode. Lavs
  sit where cloth will not rub, and a backup recording runs beside the main one.
- **A wild-sound or foley pass for every audible action, before the set is struck** — the same
  action again on a quiet set, a recorder close. Foley mimed to the picture into a phone afterwards
  is a repair, not the plan.
- **The frame rate goes on each shot, not on the job.** Mark the row `source: real` with an `fps:`;
  `shotlist.py --check` warns a real shot with none. The course's readings — 24 for speaking lines, 30 for coverage, 60 for slow motion or a
  whip — are a practitioner's choices, not defaults; how a slowed real shot counts against the
  ramp rules is open (`move-catalogue.md` Appendix P, P15).

---

## 3. The seam taxonomy — pick the cheapest join that tells the story

⛔ **This taxonomy is this skill's, assembled from the sources above.** It exists because the four
kinds of seam differ in cost by more than an order of magnitude, and the lead-level decision is
almost always *which seam to use*, not *how to fix the one you chose*.

| Seam | What meets what | Cost | What it needs |
|---|---|---|---|
| **Cut seam** | A real shot, then a generated shot | **Cheapest** | Grade, grain, format, frame rate. No compositing at all |
| **Edge seam** | Generated element beside real material in frame | Moderate | Everything in the cut seam, plus perspective, light direction and edge treatment |
| **Contact seam** | A generated element *touching* something real — resting on a surface, held in a hand | **Expensive** | Contact shadow, occlusion, reflection. This is where amateur work dies |
| **Identity seam** | A real, identifiable person joined to synthetic performance or body | ⛔ **Legal before technical** | §5. Do not solve this one with craft |
| ⚡ **Generated seam** | The model is handed the whole real clip as a PLATE and composites the addition itself | Generation cost, not comp cost | §3b — an enumerated input lock, and the plate's own reaction written in |

**The lead-level rule: design the shot so the seam is a cut.** A real hand entering frame and a
generated wide of the same room, joined by a cut, costs a grade pass. The same two elements in one
frame costs a comp. Most of the value in hybrid work is available at the cut seam, and the
`shot-handoff.md` join palette is exactly the tool for planning it — a **J-cut** or an **ellipsis**
turns a contact seam into a cut seam for free.

---

## 3b. ⚡ The generated seam — video-to-video, where the model does the comp

`[SECONDARY · Seedance 2.0 4K production corpus, supplied 2026-09-18]`

**The mode.** You hand the model the entire real clip as a plate and ask for ONE addition. Everything
that normally drifts — identity, wardrobe, room, grade, camera move — is nailed down by the plate
rather than by your prompt, which is why this is the most controlled thing in the whole skill.

⛔ **It changes the taxonomy above.** §3 says *design the shot so the seam is a cut*, because the
contact seam "is where amateur work dies". That rule was written for hand compositing. Here a
contact seam costs one generation, so the calculus inverts: **when a real plate already exists, the
contact seam may now be the cheap one.** The cut-seam rule still holds everywhere the plate does not.

### The four things the prompt must do

**1. Enumerate the lock. Do not summarise it.** Not *"preserve the source"* — name the objects:
*"white desk, dark laptop, blue pen, switched-off external monitor with its golden lamp reflection,
the teal anime figure by the wall, the room, the warm tungsten lighting, the color grade, and the
exact handheld orbit."* An enumerated lock is checkable frame by frame; a summarised one is a hope.

**2. Forbid the four verbs by name.** *"Do NOT re-grade, re-time, smooth, or re-frame anything."*
Each is a thing a video model will helpfully do to a plate, and each destroys the reason you used a
plate.

**3. ⚡ Write the plate's REACTION into the additions list.** This is the craft of the whole mode,
and it is one clause: *"The ONLY additions are the creature, the light it emits/casts, its contact
shadows, the wet film it leaves, and **the laptop's slight physical reaction to its grip**."* A comp
reads as real when **the plate responds to the thing added** — a surface takes weight, a light
spills, a shadow lands, a wet mark stays. List those as additions in their own right or the element
will sit on top of the picture like a sticker.

**4. State the spatial relationship in comp language.** *"Parallax-locked to the screen plane and the
desk; correct occlusion."* *"Composition & grade INHERITED."* These are the terms that decide
whether the addition lives in the scene or in front of it.

### What it is good for, and what it costs

| ✅ Reach for it when | ⛔ Do not |
|---|---|
| The plate already exists and is right — a real room, a real product, a real hand | The plate is wrong. **You cannot fix the plate**, and a mediocre source is now a mediocre shot with a creature in it |
| The addition must touch, occlude or light something real | The addition needs the camera to move differently. The camera is the plate's |
| Identity, location and grade continuity matter more than staging freedom | You need several variations of the staging — that is i2v, where the frame is yours |

⛔ **And the legal section gets MORE load-bearing, not less.** This mode makes it trivial to put a
synthetic element onto real footage of a real, identifiable person — which is the **identity seam**,
and §5 is unchanged by the fact that it is now easy. Easy is exactly why it needs the check. A plate
of a person you do not have a release for is not made safe by the addition being original.

## 4. ⛔ What to shoot vs what to generate

**No documented decision rule exists.** Searched; everything located was vendor marketing.
**[UNVERIFIED]** What follows is derived from what this skill already knows about model failure
modes, and it is ours.

**Shoot it when the model is structurally bad at it:**

- **Legible text and brand marks** — already a hard rule here (mode A). A phone shot of the real pack
  is faster than any prompt.
- **A specific real product**, where drift is a compliance problem and not just a look problem.
- **Hands performing a precise task** — the pipeline's most persistent artifact class
  (`realism-qa.md` V6).
- **A real place you are claiming is real** — the client's actual site, the actual shop.
- **The product doing the thing the ad claims it does.** ⛔ This one is not a craft judgement at all;
  see §5.1.

**Generate it when shooting is impossible or disproportionate:** a character you do not have, a scale
or camera move you cannot achieve, weather and time of day you cannot wait for, and **volume** — the
variants a hook test needs.

⛔ **And budget for the ratio.** The best-documented generative production reported roughly **300:1**
source-to-final for ~90 seconds of footage, and worked by *"documentary-style editing"* — cutting
what came back rather than executing a script. [SECONDARY · fxguide, *Air Head* · checked 2026-08-29 ·
2024-era model; discount for improvement] Hybrid work does not remove that; it moves the selects load
into a stage the runbook budgets at 20 minutes. **A hybrid video is not a `production-runbook.md`
variant** — the plate shoot and the match pass are extra stages, and it should be timed as a setup
until `stage_timer.py` says otherwise.

---

## 5. ⛔ Rights, disclosure and provenance — read before shooting

**The ground moved in 2026 and it moved onto exactly this kind of work.** Two regimes became live
within the last month.

### 5.1 The finding that outranks everything else in this file

**The product-demonstration doctrine is sixty years old and it is about proof, not about technique.**
In the sandpaper-shave case, a plexiglass-and-sand mock-up stood in for sandpaper in a televised
demonstration. It is deceptive to

> *"convey to television viewers the false impression that they are seeing an actual test, experiment
> or demonstration which prove a product claim when they are not, because of the undisclosed use of
> mock-ups."*

— while mashed potatoes standing in for ice cream **purely for visual appeal** is acceptable. The line
is whether *"the focus of the commercial becomes the undisclosed prop and the viewer is invited to
see for himself the truth of the claims."* [PRIMARY · *FTC v. Colgate-Palmolive Co.*, 380 U.S. 374
(1965) · checked 2026-08-29]

**Translated:**

- An AI-generated *environment* behind a real product → the potato-prop case. Appearance only.
- An AI-generated shot of **the product performing** — absorbing, cleaning, whitening, lasting,
  fitting, powering a house → **the sandpaper case.** ⛔ And note the sting: **disclosing "AI-generated"
  may not cure it**, because the deception is about the *claim being unproven*, not about the
  *technique being undisclosed*.

**The house rule: the proof shot is shot.** If a frame is doing the work of demonstrating a claim,
it is captured, not generated — and if it cannot be captured, the claim comes out of the script
(`compliance.md`).

### 5.2 Platform policy — the trigger is "altered", and proportion is irrelevant

Every policy is drafted disjunctively. **Nothing turns on how much of the video is synthetic.**

- **TikTok** is the only platform that defines the partial case: label content *"significantly edited
  by AI"*, meaning it *"uses real images/video as source material, but has been modified by AI beyond
  minor corrections or enhancements."* Named triggers include subjects *"portrayed doing something
  they didn't do"* or *"saying something they didn't say."* [PRIMARY · TikTok Support, AI-generated
  content · checked 2026-08-29] Its guidelines also reach *"edited, spliced, or combined"* media —
  the closest anything comes to addressing a mixed timeline — but gated on misleading about
  real-world events, so ordinary product assembly is not caught. [PRIMARY · TikTok Community
  Guidelines · checked 2026-08-29]
- **YouTube** requires disclosure when content *"alters footage of a real event or place"* — ⛔ **no
  proportionality threshold at all.** Usefully, the named *exemptions* cover routine finishing:
  colour adjustment, lighting filters, sharpening, upscaling and repair. [PRIMARY · YouTube Help ·
  checked 2026-08-29]
- **Meta**: disclosure whenever content is *"digitally created **or altered**"*; the harsher
  consequence (labelling, ad rejection) is reserved for high risk of deceiving *"on a matter of public
  importance"*, which a product ad is not. [PRIMARY · Meta Transparency Center · checked 2026-08-29]
  ⛔ **Meta's advertiser-facing pages are robots-disallowed and were not read** — the ad-specific
  requirement is unverified here.

**Two live statutes:**

- **New York's synthetic-performer disclosure, in force 9 June 2026.** Ads must *"conspicuously
  disclose"* the presence of a synthetic performer. ⛔ **Background performers count** — a generated
  passer-by behind a real product triggers it. $1,000 first violation, $5,000 after. Digital replicas
  of *identifiable real people* are carved out of this statute and land under right-of-publicity law
  instead. [PRIMARY · NY S8420A · SECONDARY · Reed Smith · checked 2026-08-29]
- **EU AI Act Article 50, applicable since 2 August 2026** — deployers of a system that *"generates
  **or manipulates**"* image, audio or video constituting a deep fake must disclose. The
  artistic/creative carve-out **reduces** the obligation to a non-intrusive existence disclosure; it
  does not remove it, and whether a commercial is *"evidently artistic"* is unsettled. ⛔ Read from a
  widely-used unofficial reproduction — **verify against EUR-Lex before relying on it.**

⛔ **And a negative finding worth knowing:** 16 CFR 255 (the Endorsement Guides) contains **no
provision addressing AI-generated endorsers**. The nearest hook is the requirement that ads
representing people as *"actual consumers"* either use actual consumers or *"clearly and
conspicuously disclose"* otherwise — which a synthetic testimonial sits squarely inside, by analogy
rather than by text. [PRIMARY · 16 CFR Part 255 · checked 2026-08-29]

### 5.3 Provenance through a mixed timeline

The C2PA spec models this case directly: a **composed asset** is built from *"ingredients"*, and
⛔ *"when an ingredient contains one or more C2PA manifests, those manifests **shall** be inserted into
this asset's C2PA Manifest Store."* [PRIMARY · C2PA Specification 2.1 · checked 2026-08-29] So a
conformant export from a hybrid timeline is *supposed* to carry every source clip's provenance
forward.

And there is a vocabulary term for exactly this work: **`compositeWithTrainedAlgorithmicMedia`** —
*"augmentation, correction or enhancement using a Generative AI model"* — alongside
`trainedAlgorithmicMedia`, `composite` and `digitalCapture`. [PRIMARY · IPTC Digital Source Type
NewsCodes · checked 2026-08-29] This matters because YouTube **auto-labels content carrying C2PA
metadata**: provenance you attach is disclosure you no longer have to remember to make.

⛔ Whether the NLE in this pipeline actually preserves ingredient manifests on export is
**unverified** — test it before relying on it.

---

## 6. The workflow

1. **Decide the seam first** (§3), at the storyboard. It sets the cost of everything after.
2. **Decide shoot-vs-generate** (§4) — and route any **proof shot** to capture (§5.1).
3. **Shoot the plate with the 90-second kit** (§2). Log focal length and stabilisation state.
4. **Generate to the plate**, not to a mood board — the plate is the colour and detail reference.
5. **Match, in order:** exposure → colour → saturation → gamma → black level → lens character →
   soften → grain over the whole frame (§1.1). Grade the **mid-tones** first (§1.2).
6. **Conform the format** — frame rate, resolution, colour space — with `export_qc.py`.
7. **Disclose** per §5.2, and attach provenance where the tooling allows (§5.3).
8. **Register the episode** noting which shots were captured and which generated — that record is
   what makes a later compliance question answerable (`series-continuity.md` §6.1).

---

## 7. What this file cannot tell you

- **Whether mismatched synthetic motion blur is actually a cutting tell.** Widely asserted, no
  credible source (§1.4).
- **How to match grain size.** No rule located.
- **A minimum plate-capture standard for a phone.** Undocumented; §2's kit is ours. The VES guide
  (free, CC-BY, April 2026) is the document that would settle it and it could not be read.
- **A shoot-vs-generate decision rule from anyone.** Undocumented; §4 is ours.
- **What Meta requires of advertisers specifically** — robots-disallowed, unread.
- **Whether a commercial counts as "evidently artistic" under the EU AI Act**, which changes the
  disclosure burden. Unsettled in every source read.
- **Whether any regulator has ruled on AI-generated imagery in a product depiction.** No NAD decision
  addressing it was found — an absence of finding, not evidence of absence.
- **Anything measured in this pipeline.** No hybrid shot has been produced here yet. The whole file
  is doctrine awaiting its first test, which by this skill's own record is worth about half a day.
