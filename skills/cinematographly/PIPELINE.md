# Fast pipeline — kill the manual loop

**Goal:** cut the slow, hand-driven process. Today it's all manual: (1) generate reference images +
video shots by hand in the Cinema Studio UI, (2) move each final into a favorites/VideoGen folder,
(3) download it, (4) move it from `~/Downloads` into the project folder, (5) assemble in DaVinci
Resolve from scratch. The pipeline below automates the parts that are automatable and keeps a human only
where judgment is actually required.

Verified against the live Higgsfield MCP + Cinema Studio UI (2026-07) — nothing here is assumed.

## The 6 stages (⚙️ = automated, 🖐 = human judgment)

| # | Stage | How | Auto? |
|---|---|---|---|
| 0 | **Route** — mode (`modes/_INDEX.md`) + client profile (`clients/_INDEX.md`) | Claude, before anything else | 🖐 confirm |
| 1 | Script (locked words) | Claude writes / you approve | 🖐 approve |
| 2 | Shot plan + prompts | `MASTER-image-prompts-all-scenes.md` (simple per-shot blocks) | ⚙️ Claude drafts |
| 3 | **Batch generate** frames + clips + VO | Claude loops the Higgsfield MCP with `<<<element_id>>>` | ⚙️ **automated** |
| 4 | **Pick finals** | you favorite in Cinema Studio, or name the job IDs | 🖐 human pick |
| 5 | **Pull + file** finals into the project folder | `pull_finals.py` | ⚙️ **one move** |
| 6 | **Rough cut** in Resolve + finish | Resolve MCP builds the timeline (or `build_fcpxml.py`) → taste pass | ⚙️ native, 🖐 finish |

**Parallel agents (v2.50).** Stage 2's prompts are written one scene per agent (`cine-shot-writer`), and stage 4's
review runs one take per agent (`cine-take-reviewer`), side by side; the main session dispatches and joins with
`fanout.py` and still makes every spend, approval and Resolve step itself (`references/parallel-agents.md`).

## Stage 3 — batch generation replaces hand-driving the UI

> **Since 2026-09-06 every call in this stage goes through the gate.** The job is open
> (`gate.py open`), the script is approved, each shot's frame prompt and clip prompt are linted
> (`prompt_lint.py`), each start frame is approved with its media id (v2.49: a scene-form Seedance
> clip has no start frame, so each sheet it binds — `character:`, `prop:`, `world:` — is), and the params of every
> `generate_*` call are what `gate.py preflight <SHOT> --kind frame|clip` printed. The PreToolUse hook
> in `hooks/hooks.json` refuses anything else; where hooks do not fire you run preflight first and
> `gate.py reconcile` after. `SKILL.md` §0 has the whole loop.
>
> **And the references those prompts bind were sourced before this stage, not during it.** Each shot
> declares the attribute each reference carries and, for a slot nobody has filled yet, a `need:`
> line; `refsource.py brief → fill → candidates → adopt` turns those into Pixabay searches built
> from the shot's own words, candidates with provenance, a human's pick, and a rewritten ref line.
> `gate.py approve cast` and `approve clips` refuse while any of it is unsourced or uncleared
> (`references/stock-sourcing.md` §9b).

The Higgsfield MCP supports the Cinema Studio **Elements** programmatically: **embed `<<<element_id>>>`
inside a `generate_image` / `generate_video` prompt and the backend injects the character and rewrites
it to `@element-name`** (multiple per prompt OK). So the whole video's shots can be generated in a
loop instead of one-by-one in the UI:

1. `python3 scripts/master_to_jobs.py MASTER-….md` → a clean jobs list (shot · kind · subject · @elements · prompt).
2. Claude: `show_reference_elements(action='list')` → get the ids for **@Host Business** (the host),
   **@brand-business**, **@brand-house**, **@brand-watch**.
