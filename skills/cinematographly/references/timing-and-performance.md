# Timing and performance — the temporal layer

**When to read this:** a clip is technically clean and still reads dead; a face looks right in
stills and wrong in motion; a move arrives without landing; you are writing the aliveness half of a
prompt, or deciding whether a defect is a generation problem or an edit problem. `motion-design.md`
is about *obtaining* a move; this is about the **shape of a move in time** — its acceleration, its
settle, and the small facial events that make a photoreal frame read as inhabited rather than
embalmed. `direction.md` §1 says what the performance *is*; this says how long it takes.

Source tiers follow `research-quality.md`. All web sources checked **2026-08-29**. Like
`editing-storytelling.md`, most of this is **durable** — eyelid kinematics and minimum-jerk motor
control do not decay with a model release. What decays is §6, the control sort, which is a statement
about a specific roster on a specific date.

**⛔ The one thing to carry out of this file if you read nothing else.** Constant-velocity motion
does not read as *boring*; it reads as **wrong**, because the visual system's reference for normal
motion is borrowed from the motor system, and no biological effector moves at constant velocity. And
the penalty scales with photorealism: the more real your frame looks, the harsher the motion is
judged. Your best-looking frames are your most temporally fragile.

---

## 1. Easing is spacing — and why linear reads wrong

### 1.1 The principle

Slow in / slow out is one of the twelve principles codified in Thomas & Johnston, *The Illusion of
Life* (1981) — the standard restatement being Lasseter's: **"the spacing of the in-between frames to
achieve subtlety of timing and movement."** [SECONDARY · Lasseter, J. (1987), *Principles of
Traditional Animation Applied to 3D Computer Animation*, ACM SIGGRAPH Computer Graphics 21(4):35–44
— SIGGRAPH education summary retrieved, not the full paper · checked 2026-08-29]

Note the definition: easing is **spacing**, not velocity — *how far the subject travels between
consecutive frames*. That is exactly the quantity `scripts/clip_qa.py` samples with its motion-energy
series, which is why that tool can talk about easing at all.

Two craft claims worth carrying, both from the motion-graphics literature:
[PRIMARY · Crook & Beare, *Motion Graphics: Principles and Practices from the Ground Up* — via the
local extraction, read 2026-08-29]

- Easing is the most-used of the twelve; it **replaces constant velocity for almost all work**.
- **"Timing is the dominant craft dimension"** — the gap between professional and amateur motion
  work is mostly timing. The named anti-pattern is linear motion as a default: *machine-driven* is
  the word used for how it reads.

### 1.2 Why — the mechanism, which most animation writing asserts and never explains

**Production side: real limbs cannot move at constant velocity.** Human point-to-point arm movement
minimises jerk, which mathematically produces a **bell-shaped velocity profile** — accelerate, peak,
decelerate to zero. The model predicted straight-line paths, reduced velocity through high-curvature
segments, and matched measured human movement. [PRIMARY · Flash, T. & Hogan, N. (1985), *The
coordination of arm movements*, Journal of Neuroscience 5(7):1688–1703 · checked 2026-08-29]

**Perception side: the visual system judges motion against motor kinematics.** Observers judge as
*uniform* the motions that obey the two-thirds power law of natural drawing movement **even when
actual speed varies by more than 200%** — and genuinely constant-velocity motion does not look
uniform to them. [PRIMARY · Viviani, P. & Stucchi, N. (1992), *Biological movements look uniform*,
JEP: Human Perception and Performance 18(3):603–623 · checked 2026-08-29]

**The corollary that governs this whole skill.** Response bias toward judging motion "biological"
**decreases as a character's appearance becomes more anthropomorphic** — realistic characters' motion
is perceived as less natural than the same motion on abstract point-light displays. [PRIMARY ·
Chaminade, T., Hodgins, J. & Kawato, M. (2007), *Anthropomorphism influences perception of
computer-animated characters' actions*, SCAN 2(3):206–216 · checked 2026-08-29]

Photorealism raises the bar on motion. This is the temporal twin of `photorealism-physics.md`'s
finding that the closer a frame gets, the more a small physical error costs.

### 1.3 What is published about camera-move ramps: nothing

Searched specifically for ease durations for camera moves, in frames or seconds. **None exists** —
not in the cinematography texts this skill already mines, not in motion-control literature, not in
manufacturer documentation. Katz treats moves as a meaning taxonomy with the doctrine that movement
must be motivated, and never quantifies a ramp. [PRIMARY · Katz, *Film Directing Shot by Shot* — via
the local extraction, read 2026-08-29] The closest prescription is qualitative: the virtual camera
"has weight and is constantly re-composing the frame; if it moves too lightly or flips around it
pulls the audience out of the film." [PRIMARY · Kelly & Baena, *Animation Tips & Tricks, Vol. 2* —
via the local extraction, read 2026-08-29]

