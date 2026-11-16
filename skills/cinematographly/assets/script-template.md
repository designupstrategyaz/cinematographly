# <PROGRAM / OFFER> — <Audience segment>
Script v0.1 · <runtime, from the client profile> · <aspect — from clients/<brand>.md §5> · <language> · <brand>

<!-- Load clients/<brand>.md for the language, character names, tone locks, and worked examples. -->

## Brief
<offer · audience · hard mandatory (dates, codes, CTA) · who briefed · your assumptions>

## Control idea (one sentence)
<the meaning the whole video proves>

## Dramatic question
<the one thing the viewer wonders and sees answered>

## SCRIPT

<!-- Paste the block headers from `scripts/beat_plan.py plan --client <brand>`: the scene count and the
     timecodes come from the runtime, not from this example. script_score.py sets each block's speech
     against its timecode (v2.67.0). -->

[HOOK 0:00–0:06]  <the hook beat — conflict, not demographic; the length is the client's, not a house number>
carried by: <line | object | face | withheld | sound>
<TEXT record: „<the card this format historically carried — written, not rendered>">

[SCENE 1 — 0:06–0:19]  <location / visual>.  TEXT: „<on-screen fact>"
carried by: <…>
<CHARACTER A>: „<line, within the client's word budget>"

[SCENE 2 — 0:19–0:34]  <location / visual>. No line: an object or a face carries this beat (cut the line
when an object says it; references/emotional-journey.md §5.2)
carried by: object — <what the viewer sees that says it>

[SCENE 3 — 0:34–0:46]  <location / visual>.  TEXT: „<on-screen fact>"
carried by: <…>
<CHARACTER B>: „<the turn or the button — where a sentence of theirs carries most weight>"

[CTA 0:46–0:52]  <the resolved state, in-world branding>.  <CTA line + any real deadline>

## B-roll inserts  (≥ one per dialogue clip, ideally +2; include an S0B intro drone)
- S0B: <intro / establishing drone>
- <...>

## End frames / camera (max ~2)
- <...>

## Wardrobe
- <Character A>: <...>
- <Character B>: <...>

## Director's note
- <Character> arc: <skeptical → warm>
- Tonal locks (from the profile): <e.g. closing wink = "good deal", not "gotcha">

## Character blocks (paste verbatim into every AI prompt — keep identical across episodes)
- <CHARACTER A>: <fixed species/build/wardrobe/colors/badge description>
- <CHARACTER B>: <fixed species/build/wardrobe/colors description for this role>

## Compliance check (claims-sensitive categories)
- Run `python3 scripts/claims_lint.py THIS-FILE.md` → every hit reframed or client-approved.
- Required disclaimer/disclosure identified and placed.

## Duration & cost check
- Run `python3 scripts/estimate_duration.py THIS-FILE.md` → total ≤ ~60s; note clip count + credits.

_Saved: <production-root>/Proiect-Video-<N>-<SLUG>/SCRIPT-<SLUG>-v<N>.md_
