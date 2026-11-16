# Acting for the model — the acting tradition, translated into a performance a video model can render

**When to read this:** writing a performance card or the `[PERFORMANCE]` block of a clip prompt;
a performer clip came back posed, vacant, twitchy or over the top; someone asks for "more
expressive" acting; you need to turn a director's note ("reassure him", "she's devastated") into
something a model can put on screen.

**What this file owns:** which parts of a century of actor training a model can use, the evidence
on what makes screen emotion read, the vendors' current guidance, and the **performance card v2**
that puts all three into a prompt. It does not repeat what is already owned elsewhere: the vacant
face and its four causes (`emotional-journey.md` §4), the circumstance as the instruction
(`emotional-journey.md` §5), blink, gaze and smile timings (`timing-and-performance.md` §2), and how
a performance chains across shots (`sequence-grammar.md` §4). The measured performances of five
festival AI shorts are `specifics-catalogue.md` §13, §13.5a and §15.

**Tiers** follow `research-quality.md`; everything was checked **2026-09-30**. Several of the craft
books (Weston, Caine, Barr, Tucker, Donnellan) were reached only through interviews, reviews or
quotation, and are tagged that way. Quotes are ≤15 words, one per source.

**⛔ The one thing to carry out of this file.** The model has no inner life, so the half of acting
that works through the actor's inner life is closed to it. The other half works through the
**outside** — the facts of the situation, the physical task, the person played towards, the thing
reacted to, the obstacle. Every vendor's worked examples pair whatever emotion word they use with a
physical beat on that outside (§6), though their written rules disagree about the labels — that
convergence is this file's synthesis, not a vendor's claim. **Direct the outside.**

---

## 1. The tradition, split in two

| Tool | Source | The model can use it? | As prompt text |
|---|---|---|---|
| **Task / objective** — acting is doing, "acting is action - mental and physical" | Stanislavski, trans. Benedetti 2008, p. 40 `[SECONDARY · quoted on Wikipedia "Action (theatre)"]` | ❌ the want itself; ✅ once reduced to "a single, photographable act" (Swain, `sequence-grammar.md` §2) | "she is trying to get the key back" → "she reaches for the key in his hand" |
| **Given circumstances** — story, events, period, time, place | Stanislavski, *An Actor Prepares* (Hapgood 1936), p. 54 `[SECONDARY · excerpt]` | ✅ | the environment and the object's state (`emotional-journey.md` §5) |
| **Result direction is the error**; the playable alternatives are "the verbs, the facts or emotional history, imagery and physical life and event" | Weston, *Directing Actors* (1996) `[PRIMARY · Weston interview transcript, Film Courage, 2022-06-15]` — a book written for film and TV directors. In the same interview she partly retracts the book's opening list of ten result-direction don'ts, which she says was made provocative on purpose and backfired a little | ✅ facts, physical life, event · 🟡 verbs, once translated · ❌ imagery, emotional history | the event and the physical business, in the clip |
| **Actioning** — each thought gets a transitive verb done to the other person (*reassures*, *steadies*) | Stafford-Clark's method `[PRIMARY · Nick Hern Books excerpt]`; Caldarone & Lloyd-Williams, *Actions: The Actors' Thesaurus* (2004) | 🟡 the verb is an intention; the model needs the behaviour behind it | §8: "reassures him" → leans in, lowers her voice, touches his forearm |
| **The target** — played "outside, at a measurable distance", always active, always changing | Donnellan, *The Actor and the Target* (2002/2005) `[SECONDARY · StageMilk review quoting the book]` | ✅ | **TARGET:** who or what, and where in the frame |
| **The reality of doing; response to the partner** — "The foundation of acting is the reality of doing." | Meisner & Longwell 1987, p. 16 `[SECONDARY · quoted on barrypopik.com]` | ✅ | **STIMULUS:** the thing reacted to, written in |
| **The nine questions**, among them "What's in my way?"; object exercises; endowment | Hagen, *Respect for Acting* (1973) `[SECONDARY · Backstage; TheatreFolk; BYU TEDB, pp. 81–86]` | ✅ obstacle, object work · ❌ substitution | the obstacle is visible as **struggle**: the stuck lid, the held-back tears |
| **Psychological Gesture** — the core drive as one whole-body gesture, then suppressed | Michael Chekhov, *To the Actor* (1953) `[SECONDARY · Wikipedia]` | 🟡 the external stage only | **BODY:** one whole-body quality (§4) |
| **Practical Aesthetics** — an action is physically doable at once, specific, tested in the other person, and not dependent on an emotion | Bruder et al., *A Practical Handbook for the Actor* (1986) `[TERTIARY · coaching-site summary; wording UNVERIFIED]` | ✅ as a test | if the line cannot be *done*, it is not a direction |
| Emotional memory, substitution, the internalised gesture | Stanislavski; Hagen; Chekhov | ❌ | nothing — there is no one to remember |

