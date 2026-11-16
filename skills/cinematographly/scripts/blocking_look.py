#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""blocking_look.py — the concept-art look: the blocked scene lit and coloured (references/blocking.md §3d).

The blocking render is flat on purpose: legend colours, studio light, nothing a video model should copy.
A concept frame is the opposite job: the same geometry, the same camera, the same marks, rendered with
real light (sun and sky by time of day, practicals, window light, softboxes), materials (asphalt, brick,
glass, wood, fabric, foliage, water…) and the job's palette, so a director, a client or a frame model
can judge the place before anything is generated.

  python3 blocking.py concept S5.blocking.json -o <dir> [--times 0,2.5,5] [--res 720]
  python3 blocking_look.py --selftest
  python3 blocking_look.py hdri <polyhaven id> [--res 2k] [--out DIR] [--fetch]   # see below

THE SPEC. `look` (optional): {"time": day | golden | blue_hour | night | overcast | interior_day |
interior_night | studio, "sun": [azimuth°, elevation°] (overrides the time's sun), "palette": {material
or role: colour name or [r, g, b]}, "haze": 0–1, "hdri": "<path to a local .hdr/.exr>", "exposure": EV}.
Without it, the time is guessed from the environment (exteriors: golden; interiors: interior_day;
studio: studio).

