# The refinement loop — converging on a shot without burning the budget

**When to read this:** you have a result that is not right and you are deciding what to change next;
you are assembling the reference set for a batch; a shot has eaten three attempts and you need to
know whether to keep going. `prompting-craft.md` says what to write. `cinematography-craft.md` §7
says which controls exist at all. **This file is the loop that gets you from attempt one to an
approved shot, and — more importantly — the rules that stop you iterating forever.**

---

## 1. The governing rule

**Change one variable per iteration, and fix the earliest failing stage first.**

Two changes at once and you have spent credits to acquire no information: the shot either improved
or it did not, and you cannot say which change did it, so the next decision is a guess. This is the
same discipline as the retake tree in `ai-generation.md` and the same logic as the diagnosis
waterfall in `performance-metrics.md` — **a downstream fix applied to an upstream fault is a mask,
and it will come back in the next shot of the same setup.**

The loop is worth running properly because of where its leverage sits: **a fault caught at the still
costs one image; the same fault caught after the clip costs the clip, the retake, and the minutes
you spent watching it.** That is the ~10× frame-gate leverage the QA history in `realism-qa.md`
already measured — this file is how you actually collect it.

**1b ⚡ The other half of the rule: a correction must PROTECT the solved work, not just isolate the
change.** `[SECONDARY · practitioner course]`

§1 above is about **acquiring information** — change one thing so you can read the result. That is
necessary and it is not sufficient, because a pass can change one *intent* while silently
re-opening five *solved choices*. A generative model does not hold the parts you did not mention;
it re-decides them. So every rewrite is a fresh negotiation about everything in it, and the way you
lose a good shot is not by changing the wrong variable — it is by re-typing the paragraph that
contained the right one.

The corpus documents a four-pass correction on one dialogue shot, and the sequence is the lesson:

| Pass | What it did | Read |
|---|---|---|
| 1 | dialogue works; driver too excited, traveler **annoyed** instead of rattled | the miss is named, in two parts |
| 2 | traveler improved — **and the driver's playful irony is gone** | ⛔ overcorrection: a variable nobody complained about was re-opened |
| 3 | driver's irony restored, **solved visual choices kept verbatim** | ground recovered; the traveler is still wrong |
| 4 | traveler only: breathlessness, shock, and a shorter line | ✅ the remaining variable, alone |

⚡ **The diagnostic property: each pass preserves more solved work than the one before it.** If pass
*n+1* preserves less than pass *n*, the loop is running backwards and you are paying credits to
lose ground. That is a readable signal, not a feeling — see the tool below.

**What to write instead of "make it better."** The corpus's phrasing is the template, and it has
three parts in this order:

> **Keep the solved visuals.** *(name the protection)*
> **Restore a slight smirk,** *(name the thing pass n−1 broke, if any)*
> **then change only the traveler's state and delivery: pressed back, breathless, and in light
> shock. Shorten "Change what? No" to "Change? No."** *(name the visible miss and the intended
> replacement STATE — not the direction of travel)*

⛔ **"Make it better" cannot protect a solved choice**, and neither can "more natural", "punchier",
"more cinematic" or "polish it". They name a direction, and a model asked for a direction re-decides
the whole frame to travel in it. Name the **replacement state**: not *"less annoyed"* but *"pressed
back, breathless, light shock"*. This is the same rule `prompting-craft.md` applies to affect
generally — an emotion needs a mechanism — applied to the note rather than to the prompt.

**When a sub-element is still wrong, make the REFERENCE more specific — do not reopen the shot.**
Pass 2 of the corpus locked a steering-wheel logo and revealed that the wheel's *shape* still
morphed. The fix was not another wheel sentence: it was extracting the steering-wheel close-up from
footage already approved and binding it as its own element. ⚡ **A drifting detail is usually a
missing reference, not a missing adjective** — see `character-and-props.md` §8.3b on sub-references,
and note that re-deriving from approved footage keeps the detail in the same world as its parent.

