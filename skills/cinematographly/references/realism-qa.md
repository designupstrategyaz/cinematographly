# Realism QA — beating the "AI slop" tell

Everything in this file exists to answer one question a client asks in different words every time:
**"why does this look AI?"** It is the QA surface for any mode where the output has to pass as
real — UGC above all, but the narrative lane benefits from the same passes.

This file is the **symptom layer** — what to look for and what to do about it.
**`photorealism-physics.md` is the layer beneath**: why a real frame looks captured (artifacts as a
field, not a style), why AI skin and motion read wrong, and a remedy table saying for each cue
whether it can be prompted, forced with a start frame, added in post, or only fixed by a retake.
Read it when a tell keeps recurring and the counter-move here is not holding.

Two halves: the **tell list** (what gives it away, item by item) and the **counter-moves** (what
you deliberately do to break each tell). Run the checklist at the end before a clip leaves
`03-clips/_review/`.

Verified against 2026 practitioner sources and this account's own production record. Where a claim
came from one project rather than a source, it says so.

---

## 0. The framing that matters

**Do not confuse "undetectable" with "natural."** They are different goals with different methods,
and only one of them is a business you can run.

- Platform detection is now **model-level and provenance-based**, not texture-based. SynthID
  watermarks are embedded by the generating model (Google's video models, OpenAI image gen,
  ElevenLabs audio) and survive screenshots, re-encodes, and normal transforms; C2PA 2.1 Content
  Credentials ride in the file's metadata and are read directly by TikTok and YouTube's
  auto-labelling. Nothing in this file evades either, and **trying to is not the goal.**
- 2026 detection research (GazeCLIP, Face2Parts, VIGIL, VLAForge) keys on *anatomically grounded*
  signals — gaze-vector distribution, per-region face analysis, cross-modal identity mismatch. The
  useful consequence: **the same fixes that satisfy a human viewer are what those classifiers score.**
  Fixing the tell and satisfying the detector are the same work.
- So: **disclose per platform (see `compliance.md`), and make the content good.** "Reads as native
  UGC" means a viewer doesn't bounce and a brand isn't embarrassed — not that a label is avoided.
  YouTube states outright that disclosing does not by itself limit reach or monetization.

---

## 1. Visual tells → counter-moves

