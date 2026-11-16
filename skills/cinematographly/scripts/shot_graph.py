#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
shot_graph.py — how a film's shots RELATE: who and what carries from shot to shot, and what every cut
keeps or breaks. For films, shorts, promos, ads, and our own edits before picture lock.

House decision 2026-10-25: *"Analyze relationships between objects, frames, backgrounds, characters
from shot to shot"* — for movies, shorts and ads, for replicating a reference's structure with new
content (replicate.py), and as a continuity check on our own cuts. The release was asked for in one
piece ("All three in one release").

Two halves, kept apart on purpose (references/shot-relationships.md):

  MEASURED from the pixels, at every cut (frames decoded either side of the join, the real cut frame
  found from the frame difference, so a timestamp a frame off cannot put a frame on the wrong side):
    * the brightness and colour jump across the join (luma, CIE76 ΔE of the mean colour) and how alike
      the two palettes are with the mean removed (so a grade mismatch on one place reads as one place
      with a colour jump, not as two places);
    * the camera's motion just before and just after the cut, named from the camera's side;
    * the SUBJECT's screen motion either side (optical flow with the camera's motion removed), so a
      screen-direction flip is a number, not an impression;
    * where the subject sits either side (a face where OpenCV can find one, else the centroid of
      what moves) and how far the eye has to jump.

  MEASURED per shot (2026-10-25: "continuity, emotion, lighting, camera angles, camera motion
  (maybe even track and categorize it) … advanced background analysis for recreation and creativity
  enhancement"):
    * the CAMERA tracked through the shot (frames sampled at 8 fps, an inlier-gated similarity between
      each pair, chained): totals, speed, its profile (eases in, out, constant), shake, and a parallax
      index that separates a camera that TRAVELS (dolly, truck, crane) from one that only turns or
      zooms — then a category and the blocking.py move it maps to;
    * the LIGHT: brightness, contrast, low-key/high-key, the key side (on the face when there is one),
      warm/cool and saturation;
    * the BACKGROUND and composition: the 5-colour palette with shares, a 3×3 brightness map and a 3×3
      detail map (where the eye goes, where the negative space is), sharpness and a depth-of-field
      proxy, and, with --plates, a clean background plate for a held shot (the median of its frames,
      so whatever moves through it is gone).

  READ by a person or Claude, from the sheets this writes (a mid frame per shot, the frame pair at
  every cut), against a closed vocabulary (`template` writes the form, `validate` holds it to the
  vocabulary and cross-checks it against the measurements):
    * the entities — characters (the same letter in every shot they are in), props and products (who
      holds them, their state), locations (new, same, return);
    * per shot: size, angle, where each character sits, faces, looks and moves, their EMOTION and its
      intensity (film_db.py's scale) and whether it turns; the light's quality, style and time of day;
    * per location: interior or exterior, the place, era, weather, materials, what is in the fore-,
      mid- and background, what makes it distinctive, how to rebuild it, and three or more VARIANTS
      that keep its job in the frame (the depth layers, the light direction, where the eye goes) and
      change the world;
    * per cut: the relation, the match (action, eyeline, graphic, movement, sound…), the 180° line
      kept or crossed, screen direction, eyeline, what carries across, what changes, any continuity
      error seen.

  python3 shot_graph.py measure FILM.mp4 --cuts BREAKDOWN-film.json --label film --out DIR [--confirmed]
  python3 shot_graph.py template DIR/JOINS-film.json            # → READ-film.json, the form to fill
  python3 shot_graph.py validate DIR/READ-film.json             # vocabulary, counts, cross-checks
  python3 shot_graph.py merge DIR/READ-film.json                # → SHOTGRAPH-film.json + .md
  python3 shot_graph.py qa EDIT.mp4 --cuts CUTS --label cut_v3 --out DIR   # our edit: exit 1 on a flag
  python3 shot_graph.py --selftest

`--cuts` takes a film_breakdown BREAKDOWN-*.json (its rows), a text file of cut times (one per line,
# comments allowed), or `auto` (the detector, unconfirmed). ⛔ The detector finds about 76 % of true
cuts (lab-00006): confirm the list on `film_breakdown.py --strip` sheets and pass `--confirmed`, or
every output says the cut list is a draft.

⛔ Never stores dialogue, captions or any text from the film: positions, measures and the reader's own
words only (the film_db.py rule). Third-party footage is downloaded for analysis, measured, deleted.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ---- thresholds: house values, [assumed], printed with every result so they can be argued with ------
TH = {
    "delta_e_grade": 6.0,      # ΔE (CIE76, frame-mean colour) at a join between ALIKE pictures that reads
                               # as a grade / colour-cast mismatch — ~2.3 is a just-noticeable difference
    "luma_jump": 12.0,         # mean luma steps (0–255) between alike pictures that reads as an exposure jump
    "alike": 0.60,             # correlation of the mean-removed colour distributions (cast-invariant) at or
                               # above which the two sides share one palette — one place, or one look
    "unalike": 0.25,           # at or below which they look like different places
    "subject_v": 0.04,         # frame-widths per second of residual subject motion that counts as "moving"
    "eye_jump": 0.35,          # subject-position shift (fraction of the frame diagonal) that makes the eye jump
    "cam_still": 0.010,        # camera speed (frame-widths/s) under which a shot is locked
    "cam_slow": 0.060,         # under which a move is slow (film_breakdown.py's MOVE_STILL / MOVE_SLOW)
    "zoom_rate": 0.04,         # |ln(scale)| per second that counts as a push/pull or zoom
    "roll_rate": 2.0,          # degrees per second that counts as a roll
    "shake": 0.55,             # jitter / speed above which the camera is handheld
    "parallax": 0.18,          # share of the motion a flat similarity cannot explain: above it the camera travels
    "whip": 1.5,               # frame-widths per second at the peak that is a whip
    "track_back": 1.0,         # px at the 320 px analysis width: a point tracked a→b then b→a must land this
                               # close to where it started, or it is dropped (motion_track.py's FB value)
    "rest_block": 16,          # px at the 320 px analysis width: the picture AWAY from the tracked points is
                               # judged in blocks this size (a twentieth of the width)
    "rest_ratio": 0.5,         # a block sides with "the camera held" or with the fitted move only when that
                               # side's error is under this share of the other's ...
    "rest_margin": 0.3,        # ... and lower by at least this many grey levels (block mean after a 2 px blur)
    "rest_dispute": 0.5,       # a move stands but is DISPUTED when the area siding with "held" is over this
                               # share of the area behind the move (over 1.0 the move is overruled)
    "rest_large": 0.5,         # a move is UNCONFIRMED when the picture away from the points is at least this
                               # share of the frame and casts no vote either way
    "key_side": 6.0,           # L* difference between the two halves (face or frame) that names a key side
    "warm": 6.0, "cool": -4.0, # mean b* for a warm / cool picture
}
TH_TAG = "[assumed · house values, 2026-10-25 — calibrate on confirmed reads]"

# ---- the reading vocabulary (closed lists; `validate` enforces them) ---------------------------------
V = {
    "kind": {"character", "prop", "product", "location", "vehicle", "animal", "group", "graphic"},
    "size": {"EWS", "WS", "MWS", "MS", "MCU", "CU", "XCU", "insert", "n/a"},
    "angle": {"eye", "low", "high", "aerial", "dutch", "n/a"},
    "screen": {"left", "centre-left", "centre", "centre-right", "right", "off"},
    "depth": {"fg", "mid", "bg"},
    "gaze": {"camera", "screen-left", "screen-right", "up", "down", "closed", "n/a"},
    "facing": {"camera", "left", "right", "away", "n/a"},
    "motion": {"none", "left", "right", "toward", "away", "up", "down"},
    "light_key": {"left", "right", "front", "back", "top", "flat", "mixed", "practical", "n/a"},
    "relation": {"same-scene", "new-scene", "return", "insert", "cutaway", "graphic", "time-jump"},
    "match": {"action", "eyeline", "graphic", "movement", "sound", "shape", "colour", "none"},
    "axis": {"kept", "crossed", "n/a"},
    "screen_direction": {"kept", "flipped", "n/a"},
    "eyeline": {"matched", "mismatched", "n/a"},
    "changes": {"size", "angle", "subject", "place", "time", "costume", "prop-state", "light", "colour",
                "lens", "speed", "none"},
    "carries_tokens": {"light", "colour", "movement", "sound", "music", "line", "look"},
    # film_db.py's performance codebook, so a shot graph and the reference database speak one scale
    "expr": {"neutral", "attentive", "curious", "wary", "fear", "shock", "sad", "grief", "tender", "joy", "amused",
             "anger", "resolve", "awe", "relief", "pleading", "defeated", "effort", "pain", "n/a"},
    "intensity": {0, 1, 2, 3},
    "emotion_turn": {"none", "early", "late", "through"},
    "light_quality": {"hard", "soft", "mixed", "n/a"},
    "light_style": {"natural", "high-key", "low-key", "silhouette", "neon", "practical", "mixed", "n/a"},
    "time_of_day": {"day", "golden", "blue", "night", "interior", "n/a"},
    "setting": {"interior", "exterior", "virtual", "n/a"},
    "weather": {"clear", "overcast", "rain", "snow", "fog", "n/a"},
    "camera": {"locked", "drift", "handheld", "pan", "tilt", "push", "pull", "zoom", "dolly", "truck", "crane",
               "arc", "whip", "roll", "compound", "unsolved"},
}
# the measured category → blocking.py's named move (references/blocking.md §3a)
TO_BLOCKING = {"locked": "locked", "drift": "drift", "handheld": "static", "pan": "pan", "tilt": "tilt",
               "push": "push_in", "pull": "pull_out", "zoom-in": "zoom_in", "zoom-out": "zoom_out",
               "dolly-in": "dolly_in", "dolly-out": "dolly_out", "truck-left": "truck_left",
               "truck-right": "truck_right", "crane-up": "crane_up", "crane-down": "crane_down",
               "whip": "whip_pan", "roll": "static", "compound": None, "unsolved": None}
ENTITY_ID = re.compile(r"^[A-Z][A-Za-z0-9_]{0,15}$")


def _need():
    try:
        import numpy as np
        import cv2
        return np, cv2
    except ImportError as e:
        raise SystemExit(f"error: shot_graph needs numpy and OpenCV ({e}) — pip install "
                         f"'opencv-python-headless<5' numpy")


def _fb():
    import film_breakdown
    return film_breakdown


def probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,avg_frame_rate,r_frame_rate:format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [{}])[0]

    def rate(s):
        try:
            a, b = (s or "0/1").split("/")
            return float(a) / float(b) if float(b) else 0.0
        except ValueError:
            return 0.0
    fps = rate(st.get("avg_frame_rate")) or rate(st.get("r_frame_rate")) or 25.0
    return {"w": int(st.get("width") or 0), "h": int(st.get("height") or 0), "fps": fps,
            "duration": float((d.get("format") or {}).get("duration") or 0.0)}


def decode(path: str, t0: float, t1: float, info: dict, width: int = 480) -> list:
    """[(time, BGR frame)] between t0 and t1, decoded by ffmpeg with an accurate input seek."""
    np, _ = _need()
    t0 = max(0.0, t0)
    W, H = info["w"], info["h"]
    if not W or not H:
        return []
    w = min(width, W)
    h = max(2, int(round(H * w / W / 2.0)) * 2)
    w -= w % 2
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", path, "-t", f"{max(0.04, t1 - t0):.3f}",
                        "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                       capture_output=True)
    buf = r.stdout or b""
    n = len(buf) // (w * h * 3)
    fps = info["fps"] or 25.0
    return [(t0 + k / fps, np.frombuffer(buf[k * w * h * 3:(k + 1) * w * h * 3], dtype=np.uint8).reshape(h, w, 3))
            for k in range(n)]


def colour_stats(fr) -> dict:
    """Mean colour (CIE L*a*b*), luma, and the SHAPE of the colour distribution with its mean removed.
    ⛔ The shape is cast-invariant on purpose: two angles on one place under a mismatched grade have the
    same distribution moved — a hue histogram calls them different places and hides the very mismatch
    this exists to catch (found on the selftest's own blue-cast wall: correlation −0.09)."""
    np, cv2 = _need()
    lab8 = cv2.cvtColor(fr, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float64)
    lab = np.column_stack([lab8[:, 0] * 100.0 / 255.0, lab8[:, 1] - 128.0, lab8[:, 2] - 128.0])
    mean = lab.mean(axis=0)
    c = lab - mean
    shape = np.concatenate([np.histogram(c[:, 0], bins=32, range=(-50, 50))[0],
                            np.histogram(c[:, 1], bins=32, range=(-40, 40))[0],
                            np.histogram(c[:, 2], bins=32, range=(-40, 40))[0]]).astype(np.float64)
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    return {"luma": float(g.mean()), "lab": [round(float(mean[0]), 2), round(float(mean[1]), 2), round(float(mean[2]), 2)],
            "_shape": shape}


def shape_sim(a, b) -> float:
    """Pearson correlation of two mean-removed colour distributions (1 = the same palette, moved or not)."""
    np, _ = _need()
    sa, sb = a - a.mean(), b - b.mean()
    den = float(np.sqrt((sa * sa).sum() * (sb * sb).sum()))
    return float((sa * sb).sum() / den) if den else 0.0


def _cascade():
    try:
        _, cv2 = _need()
        xml = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        c = cv2.CascadeClassifier(xml) if os.path.isfile(xml) else None
        return None if (c is None or c.empty()) else c
    except Exception:
        return None


def face_pos(fr, casc):
    if casc is None:
        return None
    _, cv2 = _need()
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    faces = casc.detectMultiScale(g, 1.1, 5, minSize=(max(16, g.shape[1] // 30),) * 2)
    if not len(faces):
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return [round((x + w / 2) / g.shape[1], 3), round((y + h / 2) / g.shape[0], 3)]


def motion(fa, fb_, dt: float, static: bool = False) -> dict:
    """Camera and subject motion between two frames dt apart. Camera from an inlier-gated affine (the
    film_breakdown solver), named from the CAMERA's side; subject from dense flow with the camera's
    prediction removed: the mean of the strongest residual vectors, in frame-widths per second of
    SCREEN motion, plus their centroid. `static=True` when the camera is already known to be locked
    (from the whole clip's path): a large moving subject can win the two-frame affine and be taken
    for the camera, so the camera is then held at zero."""
    np, cv2 = _need()
    FB = _fb()
    a = cv2.cvtColor(fa, cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(fb_, cv2.COLOR_BGR2GRAY)
    h, w = a.shape
    M = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]) if static else FB._affine_lk(cv2, np, a, b)[0]
    flow = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    if M is not None:
        px = M[0, 0] * xs + M[0, 1] * ys + M[0, 2] - xs
        py = M[1, 0] * xs + M[1, 1] * ys + M[1, 2] - ys
        cx, cy = w / 2.0, h / 2.0
        pic_dx = (M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx) / w
        pic_dy = (M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy) / h
        cam_method = "held (locked clip)" if static else "affine"
    else:
        px = np.full_like(xs, float(np.median(flow[..., 0])))
        py = np.full_like(ys, float(np.median(flow[..., 1])))
        pic_dx, pic_dy = float(px.flat[0]) / w, float(py.flat[0]) / h
        cam_method = "median-flow"
    rx, ry = flow[..., 0] - px, flow[..., 1] - py
    mag = np.hypot(rx, ry)
    thr = max(float(np.percentile(mag, 92)), 0.6)
    mask = mag >= thr
    cam = {"vx": round(-pic_dx / dt, 4), "vy": round(-pic_dy / dt, 4), "method": cam_method}
    cam["label"] = _cam_label(cam["vx"], cam["vy"])
    subj = None
    if int(mask.sum()) >= max(12, int(0.002 * h * w)):
        subj = {"vx": round(float(rx[mask].mean()) / w / dt, 4), "vy": round(float(ry[mask].mean()) / h / dt, 4),
                "pos": [round(float(xs[mask].mean()) / w, 3), round(float(ys[mask].mean()) / h, 3)],
                "share": round(float(mask.mean()), 4)}
    return {"cam": cam, "subj": subj}


def _cam_label(vx: float, vy: float) -> str:
    parts = []
    if abs(vx) >= 0.03:
        parts.append(f"pan {'right' if vx > 0 else 'left'}")
    if abs(vy) >= 0.03:
        parts.append(f"tilt {'down' if vy > 0 else 'up'}")
    return " + ".join(parts) or "steady"


def decode_fps(path: str, t0: float, t1: float, info: dict, fps: float, width: int = 320) -> list:
    """[(time, BGR)] sampled at `fps` between t0 and t1 (ffmpeg fps filter, accurate seek)."""
    np, _ = _need()
    W, H = info["w"], info["h"]
    if not W or not H or t1 <= t0:
        return []
    w = min(width, W); w -= w % 2
    h = max(2, int(round(H * w / W / 2.0)) * 2)
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t0):.3f}", "-i", path, "-t", f"{t1 - t0:.3f}",
                        "-vf", f"fps={fps:.4f},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                       capture_output=True)
    buf = r.stdout or b""
    n = len(buf) // (w * h * 3)
    return [(t0 + k / fps, np.frombuffer(buf[k * w * h * 3:(k + 1) * w * h * 3], dtype=np.uint8).reshape(h, w, 3))
            for k in range(n)]


def _pair_points(cv2, np, a, b):
    """What the TRACKED POINTS say between two grey frames: (M, inlier residual px, median flow px, points in a,
    points in b, kept mask) or None. film_breakdown's gates (too few inliers or an impossible step is NO ANSWER),
    plus a there-and-back check: each point is tracked a→b and then b→a, and kept only when it lands within
    TH["track_back"] px of where it started.

    ⛔ Without that check a fast object on a weak background moves the CAMERA. It drags the background
    points beside it, the dragged points can outvote the still ones, and a locked shot reads as a pan or
    a whip [measured 2026-11-10 · 16 noise walls with a block crossing in 0.4 s: locked on 5 without the
    check, on 16 with it; the selftest holds four of the eleven that failed · on 14 real stills moved by
    a known amount, both readers were right every time: real picture texture did not need the check].

    ⛔ The points alone are NOT the camera. Corners sit where the detail is, and on a plain background the
    detail is the subject [measured 2026-11-10 · five takes of a hat flicked on a bare wall: 150 to 200 of the
    picked points on the hat, 2 to 10 on the wall, and the fitted move was the hat's in every moving frame
    pair, with this check or without]. _pair_sim asks the rest of the picture."""
    p0 = cv2.goodFeaturesToTrack(a, maxCorners=300, qualityLevel=0.01, minDistance=7)
    if p0 is None or len(p0) < 15:
        return None
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None)
    if p1 is None or st is None or int(st.sum()) < 15:
        return None
    p0r, st_back, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None)
    if p0r is None or st_back is None:
        return None
    miss = np.linalg.norm((p0 - p0r).reshape(-1, 2), axis=1)
    good = (st.ravel() == 1) & (st_back.ravel() == 1) & (miss < TH["track_back"])
    if int(good.sum()) < 15:
        return None
    ga, gb = p0[good].reshape(-1, 2), p1[good].reshape(-1, 2)
    M, inl = cv2.estimateAffinePartial2D(ga, gb, method=cv2.RANSAC, ransacReprojThreshold=3)
    if M is None or inl is None or int(inl.sum()) < 15:
        return None
    hh, ww = a.shape[:2]
    sx = math.hypot(M[0, 0], M[1, 0])
    if abs(M[0, 2]) / ww > 0.5 or abs(M[1, 2]) / hh > 0.5 or not (0.6 <= sx <= 1.6):
        return None
    keep = inl.ravel() == 1
    pred = (ga[keep] @ M[:, :2].T) + M[:, 2]
    res = float(np.median(np.linalg.norm(gb[keep] - pred, axis=1)))
    flow = float(np.median(np.linalg.norm(gb[keep] - ga[keep], axis=1)))
    return M, res, flow, ga, gb, keep


