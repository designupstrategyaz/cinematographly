#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""blocking_kit.py — the blocking render's geometry: furniture, props, rooms and the rigged mannequin
(references/blocking.md §3b).

  python3 blocking_kit.py --selftest      # every kit piece fits its footprint; rooms split around openings

Two halves. The PARTS are plain Python: each kind of set piece or prop is a list of primitives (box,
cylinder, sphere, cone) inside the piece's own footprint, so `blocking.py check` keeps measuring the
same rectangle the render draws. The BUILDERS need Blender (`bpy`): they turn parts into meshes and give
each actor an armature with 17 bones, a body skinned rigidly to it, and a pose solved per frame by
blocking_rig.py. A table has a top and four legs, a chair a seat, legs and a back, a counter a cabinet on
a toe-kick under an overhanging top, a room its walls with the doors and windows cut out — the video
model reads furniture from its silhouette, not from a legend line alone.
"""
from __future__ import annotations
import math, sys

# ── primitives, in the piece's own frame: x across its width, y across its depth (+y = its back), z up from
#    its base. Props use their centre as the origin. ───────────────────────────────────────────────────────
def box(c, s): return ("box", tuple(c), tuple(s))
def cyl(c, r, h, axis="z", r2=None): return ("cyl", tuple(c), (r, r if r2 is None else r2, h), axis)
def sph(c, rx, ry=None, rz=None): return ("sph", tuple(c), (rx, ry or rx, rz or rx))
def cone(c, r1, r2, h, axis="z"): return ("cone", tuple(c), (r1, r2, h), axis)
def ecyl(c, r1, r2, h, depth, axis="y"): return ("ecyl", tuple(c), (r1, r2, h, depth), axis)
# cyl/cone/ecyl: r1 is the radius at the axis's negative end, r2 at its positive end; ecyl's cross-section
# is an ellipse whose second radius is `depth` × the first (for axis "y": depth runs along the frame's Z)


def legs4(w, d, h, t=0.045, inset=0.04):
    x, y = w / 2 - inset - t / 2, d / 2 - inset - t / 2
    return [box((sx * x, sy * y, h / 2), (t, t, h)) for sx in (-1, 1) for sy in (-1, 1)]


EXTRA_PARTS: dict = {}      # kind → fn(w, d, h, piece); blocking_env registers its environments' parts here
MATERIAL_HOOK = None        # fn(bpy, material name, rgb) → a Blender material; set by blocking_look for concept renders


def set_parts(kind: str, w: float, d: float, h: float, piece: dict | None = None) -> list:
    """Primitives for a set piece of footprint w × d and height h (origin: footprint centre, floor)."""
    if kind in EXTRA_PARTS:
        return EXTRA_PARTS[kind](w, d, h, piece or {})
    if kind == "table" or kind == "desk":
        top = 0.04
        out = [box((0, 0, h - top / 2), (w, d, top))]
        if kind == "desk":
            out += [box((-w / 2 + w * 0.15, 0, (h - top) / 2), (w * 0.3, d * 0.92, h - top)),
                    box((w / 2 - 0.025, 0, (h - top) / 2), (0.05, d * 0.92, h - top))]
        else:
            out += legs4(w, d, h - top)
        return out
    if kind == "round_table":
        return [cyl((0, 0, h - 0.02), w / 2, 0.04), cyl((0, 0, (h - 0.04) / 2), 0.05, h - 0.04),
                cyl((0, 0, 0.015), min(w, d) * 0.28, 0.03)]
    if kind in ("counter", "island"):
        kick, top, over = 0.10, 0.04, 0.03
        body_d = d - over
        return [box((0, -over / 2 + 0.03, kick / 2), (w - 0.06, body_d - 0.06, kick)),
                box((0, -over / 2, kick + (h - top - kick) / 2), (w, body_d, h - top - kick)),
                box((0, 0, h - top / 2), (w, d, top))]
    if kind == "chair":
        seat_h, t = 0.45, 0.05
        out = [box((0, 0, seat_h - t / 2), (w, d, t))] + legs4(w, d, seat_h - t, t=0.04, inset=0.02)
        out += [box((sx * (w / 2 - 0.03), d / 2 - 0.03, seat_h + (h - seat_h) / 2), (0.04, 0.04, h - seat_h))
                for sx in (-1, 1)]
        out.append(box((0, d / 2 - 0.03, h - 0.14), (w - 0.06, 0.03, 0.26)))
        return out
    if kind == "stool":
        seat_h = h
        return [cyl((0, 0, seat_h - 0.025), min(w, d) / 2, 0.05)] + legs4(w * 0.85, d * 0.85, seat_h - 0.05, t=0.035) + \
               [box((0, 0, seat_h * 0.35), (w * 0.7, 0.03, 0.03)), box((0, 0, seat_h * 0.35), (0.03, d * 0.7, 0.03))]
    if kind == "sofa":
        base_h, seat_top, arm_w, back_d = 0.20, 0.42, 0.18, 0.20
        out = [box((0, 0, base_h / 2 + 0.06), (w, d, base_h))]
        for sx in (-1, 1):
            out.append(box((sx * (w / 2 - arm_w / 2), 0, 0.31), (arm_w, d, 0.62 - 0.0)))
        inner = w - 2 * arm_w
        for sx in (-1, 1):
            out.append(box((sx * inner / 4, -back_d / 2, (base_h + 0.06 + seat_top) / 2 + 0.02),
                           (inner / 2 - 0.01, d - back_d, seat_top - base_h - 0.06)))
        out.append(box((0, d / 2 - back_d / 2, (seat_top + h) / 2), (w - 2 * arm_w + 0.02, back_d, h - seat_top)))
        out += [box((sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), 0.03), (0.05, 0.05, 0.06)) for sx in (-1, 1) for sy in (-1, 1)]
        return out
    if kind == "bed":
        return [box((0, 0, 0.15), (w, d, 0.30)), box((0, -0.03, 0.30 + (h - 0.30) / 2), (w - 0.04, d - 0.1, h - 0.30)),
                box((0, d / 2 - 0.03, 0.5), (w, 0.06, 1.0)),
                box((-w / 4, d / 2 - 0.30, h + 0.06), (w / 2 - 0.12, 0.35, 0.12)),
                box((w / 4, d / 2 - 0.30, h + 0.06), (w / 2 - 0.12, 0.35, 0.12))]
    if kind == "shelf":
        out = [box((sx * (w / 2 - 0.01), 0, h / 2), (0.02, d, h)) for sx in (-1, 1)]
        out.append(box((0, d / 2 - 0.005, h / 2), (w, 0.01, h)))
        n = 5
        out += [box((0, 0, 0.02 + i * (h - 0.04) / (n - 1)), (w - 0.04, d - 0.01, 0.02)) for i in range(n)]
        return out
    if kind == "fridge":
        split = h * 0.62
        return [box((0, 0.02, split / 2), (w, d - 0.04, split - 0.01)), box((0, 0.02, split + (h - split) / 2), (w, d - 0.04, h - split - 0.01)),
                box((w / 2 - 0.08, -d / 2 + 0.02, split * 0.6), (0.03, 0.04, split * 0.5)),
                box((w / 2 - 0.08, -d / 2 + 0.02, split + (h - split) * 0.3), (0.03, 0.04, (h - split) * 0.4))]
    if kind == "car":
        wr = min(0.34, h * 0.24)
        out = [box((0, 0, wr + (h * 0.42) / 2), (w * 0.98, d, h * 0.42)),
               box((-w * 0.05, 0, wr + h * 0.42 + (h - wr - h * 0.42) / 2), (w * 0.5, d * 0.86, h - wr - h * 0.42))]
        for sx in (-1, 1):
            for sy in (-1, 1):
                out.append(cyl((sx * w * 0.33, sy * (d / 2 - 0.12), wr), wr, 0.22, axis="y"))
        return out
    if kind == "plant":
        pot_h = h * 0.32
        r = min(w, d) / 2
        return [cyl((0, 0, pot_h / 2), r * 0.6, pot_h, r2=r * 0.75), sph((0, 0, pot_h + (h - pot_h) * 0.45), r, r, (h - pot_h) * 0.45),
                sph((r * 0.3, r * 0.2, h - (h - pot_h) * 0.3), r * 0.6, r * 0.6, (h - pot_h) * 0.3)]
    if kind == "lamp":
        return [cyl((0, 0, 0.015), min(w, d) * 0.35, 0.03), cyl((0, 0, h * 0.42), 0.015, h * 0.84),
                cone((0, 0, h - 0.13), min(w, d) / 2, min(w, d) * 0.3, 0.26)]
    if kind == "door":
        return [box((sx * (w / 2 - 0.03), 0, h / 2), (0.06, d, h)) for sx in (-1, 1)] + [box((0, 0, h - 0.03), (w, d, 0.06)),
                box((0, 0, (h - 0.06) / 2), (w - 0.14, min(d, 0.04), h - 0.06))]
    if kind == "window":
        return [box((sx * (w / 2 - 0.03), 0, h / 2), (0.06, d, h)) for sx in (-1, 1)] + \
               [box((0, 0, sz), (w, d, 0.06)) for sz in (0.03, h - 0.03)] + \
               [box((0, 0, h / 2), (0.04, d, h - 0.1)), box((0, 0, h / 2), (w - 0.1, d, 0.04))]
    if kind == "rug":
        return [box((0, 0, h / 2), (w, d, h))]
    if kind == "tv":
        return [box((0, 0, h * 0.6), (w, min(d, 0.06), h * 0.8)), box((0, 0, h * 0.1), (w * 0.3, d, 0.04)),
                box((0, 0, h * 0.15), (0.06, 0.04, h * 0.2))]
    # wall, box, floor_mark, and anything unknown: one solid
    return [box((0, 0, h / 2), (w, d, h))]


def prop_parts(kind: str, w: float, d: float, h: float) -> list:
    """Primitives for a prop, centred on its own centre (it is placed and held by its centre)."""
    if kind == "bottle":
        r = w / 2
        return [cyl((0, 0, -h / 2 + h * 0.31), r, h * 0.62), cone((0, 0, -h / 2 + h * 0.62 + h * 0.07), r, r * 0.45, h * 0.14),
                cyl((0, 0, h / 2 - h * 0.12), r * 0.42, h * 0.16), cyl((0, 0, h / 2 - h * 0.03), r * 0.5, h * 0.06)]
    if kind == "jar":
        return [cyl((0, 0, -h * 0.1), w / 2, h * 0.8), cyl((0, 0, h * 0.4), w / 2 * 1.02, h * 0.2)]
    if kind == "mug":
        r = min(w, d) / 2 * 0.8
        return [cyl((-w * 0.05, 0, 0), r, h), box((r + 0.012 - w * 0.05, 0, 0), (0.02, 0.012, h * 0.6))]
    if kind == "glass":
        return [cyl((0, 0, 0), w / 2 * 0.8, h, r2=w / 2)]
    if kind == "plate":
        return [cyl((0, 0, 0), w / 2, h)]
    if kind == "phone":
        return [box((0, 0, 0), (w, d, h))]
    if kind == "laptop":
        base = 0.016
        ang = math.radians(20)
        sh = h - base
        return [box((0, 0, -h / 2 + base / 2), (w, d, base)),
                box((0, d / 2 - math.sin(ang) * sh / 2 - 0.005, -h / 2 + base + sh / 2), (w, 0.008, sh))]
    if kind == "book":
        return [box((0, 0, 0), (w, d, h))]
    if kind == "bag":
        return [box((0, 0, -h * 0.1), (w, d, h * 0.8)), box((0, 0, h * 0.4), (w * 0.5, 0.015, h * 0.2))]
    if kind == "tube":
        return [cyl((0, 0, -h * 0.05), w / 2, h * 0.9), cyl((0, 0, h * 0.45), w / 2 * 0.7, h * 0.1)]
    return [box((0, 0, 0), (w, d, h))]


def parts_bbox(parts: list) -> tuple:
    lo, hi = [9e9] * 3, [-9e9] * 3
    for p in parts:
        kind, c, s = p[0], p[1], p[2]
        if kind == "box":
            half = (s[0] / 2, s[1] / 2, s[2] / 2)
        elif kind == "sph":
            half = s
        else:
            r, h = max(s[0], s[1]), s[2]
            axis = p[3] if len(p) > 3 else "z"
            half = {"z": (r, r, h / 2), "x": (h / 2, r, r), "y": (r, h / 2, r)}[axis]
        for i in range(3):
            lo[i] = min(lo[i], c[i] - half[i]); hi[i] = max(hi[i], c[i] + half[i])
    return tuple(lo), tuple(hi)


# ── rooms: walls with their openings cut out ────────────────────────────────────────────────────────────
WALLS = ("back", "front", "left", "right")


def room_walls(room: dict) -> list:
    """Wall segments of a `room` set piece, as plain wall pieces in world coordinates (what `check` treats
    as solid), plus the window and door frames as visual-only pieces (`solid: False`)."""
    W, D, H = (float(v) for v in room.get("size", [5.0, 4.0, 2.7]))
    t = float(room.get("thickness", 0.10))
    cx, cy = float(room["pos"][0]), float(room["pos"][1])
    rot = math.radians(float(room.get("rot", 0)))
    walls = room.get("walls", ["back", "left", "right"])
    col = room.get("color", "grey")
    out = []

    def place(lx, ly, z, size, wall_rot, ident, solid=True, kind="wall", extra=None):
        wx = cx + lx * math.cos(rot) - ly * math.sin(rot)
        wy = cy + lx * math.sin(rot) + ly * math.cos(rot)
        piece = {"id": ident, "kind": kind, "pos": [round(wx, 4), round(wy, 4)], "z": round(z, 4),
                 "size": [round(size[0], 4), round(size[1], 4), round(size[2], 4)],
                 "rot": math.degrees(rot) + wall_rot, "color": col, "solid": solid, "room": room["id"]}
        if extra:
            piece.update(extra)
        out.append(piece)

    for wall in walls:
        if wall in ("back", "front"):
            L, sgn = W + (2 * t if wall == "back" else 0), (1 if wall == "back" else -1)
            base = lambda a: (a, sgn * (D / 2 + t / 2))
            wrot = 0.0
        else:
            L, sgn = D + 2 * t, (-1 if wall == "left" else 1)
            base = lambda a: (sgn * (W / 2 + t / 2), a)
            wrot = 90.0
        ops = sorted((o for o in room.get("openings", []) if o.get("wall") == wall), key=lambda o: float(o.get("at", 0)))
        cur = -L / 2
        for i, o in enumerate(ops):
            ow, oh = float(o.get("w", 0.9)), float(o.get("h", 2.1))
            sill = float(o.get("sill", 0.0 if o.get("kind", "door") == "door" else 0.9))
            a0, a1 = float(o.get("at", 0)) - ow / 2, float(o.get("at", 0)) + ow / 2
            if a0 > cur:
                lx, ly = base((cur + a0) / 2)
                place(lx, ly, 0.0, (a0 - cur, t, H), wrot, f"{room['id']}.{wall}.{i}a")
            if sill > 0:
                lx, ly = base((a0 + a1) / 2)
                place(lx, ly, 0.0, (ow, t, sill), wrot, f"{room['id']}.{wall}.{i}sill")
            if sill + oh < H:
                lx, ly = base((a0 + a1) / 2)
                place(lx, ly, sill + oh, (ow, t, H - sill - oh), wrot, f"{room['id']}.{wall}.{i}head")
            lx, ly = base((a0 + a1) / 2)
            place(lx, ly, sill, (ow, t * 0.6, oh), wrot, f"{room['id']}.{wall}.{i}{o.get('kind', 'door')}",
                  solid=False, kind=o.get("kind", "door"), extra={"open": o.get("open", 0)})
            cur = a1
        if cur < L / 2:
            lx, ly = base((cur + L / 2) / 2)
            place(lx, ly, 0.0, (L / 2 - cur, t, H), wrot, f"{room['id']}.{wall}.end")
    if room.get("ceiling"):
        place(0.0, 0.0, H, (W + 2 * t, D + 2 * t, t), 0.0, f"{room['id']}.ceiling")
    return out


# ── precise geometry: built from the client's numbers, in plain Python (the checks read the same bbox) ──
def lathe(profile: list, segments: int = 48, m: str | None = None) -> tuple:
    """A turned solid: `profile` is [[radius, z], …] from the bottom up (a bottle, a jar, a lamp base, a
    glass), revolved about z. Radii of 0 close the ends. Returns a "mesh" primitive."""
    rings = []
    verts = []
    for r, z in profile:
        r, z = float(r), float(z)
        if r <= 1e-6:
            rings.append([len(verts)]); verts.append((0.0, 0.0, z))
        else:
            ring = []
            for i in range(segments):
                a = 2 * math.pi * i / segments
                ring.append(len(verts)); verts.append((r * math.cos(a), r * math.sin(a), z))
            rings.append(ring)
    faces = []
    for ra, rb in zip(rings, rings[1:]):
        if len(ra) == 1 and len(rb) == 1:
            continue
        if len(ra) == 1:
            faces += [[ra[0], rb[(i + 1) % len(rb)], rb[i]] for i in range(len(rb))]
        elif len(rb) == 1:
            faces += [[ra[i], ra[(i + 1) % len(ra)], rb[0]] for i in range(len(ra))]
        else:
            faces += [[ra[i], ra[(i + 1) % len(ra)], rb[(i + 1) % len(rb)], rb[i]] for i in range(len(ra))]
    if len(rings[0]) > 1:
        faces.append(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        faces.append(list(rings[-1]))
    opts = {"m": m} if m else {}
    return ("mesh", (0.0, 0.0, 0.0), (verts, faces), opts)


def _area2(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def _ear_clip(poly: list) -> list:
    """Triangles of a simple polygon (counter-clockwise), by ear clipping."""
    idx = list(range(len(poly)))
    tris = []

    def inside(p, a, b, c):
        def s(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 1e-12:
                continue
            if any(inside(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def extrude(outline: list, height: float, z0: float = 0.0, m: str | None = None) -> tuple:
    """A prism: `outline` [[x, y], …] (any simple polygon, either winding) pushed up `height` from z0 —
    a counter of an exact shape, a plinth, a facade from its plan, a product with a flat profile."""
    poly = [(float(x), float(y)) for x, y in outline]
    if _area2(poly) < 0:
        poly.reverse()
    n = len(poly)
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z0 + height) for x, y in poly]
    faces = [[n + i for i in t] for t in _ear_clip(poly)] + [[t[2], t[1], t[0]] for t in _ear_clip(poly)]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    opts = {"m": m} if m else {}
    return ("mesh", (0.0, 0.0, 0.0), (verts, faces), opts)


def mesh_bbox(prim) -> tuple:
    vs = prim[2][0]
    return (tuple(min(v[i] for v in vs) for i in range(3)), tuple(max(v[i] for v in vs) for i in range(3)))


def shape_prims(shape: dict) -> list:
    """A piece's `shape` → primitives: {"lathe": [[r, z]…], "segments"} · {"extrude": {"outline", "height"}} ·
    {"parts": [{"lathe"…} | {"extrude"…} | {"box": [cx, cy, cz, w, d, h]} …]} · each may name its material "m"."""
    out = []
    items = shape.get("parts") or [shape]
    for it in items:
        if "lathe" in it:
            out.append(lathe(it["lathe"], int(it.get("segments", 48)), it.get("m")))
        elif "extrude" in it:
            e = it["extrude"]
            out.append(extrude(e["outline"], float(e["height"]), float(e.get("z", 0.0)), it.get("m")))
        elif "box" in it:
            cx, cy, cz, w, d, h = (float(v) for v in it["box"])
            out.append(box((cx, cy, cz), (w, d, h)) + (({"m": it["m"]},) if it.get("m") else ()))
    return out


def prims_extent(prims: list) -> tuple:
    """(w, d, h) of a piece made of these primitives, about its own origin: the footprint is taken
    symmetric about the origin (the checks treat a piece as a rectangle centred on `pos`), the height from
    the floor up."""
    xs, ys, zs = [0.0], [0.0], [0.0]
    for p in prims:
        if p[0] == "mesh":
            (x0, y0, z0), (x1, y1, z1) = mesh_bbox(p)
        else:
            c = p[1]
            if p[0] == "box":
                hx, hy, hz = (v / 2 for v in p[2])
            elif p[0] == "sph":
                hx, hy, hz = p[2]
            else:                                     # cyl / cone / ecyl: radius, radius, height along an axis
                r = max(p[2][0], p[2][1]); hh = p[2][2] / 2
                ax = p[3] if len(p) > 3 and isinstance(p[3], str) else "z"
                hx, hy, hz = {"z": (r, r, hh), "x": (hh, r, r), "y": (r, hh, r)}[ax]
            x0, y0, z0, x1, y1, z1 = c[0] - hx, c[1] - hy, c[2] - hz, c[0] + hx, c[1] + hy, c[2] + hz
        xs += [x0, x1]; ys += [y0, y1]; zs += [z0, z1]
    return (round(2 * max(abs(v) for v in xs), 4), round(2 * max(abs(v) for v in ys), 4), round(max(zs), 4))


def shape_footprints(shape: dict) -> list:
    """The ground outlines of a shape, in its own frame: an extrusion's outline, a box's rectangle, a turned
    solid's widest circle (24 sides). The checks and the map use these, not the bounding rectangle, so an
    L-shaped counter leaves its notch free."""
    out = []
    for it in shape.get("parts") or [shape]:
        if "extrude" in it:
            out.append([(float(x), float(y)) for x, y in it["extrude"]["outline"]])
        elif "box" in it:
            cx, cy, _, w, d, _ = (float(v) for v in it["box"])
            out.append([(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)])
        elif "lathe" in it:
            r = max(float(q[0]) for q in it["lathe"])
            out.append([(r * math.cos(2 * math.pi * i / 24), r * math.sin(2 * math.pi * i / 24)) for i in range(24)])
    return out


def poly_contains(poly: list, x: float, y: float, pad: float = 0.0) -> bool:
    """Inside the polygon, or within `pad` of its edge."""
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    if inside or pad <= 0:
        return inside
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        f = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        if math.hypot(x - x1 - f * dx, y - y1 - f * dy) <= pad:
            return True
    return False


def shift_prims(prims: list, d: tuple) -> list:
    """The same primitives moved by d (a mesh's vertices move; every other primitive moves its centre)."""
    out = []
    for p in prims:
        if p[0] == "mesh":
            verts, faces = p[2]
            out.append(("mesh", p[1], ([(v[0] + d[0], v[1] + d[1], v[2] + d[2]) for v in verts], faces)) + tuple(p[3:]))
        else:
            c = p[1]
            out.append((p[0], (c[0] + d[0], c[1] + d[1], c[2] + d[2])) + tuple(p[2:]))
    return out


def plan_inside(piece: dict, x: float, y: float) -> bool:
    """Is (x, y) inside a closed floor plan (even–odd rule)?"""
    ox, oy = (float(v) for v in piece.get("pos", [0, 0]))
    pts = [(float(a) + ox, float(b) + oy) for a, b in piece["points"]]
    inside = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def plan_walls(piece: dict) -> list:
    """A floor plan: walls along `points` ([[x, y], …] from `pos`, `closed`), `height`, `thickness`, with
    `openings` [{"segment": i, "at": metres from the segment's start to the opening's centre, "w", "h",
    "sill", "kind": door|window, "open"}] — any room shape, built from the plan's own numbers. `ceiling`
    closes the top (an extruded slab of the same outline)."""
    ox, oy = (float(v) for v in piece.get("pos", [0, 0]))
    pts = [(float(p[0]) + ox, float(p[1]) + oy) for p in piece["points"]]
    if piece.get("closed", True):
        pts = pts + [pts[0]]
    H = float(piece.get("height", 2.7))
    t = float(piece.get("thickness", 0.12))
    out = []
    for si, (a, b) in enumerate(zip(pts, pts[1:])):
        L = math.dist(a, b)
        if L < 1e-6:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        rot = math.degrees(math.atan2(uy, ux))
        ops = sorted((o for o in piece.get("openings", []) if int(o.get("segment", -1)) == si), key=lambda o: float(o["at"]))
        cuts = [0.0]
        for o in ops:
            c, w = float(o["at"]), float(o.get("w", 0.9))
            cuts += [c - w / 2, c + w / 2]
        cuts.append(L)

        def put(s0, s1, z, h, ident, solid=True, kind="wall", extra=None):
            mid = (s0 + s1) / 2
            p = {"id": f"{piece['id']}.s{si}.{ident}", "kind": kind, "pos": [a[0] + ux * mid, a[1] + uy * mid],
                 "rot": rot, "size": [s1 - s0, t, h], "z": z, "color": piece.get("color", "grey"), "solid": solid,
                 "room": piece["id"]}
            if kind == "wall" and piece.get("material"):
                p["material"] = piece["material"]
            if extra:
                p.update(extra)
            if not solid:
                p["walkable"] = kind == "door"
            out.append(p)
        for i in range(0, len(cuts), 2):
            if cuts[i + 1] - cuts[i] > 1e-6:
                put(cuts[i], cuts[i + 1], 0.0, H, f"{i // 2}")
        for j, o in enumerate(ops):
            c, w, oh = float(o["at"]), float(o.get("w", 0.9)), float(o.get("h", 2.1))
            sill = float(o.get("sill", 0.0 if o.get("kind", "door") == "door" else 0.9))
            if sill > 0:
                put(c - w / 2, c + w / 2, 0.0, sill, f"{j}sill")
            if sill + oh < H:
                put(c - w / 2, c + w / 2, sill + oh, H - sill - oh, f"{j}head")
            put(c - w / 2, c + w / 2, sill, oh, f"{j}{o.get('kind', 'door')}", solid=False, kind=o.get("kind", "door"),
                extra={"open": o.get("open", 0)})
    if piece.get("ceiling") and piece.get("closed", True):
        slab = extrude([(x - ox, y - oy) for x, y in pts[:-1]], t, H)
        w_, d_, _ = prims_extent([slab])
        out.append({"id": f"{piece['id']}.ceiling", "kind": "wall", "pos": [ox, oy], "rot": 0, "size": [w_, d_, t],
                    "z": 0.0, "color": piece.get("color", "grey"), "solid": False, "walkable": True,
                    "room": piece["id"], "_prims": [slab], "material": piece.get("material")})
    return out


# ── imported models: a client's CAD export, a CC0 asset — fitted to the size the spec gives it ───────────────
MODEL_EXTS = (".blend", ".glb", ".gltf", ".obj", ".fbx", ".stl", ".ply")
LICENCES_OK = ("CC0", "client", "own")              # usable with no conditions
LICENCES_CREDIT = ("CC-BY", "CC-BY-SA")             # usable; the delivery credits the author and source


def import_model(bpy, piece: dict, rgb: tuple, matrix, keep_materials: bool, origin: str = "base"):
    """Bring `piece["model"]["file"]` in, drop its cameras and lights, scale it to `size` ("fit": "contain"
    keeps proportions inside the box, "stretch" fills it), stand it on z = 0 centred on its origin, and put
    it under one empty named after the piece (props are keyed on that empty). In the blocking render every
    mesh takes the legend colour; in a concept render the model keeps its own materials (or `material`)."""
    import os
    import mathutils
    md = piece["model"]
    path = os.path.expanduser(md["file"])
    ext = os.path.splitext(path)[1].lower()
    before = set(bpy.data.objects)
    if ext == ".blend":
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            want = md.get("objects")
            dst.objects = [n for n in src.objects if not want or n in want]
        for o in dst.objects:
            if o is not None and o.name not in bpy.context.scene.collection.all_objects:
                bpy.context.scene.collection.objects.link(o)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    else:
        raise ValueError(f"{piece['id']}: model type {ext!r} is not one of {', '.join(MODEL_EXTS)}")
    new = [o for o in bpy.data.objects if o not in before]
    for o in [o for o in new if o.type in ("CAMERA", "LIGHT")]:
        new.remove(o); bpy.data.objects.remove(o, do_unlink=True)
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        raise ValueError(f"{piece['id']}: {os.path.basename(path)} holds no mesh")
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ mathutils.Vector(c) for o in meshes for c in o.bound_box]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    ext_ = [max(hi[i] - lo[i], 1e-6) for i in range(3)]
    W, D, H = (float(v) for v in piece["size"])
    if piece.get("fit", "contain") == "stretch":
        sc_ = (W / ext_[0], D / ext_[1], H / ext_[2])
    else:
        k = min(W / ext_[0], D / ext_[1], H / ext_[2]); sc_ = (k, k, k)
    lift = ext_[2] * sc_[2] / 2 if origin == "centre" else 0.0   # a prop is placed by its centre, a set piece by its base
    pre = mathutils.Matrix.Translation((0, 0, -lift)) @ mathutils.Matrix.Diagonal((*sc_, 1.0)) @ \
        mathutils.Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
    root = bpy.data.objects.new(piece["id"], None)
    bpy.context.scene.collection.objects.link(root)
    root.matrix_world = matrix
    for o in new:
        if o.parent is None or o.parent not in new:
            mw = o.matrix_world.copy()
            o.parent = root
            o.matrix_parent_inverse = mathutils.Matrix.Identity(4)
            o.matrix_basis = pre @ mw
    for o in meshes:
        o.color = (*rgb, 1.0)
        if MATERIAL_HOOK and (piece.get("material") or not keep_materials or not o.data.materials):
            o.data.materials.clear()
            o.data.materials.append(MATERIAL_HOOK(bpy, piece.get("material") or "default", rgb))
    root["fitted_scale"] = list(sc_)
    root["source_extent"] = ext_
    return root


