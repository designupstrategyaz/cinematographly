#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""blocking.py — 3D blocking for one shot: a spec Claude writes, checks a script runs, a Blender render the
human approves before a credit is spent, and prompt text computed from the same geometry
(references/blocking.md).

  python3 blocking.py example [--preset NAME] [-o S3.blocking.json]  # a starting spec (presets below)
  python3 blocking.py check   S3.blocking.json        # schema + geometry + camera; FAIL exits 1
  python3 blocking.py camera  S3.blocking.json        # per stage: size, lens, height and tilt, the move, speeds
  python3 blocking.py map     S3.blocking.json -o m.png   # top-down map drawn by code (no Blender)
  python3 blocking.py prompt  S3.blocking.json        # the clip-prompt blocks, computed from the geometry
  python3 blocking.py build   S3.blocking.json -o 02-startframes/_blocking/S3
        # Blender: clean reference MP4 (what the video model gets) + labelled review sheet + map +
        # first/last/cut frames + camera.json + manifest with sha256 per file.
        # `pip install bpy` (a Python that matches the bpy wheel), or inside Blender:
        # blender -b --python blocking.py -- build S3.blocking.json -o <dir>
  python3 blocking.py concept S3.blocking.json -o <dir> [--times 0,4,9] [--time golden]
        # Blender EEVEE: the same scene lit, with materials — concept stills for judging the place
  python3 blocking.py verify  <manifest>              # every file of a build still matches its hash
  python3 blocking.py moves | envs                    # the 73 named moves and their rigs; the 20 environments
  python3 blocking.py --selftest                     # no Blender needed

WHY A SPEC AND NOT bpy CODE. An LLM writing free-form Blender Python gets scale, facing and camera framing
wrong in ways it cannot see. The same model filling a constrained spec, with code doing the placement,
passes far more spatial constraints: SceneCraft (ICML 2024) scored 88.9 on constraint passing against 5.6
for an LLM writing Blender code directly; Holodeck (CVPR 2024) has the LLM propose relations and a solver
place the objects. Here the LLM writes positions in metres, sizes come from a dimension table, and the
camera is written in film terms (a shot plan: subject, size, lens, height, side, the move) that code turns
into a path.

THE RENDER. Rooms have walls with their doors and windows cut out; furniture is built from its parts
(blocking_kit.py). Every actor is a mannequin: a smooth torso-and-head surface and four limb surfaces,
skinned to 16 bones; IK arms and legs; walks that speed up out of a stop, keep an even pace and slow into
the next stop, with the feet planted, the heel peeling up behind and the hips rising over the planted
foot; a sit-down that moves; a head that turns to what it looks at (blocking_rig.py). A whole location can
come from a template (`env`: kitchen, café, street, road, rooftop, cyc…, blocking_env.py), with cars that
drive and passengers in them; a shape that matters is built from its numbers (a floor plan, a lathed
bottle, an extruded counter) or imported from a model file with its licence (blocking_kit.py).

THE CAMERA. A shot names one of 73 moves (a pivot whip, a worm's-eye rise, a drone reveal, an FPV chase, a
dolly zoom…) and the rig that carries the lens (blocking_camera.py). The move builds the ideal path; the
rendered camera chases it through the rig's springs, so a handheld lags, anticipates, overshoots and
settles, a drone banks into its turns and a motion-control arm stops dead. Joined moves blend; framings
hold the angle the subject faced when the shot began. The prompt describes the camera that renders, in
measured beats.

THE CONCEPT LOOK. `concept` renders the same scene in EEVEE with materials, a time of day and practical
lights (blocking_look.py): frames for judging the place, never the reference the gate approves.

WHY THE PROMPT IS COMPUTED. The text and the render must agree on who is frame left, who faces the camera
and when the cut lands. `prompt` derives those lines from the geometry, so the writer adds performance,
not positions.

WHAT IT CHECKS (FAIL exits 1; WARN prints):
  FAIL  schema: unknown kind / colour / shot size / camera height / look_at id, a missing field, a key time
        outside the duration, two camera keys at one time, a cut with no camera key at its time, shots
        that do not tile the duration
  FAIL  a colour used by the set, an actor, a prop or a label that the legend does not explain, or a legend
        colour nothing uses — the legend is what the video model is told the colours mean
  FAIL  two actors interpenetrate, or an actor stands inside a set piece or a wall (sampled every 0.1 s)
  FAIL  the camera passes inside a set piece, a wall or an actor (unless the piece says "camera_through")
  FAIL  the duration is outside the target model's measured range (assets/higgsfield-rates.json)
  FAIL  a prop "on" a set piece that does not exist, or held by a hand that is not <actor>.left/.right
  WARN  a cut crosses the line of action between the two named actors (unless "cross_line": true); a
        continuous move across it is allowed, because the audience sees the camera travel
  WARN  a cut between two framings of one subject less than 30° apart and less than two sizes apart (a
        jump cut); a moving subject whose screen direction flips across a cut
  WARN  the camera pans faster than 60°/s (unless "whip": true), travels faster than 3 m/s (unless
        "vehicle": true), or starts or stops with a jolt
  WARN  the subject is hidden behind something for 0.3 s or more (unless "occlusion_ok": true)
  WARN  the current camera subject, or an id in the key's "frame" list, leaves the frame (a listed prop must
        stay in the inner 85 %, the safe area); on a vertical frame the subject's eyes leave the 15–65 %
        band; an actor marked "face_out_of_frame" shows their chin; a key's computed size is more than one
        step from the size it asks for; a shot's declared move is not what the camera does
  WARN  a head or a prop passes within 0.35 m of the lens (it fills the frame and the model distorts it)
  WARN  more than a quarter of the frame is empty void (no wall, set piece or floor behind the action) —
        the video model invents whatever the render leaves empty; set "sky": true for an exterior
  WARN  a hand that holds two props at once, or a prop picked up from further than an arm's reach; an
        actor sitting where there is no seat
  FAIL  a floor-plan opening that does not fit its wall; a shape that cannot be read; a model with no file
        on this machine, no `size`, no `source` for a download, or a licence not cleared for client work
        (CC0, client, own; CC-BY and CC-BY-SA WARN that the hand-off credits the author)
  WARN  a focus pull to something behind the camera or out of frame; a shape whose `size` disagrees with
        what its geometry measures

WHAT IT CANNOT DO: it reads geometry, not performance. It cannot tell whether a pose reads or a move is
motivated, or whether the video model will follow the render: the blocking bake-off measures that. The
mannequins have no fingers and no expression; choreography and performance stay in the prompt.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
RATES = os.path.join(SKILL, "assets", "higgsfield-rates.json")
SPEC_VERSION = 3
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import blocking_kit as KIT   # noqa: E402  (pure Python parts; Blender only inside its builders)
import blocking_rig as RIG   # noqa: E402
import blocking_camera as CAM   # noqa: E402
import blocking_env as ENV   # noqa: E402
import blocking_look as LOOK   # noqa: E402

# Real-world sizes in metres (w, d, h). An LLM guesses scale badly; a table does not. Extend it rather than
# writing "size" by hand — a size given in the spec overrides the table for that one piece.
DIMENSIONS = {
    "box": (1.0, 1.0, 1.0), "wall": (4.0, 0.1, 2.6), "door": (0.9, 0.05, 2.1), "window": (1.2, 0.05, 1.2),
    "floor_mark": (0.3, 0.3, 0.005), "rug": (2.0, 1.4, 0.01),
    "table": (1.2, 0.8, 0.75), "round_table": (1.0, 1.0, 0.75), "desk": (1.4, 0.7, 0.75),
    "counter": (1.8, 0.6, 0.9), "island": (2.0, 1.0, 0.9), "chair": (0.45, 0.45, 0.9),
    "stool": (0.4, 0.4, 0.65), "sofa": (2.0, 0.9, 0.85), "bed": (1.6, 2.0, 0.55),
    "shelf": (1.0, 0.35, 1.8), "fridge": (0.7, 0.7, 1.8), "car": (4.5, 1.8, 1.45), "plant": (0.4, 0.4, 1.1),
    "lamp": (0.4, 0.4, 1.6), "tv": (1.2, 0.25, 0.75),
    "laptop": (0.32, 0.22, 0.24), "phone": (0.075, 0.009, 0.15), "bottle": (0.07, 0.07, 0.16),
    "jar": (0.09, 0.09, 0.11), "mug": (0.09, 0.09, 0.10), "glass": (0.07, 0.07, 0.15), "plate": (0.26, 0.26, 0.02),
    "bag": (0.35, 0.15, 0.3), "book": (0.15, 0.03, 0.22), "box_small": (0.2, 0.2, 0.2), "tube": (0.04, 0.04, 0.17),
}
WALKABLE = {"floor_mark", "rug"}
# The height a prop rests at on top of a piece; defaults to the piece's height.
SURFACE = {"chair": 0.45, "stool": 0.65, "sofa": 0.42, "bed": 0.55, "shelf": 1.0}
# Pieces an actor may sit on (seat height). Seats with a back carry it on their local +Y side: at rot 0 the
# back is away from the front of the set, so a sitter faces the front (facing -90).
SEAT = {"chair": 0.45, "stool": 0.65, "sofa": 0.42, "bed": 0.55}
# the environments' kinds (blocking_env.py): sizes, walkable surfaces, the heights things rest at
for _k, _v in ENV.DIMENSIONS.items():
    DIMENSIONS[_k] = _v
WALKABLE |= ENV.WALKABLE_KINDS
SURFACE.update(ENV.SURFACES)
KIT.EXTRA_PARTS.update(ENV.PARTS)
VEHICLE_KINDS = ("car",)
COLORS = {
    "red": (0.85, 0.15, 0.15), "blue": (0.15, 0.30, 0.90), "green": (0.15, 0.65, 0.25), "yellow": (0.95, 0.80, 0.05),
    "orange": (0.95, 0.50, 0.10), "purple": (0.55, 0.25, 0.75), "cyan": (0.10, 0.75, 0.85),
    "magenta": (0.90, 0.20, 0.70), "white": (0.95, 0.95, 0.95), "grey": (0.62, 0.62, 0.62),
    "darkgrey": (0.35, 0.35, 0.35), "brown": (0.50, 0.33, 0.18), "black": (0.06, 0.06, 0.06),
    "beige": (0.80, 0.72, 0.58), "teal": (0.10, 0.50, 0.50),
}
NEUTRAL = "grey"                                  # needs no legend line: the prompt calls grey a stand-in
# Vertical extent of the subject in frame, metres, per shot size (the chain's Size column vocabulary).
SIZES = ["ECU", "CU", "MCU", "MS", "MWS", "WS", "EWS"]
SIZE_EXTENT = {"ECU": 0.15, "CU": 0.32, "MCU": 0.55, "MS": 0.95, "MWS": 1.35}   # WS / EWS scale with height
FOV_SNAP = [180, 107, 84, 63, 47, 29, 18, 12, 8]   # degrees — the steps Higgsfield's Seedance guide uses
SENSOR_MM = 36.0                                  # spans the LONG side of the frame (Blender's AUTO fit)
BODY_R = 0.22                                     # an actor's footprint radius
POSES = ("stand", "sit", "lean")
BODIES = ("mannequin", "segments")                # a smooth skinned mannequin, or rigid primitives (the fallback)
CAM_HEIGHTS = ("level", "eye", "chest", "waist", "hip", "knee", "low", "high", "overhead")
REACH_M = 0.75                                    # body centre to a prop at pick-up: arm plus a small lean
RAMP_S = 0.35                                     # the shortest hand move; longer moves run at HAND_MPS
HAND_MPS = 1.2                                    # average hand speed, m/s (a smoothstep peaks at 1.5× this)
HOLD_AT = ("waist", "chest", "face")              # where a held prop sits: low, presented, shown beside the face
VOID_WARN = 0.25
NEAR_LENS_M = 0.35
SAFE = 0.85                                       # a listed prop must sit inside the inner 85 % of the frame
# Handheld profiles: position amplitude (m), rotation amplitude (deg), lowest and highest drift frequency (Hz).
# "breathing" is the Higgsfield blocking's "never locks off; always drifts — long slow waves, no fast jitter".
HANDHELD = {"none": (0.0, 0.0, 0.1, 0.1), "breathing": (0.006, 0.25, 0.10, 0.40),
            "handheld": (0.015, 0.6, 0.20, 1.1), "walking": (0.02, 0.8, 0.30, 1.8)}
MAX_PAN_DPS, MAX_TRAVEL_MPS, MAX_ACCEL = 60.0, 3.0, 6.0      # m/s² a rig may change speed by (rigs can raise it: max_acc)
# Named moves a shot may declare, and the computed words that confirm each one.
MOVES = {"static": set(), "locked": set(), "push_in": {"pushes in"}, "dolly_in": {"pushes in"},
         "pull_back": {"pulls back"}, "dolly_out": {"pulls back"}, "reveal": {"pulls back", "rises", "arcs"},
         "arc_left": {"arcs"}, "arc_right": {"arcs"}, "orbit": {"arcs"}, "crane_up": {"rises"},
         "crane_down": {"lowers"}, "pan": {"pans"}, "tilt": {"tilts"}, "zoom_in": {"zooms"}, "zoom_out": {"zooms"},
         "follow": {"follows"}, "lead": {"leads"}, "track": {"follows", "leads"}, "truck": {"trucks"}}


def ext_for(size: str, height: float) -> float:
    if size == "WS":
        return height * 1.25
    if size == "EWS":
        return height * 4.0
    return SIZE_EXTENT[size]


def size_for(extent: float, height: float) -> str:
    """The shot size whose extent is nearest (log scale) to this one."""
    best, bd = "MS", 9e9
    for s in SIZES:
        d = abs(math.log(max(extent, 1e-3) / ext_for(s, height)))
        if d < bd:
            best, bd = s, d
    return best


# ── geometry helpers ─────────────────────────────────────────────────────────────────────────────────────
def lerp(a, b, f):
    return a + (b - a) * f


def ang_lerp(a, b, f):
    d = (b - a + 180) % 360 - 180
    return a + d * f


def ang_diff(a, b):
    return (b - a + 180) % 360 - 180


def dims(piece: dict) -> tuple:
    if piece.get("size"):
        return tuple(float(v) for v in piece["size"])
    return DIMENSIONS[piece.get("kind", "box")]


def rect_contains(piece: dict, x: float, y: float, pad: float = 0.0) -> bool:
    """Is (x, y) inside the piece's footprint (rotated rectangle), grown by pad?"""
    w, d, _ = dims(piece)
    px, py = piece["pos"][0], piece["pos"][1]
    r = math.radians(-float(piece.get("rot", 0)))
    dx, dy = x - px, y - py
    lx, ly = dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)
    if piece.get("shape") and not piece.get("_no_fp"):      # a precise shape: its real outline, not its bounds
        fps = KIT.shape_footprints(piece["shape"])
        if fps:
            return any(KIT.poly_contains(fp, lx, ly, pad) for fp in fps)
    return abs(lx) <= w / 2 + pad and abs(ly) <= d / 2 + pad


def all_pieces(spec: dict) -> list:
    """Every set piece the render draws: rooms and floor plans expanded into their walls, doors and windows."""
    out = []
    for p in spec.get("set", []):
        if p.get("kind") == "room":
            out += KIT.room_walls(p)
        elif p.get("kind") == "plan":
            out += KIT.plan_walls(p)
        else:
            out.append(p)
    return out


def model_assets(spec: dict) -> list:
    """Every imported model the shot uses, with its licence record (written into the manifest)."""
    out = []
    for p in spec.get("set", []) + spec.get("props", []):
        md = p.get("model")
        if md:
            f = os.path.expanduser(md.get("file", ""))
            out.append({"id": p.get("id"), "file": os.path.basename(f), "sha256": sha(f) if os.path.isfile(f) else None,
                        "source": md.get("source"), "author": md.get("author"), "licence": md.get("licence"),
                        "size_m": p.get("size"), "fit": p.get("fit", "contain")})
    return out


def solids(spec: dict) -> list:
    """What a body or the lens cannot pass through: furniture, walls; not rugs, marks, door or window gaps."""
    return [p for p in all_pieces(spec) if p.get("solid", True) and p.get("kind") not in WALKABLE
            and not p.get("walkable")]


def seat_under(spec: dict, pos) -> dict | None:
    return next((p for p in spec.get("set", []) if p.get("kind") in SEAT and rect_contains(p, pos[0], pos[1], 0.05)),
                None)


def actor_heights(a: dict, pose: str, seat: float | None = None) -> dict:
    """Heights in metres for a pose. Standing proportions are adult averages scaled by the actor's height."""
    h = float(a.get("height", 1.70))
    if pose == "sit":
        hip = (seat if seat is not None else float(a.get("seat_height", 0.45))) + 0.07
        top = hip + 0.47 * h
        return {"seat": hip - 0.07, "hip": hip, "waist": hip + 0.05 * h, "chest": hip + 0.19 * h,
                "shoulder": hip + 0.29 * h, "eye": top - 0.064 * h, "top": top, "knee": hip - 0.02}
    k = 0.97 if pose == "lean" else 1.0
    return {"seat": None, "hip": 0.53 * h * k, "waist": 0.60 * h * k, "chest": 0.72 * h * k,
            "shoulder": 0.82 * h * k, "eye": 0.936 * h * k, "top": h * k, "knee": 0.285 * h}


def _by_id(spec: dict, i: str):
    a = next((x for x in spec.get("actors", []) if x.get("id") == i), None)
    if a:
        return "actor", a
    v = next((x for x in spec.get("vehicles", []) if x.get("id") == i), None)
    if v:
        return "vehicle", v
    p = next((x for x in spec.get("props", []) if x.get("id") == i), None)
    if p:
        return "prop", p
    s = next((x for x in all_pieces(spec) if x.get("id") == i), None)
    return ("set", s) if s else (None, None)


def resolve_facing(spec: dict, f, pos: tuple, t: float) -> float:
    """facing: degrees (0 = +X / screen right on the map, 90 = +Y / away from the front, -90 = toward the
    front), an actor id, "camera", or [x, y]. Returns degrees."""
    if isinstance(f, (int, float)):
        return float(f)
    target = None
    if isinstance(f, list) and len(f) == 2:
        target = (float(f[0]), float(f[1]))
    elif f == "camera":
        cam = camera_at(spec, t)
        target = (cam["pos"][0], cam["pos"][1]) if cam else None
    elif isinstance(f, str):
        other = next((a for a in spec.get("actors", []) if a["id"] == f), None)
        if other:
            target = actor_at(spec, other, t, resolve=False)["pos"]
    if target is None:
        return -90.0
    return math.degrees(math.atan2(target[1] - pos[1], target[0] - pos[0]))


def _keys_around(keys: list, t: float):
    ks = sorted(keys, key=lambda k: float(k["t"]))
    if t <= float(ks[0]["t"]):
        return ks[0], ks[0], 0.0
    for a, b in zip(ks, ks[1:]):
        ta, tb = float(a["t"]), float(b["t"])
        if ta <= t <= tb:
            return a, b, (t - ta) / (tb - ta) if tb > ta else 0.0
    return ks[-1], ks[-1], 0.0


def _moving(ks: list, i: int) -> bool:
    return 0 <= i < len(ks) - 1 and math.dist(ks[i]["pos"], ks[i + 1]["pos"]) > 1e-6


def segment_at(ks: list, t: float) -> tuple:
    """(i, f): the key segment holding t and the time fraction through it (keys sorted)."""
    if t <= float(ks[0]["t"]) or len(ks) == 1:
        return 0, 0.0
    for i in range(len(ks) - 1):
        ta, tb = float(ks[i]["t"]), float(ks[i + 1]["t"])
        if ta <= t <= tb:
            return i, (t - ta) / (tb - ta) if tb > ta else 1.0
    return len(ks) - 2, 1.0


def path_cum(ks: list) -> list:
    out = [0.0]
    for ka, kb in zip(ks, ks[1:]):
        out.append(out[-1] + math.dist(ka["pos"], kb["pos"]))
    return out


WALK_RAMP_S = 0.6    # seconds to reach walking pace from a stop, and to slow into one (assumption)


def path_run(ks: list, t: float):
    """(first key, last key) of the walk holding t — consecutive moving segments between two stops — or None."""
    i, _ = segment_at(ks, t)
    if not _moving(ks, i):
        return None
    r0, r1 = i, i + 1
    while _moving(ks, r0 - 1):
        r0 -= 1
    while _moving(ks, r1):
        r1 += 1
    return r0, r1


def path_dist(ks: list, t: float, ramp: float | None = None) -> float:
    """Distance walked along the key path by time t. People accelerate out of a stop and slow into one and
    keep an even pace between (a trapezoid of speed with smooth ramps over each walk); intermediate keys
    are still met at their times by a smooth correction that is zero wherever the trapezoid already meets
    them."""
    cum = path_cum(ks)
    run = path_run(ks, t)
    if run is None:                              # standing still: the segment's two ends are the same place
        return cum[segment_at(ks, t)[0]]
    r0, r1 = run
    T0, T1 = float(ks[r0]["t"]), float(ks[r1]["t"])
    D0, D1 = cum[r0], cum[r1]
    T, D = T1 - T0, D1 - D0
    ta = min(WALK_RAMP_S if ramp is None else ramp, T / 3.0)
    V = D / (T - ta) if T > ta else 0.0

    def trap(x):
        if x <= 0:
            return 0.0
        if x >= T:
            return D
        if x < ta:
            u = x / ta
            return V * ta * (u ** 3 - u ** 4 / 2)
        if x > T - ta:
            u = (T - x) / ta
            return D - V * ta * (u ** 3 - u ** 4 / 2)
        return V * (ta / 2 + (x - ta))
    x = t - T0
    if r1 - r0 == 1:
        return D0 + trap(x)
    times = [float(ks[j]["t"]) for j in range(r0, r1 + 1)]
    errs = [(cum[j] - D0) - trap(times[j - r0] - T0) for j in range(r0, r1 + 1)]
    tt = min(max(t, times[0]), times[-1])
    seg = max([j for j in range(len(times) - 1) if times[j] <= tt] or [0])
    e = _spline(times, errs, ["auto"] * len(times), seg, tt)
    return D0 + min(D, max(0.0, trap(x) + e))


def point_on_path(ks: list, d: float) -> tuple:
    """((x, y), unit direction or None) at distance d along the key path."""
    cum = path_cum(ks)
    if len(ks) == 1 or d <= 0:
        j = 0
    else:
        j = next((i for i in range(len(ks) - 1) if cum[i] <= d <= cum[i + 1] and cum[i + 1] > cum[i]), None)
        if j is None:
            return tuple(ks[-1]["pos"][:2]), _path_dir(ks, len(ks) - 2)
        a, b = ks[j]["pos"], ks[j + 1]["pos"]
        f = (d - cum[j]) / (cum[j + 1] - cum[j])
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), _path_dir(ks, j)
    return tuple(ks[0]["pos"][:2]), _path_dir(ks, 0)


def _path_dir(ks: list, i: int):
    for j in list(range(max(i, 0), len(ks) - 1)) + list(range(max(i, 0) - 1, -1, -1)):
        a, b = ks[j]["pos"], ks[j + 1]["pos"]
        L = math.dist(a, b)
        if L > 1e-6:
            return ((b[0] - a[0]) / L, (b[1] - a[1]) / L, 0.0)
    return None


# Seats in a car, in its own frame (+x forward from the car's centre, +y left, z the cushion's height);
# a left-hand-drive car. "drive": "right" on the vehicle mirrors them. [assumption · a mid-size sedan]
SEATS_CAR = {"driver": (0.05, 0.37, 0.50), "passenger": (0.05, -0.37, 0.50),
             "rear_left": (-0.85, 0.40, 0.52), "rear_right": (-0.85, -0.40, 0.52)}
VEHICLE_RAMP_S = 1.6                              # seconds for a car to pull away or brake to a stop (assumption)


def vehicle_at(spec: dict, v: dict, t: float) -> dict:
    """A vehicle's pose at t: its centre on the ground and its heading (degrees, the way the nose
    points). Keys: [{t, pos: [x, y], heading}]; the heading follows the road when a key leaves it out."""
    ks = sorted(v.get("keys") or [{"t": 0, "pos": v.get("pos", [0, 0]), "heading": v.get("heading", 0)}],
                key=lambda k: float(k["t"]))
    d = path_dist(ks, t, ramp=float(v.get("ramp", VEHICLE_RAMP_S)))
    pos, dirv = point_on_path(ks, d)
    i, f0 = segment_at(ks, t)
    ka, kb = ks[i], ks[min(i + 1, len(ks) - 1)]
    if "heading" in ka or "heading" in kb or not dirv:
        ha = float(ka.get("heading", kb.get("heading", v.get("heading", 0))))
        hb = float(kb.get("heading", ha))
        heading = ang_lerp(ha, hb, _smooth(f0))
    else:
        heading = math.degrees(math.atan2(dirv[1], dirv[0]))
    return {"pos": pos, "heading": heading}


def actor_at(spec: dict, a: dict, t: float, resolve: bool = True) -> dict:
    if a.get("in"):
        # a passenger: the car carries them; they sit in their seat facing where the car points
        kind, v = _by_id(spec, a["in"])
        vs = vehicle_at(spec, v, t)
        sx, sy, sz = SEATS_CAR.get(a.get("seat", "driver"), SEATS_CAR["driver"])
        if v.get("drive") == "right":
            sy = -sy
        h = math.radians(vs["heading"])
        pos = (vs["pos"][0] + math.cos(h) * sx - math.sin(h) * sy, vs["pos"][1] + math.sin(h) * sx + math.cos(h) * sy)
        out = {"pos": pos, "pose": "sit", "seat": sz}
        if resolve:
            out["facing"] = vs["heading"]
        return out
    ks = sorted(a["keys"], key=lambda k: float(k["t"]))
    i, f0 = segment_at(ks, t)
    ka, kb = ks[i], ks[min(i + 1, len(ks) - 1)]
    pos = point_on_path(ks, path_dist(ks, t, ramp=a.get("ramp")))[0]   # "ramp": 0 = already moving at the cut
    pose = (ka if f0 < 0.5 else kb).get("pose", a.get("pose", "stand"))
    out = {"pos": pos, "pose": pose, "seat": None}
    if pose == "sit":
        s = seat_under(spec, pos)
        out["seat"] = (SEAT[s["kind"]] + float(s.get("z", 0))) if s else None
    if resolve:
        fa = resolve_facing(spec, ka.get("facing", -90), pos, t)
        fb = resolve_facing(spec, kb.get("facing", ka.get("facing", -90)), pos, t)
        out["facing"] = ang_lerp(fa, fb, _smooth(f0))
    return out


def heights_at(spec: dict, a: dict, t: float) -> dict:
    st = actor_at(spec, a, t, resolve=False)
    return actor_heights(a, st["pose"], st["seat"])


def _holds_for(spec: dict, actor_id: str, hand: str) -> list:
    out = []
    for p in spec.get("props", []):
        for hk in p.get("held", []):
            who, _, hd = str(hk.get("by", "")).partition(".")
            if who == actor_id and hd == hand:
                out.append((float(hk["from"]), float(hk["to"]), p, hk))
    return sorted(out, key=lambda x: x[0])


def hold_state(spec: dict, actor_id: str, hand: str, t: float) -> tuple:
    """(weight 0..1, prop id, at) — for callers that only need 'is this hand busy'."""
    best = (0.0, None, "chest")
    for f0, f1, p, hk in _holds_for(spec, actor_id, hand):
        w = 1.0 if f0 <= t <= f1 else (t - (f0 - RAMP_S)) / RAMP_S if f0 - RAMP_S < t < f0 else \
            1.0 - (t - f1) / RAMP_S if f1 < t < f1 + RAMP_S else 0.0
        if w > best[0]:
            best = (w, p["id"], hk.get("at", "chest"))
    return best


def rest_local(hand: str, pose: str, hh: dict) -> tuple:
    side = -1.0 if hand == "right" else 1.0
    if pose == "sit":
        return (0.28, side * 0.16, hh["hip"] + 0.09)                     # on the thighs
    tall = hh["top"]                                                     # arms hang, the palm beside the thigh
    return (0.02, side * 0.135 * tall, 0.445 * tall)


def hold_local(hand: str, hh: dict, at: str = "chest") -> tuple:
    side = -1.0 if hand == "right" else 1.0
    return {"waist": (0.28, side * 0.17, hh["waist"] + 0.05), "chest": (0.30, side * 0.14, hh["chest"]),
            "face": (0.22, side * 0.25, hh["eye"] - 0.06)}.get(at, (0.30, side * 0.14, hh["chest"]))


def hand_local(a: dict, hand: str, pose: str, hh: dict, w: float, at: str = "chest") -> tuple:
    """Hand position in the actor's frame (X forward, Y to the actor's left), resting → holding by w."""
    r, h_ = rest_local(hand, pose, hh), hold_local(hand, hh, at)
    return tuple(lerp(r[i], h_[i], w) for i in range(3))


def to_world(st: dict, local: tuple) -> tuple:
    fr = math.radians(st["facing"])
    x, y, z = local
    return (st["pos"][0] + x * math.cos(fr) - y * math.sin(fr), st["pos"][1] + x * math.sin(fr) + y * math.cos(fr), z)


def to_local(st: dict, world: tuple) -> tuple:
    fr = math.radians(-st["facing"])
    dx, dy = world[0] - st["pos"][0], world[1] - st["pos"][1]
    return (dx * math.cos(fr) - dy * math.sin(fr), dx * math.sin(fr) + dy * math.cos(fr), world[2])


def _smooth(f: float) -> float:
    f = min(1.0, max(0.0, f))
    return f * f * (3 - 2 * f)


