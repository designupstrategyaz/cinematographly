# Mode routing index

Pick the mode from the **shape of the ask**, not the subject matter. One brand can need all four;
a sleep brand can need all four. Adding a mode is a table row plus one file, never a core-skill edit.

| The brief looks like… | Mode | File |
|---|---|---|
| One video that has to carry the message. A character, a story, a launch, a recurring-cast episode. "Make this one really good." | **A · Narrative Promo** | `modes/narrative-promo.md` |
| A monthly number. Multiple brands or SKUs, buyer personas, an archive to draw on, hook testing, paid social, "native, not obvious AI." | **B · UGC Volume** | `modes/ugc-volume.md` |
| Information first. An editorial topic, a category explainer, a comparison, a social-search answer. The payload is a claim about the world, not a product. | **C · Editorial / Explainer** | `modes/editorial-explainer.md` |
| The footage already exists. Teasers, shorts, fact-cards, alternate hooks, re-crops. "More from what we already made." | **D · Repurpose** | `modes/repurpose.md` |
| Still images only — website heroes, product cards, marketing stills. No motion, no voice, no cut. | **S · Stills** | `scripts/gate.py` — `Format: stills`; one `brief` approval (an artifact naming every still ID) replaces concept → script; then `frame:<ID>` → `export`. Video/audio calls are denied |

## Routing rules

1. **Count the deliverables.** One → A or C. Many, on a recurring cadence → B. From existing
   footage → D.
2. **A brief can be more than one mode.** A trial of 8 videos across 2 personas is Mode B (it's a
   batch, and the system is what's being evaluated) even though 8 is a small number — the client is
   testing whether you have a repeatable process, not whether you can make eight good videos.
3. **Mode B contains the others.** A monthly batch may include editorial rows (Mode C's structure) and
   repurposed rows (Mode D's rules). Run the batch as B and borrow the row-level discipline.
4. **When genuinely ambiguous, ask.** The cost of guessing is a whole pipeline's worth of wrong-shaped
   work. One question — "is this one hero piece or the first of a recurring set?" — settles it.
5. **State the mode in the brief note** so the choice is auditable and a later session doesn't re-litigate it.

## What is shared across all four

The mode changes the *pipeline shape and the gates*. It does not change:

- the craft (`references/craft-cheatsheet.md`),
- the generation method and guardrails (`references/ai-generation.md`),
- realism QA (`references/realism-qa.md`),
- compliance (`references/compliance.md`),
- the edit, mix, captions, and export (`references/editing-and-audio.md`),
- folders, naming, and the board (`references/pm-workflow.md`),
- the client profile, which overrides all of the above (`clients/<brand>.md`).

## Adding a mode

Copy the shape of an existing mode file: when to use / when not to · what changes vs the other modes ·
the pipeline and its gates · the mode-specific rules · a Definition of Done · cross-refs. Add a row
above. Do not fork the shared references — if a mode needs different craft advice, that advice
probably belongs in the shared reference with a condition on it.