# ── Blender builders ─────────────────────────────────────────────────────────────────────────────────────
def _mx(c, axis="z", scale=(1, 1, 1)):
    import mathutils
    rot = {"z": mathutils.Matrix.Identity(4), "x": mathutils.Matrix.Rotation(math.pi / 2, 4, "Y"),
           "y": mathutils.Matrix.Rotation(-math.pi / 2, 4, "X")}[axis]          # local +Z → +Y
    return mathutils.Matrix.Translation(c) @ rot @ mathutils.Matrix.Diagonal((*scale, 1.0))


def prim_info(p) -> tuple:
    """(axis, options) of a primitive: the axis string for cylinders and cones, and the trailing options
    dict ({"m": material, "rx"/"ry"/"rz": degrees about the part's own centre})."""
    opts = p[-1] if isinstance(p[-1], dict) else {}
    axis = p[3] if len(p) > 3 and isinstance(p[3], str) else "z"
    return axis, opts


def add_prims(bm, prims, base=None, group=None, dl=None, seg=20, mats=None, default_mat=None):
    """Append primitives to a bmesh, transformed by `base` (4×4); returns the new verts. `mats` maps a
    material name to a slot index; each part's faces get its material's slot (`default_mat` otherwise)."""
    import bmesh, mathutils
    base = base if base is not None else mathutils.Matrix.Identity(4)
    new = []
    for p in prims:
        kind, c, s = p[0], p[1], p[2]
        axis, opts = prim_info(p)
        rot = mathutils.Matrix.Identity(4)
        for ax in ("x", "y", "z"):
            if opts.get("r" + ax):
                rot = rot @ mathutils.Matrix.Rotation(math.radians(float(opts["r" + ax])), 4, ax.upper())
        place = base @ mathutils.Matrix.Translation(c) @ rot @ mathutils.Matrix.Translation([-v for v in c])
        if kind == "box":
            r = bmesh.ops.create_cube(bm, size=1.0, matrix=place @ _mx(c, scale=s))
        elif kind == "sph":
            r = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(8, seg // 2), radius=1.0,
                                          matrix=place @ _mx(c, scale=s))
        elif kind == "cyl":
            r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=s[0], radius2=s[1],
                                      depth=s[2], matrix=place @ _mx(c, axis=axis))
        elif kind == "ecyl":
            r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=s[0], radius2=s[1],
                                      depth=s[2], matrix=place @ _mx(c, axis=axis, scale=(1, s[3], 1)))
        elif kind == "mesh":                    # precise geometry: (verts, faces) already in the part's frame
            vs_ = [bm.verts.new(place @ mathutils.Vector(v)) for v in s[0]]
            for f in s[1]:
                try:
                    bm.faces.new([vs_[i] for i in f])
                except ValueError:
                    pass
            r = {"verts": vs_}
        else:
            r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=s[0], radius2=s[1],
                                      depth=s[2], matrix=place @ _mx(c, axis=axis))
        vs = r["verts"]
        if mats:
            mi = mats.get(opts.get("m") or default_mat, 0)
            faces = {f for v in vs for f in v.link_faces}
            for f in faces:
                f.material_index = mi
        if group is not None and dl is not None:
            for v in vs:
                v[dl][group] = 1.0
        new += vs
    return new


