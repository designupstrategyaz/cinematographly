#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""blocking_env.py — environments a shot can be blocked in and concept-rendered in (references/blocking.md §3c).

`"env": {"kind": "street", ...}` in a spec expands into ordinary set pieces before anything else runs, so
`check` collides bodies and lenses with a kerb or a parked car exactly as it does with a table. The same
pieces render twice: as the flat-colour blocking (Workbench) and as a lit concept frame (blocking_look.py),
where every part carries a material.

  python3 blocking_env.py --selftest
  python3 blocking_env.py --kinds          # every environment and what it builds

Four families, all built from parts in code (no downloads):
  interiors  living_room · kitchen · cafe · office · store · pharmacy · bedroom · bathroom · hallway
  exteriors  street · storefront · parking_lot · park · beach · rooftop
  vehicles   road (a driving road with verges) — the cars themselves are `vehicles` in the spec
  studio     cyc · tabletop · podium · turntable
Each takes `pos`, `rot`, `size`, `seed` (layout variety, deterministic), `dress` ("sparse" · "normal" ·
"busy"), `colors` (override the default legend colour per role) and `clear` ([[x, y, r]…] extra places
to keep empty). Dressing never lands on an actor's path or a camera position: those are cleared
automatically, so a template cannot put a plant where someone walks.

