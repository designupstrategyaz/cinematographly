# Photorealism Physics — why a frame reads captured, and what to do when it doesn't

**When to read this:** a clip is technically clean and still reads fake and nobody can name why; you
are deciding whether a shot is fixable in post or has to be regenerated; you are building the
finishing chain for a piece that must pass as real capture; or you are picking a model for a shot
with physics in it. `realism-qa.md` owns the symptom list (V1–V15 / A1–A7), the QA card and the
batch rule — go there for *what to look for and what to prompt*. This file is the layer underneath:
*why* each tell exists, and which can be put back, how, and at what limit.

Tiered per `research-quality.md`, checked **2026-08-28**. **§§1–6 are capture physics and do not
decay** — glass obeyed cos⁴ in 1950 and will in 2035. **§9 is model-specific 2026 behaviour and goes
stale in about a quarter**; re-verify it as a block. `[UNVERIFIED]` means analytical inference from
the primary material, kept as inference — nothing is upgraded by repetition.

---

## 1. The thesis: an artifact is a field, not a style

A real frame is not a picture of a scene. It is **a record of a light field having been mangled by a
specific piece of glass onto a specific piece of silicon**, and every artifact in it is a *function*
— of field position, depth, aperture, exposure zone, time. A generative model learns those artifacts
as *texture statistics correlated with content*, not as functions of those variables, so they appear
as a **flat style** rather than a **field**. That mismatch — artifact present, not varying correctly
across the frame — is the physical layer of the uncanny `[UNVERIFIED · synthesis]`. Two sources
point at it independently: Schröer's VFX practice exists because these artifacts must be reproduced
*as spatial fields derived from a shot lens grid* `[SECONDARY · Christoph Schröer · checked
2026-08-28]`, and practitioners report AI footage arrives "too clean… every frame area equally sharp
and resolved, unlike real lenses with natural falloff" `[SECONDARY · DesignHero TV · checked
2026-08-28]`.

**The method this file is really teaching**, and why it covers frames it never anticipated: name the
variable an artifact is physically a function of, then compare two places that differ in it. Centre
vs corner. Near vs far. Shadow vs highlight. Frame 1 vs frame 30. Identical in both means it was
painted on.

**Frame test (the general one).** At 100 %, sample the artifact at frame centre and at 80 % field
height and write both values down. A vignette equal at both is a filter; so is CA equal at both, or
grain equal in shadow and highlight. One number pair per artifact is the whole test.

## 2. Optical signature of a real lens

| Aberration | Physical behaviour | Field-dep? | Aperture-dep? |
|---|---|---|---|
| Spherical | Marginal vs paraxial rays focus differently → glow/veiling wide open | No — global | Yes, strongly |
| Coma, astigmatism | Off-axis points smear into comets; radial and tangential foci separate into "double edges" | **Yes** — worsen outward | Yes |
| Field curvature | Curved focal surface on a flat sensor → uneven sharpness, often W-shaped | **Yes** | Yes |
| Lateral CA | Per-channel *magnification* difference → colour outlining growing linearly from centre, **zero at centre** | **Yes** | **No** — stopping down never fixes it |
| Longitudinal CA | Per-wavelength *focus* difference → purple fringing at focus, colour in bokeh | No — global | Yes |
| Natural vignetting | cos⁴ law — irradiance falls as cos⁴ of the field angle | **Yes** — smooth radial | Yes |
| Mechanical vignetting | Barrel/pupil occlusion clips the exit pupil off-axis | **Yes** — corners | Yes; can vanish stopped down |
| Veiling glare | Diffuse internal scatter lifts blacks, kills global contrast | Global veil | Barely improves stopped down |

`[SECONDARY · Phillip Reeve, "Lens aberrations explained" · checked 2026-08-28]`

**Bokeh is a physics readout, not a shape** `[PRIMARY · H. H. Nasse, Carl Zeiss, "Depth of Field and
Bokeh", 2010 · checked 2026-08-28]`. The blur disc **is an image of the mechanical iris**: a round
iris gives a round disc, nine blades a nonagon. **Cat's-eye is mechanical vignetting, not a look**:
at the edge "a circle in the middle of the picture becomes a two-sided figure composed of segments
of circles," the clipping axis **points at the optical centre** and eccentricity **grows
monotonically with field height** — the most diagnosable optical field in any frame. **Spherical
aberration sets the brightness profile inside the disc, asymmetrically front-to-back**:
under-correction gives larger, softer discs *behind* focus (creamy background, harsh foreground),
over-correction reverses it, so a real lens renders foreground and background blur *differently*.
Longitudinal CA tints the disc purple inside, green at the rim.

**Frame test.** Compare two out-of-focus speculars, one near centre and one near a corner: the
corner disc must be clipped on the side facing the optical centre and more eccentric. Round discs in
the corners is a synthetic frame. Then compare a foreground OOF highlight against a background one —
they should not match.

### 2.1 Where models fail on optics `[UNVERIFIED · analytical, derived from §2]`

| Failure | What it looks like | The physics being skipped |
|---|---|---|
| **Flat style, not field** | Vignette as a soft oval rather than cos⁴ plus mechanical corner clipping; CA uniform rather than zero-at-centre and radial | Artifact learned as texture, not as a function of field height. Highest-signal tell to a trained eye |
| Bokeh ignores frame position | Discs stay round into the corners; any cat's-eye is not consistently aimed at the optical centre; foreground and background blur look like the same operation | The pupil is not being imaged, only its average appearance; spherical aberration not modelled |
| **DOF is a segmentation, not a lens** | Blur constant across a receding surface; transitions on object boundaries rather than depth discontinuities; halos; blur that "sticks" to a moving subject | Blur applied per subject mask, not from a depth field. Often the real cause behind `realism-qa.md` V8 |
| Flare memorised as sprites | Static, source-locked overlays | Real veiling glare is a *global* contrast lift proportional to light on the front element, and ghosts translate **along the line through the source and the optical axis** as the camera moves |

**The transferable remedy method**, from VFX: treat every artifact as a *measured* field. Ground
truth is a **shot lens grid** — a checkerboard through the production lens, revealing distortion,
vignetting, spherical softness, field curvature and CA in one capture — and vignette extraction is
just blur the grid flat and grade centre to white, which hands you the lens's real radial falloff as
an image rather than a guess `[SECONDARY · Schröer]`. Lateral and longitudinal CA always separately.

## 3. Sensor and capture signature

**Shutter.** `[PRIMARY · ARRI, "ALEXA Studio Camera Electronic and Mirror Shutter" white paper ·
checked 2026-08-28]`: "a 180º shutter angle… results in an exposure time half of the frame rate… at
25 fps and a 180º shutter each exposure lasts 1/50th of a second." It matters physically because
**the ratio of blur length to inter-frame displacement is fixed at 0.5** — the streak is exactly
half the movement between frame centres, and that ratio is what the eye reads as normal motion
`[UNVERIFIED · restatement of the ARRI arithmetic]`.

**Rolling shutter.** ARRI gives the artifacts as "skew and partially exposed frames," worse the
faster the camera moves. Quantified `[SECONDARY · Tools for Film · checked 2026-08-28]`: Pixel
Offset = Pan Speed × Readout Time — 2,000 px/s × 15 ms ≈ 30 px ≈ 0.78 % of 4K width, visible on any
vertical line (A7S III 8.3 ms, A7 IV 23 ms, A6700 30 ms). ⛔ Distrust that table's ARRI row, which
claims a 0 ms global shutter and contradicts ARRI's own paper. Three classes: **skew**, **jello**
(oscillation from footsteps, handheld, motor), **partial flash banding**. **Handheld phone footage
at 10–30 ms readout carries continuous low-level jello, and its absence is a tell** `[UNVERIFIED]`.

### 3.1 Grain vs noise — the inversion that matters most

**Grain is the image** — "the image itself entirely consists of grain" rather than being "overlaid
on top of an image"; response is stock-dependent (negative grain "more pronounced in the
highlights"), grain "cannot be visible on pitch black or pure white," and correct grain **lowers
apparent contrast** by moving the black and white points, so expand after `[SECONDARY · Dehancer ·
checked 2026-08-28]`. **Digital sensor noise — what a phone actually produces — inverts that**
`[UNVERIFIED · standard sensor physics]`: read noise dominates the shadows, shot noise scales as
√signal so its *relative* magnitude falls up the exposure ramp, and chroma noise is
disproportionately blue-channel after white-balance gain. So **film grain peaks in the mids and
highs; digital noise peaks in the shadows** — "film grain" on footage that must read as a phone
applies the wrong exposure-response curve, and the eye reads it as a filter rather than as capture.
Real noise is also **spatially white per photosite and temporally independent per frame**, where
model noise is correlated at the latent's block scale and temporally sticky. (Real capture carries
PRNU too, a fixed sensor fingerprint `[SECONDARY · PRNU literature, surveyed not fetched]` —
invisible to viewers, but a reminder that *adding noise ≠ having been captured*.)

