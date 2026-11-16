# PM Workflow — running production, output folders & file naming

You wear two hats: **director** (the craft) and **producer/PM** (the board, the gates, the
handoffs). This file is the producer hat — the general system. **The specific PM tool, workspace/
board IDs, the reusable template task, and the production root path are in the client profile**
(`clients/<brand>.md`).


> ⛔ **Every `python3 scripts/…` line in this skill assumes your shell is at the SKILL ROOT.**
> From anywhere else use the full path — `python3 <skill-root>/scripts/<tool>.py …`. The
> scripts resolve their *data* files relative to their own location, so they read the right
> `clients/` and `assets/` either way; it is only the command itself that needs the path.

## The project shape

One video = one **parent task** whose description holds the brief, plus **8 subtasks** run in
order. Keep the emoji names — they're the shared vocabulary of the board.

1. **📋 Brief & Script** — final script pasted in; script file saved to the project folder.
2. **🖼️ References & Storyboard** — shotlist + refs/storyboard.
3. **🤖 AI Generation** — start frames → clips per shot.
4. **🎙️ Voice & Audio** — character voices + SFX.
5. **🎵 Music** — bed track selected/licensed, BPM noted. **The user picks the track** from
   `creative/videos/music/`, never an autonomous default; fit it to the locked cut with
   `scripts/music_fit.py` (or plan a loop on the phrase lines with `loop_music_to_length.py` and make it in
   Resolve — v2.49, all edits in Resolve, `editing-and-audio.md` § Music bed).
6. **✂️ Assembly & Edit** — cut + beat-matching + burnt-in captions (captions are the only
   on-screen text by default; any title is one the project's title card names — `typography-and-captions.md`
   §6c), then the titles stage after picture lock.
7. **✅ Branding Check** — the compliance gate (the profile's non-negotiables).
8. **📤 Export** — final file in the client's delivery format + publish handoff.

Parent naming: `<HUMAN LABEL> – <PROGRAM/OFFER> <Segment>` (e.g. `ACME S01E007 – Spring tune-up Commuters`) — the human label, not the filename form; the task description carries the `acme-01007` show ID so a search finds either. Mark
urgent with 🚨 + priority. Most brands have a **reusable template task** to duplicate — the profile
gives its ID.

## Board operating conventions (ClickUp) — apply on every project

These are the account's standing PM conventions (they mirror the studio's project-management skill —
when that skill is available, load it for board-level work beyond production: prioritisation,
sprint planning, stakeholder updates. This file stays the production layer; don't duplicate its
twelve workflows here).

- **Log time at milestones, never with a live timer.** At each stage-gate and at session end, add a
  manual entry via `clickup_add_time_entry` (start + duration + a one-line note) on the relevant
  task. An AI session cannot guarantee a clean stop, so a running timer over-counts. Estimate active
  time honestly; never fabricate; never backfill past work.
- **Update the board at every milestone** (`clickup_create_comment` / `clickup_update_task`) so it
  reflects reality without the user relaying it. The account lead reads the board, not the folder.
- **Label every number's provenance:** `measured` (a tool or ledger said so — a settled Higgsfield
  transaction, an ffprobe readout, ClickUp time-in-status), `estimated` (you derived it —
  `estimate_duration.py`, `batch_plan.py` output), `assumed` (you made it up — a retry factor, an
  unverified rate). Assumed numbers are legitimate; **invisible ones are not.** This maps directly
  onto the cost discipline: the preflight is *estimated*, the ledger is *measured*, and the two are
  reconciled, never conflated.
- **Calibrate effort from history, not vibes.** `clickup_get_task_time_in_status` on the last three
  finished videos beats any fresh guess: if the last three "one-week" videos each took eleven days,
  a new one takes eleven days. Same rule as the per-shot-type cost actuals in `ai-generation.md` —
  cycle-time data wins wherever both exist.
- **Escalate before any write that leaves production.** Run this checklist before acting:
  - [ ] Sends email or a calendar invite? → **draft/propose only**; sending needs an explicit ask
        this session.
  - [ ] Changes priorities, dates, or assignees at scale? → show the diff, get approval, then apply.
  - [ ] Deletes or closes tasks? → explicit permission; prefer archiving or a "deprioritized" tag.
  - [ ] Commits a date to the client? → **the user approves external dates, never the agent.**
        (The silence rule in the approval loop below covers the reverse direction.)
  - [ ] Touches pricing, contract terms, or regulated claims? → flag it; it is not a production call.
  - [ ] A load-bearing number is missing? → ask now, don't assume silently.

### Decision records — write them at the time, not in the retro

Any real choice made during production gets a decision record: a mode routing that was genuinely
contested, a retake escalation past the cap, a format decision, a change-order, **any deviation
from a client hard lock** (the 2026-08-12 overlay lock is exactly this shape), a music/tone call the
client made. Format:

```
### Decision: <short title>
Date · Decided by (user approval) · Status: PROPOSED / APPROVED / IMPLEMENTED / REVERSED
Decision: <one paragraph, no hedging>
Reasoning: <the single factor that decided it>
Alternatives considered: <and why not, each>
Cost of this choice: <stated fairly — what the losing option's advocate loses>
Revisit if: <a number, an event, or a date>
```

Post it as a `clickup_create_comment` on the affected task (always), and durably in the project
folder (`00-brief/DECISIONS-<SLUG>.md`). **A reversed decision gets a new record pointing at the
old one — never edit the original**; the reversal reasoning is worth more than the decision.
A decision whose reasoning is lost gets re-litigated in six weeks by someone with less context —
on this account that someone is usually a future session of the same agent, which makes the record
cheaper than the re-litigation every single time.

### Verification readout — before any deliverable with numbers in it

A cost estimate, a batch plan, a capacity quote, a monthly report: none of it ships without six
lines. This is the difference between analysis and assertion:

```
VERIFICATION
────────────
Numbers:      each figure marked measured / estimated / assumed, with source
Arithmetic:   recomputed, not eyeballed (credits, durations, capacity)
Tool data:    what came from ClickUp / Higgsfield / ffprobe vs. what was inferred
Gaps:         what could not be verified, and how that limits the conclusion
Falsifiable:  the specific thing that would prove this wrong
Verdict:      SHIP / SHIP WITH CAVEATS / NEEDS INPUT
```

**If more than half the load-bearing numbers are `assumed`, the verdict is NEEDS INPUT, not SHIP** —
say which three numbers would change the answer most. This rule has a standing application here:
Mode B's economics have never been run in production, so any Mode B capacity quote is
SHIP WITH CAVEATS at best until real actuals exist. A silent skip is the failure mode; skipping the
readout for a conversational reply is fine, noted in one line.