Sizes are real-world: lane 3.5 m, kerb 0.15 m, sidewalk 3 m, storey 3.2 m, a parking bay 2.5 × 5 m, a
door 0.9 × 2.1 m, a counter 0.9 m high — common building dimensions, an assumption per site.
"""
from __future__ import annotations
import math, random, sys

try:
    import blocking_kit as KIT
except ImportError:                                    # imported from elsewhere: blocking.py adds the path
    KIT = None

# ── part shorthands (the kit's primitives; a trailing {"m": …} names the part's material) ───────────────
def box(c, s, m=None):
    return ("box", tuple(c), tuple(s), {"m": m}) if m else ("box", tuple(c), tuple(s))


def cyl(c, r, h, axis="z", r2=None, m=None):
    p = ("cyl", tuple(c), (r, r if r2 is None else r2, h), axis)
    return p + ({"m": m},) if m else p


def sph(c, rx, ry=None, rz=None, m=None):
    p = ("sph", tuple(c), (rx, ry or rx, rz or rx))
    return p + ({"m": m},) if m else p


def cone(c, r1, r2, h, axis="z", m=None):
    p = ("cone", tuple(c), (r1, r2, h), axis)
    return p + ({"m": m},) if m else p


def _rng(seed, *salt):
    return random.Random(hash_str(f"{seed}:" + ":".join(str(s) for s in salt)))


def hash_str(s: str) -> int:
    h = 2166136261
    for ch in s.encode():
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h


# ── part builders for the new kinds (w, d, h = footprint and height; origin: footprint centre, floor) ──
def p_building(w, d, h, piece):
    """A facade with depth: floors of recessed windows, a ground floor (storefront glass, a door, a sign
    band) and a cornice. The front is local −y."""
    out = [box((0, 0, h / 2), (w, d, h), "concrete" if piece.get("style") != "brick" else "brick")]
    storey = 3.2
    ground = 4.2
    n_up = max(0, int((h - ground) // storey))
    bays = max(1, int(w // 2.6))
    bw = w / bays
    for f in range(n_up):
        z = ground + f * storey + storey * 0.52
        for b in range(bays):
            x = -w / 2 + bw * (b + 0.5)
            out.append(box((x, -d / 2 - 0.02, z), (bw * 0.55, 0.12, storey * 0.52), "glass_dark"))   # window recess
            out.append(box((x, -d / 2 - 0.08, z - storey * 0.30), (bw * 0.62, 0.16, 0.08), "stone"))  # sill
    shop = piece.get("shop", True)
    if shop:
        out.append(box((0, -d / 2 - 0.03, ground * 0.45), (w * 0.86, 0.10, ground * 0.66), "glass"))
        out.append(box((-w * 0.3, -d / 2 - 0.05, 1.05), (1.0, 0.12, 2.1), "door"))
        out.append(box((0, -d / 2 - 0.10, ground * 0.86), (w * 0.9, 0.20, 0.55), "sign"))
        if piece.get("awning"):
            out.append(box((0, -d / 2 - 0.75, ground * 0.76), (w * 0.8, 1.5, 0.08), "fabric"))
    else:
        out.append(box((0, -d / 2 - 0.05, 1.05), (1.2, 0.12, 2.1), "door"))
    out.append(box((0, -d / 2 - 0.12, h - 0.25), (w, 0.30, 0.35), "stone"))                    # cornice
    return out


def p_streetlight(w, d, h, piece):
    return [cyl((0, 0, 0.15), 0.14, 0.3, m="metal_dark"), cyl((0, 0, h / 2), 0.07, h, m="metal_dark", r2=0.05),
            box((0.45, 0, h - 0.05), (0.9, 0.08, 0.06), "metal_dark"),
            box((0.85, 0, h - 0.12), (0.45, 0.22, 0.10), "lamp_glow")]


def p_tree(w, d, h, piece):
    r = min(w, d) / 2
    trunk = h * 0.42
    out = [cyl((0, 0, trunk / 2), r * 0.09, trunk, r2=r * 0.07, m="bark")]
    rng = _rng(piece.get("seed", 0), piece.get("id", "tree"))
    for i in range(4):
        a = rng.uniform(0, 2 * math.pi)
        rr = r * rng.uniform(0.15, 0.4)
        out.append(sph((math.cos(a) * rr, math.sin(a) * rr, trunk + (h - trunk) * rng.uniform(0.35, 0.6)),
                       r * rng.uniform(0.55, 0.8), None, (h - trunk) * rng.uniform(0.35, 0.5), m="foliage"))
    return out


def p_bush(w, d, h, piece):
    return [sph((0, 0, h / 2), w / 2, d / 2, h / 2, m="foliage")]


def p_bench(w, d, h, piece):
    out = [box((0, 0, 0.44), (w, d * 0.75, 0.05), "wood"), box((0, d / 2 - 0.05, 0.75), (w, 0.05, 0.4), "wood")]
    out += [box((sx * (w / 2 - 0.1), 0, 0.22), (0.06, d * 0.7, 0.44), "metal_dark") for sx in (-1, 1)]
    return out


def p_bin(w, d, h, piece):
    return [cyl((0, 0, h / 2), w / 2, h, r2=w / 2 * 0.92, m="metal_dark")]


def p_bollard(w, d, h, piece):
    return [cyl((0, 0, h / 2), w / 2, h, m="metal_dark"), sph((0, 0, h), w / 2, None, w / 3, m="metal_dark")]


def p_hydrant(w, d, h, piece):
    return [cyl((0, 0, h * 0.4), w * 0.3, h * 0.8, m="paint_red"), sph((0, 0, h * 0.82), w * 0.33, None, h * 0.18, m="paint_red"),
            cyl((0, 0, h * 0.5), w * 0.12, w, axis="y", m="paint_red")]


def p_bus_stop(w, d, h, piece):
    return [box((0, d / 2 - 0.05, h / 2), (w, 0.06, h * 0.85), "glass"), box((0, 0, h), (w + 0.2, d + 0.2, 0.08), "metal"),
            box((0, 0.1, 0.45), (w * 0.8, 0.35, 0.05), "metal")] + \
           [cyl((sx * (w / 2), d / 2 - 0.05, h / 2), 0.04, h, m="metal") for sx in (-1, 1)]


def p_flat(w, d, h, piece):
    """Roads, sidewalks, grass, sand, paths, bays: a slab whose top is walkable."""
    return [box((0, 0, h / 2), (w, d, h), piece.get("material", "asphalt"))]


def p_marking(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "paint_white")]


def p_water(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "water")]


def p_umbrella(w, d, h, piece):
    r = w / 2
    return [cyl((0, 0, h / 2), 0.025, h, m="wood"), cone((0, 0, h - 0.18), r, 0.05, 0.36, m="fabric")]


def p_lounger(w, d, h, piece):
    return [box((0, 0.2, 0.32), (w, d * 0.65, 0.06), "fabric"), box((0, -d / 2 + 0.3, 0.55), (w, 0.08, 0.55), "fabric")] + \
           [box((sx * (w / 2 - 0.05), sy * (d / 2 - 0.08), 0.15), (0.04, 0.04, 0.3), "wood") for sx in (-1, 1) for sy in (-1, 1)]


def p_rock(w, d, h, piece):
    rng = _rng(piece.get("seed", 0), piece.get("id", "rock"))
    return [sph((0, 0, h * 0.4), w / 2, d / 2 * rng.uniform(0.8, 1.0), h * 0.6, m="stone")]


def p_parapet(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "concrete"), box((0, 0, h + 0.03), (w, d + 0.06, 0.06), "metal")]


def p_hvac(w, d, h, piece):
    out = [box((0, 0, h / 2), (w, d, h), "metal")]
    out += [cyl((sx * w * 0.22, 0, h + 0.02), min(w, d) * 0.2, 0.04, m="metal_dark") for sx in (-1, 1)]
    return out


def p_tank(w, d, h, piece):
    return [cyl((0, 0, h * 0.62), w / 2, h * 0.6, m="wood"), cone((0, 0, h * 0.97), w / 2, 0.05, h * 0.12, m="metal_dark")] + \
           [box((sx * w * 0.3, sy * d * 0.3, h * 0.16), (0.08, 0.08, h * 0.32), "metal_dark") for sx in (-1, 1) for sy in (-1, 1)]


def p_skyline(w, d, h, piece):
    rng = _rng(piece.get("seed", 0), piece.get("id", "sky"))
    out, x = [], -w / 2
    while x < w / 2:
        bw = rng.uniform(6, 16)
        bh = h * rng.uniform(0.45, 1.0)
        out.append(box((x + bw / 2, rng.uniform(-d / 4, d / 4), bh / 2), (bw * 0.9, d * rng.uniform(0.4, 0.9), bh), "concrete"))
        x += bw
    return out


def p_cyc(w, d, h, piece):
    """A cyclorama: floor, a curved cove (12 steps) and the wall; the subject stands on local −y."""
    R = min(1.2, d * 0.35)
    out = [box((0, -R / 2, 0.01), (w, d - R, 0.02), "cyc")]
    n = 12
    yc, zc = d / 2 - R, R
    for i in range(n):
        a0, a1 = -math.pi / 2 + (math.pi / 2) * i / n, -math.pi / 2 + (math.pi / 2) * (i + 1) / n
        am = (a0 + a1) / 2
        y, z = yc + math.cos(am) * R, zc + math.sin(am) * R
        seg = 2 * R * math.sin((a1 - a0) / 2)
        th = 0.04
        # a thin slab tangent to the arc
        out.append(("box", (0, y, z), (w, th if abs(math.sin(am)) > 0.7 else seg, seg if abs(math.sin(am)) > 0.7 else th),
                    {"m": "cyc", "rx": math.degrees(am + math.pi / 2)}))
    out.append(box((0, d / 2 - 0.02, R + (h - R) / 2), (w, 0.04, h - R), "cyc"))
    return out


def p_podium(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), piece.get("material", "plaster")), box((0, 0, h + 0.01), (w * 1.02, d * 1.02, 0.02), "stone")]


def p_turntable(w, d, h, piece):
    return [cyl((0, 0, h * 0.35), w / 2 * 0.95, h * 0.7, m="metal_dark"), cyl((0, 0, h * 0.85), w / 2, h * 0.3, m="plaster")]


def p_softbox(w, d, h, piece):
    out = [cyl((0, 0, h * 0.45), 0.02, h * 0.9, m="metal_dark")]
    out += [cyl((math.cos(a) * 0.35, math.sin(a) * 0.35, 0.05), 0.015, 0.7, axis="x", m="metal_dark")
            for a in (0, 2.09, 4.19)]
    out.append(box((0, 0, h), (w, 0.25, w * 0.75), "lamp_glow"))
    return out


def p_cabinets_upper(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "wood_paint")] + \
           [box((-w / 2 + (i + 0.5) * w / max(1, int(w / 0.6)), -d / 2 - 0.01, h / 2), (w / max(1, int(w / 0.6)) - 0.02, 0.02, h - 0.04), "wood_paint")
            for i in range(max(1, int(w / 0.6)))]


def p_store_shelf(w, d, h, piece):
    out = [box((0, 0, h / 2), (w, 0.04, h), "metal"), box((0, 0, 0.06), (w, d, 0.12), "metal")]
    n = 5
    out += [box((0, 0, 0.12 + i * (h - 0.2) / n), (w, d, 0.025), "metal") for i in range(1, n + 1)]
    rng = _rng(piece.get("seed", 0), piece.get("id", "shelf"))
    for i in range(1, n + 1):
        z = 0.12 + i * (h - 0.2) / n
        x = -w / 2 + 0.06
        while x < w / 2 - 0.1:
            pw = rng.uniform(0.07, 0.16)
            ph = rng.uniform(0.12, (h - 0.2) / n * 0.8)
            out.append(box((x + pw / 2, -d * 0.1, z + ph / 2 + 0.013), (pw * 0.9, d * 0.7, ph), "product"))
            x += pw + 0.01
    return out


def p_display_fridge(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "metal"), box((0, -d / 2 - 0.01, h * 0.52), (w * 0.92, 0.02, h * 0.82), "glass")]


def p_checkout(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "wood_paint"), box((0, 0, h + 0.02), (w, d, 0.04), "stone"),
            box((w * 0.25, 0.05, h + 0.15), (0.35, 0.25, 0.26), "plastic_dark")]


def p_armchair(w, d, h, piece):
    out = [box((0, 0, 0.22), (w, d, 0.24), "fabric"), box((0, 0, 0.40), (w * 0.7, d * 0.75, 0.12), "fabric"),
           box((0, d / 2 - 0.1, (0.4 + h) / 2), (w, 0.2, h - 0.4), "fabric")]
    out += [box((sx * (w / 2 - 0.09), 0, 0.33), (0.18, d, 0.66 - 0.0), "fabric") for sx in (-1, 1)]
    return out


def p_coffee_table(w, d, h, piece):
    return [box((0, 0, h - 0.025), (w, d, 0.05), "wood")] + \
           [box((sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), (h - 0.05) / 2), (0.05, 0.05, h - 0.05), "wood")
            for sx in (-1, 1) for sy in (-1, 1)]


def p_console(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "wood"), box((0, -d / 2 - 0.005, h * 0.45), (w * 0.95, 0.01, h * 0.6), "wood_paint")]


def p_wardrobe(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "wood_paint"), box((0, -d / 2 - 0.01, h / 2), (0.01, 0.02, h * 0.95), "wood")] + \
           [box((sx * 0.06, -d / 2 - 0.03, h * 0.55), (0.02, 0.03, 0.25), "metal") for sx in (-1, 1)]


def p_nightstand(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "wood"), box((0, -d / 2 - 0.01, h * 0.7), (w * 0.85, 0.02, h * 0.3), "wood_paint")]


def p_toilet(w, d, h, piece):
    return [cyl((0, -d * 0.12, 0.2), w * 0.32, 0.4, r2=w * 0.42, m="ceramic"), box((0, d / 2 - 0.1, 0.6), (w * 0.9, 0.18, 0.4), "ceramic"),
            cyl((0, -d * 0.12, 0.42), w * 0.45, 0.04, m="ceramic")]


def p_vanity(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "wood_paint"), box((0, 0, h + 0.02), (w, d, 0.04), "stone"),
            cyl((0, -0.05, h + 0.05), 0.2, 0.08, m="ceramic"), box((0, d / 2 - 0.02, h + 0.55), (w * 0.85, 0.03, 0.75), "mirror")]


def p_bathtub(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "ceramic"), box((0, 0, h - 0.18), (w - 0.14, d - 0.14, 0.36), "water")]


def p_picture(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "wood"), box((0, -d / 2 - 0.005, h / 2), (w * 0.86, 0.01, h * 0.82), "art")]


def p_curtain(w, d, h, piece):
    out = []
    n = max(3, int(w / 0.18))
    for i in range(n):
        x = -w / 2 + (i + 0.5) * w / n
        out.append(cyl((x, 0, h / 2), w / n * 0.6, h, m="fabric_light"))
    out.append(cyl((0, 0, h + 0.02), 0.015, w + 0.2, axis="x", m="metal"))
    return out


def p_menu_board(w, d, h, piece):
    return [box((0, 0, h / 2), (w, d, h), "blackboard")]


def p_monitor(w, d, h, piece):
    return [box((0, 0, h * 0.6), (w, 0.03, h * 0.65), "plastic_dark"), box((0, 0.03, h * 0.15), (0.05, 0.05, h * 0.3), "metal"),
            box((0, 0.03, 0.01), (w * 0.35, 0.18, 0.02), "metal")]


def p_car(w, d, h, piece):
    """A car built to be looked into as well as at: chassis and sills, hood and trunk, A/B/C pillars and a
    roof, open window spaces (blocking reads the occupants through them), dashboard, steering wheel,
    seats, wheels and lamps. Local +x is the nose."""
    L, W_, H = w, d, h
    wr = 0.33
    belt = 0.98
    out = [box((0, 0, 0.42), (L * 0.98, W_, 0.5), "paint"),                                       # lower body
           box((L * 0.33, 0, belt - 0.12), (L * 0.32, W_ * 0.97, 0.24), "paint"),                  # hood
           box((-L * 0.38, 0, belt - 0.12), (L * 0.22, W_ * 0.97, 0.24), "paint"),                 # trunk lid
           box((L * 0.49, 0, 0.45), (0.08, W_ * 0.95, 0.28), "plastic_dark"),                      # front bumper
           box((-L * 0.49, 0, 0.45), (0.08, W_ * 0.95, 0.28), "plastic_dark")]
    # doors up to the beltline, cabin floor, roof and pillars
    for sy in (-1, 1):
        out.append(box((-0.05, sy * (W_ / 2 - 0.05), belt - 0.2), (L * 0.42, 0.1, 0.42), "paint"))
        out.append(box((L * 0.17, sy * (W_ / 2 - 0.12), (belt + H) / 2 - 0.02), (0.08, 0.08, H - belt), "paint"))   # A
        out.append(box((-0.05, sy * (W_ / 2 - 0.1), (belt + H) / 2), (0.1, 0.08, H - belt), "paint"))              # B
        out.append(box((-L * 0.27, sy * (W_ / 2 - 0.12), (belt + H) / 2), (0.14, 0.08, H - belt), "paint"))        # C
    out.append(box((-0.05, 0, H - 0.04), (L * 0.46, W_ * 0.86, 0.06), "paint"))                 # roof
    out.append(box((-0.05, 0, 0.32), (L * 0.5, W_ * 0.9, 0.06), "fabric_dark"))                 # cabin floor
    out.append(box((0.62, 0, 0.82), (0.32, W_ * 0.88, 0.3), "plastic_dark"))                    # dashboard
    out.append(cyl((0.48, 0.37, 0.95), 0.19, 0.03, axis="x", m="plastic_dark"))                  # steering wheel
    out.append(cyl((0.56, 0.37, 0.9), 0.03, 0.18, axis="x", m="plastic_dark"))
    for sy in (-1, 1):                                                                         # front seats
        out.append(box((0.0, sy * 0.37, 0.47), (0.5, 0.5, 0.12), "fabric_dark"))
        out.append(box((-0.24, sy * 0.37, 0.82), (0.12, 0.48, 0.62), "fabric_dark"))
        out.append(box((-0.21, sy * 0.37, 1.17), (0.1, 0.24, 0.16), "fabric_dark"))
    out.append(box((-0.85, 0, 0.49), (0.5, W_ * 0.82, 0.12), "fabric_dark"))                    # rear bench
    out.append(box((-1.1, 0, 0.82), (0.12, W_ * 0.82, 0.6), "fabric_dark"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(cyl((sx * L * 0.31, sy * (W_ / 2 - 0.12), wr), wr, 0.22, axis="y", m="rubber"))
            out.append(cyl((sx * L * 0.31, sy * (W_ / 2 - 0.0), wr), wr * 0.6, 0.02, axis="y", m="metal"))
        out.append(box((sx * L * 0.495, 0, 0.66), (0.04, W_ * 0.75, 0.1), "lamp_glow" if sx > 0 else "lamp_red"))
    out.append(box((L * 0.18, 0, (belt + H) / 2 + 0.02), (0.02, W_ * 0.75, H - belt - 0.08), "glass"))    # windshield
    return out


PARTS = {
    "building": p_building, "streetlight": p_streetlight, "tree": p_tree, "bush": p_bush, "bench": p_bench,
    "bin": p_bin, "bollard": p_bollard, "hydrant": p_hydrant, "bus_stop": p_bus_stop,
    "road": p_flat, "sidewalk": p_flat, "grass": p_flat, "sand": p_flat, "path": p_flat, "bay": p_flat,
    "deck": p_flat, "kerb": p_flat, "marking": p_marking, "water": p_water, "umbrella": p_umbrella,
    "lounger": p_lounger, "rock": p_rock, "parapet": p_parapet, "hvac": p_hvac, "tank": p_tank,
    "skyline": p_skyline, "cyc": p_cyc, "podium": p_podium, "turntable": p_turntable, "softbox": p_softbox,
    "cabinets_upper": p_cabinets_upper, "store_shelf": p_store_shelf, "display_fridge": p_display_fridge,
    "checkout": p_checkout, "armchair": p_armchair, "coffee_table": p_coffee_table, "console": p_console,
    "wardrobe": p_wardrobe, "nightstand": p_nightstand, "toilet": p_toilet, "vanity": p_vanity,
    "bathtub": p_bathtub, "picture": p_picture, "curtain": p_curtain, "menu_board": p_menu_board,
    "monitor": p_monitor, "car": p_car,
}
DIMENSIONS = {
    "building": (12.0, 10.0, 14.0), "streetlight": (0.4, 0.4, 6.0), "tree": (3.0, 3.0, 6.0), "bush": (1.2, 1.0, 0.9),
    "bench": (1.6, 0.6, 0.85), "bin": (0.5, 0.5, 0.95), "bollard": (0.2, 0.2, 0.9), "hydrant": (0.35, 0.35, 0.75),
    "bus_stop": (3.0, 1.4, 2.4), "road": (20.0, 7.0, 0.02), "sidewalk": (20.0, 3.0, 0.03), "kerb": (20.0, 0.2, 0.15), "grass": (20.0, 20.0, 0.03),
    "sand": (30.0, 20.0, 0.03), "path": (2.0, 20.0, 0.04), "bay": (2.5, 5.0, 0.01), "deck": (20.0, 20.0, 0.1),
    "marking": (3.0, 0.15, 0.005), "water": (60.0, 40.0, 0.02), "umbrella": (2.0, 2.0, 2.3), "lounger": (0.65, 1.9, 0.6),
    "rock": (1.0, 0.8, 0.6), "parapet": (10.0, 0.25, 1.1), "hvac": (1.4, 1.0, 1.1), "tank": (1.8, 1.8, 3.0),
    "skyline": (120.0, 30.0, 60.0), "cyc": (8.0, 6.0, 4.0), "podium": (0.6, 0.6, 0.9), "turntable": (0.8, 0.8, 0.08),
    "softbox": (0.9, 0.9, 2.2), "cabinets_upper": (2.4, 0.35, 0.7), "store_shelf": (2.0, 0.5, 1.8),
    "display_fridge": (1.4, 0.7, 2.0), "checkout": (1.6, 0.7, 0.95), "armchair": (0.85, 0.85, 0.9),
    "coffee_table": (1.1, 0.6, 0.42), "console": (1.6, 0.42, 0.55), "wardrobe": (1.2, 0.6, 2.1),
    "nightstand": (0.5, 0.4, 0.55), "toilet": (0.4, 0.68, 0.78), "vanity": (1.0, 0.5, 0.85), "bathtub": (1.7, 0.75, 0.55),
    "picture": (0.9, 0.04, 0.65), "curtain": (1.6, 0.12, 2.4), "menu_board": (2.4, 0.06, 1.1), "monitor": (0.6, 0.2, 0.45),
    "car": (4.6, 1.85, 1.45),
}
WALKABLE_KINDS = {"road", "sidewalk", "grass", "sand", "path", "bay", "deck", "marking", "floor_mark", "turntable", "cyc"}
SURFACES = {"turntable": 0.08, "podium": 0.9, "coffee_table": 0.42, "console": 0.55, "nightstand": 0.55,
            "checkout": 0.99, "vanity": 0.89, "bench": 0.47}


# ── templates: an environment → set pieces ───────────────────────────────────────────────────────────────
class Builder:
    """Collects pieces in the environment's own frame and places them in the world (pos, rot)."""

    def __init__(self, env: dict, prefix: str):
        self.env, self.prefix = env, prefix
        self.ox, self.oy = (float(v) for v in env.get("pos", [0, 0]))
        self.rot = float(env.get("rot", 0))
        self.pieces = []
        self.n = 0
        self.colors = dict(DEFAULT_COLORS)
        self.colors.update(env.get("colors", {}))
        self.used_roles = {}

    def add(self, kind, x, y, rot=0.0, size=None, role="set", dressing=False, z=0.0, **extra):
        self.n += 1
        a = math.radians(self.rot)
        wx = self.ox + x * math.cos(a) - y * math.sin(a)
        wy = self.oy + x * math.sin(a) + y * math.cos(a)
        p = {"id": f"{self.prefix}.{kind}{self.n}", "kind": kind, "pos": [round(wx, 3), round(wy, 3)],
             "rot": round(self.rot + rot, 2), "color": self.colors.get(role, "grey"), "_role": role,
             "_dressing": dressing, "_env": self.prefix}
        if size:
            p["size"] = [round(float(v), 3) for v in size]
        if z:
            p["z"] = z
        if kind in WALKABLE_KINDS:
            p["walkable"] = True
        p.update(extra)
        self.pieces.append(p)
        self.used_roles[role] = self.colors.get(role, "grey")
        return p


