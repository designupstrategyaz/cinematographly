#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
build_srt.py — auto-build a timed .srt from the LOCKED script text + each shot's real VO/clip
duration, instead of hand-timing captions or (never do this on a locked-audio client) letting
Resolve auto-transcribe. This is the "practical alternative" editing-and-audio.md already
prescribes for the confirmed Resolve-API gap (Timeline has no scriptable way to set subtitle
text/timing, and CreateSubtitlesFromAudio just re-transcribes, which would reword a locked script).

Timing source of truth: the SAME shot ordering + timeline offsets `build_fcpxml.py` computes (this
script imports it directly, so the two can never disagree about where a clip sits on the timeline).
Text source of truth: parsed straight from the approved SCRIPT.md using the exact same regexes
`estimate_duration.py` uses to find scene blocks and "Name: line" dialogue — never a fresh
transcription of the audio.

Shot-token mapping (script scene -> the `03-clips/`/`05-voice/` filename token): scene "SCENĂ N" /
"SCENE N" maps to `S{N}-C{i+1}` for the i-th dialogue line in that scene, in script order (matches
the naming convention in pm-workflow.md, where a two-speaker scene is `S{N}-C1`/`S{N}-C2`); INTRO
and CTA map to the literal tokens `INTRO`/`CTA`. This is a naming CONVENTION, not a guarantee — the
shotlist is what actually assigns filenames — so every computed token is checked against the real
files in `03-clips/` before it's trusted. A script line whose computed token has no matching clip on
disk is reported and SKIPPED, never guessed into a wrong position. Use `--shot-map shot_map.json`
(`{"SCENĂ 1 line 1": "S1-C1", ...}`) to override individual lines where the convention doesn't hold.

Caption timing per matched line: start = that shot's cumulative offset on the assembled timeline
(same accumulator as build_fcpxml.py, across 03-clips + 04-broll in scene order); duration = the
matching `05-voice/<SHOT>_...` file's real length if one exists (the actual spoken-audio duration,
the correct thing to sync a caption to), else the clip's own used length as a fallback (flagged as
approximate in the console report — check it by ear).

Usage:
  python3 build_srt.py --project <dir> --script 01-script/SCRIPT-SLUG-v3.md --slug acme-spring-tuneup
  # optional: --durations durations.json (same file you'd pass to build_fcpxml.py, for consistent
  #           offsets when clips carry an editorial handle) --shot-map shot_map.json --fps 30
