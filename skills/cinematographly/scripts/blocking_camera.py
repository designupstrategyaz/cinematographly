#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""blocking_camera.py — the camera as an operator with a rig (references/blocking.md §3a).

A camera move is not a pair of keyframes. It is a body (the rig) carrying a lens toward a reason (the
move), started by something in the scene (the trigger), with the physics of that body in every frame:
a dolly glides and stops clean, a handheld lags, overshoots and settles, a steadicam floats, a drone
banks into its turns, an FPV pitches into its speed, a robot arm snaps and stops dead. This module is
what turns a shot plan into that.

  python3 blocking_camera.py --selftest        # the integrator, the rigs, the move table (no Blender)
  python3 blocking_camera.py --moves           # every named move, its rig and what it is for

blocking.py calls it in three places:
  expand_shot()    a named move (`"move": "pivot_whip"`) becomes camera keys with their own timing,
                   framing, lens, roll and focus; a trigger (`"start": "A.stands"`) moves it in time
  operator table   the ideal path is run through the rig's physics: position and aim are each a
                   spring-damper (natural frequency, damping), so lag, overshoot and settle are real;
                   the operator anticipates (it tracks the plan 2ζ/ω ahead, times `anticipate`), so a
                   steady move does not trail; then the rig's own motion is added: banking into the
                   path's curvature, pitch, breathing, steps, vibration, cross-faded where rigs hand
                   over, and any `react` impulse (a flinch, a bump, a jolt)
  rig_words()      the words a prompt needs for the rig; blocking.py measures the beats on the rendered
                   camera (camera_beats) so the prompt says what the camera does, not what it was asked

Where the vocabulary comes from: the move classes and their meanings are `cinematography-craft.md` §3
(§3.4 the rigs, §3.8 the advanced moves, §3.9 signal → move); the named moves with their numbers are
`move-catalogue.md`; the rule that a long take needs the camera to have a role, not a list of moves,
is move-catalogue §33. The spring constants are house values chosen by eye against those
descriptions — an assumption, not a measurement — and every one is in RIGS below.
"""
from __future__ import annotations
import math, sys

# ── rigs: how the body that carries the lens moves ─────────────────────────────────────────────────────
# pos / aim: (natural frequency rad/s, damping ratio) of the spring that makes the real camera chase the
# ideal one; None = exact (no lag). noise: (metres, degrees, low Hz, high Hz) of drift on top. bank: how
# far it rolls into lateral acceleration (1 = the angle a free body would lean). pitch: how far it tips
# with forward acceleration. bob: step bob in metres while it travels faster than 0.4 m/s. vib: (metres,
# degrees, Hz) of engine or motor vibration. max_mps / max_dps: what the rig can do before `check` warns.
RIGS = {
    "locked":    dict(pos=None, aim=None, noise=None, bank=0, pitch=0, bob=0, vib=None, max_mps=0.05, max_dps=1,
                      words="locked off on sticks"),
    "tripod":    dict(pos=None, aim=(9.0, 0.8), noise=None, bank=0, pitch=0, bob=0, vib=None, max_mps=0.05, max_dps=120,
                      words="on a tripod head, an operator panning and tilting"),
    "dolly":     dict(pos=(6.0, 1.0), aim=(9.0, 0.85), anticipate=0.9, noise=(0.001, 0.03, 0.2, 0.6), bank=0, pitch=0, bob=0, vib=None,
                      max_mps=2.0, max_dps=90, words="on a dolly, gliding"),
    "slider":    dict(pos=(7.0, 1.0), aim=(10.0, 0.9), anticipate=0.95, noise=None, bank=0, pitch=0, bob=0, vib=None, max_mps=0.8, max_dps=60,
                      words="on a slider"),
    "crane":     dict(pos=(3.2, 0.85), aim=(7.0, 0.85), anticipate=0.8, noise=(0.002, 0.05, 0.15, 0.5), bank=0, pitch=0, bob=0, vib=None,
                      max_mps=3.0, max_dps=60, words="on a crane, the arm's weight carrying it"),
    "steadicam": dict(pos=(3.0, 0.75), aim=(5.5, 0.8), noise=(0.006, 0.25, 0.25, 0.9), bank=0.15, bank_max=5, pitch=0, bob=0.004,
                      vib=None, max_mps=3.5, max_dps=90, words="on a steadicam, floating"),
    "gimbal":    dict(pos=(5.0, 0.95), aim=(12.0, 0.95), anticipate=0.9, noise=(0.002, 0.06, 0.3, 0.9), bank=0, pitch=0, bob=0.002,
                      vib=None, max_mps=4.0, max_dps=120, words="on a gimbal, smooth"),
    "shoulder":  dict(pos=(5.0, 0.7), aim=(8.0, 0.65), noise=(0.010, 0.45, 0.2, 1.0), bank=0.1, bank_max=4, pitch=0, bob=0.010,
                      vib=None, max_mps=3.0, max_dps=180, words="on the operator's shoulder"),
    "handheld":  dict(pos=(5.0, 0.6), aim=(7.0, 0.55), noise=(0.015, 0.6, 0.2, 1.1), bank=0.1, bank_max=4, pitch=0, bob=0.012,
                      vib=None, max_mps=3.0, max_dps=240, words="handheld, an operator reacting"),
    "drone":     dict(pos=(1.8, 0.95), aim=(3.0, 0.95), anticipate=0.97, max_acc=9.0, noise=(0.010, 0.15, 0.1, 0.5), bank=1.0, bank_max=25, pitch=0.6, bob=0,
                      vib=None, max_mps=18.0, max_dps=45, words="from a drone"),
    "fpv":       dict(pos=(4.0, 0.7), aim=(6.0, 0.7), anticipate=0.95, max_acc=20.0, noise=(0.004, 0.3, 0.5, 2.0), bank=2.2, bank_max=45, pitch=1.0, bob=0,
                      vib=(0.002, 0.25, 9.0), max_mps=35.0, max_dps=300, words="on an FPV drone, banking into its turns"),
    # the small ducted FPV that flies indoors and through gaps (aerial-and-fpv.md §5): stiffer than a drone,
    # softer than a racing FPV; speed [assumed] — no source gives one
    "cinewhoop": dict(pos=(4.5, 0.85), aim=(7.0, 0.85), anticipate=0.95, max_acc=8.0, noise=(0.003, 0.15, 0.4, 1.5), bank=1.2,
                      bank_max=30, pitch=0.6, bob=0, vib=(0.001, 0.12, 9.0), max_mps=8.0, max_dps=180,
                      words="on a small ducted cinewhoop, gliding through the space a few feet above the floor"),
    # an insect's eye: quick springs that ring a little (it corrects all the time), steep banks; the speeds are
    # the bee and mosquito figures in assets/aerial-moves.json, the springs house values by eye
    "insect":    dict(pos=(9.0, 0.6), aim=(12.0, 0.6), anticipate=0.9, max_acc=12.0, noise=(0.004, 0.6, 0.8, 3.0), bank=1.6,
                      bank_max=40, pitch=0.8, bob=0, vib=None, max_mps=2.5, max_dps=400,
                      words="at an insect's scale, a hand-width above the ground, real time"),
    "car_mount": dict(pos=None, aim=None, noise=None, bank=0, pitch=0, bob=0, vib=(0.003, 0.2, 11.0), max_mps=60,
                      max_dps=90, words="rigged to the car"),
    "tracking_vehicle": dict(pos=(2.5, 0.9), aim=(6.0, 0.9), anticipate=1.0, noise=(0.004, 0.1, 0.3, 1.0), bank=0.2, bank_max=6, pitch=0.2, bob=0,
                      vib=(0.002, 0.1, 8.0), max_mps=60, max_dps=90, words="from a tracking vehicle"),
    "robo":      dict(pos=(26.0, 1.0), aim=(30.0, 1.0), anticipate=1.0, max_acc=14.0, noise=None, bank=0, pitch=0, bob=0, vib=None, max_mps=4.0,
                      max_dps=400, words="on a motion-control arm, precise and fast"),
    "snorricam": dict(pos=None, aim=None, noise=None, bank=0, pitch=0, bob=0, vib=None, max_mps=10, max_dps=400,
                      words="body-mounted on the actor (snorricam)"),
    "pov":       dict(pos=None, aim=(10.0, 0.7), noise=(0.006, 0.3, 0.3, 1.2), bank=0, pitch=0, bob=0.010, vib=None,
                      max_mps=6, max_dps=300, words="through the character's eyes"),
}
DEFAULT_RIG = "dolly"
FAST_AIM = {"handheld", "shoulder", "fpv", "robo", "pov", "snorricam", "cinewhoop", "insect"}   # rigs whose fast turns are their character


def rig_of(name):
    return RIGS.get(name or DEFAULT_RIG, RIGS[DEFAULT_RIG])


# ── triggers: a move starts because something happens ──────────────────────────────────────────────────
TRIGGER_WORDS = ("starts", "stops", "sits", "stands", "picks", "puts", "turns")


def resolve_time(bl, spec: dict, x, default: float = 0.0) -> float:
    """A time in seconds, or an event: "A.starts" (begins to walk), "A.stops", "A.sits", "A.stands",
    "bottle.picks" (is picked up), "bottle.puts" (is put down), "A.turns", each with an optional offset
    ("A.stands+0.3"). ⛔ The camera does not start before the subject does (cinematography-craft §3.8)."""
    if x is None:
        return default
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    off = 0.0
    for sign in ("+", "-"):
        if sign in s[1:]:
            i = s.rfind(sign)
            try:
                off = float(s[i:])
                s = s[:i]
            except ValueError:
                pass
            break
    try:
        return float(s) + off
    except ValueError:
        pass
    who, _, what = s.partition(".")
    kind, obj = bl._by_id(spec, who)
    if kind == "actor":
        ks = sorted(obj["keys"], key=lambda k: float(k["t"]))
        default_pose = obj.get("pose", "stand")
        for a, b in zip(ks, ks[1:]):
            if what == "starts" and math.dist(a["pos"], b["pos"]) > 1e-6:
                return float(a["t"]) + off
        if what == "stops":
            moving_segs = [(a, b) for a, b in zip(ks, ks[1:]) if math.dist(a["pos"], b["pos"]) > 1e-6]
            if moving_segs:
                return float(moving_segs[-1][1]["t"]) + off
        for a, b in zip(ks, ks[1:]):
            pa, pb = a.get("pose", default_pose), b.get("pose", default_pose)
            if what == "sits" and pb == "sit" and pa != "sit":
                return float(b["t"]) + off
            if what == "stands" and pa == "sit" and pb != "sit":
                return float(b["t"]) + off
            if what == "turns" and str(a.get("facing")) != str(b.get("facing")):
                return float(a["t"]) + off
    if kind == "prop":
        hs = obj.get("held", [])
        if hs and what in ("picks", "picked"):
            return float(hs[0]["from"]) + off
        if hs and what in ("puts", "put"):
            return float(hs[-1]["to"]) + off
    raise ValueError(f"cannot resolve the time {x!r}: use seconds, or <actor>.starts/stops/sits/stands/turns, "
                     f"or <prop>.picks/puts, with an optional +/- offset")


# ── small geometry ──────────────────────────────────────────────────────────────────────────────────────
def _v(a, b=(0, 0, 0), k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _unit(a):
    n = _norm(a) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def _flat(a):
    return _unit((a[0], a[1], 0.0))


def lens_for_extent(w: int, h: int, extent: float, dist: float) -> float:
    """The focal length (36 mm along the long side) that shows `extent` metres vertically at `dist`."""
    half = math.atan((extent / 2) / max(dist, 0.05))
    short_over_long = min(w, h) / max(w, h)
    sensor_v = 36.0 if h >= w else 36.0 * short_over_long
    return max(8.0, min(400.0, (sensor_v / 2) / math.tan(half)))


def yaw_pitch(vec):
    return math.degrees(math.atan2(vec[1], vec[0])), math.degrees(math.atan2(vec[2], math.hypot(vec[0], vec[1])))


def dir_from(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return (math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))


# ── the operator: a spring-damper chasing the ideal camera ──────────────────────────────────────────────
def spring_track(xs: list, dt: float, w: float | None, zeta: float, kicks: dict | None = None) -> list:
    """Critically or under-damped tracking of a sampled signal (a list of equal-length tuples). Semi-
    implicit Euler at dt. kicks: {sample index: velocity tuple} added at that sample (a flinch, a bump)."""
    if not xs:
        return []
    if w is None:
        return list(xs)
    n = len(xs[0])
    x = list(xs[0])
    v = [0.0] * n
    out = []
    sub = max(1, int(math.ceil(dt * w / 0.25)))          # keep each integration step stable
    h = dt / sub
    for i, target in enumerate(xs):
        if kicks and i in kicks:
            v = [v[j] + kicks[i][j] for j in range(n)]
        for _ in range(sub):
            for j in range(n):
                a = w * w * (target[j] - x[j]) - 2 * zeta * w * v[j]
                v[j] += a * h
                x[j] += v[j] * h
        out.append(tuple(x))
    return out


def spring_track_var(xs: list, dt: float, params: list, kicks: dict | None = None, ff: list | None = None,
                     valid: int | None = None) -> list:
    """spring_track with (w, zeta) per sample (None = exact at that sample): a continuous move that hands
    from one rig to another — a handheld rise that becomes a drone — changes its physics where it changes rig.
    ff: per sample, how much the operator anticipates the plan (0 = a pure spring that trails a moving
    subject; 1 = no lag at a steady speed, the spring only answers changes of speed)."""
    if not xs:
        return []
    n = len(xs[0])
    x = list(xs[0])
    v = [(xs[1][j] - xs[0][j]) / dt for j in range(n)] if len(xs) > 1 else [0.0] * n   # already moving at the cut
    off, voff = [0.0] * n, [0.0] * n
    out = []
    # the operator anticipates: a spring trails a steady move by 2ζ/ω seconds, so it tracks the plan that far
    # ahead (times `ff`) — no lag at a steady pace, and a snap still overshoots as much as the spring does
    for i in range(len(xs)):
        pr = params[i]
        shift = int(round((ff[i] if ff else 0.0) * (2 * pr[1] / pr[0]) / dt)) if pr else 0
        nv = len(xs) if valid is None else max(2, min(len(xs), valid))
        if shift == 0:
            target = xs[i]
        elif i + shift < nv:
            target = xs[i + shift]
        else:                                          # past the plan's last key it carries on as it was going
            over = i + shift - (nv - 1)
            m_ = min(4, nv - 1)
            last, prev_ = xs[nv - 1], xs[nv - 1 - m_]
            target = tuple(last[j] + (last[j] - prev_[j]) / max(m_, 1) * over for j in range(n))
        pr = params[i]
        if pr is None:
            # an exact rig (sticks, a car mount) follows the plan; a kick rings out as a stiff offset on top
            if kicks and i in kicks:
                voff = [voff[j] + kicks[i][j] for j in range(n)]
            if any(abs(c) > 1e-9 for c in off + voff):
                sub = max(1, int(math.ceil(dt * 16.0 / 0.25)))
                h = dt / sub
                for _ in range(sub):
                    for j in range(n):
                        voff[j] += (-256.0 * off[j] - 2 * 0.6 * 16.0 * voff[j]) * h
                        off[j] += voff[j] * h
                if max(abs(c) for c in off + voff) < 1e-6:
                    off, voff = [0.0] * n, [0.0] * n
            prev_t = xs[i - 1] if i else xs[i]
            v = [(xs[i][j] - prev_t[j]) / dt + voff[j] for j in range(n)]
            x = [xs[i][j] + off[j] for j in range(n)]
            out.append(tuple(x))
            continue
        if kicks and i in kicks:
            v = [v[j] + kicks[i][j] for j in range(n)]
        w, zeta = pr
        sub = max(1, int(math.ceil(dt * w / 0.25)))
        h = dt / sub
        for _ in range(sub):
            for j in range(n):
                a = w * w * (target[j] - x[j]) - 2 * zeta * w * v[j]
                v[j] += a * h
                x[j] += v[j] * h
        out.append(tuple(x))
    return out


def unwrap(angles: list) -> list:
    out, prev = [], None
    for a in angles:
        if prev is not None:
            a = prev + ((a - prev + 180) % 360 - 180)
        out.append(a)
        prev = a
    return out


def noise(t: float, seed: int, lo: float, hi: float) -> float:
    """A deterministic slow drift in -1..1: three sines between lo and hi Hz with seeded phases."""
    tot = 0.0
    for j in range(3):
        f = lo + (hi - lo) * j / 2.0
        ph = ((seed * 9301 + j * 49297 + 233280) % 1000) / 1000.0 * 2 * math.pi
        tot += math.sin(2 * math.pi * f * t + ph)
    return tot / 3.0


REACT = {   # impulses an event gives the operator: (position m/s back from the subject, up m/s, aim °/s yaw, pitch)
    "flinch": (0.6, 0.15, 35.0, 12.0),
    "startle": (0.9, 0.25, 60.0, 20.0),
    "bump": (0.0, 0.35, 6.0, 18.0),
    "jolt": (0.15, 0.5, 10.0, 30.0),
    "lean_in": (-0.35, 0.0, 0.0, -4.0),
}


# ── the move library ─────────────────────────────────────────────────────────────────────────────────────
class Ctx:
    """What a move needs to know about the scene, at any time."""

    def __init__(self, bl, spec: dict, sh: dict, t0: float, t1: float):
        self.bl, self.spec, self.sh, self.t0, self.t1 = bl, spec, sh, t0, t1
        self.w, self.h = spec["render"]["w"], spec["render"]["h"]
        self.lens = float(sh.get("lens", spec.get("camera", {}).get("lens", 35)))

    def kind(self, ident):
        return self.bl._by_id(self.spec, ident)[0] if isinstance(ident, str) else None

    def actor(self, ident):
        return self.bl._by_id(self.spec, ident)[1]

    def st(self, ident, t):
        return self.bl.actor_at(self.spec, self.actor(ident), t)

    def hh(self, ident, t):
        st = self.st(ident, t)
        return self.bl.actor_heights(self.actor(ident), st["pose"], st["seat"])

    def ground(self, ident, t):
        """(x, y) of an actor, prop, vehicle or set piece, or of a point."""
        p = self.point(ident, t)
        return (p[0], p[1])

    def point(self, ident, t):
        if isinstance(ident, (list, tuple)):
            return tuple(float(v) for v in (list(ident) + [1.0])[:3])
        if isinstance(ident, str) and "." in ident and ident.split(".")[1] in ("head", "mouth", "chest", "waist", "feet", "hands"):
            who, part = ident.split(".")
            st, hh = self.st(who, t), self.hh(who, t)
            z = {"head": hh["eye"], "mouth": hh["eye"] - 0.065 * self.height(who),
                 "chest": hh["chest"], "waist": hh["waist"], "feet": 0.12, "hands": hh["waist"] + 0.05}[part]
            return (st["pos"][0], st["pos"][1], z)
        p = self.bl.point_of(self.spec, ident, t)
        if p is None:
            raise ValueError(f"the move names {ident!r}, which is nothing in the spec")
        return tuple(p)

    def height(self, ident):
        return float(self.actor(ident).get("height", 1.7))

    def facing(self, ident, t):
        if self.kind(ident) == "actor":
            return self.st(ident, t)["facing"]
        if self.kind(ident) == "vehicle":
            return self.bl.vehicle_at(self.spec, self.bl._by_id(self.spec, ident)[1], t)["heading"]
        return -90.0

    def vfov(self, lens):
        return self.bl.vfov_hfov(lens, self.w, self.h)[0]

    def dist_for(self, ident, size, lens):
        E = self.bl.ext_for(size, self.height(ident) if self.kind(ident) == "actor" else 1.7)
        return (E / 2) / math.tan(math.radians(self.vfov(lens)) / 2)

    def lens_for(self, extent, dist):
        return lens_for_extent(self.w, self.h, extent, dist)

    def at(self, x, default):
        """A time inside the shot: seconds from the shot's start, or an event ("A.stands+0.2")."""
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return self.t0 + float(x)
        return resolve_time(self.bl, self.spec, x, default)


