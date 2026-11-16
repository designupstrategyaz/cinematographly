# Sequence grammar — how shots, performances, light and time chain into a scene

**When to read this:** you have the beats and need the shots **in order**. Writing a shotlist, a
multi-shot prompt, or a promo that has to feel like one scene rather than a pile of good clips.
Someone has sent a camera-angle or lighting cheat sheet and asked whether to use it. A cut plays
correctly one shot at a time and wrongly as a sequence.

**What this file owns:** the order. `cinematography-craft.md` owns the single frame, `direction.md` §1
and `acting-for-the-model.md` own the single performance, `editing-storytelling.md` owns why a cut
works and the continuity system (§3), and `specifics-catalogue.md` §12–§15 holds the measurements
from five festival AI shorts. This file is the grammar between them: **what shot B has to do because
of shot A.**

**"Catalogue §N"** below means `specifics-catalogue.md` §N — the measured figures from the five films.

**Tiers.** Source tiers follow `research-quality.md`. `PRIMARY*` means a fetch tool summarised the
page and the figures were not re-read against the paper; quote those only after checking. Everything
was checked **2026-09-30**. Quotes are ≤15 words, at most one per source.

**⛔ The one thing to carry out of this file.** A camera angle, a close-up and a reaction each mean
something **only in sequence**. Low angle made a chess player look like the winner in story order and
did nothing when the same pictures were shuffled. A close-up raised viewers' attention to a
character's mind only when the face showed a feeling. A reaction reads after its stimulus — or, when
the cause is withheld on purpose, as a question the next shot answers. Every cheat sheet that assigns a meaning to a single frame is describing half of a pair.

---

## 1. The cheat sheets, checked

The owner sent nine infographics (camera angles with meanings, "ChatGPT camera commands", camera heights,
a Camera Language card, 10 and 8 lighting setups, composition commands, 20 camera angles with and
without AI prompts) and a 2023 Midjourney v5 prompting thread. **What they are good for: vocabulary.
What they get wrong: the meaning column. What they leave out entirely: order.** Not one of them says
what the next shot should be.

### 1.1 Camera angle and height claims

| Claim on the sheets | Verdict | Deciding evidence (§3.3–§3.4) |
|---|---|---|
| Eye level = neutral, personal | ✅ **Holds** for neutral and trusted; "real" untested | highest trust of three angles (Baranowski & Hecht); best for moderately motivated ad viewers (Meyers-Levy & Peracchio) |
| Low angle = authority, power | 🟡 **Conditional** | needs story order (Sevenants), a context where power matters (Giessner), a large angle (~35–40°), and it **costs trust** on a face talking to camera (Baranowski). Reversed in Gruber 2023 and McCain 1977 |
| Worm's eye = tall, mighty | 🟡 "Tall" holds; "mighty" conditional | +3.9 cm perceived height (Thomas & Pemstein); Kraft |
| High angle = weak, vulnerable | 🟡 **Conditional** | shorter and weaker in a story at ~40° (Kraft); trust drop not significant (Baranowski); reversed in one of two video-call samples (Gruber) |
| Bird's eye = isolation, action | ❌ **Unsupported** | no perception study found |
| Dutch = unease, drama | 🟡 **Weak** | only indirect: unstable images are liked less unless they imply motion (Fillinger & Hübner); tilted stills imply motion (Cian et al.) |
| The list of heights (ground → aerial) | ✅ **Holds as labels** | CineScale2 annotates the same heights; nobody has tested what each one *means* |
| "Shoulder level is more standard than eye level" | ❌ **Unsupported** | one uncited StudioBinder page; *Grammar of the Shot* and Mascelli both put neutral at the subject's head |

### 1.2 Lighting claims

| Claim on the sheets | Verdict | Deciding evidence (§6) |
|---|---|---|
| Three-point = interviews | 🟡 Convention, not an effect | revealing light produced weaker reactions (Huttunen), which fits informational use |
| Rembrandt = emotional | 🟡 Weak | no pattern-specific study; only the general finding that light which obscures facial features raises the reaction (Huttunen) |
| Side light = mystery, tension | 🟡 Weak | 90° side did **not** differ from 45° in the one EEG study (Huttunen 2025); under, top and silhouette did |
| Low-key / negative fill = moody | 🟡 Conditional | mystery and suspense (Poland) — but it reverses by genre (Huang) |
| Window light = indie; practicals = realistic | ❌ Untested | style associations. 45.9 % of our five films' shots are keyed by a visible practical (`specifics-catalogue.md` §11.3), which shows it is the norm, not that it works |
| Bounce = natural skin | 🟡 Conditional | soft 45°-from-above beat overhead light for attractiveness (Roelofs, 10 subjects) |
| Loop, butterfly, split, clamshell effects | ❌ Untested | no study of any named pattern. Eyelight does help (Swenberg) |
| Day-for-night: under-expose, cooler | ✅ Holds (stop values untested) | the blue shift of night vision is a real perceptual effect (Jensen et al., "Night Rendering", 2000) |

### 1.3 Composition and colour claims

| Claim on the sheets | Verdict | Deciding evidence (§7) |
|---|---|---|
| Rule of thirds | 🟡 Weak | "minor, if any, role" in preference (Amirshahi); the centre is preferred (Palmer) |
| Centred, symmetrical | ✅ Holds | Palmer; Jacobsen & Höfel; viewers' gaze sits at the centre (Tseng) |
| Leading lines | ✅ Holds when they converge | fixations cluster at the vanishing point (Borji) |
| Look room | ✅ Holds | viewers place an averted face looking *into* the frame (Chen, Colombatto & Scholl) |
| Shallow DoF isolates emotionally; deep gives context | 🟡 Half | the *attention* half holds (Zhang; Hata); "emotionally" is untested |
| Negative space = isolation; frame-in-frame; diagonal | ❌ Untested | only indirect: small faces are read more slowly (Cutting & Armstrong 2016) |
| Wide ratio = cinematic; square = nostalgia | ❌ Unsupported | no study. Vertical on mobile is processed more fluently (Mulier et al.) |
| Colour palette sets the emotion | 🟡 Conditional | saturation drives arousal, brightness arousal and pleasantness; hue moves arousal but not reliably pleasantness (Wilms & Oberfeld) |

### 1.4 The 2023 Midjourney thread, against 2026 models

- **"From below" / "from above" instead of "low angle" / "high angle":** no longer needed. Every
  video vendor documents "low angle" directly (§9). Seedance's advice to add a plain description
  after a technical term supports writing **both**: "low angle, the camera near the floor looking up".
- **"Drone shot" or "aerial" instead of "bird's-eye":** outdated as a general swap, because they are
  two different settings. Aerial is a **height** (the camera is far up); bird's-eye, overhead and
  top-down are a **tilt** (the camera points straight down). Runway lists both; CineScale2 labels
  them separately.
- **"Extreme" as a prefix, "side view":** no vendor evidence either way `[UNVERIFIED]`.
- No Midjourney v7 angle guidance was found `[UNVERIFIED]`, so the thread cannot be checked against it.

⚡ **Use the sheets as a word list. Take the meanings from §3 and §6, and the order from §8.**

## 2. The scene arc — orient, move in, release

**One scene is one arc.** Across ~3,200 scenes from 24 Hollywood films (1940–2010), scenes open on a
wider shot, move in, and widen again at the end; a new scene or subscene starts about every
**55 seconds**, and **a change of shot size is the strongest cue that a new scene has begun**. Shot
size does *not* trend across acts. It marks scenes, not acts. Longer shots are wider (duration with
scale r = .78), about 90 % of shots contain a face, and conversations are mostly medium close-ups
without music. `[PRIMARY · Cutting, "Narrative theory and the dynamics of popular movies",
*Psychonomic Bulletin & Review* 23:1713–1743, 2016 · checked 2026-09-30]`

**Inside the scene the durations draw a U.** Shots are longer at the start and end of a scene and
shorter in the middle; median 7 shots per subscene; mean shot 4.8 s in scenes, 4.1 s in subscenes
(action 4.1, comedy 5.5, drama 6.7). Sequences are held together partly by shared **sound** — music,
voiceover, pervasive sound — and music plus short even shots blurs the scene breaks viewers
perceive. `[PRIMARY · Cutting, "Sequences in popular cinema generate inconsistent event segmentation",
*Attention, Perception & Psychophysics* 81:2014–2025, 2019 · checked 2026-09-30]`

