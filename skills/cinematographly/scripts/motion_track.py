#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""motion_track.py — read a finished video frame by frame: what the camera does, and every element
that moves on its own, with the timing and the easing of each move.

⛔ WHY THIS EXISTS. `film_breakdown.py` measures a film per SHOT: cut times, one camera move per
shot, a shot size. Motion design, product launch films and UI animation live BELOW the shot: a card
slides in, a logo pops with an overshoot, a list staggers in 80 ms apart while the virtual camera
pushes in. That is the part a reference is wanted for, and a per-shot table cannot see it. This tool
measures it per FRAME and per ELEMENT, so a reference becomes numbers a designer can rebuild:
"slides in from the right 34 %W over 0.80 s, ease-out (≈ cubic-bezier(.33,1,.68,1)), 90 ms after
the title".

What it measures, per shot:
  * CAMERA — the frame's global motion between every pair of frames (Lucas-Kanade with a
    forward-backward check, RANSAC similarity, an inlier COUNT and an inlier SPREAD gate), summed
    into a path: pan, tilt, push/zoom, roll, with its own timing and easing. A flat background has
    nothing to measure: the tool says so and treats the camera as still, rather than invent a move.
  * ELEMENTS — whatever changes after the camera is taken out (camera-compensated frame
    difference), grown into a whole element at a settled frame (GrabCut), then tracked through
    every frame with ECC (affine): position, scale, rotation, squash/stretch, and a contrast-based
    opacity proxy. An element that holds still on screen while the camera moves is reported as
    SCREEN-LOCKED (a title, a HUD, a lower third).
  * ANIMATIONS — each property's moves split into segments; each segment fitted against the 26
    Penner easings (free start and end), a damped spring, and a CSS cubic-bezier; overshoot and
    settle time; peak speed; how the element arrives and leaves (enters from an edge, pops in,
    fades in, cuts in) — and the STAGGER between the elements' starts.

Outputs (local only; nothing here belongs in git — reference frames are third-party material):
  * TRACK-<label>.md        the readable report, shot by shot
  * TRACK-<label>.json      everything, including every element's per-frame track
  * TRACK-<label>-frames.csv one row per element per frame, for a spreadsheet
  * OVERLAY-<label>-NN.png  (default on) six frames of shot NN with every tracked element boxed
  * CURVES-<label>-NN.png   (default on) each animation's measured progress with its fitted curve

⛔ WHAT IT CANNOT DO — read the overlay sheets before quoting a number.
  * It sees 2D image motion. A 3D camera move with parallax (dolly, orbit, truck past depth) does not
    fit one global transform; the residual floods and the shot is flagged `parallax`, its elements
    unreliable. Camera ANGLE (high / low / dutch as composed) is not measured: read it off the sheet.
  * Elements that touch while they move can be merged into one; one element can split into two.
    Per-letter text animation is read as words or lines at best. Low-contrast UI (a 20-level grey
    on grey) can fall under the noise floor. Motion blur and heavy compression add noise to easing.
  * Opacity is a PROXY (contrast against the element at its reference frame), exact only on a flat
    background. The easing fit names the closest standard curve; a custom curve is reported as the
    nearest one plus its fitted bezier, and close alternatives are listed with their error.
  * Thresholds marked [ASSUMED] are set by eye on synthetic and real clips, not calibrated.

Usage
-----
  python3 motion_track.py VIDEO.mp4 --label ref-01 --out ~/Movies/refs/track
  python3 motion_track.py VIDEO.mp4 --width 640 --fps 30 --threshold 12
  python3 motion_track.py VIDEO.mp4 --items items.json      # also track boxes you name yourself
  python3 motion_track.py --selftest