# role → default legend colour, and the line the legend gets for it
DEFAULT_COLORS = {"set": "grey", "walls": "darkgrey", "floor": "grey", "furniture": "grey", "soft": "beige",
                  "wood": "brown", "green": "green", "road": "black", "marking": "white", "building": "darkgrey",
                  "car": "grey", "water": "cyan", "sand": "beige", "glass": "grey", "light": "grey",
                  "studio": "white", "screen": "black"}
ROLE_WORDS = {"walls": "walls", "building": "buildings and facades", "road": "the road and asphalt", "marking":
              "road markings", "green": "trees, plants and grass", "soft": "upholstered furniture and fabric",
              "wood": "wooden furniture", "water": "water", "sand": "sand", "studio": "the studio cyclorama and sweep",
              "screen": "screens and dark glass"}


def _room(b: Builder, w, d, h, walls=("back", "left", "right"), openings=(), color_role="walls"):
    room = {"id": f"{b.prefix}.room", "kind": "room", "pos": [b.ox, b.oy], "rot": b.rot, "size": [w, d, h],
            "walls": list(walls), "openings": list(openings), "color": b.colors.get(color_role, "darkgrey"),
            "_role": color_role, "_env": b.prefix}
    b.pieces.append(room)
    b.used_roles[color_role] = room["color"]
    return room