**The reviewer test — this is what makes it checkable.**

> **You have a usable correction when another reviewer can identify the single variable that
> changed, without searching for unrelated differences.**

`scripts/prompt_lint.py <new.prompt.md> --against <old.prompt.md> [--note "…"] [--allow N]`
runs that test mechanically. It reports how many variables the pass actually moved and how much of
the previous prompt survived **verbatim**, and it fails on:

| Finding | What it caught |
|---|---|
| ⛔ *N variables changed in one pass* | pass 2 above — two performers corrected together |
| ⛔ *a reference definition changed in the same pass as the prompt body* | two grounds moved at once: change the reference, regenerate, **see** what it gives you, then write against it |
| ⛔ *0% survived verbatim* | a rewrite wearing a correction's name |
| ⛔ *the note says "better"* | a direction where a replacement state belongs |
| ~ *only X% survived* | check that every re-typed sentence is one you MEANT to reopen |
| ~ *no change* | this is a **reroll**, not an iteration — say which one you are doing |

A line change rides along with the performer being corrected (pass 4 changes her state *and* her
line and is still one variable, because a line is spoken by a performer); a camera change is a
camera variable even in a block that names a reference. A deliberate two-variable pass is legal —
declare it with `--allow 2` and say why. ⚡ **The declaration is the information**: an undeclared
second change is the one that costs you the shot.

---

## 2. The stages — each one locks something

A stage is not a step you pass through; it is a thing you **lock**. For an exterior, the world is locked too, in
its card (`world-design.md`): changing the sky, wind, life or location after it is approved stales every frame and
clip of that location until the owner approves it again. A change of direction costs an approval, not credits. Reopening a locked stage is a
decision with a cost, and it gets recorded (`pm-workflow.md` decision records), not made silently.

| # | Stage | What gets locked | Reopening it costs |
|---|---|---|---|
| 0 | **Brief** | persona, beat, format, client hard locks | everything downstream |
| 1 | **Reference set** | one reference per attribute — light, room, wardrobe, prop, motion | stages 2–5 for this setup |
| 2 | **Start frame** | the still, built coarse → fine (2a geometry · 2b identity · 2c light · 2d texture) | the clip |
| 3 | **Frame gate** | the approved still + its evidence | — (this is the cheap gate) |
| 4 | **Motion prompt** | what moves, how far, how fast — **motion only**, the frame is settled | one generation |
| 5 | **Clip gate** | QA card verdicts with observations | one generation |
| 6 | **Selects** | which take goes in the cut | an edit pass |

**The slot budget makes this concrete.** Reference-taking models bound how much you can supply —
MiniMax H3 accepts **9 images/elements, 3 videos, 3 audio** in one generation, addressable from the
prompt as *Image 1 / Video 1 / Audio 1* (`prompting-craft.md` §6b). That maps onto `_reference/`
almost slot-for-slot: character, wardrobe, props, environment and light into the image slots,
`motion/` into the video slots, the voice into the audio slots. Nine is generous until a set is
carrying three near-duplicates of the same room, which is the practical reason for the next rule.

**Stage 1 has a rule of its own: one reference carries one attribute.** A single image labelled "the
vibe" is the most common way a reference set fails, because when the output is wrong you cannot tell
which of the six things that image was carrying went wrong. Name the intent per reference — *this
one for the key-to-fill ratio, this one for the room, this one for the wardrobe* — and the fault
becomes addressable. Where the references come from is `stock-sourcing.md`, and everything it says
about what is inside the frame applies before an image enters the set, not after.

**Stage 2 runs coarse to fine for a reason:** a change at 2a (geometry, blocking, shot size)
invalidates every judgement made at 2c and 2d, so settling light before framing means grading a
composition you are about to throw away. Work down the ladder, never up it.

---

## 3. What to change, by what failed

The routing table. Find the symptom, go to the stage that **owns** it, change the one lever.