**The place change is what viewers use.** Viewers agree ~90 % on where one event ends. Shot, motion,
luminance and colour explain ~30 % of where they put the boundary, ~50 % once place and time changes
are added. `[PRIMARY (abstract) · Cutting, Brunick & Candan, *JEP:HPP* 38(6), 2012]` "Location shifts
dominate character and time shifts in event segmentation"; establishing shots are wider and longer
than average, and a **re-establishing** shot of a place already seen shows less and runs shorter.
`[PRIMARY (abstract) · Cutting & Iricinschi, *Cognitive Science* 39(2), 2015]`

**Opening close is legitimate, and current practice.** Intensified continuity covers dialogue in
tight singles and over-the-shoulders and delays or drops the establishing shot. Bordwell's example is
a café scene covered in 2 shots by Lubitsch and in 41 by the Ephron remake. `[PRIMARY* · Bordwell,
"Intensified continuity revisited", blog, 2007]` Our five films confirm it: the establishing wide is
rare and a third of each film is a face (`specifics-catalogue.md` §11.2).

**The dramatic unit that fills the arc** is Swain's. A **scene** is goal → conflict → disaster, held
together by continuous time; the goal is short-range and reduced to one act the camera can
photograph, and the disaster is a logical but unexpected development, often new information. A **sequel** is reaction → dilemma
→ decision, held together by the character's preoccupation rather than by continuous time, and it is
where time can be compressed. `[PRIMARY · Swain, *Techniques of the Selling Writer* (1965; OU Press
1973), ch. 4, Internet Archive transcription without page numbers · checked 2026-09-30]`

⚡ **A 30–60 s ad is one scene: one arc, one goal, one disaster or reveal.** A 3–15 minute short is
roughly one of Gulino's eight 10–15-minute sequences: a single tension with its own beginning, middle
and end, answered only in part `[SECONDARY · The Story Department; Film Courage interview ·
checked 2026-09-30]` (that mapping is this file's inference). The shot chain that falls out of Swain:

> **goal shot → exchange (stimulus / reaction units) → disaster, usually a reveal or an insert →
> reaction on a readable face → hold (the dilemma) → action shot (the decision) → the next goal.**

In our five films 12 of 20 payoffs are carried by an **object**, not a line
(`specifics-catalogue.md` §14.3). The disaster is usually something the camera shows.

## 2b. ⚡ Contrast, not just continuity — the contrast plan and the camera plan

**Most of this file is continuity, and continuity is affinity.** Block states the principle in one
line: "Contrast increases visual intensity, but affinity decreases visual intensity."
`[SECONDARY · Bruce Block, *The Visual Story*, via a published review · checked 2026-10-04]` His seven
basic visual components are space (deep or flat), line, shape, tone, colour, movement and rhythm.
Matched pairs, one key side, one colour family, intensity climbing one step at a time, eye level as
the baseline: each rule in §3–§7 keeps the viewer oriented, and each one, applied everywhere, lowers
the intensity of the whole piece.

`[measured 2026-10-03 · lab-00005 · 20 briefs, two blind judges]` That is what the test showed. With
this file and the craft references in the prompt, Claude's ads became more original (7.95 against
6.72 without the skill) but no more varied as sequences (7.18 against 7.13), and DeepSeek's the same
(5.11 against 5.16). Every rule was followed; none of them asked for contrast.

**What stays continuous — the only non-negotiables:**

- **screen geography:** the 180° line and where people are (`editing-storytelling.md` §3.3);
- **a recurring character's identity:** the key side within a scene (§6.1), the face, the wardrobe;
- **the audio bed** across AI joins (§4.5).

Everything else — size, height, camera behaviour, rhythm, colour, tone, depth — is a design choice,
and leaving it the same is the flat choice.

**The contrast plan — one line on the chain, written before the shots.** Pick one or two components
and write each as a progression that peaks where the story peaks:

| Component | Written as | What it looks like |
|---|---|---|
| movement | still → kinetic (or the reverse) | the camera holds through the setup, starts moving at the turn, travels at the climax |
| rhythm | long → short | 4–5 s shots in the setup, 1–2 s at the climax; shot lengths fall sharply early in a climax (§5) |
| size | wide → tight, or tight → wide | the piece closes in on one face, or opens out from a detail to the world |
| space | flat → deep | a wall behind the subject early, a long corridor or a vista at the payoff |
| tone | bright → dark → bright | the luminance arc (§6.4) |
| colour | one family → a collision | one warm family until the brand colour arrives |
| line | level → diagonal | a calm, level world until something tips |

Written on the chain as `Contrast: movement: still → kinetic; rhythm: long → short`.
`sequence_lint.py` reads it and checks the three it can measure from the rows — movement, rhythm and
size — and says which ones only the boards can show.

**The deliberate break.** §8's table is the baseline: the affinity version of each beat. Every piece
breaks it on purpose at least once, at the moment it most needs intensity, and says so in the
chain's **Break** column — the size jump against the step pattern, the camera moving where the scene
has held, a colour collision at the turn, a height change for the reveal. A sequence with no break is
by the book, and by the book is the stale result this section was written to stop.

**The camera plan.** The camera's behaviour belongs to the contrast plan, not to a per-shot default
(`cinematography-craft.md` §3.8):

- **Every row's Move says what the camera does:** `locked`, or a move with a job — reveal, follow,
  connect, change scale, carry energy across a cut.
- **Expect a mix.** About four shots in ten move in the five festival films
  (`specifics-catalogue.md` §10.3), and a median 46 % in 38 real ads (§2c). The lint warns below one
  in five (the frozen camera) and above four in five (nothing holds); 5 and 6 of 36 award winners sit
  past those lines on purpose, so each warning is a question.
- **Long runs of held shots are a choice real ads make often — as runs, not as the film.** 24 of 36
  award winners hold four or more locked shots in a row (their longest run: median 5, 75th percentile 8)
  while still moving about half their shots. Past eight, mark the run in Break (§2c).

  ⚠️ **SUPERSEDES IN PLACE** (2026-10-04) — previously: "More than three held shots in a row is a device, not a habit: mark it in Break." That threshold came from no measurement and would have flagged two in three of the award-winning ads measured in lab-00006 (`specifics-catalogue.md` §16).
- **Not every move is a push.** Pans and tilts outnumbered pushes three to one in those films; a
  sequence whose every move is a push-in is the prompt pipeline's default, not a plan
  (`cinematography-craft.md` §3.8, the push-in row).
- **A move is still one named move per clip.** Unfreezing the camera cost producibility in the lab:
  blind judges marked the v2.14 Claude scripts down 0.55 against v2.13, worse on 15 of 20 briefs
  `[measured 2026-10-04 · lab-00005 v2.14 · n=20, 2 LLM judges]`. Pick each move from the per-move
  ruling in `cinematography-craft.md` §3.8 (the twelve are not equally available) and never stack two.
- **The ending is not a crane.** A pull-out or rise to a high wide is the stock last shot; when the
  table offered it as the only Resolution move, 13 of 20 Kimi ads ended on one (§8). Close on what
  the contrast plan needs: a settle after a moving climax, or the one move after a held one.
- **Save the approach for the moment that should be felt.** A camera moving toward the subject drew
  a stronger sensorimotor response than a held or zooming one, and viewers rated it the most
  involving (`cinematography-craft.md` §3.8, lever 5).

## 2c. ⚡ Ads are not festival films — the measured ad baseline

`[measured 2026-10-04 · analyze.py (lab-00006) · 38 ads: 24 Cannes Lions / D&AD film winners 2018–2026 and 14 strong spots, 1,331 shots, every cut confirmed by hand on 4 fps strips]`

Everything above this section was measured on feature films and five festival AI shorts. lab-00006 measured
real ads for the first time (every table: `specifics-catalogue.md` §16). Where the two disagree, an ad follows
this section. Medians across the 38 ads, with the interquartile range:

| Channel | Real ads | The skill's own scripts (lab-00005, Claude v2.14) |
|---|---|---|
| Mean shot length | **1.8 s** (1.5–2.6) | 3.7 s |
| One shot | median 1.5 s; 1 in 10 under 0.7 s, 1 in 10 over 3.6 s | — |
| Shots that move | **46 %** (30–71 %) | 36 % |
| Wide shots (WS/EWS) | **32 %** (19–45 %) | 21 % |
| Eye-level shots | **77 %** (70–87 %) | 47 % |
| Longest run of held shots | **5** (2–8) | 3 |
| Cuts that keep the same size | 25 % | 17 % |
| Straight cuts (no whip, dissolve, match or wipe) | **97 %** | 94 % (bare Claude 79 %, Kimi 76 %) |

