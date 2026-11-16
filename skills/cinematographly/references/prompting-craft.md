# Prompting Craft — what vendors document, what testing supports, what is ritual

**When to read this:** you are writing or revising the prompt blocks in `ai-generation.md`, deciding
whether a shot goes text-to-video or image-to-video, writing a Seedance 2.5 clip in the scene form
(§12, v2.49), weighing whether a negative list earns its characters, or a contractor hands you a
template full of `8k, masterpiece, (subject:1.3)` and you need to know what to strike. This is the **evidence layer under the house format, not a second copy
of it** — the roster, the block set (`[SPEECH]` and `[PERFORMANCE]` included), the two-path lipsync
routing, the guardrail table and the retake economics live in `ai-generation.md` and stay there.

Source tiers per `research-quality.md` §2: **[P]** PRIMARY = vendor doc, live API schema, or
peer-reviewed paper · **[S]** SECONDARY = named practitioner with a documented test · **[U]** =
[UNVERIFIED]. All checked **2026-08-28**. ⛔ **Vendor prompt documentation decays faster than almost
anything else this skill depends on** — guides are rewritten at each release and every version here
(Veo 3.1, Kling 3.0, Runway Gen-4.5, FLUX 3, Seedance 2.5, Nano Banana 2/Pro) moves
monthly. **Re-verify anything older than a quarter.** A rule quoted from a guide that no longer
exists is worse than no rule: it carries a vendor's authority without the vendor's current position.

**One tag needs explaining.** Advice that is widely published, widely repeated, and has **no vendor
documentation and no reproducible test** is filed as [U] per house convention — but this file also
calls it **folklore**, because an [UNVERIFIED] claim awaits evidence while folklore is a **ritual
inherited from obsolete tooling that nobody re-examined when the tooling changed**. Most of §2.7 is
Stable-Diffusion-1.5 habit still typed into 2026 hosted APIs. ⛔ Never upgrade a tag because a claim
sounds mechanically plausible or several guides agree — three guides agreeing is usually one guide
copied three times (`research-quality.md` §3).

**A note on the consumer-book layer, added 2026-08-28.** Four practitioner books — Ward, Turing,
Banne, Nayar — were mined for this file and are cited in the long form `[SECONDARY · Author,
*Title* — via a local extraction, read 2026-08-28]`, the same tier as **[S]**. ⛔ **Read them at the
bottom of it.** All four are **Midjourney books** — a still-image model — **none tested a video
model**, and each extraction carries a self-declared *"Confidence: Verified"* that is an editorial
label, not a held-out test; this file's [S] bar is *a named practitioner with a documented test*,
which none of them clears. A book claim is therefore used below only where it (a) supplies concrete
photographic **vocabulary**, which is a content contribution rather than a mechanism claim, or (b)
corroborates something a vendor already documents. Where a book asserts a mechanism this file has
refuted, it is filed in §2.7 as a **named carrier** of the folklore rather than dropped — knowing
*who is teaching it* is the more useful output, because a contractor's template usually arrives
from one of these four.

⛔ **ROSTER NOTICE.** The approved models are listed in `assets/higgsfield-rates.json` and owned by `ai-generation.md`
(the 2026-08-29 lock named three; it has been amended since, so never copy a list from here). This file predates that lock and still carries prompt structures, parameters and vendor quirks for
models that are **off roster**. Those passages are kept as dated evidence,
because the *comparative* finding (vendors disagree about ordering, negatives, dialogue syntax) is
what makes the file useful. **They are not executable.** Every off-roster passage below is marked
⛔ OFF ROSTER; if one is not marked and names a model outside the current roster, treat it as historical and
say so rather than acting on it. `ai-generation.md` owns the roster.

## 1. The t2v / i2v split — the highest-value structural finding here

**Vendors are unanimous and explicit: an image-to-video prompt describes motion only. It does not
re-describe the picture.** Every clip that binds an approved start frame is i2v — Step 1 authors and
approves a start frame, Step 2 animates it — so this governs every prompt on that path.
⚠️ **SUPERSEDES IN PLACE** (2026-11-05) — previously: "Nearly every shot this skill generates is i2v".
Since v2.49 a Seedance 2.5 clip is written in the scene form by default (§12), which has no start frame.

**The three prompt paths (v2.49).** Pick the path before writing a word; `prompt_lint.py` checks each one
differently.

| Path | When | What the prompt carries | Template |
|---|---|---|---|
| **Frame-led i2v** (no `form:`) | Kling, MiniMax and Wan clips; any clip that binds `start_frame:`; **every** clip in a job whose checkpoint turns on `frame-led` | motion only — the approved frame owns the look, so `[LIGHTING]`, `[ENVIRONMENT]` and `STYLE:` are refused (this section, §11 item 1) | `prompt_lint.py --template clip` |
| **Scene** (`form: scene`) | the default for `seedance_2_5` since v2.49 (and for `cinematic_studio_video_4_0`, which is not on the roster yet, so a clip on it still fails the roster check) | the whole shot: references bound one subject per line, the place, the first frame, the optics, the timed action, the light, the sound, the locks — no frame owns the look, so the prompt does | `prompt_lint.py --template scene` (§12) |
| **Multi-shot** (`form: multishot`) | a planned clip whose internal cuts the edit depends on | a locked cut list as stages, from an approved start frame | `prompt_lint.py --template multishot` (`multishot.md`) |

`frame-led` is a project switch (`assets/project-switches.json`): use it when the client approved an exact
still (a packshot, a logo end card, a label that must match a photograph), never to save credits. With it on,
the lint refuses `form: scene` and the gate wants `frame:<SHOT>` on every clip. A Seedance clip with no
`form:` and no start frame WARNs and points to §12.

- **Runway** [P]: the image *"establishes the visual starting point"*, so the prompt should *"focus
  on describing the desired motion"* — stated as a prohibition: *"**Don't describe composition,
  subject matter, lighting, or style** — the image input handles this."* Their worked ❌: *"The tall
  man with black hair wearing a blue business suit and red tie reaches out his hand."*
- **Wan** [P]: the i2v formula is literally **`Motion + Camera movement`** — *"since the image
  already defines entity, scene, and style."*
- **Luma** [P]: *"describe only what CHANGES, don't redescribe static elements."*
- **Runway** [P] on the corollary: t2v prompts *"are typically longer… because they need to describe
  both the visual elements and the motion."*

**Why it matters more than it looks:** re-describing the picture is not redundancy, it is a *second,
competing* specification of a scene the frame already settled. Where words and frame disagree even
slightly — a lighting adjective, a wardrobe detail, a lens number — the model must reconcile two
sources for one fact. That is §2.4's contradiction failure arriving through the back door. **Reusing
one block set for both paths is the named house-format mistake** and the commonest in the wild,
because formats get written for t2v first and never forked (§11 item 1). What the split does *not*
settle: whether i2v yields *better* output — no vendor publishes a controlled comparison [U]. The
**control** argument stands alone and is decisive: i2v moves composition, wardrobe, lighting and
identity out of a sampler into a frame a human approved, which is why the frame gate has ~10×
leverage (`realism-qa.md` §6).

## 2. Stop doing this

**2.1 — Quality-word stacking (`8k, masterpiece, ultra realistic, cinematic`).** Luma [P] names
offenders: *"**Avoid these terms as they degrade quality:** 'vibrant,' 'whimsical,'
'hyper-realistic'"*, plus *"vague descriptors like 'beautiful' or 'amazing'."* BFL [P]: *"**Specific
detail helps. Filler hurts.**"* Sora 2 [P] wants *"Anamorphic 2.0x lens, shallow DOF, volumetric
light"* rather than *"cinematic look"*; Google [P]: *"A simple list of keywords won't cut it."*
**The rule is not "fewer adjectives" but "upgrade them"** — replace the quality word with the
observable thing that would produce it, the same move `realism-qa.md` §1 makes on tells and
`photorealism-physics.md` makes on light. ⚠️ Gear specificity is *not* condemned: BFL [P] endorses
*"'Shot on Fujifilm X-T5, 35mm f/1.4' produces more authentic results than just 'professional
photo'"* — but that comparison is against a **vague quality phrase**, not a different focal length
(§4.1).

**The substitution bank.** §2.1 says upgrade the adjective; this is the list of upgrades, and it is
the one thing the consumer Midjourney literature is genuinely good for. Four books converge on the
same vocabulary, and they converge because it is **borrowed wholesale from photography and
cinematography** rather than invented for prompting `[SECONDARY · Ward, *Creating Cinematic Images:
Midjourney Style Guide*; Turing, *Prompt Realism Mastery*; Banne, *10,000+ Midjourney Prompts +
Digital Guide* — via a local extraction, read 2026-08-28]`. **That provenance is the whole argument
for it:** these terms sit in the captions of real photographs, so a model has plausibly learned them
as *descriptions of how footage looks* — this file's standing test for whether a control survives a
prompt at all (§4.1). ⚠️ **All four are still-image books**, none of the terms below is a documented
parameter anywhere, and §4.1's verdict governs the lot: candidate style tokens, not knobs.

| Axis | Terms that name an observable | Standing |
|---|---|---|
| **Shot size / angle** | extreme close-up · close-up · medium close-up · medium · medium long (knee-up) · two-shot · over-the-shoulder · eye-level · low angle · overhead · symmetrical | Strongest. Wan and FLUX publish their own shot-size and angle tables [P] (§4), so this axis is vendor-attested independently of the books |
| **Format / stock** | 35mm · 16mm · anamorphic · IMAX · digital cinema · VHS · Polaroid | **Attested by vendor example:** Google's own Veo worked prompt (§10) reads *"Retro aesthetic, shot as if on 1980s color film, slightly grainy"* — an era-plus-format token in a vendor's showcase. ⚠️ Each name is an artifact **bundle**, not a look; `photorealism-physics.md` §8 owns what invoking one obliges you to deliver |
| **Optics** | 35mm / 50mm / 85mm · f/1.4, f/2.8 · shallow depth of field · deep focus | Weakest as *control* — §4.1 rules these style tokens, not optics — but they are the correct **register** and cost nothing |
| **Lighting** | golden hour · blue hour · hard light · soft diffused · backlight / rim · fill · **practical** (a source visible in frame) · chiaroscuro · softbox · neon / mixed sodium | High value. *"Practical"* is the pick of them: it forces the light to have a **location**, which is exactly the failure `photorealism-physics.md` §6 names under inverse-square. Physical parameterisation — source size, distance, ratio — is the upgrade *above* this vocabulary, not a substitute for it |
| **Material / surface** | fabric weave · linen, cotton, leather · glass refraction · water droplets · metal reflection · ~~skin texture, pore detail, hair strands~~ | ⚠️ **Split by path.** Sound on a **start frame**; the struck three are refuted on the *clip* by `photorealism-physics.md` §3.3 — pores live above the video VAE's cutoff, so no prompt recovers them |
| **Era** | 1970s · 1980s · 1990s · Victorian · Classic Hollywood | Style association only — but it carries no person's name, which makes it the substitution §2.3 is asking for |

⛔ **The books' third slot does not make the bank.** Ward's triplet is *Era + Genre + Medium*, and
the **Genre** slot (*film noir, western, thriller*) has no vendor precedent, names a narrative
category rather than anything a camera did, and behaves like the quality words above. Two-thirds of
the triplet survives; the third is a mood-board caption (§2.5).

**Two practitioner corroborations arriving from the opposite direction.** Ward's stated anti-pattern
for his own framework is *"'make it cinematic' — vague; Midjourney's default cinematic is generic"*,
and Turing's is *"'make it more realistic' as iteration. Adds more generic"* `[SECONDARY · Ward;
Turing — via a local extraction, read 2026-08-28]`. Neither is evidence — but these are authors
whose commercial interest lies in prompt tricks reporting that the quality word does nothing, which
is §2.1's vendor rule reached from practice. Ward adds one claim worth separating: overusing
*"cinematic"* does not merely fail, it **collapses output toward one homogeneous mode** — a variance
argument rather than a quality one, and untested [U].

**2.2 — Long style chains and over-long prompts.** This one has a measurement. **T2I-CoreBench** [P]
(1,080 prompts, ~13,500 checklist questions) finds **all 28 tested models degrade sharply as
compositional density rises**, reasoning lagging composition further — a **structural** failure, so
no rewrite recovers it, only fewer simultaneous demands. Vendors converge from the other side:
Runway [P] *"**Overly long prompts can create conflicting requests**"* and *"There's no ideal prompt
length — focus on clarity"*; BFL [P] **30–80 words** for most work, *"Start short. Add only what
changes the image"*; Luma [P] ~100 words; Sora 2 [P] frames it as a trade, not a quality axis —
*"Longer, more detailed prompts restrict the model's creativity."* Google publishes **no length
guidance at all** for Veo [P, absence]. **Hold this model: length is how much control you spend, and
control costs variance.**

Three additions from the still-image side, all consistent with the above. The practitioner
literature lands on BFL's order of magnitude — *"excessive length — 50+ word prompts diluted;
tighter often better"* `[SECONDARY · Banne, *10,000+ Midjourney Prompts + Digital Guide* — via a
local extraction, read 2026-08-28]`. All four books independently prescribe **changing one element
per iteration**, which is BFL's *"Start short. Add only what changes the image"* [P] arriving as
workflow rather than as a rule `[SECONDARY · Ward; Turing; Banne; Nayar — via a local extraction,
read 2026-08-28]`. And most usefully, **Midjourney ships this trade as a numeric dial**: `--stylize
[0–1000]`, *"how artistic vs literal"*, is the same trade Sora 2 states in prose and VBench-2.0
measures as Creativity-versus-Controllability (§8), exposed as a parameter `[SECONDARY · Nayar,
*Ultimate Midjourney for Creative Professionals* — via a local extraction, read 2026-08-28]`. ⛔
**Midjourney-only, still images only** — no video model in the roster has an equivalent and
`--stylize` must never be quoted as though one did. Its value here is evidential, not operational:
a vendor built a knob for the trade, which is the best argument that the trade is real rather than
rhetorical.

**2.2b — This account's own measurement, and why it does not contradict the above.**
`[PRIMARY · this account's own testing across many real generations · 2026-09-07]` **1800–2100
characters** (~300–350 words) keeps the error rate low *and* carries enough detail for accurate
generation — measured on this roster, in the house block format, against real jobs.

Read against §2.2 that looks like a flat contradiction: BFL says 30–80 words, the practitioner
literature says 50+ dilutes, and 300 words is three to ten times either. It is not a contradiction,
and the resolution is the useful part.

⛔ **The vendor numbers describe a different artifact.** BFL's 30–80 words is *one free-text prompt
describing one picture* — a single undifferentiated demand surface. The house format is **seven
labelled blocks**, each a scoped demand with its own header: SUBJECT, CHARACTER, ENVIRONMENT,
LIGHTING, CAMERA, STYLE, SAFE ZONE. 2100 characters across seven blocks is **~45 words per block**,
which lands *inside* BFL's band per demand. The two measurements agree the moment you stop applying
a per-prompt number to a per-block artifact.

And that reading is the one T2I-CoreBench supports, because CoreBench measured **compositional
density** — simultaneous demands — not length. A long prompt made of short, scoped blocks is not
the object that degraded in that benchmark; a long prompt made of long blocks is. Which produces
the operational rule:

> **Length is not the variable. Demands per block is.** Spend the band on *specificity inside a
> block*, never on *more blocks doing more jobs*.

⛔ **Three honest limits on the 1800–2100 number.** It is an **error-rate** observation, not a
controlled A/B — no side-by-side at matched density is recorded, so the band is where this account
has *seen* low errors, not a proven optimum. It is **roster-bound**: `kling3_0`, `minimax_h3`,
`seedance_2_5` and the profile's image model, in this block format; nothing licenses carrying it to
a model that is not on that list. And **thin is the more common failure here, not long** — the
house templates measured 568 and 541 characters, well under the band, and everything a prompt
leaves out the model fills in differently on every take.

`scripts/prompt_lint.py` now enforces this shape rather than a bare character count.

| what | value | tier |
|---|---|---|
| the band | 1800–2100 chars, **frame prompts only** | `[PRIMARY · own testing · 2026-09-07]` |
| thin warn | under 1400 chars | `[ASSUMED]` — ~22% below the floor |
| ceiling (FAIL) | **the model's own** (§11g, v2.45): FAIL above it; above 2,500 a WARN "past the measured band" where the model takes more; 2,500 stays a FAIL marked *house ceiling, unknown vendor cap* where no vendor publishes one | vendor docs `[PRIMARY · read 2026-10-29]`; the house 2,500 `[ASSUMED]` |
| per-block budget | SUBJECT/CHARACTER/ENVIRONMENT/MOTION 70 · SETTING 60 · PERFORMANCE 55 · LIGHTING 50 · LOCATION 45 · SPEECH 40 · STYLE 35 · COLORS 30 · CAMERA/SAFE ZONE 25 | `[ASSUMED]` — derived FROM the band |
| density | 30 demands per 100 words | `[ASSUMED]` — house, see below |

Four things about that table are worth more than the numbers in it.

**The budgets take their values from the band, not the reverse.** A frame's seven descriptive blocks
sum to 345 words, which at the ~5.9 chars/word this format measures is ~2035 characters — inside the
band. ⛔ An earlier draft ran the derivation backwards and set them at 295 words, so a prompt with
*every block at budget* could not reach the floor of the band it was supposedly derived from. Caught
by writing one and measuring it.

**The band is a FRAME rule.** A clip prompt carries motion only — the approved frame already settled
subject, environment, lighting and style — so a clip that reaches frame length is re-describing the
picture, which §11 item 1 forbids. Applying the floor to clips would push a writer to pad exactly
what the fork exists to keep out. `[ASSUMED · house · 2026-09-07 — the operator's measurement was on
picture-carrying prompts; if it was taken on clips too, this split is the thing to correct.]`

**Density is a RATE, not a count.** An absolute demand count is length again in a different unit, and
it would fight the band: a well-formed prompt at only 960 characters already carries 29 demands, so
any absolute threshold low enough to bite would fire on everything inside the band. ⛔ An earlier
draft set it at 26 and immediately flagged a legitimate prompt. Per hundred words, well-formed house
prose measures ~14–18, a degenerate comma-list ~50, and run-on prose ~0 — which is the point: the
rate separates *dense* from merely *long*, and those are different faults with different fixes.

**A sourced reference removes a demand; rewording removes none.** Moving a noun into pixels is the
one edit that lowers density, which is where the reference plan (§6b) and the length rule finally
measure the same thing.

Every `.ok` sidecar carries `prompt_len`, `prompt_words` and the full `density` breakdown, so the
band can be **re-measured from real jobs rather than re-argued**. The `[ASSUMED]` rows above are the
ones to replace first.

**2.3 — Artist- and director-name invocation.** No 2026 vendor guide recommends it; every vendor
that addresses *look* prescribes concrete photographic language instead. Google [P] goes as far as
naming camera **bodies** for style (GoPro for *"immersive, distorted action feel,"* Fujifilm for
*"authentic color science"*) — the same job with a token carrying no person's name; Midjourney's
`--sref` exists precisely to make style transferable without naming anyone. For commercial work the
substitution is strictly better: reproducible, defensible, survives model updates. ⛔ No controlled
test shows artist names beat reference-image style transfer — "it works reliably" is **folklore**
[U].

**The consumer literature is where this one comes from — and it hedges itself.** Ward makes
director/DP naming a headline framework — *Wes Anderson, Deakins, Doyle, Lubezki, Kubrick, Ridley
Scott* — on the rationale that *"Midjourney's training data includes substantial film stills and
discussion of these filmmakers' styles"*, and Banne's methodology prescribes *"reference real things
— actual artists, photographers, cinematographers"* `[SECONDARY · Ward, *Creating Cinematic Images:
Midjourney Style Guide*; Banne, *10,000+ Midjourney Prompts + Digital Guide* — via a local
extraction, read 2026-08-28]`. ⛔ **Not adopted.** The training-data rationale is an assertion about
a closed corpus, no controlled comparison against `--sref` exists, and Ward rates this framework
*Triangulated* while rating his other four *Verified* — it is the weakest claim in his own book.
**What is worth importing is their caution, not their technique.** Ward flags training-data
provenance as an open ethical and legal tension; Nayar states it as a commercial control — *"style
mimicry — using 'in the style of [living artist]' raises ethical / potential legal questions"*,
alongside *"character references of real people without consent problematic"* `[SECONDARY · Nayar,
*Ultimate Midjourney for Creative Professionals* — via a local extraction, read 2026-08-28]`. Two
books that *teach* the technique warn you off it for paid work — §2.3's own reasoning, reached by
people with no incentive to reach it, and converging with Wan's don't-list on naming real people
and Sora 2's default likeness block (§6.2).

**2.4 — Contradictory instructions.** Runway [P]: avoid *"multiple scene changes or contradictory
instructions"*; Wan [P] warns against rapid scene changes in one clip; Higgsfield [S] advises **one
primary camera instruction per shot**. The self-contradiction endemic to UGC prompts: `"handheld,
natural, authentic"` + `"locked-off static frame"` + `"smooth cinematic dolly"` in one block. **One
camera behaviour per clip** — which `realism-qa.md` V8 reaches from the artifact side, and two
independent routes to one rule is good evidence it is real.