def hand_state(spec: dict, a: dict, hand: str, t: float) -> tuple:
    """(local hand position, carried prop or None). A hold is a path, not a jump: the hand reaches to the
    prop, lifts it to the hold height, lowers it to where it is put down, and goes back to rest — so the
    prop never teleports between frames. Each move runs at HAND_MPS, never shorter than RAMP_S."""
    st = actor_at(spec, a, t)
    hh = actor_heights(a, st["pose"], st["seat"])
    rest = rest_local(hand, st["pose"], hh)
    dur = float(spec["duration"])
    span = lambda u, v: max(RAMP_S, math.dist(u, v) / HAND_MPS)
    for f0, f1, p, hk in _holds_for(spec, a["id"], hand):
        if not (f0 - 2.5 <= t <= f1 + 2.5):
            continue
        _, _, ph = dims(p)
        lift = ph / 2 - 0.03
        hold = hold_local(hand, hh, hk.get("at", "chest"))
        gx, gy, gz = prop_rest(spec, p, f0 - 1e-3)
        grab = to_local(st, (gx, gy, gz + ph / 2 - lift))
        px, py, pz = prop_rest(spec, p, f1 + 1e-3)
        put = to_local(st, (px, py, pz + ph / 2 - lift))
        r1, r2, r3, r4 = span(rest, grab), span(grab, hold), span(hold, put), span(put, rest)
        if not (f0 - r1 <= t <= f1 + r4):
            continue
        if f0 > 0 and t < f0:                                    # reach
            return tuple(lerp(rest[i], grab[i], _smooth((t - (f0 - r1)) / r1)) for i in range(3)), None
        if f0 > 0 and t < f0 + r2:                               # lift
            return tuple(lerp(grab[i], hold[i], _smooth((t - f0) / r2)) for i in range(3)), p
        if f1 < dur and t > f1:                                  # release
            return tuple(lerp(put[i], rest[i], _smooth((t - f1) / r4)) for i in range(3)), None
        if f1 < dur and t > f1 - r3:                             # lower
            return tuple(lerp(hold[i], put[i], _smooth((t - (f1 - r3)) / r3)) for i in range(3)), p
        return hold, p
    return rest, None


def hand_point(spec: dict, a: dict, hand: str, t: float) -> tuple:
    st = actor_at(spec, a, t)
    return to_world(st, hand_state(spec, a, hand, t)[0])


def prop_rest(spec: dict, p: dict, t: float) -> tuple:
    """Where a prop sits when nobody holds it: its `pos`/`on`, or the `put` of the last hold that ended."""
    base, on, z = p.get("pos", [0, 0]), p.get("on"), float(p.get("z", 0))
    for hk in sorted(p.get("held", []), key=lambda h: float(h["to"])):
        if float(hk["to"]) < t and hk.get("put"):
            base = hk["put"].get("pos", base); on = hk["put"].get("on", on)
    sets = {q["id"]: q for q in spec.get("set", [])}
    if isinstance(on, str) and on in sets:
        z = float(SURFACE.get(sets[on].get("kind"), dims(sets[on])[2])) + float(sets[on].get("z", 0))
    return float(base[0]), float(base[1]), z


def prop_at(spec: dict, p: dict, t: float) -> dict:
    _, _, h = dims(p)
    for hk in p.get("held", []):
        if float(hk["from"]) <= t <= float(hk["to"]):
            who, _, hand = str(hk["by"]).partition(".")
            act = next(a for a in spec["actors"] if a["id"] == who)
            hp = hand_point(spec, act, hand, t)
            return {"pos": (hp[0], hp[1], hp[2] + h / 2 - 0.03), "held_by": (who, hand)}
    x, y, z = prop_rest(spec, p, t)
    return {"pos": (x, y, z + h / 2), "held_by": None}


DETAILS = ("eyes", "mouth", "chest", "waist", "hands", "feet")   # parts of a person a framing can be on


def point_of(spec: dict, ident, t: float) -> tuple | None:
    """A look-at target: an actor's eyes, a prop's centre, or [x, y, z]."""
    if isinstance(ident, list):
        return tuple(float(v) for v in (ident + [1.0])[:3])
    if isinstance(ident, str) and "." in ident and ident.rsplit(".", 1)[1] in DETAILS:
        who, part = ident.rsplit(".", 1)
        kind, obj = _by_id(spec, who)
        if kind == "actor":                       # a part of a person: what a detail framing is on
            st = actor_at(spec, obj, t, resolve=False)
            hh = actor_heights(obj, st["pose"], st["seat"])
            z = {"eyes": hh["eye"], "mouth": hh["eye"] - 0.065 * float(obj.get("height", 1.7)), "chest": hh["chest"],
                 "waist": hh["waist"], "hands": hh["waist"] + 0.05, "feet": 0.12}[part]
            return (st["pos"][0], st["pos"][1], z)
    kind, obj = _by_id(spec, ident)
    if kind == "actor":
        st = actor_at(spec, obj, t, resolve=False)
        return (st["pos"][0], st["pos"][1], actor_heights(obj, st["pose"], st["seat"])["eye"])
    if kind == "prop":
        return prop_at(spec, obj, t)["pos"]
    if kind == "set":
        w, d, h = dims(obj)
        return (obj["pos"][0], obj["pos"][1], float(obj.get("z", 0)) + h / 2)
    if kind == "vehicle":
        vs = vehicle_at(spec, obj, t)
        return (vs["pos"][0], vs["pos"][1], 0.75)
    return None


def vfov_hfov(lens_mm: float, w: int, h: int) -> tuple:
    """Blender's AUTO sensor fit: the 36 mm sensor spans the LARGER frame side. So `lens` is the full-frame
    focal length along the long side: 26 mm here is a phone's 1× camera held in portrait."""
    big = 2 * math.degrees(math.atan(SENSOR_MM / (2 * lens_mm)))
    small = 2 * math.degrees(math.atan(SENSOR_MM / (2 * lens_mm) * min(w, h) / max(w, h)))
    return (big, small) if h >= w else (small, big)


def lens_for_long_fov(fov_deg: float) -> float:
    return SENSOR_MM / (2 * math.tan(math.radians(fov_deg) / 2))


# ── the camera: a shot plan, compiled to keys, solved in film terms, eased, aimed and breathed ────────────
def prepare(spec: dict) -> dict:
    """A working copy with the shot plan compiled to keys and cuts. Every entry point calls this; a spec
    already prepared comes back unchanged."""
    if spec.get("_prepared"):
        return spec
    s = copy.deepcopy(spec)
    s["_prepared"] = True
    if s.get("env"):
        s["set"] = ENV.expand(sys.modules[__name__], s) + list(s.get("set", []))
        if any(e.get("kind") in ENV.EXTERIORS for e in ENV._envs(s)):
            s.setdefault("sky", True)              # outdoors, the empty part of the frame is sky
    prop_ids = {id(p) for p in s.get("props", [])}
    for p in s.get("set", []) + s.get("props", []):
        if p.get("shape"):                       # precise geometry from the client's numbers (blocking_kit)
            try:
                p["_prims"] = KIT.shape_prims(p["shape"])
                if not p["_prims"]:
                    raise ValueError("no lathe, extrude or box in it")
                p["_extent"] = list(KIT.prims_extent(p["_prims"]))
                p.setdefault("size", p["_extent"])
                if id(p) in prop_ids:            # a prop is placed and held by its centre: lower the shape by half
                    p["_prims"] = KIT.shift_prims(p["_prims"], (0.0, 0.0, -p["_extent"][2] / 2))
            except (KeyError, ValueError, TypeError, IndexError) as e:
                p.pop("_prims", None)
                s.setdefault("_shape_errors", []).append(f"{p.get('id')}: shape is not readable ({e})")
    dur = float(s.get("duration", 5))
    for a in s.get("actors", []):
        if a.get("in"):                          # a passenger: the car carries them, so they need no walk of their own
            a["pose"] = "sit"
            a.setdefault("keys", [{"t": 0, "pos": [0, 0], "pose": "sit"}, {"t": dur, "pos": [0, 0], "pose": "sit"}])
    cam = s.setdefault("camera", {})
    if cam.get("shots"):
        keys, cuts, errs, reacts = compile_shots(s)
        cam["keys"], cam["cuts"] = keys, cuts
        s["_shot_errors"] = errs
        s["_reacts"] = reacts
    return s


SHOT_SHARED = ("on", "frame", "handheld", "ease", "place", "eyes_at", "occlusion_ok", "whip", "vehicle", "lens",
               "move", "height", "side", "size", "look_at", "pos")
SHOT_CARRY = ("frame", "handheld", "eyes_at", "occlusion_ok", "whip", "vehicle", "place", "fstop", "focus")


def _old_shot_keys(sh: dict, i: int, t0: float, end_t: float, last: bool) -> list:
    shared = {k: sh[k] for k in SHOT_SHARED if k in sh}
    shared["shot"] = i + 1
    out = [{**shared, **sh.get("from", {}), "t": t0}]
    for p in sh.get("path", []):
        out.append({**shared, **p})
    if last or end_t > t0 + 1e-6:
        out.append({**shared, **sh.get("to", sh.get("from", {})), "t": round(end_t, 6)})
    return out


def compile_shots(spec: dict):
    """camera.shots → (keys, cuts, errors, reacts). A shot is {t: [t0, t1], move, rig, …}. A named move
    (blocking_camera.LIBRARY: 70-odd, `blocking_camera.py --moves`) expands into its own keys with its
    timing, framing, lens, roll and focus; `start` (seconds into the shot, or an event such as
    "A.stands+0.2"), `dur` and `hold` place it in the shot. A shot with `path` keys, or whose move needs
    parameters it does not have, is read the plain way: `from`, `path`, `to`. Consecutive shots are cut
    together unless the later one says "cut": false (one continuous move through both). `react` lists
    events that jolt the operator: [{"at": "A.sits", "kind": "flinch"}]."""
    fps = float(spec.get("fps", 24))
    dur = float(spec["duration"])
    shots = sorted(spec["camera"]["shots"], key=lambda s: float(s["t"][0]))
    keys, cuts, errs, reacts = [], [], [], []
    prev_end = 0.0
    me = sys.modules[__name__]
    for i, sh in enumerate(shots):
        t0, t1 = float(sh["t"][0]), float(sh["t"][1])
        if abs(t0 - prev_end) > 1e-6:
            errs.append(f"shot {i + 1} starts at {t0:g} s, the previous one ends at {prev_end:g} s — shots tile "
                        f"the duration with no gap and no overlap")
        if t1 <= t0:
            errs.append(f"shot {i + 1} ends before it starts ({t0:g}–{t1:g} s)")
        prev_end = t1
        nxt = shots[i + 1] if i + 1 < len(shots) else None
        cut_next = nxt is not None and nxt.get("cut", True)
        end_t = t1 - 1.0 / fps if cut_next else t1
        mv = sh.get("move")
        raw, rig = None, sh.get("rig")
        if mv and mv not in CAM.LIBRARY:
            errs.append(f"shot {i + 1}: unknown move {mv!r} — `blocking_camera.py --moves` lists the named moves")
        if sh.get("rig") and sh["rig"] not in CAM.RIGS:
            errs.append(f"shot {i + 1}: unknown rig {sh['rig']!r} (one of {', '.join(CAM.RIGS)})")
        if mv in CAM.LIBRARY and "path" not in sh:
            try:
                raw, rig = CAM.expand_shot(me, spec, sh, t0, end_t)    # a shot cut on ends a frame before the cut
            except (ValueError, KeyError, TypeError) as e:
                if "from" in sh or "to" in sh:
                    raw = None                        # a plain from/to shot that only names its move
                    rig = sh.get("rig") or CAM.LIBRARY[mv][1]
                else:
                    errs.append(f"shot {i + 1} ({mv}): {e}")
                    continue
        if raw is None:
            raw = _old_shot_keys(sh, i, t0, end_t, nxt is None)
            rig = rig or (CAM.LIBRARY[mv][1] if mv in CAM.LIBRARY else CAM.DEFAULT_RIG)
        carry = {k: sh[k] for k in SHOT_CARRY if k in sh}
        out = []
        for k in raw:
            k2 = {**carry, **k}
            k2["shot"], k2["rig"] = i + 1, rig
            if mv:
                k2["move"] = mv
            k2["t"] = round(min(float(k2["t"]), end_t), 6)
            if out and abs(out[-1]["t"] - k2["t"]) < 1e-6:
                out[-1] = k2
            else:
                out.append(k2)
        if keys and abs(float(keys[-1]["t"]) - t0) < 1e-6:
            # a continuous join: the camera leaves the previous shot's last framing and eases into this
            # shot's plan over `blend` seconds (default 1 s), instead of jumping to where this move starts
            # (`blend` unset: long enough that the hand-over stays inside what the new rig carries comfortably)
            def joined(blend):
                tb = t0 + blend
                later = [k for k in out if float(k["t"]) >= tb - 1e-6]
                before = [k for k in out if float(k["t"]) < tb - 1e-6]
                if not later or float(later[0]["t"]) > tb + 1e-6:
                    lead = dict(before[-1] if before else out[0], t=round(tb, 6))
                    lead.pop("ease", None)
                    later = [lead] + later
                return later
            room = max(0.0, (t1 - t0) * 0.6)
            if "blend" in sh:
                blend = min(float(sh["blend"]), room)
            else:
                blend = min(1.0, room)
                comfy = max(2.5, 0.3 * float(CAM.rig_of(rig)["max_mps"]))
                for cand in (1.0, 1.5, 2.0, 2.5, 3.0):
                    if cand > room:
                        break
                    blend = cand
                    try:
                        a_ = solve_camera_key(spec, dict(keys[-1], t=t0))
                        b_ = solve_camera_key(spec, joined(cand)[0])
                        if math.dist(a_["pos"], b_["pos"]) / cand <= comfy:
                            break
                    except Exception:                 # noqa: BLE001 — the plan is not solvable yet: keep 1 s
                        blend = min(1.0, room)
                        break
            if blend <= 1e-6:
                keys.pop()
            else:
                keys[-1] = dict(keys[-1], ease="auto", rig=rig)   # the new rig takes the hand-over
                out = joined(blend)
                # v2.46: a wide hand-over whose eased path would pass through the subject swings wide instead
                # (blocking_camera.back_off: over 30° round the subject and inside its sphere → one waypoint)
                # Two framings orbiting the same subject already swing round it (camera_at eases the angle);
                # only a hand-over eased in position (a `pos` key, or another subject) can cut the chord.
                try:
                    a_ = solve_camera_key(spec, dict(keys[-1], t=t0))
                    b_ = solve_camera_key(spec, out[0])
                    subj = b_.get("subject") or a_.get("subject")
                    orbiting = bool(a_.get("orbit") and b_.get("orbit")
                                    and a_["orbit"]["subject"] == b_["orbit"]["subject"])
                    wp = None if orbiting else CAM.back_off(a_["pos"], b_["pos"], b_["look_at"], _subject_radius(spec, subj))
                except Exception:                     # noqa: BLE001 — an unsolvable plan is reported by check
                    wp = None
                if wp:
                    tm = round(t0 + (float(out[0]["t"]) - t0) / 2, 6)
                    base = {k_: v_ for k_, v_ in out[0].items()
                            if k_ not in ("on", "size", "side", "height", "ease", "orbit", "ref_facing", "pos", "look_at")}
                    out = [dict(base, t=tm, pos=wp, look_at=subj if isinstance(subj, str) else list(b_["look_at"]),
                                backoff=round(CAM.swing_deg(a_["pos"], b_["pos"], b_["look_at"]), 1))] + out
        keys += out
        for r in sh.get("react", []):
            try:
                reacts.append({"t": CAM.resolve_time(me, spec, r.get("at"), t0), "kind": r.get("kind", "flinch"),
                               "strength": float(r.get("strength", 1.0)), "shot": i + 1})
            except ValueError as e:
                errs.append(f"shot {i + 1} react: {e}")
            if reacts and reacts[-1].get("kind") not in CAM.REACT:
                errs.append(f"shot {i + 1} react: kind {reacts[-1]['kind']!r} is not one of {', '.join(CAM.REACT)}")
        if cut_next:
            cuts.append(t1)
    if shots and abs(prev_end - dur) > 1e-6:
        errs.append(f"the shots end at {prev_end:g} s and the clip runs {dur:g} s")
    return keys, cuts, errs, reacts


# a shot size on a thing (not a person): the frame's height as a multiple of the object's fitted extent
OBJECT_SIZE = {"ECU": 0.45, "CU": 1.35, "MCU": 1.9, "MS": 2.6, "MWS": 3.6, "WS": 5.5, "EWS": 14.0}


def object_size_for(spec: dict, ident: str, seen: float) -> str:
    """The shot size of a frame `seen` metres tall on a thing (OBJECT_SIZE read backwards)."""
    kind_, obj_ = _by_id(spec, ident)
    if kind_ == "vehicle":
        dd = DIMENSIONS.get(obj_.get("kind", "car"), (4.6, 1.85, 1.45))
    elif obj_ is not None:
        dd = dims(obj_)
    else:
        return "insert"
    w, h = spec["render"]["w"], spec["render"]["h"]
    fit = max(dd[2], max(dd[0], dd[1]) * (h / w if h > w else 1.0))
    return min(OBJECT_SIZE, key=lambda s_: abs(math.log(max(seen, 1e-3) / (fit * OBJECT_SIZE[s_]))))


def _subject_radius(spec: dict, ident) -> float:
    """The sphere a camera hand-over must stay out of (v2.46): 0.3 of a person's height round the point the camera
    frames (about 0.5 m: the shoulders and a margin), half an object's longest side. [assumed]"""
    if not isinstance(ident, str):
        return 0.5
    kind, obj = _by_id(spec, ident)
    try:
        if kind == "actor":
            return 0.3 * float(obj.get("height", 1.7))
        if kind == "vehicle":
            dd = DIMENSIONS.get(obj.get("kind", "car"), (4.6, 1.85, 1.45))
            return 0.5 * max(dd[0], dd[1])
        if kind is not None:
            dd = dims(obj)
            return max(0.2, 0.5 * max(dd[0], dd[1]))
    except (KeyError, TypeError, ValueError):
        pass
    return 0.5


def solve_camera_key(spec: dict, k: dict) -> dict:
    """A camera key in film terms → position, the thing it frames, and the numbers a prompt needs."""
    w, h = spec["render"]["w"], spec["render"]["h"]
    cam = spec.get("camera", {})
    lens = float(k.get("lens", cam.get("lens", 35)))
    vf, hf = vfov_hfov(lens, w, h)
    t = float(k["t"])
    orbit, look_id, look_pt, mode = None, None, None, "point"
    size = k.get("size")
    look_ids = None
    if "pos" in k:
        pos = tuple(float(v) for v in k["pos"])
        la = k.get("look_at", [0, 0, 1.0])
        if isinstance(la, list) and la and all(isinstance(x, str) for x in la):
            look_ids = list(la)                  # a group: frame the centre of everyone named
            pts = [point_of(spec, x, t) for x in la]
            pts = [p for p in pts if p] or [(0.0, 0.0, 1.0)]
            look = tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))
            subject, mode = None, "group"
            k = dict(k)
            k.setdefault("frame", list(la))
        else:
            look = point_of(spec, la, t) or (0.0, 0.0, 1.0)
            subject = k.get("on") or (la if isinstance(la, str) else None)
        if look_ids:
            pass
        elif isinstance(la, str):
            look_id = la
            mode = "eyes" if _by_id(spec, la)[0] == "actor" else "point"
        else:
            look_pt = tuple(float(v) for v in (la + [1.0])[:3])
    elif _by_id(spec, k.get("on"))[0] not in ("actor", None):
        # framing a thing: a product, a prop, a car, a piece of the set — sizes scale with the object itself
        kind_, obj_ = _by_id(spec, k["on"])
        subject = k["on"]
        c3 = point_of(spec, subject, t)
        if kind_ == "vehicle":
            dd = DIMENSIONS.get(obj_.get("kind", "car"), (4.6, 1.85, 1.45))
            front = vehicle_at(spec, obj_, t)["heading"]
        else:
            dd = dims(obj_)
            front = -90.0 + float(obj_.get("rot", 0)) if kind_ == "set" else -90.0
        size = size or "CU"
        fit = max(dd[2], max(dd[0], dd[1]) * (h / w if h > w else 1.0))
        E = fit * OBJECT_SIZE.get(size, 2.6)
        d = (E / 2) / math.tan(math.radians(vf) / 2)
        zc = c3[2]
        hgt = k.get("height", "level")
        named = {"level": zc, "eye": 1.55, "chest": 1.25, "waist": 1.0, "hip": 0.9, "knee": 0.5,
                 "low": max(0.08, zc - 0.25 * d), "high": zc + 0.5 * d, "overhead": zc + d}
        zcam = named.get(hgt, zc) if isinstance(hgt, str) else float(hgt)
        ang = front + float(k.get("side", 0))
        horiz = math.sqrt(max(d * d - (zcam - zc) ** 2, 0.04 * d * d))
        pos = (c3[0] + math.cos(math.radians(ang)) * horiz, c3[1] + math.sin(math.radians(ang)) * horiz, zcam)
        look = tuple(c3)
        orbit = {"subject": subject, "ang": ang, "horiz": horiz, "z": zcam, "zc": zc}
        look_id, mode = subject, "point"
    else:
        act = next((a for a in spec["actors"] if a["id"] == k.get("on")), None)
        if act is None:
            raise ValueError(f"camera key t={k.get('t')}: `on` {k.get('on')!r} names nothing in the spec")
        subject = k["on"]
        st = actor_at(spec, act, t)
        hh = actor_heights(act, st["pose"], st["seat"])
        size = size or "MS"
        E = ext_for(size, float(act.get("height", 1.70)))
        if size == "ECU":
            zc = hh["eye"]
        elif size in ("WS", "EWS"):
            zc = hh["top"] / 2 if st["pose"] != "sit" else hh["top"] * 0.6
        else:
            zc = hh["top"] + 0.06 * E - E / 2
        d = (E / 2) / math.tan(math.radians(vf) / 2)
        hgt = k.get("height", "eye")
        named = {"eye": hh["eye"], "level": hh["eye"], "chest": hh["chest"], "waist": hh["waist"], "hip": hh["hip"], "knee": hh["knee"],
                 "low": max(0.3, hh["waist"] - 0.2), "high": hh["top"] + 0.5, "overhead": hh["top"] + d}
        zcam = named[hgt] if isinstance(hgt, str) else float(hgt)
        side = float(k.get("side", 0))           # 0 = in front of the subject, +90 = the subject's left
        ang = float(k.get("ref_facing", st["facing"])) + side
        horiz = math.sqrt(max(d * d - (zcam - zc) ** 2, 0.25 * d * d))
        pos = (st["pos"][0] + math.cos(math.radians(ang)) * horiz, st["pos"][1] + math.sin(math.radians(ang)) * horiz, zcam)
        look = (st["pos"][0], st["pos"][1], zc)
        orbit = {"subject": subject, "ang": ang, "horiz": horiz, "z": zcam, "zc": zc}
        mode = "body" if size in ("WS", "EWS") else "eyes"
    dist = math.dist(pos, look)
    seen = 2 * dist * math.tan(math.radians(vf if h >= w else hf) / 2)
    out = {"t": t, "pos": [round(v, 3) for v in pos], "look_at": [round(v, 3) for v in look], "lens_mm": lens,
           "hfov_deg": round(hf, 1), "vfov_deg": round(vf, 1),
           "hfov_snap_deg": min(FOV_SNAP, key=lambda s: abs(s - hf)), "distance_m": round(dist, 2),
           "height_m": round(pos[2], 2), "visible_height_m": round(seen, 2), "subject": subject, "orbit": orbit,
           "look_id": look_id, "look_pt": look_pt, "look_ids": look_ids, "mode": mode, "shot": k.get("shot"),
           "handheld": k.get("handheld", cam.get("handheld", "none")), "place": k.get("place", "auto"),
           "eyes_at": k.get("eyes_at"), "ease": k.get("ease", cam.get("ease", "auto")),
           "whip": bool(k.get("whip")), "vehicle": bool(k.get("vehicle")),
           "occlusion_ok": bool(k.get("occlusion_ok")), "move": k.get("move"), "frame": list(k.get("frame", [])),
           "roll": float(k.get("roll", 0.0)), "focus": k.get("focus"), "fstop": float(k.get("fstop", 0.0)),
           "hold_size": bool(k.get("hold_size")), "attach": k.get("attach"), "rig": k.get("rig", CAM.DEFAULT_RIG),
           "detail": k.get("detail"), "beat": k.get("beat")}
    kind, obj = _by_id(spec, subject) if isinstance(subject, str) else (None, None)
    group = [a for a in spec["actors"] if a["id"] in k.get("frame", [])]
    if kind == "actor" or group:
        tall = float(obj.get("height", 1.70)) if kind == "actor" else max(float(a.get("height", 1.7)) for a in group)
        out["size_computed"] = size_for(seen, tall)
        if size:
            out["size_asked"] = size
    if group and not subject:
        out["group"] = [a["id"] for a in group]
    return out


def cam_keys_raw(spec: dict) -> list:
    return sorted(spec["camera"]["keys"], key=lambda k: float(k["t"]))


def camera_keys(spec: dict) -> list:
    return [solve_camera_key(spec, k) for k in cam_keys_raw(spec)]


_CAM: dict = {}


def reset_camera_cache() -> None:
    """Entry points call this first: solved keys are cached per spec object, and a spec edited in place
    between two calls would otherwise keep its old camera."""
    _CAM.clear()


def active_key(spec: dict, t: float) -> dict:
    """The raw camera key in force at t (the last one at or before it)."""
    ks = cam_keys_raw(spec)
    cur = ks[0]
    for k in ks:
        if float(k["t"]) <= t + 1e-9:
            cur = k
    return cur


def cuts_of(spec: dict) -> list:
    return sorted(float(c) for c in spec.get("camera", {}).get("cuts", []))


def _runs(ks: list, cuts: list) -> list:
    """Key indices grouped into runs: a run is one continuous camera; a cut starts the next run."""
    runs, cur = [], []
    for i, k in enumerate(ks):
        if cur and any(ks[cur[-1]]["t"] < c <= k["t"] + 1e-9 for c in cuts):
            runs.append(cur); cur = []
        cur.append(i)
    if cur:
        runs.append(cur)
    return runs


def _cam_state(spec: dict):
    key = id(spec)
    if key not in _CAM:
        _CAM.clear()
        _CAM[key] = None                         # guard: facing "camera" inside the solve must not recurse
        ks = camera_keys(spec)
        _CAM[key] = {"keys": ks, "runs": _runs(ks, cuts_of(spec))}
    return _CAM[key]


def _hermite(p0, p1, m0, m1, h, s):
    s2, s3 = s * s, s * s * s
    return (2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * h * m0 + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * h * m1


def _spline(times: list, vals: list, eases: list, i: int, t: float) -> float:
    """Value at t inside segment i of a run: cubic Hermite through every key at its own time, with
    Catmull-Rom tangents inside the run (the camera does not stop at an intermediate key), zero tangents at
    the run's ends (it eases in and out of the move), zero at a local extremum (no overshoot), and chord
    tangents where a key says "ease": "linear"."""
    n = len(times)

    def tangent(j):
        if eases[j] == "stop":                   # the camera stops on this key (a hold before or after it)
            return 0.0
        if eases[j] == "linear":
            a, b = max(j - 1, 0), min(j + 1, n - 1)
            return (vals[b] - vals[a]) / (times[b] - times[a]) if times[b] > times[a] else 0.0
        if j == 0 or j == n - 1:
            return 0.0
        if (vals[j] - vals[j - 1]) * (vals[j + 1] - vals[j]) <= 0:
            return 0.0
        return (vals[j + 1] - vals[j - 1]) / (times[j + 1] - times[j - 1])
    h = times[i + 1] - times[i]
    if h <= 0:
        return vals[i + 1]
    s = (t - times[i]) / h
    return _hermite(vals[i], vals[i + 1], tangent(i), tangent(i + 1), h, s)


def _noise(t: float, seed: int, lo: float, hi: float) -> float:
    """A deterministic slow drift in -1..1: three sines between lo and hi Hz with seeded phases."""
    tot = 0.0
    for j in range(3):
        f = lo + (hi - lo) * j / 2.0
        ph = ((seed * 9301 + j * 49297 + 233280) % 1000) / 1000.0 * 2 * math.pi
        tot += math.sin(2 * math.pi * f * t + ph)
    return tot / 3.0


def aim(cam_pos, target, sx: float, sy: float, hfov: float, vfov: float):
    """The look-at point that puts `target` at screen position (sx, sy), each -1..1 from edge to edge."""
    d = [target[i] - cam_pos[i] for i in range(3)]
    dist = math.sqrt(sum(v * v for v in d)) or 1.0
    az = math.atan2(d[1], d[0])
    el = math.atan2(d[2], math.hypot(d[0], d[1]))
    az_c = az + math.atan(sx * math.tan(math.radians(hfov) / 2))
    el_c = el - math.atan(sy * math.tan(math.radians(vfov) / 2))
    return [cam_pos[0] + dist * math.cos(el_c) * math.cos(az_c), cam_pos[1] + dist * math.cos(el_c) * math.sin(az_c),
            cam_pos[2] + dist * math.sin(el_c)]


def _target(spec: dict, k: dict, t: float):
    subj = k.get("subject")
    if k.get("mode") == "group" and k.get("look_ids"):
        pts = []
        for x in k["look_ids"]:
            kind, a = _by_id(spec, x)
            if kind == "actor":
                st = actor_at(spec, a, t, resolve=False)
                pts.append((st["pos"][0], st["pos"][1], actor_heights(a, st["pose"], st["seat"])["eye"]))
            else:
                p = point_of(spec, x, t)
                if p:
                    pts.append(tuple(p))
        if pts:
            return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))
    if k.get("mode") in ("eyes", "body") and isinstance(subj, str):
        kind, a = _by_id(spec, subj)
        if kind == "actor":
            st = actor_at(spec, a, t, resolve=False)
            hh = actor_heights(a, st["pose"], st["seat"])
            return (st["pos"][0], st["pos"][1], hh["eye"] if k["mode"] == "eyes" else hh["top"] / 2)
    if k.get("look_id"):
        return point_of(spec, k["look_id"], t)
    return tuple(k["look_pt"]) if k.get("look_pt") else tuple(k["look_at"])


def _placement(spec: dict, k: dict, t: float, pos, target) -> tuple:
    """(sx, sy) for the key's subject: eyes high in the frame, and look room ahead of a profile."""
    w, h = spec["render"]["w"], spec["render"]["h"]
    vertical = h > w
    pl = k.get("place", "auto")
    if isinstance(pl, list) and len(pl) == 2:
        return float(pl[0]), float(pl[1])
    sy = 0.0
    if k.get("mode") in ("eyes", "group"):
        eyes_at = float(k.get("eyes_at") or (0.36 if vertical else 0.33))   # fraction of the height from the top
        sy = 1.0 - 2.0 * eyes_at
    lead = 0.12 if vertical else 0.30
    if pl == "left":
        return -lead, sy
    if pl == "right":
        return lead, sy
    if pl == "centre" or k.get("mode") not in ("eyes", "body"):            # a group stays centred
        return 0.0, sy
    kind, a = _by_id(spec, k.get("subject")) if isinstance(k.get("subject"), str) else (None, None)
    if kind != "actor":
        return 0.0, sy
    st = actor_at(spec, a, t)
    fr = math.radians(st["facing"])
    fx, fy = target[0] - pos[0], target[1] - pos[1]
    n = math.hypot(fx, fy) or 1.0
    right = (fy / n, -fx / n)
    lateral = math.cos(fr) * right[0] + math.sin(fr) * right[1]          # +1 = facing frame right
    return -lead * max(-1.0, min(1.0, lateral * 1.4)), sy


