#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""slop_check.py — batch-level realism QA: does this delivery read as a batch, or as a template?

A single video can pass every per-clip check and the BATCH can still fail, because sameness across
the set is itself the tell — to viewers, who pattern-match a template within two exposures, and to
platforms, which demote unoriginal mass-produced content. This script measures the mechanical half of
the variance rule in ../references/realism-qa.md section 5.

It cannot see composition, performance, or whether the hooks are actually different ideas. Those stay
human. What it CAN do is catch the batch that quietly collapsed onto one duration, one loudness, one
framing spec — which is the failure mode of an assembly line running unattended.

Usage
-----
  python3 slop_check.py <folder>                     # every video in the folder
  python3 slop_check.py <folder> --window 35 55      # the brief's duration window
  python3 slop_check.py <folder> --min-spread 8      # required duration spread, seconds
  python3 slop_check.py <folder> --json
  python3 slop_check.py <folder> --loudness          # also measure integrated loudness per file

Checks by default: duration window, duration spread, distinct durations, resolution consistency,
frame-rate consistency. With --loudness it additionally measures integrated LUFS per file (via
ffmpeg loudnorm, single-pass measure, no re-encode) and fails the batch if any file is off target or
if the spread across the batch is audible. That pass is slow (roughly real-time-ish per file), which
is why it is opt-in; per-file spec compliance is export_qc.py's job.

Requires ffprobe, and ffmpeg for --loudness.
Exit codes: 0 PASS · 1 FAIL · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, json, os, re, statistics, subprocess, sys

EXTS = (".mp4", ".mov", ".m4v", ".webm")