**2.5 — Three smaller ones.** *Re-describing the image in an i2v prompt* — §1; Runway lists it as an
explicit ❌. *Conversational and command phrasing* — Runway [P] flags both *"Can you please add my
dog to the image?"* and the abstract *"The subject embodies the essence of joyful greeting"*; a
prompt is a **specification**, not a request or a mood-board caption. *Temporal hedging verbs* —
Luma [P] wants **mid-action verbs**, *"running"* not *"begins to run"*, with an explicit don't on
*"temporal phrases like 'begins to' or 'starts to'"*; a 5-second clip has no room for a preamble.
Wan's own don't-list [P] adds: naming real people, rapid scene changes, expecting legible text,
overly long action sequences, and **lip-synced dialogue to specific words** on its non-audio models.

One practitioner rule sits squarely on top of Luma's: *"use active voice — 'a knight raises his
sword' beats 'a sword raised by a knight'"* `[SECONDARY · Banne, *10,000+ Midjourney Prompts +
Digital Guide* — via a local extraction, read 2026-08-28]`. Unsourced, and about a still model — but
it is the same grammatical move as the mid-action verb, **the subject performs, in the present**,
and it costs nothing to hold both.

**2.6 — Writing negatives as `"no X, no Y"`.** Google's own syntax rule forbids it [P, Veo guide]: ❌
*"Don't use instructive language or words like `no` or `don't`"* / ✅ *"Do describe what you don't
want to see"* — write **`wall, frame`**, not *"no walls"*. **The Veo negative field takes a noun
list of things to suppress, not a sentence of prohibitions**, and nearly every published negative
template violates this. Stop entirely on Runway, Luma and FLUX, where the field does not exist or
backfires (§5.1) — and see §5.2, where a mistimed negative *generates* the thing.

**2.7 — Widely repeated advice with NO evidence behind it (folklore).** All [U]; each has a
traceable origin in obsolete tooling or in copying, which is why they are folklore rather than open
questions.

1. **`(word:1.3)` / `[word]` / `{{word}}` emphasis on hosted models** — Automatic1111/ComfyUI
   *sampler-UI* syntax. No hosted model documents it; in a Veo/Kling/Runway/Sora prompt these are
   literal characters eating your budget. **Midjourney's `::` is the only documented explicit
   weighting syntax in the mainstream 2026 stack** [P] (`--no X` = exactly `X::-0.5`), and only in
   Midjourney; everything else is absent across every vendor doc fetched [P, absence across the
   set].
   ⚠️ **The transmission route is visible in the source.** Banne teaches `::` under a
   Midjourney-specific heading and then files it cross-domain as *"the same idea applies to
   text-prompt engineering (token weighting)"* `[SECONDARY · Banne — via a local extraction, read
   2026-08-28]`. That generalisation **is** the folklore forming: a real, documented,
   single-vendor syntax exported to models that have no weighting mechanism at all.
2. **"Repeat a word to increase its weight"** — zero vendor documentation. The one cited instance
   (`"No subtitles. No subtitles!"` on Veo 3 [S]) is a bug workaround MIT Technology Review reports
   doesn't reliably work (§5.2).
   ⚠️ A Midjourney book asserts the **opposite** mechanism with equal confidence and equally no
   source — *"avoid repetition — Midjourney down-weights repeated terms"* `[SECONDARY · Banne — via
   a local extraction, read 2026-08-28]`. Two contradictory unsourced mechanisms for one behaviour
   is not a dispute to adjudicate; it is confirmation that **nobody in this literature knows**, and
   it is why the item stays [U] rather than being upgraded by whichever guide happens to agree
   with you.
3. **"Put the most important thing first — early tokens weigh more"** — Runway states the opposite
   for its own models, and no vendor publishes a position-weighting mechanism at all (§3.2). Hard
   token limits (CLIP truncating at 77) are an *architecture* fact for local stacks, not a prompting
   one [S].
   Named carriers: Nayar — *"order matters somewhat — Midjourney weights earlier terms more
   heavily; placement strategic"* — and Turing's nine-layer construction, asserting that *"ordering
   affects what the model emphasizes"* `[SECONDARY · Nayar; Turing — via a local extraction, read
   2026-08-28]`. Neither cites anything, and §3.2 has the vendors contradicting each other and
   themselves.
4. **Boilerplate negative blocks** (`blurry, low quality, watermark, extra fingers, bad anatomy…`)
   on 2026 video models — inherited SD-1.5 ritual. Three vendors say the field doesn't exist or
   backfires, Google says the syntax is wrong, and the field is vanishing from platform schemas
   entirely (§5.3).
   ⚠️ Carrier note: Nayar lists Midjourney's `--no` under the generic label *"negative prompt —
   what to exclude"* `[SECONDARY · Nayar — via a local extraction, read 2026-08-28]`. `--no` is real
   and documented, but it is `::-0.5` on **one** vendor (§5.1); the generic label is precisely how
   "every model takes a negative block" travels to models where the field does not exist.
5. **JSON prompts as universally superior** — **no vendor documents a JSON prompt schema.** BFL
   offers labelled fields as one of three formats and names the **natural-language one-liner as the
   default**; Runway: *"Both work, but natural language usually gives you more control."*
6. **"Always specify 8k / masterpiece / award-winning"** — contradicted, §2.1.
   Named carrier, in a form worth recognising: Turing's *"style hybridization"* framework
   prescribes compounds — *"cinematic realism," "editorial fashion realism," "baroque realism"* — on
   the claim that *"pure photorealism can feel generic"* `[SECONDARY · Turing, *Prompt Realism
   Mastery* — via a local extraction, read 2026-08-28]`. ⛔ *"Cinematic realism"* is the condemned
   word with a second condemned word attached; the framework's whole move is to **add** style
   adjectives, which is §2.1 inverted — and Luma [P] separately warns against polished looks for
   UGC (§10).
7. **"Seed-lock your character across a series"** — contradicted, §6.3.
   Named carriers: Ward (*"--seed parameter — locks variation across iterations"*) and Banne
   (*"seed locking — `--seed [N]` for consistent variations"*) `[SECONDARY · Ward; Banne — via a
   local extraction, read 2026-08-28]`. ⚠️ Be precise about what is refuted: `--seed` on a
   **still-image** model is a narrower and more plausible claim than the one §6.3 kills. The
   folklore is the **transfer** — that same sentence retyped into a video shot list, where two
   vendors disclaim determinism and the live registry exposes no seed at all.
8. **"Name a famous cinematographer or director for the look"** — §2.3.
   Named carrier: Ward's F4, the most fully developed statement of it in this literature — see
   §2.3 for why the substitution is strictly better, and why Ward's and Nayar's own legal caveats
   argue the same way.
9. **Universal camera-move vocabularies copied between models** — folklore *as a portability claim*.
   Runway documents `snorricam`, `lazy susan`, `split diopter`; Wan documents five movements. No
   evidence terms transfer with equivalent effect — a camera vocabulary is a per-model asset.
10. **"Longer prompts always produce better results"** — contradicted by four vendors, §2.2.
11. **One house block format that works identically across all models** — vendors disagree on order,
    negatives, length and i2v content. A portable format exists only as a **content checklist** (the
    facts a shot must decide), never as a literal string. This most constrains what
    `ai-generation.md`'s format can honestly promise.

## 3. Prompt architecture that vendors actually document

**3.1 — The structures, as published.**

| Vendor | Documented structure | Order? |
|---|---|---|
| **Veo 3.1 blog** [P] | `[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance]` — *"five-part formula for optimal control"* | Camera **first** |
| **Veo Vertex guide** [P] | Subject, Context, Action, Style, *(optional)* Camera motion, Composition, Ambiance | Camera **fifth, optional** |
| **Runway Gen-4 t2v** [P] | `[Camera] shot of [subject] [action] in [environment]. [Supporting descriptions]` | *"the order… do not matter"* |
| **Runway i2v** [P] | `The camera [motion] as the subject [action]. [Additional]` | *"far less important"* |
| **Wan** [P] | t2v `Entity + Scene + Motion` (+aesthetic +stylisation); **i2v `Motion + Camera movement`** | Fixed |
| **Luma Ray3** [P] | `[SUBJECT] [MID-ACTION VERB] in [SETTING], [SECONDARY MOTION], [CAMERA], [LIGHTING/MOOD]`, ~100 words | Yes |
| **Sora 2** [P] | Prose scene → Cinematography → Actions → Dialogue | Yes, as sections |
| **FLUX image** [P] | `[SUBJECT], [LOCATION], [STYLE], [CAMERA], [LIGHTING], [COLORS], [EFFECT], [ADDITIONAL]` — *"an aid, **not a rule**"* | *"Prompt order matters"* |
| **FLUX 3 video** [P] | Core summary → Scene → **Subject description (identical across shots)** → Dynamic narrative (timecoded) → Audio → Style & colour | Yes |
| **Nano Banana** [P] | `[Subject] + [Action] + [Location/context] + [Composition] + [Style]` | Yes |
| **Seedance** | 5–6 part: Subject+Action → Scene → Style → Camera → Audio | ⚠️ below |

⚠️ **The Seedance caveat.** ByteDance/Volcengine *do* publish official guides (BytePlus ModelArk
1631633 / 2168087 / 2222480 / 2607689; Volcengine 82379/2222480) — **none could be rendered**, all
JS-only SPAs returning navigation shells. Every Seedance structure in circulation, including the
widely cited "official six-part formula", arrives through relays that **do not quote or link the
source**; Segmind's page, asked directly, admitted *"This article does not cite or link to an
official ByteDance document."* Treat every Seedance specific as [S] at best — the docs' *existence*
is [P], their contents are not. Textbook `research-quality.md` §3: apparent convergence, one
ancestor.

**3.2 — Does block order matter? Two vendors state opposite rules, and that contradiction is the
finding.** BFL [P]: *"Prompt order matters"*, with a causal mechanism — when environment detail
lands too early, **FLUX pulls the framing wider than intended**; fix is subject first, context
after. Runway [P]: *"the order in which elements are introduced in a prompt do not matter."* Google
[P] contradicts *itself* — Cinematography is **first** in the Veo 3.1 blog formula and
**fifth-and-optional** in the Vertex guide, same company, same model family. **Read:** ordering is a
**weak, model-specific effect with exactly one documented concrete case** (FLUX framing), not a
universal mechanism — no vendor publishes the position-weighting story that would make it one. ⛔ **A
house format that treats block order as a control surface is over-fitting**; defend the house order
as *legibility for the human writing it*, which is real and sufficient. The one ordering effect with
a mechanism: BFL says **front-load the text description** when you need rendered text, and Google
says *"start a prompt with a strong verb that tells the model the primary operation"* for image
edits [both P] — both declare the **kind of job** first, neither is about emphasis.

⚠️ **The circulating version of this claim is stronger than any vendor's.** Turing prescribes a
**nine-layer** order — subject → subject details → action → wardrobe/material → setting → lighting →
camera/lens → atmosphere → style modifiers — as a rule governing emphasis `[SECONDARY · Turing,
*Prompt Realism Mastery* — via a local extraction, read 2026-08-28]`. It is worth noting for what it
resembles: it is close to FLUX's published image structure (§3.1), **which BFL itself labels *"an
aid, not a rule"***. The consumer restatement drops the vendor's hedge and keeps the list. Adopt the
layers as a **content checklist** — the facts a shot must decide, the only portable form §2.7 item
11 allows — never as an emphasis mechanism.

## 4. Camera control

Every vendor accepts camera language in text and publishes a vocabulary; the question is whether a
*parameter* sits behind the words, and mostly none does.

| Vendor | Text camera language | Parameter / preset |
|---|---|---|
| Runway | Extensive published list [P] | None; Gen-4.5 marketed as taking *"detailed camera choreography"* in-prompt |
| **Kling** | Yes | **Real numeric `camera_control`** [S, schema mirrors] |
| Veo | Movement, composition, lens/focus categories [P] | None [P] |
| Luma | *"be explicit about directional movement"* [P] | Keyframes + loop only |
| Wan | Full shot-size / angle / lens / movement tables [P] | **None** — 2.7 *removed* `shot_type`: *"Control shot structure with natural language"* |
| Sora 2 | Yes, with specificity guidance [P] | None |
| FLUX 3 | 14 documented categories [P] | None |
| Higgsfield | — | `preset_id`, `speedramp` / `genre` enums [P, live registry] |

**Kling is the outlier worth exploiting** when a series needs the *same* move ten times. Schema [S —
third-party mirrors (PiAPI, AI SDK, Segmind) agreeing; Kling's own API reference is an unrenderable
SPA]: `camera_control.type` ∈ `simple | down_back | forward_up | right_turn_forward |
left_turn_forward`, `config = {horizontal, vertical, pan, tilt, roll, zoom}`, **each in [-10, 10]**.
The only *numeric, reproducible* camera control in the mainstream stack — for an identical push-in
across ten clips a number beats an adjective. Also mirrored: `cfg_scale` [0,1] default 0.5, *"Not
supported by V2.x models"*; `image_tail` requires `mode: 'pro'`.

**4.1 — Does "35mm lens" do anything measurable?** No vendor makes a mechanistic claim and no
reproducible test exists either way. BFL's camera-terms page lists *"Wide angle (24mm)"* and
*"Telephoto compression"* as **conceptual terms** with no technical statement [P]; Google frames
lens language as effect vocabulary and camera **bodies** as explicit *style association* [P].
**Verdict, flagged as inference not vendor claim: `35mm` is a style token, not an optic** — the
effects vendors attribute to lens terms (compression, DOF, distortion) are the same effects they
attribute to plain-language terms, and no vendor anywhere claims a geometric transformation.
**Consequence:** `35mm` and `85mm` are not two settings of one knob but two different style tokens,
so keep gear names for the *look* they associate, and when a shot needs a specific optical
behaviour, **say the behaviour**. Which behaviour it wants is `cinematography-craft.md`'s call.

The still-image literature is unanimous the other way — Turing makes *"35mm / 50mm / 85mm, f/1.4 /
f/2.8"* a pillar of realism prompting `[SECONDARY · Turing, *Prompt Realism Mastery* — via a local
extraction, read 2026-08-28]` — but unanimity here is four books restating one convention with no
test between them, so it does not move the verdict. Keep the terms: they are the right register and
they cost nothing (the bank is in §2.1). Just do not spend a retake on 50mm-versus-85mm.

**4.2 — The static-camera problem, directly relevant to UGC.** Runway [P]: *"video models are
designed to create immersive, high-fidelity motion,"* which makes a truly locked-off shot **hard**.
The documented fix is **reinforcement, not negation** — they warn specifically against `"No camera
movement. The camera doesn't move"`:

