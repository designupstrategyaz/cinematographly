# Start here: Cinematographly, for people

**This page is for you, the person.** `SKILL.md` is the agent's rulebook. You don't need to read it to use the skill. House words are explained in `GLOSSARY.md`.

## What it does

- **It runs a short video, or a set of stills, from brief to export.** It works in 15 stages, the way a small production team would.
- **It asks before it spends.** A gate checks every paid generation. A stage does not start until a named person has approved the one before it.
- **It also reviews and plans.** It can review a cut, study a reference ad, or plan and price a job without making anything.

## Your first ten minutes (nothing is spent)

1. `/cinematographly:setup` makes your studio folder (`~/Cinematographly/`: clients with the sample `acme`, history,
   jobs) and a config so every tool finds it. It never overwrites anything.
2. `/cinematographly:doctor` checks the machine. Red blocks a first concept; amber waits for the step that needs it.
   `/cinematographly:studio` asks the studio's questions once (approvers, review policy, platforms, music, likeness,
   disclosure); `/cinematographly:demo` makes a finished sample job to read; `/cinematographly:new-client`
   interviews you about a real client and writes their profile.
3. `/cinematographly:new-job acme first-promo --mode A --approver "Your Name"` makes a job that opens for a concept
   only: budget 0 credits, so every paid generation is refused (any other paid tool asks you first). The approver is the person whose own words approve each stage; the
   sample's approver is invented, so a job for `acme` needs yours.
4. Say "Develop the concept for this job." You are asked first, then shown five concepts after the kill rounds.
5. `/cinematographly:next` says what is owed. An approval is your own words, e.g. "Approved: go with concept C2."

A concept and a script need neither Higgsfield nor DaVinci Resolve.

## From a concept to the first paid picture

1. **Price it.** Once the script is approved, ask "what will this cost?". The agent runs
   `estimate_duration.py --client <client> <script>` at the client's prices and shows the credits with their parts
   (keep the answer in `99-costs/` if the client will see it).
   Concept art (previz) is a paid picture too: while the envelope is 0 it is refused, so set a small envelope first if
   you want concept art before the script.
2. **Set the budget.** Edit the checkpoint's `Budget:` line (`00-brief/CHECKPOINT.md`) with the client's OK:
   `Budget:     envelope 600 cr (client, 2026-11-16) · estimate 480 cr [estimated] · preflight none yet`.
   The envelope is the cap: a call that would pass it asks you first. Exactly one of `[estimated]`, `[measured]` or
   `[assumed]` follows the estimate.
3. **Fill the inputs.** Each `Inputs:` item becomes PRESENT, or stays MISSING with `(asked …)` or `(accepted risk: …)`.
4. **Re-open the job.** `/cinematographly:next` re-checks the checkpoint and names what is owed. With Higgsfield
   connected, the first paid call is a start frame you approve before any clip is made.

## What you can ask for

| You want to… | Say something like |
|---|---|
| Make a video | "Make a 30-second promo for [brand] from this brief." |
| Make stills | "Make three hero stills for [brand]'s home page." |
| Review a cut or a take | "Review this cut against the house rules." |
| Study a reference | "Break down this reference ad: cuts, shot lengths, camera moves." |
| Plan and price a job | "Plan and price ten UGC videos for [brand]. Spend nothing." |
| Fix one shot | "The hand in shot S4 is wrong. Fix that shot only." |
| Learn how it works | "What happens at stage 5, and what will you ask me?" |

- **The brand needs a client profile.** With no profile, the skill stops and asks.
- **Asking for one thing is asking for its stage.** "Write the script" means stage 2, with the work stage 2 needs behind it.

## The stages

```
Brief → Concept ✔ → Script ✔ → Storyboard ✔ → Cast and design ✔ → Start frames ✔ → Voice ✔
      → Clips → Selects ✔ → Music ✔ → Edit → Picture lock ✔ → Mix, grade, titles ✔
      → QC and export ✔ → Delivery                        ✔ = you sign before the next stage
```

