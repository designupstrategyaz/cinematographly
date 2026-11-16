# Cinematography craft — the layer under the cheatsheet

**When to read this:** a shot is not working and "make it more cinematic" is the only note you have;
you are writing a start-frame prompt and need to know what to specify and what is pointless to type;
a client says the footage reads flat, lit, or fake and you need to name the fault; a generated frame
is technically clean and still reads amateur and you need to name which compositional rule it broke;
you are deciding whether a craft decision belongs in the prompt, the frame, the edit, or nowhere.
`craft-cheatsheet.md` is the fast lookup. **This is the reasoning underneath it, so you can derive
the right answer in a case neither file lists.**

Facts tiered per `research-quality.md`, checked **2026-08-28**. The craft is durable — Alton
published this physics in 1949 and it has not moved. **The AI-model claims in §7 decay in about a
quarter.** A layer of ten craft books — Brown, Malkiewicz & Mullen, Ward, Katz, Van Hurkman, Monaco,
Davies and two StudioBinder primers — was merged in on the same date through local extractions;
**§5 is new and comes almost entirely from them**, and §9 records what that provenance is worth.

---

## 1. Lighting as a decision system

**1.1 The founding logic.** *"in interior photography, lighting still imitates the principal light,
or sunlight, and the secondary and tertiary lights, the reflected light from the clouds and the
surrounding landscape."* [PRIMARY · Alton, *Painting with Light* ch. 2 · checked 2026-08-28] Key =
sun, fill = sky and bounce. Motivation is not etiquette: the viewer runs an unconscious physical
model of the room, and light that violates it registers as **lit** even when they cannot name the
fault (`realism-qa.md` V3, V9). Alton's second point matters more: a tree lit only by the sun reads
round, but on a flat screen *"even a round object photographs flat."* **Three-point is a
compensation for lost binocular depth, not a style** — where depth already comes from staging,
atmosphere or colour separation you need less of it, and over-lit faces read fake because it was
paid for twice.

**1.2 Real-looking versus lit is geometry, not intensity.** Three practitioners, three incompatible
methods, one shared result-claim; do not flatten this. **Lubezki** subtracts — *"I wanted to kill
any artifice"* — at a cost of usable light only ~09:30–16:00 and months of added schedule [PRIMARY ·
ASC · cost SECONDARY]. **Deakins** on *1917* does not light but *chooses*: *"as soon as we had cloud
cover, we would shoot"* [PRIMARY · ASC] — not passivity, because overcast is a sky-sized soft
source, near-shadowless and direction-neutral, therefore **matchable** across a two-hour apparent
single take. He picked a light quality by picking a weather condition. **Fraser** engineers it on
*Dune*: *"I backlit the actors… to avoid dark 'guest' eye sockets"* [PRIMARY · Cinematography
World]. **Fraser's is the transferable one:** same sun, but he turned the actor around, so ambient
off sky and sand fills the sockets — nothing added, the axis chosen. **Naturalism is an axis
decision far more than an intensity decision**, hence the commonest amateur tell: a face front-lit
by a near-axis source reads fake because nothing in nature is a small bright object one metre in
front of a person's face. [UNVERIFIED · synthesis, consistent with Alton]

**1.3 Hard and soft are a ratio, not a fixture.** Quality is *"the breadth and nature of the
transition between light and shadow — i.e., the 'shadow edge transfer,'"* determined by *"the size
of the light source relative to its distance from the subject"* [PRIMARY · Jay Holben, "Light
Quality 101", theasc.com]. **Softness is angular subtense and nothing else** — the sun is the
hardest light we know because at 150 million km it subtends ~0.5°, and a 4×4 bounce is soft at 60 cm
and hard at 10 m. Two consequences are coupled although most people treat them as independent:
closer is softer **and** falls off faster (`I = 1/d²`), while a farther, larger source spreads more
evenly. **You cannot buy wrap and evenness from one position**, and the escape — a bigger source
further away — costs money. Hence Deakins' order: *"Quality of light, aperture and cost – in that
order."* [PRIMARY · rogerdeakins.com forums]

**1.4 Direction.** Alton's reason for off-axis is geometric: *"The more surfaces of an object that
are visible, the better will be the picture."* A frontal source gives a face **one** tonal plane,
off-axis gives **two**; one plane is a mask, two are a head. The professional default is
*"shadow-side to camera positioning with a large soft key light placed off-centre"* [PRIMARY ·
Holben, "The Talking Head"]. **Short-side vs broad-side is the highest-leverage single decision on a
face:** keying the *far* side sculpts, the *near* side flattens and widens. Most weak talking-head
footage is broad-side keyed. [PRIMARY for the technique · UNVERIFIED for the prevalence]

| Axis | Effect on a face | Why — so you can extrapolate |
|---|---|---|
| Frontal / on-axis | flattens, erases structure, reads "shot" not "seen" | one tonal plane; no analogue in nature |
| 3/4 front (~30–45° off, ~20–30° up) | portrait default; nose and cheek shadows meet | mimics a window, or sun plus bounce |
| Side / 90° | statement and withholding in one face; max texture | shadow edge runs down the centreline |
| Back / rim | separates from ground, hides interiority | sockets fall to ambient — "guest eyes" when ambient is weak |
| Top | authority, secrecy, black sockets (*Godfather*) | reads ceiling or interrogation; no fill path to the eyes |
| Under | uncanny, threat | fire is the only natural under-source; the brain flags the rest |

[UNVERIFIED · consolidated from the sources above]

**The five named patterns, which are the same axis in caption space.** The table above is the
*reason*; this one is the *vocabulary*, and the distinction matters because §7.0's rule cuts between
them — "key at 40° camera-left, 25° up" is set-language and buys nothing, while **butterfly, loop,
Rembrandt, split and rim are among the most caption-dense lighting phrases in existence**: every
stock-photo caption, headshot listing and portrait-photography post uses them. §7.1 already rates
named lighting styles **T**; it simply never enumerated the set, so a writer had two of the five
[SECONDARY · StudioBinder, *Film Lighting: The Ultimate Guide*, 2023 — lead-magnet marketing, no
citations; the geometry is standard portrait convention and is not this source's finding].

| Pattern | Key geometry | **Nose-shadow signature** — how you know you got it | Reads as | UGC-safe? |
|---|---|---|---|---|
| **Butterfly** / Paramount | directly above, on-axis, angled down | symmetric shadow directly under the nose, both cheeks equal | glamour, beauty, authority | ⛔ **no** — it is literally glamour lighting; see §7.1 note and `production-design.md` §4 |
| **Loop** | ~45° to the side, just above the eye line | a small round shadow below and to one side of the nose, **not touching** the cheek shadow | the friendly default; most flattering on most faces | ✅ yes — closest to a real window |
| **Rembrandt** | 50–60° to the side, slightly above eye level | the nose shadow **joins** the cheek shadow, closing a triangle of light under the far eye | drama, interiority | 🟡 only where a single hard window motivates it |
| **Split** | perpendicular, 90°, at eye level | the shadow edge runs down the facial centreline | conflict, division, withholding | 🟡 **under-key it** — a real window with a dark wall opposite does exactly this; at full strength it reads as a portrait |
| **Rim** / kicker | directly behind, or behind and to one side | no nose shadow at all; an edge of light on hair and shoulder | separation, mystery | ⛔ **no** — requires an unmotivated instrument behind the subject. No phone video has a hair light |

⚠️ §7.0's caveat governs all five: a named style *"yields a look-alike, never a measurement."* You
get a plausible butterfly, not a verified one — which is why the nose-shadow column is not
decoration. It is the acceptance test (§8 **F22**), and it is the only reason the table is safe to
ship.

**The width footnote, for when a persona is locked and you are choosing sides across an episode.**
Broad lighting (the camera-facing half lit) **widens** the face; split lighting **pronounces the
nose**; short-side keying narrows both. Low value on a single video, real once the same face
recurs across thirty [SECONDARY · StudioBinder]. ⛔ Use the *which-half-is-lit* definition of
short/broad, never the camera-position one — that source gives both, in body and glossary, and they
are not reconciled anywhere in it (§9 blacklist).

**1.5 Practicals, and why subtraction beats fill.** A practical is both the alibi for the key and a
graphic element: *"A clear bulb gives a cleaner shadow. In a practical that might look 'right' or it
might be 'better' with a frosted bulb"* [PRIMARY · Deakins, forums] — the scare quotes are the
ethic, **"right" and "better" are separate axes and each shot serves one**. His sourceless-looking
*Blade Runner 2049* Wallace office was built from three 25-foot circles of ~35 10K Fresnels each
[PRIMARY · ASC]: **"natural light look" and "no lights" are unrelated claims**, which is why a fully
engineered start frame can still read as found. Going the other way, *"taking away light has become
just as important as adding it"* [SECONDARY · Neil Oseman] — and the portable reason is that **a
fill light raises the shadow *and* adds a second shadow edge, a second catchlight and a second
falloff**, three new pieces of physical evidence to reconcile, where negative fill steepens the
ratio without adding any. That is why negative fill reads natural and fill often does not
[UNVERIFIED · reasoning]. Mullen's corollary: key with hotter practical bulbs and accept holes,
since *"it isn't always necessary to have light on everything in the frame."* [PRIMARY · Mullen ASC]

**Motivate before you brighten — and here the art department is the `[ENVIRONMENT]` block.** The
production instruction is *"have the art department add a lamp to the room, turn it on, and then
you've motivated any additional light you need"* [SECONDARY · StudioBinder, *Film Lighting*, on *The
Whale*'s standing set, *"designed to function with as many practical lights as possible"*, the
practicals *"providing motivation for non-practicals"*]. In this pipeline there is no art
department and no set: the only place a lamp can be added is the object list of a frame prompt.
**So the instruction becomes: put the light source in the environment's noun list, not only in the
lighting block.** A named lamp in `[ENVIRONMENT]` gives the model an object to render *and* gives
the light an in-frame alibi, which is tell V9 fixed at the frame gate rather than argued about
afterwards. `production-design.md` §1 carries it as a required field, and §7 fixes a **practical
inventory per approved environment** so every clip shot in that room arrives pre-motivated — §6.2's
"contrast is a continuity budget" bought at the design stage instead of the grade.

**1.6 Ratio.** **No DP reached states a ratio number**, and a question put to Deakins about
inverse-square and ratio calculation sits at **zero replies on his own forum** [PRIMARY · verified
unanswered] — at this level ratios are read on a monitor and a face, not computed. Conventional
semantics [UNVERIFIED · no named authority]: **1:1–2:1** comedy, commercial, safety, no shadow story
· **4:1** the drama default, a face with two sides · **8:1+** the shadow becomes a character ·
**16:1 / no fill** noir, where the frame stops describing and starts implying. Alton explains *why*
it works, and it is about the audience rather than the face: *"when one cannot see, his imagination
starts to run wild… In the dark there is mystery."* [PRIMARY · ch. 3] **Ratio hands narrative work
to the audience** — a flat face tells you everything and asks nothing, which is the real reason a
1:1 hook underperforms.

**1.7 Ratio numbers now have a named source — and the disagreement survives.** The textbooks do what
the DPs would not: **2:1 naturalistic · 4:1 dramatic · 8:1 and beyond noir** [PRIMARY · Blain Brown,
*Motion Picture and Video Lighting* — via a local extraction, read 2026-08-28]. Malkiewicz & Mullen
give the neighbouring taxonomy — **high key · low key · graduated tonality** — with painterly
anchors (Turner and Degas; Rembrandt and Caravaggio; Ingres) and story registers attached [PRIMARY ·
Kris Malkiewicz & M. David Mullen, *Cinematography: A Guide for Film Makers and Film Teachers* — via
a local extraction, read 2026-08-28]. **Keep both halves of the contradiction:** §1.6 is right that
no working DP reached would state a number, and the textbooks state them anyway. The honest reading
is that ratio numbers are a **teaching notation** — precise enough to plan with, never precise
enough to approve with (§7.2). Graduated tonality is the register nobody names and the one most
naturalistic drama actually occupies: a full range without either the relentless brightness of high
key or the black-dominant field of low key.

Malkiewicz's correction is the operative one, because a model commits the error by default: **low
key is not underexposed.** True low key holds *normal or even overexposed* highlights against deep
shadow — **it is the ratio, not the level, that produces the effect** [PRIMARY · Malkiewicz &
Mullen]. Typing "dark, moody" and accepting a globally murky clip is that amateur fallacy executed
at scale, and it is exactly the failure §7.1 predicts for a "dark side" qualifier.

**1.8 The eight functions — the checklist that turns "make it more cinematic" into a named fault.**
Brown organises lighting by job rather than by style: **mood and tone · a full range of tones ·
colour control · depth and dimension · shape and fullness · separation · texture · exposure**
[PRIMARY · Brown, *Motion Picture and Video Lighting*]. The scoring claim is the useful part —
amateur lighting satisfies one to three of the eight, professional lighting six or seven — because
it converts an adjective into a list you can walk. **A frame that "reads flat" is failing depth,
separation or shape, and those three have three different fixes.** Note where exposure sits: eighth
of eight. Everything in §1.1–1.6 is a way of buying items one to seven.