```
The camera is entirely motionless for the duration of the scene, with movement only occurring from the subject.
```

Kling's answer is mechanical rather than linguistic: the **static brush** *"fix[es] pixels in the
brushed areas, preventing camera movement"*, recommended *"at image bottom to avoid unintended
camera movement"* [P].

## 5. Negative prompts

**5.1 — Support is genuinely split, and vendors say so plainly.** *Not supported or actively
discouraged:* Runway [P] — *"Gen-4 is designed to interpret prompts that describe what **should
happen**… not what should be avoided"*; Luma [P] — *"**Negative prompting is counterproductive**"*,
these are *"positive only"* models; BFL [P] — *"**Most FLUX models do not support negative
prompts**"* plus *"AI models **struggle with negation**"*, prescribing a **"Replacement Strategy"**
(name the positive alternative) and flatly **"NO negative prompts"** in its agent-skills repo; Nano
Banana [P] — *"**Use positive framing**… **'empty street' instead of 'no cars'**"*; Sora API [P] —
no such parameter. *Supported as a real field:* Kling `negative_prompt` ≤2,500 chars [S, mirror];
One vendor caps `negative_prompt` at ≤500 chars, auto-truncated [P] — but its image sibling **does not** support
it while a sibling image model does, so support varies *within one vendor's own line*; Veo
`negativePrompt`; Midjourney `--no` = `::-0.5` [P]. ⚠️ The much-quoted Kling default `"No sudden
movements, no fast zooms."` is **Segmind's wrapper default, not Kling's** [P]. Where the field
exists, write a **noun list** (§2.6) — its cap is the model's, and many models have no field at all (§11g); practitioner negative templates [S — Artlist, illustrative
before/after, explicitly *not* quantified] read plausibly but carry **no controlled test**, and
their Veo set contradicts Google's own syntax rule.

**5.2 — The failure mode: negatives that summon the thing.** Real, peer-reviewed, mechanistically
explained [P — Wu et al., *"Understanding the Impact of Negative Prompts"*, ECCV 2024,
arXiv:2406.02965]: (1) **delayed effect** — *"The impact of negative prompts is observed **after**
positive prompts render corresponding content"*; (2) **reverse activation** — *"introducing a
negative prompt in the early stages **results in the generation of the specified object**"*; (3)
**mechanism** — an *inducing effect* on the estimated noise direction plus a *momentum effect* that
locks it in; (4) **deletion works by neutralisation**, *"a mutual cancellation effect in latent
space with positive prompts"* — which is why negating something **structurally entangled with your
subject** damages the subject. **Translation for a director on hosted APIs: you do not control
negative timing — the vendor picks it**, so the reverse-activation risk is real and un-tunable. That
is the strongest argument for keeping negative lists **short and structurally peripheral**: suppress
*background clutter and era-anachronistic props*, never *the subject's hands or face*. It cuts
across `ai-generation.md`'s guardrail table, whose period-setting row is already the right shape
while its hands row is exactly where a negative would be wrong. **The field example is Veo's
burned-in subtitles** [P — MIT Technology Review, 2025-07-15]: *"no subtitles"* **doesn't work
reliably**, Tuhin Chakrabarty (named) notes negatives are generally less effective than positive
instruction, Google claimed fixes, users kept reporting it a month later, and every documented
workaround is post-hoc.

