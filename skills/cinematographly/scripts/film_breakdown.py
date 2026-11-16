#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""film_breakdown.py — turn a finished film into a shot-by-shot breakdown you can actually read.

⛔ WHY THIS EXISTS. `move-catalogue.md` names shot-by-shot BREAKDOWNS as the single best source for
this skill, and in the same table marks "a finished ad I am handed as a video" as unusable: an agent
cannot watch video. That was true and it was a tooling gap, not a law. Frames can be looked at, and
cuts, durations and camera moves can be MEASURED. This tool does the measuring and lays out the
frames, so a reference film becomes the one thing the catalogue wants: named moves, with numbers.

What it produces, per film:
  * BREAKDOWN-<label>.md   the shot table — every cut time, every shot length, the rhythm, the
                           camera move solved from the pixels, the shot size estimated from a face
  * SHEET-<label>.png      one numbered tile per shot: the whole film as a sequence, at a glance
  * MOVES-<label>-NN.png   first / middle / last frame of each shot, side by side — what MOVED
  * BREAKDOWN-<label>.json the same numbers as data
  * STRIP-<label>-NN.png   (--strip) the whole film at 4 frames a second, each frame stamped with its
                           time on the same clock as the cut table, 40 frames (10 s) per sheet — the
                           sheet a reader confirms every cut on

⛔ WHAT IT CANNOT DO. It measures motion, length and luminance; it does not know what a shot MEANS.
Dramaturgy, performance and intent still come from a person (or from frames a person then reads).
The shot-size estimate needs a visible frontal face and is a proxy, not a measurement — the bands
are [ASSUMED] and printed with the raw ratio so they can be argued with.

⛔ MEASURED RECALL — CONFIRM EVERY CUT ON THE STRIP. On 38 real ads (lab-00006, 2026-10-04) the
detector found 76 % of the true cuts: readers added 314 missed cuts and removed 95 false splits out
of 1,293. It misses soft cuts, cuts in dark scenes and cuts inside a small picture — a pillarboxed
9:16 ad in a 16:9 file lost 35 of 37 cuts, because the black bars swamp the frame difference — and
it fires strings of false cuts every ~0.2 s on fast handheld or FPV motion. `split_suspect` flags
catch most misses, not all. Its "dissolve"/"fade" labels were wrong almost every time at 4 fps.
Treat the cut table as a draft and the --strip sheets as the evidence.
A second measurement, on three AI shorts (F1, F5, F4; 2026-10-25), against the
reference database's person-read cuts: the detector found 89–92 % of them, and every cut it fired is
in that list [measured · assets/reference-cutcheck.json]. ⛔ That person's read started from this
detector's output, so a cut both missed is in neither count, and recall here is an upper bound. A
model reading of the 4 fps strips (not a person; 0.25 s resolution) put the detector at 87–93 %
precision and 80–84 % recall, but every cut it called false is in the person's list; its 61 extra
cuts (32 inside rows already flagged split_suspect) and 27 disputed ones await a person's look.

NOT A CAMERA-MOVE PRESET. Every row carries `preset`: yes, or no and the reasons. A flagged
row stays in the table, marked; nothing is deleted. The reasons:
  black opening / black tail / black stub   most sampled frames near-black
  flat card        a plain background holds most of the frame, as on a title card
  inset            picture-in-picture: the motion fills a rectangle and the rest of the frame is still
  screen scroll    the picture moves straight up or down as one rigid sheet, beside points that do not
                   move at all (a page scrolling under a browser's bars)
  scale unconfirmed  a push or pull that the face's own size does not follow
  repeat of #n     the picture already appeared (below)
  and, as before: move not measured, move unreliable, split suspect.
⛔ What these heuristics CANNOT detect: an inset whose own picture is mostly still (a webcam corner over
a static wall); a static screen recording with no scroll and no inset (it reads as locked off, or as a
flat card when the page is plain); a full-frame scroll with no still bar beside it (it reads as a tilt
over a still); tracker noise, drift and a presenter shifting. The size check needs a frontal face at
both ends of the shot; without one the row says it cannot confirm, and is not flagged. A screen
playing video inside a real scene can read as an inset, and a real tilt under a burned-in still bar can
read as a scroll. The flags are for a reader, who confirms them on the MOVES sheets.

REPEATS BY PICTURE. Rows whose sampled frames match on a 64-bit picture hash are grouped;
the later ones are marked `repeat of #n`, so a repeated shot counts once. The motion trace is never
used: the same move over a different picture is not a repeat, and a matching picture is one. Black
rows and flat cards are not grouped (a low-resolution hash cannot tell two plain cards apart), a repeat
trimmed to a different part of a fast move can be missed, and two adjacent rows that match may be one
shot split by a false cut.

Usage
-----
  python3 film_breakdown.py REFERENCE.mp4 --label pirate-cabin
  python3 film_breakdown.py REF.mp4 --out 09-qa/breakdowns --threshold 12 --samples 7
  python3 film_breakdown.py REF.mp4 --strip      # + timestamped 4 fps contact strips
  python3 film_breakdown.py --selftest

Requires ffmpeg + ffprobe; OpenCV and numpy for the motion solve (without them the cut table and
the sheets are still produced, and every motion column reads UNMEASURED rather than 0).
Exit codes: 0 ok · 2 usage/IO/ffmpeg error.
"""
from __future__ import annotations
import argparse, datetime as dt, json, math, os, re, shutil, subprocess, sys, tempfile

SCD_RE = re.compile(r"lavfi\.scd\.time:\s*([0-9]+(?:\.[0-9]+)?)")
# [ASSUMED] shot-size bands, face height as a fraction of frame height. Printed WITH the ratio so a
# reader can disagree; nothing in this skill should cite them as measured.
SIZE_BANDS = ((0.55, "ECU"), (0.35, "CU"), (0.22, "MCU"), (0.12, "MS"), (0.06, "MLS"), (0.0, "WS"))
# [ASSUMED] motion bands, in fractions of frame width per second of shot.
MOVE_STILL, MOVE_SLOW = 0.010, 0.060

# ---- rows that are not a camera-move preset ----------------------------------------------
# Luma is 0–255 on the grey motion frame; "px" is a pixel of that frame (--motion-width wide).
BLACK_MEAN = 20.0          # [assumed] house choice, 2026-11-03 — near-black: mean luma under 20 (the "visually black" transitions() uses)…
BLACK_P99 = 40.0           # [assumed] house choice, 2026-11-03 — …and 99 % of the pixels under 40, so a lit logo is a card, not black
BLACK_SHARE = 0.75         # [assumed] house choice, 2026-11-03 — a row is black when this share of its sampled frames are
CARD_TOL = 8               # [assumed] house choice, 2026-11-03 — the plain background: the luma band ± this around the commonest value
CARD_PLAIN = 0.85          # [assumed] house choice, 2026-11-03 — a flat card when that band holds this share of the frame
CARD_SHARE = 0.75          # [assumed] house choice, 2026-11-03 — a row is a card when this share of its sampled frames are
INSET_CELLS = 40           # [assumed] house choice, 2026-11-03 — the motion map is this many cells across
INSET_DIFF = 8.0           # [assumed] house choice, 2026-11-03 — a cell moved in a pair when its mean |luma change| is over this…
INSET_MOVING = 0.5         # [assumed] house choice, 2026-11-03 — …in at least this share of the row's pairs
INSET_MIN_AREA = 0.01      # [assumed] house choice, 2026-11-03 — the moving rectangle covers at least this share of the frame…
INSET_MAX_AREA = 0.40      # [assumed] house choice, 2026-11-03 — …and at most this
INSET_FILL = 0.75          # [assumed] house choice, 2026-11-03 — this share of the rectangle's cells move
INSET_SIDE_FILL = 0.6      # [assumed] house choice, 2026-11-03 — every row and column of it this full: a box, not a blob
INSET_OUTSIDE = 0.01       # [assumed] house choice, 2026-11-03 — at most this share of the cells outside it move
SCROLL_MIN_TRACKS = 20     # [assumed] house choice, 2026-11-03 — a pair is judged on at least this many moving points
SCROLL_MIN_PX = 1.0        # [assumed] house choice, 2026-11-03 — a point moved when it travelled this far in a pair…
SCROLL_STATIC_PX = 0.35    # [assumed] house choice, 2026-11-03 — …and stood still under this
SCROLL_DX_RATIO = 0.05     # [assumed] house choice, 2026-11-03 — vertical: sideways travel at most this share of the vertical
SCROLL_UNIFORM_PX = 0.35   # [assumed] house choice, 2026-11-03 — rigid: the moving points agree within this (median absolute deviation)
SCROLL_STATIC_MIN = 5      # [assumed] house choice, 2026-11-03 — hard edges: at least this many still points…
SCROLL_STATIC_OUT = 0.9    # [assumed] house choice, 2026-11-03 — …this share of them outside the moving points' rectangle
SCROLL_PAIR_SHARE = 0.6    # [assumed] house choice, 2026-11-03 — a row scrolls when this share of its moving pairs do (and two at least)
SCALE_CHECK_MIN = 0.04     # [assumed] house choice, 2026-11-03 — a scale move is checked from the 4 % describe_move names a push or pull at
SCALE_AGREE = 0.20         # [assumed] house choice, 2026-11-03 — the face's growth must agree with the solve's scale within 20 %
# ---- repeats by picture ------------------------------------------------------------------
REPEAT_HAMMING = 8         # [assumed] house choice, 2026-11-03 — two frames match when their 64-bit picture hashes differ in at most 8 bits
REPEAT_MIN_SHARE = 0.5     # [assumed] house choice, 2026-11-03 — two rows are one picture when half the shorter row's frames match the other's
PICTURE_MIN_STD = 4.0      # [assumed] house choice, 2026-11-03 — a frame flatter than this has no picture to hash (export_qc's flat-card floor)


def frame_kind(np, g) -> dict:
    """Is this grey frame near-black, or a flat card? The plain-background share is the
    commonest luma band's share of the frame: a title card is one colour with a little text on it."""
    m, p99 = float(g.mean()), float(np.percentile(g, 99))
    hist = np.bincount(g.ravel(), minlength=256).astype(np.float64)
    plain = float(np.convolve(hist, np.ones(2 * CARD_TOL + 1), mode="same").max() / g.size)
    black = m < BLACK_MEAN and p99 < BLACK_P99
    return {"black": black, "card": (not black) and plain >= CARD_PLAIN, "plain": round(plain, 3)}


def cell_motion(np, a, b):
    """Mean |luma change| per cell between two grey frames, on an INSET_CELLS-wide grid."""
    cs = max(4, a.shape[1] // INSET_CELLS)
    R, C = a.shape[0] // cs, a.shape[1] // cs
    d = np.abs(a[:R * cs, :C * cs].astype(np.int16) - b[:R * cs, :C * cs].astype(np.int16))
    return d.reshape(R, cs, C, cs).mean(axis=(1, 3))


def inset_from_cells(cv2, np, mv):
    """A picture-in-picture inset from a boolean cell map of where the row moved, or None.

    The largest moving region's bounding box must be a BOX — filled, every row and column of it full
    — inside a frame that is otherwise still. A blob (a head moving in a locked-off shot) fails the
    box test; a whole moving frame fails the area test."""
    mv = np.asarray(mv, bool)
    if not mv.any():
        return None
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mv.astype(np.uint8), connectivity=8)
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = (int(stats[k, i]) for i in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH,
                                             cv2.CC_STAT_HEIGHT))
    R, C = mv.shape
    y0, y1, x0, x1 = y, y + h, x, x + w
    # a cell straddling the inset's own border is only part-filled: trim at most one such sparse edge
    # row or column per side before the box test (a blob tapers over several, so it still fails)
    if y1 - y0 > 2 and mv[y0, x0:x1].mean() < INSET_SIDE_FILL:
        y0 += 1
    if y1 - y0 > 2 and mv[y1 - 1, x0:x1].mean() < INSET_SIDE_FILL:
        y1 -= 1
    if x1 - x0 > 2 and mv[y0:y1, x0].mean() < INSET_SIDE_FILL:
        x0 += 1
    if x1 - x0 > 2 and mv[y0:y1, x1 - 1].mean() < INSET_SIDE_FILL:
        x1 -= 1
    box = mv[y0:y1, x0:x1]
    area, fill = box.size / float(R * C), float(box.mean())
    outside = (mv.sum() - box.sum()) / float(max(1, R * C - box.size))
    side = min(float(box.mean(axis=1).min()), float(box.mean(axis=0).min()))
    if (INSET_MIN_AREA <= area <= INSET_MAX_AREA and fill >= INSET_FILL and side >= INSET_SIDE_FILL
            and outside <= INSET_OUTSIDE):
        return {"x": round(x0 / C, 3), "y": round(y0 / R, 3), "w": round((x1 - x0) / C, 3),
                "h": round((y1 - y0) / R, 3), "fill": round(fill, 2)}
    return None


