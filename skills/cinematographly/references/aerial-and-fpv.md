# Aerial, FPV, insect-scale and planet-scale shots

When an aerial earns its place, how fast and how far each move goes, how to prompt one so it doesn't come back
looking like a toy, how to cut it, and the golf, property and real-drone side of the work.

**Where this comes from.** The owner asked on 2026-10-26: *"we need to research drone camera movements, shots,
when to insert etc"*. They widened the scope three times:

- *"Golf plus indoor camera flying moves too research too, think bee, mosquito views etc"*
- *"Aerial shots include orbit planet view, fly down to ground, moving across continents fast etc"*
- *"Check DJI drone moves. They have presets in the app for moves"*

The research and the council are in lab record lab-00016 (not shipped) and
the aerial and FPV proposal of 2026-10-26 [studio history]. The owner chose all four packages. Their rulings:

- **C1** seed chaining *"Allow narrowly"*
- **C4** *"Split: rules refuse, measures warn"*
- **C5** *"Name it, labelled spec, private"*
- **C2, C3 and C6** as the jury agreed (§10, §1, §1)

The numbers live in `assets/aerial-moves.json`, the move table. The tools are:

- `scripts/aerial_qa.py`: the declaration, the measures, the lock check
- `scripts/flyover.py`: golf and property, rights, the pilot sheet
- the aerial moves in `scripts/blocking_camera.py`

---

## 1. An aerial earns its place by a job

Critics now read the overhead drone shot as a cliché: detached, map-like, like surveillance [CRITIC · Prospect,
Mark Kidel]. Earned aerials serve the story:

- Skyfall's chase.
- *Amy*, which keeps us "in the city, not above it".
- *The Banshees of Inisherin*, which bookends the film with two drone shots.

Aerials also work as elevated B-roll and as breathing room after an intimate scene [Sundance].

The crane's grammar is reveal and god's-eye [BOOK · Katz]. And "every shot is a close-up" [BOOK · Glebas]: a
wide with no chosen subject says nothing.

**The declaration.** Every aerial, FPV, insect or planet clip carries one line in its prompt's frontmatter.
`prompt_lint.py` refuses a clip without it, through `aerial_qa.lint_aerial`:

```
aerial: move=orbit, function=reveal, subject=the clubhouse roof, final=the clubhouse with the sea beyond,
        place=real, lane=golf, landmarks=the Swilcan Bridge, preset=poi
```

- **`function`** is the shot's job. It is one of:
  - **establish**: where we are
  - **scale**: how big
  - **isolation**: small and alone
  - **vulnerability**: watched from above
  - **geography**: how the place is laid out
  - **pattern**: a shape only visible from above
  - **reveal**
  - **ending**
  - **judgment**: the god's-eye view
  - **breathing**: room after intimacy
  - **journey**: the route carries the story

  The table says which moves suit which job; a mismatch warns.
- **`subject`** names a thing in the place. "Landscape", "the city" or "b-roll" refuses.
- **`final`** says what the last frame shows. An aerial with no defined end drifts.
- **Nadir shots (C6).** A shot straight down (`top_down`, `rocket`) is information in golf and property and must
  declare `geography` or `pattern`. Everywhere else it needs a story function and a `why=`.
- **Density (C3).** There is no cap; nothing evidences a number. The function rule governs:
  - golf and property have no cap, but need ground-level variety;
  - drama defaults to bookend aerials, and an aerial inside the film is noted.

  The aerial share of the runtime is logged at lock.

## 2. The moves and their numbers

The table holds 29 moves. Each has a range, its blocking move, its jobs, its prompt words and its source. The
practitioner figures [PRACTITIONER · Drone U] were converted from mph and ft:

| Move | Range | Cap |
|---|---|---|
| orbit | 1.3–2.2 m/s, radius 15–46 m | ≤ 1.5 turns in a delivered edit |
| helix | one turn per 8–12 s | ≤ 3 turns |
| fly-over (approach) | 3.6–6.7 m/s, climbing late ("climbing too early removes the tension") | |
| gap fly-through | 0.9–1.8 m/s | |
| tilt-down reveal | 2.2–4.5 m/s | |
| pull-back reveal | 1.8–3.6 m/s (endings, isolation, scale) | |
| top-down | 30–122 m up | |
| parallax orbit | 1.3–1.8 m/s, foreground 3–6 m off | ≤ 1.5 turns |
| pedestal | climbs 1.3–2.7 m/s, camera level | |
| side follow | 6–18 m off (closer is more urgent) | |
| push-in | 0.9–1.8 m/s, stops before the subject fills the frame | |
| hover pan | 7.2–12 °/s (15–25 s per half turn) | |
| hole flyover | 3.6–6.7 m/s | |
| bee | ~0.71 m/s mean | |
| mosquito | 0.2–0.6 m/s | |