## Standing up a new project

1. **Duplicate** the template task (or create a parent + the 8 subtasks with the emoji names).
2. **Rename** the parent for this video.
3. **Paste the brief** into the parent (offer, audience, mandatory facts, assumptions).
4. **Set priority + due dates**, working back from publish; give Script and Edit the most room.
5. **Work the subtasks top to bottom,** flipping status as you go so the board shows the truth.
6. **Attach outputs** to their subtask (script `.md`, clips, final `.mp4`).
7. **Create the folder tree including `_reference/`'s subfolders**, and fill the reference set
   *before* the storyboard gate — it is what the client reacts to at Gate 1, and a reference
   rejected there costs nothing while the same objection after generation costs the shot
   (`revisions.md` §3).

## ⚡ The dependency list — built BEFORE the first generation

`[SECONDARY · practitioner course]`

Before anything is generated, list **every visual that returns more than once** and what each one
locks. One row per returning visual — this is the shortest artefact in the project and the one that
decides how much of it is repairable:

| Asset class | What you lock | What it protects later |
|---|---|---|
| **Product** | silhouette, finish, badge, wheels/trim | every hero shot agreeing that it is one object |
| **Character** | face (one rendering), wardrobe, build | identity across shots and across a state change |
| **Prop** | shape, material, wear, **and its second state** if the script changes it | the close-up matching the wide |
| **Location** | the plate, cleared of failure invitations (`production-design.md` §5b) | arrivals, geography, and the bridge shot not spoiling the destination |

> ⛔ **Gate: before generating a scene, check that every returning visual has one approved reference
> and one stable name.** Not a description — a reference and a name. A visual that returns without
> one is not a risk, it is a *scheduled* continuity failure: it will be re-invented on its second
> appearance, and you will find out in the assembly.

The list is cheap because it is short, and it is valuable because it is **the thing you cannot add
later**. A reference introduced at shot 30 does not retroactively fix shots 1–29; it splits the film
into a before and an after.

**Folder structure is a RECOVERY mechanism, not tidiness.**
⚡ *"A fresh subfolder for each iteration makes the winning generation recoverable after hundreds of
attempts."* This is the argument for the versioned layout below that actually holds up under load:
by attempt 200 you will not remember which take was the good one, the filename will not tell you,
and the generation you want will be indistinguishable from the 199 you do not. One subfolder per
iteration, named for the iteration, is what makes "go back to the one from Tuesday" a command rather
than a search. The manifest (below) records lineage; the folders make the artefacts *findable*
without it.

## ⚡ The take ledger — one line per selected fragment

A selected take is not "the good one". It is a fragment that **solves a named job**, and something
was left behind to get it. Record all three:

| Selected fragment | The one job it solves | What is left behind |
|---|---|---|
| `S07_v12` 0:03–0:06 | the wind-blast beat, hero car readable | the driver's face is wrong in this take |
| `S12_v04` 0:00–0:02 | the disguise coming off | too fast in the assembly; needs a hold |

> **The test: select a take with a sentence you can finish — "I am keeping this because it supplies
> ___."** If the sentence will not finish, you are not selecting, you are accumulating. ⚡ And the
> third column is the one people skip: **an unrecorded compromise becomes an unexplained defect**
> three weeks later, when nobody remembers it was a choice.

This feeds the assembly directly: the middle column tells the editor what the fragment is *for*, so
a cut that loses the job is visible as a loss rather than as a length decision. It also feeds
`refinement-loop.md` §1b — a take's "left behind" column is the list of variables a later
correction pass is allowed to touch without reopening a solved choice.

## Output organization & file naming (senior-PM standard)

Assets pile up fast — start frames, two clips per two-speaker scene, B-roll, voice takes, music,
edits, versions, retries. A disciplined folder + naming scheme keeps a project findable,
hand-off-able, and auditable against the credit budget. **Use this structure for every video**,
under the client's production root (in the profile — this is *not* the skill folder):

```
<production-root>/<showid>-<slug>/            e.g. acme-01007-primar-comuna/
├── _reference/       INPUTS you did not generate — the reference set (see below)
│   ├── character/     identity sheets, turnarounds, approved faces
│   ├── wardrobe/      the garment, from the angles the shots need
│   ├── props/         the hero prop, lit as the close-up will light it
│   ├── environment/   the room, frozen as an image so it stops drifting
│   ├── light/         the ratio and direction — the thing a prompt cannot carry
│   ├── motion/        video references for movement, when the model takes them
│   └── <file>.json    provenance sidecar per asset (source, licence, date, cleared)
├── 00-brief/         BRIEF-<SLUG>.md · CHECKPOINT.md (validated by gate.py open) ·
│                      APPROVALS.md (gate.py approve — the human's verbatim replies + file hashes)
├── 01-script/        SCRIPT-<SLUG>-v<N>.md   MASTER-image-prompts-all-scenes.md
│   └── prompts/       <SHOT>.frame.prompt.md · <SHOT>.clip.prompt.md and their .ok sidecars
│                      (prompt_lint.py) — the ONLY text a generate_* call may carry
├── .gate/            decisions.log — every allow/ask/deny the gate made for this job
├── 02-startframes/   start-frame stills — GENERATED               (model role 1)
├── 03-clips/         character/dialogue clips      (model role 2)
├── 04-broll/         B-roll / cinematic            (model role 3)
├── 05-voice/         character lines + SFX
├── 06-music/         bed track(s)
├── 07-edit/          DaVinci Resolve project + WIP renders + resolve-production-console.py
├── 08-captions/      <SLUG>.srt (build_srt.py output; falls back to 07-edit/ if this doesn't exist)
├── 09-qa/            QA-LOG.md (one line per verdict WITH its observation — see
│                      `realism-qa.md` §6: the observation is the mechanism) + contact sheets
│   └── review/       client round record: comments-r<N>.csv (platform export, filtered to the
│                      asset) + markers-r<N>.edl (frameio_comments_to_edl.py) — the sign-off evidence
├── 10-export/        final deliverable(s)
└── 99-costs/         COSTS-<SLUG>.md  (estimate_duration.py output vs actual ledger, reconciled
                       against live transactions with reconcile_costs.py)
```

The three generation-model roles map to three folders on purpose (`02` start frames, `03` clips,
`04` B-roll) so anyone can see what came from where.

