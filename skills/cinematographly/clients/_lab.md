# Client Profile — `_lab` (internal calibration, not a client)

This is not a brand. It is the profile for calibration tests (`prompting-craft.md` §13: a few fixed
frames, one varied axis), so such a test runs through the gate like any other job instead of borrowing a
client's profile.

⛔ **Nothing generated under `_lab` ships.** No client, no distribution, no claims surface, no
disclosure obligation — because no viewer ever sees it. That is what makes the §0 answers below
legitimate rather than a shortcut: they are not unanswered questions, they are questions that do not
arise.

## 0. ⛔ Hard locks (read before any change)

**Default mode: C (editorial/explainer)** — the closest fit, chosen because a calibration frame has
no persona, no narrative and no batch. The mode is nearly inert here; what matters is that a test
declares one rather than leaving it blank.

1. **Format lock?** none — a test varies format on purpose.
2. **Audio-text lock?** n/a — calibration output carries no audio and no spoken line.
3. **Overlay policy?** none — no overlays, ever. An overlay would contaminate the varied axis.
4. **Retired tools/models?** none beyond the standing roster (`ai-generation.md`): `kling3_0`,
   `minimax_h3`, `seedance_2_5`. ⛔ A calibration job may NOT reach for an off-roster model — the
   whole point is to measure the models we actually ship on.
5. **Synthetic presenter permitted?** yes, and irrelevant — a synthetic figure in a test frame makes
   no endorsement because nobody sees it. ⛔ If a test frame is ever shown to a client or posted,
   it stops being a `_lab` asset and needs a real profile.

**Verification policy:** `per-stage-human`

⛔ Not `standing`, and the reason is the point of the file: **a test whose result nobody looked at is
the silent pass** (`research-quality.md`). A calibration run
ends with a human reading the frames and writing what they saw. The number goes in the record with
the date and the denominator, or the test did not happen.

## 1. Brand(s)
None. `_lab` is the skill testing itself.

## 2. Characters, personas & voices
None. ⛔ A calibration frame uses a generic figure or no figure. A recurring persona would import a
reference lock and a second variable.

## 3. Offer / subject matter (claims that must be accurate)
None — no offer, no claims. ⛔ This is the one profile where that is a fact rather than an omission,
and it is true only while nothing ships.

## 4. ⛔ Non-negotiables (compliance)
`claims_lint.py` still runs on anything written here, and should still pass. Not because a test frame
is an advertisement — it is not — but because a test that is allowed to be sloppy about claims
becomes the place sloppy phrasing is drafted and then copied. **No exception is granted; none is
needed.**

## 5. Language, distribution & delivery format
- **Language:** English (US).
- **Distribution:** none. Nothing is published, ever.
- **Delivery preset:** `vertical-1080` by default, so the safe box and aspect match production.
  A test that varies aspect says so in its record.

## 6. Visual Bible
None, deliberately. A house look is a confound: it is exactly the kind of held constant that hides
the axis being varied.

## 7b. Script numbers — none, and no per-client script JSON exists for this profile
n/a — calibration runs carry no script. `beat_plan.py` and `script_score.py` are not part of a
calibration job, and their refusal on zeros is correct and untouched.

## 8. Generation stack & budget
Roster as above. ⛔ **Every calibration job declares its own envelope in the checkpoint and prices it
with `rate_card.py` first.** A test is cheap only if somebody checked; "it is only a few frames" is
how a bake-off costs a month's credits.

## 10b. Review & approval
The approver is the person who ran the test and read the frames. A calibration result approved by
nobody is a claim, not a measurement.

## 11. The standing rule for this profile
⚡ **A calibration job's deliverable is a WRITTEN RESULT, not an asset.** The frames are evidence and
are disposable; the sentence that says what varied, what was held, how many were generated and what
was observed is the output. It lands in the skill file that carries the claim being tested, dated,
with its denominator — and if the result contradicts the skill, the skill changes.
