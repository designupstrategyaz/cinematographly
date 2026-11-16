#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
build_fcpxml.py — turn a filed project folder into an interchange rough-cut (.fcpxml) that
**DaVinci Resolve imports**: video clips end-to-end in scene order, the matching VO under each, and
beat markers from the music BPM. On Resolve Studio 21.1+ the MCP server that ships inside Resolve can
build the timeline NATIVELY through `run_script` (references/editing-and-audio.md § Automating); this
FCPXML is the portable fallback, and the only route when no live Resolve is reachable. Either way the
editor opens ~80% assembled.

Runs on the Mac (stdlib only). Reads the clips that pull_finals.py already filed:
  03-clips/  and  04-broll/  → video, in scene order (by the <SHOT> token in the filename)
  05-voice/                  → connected audio under the clip with the same <SHOT>
Writes  07-edit/<slug>-rough.fcpxml.

Order comes from the filename's shot token: INTRO, S0B, S1-C1, S1-C2, S2, S2B, S3, S4, B1…, CTA.

Usage:
  python3 build_fcpxml.py --project ~/<project>/creative/videos/<job-folder> \\
      --slug acme-spring-tuneup --bpm 120
  # options: --fps 30 --width 1080 --height 1920 --clip-seconds 5 --durations durations.json

Honest note: a hand-built FCPXML is a *scaffold*. Import into DaVinci Resolve (File ▸ Import ▸
Timeline ▸ Import AAF, EDL, XML…). The robust path is the Resolve MCP building the timeline directly
from the bin (import → create timeline → markers → sync). Beat markers use a steady BPM grid — nudge
to taste in the edit.

**Transition handle mechanism — read this before planning a dissolve at any join.** Every clip has
two durations that matter here, and they are NOT the same thing:
  - the **asset**'s duration = the TRUE full length of the source file on disk (via ffprobe, always,
    regardless of `--durations`) — this is what tells Resolve how many frames genuinely exist to
    extend into.
  - the **asset-clip**'s duration = what actually plays on the timeline — the `--durations` override
    for that shot if you gave one, else the same full length.