def camera_ideal(spec: dict, t: float, ri: int | None = None) -> dict | None:
    """The camera the plan asks for at time t, before the rig's physics: position along the run's spline,
    aimed by composition at what the key frames. Two keys `on` the same actor orbit and follow that actor;
    `pos` keys travel through space; a `look_at` that names something keeps it framed as it moves; a cut
    holds the outgoing key and then shows the incoming one; an `attach` key rides an actor or a vehicle.
    `ri` pins the run (the operator samples a run past its own end)."""
    state = _cam_state(spec)
    if not state or not state["keys"]:
        return None
    ks, runs = state["keys"], state["runs"]
    if ri is None:
        ri = 0
        for j, r in enumerate(runs):
            if ks[r[0]]["t"] <= t + 1e-9:
                ri = j
    run = runs[ri]
    times = [ks[i]["t"] for i in run]
    if len(run) == 1 or t <= times[0]:
        seg, s = 0, 0.0
        a = b = ks[run[0]]
    elif t >= times[-1]:
        seg, s = len(run) - 2, 1.0
        a = b = ks[run[-1]]
    else:
        seg = max(j for j in range(len(run) - 1) if times[j] <= t)
        a, b = ks[run[seg]], ks[run[seg + 1]]
        s = (t - times[seg]) / (times[seg + 1] - times[seg]) if times[seg + 1] > times[seg] else 1.0
    tt = min(max(t, times[0]), times[-1])
    eases = [ks[i]["ease"] for i in run]
    lo_i, hi_i = max(seg - 1, 0), min(seg + 2, len(run) - 1)
    window = [ks[i] for i in run[lo_i:hi_i + 1]]
    orbit_ok = all(k.get("orbit") for k in window) and len({k["orbit"]["subject"] for k in window}) == 1
    lens = _spline(times, [ks[i]["lens_mm"] for i in run], eases, seg, tt) if len(run) > 1 else a["lens_mm"]
    if len(run) > 1 and orbit_ok and all(ks[i].get("orbit") and ks[i]["orbit"]["subject"] == a["orbit"]["subject"] for i in run):
        angs, prev = [], None
        for i in run:                                    # unwrap the orbit angle along the run
            x = ks[i]["orbit"]["ang"]
            if prev is not None:
                x = prev + ang_diff(prev, x)
            angs.append(x); prev = x
        ang = _spline(times, angs, eases, seg, tt)
        hz = _spline(times, [ks[i]["orbit"]["horiz"] for i in run], eases, seg, tt)
        z = _spline(times, [ks[i]["orbit"]["z"] for i in run], eases, seg, tt)
        act = next(x for x in spec["actors"] if x["id"] == a["orbit"]["subject"])
        c = actor_at(spec, act, t, resolve=False)["pos"]
        pos = [c[0] + math.cos(math.radians(ang)) * hz, c[1] + math.sin(math.radians(ang)) * hz, z]
    elif len(run) > 1:
        pos = [_spline(times, [ks[i]["pos"][d] for i in run], eases, seg, tt) for d in range(3)]
    else:
        pos = list(a["pos"])
    vf, hf = vfov_hfov(lens, spec["render"]["w"], spec["render"]["h"])
    ta, tb = _target(spec, a, t), _target(spec, b, t)
    g = _smooth(s) if a is not b else 0.0
    target = [lerp(ta[i], tb[i], g) for i in range(3)]
    pa, pb = _placement(spec, a, t, pos, ta), _placement(spec, b, t, pos, tb)
    sx, sy = lerp(pa[0], pb[0], g), lerp(pa[1], pb[1], g)
    look = aim(pos, target, sx, sy, hf, vf)
    roll = _spline(times, [ks[i]["roll"] for i in run], eases, seg, tt) if len(run) > 1 else a["roll"]
    if a.get("attach") and (a is b or b.get("attach")):
        pos, look, target = _attached(spec, a["attach"], t)
    fa, fb = a.get("focus"), b.get("focus")
    return {"pos": list(pos), "look_at": list(look), "target": list(target), "lens_mm": lens, "vfov_deg": vf, "hfov_deg": hf,
            "subject": a["subject"] if g < 0.5 else b["subject"], "roll_deg": roll, "key": a if g < 0.5 else b,
            "key_a": a, "key_b": b, "g": g, "run": ri, "shot": (a if g < 0.5 else b).get("shot"), "place": (sx, sy),
            "focus_a": fa, "focus_b": fb, "fstop": max(a.get("fstop", 0.0), b.get("fstop", 0.0))}


def _attached(spec: dict, at: dict, t: float):
    """(pos, look, target) for a camera bolted to an actor (snorricam, pov) or a vehicle (car rigs). The
    offset is in the carrier's frame: +x forward, +y left, +z up (from the eyes for an actor, from the
    ground for a vehicle)."""
    kind, obj = _by_id(spec, at["to"])
    ox, oy, oz = (float(v) for v in at.get("offset", [0, 0, 0]))
    if kind == "vehicle":
        vs = vehicle_at(spec, obj, t)
        base, hd = (vs["pos"][0], vs["pos"][1], 0.0), vs["heading"]
    else:
        st = actor_at(spec, obj, t)
        hh = actor_heights(obj, st["pose"], st["seat"])
        base, hd = (st["pos"][0], st["pos"][1], hh["eye"]), st["facing"]
    f = (math.cos(math.radians(hd)), math.sin(math.radians(hd)), 0.0)
    l = (-f[1], f[0], 0.0)
    pos = (base[0] + f[0] * ox + l[0] * oy, base[1] + f[1] * ox + l[1] * oy, base[2] + oz)
    look = at.get("look", "forward")
    if isinstance(look, list):
        target = tuple(float(v) for v in (look + [1.0])[:3])
    elif look == "back" and kind != "vehicle":
        target = (base[0], base[1], base[2] - 0.02)
    elif look == "gaze" and kind != "vehicle":
        lk = next((k.get("look") for k in sorted(obj["keys"], key=lambda k: float(k["t"])) if float(k["t"]) <= t + 1e-9
                   and k.get("look")), obj.get("look"))
        p = point_of(spec, lk, t) if isinstance(lk, (str, list)) and lk != "camera" else None
        target = p or (pos[0] + f[0] * 5, pos[1] + f[1] * 5, pos[2] - 0.15)
    elif look in ("driver", "passenger") and kind == "vehicle":
        occ = next((a for a in spec.get("actors", []) if a.get("in") == at["to"] and a.get("seat", "driver") == look), None)
        if occ:
            target = point_of(spec, occ["id"], t)
        else:
            sx, sy, sz = SEATS_CAR[look]
            target = (base[0] + f[0] * sx + l[0] * sy, base[1] + f[1] * sx + l[1] * sy, sz + 0.62)
    elif look == "back_low":
        target = (pos[0] - f[0] * 6, pos[1] - f[1] * 6, 0.3)
    elif isinstance(look, str) and look not in ("forward", "back", "gaze"):
        target = point_of(spec, look, t) or (pos[0] + f[0] * 20, pos[1] + f[1] * 20, pos[2])
    else:
        target = (pos[0] + f[0] * 20, pos[1] + f[1] * 20, pos[2] - 0.2)
    return pos, target, target


def _run_of(state, t: float) -> int:
    ri = 0
    for j, r in enumerate(state["runs"]):
        if state["keys"][r[0]]["t"] <= t + 1e-9:
            ri = j
    return ri


def _focus_dist(spec: dict, f, cam_pos, fwd, t: float):
    if f is None:
        return None
    if isinstance(f, (int, float)):
        return float(f)
    p = point_of(spec, f, t)
    if not p:
        return None
    return max(0.05, sum((p[i] - cam_pos[i]) * fwd[i] for i in range(3)))


def camera_at(spec: dict, t: float) -> dict | None:
    """The camera that renders at time t: the plan's ideal camera run through the rig's physics
    (blocking_camera.build_run: lag, overshoot, settle, banking, the flinch of a `react`), then the rig's
    own life (drift, steps, vibration), the plan's handheld profile on top, the lens (counter-zoomed on a
    dolly zoom so the subject keeps its size) and the focus distance. What `check` measures is this."""
    state = _cam_state(spec)
    if not state or not state["keys"]:
        return None
    ks, runs = state["keys"], state["runs"]
    if _BUSY[0]:
        # asked from inside the camera's own solve (an actor facing "camera", a head looking at the lens):
        # the key in force is close enough, and it cannot recurse
        k = max((x for x in ks if x["t"] <= t + 1e-9), key=lambda x: x["t"], default=ks[0])
        return {"pos": list(k["pos"]), "look_at": list(k["look_at"]), "target": list(k["look_at"]), "lens_mm": k["lens_mm"],
                "vfov_deg": k["vfov_deg"], "hfov_deg": k["hfov_deg"], "subject": k["subject"], "roll_deg": k["roll"],
                "key": k, "run": 0, "shot": k.get("shot"), "place": (0.0, 0.0), "focus_m": None, "fstop": 0.0,
                "rig": k.get("rig"), "speed": 0.0, "ideal_pos": list(k["pos"]), "base_pos": list(k["pos"])}
    _BUSY[0] += 1
    try:
        return _camera_at(spec, t, state)
    finally:
        _BUSY[0] -= 1


_BUSY = [0]


def _camera_at(spec: dict, t: float, state: dict) -> dict:
    ks, runs = state["keys"], state["runs"]
    ri = _run_of(state, t)
    run = runs[ri]
    t0r = ks[run[0]]["t"]
    t1r = ks[runs[ri + 1][0]]["t"] - 1e-6 if ri + 1 < len(runs) else float(spec["duration"])
    tables = state.setdefault("tables", {})
    if ri not in tables:
        rig = ks[run[0]].get("rig", CAM.DEFAULT_RIG)
        reacts = [r for r in spec.get("_reacts", []) if t0r - 1e-9 <= r["t"] <= t1r]
        tables[ri] = CAM.build_run(sys.modules[__name__], spec, t0r, max(t1r, t0r + 1e-3), rig, reacts,
                                   lambda tt: camera_ideal(spec, tt, ri),
                                   t_plan=ks[run[-1]]["t"] if ri + 1 < len(runs) else None)
    smp = CAM.sample_run(tables[ri], min(max(t, t0r), max(t1r, t0r)), seed=17 * (ri + 1))
    c = camera_ideal(spec, t, ri)
    pos, look, roll = smp["pos"], smp["look_at"], smp["roll_deg"]
    a, b, g = c["key_a"], c["key_b"], c["g"]
    # the plan's handheld profile (HANDHELD), on top of the rig
    amp_a, amp_b = HANDHELD.get(a["handheld"], HANDHELD["none"]), HANDHELD.get(b["handheld"], HANDHELD["none"])
    ap, ar = lerp(amp_a[0], amp_b[0], g), lerp(amp_a[1], amp_b[1], g)
    if ap > 0 or ar > 0:
        flo, fhi = amp_a[2], amp_a[3]
        seed = 31 * (ri + 1)
        pos = [pos[d] + ap * _noise(t, seed + d, flo, fhi) for d in range(3)]
        if a["handheld"] == "walking":
            pos[2] += 0.012 * math.sin(2 * math.pi * 1.8 * t)
        d = [look[i] - pos[i] for i in range(3)]
        dist = math.sqrt(sum(v * v for v in d)) or 1.0
        az = math.atan2(d[1], d[0]) + math.radians(ar * _noise(t, seed + 5, flo, fhi))
        el = math.atan2(d[2], math.hypot(d[0], d[1])) + math.radians(ar * 0.7 * _noise(t, seed + 6, flo, fhi))
        look = [pos[0] + dist * math.cos(el) * math.cos(az), pos[1] + dist * math.cos(el) * math.sin(az),
                pos[2] + dist * math.sin(el)]
        roll += ar * 0.6 * _noise(t, seed + 7, flo, fhi)
    lens = c["lens_mm"]
    if a.get("hold_size") and b.get("hold_size"):
        # dolly zoom: the lens counter-zooms so the subject keeps the size it had where the zoom began
        j0 = next(i for i in run if ks[i].get("hold_size"))
        k0 = ks[j0]
        d0 = math.dist(k0["pos"], k0["look_at"])
        lens = k0["lens_mm"] * math.dist(pos, c["target"]) / max(d0, 1e-3)
    vf, hf = vfov_hfov(lens, spec["render"]["w"], spec["render"]["h"])
    fwd = [look[i] - pos[i] for i in range(3)]
    n_ = math.sqrt(sum(v * v for v in fwd)) or 1.0
    fwd = [v / n_ for v in fwd]
    fa, fb = _focus_dist(spec, c["focus_a"], pos, fwd, t), _focus_dist(spec, c["focus_b"], pos, fwd, t)
    focus = None
    if fa and fb:
        focus = math.exp(lerp(math.log(fa), math.log(fb), _smooth(g)))
    elif fa or fb:
        focus = fa or fb
    return {"pos": pos, "look_at": look, "target": c["target"], "lens_mm": lens, "vfov_deg": vf, "hfov_deg": hf,
            "subject": c["subject"], "roll_deg": roll, "key": c["key"], "run": ri, "shot": c["shot"],
            "place": c["place"], "focus_m": focus, "fstop": c["fstop"],
            "in_detail": bool((c.get("key_a") or {}).get("detail") or (c.get("key_b") or {}).get("detail")),
            "in_whip": bool((c.get("key_a") or {}).get("whip") or (c.get("key_b") or {}).get("whip")),
            "speed": smp["speed"], "ideal_pos": c["pos"], "base_pos": smp["base_pos"], "rig": smp["rig"] or tables[ri]["rig"]}


def project(cam: dict, p: tuple, w: int, h: int) -> tuple:
    """(sx, sy, depth): sx and sy run -1..1 from frame edge to frame edge; depth in metres along the lens."""
    fx, fy, fz = (cam["look_at"][i] - cam["pos"][i] for i in range(3))
    n = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    fwd = (fx / n, fy / n, fz / n)
    v = [p[i] - cam["pos"][i] for i in range(3)]
    depth = sum(v[i] * fwd[i] for i in range(3))
    if depth <= 0.05:
        return (0.0, 0.0, depth)
    right = (fwd[1], -fwd[0], 0.0)
    rn = math.hypot(right[0], right[1]) or 1.0
    right = (right[0] / rn, right[1] / rn, 0.0)
    up = (right[1] * fwd[2], -right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0])
    x = sum(v[i] * right[i] for i in range(3)) / depth
    y = sum(v[i] * up[i] for i in range(3)) / depth
    return (x / math.tan(math.radians(cam["hfov_deg"]) / 2), y / math.tan(math.radians(cam["vfov_deg"]) / 2), depth)


def in_frame(cam: dict, p: tuple, w: int, h: int, safe: float = 1.0) -> bool:
    sx, sy, d = project(cam, p, w, h)
    return d > 0.05 and abs(sx) <= safe and abs(sy) <= safe


def _ray_box(o, d, centre, half, rot_deg) -> float | None:
    """Distance along the ray to an oriented box (rotated about Z), or None."""
    r = math.radians(-rot_deg)
    ox, oy = o[0] - centre[0], o[1] - centre[1]
    lo = (ox * math.cos(r) - oy * math.sin(r), ox * math.sin(r) + oy * math.cos(r), o[2] - centre[2])
    ld = (d[0] * math.cos(r) - d[1] * math.sin(r), d[0] * math.sin(r) + d[1] * math.cos(r), d[2])
    t0, t1 = -1e9, 1e9
    for i in range(3):
        if abs(ld[i]) < 1e-9:
            if abs(lo[i]) > half[i]:
                return None
            continue
        a, b = (-half[i] - lo[i]) / ld[i], (half[i] - lo[i]) / ld[i]
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    return t0 if t1 >= max(t0, 0) and t1 > 0 else None


def _boxes(spec: dict, t: float, exclude=()) -> list:
    """(centre, half-size, rot, id) for every solid and every actor's body at time t."""
    out = []
    for p in solids(spec):
        w, d, h = dims(p)
        out.append(((p["pos"][0], p["pos"][1], float(p.get("z", 0)) + h / 2), (w / 2, d / 2, h / 2),
                    float(p.get("rot", 0)), p.get("id")))
    for a in spec["actors"]:
        if a["id"] in exclude:
            continue
        st = actor_at(spec, a, t, resolve=False)
        top = actor_heights(a, st["pose"], st["seat"])["top"]
        out.append(((st["pos"][0], st["pos"][1], top / 2), (0.18, 0.18, top / 2), 0.0, a["id"]))
    return out


def occluded_by(spec: dict, t: float, cam_pos, target, exclude=()) -> str | None:
    d = [target[i] - cam_pos[i] for i in range(3)]
    dist = math.sqrt(sum(v * v for v in d)) or 1.0
    u = [v / dist for v in d]
    for c, half, rot, ident in _boxes(spec, t, exclude):
        x = _ray_box(cam_pos, u, c, half, rot)
        if x is not None and 0.05 < x < dist - 0.15:
            return ident
    return None


def void_fraction(spec: dict, t: float, nx: int = 9, ny: int = 16) -> float:
    """The share of the frame whose rays meet no set piece, wall, actor or floor within 40 m."""
    cam = camera_at(spec, t)
    fwd = [cam["look_at"][i] - cam["pos"][i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in fwd)) or 1.0
    fwd = [v / n for v in fwd]
    right = (fwd[1], -fwd[0], 0.0)
    rn = math.hypot(right[0], right[1]) or 1.0
    right = (right[0] / rn, right[1] / rn, 0.0)
    up = (right[1] * fwd[2], -right[0] * fwd[2], right[0] * fwd[1] - right[1] * fwd[0])
    th, tv = math.tan(math.radians(cam["hfov_deg"]) / 2), math.tan(math.radians(cam["vfov_deg"]) / 2)
    boxes = [(c, hf_, r) for c, hf_, r, _ in _boxes(spec, t)]
    for p in all_pieces(spec):                         # doors and windows close their gaps for this test
        if not p.get("solid", True) or p.get("kind") in WALKABLE or p.get("walkable"):   # floors, roads, a cyc are seen too
            w, d, h = dims(p)
            boxes.append(((p["pos"][0], p["pos"][1], float(p.get("z", 0)) + h / 2), (w / 2, d / 2, h / 2), float(p.get("rot", 0))))
    fl = spec.get("floor", {"size": [12, 12]})["size"]
    void = 0
    for i in range(nx):
        for j in range(ny):
            sx, sy = (i + 0.5) / nx * 2 - 1, (j + 0.5) / ny * 2 - 1
            d = [fwd[k] + right[k] * sx * th + up[k] * sy * tv for k in range(3)]
            hit = any((x := _ray_box(cam["pos"], d, c, hf_, r)) is not None and x < 40 for c, hf_, r in boxes)
            if not hit and d[2] < -1e-6:
                tf = -cam["pos"][2] / d[2]
                fx, fy = cam["pos"][0] + d[0] * tf, cam["pos"][1] + d[1] * tf
                hit = abs(fx) <= fl[0] / 2 and abs(fy) <= fl[1] / 2
            void += 0 if hit else 1
    return void / (nx * ny)


def camera_motion(spec: dict, t0: float, t1: float, cam0=None, cam1=None) -> list:
    """The camera's own move between t0 and t1, in words: a subject walking past a locked-off camera is not
    a pull-back, and an arc round the subject is not a push."""
    c0, c1 = cam0 or camera_at(spec, t0), cam1 or camera_at(spec, t1)
    words = []
    sp0, sp1 = c0["target"], c1["target"]
    moved = math.dist(c0["pos"], c1["pos"]) > 0.15
    if moved:
        r0, r1 = math.dist(c0["pos"], sp0), math.dist(c1["pos"], sp1)
        if r1 < r0 * 0.85:
            words.append("pushes in")
        elif r1 > r0 * 1.15:
            words.append("pulls back")
        a0 = math.degrees(math.atan2(c0["pos"][1] - sp0[1], c0["pos"][0] - sp0[0]))
        a1 = math.degrees(math.atan2(c1["pos"][1] - sp1[1], c1["pos"][0] - sp1[0]))
        da = ang_diff(a0, a1)
        if abs(da) > 10:
            words.append(f"arcs {abs(da):.0f}° to camera-{'right' if da > 0 else 'left'}")
        subj = c0.get("subject")
        ids = c0["key"].get("look_ids") or []
        who = (_label(spec, subj) if isinstance(subj, str) and _by_id(spec, subj)[0] == "actor" else
               " and ".join(_label(spec, x) for x in ids if _by_id(spec, x)[0] == "actor") or None)
        att = (c0.get("key") or {}).get("attach")
        if att:                                    # rigged to what carries it: it rides, it does not chase
            words = [w_ for w_ in words if not w_.startswith(("pushes", "pulls", "arcs"))]
            words.append(f"rides with {_label(spec, att.get('to'))}")
        elif who and math.dist(sp0[:2], sp1[:2]) > 0.3:
            mv_s = (sp1[0] - sp0[0], sp1[1] - sp0[1])
            n_ = math.hypot(*mv_s) or 1.0
            rel = (c1["pos"][0] - sp1[0], c1["pos"][1] - sp1[1])
            ahead = (rel[0] * mv_s[0] + rel[1] * mv_s[1]) / n_                              # where it settles
            beside = abs(rel[0] * mv_s[1] - rel[1] * mv_s[0]) / n_
            if beside > 2 * abs(ahead):
                words.append(f"tracks alongside {who}")
            else:
                words.append(f"leads {who}, moving ahead of them" if ahead > 0 else f"follows {who}")
        elif not words and abs(c1["pos"][2] - c0["pos"][2]) < 0.15:
            words.append("trucks")
    dz = c1["pos"][2] - c0["pos"][2]
    # on a tight frame a small rise is a big move: 8 cm on an 85 mm ECU travels half the picture
    vis = 2 * math.dist(c0["pos"], sp0) * math.tan(math.radians(c0["vfov_deg"]) / 2)
    if abs(dz) > min(0.15, 0.3 * vis):
        words.append(("rises" if dz > 0 else "lowers") + ("" if moved or abs(dz) > 0.15 else
                     f" {abs(dz) * 100:.0f} cm ({abs(dz) / max(vis, 1e-6):.0%} of the frame)"))
    if not moved:
        y0 = math.degrees(math.atan2(c0["look_at"][1] - c0["pos"][1], c0["look_at"][0] - c0["pos"][0]))
        y1 = math.degrees(math.atan2(c1["look_at"][1] - c1["pos"][1], c1["look_at"][0] - c1["pos"][0]))
        if abs(ang_diff(y0, y1)) > 8:
            words.append(f"pans {'left' if ang_diff(y0, y1) > 0 else 'right'} {abs(ang_diff(y0, y1)):.0f}°")
        p0 = _tilt(c0); p1 = _tilt(c1)
        if abs(p1 - p0) > 6:
            words.append(f"tilts {'up' if p1 > p0 else 'down'} {abs(p1 - p0):.0f}°")
    if abs(c1["lens_mm"] - c0["lens_mm"]) > 3:
        words.append(f"zooms {c0['lens_mm']:.0f}→{c1['lens_mm']:.0f} mm")
    return words


def _tilt(c) -> float:
    return math.degrees(math.atan2(c["look_at"][2] - c["pos"][2], math.dist(c["look_at"][:2], c["pos"][:2])))


# ── checks ───────────────────────────────────────────────────────────────────────────────────────────────
def model_range(model: str, res: str = "1080p"):
    """(min_s, max_s) from the rates file; None when the model has no row; "unreadable" when the file is."""
    try:
        rt = json.load(open(RATES, encoding="utf-8"))["rate_table"]
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return "unreadable"
    try:
        row = rt[model].get(res) or next(iter(rt[model].values()))
        return float(row["min_s"]), float(row["max_s"])
    except (KeyError, ValueError, TypeError, StopIteration, AttributeError):
        return None


def colours_used(spec: dict) -> dict:
    used = {}
    for p in spec.get("set", []) + spec.get("props", []):
        used.setdefault(p.get("color", NEUTRAL), []).append(p.get("id"))
        if p.get("label_toward"):
            used.setdefault("white", []).append(f"{p.get('id')} label")
    for a in spec.get("actors", []):
        used.setdefault(a.get("color"), []).append(a.get("id"))
    for v in spec.get("vehicles", []):
        used.setdefault(v.get("color", NEUTRAL), []).append(v.get("id"))
    return used


def _size_of_cam(spec: dict, c: dict) -> str | None:
    subj = c.get("subject")
    kind, a = _by_id(spec, subj) if isinstance(subj, str) else (None, None)
    if kind != "actor":
        return None
    w, h = spec["render"]["w"], spec["render"]["h"]
    vis = 2 * math.dist(c["pos"], c["target"]) * math.tan(math.radians(c["vfov_deg"] if h >= w else c["hfov_deg"]) / 2)
    return size_for(vis, float(a.get("height", 1.7)))


