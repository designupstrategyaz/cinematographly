# Mode A — Narrative Promo

**Use when:** one video has to carry the message. A character-driven ~35–65s promo, a recurring-cast
episode, a brand or campaign hero piece, a launch film. Signals: a named cast, a story, a single
deadline, "make this one really good."

**Do not use for:** a monthly volume target — that's Mode B (`ugc-volume.md`).

## Files this mode requires — read before the artifact, not instead of it

Beyond SKILL.md §2's ladder (which applies unchanged): `references/emotional-journey.md` §1–§3 (the
map is the spine of a hero piece) · `references/direction.md` §1–§3 · `references/shot-handoff.md`
§3, §5 · `references/script-craft.md` §2b (the beat/turn/chain layer) · `references/prompting-craft.md`
§1, §6b · `references/series-continuity.md` when the cast recurs · `references/micro-drama.md` when the
piece is a short-drama episode (four parts, a cliffhanger, a series) · `references/multishot.md` when a
clip cuts inside one generation. Artifacts the gate expects from
this mode: the checkpoint (`Mode: A`), the scored script, a shotlist with a performance card per
dialogue clip, a linted frame prompt and a linted clip prompt per shot.

This is the skill's original lane and its deepest one. The craft reference behind every choice here
is `references/craft-cheatsheet.md`.

---

## The pipeline — eight gated stages

Every video is one PM **parent task** with these eight **subtasks**, run in order:

| # | Subtask | You produce | Gate before moving on |
|---|---|---|---|
| 1 | 📋 Brief & Script | Final script in the house format | Answers the one question, ends on a button, claims verified, length ≤ target |
| 2 | 🖼️ References & Storyboard | Shotlist + refs, one row per shot, **blocking card per scene, performance card per clip** | Each line mapped to ≥1 shot; coverage floor met (reaction per exchange); B-roll ≥ dialogue clips (+2); 180° & eyelines per the blocking card |
| 3 | 🤖 AI Generation | Start frames → clips per shot, payloads logged to the shot manifest | Characters consistent; brand-safe; within budget; per-clip QA card passed; **selects pass done — retakes decided here, not in the edit** |
| 4 | 🎙️ Voice & Audio | Character voices + SFX | Lines match the final script; consistent per-character voices |
| 5 | 🎵 Music | Bed track **chosen by the user** (never autonomously), BPM noted | Mood fits; licensed; looped to length if shorter than the video |
| 6 | ✂️ Assembly & Edit | Cut, beat-matched, captions | Cuts on action/beats; lipsync verified by listening; −14 LUFS; mobile-legible |
| 7 | ✅ Branding Check | Compliance pass (profile non-negotiables + `compliance.md` where the category needs it) | All pass |
| 8 | 📤 Export | Final file in the client's delivery format + publish handoff | Matches the profile's format block; `export_qc.py --format <preset>` PASS; ready for the target channel |

**Lipsync ordering exception:** for a dialogue clip using generation-side (audio-driven) lipsync,
record the line's **voice (Stage 4) before generating that clip (Stage 3)** — the mouth is animated to
the real audio. Do the voice for all dialogue lines up front, then generate. Edit-side cut-to-picture
is the fallback and keeps the plain 3→4 order.

Stage detail, output organization, and the reusable template task are in `references/pm-workflow.md`.

---

## Stage 0.5 — the angle

If the brief arrives without one, find it before writing: `references/ideation.md`. Ten concepts
before evaluating any, the five-line concept format with a **named picture**, and the four-frame test.
A script written from a thin angle cannot be rescued by craft.

## Stage 1 — Script (80% of the value)

Structure it as **hook → N turning scenes → CTA**, where ⛔ **N is derived, not chosen**:
`scripts/beat_plan.py plan --client <brand>` divides the body time by the client's beat length.
Each scene is a location plus one character's line (alternating, in a two-hander). The engine is
**the gap** — a skeptic reframed — and every scene must **turn a value**.
⛔ **Do not copy a scene count from another brief.** `script-format.md` § The scene count is DERIVED
shows how a fixed "four" got into this skill and why it was wrong.

- **The hook needs 6–7 seconds on screen, never 3.** A card that flashes for 3s reads as a glimpse,
  not a read. Let it eat into the runtime rather than into the read time.
- **The hook is the conflict, not the demographic.** "Are you a farmer?" is a filter — it gives
  everyone else permission to leave. Open on drama with a withheld answer.
- **Value-turn as a visual reaction, not a traded line.** Script the silent beat — the look at the
  crumpled bill, the brow unfurrowing — *then* the line. The audience discovering the shift on a face
  is the retention hit, and it generates better than a talking head.