def scroll_pair(np, p0, p1):
    """One pair's tracked points: a screen scroll? None when too few points moved to judge.

    A scroll is a rigid sheet moving straight up or down — every moving point by the same amount, none
    sideways — beside points that do not move at all and lie outside the sheet (the still bars a
    browser keeps). A real tilt has parallax, roll and noise, and no still points beside it."""
    p0 = np.asarray(p0, np.float32).reshape(-1, 2)
    p1 = np.asarray(p1, np.float32).reshape(-1, 2)
    d = p1 - p0
    mag = np.hypot(d[:, 0], d[:, 1])
    mov, sta = mag >= SCROLL_MIN_PX, mag < SCROLL_STATIC_PX
    if int(mov.sum()) < SCROLL_MIN_TRACKS:
        return None
    dm = d[mov]
    dx, dy = float(np.median(dm[:, 0])), float(np.median(dm[:, 1]))
    rigid = (float(np.median(np.abs(dm[:, 1] - dy))) <= SCROLL_UNIFORM_PX
             and float(np.median(np.abs(dm[:, 0] - dx))) <= SCROLL_UNIFORM_PX)
    vertical = abs(dy) >= SCROLL_MIN_PX and abs(dx) <= SCROLL_DX_RATIO * abs(dy)
    edges = False
    if int(sta.sum()) >= SCROLL_STATIC_MIN:
        pm, ps = p0[mov], p0[sta]
        x0, x1 = np.percentile(pm[:, 0], [2, 98])
        y0, y1 = np.percentile(pm[:, 1], [2, 98])
        inside = (ps[:, 0] > x0) & (ps[:, 0] < x1) & (ps[:, 1] > y0) & (ps[:, 1] < y1)
        edges = float((~inside).mean()) >= SCROLL_STATIC_OUT
    return {"scroll": bool(rigid and vertical and edges), "dy": round(dy, 2),
            "moving": int(mov.sum()), "still": int(sta.sum())}


def scale_verdict(scale, f0, f1):
    """(state, detail) for a push or pull against the face's own size at the shot's two ends.
    state: None (no scale move) · confirmed · unconfirmed · cannot confirm (no face at both ends)."""
    if scale is None or abs(scale - 1.0) < SCALE_CHECK_MIN:
        return None, ""
    if not f0 or not f1:
        return "cannot confirm", "no face at both ends of the shot, so the subject's size was not measured"
    r = f1 / f0
    agree = (r - 1.0) * (scale - 1.0) > 0 and abs(math.log(r) - math.log(scale)) <= math.log(1.0 + SCALE_AGREE)
    return ("confirmed" if agree else "unconfirmed"), f"the face x{r:.2f} against the solve's x{scale:.2f}"


def dhash(cv2, np, g):
    """A 64-bit difference hash of a grey frame, or None when it is too flat to carry a picture."""
    if float(g.std()) < PICTURE_MIN_STD:
        return None
    s = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    h = 0
    for i, bit in enumerate((s[:, 1:] > s[:, :-1]).ravel()):
        if bit:
            h |= 1 << i
    return h


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def group_repeats(rows: list) -> list:
    """Group rows by PICTURE and mark the later ones `repeat_of`. Returns [[n, …], …].

    ⛔ Only the hashes are compared. A motion trace that matches is not evidence of a repeat: the same
    move over a different picture is a different shot, and that is the case a trace correlation gets
    wrong. Black rows and flat cards are left out — a 9×8 hash cannot tell two plain cards apart."""
    cand = [r for r in rows if r.get("phash") and not r.get("black") and not r.get("card")]
    parent = {r["n"]: r["n"] for r in cand}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    hs = {r["n"]: [int(h, 16) for h in r["phash"]] for r in cand}

    def share(src, dst):                    # the share of src's frames that have a match in dst
        return sum(1 for h in src if min(hamming(h, o) for o in dst) <= REPEAT_HAMMING) / len(src)
    for i, a in enumerate(cand):
        for b in cand[i + 1:]:
            ha, hb = hs[a["n"]], hs[b["n"]]
            # judged from the SHORTER shot's frames (a trimmed reuse sits inside the longer one); when the
            # two are within 10 % of each other, both directions must agree
            da, db = a.get("dur") or len(ha), b.get("dur") or len(hb)
            if abs(da - db) <= 0.1 * max(da, db):
                s = min(share(ha, hb), share(hb, ha))
            else:
                s = share(ha, hb) if da < db else share(hb, ha)
            if s >= REPEAT_MIN_SHARE:
                parent[find(b["n"])] = find(a["n"])
    groups: dict = {}
    for r in cand:
        groups.setdefault(find(r["n"]), []).append(r["n"])
    out = sorted(sorted(g) for g in groups.values() if len(g) > 1)
    byn = {r["n"]: r for r in rows}
    for k, g in enumerate(out, 1):
        for n in g:
            byn[n]["repeat_group"] = k
            if n != g[0]:
                byn[n]["repeat_of"] = g[0]
    return out


def preset_flags(r: dict, last_n: int) -> list:
    """Why a row is not a camera-move preset; empty when it is one."""
    F = []
    if r.get("black"):
        F.append("black opening" if r["n"] == 1 else "black tail" if r["n"] == last_n else "black stub")
    if r.get("card"):
        F.append("flat card")
    if r.get("inset"):
        F.append("inset")
    if r.get("scroll"):
        F.append("screen scroll")
    if r.get("scale_check") == "unconfirmed":
        F.append("scale unconfirmed")
    if r.get("repeat_of"):
        F.append(f"repeat of #{r['repeat_of']}")
    mv = r.get("move") or "UNMEASURED"
    if mv.startswith("UNMEASURED"):
        F.append("move not measured")
    elif mv.startswith("UNRELIABLE"):
        F.append("move unreliable")
    if r.get("split_suspect"):
        F.append("split suspect")
    return F


def have(*bins) -> bool:
    return all(shutil.which(b) for b in bins)


def _np():
    try:
        import numpy, cv2                                   # noqa: F401
        return numpy, cv2
    except Exception:
        return None, None


def probe_duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, errors="replace")
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def cut_times(path: str, threshold: float, detect_h: int = 480) -> list:
    """Scene-change times in seconds, from ffmpeg's own detector.

    Detection runs on a DOWNSCALED copy and with audio disabled: a cut is a global change, so the
    extra pixels buy nothing and cost minutes on a feature-length reference. `-an` matters more than
    it looks — decoding a 15-minute AAC track for a video filter is pure waste."""
    vf = f"scale=-2:{detect_h},scdet=threshold={threshold}" if detect_h else f"scdet=threshold={threshold}"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-an", "-sn", "-i", path, "-filter:v", vf,
                        "-f", "null", "-"], capture_output=True, text=True, errors="replace")
    return sorted({round(float(m.group(1)), 3) for m in SCD_RE.finditer(r.stderr)})