| # | Stage | What you are shown | What you sign |
|---|---|---|---|
| 0 | Intake | The checkpoint: one page with the mode, client, format, budget and approver | Nothing. You answer the open questions |
| 1 | Development | First it asks you: what you'd be proud of, what you'd hate, references you love and hate, your own ideas and phrases, and one picture of yours. Then a look board and five different concepts, yours among them | `concept`: you pick one, combine two, bring your own, or pick none |
| 2 | Script | Two short script options, each keeping one sentence of yours. Beside each: what a stranger understood from it (a cold read), the question its hook asks and what its ending answers, two lines that only work in that order, the claims check, and, if it tries to be funny, your answer to "does anything make you cringe?" | `script`: you pick one |
| 3 | Storyboard and direction | First it asks for your own sketch or phone photo of the shots that matter most. Then the storyboard: every shot as a picture in cut order, with its seconds and its line, and the animatic, a free reel of the panels held for their planned time | `storyboard`: the film, before anything is paid for |
| 4 | Casting and design | The characters, props and locations, as reference sheets | `cast`, and each sheet |
| 5 | Start frames | One still per shot, on jobs that use start frames; then all of them on one page, in cut order | Each frame, then `startframes`: the set side by side |
| 6 | Voice | The voice lines | `audio` |
| 7 | Clips | The generated clips | Nothing here. Each paid call asks, unless an allowance covers the batch |
| 8 | Selects and QA | The chosen takes, each with its QA card | `clips` |
| 9 | Music | The first time, it asks you where your licensed music is. Then two or three tracks from it, each with why: cleared for ads, long enough, how it ends, any sung lyric, how well it lands the cut's key moments | `music`: you choose the track |
| 10 | Edit | The rough cut, then the fine cut | Nothing |
| 11 | Picture lock | The locked cut | `lock`: a one-way door |
| 12 | Mix, grade, captions, titles | The finished picture and sound | `titles` |
| 13 | QC and compliance | The QC report | `export` |
| 14 | Delivery and wrap | The files, the cost check and the close-out note | Nothing |

- **Stills are shorter:** `brief`, then each frame, then `export`.
- **By default a clip is built from the approved sheets** (the "scene form") and has no start frame. A "frame-led" job approves a still per shot first.

## Your approvals

- **Your own words, quoted.** An approval is your reply, word for word, after you have seen the thing. The agent cannot approve for you.
- **A named person.** The checkpoint names the approver. "The client" is not a name.
- **In order.** The gate refuses a stage signed out of order.
- **How often you are asked depends on the client's policy:**
  - `per-stage-human`: a person checks the script, the reference images, the audio and the clips, each before the next stage starts.
  - `gated`: the machine checks first; a person looks at the frame gate and at flagged, landing and hero shots.
  - `standing`: a pure variant ships on a standing approval.
  - A profile with no policy is asked about. It is never assumed.