def _p(sh, name, default):
    return sh.get(name, sh.get("params", {}).get(name, default))


def _on(subject, size, side, height, lens=None, **extra):
    k = {"on": subject, "size": size, "side": side, "height": height}
    if lens:
        k["lens"] = lens
    k.update(extra)
    return k


def _pos(pos, look_at, lens=None, **extra):
    k = {"pos": [round(v, 4) for v in pos], "look_at": look_at}
    if lens:
        k["lens"] = lens
    k.update(extra)
    return k


def _timing(c: Ctx, sh: dict, natural: float | None = None):
    """(ts, te): when the move itself runs inside the shot. `start` (seconds into the shot, or an event),
    `dur`, and `hold` [before, after] place it; by default it runs the whole shot."""
    hold = _p(sh, "hold", [0.0, 0.0])
    if isinstance(hold, (int, float)):
        hold = [hold, hold]
    ts = c.at(_p(sh, "start", None), c.t0 + float(hold[0]))
    dur = _p(sh, "dur", natural)
    te = ts + float(dur) if dur else c.t1 - float(hold[1])
    ts = max(c.t0, min(ts, c.t1))
    te = max(ts + 0.1, min(te, c.t1))
    return ts, te


def mv_static(c, sh):
    k = _framing(c, sh, "from")
    return [dict(k, t=c.t0), dict(k, t=c.t1)]


def _framing(c, sh, which):
    base = {x: sh[x] for x in ("on", "size", "side", "height", "lens", "pos", "look_at", "place", "roll", "focus", "fstop")
            if x in sh}
    base.update(sh.get(which, {}))
    if "pos" not in base and "on" not in base:
        raise ValueError(f"shot at {c.t0:g} s: give `on` (an actor) or `pos` + `look_at`")
    if "on" in base and "pos" not in base:
        base.setdefault("size", "MS")
        base.setdefault("side", 0)
        base.setdefault("height", "eye")
    return base


def mv_between(c, sh, defaults_from: dict, defaults_to: dict, natural=None, ease="auto"):
    """The common shape: a framing, a move to another framing, holds either side."""
    a = dict(defaults_from); a.update(_framing(c, sh, "from") if ("from" in sh or "on" in sh or "pos" in sh) else {})
    b = dict(a); b.update(defaults_to); b.update(sh.get("to", {}))
    for k_, v_ in defaults_from.items():
        if k_ not in sh.get("from", {}) and k_ not in sh:
            a[k_] = v_
    ts, te = _timing(c, sh, natural)
    keys = []
    if ts > c.t0 + 1e-6:
        keys.append(dict(a, t=c.t0))
    keys.append(dict(a, t=ts, ease="stop"))
    keys.append(dict(b, t=te, ease="stop" if te < c.t1 - 1e-6 else ease))
    if te < c.t1 - 1e-6:
        keys.append(dict(b, t=c.t1))
    return keys


def mv_push_in(c, sh):
    return mv_between(c, sh, {"size": "MS"}, {"size": "MCU"})


def mv_pull_out(c, sh):
    return mv_between(c, sh, {"size": "MCU"}, {"size": "WS"})


def mv_creep(c, sh):
    sh = dict(sh); sh.setdefault("hold", [0.0, 0.0])
    return mv_between(c, sh, {"size": "MS"}, {"size": "MCU"}, ease="linear")


def mv_arc(c, sh, deg=45.0):
    side0 = float(_framing(c, sh, "from").get("side", 0))
    d = float(_p(sh, "degrees", deg))
    if sh.get("move") == "arc_left":
        d = -abs(d)
    return mv_between(c, sh, {"side": side0}, {"side": side0 + d})


def mv_orbit(c, sh):
    return mv_arc(c, sh, deg=180.0)


def mv_orbit_360(c, sh):
    return mv_arc(c, sh, deg=360.0)


def mv_bullet_time(c, sh):
    sh = dict(sh); sh.setdefault("dur", 1.6)
    return mv_arc(c, sh, deg=180.0)


def mv_spiral(c, sh):
    side0 = float(_framing(c, sh, "from").get("side", 0))
    d = float(_p(sh, "degrees", 270.0))
    return mv_between(c, sh, {"size": "WS", "height": "low", "side": side0},
                      {"size": "MS", "height": "high", "side": side0 + d})


def mv_boom(c, sh, up=True):
    return mv_between(c, sh, {"height": "low" if up else "high"}, {"height": "high" if up else "low"})


def mv_crane(c, sh, up=True):
    a = {"height": "eye", "size": "MS"} if up else {"height": "overhead", "size": "WS"}
    b = {"height": "overhead", "size": "WS"} if up else {"height": "eye", "size": "MS"}
    return mv_between(c, sh, a, b)


def mv_swoop(c, sh):
    side0 = float(_framing(c, sh, "from").get("side", 0))
    return mv_between(c, sh, {"height": "overhead", "size": "WS", "side": side0 - 30},
                      {"height": "eye", "size": "MCU", "side": side0})


def mv_hero_low(c, sh):
    return mv_between(c, sh, {"height": 0.35, "size": "WS", "lens": 24}, {"height": 0.45, "size": "MWS", "lens": 24})


def mv_dolly_zoom(c, sh):
    """Vertigo: the camera travels and the lens counter-zooms so the subject keeps its size while the
    world behind it swells (dolly out, zoom in) or rushes away (dolly in, zoom out)."""
    subj = _framing(c, sh, "from").get("on")
    if not subj:
        raise ValueError("dolly_zoom needs `on` (the subject that keeps its size)")
    direction = _p(sh, "direction", "out")
    ratio = float(_p(sh, "ratio", 2.2 if direction == "out" else 0.45))
    a = _framing(c, sh, "from"); a.setdefault("size", "MCU")
    lens0 = float(a.get("lens", c.lens))
    d0 = c.dist_for(subj, a["size"], lens0)
    st = c.st(subj, c.t0)
    ang = st["facing"] + float(a.get("side", 0))
    eye = c.point(subj, c.t0)
    hz = eye[2]

    def at_dist(d, t):
        g = c.ground(subj, t)                        # ride a moving subject: the offset is kept, not the spot
        return (g[0] + math.cos(math.radians(ang)) * d, g[1] + math.sin(math.radians(ang)) * d, hz)
    ts, te = _timing(c, sh)
    d1 = d0 * ratio
    keys = []
    if ts > c.t0 + 1e-6:
        keys.append(_pos(at_dist(d0, c.t0), subj, lens0, t=c.t0, hold_size=True))
    n = max(2, int(math.ceil((te - ts) / 0.25)))
    for i in range(n + 1):
        f = i / n
        e = f * f * (3 - 2 * f)
        t = ts + (te - ts) * f
        k = _pos(at_dist(d0 + (d1 - d0) * e, t), subj, lens0, t=t, hold_size=True)
        if i in (0, n):
            k["ease"] = "stop"
        keys.append(k)
    if te < c.t1 - 1e-6:
        keys.append(_pos(at_dist(d1, c.t1), subj, lens0, t=c.t1, hold_size=True))
    return keys


def mv_zoom(c, sh, crash=False, back=False):
    a = _framing(c, sh, "from")
    lens0 = float(a.get("lens", c.lens))
    lens1 = float(sh.get("to", {}).get("lens", lens0 * (3.0 if crash else 1.8)))
    sh2 = dict(sh)
    if crash:
        sh2.setdefault("dur", 0.28)
    ts, te = _timing(c, sh2)
    pin = dict(a); pin.pop("lens", None)
    if "on" in pin:                                      # a zoom does not move the camera: pin it where it starts
        tmp = c.bl.solve_camera_key(c.spec, dict(pin, t=c.t0, lens=lens0))
        pin = {"pos": tmp["pos"], "look_at": pin["on"], "place": pin.get("place", "auto")}
    keys = [dict(pin, t=c.t0, lens=lens0)]
    keys.append(dict(pin, t=ts, lens=lens0, ease="stop"))
    if back:
        mid = (ts + te) / 2
        keys.append(dict(pin, t=mid, lens=lens1, ease="stop"))
        keys.append(dict(pin, t=te, lens=lens0, ease="stop"))
    else:
        keys.append(dict(pin, t=te, lens=lens1, ease="stop"))
    keys.append(dict(pin, t=c.t1, lens=lens0 if back else lens1))
    return _dedupe(keys)


def _dedupe(keys):
    out = []
    for k in sorted(keys, key=lambda k: k["t"]):
        if out and abs(out[-1]["t"] - k["t"]) < 1e-6:
            out[-1] = k
        else:
            out.append(k)
    return out


def mv_pan(c, sh, whip=False):
    """Pan or tilt (or a whip) from one target to another from a fixed position."""
    a, b = _framing(c, sh, "from"), sh.get("to", {})
    look_a = a.get("look_at", a.get("on"))
    look_b = b.get("look_at", b.get("on", look_a))
    pos = a.get("pos")
    if pos is None:
        tmp = c.bl.solve_camera_key(c.spec, dict(a, t=c.t0))
        pos = tmp["pos"]
    sh2 = dict(sh)
    if whip:
        sh2.setdefault("dur", 0.5)
    ts, te = _timing(c, sh2)
    lens = a.get("lens", c.lens)
    extra = {"whip": True} if whip else {}
    keys = [_pos(pos, look_a, lens, t=c.t0, place=a.get("place", "auto"))]
    keys.append(_pos(pos, look_a, lens, t=ts, ease="stop", place=a.get("place", "auto")))
    keys.append(_pos(pos, look_b, b.get("lens", lens), t=te, ease="stop", place=b.get("place", "auto"), **extra))
    keys.append(_pos(pos, look_b, b.get("lens", lens), t=c.t1, place=b.get("place", "auto")))
    return _dedupe(keys)


def mv_pivot_whip(c, sh):
    """move-catalogue §1: the camera planted midway between A and B, pivoting on the spot; settled on A,
    a ~0.5 s swing, B settled by ~1.4 s after the swing starts; the same size both ends."""
    A, B = sh.get("a") or sh.get("from", {}).get("look_at"), sh.get("b") or sh.get("to", {}).get("look_at")
    if not (A and B):
        raise ValueError("pivot_whip needs `a` and `b` (the two people)")
    ea, eb = c.point(A, c.t0), c.point(B, c.t0)
    mid = ((ea[0] + eb[0]) / 2, (ea[1] + eb[1]) / 2, (ea[2] + eb[2]) / 2)
    # step off the line toward the camera side, so neither face is in profile
    ab = _flat(_sub(eb, ea))
    normal = (-ab[1], ab[0], 0.0)
    side = float(_p(sh, "offset", 0.35))
    pos = _v(mid, normal, side)
    dist = math.dist(pos, ea)
    size = _p(sh, "size", "CU")
    lens = sh.get("lens") or round(c.lens_for(c.bl.SIZE_EXTENT.get(size, 0.32), dist))
    whip_at = c.at(_p(sh, "start", None), c.t0 + max(0.8, (c.t1 - c.t0) * 0.45))
    swing = float(_p(sh, "dur", 0.5))
    keys = [_pos(pos, A, lens, t=c.t0), _pos(pos, A, lens, t=whip_at, ease="stop"),
            _pos(pos, B, lens, t=whip_at + swing, ease="stop", whip=True), _pos(pos, B, lens, t=c.t1)]
    return _dedupe(keys)


def mv_rack_focus(c, sh):
    """Attention moves inside a held frame: focus pulls from one plane to another over `rack` seconds."""
    a = _framing(c, sh, "from")
    f_a, f_b = _p(sh, "focus_from", a.get("focus")), _p(sh, "focus_to", sh.get("to", {}).get("focus"))
    if f_a is None or f_b is None:
        raise ValueError("rack_focus needs `focus_from` and `focus_to` (ids or points)")
    fstop = float(_p(sh, "fstop", 2.0))
    at = c.at(_p(sh, "start", None), c.t0 + (c.t1 - c.t0) * 0.45)
    rack = float(_p(sh, "rack", 0.8))
    k0 = dict(a, focus=f_a, fstop=fstop)
    keys = [dict(k0, t=c.t0), dict(k0, t=at, ease="stop"), dict(k0, t=at + rack, focus=f_b, ease="stop"),
            dict(k0, t=c.t1, focus=f_b)]
    if "to" in sh:
        keys[-1].update({k_: v_ for k_, v_ in sh["to"].items() if k_ != "focus"})
    return _dedupe(keys)