The FPV, cinewhoop, planet and DJI rows are in the file.

⚡ **A drone shot is a slice of a longer flight.** The blocking moves default to a *speed* and work out the
distance from the shot's length. They don't squeeze a fixed distance into whatever time the shot has. Half an
orbit in six seconds is a 13 m/s whirl, not a drone orbit; at the table's 1.8 m/s and a 25 m radius it is 25°.
The new moves are:

- **Orbits and spirals:** `drone_orbit`, `helix`, `parallax_orbit`, `boomerang`.
- **Holds, tilts and climbs:** `hover_pan`, `tilt_down_reveal`, `pedestal`, `rocket`.
- **Following and pushing:** `drone_side_follow`, `drone_push_in`.
- **Routes:** `gap_fly_through`, `cinewhoop_oner`, `hole_flyover`.
- **Insect scale:** `bee_path`, `mosquito_path`.

Each runs on the existing `drone` rig or on the new `cinewhoop` and `insect` rigs.

`blocking.py check` holds these moves, and any shot marked `"aerial": true`, to the table (C4):

- **More turns than the cap refuses.** It is a rule.
- **A speed, radius, rate or height outside its range warns.** The ranges are practitioner defaults, not
  physics.

## 3. Prompting an aerial on the approved models

`aerial_qa.lint_aerial` applies these rules:

- **One move per clip** [VENDOR · Seedance.tv]. `move=orbit then helix` refuses: split it into two clips.
- **No speed words** ("fast", "rapid", "racing", "hurtling"…). They refuse, because the models answer with
  erratic, warped motion. Say the pace ("slow, controlled"); the edit sets the speed. A drone prompt with no pace
  word warns.