**`_reference/` is deliberately outside the numbering, and deliberately first.** The numbered
folders are pipeline *stages* — each one holds what that stage produced. The reference set is not a
stage: it is the material the stages are built from, it arrives before `00-brief` is finished, and
it is consumed by start frames, i2v, wardrobe continuity and the props pass alike. Filing it inside
`02-startframes/` — which an earlier draft of this skill did — mixes inputs with outputs in the one
folder where telling them apart matters most, because a reference photo of a real person sitting
among generated frames is exactly the asset that must never reach a delivery.

Three rules that make the folder worth having:

1. **One file carries one attribute**, and the subfolder says which (`refinement-loop.md` §1). A
   single image filed as "the vibe" is unusable the moment a shot is wrong, because you cannot tell
   which of the six things it was carrying went wrong.
2. **Provenance travels with every asset** — a `.json` sidecar naming the source, the licence, the
   download date and whether it is cleared (`stock-sourcing.md` §9). ⛔ An asset with no provenance
   cannot be cleared later, and an uncleared reference cannot ship. This is also where a
   recognisable face gets marked **reference-only**, so the rule survives the person who filed it.
3. **A promoted reference leaves the project.** One that produced an approved frame graduates into
   the client's Visual Bible (`clients/_TEMPLATE.md` §6) and is reused across the account rather
   than re-sourced per video — that is the compounding half of the visual system, the way the hook
   bank is on the writing side.

### Naming convention — the published VFX grammar, not a house invention

