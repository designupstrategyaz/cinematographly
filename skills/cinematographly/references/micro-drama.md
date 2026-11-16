# Micro-drama — a short-series episode, planned for multi-shot clips

**What this is.** A micro-drama is a one-to-three-minute episode of a scripted series: a recognisable
situation, a peak, reactions, and a cliffhanger that sells the next episode. Asked whether to add a
method for it, the owner said *"Yes, add it"* (2026-10-25).

**The source.** Higgsfield's "Short Drama Screenwriter" skill (file dated 2026-10-22), built around
one two-minute episode it calls SOUL Angel `[VENDOR]`. Every number below that carries `[VENDOR]` is
its craft advice, not a measurement, and none of it has been run here. What this file adds is where
each piece meets the gates this skill already has. Where the two disagree, this file says which one
wins and why.

**Where it routes.**
- One episode carrying a brand's message is **Mode A** (`modes/narrative-promo.md`); two or more
  episodes are a **series batch** (`series-parallel.md`) with a bible and a continuity log
  (`series-continuity.md`).
- The profile, the checkpoint and the gate apply unchanged (SKILL.md §1). A short drama is a
  production like any other: no profile, no job.
- The clips are **planned multi-shot clips** (`multishot.md`) where continuity is the content, and
  single-action clips for inserts.

---

## 1. The episode — four parts

`[VENDOR]`, about two minutes by default, anything from one to three:

| Part | What it does | The house file that owns the craft |
|---|---|---|
| **Hook** | Open on the peak, not the beginning: the outburst, the fall, the conflict. The viewer sees the loudest moment without knowing how it got there | `hook-craft.md` — the peak is the anchor, *how did we get here* is the withheld term, and the gap still needs its three legs (§2 there) |
| **Context** | Who these people are and what they want, with an **emotional swing every 20–30 s** — a start, hope, a hit, a chance. A flat stretch of explanation is where viewers leave | `emotional-journey.md` §2.2 (the flat-stretch diagnosis) |
| **Escalation** | An unexpected turn: a new character, a bigger conflict. The tension lives in **how differently two characters read the same moment** — she thinks she is in trouble, he thinks he has found someone. Write both performances, and the movement | `sequence-grammar.md` §4 (the reaction, the ladder) · `direction.md` §3 (the listener reaction is the coverage floor) |
| **Cliffhanger** | End just before the answer: a decision about to be made, an identity about to be revealed. **Promise it, do not show it.** Cut to black | `emotional-journey.md` §2.4 (the last frame is worth the hero frame) |

Near the end, **pick up the pace**: changing angles, an entrance, small interactions. Build up to a key
character's face — from behind, then the clothes, the hands, the eyes, then the face — and let lines
start while people are still moving, so there are no dead pauses `[VENDOR]`.

⛔ **The four parts are planned before any dialogue is written, and checked again when the script is
done.** A part that is missing on the second check is a script note, not an edit note.

## 2. Choosing the story

**Start from a situation the audience already understands**, and find the feeling under it — the one
the audience has had themselves (*"I don't belong here, and now I'm in trouble"*). The feeling, not
the setting, makes it relatable. The vendor's reliable engines `[VENDOR]`:
- someone ordinary gets an unexpected chance;
- love against the odds;
- a rivalry;
- hidden identity;
- turning the tables.

**Score each candidate 1–5 on six criteria** `[VENDOR]`, and recommend the highest total:

| Criterion | 5 | 3 | 1 |
|---|---|---|---|
| Instant situation | clear from one frame | needs one line | needs backstory |
| Recognisable feeling | almost everyone has felt it | one group has | rare or abstract |
| A visible peak | a physical event in one shot (a fall, a spill, a reveal) | a sharp line | an inner thought |
| Reaction contrast | two characters read the moment oppositely on camera | one clear reaction | nobody reacts |
| Easy to produce | 2–4 speaking characters, one location, everyday actions | five characters, or 2–3 locations | crowds, vehicles, dance, fights or sport as the main beat |
| Series potential | ten or more episodes | a few | one story |