Carrying theatre theory into screen work is itself defended in the scholarship: Baron & Carnicke
argue theatre theory illuminates the screen actor's craft. `[SECONDARY · publisher description,
*Reframing Screen Performance*, U. Michigan Press 2008]`

## 2. The Leandro contradiction, settled for this medium

`emotional-journey.md` §4.1 records that everyone agrees the emotion word is the wrong instruction,
and that they disagree on the replacement. Leandro rejects objective and action-verb coaching as a
theatre import that misreads a film set; the orthodoxy teaches the objective. That section used to
say the skill could not settle it, because only Leandro's side was in the corpus. The other side is
now in (§1), and it splits the question cleanly:

- **The internal half** — the objective as a felt want, the bare transitive verb, substitution, the
  internalised gesture — is exactly what a model cannot use. **Leandro's rejection holds here**, and
  for a stronger reason than his: not that it misreads a set, but that there is nobody to receive it.
- **The external half** — facts and event (Weston), physical life and objects (Weston, Hagen), the
  outside target (Donnellan), the stimulus and the response (Meisner), the obstacle (Hagen), the
  whole-body gesture made visible (Chekhov) — is renderable, and it is what every vendor's worked
  examples contain, whatever their rules say about emotion labels (§6). **Leandro's rejection does
  not reach it.**

This is a synthesis, not a source: nobody has tested it, and no controlled study compares audiences'
ratings of Method, Meisner or actioning performances `[gap]`. What it buys is a rule a check can be
written against: **every line of a performance card must name something the camera can see.**

## 3. Scale — the shot size decides which channel carries the feeling

| Size | What the viewer can read | Direct it through | Evidence |
|---|---|---|---|
| **EWS / WS** | gait, weight, posture, contact between bodies; a small face is read slowly (857 ms against ~711–720 ms at MCU/CU) | **BODY** only: a Laban bundle (§4), an action with contact | Cutting & Armstrong 2016 `[PRIMARY]`; Tucker, *Secrets of Screen Acting*, long shot needs larger, defined gesture `[TERTIARY]`; Kling: full-body shots show movement mechanics `[PRIMARY · Kling blog, 2026-07-03]` |
| **MS / MWS** | shoulders, hands, weight, and the face coarsely | **BODY** first, then one face change | `direction.md` §1 (body before face); Aviezer: bodies carry valence at peak intensity (`emotional-journey.md` §4.2) |
| **MCU / CU** | eyes, gaze shifts, the mouth; *micro-tension* | **GAZE** and a partial **FACE**; fewer blinks, never none | Tucker `[TERTIARY]`; Caine (below); Vertex and Sora: close-ups emphasise emotion `[PRIMARY]` |
| **XCU** | one feature | one change in one feature, and the stimulus off-frame | `specifics-catalogue.md` §15.2 (`F5#167`) |

