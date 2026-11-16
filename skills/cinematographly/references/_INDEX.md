# references/ — the registry

**What this file is for.** Reference files in one flat folder are not an architecture, they
are a pile with a table of contents. This is the registry: every reference is listed here exactly
once, with the **class** that says when it loads and the one sentence that says what it owns.

⛔ **A reference that is not in this table does not exist.** `scripts/skill_audit.py` fails on an
unlisted file, on a listed file that is missing, and on any file reachable from neither this index
nor `SKILL.md`. That is the whole point: *a skill that grows faster than its routing gets slower to
use*, and this is the brake.

---

## The three classes

| Class | Meaning | Budget discipline |
|---|---|---|
| **core** | Loaded at the start of essentially every job. Kept deliberately small | The always-loaded surface. `skill_audit.py --ceiling-core` gates it |
| **extended** | Loaded when the job reaches the stage that needs it, and not before | The large majority. Depth lives here and costs nothing until asked for |
| **never** | Consulted by a human, never routed into a working session | Archives, evals, further-reading |

**Why the split, given that context windows are now huge.** Not because the skill would not fit — it
would. Two reasons that survive a big window: **attention** (irrelevant material measurably degrades
accuracy; the honest expectation is that most of any loaded file is distractor for the task at hand)
and **cache hygiene** (a stable prefix is cheap on re-reads; a volatile one is not). Selective loading
is a quality discipline first and a cost discipline second.

---

## Core — the always-loaded surface

| File | Class | Loaded when | Owns |
|---|---|---|---|
| `production-runbook.md` | **core** | Every production job | ⚡ The timed route for one episode; the three-batch structure, the overlap window, tiered QA, and §7b the ~25-minute ONE-SHOT path |
| `series-parallel.md` | **core** | Every job with N ≥ 2 episodes — which is the normal case | ⚡ The series batch: fan-out, the accumulator, the freeze precondition, the join gate, and Amdahl's ceiling on all of it |
| `parallel-agents.md` | **core** | Every stage with independent units: research, drafts, critiques, shot prompts, continuity boards, take reviews, SFX spotting | ⚡ v2.50 — the plugin's seven agents, one unit each, dispatched side by side; the join by `fanout.py` (silence is a FAIL); what never runs in an agent (spend, approvals, Resolve, the browser) |
| `craft-cheatsheet.md` | **core** | Any craft decision | The short decision surface — story, shots, light, colour, rhythm — that defers to the deep files. ⚡ §3 carries the day/night × int/ext scenario matrix: fix the cell once and every shot in the batch inherits its light model |
| `delivery-format.md` | **core** | Any job that will be exported | Aspect, resolution, fps, duration, safe zones, loudness. The 1080p floor |

---

## Extended — by stage

### 1 · Decide what to make