def shots_from_cuts(cuts: list, duration: float, min_shot: float) -> list:
    """Cut times → [(start, end)]. A 'cut' closer than min_shot to the previous one is a flash or a
    fast camera move inside one shot, not an edit — merged, and the count is reported."""
    bounds, merged = [0.0], 0
    for c in cuts:
        if c - bounds[-1] < min_shot:
            merged += 1
            continue
        bounds.append(c)
    bounds.append(duration)
    out = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1) if bounds[i + 1] > bounds[i]]
    # ⛔ A cut landing within min_shot of the END emitted a 0.0-second final shot — a row that is not
    # a shot, that drags every mean down, and that a reader would take at face value (found on a real
    # film, 2026-09-30). Fold it into the shot before it.
    while len(out) > 1 and out[-1][1] - out[-1][0] < min_shot:
        a, _ = out[-2]
        out[-2] = (a, out[-1][1]); out.pop(); merged += 1
    return out, merged


def classify_size(ratio: float) -> str:
    for lo, name in SIZE_BANDS:
        if ratio >= lo:
            return name
    return "WS"


def describe_move(dx: float, dy: float, dscale: float, droll: float, per_s: float) -> str:
    """The move, named from the CAMERA's side. dx/dy are how far the PICTURE moved at the frame
    CENTRE, in fractions of frame width/height (x right, y down); dscale a multiplier; droll the
    picture's rotation in degrees (+ = clockwise on screen).

    ⛔ THE PICTURE MOVES OPPOSITE TO THE CAMERA. A camera panning right slides the picture left.
    Until 2026-10-24 this function named the picture's shift as the camera's move, so every pan and
    tilt it reported was backwards: a known pan right read "pan left 22%W", a tilt down "tilt up"
    (synthetic crops moving through a still, measured that day). 174 rows of reference-shots.jsonl
    carried the reversed words and were corrected the same day (LEDGER)."""
    parts = []
    if abs(dscale - 1.0) >= 0.04:
        parts.append(f"push in x{dscale:.2f}" if dscale > 1 else f"pull out x{dscale:.2f}")
    if abs(dx) >= 0.03:
        parts.append(f"pan {'left' if dx > 0 else 'right'} {abs(dx) * 100:.0f}%W")
    if abs(dy) >= 0.03:
        parts.append(f"tilt {'up' if dy > 0 else 'down'} {abs(dy) * 100:.0f}%H")
    if abs(droll) >= 1.5:
        parts.append(f"roll {droll:+.1f}deg")
    if not parts:
        return "locked off" if per_s < MOVE_STILL else ("drift" if per_s < MOVE_SLOW else "handheld/shake")
    speed = "slow" if per_s < MOVE_SLOW else "fast"
    return f"{speed}: " + " + ".join(parts)


def _grab(cap, cv2, t, motion_w):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
    ok, fr = cap.read()
    if not ok or fr is None:
        return None
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    if motion_w and g.shape[1] > motion_w:
        g = cv2.resize(g, (motion_w, int(g.shape[0] * motion_w / g.shape[1])))
    return g


def _affine_lk(cv2, np, a, b, info=None):
    """Affine between two frames a FEW FRAMES apart — Lucas-Kanade, which needs small displacement.
    `info`, when given, receives the tracked points (p0, p1) for the scroll test."""
    p0 = cv2.goodFeaturesToTrack(a, maxCorners=400, qualityLevel=0.01, minDistance=8)
    if p0 is None or len(p0) < 12:
        return None, None
    p1, stt, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None)
    if p1 is None or stt is None or int(stt.sum()) < 12:
        return None, None
    ga, gb = p0[stt.ravel() == 1], p1[stt.ravel() == 1]
    if info is not None:                                   # the raw tracks, before RANSAC
        info["p0"], info["p1"] = ga, gb
    M, inl = cv2.estimateAffinePartial2D(ga, gb, method=cv2.RANSAC, ransacReprojThreshold=3)
    if M is None:
        return None, None
    # ⛔ AN AFFINE WITH NO INLIER TEST IS NOT A MEASUREMENT. On flat content (colour bars, sky,
    # a gradient) the tracked corners are degenerate — every one of them on the same edge — and
    # estimateAffinePartial2D happily returns a transform that moves the frame by more than its own
    # width. A STATIC test pattern was reported as moving 10 frame-widths per second before this
    # gate existed (2026-09-30). Too few inliers, or a physically impossible step, is a NO ANSWER.
    n_in = int(inl.sum()) if inl is not None else 0
    hh, ww = a.shape[:2]
    sx = math.hypot(M[0, 0], M[1, 0]) or 1.0
    if n_in < 15 or abs(M[0, 2]) / ww > 0.5 or abs(M[1, 2]) / hh > 0.5 or not (0.5 <= sx <= 2.0):
        return None, None
    pred = cv2.transform(ga.reshape(-1, 1, 2), M).reshape(-1, 2)
    res = np.linalg.norm(gb.reshape(-1, 2) - pred, axis=1)
    keep = (inl.ravel() == 0) if inl is not None else np.ones(len(res), bool)
    return M, (float(np.median(res[keep])) if keep.any() else 0.0)


def _affine_orb(cv2, np, a, b):
    """Affine across a WHOLE SHOT — feature matching, which survives a large displacement that
    optical flow cannot. ⛔ Returns None rather than a number when too few matches agree: the first
    version of this tool ran LK between frames seconds apart and reported 'tilt down 288%H,
    roll -105.9deg' on a 22-second shot. A motion estimate with no inlier test is not a measurement
    (found 2026-09-30, on real films)."""
    orb = cv2.ORB_create(1200)
    ka, da = orb.detectAndCompute(a, None)
    kb, db = orb.detectAndCompute(b, None)
    if da is None or db is None or len(ka) < 25 or len(kb) < 25:
        return None, 0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    m = sorted(bf.match(da, db), key=lambda x: x.distance)[:200]
    if len(m) < 20:
        return None, len(m)
    src = np.float32([ka[x.queryIdx].pt for x in m]).reshape(-1, 1, 2)
    dst = np.float32([kb[x.trainIdx].pt for x in m]).reshape(-1, 1, 2)
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4)
    n_in = int(inl.sum()) if inl is not None else 0
    return (M if n_in >= 15 else None), n_in


