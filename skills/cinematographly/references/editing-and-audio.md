# Editing & Audio — beats, lipsync, loudness, captions (DaVinci Resolve)

The assembly stage in **DaVinci Resolve**. Goal: a cut that rides the music's beats, mouths that
match the voices, clean loud-enough audio, and burned-in captions (in the target language) for
sound-off viewing. This is where the pacing curve from `craft-cheatsheet.md` becomes real. *(Resolve
is the house editor; the beat-marker, lipsync, loudness, and caption principles port to any NLE —
only the command names differ.)*

**This file is the mechanics. `editing-storytelling.md` is the meaning** — why a cut works (Murch's
Rule of Six and the error-masking asymmetry it actually describes), montage and the honest Kuleshov
record, the continuity rules with the reason each exists and when breaking it is right, rhythm,
building a performance that was in no single take, and a sceptical account of what any of it does
for a 40-second vertical ad. The retention-folklore quarantine below is unchanged; that file adds a
reusable test for telling evidence from folklore rather than a longer list.

## Colour management — treat every generation model as a different camera

AI clips arrive with **no colour metadata and no shared characterisation**: assume display-referred
Rec.709/sRGB unless proven otherwise, and expect each model (dialogue model, B-roll models, the
cinematic tier) to have its **own** colour response — different default saturation, contrast and
skin rendering, exactly like footage from mismatched cameras. "Grade to taste per clip" at volume
produces the fox's fur shifting between shots and nobody knowing why. The spec:

1. **Set project colour management explicitly** — don't leave Resolve on defaults. A simple, robust
   setup for this pipeline: Rec.709 (Scene) timeline and output, inputs tagged Rec.709/sRGB. (An
   ACES/DWG working space is legitimate for a heavier finish, but only if set deliberately.)

   **The `dwg-working` switch (v2.49; HR-33, approved by the owner).** For **real log footage only**, a
   job may grade in DaVinci Wide Gamut instead, as a pair of transforms:
   - each camera's **input transform first**, on its own colour group's pre-clip graph: the camera's log and
     gamut into DaVinci Wide Gamut / DaVinci Intermediate, with no tone or gamut mapping;
   - then the match, the look and the texture, in the wide space;
   - an **output transform last**, on the timeline's last node: Rec.709 Gamma 2.4, with tone mapping on.

   Generated clips stay on the Rec.709 route above, in every job. A look LUT built on display-referred
   pixels goes **after** the output transform, or the look is built by hand. A hybrid cut that mixes
   generated clips into the wide space is untested. The export gate (`look_qa.py export`) and the grade
   rulings C1–C4 still hold. There is no template: one is written when a real log job needs it. Turn it
   on in the checkpoint's `Switches:` line with the reason (`assets/project-switches.json`).
2. **Normalise per model, then match per scene, then grade once.** Node order per clip: (a) the
   model's normalisation correction — the same first node for every clip from that model, doing the
   same job an input transform would; (b) shot-match within the scene (the white balance set from
   the prompt's Kelvin, skin value matched across intercut shots); (c) the one creative grade for
   the whole piece, applied at group/timeline level.
3. **Build each model's normalisation once, not per project.** Generate a fixed reference frame
   through each model in the stack (the same prompt: a neutral grey card + skin tones in daylight),
   correct it to neutral, save that correction as the model's standing node/LUT, and note it in the
   client profile beside the model IDs. Re-check it when the model version changes (the shot
   manifest tells you when that happened).
4. **Full-vs-legal range is the silent killer** — a washed-out or crushed export with a correct-looking
   viewer is a range mismatch at delivery, not a grade problem. Keep tags consistent end-to-end and
   eyeball the exported file, not just the timeline. Since 2.36.0 the file is also measured
   (`look_qa.py export`, below), and `approve export` refuses without it.

### The grade, built and checked — `grade_luts.py`, `look_qa.py`, the console's grade plan

Author, 2026-10-26: *"Any other FX, color grading, vignette etc? LUTS? Do we have anything for those?"*, then
*"A: Export look check, B: Per-model correction LUTs, C: Shot consistency, D: Looks per lane"* and the
four rule changes, *"Apply all four"* (the grade and finish proposal of 2026-10-26 [studio history]; the rulings
C1–C4 are in `realism-qa.md` §4).

**The order:**

1. **Once per model: its correction LUT.** Shoot or license a REAL still: a grey card or chart, and skin,
   in daylight. Never an AI image as the reference. Animate it through the model with a locked-off,
   no-motion prompt, two or three times. `grade_luts.py fit --model M --still S.png --clip a.mp4 --clip
   b.mp4 --clip c.mp4 --out DIR` measures what the model did to the colour and inverts it. It fits gentle
   monotonic curves and a 3×3 matrix kept near identity, then tests them on the last clip, which it
   held out. It is `ok` only if the curves stay monotonic and the held-out ΔE falls.
2. **Install it.** Send the `.body.py` text to the Resolve MCP's LUT tool as `cine_<model>_norm_v<N>.cube`,
   size 33. The tool writes only directly inside `LUT/MCP` (measured 2026-10-26), so every name carries the
   `cine_` prefix and Resolve lists it as `MCP/cine_…`. The file in Resolve is then the transform that was
   checked. After a still is grabbed with the LUT on, `grade_luts.py lutcheck` compares it with the LUT
   applied here (mean ΔE ≤ 1.5, [assumed]).
3. **The looks, per lane (D).** `grade_luts.py look --kind phone|brand|clean --strength 60` bakes the
   strength into the file, so "60 %" is a file and not a slider someone forgets.
   - **phone** has open shadows (C1): a lifted, unclipped toe, a soft highlight shoulder, and saturation
     that eases off on skin and near white.
   - **brand** reads a spec of hue shifts, a split tone and saturation. It changes hue only and leaves
     skin alone.
   - **clean** is the identity.

   For drama, `vignette --stops 0.3` writes a cos⁴ falloff DCTL, aspect-correct, applied in linear light;
   install it through the DCTL tool, which compiles it first. Ads get no vignette: their corners hold the
   captions. That holds unless the job's CHECKPOINT carries the `finish-texture` switch
   (`assets/project-switches.json`): a small bloom, optional grain and a light vignette in the ads lane's grade
   plan, with skin protection, the look's strength and `look_qa.py export` unchanged (v2.48.0, switch
   `finish-texture`) — when and where: § Finishing looks.

   **Choosing between looks** [PRACTITIONER · course notes]: compare two or three on the footage with the rest
   switched off, on more than one shot, and reject any that over-colours skin. The winner and its mix go
   in the grade plan. The skill buys no look packs: a purchase is a spend and needs the owner's approval.
4. **After picture lock: every take.** `look_qa.py shots <job>` measures each take in the cut:
   - clipping at ingest (G8: what the model clipped, no grade brings back);
   - colour drift from the take's start to its end;
   - flicker, which switches the Deflicker node on;
   - skin against the same cast person's other shots;
   - a shot-match CDL against the approved start frame, capped (slope 0.85–1.15, offset ±0.03,
     saturation 0.9–1.1) and kept only if it gains at least 1 ΔE.
5. **The plan, applied by the console script.** `grade_luts.py plan <job> --lane ads --look phone_60
   --template-drx <clip template> [--timeline-drx <timeline template> --vignette --film-look] --console`
   writes `07-edit/grade-plan.json` and `07-edit/resolve-production-console.grade.py`. The second file is
   a grade-only copy of the one production console script, not a third script. Send it whole as the
   `run_script` script with the cut's timeline open. It then:
   - makes a colour group per model, with the model's LUT on the group's pre-clip graph, read back;
   - assigns every clip to its group and reads that back too;
   - applies the template to a clip with no grade yet;
   - switches the nodes by shot type, sets the look LUT and the CDL;
   - for drama, sets the timeline's vignette and Film Look Creator nodes.

   It names every clip on the timeline that is not in the plan, and every planned clip it did not find.

   **Measure before calling the grade done** (production lessons, 2026-11-05): the LUT's shift on a still
   (`grade_luts.py lutcheck`), and the grain plate's average level after any conversion — on one job the first
   grain plate came out wrong because the conversion squashed its range. Look at the measured number, not the
   viewer.
6. **Export** with Data Levels **Video** and the Rec.709 colour space tag with the **Rec.709-A** gamma tag.
   A Gamma 2.4 tag reads as 1-1-1 on YouTube and Vimeo [SECONDARY · wolfcrow]. Then run `look_qa.py
   export <job> --export 10-export/<file>.mp4 --lane ads|drama` (below). `approve export` refuses without
   a passing report on those bytes.

   Then a human pass on the rendered file, after the measured one: watch it again after a break (the
   course says a couple of hours away from the grade [PRACTITIONER · course notes]) and on a phone. If it reads too
   warm or too colourful, correct on a node before the look instead of pulling the look down. `look_qa.py`
   measures range and legibility, not warmth, so this pass is a review, not a gate.

**Real footage has its own order** [PRACTITIONER · course notes]. The order above is for generated clips. Log
footage from a real shoot is graded on the clip graph in this order (a plate that will carry a generated
element also follows `real-and-ai.md` §1.1; a job on the `dwg-working` switch does step 2 as the input
transform of Colour management item 1 instead):

