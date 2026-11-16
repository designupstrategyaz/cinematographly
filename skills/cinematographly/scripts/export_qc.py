#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
export_qc.py — check a finished export against spec BEFORE it goes to the client, instead of
eyeballing resolution/duration and hoping the mix is loud enough. Every check is read-only (no
re-encode, nothing written unless --report is given):

1. ffprobe: width/height, frame rate, duration against the target spec.
2. ffmpeg `loudnorm` in single-pass MEASURE mode: the actual integrated loudness (LUFS) and true
   peak (dBTP) of the file as it stands — the same measurement a real normalize pass would use,
   just without applying it. Compared against the −14 LUFS / −1 dBTP defaults from
   editing-and-audio.md's "Audio finish" section (override with --target-lufs / --max-true-peak).
3. Audio sample rate and channel count against the preset — 48 kHz / stereo by default. Cheap checks
   for two failures that are SILENT until someone else hears them: a 44.1 kHz render in a 48 kHz
   video world (pitch/sync drift) and a mono master on a stereo spec.
4. The poster frame (v2.46, WARN only): frame 0 is the thumbnail a feed shows before anything plays
   (Meta's autoplay most of all; TikTok and Instagram let you pick a cover). It warns when frame 0 is a
   fade-up (its mean luma under 10 % of the mean over 0.5–1.5 s) or a flat card (luma spread under
   4/255) [ASSUMED thresholds]. Whether this should FAIL is the owner's open question Q6, so it never
   changes OVERALL. It cannot see whether frame 0 shows the RIGHT subject: the event sheet's POSTER tile
   (contact_sheet.py events) is where a person reads that.
5. The file-size ceiling: only when the delivery names one — a preset's optional `max_mb`, or
   --max-mb. A file above it FAILs, naming its size and the cap, and the report gives the total bitrate
   that fits the cap over this duration: lower the target bitrate until the estimate fits, re-export,
   and record that the file compresses harder (look again at dark gradients and fast motion). No preset
   carries a cap by default, so with neither the check reads SKIP. 1 MB = 1,000,000 bytes, the stricter
   reading of a ceiling written in MB.
6. The upload master (v2.48.0, project switch `upload-master`): `--upload-master` QCs the job's one extra
   upload copy. Its resolution passes at the preset's shape and a larger size (2160x3840 from vertical-1080),
   named as lifted in the report; every other check is unchanged. It is refused, naming the switch, unless the
   job's CHECKPOINT lifts `upload-master` (the job holding the file, or --job). The delivered file is still
   QC'd against its preset exactly, without the flag.

7. The one-frame flash (v2.49, production lessons 2026-11-05): every frame is read, the first and the last
   included. A FAIL counts in OVERALL: frame 0 or the last frame unlike its neighbour while the next pair agrees
   (the lockup on frame 0 before its fade-in), a one-frame shot (a stray frame at a cut), or a keyframe flash (a
   region that shows its end state for one frame, then fades in). A one-frame spike that never comes back only
   warns. --allow-flash FRAMES for a flash that is meant; --skip-flash says the check did not run.

Usage:
  python3 export_qc.py 10-export/SLUG-v1-final.mp4
  python3 export_qc.py 10-export/SLUG-v1-final.mp4 --target-duration 58 --duration-tolerance 1.5
  # --format names a preset in assets/delivery-formats.json and sets resolution, fps and
  #   the loudness target together. --landscape is kept as a shortcut for 1920x1080.
  # --report writes a copy of the printed report to <file>.qc.txt next to the export

Exit code is 0 if every check passes, 1 if any check fails or a measurement couldn't be made —
safe to use as a hard gate in a hand-off checklist.
"""
import argparse
import json
import os
import re
import subprocess
import sys


def ffprobe_json(path):
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True, text=True, timeout=30)
    return json.loads(out.stdout)


def parse_fps(rate_str):
    if not rate_str or rate_str == "0/0":
        return None
    if "/" in rate_str:
        num, den = rate_str.split("/")
        den = float(den)
        return float(num) / den if den else None
    return float(rate_str)


def measure_loudness(path):
    """Single-pass ffmpeg loudnorm in measure-only mode — reads the JSON stats block it prints to
    stderr. Target params (I/TP/LRA) only configure what a normalize pass WOULD do; the measured
    input_i / input_tp fields are the file's actual current loudness/peak regardless of them."""
    cmd = ["ffmpeg", "-i", path, "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
           "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    stderr = proc.stderr
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(stderr[start:end + 1])
    except json.JSONDecodeError:
        return None


ST_RE = re.compile(r"t:\s*([\d.]+)\s+TARGET:.*?S:\s*(-?[\d.]+|-inf|nan)")


def parse_short_term(stderr: str) -> list:
    """(t, short-term LUFS) pairs from ffmpeg ebur128's per-100 ms log lines."""
    out = []
    for m in ST_RE.finditer(stderr):
        try:
            out.append((float(m.group(1)), float(m.group(2))))
        except ValueError:
            continue
    return out


def max_short_term(path):
    """The loudest 3 s window (EBU short-term) from 3 s on, or None when ffmpeg did not run. (v2.60.0) The
    broadcast preset caps it absolutely (EBU R 128 s1: -18 LUFS); mix_qa.py only checks it relative to the
    file's own integrated level."""
    try:
        proc = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                              capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    vals = [s for t, s in parse_short_term(proc.stderr) if t >= 3.0 and s > -120]
    return max(vals) if vals else None


# ⛔ Digital silence is not quiet — it is NOTHING, and it is the sound of a two-layer mix with the
# music ducked out. `editing-and-audio.md` §: "no clip plays over silence — every moment carries at
# least the room-tone bed under it", and `realism-qa.md` calls missing room tone the single
# most-missed realism fix. Until 2026-09-07 the only enforced audio fact in this skill was
# integrated LUFS on the whole file — which a VO-over-music mix with holes in it passes cleanly,
# because the holes do not move the integrated number much. This is that rule made mechanical.
SILENCE_RE = re.compile(r"silence_start:\s*(-?[\d.]+)|silence_end:\s*([\d.]+)")


def silent_runs(path, floor_db=-60.0, min_len=0.4):
    """Runs at or below `floor_db` — near-total absence, not "quiet".

    -60 dBFS is chosen so a real room-tone bed never trips it: the house bed sits at -18 to -24 dB
    and even a very restrained one lands far above -60. What trips it is a gap with literally
    nothing under it. [ASSUMED 2026-09-07] — replace it with a measurement from real masters."""
    cmd = ["ffmpeg", "-i", path, "-af", f"silencedetect=noise={floor_db}dB:d={min_len}",
           "-f", "null", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError):
        return None
    runs, start = [], None
    for m in SILENCE_RE.finditer(proc.stderr):
        if m.group(1) is not None:
            start = max(0.0, float(m.group(1)))
        elif start is not None:
            runs.append((round(start, 2), round(float(m.group(2)), 2)))
            start = None
    return runs


def check(label, ok, detail):
    mark = "PASS" if ok else "FAIL"
    line = f"  [{mark}] {label}: {detail}"
    return line, ok


# ---- the upload master (v2.48.0, project switch upload-master) ----------------
def resolution_verdict(w, h, want_w, want_h, upload_master=None):
    """(ok, detail) for the picture size. `upload_master` is the switch's lifted() wording when the file under test is
    the job's extra upload copy (realism-qa V15 lifted): then it passes at the preset's shape and a larger size — the
    same aspect within a pixel, wider and taller. Otherwise it must equal the preset, exactly as before."""
    if not upload_master:
        return (w == want_w and h == want_h), f"{w}x{h} (want {want_w}x{want_h})"
    if not (w and h):
        return False, f"{w}x{h} — unreadable"
    same_shape = abs(w * want_h - h * want_w) <= max(want_w, want_h)
    larger = w > want_w and h > want_h
    if same_shape and larger:
        return True, f"{w}x{h}, an upload master: the shape of {want_w}x{want_h}, larger — {upload_master}"
    why = ("not the preset's shape" if not same_shape else
           "the preset's size, so it is the delivery itself: QC it without --upload-master" if (w, h) == (want_w, want_h)
           else "not larger than the preset")
    return False, (f"{w}x{h} (an upload master wants the shape of {want_w}x{want_h} at a larger size — {why}; the "
                   f"switch `upload-master` lifts the size only)")


# ---- the poster frame (v2.46) -------------------------------------------------
POSTER_FADE = 0.10      # frame 0's mean luma under 10 % of the mean over 0.5–1.5 s: a fade-up [ASSUMED]
POSTER_FLAT = 4.0       # frame 0's luma standard deviation under 4/255: a flat card [ASSUMED]
POSTER_LATER = (0.5, 1.0, 1.5)


def gray_frame(path, t, w=96, h=54):
    """One frame at `t` as w×h 8-bit luma bytes, or None."""
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                            "-vf", f"scale={w}:{h}", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                           capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 and len(r.stdout) == w * h else None


def luma_stats(buf):
    n = len(buf)
    m = sum(buf) / n
    return m, (sum((v - m) ** 2 for v in buf) / n) ** 0.5


def first_frame_verdict(m0, s0, later_mean):
    """(ok, detail) from frame 0's mean and spread and the mean over 0.5–1.5 s (None when the file is shorter)."""
    if s0 < POSTER_FLAT:
        return False, (f"frame 0 is a flat card (luma spread {s0:.1f}/255, mean {m0:.0f}) — the thumbnail shows "
                       f"nothing; open on the subject")
    if later_mean is not None and later_mean > 0 and m0 < POSTER_FADE * later_mean:
        return False, (f"frame 0 is a fade-up (mean luma {m0:.0f} against {later_mean:.0f} over 0.5–1.5 s) — the "
                       f"thumbnail is nearly black; start the picture on frame 0")
    return True, f"frame 0 carries picture (mean luma {m0:.0f}, spread {s0:.0f})"


def first_frame(path, duration):
    b0 = gray_frame(path, 0.0)
    if b0 is None:
        return None, "frame 0 could not be read"
    m0, s0 = luma_stats(b0)
    later = [luma_stats(b)[0] for b in (gray_frame(path, t) for t in POSTER_LATER if t < duration - 0.05) if b]
    return first_frame_verdict(m0, s0, sum(later) / len(later) if later else None)


# ---- the one-frame flash (v2.49, production lessons 2026-11-05) ----------------
# "A one-frame flash: the card's fade-in showed the full lockup on frame 0 for one frame. Only frames 12 and 34 were
# checked, never the first." A fade made by script keys the current value at the current time, so the comp shows its
# end state on its first frame and then fades up from nothing. Every frame of the render is read here (32x32 cell
# means, one ffmpeg pass), first and last included. Four signatures:
#   first / last   frame 0 unlike frame 1 in many cells while frames 1 and 2 nearly agree (a fade may already be moving:
#                  under a quarter of the jump); the last frame the same, mirrored
#   one-frame shot a frame unlike both neighbours as a whole, with steady pictures either side (a stray frame at a cut)
#   keyframe flash cells that jump for one frame, between neighbours that agree, and whose picture comes back within a
#                  second (the end state shown early, or late) — the lockup that flashes and then fades in
#   (warn) spike   the same jump with no return: a one-frame graphic, or fast motion. Listed to look at, never a FAIL
# Thresholds [ASSUMED], tuned on synthetic flashes and measured on eleven real cuts and clips (13,042 frames, 9.1 min:
# hands, cloth and a swinging bag in fast motion, hard cuts, fades, Kling takes), where the FAIL signatures fired 0 times
# and one spike warned (the bag). A frame that is meant to flash (a strobe, a camera flash):
# --allow-flash FRAME[,FRAME…], named in the report.
FLASH_GRID = 32         # cells per side (area-averaged)
FLASH_T = 40            # a cell jumps: |Δ| ≥ 40/255
FLASH_AGREE = 12        # the neighbours agree: |Δ| ≤ 12/255
FLASH_EDGE_CELLS = 24   # first / last: at least this many cells, and 3× the clip's usual moving cells
FLASH_KEY_CELLS = 16    # keyframe flash: at least this many jumping cells
FLASH_WARN_CELLS = 24   # a spike with no return, listed as a warning
FLASH_RETURN = 0.7      # …the share of those cells whose picture comes back (within 15/255) inside a second
FLASH_CUT_MIN = 12.0    # one-frame shot: the frame's mean change on both sides ≥ 12/255 …
FLASH_CUT_K = 3.0       # … and ≥ 3× (the steadier side's change + 6/255)


def frame_cells(path, n=FLASH_GRID):
    """Every frame as n×n luma cell means (bytes), in decode order, or None."""
    base = ["ffmpeg", "-v", "error", "-i", path, "-an", "-vf", f"scale={n}:{n}:flags=area", "-pix_fmt", "gray"]
    for sync in (["-fps_mode", "passthrough"], ["-vsync", "0"]):          # ffmpeg ≥ 5.1, then older builds
        try:
            r = subprocess.run(base + sync + ["-f", "rawvideo", "-"], capture_output=True, timeout=900)
        except (OSError, subprocess.SubprocessError):
            return None
        if r.returncode == 0 and r.stdout:
            k = n * n
            return [r.stdout[i:i + k] for i in range(0, len(r.stdout) - k + 1, k)]
    return None


def flash_frames(F, fps=24.0, allow=()):
    """[(frame, kind, detail)] — kind is first | last | one-frame shot | keyframe flash | spike (warn)."""
    import statistics
    N, T, A, out = len(F), FLASH_T, FLASH_AGREE, []
    if N < 3:
        return out
    adj = [[abs(a - b) for a, b in zip(F[k], F[k + 1])] for k in range(N - 1)]   # adj[k] = |F[k+1] − F[k]|
    mean = [sum(x) / len(x) for x in adj]
    moving = [sum(1 for v in x if v >= T) for x in adj]
    # first and last
    for idx, a, b, base in ((0, adj[0], adj[1], range(1, min(N - 1, 25))),
                            (N - 1, adj[N - 2], adj[N - 3], range(max(0, N - 26), N - 2))):
        n = sum(1 for d1, d2 in zip(a, b) if d1 >= T and d2 <= max(A, d1 / 4))       # a fade may already be moving
        usual = statistics.median([moving[k] for k in base]) if len(base) else 0
        if n >= max(FLASH_EDGE_CELLS, 3 * usual):
            nb = "1 and 2" if idx == 0 else f"{N - 2} and {N - 3}"
            out.append((idx, "first frame" if idx == 0 else "last frame",
                        f"{n} cells jump against the next frame while frames {nb} agree (usual motion {usual:g} cells)"))
    # a one-frame shot
    for i in range(N):
        sides = [x for x in ((mean[i - 1] if i >= 1 else None), (mean[i] if i <= N - 2 else None)) if x is not None]
        ctx = [x for x in ((mean[i - 2] if i >= 2 else None), (mean[i + 1] if i <= N - 3 else None)) if x is not None]
        if not ctx or (len(sides) < 2 and i not in (0, N - 1)):
            continue
        s = max(ctx) + 6.0
        if all(x >= FLASH_CUT_MIN and x >= FLASH_CUT_K * s for x in sides):
            out.append((i, "one-frame shot", f"the whole frame changes {min(sides):.0f}/255 against "
                                             f"{'both neighbours' if len(sides) == 2 else 'its neighbour'}, "
                                             f"which are steady ({max(ctx):.0f}/255)"))
    # the keyframe flash, and the spike with no return
    R = max(2, int(round(fps)))
    for i in range(1, N - 1):
        pre, post = (adj[i - 2] if i >= 2 else None), (adj[i + 1] if i <= N - 3 else None)
        S = [c for c, (x, z, d1, d2) in enumerate(zip(F[i - 1], F[i + 1], adj[i - 1], adj[i]))
             if d1 >= T and d2 >= T and abs(x - z) <= A
             and (pre is None or pre[c] <= max(A, min(d1, d2) / 4)) and (post is None or post[c] <= max(A, min(d1, d2) / 4))]
        if len(S) < FLASH_KEY_CELLS:
            continue
        back = None
        for m in range(2, R + 1):
            for j in (i + m, i - m):
                if 0 <= j < N and sum(1 for c in S if abs(F[j][c] - F[i][c]) <= 15) >= FLASH_RETURN * len(S):
                    back = j
                    break
            if back is not None:
                break
        if back is not None:
            out.append((i, "keyframe flash", f"{len(S)} cells show for one frame what frame {back} shows, and frames "
                                             f"{i - 1} and {i + 1} agree without it — an end state keyed early or late"))
        elif len(S) >= FLASH_WARN_CELLS:
            out.append((i, "spike (warn)", f"{len(S)} cells jump for one frame and do not come back — a one-frame "
                                           f"graphic, or fast motion: look at frames {i - 1}–{i + 1}"))
    seen, res = set(), []
    for f, k, d in sorted(out):
        if (f, k) not in seen:
            seen.add((f, k))
            res.append((f, k + (" (allowed)" if f in allow else ""), d))
    return res


def flash_verdict(found, fps):
    """(ok, detail, warn_lines): FAIL on any first/last/one-frame-shot/keyframe flash not allowed; spikes only warn."""
    bad = [x for x in found if "(warn)" not in x[1] and "(allowed)" not in x[1]]
    warns = [x for x in found if "(warn)" in x[1]]
    allowed = [x for x in found if "(allowed)" in x[1]]
    fmt = lambda x: f"frame {x[0]} ({x[0] / fps:.3f} s) {x[1]}: {x[2]}"
    if bad:
        return False, "; ".join(fmt(x) for x in bad[:4]) + (f"; … {len(bad) - 4} more" if len(bad) > 4 else ""), \
            [fmt(x) for x in warns[:6]]
    return True, ("no one-frame flash, first and last frames included"
                  + (f" ({len(allowed)} allowed: {', '.join(str(x[0]) for x in allowed)})" if allowed else "")), \
        [fmt(x) for x in warns[:6]]


# ---- the file-size ceiling -----------------------------------------
MB = 1_000_000          # a ceiling written in MB read as decimal megabytes: the stricter reading


def size_verdict(size_bytes, max_mb, duration_s, audio_kbps=None):
    """(ok, detail, hint) for the file against the delivery's ceiling. ok is None when no ceiling was
    named (SKIP). The hint is the total bitrate that fits the cap over this duration, and the video
    bitrate once the audio stream's own rate is taken off; it is printed with a FAIL."""
    mb = size_bytes / MB
    f = (lambda x: f"{x:.1f}" if x >= 10 else f"{x:.2f}")
    if not max_mb:
        return None, f"{f(mb)} MB (no max_mb in the preset and no --max-mb: the delivery names no ceiling)", ""
    if size_bytes <= max_mb * MB:
        return True, f"{f(mb)} MB (cap {max_mb:g} MB)", ""
    detail = f"{f(mb)} MB is over the delivery's {max_mb:g} MB cap by {f(mb - max_mb)} MB"
    if not duration_s or duration_s <= 0:
        return False, detail, ("lower the target bitrate and re-export; the duration is unreadable, so no "
                               "bitrate estimate. Record that the file compresses harder")
    total = max_mb * MB * 8 / duration_s / 1000.0            # kb/s that fills the cap exactly
    now = size_bytes * 8 / duration_s / 1000.0
    vid = f", about {total - audio_kbps:.0f} kb/s for the video after the audio's {audio_kbps:.0f}" \
        if audio_kbps and total > audio_kbps else ""
    hint = (f"lower the target bitrate until the estimate fits: {now:.0f} kb/s now, at most {total:.0f} kb/s "
            f"in total over {duration_s:.1f} s{vid} (leave a few per cent for the container). Record that "
            f"the file compresses harder, and look again at dark gradients and fast motion after the re-export")
    return False, detail, hint


# ---- delivery-format presets -------------------------------------------------
def load_format(name):
    """Read a preset from assets/delivery-formats.json. There is no house format;
    the delivery spec is a client x platform decision (references/delivery-format.md)."""
    import json, os, sys
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(os.path.dirname(here), "assets", "delivery-formats.json")
    try:
        with open(path, encoding="utf-8") as fh:
            formats = json.load(fh)["formats"]
    except (OSError, KeyError, ValueError) as e:
        print(f"error: cannot read {path}: {e}", file=sys.stderr)
        raise SystemExit(2)
    if name not in formats:
        print(f"error: unknown format {name!r}. Available: {', '.join(sorted(formats))}\n"
              f"       Add a new one to assets/delivery-formats.json rather than passing raw numbers.",
              file=sys.stderr)
        raise SystemExit(2)
    return formats[name]


def load_all_formats():
    """Preset names from assets/delivery-formats.json, for error messages."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "delivery-formats.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return list(json.load(fh)["formats"].keys())
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export_file", nargs="?")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--landscape", action="store_true", help="shorthand for --width 1920 --height 1080")
    ap.add_argument("--format", dest="fmt", default=None,
                    help="a preset name from assets/delivery-formats.json (vertical-1080, feed-4x5, "
                         "square-1080, landscape-1080, landscape-4k, broadcast-eu-1080). Sets "
                         "resolution, fps and the loudness target together, and overrides the "
                         "individual flags unless you pass them explicitly.")
    ap.add_argument("--fps", type=float, default=None, help="expected fps; omit to skip the fps check")
    ap.add_argument("--fps-tolerance", type=float, default=0.5)
    ap.add_argument("--target-duration", type=float, default=None, help="omit to skip the duration check")
    ap.add_argument("--duration-tolerance", type=float, default=1.0)
    ap.add_argument("--target-lufs", type=float, default=None)
    ap.add_argument("--sample-rate", type=int, default=None,
                    help="required audio sample rate in Hz (from --format when a preset is used)")
    ap.add_argument("--channels", type=int, default=None,
                    help="required audio channel count (from --format when a preset is used)")
    # only when the delivery names a ceiling; no preset carries one by default
    ap.add_argument("--max-mb", type=float, default=None, metavar="MB",
                    help="the delivery's file-size ceiling in MB (1 MB = 1,000,000 bytes). From the "
                         "preset's optional max_mb when --format names one that has it; omit both to "
                         "skip the size check")
    ap.add_argument("--lufs-tolerance", type=float, default=None,
                    help="± LU around the target (from the preset's loudness_tolerance_lu, else 1.0)")
    ap.add_argument("--short-term-max", type=float, default=None, metavar="LUFS",
                    help="absolute ceiling for any 3 s window (from the preset's short_term_max_lufs; "
                         "EBU R 128 s1 sets -18 for broadcast ads). Omit both to skip")
    ap.add_argument("--max-true-peak", type=float, default=-1.0)
    ap.add_argument("--silence-floor", type=float, default=-60.0, metavar="dBFS",
                    help="a run at or below this is DIGITAL SILENCE, not quiet (default -60). The "
                         "house room-tone bed sits at -18 to -24 dB, so a real bed never trips it")
    ap.add_argument("--min-silence", type=float, default=0.4, metavar="SECONDS",
                    help="shortest silent run that counts (default 0.4 — below that it is a cut, "
                         "not a hole)")
    ap.add_argument("--allow-silence", action="store_true",
                    help="skip the room-tone check. Use only where silence is a DELIBERATE beat and "
                         "say so in the QA log — the default exists because a hole is far more "
                         "often a two-layer mix than a choice")
    # (v2.48.0, project switch upload-master) the job's extra upload copy: the preset's shape at a larger size
    ap.add_argument("--upload-master", action="store_true",
                    help="the file is the job's extra UPLOAD copy, not the delivery: the resolution check passes at the "
                         "preset's shape and a larger size (2160x3840 for vertical-1080); every other check is "
                         "unchanged. Needs the job's project switch `upload-master` (the `Switches:` line in "
                         "00-brief/CHECKPOINT.md, switches.py)")
    ap.add_argument("--job", default=None,
                    help="the job whose CHECKPOINT carries its project switches (default: the job holding the file)")
    ap.add_argument("--allow-flash", default="", metavar="FRAME[,FRAME…]",
                    help="frames meant to flash (a strobe, a camera flash): reported as allowed, not failed")
    ap.add_argument("--skip-flash", action="store_true",
                    help="skip the one-frame flash check (it decodes every frame) — the report says it was skipped")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true", help="also write <file>.qc.txt")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.export_file:
        raise SystemExit("error: give an export file (or --selftest)")

    path = os.path.abspath(os.path.expanduser(a.export_file))
    if not os.path.isfile(path):
        raise SystemExit(f"Not found: {path}")
    # ⛔ AN EVALUATION NEVER SHIPS (house decision 2026-10-25, the evaluation tier). The refusal is
    # mechanical because the tier bends the 1080p floor: a file under _eval/, named EVAL, or from a
    # `Tier: evaluation` job gets no QC report, so `gate.py approve export` has nothing to accept.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import job_tier
    why = job_tier.ship_refusal(path)
    if why:
        print(f"REFUSED: {why}", file=sys.stderr)
        return 1
    # (v2.48.0, project switch upload-master) --upload-master only where the job lifts V15 for its one upload copy
    um = None
    if a.upload_master:
        import switches
        um_job = a.job or job_tier.job_root(path)
        um = switches.on(um_job, "upload-master")
        if not um:
            where = (os.path.relpath(switches.checkpoint_path(um_job)) if um_job
                     else "<job>/00-brief/CHECKPOINT.md (no job found above the file: pass --job)")
            print(f"REFUSED: --upload-master needs the job's project switch `upload-master` (realism-qa V15: deliver at "
                  f"the format's resolution and no higher) — add `upload-master — <why this job needs a larger upload "
                  f"copy>` to the `Switches:` line in {where}", file=sys.stderr)
            return 1
        um = switches.lifted("upload-master", um)
    if a.landscape:
        a.width, a.height = 1920, 1080
    if a.fmt:
        f = load_format(a.fmt)
        given = set(sys.argv)
        if "--width" not in given and "--height" not in given and not a.landscape:
            a.width, a.height = f["width"], f["height"]
        if a.fps is None:
            a.fps = f.get("fps_default")
        if "--target-lufs" not in given:
            a.target_lufs = f.get("loudness_lufs", a.target_lufs)
        if "--sample-rate" not in given:
            a.sample_rate = f.get("sample_rate_hz", a.sample_rate)
        if "--channels" not in given:
            a.channels = f.get("channels", a.channels)
        if "--max-true-peak" not in given:
            a.max_true_peak = f.get("true_peak_dbtp", a.max_true_peak)
        if a.lufs_tolerance is None:                           # (v2.60.0) broadcast: ±0.5 LU (EBU R 128)
            a.lufs_tolerance = f.get("loudness_tolerance_lu")
        if a.short_term_max is None:                           # (v2.60.0) broadcast: -18 LUFS (EBU R 128 s1)
            a.short_term_max = f.get("short_term_max_lufs")
        if a.max_mb is None:                                   # optional; absent = no ceiling
            a.max_mb = f.get("max_mb")
        print(f"format preset: {a.fmt} — {f['label']} · {f['width']}x{f['height']} · "
              f"{f.get('fps_default')}fps · {f.get('loudness_lufs')} LUFS"
              + (f" · max {f['max_mb']:g} MB" if f.get("max_mb") else ""))
        if f.get("loudness_note"):
            print(f"  ! {f['loudness_note']}")

    if a.lufs_tolerance is None:
        a.lufs_tolerance = 1.0
    # No house format. Resolution and loudness are client x platform decisions
    # (references/delivery-format.md); a default here would silently QC one client's
    # deliverable against another client's spec and pass it.
    missing = []
    if a.width is None or a.height is None:
        missing.append("resolution (--format PRESET, or --width and --height)")
    if a.target_lufs is None:
        missing.append("loudness (--format PRESET, or --target-lufs)")
    if missing:
        print("error: refusing to QC against an assumed spec — no house default exists.\n"
              "       missing: " + "; ".join(missing) + "\n"
              "       presets: " + ", ".join(sorted(load_all_formats())) + "\n"
              "       see references/delivery-format.md", file=sys.stderr)
        return 2

    results, lines = [], []
    lines.append(f"export_qc.py — {os.path.basename(path)}")
    lines.append("=" * 60)
    # The report names the exact bytes it measured. gate.py `approve export` compares this with the file
    # in 10-export/ — a PASS about a render that was replaced afterwards is a PASS about nothing.
    import hashlib
    _h = hashlib.sha256()
    with open(path, "rb") as _fh:
        for _chunk in iter(lambda: _fh.read(1 << 20), b""):
            _h.update(_chunk)
    lines.append(f"file_sha256: {_h.hexdigest()}")
    lines.append(f"format: {a.fmt or 'custom'} · target duration: {a.target_duration or '—'} s")
    if um:                                    # (v2.48.0, project switch upload-master) named in the report itself
        lines.append(f"upload master: the job's extra upload copy, not the delivery — realism-qa V15 {um}; the "
                     f"delivered file is QC'd against its preset without --upload-master")

    probe = ffprobe_json(path)
    vstream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
    duration = float(probe.get("format", {}).get("duration", 0) or 0)

    if not vstream:
        line, ok = check("video stream", False, "no video stream found")
        lines.append(line); results.append(ok)
    else:
        w, h = vstream.get("width"), vstream.get("height")
        # (v2.48.0, project switch upload-master) exactly as before unless --upload-master was allowed above
        line, ok = check("resolution", *resolution_verdict(w, h, a.width, a.height, um))
        lines.append(line); results.append(ok)

        fps = parse_fps(vstream.get("r_frame_rate"))
        if a.fps is not None:
            ok = fps is not None and abs(fps - a.fps) <= a.fps_tolerance
            line, ok = check("frame rate", ok, f"{fps:.3f}fps (want {a.fps}±{a.fps_tolerance})" if fps else "unreadable")
            lines.append(line); results.append(ok)
        else:
            lines.append(f"  [SKIP] frame rate: {fps:.3f}fps (no --fps target given)" if fps else "  [SKIP] frame rate: unreadable")
        # the poster frame: WARN only, never counted in OVERALL (house choice: warn, not fail)
        pf_ok, pf_detail = first_frame(path, duration)
        lines.append(f"  [{' ok ' if pf_ok else 'WARN' if pf_ok is False else 'SKIP'}] first frame (poster, warn-only): "
                     f"{pf_detail}")
        # (v2.49) the one-frame flash, every frame, first and last included — a FAIL counts in OVERALL
        if a.skip_flash:
            lines.append("  [SKIP] one-frame flash: --skip-flash given (frame 0 and the last frame were NOT checked)")
        else:
            cells = frame_cells(path)
            if not cells:
                line, ok = check("one-frame flash", False, "the frames could not be decoded")
                lines.append(line); results.append(ok)
            else:
                allow = {int(x) for x in re.findall(r"\d+", a.allow_flash or "")}
                fl_ok, fl_detail, fl_warn = flash_verdict(flash_frames(cells, fps or 24.0, allow), fps or 24.0)
                line, ok = check("one-frame flash", fl_ok, f"{len(cells)} frames read — {fl_detail}")
                lines.append(line); results.append(ok)
                for w_ in fl_warn:
                    lines.append(f"  [WARN] {w_}")

    if a.target_duration is not None:
        ok = abs(duration - a.target_duration) <= a.duration_tolerance
        line, ok = check("duration", ok,
                          f"{duration:.2f}s (want {a.target_duration}±{a.duration_tolerance}s)")
        lines.append(line); results.append(ok)
    else:
        lines.append(f"  [SKIP] duration: {duration:.2f}s (no --target-duration given)")

    astream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)

    # the delivery's file-size ceiling, only when it names one; a FAIL counts in OVERALL
    try:
        akbps = float((astream or {}).get("bit_rate") or 0) / 1000.0 or None
    except (TypeError, ValueError):
        akbps = None
    sz_ok, sz_detail, sz_hint = size_verdict(os.path.getsize(path), a.max_mb, duration, akbps)
    if sz_ok is None:
        lines.append(f"  [SKIP] file size: {sz_detail}")
    else:
        line, ok = check("file size", sz_ok, sz_detail)
        lines.append(line); results.append(ok)
        if sz_hint:
            lines.append(f"         ! {sz_hint}")
    if not astream:
        line, ok = check("audio stream", False, "no audio stream found — nothing to measure loudness on")
        lines.append(line); results.append(ok)
    else:
        # Sample rate and channel count: cheap, from the same probe, and the failures they catch are
        # silent ones. A 44.1k render into a 48k video world is the classic pitch/sync bug; a mono
        # master on a stereo spec is the classic "why is it quieter than everyone else's" bug.
        if a.sample_rate:
            sr = int(astream.get("sample_rate", 0) or 0)
            line, ok = check("sample rate", sr == a.sample_rate,
                             f"{sr} Hz (want {a.sample_rate})")
            lines.append(line); results.append(ok)
        else:
            lines.append(f"  [SKIP] sample rate: {astream.get('sample_rate')} Hz "
                         f"(no --format preset or --sample-rate given)")
        if a.channels:
            ch = int(astream.get("channels", 0) or 0)
            line, ok = check("channels", ch == a.channels, f"{ch} (want {a.channels})")
            lines.append(line); results.append(ok)
        stats = measure_loudness(path)
        if stats is None:
            line, ok = check("loudness measurement", False, "could not parse ffmpeg loudnorm output")
            lines.append(line); results.append(ok)
        else:
            input_i = float(stats.get("input_i", "nan"))
            input_tp = float(stats.get("input_tp", "nan"))
            ok_lufs = abs(input_i - a.target_lufs) <= a.lufs_tolerance
            line, ok = check("integrated loudness", ok_lufs,
                              f"{input_i:.1f} LUFS (want {a.target_lufs}±{a.lufs_tolerance})")
            lines.append(line); results.append(ok)
            ok_tp = input_tp <= a.max_true_peak
            line, ok = check("true peak", ok_tp, f"{input_tp:.1f} dBTP (want ≤ {a.max_true_peak})")
            lines.append(line); results.append(ok)
            if a.short_term_max is not None:
                smax = max_short_term(path)
                if smax is None:
                    line, ok = check("short-term ceiling", False, "could not measure short-term loudness (ffmpeg ebur128)")
                else:
                    line, ok = check("short-term ceiling", smax <= a.short_term_max + 0.05,
                                     f"loudest 3 s window {smax:.1f} LUFS (want ≤ {a.short_term_max:g})")
                lines.append(line); results.append(ok)
            if a.allow_silence:
                lines.append("  [SKIP] room tone: --allow-silence given")
            else:
                runs = silent_runs(path, a.silence_floor, a.min_silence)
                if runs is None:
                    lines.append("  [SKIP] room tone: silencedetect did not run")
                else:
                    worst = max((b - s for s, b in runs), default=0.0)
                    where = ", ".join(f"{s:.1f}-{b:.1f}s" for s, b in runs[:4])
                    line, ok = check("room tone (no digital silence)", not runs,
                                     "continuous bed — nothing plays over silence" if not runs
                                     else f"{len(runs)} gap(s) at or below {a.silence_floor:g} dBFS, "
                                          f"longest {worst:.1f}s: {where}"
                                          + (" …" if len(runs) > 4 else ""))
                    lines.append(line); results.append(ok)

    lines.append("-" * 60)
    overall = all(results) if results else False
    lines.append(f"OVERALL: {'PASS' if overall else 'FAIL'} ({sum(results)}/{len(results)} checks passed)")
    if not a.target_duration or a.fps is None:
        lines.append("(Duration and/or fps checks were skipped — pass --target-duration/--fps to include them.)")

    report = "\n".join(lines)
    print(report)
    if a.report:
        report_path = path + ".qc.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\nWrote {report_path}")

    sys.exit(0 if overall else 1)


def selftest() -> int:
    """The silence parser, and — the point — that a real bed does NOT trip the check."""
    ok = True

    def check_(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    # the ffmpeg stderr shape silencedetect actually emits, including a negative start
    err = ("[silencedetect @ 0x1] silence_start: -0.001\n"
           "[silencedetect @ 0x1] silence_end: 1.52 | silence_duration: 1.521\n"
           "[silencedetect @ 0x1] silence_start: 18.04\n"
           "[silencedetect @ 0x1] silence_end: 20.44 | silence_duration: 2.4\n")
    runs, start = [], None
    for m in SILENCE_RE.finditer(err):
        if m.group(1) is not None:
            start = max(0.0, float(m.group(1)))
        elif start is not None:
            runs.append((round(start, 2), round(float(m.group(2)), 2)))
            start = None
    check_("both silent runs are parsed", len(runs) == 2)
    check_("a negative start is clamped to 0", runs[0][0] == 0.0)
    check_("the second run keeps its real bounds", runs[1] == (18.04, 20.44))
    check_("the longest run is measured, not the count",
           round(max(b - s for s, b in runs), 2) == 2.4)
    # an unterminated silence_start (silence running to EOF, no end line) yields no phantom run
    partial = "[silencedetect @ 0x1] silence_start: 30.0\n"
    runs2, start2 = [], None
    for m in SILENCE_RE.finditer(partial):
        if m.group(1) is not None:
            start2 = max(0.0, float(m.group(1)))
        elif start2 is not None:
            runs2.append((start2, float(m.group(2))))
    check_("an unterminated silence_start makes no phantom run", runs2 == [])
    check_("nothing detected means nothing to report", list(SILENCE_RE.finditer("")) == [])
    # ⛔ the floor must not fire on a real room-tone bed: the house bed is -18 to -24 dB and the
    # default floor is -60, so there is 36 dB of headroom between "quiet" and "nothing"
    check_("the default floor sits far below the house room-tone bed", -60.0 < -24.0 - 30)
    # the evaluation tier's refusal runs before any measurement (job_tier.py owns the rule)
    import tempfile
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import job_tier
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "00-brief")); os.makedirs(os.path.join(td, "10-export"))
        open(os.path.join(td, "00-brief", "CHECKPOINT.md"), "w").write("Job: x\nTier: evaluation\n")
        f = os.path.join(td, "10-export", "cut_v1.mp4"); open(f, "w").write("x")
        check_("an export from an evaluation job is refused before it is measured",
               bool(job_tier.ship_refusal(f)))
    # the poster frame (v2.46): the verdict, then on real encodes when ffmpeg is here
    check_("a flat frame 0 warns", first_frame_verdict(16.0, 0.5, 120.0)[0] is False)
    check_("a near-black frame 0 before a bright picture warns (a fade-up)", first_frame_verdict(5.0, 6.0, 120.0)[0] is False)
    check_("a frame 0 with picture passes", first_frame_verdict(90.0, 40.0, 110.0)[0] is True)
    check_("a short file is judged on spread alone", first_frame_verdict(90.0, 40.0, None)[0] is True)
    import shutil
    if shutil.which("ffmpeg"):
        with tempfile.TemporaryDirectory() as td:
            def enc(name, src):
                p = os.path.join(td, name)
                r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", src, "-pix_fmt", "yuv420p", p],
                                   capture_output=True, text=True, timeout=60)
                return p if r.returncode == 0 else None
            good = enc("good.mp4", "testsrc=duration=2:size=160x90:rate=24")
            fade = enc("fade.mp4", "testsrc=duration=2:size=160x90:rate=24,fade=in:0:24")
            flat = enc("flat.mp4", "color=c=gray:duration=2:size=160x90:rate=24")
            check_("a real encode: picture on frame 0 passes", good and first_frame(good, 2.0)[0] is True)
            check_("a real encode: a one-second fade-up warns", fade and first_frame(fade, 2.0)[0] is False)
            check_("a real encode: a flat grey card warns", flat and first_frame(flat, 2.0)[0] is False)

    # (v2.60.0) EBU broadcast: the preset carries ±0.5 LU and an absolute -18 LUFS short-term ceiling
    fmts = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                       "assets", "delivery-formats.json"), encoding="utf-8"))
    bc = (fmts.get("formats") or fmts).get("broadcast-eu-1080", {})
    check_("v2.60.0 the EU broadcast preset carries ±0.5 LU and a -18 LUFS short-term ceiling",
           bc.get("loudness_tolerance_lu") == 0.5 and bc.get("short_term_max_lufs") == -18.0)
    log = ("[Parsed_ebur128_0 @ 0x1] t: 2.9     TARGET:-23 LUFS    M: -10.0 S: -11.0     I: -20.0 LUFS\n"
           "[Parsed_ebur128_0 @ 0x1] t: 3.1     TARGET:-23 LUFS    M: -16.0 S: -17.5     I: -20.0 LUFS\n"
           "[Parsed_ebur128_0 @ 0x1] t: 3.2     TARGET:-23 LUFS    M: -inf S: -inf     I: -20.0 LUFS\n")
    pst = parse_short_term(log)
    check_("v2.60.0 the ebur128 log is parsed, -inf included", len(pst) == 3 and pst[1] == (3.1, -17.5))
    if shutil.which("ffmpeg"):
        with tempfile.TemporaryDirectory() as td:
            def tone(name, vol):
                p = os.path.join(td, name)
                r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=1000:duration=6",
                                    "-af", f"volume={vol}dB", "-ar", "48000", p], capture_output=True, text=True, timeout=60)
                return p if r.returncode == 0 else None
            loud, quiet = tone("loud.wav", 12), tone("quiet.wav", -10)   # lavfi sine starts at 1/8 (about -18 dBFS)
            sl, sq = (max_short_term(loud) if loud else None), (max_short_term(quiet) if quiet else None)
            check_("v2.60.0 a real loud tone breaks the -18 LUFS short-term ceiling", sl is not None and sl > -18.0)
            check_("v2.60.0 a real quiet tone stays under it", sq is not None and sq <= -18.0)
            vid = os.path.join(td, "bcast.mp4")
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=6:size=160x90:rate=25",
                                "-f", "lavfi", "-i", "sine=frequency=1000:duration=6", "-af", "volume=12dB", "-ar", "48000",
                                "-ac", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", vid],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                out = subprocess.run([sys.executable, os.path.abspath(__file__), vid, "--format", "broadcast-eu-1080",
                                      "--allow-silence"], capture_output=True, text=True, timeout=300).stdout
                check_("v2.60.0 --format broadcast-eu-1080 applies ±0.5 LU to a real file",
                       "want -23.0±0.5" in out)
                check_("v2.60.0 ...and FAILs the -18 LUFS short-term ceiling on a loud one",
                       "[FAIL] short-term ceiling" in out)

    # the file-size ceiling: pass, fail with the bitrate that fits, and skip when none is named
    ok_, det_, hint_ = size_verdict(40 * MB, 50, 30.0, 128.0)
    check_("HR-05 a file under the cap passes, and names both", ok_ is True and "40.0 MB" in det_ and "cap 50" in det_)
    ok_, det_, hint_ = size_verdict(60 * MB, 50, 30.0, 128.0)
    check_("HR-05 a file over the cap FAILs, naming its size and the cap",
           ok_ is False and "60.0 MB" in det_ and "50 MB cap" in det_)
    check_("HR-05 ...and says to lower the target bitrate, with the total that fits (50 MB over 30 s = 13333 kb/s)",
           "lower the target bitrate" in hint_ and "13333 kb/s" in hint_ and "13205 kb/s for the video" in hint_)
    check_("HR-05 ...and to record that the file compresses harder", "compresses harder" in hint_)
    check_("HR-05 no ceiling named → SKIP, never a pass or a fail", size_verdict(60 * MB, None, 30.0)[0] is None)
    check_("HR-05 exactly at the cap passes", size_verdict(50 * MB, 50, 30.0)[0] is True)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(os.path.dirname(here), "assets", "delivery-formats.json"), encoding="utf-8") as fh:
        presets = json.load(fh)["formats"]
    check_("HR-05 no preset carries a default cap — it is added only when a delivery names one",
           not any("max_mb" in p for p in presets.values()))
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "cap.mp4")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=2:size=160x90:rate=24",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:a", "aac", "-shortest",
                            "-pix_fmt", "yuv420p", p], capture_output=True, timeout=60)
            if os.path.isfile(p):
                base = [sys.executable, os.path.abspath(__file__), p, "--width", "160", "--height", "90",
                        "--target-lufs", "-14", "--allow-silence"]
                r1 = subprocess.run(base + ["--max-mb", "0.001"], capture_output=True, text=True, timeout=120)
                r2 = subprocess.run(base, capture_output=True, text=True, timeout=120)
                r3 = subprocess.run(base + ["--max-mb", "500"], capture_output=True, text=True, timeout=120)
                check_("HR-05 a real encode over --max-mb FAILs and OVERALL fails with it",
                       "[FAIL] file size" in r1.stdout and "OVERALL: FAIL" in r1.stdout and r1.returncode == 1)
                check_("HR-05 ...with no cap the size line is a SKIP and is not counted",
                       "[SKIP] file size" in r2.stdout)
                check_("HR-05 ...and under a generous cap it is a PASS", "[PASS] file size" in r3.stdout)

    # (v2.48.0, project switch upload-master) off → the size equals the preset, as before; on → the preset's shape at a
    # larger size passes, named as lifted; on, outside what it allows → another shape, or not larger, still fails
    lf = "lifted by project switch `upload-master` (the platform re-encodes 1080 uploads badly)"
    rv = resolution_verdict
    check_("upload-master off: the size must equal the preset, as before",
           rv(1080, 1920, 1080, 1920) == (True, "1080x1920 (want 1080x1920)") and rv(2160, 3840, 1080, 1920)[0] is False)
    check_("upload-master on: 2160x3840 for a 1080x1920 preset passes, named as lifted",
           rv(2160, 3840, 1080, 1920, lf)[0] is True and lf in rv(2160, 3840, 1080, 1920, lf)[1])
    check_("upload-master on: 1620x2026 (1.5x rounded to even) of a 1080x1350 preset is its shape within a pixel",
           rv(1620, 2026, 1080, 1350, lf)[0] is True)
    check_("upload-master on, outside what it allows: another shape, the preset's own size, or smaller still FAILs",
           rv(3840, 2160, 1080, 1920, lf)[0] is False and "not the preset's shape" in rv(3840, 2160, 1080, 1920, lf)[1]
           and rv(1080, 1920, 1080, 1920, lf)[0] is False and "the delivery itself" in rv(1080, 1920, 1080, 1920, lf)[1]
           and rv(720, 1280, 1080, 1920, lf)[0] is False)
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as td2:
            os.makedirs(os.path.join(td, "00-brief")); os.makedirs(os.path.join(td, "10-export"))
            cp = os.path.join(td, "00-brief", "CHECKPOINT.md")
            open(cp, "w").write("Job:        uq-1\nSwitches:   none\n")

            def enc_(name, size, where=None):
                p = os.path.join(where or os.path.join(td, "10-export"), name)
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=duration=2:size={size}:rate=24",
                                "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:a", "aac", "-shortest",
                                "-pix_fmt", "yuv420p", p], capture_output=True, timeout=60)
                return p
            big, wide, out = enc_("up_v1.mp4", "320x180"), enc_("wide_v1.mp4", "320x240"), enc_("up_v1.mp4", "320x180", td2)
            qc = lambda f, *x: subprocess.run([sys.executable, os.path.abspath(__file__), f, "--width", "160", "--height", "90",
                                               "--target-lufs", "-14", "--allow-silence", *x],
                                              capture_output=True, text=True, timeout=120)
            if os.path.isfile(big) and os.path.isfile(wide):
                r0 = qc(big)
                check_("upload-master: a larger file without the flag FAILs its resolution, as before",
                       "[FAIL] resolution: 320x180 (want 160x90)" in r0.stdout and "upload master" not in r0.stdout)
                r1 = qc(big, "--upload-master")
                check_("upload-master off: --upload-master is refused before anything is measured, naming the switch",
                       r1.returncode == 1 and "REFUSED" in r1.stderr and "`upload-master`" in r1.stderr and not r1.stdout)
                open(cp, "w").write("Job:        uq-1\nSwitches:   upload-master — the platform re-encodes 1080 uploads badly\n")
                r2 = qc(big, "--upload-master")
                check_("upload-master on: 320x180 of a 160x90 spec passes, lifted, and the report names the upload copy",
                       "[PASS] resolution: 320x180, an upload master" in r2.stdout and lf in r2.stdout
                       and "upload master: the job's extra upload copy, not the delivery" in r2.stdout)
                r3 = qc(wide, "--upload-master")
                check_("upload-master on, outside what it allows: another shape (320x240) still FAILs",
                       "[FAIL] resolution: 320x240" in r3.stdout and r3.returncode == 1)
                r4, r5 = qc(out, "--upload-master"), qc(out, "--upload-master", "--job", td)
                check_("upload-master: a file outside the job is refused without --job, and lifted with it",
                       r4.returncode == 1 and "pass --job" in r4.stderr and "[PASS] resolution: 320x180" in r5.stdout)

    # (v2.49) the one-frame flash — on synthetic cells, then on real encodes when ffmpeg is here
    import random as _rnd
    _rnd.seed(7)
    G2 = FLASH_GRID * FLASH_GRID

    def fr(v=60, box=None, bv=230, noise=3):
        b = bytearray(min(255, max(0, v + _rnd.randint(-noise, noise))) for _ in range(G2))
        if box:
            x0, y0, w, h = box
            for y in range(y0, y0 + h):
                for x in range(x0, x0 + w):
                    b[y * FLASH_GRID + x] = bv
        return bytes(b)
    BOX = (4, 20, 24, 6)                                                    # a lockup: 144 cells
    steady = [fr() for _ in range(48)]
    kinds = lambda F_, **k: [(f, x) for f, x, _ in flash_frames(F_, 24.0, **k)]
    check_("flash: a steady picture has none", kinds(steady) == [])
    # the production case: the lockup on frame 0, then the fade from nothing
    fade0 = [fr(box=BOX, bv=230)] + [fr(box=BOX, bv=60 + int(170 * min(1, k / 12))) for k in range(47)]
    check_("flash: the lockup on frame 0 before its fade-in FAILs as a first-frame flash",
           ("0", "first frame") in [(str(f), x) for f, x in kinds(fade0)] and flash_verdict(flash_frames(fade0), 24.0)[0] is False)
    fade_ok = [fr(box=BOX, bv=60 + int(170 * min(1, k / 12))) for k in range(48)]
    check_("flash: the same fade keyed right (nothing on frame 0) passes", kinds(fade_ok) == [])
    # the same flash mid-cut: a title whose first frame shows the end state, then fades in
    mid = [fr() for _ in range(20)] + [fr(box=BOX)] + [fr(box=BOX, bv=60 + int(170 * min(1, k / 12))) for k in range(27)]
    check_("flash: a title's end state on its first frame mid-cut FAILs as a keyframe flash (frame 20)",
           (20, "keyframe flash") in kinds(mid))
    last = [fr(box=BOX, bv=230 - int(170 * min(1, k / 12))) for k in range(47)] + [fr(box=BOX)]
    check_("flash: the end state back on the last frame after a fade-out FAILs as a last-frame flash",
           (47, "last frame") in kinds(last))
    cut = [fr(60) for _ in range(20)] + [fr(180) for _ in range(28)]
    check_("flash: a hard cut is not a flash", kinds(cut) == [])
    stray = [fr(60) for _ in range(20)] + [fr(200)] + [fr(120) for _ in range(27)]
    check_("flash: a stray frame at a cut FAILs as a one-frame shot", (20, "one-frame shot") in kinds(stray))
    big = [fr() for _ in range(20)] + [fr(box=BOX)] + [fr() for _ in range(27)]
    check_("flash: a large one-frame graphic (a stray title clip) FAILs as a one-frame shot", (20, "one-frame shot") in kinds(big))
    blip = [fr() for _ in range(20)] + [fr(box=(2, 2, 8, 4))] + [fr() for _ in range(27)]
    check_("flash: a small one-frame graphic that never comes back only warns",
           kinds(blip) == [(20, "spike (warn)")] and flash_verdict(flash_frames(blip), 24.0)[0] is True)
    check_("flash: --allow-flash names an intended flash and passes it",
           flash_verdict(flash_frames(stray, 24.0, {20}), 24.0)[0] is True
           and "allowed: 20" in flash_verdict(flash_frames(stray, 24.0, {20}), 24.0)[1])
    if shutil.which("ffmpeg"):
        with tempfile.TemporaryDirectory() as td:
            def enc2(name, src):
                p = os.path.join(td, name)
                r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", src, "-t", "3", "-pix_fmt", "yuv420p",
                                    p], capture_output=True, text=True, timeout=60)
                return p if r.returncode == 0 else None
            box = "drawbox=x=60:y=60:w=200:h=60:t=fill"
            cases = {
                "moving test pattern": ("testsrc2=size=320x180:rate=24", None),
                "a fractal zoom": ("mandelbrot=size=320x180:rate=24", None),
                "grain": ("color=gray:size=320x180:rate=24,noise=alls=40:allf=t", None),
                "a fade-up keyed right": ("testsrc2=size=320x180:rate=24,fade=in:0:12", None),
                "frame 0 lockup, then the fade": (f"color=black:size=320x180:rate=24,{box}:color=white:enable='eq(n,0)',"
                                                  f"{box}:color=white@0.5:enable='gte(n,13)'", 0),
                "a one-frame stray at a cut": ("color=blue:size=320x180:rate=24,drawbox=x=0:y=0:w=320:h=180:color=yellow:"
                                               "t=fill:enable='eq(n,36)',drawbox=x=0:y=0:w=320:h=180:color=green:t=fill:"
                                               "enable='gte(n,37)'", 36),
                "the last frame flashes": ("testsrc2=size=320x180:rate=24,drawbox=x=0:y=0:w=320:h=180:color=red:t=fill:"
                                           "enable='eq(n,71)'", 71),
            }
            for name_, (src_, want_) in cases.items():
                p_ = enc2(name_.replace(" ", "_") + ".mp4", src_)
                fl_ = [x for x in flash_frames(frame_cells(p_) or [], 24.0) if "(warn)" not in x[1]] if p_ else None
                check_(f"flash, a real encode — {name_}: " + ("none" if want_ is None else f"FAIL at frame {want_}"),
                       fl_ is not None and ([f for f, _, _ in fl_] == [] if want_ is None else want_ in [f for f, _, _ in fl_]))

    print("-" * 60)
    print("selftest OK — the silencedetect parser, a clamped negative start, no phantom run from an "
          "unterminated silence, a floor that a real room-tone bed cannot trip, the evaluation "
          "tier's refusal, the poster frame (fade-up, flat card, picture) on real encodes, and the "
          "file-size ceiling (HR-05: pass, fail with the bitrate that fits, skip), and the upload master (project "
          "switch upload-master: refused without it, the preset's shape at a larger size with it)"
          if ok else "selftest FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    rc = main()
    sys.exit(rc if isinstance(rc, int) else 0)
