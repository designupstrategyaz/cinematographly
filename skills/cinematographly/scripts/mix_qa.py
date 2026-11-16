#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""mix_qa.py — the export audio gate: the mix measured from its stems and its final file before it ships.

Author, 2026-10-26, on the SFX research and jury (lab record lab-00012 (not shipped)): build *"Export
audio gate"*, *"Native audio as guide only"*, *"SFX licence manifest"* and *"Room tone and ambience
continuity"*. `gate.py approve export` runs `check` and refuses while any render in 10-export/ has no
passing mix report about its exact bytes, or the audio manifest has a problem.

What `measure` reads
--------------------
  --export    the final file, as it ships (after the AAC encode)
  --dialogue  the dialogue stem: every line, post-fader, as it plays in the mix
  --bed       the mix with the dialogue muted, DUCKING ON — the bed as the viewer hears it. Not the
              undipped music stem a language version needs (editing-and-audio.md, the M&E): that one
              has no ducking in it, so it says nothing about the gap the viewer hears
  --music / --ambience / --voices   optional stems of the same kind (ducking on), each held to its
              own floor; `--voices` is any other voice under the line (voice over voice)

What it checks (FAIL refuses the export; WARN is a finding for the mixer)
-------------------------------------------------------------------------
  stems match     the dialogue and the bed sum to the export, within 1 LU — or the report is about
                  some other mix
  VO over bed     the dialogue's loudness over the bed's while the dialogue speaks (the windows
                  where the dialogue stem is within 10 LU of its own level), against the floor
  phone           the same, after a phone-speaker simulation (mono, 300 Hz–7 kHz)
  short-term      no 3 s window louder than the export's integrated level + 5 LU
  mono fold-down  the export loses no more than 3 dB folded to mono, and the dialogue windows are not
                  out of phase
  room tone       the bed (or the ambience stem) never drops to silence (−60 LUFS for 0.4 s) outside a
                  planned hole, and has no dropout at a cut; clicks at a cut on the dialogue and
                  ambience stems are WARN; in the drama lane, an ambience level that jumps more than
                  3 LU across a cut inside one scene is WARN
  native audio    (v2.49.0) a clip's own diegetic sound is KEPT by default: the check reports which takes are
                  heard in the export and passes. With the job's project switch `guide-audio` the old rule
                  holds: a non-dialogue take heard in the export FAILS unless the manifest approves it

The audio manifest (`09-qa/mix/AUDIO-MANIFEST.md`, `manifest` scaffolds it, `licences` checks it):
every audio file under 05-voice/, 06-music/ and 06-sfx/ has a row, every row a licence that covers
paid advertising, every AI-made row its tool, version, plan and region, nothing a known block names
(`assets/ai-audio-licences.json`), and every native-audio row a director's approval.
The `channels` column: on each licensed music, sfx, ambience or foley cue, the number of
channels its plan covers (the accounts or outlets it may be published on — not audio channels), or
`unlimited`. `licences --channels N` WARNs where the delivery runs on more channels than a cue's plan
covers, and WARNs on a licensed cue with the column missing. These are warnings: they never change the
exit code and never reach `check`, which `approve export` refuses on.

Usage
-----
  python3 mix_qa.py measure <job> --export 10-export/x_master_v001_9x16.mp4 \\
      --dialogue 09-qa/mix/x_stem-d.wav --bed 09-qa/mix/x_bed.wav [--ambience …] [--lane drama]
  python3 mix_qa.py manifest <job>      # write or refresh the manifest's rows
  python3 mix_qa.py licences <job>      # exit 1 on a problem
  python3 mix_qa.py licences <job> --channels 3   # + WARN where a cue's plan covers fewer channels
  python3 mix_qa.py check <job>         # what `approve export` still needs (exit 1 if anything)
  python3 mix_qa.py wave <job> --mix 10-export/x_master_v001_9x16.mp4   # the waveform sync proof (v2.46)
  python3 mix_qa.py --selftest

The waveform sync proof (`wave`, v2.46): the whole mix as one waveform picture, 1800 × 280, with a faint line
every second and one line per picture event, read from the job by the same code as the event sheet
(contact_sheet.py events): cuts and transitions grey, must-hits and the button orange, placed sounds white,
title anchors blue. Each hit's attack should sit on or just after its line. → 09-qa/mix/WAVE-<sha8>.png and
.json (each line's id, time and x). What it cannot do: measure the offsets (`sfx_conform.py verify` and
`music_fit.py check` do) or hear; it is the one picture of sync across the whole cut, for a person to read.

Every threshold below carries its source tag; the [assumed] ones are tunable and wait for real mixes
to calibrate them. A floor can be changed for one job with `--floor-music N --why "<reason>"`; the
reason goes into the report.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, math, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import switches as SW  # noqa: E402  (v2.49.0: `guide-audio` restores native-audio-as-guide for one job)
SR = 48000

# the floors: the dialogue's loudness over the element's while the dialogue speaks, in LU
FLOORS = {"music": 14.0, "ambience": 19.0, "voices": 20.0}
FLOOR_TAGS = {
    "music": "[PRIMARY · Torcoli et al., JAES 67(12) 2019: ≥ 10 LU over music for experts; non-experts preferred "
             "about 4 LU more]",
    "ambience": "[PRIMARY · Torcoli et al. 2019: ≥ 15 LU over ambience for experts, + 4 LU for non-experts]",
    "voices": "[PRIMARY · Geary et al., JAES 68(11) 2020: recommend ≥ 20 LU, voice over voice]"}
OLDER_PLUS = 2.0        # `--audience 45+`: listeners 57+ preferred larger gaps (Geary 2020, voice over voice);
                        # no measured figure over music or ambience, so +2 LU is [assumed]
ACTIVE_BELOW = 10.0     # a dialogue window counts as speaking within this many LU of the stem's level [assumed]
ACTIVE_FLOOR = -50.0    # …and above this absolute level, LUFS [assumed]
ST_HEADROOM = 5.0       # max short-term ≤ integrated + 5 LU [PRIMARY · EBU R 128 s1 V3 2020: −18 LUFS max
                        # short-term at −23 integrated; applied here relative to the export's own level]
STEMS_TOL = 1.0         # the stems' sum within 1 LU of the export [assumed]
STEMS_P95 = 1.5         # …and 95% of its 400 ms windows within 1.5 LU of the export's (AAC noise is far less) [assumed]
MONO_LOSS = -3.0        # dB; uncorrelated stereo folds down at −3 dB, so more loss is cancellation [assumed]
PHONE = (300, 7000)     # Hz; the research found no 2024–26 measurement of phone speakers [assumed]
SILENCE_LUFS, SILENCE_S = -60.0, 0.4    # the same floor export_qc.py uses for a silent run
DROP_DB, DROP_MS, DROP_WIN = -40.0, 20, 0.25   # a dropout at a cut: 20 ms 40 dB under its neighbourhood [assumed]
CLICK_X, CLICK_WIN = 12.0, 0.5          # a sample step 12× the local median step, near a cut [assumed]
ROOM_JUMP = 3.0         # LU; the ambience level either side of a cut inside one scene [assumed]
CENTRE_DB = 1.0         # (3.2.0) dialogue: left and right energy within this while it speaks [assumed]
FIRST_WORD_S = 0.10     # (3.2.0) an SFX attack this close to a line's first syllable masks it [assumed]
LINE_GAP_S = 0.20       # (3.2.0) a line starts after at least this much silence on the dialogue stem [assumed]
NATIVE_NCC = 0.3        # normalised cross-correlation that says a clip's own audio is in the mix [assumed]
AUDIO_DIRS = ("05-voice", "06-music", "06-sfx")
AUDIO_EXT = (".wav", ".mp3", ".aif", ".aiff", ".flac", ".m4a", ".ogg", ".opus")
VIDEO_EXT = (".mp4", ".mov", ".mxf")
MANIFEST = os.path.join("09-qa", "mix", "AUDIO-MANIFEST.md")
COLS = ["file", "role", "source", "licence", "paid ads", "tool", "version", "plan", "region", "approved",
        "channels"]                     # appended last, so a manifest written before it still reads
ROLES = ("vo", "dialogue", "sfx", "foley", "ambience", "music", "native")
# a licensed CUE: a music, sfx, ambience or foley file used under someone else's licence. Its plan
# covers a number of channels (the accounts or outlets it may be published on), and the delivery's count must
# fit inside it. Voices, native audio and first-party recordings are not cues here.
CUE_ROLES = ("music", "sfx", "ambience", "foley")
FIRST_PARTY = ("own-recording", "client-supplied", "talent:")


# ⚡ THE CLIENT'S AUDIO SETTINGS (a supplement ad job, 2026-10-28). The measured "correct" bed — 13–18 dB under the voice —
# was "too loud" for one client; the owner settled about 38 dB under, "barely noticeable". So the bed level, the SFX density
# and the SFX targets are the client's, in `audio.<client>.json` beside the profile the job's CHECKPOINT names, and
# the skill's numbers are only the fallback.
CLIENT_AUDIO_DEFAULT = {"music_under_voice_db": 16.0, "sfx_density_per_min": None, "sfx_targets": {}}