3. ⛔ **Fire these as BATCHES, not per shot.** The old loop — *for each job, `generate_image` then
   `generate_video`* — is serial and turns eight shots into sixteen sequential waits. The dependency
   chain is only three deep (**VO → start frames → clips**), so use `generate_audio_batch`,
   `generate_image_batch` and `generate_video_batch` with `jobs_wait` (≤12 jobs per group), and one
   `show_generation_by_ids` at the end — never `job_display` per job. This is the single biggest
   wall-clock lever in the pipeline (`references/production-runbook.md` §2), and the wait on the clip
   batch is where captions, music and the timeline skeleton get built (§3).
   Claude substitutes `@Host Business` → `<<<its-id>>>` in each prompt before firing. ⛔ **The dialogue model is PENDING** — the
   approved roster is in `assets/higgsfield-rates.json`; where a client profile locks Kling out of dialogue
   and the H3-vs-Seedance bake-off has not run, the dialogue model is that brand's open decision. Dialogue clips use an audio-driven roster model with the padded
   VO attached as an `audio_references` media** (see `references/ai-generation.md` Step 4 and
   the client profile §6); B-roll uses the cheap no-character model. `count`=variants, `duration`,
   `medias`=start frame (+ audio for dialogue). `get_cost:true` preflights credits.
4. VO: `generate_audio` `model=text2speech_v2`, `variant=elevenlabs`, `voice_type/voice_id` for
   Tasha/Andre, `prompt` = the **locked** line. (Higgsfield Audio = ElevenLabs.) **VO comes first for
   every dialogue clip** — it is the audio reference the video model animates the mouth to.
   ElevenLabs owns every spoken word; the video model owns the picture. **v2.49:** B-roll is no longer
   generated silent — its native diegetic sound is kept, directed in the prompt's `[AUDIO]` block, and can be
   replaced in the edit (`references/editing-and-audio.md` §7d); the `guide-audio` switch restores the old rule.

Batching all shots is far faster than the UI. **Honest limit:** generations land in your general
Higgsfield library ("My generations"), not neatly inside a named Cinema Studio *project/folder* — the
MCP has no project/folder param. That's fine: the pipeline tracks assets by **job ID → filename**, not
by UI folders. If you specifically want them inside a Cinema Studio project (for the @Elements canvas,
AI Director, multi-shot), that stays a **UI step** — do it there and skip Stage 3's MCP path.

## Stage 4 — pick finals (stays human, by design)

The MCP has **no "favorites" endpoint**, and you never want the AI auto-declaring a take "final." So
you pick — star it in Cinema Studio's **My favorites**, or just tell Claude the winning job IDs.
Claude then reads each pick's result URL via `show_generations` / `job_display`.

## Stage 5 — pull + file in ONE move (`pull_finals.py`)

Collapses "favorite → download to ~/Downloads → move → rename." Claude builds a small **finals
manifest** (shot · subject · model · kind · the MCP result URL); the script downloads each straight
into the right lane with the house name:

```
python3 scripts/pull_finals.py --project ~/<project>/creative/videos/<job-folder> --manifest finals.json
# 03-clips/S1-C1_host_seedance_v1.mp4 · 05-voice/S1-C1_host_tasha_v1.wav · 04-broll/S0B_intro-drone_seedance_v1.mp4 …
```

## Stage 6 — DaVinci Resolve rough cut + taste pass

Two ways to the rough cut (clips in scene order, matching VO under each, beat markers from the BPM):

- **Native, preferred — the Resolve MCP that ships inside Resolve Studio 21.1** (`mcp__DaVinci_Resolve__*`,
  `references/environments.md` §3). Claude drives Resolve's scripting API through `run_script`: import
  the filed clips + VO into a bin → build the timeline in scene order → `resolve-production-console.py`
  (V2, the A1–A6 lanes, beat markers read back) → dissolves at the planned joins (`AddTransition`, new in
  21.1) → your taste pass → `render-mp4.py` queues the render, never starts it. Every call passes
  `scripts/gate.py` first. No interchange files. **v2.49 (the computer-control rule):** titles, Fusion and
  Fairlight work are done by computer control in Resolve's interface, never through `run_script`, and every
  SFX and edit is made in Resolve — the Python tools measure and propose (`references/editing-and-audio.md`
  § What runs through the API).