**Our films draw the same line.** 12 of the 18 peak shots carry the peak in the body or in touch,
and all 6 face-only peaks are at MCU or CU (`specifics-catalogue.md` §13.5a); high intensity goes to
face sizes in every film (§13.5).

**Caine, on the close-up.** In a close-up the eye is huge on screen, so do less as the camera comes
closer; listen seriously; look at one of your partner's eyes rather than flicking between them; and
"Blinking makes your character seem weak." `[SECONDARY · Caine, *Acting in Film*, quoted on
sheilaomalley.com]` The data half-agrees: higher blink rates were rated more nervous and careless
`[PRIMARY (abstract) · Omori & Miyata, *Social Behavior and Personality* 29(2), 2001]`, which is not
evidence that zero blinks read as strong. **For a model: fewer, deliberate blinks, never zero.** A
5-second clip needs at least one blink and a talking one usually two (`timing-and-performance.md`
§2.1), and "no blinks" is on the uncanny list (§4 there).

**Does the camera see you think?** Barr says thought registers on camera `[TERTIARY · Goodreads
quotes, *Acting for the Camera*]`; Adler calls it a myth, because the camera records movement,
shape, light and colour `[TERTIARY · Backstage, 2015]`. For a model Adler wins by default: there is
no thought to register, so **"thinking" is written as behaviour** — the eyes leave the target, hold,
and come back.

## 4. The body — Laban qualities, written as bundles

Laban's effort qualities (weight, time, space, flow) are the vocabulary every study below uses for how a body
moves. What the evidence says about using them:

- **Movers feel what they move** (Shafir, Tsachor & Welch 2016 — what performers *felt*): anger was
  predicted by strong, sudden, direct and advancing; fear by retreating, condensing, binding, moving
  back and enclosing; happiness by jumping, rhythmic re-initiation, spreading, free, light, up and
  rising; sadness by passive weight, arms to the upper body, sinking and the head down. Sustained
  time was a strong *negative* predictor of anger. `[PRIMARY · *Frontiers in Psychology* 6:2030,
  PMC full text]`
- **Observers read it, with no emotion asked for** (Melzer, Shafir & Tsachor 2019): Laban-trained
  movers performed the elements without being told to portray anything, and all four emotions were
  recognised above chance. `[PRIMARY · *Frontiers in Psychology* 10:1389, PMC full text]`
- **Single qualities are read unreliably.** Observers could not reliably perceive isolated effort
  elements — light was worst — and elements co-occur, so write them as bundles (a recommendation
  drawn from the result, not itself tested). `[PRIMARY (abstract) · Kim,
  Neff & Lee, *ACM TAP* 19(1), 2022]`
- **Speed is arousal, not valence.** Arm-movement speed carried activation; pleasantness was in the
  phase relations between limbs. `[PRIMARY (abstract) · Pollick et al., *Cognition* 82, 2001]` Gait
  was fastest for joy and anger, slowest for sadness, with neck and chest flexion marking sadness.
  `[PRIMARY (abstract) · Gross, Crane & Fredrickson, *Human Movement Science* 31, 2012]`

| Feeling | The bundle, in plain words | What raised recognition most (Melzer 2019) | Watch for |
|---|---|---|---|
| **Anger** | strong, sudden, direct, advancing: "steps in fast, straight at him, weight forward" | sudden ~9.4×, strong ~3.7×, advance ~3.2× | slow and sustained works *against* anger |
| **Sadness** | heavy, sinking, head dropping, arms drawn in: "her weight sinks, head drops, arms fold in" | head drop ~7.6×, sink ~2.5× | — |
| **Fear** | retreating, twisting back, condensing, bound: "pulls back, turns her shoulder away, arms tight to her body" | twist-and-back ~3×, retreat ~2.7× | fear was often **confused with anger**; binding went with felt fear but recognised anger |
| **Joy** | rhythmic, spreading, light, rising: "bounces on her toes, arms opening, rising" | rhythmicity ~35×, spreading ~23× | free and light went with sadness in another coding study (Crane & Gross); keep the rhythm |

