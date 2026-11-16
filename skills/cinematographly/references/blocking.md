# Blocking — a grey 3D render that fixes the camera and the positions before a credit is spent

Loaded when a shot needs blocking (§1). The tools are `scripts/blocking.py` (spec, checks, camera,
prompt, build), `scripts/blocking_rig.py` (the skeleton) and `scripts/blocking_kit.py` (rooms, furniture,
props and the mannequin's body). The approval is `gate.py approve blocking:<SHOT>`. Evidence tags:
**[PRIMARY]** a paper read on the date shown; **[VENDOR]** Higgsfield's own material; **[COMMUNITY]** a
practitioner collection, read through a fetch summary, so treat its figures as pointers; **[measured]**
something this skill ran; **[textbook]** a standard figure quoted from memory, not re-read this session;
**[assumption]** a house value nobody has measured.

⛔ **Status: adopted by house decision 2026-10-23 ("Full stage + bigger bake-off"). Whether a video model
follows the render is NOT measured yet.** The prompt-lint checks are WARN until the blocking bake-off
(lab-00011, 346.5 cr, approved, not run) says which routes work.

## 1. When a shot gets blocked

Block it when any of these is true. Otherwise the approved start frame is enough.

| The shot has | Why words fail |
|---|---|
| Two or more people | Who is frame left, who faces whom and who is in front drift between takes and across cuts |
| A geometric camera move (an arc, an orbit, a push past an object, a rise, a lead) | Prompted motion collapses to dollies and zooms (`motion-design.md` §1) |
| A count (three bottles, two cups) | Models do not count |
| A hard cut inside one generation, or a take over 8 s | Each cut's camera must land where the next one expects it |
| A product in hand | Which hand holds it, at what height, and where the label faces |
| A cut near a line of action | The 180° rule is geometry, and geometry is checkable |
| People walking | Pace, where they stop and who leads are positions over time |

**A scope caution, unmeasured by us (v2.49; HFF-04).** One festival team found a Blender previz render
**weak for two subjects moving in different directions**, and worse with a non-human body: a low crab
body gave the model no human landmarks to follow. The same team found it **fine for a single subject**
where the camera's speed had to be exact `[SECONDARY · festival study 2026-11-05, one team's diagnosis]`.
So until lab-00011 measures it (§9): reach for a blocking first on one subject and an exact camera; on two
subjects crossing, or a creature, plan a fallback — split the shot, or write the geography in the scene
form's `[LOCATION MAP]` and `[ACTION TIMING]` (`prompting-craft.md` §12) — and check the first take
against the render before the second. The same team, when one beat kept landing on the wrong object,
changed the beat rather than refining the line: a blocking does not rescue a beat the model will not read.

## 2. Getting an LLM to make a good Blender scene (the eight practices)

The research is consistent: an LLM writing Blender Python directly is the weak version; an LLM that
writes **constraints** for code to solve, and then **looks at the render and revises**, is the strong one.

- **SceneCraft** (Hu et al., ICML 2024) turns text into a relational scene graph, writes one scoring
  function per relation, lets a solver place the objects, renders, and has a vision model critique the
  render in an inner loop. An outer loop keeps the functions that worked as a reusable library. It
  reports a constraint-passing score of **88.9 against 5.6** for BlenderGPT, which writes the code
  directly, and a CLIP score **45.1 % higher** on its synthetic queries [PRIMARY · arXiv 2403.01248,
  read 2026-10-23].
- **Holodeck** (Yang et al., CVPR 2024): GPT-4 proposes spatial relations between objects, never
  coordinates, and an optimiser solves the layout [PRIMARY · CVPR 2024 pp. 16227–16237].
- **BlenderAlchemy** (Huang, Yang, Guibas, 2024) edits a Blender program in rounds. Each round generates
  several candidate edits and a vision model picks the best render. The previous best always stays in the
  running, so a round that made things worse is reverted. At a fixed 32 calls, a balanced split (8 × 4 or
  4 × 8) beat all-breadth and all-depth [PRIMARY · arXiv 2404.17672, read 2026-10-23].

What `blocking.py` does with each lesson:

| # | Practice | In this skill |
|---|---|---|
| 1 | **The LLM writes a spec, not code.** It writes positions, relations and intent; code does the placing | `<SHOT>.blocking.json`, a closed schema (§3). Claude never writes bpy for a blocking |
| 2 | **Sizes come from a table, never from a guess** | `DIMENSIONS` in metres: furniture, props, rooms. Extend the table; `size` overrides one piece |
| 3 | **The camera is written in film terms and solved by maths** | A shot plan: each shot names its move, its subject, size, lens, height and side at its start and end (§3a). Code turns it into keys, a spline, a composition and a handheld. `blocking.py camera` prints the result |
| 4 | **Relations are checked by code before anything renders** | `check`: bodies inside furniture, walls or each other; the camera inside a wall, a piece or a person; reach at a pick-up; the line of action at a cut; jump cuts and screen direction across cuts; pans, travel and jolts too fast to read; the subject hidden behind something; the subject and listed props in frame (props inside the 85 % safe area); the eyes in their band on a vertical frame; a head or prop near the lens; a face that must stay out; a declared move the camera does not make; empty void behind the action; the model's duration range; the legend both ways |
| 5 | **Look at the render, then revise. At most three rounds, keep the best** | The review sheet (facing cones on), the top-down map and the clean first and last frames, read against the critique questions in §4. A round that made it worse is reverted, not patched |
| 6 | **Keep what worked as a library** | `blocking.py example --preset NAME`: kitchen-hero, cafe-coverage, hallway-oner, street-runner, car-night, product-robo, park-fpv, rooftop-spiral (§3f). The short v3 specs stay as test fixtures. An approved spec for a client joins the library under that client's job |
| 7 | **The prompt's spatial text is computed from the same geometry** | `blocking.py prompt`: who is frame left, who faces the camera, when the cut lands, what each hand holds, what the camera does. The writer adds performance, not positions (§6) |
| 8 | **Same spec, same frames; every file hashed** | The build is deterministic (the handheld is seeded), and the manifest carries a sha256 per file. The gate binds the approval to those bytes (§7) |

**What the loop caught on its own presets** [measured · blocking.py development, 2026-10-23]. Every
item is now a check or a rule in the code.

From the first four presets (2.21.0):

1. A side-by-side two-shot at 35 mm on 9:16 lost both people out of frame, because the frame is 0.31 m
   wide at half a metre. The fix was an over-the-shoulder two-shot in depth at 28 mm.
2. That two-shot looked down the table into void behind the pharmacist (35 % of the frame was empty).
   A video model invents whatever the render leaves empty.
3. An MCU on 9:16 at 35 mm puts the lens 0.53 m from the face, so a bottle held "beside the face" passed
   0.23 m from the lens and filled the frame.
4. A bottle whose centre passed the in-frame test was still half cut off at the edge, hence the 85 %
   safe area for listed props.
5. A camera tilting to follow a lifted product brought the presenter's chin into an insert meant to be
   hands only.
6. A prop jumped from the counter to the hand in one frame. Holds are now a path (reach, lift, hold,
   lower) at about 1.2 m/s, and `build` flags any frame that changes more than 3× the frames around it.
   The first version compared against the clip's median and flagged the arm's fast lift instead, which
   is a run of large changes, not a jump. The neighbour test comes from the practitioner render loops
   in the Opus video collection [COMMUNITY · github.com/yihui-dev/awesome-opus5-5-videos].

From the rig, room and camera rebuild (2.23.0):

7. The insert declared a tilt, but a bottle lifted from the counter to waist height tilts an 85 mm less
   than 6°, which reads as a hold. Holding it at the chest instead brought the chin in again. The shot
   is now declared `static`, and every declared move is checked against what the camera does.
8. A camera moving backward ahead of two walkers was described as "trucks". The computed words now say
   "leads".
9. A walk through a middle key slowed by 18 % at the key, because each segment eased on its own. A walk
   is now one speed profile from stop to stop (0.6 s ramps, an even pace between), corrected so the
   middle keys are still met at their times.
10. With the feet landing under the hips, the trailing leg reached full length and the knee jumped
    16 cm in one frame. Feet now land half a step ahead at heel strike, the heel peels up behind, the
    hips drop as far as the legs need, and the IK eases into full reach.
11. One merged body surface webbed the arms to the ribs, and the chest tore when an arm reached forward.
    The limbs are now separate surfaces sunk into the torso, as on an artist's mannequin.
12. Resting hands sat at hip height, so every actor stood with hands on hips. They now hang beside the
    thighs.
13. At 85 mm the holding hand covered half the bottle's label, because the prop sat on the palm. Moved
    to the side, the hand still covered the label whenever the camera was on that side. A prop whose
    label faces the camera is now gripped from behind as the lens sees it; any other prop is gripped from
    the side, palm facing in.

From the camera, environment and preset rebuild (2.24.0):

14. A drone reveal kept its points round where the runner stood when the shot began, so it climbed away
    from an empty pavement while she ran on. Fixed-point moves now ride a travelling subject.
15. An arc on a host who turned to the island swung the camera through her and into the island, because a
    framing followed her live facing. Framings now hold the angle she faced when the shot began.
16. A plain spring trailed a runner by about 0.4 m at 1.8 m/s and lost her from a worm's-eye rise. The
    operator now tracks the plan ahead by the lag its spring would have; she stayed at the placed edge.
17. A continuous join jumped from one move's end to the next move's start (271°/s between a worm's-eye
    rise and a drone reveal). Joins now ease into the next move's path, and the shake, bank and tip of
    the rig taking over cross-fade.
18. The FPV banked outward and reached 86°. It now banks into the curvature of its own path, within 45°.
19. A car-mounted camera fell 0.5 m behind its car: an exact rig that started at the plan's speed was
    taken for a kicked one. Exact rigs now ride the plan; a kick rings out as an offset on top.
20. A chase cut on a frame before the cut squeezed its last 0.25 s into 0.2 s and sped up, then braked
    into the cut because the plan holds its last key until then. Cut shots are built to the frame
    before, and the operator carries on through the hold.
21. The café dressing removed the very table two seated people were blocked at. A seat under a seated
    actor, and its table, now stay.
22. A worm's-eye shot read "insert on the frame", and an 8 cm rise on an 85 mm ECU (56 % of the frame)
    read "stays put". Moves now name their subject and the part they frame, and small moves are judged
    against the frame.
23. The prompt merged two joined moves into one generic sentence. The beats now split at each joined move
    and name it.
24. Interior concept frames were washed out: walls too bright, a flat ceiling bounce, a grey window. The
    plaster is darker, the bounce lower, the windows stronger and the sky behind them blue.

From the eight presets' first review sheets (2.24.0); 25, 27–29, 31 and 32 were fixed in the presets, 26 is
a rule for writing specs, 30 was fixed in the code:

25. The kitchen hero never showed its product: at an MS on 9:16 the bottle held at the chest sat on the
    bottom edge and swung out of frame on the turn. The arc is now an MWS with the host right of centre,
    and the bottle is listed in the end framing so `check` holds it in the safe area.
26. An 85 mm ECU on a mannequin's mouth is a featureless surface; a video model can take nothing from it.
    Detail framings belong on what the mannequin has (feet, hands, a held prop). The hero now ends on an
    orbit pinned to the product in her hand.
27. A car side track from the passenger side looked across the car at a driver hidden by the B-pillar,
    and the back-seat set-up was all seat backs. The track runs on the driver's side and the third set-up
    is outside her window.
28. A lead on two walkers at 28 mm cut the leading head at the top edge. It is 22 mm with the pair placed
    lower.
29. The FPV chase flew 1.2 m above the runner's eyes at a fixed distance for nine seconds: a game camera,
    not a pilot. It now flies at her shoulder at eye height and overtakes to lead her after the bend.
30. A lathed product stood 10 cm above its plinth with its label plate hanging under it: a prop is placed
    by its centre and the shape was built from its base. Shapes and models on props are now centred.
31. The rooftop spiral never showed the skyline: a size on the shot overrode the spiral's wide, low start,
    and the crane ended looking straight down at the deck. The spiral now starts wide and low, and a drone
    reveal at a shallow angle (about −27°) ends with the skyline in the top of the frame.
32. The street's drone reveal climbed to 16 m and looked down at 60°: the runner became a speck among
    rooftops. It now pulls back down the street ahead of her at about −28°, so the street recedes behind
    her.

From the presets' concept stills (2.25.0), each fixed in `blocking_look.py` or `check`:

33. Every golden-hour frame rendered black. The haze was a world volume, which EEVEE treats as infinite,
    so it swallowed the sky. Haze is now a bounded box round the set.
34. The night drive was black: no moon, 220 W streetlights and nothing lit inside the car. Night now has
    a cool moon, a blue ambient and +1 EV, streetlights at 1500 W, and every car gets headlights and a
    dash glow on the faces inside.
35. The product studio was black: the softbox lights sat inside their own boxes, the world was black, and
    EEVEE drew the glass bottle as a dark silhouette. The lights sit in front of the softbox face, the
    studio has a grey fill, and the preset's product is glossy rather than glass.
36. A look time nobody defined ("morning") fell back to day without a word. `check` now FAILs it.

## 3. The spec

Coordinates are in metres, seen from above. **+X is screen right** for a camera at the front, and **+Y
points away from the front** (the front of the set is −Y). `facing` is in degrees (0 = +X, 90 = away,
−90 = toward the front), or an actor id, `"camera"`, or `[x, y]`. `blocking.py example` prints a complete
one.

| Field | What it holds |
|---|---|
| `shot` `duration` `fps` `aspect` `render {w,h}` `model` | The duration is the clip's duration; `check` holds it to the model's measured range |
| `env` | A whole location from a template (§3c); its pieces join `set[]` |
| `set[]` | `id`, `kind` (from `DIMENSIONS`, or `room`, or `plan`), `pos`, `rot`, `color`, optional `size`, `z`, `camera_through`, `material`, `shape` or `model` (§3e). Seats (`chair`, `sofa`) carry their back on local +Y |
| a `room` | `size [w, d, h]`, `walls` (any of back · front · left · right), `thickness`, `ceiling`, and `openings[]` of `wall`, `kind` (door · window), `at` (metres along the wall from its centre), `w`, `h`, `sill`, `open` (a door's swing in degrees). The walls are solid to `check` except where the doors are |
| `actors[]` | `id`, `color`, `height`, optional `name`, `build` (slim · average · broad), `pose` (stand · sit · lean), `body` (mannequin · segments), `face_out_of_frame`, `ramp`, `in` + `seat` (a passenger, §3c), and `keys[]` of `t`, `pos`, `facing`, `pose`, `look` (an id, `"camera"` or a point the head turns to) |
| `vehicles[]` | `id`, `kind` (car), `color`, `ramp`, `keys[]` of `t`, `pos`, `heading` (§3c) |
| `props[]` | `id`, `kind`, `color`, `pos`, `on` (a set piece), optional `name`, `label_toward: "camera"` (adds a white label plate, which needs a legend line), and `held[]` of `by` (`A.right`), `from`, `to`, `at` (waist · chest · face), `put {pos, on}`; `shape` or `model` for the exact product (§3e) |
| `camera` | `lens` and `handheld` (the defaults), then `shots[]` (§3a), or raw `keys[]` and `cuts[]`; `cross_line` |
| `line_of_action` | Two actor ids. A **cut** that crosses it warns; a continuous move across it does not, because the audience sees the camera travel |
| `legend` | One line per colour that renders, and no line for a colour nothing uses. Grey is the stand-in colour and needs no line |
| `sky` | `true` for an exterior, where empty void is sky (an exterior `env` sets it) |
| `look` | The concept render's time of day, palette, haze and exposure (§3d) |

### 3a. The shot plan

A shot is `{t: [t0, t1], move, rig, …}`. The shots tile the duration with no gap. Consecutive shots are
cut together unless the later one says `"cut": false`, which makes one continuous camera through both.
`blocking.py moves` lists every named move with its default rig and what it is for.

| Field | What it does |
|---|---|
| `move` | One of 92 named moves (below). The move builds its own keys: timing, framing, lens, roll, focus. `check` WARNs when the rendered camera does something other than what the move promises |
| `rig` | What carries the lens (below). Each move has a default; `rig` overrides it |
| `on` + `size` + `height` + `side` | A framing in film terms: on an actor, a prop, a vehicle or a set piece. Size ECU…EWS; on a thing the sizes scale with the thing (ECU = a detail of it, CU = it fills the frame). Height eye · chest · waist · hip · knee · low · high · overhead · level, or metres. Side 0 = in front of the subject, +90 = its left |
| `pos` + `look_at` | A camera placed in the set. `look_at` is a point, an id kept framed, or a list of ids framed as a group |
| `start` `dur` `hold` | Place the move inside the shot: `start` in seconds or an event (`"A.stands+0.2"`, `"A.stops"`, `"bottle.picks"`), `dur`, `hold: [before, after]` |
| `react` | Events that jolt the operator: `[{"at": "A.sits", "kind": "flinch"}]` (flinch · startle · bump · jolt · lean_in) |
| `blend` | On a continuous join: seconds over which the camera leaves the last framing and joins the next move. Unset, it is long enough for the new rig to carry the distance comfortably (1–3 s) |
| `facing_ref` | `"start"` (default): a framing holds the angle the subject faced when the shot began, so someone turning inside an arc or a held frame does not drag the camera round. `"live"`: the framing turns with them (riding moves always do) |
| `from` / `to` / `path[]` | Any key field at the move's start and end, and keys in between; the move's own parameters (`degrees`, `ratio`, `altitude`, `offset`…) sit on the shot |
| `lens` `frame` `place` `eyes_at` `focus` `fstop` | The focal length; ids that must stay in frame; where the subject sits in frame (auto · centre · left · right · `[sx, sy]`); the eye line; focus target and aperture |
| `whip` `vehicle` `occlusion_ok` | Allow a fast pan, travel faster than the rig, or the subject passing behind something |

**The named moves**, by family (each has its parameters in `blocking_camera.py`):

- *Held frames:* static, locked, drift (a hold that settles and breathes), ots, split_ots, ceiling_drop.
- *Toward and away:* push_in, dolly_in, creep, pull_out, pull_back, dolly_out, hero_low, reveal,
  pull_back_reveal, push_through (through a door or a window, a plan's or a room's), dolly_zoom.
- *Round the subject:* arc, arc_left, arc_right, orbit, orbit_360, bullet_time, spiral (orbit + rise +
  push), pinned_detail_orbital.
- *Up and down:* boom_up, boom_down, crane_up, crane_down, pedestal, swoop, worms_eye_rise, lip_ecu_rise,
  vertical_pivot, ceiling_exit, let_go_crane (v2.45, measured course numbers — `references/move-catalogue.md` §38, §58, §63).
- *Lens and aim:* zoom_in, zoom_out, crash_zoom, yoyo_zoom, pan, tilt, pan_reveal, tilt_reveal,
  whip_pan, pivot_whip, rack_focus, deep_to_near_rack, snap_zoom (v2.45, §49), tilt_down_reveal.
- *Lateral:* truck, truck_left, crab, parallax_slide, foreground_wipe.
- *With a moving subject:* follow, lead, side_track, track, fpv_chase, fpv_dive, second_participant,
  car_chase, car_lead, car_side_track, asphalt_skim.
- *Aerial:* top_down, drone_reveal, flyover, drone_orbit, drone_push_in, drone_side_follow, helix, parallax_orbit,
  boomerang, hover_pan, rocket, gap_fly_through, cinewhoop_oner, hole_flyover, bee_path, mosquito_path.
- *Rigged to a body or a car:* snorricam, pov, car_hood, car_dash, car_passenger, car_rear, car_window,
  car_wheel.
- *Motion control:* motion_control, robo_snap (`stops`: framings with holds, joined by snaps).

Moves round a subject that travels ride with it: a chase flies the line the subject took (it swings wide
and banks where they turned), a drone reveal recedes from where the runner is now, a dolly zoom keeps its
offset while the subject walks.

**The operator: what actually renders.** The plan is the ideal camera. The rendered camera chases it
through the rig, a spring on position and a spring on aim, each with its own stiffness and damping, so
a handheld snap overshoots and settles while a motion-control arm stops dead [assumption · house values,
`RIGS`]. The operator anticipates: each rig tracks the plan ahead of time by the lag its spring would
otherwise have (2ζ/ω × `anticipate`), so a steady move does not trail the subject. A rig already moving
when the shot starts is already at speed. Drones and FPVs bank into the curvature of their own path and
tip with acceleration, within each rig's limit (FPV 45°, drone 25°) [assumption]. Each rig adds its own
life on top: drift, step bob, motor vibration. Where one rig hands to another in a continuous run, the
life and the bank cross-fade over 0.8 s.

| Rig | Position spring ω, ζ | Aim ω, ζ | Words in the prompt |
|---|---|---|---|
| locked · tripod | exact | exact · 9, 0.8 | locked off on sticks · on a tripod head |
| dolly · slider · crane | 6, 1.0 · 7, 1.0 · 3.2, 0.85 | 9 · 10 · 7 | on a dolly, gliding · on a slider · on a crane |
| steadicam · gimbal | 3.0, 0.75 · 5.0, 0.95 | 5.5 · 12 | floating · smooth |
| shoulder · handheld | 5.0, 0.7 · 5.0, 0.6 | 8, 0.65 · 7, 0.55 | an operator reacting |
| drone · fpv | 1.8, 0.95 · 4.0, 0.7 | 3 · 6 | from a drone · banking into its turns |
| car_mount · tracking_vehicle | exact · 2.5, 0.9 | exact · 6 | rigged to the car · from a tracking vehicle |
| robo | 26, 1.0 | 30, 1.0 | a motion-control arm, precise and fast |
| snorricam · pov | exact | exact · 10, 0.7 | body-mounted · through the character's eyes |

All values are house assumptions set by eye against reference footage, not measurements.

**Joins.** A continuous join (`"cut": false`) does not jump to where the next move starts: the camera
leaves the last framing and eases into the next move's path over `blend`. Frame a join so the two moves
meet: a worm's-eye rise that ends 1.3 m out at eye height hands cleanly to a drone reveal that starts
1.6 m out; a spiral that ends at chest height hands to a drone reveal that starts 1.8 m out at 1.7 m.

**Detail framings.** A key can frame a part of a person: `"detail": "feet"` (or eyes, mouth, chest,
waist, hands). The prompt says "insert on the host's feet", the eye-line check stands down, and the
in-frame check looks at the feet.

**The prompt says what the camera does, measured.** `[CAMERA]` gives each stage its size, subject, lens,
height and tilt, the moves it holds ("worms eye rise → arc left"), the rigs ("handheld → steadicam"),
then the beats measured on the rendered camera: when it holds, when it moves, how (eases, snaps,
creeps), how fast at its peak, whether it lands with an overshoot, the Dutch, the focus pulls, the
flinches. A small move on a tight frame is given in frame terms ("rises 8 cm (56% of the frame)").

**Handheld on top.** `handheld` (none · breathing · handheld · walking) adds a seeded slow drift over
whatever the rig does, so a build stays deterministic: breathing 6 mm and 0.25° at 0.1–0.4 Hz, handheld
15 mm and 0.6° at 0.2–1.1 Hz, walking 20 mm and 0.8° at 0.3–1.8 Hz plus a 1.8 Hz step bob [assumption ·
house values]. "Breathing" is the Higgsfield blocking's camera that "never locks off; always drifts"
[VENDOR · Higgsfield blog, 2026-09-12, read 2026-10-23].

**The lens.** The 36 mm sensor spans the frame's **long** side, so `lens` is the full-frame focal length
along the long side. 26 mm is a phone's 1× camera held upright. On 9:16 the frame is narrow: at 35 mm it
is 0.31 m wide half a metre out [measured · `vfov_hfov`].

### 3b. What the render is made of

- **Rooms** are walls with the doors and windows cut out: a window leaves a sill and a head, a door
  leaves a head, and an open door's leaf swings on its hinge. A room gives the video model a place
  instead of a void.
- **Furniture** is built from its parts (a table's top and legs, a chair's seat, legs and back, a sofa's
  arms and cushions, an island's kick and worktop, a lamp's base, stem and shade), inside the footprint
  `DIMENSIONS` gives it. Props have shapes too (a bottle's shoulder and cap, a mug's handle, a laptop's
  lid).
- **The mannequin** is a smooth torso-and-head surface and four limb surfaces, built from metaballs in an
  A-pose and skinned to 16 bones. Weights blend across the elbow, knee, waist and neck, and the limbs sink
  into the torso at the shoulder and hip, so nothing tears when an arm moves. The head has a brow, a
  nose and ears so its facing reads. `"body": "segments"` falls back to rigid primitives.
- **The proportions** are the Drillis & Contini segment fractions of height: shoulder 0.818, hip 0.530,
  knee 0.285, ankle 0.039, upper arm 0.186, forearm 0.146, hand 0.108, thigh 0.245, shank 0.246, foot
  0.152, shoulder width 0.259, hip width 0.191 [textbook · Drillis & Contini 1966, as tabled in Winter,
  *Biomechanics and Motor Control of Human Movement*]. The girths are a mannequin's, set by eye
  [assumption].
- **The rig** solves every joint in plain Python, so `check` measures what renders. Arms and legs are
  two-bone IK; an arm reaches the palm, with the elbow back and out. A held prop is gripped from behind
  as the camera sees it when its label faces the camera, and from the side otherwise, so the hand does
  not cover what the shot sells. The
  head turns toward `look`, at most 75° of yaw and 30° of pitch from the body. A sit-down blends over the
  last second of its key segment, so it is a movement and not a jump.
- **Walking.** A walk accelerates out of a stop and slows into the next one over 0.6 s, with an even
  pace between [assumption]. Each foot lands half a step ahead of the hips and is planted until it trails
  0.7 of a step behind, with the heel peeling up about the toe. Stance is 60 % of the stride, swing 40 %
  and double support 20 % [textbook · normal gait cycle]. The step is 0.37 of height at 1.3 m/s and
  shorter for a slower walk, in proportion to √speed [assumption], fitted so the last step lands as the
  actor stops. The hips rise over the planted foot and drop in double support by as much as the legs
  need, never more than 2.5 % of height; the arms swing against the legs.

### 3c. Environments

`env` builds a whole location from a template: `{"kind": "kitchen", "seed": 2, "size": [w, d, h],
"dress": "sparse" | "normal" | "busy", "pos", "rot", "colors": {role: colour}, "clear": [[x, y, r], …]}`,
one or a list of them. `blocking.py envs` lists the 20 templates:

- *Interiors:* living_room, kitchen, cafe, office, store, pharmacy, bedroom, bathroom, hallway.
- *Exteriors:* street, storefront, parking_lot, park, beach, rooftop, road. An exterior turns on `sky`.
- *Studio and product:* cyc, tabletop, podium, turntable (`spin` in degrees per second).
- *Vehicles:* `vehicles[]` of `{id, kind: "car", color, keys[{t, pos, heading}], ramp}` drive the set; an
  actor with `"in": "<car>"` and a `seat` (driver · passenger · rear_left · rear_right) rides in it.

The template places the structure (walls with their doors and windows, the counter run, the road and
kerbs) and then dresses it from 47 part builders. Dressing never lands on an actor's path, a prop, a
camera position, a vehicle's route or a point in `clear`; a chair someone sits on stays. The same seed
builds the same place. Pieces get ids like `env1.island4`, so a prop can sit `"on"` one (read them on
`blocking.py map`). The template adds its legend lines (walls, furniture, the road) unless the spec's
own legend already says them. `set[]` pieces add to the template.

`ramp` (actors and vehicles) is the seconds to pull away and to stop; `"ramp": 0` means already moving
at the first frame and still moving at the last, for a clip cut from the middle of the action.

### 3d. The concept look

`blocking.py concept <spec> -o <dir> [--times 0,4.5,9] [--res 720] [--time golden]` renders the same
blocked scene lit and coloured in EEVEE: stills at the given times and a contact sheet. It is for judging
the place and the light, not the blocking reference, and the gate does not approve it.

- `look`: `{"time": …, "palette": {material or role: colour}, "haze": 0–1, "exposure": EV, "hdri":
  "<local .hdr/.exr>"}`. Times: day, golden, blue_hour, night, overcast, interior_day, interior_night,
  studio.
- Every part names a material (41: plaster, wood_floor, tile, brick, asphalt, glass, metal, fabric,
  foliage, lamp_glow…), with procedural texture (planks, tiles, brick, noise). Lamps glow and light the
  room; windows carry a soft area light; an interior with every camera inside it gets its ceiling and
  fourth wall so the sky does not flood in; at night a cool moon, streetlights, headlights and a dash
  glow light the scene; haze is a bounded box of volume round the set; AgX with a medium-high-contrast
  look. An unknown `time` FAILs `check`.
- **Poly Haven HDRIs:** CC0 only, downloaded per job only with the owner's OK, the licence logged with the job,
  never committed. `blocking_look.py hdri <id> [--res 2k]` shows the URL and size without downloading;
  `--fetch --out <dir>` downloads it with a unique User-Agent and writes the licence beside it.

### 3e. Precise geometry and imported models

When a shape matters (the client's product, a counter of a given plan, an odd-shaped room), build it from
numbers:

- **A floor plan:** `{"kind": "plan", "pos", "points": [[x, y], …], "closed", "height", "thickness",
  "ceiling", "openings": [{"segment", "at", "w", "h", "sill", "kind": door | window, "open"}]}`. Any room
  shape; `at` is metres from the segment's start; `check` FAILs an opening that does not fit its wall.
- **A shape:** a piece or prop with `"shape"`: `{"lathe": [[r, z], …]}` (a bottle, a jar, a glass, from
  its profile), `{"extrude": {"outline": [[x, y], …], "height", "z"}}` (an L-shaped counter, a plinth), or
  `{"parts": [...]}` mixing those with `{"box": [cx, cy, cz, w, d, h]}`; each part may name its material
  `"m"`. Its `size` comes from the geometry; the map draws its real outline and the checks collide with
  it, so an L-counter's notch is free floor.
- **An imported model:** `"model": {"file", "objects", "source", "author", "licence"}` with `"size":
  [w, d, h]` in metres and `"fit": "contain" | "stretch"`: a client's CAD export, a CC0 asset (.blend,
  .glb/.gltf, .obj, .fbx, .stl, .ply). It is scaled to the real object's size whatever units the file uses,
  stood on its base and centred; cameras and lights in the file are dropped. In the blocking render it
  takes its legend colour; in a concept render it keeps its own materials. `check` FAILs a missing file, a
  missing size, a download with no `source`, and a licence that is not cleared for client work (CC0,
  client, own; CC-BY and CC-BY-SA WARN that the hand-off credits the author). Every model goes into the
  build manifest (`assets`: file, sha256, source, author, licence) and into `<shot>.concept.assets.json`.
  Downloads (Poly Haven, BlendSwap at 7 a day) stay out of git.

### 3f. The presets

`blocking.py example --preset <name>` prints one. Each is 10–14 s, checks clean, and is a starting point
to re-block for the brief, not a template to ship:

| Preset | What the camera does |
|---|---|
| `kitchen-hero` | Worm's-eye rise off the floor as the host arrives, joined into an arc round to the camera side as she lifts the product, cut to an orbit pinned on the bottle in her hand |
| `cafe-coverage` | Mirrored split over-the-shoulders, a pivot whip to her reaction, a dolly zoom as the news lands |
| `hallway-oner` | A steadicam leading two walkers backward down a corridor, easing into a living two-shot as they stop; the operator leans in on the stop |
| `street-runner` | A handheld rise from a runner's feet at kerb height handed to a drone that climbs and pulls back down the street ahead of her |
| `car-night` | Tracking alongside the driver's door, the dash looking back at her, outside her window, an FPV skimming the asphalt head-on at the car |
| `product-robo` | A motion-control arm hitting three marks on a lathed product, then a pinned-detail orbital |
| `park-fpv` | An FPV dropping out of the sky into a chase at her shoulder, banking with her through the bend, then overtaking to lead her |
| `rooftop-spiral` | A spiral round her at the parapet that ends on a low hero angle, then a drone that pulls up and away until the skyline holds her |

The v3 library (counter-two-shot, table-exchange, …) is kept as test fixtures (`FIXTURES`).

## 4. The loop

```
blocking.py example --preset kitchen-hero -o 01-script/blocking/S5.blocking.json   # start from the nearest preset (§3f)
blocking.py moves ; blocking.py envs     # the named moves and their rigs; the environment templates
  … edit the spec to the script …
