# Mode D — Repurpose

**Use when:** the footage already exists. Cutting a shipped video into teasers, shorts, fact-cards,
alternate-hook variants, or platform-specific re-crops. Also the right lane when a client asks for
"more from what we already made" or when a hero film needs a supporting set.

**Why it's a mode and not a footnote:** it is the cheapest volume in the whole skill — roughly the
cost of an edit, no generation — and it is the correct answer far more often than "make another one."
For a locked-audio client it is often the *only* way to add volume.

## Files this mode requires — read before the artifact, not instead of it

Beyond SKILL.md §2's ladder (stages 0, 7 and 8 apply; 3–6 usually do not): `references/editing-and-audio.md`
· `references/editing-storytelling.md` (what a cut can and cannot change about meaning) ·
`references/delivery-format.md` §2–§3 (a re-crop changes the craft, and the safe zones move) ·
`references/typography-and-captions.md` · `references/compliance.md` §4 (a re-cut can create a claim
the original did not make) · `references/revisions.md`. **The gate still applies to any NEW
generation** a repurpose needs (an alternate hook's fresh shot is a Mode A/B shot with a job open);
pure re-cuts need the checkpoint (`Mode: D`) and the export approval, nothing more.

---

## The standard set from one ~60s hero

| Cut | Length | Made from | Notes |
|---|---|---|---|
| **Hero** | 35–60s | the original | the reference version |
| **Teaser** | 15–20s | scenes 1–2 + CTA | the strongest single value-turn, then out |
| **Character shorts** | 7–10s | one line + its B-roll | 2–3 of these; each must stand alone |
| **Fact card** | 10–15s | one claim + B-roll + VO segment | reuse the original VO segment unchanged |
| **Alternate hook** | full length | new opening, same body | the cheapest real A/B you can run |
| **Platform re-crop** | as needed | reframe | check safe zones per platform, not once |

Each is ~5% of the original's cost (edit and possibly a VO segment), and together they multiply
posting volume without multiplying generation credits.

---

## Rules

1. **Every cut must stand alone.** A 9-second short that only makes sense if you saw the hero is not
   a short, it's an offcut. Test: does it open on something and land on something?
2. **Reuse VO segments unchanged where the audio is locked.** Re-cutting is allowed; rewording is a
   new approved script, not an edit.
3. **Re-run the compliance gate on every cut.** A claim that was safe *in context* can become
   unsupported when the context is trimmed away — the qualifier is often the first casualty of a
   15-second cut. **This is the single most common repurposing failure.** In particular: if the
   original stated the typical result next to a dramatic one, the short must carry both or neither.
4. **Re-check the disclosure.** A dramatization or AI-disclosure label that appeared at 0:02 of the
   hero must appear at frame one of every derivative.
5. **Re-check safe zones per platform**, not once for all of them — and run T1 of the sound-off test on every
   derivative's muted proof: a re-crop moves the captions (`references/sound-off-story.md`; the hero's T2 holds
   only while the derivative's picture is the hero's picture).
6. **Version the exports properly** — a derivative is not a `v2` of the hero; it gets its own slug
   (`<SLUG>-teaser`, `<SLUG>-short-1`) so the ledger and the board stay legible.
7. **Vary the derivatives' durations.** Three 15-second cuts of identical length from one source read
   as a template (`realism-qa.md` §5).

---

## A generative reframe — when the crop would cut the action

A 16:9 master going to 9:16 normally gets a crop, and the crop is the safe answer when the action sits
in the middle third. When it does not (two people at the frame edges, a wide that IS the shot), the
alternative is to keep the whole 16:9 picture and **generate bands above and below it** — mode F of
`references/real-and-ai.md`, so the disclosure rule for an AI-altered plate applies (§5 there), and it
is a NEW generation: `reframe` / `outpaint_image` are spend tools, so a job is open and the gate runs.

`[SECONDARY · higgsfield-timed-prompts skill §9, file dated 2026-10-06 — a practitioner method; the
arithmetic is computed here]`:
- **Measure the edit first**: `ffprobe`, the scene cuts and a 1 fps contact sheet give the shot list
  with cut times. The reframe prompt goes shot by shot.
- **The band maths.** Fit the source to the output **width**; the bands share the rest:
  band = (output height − output width × 9/16) / 2.
  - 1080×1920: the source becomes 1080×608, with **656 px** above and below.
  - 1080×1080: the same 1080×608, with about **236 px** above and below.
  - Round once and use the same numbers for every frame. The source is scaled uniformly; it is never
    cropped, zoomed, re-centred or animated.
- **The bands are environment only**: ceiling or sky above, floor or table below. No new people,
  hands, faces, animals, food, phones, screens, text or logos, and no copies of what is already in
  the picture. A body cut by the frame edge continues as clothing only.
- **The cuts stay where they were**: the same cut frames, a hard cut stays hard, a camera move carries
  into the bands with its parallax.
- **Audio is the source track, passed through**: nothing generated, and the prompt says so per
  category (music, ambience, foley, voices, effects).
- **QA**: seams, anything new in a band, and whether the tool obeyed the fit. If the tool's own fit
  or fill setting still crops or moves the source, that setting overrides the prompt. Replacing the
  audio track in the edit is the safe fallback for the sound.

---

## When repurposing is the wrong answer

- The original underperformed. Repurposing a loser produces more losers — the body was the problem.
- The client wants a *new* angle or persona. That's new production; say so rather than dressing up a
  re-cut.
- The archive footage's licence doesn't cover the new use (organic → paid is the usual trap).

## Definition of Done — Mode D

Each cut stands alone · compliance gate re-run per cut, not inherited · disclosure present from frame
one on every derivative · safe zones checked per platform · T1 logged per derivative
(`references/sound-off-story.md`) · durations varied · exports slugged
distinctly · costs logged against the original's project.

**Cross-refs:** `references/editing-and-audio.md` · `references/compliance.md` §6 ·
`references/pm-workflow.md` (naming) · `modes/ugc-volume.md` §8 (feeding results back).