**The one published camera-motion number is a speed ceiling, not a ramp:** pan no faster than a full
image width every **7 seconds** at 24 fps / 180° shutter, or the pan judders. Explicitly "not an
all-or-nothing limit" and "just a good starting point"; smaller shutter angles read crisper but
choppier, larger ones smoother but blurrier. [SECONDARY · RED Digital Cinema, "Camera Panning
Speed," red-101 · checked 2026-08-29] Use it as the outer bound on how fast a *generated* move may
travel before it reads as broken — it is a QA check, not a target.

⛔ **Two contamination risks, named so they stay out.**

1. **UI-motion easing bands are not camera timings.** The nearest published ease durations
   (ease-out 200–400 ms, ease-in 300–600 ms, ease-in-out 300–500 ms; the duration ladder <200 ms
   imperceptible / 200–500 ms feedback / 500 ms–1 s intentional / >1 s cinematic) describe buttons
   and modals, not a camera with mass. [PRIMARY · Shaw, *Design for Motion* — via the local
   extraction, read 2026-08-29] They are used in §7 only as the starting window for a **post**
   speed-ramp, where the object being eased genuinely is a 2D transform.
2. **"A quadratic Bézier feels 30% more organic than a linear path" is not a fact.** [UNVERIFIED] It
   appears in the same local extraction with no source, and there is no plausible measurement behind
   a percentage of "organic". Do not propagate it. That file also self-labels claims "Verified"
   while citing nothing; everything from it is convention-level here.

---

## 2. The numbers that exist, in frames at 24 fps

### 2.1 The table

Only a handful of character beats have a traceable number. These do.

| Beat | Measured | At 24 fps | Source |
|---|---|---|---|
| **Blink, total** | 150–400 ms; fully closed ≈50 ms | **4–10 f**; closed hold ≈1 f | Nyström 2024 |
| **Blink phases** | closing ≈63 ms, opening ≈138 ms — **opening ≈2× closing** | close ≈1.5 f, open ≈3 f | Nyström 2024 |
| **Blink, animator practice** | regular 2 close / 1 hold / 3 open; long 3/2/4; eye-bat 1/2 | **6 f · 9 f · 3 f** | Meroz (Bloop) |
| **Blink rate** | rest **17/min**, conversation **26/min**, reading 4.5/min (rest range 4–43) | one per **3.5 s** rest, **2.3 s** talking | Bentivoglio 1997 |
| **Fixation (gaze hold)** | 256–260 ms, saccade amplitude 4.3–4.5° | **≈6 f** → 3–4 gaze changes/second | Rayner 2009 |
| **Eye dart, animator practice** | start pose, one transitional frame, end pose | **3–4 f** | Meroz (Bloop) |
| **Smile onset (AU12)** | mean 15.7 f @30 fps ≈ **0.52 s**, SD 8.4; spontaneous range 0.67–4.0 s | **≈12–13 f** (plausible 6–20) | Schmidt & Cohn 2001 |
| **Mouth transition to smile** | 167 ms | **4 f** | Iwasaki & Noguchi 2016 |
| **Eye-region change, detectable** | 50 ms in isolation | **1.2 f** | Iwasaki & Noguchi 2016 |
| **Micro-expression, upper bound** | total <500 ms **or** onset <260 ms | **12 f** / **6 f** onset | Yan 2013 |
| **Minimum hold** | "6 frames is considered the shortest amount of screen time for a hold" | **6 f** | Lauria, AWN (single source) |

[PRIMARY · Nyström, M. et al. (2024), *What is a blink?*, Behavior Research Methods
56(4):3280–3299] · [SECONDARY · Morr Meroz, Bloop Animation, eye-movement tutorial] · [PRIMARY ·
Bentivoglio, A.R. et al. (1997), *Analysis of blink rate patterns in normal subjects*, Movement
Disorders 12(6):1028–1034, n = 150] · [PRIMARY · Rayner, K. et al. (2009), *Eye movements and visual
encoding during scene perception*, Psychological Science 20(1):6–10] · [PRIMARY · Schmidt, K.L. &
Cohn, J.F. (2001), *Dynamics of facial expression*, IEEE ICME 2001:728–731] · [PRIMARY · Iwasaki, M.
& Noguchi, Y. (2016), *Hiding true emotions*, Scientific Reports 6:22049] · [PRIMARY · Yan, W.-J. et
al. (2013), *How Fast are the Leaked Facial Expressions*, Journal of Nonverbal Behavior
37(4):217–230] · [SECONDARY · Lauria, AWN Toon Institute "Timing," 1999] · all checked 2026-08-29.

**The blink convergence is the finding.** Independent animator practice (5–9 frames, opening slower
than closing) reproduces measured eyelid kinematics almost exactly. Nothing else in this file has
two independent traditions agreeing to the frame, which is why the blink checks in §8 are the ones
worth enforcing mechanically.

**The consequence for a 5-second clip.** At least **one blink**, usually **two** for a talking
character; and on the order of **15 small gaze shifts**, not two. A clip with a locked eyeline for
five seconds is not neutral — it is below the floor of a living face.

### 2.2 Deliberate vs spontaneous — the most transferable fact about faces here

Direction of effect is well established even where the numeric means are paywalled:

| Cue | Reads as felt | Reads as performed |
|---|---|---|
| Onset speed | slower | faster |
| Amplitude | moderate | larger |
| Apex | **sustained** | brief |
| Offset | slower | faster |
| Brow-raise duration | longer | shorter |
| Asymmetry | mild, present | (does not reliably differ — see §3.4) |

[PRIMARY · Schmidt, K.L., Ambadar, Z., Cohn, J.F. & Reed, L.I. (2006), *Movement Differences between
Deliberate and Spontaneous Facial Expressions*, Journal of Nonverbal Behavior 30(1):37–52 · abstract
checked, means paywalled] · [PRIMARY · Schmidt, K.L., Bhattacharya, S. & Denlinger, R. (2009),
*Comparison of Deliberate and Spontaneous Facial Movement*, Journal of Nonverbal Behavior 33:35–45 ·
abstract checked, means paywalled]

**Working rule: fast + big + short = performed. Slower onset + held apex = felt.** This is the one
line to keep in your head when judging a generated close-up, and it is directly actionable — a
generated smile that snaps on in under 6 frames reads posed regardless of how good the skin is.

### 2.3 Where no number exists — say so instead of inventing one

| Beat | Status |
|---|---|
| **Head turn** | No traceable published frame count. "8–12 frames" circulates online with no primary source. [UNVERIFIED] |
| **Reach / gesture** | No published frame count found. [UNVERIFIED] |
| **Anticipation** | Universally prescribed, never quantified. Treated as a *ratio* — antic-vs-action "speed/size contrast carries emotion" [PRIMARY · Kelly & Baena — via the local extraction] — not a count |
| **Settle / overshoot** | No character-animation figure found. The only offsets available are UI (secondary +100 ms, tertiary +200 ms) and transfer badly |
| **Camera-move ramp** | Nothing published at all (§1.3) |

⛔ **Conflict left standing.** The Kelly & Baena extraction prescribes "the average ~one blink per
five seconds" — 12/min — against Bentivoglio's measured 17/min at rest and 26/min in conversation.
**Prefer the measured figures**, but the practitioner rule may be a deliberate animation convention
(fewer, more legible blinks) rather than an error, and it is recorded here rather than silently
overwritten.

---

## 3. Micro-expressions — three claims, only two of them survive

The word carries three separable claims. The skill uses two and refuses the third.

### 3.1 FACS as vocabulary — true, and narrower than people think

The Facial Action Coding System (Ekman & Friesen 1978, rev. 2002) decomposes facial movement into
anatomically defined Action Units: **9 upper-face and 18 lower-face AUs**, plus head- and
eye-position codes. Two things to get right: [PRIMARY · Cohn, J.F. (2007), *Observer-Based
Measurement of Facial Expression with FACS* · checked 2026-08-29]

1. **It is purely descriptive.** "FACS itself is descriptive and includes no emotion-specified
   descriptors"; inferences about emotional meaning are *extrinsic* to it. FACS tells you what moved.
2. **Reliable for presence, weak for timing.** At a half-second tolerance all but two AUs reached
   good-to-excellent reliability — but phase agreement runs only **≈74% on onset and 67% on offset**,
   and Cohn's own conclusion is that more study is needed.

**Use:** FACS is the best available *prompt vocabulary* — "cheeks raise, crow's feet appear, lower
lids tighten" is precise, anatomically real, and describes something a model can render. It is not a
source of frame-accurate timing, and its own literature says so.

### 3.2 The famous duration figure — know where it comes from

"1/25 to 1/5 of a second" traces to **Ekman's trade writing (2009 revision of *Telling Lies*)**, not
to a measurement. [PRIMARY · Oh, Y.-H. et al. (2018), *A Survey of Automatic Facial Micro-Expression
Analysis*, Frontiers in Psychology 9:1128 · checked 2026-08-29] A second peer-reviewed review states
a *different* range (1/25 to 1/2 s) with no citation at all. [PRIMARY · Li, X. et al. (2019),
*Automatic Micro-Expression Analysis: Open Challenges*, Frontiers in Psychology 10:1833]

**The one actual measurement:** of >1,000 elicited expressions under neutralisation instructions, 109
leaked fast expressions analysed → **total duration <500 ms, or onset <260 ms**. [PRIMARY · Yan et
al. 2013] At 24 fps: **12 frames total, 6 frames onset.** Quote this one. The field does not agree
with itself — one database used 2/3 s, and a 2024 CG paper labelled 2–4-second expressions "micro",
off by an order of magnitude.

### 3.3 ⛔ The deception claim — never write it, never imply it

This is where the popular version is simply wrong, and this skill will not repeat it.

- **Far too rare.** Only **2% of ~700** high-stakes expressions were micro-expressions [PRIMARY ·
  Porter & ten Brinke 2008, *Psychological Science* 19(5):508–514, via Burgoon 2018]; in high-stakes
  pleadings, **6 instances among deceivers and 8 among genuine pleaders** — slightly *more* in the
  truth-tellers [PRIMARY · ten Brinke & Porter 2012, via Burgoon 2018].
- **Training does not work.** n = 90 randomised: METT-trained **46.3%**, bogus-training control
  47.3%, no training 44.0% — overall **45.9%, below chance**, no significant differences. [PRIMARY ·
  Jordan, S. et al. (2019), *A test of the micro-expressions training tool*, Journal of Investigative
  Psychology and Offender Profiling · checked 2026-08-29]
- **Field deployment failed.** TSA behavioural detection: arrests from **0.6% of 61,000** referrals;
  automated classification below 56%. [PRIMARY · Burgoon, J.K. (2018), *Microexpressions Are Not the
  Best Way to Catch a Liar*, Frontiers in Psychology 9:1672 · checked 2026-08-29]

**Rule: never write or imply that a facial micro-movement indicates lying** — not in a script, not
in a performance note, not in a claim about a testimonial, and not in copy about a product. It is
false, and in an ad context it is also a claim about a person (`compliance.md`).

What survives: micro-expressions as **aliveness texture** — small, fast, asymmetric facial events
that make a face read as inhabited. That claim is untouched by the critique above, because it is
about how a face *looks*, not about what it *reveals*.

### 3.4 What actually makes a generated face read alive

**The Duchenne marker — use it, for the right reason.** The traditional claim (AU6 orbicularis oculi
is involuntary, so eye-crinkle = genuine) does not hold: **71.1%** of participants produced
deliberate Duchenne smiles on instruction, and ~83% of *posed* smiles showed the marker against ~70%
of spontaneous ones. The authors conclude it "is not a reliable basis for inferring whether a smile
is spontaneous". [PRIMARY · Krumhuber, E.G. & Manstead, A.S.R. (2009), *Can Duchenne smiles be
feigned?*, Emotion 9(6):807–820 · checked 2026-08-29]

