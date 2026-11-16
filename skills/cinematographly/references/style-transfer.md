# Style transfer — using a director or genre without invoking one

**When to read this:** a client says "make it feel like Fincher", you want a genre register you can
actually specify, or you are tempted to put a DP's name in a prompt. `cinematography-craft.md` is
the craft; `prompting-craft.md` §2 is why the name itself does nothing. **This file is the bridge:
how to convert a style reference into parameters that can be supplied.** When you hold the
reference clip itself rather than a name, measure it instead: `shot-relationships.md` reads its
shots and joins (`shot_graph.py`) and maps them onto new content (`replicate.py`), flagged.

Sources tiered per `research-quality.md`, checked **2026-08-29**. The craft is durable; the platform
claims in §5 decay in about a quarter.

---

## 1. The rule, and why it is not pedantry

⛔ **The name never goes in the prompt.** Artist and DP invocation is on this skill's refused list
because vendors document it as ineffective or harmful (`prompting-craft.md` §2). But the *reference*
is not worthless — it is a compression. "Fincher" is shorthand for a dozen decisions, and those
decisions are individually specifiable. **Decompress the name into parameters, then supply the
parameters.** That is the whole method.

Two things the research changed, and both should make you more careful with any style lookup —
including this one:

- **Director "rules" are usually project dogma retold as career doctrine.** Fincher's *Zodiac*
  famously "never moves the camera and never used a Steadicam" [PRIMARY · Fincher/Savides, ASC] —
  and *The Killer* is substantially handheld, deliberately destabilised in post [PRIMARY · RED].
  Robert Yeoman says of Wes Anderson "we don't use technocranes" while the ASC's own *Moonrise
  Kingdom* report documents a Technocrane shot on that film [PRIMARY, both]. **The contradiction is
  left standing here on purpose**: it is the clearest evidence that these are per-project decisions,
  not signatures.
- **Nobody gives you a lighting ratio.** Not one primary source in the sweep gave a numeric
  key-to-fill for any of these styles, and Deakins refuses the concept outright: *"mine is not a
  mathematical approach… I just use my eye"* [PRIMARY · rogerdeakins.com]. Any style guide quoting
  "Deakins = 4:1" is fabricating. What transfers from Deakins is a **procedure** — one dominant
  motivated source, visible falloff, no cosmetic fill, decided at capture — not a number.

---

## 2. The decomposition table

Each row replaces a name with what you would actually specify. Camera-movement mechanisms are in
`motion-design.md`; lighting and lens reasoning in `cinematography-craft.md`.

