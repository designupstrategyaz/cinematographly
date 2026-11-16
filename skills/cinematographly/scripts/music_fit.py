#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""music_fit.py — the music fitted to a motion-led cut: the map, the hit list, the fit, the edits, the
arrangement and the checks on what renders.

The music fits the picture: the cuts are made from motion and the story, so the music is edited to them (library
tracks, arranged), and cut changes are only suggested: THE CUT NEVER MOVES BY ITSELF.

  map <track> [--job J] [--engine auto|beat_this|librosa|numpy]
                     beats, downbeats (Beat This! when installed; otherwise the meter's phase from the low-
                     band onsets), bars, 4-bar phrases, section changes, energy per bar, the key (advisory)
                     and how the track ends → 06-music/fit/<track>.map.json
  hits init <job>    the hit list from the cut (07-edit/timeline-dump.json): every cut an optional hit, the
                     end card the button, the dialogue tracks as speech → 07-edit/music/HITS.json, a DRAFT the
                     director edits — marks the 2–4 must-hits, names what each wants, declares the track
  fit <job> [--track F] [--pick N]
                     the in-point over the downbeats, then whole-bar edits at phrase lines, one beat added or
                     dropped only for a must-hit, a pitch-kept stretch of at most 2 % as the last resort; the
                     library's own cutdowns tried first; three plans with every hit's residual in frames and
                     the cut nudges → 07-edit/music/FIT.json (the plan picked), FIT.md (all three); then `rebuild`
  rebuild <job> [--pick N]
                     (a Python render is a preview; a client deliverable is rebuilt in Resolve)
                     the picked plan as an edit to rebuild IN RESOLVE from the
                     ORIGINAL track → 07-edit/music/REBUILD.json (each segment's source in/out and its place on the
                     timeline, in seconds and frames; each seam's crossfade; the end trim and fade; the speed; the
                     original's sha256 and the plan's) and REBUILD.md (the checklist for Fairlight, by computer
                     control), and the console copy that places the ORIGINAL's segments on A5 with sparse markers and
                     a marker per seam → 07-edit/resolve-production-console.music.py. `fit` and `render` call it
  render <job>       a PREVIEW to listen to (48 kHz, 24-bit) → 06-music/fit/<track>.fit.wav and its .conform.json
                     (kind music_fit_preview). Never imported into Resolve: the deliverable is rebuilt there from
                     REBUILD.json (`rebuild`, which this calls)
  stems <job>        the track's stems: the library's own first, Demucs only on demand (MIT, archived, ~1.5×
                     the track's length on a CPU) → 06-music/stems/<track>/
  arrange <job>      the stem energy map: the storyboard's energy per section on bar lines, a one-beat stop-
                     down before a declared reveal, the drop on the payoff, the vocal stem muted under speech →
                     <track>.arranged.wav, a PREVIEW (music_arrangement_preview); REBUILD.md lists the arrangement for
                     Fairlight
  bed <job> [--track F] [--voice V] [--length S] [--under-db N]
                     the bed as a client hears it (a supplement ad job: the approved track opened on 1.8 s of near-silence, its
                     sections swung 14 dB and the ad cut it off mid-phrase; a flat fader hid all three). By default:
                     the opening near-silence trimmed; the length met by ONE bar-aligned seam where the bars before and
                     after match best, placed under speech; the track's own ending landed on the last frame; the sections
                     ridden to one bed level; the bed ducked under the voice (60 ms in, 350 ms out) and 1.5–4.5 kHz
                     carved while it speaks; and the whole set to the CLIENT's level under the voice
                     (audio.<client>.json `music_under_voice_db` — one client's is 38, "barely noticeable") → BED.json,
                     a LEVEL PLAN for Fairlight applied by computer control, and 06-music/bed/<track>.bed.wav, a
                     PREVIEW of it (music_bed_preview) that no console copy places. A fitted render (FIT.json) is used
                     as it is: its edits already made the length and the ending
  check <job>        what `approve export` runs. Rules refuse: no plan, no current REBUILD.json (missing, or its
                     plan_sha or the original's sha256 changed), a preview render on the timeline (07-edit/
                     timeline-dump.json), a cut moved without an approved nudge, a click, a stretch over 2 % or on
                     sung vocals, sung lyrics under speech, edits on a track whose licence is not recorded as
                     allowing them, not 48 kHz. The render is NOT required: the measures run on what Resolve made —
                     the music stem (else the bed) mix_qa.py's report records under 09-qa/mix/ — and warn when
                     there is none. Measures warn: hit offsets, the ending, stop-down depth, punctuation counts, the
                     accent budget shared with the SFX, the key of a join; the share of cuts on a beat as information.
                     (v2.48.0, project switch music-led) Where the job's CHECKPOINT lifts `music-led`, the song is
                     fixed and is the deliverable and the picture is cut to it: no fit, no render of one, no stale fit
                     and no moved-cut nudge is asked for, and the lift prints. Still refused there: the song stretched
                     at all (any ratio but 1.0), an edit of it (bars, an arrangement, a bed seam) its licence is not
                     recorded as allowing, `music: none`, sung lyrics under speech, the named song not on disk
  --selftest

The windows, tiered (they replaced a single window): the IMPACT onset (the transient
peak) is never early; a hard hit is on at 0 to +1 frame after its picture event (+2 warns), a soft hit at 0 to +2
frames; the anticipating gesture is free (audio early is detected at 45 ms, late at 125 ms — ITU-R BT.1359). Stated
in milliseconds from the timeline's rate, so 24, 25 and 30 fps stay right.

What it cannot do: hear. It aligns events and measures seams; whether the music serves the scene is the
director's ear, and `approve export --quote` is where that listening pass is signed. The beat tracker can be
wrong on rubato, live-played or ambient tracks: a low-confidence map says so, and Resolve's Detect Music Beats
overlay is the cross-check. Every threshold marked [assumed] waits for real fits to calibrate it.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, math, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
SR_MAP = 22050                 # analysis rate
SR_OUT = 48000                 # delivery rate (editing-and-audio.md §4)
HOP, NFFT = 512, 2048
STRETCH_CAP = 0.02             # C2: one constant pitch-kept stretch, at most ±2 %
STRETCH_WARN = 0.015           # …and a warning above 1.5 %
CLICK_RATIO = 8.0              # a seam whose sample-step energy is this many times its surroundings' clicks [assumed]
STOPDOWN_DB = 20.0             # a stop-down is at least this far under the bars around it [assumed]
CORPUS_ON_BEAT = 0.31          # specifics-catalogue.md §16.6: 31 % of cuts on a beat in 37 real ads (chance 32 %)
HITS = os.path.join("07-edit", "music", "HITS.json")
FIT = os.path.join("07-edit", "music", "FIT.json")
REBUILD = os.path.join("07-edit", "music", "REBUILD.json")
CONSOLE = os.path.join(HERE, "resolve-production-console.py")
MUSIC_COPY = "resolve-production-console.music.py"
END_FADE_S = 0.75              # the render's (and the rebuild's) fade into the end card's end
# ⛔ Author, 2026-11-05: "`music_fit.py render` cuts the music in Python … This works for previews, but never import like
# that in to Resolve, everything has to be rebuilt and done in Resolve for client deliverables." Every music or SFX file
# a Python tool renders is a PREVIEW: these paths and names. The original track, the composed layer
# (06-music/compose/<job>.layer.wav) and its stems (*.stem-<part>.wav) are source material and do not match.
PREVIEW_NOTE = "a preview to listen to — never imported into Resolve; the deliverable is rebuilt in Resolve from REBUILD.json"
# (v2.50, the review) the folders decide, not a suffix: a library file named `Epic.Full.wav` is an original. Every
# Python render lands in one of these folders; `.preview.` counts only inside the job's own music, SFX or edit folders.
PREVIEW_AUDIO_RE = re.compile(
    r"(?:^|/)(?:06-music/(?:fit|bed|family)|06-sfx/conform)/(?:[^/]+/)*[^/]+"
    r"\.(?:wav|aif|aiff|flac|mp3|m4a|ogg|opus|caf|mp4|mov|mxf)$"
    r"|(?:^|/)(?:06-music|06-sfx|07-edit)/(?:[^/]+/)*[^/]*\.preview\.[^/]+$", re.I)


def is_preview(path) -> bool:
    """True for a Python-rendered music or SFX file — a preview that never goes into Resolve (2026-11-05).
    Paths may be relative or absolute, with / or \\ separators."""
    return bool(PREVIEW_AUDIO_RE.search(str(path or "").replace("\\", "/")))


WANTS = ("downbeat", "beat", "accent", "riser_end", "stop_down", "drop", "entry", "button")
TIERS = ("hard", "soft")                                  # the tiered window (house rule 2026-10-27)
STRATEGIES = ("catch", "anticipate", "play_through")      # how the music meets the hit (Karlin & Wright's terms)
TYPES = ("reveal", "landing", "offer", "title", "line", "button", "turn", "cut", "payoff")
FX_KINDS = ("riser", "impact", "sub_drop", "scratch", "whoosh")
CAMELOT = {"C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B", "B": "1B", "F#": "2B", "C#": "3B",
           "G#": "4B", "D#": "5B", "A#": "6B", "F": "7B",
           "Am": "8A", "Em": "9A", "Bm": "10A", "F#m": "11A", "C#m": "12A", "G#m": "1A", "D#m": "2A",
           "A#m": "3A", "Fm": "4A", "Cm": "5A", "Gm": "6A", "Dm": "7A"}
PCS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KK_MAJ = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]   # Krumhansl & Kessler 1982
KK_MIN = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
STEM_ROLES = {"drums": ("drum", "perc", "beat", "kick"), "bass": ("bass", "sub"), "vocals": ("vocal", "vox", "voice", "lead_vocal"),
              "other": ("other", "keys", "synth", "pad", "string", "guitar", "piano", "fx", "music", "inst")}


def _np():
    import numpy as np
    return np


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel(job: str | None, p: str) -> str:
    return os.path.relpath(p, job).replace(os.sep, "/") if job else p


def absj(job: str | None, p: str) -> str:
    return p if os.path.isabs(p) or not job else os.path.join(job, p)


# ── audio in and out (ffmpeg; no Python audio library needed) ───────────────────────────────────────────
def decode(path: str, sr: int, ch: int = 1):
    np = _np()
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
    x = np.frombuffer(raw, dtype=np.float32).copy()
    return x.reshape(-1, ch) if ch > 1 else x


def encode(x, sr: int, path: str, codec: str = "pcm_s24le") -> str:
    np = _np()
    x = np.asarray(x, dtype=np.float32)
    ch = 1 if x.ndim == 1 else x.shape[1]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i", "-", "-c:a", codec, path]
    subprocess.run(cmd, input=np.clip(x, -1, 1).tobytes(), check=True)
    return path


def stretch_file(src: str, dst: str, ratio: float) -> str:
    """Play `src` at `ratio` × its tempo, pitch kept: ffmpeg's rubberband filter (on both machines), atempo if not."""
    filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL).stdout
    af = f"rubberband=tempo={ratio:.6f}" if " rubberband " in filters else f"atempo={ratio:.6f}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", str(SR_OUT), "-c:a", "pcm_s24le", dst],
                   check=True, stdin=subprocess.DEVNULL)
    return dst


# ── the analysis ────────────────────────────────────────────────────────────────────────────────────────
def spectral(y, sr: int):
    """(times, onset envelope, low-band onset envelope, magnitude spectrogram, freqs)."""
    np = _np()
    if len(y) < NFFT + HOP:
        y = np.pad(y, (0, NFFT + HOP - len(y)))
    view = np.lib.stride_tricks.sliding_window_view(y.astype(np.float32), NFFT)[::HOP]
    win = np.hanning(NFFT).astype(np.float32)
    S = np.concatenate([np.abs(np.fft.rfft(view[i:i + 1024] * win, axis=1)).astype(np.float32)
                        for i in range(0, len(view), 1024)])          # in blocks: a 3-minute track stays small
    freqs = np.fft.rfftfreq(NFFT, 1.0 / sr)
    L = np.log1p(100.0 * S)
    flux = np.maximum(0.0, np.diff(L, axis=0, prepend=L[:1]))
    env = flux.sum(1)
    low = flux[:, freqs < 200].sum(1)
    # a Hann-windowed flux rises fastest when a transient passes the window's last quarter: the frame's
    # three-quarter point is when it happened, not its centre (the centre reads ~23 ms early)
    t = (np.arange(len(env)) * HOP + NFFT * 3 / 4) / sr
    return t, env, low, S, freqs


def _norm(v):
    np = _np()
    s = float(np.std(v)) or 1.0
    return (v - float(np.mean(v))) / s


def tempo_period(env, sr: int) -> int:
    """The beat period in frames: autocorrelation of the onset envelope, weighted toward 120 BPM (a log-normal
    prior one octave wide, as beat trackers commonly use)."""
    np = _np()
    e = _norm(env)
    n = len(e)
    ac = np.correlate(e, e, mode="full")[n - 1:]
    fps = sr / HOP
    best, best_score = None, -1e9
    for lag in range(int(fps * 60 / 200), min(n - 1, int(fps * 60 / 55)) + 1):
        bpm = 60.0 * fps / lag
        prior = math.exp(-0.5 * (math.log2(bpm / 120.0)) ** 2)
        s = ac[lag] * prior
        if s > best_score:
            best, best_score = lag, s
    # a refinement to sub-frame period by a parabola through the peak
    return int(best or round(fps / 2))


def track_beats(env, period: int, tightness: float = 100.0):
    """Dynamic-programming beat tracking (Ellis 2007): the best path of beats ~one period apart through the
    onset envelope. Returns beat frame indices."""
    np = _np()
    e = _norm(env)
    n = len(e)
    score = e.copy()
    back = -np.ones(n, dtype=int)
    lo, hi = max(1, int(round(period / 2))), int(round(2 * period))
    offs = np.arange(lo, hi + 1)
    pen = -tightness * (np.log(offs / float(period))) ** 2
    for t in range(lo, n):
        prev = t - offs
        ok = prev >= 0
        if not ok.any():
            continue
        cand = score[prev[ok]] + pen[ok]
        j = int(np.argmax(cand))
        score[t] = e[t] + cand[j]
        back[t] = prev[ok][j]
    tail = max(0, n - period)
    t = tail + int(np.argmax(score[tail:]))
    beats = []
    while t >= 0:
        beats.append(t)
        t = back[t]
    beats = beats[::-1]
    # trim weak beats at the edges (silence before the music, ring-out after)
    strong = np.percentile(env, 60) if len(env) else 0
    while beats and env[beats[0]] < 0.5 * strong and len(beats) > 4:
        beats.pop(0)
    while beats and env[beats[-1]] < 0.2 * strong and len(beats) > 4:
        beats.pop()
    return beats


def refine(times, y, sr: int, win: float = 0.025) -> list:
    """Each event moved to the steepest rise of the signal's short-time energy within ±win (a 2.9 ms grid):
    the analysis frames are 23 ms, too coarse for a one-frame (42 ms) window."""
    np = _np()
    h = 64
    d = np.abs(np.diff(y, prepend=y[:1]))
    out = []
    for t0 in times:
        a, b = max(0, int((t0 - win) * sr)), min(len(y), int((t0 + win) * sr))
        if b - a < 4 * h:
            out.append(float(t0)); continue
        seg = d[a:b]
        n = len(seg) // h
        e = np.log(seg[:n * h].reshape(n, h).sum(1) + 1e-9)
        rise = np.diff(e, prepend=e[:1])
        out.append(float((a + int(np.argmax(rise)) * h) / sr))
    return out


def downbeat_phase(beat_times, t, low, env):
    """(meter, phase, confidence): which beat of every 3 or 4 carries the low-band accent."""
    np = _np()
    idx = np.clip(np.searchsorted(t, beat_times), 0, len(t) - 1)
    near = lambda v: np.array([float(v[max(0, i - 2):i + 3].max()) for i in idx])   # the peak within ±2 frames
    lb, fb = near(low), near(env)
    cands = []
    for m in (4, 3):
        for ph in range(m):
            sel = slice(ph, None, m)
            if len(lb[sel]) < 2:
                continue
            cands.append((float(np.mean(lb[sel]) + 0.3 * np.mean(fb[sel])), m, ph))
    cands.sort(reverse=True)
    if not cands:
        return 4, 0, 0.0
    four = [c for c in cands if c[1] == 4]
    three = [c for c in cands if c[1] == 3]
    best = four[0] if four and (not three or three[0][0] < 1.15 * four[0][0]) else three[0]
    others = sorted(c[0] for c in cands if c[1] == best[1] and c[2] != best[2])
    conf = (best[0] - (others[-1] if others else 0)) / (abs(best[0]) or 1.0)
    return best[1], best[2], round(max(0.0, min(1.0, conf)), 3)


def chroma_key(S, freqs):
    """The key by the Krumhansl–Kessler profiles on a pitch-class profile — ADVISORY (C4)."""
    np = _np()
    sel = (freqs > 60) & (freqs < 5000)
    pc = (np.round(12 * np.log2(freqs[sel] / 440.0)) + 9) % 12
    prof = np.zeros(12)
    mag = S[:, sel].sum(0)
    for k in range(12):
        prof[k] = float(mag[pc == k].sum())
    best = (-2.0, "C", "major")
    rs = []
    for i in range(12):
        for name, P in (("major", KK_MAJ), ("minor", KK_MIN)):
            r = float(np.corrcoef(prof, np.roll(P, i))[0, 1])
            rs.append(r)
            if r > best[0]:
                best = (r, PCS[i], name)
    rs.sort()
    conf = round(best[0] - rs[-2], 3) if len(rs) > 1 else 0.0
    key = best[1] + ("m" if best[2] == "minor" else "")
    return {"name": f"{best[1]} {best[2]}", "camelot": CAMELOT.get(key), "confidence": conf}


def camelot_distance(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    na, la, nb, lb = int(a[:-1]), a[-1], int(b[:-1]), b[-1]
    d = min((na - nb) % 12, (nb - na) % 12)
    return d + (0 if la == lb else (0 if d == 0 else 1))      # relative major/minor (same number) counts as 0


def analyse(path: str, engine: str = "auto") -> dict:
    np = _np()
    y = decode(path, SR_MAP, 1)
    dur = len(y) / SR_MAP
    t, env, low, S, freqs = spectral(y, SR_MAP)
    used, beats, downs, conf_d = "numpy", None, None, None
    if engine in ("auto", "beat_this"):
        try:
            from beat_this.inference import File2Beats        # MIT; pip install beat-this (+ PyTorch)
            b, d = File2Beats(checkpoint_path="final0", device="cpu", dbn=False)(path)
            beats, downs, used, conf_d = [float(x) for x in b], [float(x) for x in d], "beat_this", 0.9
        except Exception as e:                                  # noqa: BLE001
            if engine == "beat_this":
                raise SystemExit(f"Beat This! is not usable here ({e}) — `pip install beat-this` and PyTorch, "
                                 f"or --engine numpy")
    if beats is None and engine in ("auto", "librosa"):
        try:
            import librosa
            _, bt = librosa.beat.beat_track(y=y, sr=SR_MAP, units="time")
            beats, used = [float(x) for x in bt], "librosa"
        except Exception as e:                                  # noqa: BLE001
            if engine == "librosa":
                raise SystemExit(f"librosa is not usable here ({e}) — pip install librosa, or --engine numpy")
    if beats is None:
        period = tempo_period(env, SR_MAP)
        beats = [float(t[i]) for i in track_beats(env, period)]
    if used == "numpy":
        beats = refine(beats, y, SR_MAP)
    if len(beats) < 4:
        raise SystemExit(f"{os.path.basename(path)}: fewer than four beats found — a beat-free track has no grid to "
                         f"fit; place it by hand (the fit would be a guess)")
    ibi = np.diff(beats)
    k = 8 if len(beats) > 16 else 1                            # over 8 beats, so frame steps average out
    period_s = float(np.median([(beats[i + k] - beats[i]) / k for i in range(len(beats) - k)]))
    tempo = 60.0 / period_s
    drift = float(np.std(ibi) / period_s)
    meter, phase = 4, 0
    if downs is None:
        meter, phase, conf_d = downbeat_phase(beats, t, low, env)
        downs = beats[phase::meter]
    else:
        meter = int(round(np.median([sum(1 for b in beats if d0 - 1e-3 <= b < d1 - 1e-3)
                                     for d0, d1 in zip(downs, downs[1:])]) or 4)) if len(downs) > 2 else 4
    bars = [[round(a, 4), round(b, 4), sum(1 for x in beats if a - 1e-3 <= x < b - 1e-3)] for a, b in zip(downs, downs[1:])]
    if downs:
        bars.append([round(downs[-1], 4), round(min(dur, downs[-1] + meter * period_s), 4), meter])
    # energy and a simple timbre per bar: novelty between bars marks section changes
    rms = np.sqrt(np.convolve(y ** 2, np.ones(HOP) / HOP, mode="same") + 1e-12)
    edges = np.geomspace(60, 8000, 13)
    feats, energy = [], []
    for a, b, _ in bars:
        i0, i1 = np.searchsorted(t, a), max(np.searchsorted(t, b), np.searchsorted(t, a) + 1)
        band = [float(S[i0:i1, (freqs >= lo) & (freqs < hi)].mean()) for lo, hi in zip(edges, edges[1:])]
        feats.append(np.log1p(np.array(band)))
        energy.append(round(20 * math.log10(float(rms[int(a * SR_MAP):max(int(b * SR_MAP), int(a * SR_MAP) + 1)].mean()) + 1e-9), 1))
    nov = [0.0] + [float(1 - np.dot(f0, f1) / ((np.linalg.norm(f0) * np.linalg.norm(f1)) or 1)) for f0, f1 in zip(feats, feats[1:])]
    nv = np.array(nov)
    thr = float(np.median(nv) + 2.5 * (np.median(np.abs(nv - np.median(nv))) or 1e-4))
    sections = [bars[i][0] for i in range(1, len(bars)) if nv[i] > thr and nv[i] >= nv[max(0, i - 1)] and nv[i] >= nv[min(len(nv) - 1, i + 1)]]
    phrases = [bars[i][0] for i in range(0, len(bars), 4)]
    for s in sections:                                          # a section change starts a phrase
        if all(abs(s - p) > 1e-3 for p in phrases):
            phrases.append(s)
    phrases.sort()
    # strong onsets: the accents a hit can land on
    pk = [i for i in range(1, len(env) - 1) if env[i] >= env[i - 1] and env[i] > env[i + 1]]
    thr_on = float(np.percentile(env, 92)) if len(env) else 0
    onsets = [round(x, 4) for x in refine([float(t[i]) for i in pk if env[i] >= thr_on], y, SR_MAP)]
    # how it ends: a last strong hit followed by decay, or a fade
    top = float(np.percentile(env, 99)) if len(env) else 1.0
    tail_i = np.searchsorted(t, max(0.0, dur - 10.0))
    last_hits = [i for i in pk if i >= tail_i and env[i] >= 0.6 * top]
    ending = {"kind": "fade", "t": None}
    if last_hits:
        i = last_hits[-1]
        after = env[i + 3:]
        if not len(after) or float(after.max()) < 0.35 * env[i]:
            te = refine([float(t[i])], y, SR_MAP)[0]
            near = min(downs, key=lambda d: abs(d - te)) if downs else te
            ending = {"kind": "hit", "t": round(near if abs(near - te) < 0.06 else te, 4)}
    if ending["kind"] == "fade":
        lvl = 20 * np.log10(rms + 1e-9)
        ref = float(np.median(lvl[: max(1, int(len(lvl) * 0.8))]))
        below = np.where(lvl > ref - 20)[0]
        ending["t"] = round(float(below[-1] / SR_MAP) if len(below) else dur, 4)
    return {"file": os.path.basename(path), "sha256": sha256_file(path), "duration": round(dur, 4),
            "engine": used, "tempo": round(tempo, 3), "meter": meter, "drift": round(drift, 4),
            "beats": [round(b, 4) for b in beats], "downbeats": [round(d, 4) for d in downs], "bars": bars,
            "phrases": [round(p, 4) for p in phrases], "sections": [round(s, 4) for s in sections],
            "bar_energy_db": energy, "onsets": onsets, "key": chroma_key(S, freqs), "ending": ending,
            "confidence": {"downbeats": conf_d, "tempo_steady": round(max(0.0, 1 - 10 * drift), 3)},
            "advisory": "key is advisory; a downbeat confidence under 0.15 or an unsteady tempo means the grid may "
                        "be wrong — cross-check with Resolve's Detect Music Beats",
            "made": dt.datetime.now().isoformat(timespec="minutes")}


def map_track(path: str, job: str | None = None, engine: str = "auto", force: bool = False) -> dict:
    out_dir = os.path.join(job, "06-music", "fit") if job else os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)
    mp = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + ".map.json")
    if os.path.isfile(mp) and not force:
        try:
            m = json.load(open(mp, encoding="utf-8"))
            if m.get("sha256") == sha256_file(path) and (engine == "auto" or m.get("engine") == engine):
                return m
        except ValueError:
            pass
    m = analyse(path, engine)
    json.dump(m, open(mp, "w", encoding="utf-8"), indent=1)
    return m


