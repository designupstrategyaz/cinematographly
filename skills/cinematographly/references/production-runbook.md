# Production runbook — a 20–40s video in 4–5 hours

**Owner:** the producer · **Frequency:** per video · **Applies to:** Mode A/B/C, 20–40s, **on a brand
whose series is already locked**. ⛔ Read §1 before trusting the number.

⛔ **This file is the SINGLE-episode route, and a single episode is the degenerate case.** The unit
of work is the series batch; `series-parallel.md` §0 owns that framing and §1.3 shows why. Use this
file unchanged when N = 1 — at N = 1 the batch machinery is measurably *worse*. For N ≥ 2, read
`series-parallel.md` first: §2 there becomes one accumulated batch across all episodes, and a join
gate is added after §7.

**When to read this:** you are producing a standard video and want the fast path rather than the
whole skill. This is the *route*, not the craft — every stage below links to the file that owns it,
and none of that reasoning is repeated here. If a stage goes wrong, that is when you leave the
runbook and read the reference.

---

## 0. ⛔ The number is a VARIANT number, and it is not measured yet

Two honesty flags before anything else, because both change what this document is.

**1. 4–5 hours is a *variant* target. The measured figure, 6.5 h, is a *setup*.** The capacity model
already distinguishes them: `month_hours = setups × SETUP_HOURS + variants × VARIANT_HOURS`, where
6.5 h is measured and **VARIANT_HOURS has never been measured at all**. This runbook is a proposal
for what that unmeasured number should be. **The route to 4–5 hours is therefore not "work faster"
— it is "make this video a variant"** (§8). A genuinely new brand, character, format or claim is a
setup and will not fit, and pretending otherwise just moves the overrun into QA.

**2. Nobody knows where the 6.5 hours go.** The figure is measured in aggregate and completely
unallocated. Every optimisation below is reasoned from the pipeline's structure, not from a stage
breakdown — which by this skill's own standard makes it a hypothesis. `scripts/stage_timer.py`
exists to fix that: declare each stage as you start it, and after a handful of videos the budget in
§4 either becomes a finding or gets falsified. **Run it. A budget nobody measures is a wish.**

---

## 1. Where the waste is — the current state, analysed

Using the five-waste frame from `operations:process-optimization`:

| Waste | Where it lives here | The move |
|---|---|---|
| **Waiting** | ⛔ The biggest one. `PIPELINE.md` Stage 3 says *"for each job… `generate_image` then `generate_video`"* — **serial, per shot**. Eight shots is sixteen sequential round-trips, each with its own dead wait | **Three batches, three sync points** (§2) |
| **Rework** | Retakes. A bad start frame propagates into every clip made from it | Concentrate review at the **frame gate** — the one-way door — and triage clips mechanically (§3) |
| **Handoffs** | "Pick finals" is a human sync point *after* all generation, on every clip | Machine triage first; the human sees flagged clips + the shots that must land (§5) |
| **Over-processing** | The QA card has grown a lot. Running twenty craft checks on a 2-second B-roll insert is not diligence | **Tier the gate** (§5) |
| **Manual work** | Mostly already automated — `pull_finals.py`, `build_fcpxml.py`, `build_srt.py`, and the console's `PLACE_SUBTITLES` (`native.py console`); titles, Fusion and Fairlight work are computer control since v2.49 (house rule 8, `editing-and-audio.md` § What runs through the API) | Keep the overlap window full (§3) |

---

## 2. The three-batch structure — the single biggest lever

The dependency chain is fixed and short: **VO → start frames → clips.** Dialogue clips are
audio-driven, so the VO must exist first; clips need an approved frame. That is **three** sync
points, not `3 × shots`.

⛔ **For N ≥ 2 episodes, this batch is assembled ACROSS episodes, not within one** — every line of
every episode in batch A, every shot of every episode in batch B, one frame gate for the lot. Sync
points go `3N → 3`, and the shared frame gate is the only view in which drift is visible at all.
`scripts/series_batch.py plan` emits the groups; the doctrine and its ceiling are
`series-parallel.md` §3. Everything below still describes one episode's share of that batch.