def client_audio(job: str) -> dict:
    """The job's client audio settings: `audio.<client>.json` beside the profile (CHECKPOINT `Client:`), over the
    defaults. {} fields fall back; `_source` says where they came from."""
    out = dict(CLIENT_AUDIO_DEFAULT, _source="default")
    cp = os.path.join(job, "00-brief", "CHECKPOINT.md")
    try:
        m = re.search(r"^Client:\s*(\S+)", open(cp, encoding="utf-8").read(), re.M)
    except OSError:
        m = None
    if not m:
        return out
    client = m.group(1)
    base = os.path.basename(client)
    stem = base[:-3] if base.endswith(".md") else base
    dirs = [os.path.dirname(client)] if os.path.isabs(client) else []
    try:
        import cine_home as _ch
        cfg = _ch.config_dir("clients_dir")
    except ImportError:
        cfg = None
    dirs += [d for d in (os.environ.get("CINE_CLIENTS") or cfg,) if d]
    a_ = os.path.abspath(job)                      # a `_cine-clients/` above the job, as gate.find_profile looks
    for _ in range(12):
        dirs.append(os.path.join(a_, "_cine-clients"))
        if os.path.dirname(a_) == a_:
            break
        a_ = os.path.dirname(a_)
    dirs.append(os.path.join(SKILL, "clients"))
    for d in dirs:
        f = os.path.join(d, f"audio.{stem}.json")
        if os.path.isfile(f):
            try:
                out.update({k: v for k, v in json.load(open(f, encoding="utf-8")).items() if v is not None})
                out["_source"] = f
            except ValueError:
                pass
            break
    return out


def _need():
    import numpy as np
    return np


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def has_audio(path: str) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return bool(r.stdout.strip())


def pcm(path: str, sr: int = SR, ch: int = 2):
    """Float PCM, (n, ch)."""
    np = _need()
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", str(ch), "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.float32)
    return a.reshape(-1, ch) if a.size else np.zeros((0, ch), np.float32)


_FRAME = re.compile(r"t:\s*([\d.]+)\s+TARGET:.*?M:\s*(\S+)\s+S:\s*(\S+)")


def _num(v: str) -> float:
    try:
        x = float(v)
    except ValueError:
        return -120.0
    return -120.0 if x != x or x < -120 else x


def ebur(src, pre: str | None = None, sr: int = SR) -> dict:
    """ffmpeg ebur128 over a file or a float array (n, ch): momentary and short-term every 100 ms,
    integrated and true peak. `pre` is an ffmpeg filter run first (the phone simulation)."""
    np = _need()
    af = (pre + "," if pre else "") + "ebur128=peak=true"
    if isinstance(src, str):
        cmd, inp = ["ffmpeg", "-hide_banner", "-nostats", "-v", "verbose", "-i", src, "-vn", "-af", af,
                    "-f", "null", "-"], None
    else:
        a = np.ascontiguousarray(src, dtype=np.float32)
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-v", "verbose", "-f", "f32le", "-ar", str(sr), "-ac",
               str(a.shape[1]), "-i", "-", "-af", af, "-f", "null", "-"]
        inp = a.tobytes()
    r = subprocess.run(cmd, input=inp, capture_output=True)
    err = r.stderr.decode("utf-8", "replace")
    t, M, S = [], [], []
    for m in _FRAME.finditer(err):
        t.append(float(m.group(1))); M.append(_num(m.group(2))); S.append(_num(m.group(3)))
    summ = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    mi = re.search(r"I:\s+(-?[\d.]+|-inf)\s+LUFS", summ)
    mp = re.search(r"Peak:\s+(-?[\d.]+|-inf)\s+dBFS", summ)
    return {"t": t, "M": M, "S": S, "I": _num(mi.group(1)) if mi else -120.0,
            "TP": _num(mp.group(1)) if mp else None}


def energy_mean(vals) -> float:
    np = _need()
    v = np.asarray(vals, dtype=np.float64)
    if v.size == 0:
        return -120.0
    return float(10 * np.log10(np.mean(10 ** (v / 10.0)) + 1e-30))


def active_windows(d: dict) -> list:
    """Indices of the 100 ms frames where the dialogue speaks."""
    thr = max(ACTIVE_FLOOR, d["I"] - ACTIVE_BELOW)
    return [i for i, m in enumerate(d["M"]) if m >= thr]


def vo_gap(d: dict, b: dict, idx: list) -> dict:
    """The dialogue over the element, energy-averaged over the speaking windows, plus the spans where
    the window-by-window gap is under the floor (filled in by the caller)."""
    n = min(len(d["M"]), len(b["M"]))
    idx = [i for i in idx if i < n]
    if not idx:
        return {"gap": None, "windows": 0}
    return {"gap": round(energy_mean([d["M"][i] for i in idx]) - energy_mean([b["M"][i] for i in idx]), 2),
            "windows": len(idx), "per": [(i, d["M"][i] - b["M"][i]) for i in idx]}


def spans_under(per: list, floor: float, t: list, min_s: float = 0.5) -> list:
    out, cur = [], None
    for i, g in per:
        if g < floor:
            if cur and i == cur[1] + 1:
                cur[1] = i; cur[2] = min(cur[2], g)
            else:
                if cur:
                    out.append(cur)
                cur = [i, i, g]
        elif cur:
            out.append(cur); cur = None
    if cur:
        out.append(cur)
    res = []
    for a, b, g in out:
        if (b - a + 1) * 0.1 >= min_s and a < len(t):
            res.append({"from": round(max(0.0, t[a] - 0.4), 1), "to": round(t[min(b, len(t) - 1)], 1),
                        "worst_gap": round(g, 1)})
    return sorted(res, key=lambda r: r["worst_gap"])[:5]


def runs_below(vals: list, t: list, floor: float, min_s: float) -> list:
    out, start = [], None
    for i, v in enumerate(vals + [0.0]):
        if v < floor and i < len(vals):
            start = i if start is None else start
        elif start is not None:
            if (i - start) * 0.1 >= min_s:
                out.append((round(max(0.0, t[start] - 0.4), 2), round(t[i - 1], 2)))
            start = None
    return out


def in_holes(a: float, b: float, holes: list) -> bool:
    return any(h0 - 0.1 <= a and b <= h1 + 0.1 for h0, h1 in holes)


def read_holes(path: str | None) -> list:
    if not path:
        return []
    out = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"\s*([\d.]+)\s*-\s*([\d.]+)", ln)
        if m:
            out.append((float(m.group(1)), float(m.group(2))))
    return out


def dropouts(x, cuts: list, holes: list, sr: int = SR) -> list:
    """Any 20 ms within ±0.25 s of a cut that is 40 dB under the median of the second around it."""
    np = _need()
    fr = int(sr * 0.01)
    mono = x.mean(axis=1) if x.ndim == 2 else x
    out = []
    for c in cuts:
        a0, a1 = int(max(0, (c - 0.75) * sr)), int(min(len(mono), (c + 0.75) * sr))
        seg = mono[a0:a1]
        if len(seg) < fr * 10:
            continue
        nfr = len(seg) // fr
        rms = np.sqrt(np.mean(seg[:nfr * fr].reshape(nfr, fr) ** 2, axis=1) + 1e-20)
        db = 20 * np.log10(rms)
        ref = float(np.median(db))
        if ref < -70:
            continue            # nothing there to drop out of
        tt = a0 / sr + (np.arange(nfr) + 0.5) * 0.01
        near = np.abs(tt - c) <= DROP_WIN
        low = (db < ref + DROP_DB) & near
        run, best = 0, 0
        for v in low:
            run = run + 1 if v else 0
            best = max(best, run)
        if best * 10 >= DROP_MS and not in_holes(c - DROP_WIN, c + DROP_WIN, holes):
            out.append({"cut": round(c, 2), "ms": best * 10, "under_db": round(float(db[near].min() - ref), 1)})
    return out


def clicks(x, cuts: list, sr: int = SR) -> list:
    np = _need()
    mono = x.mean(axis=1) if x.ndim == 2 else x
    out = []
    for c in cuts:
        a0, a1 = int(max(0, (c - CLICK_WIN) * sr)), int(min(len(mono), (c + CLICK_WIN) * sr))
        seg = mono[a0:a1]
        if len(seg) < sr * 0.05:
            continue
        d = np.abs(np.diff(seg))
        med = float(np.median(d)) + 1e-9
        k = int(np.argmax(d))
        if d[k] > CLICK_X * med and d[k] > 10 ** (-40 / 20):
            out.append({"cut": round(c, 2), "at": round((a0 + k) / sr, 3), "step_x": round(float(d[k] / med), 1)})
    return out


SPEECH_FLOOR_DB = -60.0  # (3.2.0) a hop under this (dBFS power) is never speech, whatever the stem's loud level [assumed]