EMOTE, the SIGGRAPH system that applied Laban efforts to animation, is often cited as showing that
efforts change perceived emotion. It did not test that: its evaluation checked only whether movement
analysts could identify the intended effort (53–77 % correct), and emotion was listed as future work.
`[PRIMARY · Chi, Costa, Zhao & Badler, SIGGRAPH 2000]`

⚡ **Write the BODY line as three or four plain-language qualities that belong to one bundle, never
as Laban terms.** Kling's own example is the same move: a *slow, deliberate wave* and a *frantic,
rapid wave* are two different gestures `[PRIMARY · Kling blog, 2026-07-03]`.

## 5. The face — partial, carried by the situation, and the struggle rather than the peak

- **Real screen actors rarely make the full expression.** In Hollywood films, actors judged happy
  smiled 97 % of the time; for surprise, fear, anger, disgust and sadness the full predicted facial
  pattern appeared in "0 to 31% of cases". Actors used partial expressions. `[SECONDARY · Carroll &
  Russell, *JPSP* 72(1), 1997, abstract via a bibliographic index]`
- **The situation carries the meaning.** 155 professional actors posing 604 rich scenarios produced
  variable, not stereotyped faces; specificity *fell* in high-intensity scenarios, and observers'
  readings were dominated by the scenario. `[PRIMARY · Le Mau et al., *Nature Communications*
  12:5037, 2021, PMC full text]`
- **Posed reads as accurate and intense but less natural.** Across 14 databases. `[PRIMARY
  (abstract) · Krumhuber et al., *Behavior Research Methods* 53, 2021]` The classic posed sets are
  "typically perceived as not showing genuine emotion". `[PRIMARY (abstract) · Dawel et al., *BRM*
  49, 2017]`
- **Audiences cannot tell felt from technical acting.** Viewers named the emotion accurately but
  could not tell whether it was felt or produced technically. `[PRIMARY (abstract) · Gosselin,
  Kirouac & Doré, *JPSP* 68, 1995]` Even on stage, actors' felt emotions were task emotions —
  challenge, tension — "barely, if at all" connected to the character. `[PRIMARY · Konijn, *Acting
  Emotions*, Amsterdam UP 2000, §8.3, open access]` **Performance is behaviour for humans too.**
- **Direct the struggle, not the tears.** Barr: "it is your struggle to keep from crying that
  makes an audience feel like crying" `[TERTIARY · Goodreads quote, *Acting for the Camera*]`.
  Hagen's obstacle (§1) is the same idea: what is visible is the effort against something.
- **The model over-drives.** Seedance's guide says it outright — "The model may overreact to strong
  emotional cues" — and names the artefact (glowing pupils) and the fix: replace *extremely
  shocked* with neutral wording such as *amazed*. `[PRIMARY · BytePlus ModelArk, Seedance 2.5
  prompt guide, updated 2026-09-28]` That is the same over-intensity the skill documents from Kramer
  (`emotional-journey.md` §4.4).
- **Ours.** 1.9 % of 934 performer shots are a full release; the modal performance is restrained,
  eyes and mouth only (`specifics-catalogue.md` §13.1).

⚡ **Write FACE as what moves and what stays still, and never with a superlative.** "Mouth tightens,
brows stay still" is a direction; *extremely devastated* is an invitation to overreact.

## 6. What the vendors say, 2025–2026