How it meets development (`ideation.md` §3–§6, SKILL.md §2 stage 1):
- The score is **one kill test among the house's**, never a replacement for divergence. Development
  still produces five or more concepts and two adversarial rounds, and the client still picks.
- ⛔ **No borrowed idea bank.** The vendor ships a hundred premises; none is imported. A premise
  taken from a list is somebody else's development, and the first one in theirs is their own
  published episode.
- Every invented full name is searched before it is used. One that belongs to a real public figure
  is renamed `[VENDOR, and compliance.md]`.

## 3. Cast, voices, continuity

- **Two to five speaking characters** `[VENDOR]`. For each: name, age, role, what they want in this
  episode, and how they behave under pressure.
- **A continuity log per scene**: what each character wears and carries, and when it changes (*the
  glasses fall off in scene 2 and stay off*). It is the series' VARIANT record
  (`series-continuity.md` §3), and a state change inside a clip needs its own reference
  (`prompting-craft.md` §11d item 2).
- **Background people come from one group reference**, and every clip where it matters says who they
  are not (*the assistant is never mistaken for a model*).

**Voices — where this file departs from the vendor.** The vendor locks a voice by repeating one
description (*accent, pitch, pace, timbre*) word for word in every clip, and calls that "the same
voice everywhere". ⛔ **Not adopted as a lock.** A description is not an identity: native audio
re-samples the voice in every generation, and nothing has measured it holding across clips here, let
alone across episodes. The house route:
- write the description anyway and repeat it verbatim — it is free;
- a voice that must hold across a series goes **voice-first** (Path A, `ai-generation.md`): a fixed
  TTS voice, then the audio in as a reference;
- native audio (Path B) only after its bake-off with a verbatim check;
- either way, continuity is checked by **listening**, episode against episode, and `gate.py` refuses
  generated sound until `audio` is approved.

## 4. References — the house sheet

The vendor's asset order `[VENDOR]`:
1. four to six face portraits, one chosen;
2. the outfit, shoulders to feet, against a plain wall;
3. a sheet that combines them: **grey background, three views, the face erased on the full-body
   view** so the close-up is the only face;
4. a changed look (hair down, glasses off) as its own sheet, because one sheet holds one look;
5. close-ups of details that must be exact;
6. one image of the background group;
7. the location as a three-quarter view, no people.

That is the house sheet, found independently (`character-and-props.md` §8.3b: one face, headless or
faceless body panels), so it is adopted with the house's conditions:
- generated sheets are **identity locks approved at the frame gate**, never mood or style references
  (`character-and-props.md` §8.7b);
- a generated character never imitates a real person;
- a clip attaches **only the references it uses** — two to five per clip in the vendor's episode
  `[VENDOR]` — inside the model's slot limits (`multishot.md` §4);
- the vendor's budget, about three image generations per main character plus one per changed look
  `[VENDOR]`, is a planning figure; quote the stills with `rate_card.py`.

## 5. Scenes into clips

- **One Seedance 2.5 generation runs up to 30 s**, so every scene is one or more clips of 30 s or less,
  with **roughly one shot per 2–5 s** inside a clip, or one continuous take `[VENDOR]`. That is a
  planned multi-shot clip: the cut list, blocking, frames and stages of `multishot.md` §2 come first.
- **An insert is its own clip** when one moment needs special treatment: a fall in slow motion, a
  phone close-up. When a scene works except for one moment, **fix the moment with an insert instead
  of regenerating the scene** `[VENDOR]`. In house terms it is a single-action clip with a
  `function:` (`direction.md`), and it is usually cheaper than a second multi-shot take.
- **The cut to black is made in the edit.** The vendor writes it into the prompt as a hard cut at a
  stated second. Here the episode's last cut is an external cut: the clip holds 1–2 s past it
  (`multishot.md` §2), and the black is the editor's.