def mv_deep_to_near(c, sh):
    """move-catalogue §7: the camera almost on the ground; focus on the far element while it acts, then a
    rack forward to a detail ~20 cm from the lens as a hand sets it down. Both planes never sharp."""
    far, near = sh.get("far"), sh.get("near")
    if not (far and near):
        raise ValueError("deep_to_near_rack needs `far` and `near`")
    pf, pn = c.point(far, c.t0), c.point(near, c.t1)
    d = _flat(_sub(pf, pn))
    cam = _v((pn[0], pn[1], 0.0), d, -float(_p(sh, "near_dist", 0.35)))
    cam = (cam[0], cam[1], float(_p(sh, "height", 0.22)))
    aim = (pf[0], pf[1], max(0.4, pf[2] * 0.6))
    sh2 = dict(sh, focus_from=far, focus_to=near, pos=cam, look_at=list(aim))
    sh2.setdefault("fstop", 1.8)
    sh2.setdefault("lens", 32)
    return mv_rack_focus(c, sh2)


def mv_truck(c, sh):
    """A lateral move parallel to the subject's plane; the camera keeps looking the same way (`keep`
    keeps a subject framed instead)."""
    a = _framing(c, sh, "from")
    tmp = c.bl.solve_camera_key(c.spec, dict(a, t=c.t0))
    pos, look = tmp["pos"], tmp["look_at"]
    fwd = _flat(_sub(look, pos))
    right = (fwd[1], -fwd[0], 0.0)
    dist = float(_p(sh, "distance", 1.5)) * (-1 if sh.get("move") in ("truck_left", "crab_left") else 1)
    keep = _p(sh, "keep", None)
    p1 = _v(pos, right, dist)
    la0 = keep or list(look)
    la1 = keep or list(_v(look, right, dist))
    ts, te = _timing(c, sh)
    keys = [_pos(pos, la0, a.get("lens"), t=c.t0), _pos(pos, la0, a.get("lens"), t=ts, ease="stop"),
            _pos(p1, la1, a.get("lens"), t=te, ease="stop"), _pos(p1, la1, a.get("lens"), t=c.t1)]
    return _dedupe(keys)


def mv_foreground_wipe(c, sh):
    """A truck that passes something close to the lens across the frame: it wipes the subject out and
    back, the cheapest way to make a reveal or hide a cut."""
    occ, subj = sh.get("past"), _framing(c, sh, "from").get("on") or sh.get("look_at")
    if not (occ and subj):
        raise ValueError("foreground_wipe needs `past` (the foreground piece) and `on` or `look_at`")
    po, ps = c.point(occ, c.t0), c.point(subj, c.t0)
    d = _flat(_sub(ps, po))
    back = float(_p(sh, "behind", 0.6))
    centre = _v((po[0], po[1], ps[2] if isinstance(ps, tuple) else 1.4), d, -back)
    right = (d[1], -d[0], 0.0)
    L = float(_p(sh, "distance", 1.2))
    lens = sh.get("lens", 35)
    ts, te = _timing(c, sh)
    a, b = _v(centre, right, -L / 2), _v(centre, right, L / 2)
    keys = [_pos(a, subj, lens, t=c.t0, occlusion_ok=True), _pos(a, subj, lens, t=ts, ease="stop", occlusion_ok=True),
            _pos(b, subj, lens, t=te, ease="stop", occlusion_ok=True), _pos(b, subj, lens, t=c.t1, occlusion_ok=True)]
    return _dedupe(keys)


def mv_push_through(c, sh):
    """Through a doorway or a window: the lens passes the plane of the opening on its way to the subject."""
    th = sh.get("through")
    target = sh.get("look_at") or sh.get("on")
    if not th:
        raise ValueError("push_through needs `through`: {room, wall, index} or {point, normal}")
    if "point" in th:
        P = tuple(float(v) for v in th["point"])
        n = _unit((float(th["normal"][0]), float(th["normal"][1]), 0.0))
    else:
        room = next((q for q in c.spec.get("set", []) if q.get("id") == th["room"]), None)
        if room is None or room.get("kind") not in ("room", "plan"):
            raise ValueError(f"push_through: {th['room']!r} is no room or plan in the set")
        if room.get("kind") == "plan":
            seg = th.get("segment")
            ops = [p for p in c.bl.KIT.plan_walls(room) if not p["solid"] and p["kind"] in ("door", "window")
                   and (seg is None or f".s{int(seg)}." in p["id"])]
        else:
            ops = [p for p in c.bl.KIT.room_walls(room) if not p["solid"] and f".{th.get('wall', 'back')}." in p["id"]]
        if not ops:
            raise ValueError(f"push_through: {th['room']!r} has no opening on wall {th.get('wall', th.get('segment'))!r}")
        o = ops[int(th.get("index", 0))]
        rot = math.radians(float(o.get("rot", 0)))
        n = (-math.sin(rot), math.cos(rot), 0.0)                     # the wall's normal
        h_open = o["size"][2]
        P = (o["pos"][0], o["pos"][1], float(o.get("z", 0)) + min(h_open * 0.62, 1.5))
        if target:                                                   # travel toward the subject
            tp = c.point(target, c.t0)
            if (tp[0] - P[0]) * n[0] + (tp[1] - P[1]) * n[1] < 0:
                n = (-n[0], -n[1], 0.0)
    before, after = float(_p(sh, "before", 2.2)), float(_p(sh, "after", 1.6))
    p0, p1 = _v(P, n, -before), _v(P, n, after)
    look = target or list(_v(P, n, 6.0))
    lens = sh.get("lens", 24)
    ts, te = _timing(c, sh)
    keys = [_pos(p0, look, lens, t=c.t0, occlusion_ok=True), _pos(p0, look, lens, t=ts, ease="stop", occlusion_ok=True),
            _pos(P, look, lens, t=ts + (te - ts) * 0.55, occlusion_ok=True),
            _pos(p1, look, lens, t=te, ease="stop", occlusion_ok=True), _pos(p1, look, lens, t=c.t1, occlusion_ok=True)]
    return _dedupe(keys)


def _moving(c, subj, t, dt=0.1) -> bool:
    """Is the subject travelling at t (faster than 0.3 m/s)?"""
    if not isinstance(subj, str) or c.kind(subj) not in ("actor", "vehicle", "prop"):
        return False
    a, b = max(0.0, t - dt), min(float(c.spec.get("duration", c.t1)), t + dt)
    return b > a and math.dist(c.ground(subj, a), c.ground(subj, b)) / (b - a) > 0.3


def _dense(c, ts, te, step, fn, subj=None):
    """Keys every `step` seconds from ts to te, each built by fn(t) — for moves that ride a moving subject.
    Where the subject is already travelling at the start or the end, the camera is too: no ease there."""
    n = max(1, int(math.ceil((te - ts) / step)))
    keys = [dict(fn(ts + (te - ts) * i / n), t=ts + (te - ts) * i / n) for i in range(n + 1)]
    if subj is not None:
        for k, t in ((keys[0], ts), (keys[-1], te)):
            if _moving(c, subj, t) and "ease" not in k:
                k["ease"] = "linear"
    return keys


def mv_follow(c, sh, side=180.0):
    a = _framing(c, sh, "from")
    subj = a.get("on")
    if not subj:
        raise ValueError(f"{sh.get('move')} needs `on`")
    side = float(_p(sh, "side", {"lead": 0.0, "side_track": 90.0, "follow": 180.0}.get(sh.get("move"), side)))
    size, height = a.get("size", "MWS"), a.get("height", "chest")
    to = sh.get("to", {})
    ts, te = c.t0, c.t1

    def k(t):
        f = (t - ts) / max(te - ts, 1e-6)
        sz = to.get("size", size) if f > 0.5 else size
        sd = side + (float(to.get("side", side)) - side) * f
        return _on(subj, sz, sd, to.get("height", height) if f > 0.5 else height, a.get("lens"))
    return _dense(c, ts, te, float(_p(sh, "step", 1.0)), k, subj=subj)


def mv_top_down(c, sh):
    a = _framing(c, sh, "from")
    subj = a.get("on") or a.get("look_at")
    p = c.point(subj, c.t0)
    alt = float(_p(sh, "altitude", 3.2))
    rot = float(_p(sh, "rotate", 0.0))
    drop = float(_p(sh, "drop", 0.0))
    lens = a.get("lens", 24)
    tgt = [p[0], p[1], 0.0]
    k0 = _pos((p[0] + 0.001, p[1], alt), tgt, lens, roll=0.0)
    k1 = _pos((p[0] + 0.001, p[1], alt - drop), tgt, lens, roll=rot)
    ts, te = _timing(c, sh)
    return _dedupe([dict(k0, t=c.t0), dict(k0, t=ts, ease="stop"), dict(k1, t=te, ease="stop"), dict(k1, t=c.t1)])


def mv_drone_reveal(c, sh):
    subj = _framing(c, sh, "from").get("on") or sh.get("look_at")
    p = c.point(subj, c.t0)
    f = math.radians(c.facing(subj, c.t0) + float(_p(sh, "side", 180)))
    d0, d1 = float(_p(sh, "from_dist", 2.5)), float(_p(sh, "to_dist", 28.0))
    z0, z1 = float(_p(sh, "from_height", 1.6)), float(_p(sh, "altitude", 22.0))
    lens = sh.get("lens", 24)
    p0 = (p[0] + math.cos(f) * d0, p[1] + math.sin(f) * d0, z0)
    p1 = (p[0] + math.cos(f) * d1, p[1] + math.sin(f) * d1, z1)
    ts, te = _timing(c, sh)
    keys = [_pos(p0, subj, lens, t=c.t0), _pos(p0, subj, lens, t=ts, ease="stop"),
            _pos(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, z0 + (z1 - z0) * 0.62), subj, lens, t=(ts + te) / 2),
            _pos(p1, subj, lens, t=te, ease="stop"), _pos(p1, subj, lens, t=c.t1)]
    return _dedupe(keys)


def mv_flyover(c, sh):
    """Across the location at altitude: `from_point` → `to_point`, or straight over `on` along its facing
    (or `heading`), `span` metres from end to end."""
    if "from_point" in sh and "to_point" in sh:
        a, b = [float(v) for v in sh["from_point"]], [float(v) for v in sh["to_point"]]
    elif sh.get("on"):
        g = c.ground(sh["on"], (c.t0 + c.t1) / 2)
        hd = math.radians(float(_p(sh, "heading", c.facing(sh["on"], c.t0))))
        L = float(_p(sh, "span", 40.0)) / 2
        a = [g[0] - math.cos(hd) * L, g[1] - math.sin(hd) * L, 0.0]
        b = [g[0] + math.cos(hd) * L, g[1] + math.sin(hd) * L, 0.0]
    else:
        raise ValueError("flyover needs `from_point` and `to_point`, or `on`")
    alt = float(_p(sh, "altitude", 18.0))
    tilt = float(_p(sh, "tilt", -30.0))
    d = _flat(_sub(b, a))
    ahead = 40.0
    drop = math.tan(math.radians(-tilt)) * ahead
    look0 = [a[0] + d[0] * ahead, a[1] + d[1] * ahead, alt - drop]
    look1 = [b[0] + d[0] * ahead, b[1] + d[1] * ahead, alt - drop]
    lens = sh.get("lens", 24)
    return [_pos((a[0], a[1], alt), look0, lens, t=c.t0), _pos((b[0], b[1], alt), look1, lens, t=c.t1)]


class _Track:
    """A subject's ground path by distance travelled: where it was, where it will be, which way the path
    runs there. Before the first step and after the last it runs straight on along the facing."""

    def __init__(self, c, subj):
        self.c, self.subj = c, subj
        dur = float(c.spec.get("duration", c.t1))
        n = max(2, int(dur / 0.05) + 1)
        self.ts = [dur * i / (n - 1) for i in range(n)]
        self.P = [c.ground(subj, t) for t in self.ts]
        self.S = [0.0]
        for a, b in zip(self.P, self.P[1:]):
            self.S.append(self.S[-1] + math.dist(a, b))
        h0, h1 = math.radians(c.facing(subj, 0.0)), math.radians(c.facing(subj, dur))
        self.d0, self.d1 = (math.cos(h0), math.sin(h0)), (math.cos(h1), math.sin(h1))

    def s_at(self, t):
        if t <= self.ts[0]:
            return 0.0
        if t >= self.ts[-1]:
            return self.S[-1]
        x = (t - self.ts[0]) / (self.ts[1] - self.ts[0])
        i = min(len(self.ts) - 2, int(x))
        return self.S[i] + (self.S[i + 1] - self.S[i]) * (x - i)

    def at(self, s):
        if s <= 0:
            return (self.P[0][0] + self.d0[0] * s, self.P[0][1] + self.d0[1] * s)
        if s >= self.S[-1]:
            e = s - self.S[-1]
            return (self.P[-1][0] + self.d1[0] * e, self.P[-1][1] + self.d1[1] * e)
        lo, hi = 0, len(self.S) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            lo, hi = (mid, hi) if self.S[mid] <= s else (lo, mid)
        f = (s - self.S[lo]) / max(self.S[hi] - self.S[lo], 1e-9)
        return (self.P[lo][0] + (self.P[hi][0] - self.P[lo][0]) * f, self.P[lo][1] + (self.P[hi][1] - self.P[lo][1]) * f)

    def tangent(self, s, t, half=0.8):
        a, b = self.at(s - half), self.at(s + half)
        L = math.dist(a, b)
        if L < 0.2 * half:                           # standing still: the way they face
            h = math.radians(self.c.facing(self.subj, t))
            return (math.cos(h), math.sin(h))
        return ((b[0] - a[0]) / L, (b[1] - a[1]) / L)


def mv_chase(c, sh, rig_offset=(-3.0, 0.0, 1.3)):
    """A camera flying or driving with a moving subject: `offset` [along, left, up] — along < 0 behind
    on the subject's own path (it flies the line they took, so it swings wide and banks where they turned),
    > 0 ahead looking back, 0 alongside. The look is on the subject (`look_offset` in its frame)."""
    subj = sh.get("on") or sh.get("subject")
    if not subj:
        raise ValueError(f"{sh.get('move')} needs `on`")
    off = sh.get("offset") or {"fpv_chase": (-2.6, 0.4, 1.2), "car_chase": (-7.0, 0.0, 1.5),
                               "car_lead": (8.0, 0.0, 1.1), "car_side_track": (0.3, -3.6, 1.1),
                               "second_participant": (-2.2, 1.4, 1.5)}.get(sh.get("move"), rig_offset)
    look_off = sh.get("look_offset", [0.0, 0.0, 0.0])
    tr = _Track(c, subj)
    veh = c.kind(subj) == "vehicle"

    def k(t):
        p = c.point(subj, t)
        base_z = 0.0 if veh else p[2]
        s0 = tr.s_at(t)
        sc = s0 + float(off[0])
        g = tr.at(sc)
        fx, fy = tr.tangent(sc, t)
        cam = (g[0] - fy * float(off[1]), g[1] + fx * float(off[1]), base_z + float(off[2]))
        tx, ty = tr.tangent(s0, t)
        look = [p[0] + tx * look_off[0] - ty * look_off[1], p[1] + ty * look_off[0] + tx * look_off[1],
                (0.9 if veh else p[2]) + look_off[2]]
        if not any(abs(float(v)) > 1e-9 for v in look_off) and not veh:
            look = subj                                # aim at them live: a baked point lags a fast subject between keys
        return _pos(cam, look, sh.get("lens", 24), on=subj)
    return _dense(c, c.t0, c.t1, float(_p(sh, "step", 0.25)), k, subj=subj)


def mv_fpv_dive(c, sh):
    subj = sh.get("on")
    keys = mv_chase(c, dict(sh, move="fpv_chase"))
    p = c.point(subj, c.t0)
    hd = math.radians(c.facing(subj, c.t0))
    start = (p[0] + math.cos(hd) * 14, p[1] + math.sin(hd) * 14, float(_p(sh, "altitude", 16.0)))
    dive_end = c.t0 + float(_p(sh, "dive", 2.2))
    keys = [dict(k, beat="chase") for k in keys if k["t"] >= dive_end - 1e-6]
    return [_pos(start, subj, sh.get("lens", 20), t=c.t0, beat="dive", on=subj)] + keys