def mesh_object(bpy, name, prims, rgb, matrix=None, material=None):
    import bmesh
    bm = bmesh.new()
    mats = None
    names = []
    if MATERIAL_HOOK:
        names = sorted({(prim_info(p)[1].get("m") or material or "default") for p in prims})
        mats = {n: i for i, n in enumerate(names)}
    add_prims(bm, prims, mats=mats, default_mat=material or "default")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for poly in me.polygons:
        poly.use_smooth = False
    for n in names:
        me.materials.append(MATERIAL_HOOK(bpy, n, rgb))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.color = (*rgb, 1.0)
    if matrix is not None:
        ob.matrix_world = matrix
    return ob


# The mannequin: bones, the joints they run between, and the segments skinned to each (radii in fractions of
# height, the segment's own +Y running from the bone's head to its tail).
BONES = [  # name, head joint, tail joint, roll reference
    ("pelvis", "pelvis", "pelvis_top", "fwd"), ("spine", "pelvis", "neck_base", "fwd"),
    ("neck", "neck_base", "head_base", "head_fwd"), ("head", "head_base", "head_top", "head_fwd"),
    ("upperarm_L", "shoulder_L", "elbow_L", "left"), ("forearm_L", "elbow_L", "wrist_L", "left"),
    ("hand_L", "wrist_L", "hand_tip_L", "left"),
    ("upperarm_R", "shoulder_R", "elbow_R", "left"), ("forearm_R", "elbow_R", "wrist_R", "left"),
    ("hand_R", "wrist_R", "hand_tip_R", "left"),
    ("thigh_L", "hip_L", "knee_L", "left"), ("shin_L", "knee_L", "ankle_L", "left"), ("foot_L", "ankle_L", "toe_L", "up"),
    ("thigh_R", "hip_R", "knee_R", "left"), ("shin_R", "knee_R", "ankle_R", "left"), ("foot_R", "ankle_R", "toe_R", "up"),
]