def _rest_votes(cv2, np, a, b, M, ga, gb, keep) -> tuple:
    """What the picture AWAY from the tracked points says about a fitted move M: (blocks that side with "the
    camera held", blocks that side with M, blocks the kept points cover, blocks away from every tracked point,
    blocks in the frame).

    The frame is cut into TH["rest_block"]-px blocks. A block within one block of any tracked point is left
    out, and so is one the move would bring in from outside the frame. Every other block of the low-passed
    picture (a 2 px blur: shading and soft edges count where no corner exists) is compared two ways, frame b
    against frame a as it is ("held") and against frame a moved by M, and votes for the side that explains it
    clearly better (TH["rest_ratio"], TH["rest_margin"]). A block both sides explain equally well does not
    vote: a truly blank wall, or a block something else moved through. So nothing here leans towards "still"."""
    BL = int(TH["rest_block"])
    h, w = a.shape[:2]
    hh, ww = h // BL, w // BL
    if hh < 2 or ww < 2:
        return 0, 0, 0, 0, 0
    occ, sup = np.zeros((hh, ww), np.uint8), np.zeros((hh, ww), np.uint8)
    for pts in (ga, gb):
        iy = np.clip((pts[:, 1] // BL).astype(int), 0, hh - 1)
        ix = np.clip((pts[:, 0] // BL).astype(int), 0, ww - 1)
        occ[iy, ix] = 1
        sup[iy[keep], ix[keep]] = 1
    k3 = np.ones((3, 3), np.uint8)
    occ = cv2.dilate(occ, k3) > 0                       # keep the subject's edges out of the rest
    sup = cv2.morphologyEx(sup, cv2.MORPH_CLOSE, k3) > 0   # the kept points' area: gaps filled, not grown
    af, bf = a.astype(np.float32), b.astype(np.float32)
    Mf = np.asarray(M, dtype=np.float64)

    def blocks(x):
        return x[:hh * BL, :ww * BL].reshape(hh, BL, ww, BL).mean(axis=(1, 3))

    def soft(x):
        return cv2.GaussianBlur(x, (0, 0), 2)
    A, B = soft(af), soft(bf)
    AM = soft(cv2.warpAffine(af, Mf, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
    inside = blocks(cv2.warpAffine(np.ones_like(af), Mf, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)) > 0.999
    e_held, e_move = blocks(np.abs(B - A)), blocks(np.abs(B - AM))
    rest = (~occ) & inside
    still = rest & (e_held < TH["rest_ratio"] * e_move) & (e_move - e_held >= TH["rest_margin"])
    moved = rest & (e_move < TH["rest_ratio"] * e_held) & (e_held - e_move >= TH["rest_margin"])
    return int(still.sum()), int(moved.sum()), int(sup.sum()), int(rest.sum()), hh * ww


def _pair_sim(cv2, np, a, b):
    """The camera between two grey frames: (M, inlier residual px, median flow px, note) or None.
    The tracked points propose a move (_pair_points). The rest of the picture is then asked whether it agrees
    (_rest_votes), and the larger AREA decides, not the larger number of points. note["tag"] is one of:

      held         more blocks side with "the camera held" than stand behind the move (the blocks that side
                   with it plus the blocks the kept points cover). The points sat on a moving subject: this
                   pair reads as no move.
      disputed     the move stands, but the area siding with "held" is over TH["rest_dispute"] of the area
                   behind it.
      unconfirmed  the move stands, but the picture away from the points is TH["rest_large"] of the frame or
                   more and casts no vote: nothing there can tell a moving subject from a moving camera.
      ""           the rest backs the move, or the points cover enough of the frame to stand alone.

    note["points"] keeps what the points alone said, so camera_path can report the other reading.

    ⛔ Do NOT turn this into "prefer still". A block votes only when the two answers differ by a clear margin,
    and a move is overruled only by more voting area than stands behind it [measured 2026-11-10 · 52 local
    clips with the camera move written down by eye: 40 right before, 49 after; the ten locked or held shots
    that read as a move on a plain background all read right now · seven known moves built from 14 real
    stills: 98 of 98 before and after · five known moves (locked, two pans, a tilt, a push) built from stills
    of 14 plain-background clips: 70 of 70, so a real move across a bare wall is still a move · with one
    threshold moved at a time the 52 score 47 to 49: margin 0.15, 0.6, 1.0 → 49, 48, 47; ratio 0.33, 0.67 →
    48, 49; blocks of 12, 24, 32 px → 49, 48, 48].

    ⛔ NOT separated, and no flat picture can separate them: a subject moving in front of a held camera, and a
    camera travelling over a near surface while a far backdrop holds still. Both leave most of the frame
    still. The reader takes the first as its answer and keeps the points' own answer as `points_alone`; the
    plan, or the person who read the shot, settles it [measured · of 366 local clips 41 changed answer; the 29
    outside the 52 were viewed afterwards: 10 better, 9 worse, 10 neither. All 9 worse are ONE kind of shot
    on one set, a camera travelling low over a baseball field under a still roof: they read locked, with
    the right answer as `points_alone`. A tenth take of it is the one clip the 52 lost]."""
    r = _pair_points(cv2, np, a, b)
    if r is None:
        return None
    M, res, flow, ga, gb, keep = r
    n_still, n_moved, n_pts, n_rest, n_all = _rest_votes(cv2, np, a, b, M, ga, gb, keep)
    note = {"tag": "", "points": (M, res, flow), "votes": (n_still, n_moved, n_pts, n_rest, n_all)}
    behind = n_moved + n_pts
    if n_still > behind:
        note["tag"] = "held"
        return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]), 0.0, 0.0, note
    if n_still > n_moved and n_still > TH["rest_dispute"] * behind:
        note["tag"] = "disputed"
    elif n_still == n_moved and n_rest >= TH["rest_large"] * n_all:
        note["tag"] = "unconfirmed"
    return M, res, flow, note


def _pair_travel(M, w: int, h: int) -> float:
    """How far one frame pair's move takes the picture: the centre's shift as a share of the frame, plus |ln scale|."""
    cx, cy = w / 2.0, h / 2.0
    pdx = (M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx) / w
    pdy = (M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy) / h
    return math.hypot(pdx, pdy) + abs(math.log(math.hypot(M[0, 0], M[1, 0]) or 1.0))


def _path_read(rows: list, pairs: int, w: int, h: int) -> dict:
    """One category from the solved frame pairs [(M, residual px, flow px, seconds)] (thresholds TH, [assumed])."""
    vx, vy, zr, rr, par = [], [], [], [], []
    ok = 0
    path_x = path_y = path_z = path_r = 0.0
    for M, res, flow, dt in rows:
        ok += 1
        cx, cy = w / 2.0, h / 2.0
        pdx = (M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx) / w
        pdy = (M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy) / h
        sc = math.hypot(M[0, 0], M[1, 0]) or 1.0
        rot = math.degrees(math.atan2(M[1, 0], M[0, 0]))
        vx.append(-pdx / dt); vy.append(-pdy / dt); zr.append(math.log(sc) / dt); rr.append(rot / dt)
        path_x += -pdx; path_y += -pdy; path_z += math.log(sc); path_r += rot
        if flow >= 1.5:
            par.append(res / flow)
    if ok < 2:
        return {"category": "unsolved", "why": f"{ok} of {pairs} frame pairs passed the inlier gate",
                "blocking_move": None, "pairs_ok": ok, "pairs": pairs}
    sp = [math.hypot(x, y) for x, y in zip(vx, vy)]
    mean_sp = sum(sp) / len(sp)
    peak = max(sp)
    jit = [math.hypot(vx[i] - vx[i - 1], vy[i] - vy[i - 1]) for i in range(1, len(vx))]
    shake = (sorted(jit)[len(jit) // 2] / (mean_sp + 1e-6)) if jit else 0.0
    zmean = sum(zr) / len(zr)
    rmean = sum(rr) / len(rr)
    parallax = (sorted(par)[len(par) // 2] if par else None)
    net = math.hypot(path_x, path_y)
    third = max(1, len(sp) // 3)
    s1, s2, s3 = (sum(sp[:third]) / third, sum(sp[third:-third] or sp) / max(1, len(sp[third:-third] or sp)),
                  sum(sp[-third:]) / third)
    if mean_sp < TH["cam_still"] and abs(zmean) < TH["zoom_rate"] / 2:
        profile = "still"
    elif s1 < 0.6 * s2 and s3 < 0.6 * s2:
        profile = "eases in and out"
    elif s1 < 0.6 * s3:
        profile = "accelerates"
    elif s3 < 0.6 * s1:
        profile = "decelerates (lands)"
    else:
        profile = "constant"
    travels = parallax is not None and parallax >= TH["parallax"]
    trans = mean_sp >= TH["cam_slow"] or net >= 0.06
    zoom = abs(zmean) >= TH["zoom_rate"]
    roll = abs(rmean) >= TH["roll_rate"]
    cat, direction = "compound", ""
    if peak >= TH["whip"]:
        cat = "whip"
    elif not trans and not zoom and not roll:
        cat = "locked" if mean_sp < TH["cam_still"] else ("handheld" if shake >= TH["shake"] else "drift")
    elif shake >= TH["shake"] and net < 0.08 and not zoom:
        cat = "handheld"
    elif zoom and not (trans and net > 0.12):
        cat = ("dolly" if travels else ("push" if zmean > 0 else "pull"))
        direction = "in" if zmean > 0 else "out"
        if cat == "dolly":
            cat = f"dolly-{direction}"
        elif not travels and parallax is not None:
            cat = f"zoom-{direction}"
    elif trans and not zoom:
        horiz = abs(path_x) >= abs(path_y)
        if travels:
            cat = (f"truck-{'right' if path_x > 0 else 'left'}" if horiz else f"crane-{'down' if path_y > 0 else 'up'}")
        else:
            cat = "pan" if horiz else "tilt"
            direction = ("right" if path_x > 0 else "left") if horiz else ("down" if path_y > 0 else "up")
    elif roll and not trans and not zoom:
        cat = "roll"
    base = cat.split("-")[0]
    return {"category": cat, "family": base if base in V["camera"] else "compound", "direction": direction,
            "blocking_move": TO_BLOCKING.get(cat, TO_BLOCKING.get(base)),
            "total": {"pan_W": round(path_x, 3), "tilt_H": round(path_y, 3), "zoom_x": round(math.exp(path_z), 3),
                      "roll_deg": round(path_r, 1)},
            "mean_speed": round(mean_sp, 4), "peak_speed": round(peak, 4), "profile": profile,
            "shake": round(shake, 3), "parallax": (round(parallax, 3) if parallax is not None else None),
            "travels": travels, "pairs_ok": ok, "pairs": pairs,
            "note": ("dolly vs zoom and truck vs pan come from parallax: a flat or distant scene has none, so a "
                     "travelling camera on it reads as a zoom or a pan") if (zoom or trans) else ""}


def camera_path(path: str, a: float, b: float, info: dict) -> dict:
    """The camera tracked through one shot and put in a category (thresholds TH, [assumed]).

    Beside the category: `held_pairs` (frame pairs where the tracked points moved and a larger part of the
    picture held still, read as a moving subject), `points_alone` (what the points by themselves would have
    said, when that differs: the right answer if the camera travels past a far backdrop that holds still),
    and `unsure` with `unsure_why` (at least half the measured travel comes from frame pairs the rest of the
    picture disputes or cannot confirm). A reader of this result treats an unsure move as "look at the clip"."""
    np, cv2 = _need()
    dur = max(0.0, b - a)
    fps = 8.0 if dur <= 15.0 else max(2.0, 120.0 / dur)
    fr = decode_fps(path, a + 0.03, b - 0.03, info, fps, 320)
    if len(fr) < 3:
        return {"category": "unsolved", "why": "too few frames", "blocking_move": None, "held_pairs": 0, "unsure": False}
    g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for _, f in fr]
    h, w = g[0].shape
    rows, alone, tags = [], [], []
    for k in range(1, len(g)):
        dt = fr[k][0] - fr[k - 1][0] or 1.0 / fps
        r = _pair_sim(cv2, np, g[k - 1], g[k])
        if r is None:
            continue
        note = r[3] if len(r) > 3 else {}          # a three-part answer (an older reader swapped in) has no note
        rows.append((r[0], r[1], r[2], dt))
        alone.append(tuple(note.get("points") or r[:3]) + (dt,))
        tags.append(note.get("tag", ""))
    out = _path_read(rows, len(g) - 1, w, h)
    out["held_pairs"] = tags.count("held")
    out["unsure"] = False
    if out["category"] == "unsolved":
        return out
    if out["held_pairs"]:
        pa = _path_read(alone, len(g) - 1, w, h)
        if (pa.get("category"), pa.get("direction")) != (out["category"], out["direction"]):
            out["points_alone"] = {k: pa.get(k) for k in ("category", "family", "direction", "blocking_move")}
    travel = [_pair_travel(M, w, h) for M, _, _, _ in rows]
    doubt = [t for t, tag in zip(travel, tags) if tag in ("disputed", "unconfirmed")]
    if out["category"] != "locked" and sum(travel) > 0 and sum(doubt) >= 0.5 * sum(travel):
        out["unsure"] = True
        out["unsure_why"] = (f"{len(doubt)} of {len(rows)} solved frame pairs carry at least half of the measured travel, and "
                             f"the picture away from the tracked points does not back them: {tags.count('disputed')} "
                             f"disputed (a large part of it held still), {tags.count('unconfirmed')} "
                             f"unconfirmed (half the frame or more is away from the points and says nothing)")
    return out


def light_stats(fr, face) -> dict:
    """Brightness, contrast, key side (on the face when one is found), warm/cool, saturation."""
    np, cv2 = _need()
    lab8 = cv2.cvtColor(fr, cv2.COLOR_BGR2LAB)
    L = lab8[..., 0].astype(np.float64) * 100.0 / 255.0
    b = lab8[..., 2].astype(np.float64) - 128.0
    a = lab8[..., 1].astype(np.float64) - 128.0
    p5, p95 = float(np.percentile(L, 5)), float(np.percentile(L, 95))
    h, w = L.shape
    on = "frame"
    if face:
        fx, fy = int(face[0] * w), int(face[1] * h)
        r = max(6, int(0.06 * w))
        reg = L[max(0, fy - r):fy + r, max(0, fx - r):fx + r]
        if reg.size and reg.shape[1] >= 4:
            left, right = float(reg[:, :reg.shape[1] // 2].mean()), float(reg[:, reg.shape[1] // 2:].mean())
            on = "face"
        else:
            left, right = float(L[:, :w // 3].mean()), float(L[:, -w // 3:].mean())
    else:
        left, right = float(L[:, :w // 3].mean()), float(L[:, -w // 3:].mean())
    top, bot = float(L[:h // 3].mean()), float(L[-h // 3:].mean())
    if right - left >= TH["key_side"]:
        key = "right"
    elif left - right >= TH["key_side"]:
        key = "left"
    elif top - bot >= TH["key_side"] * 2:
        key = "top"
    else:
        key = "even"
    mean = float(L.mean())
    contrast = p95 - p5
    style = ("low-key" if mean < 35 and contrast > 40 else "high-key" if mean > 65 and contrast < 45 else "mid-key")
    bm = float(b.mean())
    temp = "warm" if bm >= TH["warm"] else "cool" if bm <= TH["cool"] else "neutral"
    hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
    return {"L_mean": round(mean, 1), "contrast": round(contrast, 1), "key": style, "key_side": key, "key_on": on,
            "side_diff": round(right - left, 1), "temp": temp, "b_mean": round(bm, 1), "a_mean": round(float(a.mean()), 1),
            "sat": round(float(hsv[..., 1].mean()) / 255.0, 3)}


def composition(fr, face) -> dict:
    """The background as something to rebuild: palette, where the light and the detail sit, focus."""
    np, cv2 = _need()
    small = cv2.resize(fr, (160, max(2, int(fr.shape[0] * 160 / fr.shape[1]))))
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    k = 5
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    cv2.setRNGSeed(5)
    _, lab_lbl, cent = cv2.kmeans(lab, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lab_lbl.ravel(), minlength=k)
    order = np.argsort(-counts)
    pal = []
    for i in order:
        bgr = cv2.cvtColor(np.uint8([[cent[i]]]), cv2.COLOR_LAB2BGR)[0, 0]
        pal.append({"hex": "#%02x%02x%02x" % (int(bgr[2]), int(bgr[1]), int(bgr[0])),
                    "share": round(float(counts[i]) / float(counts.sum()), 3)})
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    h, w = g.shape
    edges = cv2.Canny(g, 60, 160)
    lum, det, sharp = [], [], []
    for r in range(3):
        for c in range(3):
            cell = (slice(r * h // 3, (r + 1) * h // 3), slice(c * w // 3, (c + 1) * w // 3))
            lum.append(round(float(g[cell].mean()) / 255.0, 3))
            det.append(round(float((edges[cell] > 0).mean()), 4))
            sharp.append(float(cv2.Laplacian(g[cell], cv2.CV_64F).var()))
    names = ["top-left", "top", "top-right", "left", "centre", "right", "bottom-left", "bottom", "bottom-right"]
    if face:
        fc = min(2, int(face[1] * 3)) * 3 + min(2, int(face[0] * 3))
    else:
        fc = 4
    border = [sharp[i] for i in range(9) if i != fc]
    dof = (sharp[fc] / (sorted(border)[len(border) // 2] + 1e-6)) if border else 1.0
    return {"palette": pal, "luma_3x3": lum, "detail_3x3": det,
            "brightest": names[max(range(9), key=lambda i: lum[i])],
            "negative_space": [names[i] for i in sorted(range(9), key=lambda i: det[i])[:2]],
            "sharpness": round(float(cv2.Laplacian(g, cv2.CV_64F).var()), 1),
            "dof": ("shallow" if dof >= 3.0 else "deep" if dof <= 1.5 else "medium"), "dof_ratio": round(dof, 2)}


def plate(path: str, a: float, b: float, info: dict, out_png: str) -> bool:
    """A clean background plate: the per-pixel median of up to 15 frames of a held shot."""
    np, cv2 = _need()
    fr = decode_fps(path, a + 0.05, b - 0.05, info, min(8.0, 15.0 / max(0.2, b - a)), 640)
    if len(fr) < 5:
        return False
    med = np.median(np.stack([f for _, f in fr]), axis=0).astype(np.uint8)
    return bool(cv2.imwrite(out_png, med))


def load_cuts(src: str, video: str, info: dict) -> tuple:
    """(shots [(t0, t1)], source note, move/size per shot from a breakdown or None)."""
    FB = _fb()
    if src == "auto":
        dur = info["duration"] or FB.probe_duration(video)
        cuts = [c for c in FB.cut_times(video, 10.0, 480) if c < dur - 0.05]
        shots, _ = FB.shots_from_cuts(cuts, dur, 0.15)
        return shots, "auto (film_breakdown detector, unconfirmed)", None
    if src.endswith(".json"):
        d = json.load(open(src, encoding="utf-8"))
        rows = d.get("rows") or d.get("shots6") or d.get("shots") or []
        if not isinstance(rows, list) or not rows:
            raise SystemExit(f"error: {src} has no rows/shots list")
        shots = [(float(r["start"]), float(r["end"])) for r in rows]
        extra = [{k: r.get(k) for k in ("move", "size", "dx", "dy", "scale", "roll", "per_s", "total_ok")} for r in rows]
        return shots, f"breakdown {os.path.basename(src)}", extra
    times = []
    for line in open(src, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            times.append(float(line))
    dur = info["duration"] or FB.probe_duration(video)
    times = sorted(t for t in times if 0.0 < t < dur)
    edges = [0.0] + times + [dur]
    return [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)], f"cut list {os.path.basename(src)}", None


def join_at(video: str, t: float, info: dict, casc, width: int = 480) -> dict:
    """Everything measured at one cut."""
    np, cv2 = _need()
    win = decode(video, t - 0.42, t + 0.42, info, width)
    if len(win) < 4:
        return {"t": round(t, 3), "unmeasured": "too few frames decoded around the cut"}
    g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.int16) for _, f in win]
    diffs = [float(np.abs(g[k] - g[k - 1]).mean()) for k in range(1, len(g))]
    # the real cut: the biggest frame difference within ±0.2 s of the stated time
    cand = [k for k in range(1, len(win)) if abs(win[k][0] - t) <= 0.2] or list(range(1, len(win)))
    k = max(cand, key=lambda i: diffs[i - 1])
    before, after = win[:k], win[k:]
    if not before or not after:
        return {"t": round(t, 3), "unmeasured": "the cut sits at the edge of the decoded window"}
    fo, fi = before[-1][1], after[0][1]
    co, ci = colour_stats(fo), colour_stats(fi)
    lo, li = light_stats(fo, face_pos(fo, casc)), light_stats(fi, face_pos(fi, casc))
    de = math.sqrt(sum((x - y) ** 2 for x, y in zip(co["lab"], ci["lab"])))
    sim = shape_sim(co["_shape"], ci["_shape"])
    fps = info["fps"] or 25.0
    step = max(2, int(round(0.18 * fps)))
    mb = motion(before[max(0, len(before) - 1 - step)][1], fo, max(1, min(step, len(before) - 1)) / fps) \
        if len(before) >= 2 else None
    ma = motion(fi, after[min(len(after) - 1, step)][1], max(1, min(step, len(after) - 1)) / fps) \
        if len(after) >= 2 else None
    po = face_pos(fo, casc) or ((mb or {}).get("subj") or {}).get("pos")
    pi = face_pos(fi, casc) or ((ma or {}).get("subj") or {}).get("pos")
    pm = ("face" if face_pos(fo, casc) and face_pos(fi, casc) else "moving-region" if (po and pi) else None)
    eye = round(math.hypot(po[0] - pi[0], po[1] - pi[1]) / math.sqrt(2), 3) if (po and pi) else None
    sb, sa = (mb or {}).get("subj"), (ma or {}).get("subj")
    sdir = "n/a"
    if sb and sa and abs(sb["vx"]) >= TH["subject_v"] and abs(sa["vx"]) >= TH["subject_v"]:
        sdir = "kept" if (sb["vx"] > 0) == (sa["vx"] > 0) else "flipped"
    flags = []
    if sim >= TH["alike"] and de >= TH["delta_e_grade"]:
        flags.append(f"colour jump between alike pictures (ΔE {de:.1f})")
    if sim >= TH["alike"] and abs(ci["luma"] - co["luma"]) >= TH["luma_jump"]:
        flags.append(f"exposure jump between alike pictures ({ci['luma'] - co['luma']:+.0f} luma)")
    if sdir == "flipped":
        flags.append("the subject's screen direction flips")
    if sim >= TH["alike"] and {lo["key_side"], li["key_side"]} == {"left", "right"}:
        flags.append(f"the key light changes side between alike pictures ({lo['key_side']} → {li['key_side']})")
    return {"t": round(t, 3), "t_out": round(before[-1][0], 3), "t_in": round(after[0][0], 3),
            "luma_out": round(co["luma"], 1), "luma_in": round(ci["luma"], 1),
            "luma_jump": round(ci["luma"] - co["luma"], 1), "lab_out": co["lab"], "lab_in": ci["lab"],
            "delta_e": round(de, 2), "look_sim": round(sim, 3),
            "look": ("alike" if sim >= TH["alike"] else "unalike" if sim <= TH["unalike"] else "mixed"),
            "cam_before": (mb or {}).get("cam"), "cam_after": (ma or {}).get("cam"),
            "subj_before": sb, "subj_after": sa, "screen_dir": sdir,
            "pos_out": po, "pos_in": pi, "pos_method": pm, "eye_shift": eye,
            "key_side_out": lo["key_side"], "key_side_in": li["key_side"], "temp_out": lo["temp"], "temp_in": li["temp"],
            "eye_jump": (eye is not None and eye >= TH["eye_jump"]), "flags": flags}


def _count(xs) -> dict:
    d = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: -kv[1]))


def measure(video: str, cuts_src: str, label: str, out: str, confirmed: bool = False,
            sheets: bool = True, width: int = 480, plates: bool = False) -> dict:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise SystemExit("error: ffmpeg/ffprobe not on PATH")
    _need()
    info = probe(video)
    shots, src_note, extra = load_cuts(cuts_src, video, info)
    casc = _cascade()
    os.makedirs(out, exist_ok=True)
    rows = []
    for i, (a, b) in enumerate(shots, 1):
        mid = decode(video, (a + b) / 2 - 0.02, (a + b) / 2 + 0.06, info, width)
        r = {"n": i, "start": round(a, 3), "end": round(b, 3), "dur": round(b - a, 3)}
        if mid:
            cs = colour_stats(mid[0][1])
            fp = face_pos(mid[0][1], casc)
            r.update({"luma": round(cs["luma"], 1), "lab": cs["lab"], "face_pos": fp,
                      "light": light_stats(mid[0][1], fp), "composition": composition(mid[0][1], fp)})
        r["camera"] = camera_path(video, a, b, info)
        if plates and r["camera"].get("family") in ("locked", "drift") and (b - a) >= 1.2:
            pp = os.path.join(out, f"PLATE-{label}-S{i:02d}.png")
            if plate(video, a, b, info, pp):
                r["plate"] = os.path.basename(pp)
        if extra and i - 1 < len(extra):
            r.update({k: v for k, v in extra[i - 1].items() if v is not None})
        rows.append(r)
    joins = []
    for i in range(1, len(shots)):
        j = join_at(video, shots[i][0], info, casc, width)
        j.update({"n": i, "from": i, "to": i + 1})
        joins.append(j)
    data = {"label": label, "file": os.path.abspath(video), "duration": round(info["duration"], 3),
            "fps": round(info["fps"], 3), "w": info["w"], "h": info["h"], "cuts_source": src_note,
            "cuts_confirmed": bool(confirmed), "faces_available": casc is not None,
            "camera_categories": _count(r.get("camera", {}).get("category") for r in rows),
            "thresholds": TH, "thresholds_tag": TH_TAG, "shots": rows, "cuts": joins, "sheets": {}}
    if sheets:
        FB = _fb()
        sh = []
        for k in range(0, len(rows), 24):
            p = os.path.join(out, f"SHOTS-{label}-{k // 24 + 1:02d}.png")
            if FB.sheet(video, [((r["start"] + r["end"]) / 2, f"S{r['n']} {r['dur']:.1f}s") for r in rows[k:k + 24]],
                        p, cols=6):
                sh.append(os.path.basename(p))
        pr = []
        for k in range(0, len(joins), 6):
            stamps = []
            for j in joins[k:k + 6]:
                if "t_out" in j:
                    stamps += [(j["t_out"], f"C{j['n']} out S{j['from']}"), (j["t_in"], f"C{j['n']} in S{j['to']}")]
            p = os.path.join(out, f"PAIRS-{label}-{k // 6 + 1:02d}.png")
            if stamps and FB.sheet(video, stamps, p, cols=2):
                pr.append(os.path.basename(p))
        data["sheets"] = {"shots": sh, "pairs": pr}
    with open(os.path.join(out, f"JOINS-{label}.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    return data


# ---- the read ------------------------------------------------------------------------------------
def template(joins_path: str, out_path: str | None = None) -> str:
    d = json.load(open(joins_path, encoding="utf-8"))
    form = {"film": d["label"], "joins": os.path.basename(joins_path), "reader": "", "date": "",
            "entities": [{"id": "A", "kind": "character", "desc": "own words — who this is, what they wear"},
                         {"id": "L1", "kind": "location", "desc": "own words", "setting": "", "place": "", "era": "",
                          "weather": "", "materials": "", "layers": {"fg": "", "mid": "", "bg": ""},
                          "distinctive": "", "recreate": "", "variants": ["", "", ""]}],
            "shots": [{"n": r["n"], "size": "", "angle": "", "location": "", "characters": [],
                       "props": [], "light_key": "", "light_quality": "", "light_style": "", "time_of_day": "",
                       "camera": "", "notes": "",
                       "_measured": {"camera": (r.get("camera") or {}).get("category"),
                                     **({"camera_points_alone": r["camera"]["points_alone"].get("category")}
                                        if (r.get("camera") or {}).get("points_alone") else {}),
                                     "light": {k: (r.get("light") or {}).get(k) for k in ("key", "key_side", "temp")},
                                     "dof": (r.get("composition") or {}).get("dof")}} for r in d["shots"]],
            "cuts": [{"n": j["n"], "from": j["from"], "to": j["to"], "relation": "", "match": [],
                      "axis": "", "screen_direction": "", "eyeline": "", "carries": [], "changes": [],
                      "continuity_error": "", "notes": "",
                      "_measured": {k: j.get(k) for k in ("delta_e", "look", "screen_dir", "eye_shift", "flags")}}
                     for j in d["cuts"]],
            "_how": ("characters: [{id, screen, depth, gaze, facing, motion, expr, intensity, turn}] · props: "
                     "[{id, holder, state}] · camera: blank to accept the measured category, or the category you see · "
                     "vocabulary in shot_graph.py V and references/shot-relationships.md §3. Own words only — "
                     "never dialogue, captions or on-screen text. `_measured` is the pixel read: look again "
                     "where you disagree with it.")}
    p = out_path or os.path.join(os.path.dirname(joins_path), f"READ-{d['label']}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(form, fh, indent=1, ensure_ascii=False)
    return p


def _joins_for(read: dict, read_path: str) -> dict:
    jp = os.path.join(os.path.dirname(os.path.abspath(read_path)), read.get("joins") or f"JOINS-{read.get('film')}.json")
    if not os.path.isfile(jp):
        raise SystemExit(f"error: {jp} not found — the read is checked against its measurements")
    return json.load(open(jp, encoding="utf-8"))


def _camera_read_vs_measured(read: str | None, cam: dict) -> str | None:
    """A read camera against the measured one: a "look again" line, or None when they agree. When the reader
    kept two answers (camera_path `points_alone`: the tracked points moved while a larger part of the picture
    held still), a read that matches EITHER is taken: the person who saw the shot settles which is the camera."""
    zoomy = {"push", "pull", "zoom", "dolly"}
    mcam = cam.get("family")
    alt = (cam.get("points_alone") or {}).get("family")
    if not (read and mcam) or mcam in ("unsolved", "compound") or read == mcam or {read, mcam} <= zoomy:
        return None
    if alt and (read == alt or {read, alt} <= zoomy):
        return None
    return (f"read camera {read!r}, measured {mcam!r}" + (f" (the tracked points alone: {alt!r})" if alt else "")
            + " — look again (parallax can hide a dolly)")


def validate(read_path: str) -> tuple:
    """(errors, warnings). Errors: the form is not filled to the vocabulary. Warnings: the read and the
    pixels disagree — look again, the measurement can be wrong too."""
    rd = json.load(open(read_path, encoding="utf-8"))
    jd = _joins_for(rd, read_path)
    E, W = [], []
    ents = rd.get("entities") or []
    ids = {}
    for e in ents:
        i = str(e.get("id") or "")
        if not ENTITY_ID.match(i):
            E.append(f"entity id {i!r} — a capital letter, then letters/digits (A, B, P1, L2)")
        elif i in ids:
            E.append(f"entity {i} defined twice")
        if e.get("kind") not in V["kind"]:
            E.append(f"entity {i}: kind {e.get('kind')!r} not in {sorted(V['kind'])}")
        if not str(e.get("desc") or "").strip() or "own words —" in str(e.get("desc")):
            E.append(f"entity {i}: no description")
        ids[i] = e.get("kind")
        if e.get("kind") == "location":
            if e.get("setting") not in V["setting"]:
                E.append(f"location {i}: setting {e.get('setting')!r} not in {sorted(V['setting'])}")
            if e.get("weather") and e.get("weather") not in V["weather"]:
                E.append(f"location {i}: weather {e.get('weather')!r} not in {sorted(V['weather'])}")
            lay = e.get("layers") or {}
            if not str(lay.get("bg") or "").strip():
                E.append(f"location {i}: layers.bg empty — what is behind the action is what a recreation rebuilds")
            if not str(e.get("recreate") or "").strip():
                E.append(f"location {i}: recreate empty — how to rebuild it (materials, light, what must survive)")
            vs = [v for v in (e.get("variants") or []) if str(v).strip()]
            if len(vs) < 3:
                W.append(f"location {i}: {len(vs)} variant(s) — three or more alternative worlds that keep its job in "
                         f"the frame make the replicate path creative, not a copy")
    shots, cuts = rd.get("shots") or [], rd.get("cuts") or []
    if len(shots) != len(jd["shots"]):
        E.append(f"{len(shots)} shots read, {len(jd['shots'])} measured — the read follows the measured cut list")
    if len(cuts) != len(jd["cuts"]):
        E.append(f"{len(cuts)} cuts read, {len(jd['cuts'])} measured")
    for s in shots:
        n = s.get("n")
        for k in ("size", "angle", "light_key", "light_quality", "light_style", "time_of_day"):
            if s.get(k) not in V[k]:
                E.append(f"S{n}: {k} {s.get(k)!r} not in {sorted(V[k])}")
        if s.get("camera") and s["camera"] not in V["camera"]:
            E.append(f"S{n}: camera {s.get('camera')!r} not in {sorted(V['camera'])} (blank accepts the measured one)")
        mrow = jd["shots"][n - 1] if isinstance(n, int) and 0 < n <= len(jd["shots"]) else {}
        cw = _camera_read_vs_measured(s.get("camera"), mrow.get("camera") or {})
        if cw:
            W.append(f"S{n}: {cw}")
        ml = (mrow.get("light") or {}).get("key_side")
        if s.get("light_key") in ("left", "right") and ml in ("left", "right") and s["light_key"] != ml:
            W.append(f"S{n}: read key light {s['light_key']}, measured {ml} (on the {(mrow.get('light') or {}).get('key_on')}) "
                     f"— look again; screen-left/right is from the camera")
        loc = s.get("location")
        if loc and ids.get(loc) != "location":
            E.append(f"S{n}: location {loc!r} is not a location entity")
        if not loc and s.get("size") != "insert" and not any(ids.get(c.get("id")) == "graphic" for c in s.get("characters") or []):
            E.append(f"S{n}: no location — every shot but an insert or a graphic is somewhere")
        for c in s.get("characters") or []:
            if ids.get(c.get("id")) not in ("character", "animal", "group", "graphic"):
                E.append(f"S{n}: {c.get('id')!r} is not a character/animal/group entity")
            for k in ("screen", "depth", "gaze", "facing", "motion", "expr", "intensity"):
                if c.get(k) not in V[k]:
                    E.append(f"S{n} {c.get('id')}: {k} {c.get(k)!r} not in {sorted(V[k], key=str)}")
            t = c.get("turn") or "none"
            if t.split(":")[0] not in V["emotion_turn"]:
                E.append(f"S{n} {c.get('id')}: turn {t!r} — none, or early:/late:/through: <what changes>")
        for p in s.get("props") or []:
            if ids.get(p.get("id")) not in ("prop", "product", "vehicle"):
                E.append(f"S{n}: {p.get('id')!r} is not a prop/product/vehicle entity")
            h = p.get("holder") or "none"
            if h != "none" and ids.get(h) not in ("character", "animal"):
                E.append(f"S{n}: {p.get('id')} held by {h!r}, which is not a character")
    mj = {j["n"]: j for j in jd["cuts"]}
    for c in cuts:
        n = c.get("n")
        for k in ("relation", "axis", "screen_direction", "eyeline"):
            if c.get(k) not in V[k]:
                E.append(f"C{n}: {k} {c.get(k)!r} not in {sorted(V[k])}")
        m = c.get("match") or []
        if not m or any(x not in V["match"] for x in m):
            E.append(f"C{n}: match {m!r} — a list from {sorted(V['match'])} (['none'] when nothing matches)")
        for x in c.get("carries") or []:
            if x not in ids and x not in V["carries_tokens"]:
                E.append(f"C{n}: carries {x!r} — an entity id or one of {sorted(V['carries_tokens'])}")
        ch = c.get("changes") or []
        if not ch or any(x not in V["changes"] for x in ch):
            E.append(f"C{n}: changes {ch!r} — a list from {sorted(V['changes'])}")
        j = mj.get(n) or {}
        if j.get("screen_dir") == "flipped" and c.get("screen_direction") == "kept":
            W.append(f"C{n}: read 'screen direction kept', the pixels say the subject's direction flips — look again")
        if j.get("screen_dir") == "kept" and c.get("screen_direction") == "flipped":
            W.append(f"C{n}: read 'flipped', the pixels say kept — look again")
        if c.get("relation") == "same-scene" and j.get("look") == "unalike" and (j.get("delta_e") or 0) > 20:
            W.append(f"C{n}: read same-scene, the two pictures share almost no colour (ΔE {j.get('delta_e')}) — look again")
        if c.get("relation") == "new-scene" and j.get("look") == "alike" and (j.get("delta_e") or 99) < 3:
            W.append(f"C{n}: read new-scene, the two pictures are nearly identical in colour — a return or the same place?")
        if "action" in m and not (j.get("subj_before") or j.get("subj_after")):
            W.append(f"C{n}: read match on action, the pixels found nothing moving at the join")
        for fl in j.get("flags") or []:
            if not c.get("continuity_error") and c.get("relation") in ("same-scene", "return"):
                W.append(f"C{n}: measured '{fl}' on a {c.get('relation')} cut and the read records no continuity error")
    return E, W


def merge(read_path: str) -> dict:
    E, Wn = validate(read_path)
    if E:
        raise SystemExit("error: the read does not validate:\n  - " + "\n  - ".join(E[:30]))
    rd = json.load(open(read_path, encoding="utf-8"))
    jd = _joins_for(rd, read_path)
    ents = {e["id"]: dict(e, shots=[], first=None, last=None, positions=[]) for e in rd["entities"]}
    for s, m in zip(rd["shots"], jd["shots"]):
        here = [c["id"] for c in s.get("characters") or []] + [p["id"] for p in s.get("props") or []]
        if s.get("location"):
            here.append(s["location"])
        for i in here:
            if i in ents:
                ents[i]["shots"].append(s["n"])
        for c in s.get("characters") or []:
            if c.get("id") in ents:
                ents[c["id"]]["positions"].append({"shot": s["n"], "screen": c.get("screen"), "depth": c.get("depth")})
    for e in ents.values():
        e["first"], e["last"] = (min(e["shots"]), max(e["shots"])) if e["shots"] else (None, None)
    cuts = []
    for c, j in zip(rd["cuts"], jd["cuts"]):
        cuts.append({**{k: v for k, v in c.items() if not k.startswith("_")},
                     "measured": {k: j.get(k) for k in ("t", "delta_e", "luma_jump", "look", "screen_dir",
                                                         "eye_shift", "eye_jump", "cam_before", "cam_after", "flags")}})
    n = len(cuts) or 1
    rel = {}
    for c in cuts:
        rel[c["relation"]] = rel.get(c["relation"], 0) + 1
    mt = {}
    for c in cuts:
        for x in c.get("match") or []:
            mt[x] = mt.get(x, 0) + 1
    same = [c for c in cuts if c["relation"] in ("same-scene", "return")]
    des = sorted(c["measured"]["delta_e"] for c in same if c["measured"].get("delta_e") is not None)
    eyes = sorted(c["measured"]["eye_shift"] for c in cuts if c["measured"].get("eye_shift") is not None)

    def pct(xs, q):
        return round(xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))], 2) if xs else None
    arcs = {}
    for s_ in rd["shots"]:
        for c_ in s_.get("characters") or []:
            arcs.setdefault(c_["id"], []).append(f"S{s_['n']} {c_.get('expr')}{c_.get('intensity')}"
                                                 + ("" if (c_.get("turn") or "none") == "none" else f"→{c_.get('turn')}"))
    light_breaks = []
    for c_ in cuts:
        a_, b_ = rd["shots"][c_["from"] - 1], rd["shots"][c_["to"] - 1]
        if c_["relation"] in ("same-scene", "return") and a_.get("location") == b_.get("location") \
                and {a_.get("light_key"), b_.get("light_key")} == {"left", "right"}:
            light_breaks.append(f"C{c_['n']}: key light {a_.get('light_key')} → {b_.get('light_key')} inside {a_.get('location')}")
    cams = {}
    for s_, m_ in zip(rd["shots"], jd["shots"]):
        k_ = s_.get("camera") or (m_.get("camera") or {}).get("family") or "unsolved"
        cams[k_] = cams.get(k_, 0) + 1
    backgrounds = []
    for e in rd["entities"]:
        if e.get("kind") != "location":
            continue
        sh_ = [m_ for s_, m_ in zip(rd["shots"], jd["shots"]) if s_.get("location") == e["id"]]
        pal = {}
        for m_ in sh_:
            for p_ in ((m_.get("composition") or {}).get("palette") or [])[:3]:
                pal[p_["hex"]] = pal.get(p_["hex"], 0) + p_["share"]
        backgrounds.append({"id": e["id"], "shots": [m_["n"] for m_ in sh_], "setting": e.get("setting"),
                            "place": e.get("place"), "layers": e.get("layers"), "recreate": e.get("recreate"),
                            "variants": e.get("variants"),
                            "palette": [h for h, _ in sorted(pal.items(), key=lambda kv: -kv[1])[:5]],
                            "keys": _count((m_.get("light") or {}).get("key") for m_ in sh_),
                            "temps": _count((m_.get("light") or {}).get("temp") for m_ in sh_),
                            "plates": [m_["plate"] for m_ in sh_ if m_.get("plate")]})
    summary = {"shots": len(rd["shots"]), "cuts": len(cuts), "cuts_confirmed": jd.get("cuts_confirmed"),
               "relation_pct": {k: round(100.0 * v / n, 1) for k, v in sorted(rel.items())},
               "match_pct": {k: round(100.0 * v / n, 1) for k, v in sorted(mt.items())},
               "axis_crossed": sum(1 for c in cuts if c["axis"] == "crossed"),
               "screen_flips_read": sum(1 for c in cuts if c["screen_direction"] == "flipped"),
               "screen_flips_measured": sum(1 for c in cuts if c["measured"].get("screen_dir") == "flipped"),
               "eyeline_mismatched": sum(1 for c in cuts if c["eyeline"] == "mismatched"),
               "continuity_errors": sum(1 for c in cuts if (c.get("continuity_error") or "").strip()),
               "carried_per_cut": round(sum(len(c.get("carries") or []) for c in cuts) / n, 2),
               "returns": rel.get("return", 0),
               "delta_e_same_scene_median": pct(des, 0.5), "delta_e_same_scene_p90": pct(des, 0.9),
               "eye_shift_median": pct(eyes, 0.5),
               "characters": {i: len(e["shots"]) for i, e in ents.items() if e["kind"] == "character"},
               "locations": {i: len(e["shots"]) for i, e in ents.items() if e["kind"] == "location"},
               "read_vs_pixels_warnings": len(Wn),
               "camera_pct": {k: round(100.0 * v / max(1, len(rd["shots"])), 1) for k, v in sorted(cams.items())},
               "light_breaks": light_breaks}
    out = {"film": rd["film"], "reader": rd.get("reader"), "date": rd.get("date"), "source": jd.get("file"),
           "duration": jd.get("duration"), "fps": jd.get("fps"), "aspect": [jd.get("w"), jd.get("h")],
           "thresholds": jd.get("thresholds"), "thresholds_tag": jd.get("thresholds_tag"),
           "entities": list(ents.values()),
           "shots": [{**{k: v for k, v in s.items()}, "measured": m} for s, m in zip(rd["shots"], jd["shots"])],
           "cuts": cuts, "summary": summary, "warnings": Wn, "emotion_arcs": arcs, "backgrounds": backgrounds}
    base = os.path.dirname(os.path.abspath(read_path))
    with open(os.path.join(base, f"SHOTGRAPH-{rd['film']}.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(base, f"SHOTGRAPH-{rd['film']}.md"), "w", encoding="utf-8") as fh:
        fh.write(render_md(out))
    return out


def render_md(g: dict) -> str:
    s = g["summary"]
    L = [f"# Shot graph — {g['film']}", "",
         f"{s['shots']} shots · {s['cuts']} cuts · cut list "
         + ("CONFIRMED on strips" if s.get("cuts_confirmed") else "⚠ NOT confirmed (a detector draft)")
         + f" · read by {g.get('reader') or '?'} {g.get('date') or ''}", "",
         "## Entities", "", "| id | kind | description | shots | first–last |", "|---|---|---|---|---|"]
    for e in g["entities"]:
        L.append(f"| {e['id']} | {e['kind']} | {e.get('desc', '')} | {len(e['shots'])} | "
                 f"{e['first'] or '-'}–{e['last'] or '-'} |")
    L += ["", "## Shots", "", "| S | dur | size | angle | move (measured) | location | characters (screen · gaze · motion) | props |",
          "|---|---|---|---|---|---|---|---|"]
    for sh in g["shots"]:
        m = sh.get("measured") or {}
        chars = "; ".join(f"{c['id']} {c.get('screen')} · {c.get('gaze')} · {c.get('motion')}" for c in sh.get("characters") or [])
        props = "; ".join(f"{p['id']}" + (f" ({p.get('holder')})" if p.get("holder") not in (None, "none") else "")
                          for p in sh.get("props") or [])
        L.append(f"| {sh['n']} | {m.get('dur', '')} | {sh.get('size')} | {sh.get('angle')} | {m.get('move', '—')} | "
                 f"{sh.get('location') or '—'} | {chars or '—'} | {props or '—'} |")
    L += ["", "## Cuts", "",
          "| C | S→S | relation | match | axis | screen dir (read/px) | eyeline | carries | changes | ΔE | eye shift | flags |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in g["cuts"]:
        m = c["measured"]
        L.append(f"| {c['n']} | {c['from']}→{c['to']} | {c['relation']} | {', '.join(c.get('match') or [])} | {c['axis']} | "
                 f"{c['screen_direction']}/{m.get('screen_dir')} | {c['eyeline']} | {', '.join(c.get('carries') or []) or '—'} | "
                 f"{', '.join(c.get('changes') or [])} | {m.get('delta_e')} | {m.get('eye_shift')} | "
                 f"{'; '.join(m.get('flags') or []) or (c.get('continuity_error') or '')} |")
    if g.get("emotion_arcs"):
        L += ["", "## Emotion arcs", ""] + [f"- **{k}**: " + " · ".join(v) for k, v in g["emotion_arcs"].items()]
    L += ["", "## Camera, tracked", "", "| S | category | → blocking move | total | speed (mean/peak W/s) | profile | shake | parallax |",
          "|---|---|---|---|---|---|---|---|"]
    for sh in g["shots"]:
        c = (sh.get("measured") or {}).get("camera") or {}
        t = c.get("total") or {}
        L.append(f"| {sh['n']} | {sh.get('camera') or c.get('category')} | {c.get('blocking_move') or '—'} | "
                 f"pan {t.get('pan_W')} · tilt {t.get('tilt_H')} · ×{t.get('zoom_x')} · roll {t.get('roll_deg')} | "
                 f"{c.get('mean_speed')}/{c.get('peak_speed')} | {c.get('profile')} | {c.get('shake')} | {c.get('parallax')} |")
    L += ["", "## Light, per shot", "", "| S | key (px) | side (px · read) | quality · style · time (read) | temp | contrast | sat |",
          "|---|---|---|---|---|---|---|"]
    for sh in g["shots"]:
        li = (sh.get("measured") or {}).get("light") or {}
        L.append(f"| {sh['n']} | {li.get('key')} | {li.get('key_side')} · {sh.get('light_key')} | {sh.get('light_quality')} · "
                 f"{sh.get('light_style')} · {sh.get('time_of_day')} | {li.get('temp')} | {li.get('contrast')} | {li.get('sat')} |")
    if g.get("backgrounds"):
        L += ["", "## Backgrounds — for recreation", ""]
        for b in g["backgrounds"]:
            lay = b.get("layers") or {}
            L += [f"### {b['id']} — {b.get('place') or ''} ({b.get('setting')})", "",
                  f"- shots: {', '.join(map(str, b['shots']))} · palette {' '.join(b['palette'])} · light {b['keys']} · {b['temps']}",
                  f"- layers: fg {lay.get('fg') or '—'} · mid {lay.get('mid') or '—'} · bg {lay.get('bg') or '—'}",
                  f"- rebuild: {b.get('recreate') or '—'}"]
            for v_ in [v for v in (b.get("variants") or []) if str(v).strip()]:
                L.append(f"- variant: {v_}")
            if b.get("plates"):
                L.append(f"- plates: {', '.join(b['plates'])}")
            L.append("")
    L += ["", "## Summary", ""] + [f"- {k}: {v}" for k, v in s.items()]
    L += ["", f"Thresholds {g.get('thresholds_tag')}: {g.get('thresholds')}"]
    if g.get("warnings"):
        L += ["", "## Read vs pixels — look again", ""] + [f"- {w}" for w in g["warnings"]]
    return "\n".join(L) + "\n"


def qa(video: str, cuts_src: str, label: str, out: str, confirmed: bool) -> int:
    d = measure(video, cuts_src, label, out, confirmed)
    fl = [(j["n"], f) for j in d["cuts"] for f in (j.get("flags") or [])]
    eye = [j["n"] for j in d["cuts"] if j.get("eye_jump")]
    print(f"SHOT-GRAPH QA · {label} · {len(d['shots'])} shots · {len(d['cuts'])} cuts · cut list "
          + ("confirmed" if confirmed else "⚠ NOT confirmed"))
    for n, f in fl:
        print(f"  ⛔ C{n}: {f}")
    if eye:
        print(f"  ~ the eye has to jump across C{', C'.join(map(str, eye))} (subject shift ≥ {TH['eye_jump']} of the "
              f"diagonal) — fine on a new scene, a stumble inside one")
    print(f"  pair sheets: {', '.join(d['sheets'].get('pairs') or []) or 'none'} — read them for the drift a pixel "
          f"cannot see: the same face, the same clothes, the same product, the prop in the same hand")
    print(f"  thresholds {TH_TAG}")
    return 1 if fl else 0


# ---- selftest ------------------------------------------------------------------------------------
def _synth(path: str) -> list:
    """Three shots, 24 fps, 2 s each: (1) a textured wall, a red block moving right; (2) the same wall
    with a blue cast, the block still moving right — a colour jump between alike pictures, direction
    kept; (3) a different place, the block moving LEFT — a new look and a flipped screen direction."""
    np, cv2 = _need()
    W, H, fps = 320, 180, 24
    rng = np.random.default_rng(7)
    wide = cv2.GaussianBlur(rng.integers(60, 200, (H, W * 2, 3)).astype(np.uint8), (5, 5), 0)
    wall = wide[:, :W].copy()
    gx = np.linspace(0, 1, W)[None, :, None]
    other = (np.array([30, 140, 60]) + gx * np.array([20, 60, 10])).repeat(H, axis=0).astype(np.uint8)
    for yy in range(0, H, 36):
        other[yy:yy + 6] = (200, 230, 210)
    frames = []
    for k in range(fps * 10):
        t = k / fps
        if t >= 6.0:
            # (4) the camera pans RIGHT across the wide wall: the window slides right, the picture left
            # (5) the camera pushes in ×1.25 on the wall's centre: no parallax, so it reads as a zoom
            if t < 8.0:
                x0 = int((t - 6.0) * 0.15 * W)
                frames.append(wide[:, x0:x0 + W].copy())
            else:
                z = 1.0 + 0.25 * (t - 8.0) / 2.0
                M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
                frames.append(cv2.warpAffine(wall, M, (W, H), borderMode=cv2.BORDER_REFLECT))
            continue
        if t < 2.0:
            bg, x = wall.copy(), 40 + t * 0.20 * W
        elif t < 4.0:
            bg = (wall.astype(np.int16) + np.array([40, -10, -25])).clip(0, 255).astype(np.uint8)
            x = 40 + t * 0.20 * W
        else:
            bg, x = other.copy(), 160 - (t - 4.0) * 0.15 * W
        cv2.rectangle(bg, (int(x) - 14, 70), (int(x) + 14, 110), (20, 20, 230), -1)
        frames.append(bg)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                          "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "mpeg4", "-q:v", "2", path],
                         stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    return [2.0, 4.0, 6.0, 8.0]


def _synth_plain(path: str, mode: str, seed: int = 11) -> None:
    """A detailed subject in front of a PLAIN wall, 320x180, 24 fps, 2 s: every corner is on the subject.
      "subject"  the camera is locked; the subject crosses a softly lit wall (shading and one soft shadow)
      "pan"      the camera pans right at 0.25 W/s along the same wall; the subject is fixed to the wall
      "blank"    as "subject", with a smaller subject on a wall of one flat grey: no picture away from the subject"""
    np, cv2 = _need()
    W, H, fps = 320, 180, 24
    rng = np.random.default_rng(seed)
    sw, sh = (70, 60) if mode == "blank" else (110, 100)
    tex = cv2.GaussianBlur(rng.integers(40, 220, (sh, sw, 3)).astype(np.uint8), (5, 5), 0)
    xs, ys = np.meshgrid(np.arange(2 * W, dtype=np.float32), np.arange(H, dtype=np.float32))
    lit = 150.0 - 70.0 * (((xs - 0.8 * W) / (0.9 * W)) ** 2 + ((ys - 0.4 * H) / (0.9 * H)) ** 2)
    lit -= 35.0 * np.exp(-(((xs - 1.2 * W) / 40.0) ** 2 + ((ys - 0.7 * H) / 30.0) ** 2))
    wall = np.repeat(np.clip(lit, 30, 220)[..., None], 3, axis=2).astype(np.uint8)
    if mode == "blank":
        wall[:] = 128
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                          "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "mpeg4", "-q:v", "2", path],
                         stdin=subprocess.PIPE)
    for k in range(fps * 2):
        t = k / fps
        x0, sx = (int(t * 0.25 * W), 200) if mode == "pan" else (W // 2, W // 2 + 20 + int(t * 0.25 * W))
        canvas = wall.copy()
        canvas[40:40 + sh, sx:sx + sw] = tex
        p.stdin.write(canvas[:, x0:x0 + W].tobytes())
    p.stdin.close(); p.wait()


def selftest() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if (detail and not cond) else ""))
    print("shot_graph.py selftest")
    check("a camera move is named from the camera's side", _cam_label(0.2, 0.0) == "pan right"
          and _cam_label(0.0, -0.1) == "tilt up" and _cam_label(0.0, 0.0) == "steady")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("  (ffmpeg missing — the video legs are skipped)")
        return 0 if ok else 1
    try:
        _need()
    except SystemExit:
        print("  (OpenCV missing — the video legs are skipped)")
        return 0 if ok else 1
    with tempfile.TemporaryDirectory() as td:
        v = os.path.join(td, "synth.mp4")
        cuts = _synth(v)
        cl = os.path.join(td, "cuts.txt"); open(cl, "w").write("# confirmed by construction\n2.0\n4.0\n6.0\n8.0\n")
        d = measure(v, cl, "synth", td, confirmed=True, plates=True)
        check("five shots and four cuts from the cut list", len(d["shots"]) == 5 and len(d["cuts"]) == 4, str(len(d["cuts"])))
        c1, c2 = d["cuts"][:2]
        s1, s4, s5 = d["shots"][0], d["shots"][3], d["shots"][4]
        check("S1 (static wall, moving block): the CAMERA reads locked", s1["camera"]["category"] == "locked",
              json.dumps(s1["camera"])[:200])
        check("S4: the camera pans RIGHT, maps to blocking `pan`", s4["camera"]["category"] == "pan"
              and s4["camera"]["direction"] == "right" and s4["camera"]["blocking_move"] == "pan",
              json.dumps(s4["camera"])[:240])
        check("S5: a push with no parallax reads as a zoom in", s5["camera"]["category"] in ("zoom-in", "push")
              and s5["camera"]["total"]["zoom_x"] > 1.15, json.dumps(s5["camera"])[:240])
        check("S4's speed profile is constant", s4["camera"]["profile"] == "constant", s4["camera"]["profile"])
        # A fast bright object must not move the camera (the there-and-back check in _pair_sim). Four of the
        # eleven noise walls, of 16 tried, on which the locked shot read as a pan or a whip before the check.
        import action_points as AP
        fast = []
        for seed in (1, 3, 6, 7):
            fc = os.path.join(td, f"fast{seed}.mp4")
            AP._synth(fc, seed=seed)
            fi = probe(fc)
            fast.append((seed, camera_path(fc, 0.0, fi["duration"], fi).get("category")))
        check("a locked camera stays locked while a bright block crosses the frame in 0.4 s (four noise walls)",
              all(c == "locked" for _, c in fast), str(fast))
        # On a plain wall every corner is on the subject, so the tracked points follow the subject, not the
        # camera. The picture away from the points decides (_rest_votes), by area, with no lean towards still.
        plain = {}
        for mode in ("subject", "pan", "blank"):
            pc = os.path.join(td, f"plain_{mode}.mp4")
            _synth_plain(pc, mode)
            pi = probe(pc)
            plain[mode] = camera_path(pc, 0.0, pi["duration"], pi)
        ps, pp, pb = plain["subject"], plain["pan"], plain["blank"]
        check("a locked camera reads locked while a detailed subject crosses a bare, softly lit wall, and the "
              "points' own answer (a pan) is kept beside it", ps["category"] == "locked" and ps["held_pairs"] >= 10
              and (ps.get("points_alone") or {}).get("category") == "pan" and not ps["unsure"], json.dumps(ps)[:400])
        check("the same wall and subject under a real pan still read as a pan right, with no frame pair overruled",
              pp["category"] == "pan" and pp["direction"] == "right" and pp["held_pairs"] == 0 and not pp["unsure"],
              json.dumps(pp)[:400])
        check("on a wall of one flat grey nothing can place the camera: the move is kept and marked unsure",
              pb["category"] not in ("locked", "drift") and pb["held_pairs"] == 0 and pb["unsure"]
              and "unconfirmed" in pb.get("unsure_why", ""), json.dumps(pb)[:400])
        global _pair_sim
        whole = _pair_sim
        try:
            _pair_sim = lambda cv2, np, a, b: (lambda r: None if r is None else r[:3])(whole(cv2, np, a, b))
            old3 = camera_path(os.path.join(td, "plain_pan.mp4"), 0.0, 2.0, probe(os.path.join(td, "plain_pan.mp4")))
        finally:
            _pair_sim = whole
        check("a reader that answers in three parts (an older one swapped in for a comparison) is still read",
              old3["category"] == "pan" and old3["held_pairs"] == 0, json.dumps(old3)[:300])
        two = {"family": "locked", "points_alone": {"family": "dolly"}}
        check("a read camera is checked against both answers when the reader kept two: either one settles it",
              _camera_read_vs_measured("locked", two) is None and _camera_read_vs_measured("push", two) is None
              and "points alone" in (_camera_read_vs_measured("pan", two) or "")
              and "look again" in (_camera_read_vs_measured("pan", {"family": "locked"}) or "")
              and _camera_read_vs_measured("pan", {"family": "pan"}) is None)
        check("per-shot light and composition are measured (a 5-colour palette, 3×3 maps)",
              s1["light"]["key"] in ("low-key", "mid-key", "high-key") and len(s1["composition"]["palette"]) == 5
              and len(s1["composition"]["luma_3x3"]) == 9)
        check("a held shot gets a clean plate with the moving block removed", bool(s1.get("plate")) and
              os.path.isfile(os.path.join(td, s1["plate"])))
        check("the real cut frame is found next to the stated time", abs(c1["t_in"] - 2.0) <= 0.05 and abs(c2["t_in"] - 4.0) <= 0.05,
              f"{c1.get('t_in')} {c2.get('t_in')}")
        check("C1: the two sides look like one place", c1["look"] == "alike", f"{c1['look_sim']}")
        check("C1: the blue cast is a colour jump between alike pictures", any("colour jump" in f for f in c1["flags"]),
              f"ΔE {c1['delta_e']} {c1['flags']}")
        check("C1: the block keeps moving right — direction kept", c1["screen_dir"] == "kept",
              f"{c1.get('subj_before')} {c1.get('subj_after')}")
        check("C1: the subject is found where it is (moving-region centroid, left of centre)",
              c1["pos_out"] is not None and 0.3 < c1["pos_out"][0] < 0.7, str(c1.get("pos_out")))
        check("C2: a different place reads unalike", c2["look"] in ("unalike", "mixed") and c2["delta_e"] > TH["delta_e_grade"],
              f"{c2['look_sim']} {c2['delta_e']}")
        check("C2: right then left — the screen direction flips", c2["screen_dir"] == "flipped" and
              any("flips" in f for f in c2["flags"]), f"{c2.get('subj_before')} {c2.get('subj_after')}")
        check("C2: the eye has to travel across the frame", c2["eye_shift"] is not None and c2["eye_shift"] > 0.15, str(c2.get("eye_shift")))
        check("the shot and pair sheets are written", d["sheets"]["shots"] and d["sheets"]["pairs"])
        rp = template(os.path.join(td, "JOINS-synth.json"))
        E, _ = validate(rp)
        check("an empty read does not validate", len(E) > 5, str(len(E)))
        rd = json.load(open(rp))
        loc = {"setting": "interior", "place": "a stucco wall", "era": "now", "weather": "n/a",
               "materials": "rough plaster", "layers": {"fg": "", "mid": "the block", "bg": "the wall"},
               "distinctive": "grain", "recreate": "a plaster wall, flat even light",
               "variants": ["a tiled kitchen wall", "a hedge", "a brick alley"]}
        rd.update({"reader": "selftest", "date": "2026-10-25",
                   "entities": [{"id": "A", "kind": "prop", "desc": "a red block"},
                                {"id": "B", "kind": "character", "desc": "a passer-by"},
                                {"id": "L1", "kind": "location", "desc": "a grey textured wall", **loc},
                                {"id": "L2", "kind": "location", "desc": "a green field",
                                 **dict(loc, setting="exterior", weather="clear", variants=["a beach"])}]})
        for s, lc in zip(rd["shots"], ("L1", "L1", "L2", "L1", "L1")):
            s.update({"size": "WS", "angle": "eye", "location": lc, "light_key": "flat", "light_quality": "soft",
                      "light_style": "natural", "time_of_day": "day",
                      "props": [{"id": "A", "holder": "none", "state": "moving"}] if s["n"] <= 3 else []})
        rd["shots"][2]["characters"] = [{"id": "B", "screen": "right", "depth": "bg", "gaze": "screen-left",
                                         "facing": "left", "motion": "left", "expr": "curious", "intensity": 1,
                                         "turn": "late: looks away"}]
        rd["shots"][3]["camera"] = "pan"
        rd["cuts"][0].update({"relation": "same-scene", "match": ["movement"], "axis": "n/a",
                              "screen_direction": "flipped", "eyeline": "n/a", "carries": ["A", "L1", "movement"],
                              "changes": ["colour"], "continuity_error": ""})
        rd["cuts"][1].update({"relation": "new-scene", "match": ["none"], "axis": "n/a", "screen_direction": "flipped",
                              "eyeline": "n/a", "carries": ["A"], "changes": ["place"], "continuity_error": ""})
        for c in rd["cuts"][2:]:
            c.update({"relation": "return" if c["n"] == 3 else "same-scene", "match": ["none"], "axis": "n/a",
                      "screen_direction": "n/a", "eyeline": "n/a", "carries": ["L1"], "changes": ["size"],
                      "continuity_error": ""})
        json.dump(rd, open(rp, "w"))
        E, Wn = validate(rp)
        check("a filled read validates", not E, "; ".join(E[:3]))
        check("a read that contradicts the pixels is sent back for a second look",
              any("C1" in w and "look again" in w for w in Wn) and any("colour jump" in w for w in Wn), "; ".join(Wn))
        rd["shots"][0]["size"] = "huge"; rd["cuts"][1]["carries"] = ["Z9"]
        json.dump(rd, open(rp, "w"))
        E, _ = validate(rp)
        check("off-vocabulary values and an unknown entity are errors",
              any("size 'huge'" in e for e in E) and any("Z9" in e for e in E), "; ".join(E[:4]))
        check("a location with fewer than three variants is a warning, not an error",
              any("L2: 1 variant" in w for w in validate(rp)[1]))
        rd["shots"][0]["size"] = "WS"; rd["cuts"][1]["carries"] = ["A"]; rd["cuts"][0]["screen_direction"] = "kept"
        rd["cuts"][0]["continuity_error"] = "a blue cast on the second angle of the same wall"
        json.dump(rd, open(rp, "w"))
        g = merge(rp)
        check("merge writes the graph: the block in shots 1–3, the wall in four shots and the field in one, one return",
              [e for e in g["entities"] if e["id"] == "A"][0]["shots"] == [1, 2, 3]
              and g["summary"]["locations"] == {"L1": 4, "L2": 1} and g["summary"]["returns"] == 1,
              json.dumps(g["summary"]))
        check("the summary counts the measured flip and the recorded continuity error",
              g["summary"]["screen_flips_measured"] == 1 and g["summary"]["continuity_errors"] == 1)
        check("the markdown is written", os.path.isfile(os.path.join(td, "SHOTGRAPH-synth.md")))
        check("the emotion arc and the backgrounds are in the graph",
              g["emotion_arcs"].get("B") == ["S3 curious1→late: looks away"]
              and [b["id"] for b in g["backgrounds"]] == ["L1", "L2"] and len(g["backgrounds"][0]["palette"]) >= 3,
              json.dumps(g["emotion_arcs"]))
        check("the camera distribution counts the read where given and the measure elsewhere",
              g["summary"]["camera_pct"].get("pan") == 20.0, json.dumps(g["summary"]["camera_pct"]))
        check("qa exits 1 on a flagged join", qa(v, cl, "synth_qa", os.path.join(td, "qa"), True) == 1)
    print("-" * 60)
    print("selftest OK — camera-side naming; on a synthetic five-shot film: the real cut frame, alike vs unalike "
          "pictures, a colour jump between alike pictures, direction kept and flipped, the subject's position and the "
          "eye jump; the camera tracked and categorised (locked, a pan right → blocking `pan`, a zoom); per-shot light, "
          "palette and composition maps, a clean plate; the sheets; the read form, its vocabulary (emotion, light, "
          "locations with variants), the read-vs-pixels second look, the merged graph with emotion arcs and backgrounds, "
          "and the QA exit" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("measure", "qa"):
        p = sub.add_parser(name)
        p.add_argument("video"); p.add_argument("--cuts", required=True)
        p.add_argument("--label", required=True); p.add_argument("--out", required=True)
        p.add_argument("--confirmed", action="store_true", help="the cut list was confirmed on strips")
        p.add_argument("--width", type=int, default=480)
        p.add_argument("--plates", action="store_true", help="write a clean background plate per held shot")
    sub.choices["measure"].add_argument("--no-sheets", action="store_true",
                                        help="numbers only, no contact sheets (batch measurement of a dataset)")
    t = sub.add_parser("template"); t.add_argument("joins"); t.add_argument("-o", "--out")
    v = sub.add_parser("validate"); v.add_argument("read")
    m = sub.add_parser("merge"); m.add_argument("read")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "measure":
        d = measure(a.video, a.cuts, a.label, a.out, a.confirmed, sheets=not a.no_sheets, width=a.width,
                    plates=a.plates)
        fl = sum(len(j.get("flags") or []) for j in d["cuts"])
        print(f"JOINS-{a.label}.json · {len(d['shots'])} shots · {len(d['cuts'])} cuts · {fl} measured flag(s) · cut list "
              + ("confirmed" if a.confirmed else "⚠ NOT confirmed — confirm on film_breakdown.py --strip sheets"))
        print(f"  sheets: {', '.join((d['sheets'].get('shots') or []) + (d['sheets'].get('pairs') or []))}")
        print(f"  next: shot_graph.py template {os.path.join(a.out, f'JOINS-{a.label}.json')}")
        return 0
    if a.cmd == "qa":
        return qa(a.video, a.cuts, a.label, a.out, a.confirmed)
    if a.cmd == "template":
        print(template(a.joins, a.out)); return 0
    if a.cmd == "validate":
        E, W = validate(a.read)
        for e in E:
            print(f"  ✗ {e}")
        for w in W:
            print(f"  ~ {w}")
        print("VALID" if not E else f"{len(E)} error(s)")
        return 1 if E else 0
    if a.cmd == "merge":
        g = merge(a.read)
        print(f"SHOTGRAPH-{g['film']}.json/.md · {g['summary']['shots']} shots · {g['summary']['cuts']} cuts · "
              f"{len(g['warnings'])} read-vs-pixel warning(s)")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