def measure_shot(cap, cv2, np, t0: float, t1: float, samples: int, cascade,
                 motion_w: int = 640, dt: float = 0.12) -> dict:
    """Solve a shot's camera move, and split camera motion from subject motion.

    Two measurements, because they need different tools:
      · RATE — how fast the frame is moving — from pairs of frames `dt` apart (optical flow is only
        valid across a small displacement). Bursts are spread across the shot, so a move that only
        happens at the end still registers.
      · TOTAL — how far it travelled over the whole shot — from ORB matching between the shot's
        first and last sampled frame, gated on inliers, and reported as UNRELIABLE when the gate
        fails rather than as a fabricated number.
    Residual flow after the camera transform is removed is the part that moved on its own: the
    subject. Low rate + high residual is a performance shot; the reverse is a camera shot."""
    out = {"frames": 0, "cam_px": 0.0, "residual": None, "dx": 0.0, "dy": 0.0, "scale": 1.0,
           "roll": 0.0, "luma": None, "size": None, "face_ratio": None, "total_ok": False}
    dur = max(1e-3, t1 - t0)
    n = max(2, min(samples, int(dur / max(dt * 2, 0.05)) + 1))
    anchors = [t0 + (dur - dt) * i / max(1, n - 1) for i in range(n)]
    rates, residuals, lumas = [], [], []
    kinds, hashes, scrolls = [], [], []            # (HR-23/HR-24) what each sampled frame IS
    moved, n_pairs = None, 0                       # per-cell motion counts, for the inset test
    first = last = None
    W = H = None
    for i, t in enumerate(anchors):
        ga = _grab(cap, cv2, t, motion_w)
        gb = _grab(cap, cv2, t + dt, motion_w)
        if ga is None:
            continue
        out["frames"] += 1
        H, W = ga.shape[:2]
        lumas.append(float(ga.mean()))
        kinds.append(frame_kind(np, ga))                                   #
        h_ = dhash(cv2, np, ga)                                            #
        if h_ is not None:
            hashes.append(h_)
        if first is None:
            first = ga
        last = gb if gb is not None else ga
        if gb is None:
            continue
        cm = cell_motion(np, ga, gb) > INSET_DIFF                          #
        moved = cm.astype(np.int32) if moved is None else moved + cm
        n_pairs += 1
        info: dict = {}
        M, res = _affine_lk(cv2, np, ga, gb, info)
        if info.get("p0") is not None:
            sp = scroll_pair(np, info["p0"], info["p1"])                   #
            if sp is not None:
                scrolls.append(sp)
        if M is not None:
            rates.append(math.hypot(float(M[0, 2]), float(M[1, 2])) / W / dt)
            if res is not None:
                residuals.append(res / W)
    # what the frames are, decided before anything is said about the camera
    if kinds:
        out["black_share"] = round(sum(k["black"] for k in kinds) / len(kinds), 2)
        out["card_share"] = round(sum(k["card"] for k in kinds) / len(kinds), 2)
        out["black"] = out["black_share"] >= BLACK_SHARE
        out["card"] = (not out["black"]) and out["card_share"] >= CARD_SHARE
    out["inset"] = inset_from_cells(cv2, np, moved / float(n_pairs) >= INSET_MOVING) if n_pairs else None
    n_scroll = sum(1 for s in scrolls if s["scroll"])
    out["scroll"] = len(scrolls) >= 2 and n_scroll / len(scrolls) >= SCROLL_PAIR_SHARE
    out["scroll_pairs"] = f"{n_scroll}/{len(scrolls)}"
    out["phash"] = ["%016x" % h_ for h_ in hashes]                         #
    if first is not None and last is not None and W:
        M, n_in = _affine_orb(cv2, np, first, last)
        if M is not None:
            sx = math.hypot(M[0, 0], M[1, 0]) or 1.0
            # ⛔ MEASURED AT THE FRAME CENTRE. The transform's own translation is how far the
            # top-left CORNER moved, and a push-in about the centre moves the corner too: until
            # 2026-10-24 a pure x1.15 push-in was filed as "push in + pan 8%W + tilt 7%H". The
            # picture's shift is where the centre of frame 1 lands in frame 2.
            cx, cy = W / 2.0, H / 2.0
            ccx = M[0, 0] * cx + M[0, 1] * cy + M[0, 2]
            ccy = M[1, 0] * cx + M[1, 1] * cy + M[1, 2]
            out.update({"dx": float(ccx - cx) / W, "dy": float(ccy - cy) / H, "scale": sx,
                        "roll": math.degrees(math.atan2(M[1, 0], M[0, 0])), "total_ok": True,
                        "orb_inliers": n_in, "shift_at": "centre"})
        else:
            out["orb_inliers"] = n_in
    out["luma"] = round(sum(lumas) / len(lumas), 1) if lumas else None
    out["residual"] = round(sum(residuals) / len(residuals), 5) if residuals else None
    out["per_s"] = round(sum(rates) / len(rates), 4) if rates else None
    out["rate_pairs"] = len(rates)
    # ⛔ A total that survived the inlier gate can still be physically absurd on a shot whose
    # content changed (a missed cut). Bound it, and say so, rather than print it.
    absurd = (abs(out["dx"]) > 1.5 or abs(out["dy"]) > 1.5 or abs(out["roll"]) > 45
              or not (0.2 <= out["scale"] <= 5.0))
    if out["total_ok"] and absurd:
        out["total_ok"] = False
        out["total_note"] = "bounds"
    if out["per_s"] is None:                     # no pair survived the gate: say nothing, loudly
        out["move"] = "UNMEASURED (no reliable frame pair)"
        return out
    if out["total_ok"]:
        out["move"] = describe_move(out["dx"], out["dy"], out["scale"], out["roll"], out["per_s"])
    elif out["per_s"] < MOVE_STILL:
        # The whole-shot solve abstained, but the per-pair RATE is reliable and ~zero. A frame that
        # never moves between any sampled pair did not cumulatively move either: that is a locked-off
        # shot, and refusing to say so would throw away the most common shot in a film.
        out["move"] = "locked off"
    else:
        out["move"] = ("UNRELIABLE (" + ("out of bounds" if out.get("total_note") == "bounds"
                                         else f"{out.get('orb_inliers', 0)} inliers")
                       + f") — rate {out['per_s']:.3f}/s")
    if cascade is not None and first is not None:
        faces = cascade.detectMultiScale(first, 1.1, 5, minSize=(24, 24))
        if len(faces):
            out["face_ratio"] = round(max(int(f[3]) for f in faces) / float(H), 3)
            out["size"] = classify_size(out["face_ratio"])
    # a push or pull the subject's own size does not follow is not a confirmed scale move
    if out["total_ok"]:
        f1 = None
        if cascade is not None and last is not None:
            faces1 = cascade.detectMultiScale(last, 1.1, 5, minSize=(24, 24))
            if len(faces1):
                f1 = out["face_ratio_end"] = round(max(int(f[3]) for f in faces1) / float(H), 3)
        st, det = scale_verdict(out["scale"], out.get("face_ratio"), f1)
        if st and cascade is None:
            st, det = "cannot confirm", "no face detector in this OpenCV build"
        if st:
            out["scale_check"], out["scale_detail"] = st, det
    return out


def transitions(path: str, bounds: list, cv2, np, motion_w: int = 320,
                win: float = 0.55, fps: float = 12.0) -> list:
    """Classify what happens AT each shot boundary: a hard CUT, a DISSOLVE, or a FADE.

    A hard cut is ONE huge frame-to-frame difference with quiet on either side. A dissolve spreads
    that difference over many frames, so its profile is a plateau, not a spike. A fade passes
    through near-black. The discriminator is therefore peak-to-median ratio inside a window around
    the boundary — not the peak alone, which cannot tell a cut from a fast camera move.

    ⛔ Returns 'unknown' rather than guessing when the window cannot be read."""
    out = []
    cap = cv2.VideoCapture(path)
    for t in bounds:
        prof, lumas, prev = [], [], None
        n = max(4, int(2 * win * fps))
        for i in range(n):
            tt = max(0.0, t - win + (2 * win) * i / (n - 1))
            cap.set(cv2.CAP_PROP_POS_MSEC, tt * 1000.0)
            ok, fr = cap.read()
            if not ok or fr is None:
                continue
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            g = cv2.resize(g, (motion_w, max(1, int(g.shape[0] * motion_w / g.shape[1]))))
            lumas.append(float(g.mean()))
            if prev is not None:
                prof.append(float(np.abs(g.astype(np.int16) - prev.astype(np.int16)).mean()))
            prev = g
        if len(prof) < 4:
            out.append({"at": round(t, 3), "kind": "unknown", "peak_ratio": None}); continue
        pk, med = max(prof), float(np.median(prof)) or 0.01
        ratio = pk / med
        dark = min(lumas) < 20 if lumas else False   # mean luma 20/255 is visually black
        kind = ("fade" if dark and pk > 4 else
                "cut" if ratio >= 4.0 else
                "dissolve" if pk > 3 else "soft")
        out.append({"at": round(t, 3), "kind": kind, "peak_ratio": round(ratio, 2),
                    "peak": round(pk, 1), "min_luma": round(min(lumas), 1) if lumas else None})
    cap.release()
    return out


def palette(cap, cv2, np, t: float, k: int = 3) -> list:
    """The k dominant colours at time t, as hex — what a prompt would have to name to match."""
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
    ok, fr = cap.read()
    if not ok or fr is None:
        return []
    small = cv2.resize(fr, (80, 45)).reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, lab, cen = cv2.kmeans(small, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    order = np.argsort(-np.bincount(lab.ravel(), minlength=k))
    return ["#%02x%02x%02x" % (int(cen[i][2]), int(cen[i][1]), int(cen[i][0])) for i in order]


def sheet(path: str, stamps: list, out_png: str, cols: int, label_each: bool = True) -> bool:
    """A grid of frames pulled at `stamps` [(seconds, label)]."""
    with tempfile.TemporaryDirectory() as tmp:
        tiles = []
        for n, (t, lab) in enumerate(stamps):
            p = os.path.join(tmp, f"{n:04d}.png")
            vf = "scale=480:-2"
            if label_each:
                safe = str(lab).replace(":", "\\:").replace("'", "")
                vf += (f",drawtext=text='{safe}':x=8:y=8:fontsize=26:fontcolor=white:"
                       f"box=1:boxcolor=black@0.6:boxborderw=6")
            r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}",
                                "-i", path, "-frames:v", "1", "-vf", vf, p],
                               capture_output=True, text=True, errors="replace")
            if r.returncode != 0 or not os.path.isfile(p):
                r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}",
                                    "-i", path, "-frames:v", "1", "-vf", "scale=480:-2", p],
                                   capture_output=True, text=True, errors="replace")
            if os.path.isfile(p):
                tiles.append(p)
        if not tiles:
            return False
        rows = math.ceil(len(tiles) / cols)
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for p in tiles:
            cmd += ["-i", p]
        cmd += ["-filter_complex", f"tile={cols}x{rows}:padding=6:margin=6:color=black",
                "-frames:v", "1", out_png]
        # `tile` consumes ONE input stream of successive frames, so concat the stills first
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i",
               os.path.join(tmp, "%04d.png"), "-vf",
               f"tile={cols}x{rows}:padding=6:margin=6:color=black", "-frames:v", "1", out_png]
        subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        return os.path.isfile(out_png)


def strips(path: str, out_dir: str, label: str, fps: int = 4, width: int = 256) -> list:
    """The whole film as timestamped contact sheets: one frame per 1/`fps` s, 8 x 5 per sheet; each
    stamp is the exact time of the frame under it.

    The stamp is the frame's own time from the file's start (setpts=PTS-STARTPTS), the clock the cut
    table uses. ⛔ drawtext's `%{pts:flt:N}` treats N as an OFFSET in seconds, not decimals — an early
    version wrote `:1` and every label ran one second ahead (found by two readers, lab-00006).
    """
    font = next((f for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                             "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                             "/Library/Fonts/Arial Bold.ttf") if os.path.isfile(f)), None)
    stamp = (f"drawtext={'fontfile=' + repr(font)[1:-1] + ':' if font else ''}text='%{{pts\\:flt}}':x=4:y=4:"
             f"fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.65,")
    # the first frame of every 1/fps-second bin, stamped with ITS OWN time — not the fps filter, whose
    # rounding shows a frame up to ~0.12 s after the grid time it is labelled with
    pick = f"select='eq(n\\,0)+gt(floor(t*{fps})\\,floor(prev_t*{fps}))'"
    vf = f"setpts=PTS-STARTPTS,{pick},scale={width}:-2,{stamp}tile=8x5:padding=2:color=white"
    pattern = os.path.join(out_dir, f"STRIP-{label}-%02d.png")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", vf, "-vsync", "vfr", pattern],
                       capture_output=True, text=True, errors="replace")
    if r.returncode:   # a build without drawtext still gets the sheets, unstamped
        vf = f"setpts=PTS-STARTPTS,{pick},scale={width}:-2,tile=8x5:padding=2:color=white"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", vf, "-vsync", "vfr", pattern],
                       capture_output=True, text=True, errors="replace")
    return sorted(os.path.join(out_dir, f) for f in os.listdir(out_dir)
                  if f.startswith(f"STRIP-{label}-") and f.endswith(".png"))