| Reference | Movement | Lens / perspective | Light | Palette & exposure | Staging |
|---|---|---|---|---|---|
| **Fincher** | Locked or minimal dolly; a move is licensed only by *space* or *subjectivity* — "if a director feels the need to move the camera simply to make it interesting, the scene isn't interesting" [PRIMARY · Messerschmidt ASC] | **Few focal lengths, repeated.** Cronenweth: 21–40mm is "2/3 or more of the movies"; *Mindhunter* on three lenses. The formality comes from repetition, not from an unusual lens | Motivated from the set, mixed colour temperature, "nothing looks lit" [PRIMARY · ASC] | Protect the toe; shadows hold detail. Hue-only LUTs that leave gamma and contrast alone [PRIMARY · RED] | Choreographed marks; actors structured and consistent |
| **Deakins** | Restrained, motivated | 25–50mm working range in his own words; **40mm for close-ups** — not a signature number | **One dominant motivated source**, judged by eye | *"Make the decision when you shoot, not in post"* | Naturalistic |
| **Malick / Lubezki** | Roaming handheld ↔ Steadicam, swapped continuously; actor-led, discovered like a documentary crew [PRIMARY · Widmer] | **Restricted set of short focal lengths** — *The New World* used three for the whole film "so not to change the perspective of the audience". Exaggerated depth, wide lens close | Available light, near-exclusively; light scheduled as a character | Naturalistic, unfiltered | Harvested, not blocked |
| **Wes Anderson** | Dolly on track; manual whip pans; snap zooms (12mm on *Moonrise*) | Project-specific, not a signature: 27mm on *Bottle Rocket*, ~90% on one 40mm anamorphic for *Rushmore*/*Tenenbaums* | Even, flat frontality | **Warmer and more saturated in the DI than captured** [PRIMARY · Yeoman] | **Planimetric**: camera perpendicular to a rear wall, figures "strung across the frame like clothes on a line" [PRIMARY · Bordwell]. **Deep focus — T11 exteriors, T4 minimum interiors** |
| **Vérité / doc** | Reactive handheld, shoulder-borne, sustained | ⛔ **Not long-lens observation** — Maysles: *"I'd rather be very close, rather than rely on the zoom"* [PRIMARY] | Available light; exposure ridden live, and visible drift is authentic rather than an error | — | **Close, centred, filled frame.** He rejects offset composition: "that empty space is a distraction" |
| **Lifestyle / wellness ad** | Slow, continuous, motivated by product reveal rather than narrative [UNVERIFIED — universally practised, no named practitioner source found] | **Large format + portrait-length glass**: wide framing *with* shallow separation, which S35 cannot do — this is the actual mechanism behind the "expensive" look [PRIMARY · Zabé ASC] | One large soft source, shadow-suppressing | *"Digital looks best when it's underexposed"* [PRIMARY · Zabé] | Product-led |
| **UGC / phone-native** | Movement in frame immediately, for the scroll-stop; motivation irrelevant | Phone-lens deep focus. **Shallow DOF reads as an ad** | Bright and legible on a phone outdoors | Saturated, high contrast, thumbnail-legible | Face-filling vertical |

---

## 3. Genre, honestly graded

- **Horror — partly evidenced.** The usable principle is placement, not palette: *"where the shadows
  are is where the audience doesn't want to be. If you put the main character in the light and
  surround that person with shadows, the audience instinctively wants to know what's going on in
  that darkness"* [PRIMARY · Roy H. Wagner ASC]. Selective underexposure to *withhold identity* is
  the same tool used narratively.
- **Comedy — contested, and the "rule" is wrong.** What is sourced: master-shot discipline — *"place
  the camera as if you had to tell the entire scene in one shot, from one angle"* [PRIMARY · Julio
  Macat]; wide lens close in; symmetrical wides **held slightly too long**, humour from awkward
  duration; zoom as punctuation. What is *not* sourced: that comedy must be flat-lit and static —
  contradicted by the practitioners themselves.
- **Thriller — no evidence base.** The sweep found **no** primary or empirical source establishing a
  distinct thriller parameter set. Long-lens paranoia, cool desaturation, off-centre threat framing
  are [UNVERIFIED] conventions. Build "thriller" as a *combination* of sourced parameters —
  restrained movement, low-key motivated single source, narrow lens set, cool hue-only LUT — not as
  a token.
- **Romance / warmth — the evidence is about colour association, not film.** A systematic review of
  132 articles, 42,266 participants, 64 countries [PRIMARY · Jonauskaite & Mohr] finds yellow/orange
  reliably positive and high-arousal, blue/green positive but *low*-arousal, light positive and dark
  negative. ⛔ **But the authors' own caveat is the load-bearing part**: most studies measured
  *abstract* colour–emotion associations, not whether colour changes experienced emotion in context,
  and the corpus is Western-dominated. So "warm = romantic" is supported as an association and
  **unsupported as a demonstrated effect in moving image**. Use it as a starting hypothesis.
- **Close-ups have a saturation point.** An experiment (N = 495, 13 cuts of one film) found close-up
  frequency raises spontaneous mental-state attribution — viewers thinking about what a character
  feels — on an **inverted U**: past a point, more close-ups *reduce* it [PRIMARY · Bálint et al.,
  *Poetics* 2020]. A deliberate close-up count beats a close-up-dominated cut.

⛔ **Do not quote average shot lengths as director signatures.** The mean is badly distorted by
outliers — in one analysis 7% of shots inflated a film's ASL by 33% [PRIMARY · Redfern] — and the
database most figures come from is crowd-sourced and self-described as inexact. If you must use one,
use the **median**, and treat any figure as ±30%.

---

## 4. What survives 9:16 at 40 seconds

**Survives intact** — everything frame-local: lighting direction, hardness and falloff;
single-source discipline (arguably *better* small, because one source survives downscaling where
five turn to mush); palette and hue relationships; symmetry and dead-centre framing (a vertical
frame has a stronger centre axis than 2.39, so this transfers better, not worse); frontality; close
proximity; whip pans and snap zooms as punctuation.

**Survives only if re-specified:**

- ⛔ **Focal length in millimetres does not transfer.** A 40mm S35 framing has a completely different
  field once cropped to 9:16. **Specify apparent subject distance and framing — head-and-shoulders,
  waist-up, full-figure — plus perspective character: compressed, neutral or exaggerated.** Never a
  mm number. This is the single most common style-transfer failure.
- **Exposure placement.** Fincher's protected toe and "underexpose it" both assume a screening
  condition. On a phone at outdoor brightness, low-key becomes a black rectangle — re-balance upward
  and give it a specular anchor.
- **Depth of field.** Shallow separation needs a large sensor to look like anything; in a
  phone-native register it is a tell rather than a virtue.

**Does not transfer at all** — these are duration and format devices, not looks: Anderson's
planimetric clothesline (an inherently *horizontal* organisation; 9:16 is the worst container for it
— keep the centred frontal symmetry on one subject, the palette and the snap pan, and drop the
staging system); Malick's whole method (15–40 minute takes, harvested coverage, schedule
subordinated to weather — the look transfers, the process cannot); Fincher's two-camera
cross-coverage (a dialogue apparatus, and a 40s spot has no dialogue scene to cover); deep-focus T11
(everything-sharp reads flat and cheap on a phone); ratio-as-narrative-variable; and **cut rhythm as
signature** — at Haneke's pace you get two shots in 55 seconds.

**The real container**, at 35–55s with a 3-second value proposition: roughly **one hook shot, 8–20
body shots, and a close.** Any style whose identity depends on duration or coverage volume must be
reduced to its frame-local parameters and its temporal signature discarded.

---

## 5. ⛔ The mode routing — the most important rule in this file

**For UGC, "cinematic" is a negative signal, and the platform says so itself.** TikTok's own
performance guidance instructs advertisers to *"maintain DIY or not overly polished aesthetic"*
[PRIMARY · TikTok for Business, checked 2026-08-29]. Every parameter that reads as expensive in a
feature reads as *advertisement* on a feed — and an ad is the thing a scrolling viewer is deciding
whether to skip.

| | Cinematic toolkit | What UGC needs instead |
|---|---|---|
| Movement | Motivated, restrained | Movement in frame at once; motivation irrelevant |
| Camera | Locked-off formality | Handheld imperfection reads as authenticity |
| Information | Slow reveal, deferred | Value proposition inside 3 seconds |
| Exposure | Low-key, protected shadows | Bright, legible on a phone outdoors |
| Depth | Shallow separation, portrait glass | Deep focus; shallow DOF reads as *ad* |
| Palette | Discipline, desaturation | Saturated, thumbnail-legible |
| Sound | Design under picture | Sound-forward, often the whole hook |
| Pace | Long takes | Fast scene changes early |

So: **`modes/narrative-promo.md` (Mode A) can carry this file. `modes/ugc-volume.md` (Mode B) mostly
must not.** The parameters that cross over into UGC are the frame-local ones that make an image
*good* rather than *expensive* — light direction, one source, palette coherence, close proximity,
centred framing. Everything else in §2 is Mode A vocabulary, and reaching for it in a volume batch
is how a UGC ad starts reading as a commercial. This is the same argument `photorealism-physics.md`
§8 makes about grain and halation: **the reference is a phone, not an ARRI.**

---

## 5b. ⛔ When the model has no such feature — the general rule

A named look often implies a *capability* the roster does not have: anamorphic, a 1.33× phone
adapter, a tilt-shift, a specific film stock, a shutter effect. **The name of the feature is not the
thing you want** — the visible artifacts it produces are. So the rule is the same one this whole file
is built on, applied one level down:

> **Decompose the feature into its visible artifacts, then decide for each artifact: recreate it
> prompt-side, or add it post-side. Never name the absent feature and hope.**

| Step | Question | Example — "anamorphic" |
|---|---|---|
| 1 | What does it actually *do* to the image? | Oval bokeh · horizontal flares · edge stretching · shallower apparent depth · a wider frame |
| 2 | Which artifacts are **in the frame** (prompt-side)? | Bokeh shape and the depth character — these must be in the generated pixels |
| 3 | Which are **on** the frame (post-side)? | Flares, subtle horizontal stretch, the crop — all cheaper and more controllable in the edit |
| 4 | Which are just the **format**? | The wide frame is an aspect decision, not a lens one — and ⛔ in 9:16 it is unavailable by definition |

**Worked second case — the 1.33× phone adapter.** Prompt-side: oval highlight bokeh, a slight
horizontal squeeze on faces at the frame edge. Post-side: a horizontal flare pass and a mild
anamorphic-style stretch. ⛔ **What you must not do is write "1.33x anamorphic adapter" into the
prompt** — it is a gear name, it belongs to the refused-folklore list in §1, and the model will
either ignore it or return a picture *of* a lens.

⛔ **And the honest half:** some artifacts are simply not available. If the deciding artifact is
post-side-only and the client wants it in the generated plate, say so and price the post pass —
do not spend generations discovering it.

## 6. Where each axis is actually controlled

Slots into `cinematography-craft.md` §7's prompt / start-frame / post / impossible split.

| Axis | Reference image / start frame | At generation | In post | Impossible |
|---|---|---|---|---|
| Light direction, hardness, falloff | ✅ **primary carrier** | — | shaping only | relighting |
| Exposure & contrast placement | ✅ | — | ✅ curve, toe | — |
| Palette | ✅ | — | ✅ **best here** — hue-only, per Fincher's LUT model | — |
| Lens perspective character | ✅ baked into the still | — | — | ❌ specifying "35mm" |
| Depth of field | ✅ | partial | slight | precise focus plane |
| Blocking, symmetry, frontality | ✅ **primary carrier** | — | crop only | — |
| Camera movement class | ❌ | ✅ **must be here** (`motion-design.md`) | — | motorised repeatability |
| Move speed | ❌ | ✅ | ✅ ramps | exact velocity |
| Handheld micro-jitter | ❌ | ✅ | ✅ addable — *The Killer* did exactly this | — |
| Cut rhythm | ❌ | ❌ | ✅ **entirely an edit decision** | cuts inside one clip |
| Continuity across shots | ✅ via locked reference | partial | — | ❌ reliable without one |

Two principles govern the table. **Deakins' rule applies directly to generation**: *make the
decision when you shoot, not in post* — anything a reference image can carry should be carried
there, because it is deterministic in a reference and probabilistic in a sampler. And **Fincher's
LUT discipline is the grade model**: adjust hue without touching gamma or contrast, which is what
keeps independently generated shots looking like one series.

---

## 7. What this file cannot settle

- **No numeric lighting ratio exists in the primary record for any style here.** Where you want one,
  you are choosing a reference frame, not reading a spec.
- The **lifestyle/wellness** row is the weakest: its camera-movement conventions are practised
  everywhere and documented by nobody I could reach. Treat as convention.
- Platform guidance in §5 is TikTok's first-party documentation. **Meta's equivalent was not
  retrievable**, so the cross-platform generality of those rules is [UNVERIFIED].
- Everything here describes how a style *looks*, not whether it *suits the brief*. A perfectly
  decomposed Fincher register on a sleep-aid ad is a well-executed mistake (`ideation.md`).