def bone_matrix(head, tail, ref):
    """Bone frame: +Y from head to tail, +X = Y × ref, +Z = X × Y (falls back when Y is parallel to ref)."""
    import mathutils
    y = mathutils.Vector(tail) - mathutils.Vector(head)
    L = y.length or 1e-6
    y.normalize()
    r = mathutils.Vector(ref)
    if abs(y.dot(r.normalized())) > 0.97:
        r = mathutils.Vector((0, 0, 1)) if abs(y.z) < 0.9 else mathutils.Vector((1, 0, 0))
    x = y.cross(r).normalized()
    z = x.cross(y).normalized()
    m = mathutils.Matrix(((x.x, y.x, z.x, head[0]), (x.y, y.y, z.y, head[1]), (x.z, y.z, z.z, head[2]), (0, 0, 0, 1)))
    return m, L


def joint_refs(j: dict) -> dict:
    """The joint dict plus the derived points and vectors the bone table needs."""
    out = dict(j)
    out["pelvis_top"] = tuple(j["pelvis"][i] + j["spine_up"][i] * 0.12 for i in range(3))
    return out


def body_segments(H: float, build: float, rest: dict) -> dict:
    """Primitives per bone, in that bone's frame, for an actor of height H — an artist's mannequin with the
    masses of a body (ribcage, abdomen, hips, deltoids, thighs and calves, a jaw and a nose) rather than a
    stack of balls. Bone frames (bone_matrix): Y runs along the bone; torso and head: X = the actor's left,
    Z = forward; arms and legs: X = forward (anterior), Z = the actor's left; foot: built level (see
    build_actor), X = right, Z = up. Lengths follow the Drillis & Contini fractions the rig uses; the girths
    are a mannequin's (an assumption, not a measured table)."""
    def L(bone):
        a, b = rest[BONES_BY[bone][0]], rest[BONES_BY[bone][1]]
        return math.dist(a, b)
    k = build
    sp = L("spine")
    segs = {
        "pelvis": [sph((0, -0.01 * H, -0.004 * H), 0.090 * H * k, 0.062 * H, 0.064 * H)],               # hips
        "spine": [ecyl((0, 0.095 * sp, 0.003 * H), 0.074 * H * k, 0.084 * H * k, 0.25 * sp, 0.72),       # abdomen
                  sph((0, 0.62 * sp, 0.006 * H), 0.096 * H * k, 0.098 * H, 0.068 * H),                  # ribcage
                  sph((0, 0.90 * sp, -0.006 * H), 0.112 * H * k, 0.032 * H, 0.052 * H)],                # shoulder girdle
        "neck": [ecyl((0, 0.035 * H, 0), 0.034 * H, 0.030 * H, 0.08 * H, 0.95)],
        "head": [sph((0, 0.076 * H, -0.006 * H), 0.046 * H, 0.055 * H, 0.056 * H),                     # cranium
                 sph((0, 0.044 * H, 0.016 * H), 0.037 * H, 0.044 * H, 0.041 * H),                      # face and jaw
                 cone((0, 0.054 * H, 0.059 * H), 0.009 * H, 0.002 * H, 0.020 * H, axis="z"),           # nose
                 sph((0.046 * H, 0.066 * H, -0.004 * H), 0.006 * H, 0.016 * H, 0.010 * H),             # ears
                 sph((-0.046 * H, 0.066 * H, -0.004 * H), 0.006 * H, 0.016 * H, 0.010 * H)],
    }
    fl = P_FOOT * H
    for s in "LR":
        ua, fa = L(f"upperarm_{s}"), P_FOREARM * H
        th, sh = L(f"thigh_{s}"), L(f"shin_{s}")
        segs[f"upperarm_{s}"] = [sph((0, 0.035 * H, 0), 0.036 * H, 0.052 * H, 0.030 * H),               # deltoid
                                 ecyl((0, ua / 2, 0), 0.029 * H, 0.022 * H, ua, 0.92),
                                 sph((0, ua, 0), 0.022 * H)]                                           # elbow
        segs[f"forearm_{s}"] = [ecyl((0, fa * 0.45, 0), 0.025 * H, 0.020 * H, fa * 0.9, 0.82),
                                ecyl((0, fa * 0.93, 0), 0.020 * H, 0.016 * H, fa * 0.16, 0.75)]       # wrist
        segs[f"hand_{s}"] = [sph((0, 0.040 * H, 0), 0.027 * H, 0.044 * H, 0.012 * H),                   # palm (thin across)
                             sph((0, 0.083 * H, 0.002 * H), 0.022 * H, 0.028 * H, 0.010 * H)]          # fingers
        segs[f"thigh_{s}"] = [ecyl((0, th * 0.48, 0), 0.052 * H, 0.034 * H, th * 0.96, 0.95),
                              sph((0, th, 0), 0.032 * H)]                                              # knee
        segs[f"shin_{s}"] = [ecyl((0, sh * 0.5, 0), 0.032 * H, 0.021 * H, sh, 0.95),
                             sph((-0.010 * H, sh * 0.30, 0), 0.034 * H, 0.075 * H, 0.031 * H)]         # calf
        segs[f"foot_{s}"] = [sph((0, 0.25 * fl, -0.018 * H), 0.031 * H, 0.52 * fl, 0.021 * H),         # sole and shoe
                             sph((0, 0.08 * fl, -0.012 * H), 0.026 * H, 0.32 * fl, 0.028 * H)]         # instep
    return segs