def mv_attach(c, sh, mode):
    """Rigid rigs: the camera is bolted to a body (snorricam), sees through its eyes (pov), or is rigged
    to a car (car_mount). The offset is in the carrier's own frame: +x forward, +y left, +z up."""
    who = sh.get("on")
    if not who:
        raise ValueError(f"{mode} needs `on` (the actor or vehicle that carries the camera)")
    preset = {
        "snorricam": {"offset": [0.62, 0.0, -0.18], "look": "back"},
        "pov": {"offset": [0.08, 0.0, 0.0], "look": "gaze"},
        "car_hood": {"offset": [1.55, 0.36, 1.18], "look": "driver"},
        "car_dash": {"offset": [0.62, 0.0, 1.08], "look": "driver"},
        "car_passenger": {"offset": [-0.15, -0.38, 1.12], "look": "driver"},
        "car_rear": {"offset": [-1.15, 0.0, 1.22], "look": "forward"},
        "car_window": {"offset": [-0.2, 1.35, 1.12], "look": "driver"},
        "car_wheel": {"offset": [1.25, 1.1, 0.32], "look": "back_low"},
    }.get(mode, {"offset": [0, 0, 0], "look": "forward"})
    at = dict(preset)
    at.update({k_: v_ for k_, v_ in sh.items() if k_ in ("offset", "look")})
    at["to"], at["mode"] = who, mode
    k0 = {"attach": at, "pos": [0, 0, 0], "look_at": [1, 0, 1], "lens": sh.get("lens", 18 if mode == "snorricam" else 28)}
    subj = who
    if c.kind(who) == "vehicle" and at.get("look") == "driver":
        drv = next((a for a in c.spec.get("actors", []) if a.get("in") == who and a.get("seat", "driver") == "driver"), None)
        subj = drv["id"] if drv else who
    k0["on"] = subj
    return [dict(k0, t=c.t0), dict(k0, t=c.t1)]


def mv_worms_eye_rise(c, sh):
    """move-catalogue §2: open at ground level on the feet (and what they walk toward), crane up in one
    restless move to a low-then-eye framing on the face, Dutch on the rise, held hard off-centre."""
    subj = _framing(c, sh, "from").get("on")
    if not subj:
        raise ValueError("worms_eye_rise needs `on`")
    ts, te = _timing(c, sh)
    side = float(_p(sh, "side", 25))
    d0, d1 = float(_p(sh, "from_dist", 1.4)), float(_p(sh, "to_dist", 0.85))
    edge = float(_p(sh, "edge", 0.38))
    lens = sh.get("lens", 24)
    dutch = float(_p(sh, "dutch", 12.0))
    eye_drop = 0.22
    dur = float(c.spec.get("duration", c.t1))
    walking = math.dist(c.ground(subj, max(c.t0, te - 0.5)), c.ground(subj, min(dur, te + 0.5))) > 0.1
    if not walking:
        # they arrive and stop: the camera waits low where they will stop, and rises as they arrive
        st1 = c.st(subj, te)
        f = math.radians(st1["facing"] + side)
        S = st1["pos"]
        eye = c.point(subj, te)
        p0 = (S[0] + math.cos(f) * d0, S[1] + math.sin(f) * d0, 0.10)
        p1 = (S[0] + math.cos(f) * d1, S[1] + math.sin(f) * d1, eye[2] - eye_drop)
        keys = [_pos(p0, [S[0], S[1], 0.15], lens, t=c.t0, roll=dutch, place=[edge, 0.25], on=subj, detail="feet"),
                _pos(p0, [S[0], S[1], 0.15], lens, t=ts, ease="stop", roll=dutch, place=[edge, 0.25], on=subj, detail="feet"),
                _pos(p1, subj, lens, t=te, roll=dutch * 0.5, place=[edge, 0.3]),
                _pos(p1, subj, lens, t=c.t1, roll=dutch * 0.5, place=[edge, 0.3])]
        return _dedupe(keys)

    # they keep walking: the camera rides with them, rising from their feet to their face
    def k(t):
        u = 0.0 if t <= ts else 1.0 if t >= te else (t - ts) / (te - ts)
        u = u * u * (3 - 2 * u)
        st = c.st(subj, t)
        f = math.radians(st["facing"] + side)
        d = d0 + (d1 - d0) * u
        eye = c.point(subj, t)
        z = 0.10 + (eye[2] - eye_drop - 0.10) * u
        look = [st["pos"][0], st["pos"][1], 0.15 + (eye[2] - 0.15) * u]
        extra = {"on": subj}
        if u < 0.7:
            extra["detail"] = "feet" if u < 0.4 else "waist"
        return _pos((st["pos"][0] + math.cos(f) * d, st["pos"][1] + math.sin(f) * d, z), look, lens,
                    roll=dutch * (1 - 0.5 * u), place=[edge, 0.25 + 0.05 * u], **extra)
    return _dense(c, c.t0, c.t1, 0.25, k, subj=subj)


def mv_lip_ecu_rise(c, sh):
    """move-catalogue §5: ECU on the mouth for one word, then a slow rise to the eyes, 3/4 from the
    shadow side, and hold."""
    subj = _framing(c, sh, "from").get("on")
    st = c.st(subj, c.t0)
    side = float(_p(sh, "side", 35))
    lens = float(sh.get("lens", 85))
    d = c.dist_for(subj, "ECU", lens)
    f = math.radians(st["facing"] + side)
    eye = c.point(subj, c.t0)
    mouth = (eye[0], eye[1], eye[2] - 0.075 * c.height(subj) / 1.7)
    p0 = (st["pos"][0] + math.cos(f) * d, st["pos"][1] + math.sin(f) * d, mouth[2])
    p1 = (p0[0], p0[1], eye[2] + 0.01)
    ts, te = _timing(c, dict(sh, start=_p(sh, "start", 1.2)))
    keys = [_pos(p0, list(mouth), lens, t=c.t0, place="centre", on=subj, detail="mouth"),
            _pos(p0, list(mouth), lens, t=ts, ease="stop", place="centre", on=subj, detail="mouth"),
            _pos(p1, subj, lens, t=te, ease="stop", place="centre"), _pos(p1, subj, lens, t=c.t1, place="centre")]
    return _dedupe(keys)


def mv_pinned_orbital(c, sh):
    """move-catalogue §32: arc round ONE named detail, the detail pinned in frame while the perspective
    wraps round it; it rides with the subject when the subject moves."""
    det = sh.get("detail") or sh.get("look_at")
    if not det:
        raise ValueError("pinned_detail_orbital needs `detail`")
    r = float(_p(sh, "radius", 0.9))
    a0 = float(_p(sh, "from_angle", -60.0))
    sweep = float(_p(sh, "degrees", 110.0))
    dz = float(_p(sh, "height", 0.15))
    base = c.facing(det.split(".")[0], c.t0) if isinstance(det, str) and c.kind(det.split(".")[0]) in ("actor", "vehicle") else 0.0

    def k(t):
        f = (t - c.t0) / max(c.t1 - c.t0, 1e-6)
        s = f * f * (3 - 2 * f)
        p = c.point(det, t)
        hd = c.facing(det.split(".")[0], t) if base else 0.0
        ang = math.radians(hd + a0 + sweep * s)
        return _pos((p[0] + math.cos(ang) * r, p[1] + math.sin(ang) * r, p[2] + dz), det if isinstance(det, str) else list(det),
                    sh.get("lens", 35), place="centre", frame=[det] if isinstance(det, str) and "." not in det else [])
    return _dense(c, c.t0, c.t1, float(_p(sh, "step", 0.25)), k)


def mv_reveal(c, sh):
    """Start tight on a detail and pull back and up until the place around it is the subject."""
    det = sh.get("detail") or _framing(c, sh, "from").get("on")
    p = c.point(det, c.t0)
    ang = math.radians(float(_p(sh, "angle", -90.0)))
    d0, d1 = float(_p(sh, "from_dist", 0.45)), float(_p(sh, "to_dist", 6.5))
    z1 = float(_p(sh, "altitude", 3.4))
    lens = sh.get("lens", 28)
    p0 = (p[0] + math.cos(ang) * d0, p[1] + math.sin(ang) * d0, p[2] + 0.05)
    p1 = (p[0] + math.cos(ang) * d1, p[1] + math.sin(ang) * d1, z1)
    ts, te = _timing(c, sh)
    look1 = sh.get("look_to", det)
    return _dedupe([_pos(p0, det, lens, t=c.t0), _pos(p0, det, lens, t=ts, ease="stop"),
                    _pos(p1, look1, lens, t=te, ease="stop"), _pos(p1, look1, lens, t=c.t1)])


def mv_asphalt_skim(c, sh):
    """move-catalogue §30: inches above the asphalt, hurtling forward, climbing along the flight path so
    the horizon snaps up on the oncoming car; the camera never breaks its glide."""
    speed = float(_p(sh, "speed", 9.0))
    climb_to = float(_p(sh, "climb_to", 1.3))
    T = c.t1 - c.t0
    if "from_point" in sh:
        start = [float(v) for v in sh["from_point"]]
        hd = math.radians(float(_p(sh, "heading", 90.0)))
    elif sh.get("on"):                             # head-on at the subject: start where the glide ends 2 m short of it
        g0, g1 = c.ground(sh["on"], c.t0), c.ground(sh["on"], c.t1)
        fh = math.radians(c.facing(sh["on"], c.t0))
        end = (g1[0] + math.cos(fh) * 2.0, g1[1] + math.sin(fh) * 2.0)
        hd = math.atan2(g1[1] - end[1], g1[0] - end[0])
        start = [end[0] - math.cos(hd) * speed * T, end[1] - math.sin(hd) * speed * T]
    else:
        raise ValueError("asphalt_skim needs `from_point` (and `heading`), or `on`")
    d = (math.cos(hd), math.sin(hd), 0.0)

    def k(t):
        f = (t - c.t0) / max(T, 1e-6)
        z = 0.08 + (climb_to - 0.08) * (f * f * (3 - 2 * f)) ** 0.8
        p = (start[0] + d[0] * speed * (t - c.t0), start[1] + d[1] * speed * (t - c.t0), z)
        look = [p[0] + d[0] * 20, p[1] + d[1] * 20, z + (0.3 + 1.2 * f)]
        return _pos(p, look, sh.get("lens", 20), ease="linear", on=sh.get("on"))
    return _dense(c, c.t0, c.t1, 0.25, k)                 # it flies in at speed: every key is "linear" already


def mv_ots(c, sh):
    """An over-the-shoulder: behind `over`'s shoulder on the camera side of the line, on `on`'s eyes."""
    over, on = sh.get("over"), sh.get("on")
    if not (over and on):
        raise ValueError("ots needs `over` and `on`")
    po, pn = c.point(over, c.t0), c.point(on, c.t0)
    d = _flat(_sub(pn, po))
    left = (-d[1], d[0], 0.0)
    sgn = -1.0 if _p(sh, "shoulder", "right") == "right" else 1.0
    cam = _v(_v((po[0], po[1], po[2] - 0.06), d, -float(_p(sh, "behind", 0.55))), left, sgn * float(_p(sh, "lateral", 0.32)))
    lens = sh.get("lens", 50)
    k0 = _pos(cam, on, lens, frame=[on], roll=float(_p(sh, "roll", 0.0)))
    return [dict(k0, t=c.t0), dict(k0, t=c.t1)]


def mv_ceiling_drop(c, sh):
    """move-catalogue §14: locked off below the seat line, 1 m out, looking slightly up, a hard 15° Dutch;
    the subject falls into a frame that refuses to move."""
    subj = _framing(c, sh, "from").get("on") or sh.get("look_at")
    p = c.point(subj, c.t1)
    ang = math.radians(c.facing(subj, c.t1) + float(_p(sh, "side", 20)) if c.kind(subj) == "actor" else -90)
    cam = (p[0] + math.cos(ang) * 1.0, p[1] + math.sin(ang) * 1.0, float(_p(sh, "height", 0.38)))
    k0 = _pos(cam, [p[0], p[1], p[2] - 0.2], sh.get("lens", 24), roll=float(_p(sh, "dutch", 15)))
    return [dict(k0, t=c.t0), dict(k0, t=c.t1)]


def mv_motion_control(c, sh):
    """A robot arm hitting marks: a list of `stops`, each a framing held for `hold` seconds, joined by
    snap moves of `snap` seconds."""
    stops = sh.get("stops")
    if not stops:
        raise ValueError("motion_control needs `stops`: [{framing…, hold}]")
    snap = float(_p(sh, "snap", 0.45))
    t = c.t0
    keys = []
    for i, s in enumerate(stops):
        fr = {k_: v_ for k_, v_ in s.items() if k_ != "hold"}
        if "on" in fr:
            is_actor = c.kind(fr["on"]) == "actor"
            fr.setdefault("size", "MS" if is_actor else "CU"); fr.setdefault("side", 0)
            fr.setdefault("height", "eye" if is_actor else "level")
        if i:
            t += snap
        keys.append(dict(fr, t=min(t, c.t1), ease="stop"))
        t += float(s.get("hold", 0.8))
        keys.append(dict(fr, t=min(t, c.t1), ease="stop"))
    if keys[-1]["t"] < c.t1:
        keys.append(dict(keys[-1], t=c.t1))
    return _dedupe(keys)


def mv_drift(c, sh):
    """A held framing that lives: the operator settles, breathes and creeps a few centimetres."""
    a = _framing(c, sh, "from")
    tmp = c.bl.solve_camera_key(c.spec, dict(a, t=c.t0))
    pos = tmp["pos"]
    look = a.get("on") or a.get("look_at")
    amt = float(_p(sh, "amount", 0.18))
    p1 = (pos[0] + amt * 0.6, pos[1] + amt * 0.3, pos[2] - amt * 0.2)
    return [_pos(pos, look, a.get("lens"), t=c.t0, place=a.get("place", "auto")),
            _pos(p1, look, a.get("lens"), t=c.t1, place=a.get("place", "auto"))]


# ── moves with measured numbers (move-catalogue §38, §49, §58, §63; added 2026-10-29) ──────────────────────
# The defaults are the measurements the catalogue entries cite: the course notes = a cinematography course's notes
# (our capture of real rigs, 360p), Scenario = the previs-to-picture authors' one shot. Where a default is a
# house value rather than a measurement, the comment says so.
def mv_snap_zoom(c, sh):
    """move-catalogue §49: a snap zoom on a line or a beat, as the course measured it (course notes): a hold, ×1.9
    in about 0.4 s, then a settle to ×2.2 by about 1.1 s. The camera does not move. In a film it is built in
    the edit; this is the previs and the shape the edit copies."""
    a = _framing(c, sh, "from")
    lens0 = float(a.get("lens", c.lens))
    ratio, snap_ratio = float(_p(sh, "ratio", 2.2)), float(_p(sh, "snap_ratio", 1.9))
    snap, settle = float(_p(sh, "dur", 0.41)), float(_p(sh, "settle", 0.67))
    ts = c.at(_p(sh, "start", None), c.t0 + min(1.0, 0.3 * (c.t1 - c.t0)))
    ts = max(c.t0, min(ts, c.t1 - 0.2))
    t_snap = min(ts + snap, c.t1)
    t_set = min(t_snap + settle, c.t1)
    pin = dict(a); pin.pop("lens", None)
    if "on" in pin:                                      # a zoom does not move the camera: pin it where it starts
        tmp = c.bl.solve_camera_key(c.spec, dict(pin, t=c.t0, lens=lens0))
        pin = {"pos": tmp["pos"], "look_at": pin["on"], "place": pin.get("place", "auto")}
    keys = [dict(pin, t=c.t0, lens=lens0), dict(pin, t=ts, lens=lens0, ease="stop"),
            dict(pin, t=t_snap, lens=lens0 * snap_ratio),
            dict(pin, t=t_set, lens=lens0 * ratio, ease="stop"), dict(pin, t=c.t1, lens=lens0 * ratio)]
    return _dedupe(keys)


def _front_loaded(u: float, k: float = 1.6) -> float:
    """0 → 1 with no speed at either end and the peak early, so the move lands slowly: the ease-out shape the
    course measured on carried tilts, pivots and pulls (k is a house value)."""
    u = max(0.0, min(1.0, u))
    w = 1 - (1 - u) ** k
    return w * w * (3 - 2 * w)


