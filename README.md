# Cinematographly

[![Latest release](https://img.shields.io/github/v/release/designupstrategyaz/cinematographly?label=release)](https://github.com/designupstrategyaz/cinematographly/releases/latest)
[![Licence: source-available](https://img.shields.io/badge/licence-source--available-blue)](LICENSE)
[![Works in Claude Code, Claude, Cursor and ChatGPT](https://img.shields.io/badge/works%20in-Claude%20Code%20%C2%B7%20Claude%20%C2%B7%20Cursor%20%C2%B7%20ChatGPT-d97757)](#where-it-runs)

**A plugin and agent skill for Claude Code, Claude, Cursor and ChatGPT that directs and produces short AI video, brief
to export. In Claude Code, a spend gate checks every paid call and a named person approves between stages.**

It works the way a small production team does: concept, script, storyboard, casting, start frames, voice, clips,
selects, music, edit, picture lock, mix and titles, QC, delivery. It also plans and prices a job without making
anything, reviews a cut, and breaks down a reference ad.

<!-- DEMO: the demo video goes here. Drag the .mp4 (under 10 MB) into a GitHub README edit and paste the
     github.com/user-attachments/... URL on its own line, or link a poster still to the full video. -->

## Install

In Claude Code:

```
/plugin marketplace add designupstrategyaz/cinematographly
/plugin install cinematographly@cinematographly
```

(On Claude Code 2.1.275 or later, one line does both: `/plugin install cinematographly --marketplace designupstrategyaz/cinematographly`.)

Restart Claude Code, then run `/cinematographly:doctor`. If the commands do not appear, run
`claude plugin details cinematographly` in a terminal and check the plugin is enabled.

**In Claude, Cursor or ChatGPT:** add the `skills/cinematographly` folder as a skill in the app's own skill settings.
The skill and its scripts work there, but the spend gate is not automatic, because it runs through Claude Code's hooks.
Version 3.3 adds Cursor and ChatGPT packages with their own gate. See [Where it runs](#where-it-runs).

**Upgrading from the old `cinematography` plugin?** Uninstall it first, so two gates do not run on one call: in
`/plugin` find the line `cinematography@<marketplace>` and uninstall it, or run
`claude plugin uninstall cinematography@<marketplace>` in a terminal. Your settings in `~/.cinematography` are merged into `~/.cinematographly` the first time
the gate runs; nothing is overwritten and an open job survives. `doctor` turns red while the old plugin is installed.

## How it works

```
 you ── brief ──▶ Claude + Cinematographly ──▶ wants a paid call (picture, clip, voice…)
                                                      │
                               PreToolUse hook ──▶ gate.py
                                                      │
              ┌──────────────── is a job open? is the stage before it approved, in your own words?
              │                 is the prompt linted? is it inside the job's budget?
              │
        no ───┴──▶ DENIED, with the reason (nothing is spent)
        yes ─────▶ your normal permission prompt still shows ──▶ the vendor runs it ──▶ logged by hash
```

- **Approvals are your words, quoted.** After you have seen the work, your reply is recorded as the approval, under the
  approver the job names. The agent cannot approve for you, a stage signed out of order is refused, and an approval
  whose words cannot be checked against this session is refused (where hooks never run, e.g. Cowork, set
  `studio_setup.py --hookless` once: approvals are then recorded as unverified, and batch approvals are not available).
- **The gate fails closed.** If it cannot run or answers nothing, the paid call is refused.
- **Reads are free and silent.** Model lists, balances, job status and every local check run without asking.

## Your first ten minutes (nothing is spent)

1. `/cinematographly:setup` — makes `~/Cinematographly/` with your client folder (the templates and an invented sample
   client, `acme`, a bicycle repair shop), your studio history, and `jobs/`, and writes `~/.cinematographly/config.json`
   so every tool finds them.
2. `/cinematographly:doctor` — red lines block a first concept; amber lines can wait for the step that needs them.
   Then `/cinematographly:studio` asks the studio's questions (approvers, review policy, platforms, music and likeness,
   disclosure); the answers pre-fill new clients and jobs.
3. `/cinematographly:demo` makes a finished sample job to read first (nothing in it can spend), and
   `/cinematographly:new-client` interviews you about a real client and writes their profile.
4. `/cinematographly:new-job acme first-promo --mode A --approver "Your Name"` — a job folder and a checkpoint that
   opens for a concept only: no inputs yet, a budget of 0 credits, nothing priced; every paid generation is refused (other paid tools ask you first). The approver
   is the person whose words approve each stage (you, on a trial); `acme`'s own approver is invented, so the job
   refuses without one.
5. Say: *"Develop the concept for this job."* It asks you first (what you would be proud of, what you would hate,
   references, your own phrases), then researches, writes five different concepts, runs adversarial kill rounds and
   shows you the survivors. No paid picture is made.
6. `/cinematographly:next` — what the job owes now. When it is an approval, you answer in your own words, for example
   *"Approved: go with concept C2."*

A concept and a script need neither a Higgsfield account nor DaVinci Resolve. Prefer to plan only? *"Plan and price
a 30-second promo for acme. Spend nothing."*

## Clients, teams and delivery (3.1)

- `/cinematographly:review-pack <stage> <files>` makes a static review page to send a client. Their reply is evidence;
  the approval is still the Approver's sentence in the chat, carrying the pack's code. A changed file needs a new pack.
- Optional `Producer:`, `Editor:` and `Reviewer:` checkpoint lines show who does what. Only the Approver approves.
- `/cinematographly:deliver <platforms>` builds one upload-by-hand folder per platform after the export is approved:
  master, captions, cover frame, disclosure line. Nothing is posted for you.
- Closing a job writes a scorecard: yield, retakes per shot, credits per kept take and per kept second.
- Production settings: `/cinematographly:studio` also asks for a monthly credit ceiling (a real stop: a person confirms
  each call past it), the regens one batch approval covers by default, a retake factor for new clients' estimates, and
  an optional second-opinion model. Each can only make jobs stricter. START-HERE.md, "What you can set", has the table.

## Edit in DaVinci Resolve, Final Cut Pro or Premiere Pro

Once the takes are selected, the plugin proposes where each one is cut from its measured motion: IN just before the
motion starts, never inside the start-frame settle, the shot's planned length kept, the action never split. A shot whose
action does not fit is left **unresolved** with the frame count and your three choices (regenerate longer, re-plan the
length, trim the action); nothing is chosen for you. Joins are checked for planned screen-direction clashes and for a
tracked object that jumps across a match cut. Say *"plan the cut"* (`cut_plan.py`), then *"export the timeline"*
(`timeline_export.py`):

| Editor | File | What it gets | Tested |
|---|---|---|---|
| DaVinci Resolve | `.fcpxml` (1.10) | the cut, handles, voice-over, then native titles, grade and the Fairlight music rebuild by computer control | imported on Resolve Studio 21.1.2: every clip frame-exact at 23.976 |
| Final Cut Pro 10.6+ / 11 | the same `.fcpxml` | the cut with handles and the voice-over trimmed to each shot | structurally tested, not imported here |
| Premiere Pro | `.xml` (FCP 7 XML, xmeml v5) — **experimental** | the same | structurally tested; also imported frame-exact into Resolve |

Frame-exact at 23.976, 24, 25, 29.97, 30, 59.94 and 60 fps (no drop-frame timecode). Not in the files: music
(`CUTS.md` says which original track to place and where), transitions, split audio edits. Clip markers did not survive
the Resolve import in our test; the same notes are in `07-edit/CUTS.md`. Paths are absolute: relink if the media
moves. If you import into Final Cut or Premiere, a short report of what came through is very welcome.

## What you need

| Need | For | Notes |
|---|---|---|
| Claude Code (CLI or desktop app), macOS or Linux, or Claude, Cursor or ChatGPT (see [Where it runs](#where-it-runs)) | everything | Windows is not supported (paths and the Resolve tooling) |
| Python 3.9+ as `python3` | the gate and the scripts | The gate uses only the standard library |
| `numpy`, `opencv-python-headless`, `Pillow` | the checks that measure pictures and sound | `/cinematographly:setup --install-deps`; optional extras are listed per tool in `requirements.txt` |
| `ffmpeg` and `ffprobe` | clip, loudness and export checks | |
| DaVinci Resolve Studio | edit, grade, native titles, mix | Built and tested on 21.1 |
| A Higgsfield account connected to Claude | AI generation | Kling's own API is supported too |
| Node.js | HyperFrames and GSAP titles only | GSAP keeps its own licence |

## Where it runs

| App | What runs | Spend gate |
|---|---|---|
| Claude Code (CLI or desktop app) | everything | automatic, through the plugin's hooks |
| Claude (Cowork) | the skill, and the scripts where a shell is available | automatic only where the app runs plugin hooks; elsewhere set `studio_setup.py --hookless` and approvals are recorded as unverified |
| Cursor | the skill | not automatic yet; 3.3 adds a Cursor package and gate |
| ChatGPT | the skill | not automatic yet; 3.3 adds a ChatGPT package and gate |

The DaVinci Resolve stage runs only on the machine where Resolve Studio is open (built and tested on macOS), whichever app you use.

## Under the hood

Cinematographly is a Claude Code plugin: one skill, 110 Python scripts, 10 slash commands, 8 subagents and a set of hooks. `SKILL.md` is the agent's rulebook, and 58 reference files are loaded stage by stage, only when that stage needs them.

The spend gate runs as a `PreToolUse` hook. `hooks.json` routes every Higgsfield, Kling, Scenario and DaVinci Resolve tool, plus any claude.ai connector matched by its id, to `gate.py`. Each hook has a 20-second timeout and `onFailure` set to block, and `gate.py` exits 2 for older Claude Code. So a crash, a timeout or an empty answer refuses the call.

Before a paid call runs, the gate checks four things. A job must be open: a checkpoint file that `gate.py open` has validated. Each stage before it must be approved in the approver's own words, found in this session's transcript. The prompt must have passed `prompt_lint.py`, and the call must fit the job's credit envelope.

Reads pass silently. Publishing needs the export approval. A Resolve script that starts a render or calls Resolve's AI voice or auto-captions is denied. After each generate call, a `PostToolUse` hook records the request by hash, so an identical retry within 30 minutes asks first.

The monthly credit ceiling sums one file per spend event, grouped by UTC month; a call past it needs a person to confirm it. Each Claude session keeps its own job pointer and transcript path, so two windows never share a job.

The pipeline has 15 stages, from intake to delivery. Each writes an artifact into a fixed job folder, and the next gate checks that artifact. Picture lock is a one-way door. Independent units fan out to the subagents: research, drafts, critiques, shot prompts, scene continuity, take review and sound-effect spotting. Agents never spend, approve or touch Resolve.

Quality checks measure the files: `clip_qa.py`, `motion_qa.py`, `look_qa.py`, `mix_qa.py` for loudness, `lipsync_check.py`, `title_qa.py` and `srt_qa.py`. A contact sheet is built before any draft is shown.

For the edit, `cut_plan.py` places each cut from the measured motion of the take. `timeline_export.py` writes FCPXML 1.10 for DaVinci Resolve and Final Cut Pro, and FCP 7 XML (xmeml v5) for Premiere Pro, which is experimental. On Resolve Studio 21.1.2 every clip imported frame-exact at 23.976 fps, and the exporter supports seven frame rates without drop-frame timecode.

Costs come from a dated rate card. Each client has a cost file with a retake factor, a job is priced before anything is spent, and closing a job writes a scorecard: credits per kept take and per kept second.

The test runner checks 109 scripts: 5 suites and 89 self-tests. The public CI runs four jobs: the gate on the macOS system Python with the standard library only, the full suite on Python 3.12, `claude plugin validate --strict`, and REUSE licence checks.

## What it stores, and where

- `~/.cinematographly/` (or `$CINE_HOME`): one record per Claude session in `sessions/` (its open job, its transcript's
  path, to check approvals are your words; kept per session so two windows never share a job), connector settings, `seen-connectors.json` (ids of connectors the gate asked you about, kept so `doctor` can
  show which to name), the bypass log, `config.json`. Local only.
- Your studio folder: client profiles, history and jobs. Outside the plugin, because an update replaces the plugin's
  folders.
- **No telemetry, no phone-home.** The scripts go online only when you ask for something that needs it: a Pixabay or
  Poly Haven search, or downloading your finished renders from a link you give (`pull_finals.py`). Paid calls go to
  the vendors you connect, through Claude.

## What it costs

Prices come from `skills/cinematographly/assets/higgsfield-rates.json`; each line carries the date it was read. Check
them against your account before quoting a client (`skills/cinematographly/scripts/refresh_costs.md`). Plan for
edit handles: B-roll and silent clips are generated at about 1.7× the on-screen length, so each cut has
room (the retake allowance is a separate number, `retry` in each client's cost file). Ask *"what will this cost?"* at any point.

## What it will never do

Spend without an approval on record; use AI images as references; import a title as a movie (titles are native Resolve
titles); advanced VFX (one exception: a masked repair of one region); pick the music for you; work in a language other
than English; show a draft before its contact sheet; use Higgsfield `motion_control`.
[`skills/cinematographly/START-HERE.md`](skills/cinematographly/START-HERE.md) is the full page for people;
`SKILL.md` beside it is the agent's rulebook.

## What the checks do not cover (3.1)

The gate checks every paid call, approval and export against files on your machine. It does not stop:

- **Hand edits.** Anyone with a shell, the agent included, can edit a checkpoint, `studio.json`, `connectors.json` or the
  spend records, set the connector environment variables,
  or point a command at a different home folder (`CINE_HOME`). Each shows in the session. A job that already has a
  transcript-checked approval refuses an unchecked one from anywhere. Raising a budget or the monthly ceiling through the plugin needs a person's words.
- **Parallel calls.** Spend is counted when a call returns. Several calls sent at once are each checked against the same
  total, so a job envelope or the monthly ceiling can be passed by up to one batch.
- **Another session's name, given on purpose.** `--session <id>` lets a command use another recorded session's
  transcript and job. A window never picks up another window's job on its own. Run approvals in the session where the
  person said them.
- **Review packs are opt-in.** Once a pack exists for a stage, its approval must cite the pack's code. A stage with no
  pack does not need one.
- **Uncounted tools.** Kling bills its own account. Upscale, dubbing and other tools with no price ask every time and
  are not counted toward the month.

## Licence and pricing

**Source-available, not OSI open source.** Free to use, change and use for paid client work for a studio of
**3 people or fewer**. Count employees, working owners and partners, regular contractors and affiliates, once
each, part-time people included: the count is the whole business, not a seat count (LICENSE, section 1). Larger
studios need a commercial licence, $99 per seat (a seat is one person who uses it):
see [`COMMERCIAL.md`](COMMERCIAL.md) or write to vladms@designupstrategyaz.xyz. You may share free copies and forks
with the licence and notices kept; you may not sell the plugin, host it as a paid service, or sell a subscription or bundle whose customer is paying for
it. The recipient's own size decides whether they may use a copy you share. The licensor
claims no ownership in the films you make (your client contracts decide who owns them); changed plugin files stay
under the licence. Third-party parts keep
their own licences. Full terms: [`LICENSE`](LICENSE); if this summary and LICENSE differ, LICENSE controls.

**Support the project or buy a commercial licence:** [designupstrategyaz.gumroad.com](https://designupstrategyaz.gumroad.com).

## Contributing and security

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) (contributions need a `Signed-off-by` line) and the
[code of conduct](CODE_OF_CONDUCT.md). Report a security problem privately, as [`SECURITY.md`](SECURITY.md) says,
never in a public issue.

Cinematographly is not affiliated with Anthropic, Higgsfield, Kling, Blackmagic Design, Apple or Adobe.