```
A · VO            generate_audio_batch   → jobs_wait          (all lines at once)
B · Start frames  generate_image_batch   → jobs_wait          (all shots × 2 variants)
    ⛔ FRAME GATE — the one-way door. This is where slow human review belongs.
C · Clips         generate_video_batch   → jobs_wait          (all approved frames at once)
    clip_qa.py triage → human sees flagged + landing shots only
```

⛔ **`jobs_wait` takes at most 12 jobs**, so a batch larger than that is split into groups of ≤12 and
waited on group by group — still one wait per group, not one per shot. Collect the indexed job ids
and display them with a single `show_generation_by_ids` at the end; never call `job_display` per job.

**Why this is worth more than any craft change:** it converts *n* dead waits into three. On an
eight-shot video that is the difference between a morning of babysitting a queue and three coffee
breaks — and the third one is not a break at all (§3).

---

## 3. The overlap window — what runs while Batch C cooks

Clip generation is the longest wait and it needs no human. Everything below depends only on the
**locked script** and the **approved frames**, so all of it can be done inside that window:

- **Captions** from the locked script — `build_srt.py`, placed in Resolve after lock (`native.py console <job> --srt …`;
  outside Resolve only with a reason, house rule C7). The words cannot change (`revisions.md`), so the `.srt`
  never needs to wait for picture.
- **Music** selection, mapped (`music_fit.py map`); the fit waits for the locked cut.
- **The timeline skeleton** — `build_fcpxml.py` with the planned durations, or the Resolve console
  script, so the edit starts from a built sequence rather than an empty one.
- **The delivery folder and the registry row** — `_series/<BRAND>/EPISODES.md`, including the
  invariants version (`series-continuity.md` §6.1).
- **The board** — move the ClickUp card, per `pm-workflow.md`.

⛔ **Do not use the overlap window to start reviewing clips as they land.** Reviewing a partial batch
means re-reviewing in context later; it feels productive and costs the time twice.

---

## 4. The budget

Minutes, for a 20–40s variant (6–9 shots) on a locked brand. This is the budget baked into
`stage_timer.py`, so the report compares against exactly these numbers.

| Stage | Min | What has to be true to hit it |
|---|---|---|
| `route` | 15 | Mode and client profile load clean; brief is **T0/T1** research (`preproduction-research.md` §2) |
| `script` | 30 | Locked-voice draft, `script_score.py`, read aloud once. Not a blank page — a hook from the bank |
| `shotplan` | 40 | Shotlist + emotional map + handoff cards + prompts, in one pass |
| `vo` | 10 | Batch A fired and returned; lines trimmed to length |
| `frames` | 30 | Batch B fired and returned (2 variants/shot) |
| `frame-gate` | 25 | ⛔ **The one place to spend.** Frame tests, cover-the-face, identity vs reference |
| `clips` | 25 | Batch C fired and returned; the overlap work (§3) happens here and is not charged again |
| `selects` | 20 | `clip_qa.py` triage, then eyes on flagged + landing shots only |
| `edit` | 55 | Assemble onto the skeleton, beat-match, mix, captions conform |
| `qa` | 20 | Ship gate on every clip, full card on the two that matter, `export_qc.py`, claims lint |
| `deliver` | 15 | Export, `SendUserFile`/commit, folder + manifest, board closed |
| **TOTAL** | **285** | **4 h 45 m** — 15 minutes of slack against a 5-hour ceiling |

⛔ **The slack is 5%.** One unplanned retake cycle (~25 min) eats it. That is the honest tolerance,
and it is why §5 and §8 matter more than shaving minutes anywhere else.

**Across a batch of episodes the number falls, but not far, and it has a floor.** 160 of these 285
minutes — `script`, `shotplan`, `edit`, `qa`, `deliver` — are serial per episode and no batching
touches them, which by Amdahl's law caps the whole exercise at about 1.8× and lands the per-episode
figure near **212 minutes (~3.5 h) however many episodes are in flight**. The proposed table is
`series-parallel.md` §1.3. Its practical consequence: **once you are batching, the next real speed
lever is `edit` and `shotplan`, not more parallelism.**

---

## 5. Tiered QA — the gate that keeps the budget

The craft references added a lot of checks. Running all of them on every clip would cost more than
the generation. **So the card is tiered, and the tier is chosen by what the shot does** — which the
handoff card already declares (`shot-handoff.md` §5).

