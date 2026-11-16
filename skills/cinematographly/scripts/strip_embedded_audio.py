#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
strip_embedded_audio.py — find generated character clips that carry their own embedded audio
AND have a separate external VO file for the same shot, and produce a no-audio sibling so the
two can never end up doubled/clashing on the timeline.

Why this exists: dialogue clips using generation-side audio-driven lipsync legitimately carry
their own audio — it IS the VO, generated together with the mouth movement. Leave those alone.
But whenever a shot ends up with a SEPARATE external VO track instead — the edit-side lipsync
fallback, a line re-recorded/re-approved after the clip was already generated, or a "silent"
generation that the model didn't actually render silent — the clip's own embedded audio has to
be removed before the external VO goes on the timeline. Leaving both in the mix means the
model's own (often mismatched, sometimes mumbled or wrong-language) audio bleeds in under the
correct line. This has to be an explicit step, not an assumption, because the failure is easy to
miss on a quick review: the picture looks right and the *correct* VO is audible over the top of
the buried second audio source, so it only shows up as an odd hash/doubling in the full mix.

Rule this script applies, per shot: a video in 03-clips/<SHOT>_... is checked against
05-voice/<SHOT>_... (matched on the same <SHOT> token used everywhere else in this pipeline,
see pm-workflow.md naming convention).
  - Video has audio AND a matching 05-voice file exists -> the external VO is authoritative.
    The clip's embedded audio is redundant and gets stripped (a `_noaudio` sibling is written).
  - Video has audio AND no matching 05-voice file exists -> assumed to be a generation-side
    audio-driven-lipsync clip where the embedded audio IS the VO. Left untouched, but reported
    so you can eyeball that assumption rather than it silently going unchecked.
  - Video has no audio stream at all -> nothing to do, reported for completeness.

Non-destructive, matches the project's "never overwrite, keep an audit trail" convention:
writes a `<name>_noaudio.<ext>` sibling next to the original (stream-copy, no re-encode, so it's
instant and lossless) rather than modifying anything in place. Swap the `_noaudio` version into
the timeline in place of the original once you're ready.

Usage:
  python3 strip_embedded_audio.py --project ~/<project>/creative/videos/<job-folder>
  python3 strip_embedded_audio.py --project <dir> --check      # report only, write nothing
  python3 strip_embedded_audio.py --project <dir> --broll-too  # also scan 04-broll/ (b-roll
                                                                 # should already be generated
                                                                 # sound:off — this is a
                                                                 # belt-and-braces check, not
                                                                 # the primary use case)

Runs on the machine that holds the project folder (stdlib + ffmpeg/ffprobe on PATH only).
"""
import argparse
import glob
import json
import os
import subprocess
import sys

VIDEO_EXT = (".mp4", ".mov", ".m4v")
AUDIO_EXT = (".wav", ".m4a", ".mp3", ".aif", ".aiff")


def shot_token(path):
    return os.path.basename(path).split("_", 1)[0]


def has_audio_stream(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "a", "-show_entries",
             "stream=index", "-of", "json", path],
            capture_output=True, text=True, timeout=20)
        data = json.loads(out.stdout or "{}")
        return bool(data.get("streams"))
    except Exception as e:
        print(f"  ! ffprobe failed on {path}: {e}", file=sys.stderr)
        return None  # unknown, not "no"


def strip_audio(path):
    root, ext = os.path.splitext(path)
    outp = f"{root}_noaudio{ext}"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", path, "-c:v", "copy", "-an", outp],
        check=True)
    return outp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--check", "--dry-run", dest="check", action="store_true",
                     help="report only, write nothing")
    ap.add_argument("--broll-too", action="store_true", help="also scan 04-broll/")
    a = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(a.project))
    voice_tokens = {shot_token(p) for p in glob.glob(os.path.join(root, "05-voice", "*"))
                    if p.lower().endswith(AUDIO_EXT)}

    lanes = ["03-clips"] + (["04-broll"] if a.broll_too else [])
    clips = []
    for lane in lanes:
        for p in sorted(glob.glob(os.path.join(root, lane, "*"))):
            if p.lower().endswith(VIDEO_EXT) and "_noaudio" not in os.path.basename(p):
                clips.append(p)

    if not clips:
        raise SystemExit(f"No video clips found under {[os.path.join(root, l) for l in lanes]}.")

    stripped, kept_lipsync, silent, unknown = [], [], [], []
    for p in clips:
        tok = shot_token(p)
        audio = has_audio_stream(p)
        matched_vo = tok in voice_tokens
        if audio is None:
            unknown.append(p)
            continue
        if not audio:
            silent.append(p)
            continue
        if matched_vo:
            if a.check:
                stripped.append((p, None))
            else:
                outp = strip_audio(p)
                stripped.append((p, outp))
        else:
            kept_lipsync.append(p)

    print(f"Scanned {len(clips)} clip(s) under {', '.join(lanes)} in {root}\n")

    if stripped:
        verb = "would strip" if a.check else "stripped"
        print(f"{verb.capitalize()} embedded audio (external VO found in 05-voice/):")
        for p, outp in stripped:
            tag = f" -> {os.path.basename(outp)}" if outp else ""
            print(f"  {os.path.basename(p)}{tag}")
        print()
    if kept_lipsync:
        print("Left untouched — no matching 05-voice file, assumed audio-driven lipsync "
              "(embedded audio IS the VO). Double-check this assumption if that's wrong:")
        for p in kept_lipsync:
            print(f"  {os.path.basename(p)}")
        print()
    if silent:
        print("Already silent — nothing to do:")
        for p in silent:
            print(f"  {os.path.basename(p)}")
        print()
    if unknown:
        print("Could not probe (see stderr above) — check manually:", file=sys.stderr)
        for p in unknown:
            print(f"  {os.path.basename(p)}", file=sys.stderr)

    if a.check and stripped:
        print("Re-run without --check to write the _noaudio siblings.")


if __name__ == "__main__":
    main()