The same paper hands over what does work:

- Predictive value of the D marker was **limited compared with asymmetry, apex duration, and
  nonpositive facial actions**.
- **Longer apex durations correlated with higher genuineness ratings.**
- The spontaneous/posed difference **emerged for video and did not emerge for static displays** —
  "dynamic information contains important cues concerning the spontaneity of the expression."

**So authenticity in a face lives in time, not in a pose.** Ask for the eye-crinkle because viewers
*read* it as warm; but the lever that moves the reading is dynamic — slower onset, held apex, mild
asymmetry. Note the useful tension: asymmetry predicts what viewers *judge* genuine even though it
does not reliably distinguish genuinely-felt smiles. For a generated ad the judgement is the whole
point, so mild asymmetry is worth requesting.

**⛔ "The eyes lead the mouth" is [UNVERIFIED] as usually stated** — and the one directly relevant
measurement runs the other way. A mouth change landing ~50 ms *after* an eye-region change
**inhibits conscious detection of the eye change** (backward masking); the reverse order, mouth up
to 200 ms first, caused no disruption. [PRIMARY · Iwasaki & Noguchi 2016] **Practical inversion:** if
the eyes carry the beat, do not let a mouth change land 1–2 frames behind them — separate them, or
lead with the mouth.

---

## 4. The uncanny valley is a motion problem

