# Series parallelism — the fan-out, the join, and what it is actually worth

**Owner:** the producer · **Frequency:** once per series batch (not per video) · **Applies to:** any
brand with a locked series, N ≥ 2 episodes in flight.

**When to read this:** you are making more than one episode. Which, per §0, is the normal case.

**Sibling files:** `production-runbook.md` owns the single-episode route and the stage budget;
`series-continuity.md` owns what may not change across episodes; this file owns *how many episodes
move at once and what stops them colliding*. `parallel-agents.md` (v2.50) owns the fan-out **inside** a stage —
the plugin's agents, one unit each — and composes with this file.

---

## 0. ⛔ The series is the default unit of work. One video is the degenerate case

The skill was written video-first and then grew a series layer on the side. That is backwards for
how the work actually arrives: a brand does not order one video, it orders a run. `series-continuity.md`
already says the bible and the invariants exist before episode 1; `production-runbook.md` §0 already
says the 4–5 hour target only applies **"on a brand whose series is already locked"** — that is a
series precondition wearing a per-video hat.

So the unit is **the batch of episodes**. A single video is that batch with N = 1, and §1 shows it is
the *worst* case for everything below — which is the honest reason single-video work still routes
through the runbook and not through here.

---

## 1. What parallelism is worth — the arithmetic, before the enthusiasm

**The claim to test:** "many of the steps in a series can run in parallel." True. The useful question
is *which*, and what the ceiling is.

### 1.1 The two things that actually shrink

| | Sequential (N episodes, one at a time) | Accumulated (this file) |
|---|---|---|
| **Human sync points** — times a person must return and decide | **3N** | **3** |
| **Machine wait groups** (`jobs_wait` ≤ 12/group; 3 ep × 8 shots × 2 variants) | 12 | 8 |
| **Conversations / context loads** | N | 1 |

The wait-group saving is the ragged remainder — batching 48 images into 4 groups of 12 beats three
separate runs of 2 groups (16 each). Real, but small. **The prize is the sync points: 3N → 3.** A
sync point is not a wait, it is a *human being reloading the whole problem into their head*, and that
is the expensive unit in a one-person shop.

### 1.2 The stage split — what accumulates and what refuses to

| Class | Stages | Behaviour |
|---|---|---|
| **FIXED** — paid once per batch, whatever N is | `route`, the freeze check (§2) | Client profile, mode, invariants version: loaded once |
| **ACCUMULATING** — one base cost plus a small increment per extra episode | `vo`, `frames`, `frame-gate`, `clips`, `selects` | These are the batched ones. The base is the fire-and-wait; the increment is the extra material |
| **PER-EPISODE** — paid in full, N times, and no batching touches them | `script`, `shotplan`, `edit`, `qa`, `deliver` | An episode has its own timeline, its own mix, its own export. There is no such thing as a shared cut |

### 1.3 ⛔ Amdahl's law is the ceiling, and it binds hard here

The classic result: total speedup is bounded by the fraction of work that **cannot** be parallelised
[Gene Amdahl, *Validity of the single processor approach to achieving large scale computing
capabilities*, AFIPS Spring Joint Computer Conference, 1967 — PRIMARY, the origin of the argument].

Against the runbook's 285-minute per-episode budget, the PER-EPISODE class is **160 minutes** —
`script` 30 + `shotplan` 40 + `edit` 55 + `qa` 20 + `deliver` 15. That is **56% of the work, serial
by construction.** Which caps the best possible speedup at about **1.8×**, and only in the limit of
infinite episodes.

**Proposed model** (⛔ every number below is a *proposal*, in exactly the sense of
`production-runbook.md` §0 — reasoned from structure, not measured. `stage_timer.py` is what turns
it into a finding or kills it):

```
TOTAL(N) = FIXED(25) + N x PER_EPISODE(160) + ACCUM_BASE(110) + (N-1) x ACCUM_INCREMENT(52)
```

| N | Sequential | Accumulated | Per episode | vs 285 |
|---|---|---|---|---|
| 1 | 285 | **295** | 295 | ⛔ **worse** |
| 2 | 570 | 507 | 254 | −11% |
| 3 | 855 | 719 | 240 | −16% |
| 5 | 1425 | 1143 | 229 | −20% |
| ∞ | — | — | **212** | −26% (the floor) |

Three things fall out of this table, and they are the whole point of the file:

1. **⛔ Never fan out at N = 1.** The freeze check and the state files cost ~10 minutes and buy
   nothing. One video routes through `production-runbook.md` unchanged.