- **The anti-toy rules.**
  - A blur gradient makes a real city read as a miniature; a sharp, deep-focus image reads big and far
    [PRIMARY · Held, Cooper, O'Brien & Banks 2010]. So "tilt-shift", "miniature" and "diorama" refuse, and
    "shallow depth of field" or "bokeh" on an aerial warns.
  - Scale is sold by haze, layers, texture scale and a near foreground [BOOK · Sawicki]. A drone or planet prompt
    with no depth cue warns. The layers, the visibility and the anchors are decided in the world card
    (`world-design.md` §2); an aerial with no `world:` card is refused.
- **The motion budget** (v2.42). `aerial: path_m=<metres>` says how far the clip flies. Divided by the clip's
  length, it is held to the move's speed range, and an overrun is a ⚑ warning that must be answered before spend:
  "402 m in 5 s is 80 m/s, 12× the table's 3.6–6.7 m/s; one clip covers 18–34 m". A route move with no `path_m=`
  is asked for one. The measure still warns (house rule C4); what changed is that nobody can spend past it
  unanswered.
  - The same ground speed reads slower from higher up [PRIMARY · Flach et al. 2004]. Fly low to feel speed, high
    to feel calm.
- **A real place is pinned by a real photograph.** Otherwise the model "can invent a different building" [VENDOR
  · Segmind]; Kling's own guide says its aerials are "a style of landscape, not a verified specific location".
  - `place=real` refuses unless the start frame is a cleared real photograph (client-supplied, own-shoot,
    licensed, public-domain or Pixabay, with a matching sidecar), or a declared chain from one (§11).
  - Name the landmarks that must hold their shape (`landmarks=`).
- **Name the motion, not the app preset.** "QuickShot", "Dronie" or "DJI" in a prompt warns. The preset belongs
  on the pilot sheet (§12).
- **Google Earth refuses** anywhere (§13).

The AI aerial tells to look for: crowds blend into railings, a landmark changes between shots, buildings shift,
shapes re-form [FACT-CHECK · popsci]. `aerial_qa.py drift` looks for the last two (§14).

## 4. Cutting aerials

- **Cut hard into and out of an aerial.** A transition touching one is noted at lock.
- **An aerial holds over 3 s so the move reads** [PRACTITIONER · PremiumBeat]. A drone or planet aerial on
  screen less than 3 s is noted.
- **Start and stop on action** [BOOK · Ward].
- **Hold the axis across consecutive aerials.** Opposite travel directions are noted from the motion reports.
- **Drama: bookends by default** (§1).
- **One stunt per film.** A flip, a roll or a 180° drift is punctuation.
- **The little-planet open** (the DJI Asteroid) is a stitched effect, not a camera move. It is an opener only.

## 5. Indoor FPV: the cinewhoop one-take

A cinewhoop tour is one continuous flight with the scenes in story order, scouted and rehearsed [PRACTITIONER ·
Drone U 2022]. "Right Up Our Alley" (Bryant-Lake Bowl, 87 s, 2021) took "a few takes". Every sound in it was
designed in post, and it was praised for choreography and sound, "not simply good flying" [PRESS · DroneXL].

Use the `cinewhoop_oner` move (a route of waypoints at a constant speed, looking ahead) on the `cinewhoop` rig.
Hidden joins pass through a dark object or a full-height wipe [PRACTITIONER · 4K Shooters]: declare them
(`joins=2.1,4.4`). `aerial_qa.py seams` flags any jump that no declared join explains. Seedance FPV oners from a
drawn route are written as chronological segments (launch, climb, weave, exit) [VENDOR · WeShop].

## 6. Insect scale: the bee and the mosquito

- **Probe lenses** (5 mm tips, deep-ish focus, the bug in its world) beat 1:1 macro, whose mushy background
  reads fake.
- **Real time.** High frame rates made a beetle "clumsy and ungainly", so it was shot real time with very wide
  lenses [VFX Voice]. Slow motion or a ramp on an insect shot refuses.
- **"You should never look down on your heroes"** [NatGeo, *A Real Bug's Life*]. A downward insect view warns.
- **The bee** (`bee_path`). Honeybees average 0.71 m/s, "accelerate slowly and decelerate rapidly", and turn on
  13–22 cm [PRIMARY · Hejazi et al. 2022]. The path eases into each dash and brakes into a tight turn; the
  selftest measures that profile.
- **The mosquito** (`mosquito_path`). Its heading rarely matches its travel, with 50–200° turns and sideslip
  [PRIMARY · Iams 2012]. It slips round a person while the lens stays on them; the selftest checks that the view
  points away from the travel.

## 7. Golf: the hole card and the hole flyover

A hole flyover takes off at the tee, climbs as it travels and descends to the green: "the hole from the ball's
perspective" [PRACTITIONER · Drone U golf]. Clubs use them on websites, socials, cart screens and visitor
screens, often with per-hole narration on par, yards and strategy [CLUB · Virtual Tour Co.].

1. **The card.** `flyover.py course init <job> --name …` writes `00-brief/COURSE.json`: one card per hole with
   par, yards, the strategy line, hazards, landmarks, the green, the real seed photo and optional route points.
   Nothing is invented; blanks stay blank until club data fills them. `course lint` refuses:
   - a missing number, strategy line or seed;
   - pars that don't add up to the course's par.
2. **The prompt.** `flyover.py hole prompt <job> --hole 17` drafts a declared clip prompt on the hole's seed. The
   director edits and approves it; writing it approves nothing.
3. **The overlays.** The golf title lane (`title_card.py propose --lane golf`) permits `hole`, `place` and
   `endcard` titles. `flyover.py overlays` checks every "Hole 7 · Par 4 · 371 yards" against the card. A
   mismatch refuses at `titles`, `lock` and `export`.
4. **The St Andrews protocol.**
   - `--preset old-course` carries only the checked facts: 18 holes, par 72, 7,305 yd, anticlockwise; single
     greens on 1, 9, 17 and 18; seven double greens; the Swilcan Bridge (1/18), the Road Hole (17), Hell Bunker
     (14) and the Valley of Sin (18) [REFERENCE · Wikipedia, checked 2026-10-26; confirm against the Links
     Trust's card].
   - Each hole needs a real licensed aerial photograph.
   - Run it on one hole first.
5. **Naming (C5).**
   - Name the course descriptively, labelled "Spec, not affiliated with St Andrews Links Trust".
   - No Trust logos or marks.
   - Never put the course in a service brand name.
   - The file is `private: true`: `gate.py` refuses to publish it until a legal view clears public promotion.
   - An overlay that implies an affiliation refuses.

   The Trust holds the "St Andrews" mark for goods; the EUIPO refused it for travel services (2020).

## 8. Property

- **Pin the building with a real seed.** `flyover.py property init` writes `00-brief/PROPERTY.json`: the exterior
  and every room, each on its own cleared photograph.
- **An invented room is a claims risk.** A property clip whose subject is not a room of the file refuses, and so
  does a room label that isn't on it.
- **Interiors glide slowly.** Energetic moves "read as a car advert" and warn.
- **Generate 9:16 natively.** Never crop a 16:9 walkthrough.
- **Keep clips simple.** Multi-beat prompts under ~10 s fail [VENDOR · Segmind].

## 9. Sound

- **The model's audio is muted on an aerial.** A clip with native audio on warns.
- **No motor whine unless the drone is in the story.** A drone motor in the prompt warns.
- **The bed follows altitude:** close and textured low, thin and wide high.
- **Planet scale thins toward silence**, as Contact's pull-back does.
- **The oner's sound is designed in post** (§5).

## 10. Planet scale: the plunge, the pull-back, the traverse

- **Pace.** Powers of Ten moves one power of ten per 10 s going out and per 2 s coming in [FILM · Eames 1977].
  Contact's pull-back was reversed from a fly-in because forward "seemed false" [FILM · Contact 1997].
- **The Earth-zoom preset is reference only (C2).** Higgsfield's Earth Zoom runs 3–5 s and fails on
  shallow-focus or flat start frames. It distorts when the ground-to-orbit step is rushed and is "not
  geospatially accurate" [VENDOR · Segmind]. `gate.py` refuses `execute_preset` on its id until its underlying
  model is confirmed on the approved roster; build the move from approved models and real seeds.
- **Stages.** `earth_zoom` and `pull_back_planet` run up to 3 stages; four refuse. A stage under 3 s warns.
- **No stars beside the sunlit Earth.** The exposure that shows the lit Earth can't show them, so stars in the
  prompt refuse unless it says the night side. `aerial_qa.py stars` counts isolated points beside a lit Earth.
- **The geography is simulated.** Every planet move declares `geography=simulated`, and the rights manifest says
  so.
- **The real numbers.** The ISS is 400 km up, at 28,800 km/h on a 90-minute orbit [PRIMARY · ESA], and crosses a
  continent in minutes. Anything faster is a time-lapse and reads as one.

## 11. Seed chaining (C1, allowed narrowly)

The standing rule is "never use AI images as references". Staged earth zooms and long oners need one exception,
and the owner allowed it narrowly. The next link's start frame may be a frame of an approved clip, only when:

- **the clip was measured and selected.** `aerial_qa.py chain-frame` refuses a clip that motion QA did not
  measure, that the QA log did not select, or that has no aerial declaration;
- **the chain's root is a real photograph.** Each link declares
  `chain: root=<the real seed>, stage=<1–3>, from=<shot>`;
- **the link is recorded.** `chain-frame` writes `<frame>.chain.json` with the root's, the frame's and the source
  clip's hashes;
- **it stays within three links.** A fourth refuses (Sonnet's cap, untested);
- **nothing has changed.** A link refuses if its root, its frame or the clip it came from changed since.

A `chain:` without an `aerial:` declaration refuses.

## 12. A real drone day: DJI's presets and the pilot sheet

DJI's apps fly a set of moves for you. This summary is from DJI's own manuals: Mini 4 Pro v1.0, Mini 5 Pro v1.0,
Mavic 4 Pro v1.2, Neo v1.2 and Avata 2 v1.0 [PRIMARY · DJI user manuals, read 2026-10-26]. Each preset maps to a
move of the table, and the declaration accepts the preset names as aliases (`move=dronie`).

| DJI preset | Our move | What it does |
|---|---|---|
| QuickShots › Dronie | pull_back_reveal | back and up, camera locked on the subject (the Neo also flies back in) |
| QuickShots › Rocket | rocket | straight up, camera down (the Neo keeps the camera on the subject) |
| QuickShots › Circle | orbit | one circle at the current radius |
| QuickShots › Helix | helix | one rising spiral that widens |
| QuickShots › Boomerang | boomerang | an oval, highest at the far end; clear 30 m radius and 10 m above |
| QuickShots › Asteroid | little_planet | a stitched "little planet", then the descent; clear 40 m behind and 50 m above |
| MasterShots | — | ~10 classic moves in a row, subject centred: a coverage pass for raw |
| FocusTrack › Spotlight | (flown by hand) | you fly; the camera stays locked on the subject |
| FocusTrack › Point of Interest | orbit | a set radius and speed, up to 12 m/s; the slow, long orbit QuickShots can't do |
| ActiveTrack › Trace / Parallel | side_follow | from one of 8 sides of the subject's travel, or on a fixed compass bearing |
| Hyperlapse (Free, Circle, Course Lock, Waypoint) | hyperlapse | time compressed; best above 50 m, subject over 15 m away |
| Waypoint Flight | hole_flyover, flyover… | a saved route, repeatable; per point: height, speed, heading, gimbal, zoom, hover |
| Cruise Control | (flown by hand) | holds the stick input, for an even speed |
| Avata 2 › Easy ACRO | fpv_flip, fpv_roll, fpv_drift_180 | flips, rolls, a 180° drift; not below 1.5 m or 25 % battery |

- **Before any preset.** Hover at least 2 m up. The subject must be within 50 m, on the ground and not moving
  fast. Light must be between 300 and 10,000 lux. Avoid buildings, weak GNSS, and subjects that blend into their
  surroundings or into snow or desert.
- **ActiveTrack distances.** A person 4–20 m away (Mini 4 Pro).
- **Easy ACRO.** It can't be enabled while recording, so switch it on first.
- **The pilot sheet.** `flyover.py pilot <job>` writes `09-qa/aerial/PILOT-SHEET.md`. For each aerial shot it
  gives:
  - the preset that flies it, or Waypoint Flight or hand flying when none does;
  - what to set and the clearances;
  - the table's speed, radius, height and caps;
  - for golf, a Waypoint table per hole (tee, landing area, over the hazards, approach) with height, gimbal tilt
    and speed. Fly every hole the same way, then re-fly the route in other light.
- **The route curves between waypoints.** It can dip below them, so check what is under it.
- **Raw clips only.** The app's auto-edited QuickShots and MasterShots videos never reach the cut.
- **The sheet is not a flight authorisation.** The pilot's checks, the airspace and the operator's permission
  come first.

## 13. Rights and disclosure

- **Google Earth: no.** "We currently do not offer a license to use Google Earth imagery for commercial
  applications" [PRIMARY · Google Earth Studio FAQ]. It refuses in prompts, seeds and sidecars.
- **NASA imagery** is generally not copyrighted in the US, but it must not imply NASA endorses a product. Credit
  NASA, and never use the insignia [PRIMARY · NASA brand centre].
- **`flyover.py rights <job>`** writes `09-qa/aerial/RIGHTS.md`. It lists every seed (source, holder, licence,
  clearance), the private flag and the spec label (C5), simulated geography, the NASA credit and the platforms'
  AI labels. Lock refuses without it.

## 14. The checks: what refuses and what warns (C4)

| Check | Tool | At |
|---|---|---|
| **Refuse:** a missing or empty declaration | `prompt_lint.py` → `aerial_qa.lint_aerial` | lint, lock |
| **Refuse:** speed or miniature words, a nadir without a reason, insect slow motion, stars, unsimulated planets, Google Earth | `prompt_lint.py` → `aerial_qa.lint_aerial` | lint, lock |
| **Refuse:** a real place without a real seed, a broken chain | `prompt_lint.py` → `aerial_qa.lint_aerial` | lint, lock |
| **Refuse:** over the move's turn cap | `blocking.py check` | blocking |
| **Refuse:** the course or property card, overlays against the cards, the rights manifest | `flyover.py check` | lock (overlays also at titles and export) |
| **Refuse:** a private spec published (C5); the Earth Zoom preset (C2) | `gate.py` | publish, spend |
| **Warn:** speed, radius, rate or height outside the table | `blocking.py check` | blocking |
| **Warn:** the toy look (blur gradient, no haze falloff, fast and crisp) | `aerial_qa.py scale` | lock |
| **Warn:** landmarks that re-form, a clip off its seed | `aerial_qa.py drift` | lock |
| **Warn:** unplanned seams in a oner | `aerial_qa.py seams` | lock |
| **Warn:** stars beside a lit Earth | `aerial_qa.py stars` | lock |
| **Warn:** the cut rules (§4), the aerial share, ground-level variety | `aerial_qa.py check` | lock |
| **Refuse:** an aerial with no world card; a mover the card does not cast; a sky or wind word against the card | `prompt_lint.py` → `world.lint_prompt` (`world-design.md`) | lint |
| **Warn, answer before spend (⚑):** a route over the move's speed (`path_m=`), a route with no distance | `prompt_lint.py` → `aerial_qa.lint_aerial`, `world.py accept` | lint |
| **Refuse:** the sound-off check not logged on the export's bytes — T2 reads the place, the sequence and the contact card from the picture (`sound-off-story.md`) | `soundoff.py check` | export |

Every measured threshold is [assumed]. They are tuned on synthetic clips only; real drone footage calibrates them,
and until then a human signs each warning off. What none of this does: tell a good aerial from a bad one.

## 15. Still open (named by the jury)

- Who supplies licensed real aerial photographs per hole or property, and when a real drone beats AI.
- A course map or survey as the geometry truth. The card holds facts, not positions.
- An image-to-video aerial test on each approved model.
- The time and cost per hole, to price an 18-hole package.
- Light, season and grade matching across holes.
- A property misrepresentation policy.
- Real drone clips to calibrate the measures.