P_FOOT, P_FOREARM = 0.152, 0.146      # Drillis & Contini fractions (blocking_rig.P)


BONES_BY = {b[0]: (b[1], b[2], b[3]) for b in BONES}


# ── the mannequin body: five smooth metaball surfaces (torso with head, two arms, two legs) ───────────────
MB_VISIBLE = 0.575     # a lone metaball element's visible radius per unit radius (stiffness 2, threshold 0.6; measured)

# Limbs are separate surfaces that sink into the torso at the shoulder and hip, as on an artist's mannequin:
# one merged surface webs the arm to the ribs and tears there when the arm moves. Within a part, a vertex
# blends between neighbouring bones so elbows, knees, the waist and the neck bend smoothly.
PART_BONES = {"torso": ("pelvis", "spine", "neck", "head"),
              "arm_L": ("upperarm_L", "forearm_L", "hand_L"), "arm_R": ("upperarm_R", "forearm_R", "hand_R"),
              "leg_L": ("thigh_L", "shin_L", "foot_L"), "leg_R": ("thigh_R", "shin_R", "foot_R")}
ADJ = {"pelvis": ("spine",), "spine": ("pelvis", "neck"), "neck": ("spine", "head"), "head": ("neck",),
       "upperarm_L": ("forearm_L",), "forearm_L": ("upperarm_L", "hand_L"), "hand_L": ("forearm_L",),
       "upperarm_R": ("forearm_R",), "forearm_R": ("upperarm_R", "hand_R"), "hand_R": ("forearm_R",),
       "thigh_L": ("shin_L",), "shin_L": ("thigh_L", "foot_L"), "foot_L": ("shin_L",),
       "thigh_R": ("shin_R",), "shin_R": ("thigh_R", "foot_R"), "foot_R": ("shin_R",)}