| # | Tell | Why it happens | Counter-move (specific) |
|---|---|---|---|
| V1 | **Waxy / plastic skin** | Denoising erases pore detail and subsurface scattering | **On the start frame only** (a clip prompt cannot hold pores: `prompting-craft.md` §2, the material row): prompt for it by name: "realistic skin pores, natural subsurface scattering, slight skin oiliness, faint freckles, fine laugh lines, uneven skin tone." **Never** write "flawless", "porcelain", "perfect complexion" |
| V2 | **The "AI face"** — too symmetric, mean-regressed features | Diffusion pulls toward the average face | "Natural facial asymmetry, slightly uneven features, one eyelid marginally lower." For a recurring character, bake the asymmetry into the hero reference once so every shot inherits it |
| V3 | **Dead eyes, no catchlight** | No physical light source given, so the model has nothing to reflect | Name the source *before* other details: "soft window light from camera left." A named source is what puts a catchlight in the iris |
| V4 | **Gaze drift** — eyeline wanders mid-clip | Model interpolates an unspecified gaze target | Fix the eyeline per shot and keep it consistent shot-to-shot; never ask for a gaze change mid-clip — cut instead. Also the single strongest forensic signal detectors use |
| V5 | **Blink absence or metronome blinking** | Blink isn't modelled as behaviour | Ask for "occasional natural blinks, irregular timing." Check the clip at 0.25×. The floor is measured, not felt: **17 blinks/min at rest and 26/min in conversation** — so a 5s clip wants **at least one, usually two for a talking character**, and each runs **4–10 frames with the opening about twice as long as the closing** (`timing-and-performance.md` §2.1) |
| V5b | **Glassy gaze — eyes that move only with the head** | Saccades aren't modelled; the head carries the eyes | The measured floor is **a fixation every ~6 frames, i.e. 3–4 gaze changes a second** — order of **15 small shifts in a 5s clip**, not two. Ask for the eyes to lead a head turn and for a glance to a named object. **This is the exact appearance/motion mismatch the uncanny-valley fMRI work measured** (`timing-and-performance.md` §4) |
| V5c | **No ease-out — the clip ends mid-motion** | The model blocks anticipation and action and never the settle | Measured on three clips: all peaked in their **final second**. This is an **asset** where you cut out of the peak (mid-action cuts are invisible) and a **defect** only where the shot must land. `scripts/clip_qa.py --landing` decides; the settle is manufactured in the edit (`timing-and-performance.md` §7) |
| V5d | **Lips keep moving after the line ends** — often with the head already frozen, so the mouth is the only thing moving | The clip was generated longer than its audio, and this model class has no idle state — its training data explicitly excludes non-speech segments | ⛔ Generate the dialogue clip **to the line** and take the handle from the join, not from the generation. Scope the `[SPEECH]` articulation instruction to the spoken window — written unscoped it *asks* for this — and supply a closed-mouth end frame where a tail is unavoidable (both measured 2026-08-29). ⛔⛔ **No metric in this skill detects this.** The clip with working lips measured 15.4% of peak in its tail and `clip_qa.py` called it `SETTLES`. **Check the mouth by eye at 0.25×.** `shot-handoff.md` §1 and §9 |
| V5e | **A briefed negative state — "stressed", "worried", "angry" — returns a vacant mask** | Three stacked causes: at peak intensity a face carries arousal but **not valence** (Aviezer 2012, with real photographs); these are the most resolution-hungry, shortest-range expressions (Du & Martinez; Smith & Schyns); and the model over-drives them (Kramer 2026) | ⛔ **Do not push the amplitude — change what you cast.** The reference frame is a **genuine, moderate, positive-or-neutral** state; the negative is carried by circumstance, dramatic irony, the body and the cut. Exaggeration has a measured cost — 140% facial magnitude reads *"fidgety and anxious"* (Hyde 2016). And ⛔ do not swap it for a beaming stock smile: that is V2. `emotional-journey.md` §4.5 |
| V6 | **Hands: extra/fused fingers, broken grip** | Geometric complexity at contact points | Keep hands out of frame where the shot allows. Where they must show, describe the exact pose and grip; state the object is SOLID at a fixed position and motion STOPS at its surface; name "clipping / z-fighting / interpenetration" as things to avoid. Review that frame specifically |
| V7 | **Prop physics wrong** — object weightless, no deformation, no contact shadow | Physics isn't simulated | Prefer shots where the product is *held still* or set down, not tossed/poured/squeezed. Where motion is required, keep it short and cover the impact frame with a cut |
| V7b | **An object teleports** — thrown out of frame and back at rest, or gone for a few frames and back (on one job: the keys) | The model keeps no object permanence; a three-frame review (15/50/85 %) cannot see it | Around every action point, look at EVERY 2nd frame: `action_points.py <clip> --permanence <clip>.permanence.png` writes a numbered strip from 6 frames before the onset to 6 after the settle. Count the objects held, falling and at rest on each frame; an object that disappears and reappears fails. The prompt side is `prompting-craft.md` §6.4b |
| V8 | **Background warping / temporal flicker** | Objects re-estimated each frame; no permanence | Single static light source; one camera-move type per clip (a push OR a pan, never both); **shorter clips (3–5s) compound less drift**; image-to-video from a locked reference frame; deflicker in post |
| V9 | **Lighting too even, no shadow** | Model defaults to ambient-only | ⚡ **Fix it in the start frame, not in words.** Choose or generate a frame that already has one source and a shadow side, then animate. In the *frame* prompt, name (a) the source as an **object in the room** — "a lamp on the counter, switched on" — and (b) a **named pattern** where a face is involved ("loop", "split") — both are caption-native. **Mixed colour temperature reads more real than uniform**: a warm practical against a cool window is the single cheapest realism upgrade, and it is a *scene* description, not a measurement. ⛔ Do **not** write "5200K, 2:1 key:fill" into a prompt: Kelvin and ratio have no caption presence, buy style noise, and — worse — tempt you to approve the clip because the brief said it (`cinematography-craft.md` §7.0, §7.2). Approve on F1/F2/F22/F23 |
| V10 | **Unnaturally smooth camera** | Motion path is mathematically clean | Do not prompt the word "handheld" alone (`cinematography-craft.md` and `motion-design.md` §2.5 own this): carry the move with motion transfer from a real clip, or add texture in post at the measured jitter bands in `motion-design.md` §2.5 |
| V11 | **Room too tidy / staged** | Prompt described a set, not a home | Name the mess: "a mug and a hair tie on the nightstand, a charging cable, a slightly rumpled duvet." UGC lives in imperfect rooms |
| V12 | **Wardrobe / jewelry / hair drift between shots** | No persistent identity lock | Supply identity + wardrobe + product reference images labelled by role; describe them as held: "her clothing, hairstyle and accessories stay exactly as in the references" (the nouns "outfit change, hairstyle change, missing jewellery" go in `[SUPPRESS]` or `[CONSTRAINTS]`, v2.71.0). For profile/turn shots supply three angles rather than trusting interpolation. Change **one variable per regeneration**. Check it across the scene, not shot by shot: the scene board before any approval request (`review-and-approval.md` §11, v2.49), fixing toward the scene's sheet, never toward the neighbouring shot |
| V13 | **Product drift** — label, shape, or colour changes shot to shot | The product is being re-imagined, not composited | Composite the real product/logo onto the **start frame** before generation, then animate — never ask the model to render a brand mark or legible text (verified method; see `ai-generation.md`). ⚡ Then check the paste on **four axes — direction, colour, quality, quantity** (`cinematography-craft.md` §8 **F24**): a correct product lit from the wrong side, or sharper than the plate it sits in, is a *new* tell traded for the old one |
| V14 | **Identical framing and duration across the batch** | One template, N renders | Vary framing distance, angle, and exact duration per video **within** a campaign. Platforms demote "unoriginal and spammy" mass-produced content, and viewers pattern-match a template within two exposures. See §5 for the batch-variance rule |
| V15 | **Over-clean 4K look** | Generated at hero resolution and left there | UGC should look like a phone. Grade toward phone-camera colour science (open shadows, C1), add grain only where it survives the platform round trip (C2), and deliver at the format's resolution rather than the highest one available — a 4K UGC clip reads as an ad. That holds unless the job's CHECKPOINT carries the `upload-master` switch (`assets/project-switches.json`): one extra upload copy of the same shape at a larger size (e.g. 2160p from a 1080 delivery), checked with `export_qc.py --upload-master`, while the delivered file still matches its preset (v2.48.0, switch `upload-master`). See §4 |