def check(spec: dict) -> tuple[list, list]:
    spec = prepare(spec)
    reset_camera_cache()
    F, W = [], []
    for fld in ("shot", "duration", "fps", "render", "actors", "camera", "legend"):
        if fld not in spec:
            F.append(f"missing `{fld}`")
    if F:
        return F, W
    F += list(spec.get("_shot_errors", [])) + list(spec.get("_shape_errors", []))
    lt = (spec.get("look") or {}).get("time")
    if lt is not None and lt not in LOOK.TIMES:
        F.append(f"look time {lt!r} is not one of {', '.join(LOOK.TIMES)}")
    dur = float(spec["duration"])
    fps = float(spec["fps"])
    for p in spec.get("set", []) + spec.get("props", []):
        kind = p.get("kind", "box")
        if kind == "room":
            for wl in p.get("walls", ["back", "left", "right"]):
                if wl not in KIT.WALLS:
                    F.append(f"room {p.get('id')}: wall {wl!r} is not one of {', '.join(KIT.WALLS)}")
            for o in p.get("openings", []):
                if o.get("wall") not in KIT.WALLS or o.get("kind", "door") not in ("door", "window"):
                    F.append(f"room {p.get('id')}: opening {o} needs a wall ({', '.join(KIT.WALLS)}) and a kind "
                             f"(door or window)")
        elif kind == "plan":
            pts = p.get("points", [])
            if len(pts) < 2 or any(len(q) != 2 for q in pts):
                F.append(f"plan {p.get('id')}: `points` needs at least two [x, y] corners")
            nseg = len(pts) if p.get("closed", True) else len(pts) - 1
            for o in p.get("openings", []):
                if not 0 <= int(o.get("segment", -1)) < max(nseg, 0) or o.get("kind", "door") not in ("door", "window"):
                    F.append(f"plan {p.get('id')}: opening {o} needs a segment 0–{nseg - 1} and a kind (door or window)")
                    continue
                a_, b_ = pts[int(o["segment"])], pts[(int(o["segment"]) + 1) % len(pts)]
                L_ = math.dist(a_, b_)
                c_, w_ = float(o.get("at", -1)), float(o.get("w", 0.9))
                if c_ - w_ / 2 < -1e-6 or c_ + w_ / 2 > L_ + 1e-6:
                    F.append(f"plan {p.get('id')}: opening at {c_:g} m, {w_:g} m wide, does not fit segment "
                             f"{o['segment']} ({L_:.2f} m long)")
        elif p.get("model"):
            md = p["model"]
            f_ = os.path.expanduser(str(md.get("file", "")))
            if os.path.splitext(f_)[1].lower() not in KIT.MODEL_EXTS:
                F.append(f"{p.get('id')}: model file {md.get('file')!r} is not one of {', '.join(KIT.MODEL_EXTS)}")
            elif not os.path.isfile(f_):
                F.append(f"{p.get('id')}: model file {md.get('file')!r} is not on this machine — download it first "
                         f"(Poly Haven / BlendSwap downloads need the owner's OK per job and stay out of git)")
            if len(p.get("size", [])) != 3:
                F.append(f"{p.get('id')}: a model needs `size` [w, d, h] in metres — it is fitted to that box, so the "
                         f"real object's dimensions decide the scale, not the file's units")
            lic = md.get("licence")
            if lic in KIT.LICENCES_CREDIT:
                W.append(f"{p.get('id')}: {lic} — the delivery credits {md.get('author') or 'the author'} "
                         f"({md.get('source') or 'source'}); keep that line in the hand-off")
            elif lic not in KIT.LICENCES_OK:
                F.append(f"{p.get('id')}: model licence {lic!r} is not cleared for client work (CC0, client, own; "
                         f"CC-BY/CC-BY-SA with credit)")
            if lic not in ("client", "own") and not md.get("source"):
                F.append(f"{p.get('id')}: a downloaded model records its `source` URL (and `author`)")
        elif kind not in DIMENSIONS and not p.get("size"):
            F.append(f"{p.get('id')}: unknown kind {kind!r} with no `size` — add it to DIMENSIONS or give a size")
        if p.get("_extent") and p.get("size") and any(abs(float(a_) - float(b_)) > max(0.02, 0.02 * float(b_))
                                                     for a_, b_ in zip(p["size"], p["_extent"])):
            W.append(f"{p.get('id')}: `size` {p['size']} differs from what its shape measures {p['_extent']} — the "
                     f"shape is drawn as written; the checks use `size`")
        c = p.get("color", NEUTRAL)
        if c not in COLORS:
            F.append(f"{p.get('id')}: unknown colour {c!r} ({', '.join(COLORS)})")
    for v in spec.get("vehicles", []):
        if v.get("kind", "car") not in VEHICLE_KINDS:
            F.append(f"vehicle {v.get('id')}: kind {v.get('kind')!r} is not one of {', '.join(VEHICLE_KINDS)}")
        if v.get("color", NEUTRAL) not in COLORS:
            F.append(f"vehicle {v.get('id')}: unknown colour {v.get('color')!r}")
        for k in v.get("keys", []):
            if not 0 <= float(k.get("t", -1)) <= dur or len(k.get("pos", [])) != 2:
                F.append(f"vehicle {v.get('id')}: key {k} needs t inside 0–{dur:g} s and pos [x, y]")
    ids, all_ids = set(), set()
    for x in spec.get("set", []) + spec.get("props", []) + spec["actors"] + spec.get("vehicles", []):
        if x.get("id") in all_ids:
            F.append(f"id {x.get('id')!r} used twice")
        all_ids.add(x.get("id"))
    all_ids |= {p.get("id") for p in all_pieces(spec)}
    actor_ids = {x.get("id") for x in spec["actors"]}
    for a in spec["actors"]:
        ids.add(a.get("id"))
        if a.get("color") not in COLORS:
            F.append(f"actor {a.get('id')}: colour {a.get('color')!r} is not one of {', '.join(COLORS)}")
        if a.get("build", "average") not in RIG.BUILD:
            F.append(f"actor {a.get('id')}: build {a.get('build')!r} is not one of {', '.join(RIG.BUILD)}")
        if a.get("in"):
            if _by_id(spec, a["in"])[0] != "vehicle":
                F.append(f"actor {a.get('id')}: `in` {a['in']!r} names no vehicle")
            if a.get("seat", "driver") not in SEATS_CAR:
                F.append(f"actor {a.get('id')}: seat {a.get('seat')!r} is not one of {', '.join(SEATS_CAR)}")
        if a.get("body", "mannequin") not in BODIES:
            F.append(f"actor {a.get('id')}: body {a.get('body')!r} is not one of {', '.join(BODIES)}")
        if not a.get("keys"):
            F.append(f"actor {a.get('id')}: no keys")
        for k in a.get("keys", []):
            if not 0 <= float(k.get("t", -1)) <= dur:
                F.append(f"actor {a['id']}: key at t={k.get('t')} is outside 0–{dur:g} s")
            if k.get("pose", a.get("pose", "stand")) not in POSES:
                F.append(f"actor {a['id']}: pose {k.get('pose')!r} is not one of {', '.join(POSES)}")
            fc = k.get("facing", -90)
            if isinstance(fc, str) and fc != "camera" and fc not in actor_ids:
                F.append(f"actor {a['id']}: facing {fc!r} names no actor (degrees, an actor id, \"camera\" or [x, y])")
            lk = k.get("look", a.get("look"))
            if isinstance(lk, str) and lk != "camera" and lk not in all_ids:
                F.append(f"actor {a['id']}: look {lk!r} names nothing in the spec")
    times = []
    for k in spec["camera"].get("keys", []):
        tk = float(k.get("t", -1))
        times.append(tk)
        if not 0 <= tk <= dur:
            F.append(f"camera key at t={k.get('t')} is outside 0–{dur:g} s")
        if "pos" not in k and k.get("on") not in all_ids:
            F.append(f"camera key t={k.get('t')}: `on` must name an actor, prop, vehicle or set piece (or give "
                     f"`pos` + `look_at`)")
        if "pos" in k and isinstance(k.get("look_at"), str) and k["look_at"] not in all_ids:
            F.append(f"camera key t={k.get('t')}: look_at {k['look_at']!r} names nothing in the spec")
        if "pos" in k and isinstance(k.get("look_at"), list) and any(isinstance(x, str) for x in k["look_at"]):
            if not all(isinstance(x, str) for x in k["look_at"]):
                F.append(f"camera key t={k.get('t')}: look_at mixes names and numbers — give a point [x, y, z] "
                         f"or a list of ids to frame as a group")
            else:
                for x in k["look_at"]:
                    if x not in all_ids:
                        F.append(f"camera key t={k.get('t')}: look_at {x!r} names nothing in the spec")
        for fid in k.get("frame", []):
            if fid not in all_ids:
                F.append(f"camera key t={k.get('t')}: frame lists {fid!r}, which names nothing in the spec")
        if "size" in k and k["size"] not in SIZES:
            F.append(f"camera key t={k.get('t')}: size {k['size']!r} is not one of {', '.join(SIZES)}")
        hg = k.get("height", "eye")
        if isinstance(hg, str) and hg not in CAM_HEIGHTS:
            F.append(f"camera key t={k.get('t')}: height {hg!r} is not one of {', '.join(CAM_HEIGHTS)} or metres")
        hh_ = k.get("handheld", spec["camera"].get("handheld", "none"))
        if hh_ not in HANDHELD:
            F.append(f"camera key t={k.get('t')}: handheld {hh_!r} is not one of {', '.join(HANDHELD)}")
        if k.get("move") and k["move"] not in CAM.LIBRARY:
            F.append(f"camera key t={k.get('t')}: move {k['move']!r} is not a named move (blocking_camera.py --moves)")
        if k.get("rig") and k["rig"] not in CAM.RIGS:
            F.append(f"camera key t={k.get('t')}: rig {k['rig']!r} is not one of {', '.join(CAM.RIGS)}")
        pl = k.get("place", "auto")
        if not (pl in ("auto", "centre", "left", "right") or (isinstance(pl, list) and len(pl) == 2)):
            F.append(f"camera key t={k.get('t')}: place {pl!r} is auto, centre, left, right or [sx, sy]")
    if len(set(round(x, 4) for x in times)) < len(times):
        F.append("two camera keys at the same time — use a cut (`cuts`) and put the incoming key at the cut time")
    if not spec["camera"].get("keys"):
        F.append("camera: no keys (give `keys`, or `shots`)")
    for c in cuts_of(spec):
        if not 0 < c < dur:
            F.append(f"cut at {c:g} s is outside the shot")
        elif not any(abs(c - x) <= 0.5 / fps for x in times):
            F.append(f"cut at {c:g} s has no camera key at that time — the incoming shot starts at the cut, "
                     f"so its key goes there")
    legend = spec["legend"]
    for c, who in colours_used(spec).items():
        if c != NEUTRAL and c not in legend:
            F.append(f"colour {c!r} ({', '.join(map(str, who))}) is not in the legend — the video model is told "
                     f"what each colour means, so every colour needs a line")
    for c in legend:
        if c not in colours_used(spec):
            F.append(f"legend colour {c!r} is used by nothing — a legend line for an absent colour invites the model "
                     f"to add one")
    holds = {}
    set_ids = {q["id"] for q in spec.get("set", [])}
    for p in spec.get("props", []):
        on = p.get("on")
        if isinstance(on, str) and on not in set_ids:
            F.append(f"prop {p['id']}: `on` names {on!r}, which is not a set piece")
        for hk in p.get("held", []):
            who, _, hand = str(hk.get("by", "")).partition(".")
            if who not in ids or hand not in ("left", "right"):
                F.append(f"prop {p['id']}: held by {hk.get('by')!r} — write <actor>.left or <actor>.right")
                continue
            for tt in (float(hk["from"]), float(hk["to"])):
                if not 0 <= tt <= dur:
                    F.append(f"prop {p['id']}: held from/to {tt:g} s is outside the duration")
            if hk.get("at", "chest") not in HOLD_AT:
                F.append(f"prop {p['id']}: held at {hk.get('at')!r} — one of {', '.join(HOLD_AT)}")
            holds.setdefault((who, hand), []).append((float(hk["from"]), float(hk["to"]), p["id"]))
    if F:
        return F, W
    model = spec.get("model")
    if model:
        rng = model_range(model)
        if rng == "unreadable":
            W.append(f"the rates file is not readable ({RATES}) — the duration was not checked against {model}")
        elif rng is None:
            F.append(f"model {model!r} has no rate row (not on the roster) — assets/higgsfield-rates.json")
        elif not rng[0] <= dur <= rng[1]:
            F.append(f"duration {dur:g} s is outside {model}'s measured range {rng[0]:g}–{rng[1]:g} s")
    # reach at pick-up
    for p in spec.get("props", []):
        for hk in p.get("held", []):
            if float(hk["from"]) <= 0:
                continue
            who = str(hk["by"]).partition(".")[0]
            act = next(a for a in spec["actors"] if a["id"] == who)
            body = actor_at(spec, act, float(hk["from"]), resolve=False)["pos"]
            rx, ry, _ = prop_rest(spec, p, float(hk["from"]) - 1e-3)
            reach = math.dist(body, (rx, ry))
            if reach > REACH_M:
                W.append(f"prop {p['id']}: {who} picks it up at {float(hk['from']):g} s from {reach:.2f} m away "
                         f"(an arm reaches about {REACH_M} m) — move the prop or the actor")
    # sampled geometry and framing
    w, h = spec["render"]["w"], spec["render"]["h"]
    vertical = h > w
    seen = set()
    steps = int(round(dur / 0.1)) + 1
    loa = spec.get("line_of_action")
    prev_side, prev_t = None, 0.0
    sol = solids(spec)
    occl = {}                                                # id -> (start time, blocker)
    for i in range(steps):
        t = min(dur, i * 0.1)
        states = {a["id"]: actor_at(spec, a, t) for a in spec["actors"]}
        al = list(states.items())
        for x in range(len(al)):
            for y in range(x + 1, len(al)):
                if math.dist(al[x][1]["pos"], al[y][1]["pos"]) < 2 * BODY_R * 0.9:
                    key = f"{al[x][0]}-{al[y][0]}"
                    if key not in seen:
                        F.append(f"actors {al[x][0]} and {al[y][0]} interpenetrate at t={t:.1f}s"); seen.add(key)
        for aid, st in states.items():
            act = next(a for a in spec["actors"] if a["id"] == aid)
            top = actor_heights(act, st["pose"], st["seat"])["top"]
            if st["pose"] == "sit" and st["seat"] is None and f"nosit-{aid}" not in seen:
                W.append(f"actor {aid} sits at t={t:.1f}s with no seat under them — add a chair/stool/sofa at "
                         f"their position"); seen.add(f"nosit-{aid}")
            for p in sol:
                sit_ok = st["pose"] == "sit" and p.get("kind") in SEAT
                z0 = float(p.get("z", 0))
                if sit_ok or not (z0 < top - 0.1 and z0 + dims(p)[2] > 0.1):
                    continue
                if rect_contains(p, st["pos"][0], st["pos"][1], pad=BODY_R * 0.6):
                    key = f"{aid}-in-{p['id']}"
                    if key not in seen:
                        F.append(f"actor {aid} stands inside {p['id']} at t={t:.1f}s"); seen.add(key)
        cam = camera_at(spec, t)
        cp = cam["pos"]
        for p in sol:
            if p.get("camera_through"):
                continue
            z0 = float(p.get("z", 0))
            if rect_contains(p, cp[0], cp[1]) and z0 <= cp[2] <= z0 + dims(p)[2]:
                key = f"cam-in-{p['id']}"
                if key not in seen:
                    F.append(f"the camera passes inside {p['id']} at t={t:.1f}s — move it, or mark the piece "
                             f"\"camera_through\": true if that is the shot"); seen.add(key)
        for aid, st in states.items():
            act = next(a for a in spec["actors"] if a["id"] == aid)
            top = actor_heights(act, st["pose"], st["seat"])["top"]
            if math.dist(st["pos"], cp[:2]) < 0.20 and cp[2] < top and f"cam-in-{aid}" not in seen:
                F.append(f"the camera passes through {aid} at t={t:.1f}s"); seen.add(f"cam-in-{aid}")
        for a_ in spec["actors"]:
            st_ = states[a_["id"]]
            ey = (st_["pos"][0], st_["pos"][1], actor_heights(a_, st_["pose"], st_["seat"])["eye"])
            if math.dist(ey, cp) < NEAR_LENS_M and f"near-{a_['id']}" not in seen:
                W.append(f"{a_['id']}'s head passes {math.dist(ey, cp):.2f} m from the lens at t={t:.1f}s"); seen.add(f"near-{a_['id']}")
        framed_ = {cam.get("subject")}                # a shot ON the prop is meant to be close; one merely listed is not
        for p_ in spec.get("props", []):
            pp = prop_at(spec, p_, t)["pos"]
            if p_["id"] in framed_:
                continue                              # the shot is on it: close is the point
            if math.dist(pp, cp) < NEAR_LENS_M and f"near-{p_['id']}" not in seen:
                W.append(f"{p_['id']} passes {math.dist(pp, cp):.2f} m from the lens at t={t:.1f}s — it will fill "
                         f"the frame; pull the camera back or move the hold"); seen.add(f"near-{p_['id']}")
        subj = cam.get("subject")
        listed = list(cam["key"].get("frame", []))
        det = cam["key"].get("detail")
        for sid in dict.fromkeys(([subj] if isinstance(subj, str) else []) + listed):
            pt = point_of(spec, f"{sid}.{det}" if det and sid == subj else sid, t)
            safe = SAFE if (sid in listed and _by_id(spec, sid)[0] == "prop") else 1.0   # an OTS shoulder sits at the edge
            if pt and not in_frame(cam, pt, w, h, safe) and f"out-{sid}" not in seen and not cam.get("in_whip"):
                W.append(f"{sid} is {'out of frame' if safe == 1.0 else 'outside the safe area (or out of frame)'} "
                         f"at t={t:.1f}s" + ((f" ({det})" if det and sid == subj else " (eyes)")
                                              if _by_id(spec, sid)[0] == "actor" else "")
                         + (" — the key's subject" if sid == subj and sid not in listed else " — listed in the key's `frame`"))
                seen.add(f"out-{sid}")
            # occlusion: something solid between the lens and what the shot is about
            if pt and not cam["key"].get("occlusion_ok"):
                blocker = occluded_by(spec, t, cp, pt, exclude=(sid,))
                if blocker:
                    occl.setdefault(sid, (t, blocker))
                elif sid in occl:
                    t0_, b_ = occl.pop(sid)
                    if t - t0_ >= 0.3 and f"occ-{sid}" not in seen:
                        W.append(f"{sid} is hidden behind {b_} from {t0_:.1f} s to {t:.1f} s — move the camera or "
                                 f"the blocker, or mark the key \"occlusion_ok\": true if it is a wipe"); seen.add(f"occ-{sid}")
        if vertical and isinstance(subj, str) and cam["key"].get("mode") == "eyes" and _by_id(spec, subj)[0] == "actor" \
                and not det and not cam.get("in_detail") and cam.get("speed", 0) < 3.0:
            # (on its way to or from a detail, or flying at speed, the eyes are in passing)
            sx, sy, dep = project(cam, point_of(spec, subj, t), w, h)
            frac = (1 - sy) / 2
            if dep > 0 and not 0.15 <= frac <= 0.65 and f"band-{subj}" not in seen:
                W.append(f"{subj}'s eyes sit at {frac:.0%} of the frame height at t={t:.1f}s — on a vertical frame "
                         f"they belong between 15 % and 65 % (cinematography-craft.md, the ad box)"); seen.add(f"band-{subj}")
        for a_ in spec["actors"]:
            if a_.get("face_out_of_frame") and f"face-{a_['id']}" not in seen:
                st_ = states[a_["id"]]
                chin = (st_["pos"][0], st_["pos"][1], actor_heights(a_, st_["pose"], st_["seat"])["top"] - 0.21)
                if in_frame(cam, chin, w, h):
                    W.append(f"{a_['id']} is marked face_out_of_frame and their chin is in frame at t={t:.1f}s")
                    seen.add(f"face-{a_['id']}")
        if loa and len(loa) == 2 and not spec["camera"].get("cross_line"):
            a, b = states[loa[0]]["pos"], states[loa[1]]["pos"]
            s = (b[0] - a[0]) * (cp[1] - a[1]) - (b[1] - a[1]) * (cp[0] - a[0])
            side = s > 0
            if prev_side is not None and side != prev_side:
                c = next((c for c in cuts_of(spec) if prev_t < c <= t + 1e-9), None)
                if c is not None and "line" not in seen:
                    W.append(f"the cut at {c:g} s crosses the line of action {loa[0]}–{loa[1]} — screen sides swap "
                             f"between the two shots; mark \"cross_line\": true if it is meant"); seen.add("line")
            prev_side, prev_t = side, t
    for sid, (t0_, b_) in occl.items():
        if dur - t0_ >= 0.3 and f"occ-{sid}" not in seen:
            W.append(f"{sid} is hidden behind {b_} from {t0_:.1f} s to the end — move the camera or the blocker")
    # the camera's own motion: pans, travel and jolts, frame by frame
    dt = 1.0 / fps
    cuts = cuts_of(spec)
    prev, prev_v, prev_t = None, None, None
    for i in range(int(dur * fps) + 1):
        t = min(dur, i * dt)
        c = camera_at(spec, t)
        if prev is not None and not any(prev_t < cc <= t + 1e-9 for cc in cuts):
            v = math.dist(c["base_pos"], prev["base_pos"]) / dt          # the rig's path; its vibration is not a jolt
            rig_ = CAM.rig_of(c.get("rig"))
            pan_limit = rig_["max_dps"] if c.get("rig") in CAM.FAST_AIM else MAX_PAN_DPS
            travel_limit = max(MAX_TRAVEL_MPS, rig_["max_mps"])
            f0 = [prev["look_at"][j] - prev["pos"][j] for j in range(3)]
            f1 = [c["look_at"][j] - c["pos"][j] for j in range(3)]
            n0, n1 = math.sqrt(sum(x * x for x in f0)) or 1, math.sqrt(sum(x * x for x in f1)) or 1
            cosang = max(-1.0, min(1.0, sum(f0[j] * f1[j] for j in range(3)) / (n0 * n1)))
            omega = math.degrees(math.acos(cosang)) / dt
            k = c["key"]
            if omega > pan_limit and not (k.get("whip") or c.get("in_whip")) and "pan" not in seen:
                W.append(f"the camera turns {omega:.0f}°/s at t={t:.2f}s — faster than {pan_limit:g}°/s strobes and "
                         f"loses the subject; slow it, or mark the key \"whip\": true if it is a whip pan"); seen.add("pan")
            if v > travel_limit and not (k.get("vehicle") or k.get("attach")) and "travel" not in seen:
                W.append(f"the camera travels {v:.1f} m/s at t={t:.2f}s — faster than its rig ({c.get('rig')}) carries a "
                         f"camera; use a faster rig or mark \"vehicle\": true if it is mounted on one"); seen.add("travel")
            if prev_v is not None and abs(v - prev_v) / dt > rig_.get("max_acc", MAX_ACCEL) \
                    and not (k.get("whip") or c.get("in_whip") or k.get("vehicle") or k.get("attach")) \
                    and "jolt" not in seen:
                W.append(f"the camera jolts at t={t:.2f}s (speed changes {abs(v - prev_v):.2f} m/s in one frame) — "
                         f"a move that starts or stops dead reads as a mistake; ease it"); seen.add("jolt")
            prev_v = v
        else:
            prev_v = None
        prev, prev_t = c, t
    aerial_bounds(spec, F, W)
    # across each cut: the 30° rule and screen direction
    for c in cuts:
        cb, ca = camera_at(spec, c - dt), camera_at(spec, c)
        sb, sa = cb.get("subject"), ca.get("subject")
        if isinstance(sb, str) and sb == sa and _by_id(spec, sb)[0] == "actor":
            act = _by_id(spec, sb)[1]
            S = actor_at(spec, act, c, resolve=False)["pos"]
            a0 = math.degrees(math.atan2(cb["pos"][1] - S[1], cb["pos"][0] - S[0]))
            a1 = math.degrees(math.atan2(ca["pos"][1] - S[1], ca["pos"][0] - S[0]))
            z0, z1 = _size_of_cam(spec, cb), _size_of_cam(spec, ca)
            steps_ = abs(SIZES.index(z0) - SIZES.index(z1)) if z0 and z1 else 9
            if abs(ang_diff(a0, a1)) < 30 and steps_ < 2:
                W.append(f"the cut at {c:g} s changes the angle on {sb} by {abs(ang_diff(a0, a1)):.0f}° and the size "
                         f"by {steps_} step(s) — under 30° and under two sizes reads as a jump cut "
                         f"(cinematography-craft.md §4.5)")
        for a in spec["actors"]:
            if a.get("in") and (cb["key"].get("attach") or ca["key"].get("attach")):
                continue                              # riding in the car the lens is rigged to: they do not cross frame
            p_1, p0 = actor_at(spec, a, c - 2 * dt, resolve=False)["pos"], actor_at(spec, a, c - dt, resolve=False)["pos"]
            p1, p2 = actor_at(spec, a, c, resolve=False)["pos"], actor_at(spec, a, c + dt, resolve=False)["pos"]
            if math.dist(p_1, p0) / dt < 0.2 or math.dist(p1, p2) / dt < 0.2:   # m/s: slower reads as standing
                continue
            z = heights_at(spec, a, c)["chest"]
            b0, b1 = project(cb, (*p_1, z), w, h), project(cb, (*p0, z), w, h)
            a0_, a1_ = project(ca, (*p1, z), w, h), project(ca, (*p2, z), w, h)
            if min(b0[2], b1[2], a0_[2], a1_[2]) <= 0.05:
                continue
            vb, va = b1[0] - b0[0], a1_[0] - a0_[0]
            if vb * va < 0 and abs(vb) > 1e-3 and abs(va) > 1e-3:
                W.append(f"{a['id']} moves frame {'right' if vb > 0 else 'left'} before the cut at {c:g} s and frame "
                         f"{'right' if va > 0 else 'left'} after it — screen direction flips")
    if not spec.get("sky"):
        for t in sorted({0.0, dur} | {float(k["t"]) for k in spec["camera"]["keys"]} | set(cuts)
                        | {float(i) for i in range(1, int(dur) + 1)}):
            vf_ = void_fraction(spec, min(t, dur))
            if vf_ > VOID_WARN:
                W.append(f"at t={t:g}s {vf_:.0%} of the frame is empty void — no wall or set behind the action, so the "
                         f"video model invents it. Add the walls the scene has (or \"sky\": true for an exterior)")
                break
    for ck in camera_keys(spec):
        if ck.get("size_asked") and ck.get("size_computed") and \
                abs(SIZES.index(ck["size_asked"]) - SIZES.index(ck["size_computed"])) > 1:
            W.append(f"camera key t={ck['t']:g}s: asks {ck['size_asked']}, the geometry gives "
                     f"{ck['size_computed']} ({ck['visible_height_m']} m visible)")
    for i, sh in enumerate(spec["camera"].get("shots", []), 1):
        mv = sh.get("move")
        if not mv:
            continue
        t0_, t1_ = float(sh["t"][0]), float(sh["t"][1]) - dt
        words = camera_motion(spec, t0_, t1_)
        moving = [x for x in words if x.split()[0] in ("pushes", "pulls", "arcs", "rises", "lowers", "follows", "leads", "trucks",
                                                       "tracks", "rides")]
        want = CAM.confirms(mv) if mv in CAM.LIBRARY else MOVES.get(mv, set())
        if "*" in want:
            continue
        if not want and moving:
            W.append(f"shot {i} declares {mv!r} and the camera {', '.join(moving)}")
        elif want and not any(x.startswith(tuple(want)) for x in words):
            W.append(f"shot {i} declares {mv!r} and the camera " + (", ".join(words) if words else "stays put"))
    for (who, hand), spans in holds.items():
        spans.sort()
        for (a0, a1, pa), (b0, b1, pb) in zip(spans, spans[1:]):
            if b0 < a1:
                W.append(f"{who}'s {hand} hand holds {pa} and {pb} at once ({b0:g}–{min(a1, b1):g} s)")
    seen_focus = set()
    for k in camera_keys(spec):                  # a rack must land on something the audience can see
        f_ = k.get("focus")
        if isinstance(f_, str) and (f_, k.get("shot")) not in seen_focus and point_of(spec, f_, k["t"]):
            seen_focus.add((f_, k.get("shot")))
            cam_ = camera_at(spec, k["t"])
            wh = _where(spec, cam_, point_of(spec, f_, k["t"])) if cam_ else ""
            if wh.startswith(("behind", "out of")):
                W.append(f"focus on {f_} at {k['t']:g} s: {f_} is {wh} — a rack to something the audience cannot see")
    return F, W


# ── the prompt blocks, computed from the geometry ────────────────────────────────────────────────────────
def _label(spec: dict, ident: str) -> str:
    kind, obj = _by_id(spec, ident)
    if obj and obj.get("name"):
        return obj["name"]
    col = (obj or {}).get("color", NEUTRAL)
    txt = spec["legend"].get(col, "")
    if not txt or len(colours_used(spec).get(col, [])) > 1:
        return str(ident).replace("_", " ")
    return txt.split(",")[0].split(";")[0].strip()


def _where(spec: dict, cam: dict, p: tuple) -> str:
    w, h = spec["render"]["w"], spec["render"]["h"]
    sx, sy, d = project(cam, p, w, h)
    if d <= 0.05:
        return "behind the camera"
    if abs(sx) > 1.05:
        return "out of frame " + ("left" if sx < 0 else "right")
    if abs(sy) > 1.1:
        return "out of frame " + ("below" if sy < 0 else "above")
    return "frame left" if sx < -0.33 else "frame right" if sx > 0.33 else "centre frame"


def _facing_words(spec: dict, cam: dict, st: dict, eye: float) -> str:
    to_cam = math.degrees(math.atan2(cam["pos"][1] - st["pos"][1], cam["pos"][0] - st["pos"][0]))
    d = abs(ang_diff(st["facing"], to_cam))
    if d < 25:
        return "faces the camera"
    fr = math.radians(st["facing"])
    fx, fy = cam["look_at"][0] - cam["pos"][0], cam["look_at"][1] - cam["pos"][1]
    way = "frame right" if math.cos(fr) * fy - math.sin(fr) * fx > 0 else "frame left"   # facing · camera-right
    if d < 65:
        return f"three-quarter to camera, looking {way}"
    if d < 115:
        return f"in profile, looking {way}"
    if d < 155:
        return f"three-quarter away, looking {way}"
    return "back to camera"


def _height_tilt(spec: dict, c: dict) -> str:
    """'camera at eye height, tilted 6° down' — height and tilt written separately (sequence-grammar.md §3)."""
    subj = c.get("subject")
    z = c["pos"][2]
    hw = f"camera at {z:.1f} m"
    kind, obj = _by_id(spec, subj) if isinstance(subj, str) else (None, None)
    if kind == "actor":
        hh = heights_at(spec, obj, 0.0 if c.get("t") is None else c["t"])
        for name in ("eye", "chest", "waist", "hip", "knee"):
            if abs(z - hh[name]) < 0.1:
                hw = f"camera at {name} height"
                break
    elif kind == "prop":
        hw = f"camera level with {_label(spec, subj)}" if abs(z - c["target"][2]) < 0.12 else \
            f"camera {'above' if z > c['target'][2] else 'below'} {_label(spec, subj)}"
    tl = _tilt(c)
    return hw + (", level" if abs(tl) < 4 else f", tilted {abs(tl):.0f}° {'down' if tl < 0 else 'up'}")


def positions_at(spec: dict, t: float) -> str:
    cam = camera_at(spec, t)
    parts = []
    for a in spec["actors"]:
        st = actor_at(spec, a, t)
        hh = actor_heights(a, st["pose"], st["seat"])
        where = _where(spec, cam, (st["pos"][0], st["pos"][1], hh["chest"]))
        bit = f"{_label(spec, a['id'])} {where}"
        if not where.startswith(("out of", "behind")):
            bit += (", seated" if st["pose"] == "sit" else "") + ", " + _facing_words(spec, cam, st, hh["eye"])
        parts.append(bit)
    for p in spec.get("props", []):
        pa = prop_at(spec, p, t)
        if pa["held_by"]:
            who, hand = pa["held_by"]
            bit = f"{_label(spec, p['id'])} in {_label(spec, who)}'s {hand} hand"
        else:
            on = p.get("on")
            bit = f"{_label(spec, p['id'])} {_where(spec, cam, pa['pos'])}" + (f", on the {on.replace('_', ' ')}" if on else "")
        if p.get("label_toward") == "camera" and not _where(spec, cam, pa["pos"]).startswith(("out of", "behind")):
            bit += ", label to camera"
        parts.append(bit)
    return f"{round(t, 2):g} s: " + "; ".join(parts) + "."


# the aerial moves added in v2.38.0 (and any shot marked "aerial": true) are held to the move table:
# house rule C4, 2026-10-26 — "Split: rules refuse, measures warn". A cap (max_turns) refuses; a speed,
# radius, rate or height outside the practitioner range warns, because the ranges are defaults, not physics.
AERIAL_MOVES = {"drone_orbit", "helix", "parallax_orbit", "boomerang", "hover_pan", "tilt_down_reveal", "pedestal",
                "rocket", "drone_side_follow", "drone_push_in", "gap_fly_through", "cinewhoop_oner", "hole_flyover",
                "bee_path", "mosquito_path"}


def aerial_measure(spec: dict, sh: dict) -> dict:
    """What one aerial shot does on the camera that renders: mean speed in the middle 60 % (horizontal,
    vertical, or relative to the subject, as the table row says), mean radius and distance to the subject,
    turns round it, pan rate, mean height, the closest pass to `past`."""
    name, row = CAM.aerial_spec(sh.get("move"))
    row = row or {}
    fps = float(spec["fps"])
    t0, t1 = float(sh["t"][0]), float(sh["t"][1]) - 1.0 / fps
    n = max(3, int(round((t1 - t0) * fps)) + 1)
    ts = [t0 + (t1 - t0) * i / (n - 1) for i in range(n)]
    cams = [camera_at(spec, t) for t in ts]
    subj = sh.get("on")
    sp = point_of(spec, subj, t0) is not None if isinstance(subj, str) else False
    g = [point_of(spec, subj, t)[:2] for t in ts] if sp else None
    lo, hi = int(n * 0.2), max(int(n * 0.2) + 2, int(n * 0.8))
    v = []
    for i in range(lo, min(hi, n - 1)):
        a, b = cams[i]["base_pos"], cams[i + 1]["base_pos"]
        dt_ = ts[i + 1] - ts[i]
        if row.get("speed_axis") == "vertical":
            v.append(abs(b[2] - a[2]) / dt_)
        elif row.get("speed_relative") and g:
            v.append(math.hypot((b[0] - g[i + 1][0]) - (a[0] - g[i][0]), (b[1] - g[i + 1][1]) - (a[1] - g[i][1])) / dt_)
        else:
            v.append(math.hypot(b[0] - a[0], b[1] - a[1]) / dt_)
    out = {"move": name, "speed_mps": round(sum(v) / len(v), 2) if v else 0.0,
           "height_m": round(sum(c["base_pos"][2] for c in cams) / n, 1)}
    if g:
        rad = [math.hypot(c["base_pos"][0] - q[0], c["base_pos"][1] - q[1]) for c, q in zip(cams, g)]
        out["radius_m"] = round(sum(rad) / n, 1)
        ang = [math.degrees(math.atan2(c["base_pos"][1] - q[1], c["base_pos"][0] - q[0])) for c, q in zip(cams, g)]
        swept = sum(ang_diff(a_, b_) for a_, b_ in zip(ang, ang[1:]))
        out["turns"] = round(abs(swept) / 360.0, 2)
        if out["turns"] > 0.05:
            out["secs_per_turn"] = round((t1 - t0) / out["turns"], 1)
    yaw = [math.degrees(math.atan2(c["look_at"][1] - c["pos"][1], c["look_at"][0] - c["pos"][0])) for c in cams]
    out["deg_per_s"] = round(abs(sum(ang_diff(a_, b_) for a_, b_ in zip(yaw, yaw[1:]))) / max(t1 - t0, 1e-6), 1)
    if sh.get("past") and point_of(spec, sh["past"], t0):
        q = point_of(spec, sh["past"], t0)
        out["foreground_m"] = round(min(math.hypot(c["base_pos"][0] - q[0], c["base_pos"][1] - q[1]) for c in cams), 1)
    return out