| Symptom in the output | Stage that owns it | The single lever | ⛔ Not this |
|---|---|---|---|
| Framing, shot size or blocking wrong | 2a | rebuild the still — geometry is a frame property | adding composition adjectives to the prompt |
| Subject identity drifts between shots | 2b | the approved start frame driven through i2v; vendor reference/element system | locking a seed (vendors disclaim determinism) |
| ⚡ **Identity drifts across an ACTION sequence** (multi-cut chase, driving, fight) and 2b is not holding it | **0 — design** | ⚡ **conceal it**: write a PHYSICAL reason the face is not readable — mirror-bright glass, backlight, silhouette, an occluding foreground — stated as a presence, not an absence, and restated in every cut (`specifics-catalogue.md` §1.9, `move-catalogue.md` §31) | ⛔ more identity passes on a sequence where the face is never the subject. If nothing in the story needs that face legible here, it is a cost with no return |
| ⚡ **A background element keeps mutating into a copy of the hero** | **1 — the plate** | remove it from the reference definition itself, as an absence the plate carries (`specifics-catalogue.md` §3.7: *"the curbs are completely EMPTY"*) and label the rest safe/risky/unnecessary (`production-design.md` §5b) | a suppression term in the shot — it fails at the shot that forgets |
| ⚡ **Traffic, crowds or a group read as chaos rather than as speed/scale** | **0 — design** | name the scene's **visible geometric invariant** (a lane line, a touchline, a horizon) and forbid crossing it, for EVERY element including the hero, in every cut (`specifics-catalogue.md` §2.9) | "realistic driving", "natural crowd" — a vibe cannot be checked in a frame |
| Wardrobe or prop changes between clips | 1 → 2b | a persistent reference for that element; fixed wardrobe token | re-describing it in words each time |
| Light flat, or from the wrong side | 1 → 2c | choose a reference that already has the ratio | prompting a ratio — it is not a promptable control |
| Palette off-brand | 2c | reference + the client's colour tokens | fixing it in the grade across a whole batch |
| Skin plastic, faces waxy | 2 (or the model) | start frame; then the model itself | post sharpening or grain |
| Background generic or invented | 1 | freeze the environment as an image | describing more nouns |
| Motion morphs, limbs swim | 4 | shorter duration, simpler single action, leading pad | more motion adjectives |
| Perspective or apparent focal length is wrong (a wide-lens face you wanted long, a distorted room) | **2 — the frame** | **rebuild the start frame at the right apparent distance**, then animate | ⛔ any prompt or move on the existing frame |
| Camera move wrong or absent | 4 | name one move, or none | stacking two moves in one clip |
| Mouth does not match the words | — | the lipsync routing in `ai-generation.md`, not this loop | re-rolling and hoping |
| ⚡ **The PERFORMANCE is wrong** — delivery flat, the emotion off, a line that reads recited | **6, alone** | **isolate the read**: generate a separate face-only clip in a quiet setup, direct the delivery (the word the voice breaks on, the micro-pause), marry the audio back in the edit | ⛔ re-rolling the whole shot. A locked 20-second action take is not re-shot for one line: treat the fix as a voice session for that line, not a new scene [SECONDARY · practitioner corpus] |
| ⚡ **The emotion is right but continuity of feeling is wrong** (he smiles two scenes after crying) | 0 → 6 | the performance note alone — the camera spec is a separate knob and does not reopen | rewriting the whole prompt, which re-rolls the dice on everything that already worked |
| ⚡ **It lands "in one breath"** — no room to process, a cut straight from a flashback into dialogue | **0 — the plan** | **split the beat into another shot** so the 1–2s pause has its own frame; a reused frame from an earlier generation can BE that shot | ⛔ asking one generation to carry the emotion and the recovery at once |
| ⚡ **Physics broke** — a jump truncates, limbs leave the body, the action cuts off | — | **discard and re-roll.** There is no partial credit in a physics failure | any prompt edit; nothing in the text caused it |
| Reads as an ad | 0 | the script and the hook | any visual change |
| Feels slow, no reason to stay | 0 | the hook (`persuasion-psychology.md`) | faster cutting |