---

## 2. Audio and voice tells → counter-moves

| # | Tell | Counter-move |
|---|---|---|
| A1 | **Flat prosody** — every sentence the same shape | Use expressive-model audio tags on the emotional beat: `[sighs]`, `[laughs]`, `[whispers]`, `[sarcastic]`, `[frustrated sigh]`, `[happy gasp]`. Lower the stability slider toward the creative end for variance; a high-stability voice is consistent *and* lifeless |
| A2 | **No breath, no mouth noise** | `[exhales]` / `[swallows]` between phrases; do not gate or de-breath in the mix. Audible breath under dialogue is the difference between "voice actor" and "person" |
| A3 | **Over-clean audio, no room tone** | Lay a room-tone bed at −18 to −24 dB under **all** dialogue. A phone recorded in a bedroom has a bedroom in it. This is the single most-missed UGC realism fix |
| A4 | **No disfluencies** | Write in the "um," the false start, the self-correction, the "wait, actually." Then cut mid-word on one transition instead of always cutting on a clean sentence boundary |
| A5 | **"Influencer voice"** — the same bright upsell cadence every time | Vary stability and style settings *per video*, not just per character. Rotate which tags get used. If every video in a batch sounds like the same person selling, the batch reads as a batch |
| A6 | **Pacing too even** | Use explicit break markup (`<break time="1.5s"/>`) rather than punctuation hacks; real speech has uneven gaps |
| A7 | **Music too loud, too clean, too "stock"** | Measure the gap, not the gain: the voice at least 14 LU over the music and 19 LU over the ambience while it speaks, and on a phone too (`mix_qa.py`, `editing-and-audio.md` §7b; it superseded "duck −8 to −12 dB"). For UGC, consider **no music at all** under the hook — a bare voice reads more authentic than a bed |
| A9 | **The SFX does not match the shot** — three drops of sound for one splash, a hit a few frames early, a far object as loud as a near one, a glass sound on a ceramic cup | Conform it (`editing-and-audio.md` §7f): one sound per event, on its frame or a frame late, its level, tone and room from the distance, force and size, its file from the material the read sees |
| A8 | **The clip's own sound left in** — a model's ambience that changes on every cut, gibberish under the line, a foley hit that is right in time and wrong in kind | The clip's own audio is a guide track (`editing-and-audio.md` §7d). In drama, one ambience bed per location, held across the scene (§7e). `mix_qa.py` finds a non-dialogue take's own sound in the export |

