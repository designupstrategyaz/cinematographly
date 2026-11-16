# World design — the exterior is designed once, before the frames, and every shot inherits it

A demo was killed on 2026-10-27. The plugin approached the scenario shot by shot. Birds and a boat were added to
start and end frames as separate image edits, with no count, heading or speed, so the video model invented
flocks and swoops to bridge them, and every regeneration re-rolled them. A species that does not live there was
noticed and let through. A long route was squeezed into one 5 s clip at about 12× the move table's speed, and the
warning was never answered. There were four changes of direction in one day, none of them locked. The owner
asked for the approach to change, not the golf: *"don't focus on the golf itself, but how the plugin approached
the scenario."* Research and a three-judge council are in lab record lab-00020 (not shipped). The decisions are in
the world-design proposal of 2026-10-27 [studio history]. `scripts/world.py` and `prompt_lint.py` enforce it.

## 1. The approach — world first

1. **Design the world before a single frame.** `world.py init <job> --location <LOC>` writes
   `00-brief/world/<LOC>.world.json`. One card covers one location at one time of day and one weather. Dawn
   and noon at the same place are two cards. A card can be reused on a later job with `--from`.
2. **The owner approves it:** `gate.py approve world:<LOC> --artifact 00-brief/world/<LOC>.world.json`. The
   approval refuses a card that fails `world.py check`.
3. **Every exterior frame and clip names its card** in the front matter: `world: <LOC>`. Its words come from
   the card (`world.py cues <job> --location <LOC> --shot <S>` prints the `[ENVIRONMENT]` and `[LIGHTING]`
   lines), so every shot describes the same world.
4. **The prompt lint holds each prompt to the card** (§5). A changed card makes every prompt of that location
   stale until the owner approves it again. A change of direction is exactly that, and it is no longer free.
5. **Each returned clip is read against the card** before `approve clips` (§7).

Why the model will not supply a coherent world itself:

- **Physics-IQ:** the best video model scored 29.5 against a physical baseline of 100, and the most realistic
  one scored 10.0. Realism and physics were uncorrelated [PEER-REVIEWED · Motamed et al., WACV 2026].
- **VBench:** multiple moving objects are a weak spot, and holding consistency costs motion [PEER-REVIEWED · Huang
  et al., CVPR 2024].
- **Inbetweening:** two keyframes do not define the path between them; the model invents it [PEER-REVIEWED ·
  Wang et al., ICLR 2025].

Every element that moves is a degree of freedom the model fills with something plausible-looking and physically
arbitrary. The card fixes the numbers, and the shot carries as few movers as the story allows.

## 2. What the card holds

| Field | What to decide | Source |
|---|---|---|
| place, biome, season, date, time | Real (`--real`) or invented. An invented place still names its biome | — |
| sun | Azimuth and elevation for that place, date and time. Shadows follow: length = height ÷ tan(elevation) | NOAA GML solar calculator, with the date read [PRIMARY] |
| wind | Beaufort force and the direction it blows **from**. One number moves the grass, trees, flags, water, smoke, cloud drift and which way birds face (table below) | Royal Meteorological Society [PRIMARY] |
| sky | WMO genus (one per level), cover (clear, few, scattered, broken, overcast), the drift direction, the light | WMO International Cloud Atlas [PRIMARY] |
| visibility_km, layers | Near, middle and far: what is in each and how far. Visibility sets how fast the far layer fades | Koschmieder; fog < 1 km, mist 1–2, haze 2–5 [PRIMARY-derived] |
| scale_anchors | At least one object of known size: a person, a door, a 1.2 m post | `production-design.md` §2 |
| land, water | The ground cover and plants for the place and season; the water's state follows the wind | — |
| subjects | What the shots are about (never counted as background life) | — |
| life | Background life cast like extras (§4). **None is the default** | eBird for species [PRIMARY]; Pennycuick et al. 2013 for bird speeds [PEER-REVIEWED] |
| plausible | For a real place, the species, vessels and vehicles that occur there, each with its source | eBird bar charts by region and week [PRIMARY]; a harbour record |
| max_movers_per_shot | Cast groups per shot, 1 by default [assumed] | jury K3 |

**Beaufort, as the card uses it** (10-minute mean at 10 m):

| Force | km/h | Land | Sea |
|---|---|---|---|
| 0 | < 1 | smoke rises straight up | like a mirror |
| 1 | 1–5 | smoke drifts | ripples |
| 2 | 6–11 | leaves rustle | small wavelets |
| 3 | 12–19 | leaves and small twigs in constant motion, light flags extended | large wavelets |
| 4 | 20–28 | dust and loose paper raised, small branches move | small waves, fairly frequent whitecaps |
| 5 | 29–38 | small leafy trees sway | moderate waves, many whitecaps |
| 6 | 38–49 | large branches move, wires whistle | large waves, extensive foam crests |
| 7 | 50–61 | whole trees move | foam blown in streaks |

**Depth in far space.** Beyond about 30 m the cues that still work are occlusion, relative size, height in the
frame and aerial perspective [PEER-REVIEWED · Cutting & Vishton 1995, as cited]. Aerial perspective means
contrast falls exponentially with distance, dark objects pale and turn blue, and edges and detail soften
[PRIMARY · Britannica; Leonardo: "Colours become weaker in proportion to their distance"]. So the card names
three layers and an anchor. "Scale is sold by haze, layers, texture scale and a near foreground"
(`aerial-and-fpv.md` §3).

**Sky.** Clouds sit on three levels: high is cirrus, cirrocumulus and cirrostratus; middle is altocumulus,
altostratus and nimbostratus; low is stratocumulus, stratus, cumulus and cumulonimbus. A sky is one genus per
level, a cover and a drift. "Dramatic clouds" is an adjective stack. "Scattered fair-weather cumulus drifting
north-east, the sun out between them" is a sky the model can hold across shots.