2. **The floor is 212 minutes per episode — about 3.5 hours — and no amount of batching goes below
   it.** Most of the remaining time is `edit` (55 min), which is one timeline per episode forever.
3. **Therefore the next real speed lever is not more parallelism. It is shrinking `edit` and
   `shotplan`** — the two biggest serial stages. Anyone who answers "we're still slow" with "batch
   harder" has misread Amdahl.

---

## 2. ⛔ The freeze precondition — fan-out before this is fan-out of drift

**The rule: no episode enters a shared batch until `INVARIANTS.md` is frozen and `_reference/` is
locked, and every branch records the invariants version it was cut under.**

Episodes are safely independent for one reason only: **the locked reference image is the lock, not
episode 1's output** (`SKILL.md`, the character block; `prompting-craft.md` §6b). Each branch
generates from the same frozen references, so three branches cannot drift *relative to each other*.

Break the freeze and the property inverts. If the bible is still moving while three branches are in
flight, you have not parallelised production — you have parallelised the drift, and you will find it
at the join, after the credits are spent.

**The check, before any batch is fired:**

- [ ] `series_registry.py check _series/<BRAND>/` exits 0
- [ ] `INVARIANTS.md` declares `invariants-version: N` and nothing is pending in `DECISIONS.md`
- [ ] `_reference/` holds the locked images and one reference carries one attribute
- [ ] Every branch's state file stamps that same version (`series_batch.py` writes it; the join
      refuses a mismatch)

⛔ **A bible edit mid-batch does not silently apply.** It bumps the version, which makes every
in-flight branch stale, which the join reports. That is the correct behaviour and it is why the
version column exists (`series-continuity.md` §6.1).

---

## 3. The accumulator batch, applied across episodes

The runbook's three-batch structure collapses *n* waits into three sync points **within** one
episode. The same discipline one level up is the **accumulator** pattern: append across events, flush
once, rather than processing per event.

```
                 per-episode (today)              accumulated (this file)
A  VO            3 x generate_audio_batch    ->   ONE batch: every line of every episode
B  Start frames  3 x generate_image_batch    ->   ONE batch: every shot x 2 variants, all episodes
   FRAME GATE    3 gates                     ->   ⛔ ONE gate, all episodes side by side
C  Clips         3 x generate_video_batch    ->   ONE batch: every approved frame
```

⛔ `jobs_wait` still takes at most 12 jobs, so each batch splits into groups of ≤12 and is waited on
group by group — indexed job ids collected, **one** `show_generation_by_ids` at the end, never
`job_display` per job. Accumulation reduces the number of groups; it does not repeal the cap.

**The pattern's known failure, which applies literally:** *"state file orphaned if the flush event never
fires."* A batch assembled and never fired leaves N episodes stalled behind a file nobody is
watching. **The usual remedy is a max-age sweep**, and `series_batch.py status` implements it:
an accumulator older than the threshold is reported STALE and the batch refuses to accept more.

### 3.1 The gate that gets better, not just faster

One frame gate for N episodes is the rare optimisation that **improves the work**. Drift is a
comparative property: you cannot see it in one episode, because one episode is self-consistent by
definition. Three episodes' frames on one contact sheet is the only view in which "the character's
jaw is heavier in ep 2" is visible at all.

`contact_sheet.py` across the batch, then the gate. This is the same argument as
`series-continuity.md` §6.1 — the registry exists because a property of a *set* has no per-item test.

---

## 4. The named dispatcher — one owner for the join

**Principle.** *"Parallelism is structured. One dispatcher spawns N specialists; specialists return
to the dispatcher; dispatcher re-assembles. No free-floating parallel calls, no convergence by side
channel."* [*Fan-out / fan-in with named dispatcher*]

The skill today has fan-out (batch generation) and **no named fan-in owner**. The stated failure mode
is exactly what happens without one: *"specialist results get dropped; partial results ship; failure
modes compound."*

**What this means in practice, for one person and no agent framework:**

- The dispatcher is a **role you are occupying**, and it is not the same role as making an episode.
  While dispatching you do not cut, prompt or grade — you read state and decide.
- **⛔ No episode ships from inside its own branch.** A branch produces a master and a state file and
  stops. Delivery is a join-side act, after §6.
- The dispatcher owns the ledger. Append-only, one line per decision — the A8 coordination ledger
  (§7 below). `_series/<BRAND>/BATCH-<ID>/LEDGER.md`.