**Independent practitioner corroboration, from outside the literature that produced the result.** A
Midjourney guide reports the same effect as a plain observation: *"negation — 'without people'
sometimes adds people"* `[SECONDARY · Banne, *10,000+ Midjourney Prompts + Digital Guide* — via a
local extraction, read 2026-08-28]`. That is reverse activation described by someone who had never
heard of it, on a different model family — the kind of convergence `research-quality.md` §3 *does*
count, because the observation has a different ancestor from the paper. ⛔ Their fix does **not**
port: Banne routes the exclusion to Midjourney's `--no`, which is `::-0.5` on one vendor (§5.1) and
does not exist on the video roster. The portable half is the diagnosis, not the remedy.

**5.3 — The direction of travel, from a live registry.** Querying the Higgsfield model registry on
**2026-08-28** [P, live platform schema], across ~30 current image and video models: **not one
exposes `negative_prompt`**; **not one exposes `seed`** (it survives only on 3D mesh models);
`cfg_scale` appears on exactly one video model; camera control ships as `preset_id` and enums, not
numerics. **Read: the industry is moving away from negative prompts and seeds as user-facing
controls, toward references and presets.** A house format organised around a negative block and a
seed field is optimising a shrinking surface — and this explains why `ai-generation.md`'s
observation that this stack exposes no negative field is the trend, not an oversight.

## 6. Control beyond text

⛔ **And an emotion word is not a lever either.** Naming a feeling — "stressed", "angry", "joyful" —
is an unfalsifiable instruction: nothing in the returned frame can confirm or refute it, so nothing
can be iterated. Name the **circumstance** and the **physical action** instead, and cast the state
positive-or-neutral to begin with (`emotional-journey.md` §4).

⛔ **Before the levers: timing is not one of them.** No model on the roster honours a frame count, a
millisecond, or an easing word in a prompt. Aliveness is bought by naming *behaviours* as content
(a blink, a glance, a swallow) and the *register* they are played in (slow onset and held apex vs
fast and big) — never by specifying their duration. The evidence, and the short aliveness block that
belongs in a `[PERFORMANCE]` prompt, are `timing-and-performance.md` §6A and §9.

**6.1 — Start/end frame conditioning, the best-documented lever in the survey.** In this pipeline: `end_frame:` in the clip's prompt file, `gate.py approve endframe:<SHOT>`, and preflight binds it — but ⛔ **not every model has a true first or last frame**; the per-model table is in `ai-generation.md` (the roster section) and `assets/higgsfield-rates.json` → `call_contract`.

| Vendor | Mechanism |
|---|---|
| **Veo 3.1** [P] | `image` + `lastFrame` interpolation, *"perform a smooth transition"* with synchronised audio; `durationSeconds` **must be 8** with reference images or 1080p/4k |
| **Luma Ray3** [P] | Start **and** end keyframes; *"describe only what CHANGES"* |
| **FLUX 3** [P] | `startframe` / `start+end` / ordered **`keyframes` waypoints** — *"Order matters: the frames are read as a timeline"*; keep frames related *"so the interpolation has a plausible path"*; timestamped requests need an explicit `duration` |
| **Kling** [S] | `image_tail`; requires `mode: 'pro'` on most models |
| **Sora 2** [P] | `input_reference` conditions the **opening frame only** |

⛔ **Moving things across a start and an end frame: both or neither** (`world-design.md` §5, since v2.42). A bird,
boat or vehicle added to each frame separately leaves the model to invent the path between them. This is how a demo
got flocks and swoops nobody asked for. So a mover rides both frames, at the position its heading and speed explain,
or neither. A mover in the end frame alone is refused, and an image edit may never add one.

**6.2 — Reference images for character and style.** Veo 3.1 [P]: up to **3** references, syntax
`Using the provided images for [elements], create [shot description with action and dialogue]`;
`personGeneration` is forced to `allow_adult` whenever references, i2v or interpolation are used.
Runway Gen-4 [P]: up to **3**, inline **`@tag`**. Kling [P]: **Element Library** — elements from
**2–4 images** (front-facing recommended) or a **3–8s single-character video** that *also
auto-extracts native voice*, invoked **`@ElementName`**; subject binding takes up to 4 images,
ideally *"front, side, back, and a detail shot"*; hard constraint — elements *"must appear in the
reference frames."* Nano Banana Pro [P]: blends **6–14** unconnected images preserving identity
*"even when they appear together in a group"*, with Google's own hedge that consistency *"may
vary."* Sora 2 [P]: `characters` exists but **human likeness is blocked by default**, as are human
faces in input images — materially limiting for talent-led UGC. Seedance [S, unverified per §3]:
reportedly 30–50 references; one relayed point survives its tier because it is *reasoning*, not spec
— *"A reference image carries **everything** in it… If you only want the jacket, say so."* That is
§1's lesson applied to references.

**The start-frame step has its own reference system, and it is the best-specified thing in the
consumer literature.** Midjourney's `--sref` takes an image URL or a numeric style code with a
**strength dial `--sw [0–1000]`** and accepts multiple references to blend; `--cref` takes a
character image with **`--cw [0–100]` trading face fidelity against outfit and accessories**
`[SECONDARY · Nayar, *Ultimate Midjourney for Creative Professionals*; Ward, *Creating Cinematic
Images: Midjourney Style Guide* — via a local extraction, read 2026-08-28]`. ⛔ **Midjourney-only
syntax on a still-image model.** It belongs to Step 1 — authoring and approving the start frame —
and none of it survives into a video prompt. It earns a place here for one detail no video vendor
offers: a **numeric strength on the reference**, and in `--cw` an explicit axis for *which part* of
an identity is held. That is the shape a reference control should have, and worth recognising when
the roster is next reviewed. Nayar's own hedge matches Google's: `sref` / `cref` are *"still
maturing; consistency imperfect."*

**6.3 — Seeds are far weaker than folklore assumes, and vendors say so.** Google [P]: `seed`
*"doesn't guarantee determinism but slightly improves it."* Wan [P]: *"model generation is
probabilistic, **the same seed does not guarantee identical results**."* Sora API [P]: no seed
parameter. Higgsfield registry [P, live]: none on any image or video model. Replicate [S] reports
the *opposite* problem on Veo 3 — unusual consistency across runs regardless of seed — and advises
**changing the prompt substantially to explore**. ⛔ **A seed is a nudge, not a lock. Do not build
shot consistency on it** (§11 item 6).

**6.4 — Explicit motion control, where genuine new capability lives.** **Kling Motion Brush** [P]:
up to **6 elements** with drawn trajectories — *"The element's movement will **strictly follow** the
drawn trajectory"* in direction and length; one brush per element, one connected area, brush only
the key part, and **match the text prompt to the motion** (`element + motion` phrasing);
vendor-stated limits — degrades on poor image quality and fast movement, and **hands are "imprecise
or blurry"**, the same finding `realism-qa.md` V6 reaches from the artifact side. **Runway Act-Two**
[P]: **no text prompt at all** — a driving performance video plus a character image (transfers face,
expression, gesture, adds camera motion) or character video (face only, gesture control
unavailable); max 30s; documented failures include *"Certain expressions, such as sticking out a
tongue, are not supported"* and a *"reversed boomerang effect"* on overrun; best practice is single
subject, face visible, waist-up, no cuts, *"Start in a similar pose to your character input."*
**VACE** (Wan, open weights) [P, arXiv:2503.07598]: the real ControlNet-for-video — depth,
grayscale, pose, scribble, optical flow and layout carried as RGB videos, plus masks and references,
via a Video Condition Unit `V=[T;F;M]` with task composition. The only path to true pose/depth
conditioning, and it **requires a local/ComfyUI stack**.

**6.4b — Object permanence: a thrown thing has to land** (a supplement ad job, 2026-10-27). "Keys tossed in passing" made the
keys teleport: the model threw them out of frame, then put them back on the counter. The clip passed selects with the
note "keys tossed … keys at rest", because the review looked at three frames of the shot and missed the frames between.
When an object is in the start frame and ends on a surface, write the **release** and the **landing spot** as content:
*"fingers open, the keys drop straight down onto the counter below"*. Avoid *toss*, *throw*, *fling* and *flick* unless
the landing is in the prompt, or the words say it leaves the frame for good. `prompt_lint.py` refuses a throw with no
landing (idioms such as "throws a punch" pass); the QA side is `realism-qa.md` V7b. The one-variable correction rule did
its job on the fix: the lint caught a second change in the regen, and with it reverted the regen worked first time.

**6.5 — Guidance, and a silent prompt rewriter.** Strength/denoise controls are nearly absent from
2026 hosted video APIs (exceptions: Kling `cfg_scale` [0,1], not on V2.x [S]; one Higgsfield video
model [P, live]). ⛔ **OFF ROSTER — historical.** Alibaba's `prompt_extend` was a boolean defaulting
to `true`: on Wan the prompt was silently rewritten by an LLM before generation [P], with Alibaba's
own advice to *"disable for fine detail control."* An A/B run with it on tested the rewriter, not the
prompt. **Kept because the class of hazard is not vendor-specific** — a silent server-side prompt
rewriter makes any bake-off uninterpretable, so ⛔ **before the first bake-off on any model, check
whether it rewrites prompts and record the answer in the manifest.** That question survives; the vendor-
flag does not.

> **If a client asked for a named director's look**, `style-transfer.md` converts the name into
> parameters — because the name in a prompt does nothing, but one dominant motivated source, a
> repeated narrow lens set and a hue-only LUT are all suppliable.

> **If the move is what is failing, the answer is probably not in this file.** Camera paths hit the
> same wall as lighting ratios: a prompt biases motion and cannot specify it. `motion-design.md` has
> the mechanisms that do — FLF, motion transfer, video references, multi-shot, ramping.

## 6b. Reference-indexed prompting — when the prompt addresses inputs instead of describing them

Verified in the generation UI 2026-08-29. **MiniMax H3 accepts up to 9 images and elements, 3 videos
and 3 audio files in one generation**, and its prompt field instructs you to *"Describe the video.
Refer to inputs as Image 1, Video 1, or Audio 1. Add elements using @"*
[PRIMARY · Higgsfield MiniMax H3 References panel · checked 2026-08-29].

That is a different prompting grammar from everything in §3, and it is the concrete mechanism behind
this skill's standing rule — **reference the nouns, prompt the verbs** (`character-and-props.md`
§8). Instead of *"a woman in a grey knit jacket in a sunlit bedroom, holding the amber bottle"*, the
prompt becomes *"Image 1 picks up Image 3 and turns toward the window in Image 2"*. The nouns are
approved assets carrying their own pixels; the sentence carries only the action.

Why this matters more than it looks:

- **It removes the failure mode §1 and §7 are both built around.** Wardrobe, room and prop are no
  longer sampled from a description each run — they are supplied. The consistency question stops
  being "did the model interpret my words the same way" and becomes "did I attach the right file".
- **It changes what a prompt is for.** With references attached, prompt length spent re-describing
  appearance is not just wasted (§2) — it actively competes with the reference. Describe motion,
  blocking and beat; let the images carry identity.
- **The slot budget is a design constraint, not a footnote.** Nine image slots is generous but
  finite, and it maps almost exactly onto the `_reference/` folder this skill already specifies
  (`pm-workflow.md`): character · wardrobe · props · environment · light for the image slots,
  `motion/` for the video slots, and the voice for the audio slots. **One reference carries one
  attribute** (`refinement-loop.md` §1) is what keeps you inside the budget and what makes a failure
  attributable when the output is wrong.
- ⛔ **Do not assume other models take this grammar.** Slot counts, whether references are indexed at
  all, and how the prompt addresses them are per-model. Check the References panel before writing a
  prompt that says "Image 3", or the reference silently becomes decoration.

**Seedance 2.5 takes the same grammar, with the vendor's spelling `@Image 2` / `@Video 1` /
`@Audio 1`**, and a far larger budget: up to 30 images (each up to 4K), 10 videos and 10 audio
clips, videos and audio each at most 30 s combined `[VENDOR · Higgsfield Seedance 2.5 "New
capabilities (Part 2)" deck, supplied 2026-10-25 — not measured here]`. It lives in
`assets/higgsfield-rates.json → call_contract → seedance_2_5 → ref_limits`, and `prompt_lint.py` warns
past it per model. Three rules ride with it (`multishot.md` §4):
- **The number is a position, not a name.** `@Image N` is the N-th image in the call's `medias`, in the
  order `gate.py preflight` emits (the approved start still first when it is a reference, then `refs:`
  in file order). Since 2026-10-25 `gate.py` refuses a call that binds the same pictures in another
  order whenever the linted prompt uses a positional tag — a swap puts one character's face on another.
- **One subject per binding line**: *"Mika corresponds to @Image 2. Use only the appearance,
  hairstyle, and clothing."* Never a range (*"@Images 1 through 4 define four characters"*); the lint
  refuses it.
- **A tag only where that subject is present** — the model tries to force a mentioned reference into
  frame `[VENDOR · Seedance 2.5 Prompt Writer]`.

**The slot is designed at the shot, not at the search box.** A reference the shot needs but nobody
has sourced yet is written into the prompt's own `refs:` block as a shopping-list entry —
`- role: image, what: environment, need: rustic kitchen window light`. `prompt_lint.py` FAILS a
prompt in that state (a declaration is not a reference), and `refsource.py brief` reads every one of
them, turns it into a Pixabay search built from that shot's `need:` or its own `[ENVIRONMENT]` /
`[LIGHTING]` / `[SUBJECT]` words, fetches candidates with provenance, and waits for a human to pick
(`stock-sourcing.md` §9b). The point is order: the query comes from the shot, so the picture answers
the shot, and both happen before the model is asked for anything.

The open question worth a bake-off: **MiniMax H3's audio slots may make it a Path A model** —
voice-first lipsync driven by supplied audio, at 2K, and the cheapest per second of the roster at that resolution (`scripts/rate_card.py`). The same routing was served by a since-retired model at a lower resolution and a higher rate — which
now makes H3 or Seedance 2.5 the only options, not the cheaper alternative. Unverified for
articulation quality;
worth testing before the next non-English batch.

## 7. Consistency across ten-plus clips, ranked by reliability

Ranked by (a) whether a vendor documents it as a consistency mechanism *with stated limits*, and (b)
whether it **removes** randomness rather than merely biasing it.

**Tier 1 — move the decision out of the sampler.**
1. **Author the start frame, approve it, then i2v.** [P — inferred directly from Runway and
   Luma i2v guidance] Highest reliability: wardrobe, location and framing become *approved assets*
   rather than sampled outcomes. Already this skill's default; §1 is why it works.
2. **Vendor reference/element systems with a bound multi-view set.** [P] Kling's Element Library is
   the most fully specified; Runway `@tag`, Veo Ingredients, Nano Banana Pro. Reliable but
   **vendor-hedged** — Google says consistency *"may vary"*, Kling requires elements to *"appear in
   the reference frames."*

**Tier 2 — real but narrower.**
3. **Performance transfer (Act-Two) for talking heads.** [P] Cannot drift — there is no text prompt
   to drift. Constrained: 30s, waist-up, no cuts.
4. **A fixed subject-description string copied verbatim into every shot.** [P — FLUX 3's video
   schema names exactly this field: *"a fixed description held identically across shots"*]. Cheap,
   vendor-specified, costs nothing; won't survive a model that ignores it, but strictly better than
   re-authoring per shot.
5. **First-frame chaining** (last frame of N → start of N+1). [P for the mechanism — Veo
   `lastFrame`, FLUX keyframes, Kling `image_tail`] Strong *within* a continuous action; degradation
   accumulates across hops and the vendors' own framing (interpolating between *related* frames)
   implies it is not a ten-clip spine. **Use in pairs** — how `ai-generation.md` already scopes END
   FRAME reuse.

**Tier 3 — do not rely on it.**
6. **LoRA / custom training** — strongest identity lock where available, but **no hosted video model
   in this survey exposes it** [P, absence]; closed identity features are not user training. Not an
   option for a hosted ad pipeline in 2026.
7. **Seeds** — §6.3; vendors explicitly disclaim determinism.
8. **Prompt wording alone** (*"the same woman, 28, brown bob…"*) — no vendor claims this maintains
   identity, and Runway explicitly says **not** to re-describe the subject in i2v.
   `character-and-props.md` owns what a description must contain; this says only that the
   description is not the lock.

## 8. Prompt adherence and benchmarks — what they can and cannot tell you

**No benchmark answers "which model follows my ad brief best."** **VBench-2.0** [P,
arXiv:2503.21755] is the most relevant — 18 dimensions across Human Fidelity, Creativity,
**Controllability** (dynamic attributes, spatial relations, motion order, complex plots, camera
motion), Physics and Commonsense, shifting from VBench-1.0's *"superficial faithfulness"* to
*"intrinsic faithfulness"*, with **validated human alignment** (Spearman ~90%+). Findings that
matter: most models score **poorly on controllability**; **~80% failure rate on simple attribute and
spatial changes**; and a documented **trade-off between Creativity and Controllability** — the
benchmark-side echo of §2.2's length trade. Authors' stated limits: *"large models cannot serve as
reliable evaluators"* for some dimensions (notably human anatomy), and a fixed prompt set with **no
UGC, vertical or dialogue category**. **Artificial Analysis Video Arena** [P, methodology] runs
Bradley-Terry MLE over pairwise human votes — ⛔ **it does not measure prompt adherence at all**:
*"Quality assessment relies solely on user preference votes."* It answers "which output do strangers
prefer", not "which model did what I asked." **T2I-CoreBench** [P] is the image-side evidence behind
§2.2; **GenEval 2** frames the problem as *"benchmark drift"* [S — only the listing was reachable].
**Practical stance, identical to the roster's:** run **your own fixed reference set** — eight of
your actual shots, same start frames, same VO — against candidates quarterly. Every benchmark above
is a worse predictor of your results than five minutes of your own A/B; the literature does not
replace the bake-off in `ai-generation.md`, it explains why the bake-off is necessary.

## 9. The audio and lipsync prompting path

`ai-generation.md` Step 4 owns the **routing decision** and the recipe. This is only about **what
the text prompt controls**, which is narrower than it looks and differs by path.

**9.1 — Duration is the real timing control, and a hard constraint.** Wan [P]: `audio_url` accepts
WAV/MP3, **2–30s, ≤15MB**; *"If audio exceeds video duration, only the first portion is used;
shorter audio results in silent trailing sections."* Kling [P]: voice binding takes **5–30s** of
clean single-speaker audio. **Write the line to fit the clip, not the clip to fit the line** — BFL
[P]: *"**A short line in a longer clip is safer than copy written to fill every second**"*, with the
target *"the voiceover speaks once and aims to finish by 8 seconds"*; Replicate [S] keeps Veo 3
dialogue to ~8s *"to avoid unnaturally rapid speech"*; Sora 2 [P]: *"limit exchanges to a handful of
sentences."* This is a **script-side** constraint before it is a prompt-side one — `script-craft.md`
and the duration script enforce it; by prompt-writing time it is too late. **Timestamps are the only
documented fine-grained control:** Veo 3.1 `[00:00-00:02] …`, FLUX 3 timecoded per-shot narrative
requiring an explicit `duration`, Kling `Shot 1 (3s): …` [all P].

**9.2 — Dialogue syntax is vendor-specific and it matters.**

| Vendor | Documented syntax |
|---|---|
| **Veo 3.1** [P] | Quotation marks: `A woman says, "We have to leave now."` plus `SFX:` and `Ambient noise:` prefixes |
| **Replicate on Veo 3** [S] | Prefers **colon, no quotes**: `A guy says: My name is Ben` — a subtitle-suppression tactic |
| **Sora 2** [P] | Dialogue in a **labelled block below** the visual description, speaker labels, alternating turns |
| **Kling 3.0** [P] | Inline per character: `Mom (softly, in a surprised tone): "…"` and `@Character says, "…"` |
| **FLUX 3** [P] | Exact words in quotation marks; **mark voiceover explicitly** as off-screen |
| **Seedance** [S, unverified] | Bracket routing: `( )` music-ambient, `< >` SFX, `{ }` dialogue, `【 】` on-screen subtitles |

⚠️ **The Veo tension:** Google documents quotation marks; Replicate's workaround uses colons
*specifically to avoid* triggering burned-in subtitles. Both defensible — they optimise different
things. Log which you used in the shot manifest.

**9.3 — What the prompt controls in an audio-driven model.** Hedra Character-3 [P]: **audio is the
primary driver** — *"your audio quality heavily dictates the output"*; the model maps phonemes and
micro-expressions from the speech. The **text prompt controls demeanour and gesture restraint, not
lip-sync**; the documented failure is *"overly dramatic or unnatural hand gestures"*, fixed by
*"explicitly restrain[ing] their movement"*. Character-3 is **locked-camera** — the prompt does not
control camera or background. OmniHuman-1.5 [P, arXiv:2508.19209]: the text prompt is *"an optional
text prompt describing the desired character behavior"*; an **Analyzer MLLM** infers *"persona,
language style, speech content, emotion, intent, and environmental context"* and a **Planner MLLM**
produces *"an action plan structured as a sequence of shots"*, the ablation reporting text-following
*"on par with the pre-trained general model"*. Kling [P]: binding a voice file to a multi-image
element yields *"more precise lip-syncing and expression-driven performance"* — the element system
doubles as a voice lock. **The practical rule** [P-grounded synthesis, Hedra + OmniHuman]: **on the
audio-driven path the prompt is a performance note to an actor whose lines are already recorded** —
demeanour, energy, gesture scale, gaze. Not lip timing, not camera, not wardrobe. Tighter and more
useful than "describe the mouth", and it maps exactly onto `direction.md`'s performance card.

**9.4 — Voice direction vendors specify.** BFL's is the most concrete [P] — anchor a voice on five
axes rather than personality adjectives: **Person** (age, accent) · **Register** (*"low, mid,
bright, soft, rough"*) · **Recording** (close/dry, across a room, phone mic) · **Delivery**
(conversational, hesitant, practical) · **Guardrails** (*"No announcer delivery, no sales voice"*).
Also [P]: layer sound as **speech / ambience / effects / music**; *"Name sounds that have a source
in the frame or just outside it"*; a visible speaker *"gives FLUX 3 a face to lip-sync"*; for
multilingual work label each language beside its line and keep segments short enough for natural
pauses — a direct hit on the mispronunciation problem in non-English dialogue. ⚠️ **An inconsistency worth flagging
rather than resolving:** BFL's *"Guardrails"* example is itself negative phrasing, inside a doc set
that elsewhere says FLUX does not support negation. It may be a genuine exception — it steers a
*style axis* rather than deleting an object, precisely the case §5.2 says is safe — but **BFL does
not explain it and no test exists either way** [U].

**9.4b — The voice is one string, written once (v2.49; HFF-02).** Two festival teams arrived at the same
habit on their own `[SECONDARY · festival study 2026-11-05]`, and it is now the house rule for any clip whose
model speaks a line:
- **Write the voice once**, in the character's sheet (`_reference/CHARACTER-<name>.md`), on the five axes
  above: person, register, recording, delivery, guardrails. That sentence is the voice's identity.
- **Paste it word for word** into every clip that speaks, as a `VOICE:` line in `[SPEECH]` (or `[AUDIO]`).
  Re-wording it per clip is a new voice each time, the same way a re-authored character block is a new face
  (§11 item 5).
- **The scene's emotion goes on its own line**, under the voice and never inside it — *"quietly relieved,
  trying not to show it"*. The identity stays fixed; only this line changes between scenes.
- **Time the silences** between lines, as you time the lines: `NAME: "…"` at stated seconds, then the pause
  before the next one. A pause the prompt does not name is one the model fills.

`prompt_lint.py` reads a `NAME: "…"` line in `[SPEECH]` or `[AUDIO]` as speech and WARNs when no `VOICE:` line
is present. Speech still goes through the voice gate: `gate.py` refuses `generate_audio: true` on a clip with
lines until `audio` is approved (`ai-generation.md` Step 4). Whether a scoped audio reference holds the timbre
better than the string is an open arm of the dialogue bake-off (HFF-14, `ai-generation.md` Step 4).

## 10. Vendor structures, verbatim

Reproduced for copying. All [P].

```
VEO 3.1 — Google Cloud's worked example
Medium shot, a tired corporate worker, rubbing his temples in exhaustion, in front of a bulky 1980s computer in a
cluttered office late at night. The scene is lit by the harsh fluorescent overhead lights and the green glow of the
monochrome monitor. Retro aesthetic, shot as if on 1980s color film, slightly grainy.

Timestamps:  [00:00-00:02] Medium shot from behind… [00:02-00:04] Reverse shot…
References:  Using the provided images for [elements], create [shot description with action and dialogue]
Negatives:   wall, frame          <- NEVER "no walls"
Dialogue:    A woman says, "We have to leave now."   ·   SFX:   ·   Ambient noise:

RUNWAY   T2V:  [Camera] shot of [a subject/object] [action] in [environment]. [Supporting descriptions]
         I2V:  The camera [motion description] as the subject [action]. [Additional descriptions]
Worked example:  a handheld camera tracks the mechanical bull as it runs across the desert. the movement disturbs
                 dust that trails behind the mechanical creature. cinematic live-action.
Locked-off:      The camera is entirely motionless for the duration of the scene, with movement only occurring
                 from the subject.
No cuts:         Continuous, seamless shot

         I2V:    Motion + Camera movement
         Audio:  Entity + Scene + Motion + Sound description

LUMA RAY3 (~100 words, present tense, with secondary consequences — wind, fabric, dust, ripples)
         [SUBJECT] [MID-ACTION VERB] in [SETTING], [SECONDARY MOTION/CONSEQUENCE], [CAMERA MOVEMENT if any], [LIGHTING/MOOD]
         Ad framework S.C.E.N.E.:  Subject / Context / Event / Nuance / Exclusions

FLUX 3 VIDEO, six fields
         Core summary → Scene (per shot) → Subject description (FIXED, identical across shots)
         → Dynamic narrative (per shot, timecoded) → Audio (per shot) → Style & color

NANO BANANA   [Subject] + [Action] + [Location/context] + [Composition] + [Style]
SORA 2        Prose scene description → Cinematography → Actions → Dialogue block
```

Luma's UGC camera notes [P]: *"smooth handheld movement"* for authentic UGC, *"slow push in"* for a
product hero, and *"avoid overly polished looks, scripted-feeling delivery, or product-first
framing"* — lead with problem-context before the product, the ordering `script-craft.md` and the
hook bank already argue for, arriving here from the model vendor's side.

## 11. What this implies for the house prompt format

⛔ **Proposals, not edits.** `ai-generation.md` is unchanged by this file; each item is a discrete,
reviewable change for whoever owns that format. Several contradict what it currently says — which is
why they are listed rather than quietly applied.

1. ✅ **APPLIED 2026-09-06 — `scripts/prompt_lint.py` enforces two shapes** (`kind: frame` carries
   the picture; `kind: clip` carries motion only and is refused if it re-describes the frame), and
   `ai-generation.md` Step 2 now says so. Original proposal follows. **Fork the block set by conditioning path.** One set currently serves image-to-video generations,
   yet `[START FRAME]`, `[ENVIRONMENT]`, `[LIGHTING]` and the trailing `STYLE:` line all re-describe
   a picture the approved frame already settled — the error every vendor names (§1). Keep the full
   set as the **t2v / frame-authoring** format; add an **i2v clip format** carrying only `[MOTION]`,
   `[CAMERA]`, `[PERFORMANCE]`, `[SPEECH]` and the shot's guardrail blocks. *Highest-value item
   here.*
2. ✅ **APPLIED (v2.71.0)** — the prompt file's `[SUPPRESS]` block is a noun list the lint
   refuses to accept as sentences, and a prohibition inside a positive block is warned (2026-09-06). The
   guardrail table (`ai-generation.md`) now gives each guardrail a positive line for the body and a noun list
   for `[SUPPRESS]` or, on a model with no negative field, `[CONSTRAINTS]`; `direction.md` no longer says
   "write the negative", and its card example and the shot-list template say the face as a state; a
   `prompt_lint.py` self-test holds the table. **Guardrail negatives are noun lists of things to suppress, not
   sentences of prohibitions** (§2.6).
3. **Bound negatives to structurally peripheral objects** (§5.2). Guardrails may negate props,
   background and anachronistic objects; anatomy and subject-critical elements get a **positive**
   specification instead — which the hands row already does. Stating the principle keeps the next
   row consistent.
4. **Demote block order from control surface to legibility convention** (§3.2) — one line saying the
   order is for the human writing the prompt, so nobody spends retakes reordering blocks.
5. **Name the character block as a fixed string held identically across shots** (§7 item 4, FLUX 3's
   schema) — copied verbatim, never re-authored per shot.
6. ✅ **RESOLVED 2026-08-30 — "locked seed" removed from the identity-lock recipe.** `ai-generation.md`
    Step 3 and its failure table now say *log* the seed as manifest evidence rather than *lock*
    identity with it. Original finding follows. Step 3 prescribed it; §6.3 shows two
   vendors disclaiming determinism, Sora exposing no seed, the live registry exposing none at all.
   Keep logging seeds as manifest evidence; stop presenting them as a consistency mechanism, and
   give that sentence to the reference/element lock, which is Tier 1.
7. **Split a `[SOUND]` block from `[SPEECH]`** (§9.4) — BFL prescribes layering speech / ambience /
   effects / music and Veo documents distinct `SFX:` and `Ambient noise:` prefixes. Today ambience
   is unspecified or smuggled into `[ENVIRONMENT]`, which an i2v prompt should not carry.
8. **Make the dialogue-fits-the-clip rule a format-level constraint, not a fix** (§9.1) — the ~8s
   target belongs beside the duration script, upstream of prompt writing.
9. **State "one camera instruction per clip" in `[CAMERA]`** (§2.4), and replace negated camera
   phrasing (`"no rotation"`) with Runway's positive restatement for locked-off shots (§4.2), quoted
   verbatim.
10. ✅ **APPLIED 2026-09-06** — the `.ok` sidecar records the bound references and the start-frame
    hash, and `APPROVALS.md` records the media id the clip must bind; the gate refuses a call that
    binds anything else. **Log the conditioning, not just the prompt** — §7 puts consistency in references and elements,
    so *which* elements or reference images were bound, in which roles, is now a load-bearing
    manifest field alongside model / prompt / seed / frame / VO.
11. **Record any silent prompt-rewriter state before a bake-off** (§6.5). ⛔ The vendor-specific version
    of this item is off roster; the general rule is not — a server-side rewriter makes a bake-off
    uninterpretable, so establish per model whether one exists and log it in the manifest.

## 11b. ⚡ The Higgsfield / Seedance vendor skill — what was adopted, what was tested, what is still open

Source: *Seedance 2.0 Prompt Writer*, Higgsfield's own prompting skill for a model they serve,
supplied 2026-09-17. **Tier: [SECONDARY · vendor guide]** — the same tier this file already gives
Runway, Wan, Luma, Veo and Kling docs, and for the same reason: a vendor describing their own
model's prompt surface is the best evidence that surface has. ⚠️ It carries **no citations for any of
its numbers**, and vendor guides demonstrably disagree with each other across models — fal.ai says
numeric optical specs are *"stylistic cues rather than computational parameters"* while this one
builds a whole FOV table on them. So: vendor authority raises a claim to worth-testing, not to true.

⛔ **Architecture first, because it decides how much can travel.** That skill is **t2v** — one
standalone prompt carrying subject, light, optics, physics and style together. This pipeline is
**i2v**: the frame is authored and approved, then the clip prompt carries motion only (§1). Its block
structure is not portable and importing it would dissolve the fork the frame gate depends on. It is
also written for **Seedance 2.0**; the roster carries `seedance_2_5`. (v2.49: the owner adopted a t2v-style
block template for Seedance 2.5 as the scene form, §12, on the festival evidence. The fork still holds for
every clip that binds a start frame; the scene form's approval point moved to the reference sheets.)

### ✅ Adopted — these are model-independent and consistent with §7.0

1. ⚡ **Scale by comparison to something in frame, never by measurement.** *"As tall as four humans
   stacked head to toe"* beats *"three metres tall"*. This is `cinematography-craft.md` §7.0
   predicting itself: a relational description is caption-native, a number is not. It generalises
   past giants — **any size, distance, depth or quantity is written against a thing the frame
   already contains.**
2. ⚡ **The observation pattern, as a recipe that must be COMPLETE to work.** Three ingredients at
   once: foreground occlusion over 20–30% of frame · atmospheric haze between camera and subject ·
   a distant vantage. Drop one and it reads as an ordinary shot. And the continuity rule that comes
   with it: **vary the occlusion between beats, hold the vantage.** §5.3 has the near plane as a
   figure/ground fix; this is the same object doing a second job, and the combination is the part we
   did not have.
3. **An `@tag` only goes in a shot where that object is PRESENT** — *"the model will try to force it
   into frame."* A reference plan lists what a shot needs; nothing checked that a listed reference
   is actually IN the shot. Cheap, specific, and a real failure mode.
4. **Mixed speed modes: hard cuts only between them; one speed per shot, start to finish.** Sits
   directly on top of §7.2's one-behaviour-per-clip rule and extends it to retiming.

### ⛔ Tested and rejected — for THIS pipeline's frame stage

**FOV in degrees instead of millimetres.** Measured 2026-09-17, `lab-00001-fov`: one scene, six
frames, one varied axis. The millimetre arm separated correctly; the degree arm **failed backwards**
— 18°, predicted most compressed, returned the widest frame of the six. Full record with its
caveats and denominator: `lab-00001-fov/09-qa/RESULT-2026-09-17-fov.md`; the ruling is
`cinematography-craft.md` §7.1. ⚠️ This refutes importing it into a FRAME prompt. It does not touch
the vendor's claim about their own video model.

### 🔍 Open — named, specified, not yet run

⛔ These are recorded as tests rather than doctrine **on purpose**: each is a specific vendor claim
that contradicts something here, and the cost of guessing is that a wrong rule becomes house style.

| Claim | Contradicts | The test |
|---|---|---|
| **Block ORDER matters** — "CAMERA in 3rd position; moved to the end, FOV gets ignored; moved to the front, it conflicts with identity" | this file has block budgets and no position rule at all | one prompt, same blocks, three orders, n≥4 each. Read whether the camera instruction survives |
| **Quantified atmosphere** — "fog density 40%", "haze visible at 15 metres", speeds in km/h | §7.0: a measurement is style-flavoured noise | fog at 20/40/60% on one scene. Does the haze depth actually move, or is any number just "foggy"? |
| **A whip under 0.8 s renders as a hard cut without blur** | `cinematography-craft.md` §3.8 rates the whip a JOIN and gives no threshold | three clips at 0.4 / 0.8 / 1.2 s. ⛔ This one costs real credits — it is the only open item that needs the video model |
| **The 4-mechanism stack for extreme-FOV multishot** (identity lock · lens-lock opener · lens-check closer · colour by material) | nothing here; we have no multishot consistency protocol | only worth running if the degree finding reverses on video |

⛔ **What will NOT be imported, and why it is not an oversight.** Its absolute *positive-phrasing
only* rule conflicts with `[SUPPRESS]`, which is a documented feature of models with a negative field (Kling 3.0 on this roster) with a character cap
— model-specific, not universal. Its *no equipment names ever* conflicts with the **T weak** rating
film-look tokens earn here. Both are cases where a vendor rule for one model is being read as a law.

---

## 11c. ⚡ The Higgsfield PUBLIC skills repo and live workflow catalog — a second vendor source that disagrees with the first

Source, read 2026-09-17: `github.com/higgsfield-ai/skills` (eight shipped skills, the
`higgsfield-generate` reference set, plugin manifests, CI) plus the **live** workflow catalog behind
the connected MCP — sixteen workflows, each versioned, read through `get_workflow_instructions`.
**Tier: [SECONDARY · vendor, 2026-09-17]**, same as §11b. The live catalog is the fresher of the two:
it is what the server will actually run today.

⛔ **The headline is that the vendor contradicts the vendor.** These are not different companies
disagreeing — they are two documents from Higgsfield, read the same day, giving opposite
instructions on the axis this skill had just measured.

| Axis | *Seedance 2.0 Prompt Writer* (§11b) | The public repo / live catalog | Our measurement |
|---|---|---|---|
| **Optics** | field of view in **DEGREES**; never write millimetres | their repo's prompt-engineering reference (higgsfield-generate): *"Camera: lens (35mm, 85mm), angle, motion"* — **millimetres**, no degree table anywhere | ⚡ mm separated correctly and monotonically; the degree arm **failed backwards** (`cinematography-craft.md` §7.1) |
| **Length** | a long structured block prompt | *"Keep it under ~200 tokens. Models distort with very long prompts."* And `ad-multiplier` caps a final prompt at **3900 characters**; its Soul person prompt is **140–190 words** of prose | our band is **1800–2100 chars** [PRIMARY · own testing], ~300 words — above two of the three vendor numbers and inside the third |
| **i2v discipline** | — | *"`--start-image` anchors the first frame. Prompt describes motion. Don't redescribe the static frame — model already has it."* | ✅ this is our fork (§1), reached independently by the vendor |

So the degree-FOV rejection now rests on a measurement **and** on the vendor's own general guide
siding with millimetres. The length question is the opposite: two vendor sources sit **below** our
measured band, which makes the band the most load-bearing unverified number in this file. It is
named in §13 and it is the next test worth paying for. (The band governs frames and i2v clips. The
scene form, §12, runs far longer on the festival evidence and has its own floor and ceiling.)

### ✅ Adopted from the workflow contracts — mechanisms, not numbers

1. **A finished prompt is validated before it is submitted, and "finished" is checkable.**
   `ad-multiplier` v1.4 validates byte-for-byte and refuses a prompt carrying *"branches,
   alternatives, or meta-conditions"* or *"bracketed placeholders or slash-separated
   alternatives"*. We had every quality check and no check that the writing was DONE — `[HERO
   NAME]`, "either the mug or the glass" and a pasted CDN URL all passed the lint, and the model
   renders what is written, brackets included. Now four BLOCKs in `prompt_lint.py`: unresolved
   placeholder · unresolved alternative · a raw id/URL inside the prompt text · describing by
   comparison. Each is pinned in the selftest in **both** directions, because the false-positive
   half is the half that gets skipped and the half that makes a lint something people route around.
2. **"Different from the source" is not a description.** Their casting gate states it outright:
   words such as *"different"* or *"contrasting"* without explicit positive traits do not satisfy
   it. A model cannot see what it is supposed to differ FROM. ⚠️ We adopted the **mechanism** and
   not their axes: their contract makes *apparent racial/ethnic casting presentation* a mandatory
   contrast axis, which is a vendor's answer to "make these two strangers look unalike" and is not
   a thing this skill will ever require. Name the visible trait — hair length, texture and shape;
   the garment; the colour — positively, and let the client profile say what the casting is.
3. **Render silent; carry the real audio through.** Ad Multiplier renders with
   `generate_audio:false` and restores the SOURCE's default audio in post, under QC gates for
   duration, aspect, resolution and audio presence. That is our voice gate reached from the other
   direction: a video model authoring its own soundtrack skips the approved line, the chosen voice
   and the rights check. `gate.py` now refuses `generate_audio: true` unless `audio` is approved.
   ⛔ Prevention, not cleanup — `strip_embedded_audio.py` was the cleanup.
4. **One position at a time, `count:1`, a stable output index, retry a failed position ONCE,
   continue with the successes and report the failures.** And from the explainer skill: *"Two
   identical failures mean the prompt or parameters must change."* That is a stopping rule the
   refinement loop did not have written down.
5. **Never silently replace a locked model, and never silently downgrade to fit a free tier.**
   Their `use_unlim` doctrine is the sharpest statement of it: *"never silently downgrade the
   output, and never silently charge"* — stop and ask which one the user wants. ⚡ This is the same
   class as the substitution our own calibration run hit (§7.1 caveats).
6. **Audio before picture, with a hard barrier**, when a fixed-length assembler is involved: the
   explainer skill generates every narration take first and starts no clip until all N are
   complete, because the take's real length decides the block. `estimate_duration.py` predicts;
   the take measures. Where an assembler holds a fixed window, measure.

### 🔍 Open — worth testing, not yet run

| Claim | Why it is not settled | The test |
|---|---|---|
| **Our 1800–2100 char band vs "~200 tokens"** | Two vendor sources sit below it; ours is measured but on our own generations, and the vendor's number may be model-specific or may be about DENSITY (§2.2) rather than length | one scene, one varied axis: the same shot written at ~700 / ~1400 / ~2000 chars, held constant otherwise, scored for error rate and for detail actually obeyed |
| **Prose paragraph vs labelled blocks at the frame stage** | Their Soul prompt is explicitly *"one cohesive 140–190 word natural-language paragraph, not a tag list"*; our frame prompt is blocks | same scene, same content, two shapes |
| **The single style-key image reused as a reference on EVERY clip** | Their explainer skill's whole consistency mechanism, and cheaper than our per-shot reference plan for non-photoreal work | a six-clip non-photoreal run with and without the shared key |

### 📋 Model contracts, current as of 2026-09-17 [SECONDARY · vendor repo]

Worth carrying because a wrong duration is a rejected job and a silently clamped one is worse:
**the CLI coerces an unsupported value to the nearest allowed one and continues**, reporting an
"adjustments applied" note — so a preflight that records what was REQUESTED can describe something
that was never made. Read the response, not the request.

- **Seedance 2.5** — the vendor's default for serious video. 4–30 s, `480p/720p/1080p`, modes
  `t2v` / `omni_reference` / `video_edit` / `video_extension`; media roles `start_image`,
  `end_image`, `image_references`, `video_references`, `audio_references`.
- **Seedance 2.0** — now positioned as the special case: *"use when native 4K output is required"*.
  4–15 s. ⚠️ §11b's whole guide is written for this model.
- **Kling 3.0** — 3–15 s, `16:9`/`9:16`/`1:1`, modes pro/std. Vendor's note: single-plane scenes
  that don't need heavy motion.
- **Veo 3.1** — duration **4, 6 or 8 only**, a closed set, `16:9` or `9:16`.
- **Grok Video 1.5** — requires a start image, 2–15 s, `480p`/`720p` only.
- **Virality Predictor (`brain_activity`)** — takes a finished clip, returns overall score, peak
  second, sustain, plus a report link. ⚠️ An attention **proxy** measured before publication, not a
  platform metric; `performance-metrics.md` owns the real ones. It is the only instrument named
  here that can score a hook before the money goes to distribution.

⛔ **Not adopted, deliberately.** Their `ffprobe`-in-a-sandbox finalisation, the Soul beauty floor
(*"strikingly beautiful … high model facial features"* is a vendor house style, and the client
profile decides casting here), and the whole Marketing Studio / UGC routing tree — that is a
different product's pipeline, and this skill's clients have approved shots, not generated ads.

## 11d. ⚡ A practitioner production-prompt corpus — what a working house style does that we did not

Source: a run of real Cinema Studio / Seedance production prompts — a character-sheet workflow and
several multi-part sequences — plus **the author's own revision requests on them**, which are the
most informative part: they show what the prompts FAILED to hold and what the author did next.
**Tier: [SECONDARY · practitioner corpus]** — not a vendor guide and not a measurement, but a large
body of prompts somebody actually shot with, which is evidence of a different kind: it shows which
failures were worth a whole block of prompt to prevent.

⛔ **Read this as craft, not as architecture.** These are **t2v multi-cut** prompts; this pipeline is
**i2v single-action** (§1, SKILL.md §3). The block vocabulary is not portable and importing it would
dissolve the frame gate. What IS portable is the failure taxonomy underneath it. (Since 2026-10-25
the pipeline also takes **planned** multi-shot clips — `multishot.md`, §11f below — but those keep the
frame gate and bind every reference to one subject; the corpus's block vocabulary is still not imported.)
(Since v2.49 it is, for Seedance 2.5: the scene form, §12, uses the vendor's block order, with the approved
sheets as the approval point instead of a start frame. Items 1, 4 and 5 below carry straight into it.)

### ✅ Adopted

**1. A reference declares what it must NOT bring — `not:`.** Every reference in the corpus carries a
negative scope beside the positive one. A character sheet locks identity, face and wardrobe and says
in so many words that the sheet's studio background and layout are not inherited; an environment
reference controls environment, materials and mood but not its framing; and when two location
references share one shot, each is scoped to the ground it alone defines and told to stay off the
other's. We had the positive half — `what:` names the ONE attribute a reference is FOR (§6b) — and
nothing about the rest of the picture, **which arrives anyway**. A character sheet shot on seamless
grey brings the grey, the three-panel layout and the studio key into a night interior.
`prompt_lint.py` now WARNs when a `character` / `wardrobe` / `prop` reference declares no `not:`. It
is the cheapest regeneration in this file to prevent.

**2. A state change inside one clip needs an ASSET, not more sentences.** One corpus prompt damages a
character's wardrobe partway through a clip (at 3.2 s) and then defends the new state four ways: a
wardrobe-state timeline block, an insistence that the change is permanent, the state re-asserted at
five named timestamps, and a positive lock. **The author's next revision throws all four out** and
asks for the prompt to be rewritten around a separate damaged-wardrobe asset, used from the moment of
the change. That is the whole lesson in one revision — a model has no state register
(`character-and-props.md` §8.4, statelessness), so nothing holds a change and it reverts between
frames; **the fix is to author the AFTER state as its own reference**, or to split the clip at the
change. `prompt_lint.py` now BLOCKs a described mid-clip state change unless a reference declares
`state: after`. ⚡ This also upgrades §8.8's *"wardrobe & prop continuity — does not transfer, rebuild
by hand with a per-prop state timeline"*: the timeline is the **record**, the asset is the
**enforcement**.

**3. Argue the outcome from physics, or the model will resolve it in your favour.** When the corpus
needs a MISS it does not merely say so — it gives the mechanism: how far a body can travel in a dive
(about two metres) against how far away the target lies (about eight), so the shortfall follows from
physics alone; or an obstacle that moves faster than the person, so it closes the gap first.
Generators are obliging: asked for a desperate lunge at a prize, they tend to deliver the catch. A
stated impossibility is weaker than a described one. Applies to any withheld outcome — a near miss, a
door that does not open, a hand that does not quite reach.

**4. Negate by scope, not by word.** Instead of forbidding a noun (which names it, §5), the corpus
**enumerates what IS seen** — for an impact, only its sound, its splash and its spray, never the
object that caused it — and the absence follows. Cheaper than a negative tail and it does not fight
the tokenizer.

**5. Name the invariant, then name it again at the end.** Every prompt closes with a POSITIVE LOCKS
block restating the things that must not drift — phrased positively, as the desired state. The
recurring lock types are a **failure taxonomy worth having by name**, and they now live in
`shot-handoff.md` §7 rather than here.

### 🔍 Open — genuinely unsettled, and I am not adopting either side

| Question | The corpus says | This skill says | Why it is open |
|---|---|---|---|
| **Field of view in DEGREES** | the house convention throughout — `47°`, `29°`, `84°`, `107°`, with a lens lock per segment forbidding focal drift | §7.1 rates the degree table TESTED AND REJECTED | ⚠️ **my measurement was the FRAME stage only** (`lab-00001-fov`, an image model). This corpus is the VIDEO stage, and the rejection never covered it. Their consistent use of degrees across dozens of shot prompts is real evidence that the convention does something on their video model. The two findings do not conflict; the scope line in §7.1 is doing real work and should not be quietly widened |
| **A per-segment lens lock (no focal drift mid-segment)** | stated per segment in every prompt | we specify one camera behaviour per clip and say nothing about drift | plausibly free to adopt, but it is a control we have never tested; adding an untested phrase to every prompt is how the block budget gets spent on nothing |

⚠️ **SUPERSEDES IN PLACE** (2026-10-25) — previously this table opened with **Multi-cut in ONE
generation** held open: the corpus cuts 3–7 times inside one call, against our "one clip carries ONE
complete action; the cut is made in the edit (SKILL.md §3)", pending "one honest bake-off". The owner
decided it without the bake-off: *"Multi shot but planned at senior level, with reference videos,
start and end frames etc"*. A **planned** multi-shot clip is now a clip type (`multishot.md`), and the
measurement that argued against it (57.6 % yield, no handles inside a take) stays on that page beside
the decision. The bake-off is still worth running; it now measures how much the plan buys back, not
whether the form is allowed (`multishot.md` §10).

### ⛔ Not adopted

The corpus's timestamped multi-cut format **as written** — cuts placed at stated timestamps, with one
line telling the camera not to cut on its own as the only control. The house form is the planned
`[STAGES]` form (`multishot.md` §5): ranges as budgets, timestamps only as point reinforcement, every
internal cut named — which is what the vendor's own 2.5 material now says (§11f). Lines inside a video
prompt come **with** the voice gate, never instead of it: a multi-shot clip may list its lines in
`[SOUND]`, and `gate.py` still refuses generated sound until `audio` is approved (on any clip with
lines, not only `type: dialogue`). And the corpus's habit of restating a lock four times — length is
not the variable, demands per block is (§2.2), and four restatements of one invariant is four demands
buying one.
⚠️ **SUPERSEDES IN PLACE** (2026-10-25) — previously: "The timestamped multishot format itself; the
per-cut dialogue baked into a video prompt (our voice gate owns speech …)". The owner adopted planned
multi-shot clips; what stays out is the corpus's timestamp grammar, not the form, and the voice gate
now follows the lines wherever they are written.

## 11e. ⚡ A practitioner corpus — rejected takes, with reasons. The best evidence in this file.

Source: a paid course's full build of one short film — every prompt plus **the takes that were thrown
away and why**. **Tier: [SECONDARY · course notes]** — but a better grade of secondary than a vendor
guide, because a rejected take with a stated reason is a *result*. Somebody generated it, looked at
it, and named the defect. That is the only kind of evidence in this file that did not come from a
document.

⛔ Same architectural caveat as §11d: multi-cut t2v prompts, not our i2v fork. The craft transfers;
the format does not.

### ✅ Adopted as checks

**1. A whip pan cannot change shot size.** A rejected take started at one shot size and ended at a
tighter one. The course's diagnosis: once the frame size changes mid-swing it is no longer a whip but
a hidden cut, and the viewer sees a glitch instead of a transition. One continuous move; a real
operator does not change focal length mid-swing. `prompt_lint.py` BLOCKs a whip naming two sizes.
The same take also fixes the §11b open question about whip timing by spec: **settled until ~0.3s
before, a ~0.5s motion-blur swing, the new subject settled by ~1.4s** — without the numbers the
model guesses, and the swing either lags or lands before the face on the other side has settled.

**2. On-screen text needs the words VERBATIM and a hold long enough to resolve.** A handwritten page
came back as pseudo-writing — easy to miss at playback speed, an obvious AI tell on a second look.
The fix was the exact lines (three of them) quoted in the prompt and a **~2 second** close-up.
`prompt_lint.py` now splits what was one blanket warning: a **brand mark** still routes to composite
(a model does not render a wordmark), but **diegetic text** is renderable and is BLOCKed when the
words are missing or the clip is under 2s. ⚠️ The pattern missed `writes "…"` on the first pass — the
citation-form gap again, found by testing.

**3. A close-up on a body part is an anatomy reference, not a mood.** The rejected hands had smooth,
waxy CG skin — acceptable in principle, fake the moment they filled the frame. An affect label
("nervous" hands) gives the model nothing to render; named anatomy — tendons, knuckle creases, a
torn cuticle — does. `prompt_lint.py` WARNs on a body-part CU carried by affect words with no anatomy
named.

### ✅ Adopted as doctrine — the cost levers

**4. A wrong PERFORMANCE is not a reason to re-roll the shot.** A locked 20-second action take
needed one clean line. Instead of regenerating it, the course shot **a separate face-only clip in a
quiet room**, treated as a voice recording rather than a scene, and married the audio in the edit.
⛔ **Isolate the read, fix the read, marry it back.** This is the single biggest cost lever in the
corpus and it belongs beside `refinement-loop.md`'s retake economics.

**5. Technical and emotional are separate knobs, and they revise independently.** A whip-pan take
nailed the mechanics and broke the emotion (a warm smile where the story called for grief). Giving
the prompt writer the emotional context fixed the performance without touching the whip-pan spec at
all. So a note about feeling does not reopen the camera spec, and vice versa — which is only true if
the two live in separate blocks. Ours do (`[MOTION]` / `[PERFORMANCE]`); this is the argument for why.

**6. Direct the BREAK, not the emotion.** A flat delivery of a confident line reads as recitation;
the take that works lets the confidence crack on one named word, so the feeling shows as a catch in
the throat, not as a change in the words. Name the **word** the voice breaks on. "Sad" is unactable;
"the pitch drops on *sorry*, nostrils flare, eyes flick down" is a direction. Same grammar as naming
a camera move instead of "more dynamic".

**7. Name the technique, not the mood — and only against a locked take.** A request for more drama is
too vague to act on; a request for a speed ramp on the key action tells the prompt writer exactly
which frames slow down and exactly when they snap back. ⚠️ And the precondition: a one-sentence
revision works *because* the base shot is already locked — a speed ramp asked for cold, with no
established shot, has no beat to ramp around.

**8. Judge takes by WHICH BEAT each one gets right, not good-vs-bad.** In the course build one take
supplied one line cleanly, a different take nailed the next, and both were kept over the rest of
their own batch. The finished scene is assembled from **partial wins**. A batch scored take-by-take
throws away the half that was right. See `review-and-approval.md` on the selects gate — the verdict
belongs to a beat, not to a file. And when the failure is physics, there is no partial win: a
broken-physics take cannot be fixed, only re-rolled.

**9. A beat that needs a pause needs another SHOT.** The course's rule of thumb: after a flashback,
or anything that lands on a character, give them one to two seconds to process it before they speak.
One 15-second take carrying a wide, two OTS singles and a question played as if in a single breath.
The fix was structural: split the prompt so the pause has its own frame. ⛔ Do not ask one generation
to carry the emotion and the recovery at once. ⚡ This is our one-clip-one-action rule (SKILL.md §3)
reached from a completely different direction — pacing rather than handles — which is the strongest
kind of corroboration.

**10. A time shift ages EVERY asset, or it reads as a costume.** The course's flashback aged the
character sheet (adult → child), the location palette (cold → golden hour) and the props (worn,
older versions) together. Age one piece and leave the rest adult-toned, and the flashback reads as
dress-up, not memory. And props carry era fastest: they are small enough to pass as authentic at a
glance.

**11. Rendering and EDITING are different jobs for different models.** A costume sheet was rendered
by one model, then a crest and a number on it were changed by a text-editing model: a word-level fix
is a different job from a render. ⛔ Never spend a full generation on a one-token change.

**12. A one-scene character needs no asset — but needs the negative scope more, not less.** A
one-scene background character was described cold in the prompt with no reference sheet. The prompt
still cites the lead's asset, hard-scoped to its one role in the shot, with an explicit line that the
lead's face and identity must not transfer to the new character. The reason is mechanical: **it is
the only face reference in the prompt**, so it is what the model reaches for. ⚡ That sharpens §11d's
`not:` rule — the risk is highest when a reference is the only one of its kind present.

**13. A deliberate violation of a compositional convention must be stated more than once.** The
corpus pins a subject hard to the frame edge *looking off it* — no lookroom, all the space behind
him — and says so three times in one prompt. Models regress to the convention. The general form:
**an intentional "wrong" needs repetition; an intentional "right" does not.**

### 🔍 Open

| Question | The corpus | Us | Test |
|---|---|---|---|
| **The constant house-style preamble** | every prompt opens with the same ~150-word block — capture format, named cinematographer references, 180° shutter, a 60:30:10 colour split, pore-level skin, 24fps, no music | §2.2: what degrades output is **demands per block**, and a constant preamble is ~15 demands spent before the shot is described | same shot with and without the preamble, scored for error rate and for how much of the preamble is actually obeyed. If most of it is inert, it is 15% of the band buying nothing |
| **Resolution protects atmospherics — and, on a second source, COMPLEXITY** | the course advises rendering at 4K so that flares and fog survive `[SECONDARY · course notes]`. ⚡ **Sharpened 2026-09-18** by a Seedance 2.0 4K practitioner corpus making a bigger claim with a mechanism: busy wide shots with many moving parts were exactly where 1080p and 720p broke down — morphing mid-shot or freezing into stiff poses — and at native 4K that mostly goes away, because the extra resolution lets the model hold detail across a busy frame instead of smearing it `[SECONDARY · practitioner corpus]` | our quality floor is 1080p-minimum on cost grounds | ⚡ **the test just got better defined, and cheaper.** Two independent sources now assert it, and the second says the failure is **complexity-dependent** — so vary BUSY-NESS, not haze: the same scene at 720p / 1080p / native 4K with a rising count of independently moving elements, scored for morph and for pose-freeze. If it holds, the floor stops being a cost rule and becomes a **capability** rule, and "generate wide crowd/creature shots at native 4K" becomes a roster instruction. ⚠️ Still asserted: neither source shows an A/B, a count or a denominator |
| **First-batch usable rate as a model-selection metric** | the course treats a model that needs three or four batches to get one clean take as not ready for a scene with many moving parts — four of four usable is named as the bar | the roster is chosen on measured rates and capability, not on yield | cheap to start measuring now: record usable/generated per batch in the shot manifest and let the roster argue from it |

## 11f. ⚡ Seedance 2.5's own multi-shot material, and a practitioner's timed-prompt method

Three sources, read 2026-10-25:
- **Higgsfield's Seedance 2.5 "New capabilities (Part 2)" deck**, 20 slides `[VENDOR]`;
- **Higgsfield's "Seedance 2.5 Prompt Writer"** and **"Short Drama Screenwriter"** guides (files dated
  2026-10-22) `[VENDOR]`;
- **a practitioner's timed-prompts skill**, distilled from one multi-part commercial (several people
  and locations, fixed lines, match cuts; file dated 2026-10-06) `[SECONDARY · practitioner method, no
  measurements]`.

They arrived the same day as the house decision to adopt planned multi-shot clips (§11d's
supersession), so this section says which parts of them the house form took. The form itself is
`multishot.md`; the lint is `prompt_lint.py` with `form: multishot`.

### ✅ Adopted

1. **Stages, not timestamps** (deck p.14–20). One stage per internal shot, each with **one** primary
   state change and the state visible when it closes; ranges are **budgets, not cuts**; exact time
   points only for one or two beats; **no frequencies**; a consistency block last. All of it is a lint
   rule now (`multishot.md` §5, §9).
2. **References grouped by type and bound one subject per line** (deck p.5–14): define the roles, map
   each subject to one reference, group them (`[Characters]` `[Props]` `[Scenes]` `[Motion and
   Audio]`), give a recurring character a profile, then choose per scene. A prop names its one owner;
   a scene plate never brings its people. This matches the `what:` / `not:` plan already enforced (§6b,
   §11d), with the binding grammar added (§6b above).
3. **Geometry before action** (the timed-prompts skill §2–§4): a `[WHERE]` block that fixes seats per
   location (clock face, or screen-left/centre/right from a named camera side), `BACKGROUND:` per
   stage, a per-stage hand inventory, and one canonical list of lines, *"each spoken exactly once and
   nothing else"*. Its transition notes too: a **match cut** on an action is the reliable one, and an
   occlusion cut drifts more (`multishot.md` §6). These are a practitioner's lessons from one job, so
   where the lint checks them it WARNs (a missing `[WHERE]` with two or more people), never FAILs.
4. **The outpaint band maths** for a 16:9 master (timed-prompts §9) — `modes/repurpose.md`.
5. **The Short Drama Screenwriter's structure** — `micro-drama.md`, with the changes listed there.

### ⛔ Not adopted

- **Named asset handles in place of positional tags.** The timed-prompts skill says never `@image1`,
  always `@` + the asset's file name. That is the Higgsfield **web UI**, where assets have names. The
  MCP call this pipeline makes has none: `medias` is a list of `{role, value}`, so the order IS the
  binding. The deck and the Ad Multiplier workflow both use positional tags, and `gate.py` now checks
  the order (§6b).
- **A blocking map drawn by an image model** (timed-prompts §7a). An AI image used as a reference is
  exactly what the house rule excludes; `blocking.py` renders the map from geometry instead
  (`character-and-props.md` §8.7b, `blocking.md`). The binding advice carries over: name what each
  colour is, and keep geometry apart from appearance.
- **The vendor's character "voice lock" across episodes** (Short Drama Screenwriter). Voice continuity
  stays with the voice gate (`micro-drama.md`).
- **The Prompt Writer's hard cuts on stated seconds.** The two vendor sources disagree: the Prompt
  Writer lands every `HARD CUT` on a stated second (*"0.0s to 1.0s … 1.0s HARD CUT"*); the deck says
  ranges are budgets and a boundary lands *"slightly before or after"*. The house form takes the
  deck's reading because it is the safer one for the edit: plan as if each cut will drift, and measure
  it (`multishot.md` §7).
- **The Prompt Writer's FOV degrees and `"no drift mid-segment"`** are a second vendor source for two
  of §11d's open rows. They stay open: nothing here has tested either at the video stage.
- **The deck's claims as facts.** That multi-view identity fusion is new in 2.5 is a vendor claim, and
  so are the slot limits (30 / 10 / 10); neither is measured here. The first job that relies on either
  checks it (`multishot.md` §4, §10).

### 🔍 Open

| Question | What we have | What settles it |
|---|---|---|
| How far does a stage boundary land from its budget? | the deck: *"slightly before or after"*; we plan for ±0.5 s `[assumed]` | `film_breakdown.py` on the first multi-shot takes: cut time against the plan |
| Does `wan3_0` take frames and references in one call? | the schema allows it; never measured | one lab job with `mix: true`, owner-approved spend |
| Is a long multi-shot prompt worse than a short one? | 3,900 characters is the vendor's validator ceiling, not a quality curve | length vs adherence on the first jobs, as the single-clip band was measured (§2.2) |
| Does a planned multi-shot clip beat gated single clips on usable seconds per credit? | the 57.6 % single-clip yield; nothing yet for the planned form | the bake-off kept open in §11d's supersession (`multishot.md` §10) |

## 11g. ⚡ v2.45 (2026-10-29) — the model's own ceiling, the image edit, the detail score, and the Scenario refusals

**Sources, all read 2026-10-29.** The ceilings: the author's research notes (vendor API docs, SDKs
and reseller schemas, each row with its URL and a confidence). The refusals and the edit structure: the 13 Scenario
skills as summarised in the author's research notes; the edit pages in
the author's research notes §1.1, §2.2, §3.1–§3.3 and the author's research notes §5; the
reference jobs and the lint gaps they reproduced in the author's research notes §0, §5.4, §6;
the ungated uploads and motion control in the author's research notes §2.3, §4 (R4, R5), §5.6.
Scenario's numbers are its authors' `[SECONDARY]`; nothing here was measured on our account. Two house decisions
frame it (2026-10-28): **Scenario is not a provider**, and **an AI-edited target frame of our own footage is allowed
only as a gated per-shot opt-in** (`gate.py approve target:<SHOT>`).

### The ceiling is the model's; the band is ours

`MAX_PROMPT = 2500` was one house number for every model ("nobody has measured beyond it"). The vendors' limits run
from 1,500 characters (Wan 2.6, cut off without an error) to 26,000 (Kling 4.0, English). `prompt_lint.py` now reads
each model's ceiling from `assets/higgsfield-rates.json` — `call_contract` for the roster video models,
`prompt_limits` for image models and off-roster ids, then `prompt_limits._families` by id prefix — and:

- **FAILS above the model's true ceiling**, naming it and its source;
- **WARNS "past the measured band"** above 2,500 where the model takes more. The 1,800–2,100 frame band (§2.2b) is
  unchanged: it is what this account has measured, and the vendor ceiling says nothing about quality;
- **keeps 2,500 as a FAIL marked "house ceiling, unknown vendor cap"** where no vendor publishes one;
- keeps the multi-shot form's 3,900 (Higgsfield's own Ad Multiplier validator), and adds Kling's limits under it:
  at most 6 shots, each at most 512 characters;
- (v2.49) gives the scene form its own floor and ceiling: WARN under 2,500, FAIL over 20,000, the house ceiling
  (§12). `seedance_2_5`'s `prompt_max_chars` in the rate asset is now 20,000; 3,900 was a workflow's validator,
  not the model's cap.

| Model id | FAIL above | Negative prompt | Source · confidence |
|---|---|---|---|
| `kling3_0` | 2,500 | a field, 2,500 (legacy v1 endpoint) | Kling dev docs: legacy `/v1/videos/*` "Cannot exceed 2500 characters"; the new endpoint's 3,072 is not used because which endpoint Higgsfield calls is unknown · confirmed |
| `kling4_0` | E/26,000 + N/11,000 > 1 (ASCII counted as English, an assumption) | none | Kling dev docs (kling-4 params); fal enforces 26,000. The blogs' "8,000" is tokens · confirmed |
| `minimax_h3`, `minimax_h3_max` | 7,000 | none | MiniMax API, video generation v2 · confirmed |
| `seedance_2_5`, `seedance_2_0` | 20,000 (house, v2.49) · the multi-shot form keeps 3,900 · WARN over 500 CJK characters | none | BytePlus publishes a recommendation only; 3,900 is Higgsfield's Ad Multiplier workflow validator; the festival winners' calls ran to 45,000 in the web app; the MCP's own cap is unverified · house (observed) |
| `wan3_0`, `wan3_0_prime` | 20,000 — over it the text is **truncated silently** | none | Alibaba Model Studio · confirmed |
| `gemini_omni_flash_1_1` | 20,000, a **house** sanity cap | not stated → house 500 | Gemini API: the limit is the 1,048,576-token context · confirmed |
| `nano_banana_pro` | 50,000 | none | Google: 65,536 tokens shared with images; fal's maxLength · reseller schema |
| `gpt_image_2`, `gpt_image_2_5` | 32,000 · WARN on a mostly non-English prompt over 11,000 | none | OpenAI SDK 3.41.0; the 8,192-token silent-ignore report is one relay's test · confirmed / secondary |
| `kling_omni_image` · `kling_image` | 2,500 | none · a field, 2,500 (text-to-image only) | Kling dev docs · confirmed |
| `kling3_0_turbo`, `kling_o3_*`, `kling_video_edit`, `kling2_6` | 2,500; shots ≤ 6 × 512 | none (2.6: a field, 2,500) | Kling dev docs · confirmed |
| `minimax_hailuo` | 2,000 | none | MiniMax t2v API · confirmed |
| `wan2_7` · `wan2_6` · other `wan2*` | 5,000 · 1,500 · 800, all truncated silently | a field, 500 | Alibaba · confirmed |
| `veo3_1`, `veo3_1_lite` | 3,500 (1,024 tokens less ~15 % for this dense format) | a field, length unstated → house 500 | Gemini API · confirmed |
| `grok_video_v15(_lite)` · `flux_3_video_edit` · `ideogram_4_5` | 4,096 · 4,096 · 10,000 | none · none · a field | fal / BFL schemas · reseller schema / confirmed |
| **house 2,500** — Cinema Studio (3.0, 3.5, 4.0, image 2.5), Soul (2, v2, cinematic), FLUX (2, 3 image, Kontext, 3 video), Seedream (also WARN over 600 words or 300 CJK), `nano_banana_2`, any id with no entry | 2,500, "house ceiling, unknown vendor cap" | Soul/Cinema Studio not exposed (house 500); FLUX and Seedream none | no published cap · unknown |

**The negative is per model too.** `[SUPPRESS]` FAILS above the model's own cap (Kling legacy 2,500, Wan 2.x 500) and
above the house 500 where the cap is not stated. On a model with **no negative field** (Kling 4.0, MiniMax H3,
Seedance, Wan 3.0, Nano Banana Pro, GPT Image, FLUX…) the list is **dropped, never sent**: the lint warns,
`gate.py preflight` leaves it out, and the gate refuses a `negative_prompt` for that model. Write what *is* there in
the blocks (§5.1), and put the nouns in `[CONSTRAINTS]`, the prompt's last block, sent inside it (v2.71.0;
`ai-generation.md`, the guardrails). The sidecar records `negative_channel` and `prompt_ceiling`.

**Still open** (from the research note): Higgsfield's own caps are invisible in its MCP, so a Higgsfield-side limit
below a vendor's figure stays possible (for example 8,000 on `kling4_0`); how a character is counted near a ceiling
(code points, UTF-16 units or bytes); whether Veo errors or truncates; whether the `[CONSTRAINTS]` tail on no-negative models
(v2.71.0: a noun list at the very end, after the description, decided in the Wave 5 plan reviews) summons any noun it
names (§5.2). Not measured yet: it can be measured as one Wave 5 part B arm (the same shot with and without the tail); until then check the take.

### The image edit — `kind: edit`

An edit changes **one concept** in a picture that exists and keeps the rest. Scenario's image-edit page found that
landing an edit and leaving the rest alone are separate skills, that models protect what is named, and that relative
sizes land loosely; its video-edit page converged on the same two closed lists as our own INPUT LOCK
(`specifics-catalogue.md` §6.1): an enumerated keep list, one named concept with numbered items and its reactions, a
label lock, and a close that bans only *other* text (the author's research notes §1.1, §3.1, §3.3). The file:

- frontmatter `edit_of:` — the source picture, a path under the job (required; its hash is recorded) — and
  `edit_of_media:` — the media id the call binds as that picture (the gate refuses the call without it);
- `use: frame` (the default — the result goes to the frame gate like any start frame) or `use: target` (the result
  becomes a **model reference**). `use: target` needs `gate.py approve target:<SHOT>` before the gate lets the edit
  spend, and the lint refuses it on a source whose provenance says `ai-generated`: a target frame is an edit of **our
  own** footage;
- **[SOURCE]** what the source picture is; **[KEEP]** an explicit list that names at least 4 of 8 things — identity
  and face, pose, framing and composition, light direction and colour temperature, lens and perspective, background
  and set, wardrobe, product and label; **[CHANGE]** one concept, numbered parts allowed — and when it adds or
  replaces an object, its placement in frame, its size, its material and how it meets the light (contact, shadow,
  reflection); **[LIGHT MATCH]**; **[REFERENCES]** when refs exist — one line each, its job and a "not";
  **[OUTPUT]** the aspect and resolution, and no text or logos except a product's exact label words;
- a floor: FAIL under 600 characters, WARN under 1,000 `[ASSUMED · house 2026-10-29, to calibrate]` (Scenario's kept
  edit prompts ran 1,179–1,684);
- an image edit written as `kind: frame` with `edit_of:` FAILS, pointing here. The world still reads an edit as the
  picture it makes, so "an edit adds a mover" still refuses (`world-design.md`; jury B6).

A full example — a product swap into an approved start frame (`prompt_lint.py --template edit` prints it):

```
---
shot: S4
kind: edit                # an IMAGE EDIT: one concept changed in a picture that exists (prompting-craft.md §11g)
type: product
model: nano_banana_pro    # an image model; its ceiling is in assets/higgsfield-rates.json → prompt_limits
resolution: 2k            # the 1080p floor applies: the result is a picture every clip inherits
aspect: 9:16
variants: 2
edit_of: 02-startframes/S4_kitchen_v2.png   # the source picture, under the job (its hash is recorded)
edit_of_media: <the media id the call binds as the picture being edited>
use: frame                # frame = the result goes to the frame gate · target = it becomes a MODEL REFERENCE,
                          # allowed only as the owner's gated per-shot opt-in: `gate.py approve target:S4` first
refs:                     # each reference: ONE job, and in [REFERENCES] one line saying what it must NOT bring
  - role: image, what: prop, value: <media id of the real product photo>, not: white sweep, softbox reflections
---
[SOURCE]
Image 1 is the approved start frame for S4: a woman in her forties at a pale limestone kitchen counter at about
ten in the morning, holding a plain unlabelled glass bottle of olive oil in her right hand, photographed at eye level.

[KEEP]
Keep exactly as in Image 1:
- her face, hair and expression
- her pose: right hand around the bottle's neck, left hand flat on the counter
- the framing and composition: her head in the upper third, the counter edge at 70 % of the frame height
- the light: hard morning sun from the left window, warm, long shadows falling to the right
- the lens and perspective: a 50 mm look from eye level
- the background: the open oak shelves, the jar of olives, the doorway soft and out of focus
- her wardrobe: the green linen apron over a white cotton shirt

[CHANGE]
Replace only the bottle in her right hand with the product in Image 2:
1) placement: the same spot in her right hand, lower-left third of the frame, its base on the counter
2) size: 24 cm tall, the same height as the bottle it replaces, about 18 % of the frame height
3) material: dark amber glass, a matte black aluminium cap, a cream paper label printed "Kalamata 500 ml"
4) contact with the light: her fingers wrap the neck and cover the label's left edge; its shadow falls to the right
   on the stone like the jar's; the window shows as a narrow highlight down the bottle's left shoulder

[LIGHT MATCH]
The product takes the frame's own light: the key from the left window, warm morning sun, hard, with the same
shadow direction and softness as the olive jar beside it; none of the studio highlights of Image 2.

[REFERENCES]
Image 2 is the product (prop): its shape, glass colour, cap and label only, not its white sweep, not its softbox reflections, not its shadow.

[OUTPUT]
9:16, 2k, one photographic frame. No text, letters or logos other than the label's own words "Kalamata 500 ml",
spelled exactly as printed.
```

### The detail score

The band says how long; it cannot say whether the characters carry decisions. The lint counts the concrete slots a
prompt fills — each one a thing the model would otherwise fill in its own way, differently every take — FAILS below
a per-kind minimum and writes `detail_score`, `detail_of`, `detail_min` and `detail_missing` into the sidecar, so the
minimums can be calibrated against what was approved.

| Kind | Slots | Minimum `[ASSUMED · house 2026-10-29]` |
|---|---|---|
| frame (9) | lens in mm · light direction · light quality · colour temperature or a named source · camera height or angle · subject size in frame (a % or a shot size) · materials and textures · time of day · background depth | 5 |
| clip (8) | START, MID and END each with a time, and each with a visible state or change · one camera move with its speed (or a locked-off or handheld camera) · a stillness line — what must not change | 3 |
| edit (14) | the 8 KEEP categories · the 4 CHANGE specifics · the light match's direction and its temperature or source | 7 |

**Calibrated on the corpus, 2026-10-29.** A corpus of 356 real prompt files was linted with the old and
the new rules (read-only). Of the 186 that pass today, 179 still pass. The 7 that now fail are all **image edits
written as frames** ("Exactly the reference…", "An edit of the supplied photograph…") — the case `kind: edit` exists
for; the FAIL says so. Clips scored 3–8 and real frames 5–8. The multi-shot form is not scored (its stages are).

**Filler is not detail.** cinematic, stunning, beautiful, epic, breathtaking, masterpiece, 8k, ultra-detailed,
hyperrealistic, award-winning and their kin: a WARN lists them, and past 5 % of the words the prompt FAILS (§2.1).

### Refusals adopted from the Scenario skills

| Rule | Lint / gate | Source |
|---|---|---|
| The word **"watermark"** | FAIL in the prompt. In `[SUPPRESS]` a WARN (existing job lists still carry it), and the gate refuses any call whose `negative_prompt` or Kling argument carries it — so it never leaves the machine | E10: a request carrying it was refused as watermark removal and **still charged** |
| **"No logos" / "no text" on a picture with signs or screens** | WARN on a frame or edit: say what each sign or screen shows (a blank enamel sign, a menu board too far to read, a dark phone screen) | E1: invented lettering under "no logos", on signs, scarves, cars, billboards |
| **A clip that generates sound** (the file turns it on, or the model has no off switch) with no "no music" and no `[SPEECH]` | WARN; "no music" no longer counts as a prohibition | P6 / E6: unrequested scores and murmured voices |
| **A video reference and image references in one call** | WARN until one line names which input decides the framing | P3: the inputs fight over the framing |
| **One concept per edit**, numbered parts | WARN when `[CHANGE]` runs on unnumbered or opens on "also" | the addendum §3.2 (Scenario's edits changed two to five numbered things, one concept) |

### No unlinted route (gate.py)

- **Kling's own connector** (`text_to_image`, `image_to_image`, `text_to_video`, `image_to_video`, `omni_ref_video`,
  `motion_control`) must carry a `prompt` argument identical, after the gate's normalisation, to a prompt file
  `prompt_lint.py` passes **right now**, of the right kind (an image tool takes a frame or an edit, a video tool a
  clip) and **written for a Kling model** — denied otherwise; a match still asks, because the connector's model,
  inputs and duration are not readable. The script approval, a clip's `frame:<SHOT>` and an edit's `target:<SHOT>`
  hold on this route too. Kling motion control without a prompt is denied (house decision M3 is open).
- **Higgsfield's `motion_control`** takes no prompt, so nothing linted can stand behind it: denied.
  ⚠️ **SUPERSEDES IN PLACE** (2026-11-03) — previously: "Genjutsu runs through `generate_video` on an off-roster
  model, so no linted prompt matches it either." Genjutsu (full and Lite, motion transfer and object swap) is on the
  roster through its own lane: a linted `<SHOT>.genjutsu.prompt.md` (`kind: genjutsu`), `gate.py approve
  genjutsu:<SHOT>`, and a call matched to the spec field by field, which always asks (`ai-generation.md` § Genjutsu).
- **Uploads and identity elements** — Kling `file_upload`, `element_create`, `element_update`; Higgsfield
  `media_upload`, `media_upload_widget`, `media_import_url`, `manage_reference_elements` with any action but list or
  get — are **denied with no job open** and **ask** inside one. An identity element is a face stored with the vendor
  as a reusable subject.
- **Scenario**: any server whose name contains "scenario", in any case, with any proxy segment or suffix — a
  `model_run`, a generation, a training or an `upload_asset` is **denied always**, inside a job or out: *Scenario is
  not a provider (2026-10-28)*. `hooks/hooks.json` routes it to the gate.
- **The duplicate-spend guard.** A PostToolUse hook (`gate.py posthook`) logs every generate request the vendor
  accepted, by its hash and the job id it returned; an identical request in the same job within 30 minutes asks:
  "already submitted at <time>; poll that job instead". A response with no job id records nothing, and a client-side
  timeout fires no PostToolUse, so that case is still the operator's to check (Scenario E11: a timeout resubmitted is
  paid twice).

## 12. The scene form (v2.49) — approved sheets and one long structured prompt, no start frame

**Sources.** the author's research notes — 12 Higgsfield festival films, 88.8 minutes, 4,712
video calls read from the projects' own asset feeds `[SECONDARY · festival study 2026-11-05]`; the house rule
on it `[OWNER · 2026-11-05]`: *"do it as they do it"*, *"template + long prompts"*. Everything below is in our
own words. No team's prompt, template or script is reused: the festival rules do not license them (HFF-19).

**What it is.** A clip built from **approved reference sheets** (`character:`, `prop:`, `world:`) and a long
prompt in the vendor's block order, instead of from an approved start frame. The winners worked this way:
start frames were rare (12 of 629 calls in the 1st-place film, 22 of 838 in another), and references sat on
93–99 % of calls in five films. On Seedance a start image was never a true first frame anyway: it binds as a
reference and lands close, not exact (`multishot.md` §3).

**When it is the default.** Every clip on `seedance_2_5` since v2.49. `cinematic_studio_video_4_0` reads the
same blocks but is **not on the roster**; it joins the lint's scene models when the owner adds it
(`ai-generation.md`, the roster), and until then `form: scene` on it WARNs that the template is written for
Seedance. The scene form does not apply when:
- the job's checkpoint turns on `frame-led` (§1): the lint refuses `form: scene` and every clip is i2v;
- the clip binds a `start_frame:`: the frame gate holds for it;
- the clip is a planned multi-shot with internal cuts the edit relies on: `form: multishot` (below).

`prompt_lint.py --template scene` prints the template. Its frontmatter carries `form: scene`, `model:`,
`resolution:` (720p allowed, 1080p preferred for wide plates and close faces: `ai-generation.md`, the quality
floor), `cut:` and `duration:`, `generate_audio: true`, `function:`, `payload:`, `world:` and `refs:`.

**What the lint and the gate hold.**
- The lint FAILs a scene clip with **no `refs:` and no `start_frame:`**: with neither, every take invents the
  cast and the place. It FAILs a missing required block and WARNs on a block the template does not name.
- The i2v bans (`[LIGHTING]`, `[STYLE]`, `[ENVIRONMENT]` and the rest of the frame blocks in a clip, and the
  `STYLE:` line) do **not** apply: no frame owns the look, so the prompt carries it. The detail score is not
  computed for this form.
- `gate.py`: with no start frame bound, **every bound image must be an approved sheet with its media id** —
  `character:<NAME>`, `prop:<NAME>`, `world:<LOCATION>`, or `frame:`/`endframe:`. A clip that binds none is
  refused. The sheets are the approval point now (`character-and-props.md`, the sheet rules).
- The call's `generate_audio` must equal the file's. Kept sound needs no approval; speech does (§9.4b).

**The blocks, in order.** Required: `[SCENE CONTEXT]` `[ACTIVE REFERENCES]` `[LOCATION MAP]` `[FIRST FRAME]`
`[CAMERA]` `[ACTION TIMING]` `[LIGHTING]` `[AUDIO]` `[POSITIVE LOCKS]`. Optional: `[FORMAT MODE]` `[OPTICS]`
`[PERFORMANCE]` `[PHYSICS]` `[COLOR]` `[STYLE]` `[TONE]` `[SHOTS]` `[WARDROBE]` `[OUTPUT SETTINGS]` `[SPEECH]`
`[SUPPRESS]` `[REPAIR]` `[CONSTRAINTS]` (last, v2.71.0). The lint checks that the required ones are there, and
warns only when `[CONSTRAINTS]` is not last. Keep the
template's order anyway, so every clip of a job reads the same to the model and to the reviewer (§3.2: order
is a legibility convention until a test says more).

- **[SCENE CONTEXT]** — two or three sentences: where we are in the story, what this shot is for, the one
  thing that happens. It is the shot's `function:` and `payload:` in prose. A model given the purpose makes
  fewer choices against it, and a reviewer can check the take against one sentence.
- **[ACTIVE REFERENCES]** — one line per bound sheet, **one subject per line**, each saying what that sheet
  controls and only that: *"@Image 1: the courier — face, hair and wardrobe only"*; *"@Image 3: the rooftop —
  the space and its materials only; the light comes from [LIGHTING]"*. `@Image N` is the N-th entry of
  `refs:` in file order (with no start frame there is nothing ahead of them). Never a range, and a tag only for
  a subject present in this shot (§6b). The `not:` scope in `refs:` says what each sheet must not bring (§11d
  item 1). The lint WARNs when no line binds a reference by tag.
- **[LOCATION MAP]** — the space as this camera sees it: what is screen-left, screen-right and behind; the
  distances between people and objects **in metres**; where the light enters. No frame fixes the geography
  now, so this block does. It is also what the scene board compares across shots (`review-and-approval.md`,
  the scene board): the same map, pasted into every shot of the scene, is what keeps the table where it was.
- **[FIRST FRAME]** — the opening picture **with the action already under way**: who is where, facing which
  way, holding what. Never an empty room or an establishing beat before the entrance; a model spends the head
  of a clip arriving, and those seconds are not usable. The lint WARNs on an empty or establishing opening.
- **[FORMAT MODE]** — one continuous take in real time with no cuts and no speed change, or a short cut list
  in `[SHOTS]`. Say which; the model will otherwise decide.
- **[OPTICS]** — the field of view in degrees and/or the focal length in mm, the camera's distance from the
  subject in metres, and the depth of field. Our frame-stage test rejected degrees on an image model
  (`cinematography-craft.md` §7.1), but the video stage is untested (§11d, open) and the winners split between
  the two; writing both covers either reading. Distance matters as much as the lens: subject size in frame
  follows from the two together, and it is the first thing that drifts between shots.
- **[CAMERA]** — **one camera behaviour**: who or what moves it (a person walking backwards, a locked
  tripod, a slow dolly), at what height, and how it follows. A second behaviour is a contradiction (§2.4,
  §11 item 9).
- **[ACTION TIMING]** — timed beats, `0–3 s: …`, each one a visible state or change, the last one the end
  state the clip settles into. Ranges are budgets, not cuts (`multishot.md` §5). Timestamps are the only
  documented fine timing control (§9.1), and the end state is what the edit cuts on.
- **[SHOTS]** — only when `[FORMAT MODE]` says the clip cuts: the cuts in order, each with its size and what
  changes. The lint does not check this block. When the edit depends on where the cuts land, or a clip cuts
  more than once or twice, use `form: multishot` instead: its lint checks that stages tile the duration, that
  each has an end state, and that every cut has a type.
- **[PERFORMANCE]** — **the performance card** (`direction.md` §1), the same in every form: **STATE as a
  transition** (`skeptical → curious`, never one held state: a held state reads as a mask), one **BEAT**, the
  **FACE**, the **GAZE** (with a **TARGET** when the gaze would otherwise point nowhere, and a **STIMULUS** on a
  reaction). Write visible behaviour — jaw, eyes, brows, breath, posture, hands — never an emotion word on its own
  (a house rule: vendor advice and one small test, not a study; research note R4). The lint FAILS a dialogue or
  reaction clip without the card and WARNs on a STATE that is not a transition. Restraint; no look to the lens;
  **mouths closed unless a line is scripted in `[SPEECH]`**. With several characters, one card each. For example
  (v2.70.0: `prompt_lint.py --selftest` holds this example to the lint's own rules):

  <!-- perf-example -->
  ```
  STATE: guarded → curious
  BEAT: she reads the date on the neck, then looks up
  FACE: brows lift a little, jaw loosens, lips stay closed
  GAZE: down to the label, then up to the buyer
  TARGET: the buyer across the counter
  ```
  <!-- /perf-example --> A non-human lead is written as a performer in a worn suit, which
  gets human weight and timing out of the model. Mouth-opening words with sound on make a character talk: the
  lint WARNs on them (`shot-handoff.md` §1.3).
- **[PHYSICS]** — weight and contact, cloth and hair, what moves because of what. Argue an outcome from
  physics or the model resolves it in your favour (§11d item 3).
- **[LIGHTING]** — the motivated source, its direction, its hardness, and what it does across the frame. The
  location sheet is shot on a neutral base so this block can relight it per shot (`character-and-props.md`).
- **[COLOR]** — the palette in plain words, and what must not shift (*"the jacket stays olive"*). Look-alike
  characters are told apart here by one dominant colour each (below).
- **[AUDIO]** — what the clip sounds like and what it must not sound like, first, in one sentence. Then
  `AMBIENCE:` (the bed: air, room tone, distant sources), `SFX:` (sounds tied to the action, **off-screen
  sources with their direction**, any cue at a stated second: *"the hand scrapes the wall at 4 s"*), and
  `MUSIC: none`. Native sound is kept as production sound since v2.49 and can be replaced in the edit at any
  time (`editing-and-audio.md` §7d); music is the owner's choice, laid in the edit. The lint WARNs when
  `[AUDIO]` never says "no music" and when it names no ambience.
- **[SPEECH]** — scripted lines as `NAME: "…"` at stated seconds, the `VOICE:` line pasted from the
  character's sheet, the emotion on its own line, the silences timed (§9.4b). A line makes the clip speak, and
  the voice gate applies.
- **[STYLE]** — the capture medium and texture in plain words; never a film's or a director's name (§2.3).
- **[TONE]** — the tone as a rule the shot defends, when the scene could drift (warm, not sinister). One
  winner rebuilt whole sequences that drifted out of tone; a stated rule is what he checked them against.
- **[WARDROBE]** — which state of the character's sheet this shot uses (`character-and-props.md`, one sheet
  per state), and only what the sheet does not show. The sheet carries the clothes; re-describing them
  competes with it (§6b).
- **[OUTPUT SETTINGS]** — only what the model must read in words. The call's aspect, resolution and duration
  come from the frontmatter, and the gate compares the call to the file.
- **[CONSTRAINTS]** — Seedance has no negative field, so a `[SUPPRESS]` would be dropped (§11g). Write what must
  stay out as what is there, in `[POSITIVE LOCKS]`, and the peripheral nouns (props, background, text, panels) as a
  comma-separated list in `[CONSTRAINTS]`, the last block (v2.71.0). Anatomy stays positive only: Seedance has no
  field for it.
- **[REPAIR]** — on a corrective retake, the one failure being fixed and its cause, so `prompt_lint.py
  --against` can count the variables (`refinement-loop.md` §1b). A masked region repair is its own route
  (`editing-and-audio.md`, Region repair).
- **[POSITIVE LOCKS]** — the last description block (only `[CONSTRAINTS]` follows it): every fact at risk of drifting, restated as the wanted state, once each —
  counts, positions, hands, wardrobe, screen direction, which side the drop is on (§11d item 5;
  `shot-handoff.md` §7).

**Length.** The lint WARNs under **2,500** characters: below that the look, the place and the blocking cannot
all be written, and what the prompt leaves out the model invents, differently each take. The winners' median
of medians was about **6,400** (2,700–16,300). It FAILs over **20,000**, the house ceiling, which is past
anything measured. The MCP's own cap is **unverified**: before the first long call of a job, probe it with
`get_cost: true` (it spends nothing) and record what the server accepted. Whether the model reads all of a
long prompt is unknown. Length still buys nothing by itself: one lock restated four times is four demands
buying one (§2.2). The 1,800–2,100 band (§2.2b) stays the rule for frames and i2v clips; the multi-shot form
keeps 3,900.

**Look-alike characters (HFF-05).** When two characters could be mistaken for each other (two rabbits, two
couriers in the same uniform), give each **one dominant colour** and name it the same way every time:
*"the rust-red rabbit"*, never *"the red one"* in one clip and *"the ginger rabbit"* in the next. Use the
name in `[ACTIVE REFERENCES]`, `[COLOR]` and `[POSITIVE LOCKS]`, and in the sheet (`character-and-props.md`).

**Chinese-language bodies — an open test (HFF-13).** Two winning teams wrote the body of their Seedance
prompts in Chinese with English block headers. Not adopted: the house writes in English (a locked rule), the
lint warns over 500 CJK characters on Seedance, and nobody here can check the wording of a Chinese prompt
against the script. It stays a named test: one paired EN/ZH clip on the same sheets, in an evaluation job
(`Tier: evaluation`), with owner-approved spend, read for identity, blocking and adherence.

### 12a. Scene files and the project DNA — the shared text written once

**Why.** A scene stays consistent when its shots say the same things in the same words. We measured how much
text the winners reused verbatim between the shots of one scene `[SECONDARY · festival study 2026-11-05]`:

| Film | Text shared verbatim across shots of a scene |
|---|---|
| CONTROL (1st place) | 39 % |
| Soulless | 33 % |
| Listen to Meh | 25 % |
| BALLAST | 5 % (same block structure, fresh text each shot) |

By block, the pattern was the same in every film that reused text: style and format lines **100 %** shared;
cast bindings 45–100 %; constraints 31–73 %; light, optics, camera and location map about 30–40 %; action,
first frame and performance **0–17 %**. One film's element map was pasted unchanged into every shot. So the
place, the cast, the look and the locks are written once; what happens is written per shot. Copying by hand
is where drift creeps in: one shot gets the edited map, its neighbour keeps the old one, and the table moves
(the production lessons, 2026-11-05).

**The files.** In `01-script/scenes/`:
- `_PROJECT.dna.md` — what every scene-form shot of the film carries: `[STYLE]`, `[FORMAT MODE]`, `[OUTPUT
  SETTINGS]`, film-wide `[POSITIVE LOCKS]`. `prompt_lint.py --template dna` prints it.
- `<SCENE>.scene.md` — one per scene: frontmatter `scene:`, `model:`, `aspect:`, `world:`, `time:` and the
  scene's `refs:`; blocks `[ACTIVE REFERENCES]`, `[LOCATION MAP]`, `[WARDROBE]`, `[LIGHTING]`, `[COLOR]`,
  `[AUDIO]` (the ambience bed and the `VOICE:` strings), `[POSITIVE LOCKS]`. `--template scene-file` prints it.
- The shot prompt (`01-script/prompts/<SHOT>.clip.prompt.md`) names `scene: <SCENE>` and `setup: <A|B|C…>`
  and writes only its own blocks: `[SCENE CONTEXT]`, `[FIRST FRAME]`, `[OPTICS]` (unless the setup's lens is
  in the scene file), `[CAMERA]`, `[ACTION TIMING]`, `[PERFORMANCE]`, and anything this shot adds.

**What the lint does with them.** A shot that names `scene:` is **assembled** before it is linted: block by
block, in the template's order, the DNA text, then the scene text, then the shot's own text, pasted together.
The scene's `refs:` come first, so `@Image 1` is the same sheet in every shot of the scene; the shot's own refs
follow. `world:`, `aspect:` and `model:` are inherited when the shot leaves them blank. The assembled prompt
is what gets linted, hashed and sent. A missing scene file FAILs by name. The sidecar records the DNA and
scene files and their hashes.

**Changing a shared block.** Edit the scene file and every shot in it lints to a different prompt, so the
gate's re-lint refuses the old sidecars until each shot is re-linted. That is the point: one edit, every shot,
nothing left behind.

**A shot that must differ.** It says so in its frontmatter: `override: LIGHTING — the door opens and daylight
floods in`. The block name, a dash, and a reason of at least three words; several overrides are separated by
`;`. The shot's own `[LIGHTING]` then **replaces** the shared one instead of adding to it. The lint FAILs an
override with no reason, one that names a block the DNA and scene do not have, and one whose shot writes no
replacement. Without an override a shot's block is appended to the shared text, which is right for adding
(a prop that enters) and wrong for contradicting (the light changes): contradicting text in one block is the
model's choice to resolve.

**The scene check.** `prompt_lint.py --scene <SCENE>` lints every shot that names the scene and runs the
cross-shot checks a single file cannot make:
- **one `setup:` = one lens and one distance**: two shots on the same setup with different `[OPTICS]` FAIL
  (put the setup's optics in the scene file, or give the shots different setup ids);
- a shot with no `setup:` WARNs;
- each shot's assembled length and bound refs are listed, so the board can read them side by side.

**Still read by eye.** The lint compares text. It cannot see whether the takes agree: the lens the model
actually used, camera height, subject size, distances between objects, where the furniture stands, wardrobe,
light direction. That is the scene board (`review-and-approval.md` §11), done before any approval request,
with the list of what was compared written into the request. A script that measures a take against its setup's
plate (zoom, camera move, horizon, face size) is planned for 2.50; the research behind it is
in the author's research notes (not shipped).

## 13. What this file cannot settle

Named with the same prominence as the findings, per `research-quality.md` §6.

1. **ByteDance/Seedance official prompt guides** — four official URLs identified, all JS-rendered
   SPAs returning navigation shells. **The "official six-part formula" is unverified.** Needs a
   browser fetch.
2. **Kling's own API reference** — every Kling *schema* number here (2,500-char negative,
   `cfg_scale`, `camera_control` [-10,10], `image_tail` pro-only, `dynamic_masks` ×6) comes from
   third-party mirrors that agree with each other, which is not independent convergence. Kling's
   *prose* guides are [P].
3. **Google's canonical Vertex Veo prompt guide body** — the negative rule and the seven-element
   table were recovered from a **verbatim mirror**, not a Google-served page.
4. **Any controlled test that quality words hurt** — strong vendor assertions, **no published
   ablation** with held-out prompts and blind scoring.
5. **Whether lens focal lengths do anything beyond style association** — §4.1's verdict is inference
   from vendor framing, labelled as such.
6. **Whether reverse activation (§5.2) occurs on 2026 hosted video models** — the ECCV result was
   established on Stable Diffusion; hosted implementations are untested publicly, and timing is not
   user-controllable regardless.
7. **Any rigorous lipsync comparison between models** — the most-cited 2026 test has, on its own
   account, no sample sizes, no controlled variables, no objective metrics and no blind evaluation,
   and is authored by a vendor co-founder. Its failure-mode taxonomy is a **hypothesis list for your
   own bake-off**, never a ranking.
8. **Whether i2v measurably beats t2v on output quality** — the control argument is airtight; the
   quality claim is asserted by practitioners, never measured.
9. **BFL's negation inconsistency in voice guardrails** (§9.4) — unexplained by the vendor,
   untested.
10. **Model version currency** — every version number here is a claim with a shelf life; the shot
    manifest's model-version column is the drift alarm.
11. **GenEval 2's contents** — only the "benchmark drift" framing is confirmed; the paper was not
    read.
12. **Whether the §2.1 vocabulary bank transfers to video models at all.** Every term in it comes
    from still-image practice, four Midjourney books deep, and **not one of those books tested a
    video model.** The shot-size and lighting axes are indirectly supported by Wan's and FLUX's own
    tables; the format, optics and material axes are not. One afternoon — eight fixed start frames,
    one varied axis per run — settles it per model, and it is the cheapest unrun test named here.
13. **Whether Seedance reads all of a 6,000-character prompt, and the MCP's own prompt cap** (§12). The
    winners' long prompts are evidence that the web app takes them, not that the model uses every block.
    Length against adherence on the first scene-form jobs measures it.
14. **Whether a Chinese-language body beats English on Seedance** (§12, HFF-13) — one paired test.

**Cross-refs:** `ai-generation.md` (the house format, roster, lipsync routing, guardrails, retake
economics — all owned there) · `realism-qa.md` (the artifact-side tells these prompts try to avoid)
· `photorealism-physics.md` (what light and materials should be doing; this file says only how to
ask) · `cinematography-craft.md` (which shot the scene wants) · `character-and-props.md` (what a
character description must contain) · `script-craft.md` (line length, a script decision before a
prompt one) · `research-quality.md` (tiers, decay, the refutation pass).