`--items` takes [{"name": "logo", "t": 3.2, "box": [x, y, w, h]}] with the box in fractions of the
frame at time t (read off a sheet). Requires ffmpeg/ffprobe, numpy, OpenCV; scipy for the bezier
and spring fits (without it those two columns read "—"); matplotlib for the curve sheets.
Exit codes: 0 ok · 2 usage/IO error · 3 a dependency missing.
"""
from __future__ import annotations
import argparse, csv, json, math, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import film_breakdown as fb          # noqa: E402  cut detection is shared with the shot table

# ---- thresholds ---------------------------------------------------------------------------------
DIFF_FLOOR = 12          # [ASSUMED] grey levels; a residual below this is codec noise
MIN_AREA = 0.0012        # [ASSUMED] fraction of the frame; smaller changes are not elements
GLOBAL_AREA = 0.40       # [ASSUMED] residual covering more of the frame = transition / light / parallax
CAM_MIN_FEATURES = 60    # [ASSUMED] fewer tracked corners than this = no background to measure
CAM_MIN_INLIERS = 40     # camera gate: inliers that agree
CAM_MIN_CELLS = 6        # camera gate: of a 4×4 grid, cells the inliers must cover
ECC_MIN_RHO = 0.60       # [ASSUMED] below this correlation the element is lost
MIN_CONTRAST = 0.22      # [ASSUMED] contrast ratio below which an element has faded out
MIN_CHANGE = {"position": 0.008, "scale": 0.03, "rotation": 2.0, "opacity": 0.18}  # [ASSUMED]
FLOOR_SPEED = {"position": 0.01, "scale": 0.02, "rotation": 0.6, "opacity": 0.08}  # per second
SPEED_REL = 0.04         # a segment is where speed > 4 % of the property's peak speed
PULSE_MIN = {"position": 0.015, "scale": 0.06, "rotation": 5.0, "opacity": 0.3}  # [ASSUMED] go-and-return
EDGE = 0.02              # an element within 2 % of the frame edge is AT the edge


def deps():
    try:
        import numpy as np, cv2
    except Exception:
        return None, None, None
    try:
        from scipy import optimize
    except Exception:
        optimize = None
    return np, cv2, optimize


# ---- easing library -----------------------------------------------------------------------------
def ease_library(np):
    """The 26 Penner easings (as on easings.net) + linear, as vectorised functions of τ ∈ [0, 1]."""
    pi = math.pi
    c1 = 1.70158; c2 = c1 * 1.525; c4 = 2 * pi / 3

    def bounce_out(x):
        n1, d1 = 7.5625, 2.75
        y = np.empty_like(x)
        m1 = x < 1 / d1
        m2 = (x >= 1 / d1) & (x < 2 / d1)
        m3 = (x >= 2 / d1) & (x < 2.5 / d1)
        m4 = x >= 2.5 / d1
        y[m1] = n1 * x[m1] ** 2
        a = x[m2] - 1.5 / d1; y[m2] = n1 * a * a + 0.75
        a = x[m3] - 2.25 / d1; y[m3] = n1 * a * a + 0.9375
        a = x[m4] - 2.625 / d1; y[m4] = n1 * a * a + 0.984375
        return y

    ins = {
        "sine": lambda x: 1 - np.cos(x * pi / 2),
        "quad": lambda x: x ** 2, "cubic": lambda x: x ** 3,
        "quart": lambda x: x ** 4, "quint": lambda x: x ** 5,
        "expo": lambda x: np.where(x <= 0, 0.0, 2.0 ** (10 * x - 10)),
        "circ": lambda x: 1 - np.sqrt(np.clip(1 - x * x, 0, 1)),
        "back": lambda x: (c1 + 1) * x ** 3 - c1 * x ** 2,
    }
    lib = {"linear": lambda x: x}
    for k, f in ins.items():
        lib[f"in_{k}"] = f
        lib[f"out_{k}"] = (lambda f: (lambda x: 1 - f(1 - x)))(f)
        g = f if k != "back" else (lambda x: (c2 + 1) * x ** 3 - c2 * x ** 2)
        lib[f"inout_{k}"] = (lambda g: (lambda x: np.where(x < 0.5, g(2 * x) / 2,
                                                           1 - g(2 - 2 * x) / 2)))(g)
    lib["out_elastic"] = lambda x: np.where(x <= 0, 0.0, np.where(
        x >= 1, 1.0, 2.0 ** (-10 * x) * np.sin((10 * x - 0.75) * c4) + 1))
    lib["out_bounce"] = bounce_out
    return lib


# cubic-bezier equivalents (easings.net) — the fit starts from these
BEZIER_OF = {
    "linear": (0.25, 0.25, 0.75, 0.75),
    "in_sine": (0.12, 0, 0.39, 0), "out_sine": (0.61, 1, 0.88, 1), "inout_sine": (0.37, 0, 0.63, 1),
    "in_quad": (0.11, 0, 0.5, 0), "out_quad": (0.5, 1, 0.89, 1), "inout_quad": (0.45, 0, 0.55, 1),
    "in_cubic": (0.32, 0, 0.67, 0), "out_cubic": (0.33, 1, 0.68, 1), "inout_cubic": (0.65, 0, 0.35, 1),
    "in_quart": (0.5, 0, 0.75, 0), "out_quart": (0.25, 1, 0.5, 1), "inout_quart": (0.76, 0, 0.24, 1),
    "in_quint": (0.64, 0, 0.78, 0), "out_quint": (0.22, 1, 0.36, 1), "inout_quint": (0.83, 0, 0.17, 1),
    "in_expo": (0.7, 0, 0.84, 0), "out_expo": (0.16, 1, 0.3, 1), "inout_expo": (0.87, 0, 0.13, 1),
    "in_circ": (0.55, 0, 1, 0.45), "out_circ": (0, 0.55, 0.45, 1), "inout_circ": (0.85, 0, 0.15, 1),
    "in_back": (0.36, 0, 0.66, -0.56), "out_back": (0.34, 1.56, 0.64, 1),
    "inout_back": (0.68, -0.6, 0.32, 1.6),
}


def shape_of(name: str) -> str:
    """The family a designer means, which matters more than which polynomial."""
    if name == "linear":
        return "linear"
    if name == "out_back":
        return "overshoot"
    if name == "in_back":
        return "anticipation"
    if name == "inout_back":
        return "anticipation+overshoot"
    if name == "out_elastic":
        return "elastic"
    if name == "out_bounce":
        return "bounce"
    if name.startswith("spring"):
        return "spring"
    return {"in": "ease-in", "out": "ease-out", "inout": "ease-in-out"}[name.split("_")[0]]


def _penalty(name: str) -> float:
    return {"linear": 0.0}.get(name, 0.04 if ("elastic" in name or "bounce" in name) else
                               (0.02 if "back" in name else 0.01))


def bezier_y(np, x, x1, y1, x2, y2):
    """CSS cubic-bezier: y for x, by bisection on the (monotone) x(s)."""
    lo = np.zeros_like(x); hi = np.ones_like(x)
    for _ in range(24):
        s = (lo + hi) / 2
        xs = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s * s * x2 + s ** 3
        big = xs > x
        hi = np.where(big, s, hi); lo = np.where(big, lo, s)
    s = (lo + hi) / 2
    return 3 * (1 - s) ** 2 * s * y1 + 3 * (1 - s) * s * s * y2 + s ** 3


def spring_curve(np, t, w, z):
    """Unit step response of a damped spring (mass 1): ω natural frequency, ζ damping ratio."""
    t = np.maximum(t, 0.0)
    if z < 0.999:
        wd = w * math.sqrt(1 - z * z)
        return 1 - np.exp(-z * w * t) * (np.cos(wd * t) + z / math.sqrt(1 - z * z) * np.sin(wd * t))
    return 1 - np.exp(-w * t) * (1 + w * t)


def fit_easing(np, optimize, t, y, ta: float, tb: float) -> dict:
    """Fit progress y(t) (0 → 1) against every standard curve with a free start t0 and end t1.

    ⛔ The start and end are FREE on purpose: the speed threshold that found the segment cuts an
    ease-out's long tail and an ease-in's slow start, and a curve forced onto those bounds is
    misnamed (a quint-out read on its visible part looks like a quad)."""
    lib = ease_library(np)
    D = max(tb - ta, 1e-3)
    t0s = np.linspace(ta - 1.2 * D, ta + 0.1 * D, 40)
    t1s = np.linspace(tb - 0.1 * D, tb + 1.2 * D, 40)
    T0, T1 = np.meshgrid(t0s, t1s, indexing="ij")
    ok = (T1 - T0) > 0.45 * D
    span = np.where(ok, T1 - T0, 1.0)
    tau = np.clip((t[None, None, :] - T0[..., None]) / span[..., None], 0.0, 1.0)
    res = []
    for name, f in lib.items():
        pred = f(tau)
        err = np.sqrt(np.mean((pred - y[None, None, :]) ** 2, axis=-1))
        err = np.where(ok, err, np.inf)
        i, j = np.unravel_index(int(np.argmin(err)), err.shape)
        res.append([float(err[i, j]), name, float(T0[i, j]), float(T1[i, j])])
    if optimize is not None:                       # refine the five best continuously
        res.sort(key=lambda r: r[0])
        for r in res[:5]:
            f = lib[r[1]]

            def resid(p, f=f):
                d = max(p[1] - p[0], 1e-3)
                return f(np.clip((t - p[0]) / d, 0, 1)) - y
            try:
                sol = optimize.least_squares(resid, [r[2], r[3]], method="lm")
                e = float(np.sqrt(np.mean(sol.fun ** 2)))
                if e < r[0] and sol.x[1] > sol.x[0]:
                    r[0], r[2], r[3] = e, float(sol.x[0]), float(sol.x[1])
            except Exception:
                pass
    res.sort(key=lambda r: r[0] * (1 + _penalty(r[1])) + 1e-4 * _penalty(r[1]))
    best = res[0]
    out = {"curve": best[1], "shape": shape_of(best[1]), "rmse": round(best[0], 4),
           "t0": round(best[2], 3), "t1": round(best[3], 3), "dur": round(best[3] - best[2], 3),
           "alternatives": [{"curve": r[1], "rmse": round(r[0], 4)} for r in res[1:6]
                            if r[0] <= best[0] * 1.25 + 0.004]}
    out["shape_sure"] = all(shape_of(a["curve"]) == out["shape"] for a in out["alternatives"])
    # spring: 3 parameters (start, ω, ζ) — kept only when it beats the best named curve clearly
    if optimize is not None:
        bs = None
        for z0 in (0.3, 0.6, 0.9):
            w0 = 4.0 / (z0 * max(D, 0.05))

            def sresid(p):
                return spring_curve(np, t - p[0], p[1], p[2]) - y
            try:
                sol = optimize.least_squares(sresid, [ta, w0, z0], bounds=(
                    [ta - 1.0 * D - 0.2, 0.5, 0.03], [tb, 400.0, 1.0]))
                e = float(np.sqrt(np.mean(sol.fun ** 2)))
                if bs is None or e < bs[0]:
                    bs = (e, sol.x)
            except Exception:
                pass
        if bs is not None:
            e, (st, w, z) = bs
            out["spring"] = {"rmse": round(e, 4), "start": round(float(st), 3),
                             "omega": round(float(w), 2), "zeta": round(float(z), 3),
                             "stiffness": round(float(w * w), 1), "damping": round(float(2 * z * w), 2),
                             "settle_2pct_s": round(4.0 / max(z * w, 1e-6), 3)}
            if e < 0.75 * best[0] and best[0] > 0.01:
                out["shape"] = "spring"; out["shape_sure"] = True
        # bezier (CSS / Figma / After Effects-convertible): 4 control values + free start and end
        b0 = BEZIER_OF.get(best[1])
        if b0 is not None:
            def bresid(p):
                d = max(p[1] - p[0], 1e-3)
                return bezier_y(np, np.clip((t - p[0]) / d, 0, 1), p[2], p[3], p[4], p[5]) - y
            try:
                sol = optimize.least_squares(bresid, [best[2], best[3], *b0], bounds=(
                    [best[2] - D, best[2] + 0.2 * D, 0, -1.0, 0, -1.0],
                    [best[3] - 0.2 * D, best[3] + D, 1, 2.0, 1, 2.0]))
                e = float(np.sqrt(np.mean(sol.fun ** 2)))
                p = [round(float(v), 2) for v in sol.x[2:]]
                out["bezier"] = {"css": f"cubic-bezier({p[0]}, {p[1]}, {p[2]}, {p[3]})",
                                 "values": p, "rmse": round(e, 4),
                                 "t0": round(float(sol.x[0]), 3), "t1": round(float(sol.x[1]), 3),
                                 "dur": round(float(sol.x[1] - sol.x[0]), 3)}
            except Exception:
                pass
    return out


# ---- video I/O ----------------------------------------------------------------------------------
def probe(path: str) -> dict:
    d = {}
    # ffprobe 4.x has no `stream_side_data` section and refuses the whole query, so ask again
    # without it: there the rotation is in the `rotate` tag anyway
    for entries in ("stream=width,height,avg_frame_rate,r_frame_rate:stream_side_data=rotation"
                    ":stream_tags=rotate:format=duration",
                    "stream=width,height,avg_frame_rate,r_frame_rate:stream_tags=rotate:format=duration"):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries,
                            "-of", "json", path], capture_output=True, text=True, errors="replace")
        try:
            d = json.loads(r.stdout or "{}")
        except ValueError:
            d = {}
        if d.get("streams"):
            break
    st = (d.get("streams") or [{}])[0]

    def rate(s):
        try:
            a, b = str(s).split("/")
            return float(a) / float(b) if float(b) else 0.0
        except Exception:
            return 0.0
    w, h = int(st.get("width") or 0), int(st.get("height") or 0)
    rot = 0
    for sd in st.get("side_data_list") or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    rot = rot or int(float((st.get("tags") or {}).get("rotate", 0) or 0))
    if abs(rot) % 180 == 90:
        w, h = h, w
    return {"w": w, "h": h, "fps": rate(st.get("avg_frame_rate")) or rate(st.get("r_frame_rate")),
            "duration": float((d.get("format") or {}).get("duration") or 0.0)}


def decode(path: str, width: int, height: int, fps: float, pix: str, keep=None):
    """Frames from ffmpeg at the analysis size and rate. `keep`: a set of indices to keep (others are
    decoded and dropped) — the colour pass keeps only the frames it needs."""
    import numpy as np
    ch = 1 if pix == "gray" else 3
    vf = f"fps={fps:.6f},scale={width}:{height}:flags=area"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-an", "-sn", "-i", path, "-vf", vf,
                          "-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE)
    n = width * height * ch
    out, i = ({} if keep is not None else []), 0
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        if keep is None:
            out.append(np.frombuffer(buf, np.uint8).reshape(height, width, ch)[..., 0] if ch == 1
                       else np.frombuffer(buf, np.uint8).reshape(height, width, ch))
        elif i in keep:
            out[i] = np.frombuffer(buf, np.uint8).reshape(height, width, ch).copy()
        i += 1
    p.stdout.close(); p.wait()
    return out


# ---- camera -------------------------------------------------------------------------------------
def camera_step(np, cv2, a, b):
    """Global similarity a → b, or (None, why). ⛔ Gated twice: the inliers must AGREE (count) and
    must be SPREAD across the frame — features clustered on one moving element would otherwise
    report that element's motion as a camera move."""
    h, w = a.shape
    p0 = cv2.goodFeaturesToTrack(a, maxCorners=600, qualityLevel=0.01, minDistance=6, blockSize=5)
    # ⛔ A few dozen corners all sitting on the graphics is not a background. With 31 corners on three
    # cards, RANSAC found a 'similarity' that one scaling card and one still card both satisfied
    # within tolerance and reported a push-in with a roll (synthetic test, 2026-10-24).
    if p0 is None or len(p0) < CAM_MIN_FEATURES:
        return None, "flat"
    lk = dict(winSize=(21, 21), maxLevel=3,
              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    p1, s1, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, **lk)
    if p1 is None:
        return None, "unsolved"
    p0r, s2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, **lk)
    fbe = np.linalg.norm((p0 - p0r).reshape(-1, 2), axis=1)
    ok = (s1.ravel() == 1) & (s2.ravel() == 1) & (fbe < 1.0)
    if ok.sum() < CAM_MIN_FEATURES:
        return None, "unsolved"
    ga, gb = p0.reshape(-1, 2)[ok], p1.reshape(-1, 2)[ok]
    M, inl = cv2.estimateAffinePartial2D(ga, gb, method=cv2.RANSAC, ransacReprojThreshold=1.5,
                                         maxIters=3000, confidence=0.995)
    if M is None or inl is None:
        return None, "unsolved"
    inl = inl.ravel().astype(bool)
    if inl.sum() < CAM_MIN_INLIERS:
        return None, "unsolved"
    # ⛔ ON A FLAT BACKGROUND THE ONLY CORNERS ARE ON THE ELEMENTS. RANSAC then returns the motion of
    # whichever element has the most corners — the first version reported a card scaling up as a
    # 4 % push-in with a 4.7° roll (synthetic test, 2026-10-24). The camera must explain MOST of
    # what is tracked, and must not be contradicted by a still majority.
    if inl.sum() < 0.5 * len(ga):
        return None, "split"
    still = np.linalg.norm(gb - ga, axis=1) < 0.5
    pred = cv2.transform(ga[inl].reshape(-1, 1, 2), M).reshape(-1, 2)
    if (float(np.linalg.norm(pred - ga[inl], axis=1).max()) > 1.0
            and still.sum() >= 0.3 * len(ga) and not still[inl].any()):
        return None, "split"
    cells = {(int(x * 4 // w), int(y * 4 // h)) for x, y in ga[inl]}
    if len(cells) < CAM_MIN_CELLS:
        return None, "concentrated"
    s = math.hypot(M[0, 0], M[1, 0])
    if abs(M[0, 2]) > 0.3 * w or abs(M[1, 2]) > 0.3 * h or not 0.8 < s < 1.25:
        return None, "bounds"
    return M, "ok"


def decompose(np, M3, w: int, h: int) -> dict:
    """A 3×3 content transform → what the frame did, measured at the frame CENTRE (a zoom about the
    centre is not a pan). `content_*` is how the picture moved; the camera did the opposite."""
    c = np.array([w / 2.0, h / 2.0, 1.0])
    cc = M3 @ c
    A = M3[:2, :2]
    s = math.sqrt(abs(float(np.linalg.det(A))))
    ang = math.degrees(math.atan2(A[1, 0] - A[0, 1], A[0, 0] + A[1, 1]))
    return {"content_dx": float(cc[0] - c[0]) / w, "content_dy": float(cc[1] - c[1]) / h,
            "scale": s, "content_rot": ang}


def camera_words(dx: float, dy: float, s: float, rot: float, parallax: bool) -> str:
    """Named from the CAMERA's point of view: content moving left = the camera panned right."""
    parts = []
    if abs(s - 1) >= 0.03:
        parts.append(("push-in/zoom-in" if s > 1 else "pull-out/zoom-out") + f" ×{s:.2f}")
    if abs(dx) >= 0.01:
        parts.append(f"pan/truck {'left' if dx > 0 else 'right'} {abs(dx) * 100:.0f}%W")
    if abs(dy) >= 0.01:
        parts.append(f"tilt/pedestal {'up' if dy > 0 else 'down'} {abs(dy) * 100:.0f}%H")
    if abs(rot) >= 1.0:
        parts.append(f"roll {abs(rot):.1f}° {'counter-clockwise' if rot > 0 else 'clockwise'}")
    if not parts:
        return "static"
    return " + ".join(parts) + (" (parallax: a 3D move, the 2D numbers are approximate)" if parallax else "")


# ---- change detection ---------------------------------------------------------------------------
def residual(np, cv2, a, b, M, floor: float, min_area: float):
    """What changed between a and b once the camera is taken out → (boxes, changed fraction, global)."""
    h, w = a.shape
    if M is not None:
        aw = cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        valid = cv2.warpAffine(np.full_like(a, 255), M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        valid = cv2.erode(valid, np.ones((5, 5), np.uint8))
    else:
        aw, valid = a, None
    d = cv2.absdiff(cv2.GaussianBlur(aw, (5, 5), 0), cv2.GaussianBlur(b, (5, 5), 0))
    if valid is not None:
        d[valid == 0] = 0
    thr = max(floor, 4.0 * float(np.median(d)) + 3.0)
    m = (d > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    frac = float(m.mean())
    if frac > GLOBAL_AREA:
        return [], frac, True
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    boxes = [tuple(int(v) for v in stats[i, :4]) for i in range(1, n)
             if stats[i, 4] >= min_area * w * h]
    return boxes, frac, False


def _union(a, b):
    x0, y0 = min(a[0], b[0]), min(a[1], b[1])
    x1, y1 = max(a[0] + a[2], b[0] + b[2]), max(a[1] + a[3], b[1] + b[3])
    return (x0, y0, x1 - x0, y1 - y0)


def _expand(b, f: float, px: float, w: int, h: int):
    ex, ey = b[2] * f + px, b[3] * f + px
    x0, y0 = max(0, b[0] - ex), max(0, b[1] - ey)
    x1, y1 = min(w, b[0] + b[2] + ex), min(h, b[1] + b[3] + ey)
    return (int(x0), int(y0), int(x1 - x0), int(y1 - y0))


def _inter(a, b) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return max(0, x1 - x0) * max(0, y1 - y0)


def _iou(a, b) -> float:
    i = _inter(a, b)
    u = a[2] * a[3] + b[2] * b[3] - i
    return i / u if u > 0 else 0.0


def change_events(pair_boxes: dict, w: int, h: int, gap: int = 2) -> list:
    """Change boxes over time → events: an interval in which one region keeps changing.

    ⛔ A flat-coloured element moving a few pixels changes only along its leading and trailing edges:
    two thin slivers an element's width apart, which a box-overlap tracker files as two tracks. So
    tracks that overlap in TIME and sit within an element's reach of each other in SPACE share one
    cut-out region (`swept`): GrabCut cuts the WHOLE element out of it, seeded by each track's own
    change (`boxes`)."""
    tracks = []
    for k in sorted(pair_boxes):
        recent = []
        for tr in tracks:
            if k - tr["k1"] <= gap + 1:
                ks = [kk for kk in tr["boxes"] if k - gap - 1 <= kk < k]
                if ks:
                    mb = tr["boxes"][ks[0]]
                    for kk in ks[1:]:
                        mb = _union(mb, tr["boxes"][kk])
                    recent.append((tr, _expand(mb, 0.25, 0.02 * w, w, h)))
        for bb in pair_boxes[k]:
            best, bo = None, 0
            for tr, mb in recent:
                ov = _inter(mb, bb)
                if ov > bo:
                    best, bo = tr, ov
            if best is None:
                tracks.append({"k0": k, "k1": k, "boxes": {k: bb}})
            else:
                best["boxes"][k] = _union(best["boxes"][k], bb) if k in best["boxes"] else bb
                best["k1"] = k
    for tr in tracks:
        sw = None
        for bb in tr["boxes"].values():
            sw = bb if sw is None else _union(sw, bb)
        tr["swept"] = sw
    # union-find: overlap in time (gap allowed) and near in space
    parent = list(range(len(tracks)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, a in enumerate(tracks):
        for j in range(i + 1, len(tracks)):
            b = tracks[j]
            if a["k0"] > b["k1"] + gap or b["k0"] > a["k1"] + gap:
                continue
            # a sliver's long side is the element's height or width; its partner is within that
            reach = max(a["swept"][2], a["swept"][3], b["swept"][2], b["swept"][3])
            if _inter(_expand(a["swept"], 0, reach + 0.02 * w, w, h), b["swept"]) > 0:
                parent[find(j)] = find(i)
    groups = {}
    for i, tr in enumerate(tracks):
        groups.setdefault(find(i), []).append(tr)
    # ⛔ The group is only the REGION to cut the element out of, not the element: merging the tracks
    # themselves fused a card sliding past another card that was scaling up, and the slide was lost
    # (its seeds were overwritten by the other card's, synthetic test 2026-10-24). Each track keeps
    # its own seeds; slivers of one element find the same element and are merged after tracking.
    events = []
    for trs in groups.values():
        roi = None
        for tr in trs:
            roi = tr["swept"] if roi is None else _union(roi, tr["swept"])
        for tr in trs:
            events.append({"k0": tr["k0"], "k1": tr["k1"], "boxes": tr["boxes"], "swept": roi,
                           "own": tr["swept"]})
    events.sort(key=lambda e: (e["k0"], e["own"][0]))
    return events


def cut_out(np, cv2, colour, roi_box, seed_boxes, min_px: float, cache: dict | None = None,
            key=None) -> list:
    """GrabCut inside an event's swept box → the element(s) as (bbox, mask) at this frame. Only
    components that overlap the change seen at this end of the event are kept.

    ⛔ GrabCut is quadratic in patience: on a 20 s screen recording, 50 full-resolution cuts took
    130 of 152 seconds (profiled 2026-10-24). The region is cut at ≤ 25,000 px and the mask scaled
    back, and one region at one frame is cut ONCE however many change tracks share it."""
    H, W = colour.shape[:2]
    if cache is not None and key in cache:
        parts = cache[key]
    else:
        parts = _grab_parts(np, cv2, colour, roi_box, min_px)
        if cache is not None:
            cache[key] = parts
    return [(bb, full) for bb, full in parts
            if any(_inter(_expand(sb, 0.1, 3, W, H), bb) > 0 for sb in seed_boxes)]


def _grab_parts(np, cv2, colour, roi_box, min_px: float) -> list:
    H, W = colour.shape[:2]
    rx, ry, rw, rh = _expand(roi_box, 0.15, 10, W, H)
    if rw < 12 or rh < 12:
        return []
    f = min(1.0, math.sqrt(25000.0 / (rw * rh)))
    roi = np.ascontiguousarray(colour[ry:ry + rh, rx:rx + rw])
    if f < 1.0:
        roi = cv2.resize(roi, (max(8, int(rw * f)), max(8, int(rh * f))), interpolation=cv2.INTER_AREA)
    sh, sw = roi.shape[:2]
    inner = (max(1, int((roi_box[0] - rx - 2) * f)), max(1, int((roi_box[1] - ry - 2) * f)),
             min(sw - 2, int((roi_box[2] + 4) * f)), min(sh - 2, int((roi_box[3] + 4) * f)))
    if inner[2] < 4 or inner[3] < 4:
        return []
    mask = np.zeros((sh, sw), np.uint8)
    bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(roi, mask, inner, bg, fg, 3, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return []
    m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    if f < 1.0:
        m = cv2.resize(m, (rw, rh), interpolation=cv2.INTER_NEAREST)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # ⛔ An element with detail inside it (a card with text, a lower third with bars) comes out of
    # GrabCut in pieces, and each piece was tracked as its own element: one lower third became three
    # (synthetic test, 2026-10-24). Pieces closer than ~2 % of the frame are one element; the gaps
    # between them are filled so the element's mask is solid.
    g = max(3, int(round(0.02 * W)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * g + 1, 2 * g + 1))
    md = cv2.dilate(m, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(md, connectivity=8)
    out = []
    for i in range(1, n):
        part = ((lab == i) & (m > 0)).astype(np.uint8)
        if int(part.sum()) < min_px:
            continue
        part = cv2.morphologyEx(part, cv2.MORPH_CLOSE, k)
        ys, xs = np.nonzero(part)
        bb = (int(xs.min() + rx), int(ys.min() + ry), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
        full = np.zeros((H, W), np.uint8)
        full[ry:ry + rh, rx:rx + rw][part > 0] = 255
        out.append((bb, full))
    return out


# ---- element tracking ---------------------------------------------------------------------------
class Tracker:
    """ECC (affine) template tracking of one element through a shot, from a reference frame."""

    def __init__(self, np, cv2, frames, i_lo, i_hi):
        self.np, self.cv2, self.frames = np, cv2, frames
        self.i_lo, self.i_hi = i_lo, i_hi
        self.blur = {}

    def _f(self, i):
        if i not in self.blur:
            self.blur[i] = self.cv2.GaussianBlur(self.frames[i], (3, 3), 0)
            if len(self.blur) > 400:
                self.blur.pop(next(iter(self.blur)))
        return self.blur[i]

    def track(self, ref: int, bbox, mask=None, lo=None, hi=None) -> dict:
        np, cv2 = self.np, self.cv2
        H, W = self.frames[ref].shape
        x, y, w, h = [int(v) for v in bbox]
        x0, y0 = max(0, x - 2), max(0, y - 2)
        x1, y1 = min(W, x + w + 2), min(H, y + h + 2)
        T = self._f(ref)[y0:y1, x0:x1].copy()
        # ⛔ A thin element (a scrollbar, a rule, one line of small text) does not constrain scale or
        # rotation: an affine fit on a 7-px-wide scrollbar spun it 71° in a frame (real screen
        # recording, 2026-10-24). Below 24 px on the short side only its position is measured.
        self.model = cv2.MOTION_AFFINE if min(x1 - x0, y1 - y0) >= 24 else cv2.MOTION_TRANSLATION
        tm = None
        if mask is not None:
            tm = cv2.dilate(mask[y0:y1, x0:x1], np.ones((7, 7), np.uint8))
        self.tsd = float(T[tm > 0].std()) if tm is not None and (tm > 0).any() else float(T.std())
        # the element's OUTLINE (its tightest rotated rectangle at the reference frame), in template
        # coordinates — what the sheets draw and the edge test uses, not the template's own box
        self.outline = np.array([[0, 0], [x1 - x0, 0], [x1 - x0, y1 - y0], [0, y1 - y0]], np.float32)
        self.outline_wh = (float(w), float(h), 0.0)
        if mask is not None:
            cnts, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                rr = cv2.minAreaRect(max(cnts, key=cv2.contourArea))
                self.outline = (cv2.boxPoints(rr) - np.array([x0, y0], np.float32)).astype(np.float32)
                self.outline_wh = (float(rr[1][0]), float(rr[1][1]), float(rr[2]))
        rec = {ref: self._rec(ref, np.array([[1, 0, x0], [0, 1, y0]], np.float32), 1.0, T, tm)}
        lost = {}
        for step, stop in ((-1, max(self.i_lo, lo if lo is not None else self.i_lo)),
                           (1, min(self.i_hi - 1, hi if hi is not None else self.i_hi - 1))):
            Wp = Wpp = rec[ref]["W"]
            i = ref + step
            while (i >= stop) if step < 0 else (i <= stop):
                pred = Wp.copy()
                pred[:, 2] += (Wp[:, 2] - Wpp[:, 2])          # constant velocity
                r = self._ecc(T, tm, i, pred)
                if r is None:
                    lost[step] = (i, "lost")
                    break
                rho, Wn = r
                rr = self._rec(i, Wn, rho, T, tm)
                why = self._why_lost(rr)
                prev = rec[i - step]
                # ⛔ a jump no animation makes in one frame is the tracker slipping, not the element
                if not why and (abs((rr["rot"] - prev["rot"] + 180) % 360 - 180) > 20
                                or not 0.75 < rr["s"] / max(prev["s"], 1e-6) < 1.33
                                or math.hypot(rr["cx"] - prev["cx"], rr["cy"] - prev["cy"]) > 0.25 * max(H, W)):
                    why = "jump"
                if why:
                    lost[step] = (i, why)
                    break
                rec[i] = rr
                Wpp, Wp = Wp, Wn
                i += step
        return {"ref": ref, "tw": x1 - x0, "th": y1 - y0, "rec": rec, "lost": lost,
                "outline_wh": self.outline_wh,
                "model": "affine" if self.model == cv2.MOTION_AFFINE else "position only"}

    def _ecc(self, T, tm, i, W0):
        np, cv2 = self.np, self.cv2
        F = self._f(i)
        H, Wd = F.shape
        th, tw = T.shape
        corners = np.array([[0, 0, 1], [tw, 0, 1], [0, th, 1], [tw, th, 1]], np.float32) @ W0.T
        m = max(16, int(0.6 * max(tw, th)))
        rx0, ry0 = int(max(0, corners[:, 0].min() - m)), int(max(0, corners[:, 1].min() - m))
        rx1, ry1 = int(min(Wd, corners[:, 0].max() + m)), int(min(H, corners[:, 1].max() + m))
        if rx1 - rx0 < 8 or ry1 - ry0 < 8:
            return None
        roi = F[ry0:ry1, rx0:rx1]
        Wl = W0.copy(); Wl[0, 2] -= rx0; Wl[1, 2] -= ry0
        crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5)
        masked = tm is not None and hasattr(cv2, "findTransformECCWithMask")
        imask = np.full(roi.shape, 255, np.uint8)
        for f in (0.5, 1.0):                                # coarse to fine
            if f < 1:
                if min(th, tw) * f < 10:
                    continue
                Ts = cv2.resize(T, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
                Rs = cv2.resize(roi, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
                Ms = cv2.resize(tm, (Ts.shape[1], Ts.shape[0]), interpolation=cv2.INTER_NEAREST) if masked else None
                Ws = Wl.copy(); Ws[:, 2] *= f
                try:
                    if masked:
                        _, Ws = cv2.findTransformECCWithMask(Ts, Rs, Ms, np.full(Rs.shape, 255, np.uint8),
                                                             Ws, self.model, crit, 3)
                    else:
                        _, Ws = cv2.findTransformECC(Ts, Rs, Ws, self.model, crit, None, 3)
                    Wl = Ws.copy(); Wl[:, 2] /= f
                except cv2.error:
                    pass
            else:
                try:
                    if masked:
                        rho, Wl = cv2.findTransformECCWithMask(T, roi, tm, imask, Wl,
                                                               self.model, crit, 3)
                    else:
                        rho, Wl = cv2.findTransformECC(T, roi, Wl, self.model, crit, None, 3)
                except cv2.error:
                    return None
        Wl[0, 2] += rx0; Wl[1, 2] += ry0
        return float(rho), Wl

    def _rec(self, i, Wm, rho, T, tm):
        np, cv2 = self.np, self.cv2
        th, tw = T.shape
        F = self._f(i)
        H, Wd = F.shape
        Iw = cv2.warpAffine(F, Wm, (tw, th), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        sel = (tm > 0) if tm is not None and (tm > 0).any() else np.ones(T.shape, bool)
        contrast = float(Iw[sel].std()) / max(self.tsd, 1e-6)
        A = Wm[:, :2].astype(np.float64)
        sx, sy = float(np.hypot(A[0, 0], A[1, 0])), float(np.hypot(A[0, 1], A[1, 1]))
        c = Wm @ np.array([tw / 2.0, th / 2.0, 1.0], np.float32)
        quad = np.hstack([self.outline, np.ones((len(self.outline), 1), np.float32)]) @ Wm.T
        vis = self._visible(quad, Wd, H)
        return {"i": i, "W": Wm.copy(), "rho": rho, "cx": float(c[0]), "cy": float(c[1]),
                "s": math.sqrt(abs(float(np.linalg.det(A)))), "sx": sx, "sy": sy,
                "rot": math.degrees(math.atan2(A[1, 0] - A[0, 1], A[0, 0] + A[1, 1])),
                "contrast": contrast, "visible": vis, "quad": quad.tolist()}

    @staticmethod
    def _visible(quad, W, H) -> float:
        xs, ys = quad[:, 0], quad[:, 1]
        bw, bh = float(xs.max() - xs.min()), float(ys.max() - ys.min())
        if bw <= 0 or bh <= 0:
            return 0.0
        iw = max(0.0, min(W, float(xs.max())) - max(0.0, float(xs.min())))
        ih = max(0.0, min(H, float(ys.max())) - max(0.0, float(ys.min())))
        return iw * ih / (bw * bh)

    @staticmethod
    def _why_lost(r) -> str:
        if r["visible"] < 0.35:
            return "edge"
        if r["s"] < 0.12 or r["s"] > 10:
            return "scale"
        if r["contrast"] < MIN_CONTRAST:
            return "faded"
        if r["rho"] < ECC_MIN_RHO:
            return "lost"
        return ""


# ---- animation analysis -------------------------------------------------------------------------
def segments(np, t, sig, prop: str, fps: float, W: float):
    """Where a property moves: runs of speed above max(floor, 4 % of peak), short pauses merged."""
    n = len(t)
    if n < 4:
        return []
    v = np.gradient(sig, t, axis=0)
    sp = np.linalg.norm(v, axis=1) if sig.ndim > 1 else np.abs(v)
    if prop == "position":
        sp = sp / W
    sp = np.convolve(sp, np.ones(3) / 3, mode="same")
    peak = float(sp.max())
    if peak < FLOOR_SPEED[prop]:
        return []
    act = sp > max(FLOOR_SPEED[prop], SPEED_REL * peak)
    runs, i = [], 0
    while i < n:
        if act[i]:
            j = i
            while j + 1 < n and act[j + 1]:
                j += 1
            runs.append([i, j]); i = j + 1
        else:
            i += 1
    gap = max(3, int(round(0.12 * fps)))
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    out = []
    for a, b in merged:
        a = max(0, a - 1); b = min(n - 1, b + 1)
        seg = sig[a:b + 1]
        dev = np.linalg.norm(seg - seg[0], axis=1) if sig.ndim > 1 else np.abs(seg - seg[0])
        if prop == "position":
            dev = dev / W
        if float(dev.max()) >= MIN_CHANGE[prop]:
            out.append((a, b, float(sp[a:b + 1].max())))
    return out


def analyse_segment(np, optimize, t, sig, a: int, b: int, prop: str, fps: float, W: float, H: float,
                    lost_before: bool, lost_after: bool) -> dict:
    n = len(t)
    D = max((b - a) / fps, 1.0 / fps)
    pre = max(0, a - int(round(0.3 * D * fps)) - 2)
    post_hi = min(n - 1, b + int(round(0.6 * D * fps)) + 2)
    tail = sig[b:min(n, b + max(3, int(round(0.25 * D * fps))) + 1)]
    p0 = sig[a]
    p1 = np.median(tail, axis=0) if len(tail) else sig[b]
    d = p1 - p0
    dn = float(np.dot(d, d)) if sig.ndim > 1 else float(d * d)
    seg = sig[pre:post_hi + 1]
    tt = t[pre:post_hi + 1]
    excursion = (np.linalg.norm(seg - p0, axis=1) if sig.ndim > 1 else np.abs(seg - p0)).max()
    scale_den = W if prop == "position" else 1.0
    row = {"prop": prop, "t_start": round(float(t[a]), 3), "t_end": round(float(t[b]), 3),
           "partial_start": bool(lost_before and a <= 1),
           "partial_end": bool(lost_after and b >= n - 2)}
    if dn <= 0 or math.sqrt(dn) / scale_den < 0.35 * float(excursion) / scale_den:
        # it went somewhere and came back: a pulse (a bump, a wiggle), not a move
        k = int(np.argmax(np.linalg.norm(seg - p0, axis=1) if sig.ndim > 1 else np.abs(seg - p0)))
        row.update({"kind": "pulse", "peak_t": round(float(tt[k]), 3),
                    "peak": _fmt_delta(np, seg[k] - p0, prop, W, H)})
        return row
    prog = (np.dot(seg - p0, d) / dn) if sig.ndim > 1 else (seg - p0) / d
    row["kind"] = "move"
    row["from"], row["to"] = _fmt_val(np, p0, prop, W, H), _fmt_val(np, p1, prop, W, H)
    row["delta"] = _fmt_delta(np, d, prop, W, H)
    over = float(prog.max() - 1.0)
    row["overshoot_pct"] = round(100 * over, 1) if over > 0.02 else 0.0
    ia = np.nonzero(prog > 0.03)[0]
    ta = float(tt[ia[0]]) if len(ia) else float(t[a])
    ib = np.nonzero(prog > 0.97)[0]
    ib = ib[ib >= (ia[0] if len(ia) else 0)]
    tb = float(tt[ib[0]]) if len(ib) else float(t[b])
    row["visible_dur"] = round(tb - ta, 3)
    if over > 0.02:
        k = int(np.argmax(prog))
        inband = np.abs(prog[k:] - 1) <= 0.02
        last_out = np.nonzero(~inband)[0]
        settle_i = k + (int(last_out[-1]) + 1 if len(last_out) else 0)
        row["settle_s"] = round(float(tt[min(settle_i, len(tt) - 1)]) - tb, 3)
    v = np.gradient(prog, tt)
    kp = int(np.argmax(np.abs(v)))
    row["peak_speed"] = round(float(np.abs(np.gradient(seg, tt, axis=0)).max() if sig.ndim == 1 else
                                    np.linalg.norm(np.gradient(seg, tt, axis=0), axis=1).max())
                              / scale_den, 3)
    row["peak_at"] = round((float(tt[kp]) - ta) / max(tb - ta, 1e-3), 2)
    if prop == "position":
        chord = d / max(math.sqrt(dn), 1e-9)
        perp = np.abs((seg - p0) @ np.array([-chord[1], chord[0]]))
        row["path"] = "arc" if float(perp.max()) > 0.08 * math.sqrt(dn) else "straight"
    if row["partial_start"] or row["partial_end"]:
        # only part of the move is on screen: the curve name would be a guess
        row["easing"] = {"shape": ("decelerates" if row["peak_at"] < 0.35 else
                                   "accelerates" if row["peak_at"] > 0.65 else "even"),
                         "note": "partly off-screen or lost — curve not named"}
    else:
        row["easing"] = fit_easing(np, optimize, tt, prog, ta, tb)
    return row


def _fmt_val(np, v, prop, W, H):
    if prop == "position":
        return [round(float(v[0]) / W, 3), round(float(v[1]) / H, 3)]
    return round(float(v), 3)


def _fmt_delta(np, d, prop, W, H):
    if prop == "position":
        return {"dx_W": round(float(d[0]) / W, 3), "dy_H": round(float(d[1]) / H, 3)}
    return round(float(d), 3)


def anim_words(r: dict) -> str:
    p = r["prop"]
    if r["kind"] == "pulse":
        if p == "position":
            return f"nudges {r['peak']['dx_W'] * 100:+.0f}%W {r['peak']['dy_H'] * 100:+.0f}%H and returns"
        if p == "scale":
            return f"pulses ×{1 + r['peak']:.2f} and returns"
        if p == "rotation":
            return f"wiggles {r['peak']:+.0f}° and returns"
        return f"flickers {r['peak']:+.2f} opacity and returns"
    if p == "position":
        dx, dy = r["delta"]["dx_W"], r["delta"]["dy_H"]
        parts = []
        big = max(abs(dx), abs(dy))
        if abs(dx) >= 0.3 * big:
            parts.append(f"{'right' if dx > 0 else 'left'} {abs(dx) * 100:.1f}%W")
        if abs(dy) >= 0.3 * big:
            parts.append(f"{'down' if dy > 0 else 'up'} {abs(dy) * 100:.1f}%H")
        return "moves " + " + ".join(parts) + (" on an arc" if r.get("path") == "arc" else "")
    if p == "scale":
        return f"scales ×{r['to'] / max(r['from'], 1e-6):.2f} ({r['from']:.2f}→{r['to']:.2f} of its final size)"
    if p == "rotation":
        return f"rotates {abs(r['delta']):.0f}° {'clockwise' if r['delta'] > 0 else 'counter-clockwise'}"
    return f"{'fades in' if r['delta'] > 0 else 'fades out'} (opacity ≈ {r['from']:.2f}→{r['to']:.2f})"


def edge_of(cx, cy, quad, W, H) -> str:
    xs = [q[0] for q in quad]; ys = [q[1] for q in quad]
    near = {"left": min(xs) <= EDGE * W, "right": max(xs) >= (1 - EDGE) * W,
            "top": min(ys) <= EDGE * H, "bottom": max(ys) >= (1 - EDGE) * H}
    hit = [k for k, v in near.items() if v]
    return hit[0] if hit else ""


# ---- per-shot pipeline --------------------------------------------------------------------------
def analyse_shot(np, cv2, optimize, frames, i0: int, i1: int, fps: float, a, n_shot: int,
                 manual: list) -> dict:
    H, W = frames[i0].shape
    shot = {"n": n_shot, "t0": round(i0 / fps, 3), "t1": round(i1 / fps, 3),
            "dur": round((i1 - i0) / fps, 3), "frames": i1 - i0}
    # 1 · camera, pair by pair
    C = {i0: np.eye(3)}
    why = {}
    pair_boxes, global_pairs, fracs = {}, [], {}
    for k in range(i0 + 1, i1):
        M, w_ = camera_step(np, cv2, frames[k - 1], frames[k])
        why[w_] = why.get(w_, 0) + 1
        M3 = np.eye(3)
        if M is not None:
            M3[:2] = M
        C[k] = M3 @ C[k - 1]
        boxes, frac, glob = residual(np, cv2, frames[k - 1], frames[k], M, a.threshold, MIN_AREA)
        fracs[k] = frac
        if glob:
            global_pairs.append(k)
        elif boxes:
            pair_boxes[k] = boxes
    pairs = max(1, i1 - i0 - 1)
    cam_path = []
    for k in range(i0, i1):
        dct = decompose(np, C[k], W, H)
        cam_path.append({"t": round(k / fps, 4), "cam_x": round(-dct["content_dx"], 5),
                         "cam_y": round(-dct["content_dy"], 5), "zoom": round(dct["scale"], 5),
                         "content_rot": round(dct["content_rot"], 3)})
    last = decompose(np, C[i1 - 1], W, H)
    # pairs in which the camera moved by more than 0.3 px at the frame centre, or zoomed 0.1 %
    moving = []
    for k in range(i0 + 1, i1):
        p, q = cam_path[k - i0 - 1], cam_path[k - i0]
        if (math.hypot((q["cam_x"] - p["cam_x"]) * W, (q["cam_y"] - p["cam_y"]) * H) > 0.3
                or abs(q["zoom"] / max(p["zoom"], 1e-9) - 1) > 0.001):
            moving.append(k)
    parallax = bool(moving) and float(np.mean([fracs[k] for k in moving])) > 0.20
    cam = {"measured_pairs": why.get("ok", 0), "pairs": pairs, "why_unmeasured": {k: v for k, v in why.items() if k != "ok"},
           "content_dx": round(last["content_dx"], 4), "content_dy": round(last["content_dy"], 4),
           "scale": round(last["scale"], 4), "content_rot": round(last["content_rot"], 2),
           "parallax": parallax, "global_change_pairs": len(global_pairs)}
    ok_frac = why.get("ok", 0) / pairs
    if ok_frac < 0.3 and why.get("flat", 0) + why.get("concentrated", 0) >= 0.5 * pairs:
        cam["words"] = "static as far as can be seen (flat background — a camera move over it is invisible)"
        cam["measurable"] = False
    elif ok_frac < 0.3:
        cam["words"] = "UNMEASURED (no reliable frame pairs)"
        cam["measurable"] = False
    else:
        cam["measurable"] = True
        cam["words"] = camera_words(last["content_dx"], last["content_dy"], last["scale"],
                                    last["content_rot"], parallax)
    # camera animations (the camera's own timing and easing)
    tt = np.array([p["t"] for p in cam_path])
    cam_anims = []
    if cam["measurable"]:
        sigs = {"position": np.array([[p["cam_x"] * W, p["cam_y"] * H] for p in cam_path]),
                "scale": np.array([p["zoom"] for p in cam_path]),
                "rotation": np.array([-p["content_rot"] for p in cam_path])}
        for prop, sig in sigs.items():
            for s_a, s_b, _ in segments(np, tt, sig, prop, fps, W):
                r = analyse_segment(np, optimize, tt, sig, s_a, s_b, prop, fps, W, H, True, True)
                r["what"] = {"position": "camera pan/tilt (frame path)", "scale": "camera push/zoom",
                             "rotation": "camera roll"}[prop]
                cam_anims.append(r)
    cam["animations"] = cam_anims
    shot["camera"] = cam
    shot["camera_path"] = cam_path
    # 2 · change events → elements
    events = change_events(pair_boxes, W, H)
    shot["events_detected"] = len(events)
    return shot, events, C


def place_elements(np, cv2, frames, colours, shot, events, C, i0, i1, fps, a, manual):
    """Cut each event's element out at a settled frame, track it, merge duplicates.

    Every element is tracked through the WHOLE shot (until it is lost), not just around the change
    that found it. ⛔ With a window of ±0.6 s round each change, a status bar was re-found at every
    scroll of a screen recording and reported as seven elements that never shared a frame, so the
    duplicate test could not see they were one (real clip, 2026-10-24)."""
    H, W = frames[i0].shape
    tr = Tracker(np, cv2, frames, i0, i1)
    cands = []
    grab_cache = {}
    for e in events[: a.max_events]:
        f0, f1 = max(i0, e["k0"] - 1), min(i1 - 1, e["k1"])
        tail = [e["boxes"][k] for k in e["boxes"] if k >= e["k1"] - 2]
        head = [e["boxes"][k] for k in e["boxes"] if k <= e["k0"] + 2]
        got = []
        for ref, seeds in ((min(i1 - 1, f1 + 2), tail), (f0, head)):
            col = colours.get(ref)
            if col is None:
                continue
            got = cut_out(np, cv2, col, e["swept"], seeds, MIN_AREA * W * H, grab_cache,
                          (ref, tuple(e["swept"])))
            if got:
                for bb, mk in got:
                    cands.append({"ref": ref, "bbox": bb, "mask": mk, "lo": i0, "hi": i1 - 1,
                                  "event": (e["k0"], e["k1"])})
                break
        if not got:   # GrabCut found nothing: track the change box itself, flagged
            bb = tail[-1] if tail else e["swept"]
            cands.append({"ref": min(i1 - 1, f1 + 2), "bbox": bb, "mask": None, "lo": i0,
                          "hi": i1 - 1, "event": (e["k0"], e["k1"]), "rough": True})
    for m in manual:
        cands.append({"ref": m["i"], "bbox": m["bbox"], "mask": None, "lo": i0, "hi": i1 - 1,
                      "event": None, "name": m.get("name"), "manual": True})
    tracks = []
    for c in cands:
        T = frames[c["ref"]][int(c["bbox"][1]):int(c["bbox"][1] + c["bbox"][3]),
                             int(c["bbox"][0]):int(c["bbox"][0] + c["bbox"][2])]
        if T.size == 0 or float(T.std()) < 3.0:
            continue                                     # nothing to lock onto
        res = tr.track(c["ref"], c["bbox"], c["mask"], c["lo"], c["hi"])
        if len(res["rec"]) < 3:
            continue
        res.update({k: c.get(k) for k in ("event", "name", "manual", "rough")})
        res["bbox"] = c["bbox"]
        tracks.append(res)
    # merge duplicates: the same element found by two events (or two slivers of one)
    tracks.sort(key=lambda r: -len(r["rec"]))
    kept = []
    for r in tracks:
        dup = None
        for k in kept:
            common = sorted(set(r["rec"]) & set(k["rec"]))
            if len(common) < 3:
                continue
            ious = [_iou(_qbox(r["rec"][i]["quad"]), _qbox(k["rec"][i]["quad"])) for i in common[::max(1, len(common) // 12)]]
            if float(np.mean(ious)) > 0.5:
                dup = k; break
        if dup is None:
            kept.append(r)
        elif r.get("manual") and not dup.get("manual"):
            kept[kept.index(dup)] = r
    return merge_rigid(np, kept, W)


def merge_rigid(np, tracks: list, W: int) -> list:
    """Pieces that move as one rigid body, side by side, are one element (or one group the designer
    animated together). ⛔ Without this a lower third came out as three 'elements' — its left end,
    its right half and one bar — each a GrabCut piece of the same card (synthetic test, 2026-10-24)."""
    for r in tracks:
        r.setdefault("members", 1)
    changed = True
    while changed:
        changed = False
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                a, b = tracks[i], tracks[j]
                common = sorted(set(a["rec"]) & set(b["rec"]))
                if len(common) < 5 or len(common) < 0.3 * min(len(a["rec"]), len(b["rec"])):
                    continue
                dx = np.array([a["rec"][k]["cx"] - b["rec"][k]["cx"] for k in common])
                dy = np.array([a["rec"][k]["cy"] - b["rec"][k]["cy"] for k in common])
                sr = np.array([a["rec"][k]["s"] / max(b["rec"][k]["s"], 1e-6) for k in common])
                if np.ptp(dx) > 1.5 or np.ptp(dy) > 1.5 or np.ptp(sr) > 0.02 * float(sr.mean()):
                    continue
                k = common[len(common) // 2]
                qa, qb = _qbox(a["rec"][k]["quad"]), _qbox(b["rec"][k]["quad"])
                if _inter(_expand(qa, 0, 0.03 * W, 10 ** 6, 10 ** 6), qb) <= 0:
                    continue
                keep, drop = (a, b) if a["tw"] * a["th"] >= b["tw"] * b["th"] else (b, a)
                keep["bbox"] = _union(tuple(keep["bbox"]), tuple(drop["bbox"]))
                keep["members"] += drop["members"]
                tracks.remove(drop)
                changed = True
                break
            if changed:
                break
    return tracks


def _qbox(quad):
    xs = [q[0] for q in quad]; ys = [q[1] for q in quad]
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def element_report(np, optimize, tr, C, fps, W, H, i0, i1, item_id) -> dict:
    idx = sorted(tr["rec"])
    t = np.array([i / fps for i in idx])
    rec = [tr["rec"][i] for i in idx]
    ref = tr["rec"][tr["ref"]]
    # screen vs world: does it stay put on screen while the camera moves under it?
    scr = np.array([[r["cx"], r["cy"]] for r in rec])
    wld = []
    for i, r in zip(idx, rec):
        inv = np.linalg.inv(C[i])
        p = inv @ np.array([r["cx"], r["cy"], 1.0])
        wld.append([p[0], p[1]])
    wld = np.array(wld)
    cam_move = float(np.linalg.norm(np.ptp(scr - wld, axis=0)) / W)
    scr_move = float(np.linalg.norm(np.ptp(scr, axis=0)) / W)
    locked = cam_move > 0.03 and scr_move < 0.006 + 0.1 * cam_move
    use = scr if (locked or cam_move < 0.003) else wld
    cam_s = np.array([math.sqrt(abs(float(np.linalg.det(C[i][:2, :2])))) for i in idx])
    cam_r = np.array([math.degrees(math.atan2(C[i][1, 0] - C[i][0, 1], C[i][0, 0] + C[i][1, 1]))
                      for i in idx])
    s = np.array([r["s"] for r in rec]); rot = np.array([r["rot"] for r in rec])
    if not locked and cam_move >= 0.003:
        s = s / cam_s * cam_s[idx.index(tr["ref"])]
        rot = rot - (cam_r - cam_r[idx.index(tr["ref"])])
    s_end = s[-1] if s[-1] > 0 else 1.0
    lost_before = (-1 in tr["lost"]) and tr["lost"][-1][0] > i0
    lost_after = (1 in tr["lost"]) and tr["lost"][1][0] < i1 - 1
    s_rel = s / s_end

    def how(r, r2, why, s_now, entering):
        """How an element arrives (or leaves), from why the track stopped at that end."""
        e = edge_of(r["cx"], r["cy"], r["quad"], W, H)
        moving = math.hypot(r["cx"] - r2["cx"], r["cy"] - r2["cy"]) > 1.0
        if why == "edge" or (e and moving):
            return "edge", (f"enters from the {e} edge" if entering else f"exits by the {e} edge") if e else (
                "enters from off-frame" if entering else "exits off-frame")
        if why == "scale":
            return "scale", "scales up from nothing" if entering else "scales down to nothing"
        if why == "faded" or r["contrast"] < 0.6:
            return "fade", "fades in" if entering else "fades out"
        if why == "jump":
            return "lost", "tracking slipped (overlap, blur or a look-alike nearby)"
        if why == "lost" and moving:
            return "lost", "tracking lost while it moved (motion blur or overlap)"
        size = f" at {s_now * 100:.0f}% of its final size" if s_now < 0.9 else ""
        return "cut", ("cuts in (appears between two frames)" if entering else
                       "cuts out (gone between two frames)") + size
    arrive = leave = None
    # a move already under way when the shot starts (or still going when it ends) is cut by the edit
    cut_start, cut_end = idx[0] == i0, idx[-1] == i1 - 1
    if lost_before:
        kind, words = how(rec[0], rec[min(1, len(rec) - 1)], tr["lost"][-1][1], float(s_rel[0]), True)
        arrive = {"t": round(idx[0] / fps, 3), "how": words, "kind": kind}
        cut_start = cut_start or kind in ("edge", "lost")
    if lost_after:
        kind, words = how(rec[-1], rec[max(0, len(rec) - 2)], tr["lost"][1][1], float(s_rel[-1]), False)
        leave = {"t": round(idx[-1] / fps, 3), "how": words, "kind": kind}
        cut_end = cut_end or kind in ("edge", "lost")
    con = np.array([r["contrast"] for r in rec])
    # opacity proxy: contrast against the element at its MOST visible frame (1.0), not at the
    # reference frame — a reference caught mid-fade had read as "opacity 1.50 → 1.00"
    sigs = {"position": use, "scale": s_rel, "rotation": rot,
            "opacity": np.clip(con / max(float(np.percentile(con, 95)), 1e-6), 0, 1.0)}
    def _cm(a, b):
        d = C[a] - C[b]
        return bool(np.abs(d[:2, 2]).max() > 0.3 or np.abs(d[:2, :2]).max() > 0.002)
    cam_moving = [False] + [_cm(idx[k], idx[k - 1]) for k in range(1, len(idx))]
    measured = dict(sigs)
    if tr.get("model") == "position only":
        measured.pop("scale"); measured.pop("rotation"); measured.pop("opacity")
    anims = []
    for prop, sig in measured.items():
        for a_, b_, _ in segments(np, t, sig, prop, fps, W):
            r = analyse_segment(np, optimize, t, sig, a_, b_, prop, fps, W, H, cut_start, cut_end)
            if r["kind"] == "pulse":
                pk = r["peak"]
                size = math.hypot(pk["dx_W"], pk["dy_H"]) if prop == "position" else abs(pk)
                if size < PULSE_MIN[prop]:
                    continue                       # tracker breathing, not an animation
                # ⛔ a screen-locked element whose template holds a sliver of the moving picture
                # "pulses" exactly while the camera moves — three ×1.07–1.12 pulses on a status bar,
                # one per scroll (real clip, 2026-10-24). Not an animation.
                if locked and any(cam_moving[k] for k in range(a_, b_ + 1)):
                    continue
            anims.append(r)
    anims.sort(key=lambda r: r["t_start"])
    sq = max(abs(r["sx"] / max(r["sy"], 1e-6) - ref["sx"] / max(ref["sy"], 1e-6)) for r in rec)
    bx = tr["bbox"]
    full = (bx[2] * bx[3]) / float(W * H) > 0.6
    el = {"id": item_id, "name": tr.get("name"), "manual": bool(tr.get("manual")),
          "full_frame": bool(full), "model": tr.get("model", "affine"), "members": tr.get("members", 1),
          "rough_cutout": bool(tr.get("rough")),
          "ref_t": round(tr["ref"] / fps, 3),
          "box_at_ref": [round(bx[0] / W, 3), round(bx[1] / H, 3), round(bx[2] / W, 3), round(bx[3] / H, 3)],
          "tracked": [round(idx[0] / fps, 3), round(idx[-1] / fps, 3)],
          "screen_locked": bool(locked), "coords": "screen" if (locked or cam_move < 0.003) else "world",
          "arrives": arrive, "leaves": leave, "animations": anims,
          "squash_stretch_pct": round(100 * sq, 1) if sq > 0.06 else 0.0,
          "track_quality": round(float(np.median([r["rho"] for r in rec])), 3),
          "frames": [{"t": round(i / fps, 4), "x": round(r["cx"] / W, 4), "y": round(r["cy"] / H, 4),
                      "scale": round(float(sv), 4), "rot": round(float(rv), 2),
                      "opacity": round(float(ov), 3), "rho": round(r["rho"], 3),
                      "quad": [[round(q[0], 1), round(q[1], 1)] for q in r["quad"]]}
                     for i, r, sv, rv, ov in zip(idx, rec, sigs["scale"], sigs["rotation"], sigs["opacity"])]}
    for an in anims:                                   # the start a designer would key: the fit's
        ez = an.get("easing") or {}
        an["start"] = ez.get("t0", an["t_start"]) if "curve" in ez else an["t_start"]
    starts = [an["start"] for an in anims if an["kind"] == "move"]
    el["starts"] = min([x for x in ([arrive["t"]] if arrive else []) + starts], default=None)
    return el


def stagger(elements: list) -> dict:
    s = sorted((e["starts"], e["id"]) for e in elements if e.get("starts") is not None)
    if len(s) < 2:
        return {"order": [i for _, i in s], "steps": []}
    steps = [round(b[0] - a[0], 3) for a, b in zip(s, s[1:])]
    pos = [x for x in steps if x > 0.005]
    out = {"order": [i for _, i in s], "starts": [x for x, _ in s], "steps": steps}
    if pos:
        m = sorted(pos)[len(pos) // 2]
        mean = sum(pos) / len(pos)
        sd = (sum((x - mean) ** 2 for x in pos) / len(pos)) ** 0.5
        out.update({"median_step": round(m, 3), "regular": bool(len(pos) >= 2 and sd < 0.25 * mean)})
    return out


# ---- sheets -------------------------------------------------------------------------------------
PALETTE = [(66, 135, 245), (60, 200, 90), (40, 160, 250), (220, 90, 200), (60, 220, 230),
           (230, 140, 60), (150, 120, 255), (90, 230, 160), (200, 200, 70), (255, 110, 110)]


def overlay_sheet(np, cv2, colours, shot, fps, out_png: str) -> bool:
    i0, i1 = int(round(shot["t0"] * fps)), int(round(shot["t1"] * fps))
    picks = sorted({min(i1 - 1, i0 + int(round(f * (i1 - 1 - i0)))) for f in (0, .2, .4, .6, .8, 1)})
    tiles = []
    for i in picks:
        im = colours.get(i)
        if im is None:
            continue
        im = im.copy()
        t = i / fps
        for el in shot["elements"]:
            fr = min(el["frames"], key=lambda f: abs(f["t"] - t))
            if abs(fr["t"] - t) > 0.5 / fps:
                continue
            col = PALETTE[(el["id"] - 1) % len(PALETTE)]
            q = np.array(fr["quad"], np.float32).reshape(-1, 1, 2)
            cv2.polylines(im, [np.round(q).astype(np.int32)], True, col, 2, cv2.LINE_AA)
            cv2.putText(im, f"#{el['id']}", (int(q[0, 0, 0]) + 2, int(q[0, 0, 1]) + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.rectangle(im, (0, 0), (im.shape[1], 18), (0, 0, 0), -1)
        cv2.putText(im, f"shot {shot['n']}  {t:6.2f}s", (4, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(im)
    if not tiles:
        return False
    while len(tiles) % 3:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[r:r + 3]) for r in range(0, len(tiles), 3)]
    return bool(cv2.imwrite(out_png, np.vstack(rows)))


def curves_sheet(np, shot, out_png: str) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    lib = ease_library(np)
    rows = [("camera", None, an) for an in shot["camera"]["animations"] if an["kind"] == "move"]
    for el in shot["elements"]:
        rows += [(f"#{el['id']}", el, an) for an in el["animations"] if an["kind"] == "move"]
    rows = rows[:16]
    if not rows:
        return False
    nc = 4
    nr = (len(rows) + nc - 1) // nc
    fig, axs = plt.subplots(nr, nc, figsize=(4 * nc, 2.8 * nr), squeeze=False)
    for ax in axs.ravel():
        ax.axis("off")
    for ax, (who, el, an) in zip(axs.ravel(), rows):
        ax.axis("on")
        if el is not None:
            fr = el["frames"]
            key = {"position": None, "scale": "scale", "rotation": "rot", "opacity": "opacity"}[an["prop"]]
            t = np.array([f["t"] for f in fr])
            if key is None:
                xy = np.array([[f["x"], f["y"]] for f in fr])
                y = xy[:, 0] if abs(an["delta"]["dx_W"]) >= abs(an["delta"]["dy_H"]) else xy[:, 1]
                lo = an["from"][0] if abs(an["delta"]["dx_W"]) >= abs(an["delta"]["dy_H"]) else an["from"][1]
                hi = an["to"][0] if abs(an["delta"]["dx_W"]) >= abs(an["delta"]["dy_H"]) else an["to"][1]
            else:
                y = np.array([f[key] for f in fr]); lo, hi = an["from"], an["to"]
            prog = (y - lo) / (hi - lo) if hi != lo else y * 0
        else:
            cp = shot["camera_path"]
            t = np.array([p["t"] for p in cp])
            if an["prop"] == "position":
                xy = np.array([[p["cam_x"], p["cam_y"]] for p in cp])
                d = np.array([an["to"][0] - an["from"][0], an["to"][1] - an["from"][1]])
                prog = ((xy - np.array(an["from"])) @ d) / max(float(d @ d), 1e-12)
            elif an["prop"] == "scale":
                y = np.array([p["zoom"] for p in cp]); prog = (y - an["from"]) / (an["to"] - an["from"])
            else:
                y = -np.array([p["content_rot"] for p in cp]); prog = (y - an["from"]) / (an["to"] - an["from"])
        ax.plot(t, prog, ".", ms=3, color="#444")
        ez = an.get("easing", {})
        if "curve" in ez:
            tt = np.linspace(t.min(), t.max(), 300)
            ax.plot(tt, lib[ez["curve"]](np.clip((tt - ez["t0"]) / max(ez["dur"], 1e-3), 0, 1)),
                    color="#d33", lw=1.2)
        ax.set_title(f"{who} {an['prop']}: {ez.get('curve', ez.get('shape', '?'))}"
                     f" {ez.get('dur', an.get('visible_dur', 0)):.2f}s", fontsize=8)
        ax.set_ylim(-0.15, 1.25); ax.tick_params(labelsize=7); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=90)
    plt.close(fig)
    return True


# ---- the whole film -----------------------------------------------------------------------------
def track_film(path: str, out_dir: str, label: str, a) -> dict:
    np, cv2, optimize = deps()
    if np is None:
        raise RuntimeError("numpy + OpenCV are required")
    pr = probe(path)
    if not pr["w"]:
        raise RuntimeError(f"ffprobe could not read {path}")
    fps = a.fps or min(pr["fps"] or 30.0, 30.0)
    W = a.width
    H = int(round(pr["h"] * W / pr["w"] / 2) * 2)
    frames = decode(path, W, H, fps, "gray")
    n = len(frames)
    if n < 3:
        raise RuntimeError("fewer than 3 frames decoded")
    dur = n / fps
    cuts = fb.cut_times(path, a.cut_threshold)
    shots_t, merged = fb.shots_from_cuts(cuts, dur, a.min_shot)
    bounds = [(int(round(s * fps)), min(n, int(round(e * fps)))) for s, e in shots_t]
    bounds = [(s, e) for s, e in bounds if e - s >= 3]
    manual = []
    if a.items:
        for m in json.load(open(a.items)):
            i = min(n - 1, int(round(float(m["t"]) * fps)))
            bx = m["box"]
            manual.append({"i": i, "name": m.get("name"),
                           "bbox": (bx[0] * W, bx[1] * H, bx[2] * W, bx[3] * H)})
    stage = []
    need = set()
    for sn, (i0, i1) in enumerate(bounds, 1):
        shot, events, C = analyse_shot(np, cv2, optimize, frames, i0, i1, fps, a, sn, [])
        for e in events[: a.max_events]:
            need.add(min(i1 - 1, e["k1"] + 2)); need.add(max(i0, e["k0"] - 1))
        need.update(min(i1 - 1, i0 + int(round(f * (i1 - 1 - i0)))) for f in (0, .2, .4, .6, .8, 1))
        stage.append((shot, events, C, i0, i1))
    colours = decode(path, W, H, fps, "bgr24", keep=need)
    os.makedirs(out_dir, exist_ok=True)
    shots = []
    for shot, events, C, i0, i1 in stage:
        man = [m for m in manual if i0 <= m["i"] < i1]
        tracks = place_elements(np, cv2, frames, colours, shot, events, C, i0, i1, fps, a, man)
        els = []
        for tr in tracks:
            el = element_report(np, optimize, tr, C, fps, W, H, i0, i1, len(els) + 1)
            if el["animations"] or el["arrives"] or el["leaves"] or el["screen_locked"] or el["manual"]:
                els.append(el)
        for k, el in enumerate(els, 1):
            el["id"] = k
        shot["elements"] = els
        shot["stagger"] = stagger(els)
        if a.sheets:
            p = os.path.join(out_dir, f"OVERLAY-{label}-{shot['n']:02d}.png")
            shot["overlay_sheet"] = p if overlay_sheet(np, cv2, colours, shot, fps, p) else None
        if a.plots:
            p = os.path.join(out_dir, f"CURVES-{label}-{shot['n']:02d}.png")
            shot["curves_sheet"] = p if curves_sheet(np, shot, p) else None
        shots.append(shot)
    d = {"label": label, "file": os.path.basename(path), "duration": round(dur, 3), "fps": fps,
         "size": [W, H], "source": pr, "cuts": cuts, "cuts_merged": merged, "shots": shots,
         "_assumed": {"diff_floor": a.threshold, "min_area": MIN_AREA, "ecc_min_rho": ECC_MIN_RHO,
                      "min_change": MIN_CHANGE, "speed_rel": SPEED_REL},
         "_conventions": "x right, y down, fractions of the frame. Camera words are the CAMERA's move "
                         "(the picture moving left = the camera panned right). Element scale is relative "
                         "to its last tracked size; rotation positive = clockwise on screen."}
    with open(os.path.join(out_dir, f"TRACK-{label}.json"), "w") as fh:
        json.dump(d, fh, indent=1)
    with open(os.path.join(out_dir, f"TRACK-{label}-frames.csv"), "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["shot", "element", "name", "t", "x", "y", "scale", "rot_deg", "opacity", "rho"])
        for sh in shots:
            for el in sh["elements"]:
                for f in el["frames"]:
                    wr.writerow([sh["n"], el["id"], el["name"] or "", f["t"], f["x"], f["y"],
                                 f["scale"], f["rot"], f["opacity"], f["rho"]])
    with open(os.path.join(out_dir, f"TRACK-{label}.md"), "w") as fh:
        fh.write(render_md(d))
    return d


def _ease_cell(an: dict) -> str:
    ez = an.get("easing") or {}
    if "curve" not in ez:
        return f"{ez.get('shape', '?')} ({ez.get('note', '')})"
    s = f"{ez['shape']}{'' if ez.get('shape_sure') else '?'} · {ez['curve']} {ez['dur']:.2f}s"
    if ez.get("shape") == "spring" and ez.get("spring"):
        sp = ez["spring"]
        s += f" · spring ζ {sp['zeta']} ω {sp['omega']}"
    return s


def render_md(d: dict) -> str:
    L = [f"# Motion track — {d['label']}", "",
         f"`{d['file']}` · {d['duration']:.2f} s · analysed at {d['size'][0]}×{d['size'][1]}, "
         f"{d['fps']:.2f} fps · {len(d['shots'])} shots", "",
         "Conventions: " + d["_conventions"],
         "Easing: `shape · curve duration` — a `?` after the shape means a close alternative has a "
         "different shape. Overshoot is % of the move. Thresholds are [ASSUMED] (see the JSON).", ""]
    for sh in d["shots"]:
        cam = sh["camera"]
        L += [f"## Shot {sh['n']} · {sh['t0']:.2f}–{sh['t1']:.2f} s ({sh['dur']:.2f} s)", "",
              f"**Camera:** {cam['words']} · measured on {cam['measured_pairs']}/{cam['pairs']} frame pairs"
              + (f" · {cam['global_change_pairs']} pairs changed globally (transition/light/parallax)"
                 if cam["global_change_pairs"] else ""), ""]
        for an in cam["animations"]:
            if an["kind"] == "move":
                L.append(f"- {an['what']}: {an['t_start']:.2f}–{an['t_end']:.2f} s, {_ease_cell(an)}"
                         + (f", bezier {an['easing']['bezier']['css']}" if an.get('easing', {}).get('bezier') else ""))
        if cam["animations"]:
            L.append("")
        if not sh["elements"]:
            L += ["No element moved on its own." if not sh["events_detected"] else
                  f"{sh['events_detected']} changes detected; none could be tracked as an element "
                  "(read the strip).", ""]
            continue
        L += ["| # | element (box at ref, %) | what it does | start | visible dur | easing | bezier | overshoot | peak |",
              "|---|---|---|---|---|---|---|---|---|"]
        for el in sh["elements"]:
            b = el["box_at_ref"]
            who = (el["name"] or "") + f" {b[2] * 100:.0f}×{b[3] * 100:.0f} at ({b[0] * 100:.0f},{b[1] * 100:.0f})"
            if el.get("full_frame"):
                who += " · full-frame layer (a page or scene transition)"
            if el["screen_locked"]:
                L.append(f"| {el['id']} | {who} | screen-locked: stays put on screen while the camera moves | "
                         f"{el['tracked'][0]:.2f} | — | — | — | — | — |")
            if el["arrives"]:
                L.append(f"| {el['id']} | {who} | {el['arrives']['how']} | {el['arrives']['t']:.2f} | — | — | — | — | — |")
            for an in el["animations"]:
                if an["kind"] == "pulse":
                    L.append(f"| {el['id']} | {who} | {anim_words(an)} | {an['t_start']:.2f} | "
                             f"{an['t_end'] - an['t_start']:.2f} | — | — | — | — |")
                    continue
                bz = (an.get("easing") or {}).get("bezier", {}).get("css", "—")
                unit = "W/s" if an["prop"] == "position" else ("°/s" if an["prop"] == "rotation" else "/s")
                L.append(f"| {el['id']} | {who} | {anim_words(an)} | {an['start']:.2f} | "
                         f"{an.get('visible_dur', 0):.2f} | {_ease_cell(an)} | {bz} | "
                         f"{(str(an['overshoot_pct']) + '%') if an.get('overshoot_pct') else '—'} | "
                         f"{an.get('peak_speed', 0):.2f} {unit} |")
            if el["leaves"]:
                L.append(f"| {el['id']} | {who} | {el['leaves']['how']} | {el['leaves']['t']:.2f} | — | — | — | — | — |")
        st = sh["stagger"]
        if st.get("steps"):
            L += ["", f"**Stagger:** starts at {', '.join(f'{x:.2f}' for x in st['starts'])} s "
                      f"(order #{' → #'.join(str(i) for i in st['order'])}); steps "
                      f"{', '.join(f'{x:+.2f}' for x in st['steps'])} s"
                      + (f" · median {st['median_step']:.2f} s, {'regular' if st.get('regular') else 'irregular'}"
                         if "median_step" in st else "")]
        flags = [f"#{el['id']} rough cut-out (GrabCut found nothing; the change box was tracked)"
                 for el in sh["elements"] if el["rough_cutout"]]
        flags += [f"#{el['id']} weak track (median ρ {el['track_quality']})"
                  for el in sh["elements"] if el["track_quality"] < 0.8]
        flags += [f"#{el['id']} squash/stretch up to {el['squash_stretch_pct']}%"
                  for el in sh["elements"] if el["squash_stretch_pct"]]
        if flags:
            L += ["", "Notes: " + " · ".join(flags)]
        L.append("")
    return "\n".join(L)


# ---- selftest -----------------------------------------------------------------------------------
def _draw_card(np, cv2, img, cx, cy, w, h, s, rot, col, bar=(245, 245, 245)):
    def poly(pts):
        c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        P = []
        for x, y in pts:
            x, y = x * s, y * s
            P.append([cx + x * c - y * sn, cy + x * sn + y * c])
        return np.round(np.array(P) * 16).astype(np.int32)
    hw, hh = w / 2, h / 2
    cv2.fillConvexPoly(img, poly([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]), col, cv2.LINE_AA, 4)
    for x0, y0, x1, y1 in ((-0.38, -0.30, 0.30, -0.08), (-0.38, 0.08, 0.05, 0.30)):
        cv2.fillConvexPoly(img, poly([(x0 * w, y0 * h), (x1 * w, y0 * h), (x1 * w, y1 * h), (x0 * w, y1 * h)]),
                           bar, cv2.LINE_AA, 4)


def make_fixture(np, cv2, path: str, fps: int = 30) -> dict:
    """5 s, 640×360. Shot 1 (flat background): card A slides right 220 px easeOutCubic 0.30–1.10 s;
    card B cuts in at 0.70 s at 40 % size, then scales to full easeOutBack 0.80–1.50 s; card C
    rotates 40° linearly 1.40–2.20 s. Cut at 2.50 s. Shot 2 (textured background): the camera pans
    right 30 %W (the picture moves left 192 px) easeInOutCubic 2.90–4.30 s, under a screen-locked
    lower third."""
    lib = ease_library(np)
    W, H = 640, 360
    rng = np.random.default_rng(7)
    tex = cv2.GaussianBlur((rng.random((H + 40, int(W * 1.6))) * 255).astype(np.uint8), (0, 0), 2.5)
    tex = cv2.normalize(tex, None, 50, 200, cv2.NORM_MINMAX)
    tex = cv2.merge([tex, (tex * 0.9).astype(np.uint8), (tex * 0.8).astype(np.uint8)])

    def e(name, t, a, b):
        return float(lib[name](np.clip(np.array([(t - a) / (b - a)]), 0, 1))[0])
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                          "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "14",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(5 * fps):
        t = i / fps
        if t < 2.5:
            img = np.full((H, W, 3), 38, np.uint8)
            _draw_card(np, cv2, img, 110 + 220 * e("out_cubic", t, 0.3, 1.1), 70, 120, 60, 1, 0, (40, 140, 240))
            if t >= 0.7 - 1e-9:
                _draw_card(np, cv2, img, 500, 190, 90, 90, 0.4 + 0.6 * e("out_back", t, 0.8, 1.5), 0, (200, 110, 60))
            _draw_card(np, cv2, img, 190, 270, 110, 50, 1, 40 * e("linear", t, 1.4, 2.2), (80, 190, 80))
        else:
            ox = 192 * e("inout_cubic", t, 2.9, 4.3)
            M = np.float32([[1, 0, -40 - ox], [0, 1, -20]])
            img = cv2.warpAffine(tex, M, (W, H), flags=cv2.INTER_LINEAR)
            _draw_card(np, cv2, img, 120, 318, 170, 44, 1, 0, (235, 235, 235), bar=(40, 40, 40))
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    return {"cut": 2.5}


def selftest() -> int:
    np, cv2, optimize = deps()
    # pure functions — run anywhere numpy is
    if np is not None:
        lib = ease_library(np)
        assert len(lib) == 27, len(lib)
        x = np.linspace(0, 1, 101)
        for k, f in lib.items():
            y = f(x)
            assert abs(y[0]) < 2e-3 and abs(y[-1] - 1) < 2e-3, (k, y[0], y[-1])
        assert lib["out_back"](x).max() > 1.09 and lib["in_back"](x).min() < -0.09
        assert abs(bezier_y(np, np.array([0.5]), 0.25, 0.25, 0.75, 0.75)[0] - 0.5) < 1e-3
        assert shape_of("out_cubic") == "ease-out" and shape_of("inout_sine") == "ease-in-out"
        assert shape_of("out_back") == "overshoot" and shape_of("linear") == "linear"
        assert "pan/truck right" in camera_words(-0.30, 0, 1.0, 0, False)     # picture left = camera right
        assert "tilt/pedestal down" in camera_words(0, -0.2, 1.0, 0, False)   # picture up = camera down
        assert "push-in" in camera_words(0, 0, 1.2, 0, False) and camera_words(0, 0, 1, 0, False) == "static"
        st = stagger([{"starts": 0.3, "id": 1}, {"starts": 0.5, "id": 2}, {"starts": 0.7, "id": 3}])
        assert st["steps"] == [0.2, 0.2] and st["regular"], st
        if optimize is not None:
            # every curve family recovered from a clean sampled curve, with its start and end
            rng = np.random.default_rng(3)
            t = np.arange(0, 2.0, 1 / 30)
            for name in ("linear", "out_cubic", "inout_quad", "in_quart", "out_back", "out_elastic",
                         "out_bounce", "inout_sine", "out_expo"):
                y = lib[name](np.clip((t - 0.5) / 0.8, 0, 1)) + rng.normal(0, 0.004, t.size)
                ia = np.nonzero(y > 0.03)[0][0]; ib = np.nonzero(y > 0.97)[0][0]
                r = fit_easing(np, optimize, t, y, t[ia], t[ib])
                assert r["shape"] == shape_of(name) or (name == "out_elastic" and r["shape"] == "spring"), (name, r)
                if shape_of(name) not in ("elastic", "bounce"):
                    assert abs(r["t0"] - 0.5) < 0.06 and abs(r["t1"] - 1.3) < 0.08, (name, r)
            y = lib["out_cubic"](np.clip((t - 0.5) / 0.8, 0, 1))
            r = fit_easing(np, optimize, t, y, 0.5, 1.1)
            assert r["curve"] == "out_cubic" and r.get("bezier"), r
            assert all(abs(u - v) < 0.12 for u, v in zip(r["bezier"]["values"], BEZIER_OF["out_cubic"])), r["bezier"]
            ys = spring_curve(np, t - 0.4, 14.0, 0.35)
            r = fit_easing(np, optimize, t, ys, 0.45, 0.8)
            assert r["shape"] == "spring" and abs(r["spring"]["zeta"] - 0.35) < 0.05, r
    ran = False
    if np is not None and fb.have("ffmpeg", "ffprobe"):
        with tempfile.TemporaryDirectory() as td:
            v = os.path.join(td, "fixture.mp4")
            make_fixture(np, cv2, v)
            ns = argparse.Namespace(width=480, fps=30.0, threshold=DIFF_FLOOR, cut_threshold=10.0,
                                    min_shot=0.25, items=None, sheets=True, plots=optimize is not None,
                                    max_events=60)
            d = track_film(v, os.path.join(td, "out"), "selftest", ns)
            ran = True
            assert len(d["shots"]) == 2, [(s["t0"], s["t1"]) for s in d["shots"]]
            assert abs(d["shots"][1]["t0"] - 2.5) < 0.07, d["shots"][1]["t0"]
            s1, s2 = d["shots"]
            # shot 1: the camera did not move, and the tool must not claim it did
            assert abs(s1["camera"]["content_dx"]) < 0.01 and abs(s1["camera"]["scale"] - 1) < 0.01, s1["camera"]
            els = s1["elements"]

            def find(prop, kind="move"):
                return [(e, an) for e in els for an in e["animations"] if an["prop"] == prop and an["kind"] == kind]
            # A — the slide
            sl = [(e, an) for e, an in find("position") if an["delta"]["dx_W"] > 0.25]
            assert len(sl) == 1, [(e["id"], an["delta"]) for e, an in find("position")]
            e, an = sl[0]
            assert abs(an["delta"]["dx_W"] - 220 / 640) < 0.02, an["delta"]
            assert abs(an["delta"]["dy_H"]) < 0.01, an["delta"]
            if optimize is not None:
                ez = an["easing"]
                assert ez["shape"] == "ease-out", ez
                assert abs(ez["t0"] - 0.30) < 0.07 and abs(ez["dur"] - 0.80) < 0.12, ez
            # B — the pop and the overshoot
            sc = [(e, an) for e, an in find("scale") if an["to"] / max(an["from"], 1e-6) > 2.0]
            assert len(sc) == 1, [(e["id"], an.get("from"), an.get("to")) for e, an in find("scale")]
            e, an = sc[0]
            assert abs(an["from"] - 0.4) < 0.05, an
            assert an["overshoot_pct"] >= 6, an
            assert abs(an["t_start"] - 0.8) < 0.08, an
            assert e["arrives"] and abs(e["arrives"]["t"] - 0.7) < 0.05, e["arrives"]
            if optimize is not None:
                assert an["easing"]["shape"] in ("overshoot", "spring"), an["easing"]
            # C — the rotation
            ro = [(e, an) for e, an in find("rotation") if abs(an["delta"]) > 20]
            assert len(ro) == 1, [(e["id"], an.get("delta")) for e, an in find("rotation")]
            e, an = ro[0]
            assert abs(an["delta"] - 40) < 2.5, an
            if optimize is not None:
                assert an["easing"]["shape"] == "linear", an["easing"]
                assert abs(an["easing"]["t0"] - 1.4) < 0.07 and abs(an["easing"]["t1"] - 2.2) < 0.07, an["easing"]
            # stagger: A 0.30 → B 0.70 → C 1.40
            st = s1["stagger"]
            assert len(st["starts"]) >= 3, st
            assert abs(st["starts"][0] - 0.3) < 0.08 and abs(st["starts"][-1] - 1.4) < 0.08, st
            # shot 2: a pan to the right of 30 %W, eased in and out, and a screen-locked lower third
            c2 = s2["camera"]
            assert c2["measurable"], c2
            assert abs(c2["content_dx"] + 0.30) < 0.02 and abs(c2["content_dy"]) < 0.01, c2
            assert "pan/truck right" in c2["words"], c2["words"]
            pan = [an for an in c2["animations"] if an["prop"] == "position" and an["kind"] == "move"]
            assert len(pan) == 1, c2["animations"]
            if optimize is not None:
                assert pan[0]["easing"]["shape"] == "ease-in-out", pan[0]["easing"]
                assert abs(pan[0]["easing"]["t0"] - 2.9) < 0.08 and abs(pan[0]["easing"]["t1"] - 4.3) < 0.1, pan[0]["easing"]
            locked = [e for e in s2["elements"] if e["screen_locked"]]
            assert len(locked) == 1, [(e["id"], e["screen_locked"], e["box_at_ref"]) for e in s2["elements"]]
            assert not [an for an in locked[0]["animations"] if an["prop"] == "position" and an["kind"] == "move"], locked[0]["animations"]
            md = open(os.path.join(td, "out", "TRACK-selftest.md")).read()
            assert "screen-locked" in md and "Stagger" in md, md
            assert os.path.isfile(os.path.join(td, "out", "OVERLAY-selftest-01.png"))
            assert os.path.isfile(os.path.join(td, "out", "TRACK-selftest-frames.csv"))
    if np is None:
        print("selftest OK — ⛔ numpy/OpenCV absent: only the import ran; NOTHING was measured")
        return 0
    print("selftest OK — 27 easings, camera words from the camera's side"
          + (", curve, bezier and spring fits recovered" if optimize is not None else
             " (scipy absent — the curve fits did NOT run)")
          + ("; END TO END on a synthetic 2-shot film: the cut, a still camera on a flat background, "
             "a slide (distance, ease-out, start, duration), a cut-in + overshooting scale, a 40° linear "
             "rotation, the stagger, a 30 %W ease-in-out pan, a screen-locked lower third"
             if ran else "; ⛔ ffmpeg absent — the end-to-end leg did NOT run"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?")
    ap.add_argument("--out", default=None, help="output folder (default: beside the video, in track/)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--width", type=int, default=480, help="analysis width in px (default 480)")
    ap.add_argument("--fps", type=float, default=0.0, help="analysis rate (default: the film's, capped at 30)")
    ap.add_argument("--threshold", type=float, default=DIFF_FLOOR, help="residual floor in grey levels")
    ap.add_argument("--cut-threshold", type=float, default=10.0, help="scene-change threshold (film_breakdown)")
    ap.add_argument("--min-shot", type=float, default=0.25)
    ap.add_argument("--items", default=None, help="JSON list of boxes to track: [{name, t, box:[x,y,w,h]}]")
    ap.add_argument("--max-events", type=int, default=60, help="changes followed per shot")
    ap.add_argument("--no-sheets", dest="sheets", action="store_false")
    ap.add_argument("--no-plots", dest="plots", action="store_false")
    ap.add_argument("--json", action="store_true", help="print the JSON instead of the markdown")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.video:
        ap.print_help(); return 2
    if not os.path.isfile(a.video):
        print(f"error: {a.video} not found", file=sys.stderr); return 2
    if deps()[0] is None:
        print("error: numpy and OpenCV are required (pip install numpy opencv-python)", file=sys.stderr)
        return 3
    label = a.label or re.sub(r"[^A-Za-z0-9_-]+", "-", os.path.splitext(os.path.basename(a.video))[0])
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), "track")
    d = track_film(a.video, out, label, a)
    if a.json:
        print(json.dumps(d, indent=1)); return 0
    print(render_md(d))
    print(f"\nwrote: {out}/TRACK-{label}.md · .json · -frames.csv"
          + (" · OVERLAY-*.png" if a.sheets else "") + (" · CURVES-*.png" if a.plots else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
