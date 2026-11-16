# Brand System — a video series is a design system, so run it like one

A one-off video needs taste. A **series** — twelve episodes of a recurring cast, or forty UGC videos
a month across five brands — needs a *system*, or it drifts: the palette wanders, the characters go
off-model, captions change size, and by month three nothing looks like it came from the same place.

Design systems solved this problem in interface work, and the structure ports almost directly.
Self-contained; sources named inline for provenance (Couldwell, *Laying the Foundations*; Mahon,
*Art Direction*; Shaw, *Design for Motion*).

---

## 1. The five layers, ported to video

Couldwell's foundations model is **Foundations → Components → Patterns → Templates → Pages**. For a
video series:

| Interface layer | Video equivalent | What lives there |
|---|---|---|
| **Foundations (tokens)** | **Look tokens** | Palette hexes, the held grade, caption type block, loudness target, delivery format, character wardrobe blocks, the negative list |
| **Components** | **Shot types** | The dialogue MCU, the establishing drone, the product macro, the reaction cutaway — each with its prompt block, framing, and lighting recipe |
| **Patterns** | **Scene shapes** | Two-speaker exchange (= two clips), demo beat, objection-and-answer, the value-turn |
| **Templates** | **Formats** | The 4-scene narrative promo, the hook×body×CTA UGC row, the three-beat explainer |
| **Pages** | **Episodes / videos** | The actual videos, with real content in the template |

**The point of the ladder is propagation.** Change a token — the caption face, the grade, a wardrobe
detail — and it should change everywhere, because everything downstream references the token rather
than restating it. In practice that means the token lives in **one** place (`clients/<brand>.md` §6,
the Visual Bible) and every prompt, shotlist and edit reads it from there.

## 2. Tokens — name the value, don't restate it

A token is a **named design value with one source of truth** (Couldwell F11). The failure mode
without them is exactly what this skill kept hitting: the same number written into prose in four
files, three of which go stale.

The video token set, minimum viable:

```
COLOUR      brand.primary #______   brand.accent #______   grade.name  ______
            caption.fill #______    caption.plate #______  (tonal contrast checked)
TYPE        caption.face ______ / weight ___ / size ___ / leading ___ / tracking ___
            caption.case sentence   caption.align ______
FORMAT      delivery.preset ______  (assets/delivery-formats.json)
            generation.resolution ______   timeline.fps ___
AUDIO       loudness.target ___ LUFS   truepeak.max ___ dBTP
            music.duck ___ LU below speech (≥ 10; product-video.md §5)   ambience.bed ___ LU below speech (≥ 15)
CAST        <character>.wardrobe "<verbatim block>"  .reference <file>  .voice <id>
WORLD       settings[] with light source + Kelvin + prop list + the imperfection
NEGATIVE    what never appears in frame for this brand
```

**Rules that make tokens work:**

- **A number in prose is not a token.** If a value appears in two files, one of them is wrong soon.
  Cost values already follow this discipline (`clients/costs.<brand>.json` is the source, and the
  prose says so); the look tokens should too.
- **Name by role, not by appearance.** `caption.fill`, not `white`. The day it stops being white,
  the name still works.
- **Version a breaking change.** A palette change mid-series is a breaking change: it makes new
  episodes not match old ones. Decide deliberately whether the series re-grades or forks.

## 3. Components — a shot type is a reusable unit

A component is a **single reusable unit with a consistent interface, behaviour and styling**, and
updating it propagates (Couldwell F3). A shot type is exactly that: a named framing + lighting +
prompt-block recipe that produces a consistent result across episodes.

Worth defining as components for most brands:

- **Dialogue MCU** — the workhorse. Framing, lens feel, eyeline convention, the `[SPEECH]` block.
- **Establishing / intro insert (S0B)** — opens the film.
- **Product macro** — the real asset composited onto the start frame, never model-rendered.
- **Reaction cutaway** — the lipsync-rescue and pacing tool.
- **The button** — the final held beat the cut ends on.

