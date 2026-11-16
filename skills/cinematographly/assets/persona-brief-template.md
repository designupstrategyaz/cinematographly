# Persona — <NAME / CODE>
Brand: <brand> · Mode: B (UGC Volume) · Drafted <date> · Confirmed by <client contact / ASSUMED>
Evidence: <[PRIMARY|SECONDARY · source · YYYY-MM-DD] the review, support or search text this person is drawn from>
(v2.69.0: a T2 persona carries at least one sourced evidence line; `ASSUMED` above says who confirmed it, never that
nothing was found. Advice only: no check reads this line yet. `preproduction-research.md` §2.1b)

> A persona is **a person with a problem and a reason to distrust the category** — not a demographic
> bracket. If this sheet could describe 40% of the population, it isn't finished.

## Who they are
- **One line:** <"a 34-year-old who has tried four sleep things and quit all of them">
- Life context that matters to the purchase: <work pattern, household, budget reality>
- What they already believe about this category: <the prior you're arguing with>

## The problem, in their words
- <a sentence they would actually say out loud. Not marketing language>
- When it shows up: <the specific moment — 3am, Sunday night, the school run>

## The objection that stops them buying
- <the real one, not the polite one>
- What has burned them before: <the previous product, the previous claim>

## Vocabulary
- **Words they use:** <…>
- **Words they'd never use:** <category jargon, brand language, "wellness journey">

## The world on camera
- **Setting(s):** <bedroom / kitchen counter / car / bathroom mirror — real rooms, with mess>
- **Wardrobe:** <specific and unglamorous>
- **Time of day / lighting:** <named source + rough Kelvin>
- **The imperfection:** <the one thing in frame that makes it a real room>

## Voice
- **Voice / actor:** <locked voice id or archive creator>
- **Register:** <tired-honest / dry-funny / warm-practical>
- **Delivery notes:** <pace, where the disfluency sits, what they'd hedge on>
- **Tags to use:** <the expressive tags that fit this person>

## How they move (the movement persona)
Every clip of this person carries the `MOVES LIKE:` line below, word for word, in `[MOTION]` or
`[PERFORMANCE]`, and the clip prompt names `persona: <name>`; `prompt_lint.py` checks it. The shot's
`INTENT:` shifts this baseline; it does not replace it (`references/acting-for-the-model.md` §7b).
- **MOVES LIKE:** <one line: "brisk and economical, a mother of three who never wastes a move">
- **Baseline energy and tempo:** <1–5, and the rhythm: quick and even / slow to start, then decisive>
- **Body:** <posture, where the weight sits, where the tension lives: shoulders, jaw, hands>
- **Hands with objects:** <how they handle things: brisk and sure / careful / fidgety / one-handed while doing something else>
- **Signature gestures:** <two or three, specific: "pushes her glasses up with a knuckle", "taps the lid twice">
- **Face at rest, and their tell:** <what the face does when nothing happens, and the small sign of a decision>
- **How they react:** <fast or slow, big or small, toward or away>
- **Never does:** <the moves that would break the person: "never slow, never graceful, never poses for the lens">

_Saved as `_reference/PERSONA-<name>.md` in the job when the person is cast in clips._

## Presenter strategy for this persona
- [ ] Archive-led (client footage) · [ ] AI presenter · [ ] Mascot/character · [ ] Faceless
- Reason: <why this one, per `modes/ugc-volume.md` §6.1>
- Identity lock: <Element id / hero reference file / n-a>
- Disclosure required: <dramatization? AI label? — per `references/compliance.md`>

## Angles this persona can carry
| # | Angle | Body it pairs with | Hook types that fit |
|---|-------|--------------------|---------------------|
| 1 | <…> | <B1> | <curiosity gap, skeptic> |
| 2 | <…> | <B2> | <POV, day-in-the-life> |

## What this persona must never say
- <claims outside their credibility — a layperson doesn't say "clinically proven">
- <anything on the brand's restricted list; see the compliance sheet>

_Saved: <production-root>/00-batch/PERSONA-<BRAND>-<NAME>.md_
