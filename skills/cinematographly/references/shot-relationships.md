# Shot relationships — what carries from shot to shot, and how to rebuild a reference with new content

**The owner's asks (2026-10-25).**
- *"Analyze relationships between objects, frames, backgrounds, characters from shot to shot"* — for
  films, shorts, promos and ads.
- *"in case I want a reference promo video or short to be replicated but with new environments, chars
  and sounds + voice. But framing, shots, movement etc remains the same."*
- *"Also for continouity, emotion, lighting, camera angles, camera motion (maybe even track and
  categorize it) … Even advanced background analysis for recreation and creativity enhancement."*
- The build order: *"All three in one release"*.
- The reference rule: *"Any reference, flagged"* (§5).

Two scripts:

| Script | What it does |
|---|---|
| `scripts/shot_graph.py` | Measures every cut and every shot from the pixels, writes the sheets a reader needs, and holds the reading to a closed vocabulary. Merged, the result is a **shot graph**: who and what is in each shot, what every cut keeps or breaks, the camera tracked, the light, the backgrounds. Its `qa` mode checks our own edit before picture lock (§6) |
| `scripts/replicate.py` | Turns a shot graph into a **replica plan** in a job: the structure kept, the content mapped to new characters, places, product, voice and music, the shots grouped into clips, blocking drafts, prompt skeletons, audio slots, and a closeness score (§5) |

It sits beside the other reading tools. `film_breakdown.py` gives the cut list and the per-shot move;
`motion_track.py` gives the frame-by-frame curve of one shot (easing, elements); `film_db.py` keeps
every shot of a reference as a queryable row. The shot graph is the layer none of them had: the
**relations** between shots.

---

## 1. The workflow

```
film_breakdown.py REF.mp4 --label ref --strip        # cuts + strips; CONFIRM every cut on the strips
shot_graph.py measure REF.mp4 --cuts BREAKDOWN-ref.json --label ref --out bd/ --confirmed [--plates]
shot_graph.py template bd/JOINS-ref.json             # → bd/READ-ref.json, the form
   … read SHOTS-ref-NN.png (a mid frame per shot) and PAIRS-ref-NN.png (the frame pair at every cut) …
shot_graph.py validate bd/READ-ref.json              # vocabulary + read-vs-pixel second looks
shot_graph.py merge bd/READ-ref.json                 # → SHOTGRAPH-ref.json + .md
```

⛔ **Confirm the cut list first.** The detector finds about 76 % of true cuts (lab-00006: 314 missed,
95 false splits in 1,293). Without `--confirmed`, every output says the list is a draft.

The read can be done by a person or by Claude, with the same form and the same vocabulary. On a large
set (a dataset of ads) it is the Batch-API step. The pixel half is free and runs on the CPU.

## 2. What is measured — per cut and per shot

`[assumed · house values, 2026-10-25]` for every threshold below. They are printed with every result,
and they get calibrated on confirmed reads (§8).

**At every cut.** Frames are decoded either side of the join, and the real cut frame is found from the
biggest frame difference within ±0.2 s of the stated time. A timestamp that is a frame off therefore
cannot put a frame on the wrong side.

| Measure | How | Flag |
|---|---|---|
| Colour jump | CIE76 ΔE between the mean L\*a\*b\* colours of the two frames | ΔE ≥ 6 between **alike** pictures: a grade or colour-cast mismatch |
| Alike or not | the correlation of the two colour distributions **with their means removed** | ≥ 0.60 alike (one place, one look); ≤ 0.25 unalike |
| Exposure jump | the mean luma step | ≥ 12 / 255 between alike pictures |
| Camera before and after | an inlier-gated similarity over the last and first ~0.18 s, named from the **camera's** side | — |
| Subject screen motion before and after | dense optical flow with the camera's motion removed | the direction flips when both sides move ≥ 0.04 frame-widths/s |
| Where the subject is, either side | a face (OpenCV, where available) or the centroid of what moves | an eye jump of ≥ 0.35 of the frame diagonal |
| The key light's side, either side | the brightness of the two halves of the face, or of the frame | changes side between alike pictures |

