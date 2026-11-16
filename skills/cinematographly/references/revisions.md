# Revisions — one path for a note, wherever it arrives

**When to read this:** a client has sent notes; you are quoting a change; a note has arrived after
sign-off and you need to decide whether it is a fix or a new job. `pm-workflow.md` owns the gates
and the board. `review-and-approval.md` owns the platform and what counts as sign-off.
`refinement-loop.md` owns converging on one shot. **This file is what happens to a note between
arriving and being done — the routing, the cost, and the record.**

---

## 1. The principle

**A note is routed by where the fault lives in the pipeline, not by how it was phrased or how firmly
it was asked.** Every note gets two questions before it gets a yes:

1. **Which stage owns this?** — the earliest stage whose output is wrong.
2. **What does it cost from here?** — not what it would have cost at the gate where it belonged.

Those two answers give the cost class, and the cost class decides everything else: whether it is
included, what it re-runs, what it invalidates, and whether it is a revision at all. Saying *"that
note is a regeneration, not a trim, and here is what it costs"* out loud, before agreeing, is most
of what a producer does — and it is the difference between a bounded round and a month of drift.

---

## 2. The routing table — what a note costs and what it re-runs

| The note is really about | Cost class | What has to re-run | Invalidates |
|---|---|---|---|
| The angle, the persona, the premise | **Change order** | `ideation.md` kill tests, then everything | the whole video |
| Wording of a line | **Script change** | `script_score.py`, `claims_lint.py`, VO re-record — and on an audio-driven clip, that clip's regeneration | the VO, that clip, captions |
| Structure — beat order, what the hook is | **Script change** | scorecard, then storyboard | storyboard, coverage, transition plan |
| A shot's framing, look, or subject | **Regeneration** | `refinement-loop.md` from the owning stage; retake tree, cap 2 | that shot's clip and its selects |
| Which take is used | **Edit-only** | selects pass (`direction.md` §4) | nothing — the takes exist |
| Trim, reorder, pace, music level | **Edit-only** | the cut; beat markers if music moved | nothing |
| Caption wording, position, timing | **Caption pass** | the caption route in use (`editing-and-audio.md`) | the render, and its `srt_qa.py burned` check; an outside burn (route 3) too |
| Loudness, format, aspect, safe zones | **Delivery** | re-export per `assets/delivery-formats.json`, loudness re-check | the exported masters only |
| A claim, a disclosure, a risky phrase | **Compliance** | `claims_lint.py`, the disclosure checklist — ⛔ **never negotiable, never "just this once"** | whatever carried the claim |
| "It didn't perform" | **Not a revision** | `performance-metrics.md` — this is a new variant against the hook bank | nothing |

Two entries carry most of the money. **A wording change on an audio-driven clip is not a wording
change** — it cascades VO → clip regeneration → re-edit → captions, and the honest quote is that
cascade, not the minute it takes to retype the line. And **"it didn't perform" is not a revision at
all**: re-cutting a shipped ad because a number was low, without the diagnosis waterfall, is
guessing with the client's money. Route it to a new variant with a hypothesis attached.

---

## 3. Pre-production — where revisions are supposed to happen

The cheapest revision is the one taken against a script and a reference set, and the whole point of
Gate 1 (`pm-workflow.md`) is to move notes forward into that window. That only works if the gate
shows enough to react to:

- **The script**, in house format, with the hook and the button visible as such.
- **The shotlist**, including the blocking and performance cards — a client who cannot see the
  intent will approve words and then be surprised by pictures.
- **The reference set**, labelled by intent (`refinement-loop.md` §1). This is the single highest
  yield item at the gate: clients react to a picture far more reliably than to a sentence, and a
  reference rejected here costs nothing, while the same objection after generation costs the shot.
- **The claims and their substantiation** (`compliance.md`), because a claim withdrawn later takes
  the line, the VO and the clip with it.

**Invite the objection here, deliberately.** Ask what would stop them approving this, and get the
answer before generation spends anything. A client who says "I'd never say it that way" at the
script gate has saved you a batch; the same sentence after the cut is a change order.