| Vendor | What the guide says about performance | Tier |
|---|---|---|
| **OpenAI Sora 2** (Cookbook, March 2026) | "Actions work best when described in beats or counts"; one clear subject action per shot; verbs and nouns with visible results. Its own examples still add emotion glosses (*relief and pride*) | PRIMARY |
| **Google Veo 3.1** (blog, 2025-10-16) | cinematography + subject + action + context + style; uses labels such as "Emotion: Wonder and reverence." next to the action | PRIMARY |
| **Google Vertex Veo guide** (2026-09-28) | lists emotional expressions as actions; its example ties a reaction to a stimulus: eyes "widen in a flash of alarm as a floorboard creaks off-screen" | PRIMARY |
| **Kling** (blog, 2026-07-03; 3.0 guide 2026-02-06) | describe what the viewer can see; "describe the gesture, facial expression, and delivery together"; per-line tone tags (from the 3.0 guide) | PRIMARY (blog) · PRIMARY* (3.0 guide, fetch summary) |
| **fal** (Kling 3.0 host, 2026-02-05) | "Describe the action first, then the dialogue."; per-character voice and emotion labels | SECONDARY |
| **Seedance 2.5** (BytePlus, 2026-09-28) | descriptive sentences, fewer idioms; a per-line format with the emotion in brackets; tone notes attached to single words can trigger unwanted subtitles; overreaction to strong cues (§5) | PRIMARY |
| **Runway Gen-4 / 4.5** | warns against prompts that "describe the idea or feeling behind a motion" instead of the movement — its good example is a woman who *smiles and waves*, its bad one a subject who *embodies the essence of joyful greeting*; negative phrasing unsupported | PRIMARY |
| **Higgsfield** | a promotional page naming intents ("a subtle, knowing smile"); no method | PRIMARY, marketing |

**Where they disagree:** Runway, and Sora's own rules, say physical over feeling; Veo, Kling and
Seedance use emotion labels openly. **Where they agree:** every vendor's worked examples pair a label
with a physical beat, and none relies on a bare emotion word. Seedance tones intensity down; Kling's
examples turn it up (*voice cracking*).

⚡ **The house rule that satisfies all of them:** the physical beat first; an emotion word, if any,
only after it as a gloss, and never as a superlative. The existing lint already warns on an emotion
with no mechanism (`prompt_lint.py`, `script-craft.md` §6b).

A claim that circulates and is false: *"the Sora 2 guide says don't name emotions."* A fetch-tool
summary said so; the guide does not, and its own examples name them. The same summariser also blurred
Runway's wording on the first pass; both were re-read against the raw page.

## 7. ⚡ The performance card v2

The card in `direction.md` §1 gains three lines and one rule. It still becomes the `[PERFORMANCE]`
block of the clip prompt (`ai-generation.md` Step 2).

```
[PERFORMANCE]
STATE:    <before → after, read off the emotional map — never a bare emotion word in the prompt>
STIMULUS: <what they react to, outside them, and when: "the phone buzzes face-down at 1 s" · "his line" · "none — she starts it">
TARGET:   <who or what they play towards, and where: "the man at the door, frame left" · "the lens">
BEAT:     <the before, held>, then <one change> — in the second half of the clip
BODY:     <MS or wider: one bundle in plain words — "weight sinks, head drops, arms fold in">
FACE:     <what moves and what stays still — "mouth tightens, brows stay still">
GAZE:     <where the eyes are, and when they move — "on the man; drops to the envelope on the change">
AFTER:    <the one silent beat it ends on>
```

**Why each new line exists:**

- **STIMULUS** — a reaction without its cause reads as random, and Swain's rule is that the stimulus
  comes first (`sequence-grammar.md` §4.1). Meisner's reality of doing and Vertex's floorboard
  example are the same instruction. On a reaction clip it is not optional; "none — she starts it" is
  a valid answer, and writing it forces the question.
- **TARGET** — Donnellan's point in one field. A gaze with no target drifts, and a drifting gaze is
  what "vacant" looks like. GAZE says where the eyes are; TARGET says what the performance is aimed
  at, which is also what the next shot has to show (`sequence-grammar.md` §4.5).
- **BODY** — the wide shot has no other channel (§3), and the peak in a wide frame is always a body
  or a touch in our films (`specifics-catalogue.md` §13.5a).
