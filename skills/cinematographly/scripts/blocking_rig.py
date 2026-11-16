#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""blocking_rig.py — the blocking mannequin's skeleton, solved in plain Python (references/blocking.md §3b).

blocking.py asks this module where every joint of every actor is at time t; blocking_kit.py poses a
Blender armature to those joints. The same numbers feed the checks and the render, so what `check`
measures is what the video model sees.

  python3 blocking_rig.py --selftest

THE BODY. Segment lengths are fractions of standing height from the anthropometric tables of Drillis &
Contini (1966), as reproduced in Winter, *Biomechanics and Motor Control of Human Movement*: shoulder
0.818 H, hip joint 0.53 H, knee 0.285 H, ankle 0.039 H, upper arm 0.186 H, forearm 0.146 H, hand 0.108 H,
thigh 0.245 H, shank 0.246 H, foot 0.152 H, shoulder width 0.259 H, hip width 0.191 H. `build` scales the
shoulders (slim 0.94 · average 1 · broad 1.08).

WHAT MOVES, AND HOW:
  arms    two-bone IK from the shoulder to the hand target (blocking.hand_state: rest, reach, lift,
          hold, lower), the elbow pointed back and out; arms swing against the legs while walking
  legs    two-bone IK to the ankle; the knee points forward
  feet    planted while walking: each foot lands every two steps on the actor's path, half a step ahead
          of the hips, and swings in an arc between landings (step length 0.37 H at 1.3 m/s, shorter
          for a slower walk, ∝ √speed — an assumption); they settle under the hips when the actor
          stops; seated feet sit forward of the seat
  pelvis  rises and falls 2 cm per step while walking (highest at mid-stance); drops to the seat when sitting, blended over the key
          segment so a sit-down is a movement, not a jump
  spine   leans 12° forward for `lean`, 3° while walking
  head    turns toward `look` (an actor, a prop, "camera" or a point), at most 75° of yaw and 30° of
          pitch from the body
