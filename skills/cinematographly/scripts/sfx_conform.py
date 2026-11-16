#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""sfx_conform.py — sound effects conformed to what the shot shows: how many, when, how loud, where.

Author, 2026-10-26: *"the amount and timing doesn't always match what's happening in the shot. 3 drops of
water, and they are not timed to the splash itself. The AI should cut the downloaded SFX and adjust as
needed. Also try to understand the volume based on the distance, speed of the object etc. … There are many
others with other parameters too. Find and include them."* The council (the motion sound proposal of 2026-10-26
[studio history]) ranked this first; the owner chose all four packages:
*"A: Event conform, B: Per-event parameters, C: Sound across cuts, D: Directional, earbuds only"*.

  index   <file> …            every transient in a downloaded SFX file → `<file>.onsets.json`; a file
                               with no separable events (rain, crowd, room) is tagged `bed`, not cut
  events  <clip> --job J --shot S [--track name=x,y,w,h]
                               every visual event in the clip (each drop, step, tap): local bursts of
                               motion with the camera's motion and any global flicker removed, merged with
                               the named objects' contacts, and voted on by the clip's own audio
                               → 09-qa/sfx/<S>.events.json
  read    <job> --shot S [--clip C]
                               the frames of every event on one sheet (09-qa/sfx/<S>.read-sheet.png) and a
                               closed-vocabulary form beside it (<S>.read.json): what each event is, its
                               material and the surface it meets, wet or dry, size, force, whether it is
                               seen or behind glass, the room and its size, the distance, how many events
                               there really are (and any the detector missed). The agent fills it by
                               LOOKING at the sheet — a vision model reads material and room from a frame —
                               and the director confirms; `conform` uses it
  conform <job> --shot S --sfx <file>[,<file>…] [--clip C] [tags]
                               the SFX cut into its events, one per visual event, each attack 0 to +1
                               frame after its frame (never early), each event's level, tone, room,
                               pitch, length and (optionally) pan set from what the shot shows; one
                               48 kHz WAV per clip in clip time → 06-sfx/conform/<S>.sfx.wav (+ .mp4 with
                               --mux), the placement log beside it, and the re-check written in
  verify  <job> --shot S       re-detect the attacks on the render alone: the same count, each 0 to +1
                               frame after its visual event (exit 1 otherwise)
  joins   <job> [--whoosh F]   the sound plan across each planned cut (C): an overlap on a match, one
                               ambience across a camera carry, a clean break on a flip, a whoosh only on
                               a whip (2 per ad at most), the clip muted under a ramp and its cue →
                               09-qa/sfx/<cut>.joins-sound.json + an EDL of markers; with --whoosh, a
                               stem in cut time with each whoosh on its cut
  levels  <job> --placement 06-music/SFX-PLACEMENT.json --voice <the voice, in timeline time> [--fps 24] [--write]
                               every placed SFX set by MEASUREMENT, not by guess (a supplement ad job: SFX sat 9–43 dB under the
                               voice, a plate rub inaudible, a bite and a switch clipping). Per event: its in-point moved
                               to the file's transient (a rub's peak sat 13 frames past an in-point), the momentary loudness
                               of the sound as cut against the voice's at that moment, the gain that puts it at its
                               category's level under the voice, capped so the peak stays at −6 dBFS → 09-qa/sfx/LEVELS.json
                               (and, with --write, `volume_db` and `in_s` in the placement, the old values kept). Also the
                               density against the client's (audio.<client>.json `sfx_density_per_min`), and a WARN for
                               a sound longer than 1.5 s on a graphic (v2.46, events not motion: a graphic's arrival,
                               land, snap or contact gets a sound, its drift does not; `bed: yes` on the row exempts it)
  --selftest

Tags (flags, or one `sfx:` line in the clip prompt: `sfx: count=3, material=water, surface=wet,
space=kitchen, distance=close, hero=jar`): count (the director's count, which wins), material, surface
(hard · soft · wet), space (dry · exterior · interior · kitchen · bathroom · hall), distance (close ·
medium · far), hero (the named object whose events play full level), pan (off · follow; default off).

Two kinds of evidence, kept apart. The PIXEL measurement (events, timing, position, size in frame, speed,
fall) is computed. The READ (material, surface, wet or dry, the room, what each event is, what is behind
glass, how many there really are) comes from looking at the frames: OpenCV cannot name a material, but
the agent can, from the sheet, in a closed vocabulary the conform holds it to (2026-10-26: "AI can
read materials from the frame"). The sound then has to FIT that read; listeners judge an object's size
from its sound but rarely name its material (Grassi 2005), so a wrong-material sound passes on size and
fails on feel.

What it cannot do: see a drop smaller than a grid cell, or separate two drops in the same cell on the
same frame (the read can add a missed event by its time). When it is unsure it plays fewer hits: silence
beats a wrong hit. Every threshold marked [assumed] waits for real clips to calibrate it.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, math, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SR = 48000

# --- detection thresholds -------------------------------------------------------------------------
GRID_W = 8                 # cells across the frame; rows follow the aspect [assumed]
FLUX_K = 6.0               # a burst is median + 6 MAD of the clip's local-burst curve [assumed]
FLUX_MIN = 1.5             # …and at least this many grey levels of new change [assumed]
LOCAL_X = 3.0              # the burst cell must be 3× the frame's mean cell change (global flicker is not local) [assumed]
MERGE_S = 0.08             # bursts closer than 80 ms and 1.5 cells apart are one event [the council, assumed]
TRACK_CONTACT = 0.6        # a tracked object's speed falling by 60 % within two samples is a contact [assumed]
VOTE_WIN = (-2, 3)         # frames around a visual event where the clip's own audio onset counts as a vote
SLIDE_S = 0.3              # change that lasts this long after the burst is a slide, not a hit [assumed]
DENSITY_MAX = 6.0          # events per second before hits turn into a texture [the council, untested]
# --- audio onset thresholds ------------------------------------------------------------------------
HOP = 256                  # samples per onset frame at 48 kHz (5.3 ms)
ONSET_K = 4.0              # spectral-flux peak over median + 4 MAD [assumed]
ONSET_GAP_S = 0.06         # two attacks closer than 60 ms are one [assumed]
BED_DENSITY = 8.0          # more attacks than this per second, or no attacks at all → a bed [assumed]
BED_RANGE_DB = 15.0        # a file whose loud and quiet moments sit within 15 dB is continuous → a bed [assumed]
ONSET_RISE_DB = 6.0        # an attack rises at least 6 dB over the 20 ms before it [assumed]
ONSET_RANGE_DB = 40.0      # …and comes within 40 dB of the file's loudest moment [assumed]
# --- per-event parameters ------------------------------------------------------------------------
DIST_GAIN = {"close": 0.0, "medium": -3.5, "far": -7.0}     # about −3.5 dB per doubling, a compressive slope (Zahorik 2005) [assumed]
DIST_LP = {"close": 16000, "medium": 11000, "far": 7000}   # less top end with distance [practitioner]
DIST_WET = {"close": 0.04, "medium": 0.10, "far": 0.20}    # more room with distance (direct-to-reverberant, Zahorik 2005) [assumed]
SPACE_RT60 = {"dry": 0.0, "exterior": 0.25, "interior": 0.5, "kitchen": 0.6, "bathroom": 1.1, "hall": 1.8}
STRENGTH_GAIN = {"soft": -4.0, "medium": 0.0, "hard": 3.0}  # [practitioner, assumed]
SIZE_PITCH = {"small": 2.0, "medium": 0.0, "large": -2.0}   # semitones; bigger is lower (crossmodal) [assumed]
SURFACE = {"hard": {"shelf": 2.0, "lag": 0}, "soft": {"shelf": -3.0, "lag": 0}, "wet": {"shelf": -1.5, "lag": 1}}
OFFSCREEN = {"gain": -4.0, "lp": 5000, "wet": 0.10}         # [practitioner, assumed]
BACKGROUND_GAIN = -6.0     # events that are not the hero's [the council, practitioner]
JITTER_DB = 1.0            # per-event level jitter so repeats are not identical [practitioner]
HIGHPASS = 120             # Hz, always: phones do not play below it [practitioner]
PAN_MAX = 0.4              # constant power; folds to mono ~0.4 dB down at the cap [assumed]
WHIP_MAX = 2               # whooshes per ad at most [the council]
TAGS = ("count", "material", "surface", "space", "distance", "hero", "pan")
SPACE_RT60.update({"car": 0.15, "street": 0.3, "forest": 0.2, "studio": 0.3})
SPACE_SIZE = {"small": 0.7, "medium": 1.0, "large": 1.5}
OCCLUDED = {"none": None, "glass": {"lp": 3000, "gain": -3.0}, "door": {"lp": 2000, "gain": -6.0},
            "wall": {"lp": 1200, "gain": -9.0}}                     # [practitioner, assumed]
MATERIALS = ["water", "liquid", "glass", "ceramic", "metal", "wood", "plastic", "paper", "cardboard", "fabric",
             "skin", "food", "stone", "rubber", "foliage", "other"]
VOCAB = {  # the read's closed lists (`read` writes them into the form; `conform` refuses anything else)
    "what": ["drop", "splash", "pour", "tap", "knock", "clink", "thud", "step", "scrape", "slide", "rustle", "click",
             "snap", "pop", "crunch", "squeeze", "open", "close", "other"],
    "object_material": MATERIALS, "surface_material": MATERIALS + ["none"],
    "wet": ["yes", "no"], "size": ["small", "medium", "large"], "force": ["soft", "medium", "hard"],
    "visible": ["yes", "partly", "no"], "occluded": list(OCCLUDED), "keep": ["yes", "no"],
    "space": list(SPACE_RT60), "space_size": list(SPACE_SIZE), "distance": list(DIST_GAIN)}


def _np():
    import numpy as np
    return np


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def pcm(path: str, sr: int = SR, ch: int = 1, max_s: float | None = None):
    np = _np()
    lim = ["-t", f"{max_s:.3f}"] if max_s else []
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", *lim, "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.float32).copy()
    return a.reshape(-1, ch) if ch > 1 else a


def write_wav(path: str, x, sr: int = SR) -> None:
    np = _np()
    a = np.ascontiguousarray(np.clip(x, -1.0, 1.0), dtype=np.float32)
    ch = 1 if a.ndim == 1 else a.shape[1]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i", "-",
                    "-c:a", "pcm_s24le", path], input=a.tobytes(), check=True)


def has_audio(path: str) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                        path], capture_output=True, text=True)
    return bool(r.stdout.strip())


# =================================================================================================
# A. the attacks in a sound file
# =================================================================================================
def detect_onsets(x, sr: int = SR) -> list:
    """Spectral-flux onsets: [{start, attack, end, peak_db, centroid}] in seconds. `start` is where the
    event's energy begins (the cut point), `attack` its loudest moment within 50 ms (what lands on the
    frame)."""
    np = _np()
    if len(x) < 2048:
        return []
    n = 1024
    frames = (len(x) - n) // HOP + 1
    idx = np.arange(n)[None, :] + HOP * np.arange(frames)[:, None]
    win = np.hanning(n).astype(np.float32)
    S = np.abs(np.fft.rfft(x[idx] * win, axis=1))
    L = np.log1p(S * 100)
    flux = np.maximum(0, np.diff(L, axis=0)).sum(axis=1)
    flux = np.concatenate([[0.0], flux])
    rms = np.sqrt(np.mean(x[idx] ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    med = np.median(flux)
    mad = np.median(np.abs(flux - med)) + 1e-9
    thr = med + ONSET_K * mad
    gap = int(ONSET_GAP_S * sr / HOP)
    peaks = []
    top = float(db.max())
    pre = int(0.02 * sr / HOP) + 1
    for i in range(1, frames - 1):
        rise = db[i:i + 4].max() - db[max(0, i - pre):i].min() if i > 0 else 0.0
        if flux[i] >= thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1] and db[i:i + 4].max() > -60 \
                and rise >= ONSET_RISE_DB and db[i:i + 4].max() >= top - ONSET_RANGE_DB:
            if peaks and i - peaks[-1] < gap:
                if flux[i] > flux[peaks[-1]]:
                    peaks[-1] = i
                continue
            peaks.append(i)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    out = []
    for k, i in enumerate(peaks):
        nxt = peaks[k + 1] if k + 1 < len(peaks) else frames
        a_end = min(nxt, i + int(0.05 * sr / HOP) + 1)
        ai = i + int(np.argmax(db[i:a_end]))
        s0 = i
        while s0 > 0 and s0 > i - 4 and db[s0 - 1] < db[s0]:
            s0 -= 1
        pk = db[ai]
        e = ai
        while e < nxt - 1 and db[e] > pk - 40:
            e += 1
        spec = S[ai]
        cen = float((spec * freqs).sum() / (spec.sum() + 1e-9))
        out.append({"start": round(s0 * HOP / sr, 4), "attack": round(ai * HOP / sr + n / 2 / sr, 4),
                    "end": round(min(len(x) / sr, e * HOP / sr + n / sr), 4), "peak_db": round(float(pk), 1),
                    "centroid": round(cen)})
    return out


# =================================================================================================
# A2. (v2.68.0) the SHAPE of each attack — what decides whether a hit fits the event. Planned with three review
#     rounds each by Grok 4.7 and Sonnet 5.5. `attack`
#     above is untouched: placement, the re-check and `levels` read it. These are new fields beside it.
# =================================================================================================
SHAPE_PEAK_S = 0.4         # how far past the energy start the wide peak is searched, so a soft set-down reads as
                           # slow; bounded by the next attack [assumed]
SHAPE_START_DB = 30.0      # the energy start: the first frame within this of the wide peak [assumed]
SHAPE_DIP_DB = 10.0        # a hit's rise is readable only if the level dipped this far before it [assumed]
RING_AFTER_S = 0.1         # the ring is the tail ABOVE −40 dB that is left this long after the peak [assumed]
# A "has its own room" flag was planned and dropped (plan round 3, Grok): an energy ratio 50–300 ms after the attack
# reads the next hit or the ring as room. Not measured until a measure of baked room after the ring exists.
SHAPE_V = 5                # bumps when a field's definition changes: a row with another version is "not measured"
CLEAN_GAP_S = 0.02         # silence before and after an attack, to its neighbours, for it to cut clean [assumed]
MEASURE_MAX_S = 60.0       # longer files are measured on their first MEASURE_MAX_S only: onset detection on 300 s
# used 1.67 GB (review 1); marking them beds unopened hid long footstep or door runs (build review 2, Grok)


def attack_shapes(x, ons: list, sr: int = SR) -> list:
    """Per attack, beside `detect_onsets`' own fields: sharp_ms (energy start to the FIRST peak of the rise, inside
    this attack, out to SHAPE_PEAK_S), body_s (the cutter's peak to −40 dB), ring_s (tail above −40 dB left
    RING_AFTER_S after the peak, ending at the next attack; scored on hits only), clean_in / clean_out (quiet before
    it, quiet before the next one). Known limit: a rise slower than detect_onsets' threshold is never an attack."""
    np = _np()
    if not ons:
        return []
    fr = HOP
    n_fr = len(x) // fr
    if n_fr < 2:
        return [{} for _ in ons]
    db = 20 * np.log10(np.sqrt((x[: n_fr * fr].reshape(n_fr, fr) ** 2).mean(axis=1)) + 1e-9)
    t_of = lambda i: i * fr / sr                                    # noqa: E731
    i_of = lambda s: max(0, min(n_fr - 1, int(round(s * sr / fr))))  # noqa: E731
    out = []
    for k, o in enumerate(ons):
        nxt = ons[k + 1]["start"] if k + 1 < len(ons) else len(x) / sr
        i0, i_next = i_of(o["start"]), i_of(nxt)
        i_hi = max(i0 + 1, min(i_next, i_of(o["start"] + SHAPE_PEAK_S)))
        top = float(db[i0:i_hi].max())
        # the FIRST peak of the rise that comes within 6 dB of the window's top: a later bounce is not this hit's
        # peak (plan round 3, Grok)
        ip = next((j for j in range(i0, i_hi) if db[j] >= top - 6 and (j + 1 >= i_hi or db[j + 1] <= db[j])),
                  i0 + int(np.argmax(db[i0:i_hi])))
        pk = float(db[ip])
        # the rise is read from the dip before this hit: the previous hit's end when it came back down, else the
        # quietest point since the previous attack (build review 2, Sonnet: reading only after the previous −40 dB end
        # left 55–63 % of sequence attacks unread). Too shallow a dip (< SHAPE_DIP_DB): unreadable, no force point.
        lo = i_of(ons[k - 1]["attack"]) + 1 if k else max(0, i0 - i_of(0.03))
        lo = min(lo, ip)
        iv = lo + int(np.argmin(db[lo:ip + 1])) if ip >= lo else ip
        depth = pk - float(db[iv])
        if k and depth < SHAPE_DIP_DB:
            sharp_ms = None          # this hit rides on the last one's tail: its rise cannot be read
        else:
            js = next((j for j in range(iv, ip + 1) if db[j] >= pk - min(SHAPE_START_DB, depth)), ip)
            sharp_ms = max(0.0, (t_of(ip) - t_of(js)) * 1000)
        ir0 = min(i_next, ip + i_of(RING_AFTER_S))
        ring = 0
        while ir0 + ring < i_next and db[ir0 + ring] > pk - 40:
            ring += 1
        # clean edges by the real gap to the neighbours (build review 1, Sonnet: a fixed 20 ms window flagged 93–95 %
        # of real attacks, because sequences always have a neighbour in it)
        gap_in = o["start"] - (ons[k - 1]["end"] if k else 0.0)
        gap_out = (nxt - o["end"]) if k + 1 < len(ons) else (len(x) / sr - o["end"])
        clean_in = bool(k == 0 or gap_in >= CLEAN_GAP_S)
        clean_out = bool(gap_out >= CLEAN_GAP_S or k + 1 == len(ons))
        out.append({"sharp_ms": None if sharp_ms is None else round(sharp_ms, 1), "start": o["start"], "body_s": round(max(0.0, o["end"] - o["attack"]), 3),
                    "ring_s": round(ring * fr / sr, 3),
                    "clean_in": clean_in, "clean_out": clean_out,
                    "gap_in_ms": round(max(0.0, gap_in) * 1000), "gap_out_ms": round(max(0.0, gap_out) * 1000)})
    return out


def index_file(path: str, kind: str | None = None, material: str | None = None) -> dict:
    np = _np()
    x = pcm(path)
    ons = detect_onsets(x)
    dur = len(x) / SR
    density = len(ons) / max(dur, 1e-3)
    fr = x[: (len(x) // HOP) * HOP].reshape(-1, HOP) if len(x) >= HOP else x.reshape(1, -1)
    edb = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    span = float(np.percentile(edb, 99) - np.percentile(edb, 10)) if edb.size else 0.0
    auto = "bed" if (not ons or density > BED_DENSITY or span < BED_RANGE_DB) else "event"
    rep = {"file": os.path.basename(path), "sha256": sha256_file(path), "sr": SR, "duration": round(dur, 3),
           "kind": kind or auto, "kind_auto": auto, "dynamic_range_db": round(span, 1), "events": ons,
           "material": material,
           "indexed": dt.datetime.now().isoformat(timespec="minutes")}
    json.dump(rep, open(path + ".onsets.json", "w", encoding="utf-8"), indent=1)
    return rep


def load_index(path: str) -> dict:
    sc = path + ".onsets.json"
    if os.path.isfile(sc):
        try:
            d = json.load(open(sc, encoding="utf-8"))
            if d.get("sha256") == sha256_file(path):
                return d
        except ValueError:
            pass
    return index_file(path)


# =================================================================================================
# A. the events in the picture
# =================================================================================================
def _gray_frames(clip: str, info: dict):
    import shot_graph as SG
    np, cv2 = SG._need()
    fps = info.get("fps") or 24.0
    fr = SG.decode_fps(clip, 0.0, info["duration"], info, fps, 320)
    return [(t, cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)) for t, f in fr], fps


def _stabilise(prev, cur, cv2, np):
    """prev warped onto cur by the camera's similarity transform (none when it cannot be solved)."""
    p0 = cv2.goodFeaturesToTrack(prev.astype(np.uint8), maxCorners=200, qualityLevel=0.01, minDistance=7)
    if p0 is None or len(p0) < 12:
        return prev, None
    p1, st, _ = cv2.calcOpticalFlowPyrLK(prev.astype(np.uint8), cur.astype(np.uint8), p0, None)
    ok = st.reshape(-1) == 1
    if ok.sum() < 12:
        return prev, None
    M, inl = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if M is None:
        return prev, None
    h, w = cur.shape
    return cv2.warpAffine(prev, M, (w, h), borderMode=cv2.BORDER_REPLICATE), M


def visual_events(clip: str, static: bool | None = None, tracks: list | None = None,
                  count: int | None = None, native_vote: bool = True) -> dict:
    """Every visual event in the clip. Returns {"events": [...], "fps", "dropped": [...]}"""
    import shot_graph as SG
    np, cv2 = SG._need()
    info = SG.probe(clip)
    frames, fps = _gray_frames(clip, info)
    if len(frames) < 3:
        return {"events": [], "fps": fps, "dropped": [], "error": "too few frames"}
    H, W = frames[0][1].shape
    gw = GRID_W
    gh = max(1, int(round(GRID_W * H / W)))
    ch, cw = H // gh, W // gw
    if static is None:
        cam = SG.camera_path(clip, 0.0, info["duration"], info)
        fam = (cam.get("family") or cam.get("category") or "").split("-")[0]
        static = fam in ("locked", "drift")
    E = np.zeros((len(frames), gh, gw), np.float32)
    for k in range(1, len(frames)):
        prev, cur = frames[k - 1][1], frames[k][1]
        if not static:
            prev, _ = _stabilise(prev, cur, cv2, np)
        d = np.abs((cur - cur.mean()) - (prev - prev.mean()))       # a global flicker is not an event
        E[k] = d[:gh * ch, :gw * cw].reshape(gh, ch, gw, cw).mean(axis=(1, 3))
    F = np.maximum(0, np.diff(E, axis=0, prepend=E[:1]))           # new change, per cell
    F[1] = 0                                                       # the first difference has no "before"
    s = F.reshape(len(frames), -1).max(axis=1)
    mean_cell = F.reshape(len(frames), -1).mean(axis=1) + 1e-6
    med = float(np.median(s)); mad = float(np.median(np.abs(s - med))) + 1e-6
    thr = max(FLUX_MIN, med + FLUX_K * mad)
    cand = []
    for k in range(2, len(frames)):
        if s[k] < thr:
            continue
        cells = np.argwhere(F[k] >= max(thr, 0.5 * F[k].max()))
        for (r, c) in cells:
            v = float(F[k, r, c])
            if v < thr or v < LOCAL_X * mean_cell[k]:
                continue
            if E[k - 1, r, c] >= 0.5 * E[k, r, c]:
                continue                                           # already moving: not an onset
            # persistence: the change in this cell lasts past the burst frame
            after = E[k + 1, r, c] if k + 1 < len(frames) else 0.0
            persist = after >= 0.3 * E[k, r, c]
            # slide or hit: how long the cell stays busy
            j = k
            while j + 1 < len(frames) and E[j + 1, r, c] >= 0.3 * E[k, r, c]:
                j += 1
            cand.append({"k": k, "t": float(frames[k][0]), "r": int(r), "c": int(c), "v": v, "persist": bool(persist),
                         "busy_s": round((j - k) / fps, 3)})
    # merge: same burst over neighbouring cells, or a burst that spans two frames
    cand.sort(key=lambda e: (e["k"], -e["v"]))
    merged = []
    for e in cand:
        # the same burst over neighbouring cells, or a splash still spreading from where it started
        hit = next((m for m in merged if 0 <= e["t"] - m["t"] <= max(MERGE_S, m["busy_s"]) + 1e-6
                    and abs(m["r"] - e["r"]) <= 2 and abs(m["c"] - e["c"]) <= 2), None)
        if hit:
            hit["cells"] += 1
            if e["v"] > hit["v"] and e["k"] == hit["k"]:
                hit.update({"r": e["r"], "c": e["c"], "v": e["v"]})
            continue
        merged.append({**e, "cells": 1})
    events = []
    for m in merged:
        conf = "high" if m["persist"] and m["v"] >= 2 * thr else ("medium" if m["persist"] else "low")
        # where exactly: the centroid of the new change in the cells around the burst
        k_ = m["k"]
        prev, cur = frames[k_ - 1][1], frames[k_][1]
        if not static:
            prev, _ = _stabilise(prev, cur, cv2, np)
        y0, y1 = max(0, (m["r"] - 1) * ch), min(H, (m["r"] + 2) * ch)
        x0, x1 = max(0, (m["c"] - 1) * cw), min(W, (m["c"] + 2) * cw)
        d = np.abs((cur - cur.mean()) - (prev - prev.mean()))[y0:y1, x0:x1]
        ys, xs = np.nonzero(d >= 0.5 * d.max()) if d.size and d.max() > 0 else ([], [])
        cx = (x0 + float(np.mean(xs))) / W if len(xs) else (m["c"] + 0.5) / gw
        cy = (y0 + float(np.mean(ys))) / H if len(ys) else (m["r"] + 0.5) / gh
        events.append({"t": round(m["t"], 4), "frame": m["k"], "x": round(cx, 3),
                       "y": round(cy, 3), "strength": round(m["v"], 2), "area": m["cells"],
                       "kind": "slide" if m["busy_s"] >= SLIDE_S else "hit", "busy_s": m["busy_s"],
                       "confidence": conf, "votes": ["picture"]})
    # named objects: a sharp fall in speed is a contact
    for spec in tracks or []:
        import motion_qa as MQ
        name, box = MQ.parse_track(spec)
        tr = MQ.track_object(clip, info, box)
        S_ = [x for x in tr.get("samples", []) if x["ok"]]
        for i in range(2, len(S_) - 1):
            v0 = ((S_[i - 1]["cx"] - S_[i - 2]["cx"]) ** 2 + (S_[i - 1]["cy"] - S_[i - 2]["cy"]) ** 2) ** 0.5
            v1 = ((S_[i + 1]["cx"] - S_[i]["cx"]) ** 2 + (S_[i + 1]["cy"] - S_[i]["cy"]) ** 2) ** 0.5
            if v0 > 0.004 and v1 < (1 - TRACK_CONTACT) * v0:
                t = S_[i]["t"]
                ev = next((e for e in events if abs(e["t"] - t) <= 2 / fps + 1e-6), None)
                fall = max(0.0, S_[i]["cy"] - S_[max(0, i - 12)]["cy"])
                extra = {"object": name, "speed": round(v0 * fps, 3), "fall": round(fall, 3),
                         "box": list(box)}
                if ev:
                    ev.update(extra); ev["confidence"] = "high"; ev["votes"].append(f"track:{name}")
                else:
                    events.append({"t": round(t, 4), "frame": int(round(t * fps)), "x": S_[i]["cx"], "y": S_[i]["cy"],
                                   "strength": round(v0 * fps * 10, 2), "area": 1, "kind": "hit", "busy_s": 0.0,
                                   "confidence": "high", "votes": [f"track:{name}"], **extra})
    # the clip's own audio: a second vote, never the sound (the council, M18)
    if native_vote and has_audio(clip):
        ons = detect_onsets(pcm(clip))
        for e in events:
            if any(VOTE_WIN[0] / fps <= o["attack"] - e["t"] <= VOTE_WIN[1] / fps for o in ons):
                e["votes"].append("own-audio")
                if e["confidence"] == "low":
                    e["confidence"] = "medium"
    events.sort(key=lambda e: e["t"])
    dropped = [e for e in events if e["confidence"] == "low"]
    keep = [e for e in events if e["confidence"] != "low"]
    if count is not None:
        pool = sorted(events, key=lambda e: ({"high": 2, "medium": 1, "low": 0}[e["confidence"]], e["strength"]),
                      reverse=True)
        keep = sorted(pool[:count], key=lambda e: e["t"])
        dropped = [e for e in events if e not in keep]
    # density: more than DENSITY_MAX a second turns into a texture — keep the strongest
    thinned = []
    for e in keep:
        window = [x for x in keep if abs(x["t"] - e["t"]) <= 0.5]
        if len(window) > DENSITY_MAX:
            rank = sorted(window, key=lambda x: -x["strength"]).index(e)
            if rank >= DENSITY_MAX:
                thinned.append(e)
    keep = [e for e in keep if e not in thinned]
    for e in thinned:
        e["why_dropped"] = "density — more than 6 a second; a texture bed reads better than hits"
    return {"events": keep, "dropped": dropped + thinned, "fps": fps, "static_camera": bool(static),
            "threshold": round(thr, 2), "grid": [gw, gh], "duration": info["duration"]}


# =================================================================================================
# B. the per-event parameters
# =================================================================================================
def strength_buckets(events: list) -> None:
    if not events:
        return
    vals = sorted(e["strength"] for e in events)
    lo = vals[int(0.33 * (len(vals) - 1))]
    hi = vals[int(0.8 * (len(vals) - 1))]
    for e in events:
        if len(events) < 3:
            e["bucket"] = "medium"
        else:
            e["bucket"] = "soft" if e["strength"] <= lo and lo < hi else ("hard" if e["strength"] >= hi and lo < hi else "medium")


def params_for(e: dict, tags: dict, rng, largest_area: int) -> dict:
    """Level, tone, room, pitch, lag and pan of one event, from what the shot shows and the tags."""
    dist = tags.get("distance") or "medium"
    gain = DIST_GAIN.get(dist, -3.5) + STRENGTH_GAIN.get(e.get("bucket", "medium"), 0.0)
    lp = DIST_LP.get(dist, 11000)
    wet = DIST_WET.get(dist, 0.10)
    why = [f"distance {dist}", f"strength {e.get('bucket', 'medium')}"]
    # within the shot: a smaller burst than the shot's largest reads as further away (compressive)
    if largest_area > 1 and e.get("area", 1) < largest_area:
        rel = -3.5 * 0.5 * float(_np().log2(largest_area / max(1, e["area"])))
        rel = max(-6.0, rel)
        gain += rel
        why.append(f"smaller than the shot's largest event ({rel:+.1f} dB)")
    # speed before contact and the fall, from a named object's track
    if e.get("speed"):
        sp = min(3.0, max(-3.0, (float(e["speed"]) - 0.6) * 3.0))
        gain += sp
        why.append(f"speed {e['speed']} fw/s ({sp:+.1f} dB)")
    if e.get("fall"):
        fl = min(3.0, float(e["fall"]) / 0.25 * 1.5)
        gain += fl
        why.append(f"fall {e['fall']} of the frame ({fl:+.1f} dB)")
    # size: bigger is lower
    size = tags.get("size")
    if not size:
        size = "small" if e.get("area", 1) <= 1 else ("large" if e.get("area", 1) >= 4 else "medium")
    pitch = SIZE_PITCH.get(size, 0.0)
    # on or off screen
    off = not (0.0 <= e.get("x", 0.5) <= 1.0 and 0.0 <= e.get("y", 0.5) <= 1.0) or e.get("offscreen")
    if off:
        gain += OFFSCREEN["gain"]; lp = min(lp, OFFSCREEN["lp"]); wet += OFFSCREEN["wet"]; why.append("off screen")
    # the hero plays full; the rest sit back
    hero = tags.get("hero")
    if hero and e.get("object") != hero:
        gain += BACKGROUND_GAIN; why.append("not the hero object")
    surf = SURFACE.get(tags.get("surface") or "", {"shelf": 0.0, "lag": 0})
    gain += float(rng.uniform(-JITTER_DB, JITTER_DB))
    pan = 0.0
    if (tags.get("pan") or "off") == "follow":
        pan = max(-PAN_MAX, min(PAN_MAX, (float(e.get("x", 0.5)) - 0.5) * 0.8))
    return {"gain_db": round(gain, 2), "lowpass": int(lp), "wet": round(min(0.4, wet), 3), "pitch_st": pitch,
            "shelf_db": surf["shelf"], "lag_frames": surf["lag"], "pan": round(pan, 3), "size": size,
            "why": why}


def _fft_filter(x, sr, lp=None, hp=None, shelf_db=0.0, shelf_hz=4000.0):
    np = _np()
    n = len(x)
    if n == 0:
        return x
    N = 1 << (n - 1).bit_length()
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1 / sr)
    H = np.ones_like(f)
    if lp:
        H *= 1.0 / np.sqrt(1.0 + (f / lp) ** 4)
    if hp:
        H *= 1.0 / np.sqrt(1.0 + (hp / np.maximum(f, 1e-3)) ** 4)
    if shelf_db:
        g = 10 ** (shelf_db / 20)
        H *= 1.0 + (g - 1.0) / (1.0 + (shelf_hz / np.maximum(f, 1e-3)) ** 2)
    return np.fft.irfft(X * H, N)[:n].astype(np.float32)


def _fftconv(a, b):
    """np.convolve by FFT: a real IR runs to seconds, and a direct convolution of that is minutes."""
    np = _np()
    n = a.size + b.size - 1
    N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, N) * np.fft.rfft(b, N), N)[:n].astype(np.float32)