def t_living_room(b, env, rng, dress):
    w, d, h = env.get("size", [6.0, 5.0, 2.7])
    _room(b, w, d, h, openings=[{"wall": "back", "kind": "window", "at": -w * 0.22, "w": 1.6, "h": 1.4, "sill": 0.8},
                                {"wall": "left", "kind": "door", "at": d * 0.25, "w": 0.9, "h": 2.1}])
    b.add("rug", 0, 0.1, size=[2.6, 1.8, 0.01], role="soft", dressing=True)
    b.add("sofa", 0, d / 2 - 0.65, rot=0, role="soft")
    b.add("coffee_table", 0, 0.15, role="wood", dressing=True)
    b.add("armchair", -w / 2 + 0.9, 0.0, rot=-90, role="soft", dressing=True)
    b.add("console", 0, -d / 2 + 0.3 + 0.0, rot=180, role="wood", dressing=True) if env.get("front_wall") else None
    b.add("lamp", w / 2 - 0.5, d / 2 - 0.5, role="light", dressing=True)
    b.add("plant", -w / 2 + 0.45, d / 2 - 0.45, role="green", dressing=True)
    b.add("shelf", w / 2 - 0.25, 0.3, rot=-90, role="wood", dressing=True)
    b.add("picture", w * 0.12, d / 2 - 0.03, z=1.35, role="wood", dressing=True)
    b.add("curtain", -w * 0.22 - 1.0, d / 2 - 0.12, role="soft", dressing=True)
    b.add("curtain", -w * 0.22 + 1.0, d / 2 - 0.12, role="soft", dressing=True)