---

## 5. File-based state handoff — why this works across a context reset

**Principle.** *"Cross-agent, cross-session, and cross-iteration state lives in files. Not in memory,
not in conversation, not in model context. A workflow that spans three sessions, two context resets,
and a crashed laptop survives if its state is on disk."*

This is the load-bearing enabler, and it is *why* parallelism is possible at all here. Parallel
branches cannot share a conversation — there is only one. They can only share files.

```
_series/<BRAND>/BATCH-<ID>/
  BATCH.json        the accumulator: episodes, lines, shots, group assignments, invariants version
  LEDGER.md         append-only: timestamp, signal, decision, outcome (the dispatcher's record)
  ep-<SLUG>.state   one per branch: stage reached, job ids, approved frames, findings, blockers
  JOIN.md           the join gate's readout (section 6) — written once, by the gate script
```

⛔ **A branch that exists only in the conversation is lost at the context boundary**, and a 12-hour
five-episode batch will cross at least one. If it is not in `ep-<SLUG>.state`, it did not happen.

This also makes the branches **resumable and inspectable**: `series_batch.py status` reads the files,
not the transcript, so "where is episode 3" has an answer that survives you closing the laptop.

---

## 6. ⛔ The join gate — the stage that trusts nothing

**Principle.** *"Multi-stage pipelines have at least one stage that does not trust prior stages.
Framing is explicit: you never trust the prior stage."* [*Independent audit at
pipeline gates*, load-bearing]

The per-episode QA card checks an episode against itself. **Nothing in the skill checks the episodes
against each other**, and that is the defect parallelism introduces: N branches each individually
clean, collectively inconsistent.

**The join gate runs once, after all branches report, before anything ships.** It reads the batch
state and the episode masters and asks only comparative questions:

| Check | Why only the join can see it |
|---|---|
| **Invariants version identical across branches** | A mid-batch bible edit is invisible inside a branch |
| **Same locked references cited by every branch** | A branch that regenerated its own reference is on-model *to itself* |
| **Identity side by side** — contact sheet across episodes, eye check | Drift is comparative, §3.1 |
| **Loudness and format consistent across masters** | `export_qc.py` passes each file against spec; only the join sees ep 2 sitting 2 LU hotter |
| **Hook / persona collision** | Two episodes shipping the same hook to the same audience is a batch-level fact |
| **Every branch reported** | The dropped-branch failure mode §4 names. **Silence is a FAIL, not a pass** |

`scripts/series_join.py` implements the mechanical half and **refuses a verdict without a real
observation**, the same way `qa_log.py` does. ⛔ It cannot see a face. The identity comparison is an
eye check against a cross-episode contact sheet, and the gate demands you record what you saw.

---

## 7. The archetype — A8, and explicitly not A18

A series build is a **known** workflow: the stages and their order are decided when the runbook is
written, not at runtime. That is the **Orchestrator (A8)** shape — a fixed routing table plus an
append-only coordination ledger.

It is **not** the **Supervisor (A18)** shape, which decides *which* sub-agents to spawn at runtime
and replans mid-flight. A18's own guidance is blunt about the misuse: *"If the topology is actually
known, A18 wraps A8 without adding value."*

And one level above that, the gate before either: **pipeline before loop.** *"Before reaching for the
Orchestrator archetype or any multi-step agent loop, ask: can this task be decomposed into 2–5 phases
with typed boundaries? If yes, build the pipeline first."* The measured backing is the Agentless
result — a fixed three-phase pipeline, no agentic loop, **27.3% on SWE-bench lite at $0.34/issue**
where comparable agent loops ran $5–50 [Xia et al., *Agentless: Demystifying LLM-based Software
Engineering Agents*, arXiv 2407.01489, 2024].

**The operative conclusion: parallelise the pipeline's stages across episodes. Do not spawn an
autonomous agent per episode.** Three branches of a fixed pipeline is this file. Three self-directing
agents making episodes is a different, worse system with no join.

---

## 8. What may run in parallel, and what may not

