# Glossary: the house words

**How to use it:** find the word, read one line, follow the source if you need the full rule. Paths are inside this skill's folder, except `hooks/` and `agents/`, which sit at the plugin root. A source names a file and a section, not a line number, so it stays true when the file is edited.

## 1. The gate and approvals

| Term | Meaning | Source |
|---|---|---|
| **Gate** | The check that stands between the agent and anything paid. It is a script (`gate.py`) plus the app's hooks. It compares each paid call with the open job. | `SKILL.md` §0 |
| **Hook (the gate's)** | A check the app runs by itself before a tool call. It covers Higgsfield, Kling and Scenario, DaVinci Resolve and shell commands. Not the same as a script's hook (section 6). | `hooks/hooks.json` (plugin root); `SKILL.md` §0 |
| **Owner** | The person who runs your studio. On a given job, the checkpoint's **Approver** signs each stage: the owner, or someone they name. Where a message says "the owner", read "the person who approves". The gate accepts an approval only in that person's own words, typed in the chat. | `scripts/gate.py` (`approve`) · `assets/checkpoint-template.md` |
| **Job** | One production, in one folder. Only one job is open at a time on a machine. It stays open for 24 hours. | `scripts/gate.py` |
| **Checkpoint** | `00-brief/CHECKPOINT.md`. One page: job, mode, client, policy, format, inputs, skips, budget, approver. `gate.py open` refuses it while any line is unfilled. | `assets/checkpoint-template.md` |
| **Approval** | Your reply, word for word, recorded after you saw the thing. The gate refuses a quote that appears in no human turn, where it can check. | `SKILL.md` §0 |
| **Approver** | The named person who approves each stage. Never "the client". | `assets/checkpoint-template.md` (the `Approver:` line) |
| **Approval chain** | The order approvals must come in: concept → script → cast and frames → audio → clips → music → lock → titles → export. | `SKILL.md` §0 |
| **Policy** | How much a person checks. `per-stage-human`: a person checks script, reference images, audio and clips, each before the next stage. `gated`: the machine checks first; a person looks at the frame gate and at flagged, landing and hero shots. `standing`: a pure variant ships on a standing approval. An unanswered policy is asked about, never assumed. | `clients/_TEMPLATE.md` §0 (verification policy) |
| **Allowance** | One recorded approval for a batch of shots. Each shot gets its first generation and 2 retries without a new prompt. Every call is still checked. Audio still asks per call. | `SKILL.md` §0 |
| **Resolve allowance** | The same idea for DaVinci Resolve scripts (`gate.py allow resolve`). Starting a render, the AI speech generator and auto-captions stay denied. | `SKILL.md` §0; `scripts/gate.py` |
| **Previz lane** | A capped lane for concept art during development: at most 12 images. It needs the look board filled first and a reason in your own words. It closes when the concept is signed. | `SKILL.md` §4 rule 7 |
| **Evaluation tier** | A job that answers a question and ships nothing. The checkpoint carries `Tier: evaluation` and `Question:`. It may generate below the quality floor. Its output cannot be locked or exported. | `assets/checkpoint-template.md`; `references/ai-generation.md` |
| **Evaluation lane** | An evaluation job that also says `Lane: eval`. One approved plan (`00-brief/EVAL-PLAN.md`, `gate.py approve eval`) replaces the concept and the script. The gate holds every call to the plan's shots, takes per shot and budget. No speech, Kling or previz. | `assets/eval-plan-template.md`; `references/ai-generation.md` |
| **Frame gate** | No clip generates without an approved still. A person approves it. | `SKILL.md` §4 rule 8 |
| **Computer-control rule** | Fusion, Fairlight and native titles are made in Resolve's own interface by computer control, never through the scripting API, which fails on them. The gate refuses a script that writes them. | `SKILL.md` §0 ("The computer-control rule") |
| **Native-elements rule** | A client deliverable is made in Resolve with its own elements; a file made outside Resolve needs one of a few named reasons. | `scripts/native.py` |
| **Picture lock** | Stage 11. After it, the picture does not change. It needs the QA log, the motion analysis and the title card. | `SKILL.md` §0 (the approval chain); §4 rule 4 |
| **Bypass** | Turning the gate off with `CINE_GATE=off`, set in the shell that starts the session. Every bypass is written to a log. | `SKILL.md` §0 |
| **Switch** | A house rule turned off for one job. It is written on the checkpoint's `Switches:` line with a reason. The rule stays the default for every other job. A switch changes nothing at the spend gate. | `assets/project-switches.json` |
| **Locked rules** | The eight rules no switch lifts (listed in section 9). | `assets/project-switches.json` (`locked`) |
| **Hard locks (a client's)** | The client's own fixed rules, in section 0 of their profile. For example a locked script, or no overlays. | `SKILL.md` §1 |

## 2. Routes, modes and stages

| Term | Meaning | Source |
|---|---|---|
| **Mode** | The shape of the job. **A** narrative promo: one video that carries the message. **B** UGC volume: a monthly number of videos. **C** editorial or explainer: information first. **D** repurpose: the footage already exists. **S** stills: pictures only. | `modes/_INDEX.md` |
| **Ladder** | The table of 15 stages (0–14) that every video follows. | `SKILL.md` §2 |
| **Stage** | One row of the ladder. Asking for a stage's output is asking for that stage. | `SKILL.md` §1 |
| **Hat** | The role whose judgement a stage needs: producer, writer, director, editor and so on. One agent wears them all. Naming them stops convenience from overruling the editor or the compliance check. | `SKILL.md` §2 |
| **Client profile** | The brand's file: characters, voices, offer, approved language, generation stack, costs. With no profile, nothing runs. | `SKILL.md` opening and §1 |
| **Show id** | The job's name, for example `acme-01007-primar-comuna`. | `references/pm-workflow.md` (output organization and file naming) |
| **Job folders** | `00-brief`, `01-script`, `02-startframes`, `03-clips`, `04-broll`, `05-voice`, `06-music`, `07-edit`, `08-captions`, `09-qa`, `10-export`, `99-costs`. | `SKILL.md` (the ladder's Artifact column) |
| **`_lab`** | The skill's own test bench. It is not a client. Nothing made under it ships. | `clients/_INDEX.md` |
| **`lab-NNNNN`** (in a citation) | One of the author's own experiments, cited as the evidence for a rule or a number (e.g. `[measured · lab-00006]`). The experiment records themselves are not shipped with the plugin. | the references and scripts that cite them |

## 3. Pictures and prompts

| Term | Meaning | Source |
|---|---|---|
| **Sheet** | The approved reference pictures for one character, prop or location. Signed at stage 4 as `character:<NAME>`, `prop:<NAME>` or `world:<LOCATION>`. | `SKILL.md` ladder row 4 |
| **Scene form** | The default way to write a Seedance 2.5 clip since v2.49. The clip is built from the approved sheets and has no start frame. | `SKILL.md` §0 |
| **Frame-led** | The switch that goes back to an approved start frame for every clip. | `SKILL.md` §3 |
| **Start frame** | The approved still a clip begins from. Signed as `frame:<SHOT>`. | `SKILL.md` ladder row 5 |
| **Target, blocking, family** | Three extra approvals at stage 5. `target:<SHOT>`: an edited picture used as a target. `blocking:<SHOT>`: a shot with planned positions. `family:<FAMILY>`: one approval for a family of inserts on one contact sheet. | `SKILL.md` ladder row 5; `references/dr-advertorial.md` §4 |
| **Project DNA** | `_PROJECT.dna.md`. The text every scene-form shot of a film shares: style, format, output settings and film-wide locks. Written once, so shots cannot drift apart. | `references/prompting-craft.md` §12a |
| **Scene file** | `<SCENE>.scene.md`. One per scene: its references, location map, wardrobe, lighting, colour and sound. | `references/prompting-craft.md` §12a |
| **Shot event card** | Two sentences per shot: what the viewer sees at the start, and at the end. If they are the same sentence, the shot is cut or redesigned. | `references/direction.md` §2b |
| **Look board** | A board of four real pictures, shown before the concepts. | `SKILL.md` §4 rules 2 and 7 |
| **Concept board, shot board** | The board for choosing a concept, and the board shown before any spend. `board.py` builds all three. | `SKILL.md` §4 rule 7 |
| **Scene board** | Every shot of one scene side by side, before any approval request. | `references/review-and-approval.md` §11 |
| **Contact sheet** | A grid of frames from a clip or a cut. One is built and read before any draft is shown. | `scripts/contact_sheet.py`; locked rule |
| **Lint** | An automatic check on a prompt or a script. Nothing is sent that a lint did not pass. | `SKILL.md` §4 rule 1 |
| **Roster** | The approved list of video models. The lint refuses any other. | `SKILL.md` §3 |
| **Genjutsu** | A Higgsfield tool that re-renders an existing video: motion transfer or object swap. It takes no start frame, no length and no prompt. | `references/ai-generation.md` (Genjutsu) |
| **The 1.7× rule** | Generate about 1.7 times the on-screen length. Measured on 12 real clips: 57.6% of the footage was usable. | `SKILL.md` §3 |

## 4. Sound and music

| Term | Meaning | Source |
|---|---|---|
| **Path A** | Voice first. The line is recorded as speech, then the clip is generated with that audio as its reference. Required for languages the models mispronounce. | `references/ai-generation.md` step 4 (voices and lipsync) |
| **Path B** | Native audio. The video model speaks the line itself. | `references/ai-generation.md` step 4 (voices and lipsync) |
| **Guide audio** | A switch. By default a clip's own sound is kept as production sound. With the switch, it is a guide only. | `SKILL.md` §3 |
| **Must-hits** | The 2 to 4 moments in the cut that the music must land on. Kept in `07-edit/music/HITS.json`. | `references/editing-and-audio.md` (music to picture) |
| **Music choice** | You always choose the track. The skill shortlists. | locked rule; `SKILL.md` ladder row 9 |

## 5. Edit and finish

| Term | Meaning | Source |
|---|---|---|
| **Selects** | Choosing the takes. The director's gate between generation and edit. | `references/direction.md` §4 |
| **QA card** | The realism checklist run on a clip before it leaves the review folder. Every tick carries one concrete observation. | `references/realism-qa.md` §6 |
| **Style frame** | One approved still that fixes the typeface, the type sizes and the text colours, before any title is built. | `references/typography-and-captions.md` §9 |
| **Title lanes** | The title style a job runs in: `ads`, `brand`, `drama`, `golf`, `property`, `captions-only`. | `assets/title-lanes.json` |
| **Script bands** | Measured ranges for spoken scripts (low, middle, high). They are shown beside a script's own numbers as advice. They never fail a script. | `assets/script-bands.json` |

## 6. Series, batches and agents

| Term | Meaning | Source |
|---|---|---|
| **Hook (a script's)** | The opening of a video. Not the same as the gate's hook (section 1). | `modes/ugc-volume.md` |
| **Hook bank** | A set of openings, combined with compliance-cleared bodies and a bank of closing calls to action. | `modes/ugc-volume.md` §1 |
| **Invariant, variant** | An invariant is what must stay the same across a series. A variant changes only what the invariants allow, so it can ship on a standing approval. | `references/review-and-approval.md` §10 |
| **Freeze precondition** | No episode joins a shared batch until the invariants file is frozen and the reference folder is locked. | `references/series-parallel.md` §2 |
| **Accumulator batch** | Collect work across episodes and process it once, not once per episode. | `references/series-parallel.md` §3 |
| **Join gate** | The stage where parallel work comes back together. It trusts nothing and re-checks. | `references/series-parallel.md` §6 |
| **Agents** | Eight helpers, each doing one narrow job: draft writer, cold reader, researcher, scene continuity, script critic, sound-effect spotter, shot writer, take reviewer. | `agents/` (plugin root) |
| **Episode note** | The close-out note: what broke, what fixed it, estimated against actual. | `SKILL.md` §5 |

## 7. Evidence and numbers

| Term | Meaning | Source |
|---|---|---|
| **`[PRIMARY]`, `[SECONDARY]`** | Where a claim came from. Primary is the party that owns the fact. Prices, policies and capabilities need primary, or two independent secondary sources. | `references/research-quality.md` §2 |
| **measured, estimated, assumed** | How a number was obtained. The budget line must carry exactly one, in square brackets. | `assets/checkpoint-template.md`; `references/pm-workflow.md` (verification readout) |
| **Verification readout** | The check on any deliverable with numbers: each figure tagged, the arithmetic redone, a verdict. | `SKILL.md` §5 |
| **Envelope** | The job's spending limit. It is the first figure on the checkpoint's `Budget:` line, with who set it. `SKILL.md` uses the word without explaining it. | `assets/checkpoint-template.md` (the `Budget:` line); `SKILL.md` opening and §5 |
| **Rate card** | The one place a price is read from: `rate_card.py` and `assets/higgsfield-rates.json`. | `scripts/rate_card.py` |

## 8. Set-up words

| Term | Meaning | Source |
|---|---|---|
| **`CINE_CLIENTS`** | Where your client profiles live, outside the plugin. A plugin update replaces the plugin's own `clients/` folder. | `SKILL.md`; `assets/checkpoint-template.md` |
| **`[studio history]`** | A tag on a rule's evidence: the note or proposal behind it is in a studio's own history folder, which does not ship. The date and the topic are given so that studio can find it. | `memory/README.md` |
| **Connector settings** | Which claude.ai connector id is your Higgsfield account, and which are other services. Kept in `$CINE_HOME/connectors.json`; set with `/cinematographly:connectors` (`gate.py connectors`); naming one `--other` needs the person's words. An unnamed connector asks before every paid call. A tool the gate does not know asks too, and Higgsfield-only tools stay gated even on a connector named as another service. | `START-HERE.md`; `hooks/hooks.json` |
| **`CINE_MEMORY`** | Where your studio's history lives, outside the plugin: close-out notes, proposals and your ledger. A `_cine-memory/` folder above your jobs works too. | `memory/README.md`; `references/self-evolution.md` |
| **`CINE_HOME`** | Where the gate keeps its state. Default `~/.cinematographly`. One open job per folder. | `scripts/gate.py` |
| **`CINE_GATE=off`** | The bypass. See section 1. | `SKILL.md` §0 |
| **`gate.py where`** | Prints which install is running: its scripts, skill, clients and state folders. | `scripts/gate.py` |

## 9. The switches and the locked rules

**The 15 switches.** Each lifts one default, for one job.

| Switch | The default it lifts |
|---|---|
| `music-led` | The track is fitted to the cut. With the switch, the song is fixed and the picture is cut to it. |
| `speed-conform` | The rules on speed ramps. |
| `upload-master` | Delivery at the format's resolution. With the switch, one extra larger upload copy. |
| `finish-texture` | Ads get no texture, bloom, grain or vignette. |
| `light-leak` | No flares, glows or light leaks in ads. |
| `blur-titles` | Ad titles move by opacity or rise only, with no blur. |
| `blurred-fill` | Never an image over a blurred copy of itself. |
| `caption-display-face` | The display typeface is never used for a run of captions. |
| `caption-shadow-first` | Caption contrast comes from a plate first, a shadow second. |
| `lens-smear` | The rule on foreground wipes. |
| `step-lower-thirds` | Step chips in explainers are held back. |
| `frame-led` | A Seedance 2.5 clip is written in scene form, from approved sheets. |
| `guide-audio` | A clip's own sound is kept as production sound. |
| `floor-1080` | Video is generated at 720p, with one upscale on the final. |
| `dwg-working` | The Rec.709 working route. The switch is for real log footage only. |

**The eight locked rules.** No switch lifts them.

- No advanced VFX. One exception since v2.49: the masked repair of one region of a shot.
- No AI images as references.
- No spend without approval.
- Native Resolve titles only.
- English only.
- A contact sheet before any draft.
- The skill never picks the music.
- No Higgsfield `motion_control`.

## 10. Words with more than one meaning

- **"Lock" has five:** picture lock (stage 11), the locked rules (section 9), a client's hard locks, an identity lock on a character, and the `[POSITIVE LOCKS]` block in a prompt.
- **"Hook" has two:** the gate's hook (section 1) and a script's hook (section 6).
