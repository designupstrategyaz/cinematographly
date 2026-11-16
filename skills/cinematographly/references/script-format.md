# Script Format — the short-form house style

The shape every character-driven promo script takes. Follow it so a series stays consistent and so
downstream stages (storyboard, generation, edit) can read the script without guessing.
**Language, character names, brand facts, and worked examples are in the client profile**
(`clients/<brand>.md`); this file is the reusable structure. A blank version is in
`../assets/script-template.md`.

## ⛔ The scene count is DERIVED. It was never a house rule

The template used to show **four scenes**, and four is not a general answer to anything — it was one
retired client's format lock for a ~60s two-hander, and it survived into the template because **a
number in an example looks like a rule.** Nothing in film, advertising or this skill's own sources
prescribes four beats for a short.

What the count actually is:

```
body   = runtime − hook − cta
scenes = round(body / beat_seconds)
```

Run that with the retired client's own numbers — 64s runtime, 6s hook, 5s CTA, ~13s beats — and it
returns **4**, with timecodes matching the old template to the tenth of a second. **The template was
the output of a calculation nobody had written down.** It was right for that brief and wrong as a
default, and the only way to tell those apart is to compute it:

```
python3 scripts/beat_plan.py plan --client <brand>
python3 scripts/beat_plan.py plan --runtime 45 --hook 4 --cta 5 --beat 11 --speakers 1
```

⛔ **The FUNCTIONS are fixed; the COUNT is derived.** Every script needs a hook, at least one beat
that turns a value, and a resolve into a CTA. How many turning beats fit is a property of the
runtime — a 35s monologue comes back as 3, a 20s cut as 1, and neither is a worse script for it.

⛔ **`beat_plan.py` refuses to invent the numbers.** `runtime_target_s`, `hook_seconds_min`,
`cta_seconds` and `beat_seconds` live in `clients/script.<brand>.json`, because a 6-second hook floor
is right for one brief and fails every script in another. There is no house default and the tool will
not supply one.

**Where `beat_seconds` comes from:** it is a measurable house fact — time one finished scene, wall to
wall, across a few episodes. Until it is measured it is an estimate, and the plan inherits that
uncertainty honestly rather than hiding it in a template.

## The template

The structure below is the **shape**; the number of `[SCENE]` blocks comes from `beat_plan.py`.

```
# <Program / Offer> — <Audience segment>
Script v<N.n> · ~<duration>s · <aspect, from the client's format block> · <language> · <brand>

## Brief
<one or two lines: offer, audience, any hard mandatory (dates, codes, CTA); who briefed it; assumptions>

## Control idea (one sentence)
<the meaning the whole video proves, e.g. "X wins when the skeptic takes the zero-risk step.">

## Dramatic question
<the single thing the viewer wonders and sees answered>

## SCRIPT
<timecodes and block count from: scripts/beat_plan.py plan --client <brand>>

[HOOK 0:00–<hook_end>]  <the conflict, not the demographic — it buys the next beat>
<TEXT record: "<the card this client's format carries — written, not rendered>">

[SCENE 1 — <start>–<end>]  ESTABLISH — <location / visual>. the situation the hook promised, made concrete
carried by: <line | object | face | withheld | sound — when an object says what a line would, cut the line>
<CHARACTER A>: „<line, within the client's word budget>"

[SCENE n — <start>–<end>]  TURN — <location / visual>. one value changes (skepticism→interest, worry→relief)
carried by: <…>
<CHARACTER B>: „<line>"

  … as many TURN beats as the runtime holds — two, or none, or five …

[SCENE N — <start>–<end>]  RESOLVE — <location / visual>. the value lands; proof if the mode uses it
carried by: <…>
<CHARACTER A|B>: „<resolve / social-proof line>"

[CTA <cta_start>–<runtime>]  <the resolved state, in-world branding>.  <one ask + any real deadline>

## B-roll inserts   (≥ one per dialogue clip, ideally +2; include an S0B establishing shot)
## End frames / camera (max ~2 signature moves)
## Wardrobe
## Director's note  (the expression arc; the brand's tonal locks)

_Saved: <profile production path>/SCRIPT-<SLUG>-v<N>.md_
```

⛔ **A scene that turns nothing is a scene to cut, whatever the arithmetic says.** The calculation
sizes the container; it cannot tell you the beats are any good. That is `script-craft.md` and a read
aloud.

(Use whatever scene label the language wants — e.g. "SCENĂ" in Romanian. The profile sets the
language, the character names and the speaker count; a monologue has no alternation to keep.)

## What makes each field pull its weight

- **Timecodes** keep you honest on length (~150 spoken words/minute; a 60s script ≈ 140–170 words).
> ⛔ **Every number in this section is per-client.** The reasoning is portable; the figures are not.
> Set them in `clients/script.<client>.json` — `script_score.py` and `beat_plan.py` both refuse to
> run without them rather than assuming a default.

- **A hook needs enough screen time to be read and understood, and 3s is not it.** Text that flashes for 3 seconds reads
  as a glimpse, not a read — people need actual time to parse the words before the cut. Budget the
  hook from the client's `hook_seconds_min` (there is no house number, see above) and let it eat into the total
  runtime rather than the read time.
- **TEXT lines are a record of the approved format, not a render instruction.** On-screen overlay
  windows and CTA cards are off by default across this skill — **burnt-in captions carry the scannable
  facts for sound-off viewers.** Keep writing the TEXT lines where a client's format expects them;
  just never build them unless that client's profile explicitly asks. (See `editing-and-audio.md`.)