**Ship gate — every clip, target ~60 seconds each:**

- [ ] Format and duration — `export_qc.py` (mechanical, batch it)
- [ ] `clip_qa.py` clean, or its finding is understood and accepted
- [ ] **Mouth closed and still after the final word** — eye check at 0.25× (`shot-handoff.md` §9)
- [ ] On-model against the locked reference; product and wardrobe unchanged
- [ ] No gross artifact at a contact point (hands, props, edges)

**Full card — only three kinds of shot:** the **hero**, the **landing** shot (`--landing`), and
anything the ship gate flagged. That is where blinks, gaze count, ease-out, the composed end frame
and the rest of `realism-qa.md` §6 get read in full.

**Join gate — once per batch, N ≥ 2 only:** `series_join.py check` — every branch reported,
one invariants version, loudness consistent across episodes, no hook/persona collision, and a
recorded eye check of the episodes side by side. ⛔ **It is an addition, never a substitute:** the
two gates above still run on every episode. `series-parallel.md` §6.

⛔ **A mid-sequence 2-second insert does not get the full card.** Its back-loaded peak is an *asset*
because you cut out of it, and half the temporal checks do not apply to a shot nobody looks at twice.
Applying them anyway is over-processing with a craft justification, which is the most convincing kind.

---

## 6. Procedure

**Prerequisites** — if any of these is missing, this is a setup, not a variant (§8):

- [ ] Client profile loaded, hard locks read
- [ ] `_series/<BRAND>/` exists; `INVARIANTS.md` current; `_reference/` populated
- [ ] Hook chosen from the bank, not invented
- [ ] Approved claim wording available (`compliance.md`)
- [ ] `series_registry.py check` passes

```
python3 scripts/stage_timer.py start route      # ...and at the top of every stage below
```

1. **route** — mode + client. State the production checkpoint. *If the brief needs T2/T3 research
   (`preproduction-research.md` §5), stop: this is a setup.*
2. **script** — draft to the locked voice, `script_score.py`, read aloud. *Bar is 7; below it, fix
   the script now — a generated video of a weak script costs the same and is worth less.*
3. **shotplan** — shotlist, emotional map, handoff cards, prompts, in **one** pass.
   *Expected: 6–9 shots, one beat each.*
4. **vo** — `generate_audio_batch` → `jobs_wait`. ⛔ Trim to the line; do **not** pad to a longer clip
   duration (`shot-handoff.md` §1).
5. **frames** — `generate_image_batch`, 2 variants per shot, one call per ≤12 jobs.
   ⛔ At the resolution floor — 1080p minimum, the model's 2K/4K tier where it exists. **There is no
   cheap first pass**: a lower-tier generation is a different take, not a preview of this one
   (`ai-generation.md` → the quality floor).
6. **frame-gate** — the frame tests, the cover-the-face test, identity against the reference.
   *If a frame fails twice on the same axis, the axis is not controllable — change the shot
   (`refinement-loop.md`).*
7. **clips** — `generate_video_batch` → `jobs_wait`. **Then do §3's overlap work while it runs.**
8. **selects** — `clip_qa.py` on the batch, then eyes on flagged + landing shots.
9. **edit** — assemble onto the skeleton built in §3; beat-match; mix; conform captions.
10. **qa** — ship gate on all, full card on hero + landing, `export_qc.py`, `claims_lint.py`.
11. **deliver** — export, deliver, register the episode, close the board.

```
python3 scripts/stage_timer.py report
```

---

## 7. Verification and troubleshooting

- [ ] `stage_timer.py report` total under 285 min, and **the log was actually kept**
- [ ] Every clip passed the ship gate; hero and landing passed the full card
- [ ] The episode is registered with its invariants version
- [ ] Costs reconciled (`reconcile_costs.py`)

| Symptom | Likely cause | Fix |
|---|---|---|
| `frames` blew its budget | The brief was not settled — you are art-directing and briefing at once | Stop generating. The frame is not the problem |
| `frame-gate` blew its budget | Two variants was not enough, or the reference set is weak | More variants next time is cheaper than more gate time — `refinement-loop.md` §1 |
| `selects` blew its budget | You reviewed clips as they landed (§3), or ran the full card on everything | Triage mechanically first; tier the gate (§5) |
| `edit` blew its budget | The skeleton was not built during the overlap window | It is free time; use it |
| Total fine but the video is weak | The budget is not a quality gate | The script scorecard and the QA card are; a fast bad video is still a bad video |