Two rows deserve saying out loud because they are where budgets die. **"Reads as an ad" and "feels
slow" are stage-0 faults** — no amount of regeneration fixes a script problem, and every attempt
spent trying is money converted into nothing. And **"light is flat" is not a prompt fault**: you
cannot direct a key-to-fill ratio through a text prompt, you can only choose a reference that
already has one, which is why the reference set is a production asset rather than a mood board.

---

### 3.1 ⛔ i2v interpolates motion. It does not change the lens.

**The single most expensive misunderstanding available at stage 2.** A start frame carries its own
perspective — the apparent subject distance, the facial compression, the room's convergence — and
**image-to-video cannot undo it.** Asking for "a 50mm push-in" from a frame shot wide gives you a
push-in *through* a wide-lens face: the distortion scales up with the subject.

This is the same wall the FLF test hit from the other side: asking an image model to *reframe* an
existing frame returned a new pose at the old framing (`motion-design.md` §2.1). **A model changes
what is happening in a frame far more readily than where the camera is.**

- **Fix:** regenerate the start frame at the intended apparent distance and perspective character
  (`cinematography-craft.md` — perspective is distance, not focal length), *then* animate. One extra
  image beats any number of retakes on a frame that was wrong before it moved.
- **Cheaper fix when the framing is nearly right:** **crop** the existing frame. Cropping changes
  framing without asking a model to re-imagine anything, and it is the move that made FLF work.
  ⛔ It changes framing, not perspective — a cropped wide-lens face is a tighter wide-lens face.
- ⛔ **Never spend a video generation testing whether the lens can be fixed in motion.** It cannot.

## 4. The parameters the decision is made on

When several changes look plausible, rank them by these, in this order:

1. **Earliest failing stage.** Always. A later stage cannot repair an earlier one, it can only hide
   it.
2. **Controllability class** — prompt / start frame / post / impossible, from
   `cinematography-craft.md` §7. If the lever is in a class you are not currently working in, you
   are in the wrong stage.
3. **Blast radius.** Which approved artifacts does this invalidate? Changing wardrobe invalidates
   every clip in the setup; changing a hook invalidates only the first six seconds. Prefer the
   change that voids least, when both fix the fault.
4. **Cost of the attempt** — credits plus your minutes — against what is left in this shot's budget
   (`clients/costs.<client>.json`, the retake economics table).
5. **Lock compatibility.** A client hard lock is not a lever. If the only fix violates one, the
   answer is an escalation, not a clever workaround.
6. **Evidence.** What frame test failed, stated in words. **No observation, no retake** — the same
   rule as the QA card. "Doesn't feel right" is not a lever, it is a request for a diagnosis.

---

## 5. Stop rules — what they are actually for

⛔ **Re-founded 2026-08-30.** These used to be justified as savings. They are not: **they are
information rules.** A third attempt on the same axis does not cost you money so much as it tells
you the axis is not controllable — and continuing spends the one thing that is genuinely scarce,
which is the six hours a video takes. Cost is no longer an input to any of them
(`ai-generation.md` → the quality floor).

Iteration has no natural end, so the end has to be written down.

- **Two retakes per shot** is the cap (`ai-generation.md`). The third attempt is not another try; it
  is a different decision — change stage, change approach, or accept.
- **Three attempts on the same axis with no movement means the axis is not controllable in this
  stack.** Stop pulling that lever. Record it — that is a guardrail-table row and an episode note,
  and it stops the next person (you, in three weeks) from spending the same credits.
- **The diminishing-returns test:** the failing frame test now passes and nothing else broke →
  **stop**. "It could be better" is always true and is not a criterion. The test is the criterion.