**The prompt-side version of this inversion, which is where it usually goes wrong.** The realism
literature treats *ISO* and *film grain* as one control — one photorealism guide lists *"ISO — film
speed; grain / sensitivity"* in the same breath as its film-stock terms `[SECONDARY · Turing,
*Prompt Realism Mastery* — via a local extraction, read 2026-08-28]`. They are **opposite curves**.
Naming a stock (*"pushed 400-speed negative"*) requests the mids-and-highs response; naming the
exposure condition (*"high ISO, low light, noisy shadows"*) requests the shadow-weighted digital
one. For anything that must read as a phone the second is the only correct request, and this
conflation is exactly how "film grain" ends up on footage that should be carrying sensor noise —
§7's grain row states the same rule from the post side.

**Frame test.** Measure noise amplitude in a shadow patch and a mid-tone patch of the same object,
then difference that patch across frames N and N+1. Real: amplitude differs by zone, difference
unstructured. Fake: flat across zones, and the difference near-black, because the grain is static.

### 3.2 Rolloff, clipping, banding, lifted underexposure

`[UNVERIFIED · analytical, standard imaging chain — no primary lab test in hand]`. Real rolloff is a
**soft shoulder from photosite saturation plus the display transform**, and **the three channels
clip at different scene values** because of white-balance gain: a real overexposed skin highlight
goes desaturated-warm before white, red last. AI highlights clip neutral and simultaneously, or are
tone-mapped so nothing clips at all. Real lifted underexposure shows chroma noise rising faster than
luma, black crush and shadow hue drift; a model asked for "underexposed" gives **dark but clean**,
which no camera can do. Banding is a **quantisation** artifact following the gradient's
iso-contours, where AI banding tends to be latent-block-aligned. **Frame test:** read R, G, B in the
brightest skin highlight — real capture shows a warm desaturated ramp just below clip; three
channels pinned together with no ramp is synthetic.

### 3.3 The mechanistic root: the video VAE

`[PRIMARY · Wu et al., "Improved Video VAE for Latent Video Diffusion Model," CVPR 2025 · checked
2026-08-28]`. Latent video diffusion compresses at **4×8×8** before the diffusion model sees
anything, and frames inside a latent group reconstruct unequally — "significant inter-frame flicker,
which is indicated by the fluctuating SSIM values across different frames," early frames showing
"blurring and a small amount of distortion"; ceilings before generation even starts are SSIM
0.92–0.97, PSNR 31–39 dB. **So the VAE is a low-pass filter with a *periodic* temporal quality
ripple at the group rate**, and pores, fabric weave, hair strands and grain all live above its
cutoff — which is why plastic skin survives resolution increases (upscaling restores nothing the VAE
discarded), and a plausible mechanism for the periodic shimmer in AI texture `[UNVERIFIED · the
skin/grain application is inference; the VAE data are primary]`.

## 4. Skin and faces

`[PRIMARY · Donner & Jensen, EGSR 2006 · checked 2026-08-28]`: **epidermis 0.25 mm** over a
semi-infinite dermis scattering half as much, melanin above and haemoglobin below — and the
load-bearing part, **specular is a separate physical layer** ("surface reflection is due mostly to
oil on the surface"), a Torrance–Sparrow BRDF energy-conserved against the subsurface term.
`[PRIMARY · Aliaga & Jarabo, Meta Reality Labs, arXiv 2606.27604 · checked 2026-08-28]`: melanin
fraction spans **0.001 → 0.65**, epidermal thickness **50–350 µm**, spectral scattering **3–4 orders
of magnitude** across wavelength — and their criticism of prior practice is exactly the criticism of
generative skin: RGB parameters are "artist-driven… preseted or authored manually," which
**decorrelates scattering from skin colour**. A model in RGB latents has that defect by
construction. Four separable defects follow — the cause under `realism-qa.md` V1, split because the
remedies differ `[UNVERIFIED]`:

| Defect | Physical fact being missed | How it shows |
|---|---|---|
| **Specular/diffuse coupling** | Specular is a thin oil layer with its own roughness, varying across the face — forehead and nose glossy, cheeks less, lips wet | One blended sheen; the highlight does not stay put when the head turns. **Biggest single contributor** |
| Missing scattering length scale | Subsurface scattering has a millimetre diffusion length | Hard shadow terminators, no reddening on the shadow side of the nose, no glow through ear rims or nostrils under backlight — the face reads as a painted shell |
| Missing micro-detail band | Pores ~50–150 µm, vellus hair finer — both above the VAE cutoff (§3.3) | A mid-frequency "skin-like" texture survives; hence plastic at any resolution |
| Missing haemodynamics | Blood-driven colour varies at low spatial frequency and drifts slowly in time | Flat, uniform, temporally static skin tone; no flushed cheeks, red ears, blanching at contact points |

⛔ **A consequence for prompt writing that the realism literature gets backwards.** The standard
advice is to *name* the micro-detail — *"skin texture, pore detail, hair strands"* is a headline
item in the photorealism vocabulary `[SECONDARY · Turing, *Prompt Realism Mastery* — via a local
extraction, read 2026-08-28]`. **On a still image that is sound**: nothing sits between the prompt
and the pixels. **On a clip it is spent budget** — the band is below the compressor's cutoff
(§3.3), so the words cannot deliver what they name, and the model answers with more of the
synthetic mid-frequency texture that *is* the plastic look. The same list's other half — *fabric
weave, linen, leather, glass refraction, water droplets, metal reflection* — is worth keeping,
because those are **centimetre-scale** structures that survive the VAE and are precisely what a
start frame should be asked to settle (§9).

**Frame test.** Rim-light a test frame and look at the ear: a real one glows orange-red where light
passes through cartilage. Then scrub a head turn and watch one nose or forehead highlight — it must
**slide across the curvature** as the head rotates. A highlight welded to the same patch of skin is
painted on, and no post pass fixes it.

### 4.1 What people actually detect — and therefore where to spend

Still faces sit at chance, and synthetic ones are rated *more* trustworthy `[PRIMARY · Nightingale &
Farid, PNAS 2022 — title/abstract only]`. Across all deepfake media humans are barely above chance —
**55.54 %** overall, audio 62.08 %, video 57.31 %, images 53.16 % `[PRIMARY · Diel et al., Computers
in Human Behavior Reports 16:100538, Dec 2024 · 56 papers, 86,155 participants · checked
2026-08-28]`. **Primed viewers of AI video do better, and the reason is physics, not skin**
`[PRIMARY · Shi et al., Scientific Reports, 2026-06-06 · checked 2026-08-28]`: 40 eye-tracked
participants over 80 five-second clips (half real, half Veo 3.1, matched) scored **66.4 %** —
**physics scenarios 70.8 %, stock-style 62.0 %** — split between **logic-based (25/40)** viewers
hunting physics violations and **intuition-based (15/40)** ones who said "looks artificial" and
*missed* the violations, because "gaze behavior is driven less by the video's actual authenticity
and more by the viewer's perception of its authenticity." Adding audio to the test improved
detection ~5 pp `[PRIMARY · Wang et al., arXiv 2512.13281v3 · checked 2026-08-28]`.

**Operational reading `[UNVERIFIED · synthesis]`:** a 6-second vertical ad watched once, unprimed,
at phone size sits in the Diel regime (~55–57 %), not the Shi regime — Shi's participants were
*told* to look. The enemy is the intuition viewer's fast "off" reaction and the comment section that
primes everyone after them. So spend on **motion and lighting plausibility** over **micro-texture**,
which nobody resolves at 1080×1920 on a six-inch screen — and **bad audio is a detection amplifier
worth ~5 pp**, which makes `editing-and-audio.md` and `realism-qa.md` A1–A7 realism work, not
polish.

## 5. Motion, contact and physics

Physics-IQ scores solid mechanics, fluids, optics, thermodynamics and magnetism against a real-video
upper bound of **100.0 %**. **The finding that should govern model selection:** a VLM's ability to
spot each model as fake, correlated against that model's Physics-IQ score, gives **r = −0.46, p =
.249 — no significant correlation, and the sign is negative** `[PRIMARY · Motamed et al., WACV 2026
· checked 2026-08-28]`. Visual realism and physical understanding are *decoupled*: **the prettiest
model is not the most physical one.** Through June 2026 the Verified leaderboard tops out at
**Magi-1 24B + GeoPhys 58.2 % ± 1.8** — **≈ 58 % against a 100 % ceiling, after 18 months** — and an
audit of the benchmark itself touched **57.6 % of samples**, dropping Wan 2.2 from 1st to 3rd, so
read published rankings with suspicion `[PRIMARY · physics-IQ repo; Rädsch et al., arXiv
2606.18943]`. VideoPhy-2 puts the best open model at **32.6 %** all / **21.9 %** hard, naming the
failure classes — conservation of mass and momentum, gravity direction, **permeability**, material
hardness, fluid dynamics, **contact physics** `[PRIMARY · Bansal et al. · checked 2026-08-28]`.
**That list is your shot-design blacklist**: far cheaper to design the physics out of a shot than to
generate it in — `realism-qa.md` V7 states the same rule as a counter-move.

**Why the motion reads floaty `[UNVERIFIED · mapped onto the VideoPhy-2 classes]`.** *No momentum
ledger*: diffusion produces a locally plausible trajectory carrying no conserved state, so
acceleration is not the derivative of anything — objects reach terminal velocity too early,
decelerate without cause, turn without an impulse; "floaty" is missing g in the second derivative.
*Contact is the weakest joint*: foot–ground weight transfer, hand–object mutual deformation, and the
**contact shadow**, which is what actually tells a viewer that two things touch. *Secondary motion
has no lag*: hair, cloth and flesh are damped driven systems that trail the primary motion by
frames, and AI renders them synchronously, so they read as painted on. *Breath is absent* — a held
pose in AI video is genuinely held. *Swim and drift* trace to §3.3.

**Frame test.** Step through any fall, drop or set-down four frames at a time and write the
displacement between steps: under gravity it must *increase* on the way down, and constant
displacement is floating. Then hold on the contact frame and look for a tight dark occlusion at the
contact line, and deformation in either body. Neither present means the objects are adjacent, not
touching.

## 6. Lighting physics

| Law | Physics | What a viewer feels when it is missing |
|---|---|---|
| **Inverse square** `[PRIMARY · radiometry]` | Irradiance ∝ 1/d². A subject 1 m from a source who steps to 2 m loses **two stops**; a close source falls off steeply across a *single face*, a distant or large one flatly | The light has no location in the room. Both cheeks equally bright under a close key is the readout |
| **Penumbra = apparent source size** `[PRIMARY · shadow geometry]` | Softness ≈ (source width × shadow distance) / (source distance); the *same* shadow softens as the occluder moves off the surface | Shadow edges uniformly soft everywhere, which no real source produces |
| **Coloured bounce** `[UNVERIFIED]` | Bounce carries the colour of what it bounced off — a red jumper under the chin, grass into faces | No room around the subject. Cheapest and most reliably absent cue in AI footage |
| **Contact shadow / AO** `[SECONDARY · The Rookies]` | A tight dark crevice term where two surfaces meet, distinct from the cast shadow | Objects float — this is the one that does it |
| **Shadow density** `[UNVERIFIED]` | Real shadows are filled by the ambient term and are rarely black | Shadows either black or implausibly open, with no consistent fill ratio. Together, these five laws are the physics under `realism-qa.md` V9 |

**The forensic geometry of speculars.** The catchlight encodes light direction by the law of
reflection (sclera r = 11.5 mm, cornea r = 7.8 mm, centres 4.7 mm apart), recovered to **2.8° ± 1.3°
on synthetic images, 8.6° on real photographs**; composites are exposed when highlights across two
people imply different light directions `[PRIMARY · Johnson & Farid, Dartmouth 2007 · checked
2026-08-28]`. The same geometric-consistency check is step one of professional deepfake forensics
`[SECONDARY · Iuliani, Amped Software, 2026-07-28]`. Applied here `[UNVERIFIED]`: it runs on *every*
specular in frame — both eyes, nose tip, a bottle, a phone screen, a countertop. In a real scene
they agree on where the lights are and move coherently; in generated footage they are locally
plausible, globally inconsistent, and painted on the surface rather than reflecting the environment.

**Frame test.** Mark the catchlight in both eyes and infer the key direction from each — they must
agree within roughly 10°. Do the same for one non-face specular. Three directions that disagree is a
scene the model assembled rather than lit, and it is prompt-resistant: fix by hand or retake.

---

## 7. The remedy table

**P** = prompt · **R** = reference or start frame · **T** = post · **X** = not fixable, retake. ⚠ =
**adding this badly is worse than omitting it.**

| Domain | Cue | P | R | T | Method and honest limit |
|---|---|---|---|---|---|
| **Optics** | Vignetting (cos⁴ + mechanical) | weak | yes | **yes** ⚠ | Post, as a **radial falloff derived from a real lens** (§2.1 grid method), never an oval mask. ⚠ An Instagram oval is a stronger fake-tell than no vignette at all |
| **Optics** | Lateral CA | no | weak | **yes** ⚠ | Per-channel **radial scale**, zero at optical centre, growing to the corners — not a global RGB offset, not a blur. Nuke: Bidwell gizmo; Resolve: Lens node / Film Look Creator. ⚠ Uniform CA is the classic amateur tell; keep it at the threshold of perception at 100 % |
| **Optics** | Bokeh shape / cat's-eye | no | partial | partial | R: a start frame with correct OOF discs biases the generation. T: only via a depth pass, which then lets you drive eccentricity by field position. Otherwise **X** |
| **Optics** | Focus breathing | no | no | no | **X.** If a rack matters, generate two clips at two focus states and cut, or rack in post from a depth pass |
| **Optics** | Flare / veiling glare | **yes** | yes | **yes** | P: name the source ("hard backlight clipping into the lens, veiling glare lifting the blacks"). T: glare is a *lift plus slight desaturation gated on frame brightness* — cheapest realism win in this table, and almost nobody does it. Ghost sprites: **X** unless comped by hand |
| **Optics** | Corner softness / resolution falloff | weak | yes | **yes** | Radial defocus keyed off field height. Very effective against the "equally sharp everywhere" signature |
| **Sensor** | Grain / noise | weak | weak | **yes** ⚠ | A real grain plate or a physically-modelled tool (Dehancer, FilmConvert, Resolve Film Grain), never a noise generator. Three rules: **dynamic** — a new pattern every frame, since static grain is instantly wrong; applied **at delivery resolution, after grade, before compression** — before an upscale it is mush, after compression it is bitrate suicide; and **matched to the reference's exposure-zone response** (§3.1), expanding after, because grain moves the black and white points. ⛔ For UGC "film grain" is the wrong artifact entirely — use shadow-weighted, blue-heavy chroma noise |
| **Sensor** | Motion blur | **yes** | no | partial ⚠ | P: name the shutter. T: optical-flow blur (ReelSmart; Resolve Optical Flow), which fails at occlusion boundaries, transparency and fast motion — and **you can only add blur, never remove it**. ⛔ Never add blur to output that is already temporally smeared. Diagnose first: crisp per-frame (add) vs soft everywhere (do not) |
| **Sensor** | Rolling shutter / jello | no | no | partial ⚠ | A time-offset-per-scanline warp. ⚠ Low salience and easy to overdo, so rarely worth it — **except on handheld UGC**, where it is one of the few artifacts the target genre genuinely has. ~5–15 px equivalent, maximum |
| **Sensor** | Highlight clipping character | weak | yes | **yes** | Per-channel soft-clip so the channels reach ceiling at *different* scene values (red last on skin), plus slight desaturation into the clip. Resolve: HDR wheels and a per-channel curve, or a print-emulation LUT, which does it by construction. **High value, invisible when right, almost nobody does it** |
| **Sensor** | Halation | weak | no | **yes** ⚠ | Physics `[PRIMARY · Dehancer]`: light passes the emulsion, reflects off the base, returns stripped of blue and green, re-exposes the **red** layer; the brightest bleed into green → orange. So threshold-gate on high luminance, blur, weight to red, screen. ⚠ Ungated halation is gauze. ⛔ Halation implies *film* — never combine it with digital-sensor noise unless the conceit is "shot on film, scanned" |
| **Sensor** | Banding | — | — | — | Do not add. **Remove** it — dither or grain covers it |
| **Sensor** | Lifted underexposure | **yes** | **yes** | partial | P/R get you dark; T must add the *consequences* — chroma noise rising faster than luma, shadow hue drift, reduced shadow separation |
| **Sensor** | Gate weave | no | no | yes ⚠ | Sub-pixel translate plus a tiny rotate on a slow random walk. ⚠ Only under a full film conceit; on UGC it is a category error, because phones do not weave |
| **Skin** | Specular/diffuse separation | weak | **yes** | weak | **R is the lever.** A start frame with *placed* speculars (T-zone glossy, cheeks matte, lips wet) constrains the whole generation. In post you can only reduce the blended sheen, never re-separate it |
| **Skin** | Subsurface scattering | weak | **yes** | no | **R.** Backlit or rim-lit start frames push the model toward translucency. Post cannot add scattering that was never rendered |
| **Skin** | Pore / micro-detail | weak | partial | partial ⚠ | Lost at the VAE (§3.3) and not recoverable. T: a detail-scale texture pass or light frequency-separation grain aligned to the face can *imply* pores. ⛔ Sharpening is the wrong tool — it amplifies the model's synthetic mid-frequency structure and makes the plastic worse. At phone delivery this cue is below visual acuity; **deprioritise it** |
| **Skin** | Blood-flow colour variation | **yes** | **yes** | **yes** | Cheapest genuine skin win. P: "flushed cheeks, reddened ears and nose tip." T: a soft low-frequency warm map on cheeks, ears, nose and knuckles, with a very slow temporal drift |
| **Skin** | Eye catchlight geometry | **yes** | **yes** | **yes** | P: state the key's shape and position. T: paint or reposition catchlights so both eyes agree on direction (§6) and slide correctly on a head turn. On a close-up, worth doing by hand |
| **Skin** | Micro-expression / gaze | weak | weak | no | **X.** Retake on a different seed or model — `realism-qa.md` V4 is a regeneration trigger, not a grade note |
| **Light/motion** | Contact shadow / AO | weak | **yes** | **yes** | T: roto plus a small dark multiply at the contact points, tightest and darkest at the contact line. Tedious, ~10 min a shot, and **the single highest-yield fix for "floating"** |
| **Light/motion** | Inverse-square falloff across subject | **yes** | **yes** | partial | P: "single practical 60 cm from her face, hard falloff, far side two stops down." T: a gradient can imply it but cannot re-light |
| **Light/motion** | Shadow edge quality | **yes** | **yes** | no | P/R only. Name the source size: "small hard source" vs "4×4 diffusion at 1 m" |
| **Light/motion** | Coloured bounce | **yes** | **yes** | **yes** | T: qualified secondary — take the bounce surface's hue into the adjacent shadow side. Fast and convincing |
| **Light/motion** | Specular-set consistency | weak | **yes** | partial | T: kill or reposition the offending highlight; you cannot re-derive the set |
| **Light/motion** | Weight, inertia, contact physics, secondary-motion lag | partial | partial | no | **X.** The levers are model choice, shot design (§9) and many seeds. Do not try to fix in post; hair and cloth lag cannot be added at all |
| **Light/motion** | Breath | **yes** | no | no | P: "she exhales; her shoulders drop." Reliable enough to include on every held shot |
| **Light/motion** | Temporal swim / identity drift | weak | partial | partial | R reduces drift. **The real remedy is editorial — cut before it becomes visible.** Under ~3 s a shot most of it is invisible, which is the physics reason behind `realism-qa.md` V8's short-clip rule |

**Order of operations** `[SECONDARY · The Rookies plate-integration checklist]`, sitting underneath
`realism-qa.md` §4's finishing pass rather than replacing it: exposure → per-channel colour →
saturation → gamma → black level → **contact shadows and bounce (paint)** → depth-based defocus →
optical falloff → CA → halation → highlight soft-clip → **grain/noise at delivery resolution** →
recompression. Their warnings generalise exactly — *don't overdo* the lens artifacts, and *overly
clean renders telegraph artificiality*: this file exists as much to stop over-application as
under-application.

## 8. The reference target is a phone, not an ARRI

`[UNVERIFIED · analysis, built on the sourced observation that models default to clean cinema]`
Second load-bearing claim, and it inverts much of §7 for UGC. Every model is trained toward, and
marketed on, *cinematic* output; your target is **a phone in a kitchen**. So much standard
"cinematic realism" advice actively hurts, moving the frame away from the reference the viewer is
matching against.

| Cinema realism cue | UGC realism cue |
|---|---|
| Shallow DOF, creamy bokeh | **Deep focus** — a small phone sensor has enormous DOF; AI's default shallow-DOF-everything is itself a tell |
| 180° shutter motion blur | Often 1/60 or auto — crisper motion, plus **mains flicker banding** under LED and fluorescent |
| Film grain in the mids | **Shadow-weighted chroma noise**, plus visible temporal noise-reduction smear on movement |
| Graded, protected highlights | **Blown windows**, aggressive local tone-mapping, HDR halos around the subject |
| Locked or dolly moves | **Handheld micro-jitter, autofocus hunting, auto-exposure pumping** as someone crosses the window, AWB shifting on a cut |
| Clean codec | **Two generations of H.264/HEVC recompression**, blocking in motion, chroma subsampling artifacts |
| One consistent lens | **Lens-switch jump** as the phone crosses focal length; digital-zoom softness |
| Even, motivated lighting | **One overhead LED and a window**, mixed colour temperature, ugly and uncorrected |

⛔ **Artifacts to deliberately NOT add for UGC:** film grain in the mids, halation, gate weave,
anamorphic flare, creamy shallow bokeh, protected highlight rolloff, smooth stabilised camera moves.
Every one of them says *someone made this*, which is the opposite of the claim the video is making.

### 8.1 ⛔ The lighting withhold list — the same rule, applied to §1 of `cinematography-craft.md`

The artifact list above covers the *capture chain*. The same logic has a lighting half, and it has
been implicit and therefore unenforced: **the whole feature-film lighting tradition is a catalogue
of ways to announce that someone made a decision about a face**, which is the exact claim a peer
testimonial is trying not to make. Listed as vocabulary, because the failure is a phrase getting
typed, not a concept being misunderstood.

| ⛔ Withheld from UGC | Why it fails the phone test | Buy the same thing this way instead |
|---|---|---|
| **Three-point lighting**; the words *backlight*, *rim light*, *hair light*, *kicker*, *eyelight* | **No phone video has a hair light.** Each needs an unmotivated instrument behind or beside the subject; there is no such thing in a real kitchen | separation from a **tonal step at the outline** and camera distance (F14), never from a third source |
| **Butterfly / Paramount** | literally glamour lighting, invented to make stars look like stars. It is §4's attractiveness halo applied optically, and that halo *"flips the viewer's read from 'person like me' to 'model in an ad'"* (`production-design.md` §4) | **loop**, which is what a real window does |
| **Golden hour** | beautiful, reliably promptable, and it says *someone chose when to shoot this*. Golden hour + backlit + shallow focus is the three-token advertising signature | **overcast** — one token, whole light model, matchable across a batch |
| **Reverse key** (low sun behind, bounce filling the front) | the best-looking outdoor setup there is, and 60% of the way to an ad for the same reason | keep it for narrative-promo mode; withhold from UGC |
| **Low-key / chiaroscuro / noir** | a register the format cannot carry: at 45 s on a phone at half brightness in daylight, deep shadow is an unreadable frame — and the phone reference aggressively *lifts* shadows | contrast from a **dark wall on the unlit side**, not from crushing the image |
| **High-key** — the subtler trap | it is sold as commercial, cheerful and *efficient across setups*, which is the ad look arrived at for the reason ads arrive at it. A phone in a real room is **neither** high nor low key: blown window on one side, dark on the other | the row above: "one overhead LED and a window, mixed colour temperature, ugly and uncorrected" |
| **Softbox / silk / diffusion** as vocabulary | a softbox *"reads studio, not world"* (`cinematography-craft.md` §1.9) | say **"overcast"** or **"north window"** |
| **The fill instinct itself** | the whole lighting literature reflexively opens the shadow — bounce boards, reflectors, "invest in a good reflector". UGC's shadows are open by accident and crushed by tone-mapping, never by a bounce board | read every fill decision as a **negative-fill** decision (§1.5) |

⛔ **"Overlight it and darken in post" is not merely non-transferable here — it is inverted twice
over.** A generated clip is baked-in footage with no latitude to spend (§7 item 1), so you cannot
buy headroom at generation time; and a slightly dark, slightly noisy clip is *more* credible than a
cleanly exposed one, per the phone column above.

**What does survive into UGC, from the whole tradition: four things.** Motivated practicals in
frame · mixed colour temperature · short-side keying · negative fill. Plus three *diagnostics* that
transfer completely because they are not styles — the nose-shadow read (F22), the catchlight-shape
read (F23), and the scenario cell (`craft-cheatsheet.md` §3). Everything else in the tradition is
the list above. [SECONDARY · StudioBinder, *Film Lighting: The Ultimate Guide*, 2023, for the
techniques being withheld; the withholding is this file's judgement, UNVERIFIED]

**And one level up from the artifact: a format token is a bundle, not a look** `[UNVERIFIED ·
synthesis, extending §7's halation rule]`. The still-image literature teaches capture format as a
single interchangeable slot — *35mm / 16mm / VHS / anamorphic / IMAX / Polaroid*, one term dropped
into a prompt `[SECONDARY · Ward, *Creating Cinematic Images: Midjourney Style Guide* — via a local
extraction, read 2026-08-28]`. Each of those names is physically a **co-occurring set**: 16mm is
coarse grain *and* softer resolution *and* a narrower gate; VHS is chroma bleed *and*
head-switching noise *and* roughly 240 lines *and* temporal smear; anamorphic is oval bokeh *and*
horizontal flare *and* a differential squeeze in the out-of-focus field. A model that learned the
token as a style returns **some** members of the bundle and not the rest — and a mismatched bundle
is a stronger tell than a plain frame, because it is §1's "artifact present, not varying correctly"
failure repeated at the level of the *capture chain* rather than the field. §7 already enforces
this for one pair (halation implies film, so never alongside digital sensor noise); the general
rule is that **naming a format commits you to every artifact that format implies**, and if you
cannot deliver the bundle, do not invoke it. For UGC you almost never should — the correct bundle
is the phone column above. ⚠️ Anamorphic stays the gap named in §10: its bundle is listed here from
convention, not from a primary optical source.

So the UGC post chain ends in a **deliberate degradation pass** — slight recompression, phone-style
sharpening halo, shadow chroma noise, a touch of AE/AWB drift, a hint of rolling-shutter skew on
handheld — rather than a film-emulation pass. And prompt *away* from the cinematic prior explicitly:
"shot on an iPhone front camera, harsh overhead kitchen LED, mixed colour temperature, deep focus,
no cinematic bokeh, slightly overexposed window behind her." This is the physics behind
`realism-qa.md` V15 and its §4 preference for a phone look over a cinema stock; the resolution half
lives in `delivery-format.md`, and the cinema vocabulary to *withhold* is in
`cinematography-craft.md`.

**Frame test.** Put a real phone clip shot in the target room beside the generated frame at 100 %
and compare four things in order: depth of field on the background, noise in the shadows, what the
window is doing, and the colour-temperature difference between the two sides of the face. Whichever
is furthest off is the pass worth doing — and it is almost never the pores.

---

## 9. Model-specific behaviour — checked 2026-08-28, expect this block to decay

⛔ **Re-verify this entire section before any batch more than a quarter old.** Everything above is
physics and holds; this is a snapshot of a market that moves monthly, and it belongs to
`ai-generation.md`'s roster discipline. Only what bears on *physical* realism is here.

**Aesthetic preference and physical plausibility rank differently, and the leaders are different
models.** Blind pairwise Elo `[PRIMARY · Artificial Analysis video arenas · fetched 2026-08-28]`:
T2V led by Wan 3.0 1240, Gemini Omni Flash 1237, MiniMax H3 Max 1235, Seedance 2.0 1221, with Veo
3.1 at 1090 — 130–150 Elo behind despite leading on controllability and audio; I2V led by MiniMax H3
Max 1202. Physics-IQ Verified leaders `[PRIMARY]` are instead Magi-1 24B + GeoPhys 58.2 %, Magi-1
24B 48.4 %, Cosmos3-Super-Image2Video 39.5 % — exactly what the WACV r = −0.46 result predicts.
**Runway and Luma appear on neither 2026 leaderboard; treat their standing as unknown.** Veo 3.1's
*entire published optical vocabulary* is five terms — shallow depth of field, wide-angle lens, soft
focus, macro lens, deep focus `[PRIMARY · Google Cloud, "Ultimate prompting guide for Veo 3.1"]` —
so **anything in §2 finer than that cannot be prompted on that model**; it comes from a start frame
or from post. Veo's physics claim, and Seedance 2.0's "collisions have weight, fabric tears
realistically" `[PRIMARY · fal.ai]`, are **human-preference** claims while Physics-IQ and VideoPhy-2
measure whether the video matches what happens, ceilings near 58 % and 33 %. **Read "realistic
physics" in a 2026 launch post as a claim about perceived plausibility over 4–8 seconds — which is
what an ad needs — not about simulation** `[UNVERIFIED · assessment]`.

Strategy `[UNVERIFIED · recommendation]`: physically loaded shots — pouring, dropping, contact,
cloth, fluid — go to a physics-ranked family or, more cheaply, get **designed so no physics is
tested**. Talking-head UGC goes to the preference leaders plus a start frame; controllability and
audio sync go to Veo 3.1, accepting the preference gap. And **always drive from a start frame you
control**: it settles optics, specular placement, skin, colour and framing *before* the video model
guesses at them — the same reason `realism-qa.md`'s frame gate carries ~10× the leverage of the clip
gate.

## 10. What this file cannot settle

Stated at the same prominence as the findings (`research-quality.md` §6). Each is an afternoon of
internal testing, not a reason to stop.

1. ⛔ **The central thesis is UNVERIFIED.** That CA, vignette and bokeh appear in current models as
   flat style rather than radial fields is analytically motivated and consistent with the sourced
   "too clean / equally sharp" observation, but **no published measurement was found.** It is
   cheaply testable: generate a frame of point highlights across the field and measure disc
   eccentricity and per-channel radial offset against field height. **Run it before trusting the
   claim**, and log the result per `self-evolution.md`.
2. **Whether AI video contains rolling-shutter behaviour at all.** No source either way.
3. **Whether adding post artifacts measurably changes viewer authenticity judgements.** No study
   found tests post-processed AI video against unprocessed for detection rate, and the Shi finding
   that gaze follows *perceived* authenticity implies grain, CA and halation may buy less than
   practitioners assume. **The biggest open question here, and the one most worth an internal A/B.**
   ⚠️ **A cross-domain result worth knowing and not worth over-reading.** In AI *text* the same
   question has an answer, and it is unfavourable: post-hoc filtering of a fixed output
   distribution plateaus near 55 %, and only interventions that change the **input** distribution —
   conditioning, decoding, fine-tuning — move it `[SECONDARY · internal note, "Advanced Anti-AI
   Fixes", 2026-07-09 — via a local extraction, read 2026-08-28]`. ⛔ **That is prose, scored by
   text detectors, and it is evidence about nothing in this file** — no result transfers from token
   statistics to a light field. It is recorded only because it is the same *shape* of question and
   it predicts a null. If it does generalise, §7's post chain is the low-ceiling lever and §9's
   "drive from a start frame you control" is the high-ceiling one, which is already this file's
   ranking. The note's own closing caution generalises more cleanly and is the safer takeaway:
   chasing a detector is an arms race, and the artifacts in §7 are worth adding because they make
   the frame *better*, not because something is being fooled.

**Also unverified, in one line each:** §3.2 entire — rolloff, banding and lifted-underexposure
behaviour are analytical, and the ARRI lab numbers (rolling shutter in ms, dynamic range at a stated
SNR, liftable latitude) could not be fetched. The mids-vs-shadows grain/noise split — Dehancer
supports the film half, the digital half is standard shot-noise reasoning. Optical-flow motion-blur
failure cases are standard knowledge, not vendor-documented. Nightingale & Farid is title/abstract
only. Kling 3.0 and MiniMax H3 behavioural specifics, and Runway's and Luma's 2026 positions, are
Elo-only or nothing. Anamorphic behaviour — oval bokeh, horizontal flare, differential squeeze in
the OOF field — is untreated: the ZEISS monograph is spherical-focused and no anamorphic primary was
found.

**Cross-refs:** `realism-qa.md` (the tell list, counter-moves, QA card and batch rule — this file is
its physics layer, not a substitute) · `ai-generation.md` (prompt-side guardrails, the model roster,
the identity lock and the start-frame method) · `cinematography-craft.md` (§7's translation table
tells you which cinema vocabulary reaches the model at all — and therefore what there is to withhold) · `editing-and-audio.md` (the finishing chain and the mix, where §7's
order lands) · `delivery-format.md` (resolution and codec, which decide where grain goes) ·
`research-quality.md` (tiers, dates, the refutation pass) · `self-evolution.md` (how a measured
answer to §10 becomes a permanent rule).
