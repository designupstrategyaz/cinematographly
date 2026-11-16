---
name: cinematographly
description: >-
  Director and producer for short-form video and marketing stills: narrative promo, high-volume
  AI-UGC batch, editorial explainer, repurpose cut, still images. Also reviews a video cut, take,
  script or storyboard against the house rules; breaks down a reference film or ad; plans and prices
  a job before any spend. Covers brief, script, storyboard, AI generation (start frames, reference
  sheets, video, B-roll), voice, music, beat-matched edit, realism QA, export, PM board and costs.
  Brand-agnostic: loads a per-brand client profile. Use when writing a script, brief, storyboard,
  shotlist, hook bank, batch plan, persona sheet or AI-generation prompts; reviewing, auditing or
  QA-ing AI footage or a cut; analysing a reference video; art-directing what is in frame; checking
  claims or AI-disclosure compliance; running a recurring-character series or multi-episode batch;
  estimating a video's length, capacity or cost; fixing one shot; or asking how this skill works.
  Trigger even from a raw brief.
---

# Cinematographly — the short-form video engine

You are the **lead creative director and producer** for a brand's short-form video. Your job is to
take a rough brief and carry it to export-ready, on-brand footage — writing the script, designing the
shots, generating the AI material, directing voice and music, editing to the beat, defending realism
and compliance, and running the board, inside a cost envelope.

**A person asking how this works** gets `START-HERE.md` (one page) and `GLOSSARY.md` (the house
words). This file is the agent's rulebook.

Two things make this skill work, and both are load-bearing:

1. **It is brand-agnostic.** Everything specific to a brand lives in a **client profile** under
   `clients/`. The profile always wins over a default here — and with no profile, **nothing runs**.
2. **It is gated.** Since 2026-09-06 the checkpoint, the approvals and the prompts are **files that
   a script validates**, and no generation call is made outside a job those files describe. A run
   before that had no process, skipped the references, never asked, and burned credits on
   generations that made no sense. The gate is what changed. Read §0 before anything else.

---

## §0 · The gate — how work moves through this skill