**Ordering note:** for dialogue the mouth is only right if the model has the real audio — the
recorded voice passed as a reference (Path A), or speech the model generated itself (Path B); the
routing is `ai-generation.md` Step 4. A silent generation with a separate voice laid over it is
never a path — that decorative mouth movement escaped QA three times on one project because the
check was "mouth open during VO, closed after," which tests the *window*, not the *articulation*.
**Path B adds a check: verbatim words** — listen and compare what was actually said against the
script (brand names, numbers, the CTA), because a native-audio model may drift from the text.

**The lipsync QA rule, therefore:** you check lipsync by **listening to an A/B with the VO over the
picture**, not by looking at a contact sheet. A frame grid cannot show articulation.

---

## 3. Structural and behavioural tells

These are the ones that survive a perfect render.

- **The person has no reason to be talking.** Real UGC starts mid-thought, in a place, because
  something happened. Open on a *situation*, not on a presenter addressing camera from nowhere.
- **The room is a studio.** Bedroom, kitchen counter, car, bathroom mirror, hallway. Not a
  seamless backdrop, not an office with a plant.
- **The framing is a portrait.** Real phone footage is off-centre, slightly low, sometimes with the
  subject half out of frame at the start.
- **Nothing interrupts.** A dog, a doorbell, a hand adjusting the phone, a glance off-camera — one
  small intrusion per video buys more authenticity than an hour of grading.
- **Every video is the same length.** See V14.
- **The claim arrives too fast and too clean.** Real people hedge. "I don't know if it's the
  placebo thing but—" outperforms "This changed my life" and is safer under §compliance too.

---

## 4. The finishing pass — phone-camera treatment

Order matters. Run it in this sequence on any clip meant to read as UGC:

1. **Upscale first** (if the source was generated below delivery res).
2. **Per-clip colour correct** — exposure and white balance, so all clips share a base. Since 2.36.0 this is
   the model's correction LUT on its colour group, plus a capped shot-match CDL against the approved start
   frame (`grade_luts.py`, `look_qa.py shots`; `editing-and-audio.md`, the grade).
3. **A phone look, its strength baked into the file** (`grade_luts.py look --kind phone --strength 60`).
   ⛔ **C1, 2026-10-26: open shadows, not crushed blacks.** Deep but unclipped blacks with a lifted
   toe, a soft highlight shoulder, and saturation that eases off on skin. 45+ viewers on phones in glare
   lose dark detail first (Owsley 2016). `look_qa.py export` fails a shot whose P2 black sits within 3 codes
   of legal black. This replaces "slightly crushed blacks". Cinema stocks (Kodak 2383, Fuji 3510) are for
   drama, not UGC.
4. ⛔ **Grain, C2 (2026-10-26): start at 3–6 %, and keep only what survives the platform round trip.**
   Grain is new noise on every frame, so platform encoders smear it into blocks and banding [SECONDARY ·
   FilmConvert]. `look_qa.py export` re-encodes the file like a platform: in ads, grain under 35 % surviving
   fails, so take it out; in drama it is a finding. This replaces "grain at 8–15 % opacity". The ads lane
   gets no texture node at all (`grade_luts.py` profiles). That holds unless the job's CHECKPOINT carries the
   `finish-texture` switch (`assets/project-switches.json`): a small bloom, optional grain and a light vignette
   in the ads lane's grade plan, with skin protection, the look's strength and `look_qa.py export` unchanged
   (v2.48.0, switch `finish-texture`) — when and where: `editing-and-audio.md` § Finishing looks.