def load_ir(path: str, max_s: float = 3.0):
    """A measured impulse response as the conform's room: summed to mono (the mix gate folds to mono anyway),
    everything before the direct peak cut, the direct sound itself faded out so the wet path carries the
    room only, trimmed to max_s, unit energy like the synthetic one."""
    np = _np()
    x = pcm(path, ch=1)
    if x.size < 64:
        return None
    pk = int(np.argmax(np.abs(x[: int(0.2 * SR)]))) if x.size > int(0.2 * SR) else int(np.argmax(np.abs(x)))
    x = x[pk: pk + int(max_s * SR)].astype(np.float32)
    n5 = min(x.size, int(0.005 * SR))
    x[:n5] *= np.linspace(0, 1, n5)
    return (x / (np.sqrt((x.astype(np.float64) ** 2).sum()) + 1e-9)).astype(np.float32)


def _ir(rt60: float, sr: int = SR, seed: int = 0):
    np = _np()
    if rt60 <= 0:
        return None
    n = int(min(3.0, rt60 * 1.2) * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n) * np.exp(-6.91 * t / rt60)
    ir[: int(0.005 * sr)] *= np.linspace(0, 1, int(0.005 * sr))
    return (ir / (np.sqrt((ir ** 2).sum()) + 1e-9)).astype(np.float32)


def _pitch(x, st: float):
    np = _np()
    if not st:
        return x
    r = 2 ** (st / 12.0)
    n = int(len(x) / r)
    return np.interp(np.arange(n) * r, np.arange(len(x)), x).astype(np.float32)


# =================================================================================================
# A + B + D. the conform render
# =================================================================================================
def clip_tags(prompt: str | None) -> dict:
    if not prompt or not os.path.isfile(prompt):
        return {}
    txt = open(prompt, encoding="utf-8").read()
    m = re.search(r"(?m)^sfx:\s*(.+)$", txt.split("---", 2)[1] if txt.startswith("---") else "")
    out = {}
    if m:
        for kv in re.split(r"\s*[,;]\s*", m.group(1).strip()):
            if "=" in kv:
                k, v = (s.strip().lower() for s in kv.split("=", 1))
                if k in TAGS and v:
                    out[k] = v
    return out