**The strongest single result for this skill.** fMRI repetition suppression across three agents — a
human (biological appearance + biological motion), a mechanical robot (mechanical + mechanical), and
an android (**biological appearance + mechanical motion**). Human and robot produced similar
suppression; the **android produced stronger effects**, notably in bilateral anterior intraparietal
sulcus. The interpretation is prediction error: we have learned that human appearance comes with
biological motion, and the mismatch is what the brain flags. [PRIMARY · Saygin, A.P., Chaminade, T.,
Ishiguro, H., Driver, J. & Frith, C. (2012), *The thing that should not be*, SCAN 7(4):413–422 ·
checked 2026-08-29]

Matched pairs are fine. A stylised character moving mechanically is fine; a real person moving
biologically is fine. **The failure mode is photoreal appearance carrying non-biological timing** —
which is exactly what a clip that ramps to a peak at frame 120 and stops dead is.

**Mori said it in 1970 and gave a timing observation.** Movement "changes the shape of the uncanny
valley graph by amplifying the peaks and valleys" — and an Osaka robot whose designers **halved the
speed of its smile**: "instead of looking happy, its expression turns creepy." [PRIMARY · Mori, M.
(1970), *The Uncanny Valley*, Energy 7(4):33–35, trans. MacDorman & Kageki · checked 2026-08-29]
That is primary evidence that **expression speed alone flips affect**, holding the expression
constant.