- **The listener reaction is still the coverage floor.** In a multi-shot clip it is a stage with its
  own `End state:`. ⚠ `gate.py approve clips` counts reaction **clips** per scene, so it cannot see a
  reaction stage yet: the selects pass checks it by eye.
- **The script ends with a generation and edit order**: every clip in order, its length, and how the
  edit uses it (the whole scene, part of a scene, cut into a scene).

**The vendor's clip-prompt blocks map onto the multi-shot form** (`multishot.md` §9):

| Vendor block | House block |
|---|---|
| SCENE CONTEXT | `[GOAL]` |
| ACTIVE REFERENCES | `[REFERENCES]` — one subject per line, positional tags |
| LOCATION MAP · FIRST FRAME AND SPATIAL BLOCKING | `[WHERE]`, and the blocking render as the video reference |
| FORMAT MODE · OPTICS AND CAMERA · ACTION TIMING | `[STAGES]` — budgets, not timestamps; one camera behaviour per stage |
| PHYSICS · LIGHTING | inside each stage, light last; the light source once more in `[CONSISTENCY]` |
| AUDIO | `[SOUND]` — one canonical list of lines |
| POSITIVE LOCKS | `[CONSISTENCY]` — positively, once each |

**When a take fails**, the vendor's advice is the house's: name the problem in plain words, change
only what is broken, regenerate, compare `[VENDOR]`. Here that is the one-variable correction,
checked by `prompt_lint.py NEW --against OLD` (`refinement-loop.md` §1b).

## 6. Cost and length

A two-minute episode on `seedance_2_5` is **four 30 s generations** for one take of everything —
`rate_card.py lookup --model seedance_2_5 --res 1080p --seconds 30` prices one, so the pass
is four times that. Two takes of the hero sequences, the inserts
and the stills come on top. The yield of a multi-shot take has not been measured (`multishot.md`
§10), so the per-usable-second price is unknown until the first episode.
Quote with `rate_card.py` and `estimate_duration.py`, and probe each call with `get_cost`.

## 7. A series

`[VENDOR]`, consistent with `series-parallel.md` and `series-continuity.md`:
- each episode gets its own four parts;
- every episode ends on a cliffhanger, and the next opens on its answer;
- the references and the voices stay the same across episodes;
- the first episodes get the strongest hooks, because they earn the viewers the later ones need.

The series joins the house machinery: the bible holds the INVARIANTs (identity, voice, the light
logic), the continuity log holds what changes per episode, and `series_join.py` gates the batch.

## 8. Boundaries

⛔ These are compliance, not taste (`compliance.md`), and the vendor states them too `[VENDOR]`:
- **original stories** — borrow structures and feelings from existing shows, never plots,
  characters, names or dialogue;
- **no real people** as characters, and no imitation of a real person's likeness;
- **platform-safe**: every character is an adult, romance plays out in looks and near-misses, no
  nudity or sexual content, no graphic violence;
- the **AI disclosure** follows the platform's rules on every episode (`compliance.md`).

## 9. Verification — before an episode ships

- The four parts are present on the final cut, each where the plan put it.
- No stretch longer than ~30 s without a swing `[VENDOR interval]`, checked on the emotional-journey
  map against the cut.
- Every speaking scene has its listener reaction, as a clip or a stage, seen in the selects.
- Voices match the previous episode, by listening.
- The continuity log agrees with the picture, scene by scene.
- The cliffhanger promises and does not show.
- With the sound off, the episode still reads: T2 on the locked episode, dialogue captions off, retold by
  someone who has not read the script (`sound-off-story.md`).

## 10. What this file cannot tell you

- **Whether a swing every 20–30 s holds this audience.** It is the vendor's interval, unmeasured;
  the retention curves after shipping are the test (`performance-metrics.md`).
- **Whether a voice holds across episodes on native audio.** Nobody has measured it here; that is
  why Path A is the default for a series.
- **The yield of the multi-shot clips an episode is built from** (`multishot.md` §10).
- **Whether the six-criterion score predicts anything.** It is a sensible checklist with no outcome
  data behind it; record each episode's score beside its retention and let the series argue.