| Function | What it looks like when it is missing | The fix, in a start frame |
|---|---|---|
| Mood and tone | correctly exposed and emotionally mute | change the ratio, not the level (§1.6–1.7) |
| Full range of tones | a narrow grey band; no true black, no specular | give the frame something black and something bright |
| Colour control | mixed casts nobody chose | one temperature scheme, or one deliberate mismatch (§6.8) |
| Depth and dimension | a paper cut-out on a backdrop | a darker foreground plane, a lit background (§4.2) |
| Shape and fullness | one tonal plane across the face | move the key off axis (§1.4) |
| Separation | subject and ground share a tone at the outline | backlight, or a tonal step at the edge (§5.3) |
| Texture | plastic skin, plastic fabric | a raking angle; texture is a shadow phenomenon |
| Exposure | clipped or crushed | expose for the highlight, recover the shadow (§6.1) |

[Brown's eight functions are PRIMARY; the fault column and the frame-side fixes are UNVERIFIED ·
this file's inference.]

**1.9 The three aspects, the instruments, and the wattage fallacy.** Malkiewicz's analytic frame is
that every source has **three independent dimensions — hardness, angle of throw, colour — and most
amateur setups vary one and leave the other two on default** [PRIMARY · Malkiewicz & Mullen]. That
is the diagnosis under §1.2: naturalism is usually an *angle* problem being treated as an
*intensity* problem. His anti-pattern is blunter still — **judging lights by wattage**, when "a 1K
through diffusion at the right angle does work a 5K direct at the wrong angle can't." Brown says it
from the other side: a 5K fresnel and a 5K open-face produce dramatically different light [PRIMARY ·
Brown, *Motion Picture and Video Lighting*]. **Output is not a quality of light. Apparent size, beam
control and axis are.**

The instrument catalogue is unbuyable here, but it is not useless, because **instrument nouns are
caption-native in a way measurements never are** (§7.0). A caption-writer types "neon sign",
"candlelight", "streetlight", "overcast" — each of which names a size-and-quality bundle — and never
types "4×4 bounce at 60 cm". So the instrument list is really a vocabulary list.

| Named source | Apparent size | Shadow edge | Falloff | In a prompt |
|---|---|---|---|---|
| Sun, clear day | tiny (~0.5°) | razor | none across a room | "harsh midday sun" — reliable |
| Overcast sky | the whole sky | almost none | none | the single most efficient lighting lever |
| Window, north-facing | large and near | soft, directional | fast | "soft window light" — reliable |
| Practical lamp, candle, neon | small, in frame | hard-ish, warm | very fast | says it *and* anchors motivation (§1.5) |
| Softbox or bounce, close | large relative | soft, with wrap | fast (§1.3) | reads studio, not world — use with care |
| Hard spot, far | small relative | hard, controllable | slow and even | "shaft of light", "spotlight" |
| Bare bulb overhead | small | hard, top-down | fast | a whole mood in three words |

[UNVERIFIED · consolidating Brown's and Malkiewicz's instrument taxonomies into the terms this
pipeline can use; the physics column follows §1.3.]

---

## 2. Lens language

**2.1 The correction that unlocks the rest.** *"Image compression is not the result of the focal
length of the lens; it is the result of the relative distance of the camera to the subject and the
subject to the background."* [PRIMARY · Holben, theasc.com] **Lenses do not distort faces. Distance
does; the lens only decides how much of the result you keep.** Two cameras at one distance, matched
for angle of view, give identical perspective, and Holben refuses to name a correct focal length.
This is what makes §7 tractable: **perspective is a property of frame geometry, so it survives into
a start frame even though the focal-length number never does.**

**2.2 The portrait convention, and a named DP who rejects it.** Convention: shoot faces long
(≈85–135mm still-equivalent) from further back, where the nose-to-ear ratio approaches
conversational vision [UNVERIFIED for the band]. The dissent is real: *"I'm a very big believer that
an audience can feel where the camera is in relation to the subject"* — van Hoytema, who refused the
long lens for intimacy on *Oppenheimer* and had Panavision build a **custom close-focus 40mm**,
physically closing the distance instead of simulating closeness optically [PRIMARY · Filmmaker
Magazine]. Deakins shot nearly all of *1917* on a 40mm, going to 35mm *"to accentuate the
claustrophobic feeling"* [PRIMARY · ASC]. **The claim underneath:** a long-lens close-up and a
wide-lens close-up are not interchangeable framings — the long lens says *I am observing this
person*, the short lens close says *I am inside their space*. Note what the 35mm bought:
**claustrophobia, not width** — a wider lens in a small room forces the camera nearer the walls and
the face.

**One practitioner's habit, beside both** [PRACTITIONER · course notes]: faces on about **50–70 mm**, with one wide
and one tight lens for everything else. It is a spoken habit, not a measurement, and it stays its own
range beside the 85–135 mm convention and the 40 mm dissent; do not average the three. It is not a
default. The millimetres may go into a frame prompt (§7.1).

**2.3 Depth of field, and anamorphic in a vertical frame.** Deakins is on both sides. Against the
numerology: **"The depth of field of a 40mm is the same whatever the size of the sensor"** [PRIMARY
· forums] — format blurs nothing by itself, it changes the framing a focal length gives, hence the
lens you pick, hence the depth. For shallow focus deliberately: *"We used the Alexa LF on '1917'
because we liked the shallow depth of field."* The counter-argument [UNVERIFIED · not sourced to any
DP]: **shallow focus is pre-emptive editing** — it decides what matters before the viewer looks,
where deep focus preserves their freedom to search the frame, the precondition for staging in depth
(§4.2). For 9:16 the trade is usually worth taking, but take it as a decision. (Do not attribute an
anti-shallow position to Deakins; that thread is unanswered.) Anamorphic's oval bokeh, streak flares
and edge distortion [SECONDARY · Cooke Optics] are **a catalogue of controlled failures — the lens
signing the frame** — but that identity lives on the horizontal axis, so in 9:16 it is decorative
texture with its structural logic removed [UNVERIFIED · extending a horizontal-cinema source].

**2.4 The bands, sourced — and the dispute inside them.** Three textbooks name focal-length bands on
full frame, and they disagree at the seams: **fisheye below ~23mm · wide 24–35 · standard 35–55 ·
telephoto 55–500** [SECONDARY · StudioBinder, *Camera Lenses Explained* — via a local extraction,
read 2026-08-28], against Brown's **wide 18–35 · normal ~50 · long 85–200+** [PRIMARY · Blain Brown,
*Cinematography: Theory and Practice* — via a local extraction, read 2026-08-28] and Malkiewicz's
near-identical split [PRIMARY · Malkiewicz & Mullen]. **This upgrades §2.2's portrait band from a
convention with no authority to a convention with three** — and note that 35mm is "wide" to one
source and "standard" to another, which is itself the finding: the bands are naming habits, not
thresholds.

The "standard lens sees like the human eye" claim collapses under its own source. StudioBinder
concedes the eye's true field is nearer a **17–25mm** lens and rescues 35–55mm only via the "cone of
visual attention" [SECONDARY · StudioBinder, self-flagged]. **So "normal" is a claim about
attention, not about the eye** — which is why van Hoytema's 40mm up close (§2.2) is not a
contradiction of it: he kept the attention cone and threw away the distance. Malkiewicz supplies the
demonstration worth carrying: **two people at one physical distance read as separated at 24mm and
pressed together at 85mm** [PRIMARY · Malkiewicz & Mullen] — §2.1's fact restated as a *staging*
consequence, and therefore one of the few lens facts that survives into a start frame, because it is
frame geometry and not a lens property. Brown's operational rule is **choose the lens before the
camera position, never after**; one step down it becomes **choose the camera-to-subject distance
before you write the frame prompt**, because distance is the half that survives.

**2.5 The five anamorphic signatures, named.** Not one look but five separable ones — **widescreen
aspect ratio, oval bokeh, edge distortion, falloff, horizontal streak flare** [SECONDARY ·
StudioBinder] — which upgrades §2.3's Cooke citation and sharpens its point: these are inherent
traits of the design, not faults, so you buy the package or none of it. The same source supplies the
separation that matters more here: *Parasite* reached 2.39:1 **spherically**. **Aspect ratio and
lens identity are independent** — so 9:16 is a crop decision, and nothing about the crop makes an
anamorphic token more honest (§2.3 stands).

---

## 3. Camera-movement grammar

**3.1 The principle.** *"If the camera moves it's got to be for a reason"* · *"[Bresson] doesn't
move the camera because he can't find a reason to do it, so why should we?"* [PRIMARY · Deakins,
Hazlitt] — with the honest admission that tools bias the choice anyway, *"the ability to move the
camera… influences what we might choose to do"* [PRIMARY · forums], which is exactly the trap in a
pipeline where every move costs the same nothing to *request*. **Movement quantity is also a genre
signature:** *True Grit* moves more, *No Country for Old Men* less because the reality was harsher.

**3.2 Push-in vs zoom.** A **dolly push** changes camera position, so the background parallaxes and
the viewer experiences *approach*; a **zoom** changes focal length only, so the background scales
with the subject and the viewer experiences *selection* — attention narrowing, not a body moving
[SECONDARY · forum participants, **not** Deakins]. Deakins' own position is more useful than the
rule: **"There is no right way."** He has not zoomed since *The Village*, and notes that film
language is already full of unnatural devices — cuts, desaturation, impossible moves — so "natural"
is not the criterion. **When the push goes cheap** [UNVERIFIED · grounded in the "reason"
principle]: it costs nothing and always reads as *significance approaching*, so it goes cheap the
moment it is the only event in the shot. It earns its keep when it **arrives at new information** —
a micro-expression, a decision, a reveal beside the subject — or when it *races* the subject's
realisation.

**3.3 The test: reveal or decorate. At the end of the move, does the audience know something they
did not know at the start?** New spatial relationship, new object, new eyeline, new scale. If the
only answer is "the shot feels more expensive," it decorates — and in an AI pipeline it also buys
artefacts (§7.3). On *1917* the plan preceded the equipment — *"we would not think about how we
would do it technically. Rather… what we wanted the audience to see"* [PRIMARY · British
Cinematographer]. **Derive the move from what must be seen; choose the rig afterwards** — and here
the rig is a model and a prompt token.

**3.4 Vocabulary, with the meaning rather than the label** [UNVERIFIED · craft-standard]:
**locked-off** — the frame is a proposition and the world moves inside it, **the only mode in which
an audience will search a frame**; **dolly** — a body moving with intent, reads as narration;
**crane/jib** — changes the observer's altitude and therefore the relationship, rising off a scene
being release or abandonment and descending in being commitment; **Steadicam** — a body that walks
but does not breathe, good for following, poor for adrenaline; **handheld** — a *person* present,
carried entirely by involuntary micro-corrections; **gimbal** — the *path* of handheld with none of
the *presence*, the commonest unmotivated move in short-form and what a model hands you when you
type "handheld".

**3.5 Movement and cutting are substitutes** — both redirect attention, and Deakins builds tension
in *Sicario* by **holding** rather than cutting [SECONDARY · Hazlitt]. Murch's hierarchy ranks
spatial continuity astonishingly low:

| 1 Emotion | 2 Story | 3 Rhythm | 4 Eye-trace | 5 2-D plane of screen (incl. the 180° rule) | 6 3-D space |
|---|---|---|---|---|---|
| 51% | 21–23% | 10% | 7% | 5% | 4% |

— Murch, *In the Blink of an Eye* [SECONDARY · two summaries agree on the ordering and on
51/10/7/5/4, and disagree on Story at 21% vs 23%]. **Eye-trace is the bridge:** if the point of
attention sits in the same screen region across a cut the cut disappears, and if it jumps the cut
announces itself. **A camera move is a continuous eye-trace; a cut is a discontinuous one** — which
is why a move running *into* a cut lands harder than one that settles first.

**3.6 Pivot points, and why a move implodes.** Ward's operator-level fix is the one thing in the
movement literature that transfers directly to a keyframe interface. On a zoom or a track, **choose
a pivot point — hold two adjacent sides of the frame at a constant distance from the subject** — or
you get the amateur result, "the frame imploding from all sides" [PRIMARY · Peter Ward, *Picture
Composition for Film and Television* — via a local extraction, read 2026-08-28]. Two more of his
distinctions earn their place: movement divides into **functional** (reframing to hold a moving
subject) and **interpretive** (a planned move for emphasis or mood), and **a move must start and
stop on the action** or it reads as restless. Most short-form movement is interpretive dressed as
functional. His **development shot** — a continuous move that carries the camera to a new viewpoint
and reveals fresh visual information — is §3.3's payload test with a name and a century of use
behind it.

**The pipeline translation is unusually literal: first-and-last-frame interpolation *is* a
pivot-point decision** (§7.1). Two endpoint frames holding the subject at the same offset from the
same two edges reads as a track; two endpoints both centred and differing only in scale is the
imploding zoom, and it is what you get by default. [UNVERIFIED · applying Ward to keyframe
interpolation]

**3.7 The dissent on cutting, which is stronger than it looks.** Monaco, via Godard, argues that
**the cut is often the *truer* approximation of natural perception** — "we are seldom interested in
the intervening space" — because we do not pan our attention across a room, we jump it [PRIMARY ·
James Monaco, *How to Read a Film* — via a local extraction, read 2026-08-28]. That is a direct
dissent from the intuition that a move is more natural than a cut, and from Bazin's long-take
realism. Monaco's resolution is the portable part: **montage and mise-en-scène are interchangeable
principles of organisation** — montage does in time what mise-en-scène does in space — so neither is
intrinsically more real, and the choice is what the beat needs. **Operative form here: a beat you
cannot generate as a move, you can nearly always generate as two frames and a cut, and the cut is
not the degraded version.** It is also the cheaper one (§7.1).