- **Fewer clicks:** an allowance is one recorded approval for a batch of shots, with 2 regenerations each (or your
  studio's `default_regens`).
- **Showing a client outside the chat (3.1):** `/cinematographly:review-pack <stage> <files>` makes a static page with
  a 16-character code. The client's reply is evidence only. The approval is still the Approver's sentence in the chat,
  and it must contain the code; a file changed since the pack was made is refused.
- **Saying no in the studio answers blocks export.** If `/cinematographly:studio` says there is no music licence or no
  likeness release, the export approval is refused. A "yes" there never replaces the job's own music and likeness checks.
- **A scene that fails its continuity check (3.1)** cannot have its clips generated until the check is re-run and passes.
- **Roles (3.1):** `Producer:`, `Editor:` and `Reviewer:` checkpoint lines show in status. None of them can approve.

## Delivery and close (3.1)

- `/cinematographly:deliver tiktok "Instagram Reels"` builds one folder per platform in `10-export/DELIVERY/`: the
  master (same bytes), captions, a cover frame and `delivery.json` with the AI-disclosure line. It is refused until
  `export` is approved, and it never posts: you upload by hand.
- Closing a job writes `99-costs/SCORECARD.md`: takes generated and kept, yield, retakes per shot, credits per kept take
  and per kept second.

## What costs credits

- **Costs credits:** pictures (concept art, reference sheets, start frames), clips, voice, and any other paid Higgsfield tool (upscale, dubbing, voice cloning, reframe, outpaint, apps).
- **Costs nothing:** reading the model list, your balance and job status. The boards, checks, estimates and contact sheets run on your machine.
- **Prices come from the rate card.** Ask "what will this cost?". The answer is read from `rate_card.py`, with the date the price was last checked.
- **Edit handles.** B-roll and silent clips are generated at about 1.7× the on-screen length, so every cut has room.
- **Retakes.** Estimates add a retake allowance: 1.3× on the quality preset (`retry` in each client's cost file).
- **The budget** is on the checkpoint's `Budget:` line.
- **The studio's month.** If `/cinematographly:studio` set a monthly ceiling, a Higgsfield call that would take the
  studio's month (UTC, all jobs) past it asks you first. `studio.py month` shows the total.

## What you can set

Every setting can only make a job stricter, or pre-fill a number you still see and can change. `gate.py status`
prints a `settings:` line with each value and where it came from.

| Where | What | How |
|---|---|---|
| Studio (`/cinematographly:studio`) | Approvers, review policy, platforms, disclosure, finishing looks | answered once, pre-fills new clients and jobs |
| Studio | **Monthly credit ceiling** (Higgsfield only; Kling is a separate account) | a stop. Lowering it is free; raising or removing it needs your words, `--by` and `--quote` |
| Studio | **Regens per batch approval** (0, 1 or 2) | pre-fills `gate.py allow`; one approval can still name up to 5 |
| Studio | **Retake factor** (1.0–3.0) | pre-fills new clients' cost files; it can only raise estimates |
| Studio | **Second opinion** from another model (optional, off) | text only: the agent asks you before each send |
| Client | Prices, retake factor per preset, review policy, delivery format | the client's profile and `costs.<client>.json` |
| Job | Budget envelope, mode, approver, house-rule switches with a reason | the job's `CHECKPOINT.md` |
| Never | The eight rules below, and the checks before any spend | not settings |

A checkpoint or settings file can be edited by hand; the gate reads what is there, and the edit shows in the session.
The control on raising a limit is a person's own words.

## Eight things it will never do

No switch lifts these: advanced VFX (one exception since v2.49: the masked repair of one region of a shot); AI images as references; spend without approval; titles that are not native Resolve titles; a language other than English; a draft shown before its contact sheet; picking the music for you; Higgsfield `motion_control`.

## Before your first job

The commands below run from the plugin's skill folder, `skills/cinematographly/`. The README gives the same commands from
the plugin's top folder, with `skills/cinematographly/` in front.

- **Keep client profiles and history outside the plugin.** `/cinematographly:setup` (`scripts/studio_setup.py`) makes them and writes `~/.cinematographly/config.json`. `CINE_CLIENTS` and `CINE_MEMORY`, when set in the shell, still win; `doctor` says when one hides the config. A plugin update replaces the plugin's own `clients/` folder.
- **Name your Higgsfield connector once.** In the Claude desktop app the connector is named by an id of your account, not by "higgsfield". Type `/cinematographly:connectors --higgsfield <id>` with the id from its tool names (`mcp__<id>__generate_image`). Until you do, every paid call through it asks first. Name other connectors that share a tool name with `--other <id> --quote "<your words, naming the id's first 8 characters>"`; that lets their generate tools through ungated, so it needs your own words. A hookless (Cowork) home cannot do it: there is no transcript to check the words against.
- **What the gate does with connector tools (v2.61.0).** It sees every tool of every claude.ai connector, which adds about 0.1 s per call, and lets other services' tools through at once. On Higgsfield or Kling, a read passes, a tool it knows is gated, and a tool it does not know asks you, because a new tool may spend, publish or delete. Naming any connector `--other` needs the owner's words (`--quote`), and tools only Higgsfield serves stay gated whatever the settings say.
- **Two Claude windows at once?** Each keeps its own job. The session start note gives each window's id; with two
  open, the agent passes `--session <id>` to the gate. In Cowork, where the plugin's hooks do not run, set
  `studio_setup.py --hookless` once (approvals are then recorded as unverified, and doctor says so; batch approvals,
  `gate.py allow`, need a checked quote and so are not available there). A job approved in Claude Code keeps needing
  checked quotes: a hookless home cannot add an unchecked one to it.
- **A job stays open for 24 hours.** After that, re-open it with `python3 scripts/gate.py open <job-folder>`. Until then, paid calls are denied.
- **Check which install is running.** `python3 scripts/gate.py where` prints the scripts, skill, clients and state folders in use.
- **Check the gate is live.** Where the app runs hooks, the gate checks each call by itself. Where it does not, the agent must run `gate.py preflight` first and see "would PASS". `references/environments.md` §2b has a ten-second test.

## Four sets of numbers

"Stage 7", "§3", "rule 11" and folder `07-edit` are four different things.

- **Stage 0–14:** a step in the table above.
- **§0–§6:** a section of `SKILL.md`.
- **Rule 1–16:** a non-negotiable in `SKILL.md` §4.
- **Folder 00–10, 99:** a folder inside the job.

## Where things are

| Folder or file | Holds |
|---|---|
| `SKILL.md` | The agent's rulebook: the gate, the routes, the stage table, the rules |
| `GLOSSARY.md` | The house words |
| `modes/` | The four video modes |
| `clients/` | Profile templates and one invented sample client (`acme`). Your own profiles live in your studio folder (setup) |
| `references/` | The depth files, listed in `references/_INDEX.md` |
| `scripts/` | The tools. `scripts/INDEX.md` lists every one; `scripts/README.md` is the guide |
| `assets/` | Templates and data: rates, delivery formats, switches |
| `memory/` | Templates for close-out notes. Your own notes and ledger live in your studio folder (setup) |
| `CHANGELOG.md` | What changed in each version |