- **BEAT as "<before, held>, then <one change>"** — a change inside a shot lands late 112 times
  against 17 early (`specifics-catalogue.md` §13.3), one change per clip (`direction.md` §1), and the time for the
  change belongs inside this shot (`sequence-grammar.md` §4.3).

**Rules the lint checks** (`prompt_lint.py`, warnings — a human decides):

- a **reaction** clip with no `STIMULUS:`;
- a `GAZE:` that points nowhere ("into the distance", "off-screen", "away") with no `TARGET:`;
- an **MS or wider** clip (read from `[CAMERA]` or `[MOTION]`) with no `BODY:`;
- a `BEAT:` with two changes (two "then"s);
- an intensity superlative anywhere in `[PERFORMANCE]` ("extremely", "hysterical", "uncontrollably"…);
- a gaze **on the lens** with the camera at a low or high angle — direct address from below was
  trusted less in the one study that measured it; from above the drop was not significant
  (`sequence-grammar.md` §3.3).

## 7b. ⚡ The movement persona — the person every intent starts from

Author, 2026-10-26: *"Maybe when a person or avatar is used, the skill should build a persona like in UX
or marketing, so the animation and prompt guides the output better"*.

A marketing persona says who the person is and what they want; a UX persona adds how they behave.
Neither says how they **move**, and that is what a clip needs. Without it, each clip's motion is
invented again from the shot alone: the same woman is brisk in one insert and languid in the next,
and the batch reads as several people. The model has no memory between clips, so the consistency has
to be written down once and carried by every prompt, the same way the `[CHARACTER]` block locks the
look (`series-continuity.md` §6.2).

**The rule: persona baseline, then the shot's intent.** The persona sets how this person moves on an
ordinary day; the shot's `INTENT:` (`motion-craft.md` §6b) shifts it. The same action differs by person:

| The action: getting rid of the sugar | A brisk mother of three | A careful retired teacher |
|---|---|---|
| **Baseline (MOVES LIKE)** | quick, economical, does two things at once | unhurried, precise, finishes each move |
| **Intent: done with it** | tips the jar into the bin one-handed while talking, no look back | sets her mouth, carries the jar to the bin, empties it in one firm shake, taps it once on the rim |
| **What the objects do** | the lid clatters into the sink | the jar rings once on the rim; she wipes her fingers |

**What goes in the persona** (`assets/persona-brief-template.md`, "How they move"): the `MOVES LIKE:`
line, baseline energy and tempo, body and where tension sits, how the hands handle objects, two or three
signature gestures, the face at rest and the person's tell, how they react, and what they never do.
For an avatar or a recurring character the same section applies; the gestures are the brand's.

**How it reaches the prompt.** The persona is saved as `_reference/PERSONA-<name>.md` in the job. Every
clip of that person names `persona: <name>` and carries the `MOVES LIKE:` line word for word in
`[MOTION]` or `[PERFORMANCE]`. `prompt_lint.py` warns when the persona file or its line is missing,
when a clip's line differs (change the persona, not one clip), and when a person acts in a job that has
personas and the clip names none. The `BODY:` line of the performance card (§7) is then written in the
persona's terms. It does not repeat them.

`[opinion · built on §4 and the marketing and UX persona practice the owner named; not measured here]`

## 8. Translating a note into behaviour

These are syntheses from §1–§6, not tested recipes. Each keeps the external half of the note and
drops the internal half.