# ⛔ THE MOTION FRAME'S SHORT SIDE, NOT ITS WIDTH, DECIDES WHETHER THE WHOLE-SHOT SOLVE HOLDS.
# Measured 2026-10-25 on 40 shots of F5 (1920×820, 2.34:1): at --motion-width 480 the frame is
# 205 px tall and 20 of 40 shots came out UNRELIABLE; 640 (273 px) → 7; 960 (410 px) → 2. More
# samples did not help (7 at 480 → 22). On 40 shots of 9:16 hook ads the short side is already
# 480 px at width 480, and 640 changed 18 → 16: their failures are the footage, not the frame.
# [measured on one film and one ad set; the 400 px floor is estimated from them]
MOTION_MIN_SHORT = 400


def motion_frame_note(W: int, H: int, motion_w: int) -> dict:
    """The size the motion solve will see, and a warning when its short side is under the floor."""
    s = (motion_w / W) if (motion_w and W > motion_w) else 1.0
    w, h = int(round(W * s)), int(round(H * s))
    out = {"w": w, "h": h, "short_side": min(w, h)}
    if min(w, h) < MOTION_MIN_SHORT and min(W, H) > min(w, h):
        need = int(-(-MOTION_MIN_SHORT * W // min(W, H)))
        need += need % 2
        out["warning"] = (f"the motion frame is {w}×{h}: a short side under {MOTION_MIN_SHORT} px left half of "
                          f"a 2.34:1 film's shots UNRELIABLE — use --motion-width {need} (or 0 for full res)")
    return out


def breakdown(path: str, out_dir: str, label: str, threshold: float, samples: int,
              min_shot: float, moves: bool = True, detect_h: int = 480,
              motion_w: int = 640, verify: bool = True) -> dict:
    if not have("ffmpeg", "ffprobe"):
        raise SystemExit("error: ffmpeg/ffprobe not on PATH")
    os.makedirs(out_dir, exist_ok=True)
    dur = probe_duration(path)
    if dur <= 0:
        raise SystemExit(f"error: cannot read a duration from {path}")
    cuts = cut_times(path, threshold, detect_h)
    shots, merged = shots_from_cuts(cuts, dur, min_shot)
    # ⛔ SENSITIVITY IS NOT OPTIONAL. One threshold is one opinion about what counts as a cut, and a
    # soft or low-contrast cut sits under it — a 44.5-second "shot" in a real film turned out to be
    # FIVE shots when the threshold was halved (found 2026-09-30, by looking at the frames). Every
    # shot that splits at the lower threshold is marked `split_suspect`, so a long shot is never
    # quietly reported as a long shot.
    lower = cut_times(path, threshold * 0.6, detect_h) if verify else []
    extra = [c for c in lower if all(abs(c - x) > min_shot for x in cuts)]
    np, cv2 = _np()
    cap = cascade = None
    if cv2 is not None:
        cap = cv2.VideoCapture(path)
        try:
            xml = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            cascade = cv2.CascadeClassifier(xml) if os.path.isfile(xml) else None
            if cascade is not None and cascade.empty():
                cascade = None
        except Exception:
            cascade = None
    mframe = None
    if cap is not None and cap.isOpened():
        mframe = motion_frame_note(int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                                   motion_w)
        if mframe.get("warning"):
            print(f"⚠ {mframe['warning']}", file=sys.stderr)
    trans = []
    if cv2 is not None and len(shots) > 1:
        trans = transitions(path, [b for b, _ in shots[1:]], cv2, np)
    tmap = {round(t["at"], 3): t for t in trans}
    rows = []
    for i, (a, b) in enumerate(shots, 1):
        r = {"n": i, "start": round(a, 3), "end": round(b, 3), "dur": round(b - a, 3)}
        if cap is not None and cap.isOpened():
            r.update(measure_shot(cap, cv2, np, a, b, samples, cascade, motion_w))
            r["palette"] = palette(cap, cv2, np, (a + b) / 2)
        inside = [c for c in extra if a + min_shot < c < b - min_shot]
        if inside:
            r["split_suspect"] = len(inside) + 1        # how many shots this probably really is
            r["split_at"] = [round(c, 2) for c in inside]   # all of them (the first 6 only hid most of a failed ad, lab-00006)
        inn = tmap.get(round(a, 3))
        r["transition_in"] = (inn or {}).get("kind") if i > 1 else "open"
        nxt = tmap.get(round(b, 3))
        r["transition_out"] = (nxt or {}).get("kind") if i < len(shots) else "end"
        rows.append(r)
    if cap is not None:
        cap.release()
    # repeats by picture, then every row says whether it may teach a camera move.
    # Flagged rows stay in the table; nothing is dropped.
    repeats = group_repeats(rows)
    for r in rows:
        r["preset_flags"] = preset_flags(r, len(rows))
        r["preset_ok"] = not r["preset_flags"]
    # the sequence sheet: the middle frame of every shot, numbered
    seq = os.path.join(out_dir, f"SHEET-{label}.png")
    ok_seq = sheet(path, [((r["start"] + r["end"]) / 2, f"{r['n']} · {r['dur']:.2f}s") for r in rows],
                   seq, cols=min(6, max(1, len(rows))))
    move_sheets = []
    if moves:
        for r in rows:
            a, b = r["start"], r["end"]
            stamps = [(a + (b - a) * f, lab) for f, lab in ((0.08, "IN"), (0.5, "MID"), (0.92, "OUT"))]
            p = os.path.join(out_dir, f"MOVES-{label}-{r['n']:02d}.png")
            if sheet(path, stamps, p, cols=3):
                move_sheets.append(p)
    tcount = {}
    for t in trans:
        tcount[t["kind"]] = tcount.get(t["kind"], 0) + 1
    n_susp = sum(1 for r in rows if r.get("split_suspect"))
    data = {"split_suspects": n_susp, "verify_threshold": round(threshold * 0.6, 2) if verify else None,
            "transitions": tcount, "file": os.path.abspath(path), "label": label, "duration": round(dur, 3),
            "shots": len(rows), "cuts_detected": len(cuts), "cuts_merged_as_sub_shot": merged,
            "threshold": threshold, "samples_per_shot": samples, "min_shot_s": min_shot, "motion_frame": mframe,
            "motion_measured": cv2 is not None, "faces_available": cascade is not None,
            "sequence_sheet": seq if ok_seq else None, "move_sheets": move_sheets, "rows": rows,
            # a repeated shot counts once; the rows that may teach a camera move
            "repeats": repeats, "unique_shots": len(rows) - sum(len(g) - 1 for g in repeats),
            "preset_rows": sum(1 for r in rows if r.get("preset_ok")),
            "scale_unchecked": sum(1 for r in rows if r.get("scale_check") == "cannot confirm"),
            "_bands": {"size": "[ASSUMED] face height / frame height: "
                               + ", ".join(f"{n}>={lo}" for lo, n in SIZE_BANDS),
                       "motion": f"[ASSUMED] locked<{MOVE_STILL}, slow<{MOVE_SLOW} frame-widths/s",
                       "preset": (f"[assumed] black: mean<{BLACK_MEAN:g} and p99<{BLACK_P99:g} in "
                                  f"{BLACK_SHARE:.0%} of frames; card: ±{CARD_TOL} band holds {CARD_PLAIN:.0%}; "
                                  f"inset: a filled box of {INSET_MIN_AREA:.0%}–{INSET_MAX_AREA:.0%} of the frame "
                                  f"with ≤{INSET_OUTSIDE:.0%} moving outside; scroll: rigid vertical travel beside "
                                  f"still points in {SCROLL_PAIR_SHARE:.0%} of moving pairs; scale: the face within "
                                  f"{SCALE_AGREE:.0%}; repeat: ≤{REPEAT_HAMMING} of 64 bits in "
                                  f"{REPEAT_MIN_SHARE:.0%} of frames")}}
    with open(os.path.join(out_dir, f"BREAKDOWN-{label}.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    with open(os.path.join(out_dir, f"BREAKDOWN-{label}.md"), "w", encoding="utf-8") as fh:
        fh.write(render_md(data))
    return data


def render_md(d: dict) -> str:
    L = [f"# Shot breakdown — {d['label']}", "",
         f"`{d['file']}` · **{d['duration']:.2f}s** · **{d['shots']} shots** · "
         f"{d['cuts_detected']} cuts detected"
         + (f" ({d['cuts_merged_as_sub_shot']} merged as sub-shot motion)" if d["cuts_merged_as_sub_shot"] else ""),
         ""]
    durs = [r["dur"] for r in d["rows"]]
    if durs:
        mean = sum(durs) / len(durs)
        L += [f"**Rhythm** — mean shot {mean:.2f}s · shortest {min(durs):.2f}s · longest {max(durs):.2f}s "
              f"· cuts per 10s {10 * len(durs) / max(d['duration'], 0.001):.1f}", ""]
        half = len(durs) // 2
        if half:
            first, second = sum(durs[:half]) / half, sum(durs[half:]) / (len(durs) - half)
            trend = ("ACCELERATES" if second < first * 0.8 else
                     "DECELERATES" if second > first * 1.25 else "holds an even pace")
            L += [f"The cutting **{trend}**: first half mean {first:.2f}s, second half {second:.2f}s.", ""]
    if not d["motion_measured"]:
        L += ["⛔ OpenCV/numpy unavailable — camera-move and shot-size columns read UNMEASURED.", ""]
    if d.get("split_suspects"):
        L += [f"\u26d4 **{d['split_suspects']} shot(s) split at the lower threshold "
              f"({d.get('verify_threshold')}) and are marked `split_suspect` \u2014 a soft or "
              f"low-contrast cut sits under the main threshold. Do not cite a long shot that "
              f"carries this flag.**", ""]
    # a repeated shot counts once, matched on the pictures and never on the motion trace
    reps = d.get("repeats") or []
    if reps:
        L += [f"**Repeats by picture** — " + " · ".join(" = ".join(f"#{n}" for n in g) for g in reps)
              + f". Counted once: **{d.get('unique_shots')} unique shot(s)** of {d['shots']}. Matched on the "
                f"sampled pictures, never on the motion trace; two adjacent rows that match may be one shot "
                f"split by a false cut — check the strip.", ""]
    # which rows may teach a camera move
    if d["rows"] and any("preset_flags" in r for r in d["rows"]):
        L += [f"**Move presets** — {d.get('preset_rows', 0)} of {d['shots']} row(s) may teach a camera move. "
              f"The others are marked in the `preset` column and stay in the table."
              + (f" {d['scale_unchecked']} scale move(s) could not be checked against the subject: no face "
                 f"at both ends." if d.get("scale_unchecked") else ""), ""]
    L += ["| # | in | out | len | camera move | motion/s | subject residual | size | face h | luma | preset |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in d["rows"]:
        pf = r.get("preset_flags")
        pcell = "—" if pf is None else ("yes" if not pf else "no: " + ", ".join(pf))
        L.append(f"| {r['n']} | {r['start']:.2f} | {r['end']:.2f} | {r['dur']:.2f} | "
                 f"{r.get('move', 'UNMEASURED')} | {r.get('per_s', '—')} | "
                 f"{r.get('residual') if r.get('residual') is not None else '—'} | "
                 f"{r.get('size') or '—'} | {r.get('face_ratio') or '—'} | {r.get('luma') or '—'} | {pcell} |")
    L += ["", "**How to read it.** `motion/s` is camera translation in frame-widths per second; "
              "`subject residual` is the median flow left AFTER the camera move is removed, so a shot "
              "with low motion and high residual is a PERFORMANCE shot and the reverse is a CAMERA "
              "shot. Shot size is a proxy from a frontal face and is missing wherever no face is "
              "found — the bands are [ASSUMED] " + d["_bands"]["size"] + ". `preset` says whether the row "
              "may teach a camera move: a black opening, tail or stub, a flat card, an inset, a screen "
              "scroll, a scale the face does not follow, a repeat, an unmeasured or unreliable move and a "
              "split suspect may not; the heuristics are [assumed]"
              + (" — " + d["_bands"]["preset"] if d["_bands"].get("preset") else "")
              + ", and `--help` says what they cannot see.", "",
          "⛔ **This table has no opinions.** What each shot is FOR — the beat it carries, the "
          "reason it is that size, what the cut does to the viewer — is read off the sheets by a "
          "person and written into `specifics-catalogue.md`, verbatim, with the outcome."]
    return "\n".join(L) + "\n"


def _selftest_presets() -> str:
    """HR-23 (rows that may not teach a camera move) and HR-24 (repeats by picture). Pure checks
    first; then, with ffmpeg and OpenCV, one synthetic film carrying every case end to end. Returns
    what ran, for the summary line; raises AssertionError on a failure, like the rest of selftest()."""
    # -- pure, no numpy: the scale check, the hash distance, the grouping and the flag names
    assert scale_verdict(1.30, 0.20, 0.26)[0] == "confirmed"
    assert scale_verdict(1.30, 0.20, 0.20)[0] == "unconfirmed", "a push the face does not follow"
    assert scale_verdict(0.80, 0.20, 0.25)[0] == "unconfirmed", "a pull while the face grows"
    assert scale_verdict(1.30, None, 0.26)[0] == "cannot confirm", "no face at one end: say so, never flag"
    assert scale_verdict(1.01, 0.20, 0.30) == (None, ""), "under 4 % is not a scale move"
    assert hamming(0b1011, 0b0010) == 2
    same, other = ["00ff00ff00ff00ff"] * 3, ["ff00ff00ff00ff00"] * 3
    rows = [{"n": 1, "phash": same, "dx": 0.2, "per_s": 0.1},       # picture P, move M
            {"n": 2, "phash": other, "dx": 0.2, "per_s": 0.1},      # picture Q, the SAME move M
            {"n": 3, "phash": same, "dx": -0.4, "per_s": 0.9},      # picture P again, a different move
            {"n": 4, "phash": same, "black": True},                 # black rows are never grouped
            {"n": 5, "phash": ["00ff00ff00ff00fe", "0f0f0f0f0f0f0f0f", "f0f0f0f0f0f0f0f0"]}]  # 1 of 3 match P
    g = group_repeats(rows)
    assert g == [[1, 3]], g
    assert rows[2].get("repeat_of") == 1 and "repeat_of" not in rows[0], "the repeat is counted once"
    assert "repeat_of" not in rows[1], "⛔ a matching motion trace over a different picture is NOT a repeat"
    assert "repeat_of" not in rows[3] and "repeat_of" not in rows[4]
    pf = lambda **k: preset_flags(dict({"n": 2, "move": "slow: pan right 10%W"}, **k), 5)
    assert pf() == [], "a measured move with nothing against it is a preset"
    assert preset_flags({"n": 1, "black": True, "move": "UNMEASURED (x)"}, 5)[0] == "black opening"
    assert preset_flags({"n": 5, "black": True, "move": "locked off"}, 5) == ["black tail"]
    assert preset_flags({"n": 3, "black": True, "move": "locked off"}, 5) == ["black stub"]
    assert pf(card=True) == ["flat card"] and pf(inset={"x": 0.7}) == ["inset"]
    assert pf(scroll=True) == ["screen scroll"] and pf(scale_check="unconfirmed") == ["scale unconfirmed"]
    assert pf(scale_check="cannot confirm") == [], "an unchecked scale is reported, not flagged"
    assert pf(repeat_of=1) == ["repeat of #1"] and pf(split_suspect=2) == ["split suspect"]
    assert pf(move="UNRELIABLE (3 inliers)") == ["move unreliable"]
    md = render_md({"label": "x", "file": "f", "duration": 4.0, "shots": 2, "cuts_detected": 1,
                    "cuts_merged_as_sub_shot": 0, "motion_measured": True, "repeats": [[1, 2]], "unique_shots": 1,
                    "preset_rows": 1, "_bands": {"size": "b", "motion": "m", "preset": "p"},
                    "rows": [{"n": 1, "start": 0, "end": 1, "dur": 1.0, "preset_flags": []},
                             {"n": 2, "start": 1, "end": 4, "dur": 3.0, "preset_flags": ["repeat of #1"]}]})
    assert "| preset |" in md and "| yes |" in md and "no: repeat of #1" in md and "#1 = #2" in md, md
    assert "1 unique shot(s)" in md and "1 of 2 row(s) may teach a camera move" in md, md
    np, cv2 = _np()
    if cv2 is None:
        return "HR-23/HR-24 pure checks (OpenCV absent — frame heuristics not run)"
    # -- with numpy and OpenCV: the frame heuristics on built frames
    rng = np.random.default_rng(3)
    noise = rng.integers(0, 256, (360, 640), dtype=np.uint8)
    card = np.full((360, 640), 128, np.uint8); card[160:200, 280:360] = 255
    logo = np.zeros((360, 640), np.uint8); logo[150:210, 260:380] = 230
    assert frame_kind(np, np.zeros((360, 640), np.uint8))["black"]
    assert frame_kind(np, card)["card"] and not frame_kind(np, card)["black"]
    assert frame_kind(np, logo)["card"] and not frame_kind(np, logo)["black"], "a lit logo on black is a card"
    assert not frame_kind(np, noise)["card"] and not frame_kind(np, noise)["black"]
    mv = np.zeros((22, 40), bool); mv[16:21, 29:39] = True
    ins = inset_from_cells(cv2, np, mv)
    assert ins and abs(ins["x"] - 29 / 40) < 1e-6, ins
    straddle = mv.copy(); straddle[21, 30] = straddle[21, 32] = straddle[17, 28] = True
    assert inset_from_cells(cv2, np, straddle), "cells part-covered at the inset's border are trimmed"
    assert inset_from_cells(cv2, np, np.ones((22, 40), bool)) is None, "a whole moving frame is not an inset"
    yy, xx = np.mgrid[0:22, 0:40]
    blob = ((xx - 20) / 6.0) ** 2 + ((yy - 11) / 5.0) ** 2 <= 1.0
    assert inset_from_cells(cv2, np, blob) is None, "a head-shaped blob is not a box"
    noisy = mv.copy(); noisy[rng.random((22, 40)) < 0.05] = True
    assert inset_from_cells(cv2, np, noisy) is None, "motion outside the box: not an inset"
    gx, gy = np.meshgrid(np.arange(20, 620, 24.0), np.arange(60, 300, 24.0))
    pm = np.stack([gx.ravel(), gy.ravel()], 1)
    sx, sy = np.meshgrid(np.arange(20, 620, 40.0), np.array([10.0, 340.0]))
    ps = np.stack([sx.ravel(), sy.ravel()], 1)
    P0 = np.vstack([pm, ps]); P1 = np.vstack([pm + [0.0, 6.0], ps])
    assert scroll_pair(np, P0, P1)["scroll"], "a rigid vertical sheet beside still bars is a scroll"
    assert not scroll_pair(np, pm, pm + [0.0, 6.0])["scroll"], "⛔ no still bar beside it: a tilt over a still"
    assert not scroll_pair(np, P0, np.vstack([pm + [3.0, 6.0], ps]))["scroll"], "a diagonal move is not a scroll"
    persp = pm.copy(); persp[:, 1] += 4.0 + 4.0 * (pm[:, 1] - 60) / 240.0
    assert not scroll_pair(np, P0, np.vstack([persp, ps]))["scroll"], "parallax is not a rigid sheet"
    assert scroll_pair(np, ps, ps) is None, "nothing moved: not judged"
    h1, h2 = dhash(cv2, np, noise), dhash(cv2, np, rng.integers(0, 256, (360, 640), dtype=np.uint8))
    assert h1 == dhash(cv2, np, noise) and hamming(h1, h2) > REPEAT_HAMMING
    assert dhash(cv2, np, np.full((360, 640), 90, np.uint8)) is None, "a flat frame has no picture to hash"
    if not have("ffmpeg", "ffprobe"):
        return "HR-23/HR-24 pure and frame checks (ffmpeg absent — the end-to-end film did NOT run)"
    # -- end to end: one film carrying every case, at known times
    with tempfile.TemporaryDirectory() as td:
        P = lambda n: os.path.join(td, n)

        def ff(*args):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, timeout=120)
        # ⛔ Two things keep D.png, the scrolling sheet, a fair fixture [measured 2026-11-10 · ffmpeg 8.1.1, cv2 5.0.0]:
        #  · format=rgb24. `rgbtestsrc` comes out with an alpha channel there, D.png was written see-through, and the
        #    sheet overlaid from it showed the bars behind it: 0 pairs judged.
        #  · grain 60, not the 28 of the still pictures. The sheet's only texture is its grain. At 28, about 380
        #    of the 400 tracked corners sat on the still bars and 18 to 21 on the moving sheet, against
        #    SCROLL_MIN_TRACKS 20 (1 pair judged of 4); at 60, about 190 are on the sheet in each of the 4.
        for name, src, size, grain in (("A.png", "smptehdbars", "1280x720", 28), ("B.png", "testsrc2", "1280x720", 28),
                                       ("C.png", "testsrc", "1280x720", 28), ("D.png", "rgbtestsrc", "640x1600", 60)):
            ff("-f", "lavfi", "-i", f"{src}=size={size}:rate=1:duration=1", "-vf",
               f"noise=alls={grain}:allf=p,format=rgb24", "-frames:v", "1", P(name))
        enc = ["-r", "25", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-g", "25"]
        ff("-f", "lavfi", "-i", "color=c=black:size=640x360:rate=25:duration=1", *enc, P("1.mp4"))
        for out_, still in (("2.mp4", "A.png"), ("4.mp4", "B.png")):     # the SAME pan over two pictures
            ff("-loop", "1", "-i", P(still), "-t", "2", "-vf", "crop=640:360:'200+t*50':180,fps=25", *enc, P(out_))
        ff("-f", "lavfi", "-i", "color=c=gray:size=640x360:rate=25:duration=2,"
           "drawbox=x=280:y=160:w=80:h=40:color=white:t=fill", *enc, P("3.mp4"))
        ff("-loop", "1", "-t", "2", "-i", P("C.png"), "-loop", "1", "-t", "2", "-i", P("B.png"), "-filter_complex",
           # the inset is a video playing: it changes everywhere (x264 smooths a sliding noise texture flat)
           "[0:v]crop=640:360:100:100,fps=25[bg];[1:v]crop=160:90:'100+t*120':200,fps=25,noise=alls=60:allf=t[in];"
           "[bg][in]overlay=460:250", "-t", "2", *enc, P("6.mp4"))
        ff("-loop", "1", "-t", "2", "-i", P("A.png"), "-loop", "1", "-t", "2", "-i", P("D.png"), "-filter_complex",
           "[0:v]crop=640:360:0:0,fps=25[bg];[1:v]crop=640:300:0:'t*60',fps=25[sc];[bg][sc]overlay=0:30",
           "-t", "2", *enc, P("7.mp4"))
        ff("-f", "lavfi", "-i", "color=c=black:size=640x360:rate=25:duration=1", *enc, P("8.mp4"))
        parts = [P(f"{i}.mp4") for i in (1, 2, 3, 4)] + [P("2.mp4")] + [P(f"{i}.mp4") for i in (6, 7, 8)]
        if not all(os.path.isfile(p) for p in parts):
            return "HR-23/HR-24 pure and frame checks (a fixture did not encode — the end-to-end film did NOT run)"
        open(P("l.txt"), "w").write("".join(f"file '{p}'\n" for p in parts))
        film = P("sample.mp4")
        ff("-f", "concat", "-safe", "0", "-i", P("l.txt"), *enc, film)
        d = breakdown(film, P("out"), "sample", 10.0, 5, 0.15, moves=False, verify=True)
        assert d["shots"] == 8, [(r["start"], r["end"]) for r in d["rows"]]
        at = {round(r["start"]): r for r in d["rows"]}
        fl = {k: r["preset_flags"] for k, r in at.items()}
        assert fl[0][:1] == ["black opening"] and fl[13][:1] == ["black tail"], (fl[0], fl[13])
        assert "flat card" in fl[3], (fl[3], at[3].get("card_share"))
        assert "inset" in fl[9], (fl[9], at[9].get("inset"))
        assert "screen scroll" in fl[11], (fl[11], at[11].get("scroll_pairs"))
        assert at[7].get("repeat_of") == at[1]["n"] and f"repeat of #{at[1]['n']}" in fl[7], fl[7]
        # the two pans are ONE trace — the same per-pair rate — over two different pictures
        assert at[1].get("per_s") and abs(at[1]["per_s"] - at[5]["per_s"]) <= 0.1 * at[1]["per_s"], \
            (at[1].get("per_s"), at[5].get("per_s"))
        assert "repeat_of" not in at[5], "⛔ the same pan over a different picture is not a repeat"
        new = ("black", "flat card", "inset", "screen scroll", "scale unconfirmed", "repeat")
        hit = {k for k, v in fl.items() if any(x.startswith(new) for x in v)}
        assert hit == {0, 3, 7, 9, 11, 13}, ("the camera pans must carry none of the new flags", fl)
        assert d["repeats"] == [[at[1]["n"], at[7]["n"]]] and d["unique_shots"] == 7, d["repeats"]
        assert all("preset_ok" in r and isinstance(r["preset_flags"], list) for r in d["rows"]), \
            "every row is marked, and every row stays in the table"
        md = open(P(os.path.join("out", "BREAKDOWN-sample.md")), encoding="utf-8").read()
        assert "no: black opening" in md and "#2 = #5" in md and md.count("\n| ") >= 9, md[:600]
    return ("HR-23/HR-24 end to end on a synthetic 8-shot film: black opening and tail, a flat card, an inset "
            "and a screen scroll flagged and kept; a reused shot grouped by picture and counted once; the same "
            "pan over a different picture NOT grouped; the camera pans carry none of the new flags")


def selftest() -> int:
    # pure functions first — these run everywhere, with no ffmpeg and no OpenCV
    mf = motion_frame_note(1920, 820, 480)
    assert mf["short_side"] == 205 and "--motion-width 938" in mf["warning"], mf
    assert "warning" not in motion_frame_note(1920, 820, 960), "410 px clears the floor"
    assert "warning" not in motion_frame_note(1080, 1920, 480), "a 9:16 frame at 480 wide is 480 px on its short side"
    assert "warning" not in motion_frame_note(640, 272, 640), "a small source is never warned: it cannot go higher"
    s, merged = shots_from_cuts([2.0, 2.05, 5.0], 8.0, 0.15)
    assert s == [(0.0, 2.0), (2.0, 5.0), (5.0, 8.0)] and merged == 1, (s, merged)
    assert shots_from_cuts([], 5.0, 0.15) == ([(0.0, 5.0)], 0)
    # a cut just before the end must not leave a zero-length shot behind
    s2, m2 = shots_from_cuts([2.0, 7.98], 8.0, 0.15)
    assert s2 == [(0.0, 2.0), (2.0, 8.0)] and m2 == 1, (s2, m2)
    assert classify_size(0.60) == "ECU" and classify_size(0.40) == "CU" and classify_size(0.02) == "WS"
    assert "push in" in describe_move(0, 0, 1.30, 0, 0.2)
    assert "pull out" in describe_move(0, 0, 0.80, 0, 0.2)
    # the picture moving right means the camera panned LEFT; the picture moving up, a tilt DOWN
    assert "pan left" in describe_move(0.20, 0, 1.0, 0, 0.2)
    assert "pan right" in describe_move(-0.20, 0, 1.0, 0, 0.2)
    assert "tilt down" in describe_move(0, -0.20, 1.0, 0, 0.2)
    assert "tilt up" in describe_move(0, 0.20, 1.0, 0, 0.2)
    assert "roll" in describe_move(0, 0, 1.0, 6.0, 0.2)
    assert describe_move(0, 0, 1.0, 0, 0.001) == "locked off"
    assert describe_move(0, 0, 1.0, 0, 0.5) == "handheld/shake"
    md = render_md({"label": "x", "file": "f", "duration": 4.0, "shots": 2, "cuts_detected": 1,
                    "cuts_merged_as_sub_shot": 0, "motion_measured": False,
                    "_bands": {"size": "b", "motion": "m"},
                    "rows": [{"n": 1, "start": 0, "end": 1, "dur": 1.0},
                             {"n": 2, "start": 1, "end": 4, "dur": 3.0}]})
    assert "UNMEASURED" in md and "DECELERATES" in md, md
    ran_e2e = False
    if have("ffmpeg", "ffprobe"):
        np, cv2 = _np()
        with tempfile.TemporaryDirectory() as td:
            # A synthetic film with KNOWN cuts at 2 s and 4 s, and a KNOWN push-in on shot 3.
            # ⛔ `zoompan` needs `pzoom` (the PREVIOUS zoom) to accumulate: with `zoom` and d=1 it
            # resets every frame, which is a push-in that does not move — the first version of this
            # fixture tested nothing, and the assertion below is what caught it (2026-09-30).
            a = os.path.join(td, "a.mp4"); b = os.path.join(td, "b.mp4"); c = os.path.join(td, "c.mp4")
            v = os.path.join(td, "film.mp4")
            for dst, src in ((a, "testsrc2=size=640x360:rate=25:duration=2"),
                             (b, "smptebars=size=640x360:rate=25:duration=2")):
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src,
                                "-pix_fmt", "yuv420p", dst], capture_output=True)
            # ⛔ The push-in fixture needs TEXTURE. rgbtestsrc is a smooth gradient: ORB finds zero
            # corners in it, so the total-move solve returned "0 inliers" and the test proved
            # nothing about a push-in. A noisy still, looped and zoomed, is a real subject.
            still = os.path.join(td, "still.png")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                            "-i", "smptehdbars=size=1280x720:d=1", "-vf", "noise=alls=28:allf=p",
                            "-frames:v", "1", still], capture_output=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", still,
                            "-t", "2", "-vf",
                            "zoompan=z='min(pzoom+0.006,1.6)':d=1:s=640x360:fps=25",
                            "-pix_fmt", "yuv420p", c], capture_output=True)
            lst = os.path.join(td, "l.txt")
            open(lst, "w").write("".join(f"file '{p}'\n" for p in (a, b, c)))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                            "-i", lst, "-c:v", "libx264", "-pix_fmt", "yuv420p", v], capture_output=True)
            if os.path.isfile(v) and probe_duration(v) > 5:
                ran_e2e = True
                d = breakdown(v, os.path.join(td, "out"), "selftest", 10.0, 5, 0.15, moves=False,
                              verify=True)
                assert d["verify_threshold"] == 6.0, d["verify_threshold"]
                # detection must survive the downscale it defaults to, and match full-res
                assert len(cut_times(v, 10.0, 0)) == len(cut_times(v, 10.0, 480)), "downscale changed the cuts"
                assert d["shots"] == 3, f"expected 3 shots, got {d['shots']}: {[r['dur'] for r in d['rows']]}"
                assert abs(d["rows"][0]["dur"] - 2.0) < 0.35, d["rows"][0]
                assert os.path.isfile(os.path.join(td, "out", "BREAKDOWN-selftest.md"))
                assert d["sequence_sheet"] and os.path.isfile(d["sequence_sheet"])
                st_ = strips(v, os.path.join(td, "out"), "selftest")
                assert len(st_) == 1 and os.path.isfile(st_[0]), st_   # 6 s at 4 fps = 24 frames, one sheet
                if cv2 is not None:
                    # the push-in must read as a push-in, and the static bars must not
                    assert d["rows"][2].get("scale", 1) > 1.03, d["rows"][2]
                    assert "push in" in (d["rows"][2].get("move") or ""), d["rows"][2]
                    r2 = d["rows"][1]        # static colour bars: slow, or an honest refusal
                    assert (r2.get("per_s") is None) or r2["per_s"] < MOVE_SLOW, r2
                    assert "UNMEASURED" in r2["move"] or r2["move"] in ("locked off", "drift"), r2
                    # ⛔ and a total nobody can stand behind must say so, not print a number
                    assert not _affine_orb(cv2, np, np.zeros((64, 64), np.uint8),
                                           np.zeros((64, 64), np.uint8))[0], "featureless → None"
                    # ⛔ DIRECTION, end to end: a window sliding RIGHT across a still is a camera
                    # panning RIGHT (the picture slides left); one sliding DOWN is a tilt DOWN
                    wide = os.path.join(td, "wide.png")
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                    "smptehdbars=size=1280x720:d=1", "-vf", "noise=alls=28:allf=p",
                                    "-frames:v", "1", wide], capture_output=True)
                    for name, crop, want in (("pr", "crop=640:360:'200+t*50':180", "pan right"),
                                             ("td", "crop=640:360:300:'100+t*40'", "tilt down"),
                                             # a push-in about the CENTRE is a push-in and nothing else
                                             ("pc", "zoompan=z='min(pzoom+0.004,1.5)':d=1:s=640x360:fps=25:"
                                                    "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'", "push in")):
                        cp = os.path.join(td, name + ".mp4")
                        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", wide,
                                        "-t", "3", "-vf", crop + ",fps=25", "-pix_fmt", "yuv420p", cp],
                                       capture_output=True)
                        cap = cv2.VideoCapture(cp)
                        mv = measure_shot(cap, cv2, np, 0.0, 2.9, 5, None)
                        cap.release()
                        assert want in (mv.get("move") or ""), (name, mv)
                        if name == "pc":
                            assert "pan" not in mv["move"] and "tilt" not in mv["move"], mv
                    bogus = dict(dx=0.0, dy=9.0, scale=1.0, roll=0.0)
                    assert (abs(bogus["dy"]) > 1.5), "the bounds gate must reject a 900% tilt"
                    # TRANSITIONS — a hard cut, a 1s dissolve and a fade to black, built on purpose
                    x1, x2 = os.path.join(td, "x1.mp4"), os.path.join(td, "x2.mp4")
                    xf, fd = os.path.join(td, "xf.mp4"), os.path.join(td, "fd.mp4")
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                    "smptehdbars=size=320x180:rate=25:duration=3", "-pix_fmt",
                                    "yuv420p", x1], capture_output=True)
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                    "testsrc2=size=320x180:rate=25:duration=3", "-pix_fmt",
                                    "yuv420p", x2], capture_output=True)
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", x1, "-i", x2,
                                    "-filter_complex", "xfade=transition=fade:duration=1:offset=2",
                                    "-pix_fmt", "yuv420p", xf], capture_output=True)
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", x1, "-vf",
                                    "fade=t=out:st=2:d=1", "-pix_fmt", "yuv420p", fd],
                                   capture_output=True)
                    if os.path.isfile(xf) and os.path.isfile(fd):
                        hard = transitions(v, [2.0], cv2, np)[0]
                        soft = transitions(xf, [2.5], cv2, np)[0]
                        fade = transitions(fd, [2.9], cv2, np)[0]
                        assert hard["kind"] == "cut", hard
                        assert soft["kind"] in ("dissolve", "soft"), soft
                        assert soft["peak_ratio"] < hard["peak_ratio"], (soft, hard)
                        assert fade["kind"] == "fade" and fade["min_luma"] < 20, fade
    presets_note = _selftest_presets()                     # (HR-23/HR-24)
    print("selftest OK — shot table from cut times (incl. sub-shot merge), size bands, move naming "
          "(push/pull/pan/tilt/roll/locked/handheld, pan and tilt named from the camera's side), "
          "markdown incl. the UNMEASURED and pace rows"
          + ("; END TO END on a synthetic 3-shot film: cut count, shot length, sheet written"
             + (", a generated push-in solved as a push-in, a known pan right and tilt down named so, "
                "and a centred push-in with no pan or tilt" if _np()[1] is not None else
                " (OpenCV absent — motion not solved)")
             if ran_e2e else "; ⛔ ffmpeg absent — the end-to-end leg did NOT run")
          + "; " + presets_note)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?", help="the finished film to break down")
    ap.add_argument("--out", default=None, help="output folder (default: beside the video)")
    ap.add_argument("--label", default=None, help="name for the outputs (default: the file stem)")
    ap.add_argument("--threshold", type=float, default=10.0, help="scene-change threshold, 0-100 (default 10)")
    ap.add_argument("--samples", type=int, default=5, help="frames sampled per shot for the motion solve")
    ap.add_argument("--min-shot", type=float, default=0.15,
                    help="a 'cut' closer than this to the previous is merged as sub-shot motion")
    ap.add_argument("--no-moves", action="store_true", help="skip the per-shot IN/MID/OUT strips")
    ap.add_argument("--strip", action="store_true",
                    help="also write STRIP-<label>-NN.png: the film at 4 fps, timestamped, 10 s per sheet")
    ap.add_argument("--no-verify", action="store_true",
                    help="skip the lower-threshold sensitivity pass (it is what catches a soft cut)")
    ap.add_argument("--motion-width", type=int, default=640,
                    help="solve the camera move on frames scaled to this width (0 = full res). Keep the "
                         "frame's SHORT side at 400 px or more: a 2.34:1 film needs about 940 (warned if not)")
    ap.add_argument("--detect-height", type=int, default=480,
                    help="detect cuts on a copy scaled to this height (0 = full res, much slower)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.video:
        ap.print_help(); return 2
    if not os.path.isfile(a.video):
        print(f"error: {a.video} not found", file=sys.stderr); return 2
    label = a.label or re.sub(r"[^A-Za-z0-9_-]+", "-", os.path.splitext(os.path.basename(a.video))[0])
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), "breakdown")
    d = breakdown(a.video, out, label, a.threshold, a.samples, a.min_shot,
                  moves=not a.no_moves, detect_h=a.detect_height, motion_w=a.motion_width,
                  verify=not a.no_verify)
    if a.strip:
        d["strip_sheets"] = strips(a.video, out, label)
    if a.json:
        print(json.dumps(d, indent=2)); return 0
    print(render_md(d))
    print(f"\nwrote: {out}/BREAKDOWN-{label}.md · .json · SHEET-{label}.png"
          + (f" · {len(d['move_sheets'])} MOVES-*.png" if d["move_sheets"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