def mv_vertical_pivot(c, sh):
    """move-catalogue §58 (course notes): the subject keeps one size and one place in frame while the camera sinks
    from slightly above the eyes to slightly below them, tilting up on a long lens (50–100 mm), so the world
    pivots behind them: the background shifts 13–56 % of the frame height (default `pivot` 0.45 of it),
    easing out. The same framing at both ends is what makes it the most model-friendly move in the course."""
    a = _framing(c, sh, "from")
    subj = a.get("on")
    if not subj:
        raise ValueError("vertical_pivot needs `on` (the subject that holds still in frame)")
    size = sh.get("from", {}).get("size") or sh.get("size") or "MCU"
    lens = float(sh.get("from", {}).get("lens") or sh.get("lens") or 70.0)
    d = c.dist_for(subj, size, lens)
    theta = float(_p(sh, "pivot", 0.45)) * c.vfov(lens)    # degrees the view turns = the background's shift
    above = float(_p(sh, "above", 0.6))                    # [house] share of the pivot spent above the eyes
    f = math.radians(c.facing(subj, c.t0) + float(a.get("side", 0)))
    ts, te = _timing(c, sh)

    def k(t):
        u = 0.0 if t <= ts else 1.0 if t >= te else (t - ts) / (te - ts)
        phi = math.radians(theta * above - theta * _front_loaded(u))
        P = c.point(subj, t)
        pos = (P[0] + math.cos(f) * d * math.cos(phi), P[1] + math.sin(f) * d * math.cos(phi), P[2] + d * math.sin(phi))
        return _pos(pos, subj, lens, on=subj, place=a.get("place", "auto"))
    return _dense(c, c.t0, c.t1, 0.25, k, subj=subj)


def mv_ceiling_exit(c, sh):
    """move-catalogue §63 (course notes): as the subject leaves, the camera tilts up off it to a neutral surface
    (a ceiling, the sky) — 58–66 % of the frame height over about 5 s, fast at first and landing slowly
    (17–19 → 4–7 %/s). The camera stays where it is."""
    a = _framing(c, sh, "from")
    subj = a.get("on") or a.get("look_at")
    tmp = c.bl.solve_camera_key(c.spec, dict(a, t=c.t0))
    pos = tmp["pos"]
    lens = float(a.get("lens", c.lens))
    ts = c.at(_p(sh, "start", None), c.t0 + min(1.0, 0.25 * (c.t1 - c.t0)))
    ts = max(c.t0, min(ts, c.t1 - 0.5))
    te = min(c.t1, ts + float(_p(sh, "dur", 5.0)))
    tgt = c.point(subj, ts) if isinstance(subj, str) else tuple(float(v) for v in subj)
    yaw, pitch = yaw_pitch(_sub(tgt, pos))
    p1 = min(85.0, pitch + float(_p(sh, "frame_heights", 0.62)) * c.vfov(lens))
    D = max(2.0, math.dist(pos, tgt))

    def look(p_):
        return [round(v, 4) for v in _v(pos, dir_from(yaw, p_), D)]
    # the landing: 55 % of the travel in the first 30 % of the time, then a long settle (the measured profile)
    keys = [_pos(pos, subj, lens, t=c.t0), _pos(pos, look(pitch), lens, t=ts, ease="stop"),
            _pos(pos, look(pitch + (p1 - pitch) * 0.55), lens, t=ts + (te - ts) * 0.3),
            _pos(pos, look(p1), lens, t=te, ease="stop"), _pos(pos, look(p1), lens, t=c.t1)]
    return _dedupe(keys)


def mv_let_go_crane(c, sh):
    """move-catalogue §38 (Scenario previs-to-picture, one 15 s shot): track alongside the subject, then crane
    up while the camera SLOWS, so the subject keeps its speed and pulls away; the lens eases a little wider
    and the aim blends from the subject toward a fixed point ahead for the reveal. Authors: 6.5–7.8 m off,
    1.5 m high, 28 → 26 mm, up to 30 m. Default altitude 12 m [house]: 30 m is a drone's height, so give
    `altitude: 30` with `rig: drone` for the authors' version, on a 12–15 s shot."""
    subj = _framing(c, sh, "from").get("on")
    if not subj:
        raise ValueError("let_go_crane needs `on` (the subject that is let go)")
    T0, T1 = c.t0, c.t1
    dist, h0 = float(_p(sh, "distance", 7.0)), float(_p(sh, "height", 1.5))
    alt = float(_p(sh, "altitude", 12.0))
    lens0, lens1 = float(_p(sh, "lens", 28.0)), float(_p(sh, "to_lens", 26.0))
    blend = float(_p(sh, "aim_blend", 0.6))                  # [house] how far the aim leaves the subject
    tr = c.at(_p(sh, "release", None), T0 + 0.45 * (T1 - T0))
    tr = max(T0, min(tr, T1 - 0.5))
    f0 = math.radians(c.facing(subj, T0) + float(_p(sh, "side", 90.0)))
    off = (math.cos(f0) * dist, math.sin(f0) * dist)
    dur = float(c.spec.get("duration", T1))
    ga, gb = c.ground(subj, max(0.0, tr - 0.25)), c.ground(subj, min(dur, tr + 0.25))
    span_v = max(1e-6, min(dur, tr + 0.25) - max(0.0, tr - 0.25))
    vel = ((gb[0] - ga[0]) / span_v, (gb[1] - ga[1]) / span_v)   # the subject's speed at the release
    g_r, g_0, g_1 = c.ground(subj, tr), c.ground(subj, T0), c.ground(subj, T1)
    hd = math.atan2(g_1[1] - g_0[1], g_1[0] - g_0[0]) if math.dist(g_0, g_1) > 0.3 else math.radians(c.facing(subj, T1))
    ahead = float(_p(sh, "reveal_dist", 25.0))
    R = (g_1[0] + math.cos(hd) * ahead, g_1[1] + math.sin(hd) * ahead, 0.0)
    span = max(T1 - tr, 1e-6)
    keep = float(_p(sh, "keep_in", 0.6))                   # [house] the subject stays within this share of the half-frame

    def angle(u_, v_):
        nu, nv = math.hypot(*u_), math.hypot(*v_)
        return math.degrees(math.acos(max(-1.0, min(1.0, sum(a_ * b_ for a_, b_ in zip(u_, v_)) / max(nu * nv, 1e-9)))))

    def k(t):
        if t <= tr:
            g = c.ground(subj, t)
            return _pos((g[0] + off[0], g[1] + off[1], h0), list(c.point(subj, t)), lens0, on=subj)
        u = (t - tr) / span
        s = u * u * (3 - 2 * u)
        disp = span * (u - u ** 3 + u ** 4 / 2)              # ∫(1 − smoothstep): the camera slows to a stop
        pos = (g_r[0] + off[0] + vel[0] * disp, g_r[1] + off[1] + vel[1] * disp, h0 + (alt - h0) * s)
        lens = lens0 + (lens1 - lens0) * s
        ps = c.point(subj, t)
        vf, hf = c.bl.vfov_hfov(lens, c.w, c.h)
        lim = keep * min(vf, hf) / 2                        # the authors' clamp: the subject never leaves frame
        to_s = _sub(ps, pos)
        lo, hi = 0.0, blend * s
        for _ in range(14):                                 # the largest blend toward the reveal that keeps them in
            mid = (lo + hi) / 2
            look_ = [ps[j] + (R[j] - ps[j]) * mid for j in range(3)]
            if angle(_sub(look_, pos), to_s) <= lim:
                lo = mid
            else:
                hi = mid
        look = [ps[j] + (R[j] - ps[j]) * lo for j in range(3)]
        return _pos(pos, look, lens, on=subj)
    return _dense(c, T0, T1, 0.25, k, subj=subj)


# ── aerial, FPV and insect moves (references/aerial-and-fpv.md; the numbers are assets/aerial-moves.json) ──
# A drone shot in an ad is a slice of a longer flight: the camera is already moving at the cut and still
# moving at the next one, at the speed the move table gives. So these moves default to a SPEED and derive
# the distance from the shot's length, instead of crossing a fixed distance in whatever time the shot has —
# a half orbit squeezed into six seconds is a 13 m/s whirl, not a drone orbit.
_AERIAL_CACHE: dict = {}


def aerial_table() -> dict:
    """assets/aerial-moves.json, loaded once."""
    if not _AERIAL_CACHE:
        import json, os
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "aerial-moves.json")
        with open(p, encoding="utf-8") as fh:
            _AERIAL_CACHE.update(json.load(fh))
    return _AERIAL_CACHE


def aerial_spec(blocking_name: str) -> tuple:
    """(table move name, its row) for a blocking move name, or (None, None)."""
    for k, v in aerial_table().get("moves", {}).items():
        if v.get("blocking") == blocking_name:
            return k, v
    return None, None


def _mid(rng, default):
    return (float(rng[0]) + float(rng[1])) / 2 if rng else default


def _speed(sh, blocking_name, default):
    _, row = aerial_spec(blocking_name)
    return float(_p(sh, "speed", _mid((row or {}).get("speed_mps"), default)))


def _flight(c, step, fn, settle=False):
    """Dense keys over the whole shot, already moving at both cuts unless `settle` (then it eases)."""
    n = max(2, int(math.ceil((c.t1 - c.t0) / step)))
    keys = [dict(fn(c.t0 + (c.t1 - c.t0) * i / n), t=c.t0 + (c.t1 - c.t0) * i / n) for i in range(n + 1)]
    for k in (keys[0], keys[-1]):
        k["ease"] = "stop" if settle else "linear"
    return keys


def _centre(c, sh):
    subj = sh.get("on") or sh.get("look_at") or sh.get("center")
    if subj is None:
        raise ValueError(f"{sh.get('move')} needs `on` (or `center`)")
    return subj


def _start_angle(c, sh, subj, default_side):
    base = c.facing(subj, c.t0) if isinstance(subj, str) and c.kind(subj) in ("actor", "vehicle") else 0.0
    return math.radians(base + float(_p(sh, "side", default_side)))


def mv_drone_orbit(c, sh, blocking_name="drone_orbit", r_def=25.0, h_def=12.0, v_def=1.8):
    """A drone circling the subject at `radius` and `height`, at `speed` m/s (or through `degrees`), the lens
    on the subject. Direction: `direction` "left" (counter-clockwise, default) or "right". A moving subject
    is orbited where it is at each moment."""
    subj = _centre(c, sh)
    R = float(_p(sh, "radius", r_def))
    H = float(_p(sh, "height", h_def))
    dur = c.t1 - c.t0
    if _p(sh, "degrees", None) is not None:
        sweep = math.radians(float(_p(sh, "degrees", 0)))
    else:
        sweep = _speed(sh, blocking_name, v_def) * dur / R
    if _p(sh, "direction", "left") == "right":
        sweep = -abs(sweep)
    a0 = _start_angle(c, sh, subj, 150.0)
    R1 = float(_p(sh, "radius_to", R))
    H1 = float(_p(sh, "height_to", H))
    lens = sh.get("lens", 24)

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        g = c.ground(subj, t)
        a = a0 + sweep * f
        r = R + (R1 - R) * f
        return _pos((g[0] + math.cos(a) * r, g[1] + math.sin(a) * r, H + (H1 - H) * f),
                    subj if isinstance(subj, str) else [float(v) for v in subj], lens)
    return _flight(c, float(_p(sh, "step", 0.25)), k, settle=bool(_p(sh, "settle", False)))


def mv_helix(c, sh):
    """Orbit while climbing: one turn every `secs_per_turn` (8-12 s), rising `climb` metres over the shot;
    `radius_to` widens it as it climbs (the DJI QuickShot Helix does). Tighter than an orbit by default —
    a helix turns fast enough to read only on a tall, narrow subject."""
    spt = float(_p(sh, "secs_per_turn", 10.0))
    dur = c.t1 - c.t0
    H = float(_p(sh, "height", 4.0))
    sh2 = dict(sh, degrees=float(_p(sh, "degrees", 360.0 * dur / spt)), height=H,
               height_to=float(_p(sh, "height_to", H + float(_p(sh, "climb", 1.2 * dur)))))
    sh2.setdefault("radius", _p(sh, "radius", 8.0))
    return mv_drone_orbit(c, sh2, "helix")


def mv_parallax_orbit(c, sh):
    """A slow, close arc past a near foreground (`past`, 3-6 m from the drone's path) that slides across the
    frame while the subject behind it holds."""
    sh2 = dict(sh)
    sh2.setdefault("radius", _p(sh, "radius", 15.0))
    sh2.setdefault("height", _p(sh, "height", 5.0))
    return mv_drone_orbit(c, sh2, "parallax_orbit", r_def=15.0, h_def=5.0, v_def=1.5)


def mv_boomerang(c, sh):
    """The DJI Boomerang: an oval round the subject, from the start (one end of the long axis) to the far
    side and back, highest at the far end. `radius` is the start distance; `width` the short half-axis;
    `rise` the climb at the far end. Speed-led like an orbit: a six-second slice of the oval."""
    subj = _centre(c, sh)
    A = float(_p(sh, "radius", 15.0))
    B = float(_p(sh, "width", 0.6 * A))
    H0 = float(_p(sh, "height", 3.0))
    rise = float(_p(sh, "rise", 8.0))
    dur = c.t1 - c.t0
    perim = 2 * math.pi * math.sqrt((A * A + B * B) / 2)
    if _p(sh, "degrees", None) is not None:
        sweep = math.radians(float(_p(sh, "degrees", 0)))
    else:
        sweep = 2 * math.pi * min(1.0, _speed(sh, "boomerang", 4.0) * dur / perim)
    a0 = _start_angle(c, sh, subj, 180.0)
    lens = sh.get("lens", 24)

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        th = sweep * f
        g = c.ground(subj, t)
        x, y = A * math.cos(th), B * math.sin(th)
        ca, sa = math.cos(a0), math.sin(a0)
        z = H0 + rise * math.sin(th / 2) ** 2
        return _pos((g[0] + x * ca - y * sa, g[1] + x * sa + y * ca, z), subj, lens)
    return _flight(c, float(_p(sh, "step", 0.25)), k)


def mv_hover_pan(c, sh):
    """The drone holds its spot (`pos`, or `dist` from the subject at `height`) while the camera pans
    `degrees` (default 15-25 s per half-turn: ~10°/s) across the place, tilted `tilt`."""
    subj = sh.get("on") or sh.get("look_at")
    dur = c.t1 - c.t0
    if "pos" in sh:
        P = [float(v) for v in sh["pos"]]
    else:
        g = c.ground(subj, c.t0)
        a = _start_angle(c, sh, subj, 180.0)
        d = float(_p(sh, "dist", 60.0))
        P = [g[0] + math.cos(a) * d, g[1] + math.sin(a) * d, float(_p(sh, "height", 40.0))]
    if subj is not None:
        g = c.ground(subj, c.t0)
        yaw0 = math.degrees(math.atan2(g[1] - P[1], g[0] - P[0]))
    else:
        yaw0 = float(_p(sh, "heading", 0.0))
    _, row = aerial_spec("hover_pan")
    rate = float(_p(sh, "deg_per_s", _mid((row or {}).get("deg_per_s"), 9.6)))
    deg = float(_p(sh, "degrees", rate * dur))
    if _p(sh, "direction", "left") == "right":
        deg = -abs(deg)
    tilt = float(_p(sh, "tilt", -15.0))
    lens = sh.get("lens", 24)

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        y = yaw0 - deg / 2 + deg * f
        d = dir_from(y, tilt)
        return _pos(P, [P[0] + d[0] * 80, P[1] + d[1] * 80, P[2] + d[2] * 80], lens)
    return _flight(c, float(_p(sh, "step", 0.25)), k)


def _heading_from(c, sh, subj):
    if _p(sh, "heading", None) is not None:
        return math.radians(float(_p(sh, "heading", 0.0)))
    if isinstance(subj, str) and c.kind(subj) in ("actor", "vehicle"):
        return math.radians(c.facing(subj, c.t0))
    return 0.0


def mv_tilt_down_reveal(c, sh):
    """Flying level out over an edge at `height` while the gimbal tilts from `tilt_from` (near level) to
    `tilt_to` (−60°) and the place below opens up. From `from_point` along `heading`, or over `on`."""
    subj = sh.get("on")
    hd = _heading_from(c, sh, subj)
    dur = c.t1 - c.t0
    L = _speed(sh, "tilt_down_reveal", 3.3) * dur
    if "from_point" in sh:
        a = [float(v) for v in sh["from_point"]][:2]
    else:
        g = c.ground(subj, c.t0)
        a = [g[0] - math.cos(hd) * L * 0.8, g[1] - math.sin(hd) * L * 0.8]
    H = float(_p(sh, "height", 30.0))
    t0_, t1_ = float(_p(sh, "tilt_from", -5.0)), float(_p(sh, "tilt_to", -60.0))
    lens = sh.get("lens", 24)

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        e = f * f * (3 - 2 * f)
        P = (a[0] + math.cos(hd) * L * f, a[1] + math.sin(hd) * L * f, H)
        d = dir_from(math.degrees(hd), t0_ + (t1_ - t0_) * e)
        return _pos(P, [P[0] + d[0] * 60, P[1] + d[1] * 60, P[2] + d[2] * 60], lens)
    return _flight(c, float(_p(sh, "step", 0.25)), k)


