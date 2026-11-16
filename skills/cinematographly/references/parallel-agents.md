# Parallel agents — fan-out inside a stage

**Owner:** the producer, acting as the dispatcher · **Frequency:** every stage that has independent units ·
**Applies to:** every job, N = 1 included.

**When to read this:** a stage has more than one independent unit of work: several research questions, several
script drafts or critique axes, several scenes of shot prompts, several takes to review, several scenes to
compare, several scenes to spot for sound.

**Sibling files:**
- `series-parallel.md` owns parallelism **across episodes**: the batch, the freeze, the join and Amdahl's ceiling.
- This file owns parallelism **inside a stage**: the plugin's own agents, run side by side in fresh contexts while
  the main session dispatches and merges.
- The two compose. A series batch can fan out its review stage per take, and a single video gets this file's
  speed-up without any batch.

Author, 2026-11-05: *"This massive plugin, needs to use parallel agents for many of it's tasks when possible."*
The design follows common agent-orchestration patterns: fan-out / fan-in with a named dispatcher, file-based state hand-off, and an independent audit at each gate.

---

## 0. ⛔ What never runs in parallel

Parallelise reads and drafts. Single-thread every write that reaches outside the job folder, and every decision.
*"Parallelize reads in sub-contexts; single-thread writes in the parent"* [a principle published by Cognition].
These stay in the main session, one at a time:

| Never in an agent | Why |
|---|---|
| Any generation or spend: Higgsfield, Kling, ElevenLabs or any other paid call | Spend needs the owner's approval in chat, and `gate.py` decides each call. The batch tools already run N generations in one call |
| `gate.py open`, `approve`, `allow`, `log-external` | An approval quotes the owner's words from this conversation, and an agent has no conversation |
| DaVinci Resolve: the scripting API or computer control | One application and one timeline. Rule 8 work is GUI, and a GUI has one mouse |
| The browser: Chrome capture, logins, a course site or any site | One browser profile, the owner's sign-ins, and throttling on the course host |
| Questions to the owner | An agent returns its question to the dispatcher, who asks once, batched |
| Edits to shared files: `CHECKPOINT.md`, the scene files and `_PROJECT.dna.md`, manifests, `QA-LOG.md`, the ledger | One writer per file. Agents write only the paths they are given |
| Git, release and anything on the owner's computer outside the job | Same reason |

A stage made of these rows does not fan out: edit, mix, grade, titles, delivery. Amdahl's ceiling in
`series-parallel.md` §1.3 still binds. The serial edit is the floor, and agents shrink the stages around it.

---

## 1. The shape: one dispatcher, fixed units, one join

- **The main session is the dispatcher** [*Fan-out / fan-in with named
  dispatcher*]. It splits the stage into units, launches one agent per unit **in one message** so they run
  side by side, waits, merges, and owns the result. No agent launches another.
- **The plan is made first, and the units are known at dispatch.** This is *plan-first parallelisation*. It is a pipeline with a fan-out step, not an
  Orchestrator deciding at run time (a premature orchestrator; an architecture without validation).
- **Silence is a FAIL.** Every unit has an output path before it is launched. After the join, `fanout.py check`
  confirms each one exists and carries its typed header. A unit with no file failed, whatever the agent's reply
  said. That reply is a hypothesis, not evidence [unreliable self-report].
- **Independence where it is the point.** Draft writers do not see each other's drafts. Independence is what makes
  several drafts worth more than one (voting needs independence). Critics review one axis each and do not
  see the other critics' findings [A17 *Applicability-gated reviewer panel*].
- **The reviewer is not the writer.** Reviewers run on `sonnet` while writers inherit the main model. When the main
  model is Opus, a different model family judges the work [*Judge collusion*]. When the main session itself
  runs on Sonnet, the split does not hold: say so in the stage report. Reviewer tools are read-only (Read,
  Grep, Glob) by allowlist, not by instruction. Tool absence is the hard scope [*Tool allowlist leak*].
- **The parent verifies with the plugin's scripts.** Shot prompts are re-linted by `prompt_lint.py --scene` after
  the join. Take verdicts sit beside `clip_qa.py` and `motion_qa.py` numbers. Every QA verdict reaches
  `QA-LOG.md` only through `qa_log.py`, written by the parent with the agent's report as the observation. An agent
  never logs its own pass (an independent audit).

---

## 2. The agents

They live in the plugin's `agents/` folder. A host that namespaces plugin agents lists them as
`cinematography:<name>`.