def _sheet(clip: str, events: list, out_png: str) -> None:
    """One row per event: the frame before, the event frame and two frames after, cropped around where it
    happens and boxed; a wide frame of the shot on top."""
    import shot_graph as SG
    np, cv2 = SG._need()
    info = SG.probe(clip)
    fps = info.get("fps") or 24.0
    tile = 220

    def grab(t):
        t0 = max(0.0, t - 0.3 / fps)                               # the frame nearest t, not the one after
        fr = SG.decode(clip, t0, t0 + 0.6 / fps, info, 640)
        return fr[0][1] if fr else np.zeros((tile, tile, 3), np.uint8)

    def crop(img, x, y):
        h, w = img.shape[:2]
        half = int(max(h, w) * 0.18)
        pad = cv2.copyMakeBorder(img, half, half, half, half, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        cx, cy = int(x * w) + half, int(y * h) + half             # padded, so the event stays centred
        c = pad[cy - half:cy + half, cx - half:cx + half].copy()
        c = cv2.resize(c, (tile, tile)) if c.size else np.zeros((tile, tile, 3), np.uint8)
        cv2.rectangle(c, (tile // 2 - 18, tile // 2 - 18), (tile // 2 + 18, tile // 2 + 18), (0, 220, 255), 1)
        return c
    rows = []
    for i, e in enumerate(events, 1):
        frame = grab(e["t"] + 1 / fps)
        h, w = frame.shape[:2]
        wide = cv2.resize(frame, (max(1, int(w * tile / h)), tile))   # the whole frame, where it happens boxed
        ww = wide.shape[1]
        cv2.rectangle(wide, (int(e["x"] * ww) - 10, int(e["y"] * tile) - 10), (int(e["x"] * ww) + 10, int(e["y"] * tile) + 10),
                      (0, 220, 255), 2)
        cells = [wide] + [crop(grab(e["t"] + d / fps), e["x"], e["y"]) for d in (-1, 0, 1, 2)]
        row = np.concatenate(cells, axis=1)
        cv2.putText(row, f"E{i}  {e['t']:.3f}s", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        for j, lab in enumerate(("-1f", "0", "+1f", "+2f")):
            cv2.putText(row, lab, (ww + j * tile + 6, tile - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        rows.append(row)
    if not rows:
        rows = [np.zeros((tile, tile, 3), np.uint8)]
    wmax = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 0), (0, wmax - r.shape[1]), (0, 0))) for r in rows]
    cv2.imwrite(out_png, np.concatenate(rows, axis=0))


def read_form(job: str, shot: str, clip: str | None = None, tracks: list | None = None) -> dict:
    clip = clip or _take_of(job, shot)
    VE = visual_events(clip, tracks=tracks)
    d = os.path.join(job, "09-qa", "sfx")
    os.makedirs(d, exist_ok=True)
    png = os.path.join(d, f"{shot}.read-sheet.png")
    _sheet(clip, VE["events"], png)
    form = {"shot": shot, "clip": os.path.relpath(clip, job), "clip_sha256": sha256_file(clip),
            "sheet": os.path.relpath(png, job), "events_detected": len(VE["events"]),
            "shot_read": {"space": "", "space_size": "", "distance": "", "count_seen": "", "extra_events": [],
                          "offscreen_sources": "", "search": "", "notes": ""},
            "events": [{"id": f"E{i}", "t": e["t"], "what": "", "object_material": "", "surface_material": "",
                        "wet": "", "size": "", "force": "", "visible": "", "occluded": "", "keep": ""}
                       for i, e in enumerate(VE["events"], 1)],
            "vocabulary": VOCAB, "read_by": "", "read_at": "",
            "how": "Look at the sheet (and the clip). Fill every field from the vocabulary; leave a field empty only "
                   "when the frames cannot show it. count_seen: how many sound events the shot really has; "
                   "extra_events: the times (s) of any the detector missed; keep: no for a burst that makes no "
                   "sound (a reflection, a flicker). search: the words to find the right sound (\"water drop on "
                   "steel sink, close\")."}
    fp = os.path.join(d, f"{shot}.read.json")
    if os.path.isfile(fp):                      # never overwrite a filled read; write the fresh form beside it
        fp = os.path.join(d, f"{shot}.read.new.json")
    json.dump(form, open(fp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return {"form": fp, "sheet": png, "events": len(VE["events"])}


def load_read(job: str, shot: str) -> dict | None:
    fp = os.path.join(job, "09-qa", "sfx", f"{shot}.read.json")
    if not os.path.isfile(fp):
        return None
    R = json.load(open(fp, encoding="utf-8"))
    bad = []
    for k, v in (R.get("shot_read") or {}).items():
        if k in VOCAB and v and v not in VOCAB[k]:
            bad.append(f"shot_read.{k} = {v!r}")
    for e in R.get("events") or []:
        for k, v in e.items():
            if k in VOCAB and v and v not in VOCAB[k]:
                bad.append(f"{e.get('id')}.{k} = {v!r}")
    if bad:
        raise SystemExit("error: the read is off its vocabulary — " + "; ".join(bad))
    return R


def _take_of(job: str, shot: str) -> str:
    rp = os.path.join(job, "09-qa", "motion", f"{shot}.motion.json")
    try:
        return os.path.join(job, json.load(open(rp, encoding="utf-8"))["file"])
    except (OSError, ValueError, KeyError):
        raise SystemExit(f"error: no --clip, and no motion report for {shot} to say which take is in the cut")


def conform(job: str, shot: str, sfx_files: list, clip: str | None = None, tags: dict | None = None,
            tracks: list | None = None, out: str | None = None, mux: bool = False, seed: int | None = None,
            room: str = "auto", catalogues: str | None = None) -> dict:
    np = _np()
    import shot_graph as SG
    prompt = os.path.join(job, "01-script", "prompts", f"{shot}.clip.prompt.md")
    T = {**clip_tags(prompt), **{k: v for k, v in (tags or {}).items() if v not in (None, "")}}
    clip = clip or _take_of(job, shot)
    info = SG.probe(clip)
    fps = info.get("fps") or 24.0
    R = load_read(job, shot)
    findings = []
    if R:
        sr_ = R.get("shot_read") or {}
        for k in ("space", "distance"):
            if sr_.get(k) and not (tags or {}).get(k) and not clip_tags(prompt).get(k):
                T[k] = sr_[k]                                      # flags > prompt `sfx:` > the read
        if R.get("clip_sha256") and R["clip_sha256"] != sha256_file(clip):
            findings.append("the read was made on another take — read this one again")
    count = int(T["count"]) if str(T.get("count", "")).isdigit() else None
    VE = visual_events(clip, tracks=tracks, count=count)
    events = VE["events"]
    if R:
        rev = R.get("events") or []
        for e in events:                                           # match each read row to its event by time
            row = min(rev, key=lambda r: abs(float(r.get("t", -9)) - e["t"]), default=None)
            if row and abs(float(row.get("t", -9)) - e["t"]) <= 2 / fps:
                e["read"] = {k: v for k, v in row.items() if k in VOCAB and v}
        dropped_by_read = [e for e in events if (e.get("read") or {}).get("keep") == "no"]
        events = [e for e in events if e not in dropped_by_read]
        for e in dropped_by_read:
            e["why_dropped"] = "the read: no sound"
        VE["dropped"] = VE["dropped"] + dropped_by_read
        for t in (R.get("shot_read") or {}).get("extra_events") or []:
            events.append({"t": round(float(t), 4), "frame": int(round(float(t) * fps)), "x": 0.5, "y": 0.5,
                           "strength": float(np.median([x["strength"] for x in events] or [1.0])), "area": 1,
                           "kind": "hit", "busy_s": 0.0, "confidence": "high", "votes": ["read"], "read": {}})
        events.sort(key=lambda e: e["t"])
        seen = str((R.get("shot_read") or {}).get("count_seen") or "")
        if seen.isdigit() and int(seen) != len(events) and count is None:
            findings.append(f"the read sees {seen} event(s), the conform has {len(events)} — add the missing ones "
                            f"to extra_events, or mark the extra ones keep: no")
    VE["events"] = events
    os.makedirs(os.path.join(job, "09-qa", "sfx"), exist_ok=True)
    json.dump(VE, open(os.path.join(job, "09-qa", "sfx", f"{shot}.events.json"), "w"), indent=1)
    # the library side: every attack in every file given
    pool = []
    for f in sfx_files:
        ix = load_index(f)
        if ix["kind"] == "bed":
            raise SystemExit(f"error: {os.path.basename(f)} is a bed (no separable events: {len(ix['events'])} attacks "
                             f"in {ix['duration']} s) — lay it as a bed, or re-index it with --kind event if it is not")
        x = pcm(f)
        shapes = attack_shapes(x, ix["events"])                   # (v2.68.0) the shape of each attack
        top_db = max((o["peak_db"] for o in ix["events"]), default=0.0)
        for i, o in enumerate(ix["events"]):
            pool.append({"file": f, "i": i, "x": x, "material": ix.get("material"), "rel_db": o["peak_db"] - top_db,
                         **o, **(shapes[i] if i < len(shapes) else {})})
    if not pool:
        raise SystemExit("error: no attacks found in the SFX given")
    strength_buckets(events)
    rng = np.random.default_rng(seed if seed is not None else int(hashlib.sha1(shot.encode()).hexdigest()[:8], 16))
    # (v2.68.0) no more "a random attack inside the loudness third": peak level is how hot the take was recorded,
    # not how hard the hit was. The attack is chosen by its shape against the event (plan rounds 1–3, both models).
    dur = info["duration"]
    mix = np.zeros((int(dur * SR) + SR, 2), np.float32)
    mix_dry = np.zeros_like(mix)          # the same placements with no room: what the re-check counts (a
                                          # measured room's reflections are not events, and cannot move an attack)
    space_size = ((R or {}).get("shot_read") or {}).get("space_size") or "medium"
    rt60 = SPACE_RT60.get(T.get("space") or "interior", 0.5) * SPACE_SIZE.get(space_size, 1.0)
    ir, ir_used = None, None
    if rt60 > 0 and room != "synthetic":
        pick = pick_ir(T.get("space") or "interior", space_size, rt60, catalogues) if room == "auto" else \
            {"path": room, "name": os.path.basename(room), "library": None}
        if pick:
            ir = load_ir(pick["path"])
            if ir is not None:
                ir_used = {k: pick.get(k) for k in ("library", "name", "rel", "decay_s", "licence", "paid_ads")}
                ir_used["file"] = os.path.basename(pick["path"])
    if ir is None:
        ir = _ir(rt60, seed=7)
        if rt60 > 0:
            findings.append(f"room: a synthetic {rt60:.2f} s tail — no measured space in the catalogues matched "
                            f"{T.get('space') or 'interior'}/{space_size}" if room == "auto" else
                            f"room: a synthetic {rt60:.2f} s tail")
    largest = max([e.get("area", 1) for e in events] or [1])
    placed, last = [], None
    for k, e in enumerate(events):
        rd = e.get("read") or {}
        if rd.get("force"):
            e["bucket"] = rd["force"]
        mats = {rd.get("object_material"), rd.get("surface_material")} - {None, "", "none", "other"}
        mpool = [p for p in pool if p.get("material") in mats] or pool  # a file indexed with the read's material first
        cands = [p for p in mpool if (p["file"], p["i"]) != last] or mpool
        src, e["attack_fit"] = choose_attack(cands, need_of(rd, e), rng)
        last = (src["file"], src["i"])
        TT = dict(T)
        if rd.get("size"):
            TT["size"] = rd["size"]
        if rd.get("wet") == "yes" and not T.get("surface"):
            TT["surface"] = "wet"
        P = params_for({**e, "offscreen": e.get("offscreen") or rd.get("visible") == "no"}, TT, rng, largest)
        occ = OCCLUDED.get(rd.get("occluded") or "none")
        if occ:
            P["lowpass"] = min(P["lowpass"], occ["lp"]); P["gain_db"] = round(P["gain_db"] + occ["gain"], 2)
            P["why"].append(f"behind {rd['occluded']}")
        if rd:
            P["why"].append("read: " + ", ".join(f"{k_}={v_}" for k_, v_ in rd.items() if k_ != "keep"))
        nxt = events[k + 1]["t"] if k + 1 < len(events) else dur
        s0, a0 = src["start"], src["attack"]
        seg_end = src["end"]
        if e.get("kind") == "slide":
            seg_end = min(src["x"].size / SR, max(seg_end, s0 + (a0 - s0) + e.get("busy_s", 0) + 0.15))
        seg = src["x"][int(s0 * SR):int(seg_end * SR)].astype(np.float32)
        if seg.size < 64:
            continue
        seg = _pitch(seg, P["pitch_st"])
        lead = (a0 - s0) / (2 ** (P["pitch_st"] / 12.0))          # the attack's offset inside the cut piece
        seg = _fft_filter(seg, SR, lp=P["lowpass"], hp=HIGHPASS, shelf_db=P["shelf_db"])
        fi, fo = int(0.002 * SR), int(min(0.02 * SR, seg.size // 4))
        seg[:fi] *= np.linspace(0, 1, fi)                          # heads fade, tails ring out (the council)
        seg[-fo:] *= np.linspace(1, 0, fo)
        seg *= 10 ** (P["gain_db"] / 20)
        seg_dry = seg.copy()
        if ir is not None and P["wet"] > 0:
            wet = _fftconv(seg, ir)[: seg.size + ir.size // 2] * P["wet"] * 3.0
            dry = np.concatenate([seg, np.zeros(wet.size - seg.size, np.float32)])
            seg = (dry * (1 - P["wet"]) + wet).astype(np.float32)
        th = (P["pan"] + 1) * np.pi / 4                            # constant power
        st = np.stack([seg * np.cos(th), seg * np.sin(th)], axis=1) * np.sqrt(2)
        st_d = np.stack([seg_dry * np.cos(th), seg_dry * np.sin(th)], axis=1) * np.sqrt(2)
        t_attack = e["t"] + P["lag_frames"] / fps                  # on its frame, or a frame late — never early
        at = int(round((t_attack - lead) * SR))
        if at < 0:
            st, st_d = st[-at:], st_d[-at:]; at = 0
        endi = min(mix.shape[0], at + st.shape[0])
        mix[at:endi] += st[:endi - at]
        endd = min(mix.shape[0], at + st_d.shape[0])
        mix_dry[at:endd] += st_d[:endd - at]
        placed.append({"event_t": e["t"], "attack_t": round(t_attack, 4), "source": os.path.basename(src["file"]),
                       "source_event": src["i"], "kind": e.get("kind"), "confidence": e["confidence"],
                       "attack_fit": e.get("attack_fit"),                  # (v2.68.0) why this attack, in words
                       "votes": e["votes"], **{k_: P[k_] for k_ in ("gain_db", "lowpass", "wet", "pitch_st",
                                                                    "shelf_db", "lag_frames", "pan", "size", "why")}})
    mix, mix_dry = mix[: int(dur * SR)], mix_dry[: int(dur * SR)]
    peak = float(np.abs(mix).max()) if mix.size else 0.0
    if peak > 0.89:
        mix *= 0.89 / peak                                         # headroom, never a clip
    out = out or os.path.join(job, "06-sfx", "conform", f"{shot}.sfx.wav")
    write_wav(out, mix)
    dry_p = os.path.join(job, "09-qa", "sfx", f"{shot}.sfx.dry.wav")
    write_wav(dry_p, mix_dry)
    rep = {"shot": shot, "clip": os.path.relpath(clip, job), "clip_sha256": sha256_file(clip), "render": os.path.relpath(out, job),
           "fps": fps, "tags": T, "sources": [{"file": os.path.relpath(f, job) if os.path.abspath(f).startswith(os.path.abspath(job))
                                               else os.path.basename(f), "sha256": sha256_file(f)} for f in sfx_files],
           "room": ir_used or {"synthetic_rt60_s": round(rt60, 2)},
           "events": placed, "dropped": [{"t": d["t"], "confidence": d["confidence"], "why": d.get("why_dropped", "low confidence")}
                                         for d in VE["dropped"]],
           "read": (R or {}).get("read_by") or None, "findings": findings,
           "conformed": dt.datetime.now().isoformat(timespec="minutes"), "thresholds_tag": "[assumed] where marked"}
    if mux:
        mp4 = os.path.splitext(out)[0] + ".mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", clip, "-i", out, "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", mp4], check=True)
        rep["mux"] = os.path.relpath(mp4, job)
    rep["dry"] = os.path.relpath(dry_p, job)
    rep["verify"] = verify_render(dry_p, placed, fps)
    json.dump(rep, open(out + ".conform.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return rep


def verify_render(render: str, placed: list, fps: float) -> dict:
    """The render alone, not the mix: one attack per placed event, each 0 to +1 frame after its frame."""
    ons = detect_onsets(pcm(render))
    tol = 0.012                                                    # the detector's own resolution, about 2 hops
    probs, matched = [], set()
    for p in placed:
        lo, hi = p["event_t"] - tol, p["event_t"] + 1.0 / fps + tol + p.get("lag_frames", 0) / fps
        hit = [i for i, o in enumerate(ons) if lo <= o["attack"] <= hi and i not in matched]
        if not hit:
            near = min(ons, key=lambda o: abs(o["attack"] - p["event_t"]), default=None)
            probs.append(f"event at {p['event_t']} s: no attack within 0 to +1 frame"
                         + (f" (nearest {near['attack']} s)" if near else ""))
            continue
        matched.add(hit[0])
        if ons[hit[0]]["attack"] < p["event_t"] - tol:
            probs.append(f"event at {p['event_t']} s: the attack lands early")
    extra = [o["attack"] for i, o in enumerate(ons) if i not in matched
             and not any(abs(o["attack"] - p["attack_t"]) < 0.25 for p in placed)]
    if extra:
        probs.append(f"{len(extra)} attack(s) with no visual event: {', '.join(str(t) for t in extra[:5])}")
    return {"ok": not probs, "placed": len(placed), "detected": len(ons), "problems": probs}


# =================================================================================================
# C + D. sound across the cuts
# =================================================================================================
HANDOFF = {"motion": "overlap", "action": "overlap", "carry": "carry", "flip": "break", "reverse": "break",
           "whip": "whip", "graphic": "break"}


def joins_plan(job: str, whoosh: str | None = None, pan: str = "off", fps: float = 24.0) -> dict:
    np = _np()
    import motion_qa as MQ
    js = sorted(glob.glob(os.path.join(job, "09-qa", "motion", "*.joins.json")), key=os.path.getmtime)
    if not js:
        raise SystemExit("error: no joins report — run motion_qa.py cut on the cut first")
    J = json.load(open(js[-1], encoding="utf-8"))
    prompts = os.path.join(job, "01-script", "prompts")
    rows, whips = [], 0
    for j in J.get("joins", []):
        a = j.get("from")
        plan = MQ._plan(os.path.join(prompts, f"{a}.clip.prompt.md")) if a else {}
        jn = (plan.get("join") or (j.get("planned") or {}).get("join") or "").lower()
        act = next((v for k, v in HANDOFF.items() if k in jn), "plain")
        if j.get("screen_dir") == "flipped" and act == "overlap":
            act = "break"                                          # a flip on screen takes a clean break
        note = {"overlap": "the outgoing sound's tail runs 4–8 frames past the cut; the incoming hit lands on its frame",
                "carry": "one ambience clip spans both shots, unchanged across the cut",
                "break": "no tail crosses the cut; the ambience changes on the cut",
                "whip": "one whoosh, its peak on the cut",
                "plain": "no planned hand-off: trim tails at the cut"}[act]
        row = {"n": j.get("n"), "t": j.get("t"), "from": a, "to": j.get("to"), "join": jn or None, "sound": act,
               "note": note}
        if act == "whip":
            whips += 1
            if whips > WHIP_MAX:
                row["sound"], row["note"] = "plain", f"whoosh cap reached ({WHIP_MAX} per ad): a plain cut instead"
            else:
                exitd = set((plan.get("exit") or "").lower().split()) & {"left", "right"}
                row["sweep"] = ("left" if "left" in exitd else "right") if exitd else None
        rows.append(row)
    # D. the ramps (house rule C4): a ramp is heard as much as seen — the clip's own audio is muted under it
    # and its cue (`ramp: … sfx=`) carries it; markers at its place in the cut (`cut_in=` / `cut_out=`)
    ramps = []
    for p in sorted(glob.glob(os.path.join(prompts, "*.clip.prompt.md"))):
        pl = MQ._plan(p)
        kv = MQ.parse_ramp(pl.get("ramp"))
        if not kv:
            continue
        shot = os.path.basename(p).split(".")[0]
        ci, co = MQ._num(kv.get("cut_in")), MQ._num(kv.get("cut_out"))
        kind = (kv.get("kind") or "").lower()
        hit = ("its low point on the trigger frame" if kind == "slow" else "its hit on the contact")
        ramps.append({"shot": shot, "kind": kind, "speed": kv.get("speed"), "cue": kv.get("sfx") or None,
                      "t": ci, "t_out": co,
                      "note": (f"mute {shot}'s own audio from {ci:.2f} to {co:.2f} s; the cue {kv.get('sfx')!r} carries "
                               f"the ramp, {hit}" if ci is not None and co is not None else
                               f"no place in the cut yet — add cut_in=/cut_out= to {shot}'s `ramp:` once cut")})
    stem = os.path.splitext(os.path.basename(js[-1]))[0].replace(".joins", "")
    rep = {"cut": J.get("cut"), "joins": rows, "whooshes": min(whips, WHIP_MAX), "ramps": ramps,
           "made": dt.datetime.now().isoformat(timespec="minutes")}
    if whoosh:
        x = pcm(whoosh)
        ons = detect_onsets(x)
        pk = int(np.argmax(np.abs(x))) / SR if x.size else 0.0
        end_t = max([r["t"] or 0 for r in rows] + [0]) + 2.0
        stemw = np.zeros((int(end_t * SR), 2), np.float32)
        for r in rows:
            if r["sound"] != "whip":
                continue
            seg = _fft_filter(x.copy(), SR, hp=HIGHPASS)
            n = seg.size
            if pan == "follow" and r.get("sweep"):
                p = np.linspace(-PAN_MAX, PAN_MAX, n) * (1 if r["sweep"] == "right" else -1)
            else:
                p = np.zeros(n)
            th = (p + 1) * np.pi / 4
            st = np.stack([seg * np.cos(th), seg * np.sin(th)], axis=1) * np.sqrt(2)
            at = int(round((r["t"] - pk) * SR))
            if at < 0:
                st = st[-at:]; at = 0
            e = min(stemw.shape[0], at + st.shape[0])
            stemw[at:e] += st[: e - at]
        outw = os.path.join(job, "06-sfx", "conform", f"{stem}.joins.wav")
        write_wav(outw, stemw)
        rep["stem"] = os.path.relpath(outw, job)
        rep["sources"] = [{"file": os.path.basename(whoosh), "sha256": sha256_file(whoosh)}]
        json.dump({"render": rep["stem"], "sources": rep["sources"], "kind": "joins"},
                  open(outw + ".conform.json", "w"), indent=1)
    os.makedirs(os.path.join(job, "09-qa", "sfx"), exist_ok=True)
    json.dump(rep, open(os.path.join(job, "09-qa", "sfx", f"{stem}.joins-sound.json"), "w"), indent=1)
    edl = ["TITLE: joins sound plan", "FCM: NON-DROP FRAME", ""]
    col = {"overlap": "ResolveColorGreen", "carry": "ResolveColorBlue", "break": "ResolveColorRed",
           "whip": "ResolveColorYellow", "plain": "ResolveColorCream"}
    for i, r in enumerate(rows, 1):
        tc = _tc(r["t"] or 0, fps)
        edl += [f"{i:03d}  001      V     C        {tc} {_tc((r['t'] or 0) + 1 / fps, fps)} {tc} {_tc((r['t'] or 0) + 1 / fps, fps)}",
                f"{r['sound'].upper()}: {r['note']} |C:{col[r['sound']]} |M:{r['sound']} |D:1", ""]
    k = len(rows)
    for r in ramps:
        if r["t"] is None or r["t_out"] is None:
            continue
        for t, what in ((r["t"], "RAMP IN"), (r["t_out"], "RAMP OUT")):
            k += 1
            tc = _tc(t, fps)
            edl += [f"{k:03d}  001      V     C        {tc} {_tc(t + 1 / fps, fps)} {tc} {_tc(t + 1 / fps, fps)}",
                    f"{what} {r['shot']} ({r['kind']} {r['speed']} %): {r['note']} |C:ResolveColorPurple |M:ramp |D:1", ""]
    open(os.path.join(job, "09-qa", "sfx", f"{stem}.joins-sound.edl"), "w").write("\n".join(edl))
    return rep


# =================================================================================================
# the libraries: what is on the machine, searchable, with the licence that comes with each file
# =================================================================================================
# Author, 2026-10-26: "I have the Fairlight SFX pack too installed … You can find many effects there too",
# then the Final Cut Pro content extracted beside it. A catalogue per library: one JSONL row per file
# (where it is under the library's root, its category, its words, length, channels) and one
# <name>.library.json with the roots it has been seen at and the licence. The rows hold paths RELATIVE to
# the root, because the same folder is /Users/…/Movies/… on the Mac and $HOME/mnt/<folder> in a session.
AUDIO_LIB_EXT = (".wav", ".aif", ".aiff", ".m4a", ".mp3", ".flac", ".caf", ".ogg")
BUILD_BUDGET_S = 150        # one call stays inside a 180 s shell; `build` resumes where it stopped
LIB_TAG_KEYS = ("title", "comment", "description", "genre", "album", "keywords", "subject", "category")
IR_SPACE_WORDS = {   # words in an impulse response's name that place it, per space [practitioner]
    "bathroom": ["bath", "bathroom", "tile", "tiled", "shower", "toilet", "washroom"],
    "kitchen": ["kitchen", "pantry", "dining"], "hall": ["hall", "church", "abbey", "cathedral", "chapel", "theater",
                                                         "theatre", "auditorium", "amphitheater", "arena"],
    "car": ["car", "vehicle", "van", "auto"], "street": ["street", "alley", "courtyard", "outdoor", "outside", "yard"],
    "forest": ["forest", "wood", "woods", "outdoor", "garden", "park"],
    "interior": ["room", "living", "bedroom", "office", "apartment", "house", "home", "lounge", "studio"],
    "studio": ["studio", "booth", "vocal", "drum", "live"], "exterior": ["outdoor", "outside", "street", "yard"]}
IR_NOT_A_SPACE = ["plate", "spring", "chamber", "reverse", "fx", "gate", "gated", "sweep", "synth", "pad", "echo"]
IR_OUTDOOR = {"exterior", "street", "forest"}      # outdoors a room tail is wrong unless an IR names the place
KNOWN_LICENCES = {"pixabay content license": "yes", "cc0": "yes", "cc0 1.0": "yes",
                  "remarc": "no", "bbc remarc": "no",       # BBC Sound Effects: personal, educational, research only
                  "cc by-nc": "no", "cc by-nc 4.0": "no"}


def _words(*texts) -> list:
    out = []
    for t in texts:
        for w in re.findall(r"[a-z0-9]+", str(t or "").lower()):
            if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
                w = w[:-1]
            if len(w) > 1 and not w.isdigit():
                out.append(w)
    return out


def catalogue_dir(cat: str | None = None) -> str:
    import cine_home as _ch  # noqa: E402  (3.0.0) the one home resolver
    return cat or os.environ.get("CINE_SFX_CATALOGUES") or os.path.join(_ch.home(merge=False), "sfx-catalogues")


def resolve_root(roots: list) -> str | None:
    """The first root that exists here; else the same folder under a session mount ($HOME/mnt/<folder>)."""
    for r in roots:
        if os.path.isdir(r):
            return r
    mounts = glob.glob(os.path.join(os.path.expanduser("~"), "mnt", "*"))
    for r in roots:
        parts = [p for p in r.replace("\\", "/").split("/") if p]
        for m in mounts:
            mb = os.path.basename(m)
            for i, p in enumerate(parts):
                if p == mb or mb.endswith("--" + p) or mb == "--".join(parts[max(0, i - 1):i + 1]):
                    cand = os.path.join(m, *parts[i + 1:])
                    if os.path.isdir(cand):
                        return cand
    return None


VENDOR_V = 2                 # bump when vendor_metadata reads a sheet differently: catalogues re-merge, no re-probe


def vendor_metadata(root: str) -> dict:
    """The vendor's own metadata sheets inside a library (UCS "Metadata Import" CSVs, as Ocular Sounds ships one per
    pack; added 2026-10-27): file name → its UCS category, subcategory and CatID, keywords, description, musical key
    and tempo. Read once per build; a sheet without a Filename column is not one."""
    import csv
    import unicodedata
    out = {}
    for f in glob.glob(os.path.join(root, "**", "*.csv"), recursive=True):
        try:
            with open(f, encoding="utf-8-sig", newline="") as fh:
                rd = csv.DictReader(fh)
                if "Filename" not in (rd.fieldnames or []):
                    continue
                for row in rd:
                    fn = unicodedata.normalize("NFC", (row.get("Filename") or "").strip())
                    if not fn:
                        continue
                    bpm = re.search(r"(\d{2,3})\s*bpm", fn, re.I) or re.search(r"(\d{2,3})\s*bpm", row.get("Description") or "", re.I)
                    out[fn] = {"catid": (row.get("CatID") or "").strip(), "category": (row.get("Category") or "").strip(),
                               "subcategory": (row.get("SubCategory") or "").strip(),
                               "keywords": (row.get("Keywords") or "").strip()[:300],
                               "vendor_description": (row.get("Description") or "").strip()[:300],
                               "key": _musical_key(row.get("Key")),
                               "bpm": int(bpm.group(1)) if bpm else None, "sheet": os.path.relpath(f, root)}
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
    return out


def _musical_key(k) -> str | None:
    """A sheet's Key column only when it names a key (A, F#, Bbm, Gmaj, D minor) — some vendors reuse the column."""
    k = str(k or "").strip()
    return k if re.match(r"^[A-Ga-g][#b]?\s*(m|min|minor|maj|major)?$", k) else None


def _merge_vendor(row: dict, vm: dict | None) -> dict:
    if not vm:
        return row
    row["ucs"] = {k: vm[k] for k in ("catid", "category", "subcategory") if vm.get(k)}
    for k in ("key", "bpm"):
        if vm.get(k):
            row[k] = vm[k]
        else:
            row.pop(k, None)
    row["vendor_sheet"] = vm.get("sheet")
    row["vendor_v"] = VENDOR_V
    row["words"] = sorted(set(row.get("words") or []) | set(_words(vm.get("keywords"), vm.get("vendor_description"),
                                                                   vm.get("category"), vm.get("subcategory"))))
    if not row.get("description"):
        row["description"] = vm.get("vendor_description") or vm.get("keywords") or ""
    return row


def _probe_audio(p: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags:stream=channels,sample_rate",
                        "-of", "json", p], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
        s = (j.get("streams") or [{}])[0]
        tags = {k.lower(): v for k, v in (j.get("format", {}).get("tags") or {}).items()}
        return {"duration": round(float(j["format"]["duration"]), 3), "channels": int(s.get("channels") or 0),
                "sample_rate": int(s.get("sample_rate") or 0), "tags": tags}
    except (ValueError, KeyError, TypeError):
        return {}


def build_library(root: str, name: str, cat: str | None = None, kind: str = "sfx", licence: str | None = None,
                  paid_ads: str | None = None, basis: str | None = None, condition: str | None = None,
                  licence_csv: str | None = None, budget_s: float = BUILD_BUDGET_S, mac_root: str | None = None) -> dict:
    import time
    t0 = time.time()
    d = catalogue_dir(cat); os.makedirs(d, exist_ok=True)
    mp, rp = os.path.join(d, f"{name}.library.json"), os.path.join(d, f"{name}.jsonl")
    meta = json.load(open(mp, encoding="utf-8")) if os.path.isfile(mp) else {"name": name, "kind": kind, "roots": []}
    for r in (mac_root, os.path.abspath(root)):
        if r and r not in meta["roots"] and not r.startswith(os.path.join(os.path.expanduser("~"), "mnt")):
            meta["roots"].append(r)
    if not meta["roots"]:
        meta["roots"].append(os.path.abspath(root))         # a session mount only: say so, it moves
        meta["roots_note"] = "seen only under a session mount — pass --mac-root once to record the real path"
    for k, v in (("licence", licence), ("paid_ads", paid_ads), ("basis", basis), ("condition", condition)):
        if v:
            meta[k] = v
    if licence or paid_ads:
        meta["checked"] = dt.date.today().isoformat()
    per_file = {}
    if licence_csv:
        import csv
        for row in csv.DictReader(open(licence_csv, encoding="utf-8")):
            fn = row.get("filename") or row.get("file") or ""
            if fn:
                per_file[fn] = {k: row.get(k2) for k, k2 in (("licence", "license"), ("author", "author"),
                                                             ("source_url", "source_url")) if row.get(k2)}
    rows = {}
    if os.path.isfile(rp):
        for ln in open(rp, encoding="utf-8"):
            if ln.strip():
                r = json.loads(ln); rows[r["rel"]] = r
    files = sorted(p for p in glob.glob(os.path.join(root, "**", "*"), recursive=True)
                   if p.lower().endswith(AUDIO_LIB_EXT) and os.path.isfile(p) and not os.path.basename(p).startswith("._"))
    import unicodedata
    vendor = vendor_metadata(root)
    done = left = 0
    for p in files:
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        st = os.stat(p)
        old = rows.get(rel)
        vm = vendor.get(unicodedata.normalize("NFC", os.path.basename(p)))
        if old and old.get("size") == st.st_size and int(old.get("mtime", 0)) == int(st.st_mtime):
            if vm and (old.get("vendor_sheet") != vm.get("sheet") or old.get("vendor_v") != VENDOR_V):  # no re-probe needed
                rows[rel] = _merge_vendor(old, vm); done += 1
            continue
        if time.time() - t0 > budget_s:
            left += 1; continue
        pr = _probe_audio(p)
        if not pr:
            rows[rel] = {"rel": rel, "error": "unreadable", "size": st.st_size, "mtime": int(st.st_mtime)}; continue
        parts = rel.split("/")
        stem = os.path.splitext(parts[-1])[0]
        t = pr["tags"]
        row = {"rel": rel, "category": "/".join(parts[:-1]), "name": stem, "duration": pr["duration"],
               "channels": pr["channels"], "sample_rate": pr["sample_rate"], "size": st.st_size, "mtime": int(st.st_mtime),
               "description": " · ".join(str(t[k]) for k in LIB_TAG_KEYS if t.get(k))[:300],
               "source_tag": " · ".join(str(t[k]) for k in ("artist", "copyright", "album") if t.get(k))[:200]}
        row["words"] = sorted(set(_words(os.path.splitext(rel)[0].replace("/", " "), row["description"])) - LIB_EXT_WORDS)
        if kind == "ir":
            m = re.match(r"^(\d+(?:\.\d+)?)\s*s(?=[\s_\-]|$)", stem)
            row["decay_s"] = float(m.group(1)) if m else None
            cat_l = row["category"].lower()
            row["size_class"] = next((c for c in ("small", "medium", "large", "surround") if c in cat_l), None)
        if parts[-1] in per_file:
            row.update(per_file[parts[-1]])
        rows[rel] = _merge_vendor(row, vm); done += 1
    for rel in [r for r in rows if not os.path.isfile(os.path.join(root, r))]:
        del rows[rel]                                        # gone from the library → gone from the catalogue
    with open(rp + ".part", "w", encoding="utf-8") as fh:
        for rel in sorted(rows):
            fh.write(json.dumps(rows[rel], ensure_ascii=False) + "\n")
    os.replace(rp + ".part", rp)
    meta["files"] = len(rows); meta["built"] = dt.datetime.now().isoformat(timespec="minutes")
    json.dump(meta, open(mp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return {"catalogue": rp, "files": len(rows), "indexed_now": done, "left": left, "meta": meta}


def load_catalogues(cat: str | None = None, names: list | None = None, kind: str | None = None) -> list:
    out = []
    d = catalogue_dir(cat)
    for mp in sorted(glob.glob(os.path.join(d, "*.library.json"))):
        meta = json.load(open(mp, encoding="utf-8"))
        if names and meta["name"] not in names:
            continue
        if kind and meta.get("kind", "sfx") != kind:
            continue
        root = resolve_root(meta.get("roots") or [])
        rp = os.path.join(d, f"{meta['name']}.jsonl")
        if not os.path.isfile(rp):
            continue
        for ln in open(rp, encoding="utf-8"):
            if not ln.strip():
                continue
            r = json.loads(ln)
            if r.get("error"):
                continue
            r["library"], r["kind"] = meta["name"], meta.get("kind", "sfx")
            r["path"] = os.path.join(root, r["rel"]) if root else None
            own = r.get("licence")                       # a per-file licence (a CSV beside the library) wins
            r["licence"] = own or meta.get("licence")
            r["paid_ads"] = KNOWN_LICENCES.get(str(own).strip().lower(), "unverified") if own \
                else meta.get("paid_ads", "unverified")
            r["condition"] = meta.get("condition")
            out.append(r)
    return out


def _key_root(k) -> str | None:
    m = re.match(r"^\s*([A-Ga-g])([#b]?)", str(k or ""))
    if not m:
        return None
    flat = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
    n = m.group(1).upper() + m.group(2)
    return flat.get(n, n)


def search_library(query: str, cat: str | None = None, names: list | None = None, kind: str = "sfx",
                   max_dur: float | None = None, paid_ads_only: bool = False, n: int = 12, key: str | None = None,
                   bpm: float | None = None) -> list:
    """Search by words; `key` keeps only sounds whose vendor sheet names that root note (a Felt ping for a bed in
    C#m: --key C#), `bpm` only loops at that tempo (±1). Both come from the vendor's metadata sheet."""
    q = _words(query)
    kr = _key_root(key) if key else None
    hits = []
    for r in load_catalogues(cat, names, kind):
        if max_dur and r.get("duration", 0) > max_dur:
            continue
        if paid_ads_only and r.get("paid_ads") != "yes":
            continue
        if kr and _key_root(r.get("key")) != kr:
            continue
        if bpm and not (r.get("bpm") and abs(float(r["bpm"]) - float(bpm)) <= 1):
            continue
        w = set(r.get("words") or []) - LIB_EXT_WORDS          # (v2.68.0) old rows still carry `wav`, `m4a`
        name_w = set(_words(r.get("name")))
        score = sum(2.0 if x in name_w else 1.0 for x in q if x in w)
        score += sum(0.5 for x in q for y in w if x != y and len(x) > 3 and (y.startswith(x) or x.startswith(y)))
        if score > 0:
            hits.append({**r, "score": round(score, 2)})
    hits.sort(key=lambda r: (-r["score"], r.get("duration", 0)))
    return hits[:n]


# =================================================================================================
# (v2.68.0) MEASURED LIBRARIES — each catalogue row gains the shapes of its attacks, so a search can ask "does this
# hit sound like that event" and not only "do the words match". Stored in the catalogue (never beside the audio:
# 15,000 sidecars in a vendor's folder would be litter). Incremental and resumable inside BUILD_BUDGET_S.
# =================================================================================================
MEASURE_MAX_ONSETS = 24          # attacks kept per file (a 12-hit foley file keeps every hit) [assumed]
LIB_EXT_WORDS = {"wav", "aif", "aiff", "m4a", "mp3", "flac", "caf", "ogg"}   # a file extension is not a word
MUSIC_GRID_MIN = 0.15            # music_fit's own downbeat warning line, for the numpy engine only (plan round 3)
MUSIC_STEADY_MIN = 0.8           # a beat grid steady enough to fit to (music_fit's tempo_steady) [assumed]


def measure_file(path: str, kind: str = "sfx", duration: float | None = None) -> dict:
    """The row's `measure` block. SFX: type (one-hit / sequence / bed) and the attacks' shapes. Music: tempo, the
    downbeat confidence, the engine, the length, the ending, and whether its grid can be scored."""
    if kind == "music":
        import music_fit as MF
        try:
            M = MF.analyse(path, engine="numpy")
        except SystemExit as e:                     # fewer than four beats: a drone, a pad, a riser
            return {"v": SHAPE_V, "kind": "music", "grid": "none", "why": str(e)[:160]}
        conf = (M.get("confidence") or {}).get("downbeats")
        steady = (M.get("confidence") or {}).get("tempo_steady")
        # reliable = the BEATS are steady (build review 1, Sonnet: on clean synthetic 4/4 the numpy downbeat confidence
        # sat under 0.15 in 10 of 12 tracks, which would have switched the fitter off); the downbeat guess is reported
        reliable = M["engine"] != "numpy" or (steady is not None and steady >= MUSIC_STEADY_MIN)
        return {"v": SHAPE_V, "kind": "music", "engine": M["engine"], "tempo": M["tempo"], "meter": M["meter"],
                "downbeat_conf": conf, "tempo_steady": steady, "grid": "reliable" if reliable else "unreliable",
                "downbeats": "sure" if (M["engine"] != "numpy" or (conf or 0) >= MUSIC_GRID_MIN) else "uncertain",
                "bars": len(M["bars"]), "duration": M["duration"], "ending": (M.get("ending") or {}).get("kind")}
    np = _np()
    window = bool(duration and duration > MEASURE_MAX_S)
    x = pcm(path, max_s=MEASURE_MAX_S if window else None)
    if len(x) < 2 * HOP:                             # an empty or click-length file: nothing to measure
        return {"v": SHAPE_V, "kind": "sfx", "error": f"too short to measure ({len(x)} samples)"}
    ons = detect_onsets(x)
    dur = len(x) / SR
    density = len(ons) / max(dur, 1e-3)
    fr = x[: (len(x) // HOP) * HOP].reshape(-1, HOP)
    edb = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    span = float(np.percentile(edb, 99) - np.percentile(edb, 10)) if edb.size else 0.0
    typ = "bed" if (not ons or density > BED_DENSITY or span < BED_RANGE_DB) else \
        ("one-hit" if len(ons) == 1 else "sequence")
    m = {"v": SHAPE_V, "kind": "sfx", "type": typ, "attacks": len(ons)}
    if window:
        m["window_s"] = MEASURE_MAX_S             # only the first part was read: the type and attacks describe it
    if typ != "bed":                                 # beds skip attack and decay (plan round 1, both)
        shapes = attack_shapes(x, ons)
        top_db = max((o["peak_db"] for o in ons), default=0.0)
        allo = [{"n": i, "attack": o["attack"], "peak_db": o["peak_db"], "rel_db": round(o["peak_db"] - top_db, 1),
                 "centroid": o["centroid"], **sh} for i, (o, sh) in enumerate(zip(ons, shapes))]
        # keep the most isolated attacks (the clean single hits a mixer wants), not the first ones (review 1)
        keep = sorted(allo, key=lambda a: -(min(a.get("gap_in_ms", 0), a.get("gap_out_ms", 0))))[:MEASURE_MAX_ONSETS]
        m["onsets"] = sorted(keep, key=lambda a: a["n"])
    return m


def measure_library(name: str, cat: str | None = None, budget_s: float = BUILD_BUDGET_S, progress=print) -> dict:
    """Measure the rows a catalogue has not measured yet (or measured under another SHAPE_V). Resumable: each call
    measures what fits in the budget and says how many remain."""
    import time
    t0 = time.time()
    d = catalogue_dir(cat)
    mp, rp = os.path.join(d, f"{name}.library.json"), os.path.join(d, f"{name}.jsonl")
    if not os.path.isfile(mp) or not os.path.isfile(rp):
        raise SystemExit(f"no catalogue {name!r} in {d} — `library build ROOT --name {name}` first")
    meta = json.load(open(mp, encoding="utf-8"))
    root = resolve_root(meta.get("roots") or [])
    if not root:
        raise SystemExit(f"{name}: none of its roots is reachable on this machine ({meta.get('roots')})")
    rows = [json.loads(ln) for ln in open(rp, encoding="utf-8") if ln.strip()]
    todo = [r for r in rows if not r.get("error") and ((r.get("measure") or {}).get("v") != SHAPE_V
            or ((r.get("measure") or {}).get("error") and (r["measure"].get("tries") or 1) < 2))]
    done = failed = 0
    for r in todo:
        if time.time() - t0 > budget_s:
            break
        p = os.path.join(root, r["rel"])
        try:
            r["measure"] = measure_file(p, meta.get("kind", "sfx"), r.get("duration"))
            done += 1
        except Exception as e:                       # noqa: BLE001  one unreadable file must not stop the library
            r["measure"] = {"v": SHAPE_V, "error": str(e)[:160], "tries": ((r.get("measure") or {}).get("tries") or 0) + 1}
            failed += 1
        if progress and (done + failed) % 200 == 0:
            progress(f"  {name}: {done + failed} of {len(todo)} measured this run …")
    ours = {r["rel"]: (r.get("size"), r.get("mtime"), r["measure"]) for r in rows if r.get("measure")}
    fresh = [json.loads(ln) for ln in open(rp, encoding="utf-8") if ln.strip()]   # a build may have run meanwhile
    for r in fresh:
        o = ours.get(r.get("rel"))
        if o and (r.get("size"), r.get("mtime")) == (o[0], o[1]):
            r["measure"] = o[2]
    left = sum(1 for r in fresh if not r.get("error") and (r.get("measure") or {}).get("v") != SHAPE_V)
    with open(rp + ".part", "w", encoding="utf-8") as fh:
        for r in fresh:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(rp + ".part", rp)
    rows = fresh
    return {"catalogue": rp, "measured_now": done, "failed_now": failed, "left": left, "rows": len(rows)}


# The event's words, expanded: at most three per word, never another action from the read's closed list (thud must
# not become knock — plan rounds 2–3), and never a material (a "glass" synonym of clink made every glass file look
# like a clink — build review 2). The self-test enforces all three rules.
SYNONYMS = {
    "drop": ["fall", "land", "impact"], "splash": ["splosh", "plunge", "splat"], "pour": ["pouring", "fill", "glug"],
    "tap": ["touch", "tick", "pat"], "knock": ["rap", "bang", "door"], "clink": ["ting", "chink", "tink"],
    "thud": ["impact", "hit", "bump"], "step": ["footstep", "foot", "walk"], "scrape": ["scratch", "drag", "grind"],
    "slide": ["glide", "push", "drag"], "rustle": ["crinkle", "leaves", "swish"], "click": ["switch", "tick", "button"],
    "snap": ["break", "crack", "twig"], "pop": ["cork", "burst", "bubble"], "crunch": ["crush", "bite", "gravel"],
    "squeeze": ["squelch", "squish", "press"], "open": ["opening", "unlatch", "lid"], "close": ["closing", "shut", "latch"]}
# what a material sounds like, for the shape tie-break [practitioner, assumed until the blind test]
SLIDE_WHATS = {"slide", "scrape", "pour", "rustle"}   # actions that last: length, not ring, is what fits
RINGING = {"metal", "glass", "ceramic"}
DAMPED = {"fabric", "foliage", "paper", "skin", "food", "rubber", "cardboard", "wood"}
SHARP_MS = {"hard": (0, 20), "medium": (10, 40), "soft": (30, 400)}  # force → time to the peak [assumed]; hard spans
# several 5.3 ms analysis frames (review 1, Grok: 0–10 ms passed only 0 and 5.3 ms)


def expand_words(words: list) -> list:
    out = []
    for w in words:
        out.append(w)
        out += SYNONYMS.get(w, [])
    return list(dict.fromkeys(out))


def need_of(read: dict | None, event: dict | None = None) -> dict:
    """What an event asks of a sound, from the read's closed lists (and the conform's own event kind and busy time).
    Missing fields are kept as missing, so a sheet can say the search fell back to words."""
    rd = read or {}
    ev = event or {}
    return {"what": rd.get("what"), "object_material": rd.get("object_material"),
            "surface_material": rd.get("surface_material"), "force": rd.get("force") or ev.get("bucket"),
            "wet": rd.get("wet"), "kind": ev.get("kind") or "hit", "busy_s": ev.get("busy_s")}


def shape_fit(o: dict, need: dict) -> tuple:
    """(score, reasons) of one measured attack against an event's need. A TIE-BREAK below the identity words until the
    blind listening test says otherwise (plan round 2, Sonnet)."""
    score, why = 0, []
    f = need.get("force")
    if f in SHARP_MS and o.get("sharp_ms") is not None:     # None: inside the last hit's tail, no force point
        lo, hi = SHARP_MS[f]
        if lo <= o["sharp_ms"] <= hi:
            score += 1; why.append(f"{'sharp' if f == 'hard' else 'soft' if f == 'soft' else 'medium'} attack "
                                   f"({o['sharp_ms']:.0f} ms) for a {f} contact")
    obj, surf = need.get("object_material"), need.get("surface_material")
    obj = obj if obj not in (None, "", "none", "other") else None
    surf = surf if surf not in (None, "", "none", "other") else None
    # a soft set-down sounds like the surface it meets (a mug on a desk thuds); a strike like the object (a spoon on a
    # cup rings) — review 1, Grok
    lead_m = (surf or obj) if f == "soft" else (obj or surf)
    mats = {lead_m} if lead_m else set()
    if need.get("kind") != "slide" and mats and o.get("ring_s") is not None:      # ring on hits only (round 3)
        if mats & RINGING and o["ring_s"] >= 0.15 and o.get("centroid", 0) >= 2000:
            score += 1; why.append(f"rings ({o['ring_s']:.2f} s) and bright, like {'/'.join(sorted(mats & RINGING))}")
        elif mats & DAMPED and o["ring_s"] <= 0.08:
            score += 1; why.append(f"damped (rings {o['ring_s']:.2f} s), like {'/'.join(sorted(mats & DAMPED))}")
    if need.get("kind") == "slide" and need.get("busy_s"):
        if o.get("body_s", 0) >= 0.8 * float(need["busy_s"]):
            score += 1; why.append(f"long enough ({o['body_s']:.2f} s) for a {float(need['busy_s']):.2f} s slide")
    if o.get("clean_in") and o.get("clean_out"):
        why.append("clean in and out")
    else:
        why.append("needs a trim (" + ", ".join(x for x, ok in (("noisy start", o.get("clean_in")),
                                                                 ("runs into the next hit", o.get("clean_out"))) if not ok) + ")")
    return score, why


LEVEL_FOR_FORCE = {"hard": 0.0, "medium": -6.0, "soft": -12.0}   # dB under the file's loudest attack [assumed]


def choose_attack(cands: list, need: dict, rng) -> tuple:
    """The attack that plays: the best shape fit to the event; then, among equals, the one whose level inside its own
    file suits the force (a hard event takes a hit near the file's loudest, review 1); then the seeded draw, so
    repeats vary. Returns (attack, {"score", "why"})."""
    scored = [(shape_fit(p, need)[0], p) for p in cands]
    best = max(sc for sc, _ in scored)
    tops = [p for sc, p in scored if sc == best]
    tgt = LEVEL_FOR_FORCE.get(need.get("force"))
    if tgt is not None and all(p.get("rel_db") is not None for p in tops):
        near = min(abs(p["rel_db"] - tgt) for p in tops)
        tops = [p for p in tops if abs(p["rel_db"] - tgt) <= near + 3.0]
    src = tops[int(rng.integers(len(tops)))]
    return src, {"score": best, "why": shape_fit(src, need)[1]}


def best_onset(row: dict, need: dict) -> tuple:
    """(index, score, reasons) of the measured attack in a catalogue row that best fits the need; (None, 0, [])
    when the row is not measured."""
    ons = (row.get("measure") or {}).get("onsets") or []
    if (row.get("measure") or {}).get("v") != SHAPE_V or not ons:
        return None, 0, []
    if need.get("kind") == "slide" and row.get("duration"):
        # a slide is judged on how long the FILE runs from that attack, not one grain's decay: a scrape is many short
        # grains (build review 3, Grok: a 0.4 s scrape beat a 2 s one on its first grain)
        ons = [{**o, "body_s": max(o.get("body_s") or 0.0, float(row["duration"]) - float(o.get("start") or 0.0))}
               for o in ons]
    best = max(range(len(ons)), key=lambda i: (shape_fit(ons[i], need)[0], ons[i].get("clean_in") and ons[i].get("clean_out")))
    s, why = shape_fit(ons[best], need)
    return best, s, why


def search_need(need: dict, cat: str | None = None, names: list | None = None, paid_ads_only: bool = True,
                n: int = 5, use_shape: bool = True) -> dict:
    """Five candidates for one event: identity words first (the read's what and materials, expanded), then the
    measured shape as the tie-break. Returns the rows with plain reasons, and which read fields were known.
    `use_shape=False` is the blind test's word arm: the same words, the same pool (beds off), no shape."""
    known = {k: v for k, v in need.items() if v not in (None, "", "other", "none")}
    missing = [k for k in ("what", "object_material", "surface_material", "force") if k not in known]
    act = need.get("what") if need.get("what") not in (None, "", "other") else None
    mats = [w for w in (need.get("object_material"), need.get("surface_material")) if w and w not in ("other", "none")]
    syn = SYNONYMS.get(act, []) if act else []
    words = list(dict.fromkeys(([act] if act else []) + syn + mats))
    # every catalogue row is scored here (no top-N pool from plain word overlap, where sixty "Hit" files could crowd
    # out the one named "thud" — review 1, Grok)
    pool = [r for r in load_catalogues(cat, names, "sfx") if not paid_ads_only or r.get("paid_ads") == "yes"] \
        if words else []
    rows, unmeasured = [], []
    for r in pool:
        w = set(r.get("words") or []) - LIB_EXT_WORDS
        name_w = set(_words(r.get("name")))
        # the action decides most (its own word in the name above all), then the materials, then the synonyms
        ident = (4.0 if act in name_w else 3.0 if act in w else 0.0) + sum(1.0 for m in set(mats) if m in w) \
            + sum(0.5 for x in syn if x in w)
        if ident <= 0:
            continue
        mt = (r.get("measure") or {})
        if mt.get("v") != SHAPE_V or not mt.get("type"):
            unmeasured.append({**r, "identity": ident})          # off the five: it could be a bed (review 1, Grok)
            continue
        slide = need.get("kind") == "slide"
        if mt["type"] == "bed":
            if mt.get("window_s"):    # its first minute had no separate attack; the rest was never read (review 3, Grok)
                unmeasured.append({**r, "identity": ident, "partly": True})
            continue
        if use_shape:
            i, s, why = best_onset(r, need)
        else:                                         # the blind word arm: no shape anywhere, the first kept attack
            i, s, why = (0, 0, []) if (mt.get("onsets") or []) else (None, 0, [])
        on_ = (mt.get("onsets") or [None])[i] if i is not None else None
        out_s, sustain = None, None
        if on_ and slide:
            # a slide runs to the picture's busy time, never one grain (build review 3, Grok: a chair scrape's grain
            # falls off in 40 ms, so a grain-based out-point played the scrape as a tick)
            sustain = round(float(r.get("duration") or 0) - float(on_.get("start") or 0), 3)
            if need.get("busy_s"):
                out_s = round(min(float(r.get("duration") or 0), float(on_["start"]) + float(need["busy_s"]) + 0.1), 3)
        elif on_ and on_.get("body_s") is not None:
            # where the chosen hit ends: its fall to −40 dB, plus up to 50 ms, never into the next hit (build review 2,
            # Grok: levels cut 2 s from the in-point, so a twelve-hit file played the next steps too)
            out_s = round(on_["attack"] + on_["body_s"] + min(0.05, (on_.get("gap_out_ms") or 0) / 2000), 3)
            sustain = on_["body_s"]
        if use_shape and on_ and s == 0 and (need.get("force") in SHARP_MS or need.get("object_material")
                                             or need.get("surface_material")):
            why = list(why) + ["its attack fits neither the force nor the material: listen to the next row too"]
        if slide and on_:
            why = list(why) + [f"the file runs {sustain:.2f} s from this hit"
                               + (f" for a {float(need['busy_s']):.2f} s slide" if need.get("busy_s") else
                                  " (slide length unknown: no out_s, trim it to the picture)")]
        rows.append({**r, "identity": ident, "shape": s, "onset": i, "type": mt["type"],
                     "has_action": bool(act and (act in w or any(x in w for x in syn))) if act else True,
                     "attack_s": on_.get("attack") if on_ else None, "start_s": on_.get("start") if on_ else None,
                     "out_s": out_s, "sustain_s": sustain,
                     "why": (why if i is not None else ["no attack with a measured shape"])
                     + ([f"only its first {mt['window_s']:.0f} s measured; the conform reads the whole file and may "
                         f"call it a bed: pull the hit into its own file if it does"] if mt.get("window_s") else [])})
    # when the read names an action, a file that does not carry it (or a synonym) is never above one that does
    # (build review 2, Sonnet: "Bullet Impact Glass" reached the five for a clink on materials alone)
    # last tie-break: for a hit the shorter file (less to trim); for a slide the hit that stays up longest, never the
    # shorter file (build review 2, Grok: with busy_s unknown the length point never fired and the squeak won)
    slide = need.get("kind") == "slide"
    rows.sort(key=lambda r: (not r["has_action"], -r["identity"], -r["shape"],
                             -(r.get("sustain_s") or 0) if slide else r.get("duration", 0)))
    unmeasured.sort(key=lambda r: -r["identity"])
    return {"need": need, "known": known, "missing": missing, "words": words, "candidates": rows[:n],
            "unmeasured": unmeasured[:n]}


def candidate_sheet(job: str, shot: str, cat: str | None = None, paid_ads_only: bool = True, n: int = 5) -> str:
    """The dispatcher's sheet for the spotter: per event in the shot's read, five candidates with their reasons, the
    read fields that were known and missing (a words-only fallback is visible). Writes 09-qa/sfx/<shot>.candidates.md."""
    R = load_read(job, shot)
    if not R:
        raise SystemExit(f"no read for {shot} — `sfx_conform.py read {job} --shot {shot}` writes the form the spotter "
                         f"fills; the sheet needs its closed lists")
    lines = [f"# Candidate sounds · {shot}", "",
             "Events the spotter adds or drops after reading the frames have no row here: Grep the catalogues for those.",
             "",
             "From the measured catalogues, for the spotter to choose from (the person still auditions). Identity "
             "words decide first; the attack's shape breaks ties (assumed rules, until the blind listening test). "
             + ("Only libraries cleared for paid ads." if paid_ads_only else "⚠ ALL licences, not only paid-ads yes."),
             ""]
    det = {}
    ep = os.path.join(job, "09-qa", "sfx", f"{shot}.events.json")
    if os.path.isfile(ep):                       # the detector's own kind and busy time, matched by time
        for de in (json.load(open(ep, encoding="utf-8")).get("events") or []):
            det[round(float(de.get("t", -9)), 2)] = de
    for k, ev in enumerate(R.get("events") or [], 1):
        if ev.get("keep") == "no":
            continue
        t_ = float(ev.get("t", -9))
        de = min(det.values(), key=lambda d: abs(float(d.get("t", -9)) - t_), default=None) if det else None
        de = de if de and abs(float(de.get("t", -9)) - t_) <= 0.1 else {}
        kind = "slide" if (de.get("kind") == "slide" or ev.get("what") in SLIDE_WHATS) else "hit"
        res = search_need(need_of({x: ev.get(x) for x in VOCAB if ev.get(x)}, {"kind": kind, "busy_s": de.get("busy_s")}),
                          cat, None, paid_ads_only, n)
        lines.append(f"## Event {k} · t={ev.get('t')} s · " + ", ".join(f"{a}={b}" for a, b in res["known"].items()))
        if res["missing"]:
            lines.append(f"Missing from the read: {', '.join(res['missing'])} — "
                         + ("the ranking leans on fewer words." if res["words"] else "no words to search: fill the read."))
        lines.append(f"Searched: {' '.join(res['words']) or '—'}")
        if not res["candidates"]:
            lines.append("No candidate. Widen the words, or check the licence filter.")
        for c in res["candidates"]:
            at = (f" · {c['type']} · use the hit at {c['attack_s']:.3f} s (set in_s to {max(0.0, c['start_s']):.3f}"
                  + (f", out_s to {c['out_s']:.3f}" if c.get("out_s") is not None else "") + ")"
                  if c.get("attack_s") is not None and c.get("start_s") is not None else f" · {c.get('type', '?')}")
            lines.append(f"- `{c['library']}` · {c['rel']} · {c.get('duration', 0):.2f} s · words {c['identity']}{at}"
                         + " — " + "; ".join(c["why"]))
        if res.get("unmeasured"):
            lines.append("Not measured yet, or only its first minute (could be beds; never among the five): "
                         + "; ".join(f"`{u['library']}` {u['rel']}" + (" (partly measured)" if u.get("partly") else "")
                                     for u in res["unmeasured"][:3]))
        lines.append("")
    out = os.path.join(job, "09-qa", "sfx", f"{shot}.candidates.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return out


def blind_sheet(queries: str, out: str, cat: str | None = None, n: int = 5, paid_ads_only: bool = False,
                seed: int = 7) -> dict:
    """(v2.68.0) The blind listening test: for each event in QUERIES (a JSON list of {"id", "say", "need"}), the top
    `n` from today's word search and from the measured ranking, merged, shuffled and unlabelled. The person marks each
    `[x]` keep or leaves it `[ ]`; `blind-score` counts keeps per method. The method of each row is in <out>.key.json,
    which the person never opens. Nothing is claimed as better until this says so (plan rounds 1–3)."""
    import random
    rng = random.Random(seed)
    Q = json.load(open(queries, encoding="utf-8"))
    key, lines = {}, ["# Which of these sounds would you keep?", "",
                      "For each moment, listen to every file and tick the ones you would keep for it: `- [x]`. "
                      "Leave the rest. The order is shuffled and nothing says how each was found.", ""]
    for q in Q:
        need = q["need"]
        # both arms: the same identity score on the same pool, beds dropped in both; only the measured arm adds shape
        # (build review 2, Grok: the word arm used search_library's own scoring, so words differed after all)
        base = [f"{c['library']}:{c['rel']}" for c in search_need(need, cat, None, paid_ads_only, n,
                                                                   use_shape=False)["candidates"]]
        new = [f"{c['library']}:{c['rel']}" for c in search_need(need, cat, None, paid_ads_only, n)["candidates"]]
        items = list(dict.fromkeys(base + new))
        rng.shuffle(items)
        lines += [f"## {q['id']} · {q.get('say', '')}", ""]
        for k, it in enumerate(items, 1):
            lab = f"{q['id']}-{k}"
            key[lab] = {"file": it, "word_search": it in base, "measured": it in new}
            lines.append(f"- [ ] {lab} · `{it.split(':', 1)[1]}`")
        lines.append("")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    json.dump(key, open(out + ".key.json", "w", encoding="utf-8"), indent=1)
    return {"sheet": out, "events": len(Q), "rows": len(key)}


def blind_score(sheet: str) -> dict:
    """Keeps per method from a ticked blind sheet: of the files each method offered, how many the person kept."""
    key = json.load(open(sheet + ".key.json", encoding="utf-8"))
    kept = set(re.findall(r"^- \[[xX]\] (\S+)", open(sheet, encoding="utf-8").read(), re.M))
    out = {}
    for m in ("word_search", "measured"):
        offered = [lab for lab, v in key.items() if v[m]]
        out[m] = {"offered": len(offered), "kept": sum(1 for lab in offered if lab in kept)}
        out[m]["share"] = round(out[m]["kept"] / out[m]["offered"], 3) if out[m]["offered"] else None
    # the files only one arm offered are where the methods differ: their keeps are the result that matters
    for m, other in (("word_search", "measured"), ("measured", "word_search")):
        only = [lab for lab, v in key.items() if v[m] and not v[other]]
        out[m]["only_this_arm"] = {"offered": len(only), "kept": sum(1 for lab in only if lab in kept)}
    out["note"] = ("one listener, one sitting: a pilot, not a measurement for other studios; tuned weights from it stay "
                   "on this machine")
    return out


def pick_ir(space: str, size: str, rt60: float, cat: str | None = None) -> dict | None:
    """A measured room for the read's space and size: a space IR (never a plate, spring or effect) whose name
    places it when it can, in the size class, with the decay nearest the space's RT60. Outdoors only an IR
    that names the place; otherwise None and the conform keeps its synthetic tail."""
    cands = []
    for r in load_catalogues(cat, kind="ir"):
        if not r.get("path") or not os.path.isfile(r["path"]):
            continue
        w = set(r.get("words") or [])
        if w & set(IR_NOT_A_SPACE) or (r.get("size_class") == "surround"):
            continue
        place = len(w & set(IR_SPACE_WORDS.get(space, [])))
        if space in IR_OUTDOOR and not place:
            continue
        dec = r.get("decay_s") or r.get("duration") or 0
        size_ok = 1 if (r.get("size_class") == size or not r.get("size_class")) else 0
        cands.append((-place, -size_ok, abs(dec - rt60), r["rel"], r))
    if not cands:
        return None
    cands.sort(key=lambda c: c[:4])
    return cands[0][-1]


def pull(path_or_rel: str, job: str, cat: str | None = None, library: str | None = None) -> dict:
    """Copy a library file into the job (06-sfx/library/, 48 kHz WAV) with its licence beside it, so the
    audio manifest's row is written from the catalogue, not from memory."""
    hit = None
    for r in load_catalogues(cat, [library] if library else None):
        if r.get("path") and (os.path.abspath(r["path"]) == os.path.abspath(path_or_rel) or r["rel"] == path_or_rel):
            hit = r; break
    if not hit:
        raise SystemExit(f"error: {path_or_rel} is in no catalogue — `sfx_conform.py library build` its library first")
    if hit.get("paid_ads") == "no":
        print(f"  ⚠ {hit['library']}: not for paid ads ({hit.get('licence')})", file=sys.stderr)
    d = os.path.join(job, "06-sfx", "library"); os.makedirs(d, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{hit['library']}_{os.path.splitext(os.path.basename(hit['rel']))[0]}")[:90]
    out = os.path.join(d, stem + ".wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", hit["path"], "-vn", "-ar", str(SR), "-c:a", "pcm_s24le", out], check=True)
    side = {"source": f"library:{hit['library']}", "library_file": hit["rel"], "licence": hit.get("licence") or "",
            "paid_ads": hit.get("paid_ads") or "unverified", "condition": hit.get("condition") or "",
            "author": hit.get("author") or hit.get("source_tag") or "", "pulled": dt.datetime.now().isoformat(timespec="minutes"),
            "sha256": sha256_file(out)}
    json.dump(side, open(out + ".licence.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return {"file": os.path.relpath(out, job), **side}


def _tc(t: float, fps: float) -> str:
    f = int(round(t * fps)); fr = int(round(fps))
    return f"{f // (3600 * fr):02d}:{f // (60 * fr) % 60:02d}:{f // fr % 60:02d}:{f % fr:02d}"


# =================================================================================================
# selftest
# =================================================================================================
def _synth_drops(path: str, times: list, flicker: float | None = None, fps: int = 24, seconds: float = 3.5,
                 sizes: list | None = None) -> None:
    """Splashes: a small bright ring appears and spreads for a few frames at each time; an optional
    one-frame global flicker that must not count."""
    np = _np()
    W, H = 180, 320
    rng = np.random.default_rng(11)
    bg = (rng.random((H, W)) * 30 + 70).astype(np.float32)
    spots = [(30 + 50 * i % 130, 60 + 90 * i % 220) for i in range(len(times))]
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                          "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "mpeg4", "-q:v", "2", path],
                         stdin=subprocess.PIPE)
    yy, xx = np.mgrid[0:H, 0:W]
    for i in range(int(seconds * fps)):
        t = i / fps
        img = bg.copy()
        for (x, y), t0, sz in zip(spots, times, sizes or [1.0] * len(times)):
            age = t - t0
            if -1e-6 <= age < 0.25:
                r = (3 + age * 60) * sz
                ring = np.abs(np.hypot(xx - x, yy - y) - r) < 2.5 * sz
                img[ring] = 245
        if flicker is not None and abs(t - flicker) < 0.5 / fps:
            img = np.clip(img + 60, 0, 255)
        p.stdin.write(img.astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()


def _synth_sfx(path: str, times: list, levels: list, seconds: float = 3.0) -> None:
    """Drop-like plinks: a click and a short damped tone at each time."""
    np = _np()
    rng = np.random.default_rng(3)
    x = np.zeros(int(seconds * SR), np.float32)
    for t0, lv in zip(times, levels):
        n = int(0.25 * SR)
        tt = np.arange(n) / SR
        tone = np.sin(2 * np.pi * (900 + 400 * rng.random()) * tt) * np.exp(-tt / 0.04)
        click = rng.standard_normal(n) * np.exp(-tt / 0.004)
        a = int(t0 * SR)
        x[a:a + n] += ((tone * 0.7 + click * 0.5) * lv).astype(np.float32)[: max(0, len(x) - a)]
    write_wav(path, x)


def _synth_bed(path: str, seconds: float = 3.0) -> None:
    np = _np()
    rng = np.random.default_rng(4)
    x = (rng.standard_normal(int(seconds * SR)) * 0.05).astype(np.float32)
    for k in range(int(seconds * 25)):                        # rain: 25 small ticks a second
        a = int(rng.random() * (len(x) - 500))
        x[a:a + 200] += (rng.standard_normal(200) * 0.12 * np.exp(-np.arange(200) / 40)).astype(np.float32)
    write_wav(path, x)


# ⚡ THE MEASURED LEVEL STEP (a supplement ad job, 2026-10-28). Momentary loudness of each sound as cut, against the voice's at
# that moment; the category's level under the voice, a −6 dBFS peak ceiling. Targets [measured on one supplement ad job];
# a client's audio.<client>.json `sfx_targets` overrides them.
SFX_TARGET = {"ui": -11.5, "foley": -14.0, "texture": -16.0, "bite": -10.0, "whoosh": -8.0, "rise": -12.0,
              "marker": -12.0, "hit": -10.0}
SFX_CEILING_DB = -6.0
SFX_PREROLL_S = 0.01            # the cut starts this far before the transient's attack [practitioner]
SFX_MAX_GAIN_DB = 30.0          # Resolve's clip AudioVolume tops out at +30 dB (measured, 21.1.1)
CATEGORY_WORDS = {"ui": ("ui", "click", "tap", "switch", "toggle", "pop", "notification", "button", "beep", "tick"),
                  "bite": ("bite", "crunch", "chew", "eat", "apple"),
                  "whoosh": ("whoosh", "swish", "swoosh", "swipe", "whip"),
                  "rise": ("rise", "riser", "swell", "build"),
                  "marker": ("marker", "pen", "pencil", "draw", "scribble", "circle", "stroke"),
                  "hit": ("hit", "impact", "boom", "thud", "stamp", "slam"),
                  "texture": ("texture", "rustle", "ambience", "room", "air", "hum"),
                  "foley": ("rub", "plate", "book", "drawer", "cup", "keys", "pour", "sugar", "cloth", "glass", "bottle",
                            "door", "step", "drop")}


def sfx_category(e: dict) -> str:
    if e.get("category") in SFX_TARGET:
        return e["category"]
    words = " ".join(str(e.get(k) or "") for k in ("sfx", "why", "file")).lower()
    for cat, ws in CATEGORY_WORDS.items():
        if any(re.search(rf"\b{w}", words) for w in ws):
            return cat
    return "foley"


# EVENTS, NOT MOTION (v2.46; editing-and-audio.md §7f, last paragraph). A graphic's EVENT is a sound event — it
# arrives, lands, snaps, makes contact. Its continuous motion (a drift, a slow turn, a scroll, grain) stays silent.
# One placed sound running longer than this on a graphic reads as narrating the motion, unless the row says bed: yes.
GRAPHIC_SPAN_S = 1.5            # [assumed]
GRAPHIC_ON = ("graphic", "title", "text", "ui", "shape", "card", "chart", "label", "caption")


def continuous_on_graphic(events: list, fps: float = 24.0) -> list:
    """WARN lines for placed sounds that span over GRAPHIC_SPAN_S on a graphic (the row's `on`, its title anchor,
    or a ui/marker category), unless marked `bed: yes`. The span is `dur_s`, `duration_s`, `out_s − in_s` or
    `frames`/fps — a row that states none is not judged."""
    W = []
    for i, e in enumerate(events or []):
        if str(e.get("bed") or "").lower() in ("yes", "true", "1"):
            continue
        anchor = e.get("anchor") if isinstance(e.get("anchor"), dict) else {}
        on = str(e.get("on") or anchor.get("type") or "").lower()
        graphic = on in GRAPHIC_ON or re.fullmatch(r"T\d+", str(anchor.get("id") or e.get("title") or "")) \
            or e.get("category") in ("ui", "marker")
        if not graphic:
            continue
        span = None
        for k in ("dur_s", "duration_s"):
            if e.get(k) is not None:
                span = float(e[k]); break
        if span is None and e.get("out_s") is not None and e.get("in_s") is not None:   # out_s alone is a file
            span = float(e["out_s"]) - float(e["in_s"])        # position, not a span (build review 3, Sonnet)
        if span is None and e.get("frames") is not None:
            span = float(e["frames"]) / fps
        if span is not None and span > GRAPHIC_SPAN_S + 1e-9:
            W.append(f"{e.get('sfx') or e.get('file') or f'event {i}'} (frame {e.get('frame')}): {span:.1f} s of sound on a "
                     f"graphic — sound marks the graphic's EVENT (arrival, land, snap, contact), its continuous motion "
                     f"stays silent (editing-and-audio.md §7f). Cut it to the event, or mark the row bed: yes")
    return W


def levels(job: str, placement: str, voice: str, fps: float = 24.0, write: bool = False) -> dict:
    np = _np()
    import mix_qa as MQ
    P = json.load(open(placement if os.path.isabs(placement) else os.path.join(job, placement), encoding="utf-8"))
    events = P.get("events") or []
    ca = MQ.client_audio(job)
    targets = {**SFX_TARGET, **(ca.get("sfx_targets") or {})}
    V = MQ.ebur(voice if os.path.isabs(voice) else os.path.join(job, voice))
    act = MQ.active_windows(V)
    speech = MQ.energy_mean([V["M"][i] for i in act]) if act else -23.0
    vt = np.asarray(V["t"], dtype=np.float64)
    vm = np.asarray(V["M"], dtype=np.float64)
    rows = []
    for k, e in enumerate(events):
        f = e.get("file") or ""
        fp = f if os.path.isabs(f) else os.path.join(job, f)
        cat = sfx_category(e)
        row = {"i": k, "sfx": e.get("sfx"), "frame": e.get("frame"), "category": cat, "target_under_voice_db": targets[cat]}
        if not os.path.isfile(fp):
            row["problem"] = f"the file is not on this machine: {f}"
            rows.append(row); continue
        x = pcm(fp)
        in_s = float(e.get("in_s") or 0.0)
        out_s = float(e["out_s"]) if e.get("out_s") is not None else None
        # with the sheet's out_s the in-point is exact (5 ms slack), so a tap 80 ms earlier is never taken (build
        # review 3, Grok); without it the old 50 ms look-back stays
        on = [o for o in detect_onsets(x) if o["attack"] >= in_s - (0.005 if out_s is not None else 0.05)
              and (out_s is None or o["attack"] < out_s)]
        new_in = in_s
        if not on and out_s is not None:          # build review 3, Sonnet: never measure a tail without saying so
            row["problem"] = f"no attack between in_s {in_s:.3f} and out_s {out_s:.3f}: re-read the sheet's times"
            rows.append(row); continue
        if on:
            new_in = max(0.0, round(on[0]["attack"] - SFX_PREROLL_S, 4))
            row["transient_after_in_frames"] = round((on[0]["attack"] - in_s) * fps, 1)
        stop = min(new_in + 2.0, out_s) if out_s is not None and out_s > new_in else new_in + 2.0
        seg = x[int(new_in * SR): int(stop * SR)]
        if not len(seg) or float(np.abs(seg).max()) < 1e-6:
            row["problem"] = "silent where it is cut"
            rows.append(row); continue
        pad = np.zeros(int(1.0 * SR), dtype=np.float32)
        S_ = MQ.ebur(np.concatenate([seg[: int(0.6 * SR)], pad])[:, None].repeat(2, axis=1))
        sfx_m = max([m for m in S_["M"] if m > -100] or [-70.0])
        peak_db = 20 * float(np.log10(float(np.abs(seg).max()) + 1e-12))
        t = float(e.get("frame") or 0) / fps
        w = (vt >= t - 0.2) & (vt <= t + 0.4)
        here = float(vm[w].max()) if w.any() else -120.0
        ref = here if here >= max(MQ.ACTIVE_FLOOR, V["I"] - MQ.ACTIVE_BELOW) else speech
        want = ref + targets[cat]
        gain = want - sfx_m
        cap = SFX_CEILING_DB - peak_db
        capped = gain > cap
        gain = min(gain, cap, SFX_MAX_GAIN_DB)
        row.update(in_s=new_in, sfx_momentary=round(sfx_m, 1), voice_ref=round(ref, 1),
                   voice_speaking=here >= max(MQ.ACTIVE_FLOOR, V["I"] - MQ.ACTIVE_BELOW), volume_db=round(gain, 1),
                   peak_after_db=round(peak_db + gain, 1), capped_by_peak=capped,
                   was_volume_db=e.get("volume_db"), was_in_s=e.get("in_s", 0.0))
        if out_s is not None:
            row["out_s"] = out_s                      # the clip's end in the file: trim it there when placing
        if e.get("volume_db") is not None:
            row["was_under_voice_db"] = round(sfx_m + float(e["volume_db"]) - ref, 1)
        rows.append(row)
    dur = float(P.get("duration_s") or 0) or (max([float(e.get("frame") or 0) for e in events] or [0]) / fps + 2.0)
    density = round(len(events) / (dur / 60.0), 1) if dur else None
    rep = {"placement": rel(job, placement) if os.path.isabs(placement) else placement, "voice": voice,
           "voice_speech_lufs": round(speech, 1), "targets": targets, "ceiling_dbfs": SFX_CEILING_DB, "events": rows,
           "density_per_min": density, "client_density_per_min": ca.get("sfx_density_per_min"),
           "warnings": continuous_on_graphic(events, fps),
           "client_audio": ca.get("_source"), "made": dt.datetime.now().isoformat(timespec="minutes")}
    os.makedirs(os.path.join(job, "09-qa", "sfx"), exist_ok=True)
    json.dump(rep, open(os.path.join(job, "09-qa", "sfx", "LEVELS.json"), "w", encoding="utf-8"), indent=1)
    if write:
        for r in rows:
            if "volume_db" in r:
                e = events[r["i"]]
                e.setdefault("volume_db_prev", e.get("volume_db"))
                e["volume_db"], e["in_s"] = r["volume_db"], r["in_s"]
                e["level"] = f"{r['category']} {r['target_under_voice_db']:+g} dB to the voice, measured {rep['made']}"
        pp = placement if os.path.isabs(placement) else os.path.join(job, placement)
        json.dump(P, open(pp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return rep


def rel(job: str, p: str) -> str:
    return os.path.relpath(p, job) if os.path.abspath(p).startswith(os.path.abspath(job) + os.sep) else p


def selftest() -> int:
    np = _np()
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and cond
    with tempfile.TemporaryDirectory() as td:
        os.environ["CINE_SFX_CATALOGUES"] = os.path.join(td, "catalogues")   # never the machine's real libraries
        job = os.path.join(td, "job")
        for d in ("01-script/prompts", "03-clips", "06-sfx", "09-qa/motion", "09-qa/sfx"):
            os.makedirs(os.path.join(job, d))
        drops = [1.0, 1.625, 2.5]
        clip = os.path.join(job, "03-clips", "S2_v1.mp4")
        _synth_drops(clip, drops, flicker=2.0)
        VE = visual_events(clip, static=True, native_vote=False)
        ts = [e["t"] for e in VE["events"]]
        check("three splashes are three events, each on its frame, and a one-frame flicker is none",
              len(ts) == 3 and all(abs(a - b) <= 1 / 24 + 1e-6 for a, b in zip(ts, drops)), json.dumps(VE["events"]))
        # the library: five plinks of different strength; rain is a bed
        lib = os.path.join(job, "06-sfx", "drops_lib.wav")
        _synth_sfx(lib, [0.2, 0.7, 1.15, 1.8, 2.4], [0.3, 0.9, 0.5, 0.7, 0.4])
        ix = index_file(lib)
        check("the downloaded file's five drops are indexed as five events", ix["kind"] == "event" and len(ix["events"]) == 5,
              json.dumps(ix["events"]))
        rain = os.path.join(job, "06-sfx", "rain.wav")
        _synth_bed(rain)
        check("rain has no separable events: it is a bed, not cut", index_file(rain)["kind"] == "bed")
        try:
            conform(job, "S2", [rain], clip=clip)
            refused = False
        except SystemExit:
            refused = True
        check("conform refuses to cut a bed", refused)
        rep = conform(job, "S2", [lib], clip=clip, tags={"surface": "hard", "space": "kitchen", "distance": "close"})
        check("conform keeps three of the five drops, one per splash", len(rep["events"]) == 3, json.dumps(rep["events"]))
        check("each attack lands 0 to +1 frame after its splash, checked on the render alone",
              rep["verify"]["ok"], json.dumps(rep["verify"]))
        check("no drop plays the same piece twice in a row",
              all((a["source"], a["source_event"]) != (b["source"], b["source_event"])
                  for a, b in zip(rep["events"], rep["events"][1:])))
        rep_w = conform(job, "S2", [lib], clip=clip, tags={"surface": "wet"})
        check("a wet surface lands one frame late, never early", all(p["lag_frames"] == 1 for p in rep_w["events"])
              and rep_w["verify"]["ok"], json.dumps(rep_w["verify"]))
        rep2 = conform(job, "S2", [lib], clip=clip, tags={"count": "2"})
        check("the director's count wins: count=2 keeps two", len(rep2["events"]) == 2)
        check("with no impulse responses catalogued the room is the synthetic tail, and it says so",
              rep["room"].get("synthetic_rt60_s") and any("synthetic" in f_ for f_ in rep["findings"]), json.dumps(rep["room"]))
        # the libraries: an SFX library with a per-file licence CSV, and an impulse-response library
        L1 = os.path.join(td, "Movies", "FX Lib", "Foley")
        os.makedirs(L1)
        _synth_sfx(os.path.join(L1, "Glass Clink Small.wav"), [0.2], [0.6], seconds=0.6)
        _synth_sfx(os.path.join(L1, "Wood Knock.wav"), [0.2], [0.6], seconds=0.6)
        _synth_bed(os.path.join(L1, "Rain On Window.wav"))
        csvp = os.path.join(td, "lib.csv")
        open(csvp, "w").write("filename,license,author\nWood Knock.wav,Pixabay Content License,someone\n")
        _synth_sfx(os.path.join(L1, "DSGNMisc_PING-Piano Ping C 01_Vendor_Felt.wav"), [0.2], [0.6], seconds=0.6)
        _synth_sfx(os.path.join(L1, "DSGNRythm_LOOP-Clock Tick Loopable_Vendor_Pendulum_120 bpm.wav"), [0.2], [0.6], seconds=0.6)
        open(os.path.join(L1, "Vendor Felt Metadata Import.csv"), "w", encoding="utf-8-sig").write(
            "Filename,Keywords,Description,Category,SubCategory,CatID,Key\n"
            "DSGNMisc_PING-Piano Ping C 01_Vendor_Felt.wav,\"Piano, Chime, Sting\",\"Piano, Chime, Sting\",DESIGNED,MISC,DSGNMisc,C\n"
            "DSGNRythm_LOOP-Clock Tick Loopable_Vendor_Pendulum_120 bpm.wav,\"Clock, Tick, Tension\",\"Clock, Tick, Tension\",DESIGNED,RHYTHMIC,DSGNRythm,\n")
        r1 = build_library(os.path.dirname(L1), "fxlib", licence="royalty-free, own projects only", paid_ads="unverified",
                           basis="test", licence_csv=csvp, mac_root=os.path.dirname(L1))
        r1b = build_library(os.path.dirname(L1), "fxlib")
        check("a library builds into a catalogue, and a second run indexes nothing new",
              r1["files"] == 5 and r1["indexed_now"] == 5 and r1b["indexed_now"] == 0, json.dumps([r1["files"], r1b]))
        ch = search_library("chime")
        check("the vendor's metadata sheet adds its keywords, UCS CatID and key to the row (found by 'chime')",
              ch and ch[0]["name"].startswith("DSGNMisc_PING") and ch[0].get("key") == "C"
              and (ch[0].get("ucs") or {}).get("catid") == "DSGNMisc", json.dumps(ch[:1]))
        check("--key keeps only sounds in that root (C, not D); --bpm only loops at that tempo",
              search_library("piano", key="C") and not search_library("piano", key="D")
              and search_library("tension", bpm=120) and not search_library("tension", bpm=90))
        hits = search_library("glass clink")
        check("search finds by name; the library's licence travels with the row",
              hits and hits[0]["name"] == "Glass Clink Small" and hits[0]["paid_ads"] == "unverified", json.dumps(hits[:2]))
        wk = search_library("knock")
        check("a per-file licence from the CSV wins over the library's (Pixabay → paid ads yes)",
              wk and wk[0]["paid_ads"] == "yes" and "Pixabay" in wk[0]["licence"], json.dumps(wk[:1]))
        check("--paid-ads-only leaves the unverified rows out",
              [h["name"] for h in search_library("glass knock", paid_ads_only=True)] == ["Wood Knock"])
        # (v2.68.0) the shapes of attacks, a measured library, the search by need, the candidate sheet
        tt_ = np.arange(int(1.4 * SR)) / SR
        xs = np.zeros(tt_.size, np.float32)
        n6 = int(0.6 * SR)
        xs[int(0.2 * SR):int(0.2 * SR) + n6] += (np.sin(2 * np.pi * 3000 * tt_[:n6]) * np.exp(-tt_[:n6] * 6)).astype(np.float32)
        n3 = int(0.3 * SR)
        xs[int(0.9 * SR):int(0.9 * SR) + n3] += (np.sin(2 * np.pi * 400 * tt_[:n3]) * np.linspace(0, 1, n3) * 0.6).astype(np.float32)
        on_ = detect_onsets(xs)
        sh_ = attack_shapes(xs, on_)
        check("(2.68) a sharp ringing hit reads sharp and ringing; a slow swell reads soft and damped",
              len(sh_) == 2 and sh_[0]["sharp_ms"] < 10 and sh_[0]["ring_s"] > 0.3 and sh_[1]["sharp_ms"] > 25
              and sh_[1]["ring_s"] < 0.1, json.dumps(sh_))
        check("(2.68) the attack detect_onsets places is untouched (placement, re-check and levels read it)",
              "sharp_ms" not in on_[0] and [o["attack"] for o in on_] == [o["attack"] for o in detect_onsets(xs)])
        xb = np.zeros(int(0.8 * SR), np.float32)
        nb = int(0.2 * SR)
        hit_ = (np.random.default_rng(2).standard_normal(nb) * np.exp(-tt_[:nb] / 0.01)).astype(np.float32)
        xb[int(0.1 * SR):int(0.1 * SR) + nb] += hit_ * 0.6
        xb[int(0.14 * SR):int(0.14 * SR) + nb] += hit_ * 0.9                 # a louder bounce 40 ms later
        ob_ = detect_onsets(xb)
        sb_ = attack_shapes(xb, ob_)
        check("(2.68) sharpness is the FIRST peak of the rise: a louder bounce 40 ms later does not make a hit soft",
              ob_ and sb_[0]["sharp_ms"] < 15, json.dumps([ob_, sb_]))
        L3 = os.path.join(td, "Movies", "Measured")
        os.makedirs(L3, exist_ok=True)
        def _tone(path, f0, tau, lv=0.7, seconds=1.2, swell=False):
            x_ = np.zeros(int(seconds * SR), np.float32)
            n_ = int(min(seconds - 0.2, 0.9) * SR)
            env_ = np.linspace(0, 1, n_) if swell else np.exp(-tt_[:n_] / tau)
            x_[int(0.1 * SR):int(0.1 * SR) + n_] += (np.sin(2 * np.pi * f0 * tt_[:n_]) * env_ * lv).astype(np.float32)
            write_wav(path, x_)
        _tone(os.path.join(L3, "Metal Hit Ring.wav"), 3500, 0.3)              # rings, bright
        _tone(os.path.join(L3, "Metal Hit Damp.wav"), 300, 0.01)               # damped, dark (sorts first by name)
        _tone(os.path.join(L3, "Cloth Thud Soft.wav"), 250, 0.02, swell=True)  # a slow rise
        write_wav(os.path.join(L3, "Rain Bed.wav"), (np.random.default_rng(5).standard_normal(int(3 * SR)) * 0.1).astype(np.float32))
        write_wav(os.path.join(L3, "Cloth Rustle Bed.wav"), (np.random.default_rng(6).standard_normal(int(3 * SR)) * 0.1).astype(np.float32))
        build_library(L3, "measured", licence="test", paid_ads="yes", basis="test")
        m0 = measure_library("measured", budget_s=0, progress=None)
        m1 = measure_library("measured", progress=None)
        m2 = measure_library("measured", progress=None)
        check("(2.68) measuring is resumable: a zero budget measures nothing and says how many remain; then all; then none",
              m0["measured_now"] == 0 and m0["left"] == 5 and m1["measured_now"] == 5 and m1["left"] == 0
              and m2["measured_now"] == 0, json.dumps([m0, m1, m2]))
        rows_ = {r["name"]: r for r in load_catalogues(names=["measured"])}
        check("(2.68) a rain file is a bed (no attack shapes); a single hit is one-hit, with its shape",
              rows_["Rain Bed"]["measure"]["type"] == "bed" and "onsets" not in rows_["Rain Bed"]["measure"]
              and rows_["Metal Hit Ring"]["measure"]["type"] == "one-hit"
              and rows_["Metal Hit Ring"]["measure"]["onsets"][0]["ring_s"] > 0.15, json.dumps(rows_["Rain Bed"]["measure"]))
        r_ring = search_need({"what": "other", "object_material": "metal", "surface_material": "metal", "force": "hard",
                              "kind": "hit"}, names=["measured"])
        check("(2.68) words tie (two metal hits): the measured shape breaks it — the bright ringing one first for metal",
              [c["name"] for c in r_ring["candidates"][:2]] == ["Metal Hit Ring", "Metal Hit Damp"]
              and r_ring["candidates"][0]["shape"] > r_ring["candidates"][1]["shape"], json.dumps(r_ring["candidates"][:2]))
        r_th = search_need({"what": "thud", "object_material": "fabric", "force": "soft", "kind": "hit"}, names=["measured"])
        check("(2.68) identity words decide first (thud → the cloth thud), beds never offered, missing fields named",
              r_th["candidates"] and r_th["candidates"][0]["name"] == "Cloth Thud Soft"
              and all(c["name"] != "Rain Bed" for c in r_th["candidates"]) and "surface_material" in r_th["missing"],
              json.dumps([c["name"] for c in r_th["candidates"]]))
        r_bed = search_need({"what": "rustle", "object_material": "fabric", "kind": "hit"}, names=["measured"])
        check("(2.68) a bed is never offered for an event, even when its words match",
              all("Bed" not in c["name"] for c in r_bed["candidates"]), json.dumps([c["name"] for c in r_bed["candidates"]]))
        picks_ = [choose_attack([{"sharp_ms": 60, "ring_s": 0.02, "centroid": 400, "i": 0},
                                 {"sharp_ms": 4, "ring_s": 0.5, "centroid": 3000, "i": 1}],
                                {"force": "hard", "object_material": "metal", "kind": "hit"},
                                np.random.default_rng(seed_)) for seed_ in range(20)]
        check("(2.68) the conform's choice: a hard metal event gets the sharp ringing attack, every time (20 draws)",
              all(p_["i"] == 1 and f_["score"] == 2 for p_, f_ in picks_), json.dumps([p_["i"] for p_, _ in picks_]))
        # (v2.68.0, build review 1, Grok) the action beats synonym-heavy names; wood damps a soft set-down; "hard" spans
        # several analysis frames; a tap inside a ringing tail has no readable rise; the sheet names the hit's time
        _tone(os.path.join(L3, "Impact Hit Metal.wav"), 3000, 0.2)
        _tone(os.path.join(L3, "Soft Thud Fabric.wav"), 200, 0.02)
        build_library(L3, "measured")
        measure_library("measured", progress=None)
        r_th2 = search_need({"what": "thud", "object_material": "fabric", "kind": "hit"}, names=["measured"])
        check("(2.68) the read's own word outranks synonym-heavy names: `thud` finds the soft fabric thud before "
              "an `Impact Hit` file", r_th2["candidates"] and r_th2["candidates"][0]["name"] in ("Soft Thud Fabric", "Cloth Thud Soft")
              and [c["name"] for c in r_th2["candidates"]].index("Impact Hit Metal") > 0 if any(
                  c["name"] == "Impact Hit Metal" for c in r_th2["candidates"]) else r_th2["candidates"][0]["name"] != "Impact Hit Metal",
              json.dumps([(c["name"], c["identity"]) for c in r_th2["candidates"]]))
        damp_, ring_ = ({"sharp_ms": 40, "ring_s": 0.02, "centroid": 300}, {"sharp_ms": 40, "ring_s": 0.5, "centroid": 3000})
        need_mug = {"object_material": "ceramic", "surface_material": "wood", "force": "soft", "kind": "hit"}
        check("(2.68) a soft ceramic set-down on wood prefers the damped attack (the surface it meets decides)",
              shape_fit(damp_, need_mug)[0] > shape_fit(ring_, need_mug)[0],
              json.dumps([shape_fit(damp_, need_mug), shape_fit(ring_, need_mug)]))
        need_spoon = {"object_material": "metal", "surface_material": "ceramic", "force": "hard", "kind": "hit"}
        check("(2.68) a hard metal strike on a cup prefers the ringing attack (the object decides)",
              shape_fit({**ring_, "sharp_ms": 5}, need_spoon)[0] > shape_fit({**damp_, "sharp_ms": 5}, need_spoon)[0])
        check("(2.68) a 12 ms rise still counts as hard (the band spans several 5.3 ms frames)",
              shape_fit({"sharp_ms": 12.0}, {"force": "hard", "kind": "hit"})[0] == 1)
        xt = np.zeros(int(0.8 * SR), np.float32)
        ntt = int(0.5 * SR)
        tap_ = (np.sin(2 * np.pi * 2500 * tt_[:ntt]) * np.exp(-tt_[:ntt] / 0.15)).astype(np.float32)
        xt[int(0.1 * SR):int(0.1 * SR) + ntt] += tap_ * 0.5
        xt[int(0.18 * SR):int(0.18 * SR) + ntt] += tap_ * 0.6               # 80 ms later, inside the first one's ring
        ot_ = detect_onsets(xt)
        st_ = attack_shapes(xt, ot_)
        check("(2.68) a second tap inside the first one's ring has no readable rise (no force point either way)",
              len(ot_) >= 2 and st_[1]["sharp_ms"] is None, json.dumps([ot_, st_]))
        xs2 = np.zeros(int(1.0 * SR), np.float32)
        n2 = int(0.3 * SR)
        k2 = (np.random.default_rng(4).standard_normal(n2) * np.exp(-tt_[:n2] / 0.02)).astype(np.float32)
        for t2 in (0.1, 0.35, 0.6):                                     # three knocks, each decayed before the next
            xs2[int(t2 * SR):int(t2 * SR) + n2] += k2 * 0.6
        s2_ = attack_shapes(xs2, detect_onsets(xs2))
        check("(2.68) in a sequence, a hit after a real dip has a readable rise (from the dip, not the old tail's end)",
              len(s2_) == 3 and all(x["sharp_ms"] is not None and x["sharp_ms"] < 20 for x in s2_), json.dumps(s2_))
        _tone(os.path.join(L3, "Bullet Impact Glass.wav"), 2500, 0.3)
        _tone(os.path.join(L3, "Glass Clink Bright.wav"), 3500, 0.3)
        build_library(L3, "measured")
        measure_library("measured", progress=None)
        r_ck = search_need({"what": "clink", "object_material": "glass", "surface_material": "glass", "kind": "hit"},
                           names=["measured"])
        _tone(os.path.join(L3, "Glass Metal Debris.wav"), 1500, 0.05)        # both materials, no action word
        _tone(os.path.join(L3, "Ting Small.wav"), 4000, 0.3)                # only a synonym of the action
        build_library(L3, "measured")
        measure_library("measured", progress=None)
        r_tg = search_need({"what": "clink", "object_material": "glass", "surface_material": "metal", "kind": "hit"},
                           names=["measured"])
        nm_tg = [c["name"] for c in r_tg["candidates"]]
        check("(2.68) a file carrying the action (or its synonym) sits above one that matches only the materials",
              "Ting Small" in nm_tg and "Glass Metal Debris" in nm_tg and nm_tg.index("Ting Small") < nm_tg.index("Glass Metal Debris"),
              json.dumps([(c["name"], c["identity"], c["has_action"]) for c in r_tg["candidates"]]))
        nm_ck = [c["name"] for c in r_ck["candidates"]]
        check("(2.68) a file without the action word never sits above one with it; a material counts once",
              nm_ck and nm_ck[0] == "Glass Clink Bright" and ("Bullet Impact Glass" not in nm_ck
                                                             or nm_ck.index("Bullet Impact Glass") > nm_ck.index("Glass Clink Bright")),
              json.dumps([(c["name"], c["identity"], c["has_action"]) for c in r_ck["candidates"]]))
        r_un2 = search_need({"what": "clink", "object_material": "glass", "kind": "hit"}, paid_ads_only=False)
        check("(2.68) an unmeasured row is never among the five (it could be a bed); it is listed apart",
              not any(c["name"] == "Glass Clink Small" for c in r_un2["candidates"])
              and any(u["name"] == "Glass Clink Small" for u in r_un2["unmeasured"]), json.dumps(r_un2["unmeasured"][:2]))
        w_arm = search_need({"what": "clink", "object_material": "glass", "kind": "hit"}, paid_ads_only=False,
                            use_shape=False)
        check("(2.68) the blind test's word arm: the same identity score and pool as the measured arm, no shape points",
              w_arm["words"] == r_un2["words"] and all(c["shape"] == 0 for c in w_arm["candidates"])
              and {c["rel"] for c in w_arm["candidates"]} <= {c["rel"] for c in search_need(
                  {"what": "clink", "object_material": "glass", "kind": "hit"}, paid_ads_only=False, n=99)["candidates"]},
              json.dumps([(c["name"], c["shape"]) for c in w_arm["candidates"]]))

        check("(2.68) client searches default to paid-ads yes: the unverified library stays out",
              not any(c["library"] == "fxlib" for c in search_need({"what": "clink", "object_material": "glass"})["candidates"]
                      + search_need({"what": "clink", "object_material": "glass"})["unmeasured"]))
        check("(2.68) synonyms: at most three per word, none of them another action or a material from the read's lists",
              all(len(v) <= 3 and not set(v) & set(VOCAB["what"]) and not set(v) & set(MATERIALS) for v in SYNONYMS.values())
              and set(SYNONYMS) <= set(VOCAB["what"]))
        check("(2.68) a file extension is not a word: `wav` finds nothing", search_library("wav") == [])
        sc_hard = shape_fit({"sharp_ms": 4, "ring_s": 0.5, "centroid": 3000, "clean_in": True, "clean_out": True},
                            {"force": "hard", "object_material": "glass", "kind": "hit"})
        sc_soft = shape_fit({"sharp_ms": 60, "ring_s": 0.02, "centroid": 400, "clean_in": True, "clean_out": False},
                            {"force": "hard", "object_material": "glass", "kind": "hit"})
        check("(2.68) a hard glass hit prefers a sharp ringing attack; a trim is named in the reasons",
              sc_hard[0] == 2 and sc_soft[0] == 0 and any("needs a trim" in w for w in sc_soft[1]), json.dumps([sc_hard, sc_soft]))
        qf = os.path.join(td, "q.json")
        json.dump([{"id": "E1", "say": "a metal tool hits a metal bench, hard",
                    "need": {"object_material": "metal", "surface_material": "metal", "force": "hard", "kind": "hit"}}],
                  open(qf, "w"))
        bs = blind_sheet(qf, os.path.join(td, "blind.md"))
        sheet_ = open(os.path.join(td, "blind.md")).read()
        key_ = json.load(open(os.path.join(td, "blind.md.key.json")))
        check("(2.68) the blind sheet merges both methods' picks and never names a method (the key sits beside it)",
              bs["rows"] >= 2 and not re.search(r"word|measured|method", sheet_.split("## E1", 1)[1], re.I)
              and any(v["word_search"] for v in key_.values()) and any(v["measured"] for v in key_.values()),
              sheet_[:300] + json.dumps(key_))
        open(os.path.join(td, "blind.md"), "w").write(sheet_.replace("- [ ] E1-1", "- [x] E1-1"))
        sc_ = blind_score(os.path.join(td, "blind.md"))
        check("(2.68) blind-score counts the keeps per method", sum(sc_[m]["kept"] for m in ("word_search", "measured")) >= 1
              and "pilot" in sc_["note"], json.dumps(sc_))
        Qs = json.load(open(os.path.join(os.path.dirname(HERE), "assets", "audio-match-queries.json"), encoding="utf-8"))
        check("(2.68) the shipped blind-test moments use only the read's closed lists (25 moments)",
              len(Qs) == 25 and all(q["need"].get(k) in VOCAB[v] for q in Qs for k, v in
                                    (("what", "what"), ("object_material", "object_material"),
                                     ("surface_material", "surface_material"), ("force", "force"))))
        check("(2.68) ring is never scored on a slide (a loud cloth scrape is not metal)",
              shape_fit({"sharp_ms": 40, "ring_s": 0.6, "centroid": 3000, "body_s": 0.2}, {"object_material": "metal",
                        "kind": "slide", "busy_s": 1.0})[0] == 0)
        # (v2.68.0, build review 1) the action outranks materials and synonyms; level inside the file; long files;
        # clean edges by the gap; the candidate sheet itself; the CLI end to end
        _tone(os.path.join(L3, "Finger Tap Table.wav"), 900, 0.02)
        _tone(os.path.join(L3, "Door Wood Creak Long.wav"), 200, 0.2)
        build_library(L3, "measured")
        measure_library("measured", progress=None)
        r_tap = search_need({"what": "tap", "object_material": "skin", "surface_material": "wood", "kind": "hit"},
                            names=["measured"])
        check("(2.68) the action word outranks a material: `tap` on wood finds the finger tap before the wooden door",
              r_tap["candidates"] and r_tap["candidates"][0]["name"] == "Finger Tap Table",
              json.dumps([(c["name"], c["identity"]) for c in r_tap["candidates"]]))
        lv_ = [choose_attack([{"sharp_ms": 4, "rel_db": -14.0, "i": 0}, {"sharp_ms": 4, "rel_db": -0.5, "i": 1}],
                             {"force": "hard", "kind": "hit"}, np.random.default_rng(s_))[0]["i"] for s_ in range(20)]
        check("(2.68) between equal shapes, a hard event takes the attack near its file's loudest (20 draws)",
              set(lv_) == {1}, json.dumps(lv_))
        lg_ = np.zeros(int(70 * SR), np.float32)
        for k_ in range(35):                                   # a hit every 2 s for 70 s: a long footstep run
            i_ = int((0.5 + 2 * k_) * SR)
            lg_[i_:i_ + 2400] = (0.8 * np.exp(-np.linspace(0, 8, 2400)) * np.sin(np.linspace(0, 900, 2400))).astype(np.float32)
        write_wav(os.path.join(td, "Long Steps.wav"), lg_)
        ml_ = measure_file(os.path.join(td, "Long Steps.wav"), "sfx", duration=70.0)
        check("(2.68) a file longer than a minute is measured on its first minute, never called a bed unopened",
              ml_.get("type") == "sequence" and ml_.get("window_s") == MEASURE_MAX_S and 25 <= ml_["attacks"] <= 31,
              json.dumps({k: v for k, v in ml_.items() if k != "onsets"}))
        check("(2.68) clean edges are judged by the gap to the neighbouring hits, in ms",
              "gap_in_ms" in sh_[0] and sh_[0]["clean_in"] and sh_[0]["clean_out"], json.dumps(sh_[0]))
        sj_ = os.path.join(td, "sheetjob")
        os.makedirs(os.path.join(sj_, "09-qa", "sfx"))
        json.dump({"shot_read": {}, "events": [
            {"id": "E1", "t": 0.5, "what": "other", "object_material": "metal", "surface_material": "metal", "force": "hard"},
            {"id": "E2", "t": 1.5, "what": "scrape", "object_material": "fabric"}]},
            open(os.path.join(sj_, "09-qa", "sfx", "S1.read.json"), "w"))
        json.dump({"events": [{"t": 1.5, "kind": "slide", "busy_s": 0.6}]},
                  open(os.path.join(sj_, "09-qa", "sfx", "S1.events.json"), "w"))
        out_ = candidate_sheet(sj_, "S1")
        sh_txt = open(out_).read()
        check("(2.68) the candidate sheet: written in the job, one block per event, missing read fields named, "
              "the slide checked on length (never on ring), the added-events note",
              os.path.isfile(out_) and "## Event 1" in sh_txt and "## Event 2" in sh_txt
              and "Missing from the read: what" in sh_txt and "Grep the catalogues" in sh_txt
              and "rings (" not in sh_txt.split("## Event 2")[1] and "set in_s to" in sh_txt and "out_s to" in sh_txt,
              sh_txt[:900])
        # (v2.68.0, build review 2, Grok) a slide whose length is unknown is ranked by how long it stays up, never by
        # the shorter file; the blind arms never offer a bed; keeps on files only one arm offered are reported
        _tone(os.path.join(L3, "Cloth Scrape Brief.wav"), 400, 0.01, seconds=0.8)
        _tone(os.path.join(L3, "Cloth Scrape Held.wav"), 400, 0.35, seconds=2.0)
        build_library(L3, "measured")
        measure_library("measured", progress=None)
        r_sl = search_need({"what": "scrape", "object_material": "fabric", "kind": "slide"}, names=["measured"])
        nm_sl = [c["name"] for c in r_sl["candidates"] if c["name"].startswith("Cloth Scrape")]
        check("(2.68) a slide of unknown length: the file that stays up longest first, and the row says why",
              nm_sl[:1] == ["Cloth Scrape Held"] and any("slide length unknown" in w for w in r_sl["candidates"][0]["why"]),
              json.dumps([(c["name"], c.get("sustain_s"), c.get("duration")) for c in r_sl["candidates"]]))
        # (build review 3, Grok) a slide is judged on how long the FILE runs, and cut to the picture's busy time
        gr_ = np.zeros(int(2.0 * SR), np.float32)
        for k_ in range(8):                                    # a 2 s scrape made of short grains, 4 a second
            i_ = int((0.05 + 0.25 * k_) * SR)
            gr_[i_:i_ + 1440] = (0.6 * np.exp(-np.linspace(0, 9, 1440)) * np.sin(np.linspace(0, 2000, 1440))).astype(np.float32)
        write_wav(os.path.join(L3, "Metal Scrape Grains.wav"), gr_)
        _tone(os.path.join(L3, "Metal Scrape Short.wav"), 2500, 0.08, seconds=0.4)
        wb_ = np.random.default_rng(9).standard_normal(int(70 * SR)).astype(np.float32) * 0.05
        write_wav(os.path.join(L3, "Rumble Room Long.wav"), wb_)
        build_library(L3, "measured")
        measure_library("measured", progress=None)
        sl_u = search_need({"what": "scrape", "object_material": "metal", "kind": "slide"}, names=["measured"])
        nm_u = [c["name"] for c in sl_u["candidates"] if c["name"].startswith("Metal Scrape")]
        check("(2.68) a slide of unknown length ranks the file that runs longest (a 2 s scrape of short grains beats a "
              "0.4 s one) and prints no out_s",
              nm_u[:1] == ["Metal Scrape Grains"] and sl_u["candidates"][0]["out_s"] is None
              and any("no out_s" in w for w in sl_u["candidates"][0]["why"]),
              json.dumps([(c["name"], c.get("sustain_s"), c.get("out_s")) for c in sl_u["candidates"]]))
        sl_b = search_need({"what": "scrape", "object_material": "metal", "kind": "slide", "busy_s": 1.0}, names=["measured"])
        g_ = next(c for c in sl_b["candidates"] if c["name"] == "Metal Scrape Grains")
        check("(2.68) a slide's out_s is the picture's busy time from the hit (not one grain), and the long file wins",
              sl_b["candidates"][0]["name"] == "Metal Scrape Grains" and abs(g_["out_s"] - (g_["start_s"] + 1.1)) < 0.002
              and g_["shape"] >= 1 and any("long enough" in w for w in g_["why"]),
              json.dumps([(c["name"], c.get("start_s"), c.get("out_s"), c["shape"]) for c in sl_b["candidates"]]))
        w_sl = search_need({"what": "scrape", "object_material": "metal", "kind": "slide"}, names=["measured"],
                           use_shape=False)
        check("(2.68) the blind word arm uses no shape at all: the first kept attack, never a shape-picked one",
              all(c["onset"] == 0 and c["shape"] == 0 for c in w_sl["candidates"]),
              json.dumps([(c["name"], c["onset"]) for c in w_sl["candidates"]]))
        rb_ = search_need({"what": "rumble", "kind": "hit"}, names=["measured"])
        check("(2.68) a long file whose first minute has no separate attack is listed as partly measured, never "
              "dropped", any(u["name"] == "Rumble Room Long" and u.get("partly") for u in rb_["unmeasured"])
              and not any(c["name"] == "Rumble Room Long" for c in rb_["candidates"]),
              json.dumps([(r_["name"], r_.get("measure"), r_.get("paid_ads")) for r_ in load_catalogues(names=["measured"])
                          if "Rumble" in r_["name"]]))
        z_ = search_need({"what": "thud", "object_material": "metal", "force": "soft", "kind": "hit"}, names=["measured"])
        zero_ = [c for c in z_["candidates"] if c["shape"] == 0]
        check("(2.68) a file that won on its words but fits neither force nor material says so",
              zero_ and all(any("fits neither" in w for w in c["why"]) for c in zero_),
              json.dumps([(c["name"], c["shape"], c["why"]) for c in z_["candidates"]]))
        qb_ = os.path.join(td, "qb.json")
        json.dump([{"id": "B1", "say": "cloth rustles", "need": {"what": "rustle", "object_material": "fabric", "kind": "hit"}},
                   {"id": "B2", "say": "metal on metal", "need": {"object_material": "metal", "surface_material": "metal",
                                                                  "force": "hard", "kind": "hit"}},
                   {"id": "B3", "say": "a glass clinks", "need": {"what": "clink", "object_material": "glass", "kind": "hit"}}],
                  open(qb_, "w"))
        blind_sheet(qb_, os.path.join(td, "blindb.md"))
        kb_ = json.load(open(os.path.join(td, "blindb.md.key.json")))
        sb_ = blind_score(os.path.join(td, "blindb.md"))
        arm_ = set()
        for q_ in json.load(open(qb_)):
            arm_ |= {f"{c['library']}:{c['rel']}" for c in search_need(q_["need"], paid_ads_only=False, n=99,
                                                                        use_shape=False)["candidates"]}
        check("(2.68) neither blind arm offers a bed; the word arm is the measured pool without shape; the score "
              "reports keeps on files only one arm offered",
              not any("Bed" in v["file"] for v in kb_.values())
              and all(v["file"] in arm_ for v in kb_.values() if v["word_search"])
              and all("only_this_arm" in sb_[m] for m in ("word_search", "measured")), json.dumps([kb_, sb_])[:600])
        envc = {**os.environ, "CINE_SFX_CATALOGUES": os.environ["CINE_SFX_CATALOGUES"]}
        me_ = os.path.abspath(__file__)
        cli = [subprocess.run([sys.executable, me_, "library", *args], capture_output=True, text=True, env=envc)
               for args in (["list"], ["measure", "--name", "measured"], ["sheet", sj_, "S1"],
                            ["search", "metal", "--kind", "music"], ["blind", qf, os.path.join(td, "b2.md")],
                            ["blind-score", os.path.join(td, "b2.md")])]
        check("(2.68) every new library verb runs end to end from the command line",
              all(c.returncode == 0 for c in cli), json.dumps([(c.returncode, c.stderr[-200:]) for c in cli]))
        L2 = os.path.join(td, "Movies", "IRs")
        for sub_, nm, dec in (("03 Small Spaces", "0.9s_Tiled Bathroom", 0.9), ("03 Small Spaces", "1.1s_Vocal Plate", 1.1),
                              ("02 Medium Spaces", "0.6s_Kitchen", 0.6), ("01 Large Spaces", "2.4s_Concert Hall", 2.4)):
            os.makedirs(os.path.join(L2, sub_), exist_ok=True)
            n_ = int(dec * SR)
            tt = np.arange(n_) / SR
            irx = np.random.default_rng(1).standard_normal(n_) * np.exp(-6.91 * tt / dec)
            irx[0] = 4.0                                             # the direct sound, which load_ir fades out
            write_wav(os.path.join(L2, sub_, nm + ".wav"), (irx * 0.2).astype(np.float32))
        build_library(L2, "irs", kind="ir", licence="royalty-free with the app", paid_ads="yes", basis="test")
        b_ = pick_ir("bathroom", "small", 1.1 * 0.7)
        check("a small bathroom gets the tiled bathroom — named for the place, never the plate",
              b_ and b_["name"] == "0.9s_Tiled Bathroom", json.dumps(b_ and b_["name"]))
        check("a street gets no room tail unless an IR names the place", pick_ir("street", "medium", 0.3) is None)
        rep_r = conform(job, "S2", [lib], clip=clip, tags={"space": "bathroom"})
        check("(2.68) the conform records why it chose each attack (its shape against the event), not a random third",
              "attack_fit" in json.dumps(rep_r), json.dumps(rep_r)[:300])
        check("conform puts the hits in the measured room and records which one, with its licence",
              rep_r["room"].get("rel", "").endswith("Tiled Bathroom.wav") and rep_r["room"].get("paid_ads") == "yes"
              and rep_r["verify"]["ok"], json.dumps([rep_r["room"], rep_r["verify"], [e_["wet"] for e_ in rep_r["events"]]]))
        ir_ = load_ir(os.path.join(L2, "03 Small Spaces", "0.9s_Tiled Bathroom.wav"))
        check("a measured IR loses its direct spike (the wet path is room only) and has unit energy",
              abs(float((ir_.astype(np.float64) ** 2).sum()) - 1.0) < 1e-3 and abs(float(ir_[0])) < 1e-6)
        pr_ = pull(wk[0]["path"], job)
        side = json.load(open(os.path.join(job, pr_["file"]) + ".licence.json"))
        import mix_qa as MX
        MX.write_manifest(job)
        rows_ = {r_["file"]: r_ for r_ in MX.read_manifest(job)}
        check("pull copies the file into the job with its licence beside it, and the manifest row is written from it",
              side["paid_ads"] == "yes" and rows_.get(pr_["file"], {}).get("paid ads") == "yes"
              and "Pixabay" in rows_.get(pr_["file"], {}).get("licence", ""), json.dumps(rows_.get(pr_["file"])))
        os.rename(os.path.join(td, "Movies"), os.path.join(td, "Moved"))
        check("a library that moved is reported unreachable, not silently empty",
              resolve_root([os.path.dirname(L1)]) is None and not [h for h in search_library("glass") if h.get("path")])
        # tamper: a placement moved two frames early must fail the re-check
        bad = [dict(p, event_t=p["event_t"] + 3 / 24) for p in rep["events"]]
        check("a render whose attacks come early fails the re-check",
              not verify_render(os.path.join(job, rep["render"]), bad, 24.0)["ok"])
        # the read: the agent looks at the sheet and fills the form; the conform holds it to the vocabulary
        rf = read_form(job, "S2", clip)
        check("read writes the sheet and a form with a row per event",
              os.path.isfile(rf["sheet"]) and len(json.load(open(rf["form"]))["events"]) == 3)
        F_ = json.load(open(rf["form"]))
        F_["shot_read"].update({"space": "bathroom", "space_size": "small", "count_seen": "3", "extra_events": [3.0]})
        F_["events"][0].update({"what": "splash", "object_material": "water", "surface_material": "metal", "force": "hard",
                                "wet": "yes"})
        F_["events"][1].update({"keep": "no"})
        F_["events"][2].update({"what": "drop", "object_material": "water", "occluded": "glass", "visible": "partly"})
        F_["read_by"] = "selftest"
        json.dump(F_, open(rf["form"], "w"))
        rr = conform(job, "S2", [lib], clip=clip)
        ev = {round(p["event_t"], 2): p for p in rr["events"]}
        check("the read drops a silent burst, adds a missed event, and sets force, wet and glass per event",
              len(rr["events"]) == 3 and 1.62 not in ev and 3.0 in ev and ev[1.0]["lag_frames"] == 1
              and ev[2.5]["lowpass"] <= 3000 and rr["verify"]["ok"], json.dumps(rr["events"]) + json.dumps(rr["verify"]))
        check("…and the room comes from the read (a small bathroom)", rr["tags"].get("space") == "bathroom")
        F_["events"][0]["object_material"] = "unobtainium"
        json.dump(F_, open(rf["form"], "w"))
        try:
            conform(job, "S2", [lib], clip=clip); refused = False
        except SystemExit:
            refused = True
        check("a read off its vocabulary is refused", refused)
        os.remove(rf["form"])
        # the parameters
        rng = np.random.default_rng(0)
        P = lambda e, t: params_for({"x": 0.5, "y": 0.5, "area": 2, "bucket": "medium", **e}, t, np.random.default_rng(0), 2)
        near, far = P({}, {"distance": "close"}), P({}, {"distance": "far"})
        check("far is quieter, duller and roomier than close", far["gain_db"] < near["gain_db"] - 5
              and far["lowpass"] < near["lowpass"] and far["wet"] > near["wet"], json.dumps([near, far]))
        check("a harder, faster, longer-falling event is louder",
              P({"bucket": "hard", "speed": 1.5, "fall": 0.4}, {})["gain_db"] > P({"bucket": "soft", "speed": 0.2}, {})["gain_db"] + 6)
        check("bigger is lower in pitch", P({"area": 6}, {})["pitch_st"] < P({"area": 1}, {})["pitch_st"])
        check("an off-screen event is lower and duller", P({"x": 1.3}, {})["gain_db"] < P({}, {})["gain_db"] - 3
              and P({"x": 1.3}, {})["lowpass"] <= 5000)
        check("an event that is not the hero's sits 6 dB back",
              abs(P({"object": "cup"}, {"hero": "jar"})["gain_db"] - P({"object": "jar"}, {"hero": "jar"})["gain_db"] + 6) < 0.01)
        check("pan is off by default, follows the object only on request, capped at ±0.4",
              P({"x": 0.95}, {})["pan"] == 0 and 0 < P({"x": 0.95}, {"pan": "follow"})["pan"] <= PAN_MAX
              and P({"x": 1.0}, {"pan": "follow"})["pan"] == PAN_MAX)
        rp = conform(job, "S2", [lib], clip=clip, tags={"pan": "follow"})
        import mix_qa as MX
        fd = MX.fold_down(pcm(os.path.join(job, rp["render"]), SR, 2))
        check("a panned render still folds to mono inside the gate's 3 dB", fd["loss_db"] is not None and fd["loss_db"] >= -3.0,
              json.dumps(fd))
        # the clip prompt carries the tags
        open(os.path.join(job, "01-script", "prompts", "S2.clip.prompt.md"), "w").write(
            "---\nshot: S2\nkind: clip\nsfx: count=1, surface=wet, space=bathroom\n---\n[MOTION]\nx\n")
        check("an `sfx:` line in the clip prompt sets the tags",
              clip_tags(os.path.join(job, "01-script", "prompts", "S2.clip.prompt.md")) ==
              {"count": "1", "surface": "wet", "space": "bathroom"})
        # density: twenty drops in one second are thinned to six
        dense = os.path.join(job, "03-clips", "S5_v1.mp4")
        _synth_drops(dense, [0.5 + 0.05 * i for i in range(14)], seconds=2.0)
        VD = visual_events(dense, static=True, native_vote=False)
        check("more than six events a second are thinned, and the drop is explained",
              len([e for e in VD["events"] if 0.4 <= e["t"] <= 1.3]) <= 6 * 2
              and any("density" in (d.get("why_dropped") or "") for d in VD["dropped"]), json.dumps(len(VD["events"])))
        # C: the sound across the cuts
        for s_, jn in (("S1", "motion-match"), ("S2", "whip"), ("S3", "flip"), ("S4", "whip"), ("S5", "whip"), ("S6", "camera-carry")):
            open(os.path.join(job, "01-script", "prompts", f"{s_}.clip.prompt.md"), "w").write(
                f"---\nshot: {s_}\nkind: clip\nexit: right\njoin: {jn}\n---\n[MOTION]\nx\n")
        json.dump({"cut": "07-edit/cut.mp4", "joins": [{"n": i + 1, "t": 1.0 + i, "from": f"S{i + 1}", "to": f"S{i + 2}",
                                                       "screen_dir": "kept"} for i in range(6)]},
                  open(os.path.join(job, "09-qa", "motion", "cut.joins.json"), "w"))
        wh = os.path.join(job, "06-sfx", "whoosh.wav")
        _synth_sfx(wh, [0.3], [0.8], seconds=0.8)
        JP = joins_plan(job, whoosh=wh, pan="follow")
        snd = [r["sound"] for r in JP["joins"]]
        check("hand-offs follow the plan: overlap on a match, a break on a flip, one ambience across a carry",
              snd[0] == "overlap" and snd[2] == "break" and snd[5] == "carry", json.dumps(snd))
        check("a whoosh only on a whip, and only two per ad", snd.count("whip") == 2 and snd[4] == "plain", json.dumps(snd))
        check("the whoosh stem and the EDL are written", os.path.isfile(os.path.join(job, JP["stem"]))
              and os.path.isfile(os.path.join(job, "09-qa", "sfx", "cut.joins-sound.edl")))
        open(os.path.join(job, "01-script", "prompts", "S3.clip.prompt.md"), "w").write(
            "---\nshot: S3\nkind: clip\nexit: right\njoin: flip\nramp: kind=slow, speed=40, trigger=1.1, reveal=the spray, "
            "sfx=whoosh-down, cut_in=3.2, cut_out=4.4\n---\n[MOTION]\nx\n")
        JR = joins_plan(job)
        rr = [r for r in JR["ramps"] if r["shot"] == "S3"]
        check("a ramp mutes the clip under it, its cue named, with markers at its place in the cut",
              rr and rr[0]["cue"] == "whoosh-down" and "mute S3" in rr[0]["note"]
              and "RAMP IN S3" in open(os.path.join(job, "09-qa", "sfx", "cut.joins-sound.edl")).read(), json.dumps(rr))
    print("-" * 60)
    # the measured level step (a supplement ad job)
    with tempfile.TemporaryDirectory() as td2:
        job2 = os.path.join(td2, "job")
        for d in ("00-brief", "06-music", "09-qa/sfx"):
            os.makedirs(os.path.join(job2, d))
        rng = np.random.default_rng(3)
        n = int(8 * SR)
        v = np.zeros(n, dtype=np.float32)
        for a0, a1 in ((0.5, 3.0), (4.0, 7.5)):                          # the voice speaks in two stretches
            m = int(a1 * SR) - int(a0 * SR)
            v[int(a0 * SR): int(a1 * SR)] = (0.08 * rng.standard_normal(m) * np.abs(np.sin(np.linspace(0, 40, m)))).astype(np.float32)
        write_wav(os.path.join(job2, "voice.wav"), v)
        click = np.zeros(int(1.0 * SR), dtype=np.float32)
        lead = int(0.55 * SR)                                              # its transient sits 0.55 s into the file
        click[lead: lead + 2400] = (0.9 * rng.standard_normal(2400) * np.exp(-np.linspace(0, 8, 2400))).astype(np.float32)
        write_wav(os.path.join(job2, "06-music", "switch.wav"), click)
        json.dump({"events": [{"sfx": "light switch", "frame": 48, "file": "06-music/switch.wav", "volume_db": 2.6}]},
                  open(os.path.join(job2, "06-music", "SFX-PLACEMENT.json"), "w"))
        r = levels(job2, "06-music/SFX-PLACEMENT.json", "voice.wav", 24.0, write=True)
        e0 = r["events"][0]
        check("levels: the in-point moves to the file's transient (it sat ~13 frames past the cut)",
              abs(e0["in_s"] - 0.54) < 0.03 and e0["transient_after_in_frames"] > 10, e0)
        check("levels: a switch is UI — set under the voice by measurement, and its peak capped at −6 dBFS",
              e0["category"] == "ui" and e0["peak_after_db"] <= -5.9 and e0["volume_db"] < 2.6, e0)
        # (v2.68.0, build review 2, Grok) the chosen hit's end: levels measures only up to out_s and passes it on
        two_ = np.zeros(int(1.5 * SR), dtype=np.float32)
        for at_, lv2 in ((0.1, 0.08), (0.6, 0.9)):                         # a quiet tap, then a loud one
            two_[int(at_ * SR): int(at_ * SR) + 2400] = (lv2 * np.exp(-np.linspace(0, 8, 2400))
                                                           * np.sin(np.linspace(0, 700, 2400))).astype(np.float32)
        write_wav(os.path.join(job2, "06-music", "two.wav"), two_)
        json.dump({"events": [{"sfx": "tap", "frame": 48, "file": "06-music/two.wav", "in_s": 0.0, "out_s": 0.4},
                              {"sfx": "tap", "frame": 48, "file": "06-music/two.wav", "in_s": 0.0},
                              {"sfx": "tap", "frame": 48, "file": "06-music/two.wav", "in_s": 0.3, "out_s": 0.5}]},
                  open(os.path.join(job2, "06-music", "TWO.json"), "w"))
        rt_ = levels(job2, "06-music/TWO.json", "voice.wav", 24.0)["events"]
        pk_ = [e_["peak_after_db"] - e_["volume_db"] for e_ in rt_[:2]]
        check("levels (2.68): with out_s it measures only the chosen hit (the quiet tap), and passes out_s on",
              rt_[0].get("out_s") == 0.4 and "out_s" not in rt_[1] and pk_[0] < pk_[1] - 12
              # no attack between in_s and out_s: it says so, never jumps to the next hit past the end
              and "no attack between" in rt_[2].get("problem", "") and "transient_after_in_frames" not in rt_[2],
              json.dumps(rt_))
        # (build review 3, Grok) with the sheet's out_s the in-point is exact: two slow-rising taps 80 ms apart, the
        # first one's attack (its peak) lands inside the old 50 ms look-back before the second one's start
        n_, r_ = int(0.06 * SR), int(0.04 * SR)
        env_ = np.concatenate([np.linspace(0, 1, r_), np.exp(-np.linspace(0, 8, n_ - r_))])
        pr_ = np.zeros(int(1.0 * SR), dtype=np.float32)
        for at_, lv2 in ((0.30, 0.9), (0.38, 0.6)):
            i_ = int(at_ * SR)
            pr_[i_:i_ + n_] += (lv2 * env_ * np.sin(np.linspace(0, n_ / SR * 2 * np.pi * 900, n_))).astype(np.float32)
        write_wav(os.path.join(job2, "06-music", "pair.wav"), pr_)
        ons_ = detect_onsets(pr_)
        check("levels (2.68) test design: the first tap's attack sits inside 50 ms before the second one's start",
              len(ons_) == 2 and ons_[0]["attack"] >= ons_[1]["start"] - 0.05, json.dumps(ons_, default=str)[:300])
        if len(ons_) == 2:
            s2_, a2_ = ons_[1]["start"], ons_[1]["attack"]
            json.dump({"events": [{"sfx": "tap", "frame": 48, "file": "06-music/pair.wav", "in_s": round(s2_, 4),
                                   "out_s": round(a2_ + 0.03, 4)}]}, open(os.path.join(job2, "06-music", "PAIR.json"), "w"))
            rq_ = levels(job2, "06-music/PAIR.json", "voice.wav", 24.0, write=True)["events"][0]
            pq_ = json.load(open(os.path.join(job2, "06-music", "PAIR.json")))["events"][0]
            check("levels (2.68): with out_s it takes the hit at the printed in_s, never the earlier tap, and the "
                  "placement keeps out_s after --write",
                  rq_.get("transient_after_in_frames", -9) >= 0 and pq_.get("out_s") == round(a2_ + 0.03, 4),
                  json.dumps([rq_, pq_]))
        P2 = json.load(open(os.path.join(job2, "06-music", "SFX-PLACEMENT.json")))
        check("levels --write: the placement takes the measured gain and in-point, keeping the old gain",
              P2["events"][0]["volume_db_prev"] == 2.6 and P2["events"][0]["volume_db"] == e0["volume_db"], P2)
        open(os.path.join(job2, "00-brief", "CHECKPOINT.md"), "w").write(f"Client:     {td2}/acme.md\n")
        json.dump({"music_under_voice_db": 38, "sfx_density_per_min": 13}, open(os.path.join(td2, "audio.acme.json"), "w"))
        G = continuous_on_graphic([{"sfx": "whoosh", "frame": 10, "on": "title", "dur_s": 2.4},
                                   {"sfx": "pad", "frame": 10, "on": "graphic", "dur_s": 4.0, "bed": "yes"},
                                   {"sfx": "pop", "frame": 30, "on": "title", "dur_s": 0.4},
                                   {"sfx": "riser", "frame": 40, "category": "ui", "in_s": 0.2, "out_s": 2.2},
                                   {"sfx": "door", "frame": 50, "dur_s": 3.0},
                                   {"sfx": "tick", "frame": 60, "category": "ui", "out_s": 12.3}], 24.0)
        check("events, not motion: a 2.4 s sound on a title and a 2 s UI sound warn; a marked bed, a short pop, a "
              "non-graphic door and an out_s with no in_s (a file position, not a span) do not", len(G) == 2 and "whoosh" in G[0] and "riser" in G[1], json.dumps(G))
        import mix_qa as MQ
        ca = MQ.client_audio(job2)
        check("the client's audio settings are read beside the profile the CHECKPOINT names",
              ca["music_under_voice_db"] == 38 and ca["sfx_density_per_min"] == 13 and ca["_source"].endswith("audio.acme.json"), ca)
    print("selftest OK — splashes counted and timed (a flicker is not one), a downloaded file indexed into its "
          "drops and rain kept as a bed, the conform (one drop per splash, 0 to +1 frame, never early, no repeats, "
          "a wet lag, the director's count, the re-check catches an early render), events not motion on graphics, the parameters (distance, "
          "strength, speed, fall, size, off screen, hero, pan within the mono gate), the prompt's sfx: tags, "
          "the read (sheet, form, a silent burst dropped, a missed one added, force/wet/glass, the room, its "
          "vocabulary), density thinning, the sound across the cuts (overlap, break, carry, whip cap, the stem and the EDL, a ramp's mute and cue), "
          "and the libraries (catalogue, resume, search, per-file licence, paid-ads filter, the measured room, pull and the manifest)"
          if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("index"); i.add_argument("files", nargs="+"); i.add_argument("--kind", choices=["event", "bed"])
    i.add_argument("--material", choices=MATERIALS, help="what the file is made of, so the read can pick it")
    rd_ = sub.add_parser("read"); rd_.add_argument("job"); rd_.add_argument("--shot", required=True)
    rd_.add_argument("--clip"); rd_.add_argument("--track", action="append", default=[])
    e = sub.add_parser("events"); e.add_argument("clip"); e.add_argument("--job"); e.add_argument("--shot")
    e.add_argument("--track", action="append", default=[]); e.add_argument("--count", type=int)
    c = sub.add_parser("conform"); c.add_argument("job"); c.add_argument("--shot", required=True)
    c.add_argument("--sfx", required=True, help="one or more downloaded SFX files, comma-separated")
    c.add_argument("--clip"); c.add_argument("--track", action="append", default=[]); c.add_argument("--out")
    c.add_argument("--mux", action="store_true", help="also write the clip with the conformed SFX as its audio")
    c.add_argument("--room", default="auto", help="auto (a measured space from the IR catalogues, else synthetic) · "
                                                   "synthetic · a path to an impulse response")
    c.add_argument("--catalogues")
    for t in TAGS:
        c.add_argument(f"--{t}")
    lv = sub.add_parser("levels"); lv.add_argument("job"); lv.add_argument("--placement", required=True)
    lv.add_argument("--voice", required=True, help="the voice (dialogue stem or VO) in timeline time")
    lv.add_argument("--fps", type=float, default=24.0); lv.add_argument("--write", action="store_true")
    v = sub.add_parser("verify"); v.add_argument("job"); v.add_argument("--shot", required=True)
    j = sub.add_parser("joins"); j.add_argument("job"); j.add_argument("--whoosh"); j.add_argument("--pan", default="off")
    lb = sub.add_parser("library", help="the SFX and impulse-response libraries on this machine")
    lb.add_argument("action", choices=["build", "measure", "search", "sheet", "blind", "blind-score", "pull", "ir", "list"])
    lb.add_argument("arg", nargs="*", help="build: ROOT · measure: (--name) · search: WORDS · sheet: JOB SHOT · "
                                           "pull: FILE JOB · ir: SPACE SIZE")
    lb.add_argument("--name"); lb.add_argument("--kind", choices=["sfx", "ir", "music"], default="sfx")
    lb.add_argument("--all-licences", action="store_true",
                    help="sheet / music search: include libraries not cleared for paid ads (internal work only)")
    lb.add_argument("--catalogues", help="default $CINE_SFX_CATALOGUES, else $CINE_HOME/sfx-catalogues")
    lb.add_argument("--licence"); lb.add_argument("--paid-ads", choices=["yes", "no", "unverified"])
    lb.add_argument("--basis"); lb.add_argument("--condition"); lb.add_argument("--licence-csv")
    lb.add_argument("--mac-root", help="the library's real path on the Mac, recorded once")
    lb.add_argument("--lib", action="append", help="search only these libraries")
    lb.add_argument("--max-dur", type=float); lb.add_argument("--paid-ads-only", action="store_true")
    lb.add_argument("-n", type=int, default=12)
    lb.add_argument("--key", help="search: only sounds whose vendor sheet names this root note (e.g. C#)")
    lb.add_argument("--bpm", type=float, help="search: only loops at this tempo (±1 BPM)")
    a = ap.parse_args()
    if not a.selftest:
        import cine_home as _ch
        _ch.merge_now()                     # (3.0.0) the one-time merge from ~/.cinematography
    if a.selftest:
        return selftest()
    if a.cmd == "levels":
        r = levels(a.job, a.placement, a.voice, a.fps, a.write)
        for e in r["events"]:
            if e.get("problem"):
                print(f"  ! {e['sfx']}: {e['problem']}"); continue
            print(f"  {e['sfx'] or '?':<14} {e['category']:<8} in {e['in_s']:.3f} s · {e['volume_db']:+.1f} dB "
                  f"(was {e.get('was_volume_db')}) → {e['target_under_voice_db']:+g} dB to the voice, peak {e['peak_after_db']} dBFS"
                  + (" [capped by the peak]" if e.get("capped_by_peak") else ""))
        for w_ in r.get("warnings") or []:
            print(f"  WARN {w_}")
        print(f"density {r['density_per_min']}/min" + (f" (client: {r['client_density_per_min']}/min)" if r.get("client_density_per_min") else "")
              + f" · 09-qa/sfx/LEVELS.json" + (" · placement updated" if a.write else " · --write to apply"))
        return 0
    if a.cmd == "read":
        r = read_form(a.job, a.shot, a.clip, a.track)
        print(f"{r['events']} event(s) · look at {r['sheet']} and fill {r['form']} from its vocabulary")
        return 0
    if a.cmd == "index":
        for f in a.files:
            r = index_file(f, a.kind, a.material)
            print(f"{r['file']}: {r['kind']} · {len(r['events'])} attack(s) in {r['duration']} s")
        return 0
    if a.cmd == "events":
        r = visual_events(a.clip, tracks=a.track, count=a.count)
        if a.job and a.shot:
            os.makedirs(os.path.join(a.job, "09-qa", "sfx"), exist_ok=True)
            json.dump(r, open(os.path.join(a.job, "09-qa", "sfx", f"{a.shot}.events.json"), "w"), indent=1)
        for ev in r["events"]:
            print(f"  {ev['t']:.3f} s  {ev['kind']:<5} at ({ev['x']}, {ev['y']}) strength {ev['strength']} "
                  f"[{ev['confidence']}: {', '.join(ev['votes'])}]")
        print(f"{len(r['events'])} event(s) · {len(r['dropped'])} dropped")
        return 0
    if a.cmd == "conform":
        r = conform(a.job, a.shot, [s.strip() for s in a.sfx.split(",") if s.strip()], a.clip,
                    {t: getattr(a, t) for t in TAGS}, a.track, a.out, a.mux, room=a.room, catalogues=a.catalogues)
        for p in r["events"]:
            print(f"  {p['attack_t']:.3f} s ← {p['source']}#{p['source_event']} · {p['gain_db']:+.1f} dB · "
                  f"lp {p['lowpass']} · wet {p['wet']} · {p['pitch_st']:+g} st · pan {p['pan']} · {'; '.join(p['why'])}")
        rm = r.get("room") or {}
        print(f"  room: {rm.get('library')}: {rm.get('rel')} (decay {rm.get('decay_s')} s)" if rm.get("rel")
              else f"  room: {rm}")
        for f_ in r.get("findings") or []:
            print(f"  ! {f_}")
        v_ = r["verify"]
        print(f"{r['render']}: {len(r['events'])} event(s) · re-check {'OK' if v_['ok'] else 'FAILED'}"
              + ("" if v_["ok"] else ":\n  - " + "\n  - ".join(v_["problems"])))
        return 0 if v_["ok"] else 1
    if a.cmd == "verify":
        p = os.path.join(a.job, "06-sfx", "conform", f"{a.shot}.sfx.wav")
        r = json.load(open(p + ".conform.json", encoding="utf-8"))
        dp = os.path.join(a.job, r["dry"]) if r.get("dry") else p
        v_ = verify_render(dp if os.path.isfile(dp) else p, r["events"], r.get("fps") or 24.0)
        print("re-check OK" if v_["ok"] else "re-check FAILED:\n  - " + "\n  - ".join(v_["problems"]))
        return 0 if v_["ok"] else 1
    if a.cmd == "library":
        C = a.catalogues
        if a.action == "build":
            if not a.arg or not a.name:
                raise SystemExit("usage: library build ROOT --name NAME [--kind ir] [--licence … --paid-ads … --basis …]")
            r = build_library(a.arg[0], a.name, C, a.kind, a.licence, a.paid_ads, a.basis, a.condition, a.licence_csv,
                              mac_root=a.mac_root)
            print(f"{r['catalogue']}: {r['files']} file(s), {r['indexed_now']} indexed now"
                  + (f" — {r['left']} left: run the same command again" if r["left"] else " — complete"))
            return 3 if r["left"] else 0
        if a.action == "measure":
            names = [a.name] if a.name else [json.load(open(mp, encoding="utf-8"))["name"]
                                             for mp in sorted(glob.glob(os.path.join(catalogue_dir(C), "*.library.json")))]
            left = 0
            for nm in names:
                try:
                    r = measure_library(nm, C)
                except SystemExit as e:                  # a library whose folder is not here: say so, keep going
                    print(f"{nm}: skipped — {e}")
                    continue
                left += r["left"]
                print(f"{nm}: {r['measured_now']} measured now" + (f", {r['failed_now']} unreadable" if r["failed_now"] else "")
                      + (f" — {r['left']} left: run the same command again" if r["left"] else " — complete"))
            return 3 if left else 0
        if a.action == "sheet":
            if len(a.arg) != 2:
                raise SystemExit("usage: library sheet JOB SHOT [--all-licences]  (the dispatcher's candidate sheet for the spotter)")
            print(candidate_sheet(a.arg[0], a.arg[1], C, paid_ads_only=not a.all_licences))
            return 0
        if a.action == "blind":
            if len(a.arg) != 2:
                raise SystemExit("usage: library blind QUERIES.json OUT.md  (the blind listening sheet)")
            r = blind_sheet(a.arg[0], a.arg[1], C, paid_ads_only=not a.all_licences)
            print(f"{r['sheet']}: {r['events']} moments, {r['rows']} files to hear — the key is beside it; do not open it")
            return 0
        if a.action == "blind-score":
            print(json.dumps(blind_score(a.arg[0]), indent=1))
            return 0
        if a.action == "list":
            for mp in sorted(glob.glob(os.path.join(catalogue_dir(C), "*.library.json"))):
                m = json.load(open(mp, encoding="utf-8"))
                print(f"  {m['name']:<28} {m.get('kind', 'sfx'):<4} {m.get('files', 0):>5} files · paid ads "
                      f"{m.get('paid_ads', 'unverified')} · {m.get('licence', '?')}"
                      + (f" · {m['condition']}" if m.get("condition") else "")
                      + ("" if resolve_root(m.get("roots") or []) else " · ⚠ not reachable here"))
            return 0
        if a.action == "search":
            # (v2.68.0) music is searchable, but only libraries cleared for paid ads unless the person says otherwise
            pao = a.paid_ads_only or (a.kind == "music" and not a.all_licences)
            for h in search_library(" ".join(a.arg), C, a.lib, a.kind, a.max_dur, pao, a.n, a.key, a.bpm):
                tag = " ".join(x for x in ((h.get("ucs") or {}).get("catid"), f"key {h['key']}" if h.get("key") else "",
                                           f"{h['bpm']} BPM" if h.get("bpm") else "") if x)
                print(f"  {h['score']:>4} · {h['library']:<22} · {h['duration']:>6.2f} s · ads {h['paid_ads']:<10} · "
                      f"{h['rel']}" + (f" [{tag}]" if tag else "") + (f" — {h['description'][:70]}" if h.get("description") else ""))
            return 0
        if a.action == "pull":
            if len(a.arg) != 2:
                raise SystemExit("usage: library pull FILE_OR_REL JOB [--lib NAME]")
            r = pull(a.arg[0], a.arg[1], C, (a.lib or [None])[0])
            print(f"{r['file']} ← {r['source']} · paid ads {r['paid_ads']} · licence beside it (.licence.json)")
            return 0
        if a.action == "ir":
            sp, sz = (a.arg + ["interior", "medium"])[:2]
            rt = SPACE_RT60.get(sp, 0.5) * SPACE_SIZE.get(sz, 1.0)
            r = pick_ir(sp, sz, rt, C)
            print(f"{sp}/{sz} (RT60 ≈ {rt:.2f} s) → " + (f"{r['library']}: {r['rel']} (decay {r.get('decay_s')} s)"
                                                         if r else "no measured space fits: the synthetic tail"))
            return 0
    if a.cmd == "joins":
        r = joins_plan(a.job, a.whoosh, a.pan)
        for row in r["joins"]:
            print(f"  cut {row['n']} at {row['t']} s ({row['from']}→{row['to']}): {row['sound']} — {row['note']}")
        return 0
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