- **Judge at delivery size.** A fault visible only at 100% on a 27-inch monitor is not a fault in a
  9:16 ad watched on a phone; a fault visible on the phone is worth another generation. Use the
  contact sheet at the real size (`contact_sheet.py`).
- **Escalate instead of iterating** when the fault is in the brief. NEEDS INPUT is a legitimate
  output of this loop and is cheaper than any number of attempts (`pm-workflow.md`).
- **At volume, time-box per shot.** Mode B's economics assume a shot converges in a bounded number
  of attempts; a shot that does not is a stretch row, and the batch plan already marked which rows
  can be cut (`modes/ugc-volume.md`).

---

## 6. The reference set is versioned too

References are not scratch. A set that improves is the compounding asset on the visual side, exactly
as the hook bank is on the writing side.

- Keep the set in the project's **`_reference/`** folder, one subfolder per attribute
  (`character/`, `wardrobe/`, `props/`, `environment/`, `light/`, `motion/`), intent labelled per
  file. It sits outside the numbered stages because it is input, not output (`pm-workflow.md`).
- **A rejected reference gets retired with a reason** — "too much contrast for the wardrobe token",
  "face is recognisable, reference-only" — so it is not re-tried next month.
- A reference that produced an approved frame gets promoted into the client's Visual Bible
  (`clients/_TEMPLATE.md` §6) and is reused rather than re-sourced.
- Provenance travels with it (`stock-sourcing.md` §9). A reference with no provenance cannot be
  cleared later, and an uncleared reference cannot ship.

---

## 7. Logging — what makes the loop pay for itself twice

**Every iteration is a shot manifest row** (`shot_manifest.py`), and the row records **the one
variable that changed**. That is what turns a day of fiddling into three durable things: the
retake-economics actuals, a new guardrail row when an attempt fails in a new way, and the episode
note that feeds the consolidation pass (`self-evolution.md`). A loop that is not logged teaches
nothing and has to be re-learned per project, which is the expensive way to run a studio.

**7b. ⚡ Pair every rejected setup with the COMPLEXITY IT REVEALED — not with the fact that it
failed.** `[SECONDARY · practitioner course]`

> *"'Aerial failed' is vague; 'the aerial exposed all traffic lanes at once' tells you what to
> remove from the next attempt."*

A rejection log that records outcomes teaches you nothing you did not already know by looking. A
rejection log that records **what the setup demanded** is a list of the things this scene cannot
afford, and it transfers — to the next setup, the next scene, and the next project.

| ⛔ Logged as | ✅ Logged as |
|---|---|
| aerial failed | the aerial exposed all traffic lanes at once — every vehicle in frame is a dependency |
| the wide didn't work | the wide put four characters and the product in one frame; nothing had enough pixels to stay itself |
| plate looked wrong in motion | the plate's signage text re-rendered per frame; any legible text is a risky element (`production-design.md` §5b) |
| take rejected, face off | the expression pass traded identity for emotion — these are separate passes (`ai-generation.md` §3b) |

The right-hand column is the one that generalises, because it names a **class**, and a class can be
designed out of the next attempt. ⚡ This is the same asymmetry the move catalogue records: *a kept
take tells you one thing worked; a rejected take with a diagnosis tells you what fails.* Write the
diagnosis while you still have the frame in front of you — it is unrecoverable an hour later.

---

## 8. What this file cannot do

- It cannot tell you a shot is good — only that a named test now passes. Taste is not delegated
  here.
- It cannot rescue a stage-0 fault. If the brief, persona or hook is wrong, every lever below is a
  more expensive way to be wrong.
- The stage ladder is house doctrine derived from this pipeline's own retake history, not a
  published method — it is stated as reasoning so it can be argued with, and it should be revised
  when the manifest actuals disagree with it.
- Model behaviour underneath it decays. The routing table's levers assume the 2026 stack in
  `ai-generation.md`; re-check it when the roster changes.