| Agent | Archetype | Tools | Model | One unit is | Writes |
|---|---|---|---|---|---|
| `cine-researcher` | A6 Analyzer (with Write for its notes) | Read, Grep, Glob, WebSearch, WebFetch, Write | sonnet | one question, one source, one film or one course note | its note file |
| `cine-draft-writer` | Generator, independent | Read, Grep, Glob, Write | inherit | one concept, hook set or full script draft, on an assigned angle | its draft file |
| `cine-script-critic` | A1 Reviewer, one axis (A17 panel member) | Read, Grep, Glob | sonnet | one draft × one axis: logic · coverage · continuity · timing · hook · claims · voice (v2.67.0) | nothing; returns its report |
| `cine-cold-reader` | A1 Reviewer, blind (v2.67.0) | Read, Write | sonnet | one script file and nothing else: what it is for, who speaks, what the hook asks, what the ending answers, whether a line tries to be funny | its cold-read file, then the parent runs `develop.py stamp` |
| `cine-shot-writer` | Generator with a self-check (lint loop) | Read, Grep, Glob, Write, Edit, Bash (the one shell: its lint loop) | inherit | one scene's shot prompt files | the shot prompts its `--writes` names |
| `cine-take-reviewer` | A5 Specialist (auditor), vision | Read, Grep, Glob | sonnet | one take: its contact sheet and QA numbers against its shot's function, and (v2.70.0) against the approved character and prop sheets and the permanence strip | nothing; returns its report, with `identity: held / drifted / unknown` |
| `cine-scene-continuity` | A5 Specialist (auditor), vision | Read, Grep, Glob | sonnet | one scene: every shot side by side against the scene's sheets (`review-and-approval.md` §11) | nothing; returns its report |
| `cine-sfx-spotter` | A6 Analyzer (with Write for its proposal) | Read, Grep, Glob, Write | sonnet | one scene or segment of the cut: events, frames, starting levels, rooms | its spotting proposal |

**One shell.** Bash is unrestricted once granted, so a rule in prose is not a scope. Only the shot writer
holds it, for its own `prompt_lint.py` loop; `fanout.py agents` fails any other agent that lists it. Every other
agent's measuring is run by the dispatcher before or after the round.

**Seven, not more, for v0.1**. Each takes over work the main session already did one unit at a time, so
the stage table and the gates are unchanged [the strangler-fig pattern: split one capability at a time behind the same
front door]. A new agent lands when a stage's timing shows the need (`stage_timer.py`), not because an archetype
exists.

**When the host does not list plugin agents** (an older client, or a host that loads skills only), dispatch a
`general-purpose` agent whose prompt starts with: *"Read `<plugin>/agents/<name>.md` and act as that agent, and
only as that agent. Your unit: …"*. The tool allowlist is then **not** enforced. Say so in the stage report, and
check after the join that no file outside the unit's paths changed.

---

## 3. Where each stage fans out

Stages are `SKILL.md` §2's rows.