---

## 4. Revisions in DaVinci Resolve

Notes arriving against a cut land as **timeline markers**, not as a chat thread you scroll while
scrubbing:

- **Frame.io:** filter comments to the asset → export CSV → `scripts/frameio_comments_to_edl.py` →
  Media Pool → right-click the timeline → **Timelines → Import → Timeline Markers from EDL**. Mind
  the offset: comment timecodes are file-relative and the timeline usually starts at `01:00:00:00`,
  and out-of-range markers import as nothing, silently.
- **Dropbox Replay:** comments sync natively both ways on Resolve Studio — but ⛔ **import every note
  before you render the next version**, because Resolve can only pull comments from the file's
  *current* version, and a note you leave behind becomes web-only permanently.

Then work the markers, not the memory of the call:

- **One round per version.** Take the whole marker set, do the pass, render one new version. A cut
  re-rendered per note trains the client to send notes one at a time, which is the most expensive
  cadence there is.
- **Version bump, never overwrite** — `<SLUG>-v<N>` per `pm-workflow.md`. The approved version has
  to stay reachable, because the silence rule and the sign-off both point at "the last approved
  version" and that has to be a real file.
- **Delete or resolve a marker only when the note is done**, so the remaining markers are the to-do
  list and the empty timeline is the definition of finished.
- **Captions re-conform after any timing change** — a trim moves every cue after it. The conform
  bridge (`DUMP_TIMELINE_JSON` → the caption route) exists for exactly this, and skipping it is how
  a batch ships with captions half a second late.
- ⛔ **Do not re-cut from scratch** to satisfy a note. The approved material's timings are the
  client's expectation; rebuilding the cut re-opens decisions that were already made and produces a
  second round of notes on things nobody had objected to.

---

## 5. The record

Every round leaves three artifacts, and they take about four minutes:

1. **A decision record** in `00-brief/DECISIONS-<SLUG>.md` — what was asked, what class it was, what
   it cost, who approved. **A reversal is a new record pointing at the old one**, never an edit of
   it: "we went back to v1's opening" is information, and overwriting the history destroys it.
2. **Manifest rows** for anything regenerated (`shot_manifest.py`) — retakes are new rows carrying
   the one variable that changed, so the cost of the round is measured rather than estimated.
3. **The round's evidence** in `09-qa/review/` — the comment export and the version it was against.

On the board (`pm-workflow.md`): a milestone time entry for the round, never a live timer; a comment
naming the round and its cost class; and, if the round exceeded what was included, the escalation
happens **before** the work, not in the invoice.

---

## 6. The scope boundary

- **Round one** is scoped to the whole cut. **Round two** is scoped to round one's items — new
  material introduced in round two is a change order, not a continuation. **Round three** is a
  change order by definition.
- **A note that contradicts an earlier approval is a change order**, however small it looks. The
  cost is not the edit; it is that the approval it overturns had things built on top of it.
- **After sign-off, everything is a new job** — priced, scheduled, and not squeezed into the current
  batch, because the batch's capacity was planned at 70–80% for the work that was known.
- **Silence is not approval, and it is not a licence to stall either.** State the window in the
  handoff — "notes by Thursday, else this version ships Friday" — and then honour it in both
  directions (`pm-workflow.md`).
- ⛔ **Compliance is outside this section.** A claims or disclosure note is not a round, is not
  negotiable, and does not get traded against scope.

---

## 7. At volume

- **Batch the revision pass.** Collect the drop's notes, do one revision session across all of them,
  ship one new version set. Context-switching per note is the hidden throughput killer at 30–50
  videos a month, exactly as it is in generation (`modes/ugc-volume.md`).
- **A note that repeats across videos is not a revision — it is a brief defect.** Three clients'
  worth of "the CTA feels pushy" is a hook-bank and script-craft problem; fix it upstream and the
  round disappears next month. Repeated notes belong in the episode note (`self-evolution.md`).
- **Revision capacity is planned capacity.** If a client's rounds routinely consume a day a month,
  that day is in the plan or the plan is fiction.