def t_kitchen(b, env, rng, dress):
    w, d, h = env.get("size", [5.0, 4.0, 2.7])
    _room(b, w, d, h, openings=[{"wall": "back", "kind": "window", "at": 0.6, "w": 1.2, "h": 1.0, "sill": 1.05},
                                {"wall": "left", "kind": "door", "at": 0.0, "w": 0.9, "h": 2.1, "open": 30}])
    b.add("counter", -0.6, d / 2 - 0.35, size=[w - 1.6, 0.6, 0.9], role="furniture")
    b.add("cabinets_upper", -1.4, d / 2 - 0.2, size=[1.6, 0.35, 0.7], z=1.45, role="furniture", dressing=True)
    b.add("fridge", w / 2 - 0.45, d / 2 - 0.4, role="furniture")
    if env.get("island", True):
        b.add("island", 0, 0.1, size=[1.8, 0.9, 0.9], role="furniture")
        for sx in (-0.5, 0.5):
            b.add("stool", sx, -0.6, role="furniture", dressing=True)
    b.add("plant", -w / 2 + 0.35, d / 2 - 0.35, role="green", dressing=True)
    b.add("lamp", -w / 2 + 0.4, -d / 2 + 0.4, role="light", dressing=True) if dress == "busy" else None


def t_cafe(b, env, rng, dress):
    w, d, h = env.get("size", [8.0, 6.0, 3.0])
    _room(b, w, d, h, walls=("back", "left", "right"),
          openings=[{"wall": "left", "kind": "window", "at": -0.5, "w": 2.4, "h": 1.6, "sill": 0.6},
                    {"wall": "right", "kind": "window", "at": 0.5, "w": 2.4, "h": 1.6, "sill": 0.6},
                    {"wall": "back", "kind": "door", "at": w / 2 - 1.0, "w": 0.9, "h": 2.1}])
    b.add("counter", -w * 0.15, d / 2 - 0.9, size=[3.2, 0.7, 1.05], role="wood")
    b.add("menu_board", -w * 0.15, d / 2 - 0.05, z=1.6, role="screen", dressing=True)
    b.add("display_fridge", w * 0.18, d / 2 - 0.4, size=[1.2, 0.7, 1.9], role="furniture", dressing=True)
    n = {"sparse": 2, "normal": 4, "busy": 6}.get(dress, 4)
    spots = [(-w * 0.3, -0.6), (w * 0.25, -0.4), (-w * 0.3, -d * 0.35 + 0.2), (w * 0.25, -d * 0.35), (0, -0.5), (0, -d * 0.35)]
    for i, (x, y) in enumerate(spots[:n]):
        b.add("round_table", x, y, size=[0.7, 0.7, 0.75], role="wood", dressing=True)
        for sx in (-1, 1):
            b.add("chair", x + sx * 0.62, y, rot=90 * sx, role="furniture", dressing=True)
    b.add("plant", w / 2 - 0.4, -d / 2 + 0.4, role="green", dressing=True)
    b.add("lamp", -w / 2 + 0.4, d / 2 - 0.4, role="light", dressing=True)


def t_office(b, env, rng, dress):
    w, d, h = env.get("size", [7.0, 5.5, 2.8])
    _room(b, w, d, h, openings=[{"wall": "back", "kind": "window", "at": 0.0, "w": 3.6, "h": 1.7, "sill": 0.6},
                                {"wall": "right", "kind": "door", "at": -d * 0.25, "w": 0.9, "h": 2.1}])
    for x in (-w * 0.25, w * 0.25):
        b.add("desk", x, d / 2 - 1.4, role="wood")
        b.add("monitor", x, d / 2 - 1.15, z=0.75, role="screen", dressing=True)
        b.add("chair", x, d / 2 - 2.0, rot=180, role="furniture", dressing=True)
    b.add("shelf", -w / 2 + 0.2, 0.0, rot=90, role="wood", dressing=True)
    b.add("plant", w / 2 - 0.4, d / 2 - 0.4, role="green", dressing=True)
    b.add("sofa", w / 2 - 0.5, -d * 0.25, rot=-90, size=[1.8, 0.85, 0.85], role="soft", dressing=True) if dress != "sparse" else None


def t_store(b, env, rng, dress, pharmacy=False):
    w, d, h = env.get("size", [9.0, 7.0, 3.2])
    _room(b, w, d, h, walls=("back", "left", "right"),
          openings=[{"wall": "left", "kind": "door", "at": -d * 0.3, "w": 1.6, "h": 2.3}])
    if pharmacy:
        b.add("checkout", 0, d / 2 - 1.6, size=[3.2, 0.7, 1.0], role="wood")
        for x in (-w * 0.3, 0, w * 0.3):
            b.add("store_shelf", x, d / 2 - 0.3, size=[2.4, 0.4, 2.2], role="furniture", dressing=False)
    else:
        b.add("checkout", -w / 2 + 1.4, -d / 2 + 1.2, rot=90, role="wood")
        for i, x in enumerate((-w * 0.15, w * 0.12, w * 0.38)):
            b.add("store_shelf", x, 0.2, rot=90, size=[3.0, 0.5, 1.7], role="furniture")
        b.add("display_fridge", 0, d / 2 - 0.4, size=[3.0, 0.7, 2.0], role="furniture")
    b.add("plant", w / 2 - 0.4, -d / 2 + 0.4, role="green", dressing=True)


def t_pharmacy(b, env, rng, dress):
    t_store(b, env, rng, dress, pharmacy=True)


def t_bedroom(b, env, rng, dress):
    w, d, h = env.get("size", [5.0, 4.5, 2.7])
    _room(b, w, d, h, openings=[{"wall": "left", "kind": "window", "at": 0.3, "w": 1.4, "h": 1.4, "sill": 0.8},
                                {"wall": "right", "kind": "door", "at": -d * 0.3, "w": 0.9, "h": 2.1}])
    b.add("bed", 0, d / 2 - 1.05, role="soft")
    for sx in (-1, 1):
        b.add("nightstand", sx * 1.1, d / 2 - 0.25, role="wood", dressing=True)
        b.add("lamp", sx * 1.1, d / 2 - 0.25, z=0.55, size=[0.3, 0.3, 0.5], role="light", dressing=True)
    b.add("wardrobe", w / 2 - 0.35, 0.2, rot=-90, role="wood", dressing=True)
    b.add("rug", 0, 0.0, size=[2.0, 1.4, 0.01], role="soft", dressing=True)
    b.add("picture", 0, d / 2 - 0.03, z=1.5, size=[1.2, 0.04, 0.6], role="wood", dressing=True)


def t_bathroom(b, env, rng, dress):
    w, d, h = env.get("size", [3.0, 2.6, 2.5])
    _room(b, w, d, h, openings=[{"wall": "right", "kind": "door", "at": -0.5, "w": 0.8, "h": 2.1}])
    b.add("vanity", -0.4, d / 2 - 0.25, role="furniture")
    b.add("toilet", w / 2 - 0.5, d / 2 - 0.35, role="furniture", dressing=True)
    b.add("bathtub", -w / 2 + 0.38, -0.2, rot=90, size=[1.7, 0.75, 0.55], role="furniture", dressing=True)