**A second ad source agrees, and the films sit well above it (2026-10-25).** The five direct-response
examples in a direct-response agency's brief (1–4 min) average about **2.0 s** a shot in four of five, and 2.7 s in the one that
is a third talking head `[measured · film_breakdown + a model read of the 4 fps strips, so ±10 %]`. The three
AI shorts in the database average **2.8–4.2 s** on their person-read cuts (F5 2.84, F1 3.43,
F4 4.16 s) `[measured · reference-shots.jsonl, sponsor tail dropped]`. A detector-only count reads them
3.2–4.6 s, because it misses about one cut in ten (`assets/reference-cutcheck.json`). A film's pace is not an
ad's pace: never take a festival short's rhythm as an ad's.

**Music-video shot lengths, as practitioner data** `[PRACTITIONER · course notes]`. Our capture of a course
gives medians of about **1.5–2.9 s a shot** across five lessons (1.52; 2.17 over 71 shots; 2.29 for a 30-clip
reel; 2.78 over 358 shots; 2.92 over 65 shots). These are medians per shot, while the table's 1.8 s is a mean
per ad, so they are not one measure and do not compare directly; the One shot row (median 1.5 s) is nearer in
kind, but it is taken across the corpus, not per piece. One more lesson read 0.16 s, which looks like scrubbing
inside an editing lesson: the capture cannot always tell played picture from scrubbing, so re-derive these with
`film_breakdown.py` before use. Data only, never a cutting target: music-led cutting is `move-catalogue.md`
Appendix P, P12.

**What follows for an ad's shotlist:**
1. **Cut about twice as fast as §2's festival numbers.** A real ad runs about 15 shots per 30 s. Hold 3–5 s for
   dialogue, deadpan and the payoff; let inserts run 0.5–1 s. **Dur in the chain is time on screen in the cut,
   not the generated clip:** generate lead-in + cut + handle (`ai-generation.md`, clip length; ⚠️
   **SUPERSEDES IN PLACE** (2026-10-26) — previously: "generate the model's length (usually 5 s,
   `ai-generation.md`)") and cut the part
   after the ramp — that is how an AI piece reaches real-ad pace without fighting the model. Dialogue-led and deadpan spots are the slow end
   (3.3–5.5 s mean shot). No measured ad cuts to even lengths (coefficient of variation median 0.64, lowest
   0.36), and the shortest shots sit mid-film (median position 55 % of the running time), not in the open.
2. **Show the world.** A third of shots are wide. The first shot is a wide in 23 of 38 ads and runs longer than
   the ad's average shot (median 2.8 s).
3. **Height is an accent, not a spread.** Eye level three shots in four; low 16 %, high 8 %, aerial 2 %.
4. **Enter late.** 45 % of cuts land on an action already under way; 2 % on its start. A generated clip starts
   from rest, so write the start state mid-motion or generate a head and cut in after the ramp (§9, item 8).
5. **Cut on motion and looks, not on beats.** The outgoing shot carries motion at 36 % of cuts and a look at
   11 %. Cuts land on a detected beat no more often than chance (31 % against 32 %); 2 of 37 ads clearly cut
   on the beat. Let the music land a few hits — the reveal, the product — not every cut.
6. **Change one or two things per cut, never the emotion.** A cut usually changes subject and size, often the
   angle. Emotion changes across 1.2 % of cuts — the turn happens inside the shot (§4.3) — and place, subject
   and emotion change together at 2 cuts in 1,293. Lab work agrees: an emotion change is the most taxing thing
   a cut can add `[PRIMARY* · Lang, Kurita, Gao & Rubenking 2013, Media Psychology 16(2) · checked 2026-10-04]`.
7. **Budget the two kinds of cut separately.** Edits (a new angle on the same scene) run a median 8.6 per 30 s;
   cuts to a new place or time 4.4 per 30 s. The five ads over 10 per 30 s are all music-led montages with no
   spoken claim, which fits Lang's threshold of about 10 unrelated cuts per 30 s for message memory
   `[SECONDARY · Niederdeppe 2005, reporting Lang et al. 1999 · checked 2026-10-04]` and the finding that fast,
   arousing pace costs verbal memory, not visual `[PRIMARY* · Lang, Potter & Bolls 1999, Media Psychology 1(2) ·
   checked 2026-10-04]`. A fast montage carries its claim in pictures.
8. **Straight cuts.** Whips, dissolves, match cuts and graphic wipes are 3 % of real cuts together. A transition
   on every other cut is the model's default, not advertising. Hidden joins (a lens wipe, whip blur, steam) are
   how a long take hides its cuts, not a garnish.
9. **Long holds are normal — inside a piece that still moves about half its shots.** 24 of 36 award winners
   hold four or more locked shots in a row, and the same ads move a median 46 % of their shots: the holds
   are runs, not the whole film. `sequence_lint.py` warns on a run from nine (past their 75th percentile)
   and on a piece where under one shot in five moves.
10. **Same-size cuts are allowed.** A quarter of cuts keep the size and half jump two steps or more. The ladder
    in §4.2 is a dialogue-coverage tool, not an ad's rhythm.
11. **Brand: choose the mode per brief.** *Brand film* (the award winners): the product is on screen early
    (median 17 % of the running time), the brand late (median 76 %; only at the end in 15 of 38), in one or two
    runs, with an end card of about 4 s (IQR 3.0–5.5, 7 % of the running time). *Performance*: the proposition in
    the first 3–5 s and the brand pulsed. The vendors say so `[PRIMARY · VENDOR · Meta × Toluna; SECONDARY ·
    VENDOR · Vidmob × TikTok, 1,678 ads · checked 2026-10-04]`, and brief, repeated brand appearances cut
    avoidance by about 8 % `[PRIMARY · Teixeira, Wedel & Pieters 2010, Marketing Science 29(5) · checked
    2026-10-04]`. Never open on a logo card. The end card's floor is reading time: 0.2 s a word plus 2 s up to
    9 words, plus 3 s from 10 words `[PRIMARY · Clearcast legal-supers guidance, 2019 · checked 2026-10-04]`.
12. **Give the logo and the claim a beat.** Not in the half-second after a hard cut — gaze re-centres about
    333 ms after one `[PRIMARY · Mital, Smith, Hill & Henderson 2011, Cognitive Computation 3(1) · checked
    2026-10-04]` — and not straight after the peak, where a second target 180–450 ms later is missed
    `[PRIMARY · Raymond, Shapiro & Arnell 1992, JEP:HPP 18(3) · checked 2026-10-04]`. Put the new subject near
    the centre after a hard cut: 72 % of first frames do.
13. **Slow motion by subject.** It lifts liking for pleasant, complex product action — a pour, fabric, food
    `[PRIMARY* · Stuppy, Landwehr & McGraw 2024, JMR 61(2) · checked 2026-10-04]` — and reads as contrived on a
    human endorser `[PRIMARY* · Yin, Jia & Zheng 2021, JMR 58(5) · checked 2026-10-04]`.