- **Interchange fallback — `build_fcpxml.py`:** emits an FCPXML that Resolve imports
  (File ▸ Import ▸ Timeline ▸ Import AAF, EDL, XML…). Pass `--durations` with each dissolve shot's
  *needed* (non-handle) length so real transition handle survives into the timeline — the script
  prints a handle-exposure summary so you know before Resolve which joins can actually take a
  dissolve:
  ```
  python3 scripts/build_fcpxml.py --project <that dir> --slug acme-spring-tuneup --bpm 120 \
      --durations durations.json
  # → 07-edit/acme-spring-tuneup-rough.fcpxml
  ```

Before assembling: run `scripts/strip_embedded_audio.py --project <that dir>` to delink/remove
embedded audio on any character clip that has a separate external VO filed in `05-voice/` — never
let two voice sources land on one clip. `--bpm` markers are a steady grid — prefer
`scripts/detect_beats.py` on the actual chosen track once picked (see below) for its phrase and bar
lines, and `scripts/music_fit.py` once the cut is locked: it fits the track to the cut's 2–4 must-hits
and never moves a cut by itself. This skill ships exactly **two** Resolve scripts, total, and
each runs through the MCP's `run_script` or pasted into the console: `render-mp4.py` (saves the
project, queues the render, never starts it) and `resolve-production-console.py` (V2, the A1–A6
lanes, beat markers read back, the timeline dump — `detect_beats.py` fills the markers into a copy
of it, it doesn't write its own file). Captions: `scripts/build_srt.py` builds the .srt from
the locked script + real durations (never a fresh transcription); the actual Resolve import is
still a manual step, no scripting path exists for it. Before hand-off, run
`scripts/export_qc.py --report` on the rendered file — it PASS/FAILs resolution, fps, duration,
loudness/true-peak and (v2.49) a one-frame flash on any frame, the first and last included, against spec
instead of an eyeball check, and `gate.py approve export` refuses
without that report. See `references/editing-and-audio.md`.

**Music:** ask the user which track from `creative/videos/music/` to use — never pick one
autonomously. If it's shorter than the assembled video, `scripts/loop_music_to_length.py` plans a loop
on the phrase lines, joining just before a downbeat, instead of letting it end early; since v2.49 the loop
itself is made in Resolve at those points, and the script's render is a proof, not the bed.

**Costs:** reconcile `99-costs/COSTS-<SLUG>.md` against what Higgsfield actually settled, not just
the `get_cost` preflight it was built from — `scripts/reconcile_costs.py` diffs a live
`transactions` export against the ledger's logged total (a real ~15cr drift was caught this way).

## What's automated vs still manual — the honest scorecard

| Old manual step | Now |
|---|---|
| Generate each shot by hand in the UI | ⚙️ **Automated** via MCP batch (`<<<element_id>>>`), *unless* you want the Cinema Studio project canvas → then UI |
| Move finals to a favorites folder | 🖐 **Still human** — you pick the keeper (no favorites API) |
| Download each final | ⚙️ **Automated** (`pull_finals.py` fetches the MCP URLs) |
| Move from ~/Downloads → project folder + rename | ⚙️ **Automated** (filed + named in one move) |
| Assemble in Resolve from scratch | ⚙️ **Automated** (the MCP inside Resolve Studio 21.1 builds the timeline through `run_script`; or `build_fcpxml.py` interchange) + 🖐 taste pass |

Net: the two biggest time-sinks — **shot-by-shot generation** and **download/file/rename** — are
automated; the **creative pick** and the **final edit polish** stay human, where they belong.

## Cost (verified)

Cinema Studio image @2K = **2 cr**; the dialogue rate depends on which model the H3-vs-Seedance bake-off names, and the two differ by ~4.5x at delivery resolution — run `python3 scripts/rate_card.py compare --seconds <n>` rather than assuming;
B-roll on the cheap no-character models. Real lipsync costs roughly **+67% on dialogue seconds** vs the
retired Kling rate — a five-line ~25s episode moves from ~37 to ~62 cr, and it is worth it. **Generate
at exactly 1080p / 1080×1920** per the account's standing rule (the client profile §6; a client rule — the
house video floor is 720p with one upscale on the final since v2.49) — a reference at
another size comes back the wrong shape and costs a regeneration. Source of truth is
`clients/costs.<client>.json`, not this paragraph. Price any script with
`scripts/estimate_duration.py`; confirm live on the **Generate button** or `get_cost` before a run,
and reconcile against what actually settled afterwards with `reconcile_costs.py`.