**3.8 ⚡ Motion that is not boring — and why "a better move" is the wrong answer.**

The complaint "the motion is boring" almost never has a camera solution, and reaching for one is how
a 30-second film acquires five moves and no argument. The diagnosis is already in this skill and it
is mechanical: **a MOTION block whose only verbs are camera verbs is a filter over a photograph**
(`motion-craft.md` §6 item 6, and `prompt_lint.py` warns on it). A push across a still world is not
motion; it is a slow crop.

**The five levers. A camera move is one of them — with a job, not as a last resort.**

| # | Lever | What it buys | Cost |
|---|---|---|---|
| 1 | **Subject motion, plus one secondary action** | a glance, a weight shift, a sleeve, steam, a curtain — one subordinate move is the difference between a mannequin and a person (`motion-craft.md` §1) | free, it is a sentence |
| 2 | **The world moving through a held frame** | locked-off is *"the only mode in which an audience will search a frame"* (§3.4). A still camera on a busy world reads as confidence | free |
| 3 | **The LIGHT moving** | a shaft crossing, a cloud passing, a lamp switched on, dust turning in a beam. Motion with no geometry to warp, so the one kind a model cannot break | free, and generation-safe |
| 4 | **Speed, not path** | a ramp restructures the rhythm of a shot whose path is plain (`motion-design.md` §3). ⛔ Ramp **down** on generated footage — slowing hides artifacts, speeding up exposes them | free, post-side |
| 5 | **A camera move with a job** | **reveal** (what could I not see before?), **follow** (keep a moving subject), **connect** (two things in one take), **change scale** (the world grows or shrinks around the subject), **carry energy across a cut** (a matched vector, §3.8's last paragraph). An approaching moving camera drew a stronger sensorimotor response than a static or zooming one and was rated the most involving `[PRIMARY* · Heimann et al., *Journal of Cognitive Neuroscience* 26(9), 2014; Heimann et al., *PLoS ONE* 14(3), 2019 · abstracts via fetch summary · checked 2026-10-04]` | a generation, plus artifacts — so spend it where the job is, and obey the trigger rule below |

⛔ **A held frame is a choice too, and it needs its reason** — the frame is there to be searched, the
joke is deadpan, the performance is the event. **Neither the hold nor the move is the default; the
sequence decides** (`sequence-grammar.md` §2b, the camera plan). The measured mix in five festival AI
shorts is roughly **four shots in ten with a deliberate move** (`specifics-catalogue.md` §10.3) — a
mix, not a rule in either direction.

⚠️ **SUPERSEDES IN PLACE** (2026-10-04) — previously: "The five levers, cheapest first. Only the
fifth is a camera move." with the move's row reading "last, and only when §3.3's payload test
passes", and the Static row below reading "The default answer". `[measured 2026-10-03 · lab-00005 ·
metrics.py · 20 briefs per arm]` With that wording in the skill, **97 %** of the shots in 20
Claude-written ads were locked off (Kimi K3 84 %, DeepSeek V4 Pro 73 %), against **58 %** and **35 %**
when the same models wrote without the skill. A corrective against push-in filler had become a frozen
camera, and the blind judges' sequence-variety score did not move with the skill at all.

⚡ **The single highest-value reframe: the camera should be the REASON you can see something, not
the thing you are watching.** Ward's *development shot* is that with a century behind it (§3.6).
Every move that survives review answers "what could I not see before?"

**Advanced moves, and how each is actually obtained here.** The standard twelve
[SECONDARY · StudioBinder, *The Shot List* Ep.6 — vocabulary citable, attributions not, §9.1] are
not equally available, and the useful question is never "which move" but "which mechanism".

| Move | Here | How you actually get it |
|---|---|---|
| Static | **T**, and under-rated | A choice with a reason, not the default. Give the world something to do (levers 1–3), and say on the chain why the frame holds |
| Pan · tilt | **T** | One per clip. In 9:16 a tilt has 16 units to travel and a pan has 9 — **the vertical move is the native one**, which inverts the horizontal-cinema habit |
| Push in · pull out | **T** | The safest completion of any sentence, which is why a prompt-only pipeline converges on it (`motion-design.md` §1) — reach past it deliberately |
| Zoom | **T** weak | Not a camera move at all: focal length, so the background *scales* rather than parallaxing (§3.2). The model fakes it by cropping, so you lose resolution rather than gain compression |
| Crash zoom / whip pan | **T** as a **JOIN, not a move** | ⚡ Generate the blur at the *tail* of A and the *head* of B and hide the cut inside it. That is one transition out of two clips, and it is the cheapest "impossible" energy in the format (`editing-and-audio.md`) |
| **Dolly zoom** | ⛔ **X** | Two continuous parameters at once, one of them focal length, and **no 2026 model exposes a focal-length channel** — nothing counter-rotates against the dolly, so you get a push with a wobble at full price. Buy the *meaning* — the background relationship changing under a still subject — as two frames and a cut, or as a scale change between interpolation endpoints. `prompt_lint.py` refuses it |
| **Roll** | **T**, and ⛔ handle with care | Absent from this skill until 2026-09-08. It degrades **worse in 9:16 than in any other ratio**: the frame's own diagonal already sits ~29° from vertical (§5.10), so the tilt is read against an already-steep reference and reads as a mistake sooner |
| Tracking · trucking · crabbing | **F** | A path, and paths do not survive text. Supply it: first-and-last-frame, or motion transfer (`motion-design.md` §2.1–2.2) |
| Arc / orbit | **T** weak | The one path a model volunteers, and vendors document warping when it is combined with anything (§7.2). Alone and short, or not at all |
| Boom · pedestal · crane | **F** | Two endpoint frames at different heights *is* the boom. This is the clearest case where the interpolation is the rig |
| **Handheld** | ⛔ **X** as written | You get a **gimbal**: the path with none of the presence, because presence is involuntary micro-correction and the model has no body to correct (§3.4). Supply it by motion transfer, or add jitter in post |
| **"Random movement"** — handheld shake plus arbitrary zooms, for documentary realism | ⛔ **X**, and it is the one this pipeline most needs | The source names it as *the* approach for documentary realism, which is exactly the register a UGC ad is trying to reach — and it is precisely the thing generated motion cannot produce, because "arbitrary" is the property a next-frame predictor has no reason to have (`motion-craft.md` §1). ⚡ **Name it as the gap rather than prompting at it**: it is bought in post, or not at all |
| **Rack focus** | **F** | Absent until 2026-09-08. Attention transfer inside one shot with no cut — exactly what short form wants. Buy it as two frames with different focus, or as a post blur pass |
| Bird's eye / overhead | ⛔ **an ANGLE, not a move** | Mixing axes is how prompt vocabulary degrades (§9.0). It belongs to the height ladder (§5.4) — where it is also the one angle 9:16 has *more* room for than 16:9 |

⚡ **The technique that buys the most, and nobody reaches for it: assemble one impossible move out of
several clips.** A model gives you ≤8 seconds and one behaviour. A 20-second continuous move is
three clips whose **motion vectors agree across the joins** — the same direction, the same speed,
cut mid-movement. Match-on-action is the mechanism and it is the *most-missed* cut in the corpus at
**32.4%** (`editing-storytelling.md` §3.1), which is another way of saying it is the cheapest
invisibility available. Design the vector at the storyboard; you cannot discover it in AI footage.

**And the trigger rule, which costs nothing:** ⛔ **the camera does not start before the subject
does.** A move that begins on frame 1 is a filter. A move that begins because she stood up is
camera work — the same path, the same credits, and the only difference is *what the first half-second
is for*. This is §3.6's "start and stop on the action" and `motion-craft.md` §6's anticipation
arriving at the same instruction from two directions.

**3.9 The script signal → the move.** §3.8 says which mechanism; this says when. ⚡ And when you have the job but want the actual executable move with its numbers, that is `move-catalogue.md` — this table names a CLASS, that file names the move. Keyed on what is in
front of you, because "which move" is the wrong question at the desk — the same inverse-index
`editing-and-audio.md` uses for transitions, and for the same reason.

⛔ **If nothing in the writing asks for a move, the answer is a static frame with a live world.** That
is not a fallback. It is the correct answer most of the time.

| The script says | The move | Because |
|---|---|---|
| A fact the audience must weigh | **static**, subject moving | the only mode in which they will search the frame (§3.4) |
| Something is revealed *beside* the subject | **pan or tilt**, ending on it | the payload is the new thing, so the move must arrive at it (§3.3) |
| Significance approaching; a decision forming | **push in** — but only if it lands on new information | otherwise it is the cheap default (§3.2) |
| The subject is losing ground; the world is bigger than they thought | **pull out** | disconnection is the pull-out's actual meaning |
| Two things are the same thing | **no move — a match cut** | plan both frames to match; you cannot find it in the rushes (`editing-and-audio.md`) |
| Energy rises with the music | **whip as a JOIN**, beat-matched | one per video is seasoning, five is a template |
| Scale, or a person made small | **boom/crane** = two endpoint frames | the interpolation is the rig |
| A world that keeps going past the frame | ⛔ **a cut, not a move** | a generative clip has no off-screen world; an entrance is a cut (§5.9) |
| Documentary presence, "someone is holding this" | ⛔ **not a prompt** | motion transfer, or post jitter. The word returns a gimbal (§3.4) |
| A joke's turn | ⛔ **hold absolutely still through the protected air** | ~1.4–1.6 s before the turn and ~0.8–1.5 s after are measured (`comedy-craft.md` §4). **A move is an event, and that air has to be empty** — this is the one place where the timing evidence, not taste, forbids the move |
| Tension building on a held face | **hold, do not cut** | Deakins builds *Sicario*'s tension by holding (§3.5) |

⛔ **Note what this table is NOT: a genre mapping.** There is no action/drama/comedy → movement rule
here, because the evidence for one does not exist — and §9.0 blacklists exactly that shape of claim
(genre→lighting mappings asserted with no frequency data, then immunised against their own
counterexample). **The beat's function picks the move; the genre does not.** The one row above that
looks like a genre rule — comedy — is not one: it is a measured timing constraint that happens to
appear in comedy, and it would apply identically to any beat with protected air.

---

**If the brief arrives as a name** — "like Fincher", "Deakins-ish", "a Wes Anderson thing" —
`style-transfer.md` decomposes it into the parameters below, and records what the primary sources
actually support (very little of the folklore, and no lighting ratios at all).

**Obtaining a move is a separate problem from choosing one.** This section is the grammar — what a
move means and when it is motivated. **`motion-design.md` is the mechanism**: first-and-last-frame
constraint, motion transfer from a driving clip, video references, multi-shot and extension, and
speed ramping — the ladder you climb when a prompt keeps returning the same dolly.

## 4. Staging and blocking

**4.1 Blocking replaces coverage.** Deakins names the divide — some filmmakers *"just stick up
multiple cameras on zoom lenses… For me it doesn't matter"* — and on the Coens, *"most of those
basic decisions are made during pre production"* [PRIMARY · Hazlitt, forums]. **The real argument
for the one shot that plays:** coverage defers the decision to the edit, so the *scene* was never
designed, only the options were. Blocking makes staging carry the meaning, which requires knowing
what the scene is about before you shoot, at the cost that you cannot fix it later. Van Hoytema
supplies the counterintuitive half — **constraint is an asset, not a tax**: *"I love the fact that
there isn't an endless number of possibilities for where to put your camera"* [PRIMARY · Filmmaker
Magazine]. A model that accepts any prompt hands you the endless-possibility problem for free; the
discipline has to be imported (`direction.md` §3).

**4.2 Depth, foreground, and the vertical frame.** Alton on foreground is attention physics, not
taste: *"Never use a lighted lamp… or any other hot object in the foreground, because light catches
the eye."* [PRIMARY] **The eye goes to the brightest thing, then the sharpest, then the moving
thing, then the face, then to whatever is being looked at** [PRIMARY for brightness · UNVERIFIED for
the ordering] — so foreground layers work when they are **darker** than the subject, building depth
without competing, and a bright foreground layer is a leak (§8 F5). Alton's composition law is close
to controlling in 9:16: *"place features of interest in the upper part of the picture… above the
half-line,"* because *"the eyes are in the upper part of the face."* A tall frame gives enormous
real estate below the eyeline and almost none beside it, so **depth staging in vertical runs
front-to-back and top-to-bottom, never left-to-right** [UNVERIFIED · applying Alton to the format] —
and that lower third is the zone `delivery-format.md` reserves for captions, so the subject belongs
high and the depth behind. Alton then refuses to systematise any of it: **"there are no rules or
laws for the creation of close-ups or portraits."**

**4.3 The 180-degree line and eyelines. State the cost correctly:** breaking the line is not
"confusion" as a moral failing, it is a **re-render** — the viewer's spatial model is invalidated
and must be rebuilt, and the attention paying for that rebuild was being spent on the performance.
In a six-second vertical ad that is the whole shot [UNVERIFIED · reasoning]. **But Murch ranks it
fifth of six at 5%** [SECONDARY], below rhythm and eye-trace — a genuine dissent from how the rule
is taught. Portable version: **cross the line if the emotional beat requires it; never cross it to
save a setup.** Eyeline geometry: **height** relative to the lens sets status (above reads
aspiration or deference, below reads authority) and **lateral offset** sets intimacy [PRIMARY ·
Holben · UNVERIFIED generalisation].

**4.4 Katz's geometry — the triangle, the master, and POV as three shots.** Katz's contribution is
that staging has a *solvable geometry*, worked out on paper before anything is shot [PRIMARY ·
Steven D. Katz, *Film Directing Shot by Shot* — via a local extraction, read 2026-08-28]. Four
pieces survive into this pipeline:

- **The triangle system.** Inside the 180° arc, a scene's whole coverage comes from three vertices —
  the external reverses (the over-the-shoulder pair), the internal reverses (matched singles), and
  the parallel or common positions. It is a recipe for **frames that will intercut**, which is
  exactly the property nothing in this pipeline enforces (§7.1).
- **The master as anchor.** Even when a 9:16 ad never plays a wide at length, **generate the master
  frame anyway** — as the geometry reference the closer frames are built against, the same role the
  hero shot plays for colour (§6.7).
- **POV is a triad, not a shot:** glance → object → reaction, with the object's screen direction
  agreeing with the glance. Three generations and one constraint, and the constraint is checkable
  (§8 F10).
- **Mobile staging moves the line.** When actors walk, the axis is redrawn mid-shot — precisely what
  a generative clip does not track, and a reason to keep walk-and-talks short.

Katz also explains *why* the file's multi-figure row (§7.1) is hard for humans too: two subjects are
the triangle, three introduce a second axis and force a decision about which line governs, four or
more become a grouping problem. **The degradation is not only a model limitation; it is the same
geometry getting harder.**

**4.5 Shooting for the cut — the match conditions and the 30° rule.** Ward states the conditions for
an invisible cut as a checklist: intercut shots match in **size, headroom, looking space, lens angle
and camera height**, are colour-matched, carry continuity of action and movement, and — cutting on
the same subject — show a **significant change of angle or size**, conventionally **at least 30°**
[PRIMARY · Ward; the 30° system also in Katz]. **The 30° rule is genuine new leverage**, because it
is a frame-gate test in a pipeline with no other enforcement of cut geometry: two start frames of
one subject less than about 30° apart will read as a jump however good the clips are (§8 F20).

Brown adds the four continuities the shoot must protect — **content, movement, position, time** —
with the observation that audiences forgive most slips **except wardrobe** [PRIMARY · Brown,
*Cinematography: Theory and Practice*]. In a batch pipeline wardrobe is a generation parameter
rather than an on-set discipline, so it is the continuity axis worth spending the identity-lock
budget on (`character-and-props.md`, `realism-qa.md` V13).

**4.6 Depth staging is a cut you do not have to pay for.** §4.2 makes depth an attention argument;
Katz makes it an economic one. **Staging across foreground, middle and background lets one frame
carry two pieces of information, and is an alternative to coverage** [PRIMARY · Katz]. In live
action that buys continuity. Here it buys credits: a foreground reaction against a background action
is **one generation instead of two**, and it sidesteps the §7.1 rows that push inter-shot continuity
into the edit. The 9:16 constraint from §4.2 still binds — depth runs front-to-back and
top-to-bottom, never left-to-right (§5.10).

---

## 5. Composition and frame geometry

**Why this section sits here.** §1 and §2 are about arriving at a frame; this is the frame itself,
and it is the one craft layer that survives into an AI pipeline at *full strength* — a start frame
**is** a composition, so every claim below can either be typed into an image prompt or checked
against the returned pixels. Everything §7 says is lost was measured on set. Nothing here was.

**5.1 The default is not neutral.** Ward's central warning is that a camera converts three
dimensions to two and **always** imprints lens height, tilt, distance and angle on the image, so if
the operator makes no conscious decision, **"auto composition" takes over and the picture becomes a
product of the optics rather than of intent** [PRIMARY · Peter Ward, *Picture Composition for Film
and Television* — via a local extraction, read 2026-08-28]. He is equally clear that the camera's
claim to objective mechanical reproduction is a fallacy for the same reason. The generative analogue
is exact and slightly worse: **a model given no compositional instruction returns the
caption-average frame** — subject centred, eye-level, mid-distance, background evenly interesting —
which is auto-composition performed by a population instead of by a lens. Declining to frame is
still framing, and its result is known in advance. [UNVERIFIED · applying Ward to generation]

**5.2 One focal point, and it is built rather than inherited.** Davies reduces the whole craft to a
single rule: every picture has **one** point of interest emphasised above everything else, and
secondary interest is permitted only as a path back to it [SECONDARY · Phil Davies, *Composition for
Artists* — via a local extraction, read 2026-08-28]. His three failure modes are worth memorising
because a generated frame commits all three: no focal point (the eye scans, finds nothing, leaves),
**two focal points of equal weight**, and a focal point assumed to work "because of what it is."
That last is the important one — **content does not confer focus; characteristics do.** His
green-traffic-light case is a dull object dominating a painting purely on unique hue and local
contrast. Katz names the same mechanism as **dominant contrast**: the eye goes to the area of
greatest contrast [PRIMARY · Steven D. Katz, *Film Directing Shot by Shot*], which is Alton's
brightness law in §4.2 arriving from the composition side.

| Emphasis lever | Strength | Survives into a start frame? |
|---|---|---|
| Local value contrast (light against dark at the subject's edge) | strongest | **yes** — author it; check in greyscale (§8 F13) |
| A hue that appears nowhere else, in an otherwise restrained palette | strong | **yes** — this is the discordant accent (§6.6) |
| Sharpness and detail against looser surroundings | strong | **yes** — "shallow focus" is caption-native (§7.1) |
| Size and scale | moderate | yes, via shot size — the most reliable prompt token |
| Isolation and surrounding quiet | moderate | yes, but a model fills space by default; state the emptiness |
| **Contrast within the subject group** — one figure differing from the others in scale, posture, hue or attention | strong | **yes** — a single frame carrying its own juxtaposition; the cheapest way to make one frame *mean* something, and it needs no cut |
| **An established pattern, then one break in it** | strong | **yes** — the eye goes to the interruption, not the pattern; state both halves ("six identical mugs, one turned over") |
| Motion | overrides all of the above | **no** — a still cannot carry it; it belongs to the clip |

Ward's ranking note: **movement and sound override composition entirely** [PRIMARY · Ward]. In a
still-frame-first pipeline that is good news — you are authoring in the layer that is decided
*before* motion arrives — and a warning, because a moving background element will steal a frame you
carefully balanced.

**The two new rows are worth their own sentence, because they are the only emphasis levers that
produce *narrative* rather than attention.** Contrast between subjects puts the comparison inside
one frame — a still image cannot cross-cut, so a juxtaposition either happens within the borders or
it happens in the edit and costs a second generation. Pattern-then-interrupt is the same trick with
a stronger pull, because it recruits the grouping mechanism of §5.7 and then violates it: the mind
resolves the repetition into one shape, and the exception is what is left over. Both are
caption-native — a photographer would write either sentence under a real photograph — so both are
**T**, unusually for a composition control (§7.1). Both also work as hooks, and `hook-craft.md`
should be where a writer reaches for them; the frame is only where they get built.
[SECONDARY · StudioBinder, *Elements of Composition*, 2023 — the taxonomy; the mechanism is Ward's]

**5.3 Figure and ground, which is where generated frames actually fail.** Ward, drawing on Gestalt:
figure is the shape observed, ground is the context that defines it, they are read **sequentially
and never simultaneously**, and any element that gains prominence *becomes* figure — including one
you meant as background. When two areas compete you get **figure/ground flip** and the shot loses
impact [PRIMARY · Ward]. His working number is usable: the eye's just-noticeable brightness
difference is about **8%**, so a tonal separation below that is not separation at all [PRIMARY ·
Ward]. His named faults are the ones that recur here — the background object "that sits neatly on a
subject's head", and the presenter framed tight against a busy sign, producing divided interest.

**This is the single most common defect in a generated start frame**, because an image model
composes subject and background from the same caption and has no notion of subordination — it
renders the background as interestingly as the subject [UNVERIFIED · inference, consistent with
§7.0]. The three fixes that survive are all frame-side: a **tonal step** at the outline, **focus
separation**, and a **narrower angle from further back** to push the ground away (§2.1). Ward's
summary of the whole discipline: strip enough detail from the ground that it cannot compete.

**A fourth fix, and the only one that is also promptable: frame within a frame.** Put a doorway, a
window, a mirror, an archway, a car windscreen, a gap between two foreground objects, or a hand
holding something into the near plane, and shoot the subject through it. It does four jobs with one
noun: it **occludes** the competing background (§5.3's problem, solved by subtraction rather than
by tone), it forces a **near plane** and so buys depth in a format that has no lateral room for it
(§5.10, §4.6), it **points** — an inner border is a converging line that resolves on the subject
(§5.7's "frustrated journey" answered), and it reads as *found*, because a real phone video shot in
a real room has objects between the camera and the person.

⚡ **It is rated T, which almost no composition control is** (§7.1). "Shot through a doorway",
"framed by the kitchen window", "seen past a shelf of jars" are sentences that appear under real
photographs in quantity, so they survive tokenisation where "figure/ground separation" does not.
That makes it the single highest-leverage composition instruction available as *prompt text* rather
than as frame authoring, and it is the reason this paragraph sits in §5.3 instead of the devices
list — it is not a decoration, it is the fix for the defect the section is about.
[SECONDARY · StudioBinder, *Elements of Composition* — for the device; the depth and occlusion
reasoning is this file's, UNVERIFIED]

⛔ Two limits. The near plane must be **darker and softer** than the subject or it becomes the
figure (§5.3's own flip). And in 9:16 an inner frame that is a *horizontal* letterbox eats the only
axis with room in it — build the inner frame as an upright shape (a doorway, a window jamb, a
vertical gap) or accept the crop cost.

**5.4 The structural skeleton, and the four parameters that rebuild it.** Every shot works on two
planes at once — **content** (what is depicted, carrying depth cues and information) and **form**
(the front-surface arrangement of line, shape, tone and contrast). Most viewers consciously remember
only the content and are affected by the form. Reduce the form to a diagram and you have the
**structural skeleton**, and it can be restructured *without changing the content at all* by moving
four controls: **camera angle, lens angle, camera distance, camera height**, with tilt as a fifth
that shifts the horizon [PRIMARY · Ward]. A house shot square-on is static because it maximises
horizontals; angling to show two sides converts them to diagonals and the frame comes alive.

**The operative version for a start frame: when a frame is dead, do not add elements — re-angle.** A
prompt tempts you toward addition because adding nouns is easy, and addition is usually the wrong
move: it multiplies the competitors in §5.3 while leaving the skeleton exactly as flat as it was.

Camera height deserves its own line because it is both meaning and geometry. On flat ground **the
horizon cuts every similar-size figure at lens height** (Alberti's construction), so height
simultaneously sets status and decides where the horizon falls: low reads dominant, high diminishes
the subject and opens the ground plane like a scale model, eye-level places the horizon behind the
eyes and emphasises the face [PRIMARY · Ward, citing *Touch of Evil* and *Triumph of the Will*].
Davies calls the same lever **vantage point** and adds the reason it is under-used: the default is
standing eye level, roughly five to six feet, which is why most images look like everyone else's
[SECONDARY · Davies]. Both halves survive as prompt text — angle and height words are caption-native
(§7.1, first row).

**The ladder, because "low angle" is four different instructions.** Height is continuous and the
caption vocabulary is not, so name the rung. Each rung's real consequence is *where the horizon
falls*, which is the half nobody states:

| Rung | Lens height | Horizon lands | What it does | 9:16 verdict |
|---|---|---|---|---|
| Overhead / top-down | above the subject | no horizon; the ground plane **is** the frame | pattern, order, smallness; the frame becomes a diagram | ✅ **promote** — the one angle where 9:16 has more usable area than 16:9, because there is no sky to waste |
| Eye level | ~1.5–1.7 m | behind the eyes | neutral, face-forward, the default | ✅ the baseline |
| Shoulder | just below the eyes | across the upper chest | very slightly elevated subject; almost invisible, which is the point | ✅ safe |
| Hip | ~1 m | across the waist | subject gains height and presence without theatre | ✅ **the under-used one** |
| Knee | ~0.5 m | across the thigh | clear dominance; the ceiling or sky enters the frame | 🟡 check what the upper third fills with |
| Ground | on the floor | at the subject's feet; **the ground plane collapses to a line** | monumental, or a bug's-eye look at an object | 🟡 strong flavour, use once |
| High angle (looking down from above eye level, subject on the ground) | above, tilted down | low in the frame, or out of it | diminishes the subject | ⛔ **demote in 9:16** — it fills the bottom third with floor, and that band is already surrendered to captions (§5.10) |

**The demotion is the finding.** In 16:9 a high angle spends a modest strip on foreground floor. In
9:16 the same tilt spends the entire lower third — which `delivery-format.md` has already given
away — so a high-angle vertical frame pays twice for one decision and gets a smaller face. Overhead
and low angles do not have this problem; the plain high angle is the one to write out of the
default vocabulary. [UNVERIFIED · this file's geometry, from the measured safe box in §5.10]

**What an angle MEANS is conditional, and it lives in the sequence (added 2026-09-30).** Ward's
"low reads dominant, high diminishes" is the craft version of a result that holds in experiments only
under conditions: a large angle (~35–40°), a story already about power, and **story order** — shuffled,
the same low-angle pictures stopped making anyone look powerful. A low camera on a face talking to
camera **cost trust**, and eye level was trusted most. Viewers barely remember the angle itself; it
shifts the story they remember. The experiments and the rules they give — eye level as the baseline,
an angle given its partner, direct address kept level — are `sequence-grammar.md` §3.3. Two
corrections to the ladder above: its rows mix **height** (hip, knee, ground at a level camera) with
**tilt** (the high-angle row), and a prompt should state both (`sequence-grammar.md` §3.4); and in the
five reference films, 90.5 % of shots sit at eye level and the low shots are mostly feet crossing
thresholds — angle used for geography, not power (`specifics-catalogue.md` §11.1, §15.4).

**5.5 Balance, visual weight, and the frame as a field of forces.** Visual weight comes from
position (an element near an edge or high in the frame is heavier; for Western viewers left is
heavier than right), size, colour, light and dark, isolation, and the intrinsic interest of the
content — and it works like a seesaw, so a small significant weight far from centre balances a large
one near it [PRIMARY · Ward]. Davies gives the same seesaw and its counter-intuitive half: **weight
is set by contrast, colour and detail far more than by size**, so a small high-contrast boat
outweighs a row of dull buildings, and a counterweight can be an object, a shadow, or an abstract
patch of colour [SECONDARY · Davies].

The frame edge is not neutral either. A static element is perceptually felt to be pulling toward
centre, edge or corner depending on where it sits, with **points of rest** (the centre, and the
mid-diagonal between corner and centre) and **points of ambiguity** that read as unease; **headroom
obeys the same field of forces rather than a fixed margin** — too much and the subject slips out the
bottom, too little and it leaves through the top [PRIMARY · Ward, from the white-dot experiment].

**A disagreement worth keeping.** Ward says dead-centre placement achieves equilibrium but no visual
stress, so the eye consumes the image at once and looks away. Davies says **symmetric subjects
belong dead centre** — the water droplet, the doorway, the frontal portrait — and that forcing every
subject off-centre makes you a slave to thirds [SECONDARY · Davies]. Neither states the rule that
decides between them, but **Davies names the variable Ward does not: symmetry.** Use it as the
tie-break — symmetric subject centred, asymmetric subject offset — and note that a frontal talking
head is the symmetric case, which is why centring a presenter is not the error it is usually called.

**5.6 Thirds and the golden section, demystified by both sources.** Ward reports that Fechner's
golden-rectangle preference experiments **largely failed to replicate**, and that the Greeks used
the ratio as a practical design module rather than because it was the most pleasing shape — while
still recommending thirds as a working default, because it produces an unequal division fast and
under time pressure [PRIMARY · Ward]. Davies goes further and dismisses the golden ratio outright
for picture-making: with so many variables in play, **approximate off-centre placement does the real
work, and 1.5 or 1.7 would serve as well as 1.618**; he flags the position as contested and concedes
the ratio may matter more in logo and layout work [SECONDARY · Davies].

**So: use thirds, and never defend it with the golden section.** Ward's coda is the one to remember
when a format is being sold to you — 16:9 was justified in part by a golden-ratio argument, although
1.778 is not 1.618, and his running case through those chapters is that the conversion was
**commercially, not aesthetically, driven** and carried compositional costs it was never honest
about [PRIMARY · Ward]. 9:16 is the same event again (§5.10).

**5.7 Lines, grouping, and what the eye actually does.** Lines — visible or implied, and an eyeline
counts — channel eye movement, and the eye is drawn to where lines converge or cross. **A vertical
line is commanding, a horizontal is at rest, a diagonal is most active at 45°**, and a strong
directional line must resolve somewhere or the composition frustrates: Ward's phrase for one that
leads nowhere is "a frustrated journey" [PRIMARY · Ward]. Curves lead more softly than straight
lines (Hogarth's line of beauty) and knit disparate elements together. Davies adds the practical
inversion nobody says out loud: **if the lines point away from the subject, lose or soften them** —
a focal point set outside strong converging lines reads as out of place [SECONDARY · Davies].

Grouping is the other half. The mind resolves a complex frame into the simplest patterns it can — by
proximity, by similarity of size and colour, and by closure — so a frame either **groups into a few
shapes at a glance or it does not**, and one that does not forces the eye to search and then to give
up [PRIMARY · Ward, from Arnheim].

The mechanism under all of it, and the named source §4.2's attention ordering was missing: sharp
receptors sit only in the fovea, so the eye builds any image larger than a point out of **saccades**
of roughly 1/20 second each, and Yarbus's recordings show it **fixes on nodes — the face, the eye —
rather than sweeping evenly** [PRIMARY · James Monaco, *How to Read a Film* — via a local
extraction, read 2026-08-28, citing Yarbus]. Monaco's asymmetry is worth carrying too: *"we read
images by directing attention; we do not read sound"* — eyes choose, ears take whatever is
available. Two consequences for a frame: a face wins the first fixation against nearly anything, and
two high-interest nodes mean the scan never settles.

**5.8 Breathing space, filling the frame, and the failure between them.** A subject placed
off-centre needs quiet, uncluttered **breathing space in the direction it faces, looks or moves** —
and the more detailed the focal point, the quieter that space should be; a vignette or a dark sparse
edge can serve as breathing space inside an otherwise busy picture [SECONDARY · Davies]. Katz calls
the same thing **lookspace** and pairs it with headroom [PRIMARY · Katz]. The opposite move —
**filling the frame**, taking the subject to and past the edges — removes the background problem
entirely, reveals texture the viewer would not otherwise see, and reads as deliberate precisely
*because* the crop is obviously close, so no empty space is expected.

**The failure is the middle.** Davies's name for it is "neither one thing nor the other": too tight
for context, too loose to fill, so it is neither breathing space nor frame-filling [SECONDARY ·
Davies]. That middle crop is close to what a model returns by default for a person, which makes this
a live fault at the frame gate rather than a theoretical one [UNVERIFIED · inference].

**A movement demonstration is never frame-filling.** When the shot exists to show how a body moves —
an exercise, a pose, a technique, the explainer mode's demonstrations — the whole body stays inside
the frame for every move, hands and feet included: a limb cut by the edge is the information the
viewer came for. [PRACTITIONER · course notes]

**Headroom as one practitioner frames it** `[PRACTITIONER · course notes · measured from a 360p decode]`. The
measure: the gap from the top of the frame to the top of the main person's detected box, as a share
of frame height, the median per shot family, on MS–CU rows only. On the course's films: presenters
and interviews about 2–12 %, spot coverage about 4–14 %, product 3–22 %. Gear close-ups read about
1 % because the object fills the frame, and a person inside a screen recording is not headroom at
all — leave those rows out. This is data to frame by eye against, not a frame-gate threshold, and it
does not replace the 9:16 eye line (§5.10, F8).

**5.9 Open and closed framing — and why this pipeline is structurally closed.** Closed framing
contains all relevant action inside the frame and refers only to what is seen; open framing lets
action move in and out and treats the frame as a partial window on a larger world that is implied
rather than shown. Three of the ten sources agree on the distinction and on the register it sets —
control and formality versus naturalism and continuing space [PRIMARY · Ward; PRIMARY · Katz;
PRIMARY · Monaco]. Monaco locates it precisely at the edge: open form keeps the viewer *subliminally
aware* of space beyond the border.

**The consequence here is specific and, as far as this file can tell, unstated anywhere: a
generative clip has no off-screen world.** Nothing exists outside the frame to enter it; a model
asked for an entrance invents a body rather than moving one. **So short-form AI work is structurally
closed-frame**, and open framing has to be manufactured in the edit — an entrance becomes a cut —
which is one more item §7.1 pushes downstream. [UNVERIFIED · inference from §7.0]

**5.10 What 9:16 does to all of it.** This extends §4.2 rather than replacing it, and every claim
here applies a horizontal-cinema source to a vertical frame, so treat the section as reasoning
rather than citation [UNVERIFIED throughout, except where marked].

- ⚡ **Measure the canvas before composing on it.** The usable box is **not** the frame: it is
  `y = 15–65%`, `x = 11–72%` of frame height and width — the ad safe zone measured from TikTok's and
  Google's own template files, not from a listicle (`assets/delivery-formats.json`,
  `safe_zone_pct`, measured 2026-09-08). Organic posts get a bigger box (`y = 12–80%`,
  `x = 6–82%`), but **compose to the ad box**: a frame that survives the ad crop survives both, and
  the same start frame is used for both cuts. Everything below follows from those four numbers.

- ⛔ **Exactly one of the four third-lines lands inside the box, and it is the upper horizontal
  one.** Check them: the upper horizontal third at 33.3% is inside `15–65%` ✅; the lower horizontal
  third at 66.7% falls **below** the 65% caption keep-out ⛔; the left vertical third at 33.3% is
  inside `11–72%` ✅ but see the next bullet; the right vertical third at 66.7% is inside `11–72%`
  by four points and is inside the *organic* right keep-out — and the moment a CTA button renders,
  it is gone ⛔. **So "rule of thirds" in vertical means one line.** Anyone applying the four-line
  grid to a 9:16 frame is composing two of their four anchors into furniture.

- **The lateral thirds barely exist even where they fit.** A third-line sits one sixth of the frame
  *width* from centre in any ratio — but in 9:16 that is 1.5 units against a 16-unit height, and a
  head in a medium shot is wider than the offset itself. **"On the left third" and "centred" differ
  by less than a face**, so the offset reads as a mistake rather than as a choice. Which is
  Alton's above-the-half-line law (§4.2) arriving from a second direction, and Davies's "break it
  boldly or not at all" (§5.6) applied to the only axis with room to break it in.

- ⚡ **Four independent constraints converge on the same number: put the eyes at 30–40% of frame
  height.** The upper third line is 33.3%. The vertical centre of the safe box `15–65%` is 40%.
  Alton's above-the-half-line law puts the point of interest above 50%. And headroom that reads
  correct at a medium shot lands the eyes just under the upper third. **Four different arguments,
  one answer, and none of them was derived from the others** — which is the strongest evidence in
  this section. F8 tests it.
- **A two-shot becomes a depth arrangement.** Wide screens *force space between* people in a
  two-shot [PRIMARY · Monaco, on aspect ratio and the codes it permits]; 9:16 inverts it and forces
  people to overlap or stack, so two figures are staged one nearer and one further, never side by
  side.
- **Figure/ground cannot be bought laterally**, so it must come from tone, focus and scale (§5.3).
  This is why the 8% separation threshold is worth taking literally in vertical: there is no lateral
  escape from a busy background.
- **Lookspace runs vertically or not at all.** A subject looking left in 9:16 has almost no space to
  look into. Turn the subject toward the camera, or stage the gaze into depth rather than across
  (§5.8).
- **Counterweights live above and below**, and the lower third is spoken for by captions
  (`delivery-format.md`). The practical canvas is the band `y = 15–65%` — call it the upper half
  plus a little, not "the upper two thirds", which overstates it by fifteen points of frame height
  — with everything below 65% designed *as* breathing space rather than left empty by accident.

- ⛔ **The diagonal is the one depth cue that does not survive the crop.** §5.7 rates a diagonal
  most active at 45°, and §5.4 makes re-angling the first move on a dead frame — but a line drawn
  corner to corner in 9:16 has 9 units of run against 16 of rise, so the frame's own diagonal sits
  about **29° from vertical**, not 45. A "diagonal" composition in vertical is a steep near-vertical
  one, and it reads as a tilt rather than as movement into depth. Two consequences: **a Dutch angle
  degrades worse in 9:16 than in any other ratio** — the reference against which the tilt is read is
  itself already steep — and **depth in vertical has to be bought with scale, occlusion and tone
  (the near plane of §5.3's frame-within-a-frame), never with a leading line running across the
  frame.** [UNVERIFIED · geometry, this file]

- **One-point perspective and radial balance are the two arrangements that are *better* in
  vertical.** A corridor, a road, a supermarket aisle, an escalator: a single vanishing point on
  the centreline needs height rather than width, and the format supplies it. Radial balance —
  everything arranged around one centre — likewise. Both are also caption-native ("one-point
  perspective", "symmetrical corridor"), so they are **T**, and both are the answer to the previous
  bullet: they put depth on the vertical axis instead of the diagonal one. [SECONDARY ·
  StudioBinder, *Elements of Composition*, for the terms; the vertical argument is this file's]

- **Lookroom inverts with gaze direction.** A subject looking *down* — at a phone, a product, a
  cup — composes, because the space they are looking into is the caption band that was surrendered
  anyway. A subject looking *up* does not, because the space above is the 15% already lost to the
  profile row. So of the two vertical gaze directions only one is free, and it is the one that also
  happens to be what people actually do on their phones.
- **Treat the format as a constraint with costs, not as a style.** Ward's honesty about 16:9 is the
  model: the format changed for commercial reasons and the composition paid for it [PRIMARY · Ward].
  Anyone defending 9:16 aesthetically is doing what the broadcasters did.

---

## 6. Exposure, contrast and colour as narrative

**6.1 Where to place skin.** [UNVERIFIED — no IRE or stop figure was verifiable against a named ASC
authority; treat every number as convention, not citation.] Practice places average Caucasian skin
roughly ½–1 stop above middle grey, with darker skin placed relative to *its own* reflectance rather
than a fixed number — **skin belongs where its texture survives**, not where a meter says. Deakins
rejects instrument-led exposure outright: *"I do very little in the DI… And I don't look at a
histogram."* [PRIMARY · forums] **The reasoning that outlives the numbers:** on a log sensor the
decision is not correct-versus-incorrect, it is *where in the transfer curve skin's tonal separation
should be widest*. Low, skin gains mystery and loses texture; high, it approaches the shoulder where
separation collapses and faces go waxy — the waxy `realism-qa.md` V1 chases from the other end. And
the asymmetry that is the whole of digital exposure discipline: **a clipped highlight has no data
and cannot be recovered; a crushed shadow usually has data and can be lifted at the cost of noise.**
Expose for the highlight; control the shadow with negative fill (§1.5), not in the grade.
[UNVERIFIED · standard]

**6.2 Contrast is a continuity constraint before it is a mood setting.** *1917* is the instructive
inverse of Alton: Deakins chose the **lowest-contrast** condition available, not for beauty but
because low contrast is **matchable** and an apparent single take cannot survive a moving key
[PRIMARY · ASC + British Cinematographer]. **Whenever shots must intercut, contrast is a continuity
budget** — the most transferable idea here for a batch pipeline, where every clip is generated
independently and nothing enforces a shared key (§7.1, `realism-qa.md` §5).

**6.3 Colour as story structure.** Storaro is the maximalist — colour as a symbolic system mapped to
the script before shooting: *"Photography means write with light. So I was trying to write with
light, with these elements — the colors — the story itself."* He assigns a fixed meaning to each
step of the spectrum, from *"Black is the unconscious"* up to white, *"equilibrium"*, written
*"sequence by sequence, on the script itself… only then can I start filming"* [PRIMARY · via No Film
School and Film Comment] — **a colour script written against the script, before photography.** Block
is the formalist and gives the operative rule: *"Contrast of visual components increases visual
intensity and affinity decreases visual intensity"* · *"Make visual rules that satisfy your
requirements, but whatever you decide, adhere to your rules"* [SECONDARY · via a summary of *The
Visual Story*; the text was not reachable]. **The usable synthesis: Storaro says colour can mean;
Block says the meaning is delivered by change over time, not by a palette.** A blue scene means
nothing; a blue scene *after* an orange scene means something. In a 15–30 s vertical ad you get
roughly **one colour-structural move** — establish, then break it once, on the beat that matters
(`script-craft.md`).

**6.4 What a "look" consists of.** Deakins dismantles the mystique: the LUT *"is not hard to do.
Just shoot some tests and take them to the DI suite."* He uses **the same LUT across all his
projects**, adjusting only contrast curve and saturation, and attributes the fact that *No Country
for Old Men* and *Prisoners* "look diametrically different" to lighting, design and wardrobe
[PRIMARY · forums]. Van Hoytema chose the restriction of an analog grade — *"you cannot just use
power windows"* — to force decisions on set [PRIMARY]. **So a look = (1) a transfer curve, (2) a
saturation and hue-shift character, (3) the physical content the curve is applied to.** Item 3 is
the majority of it and **cannot be bought as a LUT** — which is the justification for §7.

**6.5 Place and fall — §6.1's method, now with a name behind it.** Brown adapts Ansel Adams' Zone
System to motion picture work: measure the scene, **place** the critical tone where you want it, and
let everything else **fall** where it lands [PRIMARY · Blain Brown, *Cinematography: Theory and
Practice* — via a local extraction, read 2026-08-28]. Zone 5 is middle grey, Zone 3 a shadow that
still holds detail, Zone 7 a highlight that still holds detail; a face placed at Zone 5 reads
plainly lit, at Zone 7 glowing, at Zone 3 ominous. Malkiewicz & Mullen give the identical move as
curve placement — **toe, straight line, shoulder** — and add that the cinematographer who knows only
"expose for the face" has abandoned most of the available latitude [PRIMARY · Malkiewicz & Mullen].
Brown lists "expose for the face" as an anti-pattern for the same reason: sometimes right, ruinous
as a universal rule.

**This upgrades §6.1 from an unsourced convention to a named method** without changing its
conclusion — place-and-fall *is* the "where in the transfer curve should skin's separation be
widest" question, with a vocabulary attached. And it settles the shape of the gap: **neither
textbook gives an IRE or stop figure for skin either.** The absence recorded in §6.1 was not a
research failure. It is what the literature actually says.

**6.6 Colour schemes as a buildable structure, not a mood word.** StudioBinder names four wheel
relationships — **monochromatic, complementary, analogous, triadic** — plus three structural moves:
**discordant** (a deliberate break from the established scheme), **associative** (a colour bound to
a character or object until it reads as a symbol), and **transitional** (a palette that shifts
across the runtime to mark an arc) [SECONDARY · StudioBinder, *How to Use Color in Film* — via a
local extraction, read 2026-08-28]. Two of these are operative at 15–30 seconds:

- **Discordant colour is §6.3's "one colour-structural move" with a mechanism attached.** Establish
  a controlled palette, then put exactly one off-palette colour on the thing that matters — the red
  coat. In a promo that thing is the product, the CTA, or the face. It works *only* because the
  balanced scheme established the norm being broken, which is Block's point (§6.3) restated as a
  recipe.
- **Dominant / support / accent.** A multi-colour palette reads as intentional when one hue leads
  and the others are subordinate; equal weighting reads as garish or as mush [SECONDARY ·
  StudioBinder]. **This is a rule you can type into an image prompt and verify on the returned
  frame** (§8 F19), which is rare in this file.

The same source contradicts itself in a way worth preserving rather than resolving: it asserts
predictable physiological reactions (a strong red raising blood pressure, blue calming) and then
insists meaning is entirely film-defined, citing red as dread in *The Sixth Sense* against red as
hope in *Pleasantville* — and its own extraction flags the two claims as unreconciled [SECONDARY ·
StudioBinder]. **The file already contains the missing hierarchy:** convention sets the default
expectation (Storaro), and change over time confirms or overrides it (Block) — §6.3. Calibration
note: this source misattributes *Pleasantville* to David Lynch; treat its attributions loosely.

**6.7 What grading cannot get back — three colourist claims that are actually shooting decisions.**
Grading mechanics belong to `editing-and-audio.md`; these three do not, because they change what you
generate [PRIMARY · Alexis Van Hurkman, *Color Correction Handbook* — via a local extraction, read
2026-08-28].

1. **Latitude is spent at capture.** Van Hurkman's anti-pattern is shooting baked-in high-contrast
   footage and trying to grade it later: the latitude is already gone. **A generated clip is
   baked-in footage** — already contrast-shaped, already saturated, no log, no raw, no headroom in
   the highlight. So the grade can only make small moves, and the look has to be right at
   generation. This is the strongest available argument for §7.3's "all lighting craft moves
   upstream." [The Van Hurkman claim is PRIMARY; the application to generated footage is
   UNVERIFIED.]
2. **Contrast before colour**, always, because changing contrast shifts perceived colour and you
   will otherwise redo the colour. As a frame-gate order: settle ratio and tonal range first, judge
   hue second. Most frame-gate arguments about "the colour is off" are contrast arguments in
   disguise.
3. **Match to a hero shot, not to taste.** A scene reads as one space when every shot is matched to
   one chosen reference in the fixed order **contrast → balance → skin**; grading each shot to look
   good on its own guarantees the set will not match [PRIMARY · Van Hurkman]. **In a batch pipeline
   this is a pre-generation instruction:** choose one hero start frame, then build every other frame
   against it. §7.1's "one LUT, one contrast-and-saturation character across every clip" is the
   downstream half of this rule; this is the upstream half, and `realism-qa.md` §6 prices the
   difference.

One perceptual fact from the same source changes a frame test: **skin is the memory colour the eye
judges most strictly**, ahead of sky and foliage, and natural skin across ethnicities falls along a
narrow line on a vectorscope. Get skin right and the audience forgives a great deal; get it wrong
and no other correctness rescues the frame [PRIMARY · Van Hurkman] (§8 F18, `realism-qa.md` V1).

**6.8 Temperature is a mismatch decision, and the mismatch is sayable.** Brown's working numbers are
daylight ~5600K and tungsten ~3200K, with fluorescent, sodium and mercury as named off-axis casts;
his operative point is that **an unintentional mix reads as "set, not world", while a deliberate one
becomes a third character in the scene** [PRIMARY · Brown, *Motion Picture and Video Lighting*].
Kelvin numbers remain decoration in a prompt (§7.1) — but **the mismatch itself is describable in
ordinary words**, and that is the whole of the effect: "warm lamplight against a cold window",
"sodium street light through a blue dusk". A caption-writer would type those. Nobody captions 3200K.

---

## 7. The translation layer — what survives into an AI pipeline in 2026

**7.0 The mechanism, first, because it explains every row.** Video models are conditioned on
**captions of footage**. A control survives into a prompt if and only if the phrase for it plausibly
appeared in training captions describing what the footage *looks like*. Terms describing a
**measurement made on set** — a 4:1 ratio, T2.8, "40mm at 1.2 m," "key at 40° camera-left, 25° up" —
never appear in captions, because nobody captions footage that way. They are not weak controls.
**They are not controls at all: they are style-flavoured noise.** The vendors nearly say it: numeric
optical specs like "virtual anamorphic lens, 24mm, f/2.8" function as **"stylistic cues" rather than
computational parameters** [SECONDARY · fal.ai, Kling 2.6 Pro guide]. The literature says it for
motion: models *"lack control of camera pose that serves as a cinematic language,"* and precise
control needs pose supplied as a **separate conditioning channel** [PRIMARY · He et al.,
*CameraCtrl*, arXiv:2404.02101]. [The generalisation from those two citations to the caption-space
rule is UNVERIFIED — a synthesis no source states in that form, though every row below is consistent
with it.] The ceiling is visible in Google's own Veo docs, which enumerate the entire prompt surface
as four optional fields — camera positioning (*"aerial view… dolly shot, or worms eye"*),
composition (*"wide shot, close-up, single-shot or two-shot"*), focus and lens effects (*"shallow
focus, deep focus, soft focus, macro lens"*) and ambiance (*"blue tones, night, or warm tones"*)
[PRIMARY · ai.google.dev/gemini-api/docs/veo · checked 2026-08-28]. **That list is the whole
language.**

**The deeper reason the mechanism holds, from outside the AI literature.** Monaco's account of the
photographic sign explains why a caption is a weak control surface and a frame is a strong one. In
language the power comes from the *gap* between signifier and signified — the word "book" is nothing
like a book — whereas in a photographic image the two nearly coincide; he calls it the
**short-circuit sign**, and the consequence is that **film states where language suggests** [PRIMARY
· James Monaco, *How to Read a Film* — via a local extraction, read 2026-08-28]. A prompt is
language and therefore suggests; the model's job is to convert the suggestion into a specific,
unretractable statement. **You cannot prompt an ambiguity — you will get a particular rose** — and
every specificity you did not choose is chosen for you, which is §5.1's auto-composition arriving by
a different road.

Two working consequences follow, and both are cheap. First, for an abstract idea in six seconds,
reach for an **index** — a concrete thing causally linked to the idea (sweat for heat, a clock for
time, breath for cold) — rather than a symbol, because the photographic image is *too present* to
work as metaphor and literary-style metaphor on screen reads "crude, static, and forced" [PRIMARY ·
Monaco, after Peirce and Wollen]. Second, **metonymy is the compression tool short form actually
runs on**: one charged associated detail invoking a whole idea, which Monaco calls "a kind of
cinematic shorthand" that film does *better* than prose. Both are frame-side, both are
caption-native, and neither costs a generation. Against that, his warning: reading an image is
**learned, not innate** — comprehension is not apprehension, and cross-cultural tests show pictorial
depth codes are not universal [PRIMARY · Monaco, citing Hudson] — so a device that needs decoding
will not land in six seconds on a scrolling audience.

**7.1 The master table.** **T** = survives as prompt text · **F** = only by authoring or choosing a
start frame / reference · **E** = fixed in the edit or the grade · **X** = cannot be had.

| Control | | Why | The move |
|---|---|---|---|
| Shot size and camera angle (CU/WS/two-shot; low, high, top-down, Dutch, POV) | **T** | both in Veo's documented list; dense in captions [PRIMARY] | type it; reliability high |
| **One** named camera move (push, dolly, track, orbit, crane, pan, tilt, roll) | **T** | documented by Veo and Kling; strong caption presence | one move per clip, never two — and §3.8 has the per-move ruling, because the twelve are not equally available |
| **Handheld** as a texture | **X** as written | presence is involuntary micro-correction and the model has no body to correct (§3.4) | you get a gimbal. Motion transfer, or post jitter — never the word alone |
| **Dolly zoom** | **X** | two continuous parameters at once, one of them focal length, and no model exposes a focal-length channel (§3.8) | buy the meaning as two frames and a cut, or a scale change between endpoints. `prompt_lint.py` refuses it |
| **Rack focus** | **F** | a lens move with no caption phrase precise enough to steer | two frames with different focus, or a post blur pass (§3.8) |
| A move longer than one clip — the "impossible" continuous move | **E** | ≤8 s and one behaviour per generation | ⚡ three clips whose **motion vectors agree across the joins**, cut mid-movement. Match-on-action is the mechanism and it is the most-missed cut in the corpus at 32.4% (§3.8) |
| Time of day / weather ("golden hour", "overcast", "night") | **T** | implies the *entire* light model at once — the most efficient lighting lever there is | prefer this over describing fixtures |
| Named lighting styles ("Rembrandt", "backlit", "silhouette", "noir", "neon") | **T** | caption-native [SECONDARY · Luma] | yields a look-*alike*, never a measurement |
| The five named **portrait patterns** (butterfly/Paramount, loop, Rembrandt, split, rim) | **T** | the densest lighting phrases in caption space — every headshot listing uses them (§1.4) | type the name; **verify with the nose shadow** (F22). ⛔ butterfly and rim are withheld from UGC — see `photorealism-physics.md` §8 |
| **Frame within a frame** ("through a doorway", "framed by the window") | **T** | the near plane is a *noun*, and nouns survive; a real photograph gets captioned this way | the one composition control you can type rather than author (§5.3). Keep the near plane darker and softer, and upright in 9:16 |
| **Contrast between subjects**, or a pattern with one break in it | **T** | describable as objects and their differences, not as a geometry | "six identical mugs, one turned over" — state both halves (§5.2) |
| One-point perspective; radial balance | **T** | caption-native, and both are *better* in 9:16 than in 16:9 (§5.10) | the vertical-native way to buy depth, since the diagonal does not survive the crop |
| Camera height as a named rung (overhead, eye, hip, knee, ground) | **T** | height words are caption-native; the rung names are not measurements (§5.4) | ⛔ avoid the plain **high angle** in 9:16 — it spends the whole lower third on floor that captions already own |
| Colour temperature and DoF in words ("warm tones", "shallow focus", "macro") | **T** | documented list [PRIMARY] | words only; Kelvin and T-stop numbers are decoration |
| Film-look tokens ("35mm", "film grain", "anamorphic") | **T** weak | "stylistic cues, not parameters" [SECONDARY · fal.ai] | flavour, non-linear; never budget on it |
| **Key/fill ratio** | **F** | no ratio token exists in caption space; the model has no meter and no exposure model | **generate or choose a start frame that already has the ratio, then animate it** |
| Key direction and height; short-side vs broad-side keying | **F** | "camera-left, 30° up" is set-language; short-vs-broad is too fine to survive tokenisation | bake into the frame — the highest-value thing to fix there (§1.4) — and keep the move short so it is not re-lit mid-clip |
| Negative fill / a controlled dark side | **F** | subtraction has no vocabulary; "dark side" invites global underexposure | frame, or a shadow-side qualifier in the grade |
| Exact focal length / perspective | **F**, but the mm TOKEN does real work | numeric specs are cues, not parameters — and a cue is not nothing. ⚡ **Measured 2026-09-17** (`lab-00001-fov`): 24mm / 50mm / 135mm, one scene, one varied axis, separated correctly and monotonically — 135mm filled the frame with the subject and flattened the depth, 24mm put two walls and a corner in. Keep writing the millimetres | choose a frame with the right *camera-to-subject distance* — perspective lives in frame geometry and is broadly preserved (§2.1) — and name the mm anyway |
| ⛔ **Field of view in DEGREES** ("84°", "18°"), the vendor alternative to millimetres | **TESTED AND REJECTED** for the frame stage | [SECONDARY · Higgsfield, *Seedance 2.0 Prompt Writer*, 2026-09-17] prescribes a fixed degree table and says never to use millimetres. Run against the same scene the same day, the degree arm did not merely fail — **it failed backwards**: 18°, predicted the most compressed, returned the WIDEST frame of all six, with a foreground the model invented by reading it as a seated POV. The one cell that held was 47° ≈ 50mm | ⛔ Do not import the degree table into a frame prompt. ⚠️ This does NOT refute the vendor's claim about their own VIDEO model's prompt surface, which is a different measurement nobody has run |
| **A state CHANGE within one clip** (clothing torn, a prop broken, a surface soaked) | **F**, and no amount of restatement raises it | the model has no state register — it renders each moment from the description, so "torn from here on" has nothing holding it and the change reverts between frames [SECONDARY · Kling on drift · `character-and-props.md` §8.4]. ⚡ **Observed 2026-09-18** in the supplied production corpus: one prompt defends a wardrobe change with a state timeline, the words "permanent and irreversible", the state re-asserted at five named timestamps AND a positive lock — and the author's own next revision replaces all four with a second reference asset | ⛔ author the AFTER state as its OWN reference (`state: after`), or split the clip at the change. `prompt_lint.py` blocks the words-only version |
| A specific face, product or logo | **F** | text generates a plausible instance; drift is documented ("a red logo shifts to orange") [SECONDARY] | reference images (Veo ≤3 [PRIMARY]); composite the real asset onto the frame (`realism-qa.md` V13) |
| Exact colour palette | **F** | "warm tones" is a direction, not a palette | frame carries it; the grade enforces it downstream |
| Composition: subject placement, headroom, lookspace, horizon height, figure/ground separation | **F** | all of it is visible in a still, and none of it has a caption phrase precise enough to steer — "centred" is about the only one a model obeys | author the frame against §5; the checklist is §8 F13–F19 |
| Cut geometry: ≥30° or a clear size step between two shots of one subject | **F** | no model knows what the previous clip's camera did; there is no shared camera space between generations | design it into the *pair* of start frames and check them side by side (§4.5, §8 F20) |
| A single off-palette accent on the thing that matters | **F** | "one red object" is a composition, not a caption; palettes drift across generations | put it in the frame, then hold it with one grade (§6.6) |
| Precise camera trajectory | **F** | needs a separate pose channel [PRIMARY · CameraCtrl] | Kling's numeric camera parameters where available [PRIMARY]; else **first-and-last-frame interpolation** [PRIMARY · Veo] |
| The 180° line and eyelines across shots | **E** | each generation is independent; no persistent scene geometry or shared 3-D space between clips | design each start frame facing the right way, verify on the timeline, budget a retake |
| Ratio, contrast and colour consistency clip to clip | **E** | no shared exposure state across generations | **one LUT, one contrast-and-saturation character across every clip** — Deakins' method taken literally [PRIMARY] |
| Timing of a move (start on beat 2, land on beat 5) | **E** | no temporal control surface inside a clip | generate long, trim into the move (`editing-and-audio.md`) |
| Blocking of more than one or two figures | **E** | multi-figure staging degrades; objects "change appearance mid-video" [SECONDARY · fal.ai] | restage as single-subject clips, build the scene in the edit |
| Movement/cutting rhythm | **E** | clip-level generation cannot author a cut | the edit — Murch's top four, 89% of his weighting, are *all* edit-side |
| Motivated-source logic through a big move; a focus pull landing on a chosen word | **X** | the model re-derives lighting per frame and tracks no source object; there is no intra-clip temporal control | keep moves short and the practical **in frame** as an anchor [UNVERIFIED · inference]; otherwise cut to a second clip |
| An off-screen world — a subject entering or leaving frame | **X** | nothing exists outside the frame to enter it; the model invents a body rather than moving one (§5.9) | an entrance is a cut: two clips, joined in the edit |
| Duration beyond model limits (Veo 4/6/8 s [PRIMARY]) | **X** | hard cap | design in ≤8 s beats — for 9:16 a fit, not a constraint |

**Say it plainly, because it is the sentence this file exists for: you cannot direct a key-to-fill
ratio through a prompt. You can only choose a reference image that already has one.** Same for key
direction, short-side keying, negative fill and focal length: everything in §1 and §2 is now a
**still-image problem**, solved in the image model and then animated. **First-and-last-frame
interpolation is the most underrated control here** [PRIMARY · Veo] — it converts "describe a move"
into "specify the two endpoints," the closest thing 2026 offers to operating a dolly.

**7.2 The rules that fall out.** **One subject, one action, one camera behaviour per generation.**
Vendors are explicit that conflicting instructions break the model: "fast and slow motion" makes it
*"average competing signals rather than commit to either"* [SECONDARY · LTX]; an orbit while zooming
gives *"warped geometry due to multiple simultaneous camera transformations"* [SECONDARY · fal.ai];
a 40,000-prompt analysis agrees that *"conflicting camera instructions… are where models fall
apart"* [SECONDARY · vivideo.ai, AI-classified and self-described as imperfect].

⛔ **Do not write a measured spec into a video prompt and then approve the clip because the prompt
said it.** "2:1 key:fill, 5200K, 40mm" costs a full generation and buys style noise. Approval comes
from the pixels (§8), never the brief — the same rule as `realism-qa.md` §6.

⛔ **Do not repair lighting at the clip stage.** Lighting lives in the start frame, so a lighting
fault found after generation is a frame problem: regenerate the frame and re-animate. The production
record in `realism-qa.md` §6 prices it — ~2 credits at the frame gate against 21 in redone clips.

**7.3 The honest summary. You do not direct a cinematographer. You direct a caption-writer, and you
hand it a photograph.** (1) **All lighting craft moves upstream, into the start frame** —
text-to-video is where lighting becomes generic, image-to-video is where it stays specific. (2)
**All continuity craft moves downstream, into the edit**, and Murch's ranking is consoling here: the
two things you cannot control are the two he cared least about. (3) **Lens and movement are the only
areas where text genuinely carries meaning**, and only in the *named* form, never the *measured*
form — so "if the camera moves it's got to be for a reason" becomes doubly true: every requested
move is also a request to hallucinate new geometry, and an unmotivated one costs artefacts as well
as meaning.

---

## 8. Frame tests — checks that emit evidence

Adjectives do not pass a gate; observations do (`realism-qa.md` §6). Each test is answerable from
the pixels and yields a sentence for `09-qa/QA-LOG.md`.

| # | Test | Where you look | Fails when |
|---|---|---|---|
| F1 | **Catchlight** | the iris, at 100% | none, or two of equal strength — two keys, single-source story broken (§1.5) |
| F2 | **Shadow edge** | the transition on cheek or jaw | you cannot tell whether it is hard or soft; a mushy edge means averaged sources, not one light (§1.3) |
| F3 | **Two-plane** | the whole face, squinting | it reads as one flat tone — frontal key, no modelling. Squinting strips detail and leaves the tonal blocks you are counting (§1.4) |
| F4 | **Short-side** | which half of the face is lit | the *near* half is the bright half — broad-side keying flattens and widens (§1.4) |
| F5 | **First fixation** | where your eye lands in the first half-second | it lands on a bright foreground object, window or lamp — a leak (§4.2). Look away and back to re-run it |
| F6 | **Source plausibility** | every light in frame, asking what caused it | a rim with no window, a fill with no bounce surface; the physical model is contradicted (§1.1) |
| F7 | **Perspective / distance** | nose-to-ear relationship, room behind the head | wide-lens-close when the shot should observe, or long-lens-flat when it should intrude (§2.1–2.2) |
| F8 | **Safe box** (9:16) | the eyes, measured as a fraction of frame height | eyes are outside **30–40%** of frame height, or any load-bearing element falls outside `y = 15–65%` / `x = 11–72%` — the *measured* ad safe zone, not the frame (§5.10, `assets/delivery-formats.json`). Four independent constraints converge on that band; a frame outside it collides with the profile row above or the caption block below |
| F9 | **Highlight integrity** | the brightest skin: forehead, cheekbone | texture is gone — clipped or on the shoulder, unrecoverable, faces waxy (§6.1; `realism-qa.md` V1) |
| F10 | **Screen direction** | which way the subject faces, against the previous shot | direction has flipped; the line is broken across a cut nothing in the pipeline enforces (§4.3) |
| F11 | **Move payload** (clip) | last frame against first | the audience learned nothing across the move — it decorates (§3.3) |
| F12 | **Contrast match** (batch) | the batch's frames on one contact sheet | one clip's key or contrast does not belong to the set; fix in the grade before the edit (§6.2) |
| F13 | **Focal point** | the frame desaturated to greyscale | the highest local value contrast is not on the subject — content was assumed to carry focus (§5.2) |
| F14 | **Figure/ground** | the subject's outline against what is directly behind it | a background element merges with, crowns or out-competes the subject, or the tonal step at the edge is under ~8% (§5.3) |
| F15 | **Skeleton** | the frame squinted down to lines and blocks | it is all square-on horizontals and reads static — re-angle rather than add elements (§5.4) |
| F16 | **Edge and headroom** | the four borders, one at a time | something is tangent to or half-cut by an edge, or headroom reads as the subject sliding out of frame (§5.5); in a movement demonstration, the frame leaves no room for the whole body through the move — or, on the clip, a hand or foot crosses an edge (§5.8). Headroom is read by eye: the measured family medians in §5.8 are practitioner data, not this test's threshold |
| F17 | **Lookspace** | the direction of the gaze or the implied motion | the quiet space sits behind the subject rather than ahead of it; in 9:16 check vertically, not laterally (§5.8, §5.10) |
| F18 | **Skin** | faces at 100%, then the same frame in greyscale | skin reads plastic, sunburnt or grey-green — the memory colour the audience audits hardest, and the one no other correctness rescues (§6.7) |
| F19 | **Palette discipline** | count the hue families in the frame | more than one off-palette accent, or the accent is not on the thing that matters (§6.6) |
| F20 | **Cut geometry** (pair) | two start frames of the same subject, side by side | the angle change is under ~30° with a similar size — it will read as a jump whatever the clips do (§4.5) |
| F21 | **Depth payload** | how many planes carry information | everything sits on one plane; the frame is spending a whole generation on what one deep frame could hold (§4.6) |
| F22 | **Named-pattern delivery** | the nose-and-cheek shadow at 100%, against the pattern you asked for (§1.4) | the signature is absent — a "butterfly" that is asymmetric; a "loop" whose shadow has merged into the cheek shadow; a "Rembrandt" with no closed triangle, or one **wider than the eye or longer than the nose**. ⛔ That last criterion is *convention, unsourced* — the source that supplies it hedges it — but a testable convention beats an untestable truth in this table |
| F23 | **Catchlight shape** | the iris at 100%, asking what object made that reflection | the shape contradicts the source you named. A catchlight **is an image of the source**: a window is a rectangle, an overhead panel a bar, a large soft source a large soft-edged patch, a bare bulb a hard point. "Soft window light" returning a tiny round point means the model rendered a hard source. Independent of F2: F2 reads the shadow the source made, F23 reads the source (§1.3) |
| F24 | **Composite match** (any pasted asset) | the pack shot, logo or plate against the frame it now sits in | any of the four axes disagrees — **direction, colour, quality, quantity**. A complete four-item check on every composited element; `photorealism-physics.md` §7 has the optics remedies, this decides whether they are needed (`realism-qa.md` V13) |

F1–F9, F13–F19, F21 and F22–F24 run at the **frame gate**, before a clip is generated — that is
where the leverage is, and F13–F19 are the composition sweep §5 exists to make answerable. F20 runs
across the frame *set*, before any generation. F10–F12 run at the clip and selects gates
(`direction.md` §4). F24 runs whenever something real is pasted onto something generated, which is
usually the pack shot. Write the observation, not the checkmark.

---

## 9. What this file cannot settle

### 9.0 ⛔ Blacklist — claims from this file's own sources that do not survive their trail

These were read, and rejected. They are listed rather than silently dropped because each is
confident, widely repeated, and would otherwise be re-imported by the next person who reads the
same book.

**Composition** [all from SECONDARY · StudioBinder, *Elements of Composition: The Complete Guide*,
2023]

| ⛔ Claim | Why it is out |
|---|---|
| The **golden ratio** as a reason to place anything | Ward reports Fechner's golden-rectangle preference experiments **largely failed to replicate**, and Davies dismisses it outright for picture-making — *approximate* off-centre does the work, and 1.5 or 1.7 would serve as well as 1.618 (§5.6). Use thirds; never defend it with φ |
| The **"Golden Triangle"** demonstrated on *Pulp Fiction* | A grid drawn over a finished frame after the fact. Any frame admits some grid; a rule that cannot fail before the shot is not a rule. **Post-hoc geometry fitting** — the composition equivalent of §D's genre mappings |
| *"Off-center composition is pleasing to the eye because it's typically where the eyes go first"* | Contradicted by measurement on the actual device: gaze **dispersion is significantly lower on phones** and fixations run central [PRIMARY · Szita & Rooney 2021, *i-Perception*]. The claim is a rationalisation of a convention, and it is wrong in the direction that matters for 9:16 |
| The **"parallel / perpendicular / diagonal" camera-angle taxonomy** | An invented three-term scheme that collides with the established vocabulary (angle, height, tilt, Dutch). ⛔ Adopting it would *degrade* prompt vocabulary: none of the three terms is caption-native, so it trades three working tokens for three that return noise (§7.0) |
| The book's **"Simplicity" section**, printed twice near-verbatim | Not wrong, but an editorial-quality signal about the source. Noted for calibration, not for content |

**Lighting** [all from SECONDARY · StudioBinder, *Film Lighting: The Ultimate Guide*, 2023]

| ⛔ Claim | Why it is out |
|---|---|
| *"Every time we double the distance from the source, we lose 75% **more** light"* | Doubling distance leaves 25% — you lose 75% *of* it, i.e. **two stops**. "75% more" is either meaningless or asserts a 175% loss. The same book states the law correctly in its glossary. Canonical form stays `photorealism-physics.md` §6 |
| *"Weaker key light will produce a higher contrast ratio with sharper shadows"* | Two errors in one line. Weakening the key toward a fixed fill moves the ratio **toward 1:1** — *less fill* is what raises it, which the next paragraph of the same book says correctly. And key intensity has no bearing on shadow **sharpness**, which is apparent source size (§1.3) |
| *"Hard light is made of parallel rays… because nothing disrupts the direct beam"* | Hardness is **angular subtense** — apparent source size relative to distance. A bare bulb 30 cm from a face throws wildly non-parallel rays and is hard. ⚡ This is the book's largest omission, not just an error: it never once says *"relative to distance"*, so a reader who absorbs it cannot answer "is this source hard or soft?" for any source not on its list. Holben's rule in §1.3 is the correction |
| Contrast-ratio numbers (2:1, 8:1) as specs | Uncredited, and the book **never says what is being ratioed** — illuminance on the two sides, or luminance of the two halves of the face? They differ, because the key side receives key *plus* fill. A reader cannot reproduce a 2:1 from it. §1.6/§1.7's treatment — teaching notation, never an approval criterion — absorbs this source at that tier, not above it |
| Genre→lighting mappings (*"thrillers and horror use hard light"*, *"comedies use soft"*) | No frequency data, no sample, no citation — then the book supplies *Midsommar* as a counterexample and files it under *"there are always exceptions"*, which converts an unsupported convention into an unfalsifiable one. **Same failure the sibling colour ebook already committed** (§6.6) |
| *"Caravaggio, Leonardo da Vinci, and Rembrandt… during the Italian Renaissance"* · *"The Cabinet of Dr. Cagliari"* | Rembrandt was Dutch, active 1625–69 — Dutch Golden Age, a different country a century later. Caligari is misspelled in the sentence citing it as load-bearing. See §9.1 |
| The Rembrandt triangle placed *"on the fill side of the face"* | The triangle is on the **shadow** side, where the nose shadow meets the cheek shadow — away from the key. The book's own setup puts a reflector there, so its phrasing sends a reader to the wrong cheek. F22 uses the corrected statement |
| *"White walls are always the best for bouncing light"* | "Always" contradicts the same book's celebration of motivated colour; a warm bounce off wood is a standard deliberate tool. Convention stated as law |
| *"A well-lit scene shot with a cheap camera will almost always beat out a poorly-lit scene shot with a great camera"* · *"You don't need a Hollywood budget to get a Hollywood look"* | No metric for "beat", no test, and "almost always" cannot be wrong — printed a few pages after the book's own *Sicario* diagram showing dozens of units for one house raid |
| Body-vs-glossary definitions of **short/broad** | The body gives a which-half-is-lit definition (executable); the glossary gives a camera-position definition, with "smart side / dumb side" slang and no reconciliation. **Use the body form** (§1.4) |
| Named-pattern **provenance** — "Paramount lighting, named for how they lit their most glamorous actresses"; Dietrich; *"traditionally the triangle should be no wider than the eye"* | Keep the **terms** — they are caption-dense and that is the whole reason §1.4 carries them. ⛔ Do not repeat the **histories**: no dates, no sources, whose tradition unstated. F22's triangle criterion ships flagged as *convention, unsourced* for exactly this reason |
| Colour-temperature values | Daylight is given as 5500–6000K, 5600K, and *"typically around 5,900K"* on three different pages, unacknowledged. Brown's numbers in §6.8 stay canonical |

### 9.1 Source calibration — a standing note on this publisher

**Three factual errors across three StudioBinder ebooks now read into this skill**: *Pleasantville*
attributed to David Lynch (it is Gary Ross) in the colour ebook; Rembrandt placed in the Italian
Renaissance and *Caligari* misspelled in the lighting ebook. All three books carry **no citations
anywhere** — every practitioner claim (Deakins, van Hoytema, Libatique, Seale) arrives as a caption
on a film still, none quoted, none linked, none checkable — and all three are lead-magnet marketing
with inline cross-sells, discount codes and, in the lighting ebook, a chapter-numbering skip
(Ch. 7 → Ch. 9) and a table of contents that does not match its own headings.

⚡ **The operative rule, and it belongs in `research-quality.md` too: StudioBinder's *vocabulary* is
citable at [SECONDARY]; its *attributions, histories and numbers* are not citable at all.** The
vocabulary is genuinely valuable here — it is a distillation of what the internet calls things,
which is exactly what §7.0 says a prompt is scored against. Take the words. Verify every claim
attached to them somewhere else, or mark it unsourced and testable, as F22 does.

**Live disputes, left open on purpose** — do not resolve them in a brief: what "natural light" means
(§1.2) · long lens versus proximity for faces (§2.2) · whether the zoom is cheap (§3.2) · shallow
focus as a default (§2.3) · the 180° rule's real status (§4.3) · whether ratio numbers mean anything
(§1.6) · whether portraiture has rules at all (§4.2, and Mullen: *"I wouldn't tell a painter what
colors to choose"*).

- **Ratio numbers and their emotional meanings** (§1.6) are convention with **no named authority
  behind them** — shorthand between humans, never a spec. **Skin-tone placement** (§6.1) likewise;
  no named-source figure was found.
- **The caption-space mechanism** (§7.0) is a synthesis. Its two citations are real and load-bearing
  (fal.ai on numeric specs as "stylistic cues" [SECONDARY]; CameraCtrl on the separate pose channel
  [PRIMARY]), but no source states the generalisation. It predicts the table well but remains a
  model, and a vendor could falsify it next quarter by shipping a real parameter surface — Kling's
  numeric camera control is already the exception.
- **Every vertical-format application** of Alton, Block and the anamorphic material (§2.3, §4.2, F8)
  extends horizontal-cinema sources, as do the `[UNVERIFIED]` formulations: shallow focus as
  pre-emptive editing, the push-goes-cheap and reveal-versus-decorate tests, the movement vocabulary
  (§3.4), broad-side keying as the commonest amateur fault, and the eye-attention ordering beyond
  Alton's brightness point.
- **Murch's Story weighting** is 21% in one summary and 23% in the circulated figure, though the
  ordering and the other five values agree; the book was not reachable, and **Block and Mascelli
  were never read directly** — both borrow-only, the archive API failed, so everything from Block is
  [SECONDARY].
- **Storaro's *Film Quarterly* essay returned HTTP 403**, so his material comes via No Film School
  and Film Comment, and the CineD piece on van Hoytema's lens reasoning returned no article body.
  **Runway's Gen-4.5 surface is unconfirmed** — vertical ratios, keyframe parameters and numeric
  camera values could not be verified from Runway's own docs. Treat any Runway row as unverified
  until tested.
- **Alton quotes circulating online** ("I used light for mood") come from interviews and Todd
  McCarthy's introduction, **not** Alton's chapters. Every Alton quote marked [PRIMARY] here is from
  the book's body text.
- **The book layer merged in on 2026-08-28 came through local extractions that mostly paraphrase**,
  so the wording is rarely the author's. Six tier-1 texts are cited [PRIMARY] for their own claims —
  Brown (*Cinematography: Theory and Practice*; *Motion Picture and Video Lighting*), Malkiewicz &
  Mullen, Ward, Katz, Van Hurkman, Monaco — and the three thin sources are cited [SECONDARY]
  throughout: both StudioBinder ebooks are lead-magnet marketing with no citations, and Davies is
  self-published, un-dated and explicitly opinion-led. **The StudioBinder colour ebook contains at
  least one outright error** (*Pleasantville* attributed to David Lynch; it is Gary Ross), so treat
  its attributions as loose. Davies flags his own golden-ratio position as contested, and Ward's
  extraction rates his design doctrines as convention rather than finding.
- **New live disputes, also left open:** whether a symmetric subject should be centred (Ward against
  Davies, §5.5) · the status of the golden section, and whether thirds survives its collapse (§5.6)
  · ratio numbers as textbook notation against practitioner refusal to state one — the first bullet
  above was written before the book layer, and §1.7 now supplies the named authority it says does
  not exist, without making §1.6's refusal wrong · coverage versus deep staging, which Katz argues
  against himself (§4.4 against §4.6) · continuity as procedure (Katz) against continuity as one
  historically contingent code — "there is nothing preordained about film syntax" (Monaco) · the cut
  against the held frame as the truer approximation of perception (Monaco and Godard against Bazin,
  §3.7) · predictable colour psychology against wholly film-defined colour meaning (§6.6, unresolved
  by its own source).
- **Everything in §5.10 extends horizontal-cinema sources to a vertical frame**, as do the
  closed-frame claim in §5.9, the caption-average auto-composition claim in §5.1, the keyframe
  reading of Ward's pivot point (§3.6), and the application of Van Hurkman's latitude argument to
  generated footage (§6.7). None of the ten books has a word to say about generative video; every §7
  application of them is this file's extrapolation.
- **The books are also dated in ways that matter.** Ward (2003) writes from inside the 4:3-to-16:9
  conversion, so his format chapters are period-specific even where the perceptual grammar is not;
  Brown (2002, 2008) and Malkiewicz & Mullen (2005) predate the LED and digital-cinema shift, so
  their instrument and stock chapters are partly historical; Van Hurkman (2013) predates HDR and
  ACES; Katz (1991) predates digital previs. **The perceptual and geometric layers age well; the
  equipment layers do not**, which is the reason §1.9 keeps the instrument *taxonomy* and discards
  the catalogue.

**Cross-refs:** `craft-cheatsheet.md` (the fast lookup this sits under) · `ai-generation.md`
(start-frame and clip-prompt mechanics) · `realism-qa.md` (the tell list and QA card §8 extends) ·
`direction.md` (blocking cards, selects) · `production-design.md` (what is in the frame to light) ·
`editing-and-audio.md` (what §7 pushes downstream) · `delivery-format.md` (9:16 safe areas) ·
`script-craft.md` (where §6.3's colour move lands).