If you don't pass `--durations`, every clip plays its FULL generated length (including any 1–2s
editorial handle baked in at generation time per ai-generation.md) with **zero spare frames left** —
dropping a dissolve on that join later has nothing to extend into and will eat into the adjacent
clip's needed content (exactly the failure mode editing-and-audio.md's Transitions section warns
about). To leave real overlap room for a planned dissolve: put that shot's **needed** (non-handle)
length in `durations.json` — shorter than the real file — so the asset-clip uses less than the
asset's true duration, and Resolve has genuine extra source frames on that side of the join to pull
into the dissolve once you drag it on by hand (transitions themselves are still UI-only, per
editing-and-audio.md — not written into this FCPXML). The script prints a handle-exposure summary
at the end so you can see, per clip, how much spare room (if any) is actually available before you
get to Resolve and find out the hard way.
"""
import argparse
import glob
import json
import os
import re
import sys
import subprocess
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cut_plan as CP          # noqa: E402  (3.0.0) rational rates, one conversion
import timeline_export as TE   # noqa: E402  (3.0.0) the one FCPXML writer

VIDEO_EXT = (".mp4", ".mov", ".m4v")
AUDIO_EXT = (".wav", ".m4a", ".mp3", ".aif", ".aiff")


def shot_token(path):
    return os.path.basename(path).split("_", 1)[0]


def sort_key(token):
    t = token.upper()
    if t == "INTRO":
        return (-2, 0)
    if t.startswith("S0B") or t == "S0":
        return (-1, 0)
    if t == "CTA":
        return (10_000, 0)
    m = re.match(r"S(\d+)(?:-C(\d+))?B?", t)
    if m:
        return (int(m.group(1)), int(m.group(2) or 0))
    m = re.match(r"B(\d+)", t)          # generic B-roll after the scenes
    if m:
        return (9000 + int(m.group(1)), 0)
    return (5000, 0)


def probe_seconds(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=nk=1:nw=1", path],
            capture_output=True, text=True, timeout=20)
        return float(out.stdout.strip())
    except Exception:
        return None


def rt(seconds, fps):
    """FCPXML time for `seconds`, on the nearest whole frame at `fps` (a rational rate: 24000/1001 works), reduced:
    5 s at 30 → '5s'. (3.0.0: was `round(seconds × fps)/fps` with an integer rate, never frame-exact at 23.976.)"""
    R = CP.parse_rate(fps)
    return TE.ft(CP.to_frame(seconds, R), R)


def main():
    ap = argparse.ArgumentParser(description="Build an interchange rough-cut .fcpxml (DaVinci Resolve imports it) from a filed project.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--bpm", type=float, default=0, help="music BPM for beat markers (0 = none)")
    ap.add_argument("--fps", default=None,
                    help="timeline frame rate. No house default — pass it, or --format PRESET "
                         "(takes the preset's fps_default)")
    ap.add_argument("--width", type=int, default=None,
                    help="timeline width. No house default — pass it, or --format PRESET.")
    ap.add_argument("--height", type=int, default=None,
                    help="timeline height. No house default — pass it, or --format PRESET.")
    ap.add_argument("--format", dest="fmt", default=None,
                    help="preset name from assets/delivery-formats.json; sets width/height together")
    ap.add_argument("--clip-seconds", type=float, default=5.0, help="fallback per-clip length if ffprobe unavailable")
    ap.add_argument("--durations", help="optional JSON {shot: seconds} to override lengths")
    a = ap.parse_args()

    # No house format. A timeline built at one client's resolution and handed to another is a
    # silent defect that survives all the way to delivery (references/delivery-format.md).
    if a.fmt:
        import json as _json
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets",
                          "delivery-formats.json")
        try:
            with open(fp, encoding="utf-8") as fh:
                presets = _json.load(fh)
            presets = presets["formats"]
            pr = presets[a.fmt]
        except KeyError:
            print(f"error: unknown format {a.fmt!r}. Valid: {', '.join(sorted(presets))}", file=sys.stderr)
            return 2
        except OSError as e:
            print(f"error: cannot read delivery-formats.json: {e}", file=sys.stderr)
            return 2
        a.width = a.width or pr["width"]
        a.height = a.height or pr["height"]
        a.fps = a.fps or pr.get("fps_default")
    if not a.width or not a.height:
        print("error: no timeline resolution — pass --format PRESET, or --width and --height. "
              "There is no house default (references/delivery-format.md).", file=sys.stderr)
        return 2
    # ⛔ The frame rate had a silent default of 30 while the vertical-1080 preset's is 24, so a
    # timeline built with `--format vertical-1080` came out at 30 fps: every duration and every beat
    # marker in the file counted in the wrong frames, and nothing said so.
    if not a.fps:
        print("error: no timeline frame rate — pass --format PRESET (its fps_default) or --fps N. "
              "There is no house default (references/delivery-format.md).", file=sys.stderr)
        return 2

    root = os.path.abspath(os.path.expanduser(a.project))
    durs = json.load(open(os.path.expanduser(a.durations))) if a.durations else {}

    vids = []
    for lane in ("03-clips", "04-broll"):
        for p in glob.glob(os.path.join(root, lane, "*")):
            if p.lower().endswith(VIDEO_EXT):
                vids.append(p)
    # ⛔ strip_embedded_audio.py writes a `<name>_noaudio.<ext>` sibling and keeps the original, and
    # both used to land on the spine under the same shot token — the shot played twice. The stripped
    # copy is the one to cut with (its voice is external now), so its original is dropped.
    stripped = [p for p in vids if os.path.splitext(p)[0].endswith("_noaudio")]
    vids = [p for p in vids if p in stripped
            or not any(s.startswith(os.path.splitext(p)[0] + "_noaudio.") for s in stripped)]
    if not vids:
        raise SystemExit(f"No video clips found under {root}/03-clips or /04-broll — run pull_finals.py first.")
    vids.sort(key=lambda p: sort_key(shot_token(p)))

    voices = {}
    for p in glob.glob(os.path.join(root, "05-voice", "*")):
        if p.lower().endswith(AUDIO_EXT):
            voices.setdefault(shot_token(p), p)

    R = CP.parse_rate(a.fps)
    fps = float(R)
    clips, handle_report, pos = [], [], 0
    for p in vids:
        tok = shot_token(p)
        info = TE.probe(p)
        full_secs = probe_seconds(p) or a.clip_seconds       # TRUE source length, always
        used_secs = min(durs.get(tok) or full_secs, full_secs)  # what actually plays on the timeline
        full_f = CP.frames_floor(full_secs, R)
        used_f = max(1, min(CP.to_frame(used_secs, R), full_f))
        handle_report.append((tok, used_f / fps, full_f / fps, (full_f - used_f) / fps))
        c = {"shot": tok, "path": p, "asset_frames": full_f, "in": 0, "out": used_f, "offset": pos,
             "audio_channels": info.get("audio_channels", 0), "vo": None, "markers": []}
        if tok in voices:
            vp = voices[tok]
            vsecs = probe_seconds(vp) or used_secs
            vf = CP.frames_floor(vsecs, R)
            c["vo"] = {"path": vp, "seconds": vsecs, "asset_frames": vf, "frames": max(1, min(vf, used_f)),
                       "channels": TE.probe(vp).get("audio_channels") or 2}
        clips.append(c)
        pos += used_f
    total_f = pos
    n_markers = 0
    if a.bpm > 0:
        beat, n, t = 60.0 / a.bpm, 0, 0.0
        while CP.to_frame(t, R) < total_f:
            n += 1
            f = CP.to_frame(t, R)
            for c in clips:
                if c["offset"] <= f < c["offset"] + c["out"] - c["in"]:
                    c["markers"].append((f - c["offset"], "downbeat" if n % 4 == 1 else "beat"))
                    n_markers += 1
                    break
            t += beat
    model = {"name": a.slug, "project": f"{a.slug}-rough", "rate": R, "width": a.width, "height": a.height,
             "clips": clips, "frames": total_f}
    doc = TE.write_fcpxml(model)
    outdir = os.path.join(root, "07-edit")
    os.makedirs(outdir, exist_ok=True)
    outp = os.path.join(outdir, f"{a.slug}-rough.fcpxml")
    open(outp, "w", encoding="utf-8").write(doc)
    probs = TE.check_fcpxml(doc, R)
    wf = "checked ✓ (whole frames, gapless, ranges inside each file)" if not probs else "CHECK: " + "; ".join(probs)
    print(f"Wrote {outp}")
    print(f"  {len(vids)} video clips, {sum(1 for v in vids if shot_token(v) in voices)} with VO, "
          f"{n_markers} beat markers, total {total_f / fps:.1f}s @ {CP.rate_str(R)}fps.  {wf}")
    print("Import into DaVinci Resolve: File ▸ Import ▸ Timeline ▸ Import AAF, EDL, XML…  (Prefer the Resolve MCP for a "
          "native timeline build; with a cut plan, timeline_export.py writes the same file from CUTS.json.)")

    print("\nTransition handle exposure (used length vs. true source length — see docstring):")
    any_handle = False
    for tok, used_secs, full_secs, handle in handle_report:
        if handle > 0.05:
            any_handle = True
            print(f"  {tok:<10} used {used_secs:5.2f}s / source {full_secs:5.2f}s  -> "
                  f"~{handle:.2f}s of handle available for a dissolve on this clip's tail")
        else:
            print(f"  {tok:<10} used {used_secs:5.2f}s / source {full_secs:5.2f}s  -> "
                  f"NO spare handle — a dissolve here will eat into adjacent content")
    if not any_handle:
        print("  (No clip has spare handle — every join is effectively a hard cut unless you pass "
              "--durations with each dissolve shot's needed length shorter than its real file.)")


def xml(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


if __name__ == "__main__":
    rc = main()
    sys.exit(rc if isinstance(rc, int) else 0)
