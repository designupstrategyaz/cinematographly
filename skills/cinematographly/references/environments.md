# Execution Environments — where this skill runs, and what each place can reach

The skill is one playbook, but it executes in three different places with three different
capability sets. Most "why isn't this working" moments are actually "wrong environment for this
step." Route the step to the place that can do it.

---

## 1. The three environments

| Capability | **Claude Code (on the Mac)** | **Cowork cloud container** | **Cowork device VM** (`device_bash`) |
|---|---|---|---|
| Production folders | direct, native paths | staged copies via the device bridge | mounted at `$HOME/mnt/<folder>` |
| Run `scripts/*.py` | ✅ | ✅ (on staged files) | ✅ (ffmpeg/ffprobe **with libass** — a caption burn with a recorded reason runs here; the default burn is Resolve's, house rule C7) |
| Network egress | per user config | ✅ allowlisted | ❌ **none** (verified: HTTP 000) |
| Higgsfield MCP | ✅ if configured in `.mcp.json` | ✅ when attached to the session | ❌ |
| ClickUp MCP | ✅ if configured | ✅ when attached | ❌ |
| **DaVinci Resolve MCP** | ✅ **the only place it works** | ❌ no localhost path to the Mac | ❌ |
| Another model for second opinions (optional) | ✅ if the studio connected one | ✅ if connected | ❌ no egress |
| Watch/hear a clip (human) | ✅ locally | via staged files / sent files | n/a |

**Rules of thumb:**
- **Generation and research** run anywhere with egress — cloud container or Claude Code.
- **Review-platform API calls** (Frame.io shares, uploads, comment pulls — `review-and-approval.md`
  §6) need egress: Claude Code on the Mac or the cloud container, never the device VM. The
  CSV→EDL converter (`frameio_comments_to_edl.py`) is offline and runs anywhere.
- **File surgery on production folders** (conform, strip, manifest, contact sheets) runs where the
  files are: device VM in Cowork, natively in Claude Code.
- **The Resolve stage runs in Claude Code or not at all** (as an MCP; the console-paste scripts are
  the everywhere-fallback).
- **Never assume egress in the device VM.** Installs, API calls, and downloads there fail silently
  slow; route them to the cloud container.

## 2. Running the skill in Claude Code

Yes — the skill is already packaged as a Claude Code plugin
(the plugin manifest at `../../.claude-plugin/plugin.json`, two levels above this skill folder). In Claude Code on the production Mac
you get the *full* pipeline in one place: native file access, every script, the MCPs, and Resolve.

Setup, once per machine:

1. Install/enable the plugin (from the marketplace it was shared through, or point Claude Code
   at the local folder).
2. Configure MCPs in the project's `.mcp.json`: Higgsfield and ClickUp. The Resolve MCP comes with
   Resolve Studio 21.1 and is registered at user scope (§3).
3. ⛔ **Keys stay out of the repo, always.** This folder is a git repo that pushes to GitHub and
   ships as a `.plugin` bundle other people install — a credential committed here is published, not
   stored. The convention, per key:

   | Key | Where it lives | How the tool reads it |
   |---|---|---|
   | Pixabay | `~/.config/pixabay.key`, `chmod 600` — or `export PIXABAY_API_KEY=...` in your shell profile | `pixabay_search.py --key-file ~/.config/pixabay.key`, or the env var. ⛔ There is deliberately **no `--key` argument**: a key on the command line lands in shell history and in every process listing |
   | Higgsfield | the MCP server's own config, never a file here | the MCP client |
   | ClickUp | the MCP server's own config | the MCP client |

   The Pixabay key is personal and issued on login — the docs page's `key` field reads *"Please
   login to see your API key here"* [PRIMARY · pixabay.com/api/docs · read 2026-09-06]; 100 requests
   per 60 seconds, bound to the key rather than your IP. **A key found in a public repository is
   somebody else's credential and rate limit, and is rotated as soon as it is noticed — it is not a
   shortcut, it is a dead end.** If a key ever does reach a transcript, a screenshot or a commit,
   rotate it on the account rather than hoping.
4. Verify with a dry pass: `python3 scripts/run_tests.py` from the skill folder, then a
   `get_cost:true` probe through the Higgsfield MCP.

The skill text needs no changes between environments — paths in client profiles are the Mac's real
paths, which is exactly what Claude Code sees.

## 2b. Where the gate runs — and the one test that proves it (2026-09-06)

The gate (`SKILL.md` §0, `scripts/gate.py`) has three layers, and which of them is live depends on
the environment:

| Layer | Claude Code CLI (Mac) | Cowork (desktop / cloud) | Device VM |
|---|---|---|---|
| `hooks/hooks.json` PreToolUse → `gate.py hook` | **fires** — documented plugin-hook shape | ✅ **VERIFIED FIRING 2026-09-06** in a cloud Cowork session: a live `generate_image` with `get_cost: true` and no job open came back refused with the gate's own reason, and SessionStart wrote `$CINE_HOME/transcript-path`. ✅ **RE-VERIFIED 2026-09-07** the same way (`generate_video`, `wan3_0`, `get_cost: true`) **after a day of heavy `gate.py` edits** — the master-gate requirement, the coverage floor, a new `glob` import. Re-running the ten-second test after touching the gate is the cheap half of not breaking it, and it costs nothing because `get_cost: true` submits no job. (#63360 is about LOCAL Cowork seeing host hooks; a cloud session syncs the plugin and runs them.) | no Higgsfield MCP here |
| `gate.py preflight` before every call, by you | required | **required — you are the hook** | — |
| `gate.py reconcile transactions.json` after | required | required | — |

**The proof, ten seconds, spends nothing:** with no job open, call `generate_image` with
`get_cost: true`. ⛔ Read the refusal text, not just the fact of it: on 2026-09-07 it named **a stale active job** — `/tmp/eval-…/jobs/bk-01001-morning no longer exists` — a pointer left behind by that morning's eval runs and carried all day. The gate denied correctly either way, but a dangling pointer means `status` and `reconcile` have been answering about a job that is gone. `gate.py close`, or open the real one.
If the call is **denied** with "No production job is open", the hook fires in
this environment; if the cost comes back, it does not, and the second and third layers are the
whole gate there. **Run it once per environment and record the answer** — cloud Cowork was verified
2026-09-06 (a close-out note of 2026-09-06 on the reference plan [studio history]); the Claude Code CLI on the Mac and the
desktop Cowork app are still untested by this method.
`CINE_HOME` (default `~/.cinematographly`) holds the active-job pointer; `CINE_JOB` overrides it for
one shell; `CINE_GATE=off` in the *launching* shell bypasses the hook and is logged.

## 3. The DaVinci Resolve MCP — the one that ships inside Resolve Studio (2026-09-14)

**Resolve Studio 21.1 ships its own MCP server:** `ResolveMCP` inside the app bundle
(`/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolveMCP`), plus a Claude
Desktop extension (`Contents/Resources/DaVinciResolve.mcpb`, author "Blackmagic Design", which states
it needs Resolve **Studio**) [PRIMARY · the shipped files · read 2026-09-14]. That is the Resolve MCP
this skill targets. ⛔ The community server this runbook used to name (`samuelgursky/davinci-resolve-mcp`,
`npx davinci-resolve-mcp setup`) was removed from the production Mac on 2026-09-14 — do not install it
next to the official one: two servers driving one Resolve are two sets of assumptions about the same
project. It only works **on the same machine as a running Resolve Studio** — Claude Code on the Mac.

1. **Requirements:** DaVinci Resolve **Studio 21.1+** (21.1 moved Python scripting to Studio; on the
   FREE edition neither this server nor console Python runs — `editing-and-audio.md`, the 21.1 note) · Preferences ▸ System ▸ General ▸ *External scripting
   using* = **Local** (Blackmagic's scripting README lists that preference as a prerequisite) · no
   Python install — 21.1 bundles its own.
2. **Registration:** on the production Mac the entry `"DaVinci Resolve"` → the `ResolveMCP` path above
   was already in `~/.claude.json` after the 21.1 install. Check with `claude mcp get "DaVinci Resolve"`;
   the tools arrive as `mcp__DaVinci_Resolve__*`.
3. **What it gives you — 14 tools** [MEASURED · 2026-09-14]:
   - read-only: `get_resolve_status`, `search_scripting_api` / `get_scripting_api` (the 21.1 API stubs),
     `get_scripting_docs` (Blackmagic's README), `list_luts`, `list_dctls`, `launch_resolve`;
   - `run_script` — Python with `resolve` and `project` injected; **no `os`, no `open`** (`json` and
     `posixpath` import fine); 10 s timeout by default, 60 s max. It cannot touch files — Resolve itself
     still reads media and writes renders at the paths you give it;
   - `run_script_unsafe` — the same with the whole OS, and a script that times out **keeps running**
     inside the server [PRIMARY · the server source, read 2026-09-14]. Use it only when the OS is the
     point;
   - `generate_lut`, `update_dctl`, `delete_lut`, `delete_dctl` (write only under `…/LUT/MCP`).
   - ⛔ `get_whats_new` stops at 21.0.4 while answering "you are up to date with DaVinci Resolve 21.1"
     [MEASURED]. For what 21.1 changed, read
     `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/CHANGELOG.md`.
4. **The gate reads it.** `hooks/hooks.json` sends every `mcp__DaVinci_Resolve__*` call through
   `scripts/gate.py`: read-only tools pass silently; a `run_script` that **starts** a render, calls
   Resolve's AI Speech Generator or auto-captions from audio is **denied** (each has its own gate in
   this skill), and since v2.49 so is one that **writes** Fusion, Fairlight or a native title (owner
   rule 8: that work is computer control; reads stay open); render settings, deletes and project switches **ask**; `run_script_unsafe` and LUT/DCTL
   writes always ask. The scan reads code, not comments or strings, and says so when `getattr`/`exec`
   hides a call — it is a guard against honest mistakes, not a seal (SKILL.md §0, the trust boundary).
5. **The two scripts run through it unchanged.** `render-mp4.py` and `resolve-production-console.py`
   detect which environment they are in: sent as the `run_script` script they return their result in
   `result` instead of writing files; pasted into Workspace ▸ Console ▸ Py3 they behave as before.
   `scripts/test_console_scripts.py` executes both, in both environments, against a fake Resolve that
   encodes the measurements below.
6. **Verify before trusting it — re-run after every Resolve update** (evidence, not intention). Run on
   2026-09-14 against Studio 21.1.0.14, in a scratch project: `get_resolve_status` → create a timeline →
   `AddTrack` (✅) → `SetTrackName` + `GetTrackName` (✅ reads back) → `AddMarker(10)` and read it back
   through an OTIO export (✅ 10 frames from the timeline's first frame) → queue one render job and read
   `GetRenderJobList()` back (✅, but see 7). ⛔ **Do it in a project you have NAMED** — see 7.
7. **Hazards measured on the production Mac:**
   - **Resolve aborts inside the Deliver page's render-settings widget.** Five aborts with that stack in
     `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/crash_archive.txt` — 2026-08-29 ×4
     on 21.0.3, 2026-09-14 on 21.1. On 2026-09-14 a scripted render-settings change reproduced it once,
     and the same calls minutes later did not. Cause unproven. `render-mp4.py` saves the named project
     first and only queues.
   - **Making a timeline in an unsaved project auto-saves it** as `Untitled Project <date>_<time>` — a
     "scratch" test leaves a real project in the library, and a crash then takes it down with it.
   - `Project.SaveProject` does not exist (the attribute is `None`); `ProjectManager.SaveProject()`
     returns True on a saved, named project.
   - `AddMarker` returns True for a frame an hour past the end of the timeline — read markers back.
   - Render calls switch Resolve to the Deliver page; put the page back.
8. **Fallback everywhere else:** the same two scripts, pasted into Workspace ▸ Console ▸ Py3 on the
   editor's machine. That is why the skill still ships exactly two of them.
9. **One approval for a session's scripts** (2026-10-28: *"stop asking me to approve every script for
   Davinci, do it in a batch, like with AI gens"*). `gate.py allow resolve --scope edit,render --scripts N --hours H
   --by … --quote "…"` records one allowance; each `run_script` it covers passes as *preapproved* and spends one
   script (default 200 scripts over 12 h). Denied as before, whatever the allowance: a script that starts a render, the
   AI Speech Generator, auto-captions. Still asked every time: deletes, project switches, and a script the scan cannot
   read. `run_script_unsafe` and LUT/DCTL writes are covered only by the scopes `unsafe` and `luts`, named on purpose.
   `gate.py allow --list` shows what is left; `--revoke` ends it.

## 3c. Resolve 21.1.1 as measured on a supplement ad job (2026-10-25 → 28)

Every line below was measured on the production Mac in one 162 s 9:16 ad. They are in `scripts/test_console_scripts.py`'s
fake, so the console copies are tested against them.

**Text and titles**

v2.49 (house rule 8, 2026-11-05: *"It fails all the time"*): native titles, Fusion and Fairlight work are done by
**computer control** in Resolve's interface, never through the scripting API; the API keeps reads, timeline setup,
media import, markers and the render queue (`editing-and-audio.md` § What runs through the API). The lines below stay
as the measured record of why, and as what a computer-control placement must still check (the ripple, the locks,
the read-back, the still). `PLACE_TITLES` is retired as a placement route, and `gate.py` denies it through
`run_script`.
- **A Fusion comp on a clip does not show on the Edit page.** Text+ added inside a clip's own comp (`AddFusionComp`)
  never rendered on 12 card clips. Titles are Text+ title clips: `InsertFusionTitleIntoTimeline`.
- **The insert lands on the topmost unlocked video track, at the playhead, for the mark in–out** (120 frames with no
  marks). Every other unlocked track ripples: the first insert pushed V1 by 120 frames. Inserting onto V3 with V4
  locked failed silently. So: lock every track but the text track, set `SetCurrentTimecode` and `SetMarkInOut`,
  insert, `ClearMarkInOut`, restore the locks. Place the text tracks bottom-up (Titles, then Disclosure, then Supers).
  `PLACE_TITLES` does all of it and reports a track that is not on top.
- **Write `StyledText` inside `comp.Lock()` / `comp.Unlock()`.** `SetInput` alone read back empty on all 12 titles after
  a later edit. Confirm with a still.
- **Layout keys that work:** left-aligned `HorizontalLeftCenterRight = -1` with `HorizontalJustificationNew = 0`; a
  highlighter or pill is element 3 — `ElementShape3 = 2`, `Offset3 = {0, 0}` (it defaults to a shadow offset),
  `Level3 = 1` for one bar per line.
- **`DeleteFusionCompByName` cannot delete a clip's last comp.** Delete the tools inside and wire MediaIn to MediaOut.
- **A still image can only be placed at 120 frames.** Use a short video carrier, or Text+.
- **ProRes 4444 alpha overlays showed as black boxes after a relaunch; QuickTime Animation (qtrle) did not.** Prefer
  native Text+; for an outside overlay with a recorded reason (C7), qtrle.
- **Verify with `Project.ExportCurrentFrameAsStill(path)`, never a screenshot.** A screenshot goes stale when Resolve is
  on another Space; a still is the composite. Export one per placed title into `09-qa/stills/` (a read, so the API
  may do it) and put them on a contact sheet.
- **The standard track layout:** V1 Picture, V2 Graphics, V3 Titles, V4 Disclosure, V5 Supers (`TRACK_LAYOUT`,
  `NAME_TRACKS`). `render-mp4.py TITLE_TRACKS` is `titles` and `supers` only: a titles-off render keeps the graphics
  and the disclosure.

**Subtitles**
- The `.srt` imports with `AppendToTimeline` and the playhead at the timeline's start (frame 0). `mediaType 3` crashed
  Resolve. `SetTrackEnable("subtitle", …)` does nothing, so a picture-only render keeps the subtitles out with
  `ExportSubtitle = False`.

**Timeline integrity**
- **The editor edits while the agent edits.** On that job V2 was emptied, tracks went missing, one was disabled and a
  render job replaced — and the supers vanished unnoticed until the final check. Read the timeline back before every
  write, lock what you are not touching, and run the invariant: `SNAPSHOT_TIMELINE` before a structural edit, then the
  next console copy with `EXPECT_SNAPSHOT` (`native.py console --expect <snapshot>`) compares items per track, every
  title by name, the track names and enable states. Keep `07-edit/RESOLVE-PLACEMENT.json` current: it was the only way
  to rebuild V2.
- Once titles live in Resolve, the timeline is the truth: `DUMP_TIMELINE_JSON` (it carries each title's words) →
  `native.py sync-specs <job> --write` rewrites each spec's time, length and words.

**Renders and the bridge**
- **A render can report "Complete" with no file on disk.** After every render, check the file exists and has a size
  before any QC.
- **The bridge sometimes returns an empty error.** Retry once with a trivial call (`resolve.GetVersionString()`) before
  assuming anything changed.
- The `run_script` sandbox has no `os` and no `open`: scripts print or return their results; the agent writes the file.
- `gate.py pre-lock --write [--host-job <the job's path on the Mac>]` writes the three renders lock reads (the cut,
  titles off, picture only) as filled `render-mp4.py` copies in `07-edit/_queue/`; one `gate.py allow resolve --scope
  render --scripts 3` covers them.

**Fairlight — what the API can and cannot do**
- **Can:** Dialogue Leveler, Voice Isolation, `NormalizeAudioLevel`, a saved Fairlight preset, clip `AudioVolume` (up to
  +30 dB — useful for a quiet library file).
- **Cannot:** EQ, dynamics, limiters, ducking. Those are the Fairlight UI, through computer use: Bus 1 ▸ Dynamics ▸
  Limiter, and the track's EQ window. **Computer use fails while the owner's current Space is a full-screen app** — ask
  them to leave it before starting; never retry blind.
- **Never apply a Fairlight preset from another project.** A preset saved for one ad maps to a different track layout on the next.
- **Never drop a Python render back on the timeline (v2.50).** That job's music bed (trim, seam, level ride,
  duck, speech-band carve) was once processed outside and dropped back on the music track. Author, 2026-11-05: that
  works for previews, but the client's version is rebuilt and done in Resolve. `music_fit.py bed` and `render` are
  previews and level plans; `gate.py` refuses a script that imports one (`editing-and-audio.md` § Music to picture).

**Moving files between the cloud session and the Mac**
- `device_stage_files` fails for a path more than 7 folders deep: copy the file to `<project>/_claude-stage/`
  on the Mac first.
- `device_commit_files` fails at about 27 MB with HTTP 400, under its stated 30 MB: keep each file ≤ 23 MB (a 47 MB WAV
  went over as two halves joined on the Mac). Committing a revised file again from the **same** staged path wrote the
  earlier upload, reporting success (measured 2026-10-28): stage each revision under a new name, and check the hash on
  the Mac after every commit.
- `device_bash` cannot delete in a connected folder until the owner grants it once
  (`device_request_delete_permission`): ask once, for the narrowest folder.
- The plugin can be reinstalled under a session (`cinematography` → `cinematography~g2`): run the scripts from the path
  the SessionStart line names (`gate.py where`), never from one remembered from an earlier session.
- A CHECKPOINT `Client:` names a profile by name (`acme`), not by a path: a cloud path is not on the Mac.
  `gate.py` finds it from `CINE_CLIENTS` or a `_cine-clients/` folder above the job.

## 3b. Which environment should own the workflow?

The honest answer is **both, split by what the work touches** — and the split is not a compromise,
it follows from one hard constraint and one soft one.

The hard constraint: **Claude Code on the Mac is the only place the Resolve MCP can run**, and it is
the only place with native access to the media without staging files across a bridge. So everything
downstream of an approved script belongs there: generation, the refinement loop, the edit, captions,
QC, export. Running that half anywhere else means moving gigabytes to reach a Resolve that is not
there.

The soft one: a cloud session holds the connectors (ClickUp, Drive, mail), can run long research and
subagent work while you are away from the machine, and does not stop when the laptop closes. So the
work that is *about* the videos rather than *in* them belongs here: research, ideation and scripting,
compliance and claims checks, the batch plan, PM, client comms, metrics pulls, and maintaining this
skill.

**The handoff between them is this folder.** Both environments read the same doctrine, the same
client profiles and the same scripts, and the artifacts that carry state — the shot manifest, the
ledger, the decision records, `memory/LEDGER.md` — are files, not conversation. That is what makes
the split safe: neither environment has to remember what the other did.

⛔ **The Resolve MCP was verified on the production Mac on 2026-09-14** — Studio 21.1.0.14, through
`run_script`, by read-back (§3 step 6) — and one of those tests crashed Resolve (§3 step 7).
**Re-verify after every Resolve update:** a workflow built on an integration nobody re-checked is a
workflow that fails on the day you have a deadline.

## 4. A second model from inside production (optional)

Cross-vendor consults (script review, adversarial QA, bulk drafts) are optional. Use whatever
second-model tool your studio has, from the **cloud container or Claude Code**, never the device VM. Verify-always applies: an offloaded finding is a lead until checked
against the actual files.

**Cross-refs:** `editing-and-audio.md` (the Resolve MCP capability table and console-script
doctrine) · `PIPELINE.md` (the automated end-to-end) · `scripts/README.md` (script conventions and
the test runner) · `research-quality.md` (verification discipline for anything fetched).