def aerial_bounds(spec: dict, F: list, W: list) -> None:
    for i, sh in enumerate(spec["camera"].get("shots", []), 1):
        mv = sh.get("move")
        if mv not in AERIAL_MOVES and not sh.get("aerial"):
            continue
        name, row = CAM.aerial_spec(mv)
        if not row:
            continue
        m = aerial_measure(spec, sh)
        tag = f"shot {i} ({mv} — the table's {name})"
        cap = row.get("max_turns")
        if cap is not None and m.get("turns", 0) > float(cap) + 1e-6:
            F.append(f"{tag}: {m['turns']:.2f} turns round {sh.get('on')} — never more than {cap:g} in a delivered "
                     f"edit ({row.get('source', '').split(':')[0]}); cut it shorter or slow it")
        checks = [("speed_mps", "speed_mps", "m/s", "flies"), ("radius_m", "radius_m", "m", "circles at a radius of"),
                  ("secs_per_turn", "secs_per_turn", "s per turn", "turns once every"),
                  ("deg_per_s", "deg_per_s", "°/s", "pans"), ("altitude_m", "height_m", "m", "flies at"),
                  ("distance_m", "radius_m", "m", "keeps"), ("foreground_m", "foreground_m", "m", "passes its foreground at")]
        for key, got, unit, verb in checks:
            rng = row.get(key)
            if not rng or got not in m:
                continue
            x = float(m[got])
            if not (float(rng[0]) <= x <= float(rng[1])):
                W.append(f"{tag}: it {verb} {x:g} {unit}; the move table gives {rng[0]:g}–{rng[1]:g} {unit} "
                         f"(assets/aerial-moves.json, {row.get('source', '').split(';')[0][:60]})")


def camera_beats(spec: dict, s0: float, s1: float) -> list:
    """The shot's camera, phase by phase, measured on the camera that renders: when it holds, when it
    moves and how (the words, how long, how fast at its peak, whether it eases, snaps or overshoots), and
    the dutch, focus pulls and flinches inside it. This is what makes the prompt say what the blocking
    does instead of naming a move."""
    fps = float(spec["fps"])
    n = max(2, int(round((s1 - s0) * fps)) + 1)
    ts = [s0 + (s1 - s0) * i / (n - 1) for i in range(n)]
    cams = [camera_at(spec, t) for t in ts]
    yaw, dirs = [], []
    for c in cams:
        d = [c["look_at"][j] - c["pos"][j] for j in range(3)]
        yaw.append((math.degrees(math.atan2(d[1], d[0])), math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))))
        nd = math.sqrt(sum(x * x for x in d)) or 1.0
        dirs.append([x / nd for x in d])

    def turn(i, j):                                   # the angle the lens turns between two samples (no gimbal lock)
        return math.degrees(math.acos(max(-1.0, min(1.0, sum(dirs[i][q] * dirs[j][q] for q in range(3))))))
    moving = []
    for i in range(n):
        j = min(i + 1, n - 1); k = max(i - 1, 0)
        dt = (ts[j] - ts[k]) or 1.0
        v = math.dist(cams[j]["base_pos"], cams[k]["base_pos"]) / dt
        w = turn(k, j) / dt
        z = abs(cams[j]["lens_mm"] - cams[k]["lens_mm"]) / dt
        moving.append(v > 0.08 or w > 9.0 or z > 4.0)
    # phases: runs of moving/holding, short flickers merged into their neighbours
    shot_of = [(c.get("shot"), c["key"].get("beat")) for c in cams]     # a move's own phases (a dive, then a chase)
    phases, start = [], 0
    for i in range(1, n + 1):
        if i == n or moving[i] != moving[start] or shot_of[i] != shot_of[start]:   # a joined shot is its own beat
            phases.append([start, i - 1, moving[start]])
            start = i
    merged = []
    for p in phases:
        same_shot = merged and (shot_of[merged[-1][0]] == shot_of[p[0]] or (not p[2] and not merged[-1][2]))
        if merged and same_shot and (ts[p[1]] - ts[p[0]] < 0.25):
            merged[-1][1] = p[1]
        else:
            if merged and same_shot and merged[-1][2] == p[2]:
                merged[-1][1] = p[1]
            else:
                merged.append(p)
    out = []
    for a, b, mv in merged:
        ta, tb = ts[a], ts[b]
        if not mv:
            out.append({"t0": ta, "t1": tb, "kind": "hold"})
            continue
        words = camera_motion(spec, ta, tb, cams[a], cams[b])
        peak_w = max((turn(i, i + 1) * fps for i in range(a, b)), default=0.0)
        peak_v = max((math.dist(cams[i]["base_pos"], cams[i + 1]["base_pos"]) * fps for i in range(a, b)), default=0.0)
        # overshoot: the aim passes where it ends up and comes back
        final = yaw[min(b + int(0.6 * fps), n - 1)][0]
        sweep = ang_diff(yaw[a][0], final)
        over = 0.0
        if abs(sweep) > 6:
            for i in range(a, min(b + int(0.6 * fps), n - 1) + 1):
                past = ang_diff(final, yaw[i][0]) * (1 if sweep > 0 else -1)
                over = max(over, past)
        dur_ = tb - ta
        if dur_ < 0.7 and (peak_w > 90 or peak_v > 2.0):
            feel = "snaps"
        elif dur_ > 3.0 and peak_v < 0.35 and peak_w < 20:
            feel = "creeps"
        else:
            feel = "eases"
        shots_ = spec["camera"].get("shots", [])
        sh_i, beat_ = shot_of[a]
        mvname = shots_[sh_i - 1].get("move") if sh_i and 0 < sh_i <= len(shots_) else None
        if beat_:
            mvname = f"{(mvname or '').replace('_', ' ')}: {beat_}".strip(": ")
        out.append({"t0": ta, "t1": tb, "kind": "move", "words": words, "peak_dps": peak_w, "peak_mps": peak_v,
                    "overshoot_deg": over, "feel": feel, "move": mvname, "shot": sh_i})
    return out


def _beats_text(spec: dict, s0: float, s1: float) -> str:
    beats = camera_beats(spec, s0, s1)
    if len(beats) <= 1 and beats and beats[0]["kind"] == "hold":
        parts = []
    else:
        parts = []
        for b in beats:
            if b["kind"] == "hold":
                parts.append(f"holds {b['t0']:.1f}–{b['t1']:.1f} s")
            else:
                w = ", ".join(b["words"]) or "drifts"
                speed = []
                if b["peak_mps"] > 0.15:
                    speed.append(f"{b['peak_mps']:.1f} m/s at its fastest")
                if b["peak_dps"] > 15:
                    speed.append(f"{b['peak_dps']:.0f}°/s at its fastest")
                land = " and lands with a small overshoot" if b["overshoot_deg"] > 1.2 else ""
                named = (f" ({b['move'].replace('_', ' ')})" if b.get("move") and
                         len({x.get("move") for x in beats if x["kind"] == "move"}) > 1 else "")
                parts.append(f"{b['t0']:.1f}–{b['t1']:.1f} s {b['feel']}{named}: {w}" + (f" ({'; '.join(speed)})" if speed else "") + land)
    c0, c1 = camera_at(spec, s0), camera_at(spec, s1)
    extra = []
    r0, r1 = c0["roll_deg"], c1["roll_deg"]
    if max(abs(r0), abs(r1)) > 3:
        extra.append(f"Dutch {abs(r0):.0f}°" + (f" easing to {abs(r1):.0f}°" if abs(abs(r1) - abs(r0)) > 2 else "")
                     + (" left" if r0 > 0 else " right"))
    if c0.get("fstop"):
        f0, f1 = c0.get("focus_m"), c1.get("focus_m")
        if f0 and f1 and abs(math.log(f1 / f0)) > 0.3:
            extra.append(f"focus racks from {f0:.1f} m to {f1:.1f} m at f/{c0['fstop']:g}, one plane sharp at a time")
        elif f0:
            extra.append(f"shallow focus at f/{c0['fstop']:g} on {f0:.1f} m")
    for r in spec.get("_reacts", []):
        if s0 <= r["t"] <= s1:
            extra.append(f"the operator {r['kind'].replace('_', ' ')}es at {r['t']:.1f} s" if r["kind"].endswith("ch")
                         else f"the camera takes a {r['kind'].replace('_', ' ')} at {r['t']:.1f} s")
    txt = ""
    if parts:
        txt += " Beats: " + "; ".join(parts) + "."
    if extra:
        txt += " " + "; ".join(extra).capitalize() + "."
    return txt


def describe(spec: dict) -> dict:
    """The clip-prompt blocks a blocked take needs, in the house block grammar (prompting-craft.md)."""
    spec = prepare(spec)
    reset_camera_cache()
    dur, fps = float(spec["duration"]), float(spec["fps"])
    bounds = [0.0] + [c for c in cuts_of(spec) if 0 < c < dur] + [dur]
    shots = spec["camera"].get("shots", [])
    stages, marks = [], []
    for si, (s0, s1) in enumerate(zip(bounds, bounds[1:])):
        e = s1 - (1.0 / fps if s1 < dur else 0.0)
        c0, c1 = camera_at(spec, s0), camera_at(spec, e)
        c0["t"], c1["t"] = s0, e
        subj = c0.get("subject")
        group = [a for a in spec["actors"] if a["id"] in c0["key"].get("frame", [])] if not subj else []
        if not subj and c0["key"].get("look_ids"):
            group = [a for a in spec["actors"] if a["id"] in c0["key"]["look_ids"]] or group
        kind, obj = _by_id(spec, subj) if isinstance(subj, str) else (None, None)
        tall = (float(obj.get("height", 1.7)) if kind == "actor" else
                max([float(a.get("height", 1.7)) for a in group] or [1.7]))

        def size_at(c):
            if kind != "actor" and not group:
                if isinstance(subj, str) and kind:
                    seen_ = 2 * math.dist(c["pos"], c["target"]) * math.tan(math.radians(c["vfov_deg"]) / 2)
                    return object_size_for(spec, subj, seen_)
                return "insert"
            if c["key"].get("detail") in ("mouth", "eyes"):
                return "ECU"
            if c["key"].get("detail"):
                return "insert"
            dist = math.dist(c["pos"], c["target"])
            return size_for(2 * dist * math.tan(math.radians(c["vfov_deg"] if spec["render"]["h"] >= spec["render"]["w"]
                                                              else c["hfov_deg"]) / 2), tall)
        z0, z1 = size_at(c0), size_at(c1)
        moves = camera_motion(spec, s0, e, c0, c1)
        hh_kind = c0["key"].get("handheld", "none")
        if hh_kind != "none":
            moves.append({"breathing": "handheld, breathing (never quite still)", "handheld": "handheld",
                          "walking": "handheld, walking with them"}[hh_kind])
        det0 = c0["key"].get("detail")
        who = ((f"{_label(spec, subj)}'s {det0}" if det0 and kind == "actor" else _label(spec, subj)) if isinstance(subj, str) else
               ("two-shot of " + " and ".join(_label(spec, a["id"]) for a in group) if len(group) == 2 else
                "group shot of " + ", ".join(_label(spec, a["id"]) for a in group) if group else "the frame"))
        if kind not in ("actor", None) and isinstance(subj, str):   # a frame on a thing: say who shares it
            w_, h_ = spec["render"]["w"], spec["render"]["h"]
            mates = [a["id"] for a in spec["actors"]
                     if any(in_frame(cc, point_of(spec, f"{a['id']}.chest", cc["t"]), w_, h_) for cc in (c0, c1))]
            if mates:
                who = f"{who}, with {' and '.join(_label(spec, m) for m in mates)} in frame"
        on_ = "" if who.startswith(("two-shot", "group shot")) else "on "
        size_txt = z0 if z0 == z1 else f"{z0} → {z1}"
        det1 = c1["key"].get("detail")
        if det0 != det1 and kind == "actor" and isinstance(subj, str):
            who1 = f"{_label(spec, subj)}'s {det1}" if det1 else _label(spec, subj)
            size_txt, on_, who = f"{z0} on {who} → {z1}", "on ", who1
        declared = c0.get("shot") and shots and shots[c0["shot"] - 1].get("move")
        joined = [shots[k_ - 1].get("move") for k_ in range(c0.get("shot") or 1, (c1.get("shot") or 0) + 1)
                  if shots and 0 < k_ <= len(shots) and shots[k_ - 1].get("move")]
        if len(joined) > 1:
            declared = " → ".join(joined)
        lens_txt = (f"{c0['lens_mm']:.0f} mm" if abs(c1["lens_mm"] - c0["lens_mm"]) < 2 else
                    f"{c0['lens_mm']:.0f} → {c1['lens_mm']:.0f} mm")
        stages.append(f"{s0:.1f}–{s1:.1f} s: {size_txt} {on_}{who}, {lens_txt}, {_height_tilt(spec, c0)}; "
                      + (", ".join(moves) if moves else "locked off") + "."
                      + (f" ({declared.replace('_', ' ')})" if declared else "")
                      + f" Rig: {CAM.rig_words(c0.get('rig'))}"
                      + (f" → {CAM.rig_words(c1.get('rig'))}" if c1.get("rig") != c0.get("rig") else "") + "."
                      + _beats_text(spec, s0, e))
        times = sorted({round(s0, 2), round(e, 2)} | {round(float(k['t']), 2) for k in spec['camera']['keys']
                                                         if s0 < float(k['t']) < e})
        for t in times[:4]:
            m = positions_at(spec, t)
            if not marks or marks[-1].split(": ", 1)[1] != m.split(": ", 1)[1]:
                marks.append(m)               # an unchanged picture is said once
    events = []
    for a in spec["actors"]:
        ks = sorted(a["keys"], key=lambda k: float(k["t"]))
        for ka, kb in zip(ks, ks[1:]):
            ta, tb = float(ka["t"]), float(kb["t"])
            if math.dist(ka["pos"], kb["pos"]) > 0.3:
                events.append((ta, f"{_label(spec, a['id'])} walks {math.dist(ka['pos'], kb['pos']):.1f} m "
                                   f"({ta:g}–{tb:g} s)"))
            pa, pb = ka.get("pose", a.get("pose", "stand")), kb.get("pose", a.get("pose", "stand"))
            if pa != pb:
                events.append((tb, f"{_label(spec, a['id'])} {'sits down' if pb == 'sit' else 'stands up' if pa == 'sit' else pb} by {tb:g} s"))
            fa = actor_at(spec, a, ta)["facing"]; fb = actor_at(spec, a, tb)["facing"]
            if abs(ang_diff(fa, fb)) > 40:
                tgt = kb.get("facing")
                to = (f"toward {_label(spec, tgt)}" if isinstance(tgt, str) and tgt != "camera" else
                      "to the camera" if tgt == "camera" else f"{abs(ang_diff(fa, fb)):.0f}°")
                events.append((ta, f"{_label(spec, a['id'])} turns {to} ({ta:g}–{tb:g} s)"))
            lk = kb.get("look")
            if isinstance(lk, str) and lk != ka.get("look"):
                events.append((ta, f"{_label(spec, a['id'])} looks at {'the camera' if lk == 'camera' else _label(spec, lk)} "
                                   f"by {tb:g} s"))
    for p in spec.get("props", []):
        for hk in p.get("held", []):
            who, _, hand = str(hk["by"]).partition(".")
            f0, f1 = float(hk["from"]), float(hk["to"])
            if f0 > 0:
                events.append((f0, f"{_label(spec, who)} picks up {_label(spec, p['id'])} with the {hand} hand at {f0:g} s"))
            if f1 < dur:
                events.append((f1, f"{_label(spec, who)} sets {_label(spec, p['id'])} down at {f1:g} s"))
    legend = [f"{c} = {txt}" for c, txt in spec["legend"].items()]
    legend.append("grey shapes and the floor grid = stand-ins only; the set, light and wardrobe come from the text "
                  "and the reference images")
    n_cuts = len(bounds) - 2
    blocks = {
        "BLOCKING": (f"The blocking video is a grey 3D render of this shot, {dur:g} s, "
                     f"{spec.get('aspect', '')}{', ' + str(n_cuts) + ' hard cut' + ('s' if n_cuts > 1 else '') if n_cuts else ', one continuous take'}. "
                     f"Take from it only: camera position and path, framing, cut times, where each person and object is, "
                     f"and which way each person faces. Its colours, mannequins, boxes, grid and flat light are not "
                     f"visual targets.\n" + "\n".join(marks)),
        "LEGEND": "\n".join(legend),
        "PRECEDENCE": ("Camera, cuts, timing, framing and positions: follow the blocking video. Faces, wardrobe, "
                       "product and location look: follow the reference images. Performance, hands, light and "
                       "sound: follow this text."),
        "CAMERA": "\n".join(stages),
        "MOTION": ("START: as the 0 s mark above. TBD: the performance at the start.\n"
                   "MID: " + ("; ".join(e for _, e in sorted(events)) or "no blocked movement") +
                   ". TBD: how they move — weight, hands, small actions; the mannequins are stiff on purpose.\n"
                   f"END: as the {dur:g} s mark above. TBD: the aftermath the clip settles into."),
        "SOUND": "The blocking video is silent: no sound, speech or on-screen text comes from it. TBD: ambience and music policy.",
    }
    return {"blocks": blocks, "duration": dur, "stages": stages, "events": [e for _, e in sorted(events)]}


def prompt_text(spec: dict) -> str:
    spec = prepare(spec)
    d = describe(spec)
    out = [f"# computed by blocking.py from {spec['shot']}.blocking.json — replace every TBD before linting",
           f"# frontmatter: duration: {d['duration']:g} · refs: - role: video_references · what: blocking · "
           f"manifest: <path to {spec['shot']}.blocking.manifest.json> · value: <media id of the uploaded MP4> · "
           f"not: mannequins, flat colours, floor grid, grey boxes"]
    for k, v in d["blocks"].items():
        out += [f"[{k}]", v]
    return "\n".join(out) + "\n"


# ── the map (code-drawn, no Blender) ─────────────────────────────────────────────────────────────────────
def draw_map(spec: dict, out: str, px: int = 900) -> str:
    from PIL import Image, ImageDraw
    spec = prepare(spec)
    reset_camera_cache()
    pieces = all_pieces(spec)
    pts = []
    for p in pieces:
        w, d, _ = dims(p)
        pts += [(p["pos"][0] - w / 2, p["pos"][1] - d / 2), (p["pos"][0] + w / 2, p["pos"][1] + d / 2)]
    for a in spec["actors"]:
        pts += [tuple(k["pos"]) for k in a["keys"]]
    dur = float(spec["duration"])
    path = [camera_at(spec, i * dur / 60) for i in range(61)]
    pts += [(c["pos"][0], c["pos"][1]) for c in path]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = 0.6
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    sc = (px - 60) / max(x1 - x0, y1 - y0)
    H = int((y1 - y0) * sc) + 60
    W_ = int((x1 - x0) * sc) + 60
    img = Image.new("RGB", (W_, H + 40), (236, 236, 236))
    dr = ImageDraw.Draw(img)

    def P(x, y):
        return (30 + (x - x0) * sc, 30 + (y1 - y) * sc)   # +Y is up on the map, away from the front

    g = math.floor(x0)
    while g <= x1:
        dr.line([P(g, y0), P(g, y1)], fill=(222, 222, 222)); g += 1
    g = math.floor(y0)
    while g <= y1:
        dr.line([P(x0, g), P(x1, g)], fill=(222, 222, 222)); g += 1

    def col(c, light=False):
        r = COLORS.get(c, COLORS[NEUTRAL])
        if light:
            r = tuple(0.5 + v / 2 for v in r)
        return tuple(int(v * 255) for v in r)

    for p in sorted(pieces, key=lambda q: 0 if q.get("kind") in WALKABLE else 1):
        if p["id"].endswith(".ceiling"):
            continue
        w, d, _ = dims(p)
        r = math.radians(float(p.get("rot", 0)))
        cs = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
        poly = [P(p["pos"][0] + cx * math.cos(r) - cy * math.sin(r), p["pos"][1] + cx * math.sin(r) + cy * math.cos(r))
                for cx, cy in cs]
        opening = not p.get("solid", True)
        fps = KIT.shape_footprints(p["shape"]) if p.get("shape") else []
        if fps:                                       # a precise shape draws its own outline
            for fp in fps:
                dr.polygon([P(p["pos"][0] + cx * math.cos(r) - cy * math.sin(r), p["pos"][1] + cx * math.sin(r) + cy * math.cos(r))
                            for cx, cy in fp], fill=col(p.get("color", NEUTRAL)), outline=(90, 90, 90))
        else:
            dr.polygon(poly, fill=col(p.get("color", NEUTRAL), light=opening or p.get("kind") in WALKABLE),
                       outline=(90, 90, 90))
        if not p.get("room") or opening:
            dr.text(P(p["pos"][0] - w / 2, p["pos"][1] + d / 2), p["id"].split(".")[-1] if p.get("room") else p["id"],
                    fill=(60, 60, 60))
    for p in spec.get("props", []):
        x, y, _ = prop_rest(spec, p, 0.0)
        cx, cy = P(x, y)
        dr.rectangle([cx - 4, cy - 4, cx + 4, cy + 4], fill=col(p.get("color", NEUTRAL)), outline=(30, 30, 30))
        dr.text((cx + 6, cy - 6), p["id"], fill=(30, 30, 30))
    loa = spec.get("line_of_action")
    if loa and len(loa) == 2:
        a0 = next(a for a in spec["actors"] if a["id"] == loa[0]); b0 = next(a for a in spec["actors"] if a["id"] == loa[1])
        pa, pb = actor_at(spec, a0, 0)["pos"], actor_at(spec, b0, 0)["pos"]
        vx, vy = pb[0] - pa[0], pb[1] - pa[1]
        dr.line([P(pa[0] - vx * 3, pa[1] - vy * 3), P(pb[0] + vx * 3, pb[1] + vy * 3)], fill=(200, 60, 60), width=1)
    for a in spec["actors"]:
        trail = [actor_at(spec, a, i * dur / 40, resolve=False)["pos"] for i in range(41)]
        dr.line([P(*q) for q in trail], fill=col(a["color"]), width=2)
        ks = sorted(a["keys"], key=lambda k: float(k["t"]))
        for j, k in enumerate(ks):
            st = actor_at(spec, a, float(k["t"]))
            cx, cy = P(*st["pos"])
            r_ = BODY_R * sc
            dr.ellipse([cx - r_, cy - r_, cx + r_, cy + r_], fill=col(a["color"]), outline=(30, 30, 30))
            fr = math.radians(st["facing"])
            dr.line([(cx, cy), (cx + math.cos(fr) * r_ * 2.0, cy - math.sin(fr) * r_ * 2.0)], fill=(20, 20, 20), width=3)
            dr.text((cx + r_ + 3, cy - r_ + 12 * j), f"{a['id']} {float(k['t']):g}s", fill=(20, 20, 20))
    dr.line([P(c["pos"][0], c["pos"][1]) for c in path], fill=(20, 20, 20), width=1)
    marks = sorted({0.0} | set(cuts_of(spec)) | ({float(s["t"][0]) for s in spec["camera"].get("shots", [])}))
    for tm in marks:
        c = camera_at(spec, tm)
        cx, cy = P(c["pos"][0], c["pos"][1])
        ang = math.atan2(c["look_at"][1] - c["pos"][1], c["look_at"][0] - c["pos"][0])
        half = math.radians(c["hfov_deg"]) / 2
        L = 1.4 * sc
        dr.polygon([(cx, cy), (cx + math.cos(ang - half) * L, cy - math.sin(ang - half) * L),
                    (cx + math.cos(ang + half) * L, cy - math.sin(ang + half) * L)], outline=(20, 20, 20))
        dr.rectangle([cx - 5, cy - 5, cx + 5, cy + 5], fill=(20, 20, 20))
        lab = f"cam {tm:g}s {c['lens_mm']:.0f}mm" + (f" shot {c['shot']}" if c.get("shot") else "")
        dr.text((cx + 8, cy + 6), lab, fill=(20, 20, 20))
    endc = camera_at(spec, dur)
    ex, ey = P(endc["pos"][0], endc["pos"][1])
    dr.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], outline=(20, 20, 20))
    cuts = ", ".join(f"{c:g}" for c in cuts_of(spec))
    dr.text((10, H + 12), f"{spec['shot']} · top-down · 1 m grid · front of set = bottom edge · arrows = facing · "
                          f"wedges = horizontal FOV · thin line = camera path (o = end)" + (f" · cuts at {cuts} s" if cuts else ""),
            fill=(40, 40, 40))
    img.save(out)
    return out


