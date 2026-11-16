# Further Reading — provenance for what this skill already teaches

<!-- skill_audit: external-paths -->  <!-- this file cites files in OTHER repos on purpose -->

**The skill is self-contained.** Everything it asks you to do is written into `references/` in full;
nothing here is required to use it. This file exists for two other reasons:

1. **Provenance.** Every non-obvious claim in the references traces to a named source, so a future
   reader can check the reasoning instead of taking a rule on faith — and so a rule that turns out to
   be wrong can be traced back and retired.
2. **Depth on demand.** When a decision is genuinely contested, expensive, or about to become a
   standing rule for a whole brand, the underlying work has more than the reference could carry.

The author keeps structured extractions of most of these privately; the skill does not depend on them.

---

## Where each reference's material comes from

| Reference file | Built from |
|---|---|
| `ideation.md` | Young *A Technique for Producing Ideas* (the five steps; recombination not invention) · Mahon *Art Direction* (the four-frame test) · Heath & Heath *Made to Stick* (the SUCCESs bar as a kill test) |
| `script-craft.md` | The spoken-word layer is this skill's own; a studio's own prose writing system is optional (see its §0) |
| `craft-cheatsheet.md` | McKee *Story* · Cooper & Dancyger *Writing the Short Film* · Katz *Shot by Shot* · Brown *Cinematography: Theory and Practice* and *Motion Picture and Video Lighting* · Ward *Picture Composition* · Pearlman *Cutting Rhythms* · Bowen *Grammar of the Edit* · Glebas *Directing the Story* · Rabiger *Directing* · StudioBinder on lenses and colour |
| `production-design.md` | Mahon *Basics Advertising: Art Direction* · Perryman *The Colour Bible* · Segall *The Complete Guide to Choosing Colors* · Neufert *Architects' Data* · Rumsey & Harcourt *The Oxford Handbook of the Psychology of Appearance* · Bruce & Green *Visual Perception* · Davies *Composition for Artists* |
| `typography-and-captions.md` | Stocks *Universal Principles of Typography* · Brown & Coles *A Pocket Guide to Combining Typefaces* · Shaw *Design for Motion* · Segall *Choosing Colors* (tonal contrast) · Bringhurst via Stocks (measure, typographic colour) · Crook & Beare *Motion Graphics: Principles and Practices from the Ground Up* (the reading rate for text the audio does not speak; tracking under motion; motion/dwell as a hierarchy channel) |
| `brand-system.md` | Couldwell *Laying the Foundations* (design systems) · Mahon *Art Direction* (the brand look) · Shaw *Design for Motion* (motion tokens) |
| `persuasion-psychology.md` | Styles *The Psychology of Attention* · Schwartz's awareness ladder via Masterson & Forde *Great Leads* · Heath & Heath *Made to Stick* · Tan, Pfordresher & Harré *Psychology of Music* · Hormozi *$100M Offers* · Haugtvedt et al. *Online Consumer Psychology* · Wänke *Social Psychology of Consumer Behavior* · Kahneman *Thinking, Fast and Slow* |
| `direction.md` | A cross-vendor production review (director/producer/editor/VFX panel, run 2026-08-28 through the model-router: Kimi K3 + DeepSeek V4 Pro, findings verified against the pipeline before landing) · Katz and Glebas via the craft file for the underlying stagecraft |
| `realism-qa.md` | 2026 practitioner and detection-research survey (gaze/blink/hand forensics, provenance watermarking), plus this account's own production record |
| `real-and-ai.md` | The integration parameters and their order from practitioner accounts (Vulto/The Rookies; Whiteley of The Embassy and Camilleri of Alt VFX via LBBOnline; König on the Blender Foundation's *Tears of Steel*), with grain mechanics from Foundry's Nuke docs (⛔ Foundry sells Nuke) and a vendor-adjacent grain-profiling source flagged as such · **the unresolved contradiction on what viewers notice**: Xue, Agarwala, Dorsey & Rushmeier 2012 (*ACM TOG* 31(4) — luminance, CCT, saturation and local contrast are what correlate; saturation r = 0.811 in highlights) against Nightingale, Wade, Farid & Watson 2019 (*Atten. Percept. Psychophys.* 81(8) — *"people do not readily make use of shadow and reflection cues"*) · capture discipline from CAVE Academy and VFX Voice, with the **VES On-Set VFX Data Collection and Usage Guide** (30 April 2026, free CC-BY) named as the unread document that would settle §2 · ⛔ the legal spine: ***FTC v. Colgate-Palmolive*, 380 U.S. 374 (1965)** — the product-demonstration doctrine, which is about proof rather than technique — plus 16 CFR 255, TikTok's "significantly edited by AI" definition, YouTube's "alters footage of a real event or place" trigger, Meta's "created or altered", **NY S8420A** (synthetic performers, in force 9 June 2026) and **EU AI Act Art. 50** (applicable 2 August 2026) · provenance from the C2PA 2.1 spec's ingredient/manifest-store model and IPTC's `compositeWithTrainedAlgorithmicMedia` · and *Air Head* via fxguide for the 300:1 source-to-final ratio |
| `production-runbook.md` | Method from the `operations` plugin: `process-optimization` (the five-waste frame — waiting, rework, handoffs, over-processing, manual work — and the map-current-state → design-future-state → measure-impact sequence) and `runbook` (purpose / prerequisites / procedure with expected results / verification / troubleshooting / rollback). Everything else is this pipeline's own structure: the three-deep dependency chain VO → frames → clips, the Higgsfield batch tools and `jobs_wait`'s 12-job group limit, and the measured 6.5 h setup figure from `pm-workflow.md`'s capacity arithmetic. ⛔ The 4 h 45 m budget is apportioned by reasoning, not measured — `scripts/stage_timer.py` exists to settle it |
| `preproduction-research.md` | *The Client Brief* (IPA/ISBA/MCCA/PRCA — the only citable multi-body brief specification, and ~20 years old) · UK Government Communication Service *OASIS* (the independent corroboration of the six-field skeleton) · the BetterBriefs research via IPA and trade reporting (**perception data, not outcome data**) · Rosser Reeves *Reality in Advertising* 1961 (the USP, routinely conflated with the untraceable "single-minded proposition") · Amazon shareholder letters **2015** (one-way/two-way doors) and **2016** (the 70% rule, disagree-and-commit) · Howard, *Information Value Theory* 1966 · Spetzler, Winter & Meyer, *Decision Quality* (Wiley 2016) · CEBMa *Guideline for Rapid Evidence Assessments* 2017 (the precedent for declaring reduced rigour) · Guest, Bunce & Johnson 2006 and Hennink & Kaiser 2022 (saturation) · Braun & Clarke 2021 (why not to claim it) · Malterud et al. 2016 (information power) · **Oskamp 1965, Tsai et al. 2008 and Bastardi & Shafir 1998 — the measured cost of over-research** · Eisenhardt 1989 (the unresolved counter-case). Plus the `product-management` plugin skills `write-spec`, `synthesize-research` and `competitive-brief` for methods this skill routes to rather than re-deriving |
| `series-continuity.md` | The *Star Trek: TNG* Writers'/Directors' Guide 1987 and the **Smokey Bear Guidelines** (USDA Forest Service / Ad Council / NASF, 2022 edition) — the two public primary examples of series and character governance · FRAPA's Format Bible Template via The Format People (**the one tradition that writes the non-negotiable/negotiable split down explicitly**, and the reason it is load-bearing: in format licensing that list defines the IP) · Schumann, Petty & Clemons 1990, *JCR* 17(2) (cosmetic vs substantive variation, and which works at which involvement level) · Romaniuk, *Building Distinctive Brand Assets* (OUP 2018) for the Fame × Uniqueness criterion (cited, not read) · IPA Databank character cut via a System1 presentation (vendor-chosen cut, independent dataset) · script-supervisor practice for the continuity log · and the `product-management` plugin's `roadmap-update`, `stakeholder-update` and `sprint-planning` for the month-to-month layer |
| `emotional-journey.md` | A 2026-08-29 mining of the film corpus for an emotional-mapping instrument, which established that **none exists**: Pope *Good Scripts, Bad Scripts* (Theory Charts #1–#4 — tension against time, the only drawn curve) · McKee (the value charge as a binary on a named antonym pair) · Cowgill *The Art of Plotting* (ternary scene values; "plot is the ordering of emotions", quoting Blacker) · Glebas (the seven-step viewer model, "meaning automatically evokes emotions", dramatic irony, and the two-column test this skill's map is built on) · Mahaffy (Kuleshov, offscreen space, performance modes) · Miller (Adler and Kazan on behaviour; "cut on e-motion"; join by opposites) · Hullfish (the information/emotion channel split; withdrawal) · Dmytryk (the reaction shot as emotional instruction) · Pearlman (breath; the movement phrase) · Kelly & Baena (key poses, the cover-the-face test, the uncanny-valley checklist) · Leandro (the camera as "an x-ray machine"; result-driven notes photograph as fake) · Lichaw *The User's Journey* (the peak–end rule, imported from Kahneman). Plus the perception literature on why a still fails: **Aviezer, Trope & Todorov, *Science* 338:1225 (2012)** — a face at peak intensity carries arousal but not valence · Namba et al. 2018 (static collapses genuine/posed discrimination) · Krumhuber & Manstead 2009 · Kramer et al. 2026 (AI faces measurably more intense, more extreme AU activation, yet recognised *more* accurately) · Du & Martinez 2011 and Smith & Schyns 2009 (fear and disgust are the most resolution-hungry and shortest-range expressions) · Peter Hurley on the squinch · and Black Forest Labs' published agent skills, the only vendor documentation anywhere that says to replace a mood word with visible behaviour |
| `shot-handoff.md` | The craft half from a 2026-08-29 mining of the film corpus for shot exits and joins: Ward *Picture Composition* (the composed end frame; the only itemised join checklist) · Glebas (anticipation/action/**aftermath**) · Pearlman (the movement phrase and its resolution) · Leandro (the "kit of parts", clear entrances and exits) · Brown (overlap **of the action**) · Purcell *Dialogue Editing* (what a handle actually is — an audio-conform allowance; ⛔ weakest-provenance file in the corpus) · Dmytryk (the overlap cut; "coverage anxiety") · Bowen (J/L cuts; the flat/random/shaped curve) · Miller (Pudovkin's five relational structures; join by opposites; transitions designed in pre-production) · Mahaffy (hide-to-reveal, ellipsis) · Katz and Rabiger (coverage, POV, screen direction) · Hullfish (⛔ never play a plot-critical line over B-roll; and the argument against fixed numeric cut rules) · Kelly & Baena (the animator handed one shot without its neighbours — the thesis). The model half from vendor documentation and papers checked 2026-08-29: sync.so, Luma, Everypixel, ImagineArt, Hedra, Runway, Higgsfield (all say match durations; none documents silence behaviour) · TalkVid arXiv:2508.13618 and Wan-S2V arXiv:2508.18621 (training data excludes non-speech segments) · OmniHuman-1.5 arXiv:2508.19209 (speaking↔idle as a NEW capability) · Wan2.2 issue #77 and Wav2Lip issue #19 (the defect reported, the prompt fix reported failing) |
| `timing-and-performance.md` | Peer-reviewed motor control and perception: Flash & Hogan 1985 (minimum jerk) · Viviani & Stucchi 1992 (biological movements look uniform) · Chaminade et al. 2007 · Saygin et al. 2012 (the uncanny valley as prediction error) · Mori 1970 (trans. MacDorman & Kageki) · Hyde et al. 2016 (motion magnitude → personality) · Nyström et al. 2024 (blink kinematics) · Bentivoglio et al. 1997 (blink rate, n = 150) · Rayner et al. 2009 (fixations) · Schmidt & Cohn 2001, Schmidt et al. 2006/2009 (deliberate vs spontaneous) · Krumhuber & Manstead 2009 (Duchenne smiles can be feigned) · Iwasaki & Noguchi 2016 · Yan et al. 2013 (the only real micro-expression duration measurement) · Cohn 2007 (FACS reliability) · Burgoon 2018 and Jordan et al. 2019 (**why the deception claim is refused**) · Montanha et al. 2024 · animation practice via Lasseter 1987, Crook & Beare, Kelly & Baena, Glebas, Meroz and Lauria · Dmytryk, Bowen, Pearlman and Dovale for the edit-side remedies · and this account's own three-clip measurement of 2026-08-29 |
| `compliance.md` | FTC Health Products Compliance Guidance · FTC Endorsement Guides (16 CFR 255) · FTC Rule on Consumer Reviews and Testimonials (16 CFR 465) · FDA structure/function and the DSHEA disclaimer · TikTok, Meta and YouTube synthetic-media policies · Hutson & Smith *Cinematic Algorithms* (the EU AI Act / C2PA statutory layer sitting above platform policy) |
| `research-quality.md` | An online-research discipline (verified URLs, refutation search, tier honesty) · this account's own incidents: the ~40% per-second cost drift, the phantom "2026 FTC AI endorsement rule" caught by hunting the primary, the silent 30fps quirk |
| `delivery-format.md` | Platform delivery specs · EBU R128 / streaming loudness practice |
| `self-evolution.md` | Offline memory consolidation ("dreaming") as presented by Anthropic's applied team · Letta sleep-time compute · a promotion-gate discipline |
| `ai-generation.md`, `editing-and-audio.md`, `pm-workflow.md` | This account's own production record — the guardrail tables are failures that actually happened · Dovale *Mastering DaVinci Resolve 20* (Cut-page mechanics, adjustment vs effects layers, the trim repertoire, proxy/cache/GPU performance config, Fairlight clip-vs-track scoping and loudness conforming — corroboration only; it is silent on the scripting API) · Mahaffy *Micro-Budget Methods of Cinematic Storytelling* (concentrate rather than average the budget; match the piece to the schedule at the plan; consistency reads as authorship; the coverage disagreement with Katz) · Hutson & Smith *Cinematic Algorithms* (the moderated production-economics picture and the new cost categories AI adds) |

## A studio's own writing system is optional

`script-craft.md` §0: if your studio keeps voice profiles or a lexical scanner, use them alongside the skill. Nothing
here depends on one; `script-craft.md` carries the spoken craft, the scorecard and the iteration discipline in full, and
`script_score.py` runs standalone.

## When to go deeper than the reference

- A client challenges a creative choice and "because it works" isn't an answer.
- A rule is about to be written into a client profile or into this skill, where it will affect
  everything downstream.
- A series-level decision — palette, cast, format, house structure — is being made once and held.
- A hook or structure is underperforming and you need a *mechanism* rather than another guess.

Read the source, make the call, and **write the attribution next to the decision** in the script,
shotlist or client profile. Then, if it becomes a standing rule, promote it through
`references/self-evolution.md` with the attribution intact.

## The division that keeps this honest

**Durable principles come from the literature.** Attention, perception, colour, memory, persuasion
structure, music cognition, typographic legibility — these do not change on an annual cycle, and a
citation from 2012 is still good.

**Current specifics come from the web, checked at the time of use.** Model capabilities, prices,
platform policy, retention benchmarks, the tool landscape, and every compliance rule's live wording.
A remembered figure in any of those is a liability.

**Never cite a book for a price or a policy, and never cite a blog for a mechanism.**

## `references/series-parallel.md` — where the parallelism doctrine comes from

- Common agent-orchestration patterns: file-based state hand-off, fan-out / fan-in with a named dispatcher, an
  independent audit at pipeline gates, pipeline before loop, accumulator batching with a max-age sweep, and the
  orchestrator-versus-supervisor choice (a supervisor is refused here). The four disciplines this file ports.
- The core / extended / never-loaded split behind `references/_INDEX.md`, and the attention-and-cache argument for
  selective loading in a 1M-context world.
- **Gene Amdahl**, *Validity of the single processor approach to achieving large scale computing
  capabilities*, AFIPS Spring Joint Computer Conference, 1967 [PRIMARY] — the ceiling in §1.3.
- **Xia et al.**, *Agentless: Demystifying LLM-based Software Engineering Agents*, arXiv 2407.01489,
  2024 — the pipeline-before-loop evidence (cited, not read in full).

## `references/pm-workflow.md` § Naming convention — the published grammar

- **ETC / MovieLabs, *VFX Image Sequence Naming* v1.0** (2020),
  `movielabs.com/prodtech/sdw/vfx/ETC-ImageSequenceNaming-v1.0-063020-FINAL.pdf` [PRIMARY] — the
  cross-studio spec this skill's filenames follow: the field order, the episodic show id
  `<series>-<season><episode>`, 4-digit shot numbers, *"at least 3 numerals"* for the revision code,
  underscore-between-fields with alphanumeric-and-dash inside, no whitespace, and *"all lower case is
  preferable"*. Three deviations are taken deliberately and named in the file.
- **Evan Schiff, ACE**, *Feature Turnover Guide — VFX*, `evanschiff.com` [PRIMARY · working feature
  editor] — 2-letter sequence codes and **shot numbers in increments of 10 from 0010**, because it
  *"allows you to maintain a rough chronological order if you need to insert a new shot after an
  existing one."* Also the argument for keeping scene numbers OUT of shot ids.
- **Ad-ID** (American Association of Advertising Agencies + ANA; replaced ISCI in 2003, ISCI formally
  withdrawn 2007) [SECONDARY · encyclopaedic] — cited only for the structural point that the
  advertising industry's own identifier is an **issued, registered code**, not one a producer
  composes, which is why the ad-name join key and the show id stay separate keys.
- ⛔ **Netflix's *VFX Shot and Version Naming Recommendations*** was sought and **could not be read** —
  the partner-help URL now redirects to a login-gated SPA. Recorded as unread, not as corroboration.

## `references/editing-and-audio.md` § The audio delivery layer

- **Woody Woodhall**, *Audio Splits, Stems & Elemental Tracks*, ProVideo Coalition, 2015
  `[SECONDARY · post-sound practitioner]` — the definitions of stems/splits, **DME** and **M&E**, and
  the note that some deliveries require **"undipped stems"** *"for international re-versioning
  flexibility"*, which is where §3's rule comes from.
- **ASCAP**, *Music in Advertisements* `[PRIMARY · the PRO's own page]` — the negative finding that
  commercials are processed from **Competitrack** monitoring *"on the basis of a census survey"* and
  **Soundmouse** fingerprinting, with cue sheets reserved for long-form infomercials over five
  minutes. This is why the skill does **not** build a cue sheet for a 30-second promo.
- **ASCAP**, *Cue Sheet Corner* `[PRIMARY]` — what a cue sheet is and the four fields it carries,
  cited to show what the instrument is *for*, not to adopt it.
- ⚠ **Not checked: the EU / Romanian rights position.** ASCAP is a US society; UCMR-ADA and its
  counterparts were not consulted, and §5 says so rather than implying the finding travels.