"""
from __future__ import annotations
import math, sys

# Drillis & Contini (1966) segment fractions of standing height.
P = {"shoulder_z": 0.818, "hip_z": 0.530, "knee_z": 0.285, "ankle_z": 0.039, "chin_z": 0.870, "top_z": 1.0,
     "eye_z": 0.936, "upper_arm": 0.186, "forearm": 0.146, "hand": 0.108, "thigh": 0.245, "shank": 0.246,
     "foot": 0.152, "shoulder_w": 0.259, "hip_w": 0.191}
BUILD = {"slim": 0.94, "average": 1.0, "broad": 1.08}
STEP = 0.37          # step length as a fraction of height, at an ordinary walking pace
WALK_REF = 1.3       # m/s: the ordinary pace that STEP describes (assumption, not a measured figure)
SWING_H = 0.06       # foot clearance in a swing, metres
SWING_PART = 0.8     # the swing takes 0.8 of a step (40 % of the stride); both feet are down for the rest
HEEL_LIFT = 0.07     # metres the heel peels up by toe-off
TOE_Z = 0.025        # the toe joint's height off the floor
MAX_YAW, MAX_PITCH = 75.0, 30.0


# ── small vector helpers ─────────────────────────────────────────────────────────────────────────────────
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a, fallback=(1.0, 0.0, 0.0)):
    n = norm(a)
    return mul(a, 1.0 / n) if n > 1e-9 else fallback
def lerp3(a, b, f): return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)
def smooth(f):
    f = min(1.0, max(0.0, f))
    return f * f * (3 - 2 * f)


def frame_of(pos2, facing_deg):
    """World origin, forward and left vectors of an actor standing at pos2 facing facing_deg."""
    fr = math.radians(facing_deg)
    return (pos2[0], pos2[1], 0.0), (math.cos(fr), math.sin(fr), 0.0), (-math.sin(fr), math.cos(fr), 0.0)


def to_world(origin, fwd, left, local):
    x, y, z = local
    return (origin[0] + fwd[0] * x + left[0] * y, origin[1] + fwd[1] * x + left[1] * y, origin[2] + z)


def two_bone_ik(root, target, a, b, pole, soft=0.0):
    """Elbow/knee position for a two-segment chain from root toward target, bending toward pole.
    Returns (joint, end) where end is the target pulled in to reach when it is too far. `soft` (0..1) eases
    the last part of the reach: a chain that straightens fully snaps the joint in the frames around it,
    so beyond (1 - soft) of full length the end approaches full extension asymptotically."""
    d_vec = sub(target, root)
    d = norm(d_vec)
    u = unit(d_vec, (0.0, 0.0, -1.0))
    reach = a + b - 1e-4
    if soft > 0:
        ds = reach * (1.0 - soft)
        if d > ds:
            d = ds + (reach - ds) * (1.0 - math.exp(-(d - ds) / (reach - ds)))
            target = add(root, mul(u, d))
    if d > reach:
        target, d = add(root, mul(u, reach)), reach
    d = max(d, abs(a - b) + 1e-4)
    pv = sub(pole, root)
    v = sub(pv, mul(u, dot(pv, u)))
    v = unit(v, unit(cross(u, (0.0, 1.0, 0.0)), (1.0, 0.0, 0.0)))
    cos_a = (a * a + d * d - b * b) / (2 * a * d)
    cos_a = min(1.0, max(-1.0, cos_a))
    sin_a = math.sqrt(1 - cos_a * cos_a)
    joint = add(root, add(mul(u, a * cos_a), mul(v, a * sin_a)))
    return joint, target


# ── the solver ───────────────────────────────────────────────────────────────────────────────────────────
class Rig:
    """Joint positions for one actor. `bl` is the blocking module (for actor_at, hand_state, …)."""

    def __init__(self, bl, spec: dict, actor: dict):
        self.bl, self.spec, self.a = bl, spec, actor
        self.H = float(actor.get("height", 1.70))
        self.k_sh = BUILD.get(actor.get("build", "average"), 1.0)
        ks = sorted(actor["keys"], key=lambda k: float(k["t"]))
        self.keys = ks
        # cumulative path length at each key, for the step phase
        self.cum = [0.0]
        v_top = 0.0
        for ka, kb in zip(ks, ks[1:]):
            L = math.dist(ka["pos"], kb["pos"])
            self.cum.append(self.cum[-1] + L)
            if float(kb["t"]) > float(ka["t"]):
                v_top = max(v_top, L / (float(kb["t"]) - float(ka["t"])))
        # a slower walk takes shorter steps as well as fewer of them (step ∝ √speed: an assumption, tagged)
        self.step = STEP * self.H * min(1.1, max(0.6, math.sqrt(v_top / WALK_REF))) if v_top > 0 else STEP * self.H

    # -- path (the same walk blocking.actor_at places the pelvis on) ---------------------------------------
    def dist_at(self, t: float) -> float:
        return self.bl.path_dist(self.keys, t, ramp=self.a.get("ramp"))

    def point_at_dist(self, s: float) -> tuple:
        return self.bl.point_on_path(self.keys, s)

    def speed_at(self, t: float, win: float = 0.25) -> float:
        """Walking speed, averaged over ±win s so starts and stops blend instead of popping."""
        n, tot = 8, 0.0
        for i in range(n):
            t0 = t - win + 2 * win * i / n
            t1 = t0 + 2 * win / n
            tot += abs(self.dist_at(t1) - self.dist_at(t0))
        return tot / (2 * win)

    # -- pose blend ---------------------------------------------------------------------------------------
    def pose_blend(self, t: float):
        """(pose_a, pose_b, w): the pose changes smoothly across a key segment whose ends differ."""
        default = self.a.get("pose", "stand")
        ks = self.keys
        if t <= float(ks[0]["t"]):
            p = ks[0].get("pose", default)
            return p, p, 0.0
        for ka, kb in zip(ks, ks[1:]):
            ta, tb = float(ka["t"]), float(kb["t"])
            if ta <= t <= tb:
                pa, pb = ka.get("pose", default), kb.get("pose", default)
                if pa == pb or tb <= ta:
                    return pa, pa, 0.0
                # the sit-down (or stand-up) takes the last 1.0 s of the segment, or all of it if shorter
                d = min(1.0, tb - ta)
                return pa, pb, smooth((t - (tb - d)) / d)
        p = ks[-1].get("pose", default)
        return p, p, 0.0

    # -- feet -----------------------------------------------------------------------------------------------
    def _stance(self, pose, seat_x=0.0):
        H = self.H
        if pose == "sit":
            return {"L": (0.42 * H / 1.7 + seat_x, 0.11, P["ankle_z"] * H),
                    "R": (0.42 * H / 1.7 + seat_x, -0.11, P["ankle_z"] * H)}
        return {"L": (0.02, 0.095 * H / 1.7, P["ankle_z"] * H), "R": (0.02, -0.095 * H / 1.7, P["ankle_z"] * H)}

    def _gait(self, t: float):
        """(D0, D1, S) for the walk holding t: where it starts and ends along the path, and a step length
        near the actor's own that fits the walk so its last step lands as it stops; None when standing."""
        run = self.bl.path_run(self.keys, t)
        if run is None:
            return None
        cum = self.bl.path_cum(self.keys)
        D0, D1 = cum[run[0]], cum[run[1]]
        Dr = D1 - D0
        m = max(0, round(Dr / self.step - SWING_PART))
        return D0, D1, Dr / (m + SWING_PART)

    def _landing(self, j: int, side: str, gait):
        # landing j is planted 0.3 of a step ahead of where the pelvis is at phase j; the swing ends at 0.8 of
        # the step, so at heel strike the leading ankle is half a step ahead of the hips and at toe-off the
        # trailing one is 0.7 of a step behind (stance 60 % of the stride, swing 40 %, double support 20 %).
        # The first foot down is where the actor stood; the last ones are where they stop.
        D0, D1, S = gait
        dd = D0 + (min(j * S + 0.3 * S, D1 - D0) if j > 0 else 0.0)
        pt, d = self.point_at_dist(dd)
        if d is None:
            d = (1.0, 0.0, 0.0)
        left = (-d[1], d[0], 0.0)
        off = (0.095 if side == "L" else -0.095) * self.H / 1.7
        return (pt[0] + left[0] * off, pt[1] + left[1] * off, P["ankle_z"] * self.H), d

    def _foot(self, ankle_flat, d, behind, arc, S):
        """(ankle, toe) for a foot whose flat-footed ankle would be at ankle_flat pointing d: the heel peels
        up about the toe as the foot trails behind the hips (terminal stance), then the swing arc."""
        H = self.H
        toe_h, toe_z, ank_z = 0.75 * P["foot"] * H, TOE_Z, P["ankle_z"] * H
        T = (ankle_flat[0] + d[0] * toe_h, ankle_flat[1] + d[1] * toe_h, toe_z)
        lift = HEEL_LIFT * smooth((behind - 0.25 * S) / (0.45 * S)) + 0.08 * smooth((behind - 0.7 * S) / (0.3 * S))
        Lf = math.hypot(toe_h, ank_z - toe_z)
        dz = min(ank_z - toe_z + lift, Lf * 0.98)
        horiz = math.sqrt(Lf * Lf - dz * dz)
        ankle = (T[0] - d[0] * horiz, T[1] - d[1] * horiz, toe_z + dz + arc)
        return ankle, (T[0], T[1], T[2] + arc)

    def feet(self, t: float, origin, fwd, left, pose_w):
        """World ankle and toe for both feet, and the walk phase."""
        pa, pb, w = pose_w
        st_a, st_b = self._stance(pa), self._stance(pb)
        stance = {s: lerp3(st_a[s], st_b[s], w) for s in "LR"}
        speed = self.speed_at(t)
        gait = self._gait(t)
        w_walk = smooth(speed / 0.15) if "sit" not in (pa, pb) and gait else 0.0
        out = {}
        if gait:
            S = gait[2]
            n = (self.dist_at(t) - gait[0]) / S
        else:
            S, n = self.step, 0.0
        k = math.floor(n)
        frac = n - k
        toe_h = 0.75 * P["foot"] * self.H
        for side in "LR":
            st = to_world(origin, fwd, left, stance[side])
            st_toe = (st[0] + fwd[0] * toe_h, st[1] + fwd[1] * toe_h, TOE_Z)
            if w_walk <= 1e-3:
                out[side] = (st, st_toe)
                continue
            parity = 0 if side == "L" else 1
            if (k + 1) % 2 == parity:                 # this foot swings during step k, landing at 0.8 of it
                a_, da = self._landing(k - 1, side, gait)
                b_, db = self._landing(k + 1, side, gait)
                fs = min(1.0, frac / SWING_PART)
                g = smooth(fs)
                p = lerp3(a_, b_, g)
                d = unit(lerp3(da, db, g))
                arc = SWING_H * math.sin(math.pi * fs)
            else:
                p, d = self._landing(k, side, gait)
                arc = 0.0
            behind = (origin[0] - p[0]) * d[0] + (origin[1] - p[1]) * d[1]
            ankle, toe = self._foot(p, d, behind, arc, S)
            out[side] = (lerp3(st, ankle, w_walk), lerp3(st_toe, toe, w_walk))
        return out, speed, n

    # -- the whole skeleton -----------------------------------------------------------------------------------
    def joints(self, t: float) -> dict:
        bl, spec, a, H = self.bl, self.spec, self.a, self.H
        st = bl.actor_at(spec, a, t)
        origin, fwd, left = frame_of(st["pos"], st["facing"])
        up = (0.0, 0.0, 1.0)
        pose_w = self.pose_blend(t)
        pa, pb, w = pose_w
        seat = st.get("seat")
        seat_h = seat if seat is not None else float(a.get("seat_height", 0.45))
        feet, speed, n = self.feet(t, origin, fwd, left, pose_w)
        walk = smooth(speed / 0.5) * (0.0 if "sit" in (pa, pb) else 1.0)

        def pelvis_for(pose):
            if pose == "sit":
                return (-0.04, 0.0, seat_h + 0.09)
            z = P["hip_z"] * H * (0.97 if pose == "lean" else 1.0)
            return (0.0, 0.0, z)
        pel_l = lerp3(pelvis_for(pa), pelvis_for(pb), w)
        # the hips drop as far as the legs need to reach the feet: the walk's rise and fall (highest over a
        # planted foot, lowest in double support) comes from the legs, not from a sine
        th_, sh_ = P["thigh"] * H, P["shank"] * H
        hip_half_ = P["hip_w"] * H / 2 * 0.6
        pw = to_world(origin, fwd, left, pel_l)
        zs = [pel_l[2]]
        for side_, sign_ in (("L", 1.0), ("R", -1.0)):
            hx, hy = pw[0] + left[0] * sign_ * hip_half_, pw[1] + left[1] * sign_ * hip_half_
            ank = feet[side_][0]
            hz = math.hypot(hx - ank[0], hy - ank[1])
            r = 0.985 * (th_ + sh_)
            zs.append(ank[2] + math.sqrt(max(r * r - hz * hz, 0.0)))
        kk = 0.01
        zmin = min(zs)
        z_reach = zmin - kk * math.log(sum(math.exp(-(z - zmin) / kk) for z in zs))
        # a person does not sink more than a few centimetres to make a step; past that the trailing heel rises
        # and the leg straightens (soft IK) instead
        pel_l = (pel_l[0], pel_l[1], max(z_reach, zs[0] - 0.025 * H))
        lean = {"lean": 12.0, "stand": 0.0, "sit": 0.0}
        lean_deg = lean.get(pa, 0.0) * (1 - w) + lean.get(pb, 0.0) * w + 3.0 * walk
        pelvis = to_world(origin, fwd, left, pel_l)
        spine_len = (P["shoulder_z"] - P["hip_z"]) * H
        lr = math.radians(lean_deg)
        neck_base = add(pelvis, add(mul(fwd, spine_len * math.sin(lr)), mul(up, spine_len * math.cos(lr))))
        spine_up = unit(sub(neck_base, pelvis))
        sh_half = P["shoulder_w"] * H * self.k_sh / 2 * 0.86                  # joint centres sit inside the acromion
        shoulders = {"L": add(add(neck_base, mul(left, sh_half)), mul(spine_up, -0.03 * H / 1.7)),
                     "R": add(add(neck_base, mul(left, -sh_half)), mul(spine_up, -0.03 * H / 1.7))}
        head_base = add(neck_base, mul(spine_up, (P["chin_z"] - P["shoulder_z"]) * H * 0.9))
        head_len = (P["top_z"] - P["chin_z"]) * H
        # the head turns toward `look`, within the neck's range
        look_dir = self._look_dir(t, head_base, fwd, st)
        head_fwd = look_dir
        head_top = add(head_base, mul(up, head_len))
        eye = add(head_base, add(mul(up, (P["eye_z"] - P["chin_z"]) * H), mul(head_fwd, 0.07 * H / 1.7)))
        # arms
        out = {"pelvis": pelvis, "neck_base": neck_base, "head_base": head_base, "head_top": head_top,
               "eye": eye, "head_fwd": head_fwd, "fwd": fwd, "left": left, "up": up, "spine_up": spine_up}
        ua, fa, hd = P["upper_arm"] * H, P["forearm"] * H, P["hand"] * H
        holding = {}
        for side, hand in (("L", "left"), ("R", "right")):
            loc, prop = bl.hand_state(spec, a, hand, t)
            holding[side] = prop
            # a held prop is gripped, not covered: the hand goes beside it (palm facing in), or behind it
            # as the camera sees it when its label faces the camera, so the label stays readable
            w_hold, pid, _ = bl.hold_state(spec, a["id"], hand, t) if hasattr(bl, "hold_state") else (0.0, None, None)
            if pid and w_hold > 0:
                kind_, pobj = bl._by_id(spec, pid)
                half = (bl.dims(pobj)[0] / 2 if pobj else 0.04) + 0.012 * H
                sgn = 1.0 if side == "L" else -1.0
                off = (0.0, sgn)
                cam = bl.camera_at(spec, t) if pobj and pobj.get("label_toward") == "camera" else None
                if cam:
                    pw = to_world(origin, fwd, left, loc)
                    dx, dy = pw[0] - cam["pos"][0], pw[1] - cam["pos"][1]
                    n_ = math.hypot(dx, dy) or 1.0
                    away = (dx / n_, dy / n_)                         # from the lens through the prop
                    off = (away[0] * fwd[0] + away[1] * fwd[1], away[0] * left[0] + away[1] * left[1])
                loc = (loc[0] + off[0] * half * w_hold, loc[1] + off[1] * half * w_hold, loc[2])
            if prop is None and walk > 0:                                   # arms swing against the legs
                swing = 0.11 * walk * math.sin(math.pi * n + (0.0 if side == "L" else math.pi))
                loc = (loc[0] + swing, loc[1], loc[2])
            target = to_world(origin, fwd, left, loc)
            s = shoulders[side]
            side_sign = 1.0 if side == "L" else -1.0
            pole = add(s, add(add(mul(fwd, -0.35), mul(left, side_sign * 0.25)), mul(up, -0.25)))
            # the IK reaches the palm (what holds a prop, 0.35 of the hand past the wrist); the wrist sits a
            # forearm's length from the elbow on the same line
            elbow, palm = two_bone_ik(s, target, ua, fa + 0.35 * hd, pole, soft=0.04)
            hand_dir = unit(sub(palm, elbow))
            wrist = add(elbow, mul(hand_dir, fa))
            out[f"shoulder_{side}"], out[f"elbow_{side}"], out[f"wrist_{side}"] = s, elbow, wrist
            out[f"palm_{side}"] = palm
            out[f"hand_tip_{side}"] = add(wrist, mul(hand_dir, hd))
        # legs
        th, sh = P["thigh"] * H, P["shank"] * H
        hip_half = P["hip_w"] * H / 2 * 0.6
        for side in "LR":
            side_sign = 1.0 if side == "L" else -1.0
            hip = add(pelvis, mul(left, side_sign * hip_half))
            ankle, toe0 = feet[side]
            pole = add(hip, add(mul(fwd, 1.0), mul(left, side_sign * 0.15)))
            knee, ankle2 = two_bone_ik(hip, ankle, th, sh, pole, soft=0.04)
            fl = P["foot"] * H
            toe = add(toe0, sub(ankle2, ankle))           # a leg pulled short lifts the whole foot with it
            fdir = unit((toe[0] - ankle2[0], toe[1] - ankle2[1], 0.0), fwd)
            heel = add(ankle2, add(mul(fdir, -0.25 * fl), (0.0, 0.0, -0.035 * H / 1.7)))
            out[f"hip_{side}"], out[f"knee_{side}"], out[f"ankle_{side}"] = hip, knee, ankle2
            out[f"toe_{side}"], out[f"heel_{side}"], out[f"foot_dir_{side}"] = toe, heel, fdir
        out["walk"], out["speed"], out["holding"] = walk, speed, holding
        return out

    def canonical(self) -> dict:
        """The same skeleton in an A-pose at the origin facing +X (arms 22° out, elbows a little bent, feet
        a little apart): the rest pose a body is modelled and skinned in. Segment lengths are the ones
        joints() uses, so posing never stretches a bone."""
        H, k = self.H, self.k_sh
        fwd, left, up = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
        pelvis = (0.0, 0.0, P["hip_z"] * H)
        spine_len = (P["shoulder_z"] - P["hip_z"]) * H
        neck_base = add(pelvis, mul(up, spine_len))
        sh_half = P["shoulder_w"] * H * k / 2 * 0.86
        head_base = add(neck_base, mul(up, (P["chin_z"] - P["shoulder_z"]) * H * 0.9))
        head_top = add(head_base, mul(up, (P["top_z"] - P["chin_z"]) * H))
        out = {"pelvis": pelvis, "neck_base": neck_base, "head_base": head_base, "head_top": head_top,
               "eye": add(head_base, add(mul(up, (P["eye_z"] - P["chin_z"]) * H), mul(fwd, 0.07 * H / 1.7))),
               "head_fwd": fwd, "fwd": fwd, "left": left, "up": up, "spine_up": up}
        ua, fa, hd = P["upper_arm"] * H, P["forearm"] * H, P["hand"] * H
        th, sh = P["thigh"] * H, P["shank"] * H
        hip_half = P["hip_w"] * H / 2 * 0.6
        toe_h = 0.75 * P["foot"] * H
        for side, sg in (("L", 1.0), ("R", -1.0)):
            s = add(add(neck_base, mul(left, sg * sh_half)), mul(up, -0.03 * H / 1.7))
            d = unit((math.sin(math.radians(5)), sg * math.sin(math.radians(22)), -math.cos(math.radians(22))))
            e = add(s, mul(d, ua))
            d2 = unit(add(d, mul(fwd, 0.21)))                      # the elbow bent ~12° forward
            w = add(e, mul(d2, fa))
            out.update({f"shoulder_{side}": s, f"elbow_{side}": e, f"wrist_{side}": w,
                        f"palm_{side}": add(e, mul(d2, fa + 0.35 * hd)), f"hand_tip_{side}": add(w, mul(d2, hd))})
            hip = add(pelvis, mul(left, sg * hip_half))
            dl = unit((0.01, sg * 0.045, -1.0))
            knee = add(hip, mul(dl, th))
            ankle = add(knee, mul(dl, sh))
            toe = (ankle[0] + toe_h, ankle[1], ankle[2] - (P["ankle_z"] * H - TOE_Z))
            out.update({f"hip_{side}": hip, f"knee_{side}": knee, f"ankle_{side}": ankle, f"toe_{side}": toe,
                        f"heel_{side}": (ankle[0] - 0.25 * P["foot"] * H, ankle[1], 0.0), f"foot_dir_{side}": fwd})
        return out

    def _look_dir(self, t, head_base, fwd, st):
        tgt = None
        ka = self.bl._keys_around(self.keys, t)[0]
        look = ka.get("look", self.a.get("look"))
        if look == "camera":
            cam = self.bl.camera_at(self.spec, t)
            tgt = tuple(cam["pos"]) if cam else None
        elif isinstance(look, list):
            tgt = tuple(float(v) for v in (look + [head_base[2]])[:3])
        elif isinstance(look, str):
            tgt = self.bl.point_of(self.spec, look, t)
        if tgt is None:
            return fwd
        d = sub(tgt, head_base)
        yaw_body = math.atan2(fwd[1], fwd[0])
        yaw = math.atan2(d[1], d[0])
        dy = (math.degrees(yaw - yaw_body) + 180) % 360 - 180
        dy = max(-MAX_YAW, min(MAX_YAW, dy))
        pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
        pitch = max(-MAX_PITCH, min(MAX_PITCH, pitch))
        y = yaw_body + math.radians(dy)
        p = math.radians(pitch)
        return (math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────────
def selftest() -> int:
    a, b = 0.30, 0.30
    j, e = two_bone_ik((0, 0, 1), (0, 0, 0.5), a, b, (1, 0, 0.75))
    assert abs(math.dist(j, (0, 0, 1)) - a) < 1e-6 and abs(math.dist(j, e) - b) < 1e-6 and j[0] > 0, j
    j, e = two_bone_ik((0, 0, 1), (0, 0, -5), a, b, (1, 0, 0.5))           # out of reach: straight
    assert abs(math.dist((0, 0, 1), e) - (a + b)) < 1e-3, e
    # soft IK: the joint moves smoothly as the target passes full reach (no snap in the last centimetres)
    prev, worst = None, 0.0
    for i in range(201):
        z = 1.0 - (0.50 + 0.12 * i / 200)
        jj, _ = two_bone_ik((0, 0, 1), (0, 0, z), a, b, (1, 0, 0.75), soft=0.04)
        if prev:
            worst = max(worst, math.dist(jj, prev))
        prev = jj
    assert worst < 0.004, worst
    class _BL:                                   # a stand-in for blocking.py: one actor standing still
        @staticmethod
        def actor_at(spec, a, t, resolve=True):
            return {"pos": (0.0, 0.0), "facing": 0.0, "pose": "stand", "seat": None}
    rig = Rig.__new__(Rig)
    rig.H, rig.k_sh = 1.7, 1.0
    c = rig.canonical()
    for j0, j1, L in (("shoulder_L", "elbow_L", P["upper_arm"]), ("elbow_L", "wrist_L", P["forearm"]),
                      ("hip_R", "knee_R", P["thigh"]), ("knee_R", "ankle_R", P["shank"])):
        assert abs(math.dist(c[j0], c[j1]) - L * 1.7) < 1e-9, (j0, j1)
    assert abs(c["ankle_L"][2] - P["ankle_z"] * 1.7) < 0.01, c["ankle_L"]
    print("selftest OK — two-bone IK keeps segment lengths, bends toward the pole, straightens out of reach, eases into full reach; the A-pose rest has the posed lengths "
          "(the full rig is exercised by blocking.py --selftest)")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