5. **Light blur under 1px** to kill the AI micro-sharpness. ⚠ Two of the three council judges would remove
   this, because it costs older eyes contrast and compression blurs anyway. It was not among the four rule
   changes the owner accepted, so it stands until they decide (the grade and finish proposal of 2026-10-26 [studio history]).
6. **Handheld shake** if the generated move was too smooth — a small, irregular 2D transform, not a
   sine wave.
7. **Re-encode once at delivery**, not repeatedly. Each pass costs quality and can degrade
   provenance metadata you may need for disclosure. Deliver with Video levels and the Rec.709-A tag, then
   run `look_qa.py export`; `approve export` refuses without a passing report.

⛔ **C3, effects source (2026-10-26):**

- **Colour** comes from LUTs.
- **Drama texture** (grain, halation, bloom, gate) comes from Film Look Creator through the template's
  DRX.
- **A hand-written DCTL** only where neither can do the job, today the radial vignette. Every LUT and DCTL
  gets a render test (`grade_luts.py lutcheck`).
- No radial chromatic aberration: all three judges found it invisible after compression, a gimmick.

⛔ **C4, Resolve 21's AI face tools (2026-10-26):** Face Reshaper and Face Age Transformer are
never used in ads. Blemish Removal is allowed at most on an AI artefact; log it, and never use it on a
before/after shot.

The more of §1 you got right in the prompt, the less of this you have to do. Post is a repair
budget, not a plan.

---

## 5. The batch-variance rule (volume mode only)

A batch that shares a template *is* a tell, independent of any single video's quality.

⛔ **And since 2026 it is more than a tell — a template batch is named in YouTube's own policy.**
Its inauthentic-content rule covers *"AI-generated content made with generic or unoriginal templates
giving the impression of mass production"* and *"videos where characters are put in the same
situation over and over again with the same outcome"* — original AI content made at volume, with no
reuse element and no escape by having filmed it yourself. Meta's parallel rule is narrower: its
"duplicative" language reaches near-identical variants posted into one surface, while its enumerated
low-value edits are scoped to laundering *another creator's* post (`discovery-and-search.md` §4c).
Consequences run to a non-recommendable account. So this section is not only about whether the work
reads as AI — **it is about whether the account keeps its reach.**

Within one brand's monthly batch, hold these ranges:

| Dimension | Rule |
|---|---|
| Duration | Spread across the brief's window (e.g. 35–55s), never all within 2s of each other |
| Opening framing | At least 3 distinct framings across the batch (close selfie / mid room / product-first / hands-only) |
| Location | At least 3 distinct rooms or settings |
| Presenter | Rotate personas; no single face is more than ~40% of a month's batch for one brand |
| Hook type | At least 4 distinct hook patterns represented (see `modes/ugc-volume.md`) |
| Music | Not every video scored; some VO-and-room-tone only |

⛔ **And the rule the six rows above cannot express: no two of these dimensions may move together.**
Each row is a *within-column* rule, and a batch can satisfy every one of them and still be a
template — persona P1 serious in every row and P2 light in every row is perfectly balanced on both
columns and is one video shot eight times. That is not hypothetical: it is what `batch_plan.py`
shipped until 2026-09-07, and all six checks passed on it every day
(`self-evolution.md` §6b, "the check that looks at one column at a time").

> **A property that only exists BETWEEN two variables cannot be checked one variable at a time.**

So the seventh rule is pairwise: **for any two dimensions, knowing one must not tell you the other.**
`batch_plan.py` measures it as a predictability share normalised against chance — 1.0 is a perfect
template, and the threshold is 0.60, set from the measured achievable floor (an 8-row batch bottoms
out at 0.50 and cannot go lower at any search budget; a 30-row month reaches 0.19–0.29). Pairs whose
level counts multiply past the row count are reported **structural** and excluded: no re-deal can
separate 4 hooks × 3 settings inside 8 rows, and the fix there is fewer levels, not more inputs.