⛔ **Rewritten twice on 2026-08-30.** The first rewrite fixed the scaling break (a flat project
counter, and shot names that collide when a batch returns every episode's clips into one place). The
second replaced the homegrown shape with the **published cross-studio standard**, because there is
one and there was no reason to invent a second:

> `<showid>_<vfx-sequence>_<vfx-shot>_<image-type>{_<identifying-description>}{_<vendor-code>}_<revision-code>{_<alternate>}{_<camera-reference>}_<frame-number>.<file-extension>`
> — **ETC / MovieLabs, *VFX Image Sequence Naming* v1.0 (2020)** `[PRIMARY · published spec, read 2026-08-30]`

Adopting it costs nothing and buys three things a private scheme cannot: a contractor already knows
it, it is defensible to a client, and its field order is the one every post tool expects.

#### The grammar

```
<showid>_<seq>_<shot>_<type>_<subject>_<model>_v<NNN>[_<alt>].<ext>
```

```
acme-01007_s1_0020_frame01_host_gptimg_v001.png     a start frame, variant 1
acme-01007_s1_0020_frame02_host_gptimg_v001.png     variant 2 of the same shot
acme-01007_s1_0020_clip_host_seedance_v002.mp4      the clip, second generation
acme-01007_s1_0020_vo_host_tasha_v001.wav           the line
acme-01007_hk_0010_broll_panels-drone_cinema_v001.mp4  the hook's B-roll
acme-01007_master_v001_9x16.mp4                        the deliverable
```

**Audio deliverables carry no shot — they have all of them** — and add two fields picture does not
need, the channel layout and the rate + bit depth:

```
<showid>_<type>_v<NNN>[_<layout>][_<rate>].wav

acme-01007_mne_v001_20_48k24.wav        the undipped M&E — the file a language version needs
acme-01007_stem-m_v001_20_48k24.wav     the music stem
acme-01007_stem-d_v001_20_48k24.wav     dialogue · stem-e for effects · mix for the full mix
```

`20` = stereo (`10` mono, `51`, `71`); `48k24` = 48 kHz, 24-bit. ⛔ **A per-shot audio element is not
a deliverable** and keeps the picture grammar: `acme-01007_s1_0020_vo_host_tasha_v001.wav`.
Why these files exist at all, and why the M&E must be undipped: `editing-and-audio.md` § The audio
delivery layer.

| Field | Rule | Source |
|---|---|---|
| **`<showid>`** | `<brand>-<SS><EEE>` — brand, 2-digit season, 3-digit episode: `acme-01007` | ETC episodic show ID |
| **`<seq>`** | 2 letters for the sequence: `hk` hook · `s1`–`s4` scenes · `ct` CTA | Schiff (ACE); ETC allows 2–4 |
| **`<shot>`** | **4 digits, allocated in increments of 10** — `0010`, `0020`, `0030` | ETC (4-digit) + Schiff (the tens) |
| **`<type>`** | Elements: `frame` · `clip` · `broll` · `vo` · `sfx` · `mus`. Deliverables (no shot): `master` · `mix` · `mne` · `stem-d` · `stem-m` · `stem-e`. **Two digits appended = instance**: `frame01`, `frame02` | ETC image-type + instance number |
| **`<subject>`** | Character or B-roll descriptor, dashes for spaces, **identical all production long** | ETC identifying-description |
| **`<model>`** | The generating model — this pipeline's vendor | ETC vendor-code (deviated, below) |
| **`v<NNN>`** | **Three digits, zero-padded**: `v001`, `v002` | ETC: *"at least 3 numerals"* |
| **`[_<alt>]`** | Delivery-format token on exports only: `9x16`, `16x9`. Omitted on the primary | ETC alternate |

#### ⛔ The four character rules — these are the spec's, and they are not style

1. **Underscore separates FIELDS. Dash separates words INSIDE a field.** Nothing else. This is what
   makes every name parseable with `split("_")` and nothing more. *(The old `S1-C1` broke it: a dash
   was doing a separator's job.)*
2. **Lowercase everywhere.** The spec says *"all lower case is preferable"*, and the practical reason
   bites here specifically: macOS is case-insensitive, Linux is not, and these files cross between a
   Mac and Linux tooling constantly. `the host.png` and `host.png` are one file on one machine and
   two on the other, and the failure is silent.
3. **Alphanumeric and dash only. No whitespace.** So: `stefan`, never `ștefan` — diacritics belong
   in the script and the burnt-in captions, where they are the point; in a path they break tool
   round-trips and CSV exports without an error message.
4. **Zero-pad everything that sorts.** `v010` before `v002` in a listing is how a retake chain becomes
   unreadable, and it is the commonest naming failure there is.

#### ⛔ Why shot numbers go up in TENS — the rule worth stealing

> *"come up with 2-letter abbreviations for all the VFX sequences in the film, and then starting from
> 0010, name all your shots in increments of 10"* — it *"allows you to maintain a rough chronological
> order if you need to insert a new shot after an existing one."*
> — **Evan Schiff, ACE**, *Feature Turnover Guide — VFX* `[PRIMARY · working feature editor, read 2026-08-30]`

This is the single most valuable thing the grammar brings, because **inserting a beat is the most
common script change there is.** A reaction shot added between `0010` and `0020` becomes `0015`. No
renumbering, no rename, no broken manifest, no broken cost record. Under the old `S1-C1 / S1-C2` there
was nowhere to put it.

Schiff also **omits scene numbers from shot IDs on purpose** — *"an irrelevant piece of information
for VFX purposes."* Here the sequence code carries that job, which is why `<seq>` is `s1`, not the
scene number repeated in the shot.

#### ⛔ Three deliberate deviations from the spec, and the reason for each

A standard followed without understanding it is cargo cult. These three are chosen, not missed:

1. **The vendor code is a readable model token, not 2 characters.** The spec caps it at two because a
   feature has dozens of vendors and a fixed-width parse. This pipeline has **four approved models**,
   and `seedance` beats `sd` every time a human reads a folder. Field position kept, width dropped.
2. **The brand is 2–8 characters, not exactly 4.** The spec's 4 is a legacy-system constraint that
   does not apply here; `brandco` should not become `bran`.
3. **No `<frame-number>` and no `<camera-reference>` fields.** Both exist for image sequences (DPX/EXR)
   and multi-camera shoots. This pipeline emits single files and has one virtual camera. Carrying
   empty fields would be the cargo cult.

**And one exception, for the deliverable only:** a delivered master has no sequence and no shot, so
`acme-01007_master_v001_9x16.mp4` omits both. The client is the audience for that filename, not a
pipeline.

#### The human name and the file name are allowed to differ

`acme-01007` is fixed-width and unambiguous to a parser, and slightly hostile to read. That is the
spec's trade and it is the right one — **so the human-facing label is different on purpose**: the
registry, the ClickUp task and the conversation all say **`ACME S01E007`**. Film works this way too;
the file says `abcd-01007` and the people say "season one, episode seven." ⛔ Only one of them is the
key: **the filename is.**

#### The four identifiers — and which may never change

| ID | Shape | Example | Allocated | Mutable? |
|---|---|---|---|---|
| **Show ID** | `<brand>-<SS><EEE>` | `acme-01007` | `EPISODES.md`, when the episode is planned | ⛔ **Never.** The creative primary key |
| **Batch ID** | `B<YYYY-MM><LETTER>` | `B2026-09A` | `series_batch.py init` | Fixed for the batch's life |
| **Shot ID** | `<seq>_<NNNN>` | `s1_0020` | The shotlist, in tens | Scoped by the show ID; gaps are for inserts |
| **Ad-name join key** | `<BRAND>-<body>-<hook>-<persona>-<variant>` | `ACME-B2-H07-P1-a` | `batch_plan.py`, at plan time | ⛔ **Never rename a live ad** — renames orphan history |

⛔ **The show ID and the ad name are deliberately DIFFERENT keys and merging them breaks both.** The
ad name is a media-side key that cannot change once live; the show ID is assigned before any ad
exists. This mirrors real practice — the advertising industry's own identifier, **Ad-ID** (4 A's +
ANA; replaced ISCI as the official standard in 2003, ISCI formally withdrawn 2007), is an
**issued, registered code**, not something a producer composes `[SECONDARY · encyclopaedic, read
2026-08-30]`. **`EPISODES.md` is the only place the two keys meet**, which is why "which episode was
this ad?" is a registry lookup and not a string parse (`performance-metrics.md` §2).

#### The folder

```
<production-root>/<showid>-<slug>/        e.g.  acme-01007-primar-comuna/
```

The `00-brief … 10-export / 99-costs` layout inside is unchanged.

⛔ **Do not rename existing folders.** `Proiect-Video-<N>-<SLUG>` and anything named under the
short-lived `ACME-S01E07_…` shape both stay exactly as they are — a rename breaks every ClickUp link,
manifest path and cost record pointing at them. Put the old name in the registry's **Aliases** column
and use the canonical ID for everything new. `scripts/name_lint.py` flags legacy names with the fix
attached; it never renames anything.

#### Two rules that are about scale, not format

- **One token vocabulary per brand, defined once in the profile** — subjects, models, sequence codes.
  Used identically by filenames, `SHOTS-<SLUG>.json` and the batch state. A token that means two
  things means nothing.
- **⛔ Never rename a shipped asset.** A new name is a new row (`shot_manifest.py add --retake-of`),
  never an edit to an old one — the same discipline as the ad name, for the same reason.

#### Reference files are named for what they FIX

`_reference/` is the exception to the shot-prefix rule, because it holds inputs you did not generate
and the question you ask of them is "what attribute does this pin?", not "which shot was it":

```
<attribute>-<what-it-fixes>_<source>.<ext>     light-key-ratio-4to1_pexels-1183.jpg
                                               wardrobe-jacket-3qtr_client-supplied.png
```

⛔ **A series-level `_reference/` set lives in `_series/<BRAND>/_reference/`, not in an episode**, and
is what every branch of a batch generates from. An episode's own `_reference/` holds only what is
specific to that episode. Copying the series set into an episode folder is how two branches end up
locked to two different "locked" references (`series-parallel.md` §2).

- **Scripts & prompts** also get a copy in this skill's `script-archive/`; the final script is
  pasted into the 📋 subtask. **The final export** attaches to the 📤 subtask. The board is the
  index of truth; the folder is the file-of-record.
- **`99-costs/COSTS-<SLUG>.md`** holds the `estimate_duration.py` budget and, after production, the
  actual credits spent — that's how the per-video envelope and the monthly ceiling stay honest.
  Reconcile it against what Higgsfield actually settled, don't just trust the preflight numbers it
  was built from: `scripts/reconcile_costs.py --transactions tx.json --ledger-total <N>` diffs a
  live `mcp__Higgsfield__transactions` export against the logged total (with an optional
  `--balance-before`/`--balance-after` sanity check) and flags the delta — it found a real ~15cr
  overstatement doing this by hand once already. It doesn't auto-attribute the delta to one line
  item; that comparison still needs a human eye on both lists.

## The ledger — one record per video, and the index across all of them

⛔ **Until 2026-09-08 this skill had a rigorous per-video quality gate and no production tracker.**
Every question a producer asks mid-month was unanswerable without walking folders by hand, and one
of them was not a convenience question at all: *"this claim turned out to be wrong — which shipped
videos contain it?"* had **no mechanism**. `claims_lint.py` ran at approve-script, printed, and was
forgotten; `--allow` was a command-line flag that left no trace of who approved what; and
`script-archive/`, the only cross-video corpus, was empty because populating it was a convention
with no tool. At two or three videos a month that is survivable. At thirty to fifty it is a recall
problem with a lawyer attached.

`scripts/ledger.py` closes it, with one machine-readable record per video at
`00-brief/RECORD.json` inside the job folder.

**The design rule, and it comes from this skill's own failures: state that needs a second command
stops being written.** `shot_manifest.py add`, `qa_log.py`, `EPISODES.md`, the hook bank and
`COSTS-*.md` are all manual, and every one of them goes quiet under load. So the record **derives**
everything it can from artifacts the gate already forces to exist — CHECKPOINT.md, APPROVALS.md,
QA-LOG.md, the shot manifest — and `gate.py` writes it itself on `open`, every `approve`, and
`close`. Delete the record and `sync` rebuilds it. Only two things are authored, because no
artifact implies them:

| Authored | Why it cannot be derived |
|---|---|
| **Identity** — `ad_name`, persona, hook, body, cta, tone, batch, platforms | The job folder carries none of it. `batch_plan.py --out` writes the matrix that supplies it; `ledger.py set` puts it on the video |
| **Terminal facts** — `kill`, `deliver`, `signoff`, `note --blocked` | Nothing on disk means "the client said no". A killed script used to leave **no trace anywhere** — not in the approvals ledger (append-only positives), not in `script-archive/` (finals only). It just vanished |

**The commands, in the order a month uses them:**

```
python3 scripts/batch_plan.py … --out 00-batch/BATCH-<BRAND>-<YYYY-MM>.json
python3 scripts/ledger.py set <job> --ad-name … --persona P1 --hook H05 --platform tiktok
python3 scripts/ledger.py index <production-root> --client <brand> --month 2026-09
python3 scripts/ledger.py kill <job> --by "Dana" --why "client killed the angle"
python3 scripts/ledger.py note <job> --by "Dana" --why "waiting on the claims sheet" --blocked
python3 scripts/ledger.py deliver <job> --by "Dana" --platform tiktok --url …
python3 scripts/ledger.py find <production-root> --claim "clinically proven"     # ⛔ RECALL
```

⛔ **`ledger.py find` is the one that matters most, and it only works because the corpus fills
itself.** At `gate.py approve script` the approved text is copied into
`script-archive/<client>/<job>-<sha12>.md` — named by content hash, so re-approving is a no-op and a
revision files a second copy rather than overwriting the one that shipped. `find` searches the
records *and* the archive, reports **how many of each it searched**, flags any hit whose state is
`delivered` or `signed-off` as *this one shipped*, and — per the SILENT PASS rule
(`self-evolution.md` §6b) — returns **INCONCLUSIVE, not clean**, when the corpus is empty.

⚠ **What the recall cannot tell you, and this is not a small caveat.** It searches *approved
scripts*. A claim added in the edit, improvised in a VO take, or burned into an overlay is not in the
corpus. Three more holes, all of which were live false negatives until an adversarial read found
them on 2026-09-08 and all of which now have a pinned test: a claim **wrapped across a line break**
(the query normalises whitespace now), a job folder under a `_`-prefixed directory such as this
skill's own `_series/` (the walk pruned them and still printed a confident denominator), and a
**non-UTF-8 file** — a script saved by Word — which crashed the query into the same exit code it
uses for "no match". The query now reports how many records and archived scripts it searched, names
any directory it skipped, and returns **INCONCLUSIVE rather than clean** when any record points at
an archived script that is missing. The audio-text lock (`clients/<brand>.md` §0 item 2) is what makes the script a truthful
proxy for the delivered file — in a claims-sensitive category that lock is the thing that makes the
recall query meaningful, which is a second reason to insist on it.

**`ledger.py index` prints its own gaps rather than a clean-looking table**: how many videos carry no
shot manifest (lineage unrecorded), no ad-name join key (performance data cannot be joined), and no
claims record (invisible to recall). A row count with silent holes in it is the kind of report that
gets trusted and should not be.

**`--allow` now exists on `gate.py approve`** and is recorded with the approver's name.
Before this it was named in the gate's own refusal message and **was not a flag at all**, so a phrase
the client had approved in writing could never pass — an instruction that cannot be followed, which
teaches people to reach for `CINE_GATE=off`.

---

## The shot manifest — lineage for every generated asset

The naming convention says *what* a file is; the manifest says **where it came from**. One
`SHOTS-<SLUG>.json` (or `.csv`) per project, one row per generated asset, written at generation time
— not reconstructed later:

```
shot_id · kind (dialogue/reaction/insert/broll/frame) · file · model + version/date · prompt (or
prompt file+hash) · seed (if exposed) · start_frame file · vo file · resolution · duration ·
cost_credits · qa_status (pending/pass/retake/select/backup) · retake_of (shot_id) · notes
```

`scripts/shot_manifest.py` is the tool: `init` creates it, `add` appends a row (a regeneration is a
NEW row with `--retake-of` — which makes the retake counter and the one-variable rule auditable),
`status` records QA/selects verdicts, `validate` fails loudly on missing files or broken retake
chains, and **`report` turns the rows into measured cost actuals per shot type** — the numbers that
calibrate the estimate and the quote.

Why it earns its keep at volume: **reproducibility** ("make it like the last one" needs the exact
payload that made the last one), **drift diagnosis** (when quality shifts, the manifest says whether
the model version changed or your prompt did), **retake discipline** (the one-variable rule is
auditable), **cost actuals per shot type** (the retake-economics table in `ai-generation.md` is built
from these rows), and **the selects pass** (`direction.md` §4) records its verdicts in `qa_status`
instead of in someone's memory. The ledger (`99-costs/`) reconciles money; the manifest reconciles
*provenance*. Keep both.

## Client approval — two gates, bounded rounds, priced changes

At one video a month, revision chaos is annoying; at volume it is the margin. The loop is part of
the pipeline, not an interruption of it:

- **Gate 1 — script + storyboard sign-off** (after Stage 2). The client approves words, scenes, and
  the shotlist **before generation spends anything**. After this gate, a wording change is a
  change-order, priced honestly: it cascades through VO re-record → clip regeneration → re-edit, and
  the price of "one small line change" is that cascade, not the minute it takes to type.
- **Gate 2 — cut review** (after Stage 6). Deliver a review cut: low-res, watermarked, **visible
  timecode**. Notes come back **timecode-referenced**, one round. A second round is scoped to the
  first round's items; a third is a change-order. **How the round actually runs — the platform
  choice, the share setup, and the marker bridge back into Resolve — is
  `references/review-and-approval.md`.**
- **Sign-off must be producible on demand.** No review platform gives you an approval action —
  Frame.io has none, in the UI or the API (`review-and-approval.md` §2) — so the house convention is
  **a top-level comment reading `APPROVED` on the latest version, from a named reviewer**, never a
  reply, an emoji, or a "looks great" in chat. Export the comment log to `09-qa/review/` at sign-off.
  A sign-off you cannot produce later did not happen, and the silence rule below only works if
  "the last approved version" is something you can point at.
- **Map every note to its cost class before agreeing to it:** *edit-only* (trim, reorder, music
  level — minutes) · *audio-only* (re-record a line, remix — cheap, but a re-recorded line on an
  audio-driven clip forces that clip's regeneration too) · *regeneration* (a new take — credits per
  the retake tree) · *script change* (back through Gate 1). Saying "that note is a regeneration, not
  a trim" out loud, with the cost, is most of what a producer does.
- **Silence rule for unattended cadences:** state the review window in the handoff note ("notes by
  Thursday, else this version ships Friday") — a volume cadence cannot block on an absent reviewer.

## Calendar, capacity and contingency (volume accounts)

- **Batch by reuse, not by deadline.** Group the week's generation by persona/setting/character so
  start frames, Elements and blocking cards amortise; context-switching between brands per-clip is
  the hidden throughput killer.
- **Forecast credits weekly against actuals** (the manifest supplies actuals) and hold **~20%
  contingency** — retakes are not an exception, they are a line item.
- **Know the throughput ceiling and plan at 70–80% of it.** The gates (QA card, selects, compliance,
  captions) have a fixed human cost per video; find the honest number of videos/day the operator can
  gate *well* — from ClickUp time-in-status on finished videos, not from vibes — then book **70–80%**
  of it. A month planned at 100% fails at 85%: retakes, late notes and platform hiccups are not
  exceptions, they are the schedule.

### The capacity arithmetic — and why the modular system is not optional

**Measured: a from-scratch 40–60s video takes 6–7 hours** end to end — script through delivery,
gates included. That number is the operator's own, from doing the work, and it is the only capacity
figure in this skill that is not an estimate.

Run it forward and the volume promise collapses if every video is built from scratch:
**40 × 6.5h ≈ 260 hours a month**, against roughly 120–130 productive hours for one person at the
70–80% planning rule. **A 30–50/month commitment is undeliverable as 30–50 separate videos.** Saying
that out loud early is worth more than any efficiency.

What makes it deliverable is that a batch is not N videos, it is **n setups × k variants**:

```
month_hours  =  n_setups × SETUP_HOURS  +  n_variants × VARIANT_HOURS
```

- **SETUP_HOURS ≈ 6.5** [MEASURED] — the first video of a new body/persona/setting: script, reference
  set, start frames, generation, edit, captions, QC, delivery.
- **VARIANT_HOURS = ?** [**UNMEASURED — the single most important number in this skill**] — the same
  body and setup with a new hook: new opening lines, one or two new start frames and clips, re-cut
  head, re-caption, QC. Everything upstream is already approved and reusable.

Worked, at 120 productive hours: 5 setups (32.5h) leaves 87.5h. At a variant cost of 1.5h that is
**58 variants — 63 videos**. At 2.5h it is **35 variants — 40 videos**. At 4h it is **21 variants —
26 videos, and the contract is missed.** The whole commercial question sits in one unmeasured number.

⛔ **So measure `VARIANT_HOURS` on the first batch, before quoting a second month.** Log setup and
variant work as separate ClickUp entries (the board conventions above), and the number arrives for
free. Until then, every capacity figure quoted to a client is **ASSUMED** and goes behind the
verification readout with its range, never as a single confident number.

### The second ceiling: credits, and on the current plan it binds first

Hours are not the only wall. The generation plan caps output independently, and on this account it is
the tighter of the two.

**Measured 2026-08-29** (read off the Generate button, this account, 5s clip at 1080p):

⛔ **Rates are not restated here.** `scripts/rate_card.py table` prints the live matrix; `rate_card.py lookup --model <m> --res <r> --seconds <n>` prices one shot; `compare --seconds <n>` prices it across the roster. The single source is `assets/higgsfield-rates.json` → `rate_table`, measured on the Generate button 2026-09-01.

The capacity ceiling it feeds is unchanged: **credits are a second ceiling alongside hours**, and the cheapest and dearest roster options differ by ~6× at the same duration, so model choice moves the monthly video count by more than any scheduling change.

⛔ **Only `kling3_0`, `minimax_h3` and `seedance_2_5` may be quoted or used** (client lock,
2026-08-29 — `ai-generation.md` § The approved video-model roster). Off-roster rows are removed rather than struck through
so quotes issued before that date remain auditable. **There is no cheaper fallback tier**: if the
budget does not fit the approved roster, the answer is fewer or shorter shots, not a cheaper model.
| **Seedance 2.5** @1080p | **45** | 9.0 | ~376 cr | **~8** |

(8 clips + 8 start frames at 2 cr + VO, before the retake factor.)

**Three pricing rules, verified in the UI 2026-08-29 rather than assumed:**

- **Aspect ratio is free.** 16:9 and 9:16 cost the same, so delivering vertical carries no premium.
- **Duration is exactly linear** — reconfirmed on four models with two readings each (`rate_card.py`). So **quote in
  credits per second, never per clip**: clip length changes cost proportionally and nothing else does.
- **Resolution is the only real lever, and its tiers are not proportional.** Seedance 2.5 costs 3.6×
  more at 1080p than at 480p; Kling 3.0 costs only 1.14× more at 1080p than at 720p but 3× at 4K.
  Dropping one tier is the cheapest capacity you can buy — but check it against the client's format
  lock before spending the saving (`delivery-format.md`).
- ⛔ **Bitrate is untested.** A Standard/High control exists on the Seedance models and the figures
  above are at High. Test it before assuming the setting is free.

**The model choice moves the month's ceiling by ~4×.** Seedance 2.5 cannot deliver 30–50 videos a
month on a 3,000-credit plan at any hour count — it tops out around eight. Kling 3.0 gets you into
the low thirties before retakes. That is not a preference, it is arithmetic, and it belongs in the
conversation *before* a volume commitment is signed, alongside the hours model above.

⛔ **Two things that change this materially, both checked per batch:**

- **Free generations and unlimited windows are plan features, and they are browser-only.** The
  platform states plainly that unlimited models and free generations "are accessible only via
  higgsfield.ai and are not accessible on MCP/CLI" — so **a scripted pipeline pays cash for what the
  browser gets free.** If a month is credit-bound, that is an argument for generating by hand in the
  UI, and it is the one place where automation costs money rather than saving it.
- **Published pricing is not your pricing.** Two of the models this pipeline uses are absent from the
  public rate card, and the two that appear on it were understated by ~45% against what the app
  actually charges. Preflight in the UI; see `scripts/refresh_costs.md`.

Two consequences worth stating, because they change how the work is designed:

1. **Variant cost, not setup cost, is the business.** Effort spent making a setup more reusable — a
   locked reference set, an approved presenter, a clean body register — buys back hours on every
   variant after it. Effort spent shaving the setup buys hours once.
2. **A batch matrix with many distinct settings and personas is a batch of setups wearing variant
   clothing.** `batch_plan.py --hours` now counts distinct setups in the matrix and prices the month;
   if the plan reads as 30 setups, the variance rule is being satisfied by brute force and the month
   will not close. Fix it at the plan, where it costs nothing.
- **Mark the stretch rows in the batch matrix** — know which videos get cut *before* the week you
  have to cut them, so a slip degrades gracefully instead of at random.
- **Carry over honestly.** A row that slipped into next week gets a one-line *why* before it is
  re-committed; a row that slips twice for the same reason will slip a third time — change the
  approach (different presenter strategy, simpler coverage, or kill the row), don't re-book it.
- **One overflow day per cycle** for re-renders, platform hiccups and the note that arrives late.
- **Platform contingency, decided in advance:** the fallback model per role (dialogue / B-roll /
  frames) named in the client profile; an outage note ready to send ("this week's batch slips N days
  — platform issue, not production"); and the manifest's model-version column watched so a silent
  model update is caught at the first drifted clip, not at episode four.

### What the micro-budget literature says about that number — and what it does not

⛔ **The negative result first, because it is the useful part.** The strongest available source on
one-person production — a Routledge book by a director who shot one feature single-handed over five
years and made an award-winning one for about $2,000 cash [PRIMARY · Mahaffy, *Micro-Budget Methods
of Cinematic Storytelling* — via a local extraction, read 2026-08-29] — **contains no
hours-per-video figure, no setup-versus-variant ratio, and no batch-reuse measurement of any kind.**
It disclaims scheduling and budgeting deliberately; it is a craft-and-philosophy text. So
`VARIANT_HOURS` stays [UNMEASURED] and the instruction above is unchanged: **measure it on the first
batch.** No reading substitutes for that, and a number borrowed from a book that does not have one
would be worse than the honest blank.

What the same book does supply is three rules that change how the hours get *spent*:

1. **Concentrate the budget; never average it.** The organizing equation is *effect − effort =
   value*, and the named failure is "stretching yourself thin pulling ordinary value from too many
   inadequate compromises" — the recommended move is to subtract catastrophically from one area to
   fund another. Applied here: the ~20% credit contingency and the retake budget are **not spread
   evenly across the shot list.** Decide at the plan which one or two shots carry the video and let
   the rest be adequate — a batch where every shot got a second pass is a batch where nothing got a
   third.
2. **Match the piece to the schedule at the plan, not at the deadline.** The micro-budget move is to
   build the story out of the resources that actually exist rather than script first and absorb
   compromises during production. That is the same argument `batch_plan.py --hours` makes
   arithmetically, and it is why stretch rows are marked in the plan: the cheapest place to lose a
   video is the one where it has not been made yet.
3. **A failure is a design brief before it is a re-roll.** "The obstacle holds the solution" — the
   dropped prop gets absorbed into the scene rather than reshot. Applied to generation: when a clip
   fails the QA card for something the model will not fix, the first branch of the retake tree
   (`ai-generation.md` → Retake economics) is **rewrite the beat around what the model actually
   produced**, not spend the same credits again on the same prompt hoping for a luckier sample.

**A disagreement to keep rather than smooth over.** Mahaffy treats coverage as expensive and largely
wasteful — he argues for a planned continuous take plus one reverse, near a 1:1 ratio — where
conventional shot-design practice (Katz, via `craft-cheatsheet.md`) treats master-plus-coverage as
the safe default. This skill sits on the coverage side and says so twice: editorial handles generated
past the cut, and ≥1 B-roll per dialogue line with two more available. **Both positions are right
about their own binding constraint.** Coverage buys editorial freedom with shooting time; Mahaffy
optimises for the end of the spectrum where shooting time is the scarce thing. Here the scarce thing
is neither — it is **credits and gate time** — which is why the skill keeps coverage but caps it. The
honest consequence: **the extra B-roll is the first thing to cut when the month is tight**, and
cutting it is a Mahaffy-shaped decision rather than a failure of the standard.

**A corrective on the expectation, from the AI side.** The 2023–24 wave of production-economics
claims (whole crews replaced, campaigns compressed from 6–8 weeks to 2–3) over-promised, and by 2025
the consensus had moderated to: generative AI compresses **some** tasks dramatically, others
marginally, and **adds cost categories that did not exist before — prompt engineering, reference and
model setup, and output curation** [SECONDARY · Hutson & Smith, *Cinematic Algorithms* — via a local
extraction, read 2026-08-29]. That is precisely where the measured 6–7 hours goes, and it is the
sentence to have ready when a client's mental model is "AI makes it instant": the saving is real,
and it is not where people assume it is.

## Delivery — handing the finished files over

**Review and delivery are different acts and must not share a surface.** A review link carries
watermarked, timecoded, sometimes unfinished cuts; a delivery folder carries the masters. Conflating
them is how a client grabs a watermarked review cut and runs it as an ad — which has happened to
enough shops to be a convention rather than a worry. Keep them separate on purpose.

**The master of record is always `10-export/` on your own disk.** No review platform, no client
drive, no cloud tool is the archive — plan-lapse behaviour is undocumented on every one of them
(`review-and-approval.md` §8), and a client who leaves takes their storage with them.

**The default hand-off is a shared Drive folder**, unless the client's profile says otherwise. It
wins for unexciting reasons that matter at volume: the client already has an account, folders are
durable and re-shareable without you being present, and the whole step is automatable from a session
with the Drive connector attached. The alternatives, and when they are right: the **client's own
system** (their Drive, their SharePoint, their DAM) whenever they have one — you are a guest, use
it; **ClickUp attachments** when the deliverable is small and genuinely belongs to a task's history;
**a review-platform download link** only when the client insists, and then with downloads explicitly
enabled on the approved version and nothing else. ⛔ **Never WeTransfer or any expiring link** for a
master — the deliverable outlives the link and you will be re-uploading it in six months.

**The shape that survives 30–50 videos a month:**

```
<Client> — Video deliverables/
├── 2026-08/                      one folder per drop, never one per video
│   ├── ACME-B2-H07-P1-a_9x16.mp4                      the ad-name join key IS the filename
│   ├── ACME-B2-H07-P1-a_1x1.mp4                       format token per delivery-formats.json
│   └── DELIVERY-2026-08.md              the manifest below
└── 2026-07/
```

The filename is the **ad-name join key** (`performance-metrics.md` §2) plus the format token. That
single convention means the delivered file, the platform ad name, the hook-bank row, the shot
manifest and the approval all name the same object — and a client asking "which one was the
skeptic hook?" is answerable without opening anything.

**Every drop ships with a delivery manifest** (`DELIVERY-<YYYY-MM>.md`) — one row per file: filename,
format preset, duration, measured loudness, the version approved, and who approved it. It takes two
minutes, it is the thing that ends "is this the final one?" threads, and it is the evidence half of
`review-and-approval.md` §2 in a form the client can read.

**Then close the loop on the board:** milestone time entry (never a live timer), a comment carrying
the folder link and the manifest, and the ClickUp status moved. A delivery that is not on the board
did not happen, because next month's capacity plan reads the board, not your memory.

## Definition of Done — the ✅ Branding Check gate

A real gate, not a checkbox. The exact items are the **profile's non-negotiables** plus:
every claim accurate & approved (run `references/compliance.md` in a claims-sensitive category) ·
characters and product on-model & consistent · captions correct language & mobile-legible · any
required disclosure burnt in · in-frame brand marks real and undistorted · music and archive footage
licensed for **this** use (organic ≠ paid) · **matches the client's delivery format** (aspect,
resolution, fps, duration window, loudness — `export_qc.py --format <preset>` PASS) · credit spend
within envelope. If anything fails, bounce it
back to the owning subtask rather than waving it through.

## Growth & throughput add-ons (optional, verified 2026)

Fold these in when a client wants volume/consistency (see `evals/` (retired 2026-08-30)):

- **🪝 Hook Variants (optional Stage 1.5).** Produce 2–3 hook variants and A/B them (winner by
  3-second retention becomes the locked opener for all cuts). Cheap — edit-stage, reusing generated
  B-roll. *(For locked-audio clients: vary only the opening B-roll, never a spoken line.)* At volume this
  stops being optional — see `modes/ugc-volume.md` §5 for the hook bank and the variant math.
- **♻️ Repurposed Cuts (optional Stage 6.5).** One shoot → many posts: the 60s hero, a 15–20s teaser
  (S1+S2), 2–3 character shorts (7–10s), a voiced fact-card, an alternate-hook cut. ~5% extra cost
  each (VO/edit only) and multiplies posting volume without multiplying generation credits.
  *(Locked-audio clients: re-cut existing footage reusing the original VO segments unchanged.)*
- ⛔ **Not every video gets a review round.** At 2–3 a day a per-video approval is structurally
  impossible and produces an approval record that is fiction. The tiering — Standing / Batch / Named,
  driven by the INVARIANT/VARIANT split — is `review-and-approval.md` §10, and the timebox only works
  if a **deemed-approval clause is in the contract**.
- ⛔ **VARIANT_HOURS now has a proposed value, and it is still not measured.**
  `production-runbook.md` budgets **4 h 45 m** for a 20–40s variant on a locked brand, against the
  **6.5 h measured** setup. Quote the setup figure until `stage_timer.py` has logged a few videos;
  the runbook's number is a design, and a capacity quote built on it would be a guess wearing a
  decimal point.
- ⛔ **A recurring series has a layer above the project.** The folders below run *one video*. The
  series that contains it — the bible, the INVARIANT/VARIANT/DRIFT split, the episode registry, the
  decision records and the hooks already used — lives in `_series/<BRAND>/` and is governed by
  `series-continuity.md`. **Register the episode when it ships, with the invariants version it was
  made under**; without that column a later bible edit silently reclassifies every past episode.
- **Per-shot QA gate (between stages, not just the final ✅ Branding Check).** The full card is
  `references/realism-qa.md` §6 — on-model vs hero reference · face/mouth in safe zone · eyeline and
  gaze consistent · at least one natural blink · lighting Kelvin matches grade · no text/logo drift ·
  **duration fits the line via `ffprobe`, with any seconds past it carrying a designed aftermath —
  ⛔ NOT an editorial handle, which on an audio-driven clip produces lips still moving after the
  line** (`shot-handoff.md` §1) · **no clipping/interpenetration at
  any contact point, sampled across several frames of the clip, not just the thumbnail**
  (`ai-generation.md` → "Known failure guardrails") · **and lipsync verified by listening to an A/B
  with the VO over picture, never from a contact sheet** — a frame grid shows the speech *window*, not
  the articulation, which is exactly how three bad clips passed on one project. Clips land in
  `03-clips/_review/` and move to `03-clips/` only when the card passes — catches drift/lipsync/morph
  when they're cheapest to fix, not after every credit is spent. **Re-run this gate on every
  regeneration, not just the first pass** — a prompt fix for a known artifact is a hypothesis until
  a frame-by-frame check confirms it.
- **Release calendar & cadence.** Consistency beats sporadic virality: a steady **2–4 posts/week**
  from the one handle (quality-gated — skip a slot rather than ship weak) trains the algorithm. Add a
  rolling 4-week calendar list (Concept→Script→Gen→Edit→Scheduled→Posted→Reviewed) as the parent of
  the per-video tasks.
- **Throughput tooling (bigger builds).** A **prompt factory** (final script → shotlist + MASTER
  prompts + per-shot subtasks, deterministically, with a lint gate) and a **generation lane runner**
  (parallel frames/dialogue/B-roll queues + a cheap draft lane) cut the re-keying and serial waiting
  that drive rework. Scope these as `scripts/` additions when volume justifies it.
- **Auto-assemble the edit with the MCP inside DaVinci Resolve Studio 21.1** (`run_script`, gated by
  `gate.py`): import the filed clips → build the timeline in scene order → `resolve-production-console.py`
  (lanes + beat markers, read back) → planned dissolves (`AddTransition`) → `render-mp4.py` queues the
  render — so the editor opens Resolve ~80% assembled and only does the taste pass. (`build_fcpxml.py`
  is the interchange fallback.) Setup and hazards in `references/environments.md` §3; the step-by-step
  in `references/editing-and-audio.md`.

## Cadence & onboarding

Keep statuses current (the account lead reads the board, not your inbox); log assumptions when a
brief was thin. To onboard a new contractor, point them in order: `SKILL.md` (the mode router) →
the relevant `modes/<mode>.md` → `clients/<brand>.md` (who/what/tone/locks) → `script-format.md`
(write a script from a one-line brief) → this file (the board) → `craft-cheatsheet.md` +
`ai-generation.md` (make it look good, on budget) → `realism-qa.md` + `compliance.md` (the two gates). Have them draft a
script for a sample brief and run it through the DoD checklist before touching production.