- **One character per scene, alternating** keeps the banter rhythm — *in a two-hander*. A UGC
  monologue has no alternation to keep; its rhythm test is inevitability (no two adjacent lines
  could swap order), `script-craft.md` §6 dimension 5.
- **End frames** flag the one or two camera moves worth designing (you storyboard them in Stage 2).
- **Director's note** protects the tone — the character arc and the brand's tonal locks.

## Duration & B-roll (run these defaults every time)

**Figure out the length before you fall in love with the words.** Count spoken words and convert
to time — don't eyeball it:

```
python3 scripts/estimate_duration.py path/to/SCRIPT.md
```

It prints per-scene and total speech seconds (2.4 words a second plus 0.6 s a line, an assumed rate; the same
figures `script_score.py`'s two clocks and `beat_plan.py`'s word budget use), a
**recommended video length**, the **clip count** (one line = one clip; two speakers = two clips),
and the **credit cost + Quality-vs-Economy**. Target the **runtime window in the client profile**
(one dialogue series ran ~60s; a volume UGC brief, 35–55s) — there is no house length; trim a line or a
scene if it runs over.

**What real spots spend, for reference** [MEASURED · script corpus 2026-11-05, `script-craft.md` §2d,
`assets/script-bands.json`]. These are not targets:
- **15 s spot:** 35–45 spoken words.
- **30 s spot:** 37–81, median 63.
- **Pace:** 2.2 words a second (1.15–2.83). Award-annual spots run about 1.8 and leave the rest to picture.
- **Supers:** a TV spot carries about 3.
- **Direct address:** "you / your" runs about 3.4 per 100 spoken words on TV and about 8 in social scripts.

`script_score.py` prints these beside the script's own numbers. `beat_plan.py` prints where the CTA falls against
real spots: in 15–30 s spots the spoken CTA starts in the last eighth of the words; in 60–120 s films it is mostly on
the end card.

**B-roll: cut ≥ as many inserts as dialogue clips, ideally +2 for options.** Always open with an
**intro / establishing B-roll (S0B)**. B-roll gives variety, lets you cut to the music, and covers
lipsync mismatches.

## The dramatic engine (why the format works)

Each scene should **turn a value** (skepticism → interest, worry → relief) — that's the gap
(McKee) that pulls the viewer. Open with a hook of the length the client profile sets (never shorter — the
viewer needs time to actually read it, not just glimpse it); pose one dramatic
question by ~0:15–0:20 and answer it by ~0:55–1:00; end on a single CTA **button**, not a summary. Write for
the ear and the eye at once: short spoken sentences, natural rhythm, every line sitting on a
concrete visual. For the brand's specific characters, tone, offer, and 1–3 worked example scripts,
read the client profile.

## Higher-craft moves (retention) — verified 2026

These lift a script from "clear" to "magnetic." **They change the words/structure, so they apply to
NEW scripts and clients whose copy is open — not to a client whose script + audio are locked (check
the profile's `⛔ hard locks` section first).**

- **Curiosity-gap hook, not audience-naming.** Early seconds carry most of the recall impact (the
  sourced figures and their limits are in `hook-craft.md`; the old "3 seconds decide >70%" claim is not
  citable). "Are you a farmer?" is a *filter* — it
  lets non-farmers leave. Open on drama with a withheld answer: a character mid-emotion + a card
  like "The €50,000 mistake." The hook is the *conflict*, not the demographic. Budget the hook at
  **~6 seconds** — around 90% of ad-recall impact lands in the first six; the 3-second figure people
  quote is a retention *measurement point*, not a hook length.
- **Value-turn as a visual reaction, not a traded line.** Script the *silent* beat — a look at a
  crumpled bill, the brow unfurrowing, *then* the line. The audience discovering the shift
  (skepticism → hope) on a face is the retention hit, and it generates better than a talking head.
- **Character signature.** Give each recurring character one repeatable non-verbal bit (a specific
  wink sequence; polishing glasses on a tie before caving). It becomes a series hallmark viewers wait
  for. (Non-verbal → safe even for locked-audio clients.)
- **CTA as narrative payoff.** Resolve the dramatic question visually (a time-jump to the solved
  state) with in-world branding over a living scene, rather than a static end card the viewer is
  trained to skip — and which this skill does not render by default anyway.
- **Test the hook (cheap, high-leverage).** Cut 3–5 hook variants (a different opening B-roll, or a
  different first line where copy is open) onto the same locked body and A/B them — a native split-test,
  or organically post variants a few hours apart and keep the best 3-second retention. Hook-only tests
  resolve in 2–3 days rather than 5–7 and cost far less per learning, because only the first seconds
  change. (For locked-audio clients, vary only the B-roll, never a spoken line.) At volume this becomes
  a standing **hook bank** — see `modes/ugc-volume.md` §5 and `assets/hook-bank-template.md`.

## Quick self-check before you call a script done

- One dramatic question, posed by ~0:15, answered by ~0:55?
- Every scene turns a value?
- Line lengths inside the measured bands in `script-craft.md` §2d (not a flat 10–15 words), natural spoken delivery, correct diacritics for the language?
- Each line has a concrete visual to sit on?
- Exactly one CTA, with any date/claim verified against the profile?
- Character arc lands; the brand's tonal locks (e.g. an honest wink) respected?
- Ran `estimate_duration.py --client <name>` — total inside the profile's runtime window, clip count known, within credit envelope?
- Hook held for at least the profile's hook floor (`clients/script.<client>.json`), not a flashed 3s?
- B-roll planned ≥ dialogue clips (ideally +2), plus an S0B intro?