Each gets: its purpose, its framing, its prompt skeleton, its known failure mode, and its QA note.
Keep them in the client profile beside the tokens. **A new episode should be assembled mostly from
existing components**, with novelty reserved for where the story actually needs it — that is what
makes a series cheap to produce and recognisable to watch.

## 4. Patterns and templates

**Patterns** are multi-component combinations that solve a recurring problem: the two-speaker
exchange is two dialogue-MCU components plus the one-line-one-clip rule; the objection-and-answer is
a reaction cutaway between two dialogue components.

**Templates** are the mode-level formats — the 4-scene narrative promo, the UGC hook×body×CTA row,
the three-beat explainer. They already live in `modes/`. Recognising them as templates is what lets
you say "this brief is a known template with new content," rather than designing from scratch each
time.

## 5. Governance — who decides, and how a change lands

A system without governance decays into a folder of assets (Couldwell F5–F6). For a small team the
whole apparatus is three rules:

1. **One owner per brand's Visual Bible.** Changes go through them.
2. **A change is proposed, not applied.** New token, new component, or a variation on an existing
   one — write what changes and why, then decide. This is the same discipline as
   `self-evolution.md`, applied to the look rather than to the skill.
3. **A variation used twice is a component.** The third time you write the same ad-hoc prompt
   variation, it stops being a one-off and gets a name, a definition, and a place in the profile.
   Otherwise the system stays small on paper and sprawls in practice.

## 6. The drift audit — run it per series, not per video

Adapted from the interface-audit method (Couldwell F4): the point is to find **unintentional
variation**, which is invisible one video at a time and obvious across a set.

Every ~10 videos, or at the end of a monthly batch:

- **Contact-sheet the set** — `scripts/contact_sheet.py --folder <clips> --first-frame-only` builds
  the grid (one frame per clip, sampled at t=0.5s, past the morph-settle). One frame per shot type,
  all episodes, side by side: drift that is invisible in sequence is loud in a grid.
- **Count the variants.** How many distinct caption sizes are actually in use? How many greys? How
  many wardrobe versions of the same character? Each unintended variant is either a token violation
  or a missing token.
- **Check the tokens against reality.** Does the palette in the profile match what shipped?
- **List what is used but undefined** — the ad-hoc shot types that have quietly become standard.
  Promote them.
- **List what is defined but unused.** Dead tokens and components are cost with no benefit; remove them.

Output is a short list of: violations to fix, variants to consolidate, components to promote, dead
weight to delete. Log it as an episode note (`memory/episodes/`) so it feeds the skill's own loop.

## 7. The look is the differentiator — "the right kind of wrongness"

The system exists to hold something worth holding. Mahon's argument: when competing brands offer
near-identical benefits, **the brand's look becomes the differentiator** — "origination, not
imitation." Al Young's phrase for finding it is *the right kind of wrongness*: the one thing that
does not fit the category's generic template but does fit this brand's character.

Two practical consequences:

- **Decide the wrongness deliberately, then tokenise it.** A cartoon animal in business dress selling
  insurance is a right-kind-of-wrongness. So is a wellness brand shot on obviously imperfect phone footage while
  the category shoots glossy. Whatever it is, write it down — otherwise it erodes toward the
  category mean one small decision at a time.
- **Consistency is what converts a look into recognition.** A distinctive look used inconsistently
  is just noise. This is the whole argument for the system.

## 8. Where it lives

`clients/<brand>.md` §6 is the Visual Bible: tokens, components, settings, cast blocks, negative
list. `assets/delivery-formats.json` holds the format tokens. `clients/costs.<brand>.json` holds the
cost tokens. Nothing else restates any of them.

**Cross-refs:** `production-design.md` (what the tokens describe) · `typography-and-captions.md`
(the type tokens) · `delivery-format.md` (the format tokens) · `ai-generation.md` (identity lock and
the prompt blocks components are made of) · `realism-qa.md` §5 (batch variance — the deliberate
opposite of drift) · `self-evolution.md` (the same propose-then-promote discipline, one level up) ·
`clients/_TEMPLATE.md` §6.