| File | Class | Loaded when | Owns |
|---|---|---|---|
| `preproduction-research.md` | extended | Intake, before research starts | How much research a decision deserves; the six sourced brief fields; the four-tier depth ladder; the measured cost of over-researching |
| `ideation.md` | extended | Before anyone writes | Divergence, the concept, the kill tests |
| `persuasion-psychology.md` | extended | Choosing a hook or building an offer | Audience-first hooks, offer construction, the ethics gate |
| `hook-craft.md` | extended | Writing or scoring the first six seconds | ⚡ The sourced hook evidence: the concreteness curve that turns over, the gap's three legs, where "six seconds" and the "3-second rule" actually come from, brand placement, and the blacklist |
| `discovery-and-search.md` | extended | The video will be searched for, not only fed — captions, hashtags, and the eligibility gates | ⚡ What is DOCUMENTED about in-platform search: the caption is the index and the VO is not, the levers that are real, Google's Search Console platform properties, the watermark/originality gates, and the blacklist |
| `comedy-craft.md` | extended | A brief asks for humour, or for a mix of serious and light | ⚡ Why funniness is the wrong metric (absence of negative reaction is), relatedness as the switch for a considered purchase, the two earned timing numbers, substantive vs cosmetic variation, and why AI comedy fails at SELECTION |
| `script-craft.md` | extended | Writing lines that will be spoken | Spoken-line craft and the mechanical self-test · ⚡ §2d (v2.51) MEASURED BANDS from 39 screenplays, 38 interviews and 67 verbatim ads (`assets/script-bands.json`): dialogue lines about 6 words, sentences about 6 words; talking-head sentences about 16 words, soundbites 30–40 s; ads about 2.2 words a second, with 35–45 words in a 15 s spot and about 63 in a 30 s spot, and the CTA in the last eighth; the short-closer tell; `script_score.py` prints the bands and `--house` opts in to a line ceiling · ⚡ §7b (v2.49) scripts written in four passes — story logic, coverage, continuity, cut-down and read-aloud — only the last shown, with its checks; festival-short story patterns (HFF-07) |
| `script-format.md` | extended | Formatting the script | The house shape |
| `micro-drama.md` | extended | A short-drama episode or series — a micro-drama, an AI series, a cliffhanger episode | The vendor's four-part episode (hook on the peak, context with a swing every 20–30 s, escalation through opposite reactions, a cliffhanger that promises), the six-criterion story score as one kill test, cast and continuity, the house sheet, scenes into ≤30 s multi-shot clips plus inserts, cost, a series. Departs from the vendor on voice (Path A, not a repeated description), on the idea bank (none imported) and on the cut to black (the edit's) |
| `research-quality.md` | extended | A fact will decide money or compliance | Source tiers, refutation pass, decay — and ⚡ that a tier is not uniform across a source: the standing StudioBinder note (vocabulary citable, attributions not) · §5b ⚡ SUPERSESSION: a corrected claim names what it replaced and the replaced one carries the back-pointer, enforced by `skill_audit.py` check 11 — and what supersession is NOT (an open question, a scope, or a disagreement nobody can settle) |

### 2 · Decide how it looks

| File | Class | Loaded when | Owns |
|---|---|---|---|
| `cinematography-craft.md` | extended | A shot decision needs its reason | Lighting logic, lens language, movement, staging, composition — and what survives into a prompt. ⚡ §3.8 motion that is NOT boring — the five levers, only the fifth of which is a camera move — and the per-move ruling on the standard twelve · §3.9 the script-signal → move index (function picks the move; genre does not) · the five named portrait patterns and the nose shadow that proves you got one (§1.4) · frame-within-a-frame, the one composition control you can TYPE (§5.3) · the camera-height ladder and why the plain high angle is wrong in 9:16 (§5.4) · the measured vertical canvas, where exactly ONE third-line survives (§5.10) · frame tests F1–F24 · the source blacklist (§9.0) |
| `production-design.md` | extended | Dressing the frame | Room, set dressing, wardrobe, palette — and the two environment fields that were missing: the practical as an OBJECT in the noun list, and the near-plane object the camera shoots through |
| `character-and-props.md` | extended | Designing or holding a character | Silhouette, costume as characterisation, prop placement, consistency across shots · ⚡ §8.3g (v2.49) the sheets a scene clip binds: one per character state, locations on a neutral base, `prop:` approvals, look-alikes one colour each, the wardrobe and props sheet per scene, fixes toward the sheet |
| `brand-system.md` | extended | Holding a look across a series | Tokens, shot components, governance, drift audit |
| `style-transfer.md` | extended | "Make it feel like <director>" | Decomposing a style into parameters; why the name never goes in the prompt |
| `environments.md` | extended | Setting up, or the tooling is misbehaving | Where the skill runs — Claude Code vs Cowork vs the device VM; the Resolve hookup (v2.49: titles, Fusion and Fairlight by computer control) |

### 3 · Get it out of the model