| The note you want to give | What the model gets |
|---|---|
| "Reassure him" (an actioning verb) | TARGET him · BODY leans in · FACE small, steady smile, brows soft · GAZE holds his eyes · BEAT she lowers her voice, then touches his forearm |
| "She's devastated" | STIMULUS the letter · BODY weight sinks, head drops · FACE lips press together, chin tightens · BEAT reads it, then fights not to cry — the struggle, not the tears (§5) |
| "He's thinking it over" | GAZE leaves her, drops to the table, holds, comes back · FACE still · BEAT the look away, then back (§3, Adler) |
| "Nervous" | GAZE to the door, twice · BODY fingers work at the cuff, weight shifts · FACE a swallow · blinks a little more than normal (Omori & Miyata) |
| "Furious" | BODY steps in suddenly, straight at him, weight forward · FACE jaw set, brows down · no shouting unless the line shouts (§4) |
| "Overjoyed" in a wide | BODY bounces on her toes, arms opening, rising · a grab or an embrace if there is someone to reach (§4; `specifics-catalogue.md` §13.5a) |
| "Shocked" | FACE *amazed*: eyes widen and freeze, a breath in, mouth opens slightly — not *extremely shocked* (Seedance) |
| "Confident" | BODY still · GAZE holds on the target · FACE few blinks, a small smile that does not widen (Caine) |
| "Heartbroken" at a wide | BODY sits down slowly on the step, head drops, arms round the knees · hold the shot longer (`sequence-grammar.md` §5) |
| "Tears" | BEAT eyes fill, then she looks up and blinks them back; jaw works (Barr) |

## 9. Verification — read the strip, not the clip

1. **Build the performance strip** for every performer clip: `python3 scripts/contact_sheet.py
   --clip <clip.mp4> --perf` (or `--project <job> --glob "S1-*" --perf` for a scene) samples three frames at 15 %, 50 % and 85 % of the clip and labels them IN, MID
   and OUT — the same three frames the reference films were coded on (`specifics-catalogue.md` §13).
2. **Check the strip against the card.** IN is the STATE's *before*. OUT is the *after*. The change
   sits between MID and OUT, not between IN and MID. GAZE is on the TARGET in all three frames unless
   the card moves it. At MS or wider, the BODY bundle is visible in the posture — crop the head and
   ask what the body is doing (`emotional-journey.md` §4.6, item 3).
3. **Compare with a reference performance** at the same size and intensity: `film_db.py query
   --intensity 2 --size MCU`, then `film_db.py card <FILM#N>` prints it as a card in exactly this
   shape.
4. **Score it** on the QA rubric (`timing-and-performance.md` §8) and record the verdict with an
   observation (`realism-qa.md` §6).

## 10. Failure modes, named

| Name | Signature | Cause | Fix |
|---|---|---|---|
| **The pageant** | a posed prototype face, the same "sad" on every character | a bare emotion word | circumstance and a physical beat (`emotional-journey.md` §4.6) |
| **The overdrive** | gurning, bulging or glowing eyes, a scream for a surprise | superlatives, strong emotional cues | neutral wording, partial FACE (§5) |
| **The drift** | eyes wander, unfocused, "vacant" | GAZE with no TARGET | name the target and where it is (§7) |
| **The unmotivated reaction** | a face reacts to nothing and reads random | no STIMULUS | write the stimulus in, before the reaction (§7) |
| **The twitch** | two expressions in four seconds | two changes in the BEAT | one change per clip (`direction.md` §1) |
| **The talking head in a wide** | a WS where nothing reads | the feeling written only for the face | a BODY bundle (§3–§4) |
| **The dead eye** | a stare with no blinks | "don't blink" taken literally | fewer, deliberate blinks, never none (§3) |
| **The snap** | an expression that switches on | fast onset | a slower onset and a held apex (`timing-and-performance.md` §2.2) |

## 11. What this file cannot tell you

- **No study compares audiences' ratings of Method, Meisner or actioning performances.** §2 is a
  synthesis.
- **The craft books were not read directly.** Weston's list is from her own interview; Caine, Barr,
  Tucker and Donnellan come through quotations and reviews. The actual list of Weston's
  result-direction words is unverified.
- **The Laban odds come from trained human movers**, not from generated bodies; whether a model
  renders "sinking" so that it reads as sad is untested.
- **None of this is yet tested on the roster.** Card v2 is a hypothesis until an A/B on a real job
  compares it with the v1 card on the same shot. Record that test in `memory/episodes/` when it runs.
- **Vendor guidance is dated** to the checked dates above and moves with every model release.