blocking.py check  S5.blocking.json      # FAILs exit 1; read every WARN
blocking.py camera S5.blocking.json      # per stage: size, lens, distance, height and tilt, the move, top speed
blocking.py map    S5.blocking.json      # top-down: rooms and openings, positions, facing, walks, the line, the camera
blocking.py build  S5.blocking.json -o 02-startframes/_blocking/S5
  → look, critique, revise the spec, rebuild — at most three rounds, keep the best
blocking.py concept S5.blocking.json -o 02-startframes/_blocking/S5-concept   # optional: the place lit, for judging it (§3d)
blocking.py prompt S5.blocking.json      # the computed prompt blocks
gate.py approve blocking:S5 --by <name> --quote "…" --artifact 02-startframes/_blocking/S5/S5.blocking.manifest.json --media-id <id>
```

**The critique questions**, asked of the review sheet, the map and the clean first and last frames,
before anyone else sees them (the standing contact-sheet rule):

1. Does each frame read as the size the shotlist says?
2. Is everything the line has to sell in frame and readable: the product, the label, the face?
3. Is every face turned the right way? The black cones on the review sheet show facing, and the clean
   render does not carry them.
4. Will the model have to invent anything: void, a missing wall, an empty table?
5. Does anything jump between frames? `build` prints the pops.
6. On the map, is the camera on one side of the red line at every cut?
7. Does the clean render show anything the legend does not explain?
8. Do the bodies read as people doing the action: feet on the floor, hands where the props are, heads
   turned to whoever they talk to?
9. Does the working part read from this view (v2.46)? The part that does the job (a hand on the dial, the
   moving piece of a mechanism, the product's opening) must not be hidden by another moving part. If two
   moving parts overlap for more than half the move, change the view; a label does not fix a view.

Answer them in writing. Fix by editing the spec, never the render, and rebuild. After three rounds, keep
the best build and say what is still wrong.

**The back-off on a wide hand-over (v2.46).** A continuous join (`"cut": false`) eases the camera from one
framing into the next. Two framings that orbit the same subject already swing round it. When the join is
eased in position instead (a `pos` key, or a new subject), the eased path cuts the chord and can pass
through the subject: a hand-over from her front to a spot behind her came within 0.02 m of her. When such a
join swings more than 30° round the subject and its straight path enters the subject's sphere (0.3 of a
person's height round the framed point, half an object's longest side), `blocking.py` adds one waypoint at
the bisecting angle, pushed out by 30 % of the distance at a swing of 90° or more, and further until both
halves of the path clear (`blocking_camera.back_off`; the same hand-over now keeps 0.79 m). The key carries
`backoff: <swing degrees>`. The thresholds are [assumed]: the 30 % comes from one shipped camera path.

## 5. Routes: how each roster model takes a blocking

⛔ All unmeasured. The bake-off decides which of these work.

| Model | How it takes the blocking |
|---|---|
| `seedance_2_5` | The MP4 as `video_references` in `omni_reference` mode, beside the approved start frame as an image reference — or, in the scene form (v2.49, `prompting-craft.md` §12), beside the approved sheets with no start frame. Duration = the blocking's duration |
| `minimax_h3` | The MP4 in one of its three video slots, with identity as image references. It cannot mix frames and references in one call (`assets/higgsfield-rates.json` → call_contract, `mix: false`), so no start frame |
| `wan3_0` | Video references natively. Mind its 720p default and the `duration: -1` trap (`ai-generation.md`) |
| `kling4_0` | `reference-to-video` mode takes a video reference (`assets/higgsfield-rates.json` → call_contract) |
| `kling3_0` | No video references. Use the clean `first.png` and `last.png` (and `cut-<t>s.png`), each restyled through the frame gate from the same identity references, as start and end frames (`motion-design.md` §2.1) |

Higgsfield's own 3D scene builder generates video through a tool the gate refuses
(`scene_builder_3d_generate_video`, since 2.19.1). The route is this file's render plus `generate_video`.

## 6. The prompt

`blocking.py prompt` emits the blocks a blocked clip needs, in the house grammar:

- `[BLOCKING]`: the scope line (take camera, framing, cut times, positions and facing; the colours,
  mannequins, boxes, grid and flat light are not visual targets), then the computed marks at each stage's
  start and end.
- `[LEGEND]`: one line per colour, plus the stand-in line for grey.
- `[PRECEDENCE]`: camera, cuts, timing, framing and positions follow the blocking; faces, wardrobe,
  product and location follow the reference images; performance, hands, light and sound follow the text.
- `[CAMERA]`: per stage, the size, the subject (or a two-shot or group, or a part: "the host's feet"),
  the lens, the height and tilt, the camera's own move (pushes, pulls, arcs, follows, leads, pans, tilts,
  rises, lowers, trucks, zooms, or locked off), the declared moves ("worms eye rise → arc left"), the rigs
  ("handheld → on a steadicam, floating"), then the measured beats: holds, eases, snaps and creeps with
  their peak speeds and overshoots, the Dutch, focus pulls and flinches (§3a). A subject that moves past a
  static camera is not a pull-back.
- `[MOTION]`: START / MID / END, with MID listing the computed events (walks, turns, sitting down and
  standing up, who looks at whom, pick-ups, put-downs).
- `[SOUND]`: the blocking is silent; nothing in the clip's sound comes from it.

Every `TBD` is the writer's: the performance, the aftermath, the sound policy. `prompt_lint.py` FAILs
an unresolved `TBD`. The frontmatter declares the blocking as a reference:
`role: video_references`, `what: blocking`, `manifest:`, `value:` (the media id of the uploaded MP4) and
`not: mannequins, flat colours, floor grid, grey boxes`.

The computed text gives the **lens in mm, not the FOV in degrees**. FOV-in-degrees was tested for frames
and failed backwards (`prompting-craft.md` §11b). It is still open for video and stays out until tested.
`camera` prints the degrees for anyone who wants them.

The vendor's own blocking prompts carry the same parts: a legend, a precedence rule, choreography in
text because the boxes stand still, and nothing inherited from the blocking's audio [VENDOR · Higgsfield
blog, "GPT Astra 6 + Blender + Higgsfield", 2026-09-12, read 2026-10-23]. Theirs run to thousands of characters because they
describe geometry. Ours stay near the house band (about 2,000 characters before the performance is
written) because the geometry is in the video.

## 7. Approval and the gate

`gate.py approve blocking:<SHOT>` needs `script` approved first. It refuses an artifact that is not a
`.blocking.manifest.json` under the job, and refuses one whose listed files are missing or changed since
the build (`blocking.py verify` runs the same check). It records the manifest's sha256 and the media id
of the uploaded MP4.

On `generate_video`, a clip prompt with a `what: blocking` reference is **denied** unless all three hold:

1. `blocking:<SHOT>` is approved.
2. The reference's `value` is the approved media id.
3. The manifest it names still hashes to the approved one.

An unapproved blocking steers a clip as hard as an unapproved start frame.

`prompt_lint.py` WARNs until the bake-off:

- `[LEGEND]` or `[PRECEDENCE]` missing on a blocked clip;
- a legend colour from the manifest that the prompt never names;
- a clip duration that differs from the blocking's;
- a blocking reference with no `manifest:` or no `not:`.

## 8. Running Blender

- **Cloud container:** `pip install bpy` gave Blender 5.2.3 on Python 3.13. Workbench at 540 × 960 with
  the mannequin bodies runs at 1.4–2.2 s a frame on two CPUs (the rigid 2.21.0 mannequins ran at 0.8),
  so a 5–7.5 s shot renders in about 3–5 minutes [measured · seven preset builds, 2026-10-23]. The 2.24.0
  presets (10–14 s, environments, two builds at a time) took 17–25 minutes each, 3.4–4.5 s a frame
  [measured · eight preset builds, 2026-10-23]. A concept still in EEVEE takes 30–45 s.
  For a quick look while authoring, `BLOCKING_FRAME_STEP=24` makes `build()` render one frame a second
  (call it from Python). `blocking.py build` refuses to run with the variable set, so a quick look can
  never become the build someone approves.
- **A Mac with Blender.app:** `blender -b --python scripts/blocking.py -- build <spec> -o <dir>`.
  `check`, `camera`, `map`, `prompt` and `verify` need only Python and Pillow.
- **The device VM** used on 2026-10-23 had no `bpy`; Blender.app on the Mac itself was not checked.

The reference video does not need to be sharp: it carries geometry, not texture. Check the model's
minimum input size in `models_explore` before the first upload.

## 9. What it cannot do, and what the bake-off has to answer

- It reads geometry, not performance. It cannot say whether a pose reads or a move is motivated
  (`direction.md`, `motion-craft.md`).
- The mannequins have no fingers, no expression and three poses (stand, sit, lean). Gesture and
  performance stay in the text.
- Imported models are wired in for props and set pieces (§3e). A rigged character from an asset library
  (for example BlendSwap's Body Mechanics Rigs) is not yet: the mannequin is still the body. When it is,
  the asset's licence goes in the manifest with the file, as a model's does.
- The camera rigs, springs, anticipation and bank limits are house values set by eye (§3a). Whether a
  video model follows a handheld overshoot or an FPV bank from the reference is open for the bake-off.
- **Open, for lab-00011:**
  - Does each route follow the camera and the positions better than the same prompt without the
    blocking?
  - Do legend colours or mannequin shapes leak into the output?
  - Do the computed marks help, or crowd the prompt?
  - Does a 540 × 960 reference work as well as a sharper one?
  - Do the `kling3_0` restyled first and last frames hold identity?
  - Does a blocking hold two subjects moving in different directions, and a non-human body? One festival
    team said no to both, and yes for one subject at an exact camera speed (§1, HFF-04). Not measured here.