def _speaking(x, sr: int = SR, hop_s: float = 0.01, below: float = 25.0):
    """(3.2.0) Per 10 ms hop of a dialogue stem: is it speaking (within `below` dB of its loud level, and above the
    absolute floor, so a silent stem never "speaks")?"""
    np = _need()
    m = x.mean(axis=1) if x.ndim == 2 else x
    hop = int(sr * hop_s)
    n = len(m) // hop
    if n == 0:
        return np.zeros(0, bool)
    e = (m[:n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(axis=1)
    db = 10 * np.log10(e + 1e-12)
    return db >= max(float(np.percentile(db, 95)) - below, SPEECH_FLOOR_DB)


def dialogue_balance(x, sr: int = SR) -> dict:
    """(3.2.0) How far the dialogue sits off centre while it speaks: left minus right energy, in dB. A location
    reverb send is decorrelated by design, so this reads level only, never correlation."""
    np = _need()
    if x.ndim != 2 or x.shape[1] < 2:
        return {"lr_db": 0.0, "mono": True}
    sp = _speaking(x, sr)
    hop = int(sr * 0.01)
    if not sp.any():
        return {"lr_db": None, "mono": False}
    idx = np.repeat(sp, hop)[: len(x)]
    seg = x[: len(idx)][idx].astype(np.float64)
    l_, r_ = float((seg[:, 0] ** 2).sum()), float((seg[:, 1] ** 2).sum())
    return {"lr_db": round(10 * math.log10((l_ + 1e-12) / (r_ + 1e-12)), 2), "mono": False}


def line_onsets(x, sr: int = SR) -> list:
    """(3.2.0) The times a line starts on the dialogue stem: speech after at least LINE_GAP_S of quiet."""
    sp = _speaking(x, sr)
    gap = int(LINE_GAP_S / 0.01)
    out, quiet = [], gap
    for i, v in enumerate(sp):
        if v and quiet >= gap:
            out.append(round(i * 0.01, 3))
        quiet = 0 if v else quiet + 1
    return out


def first_word_hits(dialogue_x, sfx_path: str, sr: int = SR) -> list:
    """(3.2.0) SFX attacks within FIRST_WORD_S of a line's first syllable: [(line_t, attack_t)]."""
    import sfx_conform as SC
    ons = line_onsets(dialogue_x, sr)
    att = [o["attack"] for o in SC.detect_onsets(SC.pcm(sfx_path))]
    return [(lt, round(a, 3)) for lt in ons for a in att if abs(a - lt) <= FIRST_WORD_S]


def fold_down(x, idx_vo: list | None = None) -> dict:
    """Loss folding the export to mono, and the L/R correlation in the dialogue windows."""
    np = _need()
    if x.ndim != 2 or x.shape[1] < 2 or len(x) == 0:
        return {"loss_db": None}
    L, R = x[:, 0].astype(np.float64), x[:, 1].astype(np.float64)
    e_avg = np.mean((L ** 2 + R ** 2) / 2) + 1e-20
    e_mono = np.mean(((L + R) / 2) ** 2) + 1e-20
    out = {"loss_db": round(float(10 * np.log10(e_mono / e_avg)), 2)}
    if idx_vo:
        cs = []
        for i in idx_vo:
            a, b = int(max(0, (i * 0.1 - 0.3) * SR)), int(min(len(L), (i * 0.1 + 0.1) * SR))
            l, r = L[a:b], R[a:b]
            if len(l) > 100 and np.std(l) > 1e-6 and np.std(r) > 1e-6:
                cs.append(float(np.corrcoef(l, r)[0, 1]))
        out["vo_corr"] = round(float(np.mean(cs)), 3) if cs else None
    return out


def find_in(mix8k, x8k, sr: int = 8000) -> tuple:
    """Best normalised cross-correlation of x inside the mix, over 2 s chunks of x: (ncc, t in the mix)."""
    np = _need()
    best = (0.0, None)
    n = len(mix8k)
    e = np.concatenate([[0.0], np.cumsum(mix8k.astype(np.float64) ** 2)])
    step = 2 * sr
    for c0 in range(0, max(1, len(x8k) - sr // 2), step):
        x = x8k[c0:c0 + step].astype(np.float64)
        m = len(x)
        if m < sr // 2 or n < m or np.sqrt(np.mean(x ** 2)) < 10 ** (-50 / 20):
            continue
        nfft = 1 << (n + m - 1).bit_length()
        corr = np.fft.irfft(np.fft.rfft(mix8k, nfft) * np.conj(np.fft.rfft(x, nfft)), nfft)[: n - m + 1]
        local = np.sqrt(np.maximum(e[m:] - e[:-m], 1e-12))[: n - m + 1]
        ncc = corr / (np.linalg.norm(x) * local + 1e-12)
        k = int(np.argmax(ncc))
        if ncc[k] > best[0]:
            best = (float(ncc[k]), round(k / sr, 2))
    return best


# --- the manifest --------------------------------------------------------------------------------
def read_manifest(job: str) -> list:
    p = os.path.join(job, MANIFEST)
    if not os.path.isfile(p):
        return []
    rows, cols = [], None
    for ln in open(p, encoding="utf-8"):
        if not ln.strip().startswith("|"):
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if cols is None:
            cols = [x.lower() for x in c]
            continue
        if all(set(x) <= set("-: ") for x in c):
            continue
        rows.append({k: (c[i] if i < len(c) else "") for i, k in enumerate(cols)})
    return rows


def audio_files(job: str) -> list:
    out = []
    for d in AUDIO_DIRS:
        for p in glob.glob(os.path.join(job, d, "**", "*"), recursive=True):
            if p.lower().endswith(AUDIO_EXT) and os.path.isfile(p) and "/_archive/" not in p.replace(os.sep, "/"):
                out.append(os.path.relpath(p, job).replace(os.sep, "/"))
    return sorted(out)


def _guess_role(rel: str) -> str:
    n = os.path.basename(rel).lower()
    for k, role in (("_vo", "vo"), ("_sfx", "sfx"), ("_mus", "music"), ("ambience", "ambience"),
                    ("roomtone", "ambience"), ("room-tone", "ambience"), ("foley", "foley")):
        if k in n:
            return role
    return "music" if rel.startswith("06-music") else ("sfx" if rel.startswith("06-sfx") else "vo")


def write_manifest(job: str) -> str:
    rows = {r.get("file"): r for r in read_manifest(job)}
    for f in audio_files(job):
        if not os.path.isfile(os.path.join(job, f + ".conform.json")):   # derived renders inherit their sources' rows
            row = rows.setdefault(f, {"file": f, "role": _guess_role(f)})
            side = os.path.join(job, f + ".licence.json")                 # `sfx_conform.py library pull` wrote it
            if os.path.isfile(side) and not (row.get("licence") or "").strip():
                try:
                    L = json.load(open(side, encoding="utf-8"))
                except ValueError:
                    L = {}
                row.update({"source": L.get("source", ""), "paid ads": L.get("paid_ads", ""),
                            "licence": (L.get("licence") or "") + (f" — {L['condition']}" if L.get("condition") else "")})
                # composer.py generated record writes the generator's tool, version, plan and region too (v2.40);
                # a sidecar that names its plan's channel count carries it across as well
                for k in ("tool", "version", "plan", "region", "channels"):
                    if L.get(k) and not (row.get(k) or "").strip():
                        row[k] = str(L[k])
    p = os.path.join(job, MANIFEST)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    L = ["# Audio manifest — every audio file in the mix, and the licence that lets it ship", "",
         "One row per file. `role`: " + " · ".join(ROLES) + ". `source`: own-recording · library:<name> · "
         "ai:<tool> · client-supplied · talent:<name>. `paid ads`: yes, only when the licence covers paid "
         "advertising. AI rows also need `tool`, `version`, `plan` and `region` (where the ad runs, ISO codes). "
         "A `native` row (a clip's own audio kept in the mix) needs `approved`: who, and their words. "
         "`channels`: on a licensed music, sfx, ambience or foley cue, the number of channels its plan covers "
         "(or `unlimited`); `mix_qa.py licences <job> --channels N` warns when the delivery runs on more. "
         "Checked by `mix_qa.py licences` (editing-and-audio.md, the mix gate).", "",
         "| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    for f in sorted(rows):
        r = rows[f]
        L.append("| " + " | ".join((r.get(k) or "").replace("|", "/") for k in COLS) + " |")
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return p


def _rules() -> dict:
    return json.load(open(os.path.join(SKILL, "assets", "ai-audio-licences.json"), encoding="utf-8"))


def licence_problems(job: str) -> list:
    P = []
    rows = read_manifest(job)
    if not os.path.isfile(os.path.join(job, MANIFEST)):
        return [f"no audio manifest — `mix_qa.py manifest <job>` writes {MANIFEST} with a row per audio file; "
                f"fill in each licence"]
    listed = {r.get("file", "") for r in rows}
    names = {os.path.basename(r.get("file", "")) for r in rows}
    for f in audio_files(job):
        # a conformed render (sfx_conform.py) is derived: its licence is its sources' rows
        sc = os.path.join(job, f + ".conform.json")
        if os.path.isfile(sc):
            try:
                srcs = json.load(open(sc, encoding="utf-8")).get("sources") or []
            except ValueError:
                srcs = []
            for src in srcs:
                sf = str(src.get("file") or "")
                if sf not in listed and os.path.basename(sf) not in names:
                    P.append(f"{f}: conformed from {sf}, which has no manifest row — the render inherits its licence")
            try:
                room = json.load(open(sc, encoding="utf-8")).get("room") or {}
            except ValueError:
                room = {}
            if room.get("rel") and str(room.get("paid_ads", "")).lower() == "no":
                P.append(f"{f}: its room is {room.get('library')}: {room.get('rel')}, whose licence does not cover paid "
                         f"ads — conform again with another space or --room synthetic")
            continue
        if f not in listed:
            P.append(f"{f}: in the job and not in the manifest — add its row (`mix_qa.py manifest <job>`)")
    R = _rules()
    eu = set(R.get("eu_regions", []))
    for r in rows:
        f, role = r.get("file", ""), (r.get("role") or "").lower()
        src, tool = (r.get("source") or "").lower(), (r.get("tool") or "").strip()
        if not f:
            continue
        if not os.path.isfile(os.path.join(job, f)):
            P.append(f"{f}: listed and not on disk — remove the row or restore the file")
        if role not in ROLES:
            P.append(f"{f}: role {role!r} — one of {', '.join(ROLES)}")
        if role == "native":
            if SW.on(job, "guide-audio") and not (r.get("approved") or "").strip():
                P.append(f"{f}: the clip's own audio stays in the mix only with the director's approval — "
                         f"`approved`: who, and their words (native audio is a guide track by default)")
            continue
        if not (r.get("licence") or "").strip():
            P.append(f"{f}: no licence named")
        if (r.get("paid ads") or "").strip().lower() not in ("yes", "y"):
            P.append(f"{f}: `paid ads` is not yes — the licence must cover paid advertising")
        if src.startswith("ai") or tool:
            miss = [k for k in ("tool", "version", "plan", "region") if not (r.get(k) or "").strip()]
            if miss:
                P.append(f"{f}: AI-made, and no {', '.join(miss)} — the licence depends on them")
        regions = {x.strip().upper() for x in re.split(r"[,;/ ]+", r.get("region") or "") if x.strip()}
        for rule in R.get("rules", []):
            if not re.search(rule["tool"], tool + " " + src, re.I):
                continue
            hit = False
            if rule["block"] == "always":
                hit = True
            elif rule["block"] == "region":
                bad = set()
                for g in rule.get("regions", []):
                    bad |= eu if g == "@eu" else {g}
                hit = bool(regions & bad) or not regions
            elif rule["block"] == "plan":
                hit = (r.get("plan") or "").strip().lower() in rule.get("plans", [])
            elif rule["block"] == "version":
                hit = bool(re.search(rule.get("version_re", "$^"), r.get("version") or "", re.I))
            if hit:
                P.append(f"{f}: BLOCKED — {tool or src}: {rule['why']} {rule['source']}")
    return P


def _plan_channels(v: str):
    """A row's `channels` cell: an int, float('inf') for `unlimited`, or None when unreadable/empty."""
    s = (v or "").strip().lower()
    if s in ("unlimited", "any", "∞"):
        return float("inf")
    return int(s) if s.isdigit() and int(s) > 0 else None


def licence_warnings(job: str, channels: int | None = None) -> tuple:
    """(warnings, infos) for the channels each licensed cue's plan covers.

    WARN, never a refusal: these do not enter licence_problems() or check_job(), which `gate.py approve
    export` refuses on. ⛔ `channels` here is distribution channels (the accounts or outlets the film is
    published on), not audio channels: a preset's `channels: 2` in delivery-formats.json is stereo and is
    not read. Nothing in the job lists the delivery's channels in a form a script can count (the CHECKPOINT
    `Format:` names presets; the profile's `Platforms:` line is prose), so the count is `--channels N`."""
    W, I = [], []
    if not os.path.isfile(os.path.join(job, MANIFEST)):
        return W, I
    cues = 0
    for r in read_manifest(job):
        f, role = r.get("file", ""), (r.get("role") or "").strip().lower()
        src = (r.get("source") or "").strip().lower()
        if not f or role not in CUE_ROLES or src.startswith(FIRST_PARTY):
            continue
        cues += 1
        raw = (r.get("channels") or "").strip()
        n = _plan_channels(raw)
        if "channels" not in r or not raw:
            W.append(f"{f}: no `channels` — write the number of channels its plan covers (or `unlimited`), so the "
                     f"delivery can be checked against it")
        elif n is None:
            W.append(f"{f}: `channels` {raw!r} is not a number — the channels its plan covers, or `unlimited`")
        elif channels is not None and channels > n:
            W.append(f"{f}: the delivery runs on {channels} channel(s) and this cue's plan covers {n} — a plan "
                     f"that covers them, or a licence for the rest, before it ships")
    if cues and channels is None:
        I.append(f"the delivery's channel count was not given — pass --channels N (the accounts or outlets the film "
                 f"is published on); {cues} licensed cue(s) were not checked against it")
    return W, I


# --- the selected takes, for the native-audio check -------------------------------------------------
def selected_takes(job: str) -> list:
    """(shot, take file, its clip prompt) for every shot in the cut, from the motion reports."""
    try:
        import motion_qa as MQ
        shots = MQ.selected_shots(job)
    except Exception:
        shots = []
    out = []
    for s in shots:
        rp = os.path.join(job, "09-qa", "motion", f"{s}.motion.json")
        try:
            f = json.load(open(rp, encoding="utf-8")).get("file")
        except (OSError, ValueError):
            continue
        if f and os.path.isfile(os.path.join(job, f)):
            out.append((s, f, os.path.join(job, "01-script", "prompts", f"{s}.clip.prompt.md")))
    return out


def is_dialogue_prompt(prompt: str) -> bool:
    if not os.path.isfile(prompt):
        return False
    txt = open(prompt, encoding="utf-8").read()
    head = txt.split("---", 2)[1] if txt.startswith("---") else ""
    return bool(re.search(r"(?m)^type:\s*dialogue\b", head) or re.search(r"(?m)^(vo|line):\s*\S", head)
                or "[SPEECH]" in txt)


# --- measure -------------------------------------------------------------------------------------
def _scenes(spec: str | None) -> list:
    groups = []
    for g in re.split(r"\s*;\s*", spec or ""):
        ids = set()
        for tok in re.split(r"\s*,\s*", g.strip()):
            m = re.match(r"^([A-Za-z]+)(\d+)-\1?(\d+)$", tok)
            if m:
                ids |= {f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)}
            elif tok:
                ids.add(tok)
        if ids:
            groups.append(ids)
    return groups


def cut_list(job: str, cuts_file: str | None) -> list:
    """[(t, from, to)] — from a cut list, or the newest motion joins report."""
    if cuts_file:
        return [(float(m.group(1)), None, None) for m in
                (re.match(r"\s*([\d.]+)", ln) for ln in open(cuts_file, encoding="utf-8")) if m]
    js = sorted(glob.glob(os.path.join(job, "09-qa", "motion", "*.joins.json")), key=os.path.getmtime)
    if not js:
        return []
    try:
        d = json.load(open(js[-1], encoding="utf-8"))
    except ValueError:
        return []
    return [(float(j["t"]), j.get("from"), j.get("to")) for j in d.get("joins", []) if j.get("t") is not None]


def measure(job: str, export: str, dialogue: str | None, bed: str | None, music=None, ambience=None,
            voices=None, audience="general", lane="ads", holes_file=None, cuts_file=None, scenes=None,
            no_vo_why=None, floors_over=None, why=None, sfx=None) -> dict:
    np = _need()
    rel = lambda p: os.path.relpath(p, job).replace(os.sep, "/") if p else None
    checks, findings = [], []

    def C(name, status, value=None, want=None, detail=""):
        checks.append({"name": name, "status": status, "value": value, "want": want, "detail": detail})
    floors = {k: v + (OLDER_PLUS if audience == "45+" else 0.0) for k, v in FLOORS.items()}
    for k, v in (floors_over or {}).items():
        if v is not None:
            floors[k] = float(v)
    if floors_over and any(v is not None for v in floors_over.values()) and not (why or "").strip():
        raise SystemExit("error: a changed floor needs --why (it goes into the report)")
    holes = read_holes(holes_file)
    cuts = cut_list(job, cuts_file)
    rep = {"export": rel(export), "export_sha256": sha256_file(export),
           "measured": dt.datetime.now().isoformat(timespec="minutes"), "audience": audience, "lane": lane,
           "floors": floors, "floor_tags": FLOOR_TAGS, "floors_why": why or "", "holes": holes,
           "cuts": [c[0] for c in cuts],
           "stems": {k: ({"file": rel(v), "sha256": sha256_file(v)} if v else None)
                     for k, v in (("dialogue", dialogue), ("bed", bed), ("music", music), ("ambience", ambience),
                                  ("voices", voices), ("sfx", sfx))}}
    if not has_audio(export):
        C("audio stream", "FAIL", detail="the export has no audio stream")
        return _finish(job, export, rep, checks, findings)
    E = ebur(export)
    X = pcm(export)
    # ⛔ the stems first: a report about some other mix measures nothing
    if no_vo_why:
        rep["no_vo"] = no_vo_why
        C("VO over bed", "N/A", detail=f"no dialogue in this film: {no_vo_why}")
    else:
        if not (dialogue and bed):
            C("stems", "FAIL", detail="--dialogue and --bed are both needed (or --no-vo --why, for a film with no "
                                      "dialogue)")
            return _finish(job, export, rep, checks, findings)
    D = pcm(dialogue) if dialogue else None
    B = pcm(bed) if bed else None
    if B is not None:
        n = min(len(B), len(D)) if D is not None else len(B)
        summed = (B[:n] + D[:n]) if D is not None else B[:n]
        Es_ = ebur(summed)
        diff = round(Es_["I"] - E["I"], 2)
        # window by window too: the integrated level hides a bed that changed under a loud voice
        k = min(len(Es_["M"]), len(E["M"]))
        dm = sorted(abs(Es_["M"][i] - E["M"][i]) for i in range(k) if max(Es_["M"][i], E["M"][i]) > -60)
        p95 = round(dm[int(0.95 * (len(dm) - 1))], 2) if dm else 0.0
        okm = abs(diff) <= STEMS_TOL and p95 <= STEMS_P95
        C("stems match the export", "PASS" if okm else "FAIL", diff, f"±{STEMS_TOL:g} LU, 95% of windows within "
          f"{STEMS_P95:g} LU", f"window difference p95 {p95} LU" + ("" if okm else " — the stems do not sum to this "
          "export: render both from the timeline that made it, with the ducking on"))
    idx = []
    if D is not None:
        Ed = ebur(D)
        idx = active_windows(Ed)
        if not idx:
            C("VO over bed", "FAIL", detail="the dialogue stem never speaks above "
                                            f"{max(ACTIVE_FLOOR, Ed['I'] - ACTIVE_BELOW):.0f} LUFS — wrong file?")
        else:
            for name, stem, floor in (("bed", B, floors["music"]), ("music", music, floors["music"]),
                                      ("ambience", ambience, floors["ambience"]), ("voices", voices, floors["voices"])):
                if stem is None:
                    continue
                Es = ebur(stem if isinstance(stem, np.ndarray) else pcm(stem))
                g = vo_gap(Ed, Es, idx)
                ok = g["gap"] is not None and g["gap"] >= floor
                C(f"VO over {name}", "PASS" if ok else "FAIL", g["gap"], f"≥ {floor:g} LU",
                  f"over {g['windows']} speaking windows")
                sp = spans_under(g.get("per", []), floor, Ed["t"])
                if sp:
                    findings.append(f"VO over {name}: under {floor:g} LU at " +
                                    ", ".join(f"{s['from']}–{s['to']} s ({s['worst_gap']} LU)" for s in sp))
            if B is not None:
                phone = f"pan=mono|c0=0.5*c0+0.5*c1,highpass=f={PHONE[0]},lowpass=f={PHONE[1]}"
                gp = vo_gap(ebur(D, phone), ebur(B, phone), idx)
                okp = gp["gap"] is not None and gp["gap"] >= floors["music"]
                C("VO over bed on a phone", "PASS" if okp else "FAIL", gp["gap"], f"≥ {floors['music']:g} LU",
                  f"mono, {PHONE[0]} Hz–{PHONE[1] // 1000} kHz")
    # (3.2.0) where the dialogue sits, and the first word of each line kept clear of the effects
    if D is not None:
        bal = dialogue_balance(D)
        if bal.get("mono"):
            C("dialogue in the centre", "PASS", 0.0, f"within ±{CENTRE_DB:g} dB", "the dialogue stem is mono")
        elif bal["lr_db"] is None:
            C("dialogue in the centre", "N/A", detail="the dialogue stem never speaks")
        else:
            okc = abs(bal["lr_db"]) <= CENTRE_DB
            C("dialogue in the centre", "PASS" if okc else "WARN", bal["lr_db"], f"within ±{CENTRE_DB:g} dB",
              "left minus right energy while it speaks" + ("" if okc else
                                                           f" — the voice leans {'left' if bal['lr_db'] > 0 else 'right'}: "
                                                           f"dialogue stays centred (editing-and-audio.md §7f)"))
        if sfx:
            hits = first_word_hits(D, sfx)
            C("first word clear of the effects", "PASS" if not hits else "WARN", len(hits), "0",
              "; ".join(f"a line at {lt} s, an effect at {at} s" for lt, at in hits[:5]) or
              f"no effect attack within {int(FIRST_WORD_S * 1000)} ms of a line's start")
        else:
            C("first word clear of the effects", "N/A", detail="not checked: no --sfx stem")
    # short-term ceiling, on the file that ships
    st = [(t, s) for t, s in zip(E["t"], E["S"]) if t >= 3.0]
    smax = max(st, key=lambda x: x[1]) if st else (None, -120.0)
    okst = smax[1] <= E["I"] + ST_HEADROOM
    C("short-term ceiling", "PASS" if okst else "FAIL", round(smax[1] - E["I"], 2), f"≤ +{ST_HEADROOM:g} LU",
      f"loudest 3 s ends at {smax[0]} s; integrated {E['I']} LUFS, true peak {E['TP']} dBFS")
    fd = fold_down(X, idx)
    if fd["loss_db"] is None:
        C("mono fold-down", "N/A", detail="the export is mono")
    else:
        okm = fd["loss_db"] >= MONO_LOSS and (fd.get("vo_corr") is None or fd["vo_corr"] >= 0)
        C("mono fold-down", "PASS" if okm else "FAIL", fd["loss_db"], f"≥ {MONO_LOSS:g} dB, dialogue windows in phase",
          f"L/R correlation in the dialogue windows {fd.get('vo_corr')}")
    # room tone: the bed never drops to silence, no dropout at a cut
    room = ambience or None
    Rm = pcm(room) if room else B
    if Rm is not None and len(Rm):
        Er = ebur(Rm)
        dur = Er["t"][-1] if Er["t"] else 0.0
        silent = [(a, b) for a, b in runs_below(Er["M"], Er["t"], SILENCE_LUFS, SILENCE_S)
                  if a > 0.5 and b < dur - 0.5 and not in_holes(a, b, holes)]
        C("room tone under every moment", "PASS" if not silent else "FAIL", len(silent), "0 silent runs",
          "; ".join(f"{a}–{b} s" for a, b in silent[:5]) or f"the {'ambience' if room else 'bed'} never goes silent")
        drops = dropouts(Rm, [c[0] for c in cuts], holes)
        C("no dropout at a cut", "PASS" if not drops else "FAIL", len(drops), "0",
          "; ".join(f"{d['cut']} s: {d['ms']} ms, {d['under_db']} dB" for d in drops[:5]) or
          (f"{len(cuts)} cuts checked" if cuts else "no cut list (motion_qa.py cut, or --cuts)"))
        if not cuts:
            findings.append("no cut list: dropouts and clicks at the cuts were not checked (run motion_qa.py cut, or "
                            "pass --cuts)")
        for name, stem in (("dialogue", D), ("ambience", pcm(ambience) if ambience else None)):
            if stem is not None and cuts:
                for k in clicks(stem, [c[0] for c in cuts]):
                    findings.append(f"click on the {name} stem near the cut at {k['cut']} s (at {k['at']} s, a step "
                                    f"{k['step_x']}× the local median) — listen")
    # the drama lane: one ambience per location, held across the scene
    if lane == "drama":
        if not ambience:
            C("ambience held across each scene", "FAIL", detail="a drama mix needs --ambience: the room-tone check "
                                                                "reads the ambience stem")
        else:
            groups = _scenes(scenes)
            Ea = ebur(pcm(ambience))
            jumps = []
            for t, a, b in cuts:
                if not (a and b and any(a in g and b in g for g in groups)):
                    continue
                pre = [s for tt, s in zip(Ea["t"], Ea["S"]) if t - 1.2 <= tt <= t - 0.2]
                post = [s for tt, s in zip(Ea["t"], Ea["S"]) if t + 0.2 <= tt <= t + 1.2]
                if pre and post:
                    j = round(energy_mean(post) - energy_mean(pre), 1)
                    if abs(j) > ROOM_JUMP:
                        jumps.append((t, a, b, j))
            C("ambience held across each scene", "PASS", len(jumps), f"≤ {ROOM_JUMP:g} LU per cut inside a scene",
              "" if groups else "no --scenes given: nothing grouped, nothing compared")
            for t, a, b, j in jumps:
                findings.append(f"ambience jumps {j:+} LU across the cut at {t} s ({a}→{b}), inside one scene — one bed "
                                f"per location, held across the scene")
    # native audio: a clip that is not dialogue is a guide track, never the mix
    mix8 = pcm(export, 8000, 1)[:, 0] if len(X) else None
    approved = {r.get("file"): r for r in read_manifest(job)
                if (r.get("role") or "").lower() == "native" and (r.get("approved") or "").strip()}
    heard, looked = [], 0
    for s, f, pr in selected_takes(job):
        if is_dialogue_prompt(pr) or not has_audio(os.path.join(job, f)):
            continue
        looked += 1
        x8 = pcm(os.path.join(job, f), 8000, 1)[:, 0]
        ncc, at = find_in(mix8, x8)
        if ncc >= NATIVE_NCC and f not in approved:
            heard.append(f"{s} ({f}): its own audio is in the mix (correlation {ncc:.2f} at {at} s)")
    if SW.on(job, "guide-audio"):
        C("native audio is a guide only", "PASS" if not heard else "FAIL", len(heard), "0 unapproved",
          "; ".join(heard) or f"{looked} non-dialogue take(s) with audio checked against the export")
    else:
        # v2.49.0 (2026-11-05): native diegetic sound is production sound; it is reported, never refused
        C("native audio kept", "PASS", len(heard), "kept by default (editing-and-audio.md §7d)",
          "; ".join(heard) or f"{looked} non-dialogue take(s) with audio checked; none heard in the export")
    return _finish(job, export, rep, checks, findings)


def _finish(job, export, rep, checks, findings) -> dict:
    rep["checks"], rep["findings"] = checks, findings
    rep["verdict"] = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    rep["thresholds_tag"] = "[assumed] where marked in mix_qa.py; the floors carry their sources"
    json.dump(rep, open(export + ".mix.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(export + ".mix.md", "w", encoding="utf-8").write(render_md(rep))
    return rep


def render_md(r: dict) -> str:
    L = [f"# Mix QA — {r['export']}", "", f"**{r['verdict']}** · audience {r['audience']} · lane {r['lane']} · "
         f"measured {r['measured']}", "", "| check | status | value | want | detail |", "|---|---|---|---|---|"]
    L += [f"| {c['name']} | {c['status']} | {c['value'] if c['value'] is not None else ''} | {c['want'] or ''} | "
          f"{(c['detail'] or '').replace('|', '/')} |" for c in r["checks"]]
    L += ["", "## Findings", ""] + ([f"- {f}" for f in r["findings"]] or ["- none"])
    if r.get("floors_why"):
        L += ["", f"Floors changed for this job: {r['floors_why']}"]
    L += ["", f"_{r['thresholds_tag']}_", ""]
    return "\n".join(L)


def check_job(job: str) -> list:
    P = []
    exp = os.path.join(job, "10-export")
    for v in sorted(p for p in glob.glob(os.path.join(exp, "*")) if p.lower().endswith(VIDEO_EXT)):
        rel = os.path.relpath(v, job)
        rp = v + ".mix.json"
        if not os.path.isfile(rp):
            P.append(f"{rel}: no mix report — `mix_qa.py measure <job> --export {rel} --dialogue <stem> --bed "
                     f"<mix minus dialogue>`")
            continue
        try:
            r = json.load(open(rp, encoding="utf-8"))
        except ValueError:
            P.append(f"{rel}: mix report unreadable"); continue
        if r.get("export_sha256") != sha256_file(v):
            P.append(f"{rel}: the file changed after its mix was measured — measure it again")
        elif r.get("verdict") != "PASS":
            bad = [c["name"] for c in r.get("checks", []) if c.get("status") == "FAIL"]
            P.append(f"{rel}: the mix FAILS — {', '.join(bad)} ({os.path.basename(v)}.mix.md)")
    P += licence_problems(job)
    return P


# --- selftest ------------------------------------------------------------------------------------
# ── the waveform sync proof (v2.46) ───────────────────────────────────────────────────────────────────────
WAVE_W, WAVE_H = 1800, 280
WAVE_LINE = {"cut": ("0x9a9a9a", 2), "transition": ("0x9a9a9a", 2), "hit": ("0xff8c1a", 3), "sfx": ("0xffffff", 2),
             "title": ("0x3d8bfd", 2)}


def _duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def wave(job: str, mix: str, out: str | None = None) -> dict:
    """The mix's waveform with every picture event drawn as a line. Events come from contact_sheet.job_events, the
    event sheet's own reader, so the two proofs can never disagree about where an event is."""
    import contact_sheet as CS
    dur = _duration(mix)
    if dur <= 0 or not has_audio(mix):
        raise SystemExit(f"error: {mix} has no audio to draw")
    events, notes = CS.job_events(job, dur)
    sha = sha256_file(mix)
    lines = []
    for e in events:
        if e["kind"] not in WAVE_LINE:
            continue
        x = int(round(min(max(float(e["at"]), 0.0), dur) / dur * (WAVE_W - 1)))
        lines.append({"id": e["id"], "kind": e["kind"], "t": e["at"], "x": x, "colour": WAVE_LINE[e["kind"]][0]})
    draw = [f"drawbox=x={int(round(k / dur * (WAVE_W - 1)))}:y=0:w=1:h={WAVE_H}:color=0x5a5f66@0.6:t=fill"
            for k in range(1, int(dur) + 1) if k < dur]
    for ln in sorted(lines, key=lambda l: ("cut", "transition", "title", "sfx", "hit").index(l["kind"])):
        c, w = WAVE_LINE[ln["kind"]]
        draw.append(f"drawbox=x={max(0, ln['x'] - w // 2)}:y=0:w={w}:h={WAVE_H}:color={c}@0.9:t=fill")
    fc = (f"[0:a]aformat=channel_layouts=mono,showwavespic=s={WAVE_W}x{WAVE_H}:colors=0x8fa3b5[w];"
          f"color=c=0x15171a:s={WAVE_W}x{WAVE_H}:d=1[bg];[bg][w]overlay=format=auto"
          + ("," + ",".join(draw) if draw else ""))
    dest = out or os.path.join(job, "09-qa", "mix", f"WAVE-{sha[:8]}.png")
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mix, "-filter_complex", fc, "-frames:v", "1", dest],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(dest):
        raise SystemExit(f"error: the waveform did not draw: {r.stderr.strip()[:300]}")
    rep = {"tool": "mix_qa.py wave", "mix": os.path.relpath(os.path.abspath(mix), os.path.abspath(job)), "mix_sha256": sha,
           "duration_s": round(dur, 3), "png": os.path.relpath(os.path.abspath(dest), os.path.abspath(job)),
           "size": [WAVE_W, WAVE_H], "lines": lines, "notes": notes,
           "legend": {"grey": "cut / transition", "orange": "must-hit, button", "white": "placed sound", "blue": "title anchor"},
           "made": dt.datetime.now().isoformat(timespec="seconds")}
    json.dump(rep, open(os.path.splitext(dest)[0] + ".json", "w", encoding="utf-8"), indent=1)
    return rep


def _wav(path: str, x) -> None:
    np = _need()
    a = np.ascontiguousarray(x, dtype=np.float32)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(a.shape[1]), "-i", "-",
                    "-c:a", "pcm_s24le", path], input=a.tobytes(), check=True)


def _mp4(path: str, x) -> None:
    np = _need()
    a = np.ascontiguousarray(x, dtype=np.float32)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(a.shape[1]), "-i", "-",
                    "-c:a", "aac", "-b:a", "192k", path], input=a.tobytes(), check=True)


def _band(rng, lo, hi, size):
    """Unit-RMS noise between lo and hi Hz."""
    np = _need()
    X = np.fft.rfft(rng.standard_normal(size))
    f = np.fft.rfftfreq(size, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, size)
    return y / (np.sqrt(np.mean(y ** 2)) + 1e-12)


def _synth(seconds: float = 12.0, seed: int = 1):
    """A dialogue stem (speech-band bursts, centred) and a bed (wide noise, decorrelated L/R)."""
    np = _need()
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR

    band = lambda lo, hi, size: _band(rng, lo, hi, size)
    env = ((t % 4.0) >= 1.0).astype(float)                 # speaks 3 s in every 4, from 1 s
    env[t > seconds - 0.5] = 0.0
    env *= 0.6 + 0.4 * np.sin(2 * np.pi * 3.0 * t) ** 2     # syllable-ish
    d = band(150, 5000, n) * env * 0.1
    D = np.stack([d, d], axis=1)
    B = np.stack([band(60, 12000, n), band(60, 12000, n)], axis=1) * 0.1 * 10 ** (-20 / 20)
    return D.astype(np.float32), B.astype(np.float32)


def selftest() -> int:
    np = _need()
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and cond
    st = lambda r, n: next((c for c in r["checks"] if c["name"] == n), {}).get("status")
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("05-voice", "06-music", "09-qa/mix", "09-qa/motion", "10-export", "03-clips", "01-script/prompts"):
            os.makedirs(os.path.join(job, d))
        D, B = _synth()
        dw, bw = os.path.join(job, "09-qa", "mix", "d.wav"), os.path.join(job, "09-qa", "mix", "b.wav")
        _wav(dw, D); _wav(bw, B)
        ex = os.path.join(job, "10-export", "x_master_v001_9x16.mp4")
        _mp4(ex, D + B)
        r = measure(job, ex, dw, bw)
        check("a clean mix passes: the stems sum to the export, the VO sits well over the bed, on a phone too",
              r["verdict"] == "PASS" and st(r, "VO over bed") == "PASS" and st(r, "VO over bed on a phone") == "PASS"
              and st(r, "stems match the export") == "PASS", json.dumps(r["checks"]))
        gap = next(c for c in r["checks"] if c["name"] == "VO over bed")["value"]
        check("the gap is measured, not guessed (the synthetic bed sits ~20 dB under)", 15 <= gap <= 26, str(gap))
        B2 = B * 10 ** (12 / 20)
        bw2 = os.path.join(job, "09-qa", "mix", "b2.wav"); _wav(bw2, B2)
        ex2 = os.path.join(job, "10-export", "x2.mp4"); _mp4(ex2, D + B2)
        r2 = measure(job, ex2, dw, bw2)
        check("a bed 12 dB hotter fails the floor, and names where", st(r2, "VO over bed") == "FAIL"
              and any("under" in f for f in r2["findings"]), json.dumps(r2["checks"]))
        r3 = measure(job, ex2, dw, bw)
        check("stems that are not this mix are refused", st(r3, "stems match the export") == "FAIL",
              json.dumps(r3["checks"]))
        # a voice whose weight is all below 300 Hz, over a bed in the presence band: fine on headphones,
        # buried on a phone speaker
        rng = np.random.default_rng(7)
        nn = len(D)
        envd = (np.abs(D[:, 0]) > 0).astype(np.float32)
        lowv = (_band(rng, 100, 300, nn) + 0.1 * _band(rng, 1000, 3000, nn)) * 0.1 * envd
        Dl = np.stack([lowv, lowv], axis=1).astype(np.float32)
        mid = _band(rng, 1000, 4000, nn) * 0.1 * 10 ** (-19 / 20)
        Bm = np.stack([mid, _band(rng, 1000, 4000, nn) * 0.1 * 10 ** (-19 / 20)], axis=1).astype(np.float32)
        dwl, bwm = os.path.join(job, "09-qa", "mix", "dl.wav"), os.path.join(job, "09-qa", "mix", "bm.wav")
        _wav(dwl, Dl); _wav(bwm, Bm)
        exl = os.path.join(job, "10-export", "xl.mp4"); _mp4(exl, Dl + Bm)
        rl = measure(job, exl, dwl, bwm)
        check("a bass-heavy voice over a presence-band bed passes full band and fails on a phone",
              st(rl, "VO over bed") == "PASS" and st(rl, "VO over bed on a phone") == "FAIL", json.dumps(rl["checks"][:3]))
        r45 = measure(job, ex, dw, bw, audience="45+")
        check("the 45+ audience raises the floors", r45["floors"]["music"] == FLOORS["music"] + OLDER_PLUS)
        try:
            measure(job, ex, dw, bw, floors_over={"music": 9})
            refused = False
        except SystemExit:
            refused = True
        check("a lowered floor without --why is refused", refused)
        # a loud stinger: one 3 s window far over a 30 s programme
        DL, BL = _synth(30.0, 4)
        loud = (DL + BL).copy()
        loud[int(24 * SR):int(27 * SR)] += np.random.default_rng(9).standard_normal((int(3 * SR), 2)).astype(np.float32) * 0.3
        dw3 = os.path.join(job, "09-qa", "mix", "d3.wav"); _wav(dw3, DL)
        ex3 = os.path.join(job, "10-export", "x3.mp4"); _mp4(ex3, loud)
        bw3 = os.path.join(job, "09-qa", "mix", "b3.wav"); _wav(bw3, loud - DL)
        r4 = measure(job, ex3, dw3, bw3)
        check("a 3 s window more than 5 LU over the programme fails the short-term ceiling",
              st(r4, "short-term ceiling") == "FAIL", json.dumps(r4["checks"]))
        # the bed out of phase between the channels
        Bp = B.copy(); Bp[:, 1] = -Bp[:, 0]
        bwp = os.path.join(job, "09-qa", "mix", "bp.wav"); _wav(bwp, Bp)
        exp_ = os.path.join(job, "10-export", "x4.mp4"); _mp4(exp_, D * 0.05 + Bp * 8)
        r5 = measure(job, exp_, None, bwp, no_vo_why="test: a bed alone")
        check("a mix that cancels when folded to mono fails", st(r5, "mono fold-down") == "FAIL",
              json.dumps(r5["checks"]))
        # a hole in the bed, and a dropout at a cut
        Bh = B.copy(); Bh[int(6.0 * SR):int(7.0 * SR)] = 0
        Bh[int(3.0 * SR):int(3.0 * SR) + int(0.03 * SR)] = 0
        bwh = os.path.join(job, "09-qa", "mix", "bh.wav"); _wav(bwh, Bh)
        exh = os.path.join(job, "10-export", "x5.mp4"); _mp4(exh, D + Bh)
        cl = os.path.join(job, "09-qa", "mix", "cuts.txt"); open(cl, "w").write("3.0\n8.5\n")
        r6 = measure(job, exh, dw, bwh, cuts_file=cl)
        check("a silent second in the bed and a 30 ms dropout at a cut both fail",
              st(r6, "room tone under every moment") == "FAIL" and st(r6, "no dropout at a cut") == "FAIL",
              json.dumps(r6["checks"]))
        hf = os.path.join(job, "09-qa", "mix", "HOLES.txt"); open(hf, "w").write("6.0-7.0 planned silence before the offer\n")
        r7 = measure(job, exh, dw, bwh, cuts_file=cl, holes_file=hf)
        check("a planned hole is allowed; the unplanned dropout still fails",
              st(r7, "room tone under every moment") == "PASS" and st(r7, "no dropout at a cut") == "FAIL",
              json.dumps(r7["checks"]))
        check("the drama lane needs its ambience stem", st(measure(job, ex, dw, bw, lane="drama"),
                                                          "ambience held across each scene") == "FAIL")
        Am = B * 0.5
        Am[int(8.5 * SR):] *= 10 ** (8 / 20)
        aw = os.path.join(job, "09-qa", "mix", "amb.wav"); _wav(aw, Am)
        open(os.path.join(job, "09-qa", "motion", "cut_v1.joins.json"), "w").write(json.dumps(
            {"joins": [{"t": 3.0, "from": "S1", "to": "S2"}, {"t": 8.5, "from": "S2", "to": "S3"}]}))
        r8 = measure(job, ex, dw, bw, ambience=aw, lane="drama", scenes="S1-S3")
        check("an ambience that jumps 8 LU across a cut inside one scene is named",
              any("jumps" in f and "8.5" in f for f in r8["findings"]), json.dumps(r8["findings"]))
        # native audio: a b-roll take whose own sound is in the mix
        clip = os.path.join(job, "03-clips", "S4_v1.mp4")
        _mp4(clip, B[int(2 * SR):int(6 * SR)] * 6)
        exn = os.path.join(job, "10-export", "x6.mp4")
        mixn = D + B
        mixn[int(4 * SR):int(8 * SR)] += B[int(2 * SR):int(6 * SR)] * 6
        _mp4(exn, mixn)
        bwn = os.path.join(job, "09-qa", "mix", "bn.wav"); _wav(bwn, mixn - D)
        open(os.path.join(job, "01-script", "prompts", "S4.clip.prompt.md"), "w").write(
            "---\nshot: S4\nkind: clip\ntype: broll\n---\n[MOTION]\nx\n")
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "w").write(
            "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n"
            "| t | S4 | selects | SELECT | the jar tips into the bin |\n")
        json.dump({"shot": "S4", "file": "03-clips/S4_v1.mp4"}, open(os.path.join(job, "09-qa", "motion", "S4.motion.json"), "w"))
        r9k = measure(job, exn, dw, bwn)
        check("v2.49: a b-roll take's own audio in the mix is KEPT and reported, not refused",
              st(r9k, "native audio kept") == "PASS" and any(c.get("n") == 1 or "S4" in json.dumps(c)
                                                              for c in r9k["checks"] if "native" in json.dumps(c)),
              json.dumps(r9k["checks"]))
        _ck = os.path.join(job, "00-brief", "CHECKPOINT.md")
        os.makedirs(os.path.dirname(_ck), exist_ok=True)
        _prev = open(_ck).read() if os.path.isfile(_ck) else None
        open(_ck, "a").write("\nSwitches: guide-audio — the client wants clean licensed stems throughout\n")
        r9 = measure(job, exn, dw, bwn)
        check("with `guide-audio`: a b-roll take's own audio in the mix fails", st(r9, "native audio is a guide only") == "FAIL",
              json.dumps(r9["checks"]))
        check("…and the same take is not found in a mix that does not use it",
              st(measure(job, ex, dw, bw), "native audio is a guide only") == "PASS")
        # the manifest
        open(os.path.join(job, "05-voice", "x_s1_0010_vo_host_v001.wav"), "wb").write(b"RIFF")
        open(os.path.join(job, "06-music", "x_mus_bed_v001.wav"), "wb").write(b"RIFF")
        check("no manifest → the export is refused, and says how to write one",
              any("no audio manifest" in p for p in licence_problems(job)))
        write_manifest(job)
        P = licence_problems(job)
        check("a scaffolded manifest still needs every licence",
              any("vo_host" in p and "no licence" in p for p in P) and any("paid ads" in p for p in P), json.dumps(P))
        mp = os.path.join(job, MANIFEST)
        hdr = open(mp).read().split("| file |")[0]

        def rows(*rs):
            open(mp, "w").write(hdr + "| " + " | ".join(COLS) + " |\n|" + "---|" * len(COLS) + "\n" +
                                "".join("| " + " | ".join(r) + " |\n" for r in rs))
        vo_ok = ["05-voice/x_s1_0010_vo_host_v001.wav", "vo", "ai:elevenlabs", "ElevenLabs terms, Creator plan", "yes",
                 "ElevenLabs", "eleven_v3", "creator", "RO", ""]
        mus_ok = ["06-music/x_mus_bed_v001.wav", "music", "library:Artlist", "Artlist Pro, social and paid", "yes",
                  "", "", "", "", ""]
        rows(vo_ok, mus_ok)
        check("a complete manifest is clean", licence_problems(job) == [], json.dumps(licence_problems(job)))
        # the channels a cue's plan covers against the delivery's: WARN only, never a refusal
        W0, I0 = licence_warnings(job)
        check("HR-11 a licensed music cue with no `channels` WARNs, and the voice row does not",
              len(W0) == 1 and "x_mus_bed" in W0[0] and "no `channels`" in W0[0], json.dumps(W0))
        check("HR-11 ...while the manifest stays clean: a warning never refuses", licence_problems(job) == [])
        check("HR-11 with no --channels the report says no cue was checked against the delivery",
              any("--channels N" in x for x in I0), json.dumps(I0))
        mus_c = mus_ok[:10] + ["3"]
        rows(vo_ok, mus_c)
        check("HR-11 a plan covering 3 channels passes a delivery on 2", licence_warnings(job, 2)[0] == [])
        W4 = licence_warnings(job, 4)[0]
        check("HR-11 ...and WARNs a delivery on 4, naming both counts",
              len(W4) == 1 and "4 channel(s)" in W4[0] and "covers 3" in W4[0], json.dumps(W4))
        rows(vo_ok, mus_ok[:10] + ["unlimited"])
        check("HR-11 `unlimited` covers any delivery", licence_warnings(job, 40)[0] == [])
        rows(vo_ok, mus_ok[:10] + ["three"])
        check("HR-11 an unreadable count WARNs", any("not a number" in w for w in licence_warnings(job, 2)[0]))
        rows(vo_ok, ["06-music/x_mus_bed_v001.wav", "music", "own-recording", "recorded on the shoot", "yes",
                     "", "", "", "", "", ""])
        check("HR-11 a first-party recording is not a licensed cue", licence_warnings(job, 9) == ([], []))
        hdr_line = [ln for ln in open(mp).read().splitlines() if ln.startswith("| file |")]
        write_manifest(job)
        check("HR-11 the scaffolded manifest carries the `channels` column",
              any(ln.startswith("| file |") and ln.rstrip().endswith("| channels |")
                  for ln in open(mp).read().splitlines()), str(hdr_line))
        rows(vo_ok, mus_c)
        r_ = subprocess.run([sys.executable, os.path.abspath(__file__), "licences", job, "--channels", "5"],
                            capture_output=True, text=True, timeout=60)
        check("HR-11 `licences --channels 5` prints the WARN and still exits 0 on a clean manifest",
              r_.returncode == 0 and "WARN" in r_.stdout and "covers 3" in r_.stdout, r_.stdout + r_.stderr)
        rows(vo_ok, mus_ok)
        os.makedirs(os.path.join(job, "06-sfx", "conform"))
        cr = os.path.join(job, "06-sfx", "conform", "S2.sfx.wav"); open(cr, "wb").write(b"RIFF")
        json.dump({"sources": [{"file": "06-sfx/drops.wav"}]}, open(cr + ".conform.json", "w"))
        check("a conformed render whose source has no row is named", any("conformed from 06-sfx/drops.wav" in p
                                                                           for p in licence_problems(job)))
        json.dump({"sources": [{"file": "x_mus_bed_v001.wav"}]}, open(cr + ".conform.json", "w"))
        check("…and one whose source has a row inherits it", licence_problems(job) == [], json.dumps(licence_problems(job)))
        os.remove(cr); os.remove(cr + ".conform.json")
        for bad, needle, name in (
                (vo_ok[:7] + ["free"] + vo_ok[8:], "BLOCKED", "an ElevenLabs free-plan voice"),
                (vo_ok[:6] + ["sfx_v2 beta"] + vo_ok[7:], "BLOCKED", "an ElevenLabs Beta output"),
                (["06-music/x_mus_bed_v001.wav", "sfx", "ai:mmaudio", "CC-BY-NC", "yes", "MMAudio", "1.0", "-", "RO", ""],
                 "BLOCKED", "an MMAudio effect"),
                (["06-music/x_mus_bed_v001.wav", "sfx", "ai:hunyuan", "Tencent Hunyuan community", "yes",
                  "HunyuanVideo-Foley", "1.0", "-", "RO", ""], "BLOCKED", "Hunyuan foley in an EU ad"),
                (vo_ok[:5] + ["", "", "", "", ""], "AI-made", "an AI voice with no tool, version, plan or region")):
            rows(bad, mus_ok if bad[0] != mus_ok[0] else vo_ok)
            check(f"the manifest refuses {name}", any(needle in p for p in licence_problems(job)),
                  json.dumps(licence_problems(job)))
        rows(vo_ok, mus_ok, ["03-clips/S4_v1.mp4", "native", "", "", "", "", "", "", "", ""])
        check("a native-audio row needs the director's approval",
              any("approval" in p for p in licence_problems(job)), json.dumps(licence_problems(job)))
        rows(vo_ok, mus_ok, ["03-clips/S4_v1.mp4", "native", "", "", "", "", "", "", "",
                             "Dana: \"keep the real clink under S4\""])
        check("…and with it, the take's own audio may stay in the mix",
              st(measure(job, exn, dw, bwn), "native audio is a guide only") == "PASS" and licence_problems(job) == [])
        # the export check
        for p in glob.glob(os.path.join(job, "10-export", "*")):
            if p != ex and not p.startswith(ex):
                os.remove(p)
        # (3.2.0) the dialogue in the centre and the first word clear of the effects
        tt = np.arange(int(4.0 * SR)) / SR
        line = (0.3 * np.sin(2 * np.pi * 180 * tt)).astype(np.float32)
        line[: int(1.0 * SR)] = 0.0; line[int(2.0 * SR): int(2.5 * SR)] = 0.0       # lines start at 1.0 s and 2.5 s
        rg = np.random.default_rng(5)                                                # a room send: two independent
        tail = (np.abs(line) > 0).astype(np.float32) * 0.05                          # tails, decorrelated by design
        centred = np.stack([line + tail * rg.standard_normal(len(line)).astype(np.float32),
                            line + tail * rg.standard_normal(len(line)).astype(np.float32)], axis=1)
        check("(3.2.0) a centred voice with a decorrelated room send sits in the centre",
              abs(dialogue_balance(centred)["lr_db"]) <= CENTRE_DB, json.dumps(dialogue_balance(centred)))
        left = np.stack([line * 1.0, line * 0.6], axis=1)                            # about 30 % left
        check("(3.2.0) a voice leaning left is outside ±1 dB", dialogue_balance(left)["lr_db"] > CENTRE_DB,
              json.dumps(dialogue_balance(left)))
        quiet = np.zeros((int(2.0 * SR), 2), np.float32)
        check("(3.2.0) a silent dialogue stem never speaks: no balance, no line starts",
              dialogue_balance(quiet)["lr_db"] is None and line_onsets(quiet) == [])
        check("(3.2.0) the lines start where the quiet ends", [round(x, 1) for x in line_onsets(centred)] == [1.0, 2.5],
              json.dumps(line_onsets(centred)))
        hit = np.zeros(int(4.0 * SR), np.float32)
        for at in (1.03, 3.4):                                                       # one on a first syllable, one clear
            k = int(at * SR); hit[k:k + 2400] = (0.8 * np.exp(-np.arange(2400) / 300.0)).astype(np.float32)
        sx = os.path.join(td, "sfx.wav"); _wav(sx, np.stack([hit, hit], axis=1))
        fw = first_word_hits(centred, sx)
        check("(3.2.0) an effect on a line's first syllable is caught, one 0.9 s later is not",
              len(fw) == 1 and fw[0][0] == 1.0, json.dumps(fw))
        dl = os.path.join(td, "dl.wav"); _wav(dl, left)
        rl = measure(job, ex, dl, bw, sfx=sx)
        check("(3.2.0) the report carries both checks as WARNs, never a FAIL of their own",
              st(rl, "dialogue in the centre") == "WARN" and st(rl, "first word clear of the effects") == "WARN",
              json.dumps([c for c in rl["checks"] if c["name"] in ("dialogue in the centre",
                                                                   "first word clear of the effects")]))
        check("(3.2.0) with no effects stem the first-word check says it was not checked",
              st(measure(job, ex, dw, bw), "first word clear of the effects") == "N/A")
        r0 = measure(job, ex, dw, bw)
        check("export check: a passing report on these bytes and a clean manifest → nothing missing",
              check_job(job) == [], json.dumps(check_job(job)))
        open(ex, "ab").write(b"\0")
        check("export check: a render changed after its mix was measured is stale",
              any("changed after" in p for p in check_job(job)))
        os.remove(ex + ".mix.json")
        check("export check: a render with no mix report is named", any("no mix report" in p for p in check_job(job)))
    # the waveform sync proof: every event a line at its own time, from the event sheet's reader
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("07-edit/music", "09-qa/mix"):
            os.makedirs(os.path.join(job, d))
        D, B = _synth(6.0)
        mw = os.path.join(job, "09-qa", "mix", "mix.wav")
        _wav(mw, D + B)
        json.dump({"fps": 24, "tracks": {"video1": [{"name": "S1", "type": "Video", "start": 0, "duration": 48},
                                                    {"name": "S2", "type": "Video", "start": 48, "duration": 96}]}},
                  open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
        json.dump({"hits": [{"id": "BUTTON", "t": 4.5, "priority": "must", "want": "button"}]},
                  open(os.path.join(job, "07-edit", "music", "HITS.json"), "w"))
        r = wave(job, mw)
        X = {l["id"]: l["x"] for l in r["lines"]}
        png = os.path.join(job, r["png"])
        dims = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", png],
                              capture_output=True, text=True).stdout.strip()
        check("wave: one line per event at its own time (the cut at 2.0 s, the button at 4.5 s of 6 s)",
              X == {"C1": round(2.0 / r["duration_s"] * 1799), "BUTTON": round(4.5 / r["duration_s"] * 1799)}, json.dumps(r["lines"]))
        check("wave: an 1800 × 280 picture, named for the mix's bytes", dims == "1800,280"
              and os.path.basename(png) == f"WAVE-{sha256_file(mw)[:8]}.png", dims)
    print("-" * 60)
    print("selftest OK — the stems checked against the export, the VO over the bed (full band and on a phone) "
          "against the floors, the 45+ floors and a changed floor's reason, the short-term ceiling, mono fold-down, "
          "room tone (silence, a planned hole, a dropout at a cut, the drama lane's ambience), native audio found "
          "in the mix and approved, the manifest (missing licence, the four known blocks, AI fields, native approval, "
          "and the channels a cue's plan covers against the delivery's, HR-11, as warnings), "
          "the export check (missing, stale) and the waveform sync proof" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    m = sub.add_parser("measure"); m.add_argument("job")
    m.add_argument("--export", required=True); m.add_argument("--dialogue"); m.add_argument("--bed")
    m.add_argument("--music"); m.add_argument("--ambience"); m.add_argument("--voices")
    m.add_argument("--sfx", help="(3.2.0) the effects stem: checks that no effect lands on a line's first word")
    m.add_argument("--audience", choices=["general", "45+"], default="general")
    m.add_argument("--lane", choices=["ads", "drama"], default="ads")
    m.add_argument("--holes", help="planned silences, one `start-end` (seconds) per line")
    m.add_argument("--cuts", help="the cut times, one per line (default: the newest motion joins report)")
    m.add_argument("--scenes", help="shots that share one location, e.g. 'S1-S4;S5,S6' (drama lane)")
    m.add_argument("--no-vo", dest="no_vo", help="a film with no dialogue: say why")
    for k in FLOORS:
        m.add_argument(f"--floor-{k}", type=float)
    m.add_argument("--why", help="the reason for a changed floor, recorded in the report")
    sub.add_parser("manifest").add_argument("job")
    li = sub.add_parser("licences"); li.add_argument("job")
    # the number of channels (accounts or outlets) the delivery is published on — not audio channels
    li.add_argument("--channels", type=int, default=None, metavar="N",
                    help="the delivery's channel count: the accounts or outlets the film is published on (not "
                         "audio channels). WARN when a licensed cue's plan covers fewer")
    sub.add_parser("check").add_argument("job")
    wv = sub.add_parser("wave"); wv.add_argument("job"); wv.add_argument("--mix", required=True); wv.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "measure":
        j = a.job
        P = lambda p: (p if os.path.isabs(p) else os.path.join(j, p)) if p else None
        r = measure(j, P(a.export), P(a.dialogue), P(a.bed), P(a.music), P(a.ambience), P(a.voices), a.audience,
                    a.lane, P(a.holes), P(a.cuts), a.scenes, a.no_vo,
                    {k: getattr(a, f"floor_{k}") for k in FLOORS}, a.why, sfx=P(a.sfx))
        print(render_md(r))
        return 0 if r["verdict"] == "PASS" else 1
    if a.cmd == "manifest":
        print(write_manifest(a.job)); return 0
    if a.cmd == "wave":
        mx = a.mix if os.path.isabs(a.mix) else os.path.join(a.job, a.mix)
        r = wave(a.job, mx, a.out)
        n = {}
        for ln in r["lines"]:
            n[ln["kind"]] = n.get(ln["kind"], 0) + 1
        print(f"wrote {r['png']} — {r['duration_s']} s, " + ", ".join(f"{v} {k}" for k, v in n.items())
              + " · grey cut, orange must-hit, white placed sound, blue title; each attack should sit on or just after its line")
        for x in r["notes"]:
            print(f"  note: {x}")
        return 0
    if a.cmd in ("licences", "check"):
        P = licence_problems(a.job) if a.cmd == "licences" else check_job(a.job)
        for p in P:
            print(f"  ✗ {p}")
        # the plan's channels against the delivery's: WARN and info only, never the exit code
        W, I = licence_warnings(a.job, getattr(a, "channels", None)) if a.cmd == "licences" else ([], [])
        for w in W:
            print(f"  WARN  {w}")
        for x in I:
            print(f"  info  {x}")
        print(("clean" if not P else f"{len(P)} problem(s)") + (f" · {len(W)} warning(s)" if W else ""))
        return 1 if P else 0
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