def mv_pedestal(c, sh):
    """Straight up the face of the subject at a constant climb (`speed`), the camera level."""
    subj = _centre(c, sh)
    dur = c.t1 - c.t0
    v = _speed(sh, "pedestal", 2.0)
    z0 = float(_p(sh, "from_height", 1.5))
    a = _start_angle(c, sh, subj, 0.0)
    d = float(_p(sh, "dist", 20.0))
    lens = sh.get("lens", 24)

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        g = c.ground(subj, t)
        z = z0 + v * dur * f
        return _pos((g[0] + math.cos(a) * d, g[1] + math.sin(a) * d, z), [g[0], g[1], z], lens)
    return _flight(c, float(_p(sh, "step", 0.25)), k)


def mv_rocket(c, sh):
    """The DJI Rocket: straight up over the subject, looking straight down as the ground falls away."""
    subj = _centre(c, sh)
    dur = c.t1 - c.t0
    v = _speed(sh, "rocket", 2.0)
    z0 = float(_p(sh, "from_height", 4.0))
    lens = sh.get("lens", 24)

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        g = c.ground(subj, t)
        return _pos((g[0] + 0.001, g[1], z0 + v * dur * f), [g[0], g[1], 0.0], lens, roll=0.0)
    return _flight(c, float(_p(sh, "step", 0.25)), k)


def mv_drone_side_follow(c, sh):
    """Alongside a travelling subject at a fixed `distance` (6-18 m; closer is more urgent) and `height`."""
    d = float(_p(sh, "distance", 10.0))
    side = -1.0 if _p(sh, "side_of", "right") == "right" else 1.0
    return mv_chase(c, dict(sh, offset=[float(_p(sh, "along", 0.0)), side * d, float(_p(sh, "height", 4.0))]))


def mv_drone_push_in(c, sh):
    """Straight in toward the subject at a constant slow speed, stopping before it fills the frame."""
    subj = _centre(c, sh)
    dur = c.t1 - c.t0
    v = _speed(sh, "drone_push_in", 1.4)
    d1 = float(_p(sh, "to_dist", 12.0))
    d0 = float(_p(sh, "from_dist", d1 + v * dur))
    H = float(_p(sh, "height", 8.0))
    a = _start_angle(c, sh, subj, 0.0)
    lens = sh.get("lens", 24)
    g0 = c.ground(subj, c.t0)                             # a line over the ground at its own speed, the lens live on them

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        dd = d0 + (d1 - d0) * f
        return _pos((g0[0] + math.cos(a) * dd, g0[1] + math.sin(a) * dd, H), subj, lens)
    keys = _flight(c, float(_p(sh, "step", 0.5)), k)
    keys[-1]["ease"] = "stop"
    return keys


def _route_points(c, sh, default):
    pts = sh.get("route")
    if not pts:
        return default()
    out = []
    for q in pts:
        if isinstance(q, str):
            p = c.point(q, c.t0)
            out.append((p[0], p[1], float(_p(sh, "height", 1.2))))
        else:
            q = [float(v) for v in q]
            out.append((q[0], q[1], q[2] if len(q) > 2 else float(_p(sh, "height", 1.2))))
    return out


def _poly(pts):
    S = [0.0]
    for a, b in zip(pts, pts[1:]):
        S.append(S[-1] + math.dist(a, b))
    return S


def _along(pts, S, s):
    s = max(0.0, min(S[-1], s))
    for i in range(len(S) - 1):
        if S[i + 1] >= s:
            f = (s - S[i]) / max(S[i + 1] - S[i], 1e-9)
            return tuple(pts[i][j] + (pts[i + 1][j] - pts[i][j]) * f for j in range(3))
    return pts[-1]


def mv_route(c, sh, blocking_name="cinewhoop_oner", v_def=2.5):
    """A flight along a `route` of waypoints ([x, y, z] or names) at a constant speed, looking `ahead`
    metres down the path (or at `look_at`). With no route: low through the scene past `on`."""
    subj = sh.get("on")
    dur = c.t1 - c.t0
    v = _speed(sh, blocking_name, v_def)

    def default():
        g = c.ground(subj, c.t0)
        hd = _heading_from(c, sh, subj) + math.radians(float(_p(sh, "side", 25.0)))
        L = v * dur
        z = float(_p(sh, "height", 1.2))
        return [(g[0] - math.cos(hd) * L * 0.6, g[1] - math.sin(hd) * L * 0.6, z),
                (g[0] + math.cos(hd) * L * 0.4 - math.sin(hd) * 1.2, g[1] + math.sin(hd) * L * 0.4 + math.cos(hd) * 1.2, z)]
    pts = _route_points(c, sh, default)
    S = _poly(pts)
    L = min(S[-1], v * dur) if "route" in sh and _p(sh, "speed", None) is not None else S[-1]
    ahead = float(_p(sh, "ahead", 6.0))
    look = sh.get("look_at")
    lens = sh.get("lens", 18)

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        s = L * f
        P = _along(pts, S, s)
        if look is not None:
            return _pos(P, look, lens)
        Q = _along(pts, S, s + ahead)
        if math.dist(P, Q) < 0.5:                       # the end of the route: carry on the way it was going
            Pb = _along(pts, S, s - ahead)
            Q = tuple(P[j] + (P[j] - Pb[j]) for j in range(3))
        return _pos(P, list(Q), lens)
    return _flight(c, float(_p(sh, "step", 0.25)), k)


def mv_gap_fly_through(c, sh):
    """Slowly through a gap (`gap`: a set piece or opening's centre, or a point) — the route threads it."""
    if sh.get("gap") and not sh.get("route"):
        gp = c.point(sh["gap"], c.t0)
        subj = sh.get("on")
        hd = _heading_from(c, sh, subj)
        v = _speed(sh, "gap_fly_through", 1.35)
        L = v * (c.t1 - c.t0)
        z = float(_p(sh, "height", gp[2] if len(gp) > 2 else 1.2))
        sh = dict(sh, route=[[gp[0] - math.cos(hd) * L * 0.5, gp[1] - math.sin(hd) * L * 0.5, z],
                             [gp[0] + math.cos(hd) * L * 0.5, gp[1] + math.sin(hd) * L * 0.5, z]])
    return mv_route(c, sh, "gap_fly_through", 1.35)


def mv_hole_flyover(c, sh):
    """A golf hole from the ball's point of view: lifting off the tee low, climbing LATE along the strategy
    line (`route`: tee, landing area, green — or `on` and `heading`), over the hazards at `peak`, descending
    toward the green to `green_height`, the camera tipping down as it goes."""
    subj = sh.get("on")
    dur = c.t1 - c.t0
    v = _speed(sh, "hole_flyover", 5.0)

    def default():
        g = c.ground(subj, c.t0)
        hd = _heading_from(c, sh, subj)
        L = v * dur
        return [(g[0] - math.cos(hd) * L * 0.1, g[1] - math.sin(hd) * L * 0.1, 0.0),
                (g[0] + math.cos(hd) * L * 0.9, g[1] + math.sin(hd) * L * 0.9, 0.0)]
    pts = [(p[0], p[1], 0.0) for p in _route_points(c, sh, default)]
    S = _poly(pts)
    h0 = float(_p(sh, "tee_height", 3.0))
    hp = float(_p(sh, "peak", h0 + min(25.0, 0.3 * S[-1])))     # a slice of a hole climbs less than the whole hole
    h1 = float(_p(sh, "green_height", h0 + 0.5 * (hp - h0)))
    climb_at = float(_p(sh, "climb_at", 0.2))           # it stays low until here: 'climbing too early removes the tension'
    lens = sh.get("lens", 24)

    def z_of(f):
        if f <= climb_at:
            return h0
        if f <= 0.65:
            u = (f - climb_at) / (0.65 - climb_at)
            return h0 + (hp - h0) * (u * u * (3 - 2 * u))
        u = (f - 0.65) / 0.35
        return hp + (h1 - hp) * (u * u * (3 - 2 * u))

    def k(t):
        f = (t - c.t0) / max(dur, 1e-6)
        P = _along(pts, S, S[-1] * f)
        P = (P[0], P[1], z_of(f))
        G = pts[-1]
        Q = _along(pts, S, min(S[-1], S[-1] * f + 25.0))
        aim = (Q[0], Q[1], 0.0) if math.dist(P[:2], G[:2]) > 30 else G
        return _pos(P, list(aim), lens)
    return _flight(c, float(_p(sh, "step", 0.25)), k)


def _hash01(*xs) -> float:
    """A deterministic number in 0..1 from the arguments (the same spec flies the same path)."""
    h = 0
    for x in xs:
        h = (h * 1000003 + int(round(float(x) * 1000))) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5bd1e995) & 0xFFFFFFFF
    return ((h ^ (h >> 15)) & 0xFFFF) / 65535.0


def bee_profile(u: float, accel_share: float = 0.75) -> float:
    """Distance done (0..1) at u (0..1) through one dash: the speed ramps up over `accel_share` of it and
    falls to nothing over the rest — 'accelerate slowly and decelerate rapidly' (Hejazi et al. 2022)."""
    a = accel_share
    if u <= a:
        return (u * u / (2 * a)) / 0.5
    tail = ((u - u * u / 2) - (a - a * a / 2)) / (1 - a)
    return (a / 2 + tail) / 0.5


def mv_bee_path(c, sh):
    """A bee's flight to the subject: dashes that ease forward and brake hard into tight turns a hand-width
    wide (13-22 cm), weaving toward `on` a little above the ground; the lens looks where it goes, then at
    what it arrives at. Mean speed ~0.71 m/s (`speed`)."""
    subj = _centre(c, sh)
    dur = c.t1 - c.t0
    v = _speed(sh, "bee_path", 0.71)
    _, row = aerial_spec("bee_path")
    r_turn = _mid((row or {}).get("turn_radius_m"), 0.17)
    z0 = float(_p(sh, "height", 0.3))
    goal = c.ground(subj, c.t1)
    a = _start_angle(c, sh, subj, 180.0)
    dist = float(_p(sh, "dist", max(1.0, v * dur * 0.55)))
    P = [goal[0] + math.cos(a) * dist, goal[1] + math.sin(a) * dist]
    seed = float(_p(sh, "seed", 1.0))
    # the legs: a dash (slow up, hard down), then a turn on a tight arc at walking-pace-for-a-bee
    legs, t, i = [], c.t0, 0
    hd = math.atan2(goal[1] - P[1], goal[0] - P[0])
    sign = 1.0
    while t < c.t1 and i < 64:
        L = 0.45 + 0.4 * _hash01(seed, i, 1)
        T = L / v
        legs.append(("dash", t, t + T, tuple(P), hd, L))
        P = [P[0] + math.cos(hd) * L, P[1] + math.sin(hd) * L]
        t += T
        to_goal = math.atan2(goal[1] - P[1], goal[0] - P[0])
        dev = math.radians(35 + 50 * _hash01(seed, i, 2)) * sign
        new_hd = to_goal + dev
        turn = (new_hd - hd + math.pi) % (2 * math.pi) - math.pi
        Tt = max(0.18, abs(turn) * r_turn / 0.35)
        legs.append(("turn", t, t + Tt, tuple(P), hd, turn))
        cx = P[0] + math.cos(hd + math.copysign(math.pi / 2, turn)) * r_turn
        cy = P[1] + math.sin(hd + math.copysign(math.pi / 2, turn)) * r_turn
        ang0 = math.atan2(P[1] - cy, P[0] - cx)
        P = [cx + math.cos(ang0 + turn) * r_turn, cy + math.sin(ang0 + turn) * r_turn]
        hd = hd + turn
        t += Tt
        sign = -sign
        i += 1
    lens = sh.get("lens", 18)

    def at(tt):
        for kind, ta, tb, P0, h0, x in legs:
            if tt <= tb + 1e-9:
                u = max(0.0, min(1.0, (tt - ta) / max(tb - ta, 1e-9)))
                if kind == "dash":
                    s = x * bee_profile(u)
                    return (P0[0] + math.cos(h0) * s, P0[1] + math.sin(h0) * s), h0
                cx = P0[0] + math.cos(h0 + math.copysign(math.pi / 2, x)) * r_turn
                cy = P0[1] + math.sin(h0 + math.copysign(math.pi / 2, x)) * r_turn
                ang0 = math.atan2(P0[1] - cy, P0[0] - cx)
                return (cx + math.cos(ang0 + x * u) * r_turn, cy + math.sin(ang0 + x * u) * r_turn), h0 + x * u
        kind, ta, tb, P0, h0, x = legs[-1]
        return (P0[0], P0[1]), h0

    def k(tt):
        (x, y), h = at(tt)
        z = z0 + 0.08 * math.sin(2 * math.pi * 0.4 * (tt - c.t0) + seed)
        f = (tt - c.t0) / max(dur, 1e-6)
        d = dir_from(math.degrees(h), -12.0)
        ahead = [x + d[0] * 1.5, y + d[1] * 1.5, z + d[2] * 1.5]
        w = max(0.0, min(1.0, (f - 0.75) / 0.2))          # it arrives: the lens finds what it came for
        if w > 0:
            q = c.point(subj, tt)
            n_ = math.dist(q, (x, y, z)) or 1.0
            q = [x + (q[0] - x) / n_ * 1.5, y + (q[1] - y) / n_ * 1.5, z + (q[2] - z) / n_ * 1.5]
            w = w * w * (3 - 2 * w)
            ahead = [ahead[j] + (q[j] - ahead[j]) * w for j in range(3)]
        return _pos((x, y, z), ahead, lens)
    keys = _flight(c, float(_p(sh, "step", 1 / 24)), k)
    return keys


def mv_mosquito_path(c, sh):
    """A mosquito round a person: slow (0.2-0.6 m/s), slipping sideways and backwards in segments that turn
    50-200° at a time, keeping 0.6-1.2 m from the skin — and the lens stays on them, so the view rarely
    points where it travels (Iams 2012). On `on` (an actor: their `part`, default head)."""
    subj = _centre(c, sh)
    dur = c.t1 - c.t0
    v = _speed(sh, "mosquito_path", 0.4)
    part = _p(sh, "part", "head")
    tgt = (lambda t: c.point(f"{subj}.{part}", t)) if c.kind(subj) == "actor" else (lambda t: c.point(subj, t))
    seed = float(_p(sh, "seed", 3.0))
    a = _start_angle(c, sh, subj, 40.0)
    # the path is flown in the person's own frame (it keeps up with them), so the distance band holds
    O = [math.cos(a) * 0.9, math.sin(a) * 0.9, 0.1]
    hd = a + math.pi / 2
    segs, t, i = [], c.t0, 0
    while t < c.t1 and i < 64:
        T = 0.6 + 0.4 * _hash01(seed, i, 7)
        dist = math.hypot(O[0], O[1])
        turn = math.radians(50 + 150 * _hash01(seed, i, 8)) * (1 if _hash01(seed, i, 9) > 0.5 else -1)
        hd = hd + turn
        away = math.atan2(O[1], O[0])
        if dist > 1.0:
            hd = away + math.pi + 0.6 * math.sin(hd - away)     # drawn back in toward the skin
        elif dist < 0.75:
            hd = away + 0.6 * math.sin(hd - away)                # and out again
        Q = [O[0] + math.cos(hd) * v * T, O[1] + math.sin(hd) * v * T, O[2] + (0.05 * math.sin(i) - O[2]) * 0.5]
        segs.append((t, t + T, tuple(O), tuple(Q)))
        O, t, i = Q, t + T, i + 1
    lens = sh.get("lens", 24)

    def k(tt):
        for ta, tb, A, B in segs:
            if tt <= tb + 1e-9:
                u = max(0.0, min(1.0, (tt - ta) / max(tb - ta, 1e-9)))
                u = u * u * (3 - 2 * u)
                On = [A[j] + (B[j] - A[j]) * u for j in range(3)]
                break
        else:
            On = list(segs[-1][3])
        T_ = tgt(tt)
        return _pos([T_[0] + On[0], T_[1] + On[1], T_[2] + On[2]], list(T_), lens)
    return _flight(c, float(_p(sh, "step", 1 / 24)), k)