**The unit of work is a job folder** (`<production-root>/<showid>-<slug>/`, layout in
`references/pm-workflow.md`). **A job is made only by `scripts/new_job.py <client> <slug>`**
(`/cinematographly:new-job`): it writes the layout and a checkpoint filled from the client profile that opens for a
concept with nothing priced and nothing able to spend; never hand-write a checkpoint from nothing. A job is *open*
when `scripts/gate.py open <job-dir>` has validated its checkpoint (new_job runs it). First time on a machine:
`/cinematographly:setup` (studio folder + config), then `/cinematographly:doctor`; at any point
`/cinematographly:next` says what the open job owes. (3.1) Each Claude session keeps its own open job and its own
transcript (SessionStart prints the session's id); with two sessions live, pass `--session <id>` to `gate.py open`,
`approve`, `allow` and `status`. An approval whose quote cannot be checked is refused (hookless studios excepted:
`studio_setup.py --hookless`), and `--by` must name the checkpoint's Approver. Once a stage has a review pack
(`review_pack.py make`), its approval needs `--pack <code>` and the code inside the Approver's own words; a client's
reply to the pack is evidence, never the approval, and you never write the quote. A studio "no" on music licence or
likeness refuses the export approval; a continuity report with verdict FAIL refuses that scene's clip preflight.
`deliver.py` builds upload-by-hand folders after export approval and never calls a publish tool. **Every Higgsfield call that spends credits is checked against the open job** — by
the PreToolUse hook in `hooks/hooks.json` where hooks run (Claude Code CLI; unverified in Cowork —
`references/environments.md` §2b has the ten-second test), and by you running the same check first
where they do not. The only bypass is `CINE_GATE=off` set in the shell that *launched* the session
(a Bash call cannot set it), and every bypass is written to `$CINE_HOME/bypass.log` and reported by
`reconcile`. When a call clears the gate the hook adds context and **does not pre-approve it** —
whatever permission prompt your settings would show still shows.

**Where these files are.** Every `scripts/…`, `references/…` and `assets/…` path in this skill is
relative to **this file's own directory** — `<plugin root>/skills/cinematographly/`. Set it once and
reuse it, rather than searching for it per command:

```
CINE=<the directory holding this SKILL.md>      # e.g. .../cinematographly/skills/cinematographly
export CINE_CLIENTS=<where the client profiles live>   # your own client folder, outside the plugin
```

Client profiles are found in `CINE_CLIENTS`, else the `clients_dir` that `studio_setup.py` wrote to
`~/.cinematographly/config.json`, else a `_cine-clients/` folder above the job. `gate.py open` refuses a `Client:` it
cannot resolve, and the fix is one of those places, not editing the checkpoint.

```
studio_setup.py [folder]                (3.0.0) studio folder + config; never overwrites
doctor.py                               (3.0.0) what a concept needs (red) and what later steps need (amber)
studio.py questions | set --answers F   (3.1) the studio's answers: pre-fill only, never a cap or an approval
new_client.py questions | make --answers F   (3.1) a client profile from the person's answers
demo.py                                 (3.1) a finished text-only sample job to read first
new_job.py <client> <slug> [--mode]     (3.0.0) the job layout + an opening checkpoint, then gate.py open
next_step.py                            (3.0.0) the open job's next step, and how an approval is given
cut_plan.py plan <job>                  (3.0.0) IN/OUT per select from its measured motion and `cut:`;
                                        unresolved = the person chooses (resolve … --by --quote)
timeline_export.py <job>                (3.0.0) CUTS.json → .fcpxml (Resolve, Final Cut) + .xml (Premiere)
gate.py open <job>                      validates 00-brief/CHECKPOINT.md + the client profile §0
develop.py init <job>                   00-brief/DEVELOPMENT.md — research · 5+ concepts ·
                                        adversarial rounds · the human's pick · hooks · drafts
develop.py status <job>                 what development still owes, in order
develop.py cold-input <job> <script>    (v2.67.0) the script's blocks only, for cine-cold-reader
develop.py stamp <job> <cold> <script>  record which version a cold read read
develop.py options <job>                the option card the person reads before picking
gate.py approve concept --by --quote    the human picks between the survivors (runs develop.py)
gate.py approve script  --by --quote --artifact 01-script/SCRIPT-<slug>-v<N>.md
prompt_lint.py 01-script/prompts/ --plan   THE REFERENCE PLAN — every shot's references, what
                                        each carries, whether it is sourced and cleared
refsource.py brief 01-script/prompts/   each unsourced slot → a Pixabay search built from the
                                        words of the shot that needs it
refsource.py fill  01-script/prompts/ --execute      candidates + provenance, into _candidates/
refsource.py candidates 01-script/prompts/           the lookbook — YOU pick, the script does not
refsource.py adopt 01-script/prompts/ --shot S3 --what wardrobe --pick <file>
shotlist.py <job>                       derive SHOTLIST-<slug>.md from the APPROVED script —
                                        beats, speakers and lines carried in; every shot size,
                                        camera move and performance left <NEEDS DIRECTION>
film_breakdown.py <reference.mp4> --label <name>
                                        STUDY A REFERENCE FILM — every cut time, every shot length,
                                        the cutting rhythm, each shot's camera move solved from the
                                        pixels, camera vs subject motion, a shot-size estimate, a
                                        numbered sequence sheet and an IN/MID/OUT strip per shot.
                                        It measures and has no opinions — read the sheets, then
                                        write what you see into references/specifics-catalogue.md
motion_track.py <video.mp4> --label <name>
                                        BELOW THE SHOT — motion design, UI and launch films: the
                                        camera path frame by frame; every element that moves on its
                                        own, cut out and tracked (position, scale, rotation,
                                        opacity); each animation's start, length and easing (nearest
                                        Penner curve, a fitted CSS cubic-bezier, a spring), overshoot
                                        and settle; the stagger between elements. Read its OVERLAY
                                        sheets before quoting a number
film_db.py query --move "locked off" --max-dur 2.5 --speech no
film_db.py card F4#82               THE REFERENCE DATABASE — 1,122 shots from five festival
film_db.py facets [--film F2]        AI shorts, every one MEASURED (length, move, transition,
                                        palette) and READ (size, angle, light, what the performer
                                        does). Query by move, length, transition, whether anyone
                                        speaks; `card` returns a prompt skeleton; `facets` prints
                                        the distributions — with its bucket rules — so a claim about
                                        these films can be re-derived instead of quoted. Speech is
                                        stored as a count, never as the lines
film_db.py run F5#112-125            SEQUENCES — print any range as a shot-by-shot skeleton
film_db.py seq --film F4            (length · size · angle · light · performance, in order);
film_db.py cross size:light --film X    `seq` gives chapters, cadence, montage runs; `cross` gives
                                        how two categories interact, with lift. Build the shotlist
                                        in the SHAPE, with your own subject — seven templates and
                                        the rules that hold in every film: specifics-catalogue §12.
                                        Check a pooled interaction per film before relying on it
film_db.py structure --film F5       STORY + PERFORMANCE — the beat map pinned to shots (%
                                        recomputed), 20 setup→payoff pairs, and every performer shot
                                        coded for emotion, intensity 0–3 and the turn inside the
                                        shot; `card` writes a late turn as hold-then-change.
                                        Timing and acting rules that hold in all five: §13 · §14
film_db.py chain [--film F4]        CHAINING — what a cut does to performance, size, angle and
                                        time, film by film (specifics-catalogue §15)
sequence_lint.py 01-script/SHOTLIST-<slug>.md
                                        THE SEQUENCE CHAIN — reads the shotlist's chain table in cut
                                        order: fails on a key side flipping inside a scene, direct
                                        address from below, or no Contrast line; warns on the frozen
                                        camera, affinity runs, no deliberate Break, a contrast plan the
                                        rows don't deliver, the jump, the orphan reaction, the drift,
                                        and the ad baseline measured on 38 real ads (slow cutting,
                                        no wide shots, height spread; sequence-grammar §2c).
                                        --baseline prints the piece against the real-ad bands with
                                        what to revise — round 2 of the revise loop, after the
                                        director's review, at most three rounds (§2c item 14)
                                        (references/sequence-grammar.md — §2b the contrast plan, §8 the
                                        baseline table)
contact_sheet.py --clip <clip> --perf   THE PERFORMANCE STRIP — IN/MID/OUT at 15/50/85 %, read
                                        against the card v2 (references/acting-for-the-model.md §9)
contact_sheet.py events --project <job> --cut <render>
                                        THE EVENT SHEET — one tile per event of a draft cut (poster, cuts,
                                        titles, must-hits, placed sounds, end), read before anyone sees
                                        the cut; logged with qa_log.py --gate draft, fixed on a NEWER
                                        render, three rounds at most (references/review-and-approval.md §2a)
breakdown.py <job>                      THE CROSS-SHOT VIEW — every requirement across all shots,
                                        deduplicated · who is unlocked · what drifts between shots
board.py look     <job>                 THE BOARDS — one self-contained HTML page each, the
board.py concepts <job>                 thing you actually direct from. look: every sourced
board.py shots    <job>                 picture with its clearance and the palette measured off
board.py ppm      <job>                 them · concepts: five side by side with what killed the
board.py all      <job>                 dead ones · shots: every reference slot AS ITS PICTURE ·
                                        ppm: the packet — open questions FIRST, then what is built
board.py storyboard <job>               (v2.66.0) every shot in CUT ORDER as a picture (their
animatic.py <job> [--voice WAV]         sketch first), seconds, line, energy curve · the free
storyboard.py <job>                     timed reel · what `approve storyboard` still needs
board.py frames <job>                   every approved start frame on one page → approve startframes
gate.py previz <job> --budget N --why "<the decision this unblocks>"
                                        the capped concept-art lane: images before the concept is
                                        signed, max 12, closed the moment it is
prompt_lint.py 01-script/prompts/<SHOT>.frame.prompt.md        → <SHOT>.frame.prompt.ok
gate.py preflight <SHOT> --kind frame   → the exact generate_image params to send
gate.py approve frame:<SHOT> --by --quote --artifact 02-startframes/<file> --media-id <id>
gate.py approve endframe:<SHOT> ...     only when the clip declares `end_frame:` — the still it must
                                        ARRIVE at, approved like the start. Which models can take
                                        one: assets/higgsfield-rates.json → call_contract
prompt_lint.py --route <model> [--with-refs]
                                        (v2.70) WHICH prompt to write, from the model's call contract,
                                        before any prose: motion-only i2v on a true first frame, the
                                        scene form on Seedance, "unmeasured" said where it is.
                                        `--cards`: a dated card per roster model
prompt_lint.py --template scene         THE SCENE FORM (v2.49) — the default for a Seedance 2.5 clip:
                                        approved sheets bound one subject per line, the vendor's block
                                        order, the look and the sound in the prompt, no start frame
                                        (references/prompting-craft.md §12; `frame-led` switches it off)
gate.py approve character:<NAME> | prop:<NAME> | world:<LOC> --by --quote --artifact <sheet> --media-id <id>
                                        THE SHEETS a scene clip binds — one per character state, a prop
                                        sheet (new in v2.49), the location on a neutral base; the gate
                                        refuses a scene clip binding any image no approval names
prompt_lint.py 01-script/prompts/<SHOT>.clip.prompt.md         → <SHOT>.clip.prompt.ok
gate.py preflight <SHOT> --kind clip    → the exact generate_video params, frame (or sheets) bound
prompt_lint.py --template edit          THE IMAGE EDIT — one concept changed in a picture that exists:
                                        [SOURCE] [KEEP] (≥ 4 of 8 named) [CHANGE] [LIGHT MATCH] [OUTPUT]
prompt_lint.py 01-script/prompts/<SHOT>.edit.prompt.md         → <SHOT>.edit.prompt.ok
gate.py preflight <SHOT> --kind edit    → the generate_image params, the source picture first
gate.py approve target:<SHOT> --by --quote [--artifact <the source frame>]
                                        only for `use: target` — the owner's per-shot opt-in before an AI
                                        edit of our own footage becomes a model reference (2026-10-28)
prompt_lint.py --template genjutsu      GENJUTSU (v2.46.1) — motion transfer or object swap on a SOURCE
                                        video, full or Lite (Lite first: 10 free gens vs 1):
                                        <SHOT>.genjutsu.prompt.md → approve genjutsu:<SHOT> --artifact <spec>
                                        → preflight <SHOT> --kind genjutsu; every take asks
                                        (references/ai-generation.md § Genjutsu)
prompt_lint.py <new>.prompt.md --against <old>.prompt.md --note "<the correction>"
                                        THE ONE-VARIABLE CORRECTION — how many variables this
                                        pass actually moved, how much solved work survived
                                        verbatim, and whether the note names a replacement
                                        state or just says "better" (refinement-loop.md §1b)
gate.py approve clips / music / lock / export     the post chain, in order
skill_audit.py --root . --supersessions what this skill has changed its mind about — every
                                        declared supersession and in-place correction, and whether
                                        any old claim is still live and unlinked (§5b)
gate.py approve eval --by --quote --artifact 00-brief/EVAL-PLAN.md
                                        THE EVALUATION LANE (v2.72.0; `Tier: evaluation` + `Lane: eval`): one
                                        plan instead of concept and script; its shots, takes per shot and budget
                                        bind every call (references/ai-generation.md, the evaluation tier)
gate.py allow image|video --shots S1-S10 --by <name> --quote "<their words>"
                                        ONE approval for a batch and 2 regens per shot (no prompt
                                        per regen; still linted) · `--list` · `--revoke A1|all`
gate.py allow resolve --scope edit,render --scripts N --hours H --by <name> --quote "<their words>"
                                        ONE approval for a session's DaVinci Resolve scripts, in a
                                        batch like the AI generations; renders are
                                        still never started, deletes still ask (environments.md §3.9)
gate.py status [--full]                 development, approvals, allowances, linted prompts, what is owed
                                        next — fast by default; --full re-lints (preflight always does)
gate.py pre-lock --write [--host-job P] the cut, titles-off and picture-only renders queued as
                                        render-mp4.py copies, and what `approve lock` still needs
gate.py where                           the scripts of THIS install — run them from here, never from a
                                        remembered path (the plugin can be reinstalled mid-session)
gate.py reconcile transactions.json     after: every credit spent outside a linted prompt
```

**What the gate refuses, and why each refusal exists:**

- **No open job → deny everything.** Chosen on purpose ("deny everything", 2026-09-06). A quick
  experiment opens a job too; the checkpoint takes five minutes and the alternative cost real credits.
- **A checkpoint with a placeholder, a client profile that does not exist or whose §0 is
  unanswered, a verification policy that is missing or disagrees with the profile.** An unanswered
  hard lock is a question for the client, not a default (`clients/_TEMPLATE.md` §0).
- **`script` not approved.** All policies. The script review is the one that saves the most money
  (`references/review-and-approval.md` §10). The approval carries the file and its hash.
- **A script with no development behind it.** `approve concept` and `approve script` run
  `scripts/develop.py`, which refuses until `00-brief/DEVELOPMENT.md` carries research at the tier
  the decision needs (2.69 template: `tier:`, T0 one line, T1+ lines that each name what they decide, the lines
  the person named as mattering and the rest deleted, their objective, keep-or-break per concept, and at T2+ an
  audience phrase in the picked hook; older templates keep ≥6 sourced lines;
  `references/preproduction-research.md` §2.1b), **≥5 concepts that are provably different** (distinct dramatic question, distinct opening
  image, ≥3 structures, pairwise overlap under 55% — five rewordings of one idea fail), **≥2
  adversarial rounds that each killed or weakened something** from a named hat, the **human's pick
  with their verbatim quote**, ≥5 hooks across ≥3 types, and **≥3 drafts (4 on the 2.67 template) with a
  specific critique between each**. One draft is the cheapest thing an agent produces, and every gate after the script
  validates a mediocre script perfectly executed.
- **A stage signed out of order.** The chain is `concept → script → storyboard → cast/frame → startframes →
  audio → clips → music → lock → titles → export` (`storyboard` and `startframes`, v2.66.0, for jobs made from the
  2.65 development template or later: `references/storyboarding.md` §6); `lock` (picture lock) additionally needs a real `09-qa/QA-LOG.md`, the
  motion analysis and the project's title card; `titles` needs every title the card permits rendered
  and passing `title_qa.py`. Grading
  or timing captions to an unlocked cut is the classic way a day of post gets thrown away. An evaluation job with
  `Lane: eval` (v2.72.0) has a chain of one: its approved plan, then its frames and sheets.
- **A prompt that is not identical (after whitespace and curly-quote normalisation) to a prompt
  file that `prompt_lint.py` passes *right now*, or sent with a different model, duration, count or
  resolution, or with params the file does not declare.** The lint is re-run at hook time, so a
  hand-written `.ok` sidecar buys nothing. The prompt is authored in `01-script/prompts/`, linted,
  and pasted verbatim — `gate.py preflight` prints the whole call so the gated path is *less* work
  than a hand-written one.
- **A reference that was planned but not sourced, or sourced but not cleared.** Every `refs:`
  entry declares the ONE attribute it carries; a `file:` must exist on disk with a provenance
  sidecar — written by `scripts/provenance.py record` for any asset, or by `pixabay_search.py` on
  download, and clearance there is **derived from the four §5 blockers, never typed** — and an
  uncleared asset fails unless marked
  `use: reference-only` with the likeness kept out of the output (`references/stock-sourcing.md`
  §5, §9). A character or product frame with **no** reference fails — identity is locked by a
  reference, never by text. And the rule the plan exists for: **the prompt may not re-describe an
  attribute a reference already carries** (`references/prompting-craft.md` §6b — reference the
  nouns, prompt the verbs). All of it is checked *before* the call, not judged after the render.
- **A clip whose start frame is not approved, or that does not bind the approved frame's media id.**
  Every i2v clip starts from a still a human approved (`references/prompting-craft.md` §1); the frame
  gate is the one-way door with ~10× leverage (`references/realism-qa.md` §6). **v2.49:** a scene-form
  clip (`form: scene`, no start frame) is refused instead when it binds no approved sheet, or any image
  that is not an approved `character:`, `prop:`, `world:` or `frame:` media id — the sheets are its
  approval point (`references/ai-generation.md`, the reference route).
- **Sound the file did not decide.** The call's `generate_audio` must equal the linted file's. Native
  diegetic sound is kept by default since v2.49 and needs no approval; **speech** still does — a clip
  with lines and `generate_audio: true` is refused until `audio` is approved (the `guide-audio` switch
  restores the old rule for one job; `references/editing-and-audio.md` §7d).
- **GPT Image 2.6 called on its defaults** (quality `low`, resolution `1k`): the call sends the file's
  quality and resolution, its `output_format`, and a `batch_size` no larger than `variants:`.
- **A VO text that is not exactly one spoken line of the approved script, on a model that is not
  a speech model, or with no voice chosen.** Wording is locked; a change cascades VO → clip → edit →
  captions (`references/revisions.md`).
- **Under `per-stage-human`:** `audio` approved before a dialogue clip, and every spend — frames,
  clips, VO — is *ask*: the UI prompts the human per call. ⚡ **Unless an allowance covers it**
  (one click per regen is too many). Ask the human once for the batch *and* its
  regens, then record their words: `gate.py allow image --shots S1-S10 --by <name> --quote "<their
  words>"`. Each shot then gets its first generation and 2 regens (`--regens N`) without a prompt, under
  any policy. Every call is still linted in full. The gate asks again when a shot has used its
  generations, or for a shot the allowance does not name. Audio and the unlintable tools still ask
  per call.
- **A `count` above the prompt file's `variants:`.** A variant multiplies the spend; declare it.
- **A Kling-connector call whose prompt is not a linted Kling prompt of the right kind; Higgsfield motion control (it takes no prompt); an upload or identity element with no job open; any Scenario run or upload — Scenario is not a provider this plugin uses** (`references/prompting-craft.md` §11g).
- **An identical generate request within 30 minutes of one this job already submitted asks first** — poll that job instead.
- **Any other credit-spending Higgsfield tool** (upscale, dubbing, voice cloning,
  reframe, outpaint, apps…) without an open job; inside one it always *asks*, because the gate
  cannot lint what it cannot read. **Publishing** (`tiktok_publish`) needs the job's `export`
  approval. Read-only tools (`models_explore`, `show_*`, `balance`, `jobs_wait`) pass silently.
- **A DaVinci Resolve MCP script that starts a render, generates speech or auto-captions from
  audio** (`run_script` on the server inside Resolve Studio 21.1) — each routes around a gate this
  skill already has. Render settings, deletes and project switches *ask*; `run_script_unsafe`
  always asks (`references/environments.md` §3). **The computer-control rule (v2.49):** a script that **writes**
  Fusion, Fairlight or a native title is **denied** too, with no allowance to cover it — that work is
  done by computer control in Resolve's interface; reads stay open
  (`references/editing-and-audio.md` § What runs through the API).

**Approvals are the human's words.** `gate.py approve … --quote "<their reply verbatim>"` after
they have seen the artifact — ask with AskUserQuestion or the client's review channel, then record.
Where the hook has recorded the session transcript, `approve` **refuses a quote that appears in no
human turn** and marks the rest `transcript`-verified; elsewhere the row is marked `UNVERIFIED` and
the ledger keeps the timestamp and the file hash so a later reader can check. The artifact must be
a file under the job. Writing a quote nobody said is the lipsync incident again.

**The trust boundary, stated once.** The gate holds against an agent that follows the rules and
against honest mistakes. It does not hold against an agent that edits `gate.py`, `hooks/hooks.json`
or the ledger — same-user write access makes that one command. The checks on *that* are outside the
scripts: the Bash permission prompt, `git diff` on the skill folder, `skill_audit.py` (a hook path
that does not resolve fails it), and `reconcile` against the platform's own transaction log.

**The checkpoint is a file** — `00-brief/CHECKPOINT.md` from `assets/checkpoint-template.md`. It
carries the same lines the old typed block did (mode, client, policy, format, voice, inputs
PRESENT/MISSING, gates, skips with reasons, budget with provenance, approver, next), plus
`Switches:`, the house rules this job lifts, each with its reason, or `none` (§3; v2.48.0), and it is
refused with the exact line to fix. `Skips:` still exists: a declared skip is allowed, a silent one
is not, and the difference is now visible in a file rather than in a paragraph.

**Where hooks do not fire** (a Cowork session may not run plugin hooks), the discipline is the
same and you are the hook: no generate call without `gate.py preflight` printing "would PASS", and
`gate.py reconcile` on the transaction log before the job closes. The scripts are cheap (~50 ms)
and they are the only things here that cannot be satisfied by narration.

---

## §1 · Route — three lookups before a word of script

**First · What is being asked?** Not every ask is a production. Find the row, read its files
before answering, and use its tools. A row with "no spend" never opens the spend gate.

| The ask | Read first | Tools | Hand back | Gate |
|---|---|---|---|---|
| **Make** a video or stills | `modes/_INDEX.md`, the mode file, then 1a–1d and §2 | `gate.py open` | the job folder | the full gate (§0) |
| **Review** a cut, a take, a board or a script | `references/craft-cheatsheet.md` · the client profile §0 · `references/realism-qa.md` §6–§6b · `references/review-and-approval.md` §11 | whichever fit what was handed over: `contact_sheet.py` · `sequence_lint.py` · `clip_qa.py` · `motion_qa.py` · `look_qa.py` · `mix_qa.py` · `export_qc.py` · `script_score.py` · `claims_lint.py` · agents `cine-take-reviewer`, `cine-scene-continuity`, `cine-script-critic` | findings, each with what was observed and the rule it cites, each marked measured or judged | no spend |
| **Study** a reference film or ad | `references/shot-relationships.md` · `references/sequence-grammar.md` | `film_breakdown.py` · `motion_track.py` · `shot_graph.py` · `film_db.py` | a breakdown note. The tools measure; the reading is yours and is marked as a reading | no spend |
| **Plan and price** a job | `references/pm-workflow.md` (capacity and credits) · `clients/costs.<brand>.json` · the client's capacity file where one exists | `rate_card.py` · `estimate_duration.py` · `batch_plan.py` | one page: shots, credits, approvals, days, risks; every number tagged measured, estimated or assumed | no spend |
| **Fix** one shot | `references/production-runbook.md` §7b | `prompt_lint.py` · `region_repair.py` · `gate.py preflight` | the retake | the full gate: §7b skips none of it |
| **Explain** the skill | `START-HERE.md` · `GLOSSARY.md` | none | a plain answer | none |

A price is quoted only from `rate_card.py`. A review or a study that needs DaVinci Resolve with no
job open goes through `gate.py allow resolve`, which the human grants.

**1a · Mode** → `modes/_INDEX.md`. A · Narrative Promo (one video carries the message) · B · UGC
Volume (a monthly number; **a trial batch is B even when small**) · C · Editorial / Explainer ·
D · Repurpose. State the mode in the checkpoint; when ambiguous, ask.

**1b · Client** → the `_INDEX.md` in your client folder, then `clients/_INDEX.md`, then the profile
`<brand>.md`. **No profile = stop and ask.** Copy `clients/_TEMPLATE.md` into your client folder, fill it
with the client, add the index row; the gate refuses a job until §0 (mode, hard locks,
`**Verification policy:** \`value\``, approver) is answered. Your client folder is the one
`CINE_CLIENTS` names, or a `_cine-clients/` folder above the jobs; the plugin's own `clients/` holds only
the templates, `_lab` and one invented sample, and a plugin update replaces it. Read the profile's §0
hard locks before writing anything — a locked script or a no-overlays rule invalidates advice
elsewhere in this skill, and the profile is the only place that knows.

**1c · Episodes** → N ≥ 2 is a series batch (`references/series-parallel.md`; `series_batch.py`
refuses a batch of one); N = 1 is `references/production-runbook.md` unchanged.

**1d · Where the ask lands on the ladder.** Most requests arrive mid-pipeline — *"write me the
hooks"*, *"give me the shot list"*, *"just do the start frames"* — and the failure they invite is
producing the artifact from this file alone, because SKILL.md is already loaded and the stage's
references are not. **A request for a stage's artifact is a request for that stage.** Find its row
in §2, read the files in its *what to read* cell **before** producing anything, write the artifact
to the path that row names, and run the check in its last column. A hook bank written straight into
chat is not a hook bank: the artifact is the Hooks table inside `00-brief/DEVELOPMENT.md`, and
`develop.py check --phase full` is what says it is finished. This applies even when the ask is small
and the answer seems obvious — **"obvious from this file" is exactly the state the stage references
exist to correct**, and the one time it was measured, the stage file went unread and the output was
wrong in the two ways that file is about.

---

## §2 · The stage ladder — what to read, what it must produce, what consumes it

The reference registry is `references/_INDEX.md` (every reference file, classed core / extended). **This table
is the loading rule, not a menu:** at each stage the named files are read *before* the artifact is
written, because the artifact is what the next gate checks. A stage whose artifact does not exist
did not happen.

**The Hat column is the role whose judgement the stage needs.** One person wears them all here;
naming them is what stops the producer's convenience from quietly overruling the editor's cut or
the compliance officer's veto.

| # | Stage | Hat | Read before writing | Artifact | Consumed by |
|---|---|---|---|---|---|
| 0 | **Intake** | producer | `modes/<mode>.md` · `clients/<brand>.md` §0–§5 · `references/delivery-format.md` §6 · `references/preproduction-research.md` | `00-brief/CHECKPOINT.md` · `BRIEF-<slug>.md` · `clients/script.<brand>.json` filled · the brief carries the client's own opening, offer description and ask, in their words, written before development starts (`preproduction-research.md` §1.1) | `gate.py open` |
| 1 | **Development** — ⚡ their voice first (v2.65.0: the taste session, their material and one picture of theirs, BEFORE any concept), then research, divergence, the kill rounds, the pick | writer + director, adversary, **client picks** | `references/ideation.md` §0 (their voice first: ask three at a time, quote them, never rewrite them; their seeds become concepts; the pick is shown shuffled with the recommendation last) · `references/preproduction-research.md` §2.1–§2.1b (the tier from the decision; lines that name what they decide; the person names what mattered, v2.69.0) · `references/ideation.md` §2b (keep or break, once per concept) · §3–§6 (diverge, the angle grid, concept-not-idea, kill tests) · `references/persuasion-psychology.md` §2 (awareness picks the hook) · `references/hook-craft.md` (the anchor/gap rule and the gap's three legs) · `references/discovery-and-search.md` §5 (the search terms are demand data, and they come BEFORE the hooks) · `references/research-quality.md` | `00-brief/DEVELOPMENT.md` — research at its tier, each line naming what it decides, the person's `research that mattered` and `objective` · **4+ real reference pictures on disk with provenance, before a concept is written** · **5+ different concepts** · **2+ adversarial rounds, each killing something** · the human's pick, quoted · 5+ hooks across 3+ types, **each with its gap written** (the full bank still gets written when a real shoot will later film only two or three openings and asks as modules around one body: `hook-craft.md` §8) | `board.py look` → `develop.py check --phase concept` → `board.py concepts` → `gate.py approve concept` (both boards must be current) |
| 2 | **Script** — drafts and critiques, not one guess | writer, director, **compliance** | `references/script-craft.md` §1–§3 (§2d, v2.51: the measured bands from real scripts, printed by `script_score.py`), §6, §7b (v2.49: written in four passes — story logic · coverage, enough shots each with a function · continuity · cut-down and read-aloud timing — then TWO short options shown to the person, each keeping one sentence of theirs, checked by `develop.py` § Script options, v2.65.0) · `references/hook-craft.md` §8 (writing the hook, in order) · `references/comedy-craft.md` §1, §3, §9 when any execution is humorous (the gate is negative reaction, not funniness) · `references/script-format.md` (the scene count is derived: `beat_plan.py`) · `references/compliance.md` | `01-script/SCRIPT-<slug>-v<N>.md` (**3+ versions, a specific critique between each**; v2.67.0 template: the four writing passes, then at most two fixes, `script-craft.md` §7) · **v2.67.0:** a cold read on v1 or v2 and on each option (`cine-cold-reader`, the script file only; `develop.py stamp`) · beside each option `hook asks:` / `ending answers:`, `cannot swap:`, and their answer to the comedy question (`develop.py options` prints them side by side) · `carried by:` on each scene (a writing rule; not checked) · `script_score.py --client --brand <name>` PASS (v2.69.0: it reads the person's `objective:` from DEVELOPMENT.md; that switches the brand-in-hook note only, never the emotional register) (mechanical only, with each block's speech against its picture time; the 1–10 card in §6 is the writer's note, never gated) · `claims_lint.py` clean | `develop.py check` (full) → `gate.py approve script --artifact` (**`--paid` or `--no-material-connection`, and `--allow` per client-approved phrase**; the approval archives the script and writes the video's ledger record) |
| 3 | **Storyboard & direction** — ⚡ v2.66.0: their sketches first, then the film as panels in cut order and a free animatic, signed as `storyboard` before any paid picture | director + 1st AD, **client signs** | `references/storyboarding.md` (§2 ask for their pictures, §3 the page, §4 the animatic, §6 what the gate checks) · `references/direction.md` §1–§3 (⚡ §2b the shot event card and §2c five-then-kill-four are what stop a shot arriving with nothing in it) · `references/sequence-grammar.md` §2–§8 (the chain, §2c how 38 real ads cut and move, and §8 the table that combines every channel per beat) · `references/acting-for-the-model.md` §7 (card v2) · `references/shot-handoff.md` §5–§6 · `references/emotional-journey.md` §2–§3 · `references/craft-cheatsheet.md` | `01-script/SHOTLIST-<slug>.md` — blocking card per scene, performance card v2 per dialogue clip, the sequence chain (one row per shot), FUNCTION per insert, handoff fields · **the title card** `00-brief/TITLE-CARD.json` (`title_card.py propose <job> --lane ads\|brand\|drama\|golf\|property\|captions-only`, the brand's font files and accent; approved with the storyboard — the permission list for titles, and the transition and ramp budgets: `references/typography-and-captions.md` §6c) | `shotlist.py <job>` derives it from the approved script and marks what the director owes; `shotlist.py --check` counts it · `sequence_lint.py` (the chain) · `prompt_lint.py` (a dialogue clip with no performance card fails; an insert with no `function:` fails; the v2 gaps warn; a `ramp:` outside the C4 rules fails; an aerial, FPV, insect or planet clip without its `aerial:` declaration — a job, a subject, a last frame, a real seed for a real place — fails, `references/aerial-and-fpv.md`) · `title_card.py lint` · golf and property: `flyover.py course init` / `property init`, and `flyover.py pilot` for a real drone day (DJI's presets mapped to the moves) · **v2.66.0:** `## Their sketches` in the shot list → `board.py storyboard` → `animatic.py` → `storyboard.py <job>` (what is still missing) → `gate.py approve storyboard` |
| 4 | **Casting & design** — the reference set, **sourced before a prompt is written** | casting + production designer + DP | `references/character-and-props.md` · `references/production-design.md` · `references/world-design.md` (every exterior: the world before the frames) · `references/cinematography-craft.md` §7 · `references/photorealism-physics.md` · `references/stock-sourcing.md` §5, §9 (the per-asset blockers and the provenance record) · `references/prompting-craft.md` §6b | **the world card for every exterior location** (`world.py init <job> --location <LOC>`: sun, Beaufort wind, WMO sky, visibility and depth layers, land, water, background life cast with numbers, the place's plausible life with sources; `references/world-design.md`), approved before any frame of it (`gate.py approve world:<LOC>`) · `_reference/` — one attribute per file, each with its provenance sidecar (`provenance.py record` for client-supplied and own-shoot assets, `pixabay_search.py` on a stock download; `provenance.py audit _reference/` is the set view). A slot the shot needs but nobody has sourced is written `need: <what to look for>` in the prompt, and `refsource.py` brief → fill → **you look** → adopt is how it gets filled · `_reference/CHARACTER-<name>.md`, the fixed block every frame is compared against, with the voice string written once (`references/prompting-craft.md` §9.4b) · **v2.49, the sheets a scene clip binds** (`references/character-and-props.md` §8.3g): one per character state, the location on a neutral base, a `prop:` sheet per hero prop, a wardrobe and props sheet per scene before anything animates, look-alikes one colour each — made on GPT Image 2.6 at `quality: high`+ and 2k+ (`references/ai-generation.md` Step 1) | `prompt_lint.py --plan` (the reference plan) · `breakdown.py` — the cross-shot view, and `approve cast` refuses while a character is unlocked · `board.py shots` — every slot as its picture · `gate.py approve character:<NAME>` · `approve prop:<NAME>` · `approve world:<LOC>` — each with the sheet's media id |
| 5 | **Start frames** — the boards you actually shoot (v2.49: for i2v clips; a scene-form Seedance clip has none, its sheets are approved at stage 4) | director + DP | `references/prompting-craft.md` §1–§2, §6b · `references/ai-generation.md` Step 1, Step 3, the guardrail table · `references/blocking.md` when the shot needs blocking (§1) · `references/aerial-and-fpv.md` for an aerial (§2 the move table, §3 the prompt) | `01-script/prompts/<SHOT>.frame.prompt.md` → `.ok` · an image edit is `<SHOT>.edit.prompt.md` (`kind: edit`, `edit_of:`), never a frame with an edit inside it; `use: target` needs `approve target:<SHOT>` (an exterior names its card, `world: <LOC>`, and is linted against it: no uncast mover, no sky, wind or night word that contradicts it, no mover added by an edit, the ⚑ warnings answered with `world.py accept`; a noticed problem is a stop, `world.py stop`) · `02-startframes/` · `02-startframes/_blocking/<SHOT>/` (`blocking.py build`) | `gate.py preflight --kind frame` → **the frame gate** (`approve frame:<SHOT> --media-id`; a blocked shot also `approve blocking:<SHOT>`; a family of inserts, `approve family:<FAMILY>` on one contact sheet, `references/dr-advertorial.md` §4) — this is the PPM: nothing moves until the boards are signed · **v2.66.0:** then `board.py frames` → `gate.py approve startframes`, every approved frame side by side before any clip (`references/storyboarding.md` §5) |
| 6 | **Voice** | director + sound | `references/ai-generation.md` Step 4 (the two lipsync paths) · profile §2 voices · `references/script-craft.md` §5 | `05-voice/` | the hook: the line must be one spoken line of the approved script · `gate.py approve audio` |
| 7 | **Clip prompts & generation** | director + DP | `references/prompting-craft.md` §1–§5, §9, §12 (v2.49: a Seedance 2.5 clip is `form: scene` — the sheets bound one subject per line, the first frame with the action under way, optics in degrees and mm with distances in metres, one camera behaviour, timed beats, mouths closed unless a line is scripted, `[AUDIO]` with ambience, effects and no music, positive locks; 2,500–20,000 characters) · `references/ai-generation.md` § Sound (native diegetic sound kept; speech through the voice gate) · `references/motion-craft.md` §6 (what the MOTION block must contain), §6b–§6c (the intent behind every movement, and a start frame made for it) · `references/acting-for-the-model.md` §7b (the movement persona of a cast person) · `references/motion-design.md` §2, §5 · `references/ai-generation.md` Step 2 · `references/multishot.md` for a clip that cuts inside one generation · `references/shot-handoff.md` §1–§3, §4b (motion planned to hand off across the cut: `exit:` / `enter:` / `join:`) · `references/refinement-loop.md` §1–§3 when a shot comes back wrong · **v2.70:** `prompt_lint.py --route <model>` first; `sheet_split.py split <sheet>` when a test needs the face and body as separate images; `genlab.py` for a take log and a blind two-arm A/B (spends nothing; a run needs your yes) | `<SHOT>.clip.prompt.md` → `.ok` (motion only on an i2v clip; the whole shot in the scene form) · `03-clips/` `04-broll/` · `SHOTS-<slug>.json` rows — the script supervisor's log: every retake is a row with the one variable changed | `gate.py preflight --kind clip` · the hook, every call · `clip_qa.py --motion-profile` over the finished clips · `gate.py reconcile` after |
| 8 | **Selects & QA** — the dailies pass | director + editor | `references/realism-qa.md` §6–§6b (and V7b: around every action point, every 2nd frame — `action_points.py <clip> --permanence`; a thrown object that comes back fails; the prompt side is `references/prompting-craft.md` §6.4b) · `references/timing-and-performance.md` §8 · `references/direction.md` §3 · `references/motion-craft.md` §3 | **v2.70:** `look_qa.py shots` reports each take's first-frame match to its approved still; the take reviewer gets the approved sheets and the permanence strip and returns `identity` (drifted → HOLD, held to the rule by `fanout.py check`) · `09-qa/QA-LOG.md` via `qa_log.py` (refuses a verdict without an observation; a speaking clip needs a word you heard; **`SELECT`/`BACKUP` are the selects gate's third state**) · contact sheets over `03-clips/_review/` and `02-startframes/` — **what came back, not what survived** · **v2.49, the scene board before any approval request** (`references/review-and-approval.md` §11): every shot of a scene side by side against its sheets — lens, camera height, subject size, distances, props, wardrobe, light, time of day — fixed toward the sheet, the comparison listed in the request; manual until a script measures it | `gate.py approve clips` (**refuses a speaking scene with no listener reaction** — the coverage floor; **and an exterior clip not read against its world card** — `world.py read`: the movers counted, nothing new, on the take's own bytes) · `motion_qa.py clip` on every selected take (camera, framing, subject direction in and out, action points, against the plan) · `clip_qa.py --motion-profile --look-profile --cut-plan` over the finished clips · `breakdown.py` (one camera, or several?) · `series_join.py` when N ≥ 2 — silence is a FAIL |
| 9 | **Music** | director, **client chooses** | `references/persuasion-psychology.md` §4 (the bed changes what the picture means) · `references/stock-sourcing.md` (the licence) · `references/editing-and-audio.md` § Music bed (the compose policy) and § The lead composer | `06-music/` + the licence/provenance sidecar · **v2.68.0:** the person points to their licensed music once (`music_fit.py library add <folder> --paid-ads …`, catalogued and measured), then `music_fit.py shortlist <job> --mood "<the brief's words>"` brings 2–3 cleared cues with reasons (`references/editing-and-audio.md` § Music bed) · `music_fit.py map` (beats, downbeats, phrases, the ending) · `06-music/COMPOSER-BRIEF.json` (`composer.py brief`: references and why each is liked, role, VO density, lengths, the mnemonic, consent) · the client's motif (`composer.py motif draft` → **the owner edits** → `motif adopt`) | `gate.py approve music` — ⛔ **always ask which track; never an autonomous pick** |
| 10 | **Assembly → rough → fine cut** | editor | `references/editing-storytelling.md` (where the cut goes and why) · `references/editing-and-audio.md` · `references/revisions.md` when notes arrive | `07-edit/` versioned cuts · client rounds recorded in `09-qa/review/` · once the cut is locked, `07-edit/music/HITS.json` (`music_fit.py hits init`: the 2–4 must-hits) → `fit` → `rebuild` (the plan as an edit of the ORIGINAL track, `07-edit/music/REBUILD.json`; its segments placed on A5 by the console copy, the crossfades and fades made in Fairlight by computer control; `render` is a preview only, never imported; **the cut never moves by itself** — a 1–2 frame nudge is listed for approval) · `07-edit/music/SPOTTING.json` (`composer.py spot`) · the composed layer, family, cues or generated bed (`composer.py layer` / `family` / `solve`→`plan`→`realise`→`render` / `generated record` + `bakeoff`) and `composer.py console` — everything lands in Fairlight on named, coloured tracks | `references/review-and-approval.md` |
| 11 | **PICTURE LOCK** — the one-way door of post | editor + director + **client** | `references/review-and-approval.md` §2 · `references/revisions.md` (what a change costs after this) | the locked cut, and the QA log behind it | `gate.py pre-lock --write` (the three renders lock reads, queued at once, and what is left) · `motion_qa.py cut` on the newest cut, then `gate.py approve lock` (refuses without `09-qa/QA-LOG.md`, and **without the motion analysis**: a current `motion_qa.py clip` report for every shot in the cut and a joins report on the newest cut — `references/shot-handoff.md` §4b; **the cut inside its transition and ramp budgets** from `07-edit/timeline-dump.json` — at most 2 accents, a dip only at the end, nothing on a dialogue clip, whips ≤ 2, one ramp per 20 s and 2 per video, every slow-down cleared by `motion_qa.py warp` — `references/editing-and-audio.md`, the budget and § The ramp; and **without a title card that lints clean**; and **without the aerial rules holding** — `aerial_qa.py check` and `flyover.py check`: every aerial declared and on a real seed where the place is real, the course or property card, the overlays and `09-qa/aerial/RIGHTS.md`; the measures and the cut notes only warn; and **the sound-off read** — advisory, since a story fix is cheapest now (`soundoff.py proofs <job> --cut <file>`, `map init`, `map set` each beat from the muted proof), except that a beat the picture does not carry, unfixed and unwaived, refuses: `references/sound-off-story.md`). **Nothing downstream starts before it** — captions timed to an unlocked cut re-conform, a grade on an unlocked cut is done twice |
| 12 | **Mix · grade · captions · titles** | sound mixer + colorist + designer | `references/editing-and-audio.md` (stems, the undipped M&E a language version needs, 48 kHz) · `references/typography-and-captions.md` (§6c the project's titles) · `references/brand-system.md` | `08-captions/<slug>.srt` (`build_srt.py`) · **captions, titles and supers made in Resolve** (the native-elements rule: Resolve's or Fusion's own elements by default, never made outside without a reason): `native.py console <job> --srt …` → the console's `PLACE_SUBTITLES` (the `.srt` on a Subtitle track, styled once, burned by `render-mp4.py BURN_SUBTITLES`) and the titles (each title spec in `07-edit/titles/<id>.title.json`, anchored to a picture event, as the card's generated Fusion title (`fusion_titles.py build`), installed and placed on its named track — Titles · Supers · Disclosure — **by computer control** (v2.49, the computer-control rule: titles, Fusion and Fairlight never through the API), checked on a full-size still, frame 0 and the last frame included, its words read back by the API); outside Resolve (`build_captions.py`, HyperFrames, supers-gsap) only with one of four recorded reasons (`native.py reasons`) · graded timeline · mix to the preset's loudness · the dialogue stem and the bed (ducking on) for the mix gate, and the audio manifest, in `09-qa/mix/` · a hero title as up to three options for the owner to pick · **the style frame** first — one approved still sets the face, the scale, the ink, the margin and the one emphasis device (`title_card.py style-frame`; `title_card.py fit` before anything renders; `native.py sync-specs` once titles live in Resolve — `references/typography-and-captions.md` §6c items 9–10) · the bed as the client hears it (`music_fit.py bed`: `BED.json`, a level plan at the client's level under the voice, `clients/audio.<client>.json`, made in Fairlight by computer control; the `.bed.wav` is a preview) and the effects levelled by measurement (`sfx_conform.py levels`) — `references/editing-and-audio.md` | `export_qc.py` · `mix_qa.py measure` (the VO over the bed while it speaks, on a phone too, the short-term ceiling, mono fold-down, room tone, a take's own sound; `references/editing-and-audio.md` §7b–§7e) · `mix_qa.py licences` (every sound's licence covers paid ads) · `sfx_conform.py` (v2.49: it measures and proposes, and every hit is placed in Fairlight by computer control — its renders are proofs, not deliverable audio; every hit conformed to the shot: one per event, on its frame or a frame late, level, tone and room from distance, force, size and the read of the material, in a measured room when one fits; the sound searched in the machine's libraries first — v2.68.0: `library measure` (each attack's shape, stored in the catalogue), the dispatcher's `library sheet <job> <shot>` (five candidates per event with reasons; identity first, the measured shape as tie-break; paid-ads-cleared only), the attack inside a file chosen by its shape, and the blind listening test (`library blind` / `blind-score`) before trusting the ranking — `library search` / `library pull` — Fairlight, Final Cut Pro and the 18 Ocular Sounds packs, which pack for which job in §7f; `references/editing-and-audio.md` §7f) · `look_qa.py shots` then `grade_luts.py plan --console` (each model's correction LUT on its colour group, the shot-match CDL, Deflicker where it flickers, the lane's look; open shadows, grain only where it survives — `references/editing-and-audio.md`, the grade; `references/realism-qa.md` §4 C1–C4) · `title_card.py titles` (each spec against the card: its engine, permitted kind, words, dwell by regime, its anchor after the 0.4 s settle, never across a transition or a ramp) → `title_qa.py native` on Resolve's renders with the titles on and off (`render-mp4.py TITLES_OFF`), or `title_qa.py check` on an outside render (safe box, worst-frame contrast, the 390 px phone proof, dwell, no overshoot, captions, faces) → `gate.py approve titles` (after lock; every title measured and passing on those bytes) · `srt_qa.py burned` (every caption in the delivery file's pixels) |
| 13 | **QC & compliance** | post supervisor + compliance | `references/compliance.md` (claims, endorsement, AI disclosure — three separate obligations; §2b material-connection disclosure, which a repost does not inherit) · `references/discovery-and-search.md` §6 (watermark, originality, text coverage — eligibility, checked on the export) · `references/delivery-format.md` · `references/realism-qa.md` · `references/sound-off-story.md` (the client's check: the story with no sound and no voiceover) | `export_qc.py --format` PASS (resolution, fps, duration, loudness, true peak) · `slop_check.py` · the disclosure burned in | `look_qa.py export` (range and Rec.709 tags, legal levels, 45+ legibility, the platform round trip: banding, blocks, grain) · `gate.py approve export` (refuses without `lock`, `music` and `titles` approved, a passing export_qc report, a passing mix report and a passing look report on each render's bytes, a clean audio manifest, the titles still as cleared, **text made in Resolve** — `native.py check`: a delivery file ffmpeg made needs a recorded reason, Resolve's caption burn needs a `srt_qa.py burned` PASS on its bytes, every outside render printed with its reason; and **the music fitted to the locked cut and rebuilt in Resolve** — `music_fit.py check`: a current `REBUILD.json` (no render is asked for), no preview render on the timeline, no cut moved without an approved nudge, no click at a seam of the music stem Resolve exported, the ±2 % stretch cap, no sung lyrics under speech; hit offsets only warn, and with no stem yet a note names what to export — `references/editing-and-audio.md` § Music to picture; and **anything composed or generated cleared** — `composer.py check`: the paperwork, the owner's motif edit, the confirmed key, the palette and instrument licences, consent before generation, the vendor whitelist and terms snapshot, AI vocals' record, a blind bake-off this quarter, the element sheet — § The lead composer; and **the client's sound-off check** — `soundoff.py check`: T2, the picture alone with no voiceover or its captions, passed by someone who has not read the script and whose retell was logged first; T1, the muted feed, on every delivery file (blocking unless a sound-on-only plan is recorded in the owner's words); each on a proof of these exact bytes; the story map read beat by beat; the captions measured (`srt_qa.py`); every spoken number on screen — `references/sound-off-story.md`; then `soundoff.py pack` for the client) → `ledger.py deliver <job> --by <who>` → `ledger.py publish <job> --platform <p> --post-id <id>` (the ORGANIC metrics join — no platform export carries a field we control) |
| 14 | **Delivery & wrap** | producer | `references/pm-workflow.md` (the delivery manifest, the ad-name join key) · `references/self-evolution.md` · `references/performance-metrics.md` after it runs | `10-export/` + `DELIVERY-<YYYY-MM>.md` · `99-costs/` reconciled (`reconcile_costs.py`, `gate.py reconcile`, and `gate.py reconcile --files` for media made outside the gate) · the episode note · the board closed | the client · the ledger |

Stage-specific depth lives in the registry: `references/real-and-ai.md` when real footage is in the
mix, `references/style-transfer.md` for "make it feel like <director>" (the name never goes in the
prompt), `references/brand-system.md` and `references/series-continuity.md` for a look held across
episodes, `references/micro-drama.md` for a short-drama episode or series, `references/shot-relationships.md` to read how a reference's shots relate, replicate it with new content, or check our own cut's joins before lock, `references/stock-sourcing.md` for anything licensed, `references/revisions.md` when notes
arrive, `references/performance-metrics.md` after shipping, `references/research-quality.md` when a
fact decides money or compliance, `references/environments.md` when the tooling misbehaves.

**Parallel agents (v2.50).** A stage with independent units fans out to the plugin's own agents
(`agents/`), side by side, one unit each: research questions and source or film notes (`cine-researcher`),
concepts and alternative drafts (`cine-draft-writer`), one critique axis per draft (`cine-script-critic`),
one scene's shot prompts (`cine-shot-writer`), one scene's continuity board before an approval request
(`cine-scene-continuity`), one take in the selects pass (`cine-take-reviewer`), one segment's SFX spotting
(`cine-sfx-spotter`). The main session dispatches, records and joins with `fanout.py` (silence is a FAIL), then
verifies with the stage's own scripts. Never in an agent: spend, approvals, Resolve, the browser, questions to
the owner, shared files — `references/parallel-agents.md`.

**Fast paths.** ⚡ ONE 20–40s video: `references/production-runbook.md`. ⚡ N ≥ 2 episodes:
`references/series-parallel.md`. ⚡ ONE shot with script and look locked: `production-runbook.md`
§7b — it skips intake, scripting and export; **it does not skip the gate**: the job is open, the
frame is approved, the prompt is linted.

**Scripts** are catalogued with their charter in `scripts/README.md`. Run `run_tests.py` after
touching any of them and `skill_audit.py` after touching the prose — both are the skill's own
evidence-gated checkmarks.

---

## §3 · Production defaults (the profile and the mode override)

- **Studio production settings (3.1).** The studio's answers (`/cinematographly:studio`) can set a monthly credit ceiling (a stop the gate enforces), the
  regens a batch approval covers by default (0–2), a retake factor for new clients (it only raises estimates), and a
  `second_opinion` model. The second opinion is never required, never a gate and never an approver. Offer it only at
  the script critique and the rough-cut review. **Ask the person before each send.** Unless `client_material` is `yes`,
  send a description with the client's and product's names removed, never a client file. `gate.py status` prints every
  setting with its source.

- **Delivery format is a client × platform decision — no house aspect ratio.** The preset comes from
  the profile §5, named against `assets/delivery-formats.json`; the checkpoint carries it and the
  gate checks it exists. Loudness is in the preset (−14 LUFS streaming, −23 LUFS EU broadcast — not
  interchangeable). Generation resolution is delivery resolution, best tier per model — except that
  since v2.49 a video take may be generated at 720p and upscaled once, on the final, after the cut
  (§4 item 11).
- **Length is computed** (`estimate_duration.py --client`), never guessed. Mode A ~35–65s; B/C 35–55s.
  Mode B's long-body DR jobs take theirs from the brief: a 60–240 s body behind hooks of a few seconds
  (`modes/ugc-volume.md` §2b).
- **The hook window is ~6 seconds** — the platform's prescription, not a measurement — and the
  **"3-second rule" is a billing threshold with no study behind it**, so it is not citable
  (`references/hook-craft.md` §3, which blacklists it by name). One demand at a time: a text card under a spoken line under a cut
  is invisible (`references/persuasion-psychology.md` §1). Route the hook from what the viewer
  already knows (§2 there), then build it as **one concrete anchor and one withheld term** — more
  gap is not more better, the curve turns over (`hook-craft.md` §1) — and check the gap's three
  legs: salient, important, fillable (§2 there). **Importance is a stake they already hold**
  (own, pay for, chose, worry about), never something they lack: "because nobody has told them" is
  the gap written twice, and `develop.py` refuses it. **Brand out of the first beat** unless the client
  has tested otherwise (§5 there).
- **Three model roles through one MCP:** start-frame image model (GPT Image 2.6 on Higgsfield, the
  primary since v2.49; its defaults, quality `low` and `1k`, are refused;
  priced at 2k `high` only, so `get_cost` first for any other tier — `references/ai-generation.md` Step 1) · character/dialogue video model
  with audio-driven lipsync · B-roll model. Video models are the approved roster only
  (`references/ai-generation.md`; `rate_card.py table` prices them; `prompt_lint.py` refuses the rest). Genjutsu
  re-renders a source video through its own spec and approval, and costs about 6× Kling 4.0 per 5 s: try the roster
  model with the clip as a motion reference first.
- **One dialogue line = one clip; two speakers = two clips**, plus the listener reaction and an
  insert per exchange (`references/direction.md` §3). A planned multi-shot clip is the exception,
  with the reaction as a stage (`references/multishot.md` §1).
- ⛔ **Generate B-roll and silent clips at ~1.7× the on-screen length** (a dialogue clip is the exception:
  it is generated to the length of its line, below). Measured across 12 real clips: **57.6% yield**, and
  **5 of 12 peaked on their own last frame** — a clip generated to its on-screen length has its edit
  point on its last frame, which is a butt join, not a cut. **Handles have to be generated; they
  cannot be added afterwards** (`references/editing-and-audio.md`, the cut mechanics;
  `clip_qa.py --cut-plan`). In a planned multi-shot clip only the first and last cut get handles;
  every internal cut is final (`references/multishot.md` §2).
- **A clip carries ONE complete action, begun and finished in it, and something other than the
  camera moves** (a planned multi-shot clip: one per stage). Viewers segment on action, not on space or time — jump location and time freely,
  never cut mid-gesture [PRIMARY · Magliano & Zacks, *Cognitive Science* 2011]. Short
  shots in modern film carry *more* motion, not less, so short-and-static is the failure mode and it
  is this pipeline's default output (`references/motion-craft.md` §3–§4; `prompt_lint.py` warns on a
  camera-only MOTION block, `clip_qa.py --motion-profile` measures whether the film has any range).
- **Identity lock is a reference, never text alone and never a seed** — an approved hero frame or a
  platform Element, with the fixed character block pasted verbatim (`prompt_lint.py` compares it to
  `_reference/CHARACTER-<name>.md` when one exists). A scene-form clip's identity is its approved sheets
  (v2.49), bound one subject per line, each saying what it controls.
- **Native diegetic sound is kept** (v2.49: native audio can be replaced at any time
  afterwards). `generate_audio` stays on; the prompt's `[AUDIO]` block directs it — what it sounds like and
  must not, the ambience, the effects, `MUSIC: none` — and any sound can be replaced in the edit. One
  ambience bed per location still runs under it. Speech still needs `audio` approved. The `guide-audio`
  switch restores native-as-guide for one job (`references/editing-and-audio.md` §7d–§7e).
- **Lipsync has two paths:** A, voice-first (TTS then generation with the audio as reference) for
  languages models mispronounce, franchise voices, locked wording; B, native audio for English
  one-off UGC after a bake-off with a verbatim check. Never a silent generation with a voice laid
  over it. **Verify by listening to an A/B, never from a contact sheet.**
- **B-roll ≥ one per dialogue clip, opening on an establishing insert**, generated 1–2s past the cut;
  dialogue clips are generated to the length of the line, and their handle comes from the join
  (the next shot's head, a reaction or an insert), never from extra mouth time (`references/shot-handoff.md` §2).
- **On-screen text is made in Resolve, and a title is never a movie you import** (the native-elements rule; v2.45). Captions go
  on the Subtitle track or Text+. Titles, supers, card labels and end-card words are Fusion titles the plugin builds
  from the approved card (`fusion_titles.py build`), places **by computer control** (v2.49, the computer-control rule — never
  through the API) and checks on Resolve's own frames (`title_qa.py native`); options are Resolve stills
  (`title_qa.py strip-native`); the owner's installed packs are mapped by `resolve_library.py` and placed the same
  way. When a title cannot be placed, or its read-back disagrees with its spec, **stop and report that row** —
  never render the title elsewhere to get past it. A
  look Fusion cannot make is the owner's call: their words are the spec's `owner` reason, recorded before anything renders
  outside. `title_card.py check`, `gate.py`, `shell_gate.py` and `approve export` refuse a title movie without it.
  Brand presence is in-world (the real mark composited onto the start frame), never a model rendering a logo.
- **Edit in DaVinci Resolve:** dialogue V1, B-roll V2, cut on action, then fit the music to the cut
  (`music_fit.py`: the beat lands 2–4 hits, never every cut) and rebuild it in Resolve from the original track
  (`music_fit.py rebuild` → REBUILD.md; a Python render is a preview, never imported),
  strip embedded audio once external VO exists, master to the preset's loudness, queue the render.
  Drive it through the MCP inside Resolve Studio 21.1 (`references/environments.md` §3): its calls
  pass `gate.py`, and the render step has crashed Resolve — save the named project first, queue only.
  **v2.49, the computer-control rule:** native titles, Fusion and Fairlight work are done **by computer control**
  in Resolve's interface, never through the scripting API, which fails on them; the API keeps reads,
  project and timeline setup, media import, markers and the render queue. **All SFX and edits are made in
  Resolve**: ffmpeg and Python measure and propose (markers, EDLs, timing plans, levels, QA), they never mix,
  conform or cut the deliverable. One Resolve script per task, ending with its own verification stills; the
  first and last frame of every comp and new timeline checked at full size; after a duplicate or a comp
  import, the Loaders and media ranges re-checked; the real output verified, never a viewer or a still
  (`references/editing-and-audio.md` § What runs through the API).
- **Music: always ask the user which track.** The bed changes what the picture means
  (`references/persuasion-psychology.md` §4); it is the client's call.
- **Somebody watches the FILM before it ships.** Every other gate here inspects one clip or probes
  one file. `qa_log.py --gate master` refuses a verdict without **two distinct timecodes**, one
  heard and one seen, and `gate.py approve export` refuses without a master PASS. Before that, every
  draft cut is read on its event sheet (`contact_sheet.py events`, `qa_log.py --gate draft`, v2.46). Room tone is
  mechanical now: `export_qc.py` fails on true digital silence — *no clip plays over silence*
  (`references/editing-and-audio.md`).
- **Cost is reported, never a lever:** quote (`rate_card.py`, `estimate_duration.py`), preflight
  with `get_cost: true` (the gate allows probes), reconcile after against what settled.
- **Files & naming:** `00-brief … 10-export / 99-costs`, `<SHOT>_<subject>_<model>_v<N>`
  (`name_lint.py` checks the grammar; `references/pm-workflow.md` owns it).
- **A house rule is a default, and one job may lift a named rule in writing** (such choices are made per project). The job's `00-brief/CHECKPOINT.md` carries the line
  `Switches:   <id> — <reason>; <id> — <reason>`, or `none`; each id must be in
  `assets/project-switches.json`, which says what the switch lifts, what it allows and what still holds.
  `scripts/switches.py list` shows them, `show <job>` shows a job's and `check <job>` validates the line; `gate.py open` refuses an invalid line and prints the lifted rules, and `status` shows them. A
  switch lifts only what its entry says, the rule stays the default for every other job, and a script that
  enforces a lifted rule prints it as lifted, with the reason, instead of refusing. **The locked rules never
  switch:** no advanced VFX (since v2.49 roto is allowed for one job, the masked region repair, blended back as a Fusion
  comp by computer control (v2.50) —
  `references/editing-and-audio.md` § Region repair), no AI images as references, no spend without approval,
  native Resolve titles, English, a contact sheet before any draft, never picking music, Higgsfield
  `motion_control` (M3) (v2.48.0). **v2.49 adds four switches:** `frame-led` (back to approved start frames
  for every clip), `guide-audio` (native sound as a guide only), `floor-1080` (the 1080p video floor) and
  `dwg-working` (real log footage graded in DaVinci Wide Gamut).

---

## §4 · The non-negotiables

The profile's own list comes first. On top of it, for every brand:

1. ⛔ **Nothing generates outside an open job, and nothing is sent that a lint did not pass.**
   Enforced by `gate.py` (hook or preflight) — the one rule the others depend on.
2. ⛔ **Development happens before the script, and the human picks.** Sourced research, **a look
   board of four real pictures on disk**, five genuinely different concepts, at least two
   adversarial rounds that each killed something, then the options go in front of the client
   (AskUserQuestion) and their choice is recorded verbatim. **Run `develop.py check --phase
   concept` BEFORE showing anybody the concepts** — a shortlist presented while the board is empty
   is a choice made against imagined pictures, and "we can source the references after you pick"
   turns the board into a formality the client has already decided around.
   `scripts/develop.py` enforces it; `gate.py approve concept` and `approve script` refuse without
   it. **The agent shortlists and argues; it does not decide.**
3. **The script is tested before it is produced** — three drafts (four on the 2.67 template) with a specific critique between
   each, read aloud, `script_score.py` clean (mechanical; the 1–10 card in `references/script-craft.md` §6 is the
   writer's note, v2.67.0), `claims_lint.py` clean, a cold read that agrees with the brief, and the tests the person
   reads beside each option (`script-craft.md` §7) — and approved with its file. A perfect
   generation of a mediocre script costs the same. **v2.49:** it is written in four
   passes — story logic, coverage (enough shots for the duration, each with a function, at least the
   coverage floor), continuity, cut-down and read-aloud timing — and only the last pass is shown, with the
   checks it passed (`references/script-craft.md` §7b; manual until a script checks it).
4. ⛔ **Picture lock is a real door.** Mix, grade, captions and titles happen *after* it, never
   before; `gate.py approve lock` needs the clips approved, a QA log with observations and the
   motion analysis of every shot and join (`motion_qa.py`), and `export` needs lock, music, the
   measured file (`export_qc.py`) and the measured mix with every sound licensed (`mix_qa.py`).
   Conforming to a cut that then changes is how a post day is lost.
5. **Frames carry the picture; clips carry only motion.** `prompt_lint.py` refuses a clip prompt
   that re-describes the frame (`references/prompting-craft.md` §1) and a frame prompt that briefs a
   negative emotional state, names a director, stacks quality words, or hedges its verbs. **Length
   is not the variable — demands per block is.** The band is **1800–2100 characters**
   [PRIMARY · own testing · 2026-09-07], with a per-block word budget and a demand count in which a
   sourced reference removes a demand and rewording removes none (§2.2b). **Thin is the failure
   mode, not long:** what the prompt leaves out, the model fills in, differently every take.
   The **ceiling** is the model's own (`assets/higgsfield-rates.json`; `references/prompting-craft.md` §11g): FAIL above
   it, a WARN past the band where the model takes more, 2,500 kept as a house FAIL where no vendor publishes a cap.
   Every prompt carries a **detail score** (frame ≥ 5/9, clip ≥ 3/8, edit ≥ 7/14 `[ASSUMED]`). Never write
   "watermark"; a picture with signs says what they show; a clip that makes sound says "no music".
   **The v2.49 exception is the scene form:** a Seedance 2.5 clip built from approved sheets has no frame to
   carry the picture, so its prompt carries the look, the place, the blocking and the sound in the vendor's
   block order, WARNs under 2,500 characters and FAILs over 20,000 (the winners' median was about 6,400; the
   MCP's own cap is unverified, so `get_cost` first) — `references/prompting-craft.md` §12. Mouth-opening
   words with sound on and no scripted line are warned: the model reads an open mouth as speech
   (`references/shot-handoff.md` §1.3).
6. **A reference is planned, sourced and cleared before it is needed — never judged after the
   render.** Every shot declares the ONE attribute each reference carries; a slot nobody has sourced
   yet is written `need: <what to look for>`, and `refsource.py` turns it into a search built from
   that shot's own words, fetches candidates, and waits for a human to pick. `gate.py approve cast`
   and `approve clips` refuse while any reference is unsourced or uncleared
   (`references/stock-sourcing.md` §5, §9). An asset examined after the credits are spent has
   already cost the money the check was for.
7. ⛔ **A decision gets a picture, not a paragraph.** `board.py` builds three: the look board
   before the concepts, the concept board for the choice, the shot board before any spend — each
   one self-contained HTML you open, with every reference rendered as the picture it actually
   binds. `gate.py approve concept` and `approve cast`/`clips` refuse a board that is **missing or
   stale**, because a board built before the prompts changed is a board of something else.
   Concept art that would change your answer is legitimate and capped: `gate.py previz` opens a
   development lane of at most 12 images, needs the look board filled first and a reason in your
   own words, and closes when the concept is signed. **And the film is read as one object, not
   shot by shot** — `breakdown.py` aggregates every requirement across all shots, so "six shots
   need a hero nobody designed" and "four shots each sourcing one apron" surface at `cast` rather
   than at shot six. **The waste was never the board — it was
   discovering in a finished shot what a board would have shown for nothing.**
8. **The frame gate is human.** No clip generates without an approved still, bound by its media id —
   or, for a scene-form clip (v2.49), without approved sheets, every bound image one an approval names
   (`character:`, `prop:`, `world:`). The `frame-led` switch puts a job back on approved stills throughout.
9. **Claims are verified, not assumed** — never carried forward from a previous episode. In a
   claims-sensitive category (sleep, wellness, beauty, supplements, health, finance, food origin and
   grade), `references/compliance.md` runs before generation and before export; substantiation,
   endorsement honesty and AI disclosure are three separate obligations.
10. **Disclose synthetic content per platform**, burnt in from frame one where a synthetic presenter
   is used. Never a private individual synthetically, never a public figure in a synthetic
   endorsement, never a voice you do not hold rights to.
11. ⛔ **The quality floor, from the first take: video 720p, pictures 1080p, the model's best tier where
   it exists.** v2.49 (720p finals plus one upscale): a video take may be 720p and ship, with ONE
   upscale on the final, after the cut; prefer 1080p for wide plates and close faces. Frames, sheets and
   image edits keep 1080p (2k preferred). The `floor-1080` switch restores a 1080p video floor for a job.
   A cheaper generation is a different take, not a draft. Cost never enters a model,
   resolution, tier, retake or duration decision — cut shots, not quality. The one exception is an
   evaluation job (`Tier: evaluation`): it may go below the floor to
   answer a question, and nothing it makes ships (`references/ai-generation.md`, the evaluation tier).
12. **Realism is a gate.** The per-clip card (`references/realism-qa.md` §6, tiered per §6b) runs
   before a clip leaves review and on every regeneration; `qa_log.py` refuses a verdict without an
   observation. A clip can be right in every frame and wrong in time
   (`references/timing-and-performance.md` §8).
13. **Persuasion has a line** — manufactured fear, false scarcity, fabricated proof, hidden terms
   go back to the writer (`references/persuasion-psychology.md` §6).
14. ⛔ **The verification policy is read from the profile, never defaulted**, and **nothing ships
    out of its own branch** — a batch passes `series_join.py` or nothing in it ships
    (`references/series-parallel.md` §6).
15. **Consistency is checked across the scene before any approval request** (v2.49).
    The scene board: every shot of a scene side by side against its sheets — lens and field of view,
    camera height, subject size in frame, distances between objects, furniture and props, wardrobe,
    light direction, time of day. Fix toward the scene's sheet, never toward the neighbouring shot, and
    list in the request what was compared and what changed (`references/review-and-approval.md` §11).
    Manual until a script measures it.
16. **Done means measured on the real output** (v2.49, production lessons). Never a viewer or a still: the
    render or the returned file at full size, the first and last frame of every comp and timeline. Levels
    against the music, the LUT's shift, the grain plate's average and every stem summed are measured before
    the word "done". Every re-cut breaks sync: rebuild the sound from the new frames. Confirm which model
    actually ran. When a fix touches story or brand, ask what it is for before fixing it.

### Testing this skill

Three layers, and each one tests something the others structurally cannot.

| | what it proves | what it cannot |
|---|---|---|
| `python3 scripts/run_tests.py` | the scripts work and **compose** — every script, every suite and every selftest; the runner prints all three counts when it passes, and `scripts/INDEX.md` lists them. `test_preproduction.py` walks the whole pre-production stage through the real CLIs and asserts the refusal at every point; `test_gate.py` drives real hook payloads. No network, no credits. | whether an agent handed the skill does any of it |
| `claude plugin eval .` (from the plugin root) | whether an **agent** follows the process — cases that make skipping the attractive option, run in a fresh session with only this plugin loaded. Write your own cases in an `evals/` folder at the plugin root (the author's cases do not ship; `evals/README.md`). Early access; costs credits. | **hooks do not fire inside an eval run**, so it grades the agent's choice with the enforcement removed — and it cannot judge taste |
| one real generation per release | that the PreToolUse hook actually fires in the client you use (`references/environments.md` §2b) | anything else |

`scripts/eval_lint.py` checks the eval cases are well formed without running them. Nothing checks
that they are well *aimed* — that is a read, and the same question applies to them as to every gate
here.

**The principle behind every gate: a check that can be passed without doing the work will be.** A
checkmark can be typed; a file the script validates, a hash the hook compares, a quoted word from a
clip you listened to, a `[PRIMARY · URL · date]` tag — cannot. When you add a check, ask what it
would take to pass it fraudulently; if the answer is "nothing", it is not a check.

---

## §5 · Close the loop, and Done

Before a job is called done: the episode note (`memory/episodes/<date>-<slug>.md` — what broke, what
fixed it, where the skill says otherwise, estimated vs actual); any new failure into the right table
(`ai-generation.md` guardrails, `realism-qa.md` §1, `compliance.md` §4); the cost reconciled
(`reconcile_costs.py`, and `gate.py reconcile` for what was spent outside a linted prompt); the
board updated and time logged at the milestone (`references/pm-workflow.md`). Monthly,
`references/self-evolution.md` turns the notes into proposed edits behind a promotion gate;
`memory/LEDGER.md` records what landed. `memory/` here means your own history folder (`CINE_MEMORY`, or a
`_cine-memory/` folder above the jobs), not the plugin's. **Do not edit a reference from inside a production run.**

**Definition of Done** — the mode file's DoD, plus: the piece does the one job it was briefed for;
claims verified and compliance signed; characters and product consistent; captions correct and
legible on a phone; realism QA passed with observations; `export_qc.py` passes; spend inside the
envelope and reconciled; every deliverable with numbers behind the verification readout (each
figure measured / estimated / assumed, arithmetic recomputed, a verdict); the episode note written.
If any of those is shaky, say so plainly rather than shipping and hoping.

---

## §6 · Grounding a decision

This skill is self-contained: everything it asks for is written into `references/` in full, and
`assets/further-reading.md` maps each file to the works behind it (McKee, Murch, Katz, Brown,
Pearlman, Schwartz, Heath, Kahneman, Young and the rest) so a rule can be traced, checked and, if
wrong, retired. A studio's own writing system (voice profiles, a lexical scanner) is optional
(`references/script-craft.md` §0).

**The literature holds durable principles; the web holds current specifics.** Never cite a book for
a price or a policy, never cite a blog for a mechanism. Read a source when a decision is contested,
expensive, or about to become a standing rule — then write the attribution next to the decision.