| Stage | Parallel across episodes? | Why |
|---|---|---|
| `route`, freeze check | Once for the batch | FIXED — one client profile, one invariants version |
| `script` | ⛔ **Serial** | Each episode needs its own argument. Writing three at once produces three of the same |
| `shotplan` | ⛔ **Serial** per episode, but the **handoff cards join** | The last shot of ep 1 does not hand off to ep 2 — episodes are independent works, not a continuous cut (`shot-handoff.md` §5 applies **within** an episode only) |
| `vo` | ✅ One batch | Audio-driven dialogue needs the VO first; that dependency is per-episode and batching does not violate it |
| `frames` | ✅ One batch | All branches generate from the same frozen references |
| `frame-gate` | ✅ **One gate, and better for it** | §3.1 |
| `clips` | ✅ One batch | Every approved frame from every episode |
| `selects` | ✅ Mechanical triage batches; eyes on flagged + landing only | `clip_qa.py` over the whole batch, one report |
| `edit` | ⛔ **Serial** | One timeline, one mix, one export per episode. The floor in §1.3 |
| `qa` | Ship gate batches; full card is per-episode | Plus the join gate (§6), once |
| `deliver` | Per episode, **released by the join** | §4: no branch ships itself |

⛔ **The one thing that must never be batched: the decision to ship.** Batching generation is
efficiency. Batching approval is how a shared defect reaches N clients at once instead of one.

### 8.1 ⛔ A client profile can require verification at every stage, and then most of §3 is off

Some accounts are checked by a person at every step — script, reference images, audio, clips — each
before the next stage begins. **A client with hard locks in its profile is one**, and on such an account
the shared frame gate is **not** a substitute for the per-stage checks.

The batching still pays, but only on its machine half. Keep the accumulator: firing one VO batch,
one image batch and one clip batch across episodes costs a person nothing and still collapses the
*waiting*. Drop the human saving: the gates stay per stage and per episode, so the sync points do
**not** collapse `3N → 3` on that account.

⛔ **Say which half you are claiming.** The §1.3 model assumes machine triage in front of the eye; on
a per-stage-human account it does not hold, and quoting it there is a promise you cannot keep. Time
the account with `stage_timer.py` and use the measurement.

---

## 9. Failure modes this introduces, and the guard for each

| Failure | Signature | Guard |
|---|---|---|
| **Drift fan-out** | Branches cut under different invariants versions | §2 freeze; version stamped per branch; join refuses a mismatch |
| **Orphaned accumulator** | A batch assembled, never fired; episodes stalled | max-age sweep — `series_batch.py status` reports STALE |
| **Dropped branch** | 5 fired, 4 delivered, nobody noticed | Join treats **silence as FAIL**; the ledger has no closing line for that branch |
| **Partial ship** | Two episodes go out, the third is "nearly done" | ⛔ Nothing ships until the join passes for the whole batch |
| **Shared defect × N** | One bad prompt convention repeated in every branch | This is the real cost of batching. The join's comparative checks exist for it; a defect *identical* across branches is the hardest kind to see and the reason the frame gate is the one place to spend |
| **Batch too big to review** | The frame gate becomes unreviewable and gets rubber-stamped | Cap the batch. **N ≤ 5 until `stage_timer.py` says otherwise** — beyond that the gate stops being a gate |
| **Sunk-cost join** | The join finds a batch-wide fault after all credits are spent | Fire batch B (frames) before batch C (clips) — the frame gate is upstream of the expensive stage precisely so a batch-wide fault costs images, not video |

---

## 10. Evidence — what has to exist before a batch is called done

- `BATCH.json` present, `invariants-version` identical across every `ep-*.state`
- `LEDGER.md` has a closing line for **every** branch — count matches the episode count
- `series_join.py` exit 0, with a recorded human observation for the identity comparison
- A cross-episode contact sheet actually looked at (`contact_sheet.py`), not just generated
- Per-episode evidence unchanged — the ship gate and full card of `production-runbook.md` §5 still
  apply to each episode. **The join is an addition, never a substitute**
- `EPISODES.md` row appended per episode, with the invariants version and the join key
- `stage_timer.py` report filed for the batch, so §1.3's model gets a data point

---

## 11. What this file cannot tell you

- **Whether the numbers in §1.3 are right.** They are structural reasoning, not measurement. The
  first real batch either confirms the model or falsifies it; until then the honest claim is
  "parallelism helps somewhat and has a floor around 3.5 h/episode", not a promise.
- **The right N for your attention.** The cap of 5 is a judgement about how many episodes' frames a
  person can hold in one gate, not a finding. If the gate starts feeling like paperwork, N is too big.
- **Whether a shared defect was worth the batching.** Batching multiplies mistakes at the same rate
  it multiplies output. That trade is only good if the frame gate is genuinely defended.
- **Anything about running episodes for *different brands* at once.** Everything here assumes one
  frozen invariants set. Two brands in one batch is two batches.
