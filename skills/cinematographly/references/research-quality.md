# Research Quality — how online facts earn their way into production

The skill's division of labour says the web holds current specifics — prices, model capabilities,
platform policy, benchmarks, compliance wording. This file is the discipline for *how* those
specifics are gathered, so a confidently wrong fact never becomes a script claim, a cost quote, or
a compliance decision.

**The governing principle, same as every other gate in this skill:** a research claim must carry
evidence that could not exist without the work having been done — a URL, a tier, a check date. A
fact stated without those is a recollection wearing a fact's clothes.

---

> **This file governs how a claim is sourced and labelled. It does not decide which questions get
> asked, or how hard.** That is `preproduction-research.md` — the depth ladder, the saturation
> stopping rule, and the measured cost of researching a question whose answer cannot change the
> decision. Read that one first when scoping; read this one while doing the work.

## 1. When research is mandatory, not optional

Run a live check — never answer from training recall — for anything in these classes:

| Class | Examples | Why recall fails |
|---|---|---|
| **Prices & rates** | credits/sec, plan tiers, market rates | Drift constantly; this account has already been burned by a ~40% per-second drift |
| **Model capabilities** | what a model outputs, fps, audio support, whether it still exists | Models update *silently*; the roster (`ai-generation.md`) is a hypothesis until re-verified |
| **Platform policy** | AI disclosure, ad rules, safe zones, spec | Changes quarterly; a wrong disclosure rule is a compliance failure, not a typo |
| **Regulatory wording** | FTC/FDA guidance, statute status | "A new 2026 rule" that doesn't exist has already circulated in secondary sources — we caught one |
| **Benchmarks** | retention rates, hook-rate norms, refresh cadence | Vendor-aggregated and moving; usable directionally, never as an SLA |

Durable principles — attention, perception, colour, persuasion structure — do **not** need a live
check; they come from the literature (`assets/further-reading.md`). Never spend a search on
Gestalt; never trust recall on a price.

## 2. Source tiers — label every researched claim

Every claim that enters a deliverable, a client profile, or this skill carries a tier, a date, and
a source:

- **[PRIMARY]** — the party that owns the fact: the vendor's pricing page, the platform's own policy
  page, the regulator's text, the API's live model list, a `get_cost` preflight, your own settled
  ledger. **Prices, policies, and capabilities require PRIMARY — or two independent SECONDARY with
  the disagreement noted.**
- **[SECONDARY]** — a reputable practitioner, agency, or aggregator reporting on a primary.
  Usable for practice norms and benchmarks; always attributed as secondary.
- **[UNVERIFIED]** — a listicle, a single blog, a forum post, or model recall. May generate leads;
  **never terminates a claim.** If it can't be upgraded, it ships flagged or not at all.

Format, wherever the claim lands: `<claim> [PRIMARY · vendor pricing page · checked 2026-08-28]`.
The date matters as much as the tier — see §5.

**A tier is not uniform across a source. Split it when the evidence says to.** A source can be
worth citing for one kind of claim and worthless for another, and collapsing that into one tier
either throws away usable material or launders unusable material.

⚠️ **Standing note — StudioBinder.** Three of its ebooks are read into this skill and all three are
**lead-magnet marketing with no citations anywhere**: every practitioner quote arrives as a caption
on a film still, none quoted, none linked, none checkable. Three factual errors are on record across
them (*Pleasantville* attributed to David Lynch; Rembrandt placed in the Italian Renaissance;
*Caligari* misspelled in the sentence citing it), plus internally inconsistent colour temperatures,
a chapter-numbering skip, and a worked example that commits the exact error the same chapter teaches
you to catch. **So: the vocabulary is citable at [SECONDARY]; the attributions, histories and
numbers are not citable at all.** The vocabulary is the part that is genuinely valuable — it is a
distillation of what the field *calls* things, which is what `cinematography-craft.md` §7.0 says a
prompt is actually scored against. The full ledger of rejected claims is that file's §9.0.

## 3. Convergence is not verification

Three listicles agreeing is usually **one source copied three times** — aggregators feed on each
other. Real convergence means independent *kinds* of source: a vendor page plus a practitioner
report plus your own tool output. Before treating agreement as strength, ask whether the sources
could have a common ancestor. The strongest verification available to this account is always the
same: **run the tool** — `get_cost` beats every article about pricing ever written.

## 4. The refutation pass — for load-bearing claims only

Before a claim decides real money or a compliance stance, spend one search looking for evidence
**against** it: "X discontinued", "X changed", "X wrong", the newest results first. Two outcomes,
both valuable: you find the correction before production does, or you note "refutation search:
nothing found, <date>" — which is itself evidence. This is how the phantom "2026 FTC AI endorsement
rule" was caught: the check wasn't "find support" (plenty existed, all copying each other) but
"find the primary rulemaking" — which didn't exist.

## 5. Research decays — verify at point of use

A researched fact is stamped, not permanent:

- **Prices, model capabilities, model lists:** stale after ~a quarter, and immediately stale on any
  sign of drift (the shot manifest's model-version column is the early-warning system). Re-verify
  before any big batch.
- **Platform policy and specs:** re-check per engagement for a new channel; safe zones and
  disclosure mechanics move with UI releases.
- **Regulatory:** re-check per claims-sensitive engagement. Guidance documents get superseded.
- **Anything entering a client profile or this skill** gets its check date written next to it, so
  the next reader can judge staleness instead of inheriting confidence.

## 5b. ⚡ Supersession — a corrected claim must say what it replaced, and the replaced one must know

A tier says how well a claim is evidenced. A date says when it was checked. Neither says **that a
later finding overturned it** — and that is the failure this skill keeps having. Four times in one
day (2026-09-17): the sheet's *"one identical person across all three panels"*, the *"four
attributes, not a paragraph"* vehicle sheet, the nano-banana image rate, and the earlier reading of
the Kling 1080p rate. Each was corrected properly *in the moment*; none of them left a trail a
checker could follow, so the next reader's protection was that I happened to remember.

⛔ **The danger is not the wrong claim. It is the wrong claim left LIVE and UNLINKED** — still
loadable, still confidently worded, in a file nobody is about to open. Two contradictory statements
in one skill are worse than either one alone, because whichever the reader reaches first wins.

**The markers.** Two forms, and which one you use depends on whether the old text survives.

```
the old text is DELETED and the new text stands where it stood
    at the new claim :  <warn> **SUPERSEDES IN PLACE** (YYYY-MM-DD) - previously: "<old wording>". <why it was wrong>
    at the old claim :  nothing; it is gone

the old section REMAINS (it carries other content, or it is kept as history)
    at the new claim :  <warn> **SUPERSEDES** <backtick><the file.md><backtick> §N (YYYY-MM-DD) - <why>
    at the old claim :  <stop> **SUPERSEDED BY** <backtick><the file.md><backtick> §N (YYYY-MM-DD)
```

Write the real markers with this file's usual ⚠️ and ⛔ in place of `<warn>` and `<stop>`, a
backtick where the skeleton says so, and an em dash for the separator. ⚡ **Markers inside backticks or a fenced block are examples and are not
checked** — which is how this section can show all three without declaring any.

Both are enforced by `skill_audit.py` (check 11):

- a `SUPERSEDES` target must **resolve** — the file and the section must exist
- it must carry a **date** and a **reason** — "superseded" with no reason is a deletion with extra
  steps, and the reason is the only part a future reader can argue with
- ⚡ **reciprocity**: if the superseded section still exists it must carry the back-pointer. This is
  the check that matters — it is what makes a live stale claim impossible to leave behind
- a `SUPERSEDED BY` must point at a section that supersedes it *back*, so a half-written pair fails
  from either end
- `SUPERSEDES IN PLACE` must quote what the text **used to say**, so the correction is legible
  without a git blame
- nothing may supersede itself

`skill_audit.py --supersessions` prints the whole graph, which is the fastest way to see what this
skill has changed its mind about.

**What supersession is NOT.** ⛔ Do not use it to close an argument you have not settled.

- Two findings that **disagree and are both live** are an **open question**. They go in the relevant
  asset with a proposed study, the way the resolution-vs-framing tension does
  (`assets/creative-benchmarks.json` → `_the_resolution_vs_framing_question`, `lab-00003`). Marking
  one "superseded" because it arrived later is how a corpus becomes an opinion.
- Two findings about **different things** are a **scope**, not a conflict — see the brand-timing
  question in the same asset, which was resolved as a scope after being mistaken for a contradiction.
- A measurement that **disagrees with an older measurement of the same thing** supersedes it only
  when someone who can settle it says so. `assets/higgsfield-rates.json` keeps the older reading in
  `superseded_history` rather than deleting it, because ⚡ **the disagreement is itself evidence** —
  four sources gave four answers for one model at one resolution, and that fact is worth more than
  any one of the numbers.

**The test before you write either marker:** *can I say what changed my mind, and would a reader who
believed the old thing accept the reason?* If not, you have a new opinion, not a supersession.

## 6. Honest gaps — the researcher's obligation

Research output must name what it could **not** verify, with the same prominence as what it could.
"Pricing is [SECONDARY] only — the vendor page is JS-gated" changes what a quote may claim. The
verification readout's `Gaps:` line (`pm-workflow.md`) is where this surfaces in deliverables; a
research pass with no stated gaps is either a miracle or a silence, and silences are the failure
mode. When a fact is missing and load-bearing, the verdict is **NEEDS INPUT** — not a best guess
dressed as a finding.

**A reference film is read, not quoted.** Text, names, prices, taglines and claims read off a
reference film's frames stay in the local notes, in our own words, and never pass into a client's
script, cards or the move catalogue. And a card, a price or a word that did not read on the frame is
recorded as unread — never completed from the voice, a neighbouring frame or a guess. That is this
section's rule at the point where `film_breakdown.py` sheets are read (`move-catalogue.md`, the
legend before §34).

## 7. Where this feeds

Compliance rules (`compliance.md` — live wording, always), cost cards (`clients/costs.<brand>.json`
— source line carries tier + date), the **model roster** (`ai-generation.md` — capabilities with
last-verified dates), delivery presets (`assets/delivery-formats.json` — its `_verify` note),
benchmarks in `modes/ugc-volume.md` §1 (directional, secondary, and marked as such), and any fact a
script will speak out loud (`script-craft.md` — a spoken number is a claim; see the claims lint).

**Cross-refs:** `pm-workflow.md` (provenance labels, the verification readout) · `compliance.md` ·
`ai-generation.md` (the model roster and bake-off) · `assets/further-reading.md` (the
durable-vs-current division this file operationalises).