# ── the hit list ────────────────────────────────────────────────────────────────────────────────────────
def _timeline(job: str) -> dict | None:
    p = os.path.join(job, "07-edit", "timeline-dump.json")
    try:
        return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None
    except ValueError:
        return None


def cuts_of(job: str) -> tuple:
    """(fps, cut times in seconds, timeline end, speech spans) from the timeline dump."""
    d = _timeline(job)
    if not d:
        return None, [], None, []
    fps = float(d.get("fps") or 24.0)
    rows = {}
    for tn, items in (d.get("tracks") or {}).items():
        rs = []
        for it in items or []:
            s = it.get("start_s") if it.get("start_s") is not None else (it.get("start") or 0) / fps
            du = it.get("duration_s") if it.get("duration_s") is not None else (it.get("duration") or 0) / fps
            rs.append({"name": str(it.get("name") or ""), "t0": float(s), "t1": float(s) + float(du),
                       "transition": "transition" in str(it.get("type") or "").lower()})
        rows[tn] = sorted(rs, key=lambda r: r["t0"])
    v1 = [r for r in rows.get("video1", []) if not r["transition"]]
    cuts = sorted({round(r["t0"], 4) for r in v1[1:]})
    end = max((r["t1"] for rs in rows.values() for r in rs), default=None)
    speech = [[round(r["t0"], 3), round(r["t1"], 3)] for tn in ("audio1", "audio2") for r in rows.get(tn, [])]
    return fps, cuts, end, sorted(speech)


def hits_init(job: str, force: bool = False) -> str:
    p = os.path.join(job, HITS)
    if os.path.isfile(p) and not force:
        raise SystemExit(f"error: {HITS} exists — the director's marks are not overwritten (--force to start again)")
    fps, cuts, end, speech = cuts_of(job)
    if fps is None:
        raise SystemExit("no 07-edit/timeline-dump.json — dump the cut first (resolve-production-console.py "
                         "DUMP_TIMELINE_JSON); the fit is made against the locked cut")
    ec = None
    for sp in glob.glob(os.path.join(job, "07-edit", "titles", "*.title.json")):
        try:
            s = json.load(open(sp, encoding="utf-8"))
        except ValueError:
            continue
        if s.get("kind") in ("endcard", "end-card") and s.get("at_s") is not None:
            ec = {"t": float(s["at_s"]), "dur": float(s.get("duration_s") or 4.0)}
    if ec is None and end:
        ec = {"t": round(max(0.0, end - 4.0), 3), "dur": 4.0, "note": "guessed: the last 4 s — set it"}
    hits = [{"id": f"H{i + 1}", "t": c, "type": "cut", "priority": "optional", "tier": "soft", "want": "beat",
             "strategy": "play_through", "gesture_t": None, "onset": "transient_peak", "cut": True,
             "nudge_ok": True} for i, c in enumerate(cuts)]
    if ec:
        hits.append({"id": "BUTTON", "t": ec["t"], "type": "button", "priority": "must", "tier": "hard", "want": "button",
                     "strategy": "catch", "gesture_t": None, "onset": "transient_peak", "cut": False, "nudge_ok": False})
    d = {"status": "DRAFT — mark the 2–4 must-hits (the reveal, the product landing, the title, the button), name "
                   "what each wants, declare the track; written by music_fit.py hits init",
         "music": "fit", "fps": fps, "duration": end, "start": 0.0, "end_card": ec,
         "track": {"file": "", "vocals": "unknown", "edits_allowed": "unknown", "stems": "none",
                   "key_confirmed": None},
         "hits": hits, "speech": speech, "locked": [], "sections": [], "fx": [], "combine": None,
         "approved_nudges": [], "lane": "ads"}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1)
    return p


def load_hits(job: str) -> dict:
    p = os.path.join(job, HITS)
    if not os.path.isfile(p):
        raise SystemExit(f"no {HITS} — `music_fit.py hits init <job>`, then mark the must-hits")
    return json.load(open(p, encoding="utf-8"))


def hits_problems(H: dict) -> tuple[list, list]:
    P, W = [], []
    if H.get("music") == "none":
        return P, W
    musts = [h for h in H.get("hits") or [] if h.get("priority") == "must"]
    for h in H.get("hits") or []:
        if h.get("want") not in WANTS:
            P.append(f"hit {h.get('id')}: want {h.get('want')!r} — one of {', '.join(WANTS)}")
        if h.get("priority") not in ("must", "optional"):
            P.append(f"hit {h.get('id')}: priority must or optional")
        if not isinstance(h.get("t"), (int, float)):
            P.append(f"hit {h.get('id')}: no time")
    if len(musts) > 4:
        W.append(f"{len(musts)} must-hits — the beat is for a few hits (2–4 by default; untested): the measured ads cut "
                 f"on the beat no more often than chance")
    for h in H.get("hits") or []:
        if h.get("tier") is not None and h.get("tier") not in TIERS:
            P.append(f"hit {h.get('id')}: tier hard or soft")
        if h.get("strategy") is not None and h.get("strategy") not in STRATEGIES:
            P.append(f"hit {h.get('id')}: strategy catch, anticipate or play_through")
        g = h.get("gesture_t")
        if isinstance(g, (int, float)) and isinstance(h.get("t"), (int, float)) and g > float(h["t"]) + 1e-6:
            P.append(f"hit {h.get('id')}: the gesture starts after its impact (gesture_t {g} > t {h['t']})")
    P += density_problems(H)[0]
    W += density_problems(H)[1]
    if not (H.get("track") or {}).get("file"):
        P.append("the hit list names no track (`track.file`) — the owner picks it from the library (never chosen here)")
    tr = H.get("track") or {}
    if tr.get("vocals") not in ("none", "lyrics", "vocal_chops", "unknown"):
        P.append("track.vocals is none, lyrics, vocal_chops or unknown")
    return P, W


def density_problems(H: dict) -> tuple[list, list]:
    """Hit density (house choice, 2026-10-27): hard hits are few. A stop-down (an accented silence)
    counts as a hit. Warnings only (C5) — the density evidence is practitioner-level."""
    W = []
    hard = [h for h in H.get("hits") or [] if tier_of(h) == "hard" and h.get("strategy") != "play_through"
            and isinstance(h.get("t"), (int, float))]
    dur = float(H.get("duration") or 0)
    if dur and dur <= 16 and len(hard) > 2:
        W.append(f"{len(hard)} hard hits in a {dur:.0f} s spot — more than 2 in 15 s reads as Mickey-Mousing; play "
                 f"through the rest (strategy play_through)")
    elif len(hard) > 4:
        W.append(f"{len(hard)} hard hits — 2–4 per spot; the harder you hit something, the more it comes into focus")
    return [], W


# ── the plan: music segments laid on the timeline ───────────────────────────────────────────────────────
class Plan:
    """A fit: the music segments [m0, m1) in play order, the timeline time the first one starts, and the tempo
    ratio (music plays `ratio` × its speed, so a timeline second holds `ratio` music seconds)."""

    def __init__(self, segments, start, ratio=1.0, edits=None, track=None, label=""):
        self.segments = [list(s) for s in segments]
        self.start, self.ratio = float(start), float(ratio)
        self.edits = list(edits or [])
        self.track, self.label = track, label

    def to_timeline(self, m: float):
        acc = 0.0
        for m0, m1 in self.segments:
            if m0 - 1e-6 <= m < m1 - 1e-6:
                return self.start + (acc + m - m0) / self.ratio
            acc += m1 - m0
        return None

    def length(self) -> float:
        return sum(m1 - m0 for m0, m1 in self.segments) / self.ratio

    def events(self, times) -> list:
        """Music event times (any segment may play a bar twice) → their timeline times."""
        out = []
        acc = 0.0
        for m0, m1 in self.segments:
            for m in times:
                if m0 - 1e-6 <= m < m1 - 1e-6:
                    out.append(self.start + (acc + m - m0) / self.ratio)
            acc += m1 - m0
        return sorted(out)

    def seams(self) -> list:
        """Timeline times of the joins between segments."""
        out, acc = [], 0.0
        for m0, m1 in self.segments[:-1]:
            acc += m1 - m0
            out.append(self.start + acc / self.ratio)
        return out

    def as_dict(self) -> dict:
        return {"label": self.label, "track": self.track, "segments": [[round(a, 4), round(b, 4)] for a, b in self.segments],
                "start": round(self.start, 4), "ratio": round(self.ratio, 6), "edits": self.edits}

    @staticmethod
    def from_dict(d: dict) -> "Plan":
        return Plan(d["segments"], d["start"], d.get("ratio", 1.0), d.get("edits"), d.get("track"), d.get("label", ""))


def frame_s(fps: float) -> float:
    return 1.0 / float(fps or 24.0)


def tier_of(h: dict) -> str:
    """A hit's tier (house rule 2026-10-27, the tiered window): `hard` for a director-called hit, `soft` for a
    secondary one. Unset, a must-hit is hard and an optional one soft."""
    t = str(h.get("tier") or "").lower()
    return t if t in TIERS else ("hard" if h.get("priority") == "must" else "soft")


def classify(d: float, fps: float, tier: str = "hard") -> str:
    """The tiered window (house rule 2026-10-27, superseding C1's single window): the IMPACT onset (the measured
    transient peak) never sits early. A hard hit is on at 0 to +1 frame after its picture event and warns at +2;
    a soft hit is on at 0 to +2 frames. Anything else is early or late. The anticipating gesture is free."""
    f = frame_s(fps)
    if d < -0.001:
        return "early"
    if d <= f + 0.001:
        return "on"
    if d <= 2 * f + 0.001:
        return "on" if tier == "soft" else "warn"
    return "late"


def event_times(plan: Plan, M: dict, want: str) -> list:
    if want == "beat":
        return plan.events(M["beats"])
    if want == "accent":
        return plan.events(M["onsets"])
    if want == "entry":
        return plan.events(M["phrases"])
    if want == "button":
        e = M.get("ending") or {}
        if e.get("kind") == "hit" and e.get("t") is not None:
            return plan.events([e["t"]])
        return plan.events(M["downbeats"][-1:])
    return plan.events(M["downbeats"])                          # downbeat, riser_end, stop_down, drop


def residual(plan: Plan, M: dict, h: dict, fps: float):
    """(music time − picture time) for the event that suits the hit best: the nearest one that is not early,
    unless an early one is much closer."""
    ev = event_times(plan, M, h["want"])
    if not ev:
        return None
    p = float(h["t"])
    after = [e - p for e in ev if e - p >= -0.001]
    before = [e - p for e in ev if e - p < -0.001]
    best_after = min(after) if after else None
    best_before = max(before) if before else None
    if best_after is not None and (best_before is None or best_after <= 2 * frame_s(fps) or abs(best_after) <= abs(best_before)):
        return best_after
    return best_before


def score_plan(plan: Plan, M: dict, H: dict) -> tuple:
    fps = float(H.get("fps") or 24)
    beat = 60.0 / float(M["tempo"])
    tot, rows = 0.0, []
    for h in H.get("hits") or []:
        if not isinstance(h.get("t"), (int, float)) or h.get("want") not in WANTS:
            continue
        d = residual(plan, M, h, fps)
        w = 3.0 if h.get("priority") == "must" else 1.0
        if d is None:
            cls, pen = "none", 2.0
        else:
            cls = classify(d, fps, tier_of(h))
            pen = {"on": 0.0, "warn": 0.4}.get(cls, 1.0 + min(abs(d) / beat, 1.0))
        tot += w * pen
        rows.append({"id": h["id"], "t": h["t"], "want": h["want"], "priority": h.get("priority"), "tier": tier_of(h),
                     "residual_ms": None if d is None else round(1000 * d, 1),
                     "residual_frames": None if d is None else round(d * fps, 2), "class": cls})
    # coverage: the music must run from its start to the end card (or the timeline's end)
    ec = H.get("end_card") or {}
    need_to = float(ec.get("t") or H.get("duration") or 0)
    short = max(0.0, need_to - (plan.start + plan.length()))
    tot += 10.0 * short
    for e in plan.edits:
        tot += {"bars": 0.25 if e.get("phrase") else 0.5, "beat": 0.8}.get(e.get("kind"), 0.3)
    if abs(plan.ratio - 1.0) > 1e-6:
        tot += 0.3 + 20.0 * abs(plan.ratio - 1.0)
    return round(tot, 4), rows


def nudges(plan: Plan, M: dict, H: dict) -> list:
    """Cuts a 1–2 frame nudge would put on their wanted event — listed, NEVER applied (house rule)."""
    fps = float(H.get("fps") or 24)
    out = []
    for h in H.get("hits") or []:
        if not h.get("cut") or not h.get("nudge_ok", True) or h.get("want") not in WANTS:
            continue
        d = residual(plan, M, h, fps)
        if d is not None and classify(d, fps, tier_of(h)) == "on":
            continue
        for k in (1, -1, 2, -2):
            hh = dict(h, t=float(h["t"]) + k / fps)
            d2 = residual(plan, M, hh, fps)
            if d2 is not None and classify(d2, fps, tier_of(h)) == "on":
                out.append({"hit": h["id"], "cut_at": h["t"], "move_frames": k, "new_residual_ms": round(1000 * d2, 1),
                            "priority": h.get("priority"), "applied": False})
                break
    return out


def _similar(M: dict, a_i: int, b_i: int) -> float:
    e = M.get("bar_energy_db") or []
    if a_i >= len(e) or b_i >= len(e):
        return 0.0
    return -abs(e[a_i] - e[b_i])


def plans_for(M: dict, H: dict, track_rel: str, label: str = "") -> list:
    """Every plan worth scoring for one track: in-points over the downbeats; then the length fixed by whole
    bars at a phrase line (removed or repeated), one beat only for a must-hit, and a ≤2 % stretch last."""
    fps = float(H.get("fps") or 24)
    start = float(H.get("start") or 0.0)
    ec = H.get("end_card") or {}
    target_end = float(ec["t"]) if ec.get("t") is not None else None
    timeline_end = float(H.get("duration") or (target_end + float(ec.get("dur") or 4.0) if target_end else 0) or 0)
    dur = float(M["duration"])
    downs, beats = M["downbeats"], M["beats"]
    beat = 60.0 / float(M["tempo"])
    bar = beat * int(M.get("meter") or 4)
    vocals = (H.get("track") or {}).get("vocals")
    button = next((h for h in H.get("hits") or [] if h.get("want") == "button"), None)
    end_m = (M.get("ending") or {}).get("t")
    out = []
    first = []
    how = (H.get("track") or {}).get("in", "phrase")
    if isinstance(how, (int, float)):
        ins = [min(downs, key=lambda x: abs(x - float(how)))]
    elif how == "any":
        ins = downs[:-1]
    else:
        ins = [x for x in M["phrases"] if x in downs] or downs[:1]
    for d in ins:
        if end_m is not None and d >= end_m - bar:
            break
        p = Plan([[d, dur]], start, 1.0, [], track_rel, label)
        s, _ = score_plan(p, M, dict(H, hits=[h for h in H.get("hits") or [] if h.get("want") != "button"]))
        first.append((s, d))
    first.sort()
    for _, d in first[:6]:
        base = Plan([[d, dur]], start, 1.0, [], track_rel, label)
        out.append(base)
        if target_end is None or end_m is None or (M.get("ending") or {}).get("kind") != "hit":
            continue
        te = base.to_timeline(end_m)
        if te is None:
            continue
        delta = target_end - te                                # + → the ending comes early: repeat; − → remove
        n = int(round(delta / bar))
        cand_n = sorted({n, n - 1, n + 1} - {0}, key=lambda k: abs(delta - k * bar)) if abs(delta) > frame_s(fps) else []
        # the phrase lines between the last must-hit before the button and the ending, ≥ 1 bar from any hit
        musts = [float(h["t"]) for h in H.get("hits") or [] if h.get("priority") == "must" and h.get("want") != "button"]
        last_must_tl = max([m for m in musts if m < target_end] or [start])
        lines = [p_ for p_ in M["phrases"] if p_ > d and (base.to_timeline(p_) or 0) > last_must_tl + bar * 0.5
                 and p_ < end_m - bar]
        if not lines:
            lines = [x for x in downs if x > d and (base.to_timeline(x) or 0) > last_must_tl and x < end_m - bar]
        for k in cand_n[:2]:
            best = None
            for ln in lines:
                bi = min(range(len(downs)), key=lambda i: abs(downs[i] - ln))
                if k < 0:                                      # remove |k| bars starting at this line
                    j = bi - k
                    if j >= len(downs) or downs[j] >= end_m:
                        continue
                    segs = [[d, downs[bi]], [downs[j], dur]]
                    sim = _similar(M, bi, j)
                    ed = {"kind": "bars", "op": "remove", "bars": -k, "at_m": downs[bi], "to_m": downs[j],
                          "phrase": (-k) % 4 == 0}
                else:                                          # repeat k bars ending at this line
                    i0 = bi - k
                    if i0 < 0 or downs[i0] < d:
                        continue
                    segs = [[d, downs[bi]], [downs[i0], dur]]
                    sim = _similar(M, bi, i0)
                    ed = {"kind": "bars", "op": "repeat", "bars": k, "at_m": downs[bi], "to_m": downs[i0],
                          "phrase": k % 4 == 0}
                if best is None or sim > best[0]:
                    best = (sim, segs, ed)
            if not best:
                continue
            p = Plan(best[1], start, 1.0, [best[2]], track_rel, label)
            out.append(p)
            te2 = p.to_timeline(end_m)
            if te2 is None:
                continue
            rest = target_end - te2
            # one beat added or dropped, only to land a must-hit (the button is one)
            if button and button.get("priority") == "must" and abs(abs(rest) - beat) < 0.25 * beat:
                bi = min(range(len(downs)), key=lambda i: abs(downs[i] - best[2]["to_m"]))
                if rest < 0 and bi + 1 < len(downs):            # drop a beat: start the next segment a beat later
                    segs2 = [list(s) for s in p.segments]
                    segs2[-1][0] = segs2[-1][0] + beat
                    out.append(Plan(segs2, start, 1.0, p.edits + [{"kind": "beat", "op": "drop"}], track_rel, label))
                elif rest > 0:
                    segs2 = [list(s) for s in p.segments]
                    segs2[-1][0] = segs2[-1][0] - beat
                    out.append(Plan(segs2, start, 1.0, p.edits + [{"kind": "beat", "op": "add"}], track_rel, label))
        # the last resort: one constant pitch-kept stretch, ≤ 2 %, never on sung vocals (C2)
        if vocals != "lyrics":
            for p in list(out):
                if p.ratio != 1.0 or p.track != track_rel:
                    continue
                te3 = p.to_timeline(end_m)
                if te3 is None:
                    continue
                span = te3 - start
                want_span = target_end - start
                if span <= 0 or want_span <= 0 or abs(span - want_span) <= frame_s(fps):
                    continue
                r = span / want_span                           # play faster when the music runs long
                if abs(r - 1.0) <= STRETCH_CAP + 1e-9:
                    out.append(Plan(p.segments, start, r, p.edits + [{"kind": "stretch", "ratio": round(r, 6)}],
                                    track_rel, label))
    # a plan that runs past the timeline's end is trimmed in the render; one that stops short is penalised
    return out


def cutdowns(track_abs: str) -> list:
    """The library's own edits of a track (60/30/15 s) beside it — tried before any edit of ours (M4)."""
    d, stem = os.path.dirname(track_abs), os.path.splitext(os.path.basename(track_abs))[0]
    base = re.sub(r"[\s_-]*(full|main|master)$", "", stem, flags=re.I)
    out = []
    for p in glob.glob(os.path.join(d, "*")):
        n = os.path.splitext(os.path.basename(p))[0]
        if p == track_abs or not os.path.isfile(p) or not p.lower().endswith((".wav", ".mp3", ".aif", ".aiff", ".flac", ".m4a")):
            continue
        if n.lower().startswith(base.lower()) and re.search(r"(?<!\d)(60|30|15|10|6)\s*(s|sec|second)?s?(?!\d)", n[len(base):], re.I):
            out.append(p)
    return sorted(out)


def fit(job: str, track: str | None = None, engine: str = "auto", top: int = 3) -> dict:
    H = load_hits(job)
    P, W = hits_problems(H)
    if H.get("music") == "none":
        raise SystemExit("HITS.json says music: none — nothing to fit")
    if P:
        raise SystemExit("the hit list does not hold:\n  - " + "\n  - ".join(P))
    tr = track or (H.get("track") or {}).get("file")
    ta = absj(job, tr)
    if not os.path.isfile(ta):
        raise SystemExit(f"track {tr!r} not found")
    fps_now, cuts_now, _, _ = cuts_of(job)
    cands = []
    for path, label in [(ta, "the track")] + [(c, "library cutdown " + os.path.basename(c)) for c in cutdowns(ta)]:
        M = map_track(path, job, engine)
        for p in plans_for(M, H, rel(job, path), label):
            s, rows = score_plan(p, M, H)
            if label != "the track":
                s -= 0.2                                        # the library's own edit beats ours (M4)
            cands.append((s, p, rows, M))
    if not cands:
        raise SystemExit("no plan could be made — is the track shorter than the cut, or beat-free?")
    cands.sort(key=lambda c: c[0])
    seen, best = set(), []
    for s, p, rows, M in cands:
        sig = (p.track, round(p.segments[0][0], 2), len(p.segments), round(p.ratio, 4))
        if sig in seen:
            continue
        seen.add(sig)
        best.append({"score": s, "plan": p.as_dict(), "hits": rows, "nudges": nudges(p, M, H),
                     "map": rel(job, os.path.join(job, "06-music", "fit", os.path.splitext(os.path.basename(absj(job, p.track)))[0] + ".map.json")),
                     "engine": M["engine"], "tempo": M["tempo"], "key": M["key"], "ending": M["ending"],
                     "confidence": M["confidence"]})
        if len(best) >= top:
            break
    out = {"job": os.path.basename(os.path.abspath(job)), "made": dt.datetime.now().isoformat(timespec="minutes"),
           "fps": fps_now or H.get("fps"), "cuts_at_fit": cuts_now, "plans": best, "picked": 0,
           "hit_list_warnings": W, "rule": "music only; the cut never moves; nudges are listed"}
    p = os.path.join(job, FIT)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    open(p[:-5] + ".md", "w", encoding="utf-8").write(fit_md(out))
    rebuild(job)                                            # the picked plan, as the edit Resolve rebuilds (2026-11-05)
    return out