ROOTED = {"neck"}      # below the neck's root joint is the trapezius, which follows the spine


def _v(a, b=(0, 0, 0), k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def _u(a):
    n = math.sqrt(sum(x * x for x in a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def mannequin_elements(J: dict, H: float, k: float = 1.0) -> list:
    """Metaball elements for the A-pose skeleton J (blocking_rig.Rig.canonical: +X forward, +Y left, +Z up),
    each (part, kind, centre, sizes, extra): "ball" (visible radius), "ell" (visible half-axes along X, Y,
    Z; extra = stiffness), "cap" (from, to; extra = visible radius), "hand" (half-axes along the hand,
    across it and through the palm; extra = the hand's direction and the palm's normal); "neg" cuts (the
    eye sockets). The girths are a mannequin's, set by eye against the Drillis & Contini lengths (an
    assumption, not a measured table)."""
    h = lambda x: x * H
    P0, NB, HB = J["pelvis"], J["neck_base"], J["head_base"]
    T = "torso"
    out = [
        (T, "ell", _v(P0, (h(-0.005), 0, h(0.005))), (h(0.062), h(0.095) * k, h(0.06)), None),        # hips
        (T, "ell", _v(P0, (0, 0, h(0.095))), (h(0.058), h(0.08) * k, h(0.085)), None),                 # waist
        (T, "ell", _v(P0, (h(0.006), 0, h(0.175))), (h(0.07), h(0.094) * k, h(0.088)), None),          # ribcage
        (T, "ell", _v(P0, (h(0.012), 0, h(0.235))), (h(0.06), h(0.098) * k, h(0.045)), None),          # chest
        (T, "cap", _v(NB, (h(-0.008), h(-0.075) * k, h(-0.022))), _v(NB, (h(-0.008), h(0.075) * k, h(-0.022))), h(0.028)),
        (T, "ell", _v(NB, (h(-0.012), 0, h(-0.012))), (h(0.036), h(0.055), h(0.028)), None),           # trapezius
        (T, "cap", _v(NB, (h(-0.008), 0, h(-0.02))), _v(HB, (h(-0.006), 0, h(0.012))), h(0.028)),     # neck
        (T, "ell", _v(HB, (h(-0.004), 0, h(0.075))), (h(0.058), h(0.047), h(0.06)), None),            # cranium
        (T, "ell", _v(HB, (h(0.016), 0, h(0.035))), (h(0.044), h(0.039), h(0.037)), 3.0),             # jaw
        (T, "ell", _v(HB, (h(0.057), 0, h(0.048))), (h(0.009), h(0.007), h(0.014)), 3.0),             # nose
        (T, "ell", _v(HB, (h(0.047), 0, h(0.075))), (h(0.007), h(0.028), h(0.006)), None),            # brow
    ]
    for sg in (-1.0, 1.0):
        out += [(T, "ell", _v(P0, (h(-0.035), sg * h(0.045), h(-0.025))), (h(0.05), h(0.05), h(0.06)), None),  # glutes
                (T, "neg", _v(HB, (h(0.058), sg * h(0.018), h(0.063))), h(0.008), None),             # eye sockets
                (T, "ell", _v(HB, (h(-0.004), sg * h(0.048), h(0.06))), (h(0.012), h(0.006), h(0.018)), 3.0)]  # ears
    for s in "LR":
        A_ = "arm_" + s
        S, E, W, Tp = J[f"shoulder_{s}"], J[f"elbow_{s}"], J[f"wrist_{s}"], J[f"hand_tip_{s}"]
        d = _u(_v(E, S, -1)); d2 = _u(_v(W, E, -1))
        lat = (0.0, 1.0 if s == "L" else -1.0, 0.0)
        dl = sum(lat[i] * d2[i] for i in range(3))
        n = _u(tuple(-(lat[i] - d2[i] * dl) for i in range(3)))       # the palm faces in, toward the body
        hd = math.dist(W, Tp)
        out += [(A_, "ball", _v(S, d, h(0.022)), h(0.036), None),                                    # deltoid
                (A_, "cap", S, E, h(0.031)),
                (A_, "cap", E, _v(E, d2, math.dist(E, W) * 0.55), h(0.025)),                          # forearm, tapering
                (A_, "cap", _v(E, d2, math.dist(E, W) * 0.55), W, h(0.019)),                          # to the wrist
                (A_, "ball", _v(E, d2, h(0.04)), h(0.028), None),
                (A_, "hand", _v(W, d2, hd * 0.47), (hd * 0.47, h(0.025), h(0.009)), (d2, n))]
        L_ = "leg_" + s
        Hj, K, A, Tt = J[f"hip_{s}"], J[f"knee_{s}"], J[f"ankle_{s}"], J[f"toe_{s}"]
        dk = _v(K, Hj, -1); da = _v(A, K, -1)
        fwd_f = _u((Tt[0] - A[0], Tt[1] - A[1], 0.0))
        fl = 0.152 * H
        out += [(L_, "ell", _v(_v(Hj, dk, 0.3), (h(0.004), 0, 0)), (h(0.056), h(0.055), h(0.09)), None),  # upper thigh
                (L_, "cap", Hj, K, h(0.042)), (L_, "ball", K, h(0.033), None),
                (L_, "cap", K, A, h(0.028)),
                (L_, "ell", _v(_v(K, da, 0.3), (h(-0.012), 0, 0)), (h(0.034), h(0.032), h(0.07)), None),   # calf
                (L_, "ball", A, h(0.024), None),
                (L_, "ell", _v(_v(A, fwd_f, fl * 0.25), (0, 0, h(-0.02))), (fl * 0.52, h(0.03), h(0.02)), 3.0)]  # foot
    return out


def mannequin_mesh(bpy, J: dict, H: float, k: float = 1.0, name: str = "body"):
    """Build the five metaball parts in the A-pose and join them into one plain mesh. Returns (mesh, part
    of each vertex). Each part is its own metaball family (a distinct name with no dot), so parts do not
    melt into each other."""
    import bmesh
    from mathutils import Vector, Quaternion
    els = mannequin_elements(J, H, k)
    bm_all = bmesh.new()
    part_of = []
    for pi, part in enumerate(PART_BONES):
        fam = f"mb{abs(hash(name)) % 100000}p{pi}"
        mb = bpy.data.metaballs.new(fam)
        mb.resolution = 0.005 * H
        mb.threshold = 0.6
        ob = bpy.data.objects.new(fam, mb)
        bpy.context.scene.collection.objects.link(ob)
        for prt, kind, c, sz, extra in els:
            if prt != part:
                continue
            if kind in ("ball", "neg"):
                e = mb.elements.new(type="BALL"); e.co = c; e.radius = sz / MB_VISIBLE
                e.use_negative = kind == "neg"
            elif kind == "ell":
                m = max(sz)
                e = mb.elements.new(type="ELLIPSOID"); e.co = c; e.radius = m / MB_VISIBLE
                e.size_x, e.size_y, e.size_z = sz[0] / m, sz[1] / m, sz[2] / m
                if extra:
                    e.stiffness = extra
            elif kind == "cap":
                a_, b_ = Vector(c), Vector(sz)
                e = mb.elements.new(type="CAPSULE"); e.co = (a_ + b_) / 2; e.radius = extra / MB_VISIBLE
                e.size_x = (b_ - a_).length / 2
                e.rotation = Vector((1, 0, 0)).rotation_difference(b_ - a_)
            elif kind == "hand":
                d, nrm = Vector(extra[0]), Vector(extra[1])
                q = Vector((1, 0, 0)).rotation_difference(d)
                yax, zax = q @ Vector((0, 1, 0)), q @ Vector((0, 0, 1))
                q = Quaternion(d, -math.atan2(nrm.dot(yax), nrm.dot(zax))) @ q   # thin axis along the palm normal
                m = max(sz)
                e = mb.elements.new(type="ELLIPSOID"); e.co = c; e.radius = m / MB_VISIBLE; e.stiffness = 2.5
                e.size_x, e.size_y, e.size_z = sz[0] / m, sz[1] / m, sz[2] / m
                e.rotation = q
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        me_p = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        n0 = len(bm_all.verts)
        bm_all.from_mesh(me_p)
        part_of += [part] * (len(bm_all.verts) - n0)
        bpy.data.meshes.remove(me_p)
        bpy.data.objects.remove(ob)
        bpy.data.metaballs.remove(mb)
    me = bpy.data.meshes.new(name)
    bm_all.to_mesh(me); bm_all.free()
    for poly in me.polygons:
        poly.use_smooth = True
    return me, part_of


def skin_weights(verts: list, J: dict, H: float, parts: list | None = None) -> list:
    """Per vertex, [(bone, weight)]: the nearest bone of its part, blended with the part's bone across the
    nearest joint (Gaussian on the distance difference, σ = 3 % of height)."""
    Jr = joint_refs(J)
    segs = {name: (Jr[h], Jr[t]) for name, h, t, _ in BONES}
    sigma = 0.03 * H
    out = []
    for vi, p in enumerate(verts):
        bones = PART_BONES[parts[vi]] if parts else tuple(segs)
        ds = {}
        for name in bones:
            a, b = segs[name]
            ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            L2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2 or 1e-12
            fr = ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1] + (p[2] - a[2]) * ab[2]) / L2
            f = max(0.0, min(1.0, fr))
            q = (a[0] + ab[0] * f, a[1] + ab[1] * f, a[2] + ab[2] * f)
            ds[name] = math.dist(p, q) + (2.0 * (-fr) * math.sqrt(L2) if fr < 0 and name in ROOTED else 0.0)
        b0 = min(ds, key=ds.get)
        cand = (b0,) + tuple(x for x in ADJ[b0] if x in ds)
        ws = [(b, math.exp(-((ds[b] - ds[b0]) / sigma) ** 2)) for b in cand]
        ws = [(b, w) for b, w in ws if w > 0.02]
        tot = sum(w for _, w in ws)
        out.append([(b, w / tot) for b, w in ws])
    return out


def build_actor(bpy, rig, actor: dict, rgb: tuple, samples: list, fps: float, cone_rgb=(0.06, 0.06, 0.06)):
    """An armature posed per sample from the rig solver, a body skinned to it, and a review-only facing cone
    on the head. Returns (armature, body, cone). actor["body"]: "mannequin" (default — one continuous
    metaball surface modelled in the A-pose and skinned with blended weights) or "segments" (rigid
    primitives, the fallback when metaballs are unavailable)."""
    import bmesh, mathutils
    sc = bpy.context.scene
    H = rig.H
    mode = actor.get("body", "mannequin")
    rest = joint_refs(rig.canonical() if mode == "mannequin" else rig.joints(samples[0]))
    arm_data = bpy.data.armatures.new(actor["id"] + "_rig")
    arm = bpy.data.objects.new(actor["id"] + "_rig", arm_data)
    sc.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    rest_m = {}
    for name, h, t, ref in BONES:
        m, L = bone_matrix(rest[h], rest[t], rest[ref] if ref in rest else (0, 0, 1))
        eb = arm_data.edit_bones.new(name)
        eb.head = (0, 0, 0); eb.tail = (0, max(L, 0.01), 0)
        eb.matrix = m
    bpy.ops.object.mode_set(mode="OBJECT")
    for name, *_ in BONES:                       # Blender may re-roll an edit bone: read back what it kept
        rest_m[name] = arm_data.bones[name].matrix_local.copy()
    names = [b[0] for b in BONES]
    if mode == "mannequin":
        me, parts = mannequin_mesh(bpy, rest, H, float(rig.k_sh), actor["id"] + "_body")
        body = bpy.data.objects.new(actor["id"] + "_body", me)
        sc.collection.objects.link(body)
        groups = {name: body.vertex_groups.new(name=name) for name in names}
        for vi, ws in enumerate(skin_weights([tuple(v.co) for v in me.vertices], rest, H, parts)):
            for bname, w in ws:
                groups[bname].add([vi], w, "REPLACE")
    else:
        bm = bmesh.new()
        dl = bm.verts.layers.deform.verify()
        segs = body_segments(H, float(rig.k_sh), rest)
        for gi, name in enumerate(names):
            base = rest_m[name]
            if name.startswith("foot_"):
                # the foot bone runs from the ankle down to the toe joint; the shoe is built level with the
                # floor when the foot is flat, so tilt its frame up by that slope
                side = name[-1]
                v = [rest[f"toe_{side}"][i] - rest[f"ankle_{side}"][i] for i in range(3)]
                pitch = math.atan2(-v[2], math.hypot(v[0], v[1]))
                base = base @ mathutils.Matrix.Rotation(pitch, 4, "X")
            add_prims(bm, segs.get(name, []), base=base, group=gi, dl=dl, seg=28)
        me = bpy.data.meshes.new(actor["id"] + "_body")
        bm.to_mesh(me); bm.free()
        for poly in me.polygons:
            poly.use_smooth = True
        body = bpy.data.objects.new(actor["id"] + "_body", me)
        sc.collection.objects.link(body)
        for name in names:
            body.vertex_groups.new(name=name)
    mod = body.modifiers.new("rig", "ARMATURE"); mod.object = arm
    body.color = (*rgb, 1.0)
    # the review-only facing cone, skinned to the head
    bm = bmesh.new()
    dl = bm.verts.layers.deform.verify()
    # in the head bone's frame +Z is the way the face points (bone_matrix with head_fwd as the reference)
    add_prims(bm, [cone((0, 0.055 * H, 0.10 * H), 0.012 * H, 0.0, 0.06 * H, axis="z")], base=rest_m["head"],
              group=0, dl=dl)
    me2 = bpy.data.meshes.new(actor["id"] + "_facing")
    bm.to_mesh(me2); bm.free()
    cone_ob = bpy.data.objects.new(actor["id"] + "_facing", me2)
    sc.collection.objects.link(cone_ob)
    cone_ob.vertex_groups.new(name="head")
    m2 = cone_ob.modifiers.new("rig", "ARMATURE"); m2.object = arm
    cone_ob.color = (*cone_rgb, 1.0)
    cone_ob.hide_render = True
    # pose every sample: matrix_basis = rest⁻¹ · pose, for a flat (unparented) bone set
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    for t in samples:
        f = int(round(t * fps)) + 1
        j = joint_refs(rig.joints(t))
        for name, h, tl, ref in BONES:
            pm, _ = bone_matrix(j[h], j[tl], j[ref] if ref in j else (0, 0, 1))
            basis = rest_m[name].inverted() @ pm
            loc, quat, _ = basis.decompose()
            pb = arm.pose.bones[name]
            pb.location = loc; pb.rotation_quaternion = quat
            pb.keyframe_insert("location", frame=f); pb.keyframe_insert("rotation_quaternion", frame=f)
    return arm, body, cone_ob


def build_piece(bpy, piece: dict, rgb: tuple, dims_fn, set_kinds_round=()):
    """One set piece as one mesh object, parts placed in its own frame and then rotated and moved."""
    import mathutils
    w, d, h = dims_fn(piece)
    kind = piece.get("kind", "box")
    prims = piece["_prims"] if piece.get("_prims") else set_parts(kind, w, d, h, piece)
    mat = piece.get("material") or DEFAULT_MATERIAL.get(kind)
    m = mathutils.Matrix.Translation((piece["pos"][0], piece["pos"][1], float(piece.get("z", 0)))) @ \
        mathutils.Matrix.Rotation(math.radians(float(piece.get("rot", 0))), 4, "Z")
    if kind == "door" and piece.get("open"):
        # the leaf swings about its hinge (the piece's local −x edge)
        leaf = prims.pop()
        frame_ob = mesh_object(bpy, piece["id"], prims, rgb, m, mat)
        hinge = mathutils.Matrix.Translation((-w / 2 + 0.07, 0, 0)) @ \
            mathutils.Matrix.Rotation(math.radians(float(piece["open"])), 4, "Z") @ \
            mathutils.Matrix.Translation((w / 2 - 0.07, 0, 0))
        mesh_object(bpy, piece["id"] + "_leaf", [leaf], rgb, m @ hinge, mat)
        return frame_ob
    return mesh_object(bpy, piece["id"], prims, rgb, m, mat)


# what a kit piece is made of, when its parts do not say (blocking_look turns names into materials)
DEFAULT_MATERIAL = {"table": "wood", "desk": "wood", "round_table": "wood", "counter": "wood_paint", "island": "wood_paint",
                    "chair": "wood", "stool": "wood", "sofa": "fabric", "bed": "fabric_light", "shelf": "wood",
                    "fridge": "metal", "car": "paint", "plant": "foliage", "lamp": "metal", "door": "door",
                    "window": "window_frame", "rug": "fabric", "tv": "plastic_dark", "wall": "plaster",
                    "floor_mark": "paint_white", "box": "default"}


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────────
def selftest(dimensions: dict | None = None) -> int:
    dims = dimensions or {"table": (1.2, 0.8, 0.75), "chair": (0.45, 0.45, 0.9), "counter": (1.8, 0.6, 0.9),
                          "sofa": (2.0, 0.9, 0.85), "bed": (1.6, 2.0, 0.55), "shelf": (1.0, 0.35, 1.8),
                          "stool": (0.4, 0.4, 0.65), "car": (4.5, 1.8, 1.45), "plant": (0.4, 0.4, 1.1),
                          "fridge": (0.7, 0.7, 1.8), "desk": (1.4, 0.7, 0.75), "round_table": (1.0, 1.0, 0.75),
                          "lamp": (0.4, 0.4, 1.6), "rug": (2.0, 1.4, 0.01), "tv": (1.2, 0.25, 0.75),
                          "door": (0.9, 0.05, 2.1), "window": (1.2, 0.05, 1.2), "island": (2.0, 1.0, 0.9)}
    tol = 0.02
    for kind, (w, d, h) in ((k_, v_) for k_, v_ in dims.items() if k_ not in EXTRA_PARTS):   # the kit's own kinds
        lo, hi = parts_bbox(set_parts(kind, w, d, h))
        allow_up = 0.50 if kind == "bed" else tol                    # pillows and the headboard rise above the mattress
        assert lo[0] >= -w / 2 - tol and hi[0] <= w / 2 + tol, (kind, "x", lo, hi)
        assert lo[1] >= -d / 2 - tol and hi[1] <= d / 2 + tol, (kind, "y", lo, hi)
        assert lo[2] >= -tol and hi[2] <= h + allow_up, (kind, "z", lo, hi)
    for kind, (w, d, h) in {"bottle": (0.07, 0.07, 0.16), "mug": (0.09, 0.09, 0.10), "laptop": (0.32, 0.22, 0.24),
                            "phone": (0.075, 0.009, 0.15), "jar": (0.09, 0.09, 0.11)}.items():
        lo, hi = parts_bbox(prop_parts(kind, w, d, h))
        assert all(lo[i] >= -(w, d, h)[i] / 2 - tol and hi[i] <= (w, d, h)[i] / 2 + tol for i in range(3)), (kind, lo, hi)
    room = {"id": "k", "kind": "room", "pos": [0, 0], "size": [4, 3, 2.6], "walls": ["back", "left"],
            "openings": [{"wall": "back", "kind": "window", "at": 0.5, "w": 1.2, "h": 1.1, "sill": 0.9},
                         {"wall": "left", "kind": "door", "at": 0.0, "w": 0.9, "h": 2.1}]}
    ws = room_walls(room)
    solid = [p for p in ws if p["solid"]]
    # the back wall: left part, sill, head, right part; the left wall: two parts and a head over the door
    assert len([p for p in solid if ".back." in p["id"]]) == 4 and len([p for p in solid if ".left." in p["id"]]) == 3, \
        [p["id"] for p in solid]
    back_len = sum(p["size"][0] for p in solid if ".back." in p["id"] and p["z"] == 0.0 and p["size"][2] == 2.6)
    assert abs(back_len - (4 + 0.2 - 1.2)) < 1e-6, back_len
    assert any(p["kind"] == "door" and not p["solid"] for p in ws)
    # the mannequin: elements sit inside the body's height; weights follow the nearest bone and blend at joints
    import blocking_rig as RIG
    rig = RIG.Rig.__new__(RIG.Rig)
    rig.H, rig.k_sh = 1.7, 1.0
    J = rig.canonical()
    els = mannequin_elements(J, 1.7)
    assert len(els) > 30 and all(-0.05 < e[2][2] < 1.75 for e in els) and {e[0] for e in els} == set(PART_BONES)
    near = lambda j, off=(0, 0, 0): tuple(J[j][i] + off[i] for i in range(3))
    w_hand, w_elbow, w_thigh, w_chest = skin_weights(
        [near("palm_L"), near("elbow_L", (0, 0, 0.02)), near("hip_L", (0, -0.04, -0.12)), near("shoulder_R", (0.1, 0.05, -0.05))],
        J, 1.7, ["arm_L", "arm_L", "leg_L", "torso"])
    assert max(w_hand, key=lambda x: x[1])[0] == "hand_L", w_hand
    assert {b for b, _ in w_elbow} >= {"upperarm_L", "forearm_L"}, w_elbow
    assert {b for b, _ in w_thigh} <= {"thigh_L", "shin_L"} and abs(sum(w for _, w in w_thigh) - 1) < 1e-9, w_thigh
    assert {b for b, _ in w_chest} <= {"spine", "pelvis", "neck"}, w_chest      # the chest never follows an arm
    # precise geometry: a lathed bottle and an extruded L-shaped counter have the dimensions they were given
    bottle = lathe([[0, 0], [0.035, 0], [0.035, 0.11], [0.014, 0.135], [0.014, 0.16], [0, 0.16]], 32)
    lo, hi = mesh_bbox(bottle)
    assert abs(hi[0] - 0.035) < 1e-6 and abs(hi[2] - 0.16) < 1e-6 and lo[2] == 0.0, (lo, hi)
    assert all(len(f) >= 3 for f in bottle[2][1])
    ell = extrude([[0, 0], [2, 0], [2, 0.6], [0.6, 0.6], [0.6, 1.8], [0, 1.8]], 0.9)
    lo, hi = mesh_bbox(ell)
    assert hi == (2.0, 1.8, 0.9) and len(_ear_clip([(0, 0), (2, 0), (2, 0.6), (0.6, 0.6), (0.6, 1.8), (0, 1.8)])) == 4
    pl = plan_walls({"id": "p", "points": [[0, 0], [4, 0], [4, 3], [0, 3]], "height": 2.6,
                     "openings": [{"segment": 0, "at": 2.0, "w": 0.9, "kind": "door"}]})
    assert sum(1 for p in pl if p["solid"] and p["z"] == 0.0 and p["size"][2] == 2.6) == 5, [p["id"] for p in pl]
    assert any(p["kind"] == "door" and not p["solid"] for p in pl) and all(p["room"] == "p" for p in pl)
    pl2 = plan_walls({"id": "q", "pos": [10, 0], "points": [[0, 0], [4, 0], [4, 3], [0, 3]], "ceiling": True})
    ceil = next(p for p in pl2 if p["id"] == "q.ceiling")
    assert ceil["size"][:2] == [8.0, 6.0] and mesh_bbox(ceil["_prims"][0])[0][2] == 2.7, ceil["size"]
    assert min(p["pos"][0] for p in pl2) >= 10.0 - 1e-9                  # the plan's corners are measured from its pos
    assert plan_inside({"points": [[0, 0], [4, 0], [4, 1], [1, 1], [1, 3], [0, 3]]}, 0.5, 2.5)
    assert not plan_inside({"points": [[0, 0], [4, 0], [4, 1], [1, 1], [1, 3], [0, 3]]}, 3.0, 2.5)   # the L's notch
    fp = shape_footprints({"extrude": {"outline": [[0, 0], [2, 0], [2, 0.6], [0.6, 0.6], [0.6, 1.8], [0, 1.8]], "height": 0.9}})
    assert poly_contains(fp[0], 0.3, 1.5) and not poly_contains(fp[0], 1.5, 1.5) and poly_contains(fp[0], 1.5, 0.65, pad=0.1)
    sb = shift_prims([bottle, box((0, 0, 0.5), (1, 1, 1))], (0, 0, -0.08))
    assert mesh_bbox(sb[0])[0][2] == -0.08 and sb[1][1] == (0, 0, 0.42)
    assert prims_extent([bottle]) == (0.07, 0.07, 0.16) and prims_extent([ell]) == (4.0, 3.6, 0.9)
    assert prims_extent(shape_prims({"parts": [{"box": [0, 0, 0.45, 1.2, 0.6, 0.9]},
                                               {"lathe": [[0, 0.9], [0.1, 0.9], [0.1, 1.2], [0, 1.2]]}]})) == (1.2, 0.6, 1.2)
    print("selftest OK — every set piece and prop fits its footprint; a room's walls split around a window "
          "(sill and head) and a door (head only), and the openings stay walkable; the mannequin's skin weights "
          "follow the nearest bone and blend across the joint; lathed, extruded and floor-plan geometry keeps the "
          "dimensions it was given")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