# name: (function, default rig, words that confirm it in camera_motion, what it is for)
LIBRARY = {
    "static": (mv_static, "locked", set(), "a held frame; the world moves inside it"),
    "locked": (mv_static, "locked", set(), "the same, said as a rig"),
    "drift": (mv_drift, "handheld", set(), "a held frame that lives: settle, breathe, creep"),
    "push_in": (mv_push_in, "dolly", {"pushes in"}, "significance arriving; it must land on new information"),
    "dolly_in": (mv_push_in, "dolly", {"pushes in"}, "push_in"),
    "creep": (mv_creep, "dolly", {"pushes in"}, "a push so slow it is felt, not seen, the whole shot"),
    "pull_out": (mv_pull_out, "dolly", {"pulls back"}, "the world is bigger than they thought"),
    "pull_back": (mv_pull_out, "dolly", {"pulls back"}, "pull_out"),
    "dolly_out": (mv_pull_out, "dolly", {"pulls back"}, "pull_out"),
    "arc": (mv_arc, "dolly", {"arcs"}, "the relationship turns; background slides behind"),
    "arc_left": (mv_arc, "dolly", {"arcs"}, "arc to camera-left"),
    "arc_right": (mv_arc, "dolly", {"arcs"}, "arc to camera-right"),
    "orbit": (mv_orbit, "steadicam", {"arcs"}, "a half circle round the subject"),
    "orbit_360": (mv_orbit_360, "steadicam", {"arcs"}, "the full circle"),
    "bullet_time": (mv_bullet_time, "robo", {"arcs"}, "a fast 180° round a moment held still"),
    "spiral": (mv_spiral, "crane", {"arcs", "rises"}, "orbit + rise + push in one move"),
    "boom_up": (lambda c, s: mv_boom(c, s, True), "crane", {"rises"}, "pedestal up: altitude, not angle"),
    "boom_down": (lambda c, s: mv_boom(c, s, False), "crane", {"lowers"}, "pedestal down"),
    "crane_up": (lambda c, s: mv_crane(c, s, True), "crane", {"rises", "pulls back"}, "rising off a scene: release, abandonment"),
    "crane_down": (lambda c, s: mv_crane(c, s, False), "crane", {"lowers", "pushes in"}, "descending in: commitment"),
    "swoop": (mv_swoop, "crane", {"lowers", "pushes in"}, "down out of the air into the scene"),
    "hero_low": (mv_hero_low, "dolly", {"pushes in"}, "a low wide lens pushing up at someone who wins"),
    "dolly_zoom": (mv_dolly_zoom, "dolly", {"pushes in", "pulls back", "zooms"}, "vertigo: the subject holds size while the world warps"),
    "zoom_in": (lambda c, s: mv_zoom(c, s), "tripod", {"zooms"}, "selection, not approach"),
    "zoom_out": (lambda c, s: mv_zoom(c, dict(s, to=dict(s.get("to", {}), lens=s.get("to", {}).get("lens", 18)))), "tripod",
                 {"zooms"}, "zoom back"),
    "crash_zoom": (lambda c, s: mv_zoom(c, s, crash=True), "handheld", {"zooms"}, "a violent zoom in ~0.25 s"),
    "yoyo_zoom": (lambda c, s: mv_zoom(c, s, back=True), "tripod", {"zooms"}, "in and back out"),
    "pan": (mv_pan, "tripod", {"pans"}, "a reveal beside the subject; it must arrive at something"),
    "tilt": (mv_pan, "tripod", {"tilts"}, "a vertical reveal; the native move in 9:16"),
    "pan_reveal": (mv_pan, "tripod", {"pans"}, "pan that lands on the payload"),
    "tilt_reveal": (mv_pan, "tripod", {"tilts"}, "tilt that lands on the payload"),
    "whip_pan": (lambda c, s: mv_pan(c, s, whip=True), "handheld", {"pans"}, "a whip between two subjects"),
    "pivot_whip": (mv_pivot_whip, "shoulder", {"pans"}, "move-catalogue §1: the reaction you cannot avoid"),
    "rack_focus": (mv_rack_focus, "locked", set(), "attention moves inside the frame, no cut"),
    "deep_to_near_rack": (mv_deep_to_near, "locked", set(), "move-catalogue §7: two ends of a geography, one shot"),
    "truck": (mv_truck, "dolly", {"trucks"}, "a lateral glide; parallax does the work"),
    "truck_left": (mv_truck, "dolly", {"trucks"}, "truck to camera-left"),
    "crab": (mv_truck, "dolly", {"trucks"}, "truck"),
    "parallax_slide": (mv_truck, "slider", {"trucks"}, "a short slide past foreground layers"),
    "foreground_wipe": (mv_foreground_wipe, "dolly", {"trucks"}, "something near the lens wipes the frame"),
    "push_through": (mv_push_through, "gimbal", {"pushes in"}, "through a door or window into the scene"),
    "follow": (mv_follow, "steadicam", {"follows"}, "behind a walking subject"),
    "lead": (mv_follow, "steadicam", {"leads"}, "ahead of them, walking backward"),
    "side_track": (mv_follow, "steadicam", {"follows", "leads", "tracks"}, "alongside, in profile"),
    "track": (mv_follow, "steadicam", {"follows", "leads", "tracks"}, "follow"),
    "top_down": (mv_top_down, "drone", set(), "the overhead: geometry becomes graphic"),
    "drone_reveal": (mv_drone_reveal, "drone", {"rises", "pulls back"}, "up and away until the place is the subject"),
    "flyover": (mv_flyover, "drone", {"trucks", "pushes in"}, "across the location at altitude"),
    "fpv_chase": (mv_chase, "fpv", {"follows"}, "a second flyer chasing the subject"),
    "fpv_dive": (mv_fpv_dive, "fpv", {"lowers", "follows"}, "dive from altitude into the chase"),
    "second_participant": (mv_chase, "fpv", {"follows"}, "move-catalogue §33: the camera has a role"),
    "car_chase": (mv_chase, "tracking_vehicle", {"follows"}, "behind the car at speed"),
    "car_lead": (mv_chase, "tracking_vehicle", {"leads"}, "ahead of the car, looking back"),
    "car_side_track": (mv_chase, "tracking_vehicle", {"follows", "leads", "tracks"}, "alongside the car"),
    "snorricam": (lambda c, s: mv_attach(c, s, "snorricam"), "snorricam", set(), "the world swings round a fixed face"),
    "pov": (lambda c, s: mv_attach(c, s, "pov"), "pov", set(), "through their eyes"),
    "car_hood": (lambda c, s: mv_attach(c, s, "car_hood"), "car_mount", set(), "hood mount, looking in at the driver"),
    "car_dash": (lambda c, s: mv_attach(c, s, "car_dash"), "car_mount", set(), "on the dashboard, looking back"),
    "car_passenger": (lambda c, s: mv_attach(c, s, "car_passenger"), "handheld", set(), "from the passenger seat"),
    "car_rear": (lambda c, s: mv_attach(c, s, "car_rear"), "car_mount", set(), "from the back seat, through the windshield"),
    "car_window": (lambda c, s: mv_attach(c, s, "car_window"), "car_mount", set(), "outside the side window, looking in"),
    "car_wheel": (lambda c, s: mv_attach(c, s, "car_wheel"), "car_mount", set(), "low on the wheel arch, road streaming"),
    "worms_eye_rise": (mv_worms_eye_rise, "handheld", {"rises"}, "move-catalogue §2: recovery without a word"),
    "lip_ecu_rise": (mv_lip_ecu_rise, "slider", {"rises", "tilts"}, "move-catalogue §5: the word, then the face"),
    "pinned_detail_orbital": (mv_pinned_orbital, "gimbal", {"arcs"}, "move-catalogue §32: one detail pinned, the world wraps"),
    "reveal": (mv_reveal, "crane", {"pulls back", "rises"}, "from a detail out to the place"),
    "pull_back_reveal": (mv_reveal, "crane", {"pulls back", "rises"}, "reveal"),
    "asphalt_skim": (mv_asphalt_skim, "fpv", {"trucks", "rises"}, "move-catalogue §30: the near-miss, never breaking the glide"),
    "ots": (mv_ots, "locked", set(), "over the shoulder"),
    "split_ots": (mv_ots, "locked", set(), "move-catalogue §4: one line each, the pause between shots"),
    "ceiling_drop": (mv_ceiling_drop, "locked", set(), "move-catalogue §14: a locked frame makes the arrival violent"),
    "motion_control": (mv_motion_control, "robo", set(), "a robot arm hitting marks: snap, hold, snap"),
    "robo_snap": (mv_motion_control, "robo", set(), "motion_control"),
    # measured moves added 2026-10-29 (move-catalogue §38, §49, §58, §63)
    "snap_zoom": (mv_snap_zoom, "tripod", {"zooms"}, "move-catalogue §49: ×1.9 in ~0.4 s, settling to ×2.2 by ~1.1 s"),
    "vertical_pivot": (mv_vertical_pivot, "crane", {"lowers"}, "move-catalogue §58: the subject pinned while the camera sinks and tilts up"),
    "ceiling_exit": (mv_ceiling_exit, "tripod", {"tilts"}, "move-catalogue §63: tilt up off a leaving subject, fast then landing"),
    "let_go_crane": (mv_let_go_crane, "crane", {"tracks", "rises"}, "move-catalogue §38: alongside, then up and slowing so the subject pulls away"),
    # aerial, FPV and insect (aerial-and-fpv.md; speeds and caps in assets/aerial-moves.json)
    "drone_orbit": (mv_drone_orbit, "drone", {"arcs"}, "a slow controlled circle at altitude: scale, reveal, geography"),
    "helix": (mv_helix, "drone", {"arcs", "rises"}, "an orbit that climbs: one turn every 8-12 s, three at most"),
    "parallax_orbit": (mv_parallax_orbit, "drone", {"arcs"}, "a close slow arc past a near foreground"),
    "boomerang": (mv_boomerang, "drone", {"arcs", "rises", "pulls back"}, "the DJI oval: up as it swings away, down as it returns"),
    "hover_pan": (mv_hover_pan, "drone", {"pans"}, "the drone holds; the camera pans ~10°/s across the place"),
    "tilt_down_reveal": (mv_tilt_down_reveal, "drone", {"tilts", "trucks", "pushes in"}, "out over the edge, the camera tilting down"),
    "pedestal": (mv_pedestal, "drone", {"rises"}, "straight up the face of the subject, the camera level"),
    "rocket": (mv_rocket, "drone", {"rises", "pulls back"}, "the DJI Rocket: straight up, looking straight down"),
    "drone_side_follow": (mv_drone_side_follow, "drone", {"follows", "leads", "tracks", "trucks"}, "alongside at a fixed distance"),
    "drone_push_in": (mv_drone_push_in, "drone", {"pushes in"}, "slowly in, stopping before the subject fills the frame"),
    "gap_fly_through": (mv_gap_fly_through, "cinewhoop", {"pushes in", "trucks"}, "threading slowly through a gap"),
    "cinewhoop_oner": (mv_route, "cinewhoop", {"pushes in", "trucks", "follows", "arcs"}, "one continuous indoor flight, scene after scene"),
    "hole_flyover": (mv_hole_flyover, "drone", {"trucks", "pushes in", "rises"}, "a golf hole from the ball's point of view, climbing late"),
    "bee_path": (mv_bee_path, "insect", {"*"}, "a bee's flight: easing forward, braking into tight turns"),
    "mosquito_path": (mv_mosquito_path, "insect", {"*"}, "a mosquito round a person: the view rarely points where it goes"),
}


# moves whose camera motion is their own business (it rides a body or a car, or hits several marks):
# `check` does not hold them to one word
for _n in ("drift", "top_down", "snorricam", "pov", "car_hood", "car_dash", "car_passenger", "car_rear", "car_window",
           "car_wheel", "motion_control", "robo_snap", "second_participant"):
    _f, _r, _w, _why = LIBRARY[_n]
    LIBRARY[_n] = (_f, _r, {"*"}, _why)


# moves whose framing turns with the subject as they turn (riding moves); every other move holds the angle
# the subject faced at the start of the shot
LIVE_FACING = {"follow", "lead", "side_track", "track", "fpv_chase", "car_chase", "car_lead", "car_side_track", "drone_side_follow",
               "second_participant", "snorricam", "pov", "car_hood", "car_dash", "car_passenger", "car_rear",
               "car_window", "car_wheel", "fpv_dive"}

# moves built from fixed points round where the subject stands: on a subject that travels they ride along
RIDE_MOVES = {"drone_reveal", "top_down", "reveal", "pull_back_reveal", "hero_low"}


def _ride(c, subj, keys, step=0.25):
    """Carry a move's fixed points with a travelling subject: dense keys, each the move's own path at that
    moment (eased between its keys) moved by how far the subject has gone since the shot began."""
    pk = [k for k in keys if "pos" in k]
    if len(pk) < 2:
        return keys
    g0 = c.ground(subj, c.t0)
    n = max(2, int(math.ceil((c.t1 - c.t0) / step)))
    out = []
    for i in range(n + 1):
        t = c.t0 + (c.t1 - c.t0) * i / n
        j = max(0, min(len(pk) - 2, max((m for m in range(len(pk)) if pk[m]["t"] <= t + 1e-9), default=0)))
        a, b = pk[j], pk[j + 1]
        f = 0.0 if b["t"] - a["t"] < 1e-9 else max(0.0, min(1.0, (t - a["t"]) / (b["t"] - a["t"])))
        if a.get("ease") == "stop" or b.get("ease") == "stop":
            f = f * f * (3 - 2 * f)
        g = c.ground(subj, t)
        pos = [a["pos"][q] + (b["pos"][q] - a["pos"][q]) * f for q in range(3)]
        pos = [pos[0] + g[0] - g0[0], pos[1] + g[1] - g0[1], pos[2]]
        k = dict(a, t=round(t, 6), pos=[round(v, 4) for v in pos])
        k.pop("ease", None)
        for fld in ("lens", "roll"):
            if fld in a and fld in b:
                k[fld] = float(a[fld]) + (float(b[fld]) - float(a[fld])) * f
        if i in (0, n):
            k["ease"] = "linear" if _moving(c, subj, t) else (keys[0] if i == 0 else keys[-1]).get("ease", "auto")
        out.append(k)
    return out


# ── the back-off on a wide swing (v2.46) ─────────────────────────────────────────────────────────────────
# A continuous hand-over between two framings (blocking.py's join of one shot into the next) eases the camera's
# POSITION from one to the other. When the two sit far apart round the subject, the eased path cuts the chord and
# can pass through the subject. A real operator swings wide instead. Remedy, not a check: when the swing round
# the subject is over BACKOFF_SWING and the straight path enters the subject's sphere, one waypoint is added at
# the bisecting angle, pushed out by BACKOFF_K of the distance at a swing of 90° or more (less below).
BACKOFF_SWING = 30.0    # degrees round the subject before a hand-over is checked [assumed]
BACKOFF_K = 0.3         # extra distance at ≥ 90°, as a share of the camera's distance [practitioner: one shipped camera path]


def swing_deg(pa, pb, centre) -> float:
    """The horizontal angle between two camera positions, seen from the subject."""
    a = math.atan2(pa[1] - centre[1], pa[0] - centre[0])
    b = math.atan2(pb[1] - centre[1], pb[0] - centre[0])
    return abs(math.degrees((b - a + math.pi) % (2 * math.pi) - math.pi))


def seg_dist(pa, pb, c) -> float:
    """The closest the straight path pa → pb comes to the point c (3-D)."""
    ab = [pb[i] - pa[i] for i in range(3)]
    L2 = sum(v * v for v in ab)
    f = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, sum((c[i] - pa[i]) * ab[i] for i in range(3)) / L2))
    return math.dist(c, [pa[i] + ab[i] * f for i in range(3)])