⛔ The alike measure is cast-invariant on purpose. A hue histogram calls two angles on one place under a
mismatched grade "two places", and that hides the exact mismatch the check is for. The selftest's own
blue-cast wall scored −0.09 that way.

**Per shot.**
- **The camera, tracked.** Frames are sampled at 8 fps, with an inlier-gated similarity between every
  pair, chained into a path. That gives:
  - the totals: pan in frame-widths, tilt in frame-heights, zoom ×, roll in degrees;
  - mean and peak speed;
  - the **profile**: constant, accelerates, decelerates (lands), eases in and out;
  - **shake**: frame-to-frame jitter divided by speed;
  - a **parallax index**: the share of the motion that a flat similarity cannot explain. A camera that
    travels (dolly, truck, crane) has parallax; one that only turns or zooms has none.

  Then a category, and the `blocking.py` move it maps to:

  | Measured | When | Blocking move |
  |---|---|---|
  | locked · drift · handheld | below 0.010 W/s · slow with no net move · shake ≥ 0.55 | `locked` · `drift` · `static` on a handheld rig |
  | pan · tilt | translation, no parallax | `pan` · `tilt` |
  | truck-left/right · crane-up/down | translation with parallax ≥ 0.18 | `truck_left`/`truck_right` · `crane_up`/`crane_down` |
  | push · pull · zoom-in/out | scale, no travel | `push_in` · `pull_out` · `zoom_in`/`zoom_out` |
  | dolly-in/out | scale with parallax | `dolly_in` · `dolly_out` |
  | whip | peak ≥ 1.5 W/s | `whip_pan` |
  | roll · compound · unsolved | roll only · more than one at once · too few reliable pairs | — (written by hand) |

  ⚠ A flat or distant scene has no parallax, so a travelling camera on it reads as a pan or a zoom. For
  the frame-level curve of one shot (its easing, overshoot and settle), run `motion_track.py` on it.

  ⚠ **The tracked points are not the camera (2026-11-10).** Corners sit where the detail is, and on a
  plain background the detail is the subject. So each frame pair's move is checked against the picture
  away from the points, in blocks, and the larger area decides. Three things can come back beside the
  category:
  - `held_pairs`: frame pairs where the points moved and a larger part of the picture held still. They
    count as no move.
  - `points_alone`: what the points by themselves said, when that differs. ⛔ **Two answers, and no flat
    picture can choose between them:** a subject moving in front of a held camera (a hat flicked on a
    bare wall), or a camera travelling over a near surface while a far backdrop holds (a low travel over
    a field under a still sky). The reader takes the first. The plan, or the person who read the shot,
    settles it: `motion_qa.py` and the read check accept either answer.
  - `unsure` with `unsure_why`: at least half the measured travel comes from frame pairs the rest of the
    picture disputes or cannot confirm (a subject on a wall of one flat colour). Treat an unsure move as
    "look at the clip".
- **The light:** mean L\*, contrast (p95 − p5), low-key / mid-key / high-key, the key side (on the face
  when one is found, else the frame halves), warm / cool / neutral (mean b\*), and saturation.
- **The background and the composition:**
  - a 5-colour palette with shares;
  - a 3×3 brightness map, which names where the eye goes;
  - a 3×3 detail map, which names the negative space;
  - sharpness, and a depth-of-field proxy (the subject's cell against the rest: shallow, medium,
    deep).
- **A clean plate,** with `--plates`, for a held shot (locked or drift, 1.2 s or longer): the per-pixel
  median of up to 15 frames, so whatever moves through the shot disappears. It's a reference for the
  set, read for recreation. ⛔ A plate cut from someone else's film is a third-party picture: it's for
  study and briefs, never a generation reference without a licence (`stock-sourcing.md` §5,
  `character-and-props.md` §8.7b).