# ── the Blender build ────────────────────────────────────────────────────────────────────────────────────
def build(spec: dict, outdir: str, review_times: list, look: dict | None = None, times: list | None = None,
          res: int | None = None) -> dict:
    """The Blender scene, rendered. With `look` it is a concept frame instead (blocking_look.py): lit,
    materials on every part, stills at `times`, no grid, no legend colours on the set."""
    import bpy                                      # Blender as a Python module, or run inside Blender
    import mathutils
    spec = prepare(spec)
    concept = look is not None
    if concept and look.get("ceiling", (look.get("time") or LOOK.guess_time(spec)).startswith("interior")):
        reset_camera_cache()
        cams = [camera_at(spec, float(spec["duration"]) * i / 12)["pos"] for i in range(13)]
        for p_ in spec.get("set", []):            # a lit interior needs its ceiling, or the sky floods in
            if p_.get("kind") == "room":
                p_["ceiling"] = True
                W_, D_, H_ = (float(v) for v in p_.get("size", [5, 4, 2.7]))
                a_ = math.radians(float(p_.get("rot", 0)))
                inside = all(abs((c[0] - p_["pos"][0]) * math.cos(-a_) - (c[1] - p_["pos"][1]) * math.sin(-a_)) < W_ / 2
                             and abs((c[0] - p_["pos"][0]) * math.sin(-a_) + (c[1] - p_["pos"][1]) * math.cos(-a_)) < D_ / 2
                             and c[2] < H_ for c in cams)
                if inside:                        # every camera is in the room: close the fourth wall too
                    p_["walls"] = list(KIT.WALLS)
            elif p_.get("kind") == "plan" and p_.get("closed", True):
                if all(KIT.plan_inside(p_, c[0], c[1]) for c in cams):
                    p_["ceiling"] = True
    reset_camera_cache()
    os.makedirs(outdir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    except (AttributeError, TypeError):
        pass
    sc = bpy.context.scene
    fps, dur = int(spec["fps"]), float(spec["duration"])
    nfr = max(1, int(round(dur * fps)))
    sc.frame_start, sc.frame_end = 1, nfr
    sc.frame_step = max(1, int(os.environ.get("BLOCKING_FRAME_STEP", "1")))   # >1 only for a quick look while authoring
    sc.render.fps = fps
    sc.render.resolution_x, sc.render.resolution_y = spec["render"]["w"], spec["render"]["h"]
    sc.render.resolution_percentage = 100
    sc.render.engine = "BLENDER_WORKBENCH"
    try:
        sc.view_settings.view_transform = "Standard"   # the legend colours render as written, not tone-mapped
    except (TypeError, AttributeError):
        pass
    sh = sc.display.shading
    sh.light, sh.color_type = "STUDIO", "OBJECT"
    sh.show_shadows, sh.show_cavity = True, True
    for attr, val in (("cavity_type", "BOTH"), ("show_object_outline", True), ("use_world_space_lighting", True)):
        try:
            setattr(sh, attr, val)
        except (AttributeError, TypeError):
            pass
    light = spec.get("light", {})
    if light.get("from"):
        v = mathutils.Vector(light["from"]).normalized()
        try:
            sh.studiolight_rotate_z = math.atan2(v.y, v.x) - math.pi / 2
            sc.display.light_direction = (v.x, v.y, max(0.2, v.z))
        except (AttributeError, TypeError):
            pass
    world = bpy.data.worlds.new("w"); sc.world = world
    try:
        world.color = (0.55, 0.55, 0.57)
    except AttributeError:
        pass
    rgb = lambda c: c if isinstance(c, tuple) else COLORS.get(c, COLORS[NEUTRAL])
    KIT.MATERIAL_HOOK = LOOK.material_hook(look.get("palette", {}), COLORS) if concept else None
    try:
        # floor with a 1 m grid: scale and parallax read from it (a neutral grey, so it needs no legend line)
        outdoors = any(e.get("kind") in ENV.EXTERIORS for e in ENV._envs(spec))
        fl = spec.get("floor", {"size": [240, 240] if outdoors else [12, 12]})
        floor_mat = look.get("floor") if concept else None
        if concept and not floor_mat:
            tname = look.get("time") or LOOK.guess_time(spec)
            floor_mat = "cyc" if tname == "studio" else ("gravel" if outdoors else "wood_floor")
        KIT.mesh_object(bpy, "floor", [KIT.box((0, 0, -0.01), (fl["size"][0], fl["size"][1], 0.02))], rgb(NEUTRAL),
                        material=floor_mat)
        if not concept:
            gx, gy = min(fl["size"][0], 24), min(fl["size"][1], 24)
            grid = [KIT.box((i, 0, 0.001), (0.012, gy, 0.002)) for i in range(-int(gx / 2), int(gx / 2) + 1)]
            grid += [KIT.box((0, j, 0.001), (gx, 0.012, 0.002)) for j in range(-int(gy / 2), int(gy / 2) + 1)]
            KIT.mesh_object(bpy, "grid", grid, (0.5, 0.5, 0.5))
        return _build_rest(bpy, mathutils, spec, outdir, review_times, look, times, res, sc, sh, rgb, fps, dur, nfr)
    finally:
        KIT.MATERIAL_HOOK = None


def _build_rest(bpy, mathutils, spec, outdir, review_times, look, times, res, sc, sh, rgb, fps, dur, nfr):
    concept = look is not None
    def placed(p):
        return mathutils.Matrix.Translation((p["pos"][0], p["pos"][1], float(p.get("z", 0)))) @ \
            mathutils.Matrix.Rotation(math.radians(float(p.get("rot", 0))), 4, "Z")
    for p in all_pieces(spec):
        if p.get("model"):
            ob = KIT.import_model(bpy, p, rgb(p.get("color", NEUTRAL)), placed(p), keep_materials=concept)
        else:
            ob = KIT.build_piece(bpy, p, rgb(p.get("color", NEUTRAL)), dims)
        if p.get("spin"):                         # a turntable: degrees per second about its own centre
            ob.rotation_mode = "XYZ"
            for fr in (1, nfr):
                ob.rotation_euler = (0, 0, math.radians(float(p.get("rot", 0)) + float(p["spin"]) * (fr - 1) / fps))
                ob.keyframe_insert("rotation_euler", frame=fr)
    for v in spec.get("vehicles", []):
        w_, d_, h_ = DIMENSIONS.get(v.get("kind", "car"), (4.6, 1.85, 1.45))
        piece = {"id": v["id"], "kind": v.get("kind", "car"), "pos": [0, 0], "rot": 0, "size": [w_, d_, h_]}
        ob = KIT.build_piece(bpy, piece, rgb(v.get("color", NEUTRAL)), dims)
        ob.rotation_mode = "XYZ"
        for t in sorted(set([0.0, dur] + [round(i / fps, 4) for i in range(int(dur * fps) + 1)])):
            vs = vehicle_at(spec, v, t)
            fr = int(round(t * fps)) + 1
            ob.location = (vs["pos"][0], vs["pos"][1], 0.0); ob.keyframe_insert("location", frame=fr)
            ob.rotation_euler = (0, 0, math.radians(vs["heading"])); ob.keyframe_insert("rotation_euler", frame=fr)
    samples = sorted(set([0.0, dur] + [round(i * 2 / fps, 4) for i in range(int(dur * fps / 2) + 1)]))
    review_only = []
    me = sys.modules[__name__]
    for a in spec["actors"]:
        rig = RIG.Rig(me, spec, a)
        _, body, cone_ob = KIT.build_actor(bpy, rig, a, rgb(a["color"]), samples, fps)
        review_only.append(cone_ob)
        if concept:                                  # a clay mannequin with a hint of the actor's colour, matte
            soft = tuple(0.25 * c + 0.75 * g_ for c, g_ in zip(rgb(a["color"]), (0.62, 0.58, 0.54)))
            body.data.materials.append(KIT.MATERIAL_HOOK(bpy, "fabric", soft))
    for p in spec.get("props", []):
        w, d, h = dims(p)
        if p.get("model"):
            o = KIT.import_model(bpy, p, rgb(p.get("color", NEUTRAL)), mathutils.Matrix.Identity(4), keep_materials=concept,
                                 origin="centre")
        else:
            parts_ = p["_prims"] if p.get("_prims") else KIT.prop_parts(p.get("kind", "box"), w, d, h)
            o = KIT.mesh_object(bpy, p["id"], parts_, rgb(p.get("color", NEUTRAL)), material=p.get("material", "paint"))
        o.rotation_mode = "XYZ"
        if p.get("label_toward"):
            lab = KIT.mesh_object(bpy, p["id"] + "_label", [KIT.box((0, -d / 2 - 0.002, -h * 0.08), (w * 0.92, 0.004, h * 0.36))],
                                  rgb("white"), material="paint_white")
            lab.parent = o
        for t in samples:
            f = int(round(t * fps)) + 1
            pa = prop_at(spec, p, t)
            o.location = pa["pos"]; o.keyframe_insert("location", frame=f)
            if p.get("label_toward") == "camera":
                cam = camera_at(spec, t)
                phi = math.atan2(cam["pos"][1] - pa["pos"][1], cam["pos"][0] - pa["pos"][0])
                o.rotation_euler = (0, 0, phi + math.pi / 2)
            else:
                o.rotation_euler = (0, 0, math.radians(float(p.get("rot", 0))))
            o.keyframe_insert("rotation_euler", frame=f)
    # camera: keyed on every frame from camera_at — position, rotation (with the handheld roll) and lens
    cam_data = bpy.data.cameras.new("cam")
    cam_data.sensor_fit = "AUTO"; cam_data.sensor_width = SENSOR_MM
    cam_data.clip_start = 0.02
    cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
    cam.rotation_mode = "QUATERNION"
    prev_q = None
    for fr in range(1, nfr + 1):
        c = camera_at(spec, (fr - 1) / fps)
        fwd = mathutils.Vector(c["look_at"]) - mathutils.Vector(c["pos"])
        q = fwd.to_track_quat("-Z", "Y") @ mathutils.Quaternion((0, 0, 1), math.radians(c["roll_deg"]))
        if prev_q is not None and prev_q.dot(q) < 0:
            q.negate()                                   # keep the quaternion path short between frames
        prev_q = q
        cam.location = c["pos"]; cam.keyframe_insert("location", frame=fr)
        cam.rotation_quaternion = q; cam.keyframe_insert("rotation_quaternion", frame=fr)
        cam_data.lens = c["lens_mm"]; cam_data.keyframe_insert("lens", frame=fr)
        if c.get("fstop") and c.get("focus_m"):
            # depth of field for a rack or a shallow shot: Workbench renders it, so the reference shows which
            # plane is sharp
            cam_data.dof.use_dof = True
            cam_data.dof.focus_distance = c["focus_m"]; cam_data.dof.keyframe_insert("focus_distance", frame=fr)
            cam_data.dof.aperture_fstop = c["fstop"]; cam_data.dof.keyframe_insert("aperture_fstop", frame=fr)
            try:
                sh.use_dof = True
            except (AttributeError, TypeError):
                pass
    if concept:
        info = LOOK.setup(bpy, spec, look)
        if res:
            sc.render.resolution_percentage = int(round(100 * res / min(spec["render"]["w"], spec["render"]["h"])))
        out = []
        for t in times or [0.0]:
            fr = min(nfr, int(round(t * fps)) + 1)
            sc.frame_set(fr)
            path_ = os.path.join(outdir, f"{spec['shot']}.concept.{t:05.2f}s.png")
            sc.render.filepath = path_
            bpy.ops.render.render(write_still=True)
            out.append(path_)
        blend = os.path.join(outdir, f"{spec['shot']}.concept.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        return {"stills": out, "blend": blend, "look": info}
    frames_dir = os.path.join(outdir, "frames")
    review_dir = os.path.join(outdir, "review")
    for dd in (frames_dir, review_dir):
        shutil.rmtree(dd, ignore_errors=True); os.makedirs(dd)
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(frames_dir, "f_")
    bpy.ops.render.render(animation=True)                   # the clean reference: no facing cones
    for o in review_only:
        o.hide_render = False
    for t in review_times:                                   # the review frames: facing cones on
        fr = min(nfr, int(round(t * fps)) + 1)
        sc.frame_set(fr)
        sc.render.filepath = os.path.join(review_dir, f"r_{fr:04d}.png")
        bpy.ops.render.render(write_still=True)
    for o in review_only:
        o.hide_render = True
    blend = os.path.join(outdir, f"{spec['shot']}.blocking.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    return {"frames": frames_dir, "review": review_dir, "blend": blend, "nfr": nfr}


def sheet_times(spec: dict) -> list:
    spec = prepare(spec)
    dur = float(spec["duration"])
    fps = float(spec["fps"])
    ts = {0.0, dur} | {float(k["t"]) for k in spec["camera"]["keys"]} | {float(i) for i in range(1, int(dur) + 1)}
    for c in cuts_of(spec):
        ts |= {c, max(0.0, c - 1.0 / fps)}
    return sorted(t for t in ts if 0 <= t <= dur)


def encode_and_sheet(spec: dict, outdir: str, b: dict) -> dict:
    spec = prepare(spec)
    fps = int(spec["fps"])
    nfr = b["nfr"]
    mp4 = os.path.join(outdir, f"{spec['shot']}.blocking.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(b["frames"], "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", mp4], check=True)
    from PIL import Image, ImageDraw
    tiles = []
    for t in sheet_times(spec):
        fr = min(nfr, int(round(t * fps)) + 1)
        p = os.path.join(b["review"], f"r_{fr:04d}.png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB")
        im.thumbnail((270, 480))
        cam = camera_at(spec, t)
        sz = _size_of_cam(spec, cam) or ""
        lab = Image.new("RGB", (im.width, im.height + 34), (20, 20, 20))
        lab.paste(im, (0, 0))
        dr = ImageDraw.Draw(lab)
        cut = any(abs(t - c) < 0.5 / fps for c in cuts_of(spec))
        dr.text((6, im.height + 4), f"{spec['shot']} t={t:.2f}s {sz}{'  CUT' if cut else ''}"
                                    + (f"  shot {cam['shot']}" if cam.get("shot") else ""), fill=(240, 240, 240))
        dr.text((6, im.height + 18), f"{cam['lens_mm']:.0f}mm  cam {cam['pos'][2]:.2f} m  tilt {_tilt(cam):+.0f}°",
                fill=(200, 200, 200))
        tiles.append(lab)
    cols = min(6, len(tiles))
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * tiles[0].width, rows * tiles[0].height), (10, 10, 10))
    for i, t_ in enumerate(tiles):
        sheet.paste(t_, ((i % cols) * t_.width, (i // cols) * t_.height))
    sp = os.path.join(outdir, f"{spec['shot']}.blocking.sheet.png")
    sheet.save(sp)
    stills = {}
    picks = [("first", 1), ("last", nfr)] + [(f"cut-{c:g}s", min(nfr, int(round(c * fps)) + 1)) for c in cuts_of(spec)]
    for name, fr in picks:
        src = os.path.join(b["frames"], f"f_{fr:04d}.png")
        if os.path.exists(src):
            dst = os.path.join(outdir, f"{spec['shot']}.blocking.{name}.png")
            shutil.copyfile(src, dst); stills[name] = dst
    return {"mp4": mp4, "sheet": sp, "stills": stills, "pops": find_pops(spec, b["frames"], nfr)}


def find_pops(spec: dict, frames_dir: str, nfr: int) -> list:
    """Frames whose change from the previous frame is more than 3× the change around them (the two
    frames either side) — a prop teleporting, a limb flipping. A fast move is a RUN of large changes and
    is not a pop; a cut is meant to change everything and is skipped."""
    from PIL import Image, ImageChops, ImageStat
    fps = float(spec["fps"])
    cut_frames = {int(round(c * fps)) + 1 for c in cuts_of(spec)}
    prev, diffs = None, []
    for fr in range(1, nfr + 1):
        p = os.path.join(frames_dir, f"f_{fr:04d}.png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("L").resize((90, 160))
        if prev is not None:
            diffs.append((fr, ImageStat.Stat(ImageChops.difference(im, prev)).mean[0]))
        prev = im
    out = []
    for i, (f, d) in enumerate(diffs):
        if f in cut_frames:
            continue
        around = [diffs[j][1] for j in (i - 2, i - 1, i + 1, i + 2)
                  if 0 <= j < len(diffs) and diffs[j][0] not in cut_frames]
        if not around:
            continue
        local = sorted(around)[len(around) // 2]
        if d > max(3 * local, 1.5):
            cam_ = camera_at(spec, (f - 1) / fps) if spec["camera"].get("keys") else None
            if cam_ and cam_.get("in_whip"):
                continue                              # a whip pan is meant to blur the world past in a frame or two
            out.append({"frame": f, "t": round((f - 1) / fps, 3), "diff": round(d, 2), "around": round(local, 2)})
    return out


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def do_build(spec_path: str, outdir: str) -> int:
    if os.environ.get("BLOCKING_FRAME_STEP", "1") != "1":
        print("FAIL  BLOCKING_FRAME_STEP is set: that is a quick look for authoring (build() renders one frame in "
              "N); a build anyone approves renders every frame. Unset it and run again.")
        return 2
    raw = json.load(open(spec_path, encoding="utf-8"))
    F, W = check(raw)
    for x in W:
        print(f"WARN  {x}")
    for x in F:
        print(f"FAIL  {x}")
    if F:
        print("not built — fix the FAILs first")
        return 1
    try:
        import bpy  # noqa: F401
    except ImportError:
        print("FAIL  Blender is not importable here. `pip install bpy` into a Python that matches the wheel, or run "
              "inside Blender: blender -b --python blocking.py -- build <spec> -o <dir>")
        return 2
    spec = prepare(raw)
    os.makedirs(outdir, exist_ok=True)
    b = build(spec, outdir, sheet_times(spec))
    e = encode_and_sheet(spec, outdir, b)
    mp = draw_map(spec, os.path.join(outdir, f"{spec['shot']}.blocking.map.png"))
    reset_camera_cache()
    cams = camera_keys(spec)
    cj = os.path.join(outdir, f"{spec['shot']}.blocking.camera.json")
    json.dump(cams, open(cj, "w", encoding="utf-8"), indent=1, default=str)
    pt = os.path.join(outdir, f"{spec['shot']}.blocking.prompt.txt")
    open(pt, "w", encoding="utf-8").write(prompt_text(spec))
    shutil.rmtree(b["frames"], ignore_errors=True); shutil.rmtree(b["review"], ignore_errors=True)
    for pp in e["pops"]:
        print(f"WARN  frame {pp['frame']} (t={pp['t']} s) changes {pp['diff']} against {pp['around']} around it — "
              f"a pop: something jumps between two frames. Look at it before approving")
    files = [("spec", spec_path), ("mp4", e["mp4"]), ("sheet", e["sheet"]), ("map", mp), ("camera", cj),
             ("prompt", pt), ("blend", b["blend"])] + [(f"still:{k}", v) for k, v in e["stills"].items()]
    man = {"shot": spec["shot"], "spec_version": SPEC_VERSION, "model": spec.get("model"), "pops": e["pops"],
           "duration": spec["duration"], "fps": spec["fps"], "render": spec["render"], "aspect": spec.get("aspect"),
           "cuts": cuts_of(spec), "legend": spec["legend"], "assets": model_assets(spec),
           "files": {k: {"path": os.path.relpath(v, outdir), "sha256": sha(v)} for k, v in files}}
    mpath = os.path.join(outdir, f"{spec['shot']}.blocking.manifest.json")
    json.dump(man, open(mpath, "w", encoding="utf-8"), indent=1)
    print(f"built {spec['shot']}: {e['mp4']}\n  review sheet: {e['sheet']}\n  map: {mp}\n  prompt blocks: {pt}\n"
          f"  manifest: {mpath}")
    print("next: look at the sheet, the map and the MP4; revise the spec and rebuild until it is right (at most "
          "three rounds, keep the best); then `gate.py approve blocking:" + spec["shot"] +
          " --by <name> --quote \"...\" --artifact <manifest>`")
    return 0


def verify_manifest(path: str) -> list:
    """Problems with a built manifest: a file missing or changed since the build. [] when intact."""
    out = []
    try:
        man = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"cannot read {path}: {e}"]
    base = os.path.dirname(os.path.abspath(path))
    for k, v in (man.get("files") or {}).items():
        fp = os.path.normpath(os.path.join(base, v.get("path", "")))
        if not os.path.isfile(fp):
            out.append(f"{k}: {v.get('path')} is missing")
        elif sha(fp) != v.get("sha256"):
            out.append(f"{k}: {v.get('path')} changed after the build")
    if "mp4" not in (man.get("files") or {}):
        out.append("the manifest lists no mp4")
    return out


# ── test fixtures: the v3 library, short and plain — the selftest exercises the checks on them ─────────────
def _kitchen(pos, size, extra_openings=()):
    return {"id": "kitchen", "kind": "room", "pos": pos, "size": size, "walls": ["back", "left", "right"],
            "color": "darkgrey",
            "openings": [{"wall": "back", "kind": "window", "at": 1.3, "w": 1.2, "h": 1.0, "sill": 1.0},
                         {"wall": "left", "kind": "door", "at": 0.2, "w": 0.9, "h": 2.1, "open": 35}] + list(extra_openings)}


FIXTURES = {
    # two people at a kitchen island: a breathing MS that arcs to the camera side of the line as she lifts the
    # bottle to her chest, label to camera
    "counter-two-shot": {
        "shot": "S3", "fps": 24, "duration": 5.0, "aspect": "9:16", "render": {"w": 540, "h": 960},
        "model": "seedance_2_5",
        "set": [_kitchen([0, 0.4], [5.0, 2.2, 2.6]),
                {"id": "counter", "kind": "island", "pos": [0, 0.8], "size": [1.8, 0.6, 0.9], "color": "grey"},
                {"id": "fridge", "kind": "fridge", "pos": [-1.9, 1.1], "color": "grey"},
                {"id": "plant", "kind": "plant", "pos": [2.1, 1.2], "color": "green"}],
        "actors": [
            {"id": "A", "color": "red", "height": 1.65, "build": "slim",
             "keys": [{"t": 0, "pos": [-0.4, 0.3], "facing": -90, "look": "camera"},
                      {"t": 5, "pos": [-0.3, 0.3], "facing": "B", "look": "B"}]},
            {"id": "B", "color": "blue", "height": 1.80,
             "keys": [{"t": 0, "pos": [0.8, 0.0], "facing": "A"}, {"t": 5, "pos": [0.6, 0.0], "facing": "A"}]}],
        "props": [{"id": "bottle", "kind": "bottle", "color": "yellow", "on": "counter", "pos": [-0.05, 0.6],
                   "label_toward": "camera", "held": [{"by": "A.right", "from": 2.0, "to": 5.0, "at": "chest"}]}],
        "camera": {"lens": 35, "handheld": "breathing",
                   "shots": [{"t": [0, 5], "move": "arc_right", "on": "A", "height": "eye", "facing_ref": "live",
                              "from": {"size": "MS", "side": 0}, "to": {"size": "MS", "side": -30, "frame": ["bottle"]}}]},
        "line_of_action": ["A", "B"],
        "legend": {"red": "the presenter, a woman in her 50s", "blue": "her friend", "yellow": "the supplement bottle",
                   "white": "the bottle's label", "darkgrey": "the kitchen's walls, with a window and a door",
                   "green": "a potted plant"},
    },
    # two people seated across a café table: an over-the-shoulder two-shot, then a cut to a clean single on the
    # same side of the line
    "table-exchange": {
        "shot": "S5", "fps": 24, "duration": 6.0, "aspect": "9:16", "render": {"w": 540, "h": 960},
        "model": "seedance_2_5",
        "set": [{"id": "cafe", "kind": "room", "pos": [0.0, 0.6], "size": [5.0, 4.0, 2.8], "walls": ["back", "left", "right"],
                 "color": "darkgrey",
                 "openings": [{"wall": "right", "kind": "window", "at": 0.4, "w": 1.4, "h": 1.2, "sill": 0.9},
                              {"wall": "back", "kind": "door", "at": -1.2, "w": 0.9, "h": 2.1}]},
                {"id": "table", "kind": "table", "pos": [0, 0.6], "color": "brown"},
                {"id": "chair_a", "kind": "chair", "pos": [-0.85, 0.6], "rot": 90, "color": "grey"},
                {"id": "chair_b", "kind": "chair", "pos": [0.85, 0.6], "rot": -90, "color": "grey"},
                {"id": "lamp", "kind": "lamp", "pos": [2.1, 2.2], "color": "grey"}],
        "actors": [
            {"id": "A", "color": "red", "height": 1.65, "pose": "sit", "build": "slim",
             "keys": [{"t": 0, "pos": [-0.85, 0.6], "facing": 0, "look": "B"}, {"t": 6, "pos": [-0.85, 0.6], "facing": 0, "look": "B"}]},
            {"id": "B", "color": "blue", "height": 1.78, "pose": "sit",
             "keys": [{"t": 0, "pos": [0.85, 0.6], "facing": 180, "look": "A"}, {"t": 6, "pos": [0.85, 0.6], "facing": 180, "look": "A"}]}],
        "props": [{"id": "cup_a", "name": "Maria's cup", "kind": "mug", "color": "white", "on": "table", "pos": [-0.35, 0.5]},
                  {"id": "cup_b", "name": "the pharmacist's cup", "kind": "mug", "color": "white", "on": "table", "pos": [0.35, 0.7],
                   "held": [{"by": "B.right", "from": 3.5, "to": 6.0}]}],
        "camera": {"lens": 35, "handheld": "breathing",
                   "shots": [{"t": [0, 3], "move": "static", "pos": [-1.6, 0.0, 1.2], "look_at": [0.4, 0.75, 1.0],
                              "lens": 28, "frame": ["A", "B"]},
                             {"t": [3, 6], "move": "static", "on": "B", "size": "MCU", "height": "eye",
                              "from": {"side": 40}, "to": {"side": 35}}]},
        "line_of_action": ["A", "B"],
        "legend": {"red": "Maria, the customer", "blue": "the pharmacist", "brown": "the café table",
                   "white": "two coffee cups", "darkgrey": "the café's walls, with a window and a door"},
    },
    # a seated presenter: the camera rises and arcs round her; the shelf and the plant give the move parallax
    "orbit-reveal": {
        "shot": "S1", "fps": 24, "duration": 6.0, "aspect": "9:16", "render": {"w": 540, "h": 960},
        "model": "seedance_2_5",
        "set": [{"id": "studio", "kind": "room", "pos": [0, 0.6], "size": [4.5, 3.2, 2.7], "walls": ["back", "left", "right"],
                 "color": "white", "openings": [{"wall": "left", "kind": "window", "at": 0.5, "w": 1.2, "h": 1.3, "sill": 0.8}]},
                {"id": "stool", "kind": "stool", "pos": [0, 0.5], "color": "grey"},
                {"id": "shelf", "kind": "shelf", "pos": [0.9, 1.9], "color": "darkgrey"},
                {"id": "plant", "kind": "plant", "pos": [-1.0, 1.3], "color": "green"},
                {"id": "lamp", "kind": "lamp", "pos": [-1.6, 1.8], "color": "grey"}],
        "actors": [{"id": "A", "color": "red", "height": 1.68, "pose": "sit",
                    "keys": [{"t": 0, "pos": [0, 0.5], "facing": -90, "look": "camera"},
                             {"t": 6, "pos": [0, 0.5], "facing": -90, "look": "camera"}]}],
        "camera": {"lens": 35, "handheld": "breathing",
                   "shots": [{"t": [0, 6], "move": "orbit", "on": "A",
                              "from": {"size": "MS", "height": "chest", "side": -60},
                              "to": {"size": "MCU", "height": "eye", "side": 20}}]},
        "legend": {"red": "the presenter, a woman in her 40s", "darkgrey": "a bookshelf", "green": "a potted plant",
                   "white": "pale plaster walls, a window on the left"},
    },
    # an insert: hands lift the product off the counter; the 85 mm holds on it (the lift tilts it under 6°, which
    # reads as a hold); her face stays out
    "product-insert": {
        "shot": "S7", "fps": 24, "duration": 5.0, "aspect": "9:16", "render": {"w": 540, "h": 960},
        "model": "seedance_2_5",
        "set": [{"id": "kitchen", "kind": "room", "pos": [0, 0.9], "size": [4.0, 2.2, 2.6], "walls": ["back", "left", "right"],
                 "color": "darkgrey", "openings": [{"wall": "back", "kind": "window", "at": -1.0, "w": 1.0, "h": 1.0, "sill": 1.1}]},
                {"id": "counter", "kind": "counter", "pos": [0, 0.55], "color": "grey"}],
        "actors": [{"id": "A", "name": "the presenter", "color": "red", "height": 1.65, "face_out_of_frame": True,
                    "keys": [{"t": 0, "pos": [0, 1.0], "facing": -90}, {"t": 5, "pos": [0, 1.0], "facing": -90}]}],
        "props": [{"id": "bottle", "kind": "bottle", "color": "yellow", "on": "counter", "pos": [-0.15, 0.5],
                   "label_toward": "camera", "held": [{"by": "A.right", "from": 1.5, "to": 5.0, "at": "waist"}]}],
        "camera": {"lens": 85, "handheld": "breathing",
                   "shots": [{"t": [0, 5], "move": "static", "pos": [-0.1, -0.45, 0.95], "look_at": "bottle", "frame": ["bottle"]}]},
        "legend": {"red": "the presenter; her torso, hands and forearms are in frame, her face is not",
                   "yellow": "the supplement bottle", "white": "the bottle's label",
                   "darkgrey": "the kitchen's tiled walls, a window behind"},
    },
    # two people walk and talk down a corridor toward a camera that leads them backward, handheld
    "walk-and-talk": {
        "shot": "S9", "fps": 24, "duration": 6.0, "aspect": "9:16", "render": {"w": 540, "h": 960},
        "model": "seedance_2_5",
        "set": [{"id": "hall", "kind": "room", "pos": [0, 3.0], "size": [3.0, 8.0, 2.7], "walls": ["back", "left", "right"],
                 "color": "darkgrey",
                 "openings": [{"wall": "left", "kind": "door", "at": -1.0, "w": 0.9, "h": 2.1},
                              {"wall": "left", "kind": "door", "at": 2.0, "w": 0.9, "h": 2.1, "open": 60},
                              {"wall": "right", "kind": "window", "at": 0.5, "w": 1.6, "h": 1.2, "sill": 0.9}]},
                {"id": "runner", "kind": "rug", "pos": [0, 3.0], "size": [1.2, 6.0, 0.01], "color": "brown"}],
        "actors": [
            {"id": "A", "color": "red", "height": 1.66,
             "keys": [{"t": 0, "pos": [-0.35, 5.6], "facing": -90}, {"t": 3, "pos": [-0.35, 3.6], "facing": -90, "look": "B"},
                      {"t": 6, "pos": [-0.35, 1.6], "facing": -90, "look": "camera"}]},
            {"id": "B", "color": "blue", "height": 1.82, "build": "broad",
             "keys": [{"t": 0, "pos": [0.35, 5.6], "facing": -90, "look": "A"}, {"t": 6, "pos": [0.35, 1.6], "facing": -90, "look": "A"}]}],
        "camera": {"lens": 28, "handheld": "walking",
                   "shots": [{"t": [0, 6], "move": "lead", "look_at": ["A", "B"], "frame": ["A", "B"],
                              "from": {"pos": [0.0, 3.5, 1.55]}, "to": {"pos": [0.0, -0.5, 1.55]}}]},
        "line_of_action": ["A", "B"],
        "legend": {"red": "Ana, a nurse in her 30s", "blue": "the night-shift doctor",
                   "darkgrey": "the hospital corridor's walls, doors on the left, a window on the right",
                   "brown": "a long runner rug"},
    },
    # a crane reveal: from the mug on the coffee table up and back to the whole living room
    "crane-reveal": {
        "shot": "S11", "fps": 24, "duration": 6.0, "aspect": "9:16", "render": {"w": 540, "h": 960},
        "model": "seedance_2_5",
        "set": [{"id": "living", "kind": "room", "pos": [0, 1.0], "size": [5.0, 4.0, 2.7], "walls": ["back", "left", "right"],
                 "color": "beige",
                 "openings": [{"wall": "back", "kind": "window", "at": 1.4, "w": 1.4, "h": 1.3, "sill": 0.8},
                              {"wall": "left", "kind": "door", "at": -0.8, "w": 0.9, "h": 2.1}]},
                {"id": "sofa", "kind": "sofa", "pos": [0, 2.5], "color": "teal"},
                {"id": "coffee_table", "kind": "table", "pos": [0, 1.75], "size": [1.0, 0.6, 0.45], "color": "brown"},
                {"id": "rug", "kind": "rug", "pos": [0, 1.6], "color": "grey"},
                {"id": "lamp", "kind": "lamp", "pos": [1.6, 2.6], "color": "grey"},
                {"id": "tv", "kind": "tv", "pos": [-1.9, 1.2], "rot": -90, "color": "black"}],
        "actors": [{"id": "A", "color": "red", "height": 1.7, "pose": "sit",
                    "keys": [{"t": 0, "pos": [0, 2.45], "facing": -90, "look": "mug"}, {"t": 6, "pos": [0, 2.45], "facing": -90, "look": "camera"}]}],
        "props": [{"id": "mug", "kind": "mug", "color": "white", "on": "coffee_table", "pos": [0.2, 1.9],
                   "held": [{"by": "A.right", "from": 3.0, "to": 6.0, "at": "chest"}]}],
        "camera": {"handheld": "breathing",
                   "shots": [{"t": [0, 6], "move": "reveal",
                              "from": {"pos": [0.25, 1.05, 0.72], "look_at": "mug", "lens": 50},
                              "to": {"pos": [0.0, -0.8, 2.2], "look_at": [0.0, 1.9, 0.85], "lens": 24, "frame": ["A"]}}]},
        "legend": {"red": "Lena, a woman in her 30s", "teal": "a deep teal sofa", "brown": "the coffee table",
                   "white": "her coffee mug", "beige": "warm beige living-room walls, a window and a door",
                   "black": "a television on the side wall"},
    },
    # dialogue coverage: a wide two-shot, then matched singles from the same side of the line
    "dialogue-coverage": {
        "shot": "S13", "fps": 24, "duration": 7.5, "aspect": "9:16", "render": {"w": 540, "h": 960},
        "model": "seedance_2_5",
        "set": [{"id": "office", "kind": "room", "pos": [0, 1.2], "size": [5.0, 4.0, 2.7], "walls": ["back", "left", "right"],
                 "color": "darkgrey", "openings": [{"wall": "back", "kind": "window", "at": 0.0, "w": 2.0, "h": 1.3, "sill": 0.8}]},
                {"id": "desk", "kind": "desk", "pos": [1.4, 2.6], "color": "brown"},
                {"id": "shelf", "kind": "shelf", "pos": [-1.6, 2.95], "color": "grey"}],
        "actors": [
            {"id": "A", "color": "red", "height": 1.64, "keys": [{"t": 0, "pos": [-0.5, 1.2], "facing": "B", "look": "B"},
                                                               {"t": 7.5, "pos": [-0.5, 1.2], "facing": "B", "look": "B"}]},
            {"id": "B", "color": "blue", "height": 1.80, "keys": [{"t": 0, "pos": [0.5, 1.2], "facing": "A", "look": "A"},
                                                                {"t": 7.5, "pos": [0.5, 1.2], "facing": "A", "look": "A"}]}],
        "camera": {"lens": 35, "handheld": "breathing",
                   "shots": [{"t": [0, 2.5], "move": "static", "pos": [0.0, -1.6, 1.5], "look_at": ["A", "B"], "lens": 28,
                              "frame": ["A", "B"]},
                             {"t": [2.5, 5.0], "move": "push_in", "on": "A", "height": "eye",
                              "from": {"size": "MS", "side": -40}, "to": {"size": "MCU", "side": -40}},
                             {"t": [5.0, 7.5], "move": "static", "on": "B", "size": "MCU", "height": "eye", "side": 40}]},
        "line_of_action": ["A", "B"],
        "legend": {"red": "the founder", "blue": "the investor", "brown": "a desk",
                   "darkgrey": "the office's walls, a wide window behind them"},
    },
}
EXAMPLE = FIXTURES["counter-two-shot"]


# ── the preset library: bold, long, layered starting points — every one checks clean (selftest) ────────────
# Each is 10–14 s, joins moves into one continuous camera or cuts them on purpose, and names what the shot is
# for. Start from the nearest one (`blocking.py example --preset <name>`), then re-block it for the brief.
_V = {"fps": 24, "aspect": "9:16", "render": {"w": 540, "h": 960}, "model": "seedance_2_5"}

PRESETS = {
    # 12 s · a host walks in, the camera rises off the floor as she arrives at the island, keeps moving round to
    # the camera side as she lifts the product, then cuts to an orbit pinned on the bottle in her hand
    "kitchen-hero": dict(_V, **{
        "shot": "K1", "duration": 12.0,
        "env": {"kind": "kitchen", "seed": 2},
        "look": {"time": "interior_day", "palette": {"wood_paint": "cream"}},
        "actors": [{"id": "A", "name": "the host", "color": "red", "height": 1.68, "build": "slim",
                    "keys": [{"t": 0, "pos": [-2.3, 0.0], "facing": -30},
                             {"t": 1.6, "pos": [-1.2, -0.75], "facing": 0},
                             {"t": 3.4, "pos": [0.0, -0.75], "facing": -90, "look": "camera"},
                             {"t": 4.1, "pos": [0.0, -0.75], "facing": -90, "look": "camera"},
                             {"t": 4.7, "pos": [0.0, -0.75], "facing": 80, "look": "bottle"},
                             {"t": 5.2, "pos": [0.0, -0.75], "facing": 80, "look": "bottle"},
                             {"t": 6.1, "pos": [0.0, -0.75], "facing": -95, "look": "camera"},
                             {"t": 12.0, "pos": [0.0, -0.75], "facing": -95, "look": "camera"}]}],
        "props": [{"id": "bottle", "kind": "bottle", "color": "yellow", "on": "env1.island4", "pos": [0.1, -0.2],
                   "label_toward": "camera", "held": [{"by": "A.right", "from": 4.9, "to": 12.0, "at": "chest"}]}],
        "camera": {"shots": [
            {"t": [0, 4.2], "move": "worms_eye_rise", "on": "A", "side": 30, "dutch": 10},
            {"t": [4.2, 8.0], "move": "arc_left", "on": "A", "size": "MWS", "lens": 40, "side": 30, "degrees": 50, "cut": False,
             "rig": "steadicam", "place": [0.3, 0.42], "to": {"frame": ["bottle"]}},
            {"t": [8.0, 12.0], "move": "pinned_detail_orbital", "detail": "bottle", "radius": 1.0, "from_angle": -125,
             "degrees": 70, "height": 0.3, "lens": 35}]},
        "legend": {"red": "the host, a woman in her 40s", "yellow": "the supplement bottle", "white": "the bottle's label"},
    }),

    # 12 s · café coverage that refuses to sit still: mirrored dirty over-the-shoulders, then the news lands —
    # a pivot whip from him to her reaction, and a dolly zoom as she takes it in
    "cafe-coverage": dict(_V, **{
        "shot": "C1", "duration": 12.0,
        "env": {"kind": "cafe", "seed": 1},
        "look": {"time": "interior_day"},
        "actors": [{"id": "A", "name": "Maria", "color": "red", "height": 1.65, "pose": "sit", "build": "slim",
                    "keys": [{"t": 0, "pos": [-3.02, -0.6], "facing": 0, "look": "B"},
                             {"t": 12, "pos": [-3.02, -0.6], "facing": 0, "look": "B"}]},
                   {"id": "B", "name": "the pharmacist", "color": "blue", "height": 1.8, "pose": "sit",
                    "keys": [{"t": 0, "pos": [-1.78, -0.6], "facing": 180, "look": "A"},
                             {"t": 12, "pos": [-1.78, -0.6], "facing": 180, "look": "A"}]}],
        "props": [{"id": "cup", "name": "Maria's cup", "kind": "mug", "color": "white", "on": "env1.round_table4",
                   "pos": [-2.55, -0.65]}],
        "line_of_action": ["A", "B"],
        "camera": {"shots": [
            {"t": [0, 3.0], "move": "split_ots", "over": "B", "on": "A", "lens": 65},
            {"t": [3.0, 6.0], "move": "split_ots", "over": "A", "on": "B", "lens": 65, "shoulder": "left"},
            {"t": [6.0, 8.5], "move": "pivot_whip", "a": "B", "b": "A", "start": 0.9, "offset": -0.35},
            {"t": [8.5, 12.0], "move": "dolly_zoom", "on": "A", "size": "MCU", "side": 75, "direction": "out", "ratio": 1.8,
             "hold": [0.4, 0.6]}]},
        "legend": {"red": "Maria, 60s", "blue": "the pharmacist, 30s", "white": "Maria's coffee cup"},
    }),
    # 14 s · a walk-and-talk oner down a corridor: the camera leads them backward, eases round to an angle as they
    # slow, and settles into a living two-shot when they stop at the door; the operator leans in on the stop
    "hallway-oner": dict(_V, **{
        "shot": "H1", "duration": 14.0,
        "env": {"kind": "hallway", "seed": 1},
        "set": [{"id": "end_wall", "kind": "wall", "pos": [0.0, -4.56], "size": [2.6, 0.12, 2.7], "color": "darkgrey"}],
        "look": {"time": "interior_day"},
        "actors": [{"id": "A", "name": "the doctor", "color": "red", "height": 1.7,
                    "keys": [{"t": 0, "pos": [-0.25, -3.2], "facing": 90}, {"t": 8.5, "pos": [-0.25, 1.1], "facing": 90},
                             {"t": 9.4, "pos": [-0.25, 1.1], "facing": 0, "look": "B"},
                             {"t": 14, "pos": [-0.25, 1.1], "facing": 0, "look": "B"}]},
                   {"id": "B", "name": "the patient", "color": "blue", "height": 1.78,
                    "keys": [{"t": 0, "pos": [0.27, -3.9], "facing": 90}, {"t": 8.9, "pos": [0.27, 0.9], "facing": 90},
                             {"t": 9.7, "pos": [0.27, 0.9], "facing": 160, "look": "A"},
                             {"t": 14, "pos": [0.27, 0.9], "facing": 160, "look": "A"}]}],
        "camera": {"shots": [
            {"t": [0, 8.0], "move": "lead", "on": "A", "size": "WS", "side": -14, "lens": 22, "frame": ["A", "B"],
             "height": "chest", "place": [0.3, -0.2]},
            {"t": [8.0, 14.0], "move": "drift", "pos": [0.2, 3.3, 1.5], "look_at": ["A", "B"], "lens": 32, "cut": False,
             "blend": 1.6,
             "rig": "steadicam", "react": [{"at": "A.stops", "kind": "lean_in"}]}]},
        "legend": {"red": "the doctor", "blue": "the patient"},
    }),

    # 12 s · a runner on a city pavement: the camera starts on her feet at kerb height and rises with her
    # stride, then hands over to a drone that climbs and pulls back down the street ahead of her, at a shallow
    # angle, until the street is the subject
    "street-runner": dict(_V, **{
        "shot": "R1", "duration": 12.0,
        "env": {"kind": "street", "seed": 4, "dress": "busy", "length": 70},
        "look": {"time": "golden"},
        "actors": [{"id": "A", "name": "the runner", "color": "red", "height": 1.72, "build": "slim", "ramp": 0,
                    "keys": [{"t": 0, "pos": [-14, 5.7], "facing": 0}, {"t": 12, "pos": [8, 5.7], "facing": 0}]}],
        "vehicles": [{"id": "taxi", "color": "yellow", "keys": [{"t": 0, "pos": [30, -1.75], "heading": 180},
                                                                {"t": 12, "pos": [-26, -1.75], "heading": 180}]}],
        "camera": {"shots": [
            {"t": [0, 5.0], "move": "worms_eye_rise", "on": "A", "side": -35, "dutch": 12, "to_dist": 1.3},
            {"t": [5.0, 12.0], "move": "drone_reveal", "on": "A", "side": -20, "from_dist": 1.6, "from_height": 1.5,
             "altitude": 8, "to_dist": 24, "cut": False, "blend": 1.6, "occlusion_ok": True}]},
        "legend": {"red": "the runner, 30s, running kit", "yellow": "a taxi"},
    }),
    # 12 s · a night drive in four set-ups: tracking alongside the driver's door, the dash looking back at her,
    # outside her window, and an FPV skimming the asphalt head-on at the car
    "car-night": dict(_V, **{
        "shot": "D1", "duration": 12.0,
        "env": {"kind": "road", "seed": 1},
        "look": {"time": "night"},
        "vehicles": [{"id": "car", "name": "the family car", "color": "white", "ramp": 0, "keys": [{"t": 0, "pos": [-60, -1.75], "heading": 0},
                                                              {"t": 12, "pos": [84, -1.75], "heading": 0}]}],
        "actors": [{"id": "A", "name": "the driver", "color": "red", "in": "car", "seat": "driver"},
                   {"id": "B", "name": "her son", "color": "blue", "in": "car", "seat": "rear_right", "height": 1.6}],
        "camera": {"shots": [
            {"t": [0, 3.5], "move": "car_side_track", "on": "A", "offset": [0.2, 3.0, -0.05], "lens": 45},
            {"t": [3.5, 6.5], "move": "car_dash", "on": "car"},
            {"t": [6.5, 9.0], "move": "car_window", "on": "car", "lens": 32, "offset": [0.55, 1.3, 1.15]},
            {"t": [9.0, 12.0], "move": "asphalt_skim", "on": "car", "speed": 8}]},
        "legend": {"white": "the family car", "red": "the driver, a mother in her 40s", "blue": "her teenage son"},
    }),
    # 10 s · a hero product shot on a plinth: a robot arm hits three marks (label ECU, high three-quarter,
    # level medium), then the label stays pinned while the world wraps round it
    "product-robo": dict(_V, **{
        "shot": "P1", "duration": 10.0,
        "env": {"kind": "podium", "seed": 1},
        "look": {"time": "studio"},
        "props": [{"id": "bottle", "kind": "bottle", "color": "yellow", "on": "env1.podium4", "pos": [0.0, -0.5],
                   "label_toward": "camera", "material": "product",
                   "shape": {"parts": [{"lathe": [[0, 0], [0.034, 0], [0.036, 0.004], [0.036, 0.13], [0.03, 0.15],
                                                   [0.016, 0.168], [0.015, 0.19], [0, 0.19]], "segments": 48},
                                       {"lathe": [[0, 0.188], [0.018, 0.188], [0.018, 0.215], [0, 0.215]], "m": "plastic_dark"}]}}],
        "actors": [],
        "camera": {"shots": [
            {"t": [0, 5.0], "move": "motion_control", "rig": "robo",
             "stops": [{"on": "bottle", "size": "ECU", "side": 18, "hold": 0.9},
                       {"on": "bottle", "size": "CU", "side": -35, "height": "high", "hold": 0.9},
                       {"on": "bottle", "size": "MS", "side": 0, "hold": 1.4}]},
            {"t": [5.0, 10.0], "move": "pinned_detail_orbital", "detail": "bottle", "from_angle": -125, "degrees": 70,
             "radius": 0.55, "cut": False, "blend": 1.4}]},
        "legend": {"yellow": "the product bottle", "white": "its label"},
    }),

    # 12 s · a park run seen by a second flyer: an FPV drops out of the sky into a chase at her shoulder, banks
    # with her through the bend in the path, then overtakes and turns to lead her
    "park-fpv": dict(_V, **{
        "shot": "F1", "duration": 12.0,
        "env": {"kind": "park", "seed": 1},
        "look": {"time": "golden"},
        "actors": [{"id": "A", "name": "the runner", "color": "red", "height": 1.7, "build": "slim", "ramp": 0,
                    "keys": [{"t": 0, "pos": [0.3, -14.0], "facing": 90}, {"t": 6.0, "pos": [0.3, -1.0], "facing": 90},
                             {"t": 8.0, "pos": [2.4, 4.6], "facing": 20}, {"t": 12.0, "pos": [11.0, 6.2], "facing": 0}]}],
        "camera": {"shots": [
            {"t": [0, 7.0], "move": "fpv_dive", "on": "A", "offset": [-2.2, -0.9, -0.15]},
            {"t": [7.0, 12.0], "move": "lead", "on": "A", "rig": "fpv", "size": "MWS", "side": -35, "height": "eye",
             "cut": False, "blend": 2.0}]},
        "legend": {"red": "the runner, 20s, bright running kit"},
    }),
    # 10 s · a rooftop at golden hour: one spiral round her at the parapet (orbit, rise and push in one move,
    # ending on a low hero angle), then a drone lets her go, pulling up and away until the skyline holds her
    "rooftop-spiral": dict(_V, **{
        "shot": "T1", "duration": 10.0,
        "env": {"kind": "rooftop", "seed": 1},
        "look": {"time": "golden"},
        "actors": [{"id": "A", "name": "the founder", "color": "red", "height": 1.74,
                    "keys": [{"t": 0, "pos": [1.0, 4.9], "facing": 90}, {"t": 10, "pos": [1.0, 4.9], "facing": 90}]}],
        "camera": {"shots": [
            {"t": [0, 6.0], "move": "spiral", "on": "A", "side": -160, "degrees": 110, "to": {"height": "chest"}},
            {"t": [6.0, 10.0], "move": "drone_reveal", "on": "A", "side": -50, "from_dist": 1.8, "from_height": 1.7,
             "altitude": 5, "to_dist": 15, "cut": False, "blend": 1.2}]},
        "legend": {"red": "the founder, 40s, dark coat"},
    }),
}



# ── selftest (no Blender needed) ─────────────────────────────────────────────────────────────────────────
# ── the move library under test: one scene every named move can run in, and what each move must do ─────
def move_scene() -> dict:
    """A test location: a runner crossing, a friend standing, a mug on a table, a post near the lens line,
    a car driving past with a driver in it, a flat (floor plan) with a door."""
    return {"shot": "M", "fps": 24, "duration": 6.0, "aspect": "9:16", "render": {"w": 540, "h": 960}, "model": "seedance_2_5",
            "set": [{"id": "post", "kind": "box", "pos": [0.3, -1.6], "size": [0.12, 0.12, 2.0]},
                    {"id": "table", "kind": "table", "pos": [1.6, 1.0]},
                    {"id": "flat", "kind": "plan", "pos": [-3.0, 4.0], "points": [[0, 0], [6, 0], [6, 4], [0, 4]],
                     "openings": [{"segment": 0, "at": 3.0, "w": 1.0, "kind": "door", "open": 80}]}],
            "props": [{"id": "mug", "kind": "mug", "pos": [1.6, 1.0], "z": 0.75, "color": "blue"}],
            "vehicles": [{"id": "car1", "kind": "car", "color": "yellow",
                          "keys": [{"t": 0, "pos": [-30, -8]}, {"t": 6, "pos": [40, -8]}]}],
            "actors": [{"id": "A", "name": "the runner", "color": "red", "height": 1.75,
                        "keys": [{"t": 0, "pos": [-2.0, 0.0], "facing": 0}, {"t": 6, "pos": [2.0, 0.0], "facing": 0}]},
                       {"id": "B", "name": "the friend", "color": "green", "height": 1.65,
                        "keys": [{"t": 0, "pos": [0.9, 1.4], "facing": -120}, {"t": 6, "pos": [0.9, 1.4], "facing": -120}]},
                       {"id": "C", "name": "the cook", "color": "orange", "height": 1.7,
                        "keys": [{"t": 0, "pos": [0.0, 6.0], "facing": -90}, {"t": 6, "pos": [0.0, 6.0], "facing": -90}]},
                       {"id": "D", "name": "the driver", "color": "purple", "in": "car1", "seat": "driver"}],
            "camera": {"shots": []},
            "legend": {"red": "the runner", "green": "the friend", "orange": "the cook", "purple": "the driver",
                       "yellow": "the car", "blue": "the mug"}}


MOVE_PARAMS = {   # what each move needs beyond `on` (the runner) in move_scene
    "pivot_whip": {"a": "A", "b": "B"}, "rack_focus": {"focus_from": "A", "focus_to": "B"},
    "deep_to_near_rack": {"far": "A", "near": "mug"}, "foreground_wipe": {"past": "post"},
    "push_through": {"on": "C", "through": {"room": "flat", "segment": 0}}, "pinned_detail_orbital": {"detail": "mug"},
    "ots": {"over": "B"}, "split_ots": {"over": "B"},
    "motion_control": {"stops": [{"on": "B", "size": "CU", "hold": 1.2}, {"on": "mug", "size": "CU", "hold": 1.0},
                                 {"on": "A", "size": "MS", "hold": 1.5}]},
    "robo_snap": {"stops": [{"on": "B", "size": "CU", "hold": 1.2}, {"on": "A", "size": "MS", "hold": 1.5}]},
    **{m: {"on": "car1"} for m in ("car_chase", "car_lead", "car_side_track", "car_hood", "car_dash", "car_passenger",
                                   "car_rear", "car_window", "car_wheel", "asphalt_skim")},
}


def _run_move(name: str, extra: dict | None = None, scene: dict | None = None) -> tuple:
    s = scene or move_scene()
    sh = {"t": [0, float(s["duration"])], "move": name, "on": "A", "size": "MS"}
    sh.update(MOVE_PARAMS.get(name, {}))
    sh.update(extra or {})
    s["camera"]["shots"] = [sh]
    p = prepare(s)
    reset_camera_cache()
    fr = int(round(float(s["duration"]) * float(s["fps"])))
    return p, [camera_at(p, i / float(s["fps"])) for i in range(fr + 1)]


def _yaw(c):
    return math.degrees(math.atan2(c["look_at"][1] - c["pos"][1], c["look_at"][0] - c["pos"][0]))


def selftest_moves() -> str:
    """Every named move compiles and renders; the signature moves do what their names promise."""
    fps = 24.0
    for name in CAM.LIBRARY:
        p, cs = _run_move(name)
        assert not p.get("_shot_errors"), (name, p.get("_shot_errors"))
        assert all(all(math.isfinite(v) for v in c["pos"] + c["look_at"]) and 6 <= c["lens_mm"] <= 400 for c in cs), name
    # dolly zoom: the subject holds its size while the lens changes by a third or more
    p, cs = _run_move("dolly_zoom", {"on": "B"})
    ext = [2 * math.dist(c["pos"], point_of(p, "B", i / fps)) * math.tan(math.radians(c["vfov_deg"]) / 2)
           for i, c in enumerate(cs)]
    lens = [c["lens_mm"] for c in cs]
    assert max(lens) / min(lens) > 1.3 and max(ext) / min(ext) < 1.1, (min(lens), max(lens), min(ext), max(ext))
    # pivot whip: planted on the spot, a swing faster than 150°/s, settled on A before and on B after
    p, cs = _run_move("pivot_whip")
    travel = max(math.dist(c["pos"], cs[0]["pos"]) for c in cs)
    rate = max(abs(ang_diff(_yaw(a), _yaw(b))) * fps for a, b in zip(cs, cs[1:]))
    toB = lambda c: abs(ang_diff(_yaw(c), math.degrees(math.atan2(point_of(p, "B", 6)[1] - c["pos"][1],
                                                                    point_of(p, "B", 6)[0] - c["pos"][0]))))
    assert travel < 0.3 and rate > 150 and toB(cs[-1]) < 8, (travel, rate, toB(cs[-1]))
    # rack focus: sharp on A at the start, on B at the end
    sc = move_scene(); sc["actors"][0]["keys"][1]["pos"] = [-2.0, 0.0]     # A holds; B stands deep behind A
    sc["actors"][1]["keys"] = [{"t": 0, "pos": [-4.6, 0.7], "facing": 0}, {"t": 6, "pos": [-4.6, 0.7], "facing": 0}]
    p, cs = _run_move("rack_focus", scene=sc)
    assert not [x for x in check(p)[1] if x.startswith("focus on")], check(p)[1]
    dA, dB = math.dist(cs[0]["pos"], point_of(p, "A", 0)), math.dist(cs[-1]["pos"], point_of(p, "B", 6))
    assert abs(cs[0]["focus_m"] - dA) < 0.15 * dA and abs(cs[-1]["focus_m"] - dB) < 0.15 * dB, (cs[0]["focus_m"], dA, cs[-1]["focus_m"], dB)
    p2, _ = _run_move("rack_focus")                                     # the friend behind the lens: a warning
    assert [x for x in check(p2)[1] if x.startswith("focus on B")], check(p2)[1]
    # push through: the lens crosses the doorway's plane inside the opening, and the check finds no wall in the lens
    p, cs = _run_move("push_through")
    door = next(q for q in all_pieces(p) if q["kind"] == "door")
    cross = [c for a, c in zip(cs, cs[1:]) if (a["pos"][1] - door["pos"][1]) * (c["pos"][1] - door["pos"][1]) <= 0]
    assert cross and abs(cross[0]["pos"][0] - door["pos"][0]) < door["size"][0] / 2 - 0.1, cross[:1]
    sp = copy.deepcopy(move_scene()); sp["camera"]["shots"] = [dict({"t": [0, 6], "move": "push_through", "size": "MS"},
                                                                     **MOVE_PARAMS["push_through"])]
    assert not [x for x in check(sp)[0] if "wall" in x or "lens" in x], check(sp)[0]
    # fpv banks into a turn: up leans toward the centre (roll > 0 turning left, < 0 turning right)
    for sign in (1, -1):
        sc = move_scene()
        sc["actors"][0]["keys"] = [{"t": 0, "pos": [0, 0], "facing": 0}, {"t": 2, "pos": [8, 0], "facing": 0},
                                   {"t": 4, "pos": [12, sign * 4], "facing": sign * 90},
                                   {"t": 6, "pos": [12, sign * 12], "facing": sign * 90}]
        p, cs = _run_move("fpv_chase", scene=sc)
        mid = [c["roll_deg"] for c in cs[60:100]]
        assert sign * max(mid, key=abs) > 3, (sign, min(mid), max(mid))
    # a handheld operator overshoots a hard stop and settles; the robot arm does not overshoot
    def overshoot(rig):
        p, cs = _run_move("motion_control", {"rig": rig, "stops": [{"on": "B", "size": "CU", "hold": 2.0},
                                                                     {"on": "A", "size": "CU", "hold": 3.0}]})
        ys = [_yaw(c) for c in cs]
        final, start = ys[-1], ys[0]
        over = max(sign_ * ang_diff(final, y) for y in ys[48:] for sign_ in [1 if ang_diff(start, final) > 0 else -1])
        return over
    oh, orb = overshoot("handheld"), overshoot("robo")
    assert oh > 0.5 and orb < 0.2, (oh, orb)
    # snorricam: bolted to the runner — the lens keeps its distance from the chest while they cross 4 m
    p, cs = _run_move("snorricam")
    dd = [math.dist(c["pos"], point_of(p, "A", i / fps)) for i, c in enumerate(cs)]
    assert max(dd) - min(dd) < 0.06, (min(dd), max(dd))
    # car rigs ride the car: the dash camera stays put in the car's own frame while it covers 70 m
    p, cs = _run_move("car_dash")
    car = p["vehicles"][0]
    loc = []
    for i, c in enumerate(cs):
        vs = vehicle_at(p, car, i / fps)
        h_ = math.radians(vs["heading"])
        dx, dy = c["pos"][0] - vs["pos"][0], c["pos"][1] - vs["pos"][1]
        loc.append((dx * math.cos(h_) + dy * math.sin(h_), -dx * math.sin(h_) + dy * math.cos(h_), c["pos"][2]))
    spread = max(math.dist(a, loc[0]) for a in loc)
    assert spread < 0.08, spread
    # aerial: the table's speed, turns and rates come out of the defaults, a cap refuses and a range warns
    sc = move_scene(); sc["actors"][0]["keys"][1]["pos"] = [-2.0, 0.0]      # the runner holds for these
    def aer(name, extra=None):
        s_ = copy.deepcopy(sc)
        s_["camera"]["shots"] = [dict({"t": [0, 6], "move": name, "on": "A"}, **(extra or {}))]
        return prepare(s_), aerial_measure(prepare(s_), s_["camera"]["shots"][0]), check(s_)
    _, m, (f_, w_) = aer("drone_orbit")
    assert 1.3 <= m["speed_mps"] <= 2.2 and 15 <= m["radius_m"] <= 46 and not [x for x in f_ + w_ if "move table" in x or "turns" in x], (m, f_, w_)
    _, m, (f_, w_) = aer("drone_orbit", {"radius": 6, "degrees": 720})
    assert [x for x in f_ if "turns round A" in x], (m, f_)                 # two orbits: the cap refuses
    _, m, (f_, w_) = aer("drone_orbit", {"speed": 5.0})
    assert not [x for x in f_ if "turns" in x] and [x for x in w_ if "flies 5" in x or "flies 4.9" in x], (m, w_)
    _, m, _x = aer("helix", {"secs_per_turn": 10.0})
    assert 8 <= m["secs_per_turn"] <= 12 and m["turns"] <= 3, m
    _, m, _x = aer("hover_pan")
    assert 7.2 <= m["deg_per_s"] <= 12.0 and m["speed_mps"] < 0.05, m
    # the bee eases into each dash and brakes out of it: the speed rises for longer than it falls
    p, cs = _run_move("bee_path", scene=copy.deepcopy(sc))
    v = [math.dist(a["base_pos"], b["base_pos"]) * fps for a, b in zip(cs, cs[1:])]
    pk = [i for i in range(2, len(v) - 2) if v[i] == max(v[i - 2:i + 3]) and v[i] > 0.5]
    rise_fall = []
    for i in pk:
        lo_ = i
        while lo_ > 0 and v[lo_ - 1] < v[lo_]:
            lo_ -= 1
        hi_ = i
        while hi_ < len(v) - 1 and v[hi_ + 1] < v[hi_]:
            hi_ += 1
        rise_fall.append((i - lo_, hi_ - i))
    assert rise_fall and sum(1 for r_, f2 in rise_fall if r_ > f2) >= 0.6 * len(rise_fall), rise_fall
    assert CAM.bee_profile(0.5) < 0.5 and abs(CAM.bee_profile(1.0) - 1.0) < 1e-9     # slow start, fast finish
    # the mosquito's view rarely points where it travels
    p, cs = _run_move("mosquito_path", scene=copy.deepcopy(sc))
    off = []
    for a, b in zip(cs[::4], cs[4::4]):
        d = [b["base_pos"][j] - a["base_pos"][j] for j in range(2)]
        if math.hypot(*d) > 0.02:
            off.append(abs(ang_diff(math.degrees(math.atan2(d[1], d[0])), _yaw(b))))
    assert off and sum(off) / len(off) > 45, sum(off) / max(len(off), 1)
    return (f"{len(CAM.LIBRARY)} named moves compile and render; dolly zoom holds size, pivot whip snaps, rack focus "
            f"lands, push-through threads the door, FPV banks into the turn, handheld overshoots where the robot "
            f"does not, the snorricam and car rigs ride their carrier; a drone orbit flies the table's speed and "
            f"radius, two turns refuse and a fast orbit warns, a helix turns every 8-12 s, a hover pan sweeps "
            f"7-12°/s, a bee eases in and brakes out, a mosquito looks away from where it goes")


def selftest_precise() -> str:
    """Floor plans, shapes and imported models: what the checks accept and refuse."""
    base = {"shot": "G", "fps": 24, "duration": 4.0, "aspect": "9:16", "render": {"w": 540, "h": 960},
            "model": "seedance_2_5", "legend": {"red": "the host"},
            "set": [{"id": "flat", "kind": "plan", "points": [[-3, -2], [3, -2], [3, 2], [-3, 2]],
                     "openings": [{"segment": 0, "at": 3.0, "w": 1.0, "kind": "door"}]},
                    {"id": "counter", "kind": "counter", "pos": [0, 1.0],
                     "shape": {"extrude": {"outline": [[-1, -0.3], [1, -0.3], [1, 0.3], [0.4, 0.3], [0.4, 0.9], [-1, 0.9]],
                                           "height": 0.9}}}],
            "actors": [{"id": "A", "color": "red", "keys": [{"t": 0, "pos": [0.8, 1.6], "facing": -90},
                                                            {"t": 4, "pos": [0.8, 1.6], "facing": -90}]}],
            "camera": {"keys": [{"t": 0, "on": "A", "size": "MS"}]}}
    f_, w_ = check(copy.deepcopy(base))
    assert not [x for x in f_ if "counter" in x], f_                      # standing in the L's notch is free floor
    inside = copy.deepcopy(base); inside["actors"][0]["keys"] = [dict(k, pos=[-0.5, 1.6]) for k in base["actors"][0]["keys"]]
    assert [x for x in check(inside)[0] if "counter" in x], check(inside)[0]   # inside the L's arm is not
    assert prepare(copy.deepcopy(base))["set"][1]["size"] == [2.0, 1.8, 0.9]  # the size comes from the shape
    bad = copy.deepcopy(base); bad["set"][0]["openings"][0]["at"] = 5.8
    assert [x for x in check(bad)[0] if "does not fit segment" in x], check(bad)[0]
    mdl = copy.deepcopy(base)
    mdl["props"] = [{"id": "kettle", "kind": "box", "pos": [0.5, 1.0], "z": 0.9, "color": "red",
                     "model": {"file": "/nonexistent/kettle.glb", "licence": "CC-BY-NC", "source": "https://example.org"}}]
    f2 = check(mdl)[0]
    assert [x for x in f2 if "not on this machine" in x] and [x for x in f2 if "needs `size`" in x] \
        and [x for x in f2 if "not cleared for client work" in x], f2
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "kettle.glb"); open(fp, "wb").write(b"glTF")
        mdl["props"][0]["model"].update(file=fp, licence="CC-BY", author="someone"); mdl["props"][0]["size"] = [0.2, 0.2, 0.2]
        f3, w3 = check(mdl)
        assert not [x for x in f3 if "kettle" in x] and [x for x in w3 if "credits" in x], (f3, w3)
        assert model_assets(prepare(mdl))[0]["licence"] == "CC-BY" and model_assets(prepare(mdl))[0]["sha256"]
    return ("floor plans, shapes and models: real outlines collide, sizes come from the geometry, openings must fit, "
            "models need a size, a file and a cleared licence")


def selftest() -> int:
    KIT.selftest(DIMENSIONS)
    RIG.selftest()
    me = sys.modules[__name__]
    for name, ps in list(FIXTURES.items()) + list(PRESETS.items()):   # every fixture and every preset is clean
        f_, w_ = check(copy.deepcopy(ps))
        assert not f_ and not [x for x in w_ if "rates file" not in x], (name, f_, w_)
    s = copy.deepcopy(EXAMPLE)
    # camera maths: 35 mm on a 9:16 frame — the 36 mm sensor spans the long (vertical) side
    vf, hf = vfov_hfov(35, 540, 960)
    assert 54 < vf < 55 and 32 < hf < 33, (vf, hf)
    assert abs(vfov_hfov(26, 540, 960)[0] - 69.4) < 0.2
    # the shot plan compiles to keys and cuts
    tx = prepare(copy.deepcopy(FIXTURES["table-exchange"]))
    assert tx["camera"]["cuts"] == [3.0] and len(tx["camera"]["keys"]) == 4, tx["camera"]
    gap = copy.deepcopy(FIXTURES["table-exchange"]); gap["camera"]["shots"][1]["t"] = [3.5, 6]
    assert any("tile" in x for x in check(gap)[0])
    # composition: eyes at 36 % of the height on a vertical frame; MCU distance from the lens maths
    mcu = copy.deepcopy(s); mcu["camera"] = {"lens": 35, "keys": [{"t": 0, "on": "A", "size": "MCU", "height": "eye"}]}
    mcu = prepare(mcu); reset_camera_cache()
    c0 = camera_at(mcu, 0.0)
    sx, sy, _ = project(c0, point_of(mcu, "A", 0.0), 540, 960)
    assert abs((1 - sy) / 2 - 0.36) < 0.02 and abs(sx) < 0.05, (sx, sy)
    assert abs(math.dist(c0["pos"], c0["target"]) - 0.275 / math.tan(math.radians(vf) / 2)) < 0.12, c0
    # the moves ease in and out, and pass through intermediate keys without stopping
    push = copy.deepcopy(s)
    push["camera"] = {"lens": 35, "keys": [{"t": 0, "on": "A", "size": "MS", "side": 0},
                                           {"t": 2.5, "on": "A", "size": "MCU", "side": -20},
                                           {"t": 5, "on": "A", "size": "MCU", "side": -40}]}
    push = prepare(push); reset_camera_cache()
    v = lambda t: math.dist(camera_ideal(push, t)["pos"], camera_ideal(push, t + 0.01)["pos"]) / 0.01
    assert v(0.0) < 0.06 and v(4.99) < 0.06 and v(2.5) > 0.03, (v(0.0), v(2.5), v(4.99))
    assert math.dist(camera_ideal(push, 2.5)["pos"], camera_keys(push)[1]["pos"]) < 1e-3
    # the operator: the rendered camera chases the plan through the rig's spring — close, never ahead
    lag = math.dist(camera_at(push, 2.5)["pos"], camera_keys(push)[1]["pos"])
    assert 0 < lag < 0.06, lag
    # the handheld breathes: deterministic, small, never still
    hb = prepare(copy.deepcopy(s)); reset_camera_cache()
    p1, p2 = camera_at(hb, 1.0)["pos"], camera_at(hb, 1.0)["pos"]
    assert p1 == p2
    still = copy.deepcopy(s); still["camera"]["handheld"] = "none"; still = prepare(still); reset_camera_cache()
    d_hh = math.dist(camera_at(still, 1.0)["pos"], p1)
    assert 0 < d_hh < 0.02, d_hh
    # an orbit keeps its distance instead of cutting the chord; a cut holds, then jumps
    o = prepare(copy.deepcopy(FIXTURES["orbit-reveal"])); reset_camera_cache()
    r = lambda c: math.dist(c["pos"][:2], (0, 0.5))
    a0, mid, a1 = camera_ideal(o, 0.0), camera_ideal(o, 3.0), camera_ideal(o, 6.0)
    assert min(r(a0), r(a1)) - 0.05 <= r(mid) <= max(r(a0), r(a1)) + 0.05, (r(a0), r(mid), r(a1))
    tx = prepare(copy.deepcopy(FIXTURES["table-exchange"])); reset_camera_cache()
    before, after = camera_at(tx, 2.95), camera_at(tx, 3.0)
    assert math.dist(before["pos"], after["pos"]) > 0.5 and before["subject"] != after["subject"]
    # the legend both ways; a label plate is a colour too
    s2 = copy.deepcopy(s); del s2["legend"]["yellow"]
    assert any("not in the legend" in x for x in check(s2)[0])
    s2b = copy.deepcopy(s); del s2b["legend"]["white"]
    assert any("bottle label" in x for x in check(s2b)[0])
    s3 = copy.deepcopy(s); s3["legend"]["purple"] = "a chair"
    assert any("used by nothing" in x for x in check(s3)[0])
    # schema FAILs
    bad = [("height", "shoulder", "height 'shoulder'"), ("handheld", "shaky", "handheld 'shaky'"),
           ("move", "spin", "move 'spin'"), ("place", "top", "place 'top'")]
    for fld, val, msg in bad:
        sb = copy.deepcopy(s); sb["camera"]["shots"][0][fld] = val
        assert any(msg in x for x in check(sb)[0]), (fld, check(sb)[0])
    sb_ = copy.deepcopy(s); sb_["actors"][0]["body"] = "clay"
    assert any("body 'clay'" in x for x in check(sb_)[0])
    sl = copy.deepcopy(FIXTURES["product-insert"]); sl["camera"]["shots"][0]["look_at"] = "jar"
    assert any("look_at 'jar'" in x for x in check(sl)[0])
    sk = copy.deepcopy(s); sk["camera"] = {"keys": [{"t": 0, "on": "A"}, {"t": 0, "on": "A", "size": "CU"}]}
    assert any("same time" in x for x in check(sk)[0])
    sc_ = copy.deepcopy(s); sc_["camera"] = {"keys": [{"t": 0, "on": "A"}, {"t": 5, "on": "A"}], "cuts": [2.5]}
    assert any("no camera key at that time" in x for x in check(sc_)[0])
    # reach and seats WARN
    sr = copy.deepcopy(s); sr["props"][0]["pos"] = [0.8, 0.6]
    assert any("picks it up" in x for x in check(sr)[1]), check(sr)
    sn = copy.deepcopy(s); sn["actors"][0]["keys"][0]["pose"] = "sit"
    assert any("no seat under" in x for x in check(sn)[1]), check(sn)
    # bodies FAIL: two in one place, inside the island, inside a wall; a door opening is walkable
    s4 = copy.deepcopy(s); s4["actors"][1]["keys"][1]["pos"] = [-0.3, 0.25]
    assert any("interpenetrate" in x for x in check(s4)[0])
    s5 = copy.deepcopy(s); s5["actors"][0]["keys"][1]["pos"] = [0.0, 0.8]
    assert any("inside counter" in x for x in check(s5)[0])
    wall = copy.deepcopy(s); wall["actors"][1]["keys"] = [{"t": 0, "pos": [-3.0, -0.4], "facing": 0}, {"t": 5, "pos": [-2.0, -0.4], "facing": 0}]
    assert any("inside kitchen.left" in x for x in check(wall)[0]), check(wall)[0]
    door = copy.deepcopy(s); door["actors"][1]["keys"] = [{"t": 0, "pos": [-3.0, 0.6], "facing": 0}, {"t": 5, "pos": [-1.6, 0.6], "facing": 0}]
    assert not any("inside kitchen" in x for x in check(door)[0]), check(door)[0]
    # the lens FAILs inside furniture (unless camera_through) and inside a person
    s7 = copy.deepcopy(s); s7["camera"] = {"keys": [{"t": 0, "pos": [0, 0.8, 0.5], "look_at": "A"}]}
    assert any("passes inside counter" in x for x in check(s7)[0])
    s7["set"][1]["camera_through"] = True
    assert not any("passes inside counter" in x for x in check(s7)[0])
    s7b = copy.deepcopy(s); s7b["camera"] = {"keys": [{"t": 0, "pos": [0.8, 0.0, 1.2], "look_at": "A"}]}
    assert any("passes through B" in x for x in check(s7b)[0])
    # the line at a cut WARNs; a continuous move across it does not
    s8 = copy.deepcopy(s); s8["camera"] = {"keys": [{"t": 0, "on": "A", "size": "MS"}, {"t": 2.5, "pos": [0.2, 1.3, 1.5], "look_at": "A"}]}
    s8["set"] = [x for x in s8["set"] if x["id"] != "counter"]; s8["props"] = []
    for c_ in ("yellow", "white"):
        s8["legend"].pop(c_)
    assert not any("crosses the line" in x for x in check(s8)[1]), check(s8)
    s8["camera"]["keys"].insert(1, {"t": 2.458, "on": "A", "size": "MS"}); s8["camera"]["cuts"] = [2.5]
    assert any("crosses the line" in x for x in check(s8)[1]), check(s8)
    s8["camera"]["cross_line"] = True
    assert not any("crosses the line" in x for x in check(s8)[1])
    # the duration must fit the model's measured range (Seedance 2.5's row starts at 4 s)
    rng = model_range("seedance_2_5")
    rng = rng if isinstance(rng, tuple) else None
    if rng:
        s9 = copy.deepcopy(FIXTURES["orbit-reveal"]); s9["duration"] = 3.0
        s9["actors"][0]["keys"][-1]["t"] = 3.0; s9["camera"]["shots"][0]["t"] = [0, 3.0]
        assert any("outside seedance_2_5" in x for x in check(s9)[0]) == (3.0 < rng[0]), (rng, check(s9))
        s10 = copy.deepcopy(s); s10["model"] = "wan2_7"
        assert any("no rate row" in x for x in check(s10)[0])
    # framing WARNs: the subject out of frame on a locked camera (a follow keeps it), a prop at the lens,
    # a prop outside the safe area, a hands-only presenter's chin, the eyes outside the band
    s13 = copy.deepcopy(s); s13["actors"][0]["keys"][1]["pos"] = [-2.0, 0.3]; s13["props"] = []
    for c_ in ("yellow", "white"):
        s13["legend"].pop(c_)
    s13["camera"] = {"keys": [{"t": 0, "pos": [-0.4, -0.6, 1.5], "look_at": "A"}]}
    assert not any("out of frame" in x for x in check(s13)[1]), check(s13)        # pans to follow A
    s13["camera"] = {"keys": [{"t": 0, "pos": [-0.4, -0.6, 1.5], "look_at": [-0.4, 0.3, 1.5], "frame": ["A"]}]}
    assert any("out of frame" in x for x in check(s13)[1]), check(s13)
    sa = copy.deepcopy(s); sa["camera"]["shots"][0]["to"] = {"size": "MCU", "side": -30, "frame": ["bottle"]}
    sa["props"][0]["held"][0]["at"] = "face"
    assert any("bottle passes" in x and "lens" in x for x in check(sa)[1]), check(sa)
    sm = copy.deepcopy(s); sm["camera"]["shots"][0]["to"] = {"size": "MCU", "side": -70, "frame": ["bottle"]}
    assert any("bottle is outside the safe area" in x for x in check(sm)[1]), check(sm)
    sp = copy.deepcopy(FIXTURES["product-insert"]); sp["camera"]["lens"] = 50; sp["props"][0]["held"][0]["at"] = "chest"
    assert any("face_out_of_frame" in x for x in check(sp)[1]), check(sp)
    se = copy.deepcopy(s); se["camera"]["shots"][0]["from"]["place"] = [0, -0.8]
    assert any("eyes sit at" in x for x in check(se)[1]), check(se)
    # the camera's own motion: a whip pan and a dead stop WARN; marked or eased, they do not
    wp = copy.deepcopy(FIXTURES["dialogue-coverage"])
    wp["camera"] = {"lens": 35, "keys": [{"t": 0, "pos": [0, -1.6, 1.5], "look_at": "A", "ease": "linear", "rig": "locked"},
                                         {"t": 0.3, "pos": [0, -1.6, 1.5], "look_at": "B", "ease": "linear", "rig": "locked"},
                                         {"t": 7.5, "pos": [0, -1.6, 1.5], "look_at": "B", "rig": "locked"}]}
    assert any("°/s" in x for x in check(wp)[1]), check(wp)
    for k in wp["camera"]["keys"][:2]:
        k["whip"] = True
    assert not any("°/s" in x for x in check(wp)[1]), check(wp)
    jl = copy.deepcopy(FIXTURES["dialogue-coverage"])
    # (a rig with no give — car_mount — so the plan's own jolt reaches the frame; a dolly would absorb it)
    jl["camera"] = {"lens": 35, "keys": [{"t": 0, "pos": [0, -2.0, 1.5], "look_at": [0, 1.2, 1.4], "ease": "linear", "rig": "car_mount"},
                                         {"t": 2.0, "pos": [0, -1.0, 1.5], "look_at": [0, 1.2, 1.4], "ease": "linear", "rig": "car_mount"}]}
    assert any("jolts" in x for x in check(jl)[1]), check(jl)
    for k in jl["camera"]["keys"]:
        k.pop("ease")
    assert not any("jolts" in x for x in check(jl)[1]), check(jl)
    jd = copy.deepcopy(jl)
    for k in jd["camera"]["keys"]:
        k["rig"], k["ease"] = "dolly", "linear"
    assert not any("jolts" in x for x in check(jd)[1]), check(jd)       # the dolly's spring takes the start
    # across a cut: under 30° and under two sizes on one subject is a jump cut
    jc = copy.deepcopy(FIXTURES["dialogue-coverage"])
    jc["camera"]["shots"][2] = {"t": [5.0, 7.5], "move": "static", "on": "A", "size": "MCU", "height": "eye", "side": -30}
    assert any("jump cut" in x for x in check(jc)[1]), check(jc)
    jc["camera"]["shots"][2]["side"] = 25
    assert not any("jump cut" in x for x in check(jc)[1]), check(jc)
    # screen direction flips when a cut puts the camera on the other side of walkers
    sd = copy.deepcopy(FIXTURES["walk-and-talk"])
    for a in sd["actors"]:
        a["keys"] = [{"t": 0, "pos": [-0.8, 3.0 + (0.4 if a["id"] == "B" else 0.0)], "facing": 0},
                     {"t": 6, "pos": [0.8, 3.0 + (0.4 if a["id"] == "B" else 0.0)], "facing": 0}]
    sd["camera"] = {"lens": 28, "shots": [{"t": [0, 3], "move": "static", "pos": [0, 0.6, 1.5], "look_at": ["A", "B"]},
                                          {"t": [3, 6], "move": "static", "pos": [0.3, 6.2, 1.5], "look_at": ["A", "B"]}],
                    "cross_line": True}
    sd.pop("line_of_action")
    assert any("screen direction flips" in x for x in check(sd)[1]), check(sd)
    # occlusion: a wall between the lens and the subject WARNs, unless the key says it is a wipe
    oc = copy.deepcopy(s); oc["set"].append({"id": "screen", "kind": "box", "pos": [-0.4, -0.25], "size": [0.6, 0.05, 2.0], "color": "grey"})
    assert any("hidden behind screen" in x for x in check(oc)[1]), check(oc)
    oc["camera"]["shots"][0]["occlusion_ok"] = True
    assert not any("hidden behind screen" in x for x in check(oc)[1])
    # a shot's declared move must be what the camera does
    mv = copy.deepcopy(FIXTURES["dialogue-coverage"]); mv["camera"]["shots"][1]["move"] = "pull_back"
    assert any("shot 2 declares 'pull_back'" in x for x in check(mv)[1]), check(mv)
    # an empty background WARNs
    tv = copy.deepcopy(FIXTURES["table-exchange"]); tv["set"] = [x for x in tv["set"] if x["kind"] != "room"]
    tv["legend"].pop("darkgrey")
    assert any("empty void" in x for x in check(tv)[1]), check(tv)
    # two props in one hand WARN
    s12 = copy.deepcopy(s); s12["props"].append({"id": "phone", "kind": "phone", "color": "yellow", "pos": [-0.2, 0.6],
                                                 "on": "counter", "held": [{"by": "A.right", "from": 1.0, "to": 3.0}]})
    assert any("holds bottle and phone" in x or "holds phone and bottle" in x for x in check(s12)[1]), check(s12)
    # the rig: bone lengths hold, joints move smoothly, feet plant while walking, a sit puts the hips on the seat
    for name in ("walk-and-talk", "counter-two-shot", "crane-reveal"):
        ps = prepare(copy.deepcopy(FIXTURES[name])); reset_camera_cache()
        for a in ps["actors"]:
            rig = RIG.Rig(me, ps, a)
            prev, lens_ = None, None
            planted = {"L": 0, "R": 0}
            n = int(float(ps["duration"]) * 24)
            for i in range(n + 1):
                j = rig.joints(i / 24)
                ua = math.dist(j["shoulder_L"], j["elbow_L"]); th = math.dist(j["hip_R"], j["knee_R"])
                if lens_ is None:
                    lens_ = (ua, th)
                assert abs(ua - lens_[0]) < 1e-3 and abs(th - lens_[1]) < 1e-3, (name, a["id"], i, ua, th)
                if prev is not None:
                    for jn in ("pelvis", "head_top", "wrist_L", "wrist_R", "ankle_L", "ankle_R", "knee_L", "elbow_R"):
                        step = math.dist(prev[jn], j[jn])      # a swinging foot peaks near 4× walking pace
                        assert step < (0.17 if jn.startswith("ankle") else 0.12), (name, a["id"], jn, i / 24, step)
                    for f_ in "LR":                      # a planted foot: its toe does not slide
                        if math.dist(prev[f"toe_{f_}"], j[f"toe_{f_}"]) < 0.002 and j[f"toe_{f_}"][2] < 0.03:
                            planted[f_] += 1
                prev = j
            if name == "walk-and-talk":
                assert planted["L"] > n * 0.3 and planted["R"] > n * 0.3, planted
    # a quick-look frame step can never become an approvable build
    os.environ["BLOCKING_FRAME_STEP"] = "24"
    try:
        assert do_build(os.devnull, tempfile.mkdtemp()) == 2
    finally:
        os.environ.pop("BLOCKING_FRAME_STEP", None)
    # a held prop sits beside the palm, not under it (the label stays clear)
    cs = prepare(copy.deepcopy(FIXTURES["counter-two-shot"])); reset_camera_cache()
    jh = RIG.Rig(me, cs, cs["actors"][0]).joints(4.0)
    bp = prop_at(cs, cs["props"][0], 4.0)["pos"]
    assert math.dist(jh["palm_R"], bp) > 0.035 + 0.015, (jh["palm_R"], bp)
    cp_ = camera_at(cs, 4.0)["pos"]                     # its label faces the lens, so the hand is behind it
    assert math.dist(jh["palm_R"], cp_) > math.dist(bp, cp_), (jh["palm_R"], bp, cp_)
    tx = prepare(copy.deepcopy(FIXTURES["table-exchange"])); reset_camera_cache()
    jA = RIG.Rig(me, tx, tx["actors"][0]).joints(1.0)
    assert abs(jA["pelvis"][2] - (0.45 + 0.09)) < 0.02 and jA["knee_L"][0] > jA["hip_L"][0] + 0.2, (jA["pelvis"], jA["knee_L"])
    # the head turns toward what it looks at, within the neck's range
    jB = RIG.Rig(me, tx, tx["actors"][1]).joints(1.0)
    assert jB["head_fwd"][0] < -0.9, jB["head_fwd"]
    # the prompt blocks are computed from the geometry and agree with it
    d = describe(copy.deepcopy(s))
    assert set(d["blocks"]) == {"BLOCKING", "LEGEND", "PRECEDENCE", "CAMERA", "MOTION", "SOUND"}
    assert "MS on the presenter" in d["stages"][0] and "arcs" in d["stages"][0] and "camera at eye height" in d["stages"][0], d["stages"]
    assert "breathing" in d["stages"][0] and "(arc right)" in d["stages"][0], d["stages"]
    assert any("picks up the supplement bottle with the right hand at 2 s" in e for e in d["events"]), d["events"]
    dt_ = describe(copy.deepcopy(FIXTURES["table-exchange"]))
    assert len(dt_["stages"]) == 2 and "1 hard cut" in dt_["blocks"]["BLOCKING"], dt_["stages"]
    assert "two-shot of Maria and the pharmacist" in dt_["stages"][0], dt_["stages"]
    dw = describe(copy.deepcopy(FIXTURES["walk-and-talk"]))
    assert "leads" in dw["stages"][0] and "walking with them" in dw["stages"][0], dw["stages"]
    dc = describe(copy.deepcopy(FIXTURES["crane-reveal"]))
    assert "rises" in dc["stages"][0] and "zooms" in dc["stages"][0], dc["stages"]
    assert "placeholder" not in prompt_text(copy.deepcopy(s)).lower()   # prompt_lint FAILs that word
    # the map draws without Blender, and a manifest is verified file by file
    try:
        import PIL  # noqa: F401
        with tempfile.TemporaryDirectory() as td:
            for name in ("counter-two-shot", "walk-and-talk"):
                out = draw_map(copy.deepcopy(FIXTURES[name]), os.path.join(td, f"{name}.png"))
                from PIL import Image
                assert Image.open(out).size[0] > 400
    except ImportError:
        print("  (Pillow missing — map not exercised)")
    with tempfile.TemporaryDirectory() as td:
        f1 = os.path.join(td, "S3.blocking.mp4"); open(f1, "wb").write(b"x")
        mp = os.path.join(td, "S3.blocking.manifest.json")
        json.dump({"files": {"mp4": {"path": "S3.blocking.mp4", "sha256": sha(f1)}}}, open(mp, "w"))
        assert verify_manifest(mp) == []
        open(f1, "wb").write(b"y")
        assert any("changed" in x for x in verify_manifest(mp))
    try:
        from PIL import Image, ImageDraw
        with tempfile.TemporaryDirectory() as td:
            xs = [20 + 6 * i for i in range(12)] + [200] + [206 + 6 * i for i in range(11)]   # jump at frame 13
            xs[5:9] = [50, 90, 130, 170]                                                       # a fast run, no jump
            for i, x in enumerate(xs, 1):
                im = Image.new("RGB", (540, 960), (128, 128, 128))
                ImageDraw.Draw(im).rectangle([x, 400, x + 120, 520], fill=(220, 40, 40))
                im.save(os.path.join(td, f"f_{i:04d}.png"))
            pops = find_pops({"fps": 24, "camera": {"keys": []}}, td, len(xs))
            assert [p["frame"] for p in pops] == [13], pops
    except ImportError:
        pass
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "S3.blocking.json")
        json.dump(s, open(p, "w"))
        assert main(["check", p]) == 0
        json.dump(s4, open(p, "w"))
        assert main(["check", p]) == 1
    # v2.46, the back-off: a continuous hand-over eased in position from A's front to a spot behind her swings wide
    # (without it the path passed 0.02 m from her); two framings orbiting A already swing round and get no waypoint
    bo = copy.deepcopy(PRESETS["cafe-coverage"]); bo["duration"] = 6.0; bo.pop("line_of_action", None)
    bA = next(a for a in bo["actors"] if a["id"] == "A")
    for second, want_wp in (({"pos": [-4.0, -0.6, 1.2], "look_at": "A"}, True), ({"on": "A", "size": "MS", "side": 180}, False)):
        sp = copy.deepcopy(bo)
        sp["camera"] = {"shots": [{"t": [0, 3.0], "move": "static", "on": "A", "size": "MS", "side": 0, "lens": 35},
                                  dict({"t": [3.0, 6.0], "move": "static", "lens": 35, "cut": False, "blend": 2.0}, **second)]}
        ks_, _, er_, _ = compile_shots(sp)
        _CAM.clear()
        sp["camera"] = {"keys": ks_}
        gA = actor_at(sp, bA, 3.0)["pos"]
        near = min(math.dist(camera_at(sp, 3.0 + 2.0 * i / 80)["pos"][:2], gA[:2]) for i in range(81))
        assert not er_ and any(k.get("backoff") for k in ks_) == want_wp and near > 0.5, (second, near, er_)
    _CAM.clear()
    mv = selftest_moves() + "; " + selftest_precise()
    print(f"selftest OK — {mv}; {len(FIXTURES)} fixtures and {len(PRESETS)} presets clean; shot plans compile and tile; the back-off on a wide hand-over; composition puts the eyes at "
          f"36 %; moves ease in and out and pass through their keys; the handheld breathes; orbits and cuts; legend, "
          f"schema, reach, seats, bodies in furniture and walls (doors walkable), the lens in furniture and in a "
          f"person, the line at a cut, the model's range, framing, the lens, the safe area, hands-only, the eye band, "
          f"whip pans, jolts, jump cuts, screen direction, occlusion, declared moves, void, two props in one hand; "
          f"the rig keeps its bone lengths, moves smoothly, plants its feet, sits on the seat, turns its head and grips a prop without covering its label; "
          f"the computed prompt; the map; manifests; pops")
    return 0


def do_concept(spec_path: str, outdir: str, times: str | None, res: int | None, tname: str | None) -> int:
    """Concept stills: the blocked scene lit and coloured (blocking_look.py), plus a contact sheet."""
    raw = json.load(open(spec_path, encoding="utf-8"))
    F, W = check(raw)
    for x in F:
        print(f"FAIL  {x}")
    if F:
        return 1
    spec = prepare(raw)
    look = dict(spec.get("look", {}))
    if tname:
        look["time"] = tname
    if times:
        ts = [float(x) for x in times.split(",")]
    else:
        dur = float(spec["duration"])
        ts = sorted({0.0, round(dur / 2, 2), round(dur - 1.0 / float(spec["fps"]), 2)} | {round(c, 2) for c in cuts_of(spec)})
    os.makedirs(outdir, exist_ok=True)
    b = build(spec, outdir, [], look=look, times=ts, res=res)
    try:
        from PIL import Image, ImageDraw
        ims = [Image.open(p_) for p_ in b["stills"]]
        w_, h_ = ims[0].size
        sheet = Image.new("RGB", (w_ * len(ims), h_ + 28), (16, 16, 16))
        d_ = ImageDraw.Draw(sheet)
        for i, (im, t) in enumerate(zip(ims, ts)):
            sheet.paste(im, (i * w_, 0))
            d_.text((i * w_ + 6, h_ + 8), f"{spec['shot']} t={t:.2f}s · concept · {b['look']['time']}", fill=(220, 220, 220))
        sp_ = os.path.join(outdir, f"{spec['shot']}.concept.sheet.png")
        sheet.save(sp_)
        print(f"concept sheet: {sp_}")
    except ImportError:
        pass
    assets = model_assets(spec)
    if assets:
        ap_ = os.path.join(outdir, f"{spec['shot']}.concept.assets.json")
        json.dump(assets, open(ap_, "w", encoding="utf-8"), indent=1)
        print(f"assets and licences: {ap_}")
    for p_ in b["stills"]:
        print(f"  {p_}")
    print(f"look: {b['look']['time']}, {b['look']['practicals']} practicals, haze {b['look']['haze']:g} — these are concept "
          f"frames for judging the place: not the blocking reference, not approved by the blocking gate")
    return 0


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["check", "camera", "map", "prompt", "build", "concept", "example", "verify",
                                               "moves", "envs"])
    ap.add_argument("spec", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--preset", default="kitchen-hero", choices=sorted(PRESETS))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--times", help="concept: seconds, comma-separated (default: start, the middle, the cuts, the end)")
    ap.add_argument("--res", type=int, help="concept: the short side in pixels (default: the spec's render size)")
    ap.add_argument("--time", help="concept: time of day, overriding the spec's look (blocking_look.TIMES)")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "moves":
        for n_, (fn, rig, words, why) in CAM.LIBRARY.items():
            print(f"  {n_:22s} {rig:16s} {why}")
        return 0
    if a.cmd == "envs":
        print(ENV.kinds_text()); return 0
    if a.cmd == "example":
        txt = json.dumps(PRESETS[a.preset], indent=1)
        dest = a.out or a.spec
        if dest:
            open(dest, "w", encoding="utf-8").write(txt + "\n"); print(dest)
        else:
            print(txt)
        return 0
    if not a.cmd or not a.spec:
        ap.print_help(); return 2
    if a.cmd == "verify":
        probs = verify_manifest(a.spec)
        for x in probs:
            print(f"FAIL  {x}")
        print("manifest intact" if not probs else f"{len(probs)} problem(s)")
        return 1 if probs else 0
    try:
        raw = json.load(open(a.spec, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL  cannot read {a.spec}: {e}"); return 2
    if a.cmd == "build":
        return do_build(a.spec, a.out or os.path.join(os.path.dirname(os.path.abspath(a.spec)), "_render"))
    if a.cmd == "concept":
        return do_concept(a.spec, a.out or os.path.join(os.path.dirname(os.path.abspath(a.spec)), "_concept"),
                          a.times, a.res, a.time)
    F, W = check(raw)
    if a.cmd == "check":
        for x in W:
            print(f"WARN  {x}")
        for x in F:
            print(f"FAIL  {x}")
        print(f"{raw.get('shot')}: {len(F)} fail · {len(W)} warn")
        return 1 if F else 0
    if F:
        for x in F:
            print(f"FAIL  {x}")
        return 1
    spec = prepare(raw)
    reset_camera_cache()
    if a.cmd == "camera":
        dur, fps = float(spec["duration"]), float(spec["fps"])
        bounds = [0.0] + cuts_of(spec) + [dur]
        for s0, s1 in zip(bounds, bounds[1:]):
            e = s1 - (1.0 / fps if s1 < dur else 0.0)
            c0, c1 = camera_at(spec, s0), camera_at(spec, e)
            c0["t"] = s0
            vmax = max(math.dist(camera_at(spec, s0 + i * (e - s0) / 40)["pos"], camera_at(spec, s0 + (i + 1) * (e - s0) / 40)["pos"])
                       / ((e - s0) / 40) for i in range(40)) if e > s0 else 0.0
            print(f"{s0:5.2f}–{s1:5.2f}s  shot {c0.get('shot') or '-'}  {_size_of_cam(spec, c0) or 'insert':>6} → "
                  f"{_size_of_cam(spec, c1) or 'insert':<6} lens {c0['lens_mm']:.0f}→{c1['lens_mm']:.0f} mm  "
                  f"hFOV {c0['hfov_deg']:.0f}°  {_height_tilt(spec, c0)}  moves: "
                  f"{', '.join(camera_motion(spec, s0, e)) or 'locked off'}  top speed {vmax:.2f} m/s  "
                  f"handheld {c0['key'].get('handheld')}")
        return 0
    if a.cmd == "map":
        out = a.out or os.path.splitext(a.spec)[0] + ".map.png"
        print(draw_map(spec, out)); return 0
    if a.cmd == "prompt":
        txt = prompt_text(spec)
        if a.out:
            open(a.out, "w", encoding="utf-8").write(txt); print(a.out)
        else:
            print(txt)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