14. **Revise in two passes — the director's review, then the card — at most three rounds.** Measured on the
    lab-00005 briefs in lab-00008 (`specifics-catalogue.md` §16.10):
    - **Round 1 — the director's review.** Re-read the chain against the brief and this section as a whole and
      rewrite what makes it a weaker ad: people who only stand and look, a world never shown, the product or
      brand placed against the brief's mode (item 11), an end card shorter than its reading time, a fancy join
      where a straight cut works, Dur written as the clip's length. Story first; the concept, the beats, the
      must-say line and the brand line stay.
    - **Round 2 — the card.** Run `python3 scripts/sequence_lint.py <SHOTLIST.md> --baseline`. It prints eight
      numbers (mean shot, shots that move, wide, close, eye height, same-size cuts, 2+ size jumps, longest held
      run) against the middle half and the 8-in-10 range of the measured ads, and a `revise` line for each one
      outside 8 in 10. Revise only those, each with its reason; a deviation kept on purpose goes in Break with why.
      **A 9:16 film of 45 s or less** (the job's CHECKPOINT `Format:` preset, and the sum of the chain's Dur) gets
      those lines, and the three ad-baseline warnings (slow, no world, height spread), as notes citing
      `specifics-catalogue.md` §16.9: 35 of the 38 ads are landscape and only 9 run 45 s or less (§16.1), so they
      are not its baseline. The held-run, affinity and camera-plan checks stay warnings (v2.69.0).
      **A long-body DR job (`modes/ugc-volume.md` §2b) adds `--regime dr`**: the card then reads against 13
      measured direct-response ads (lab-00009, one agency's work, so provisional). Read against the award
      bands, those 13 ads came out OUT on wide in 11, on 2+ size jumps in 8 and on close in 7: the award card
      would push a DR script toward framing DR ads do not use.
    - **Round 3 — only when something is still OUT and not kept on purpose.** Card once more, then stop.

    Why this order: the card alone fixed the numbers (Claude: 33 OUT measures on 17 scripts → 1, in one round)
    but judges scored the pieces only a little higher (sequence variety +0.18 and +0.41 on a 1–10 scale in two
    blind judgings). The review alone made better ads (variety +0.76 and +0.85, action +0.62 and +0.71) and left
    the numbers out (33 → 28). The review then the card scored best (variety +1.24, action +1.03, imagery +0.74,
    ranked above the first draft in 29 of 34 judgements) with nothing OUT. A router model converges slower
    (Kimi K3: 61 → 33 → 18 → 14 OUT over three card rounds), and a third round brought no judged gain after
    the review (ranked above the first draft in 28 of 40 after round 2, 23 of 40 after round 3). Every revision
    cost a little producibility (−0.1 to −0.6; −0.2 to −0.3 for review then card): more shots and moves to make.
    ⛔ Never revise toward the middle: the bands are ranges, and a chain tuned to every median is the flat
    version of the piece (§2b). ⛔ Never relabel a size or height to pass — the labels describe the frame. The
    ads were coded against the subject's eyes, so a film at a child's or an animal's eye line reads low on eye
    height by construction: keep it and say so in Break. ⛔ Re-check the running time after every round (Kimi's
    review pass drifted to a median 26.9 s on 30–45 s briefs). Written rules alone over-correct — a single table
    cell made the crane ending of 13 of 20 Kimi ads, and "long holds are normal" froze the camera — so the
    numbers are fed back per piece, not stated harder in prose.

⛔ **Limits.** One reader per ad; 35 of 38 are landscape, so **vertical is not yet measured**; award films
over-represent big-budget craft; beats were detected on the full mix. The lab record is
lab record lab-00006 (not shipped).

## 2d. ⚡ The energy plan — fast, fast, hold

Adopted 2026-10-26 from the three-model jury (the intent and emotion proposal of 2026-10-26 [studio history],
M16 with M3, M4 and M14). §2b plans contrast between shots in kind; this plans it in **energy**: how
much the shot moves and how hard, on a 1–5 scale, written per shot in the chain's `Energy` column.

- **1** a held frame where almost nothing moves (a face taking it in, a product at rest);
  **3** an ordinary action at its persona's pace; **5** the commit: the throw, the slam, the reveal.
- **Plan it like music.** A burst lands against a hold: fast, fast, hold. In an ads sequence, put one
  shot at 1–2 every four to six, so the bursts read. In a drama, the hold usually comes after the turn
  (§4.3).
- **Each shot's energy comes from its intent** (`motion-craft.md` §6b) and its person's baseline
  (`acting-for-the-model.md` §7b), not from the camera. A fast camera over a calm action is not energy 5.
- **Three optional lines on the event card raise a shot's charge** without raising its speed
  (`direction.md` §2b): the decision tell before the action, the one obstacle the intent beats, and the
  prop that witnesses the state.

`sequence_lint.py` reads the column: a value outside 1–5 fails; a chain where every shot has the same
energy warns; under `--regime dr`, more than six shots in a row at 3 or more with no still beat warns.
A chain without the column is told once, as information. `[opinion · the jury's consensus; the
thresholds are house values]`

## 3. Shot size and angle across a cut

### 3.1 Change the picture enough — but there is no step rule

`Grammar of the Edit`: two shots "must be different enough" in angle and shot type, or the cut reads
as a jump. `[PRIMARY · Thompson & Bowen, 3rd ed. 2013, Internet Archive search-inside snippet]` Why
the 30° figure has no empirical validation is `editing-storytelling.md` §3.4. Mascelli names three
patterns, **progressive** (step by step in or out), **contrasting** (a jump) and **repetitive**, and
warns against the routine wide–medium–close. `[PRIMARY · Mascelli, *The Five C's of Cinematography*,
1965, snippets]`

**"Change size by at least two steps" was not found in any searchable editing text** `[UNVERIFIED]`.
Our films do not follow it either: same size on 23–36 % of cuts, one step 23–31 %, two 20–32 %,
three or more 13–24 %, in and out nearly balanced (`specifics-catalogue.md` §15.3). A same-size cut
works when the subject, angle or place changes instead.

### 3.2 Dialogue — matched pairs that climb to a peak and recede

- **Pairs.** Match size, lens, camera height and tilt on both sides of an exchange. `[PRIMARY ·
  Bowen & Thompson, *Grammar of the Shot*, 3rd ed.; Mascelli, snippets]` Over-the-shoulder close-ups
  come in matched pairs, and a run of close-ups should match in size (Mascelli).
- **Peaks.** A long dialogue needs "certain peaks of interest": coverage moves closer towards each
  peak, then drops back to medium shots to rest the audience. Use shot distances in pairs, at most
  two pairs. `[PRIMARY · Arijon, *Grammar of the Film Language*, snippets]`
- **Order.** Establishing → shot/reverse-shot on one side of the line → re-establishing, and a
  shot/reverse-shot "need not employ eyeline matches" (most do). `[PRIMARY · Bordwell & Thompson,
  *Film Art*, 11th ed., snippets]` The 180° line itself is `editing-storytelling.md` §3.3. One
  addition: viewers often do not *notice* a line cross `[PRIMARY · Smith 2012, p. 25]`, but keeping
  the line made judgements of where the actors are faster `[PRIMARY (abstract) · Candan Şimşek, PhD
  thesis, Cornell, 2017]`. `[inference]` A cross may cost processing even when nobody sees it.
- **The reaction shot is 17 %.** Across 24 films (1940–2010) reaction shots are ~17 % of all shots,
  flat across the decades. They average **3.4 s** against 5.6 s for shot/reverse-shot and OTS, and
  4.3 s when one ends a conversation. 300 of 679 two-person conversations end on at least one
  **cryptic** reaction — a silent listener with a restrained face, slightly negative and slightly
  aroused, not neutral, framed at MS–MCU. `[PRIMARY · Cutting & Armstrong, "Cryptic emotions…",
  *Cognitive Science* 42:1317–1344, 2018]`

⚡ **End an exchange on a restrained listener for 3–4 s.** Not on the speaker's last word.

### 3.3 Angle — an adjective the viewer does not notice, and it needs its pair

**The experiments.**

- **Kraft 1987.** Characters shot ~40° from below were rated taller, stronger, bolder and more
  aggressive (5 of 6 scales, F(2,82) = 17.6–29.3), but **not** better or worse. The angle changed
  what viewers remembered the story to be — who caused the accident — while viewers barely
  remembered the angle itself (d′ 1.75 for angle against 4.19 for content). The effect was largest
  where the action gave least context. His design paired one character low with the other high.
  `[PRIMARY · Kraft, *Memory & Cognition* 15(4), 1987, full text]`
- **Sevenants & d'Ydewalle 2006** (116 viewers, ~35°). Low angle made characters seem more powerful
  **only when the pictures ran in story order**. In a chess story the player shot from below was
  judged the winner 59 % of the time, against 12 % at eye level and 10 % from above; shuffled, there
  was no effect. `[PRIMARY* · *Psychologica Belgica* 46(3), 2006]`
- **Baranowski & Hecht 2018** (34 viewers, 12 actors talking to camera at +30°, 0°, −30°). Eye level
  was trusted most (5.03); from below 4.27, a large drop (ηp² = .31); from above 4.57, not
  significant. Attractiveness did not change. `[PRIMARY* · *Empirical Studies of the Arts* 36(1)]`
- **Thomas & Pemstein 2015.** A webcam 17 cm low made people look ~3.9 cm taller (d = .53) and
  changed how partners played a money game. `[PRIMARY* · *Frontiers in Psychology* 6:306]`
- **Giessner et al. 2011.** Powerful people are photographed from below more often, and ordinary
  participants chose low-angle photos for high-power roles (22 of 61 vs 2 of 54). The code is
  shared, and strongest where power is already in the story. `[PRIMARY* · *Media Psychology* 14(4)]`
- **Against.** Gruber et al. 2023: in one of two video-call samples the actor filmed from below read
  as *less* powerful (d = −0.40), possibly because the high camera gave more eye contact.
  `[PRIMARY* · *Computers in Human Behavior Reports* 10:100285]` Witkower & Tracy 2019 (five studies,
  1,517 people): a head tilted *down* with the eyes on the viewer reads as more dominant, because the
  brows appear lowered. `[PRIMARY (abstract) · *Psychological Science* 30]` McCain, Chilberg &
  Wakshlag 1977 found a *higher* camera raised competence ratings. `[SECONDARY · via Baranowski &
  Hecht]` **Power and credibility are two outcomes, and one angle can raise one and lower the other.**
- **Ads.** Low-motivation viewers rated a product seen from below best; for moderately motivated
  viewers "eye-level shots produced the most favorable evaluations"; for highly motivated viewers
  angle effects are unlikely. `[PRIMARY (abstract) · Meyers-Levy & Peracchio, *Journal of Marketing
  Research* 29(4), 1992]` The same authors later found style carries meaning only when the copy has
  already planted the idea. `[PRIMARY (abstract) · Peracchio & Meyers-Levy, *JCR* 32(1), 2005]`

**What our films do.** 90.5 % of shots are at eye level (`specifics-catalogue.md` §11.1). Of 102
low or high shots, **6** are followed by the opposite angle (catalogue §15.4). High is an insert and low is an
MS of feet crossing a threshold (catalogue §12.1). They use angle for geography and point of view, not power.

⚡ **Rules.**
1. **Eye level is the baseline.** Leave it rarely, and with a job: point of view, geography, a
   power relation the story has already set up.
2. **Anyone talking to camera stays at eye level, level tilt.** The trust cost is the one effect
   measured on faces addressing the viewer — one study, significant from below, not from above.
3. **When angle has to mean power, go far (30–40°) and give it its partner** — the other character
   at eye level or the opposite angle, in story order. `[inference]` A single low shot among
   eye-level shots still moves perceived height (Thomas & Pemstein), but without story context it
   reads as a camera position rather than a statement.
4. **A POV or insert is at the looker's eye height**, not a comment on the subject: Mascelli's
   point-of-view close-ups are shot at the eye level of the character who is looking. This is what our films' high-angle inserts are.
5. **In feed ads, where attention is low**, a low angle on the *product* may help; keep the
   spokesperson at eye level; make the copy and the angle point at the same trait.
6. `[inference, untested]` A high camera with the performer looking **up into the lens** may read
   dominant rather than weak (Witkower & Tracy's brow effect). Do not rely on high = weak for a
   face that looks at the viewer.

### 3.4 Height and tilt are two settings — write both

CineScale2 annotates **tilt** (overhead, high, neutral, low, Dutch) separately from **height**
(aerial, eye, shoulder, hip, knee, ground). Its per-category counts are hand-picked, so they say
nothing about how common each is. It describes knee- and ground-level shots as a way to show someone
walking without showing the face. `[PRIMARY · Savardi, Kovács, Signoroni & Benini, *Data in Brief*,
2023]` Ozu held a low camera in nearly every shot without tilting it up. `[PRIMARY* · Bordwell, "A
modest extravagance", blog, 2011]` Seedance 2.5's worked examples state them separately — a low angle
at a child's eye level. `[PRIMARY · BytePlus ModelArk Seedance 2.5 guide, updated 2026-09-28]`

**Reading height from a frame needs no judgement: the horizon sits at lens height.**
`[PRIMARY · Katz, *Film Directing Shot by Shot*, 1991, snippet]` A level camera at shoulder height
still looks like eye level; judge by where the horizon falls. That is the check to use, because a
vision model's angle label is right only 58 % of the time (`specifics-catalogue.md` §11.7).

⚡ **Write "camera at hip height, level" or "camera at eye height, tilted 30° down" — never "low
angle" alone.** "Low angle" is four instructions (`cinematography-craft.md` §5.4). Our films'
threshold shots are read as "low"; whether the camera was tilted up or only placed low was not
recorded, which is exactly the ambiguity two values remove.

### 3.5 Close-ups are punctuation, and only on a face that shows something

- A close-up of a **sad** face raised unprompted talk about the character's thoughts and feelings
  (3.17 mentions, against 2.29 for the long-shot version); a close-up of a **neutral** face did not
  (1.97). Asked directly, all groups understood the character equally well. `[PRIMARY* · Rooney &
  Bálint, *Frontiers in Psychology* 8:2349, 2018]`
- More is not better: **three** close-ups inserted into an 8-minute film worked better than 4, 5 or
  10. `[PRIMARY* · Bálint, Blessing & Rooney, *Poetics* 83, 2020]` One film, one manipulation — it
  sets a direction, not a quota.
- Close shots activate face, emotion and theory-of-mind regions; long shots, spatial and place
  regions. `[PRIMARY* · Raz et al., *Projections* 13(3), 2019]`

⚡ **Put the close-up on the change.** Our films frame the big emotion tight in every film
(`specifics-catalogue.md` §13.5) and cut tighter on most intensity jumps — 60–84 % by film (catalogue
§15.2). A close-up of a face doing nothing spends the frame that carries the most.

## 4. Chaining a performance across shots

### 4.1 The unit: stimulus, then feeling, then action, then speech

Swain's motivation–reaction unit: a **motivating stimulus** is "anything outside your focal
character to which he reacts", and the reaction has three parts in a fixed order, **feeling →
action → speech**, ordered by how much the character controls each. Parts can be dropped; the kept
ones stay in order. The stimulus must come **before** the reaction, or the reader supplies his own
reading, and an action with no readable feeling is ambiguous — turning away can mean anything from
boredom to rage. `[PRIMARY · Swain, ch. 3 · checked 2026-09-30]` The five-step version with a separate "reflex"
is Ingermanson's reading, not Swain's. `[SECONDARY · Ingermanson, advancedfictionwriting.com]`

⚡ **In shots:** show or sound the stimulus (a line, an event, an insert) → the feeling lands on a face
big enough to read → the involuntary body movement → the deliberate act or line. The feeling beat
needs MCU or closer, or a body read in a wider frame (`acting-for-the-model.md` §3–§4). A face in an
extreme long shot is read ~140 ms slower than one at MCU (§5).

**The deliberate exception.** A reaction to a cause the viewer has not seen yet turns the next shot
into a reveal: reaction → cause → realisation (`specifics-catalogue.md` §1.5, where the prompt says
outright that we see only her, not the wall). Swain's warning is the mechanism — the viewer supplies
a reading — and here that is the point. It needs the cause **in the very next shot**; a reaction
whose cause never arrives is the orphan (§10).

### 4.2 Intensity climbs a ladder, and the frame climbs with it

**Measured** (`specifics-catalogue.md` §15.1–§15.2): 86–97 % of cuts between two performers keep the
intensity or move it one step. When it jumps two or more, the frame moves with it — tighter going
up, wider coming down — in 60–84 % of jumps by film, against 52–67 % for a step of one and a chance
level near a third (the catalogue's own arithmetic, not a measurement). Colour carries the jump in
only two of five films.

There is no experiment on matching performance intensity across coverage `[gap]`. The craft side:
Caine on matching business across master, medium and close-up `[TERTIARY · blog summary of *Acting in
Film*]`, and Murch's line that it is "the job of the subsequent shot to 'receive' energy from the
previous one" `[SECONDARY · Lahr, *LRB* 47(19), 2025, reviewing Murch]`.

⚡ **Plan the intensity as a ladder of 0–3 across the shotlist, and give every jump of two a frame
jump in the same direction.** A 1 in a WS followed by a 3 in a WS is the pattern our five films
almost never cut. The ladder is the baseline, not the goal: the jump is the contrast tool (§2b), and
the piece should use it where it peaks, with the frame jump that carries it.

### 4.3 The change lands late, and the hold is inside it

- Changes inside a shot land **late**: 112 late against 17 early across 934 performer shots
  (`specifics-catalogue.md` §13.3).
- The shot that carries the change is held **1.15–1.89×** longer (catalogue §13.4); the shot **after** it runs
  at the film's normal length (catalogue §15.5). The time is spent inside the turn shot.
- An expression that snaps on reads fake. Synthetic smiles with a ~133 ms onset were judged more
  fake than ~533 ms onsets, and genuineness rose with onset, apex and offset duration.
  `[PRIMARY · Krumhuber & Kappas, *Journal of Nonverbal Behavior* 29(1), 2005]` The onset table is
  `timing-and-performance.md` §2.

⚡ **Write the turn shot as "before held, then one change" in its second half, give it the extra
second, and do not add an aftermath shot to make room.**

### 4.4 The reaction — restrained by default, released once

- Reaction shots are brief and **restrained**, and end conversations more and more often (§3.2).
- Only **1.9 %** of our 934 performer shots are a full release (`specifics-catalogue.md` §13.1).
  The most intense run sits **before** the climax in four of five films, no climax is played at 3,
  and after the climax the intensity is equal to or higher than before it: the action lands, then the
  release comes (catalogue §13.6).
- Chu & Roy built audio-visual sentiment arcs for 1,326 Vimeo shorts; in a small follow-up
  experiment (visual arcs only, comments as the only metric), Icarus-like arcs and arcs with a large
  peak near the end predicted more comments. `[PRIMARY · Chu & Roy, ICDM 2017, arXiv 1712.02896]`
- **Do not rely on Kuleshov.** A blank face plus a context shot is weak and conditional:
  some category effect without matching eye-movement differences `[PRIMARY (abstract) · Barratt et
  al., *Perception* 45(8):847–874, 2016]`; a shift only for fear `[PRIMARY (abstract) · Calbi et
  al., *Frontiers in Psychology*, 2017]`; no effect at all for first-time film viewers
  `[SECONDARY · Ildirar & Ewing, *Projections* 12(1), 2018]`. The honest synthesis is
  `editing-storytelling.md` §2.1. Give the face a slight, readable expression.

⚡ **One release per piece, after the climax's action has landed — quiet, and held.** Tight (MCU/CU)
if the face carries it; a body with contact if the frame is wider (catalogue §13.5a). Reisz's example is a realisation played
in a very big close-up in silence so the pause lets it register `[PRIMARY · Reisz, *The Technique of
Film Editing*, 1966 printing, pp. 95–100]`.

### 4.5 Cut on the look, and enter on the voice

- A glance off-screen sets up an expectation that the cut satisfies by showing the target where the
  look points. Viewers begin moving to the next speaker's expected position ~**200 ms** after that
  speaker starts. When the subject leaves, eyes default back to the centre. `[PRIMARY · Smith, "The
  attentional theory of cinematic continuity", *Projections* 6(1):1–27, 2012]`
- Edit blindness mostly disappears **without audio**. `[PRIMARY (repository abstract) · Smith &
  Martin-Portugues Santacreu, *Media Psychology* 20(2), 2017]`

⚡ **The look begins in shot A; its target appears in shot B where the look pointed. Cut to a new
speaker on or just after the first syllable, or pre-lap the line (J-cut). Keep one continuous audio
bed across every AI join.** `[inference from live-action edit blindness]` Continuous sound is the
likeliest way to hide the visual mismatch between two generations.

## 5. Timing across the sequence

- **Length follows size.** Across ~31,000 shots, mean duration falls from ~8 s (extreme long shot)
  to ~2.5 s (extreme close-up); in 2000–2010 films, ~4.5 s to ~2.5 s. Classifying a face as positive
  or negative takes ~640–860 ms, slower for small faces (857 ms at extreme long shot, ~711–720 ms at
  MCU/CU), slower for neutral or negative faces, and slower still for distant faces against clutter. `[PRIMARY · Cutting &
  Armstrong, *Attention, Perception & Psychophysics* 78:891–901, 2016]`
- **A change needs time; a state does not.** Give a change ≥0.5 s of onset plus about a second to be
  read (Krumhuber & Kappas, plus the reading times above). A state-only listener can go at 3–4 s in
  dialogue (§3.2).
- **Inside the scene: the U.** Longer at the start and end, shorter in the middle (§2).
- **Across the film:** shot lengths fall from setup to complication, lengthen slightly in
  development, "fall precipitously" early in the climax (~75 %), and lengthen in the epilog; motion
  peaks in the climax; music rises across the film. `[PRIMARY · Cutting 2016]` Ours: climax at
  74–91 %, resolution after 92 % (`specifics-catalogue.md` §14.1).
- **Montage is the sequel, and sound glues it.** Swain's sequel is where summary compresses hours
  or weeks; Cutting finds sequences defined partly by shared sound coverage — music, voiceover or
  pervasive sound. Our montage runs have no sync speech and run at mostly 1.2 s or less a shot
  (`specifics-catalogue.md` §12.4, T3); whether a bed carried them was not measured.
- **Correlated runs.** Shot lengths became more correlated with their neighbours over 1935–2005
  `[PRIMARY (abstract) · Cutting, DeLong & Nothelfer, *Psychological Science* 21, 2010]`, a claim
  Salt disputes as a by-product of falling average shot length `[SECONDARY · Cinemetrics]`. Useful as
  "cut in runs, not at random"; not as a law.

The rhythm material that is not about chaining — tension and release, Pearlman, cutting to music —
stays in `editing-storytelling.md` §4.

## 6. Light and colour across the sequence

### 6.1 One key direction per scene

A face was matched faster and more accurately when the light direction stayed the same (877 vs
930 ms; 92 vs 85 %). `[PRIMARY (abstract) · Braje, Kersten, Tarr & Troje, *IOVS* 37(3), 1996]` A
bright/dim mismatch between learning a face and recognising it cost ~0.59 d′.
`[PRIMARY · Lim, Lee & Or, *Frontiers in Psychology* 13, 2022]` Faces lit from above are recognised
better than from below `[PRIMARY (abstract) · Hill & Bruce, 1995/1996]` and detected far more easily
`[PRIMARY · Palmer, Goddard & Clifford, *Cognition* 225, 2022]`.

`[implication, not tested on generated footage]` For a generated character, a key flip across a
cut **stacks on top of identity drift**: the studies above say a face is re-identified less reliably
when the light moved. Sora's guide asks for the same lighting logic
across clips that will be cut together, and names its failure: broad lighting notes give
inconsistent results. `[PRIMARY · OpenAI Cookbook, Sora 2 prompting guide, March 2026]`

⚡ **Fix the key side per scene (camera-left, camera-right, top, front) and change it only at a story
boundary.** Shot/reverse-shot: key each actor from the far side of the eyeline, so each lamp is one
character's key and the other's backlight `[TERTIARY · Oseman, neiloseman.com]`.

### 6.2 Cheat the close-up softer, keep the source

Our films: a CU is soft-lit and a WS flat in all five (`specifics-catalogue.md` §12.1). Alton relit
close-ups from scratch; Oseman's view is that modern audiences reject radical relighting, so keep the
source and soften it. `[SECONDARY · Oseman's review of Alton, *Painting with Light*]` With a catchlight, viewers' attention
reached the eyes **49 % faster**, and 58 % found emotions easy to read against 36 % without.
`[PRIMARY (abstract) · Swenberg, Thedeby, Berg & Jonsson, *PACA* 16(3):389–399, 2022]` That is
live-action film; whether it transfers to a rendered eye is still open (`emotional-journey.md` §9).

⚡ **In the emotional close-up, name a real source the eyes can reflect** — the window, the screen,
the lamp. In UGC the word *eyelight* is withheld (`photorealism-physics.md` §8.1); the source is
not.

### 6.3 Hiding the face is a single beat

Under-lighting disrupts how faces are read `[PRIMARY (abstract) · Johnston, Hill & Carman,
*Perception* 21, 1992]`. In the one EEG study, underlight, silhouette and toplight produced a stronger
early emotional response than 45° light (toplight in the late window only); 90° side light did not
differ (N = 9, a still photo, no context). `[PRIMARY · Huttunen, *Frontiers in Neuroscience*, 2025]` Two of our films put a screen
under-light on the moment of truth (`specifics-catalogue.md` §11.4).

⚡ **Under-light, top-light or silhouette once, on the reveal.** Under-light and silhouette also hide
the identity the model is already struggling to hold, so never for a run of shots on a recurring
character. Top-light is different: overhead light made faces *easier* to detect (§6.1), so its case
for rationing is the raised reaction, not identity. (Whether Palmer's "overhead" and Huttunen's
"toplight" are the same set-up is unclear.)

### 6.4 Colour is the chapter code, luminance is the arc

- Colour and luminance contribute to where viewers put event boundaries (§2); scene-detection
  algorithms rely on colour holding across a scene `[PRIMARY (abstract) · Rasheed & Shah, CVPR 2003]`;
  *Game of Thrones* flips location palettes at storyline boundaries `[PRIMARY · Hohman et al.,
  VIS4DH 2017]`. Ours: chapters of 6–54 shots, one palette each, changing at a story boundary
  (`specifics-catalogue.md` §12.2).
- **Saturation and brightness are the levers.** Saturation drove arousal (ηp² = .69), brightness
  raised arousal and pleasantness; hue moved arousal (red above green above blue) but had no reliable
  effect on pleasantness.
  `[PRIMARY · Wilms & Oberfeld, *Psychological Research* 82:896–914, 2018]` Colour versus black and
  white moved self-reports but no physiology `[PRIMARY (abstract) · Detenber et al., *Media
  Psychology* 2(4), 2000]` and mattered less than sound `[PRIMARY (abstract) · İyilikci et al.,
  *Current Psychology* 43, 2023]`.
- **Low-key is not reliably "negative".** It raised mystery and suspense and, unexpectedly, some
  positive responses `[PRIMARY (abstract) · Poland, MA thesis, Cleveland State, 2015]`; in drama and
  romance it went with slightly higher arousal and slightly more negative feeling, in action the
  reverse, and empathy fell as low-key lighting rose `[PRIMARY · Huang, MSc thesis, Tilburg, 2018]`. The two disagree; genre decides.
- **The luminance arc.** Films darken across the development to a darkest point at ~¾ of the
  runtime and brighten through the climax (complication vs development d = 2.90). `[PRIMARY ·
  Cutting 2016]`

⚡ **One colour family per scene; at most two or three families in a 30–60 s piece; change family only at a
story boundary.** Use warm/cool as the code for time, place and chapter, and saturation and
brightness for the feeling. Darken towards the low point, brighten for the resolution or the CTA.

## 7. Composition across the cut

- **Cut to where the eye already is.** The first eye movements go to the screen centre, to motion
  and to people `[PRIMARY (abstract) · Smith & Mital, *Journal of Vision* 13(8), 2013]`; the centre
  bias in video follows where photographers put subjects `[PRIMARY (abstract) · Tseng et al., *Journal
  of Vision* 9(7), 2009]`; most viewers look at the same thing at the same time, and are only
  weakly moved by what they understand of the story `[PRIMARY (abstract) · Loschky et al., *PLoS ONE* 10(11), 2015]`. Centre
  the incoming subject, or put it where the outgoing look or motion points (§4.5).
- **Look room is measured.** Viewers place an averted face looking into the frame; a face looking
  at camera shows no bias. `[PRIMARY · Chen, Colombatto & Scholl, *Cognition* 176, 2018, lab summary]`
  Short-siding goes against that preference, which is the likely reason it reads as unease
  `[TERTIARY · Haggstrom, reel3.com, 2013]`. Use it sparingly.
- **Thirds barely matter; centre and symmetry do.** `[PRIMARY · Amirshahi et al., *Art & Perception*
  2, 2014]` · `[SECONDARY · Palmer Lab summary of Palmer, Gardner & Wickens 2008]` ·
  `[PRIMARY (abstract) · Jacobsen & Höfel, *Perceptual & Motor Skills* 95, 2002]`
- **Converging lines pull the eye to the vanishing point** (search 1.34 vs 1.96 s). `[PRIMARY
  (abstract) · Borji, Feng & Lu, *Journal of Vision* 16(14), 2016]` Put the next shot's subject there.
- **Shallow focus steers the eye** `[PRIMARY (abstract) · Zhang et al., 2019; PRIMARY (project page) ·
  Hata, Koike & Sato, AVI 2016]`, and blur is ignored rather than avoided `[SECONDARY · K-State Visual
  Cognition Lab summary of Loschky et al.]`. It is an attention tool, not an emotion one.
- **Match screen positions in reverses** (Smith 2012; `editing-storytelling.md` §1.3).
- **Vertical** ads on mobile were processed more fluently and raised engagement. `[PRIMARY
  (abstract) · Mulier, Slabbinck & Vermeir, *Journal of Interactive Marketing* 55, 2021]` No
  published shot-size grammar for 9:16 was found `[gap]`; the vertical canvas rules are
  `cinematography-craft.md` §5.10.

## 8. ⚡ The combination table — the baseline for every channel, per beat, and where to break it

This is the answer to "how do I combine them". Each row is a beat from §2. Read across: the shot for
that beat is the whole row, not one column. Where a cell cites our five films it is measured; the
rest comes from the sections above.

⛔ **This table is the affinity baseline.** A shotlist that follows every row exactly is the flat
version of the piece. The contrast plan (§2b) decides which rows to break and where, and the chain
records each break.

| Beat | Size | Height · tilt | Camera (baseline) | Light | Colour | Performance (0–3) | Duration | Cut in on |
|---|---|---|---|---|---|---|---|---|
| **Orient** — a new place, the goal | WS/EWS, or open close and reveal later (§2) | eye or hip · level | held, to be searched — or a reveal move (rise, tilt, pull) that discovers the place | set the scene's key side; wides flat or even (catalogue §12.1) | set the scene's family | body only: a goal as one photographable act (Swain) | the longest shot of the scene | the scene boundary — the size change is the cue |
| **Re-orient** — a place already seen | MWS/WS, closer than the first time | as the first time | held | same key | same family | — | shorter than the orient, longer than average | a return |
| **Exchange** — dialogue | matched singles or OTS, climbing towards the peak (§3.2) | matched height and tilt both sides | held matched singles; a push toward the peak is the cliché — earn it | key from the far side of each eyeline | same | 1, rising one step at a time (§4.2) | Hollywood shot/reverse-shot averages ~5.6 s (§3.2); speaking shots in our films are more often over 5 s and never 1.2 s or shorter (catalogue §12.1) | the new speaker's first syllable, or a J-cut |
| **Stimulus / disaster** — the reveal | insert or POV | the looker's eye height; top-down for an object on a table | held on the object, or a rack from the looker to it | same key; a single source on the object (catalogue §12.1) | same family, or the first shot of the new one | none — the object carries it (catalogue §14.3) | short — inserts are short in two of our four films that have enough; not a rule (catalogue §12.1) | the look (§4.5) — or one shot after the reaction, when the cause is withheld (§4.1) |
| **Reaction** — the feeling | MCU/CU, tighter than the shot before if the intensity jumps (catalogue §15.2) | eye · level | held: the face is the motion | same key, softer, a source in the eyes (§6.2) | same | +1, or +2 with the tighter frame; late in the shot (§4.3) | a change shot runs 1.15–1.89× the film's typical shot (catalogue §13.4); a state-only listener 3–4 s (§3.2) — `[inference]` the difference is change vs state | the stimulus |
| **Dilemma** — the hold | CU or MCU, still | eye · level | held | same | same | hold the new state; gaze off to the target or down | long enough for one visible thought: a look away and back | the end of the reaction |
| **Decision** — the act | MS/WS: the body carries it | eye or hip · level | follows the act: a pan or track with it | same | same, or the family change if this is the boundary | a body bundle (`acting-for-the-model.md` §4) | normal | the action (match on action) |
| **Montage / sequel** — time passing | CU and inserts (process) or MS/WS (action) (catalogue §12.4) | varied, geography | varied, with motion vectors matched across the cuts (`cinematography-craft.md` §3.8) | one source per insert | **one** family for the whole run | 0–1 | mostly 1.2 s or less, even (catalogue §12.4, T3) | the music bed; no sync speech |
| **Climax** (~75 %+) | the most varied; motion carries it | varied | moving: follow, track, whip joins — the movement peak | darkest point just before, then brightening (§6.4) | the high-contrast family | never 3 in our films; the peak run usually came **before** (catalogue §13.6) | the shortest shots of the piece | action and motion |
| **Release** — once, after the climax lands | MCU/CU if the face carries it; MS/WS with body contact otherwise (catalogue §13.5a) — framed tighter than the shot before (catalogue §15.2) | eye · level | held, or the piece's one approach move (§2b) | softest of the piece | the piece's warmest or most saturated | 3, restrained before it; quiet (§4.4) | held | a silence |
| **Resolution / CTA** | widen: the arc releases (§2) | eye · level; product at eye level for a motivated viewer | settle: the camera comes to rest on the widened frame, the opposite of a moving climax. A pull-out or rise is one way to widen and the stock one: as this cell's only option it closed 13 of 20 Kimi ads `[measured 2026-10-04 · lab-00005 v2.14 · n=20]` | brighter than the climax | resolve to the opening family, or the brand's | the release if it is not yet spent; otherwise 1, settled (catalogue §13.6) | longer again: the epilog | the payoff object, changed by the story (catalogue §14.3) |

**Why these combinations and not others:** each column's rule is in §3–§7, and the rows only put
them in one place. And why they are not enough: every row is the calm version of its beat, so a
piece built only from rows has no peak in its pictures (§2b). The two things the table encodes that no single column does: **intensity and
frame move together** (a jump of two gets a frame jump the same way), and **key and colour change
together, at a boundary, and nowhere else**.

## 9. Translating the chain into prompts

**Every generation is stateless.** Each clip re-lights and re-casts itself, so the chain exists only
if each prompt restates it. `[TERTIARY · Houbre, HackerNoon, 2026-07-23: a written lighting plan plus
close-ups conditioned on the approved wide]`

1. **Write the chain before any prompt**, as the *Sequence chain* table in the shotlist
   (`assets/shotlist-template.md`), and run `python3 scripts/sequence_lint.py <SHOTLIST.md>`.
2. **Every prompt carries its row, split the way the house format splits.** The **frame** prompt
   carries the look: the key side and quality ("soft key from a camera-left window"), the colour
   family as 3–5 palette anchors (Sora), and camera **height and tilt as two values**. The **clip**
   prompt carries only motion, camera and performance (`ai-generation.md` Step 2), so its row is the
   entering state, the intensity, the target of the gaze, the one change, and the Move with its job
   in `[CAMERA]` ("track with her as she crosses: follow", or "locked: the frame is to be searched"). Its light comes from
   the approved start frame and is never re-described.
3. **Condition close-ups on the approved wide** — first frame, reference image or element reference
   — so the source and the face come from the same picture. Veo 3.1 documents first/last frame,
   reference images and timestamped multi-shot prompts `[PRIMARY · Google Cloud blog, 2025-10-16]`;
   Kling 3.0's Custom Multi-Shot sets length, framing, viewpoint and movement per shot `[PRIMARY* ·
   Kling guide, 2026-08-07]`, and a host reports up to six shots per output with shot/reverse-shot
   dialogue `[SECONDARY · fal.ai, 2026-02]`.
4. **One camera move, one subject action, one lighting recipe per shot.** Sora: "Each shot should
   have one clear camera move and one clear subject action." `[PRIMARY · Sora 2 guide]`
5. **Term plus description.** Seedance: convert specialist terms into "term + descriptive
   explanation" and label every shot `[PRIMARY · Seedance 2.5 guide]`. "Low angle, camera at knee
   height tilted up 20°" beats either half.
6. **Phrase positively.** Runway: negative phrasing may produce the opposite. `[PRIMARY · Runway
   Gen-4 guide, Help Center]` The vendor-by-vendor prompt mechanics are `prompting-craft.md`.
7. **Multi-shot generation does not remove the table.** A model that cuts inside one generation still
   needs to be told what the second shot inherits from the first. The planned form (`multishot.md`)
   writes each row as a stage, with its `End state:` as what the next stage inherits and a
   `[CONSISTENCY]` block for what every stage keeps. §2c item 8 holds inside the take as well: whips,
   dissolves, match cuts and graphic wipes together are 3 % of real ad cuts, so a multi-shot clip is not a licence for
   transitions. A cut made inside the take is final, so its type is chosen here, in the table, not
   found in the edit.
8. **Enter on the action, not before it.** 45 % of real ad cuts land on an action already under way
   (§2c). A generated clip ramps up from a still start frame, so either write the start state in motion
   ("mid-stride", "the pour already falling") or generate a 1 s head and set the cut after the ramp.

## 10. Failure modes, named

| Name | Signature | Cause | Fix |
|---|---|---|---|
| **The jump** | a performer goes from 1 to 3 on a cut and it reads as a glitch | intensity jumped with no frame move and no stimulus between | climb one step at a time, or cut tighter on the jump (§4.2) |
| **The orphan reaction** | a strong face with nothing to react to | the stimulus is missing, or withheld and never shown | stimulus first, on screen or on the track — or the cause in the very next shot, as a reveal (§4.1) |
| **The stranded look** | a character looks off-screen and the next shot is elsewhere | the look's target never appears | cut to the target, placed where the look points (§4.5) |
| **The unpaired angle** | one low shot in an eye-level scene, read as a mistake | angle used as decoration | give it a job (POV, geography) or its partner (§3.3) |
| **The trust tilt** | a to-camera speaker feels off | off-eye angle on direct address | eye level, level tilt (§3.3) |
| **The relight** | the same face looks like a different person after the cut | the key flipped inside the scene | one key side per scene (§6.1) |
| **The confetti palette** | the piece feels like several ads | colour family changes without a story boundary | one family per scene (§6.4) |
| **The routine** | every scene goes wide–medium–close | Mascelli's monotony | mix progressive, contrasting and repeated (§3.1) |
| **The blank close-up** | a CU that adds nothing | a neutral face framed tight | put the close-up on the change (§3.5) |
| **The aftermath shot** | a lingering shot after every turn drags | the hold was put after the turn | give the turn shot the extra second instead (§4.3) |
| **The frozen camera** | every shot held; the ad reads as a slideshow | a corrective ("hold the frame") applied as a default | a camera plan with moves that have jobs (§2b; `cinematography-craft.md` §3.8) |
| **By the book** | every rule followed, nothing peaks | all affinity, no contrast plan, no break | one or two components progressing to the climax, and one deliberate break (§2b) |
| **The silent join** | two generations cut together and the seam shows | audio cut with the picture | one continuous bed across the join (§4.5) |

## 11. Verification

1. `python3 scripts/sequence_lint.py <SHOTLIST.md>` — the chain table. It fails on a key side that
   changes inside a scene, on direct address from below and on a missing contrast plan, and warns on
   the patterns in §10 that need a human decision: the frozen camera, the push-in monoculture, the
   affinity run, the piece with no deliberate break, and a contrast plan the rows do not deliver.
2. For an ad: the revise loop of §2c item 14 — the director's review, then
   `python3 scripts/sequence_lint.py <SHOTLIST.md> --baseline`, at most three rounds.
3. `python3 scripts/film_db.py chain` — the reference distribution from five films. A plan far outside
   it is not wrong, but it should be deliberate.
4. **Contact sheets of the assembled sequence**, and `contact_sheet.py --clip <clip> --perf` strips for every
   performer clip (`acting-for-the-model.md` §9), read in order: intensity by shot, key side by
   shot, colour by shot.
5. ⛔ **Do not trust a vision model's angle or size label.** On ShotBench, GPT-4o named the angle
   correctly 58.2 % of the time and the size 69.3 %, and called a medium shot a medium close-up
   36.2 % of the time; the best model averaged under 60 % across eight dimensions, lighting
   included. `[PRIMARY* · Liu et al., ShotBench, arXiv:2506.21356, 2025]` Check height by the
   horizon (§3.4) and size by eye.

## 12. What this file cannot tell you

- **Most angle and close-up experiments used stills or short clips**, and several are known only
  from abstracts or fetch-tool summaries (`PRIMARY*`). The directions that hold are eye level trusted
  most on direct address, a low angle reading taller and stronger in story context, and close-ups
  helping on expressive faces; the rest are conditional (§1.1). None of the effect sizes is portable.
- **Cutting's corpora are Hollywood features.** A 30–60 s ad as "one scene" is this file's mapping,
  not a finding.
- **No study of any named lighting pattern was found**, and none that varies white balance in real
  footage.
- **No study measures intensity matching across coverage.** §4.2 rests on our five films and on
  craft testimony.
- **Our five films are festival AI shorts, not ads**, read by one reader (`specifics-catalogue.md`
  §13.8 and §15.6).
- **No shot grammar for 9:16 was found.** The rules here were measured on 16:9 and 2.39:1.
- **The vendor guidance is dated.** Each vendor line is as of its checked date; the roster moves
  faster than this file.