## 3. What is read — the codebook

Closed lists, enforced by `validate`, are listed below. Write in your own words only: ⛔ never
dialogue, captions or any text from the film.

**Entities**, each with an id: `A`, `B` for characters, `P1` for props, `L1` for locations. Kinds:
character · prop · product · location · vehicle · animal · group · graphic. **The same letter in every
shot the same person is in**: that's what makes it a graph.

**Each location** also carries the recreation brief:

| Field | What |
|---|---|
| setting | interior · exterior · virtual |
| place, era, materials | own words |
| weather | clear · overcast · rain · snow · fog |
| layers | what is in the foreground, the middle ground and the background (bg is required) |
| distinctive | what makes it this place |
| recreate | how to rebuild it: what must survive (light direction, depth, the negative space) and what can go |
| **variants** | three or more **alternative worlds that keep its job in the frame**: the same depth layers, the same light side, the eye going to the same place, and a different world. A café that becomes a night bakery, a train carriage, a greenhouse. This is the creative part: the replica keeps the grammar and changes the world |

**Each shot:**
- size (EWS … XCU, insert) and angle (eye · low · high · aerial · dutch);
- the location;
- the key side (left · right · front · back · top · flat · mixed · practical), the quality (hard ·
  soft · mixed), the style (natural · high-key · low-key · silhouette · neon · practical · mixed) and
  the time of day (day · golden · blue · night · interior);
- `camera`: blank to accept the measured category, or the category you see;
- and, **per character:**
  - screen position (left … right, off), depth (fg · mid · bg);
  - gaze (camera · screen-left · screen-right · up · down · closed), facing (camera · left · right ·
    away), motion (none · left · right · toward · away · up · down);
  - **emotion** on `film_db.py`'s performance scale: `expr` is one word from its 19, `intensity` runs
    0 blank · 1 restrained · 2 open · 3 peak, and `turn` is `none` or `early:/late:/through: <what
    changes>`. The two databases speak one scale;
- props: who holds them, and their state.

**Each cut:**

| Field | Values |
|---|---|
| relation | same-scene · new-scene · return · insert · cutaway · graphic · time-jump |
| match | action · eyeline · graphic · movement · sound · shape · colour · none |
| axis | the 180° line kept · crossed |
| screen direction | kept · flipped |
| eyeline | matched · mismatched |
| carries | entity ids, plus light · colour · movement · sound · music · line · look |
| changes | size · angle · subject · place · time · costume · prop-state · light · colour · lens · speed |
| continuity_error | own words, or empty |

## 4. Read against the pixels

`validate` sends the read back for a second look when it disagrees with the measurement. The
measurement can be wrong too, so these are warnings, not errors:
- the screen direction read as kept, but the subject's measured direction flips (or the reverse);
- read as same-scene, but the two pictures share almost no colour; read as new-scene, but they are
  nearly identical;
- a match on action when nothing moves at the join;
- a measured flag (a colour, exposure or light-side jump) on a same-scene cut that records no
  continuity error;
- a camera category or key side read differently from the measurement (push, pull, zoom and dolly are
  allowed to disagree, because parallax hides the difference);
- a location with fewer than three variants.

The merged graph summarises:
- the relation and match shares, axis crossings, direction flips (read and measured) and eyeline
  mismatches;
- the continuity errors, and what each cut carries on average;
- the ΔE of same-scene cuts (median and p90): a film's own grading tolerance;
- an **emotion arc** per character;
- **light breaks**: the key side flipping inside a location;
- the camera distribution;
- a **background card** per location, with palette, light, layers, the rebuild note, the variants and
  the plates.

## 5. Replicating a reference — `replicate.py`