Writes 08-captions/<slug>.srt (falls back to 07-edit/<slug>.srt if 08-captions/ doesn't exist).
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_fcpxml as bf          # noqa: E402  (shot_token, sort_key, probe_seconds, AUDIO_EXT)
import estimate_duration as ed     # noqa: E402  (BLOCK_RE, CHAR_RE, HEADER_RE, TEXT_OVERLAY_RE, is_speaker)

SCENE_NUM_RE = re.compile(r"(\d+)")


def extract_scenes_with_text(text):
    """Mirrors estimate_duration.parse()'s control flow exactly (same regex objects, so scene/
    speaker detection can never disagree with the tested word-count parser) but keeps the actual
    line TEXT instead of collapsing it to a word count."""
    scenes, current, in_block = [], None, False
    for raw in text.splitlines():
        mb = ed.BLOCK_RE.match(raw)
        if mb:
            if current and current["lines"]:
                scenes.append(current)
            current = {"name": mb.group(1).upper().replace("SCENA", "SCENĂ"), "lines": []}
            in_block = True
            continue
        if ed.HEADER_RE.match(raw):
            if current and current["lines"]:
                scenes.append(current)
            current, in_block = None, False
            continue
        if not in_block:
            continue
        if ed.TEXT_OVERLAY_RE.match(raw.strip()):
            continue
        m = ed.CHAR_RE.match(raw)
        if m and ed.is_speaker(m.group(1)):
            current["lines"].append((m.group(1).strip(), clean_caption_text(m.group(2))))
    if current and current["lines"]:
        scenes.append(current)
    return scenes


def clean_caption_text(line):
    line = ed.PAREN_RE.sub(" ", line)  # strip (stage directions)
    line = ed.BRACKET_RE.sub(" ", line)  # strip [editorial annotations] e.g. "[LOCKED]"
    line = line.strip().strip("*").strip()
    line = line.strip("„”\"'").strip()
    return re.sub(r"\s+", " ", line).strip()


def default_token_for(scene_name, line_index):
    name = scene_name.upper()
    if name == "INTRO":
        return "INTRO" if line_index == 0 else f"INTRO-C{line_index + 1}"
    if name == "CTA":
        return "CTA" if line_index == 0 else f"CTA-C{line_index + 1}"
    m = SCENE_NUM_RE.search(name)
    if not m:
        return None
    return f"S{m.group(1)}-C{line_index + 1}"


def srt_timestamp(seconds):
    seconds = max(seconds, 0.0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:  # rounding carry
        ms = 0
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--script", required=True, help="path to the LOCKED SCRIPT.md (relative to --project or absolute)")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--durations", help="optional JSON {shot: seconds} — same file you'd pass to build_fcpxml.py")
    ap.add_argument("--shot-map", help='optional JSON {"SCENĂ 1 line 1": "S1-C1", ...} to override the default scene->token mapping')
    a = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(a.project))
    script_path = a.script if os.path.isabs(a.script) else os.path.join(root, a.script)
    if not os.path.isfile(script_path):
        raise SystemExit(f"Script not found: {script_path}")

    durs = json.load(open(os.path.expanduser(a.durations))) if a.durations else {}
    shot_map = json.load(open(os.path.expanduser(a.shot_map))) if a.shot_map else {}

    # 1) Real timeline offsets — identical logic/order to build_fcpxml.py's main loop.
    vids = []
    for lane in ("03-clips", "04-broll"):
        for p in glob.glob(os.path.join(root, lane, "*")):
            if p.lower().endswith(bf.VIDEO_EXT):
                vids.append(p)
    if not vids:
        raise SystemExit(f"No video clips found under {root}/03-clips or /04-broll — file the clips first.")
    vids.sort(key=lambda p: bf.sort_key(bf.shot_token(p)))

    offsets, offset = {}, 0.0
    for p in vids:
        tok = bf.shot_token(p)
        used_secs = durs.get(tok) or bf.probe_seconds(p) or 5.0
        offsets[tok] = offset
        offset += used_secs

    voice_files = {}
    for p in glob.glob(os.path.join(root, "05-voice", "*")):
        if p.lower().endswith(bf.AUDIO_EXT):
            voice_files.setdefault(bf.shot_token(p), p)

    # 2) Parse the locked script for scene/line text.
    text = open(script_path, encoding="utf-8").read()
    scenes = extract_scenes_with_text(text)
    if not scenes:
        raise SystemExit("No dialogue lines parsed from the script — check it uses [SCENE n]/[SCENĂ n] "
                          "headers and 'Name: line' dialogue (see script-format.md).")

    entries, skipped = [], []
    for scene in scenes:
        for i, (speaker, line_text) in enumerate(scene["lines"]):
            key = f"{scene['name']} line {i + 1}"
            tok = shot_map.get(key) or default_token_for(scene["name"], i)
            if not tok or tok not in offsets:
                skipped.append((key, tok, speaker, line_text))
                continue
            start = offsets[tok]
            if tok in voice_files:
                dur = bf.probe_seconds(voice_files[tok]) or (durs.get(tok) or 5.0)
                approx = False
            else:
                dur = durs.get(tok) or bf.probe_seconds(next(p for p in vids if bf.shot_token(p) == tok)) or 5.0
                approx = True
            entries.append({
                "tok": tok, "start": start, "end": start + dur, "speaker": speaker,
                "text": line_text, "approx": approx,
            })

    entries.sort(key=lambda e: e["start"])

    lines = []
    for i, e in enumerate(entries, start=1):
        lines.append(str(i))
        lines.append(f"{srt_timestamp(e['start'])} --> {srt_timestamp(e['end'])}")
        lines.append(e["text"])
        lines.append("")
    srt_body = "\n".join(lines)

    out_dir = os.path.join(root, "08-captions")
    if not os.path.isdir(out_dir):
        out_dir = os.path.join(root, "07-edit")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{a.slug}.srt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(srt_body)

    print(f"Wrote {out_path}  ({len(entries)} caption(s))")
    approx_n = sum(1 for e in entries if e["approx"])
    if approx_n:
        print(f"  ! {approx_n} caption(s) timed off clip length, not a matching 05-voice/ file — "
              f"double-check these durations by ear:")
        for e in entries:
            if e["approx"]:
                print(f"      {e['tok']}: \"{e['text'][:50]}\"")
    if skipped:
        print(f"\nSkipped {len(skipped)} script line(s) — no matching clip found for the computed "
              f"shot token (never guessed a position for these):")
        for key, tok, speaker, line_text in skipped:
            print(f"  {key} ({speaker}): computed token '{tok}' -> not found among filed clips. "
                  f"\"{line_text[:50]}\"")
        print("  Fix with --shot-map if the shotlist used different numbering than the script's "
              "scene order.")
    print("\nImport into Resolve: File ▸ Import ▸ Subtitle (or drag onto a new subtitle track). "
          "This is still the only path in — subtitle import has no scripting API (editing-and-audio.md).")


if __name__ == "__main__":
    main()