def back_off(pa, pb, centre, radius: float, swing_min: float = BACKOFF_SWING, k: float = BACKOFF_K):
    """A waypoint [x, y, z] that keeps the hand-over pa → pb outside the subject's sphere, or None when the swing is
    small or the straight path already stays clear."""
    sw = swing_deg(pa, pb, centre)
    if sw <= swing_min or seg_dist(pa, pb, centre) >= radius:
        return None
    ua = _unit((pa[0] - centre[0], pa[1] - centre[1], 0.0))
    ub = _unit((pb[0] - centre[0], pb[1] - centre[1], 0.0))
    m = (ua[0] + ub[0], ua[1] + ub[1], 0.0)
    if math.hypot(m[0], m[1]) < 1e-6:                       # straight across: go round the camera's left
        m = (-ua[1], ua[0], 0.0)
    m = _unit(m)
    d0 = max(math.hypot(pa[0] - centre[0], pa[1] - centre[1]), math.hypot(pb[0] - centre[0], pb[1] - centre[1]))
    d = d0 * (1.0 + k * min(1.0, sw / 90.0))
    z = (pa[2] + pb[2]) / 2
    wp = [centre[0] + m[0] * d, centre[1] + m[1] * d, z]
    while min(seg_dist(pa, wp, centre), seg_dist(wp, pb, centre)) < radius and d < 3.0 * d0:   # both halves clear too
        d *= 1.1
        wp = [centre[0] + m[0] * d, centre[1] + m[1] * d, z]
    return [round(v, 4) for v in wp]


def expand_shot(bl, spec: dict, sh: dict, t0: float, t1: float) -> tuple[list, str]:
    """A named move → (raw camera keys inside [t0, t1], the rig). Unknown names raise."""
    name = sh.get("move", "static")
    if name not in LIBRARY:
        raise ValueError(f"unknown move {name!r} — `blocking_camera.py --moves` lists the {len(LIBRARY)} named moves")
    fn, rig, _, _ = LIBRARY[name]
    c = Ctx(bl, spec, sh, t0, t1)
    keys = fn(c, sh)
    subj = sh.get("on")
    if name not in LIVE_FACING and sh.get("facing_ref", "start") != "live":
        # framings in film terms ("on A, side 30") hold the angle the subject faced when the shot began:
        # someone turning round inside a held frame or an arc does not drag the camera round with them
        for k in keys:
            if "pos" not in k and isinstance(k.get("on"), str) and c.kind(k["on"]) == "actor" and "ref_facing" not in k:
                k["ref_facing"] = c.facing(k["on"], t0)
    if name in RIDE_MOVES and sh.get("ride", True) and isinstance(subj, str) and c.kind(subj) in ("actor", "vehicle") \
            and math.dist(c.ground(subj, t0), c.ground(subj, t1)) > 0.3:
        keys = _ride(c, subj, keys)
    rig = sh.get("rig", rig)
    for k in keys:
        k["t"] = round(min(max(k["t"], t0), t1), 6)
    return keys, rig


# ── the operator: what actually renders ────────────────────────────────────────────────────────────────
OVERSAMPLE = 8          # integration samples per frame


def build_run(bl, spec: dict, t0: float, t1: float, rig_name: str, reacts: list, ideal, t_plan: float | None = None) -> dict:
    """Run the ideal camera of one continuous run [t0, t1] through its rig(s): a spring on position, a
    spring on aim (yaw, pitch, roll), lens and focus kept as they are. Each sample uses the rig of the key
    in force, so a run that joins two shots changes physics where the shots change. Returns a table."""
    fps = float(spec.get("fps", 24))
    dt = 1.0 / (fps * OVERSAMPLE)
    n = max(2, int(math.ceil((t1 - t0) / dt)) + 1)
    ts = [min(t0 + i * dt, t1) for i in range(n)]
    ids = [ideal(t) for t in ts]
    rigs = [c.get("key", {}).get("rig") or rig_name for c in ids]
    pos = [tuple(c["pos"]) for c in ids]
    yaws, pitches = [], []
    for c in ids:
        y, p = yaw_pitch(_sub(c["look_at"], c["pos"]))
        yaws.append(y); pitches.append(p)
    yaws = unwrap(yaws)
    rolls = [float(c.get("roll_deg", 0.0)) for c in ids]
    kick_p, kick_a = {}, {}
    for r in reacts or []:
        i = int(round((r["t"] - t0) / dt))
        if 0 <= i < n:
            back, up, ay, ap = REACT.get(r.get("kind", "flinch"), REACT["flinch"])
            s_ = float(r.get("strength", 1.0))
            fwd = dir_from(yaws[i], 0.0)
            sgn = 1.0 if i % 2 else -1.0                   # deterministic: the same spec flinches the same way
            kick_p[i] = (-fwd[0] * back * s_, -fwd[1] * back * s_, up * s_)
            kick_a[i] = (ay * s_ * sgn, ap * s_, 0.0)
    ffs = [rig_of(r).get("anticipate", 0.85) for r in rigs]
    # the plan's last key: after it the run only holds until the cut, so the operator does not anticipate a stop
    valid = n if t_plan is None else sum(1 for tt in ts if tt <= t_plan + 1e-9)
    pos_f = spring_track_var(pos, dt, [rig_of(r)["pos"] for r in rigs], kicks=kick_p, ff=ffs, valid=valid)
    aim_in = [(yaws[i], pitches[i], rolls[i]) for i in range(n)]
    aim_f = spring_track_var(aim_in, dt, [rig_of(r)["aim"] for r in rigs], kicks=kick_a, ff=ffs, valid=valid)
    # banking and pitching come from the real (filtered) path's acceleration
    vel = [(0.0, 0.0, 0.0)] + [tuple((pos_f[i][j] - pos_f[i - 1][j]) / dt for j in range(3)) for i in range(1, n)]
    acc = [(0.0, 0.0, 0.0)] + [tuple((vel[i][j] - vel[i - 1][j]) / dt for j in range(3)) for i in range(1, n)]
    w_acc = max(1, int(OVERSAMPLE * 0.75))                # smooth the acceleration over ~3/4 of a frame
    acc_s = []
    for i in range(n):
        lo, hi = max(0, i - w_acc), min(n, i + w_acc + 1)
        acc_s.append(tuple(sum(acc[k][j] for k in range(lo, hi)) / (hi - lo) for j in range(3)))
    # bank and tip gains cross-fade over ±0.4 s where the rig changes (a drone's lean does not switch on in a frame)
    span = max(1, int(round(0.4 / dt)))

    def smooth_gain(vals):
        cs = [0.0]
        for v_ in vals:
            cs.append(cs[-1] + v_)
        return [(cs[min(n, i + span + 1)] - cs[max(0, i - span)]) / (min(n, i + span + 1) - max(0, i - span)) for i in range(n)]
    g_bank = smooth_gain([float(rig_of(r)["bank"]) for r in rigs])
    g_bmax = smooth_gain([float(rig_of(r).get("bank_max", 30.0)) for r in rigs])
    g_tip = smooth_gain([float(rig_of(r)["pitch"]) for r in rigs])
    out = []
    for i in range(n):
        rig = rig_of(rigs[i])
        y, p, r = aim_f[i]
        fwd = dir_from(y, 0.0)
        # the body banks with the curvature of its own path (centripetal acceleration), seen from where the
        # lens points: looking back down the path the lean reads mirrored, looking sideways it barely reads
        sp = math.hypot(vel[i][0], vel[i][1])
        if sp > 0.3:
            vx, vy = vel[i][0] / sp, vel[i][1] / sp
            fade = min(1.0, (sp - 0.3) / 0.5)
            align = fwd[0] * vx + fwd[1] * vy
            a_lat = (acc_s[i][0] * -vy + acc_s[i][1] * vx) * align * fade
            a_fwd = (acc_s[i][0] * vx + acc_s[i][1] * vy) * align * fade
        else:
            a_lat = a_fwd = 0.0
        bank = g_bank[i] * math.degrees(math.atan2(a_lat, 9.81))      # roll into the turn: up leans to its centre
        bmax = g_bmax[i]
        bank = bmax * math.tanh(bank / bmax) if bmax > 0 else 0.0
        tip = -g_tip[i] * math.degrees(math.atan2(a_fwd, 9.81)) * 0.5
        tip = 8.0 * math.tanh(tip / 8.0)                      # a nose-down lean, never a lurch
        speed = math.hypot(vel[i][0], vel[i][1])
        out.append({"t": ts[i], "pos": pos_f[i], "yaw": y, "pitch": p + tip, "roll": r + bank,
                    "dist": math.dist(ids[i]["pos"], ids[i]["look_at"]), "speed": speed, "ideal": ids[i], "rig": rigs[i]})
    return {"t0": t0, "t1": t1, "dt": dt, "samples": out, "rig": rig_name}


def sample_run(run: dict, t: float, seed: int) -> dict:
    """The camera at t from a run table: interpolated, then the rig's own life added (drift, steps,
    vibration). Deterministic: the same spec renders the same frames."""
    S = run["samples"]
    x = (t - run["t0"]) / run["dt"]
    i = max(0, min(len(S) - 2, int(math.floor(x))))
    f = max(0.0, min(1.0, x - i))
    a, b = S[i], S[i + 1]
    lerp = lambda u, v: u + (v - u) * f
    pos = [lerp(a["pos"][j], b["pos"][j]) for j in range(3)]
    yaw, pitch, roll = lerp(a["yaw"], b["yaw"]), lerp(a["pitch"], b["pitch"]), lerp(a["roll"], b["roll"])
    speed = lerp(a["speed"], b["speed"])
    base_pos = list(pos)                                 # the rig's path, before its own life is added
    # the rig's own life, cross-faded over ±0.4 s where one rig hands over to another (a handheld shake does
    # not switch off in one frame when the drone takes the camera)
    span = max(1, int(round(0.4 / run["dt"])))
    near = [S[max(0, min(len(S) - 1, i + o))].get("rig") for o in range(-span, span + 1, max(1, span // 4))]
    weights = {}
    for r_ in near:
        weights[r_] = weights.get(r_, 0) + 1
    tot = float(sum(weights.values()))
    dp, dy_, dpi, dr = [0.0, 0.0, 0.0], 0.0, 0.0, 0.0
    for r_, wn in weights.items():
        rig = rig_of(r_)
        wgt = wn / tot
        if rig["noise"]:
            amp, ang, lo, hi = rig["noise"]
            for j in range(3):
                dp[j] += wgt * amp * noise(t, seed + j, lo, hi)
            dy_ += wgt * ang * noise(t, seed + 5, lo, hi)
            dpi += wgt * ang * 0.7 * noise(t, seed + 6, lo, hi)
            dr += wgt * ang * 0.6 * noise(t, seed + 7, lo, hi)
        if rig["bob"] and speed > 0.4:
            k = min(1.0, (speed - 0.4) / 0.6)
            dp[2] += wgt * rig["bob"] * k * math.sin(2 * math.pi * 1.9 * t)
            dr += wgt * 0.4 * k * math.sin(2 * math.pi * 0.95 * t)
        if rig["vib"]:
            amp, ang, hz = rig["vib"]
            dp[2] += wgt * amp * math.sin(2 * math.pi * hz * t + 0.7) * (0.6 + 0.4 * math.sin(2 * math.pi * 1.3 * t))
            dpi += wgt * ang * math.sin(2 * math.pi * hz * 1.07 * t)
    pos = [pos[j] + dp[j] for j in range(3)]
    yaw, pitch, roll = yaw + dy_, pitch + dpi, roll + dr
    d = dir_from(yaw, pitch)
    dist = lerp(a["dist"], b["dist"])
    look = [pos[j] + d[j] * dist for j in range(3)]
    return {"pos": pos, "look_at": look, "roll_deg": roll, "speed": speed, "base_pos": base_pos,
            "rig": a.get("rig") if f < 0.5 else b.get("rig"),
            "ideal_a": a["ideal"], "ideal_b": b["ideal"], "f": f}


# ── the words ───────────────────────────────────────────────────────────────────────────────────────────
def rig_words(name):
    return rig_of(name)["words"]


def move_words(name):
    return LIBRARY.get(name, (None, None, set(), ""))[3]


def confirms(name):
    return LIBRARY.get(name, (None, None, set(), ""))[2]


# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────
def selftest() -> int:
    # the spring: a step input; critically damped never overshoots, under-damped does and settles
    step = [(0.0,)] * 10 + [(1.0,)] * 400
    crit = spring_track(step, 1 / 192, 8.0, 1.0)
    under = spring_track(step, 1 / 192, 8.0, 0.5)
    assert max(v[0] for v in crit) <= 1.0 + 1e-6 and abs(crit[-1][0] - 1) < 1e-3, crit[-1]
    assert max(v[0] for v in under) > 1.1 and abs(under[-1][0] - 1) < 1e-2, max(v[0] for v in under)
    exact = spring_track(step, 1 / 192, None, 1.0)
    assert exact == step
    # a kick displaces and decays
    flat = [(0.0,)] * 300
    k = spring_track(flat, 1 / 192, 10.0, 0.7, kicks={20: (1.0,)})
    assert max(abs(v[0]) for v in k) > 0.02 and abs(k[-1][0]) < 1e-3
    assert unwrap([170, -170, -150]) == [170, 190, 210]
    # every rig names its words and limits; every library move has a function and a known rig
    for n_, r in RIGS.items():
        assert r["words"] and r["max_mps"] > 0 and r["max_dps"] > 0, n_
    for n_, (fn, rig, words, why) in LIBRARY.items():
        assert callable(fn) and rig in RIGS and why, n_
    # the aerial move table and the library agree: every blocking name is a move, every kind's rig is a rig,
    # every alias and every DJI preset points at a row of the table
    T = aerial_table()
    for n_, row in T["moves"].items():
        assert row.get("blocking") is None or row["blocking"] in LIBRARY, (n_, row.get("blocking"))
        assert row["kind"] in T["kinds"] and (T["kinds"][row["kind"]]["rig"] is None or T["kinds"][row["kind"]]["rig"] in RIGS), n_
        assert set(row.get("for", [])) <= set(T["functions"]) and row.get("words") and row.get("source"), n_
        for key in ("speed_mps", "radius_m", "secs_per_turn", "deg_per_s", "altitude_m", "distance_m", "foreground_m",
                    "turn_radius_m", "turn_deg"):
            if key in row:
                assert len(row[key]) == 2 and row[key][0] < row[key][1], (n_, key)
    assert all(v in T["moves"] for v in T["aliases"].values()), T["aliases"]
    for n_, pr in T["dji"]["presets"].items():
        assert pr.get("move") is None or pr["move"] in T["moves"], n_
        assert all(u in T["moves"] for u in pr.get("use_for", [])), n_
        assert pr.get("move") or pr.get("use_for") or n_ == "mastershots", n_
    assert abs(lens_for_extent(540, 960, 0.95, 0.92) - 35.0) < 1.0           # MS on 9:16 at 35 mm ≈ 0.92 m
    assert noise(1.3, 5, 0.1, 0.4) == noise(1.3, 5, 0.1, 0.4)
    # the back-off: a hand-over straight across a person swings wide; a small or a clear swing is left alone
    c0 = (0.0, 0.0, 1.0)
    wp = back_off((2.0, 0.0, 1.5), (-2.0, 0.0, 1.5), c0, 0.85)
    assert wp is not None and abs(math.hypot(wp[0], wp[1]) - 2.6) < 1e-3 and wp[2] == 1.5, wp      # 180°: +30 % of 2 m
    assert seg_dist((2.0, 0.0, 1.5), wp, c0) > 0.85 and seg_dist(wp, (-2.0, 0.0, 1.5), c0) > 0.85, wp
    assert back_off((2.0, 0.0, 1.5), (2.0 * math.cos(0.35), 2.0 * math.sin(0.35), 1.5), c0, 0.85) is None   # 20°
    assert back_off((3.0, 0.0, 1.5), (0.0, 3.0, 1.5), c0, 0.85) is None       # 90° at 3 m: the chord stays 2.1 m clear
    wp2 = back_off((1.0, 0.0, 1.0), (0.0, 1.0, 1.0), c0, 0.85)                # 90° at 1 m: the chord passes 0.71 m away
    assert wp2 and abs(math.atan2(wp2[1], wp2[0]) - math.pi / 4) < 1e-6 and abs(math.hypot(wp2[0], wp2[1]) - 1.3) < 1e-3, wp2
    print(f"selftest OK — the operator spring lags, overshoots and settles as its damping says, a kick decays; "
          f"{len(RIGS)} rigs and {len(LIBRARY)} named moves are complete (the moves are exercised by "
          f"blocking.py --selftest); a wide hand-over through the subject backs off, a small or clear one does not")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--moves" in sys.argv:
        for n_, (fn, rig, words, why) in LIBRARY.items():
            print(f"  {n_:22s} {rig:16s} {why}")
        sys.exit(0)
    print(__doc__)