POLY HAVEN (CC0). HDRI skies make an exterior read as a real place. Assets are CC0 ("You can use our
assets for any purpose… You do not need to give credit", polyhaven.com/license, read 2026-10-23); the API
asks for a unique User-Agent and, where content is surfaced to users, a "Powered by Poly Haven" credit
(Public-API ToS §2.4–2.5). `hdri` prints the file's URL and size and downloads nothing until it is run
again with `--fetch` — a download is the owner's call, per job. A fetched file goes in the job's
assets folder with a licence record beside it, never into git or the plugin bundle.

RENDER COST. EEVEE in the cloud container runs on the CPU (software OpenGL): about 25–45 s a still at
540 × 960 [measured · 2026-10-23]. Concept frames are stills; a lit animation belongs on a Mac with a GPU.
"""
from __future__ import annotations
import json, math, os, sys, urllib.request

USER_AGENT = "cinematographly-blocking/3.0 (+concept frames)"

# name: (rgb or None = the piece's own colour, roughness, metallic, transmission, emission strength, pattern)
MATERIALS = {
    "default": (None, 0.6, 0.0, 0.0, 0.0, None),
    "plaster": ((0.70, 0.68, 0.64), 0.85, 0.0, 0.0, 0.0, "noise_fine"),
    "concrete": ((0.55, 0.54, 0.52), 0.9, 0.0, 0.0, 0.0, "noise"),
    "brick": ((0.52, 0.27, 0.19), 0.85, 0.0, 0.0, 0.0, "brick"),
    "stone": ((0.62, 0.60, 0.56), 0.8, 0.0, 0.0, 0.0, "noise"),
    "pavement": ((0.58, 0.57, 0.55), 0.85, 0.0, 0.0, 0.0, "tiles_large"),
    "asphalt": ((0.11, 0.11, 0.12), 0.9, 0.0, 0.0, 0.0, "noise"),
    "gravel": ((0.55, 0.50, 0.44), 0.95, 0.0, 0.0, 0.0, "noise"),
    "grass": ((0.20, 0.36, 0.12), 0.95, 0.0, 0.0, 0.0, "noise"),
    "sand": ((0.84, 0.74, 0.56), 0.95, 0.0, 0.0, 0.0, "noise_fine"),
    "water": ((0.05, 0.22, 0.30), 0.05, 0.0, 0.0, 0.0, None),
    "foliage": ((0.17, 0.33, 0.12), 0.8, 0.0, 0.0, 0.0, "noise"),
    "bark": ((0.27, 0.19, 0.13), 0.9, 0.0, 0.0, 0.0, "noise"),
    "wood": ((0.47, 0.31, 0.18), 0.55, 0.0, 0.0, 0.0, "wood"),
    "wood_paint": ((0.86, 0.85, 0.82), 0.45, 0.0, 0.0, 0.0, None),
    "wood_floor": ((0.52, 0.36, 0.22), 0.5, 0.0, 0.0, 0.0, "planks"),
    "tile": ((0.85, 0.85, 0.83), 0.3, 0.0, 0.0, 0.0, "tiles_small"),
    "fabric": (None, 0.95, 0.0, 0.0, 0.0, "noise_fine"),
    "fabric_light": ((0.88, 0.86, 0.82), 0.95, 0.0, 0.0, 0.0, "noise_fine"),
    "fabric_dark": ((0.12, 0.12, 0.13), 0.95, 0.0, 0.0, 0.0, "noise_fine"),
    "metal": ((0.72, 0.72, 0.74), 0.3, 1.0, 0.0, 0.0, None),
    "metal_dark": ((0.16, 0.16, 0.17), 0.4, 1.0, 0.0, 0.0, None),
    "glass": ((0.75, 0.82, 0.85), 0.03, 0.0, 0.92, 0.0, None),
    "glass_dark": ((0.10, 0.13, 0.16), 0.08, 0.0, 0.0, 0.0, None),
    "mirror": ((0.92, 0.92, 0.92), 0.02, 1.0, 0.0, 0.0, None),
    "door": ((0.30, 0.22, 0.16), 0.5, 0.0, 0.0, 0.0, "wood"),
    "window_frame": ((0.85, 0.85, 0.85), 0.5, 0.0, 0.0, 0.0, None),
    "sign": ((0.15, 0.15, 0.17), 0.4, 0.0, 0.0, 0.0, None),
    "paint": (None, 0.25, 0.3, 0.0, 0.0, None),
    "paint_red": ((0.65, 0.08, 0.06), 0.35, 0.0, 0.0, 0.0, None),
    "paint_white": ((0.90, 0.90, 0.88), 0.6, 0.0, 0.0, 0.0, None),
    "rubber": ((0.05, 0.05, 0.05), 0.85, 0.0, 0.0, 0.0, None),
    "plastic_dark": ((0.07, 0.07, 0.08), 0.45, 0.0, 0.0, 0.0, None),
    "ceramic": ((0.93, 0.93, 0.92), 0.15, 0.0, 0.0, 0.0, None),
    "product": (None, 0.4, 0.0, 0.0, 0.0, "labels"),
    "art": ((0.55, 0.45, 0.38), 0.7, 0.0, 0.0, 0.0, "noise"),
    "blackboard": ((0.08, 0.10, 0.09), 0.9, 0.0, 0.0, 0.0, None),
    "cyc": ((0.92, 0.92, 0.91), 0.9, 0.0, 0.0, 0.0, None),
    "lamp_glow": ((1.0, 0.92, 0.78), 0.5, 0.0, 0.0, 6.0, None),
    "lamp_red": ((0.9, 0.08, 0.05), 0.5, 0.0, 0.0, 3.0, None),
    "skin": (None, 0.55, 0.0, 0.0, 0.0, None),
}
NAMED = {   # palette colour names (blocking.COLORS covers the legend names)
    "oak": (0.47, 0.31, 0.18), "walnut": (0.27, 0.17, 0.10), "cream": (0.90, 0.86, 0.76), "sage": (0.55, 0.62, 0.50),
    "terracotta": (0.70, 0.36, 0.24), "navy": (0.10, 0.14, 0.30), "charcoal": (0.16, 0.16, 0.17),
    "sand": (0.84, 0.74, 0.56), "olive": (0.40, 0.42, 0.20), "blush": (0.88, 0.70, 0.66),
}

# times of day: (sun azimuth°, sun elevation°, sun strength, sun colour, sky strength, practicals on, world tint)
TIMES = {
    "day": (140, 55, 4.0, (1.0, 0.97, 0.92), 1.0, False, None),
    "golden": (250, 9, 3.2, (1.0, 0.72, 0.45), 0.8, False, None),
    "blue_hour": (260, -4, 0.0, (1.0, 1.0, 1.0), 0.45, True, (0.32, 0.42, 0.75)),
    "night": (200, 35, 0.12, (0.62, 0.72, 1.0), 0.3, True, (0.05, 0.07, 0.14)),     # a cool moon and a blue ambient
    "overcast": (160, 40, 0.0, (1.0, 1.0, 1.0), 1.4, False, (0.72, 0.74, 0.78)),
    "interior_day": (150, 30, 3.0, (1.0, 0.96, 0.9), 0.6, False, (0.62, 0.74, 0.92)),
    "interior_night": (0, -30, 0.0, (1.0, 1.0, 1.0), 0.03, True, (0.05, 0.06, 0.1)),
    "studio": (0, -30, 0.0, (1.0, 1.0, 1.0), 0.6, True, (0.2, 0.2, 0.21)),       # a soft grey fill under the softboxes
}


def colour(spec_colors: dict, x, fallback=(0.6, 0.6, 0.6)):
    if isinstance(x, (list, tuple)) and len(x) == 3:
        return tuple(float(v) for v in x)
    if isinstance(x, str):
        return spec_colors.get(x) or NAMED.get(x) or fallback
    return fallback


def guess_time(spec: dict) -> str:
    envs = spec.get("env")
    envs = envs if isinstance(envs, list) else ([envs] if envs else [])
    kinds = {e.get("kind") for e in envs}
    if kinds & {"cyc", "tabletop", "podium", "turntable"}:
        return "studio"
    if kinds & {"street", "storefront", "parking_lot", "park", "beach", "rooftop", "road"}:
        return "golden"
    return "interior_day"


# ── Blender side ───────────────────────────────────────────────────────────────────────────────────────
_CACHE = {}


def material_hook(palette: dict, spec_colors: dict):
    """KIT.MATERIAL_HOOK: (bpy, material name, piece rgb) → a Principled material, cached by (name, rgb)."""
    def hook(bpy, name, rgb):
        key = (name, tuple(round(v, 3) for v in rgb))
        if key in _CACHE:
            return _CACHE[key]
        base, rough, metal, trans, emit, pattern = MATERIALS.get(name, MATERIALS["default"])
        col = colour(spec_colors, palette.get(name), base if base else tuple(rgb)) if name in palette else (base or tuple(rgb))
        m = bpy.data.materials.new(f"{name}_{len(_CACHE)}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        _set(bsdf, "Roughness", rough)
        _set(bsdf, "Metallic", metal)
        if trans:
            _set(bsdf, "Transmission Weight", trans) or _set(bsdf, "Transmission", trans)
            _set(bsdf, "IOR", 1.45)
            try:
                m.blend_method = "BLEND"
            except (AttributeError, TypeError):
                pass
        if emit:
            _set(bsdf, "Emission Color", (*col, 1.0)) or _set(bsdf, "Emission", (*col, 1.0))
            _set(bsdf, "Emission Strength", emit)
        if pattern:
            _pattern(nt, bsdf, col, pattern)
        else:
            _set(bsdf, "Base Color", (*col, 1.0))
        _CACHE[key] = m
        return m
    return hook


def _set(node, name, val):
    try:
        node.inputs[name].default_value = val
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _pattern(nt, bsdf, col, pattern):
    """Procedural variation so surfaces read as materials: noise for concrete and grass, a grain for wood,
    courses for brick, a grid for paving, scattered tones for shelf products."""
    links = nt.links
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    dark = tuple(max(0.0, c * 0.72) for c in col)
    light = tuple(min(1.0, c * 1.12) for c in col)
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*light, 1.0)
    if pattern in ("noise", "noise_fine"):
        tex = nt.nodes.new("ShaderNodeTexNoise")
        _set(tex, "Scale", 9.0 if pattern == "noise" else 28.0)
        _set(tex, "Detail", 6.0)
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    elif pattern == "wood":
        tex = nt.nodes.new("ShaderNodeTexWave")
        _set(tex, "Scale", 6.0)
        _set(tex, "Distortion", 6.0)
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    elif pattern == "brick":
        tex = nt.nodes.new("ShaderNodeTexBrick")
        _set(tex, "Color1", (*col, 1.0)); _set(tex, "Color2", (*dark, 1.0)); _set(tex, "Mortar", (0.7, 0.68, 0.64, 1.0))
        _set(tex, "Scale", 2.2)
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        return
    elif pattern == "planks":
        tex = nt.nodes.new("ShaderNodeTexBrick")
        _set(tex, "Color1", (*col, 1.0)); _set(tex, "Color2", (*dark, 1.0)); _set(tex, "Mortar", (*dark, 1.0))
        _set(tex, "Scale", 1.0); _set(tex, "Mortar Size", 0.004); _set(tex, "Brick Width", 1.4); _set(tex, "Row Height", 0.16)
        try:
            tex.offset = 0.37
        except AttributeError:
            pass
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        return
    elif pattern == "tiles_small":
        tex = nt.nodes.new("ShaderNodeTexBrick")
        _set(tex, "Color1", (*col, 1.0)); _set(tex, "Color2", (*col, 1.0)); _set(tex, "Mortar", (*dark, 1.0))
        _set(tex, "Scale", 4.0); _set(tex, "Mortar Size", 0.01); _set(tex, "Brick Width", 0.5); _set(tex, "Row Height", 0.5)
        try:
            tex.offset = 0.0
        except AttributeError:
            pass
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        return
    elif pattern in ("tiles_large",):
        tex = nt.nodes.new("ShaderNodeTexChecker")
        _set(tex, "Color1", (*col, 1.0)); _set(tex, "Color2", (*dark, 1.0)); _set(tex, "Scale", 1.6)
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        return
    elif pattern == "labels":
        tex = nt.nodes.new("ShaderNodeTexVoronoi")
        _set(tex, "Scale", 14.0)
        links.new(coord.outputs["Object"], tex.inputs["Vector"])
        ramp.color_ramp.elements[0].color = (0.75, 0.25, 0.2, 1.0)
        ramp.color_ramp.elements[1].color = (0.2, 0.45, 0.7, 1.0)
        links.new(tex.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])


def setup(bpy, spec: dict, look: dict, actors_rgb: dict | None = None):
    """Engine, world (sky or HDRI), sun, practicals and atmosphere for the look. Call after the scene's
    objects exist (practicals are found by their material)."""
    import mathutils
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    ee = sc.eevee
    for attr, val in (("taa_render_samples", int(look.get("samples", 32))), ("use_shadows", True),
                      ("use_raytracing", True), ("use_gtao", True), ("use_bloom", True), ("use_soft_shadows", True),
                      ("shadow_ray_count", 2), ("shadow_step_count", 6), ("use_volumetric_shadows", True)):
        try:
            setattr(ee, attr, val)
        except (AttributeError, TypeError):
            pass
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except (TypeError, AttributeError):
        try:
            sc.view_settings.view_transform = "Filmic"
        except (TypeError, AttributeError):
            pass
    t_ = look.get("time") or guess_time(spec)
    sc.view_settings.exposure = float(look.get("exposure", {"night": 1.0, "blue_hour": 0.3, "day": -0.5}.get(
        t_, -0.9 if t_.startswith("interior") else 0.0)))
    tname = look.get("time") or guess_time(spec)
    az, el, sun_s, sun_c, sky_s, practicals, tint = TIMES.get(tname, TIMES["day"])
    if look.get("sun"):
        az, el = (float(v) for v in look["sun"])
    world = bpy.data.worlds.new("concept_world")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    hdri = look.get("hdri")
    if hdri and os.path.exists(hdri):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        _set(bg, "Strength", sky_s if sky_s > 0 else 1.0)
    elif tint is not None:
        _set(bg, "Color", (*tint, 1.0))
        _set(bg, "Strength", max(sky_s, 0.02))
    else:
        sky = nt.nodes.new("ShaderNodeTexSky")
        for attr, val in (("sky_type", "NISHITA"), ("sun_elevation", math.radians(max(el, 0.5))),
                          ("sun_rotation", math.radians(az)), ("altitude", 30.0), ("air_density", 1.2),
                          ("dust_density", 2.0 if tname == "golden" else 1.0), ("sun_disc", False)):
            try:
                setattr(sky, attr, val)
            except (AttributeError, TypeError):
                pass
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        _set(bg, "Strength", 0.35 * sky_s)
    if sun_s > 0 and el > -1:
        sun = bpy.data.lights.new("sun", "SUN")
        sun.energy = sun_s
        sun.color = sun_c
        try:
            sun.angle = math.radians(1.2 if tname != "overcast" else 20)
        except AttributeError:
            pass
        ob = bpy.data.objects.new("sun", sun)
        sc.collection.objects.link(ob)
        d = mathutils.Vector((math.cos(math.radians(el)) * math.cos(math.radians(az)),
                              math.cos(math.radians(el)) * math.sin(math.radians(az)), math.sin(math.radians(el))))
        ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    lights = 0
    if practicals or tname.startswith("interior") or tname == "studio":
        for ob in list(sc.objects):
            if ob.type != "MESH" or not ob.data.materials:
                continue
            if any(m and m.name.startswith("lamp_glow") for m in ob.data.materials):
                bb = [ob.matrix_world @ mathutils.Vector(c) for c in ob.bound_box]
                top = max(v.z for v in bb)
                cx = sum(v.x for v in bb) / 8; cy = sum(v.y for v in bb) / 8
                L = bpy.data.lights.new(f"practical{lights}", "AREA" if tname == "studio" else "POINT")
                L.energy = 900 if tname == "studio" else (60 if tname.startswith("interior") else 1500)
                if not tname.startswith("interior") and tname != "studio":
                    L.shadow_soft_size = 0.3
                L.color = (1.0, 0.86, 0.68) if tname != "studio" else (1.0, 0.98, 0.95)
                lo = bpy.data.objects.new(L.name, L)
                sc.collection.objects.link(lo)
                lo.location = (cx, cy, top - (0.15 if tname != "studio" else 0.0))
                if tname == "studio":
                    L.size = 0.9
                    aim_ = mathutils.Vector((0 - cx, -0.5 - cy, 1.2 - top))
                    lo.location = mathutils.Vector((cx, cy, top)) + aim_.normalized() * 0.4   # in front of the box's face
                    lo.rotation_euler = aim_.to_track_quat("-Z", "Y").to_euler()
                lights += 1
    if tname == "interior_day":
        # window light: an area light in each window opening, aimed into the room
        for ob in list(sc.objects):
            if ob.type == "MESH" and "window" in ob.name and "sill" not in ob.name:
                L = bpy.data.lights.new(f"window{lights}", "AREA")
                L.energy = 260
                L.size = 1.3
                L.color = (1.0, 0.97, 0.92)
                lo = bpy.data.objects.new(L.name, L)
                sc.collection.objects.link(lo)
                bb = [ob.matrix_world @ mathutils.Vector(c) for c in ob.bound_box]
                c = sum(bb, mathutils.Vector()) / 8
                lo.location = c
                room_c = mathutils.Vector((c.x * 0.2, c.y * 0.2, 1.0))
                lo.rotation_euler = (room_c - c).to_track_quat("-Z", "Y").to_euler()
                lights += 1
    if tname.startswith("interior"):
        # EEVEE has no full bounce light: a soft panel under each ceiling stands in for the light the walls
        # and floor would bounce (a stand-in, by eye)
        for ob in list(sc.objects):
            if ob.type == "MESH" and ob.name.endswith(".ceiling"):
                bb = [ob.matrix_world @ mathutils.Vector(c) for c in ob.bound_box]
                c = sum(bb, mathutils.Vector()) / 8
                w_ = max(v.x for v in bb) - min(v.x for v in bb)
                d_ = max(v.y for v in bb) - min(v.y for v in bb)
                L = bpy.data.lights.new("bounce", "AREA")
                L.shape = "RECTANGLE"
                L.size, L.size_y = w_ * 0.8, d_ * 0.8
                L.energy = (12.0 if tname == "interior_day" else 4.0) * w_ * d_    # low: the windows must model the room
                L.color = (1.0, 0.96, 0.9)
                lo = bpy.data.objects.new("bounce", L)
                sc.collection.objects.link(lo)
                lo.location = (c.x, c.y, min(v.z for v in bb) - 0.05)
    if practicals and not tname.startswith("interior") and tname != "studio":
        # cars after dark: headlights down the road and a dash glow on the faces inside
        for v in spec.get("vehicles", []):
            car = sc.objects.get(v["id"])
            if car is None:
                continue
            L_ = 4.6
            for side in (0.6, -0.6):
                hl = bpy.data.lights.new(f"{v['id']}_headlight", "SPOT")
                hl.energy, hl.spot_size, hl.color = 700, math.radians(55), (1.0, 0.95, 0.85)
                lo = bpy.data.objects.new(hl.name, hl)
                sc.collection.objects.link(lo)
                lo.parent = car
                lo.location = (L_ / 2 + 0.05, side, 0.65)
                lo.rotation_euler = (0.0, math.radians(-95), 0.0)          # the lamp's −Z turned to the car's +X
            dash = bpy.data.lights.new(f"{v['id']}_dash", "AREA")
            dash.energy, dash.size, dash.color = 30, 0.5, (1.0, 0.82, 0.62)
            lo = bpy.data.objects.new(dash.name, dash)
            sc.collection.objects.link(lo)
            lo.parent = car
            lo.location = (0.75, 0.0, 1.0)
            lo.rotation_euler = (0.0, math.radians(70), 0.0)             # aimed back and up at the front seats
            lights += 3
    haze = float(look.get("haze", 0.15 if tname in ("golden", "blue_hour") else 0.0))
    if haze > 0:
        # a bounded box of haze round the set, not a world volume: EEVEE treats a world volume as infinite and
        # it swallows the sky, which rendered every golden-hour frame black [measured · 2026-10-23]
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        me = bpy.data.meshes.new("haze")
        bm.to_mesh(me); bm.free()
        hz = bpy.data.objects.new("haze", me)
        sc.collection.objects.link(hz)
        span = float(look.get("haze_span", 160.0))
        hz.scale = (span, span, 40.0)
        hz.location = (0.0, 0.0, 19.9)
        mat = bpy.data.materials.new("haze")
        mat.use_nodes = True
        mnt = mat.node_tree
        for n_ in list(mnt.nodes):
            if n_.type == "BSDF_PRINCIPLED":
                mnt.nodes.remove(n_)
        mo = next(n_ for n_ in mnt.nodes if n_.type == "OUTPUT_MATERIAL")
        vol = mnt.nodes.new("ShaderNodeVolumePrincipled")
        _set(vol, "Density", 0.0025 * haze)
        _set(vol, "Anisotropy", 0.3)
        mnt.links.new(vol.outputs[0], mo.inputs["Volume"])
        me.materials.append(mat)
        hz.hide_render = False
    return {"time": tname, "practicals": lights, "haze": haze}


# ── Poly Haven ──────────────────────────────────────────────────────────────────────────────────────────
def hdri_info(asset_id: str, res: str = "2k") -> dict:
    """URL and size of a Poly Haven HDRI, from the public API — reads metadata, downloads nothing."""
    req = urllib.request.Request(f"https://api.polyhaven.com/files/{asset_id}", headers={"User-Agent": USER_AGENT})
    files = json.load(urllib.request.urlopen(req, timeout=20))
    f = files["hdri"][res]["hdr"]
    info = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/info/{asset_id}",
                                                                   headers={"User-Agent": USER_AGENT}), timeout=20))
    return {"id": asset_id, "name": info.get("name"), "url": f["url"], "bytes": f.get("size"), "res": res,
            "license": "CC0 (polyhaven.com/license)", "source": f"https://polyhaven.com/a/{asset_id}",
            "credit": "Powered by Poly Haven"}


def hdri_fetch(asset_id: str, res: str, out_dir: str) -> str:
    meta = hdri_info(asset_id, res)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{asset_id}_{res}.hdr")
    req = urllib.request.Request(meta["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())
    meta["file"] = os.path.basename(path)
    json.dump(meta, open(path + ".licence.json", "w"), indent=2)
    return path


# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────
def selftest() -> int:
    for name, (base, rough, metal, trans, emit, pattern) in MATERIALS.items():
        assert 0 <= rough <= 1 and 0 <= metal <= 1 and 0 <= trans <= 1 and emit >= 0, name
        assert base is None or len(base) == 3, name
        assert pattern in (None, "noise", "noise_fine", "wood", "brick", "tiles_large", "tiles_small", "planks", "labels"), (name, pattern)
    for t, v in TIMES.items():
        assert len(v) == 7, t
    assert guess_time({"env": {"kind": "street"}}) == "golden"
    assert guess_time({"env": {"kind": "cyc"}}) == "studio"
    assert guess_time({"env": {"kind": "kitchen"}}) == "interior_day"
    assert colour({}, "oak") == NAMED["oak"] and colour({}, [0.1, 0.2, 0.3]) == (0.1, 0.2, 0.3)
    # every material name the environments and the kit use exists here
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import blocking_env as ENV, blocking_kit as KIT
    used = set(KIT.DEFAULT_MATERIAL.values())
    for kind, fn in ENV.PARTS.items():
        w, d, h = ENV.DIMENSIONS[kind]
        for p in fn(w, d, h, {"id": kind}):
            if isinstance(p[-1], dict) and p[-1].get("m"):
                used.add(p[-1]["m"])
    missing = sorted(used - set(MATERIALS))
    assert not missing, missing
    print(f"selftest OK — {len(MATERIALS)} materials and {len(TIMES)} times of day are complete; every material "
          f"the kit and the {len(ENV.TEMPLATES)} environments name exists")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if len(sys.argv) > 2 and sys.argv[1] == "hdri":
        aid = sys.argv[2]
        res = sys.argv[sys.argv.index("--res") + 1] if "--res" in sys.argv else "2k"
        out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
        meta = hdri_info(aid, res)
        print(json.dumps(meta, indent=2))
        if "--fetch" in sys.argv:
            print("fetched:", hdri_fetch(aid, res, out))
        else:
            print(f"(nothing downloaded: {meta['bytes'] / 1e6 if meta.get('bytes') else '?'} MB — run again with --fetch "
                  f"once the owner has said yes for this job)")
        sys.exit(0)
    print(__doc__)