def t_hallway(b, env, rng, dress):
    w, d, h = env.get("size", [2.4, 9.0, 2.7])
    _room(b, w, d, h, openings=[{"wall": "left", "kind": "door", "at": -d * 0.2, "w": 0.9, "h": 2.1},
                                {"wall": "left", "kind": "door", "at": d * 0.2, "w": 0.9, "h": 2.1, "open": 50},
                                {"wall": "right", "kind": "window", "at": 0.0, "w": 1.4, "h": 1.2, "sill": 0.9},
                                {"wall": "back", "kind": "door", "at": 0.0, "w": 1.0, "h": 2.2}])
    b.add("rug", 0, 0, size=[1.0, d * 0.7, 0.01], role="soft", dressing=True)
    b.add("console", w / 2 - 0.25, -d * 0.3, rot=-90, size=[1.2, 0.35, 0.8], role="wood", dressing=True)
    for y in (-d * 0.3, d * 0.3):
        b.add("picture", -w / 2 + 0.03, y, rot=-90, z=1.4, role="wood", dressing=True)


def t_street(b, env, rng, dress):
    L = float(env.get("length", 60.0))
    lanes = int(env.get("lanes", 2))
    lane = 3.5
    rw = lanes * lane
    sw = float(env.get("sidewalk", 3.2))
    b.add("road", 0, 0, size=[L, rw, 0.02], role="road", material="asphalt")
    n_dash = int(L // 6)
    for i in range(n_dash):
        b.add("marking", -L / 2 + 3 + i * 6, 0, size=[3.0, 0.14, 0.005], role="marking", dressing=False)
    for sy in (1, -1) if env.get("both_sides", True) else (1,):
        y0 = sy * (rw / 2)
        b.add("kerb", 0, y0 + sy * 0.1, size=[L, 0.2, 0.15], role="set", material="stone")
        b.add("sidewalk", 0, y0 + sy * (0.2 + sw / 2), size=[L, sw, 0.03], role="set", material="pavement")
        # buildings: a run of facades with their own widths and heights
        x = -L / 2
        k = 0
        while x < L / 2 - 4:
            bw = rng.uniform(7.0, 13.0)
            bh = rng.uniform(9.0, 22.0)
            b.add("building", x + bw / 2, y0 + sy * (0.2 + sw + 5.0), rot=0 if sy > 0 else 180, size=[bw - 0.2, 10.0, bh],
                  role="building", shop=rng.random() < 0.8, awning=rng.random() < 0.35,
                  style="brick" if rng.random() < 0.4 else "concrete")
            x += bw
            k += 1
        n_lights = int(L // 16)
        for i in range(n_lights):
            b.add("streetlight", -L / 2 + 8 + i * 16, y0 + sy * 0.6, rot=-90 if sy > 0 else 90, role="light", dressing=True)
        if dress != "sparse":
            for i in range(int(L // 9)):
                if rng.random() < (0.8 if dress == "busy" else 0.5):
                    b.add("tree", -L / 2 + 4.5 + i * 9, y0 + sy * 1.1, size=[3.2, 3.2, rng.uniform(5, 7.5)], role="green",
                          dressing=True, seed=rng.randint(0, 999))
            for i in range(int(L // 12)):
                b.add("bin", -L / 2 + 6 + i * 12 + rng.uniform(-1, 1), y0 + sy * 0.55, role="set", dressing=True)
            if env.get("parked", dress == "busy"):
                for i in range(int(L // 7)):
                    if rng.random() < 0.6:
                        b.add("car", -L / 2 + 4 + i * 7, y0 - sy * 1.25, rot=0 if rng.random() < 0.5 else 180, role="car",
                              dressing=True)
    if env.get("crosswalk", True):
        for i in range(-int(rw / 0.9) // 2, int(rw / 0.9) // 2 + 1):
            b.add("marking", 0, i * 0.9, size=[3.0, 0.45, 0.005], role="marking")


def t_storefront(b, env, rng, dress):
    w = float(env.get("width", 9.0))
    b.add("sidewalk", 0, 0, size=[w + 8, 4.0, 0.03], role="set", material="pavement")
    b.add("kerb", 0, -2.1, size=[w + 8, 0.2, 0.15], role="set", material="stone")
    b.add("road", 0, -4.0, size=[w + 8, 3.6, 0.02], role="road", material="asphalt")
    b.add("building", 0, 2.0 + 5.0, size=[w, 10.0, env.get("height", 8.0)], role="building", shop=True, awning=True,
          style=env.get("style", "brick"))
    b.add("building", -w / 2 - 4.0, 7.0, size=[8.0, 10.0, 12.0], role="building", shop=False)
    b.add("building", w / 2 + 4.0, 7.0, size=[8.0, 10.0, 10.0], role="building", shop=True)
    b.add("bench", w * 0.35, 1.2, rot=180, role="wood", dressing=True)
    b.add("plant", -w * 0.3, 1.6, role="green", dressing=True)
    b.add("streetlight", -w * 0.45, -1.6, rot=90, role="light", dressing=True)


def t_parking_lot(b, env, rng, dress):
    W, D = env.get("size", [30.0, 24.0])[:2]
    b.add("road", 0, 0, size=[W, D, 0.02], role="road", material="asphalt")
    for row, y in enumerate((-D / 2 + 3.0, D / 2 - 3.0)):
        for i in range(int(W // 2.6)):
            x = -W / 2 + 1.3 + i * 2.6
            b.add("marking", x - 1.25, y, rot=90, size=[5.0, 0.12, 0.005], role="marking")
            if rng.random() < {"sparse": 0.25, "normal": 0.5, "busy": 0.8}.get(dress, 0.5):
                b.add("car", x, y, rot=90 if row == 0 else -90, role="car", dressing=True)
    for x in (-W / 3, 0, W / 3):
        b.add("streetlight", x, 0, role="light", dressing=True)
    b.add("building", 0, D / 2 + 6, size=[W, 10, 7], role="building", shop=True)


def t_park(b, env, rng, dress):
    W, D = env.get("size", [40.0, 40.0])[:2]
    b.add("grass", 0, 0, size=[W, D, 0.03], role="green", material="grass")
    b.add("path", 0, 0, size=[2.4, D, 0.04], role="set", material="gravel")
    b.add("path", 0, D * 0.15, size=[W, 2.0, 0.04], role="set", material="gravel")
    n = {"sparse": 8, "normal": 16, "busy": 26}.get(dress, 16)
    for i in range(n):
        x, y = rng.uniform(-W / 2 + 3, W / 2 - 3), rng.uniform(-D / 2 + 3, D / 2 - 3)
        if abs(x) < 3 or abs(y - D * 0.15) < 3:
            continue
        b.add("tree", x, y, size=[rng.uniform(3, 6)] * 2 + [rng.uniform(5, 10)], role="green", dressing=True,
              seed=rng.randint(0, 999))
    for i, y in enumerate((-D * 0.25, D * 0.35)):
        b.add("bench", 2.0, y, rot=90, role="wood", dressing=True)
        b.add("streetlight", -1.8, y + 2, rot=0, role="light", dressing=True)
    for i in range(n // 3):
        b.add("bush", rng.uniform(-W / 2 + 2, W / 2 - 2), rng.uniform(-D / 2 + 2, D / 2 - 2), role="green", dressing=True)
    if env.get("pond", dress != "sparse"):
        b.add("water", W * 0.25, -D * 0.25, size=[9.0, 6.0, 0.02], role="water")


def t_beach(b, env, rng, dress):
    W = float(env.get("width", 60.0))
    b.add("sand", 0, 0, size=[W, 30.0, 0.03], role="sand", material="sand")
    b.add("water", 0, 15.0 + 60.0, size=[W * 4, 120.0, 0.02], role="water")
    n = {"sparse": 2, "normal": 5, "busy": 9}.get(dress, 5)
    for i in range(n):
        x, y = rng.uniform(-W / 3, W / 3), rng.uniform(-6, 8)
        if abs(x) < 2.5 and abs(y) < 2.5:
            continue
        b.add("umbrella", x, y, role="soft", dressing=True)
        b.add("lounger", x + 0.6, y - 0.4, role="soft", dressing=True)
    for i in range(n):
        b.add("rock", rng.uniform(-W / 2, W / 2), rng.uniform(10, 14), size=[rng.uniform(0.6, 2.0)] * 2 + [rng.uniform(0.4, 1.2)],
              role="set", dressing=True, seed=rng.randint(0, 999))


def t_rooftop(b, env, rng, dress):
    W, D = env.get("size", [16.0, 12.0])[:2]
    b.add("deck", 0, 0, size=[W, D, 0.05], role="set", material="concrete")
    for sy in (-1, 1):
        b.add("parapet", 0, sy * D / 2, size=[W, 0.25, 1.1], role="walls")
    b.add("parapet", -W / 2, 0, rot=90, size=[D, 0.25, 1.1], role="walls")
    b.add("parapet", W / 2, 0, rot=90, size=[D, 0.25, 1.1], role="walls")
    b.add("hvac", -W / 2 + 2.0, D / 2 - 1.5, role="set", dressing=True)
    b.add("hvac", -W / 2 + 4.0, D / 2 - 1.5, role="set", dressing=True)
    b.add("tank", W / 2 - 2.2, D / 2 - 2.0, role="wood", dressing=True)
    b.add("skyline", 0, D / 2 + 60, size=[260.0, 40.0, 70.0], z=-40.0, role="building", seed=rng.randint(0, 999))
    b.add("skyline", 0, -D / 2 - 70, rot=180, size=[260.0, 40.0, 60.0], z=-40.0, role="building", seed=rng.randint(0, 999))
    if dress != "sparse":
        b.add("bench", 0, -D / 2 + 1.0, role="wood", dressing=True)
        b.add("plant", W / 2 - 1.0, -D / 2 + 1.0, role="green", dressing=True)


def t_road(b, env, rng, dress):
    """A driving road: two lanes, verges and trees, for a car to travel on and a camera to chase it."""
    L = float(env.get("length", 200.0))
    b.add("road", 0, 0, size=[L, 7.0, 0.02], role="road", material="asphalt")
    for i in range(int(L // 8)):
        b.add("marking", -L / 2 + 4 + i * 8, 0, size=[3.0, 0.14, 0.005], role="marking")
    for sy in (1, -1):
        b.add("grass", 0, sy * (3.5 + 10), size=[L, 20.0, 0.03], role="green", material="grass")
        for i in range(int(L // 14)):
            if rng.random() < 0.7:
                b.add("tree", -L / 2 + 7 + i * 14 + rng.uniform(-3, 3), sy * rng.uniform(7, 16),
                      size=[rng.uniform(3, 5)] * 2 + [rng.uniform(6, 10)], role="green", dressing=True, seed=rng.randint(0, 999))
        for i in range(int(L // 30)):
            b.add("streetlight", -L / 2 + 15 + i * 30, sy * 4.2, rot=-90 * sy, role="light", dressing=True)


def t_cyc(b, env, rng, dress):
    w, d, h = env.get("size", [8.0, 6.0, 4.0])
    b.add("cyc", 0, 0, size=[w, d, h], role="studio", material="cyc")
    if env.get("lights", True):
        for sx in (-1, 1):
            b.add("softbox", sx * 2.4, -d / 2 + 1.2, rot=sx * 35, role="light", dressing=True)


def t_tabletop(b, env, rng, dress):
    b.add("table", 0, 0, size=[1.6, 0.9, 0.85], role="furniture")
    b.add("cyc", 0, 0.05, size=[1.5, 0.85, 0.9], z=0.85, role="studio", material="cyc")
    for sx in (-1, 1):
        b.add("softbox", sx * 1.4, -0.9, rot=sx * 40, role="light", dressing=True)


def t_podium(b, env, rng, dress):
    t_cyc(b, env, rng, dress)
    b.add("podium", 0, -0.5, size=env.get("podium", [0.5, 0.5, 0.95]), role="studio", material="plaster")


def t_turntable(b, env, rng, dress):
    t_cyc(b, env, rng, dress)
    b.add("podium", 0, -0.5, size=[0.7, 0.7, 0.8], role="studio", material="plaster")
    b.add("turntable", 0, -0.5, size=[0.6, 0.6, 0.06], z=0.8, role="studio", spin=float(env.get("spin", 45)))


EXTERIORS = {"street", "storefront", "parking_lot", "park", "beach", "rooftop", "road"}
TEMPLATES = {
    "living_room": (t_living_room, "a living room: sofa, coffee table, armchair, rug, shelf, lamp, window and door"),
    "kitchen": (t_kitchen, "a kitchen: counter run, upper cabinets, fridge, island with stools, window, door"),
    "cafe": (t_cafe, "a café: counter, menu board, display fridge, tables and chairs, windows both sides"),
    "office": (t_office, "an office: two desks with monitors and chairs, shelf, sofa, a window wall"),
    "store": (t_store, "a shop floor: checkout, shelving runs, a fridge wall, the entrance"),
    "pharmacy": (t_pharmacy, "a pharmacy: counter with shelving behind"),
    "bedroom": (t_bedroom, "a bedroom: bed, nightstands and lamps, wardrobe, rug, window"),
    "bathroom": (t_bathroom, "a bathroom: vanity with mirror, toilet, bathtub"),
    "hallway": (t_hallway, "a corridor: doors, a runner, a console, pictures, a window"),
    "street": (t_street, "a city street: lanes and markings, kerbs, sidewalks, facades with shops, lights, trees, "
                         "bins, parked cars, a crosswalk"),
    "storefront": (t_storefront, "one shopfront with its neighbours, sidewalk and kerb, bench, light"),
    "parking_lot": (t_parking_lot, "a parking lot: bays, cars, lamp posts, a building edge"),
    "park": (t_park, "a park: grass, paths, trees, bushes, benches, lamps, a pond"),
    "beach": (t_beach, "a beach: sand, the sea to the horizon, umbrellas, loungers, rocks"),
    "rooftop": (t_rooftop, "a rooftop: deck, parapets, HVAC units, a water tank, the skyline below"),
    "road": (t_road, "a driving road: two lanes, verges, trees, lamps — for cars and chases"),
    "cyc": (t_cyc, "a studio cyclorama with softboxes"),
    "tabletop": (t_tabletop, "a product tabletop: table, sweep, softboxes"),
    "podium": (t_podium, "a cyclorama with a plinth for a product"),
    "turntable": (t_turntable, "a plinth with a turntable that spins (`spin` degrees per second)"),
}


def _clear_points(bl, spec: dict) -> list:
    """Where nothing may be dressed: every actor's path, every prop, every camera position, plus `clear`."""
    pts = []
    dur = float(spec.get("duration", 5))
    for a in spec.get("actors", []):
        for k in a.get("keys", []):
            if k.get("pose", a.get("pose", "stand")) == "sit":
                pts.append((float(k["pos"][0]), float(k["pos"][1]), 0.0, "sit"))   # keep the seat and the table
            else:
                pts.append((float(k["pos"][0]), float(k["pos"][1]), 0.7))
        ks = sorted(a.get("keys", []), key=lambda k: float(k["t"]))
        for ka, kb in zip(ks, ks[1:]):
            if math.dist(ka["pos"], kb["pos"]) < 0.05:
                continue
            n = max(1, int(math.dist(ka["pos"], kb["pos"]) / 0.5))
            for i in range(n + 1):
                f = i / n
                pts.append((ka["pos"][0] + (kb["pos"][0] - ka["pos"][0]) * f, ka["pos"][1] + (kb["pos"][1] - ka["pos"][1]) * f, 0.7))
    for v in spec.get("vehicles", []):
        for k in v.get("keys", []):
            pts.append((float(k["pos"][0]), float(k["pos"][1]), 2.8))
    for p in spec.get("props", []):
        if "pos" in p and not p.get("on"):
            pts.append((float(p["pos"][0]), float(p["pos"][1]), 0.4))
    cam = spec.get("camera", {})
    for sh in cam.get("shots", []) + cam.get("keys", []):
        for fr in (sh, sh.get("from", {}), sh.get("to", {})):
            if isinstance(fr.get("pos"), list):
                pts.append((float(fr["pos"][0]), float(fr["pos"][1]), 0.6))
    for env in _envs(spec):
        for c in env.get("clear", []):
            pts.append((float(c[0]), float(c[1]), float(c[2]) if len(c) > 2 else 0.8))
    return pts


def _envs(spec):
    e = spec.get("env")
    return e if isinstance(e, list) else ([e] if e else [])


def _footprint_hit(bl, p: dict, pts: list) -> bool:
    w, d, _ = (p.get("size") or DIMENSIONS.get(p["kind"]) or bl.DIMENSIONS.get(p["kind"], (1, 1, 1)))[:3]
    a = math.radians(float(p.get("rot", 0)))
    for pt in pts:
        x, y, r = pt[:3]
        if len(pt) > 3 and pt[3] == "sit" and p["kind"] in ("chair", "stool", "sofa", "bench", "bed", "armchair"):
            continue                                  # someone sits here: the seat stays
        dx, dy = x - p["pos"][0], y - p["pos"][1]
        lx = dx * math.cos(-a) - dy * math.sin(-a)
        ly = dx * math.sin(-a) + dy * math.cos(-a)
        if abs(lx) < w / 2 + r and abs(ly) < d / 2 + r:
            return True
    return False


def expand(bl, spec: dict) -> list:
    """`env` (one or a list) → set pieces, dressing cleared off every path, legend lines merged in for the
    roles the environment used (the spec's own legend wins)."""
    out = []
    pts = None
    for i, env in enumerate(_envs(spec)):
        kind = env.get("kind")
        if kind not in TEMPLATES:
            raise ValueError(f"env kind {kind!r} is not one of {', '.join(TEMPLATES)}")
        b = Builder(env, env.get("id", f"env{i + 1}"))
        rng = _rng(env.get("seed", 1), kind)
        TEMPLATES[kind][0](b, env, rng, env.get("dress", "normal"))
        if pts is None:
            pts = _clear_points(bl, spec)
        for p in b.pieces:
            if p.get("_dressing") and _footprint_hit(bl, p, pts):
                continue
            out.append(p)
        legend = spec.setdefault("legend", {})
        used = {p["color"] for p in out if p.get("_env") == b.prefix}
        for role, col in b.used_roles.items():
            if col in used and col not in legend and col != "grey":
                legend[col] = f"the {TEMPLATES[kind][1].split(':')[0].replace('a ', '').replace('an ', '')}'s " \
                              f"{ROLE_WORDS.get(role, role)}"
    return out


def kinds_text() -> str:
    return "\n".join(f"  {k:12s} {v[1]}" for k, v in TEMPLATES.items())


# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────
class _BL:
    DIMENSIONS = {"sofa": (2.0, 0.9, 0.85), "rug": (2.0, 1.4, 0.01), "lamp": (0.4, 0.4, 1.6), "plant": (0.4, 0.4, 1.1),
                  "shelf": (1.0, 0.35, 1.8), "counter": (1.8, 0.6, 0.9), "fridge": (0.7, 0.7, 1.8),
                  "island": (2.0, 1.0, 0.9), "stool": (0.4, 0.4, 0.65), "round_table": (1.0, 1.0, 0.75),
                  "chair": (0.45, 0.45, 0.9), "desk": (1.4, 0.7, 0.75), "bed": (1.6, 2.0, 0.55), "table": (1.2, 0.8, 0.75)}


def selftest() -> int:
    for kind, fn in PARTS.items():
        w, d, h = DIMENSIONS[kind]
        prims = fn(w, d, h, {"id": kind, "seed": 1})
        assert prims, kind
        for p in prims:
            assert p[0] in ("box", "cyl", "sph", "cone") and len(p[1]) == 3 and len(p[2]) == 3, (kind, p)
    for kind in TEMPLATES:
        spec = {"duration": 5, "env": {"kind": kind, "seed": 3},
                "actors": [{"id": "A", "keys": [{"t": 0, "pos": [0, 0]}, {"t": 5, "pos": [1, -1]}]}]}
        pieces = expand(_BL, spec)
        assert pieces, kind
        assert len({p["id"] for p in pieces}) == len(pieces), kind
        for p in pieces:
            if p.get("_dressing"):
                assert not _footprint_hit(_BL, p, [(0, 0, 0.7), (1, -1, 0.7)]), (kind, p["id"])
        assert spec["legend"] is not None
    # determinism: the same seed builds the same street
    s1 = expand(_BL, {"duration": 5, "env": {"kind": "street", "seed": 7}, "actors": []})
    s2 = expand(_BL, {"duration": 5, "env": {"kind": "street", "seed": 7}, "actors": []})
    assert [p["pos"] for p in s1] == [p["pos"] for p in s2]
    s3 = expand(_BL, {"duration": 5, "env": {"kind": "street", "seed": 8}, "actors": []})
    assert [p["pos"] for p in s1] != [p["pos"] for p in s3]
    print(f"selftest OK — {len(PARTS)} part builders and {len(TEMPLATES)} environments build; dressing stays off "
          f"every path; a seed is deterministic and two seeds differ")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--kinds" in sys.argv:
        print(kinds_text())
        sys.exit(0)
    print(__doc__)