## 3. What the card's own check refuses (`world.py check`, run by `approve world:`)

- an unfilled field;
- a sun, wind, sky, visibility or layer that is missing or out of range;
- a cloud genus that is not one of the WMO's ten;
- a water state the wind cannot make (glassy at force 3, whitecaps at force 2);
- a life entry with a missing field;
- a species not on a real place's list, unless the owner overrides it (`world.py override … --quote "…"`, kept
  on the card where the client can see it);
- a flying bird outside 8–22 m/s. Measured mean air speeds run 11–20.6 m/s across 31 species; the range is
  widened [assumed];
- a still animal or vessel with a speed;
- a mover in the end frame alone (§5);
- an end position against the heading;
- more cast groups in a shot than the card allows.

It also warns about vehicles and vessels without a sourced speed (no table is verified here), and birds
landing or taking off without a heading into the wind.

## 4. Background life is cast, like extras

The rule in `specifics-catalogue.md` §3.11 for people now covers animals, vehicles and vessels. Each life entry
gives:

| Field | Example |
|---|---|
| id, species | L1, herring gull |
| count | 3 |
| behaviour | crossing · soaring · circling · landing · resting · moored · driving |
| heading | left to right, quartering into the wind |
| speed_ms and speed_source | 12, Pennycuick et al. 2013 |
| frame | upper third |
| carry | true: it is in the next shot, same count and heading |
| shots | S1, S2 |
| in_frames | start · both · none |

A flock keeps one heading and near-constant spacing (separation, alignment, cohesion; Reynolds 1987). It does
not split and re-form at random. **Uncast life is not in the frame.** Plate hygiene still holds
(`production-design.md` §5b): cast life is necessary, uncast life is removed.

## 5. What the prompt lint refuses on a `world:` prompt (`[world]` in the message)

- **The card is not approved, or changed since.**
- **An uncast mover:** a bird, animal, boat or vehicle named in the frame's `[ENVIRONMENT]` or the clip's
  `[MOTION]` that the card does not cast for that shot. The card's `subjects` are exempt.
- **An explicit contradiction:** a sky word against the card's sky (overcast against scattered cumulus); a calm
  word at force 3 or more; a whitecap or gale word at force 3 or less; night with the sun up. Low-sun words with
  a high sun only warn (jury K2: refuse the explicit, warn the uncertain).
- **An image edit that adds a mover** (`edit_of:` or a reference to a frame in `02-startframes/`). Edits remove
  things or correct static ones. To add life, cast it in the card, have the card approved and regenerate the
  frame (jury B6).
- **Start and end frames — both or neither** (jury K4). A mover in the end frame alone is refused in the card. A
  mover in both frames must be where its heading and speed take it in the clip's length; the lint raises a ⚑
  warning to check that on the two stills. Better still, keep movers out of the end frame and put the motion in
  the clip prompt.
- **An aerial with no card.** An aerial is all world. Use `world: none (<why>)` only when that is true.
- **An open stop** (§6).

**The ⚑ warnings must be answered before spend** (jury B9). Measures still warn, so house rule C4 stands. But a
⚑ warning keeps the prompt from linting until it is fixed or answered: `world.py accept <job> <prompt> --reason
"…"`. The answer is bound to the prompt's text, so a changed prompt needs a new one. There are three ⚑ warnings:

- **an exterior with no card:** the prompt reads as outdoors and declares none;
- **the motion budget** (`aerial_qa.py`): `aerial: path_m=` against the move table — "402 m in 5 s is 80 m/s, 12×
  the table's 3.6–6.7 m/s; one clip covers 18–34 m: fly a 34 m segment, or cut the route into 12 clips." A route
  move with no `path_m=` is asked for one;
- **a mover on both frames:** check its positions on the stills.

## 6. A noticed problem is a stop, not a note (jury B11, K6)

When anyone notices that something doesn't belong (the wrong species, the wrong season, a sky the place cannot
have), open a stop: `world.py stop <job> --what "…"`. While a stop is open, no prompt in the job lints, so
nothing is spent. A fix closes it (`world.py close <job> --stop N --fixed "…"`). Keeping the thing anyway
needs the owner's own words (`--override --quote "…"`).

A change of direction changes the card. Every frame and clip of that location is then stale until they approve
it again. Only the approvals that depend on the changed card are reopened (jury K7).

## 7. The returned clip, read against the card (jury B12)

On the contact sheet (built before any draft is shown), count the movers and check:

- their heading;
- the sky;
- the wind cues;
- the sun's side;
- anything that appeared.

Log the read:

```
world.py read <job> --shot <S> --clip <file> --movers <N> --obs "…" --new none
```

A count that differs from the card, or anything new, is a RETAKE. `gate.py approve clips` refuses an exterior
clip whose read is missing, failing, or about bytes that changed.

**In Resolve:** `world.py console <job>` writes `07-edit/resolve-production-console.world.py`. It puts one
marker on each exterior clip with its world and the read: Green PASS, Red RETAKE, Blue unread.

## 8. What this file does not know

- **The numbers marked [assumed]:** one cast group per shot, the 8–22 m/s window for flying birds, and 15° for
  golden light. Calibrate them on real jobs.
- **Speeds for vehicles, vessels and cloud drift.** No sourced table was found; the card asks for a source or the
  word "unverified".
- **Tides and currents** are free text; no source is wired in.
- **Weather or time changing within one video** needs a second card; there is no transition rule.
- **How long a card takes on a first location** has not been measured. The jury asked for a timed pilot.
- **Lookups are by hand,** with their source: NOAA for the sun, eBird for species. No fetch is wired in (jury K8).