def fit_md(F: dict) -> str:
    L = [f"# Music fit — {F['job']}", "", f"Made {F['made']}. The cut never moves; nudges are suggestions for the owner.", ""]
    for i, b in enumerate(F["plans"]):
        p = b["plan"]
        L += [f"## Plan {i + 1}{' (picked)' if i == F.get('picked', 0) else ''} — score {b['score']}",
              f"- {p['label']}: `{p['track']}` from {p['segments'][0][0]:.2f} s, starting at {p['start']:.2f} s on the timeline"
              + (f", stretched ×{p['ratio']:.4f}" if abs(p['ratio'] - 1) > 1e-6 else ""),
              "- edits: " + ("; ".join(f"{e.get('op', '')} {e.get('bars', '')} {e['kind']}".strip() for e in p["edits"]) or "none"),
              f"- {b['engine']} grid, {b['tempo']:.1f} BPM, key {b['key'].get('name')} ({b['key'].get('camelot')}, advisory), "
              f"ends with a {b['ending'].get('kind')}", "", "| Hit | at | wants | residual | |", "|---|---|---|---|---|"]
        for r in b["hits"]:
            L.append(f"| {r['id']} ({r['priority']}) | {r['t']:.3f} s | {r['want']} | "
                     f"{'—' if r['residual_frames'] is None else str(r['residual_frames']) + ' f'} | {r['class']} |")
        if b["nudges"]:
            L += ["", "Cut nudges (not applied — approve in HITS.json `approved_nudges`):"]
            L += [f"- {n['hit']} at {n['cut_at']:.3f} s: move {n['move_frames']:+d} frame(s) → {n['new_residual_ms']} ms" for n in b["nudges"]]
        L.append("")
    return "\n".join(L)


# ── the render ──────────────────────────────────────────────────────────────────────────────────────────
PRE_S = 0.010                  # the splice sits 10 ms before the join's downbeat: the transient masks it (M3)


def seam_xfades(plan: "Plan", M: dict) -> list:
    """Per join, the crossfade: ~3 ms over a strong transient, a 40 ms equal-power fade where it is soft (M3)."""
    on = M.get("onsets") or []
    return [0.003 if any(abs(o - plan.segments[k][0]) < 0.03 for o in on) else 0.040 for k in range(1, len(plan.segments))]


def assemble(x, sr: int, plan: Plan, M: dict):
    """The segments joined just before each join's downbeat, each crossfade centred on the splice, so nothing
    after a join moves in time."""
    np = _np()
    pre = int(PRE_S * sr)
    xfs = [int(v * sr) for v in seam_xfades(plan, M)]
    out = None
    nseg = len(plan.segments)
    for k, (m0, m1) in enumerate(plan.segments):
        h_in = xfs[k - 1] // 2 if k else 0
        h_out = xfs[k] - xfs[k] // 2 if k < nseg - 1 else 0
        a = max(0, int(m0 * sr) - (pre if k else 0) - h_in)
        b = min(len(x), (int(m1 * sr) - pre + h_out) if k < nseg - 1 else int(m1 * sr))
        piece = x[a:b]
        if out is None:
            out = piece
            continue
        xf = min(xfs[k - 1], len(out), len(piece))
        if xf <= 1:
            out = np.concatenate([out, piece])
            continue
        u = np.linspace(0, 1, xf, dtype=np.float32)
        fo, fi = np.cos(u * np.pi / 2), np.sin(u * np.pi / 2)
        if out.ndim > 1:
            fo, fi = fo[:, None], fi[:, None]
        out = np.concatenate([out[:-xf], out[-xf:] * fo + piece[:xf] * fi, piece[xf:]])
    return out


def render(job: str, pick: int | None = None) -> dict:
    """A PREVIEW of the picked plan, cut in Python, to listen to (2026-11-05: "This works for previews, but
    never import like that in to Resolve"). It stays where other tools read it (06-music/fit/<track>.fit.wav,
    F["render"]); the deliverable is rebuilt in Resolve from the original (`rebuild`, called at the end)."""
    np = _np()
    F = json.load(open(os.path.join(job, FIT), encoding="utf-8"))
    if pick is not None:
        F["picked"] = int(pick)
    b = F["plans"][F.get("picked", 0)]
    plan = Plan.from_dict(b["plan"])
    M = json.load(open(os.path.join(job, b["map"]), encoding="utf-8"))
    H = load_hits(job)
    ta = absj(job, plan.track)
    x = decode(ta, SR_OUT, 2)
    y = assemble(x, SR_OUT, plan, M)
    td = tempfile.mkdtemp(prefix="mfit-")
    if abs(plan.ratio - 1.0) > 1e-6:
        if (H.get("track") or {}).get("vocals") == "lyrics":
            raise SystemExit("refused: a stretch on a track with sung vocals")
        a_p = encode(y, SR_OUT, os.path.join(td, "a.wav"))
        y = decode(stretch_file(a_p, os.path.join(td, "b.wav"), plan.ratio), SR_OUT, 2)
    lead = np.zeros((int(round(plan.start * SR_OUT)), 2), dtype=np.float32)
    y = np.concatenate([lead, y])
    ec = H.get("end_card") or {}
    end = float(H.get("duration") or ((ec.get("t") or 0) + (ec.get("dur") or 0)) or len(y) / SR_OUT)
    n_end = int(round(end * SR_OUT))
    if len(y) > n_end:
        y = y[:n_end].copy()
        f = min(int(END_FADE_S * SR_OUT), len(y))
        y[-f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]
    stem = os.path.splitext(os.path.basename(plan.track))[0]
    out = os.path.join(job, "06-music", "fit", stem + ".fit.wav")
    encode(y, SR_OUT, out)
    side = {"kind": "music_fit_preview", "preview": True, "sources": [{"file": plan.track, "role": "music"}],
            "plan": plan.as_dict(), "made": dt.datetime.now().isoformat(timespec="minutes"),
            "note": PREVIEW_NOTE + " (derived from the track: its manifest row and licence cover it, mix_qa.py)"}
    json.dump(side, open(out + ".conform.json", "w", encoding="utf-8"), indent=1)
    F["render"] = {"file": rel(job, out), "sha256": sha256_file(out), "sr": SR_OUT, "preview": True, "note": PREVIEW_NOTE}
    json.dump(F, open(os.path.join(job, FIT), "w", encoding="utf-8"), indent=1)
    rebuild(job)
    shutil.rmtree(td, ignore_errors=True)
    return F