| File | Class | Loaded when | Owns |
|---|---|---|---|
| `ai-generation.md` | extended | Generating frames, clips or voices | The generation stack, the roster, the quality floor · ⚡ v2.49: GPT Image 2.6 as the primary image model (Step 1), the reference route (approved sheets instead of a start frame), native sound kept (§ Sound), the 720p video floor with one upscale on the final, the festival shooting ratio as an outside sanity range |
| `prompting-craft.md` | extended | Writing the prompt itself | Vendor-documented structure, the t2v/i2v split, negatives, consistency, and what is folklore ⚡ §11b the Higgsfield/Seedance vendor skill: what was adopted (scale by comparison, the three-part observation pattern, @tag presence, one speed per shot), what was TESTED AND REJECTED (FOV in degrees — it failed backwards, 2026-09-17), and the four claims still open as named tests. ⚡ §1 the three prompt paths (frame-led i2v, scene, multi-shot) · §9.4b the voice string written once · **§12 the scene form (v2.49)**: the default for Seedance 2.5 — approved sheets, the vendor's block order, 2,500–20,000 characters, `prompt_lint.py --template scene` · **§12a scene files + project DNA**: shared blocks written once in `01-script/scenes/`, pasted per block by the lint, `override:` with a reason, `--scene` checks one setup = one lens |
| `move-catalogue.md` | extended | You know the dramatic job and want the actual move, with the numbers, not another principle | ⚡ Named moves that were shot and kept: the centred pivot whip (0.3/0.5/1.4s), the worm's-eye rise, the blind open, the split OTS pair, the lip-ECU rise, the doorway silhouette, the deep-to-near rack, the anti-lookroom pin, the strike ramp, the broadcast interruption, the reused frame, the isolated read, the frozen-frame handoff, and the comedy set — the ceiling drop, the chair-back reveal, the mirrored Dutch, the 5cm threat, the repeated identical single, the persistent live element, the uniform dissolve, the split reaction, the single column, the seeded transformation, the named ramp, the pinned screen-space layer, the bridge shot, the statics pull, the unambiguous first setup, the survivor anchor, the asphalt-skim head-on near-miss, the reflection tag-chase, the pinned-detail orbital, the camera as a second participant. ⚡ Added 2026-10-29 (v2.45), with numbers and who measured them (Scenario's authors, our plans, or the course's real rigs) and a For / Spec / Make it / Prompt / QA block each: the counter dive, the punched still, the let-go crane, the locked-clock versions, the off-camera-cause reaction, the empty-frame entrance, the assembled mark, the snap pull to a point, the closed loop, the reversed approach, the switch-off, the snap zoom on the line, the locked release, the struck operator, the ride-along roll, the foreground-graze push, the walk-in focus, the exit pull, the tilt-up opener, the process opener, the vertical pivot, the structure sweep, the roll layer, the pinned slider parallax, the lean, the ceiling exit, the locked timelapse, the fake timelapse move, the walked hyperlapse; measured amendments to §1, §2, §7, §24, §28, §32 and §33. 62 usable moves (§34, §35, §39 and §40 reserved), each with its provenance, what it does and what breaks it. ⛔ **Appendix P**: every Scenario or course move that breaks a house rule (overshoot on text, the flash limit, the transition budget, the ads-lane bans, §7b orbits and reveals, music-led cutting, AI images as conditioning, retiming people), with the rule and the decision it waits on |
| `specifics-catalogue.md` | extended | You want the actual fragment that worked — the line, the prop description, the shot chain, the beat structure — not the rule derived from it | ⚡ The five categories `move-catalogue.md` does not cover: DRAMATURGY (the payoff delivered by a POV of an obstacle rather than a line; the rejected read named four ways; emotion located anatomically with the rest of the face held still; intensity as a number plus a seven-point manifest) · SEQUENCES (the four-cut cabin and why cut 3 leaves the car; the physical constant restated in every cut; the light event as the thing that makes four angles one moment) · PROP DESIGN (a badge locked by geometry under NON-IP; the four-attribute vehicle sheet; the prop built for the scene that destroys it) · SCRIPTING (the nine-word exchange; the beat written as stage business; line length as a function of breath; delivery as rhythm + subtext + a simile) · TRANSITIONS (the eyeline handoff into a POV; the same light carrying a cut) · plus V2V (the INPUT LOCK's two closed lists; a transformation as an ordered assembly anchored on a real feature of the plate) and the Seedance structured-block format (MATERIAL, FORMAT MODE, POSITIVE LOCKS; field of view in degrees per cut; 60:30:10 with the accent assigned to an object; the speed ramp defined by its sound). ⚡ The headline: HIDE WHAT THE MODEL CANNOT HOLD — a driver kept unreadable behind mirror-bright glass for a whole action sequence, so identity never appears to drift. · §10 FIVE FESTIVAL AI SHORT FILMS MEASURED END TO END (1,122 shots, queryable in `assets/reference-shots.jsonl` via `film_db.py`): median shot 2.0-3.4 s, 170-250 shots per ten minutes, openings and endings SLOWER than the body, ~six shots in ten with no deliberate camera move, hard cuts 85-92% everywhere but one, SPEECH COVERAGE from 62% to 0% as the clearest signature of a film's architecture, and two opposite answers to consistency — one room or one face. §10.7 lists what reversed and why. · §15 CHAINING, measured with `film_db.py chain`: performance moves one step at a time across 86–97 % of cuts, and when it jumps two the FRAME jumps with it (60–84 %; colour carries it in only two films); no shot-size step rule; 6 of 102 off-eye angles are answered by the opposite angle; the hold is inside the turn shot, not after it. Every entry is a verbatim quote or a dated measurement — ⛔ an entry that cannot be quoted does not belong. §16: the 38-ad corpus measured shot by shot (lab-00006), and the same measures on the skill's own scripts. §16.10: the revise loop measured (lab-00008) — the director's review then the baseline card beat either alone. |
| `motion-craft.md` | extended | The clips are clean and the film still looks lame, or someone says it "looks AI" | ⚡ What a move must CONTAIN: the five animation principles a model has no reason to produce, the uncanny as a motion MISMATCH with two exits, what "modern" measurably is (short AND busy), cutting on action not space, and the blacklist; §6b and §7b cross-reference the catalogue's measured knock and its pending orbits and reveals |
| `motion-design.md` | extended | A move the prompt cannot describe | First/last frame, motion transfer, video references, multi-shot, ramping; §2.5 the measured feel bands (jitter: locked < 0.8 · float 0.8–2.5 · controlled 2.5–5 · calm 5–12 · agitated 12–25 · frantic 25–65 %/s) and cross-references to the catalogue's measured moves |
| `product-video.md` | extended | The subject is a product's own interface: a web app, a mobile app, a dashboard | The product's UI is never generated (real captures only); beat maps for the social clip, feature launch, teaser, demo, explainer and customer story; the capture spec (4K, 125 % zoom, staged fictional data); frame or no frame, and never a full-width desktop on 9:16; cursor, click, zoom and camera over the UI; carried transitions, not crossfades; text over UI; VO and supers with separate jobs; the standard ElevenLabs voice; UI sound and music at least 10 LU under speech; opening and end cards as opt-ins. Fills through `clients/_STYLE-GUIDE-TEMPLATE.md` |
| `blocking.md` | extended | A shot with two or more people, a geometric camera move, a count, a cut inside one take, a product in hand, or people walking | ⚡ The 3D blocking stage: Claude writes a spec, never bpy (SceneCraft 88.9 vs 5.6); real sizes from a table; the camera in film terms solved by maths; geometry checked before a render (collisions, reach, the line at a cut, frame and safe area, void, the lens); render → critique → revise, three rounds, keep the best; eight bold 10–14 s presets; the prompt's spatial text, and the camera's measured beats, computed from the same geometry; routes per roster model; `approve blocking:<SHOT>` binds the manifest's hash. §3a the shot plan (73 named moves on 16 rigs, an operator that lags, anticipates, overshoots and banks, joins that blend, detail framings) · §3b rooms with doors and windows, furniture from parts, a skinned mannequin with planted-foot walks · §3c 20 environment templates and vehicles · §3d the concept look (EEVEE, materials, times of day; Poly Haven CC0 with an OK) · §3e precise geometry (floor plans, lathe and extrude) and imported models with their licences · §3f the presets. `scripts/blocking.py`, `blocking_rig.py`, `blocking_kit.py`, `blocking_camera.py`, `blocking_env.py`, `blocking_look.py`. Adopted 2026-10-23, the bake-off (lab-00011) pending · §1 the v2.49 scope caution: weak for two subjects crossing or a non-human body, fine for one subject at an exact camera speed (HFF-04, unmeasured here) |
| `aerial-and-fpv.md` | extended | A drone, FPV, cinewhoop, insect-scale or planet-scale shot, a golf or property flyover, or a real drone day | ⚡ When an aerial earns its place (the `aerial:` declaration: a job, a subject, a last frame); the move table with its numbers (`assets/aerial-moves.json`: orbit 1.3–2.2 m/s, ≤ 1.5 turns; helix 8–12 s a turn…); prompting so it does not look like a toy (Held 2010); cutting aerials; the cinewhoop one-take; the bee and the mosquito; the golf hole card and flyover, St Andrews labelled spec and private (C5); property; sound; planet scale (no stars, simulated geography, the Earth-zoom preset reference only, C2); seed chaining (C1); DJI's in-app presets mapped to the moves and the pilot sheet; rights. `scripts/aerial_qa.py`, `scripts/flyover.py`. Adopted 2026-10-26 (lab-00016) |
| `multishot.md` | extended | A clip that cuts inside one generation (`form: multishot`), or a sequence whose continuity IS the content | ⚡ The planned multi-shot clip, adopted by house decision 2026-10-25: the cut list locked first (an internal cut is final, no handles), the blocking render as the video reference, approved frames at both ends where the model can honour them (§3 the per-model route), one subject per reference with positional `@Image N` tags, `[STAGES]` as budgets with one state change and one end state each, `[WHERE]` seats, one canonical list of lines, QA against the plan, cost. `prompt_lint.py` `form: multishot`; `gate.py` holds the end still, the tag order and the voice gate · v2.49: how it splits from the scene form (who owns the cuts), the HFF-04 blocking caution |
| `shot-relationships.md` | extended | Reading how a reference's shots relate (characters, props, places, light, camera, every cut), replicating a reference with new cast, places, voice and music, or checking our own edit's joins before picture lock | `shot_graph.py` measures every join (colour, exposure, alike-or-not, camera and subject motion either side, where the subject sits, the key side) and every shot (the camera tracked and categorised onto blocking moves, light, palette, composition maps, depth of field, clean plates), and holds a closed-vocabulary read (entities, positions, emotion on film_db's scale, light, locations with a recreation brief and variants, cut relations) to the pixels; `replicate.py` turns the graph into a gated job plan with a closeness score (house rule 2026-10-25: any reference, flagged); `shot_graph.py qa` on our cuts |
| `sequence-grammar.md` | extended | Putting shots IN ORDER — a shotlist, a multi-shot prompt, a promo that must play as one scene — or judging a camera-angle / lighting cheat sheet | ⚡ What shot B has to do because of shot A: the scene arc (orient → in → release, ~55 s a scene), size and angle across a cut (no step rule; an angle means something only in story order and with its partner; eye level for direct address; height and tilt written separately), the stimulus → feeling → action → speech unit, intensity as a ladder the frame climbs with, one key side and one colour family per scene, the luminance arc, composition at the cut — ⚡ §2b THE CONTRAST PLAN AND THE CAMERA PLAN (continuity only for geography and identity; one or two components progressing to the climax; at least one deliberate break; a camera mix with jobs, not a frozen default — written after lab-00005 measured 97 % locked shots) — and §8, ONE TABLE that combines every channel per beat, as the baseline to break. §1 checks the infographics claim by claim. `sequence_lint.py` enforces it. §2c: how 38 real award-winning ads cut and move — pace ~1.8 s a shot, a third wide, eye level three in four, straight cuts, cuts on action and looks, not beats; read it before any ad shotlist. §2c item 14: the revise loop — the director's review, then `sequence_lint.py --baseline`, at most three rounds. |
| `acting-for-the-model.md` | extended | Writing a performance card or a `[PERFORMANCE]` block; a performer clip came back posed, vacant, twitchy or overdriven | ⚡ Which half of the acting tradition a model can use (the external half: facts, event, physical life, the target, the stimulus, the obstacle — where every video vendor's guidance has converged), the shot size that decides the channel (body at MS+, gaze and a partial face at MCU/CU), Laban qualities as plain-language bundles with their recognition odds, partial expression and the struggle over the peak, the vendors' 2025–26 guidance side by side, **performance card v2** (STIMULUS, TARGET, BODY) and a note → behaviour translation table. `prompt_lint.py` warns on the v2 gaps; `contact_sheet.py --perf` is the check |
| `storyboarding.md` | extended | Stage 3, once the shot list exists, and the start-frame sheet in stage 5 | (v2.66.0) See the film before paying for it: ask for the person's own sketches first, the storyboard page (every shot in cut order, energy on top), the free animatic, the `storyboard` and `startframes` sign-offs, and what is not measured (no published keep rate) |
| `direction.md` | extended | Directing the take, and deciding WHAT HAPPENS in a shot | Performance cards, blocking, coverage, the selects pass. ⚡ §2b **the shot event card** — F11 asked on the plan instead of after the clip is paid for: if AT START and AT END are the same sentence the shot is dead · §2c **five shots, then kill four** — the divergence step that existed only at concept level, which is why a first shot idea got defended instead of compared |
| `refinement-loop.md` | extended | A shot came back wrong | The staged loop, the fault→lever table, the stop rules |
| `real-and-ai.md` | extended | Real footage is in the mix | The six blend modes, the seam taxonomy, and the disclosure exposure hybrid work creates |

### 4 · Make it feel alive

| File | Class | Loaded when | Owns |
|---|---|---|---|
| `timing-and-performance.md` | extended | A clip is technically right and reads dead | Easing as spacing; blink/gaze/smile timings in frames; micro-expressions; manufacturing the settle |
| `shot-handoff.md` | extended | Planning ends of shots and joins | The tail defect, the corrected handle rule, the aftermath, the FUNCTION required on every B-roll insert · §1.3 mouth-opening words trigger speech (v2.49, HFF-03) |
| `emotional-journey.md` | extended | Planning the shape of feeling | Viewer vs character emotion, the start→end emotional delta, the vacant face, props/environment/transitions on the curve |

### 5 · Assemble

| File | Class | Loaded when | Owns |
|---|---|---|---|
| `editing-storytelling.md` | extended | Deciding where a cut goes | Murch, montage, continuity and its violations, rhythm — and what transfers to 40 seconds |
| `editing-and-audio.md` | extended | In the edit | Music to picture (the fit, the edits, the arrangement, the check), the lead composer (brief, spotting, owned motif, composed layers, note engine, generated beds, Fairlight), lipsync, mix, captions, export (DaVinci Resolve) · ⚡ v2.49: §7d native sound kept by default (`guide-audio` restores the guide rule), §7e the bed under kept sound, §7g festival sound patterns, Region repair, the `dwg-working` switch, § What runs through the API (titles, Fusion and Fairlight by computer control; all SFX and edits in Resolve) and the Resolve traps |
| `typography-and-captions.md` | extended | Any on-screen type | Face, setting, contrast, placement, motion; ⚡ §6b a motion system for supers, titles and end cards (curves, duration tiers, damping, stagger) · §6c titles placed by computer control since v2.49, read back by the API |
| `dr-advertorial.md` | extended | A long-body DR ad (`modes/ugc-volume.md` §2b) | The on-screen devices one DR agency uses, counted on 13 ads (lab-00009); the safe box for every platform; the long-body pace; the SFX map; a UGC voice; roster-only AI routing; the mute and organic-feel tests |
| `stock-sourcing.md` | extended | Sourcing a photo, clip or music bed | The licence, the per-asset blockers, the Pixabay API's limits |

### 6 · Ship

| File | Class | Loaded when | Owns |
|---|---|---|---|
| `realism-qa.md` | extended | The QA gate | Making it not read as AI; the clip and batch cards · V12 points to the scene board; §7 its measurement planned |
| `photorealism-physics.md` | extended | A frame reads synthetic and nobody can say why | Capture physics, the remedy table, the phone-not-ARRI target — and ⚡ §8.1, the LIGHTING withhold list: the named vocabulary that makes UGC look like an ad, and the four techniques out of the whole tradition that survive |
| `compliance.md` | extended | Claims, endorsements, testimonials, AI disclosure | The legal surface |
| `review-and-approval.md` | extended | Getting a cut approved | Review rounds, sign-off, the platform, the Resolve marker bridge · ⚡ §11 (v2.49) the scene board before any approval request: every shot of a scene compared against its sheets, fixed toward the sheet, the comparison listed |
| `world-design.md` | extended | Before the first frame of any exterior | The world designed once and inherited: the card (sun, Beaufort wind, WMO sky, visibility and depth layers, land, water, cast background life, the place's plausible life), its approval, the prompt lint against it, both-or-neither frames, no movers by edit, the ⚑ warnings answered before spend, stops, the clip read |
| `sound-off-story.md` | extended | Before lock and at export, every lane | The client's check — does it tell the story with no sound and no voiceover: T1 (the muted feed) and T2 (the picture alone), the cold viewer's retell first, the story map, the proofs, the gates, the pack |
| `revisions.md` | extended | Client notes have arrived | Routing a revision by cost class; where the scope line is |
| `performance-metrics.md` | extended | After shipping | The diagnosis waterfall, the ad-name join key, promotion floors |

### 7 · Across videos, and the skill itself

| File | Class | Loaded when | Owns |
|---|---|---|---|
| `series-continuity.md` | extended | Any series work | The bible vs the continuity log; INVARIANT/VARIANT/DRIFT; the episode registry; §6.2 the freeze |
| `pm-workflow.md` | extended | Running the board | Output folders, file naming, ClickUp conventions, milestone logging, escalation |
| `self-evolution.md` | extended | Production taught you something | Episode note → consolidation → promotion gates → LEDGER |

---

## Never-loaded — human-only

`evals/` · `memory/episodes/` · `memory/reviews/` · `memory/proposals/` · `assets/further-reading.md`
· `script-archive/`. Consulted deliberately, never routed into a working session.
⛔ `memory/LEDGER.md` is the exception in that folder: it is read when a decision's history matters.
`memory/` is the studio's own history folder (`CINE_MEMORY` or `_cine-memory/`), not the plugin's.

---

## The shape a reference should have

Borrowed wholesale, because the alternative is thirty-eight private structures: **every reference
covers four slots**, whatever it calls them.

1. **Patterns** — how good work in this area looks. The craft, the idioms, the decision trees.
2. **Failure-mode guard** — what goes wrong here, named, with its signature.
3. **Target-match discipline** — how we know we are making the right thing; name the target before,
   verify against it after.
4. **Verification** — the pre-ship readout. What evidence closes this out.

Plus two this skill adds and will not give up:

5. **⛔ Hard rules marked and separable** — a rule that cannot be violated is marked ⛔ and is
   phrased so a check can be written against it.
6. **"What this file cannot tell you"** — the honest floor. A reference that claims no limits is
   a reference nobody can calibrate.

---

## Adding a reference

1. It must be **needed at a stage** that no existing file owns. Growth without routing is the
   failure this index exists to prevent — prefer a section in an existing file.
2. Add the row here, in its stage bucket, with a class.
3. Add the router row in `SKILL.md`.
4. Run `python3 scripts/skill_audit.py`. It must exit 0.