**Rollback:** there is nothing to undo — the timer only writes a log. If the budget is unreachable
after three honest attempts, **the budget is wrong**: change it here and say why, rather than quietly
running over.

---

## 7b. The ONE-SHOT path — when the job is a shot, not a video

⛔ **Added 2026-08-30 after an external review found the gap.** Everything above is a *video*-level
fast path: it assumes a brief, a script and a delivery. But a real request is often *"design this one
shot"* — the script exists, the plan exists, one shot is wrong or missing. Routed through §6 that
request inherits intake, scripting, compliance and export gates it does not need, which is the
"unbounded textbook" failure in miniature.

**Entry test — all three must be true, or go back to §6:**

1. The words are already locked (or the shot is silent).
2. The brand's invariants and `_reference/` exist — this shot joins an established look.
3. Nothing about the shot touches a claim, a disclosure or a new format.

**The path, ~25 minutes:**

| # | Step | Owner file |
|---|---|---|
| 1 | **State the shot's job in one line** — what the viewer should feel and what question is open | `emotional-journey.md` §2 |
| 2 | **Handoff card** — FUNCTION / IN / OUT / JOIN. What it inherits, what it hands on | `shot-handoff.md` §5 |
| 3 | **Blocking + performance card** if a character is in it | `direction.md` §1–2 |
| 4 | **Start frame**, then the frame gate — ⛔ the one-way door, and the only place to spend | `refinement-loop.md` §2 |
| 5 | **Motion prompt**, one beat, one move | `motion-design.md` §5 |
| 6 | **Generate, then `clip_qa.py`** | `production-runbook.md` §5 ship gate |
| 7 | **Ship gate only** — full card only if this is the hero or the landing shot | `realism-qa.md` §6b |

⛔ **What this path does NOT skip:** the client's hard locks, the format, the identity lock — and
**the gate**: the job is open, the frame is approved with its media id, the clip prompt is linted,
and the call is what `gate.py preflight` printed (`SKILL.md` §0). A one-shot request is still a
generate call, and generate calls outside a job are denied. A
one-shot request that would break an invariant is not a one-shot request — it is a change to the
series (`series-continuity.md` §3), and it goes back to the full path.

## 8. ⛔ What makes a video a SETUP — and therefore not 4–5 hours

Any one of these and the 6.5 h figure applies, not this runbook:

- **A hybrid shot** — real footage cut with, or composited into, generated footage. The plate shoot
  and the match pass are extra stages the budget does not contain (`real-and-ai.md` §4)
- A new brand, or a client profile that does not exist yet
- A new character, persona or voice — the identity work is the setup
- No `_series/<BRAND>/_reference/` folder, or invariants not yet written
- A **new claim** needing T3 research (`preproduction-research.md` §2) — one-way door
- A **new model** — a bake-off is mandatory before adoption (`ai-generation.md`)
- A new delivery format, aspect ratio or platform
- A hook invented rather than drawn from the bank

**This is the actual answer to "how do we get to 4–5 hours".** Not compression — **conversion.** Each
of the items above is a one-time cost that a series pays once and then amortises across every
episode, which is exactly what `series-continuity.md` is for. A producer running four brands with
locked series and full reference folders is in a different time regime from one starting fresh each
month, and no amount of batching closes that gap.

---

## 9. What this runbook cannot promise

- **That 4–5 hours is achievable.** It is a designed budget, not a measurement. `stage_timer.py`
  exists to prove or refute it, and the honest state today is *unproven*.
- **That the stage budgets are right relative to each other.** They are apportioned by reasoning
  about the pipeline's structure. The first three logged videos will redistribute them.
- **Anything about a setup video.** The 6.5 h figure stands and is not addressed here.
- **That the craft references can all be applied at this speed.** They cannot, which is why §5 tiers
  them. ⛔ A skill that grows faster than its routing gets slower to use — this file is the routing,
  and if it stops being the fast path it has failed.