**How much motion.** Facial motion scaled 60%–140% of recorded magnitude (±40% clearly perceptible):
damped characters were rated significantly **less extroverted** but **more respectful and calmer**;
exaggerated motion read **"fidgety and anxious."** [PRIMARY · Hyde, J., Carter, E.J., Kiesler, S. &
Hodgins, J.K. (2016), *Evaluating animated characters: Facial motion magnitude influences personality
perceptions*, ACM TAP 13(2):8 · checked 2026-08-29] Useful nuance for briefs: an under-moving
generated face does not necessarily read *dead* — it reads **low-energy and introverted**. For a calm
authority register that may be free; for warmth, energy or charisma it is fatal.

**Driven faces smooth away exactly the range that matters.** In performance-driven realistic virtual
humans, **~40% of participants perceived no emotion whatsoever**; fear was recognised under 5% of the
time, happiness and disgust ~50%, anger 41%. The authors attribute the gap to **smoothing effects**
and conclude artist-built animation reads better than driven animation. [PRIMARY · Montanha, R.H. et
al. (2024), *Micro and macro facial expressions by driven animations in realistic Virtual Humans*,
arXiv:2408.16110 · checked 2026-08-29] **Generative video shares this failure mode** — it is the same
smoothing, from a different pipeline.

**The practitioner diagnostic, and how well it matches the papers.** Symptoms that drop a realistic
character into the valley: *no eye jitter; glassy or wall-eyed eyes; eyes that move only with the
head; off lip-sync; slack or mirror-perfect faces; no blinks; uncoordinated face and body.*
Remedies: *micro-expressions, nostril flares, brow and cheek raises, sticky lips, swallows and neck
tightens, broken-up head motion, blink-linked cheek raises, saccades, leading head rotation with eye
tics.* Explicit anti-pattern: **chasing maximal realism** — perfect symmetry, "true" skin, a static
head — pushes the character *deeper* into the valley. [PRIMARY · Kelly & Baena (Sintay, "Animation
and the Uncanny Valley," pp. 38–39) — via the local extraction, read 2026-08-29]

That list is not folklore: "eyes that move only with the head" is Saygin's appearance/motion
mismatch, "no eye jitter" is Rayner's missing 3–4 gaze shifts per second, and "mirror-perfect faces"
is Krumhuber's asymmetry cue. Three traditions, one diagnosis.

**And the framing sentence for the whole file:** treat generated footage the way an animator treats
motion capture — **"a foundation that needs an editor's judgement (re-time, re-cut, exaggerate the
beats) to feel alive, not a finished performance."** Untouched mocap reads dead, stiff, creepy; the
work is exaggerating poses, weight and **timing** on top of the captured base. [PRIMARY · Kelly &
Baena (F11, "Motion Capture," pp. 41–43) — via the local extraction, read 2026-08-29]

---

## 5. What our own clips actually do — measured, not assumed

Three clips, kling3_0, 5 s, 9:16, measured 2026-08-29 with `scripts/clip_qa.py` at 12 samples/s
(a close-out note of 2026-08-29 on first-and-last-frame against prompted motion [studio history]):

| Clip | Peak at | Final-1 s mean, % of peak | Clip mean, % of peak | Verdict |
|---|---|---|---|---|
| A · prompt-only | 4.67 s | **75%** | 46% | ends accelerating |
| B · FLF, pose-only pair | 4.00 s | **53%** | 35% | ends accelerating (+1.83 s dead zone) |
| C · FLF, cropped pair | 4.42 s | **83%** | 66% | ends accelerating |

**Every clip peaked in its final second. Every clip ended mid-motion. None eased out.**

In animation vocabulary: **the model blocks the anticipation and the action, and never the settle.**
It also distributes spacing badly — near-zero spacing at the head, maximum at the tail. Since easing
*is* spacing (§1.1), the model owns your curve and has chosen a one-sided one.

Three consequences, and the third is the one that changes planning:

1. **The ~0.4 s static open is a flat hold, not a slow-in.** Frame one is the supplied start image
   and the model takes about 10 frames to leave it. That is a dead hold, not an accelerating ramp —
   it is not free anticipation unless you deliberately author it as one (§6B).
2. **A shot that must LAND has no landing.** Final beats, buttons, the last frame before the CTA —
   these are the shots where the missing settle actually costs something (§7).
3. **⛔ Longer clips do not buy more peak.** If the peak always lands in the final second, a 10 s
   generation gives you a longer dead front, not a longer action. **Generate shorter and cut more.**
   ⛔ The reason is the dead front, not the credit line — cost is no longer a decision input
   (`ai-generation.md` → the quality floor). The shorter clip is better *and* cheaper; only the first
   half is an argument.

---

## 6. The control sort — what you can actually reach

Dated **2026-08-29**, current roster. This is the half of this file that decays.

### A · Specifiable in the prompt (language only — no numeric parameter is honoured)

- **Which camera move.** Pan, tilt, zoom, dolly, orbit, crane and combinations; preset "master shot"
  moves exist. [SECONDARY · Kling AI, "Guide to AI Camera Control" · checked 2026-08-29]
- **A coarse speed register.** The vendor guide maps phrases to bands — "quick snap" 1–2 s,
  "moderate pace" 3–5 s, "slow and deliberate" 5–8 s — and advises writing exact timings
  ("a 5-second dolly zoom"). ⛔ **Treat this as a hint, not a contract**: there is no numeric
  parameter and no evidence the phrasing is enforced. [SECONDARY · same guide · UNVERIFIED as
  behaviour]
- **Presence or absence of named behaviours** — blink, glance away, small smile, breath, swallow,
  weight shift, head tilt. Request them as *content*, not as timings. This is the aliveness block
  (§9).
- **Which layer the performance lives in.** Body language carries ~90% of the acting in a medium
  shot or wider; the eyes carry ~90% of the *facial* performance; lip-sync is last. **Prompt the
  body first.** [PRIMARY · Kelly & Baena (F2, pp. 28–29) — via the local extraction]
- **One idea per clip.** Most actions need three stages — anticipation, action, aftermath — and a
  beat should become a small series of shots, not one crowded one. [PRIMARY · Glebas, *Directing the
  Story* — via the local extraction] Given the measured back-loading, asking a 5 s clip for
  antic + action + settle guarantees all three compress into the last second.
- **Emotional register / motion magnitude**, in words. ±40% is perceptible and shifts perceived
  extroversion and calm (§4).
- **Expression type in FACS-derived language** (§3.1).

**Explicitly NOT specifiable:** the easing curve · frame counts · onset/apex/offset durations · where
the energy peak falls · the motion-energy distribution · blink count or blink placement.

### B · Obtainable through the frame pair or the duration

| Lever | What it buys | Evidence |
|---|---|---|
| **Give the frame pair a *travel* difference, not a pose difference** | A pose-only pair produced 1.83 s of nothing. A pair differing in position, scale or framing gives the model a distance it must cover across the whole runtime — the only structural pressure available against back-loading | Measured (B vs C above); **[UNVERIFIED] as a *fix* for back-loading** — C still ended accelerating |
| **Generate shorter, not longer** | The peak lands in the final second regardless, so shorter runtime = smaller dead front = higher usable fraction | Measured |
| **One beat per clip; let the cut carry the transition** | Follows from Glebas plus the observed compression | Primary + measured |
| **Choose a start image that is holdable** | Frame one is held ~10 frames. Supply an **anticipation pose or a settled pose** — never a mid-action pose, which reads as freeze-then-jerk | Measured |
| **The end frame fixes WHERE motion stops** | Placement, not curve. It does not buy a decelerating approach | Measured |

### C · Fixable only in the edit — the ease-out has to be manufactured (§7)

### D · Not obtainable at all, on this roster, today

- Frame-accurate onset/apex/offset control of an expression.
- A specified number of blinks, or blinks at specified frames.
- Deliberate placement of a sub-500 ms micro-expression. Nothing addresses this range, and driven
  animation demonstrably smooths it away (§4).
- A true slow-out *inside* the generated motion.
- A guaranteed motion-energy distribution across the runtime.
- Deterministic eye-line or saccade timing.
- Any per-AU control. Motion Control exposes no brush, trajectory, timing, easing or speed
  parameter — it extracts motion from a reference clip and applies it. [SECONDARY · Kling AI,
  "Motion Control User Guide" · checked 2026-08-29]

**⛔ The routing rule.** If a shot's requirement lands in D, it is not a prompt problem and no number
of regenerations will reach it. Change the shot, or move the requirement into the edit. This is the
same discipline as `refinement-loop.md`'s stop rules, applied to time instead of to look.

---

## 7. Manufacturing the settle — eight edit-side remedies, by leverage

### 7.1 First, reframe the defect: **cut out of the peak**

A clip that ends mid-motion is a clip that **cuts invisibly.** Dmytryk's action cut says to cut at
the mid-point of a continuous movement, because the eye follows the movement across the join and it
masks the transition. [PRIMARY · Dmytryk, *On Film Editing* — via the local extraction, read
2026-08-29] Bowen is blunter: start-of-action cuts feel premature, end-of-action cuts feel late,
**mid-action is invisible.** [PRIMARY · Bowen, *Grammar of the Edit* — via the local extraction]

**So the model's back-loaded peak is an editorial asset for every clip except one that has to land.**
This inverts the whole problem: the defect bites at the end of a sequence, the end of the video, and
any held beat — and nowhere else. Before applying any remedy below, ask *does this shot land?* If it
cuts, you are already done, and the remedies cost time for nothing.

### 7.2 The remedies, when the shot does have to land

1. **Speed-ramp the tail.** Over the last **8–14 frames** (0.33–0.58 s), ramp playback from 100% to
   ~20–30%, **with the speed keyframes themselves eased**, not linear. Use optical-flow retiming, not
   frame blending. Keyframed retime and custom speed curves are standard [PRIMARY · Dovale,
   *Mastering DaVinci Resolve 20* (Speed Effects and Time Remapping) — via the local extraction], and
   the named anti-pattern in the same source is **two linear keyframes where the motion needs eased
   interpolation**, which produces exactly the mechanical result you are trying to remove.
   ⛔ The 8–14 frame window is inferred from the UI ease-out band (§1.3), **not measured and not
   published** — [UNVERIFIED]. Treat the first ten uses as the measurement.
2. **Freeze-frame settle with a residual move.** Hold the final frame **4–8 frames** while a very
   slight eased scale push (1–2%) continues under it. Freeze and strobe are standard retime tools
   [PRIMARY · Dovale]; the hold length respects the 6-frame minimum-hold convention (§2.1). This is
   the cheapest reliable ease-out in the box.
3. **Trim the dead head off every clip.** ~0.4 s ≈ **10 frames** of near-static opening on every i2v
   clip. Unless you are using it as anticipation, cut the first **6–10 frames**. On a pose-only frame
   pair, cut ~1.5 s. Measured.
4. **Retime the front to redistribute energy.** Where the dead front carries needed content, run the
   first section at 150–200% and leave the tail at 100%. This flattens the energy curve toward the
   even distribution the model will not produce — literally re-spacing the inbetweens, which is the
   animator's definition of easing (§1.1).
5. **Treat follow-through as a cross-clip property.** Once you are cutting mid-motion, overlap is an
   edit concern: let the outgoing motion vector continue into the incoming shot's first frames —
   **match the angle of the action; the vector should continue across the cut, not reverse.**
   [PRIMARY · Dmytryk — via the local extraction]
6. **Add a counter-move you control.** You cannot ease the model's internal camera; you *can* add a
   post scale/position move on top and ease that curve — including a small opposing push over the
   final ~10 frames that cancels part of the generated velocity. [UNVERIFIED · standard practice, no
   published spec]
7. **Let sound supply the landing.** A settling sound on the trim point — cloth, footfall, exhale,
   a bottle set down — supplies the perceptual arrival the picture does not. [UNVERIFIED · standard
   post practice; no study found measuring whether audio compensates for a missing visual slow-out]
8. **Re-generate shorter and cut, rather than fixing a long clip.** The last resort in the edit is
   often the cheapest decision one step upstream (§5, consequence 3).

**The vocabulary to use for all of this** is Pearlman's three controls — **timing** (which exact
frame the event lands on), **pacing** (rate and duration; how long a shot is held), and **trajectory
phrasing** (shaping the direction and intensity of movement across a phrase, its build and release).
[PRIMARY · Pearlman, *Cutting Rhythms* — via the local extraction, read 2026-08-29] Trajectory
phrasing names the missing quantity exactly: **the model produces a build with no release, and
phrasing is the editor's word for putting the release back.**