1. **Match** exposure and white balance across the shots, on a node before the conversion.
2. **Convert** from log on its own node: the camera maker's conversion LUT, or a Color Space Transform.
3. **One creative look** on its own node, at partial strength (the node's Key Output Gain). The course
   works at 40–70, used 70 on its job and allows 80; its panels read 70.8 and 67.4 [PRACTITIONER · course notes ·
   read off the course frames]. `grade_luts.py look --strength 60` already sits inside that range. The
   range is not a new default.
4. **At most one softening control** (the course's is a bloom), in the drama lane only: the `texture`
   node below. ⛔ Ads skip this step. They still get no bloom, grain, halation or vignette (C2, and step 3
   of the order for generated clips).

**A local face lift is a manual pass** [PRACTITIONER · course notes]. After the look, a second, local pass can lift
a face: a static window round it (a Power Window on its own node), inverted, with a little more contrast,
faded out with a keyframe where the person leaves frame. No slider values were read off the course
frames, and none are given here. ⛔ The window never moves: no tracker, and no keyframes on its position
or shape. A window that follows a face is rotoscoping, which the house does not do. If the face moves
too far for a static window, skip the pass. The scripted plan has no window step and the API cannot add
nodes, so this pass is the colourist's.

**Finishing looks — when, where and how much (v2.48.0).** Author, 2026-11-03: *"The skill should know when and
where to apply them. Look it up."* Six finishing devices are banned in the ads lane by default, and a job lifts
each one with a project switch in its CHECKPOINT (`assets/project-switches.json`; `scripts/switches.py list` prints
each one's `when` and `where`). These blocks say when a brief calls for one, where it goes and how much. Sources:
the finishing-looks research (the author's research notes, 2026-11-03) and the course notes. [INFERENCE]
marks the research's own reasoning from its sources, not a claim any source makes. No number here is a default. A
range stays a range, and where only weak sources give a number, the block says there is no reliable one.

| Device | Switch | Lives in Resolve as | Block |
|---|---|---|---|
| Bloom, glow, halation | `finish-texture` | the clip's `texture` node: Film Look Creator's Bloom or Halation, or the Glow or Halation FX | below |
| Film grain | `finish-texture` | the same `texture` node, one grain source | below |
| Vignette | `finish-texture` | a static Power Window on a clip node (motivated), or the timeline `vignette` DCTL (lens) | below |
| Light leak | `light-leak` | an Edit-page transition or an overlay track, never a grade node | below |
| Blur-in title | `blur-titles` | a native Fusion title (Text+) | `typography-and-captions.md` §6c, after item 3 |
| Blurred fill | `blurred-fill` | Resolve FX Stylize › Blanking Fill on the clip | `typography-and-captions.md` §6c, after item 10 |

*Bloom, glow and halation* (`finish-texture`)
- **When.** A look that already reads as film: lifestyle, beauty, nostalgic, period and music-video registers. A
  commercial colourist adds bloom and halation when he wants film character, and finds film looks suit music video
  better than a TVC [PRACTITIONER · Marc McCarthy, Reel Factory, LBB 2026]. The course's commercial keeps one small
  bloom to soften skin on the tight shots, with the film plugin's grain, halation and own LUT switched off
  [PRACTITIONER · course notes]. A glow can also draw the eye to talent or a lit product [PRACTITIONER · Jason
  Bowdach, Mixing Light 2025]. Halation carries a register of its own (memory, dream, menace) [SECONDARY · CineD
  2026], so in an ad it needs an explicitly filmic brief; a small bloom needs less.
- **Not when.** Clean tech, SaaS, fintech, explainer and high-key commercial looks [PRACTITIONER · Robbie Carman, DC
  Color EP005, on clean high-tech looks; INFERENCE for the rest]. Product-clarity shots, packshots, UI recordings
  and text-heavy frames, because glow softens edges and lifts the area round white type [INFERENCE]. As a trend reflex
  [PRACTITIONER · Joey D'Anna, DC Color EP005]. To rescue clipped highlights: a generated clip clipped at ingest (G8)
  gets a weaker, colourless glow, not its light back [PRACTITIONER · Uli Plank, Digital Production 2024]. Halation
  on a clean digital image with no grain to diffuse into [PRACTITIONER · D'Anna]. Film Look Creator's Halation or
  Film Gate on a picture smaller than the frame, such as a fitted band in a 9:16 timeline [PRIMARY · Resolve 21
  manual, ch. 157 · docs.imaster.org/davinci-resolve-21-manual/part-12-resolve-fx-overview/ch.-157-resolve-fx-film-emulation].
- **Where.** In: shots with a motivated bright source against a darker field, such as practicals, windows, signs and
  specular water [PRIMARY · ch. 157]; for the bloom, skin on the tight shots [PRACTITIONER · course notes]. On real
  footage this is step 4 of the order above, which the switch opens to ads. Never: the product, anatomy and clean
  shots, which `grade_luts.py` keeps clean even with the switch on. A clip prompt with no `grade:` counts as b-roll
  and gets the texture, so a UI recording or any shot that must stay crisp carries `grade: clean` or `product`.
  Never white packaging, white UI or white wardrobe unless the brief is filmic, because they halate red-orange
  [INFERENCE]; never captions and supers, which sit outside the clip graph. Watch a face as it passes the light, at
  delivery resolution: a halo that is fine on a still can wash over the subject a moment later [SECONDARY ·
  DaVinci Resolve Club]. Order on the `texture` node:
  bloom or diffusion, then halation with Reduce Highlights on, then grain [INFERENCE from the manual's Halation →
  Film Grain order and Cullen Kelly's colour-first, texture-later build, Frame.io 2024]. One owner per effect: Film
  Look Creator's modules or the dedicated Glow and Halation FX, never both [PRIMARY · ch. 157, which calls Film Look
  Creator a simplified tool set].
- **How much.** There are no portable slider numbers: the same Shine Threshold reads very differently on a dark
  street and on snow [SECONDARY · DaVinci Resolve Club]. Push past the target, then pull back with Opacity or Global
  Blend [PRACTITIONER · Bowdach]. Keep halation very subtle [PRACTITIONER · Plank]. Kelly runs it at about half of his
  own calibrated stack and almost never at full strength, a share of his build and not a slider value [PRACTITIONER ·
  Cullen Kelly, Grade School 2022]. A simulated 1/2 Black Pro-Mist is already not subtle [PRACTITIONER · Plank 2025].
  The course's bloom is a plugin profile, spoken as 65 mm while its menu read 35 mm [PRACTITIONER · course notes · read off
  the course frames], so no number carries over. Under the switch: one bloom, and halation only on a
  filmic brief.
- **Delivery.** Soft glows band after compression, and grain laid over them dithers the banding [PRACTITIONER · Rich
  Young, ProVideo Coalition; D'Anna]. Measured median top-stream bitrates of about 2.1 Mbit/s on Reels, 1.1 on
  TikTok and 5.7 on Shorts [SECONDARY · shortformkit.com short-form quality study, Oct 2026] make a wide glow the
  first gradient to band, so keep halos tight. 4:2:0 delivery halves chroma both ways, so a thin red halation fringe
  smears or vanishes on platform [INFERENCE from PRIMARY · YouTube upload spec, support.google.com/youtube/answer/1722171].
  `look_qa.py export`'s banding check stands; a dark scene is the one to look at.
- **Tells it is cheap.** The red outline is seen before the light; an RGB spread reads as chromatic aberration
  [SECONDARY · videomontazher; PRACTITIONER · Carman]; a milky whole-frame wash from a threshold set too low; a glow
  switches on and off as a light crosses frame [SECONDARY · DaVinci Resolve Club]; a heavy look covers a weak image
  [PRACTITIONER · Carman].

*Film grain* (`finish-texture`)
- **When.** Only on a look that already reads as film: grain on an image whose contrast and colour read digital
  feels slapped on [PRACTITIONER · Cullen Kelly, Frame.io 2023]. As one texture that unifies a cut of mixed sources
  [PRACTITIONER · D'Anna, DC Color EP005; INFERENCE: camera, stock and generated clips make such a cut]. Lightly, to
  tie a commercial look together [PRACTITIONER · McCarthy, LBB 2026]. As a dither under glows and soft vignettes
  that would band [PRACTITIONER · D'Anna; Rich Young].
- **Not when.** Clean, modern registers, where a smooth image is a valid choice [PRACTITIONER · D'Anna]. When nobody
  asked: Kelly used none in 2022 unless a client asked [PRACTITIONER · Kelly, via Daejeon Chronicles], and Walter
  Volpatto mostly avoids it for streaming, because compression destroys it and it makes the encoder work harder
  [PRACTITIONER · Volpatto, via Daejeon Chronicles]. Heavy grain on a hero product shot [PRACTITIONER · McCarthy].
  Grain standing in for a look [PRACTITIONER · Carman]. Grain the brief needs seen on Reels or TikTok (Delivery).
- **Where.** Every textured shot at one setting, because grain that changes between shots is the failure
  [PRACTITIONER · Kelly]. `grade_luts.py` keeps product, anatomy and clean shots clean even with the switch on, so a
  spot that cuts from textured shots to the packshot shows the grain switching off. If that reads on the contact
  sheet, leave grain out and keep the bloom, which is the course's own commercial choice [PRACTITIONER · course notes]. Grain goes on inside the 9:16 timeline, after the reframe: Film Grain is generated at the project
  resolution, and a 9:16 crop from a grained 16:9 HD render enlarges the grain about 1.78× [INFERENCE]. Put it on
  the clip's `texture` node or a clip group's post-clip graph, never the Timeline graph, which also grades the
  titles and captions Resolve finishes [SECONDARY · Blackmagic forum, Shebanjah Klaasen 2023]. Titles and captions
  stay above it. It goes after keys and noise reduction, since grain early in the tree makes qualifiers chatter
  [SECONDARY · Blackmagic forum 2022]. Use one grain source, never two: Film Look Creator's Grain, Halation's Basic
  Grain or Film Grain [PRIMARY · ch. 157].
- **How much.** The house start is C2's 3–6 %, kept only where it survives the round trip (`realism-qa.md` §4
  step 4); the switch changes neither. Kelly sets Film Grain at full opacity to judge it, picks a preset, sets size
  then strength, then drops Opacity to about 30 % until the grain is felt rather than seen [PRACTITIONER · Kelly,
  Frame.io 2023]. That is the effect's own opacity, not the house percentage. The course names a 35 or 65 profile,
  kept subtle, for when it does grain a commercial; on its own commercial it says grain is off, though the panel
  read 35 mm and on [PRACTITIONER · course notes · read off the course frames]. As a dither only, 1–5 % noise, in another
  NLE's units [PRACTITIONER · Rich Young]. No hero product shot carries heavy grain.
- **Delivery.** Grain is expensive to encode. Netflix's AV1 grain synthesis took one sample frame from about 8,274 to
  2,804 kbps and averaged 36 % less bitrate at 1080p and above, about 10 % below [PRIMARY · Netflix TechBlog, July
  2025 · netflixtechblog.com/av1-scale-film-grain-synthesis-the-awakening-ee09cfdff40b]. No social platform is shown
  to synthesise grain, so it is encoded as picture detail and spends bits the faces, product and type need
  [INFERENCE]. At the medians above, grain at Kelly's level is invisible or turns into compression noise on Reels and
  TikTok [INFERENCE]. `look_qa.py`'s round trip runs at 3 Mbit/s, above both medians, so passing it is necessary,
  not sufficient [INFERENCE]. Fine, clean grain survives a web upload better than coarse grain [SECONDARY ·
  PremiumBeat 2017], and as a dither it still breaks up banding after YouTube's encode [SECONDARY · PremiumBeat 2021].
- **Tells it is cheap.** Grain on a digital-looking image; grain that changes between shots, or appears on only some
  [PRACTITIONER · Kelly]; the same amplitude in the blacks as in the mids, where real grain rises with exposure
  [PRIMARY · Fusion Film Grain, Resolve 18.6 manual]; grain that lifts the blacks [PRACTITIONER · Orash Rahnema,
  Lowepost]; grain on titles [SECONDARY · Klaasen]; a frozen or looping pattern on moving footage [INFERENCE].

*Vignette* (`finish-texture`). Two devices, and the switch treats them differently.
- **When.** *The motivated window* is a static, inverted Power Window shaped to a real or implied source. It gives
  the frame weight while the subject keeps a healthy level [PRACTITIONER · Cullen Kelly, Mixing Light 2022; Patrick
  Inhofer, Mixing Light 2022]. This is mostly what commercial colourists mean: grading that guides the eye to the
  product and off the distractions [PRACTITIONER · Karol Cybulski, Harbor, LBB 2024]. Under the switch the ads lane
  may use it on a wide, an interior or a night shot whose edges compete with the subject. *The stylised lens
  vignette* (the template's DCTL, Film Look Creator's Vignette, the Vignette FX) darkens the corners by a lens law,
  whatever the light. It needs the stronger case. In ads it goes only on a look that already reads as film (the
  bloom's **When**) and a frame whose corners and bottom carry no type, or as part of a vintage or archival look
  [PRIMARY · ch. 157, Film Damage › Add Vignetting].
- **Not when.** By reflex, as the same shape on every shot [PRACTITIONER · Kelly]. To fix exposure: fix the light
  ratio first [SECONDARY · a Mixing Light member, quoted by Inhofer 2022]. Three more cases [INFERENCE]: frames whose
  edges carry information (UI recordings, screen captures, split screens, product grids); high-key or white-seamless
  sets, where it reads as grey corners; packshots on white or brand-colour grounds, whose colours are spec.
- **Where.** *The window* is built by hand on a clip node after `look` and before `texture`, like the face lift
  above (the API cannot add nodes). It is static only: no tracker, and no keyframed position or shape, the face
  lift's own rule. The research says to track a vignette or not use it; with the house's no-tracker rule, a
  moving shot gets the lens vignette or none. Never across a face: a darkened face means the window is not inverted
  or its soft edge crosses it [SECONDARY · DaVinci Resolve Club]. *The lens vignette* is the template's timeline
  `vignette` node. That node runs after every clip's `texture` node, so it dims the grain in the corners (the
  research would put a lens vignette before the grain [INFERENCE]). The Timeline graph also grades titles and
  captions finished in Resolve [SECONDARY · Klaasen], so in ads keep it light enough that `title_qa`'s contrast
  check still passes on the worst frame. On 9:16, centre it on the safe box, not the frame [INFERENCE]. The house box
  (top 15 %, bottom 35 %, `delivery-format.md` §3) runs y 288–1248 on 1920, so its centre is about y 768, 192 px
  above the frame's. Across, keep x 540, as titles do (`typography-and-captions.md` §6c item 9).
  `cine_vignette.dctl` is frame-centred and has no centre control. The Vignette FX's Advanced mode has Center
  [PRIMARY · ch. 157], and a window goes where it is drawn. The caption veil of `caption-shadow-first` is a vignette
  too (`typography-and-captions.md` §4).
- **How much.** No quality source gives a numeric range. Strength is judged by eye: the subject's level stays
  healthy, and no ring shows on skin or a white wall [PRACTITIONER · Kelly; Inhofer; SECONDARY · DaVinci Resolve
  Club]. If a ring shows, change shape and softness, not strength. The course puts its vignette last, at a panel
  amount near −0.3, then watches every clip and pulls it back where it is heavy [PRACTITIONER · course notes · read off the
  course frames]. That is another NLE's scale: that it matches `grade_luts.py vignette --stops 0.3` is coincidence,
  not confirmation. Edge figures of half a stop to two stops come from unsigned explainers and are not
  adopted.
- **Delivery.** A wide, soft vignette in a dark scene bands at Reels and TikTok bitrates, and grain dithers it
  [PRACTITIONER · Rich Young; D'Anna]. Darkening the bottom 35 % can help white platform text, and can bury dark
  captions and marks [INFERENCE]. Meta may zoom a 9:16 ad on a taller phone and crop outside the safe zone
  [SECONDARY · quoting Meta's ads guide], so keep the falloff gentle enough that a crop leaves no half-ring
  [INFERENCE]. Film Look Creator's Film Gate (blanking) is a different device. Kelly finds it wrong for most projects
  [PRACTITIONER · Kelly, Frame.io 2024], and on 9:16 it collides with the safe box [INFERENCE].
- **Tells it is cheap.** The same oval on every shot; a visible ring or empty black corners; a darkened subject, or
  a falloff that fights the light's direction; darkness that wanders [PRACTITIONER · Kelly; Inhofer; SECONDARY ·
  DaVinci Resolve Club].

*Light leaks* (`light-leak`; the budget in § Transitions points here)
- **When.** Motivated by film or by a real source. Film fogs at a roll's head or tail, and flashes as a film camera
  starts [PRACTITIONER · DVXuser thread 2005; Phil Rhodes, RedShark]. A Super 8, home-movie or nostalgic register
  calls for it, as do memory, dream and flashback [PRACTITIONER · Tiffany Harness, Videomaker; Sara Zarrella]. So
  does a music video whose flash sequence says something [PRACTITIONER · Graham Patterson, Modern Post], and a sun,
  headlight, fixture or fire in or near frame, where Lens Reflections is the native match [PRIMARY · Resolve 21
  manual, ch. 160]. A real shoot can make its own in camera: lens whacking [PRACTITIONER · DVInfo.net wedding forum
  2014], or the small orange gel held at the lens in the course [PRACTITIONER · course notes · read off the
  course frames].
- **Not when.** As a generic pack transition, or to hide a weak cut [PRACTITIONER · LBB editors' roundtable 2023].
  Stock overlays on digital footage with nothing to motivate them [PRACTITIONER · DVInfo 2014]. A TikTok ad meant to
  look native: TikTok asks for a DIY, not over-polished style [PRIMARY · TikTok Ads help, creative best practices],
  and a stock leak reads as edited [INFERENCE]. Saturated leaks over faces [SECONDARY · We Design Motion]. A film
  meant to age well [PRACTITIONER · Zarrella].
- **Where.** One hit on one cut (the switch), inside the accent budget, on a cut the brief already motivates: a jump
  in time, memory or place; the open or the close [PRACTITIONER · Tim Clague, Projector Films]; or a hit the
  client's track already makes, never on every cut or bar [PRACTITIONER · Patterson]. Peak on the cut, then a fast
  fade [PRACTITIONER · course notes]. Park the brightest frame on the edit, with a 3–4 frame dissolve at each end
  if the clip does not start and end on black [SECONDARY · No Film School 2016]. It lives on the Edit page, as a
  transition or an overlay on a track above; never a grade node, never a look. Built as a transition, it keeps the
  budget's rule for dialogue clips. Captions, titles and the disclosure sit on tracks above it, and it never crosses
  the product, a price or the disclosure [INFERENCE]. Resolve 21 has no "Light Leaks" effect [PRIMARY · ch. 160].
  The native ways:
  - Lens Reflections (Studio), which the manual offers for abstract leaks on a shot without intense highlights;
  - Cross Dissolve set to Additive or Highlights, or Additive Dissolve;
  - the Fusion transitions Brightness Flash and Tunnel of Light;
  - Burn Away, which costs more to render;
  - a leak clip on a track above, with Composite Mode Screen, Add or Lighten and Opacity lowered [PRIMARY ·
    Resolve 21 manual, ch. 55 and 57].

  An installed, starred `light-leak` item (§ The installed library) comes before a new one, and the course reuses a
  past job's setting rather than inventing one [PRACTITIONER · course notes]. A stock pack or a paid leak plug-in is a
  purchase and needs the owner's approval. A landscape leak in a 9:16 cut needs a rotate and a resize
  [PRACTITIONER · course notes].
- **How much.** There is no reliable count per film. One or two a scene comes from weak sources [SECONDARY ·
  Cliptude], and the switch allows one. Strength: the course tries about 50, then 40, 30 and 20 on Screen, its panel
  printing 16.7–32.7 %, and pulls the colour out when the hue is wrong [PRACTITIONER · course notes]. Weak sources
  put overlays at 40–80 % with a short flash at full [SECONDARY · davinciresolve21.com], and about 30 % over a held
  shot [SECONDARY · ANFX]. Length: 1–2 s, from one explainer [SECONDARY · Screenweaver]. Vary it, because every
  transition at the same length is the fake's giveaway [PRACTITIONER · DVXuser 2005]. Colour: toward the shot's
  grade [SECONDARY · ANFX]. Super 8 leaks are orange because tungsten fogged daylight stock, so a cool grade can take
  a white or magenta one [PRACTITIONER · Rhodes]. Add can carry values over 1.0 that clip at delivery, so check the
  scopes [PRIMARY · ch. 57; INFERENCE].
- **Delivery.** At most 3 flashes in any second over more than a quarter of the screen. Flashes whose leading edges
  are 9 or more frames apart at 25 fps are acceptable at any brightness [PRIMARY · Ofcom/ITC flashing-images
  guidance · ofcom.org.uk/siteassets/resources/documents/tv-radio-and-on-demand/broadcast-guidance/gn_flash.pdf].
  WCAG 2.3.1 runs the same 3-a-second test [PRIMARY · W3C, Understanding 2.3.1]. Any transition to or from saturated
  red is a risk whatever its brightness [PRIMARY · Ofcom/ITC]. Warm leaks drift red-orange, so take the saturation
  down before they reach red. `title_qa` counts flashes on titles only and nothing counts them on the cut, so a flash
  sequence gets a frame-by-frame look. Fades and flashes spike the bitrate [PRACTITIONER · x265 developers, 2015], so
  prefer a ramp to a one-frame spike and check the platform's copy [INFERENCE]. Soft orange gradients band after the
  re-encode, and fine grain added last helps [PRACTITIONER · Gerald Undone; SECONDARY · Neat Video], though a dither
  before a lossy encode can be quantised away [SECONDARY · Fora Soft].
- **Tells it is cheap.** The same leak clip repeated, or every leak the same length; no source in or near frame and
  no story reason; a grey haze box, because the overlay's black is not true black (crush it first); colour that
  fights the grade; a leak on every cut; a soft overlay stretched over a larger timeline [PRACTITIONER · DVXuser;
  DVInfo; SECONDARY · davinciresolve21.com; ANFX; AI Song Cover].

*Blur-in titles* (`blur-titles`) and *the blurred fill* (`blurred-fill`) have their blocks beside their home rules,
in `typography-and-captions.md` §6c: after item 3 and after item 10.

**The decision rule for the agent.**
- **(a) The house default holds.** The ads lane gets none of these six. The blurred fill stays out of every lane
  (`typography-and-captions.md` §6c item 10) and the leak out of launches too (`product-video.md` §2.5), unless the
  job carries the switch. Outside those bans, such as drama's texture and vignette, the blocks above still guide the
  work, with no switch.
- **(b) Propose, never add.** When a brief matches a device's **When** and none of its **Not when**, the agent
  proposes the switch to the owner, with the reason, in the form the CHECKPOINT line takes (`<id> — <reason>`). It
  never adds the switch itself, and never applies a device silently.
- **(c) Once the switch is on, the Where and How much bind.** Anything outside them is a finding at review: a grain
  level past the range, a leak on every cut, a blur on the hook card, a fill held past about two seconds, a vignette
  across a face. Scripts measure little of this: `look_qa.py export`'s round trip and banding, `motion_qa.py`'s
  accent budget and `title_qa`'s flash count on titles. The rest is read on the contact sheet and at review.

What the research could not settle: no viewer or performance study covers any of the six in ads; grain size against
Reels, TikTok and Shorts encoding is untested; beyond Kelly's shares of his own builds, no quality source gives a
number for bloom, halation or vignette strength; nothing measures a blur-in title's legibility after a platform
re-encode, or how long a blurred fill can run before viewers tire of it.

**The grade template.** The scripting API **cannot add nodes** [PRIMARY · the API stubs on the owner's
machine], so a DRX still carries them. Build it once by hand: label the nodes exactly as below, grab a
still and export the DRX.

| Graph | Node | Label | Holds | Switched on |
|---|---|---|---|---|
| clip | 1 | `shot_match` | the CDL | when `look_qa.py shots` solved one |
| clip | 2 | `deflicker` | ResolveFX Deflicker | when the take flickers |
| clip | 3 | `look` | the lane's look LUT | not for product, anatomy or clean shots (`grade:` in the clip prompt) |
| clip | 4 | `texture` | Film Look Creator (grain, halation, bloom) | drama only; never in ads (C2) |
| colour group, pre-clip | 1 | — | the model's correction LUT | always |
| timeline | 1 | `vignette` | `cine_vignette.dctl` | drama, `--vignette` |
| timeline | 2 | `film_look` | Film Look Creator | drama, `--film-look` |

The `texture` and `vignette` rows stay off in ads unless the job's CHECKPOINT carries the `finish-texture`
switch (`assets/project-switches.json`): then the ads lane's plan may switch on a small bloom, optional grain
and a light vignette (v2.48.0, switch `finish-texture`) — when and where: § Finishing looks.

⛔ **The labels are how the script knows it is the template.** It applies the template only to a clip
with no grade yet (one node, no tools in it). It leaves alone any clip whose labels do not match the map,
so it never overwrites a colourist's grade. Measured on Studio 21.1.1, 2026-10-26:

- a timeline with no timeline grade has **0 nodes**;
- an unlabelled node's label is `''`;
- a graded node lists its tools ("Primary Balance", "LUT: <name>");
- `GetLUT` returns the path relative to the LUT folder (`MCP/…`).

A node's on/off state has no getter, so the script reports it as set, not as read back. Groups and LUTs are
read back.

**The export look gate — `look_qa.py export`.** All thresholds are [assumed] until approved real ads
calibrate them. A FAIL refuses the export, a WARN is a finding for the colourist.

| Check | What it measures | Fails when |
|---|---|---|
| Range and tags | colour range, primaries, transfer and matrix, read from the file | full range (pc), or anything not BT.709 |
| Legal levels | the share of the picture below Y 16 or above 235 | more than 1 % |
| Legibility, per shot (ads) | tonal spread (P5–P95), blown highlights, the black floor (C1), face local contrast, caption contrast | spread under 0.40, blown over 3 %, the P2 black under 3 codes above legal black, a face under 0.06 RMS; captions under 4.5:1 only WARN |
| Platform round trip | an x264 encode at 3 Mbit/s: banding in smooth gradients, block edges, grain that survives | banding over 15 %, or grain under 35 % surviving in ads (C2: take it out); blocking WARNs |

The legibility checks are there because older viewers lose contrast sensitivity at mid and high spatial
frequencies and suffer more glare (Owsley 2016, *Annual Review of Vision Science* 2). Grain is fresh
noise on every frame, so a platform encoder smears it [SECONDARY · FilmConvert].

**A saturation band the course states, not a threshold** [PRACTITIONER · course notes]. On a beauty grade the
course aims to land saturation between 30 and 50 on the scope. One reading moved from 29 to 36 with the
grade on, and darker areas of the same frame already sat in the mid-50s [PRACTITIONER · course notes · read off the
course frames]. The course names neither the scope nor its unit, so the band cannot be measured here, and
`look_qa.py` has no saturation check. It is a practitioner claim, never a default.

## Region repair — fix one region of a good take, and blend it back in a Fusion comp (v2.49, v2.50)

Author, 2026-11-05, on whether a masked region can be repaired instead of the whole take re-rolled: *"if we
can successfully incorporate Roto, it could work"*, then *"Tracked box + SAM 2"*. So roto is allowed for
this one job. The locked rule in `assets/project-switches.json` is narrowed to **advanced VFX**: mask-wipe and
luma-key joins and heavy compositing stay out.

Author, 2026-11-05, on the blend: *"should the blend be done as a Fusion comp by computer control? — YES,
always."* The final blend of a repaired region is a Fusion comp in Resolve. It is built by computer control
(driving the Resolve window), never through the scripting API (rule 8: Fusion, Fairlight and titles are always
computer control). The tool's own composite is a **preview only**. It is never imported into Resolve as footage.

Author, 2026-11-05, on drift: *"Region repair failures: should a failed drift check block a take, or only
report it? — report it. Not sure."* So drift outside the region is reported and never blocks. **Provisional:**
revisit it after the first real job.

**When.** A take is right except in one region (a hand, a screen, a gauge, a label, a sign) and the retake
tree (`ai-generation.md`, Retake economics) says a full retake would lose what is right. A festival team
repaired regions this way: black the region out, give the clip back to the model as the clip to edit, ask
for that region only `[SECONDARY · festival study 2026-11-05]`. **Not** for a whole shot that is wrong
(regenerate), a large face, an identity, a performance, or joining two takes.

**The tool: `scripts/region_repair.py`** (numpy + OpenCV + ffmpeg; SAM 2 optional; it never calls a paid API).
`--job` takes the `REPAIR-<label>.json` or the folder that holds it.
1. **Track** — `track CLIP --box x,y,w,h --at S [--engine box|sam2] [--frames A-B]`: the region followed
   through every frame (LK flow + RANSAC with template fallback; or SAM 2 for organic shapes). Lost frames are
   marked, never invented. `--frames` limits the work to the frames the cut uses plus handles.
2. **Mask** — `mask --region … --contains "<what belongs there>" [--pad] [--feather] [--ref-image …]`: the
   masked plate (the region pure black, same size, fps, frames and sound) and a prompt stub,
   `REPAIR-<label>.prompt.md`: keep every unmasked pixel, the timing, the camera, the light changes and the
   sound; rebuild only the black region; what the region must show.
3. **Repair** — one `seedance_2_5` call, `mode: video_edit`, the masked plate as `video_references`, linted
   and gated like any call. Nothing is spent without the gate.
4. **Preview (optional)** — `composite REPAIRED --job …` writes `PREVIEW-<label>.mov` beside the job. Only
   the masked region comes from the model's clip; every other pixel is the source's. The name must start with
   `PREVIEW-`, or it is refused. Its record says `"preview": true`. `qa --composite PREVIEW-… --repaired …
   --job …` measures it. Never put it on a timeline.
5. **The Fusion kit** — `fusion --job … --repaired …` writes `FUSION-<label>/`:
   - `matte/%06d.png`: the matte exactly as the tool blends it. It is grown by the job's pad and feathered
     8 px inside the edge (`--feather`). It is 8-bit, full source size, with the matte in R, G, B and alpha.
     Frame `000000.png` is the first frame of the work range, so the Loader needs no trim. It sits at
     Global In = the work-range start, which `fusion.json` records as `global_offset`.
   - `track.csv` and `track.json`: the region per frame in Fusion's coordinates (x / width, 1 − y / height),
     its size and its scale; lost frames flagged. Only for keying a Transform by hand.
   - `RECIPE.md`: the node-by-node build, the checks, the render and the qa command, with the real paths and
     frame numbers filled in.
   - `fusion.json`: what `qa --render` checks against.

   Like composite, it refuses a reframed clip, and a frame count off by more than one unless `--retime`.
   `--retime` writes `repaired-conformed.mov` for the Loader.
6. **Build the comp by computer control, from `RECIPE.md`.** Put the whole source clip on the timeline,
   untrimmed. In the Fusion page:
   - MediaIn1 is the source clip.
   - Loader1 is the repaired clip, at Global In = the work-range start. Add a Resize to the source size when
     the model's clip is another size.
   - Loader2 is the matte, at the same Global In.
   - Merge1: Background = MediaIn1, Foreground = the repaired clip, Effect Mask = the matte through a Bitmap
     mask with its channel set to Luminance. A bitmap mask with no channel set blocks everything.
   - An optional Transform aligns the repaired clip by hand. Alignment is not automated yet.
   - Merge1 goes to MediaOut1.

   Check before the render:
   - the first and the last frame of the work range at full size (100 %), against MediaIn1;
   - the frames just outside the work range: the untouched source;
   - after any comp import, every Loader again: importing a comp turns Loaders into empty MediaIns;
   - never wire nodes through the API. It cross-wired inputs.
7. **Render, then QA** — render the clip from Resolve: the whole source clip, the same size and frame rate,
   ProRes 4444, with no grade. Then run `qa --render RENDER-<label>.mov --repaired … --job …`. It needs no
   composite record. It checks identity against the job and `fusion.json`. It takes the pad from the job, the
   feather from `fusion.json`, and the drift tolerance from the render's own codec. It measures:
   - drift outside the region;
   - the seam per side and per colour channel;
   - sharpness, grain and black level inside, against the surround;
   - a ±2-stop gamma slam of the seam;
   - flicker inside the mask;
   - a region that came back still black;
   - coverage: the repair is in the render, on the right frames. It FAILs a render that shows the source in
     the region, or the model's clip one frame early or late.

   Exit 1 on any FAIL. **Drift outside the region is a WARN, never a FAIL** (2026-11-05, provisional).
   It is printed first, with its numbers. It changes neither the verdict nor the exit code.
8. **Then the edit**: the clip with its comp is cut and finished in Resolve (house rule: all edits in
   Resolve). The contact sheet of the render comes before anyone sees it, first and last frame included.

**Open, from the research (the author's research notes, not shipped):** align the model's clip to the source
before the blend (a shift or re-crop doubles the seam; today it is a Transform keyed by hand from
`track.csv`); size the pad from the model's working grid and the motion blur (12 px is likely too small); hull
and box mask shapes with ±2 frames of temporal spread; fill lost frames and fade the repair in and out; a
motion-compensated edge-flicker check; a small paid calibration test (black vs grey fill, pad size, tight vs
hull). Thresholds are [ASSUMED] until a real repair calibrates them. **Also open, from 2.50:** whether a
failed drift check should block (decide after the first real job), and whether the Fusion page numbers the
comp from 0 on the clip's first frame (the recipe assumes so, and its first- and last-frame checks confirm it).

## Music bed — ask the user which track, every time

**Never pick the bed track autonomously.** **Ask the person where their licensed music lives**, the
first time (v2.68.0: the plugin never assumes a music folder): `music_fit.py library add <their folder> --name
<name> --paid-ads yes|no|unverified --licence "<the licence, in their words>"` catalogues and measures it
(tempo, beat grid and its reliability, length, ending). Then `music_fit.py shortlist <job> --mood "<the brief's
mood words>"` brings two or three cues, each with its reasons: cleared for paid ads, long enough for the cut or
needing a phrase edit, ending on a hit for the button or fading, a sung lyric flagged, and, once the hit list
exists, how well the existing fitter lands the must-hits (on a steady beat grid; bar lines guessed by the numpy
engine are flagged, not trusted). With no mood words and no hit list it says it has nothing to rank by. Tracks
with no vocal or instrumental tag say "lyrics unknown"; "no vocals" or "instrumental" in the file name, the
description or the studio's own tags marks a track instrumental. `--tags-csv` (filename,tags) adds the studio's own mood
words to a library whose files carry none. Music not cleared for paid ads is never shortlisted
unless the person says so (`--all-licences`, internal work). **Then ask the person which track** to use before
touching the edit. Mood is a creative call that belongs to them, not a default to reach for because a track
happens to fit the runtime. The shortlist never compares a track's loudness curve with the shots' Energy: that
column is picture intent, and a first plan that did so was cut in review as ranking noise.

**Bring a shortlist, not one track** [PRACTITIONER · course notes]. Two or three cleared cues, each auditioned
under the finished voice cut with the others muted. Drop any build that crowds the voice before it reaches
the list. Stems let a bright part be pulled out, and a cue with no stems can still win if it fits and
stays even. The client picks, through the owner; the agent only shortlists, and the cut is not re-cut to
the winner (§ Music to picture). Mood words come from that client's brief, never from a default. The
course puts the shortlist at half an hour to an hour.

**What "composing" means in this skill (house rule C7, 2026-10-26, and v2.40, 2026-10-27).** Library
music arranged for the story is still the default bed: the library's own cutdowns (60/30/15), its stems and
alternate mixes, whole-bar edits, one stop-down and one drop, the vocal stem muted under speech (§ Music to
picture, below). Since v2.40 the skill is also the lead composer (§ The lead composer, below). It writes the
composer's brief and spotting note. It drafts the client's motif for the owner to edit. It composes the layer
of accents and the button over the library bed. It writes whole cues with a rules-first note engine. And it
can trial generated beds blind. The options:

- **A, library only:** always available. Use the track whole, with no edits.
- **B, library plus arranging:** the default.
- **Route 1, composed here:** owner-edited motif, layers and cues rendered from licensed instruments, with
  their provenance.
- **C, generated music as a temp track only:** logged in the job, never delivered.
- **D, generated music shipped:** case by case, and only when all of these hold:
  - the client's written consent is recorded **before** the generation (amended 2026-10-27, IPA/ISBA
    Principle 11);
  - the vendor is on the whitelist (`assets/music-generators.json`: ElevenLabs paid plans and Stable Audio);
  - the terms page is snapshotted at generation;
  - the vendor has passed a blind bake-off this quarter;
  - the record names the plan, the prompts and the human edits.

  No generator indemnifies the user, and copyright may not vest: prompts alone do not make an author
  [PRIMARY · US Copyright Office, 2025-01-29].
- **AI vocals** (2026-10-27: *"AI vocals - needed sometimes"*): case by case, under D, plus:
  - lyrics written by a named person, never an existing song's;
  - a voice described without any artist, and no soundalike;
  - the disclosure written down;
  - the client's consent to AI vocals.
- **E, Higgsfield's Sonilo:** excluded. The account marks it "Game pipeline only".

**If the chosen track is shorter than the assembled video, loop it on the phrase lines.**
`scripts/loop_music_to_length.py` maps the track (`music_fit.py`'s analysis), plays it to the last phrase
line, repeats the passage from an earlier phrase line, and joins just before the downbeat with a short
equal-power crossfade. Then it trims to the exact length with its own head and tail fade. If the track is
already long enough, it trims cleanly. Run it either way:

```
python3 scripts/loop_music_to_length.py 06-music/chosen-track.mp3 --match-video 10-export/<SLUG>-vN-final.mp4
# or, before the final export exists yet: --target-seconds 58
# --blind = the old loop (a 2.5 s crossfade wherever the length falls) for a track with no beat to find
```

When the film has a hit list, use `music_fit.py fit` instead: it fits the length and the hits together.

**v2.49 (house rule 9):** the loop is a **plan**. Its render is a proof to listen to, never the bed that
ships: the loop points and the crossfade it found are made in Resolve, on the music lane, at the same
frames (§ What runs through the API).

⚠️ **SUPERSEDES IN PLACE** (2026-10-26) — previously: the loop "repeats the track with an `ffmpeg
acrossfade` crossfade at the seam … default 2.5s". That seam fell wherever the length did, not on a bar, so a
listener heard the phrase restart mid-bar. It is now `--blind`.

File the result per the naming convention (`06-music/MUSIC_<track>_<bpm>bpm_v1.mp3`) and note the
BPM in the PM board per `pm-workflow.md`.

## Music to picture — fit the track to the cut, never the cut to the track

Author, 2026-10-26: *"Detect music beats, and move the sound track to match the cuts? Since cuts are based on
motion and object analysis, not the score itself?"* The council
(the music-to-picture proposal of 2026-10-26 [studio history]) ranked it first in every lane, and they chose all four
packages with the ruling *"Music only; suggest cut nudges"*. **The cut never moves by itself.** The music
is fitted to the locked cut. A cut that a 1–2 frame nudge would put on a beat is listed for them to approve,
and the approval is recorded. That holds unless the job's CHECKPOINT carries the `music-led` switch
(`assets/project-switches.json`): the song is fixed and is the deliverable, so the picture is cut to its beats
and sections; the song is still the client's, never picked here, and no genre-to-camera mapping comes with it
(`cinematography-craft.md` §3.9) (v2.48.0, switch `music-led`).

**Why this direction.** Editors cut picture first and lay music after. Cutting so "the edit serves the
track" is the anti-pattern, and cutting on every beat reads as flat [BOOK · Hullfish, *Art of the Cut*].
Measured ads cut on a beat no more often than chance (31 % of cuts against 32 %, `specifics-catalogue.md`
§16.6). The beat is for a few hits: the reveal, the product landing, the title, the button
[PRACTITIONER · MusicTech].

**The order, per film:**

1. **The map.** `music_fit.py map 06-music/<track> --job <job>` finds the beats and downbeats, bars,
   4-bar phrases, section changes, energy per bar, the key (advisory) and how the track ends (a hit or a
   fade). It uses Beat This! when installed (MIT, beats and downbeats, `pip install beat-this` with
   PyTorch), then librosa, then a numpy tracker that reads the meter's phase from the low-band onsets.
   The map is cached in `06-music/fit/<track>.map.json`. A low-confidence map says so: rubato, live-played
   and ambient tracks fool every tracker. Cross-check it against Resolve's **Detect Music Beats** overlay
   (Studio).
2. **The hit list.** `music_fit.py hits init <job>` drafts `07-edit/music/HITS.json` from the timeline dump
   (`resolve-production-console.py`, `DUMP_TIMELINE_JSON`). Every cut is an optional hit, the end card is
   the button, and the dialogue tracks become the speech spans. The director edits the draft:
   - marks the **2–4 must-hits**, each with a `type` and the music event it `want`s: `downbeat`, `beat`,
     `accent`, `riser_end`, `stop_down`, `drop`, `entry` or `button`;
   - declares the track: `file` (the one the owner picked), `vocals` (`none`, `lyrics`, `vocal_chops`),
     `edits_allowed` (`yes` once the licence says so), `stems`, and `in` (`phrase` by default, `any`, or a
     time in seconds);
   - adds `sections` (`t0`, `t1`, `energy`: `low`, `mid` or `high`) for the arrangement, and any `fx`
     (risers, impacts, sub drops, scratches, whooshes) for the accent budget.

   A film with no music bed says `"music": "none"`, and `approve export` notes it.
3. **The fit.** `music_fit.py fit <job>` solves in this order, and stops at the first step that works:
   1. the library's own cutdowns (a 60, 30 or 15 s version beside the track);
   2. the in-point, slid over the downbeats (phrase starts by default) with no edit at all;
   3. whole bars removed or repeated at a phrase line after the last must-hit;
   4. one beat added or dropped, only to land a must-hit ("usually not conspicuous" [PRACTITIONER ·
      MusicTech]);
   5. a pitch-kept stretch of at most ±2 %, last.

   It writes the three best plans to `07-edit/music/FIT.md`, each with every hit's residual in frames and
   milliseconds and the cut nudges. The owner picks one (`--pick N`). The pick is stored in `07-edit/music/FIT.json`
   with the cut it was fitted to.
4. **The rebuild, in Resolve.** ⛔ Author, 2026-11-05: *"never import like that in to Resolve, everything has to
   be rebuilt and done in Resolve for client deliverables."* The music the client gets is cut in Resolve, from
   the ORIGINAL track. `music_fit.py rebuild <job>` writes the picked plan as that edit. `fit` and `render`
   run it too.
   - `07-edit/music/REBUILD.json`: each segment's source in and out in the original, and its place on the
     timeline, in seconds and in frames at the job's rate. Each seam's cut and crossfade length. The end trim
     and its 0.75 s fade. The speed. The original's sha256, and `plan_sha`, the sha256 of the picked plan.
   - `07-edit/music/REBUILD.md`: the checklist for the Resolve side, done by computer control.
   - `07-edit/resolve-production-console.music.py`: imports the original once and places each segment on
     **A5** as a source range at its frame. It reads each one back, start and length, and reports any that
     differ. It never places over a clip already on A5 and never deletes anything. Markers: Red on the phrase
     starts, Green on the must-hits, Yellow on the listed nudges, Cyan on each seam and over the end fade.

   The script places on whole frames. Each segment's downbeat may sit up to half a frame off the plan, and
   REBUILD.json lists that offset. The cut at a seam sits on the frame at or before 10 ms ahead of the
   downbeat, so no downbeat loses its attack.

   Then, in Fairlight, by computer control (house rule 8, never the API), as REBUILD.md lists:
   1. check A5 against the table;
   2. slip any segment the table shows off its downbeat;
   3. add each seam's crossfade at the stated length, centred on the cut;
   4. fade the end over 0.75 s;
   5. listen at every seam and at the end;
   6. export the music stem (A5–A6 only, the ducking on, 48 kHz) into `09-qa/mix/` and pass it to
      `mix_qa.py measure` as `--music`.

   With a speed change (a stretch), the script does not place the segments. It places the original whole.
   Retime it first, pitch kept, then cut the segments at the retimed times REBUILD.md gives.

   **The render is a preview.** `music_fit.py render <job>` still cuts the plan in Python, to listen to:
   `06-music/fit/<track>.fit.wav`, 48 kHz, 24-bit, with its `.conform.json` (kind `music_fit_preview`, so the
   track's licence travels with it). Nothing places it. Never import it into Resolve.

   ✅ **Decided (2026-11-05).** The render is a preview. The deliverable is rebuilt in Resolve from
   REBUILD.json. `approve export` no longer asks for a render. It asks for a current REBUILD.json, and it
   refuses a preview found on the timeline. Every Python-rendered music or SFX file is a preview:
   `06-music/fit/`, `06-music/bed/`, `06-music/family/`, `06-sfx/conform/`, and any `.fit.wav`, `.arranged.wav`,
   `.bed.wav`, `.full.wav`, `.joins.wav` or `.preview.` file (`music_fit.is_preview`). The original track, the
   composed layer and its stems are source material. `gate.py` refuses a Resolve script that imports or places a
   preview (v2.50), as it refuses region repair's `PREVIEW-*.mov` composite; no allowance covers it.
5. **The arrangement, when the story asks.** `music_fit.py stems <job>` takes the library's own stems
   first. Only on demand does it run Demucs (MIT, archived; four stems, about 1.5× the track's length on a
   CPU). `music_fit.py arrange <job>` then mixes the stems on bar lines to each section's energy, cuts one
   beat of accented silence before a declared `stop_down`, opens up on the `drop`, and mutes the vocal stem
   under speech. The arranged bed is a preview (`music_arrangement_preview`). REBUILD.json and REBUILD.md list the
   arrangement for Fairlight: the stems, the section levels, the stop-downs and the vocal stem muted under speech.
   The original on A5 is not that arrangement, so it is rebuilt there from the stems. Resolve's
   **Music Remixer** (Resolve 19+) is for auditioning a balance only. The API cannot read it back, so the
   script renders the stems (C6).

**The windows — tiered (house rule 2026-10-27).** Each hit is `hard` (director-called) or `soft`
(secondary); unset, a must-hit is hard and an optional one soft.

- **The impact onset is never early.** Audio that leads is detected at 45 ms, audio that lags at 125 ms
  [PRIMARY · ITU-R BT.1359].
- **A hard hit** lands 0 to +1 frame after its picture event; +2 frames warns.
- **A soft hit** may land up to +2 frames late (83 ms at 24 fps, 67 ms at 30).
- **The onset is the measured transient peak.** The anticipating gesture (a swell, a pickup) may start
  early. Each hit records `gesture_t` apart from `t`, and its `strategy`: catch, anticipate or play_through.
- **The windows are stated in milliseconds** from the timeline's rate, so 24, 25 and 30 fps stay right.
- **Density.** More than 2 hard hits in a 15 s spot, or 4 in any spot, warns. A stop-down counts as a hit.
  `play_through` takes a hit out of the count.

These numbers come from lip-sync research, not music. A small listening test on music hits at 24 and 30 fps
would settle them.

⚠️ **SUPERSEDES IN PLACE** (2026-10-27) — previously (C1, 2026-10-26): "A music hit sits 0 to +1 frame after
its picture event … +2 frames warns" for every hit. The council kept that for hard hits, gave secondary hits
+2 frames, and named the onset.

**The edits (B).**

- **Hide each join.** Cut about 10 ms before the downbeat's transient with a short equal-power crossfade:
  3 ms on a strong transient, 40 ms where the material masks it. A strong backbeat masks an edit
  [PRACTITIONER · Sound on Sound].
- **The stretch cap (C2).** At most ±2 %, one constant stretch, no ramps. A warning above 1.5 %, and no
  stretch at all on a track with sung vocals. Tempo-change thresholds fall to 1.5 % at 75–200 BPM
  [PRIMARY · Drake & Botte 1993], and a stretched recording can be told from the original [PRIMARY · Honing
  2005].
- **The ending.** The last hit or downbeat lands on the end card's first frame and rings out under the
  card. A fade is the fallback, with a warning.

**Punctuation (C3), all untested, as warnings.** By default an ad takes one stop-down and one drop, and the
drop never comes in the first act. Long brand or drama pieces (over 45 s) may take two stop-downs. A
stop-down cuts out for a beat and comes back with impact; the drop is the payoff [PRACTITIONER · Rareform].
An accented silence on a strong beat is felt, because the meter is a grid the listener keeps even without
notes [BOOK · Tan, Pfordresher & Harré].

**One accent budget with the SFX (A11).** Risers, impacts, sub drops, scratches and whooshes are counted
together with `sfx_conform.py`'s joins: 2–3 risers per ad, each ending exactly on a must-hit; a scratch at
most once; one owner of the low end per hit; no whoosh within 2 frames of a riser's end.

**No sung lyrics under speech (A12).** Use the instrumental or underscore mix first; otherwise mute the
vocal stem. Speech is most intelligible over instrumental music, and meaningful lyrics interfere most
[PRIMARY · Brouwer et al., *J. Exp. Psych.: Applied*].

**Two tracks (A10), off by default.** Short ads rarely earn two tracks. When a film joins two, the key
relation is advisory (Camelot distance), and the owner listens to every join. A hard cut under a stop-down
sidesteps key (C4).

**The check — what `approve export` runs (C5: rules refuse, measures warn).** `music_fit.py check <job>`.

- **Refused:**
  - no hit list, or no fit;
  - no REBUILD.json, or a stale one (the picked plan or the original changed since it was written) —
    `music_fit.py rebuild <job>`. No render is asked for;
  - a preview render on an audio track of `07-edit/timeline-dump.json` — rebuild it in Resolve from the
    original;
  - the cut changed since the fit (a stale fit);
  - a cut moved without an approved nudge in `approved_nudges`;
  - a stretch over ±2 %, or any stretch on sung vocals;
  - edits on a track whose licence is not recorded as allowing them;
  - sung lyrics under speech, unless arranged;
  - a music stem from Resolve that is not 48 kHz;
  - a click at a music seam of that stem (on the bed, which carries other sounds, a click only warns).
- **Warned:**
  - nothing measured yet: no music stem from Resolve in `09-qa/mix/`. The check reads the stems `mix_qa.py`'s
    report records (`--music`, else `--bed`), else a file there named `<slug>_stem-m_…` or `<slug>_qc-bed.wav`;
  - the original track on no audio track of the timeline dump;
  - each must-hit's offset, measured on what Resolve made;
  - a fade ending;
  - a stop-down shallower than 20 dB;
  - the punctuation counts;
  - the accent budget;
  - a two-track join;
  - the share of cuts on a beat, as information only.

**What it cannot do: hear.** It aligns events and measures seams. Whether the music serves the scene is the
director's ear, and the `approve export --quote` is where that listening pass is signed. Every threshold
marked [assumed] or untested waits for real fits to calibrate it. The tracker has not yet been checked
against hand-tapped downbeats from the owner's library.

### The bed as the client hears it — `music_fit.py bed` (a supplement ad job, 2026-10-28)

The approved track on that job opened on 1.8 s of near-silence, its sections swung 14 dB, and the ad cut it off
mid-phrase. A flat fader hid all three. `music_fit.py bed <job> [--track F] [--voice V] [--length S]` makes the bed
as a client hears it, by default:

1. the opening near-silence trimmed;
2. the length met by **one** bar-aligned seam where the bars before and after match best, placed under speech,
   joined with a 30 ms equal-power crossfade;
3. the track's own ending landed on the last frame;
4. the sections ridden toward one bed level (at most ±8 dB);
5. ducked under the voice (60 ms in, 350 ms out) and 1.5–4.5 kHz carved 3 dB while it speaks;
6. the whole set to the **client's** level under the voice.

It writes `06-music/bed/BED.json`, a **level plan** for Fairlight: each step in plain words, done there by
computer control (house rule 8). `06-music/bed/<track>.bed.wav` beside it is a preview to listen to
(`music_bed_preview`). No console copy places it. A fitted plan (`07-edit/music/FIT.json`) is used as it is:
its edits already set the length and the ending.

⛔ **The bed level is the client's, not the skill's.** The measured target, 13–18 dB under the voice, was "too loud"
for that client; the owner settled on about 38 dB under, "barely noticeable". It lives in `clients/audio.<client>.json`
(`music_under_voice_db`), beside the client's profile (the private `_cine-clients/` folder or `CINE_CLIENTS`);
`sfx_conform.py levels` reads the same file. With no file the default is 16 dB, and the first client listen sets it.
The mix gate's "VO over bed" is a floor, so a quieter client bed passes it.

## The lead composer — the paperwork, the owned motif, composed layers, the note engine, generated beds

Author, 2026-10-27: *"Need more deep research on the skill being a lead composer"*. The research and the council
are in the lead-composer proposal of 2026-10-27 [studio history] and lab record lab-00018 (not shipped). They chose:

- all four packages;
- *"Skill drafts, I edit"* for the motif;
- the tiered hit window;
- consent first with a whitelist;
- −14 LUFS as a house value;
- *"AI vocals - needed sometimes"*.

Then: *"whatever you build, has to be in Resolve too (Fairlight compatible and enhanced)"*.

**Why the composer's value is not a new bed.** Bespoke beds beat library beds by about two recall points
(60.8 against 58.7) [PRIMARY, commissioned · MassiveMusic × IPA, 150 UK TV ads]. Ads with sonic brand cues
were 8.53× more likely to rank in the top third for branded attention [PRIMARY · Ipsos 2020, 2,015 ads]. So
the composer's work is three things a library cannot give:

- **A spotting plan** whose few director-called hits land to the frame.
- **An owned motif** carried across a client's series.
- **A length family** (60/30/15/6, stingers, mixes that sit under the voice) cut from one musical idea.

Language models reason about harmony near chance (GPT-4 scored 25.6 against a 25 % baseline on
MusicTheoryBench) [PRIMARY]. So the agent writes the plan, and code realises and checks every note.

`scripts/composer.py` runs it, in four packages.

### A. The paperwork (every job, library jobs included)

1. **The composer's brief.** `composer.py brief init|lint <job>` writes `06-music/COMPOSER-BRIEF.json`:
   - the media plan and its territories;
   - the references, each with **why it is liked** (ask why a temp was chosen, not only which);
   - the music's role (hero or texture);
   - the VO density;
   - the slot lengths;
   - the mnemonic (the brand name and its syllables);
   - the revision cap;
   - the deliverables;
   - the route;
   - the client's consents.
2. **The spotting note.** `composer.py spot init|lint <job>` writes `07-edit/music/SPOTTING.json`. Each cue
   records its function, the one feeling it serves, the temp and why it was liked, withhold or release, and
   (last cue) the end-card mood. The music under the product shot changes what is remembered (Boltz 2001).
   The note is spotted at the timeline's fps, and lint refuses a mismatch.
3. **The hit record.** Each hit carries its tier, strategy, gesture and onset (§ Music to picture, the tiered
   windows). `music_fit.py check` measures every hard and soft impact on the render in milliseconds.
4. **Consent.** `composer.py consent <job> --by … --quote … --scope generated,composed,ai_vocals` records the
   client's own words. For generated material the consent must be dated **before** the generation.

At export the paperwork **warns** on a library-only film and **refuses** once anything is composed or
generated.

### B. The owned identity layer

1. **The motif: the skill drafts, the owner edits (K2).** `composer.py motif draft <brand-music-dir> --brand B
   --key K --syllables "a-MUR" --feeling warm` writes three drafts as JSON and `.mid`:
   - 3–6 notes, simple 1:1 and 1:2 rhythms;
   - the brand name's rhythm ends the motif, with the stressed syllable long;
   - a rising contour reads exciting, a falling one pleasant;
   - each ends on the tonic or the fifth.

   The owner edits one in any MIDI editor (or the JSON). `motif adopt --draft N --edited <file> --by <name>`
   keeps the diff as the evidence of their authorship. It is **refused** when less than a third of the notes
   changed, unless he says he wrote it himself. Each motif is checked against his kits' MIDI
   (`--midi-dir`) and every other client's motif. The same intervals with the same rhythm are refused.

   Why the owner's hand matters: the US Copyright Office, the Philippine IP office's draft guidelines and a
   Czech court all deny protection to AI-generated material, and none of them treats MIDI differently from
   audio. The owner's edit is what can make the motif theirs, case by case; counsel has the last word.
2. **The brand name.** Build it into the motif's rhythm where it fits. Logos that carry the name scored 29 %
   higher in Veritonic's vendor index, which also found 0 % correct brand association for Mastercard's logo.
   One vendor's index, so it is a warning, never a refusal.
3. **The key, confirmed by ear (K9).** `composer.py key confirm <job> --key C#m --by Dana`. The map's key
   detector errs on modal and sparse beds. No layer is made, and nothing exports, on an unconfirmed key.
4. **The layer.** `composer.py layer <job> --motif <dir>/MOTIF.json` writes the layer on the bed's bar grid:
   - an impact on every hard hit, 8 ms after its frame (inside the window; measured at export);
   - the mnemonic as the button, its last note on the end card's first frame;
   - the motif transposed by scale degree into the bed's confirmed key;
   - motif notes muted under speech;
   - the impacts counted in the accent budget with the SFX.

   It renders `06-music/compose/<job>.layer.wav` and a stem per part (48 kHz, 24-bit, −3 dBFS peak, no
   limiter; the stems sum to the mix), plus `.compose.json` (the provenance) and `.licence.json` (its audio
   manifest row: own composition, and its instruments' licences).
5. **The length family.** `composer.py family <job> --lengths 30,15,6` fits each length with the same solver.
   Each ends inside its slot on the mnemonic. It also writes the full alt mix (bed plus layer); the underscore
   mix is the bed.
6. **The element sheet.** `composer.py elements <job>` writes `09-qa/mix/ELEMENTS.md` for the client. It
   classes every sound:
   - library;
   - human;
   - sample-rendered (composed here);
   - AI-generated.

   It also writes what each needs disclosed (compliance.md §5).

### C. The note engine (route 1, whole cues)

1. **The tempo map.** `composer.py solve <job> --bpm 70-140` sets one tempo in 4/4, with at most one inserted
   2/4 or 3/4 bar ("a single beat change is usually not conspicuous", MusicTech), so that every hard hit lands
   on a downbeat. It ranks three maps. A hit no tempo can land is named; the owner marks it `play_through`
   (`--play-through H3`).
2. **The plan.** `composer.py plan template <job>` writes `07-edit/music/PLAN.json` with:
   - a section per spotting cue on bar lines;
   - a Roman numeral per bar, '?' until written;
   - the parts;
   - where the motif plays.

   **The agent writes the key and the chords.** `plan lint` refuses a chord that is not a Roman numeral, a
   section that does not run on, and a part outside the palette.
3. **The notes.** `composer.py realise <job>` voices and checks them:
   - pads by the nearest move, never in parallel fifths or octaves with the bass;
   - the bass on the roots;
   - piano and arps from the chord tones, alternating patterns;
   - drums by energy;
   - an impact on every hard hit;
   - a beat of silence before a stop-down;
   - the motif where the plan says.

   The validators refuse an out-of-key note, an out-of-range part, a note past the end, parallels, and the
   same bar more than four times running. Nothing renders until they pass. The `.mid` is written for any DAW.
4. **The palette** (`assets/music-instruments.json`):
   - **Allowed:** synth, piano, bell, percussion and ambient. Free and owner-licensed instruments sound
     professional there.
   - **Blocked unless the owner overrides with a reason:** exposed solo strings, winds, guitars, vocals and
     orchestral realism. These give a sample mockup away.
   - **Instrument licences** come from the same file. An unknown instrument is refused until its licence is
     read and added.
   - **Sonatina Symphonic Orchestra** (and Virtual Playing Orchestra, built on it) cannot advertise anything
     but the work itself, so neither renders client ads.
   - **Kits and loops:** an Ocular sound is never "the main element of a music track", and a Ghosthack kit's
     MIDI or stems are never the delivered cue.
   - **Layering in key.** A Felt piano ping in the bed's confirmed key can sit under a hit as its stab
     (`sfx_conform.py library search "piano ping" --key <root>`), and a Pendulum loop at the bed's tempo
     (`--bpm 90|120`) can pulse under a section. Both are support under the music, never its main element.
5. **The render.** `composer.py render <job> --backend numpy|fluidsynth|sfizz` renders a 48 kHz mix and a stem
   per part, and times the render.
   - The built-in synths need nothing installed.
   - FluidSynth renders SF2 offline; on the VM it comes from apt.
   - `sfizz_render` renders SFZ at 48 kHz.
   - Commercial plugins (Kontakt, Spitfire) loading headless is untested.
6. **Gate A.** `composer.py gate-a <wav> --refs <library cues for the mood>` flags a cue outside the 5th–95th
   percentile of the references. It measures loudness, true peak, mono loss, high-band flux and verbatim
   repeats. The research wants 20–50 references per mood; a 14-track library cannot give that, and the
   report says so.

### D. Generated beds, on trial

1. **The record.** `composer.py generated record <job> --file … --vendor … --plan … --prompt … --terms-url …
   --terms-file … --use temp|ship` writes `<file>.gen.json` and the manifest row: tool, version, plan and
   region. It is **refused**:
   - without consent dated before the generation;
   - for shipping, from a vendor that is not whitelisted, on a blocked plan, or without the terms snapshot;
   - for a prompt that names an artist, quotes a title or a lyric, or asks for a style "of" or "like" a work
     (the GEMA outputs came from title and lyric prompts);
   - for stems separated from generated stereo.

   Whitelisted: ElevenLabs paid plans and Stable Audio. Held: Adobe Firefly and Google Lyria. Excluded: Suno,
   Udio, MiniMax and Soundraw. Open weights: temp only until tested on the owner's hardware.
2. **AI vocals, case by case.** `composer.py vocals record <job> --file … --lyrics-file … --lyrics-by … --voice …
   --disclosure … --no-soundalike` needs:
   - the lyrics as written, by a named person;
   - a voice described without any artist;
   - the no-soundalike statement;
   - the disclosure;
   - the client's consent to AI vocals.

   Vocals are the main thing listeners use to spot generated music (Figueiredo et al., NeurIPS 2025).
3. **The blind bake-off (K5, K7).** `composer.py bakeoff init <job> --library … --candidate … --subject
   vendor:elevenlabs|route1:score|motif:<brand> [--vo …] [--picture …]` cuts level-matched, half-overlapping
   excerpts under the VO and the picture. Each pair is labelled a/b at random, and one hidden duplicate checks
   each listener's consistency. Listeners record their picks with `bakeoff record`; `bakeoff result` pools
   them:
   - 30+ trials from 3+ listeners who are not the composer;
   - the composer's own picks, and a session that fails the duplicate, are dropped;
   - **fail** when the candidate is significantly worse (10 of 30 or fewer);
   - **pass** at 11 or more;
   - **prefer** at 20 or more.

   A pass counts for the quarter. Advertising professionals are swayed by where they think music came from;
   consumers are not (Anglada-Tort 2020). So the owner's unblinded listen is never the gate.

### In Resolve: Fairlight

`composer.py console <job> [--fairlight-preset "<name>"]` writes `07-edit/resolve-production-console.compose.py`.
Send it through the Resolve MCP's `run_script`, or paste it into the console.

- **Tracks:**
  - on A5, the original track's segments, as `music_fit.py rebuild` places them. Never a render;
  - the composed layer on A6;
  - every stem on its own **named stereo track**, **disabled** so the mix is never doubled; switch one on in
    Fairlight to rebalance.
  - Not placed: the alt mix (`06-music/family/<stem>.full.wav`) and the length family
    (`06-music/family/<stem>.<L>s.wav`). Both are made in Python, so both are previews. Rebuild each in Resolve
    from the original; `07-edit/music/FAMILY.json` lists each length's plan.
- **Clip colours by origin:** library Blue, composed Purple, generated Orange, stems Navy.
- **Markers:** each spotting cue as a duration marker. Each hard hit as a Green marker whose custom data
  carries its window in milliseconds.
- **No timeline per length** any more: the family's lengths are previews (2026-11-05). Make each
  length's timeline in Resolve and rebuild its music there.
- **The Fairlight preset (optional):** one the owner saved (busses, a Ducker on the music keyed from
  dialogue, a limiter). A preset can change the track layout, so it is off by default. The API cannot create
  one, so the owner saves it once in Fairlight. Since v2.49 it is **applied by computer control** in Fairlight,
  not by the script (house rule 8, § What runs through the API); the script may read `GetFairlightPresets()` to
  say whether it exists.
- **v2.49 (rules 8 and 9):** the script's track layout, names, colours and markers are timeline setup and
  markers, which the API may still do. Every level, EQ, ducking or effect move, and every SFX placement, is
  made in Fairlight by computer control and checked by listening.
- **Safety:** nothing is placed over a clip and nothing is deleted; everything is read back.
- **Not in Resolve:** Resolve has no MIDI instruments, so the `.mid` files are for a DAW; Fairlight gets
  rendered stems.

### The check at export

`approve export` runs `composer.py check` after the music fit. Rules refuse; measures warn (C5).

**Refused:**

- the paperwork incomplete when anything is composed or generated;
- a composed file changed after its render;
- an instrument not cleared for paid ads;
- a part outside the palette;
- a layer on an unconfirmed key, or a motif with no record of the owner's edit or of its melody check;
- a score whose plan changed, or that failed its validators, or whose route has no bake-off this quarter;
- for generated audio:
  - a vendor off the whitelist, a missing or changed terms snapshot, or no consent before the generation;
  - a prompt naming a work or an artist, or separated stems;
  - AI vocals without their record;
  - no passing bake-off for the vendor;
- a temp-only track in the mix;
- a missing or stale element sheet.

**Warned:**

- a hit's measured impact outside its window;
- a hero motif not yet blind-tested;
- the accent budget;
- a missing length or alt mix;
- a score whose authorship rests on the agent's plan;
- the disclosure lines.

**What it cannot do: hear.** The blind bake-off is where the music is judged, and `approve export --quote` is
where the owner signs the listening pass.

## Pick the BPM up, then mark the beats

Know the bed's **BPM** before you fine-cut: one beat = 60 / BPM seconds (120 BPM → a beat every 0.5 s, a
bar every 2 s). `music_fit.py map` measures it, as the median over 8-beat spans, so a drifting track reads
true.

## Action points — the edit carries the sub-second timing

Adopted 2026-10-26 (the intent and emotion proposal of 2026-10-26 [studio history], package B). Three models
judging separately agreed that image-to-video models ignore sub-second timing in a prompt, so the prompt
writes the order of events (`motion-craft.md` §6b) and the edit makes the intent land:

- **Enter at the onset.** Cut in a couple of frames before the action starts moving, after the lead-in
  has settled. The settle at the head of a generated clip is never in the cut.
- **Cut on the commit.** Leave the shot a few frames after its fastest moment, into its consequence
  (the sugar in the bin, the face). Leave before the settle completes; a drama may hold the after.
- **Ramp only the burst, and only if it is slow.** 115–150 % from the onset to the contact, back to
  100 % for the settle. ⛔ Never speed up a whole clip: it kills the weight and exposes the interpolation.
- **Lay the foley on the hit frame.** The contact (the knock, the tap, the lump landing) gets a hard,
  slightly exaggerated hit, with the bed dipped for 1–3 frames before it.

`python3 scripts/action_points.py CLIP.mp4 --edl markers.edl` measures the clip's motion and proposes
the four points (in, commit/cut, hit, settle) and the ramp, and writes them as timeline markers Resolve
imports (Timeline → Import → Timeline Markers from EDL). It runs outside Resolve, so it is not a third
Resolve script. It proposes; the editor checks it against the contact sheet and moves a point by hand
where the motion it measured is the camera, or another person, and not the action.

### The ramp — planned, capped, checked (house rule C4, 2026-10-26)

Author, 2026-10-26: *"Does the plugin know when and when not to use speedramps and related cuts and
transitions?"* — then, after the council (the titles and motion proposal of 2026-10-26 [studio history]): *"Keep
burst speed-up + cap"*. Two of the three models kept the burst above; the third would ramp generated footage
down only. The ruling:

- **A ramp is planned on the clip, not found in the edit:** `ramp: kind=slow|burst, speed=<%>,
  trigger=<s in the clip>, reveal=<what the slow motion shows>, sfx=<the cue>` in the clip prompt, and
  `cut_in=` / `cut_out=` (seconds in the cut) once it is cut. `prompt_lint.py` refuses a burst outside
  115–150 %, a slow-down outside 20–90 %, a slow-down with no `reveal=` (a ramp is a shot that only exists
  at that speed — `move-catalogue.md` §24), a ramp with no cue, and any ramp on a speaking or reacting
  person (slow motion reads as contrived on an endorser — Yin et al. 2021 — and makes an act look more
  intentional — Caruso, Burns & Converse 2016).
- **The cap: one per 20 s of film and no more than 2 per video, whichever is lower** (the title card's
  `ramps`). Two ramps closer than 20 s apart count as two in one window. Checked at picture lock
  (`motion_qa.py check`).
- **Every slow-down passes the warp check on the cut as rendered:** `motion_qa.py warp <the cut> --at
  <cut_in>-<cut_out> --shot <S> --job <job>` predicts each frame of the ramp from the one before and
  measures where the prediction tears, against the footage around the ramp; it also catches a frame-repeat
  retime (a stutter: set Retime Process to Optical Flow, Speed Warp on Studio). Frame blending's ghosting
  is not measured — look at the strip it writes. Lock refuses a slow-down without a passing report on the
  newest cut.
- **It is heard as much as seen.** The clip's own audio is muted under the ramp and the cue carries it — a
  slow-down's whoosh-down with its low point on the trigger, a burst's hit on the contact. The cues are on the
  machine: Ocular's **Shift** pack is built for speed ramps and slow motion
  (`library search "slow motion ramp" --paid-ads-only`).
  `sfx_conform.py joins` lists each ramp with its mute window and cue and puts RAMP IN / RAMP OUT markers
  in its EDL.
- **A real-footage shot slowed at one constant speed keeps its own sound at real-time speed**
  [PRACTITIONER · course notes]: unlink it, lay the take's sound at 100 % (a kept take, §7d), fade it in and out,
  and overlap the next bed so the track never goes empty (room tone counts, §7e; `export_qc.py` already
  fails true silence). Under a planned ramp the bullet above still holds: the clip's own audio is muted and
  the cue carries it. ⛔ This settles the sound only. Whether a whole slowed clip of real footage counts
  against the cap and needs `reveal=` is open (Appendix P, P15), and nothing here exempts it.
- **Lifted per job by a switch, never by default.** Nothing above exempts a whole-clip constant conform or a
  shallow ease inside a planned whip unless the job's CHECKPOINT carries the `speed-conform` switch
  (`assets/project-switches.json`): then `conform=<speed>%` (or `conform=<src fps>/<timeline fps>`) on a shot,
  and `ease=<min>%` (85 or more) on a shot with `join: whip`, are not ramps and need no `reveal=`; the
  frame-repeat floor still holds, and any other speed change inside a clip is still a ramp (v2.48.0, switch
  `speed-conform`). A burst's `trigger=` is a time in the clip unless the job carries the `music-led` switch:
  then a burst may be cued to a sound in the song, `trigger=song@<s>`, and it still counts against the cap
  (v2.48.0, switch `music-led`).
- **No title spans a ramp** (`title_card.py titles`).
- **Slow motion nobody asked for** — a model slowing a clip unasked (§24's "Without this the model ramps
  everywhere") — is noted, not refused: `motion_qa.py check` sets each clip's speed against the other
  clips the same model made for the job and names one far slower whose prompt plans no slow-down, and it
  names a clip whose frames repeat. Look at it at full speed; retake it or conform it faster. It also warns
  on any clip slowed below timeline fps ÷ source fps (a 60 fps source on a 24 fps timeline: 40 %), where
  frames start to repeat.

## This skill ships exactly TWO Resolve scripts — don't add a third

Everything that runs inside Resolve lives in one of two files: `scripts/render-mp4.py` (the
render/Deliver step, see "Export" below) and `scripts/resolve-production-console.py` (everything else —
the V2 b-roll track, the A1–A6 lanes, beat markers, the timeline dump, and any future
production/editing-setup automation). New Resolve capability gets added as a **CONFIG toggle inside
`resolve-production-console.py`**, not as a new standalone file — that script's own docstring says so.

**Both run two ways, unchanged** (2026-09-14): sent as the `run_script` script of the MCP server that
ships inside Resolve Studio 21.1 (§ "Automating DaVinci Resolve via MCP" below) — where there is no
`os` and no `open`, so they hand data back in `result` — or pasted into Workspace ▸ Console ▸ Py3 on
the editor's machine. `scripts/test_console_scripts.py` executes both, both ways, against a fake
Resolve. This keeps "which script runs" a two-item answer forever instead of a growing pile of one-offs.

## Beat markers in Resolve

1. **Sparse markers from the real track (best).** `scripts/detect_beats.py` maps the chosen file with
   `music_fit.py`'s analysis (no librosa needed) and fills the `MARKERS` list inside a copy of
   `resolve-production-console.py`: Red "Phrase" on each phrase start, Blue "Bar" on the other downbeats.
   It never marks every beat. A marker on every beat invites cutting to the music, and the measured ads do
   not (§ Music to picture).
   ```
   python3 scripts/detect_beats.py 06-music/chosen-track.mp3 --project <that dir> --format vertical-1080 --offset-seconds 3.0
   # --format / --fps = the TIMELINE's frame rate. No default: markers are frames, and the old default of 30 drifted every marker on a 24 fps cut
   # --offset-seconds = how far into the TIMELINE the music actually starts (e.g. after a 3s hook)
   # writes 07-edit/resolve-production-console.py with MARKERS populated
   ```
   Send the resulting `07-edit/resolve-production-console.py` through the Resolve MCP's `run_script`
   (or paste it into Workspace ▸ Console ▸ Py3) with the target timeline open. Once there is a hit list,
   `music_fit.py rebuild` writes the better copy (`resolve-production-console.music.py`): the original
   track's segments on A5, and markers on the phrases, the must-hits, the nudges, each seam and the end fade.
   The crossfades and the fade are then made in Fairlight by computer control. `ENSURE_BROLL_TRACK` is on by default in
   the beat copy, so the V2 track (see "Track structure" above) gets created in the same step.
   ⛔ Marker frames count from the timeline's **first** frame — measured 2026-09-14 on Studio 21.1.0.14
   through an OTIO export — so never add `GetStartFrame()`; and `AddMarker` returns True even for a frame
   an hour past the end, which is why the script reads every marker back. A clip's `recordFrame` in
   `AppendToTimeline` is the opposite: absolute, so the music copy adds `GetStartFrame()` there.
2. **Tap the beats live (fallback).** On the **Edit** page, park the playhead at the music start, play,
   and press **M** on each downbeat to drop a **timeline marker**. Do it at reduced speed (`J`/`L`) for
   tighter placement.
3. **Compute markers from BPM (fallback, steady-grid only).** `build_fcpxml.py --bpm` does this —
   fine for a rough-cut scaffold, but it's a perfectly even grid, not the track's real beats; prefer
   `detect_beats.py` once you have the actual chosen file.

⚠️ **SUPERSEDES IN PLACE** (2026-10-26) — previously: "Downbeats land as Red markers, other beats as Blue",
with librosa required. Every beat as a marker pointed the edit at the music; the house rule is the
opposite direction.

Turn on **Snapping (N)** so edits click to the markers.

## Retention editing — current practice, tagged honestly

The pacing curve and cut-on-action are the durable layer (`craft-cheatsheet.md`). The 2026 practice
layer, researched and tiered per `research-quality.md` — note how much of the folklore did NOT
verify:

- **Every second is auditable.** The strongest named data: a top Shorts creator targets ~34s,
  ≥90% retention to travel, and measured cutting ONE weak final second raising retention 83→88%
  [PRIMARY · named creator interview · checked 2026-08-28]. The unit of retention editing is the
  individual second, not the vibe — which is exactly what the beat-by-beat script and selects pass
  already produce.
- **The hyper-cut era has a confirmed counter-current.** The style's own inventor publicly halved
  his cut rate (38→23 cuts/min) and reported growth; named editors corroborate audiences tiring of
  "energy energy energy" [SECONDARY · checked 2026-08-28]. Consequence: pace by *information and
  emotion*, not by a cuts-per-second quota.
- **No verified cuts-per-10-seconds norm for vertical exists.** Every specific number in circulation
  traces to unattributed content-mill copy [UNVERIFIED]. Do not put one in a client deliverable.
- **"Hold rate," loop-editing-for-rewatch, and fixed pattern-interrupt cadences are industry
  folklore** — no platform or named-practitioner confirmation found [UNVERIFIED]. Rewatch itself is
  real (the same creator's best videos exceed 100% retention via rewatches); the *engineered
  last-frame-matches-first trick* is the unverified part.
- **Fix dead air at the script, not in the trim.** The verified practitioner move replaces filler
  lines at writing time rather than surgically shaving pauses in post — which is `script-craft.md`'s
  job, and cheaper.

## Resolve at volume — efficiency that's actually confirmed

- **The Cut page is vendor-positioned for exactly this workload** (fast-turnaround commercials,
  one-click live trims, Speed Editor hardware) [PRIMARY vendor · practitioner adoption UNVERIFIED].
  Try it for Mode B assembly; the Edit page remains home for the finish.
- **Power Bins** = cross-project media (the brand's music beds, room-tone loops, approved pack
  assets, the S0B library) — load once, available in every project [SECONDARY, convergent].
- **Adjustment clips** = the per-model normalisation and the creative grade applied over a span,
  trimmed to range, savable as presets — the mechanism for one-grade-over-everything at batch scale
  [SECONDARY, fetch-confirmed]. One trimmed to span a cut is also where a join effect that has to see
  both shots goes (§ Applying transitions).
- **Smart Reframe (Studio) auto-reframes 16:9↔9:16 with subject tracking — with hard limits:** works
  only on a timeline of individual clips (not a flattened export), and **titles/graphics are not
  reframed — burnt-in text breaks**. Which is independent confirmation of this skill's own rule:
  captions burn per format, never before the fork. Workflow: duplicate the timeline, change ITS
  resolution, reframe, manually nudge misses [SECONDARY, fetch-confirmed · checked 2026-08-28].
- **Two shapes from a real shoot: cut the second on its own timeline from the locked master.** Lock the
  first shape, duplicate its timeline, change the copy's resolution, reframe (Smart Reframe or by hand) and
  re-cut where the new shape needs it. Never crop it at export. This works only if the shoot recorded the
  full sensor with both frame guides on (`delivery-format.md` §1–§2).
- **Stabilise real handheld on a copy, so the untouched original stays free for the vertical reframe**
  [PRACTITIONER · course notes]. The course duplicates and nests the clip and stabilises the nest. In Resolve,
  stabilise the clip on its own timeline (Edit page Inspector › Stabilization) or a compound clip of it.
  The setting belongs to the timeline clip, so it is copied when the timeline is duplicated: on the
  vertical copy, reset it and stabilise again after the reframe. Keep the smoothing low, and lower still
  when hands fill the frame. The course's values (about 15 %, 7 % as the middle step, 2 % or none when
  hands are large) are on its own editor's scale and do not map onto Resolve's stabiliser. No Resolve
  value follows from them, so set it by eye. The course also says the camera's own digital stabilisation
  is not available when shooting open gate or raw.
- **Text-based editing** (cut by transcript) exists in current Resolve — promising for talking
  content, limitations unverified; on a locked-script client the transcript is the script, which
  makes it safer than for most [UNVERIFIED — verify hands-on before relying].
- **The v20 AI layer — most of it is for footage this skill does not shoot.** Resolve 20 ships an
  automation tier (IntelliScript, IntelliCut, Multicam SmartSwitch, Dialogue Matcher, Audio
  Assistant, Magic Mask v2, Depth Map, Voice Convert, SuperScale, Animated Subtitles, Detect Music
  Beats…) presented as a feature catalogue with a **"review and fine-tune" step attached to every
  one of them** [SECONDARY · Dovale, *Mastering DaVinci Resolve 20* — via a local extraction, read
  2026-08-29]. Triaged against this pipeline: **IntelliCut, SmartSwitch and Dialogue Matcher have no
  work to do here** — they split silences and speakers out of long talking-head takes, cut multicam
  by active speaker, and conform location audio, none of which exists when every clip is generated
  to a locked line. **Detect Music Beats** draws an overlay, not markers, and the API cannot read it: it is the cross-check
  for `music_fit.py map`, not a replacement (§ Music to picture). The **AI Music Editor** (fits a track to
  a length in the UI) is likewise UI-only; `music_fit.py fit` does the same against the hit list.
  **Audio Assistant's one-click mix fights the sound-design sandwich below** — if you run it, run it
  *before* the sandwich, never over it. And **SuperScale is contraindicated on this account**: the
  standing rule is generate at exactly 1080p, not generate small and upscale.

**A current Resolve-20 book corroborates two of those bullets and is silent on three.** A published
end-to-end manual on v20 [SECONDARY · Dovale, *Mastering DaVinci Resolve 20* — via a local
extraction, read 2026-08-29] positions the **Cut page** exactly as the vendor does — social, vlog,
news and rough-cut work — and names the two mechanisms that actually buy the speed: **Source Tape**
(every media-pool clip concatenated into one scrubbable tape, so takes get marked in a continuous
scan instead of opened one at a time) and the **dual timeline** (whole-project overview above,
working detail below). It also confirms **adjustment clips**, and adds a distinction this file did
not carry: an *adjustment clip* reaches **down** to everything beneath it for its span, while
*effects layers* stack treatments across tracks so they **interact** — the first is the per-model
normalisation and the batch grade, the second is anything composited. It stays SECONDARY rather than
PRIMARY on purpose: the book is self-published, restates Blackmagic's own framing for most of its
benefit claims, and its own extraction flags machine-paraphrase errors in tool names. It
corroborates; it does not settle. And note the silence — **Power Bins, Smart Reframe and text-based
editing appear nowhere in it**, so none of those three tags move.

## Playback and render performance — configure the machine once, not per project

Resolve is GPU- and data-bound, and playback performance is a **configuration discipline before it
is a hardware question** [PRIMARY · Dovale, *Mastering DaVinci Resolve 20* — via a local extraction,
read 2026-08-29]. This file carried nothing on it, which is a real gap at volume — a stuttering
timeline does not merely cost minutes, it **hides the thing you are trying to judge**: a retime, a
lipsync A/B or a caption pass reviewed through dropped frames gets approved wrong. The standing
setup:

- **Generate optimized/proxy media before heavy editing** and work at reduced timeline resolution;
  export full resolution at the end. Generated clips are short and 1080p, so this bites hardest when
  licensed archive or 4K client material is in the cut (Mode B, `modes/ugc-volume.md` §6.2).
- **Smart Render Cache on — and cache heavy retimes deliberately.** An uncached speed ramp stutters,
  and the stutter reads as a bad retime, so the note goes back to generation instead of to the cache.
- **GPU acceleration on** (CUDA/Metal), **cache on SSD/NVMe**, never on the spinning archive drive.
- **Stated floors: ≥4 GB VRAM, 16 GB RAM minimum, 32 GB for 4K.** These are one 2025 book's minimums
  for v20 — a floor to clear, not a spec to buy to, and readers on 18/19 are no better off.
- **Treat playback lag as a configuration bug until proven otherwise.** Before blaming a clip, a
  model or the software, check proxies, cache and GPU — in that order.

## Cut on action and looks — let the beat land a few hits

- **Cut on action and on looks.** In 38 measured ads the outgoing shot carries motion at 36 % of cuts
  and a look at 11 %, and 45 % of cuts land on an action already under way (`sequence-grammar.md` §2c).
- **The beat is for a few hits, not every cut.** Real ads cut on a beat no more often than chance
  (31 % of cuts against 32 %); 2 of 37 clearly cut on it (`specifics-catalogue.md` §16.6). Put the
  reveal, the product landing or the button on a hit; let the rest follow the action. Where a passage
  does lock to the music (a chase, a dance), cut slightly *before* the beat to build and slightly
  *after* to release — exactly on every beat feels stiff (see Pearlman in `craft-cheatsheet.md`).
- **Build the cut so it survives a music change.** Commercial editors split between cutting to music
  and cutting to an internal rhythm, and tracks get swapped late (lab record lab-00006 (not shipped)
  in the repository, P3).
- **The measured pacing curve:** open on a shot a little longer than average (median 2.8 s), run at
  about 1.8 s a shot, put the shortest shots in the middle (median position 55 % of the running time),
  and hold the end card about 4 s — never less than its reading time (`sequence-grammar.md` §2c, item 11).

⚠️ **SUPERSEDES IN PLACE** (2026-10-04) — previously: "Big cuts (scene → scene) land on the downbeat; small accents (a B-roll flash, a reaction) can land on off-beats." and "open ~4–5s, tighten to 2–3s, quicken at the turn, then a 3s hold on the button". Neither was measured; 38 real ads cut at chance against the beat and open at about 2.8 s (`specifics-catalogue.md` §16).

## Track structure — b-roll lives on its own video track (V2)

**Standing rule, every project:** dialogue/A-roll clips go on **V1**; **all b-roll goes on a
separate video track, V2**, stacked above it — never intercut directly into V1 alongside the
dialogue clips. Audio mirrors it: **A1–A2 dialogue/VO · A3 ambience beds · A4 foley/SFX · A5–A6
music** — fixed lanes, every project, so a mix can be read at a glance and the sound-design
sandwich (below) is visible as tracks, not buried in a pile. And the sandwich's corollary as a
rule: **no clip plays over silence** — every moment carries at least the room-tone bed under it. Reasons this pays for itself immediately:

- **Non-destructive re-cutting.** A b-roll clip on V2 can be trimmed, slid, replaced, or deleted
  without rippling or re-timing the dialogue cut underneath it — the VO/lipsync timing on V1 never
  moves by accident.
- **Toggle for a quick A/B.** Solo/mute the V2 track to instantly compare "b-roll covering the line"
  vs. "straight cut on the dialogue clip" without touching either track's edit.
- **Faster QA.** The per-shot QA gate (`pm-workflow.md`) can review V1 (performance/lipsync) and V2
  (coverage/continuity) as two separate passes instead of one tangled track.
- **Matches how the footage is generated.** B-roll and dialogue clips already come from different
  model roles and different folders (`03-clips/` vs `04-broll/`, see `pm-workflow.md`) — keeping them
  on separate tracks continues that same separation into the edit instead of collapsing it.

In Resolve: create the second video track (Timeline ▸ Track ▸ Add Track ▸ Video, or right-click the
track header) before importing b-roll, and drop b-roll clips there, positioned to cover the V1
dialogue clip(s) they're meant to accompany. Same convention in FCP (a second video lane/connected
clip above the primary storyline). This applies to the real production timeline — however it's
assembled: by hand, or natively via the Resolve MCP (`AddTrack("video")` then place b-roll items on
it, rather than appending them into the same track as the dialogue clips).

**Known scope note — `build_fcpxml.py`:** the interchange script lays all clips (dialogue *and*
b-roll) end-to-end on one spine — that's fine for its job (a rough-cut scaffold that just needs the
overall order/length right before hand-off), but it does **not** yet split them onto separate
tracks/lanes. Treat its output as a starting point only: once imported, move the b-roll clips up to
a V2 track before doing real edit work, or update the script to emit b-roll as lane-1 connected
clips if this becomes a recurring manual step worth automating.

### Which trim — and why ripple is the dangerous one here

The four trims have deterministic and different effects on their neighbours [PRIMARY · Dovale,
*Mastering DaVinci Resolve 20* — via a local extraction, read 2026-08-29], and on this timeline the
choice is not a matter of taste — it decides whether the lipsync survives. Pick by **what must stay
fixed**:

| Trim | Changes | Leaves fixed | Use here |
|---|---|---|---|
| **Ripple** | a clip's edge, shifting everything downstream | nothing after the edit | ⚠ **The hazard.** On V1 it moves every later clip relative to the VO *and* the beat markers — safe only before the VO is placed, or with everything deliberately re-synced afterwards |
| **Roll** | where the cut falls between two clips | total duration, downstream positions | Re-framing a join without touching the music grid — the default fix on a locked cut |
| **Slip** | which frames of a clip play | the clip's position and duration | The lipsync technique on *silent* clips — and forbidden on baked-audio clips (see the slip table under **Lipsync** below) |
| **Slide** | a clip's position | total duration; neighbours absorb it | Moving a B-roll cover on V2 without opening a gap |

The V1/V2 split is what makes this survivable: a **roll or slide on V2 cannot disturb the dialogue
cut underneath it**, which is the same reason b-roll lives on its own track in the first place.

## Transitions — the grammar, the library, and the plan

Three layers, in order: **what a transition means** (the grammar), **what is installed** (the
library), and **when it gets decided** (pre-production, not the edit). A transition chosen at the
cut point is decoration; a transition planned at the storyboard is language.

### The grammar — what each choice signals

Hard cut is the neutral, unmarked default; everything else is a statement and must be **motivated**
— by energy, by a location/time change, or by a visual correspondence. Unmotivated is what reads as
amateur, in every era.

| Transition | Signals | Motivated when | Beware |
|---|---|---|---|
| **Hard cut** | nothing — invisible | always; the default | none. When in doubt, cut |
| **J-cut / L-cut** (audio leads/trails) | continuity, flow | dialogue and VO bridges — the ear carries the join the eye doesn't notice | on baked-audio clips the audio cannot slip: build the overlap from the *other* clip's track |
| **Punch-in / jump cut** | compression, candour | talking content — removing dead air while staying on the speaker | at volume it becomes the template tell; vary the punch size |
| **Match cut** | wit, connection | a real visual/shape/action correspondence exists (plan it at the storyboard — `craft-cheatsheet.md`) | faking the correspondence reads as a gimmick |
| **Whip pan / smooth-zoom (pack)** | energy, cause→effect | a beat-matched energy rise, a location jump; on real footage, both sides shot for it (§ The hidden cut) | the most overused pack asset; one per video is seasoning, five is a template |
| **Speed-ramp** | drama, emphasis | into or out of a hero moment | planned on the clip (`ramp:`), one per 20 s and 2 per video at most; a burst only from onset to contact (115–150 %), a slow-down only with its reveal and a passing warp check; never on a speaking or reacting person (§ The ramp) |
| **Dissolve** | time passing, mood shift | scene-to-scene or the montage's breath | needs real handles both sides — ⛔ and a dialogue clip may NOT be extended to supply them (`shot-handoff.md` §2); plan the dissolve onto a silent clip or an insert; never inside a continuous VO line |
| **Dip to black/white** | closure, chapter break | the end, or a deliberate act break | mid-story it tells the viewer "it's over" — and on a feed they'll take the exit |
| **Glitch / heavy warp (pack)** | style, tech register | the brand's register says so (Visual Bible) | strong flavour; it dates fast and it *is* the brand voice once used |

**Per-mode palette** (the Visual Bible may tighten further):
- **A · Narrative:** motivated cuts + J/L; a dissolve at scene shifts; one signature move per episode
  at most. No pack glitches.
- **B · UGC volume:** hard cuts + punch-ins are the native grammar; a whip/smooth-zoom on an energy
  beat, sparingly; **vary transition choices across the batch** — identical transitions across 12
  videos is batch-sameness (`realism-qa.md` §5). ⚠ **But varying the transition is not what makes a
  batch varied.** YouTube's inauthentic-content policy names the *template* itself, so a batch whose
  only difference is its wipes is still a template with different wipes
  (`discovery-and-search.md` §4c). Transition variety rides on top of argument, setting and
  presenter variety; it does not substitute for it. The corollary is freeing: on any single video,
  pick the transition that serves the cut and stop worrying about whether it is "the same as the
  last one".
- **C · Editorial:** cuts + dissolves for time; wipes only as a deliberate retro statement.
- **D · Repurpose:** inherit the source's palette; derivatives don't introduce new moves.

**⛔ The budget (house rule C5 of the titles-and-motion council, 2026-10-26 —
the titles and motion proposal of 2026-10-26 [studio history]; all three models).** The hard cut governs edited AI
footage. HyperFrames' rule that "one primary transition carries most seams" applies only inside a
HyperFrames composition (and to a brand film's one signature move), never to the cut. Checked at picture
lock from the timeline Resolve reports (`DUMP_TIMELINE_JSON` → `07-edit/timeline-dump.json`) and the
selected shots' prompts — `motion_qa.py check`, which `gate.py approve lock` runs:
- **at most 2 accent kinds per film** (the title card's `transitions.max_accents`; when the card lists
  `accents`, families or starred names from the inventory, only those) — an opening fade from black and
  the ending's dip are not accents;
- **a dip only at the end**, or at an act break the card names (`transitions.act_breaks`);
- **no transition beside a dialogue clip** — it eats handles a dialogue clip may not be extended to supply
  (`shot-handoff.md` §2); a Smooth Cut on a jump cut is the exception, checked by eye on a generated face;
- **whips, in the timeline and planned (`join: whip`), 2 a film at most** — one is seasoning;
- a clip left at an opacity under 100 % outside a planned transition is warned: a line-up opacity used to
  align two clips goes back to 100 % before export;
- a light leak stays out of ads and launches (`product-video.md` §2.5) unless the job's CHECKPOINT carries the
  `light-leak` switch (`assets/project-switches.json`): one leak hit on one cut, screen-blended and peaking on
  the transition, counted inside the accents above, never as a grade and never on every cut (v2.48.0, switch
  `light-leak`) — when and where: § Finishing looks;
- the same accent on two seams in a row is noted: it has become the film's grammar, which is right for a
  montage and wrong anywhere else.

**AI-footage notes:** cut on motion peaks, not rests — motion masks the clip seam. The morph-settle
head/tail (`ai-generation.md` guardrails) means pack transitions with heavy warp can *hide* an
imperfect join — legitimate, but it's concealer, not a system; if every join needs concealing, the
generation plan was wrong. And retiming asymmetry is real: **slow-down conceals AI artifacts,
speed-up exposes them** [SECONDARY · practitioner writeups · checked 2026-08-28] — which is why a burst is
confined to the onset-to-contact stretch at 115–150 % and a whole clip is never sped up (§ The ramp, owner
ruling C4). ⚠️ **SUPERSEDES IN PLACE** (2026-10-26) — the tables here previously said "on AI footage, ramp
**down**" without exception, which contradicted the burst rule in § action points; the owner kept the burst.

### From the SCRIPT to the cut — the inverse index

The table above is indexed by transition: *here is a whip pan, when is it motivated?* That is the
wrong way round at the desk. The question an editor actually has is **"this line is in front of me —
what does it ask for?"** So here is the same grammar keyed on what is in the script or the prompt.

⛔ **Read the signal in the writing, not the timeline.** If nothing in the script asks for a move,
the answer is a hard cut. That is not a fallback; it is the correct answer most of the time, and
reaching past it is how a 40-second ad acquires five transitions and no argument.

| What the script/prompt says | The cut | Why, and the trap |
|---|---|---|
| Nothing in particular — the next beat just starts | **Hard cut** | The unmarked default. `editing-storytelling.md` §1.1: the cut carries meaning only when everything else is already right |
| One speaker, and the line has dead air in it, or you need it 20% shorter | **Jump cut / punch-in** | Compression while staying on the face. ⛔ **Vary the punch size** — identical framings across a batch is the template tell (`realism-qa.md` §5). On generated footage a punch-in is a re-frame of the SAME clip, so it costs nothing and hides nothing |
| The line names a thing — a coil, a seam, a phone screen, a price | **Cut-in / insert** | The cheapest shot in the film and the one that buys the most. ⛔ Every insert declares a FUNCTION (`shot-handoff.md`): what it *proves*. An insert with no function is a stock shot with a job title |
| A VO line runs over something other than its speaker | **J-cut or L-cut** | The ear carries the join. ⛔ **On baked-audio clips the audio cannot slip** — build the overlap from the *other* clip's track, or generate that shot silent |
| Two things happening at once — "while she sleeps, he's still scrolling" | **Cross-cut** | ⚠ **Usually the wrong call at 35–55s.** It needs two locations generated and inter-cut, so it roughly doubles the shot count for a structural idea the runtime cannot pay off. Prefer one location and a line that implies the other |
| A reaction, an aside, a joke's tag | **Cutaway** | Also the release valve after a comedy turn — and the ~1s the resolution needs is a place to put it (`comedy-craft.md` §5) |
| Two images genuinely rhyme — a shape, a movement, a sound | **Match cut** | ⛔ **Plan it at the storyboard or you will not get it.** Both frames have to be *generated to match*; you cannot discover a match cut in AI footage the way you can in rushes. Faking the correspondence reads as a gimmick |
| The tone breaks hard — the joke lands, the problem arrives | **Smash cut** | ⛔ **The one AI footage fights.** A smash cut wants the incoming clip hot on frame 1, and a generated clip opens on a ~0.4s morph-settle (`ai-generation.md` guardrails). Cut into the clip past the settle, or generate that shot with the action already running |
| "Weeks later", "every night for a month" | **Dissolve** or a **montage** | A dissolve needs real handles both sides — ⛔ never inside a continuous VO line, and a dialogue clip may not be extended to supply them (`shot-handoff.md` §2). A montage at 40 seconds costs a third of the runtime: it had better BE the argument, not decorate it |
| An energy rise the music is already making | **Whip pan / smooth-zoom** | One per video is seasoning. Beat-matched or it is noise |
| Into or out of a hero moment | **Speed-ramp** | ⛔ **Planned on the clip, capped, checked** (§ The ramp, house rule C4): a burst only from onset to contact at 115–150 %, never a whole clip; a slow-down names what it reveals and passes `motion_qa.py warp`. One per 20 s, 2 per video at most |
| The end | **Dip to black** | ⛔ Only the end. Mid-story it tells a feed viewer the video is over, and they will take the exit |

**The three questions that resolve most disputes at the timeline**, in order:

1. **What is the emotional beat here?** Murch's first and heaviest criterion — 51% of the weight,
   more than the other five combined (`editing-storytelling.md` §1.1). A cut that serves continuity
   and betrays the beat is the wrong cut.
2. **Is the move motivated by something in the script, or by the timeline being boring?** The second
   is the honest reason most transitions get added, and it is never sufficient.
3. **Can this shot actually give me that cut?** Handles, settle, baked audio, motion peak. On
   generated footage this question has teeth that it does not have with rushes — see the mechanics
   below.

⚠ **What this table cannot tell you.** The names are craft vocabulary, not findings: no measured
work establishes that a smash cut outperforms a hard cut anywhere, and the popular listicles that
enumerate them cite nothing. What *is* evidenced is narrow and already in the skill — cut on action
rather than on space (`motion-craft.md`), and the expectation mechanism in `editing-storytelling.md`
§1.4. Treat the table as a routing index for decisions you are already making, and do not let the
existence of eleven named cuts persuade you to use eleven.

### The techniques the grammar table does not name — and the one that matters most here

The table above and the inverse index cover the cuts a shot list plans. These are the ones an editor
reaches for **when the material will not do what the plan assumed** — which, on generated footage, is
most days. All craft doctrine unless marked; the AI-specific parts derive from this skill's own
measurements (the ~0.4 s morph-settle, the 57.6% usable yield, "handles have to be GENERATED").

#### 1. The hidden cut — the highest-value technique this file was missing

Two shots joined so the viewer reads **one continuous take**. Note this is a different thing from the
"invisible cut" in `editing-storytelling.md` §6, which is the name of a *school* (Hollywood
continuity). This is a specific move:

| Device | How it hides the join | On generated footage |
|---|---|---|
| **Whip pan** | Both shots blur past the cut; the eye has nothing to hold | The cheapest one, and the one a pack asset gives you. Generate the outgoing clip with a fast move at its tail and the incoming with one at its head |
| **Object wipe** | Something crosses frame — a hand, a doorway, a passing body — and you cut inside the black | ⛔ **Must be planned into the prompt.** You cannot discover a wipe in AI footage the way you can in rushes |
| **Match on black / into shadow** | Cut when the frame is briefly dark | Easiest to get: prompt a move into shadow, or a blink-to-black |
| **Speed blur** | Ramp into the cut so motion smears it | A slow-down across the join that passes the warp check, or a burst into it (115–150 %) — never a whole clip sped up; it counts against the ramp cap (§ The ramp) |
| **Sound-led** | Audio runs straight through; the picture change rides under it | Costs nothing, needs no generation, works every time. Start here |

**On real footage the whip is shot, not found** [PRACTITIONER · course notes]. Shoot both sides of the join at a
high frame rate with a shutter slow enough to blur: the course shoots 60 fps at 1/125, and a fast shutter
(1/1000–1/2000) kills the blur. End the outgoing shot and start the incoming one moving the same way, at
matching brightness. Sell the join with a directional blur along the move (Resolve FX Directional Blur, on
an adjustment clip across the cut, § Applying transitions) that rises from none to a peak on the cut and
falls back to none. The course keys its blur length 0 → 15 → 0 on its own editor's scale, at the angle of
that move (61° in its example). A 60 fps source on a 24 fps timeline is a mixed-rate timeline, which
`motion_qa.py check` warns on, so check the join frame by frame. A rotation join counts as a
whip. ⛔ The budget is unchanged: two whips a film at most, planned and in the timeline (C5, above). A card
that says whip is not proof of one: `motion_qa.py cut` (the joins report) gives each `join: whip`'s measured pan rate and
warns only below a `--whip-min` you pass, and there is no default threshold yet.

**A smooth zoom on real footage joins two shots that already share a subject and a direction**, the same
condition as a match cut [PRACTITIONER · course notes]. Sell it with a lens distortion, on an adjustment clip
across the cut, that peaks on the cut and returns to none on either side: about 100 at the join on the
course editor's scale. Keep the corners full (§ Applying transitions). It counts as one accent kind under
the budget (C5, above).

**Why this belongs in an AI pipeline more than a live one.** A generated clip opens on a
morph-settle and its head and tail are the least stable frames it has. The hidden cut is what lets
you **cut away from the unstable part** rather than fixing it: you are not concealing a bad edit, you
are choosing to join where the material is strongest. But the honest line from the transitions
section holds — **if every join needs concealing, the generation plan was wrong**, and the answer is
a different shot list, not more whip pans.

#### 2. The sound bridge — the scene change you can afford

Sound from the next scene starts under the end of this one (or the reverse), carrying the viewer
across a location or time change. **Distinct from a J/L cut**, which lives inside one continuous
scene; a bridge crosses a *break*.

**This is the workhorse for a 35–55 s ad, because the alternatives are unavailable.** A dissolve
needs real handles both sides and a dialogue clip may not be extended to supply them
(`shot-handoff.md` §2); a dip to black mid-story tells a feed viewer it is over. A sound bridge needs
neither handles nor generation — just a room tone, a music phrase or an effect that starts two beats
early. It is the cheapest "this is a deliberate scene change, not a mistake" signal available.

#### 3. Elliptical editing — how a 40-second video holds three days

Time removed by omission rather than by a transition: hand reaches for the light → already asleep.
No dissolve, no title card, no "3 hours later". The viewer bridges it, and bridging it is the
pleasure.

**At this runtime it is the primary structural tool and it was not named anywhere in this skill.**
The whole reason a 35–55 s ad can carry a night, a morning and a verdict is that it shows three
moments and cuts the rest. Two rules that keep it readable: **change something visible across the
ellipsis** (light, wardrobe, position — the cue that time moved), and **do not ellipse the thing the
video is arguing**. Skipping the night is fine; skipping the moment the product does its work is
skipping the ad.

#### 4. Freeze frame and split screen — UGC vernacular, and useful here

Both absent from this skill and both native to the format. A **freeze frame** buys a beat for an
on-screen line without spending runtime on new footage — and on generated footage it is free, since a
held frame has no motion to go wrong. A **split screen** or side-by-side is the honest way to show a
comparison, and for a sleep brand it is the shape a before/after wants.
⛔ Both are claims the moment they carry a result: a split-screen before/after is a
**demonstration**, and `real-and-ai.md` §5's product-demonstration doctrine applies — the proof shot
is shot.

#### 5. The cheat cut — permission you will need

A deliberate continuity break the viewer does not notice: the hand is in a different position, the
light shifted, the mug moved. In live action it is a compromise. **On generated footage it is the
normal case** — two clips of the "same" scene never match exactly, and the choice is between a cheat
cut and a regeneration.

⛔ **The rule that keeps it honest: cheat continuity, never cheat the argument.** A mug that moves
between shots is invisible to a viewer watching the person. A *product* that changes between shots is
the thing they are looking at, and it reads instantly. `realism-qa.md` V12/V13 draws that line; this
is the editing-side statement of it.

#### 6. Eisenstein's first two, for completeness

`editing-storytelling.md` §2.2 covers tonal, overtonal and intellectual montage. The two it does not
name: **metric** (cutting on a fixed frame count regardless of content — which is exactly what
beat-matched cutting is, so this skill already does it under another name) and **rhythmic** (cut
length driven by the movement *inside* the frame). Naming them matters only so nobody thinks
"montage" means one thing.

---

### ⛔ The mechanics on generated footage — where the cut can actually go

The grammar above is right and it assumes a shot. **A generated clip is not a shot.** It has a
morph-settle head, and its energy peak lands wherever the model put it rather than where the beat
wants it — so "cut on motion peaks" is correct advice that is sometimes impossible to take.

**Measured on 12 real clips from a finished film, 2026-09-07** [PRIMARY · own measurement,
`clip_qa.py`]:

| What | Measured |
|---|---|
| Morph-settle head, before the picture leaves the start frame | **~0.4s** [PRIMARY · own testing, 2026-08-29] |
| Median energy-peak position | **73% of the clip** |
| Clips peaking in the **last 3%** — i.e. on their own last frame | **5 of 12** |
| ⛔ **Usable yield**: on-screen seconds ÷ generated seconds | **57.6%** — 38.9s from 67.6s |

**Three rules come out of that, in order of how much money they save.**

**1 · ⛔ Handles have to be GENERATED. They cannot be added afterwards.**
A clip generated to its on-screen length has its edit point on its own last frame, which is a butt
join, not a cut. There is no tail to cut out of, no room to trim the morph-settle off the head, and
no overlap for a J-cut or a dissolve. **Budget ~1.7× the on-screen length** on the measurement above,
per clip, and treat that as generation cost rather than waste — the alternative is an edit with no
choices in it. This is the single highest-leverage line in this section and it belongs in the shot
list, not the edit.

**2 · Cut just PAST the peak, not on it.** Motion masks the seam — that is why the grammar says cut
on peaks — but the gesture also has to have completed, which is rule 3. A few frames past the peak
gets both. `clip_qa.py --cut-plan` computes the in and out points for a whole film from what it has
already measured, and names the clips that have no tail to cut out of at all.

**3 · ⛔ Never cut mid-gesture. Jump place and time as freely as you like.**
This is the one that is usually stated backwards. **[PRIMARY · Magliano & Zacks, "The Impact of
Continuity Editing in Narrative Film on Event Segmentation", *Cognitive Science* 35(8), 2011 · 211
edits, N = 41 and 24 · verified 2026-09-07]** — **action-discontinuity** edits drove perceived event
boundaries (weight **0.96**, p < .001) while **spatial and temporal discontinuity produced a
*negative* effect** (−0.28, p = .004). Viewers do not track your geography; they track actions
starting and finishing. So the location jump you were worried about is free, and the cut two frames
early through a hand's movement is the one they feel.

**And the join that disappears entirely:** a cut placed on a **motion onset at a matching screen
position** [PRIMARY · Smith, "The Attentional Theory of Cinematic Continuity", *Projections* 6(1),
2012] — because a movement onset draws the eye to that screen location, and the incoming shot has
already put the thing there. On an object-led film this is nearly free: same object, same position
in frame, one gesture continuing across the join. It is the cheapest invisible transition available
and it costs nothing but planning it at the shot list.

⛔ **What this does NOT license.** A pack transition with heavy warp will hide a bad join — the
grammar table already says so, and calls it concealer rather than a system. The measurements above
are the reason: if the joins need concealing, the *generation* plan was wrong, and no amount of
whip-pan fixes a film whose every clip ends mid-gesture on its last frame.

### The installed library — packs are assets: inventory them, map them, place them by script (v2.45)

The edit machine carries packs; treat them like any other brand asset — inventoried, named, mapped to this skill's
kinds and **used**. What the owner has installed (Resolve 21.1.2, `GetEffectsList` read 2026-10-29, and their own list):
- **Fusion titles:** "Background Reveal", "Background Reveal Lower Third"; the **JTechWP** and **Video Editor Studio**
  title packs.
- **Transitions:** **Free Smooth Transitions**; the JTechWP and Video Editor Studio transition packs; Resolve's own Video
  Transitions (Cross Dissolve measured through the API; the rest by name).
- **Fusion effects and generators:** **Krokodove** (Bevel, Duplicate, Extrude, Generate, Pack, Rasterize, Spherize);
  Resolve's own Fusion effects (DVE, Digital Glitch, Paper Edge, Pen Stroke Arrow / Circle / Line, Video Call, Drone
  Overlay …); the **Video Editor Studio Free Starter Pack** (Animation In & Out, Continuous Zoom, Exclusion, Glass Effect,
  Icon Mask, Levitation, Phone Effect, Shadow Glow And Background).
- **OFX:** **MagicAnimate Free** (MrAlexTech), **CineDream** (Full Editor · Base Correction · Final Grading),
  **Higgsfield Color Match**, and every Resolve FX.

Packs this file listed before (VideoKits Essential Transitions, the DaVinciResolveTitles collections) are vendor-page
descriptions [PRIMARY · vendor pages, checked 2026-08-28]; buy or install one and it goes through the same scan.

**The scan — `resolve_library.py scan`.** Titles and transitions are **not** in `GetEffectsList`; only the template
folders, or the owner's list, know them. So the inventory merges what each source can say:
1. the console's `LIBRARY_SCAN` (`resolve_library.py console <job> --scan`): `GetEffectsList("video"/"audio")` — every
   Fusion, OFX and audio effect with its **category and id** (what `AddEffect` needs) — and, run in Workspace ▸ Console or
   `run_script_unsafe`, every template under the Fusion Templates folders (and inside every `.drfx`) with each macro's
   **published inputs**; `run_script` has no filesystem, so there it lists the effects and says where to run for the rest;
2. `--folder <…/Fusion/Templates>` once the owner grants that folder to this machine;
3. `--names <file>` — the owner's own list ("Titles/Background Reveal", "transition: Smooth Zoom In", or names under
   `# Titles` / `# Transitions` headings).
It writes `07-edit/resolve-library.json` for a job or `_studio/resolve-library.json` for the studio
(`assets/resolve-library.schema.json`): each item's type, pack, category and id, published inputs, the call that places
it, whether it is scriptable, and a **`kinds` map** — title/lower-third, super, hero, end-card, stat, price, logo-animate,
social · transition/dissolve, dip, smooth-cut, whip, push, zoom, wipe, light-leak, glitch (the families `motion_qa.py`
uses) · effect/animate-in-out, continuous-zoom, 3d-text, glow, glass, phone, glitch, pen-stroke, color-match, grade …
Starred items come first (and stay starred across re-scans); a dissolve's first choice is Resolve's own Cross Dissolve.

**Placing them — the console.** A plan of kinds (`07-edit/fx-plan.json`: `{"transitions": [{at_s, kind | type, duration}],
"effects": [{item, kind | name, inputs}]}`) → `resolve_library.py console <job> --plan …` resolves each kind to an
installed item and writes the console copy:
- `APPLY_TRANSITIONS` — `TimelineItem.AddTransition({type, category, position, alignment, duration})` on the outgoing
  clip at each cut; both neighbours are read back, and a transition that ate frames (no handle) is reported, not left.
- `APPLY_EFFECTS` — `TimelineItem.AddEffect(category, id)` on each named item (`cine:<id>` for a title); a Fusion
  effect's inputs are set through `Effect.GetFusionComp()` and read back; a re-run adds nothing twice.
- A **title template from a pack** goes in by name like the generated ones (`InsertFusionTitleIntoTimeline`), its words
  on its published inputs — prove each once with `FUSION_TITLE_SPIKE` before a job leans on it.

**⛔ What a script cannot do — the OFX line.** The 21.1.2 API has **no call that sets an OFX parameter.** An OFX effect
goes on with its defaults (or a preset saved in its own UI) and is flagged **MANUAL** in the plan and in the console's
report: **MagicAnimate**'s In / Mid / Out animation is picked by hand in the Inspector (and on text, one that lands
without overshoot — C2); **CineDream**'s look is set in its panel (the grade plan, `grade_luts.py`, stays the grade);
**Higgsfield Color Match** needs its reference picked in its UI. The Fusion-based packs (Video Editor Studio's starter
pack, Krokodove) are controllable through their comp's inputs, so prefer them where they serve the same kind.

Rules for the library:
1. **Plan against it in the Visual Bible** (`clients/_TEMPLATE.md` §6): the *specific item names* this brand may use, by
   kind — "`Smooth Zoom In`, 12 f", not "some cool transition from the pack". Star them in the inventory.
2. **Title packs are gated by the project's title card** (house rule C3: *"Yes, the card is the permission"*). A title
   template is in play only where the approved card names that kind (`typography-and-captions.md` §6c); a client
   profile that forbids titles gets a captions-only card (and a profile that forbids overlays, none). The
   **default** is the card's own generated title (C7); a pack title is the brand's choice for a kind, on the card.
3. **Refused, never improvised** (`resolve_library.py plan` / `console`): a kind nothing installed provides; an item
   whose name says it overshoots (bounce, elastic, pop…) on a title, number or UI (C2); an effect with no id; more accent
   transitions than the title card allows (C5).
4. **A pack transition consumes real frames on both sides.** The 1–2 s handle rule isn't optional where the plan calls a
   pack move — and heavier moves eat more. The console reads both neighbours back; check the asset's span before
   trusting the default handle.
5. **`INVENTORY_TEMPLATES` + `motion_qa.py inventory`** still tag the transitions' families for the budget at lock;
   `LIBRARY_SCAN` is the superset `resolve_library.py` reads.

### The plan — transitions are a pre-production decision

**The transition plan is written at the storyboard (Stage 2), one line per join,** in the shotlist's
Transition Plan section: `S1→S2 · <type from the palette> · <exact pack asset, if any> · handle
needed both sides? · why (the motivation)`. Downstream:

- `ai-generation.md`'s editorial-handles rule reads the plan: **every join the plan marks
  non-hard-cut gets its 1–2s handles generated**, on both sides. A dissolve decided in the edit,
  on clips generated to exact length, is a dissolve you can't have.
- The selects pass (`direction.md` §4) checks adjacent clips *against the planned join* — a match
  cut needs its correspondence confirmed in pixels before the edit inherits it.
- The edit **executes** the plan; deviating from it is fine when the footage argues, but it's a
  noted decision, not a browse through 1,000 options at the cut point. That browse is where whole
  afternoons and brand consistency both die.

## Applying transitions — the mechanics

⛔ **Until Resolve 21.1 the scripting API could not add a transition, and this section said so. 21.1
added `TimelineItem.AddTransition`** [PRIMARY · Blackmagic's scripting CHANGELOG § 21.1, "Transition
API"]: `item.AddTransition({"type": "Cross Dissolve", "category": "simple", "position": "end",
"alignment": "center", "duration": 12})` on the outgoing item. **Measured 2026-09-14 on Studio
21.1.0.14:** it placed a 12-frame Cross Dissolve centred on the cut (6 frames either side) and returned
the transition item — and `GetItemListInTrack` now returns that transition **as an item of its own**
(`GetType() == "transition"`), so anything that counts shots from a track must filter on type.
⚠ **That was measured on two generated solid-colour clips, which have unlimited frames past the cut.
What it does on media with no handle — refuse, or eat the adjacent clip's needed frames — is
UNVERIFIED,** and so are pack assets through `category: "fusion"`/`"ofx"`. Read the clips' positions
back after the call. So:

- **Apply the planned transition at the cut point** — through the console's `APPLY_TRANSITIONS`
  (`resolve_library.py console <job> --plan 07-edit/fx-plan.json`, v2.45): built-in dissolves as `category: "simple"`,
  installed pack transitions by name as `category: "fusion"` [stub until the live test L7], each read back with both
  neighbours. The *choice* was already made at the storyboard (see the grammar above); the edit is applying it. A pack
  transition the API refuses is placed by hand from the Effects Library, and the report says which.
- **This only works if the clips were generated with a handle to blend.** See `ai-generation.md` →
  "Editorial handles": B-roll generated 1–2s past the montage length — ⛔ **B-roll only.** A
  dialogue clip is audio-conditioned and must NOT be extended past its line; over the silent tail
  the model invents lip movement (`shot-handoff.md` §1). Where a dialogue join needs frames to
  blend, they come from a silent settle clip, a cutaway, or a J/L cut (`shot-handoff.md` §2.2) 1–2s past where the line ends. A clip trimmed to exactly the frame the montage needs
  has nothing to dissolve into — Resolve will either refuse the transition length or eat into the
  adjacent clip's needed content. If a handle is missing, that join has to stay a hard cut.
- **Know whether the handle actually survived into the assembled timeline — don't assume it did.**
  If the rough cut came from `build_fcpxml.py`, the handle only shows up if you told it to: pass
  `--durations durations.json` with each dissolve shot's *needed* (non-handle) length, shorter than
  the real generated file. Without it, every clip plays its **full** generated length (handle
  included) with zero spare frames left — the exact "eats into the adjacent clip's needed content"
  failure above. The script prints a **transition handle exposure** summary after every run — read
  it before you get to Resolve and find out the hard way which joins can actually take a dissolve.
- **Reserve dissolves for scene-to-scene or mood-shift joins.** Keep same-scene dialogue-clip →
  B-roll-tail cuts (covering one continuous VO line) hard — a dissolve there reads as a mistake,
  not a transition.
- **A join effect that has to see both shots goes on one adjustment clip across the cut**, not on each
  clip: a zoom, a directional blur, a lens distortion. The course's editor nests the clips. Resolve's
  equivalent is an adjustment clip on a track above both shots, trimmed to span the cut, since it reaches
  down to everything beneath it (§ Resolve at volume), or a compound clip of the two shots. Resolve
  stabilises clips, so a stabiliser across a join goes on the compound clip (untested here; check it frame
  by frame). A
  directional blur across a cut does not make a seamless join by itself: match its direction to the action
  [PRACTITIONER · course notes].
- **Before a spin or a zoom made in post, keep the corners full.** Scale the picture a little past 100 % or
  mirror its edges, so no corner ever shows empty [PRACTITIONER · course notes]: 101–102 %, or a mirrored tile
  (about 300 in the course's editor) with the scale returned to 100. In Resolve: a transform with mirrored
  edges on the adjustment clip (in Fusion, the Transform tool with its Edges set to Mirror).

## Lipsync — cut the sound to the picture

**Never let the video model *invent* the speech.** Video models mispronounce many languages badly
(and non-English ones especially), so every spoken word is owned by a proper TTS and the video model
only animates a mouth to it. **The preferred method is generation-side: the recorded VO is passed into
the model as an audio reference so the mouth is animated to the real audio** — see `ai-generation.md`
Step 4 for the full recipe. Edit-side alignment in Resolve is the fallback for clips that were
generated silent:

1. Put the character clip + its VO line on the timeline; open the **audio waveform** (or the
   **Fairlight** page). Resolve's **auto-sync** (sync by waveform / timecode) can line them up.
2. **Slip the audio** so the loud consonant hits (waveform peaks on p/b/t/k) sit on the frames where
   the mouth is most open. Nudge one frame at a time (`,` / `.`).
3. If a syllable still floats, **cut away to a B-roll or the other character's reaction** on that
   exact syllable — the eye forgives what it can't see. (This is why we cut extra B-roll.)
4. For a stubborn line, retime the clip a few percent.

**⚠ Know which kind of clip you're holding before you touch its audio — the two behave oppositely.**

| Clip kind | Can the VO be slipped? | Why |
|---|---|---|
| **Baked-audio clips** — audio-driven (generated *with* the VO as a reference) **and** native-audio (the model spoke, Path B) | **No.** The audio is locked to the clip's cut | The sync is baked into the picture; any offset breaks phoneme alignment and there is no way to fix it in the edit. For native-audio clips the embedded audio **is** the VO — keep it, and run the verbatim word check before captioning |
| **Silent generation** (no audio ever given to the model) | **Yes** — slipping is the whole technique | Nothing in the picture is tied to specific phonemes, so the cut-to-picture pass is what creates the illusion |

Mark which is which when the clips are filed (the `_noaudio` suffix on a conformed lipsync clip is
the flag), so the editor doesn't slip a clip whose sync is already correct and destroy it.

**And verify by listening.** The check is an A/B with the VO over picture at speed, not a contact
sheet — a frame grid shows when the mouth moves, not whether it articulates. See `realism-qa.md` §2.

## Audio hygiene — delink/remove embedded audio when the VO is separate

**Rule:** if a character clip's own audio is not the audio that's going to play in the final mix,
it cannot be left on the clip once the external VO is on the timeline — mute or strip it first,
every time, not just when it happens to be audible on a quick review.

This matters because it's easy to miss: generation-side audio-driven lipsync clips (Step 4 in
`ai-generation.md`) legitimately keep their own embedded audio — it **is** the VO, generated
together with the mouth movement, and that's correct, leave it alone. But the moment a shot ends up
with a **separate** external VO file instead — the edit-side lipsync fallback path, a line
re-recorded after the clip was already generated, or a "silent" generation the model didn't
actually render silent — the clip's own audio has to come off before the real VO goes under it.
Skip this and the mix doesn't obviously break: the correct line is still audible on top, so a quick
watch-through sounds fine, and only a proper listen (or the client) catches the buried second audio
source underneath it.

**`scripts/strip_embedded_audio.py` automates the check and the fix.** It cross-references
`03-clips/<SHOT>_...` against `05-voice/<SHOT>_...` on the same `<SHOT>` token this pipeline already
uses everywhere: a clip with audio AND a matching external VO file gets its embedded audio stripped
(a non-destructive `_noaudio` sibling, never an overwrite); a clip with audio and **no** matching VO
file is left alone (assumed to be the audio-driven-lipsync case) but is still reported so you can
eyeball that assumption. Run it once dialogue clips + VO are filed, before assembling the timeline:

```
python3 scripts/strip_embedded_audio.py --project <that dir> --check   # report only, first
python3 scripts/strip_embedded_audio.py --project <that dir>           # writes the _noaudio siblings
```

Swap the `_noaudio` version into the timeline in place of the original wherever the report lists a
strip. This is a dialogue-clip check: the rule is never two **voice** sources on one clip
(`ai-generation.md` → the quality floor, "what survives", item 1). Do not pass `--broll-too` on a v2.49
job: B-roll keeps its native diegetic sound (§7d), unless the job is on the `guide-audio` switch.

Beyond the dialogue clips, **a clip's own diegetic sound is kept as production sound and can be replaced at
any time** (§7d). `mix_qa.py` reports which takes are heard in the export and passes; under `guide-audio` it
refuses a heard take the audio manifest does not approve.

## ⛔ Sound perspective and space — the gap that had no doctrine

Everything else in this file assumed a shoot, where perspective comes free: the boom is closer on a
close-up, the room is in the recording, and a wide *sounds* wider because it was. **This pipeline has
none of that**, and until 2026-09-07 nothing here said so.

### What actually happens now, stated plainly

Every line is **one TTS render**. That one render is cut against a wide, a close-up and an insert.
So the CU and the WS carry **byte-identical audio**, dry, at one apparent distance, in no room at
all. Nothing in the skill noticed, because the only enforced audio fact was integrated loudness on
the finished file.

That is the sound equivalent of using one focal length for every shot and grading none of them, and
it produces the same symptom: the viewer cannot name what is wrong, which is exactly when they are
hearing the join (see *Purcell* under **Retention editing** — a viewer who cannot say what is wrong
is usually hearing it, not seeing it).

### Two moves, and they are the whole of it

**1 · Put the voice in the room.** One short reverb send per LOCATION, not per shot. Set it once
against the widest shot in that location, then leave it. Dry dialogue over a picture of a tiled
kitchen is the tell; a small amount of the right room is the fix. **The send is per location so it
cannot drift between shots** — which is the same reasoning as one grade over the whole film.

**2 · Trim presence by shot size.** From the same take, on the same line:

| Shot | Voice | Room send | Why |
|---|---|---|---|
| **Close** | Full presence, a touch more low-mid, breaths audible | Least | You are inside their space; the room barely exists |
| **Room** (medium / two-shot) | Neutral — this is the reference | Set here | The default the other two are trimmed against |
| **Distant** (wide, over-shoulder, through a door) | Slightly softer, a little less top | Most | The room is between you and them |

Two or three dB and a shelf. ⛔ **This is not a mix flourish; it is the audio half of shot size**,
and it is free — one take, three treatments.

### What decides it, and where it is written down

The shot list's handoff card carries a **`PRESENCE:`** field per dialogue clip — `close`, `room` or
`distant` — derived from the shot size the director sets in the same card. `shotlist.py` writes it
as `<NEEDS DIRECTION>` like every other directorial field, so an undirected film shows it as a blank
rather than defaulting silently to "room", and `shotlist.py --check` counts it.

**Why a field rather than a rule:** presence follows the *cut*, not the *script*, and the cut is the
director's. A whispered line in a wide is a legitimate choice that inverts the table above. A blank
gets filled; a guess gets approved.

### ⛔ And the one thing that is not optional

The ambience bed on **A3**. *No clip plays over silence.* `export_qc.py` now **FAILS** a master
carrying true digital silence, so an empty A3 is caught at the door instead of by a client, and
`resolve-production-console.py` creates the lane rather than assuming somebody made it. A deliberate
held beat is a real choice — use `--allow-silence` and say so in the QA log, which is the difference
between a decision and an omission.

---

## Audio finish (Fairlight)

- **The sound-design sandwich** (biggest amateur→pro jump; safe even when the words are locked — it
  sits *under* the VO). Three layers per scene: **(1) ambience** — a room/world loop (countryside
  wind, office, factory floor) at −18 to −24 dB, felt not heard; **(2) foley/SFX** — a sharp hit on
  a key action (folder slam, button click, a whoosh into the final beat); **(3) music** — the
  emotional bed. A flat "VO + music" mix is the #1 amateur tell. When they compete, words lead, the
  music sits as loud as it can without covering them, and effects come last [PRACTITIONER · course notes]. A
  picture's own actions get a sound only where the room would make one; designed accents (whooshes,
  risers) follow the accent budget (§ Music to picture), and a graphic's events follow §7f. Before
  calling the mix done, solo the effects lane (A4) and play it alone. The course's one fader move (−8 to
  about −4.5 dB) was a single clip, not a default [PRACTITIONER · course notes].
- **Duck the music under the speech until the speech is at least 14 LU louder than it, and at least
  19 LU louder than the ambience.** Those are the floors for a general audience: Torcoli's expert
  floors (10 LU over music, 15 LU over ambience), plus the 4 LU more that non-expert listeners wanted.
  Over another voice the floor is 20 LU. Use Fairlight clip volume or a compressor side-chain, and lift
  the bed in the gaps and into the CTA. The gain change is whatever reaches that gap. `mix_qa.py`
  measures it on the export's stems while the dialogue speaks, and `approve export` refuses a mix under
  it (the mix gate, §7b) [PRIMARY · Torcoli et al., JAES 67(12) 2019, abstract read 2026-10-23 · Geary
  et al., JAES 68(11) 2020, read 2026-10-26]. For a 45+ audience the gate adds 2 LU
  (`--audience 45+`): Geary's listeners aged 57+ preferred larger gaps, but only voice over voice was
  measured, so the +2 is [assumed]. The profile token is `music.duck` (`brand-system.md` §2).

  **On top of the gap, notch the bed under the voice** [PRACTITIONER · course notes]: solo the cue, find the band
  that sits on the words, and cut it with the music lane's EQ, so the rest of the bed can stay loud.
  `music_fit.py bed` already carves 1.5–4.5 kHz by 3 dB while the voice speaks; this is the hand pass for a
  band that still fights. No frequency is a default. The course's printed curve (about 4.4 kHz, −10.6 dB,
  Q 1.3, with the music at −7.6 dB) is one example [PRACTITIONER · course notes · read off the course frames]. The
  notch adds to the 14 LU gap and does not replace it; `mix_qa.py` still measures the gap (§7b).

  ⚠️ **SUPERSEDES IN PLACE** (2026-10-26). Previously: "about 14 LU for a general audience, and 15 LU
  or more over ambience". The 4 LU non-experts wanted was added to the music floor and not to the
  ambience one. The research and jury in lab record lab-00012 (not shipped) caught it.

  ⚠️ **SUPERSEDES IN PLACE** (2026-10-23). Previously: "Duck the music under the VO (−8 to −12 dB
  while a character speaks)". A gain change does not fix the result: an 8 dB duck under a loud bed can
  still leave the music a few LU under the voice. Two sources disagreed (Higgsfield's launch film
  skill at about 10 dB, lab-00009's research at 15–20 dB), and the measured gap settles both.
- **Loudness: the target comes from the delivery format, not from habit.** Streaming and social sit
  around **−14 LUFS** integrated with true peak ≤ −1 dBTP — **a house value, unverified until Meta's,
  TikTok's and YouTube's own normalisation targets are sourced** (2026-10-27; `delivery-format.md`) (platform "official" ≈ −16; TikTok/Reels
  normalize ~−14 to −16; many push −10 to −12 for mobile punch — −14 is the safe, consistent
  choice). **EU broadcast is EBU R128 −23 LUFS**, nine LU quieter, and delivering a −14 master to a
  broadcaster is a rejected deliverable. Read the target off the format preset
  (`assets/delivery-formats.json`) rather than assuming −14, and check it with `export_qc.py
  --format <preset>`. A working editor's ranges sit beside the house value for comparison only
  [PRACTITIONER · course notes]: a punchy ad about −15 to −14 LUFS, a long piece about −17 to −19, delivered as
  quiet as −18. The preset still decides. The course's soloed voice at about −15.5 is a voice, not a
  value for the full mix.
- **Scope the fix to the problem — clip effects for one bad clip, track effects for a consistent
  treatment** [PRIMARY · Dovale, *Mastering DaVinci Resolve 20* — via a local extraction, read
  2026-08-29]. Fairlight allows non-destructive **clip-based** effects alongside the track chain,
  and with the fixed A1–A6 lanes above the temptation at volume is to fix everything at track level,
  which degrades the clips that were already fine. One hissy generated line is a clip-level fix; a
  whole VO track needing the same EQ is a track-level one.
- **There is an in-Resolve route to the number, not just a check after render.** Fairlight meters
  loudness **across the whole programme** (with a history of how loud the mix has been) and offers a
  bounce-to-track pass where you set a loudness target and conform the bounced mix to it [SECONDARY
  · Dovale, *Mastering DaVinci Resolve 20* — via a local extraction, read 2026-08-29]. ⚠ **The book
  states the mechanism and gives no numeric targets at all** — so the target still comes from
  `assets/delivery-formats.json`, and `export_qc.py` still runs on the rendered file, because a
  conform inside the NLE is not evidence about the file that shipped.
- **Voice Isolation / Noise Reduction are the first reach for a noisy source**, before an AU/VST
  round-trip [SECONDARY · Dovale, *Mastering DaVinci Resolve 20* — via a local extraction, read
  2026-08-29]. In this pipeline that is a **Path B** concern only (native model audio); a clean
  external VO should never need either, and if it does, the take is the problem — fix it upstream
  rather than restoring it here.
- **Recorded dialogue (a real shoot or a recorded read, not a TTS render) runs one chain, in order**
  [PRACTITIONER · course notes]:
  1. capture at 32-bit float on the recorder;
  2. pull a clipped clip down (the course uses 3 dB) and bring the other lines to match;
  3. EQ: a high-pass near 100 Hz, a little low end back on a lav, a little air;
  4. soft compression: ratio 2.5, threshold by ear (the course tries −9);
  5. de-click (the course sets 2.5) or de-ess, only when the click or the sharp "s" is heard;
  6. denoise off when the floor is already quiet;
  7. rides of about 1 dB so the lines peak alike (the course's peak near −5 to −4 dBFS).

  In Fairlight, steps 3–4 are the track's own EQ and Dynamics on A1–A2, and the scope rule above holds: a
  clip effect for one bad clip. ⛔ The course's track limiter at −0.1 dBFS is a track setting, not the
  ceiling: the master still ships at true peak ≤ −1 dBTP (the loudness line above).

## The audio delivery layer — stems, M&E, and what a 30-second ad actually owes

Everything above is the mix. This is what leaves the building with it, and until 2026-08-30 the skill
had none of it: no stems, no M&E, no statement of sample rate, and no answer to "what does the music
licence actually require."

### 1. The A1–A6 lanes ARE a DME split. They were just never exported

The fixed lane convention above maps one-to-one onto the industry's standard separation:

| Lanes | Stem | |
|---|---|---|
| **A1–A2** dialogue / VO | **D** — dialogue | |
| **A3** ambience · **A4** foley/SFX | **E** — effects | |
| **A5–A6** music | **M** — music | |

> *"Stem outputs, also interchangeably called split tracks or just stems, are a separation of the
> final mix into discrete audio elements."* · *"**DME** – Dialog, Music, Effects – this split is
> typically the full final mix with the narration removed."* · *"**M & E** – Music and effects – here
> all of the musical elements and sound effect elements have been combined into a single split, but
> containing no story important dialog or narration."*
> — Woody Woodhall, post-sound professional, *Audio Splits, Stems & Elemental Tracks*, ProVideo
> Coalition, 2015 `[SECONDARY · practitioner, read 2026-08-30]`

**So the work is already done.** The lanes exist for editing reasons; rendering them as separate
files is a Deliver-page bus assignment, not a re-mix.

### 2. ⛔ Why stems earn their keep on a SERIES — and are ceremony on a one-off

The honest case first: **for a single video you own the Resolve project and can re-export anything**,
so a stem set proves nothing you cannot regenerate. Four reasons it still pays on the work this shop
actually does:

1. **⛔ Language versions — this is the real argument.** An **M&E** turns a Hungarian, English or
   Ukrainian version into *a VO swap*, not a re-production. **A non-English account is the common case**, and the day a
   second-language version is asked for, the M&E is either sitting in `10-export/` or the episode is
   rebuilt from scratch.
2. **Project rot.** A Resolve project depends on media paths, plugin versions, the app version and
   the machine it was built on. A stem set is flat, permanent and tool-independent. **Over a series
   that runs for years, the master and the stems outlive the project file** — this is the same
   argument as `series-continuity.md`'s registry, applied to sound.
3. **The sound-off / in-store cut.** Music and effects with no voice, for a screen nobody listens to.
   That is the M&E, already rendered.
4. **Revision cost class.** "Change the music" against a stem set is a re-mix of one element rather
   than a trip back through the whole timeline (`revisions.md`).

⛔ **The limit, stated:** on a one-off that will never be re-versioned, rendering five files instead
of one is ceremony. **Deliver stems when the account is a series or a re-version is plausible** —
which, for this shop, is most of them.

### 3. ⛔ The M&E must be UNDIPPED, or it carries holes shaped like Romanian

The single non-obvious rule here, and the one that makes the difference between an M&E that works and
one that looks fine and is useless. Woodhall notes that some deliveries require *"undipped stems"*
(unmixed elements) *"for international re-versioning flexibility."*

**The mechanism:** the mix ducks music under the VO (to the gap above). If that ducking is baked
into the music stem, the M&E has a volume dip **at every place the Romanian line happened to fall**.
Drop an English VO of different length onto it and the music sags where nobody is speaking and
fights where somebody is.

**So render the M&E from the undipped music and effects**, and let the new mix duck it again. The
full mix keeps its ducking; the M&E does not. In Fairlight this means the ducking lives on a clip or
track *volume automation* you can bypass for the M&E pass, **never printed into the source file**.

### 4. ⛔ 48 kHz. Always. And the reason it bites silently

The video world runs at **48 kHz**; the music world runs at **44.1 kHz**. A library track downloaded
at 44.1 and dropped into a 48 k timeline is the classic pitch-and-drift bug, and **it produces no
error** — it just sounds very slightly wrong to someone who cannot say why, or drifts against the
lipsync over 40 seconds.

- Every delivery preset now states `sample_rate_hz: 48000`, `bit_depth: 24`, `channels: 2`
  (`assets/delivery-formats.json`).
- `export_qc.py --format <preset>` now checks the **rendered file's** sample rate and channel count
  alongside loudness — because a setting inside the NLE is not evidence about the file that shipped.
- **Stems render 24-bit** — headroom for a later re-mix. The delivered `.mp4`'s AAC track is whatever
  the preset says.
- A mono master on a stereo spec is the other silent one: it plays quieter than everything around it
  and reads as "your video sounds bad" rather than "your video is mono".
- `motion_qa.py check` warns on a timeline that mixes audio sample rates or source frame rates (a
  44.1 kHz voice beside 48 kHz audio, 59.94 fps sources in a 23.976 timeline) before any frame-accurate
  join is trusted.

### 5. ⛔ A cue sheet is NOT the instrument for a 30-second ad — a negative finding worth having

The instinct on hearing "music rights" is to build a cue sheet. **For commercials that is the wrong
document**, and knowing so saves building one nobody will read:

> ASCAP *"processes television commercial, PSA and movie trailer performances reported by
> **Competitrack**, a sophisticated digital monitoring system, on the basis of a census survey"*, and
> uses *"**Soundmouse** fingerprint technology to identify music used in Radio Commercials, Public
> Service Announcements, Short Form Infomercials, Movie Trailers…"*. Cue sheets appear only for
> **long-form infomercials over five minutes**, which are processed *"in the same manner as other
> program performances, using information ASCAP obtains primarily from cue sheets."*
> — ASCAP, *Music in Advertisements* `[PRIMARY · the PRO's own page, read 2026-08-30]`

A cue sheet is *"a schedule of the music contained in a film or television program"* listing the
title, **the way the music was performed** (visual instrumental, vocal, background), **the duration**,
and the composers/publishers with their ownership shares — *"the essential document for ASCAP to
distribute royalties"* `[PRIMARY · ASCAP Cue Sheet Corner, read 2026-08-30]`. **That is a programme
instrument.** A 30-second promo is identified by fingerprint, not by paperwork you file.

⛔ **What IS the instrument is the licence record** — the sync and master licence for the bed — which
this skill already keeps as the **per-asset provenance sidecar** (`stock-sourcing.md`). The exposure
that would actually bite is an unlicensed or wrongly-scoped bed (a "free for personal use" track in a
paid ad), not a missing cue sheet.

⚠ **Scope limit, stated rather than glossed:** ASCAP is a **US** society. The Romanian and wider EU
PROs (UCMR-ADA and its counterparts) were **not checked**, and a broadcast rather than social
placement may carry obligations this paragraph does not cover. If a placement ever moves to
broadcast, verify before assuming this transfers.

### 6. What to render, and what it is called

| File | When | Name |
|---|---|---|
| Full mix (inside the `.mp4`) | Always | `acme-01007_master_v001_9x16.mp4` |
| **M&E**, undipped | **Any series account** | `acme-01007_mne_v001_20_48k24.wav` |
| Stem — dialogue | Series, or on request | `acme-01007_stem-d_v001_20_48k24.wav` |
| Stem — music, undipped | Series, or on request | `acme-01007_stem-m_v001_20_48k24.wav` |
| Stem — effects | Series, or on request | `acme-01007_stem-e_v001_20_48k24.wav` |
| Full mix as a separate WAV | On request (broadcast) | `acme-01007_mix_v001_20_48k24.wav` |

`20` is the channel layout (stereo; `51` for 5.1), `48k24` the rate and bit depth. The grammar and
its rules are `pm-workflow.md` § Naming convention; `name_lint.py` checks these names too.

⛔ **Per-shot audio elements keep the picture grammar** — `acme-01007_s1_0020_vo_host_tasha_v001.wav`
is an element, not a deliverable. Deliverables have no shot because they have all of them.

### 7. The audio ship gate

- [ ] `export_qc.py --format <preset>` PASS — loudness, true peak, **sample rate, channels**
- [ ] The M&E plays with **no dips where the VO used to be** (listen to it, do not look at it)
- [ ] Every music bed has a provenance sidecar with a licence that covers **paid advertising**
      (`stock-sourcing.md`) — the exposure is the licence, not the paperwork
- [ ] Stems render only on a series account; a one-off ships the master alone (§2)
- [ ] Nothing plays over silence — the room-tone bed runs under every moment (the sandwich, above)
- [ ] **`mix_qa.py measure` PASS on every render in 10-export/, and `mix_qa.py licences` clean.**
      `gate.py approve export` refuses without both (§7b–§7e)
- [ ] Every hit in the cut was placed in Fairlight at the frame `sfx_conform.py` proposed (§7f): one per
      event, on its frame or a frame late, and its re-check OK; after any re-cut, rebuilt from the new frames
- [ ] Measured before calling it done: the effects against the music and the voice (`sfx_conform.py
      levels`), and the stems summed — all of them — against the export (`mix_qa.py`, §7b)
- [ ] The waveform sync proof read (`mix_qa.py wave`, v2.46): every attack on or just after its line, and
      no long sound narrating a graphic's motion (§7f, events not motion)

### 7b. ⛔ The mix gate — `mix_qa.py`, which `approve export` runs

Author, 2026-10-26, on the SFX research and jury (lab record lab-00012 (not shipped)): build
*"Export audio gate"*, *"Native audio as guide only"* (reversed 2026-11-05, §7d), *"SFX licence manifest"* and *"Room tone and
ambience continuity"*. All three judges named the same first build: one gate that measures the mix
the viewer hears, on the file that ships. `export_qc.py` measures the file's level. This gate measures
whether the line is heard over the bed.

**What to render for it in Fairlight** (QC files, not deliverables, so they go in `09-qa/mix/`):

- **The dialogue stem**: every line, post-fader, as it plays in the mix.
- **The bed**: the whole mix with the dialogue tracks muted and **the ducking on**. This is not the
  undipped music stem a language version needs (§3). That one has no ducking in it, so it says nothing
  about the gap the viewer hears.
- Optional, each held to its own floor: an ambience stem (**required in the drama lane**), a music
  stem with the ducking on, and `--voices` for any other voice under the line.

```
python3 scripts/mix_qa.py measure <job> --export 10-export/<slug>_master_v001_9x16.mp4 \
    --dialogue 09-qa/mix/<slug>_qc-d.wav --bed 09-qa/mix/<slug>_qc-bed.wav \
    [--ambience 09-qa/mix/<slug>_qc-amb.wav] [--audience 45+] [--lane drama --scenes "S1-S4;S5-S7"] \
    [--holes 09-qa/mix/HOLES.txt]
```

It writes `<render>.mix.json` and `.mix.md` beside the render. `approve export` refuses while any
render in `10-export/` has no report about its exact bytes, or a report that FAILS.

| Check | FAIL when | Source |
|---|---|---|
| Stems match the export | the dialogue and the bed do not sum to the export within 1 LU, or 95 % of their 400 ms windows not within 1.5 LU | [assumed]. A report about some other mix measures nothing |
| VO over bed / music / ambience / voices | the dialogue's loudness over the element's, energy-averaged over the windows where the dialogue speaks, is under the floor (14 / 14 / 19 / 20 LU) | Torcoli 2019, Geary 2020 (above) |
| VO over bed on a phone | the same after a mono fold and a 300 Hz–7 kHz band | [assumed]. The research found no 2024–26 measurement of phone speakers |
| Short-term ceiling | any 3 s window is more than 5 LU over the export's integrated level | [PRIMARY · EBU R 128 s1 V3 2020: −18 LUFS max short-term at −23 integrated], applied relative to the export's level, which is an extrapolation |
| Mono fold-down | the export loses more than 3 dB folded to mono, or the dialogue windows are out of phase | [assumed]. Uncorrelated stereo folds down at −3 dB |
| Room tone under every moment | the bed (or the ambience stem) is silent, −60 LUFS for 0.4 s, outside a planned hole | export_qc.py's silence floor |
| No dropout at a cut | 20 ms of the bed sits 40 dB under its neighbourhood within ±0.25 s of a cut | [assumed] |
| Ambience held across each scene (drama) | no ambience stem. A level jump over 3 LU across a cut inside one scene is a finding | [assumed] |
| Native audio kept (v2.49) | never — it reports which non-dialogue takes are heard in the export (cross-correlation ≥ 0.3) and passes. Under the `guide-audio` switch the old check returns: "native audio is a guide only" FAILs a heard take the manifest does not approve | [assumed] |

**Findings are for the mixer, not the gate:** spans under the floor, a click near a cut on the
dialogue or ambience stem, an ambience jump inside a scene. A planned silence before the claim is a
craft move (Thom, in the research), so list it in `HOLES.txt` (`12.3-12.8 the pause before the
offer`) and the room-tone check allows it.

**A floor is changed per job, never silently:** `--floor-music 12 --why "<the reason>"`. The reason
goes into the report.

### 7c. ⛔ The audio manifest — every sound, and the licence that lets it ship

`mix_qa.py manifest <job>` writes `09-qa/mix/AUDIO-MANIFEST.md`, one row per audio file under
`05-voice/`, `06-music/` and `06-sfx/`. Fill each row in, and `mix_qa.py licences <job>` (part of the
export check) refuses while:

- a file in those folders has no row, or a row names a file that is gone;
- a row names no licence, or its licence does not cover **paid advertising** (`paid ads: yes`);
- an AI-made row (`source: ai:<tool>`) is missing its `tool`, `version`, `plan` or `region` (where the
  ad runs). The licence depends on all four;
- a row hits a known block in `assets/ai-audio-licences.json`: MMAudio (its weights are
  non-commercial), HunyuanVideo-Foley in an EU, UK or Korean ad, an ElevenLabs free plan, or an
  ElevenLabs Beta output. That file carries each block's source and the date it was read, and
  licences change, so re-read the source before trusting an old row;
- a `native` row has no `approved` — only in a job on the `guide-audio` switch (§7d); since v2.49 a kept
  native take needs no approval.

The manifest is a record, not legal advice. It writes down which licence each sound ships under, so
that a bed marked "free for personal use" is caught before the paid ad goes out.

### 7d. Native sound is kept by default (v2.49)

Author, 2026-11-05: *"Native audio can be replaced at any time after. Not an issue."* All 12 festival films
read for 2.49 generated native audio on 94–100 % of their video calls, directed it in the prompt, and the
jury named sound in the notes for 1st and 2nd place `[SECONDARY · festival study 2026-11-05]`.

⚠️ **SUPERSEDES IN PLACE** (2026-11-05) — previously "Native audio is a guide track": the clip's own sound
was "a timing scaffold", put "on a muted guide track under the clip" and replaced, and `mix_qa.py` refused a
heard non-dialogue take without a `native` approval. That rule now lives behind the `guide-audio` switch.

1. **The clip's own diegetic sound is production sound.** Ambience, footsteps, the door, the fabric: it goes
   on the timeline with its clip, audible. It was directed before the take, in the prompt's `[AUDIO]` block
   (`prompting-craft.md` §12): what the place sounds like and must not, the ambience, the effects, off-screen
   sources with their direction, `MUSIC: none`.
2. **It can be replaced at any time.** Any sound that is wrong — a thin room, a hit on the wrong frame, a
   material that reads false — is replaced in Fairlight with a licensed one (§7c), placed at the frame
   `sfx_conform.py` proposes (§7f). Replacing one sound does not oblige you to replace the rest.
3. **The models are still weakest on the room and on what a hit sounds like** (FoleyBench 2025, FlatSounds
   2026, in the research), and better at *when*. So listen to the room first, and keep the onsets as
   candidate event times even when a sound is replaced; `action_points.py` proposes the hit frame from the
   picture too.
4. **Dialogue is unchanged.** A clip that speaks is the voice gate's (`ai-generation.md` § Sound and Step 4);
   `strip_embedded_audio.py` handles a doubled line.
5. **`mix_qa.py` reports, it never refuses, on native sound.** It searches the export for the own sound of
   every non-dialogue take in the cut (the takes come from the motion reports), lists what it heard, and
   passes as "native audio kept". A `native` row in the audio manifest needs no approval.

**The `guide-audio` switch** restores the old rule for one job, written in the checkpoint's `Switches:` line
with its reason: native sound is a guide only, `generate_audio: true` needs `audio` approved, and `mix_qa.py`
FAILs a non-dialogue take heard in the export unless its `native` row carries `approved: <who>: "<their
words>"`. Use it for a sound-designed spot built from licensed libraries end to end, or a client who asked
for clean stems; never as a habit.

### 7e. Room tone and ambience continuity

In the drama lane the room is part of the continuity. Lay **one ambience bed per location, held
across every shot of the scene**. A per-clip native ambience changes on every cut, which is the
cheap-AI-drama tell the jury named. Pass `--lane drama --ambience <stem> --scenes "S1-S4;S5-S7"` (the
shots that share a location). The gate refuses a drama mix without the ambience stem, and names any
cut inside one scene where the ambience level jumps more than 3 LU. In both lanes the bed must never go
silent outside a planned hole, and must not drop out at a cut.

The beds on the machine are long, seamless location loops (Ocular Sounds' Ambiences: cities, coast, farmland,
rainforest, Provence; §7f lists them). Pick one whose place matches the story's (§7f, a recorded city is a real
place).

**With native sound kept (v2.49), the bed still holds.** Each clip now brings its own room, and those rooms
differ cut to cut: that is exactly the change this rule exists to hide. So:
- **one bed per location, laid under the native tracks**, running across every shot of the scene; the clips'
  own ambience sits on top of it, pulled down where it fights the bed or jumps at a cut;
- **one processing chain per location**: the same EQ, room send and level treatment on every native track of
  that location, set once against the widest shot (the same reasoning as § Sound perspective, one reverb send
  per location);
- the 3 LU jump check still runs on the ambience stem in the drama lane. A native track that jumps more than
  that across a cut inside one scene is pulled into line or replaced at that cut.

### 7f. ⚡ SFX that match the picture — `sfx_conform.py`

Author, 2026-10-26: *"the amount and timing doesn't always match what's happening in the shot. 3 drops of
water, and they are not timed to the splash itself. The AI should cut the downloaded SFX and adjust as
needed. Also try to understand the volume based on the distance, speed of the object etc."* The council
ranked it first (the motion and sound-effects proposal of 2026-10-26 [studio history]), and the owner chose all four
packages: event conform, per-event parameters, sound across cuts, and directional sound for earbuds.

**v2.49 — the script proposes, Fairlight places (house rule 9).** All SFX and edits are done in Resolve. The
steps below still find the events, read the frames, pick the sound, and work out each hit's frame, level,
tone and room — that is measuring and proposing. What leaves the step is the **placement plan** (the
placement log, the Resolve markers and EDL, `06-music/SFX-PLACEMENT.json`, `09-qa/sfx/LEVELS.json`). The hit
itself is placed in **Fairlight, by computer control** (rule 8, § What runs through the API), at the proposed
frame and gain, and checked by listening. The WAV and `--mux` renders of step 4 are proofs to listen against,
never deliverable audio.

**Two lessons from a real job** (production lessons, 2026-11-05):
- **Every re-cut breaks sync.** Foley carried over from an earlier cut through the EDL no longer matched the
  picture, and it passed loudness QA because QA cannot hear sync. After any re-cut, re-run the events on the
  new edit and rebuild the sound from its frames; never carry it over.
- **Measure before calling it done.** The first balance put a chair landing 13 dB over the music and left the
  fabric inaudible: the gains were set by feel. Run `sfx_conform.py levels` against the voice and the music,
  and sum **every** stem against the export (a check once summed three of four).

**The order, per shot:**

1. **Find the events.** `sfx_conform.py events <clip>` finds every local burst of new motion: each drop,
   step and tap, not one contact per clip. The camera's own motion and any global flicker are removed
   first. A named object's contact (`--track`, a sharp fall in its speed) confirms an event, and the
   clip's own audio casts a second vote. It is never used as the sound.
2. **Read the frames.** `sfx_conform.py read <job> --shot S` puts every event's frames (one before, the
   event, two after, boxed, and the whole frame) on one sheet, with a form beside it. The agent fills the
   form by **looking at the sheet**, in a closed vocabulary:
   - each event: what it is, the object's material, the surface it meets, wet or dry, size, force, and
     whether it is seen, partly seen or behind glass;
   - the shot: the room and its size, the distance, how many events there really are, the times of any the
     detector missed, and the words to search the sound by.

   The author, 2026-10-26: *"AI can read materials from the frame"*. Pixel code cannot name a material, so
   the read does it, and the director confirms. `keep: no` drops a burst that makes no sound, such as a
   reflection.
3. **Get the sound.** Search the libraries on the machine first. **(v2.68.0) The dispatcher runs the search
   and hands the spotter a candidate sheet:** `sfx_conform.py library sheet <job> <shot>` writes
   `09-qa/sfx/<shot>.candidates.md`, five sounds per event in the read. Identity decides first: the read's
   action first (its own word in a file's name counts most), then the materials, then at most three synonyms of
   the action that are never another action (thud → impact, hit, bump; never knock). The **measured shape** of each sound's attacks breaks ties, as an assumed
   rule until the blind test passes: time to its first peak against force (a hard contact is sharp, a soft
   set-down slow), how long it rings and how bright it is against material (metal, glass and ceramic ring and are
   bright; cloth, paper and food do not; never scored on a slide, and a slide, scrape, pour or rustle is matched on
   how long the FILE runs from the chosen attack, never one grain's decay, against the detector's busy time; when
   that busy time is unknown, slides are ranked by how long the file runs and the row says so). Each row says why,
   whether the attack has a clear gap to its neighbours (a clean cut, in ms) and which read fields were missing,
   so a words-only fallback is visible. From a file of many hits the index keeps the most isolated ones (the clean
   single hits a mixer wants); a file over a minute is measured on its first minute only, and its row says so (the
   conform still reads the whole file); a row not measured yet, or a long file whose first minute was a bed, is
   listed apart as not or partly measured, never among the five. Each row prints the chosen hit's time and the
   `in_s` and `out_s` to set, so `levels` takes the hit at that in-point (never an earlier one) and measures it
   alone, and the clip is trimmed at `out_s` when it is placed. A slide's `out_s` is the picture's busy time from
   the hit; with no busy time there is no `out_s`, so trim it to the picture. A row whose attack fits neither the
   force nor the material says so: listen to the next row too. A soft set-down is judged by the surface it meets (a mug on a
   desk thuds), a strike by the object (a spoon on a cup rings). Events the spotter adds after reading the frames
   have no row on the sheet: Grep the catalogues for those, keeping to paid-ads-cleared rows for client work. Client sheets keep only libraries cleared for paid ads. Distance, speed and size never
   choose the file: they set level, top end, room and pitch in the mix. The shapes come from
   `sfx_conform.py library measure` (resumable; stored in the catalogue, never beside the audio). By hand,
   `sfx_conform.py library search "water drop splash" --paid-ads-only` still works (`library list` shows what
   is catalogued, and each library's licence). `library pull <file> <job>` copies the pick into
   `06-sfx/library/` as a 48 kHz WAV, with a `.licence.json` beside it, and `mix_qa.py manifest` writes its
   row from that (§7c). Download only what the libraries lack (`stock-sourcing.md` §8). Then index the
   file: `sfx_conform.py index <file> [--material water]`. The index lists every attack in the file. A
   file with no separable attacks (rain, crowd, room) is a **bed** and is never cut. (v2.68.0) Inside the
   chosen file the conform picks the attack whose shape fits the event (time to its first peak against force,
   ring and brightness against material), not a random one from a loudness third: a quiet take of a hard hit
   is still a hard hit. Among equal shapes, the attack whose level inside its own file suits the force wins (a hard
   event takes a hit near the file's loudest). The placement records why (`attack_fit`).

   **On a real shoot, the set comes before the library** [PRACTITIONER · course notes]. Record a wild-sound or
   foley pass for each audible action before the set is struck (`real-and-ai.md` §2): the same action
   again, for sound only. File it under `06-sfx/` with its manifest row (§7c), index it, and conform it
   like a library pull, so the real sound is cut to the events. Foley mimed into a phone against the
   picture afterwards is a repair, not the plan. One of the course's spots carried about eight
   effect layers, about half from the set and half from a library [PRACTITIONER · course notes].

   **The libraries** (2026-10-26). Each has a catalogue: one row per file, with its words, length and
   licence, built by `sfx_conform.py library build <root> --name N --licence … --paid-ads yes|no|unverified
   --basis …`. A build resumes if it runs out of time. Catalogues live in `$CINE_SFX_CATALOGUES`, else
   `$CINE_HOME/sfx-catalogues`.
   Rows hold paths relative to each library's root, so the same catalogue works on the Mac and under a
   session's mount. Impulse responses are built with `--kind ir`.

   **The vendor's own sheets** (2026-10-27). A library that ships UCS "Metadata Import" CSVs (Ocular
   Sounds does, one per pack) is read into its catalogue at build time: each file's UCS category and CatID,
   the vendor's keywords and description, its musical key and its tempo. Search then finds a sound by the
   vendor's words, not only its file name. `library search "piano ping" --key C#` keeps only pings whose
   sheet names that root; `--bpm 120` keeps only loops at that tempo.

   **What one studio's machine had catalogued** (`library list`):

   | Library | Files | Paid ads |
   |---|---|---|
   | Fairlight Sound Library | 515 | yes, in a Resolve project |
   | Final Cut Pro Sound Effects | 1,337 | yes |
   | Final Cut Pro impulse responses | 362 | yes |
   | Pixabay downloads, SportsSFX | per file | per file |
   | Ghosthack | 169 SFX, 152 music (loop packs, not cues) | unverified, so never with `--paid-ads-only` |
   | Adobe Audition SFX (v2.68.0) | 8,269 | unverified until its licence is read |
   | **Ocular Sounds** (`ocular-sounds`) | 3,644 (96 kHz/24-bit) | yes |

   The terms are in `stock-sourcing.md` §8b.

   **Does the measured ranking help? The blind listening test (v2.68.0).** `sfx_conform.py library blind
   QUERIES.json OUT.md` builds, for each described moment, the top five from word search and from the measured
   ranking, merged, shuffled and unlabelled; the person ticks what they would keep, and `library blind-score
   OUT.md` counts keeps per method, and separately the keeps on files only one method offered (where they differ). Both
   arms score the same words on the same measured pool, beds dropped in both, so only the measured shape differs:
   it tests the shape tie-break, not the whole new ranking against the older plain word search.
   `--all-licences` includes libraries not cleared for paid ads (e.g. to hear the Adobe set). One listener in one
   sitting is a pilot. The plugin ships 25 moments in
   `assets/audio-match-queries.json`; any rule tuned on one studio's library stays on that machine.

   **Which Ocular pack for which job** (`Fairlight Sound Library/Ocular Sounds/`, by folder):

   | The job | The pack | Notes |
   |---|---|---|
   | Footsteps | Foley/**Stride** (853) | One step per file, by shoe (boots, sneakers, heels, dress shoes, sandals, bare and socks) and surface. A one-per-event conform keeps exactly the steps the shot shows |
   | Desk, keyboard, mouse, paper, pens | Foley/**Utility** (766) | |
   | Cameras: shutters, lenses, winders, flashes | Foley/**Aperture** (98) | |
   | Gears, switches, dials, small mechanisms | Foley/**Mechanica** (84) | Product films, UI |
   | Bicycles | Foley/**Vélo** (591) | Foley and designed pass-bys, skids |
   | Cars: pass-bys, engines, gear shifts | Vehicles/**Velocity** (113) | Designed; stems included |
   | Impacts, booms, risers, whooshes | Cinematic/**Foundation** (75) | The accent budget and the direct-response sound map: 2–3 risers an ad, each ending on a must-hit |
   | A speed ramp's cue | Cinematic/**Shift** (105, 35 of them stems) | Slow-motion morphs, the whoosh-down to the trigger (§ The ramp) |
   | Ocean hits, underwater | Cinematic/**Swell** (48) | |
   | UI and motion-graphics sounds, title pops | UI and Motion/**Vector** (250) | The Designed edition; the Construction Kit was not downloaded |
   | One ambience bed per location (§7e) | Ambiences/**Cityscapes Vol.1** (Houston), **Vol.2** (Barcelona, Florence), **Seaside Vol.1** (southern Spain), **Countryside Vol.1** (rural Texas), **Rainforest** (Borneo), **The Provence** (France) | Long, seamless loops: beds, never cut |
   | Tonal pings, a hit's stab in the bed's key | Tonal and Rhythmic/**Felt** (314) | Each ping's key is in its sheet (`--key`). The pings cover the seven natural notes and a few chords: for a bed in a sharp or flat key, use a natural note of its scale |
   | A tension pulse under the bed | Tonal and Rhythmic/**Pendulum** (65) | 8-bar loops at 90 and 120 BPM (`--bpm`) |

   ⛔ **Two conditions travel with every Ocular sound.**

   - It is never "the main element of a music track". Felt pings and Pendulum loops sit **under** a bed as
     support; they are never the motif, the mnemonic or a cue on their own.
   - The licence is per person. An outside editor working with the raw files needs their own seat. Only the
     finished mix leaves the machine.

   ⚠️ **A recorded city is a real place.** Sirens, bells, announcements and the language of the walla are
   national. Florence's bells or a Houston siren under a scene set in Bucharest is a continuity error a local
   hears at once. Pick the bed by the story's place, or keep it to a city's anonymous hum.
4. **Conform.** `sfx_conform.py conform <job> --shot S --sfx <file>[,<file>]` works as follows:
   - It cuts the file into its events and keeps exactly as many as the shot has.
   - It puts each attack on its frame, or **one frame late, never early**. Viewers notice early sound
     sooner: for a hammer on a peg, nobody noticed from about 75 ms early to 188 ms late (Dixon & Spitz
     1980, in Eg & Behne 2015).
   - It never plays the same piece twice in a row, and sets each event's level, tone, room, pitch and pan
     from the table below.

   It renders one 48 kHz WAV per clip in clip time (`06-sfx/conform/<S>.sfx.wav`). `--mux` also writes the
   clip with that sound as its audio, so it drops into the timeline in sync. It then **re-checks the render
   alone**: one attack per event, each 0 to +1 frame after its frame, no extra attacks. It counts on a
   dry twin of the render (`09-qa/sfx/<S>.sfx.dry.wav`): the same placements without the room, because
   a measured room's reflections are not events and cannot move an attack. The render inherits its
   sources' rows in the audio manifest.

   **The room is a measured space when one fits** (`--room auto`, the default). The conform picks an
   impulse response from the IR catalogues, using the read's space and size:
   - it must be a real space, never a plate, a spring or an effect;
   - an IR whose name places it (bathroom, kitchen, hall, car) comes first;
   - then the size class, then the decay nearest the space's RT60.

   Outdoors only an IR that names the place is used; otherwise the conform keeps its synthetic tail and
   says so. The IR's direct sound is faded out, so the wet path carries the room only. Which IR it used,
   and its licence, are in the placement log. `--room synthetic` or `--room <file>` overrides the pick.
5. **Across the cuts.** `sfx_conform.py joins <job>` reads the planned `join:` of each cut
   (`shot-handoff.md` §4b):
   - **Match:** the outgoing tail runs 4–8 frames past the cut.
   - **Camera carry:** one ambience clip spans both shots.
   - **Direction flip:** a clean break.
   - **Whip:** a whoosh with its peak on the cut, 2 per ad at most.

   It writes the plan and Resolve markers (EDL). `--whoosh <file>` also renders the whooshes as a stem in
   cut time.

**What sets each sound:**

| Parameter | What it changes | From |
|---|---|---|
| Count, timing | how many hits play, each 0 to +1 frame late | the pixels; the read's count and extra events; the `sfx: count=` the director sets wins |
| Distance | about −3.5 dB per class (close, medium, far), less top end, more room; a smaller burst than the shot's largest sits further back | the read or the tag; the burst's size (Zahorik 2005: a compressive curve) |
| Force, speed, fall | soft, medium or hard (−4 / 0 / +3 dB); faster and longer falls are louder, up to +3 dB each | the read's force; the pixels (burst strength, a named object's speed and fall) |
| Size | ±2 semitones: bigger is lower | the read; the burst's size |
| Material, surface, wet | which file plays (indexed with `--material`); hard is brighter, soft duller; wet lands one frame late | the read |
| Seen or not, occlusion | off screen −4 dB and duller; behind glass, a door or a wall −3 / −6 / −9 dB, low-passed | the read; the track's leaves-frame flag |
| Room | a measured impulse response for the space and its size, else a synthetic tail of the space's length (dry, exterior, interior, kitchen, bathroom, hall, car, street, forest, studio) | the read or the tag; the IR catalogues |
| Hero and density | the hero object's events at full level, the rest −6 dB; more than 6 events a second are thinned (a bed reads better) | the tag `hero=`; the pixels |
| Slide or hit | a slide keeps the sound running to the settle | the pixels (how long the change lasts) |
| Variation | ±1 dB jitter; never the same piece twice in a row | always |
| Phone low end | a 120 Hz high-pass on every event | always (the mix gate's phone simulation checks the rest) |
| Lateral position | constant-power pan capped at ±0.4, which folds to mono about 0.4 dB down | `--pan follow` only; off by default |

**Directional sound is for earbuds and headphones.** No 2024–26 measurement of phone stereo in portrait
was found, and the two speakers sit top and bottom [UNVERIFIED]. So pan stays off for phone-only ads.
Where it pays, in a 16:9 drama on headphones or an earbud cut:

- **The script bakes it.** `--pan follow` pans each hit to where it happens. Resolve's scripting API has no
  audio automation, so any movement inside a clip must be baked.
- **The editor does it by hand,** on up to five hero moments, with IntelliTrack (Resolve 19+, Studio
  only) [PRIMARY · Blackmagic, Resolve 19 New Features Guide]:
  1. Turn on Toggle Automation above the Fairlight tools.
  2. In the viewer's mini drop-down, choose Display Tracker Controls, turn on Auto, and choose the pan
     controls to automate.
  3. Select the range on the timeline, and the target track.
  4. Show a write-enabled pan parameter in the track's automation view.
  5. Drag the tracker onto the object and press Track.
  6. Cap the written curve to about ±40 % and smooth it.

  The mix gate's mono fold-down still applies.

**What it cannot do:** see a drop smaller than a grid cell, or separate two drops in the same cell on the
same frame. The read adds a missed event by its time. When unsure it plays fewer hits, because silence
beats a wrong hit. Every [assumed] threshold in the script waits for real clips to calibrate it.

**The measured level step — `sfx_conform.py levels` (a supplement ad job, 2026-10-28).** The levels on that job were guesses
and the measurement showed it: the effects sat 9 to 43 dB under the voice, the plate rub was inaudible, and the apple
bite (+4 dBFS) and the switch (+2.6 dBFS) clipped. `sfx_conform.py levels <job> --placement 06-music/SFX-PLACEMENT.json
--voice <the voice in timeline time> [--write]` measures each event's momentary loudness as cut against the voice's at
that moment and sets its gain to the category's target under the voice, with a −6 dBFS peak ceiling and Resolve's
+30 dB clip-gain limit:

| Category | Under the voice |
|---|---|
| whoosh | −8 dB |
| bite, hit | −10 dB |
| UI (click, tap, switch) | −11.5 dB |
| rise, marker | −12 dB |
| foley | −14 dB |
| quiet textures | −16 dB |

The targets were measured on one job; a client's `audio.<client>.json` `sfx_targets` overrides them. Each in-point moves
to the file's own transient, 10 ms before its attack: the plate rub's peak had sat 13 frames past an in-point in
silence. It writes `09-qa/sfx/LEVELS.json`; `--write` updates the placement and keeps the old gain beside the new.

**The density is the client's too.** Measuring one client's own reference ads (up to 13 sound events a minute, 48 % of cuts
with a transient) and matching it was right. The client's `audio.<client>.json` holds `sfx_density_per_min`; the
measurement that set it (`09-qa/<client>-sfx-density.json` on that job) is the model for the next client.

**New motion gets its sound in the same pass.** The circle drawn on the ingredient cards got its marker stroke only on a
later pass. A graphic's EVENT is a sound event: add it to the placement when the motion is made.

**Events, not motion (v2.46).** Sound marks what happens to a graphic: it arrives, lands, snaps into place, makes
contact, is drawn (the marker stroke). Its continuous motion stays silent: a slow drift, a turn, a scroll, grain, a
gentle push. Narrating motion with sound fills the mix with texture that competes with the voice and dulls the hits
that matter. `sfx_conform.py levels` warns on a placed sound longer than 1.5 s on a graphic (a row whose `on` or
title anchor names one, or a UI or marker sound) unless the row says `bed: yes` [assumed threshold]. The rule came
from two open-source animation skills' sound notes and agrees with this section's own "silence beats a wrong hit".
`mix_qa.py wave <job> --mix <file>` draws the whole mix with every event as a line (cuts grey, must-hits orange,
placed sounds white, titles blue); each attack should sit on or just after its line.

### 7g. Sound patterns from the festival winners (v2.49; HFF-08)

`[SECONDARY · festival study 2026-11-05]` — one or two films each, so these are patterns to reach for, not
rules. In our words:

- **Open the sound brief with "sounds like X, not Y".** One team's audio block starts with what the clip
  sounds like and what it must not sound like, then splits ambience, effects and music. The scene form's
  `[AUDIO]` block starts the same way (`prompting-craft.md` §12).
- **Tie a motif to an action, not to a character.** In one film the theme enters on the act of buying, **cuts
  out hard with no tail** when she stops, and returns faster each time. The audience learns the rule from the
  silences, and the finale breaks it. A motif that obeys a rule the viewer has learned can then carry the
  climax by breaking it.
- **Build an antagonist from texture only.** The same film's creature has no theme: breath, chewing, fabric,
  weight, kept out of the music until it "absorbs" it. A presence with no melody reads as other.
- **Give each environment its own ambience level, and let the change be heard.** The bed per location (§7e)
  is held inside a scene; between scenes the change is a cut the ear notices, and that is the point.
- **Music after, or not at all.** The winners added music afterwards (a song or a generated score) or left it
  out entirely, and their audio blocks said "no music" on most calls (over 60 % in seven of the nine films
  written in English). Here the owner picks the music, always (§ Music bed).

The `sound-off-story.md` check still runs on every film: a sound design this deliberate is still not allowed
to carry a beat the picture does not.

### 8. What this section cannot tell you

- **Whether the mix is good.** Everything here is deliverables and hygiene. The sandwich, the ducking
  and the beat-matching above are the craft; a file can pass every check in §7 and sound thin.
  `mix_qa.py` measures the gap, the ceiling, the fold-down and the room, not taste. Its phone check is
  a filter, not a phone, and its [assumed] thresholds wait for real mixes to calibrate them.
- **The EU/Romanian rights position** — §5 is explicit that it checked one US society and no other.
- **Whether a client wants stems.** Nobody asks for an M&E until they need one, and then they need it
  retroactively. That asymmetry is the whole argument for rendering it by default on a series.

## Captions and titles — made in Resolve (house rule C7, 2026-10-27)

> *"There is one more issue, Claude keeps insisting in creating mp4s of captions etc outside resolve, it should
> defrult to Resolve or Fusion native elements. Not create outside for no reason."*

⚠️ **SUPERSEDES IN PLACE** (2026-10-27) — previously: "three routes, ranked by automatability", with the ffmpeg burn
as the one fully automated route and the Subtitle track "not automatable — confirmed, permanent". Ranking by what a
script can do made the outside render the path of least resistance, and it was taken when nothing required it. The
routes are now ranked by where the text is made, and the outside one needs a reason. The decision is in the native-text proposal of 2026-10-27 [studio history].

| Route | How | Automation | Use when |
|---|---|---|---|
| **1 · The Subtitle track, burned by Resolve** | `build_srt.py` → the `.srt` onto a Subtitle track: `native.py console <job> --srt 08-captions/<slug>.srt` → the console's `PLACE_SUBTITLES` (ImportMedia, then AppendToTimeline onto an empty Subtitle track, every cue read back on its frame), or **File ▸ Import ▸ Subtitle**, one step → the track styled once from the card's caption tokens (Inspector ▸ Track Style) and kept in the project → `render-mp4.py` with `BURN_SUBTITLES = True` → `srt_qa.py burned` on the file | The placement is scripted with a read-back (the `.srt` import is a probe until it runs live); the burn is a documented render setting, checked in the pixels; the track's style is one manual step per project | **Every caption, by default** |
| **2 · The card's Fusion titles, generated by script, placed by computer control** (v2.45; placement v2.49) | `fusion_titles.py build <job>` writes one Fusion title per kind on the approved card — the card's font and Style, sizes, ink, plate, page and motion tokens as keyframes (§ The generated titles, below) → **in Resolve, by computer control** (house rule 8, § What runs through the API): the `.drfx` installed, each spec's template dragged onto its named track (Titles · Supers · Disclosure) at the spec's frame with every other track locked, its words typed per tool, a full-size still read on screen, frame 0 and the last frame included → the API **reads** the placed title back: its words, the font as installed, the card's hash in `CustomData`, the position and the fold → options reviewed as Resolve's own stills (`title_qa.py strip-native`) → measured on Resolve's own renders with the titles on and off (`render-mp4.py TITLES_OFF`, `title_qa.py native`) | The template is generated, never hand-styled; placement and words are by computer control, checked on screen and read back by the API. A row that cannot be placed **stops** with its reason — never rendered around | **Every title and super, by default**; captions in the pop regime, or a caption look the track cannot style (`SUBTITLES_AS = "textplus"`) |
| **3 · Outside Resolve** — `build_captions.py` (ffmpeg/libass), `assets/titles-hyperframes/`, `assets/supers-gsap/` | A captionless master → a styled `.ass` per format → ffmpeg burn; titles as ProRes 4444 with alpha for the track above the cut | Fully scriptable anywhere, the device VM included | **Only with a recorded reason**, one of four (`native.py reasons`): `batch` (a machine-assembled Mode B batch: no Resolve timeline exists), `derivative` (a Mode D re-format of a master already rendered), `remux` (a stream copy: no new pixels, checked packet for packet), `owner` (their words, `--quote`). `build_captions.py` refuses a burn without `--reason` and writes `<file>.external.json`; a title spec names `engine` and `engine_reason`; `shell_gate.py` refuses an ffmpeg text filter into a video outside `09-qa/`; `approve export` refuses a delivery file ffmpeg made with no record, and prints every reason |

⚠️ **SUPERSEDES IN PLACE** (2026-11-05) — previously route 2 was "generated and placed by script", the console's
`PLACE_TITLES` inserting each title and writing its words through the API. House rule 8: native titles, Fusion
and Fairlight are always computer control, never the API (*"It fails all the time"*). `PLACE_TITLES` is no
longer the placement route, and `gate.py` denies it through `run_script`; `native.py console` writes a copy
that places nothing (track setup, `CHECK_FONTS`, the Subtitle-track captions), and the words and positions are
read back with `DUMP_TIMELINE_JSON` and `native.py sync-specs` after the titles are placed by hand. The 21.1.2 calls below are kept as what the
API can read and set up, not as a way to place a title.

**What the scripting API settles** [PRIMARY · `DaVinciResolveScript.pyi` served by the Resolve Studio MCP on the
production Mac, read 2026-10-27]:

- **The burn is a render setting.** `RenderSettings` documents `ExportSubtitle` (bool) and `SubtitleFormat`:
  `'BurnIn'`, `'EmbeddedCaptions'` or `'SeparateFile'`. This file's earlier line, "no burn-in toggle via any API", is
  wrong and is withdrawn. An accepted key is still not a burned caption: a community measurement on 19.1.3.7 found no
  subtitles in the output. So `srt_qa.py burned <job> --render <file> --plate <the PICTURE_ONLY render>` compares
  the delivery render with the same timeline rendered captions-off, at every cue: something drawn there, inside the
  format's safe box, or a FAIL that names the cue.
- **The `.srt` import is undocumented, not impossible.** `MediaPool.ImportMedia` takes file paths;
  `AppendToTimeline` takes `trackIndex`, `recordFrame`, `startFrame` and `endFrame`. Whether an `.srt` imports that
  way and lands on a Subtitle track is not in the documentation. `PLACE_SUBTITLES` tries it and reads every cue back;
  it has **not yet run live**. File ▸ Import ▸ Subtitle stays the one-step fallback.
- **Still no subtitle text, timing or style call.** Nothing gets or sets a subtitle's words, its in and out, or its
  look, so the track's style is set by hand once per project, and the words come from the `.srt`.
- **Text+ is reachable.** `TimelineItem.GetFusionCompByIndex(1)` → the comp's TextPlus tool →
  `SetInput("StyledText", …)` and `GetInput` to read it back. `FUSION_TITLE_SPIKE` proves one template on a scratch
  timeline; it has **not yet run live** on the production Mac either.

**⚡ What 21.1.2 adds** [PRIMARY · the 21.1.2 stubs served by the Resolve Studio MCP, read 2026-10-29; each one **[stub]**
until the live test in the author's research notes §7 measures it, then **[measured 21.1.2, <date>]**]:
- `TimelineItem.SetPosition({trackIndex, startFrame})` and `Timeline.MoveItems(items, position)` — a title can be
  moved between video tracks. This is what lets the insert land on a **scratch top track** with everything else
  locked (the measured 21.1.1 behaviour) and then go **down** onto its named track: the text track no longer has to be
  on top, so the plugin's own `TRACK_LAYOUT` (Picture · Graphics · Titles · Disclosure · Supers) works. On a Resolve
  older than 21.1.2 the console says so and keeps the old rule (place the text tracks bottom-up). [stub — L1-a]
- `Timeline.ExportFrame(offset, {outputType: 'file', filePath})` and `TimelineItem.ExportFrame` — Resolve's own still
  at a frame, with no playhead move and no dependence on which page or Space Resolve shows. Every placed title gets
  one; the options are reviewed on them. [stub — L1-c]
- `TimelineItem.ImportFusionComp(path)`, `GetFusionCompNameList`, `LoadFusionCompByName`, `DeleteFusionCompByName` — the
  generated comp goes onto a stock Text+ with no install at all (the stock comp is deleted after: it is not the last).
  [stub — L1-h]
- `fusion.InstallFile(.drfx, quiet)` and `fusion.FontManager().GetFontList()` / `AddFont(file)` — the templates and the
  brand's faces installed by script. Whether either applies without a restart is unmeasured (L1-e, L1-f): route auto
  imports when the name is not listed, and a face `AddFont` cannot make appear is the one manual step, named.
- `TimelineItem.SetLeftOffset` / `SetRightOffset` (a trim without re-inserting) and `SetFades` (linear, so not used for
  the card's eased fades). [stub — L1-b] Once `SetRightOffset` is measured, "the API has no trim call" (the 2.44 lessons)
  is superseded.
- `TimelineItem.AddEffect(category, id)`, `GetEffects`, `Effect.GetFusionComp()` and `Resolve.GetEffectsList(mediaType)` —
  the installed effects by id (§ The installed library, under Transitions). **No call sets an OFX parameter.**

### The generated titles — `fusion_titles.py` (v2.45)

The native route used to lose to the outside one because it could not make the approved look: PLACE_TITLES wrote
static Text+ inputs only (no entrance, no exit, no plate, the weight never a Style — a Poppins 700 title came out
Regular), and "the brand template keyed once" was a manual job nobody did (the author's research notes
§1). Now the template is written from the card, every time:
- **One Fusion macro per kind** (`07-edit/titles/fusion/cine-<job>-<kind>-<fmt>-<card sha8>.setting`), the same graph as a
  `.comp`, a `.drfx` bundle and the manifest `07-edit/titles/fusion/templates.json` (names, sha256 of each file, the
  card's sha256, the fps, the tool names,
  the motion in frames). A name carries the card's hash, so a template from an older card can never be picked up;
  `fusion_titles.py check` refuses a stale or hand-edited one, and `native.py console` rebuilds before it splices.
- **The graph:** `TT_Page` (transparent, or the end card's opaque page) · `TT_Main` TextPlus (the face and its Style, the
  style frame's Size for the kind, the ink, CharacterSpacing 1 + tracking, the alignment and Center, a plate kind's
  `colors.plate` on element 3) · one TextPlus per kit field (`was`, `url`, `label` …, on the companion face) · `TT_Move`
  (Blend and Center.Y keyed) · `TT_Fold` (a TimeStretcher). `CustomData.cine` on TT_Main carries the card's hash: the
  console reads it back after the insert, so what Resolve placed is known, not assumed.
- **The motion is exact and cannot overshoot.** A Fusion spline is a cubic Bézier in (time, value), as a CSS
  cubic-bezier is: the handles are `(t0 + x1·Δt, v0 + y1·Δv)` and `(t0 + x2·Δt, v0 + y2·Δv)`, and with y in [0, 1] (the
  card lint, C2) no handle leaves its segment. Every spline is keyed at frame 0 (found on an accessories brand's ad job). At 24 fps the ads
  card's fade-rise 450 ms keys at 10.8 frames and its 250 ms fade runs 6.
- **The fold:** `SourceTime = iif(time < comp.RenderEnd - X, min(time, h), x0 + time - (comp.RenderEnd - X))` — the
  entrance from frame 0, the rest held, the exit over the clip's last X frames whatever its length. Whether
  `comp.RenderEnd` is the clip's last frame inside a Resolve title is the first live probe (L1-d); the console reads
  `COMPN_RenderEnd` back and stops a row where it is not.
- **Not made natively yet** (each a WARN in `title_card.py titles`, naming what the native title does instead):
  per-word and mask-reveal entrances, the stagger, a stat's count, the one-word highlighter, the underline. A look that
  needs them is the owner's call, recorded as their reason before anything renders outside.
- **Positions** come from the style frame (`POSITION_Y`, `FIT_EM_PER_SIZE` — [assumed]) until a calibration measured in
  Resolve exists (fusion-calibration.json in assets/, written only by the live test L1-i — not built yet); the manifest
  says which.

**⛔ The refusals that hold it** (v2.45; 2026-10-29: *"It keeps making mp4s which it imports"* — a supplement ad job's
six titles were HyperFrames movies imported onto V2 while their specs read as made in Resolve):
`title_card.py titles`/`check` refuse a Resolve spec with a movie beside it (`<id>.mov`, `<id>_*.mov`, `<id>.optN.mov`,
naming what made it); `approve titles` and `approve export` refuse a title-folder movie on the **timeline** (the dump
now carries each item's media file), and export wants a dump made after the newest delivery render; `gate.py` and
`shell_gate.py` refuse the import and the outside render themselves (see SKILL.md). When a title cannot be placed
by computer control (or its read-back disagrees with the spec), **stop and report that row** — never render the
title elsewhere to get past it.

**Route by who owns the timing** still holds. On routes 1 and 2 the captions live on the timeline, so the editor's
re-time *is* the timing. Route 3's `batch` reason only holds where the timeline was machine-assembled and timing =
plan; pointed at a hand-edited cut, it produces captions that drift against the edit.

### The conform bridge — for route 3 only

When a reason sends a hand-edited cut's captions outside Resolve (a Mode D re-format with no timeline is the usual
one), the edit's clip positions can still be read: paste `resolve-production-console.py` with
`DUMP_TIMELINE_JSON = True` (writes `07-edit/timeline-dump.json`: every clip's real start and duration in seconds)
→ re-time the caption cues against the dumped VO and clip positions → then `build_captions.py --reason …` burns each
delivery format from the *actual* cut. The dump toggle prints a read-back check; **confirm it once on a live
Resolve before relying on it in a delivery chain.** (Automating the retime — `build_srt.py --conform
timeline-dump.json` — is designed, on the `scripts/README.md` roadmap, not built.)

**`build_captions.py` is verified working** (2026-08-28, device VM): styled plate, per-format margins read from
`assets/delivery-formats.json`, a `--disclosure` line pinned top-of-frame from frame one at caption prominence,
Romanian diacritics rendered in-face — confirmed by extracting and inspecting a burned frame, not by the exit code.
Three built-in refusals: no burn without a reason (C7), no burn onto a file that already looks burned, and no
unknown format preset.

**Rules that hold on every route:**
- The text source is the **locked script** via `build_srt.py` — never a fresh transcription (and on
  a Path B native-audio clip, only after the verbatim word check).
- **Captions burn per format, after the fork.** In Resolve: one timeline per format, duplicated after lock, each
  burning its own Subtitle track inside its own safe box at its own render. Route 3: a captionless master, burned per
  format.
- The caption QA card (`typography-and-captions.md` §9) runs **on the output**: `srt_qa.py burned` finds every cue
  in the pixels, and someone still extracts a frame on the brightest background a caption sits on and looks at it.
- Type tokens come from the client profile's caption block; the face must pass the diacritic check.

## Captions & on-screen TEXT (sound-off) — the Resolve mechanics

- **Burn in captions (target language)** for the dialogue: Feed placements are still often watched
  muted, and captions carry accessibility. Correct accents/diacritics. Mix for sound-on viewing.

  ⚠️ **SUPERSEDES IN PLACE** (2026-10-21) — previously: "Most short-form is watched muted". Meta reports
  80 % of Reels viewed with sound on (Aug 2022); the muted-Feed figure dates from February 2016 (the
  opening note of `typography-and-captions.md` carries the sources).
- **Captions are the only on-screen text by default.** No TEXT overlay windows and no logo watermark
  unless the client profile explicitly asks for them; every title — a hero line, a stat, a price, an end
  card — is one the project's approved title card names (`typography-and-captions.md` §6c; house rule
  C3, 2026-10-26: *"Yes, the card is the permission"*). Scripts and shotlists may still
  carry `TEXT:` lines as a record of the approved format — they are **not rendered** unless a title spec
  the card permits carries them. Brand presence
  comes from *in-world* branding composited onto the start frame before generation. The one thing that
  always gets burnt in regardless: any **required disclosure** (dramatization, AI, material connection)
  — see `compliance.md` §2.
- In Resolve: a **Subtitle track** (an **SRT** built from the *locked* VO text, never a fresh auto-transcription,
  placed by `PLACE_SUBTITLES` or File ▸ Import ▸ Subtitle — a media import, so the API may do it); **Text+**
  for the animated title and CTA, placed and edited by computer control (rule 8). Burn subtitles in at the render (`render-mp4.py BURN_SUBTITLES = True`, or Deliver ▸ Advanced
  Settings ▸ Subtitles ▸ Burn into video), then `srt_qa.py burned` on the file.
- Large, high-contrast type; keep it inside the **safe zone** — top ~35% for the title/hook, clear of
  the platform's bottom (~15%) and right-rail UI.
- **Subtitles/captions invisible in the exported MP4 even though they look right in the Resolve
  viewer — the #1 cause is the Deliver-page burn-in setting, not the subtitle track itself.** A
  Subtitle track only shows up in playback inside Resolve by default; it does **not** automatically
  get composited into the rendered file. Before re-rendering, check, in order: (1) the subtitle
  track's **eye/visibility toggle** in the track header is ON; (2) on the **Deliver** page, expand
  **Advanced Settings** in the render-settings panel and find the **Subtitles** section — it must be
  set to **export/burn subtitles into the video** (not "off" and not a sidecar/embedded-track-only
  mode if the goal is captions visible in any player); (3) if multiple subtitle tracks exist, the
  correct one is selected there. This setting lives in the render/delivery UI, not in the timeline —
  don't confuse it with the subtitle *content* being UI-only (next bullet); this is a separate export
  toggle that's easy to miss because nothing about the timeline itself looks wrong. Re-render after
  fixing it — a prior render made before this was set has to be redone, there's no partial fix.
  **If a client profile explicitly does render Text+ title cards on a video track** (not a Subtitle track), they
  composite in automatically like any other video element — if those aren't showing, the cause is
  different: check the track's enable toggle, the clip's own Enable/Disable state, and that no
  opaque track above it is covering it, rather than the subtitle burn-in setting above.
- **⚠ A subtitle's text, timing and style are UI-only — confirmed, even via the Resolve MCP.**
  The Resolve scripting API (which every Resolve MCP, including the one inside Resolve 21.1, is built on — 21.1's CHANGELOG adds
  no subtitle call) exposes
  **no method to get/set subtitle text, per-item start/end/duration, or any subtitle styling**. The `.srt`
  import has **no documented call**: `PLACE_SUBTITLES` tries ImportMedia + AppendToTimeline and reads every cue back
  (not yet run live), and File ▸ Import ▸ Subtitle is the one-step fallback. The burn is a render setting
  (`SubtitleFormat: 'BurnIn'`, § Captions and titles above). The one scriptable subtitle call
  (`Timeline.CreateSubtitlesFromAudio`) only runs Resolve's own auto-transcription engine, which is
  useless here (it can't be fed the locked VO text and there's no alternate-provider param) — never
  use it on a locked-audio client, it will reword the dialogue (`gate.py` denies a `run_script` that calls it). **Practical alternative, automated:**
  `scripts/build_srt.py` generates that proper `.srt` for you — it parses the locked SCRIPT.md with
  the exact same regexes `estimate_duration.py` uses (never a fresh transcription of the audio), and
  times each line using the same shot-ordering/offset logic `build_fcpxml.py` computes for the
  assembled timeline, plus the matching `05-voice/` file's real duration:
  ```
  python3 scripts/build_srt.py --project <that dir> --script 01-script/SCRIPT-SLUG-v3.md --slug acme-spring-tuneup
  # → 08-captions/acme-spring-tuneup.srt
  ```
  It's defensive about the one guess it has to make (mapping a script scene to a `<SHOT>` filename
  token): every computed token is checked against the clips actually filed in `03-clips/`, and any
  line that doesn't match is reported and **skipped**, never guessed into a wrong position — fix
  those with `--shot-map` if the shotlist used different numbering than the script's scene order.
  **Upgrade path — word-level timing:** the TTS API returns character/word timestamps with each
  generated line; `build_srt.py` currently times captions from line durations. Wiring the timestamp
  JSON in (stored beside the VO file at generation time) upgrades captions from line-accurate to
  word-accurate for free — worth doing before any client asks for word-highlight caption styles,
  which cannot be built on line timings at all.
  Place the resulting `.srt` with `native.py console <job> --srt …` (`PLACE_SUBTITLES`), or by hand with
  **File ▸ Import ▸ Subtitle** when the probe does not take. **Titles are a different path** (the card's
  generated Fusion title, placed and its words typed by computer control, then read back by the API — § Captions
  and titles route 2) — don't confuse the two when planning what an agent can automate.

## ⚠ Resolve 21.1 (2026-09-08) — Python scripting moved to Studio, and a native MCP server

**Re-checked 2026-09-14 against Blackmagic's own files on the production Mac** — the scripting
CHANGELOG and `README.md` in `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/`,
and the server inside the app bundle — **and live against Studio 21.1.0.14.** The first version of this
note (same day, from press coverage alone) is superseded.

**What Blackmagic says:**
- *"Python 2 is no longer supported."* · *"Built-in Python support for script menu and console
  scripts."* · *"Overloaded function signatures are deprecated."* [PRIMARY · CHANGELOG § 21.1]
- *"Advanced scripting now requires DaVinci Resolve Studio"* [PRIMARY wording · SECONDARY channel — the
  release notes as reprinted by Newsshooter, 2026-09-07]; and in prose, *"We have moved the ability to
  script in Python to the Studio version"* [Blackmagic, quoted by ProVideo Coalition and Puget Systems].
  On Blackmagic's download list the scripting and AI-assistant items sit on the **Studio** 21.1 entry,
  not the free one [PRIMARY · blackmagicdesign.com downloads.json · read 2026-09-14].
- The Claude extension that ships with the MCP server states it needs Resolve **Studio** [PRIMARY · the
  shipped `DaVinciResolve.mcpb` manifest].

**What that settles, and what it does not:**

| Route | Studio 21.1 | FREE 21.1 |
|---|---|---|
| the MCP inside Resolve (`run_script`) | ✅ measured 2026-09-14 — both skill scripts' calls run | ⛔ assume not — its extension says Studio |
| `resolve_selftest.py` (external `DaVinciResolveScript`) | ✅ | ⛔ Studio on every reading |
| `resolve-production-console.py` · `render-mp4.py` pasted into the console | ✅ | ⛔ **does not run** [CLIENT · stated 2026-09-14] |

⛔ **So on the free edition there is no automation route into Resolve at all** — no MCP, no external
scripting, no console Python. **The Resolve stage of this skill is Studio-only from 21.1.** A client or
editor on free Resolve gets `build_fcpxml.py`'s interchange file, `build_srt.py`'s captions and a
hand-built edit; nothing here should promise them a scripted timeline.

**The MCP server stopped being a design question on 2026-09-14** — it was verified by read-back and the
skill was rebuilt around it (§ "Automating DaVinci Resolve via MCP" below, `environments.md` §3). What
21.1 added that this skill now uses or rules on:
- `TimelineItem.AddTransition` — measured (§ "Applying transitions").
- `TimelineItem.Get/SetFades` — measured, reads back. `Get/SetSpeed` — `GetSpeed` returned False on a
  generator; untested on media.
- `Timeline.NormalizeAudioLevel` — clip-level normalisation; `GetNormalizeAudioModes()` lists EBU R128,
  ITU-R BS.1770-4, ATSC A/85, YouTube and others [MEASURED · 2026-09-14]. Its loudness semantics are
  undocumented, so it is a mix aid, never the evidence: `export_qc.py` measures the rendered file.
- ⛔ The AI Speech Generator (`Project.GenerateSpeech`, since 21.0) is **denied by `gate.py`** inside
  `run_script`: a voice made in the NLE skips stage 6 — an approved line, a chosen voice, rights held.

⛔ The MCP's own `get_whats_new` tool stops at 21.0.4 while reporting "up to date with DaVinci Resolve
21.1" [MEASURED] — read the CHANGELOG instead.

## Getting client notes back onto the timeline

Resolve once had a native Frame.io Deliver-page preset that synced comments back as a dedicated
marker type. **It is V3-era and Resolve 16/17 Studio only; Frame.io V4 does not list Resolve as a
supported integration at all — and ⛔ in Resolve 21 the whole Frame.io chapter is gone from the
manual and there is no Frame.io preset on the Deliver page** (`review-and-approval.md` §5b). So on a
2026 account: upload is manual (or scripted against the API), and notes come back as a file, not a
sync.

⛔ **Two presets DO still sync comments back automatically, and both are on the Resolve 21 Deliver
page: `Dropbox or Dropbox Replay` and `Presentations`.** If the round trip matters more than the
reviewer's experience — and at 30–50 videos a month it does — pick one of those and the whole CSV→EDL
paragraph below stops applying. `review-and-approval.md` §5b has the comparison and the reasons
Replay is still the pipeline while Presentations is the second channel.

The working path — export the platform's comments as CSV (filtered to the one asset; **replies never
appear in filters, so they never reach the export**), convert with
`scripts/frameio_comments_to_edl.py`, then **Media Pool → right-click the timeline → Timelines →
Import → Timeline Markers from EDL** ⚠ (that command is documented by Frame.io, **not** by
Blackmagic — the R21 manual documents marker *export* to EDL and carries no import section at all,
so verify it once in your build: `review-and-approval.md` §5b). Offset matters: comment timecodes are file-relative, your
timeline probably starts at `01:00:00:00`, and markers outside the timeline's range import as
nothing, silently — so check the first marker landed where you expect. Dropbox Replay is the one
tool that still round-trips comments bidirectionally with Resolve Studio if that matters more than a
branded review page; the comparison is in `review-and-approval.md` §3.

## Export (Deliver page)

**Deliver** ▸ **the client's delivery format** — aspect, resolution and frame rate from
`clients/<brand>.md` §5 against the presets in `assets/delivery-formats.json`, H.264/HEVC, fps
matching the conformed clips, `<SLUG>-vN-final_<token>.mp4` (or **Quick Export**). There is no house
format; see `delivery-format.md`. Do the ✅ Branding Check (`pm-workflow.md`) before you call it done.

`scripts/render-mp4.py` — sent through the Resolve MCP's `run_script` or pasted into Console ▸ Py3 —
checks the timeline's frame rate against CONFIG, **saves the named project**, sets
format/codec/resolution/frame rate/48 kHz/destination by ID, replaces only **its own** earlier job,
**adds the job to the render queue — it does not start the render** — and reads the queued job back,
removing it again if it does not match. That's deliberate: it lets you eyeball the queued job
(resolution, destination, filename, in/out, and the subtitle burn-in, which `BURN_SUBTITLES` sets and
`srt_qa.py burned` checks in the pixels — see "Captions and titles" above) before committing render time. Press **Render All** / **Start Render**
yourself once it looks right; a script that starts a render is denied by `gate.py`.

⛔ **Three things it got wrong until 2026-09-14:** it deleted **every** job in the render queue,
including jobs an editor had queued by hand for other timelines; it defaulted to 1080×1920 and set no
frame rate at all; and it touched render settings on whatever project was open, unsaved — the step
where Resolve has aborted five times on the production Mac (`environments.md` §3). It still refuses to
run while `OUTPUT_FOLDER`/`OUTPUT_FILENAME` hold the `REPLACE-WITH-...` placeholder — an earlier
unedited run created a folder named after the placeholder on disk.

**Burn captions per delivery format, never before the format fork.** A burnt-in caption bakes its
position; a 9:16 master with baked captions cannot be re-cropped to 4:5 or 16:9 without the captions
sitting wrong or cropping off (`delivery-format.md` §2, `modes/repurpose.md`). The subtitle track
stays live on the timeline; the burn happens at each format's own export, positioned inside **that
format's** safe zones.

**Once it's rendered, QC it before it goes to the client** — `scripts/export_qc.py` checks the
actual file against spec instead of eyeballing it: resolution, frame rate, duration (all via
ffprobe), plus a real integrated-loudness/true-peak measurement (`ffmpeg loudnorm` in single-pass
measure mode — no re-encode) against the −14 LUFS / −1 dBTP targets above.
```
python3 scripts/export_qc.py 10-export/<SLUG>-vN-final.mp4 --target-duration 58
# --format names a preset in assets/delivery-formats.json (vertical-1080, landscape-1080,
#   feed-4x5, broadcast-eu-1080 …); it sets resolution, fps and the loudness target together
```
Prints a PASS/FAIL per check and exits non-zero if anything fails — safe to treat as a hard gate
before the ✅ Branding Check hand-off, not just an FYI.
`--report` writes `<file>.qc.txt` naming the file's sha256, and **`gate.py approve export` refuses unless
every file in `10-export/` carries a passing report about its exact bytes** (2026-09-14) — until then
the gate told you to run the QC and never checked that anyone had.

## Automating DaVinci Resolve via MCP (the fast path)

**The MCP is the one that ships inside DaVinci Resolve Studio 21.1** — `ResolveMCP` in the app bundle,
tools `mcp__DaVinci_Resolve__*`. Setup, the 14 tools, the gate and the measured hazards are
`environments.md` §3; this section is what the edit stage does with it. ⛔ The community server this
section used to describe (`samuelgursky/davinci-resolve-mcp`) was removed from the production Mac on
2026-09-14. Its compound tools, delivery targets and confirm tokens do not exist in the official
server, which exposes the scripting API as one tool — `run_script` — and the guards that server carried
now live in this skill: `gate.py` (what may run), `render-mp4.py` (how a render is queued), and the
read-backs below.

### What runs through the API, and what is done by computer control (v2.49, house rules 8 and 9)

**Rule 8 — Fusion, Fairlight and native titles: always computer control, never the scripting API.** Owner,
2026-11-05: *"It fails all the time."* Making, adding or editing a native title (Text+, a Fusion title), any
Fusion comp work, and any Fairlight work is done by **driving Resolve's own interface with computer use**,
then verified on screen. The API stays for:
- reads (the timeline dump, a title's words and position read back, the markers, the render queue);
- project and timeline setup (tracks, track names, timelines);
- media import;
- markers;
- render-queue preparation (`render-mp4.py` queues; the owner starts every render).

**`gate.py` denies** a Resolve `run_script` (or `run_script_unsafe`) that **writes** to Fusion, Fairlight or a
native title — a deny, not an ask; no `allow resolve` allowance covers it. It reads the script's live code:
- **denied:** a Fusion comp made, imported, loaded, renamed or deleted (`AddFusionComp`, `ImportFusionComp`, …);
  a title inserted (`InsertFusionTitleIntoTimeline`, `InsertTitleIntoTimeline`) or a template installed
  (`InstallFile`); any call other than a `Get…`/`Find…` read on a Fusion object, or an assignment to one
  (`tool.StyledText = …`, `SetInput`, `AddTool`, `Lock`, `AddFont`); a Fusion effect or transition added;
  Fairlight calls (`ApplyFairlightPresetToCurrentTimeline`, `InsertAudioToCurrentTrackAtPlayhead`,
  `SetVoiceIsolationState`);
- **open:** reads of all of it (a title's words and font read back, the comp list, the Loaders after an
  import), markers, clip fades, track setup, media import, the Subtitle-track `.srt`;
- a console toggle set `False`, a loop over an empty plan and a helper nothing live calls are not counted, so
  the shipped `resolve-production-console.py` passes with its toggles as shipped. `native.py console` writes a
  copy that places no title (`--owner-paste` writes the old placing copy for the owner to paste into
  Workspace ▸ Console themselves; the gate refuses it through `run_script`).

**Rule 9 — all SFX and edits are done in Resolve.** No ffmpeg or Python mixing, conforming or cutting of the
deliverable's sound or picture outside Resolve. The Python tools **measure and propose**: markers, EDLs,
timing plans, levels, QA. The edit and the SFX placement happen in Resolve, Fairlight by computer control.
`sfx_conform.py` and `loop_music_to_length.py` are planning and measuring tools now; their renders are proofs
to listen to, **not deliverable audio** (§7f).

**One Resolve script per task, ending with its own verification stills** (production lessons, 2026-11-05).
One approval per small script was too many prompts; batch the task's API work into one script, under one
`gate.py allow resolve` allowance, and end it with stills of the result exported at full size. A task done
by computer control ends the same way: a full-size still of the result, read before calling it done.

**Check where comps break** (production lessons, 2026-11-05):
- look at the **first and the last frame** of every comp and every new timeline, at full size;
- after any timeline duplicate or comp import, **re-check the Loaders and the media ranges**;
- verify the **real output**, never a Fusion viewer or an Edit-page still: a viewer can show an old frame, and
  a still is not a render. The owner starts renders, so these checks are what stands between a fix and their
  first render of it.

The comp checks above are by eye. On the render, **`export_qc.py` reads every frame** (v2.49) and FAILs a
one-frame flash, the first and last frames included:
- **first / last frame** — frame 0 (or the last) unlike its neighbour in many places while the next pair nearly
  agrees: the lockup on frame 0 before its fade-in, the case that reached the owner;
- **one-frame shot** — a whole frame unlike both neighbours, steady either side: a stray frame left at a cut;
- **keyframe flash** — a region that shows its end state for one frame mid-cut and then fades in (or the end
  state back on a fade-out's last frame).

A one-frame spike that never comes back (fast motion, or a small stray graphic) only **warns**, with the frames
to look at. A flash that is meant (a strobe, a camera flash) passes with `--allow-flash FRAME,…`, named in the
report. The thresholds are assumed; on eleven real cuts and clips (13,042 frames) the FAIL signatures fired
zero times. A render that has not been through it has not been checked for flashes.

Edit stage → what runs:

| Step | Through `run_script` |
|---|---|
| Import the filed clips + VO into a bin | `resolve.GetMediaStorage().AddItemListToMediaPool([paths])` — Resolve reads the files; the sandbox never does |
| Build the rough cut (clips in scene order) | `MediaPool.CreateEmptyTimeline` → `AppendToTimeline([{"mediaPoolItem", "startFrame", "endFrame", "recordFrame", "trackIndex"}])` — `recordFrame` is ABSOLUTE (gotchas below); read every item's `GetStart()`/`GetDuration()` back |
| V2, the A1–A6 lanes, beat markers | `resolve-production-console.py` — measured: `AddTrack`, `SetTrackName` (reads back), `AddMarker` (frames from the timeline start) |
| Dissolves at the planned joins | `TimelineItem.AddTransition` — measured on 21.1 (§ "Applying transitions"); pack assets by hand |
| What is installed (titles, transitions, generators, effects, OFX) | `resolve-production-console.py` `INVENTORY_TEMPLATES` — the Console or `run_script_unsafe` only (it reads folders); then `motion_qa.py inventory` |
| Can a title template's text be set by script? | v2.49: no longer asked. Titles are placed and edited by computer control (rule 8, above); the API reads a placed title's words back. `FUSION_TITLE_SPIKE` stays in the console as a read-only probe — not yet run live |
| Fades | `TimelineItem.SetFades({"FadeIn": n, "FadeOut": n})` — measured, reads back, linear. A fade inside a Fusion comp or title is computer control (rule 8): a script-made one keyed a frame-0 flash (gotchas below) |
| The final cut's real timings | `resolve-production-console.py` `DUMP_TIMELINE_JSON` → `result` → `07-edit/timeline-dump.json` (items carry `type` — a transition is an item) |
| Captions | ⚠ **no subtitle import and no subtitle text API** — `build_srt.py` builds the .srt, the import is by hand; `CreateSubtitlesFromAudio` is ⛔ denied by the gate |
| Voice | ⛔ `GenerateSpeech` is denied by the gate — stage 6 owns voice |
| Export | `render-mp4.py` (saves, queues, never starts — a scripted start is ⛔ denied) → a person presses Render → `export_qc.py --report` → `gate.py approve export` |
| Import an interchange file | `MediaPool.ImportTimelineFromFile(path, {"timelineName": <unique>})` for `build_fcpxml.py`'s file — a reused `timelineName` makes a later import return None silently [COMMUNITY · measured on 19.1.3.7] |

The rows marked *measured* ran live on 2026-09-14. Media import, `AppendToTimeline` and
`ImportTimelineFromFile` have **not** been run through the MCP on this Mac yet — the first time, verify
by read-back before trusting the row.

**Two ways to get to a rough cut:** (a) **native, preferred** — build the timeline through `run_script`
directly; (b) **interchange** — `scripts/build_fcpxml.py` emits an FCPXML that `ImportTimelineFromFile`
(or File ▸ Import ▸ Timeline) takes. Use (a) when the MCP is connected; (b) as the portable fallback.

**From a cut plan (3.0.0).** `scripts/cut_plan.py plan <job>` proposes each select's IN and OUT from its measured
motion (`motion_qa.py clip` first) and the prompt's `cut:` — IN two frames before the onset and never inside the lead,
OUT at IN + `cut:`, the slack as tail; an action longer than `cut:` is UNRESOLVED until the person chooses (a recorded
choice clears nothing until a new take, a new `cut:` or a recorded trim is what CUTS.json holds). Then
`scripts/timeline_export.py <job>` writes the same cut as FCPXML 1.10 (Resolve, Final Cut Pro) and xmeml v5 (Premiere
Pro, experimental): integer frames at a rational rate, handles as unused source, the VO trimmed to its shot, no music
(Resolve rebuilds it in Fairlight from REBUILD.json). Measured on Resolve Studio 21.1.2, 2026-11-15: both files import
frame-exact at 23.976; Resolve imported none of the clip markers, so the notes live in `07-edit/CUTS.md`.

**`run_script` constraints that shape every call** [MEASURED · 2026-09-14]: a fresh process per call —
nothing carries over; 10 s default and 60 s max timeout, so pass `timeout` for anything long and poll
across calls rather than looping inside one; no `os` and no `open`, so paths go INTO Resolve's calls and
data comes OUT through `result`. Use `run_script_unsafe` only when the OS is the point — the gate asks
every time, and a script that times out keeps running inside the server.

### When you're an agent with no path to the editor's machine — hand over the script instead

The Resolve MCP only works on the same machine as a running Resolve Studio. A cloud-hosted agent session
**cannot reach it**, even with Resolve open in front of the user. That is a real, recurring situation —
don't present it as a dead end: hand the user the same two scripts, CONFIG filled in, to paste into
Workspace ▸ Console ▸ Py3. They are the files the MCP runs, so the result is the same timeline; the only
cost is a paste instead of a call.

**Known gotchas when scripting the API (MCP or console — the same calls):**
- **`ProjectManager.SaveProject()`, not `Project.SaveProject()`** — on the Project object that attribute
  is `None` (measured 2026-09-14), so calling it raises `TypeError: 'NoneType' object is not callable`.
  And name the project before you save it.
- **Creating a timeline in an unsaved project auto-saves it** as `Untitled Project <date>_<time>`
  (measured 2026-09-14) — a "scratch" test leaves a real project behind.
- **`recordFrame` (in `AppendToTimeline` clipInfo) is ABSOLUTE; `AddMarker`'s frame is RELATIVE.** A
  fresh timeline starts at frame 86400 (01:00:00:00): add `timeline.GetStartFrame()` to a recordFrame,
  never to a marker. Skip it and a clip lands an hour before the timeline begins, with the call
  reporting success; add it to a marker and the marker lands an hour past the end — `AddMarker` returns
  True (measured 2026-09-14).
- **Verify structure, not return values.** A True from `AppendToTimeline`, `AddMarker`,
  `SetRenderSettings` or `AddRenderJob` means the API accepted the call, not that the result is right.
  Read back `GetStart()`/`GetDuration()`, `GetMarkers()`, `GetRenderJobList()` and print PASS/MISMATCH —
  the same discipline as reviewing a generated clip before accepting it (`ai-generation.md` → "Known
  failure guardrails").
- **Render settings are state, not a request.** There is no `GetRenderSettings`; `SetRenderSettings`
  changes the keys you pass and leaves the rest as the Deliver page holds them, and render calls switch
  Resolve to the Deliver page (measured). Set every key you care about, then read the queued job back.
- **Resolve objects answer any attribute name** — with `None` — so `hasattr()` is True for methods that
  do not exist. Search the stubs (`search_scripting_api`), or catch `'NoneType' object is not callable`.
- `Timeline.DeleteClips([items], ripple_bool)` removes a misplaced item before re-placing it — the basis
  of any idempotent "fix this one clip" script (the gate asks before it runs).
- **Resolve traps from a real job** (production lessons, studio-supplied, 2026-11-05) — each one a reason
  for rule 8 and for the full-size checks above:
  - **Inserting a title rippled V1.** Lock every track you are not editing first, and read the cut back.
  - **Importing a Fusion comp quietly turns its Loaders into empty MediaIns** (hit twice). After any comp
    import, open the comp and check every input is connected to real media.
  - **Duplicating a timeline can shift a comp's media range by a frame.** An end card's background moved one
    frame and the render failed on one machine. Re-check the ranges after every duplicate.
  - **Connecting nodes through the API cross-wired image inputs.** Wire a comp by hand, by computer control.
  - **A bitmap mask with no channel set blocks everything.** Set the channel, then look at the output, not
    the mask.
  - **A script-made fade keys the current value at the current time.** The card showed the full lockup on
    frame 0 for one frame. Check frame 0 and the last frame of every comp at full size.

**Locked-script clients:** Resolve automation only touches the *edit / mix / QC / export* — it never
changes the words. Build captions from the **approved VO transcript** (the locked lines), never a fresh
auto-transcription that could reword them.

## Quick edit checklist

- [ ] Dialogue/A-roll on V1, all b-roll on a separate V2 track (never intercut into V1)
- [ ] User picked the soundtrack from `creative/videos/music/` (never an autonomous default)
- [ ] The music fitted to the locked cut (`music_fit.py` hits init → fit → rebuild), the cut never moved
      without an approved nudge, and rebuilt in Resolve from the original: the segments placed on A5, the
      crossfades and the end fade made in Fairlight by computer control (REBUILD.md), the music stem exported
      into `09-qa/mix/`. The render is a preview, never on the timeline. Or a loop on the phrase lines planned
      with `loop_music_to_length.py` and made in Resolve (rule 9: its render is a proof, not the bed)
- [ ] The composer's brief and spotting note filled; anything composed or generated has its record, the
      owner's motif edit, consent before generation, its bake-off, and the element sheet (`composer.py check`)
- [ ] BPM noted; sparse markers from the real track (phrases, must-hits), not every beat
- [ ] Cut on action; the beat for 2–4 hits (the reveal, the landing, the button), not every cut
- [ ] Cut on action; pacing curve; ~3s hold on the button, then out (no end card by default)
- [ ] Handles exist wherever a dissolve/transition is planned (clips generated 1–2s past the cut,
      not trimmed exactly to it) **and** actually exposed in the assembled timeline (`--durations`
      passed to `build_fcpxml.py`, handle-exposure summary checked) — otherwise that join stays a
      hard cut
- [ ] Every line synced, **verified by listening to an A/B with the VO over picture** — not from a
      contact sheet; audio-driven clips left at their cut, silent clips cut to picture, B-roll covers the rest
- [ ] Embedded audio stripped/muted on any character clip that has a separate external VO
      (`strip_embedded_audio.py`) — never two voice sources live on one clip; B-roll keeps its native
      diegetic sound under the location's bed (§7d–§7e)
- [ ] Every SFX and edit made in Resolve; titles, Fusion and Fairlight work by computer control, checked on a
      full-size still and on the first and last frame of every comp (§ What runs through the API)
- [ ] ≥ one B-roll per dialogue clip used (ideally +2 available)
- [ ] −14 LUFS (the house value), music ducked under VO
- [ ] Captions (target language) made in Resolve and burned in — `srt_qa.py burned` PASS on the file — correct
      diacritics, in safe zones; any required disclosure burnt in from frame one at caption prominence
- [ ] Captions built from the locked script + real VO durations (`build_srt.py`), not a fresh
      transcription; every skipped line resolved (matched via `--shot-map` or the shotlist fixed)
- [ ] Export matches the client's delivery format — aspect, resolution, fps (Deliver ▸ queue the render job, verify
      settings incl. subtitle burn-in, then start it yourself)
- [ ] `export_qc.py` run on the final file and PASS before hand-off (resolution, fps, duration,
      loudness, true peak) — not just an eyeball check