def probe(path: str) -> dict | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
             path], capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        d = json.loads(out.stdout)
    except json.JSONDecodeError:
        return None
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    num, _, den = (v.get("r_frame_rate") or "0/1").partition("/")
    try:
        fps = round(float(num) / float(den or 1), 3)
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    try:
        dur = float(d.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        dur = 0.0
    return {"file": os.path.basename(path), "duration": round(dur, 2),
            "w": v.get("width"), "h": v.get("height"), "fps": fps}


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


def measure_lufs(path: str) -> float | None:
    """Integrated loudness via ffmpeg loudnorm in measure mode — no re-encode, no output file."""
    try:
        out = subprocess.run(
            ["ffmpeg", "-nostdin", "-i", path, "-af", "loudnorm=print_format=json",
             "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    m = re.findall(r'"input_i"\s*:\s*"(-?[\d.]+)"', out.stderr)
    try:
        return round(float(m[-1]), 1) if m else None
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--window", nargs=2, type=float, metavar=("MIN", "MAX"), default=[35.0, 55.0])
    ap.add_argument("--format", dest="fmt", default=None,
                    help="a preset name from assets/delivery-formats.json. Checks the batch against "
                         "the client's actual delivery spec (resolution, fps, loudness) instead of "
                         "only checking it is internally consistent.")
    ap.add_argument("--min-spread", type=float, default=6.0,
                    help="required spread between shortest and longest, seconds (default 6)")
    ap.add_argument("--min-distinct", type=int, default=0,
                    help="required distinct rounded durations; default = ceil(n/2)")
    ap.add_argument("--loudness", action="store_true",
                    help="also measure integrated LUFS per file (slow; needs ffmpeg)")
    ap.add_argument("--target-lufs", type=float, default=None,
                    help="loudness target. No house figure: -14 is streaming, EU broadcast is -23 "
                         "(references/delivery-format.md). Comes from --format, or pass it.")
    ap.add_argument("--lufs-tolerance", type=float, default=1.5)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    fmt = load_format(a.fmt) if a.fmt else None
    if fmt:
        if "--target-lufs" not in sys.argv:
            a.target_lufs = fmt.get("loudness_lufs", a.target_lufs)
    if a.target_lufs is None:
        print("error: no loudness target — pass --format PRESET or --target-lufs. There is no house "
              "default (-14 streaming vs -23 EU broadcast is a client x platform decision; "
              "references/delivery-format.md).", file=sys.stderr)
        return 2
        print(f"format preset: {a.fmt} — {fmt['label']} · {fmt['width']}x{fmt['height']} · "
              f"{fmt.get('fps_default')}fps · {fmt.get('loudness_lufs')} LUFS")

    if not os.path.isdir(a.folder):
        print(f"error: not a folder: {a.folder}", file=sys.stderr)
        return 2
    files = sorted(os.path.join(a.folder, f) for f in os.listdir(a.folder) if f.lower().endswith(EXTS))
    if not files:
        print(f"error: no video files in {a.folder}", file=sys.stderr)
        return 2

    infos = []
    for f in files:
        i = probe(f)
        if i is None:
            print(f"error: ffprobe failed on {f} (is ffmpeg installed?)", file=sys.stderr)
            return 2
        infos.append(i)

    durs = [i["duration"] for i in infos]
    lo, hi = a.window
    spread = max(durs) - min(durs)
    distinct = len({round(d) for d in durs})
    need_distinct = a.min_distinct or max(2, (len(infos) + 1) // 2)
    specs = {(i["w"], i["h"]) for i in infos}
    rates = {i["fps"] for i in infos}
    out_of_window = [i for i in infos if not (lo - 0.5 <= i["duration"] <= hi + 0.5)]

    if a.loudness:
        for i, f in zip(infos, files):
            i["lufs"] = measure_lufs(f)

    checks = [
        ("duration in window", not out_of_window,
         f"{len(out_of_window)} file(s) outside {lo:g}–{hi:g}s"
         + (": " + ", ".join(f"{i['file']} ({i['duration']}s)" for i in out_of_window[:5]) if out_of_window else "")),
        ("duration spread", spread >= a.min_spread,
         f"spread {spread:.1f}s (need >= {a.min_spread:g}s) — min {min(durs):.1f} / max {max(durs):.1f} / median {statistics.median(durs):.1f}"),
        ("distinct durations", distinct >= need_distinct,
         f"{distinct} distinct rounded durations across {len(infos)} files (need >= {need_distinct})"),
        ("consistent resolution", len(specs) == 1,
         f"{len(specs)} resolution(s): {sorted(str(s) for s in specs)}"),
        ("consistent frame rate", len(rates) == 1,
         f"{len(rates)} frame rate(s): {sorted(rates)}"),
    ]

    if fmt:
        want = (fmt["width"], fmt["height"])
        wrong = [i for i in infos if (i["w"], i["h"]) != want]
        checks.append((f"matches {a.fmt}", not wrong,
                       f"target {want[0]}x{want[1]}; "
                       + ("all match" if not wrong else
                          ", ".join(f"{i['file']} {i['w']}x{i['h']}" for i in wrong[:4]))))
        wf = fmt.get("fps_default")
        if wf:
            bad_fps = [i for i in infos if abs(i["fps"] - wf) > 0.5]
            checks.append((f"frame rate == {wf}", not bad_fps,
                           "all match" if not bad_fps else
                           ", ".join(f"{i['file']} {i['fps']}" for i in bad_fps[:4])))

    if a.loudness:
        vals = [i["lufs"] for i in infos if i.get("lufs") is not None]
        if not vals:
            checks.append(("loudness", False,
                           "measurement returned nothing for every file — either ffmpeg is missing, "
                           "or none of these files has an audio track (a silent delivery is itself a defect)"))
        else:
            off = [i for i in infos if i.get("lufs") is not None
                   and abs(i["lufs"] - a.target_lufs) > a.lufs_tolerance]
            checks.append(("loudness on target", not off,
                           f"target {a.target_lufs:g} LUFS +/-{a.lufs_tolerance:g}; "
                           + ("all on target" if not off else
                              ", ".join(f"{i['file']} {i['lufs']:.1f}" for i in off[:5]))))
            checks.append(("loudness spread", (max(vals) - min(vals)) <= 2 * a.lufs_tolerance,
                           f"{max(vals) - min(vals):.1f} LU between quietest and loudest"))

    failed = [n for n, ok, _ in checks if not ok]
    if a.json:
        print(json.dumps({"files": infos,
                          "checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in checks],
                          "result": "FAIL" if failed else "PASS"}, indent=2))
        return 1 if failed else 0

    print(f"\nslop_check — {len(infos)} file(s) in {a.folder}\n" + "=" * 68)
    for i in infos:
        lu = f"  {i['lufs']:>6.1f} LUFS" if i.get("lufs") is not None else ("  (lufs n/a)" if a.loudness else "")
        print(f"  {i['file'][:44]:<44} {i['duration']:>6.2f}s  {i['w']}x{i['h']}  {i['fps']}fps{lu}")
    print("-" * 68)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<22} {detail}")
    print("-" * 68)
    print("  Mechanical checks only. Still verify by eye, per realism-qa.md section 5:")
    print("    - >=3 distinct opening framings      - >=3 distinct settings")
    print("    - no presenter >~40% of the batch    - >=4 distinct hook TYPES (not just wordings)")
    print("    - not every row scored with music")
    print("=" * 68)
    if failed:
        print(f"  RESULT: FAIL — {', '.join(failed)}")
        print("  A batch that collapsed onto one shape reads as a template. Vary it before delivery.")
        return 1
    print("  RESULT: PASS (mechanical)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
