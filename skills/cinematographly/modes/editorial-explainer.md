# Mode C — Editorial / Explainer

**Use when:** the video's job is to *inform* rather than to sell a specific SKU — an editorial topic,
a category explainer, a comparison, a "how to choose", a social-search asset ("what actually causes
X"). Common on publisher-side or content-marketing briefs, and increasingly on ecommerce brands that
run an editorial arm.

**The distinguishing feature:** the payload is a *claim about the world*, not a claim about a
product. That changes the risk profile and the structure, so it gets its own lane rather than being
squeezed into a UGC ad shape.

## Files this mode requires — read before the artifact, not instead of it

Beyond SKILL.md §2's ladder: `references/research-quality.md` (every claim decides trust — source
tiers, the refutation pass) · `references/compliance.md` §1–§4 · `references/preproduction-research.md`
(how deep, when to stop) · `references/typography-and-captions.md` (this mode is the one that may
need on-screen type — check the profile's overlay policy, it overrides the captions-only default) ·
`references/editing-storytelling.md` for the structure of an argument in 40 seconds. Artifacts: the
checkpoint (`Mode: C`), a script whose every factual line carries a `[PRIMARY · URL · date]` tag,
`claims_lint.py` clean, then the same linted prompts as any mode.

---

## What changes vs the other modes

| | Narrative promo | UGC volume | **Editorial** |
|---|---|---|---|
| Payload | A story that sells | A hook that converts | **Information that's correct** |
| Authority comes from | Character and craft | Peer authenticity | **Sourcing and clarity** |
| Failure mode | Boring | Reads as AI | **Being wrong, or sounding like an ad** |
| Compliance focus | Brand non-negotiables | Claims + disclosure | **Accuracy, attribution, and not implying a health claim** |

---

## Structure

**35–55s, three movements:**

1. **The question (0:00–0:06).** Ask the thing the viewer typed into search, in their words.
   "Why do you wake up at 3am every night?" — not "Sleep facts you need to know."
2. **The answer, in ordered beats (0:06–0:40).** Two to four beats, each one *visual*: a number, a
   comparison, a demonstration, a diagram. **One idea per beat.** If a beat needs a sentence to set up
   another sentence, it's two beats.
3. **The turn (0:40–0:55).** What the viewer should do differently, or the one thing that surprised
   them. Editorial earns a soft CTA at most — a hard offer here breaks the register and the trust.

**"Three things" is the reliable default shape.** Numbered beats give the viewer a progress bar,
which measurably holds retention, and they make the script trivially modular for reuse.

---

## Sourcing rules

- **Every factual claim needs a source you could show.** Not necessarily on screen — but in the
  script file, next to the line.
- **Attribute on screen when the claim is load-bearing** — a study, a figure, a regulation. A small
  source line in the caption safe zone.
- **Never let a general fact become a product claim by adjacency.** An editorial beat about magnesium
  and sleep, cut next to a product shot, is a product claim regardless of what the words said. This is
  the *net impression* rule from `compliance.md` §1, and editorial is where it is easiest to trip.
- **Distinguish "research suggests" from "research shows."** Use the weaker verb when the evidence is
  observational; it costs nothing and is the difference between accurate and overstated.
- **Date-stamp anything that expires** — prices, regulations, deadlines, "the current best".

---

## Production notes

- **Faceless or low-presenter is usually right.** The authority is the information; a presenter adds
  a face to distrust. VO + B-roll + text kinetics + product/object macro.
- **Text on screen carries the numbers.** Editorial is consumed muted more than any other format —
  every figure spoken should also be readable. `soundoff.py claims` lists any number the VO says that no
  caption or title shows, and the full T2 (`references/sound-off-story.md`) asks whether the B-roll shows each beat.
- **Pace is slower than UGC and faster than narrative.** Give a number two seconds to land.
- **B-roll is the whole visual budget.** Plan more inserts than an ad would need — one per beat
  minimum, ideally two, because there's no dialogue performance to hold the eye.
- Everything else — generation, identity, mix, captions, export — follows the shared references.

---

## The mechanism and diagram beat (v2.46): built from numbers, never generated

A diagram beat, or a beat that shows how something works (a mechanism, a cross-section, a process), is the one
beat in this mode where a generated picture is always wrong. A video or image model invents the parts, the
proportions and every number on screen, which is `references/product-video.md` §0's rule about UI, applied to a
mechanism. The method was adapted from an open-source teardown-simulator skill's build rules, in our own words
and with none of its code. These are the rules. The tooling to build such a beat is not part of the plugin yet.

1. **Never generated.** No image or video model draws the mechanism, the diagram or its labels. Generation is
   still fine for the people and the world around the beat.
2. **Built from numbers.** The beat is made in Blender from a blocking spec with real dimensions
   (`references/blocking.md` §3e, precise geometry), or as native Fusion shapes in Resolve. Either way it is
   built from one written spec. **Open question Q1 (the owner's): may our own 3D render be delivered picture,
   and do isolate, section and exploded views count as the "advanced VFX" the house does not do?** Until it
   is answered, the 3D build is a previs and a reference only.
3. **One source for every on-screen number.** Each label and each figure on screen is read from that same
   spec, never typed again into a title. When the spec changes, the labels change with it.
4. **One hand check, written down.** For each mechanism beat, the script file carries one worked check of
   the numbers (a gear ratio, a stroke length, a flow rate), and each dimension carries its source tag
   (`[PRIMARY · URL · date]`, as every factual line here does).
5. **Every figure on screen is a claim.** It goes through `claims_lint.py` like the narration, and the
   sound-off check (`soundoff.py claims`) treats it as a number the viewer reads.
6. **One driver.** The mechanism moves from one value over time (a crank angle, a valve position), named in
   the spec. Titles and sounds anchor to the times of that driver's events, written in the spec: a built shot
   knows its own events exactly, so its sound placement takes them from the spec rather than from detecting
   motion in pixels (which is what `sfx_conform.py events` does for footage).
7. **The working part reads.** Choose the view where the part that does the work is not hidden by another
   moving part (`references/blocking.md` §4, critique question 9). If it is hidden for more than half the
   move, change the view; a label does not fix a view.

Labels with leader lines and numbered step chips need an explainer title lane, which waits on the owner's
answer to Q2 (may a leader line follow a moving part in our own 3D, or only point at a static spot?).
The step chips stay deferred unless the job's CHECKPOINT carries the `step-lower-thirds` switch
(`assets/project-switches.json`): a native Text+ lower third per step, on the shot each step or tip names, with
no leader line. Leader lines still wait on Q2, and card words that did not read stay unread (v2.48.0, switch
`step-lower-thirds`).

## Definition of Done — Mode C

Every factual claim sourced in the script file · load-bearing claims attributed on screen · no
adjacency that converts a general fact into a product claim · numbers readable, not just spoken ·
one idea per beat · a turn, not a hard sell · the sound-off check logged (`references/sound-off-story.md`) ·
spec-compliant export.

**Cross-refs:** `references/ideation.md` (finding the question worth answering) ·
`references/script-craft.md` (writing narration for the ear) ·
`references/persuasion-psychology.md` §1 (why numbered beats hold attention) ·
`references/compliance.md` (net impression; the claims lint applies here too) ·
`references/realism-qa.md` · `references/editing-and-audio.md` · `modes/ugc-volume.md` (when the
editorial piece is one row in a monthly batch) · `references/product-video.md` (when the subject is a
product's own interface: real UI captures, the demo and explainer beat maps, text over UI).