- **Character signature.** One repeatable non-verbal bit per recurring character becomes a series
  hallmark. Non-verbal, so it stays safe even for locked-audio clients.
- **CTA as narrative payoff**, resolving the dramatic question visually rather than a static end card.
- Lines 10–15 spoken words. One CTA button, not a summary.
- **Run `scripts/estimate_duration.py`** to confirm length and get the clip count.
- **Then test it before it goes anywhere:** read it aloud, run `scripts/script_score.py`, and score
  the scorecard in `references/script-craft.md` §6 (four universal + four chosen, of twelve).
  Nothing under 7 ships. The line-level
  craft — speakability, reactivity, the breath unit — is in that file; this stage is the shape.

Full format: `references/script-format.md`. Worked examples: the client profile.

## Stage 2 — Storyboard & shotlist

`assets/shotlist-template.md`: one row per shot — size, description, camera move / END FRAME, the
line or text it carries, and the AI-gen prompt — **plus the transition plan, one line per join**:
the join's type from the mode palette, the exact pack asset if any, and whether it demands
generation handles. Transitions are decided here, not discovered at the cut point. Establish → intimate; shot count from the runtime and the pace in `references/sequence-grammar.md` §2c (dialogue-led scenes run slower, about 3.3–5.5 s a shot); honor the 180° line
and eyelines. **One line = one clip; two speakers = two clips.** Plan **B-roll ≥ dialogue clips,
ideally +2**, plus an S0B intro. Tag END FRAME only where the shot lands on a specific composed end
state — a simple dolly/zoom/pan is text-driven and needs no end-frame image, which saves credits.

## Stage 3 — AI generation

Start frame per shot → animate. **Lock character identity with a reusable Element (or a hero
reference image + seed) — not text alone.** Record dialogue voices first. Budget first, generate in
economy mode, run the per-clip QA card (`realism-qa.md` §6) before a clip leaves review.
Everything — models, the prompt block, the guardrail table, the identity lock, lipsync, the economy
playbook — is in `references/ai-generation.md`; model IDs and costs are in the profile.

## Stages 4–6 — Voice, music, edit

Lock one voice per character. Record dialogue before its clip for audio-driven lipsync; strip or mute
a character clip's embedded audio once a separate external VO exists for it. **Ask the user which
music track** and note its BPM. In Resolve, cut on action and follow the pacing curve, then fit the
music to the locked cut (`music_fit.py`: 2–4 hits, the cut never moves by itself), master to −14 LUFS, burn in captions,
and queue the render rather than auto-starting it. See `references/editing-and-audio.md`.

## Stage 7 — Branding & compliance

Run the profile's non-negotiables as a real gate; add `references/compliance.md` where the category is
claims-sensitive. Bounce failures back rather than shipping.

## Stage 8 — Export

The client's delivery format (`references/delivery-format.md`), publish handoff. Queue the render
(don't auto-start) and run
`scripts/export_qc.py` on the result. Treat a FAIL as a real gate, same as branding. Before the client sees it,
run the client's own check: **does it tell the story with no sound and no voiceover?** (`references/sound-off-story.md`:
T2, the picture alone, read by a cold viewer; T1 on each delivery file; `soundoff.py pack` for the hand-over).

---

## Growth add-ons (optional, when a client wants more from one shoot)

- **🪝 Hook Variants (Stage 1.5).** 2–3 hook variants A/B'd; winner becomes the locked opener.
  Cheap — edit-stage, reusing generated B-roll. *(Locked-audio clients: vary only B-roll, never a
  spoken line.)*
- **♻️ Repurposed Cuts (Stage 6.5).** One shoot → many posts. See `modes/repurpose.md`.
- **Release calendar.** A steady 2–4 posts/week from one handle beats sporadic virality — skip a slot
  rather than ship weak.

## Definition of Done — Mode A

The script answers one question and ends on one CTA; claims verified; characters consistent and
on-tone; captions correct and mobile-legible; the story reads with the sound off (T2 and T1 logged on the export's
bytes, `references/sound-off-story.md`); file meets specs; credit spend within envelope; the
board reflects reality with the final attached. If any is shaky, say so plainly rather than shipping
and hoping.

**Cross-refs:** `references/script-format.md` · `references/craft-cheatsheet.md` ·
`references/production-design.md` · `references/persuasion-psychology.md` ·
`references/ai-generation.md` · `references/editing-and-audio.md` · `references/pm-workflow.md` ·
`references/realism-qa.md` · `PIPELINE.md` (the automated end-to-end).