```
replicate.py map SHOTGRAPH-ref.json -o MAP-ref.json        # who and what becomes whom, the licence, keep switches
replicate.py audio REF.mp4 -o AUDIO-ref.json              # speech windows + word counts, beats, hits — no words
replicate.py plan SHOTGRAPH-ref.json --map MAP-ref.json --job <job> [--audio AUDIO-ref.json]
replicate.py closeness <job>/01-script/REPLICA-ref.json   # re-score after editing the plan
```

**What is kept:**
- each shot's length, size and angle;
- the measured camera: category, totals, speed profile, and the `blocking.py` move;
- who stands where, faces where, looks where and moves where (now the new cast);
- each character's emotion and its turn;
- the light: side, quality, style, time of day;
- where the eye goes and where the negative space is;
- each cut's relation, match, line and screen direction, and what carries across it.

**What is swapped** through the mapping you approve: every character, prop, product and place. A
location can take one of its read **variants**. Voice and music too:
- each **speech slot** gives its window and how many words fit it at the source's pace, so the new
  line is written to length;
- the **beat map** gives the bpm and the beat times for the new track;
- the **hits** give where the new effects or accents land.

The source's words, music and pictures never enter the job.

**What the plan writes:**
- `REPLICA-<label>.json/.md`, with a prompt skeleton per shot.
- The shots grouped into clips: a new scene, or more than `--clip-max` seconds, starts a new clip. A
  one-shot clip is a single-action clip; several shots make a planned multi-shot clip, with its
  `[STAGES]` skeleton (`multishot.md`).
- A `blocking.py` **draft** per clip. The camera shots come from the measured moves; the mapped actors
  are placed from their screen and depth positions (left −1.2 m … right +1.2 m, fg −1.0 m … bg +1.6 m,
  facing from the read), with the line of action between the first two. `_need` lists what a person
  still writes, the set and the props, before `blocking.py check`. A draft built from a synthetic
  reference passed `check` with no FAIL.
- `00-brief/REPLICA-SOURCE.json`: the source, its licence and the closeness.

From there the job runs exactly as any other, through the gates: development and script approval, the
blocking approval, the frame gate, the clip prompts, voice, music, the edit.

**The closeness score, and the rule it serves.** Each source shot scores the share it keeps of:
- its duration (within 15 %), size, angle and camera family;
- every character's screen side;
- the cut into it (relation and match).

The score is the mean over the shots, 0 to 100 `[assumed · equal weights]`. The bands are ≥ 85
**shot-for-shot**, ≥ 60 **close**, below that **loose**. Turning a `keep` switch off, or editing the
plan, moves the score; `closeness` re-scores it.

⚠ **House decision 2026-10-25: any reference may be used, flagged.** The source, its licence (own ·
client · licensed · third-party) and the score travel with the job. `gate.py status` shows them, and
`gate.py approve export` says them again. Neither refuses: the decision is the owner's, per job.
Framing, camera moves and pacing are technique. A shot-for-shot copy of one specific film or ad also
copies its sequence, and for a client deliverable built from a third-party source that's a real risk.
The flag exists so the risk is decided with the facts on the table (`compliance.md`; this is not legal
advice).

## 6. Our own edit, before picture lock — `shot_graph.py qa`

```
shot_graph.py qa 07-edit/cut_v3.mp4 --cuts <the edit's cut list> --label cut_v3 --out 09-qa/joins --confirmed
```

It measures every join of the edit and exits 1 on a flag:
- a colour or exposure jump between alike pictures, which is the grade not matching across a cut in
  one scene;
- a screen-direction flip;
- the key light changing side between alike pictures.

It also notes eye jumps, which are fine on a new scene and a stumble inside one. Then it writes the
pair sheets for what pixels cannot see: the same face, the same clothes, the same product, the prop in
the same hand. Read them in the realism pass (`realism-qa.md` §6); AI clips drift there.