---

## 8. The QA rubric — numbers, not vibes

Add to the per-clip card in `realism-qa.md` §6. `scripts/clip_qa.py --landing` measures the last
three mechanically; the rest are eye checks at 0.25× speed.

| Check | Target | Source |
|---|---|---|
| Blinks in a 5 s clip | **≥1** at rest, **~2** if speaking | Bentivoglio 1997 |
| Blink shape | close ~1–2 f, hold ~1 f, open ~3 f (**opening ≈2× closing**) | Nyström 2024 + Meroz |
| Distinct gaze shifts in 5 s | order of **15**; **<5 reads glassy** | Rayner 2009 |
| Eyes move independently of the head | must be true | Saygin 2012; Kelly & Baena |
| Smile onset | **~12 f**; snapping on in **<6 f** reads posed | Schmidt & Cohn 2001; Schmidt 2006 |
| Apex held | yes — a brief apex reads insincere | Krumhuber & Manstead 2009 |
| Face perfectly symmetric | **must not be** | Krumhuber & Manstead 2009; Kelly & Baena |
| Camera pan speed | not faster than **one image width per 7 s** | RED |
| Clip ends mid-motion | acceptable **only** if you cut out of it; otherwise remedy 1 or 2 (§7) | Measured + Dmytryk/Bowen |
| Photoreal frame + mechanical timing | the more photoreal, the harsher the motion penalty — judge motion *hardest* on your best-looking clips | Chaminade 2007; Saygin 2012 |