| Stage | Unit | Agent | The parent's join | The parent's check |
|---|---|---|---|---|
| 1 Development: research | one question from the brief's research tier (`preproduction-research.md`) | `cine-researcher` | one research note in `00-brief/`, each claim with its source and tag | sources open; a claim with no source is cut |
| 1 Development: divergence | one angle each (3–6 angles; each of the person's seeds is one angle, v2.65.0); every brief carries a copy of their Taste and Their material | `cine-draft-writer` (concepts) | the kill rounds in `00-brief/DEVELOPMENT.md` | `develop.py check` |
| 2 Script, passes 1–3 | one draft × one axis | `cine-script-critic` ×3–5 | the next pass's draft, written by the parent | `script_score.py`, `estimate_duration.py`, `claims_lint.py` |
| 2 Script, cold reads (v2.67.0) | one script file: v1 or v2, then each option file | `cine-cold-reader` ×1–3 | shown beside the brief's premise and each option | `develop.py stamp`, then `develop.py check` |
| 2 Script, alternative drafts | one assigned angle | `cine-draft-writer` | pick or merge; the critique between drafts | `develop.py check` (3+ versions, a critique between each) |
| 4 References | one film, one shot study, or one reference cut | `cine-researcher` | the reference library rows | rights and source recorded |
| 7 Clip prompts | one scene | `cine-shot-writer` | — the files are the join | `prompt_lint.py --scene <S>` for every scene, then preflight |
| 5 / 7 Before any approval request | one scene | `cine-scene-continuity` | the approval request's "what was compared" list | the owner reads the board; the agent's table is the evidence |
| 8 Selects and QA | one take | `cine-take-reviewer` | `qa_log.py` lines, written by the parent | `clip_qa.py`, `motion_qa.py`, `look_qa.py shots` (first-frame match), contact sheets; the brief names the approved sheets, the permanence strip and any planned costume or prop change |
| 10–12 Sound | one scene or segment (the parent runs `sfx_conform.py events`, then `library sheet <job> <shot>` for each shot's candidate sheet, first) | `cine-sfx-spotter` | one `06-music/SFX-PLACEMENT.json` merged and sorted | `sfx_conform.py levels` on the merged placement; placement in Fairlight by computer control (rule 8) |
| Analysis work (courses, books, films) | one lesson, chapter or film | `cine-researcher` | the adoption table | the table's rows each cite their item |

Stages with no fan-out: intake, boards (one owner conversation), casting decisions, start frames and every
generation (spend), voice, music choice (never picked by the agent), picture lock, edit, mix, grade, titles,
delivery.

---

## 4. The dispatch, step by step

1. **Split.** Name the units. Run `fanout.py plan <job> --stage <stage> --agent <agent> --unit <id> …`. It writes
   `09-qa/fanout/<run>/PLAN.json` and prints each unit's output path. A writer also gets `--writes <glob>`, the
   files it may change besides its report (`{unit}` is filled in per unit), or `--writes-for UNIT=GLOB` for files
   named per unit — one scene's shots: `--writes-for S2='01-script/prompts/S4.clip.prompt.*'`, one per shot (the
   `.ok` sidecar the lint writes is matched by the same glob). The scope check allows only these. A writer's own
   header can list fewer, never more.
2. **Brief each agent with only what its unit needs.** That is the job path, the scripts path (`gate.py where`),
   the unit id, the input files by path (never pasted contents), and its output path. Per-agent context is the
   budget [scalability §19: parallelism × per-agent context = total]. A brief that says "read the whole job" is
   too wide.
3. **Launch the whole round in one message.** Default cap: **6 agents a round** [ASSUMED: past that, the merge
   becomes a skim]. Twelve takes run as two rounds of six.
4. **Record the read-only agents' reports.** A reviewer returns its report instead of writing it. Save each with
   `fanout.py record <job> <run> <unit> --from <file>`, so the evidence is on disk and not only in the
   conversation (`series-parallel.md` §5).
5. **Check the round.** `fanout.py check <job> <run>` confirms every unit has its file with a typed header and an
   allowed verdict, and writes the round's result beside its plan. A missing or malformed unit is re-run once, alone. A second failure
   is done by the parent, by hand, and the stage report says so.
6. **Merge, then verify with the stage's own scripts** (§3, the right-hand column). Only then does anything reach
   the owner or a gate.

**Questions from agents.** Each agent ends with `questions:` in its header when it needs the owner. The dispatcher
collects them across the round and asks once, in one message.

---

## 5. The output contract every agent follows

Every report or file starts with one fenced block that `fanout.py` parses:

````
```fanout
{"unit": "S2", "agent": "cine-scene-continuity", "verdict": "FAIL", "findings": 3, "questions": []}
```
````

Allowed verdicts per agent:

| Agent | Verdicts |
|---|---|
| `cine-researcher` | `DONE` · `PARTIAL` (with the gaps named) |
| `cine-draft-writer` | `DONE` |
| `cine-script-critic` | `PASS` · `FAIL` |
| `cine-cold-reader` | `DONE` |
| `cine-shot-writer` | `LINT-CLEAN` · `LINT-FAIL` |
| `cine-take-reviewer` | `PASS` · `RETAKE` · `HOLD` (v2.70.0: plus `identity`; plan the round with `fanout.py plan … --sheets-sent <units|all>` so the check knows which briefs carried the sheets; `fanout.py check` refuses BAD-IDENTITY: no sheet → unknown, drifted → HOLD unless another CRITICAL/HIGH) |
| `cine-scene-continuity` | `PASS` · `FAIL` · `ASK` |
| `cine-sfx-spotter` | `DONE` · `PARTIAL` |

A JSON output (the spotter's placement proposal) carries the same object as a top-level `"fanout"` key instead,
so the file stays loadable by `sfx_conform.py levels`. The body under the block is the agent's own format (each
agent file gives it). Severity and confidence are
written per finding. When several critics or reviewers report on one artefact, the parent drops findings under
confidence 80 before the owner sees them [*Confidence-threshold filter for parallel panels*], and keeps them
in the run folder.

---

## 6. Failure modes and their guards

| Failure | Signature | Guard |
|---|---|---|
| **Dropped unit** | 6 launched, 5 reported, nobody noticed | `fanout.py check`: silence is a FAIL |
| **Groupthink** | Three "independent" drafts that read the same | Each writer gets a different angle and never sees the others' drafts; the parent's critique names what differs |
| **Self-approval** | An agent's "PASS" lands in `QA-LOG.md` | Only the parent writes `qa_log.py` lines, with the report as the observation |
| **Scope leak** | A reviewer edits a file, or a writer touches another scene | Read-only allowlists. Writers get `--writes` globs. `fanout.py check` snapshots the job's text files at `plan` and fails any change outside the outputs and those globs |
| **Context sprawl** | Each agent re-reads the whole skill | Briefs name files by path; each agent file says what to read and nothing more |
| **Parallel drift** | Two shot writers describe the same room differently | The scene file and `_PROJECT.dna.md` hold the shared text, and writers never edit them (`prompting-craft.md` §12a) |
| **Spend by the back door** | An agent tries a generation tool | No agent has a generation tool, and `gate.py` still gates every call in any context |

---

## 7. What this file cannot tell you

- **How much faster a job gets.** No job has run with these agents yet. `stage_timer.py` on the next job is the
  first number. Until then the honest claim is "the review, prompt and research stages run side by side", not a
  time.
- **Whether `sonnet` catches what the main model misses.** A family split guards against self-preference, not
  against a shared blind spot (voting fixes variance, not bias). A cross-vendor reviewer is the next step if
  the reviews prove too kind.
- **The right round size.** Six is a guess about attention and cost, not a finding.
