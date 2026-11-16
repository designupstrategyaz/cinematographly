#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
detect_beats.py — analyze the chosen music track for tempo + real beat positions, and fill them
into `resolve-production-console.py` (the ONE production/editing-setup Resolve console script
this skill ships — see that file's docstring: one for production, one for render, nothing else).
This script does not generate its own standalone console script; it writes a copy of the shared
template with MARKERS populated from real analysis.

Why this beats a steady BPM grid: `build_fcpxml.py --bpm` (and the "tap the beats live with M"
technique in editing-and-audio.md) both assume — or require manually re-creating — a perfectly
steady grid from one BPM number. Real tracks drift a little and rarely start exactly on a
downbeat. This script analyzes the actual chosen audio file and finds where the beats really
are, still with no live Resolve MCP connection required — analysis runs here.

Usage:
  python3 detect_beats.py MUSIC_FILE.mp3 --project <that dir> --format vertical-1080
  python3 detect_beats.py MUSIC_FILE.mp3 --project <dir> --fps 25 --offset-seconds 2.5

  --project            the video project dir — the filled-in script is written to
                        07-edit/resolve-production-console.py there (falls back to next to the
                        track if --project is omitted).
  --offset-seconds     how many seconds into the TIMELINE the music actually starts (e.g. after a
                        3s cold-open hook before the bed track comes in) — every marker is shifted
                        by this amount so it lands correctly relative to timeline frame 0, not the
                        audio file's own frame 0. Default 0 (music starts at the top).
  --fps / --format     the TIMELINE's frame rate, or a delivery preset whose fps_default it takes.
                        No default — markers are frame numbers, and a wrong rate drifts every bar.
  --out                override the output path entirely (skips the --project default location).

⚠️ SUPERSEDES IN PLACE (2026-10-26, v2.39.0; author: "move the sound track to match the cuts … cuts are based
on motion and object analysis, not the score itself"). Previously this script wrote EVERY beat as a marker so the
editor could cut TO the music — and its checklist line said "big cuts on downbeats", which the 38-ad measure had
already superseded (cuts land on a beat no more often than chance). It now writes SPARSE markers: phrase starts
(Red) and the other bar lines (Blue), never every beat. Fitting the music TO the cut is `music_fit.py`, which
writes its own sparse markers (phrase starts, the must-hits, the cut nudges) into the same console script.

The analysis is music_fit.py's: Beat This! when installed (beats and downbeats), librosa when installed, and
otherwise the numpy tracker that needs nothing but ffmpeg — so librosa is no longer required.
"""
import argparse
import os
import re
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("track", help="path to the chosen music file")
    ap.add_argument("--project", help="video project dir — output goes to 07-edit/resolve-production-console.py there")
    ap.add_argument("--fps", type=int, default=None,
                    help="timeline frame rate. No house default — pass it, or --format PRESET")
    ap.add_argument("--format", dest="fmt", default=None,
                    help="preset name from assets/delivery-formats.json; takes its fps_default")
    ap.add_argument("--offset-seconds", type=float, default=0.0,
                     help="seconds into the timeline where the music actually starts")
    ap.add_argument("--out", help="override the output path entirely")
    a = ap.parse_args()

    # ⛔ The markers are FRAME numbers, so the frame rate is not a detail. The old default was 30,
    # the vertical-1080 preset's is 24: on that timeline a beat at t seconds lands at 1.25·t — the
    # grid drifts off the music further every bar, and a drifting grid is worse than no grid.
    if a.fmt and not a.fps:
        import json
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets",
                          "delivery-formats.json")
        try:
            with open(fp, encoding="utf-8") as fh:
                a.fps = json.load(fh)["formats"][a.fmt]["fps_default"]
        except KeyError:
            raise SystemExit(f"unknown format {a.fmt!r} — the presets are in assets/delivery-formats.json")
    if not a.fps:
        raise SystemExit("no frame rate — pass --fps N (the timeline's real rate) or --format PRESET. "
                         "There is no house default (references/delivery-format.md).")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import music_fit as MF
    track = os.path.abspath(os.path.expanduser(a.track))
    if not os.path.isfile(track):
        raise SystemExit(f"Not found: {track}")
    print(f"Analyzing {os.path.basename(track)} …")
    m = MF.analyse(track, "auto")
    tempo = m["tempo"]
    phrases = set(round(p, 4) for p in m["phrases"])
    print(f"Detected tempo: {tempo:.1f} BPM  |  {len(m['bars'])} bars over {m['duration']:.1f}s, {m['engine']} grid "
          f"(downbeat confidence {m['confidence']['downbeats']})")
    beats = []
    for d in m["downbeats"]:
        shifted = float(d) + a.offset_seconds
        if shifted < 0:
            continue  # music offset pushed this bar line before the timeline starts — skip it
        beats.append({"time": shifted, "frame": int(round(shifted * a.fps)), "downbeat": round(d, 4) in phrases})

    if a.out:
        out_path = os.path.abspath(os.path.expanduser(a.out))
    elif a.project:
        out_path = os.path.join(os.path.abspath(os.path.expanduser(a.project)), "07-edit",
                                 "resolve-production-console.py")
    else:
        out_path = os.path.splitext(track)[0] + "-resolve-production-console.py"
    _fill_production_template(out_path, beats, tempo, os.path.basename(track))

    print(f"\nWrote {out_path}")
    print(f"  {len(beats)} sparse markers ({sum(1 for b in beats if b['downbeat'])} phrase starts, "
          f"{sum(1 for b in beats if not b['downbeat'])} bar lines; never every beat)")
    print("This is the skill's ONE production console script (resolve-production-console.py) "
          "with MARKERS filled in — paste it into Resolve's Workspace ▸ Console ▸ Py3 tab with "
          "the target timeline open. ENSURE_BROLL_TRACK is also on by default; edit the CONFIG "
          "block if you only want the markers.")

    print("\nFirst 8 markers (mm:ss.mmm | frame @ {}fps | type):".format(a.fps))
    for b in beats[:8]:
        mm, ss = divmod(b["time"], 60)
        print(f"  {int(mm):02d}:{ss:06.3f}  frame {b['frame']:>6}  {'PHRASE' if b['downbeat'] else 'bar'}")


def _fill_production_template(out_path, beats, tempo, track_name):
    """Load resolve-production-console.py (the shared template, next to this script) and splice
    in a populated MARKERS list. Never generates a bespoke script shape of its own — this skill
    ships exactly two Resolve console scripts (production, render); this keeps it that way."""
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resolve-production-console.py")
    template = open(template_path, encoding="utf-8").read()

    marker_lines = []
    for b in beats:
        color = "Red" if b["downbeat"] else "Blue"
        name = "Phrase" if b["downbeat"] else "Bar"
        marker_lines.append(f"    ({b['frame']}, {color!r}, {name!r}),")
    markers_block = "MARKERS = [\n" + "\n".join(marker_lines) + "\n]  # __DETECT_BEATS_MARKERS__"

    placeholder_re = re.compile(r"MARKERS = \[\]  # __DETECT_BEATS_MARKERS__")
    if not placeholder_re.search(template):
        raise RuntimeError(
            f"resolve-production-console.py's MARKERS placeholder not found — the template at "
            f"{template_path} may have changed shape; update this splice accordingly.")
    filled = placeholder_re.sub(markers_block, template, count=1)
    filled = filled.replace(
        '"""\nDaVinci Resolve — the ONE production/editing-setup console script',
        f'"""\nFilled in by detect_beats.py from "{track_name}" (~{tempo:.1f} BPM, {len(beats)} sparse markers).\n\n'
        f'DaVinci Resolve — the ONE production/editing-setup console script',
        1,
    )

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(filled)


if __name__ == "__main__":
    main()