---

## 9. The aliveness block — what this looks like in a prompt

Timing is not specifiable (§6A), so a prompt buys aliveness by **naming behaviours as content** and
letting the model place them. Keep it short: it competes for tokens with identity and light, and per
`prompting-craft.md` §6b every attribute a reference image already carries should not be re-described
in words.

- **Name two or three behaviours, not a list of ten.** "She blinks once, glances down at the label,
  then back up" is directable; "natural micro-expressions throughout" is decoration.
- **Prompt the body before the face** (§6A) — in a medium shot the acting is in the shoulders and
  the weight shift, and the face is a detail the model will smooth anyway.
- **Ask for the eye-crinkle by its anatomy** — "cheeks raise, crow's feet appear" — not by the word
  "genuine" (§3.4).
- **Ask for slow, not big.** "A small smile that grows slowly and holds" is the felt reading;
  "a big smile" buys the performed one (§2.2).
- **Ask for asymmetry explicitly.** Mild, one-sided — it is what viewers read as genuine, and the
  model's default is mirror-perfect (§3.4, `realism-qa.md` V2).
- ⛔ **Do not write frame counts, milliseconds or easing words into a prompt.** They are not honoured
  (§6A/D), they read as noise to the model, and they crowd out the words that do work. "Ease out" in
  a prompt buys nothing; a speed ramp in Resolve buys the thing you meant.

---

## 10. What this file cannot tell you

- **Frame counts for a head turn, a reach, or a take.** Only blinks and eye darts have traceable
  character-action numbers. Everything else circulating online is unsourced (§2.3).
- **Any published ease-duration for a camera move.** None exists (§1.3). The 8–14 frame tail ramp in
  §7 is an inference from UI motion design and must be treated as a hypothesis under test.
- **Whether a vendor honours numeric timing phrases in a prompt.** The guide recommends writing them;
  no evidence they are enforced (§6A).
- **Whether audio compensates for a missing visual slow-out.** Standard practice, no study found.
- **Saccade duration, and eye-head lead time in milliseconds.** Fixation duration and saccade
  amplitude are sourced; the durations were not retrievable.
- **Numeric means for deliberate vs spontaneous expression.** Paywalled — the *direction* of every
  effect is sourced, the values are not (§2.2).
- **Nothing here fixes a performance that was never designed.** Timing is the layer on top of a
  performance card (`direction.md` §1); a well-timed default pleasant face is still a retake.
