#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
loop_music_to_length.py — stretch a chosen music bed to cover the full video by looping it with
a smooth crossfade at the seam, instead of a hard cut/restart or manual volume-keyframing in the
NLE. Also handles the reverse case (track already long enough) by trimming with a clean fade-out.

Workflow this serves: ask the user which track from the shared `creative/videos/music/` library
to use for THIS project (never pick autonomously — tracks carry a mood/identity choice that's
the user's call, see SKILL.md → Stage 5). If that track is shorter than the assembled video's
total runtime, loop it with this script rather than letting it end early or cutting it off mid-
phrase; if it's already long enough, this script just trims it cleanly instead.

How the crossfade works: ffmpeg's `acrossfade` overlaps the tail of one copy of the track with
the head of the next copy for `--crossfade` seconds, blending between them on a volume curve
(`--curve`, default a linear "tri" ramp — pass `qsin`/`hsin` for a smoother equal-power blend if
the track has a very busy tail/head). Repeats however many times are needed to clear the target
length, then trims to the exact target with its own short head/tail fade so it doesn't start or
stop on a raw waveform edge.

Usage:
  python3 loop_music_to_length.py TRACK.mp3 --target-seconds 58 --out 06-music/MUSIC_track_120bpm_v1.mp3
  python3 loop_music_to_length.py TRACK.mp3 --match-video 10-export/SLUG-v1-final.mp4
  # optional: --crossfade 2.5 --curve tri --head-fade 0.3 --tail-fade 1.5

Requires ffmpeg/ffprobe on PATH. No Python audio libraries needed (pure ffmpeg filter graph).

⚠️ SUPERSEDES IN PLACE (2026-10-26, v2.39.0; the music-to-picture council, owner's choice "B: Length and
edits"). Previously the loop crossfaded 2.5 s wherever the track's length happened to fall — mid-bar, mid-phrase,
across a transient. Now it is BAR-AWARE by default: the track is mapped (music_fit.py: beats, downbeats,
phrases), the loop jumps back from a phrase line to an earlier phrase line, each join cut 10 ms before the
downbeat with a short equal-power crossfade, so the seam lands where the music itself turns; the track's own
ending plays out at the end. `--blind` keeps the old crossfade loop, and a track with no usable grid falls back
to it with a warning. For a film whose hits must land, use `music_fit.py fit` — this tool only covers a length.
"""
import argparse
import os
import subprocess
import sys


def probe_seconds(path):
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", path],
        capture_output=True, text=True, timeout=30)
    return float(out.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("track", help="the music file the user picked")
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--target-seconds", type=float, help="target total duration in seconds")
    target.add_argument("--match-video", help="a video file — its duration (via ffprobe) becomes the target")
    ap.add_argument("--out", help="output path (default: <track-stem>_looped.<ext> next to the track)")
    ap.add_argument("--crossfade", type=float, default=2.5, help="seconds of overlap at each loop seam (default 2.5)")
    ap.add_argument("--curve", default="tri", help="ffmpeg acrossfade curve for both sides, e.g. tri, qsin, hsin (default tri)")
    ap.add_argument("--head-fade", type=float, default=0.3, help="fade-in at the very start of the final file (default 0.3s)")
    ap.add_argument("--tail-fade", type=float, default=1.5, help="fade-out at the very end of the final file (default 1.5s)")
    ap.add_argument("--blind", action="store_true", help="the old loop: a crossfade wherever the length falls")
    a = ap.parse_args()

    track = os.path.abspath(os.path.expanduser(a.track))
    if not os.path.isfile(track):
        raise SystemExit(f"Not found: {track}")

    target_seconds = a.target_seconds if a.target_seconds is not None else probe_seconds(
        os.path.abspath(os.path.expanduser(a.match_video)))
    track_seconds = probe_seconds(track)

    stem, ext = os.path.splitext(track)
    out_path = os.path.abspath(os.path.expanduser(a.out)) if a.out else f"{stem}_looped{ext}"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    print(f"Track: {os.path.basename(track)} ({track_seconds:.1f}s)  |  Target: {target_seconds:.1f}s")

    if track_seconds >= target_seconds:
        # Already long enough — trim, don't loop. Still apply a clean tail fade so the cut isn't raw.
        tail = min(a.tail_fade, target_seconds * 0.2)
        head = min(a.head_fade, target_seconds * 0.05)
        filt = (
            f"afade=t=in:st=0:d={head},"
            f"afade=t=out:st={max(target_seconds - tail, 0):.3f}:d={tail}"
        )
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", track, "-t", f"{target_seconds:.3f}",
               "-af", filt, out_path]
        subprocess.run(cmd, check=True)
        print(f"Track already >= target — trimmed to {target_seconds:.1f}s with a clean fade-out.")
        print(f"Wrote {out_path}")
        return

    if not a.blind:
        try:
            done = bar_aware_loop(track, target_seconds, out_path, a.head_fade, a.tail_fade)
        except SystemExit as e:
            done = None
            print(f"  ! no usable bar grid ({e}) — falling back to the blind crossfade loop", file=sys.stderr)
        if done:
            print(done)
            return

    crossfade = a.crossfade
    if crossfade >= track_seconds:
        raise SystemExit(
            f"--crossfade ({crossfade}s) must be shorter than the track itself ({track_seconds:.1f}s).")

    # n * track_seconds - (n-1) * crossfade >= target_seconds
    n = 1
    total = track_seconds
    while total < target_seconds:
        n += 1
        total = n * track_seconds - (n - 1) * crossfade
        if n > 50:
            raise SystemExit("Would need >50 repeats to reach the target — check --target-seconds "
                              "and --crossfade are sensible.")

    print(f"Looping {n}x with a {crossfade:.1f}s crossfade ({a.curve} curve) -> "
          f"{total:.1f}s before trim, then trimmed to {target_seconds:.1f}s.")

    inputs = []
    for _ in range(n):
        inputs += ["-i", track]

    chain = "[0:a][1:a]acrossfade=d={cf}:c1={c}:c2={c}[a1]".format(cf=crossfade, c=a.curve)
    label = "a1"
    for i in range(2, n):
        new_label = f"a{i}"
        chain += f";[{label}][{i}:a]acrossfade=d={crossfade}:c1={a.curve}:c2={a.curve}[{new_label}]"
        label = new_label

    tail = min(a.tail_fade, target_seconds * 0.2)
    head = min(a.head_fade, target_seconds * 0.05)
    chain += (
        f";[{label}]atrim=0:{target_seconds:.3f},"
        f"afade=t=in:st=0:d={head},"
        f"afade=t=out:st={max(target_seconds - tail, 0):.3f}:d={tail}[out]"
    )

    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + [
        "-filter_complex", chain, "-map", "[out]", out_path]
    subprocess.run(cmd, check=True)

    actual = probe_seconds(out_path)
    print(f"Wrote {out_path}  (actual duration {actual:.2f}s, target {target_seconds:.1f}s)")
    if abs(actual - target_seconds) > 0.2:
        print(f"  ! duration drifted by {actual - target_seconds:+.2f}s from target — "
              f"acceptable for most edits, re-check if you need frame-exact length.", file=sys.stderr)


def bar_aware_loop(track, target, out_path, head_fade=0.3, tail_fade=1.5):
    """Loop whole phrases: play the track to its last phrase line before the ending, jump back to an earlier
    phrase line as often as the length needs, then play the ending out; trim and fade to the target."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import math
    import music_fit as MF
    np = MF._np()
    M = MF.analyse(track, "auto")
    if (M.get("confidence") or {}).get("downbeats") is not None and M["confidence"]["downbeats"] < 0.02:
        raise SystemExit("the downbeat confidence is too low to loop on bar lines")
    dur = float(M["duration"])
    bar = 60.0 / M["tempo"] * M["meter"]
    end_m = (M.get("ending") or {}).get("t") or dur
    lines = [x for x in M["phrases"] if bar <= x < end_m - bar]
    if len(lines) < 2:
        raise SystemExit("fewer than two phrase lines before the ending")
    pe = lines[-1]
    need = target - dur
    # the loop body: from the earliest phrase line that keeps the body at least two phrases long
    ps = next((x for x in lines if pe - x >= 2 * 4 * bar), lines[0])
    L = pe - ps
    reps = max(1, int(math.ceil(need / L)))
    segs = [[0.0, pe]] + [[ps, pe]] * (reps - 1) + [[ps, dur]]
    plan = MF.Plan(segs, 0.0)
    x = MF.decode(track, MF.SR_OUT, 2)
    y = MF.assemble(x, MF.SR_OUT, plan, M)
    n = int(round(target * MF.SR_OUT))
    y = y[:n].copy()
    h, t = int(min(head_fade, target * 0.05) * MF.SR_OUT), int(min(tail_fade, target * 0.2) * MF.SR_OUT)
    if h > 1:
        y[:h] *= np.linspace(0, 1, h, dtype=np.float32)[:, None]
    if t > 1 and len(y) >= n:
        y[-t:] *= np.linspace(1, 0, t, dtype=np.float32)[:, None]
    MF.encode(y, MF.SR_OUT, out_path)
    return (f"Looped on phrase lines: {reps} repeat(s) of {ps:.2f}–{pe:.2f} s ({L:.2f} s, {M['tempo']:.1f} BPM, "
            f"{M['engine']} grid), joins cut before the downbeat; trimmed to {target:.1f} s.\nWrote {out_path}")


if __name__ == "__main__":
    main()