# ── the rebuild: the picked plan as an edit made IN RESOLVE from the original (2026-11-05) ────────────
def plan_sha(plan_dict: dict) -> str:
    """The picked plan's fingerprint: REBUILD.json carries it, so a plan picked or fitted since shows as stale."""
    return hashlib.sha256(json.dumps(plan_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def end_of(H: dict) -> float | None:
    """Where the music stops on the timeline — the render's rule: the hit list's duration, else the end card's end."""
    ec = H.get("end_card") or {}
    return float(H.get("duration") or ((ec.get("t") or 0) + (ec.get("dur") or 0)) or 0) or None


def rebuild_segments(plan: Plan, M: dict, fps: float, end_t: float | None = None) -> tuple[list, list, dict]:
    """(segments, seams, end): the plan as the edit Resolve rebuilds from the original.

    Seconds are assemble()'s own cut points: a join's incoming segment starts PRE_S before its downbeat and the
    outgoing one ends PRE_S before the downbeat it skips; the segments abut, each placed at plan.start + the
    preceding lengths ÷ the ratio; the crossfade (seam_xfades) is centred on each splice; the end is trimmed at the
    timeline's end with a 0.75 s fade, as render() does. Frames are whole frames at `fps` for the scripting API, made
    so the segments still abut: each segment's source→timeline offset is rounded once, so its downbeat sits within
    half a frame of the plan (offset_ms, slipped by hand in Fairlight), and each splice is put on the frame at or
    before PRE_S ahead of both downbeats it touches, so no downbeat transient is cut. src_out_f is exclusive."""
    fps = float(fps or 24.0)
    r = float(plan.ratio or 1.0)
    segs = [list(map(float, s)) for s in plan.segments]
    n = len(segs)
    xfs = seam_xfades(plan, M or {})
    cin = [m0 - (PRE_S if k else 0.0) for k, (m0, _m1) in enumerate(segs)]
    cout = [m1 - PRE_S if k < n - 1 else m1 for k, (_m0, m1) in enumerate(segs)]
    rec, acc = [], 0.0
    for k in range(n):
        rec.append(plan.start + acc / r)
        acc += cout[k] - cin[k]
    down = [rec[k] + (segs[k][0] - cin[k]) / r for k in range(n)]      # plan.start, then plan.seams()
    music_end = rec[-1] + (cout[-1] - cin[-1]) / r
    trims = end_t is not None and music_end > end_t + 1e-6
    L = n if not trims else max(1, sum(1 for k in range(n) if rec[k] < end_t - 1e-6))
    if trims:
        cout[L - 1] = cin[L - 1] + (end_t - rec[L - 1]) * r
    one = abs(r - 1.0) < 1e-6
    E = int(round(end_t * fps)) if trims else None
    if one:
        off = [int(round((down[k] - segs[k][0]) * fps)) for k in range(L)]
        S = [None] * L
        for k in range(1, L):
            t_in = segs[k][0] + off[k] / fps             # the incoming downbeat, placed on whole frames
            t_out = segs[k - 1][1] + off[k - 1] / fps    # where the outgoing segment would reach the downbeat it skips
            S[k] = int(math.floor((min(t_in, t_out) - PRE_S) * fps + 1e-6))
        rec_f = [max(0, int(math.floor(segs[0][0] * fps + 1e-6)) + off[0])] + S[1:]
        in_f = [rec_f[k] - off[k] for k in range(L)]
        out_f = [S[k + 1] - off[k] for k in range(L - 1)]
        out_f.append(E - off[L - 1] if trims else int(math.floor(cout[L - 1] * fps + 1e-6)))
        offs = [round(1000.0 * (segs[k][0] + off[k] / fps - down[k]), 1) for k in range(L)]
    else:                                                # not placed by script: the speed change comes first
        rec_f = [int(round(rec[k] * fps)) for k in range(L)]
        in_f = [int(round(cin[k] * fps)) for k in range(L)]
        out_f = [int(round(cout[k] * fps)) for k in range(L)]
        offs = [None] * L
    rows = []
    for k in range(L):
        if out_f[k] <= in_f[k]:
            raise SystemExit(f"segment {k + 1} of the plan is under one frame long at {fps:g} fps — fit again")
        row = {"k": k + 1, "src_in_s": round(cin[k], 4), "src_out_s": round(cout[k], 4),
               "src_in_f": in_f[k], "src_out_f": out_f[k], "frames": out_f[k] - in_f[k],
               "record_s": round(rec[k], 4), "record_end_s": round(rec[k] + (cout[k] - cin[k]) / r, 4),
               "record_f": rec_f[k],
               "record_end_f": rec_f[k] + (out_f[k] - in_f[k]) if one else int(round((rec[k] + (cout[k] - cin[k]) / r) * fps)),
               "downbeat_s": round(down[k], 4), "offset_ms": offs[k]}
        if not one:
            row.update(retimed_in_s=round(cin[k] / r, 4), retimed_out_s=round(cout[k] / r, 4))
        rows.append(row)
    seams = [{"k": k, "splice_s": round(rec[k], 4), "splice_f": rec_f[k], "downbeat_s": round(down[k], 4),
              "crossfade_s": xfs[k - 1], "crossfade_ms": round(1000.0 * xfs[k - 1], 1), "centred": True,
              "between": [k, k + 1]} for k in range(1, L)]
    if trims:
        nf = int(round(END_FADE_S * fps))
        end = {"trim": True, "t_s": round(end_t, 4), "frame": E, "fade_s": END_FADE_S,
               "fade_from_s": round(end_t - END_FADE_S, 4), "fade_from_f": E - nf, "music_end_s": round(music_end, 4)}
    else:
        end = {"trim": False, "t_s": round(music_end, 4), "frame": rows[-1]["record_end_f"], "fade_s": 0.0,
               "music_end_s": round(music_end, 4), "note": "the track's own ending plays out: no trim, no fade"}
    return rows, seams, end


def rebuild_state(job: str, F: dict | None = None) -> tuple[dict | None, str | None]:
    """(REBUILD.json, None) when it is current; (whatever is there, the reason) when it is missing or stale."""
    p = os.path.join(job, REBUILD)
    if not os.path.isfile(p):
        return None, "missing"
    try:
        RB = json.load(open(p, encoding="utf-8"))
    except ValueError:
        return None, f"{REBUILD} is not valid JSON"
    if F is None:
        fp = os.path.join(job, FIT)
        F = json.load(open(fp, encoding="utf-8")) if os.path.isfile(fp) else None
    if not F:
        return RB, "there is no fit for it to describe"
    b = F["plans"][F.get("picked", 0)]
    if RB.get("plan_sha") != plan_sha(b["plan"]):
        return RB, "the picked plan changed after it was written"
    # (v2.50, the review) the plan alone is not the edit: the frame rate, the end card's trim and the start live
    # outside it, so the table is recomputed and compared
    try:
        H = load_hits(job)
        mp = os.path.join(job, b["map"]) if b.get("map") else ""
        M = json.load(open(mp, encoding="utf-8")) if mp and os.path.isfile(mp) else {}
        fps = float(F.get("fps") or H.get("fps") or 24)
        rows, seams, end = rebuild_segments(Plan.from_dict(b["plan"]), M, fps, end_of(H))
    except Exception as e:                                  # noqa: BLE001
        return RB, f"the rebuild table could not be recomputed ({e})"
    if abs(float(RB.get("fps") or 0) - fps) > 1e-6 or RB.get("segments") != rows or RB.get("seams") != seams \
            or RB.get("end") != end:
        return RB, "the frame rate, the end card or the segment table changed after it was written"
    o = absj(job, (RB.get("original") or {}).get("file") or "")
    if not os.path.isfile(o):
        return RB, f"the original track it names ({(RB.get('original') or {}).get('file')}) is not on disk"
    if sha256_file(o) != (RB.get("original") or {}).get("sha256"):
        return RB, "the original track changed after it was written"
    return RB, None


def current_rebuild(job: str) -> dict:
    """REBUILD.json, written again when it is missing or stale."""
    RB, why = rebuild_state(job)
    return RB if not why else rebuild(job)


def rebuild(job: str, pick: int | None = None) -> dict:
    """07-edit/music/REBUILD.json and REBUILD.md — the picked plan as the edit to rebuild IN RESOLVE from the ORIGINAL
    track — and the console copy that places the original's segments on A5 (2026-11-05)."""
    fp = os.path.join(job, FIT)
    if not os.path.isfile(fp):
        raise SystemExit("no fit — `music_fit.py fit <job>` first, then `rebuild`")
    F = json.load(open(fp, encoding="utf-8"))
    if pick is not None:
        F["picked"] = int(pick)
        json.dump(F, open(fp, "w", encoding="utf-8"), indent=1)
    i = int(F.get("picked", 0))
    b = F["plans"][i]
    plan = Plan.from_dict(b["plan"])
    H = load_hits(job)
    mp = os.path.join(job, b["map"]) if b.get("map") else ""
    M = json.load(open(mp, encoding="utf-8")) if mp and os.path.isfile(mp) else {}
    fps = float(F.get("fps") or H.get("fps") or 24)
    ta = absj(job, plan.track)
    if not os.path.isfile(ta):
        raise SystemExit(f"the original track {plan.track!r} is not on disk — the rebuild starts from it")
    rows, seams, end = rebuild_segments(plan, M, fps, end_of(H))
    one = abs(plan.ratio - 1.0) < 1e-6
    RB = {"kind": "music_rebuild", "job": os.path.basename(os.path.abspath(job)),
          "made": dt.datetime.now().isoformat(timespec="minutes"),
          "rule": "the Python render is a preview; the client's music is rebuilt in Resolve from the "
                  "original — placed by the scripting API, crossfades, fades and any speed change in Fairlight by "
                  "computer control (the computer-control rule)",
          "original": {"file": rel(job, ta) if os.path.abspath(ta).startswith(os.path.abspath(job)) else ta,
                       "sha256": sha256_file(ta)},
          "picked": i, "label": plan.label, "plan_sha": plan_sha(b["plan"]), "plan": b["plan"],
          "fps": fps, "ratio": plan.ratio, "start_s": plan.start, "pre_s": PRE_S, "track": 5,
          "placed_by_script": one,
          "speed": None if one else {"ratio": plan.ratio, "percent": round(100.0 * plan.ratio, 3), "pitch": "preserved"},
          "segments": rows, "seams": seams, "end": end,
          "preview": (F.get("render") or {}).get("file"),
          "export": "the music stem from Resolve (A5–A6 only, the ducking on) into 09-qa/mix/, passed to `mix_qa.py "
                    "measure` as --music; `music_fit.py check` measures it"}
    if (F.get("render") or {}).get("arranged"):
        cj = absj(job, F["render"]["file"]) + ".conform.json"
        A = json.load(open(cj, encoding="utf-8")) if os.path.isfile(cj) else {}
        RB["arrangement"] = {"preview": F["render"]["file"], "stems": [s.get("file") for s in A.get("sources") or []
                                                                       if s.get("role") == "music stem"],
                             "sections": A.get("sections") or [], "stop_downs": A.get("stop_downs") or [],
                             "drops": A.get("drops") or [], "vocals_muted_under": H.get("speech") or [],
                             "levels_db": LEVELS}
    p = os.path.join(job, REBUILD)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(RB, open(p, "w", encoding="utf-8"), indent=1)
    open(p[:-5] + ".md", "w", encoding="utf-8").write(rebuild_md(RB))
    console_copy(job, F, M, H, RB)
    return RB


def _tc(s: float) -> str:
    return f"{s:.3f} s"


def rebuild_md(RB: dict) -> str:
    """REBUILD.md — the checklist for the Resolve side, by computer control, in plain English."""
    one = RB["placed_by_script"]
    o = RB["original"]
    name = os.path.basename(o["file"])
    segs, seams, end = RB["segments"], RB["seams"], RB["end"]
    L = [f"# Music rebuild in Resolve — {RB['job']}", "",
         f"Made {RB['made']} by `music_fit.py rebuild`. The Python render is a preview. The "
         f"music the client gets is rebuilt here, in DaVinci Resolve, from the original track.", "",
         f"- Original: `{o['file']}` (sha256 {o['sha256'][:12]}…)",
         f"- Plan: {RB.get('label') or 'the track'}, plan {RB['picked'] + 1} as picked (plan_sha {RB['plan_sha'][:12]}…)",
         f"- Frame rate: {RB['fps']:g} fps. Every time and frame counts from the timeline's first frame.",
         "- Speed: " + ("×1.0, no speed change." if one else
                       f"×{RB['ratio']:.4f} ({RB['speed']['percent']:g} %), with the pitch kept."),
         f"- Track: A{RB['track']}, the music lane.", ""]
    if RB.get("preview"):
        L += [f"`{RB['preview']}` is a preview to listen to. Never import it into Resolve.", ""]
    L += ["## What the console script does", ""]
    if one:
        L += [f"`07-edit/{MUSIC_COPY}` imports the original once and places its {len(segs)} segment(s) on A5 at the "
              f"frames below. It reads each one back and reports any that differ. It adds a marker at every seam and at "
              f"the end fade. It never places over a clip and never deletes anything.", ""]
    else:
        L += [f"`07-edit/{MUSIC_COPY}` places the original WHOLE on A5 at the first frame, with the markers. It does "
              f"not place the segments, because the speed change comes first.", ""]
    L += ["## The segments", "",
          "| # | source in → out | on the timeline | frames: source in → out, at | downbeat at | offset |",
          "|---|---|---|---|---|---|"]
    for s in segs:
        L.append(f"| {s['k']} | {_tc(s['src_in_s'])} → {_tc(s['src_out_s'])} | {_tc(s['record_s'])} → "
                 f"{_tc(s['record_end_s'])} | {s['src_in_f']} → {s['src_out_f']}, at {s['record_f']} | "
                 f"{_tc(s['downbeat_s'])} | " + ("—" if s.get("offset_ms") is None else f"{s['offset_ms']:+g} ms") + " |")
    L += ["", "Source times are in the original. The out frame is the first frame NOT played.", "",
          "## The checklist — in Resolve, by computer control", "",
          "The computer-control rule: Fairlight work is done by computer control, never by the scripting API.", ""]
    n = 1
    if one:
        L.append(f"{n}. Open the timeline. Check A5: {len(segs)} clip(s) of `{name}`, at the frames in the table. Each "
                 f"clip's start and length match it.")
        n += 1
        slips = [s for s in segs if abs(s.get("offset_ms") or 0) >= 1.0]
        if slips:
            L.append(f"{n}. The script places on whole frames, so some downbeats sit a little off the plan. In "
                     f"Fairlight, slip the audio inside each of these clips (the clip stays where it is) so its downbeat "
                     f"sits where the plan has it: " +
                     "; ".join(f"segment {s['k']} lands {abs(s['offset_ms']):g} ms "
                               f"{'early' if s['offset_ms'] < 0 else 'late'} — slip it {abs(s['offset_ms']):g} ms "
                               f"{'later' if s['offset_ms'] < 0 else 'earlier'}, downbeat at {_tc(s['downbeat_s'])}"
                               for s in slips) + ".")
            n += 1
    else:
        L.append(f"{n}. Check A5: the original, whole, at the first frame. Change its speed to {RB['speed']['percent']:g} % "
                 f"with pitch correction on (Change Clip Speed). Do this before any cut.")
        n += 1
        L.append(f"{n}. Cut the retimed clip into the segments and move each to its place on the timeline. In the "
                 f"retimed clip, segment k runs from its retimed in to its retimed out: " +
                 "; ".join(f"segment {s['k']}: {_tc(s['retimed_in_s'])} → {_tc(s['retimed_out_s'])}, placed at "
                           f"{_tc(s['record_s'])}" for s in segs) +
                 ". A bar that plays twice needs a second copy of the clip. Remove only the unused parts of this clip; "
                 "touch nothing else on the timeline.")
        n += 1
    for sm in seams:
        L.append(f"{n}. Seam {sm['k']}, the cut at frame {sm['splice_f']} ({_tc(sm['splice_f'] / RB['fps'])}), between "
                 f"segments {sm['between'][0]} and {sm['between'][1]}: in Fairlight, add a {sm['crossfade_ms']:g} ms "
                 f"crossfade centred on the cut. The downbeat after it plays at {_tc(sm['downbeat_s'])}; keep the cut "
                 f"before it.")
        n += 1
    if end.get("trim"):
        L.append(f"{n}. The end: the music stops at {_tc(end['t_s'])} (frame {end['frame']}). In Fairlight, fade it out "
                 f"over the last {end['fade_s']:g} s, from {_tc(end['fade_from_s'])} to {_tc(end['t_s'])}.")
    else:
        L.append(f"{n}. The end: no trim and no fade. The track's own ending plays out at {_tc(end['t_s'])}.")
    n += 1
    if RB.get("arrangement"):
        A = RB["arrangement"]
        L.append(f"{n}. The preview was arranged from stems (`arrange`). The original on A5 is NOT that arrangement. "
                 f"Rebuild it in Fairlight from the stems ({', '.join(f'`{x}`' for x in A['stems']) or 'see STEMS.json'}): "
                 f"the section levels in REBUILD.json, a one-beat stop before each stop-down "
                 f"({', '.join(_tc(t) for t in A['stop_downs']) or 'none'}), and the vocal stem muted under speech "
                 f"({', '.join(f'{a:g}–{z:g} s' for a, z in A['vocals_muted_under']) or 'none'}). Without that, sung "
                 f"lyrics play under the voice.")
        n += 1
    L.append(f"{n}. Listen at every seam and at the end, at full level and on headphones: no click, no doubled hit, "
             f"no lost beat, no jump in level.")
    n += 1
    L.append(f"{n}. Export the music stem for the mix gate: render A5–A6 only, the ducking on, at 48 kHz, into "
             f"`09-qa/mix/`. Pass it to `mix_qa.py measure` as `--music`. Then `music_fit.py check <job>` measures the "
             f"clicks, the hits and the stop-downs on what Resolve made.")
    L += ["", "If the plan changes, run `music_fit.py rebuild <job>` again: REBUILD.json carries the plan's sha256, and "
              "`approve export` refuses a stale one.", ""]
    return "\n".join(L)


def console_music_fit(job: str, RB: dict, color: str | None = None) -> dict:
    """MUSIC_FIT for the console: the ORIGINAL track (never a render), and its segments when the script places them."""
    o = RB["original"]
    mf = {"file": os.path.abspath(absj(job, o["file"])), "sha256": o["sha256"], "track": int(RB.get("track") or 5),
          "record_offset_frames": 0,
          "segments": [{"src_in_f": s["src_in_f"], "src_out_f": s["src_out_f"], "record_f": s["record_f"]}
                       for s in RB["segments"]] if RB.get("placed_by_script") else []}
    if color:
        mf["color"] = color
    return mf


def rebuild_markers(RB: dict) -> list:
    """A marker per seam (its crossfade) and one over the end fade — what Fairlight work is left, at its frame."""
    out = [(s["splice_f"], "Cyan", f"Music seam {s['k']} — crossfade {s['crossfade_ms']:g} ms",
            "add it in Fairlight by computer control (07-edit/music/REBUILD.md)", 1, "") for s in RB.get("seams") or []]
    e = RB.get("end") or {}
    if e.get("trim"):
        out.append((e["fade_from_f"], "Cyan", f"Music end — fade {1000 * e['fade_s']:g} ms",
                    f"fade to silence at {e['t_s']:g} s, in Fairlight by computer control (REBUILD.md)",
                    max(1, int(e["frame"]) - int(e["fade_from_f"])), ""))
    return out


def merge_markers(*lists) -> list:
    """One marker per frame (Resolve keeps one): later lists add their name to an earlier marker on the same frame."""
    by = {}
    for lst in lists:
        for m in lst:
            m = tuple(m)
            if m[0] < 0:
                continue
            if m[0] in by:
                o = by[m[0]]
                by[m[0]] = (o[0], o[1], f"{o[2]} · {m[2]}") + tuple(o[3:] if len(o) > 3 else m[3:])
            else:
                by[m[0]] = m
    return [by[f] for f in sorted(by)]


def sparse_markers(job: str, F: dict, M: dict, H: dict) -> list:
    """Phrase starts (Red), declared hits (Green), nudge candidates (Yellow) — sparse, never every beat."""
    b = F["plans"][F.get("picked", 0)]
    plan = Plan.from_dict(b["plan"])
    fps = float(F.get("fps") or H.get("fps") or 24)
    mk = {}
    for t in plan.events((M or {}).get("phrases") or []):
        mk.setdefault(int(round(t * fps)), ("Red", "Phrase"))
    for h in H.get("hits") or []:
        if h.get("priority") == "must":
            mk[int(round(float(h["t"]) * fps))] = ("Green", f"Hit {h['id']} {h['want']}")
    for n in b.get("nudges") or []:
        mk.setdefault(int(round(float(n["cut_at"]) * fps)) + 0, ("Yellow", f"Nudge {n['hit']} {n['move_frames']:+d}f"))
    return [(f, c, n) for f, (c, n) in sorted(mk.items()) if f >= 0]


def console_copy(job: str, F: dict, M: dict, H: dict, RB: dict | None = None) -> str:
    """07-edit/resolve-production-console.music.py: the ORIGINAL track on A5 — its segments when the speed is ×1.0,
    whole when there is a speed change — the sparse markers and a marker per seam and over the end fade. Never a
    render: a render is a preview (2026-11-05)."""
    RB = RB or current_rebuild(job)
    src = open(CONSOLE, encoding="utf-8").read()
    mf = console_music_fit(job, RB)
    mk = merge_markers(sparse_markers(job, F, M, H), rebuild_markers(RB))
    pairs = [("MUSIC_FIT = {}  # __MUSIC_FIT__", "MUSIC_FIT = " + repr(mf) + "  # __MUSIC_FIT__"),
             ("\nPLACE_MUSIC_FIT = False", "\nPLACE_MUSIC_FIT = True"),
             ("MARKERS = []  # __DETECT_BEATS_MARKERS__", "MARKERS = " + repr(mk) + "  # __DETECT_BEATS_MARKERS__"),
             ("\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False")]
    for old, new in pairs:
        if old not in src:
            raise RuntimeError(f"resolve-production-console.py no longer contains {old!r} — update music_fit.console_copy()")
        src = src.replace(old, new, 1)
    head = ("Filled in by music_fit.py rebuild: the ORIGINAL track's segments on A5; crossfades and fades in Fairlight "
            "by computer control (REBUILD.md)")
    if not RB.get("placed_by_script"):
        head += (f".\nSpeed ×{RB['ratio']:.4f}: the original is placed WHOLE — retime it with the pitch kept, then cut "
                 f"the segments (REBUILD.md)")
    src = src.replace('"""\nDaVinci Resolve — the ONE production/editing-setup console script',
                      f'"""\n{head}.\n({RB.get("made")})\n\nDaVinci Resolve — the ONE production/editing-setup console script', 1)
    out = os.path.join(job, "07-edit", MUSIC_COPY)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(src)
    return out


# ── stems and the arrangement (package D) ───────────────────────────────────────────────────────────────
def find_stems(track_abs: str) -> dict:
    """The library's own stems beside the track: `<name>_drums.wav`, `<name> - Bass.wav`, or a `<name> stems/`
    folder. Roles: drums, bass, vocals, other (everything else sums into other)."""
    d, stem = os.path.dirname(track_abs), os.path.splitext(os.path.basename(track_abs))[0]
    pool = glob.glob(os.path.join(d, stem + "*")) + glob.glob(os.path.join(d, stem + "*stem*", "*")) + \
        glob.glob(os.path.join(d, "stems", stem + "*"))
    out = {}
    for p in pool:
        if p == track_abs or not os.path.isfile(p) or not p.lower().endswith((".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a")):
            continue
        n = os.path.basename(p).lower()
        for role, keys in STEM_ROLES.items():
            if any(k in n[len(stem.lower()):] for k in keys):
                out.setdefault(role, []).append(p)
                break
    return out


def stems(job: str, engine: str = "auto") -> dict:
    H = load_hits(job)
    ta = absj(job, (H.get("track") or {}).get("file") or "")
    if not os.path.isfile(ta):
        raise SystemExit("the hit list names no track that exists")
    stem = os.path.splitext(os.path.basename(ta))[0]
    od = os.path.join(job, "06-music", "stems", stem)
    os.makedirs(od, exist_ok=True)
    found = find_stems(ta) if engine in ("auto", "library") else {}
    rec = {"track": rel(job, ta), "source": None, "stems": {}}
    if found:
        rec["source"] = "library"
        for role, ps in found.items():
            rec["stems"][role] = [rel(job, p) if p.startswith(os.path.abspath(job)) else p for p in ps]
    else:
        try:
            import demucs  # noqa: F401  MIT, archived — pip install demucs (+ PyTorch)
        except Exception:                                   # noqa: BLE001
            raise SystemExit("no library stems beside the track, and Demucs is not installed — `pip install demucs` "
                             "(and PyTorch; ~1.5× the track's length on a CPU), or ask the library for its stems")
        subprocess.run([sys.executable, "-m", "demucs", "-n", "htdemucs", "-o", od, ta], check=True, stdin=subprocess.DEVNULL)
        base = os.path.join(od, "htdemucs", stem)
        rec["source"] = "demucs htdemucs"
        for role in ("drums", "bass", "vocals", "other"):
            p = os.path.join(base, role + ".wav")
            if os.path.isfile(p):
                rec["stems"][role] = [rel(job, p)]
    rec["made"] = dt.datetime.now().isoformat(timespec="minutes")
    json.dump(rec, open(os.path.join(od, "STEMS.json"), "w", encoding="utf-8"), indent=1)
    H.setdefault("track", {})["stems"] = rec["source"]
    json.dump(H, open(os.path.join(job, HITS), "w", encoding="utf-8"), indent=1)
    return rec


LEVELS = {"low": {"drums": -96.0, "bass": -6.0, "other": 0.0, "vocals": 0.0},
          "mid": {"drums": -6.0, "bass": 0.0, "other": 0.0, "vocals": 0.0},
          "high": {"drums": 0.0, "bass": 0.0, "other": 0.0, "vocals": 0.0}}


def arrange(job: str) -> dict:
    """The stems mixed on bar lines to the storyboard's energy per section, with the declared stop-down and drop,
    the vocal stem muted under speech; rendered through the fitted plan → <track>.arranged.wav, a PREVIEW to listen
    to (2026-11-05). It becomes F["render"]; REBUILD.json/.md carry the arrangement for Fairlight."""
    np = _np()
    H = load_hits(job)
    F = json.load(open(os.path.join(job, FIT), encoding="utf-8"))
    b = F["plans"][F.get("picked", 0)]
    plan = Plan.from_dict(b["plan"])
    M = json.load(open(os.path.join(job, b["map"]), encoding="utf-8"))
    ta = absj(job, plan.track)
    stem = os.path.splitext(os.path.basename(ta))[0]
    sp = os.path.join(job, "06-music", "stems", stem, "STEMS.json")
    if not os.path.isfile(sp):
        raise SystemExit("no stems — `music_fit.py stems <job>` first")
    S = json.load(open(sp, encoding="utf-8"))
    beat = 60.0 / float(M["tempo"])
    tl_downs = plan.events(M["downbeats"])

    def snap(t):
        return min(tl_downs, key=lambda d: abs(d - t)) if tl_downs else t
    secs = sorted(H.get("sections") or [], key=lambda s: s.get("t0", 0))
    stop = [float(h["t"]) for h in H.get("hits") or [] if h.get("want") == "stop_down"]
    drops = [float(h["t"]) for h in H.get("hits") or [] if h.get("want") == "drop"]
    speech = H.get("speech") or []
    mixes = {}
    for role, files in S["stems"].items():
        acc = None
        for f in files:
            x = decode(absj(job, f), SR_OUT, 2)
            acc = x if acc is None else (acc[:min(len(acc), len(x))] + x[:min(len(acc), len(x))])
        mixes[role] = assemble(acc, SR_OUT, plan, M)
    n = max(len(v) for v in mixes.values())
    out = np.zeros((n, 2), dtype=np.float32)
    at = lambda T: max(0, int((T - plan.start) * plan.ratio * SR_OUT))   # timeline time → the unstretched bed
    ramp = int(0.03 * SR_OUT)
    for role, y in mixes.items():
        g = np.ones(n, dtype=np.float32)
        for s in secs:
            lv = LEVELS.get(str(s.get("energy") or "high"), LEVELS["high"]).get(role, 0.0)
            i0, i1 = at(snap(float(s.get("t0", 0)))), min(n, at(snap(float(s.get("t1", 1e9)))))
            g[i0:i1] = 10 ** (lv / 20.0)
        for t in stop:                                    # one beat of accented silence, ending on the hit
            i1 = at(snap(t))
            i0 = max(0, i1 - int(beat * plan.ratio * SR_OUT))
            g[i0:max(i0, i1)] = 0.0
        if role == "vocals":
            for a, z in speech:
                g[at(a):at(z)] = 0.0
        # 30 ms ramps at every change, so the bar-line moves do not click
        k = np.ones(ramp, dtype=np.float32) / ramp
        g = np.convolve(g, k, mode="same").astype(np.float32)
        yy = np.zeros((n, 2), dtype=np.float32)
        yy[:len(y)] = y[:n]
        out += yy * g[:, None]
    td = tempfile.mkdtemp(prefix="marr-")
    if abs(plan.ratio - 1.0) > 1e-6:
        out = decode(stretch_file(encode(out, SR_OUT, os.path.join(td, "a.wav")), os.path.join(td, "b.wav"), plan.ratio), SR_OUT, 2)
    lead = np.zeros((int(round(plan.start * SR_OUT)), 2), dtype=np.float32)
    out = np.concatenate([lead, out])
    ec = H.get("end_card") or {}
    end = float(H.get("duration") or ((ec.get("t") or 0) + (ec.get("dur") or 0)) or len(out) / SR_OUT)
    if len(out) > int(end * SR_OUT):
        out = out[:int(end * SR_OUT)].copy()
        f = min(int(END_FADE_S * SR_OUT), len(out))
        out[-f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]
    peak = float(np.abs(out).max()) or 1.0
    if peak > 0.98:
        out *= 0.98 / peak
    dst = os.path.join(job, "06-music", "fit", stem + ".arranged.wav")
    encode(out, SR_OUT, dst)
    json.dump({"kind": "music_arrangement_preview", "preview": True, "note": PREVIEW_NOTE,
               "sources": [{"file": plan.track, "role": "music"}] +
               [{"file": f, "role": "music stem"} for fs in S["stems"].values() for f in fs],
               "sections": secs, "stop_downs": stop, "drops": drops, "made": dt.datetime.now().isoformat(timespec="minutes")},
              open(dst + ".conform.json", "w", encoding="utf-8"), indent=1)
    F["render"] = {"file": rel(job, dst), "sha256": sha256_file(dst), "sr": SR_OUT, "arranged": True, "preview": True,
                   "note": PREVIEW_NOTE}
    json.dump(F, open(os.path.join(job, FIT), "w", encoding="utf-8"), indent=1)
    rebuild(job)
    shutil.rmtree(td, ignore_errors=True)
    return F


# ── the checks ──────────────────────────────────────────────────────────────────────────────────────────
def _hf(x):
    np = _np()
    m = x.mean(1) if x.ndim > 1 else x
    return m - np.convolve(m, np.ones(8) / 8, mode="same")          # a crude high-pass, above ~6 kHz at 48 kHz


def clicks(x, src, sr: int, plan: "Plan") -> list:
    """Joins whose splice point carries a high-frequency burst that neither side of the track has at that moment:
    a raw splice is broadband; the masked, crossfaded one is not (±1.5 ms around the splice, ratio > 4)."""
    np = _np()
    hx, hs = _hf(x), _hf(src)
    w = int(0.001 * sr)

    def e(h, t):
        # the loudest 2 ms of the stretch between 14 ms and 2 ms before the downbeat: where the splice sits
        best = 0.0
        for c in np.arange(t - 0.014, t - 0.002, 0.001):
            i = int(c * sr)
            seg = h[max(0, i - w):i + w]
            if len(seg):
                best = max(best, float(np.mean(seg ** 2)))
        return best
    out, acc = [], 0.0
    for k in range(1, len(plan.segments)):
        acc += plan.segments[k - 1][1] - plan.segments[k - 1][0]
        T = plan.start + acc / plan.ratio
        ref = max(e(hs, plan.segments[k - 1][1]), e(hs, plan.segments[k][0]))
        if e(hx, T) > 4.0 * ref + 1e-7:
            out.append(round(T, 3))
    return out


def clicks_at(x, src, sr: int, joins: list) -> list:
    """clicks() for a rebuild Resolve made: each join is (the splice on the timeline, the source time the outgoing
    segment leaves at, the source time the incoming one enters at), in seconds — the splices sit on whole frames, so
    the energy is read ±4 ms around the splice itself rather than just before the downbeat."""
    np = _np()
    hx, hs = _hf(x), _hf(src)
    w = int(0.001 * sr)

    def e(h, t):
        best = 0.0
        for c in np.arange(t - 0.004, t + 0.004, 0.001):
            i = int(c * sr)
            seg = h[max(0, i - w):i + w]
            if len(seg):
                best = max(best, float(np.mean(seg ** 2)))
        return best
    return [round(T, 3) for T, a, b in joins if e(hx, T) > 4.0 * max(e(hs, a), e(hs, b)) + 1e-7]


def rebuild_joins(RB: dict | None) -> list | None:
    """The splices of a rebuild the script placed (×1.0), for clicks_at; None when there is none to read."""
    if not RB or not RB.get("placed_by_script"):
        return None
    fps = float(RB.get("fps") or 24)
    sg = RB.get("segments") or []
    return [(sg[k]["record_f"] / fps, sg[k - 1]["src_out_f"] / fps, sg[k]["src_in_f"] / fps) for k in range(1, len(sg))]


def resolve_stem(job: str) -> dict | None:
    """The music as Resolve made it, for the measures — {file, abs, kind: music|bed}. First the stems mix_qa.py's
    newest report records (10-export/<render>.mix.json `stems`, from `measure --music` and `--bed`): the music stem,
    else the bed, under 09-qa/mix/. Else a file in 09-qa/mix/ named as the skill names them: the music stem
    `<slug>_stem-m_…` (pm-workflow.md, name_lint.py), the bed `<slug>_qc-bed.wav` (editing-and-audio.md §7b) or
    `<x>_bed.wav` (mix_qa.py). A Python preview is never measured as what Resolve made."""
    found = []
    for rp in sorted(glob.glob(os.path.join(job, "10-export", "*.mix.json")), key=os.path.getmtime, reverse=True):
        try:
            st = json.load(open(rp, encoding="utf-8")).get("stems") or {}
        except (ValueError, OSError, AttributeError):
            continue
        for kind in ("music", "bed"):
            f = str((st.get(kind) or {}).get("file") or "").replace("\\", "/")
            if f.startswith("09-qa/mix/") and os.path.isfile(absj(job, f)) and not is_preview(f):
                found.append((kind, f))
        if found:
            break
    if not found:
        mixd = os.path.join(job, "09-qa", "mix")
        for pat, kind in (("*_stem-m_*.wav", "music"), ("*_stem-m.wav", "music"), ("*_qc-bed.wav", "bed"), ("*_bed.wav", "bed")):
            for p in sorted(glob.glob(os.path.join(mixd, pat)), key=os.path.getmtime, reverse=True):
                if not is_preview(p):
                    found.append((kind, rel(job, p)))
    if not found:
        return None
    kind, f = sorted(found, key=lambda c: 0 if c[0] == "music" else 1)[0]
    rb = os.path.join(job, REBUILD)
    older = os.path.isfile(rb) and os.path.getmtime(absj(job, f)) < os.path.getmtime(rb)
    return {"file": f, "abs": absj(job, f), "kind": kind, "older_than_rebuild": bool(older)}


STEM_WANTED = ("no music stem exported from Resolve under 09-qa/mix/ — render A5–A6 only, the ducking on, at 48 kHz, "
               "and pass it to `mix_qa.py measure` as --music (or the bed, the mix with the dialogue muted, as --bed); "
               "07-edit/music/REBUILD.md, the last step")


def timeline_audio(job: str, H: dict, tracks: list) -> tuple[list, list]:
    """From 07-edit/timeline-dump.json, when there is one: a preview render on any audio track refuses; the original
    track on none of them warns."""
    d = _timeline(job)
    if not d:
        # (v2.50, the review) without a dump nothing confirms the music was rebuilt in Resolve — said loudly
        return [], ["no 07-edit/timeline-dump.json — nothing confirms the music was rebuilt in Resolve or that no "
                     "preview is on the timeline: run the console with DUMP_TIMELINE_JSON = True and write the dump"]
    P, W = [], []
    names = {os.path.basename(str(t).replace("\\", "/")) for t in tracks if t}
    prev, on = [], False
    for tn, items in (d.get("tracks") or {}).items():
        if not str(tn).startswith("audio"):
            continue
        for it in items or []:
            f, nm = str(it.get("file") or ""), str(it.get("name") or "")
            if is_preview(f) or is_preview(nm):
                prev.append(f"{f or nm} on {tn}")
            if os.path.basename(f.replace("\\", "/")) in names or nm in names:
                on = True
    if prev:
        P.append("a preview render is on the timeline — rebuild it in Resolve from the original (" + "; ".join(prev) +
                 "): a Python render is a preview, never the deliverable; take it off by hand and "
                 "follow 07-edit/music/REBUILD.md")
    if names and not on:
        W.append(f"the original track ({', '.join(sorted(names))}) is on no audio track of 07-edit/timeline-dump.json — "
                 f"place it (07-edit/{MUSIC_COPY}, `music_fit.py rebuild`) and dump the timeline again")
    return P, W


def stems_on_timeline(job: str) -> bool | None:
    """(v2.50, the review) True when the timeline dump shows the track's stems (06-music/stems/) on an audio track —
    the arrangement rebuilt in Resolve. None with no dump."""
    d = _timeline(job)
    if not d:
        return None
    for tn, items in (d.get("tracks") or {}).items():
        if str(tn).startswith("audio"):
            for it in items or []:
                f = str(it.get("file") or "").replace("\\", "/")
                if "06-music/stems/" in f and not is_preview(f):
                    return True
    return False


ARRANGED_ONLY_IN_PREVIEW = ("sung lyrics under speech — the arrangement that mutes the vocal stem exists only in the "
                            "Python preview, and the original on A5 still has the vocals. Rebuild it in Fairlight from "
                            "the stems (07-edit/music/REBUILD.md) and dump the timeline: the check reads the stems on an "
                            "audio track as the evidence")


def accent_budget(job: str, H: dict) -> list:
    """A11: risers, impacts, sub drops, scratches and whooshes counted together with sfx_conform's plan."""
    W = []
    fps = float(H.get("fps") or 24)
    fx = [f for f in H.get("fx") or [] if f.get("kind") in FX_KINDS]
    for p in glob.glob(os.path.join(job, "09-qa", "sfx", "*.joins-sound.json")):
        try:
            for j in json.load(open(p, encoding="utf-8")).get("joins") or []:
                if "whoosh" in json.dumps(j).lower():
                    fx.append({"kind": "whoosh", "t": float(j.get("t") or j.get("cut") or 0)})
        except (ValueError, TypeError):
            continue
    n = {k: sum(1 for f in fx if f["kind"] == k) for k in FX_KINDS}
    if n["riser"] > 3:
        W.append(f"{n['riser']} risers — 2–3 per ad (the direct-response sound map, practitioner)")
    if n["scratch"] > 1:
        W.append(f"{n['scratch']} record scratches or hard stops — at most once")
    musts = [float(h["t"]) for h in H.get("hits") or [] if h.get("priority") == "must"]
    for f in fx:
        if f["kind"] == "riser":
            end = float(f.get("t", 0)) + float(f.get("dur") or 0)
            if not any(-0.001 <= end - m <= frame_s(fps) + 0.001 for m in musts):
                W.append(f"a riser ending at {end:.3f} s lands on no must-hit — it ends exactly on the reveal, the offer "
                         f"or the end card")
            for w in fx:
                if w["kind"] == "whoosh" and abs(float(w.get("t", 0)) - end) <= 2 * frame_s(fps):
                    W.append(f"a whoosh within 2 frames of the riser ending at {end:.3f} s — one accent per moment")
    lows = [f for f in fx if f["kind"] in ("impact", "sub_drop")]
    for i, a in enumerate(lows):
        for c in lows[i + 1:]:
            if abs(float(a.get("t", 0)) - float(c.get("t", 0))) <= 2 * frame_s(fps):
                W.append(f"an impact and a sub drop together at {float(a.get('t', 0)):.3f} s — one owner of the low end per hit")
    return W


def punctuation(H: dict) -> list:
    """C3: by default 1 stop-down and 1 drop per ad, the drop never in act one; long brand or drama pieces may take
    2 stop-downs. Warnings, all untested."""
    W = []
    dur = float(H.get("duration") or 0) or None
    sd = [h for h in H.get("hits") or [] if h.get("want") == "stop_down"]
    dr = [h for h in H.get("hits") or [] if h.get("want") == "drop"]
    cap = 2 if (H.get("lane") in ("brand", "drama") and (dur or 0) > 45) else 1
    if len(sd) > cap:
        W.append(f"{len(sd)} stop-downs — {cap} by default here; punctuation stops working when it repeats (untested)")
    if len(dr) > 1:
        W.append(f"{len(dr)} drops — one payoff")
    if dur:
        for h in dr:
            if float(h["t"]) < dur / 3:
                W.append(f"the drop at {float(h['t']):.2f} s is in the first act — the drop is the payoff (M14)")
    return W


def _music_led(job: str) -> tuple:
    """(v2.48.0, project switch music-led) (the lifted() wording when the job's CHECKPOINT lifts `music-led`, else None;
    a note when the switches cannot be read — then nothing is lifted and every house rule holds)."""
    try:
        import switches  # (stdlib-only) the one parser gate.py and every script read the `Switches:` line with
        why = switches.on(job, "music-led")
        return (switches.lifted("music-led", why) if why else None), None
    except Exception as e:                                  # noqa: BLE001  a broken registry lifts nothing
        return None, f"the project switches could not be read ({e}) — nothing is lifted, every house rule holds"


def check_job(job: str) -> tuple[list, list]:
    """(problems that refuse export, notes). C5: rules refuse, measures warn. Stdlib-only until there is a
    stem from Resolve to measure, so `approve export` on a film with no music bed needs no numpy.
    (2026-11-05, the render is a preview) No render is asked for, nor its sha256: a current REBUILD.json is (its
    plan_sha and the original's sha256), a preview on the timeline refuses, and the measures run on the music stem
    Resolve made (resolve_stem), with a note naming what to export when there is none.
    (v2.48.0, project switch music-led) A job whose CHECKPOINT lifts `music-led` is checked by _check_music_led
    instead, after the hit list: the song is the deliverable and the picture is cut to it. With the switch off,
    every line below runs exactly as in 2.47.0."""
    P, W = [], []
    led, sw_note = _music_led(job)                          # (v2.48.0, project switch music-led)
    if sw_note:
        W.append(sw_note)
    hp = os.path.join(job, HITS)
    if not os.path.isfile(hp):
        if led:                                             # (v2.48.0, project switch music-led) the song is still declared
            return [f"no music plan — `music_fit.py hits init <job>`, then declare the client's song in {HITS} "
                    f"(track.file, vocals, edits_allowed); the job is music-led, so there is no fit to make ({led})"], W
        return [f"no music plan — `music_fit.py hits init <job>` and `fit` (or set \"music\": \"none\" in {HITS} for a "
                f"film with no music bed)"], W
    try:
        H = json.load(open(hp, encoding="utf-8"))
    except ValueError:
        return [f"{HITS} is not valid JSON"], W
    if H.get("music") == "none":
        if led:                                             # (v2.48.0, project switch music-led) (c) a contradiction
            return [f"{HITS} says music: none, and the job is music-led — the song is the deliverable ('fit the track to "
                    f"the cut' is {led}), so a film with no music bed is a contradiction. Declare the client's song in "
                    f"{HITS} (track.file, vocals, edits_allowed), or take `music-led` off the `Switches:` line in "
                    f"00-brief/CHECKPOINT.md"], W
        return P, W + ["no music bed in this film (HITS.json music: none)"]
    p_, w_ = hits_problems(H)
    P += p_
    W += w_
    if led:                                                 # (v2.48.0, project switch music-led)
        return _check_music_led(job, H, P, W, led)
    fp = os.path.join(job, FIT)
    if not os.path.isfile(fp):
        return P + ["no fit — `music_fit.py fit <job>`, pick a plan, then `rebuild`"], W
    F = json.load(open(fp, encoding="utf-8"))
    b = F["plans"][F.get("picked", 0)]
    plan = Plan.from_dict(b["plan"])
    rnd = F.get("render") or {}                             # a preview: read for its `arranged` flag only (2026-11-05)
    # the deliverable is rebuilt in Resolve from the original: REBUILD.json must describe the picked plan
    RB, why = rebuild_state(job, F)
    if why == "missing":
        P.append("the music is not prepared for the Resolve rebuild — `music_fit.py rebuild <job>`")
    elif why:
        P.append(f"{REBUILD} is stale ({why}) — `music_fit.py rebuild <job>`, then place the music again from the new "
                 f"console copy")
    fps = float(F.get("fps") or H.get("fps") or 24)
    # the cut never moves by itself
    _, cuts_now, _, _ = cuts_of(job)
    then = F.get("cuts_at_fit") or []
    if cuts_now and then:
        if abs(len(cuts_now) - len(then)) > 0:
            P.append(f"the cut changed since the fit ({len(then)} cuts then, {len(cuts_now)} now) — fit again (stale)")
        else:
            ok_n = {(n.get("hit"), int(n.get("frames", 0))) for n in H.get("approved_nudges") or []}
            ids = {round(float(h["t"]), 3): h["id"] for h in H.get("hits") or [] if h.get("cut")}
            for a, c in zip(then, cuts_now):
                k = int(round((c - a) * fps))
                if k:
                    hid = ids.get(round(a, 3))
                    if (hid, k) not in ok_n:
                        P.append(f"the cut at {a:.3f} s moved {k:+d} frame(s) since the fit, with no approved nudge — the cut "
                                 f"never moves by itself; record the approval in approved_nudges or fit again")
    # the stretch cap and vocals (C2)
    if abs(plan.ratio - 1.0) > STRETCH_CAP + 1e-9:
        P.append(f"a stretch of {100 * (plan.ratio - 1):+.2f} % — at most ±2 %")
    elif abs(plan.ratio - 1.0) > STRETCH_WARN:
        W.append(f"a stretch of {100 * (plan.ratio - 1):+.2f} % — over 1.5 %: listen for it")
    tr = H.get("track") or {}
    if abs(plan.ratio - 1.0) > 1e-6 and tr.get("vocals") == "lyrics":
        P.append("a stretch on a track with sung vocals")
    # the licence travels with every edit (A15)
    edited = bool(plan.edits) or abs(plan.ratio - 1.0) > 1e-6 or (rnd.get("arranged") is True)
    if edited and tr.get("edits_allowed") != "yes":
        P.append(f"the track is edited ({', '.join(e['kind'] for e in plan.edits) or 'arranged'}) and its licence is not "
                 f"recorded as allowing it — set track.edits_allowed to yes once the licence says so (or no, and use the "
                 f"track whole)")
    # sung lyrics under speech (A12)
    sp = H.get("speech") or []
    if sp and tr.get("vocals") == "lyrics" and not rnd.get("arranged"):
        P.append("sung lyrics under speech — use the instrumental or underscore mix, or mute the vocal stem (`stems`, "
                 "`arrange`): meaningful lyrics cost speech intelligibility (Brouwer et al.)")
    elif sp and tr.get("vocals") == "lyrics" and not stems_on_timeline(job):
        P.append(ARRANGED_ONLY_IN_PREVIEW)
    elif sp and tr.get("vocals") == "unknown":
        W.append("track.vocals is unknown and the film has speech — declare it (none, lyrics, vocal_chops)")
    # (2026-11-05) what is on the timeline: never a preview; the original somewhere on it
    p_, w_ = timeline_audio(job, H, [plan.track, tr.get("file")])
    P += p_
    W += w_
    # (v2.48.0, project switch music-led) the measures moved, unchanged, into _render_measures so a music-led job's
    # render is measured by the same lines; (2026-11-05) they now read what Resolve made, never the preview
    stem = resolve_stem(job)
    if not stem:
        W.append(f"the music is not measured — {STEM_WANTED}")
    elif stem.get("older_than_rebuild"):
        W.append(f"{stem['file']} is older than {REBUILD} — it was exported before the last rebuild; export it again "
                 f"from Resolve before reading its measures")
    joins = rebuild_joins(RB) if RB and not why else None
    return _render_measures(job, H, b, plan, {"file": stem["file"]} if stem else {}, stem["abs"] if stem else "", fps,
                            cuts_now, P, W, joins=joins, strict=bool(stem) and stem["kind"] == "music")


def _render_measures(job: str, H: dict, b: dict, plan: "Plan", rnd: dict, rf: str, fps: float, cuts_now: list,
                     P: list, W: list, joins: list | None = None, strict: bool = True) -> tuple[list, list]:
    """The measures (the tail of check_job as it was in 2.47.0, moved here unchanged in v2.48.0, project switch
    music-led, so the music-led check measures with the same lines). (2026-11-05) `rf` is the music as Resolve made it
    (resolve_stem) and `rnd` names it; with no `rf` the lines that need audio are skipped and the plan's notes still
    print. `joins` are the rebuild's splices (rebuild_joins) — read there, not at the plan's. `strict` False (the bed,
    which carries other sounds too): a click is a note to listen, not a refusal."""
    if rf:
        np = _np()
        try:
            x = decode(rf, SR_OUT, 2)
        except Exception as e:                              # noqa: BLE001
            return P + [f"{rnd.get('file')} does not decode ({e})"], W
        sr_probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                                   "stream=sample_rate", "-of", "csv=p=0", rf], capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL).stdout.strip()
        if sr_probe and sr_probe != str(SR_OUT):
            P.append(f"{rnd['file']} is {sr_probe} Hz — 48 kHz")
        try:
            src = decode(absj(job, plan.track), SR_OUT, 2)
            if abs(plan.ratio - 1.0) >= 1e-6:
                bad = []
            elif joins is not None:
                bad = clicks_at(x, src, SR_OUT, joins)
            else:
                bad = clicks(x, src, SR_OUT, plan)
        except Exception:                                   # noqa: BLE001
            bad = []
            W.append("the track itself could not be read back — the joins were not checked for clicks")
        if bad:
            msg = (f"a click at the music edit(s) at {', '.join(f'{t:.3f} s' for t in bad)} in {rnd.get('file')} — re-cut "
                   f"the join before the transient, or with a longer equal-power crossfade, in Fairlight")
            if strict:
                P.append(msg)
            else:
                W.append(msg + " (measured on the bed, which carries other sounds: listen, or export the music stem)")
        mono = x.mean(1)
        t, env, _, _, _ = spectral(np.ascontiguousarray(mono[::2]), SR_OUT // 2)
        pk = [i for i in range(1, len(env) - 1) if env[i] >= env[i - 1] and env[i] > env[i + 1]]
        thr = float(np.percentile(env, 85)) if len(env) else 0
        peaks = [float(t[i]) for i in pk if env[i] >= thr]
        for r in b.get("hits") or []:
            if r.get("priority") != "must" and r.get("tier") != "soft":
                continue
            planned = r.get("residual_ms")
            if planned is None:
                W.append(f"hit {r['id']}: no music event near it")
                continue
            exp = float(r["t"]) + planned / 1000.0
            near = min(peaks, key=lambda q: abs(q - exp)) if peaks else None
            meas = (near - float(r["t"])) if near is not None and abs(near - exp) < 0.05 else planned / 1000.0
            tr_ = r.get("tier") or ("hard" if r.get("priority") == "must" else "soft")
            cls = classify(meas, fps, tr_)
            if cls != "on":
                W.append(f"hit {r['id']} ({r['want']}, {tr_}): the impact lands {1000 * meas:+.0f} ms from the picture ({cls}; "
                         f"the window is 0 to +{1 if tr_ == 'hard' else 2} frame(s), "
                         f"{1000 * (1 if tr_ == 'hard' else 2) / fps:.0f} ms at {fps:g} fps, never early)")
    e = b.get("ending") or {}
    if e.get("kind") != "hit":
        W.append("the track ends on a fade, not a hit — the end card has no button (a plain fade, as the fallback)")
    # stop-down depth, measured
    if rf:
        beat = 60.0 / float(b.get("tempo") or 120)
        lvl = lambda a, z: 20 * math.log10(float(np.sqrt(np.mean(mono[max(0, int(a * SR_OUT)):max(int(a * SR_OUT) + 1, int(z * SR_OUT))] ** 2))) + 1e-9)
        for h in H.get("hits") or []:
            if h.get("want") == "stop_down":
                T = float(h["t"])
                inside, around = lvl(T - beat * 0.9, T - beat * 0.1), lvl(T - 3 * beat, T - 1.2 * beat)
                if around - inside < STOPDOWN_DB:
                    W.append(f"the stop-down before {h['id']} is only {around - inside:.0f} dB under the bars before it — "
                             f"{STOPDOWN_DB:.0f} dB reads as silence (untested)")
    W += punctuation(H) + accent_budget(job, H)
    # combining two tracks (A10): key advisory, tempo inside the cap
    cb = H.get("combine")
    if cb:
        W.append("two tracks are joined — the owner listens to the join (key relation advisory)")
    # the share of cuts on a beat, as information
    mp_ = os.path.join(job, b["map"]) if b.get("map") else ""
    tl_beats = plan.events(json.load(open(mp_, encoding="utf-8"))["beats"]) if mp_ and os.path.isfile(mp_) else []
    if cuts_now and tl_beats:
        on = sum(1 for c in cuts_now if min(abs(c - q) for q in tl_beats) <= 0.08)
        W.append(f"{on}/{len(cuts_now)} cuts sit on a beat ({100 * on / len(cuts_now):.0f} %; real ads: 31 %, chance 32 % — "
                 f"information only)")
    return P, W


def _check_music_led(job: str, H: dict, P: list, W: list, lift: str) -> tuple[list, list]:
    """(v2.48.0, project switch music-led) The export check for a job that lifts 'fit the track to the cut, never the cut
    to the track': the song is fixed and is the deliverable, and the picture is cut to it.
    Lifted, and printed as lifted: a fit plan, its render, a fit gone stale against the cut, a cut moved without an
    approved nudge — there is no fit to keep in step with the cut.
    Still refused: (a) the song stretched at all, any ratio but 1.0, in the fit's picked plan or in a fit render's record
    (the song is the client's: its speed is not what this switch lifts); (b) an edit of the song — whole bars, an
    arrangement, a bed seam — whose licence is not recorded as allowing it; sung lyrics under speech (A12, not lifted);
    the song HITS.json names not on disk. `music: none` and no HITS.json refuse before this (check_job).
    (2026-11-05, the render is a preview) A fit render is read only for its record (a stretch, an arrangement); a
    preview on the timeline refuses here too; what Resolve made is measured with the same lines (_render_measures)."""
    W = [f"the music is not fitted to the cut — the song is fixed and the picture is cut to it, so no fit plan, no render "
         f"of one, no stale-fit and no moved-cut check is asked for ({lift})"] + W
    tr = H.get("track") or {}
    if tr.get("file") and not os.path.isfile(absj(job, tr["file"])):
        P.append(f"the song {HITS} names ({tr['file']}) is not on disk — in a music-led job the song is the deliverable: "
                 f"put the client's file where track.file says")
    F, b, plan, rnd, rf = None, {}, None, {}, ""
    fp = os.path.join(job, FIT)
    if os.path.isfile(fp):
        try:
            F = json.load(open(fp, encoding="utf-8"))
            b = F["plans"][F.get("picked", 0)]
            plan = Plan.from_dict(b["plan"])
        except (ValueError, KeyError, IndexError, TypeError) as e:
            return P + [f"{FIT} cannot be read ({e}) — a music-led job needs no fit: remove it, or fit again"], W
        rnd = F.get("render") or {}
        rf = absj(job, rnd.get("file") or "")
    # the fit renders and arrangements on disk, by their records (a render the FIT no longer names still exists)
    on_disk, arranged_files = [], []
    for cj in sorted(glob.glob(os.path.join(job, "06-music", "fit", "*.conform.json"))):
        try:
            c = json.load(open(cj, encoding="utf-8"))
        except ValueError:
            continue
        f_ = rel(job, cj[:-len(".conform.json")])
        if c.get("kind") in ("music_fit", "music_fit_preview"):           # (2026-11-05) previews now; the old name too
            on_disk.append((f_, float((c.get("plan") or {}).get("ratio") or 1.0)))
        elif c.get("kind") in ("music_arrangement", "music_arrangement_preview"):
            arranged_files.append(f_)
    # (a) the song plays at its own speed — not even inside the ±2 % a fitted track may take
    stretched = []
    if plan is not None and abs(plan.ratio - 1.0) > 1e-6:
        stretched.append((f"{FIT}, the picked plan", plan.ratio))
    for f_, r_ in on_disk:
        if abs(r_ - 1.0) > 1e-6 and not (plan is not None and f_ == rnd.get("file") and abs(r_ - plan.ratio) < 1e-9):
            stretched.append((f_, r_))
    if stretched:
        P.append("the song is stretched (" + "; ".join(f"{w_} ×{r_:.4f}, {100 * (r_ - 1):+.2f} %" for w_, r_ in stretched)
                 + ") — in a music-led job the song is the client's and is the deliverable, so it plays at its own speed: "
                 "no stretch at all, not even inside the ±2 % cap a fitted track gets. `music-led` cuts the picture to the "
                 "song, never the song to the picture; a change to the song's speed needs its licence to allow it and the "
                 "brief to ask for it. Play it at ×1.0 (fit again without a stretch, or remove the fit and its render)")
    # (b) the licence travels with every edit of the song (A15), as it does with a fitted track
    kinds = [str(e.get("kind") or "edit") for e in (plan.edits if plan is not None else [])]
    if stretched:
        kinds.append("stretched")
    if rnd.get("arranged") is True or arranged_files:
        kinds.append("arranged")
    bp = os.path.join(job, "06-music", "bed", "BED.json")
    if os.path.isfile(bp):
        try:
            B = json.load(open(bp, encoding="utf-8"))
        except ValueError:
            B = {}
        if not B.get("fitted") and B.get("removed_s"):
            kinds.append(f"a bar seam in the bed, {B['removed_s']} s taken out")
        elif not B.get("fitted") and B.get("seam"):
            kinds.append("the bed's head cut to length")
    if kinds and tr.get("edits_allowed") != "yes":
        P.append(f"the song is edited ({', '.join(kinds)}) and its licence is not recorded as allowing it — set "
                 f"track.edits_allowed to yes once the licence says so (or no, and use the song whole)")
    # sung lyrics under speech (A12) — not what the switch lifts
    sp = H.get("speech") or []
    if sp and tr.get("vocals") == "lyrics" and not rnd.get("arranged"):
        P.append("sung lyrics under speech — use the instrumental or underscore mix, or mute the vocal stem (`stems`, "
                 "`arrange`): meaningful lyrics cost speech intelligibility (Brouwer et al.)")
    elif sp and tr.get("vocals") == "lyrics" and not stems_on_timeline(job):
        P.append(ARRANGED_ONLY_IN_PREVIEW)
    elif sp and tr.get("vocals") == "unknown":
        W.append("track.vocals is unknown and the film has speech — declare it (none, lyrics, vocal_chops)")
    # (2026-11-05) the song on the timeline, and never a preview render (not what the switch lifts)
    p_, w_ = timeline_audio(job, H, [tr.get("file"), plan.track if plan is not None else None])
    P += p_
    W += w_
    if F is None:
        return P, W
    # (2026-11-05) a render is a preview: it is not asked for, not checked against its bytes and not measured; what
    # Resolve made is measured when it is there
    stem = resolve_stem(job)
    if not stem:
        W.append(f"the music is not measured — not asked for here ({lift}): {STEM_WANTED}; the picked plan in {FIT} was "
                 f"read for a stretch and edits")
        return P, W
    fps = float(F.get("fps") or H.get("fps") or 24)
    _, cuts_now, _, _ = cuts_of(job)
    RB, why = rebuild_state(job, F)
    return _render_measures(job, H, b, plan, {"file": stem["file"]}, stem["abs"], fps, cuts_now, P, W,
                            joins=rebuild_joins(RB) if RB and not why else None, strict=stem["kind"] == "music")


# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────
def synth_track(path: str, bpm: float = 120.0, bars: int = 18, lead: float = 0.25, sr: int = 44100,
                ending: str = "hit", vocals_bars: tuple = (), stems_dir: str | None = None, pitch: float = 220.0):
    """A test track: a kick on every downbeat, a softer kick on beat 3, hats on every beat, a pad that changes
    chord every phrase, and a final hit with a ring-out (or a fade). Stems written beside it on request."""
    np = _np()
    beat = 60.0 / bpm
    n = int((lead + bars * 4 * beat + 4.0) * sr)
    t = np.arange(n) / sr
    drums = np.zeros(n, np.float32)
    bass = np.zeros(n, np.float32)
    pad = np.zeros(n, np.float32)
    vox = np.zeros(n, np.float32)
    rng = np.random.default_rng(3)

    def kick(at, amp):
        i = int(at * sr); L = int(0.25 * sr)
        if i + L > n:
            L = n - i
        tt = np.arange(L) / sr
        drums[i:i + L] += amp * np.sin(2 * np.pi * (55 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12)

    def hat(at, amp):
        i = int(at * sr); L = int(0.04 * sr)
        if i + L > n:
            return
        nz = rng.standard_normal(L).astype(np.float32)
        nz = np.diff(nz, prepend=0)
        drums[i:i + L] += amp * nz * np.exp(-np.arange(L) / sr * 120)
    chords = [1.0, 1.25, 1.5, 1.335]
    for b in range(bars):
        for k in range(4):
            at = lead + (b * 4 + k) * beat
            if k == 0:
                kick(at, 0.9)
            elif k == 2:
                kick(at, 0.35)
            hat(at, 0.08)
        f0 = pitch * chords[(b // 4) % 4]
        i0, i1 = int((lead + b * 4 * beat) * sr), int((lead + (b + 1) * 4 * beat) * sr)
        tt = t[i0:i1]
        pad[i0:i1] += 0.06 * (np.sin(2 * np.pi * f0 * tt) + np.sin(2 * np.pi * f0 * 1.5 * tt))
        bass[i0:i1] += 0.10 * np.sin(2 * np.pi * f0 / 2 * tt)
        if b in vocals_bars:
            vox[i0:i1] += 0.08 * np.sin(2 * np.pi * f0 * 2 * tt) * (0.6 + 0.4 * np.sin(2 * np.pi * 5 * tt))
    end_t = lead + bars * 4 * beat
    if ending == "hit":
        kick(end_t, 1.0)
        i = int(end_t * sr)
        L = min(n - i, int(3.0 * sr))
        tt = np.arange(L) / sr
        pad[i:i + L] += 0.12 * np.sin(2 * np.pi * pitch * tt) * np.exp(-tt * 1.5)
        drums[i:i + L] += 0.3 * rng.standard_normal(L).astype(np.float32) * np.exp(-tt * 4)
    else:
        g = np.clip((end_t - t) / (8 * beat), 0, 1)
        drums *= g; pad *= g; bass *= g; vox *= g
    mix = drums + bass + pad + vox
    stereo = np.stack([mix, mix], 1)
    encode(stereo, sr, path, "pcm_s16le")
    if stems_dir:
        stem = os.path.splitext(os.path.basename(path))[0]
        for role, y in (("drums", drums), ("bass", bass), ("other", pad), ("vocals", vox)):
            encode(np.stack([y, y], 1), sr, os.path.join(stems_dir, f"{stem}_{role}.wav"), "pcm_s16le")
    return {"beat": beat, "lead": lead, "end": end_t, "bars": bars}


# ⚡ THE BED (a supplement ad job, 2026-10-28). The values that worked there: bed short-term −20 LUFS before the ride, a 9 dB
# duck (60 ms attack, 350 ms release), a 3 dB carve at 1.5–4.5 kHz, an 8 dB ride range [measured on one job].
BED_LEAD_DB = 30.0           # the opening is "near silence" until the 400 ms level comes within this of the track's [assumed]
BED_DUCK_DB = 9.0
BED_ATTACK_S, BED_RELEASE_S = 0.06, 0.35
BED_CARVE_DB, BED_CARVE_HZ = 3.0, (1500.0, 4500.0)
BED_RIDE_DB = 8.0            # the ride moves a section at most ±8 dB toward the bed level
BED_XFADE_S = 0.03           # the seam's equal-power crossfade


def _rms_db(x, sr: int, win: float):
    np = _np()
    m = x if x.ndim == 1 else x.mean(axis=1)
    n = max(1, int(win * sr))
    c = np.concatenate([[0.0], np.cumsum(m.astype(np.float64) ** 2)])
    i = np.arange(len(m))
    lo = np.clip(i - n // 2, 0, len(m))
    hi = np.clip(i + n - n // 2, 0, len(m))
    p = (c[hi] - c[lo]) / np.maximum(1, hi - lo)
    return 10 * np.log10(p + 1e-12)


def _envelope(v, sr: int, thr_db: float, attack: float, release: float):
    """0..1: where the voice speaks, with the attack and release of a ducker."""
    np = _np()
    lv = _rms_db(v, sr, 0.05)
    on = (lv > thr_db).astype(np.float64)
    a = 1 - np.exp(-1.0 / max(1, attack * sr))
    r = 1 - np.exp(-1.0 / max(1, release * sr))
    out = np.empty_like(on)
    g = 0.0
    step = 64                                   # per-block, then held — fast enough for an envelope
    for i in range(0, len(on), step):
        tgt = on[i:i + step].max()
        k = a if tgt > g else r
        g = g + (1 - (1 - k) ** step) * (tgt - g)
        out[i:i + step] = g
    return out


def bed(job: str, track: str | None = None, voice: str | None = None, length: float | None = None,
        under_db: float | None = None) -> dict:
    np = _np()
    import mix_qa as MQ
    sr = SR_OUT
    F = json.load(open(os.path.join(job, FIT), encoding="utf-8")) if os.path.isfile(os.path.join(job, FIT)) else {}
    fitted = (F.get("render") or {}).get("file") if not track else None
    src = absj(job, fitted or track or (load_hits(job).get("track") or {}).get("file") or "")
    if not src or not os.path.isfile(src):
        raise SystemExit("error: no track — --track <file>, or a fitted preview (music_fit.py render)")
    x = decode(src, sr, 2)
    H = load_hits(job) if os.path.isfile(os.path.join(job, HITS)) else {}
    L = float(length or H.get("duration") or 0) or None
    rep = {"source": rel(job, src), "fitted": bool(fitted)}
    if not fitted:
        lv = _rms_db(x, sr, 0.4)
        top = float(np.percentile(lv, 95))
        idx = np.where(lv > top - BED_LEAD_DB)[0]
        src_in = max(0.0, (int(idx[0]) / sr - 0.05) if len(idx) else 0.0)
        M = map_track(src, job)
        end_t = float((M.get("ending") or {}).get("t") or len(x) / sr)
        end_t = min(len(x) / sr, end_t + 1.0)                      # keep the ring-out after the last hit
        rep.update(src_in_s=round(src_in, 3), src_end_s=round(end_t, 3))
        avail = end_t - src_in
        vlv = None
        if voice:                                   # a seam under speech is masked by it (a supplement ad job)
            vv = decode(absj(job, voice), sr, 1)
            vlv = _rms_db(vv, sr, 0.3)
            vthr = float(np.percentile(vlv, 90)) - 15.0
        if L and avail > L + 0.05:
            R = avail - L
            downs = [d for d in M["downbeats"] if src_in + 2.0 < d < end_t - 3.0]
            e = M.get("bar_energy_db") or []
            best = None
            for i, a in enumerate(downs):
                for b in downs[i + 1:]:
                    if b - a > R + 0.001:
                        break                               # remove at most what is too long …
                    resid = R - (b - a)                     # … and take the rest, under a bar, from the head
                    if resid > (60.0 / max(1.0, M.get("tempo") or 120)) * 4:
                        continue
                    ia = min(range(len(M["downbeats"])), key=lambda k: abs(M["downbeats"][k] - a))
                    ib = min(range(len(M["downbeats"])), key=lambda k: abs(M["downbeats"][k] - b))
                    sim = -abs(e[ia] - e[ib]) if ia < len(e) and ib < len(e) else 0.0
                    sc = sim - 2.0 * resid
                    if vlv is not None:
                        k_ = int((a - src_in - resid) * sr)
                        if 0 <= k_ < len(vlv) and vlv[k_] > vthr:
                            sc += 1.5                       # under the voice
                    if best is None or sc > best[0]:
                        best = (sc, a, b, resid)
            if best:
                _, a, b, resid = best
                src_in += resid                      # the leftover under a bar is taken from the head
                rep.update(seam_out_s=round(a, 3), seam_in_s=round(b, 3), removed_s=round(b - a, 3),
                           seam_video_s=round(a - src_in, 3), head_trim_extra_s=round(resid, 3))
                if vlv is not None:
                    k_ = int(rep["seam_video_s"] * sr)
                    rep["seam_under_speech"] = bool(0 <= k_ < len(vlv) and vlv[k_] > vthr)
                n_x = int(BED_XFADE_S * sr)
                A = x[int(src_in * sr): int(a * sr) + n_x]
                B = x[int(b * sr): int(end_t * sr)]
                w = np.sin(np.linspace(0, np.pi / 2, n_x))[:, None].astype(np.float32)
                y = np.concatenate([A[:-n_x], A[-n_x:] * w[::-1] + B[:n_x] * w, B[n_x:]])
            else:
                rep["seam"] = "none found on the bars — the head trimmed instead"
                y = x[int((end_t - L) * sr): int(end_t * sr)]
        else:
            y = x[int(src_in * sr): int(end_t * sr)]
            if L and len(y) < int(L * sr):
                rep["short_by_s"] = round(L - len(y) / sr, 3)
                y = np.concatenate([np.zeros((int(L * sr) - len(y), 2), np.float32), y])   # the ending stays on the last frame
    else:
        y = x
    if L:
        y = y[-int(L * sr):] if len(y) > int(L * sr) else y
    y = np.ascontiguousarray(y, dtype=np.float32)
    rep["length_s"] = round(len(y) / sr, 3)
    # ride the sections to one level
    st = _rms_db(y, sr, 3.0)
    target = float(np.median(st[st > np.percentile(st, 20)])) if len(st) else -20.0
    ride = np.clip(target - st, -BED_RIDE_DB, BED_RIDE_DB)
    k = max(1, int(1.0 * sr))
    cr = np.concatenate([[0.0], np.cumsum(ride)])
    ii = np.arange(len(ride))
    lo, hi = np.clip(ii - k // 2, 0, len(ride)), np.clip(ii + k - k // 2, 0, len(ride))
    ride = (cr[hi] - cr[lo]) / np.maximum(1, hi - lo)
    y = y * (10 ** (ride / 20))[:, None].astype(np.float32)
    rep["ride_range_db"] = round(float(ride.max() - ride.min()), 1)
    ca = MQ.client_audio(job)
    under = float(under_db if under_db is not None else ca.get("music_under_voice_db") or 16.0)
    rep.update(under_voice_db=under, under_source="--under-db" if under_db is not None else ca.get("_source"))
    if voice:
        v = decode(absj(job, voice), sr, 1)
        v = np.pad(v, (0, max(0, len(y) - len(v))))[: len(y)]
        V = MQ.ebur(np.repeat(v[:, None], 2, axis=1))
        act = MQ.active_windows(V)
        speech = MQ.energy_mean([V["M"][i] for i in act]) if act else V["I"]
        env = _envelope(v, sr, speech - 18.0, BED_ATTACK_S, BED_RELEASE_S)
        # the level: the bed while the voice speaks sits `under` dB below it, after the duck
        Bm = MQ.ebur(y)
        bed_speech = MQ.energy_mean([Bm["M"][i] for i in act if i < len(Bm["M"])]) if act else Bm["I"]
        g = (speech - under + BED_DUCK_DB) - bed_speech
        y = y * np.float32(10 ** (g / 20))
        y = y * (10 ** (-BED_DUCK_DB * env / 20))[:, None].astype(np.float32)
        # the carve: 1.5–4.5 kHz down while she speaks (STFT, 2048/512)
        n, hop = 2048, 512
        win = np.hanning(n).astype(np.float32)
        fr = np.fft.rfftfreq(n, 1 / sr)
        band = (fr >= BED_CARVE_HZ[0]) & (fr <= BED_CARVE_HZ[1])
        out = np.zeros_like(y)
        norm = np.zeros(len(y), np.float32)
        cut = 1 - 10 ** (-BED_CARVE_DB / 20)
        for c in range(2):
            ch = y[:, c]
            for i in range(0, len(ch) - n, hop):
                X = np.fft.rfft(ch[i:i + n] * win)
                X[band] *= 1 - cut * float(env[i + n // 2])
                out[i:i + n, c] += np.fft.irfft(X, n).astype(np.float32) * win
                if c == 0:
                    norm[i:i + n] += win ** 2
        y = out / np.maximum(norm, 1e-3)[:, None]
        Ba = MQ.ebur(y)
        bed_after = MQ.energy_mean([Ba["M"][i] for i in act if i < len(Ba["M"])]) if act else Ba["I"]
        rep.update(voice=voice, voice_speech_lufs=round(speech, 1), bed_under_voice_measured_db=round(speech - bed_after, 1),
                   duck_db=BED_DUCK_DB, duck_attack_ms=int(BED_ATTACK_S * 1000), duck_release_ms=int(BED_RELEASE_S * 1000),
                   carve_db=BED_CARVE_DB, carve_band_hz=list(BED_CARVE_HZ))
    else:
        rep["voice"] = None
        rep["note"] = "no --voice: not ducked, not carved, and not set against the voice — the ride only"
    pk = float(np.abs(y).max()) if len(y) else 0.0
    if pk > 0.89:
        y = y * np.float32(0.89 / pk)
        rep["peak_trim_db"] = round(20 * np.log10(0.89 / pk), 1)
    stem = os.path.splitext(os.path.basename(src))[0].replace(".fit", "")
    out = os.path.join(job, "06-music", "bed", stem + ".bed.wav")
    encode(y, sr, out)
    rep.update(file=rel(job, out), sha256=sha256_file(out), made=dt.datetime.now().isoformat(timespec="minutes"))
    # (2026-11-05) the .bed.wav is a preview; BED.json is the level plan Fairlight carries out, by computer control
    rep.update(preview=True, note_preview=PREVIEW_NOTE,
               use="a LEVEL PLAN for Fairlight, applied by computer control (the computer-control rule) to the music on A5 — the "
                   ".bed.wav beside it is a preview to listen to; no console copy places it",
               fairlight=bed_steps(rep))
    json.dump(rep, open(os.path.join(job, "06-music", "bed", "BED.json"), "w", encoding="utf-8"), indent=1)
    json.dump({"kind": "music_bed_preview", "preview": True, "sources": [{"file": rep["source"], "role": "music"}],
               "made": rep["made"],
               "note": PREVIEW_NOTE + " (derived from the track: its manifest row and licence cover it, mix_qa.py)"},
              open(out + ".conform.json", "w", encoding="utf-8"), indent=1)
    return rep


def bed_steps(rep: dict) -> list:
    """BED.json's level plan as Fairlight steps, in plain words, for computer control."""
    S = []
    if rep.get("fitted"):
        S.append("The source is the fitted music, rebuilt on A5 from the original (07-edit/music/REBUILD.md): its edits "
                 "already set the length and the ending.")
    else:
        if rep.get("src_in_s"):
            S.append(f"Trim the head: start the original at {rep['src_in_s']} s (its near-silent opening is cut).")
        if rep.get("removed_s"):
            S.append(f"One bar seam: cut from {rep['seam_out_s']} s to {rep['seam_in_s']} s of the original "
                     f"({rep['removed_s']} s out), with a {1000 * BED_XFADE_S:.0f} ms equal-power crossfade. It sits at "
                     f"{rep['seam_video_s']} s in the ad" + (", under the voice." if rep.get("seam_under_speech") else "."))
        elif rep.get("seam"):
            S.append("No bar seam was found: start the original later so it ends on the last frame (" + rep["seam"] + ").")
        if rep.get("short_by_s"):
            S.append(f"The track is {rep['short_by_s']} s short: start it that much late, so its ending lands on the last "
                     f"frame.")
    S.append(f"Ride the sections to one level, at most ±{BED_RIDE_DB:g} dB (the preview moved {rep.get('ride_range_db')} dB "
             f"in all).")
    if rep.get("voice"):
        S.append(f"Duck the music {BED_DUCK_DB:g} dB under the voice ({int(BED_ATTACK_S * 1000)} ms attack, "
                 f"{int(BED_RELEASE_S * 1000)} ms release), keyed from the dialogue.")
        S.append(f"Cut {BED_CARVE_DB:g} dB at {BED_CARVE_HZ[0] / 1000:g}–{BED_CARVE_HZ[1] / 1000:g} kHz on the music while "
                 f"the voice speaks.")
        S.append(f"Set the music {rep.get('under_voice_db')} dB under the voice while it speaks (the client's level, "
                 f"{rep.get('under_source')}); the preview measured {rep.get('bed_under_voice_measured_db')} dB.")
    if rep.get("peak_trim_db"):
        S.append(f"Keep the music's peak at or under −1 dBFS (the preview took {rep['peak_trim_db']} dB off).")
    S.append("Listen through, then export the music stem into 09-qa/mix/ for `mix_qa.py measure --music`.")
    return S


def selftest() -> int:
    np = _np()
    fails = []

    def check(name, ok, detail=""):
        print(("PASS  " if ok else "FAIL  ") + name + (f" — {detail}" if detail and not ok else ""))
        if not ok:
            fails.append(name)

    def fake_resolve(job, RB, dst):
        """What Resolve makes of the rebuild, for these tests: the original's segments at their whole frames, each
        seam's crossfade centred on its splice, the end faded — 48 kHz, as the music stem exported into 09-qa/mix/."""
        sr = SR_OUT
        x = decode(os.path.join(job, RB["original"]["file"]), sr, 2)
        fps_, sg, sm = float(RB["fps"]), RB["segments"], RB["seams"]
        n_tot = int(round(RB["end"]["frame"] / fps_ * sr))
        y = np.zeros((n_tot, 2), np.float32)
        for i, s in enumerate(sg):
            xi = int(sm[i - 1]["crossfade_s"] * sr) if i else 0
            xo = int(sm[i]["crossfade_s"] * sr) if i < len(sg) - 1 else 0
            a = int(round(s["src_in_f"] / fps_ * sr)) - xi // 2
            piece = x[max(0, a):int(round(s["src_out_f"] / fps_ * sr)) + (xo - xo // 2)].copy()
            if xi:
                piece[:xi] *= np.sin(np.linspace(0, np.pi / 2, xi, dtype=np.float32))[:, None]
            if xo:
                piece[-xo:] *= np.cos(np.linspace(0, np.pi / 2, xo, dtype=np.float32))[:, None]
            at = int(round(s["record_f"] / fps_ * sr)) - xi // 2
            piece = piece[:max(0, n_tot - at)]
            y[at:at + len(piece)] += piece
        if RB["end"].get("trim"):
            f_ = int(RB["end"]["fade_s"] * sr)
            y[-f_:] *= np.linspace(1, 0, f_, dtype=np.float32)[:, None]
        return encode(y, sr, dst)

    # (2026-11-05) is_preview: every Python render is a preview; the original, the composed layer and its stems are not
    yes = ["06-music/fit/bed.fit.wav", "/Users/v/jobs/fx-01001/06-music/bed/t.bed.wav", "06-music/family/bed.15s.wav",
           "06-music/family/bed.full.wav", "06-sfx/conform/S2.sfx.wav", "06-sfx/conform/S1-S2.joins.wav",
           "06-sfx/conform/S2.sfx.mp4", "07-edit/music/cue.preview.wav", "/j/06-music/x.preview.wav",
           r"C:\jobs\fx\06-music\fit\bed.arranged.wav"]
    no = ["06-music/bed.wav", "06-music/compose/fx-01001.layer.wav", "06-music/compose/fx-01001.layer.stem-impact.wav",
          "06-music/stems/bed/bed_drums.wav", "05-voice/VO_1.wav", "06-music/fit/bed.map.json", "06-music/bedtime.wav",
          "09-qa/mix/fx_stem-m_v001.wav", "", "/lib/Epic.Full.wav", "/lib/Track.preview.mp3", "elsewhere/bed.arranged.wav"]
    check("is_preview: the fit, the bed, the family, the alt mix, the SFX conforms and any .preview. file are previews; "
          "the original, the composed layer, its stems, a voice and a map are not",
          all(is_preview(p) for p in yes) and not any(is_preview(p) for p in no),
          [p for p in yes if not is_preview(p)] + [p for p in no if is_preview(p)])
    # (2026-11-05) rebuild_segments: whole frames that abut, the splice never after a downbeat, the end and its fade
    rs_, ss_, es_ = rebuild_segments(Plan([[1.0, 5.0], [9.0, 20.0]], 0.5, 1.0), {"onsets": [9.0]}, 24, 12.0)
    check("rebuild_segments: two segments cut PRE_S before the join's downbeat (4.99 s, 8.99 s), abutting on whole frames "
          "— 24→119 at 12, then 215→396 at 107 — downbeats on the plan, a 3 ms crossfade over the transient, the end at "
          "frame 288 faded from 270",
          [(r["src_in_f"], r["src_out_f"], r["record_f"]) for r in rs_] == [(24, 119, 12), (215, 396, 107)]
          and abs(rs_[0]["src_out_s"] - 4.99) < 1e-9 and abs(rs_[1]["src_in_s"] - 8.99) < 1e-9
          and abs(rs_[1]["record_s"] - 4.49) < 1e-9 and abs(rs_[1]["src_out_s"] - 16.5) < 1e-9
          and [r["offset_ms"] for r in rs_] == [0.0, 0.0] and ss_[0]["crossfade_ms"] == 3.0 and ss_[0]["splice_f"] == 107
          and abs(ss_[0]["downbeat_s"] - 4.5) < 1e-9 and es_["trim"] and es_["frame"] == 288 and es_["fade_from_f"] == 270,
          json.dumps([rs_, ss_, es_]))
    rs_, _, es_ = rebuild_segments(Plan([[1.0, 20.0]], 0.0, 1.01), {}, 24, 15.0)
    check("rebuild_segments: a speed change lists the retimed in and out, no frame offsets (not placed by script)",
          rs_[0]["offset_ms"] is None and abs(rs_[0]["retimed_in_s"] - 1.0 / 1.01) < 1e-3 and es_["trim"],
          json.dumps(rs_))
    with tempfile.TemporaryDirectory() as job:
        for d in ("06-music", "07-edit/titles", "09-qa/mix"):
            os.makedirs(os.path.join(job, d), exist_ok=True)
        tr = os.path.join(job, "06-music", "bed.wav")
        info = synth_track(tr, stems_dir=os.path.join(job, "06-music"), vocals_bars=(2, 3, 4, 5))
        M = map_track(tr, job, "numpy")
        check("the tempo is found (120 BPM ±1 %)", abs(M["tempo"] - 120) < 1.2, M["tempo"])
        d0 = M["downbeats"]
        ok_phase = all(abs(((x - info["lead"]) / (4 * info["beat"])) - round((x - info["lead"]) / (4 * info["beat"]))) < 0.03 for x in d0[:10])
        check("the downbeats sit on the bar lines (the low-band accent picks the phase)", M["meter"] == 4 and ok_phase,
              json.dumps(d0[:6]))
        check("the track ends on a hit, found at its bar line", M["ending"]["kind"] == "hit" and abs(M["ending"]["t"] - info["end"]) < 0.05,
              json.dumps(M["ending"]))
        check("four-bar phrases and section changes come out of the map", len(M["phrases"]) >= 4 and len(M["bars"]) >= 16)
        check("the key is reported, advisory", M["key"].get("camelot") is not None)
        # the cut and the hit list
        fps = 24.0
        clips = [(0, 3.0), (3.0, 6.05), (6.05, 10.0), (10.0, 16.0), (16.0, 22.0), (22.0, 30.0)]
        json.dump({"fps": fps, "tracks": {"video1": [{"name": f"S{i + 1}_v1.mp4", "start_s": a, "duration_s": b - a}
                                                      for i, (a, b) in enumerate(clips)],
                                          "audio1": [{"name": "VO_1.wav", "start_s": 3.2, "duration_s": 4.0}]}},
                  open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
        json.dump({"id": "T9", "kind": "endcard", "at_s": 26.0, "duration_s": 4.0},
                  open(os.path.join(job, "07-edit", "titles", "T9.title.json"), "w"))
        hits_init(job)
        H = load_hits(job)
        check("hits init: every cut optional, the end card the must button, the VO as speech",
              len(H["hits"]) == 6 and H["hits"][-1]["want"] == "button" and H["end_card"]["t"] == 26.0 and H["speech"] == [[3.2, 7.2]])
        # (v2.68.0) the person points to their music; the shortlist ranks cleared cues with reasons
        catd = os.path.join(job, "_t", "catalogues")
        mus = os.path.join(job, "_t", "Their Music")
        os.makedirs(mus, exist_ok=True)
        synth_track(os.path.join(mus, "Warm Folk Long.wav"), bpm=120, bars=20, ending="hit")
        synth_track(os.path.join(mus, "Warm Vocal Short.wav"), bpm=120, bars=6, ending="fade")
        synth_track(os.path.join(mus, "Cold Synth Long.wav"), bpm=120, bars=20, ending="fade")
        synth_track(os.path.join(mus, "Warm Folk No Vocals.wav"), bpm=120, bars=20, ending="hit")
        check("(2.68) with no music catalogued the shortlist says so, and never assumes a folder",
              not shortlist(job, "warm", catd)["cues"] and "never assumes a music folder" in shortlist(job, "warm", catd)["message"])
        la = library_add(mus, "their-music", "their own licence", "unverified", catd)
        check("(2.68) `library add` catalogues and measures the folder (numpy grid recorded)",
              la["left"] == 0 and la["measured"]["measured_now"] == 4, json.dumps(la, default=str)[:300])
        check("(2.68) music not cleared for paid ads is never shortlisted by default",
              not shortlist(job, "warm", catd)["cues"])
        import sfx_conform as _SX
        mp_ = os.path.join(catd, "their-music.library.json")
        mm_ = json.load(open(mp_)); mm_["paid_ads"] = "yes"; json.dump(mm_, open(mp_, "w"))
        sl = shortlist(job, "warm", catd)
        names_ = [os.path.basename(c["rel"]) for c in sl["cues"]]
        check("(2.68) cleared: the brief's words, length for the cut, a hit ending for the button and the fitter "
              "rank the long warm cue first; a sung lyric is flagged",
              names_ and names_[0] in ("Warm Folk Long.wav", "Warm Folk No Vocals.wav")
              and any("ends on a hit" in w for w in sl["cues"][0]["why"])
              and all("sung lyric" in " ".join(c["why"]) for c in shortlist(job, "warm", catd, n=6)["cues"]
                      if "Warm Vocal Short" in c["rel"]),
              json.dumps([(c["rel"], c["why"], c["fit"]) for c in sl["cues"]])[:600])
        nv_ = [c for c in shortlist(job, "warm", catd, n=6)["cues"] if "No Vocals" in c["rel"]]
        check("(2.68) \"No Vocals\" is instrumental, never a sung-lyric penalty",
              nv_ and "instrumental" in nv_[0]["why"] and not any("sung lyric" in w for w in nv_[0]["why"]),
              json.dumps(nv_))
        rp_ = os.path.join(catd, "their-music.jsonl")
        rws_ = [json.loads(l_) for l_ in open(rp_)]
        for r_ in rws_:
            if "Cold Synth" in r_["rel"]:
                r_["description"] = "Cold synth bed, no vocals"
                r_["words"] = sorted(set(r_["words"]) | {"vocal"})
        open(rp_, "w").write("".join(json.dumps(r_) + "\n" for r_ in rws_))
        cs_ = [c for c in shortlist(job, "", catd, n=6)["cues"] if "Cold Synth" in c["rel"]]
        check("(2.68) \"no vocals\" in a description or the person's tags counts too (not only the file name)",
              cs_ and "instrumental" in cs_[0]["why"] and not any("sung lyric" in w for w in cs_[0]["why"]),
              json.dumps(cs_)[:400])
        check("(2.68) the fitter actually runs on a steady grid (it is not switched off by the downbeat guess)",
              any(c["fit"] is not None for c in sl["cues"]), json.dumps([(c["rel"], c["grid"], c["fit"]) for c in sl["cues"]]))
        sk_ = shortlist(job, "warm", catd, fit_budget_s=0)
        check("(2.68) every steady track is fitted inside a budget; what the budget leaves out is counted and said",
              sk_["fit_skipped"] >= 1 and "not fitted inside" in sk_["message"], json.dumps(sk_)[:300])
        nothing_ = shortlist(os.path.join(job, "_t", "nojob"), "", catd)
        check("(2.68) with no mood words and no hit list the shortlist says it has nothing to rank by",
              not nothing_["ranked"] and "Nothing to rank by" in nothing_["message"], json.dumps(nothing_)[:300])
        cm_ = subprocess.run([sys.executable, os.path.abspath(__file__), "map", os.path.join(mus, "Warm Folk Long.wav"),
                              "--engine", "numpy", "--force"], capture_output=True, text=True)
        check("(2.68) `map --force` still works from the command line (the new verbs took its flag once)",
              cm_.returncode == 0, cm_.stderr[-300:])
        rows_m = {r["name"]: r for r in _SX.load_catalogues(catd, kind="music")}
        check("(2.68) each music row records its engine and grid; the numpy line applies",
              all((r.get("measure") or {}).get("engine") == "numpy" and r["measure"]["grid"] in ("reliable", "unreliable")
                  for r in rows_m.values()), json.dumps({k: v.get("measure") for k, v in rows_m.items()})[:400])
        try:
            hits_init(job)
            check("hits init never overwrites the director's marks", False)
        except SystemExit:
            check("hits init never overwrites the director's marks", True)
        for h in H["hits"]:
            if abs(h["t"] - 10.0) < 1e-6:
                h.update(type="reveal", priority="must", want="downbeat")
        H["track"] = {"file": "06-music/bed.wav", "vocals": "lyrics", "edits_allowed": "yes", "stems": "none"}
        json.dump(H, open(os.path.join(job, HITS), "w"))
        F = fit(job, engine="numpy")
        b0 = F["plans"][0]
        rows = {r["id"]: r for r in b0["hits"]}
        reveal = next(r for r in b0["hits"] if abs(r["t"] - 10.0) < 1e-6)
        check("the fit lands the must reveal on a downbeat inside 0..+1 frame", reveal["class"] == "on", json.dumps(reveal))
        check("the fit lands the button on the end card by whole-bar edits", rows["BUTTON"]["class"] == "on"
              and any(e["kind"] == "bars" for e in b0["plan"]["edits"]), json.dumps(b0["plan"]) + json.dumps(rows["BUTTON"]))
        check("three plans, each with its residuals, and no stretch on sung vocals",
              len(F["plans"]) == 3 and all(abs(p["plan"]["ratio"] - 1) < 1e-9 for p in F["plans"]))
        cut6 = [n for n in b0["nudges"] if abs(n["cut_at"] - 6.05) < 1e-6]
        check("a cut 1–2 frames off its beat is listed as a nudge, never applied",
              bool(cut6) and cut6[0]["applied"] is False and abs(cut6[0]["move_frames"]) <= 2, json.dumps(b0["nudges"]))
        # (2026-11-05) the fit wrote the rebuild: the picked plan as the edit Resolve makes from the ORIGINAL
        RB = json.load(open(os.path.join(job, REBUILD)))
        pl0, sg, sm = Plan.from_dict(b0["plan"]), RB["segments"], RB["seams"]
        check("REBUILD.json: the original and its sha256, the plan's sha256, two segments cut PRE_S before the join's "
              "downbeat, abutting on whole frames, placed at plan.start + the preceding length, the seam's crossfade, "
              "every downbeat within half a frame, the end trimmed with a 0.75 s fade",
              RB["original"]["file"] == "06-music/bed.wav" and RB["original"]["sha256"] == sha256_file(tr)
              and RB["plan_sha"] == plan_sha(b0["plan"]) and len(sg) == len(pl0.segments) == 2 and len(sm) == 1
              and abs(sg[0]["src_out_s"] - (pl0.segments[0][1] - PRE_S)) < 1e-3
              and abs(sg[1]["src_in_s"] - (pl0.segments[1][0] - PRE_S)) < 1e-3
              and sg[1]["record_f"] == sg[0]["record_f"] + sg[0]["frames"] == sm[0]["splice_f"]
              and abs(sg[1]["record_s"] - (pl0.start + sg[0]["src_out_s"] - sg[0]["src_in_s"])) < 1e-3
              and abs(sm[0]["downbeat_s"] - pl0.seams()[0]) < 1e-3 and sm[0]["crossfade_s"] == seam_xfades(pl0, M)[0]
              and all(abs(s["offset_ms"]) <= 500.0 / fps + 0.1 for s in sg)
              and sg[1]["src_in_f"] / fps <= sg[1]["src_in_s"] + 1e-9 and sg[0]["src_out_f"] / fps <= sg[0]["src_out_s"] + 1e-9
              and RB["end"]["trim"] and RB["end"]["fade_s"] == 0.75 and RB["placed_by_script"] and RB["speed"] is None,
              json.dumps(RB)[:3000])
        md = open(os.path.join(job, "07-edit", "music", "REBUILD.md")).read()
        check("REBUILD.md is the checklist for Fairlight: check A5, the seam's crossfade at its length, the end fade, listen "
              "at every seam, export the music stem for the mix gate",
              "Check A5" in md and f"add a {sm[0]['crossfade_ms']:g} ms crossfade" in md and "fade it out" in md
              and "Listen at every seam" in md and "--music" in md and "computer control" in md, md)
        con = open(os.path.join(job, "07-edit", MUSIC_COPY)).read()
        mline = next(x for x in con.splitlines() if x.startswith("MUSIC_FIT = "))
        mkline = next(x for x in con.splitlines() if x.startswith("MARKERS = "))
        import ast
        mf_ = ast.literal_eval(mline[len("MUSIC_FIT = "):mline.index("  # __MUSIC_FIT__")])
        check("the console copy places the ORIGINAL on A5 by its segments — never a render — with sparse markers and a "
              "marker per seam and over the end fade",
              "PLACE_MUSIC_FIT = True" in con and mf_["file"] == os.path.abspath(tr) and mf_["track"] == 5
              and mf_["sha256"] == RB["original"]["sha256"]
              and mf_["segments"] == [{"src_in_f": s["src_in_f"], "src_out_f": s["src_out_f"], "record_f": s["record_f"]} for s in sg]
              and ".fit.wav" not in mline + mkline and not is_preview(mf_["file"])
              and "'Phrase'" in mkline and "Hit " in mkline and mkline.count("'Beat'") == 0
              and "Music seam 1 — crossfade" in mkline and "Music end — fade 750 ms" in mkline
              and "Filled in by music_fit.py rebuild: the ORIGINAL track's segments on A5; crossfades and fades in "
                  "Fairlight by computer control (REBUILD.md)" in con, mline + mkline)
        P, Wn = check_job(job)
        check("no render is needed for export: with REBUILD.json current the fit is not refused for want of a render, and "
              "the measures wait for what Resolve makes (a note naming the stem, not a refusal)",
              P and all("sung lyrics" in x for x in P) and any("not measured" in x and "--music" in x for x in Wn),
              json.dumps([P, Wn]))
        R = render(job)
        out = os.path.join(job, R["render"]["file"])
        cj_ = json.load(open(out + ".conform.json"))
        check("the render is a PREVIEW: 48 kHz, conform kind music_fit_preview with its note, F['render'] marked, the "
              "licence travelling from the track, and the same REBUILD.json",
              cj_["kind"] == "music_fit_preview" and cj_["preview"] is True and "never imported into Resolve" in cj_["note"]
              and cj_["sources"][0]["file"] == "06-music/bed.wav" and R["render"]["preview"] is True and is_preview(out)
              and json.load(open(os.path.join(job, REBUILD)))["plan_sha"] == RB["plan_sha"], json.dumps(cj_))
        P, Wn = check_job(job)
        check("lyrics under speech refuse", any("sung lyrics under speech" in x for x in P), json.dumps(P))
        H = load_hits(job)
        H["track"]["vocals"] = "none"
        json.dump(H, open(os.path.join(job, HITS), "w"))
        P, Wn = check_job(job)
        check("no stem from Resolve yet: nothing refused, a note names what to export", not P
              and any("the music is not measured" in x for x in Wn), json.dumps([P, Wn]))
        stem_p = fake_resolve(job, RB, os.path.join(job, "09-qa", "mix", "fx_stem-m_v001.wav"))
        P, Wn = check_job(job)
        check("a clean rebuild passes: the music stem Resolve made is measured — 48 kHz, no click at the seam",
              not P and not any("not measured" in x for x in Wn) and resolve_stem(job)["kind"] == "music", json.dumps([P, Wn]))
        check("the share of cuts on a beat is information only", any("information only" in x for x in Wn))
        os.makedirs(os.path.join(job, "10-export"), exist_ok=True)
        rq = os.path.join(job, "09-qa", "mix", "fx_qc-music.wav")
        shutil.copy(stem_p, rq)
        json.dump({"stems": {"bed": {"file": "09-qa/mix/fx_stem-m_v001.wav"}, "music": {"file": "09-qa/mix/fx_qc-music.wav"},
                             "dialogue": {"file": "09-qa/mix/fx_qc-d.wav"}}},
                  open(os.path.join(job, "10-export", "fx_master.mp4.mix.json"), "w"))
        check("the stem measured is the music stem mix_qa.py's report records (`--music`), before any file named by "
              "convention", (resolve_stem(job) or {}).get("file") == "09-qa/mix/fx_qc-music.wav", resolve_stem(job))
        os.remove(os.path.join(job, "10-export", "fx_master.mp4.mix.json")); os.remove(rq)
        H["track"]["edits_allowed"] = "unknown"
        json.dump(H, open(os.path.join(job, HITS), "w"))
        check("an edited track whose licence is not recorded as allowing it refuses",
              any("licence is not recorded" in x for x in check_job(job)[0]))
        H["track"]["edits_allowed"] = "yes"
        json.dump(H, open(os.path.join(job, HITS), "w"))
        # the cut moves: refused without an approved nudge, accepted with one
        dump = json.load(open(os.path.join(job, "07-edit", "timeline-dump.json")))
        dump["tracks"]["video1"][2]["start_s"] = 6.05 - 1 / 24.0
        json.dump(dump, open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
        P, _ = check_job(job)
        check("a cut moved without approval refuses", any("never moves by itself" in x for x in P), json.dumps(P))
        hid = next(h["id"] for h in H["hits"] if abs(h["t"] - 6.05) < 1e-6)
        H["approved_nudges"] = [{"hit": hid, "frames": -1, "by": "Dana", "quote": "take the nudge"}]
        json.dump(H, open(os.path.join(job, HITS), "w"))
        check("…and passes once the owner approves that nudge", not [x for x in check_job(job)[0] if "never moves" in x])
        # (v2.48.0, project switch music-led) the same moved cut, no nudge approved, in a music-led job: not refused (the
        # picture is cut to the song), the lift printed, and the render still measured by the same lines
        os.makedirs(os.path.join(job, "00-brief"), exist_ok=True)
        cp_ = os.path.join(job, "00-brief", "CHECKPOINT.md")
        open(cp_, "w").write("Switches:   music-led — the client's song is the deliverable\n")
        H["approved_nudges"] = []
        json.dump(H, open(os.path.join(job, HITS), "w"))
        P, Wn = check_job(job)
        check("music-led: a cut moved since the fit with no nudge approved is not refused; the lift prints and what "
              "Resolve made is still measured", not P and any("lifted by project switch `music-led` (the client's song is "
                                                              "the deliverable)" in x for x in Wn)
              and any("information only" in x for x in Wn) and not any("not measured" in x for x in Wn),
              json.dumps(P) + json.dumps(Wn))
        os.remove(cp_)
        H["approved_nudges"] = [{"hit": hid, "frames": -1, "by": "Dana", "quote": "take the nudge"}]
        json.dump(H, open(os.path.join(job, HITS), "w"))
        # a hard splice with no crossfade clicks — at the seam of what Resolve made (the rebuild's whole-frame splice)
        if len(RB["segments"]) > 1:
            y = decode(stem_p, SR_OUT, 2)
            i = int(round(RB["segments"][1]["record_f"] / fps * SR_OUT))
            y[i:] = np.roll(y[i:], 37, axis=0) * -1.0 + 0.3
            encode(y, SR_OUT, stem_p)
            P = check_job(job)[0]
            check("a raw splice at a seam of the exported music stem is heard as a click and refuses",
                  any("click" in x for x in P), json.dumps(P))
            bed_p = os.path.join(job, "09-qa", "mix", "fx_qc-bed.wav")
            os.replace(stem_p, bed_p)
            P, Wn = check_job(job)
            check("…measured on the bed instead (it carries other sounds), the click is a note to listen, not a refusal",
                  not any("click" in x for x in P) and any("click" in x and "measured on the bed" in x for x in Wn)
                  and resolve_stem(job)["kind"] == "bed", json.dumps([P, Wn]))
            os.remove(bed_p)
            fake_resolve(job, RB, stem_p)
        # (2026-11-05) the timeline: a preview on an audio track refuses; the original on none warns
        dp_ = os.path.join(job, "07-edit", "timeline-dump.json")
        dump = json.load(open(dp_))
        dump["tracks"]["audio5"] = [{"name": "bed.fit.wav", "file": os.path.join(job, "06-music", "fit", "bed.fit.wav"),
                                     "start_s": 0.0, "duration_s": 30.0}]
        json.dump(dump, open(dp_, "w"))
        P, Wn = check_job(job)
        check("a dump with the .fit.wav on an audio track refuses (a preview on the timeline), and the original on no "
              "audio track warns", any("a preview render is on the timeline" in x and "bed.fit.wav" in x for x in P)
              and any("on no audio track" in x for x in Wn), json.dumps([P, Wn]))
        dump["tracks"]["audio5"] = [{"name": "bed.wav", "file": "/Volumes/jobs/fx/06-music/bed.wav", "start_s": 0.0,
                                     "duration_s": 13.5}, {"name": "bed.wav", "file": "/Volumes/jobs/fx/06-music/bed.wav",
                                                           "start_s": 13.5, "duration_s": 16.5}]
        json.dump(dump, open(dp_, "w"))
        P, Wn = check_job(job)
        check("…the original's segments on A5 instead: nothing refused, no warning about the track",
              not P and not any("on no audio track" in x for x in Wn), json.dumps([P, Wn]))
        # (2026-11-05) a stale rebuild: another plan picked after REBUILD.json was written
        F2 = json.load(open(os.path.join(job, FIT)))
        F2["picked"] = 1
        json.dump(F2, open(os.path.join(job, FIT), "w"))
        P = check_job(job)[0]
        check("a plan picked after REBUILD.json was written refuses as stale", any("stale" in x and "rebuild" in x for x in P),
              json.dumps(P))
        rebuild(job, 0)
        os.remove(os.path.join(job, REBUILD))
        P = check_job(job)[0]
        check("no REBUILD.json refuses, naming `rebuild`", P == ["the music is not prepared for the Resolve rebuild — "
                                                                 "`music_fit.py rebuild <job>`"], json.dumps(P))
        rebuild(job)
        # the stretch: a button between bar lines is reached by ≤2 %, never more
        H = load_hits(job)
        keep = json.loads(json.dumps(H))
        H["end_card"]["t"] = 26.3
        H["hits"] = [dict(h, t=26.3) for h in H["hits"] if h["want"] == "button"]
        json.dump(H, open(os.path.join(job, HITS), "w"))
        F = fit(job, engine="numpy")
        ratios = [p["plan"]["ratio"] for p in F["plans"]]
        H = keep
        check("a stretch is the last resort and never past 2 %", all(abs(r - 1) <= STRETCH_CAP + 1e-9 for r in ratios)
              and any(abs(r - 1) > 1e-6 for r in ratios), json.dumps(ratios))
        H["end_card"]["t"] = 26.0
        next(h for h in H["hits"] if h["want"] == "button")["t"] = 26.0
        # punctuation and the accent budget
        H["hits"] += [{"id": "SD1", "t": 16.0, "type": "turn", "priority": "optional", "want": "stop_down"},
                      {"id": "SD2", "t": 22.0, "type": "turn", "priority": "optional", "want": "stop_down"},
                      {"id": "DR1", "t": 4.0, "type": "payoff", "priority": "optional", "want": "drop"}]
        H["fx"] = [{"kind": "riser", "t": 25.0, "dur": 1.0}, {"kind": "riser", "t": 9.0, "dur": 0.5},
                   {"kind": "riser", "t": 12.0, "dur": 1.0}, {"kind": "riser", "t": 20.0, "dur": 1.0},
                   {"kind": "scratch", "t": 5.0}, {"kind": "scratch", "t": 15.0},
                   {"kind": "impact", "t": 26.0}, {"kind": "sub_drop", "t": 26.0}]
        json.dump(H, open(os.path.join(job, HITS), "w"))
        W2 = punctuation(H) + accent_budget(job, H)
        check("two stop-downs, an act-one drop, four risers, two scratches and a doubled low end all warn",
              any("stop-downs" in x for x in W2) and any("first act" in x for x in W2) and any("4 risers" in x for x in W2)
              and any("scratches" in x for x in W2) and any("low end" in x for x in W2), json.dumps(W2))
        # package D: library stems, the arrangement, the stop-down measured on the render
        H["hits"] = [h for h in H["hits"] if h["id"] not in ("SD2", "DR1")]
        H["fx"] = []
        H["sections"] = [{"t0": 0, "t1": 10.0, "energy": "low", "role": "hook"}, {"t0": 10.0, "t1": 30.0, "energy": "high", "role": "body"}]
        H["track"]["vocals"] = "lyrics"
        json.dump(H, open(os.path.join(job, HITS), "w"))
        fit(job, engine="numpy")
        S = stems(job)
        check("the library's own stems are found beside the track", S["source"] == "library" and set(S["stems"]) == {"drums", "bass", "other", "vocals"},
              json.dumps(S))
        arrange(job)
        Fa_ = json.load(open(os.path.join(job, FIT)))
        arr = os.path.join(job, Fa_["render"]["file"])
        RBa = json.load(open(os.path.join(job, REBUILD)))
        check("the arrangement is a preview (music_arrangement_preview); REBUILD.json and .md carry it for Fairlight — the "
              "stems, the stop-down, the vocal stem muted under speech",
              json.load(open(arr + ".conform.json"))["kind"] == "music_arrangement_preview" and Fa_["render"]["preview"]
              and RBa["plan_sha"] == plan_sha(Fa_["plans"][Fa_.get("picked", 0)]["plan"])
              and RBa["arrangement"]["stop_downs"] == [16.0] and RBa["arrangement"]["vocals_muted_under"] == [[3.2, 7.2]]
              and len(RBa["arrangement"]["stems"]) >= 4
              and "NOT that arrangement" in open(os.path.join(job, "07-edit", "music", "REBUILD.md")).read(),
              json.dumps(RBa.get("arrangement")))
        shutil.copy(arr, stem_p)                       # Fairlight rebuilt the arrangement the preview proposes
        P, Wn = check_job(job)
        check("(v2.50) arranged only in the preview, nothing on the timeline shows the stems: lyrics under speech still "
              "refuse", ARRANGED_ONLY_IN_PREVIEW in P, json.dumps(P))
        tdp = os.path.join(job, "07-edit", "timeline-dump.json")
        _had = open(tdp, encoding="utf-8").read() if os.path.isfile(tdp) else None
        _d = json.loads(_had) if _had else {"tracks": {}}
        _d.setdefault("tracks", {}).setdefault("audio6", []).append(
            {"name": "bed_vocals.wav", "file": os.path.join(job, "06-music", "stems", "bed", "bed_vocals.wav")})
        json.dump(_d, open(tdp, "w", encoding="utf-8"))
        P, Wn = check_job(job)
        check("arranged with the vocal stem muted under speech, the stems on the timeline: lyrics no longer refuse",
              not [x for x in P if "lyrics" in x], json.dumps(P))
        if _had is None:
            os.remove(tdp)
        else:
            open(tdp, "w", encoding="utf-8").write(_had)
        check("the stop-down is measured on the music stem Resolve made", not [x for x in Wn if "stop-down before SD1" in x]
              and not any("not measured" in x for x in Wn), json.dumps(Wn))
        ya = decode(arr, SR_OUT, 2).mean(1)
        e_low = float(np.sqrt(np.mean(ya[int(1.0 * SR_OUT):int(8.0 * SR_OUT)] ** 2)))
        e_hi = float(np.sqrt(np.mean(ya[int(11.0 * SR_OUT):int(15.0 * SR_OUT)] ** 2)))
        check("the drums come in on the turn: the body is louder than the hook", e_hi > 1.3 * e_low, f"{e_low:.4f} {e_hi:.4f}")
        # the key of a join is advisory
        check("Camelot: a relative minor is no distance, two steps clash", camelot_distance("8A", "8B") == 0 and camelot_distance("8A", "10A") == 2)
        # music: none
        json.dump({"music": "none"}, open(os.path.join(job, HITS), "w"))
        check("a film with no music bed declares it and passes", check_job(job) == ([], ["no music bed in this film (HITS.json music: none)"]))
        os.remove(os.path.join(job, HITS))
        check("no hit list refuses, naming the tool", any("hits init" in x for x in check_job(job)[0]))
    # (v2.48.0, project switch music-led) the song is fixed and is the deliverable; the picture is cut to it. Off, a
    # declared track with no fit refuses as in 2.47.0; on, the fit is lifted and printed, and these still refuse: a
    # stretch of any size, an edit of the song (bars, a bed seam) its licence does not allow, music: none, sung lyrics
    # under speech, a named song not on disk. Stdlib-only: no render is made here.
    with tempfile.TemporaryDirectory() as job:
        for d in ("00-brief", "06-music/fit", "06-music/bed", "07-edit/music"):
            os.makedirs(os.path.join(job, d), exist_ok=True)
        open(os.path.join(job, "06-music", "song.wav"), "wb").write(b"RIFF fixture: the client's song")
        why = "the client's song is the deliverable"
        ON, lf = f"music-led — {why}", f"lifted by project switch `music-led` ({why})"
        base = {"music": "fit", "fps": 24, "duration": 15.0,
                "track": {"file": "06-music/song.wav", "vocals": "none", "edits_allowed": "no", "stems": "none"},
                "hits": [{"id": "BUTTON", "t": 11.0, "type": "button", "priority": "must", "want": "button"}],
                "speech": [[2.0, 5.0]], "approved_nudges": []}
        T = lambda **k: dict(base, track=dict(base["track"], **k))
        fitp = lambda ratio=1.0, edits=(): {"fps": 24, "cuts_at_fit": [3.0, 6.0], "picked": 0, "plans": [{"plan": {
            "label": "the track", "track": "06-music/song.wav", "segments": [[0.0, 15.0 * ratio]], "start": 0.0,
            "ratio": ratio, "edits": list(edits)}, "hits": [], "map": ""}]}

        def put(sw, H_, fit_=None, bed_=None):
            open(os.path.join(job, "00-brief", "CHECKPOINT.md"), "w").write(f"Switches:   {sw}\n")
            json.dump(H_, open(os.path.join(job, HITS), "w"))
            for p_, d_ in ((os.path.join(job, FIT), fit_), (os.path.join(job, "06-music", "bed", "BED.json"), bed_)):
                if d_ is not None:
                    json.dump(d_, open(p_, "w"))
                elif os.path.isfile(p_):
                    os.remove(p_)
            return check_job(job)
        P, Wn = put("none", base)
        check("music-led off: a declared track with no fit refuses as in 2.47.0 (now naming `rebuild`), nothing lifted",
              P == ["no fit — `music_fit.py fit <job>`, pick a plan, then `rebuild`"] and not any("lifted" in x for x in Wn),
              json.dumps([P, Wn]))
        P, Wn = put(ON, base)
        check("music-led on: no fit plan → nothing refused, the lift printed with its reason", not P and lf in Wn[0],
              json.dumps([P, Wn]))
        P, Wn = put(ON, T(edits_allowed="yes"), fitp(1.01))
        check("music-led on: a 1 % stretch (inside the house cap, the licence allowing edits) refuses — the song plays at "
              "its own speed", len(P) == 1 and "the song is stretched" in P[0] and "+1.00 %" in P[0], json.dumps(P))
        P, Wn = put("none", T(edits_allowed="yes"), fitp(1.01))
        check("…while with the switch off the same plan is refused only for want of REBUILD.json — never for want of a "
              "render (2026-11-05: the render is a preview)",
              P == ["the music is not prepared for the Resolve rebuild — `music_fit.py rebuild <job>`"]
              and any("the music is not measured" in x for x in Wn), json.dumps([P, Wn]))
        old = os.path.join(job, "06-music", "fit", "song.fit.wav")
        open(old, "wb").write(b"RIFF an earlier render")
        for kind_ in ("music_fit_preview", "music_fit"):
            json.dump({"kind": kind_, "plan": {"ratio": 0.985}}, open(old + ".conform.json", "w"))
            P, _ = put(ON, T(edits_allowed="yes"))
            check(f"music-led on: a fit preview on disk recorded at ×0.985 ({kind_}) refuses, with no FIT.json naming it",
                  len(P) == 1 and "06-music/fit/song.fit.wav ×0.9850" in P[0], json.dumps(P))
        os.remove(old); os.remove(old + ".conform.json")
        bars = [{"op": "drop", "bars": 2, "kind": "bars"}]
        P, _ = put(ON, base, fitp(1.0, bars))
        check("music-led on: whole bars cut from the song, its licence not allowing edits, refuses (A15)",
              len(P) == 1 and "the song is edited (bars)" in P[0] and "licence is not recorded" in P[0], json.dumps(P))
        P, Wn = put(ON, T(edits_allowed="yes"), fitp(1.0, bars))
        check("…and passes once the licence allows edits; nothing measured yet is a note, not a refusal",
              not P and any("the music is not measured — not asked for here" in x for x in Wn), json.dumps([P, Wn]))
        P, _ = put(ON, base, bed_={"source": "06-music/song.wav", "fitted": False, "removed_s": 8.0})
        check("music-led on: a bed seam that takes bars out of the song, unlicensed, refuses",
              len(P) == 1 and "a bar seam in the bed" in P[0], json.dumps(P))
        P, _ = put(ON, T(vocals="lyrics"))
        check("music-led on: sung lyrics under speech still refuse (A12 is not what the switch lifts)",
              any("sung lyrics under speech" in x for x in P), json.dumps(P))
        P, _ = put(ON, T(file="06-music/missing.wav"))
        check("music-led on: a song HITS.json names that is not on disk refuses", any("is not on disk" in x for x in P),
              json.dumps(P))
        P, _ = put(ON, {"music": "none"})
        check("music-led on: HITS.json music: none refuses as a contradiction",
              len(P) == 1 and "contradiction" in P[0] and "music: none" in P[0], json.dumps(P))
        os.remove(os.path.join(job, HITS))
        P, _ = check_job(job)
        check("music-led on: no HITS.json refuses, asking for the client's song to be declared",
              len(P) == 1 and "declare the client's song" in P[0], json.dumps(P))
        open(os.path.join(job, "00-brief", "CHECKPOINT.md"), "w").write("Switches:   none\n")
        check("music-led off: no HITS.json refuses with the 2.47.0 wording",
              check_job(job)[0] == [f"no music plan — `music_fit.py hits init <job>` and `fit` (or set \"music\": \"none\" "
                                    f"in {HITS} for a film with no music bed)"])
    # the tiered window (house rule 2026-10-27): never early; hard 0..+1 frame (+2 warns); soft 0..+2 frames
    check("the tiered window: a hard hit at +60 ms (24 fps) warns, a soft one is on, 10 ms early is early for both",
          classify(0.060, 24, "hard") == "warn" and classify(0.060, 24, "soft") == "on"
          and classify(-0.010, 24, "soft") == "early" and classify(0.090, 24, "soft") == "late"
          and tier_of({"priority": "must"}) == "hard" and tier_of({"priority": "optional"}) == "soft")
    Hd = {"duration": 15, "hits": [{"id": f"X{i}", "t": float(i), "priority": "must", "want": "downbeat"} for i in range(3)]}
    check("three hard hits in a 15 s spot warn (density), and play_through takes one out of the count",
          bool(density_problems(Hd)[1]) and not density_problems(dict(Hd, hits=Hd["hits"][:2] + [dict(Hd["hits"][2], strategy="play_through")]))[1])
    # the bed (a supplement ad job): head silence trimmed, one bar seam, the ending on the last frame, ridden, ducked, carved,
    # and set to the client's level under the voice
    with tempfile.TemporaryDirectory() as job:
        for d in ("00-brief", "06-music", "07-edit"):
            os.makedirs(os.path.join(job, d), exist_ok=True)
        tr = os.path.join(job, "06-music", "t.wav")
        info = synth_track(tr, bars=24, lead=1.8)
        sr = SR_OUT
        L = 30.0
        v = np.zeros(int(L * sr), np.float32)
        rng = np.random.default_rng(5)
        for a0, a1 in ((2.0, 9.0), (12.0, 26.0)):
            m = int(a1 * sr) - int(a0 * sr)
            v[int(a0 * sr): int(a1 * sr)] = (0.1 * rng.standard_normal(m) * np.abs(np.sin(np.linspace(0, 60, m)))).astype(np.float32)
        encode(v, sr, os.path.join(job, "05-voice.wav"))
        open(os.path.join(job, "00-brief", "CHECKPOINT.md"), "w").write(f"Client:     {job}/acme.md\n")
        json.dump({"music_under_voice_db": 38}, open(os.path.join(job, "audio.acme.json"), "w"))
        r = bed(job, track="06-music/t.wav", voice="05-voice.wav", length=L)
        check("bed: the 1.8 s near-silent head is trimmed", 1.5 < r["src_in_s"] < 2.6, r)
        check("bed: the length is met by one bar seam, and the bed is exactly the ad's length",
              r.get("removed_s") and abs(r["length_s"] - L) < 0.02, r)
        y = decode(os.path.join(job, r["file"]), sr, 1)
        tail = 20 * np.log10(np.abs(y[-int(0.6 * sr):]).max() + 1e-9)
        check("bed: the track's own ending (its last hit and ring-out) is in the last second, not cut off",
              tail > -60, round(float(tail), 1))
        check("bed: set to the client's level — about 38 dB under the voice while it speaks (one client: 'barely noticeable')",
              r["under_voice_db"] == 38 and abs(r["bed_under_voice_measured_db"] - 38) < 3.0, r)
        Bj = json.load(open(os.path.join(job, "06-music", "bed", "BED.json")))
        check("bed: BED.json is a level plan for Fairlight by computer control, the .bed.wav a preview, and no console "
              "copy places it", Bj["preview"] is True and "LEVEL PLAN for Fairlight" in Bj["use"]
              and any("Duck the music 9 dB" in s for s in Bj["fairlight"]) and any("One bar seam" in s for s in Bj["fairlight"])
              and json.load(open(os.path.join(job, r["file"]) + ".conform.json"))["kind"] == "music_bed_preview"
              and is_preview(r["file"]) and not os.path.isfile(os.path.join(job, "07-edit", MUSIC_COPY)), json.dumps(Bj))
    print("\nselftest OK — the map finds the tempo, the bar lines and the ending; the fit lands a must reveal and the button "
          "by whole-bar edits and lists the cut nudges without applying them; a stretch stays under 2 % and never on sung "
          "vocals; the render is a preview carrying its licence; the rebuild lists the original's segments on whole frames "
          "and the console copy places the original, never a render, with sparse markers and a marker per seam; no render "
          "is needed to export, a stale or missing rebuild and a preview on the timeline refuse, and what Resolve made is "
          "measured; lyrics under speech, an "
          "unrecorded licence, a moved cut and a raw splice refuse; punctuation and the accent budget warn; library stems "
          "arrange the energy and the stop-down; the bed trims a silent head, seams on a bar, lands the ending, rides, ducks, "
          "carves and sits at the client's level under the voice, as a level plan for Fairlight; a music-led job (project "
          "switch, v2.48.0) needs no fit "
          "and says so, and still refuses a stretch of any size, an unlicensed edit, music: none, lyrics under speech and "
          "a missing song" if not fails else f"\nFAIL — {len(fails)} failing")
    return 1 if fails else 0


# ── (v2.68.0) the music shortlist: two or three cues worth auditioning, from the person's own cleared library ────────
# Planned with three review rounds each by Grok 4.7 and Sonnet 5.5. A first plan correlated a track's bar-energy curve
# with the shots' Energy 1–5; both cut it (a loudness trace against a picture-intent score ranks noise). What ranks
# here is what a music supervisor checks first: rights, length, ending, a sung lyric, the brief's mood words, and,
# when the hit list exists, how well the existing fitter lands the must-hits. The person still chooses by ear.
VOCAL_WORDS = {"vocal", "vocals", "vox", "lyric", "lyrics", "acapella", "acappella", "singer", "sung", "choir"}
INSTRUMENTAL_WORDS = {"instrumental", "inst", "novocal", "novocals", "nolyrics", "underscore"}
NO_LIBRARY = ("No music library cleared for paid ads is catalogued. Ask the person where their licensed music lives "
              "(a folder of full tracks they may use in ads), then: music_fit.py library add <folder> --name <name> "
              "--paid-ads yes --licence \"<the licence, in their words>\". The plugin never assumes a music folder.")


def library_add(folder: str, name: str, licence: str | None, paid_ads: str, cat: str | None = None,
                basis: str | None = None, tags_csv: str | None = None) -> dict:
    """The person points to their music: catalogue the folder as kind music, then measure it (numpy engine, resumable).
    `tags_csv` (filename,tags) adds their own mood or use words per track, for libraries whose files carry none."""
    import sfx_conform as SX
    if not os.path.isdir(folder):
        raise SystemExit(f"{folder} is not a folder — ask the person for the folder their licensed music is in")
    b = SX.build_library(folder, name, cat, "music", licence, paid_ads, basis or "the person's word", None)
    if tags_csv:
        import csv
        tags = {r.get("filename", ""): r.get("tags", "") for r in csv.DictReader(open(tags_csv, encoding="utf-8"))}
        rp = os.path.join(SX.catalogue_dir(cat), f"{name}.jsonl")
        rows = [json.loads(ln) for ln in open(rp, encoding="utf-8") if ln.strip()]
        for r in rows:
            t = tags.get(os.path.basename(r.get("rel", "")))
            if t:
                r["words"] = sorted(set(r.get("words") or []) | set(SX._words(t)))
                r["tags"] = t
        open(rp, "w", encoding="utf-8").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    if b["left"]:
        return {"built": b, "measured": None, "left": b["left"]}
    m = SX.measure_library(name, cat)
    return {"built": b, "measured": m, "left": m["left"]}


def shortlist(job: str, mood: str = "", cat: str | None = None, n: int = 3, all_licences: bool = False,
              fit_budget_s: float = 120.0) -> dict:
    import sfx_conform as SX
    rows = [r for r in SX.load_catalogues(cat, kind="music") if all_licences or r.get("paid_ads") == "yes"]
    if not rows:
        return {"job": job, "cues": [], "message": NO_LIBRARY}
    H = None
    try:
        H = load_hits(job)
    except SystemExit:
        H = None
    end = end_of(H) if H else None
    want_button = bool(H and any(h.get("want") == "button" and h.get("priority") == "must" for h in H.get("hits") or []))
    mood_w = set(SX._words(mood)) - SX.LIB_EXT_WORDS
    cues = []
    for r in rows:
        m = r.get("measure") or {}
        why, score = [], 0.0
        words = set(r.get("words") or [])
        if mood_w:
            hit = mood_w & words
            score += 2 * len(hit)
            if hit:
                why.append("the brief's words: " + ", ".join(sorted(hit)))
        dur = m.get("duration") or r.get("duration") or 0
        if end:
            if dur >= end:
                score += 1; why.append(f"long enough ({dur:.0f} s for {end:.0f} s)")
            else:
                why.append(f"short ({dur:.0f} s for {end:.0f} s): needs a loop or a phrase edit")
        if want_button and m.get("ending"):
            if m["ending"] == "hit":
                score += 1; why.append("ends on a hit, for the button")
            else:
                why.append("fades out: the button needs an edit or a sting")
        # the name, the description and the person's own tags all count (build review 2, Grok: "No Vocals" in a
        # description or a tags-csv line was still scored as a sung lyric)
        raw_name = re.sub(r"[_\-.]+", " ", " ".join(str(r.get(k) or "") for k in ("rel", "description", "tags"))).lower()
        instrumental = bool(words & INSTRUMENTAL_WORDS) or bool(re.search(r"\bno vocals?\b|\bwithout vocals?\b", raw_name))
        if instrumental:
            why.append("instrumental")
        elif words & VOCAL_WORDS and not re.search(r"\bvocal chops?\b", raw_name):
            score -= 1; why.append("⚠ a sung lyric: keep it out from under the voice")
        elif not words & INSTRUMENTAL_WORDS:
            why.append("lyrics unknown: listen for a voice before it goes under the VO")
        if m.get("grid") != "reliable":
            why.append("no steady beat grid (an assumed line, not yet calibrated on real tracks): audition it, the fit "
                       "cannot score it" if m else "not measured yet")
        elif m.get("downbeats") == "uncertain":
            why.append("bar lines are a guess: check where the bars start before trusting the fit")
        cues.append({"library": r["library"], "rel": r["rel"], "path": r.get("path"), "paid_ads": r.get("paid_ads"),
                     "score": score, "why": why, "grid": m.get("grid"), "fit": None})
    cues.sort(key=lambda c: -c["score"])
    nothing = not mood_w and not end and not want_button
    if nothing:                                  # no criteria: say so, and spread the offer across categories
        seen, spread = set(), []
        for c in cues:
            cat_ = os.path.dirname(c["rel"])
            if cat_ not in seen:
                seen.add(cat_); spread.append(c)
        cues = spread + [c for c in cues if c not in spread]
    # the existing fitter, only on rows with a reliable grid, only when the hit list holds (plan round 2, Grok)
    # the shortlist runs BEFORE a track is chosen, so "names no track" and the track's own fields are not problems here
    hp = [x for x in (hits_problems(H)[0] if H else []) if not x.startswith(("the hit list names no track", "track."))]
    skipped = 0
    if H and not hp:
        import time as _t
        t0 = _t.time()
        # every steady track is fitted, inside a time budget, and the number left unfitted is reported (build review 2,
        # Sonnet: fitting only the first six by name left most tracks unscored)
        for c in [c for c in cues if c["grid"] == "reliable" and c["path"] and os.path.isfile(c["path"])]:
            if _t.time() - t0 > fit_budget_s:
                skipped += 1
                continue
            try:
                M = map_track(c["path"], job, "numpy")
                plans = [score_plan(p, M, H)[0] for p in plans_for(M, H, c["rel"], "shortlist")]
            except SystemExit:
                plans = []
            if plans:
                c["fit"] = round(min(plans), 2)
                c["why"].append(f"the fitter lands the hits at a cost of {c['fit']} (lower is better)")
        cues.sort(key=lambda c: (-c["score"], c["fit"] if c["fit"] is not None else 99))
    msg = ("Nothing to rank by yet: give the brief's mood words (--mood), or make the hit list first (hits init). "
           "These are one per folder, not a ranking.") if nothing else \
        "Audition these under the voice; the person chooses by ear (editing-and-audio.md, music)."
    if skipped:
        msg += f" {skipped} steady track(s) were not fitted inside the {fit_budget_s:.0f} s budget: rerun with more time."
    return {"job": job, "cues": cues[:n], "pool": len(rows), "ranked": not nothing, "fit_skipped": skipped,
            "message": msg}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("map"); p.add_argument("track"); p.add_argument("--job"); p.add_argument("--engine", default="auto")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("library", help="(v2.68.0) the person points to their music folder: catalogue and measure it")
    p.add_argument("action", choices=["add"]); p.add_argument("folder"); p.add_argument("--name", required=True)
    p.add_argument("--licence"); p.add_argument("--paid-ads", choices=["yes", "no", "unverified"], default="unverified")
    p.add_argument("--catalogues"); p.add_argument("--tags-csv", help="filename,tags: their own mood or use words per track")
    p = sub.add_parser("shortlist", help="(v2.68.0) two or three cues to audition, from cleared music, with reasons")
    p.add_argument("job"); p.add_argument("--mood", default="", help="the brief's mood words, in the person's words")
    p.add_argument("--catalogues"); p.add_argument("-n", type=int, default=3)
    p.add_argument("--all-licences", action="store_true", help="include music not cleared for paid ads (internal work)")
    h = sub.add_parser("hits"); hs = h.add_subparsers(dest="sub")
    p = hs.add_parser("init"); p.add_argument("job"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("fit"); p.add_argument("job"); p.add_argument("--track"); p.add_argument("--engine", default="auto")
    p = sub.add_parser("render"); p.add_argument("job"); p.add_argument("--pick", type=int)
    p = sub.add_parser("rebuild"); p.add_argument("job"); p.add_argument("--pick", type=int)
    p = sub.add_parser("stems"); p.add_argument("job"); p.add_argument("--engine", default="auto")
    p = sub.add_parser("arrange"); p.add_argument("job")
    p = sub.add_parser("check"); p.add_argument("job")
    p = sub.add_parser("bed"); p.add_argument("job"); p.add_argument("--track"); p.add_argument("--voice")
    p.add_argument("--length", type=float); p.add_argument("--under-db", type=float)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "library":
        r = library_add(a.folder, a.name, a.licence, a.paid_ads, a.catalogues, tags_csv=a.tags_csv)
        b = r["built"]
        print(f"{b['catalogue']}: {b['files']} track(s) catalogued, paid ads {a.paid_ads}"
              + (f" — {r['left']} left to measure: run the same command again" if r["left"] else " — measured"))
        return 3 if r["left"] else 0
    if a.cmd == "shortlist":
        r = shortlist(a.job, a.mood, a.catalogues, a.n, a.all_licences)
        if not r["cues"]:
            print(r["message"]); return 1
        for k, c in enumerate(r["cues"], 1):
            print(f"{k}. {c['library']} · {c['rel']} · paid ads {c['paid_ads']}\n   " + "; ".join(c["why"] or ["—"]))
        print(r["message"]); return 0
    if a.cmd == "map":
        m = map_track(a.track, a.job, a.engine, a.force)
        print(f"{m['file']}: {m['engine']} grid, {m['tempo']:.1f} BPM, {m['meter']}/4, {len(m['bars'])} bars, "
              f"{len(m['phrases'])} phrases, key {m['key']['name']} ({m['key']['camelot']}, advisory), ends with a "
              f"{m['ending']['kind']} at {m['ending']['t']} s; downbeat confidence {m['confidence']['downbeats']}")
        return 0
    if a.cmd == "hits" and a.sub == "init":
        print(rel(a.job, hits_init(a.job, a.force))); return 0
    if a.cmd == "fit":
        F = fit(a.job, a.track, a.engine)
        print(fit_md(F)); return 0
    if a.cmd == "render":
        F = render(a.job, a.pick)
        print(f"{F['render']['file']} — a preview to listen to, never imported into Resolve")
        print(f"  {REBUILD}, REBUILD.md and 07-edit/{MUSIC_COPY}: the original rebuilt in Resolve"); return 0
    if a.cmd == "rebuild":
        RB = rebuild(a.job, a.pick)
        print(f"{REBUILD} and REBUILD.md: {len(RB['segments'])} segment(s) of {RB['original']['file']}, "
              f"{len(RB['seams'])} seam(s), " + (f"the end faded at {RB['end']['t_s']} s" if RB["end"].get("trim")
                                                 else "the track's own ending")
              + ("" if RB["placed_by_script"] else f", speed ×{RB['ratio']:.4f} (placed whole: retime first)"))
        offs = [s for s in RB["segments"] if abs(s.get("offset_ms") or 0) >= 1.0]
        if offs:
            print("  whole-frame placement: slip in Fairlight (REBUILD.md) — " +
                  "; ".join(f"segment {s['k']} {abs(s['offset_ms']):g} ms {'later' if s['offset_ms'] < 0 else 'earlier'}"
                            for s in offs))
        print(f"  07-edit/{MUSIC_COPY} places the original's segments on A5; crossfades and fades in Fairlight by "
              f"computer control"); return 0
    if a.cmd == "stems":
        S = stems(a.job, a.engine)
        print(f"{S['source']}: {', '.join(S['stems'])}"); return 0
    if a.cmd == "arrange":
        F = arrange(a.job)
        print(f"{F['render']['file']} — a preview; REBUILD.md lists the arrangement for Fairlight"); return 0
    if a.cmd == "bed":
        r = bed(a.job, a.track, a.voice, a.length, a.under_db)
        print(f"{r['file']}: {r['length_s']} s" + (f", head trimmed {r.get('src_in_s')} s" if r.get("src_in_s") else "")
              + (f", one seam {r['seam_out_s']}→{r['seam_in_s']} s (at {r['seam_video_s']} s in the ad)" if r.get("removed_s") else "")
              + f", ride {r['ride_range_db']} dB"
              + (f", {r['bed_under_voice_measured_db']} dB under the voice (target {r['under_voice_db']}, {r['under_source']})"
                 if r.get("voice") else f" — {r.get('note')}"))
        print("  06-music/bed/BED.json — the level plan for Fairlight, by computer control; the .bed.wav is a preview, "
              "never imported into Resolve")
        return 0
    if a.cmd == "check":
        P, W = check_job(a.job)
        for x in P:
            print("REFUSE", x)
        for x in W:
            print("NOTE  ", x)
        return 1 if P else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