**Before lock, `motion_qa.py cut` runs the same measurement** with the shot order:
`motion_qa.py cut 07-edit/cut_v3.mp4 --cuts <the cut list> --shots S1,S2,S3 --job <job>`. It adds the
plan: each planned hand-off (`exit:`, `enter:`, `join:` on the clip prompts, `shot-handoff.md` §4b)
is checked against the screen direction measured across its cut. `gate.py approve lock` refuses
while the newest cut in `07-edit/` has no joins report, and while any shot in the cut has no current
`motion_qa.py clip` report.

## 7. A dataset (the Hook Atlas, a competitor library)

The dataset keeps its own clips, labels and text, outside the skill. Run `measure` on each clip with
the cut list the dataset already holds (`--cuts` takes a breakdown JSON with `rows`, or `shots6`), and
`--no-sheets`, so the run writes numbers and no frames. ⛔ A breakdown JSON's `move` and `size` are
copied into the shot rows as they stand: when those labels are known to be wrong (the Hook Atlas
moves predate 2.25.0), write the cut times to a plain text list and pass that instead. Only
aggregate numbers, with their tags, may come back into the skill, as a lab write-up. A film in the
reference database is measured on its own cut list (the row starts after the first, with `--confirmed`
because that list is a person's read), then `film_db.py attach JOINS-<FILM>.json --film <FILM>` puts a
`tracked` block beside each row's read, with its source. It refuses a cut list that is not the
database's own, and a rebuild keeps the block only while its shot did not move. A 6-frame sheet
cannot carry any of this: the camera, the subject's motion and the join all need consecutive frames
from the video.

## 8. What this file cannot tell you yet

- **The thresholds are house values.** ΔE 6, alike 0.60, parallax 0.18, shake 0.55: none is calibrated.
  The calibration is the median and p90 of the same-scene ΔE on confirmed reads of real films (the
  merged summary already computes them), and agreement against hand-read camera moves.
- **The first real-film reading (2026-10-25) says the join flags fire often.** On the person-read cuts
  of the three AI shorts in the database, 45 % (F1), 54 % (F5) and 27 % (F4) of cuts
  carry a flag, mostly a colour or exposure jump between alike pictures: the median ΔE between alike
  pictures is 11.5, 6.8 and 4.4 against the threshold of 6 [measured · the JOINS files behind
  `film_db.py attach`]. Either an AI short really drifts that much between generations, or the
  thresholds are tight; nobody has looked yet. Until a person checks a
  sample, read `qa`'s exit 1 as "look at these joins, largest ΔE first", not as a verdict.
- **Dolly vs zoom and truck vs pan** come from parallax. A flat or far scene has none, so a travelling
  camera on it reads as turning or zooming. The read can override it. The parallax index also moves
  with the tracking resolution: on 40 STILL shots, tracking at 640 px instead of 320 kept the camera
  family on 29, and most of the changes were dolly or truck becoming pan or zoom. Handheld held
  (11 → 10). Treat the travel categories as soft [measured, one film].
- **Two trackers, not reconciled.** The database's `move` (film_breakdown's whole-shot solve) and the
  `tracked` block (this tracker) agree on the coarse class (locked / drift / handheld / directed) on
  37–56 % of the shots both could measure. `film_db.py facets` prints both and picks neither. The
  whole-shot solve needs a motion frame with a short side of 400 px or more (`film_breakdown.py`
  warns): at 205 px it left half of F5's shots UNRELIABLE.
- **The key side is a brightness heuristic.** It can be fooled by a bright background on one side, or
  by a face turned in profile.
- **"Where the subject is"** is a face, or the centroid of what moves, not a person detector. OpenCV 5
  builds have no face cascade (`pip install 'opencv-python-headless<5'` restores it).
- **Emotion is read, never measured.** The scale is film_db.py's, so the two can be compared; no model
  here scores a face.
- **Speech slots need faster-whisper.** Without it the plan has no speech windows, and says so. Beats
  fall back to an onset-envelope autocorrelation, marked [estimated], when librosa is absent.
- **Closeness measures structure, not likeness.** Two films with the same timings, sizes and moves
  score high even if they look nothing alike. That's what it is for, and it is not a legal test.