`scripts/slop_check.py` measures the mechanical within-column ones across a delivery folder —
duration window, duration spread, distinct durations, resolution and frame-rate consistency — and
fails the batch if it collapsed to a template. Add `--loudness` for a per-file integrated-LUFS pass (on target, and
consistent across the batch); it is opt-in because it is slow. The rest of this section — framing,
setting, presenter mix, hook types, scoring — is a human read, and the script prints the reminder.

---

## 6. The per-clip QA card

Run before a clip moves from `03-clips/_review/` to `03-clips/`. Re-run on **every regeneration** —
a prompt fix is a hypothesis until frames confirm it.

**⛔ A checkmark is earned with evidence, not intention.** No item on this card gets a ✅ from the
prompt — only from the pixels and the audio. And every ✅ is accompanied by **one concrete
observation of what was actually seen or heard** ("low sun from camera-left, long shadows on the
stone"; "the /p/ in 'panouri' closes on the open frame"), written into `09-qa/QA-LOG.md`. The
observation is the mechanism, not the box: a ✅ can be typed without looking; a descriptive sentence
cannot.

**The production proof:** on one project, 13 start frames — 11 truly inspected, 2 "approved from the
prompt." The two prompt-approved frames were the **only** two whose clips were later rejected
(0/11 vs 2/2). The economics compound it: a wrong frame caught at the frame gate cost ~2 credits;
the same wrong frame caught after clip generation cost 21 credits in redone clips. **The frame gate
has ~10× leverage, and it is skipped exactly when you are working fast, in batch, on frames that
"obviously look fine." No exceptions, no sampling.**

QA-LOG format, one line per verdict:
`<shot> · <gate: frame/clip/selects> · PASS/RETAKE · <the observation> · <date>`

`scripts/qa_log.py` writes the line and **enforces the rule mechanically**: it refuses an empty or
intention-only observation ("looks good", "as prompted"), and refuses a dialogue/reaction clip PASS
whose observation mentions nothing *heard* — the listening requirement, machine-checked.
`scripts/contact_sheet.py` puts the pixels in front of you (several frames per clip, sampled
mid-clip past the morph-settle, away from the thumbnail trap); the observation still has to be
yours.

- [ ] **Sampled several frames across the whole clip**, not just the thumbnail or the approved start frame
- [ ] Face on-model vs the hero reference; wardrobe, hair, accessories unchanged
- [ ] Eyeline consistent with the previous shot; no mid-clip gaze drift
- [ ] **At least one natural blink** (two if speaking); irregular timing; opening slower than closing
- [ ] **Eyes move independently of the head** — small gaze shifts throughout, not a locked eyeline
- [ ] A smile, if any, **grows and holds** — a smile that snaps on in under 6 frames reads posed
- [ ] Face is **not mirror-symmetric**; mild asymmetry present
- [ ] `clip_qa.py` run: no dead zone, no focus decay past threshold — and **if this shot lands**,
      `--landing` passes or a tail ramp / freeze-settle is on the edit list
      (`timing-and-performance.md` §8 carries the numbers behind these five)
- [ ] Hands: correct count, plausible grip, no clipping at any contact point
- [ ] Product/logo is the **real** asset, undistorted, correctly spelled; no model-invented text
- [ ] Background stable — no warping, flicker, or objects appearing/disappearing
- [ ] Lighting has a named source and visible direction; not flat ambient
- [ ] Skin has texture; no plastic sheen
- [ ] **Lipsync checked by listening to an A/B with the VO over picture** — not from a contact sheet
- [ ] **Duration fits the line** (`ffprobe`) — and any seconds past it carry a *designed aftermath*,
      not an undirected handle. ⛔ The old "always carry a 1–2s handle" rule was wrong for
      audio-driven clips and produced V5d (`shot-handoff.md` §2)
- [ ] **Mouth closed and still after the final word** — ⛔ **by eye at 0.25×, never from a number**:
      the post-line motion gate is measured NOT to catch lip articulation (`shot-handoff.md` §9)
- [ ] Last frame is a **composed end frame** — pose settled, gaze placed, motion at rest. The
      exception is a clip that hands its motion to the next shot (`join:` motion, `shot-handoff.md`
      §4b): there the motion is still running at the cut, and the edit cuts before any settle
- [ ] The shot's **HANDOFF card** is satisfied — FUNCTION, IN, OUT, JOIN (`shot-handoff.md` §5) —
      and every insert has a FUNCTION, with no claim playing over B-roll
- [ ] **Motion measured** — `motion_qa.py clip` on the selected take: camera, framing (first, middle,
      last), the subject's direction in and out, the action points. Every finding is answered: either
      the take is wrong, or the plan was. ⛔ `gate.py approve lock` refuses without a current report
      for every shot in the cut, and a joins report on the newest cut (2026-10-26)
- [ ] Frame rate converted to the timeline's rate if the model output differs (see `ai-generation.md`)
- [ ] Room tone present under any dialogue in the mix
- [ ] **Delivers its performance card** — the state transition, the beat, the gaze (`direction.md` §1);
      a technically clean clip with the default pleasant face is a retake candidate
- [ ] Props per the blocking card — right object, right hand, right place
- [ ] Nothing in the frame contradicts the compliance sheet (see `compliance.md`)

---

## 6b. ⛔ The card is TIERED — read this before running it on everything

Running every check in §6 on every clip costs more than the generation does. The tier is chosen by
what the shot *does*, which its handoff card already declares (`shot-handoff.md` §5):

- **Ship gate — every clip, ~60s each:** format and duration · `clip_qa.py` clean or its finding
  accepted · `motion_qa.py clip` run (automatic, seconds per clip) · **mouth closed and still after the final word** (eye, 0.25×) · on-model against the
  locked reference · no gross artifact at a contact point.
- **Full card — the hero shot, the landing shot, and anything the ship gate flagged.** That is where
  blinks, gaze count, ease-out and the composed end frame get read in full.

⛔ A mid-sequence two-second insert does not get the full card: you cut out of its peak, so half the
temporal checks do not apply. Applying them anyway is over-processing with a craft justification,
which is the most convincing kind. The budget this protects is `production-runbook.md` §4.

## 7. Automation roadmap — honest status

**Built since 2026-08-29:** `scripts/clip_qa.py` measures the *temporal* defects a contact sheet
cannot show — dead zones and freezes, focus decay across the clip, and whether the clip eases out of
its peak (`--landing`). It is ffmpeg-only and deliberately conservative on focus. It does **not**
count blinks, track identity, or judge a performance. **Built 2026-10-26:** `scripts/motion_qa.py`
measures every selected clip's camera, framing, subject direction and action points against its
prompt's plan, and every join of the cut against the planned hand-offs; picture lock refuses without
its reports (`shot-handoff.md` §4b).

The rest of §6 is a human pass today. At volume the remaining roadmap is: lipsync confidence scoring
(phoneme-alignment of VO vs picture), identity drift (face-embedding distance from the locked
reference), background instability (frame-difference flicker metric), and the batch checks
`slop_check.py` already runs. **None of those three exists in this skill yet** — do not claim
them in a capacity quote, and treat any "automated QC" promise as unbuilt until a script ships and
a ledger entry says so. When built, automation makes human QA an exception-review, not a
replacement for the selects pass, which is judgment.

**Planned (v2.49): the scene board's measurements.** Lens and field of view, camera height, subject size
in frame and the distances between objects, compared across the shots of a scene before any approval
request (`review-and-approval.md` §11). Not built: the board is read by eye until a script ships.

## 8. When you catch a new tell, add it here

Same discipline as the generation guardrail table: the point is that the **next** clip with the same
trigger gets the counter-move automatically, instead of the artifact being rediscovered project after
project. Log it as an episode observation (`memory/episodes/`) so the consolidation pass can promote
it — see `self-evolution.md`.

**Cross-refs:** `timing-and-performance.md` (why a clean frame still reads dead — the temporal
tells and the numbers behind V5, V5b and V5c) · `ai-generation.md` (prompt-side guardrails and the identity lock) ·
`editing-and-audio.md` (the mix and the finishing pass) · `compliance.md` (disclosure and claims) ·
`modes/ugc-volume.md` (where this checklist is a gate) · `self-evolution.md` (how a new tell becomes
a permanent rule).
