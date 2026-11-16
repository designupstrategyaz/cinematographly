#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""contact_sheet.py — frame grids from clips, for the selects pass and the drift audit.

Two jobs, one tool:
  * SELECTS (direction.md section 4): a grid of frames sampled across each clip of a scene, so the
    silent-sequence read and the blocking check happen on real pixels, side by side.
  * DRIFT AUDIT (brand-system.md section 6): one frame per clip across many episodes in one grid —
    wardrobe/palette/set drift is invisible in sequence and loud in a grid.

What this tool is NOT: a QA verdict. It puts the pixels in front of the human; the observation
still has to be written (qa_log.py). Sampling several frames per clip specifically counters the
thumbnail trap — artifacts live mid-clip, not on the poster frame.

Usage
-----
  python3 contact_sheet.py --project <dir>                      # all of 03-clips/, 5 frames each
  python3 contact_sheet.py --project <dir> --glob "S1-*"        # one scene
  python3 contact_sheet.py --folder <any-dir-of-mp4s> --frames 3 --out sheet.png
  python3 contact_sheet.py --folder <dir> --first-frame-only    # drift-audit mode: 1 frame/clip
  python3 contact_sheet.py --clip 03-clips/_review/S3_v2.mp4 --perf   # the PERFORMANCE STRIP
  python3 contact_sheet.py --project <dir> --glob "S1-*" --perf        # one strip per clip, stacked
  python3 contact_sheet.py --selftest

  --perf samples each clip at 15 %, 50 % and 85 % and labels the tiles IN / MID / OUT — the three
  frames the 934 reference performances were coded on (specifics-catalogue.md §13). Read the strip
  against the performance card (acting-for-the-model.md §9): IN is the STATE's before, OUT the
  after, the change between MID and OUT, the gaze on its TARGET throughout. Stills are skipped —
  a still has no performance to read.

THE EVENT SHEET (v2.46) — one tile per event of a DRAFT CUT, the sheet every cut is read on before
anyone else sees it (review-and-approval.md §2a, the owner's standing contact-sheet rule):
  python3 contact_sheet.py events --project <job> --cut 07-edit/_renders/x_cut_v003.mp4
  python3 contact_sheet.py events --project <job> --cut <render> --scrub 11.6 12.6 --every 0.2   # a transition
  python3 contact_sheet.py events --project <job> --cut 10-export/<file>.mp4     # what the encoder wrote

  The events are read from the job, never typed: POSTER (frame 0, the thumbnail), every cut on the
  video tracks of 07-edit/timeline-dump.json (C1…, read 0.4 s after the cut, once a head has settled),
  every transition (X1…, its middle), every title spec in 07-edit/titles/ (its id, read 0.1 s after its
  entrance ends), every must-hit and the button in 07-edit/music/HITS.json (its id, 0.1 s after), every
  placed sound in 06-music/SFX-PLACEMENT.json (FX1…, 0.1 s after its frame) and END (the last frame).
  Tiles closer than a frame share one tile. Out: 09-qa/contact-sheets/EVENTS-<render sha8>.png and its
  .json (the render's sha256, every tile's time and ids), which `qa_log.py --gate draft` checks.
  What it cannot do: judge. It only puts each event's frame in front of the reader; a cut with no
  timeline dump has no cut tiles, and the sheet says so.

Output: 09-qa/contact-sheets/SHEET-<label>-<date>.png (or --out). Requires ffmpeg + ffprobe.
Exit codes: 0 ok · 2 usage/IO/ffmpeg error.
"""
from __future__ import annotations
import argparse, datetime as dt, fnmatch, glob, hashlib, json, math, os, shutil, subprocess, sys, tempfile

# ⛔ Stills belong here. The two competing start frames are the ONLY real candidates this pipeline
# produces, and until 2026-09-07 the dailies grid could not open one — so the frame gate's choice
# was made inside a vendor UI and left no artifact anybody could check later.
EXTS = (".mp4", ".mov", ".m4v", ".webm", ".png", ".jpg", ".jpeg", ".webp")
STILL_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, **kw)


def duration(path: str) -> float:
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_entries", "format=duration", path])
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:                                             # noqa: BLE001
        return 0.0


PERF_AT = (0.15, 0.50, 0.85)
PERF_LABELS = ("IN", "MID", "OUT")


def sample_times(dur: float, per: int, is_still: bool, perf: bool = False) -> list:
    """Where each tile is taken. Pure, so the selftest can pin it without ffmpeg."""
    if is_still:
        return [0.0]
    if perf:
        return [round(dur * f, 3) for f in PERF_AT]
    # sample AWAY from the endpoints: mid-clip is where artifacts live; the first ~0.5s is the
    # morph-settle zone and would poison a drift audit, so "first frame" is really t=0.5s
    return [0.5] if per == 1 else [max(0.2, dur * (i + 0.5) / per) for i in range(per)]


# ── the event sheet (v2.46) ────────────────────────────────────────────────────────────────────────────
# Where each event is read. A cut is read once the incoming head has settled; a title once its entrance has
# landed; a hit or a placed sound just after its frame, where the picture event it marks should be.
EVT_CUT_SETTLE = 0.4            # s after a cut [assumed: C1's head settle]
EVT_AFTER = 0.1                 # s after a title's entrance ends, a hit, or a placed sound [assumed]
EVT_ENTER_DEFAULT = 0.6         # s, a title's entrance when neither its spec nor the card names one (title_card.py's default)


def _jl(p: str):
    try:
        return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None
    except ValueError:
        return None


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def job_events(job: str, dur: float | None = None) -> tuple[list, list]:
    """Every picture event of the cut, read from the job's own files → (events, notes). Each event is
    {id, kind, at (when it happens), t (where its tile is read)}. Pure apart from reading files, so the
    selftest and mix_qa.py's waveform proof share it (one source of event truth, charter rule 5)."""
    ev, notes = [{"id": "POSTER", "kind": "poster", "at": 0.0, "t": 0.0}], []
    tl = _jl(os.path.join(job, "07-edit", "timeline-dump.json"))
    fps = 24.0
    if tl is None:
        notes.append("no 07-edit/timeline-dump.json — no cut tiles (dump the timeline: resolve-production-console.py "
                     "DUMP_TIMELINE_JSON)")
    else:
        fps = float(tl.get("fps") or 0) or 24.0
        starts, trans = set(), []
        for tn, items in (tl.get("tracks") or {}).items():
            if not str(tn).startswith("video"):
                continue
            for it in items or []:
                s = it.get("start_s") if it.get("start_s") is not None else (it.get("start") or 0) / fps
                d = it.get("duration_s") if it.get("duration_s") is not None else (it.get("duration") or 0) / fps
                if "transition" in str(it.get("type") or "").lower():
                    trans.append((float(s), float(d), str(it.get("name") or "")))
                    continue
                for x in (float(s), float(s) + float(d)):       # an insert's in and out are both cuts
                    if x > 0.5 / fps:
                        starts.add(round(x * fps) / fps)
        end_tl = max(starts, default=0.0)                      # the last clip's end is the film's end, not a cut
        cuts = sorted(x for x in starts if x < end_tl - 0.5 / fps)
        if dur:
            cuts = [x for x in cuts if x < dur - 0.5 / fps]
        for i, x in enumerate(cuts, 1):
            ev.append({"id": f"C{i}", "kind": "cut", "at": round(x, 4), "t": round(x + EVT_CUT_SETTLE, 4)})
        for i, (s, d, nm) in enumerate(sorted(trans), 1):
            ev.append({"id": f"X{i}", "kind": "transition", "at": round(s, 4), "t": round(s + d / 2, 4), "name": nm})
    card = _jl(os.path.join(job, "00-brief", "TITLE-CARD.json")) or {}
    for p in sorted(glob.glob(os.path.join(job, "07-edit", "titles", "*.title.json"))):
        base = os.path.basename(p)[: -len(".title.json")]
        if ".opt" in base:                                     # a design option, not a placed title
            continue
        s = _jl(p)
        if not isinstance(s, dict) or s.get("at_s") is None:
            notes.append(f"{os.path.relpath(p, job)}: no at_s — not on the sheet")
            continue
        k = (card.get("kinds") or {}).get(s.get("kind")) or {}
        ms = (s.get("enter") or {}).get("ms") or (k.get("enter") or {}).get("ms") or \
            ((card.get("motion") or {}).get("enter") or {}).get("ms")
        enter = float(ms) / 1000 if ms else EVT_ENTER_DEFAULT
        at = float(s["at_s"])
        ev.append({"id": str(s.get("id") or base), "kind": "title", "at": round(at, 4), "t": round(at + enter + EVT_AFTER, 4)})
    H = _jl(os.path.join(job, "07-edit", "music", "HITS.json")) or {}
    for h in H.get("hits") or []:
        if h.get("t") is None or not (h.get("priority") == "must" or h.get("want") == "button"):
            continue
        ev.append({"id": str(h.get("id") or "HIT"), "kind": "hit", "at": round(float(h["t"]), 4),
                   "t": round(float(h["t"]) + EVT_AFTER, 4)})
    P = _jl(os.path.join(job, "06-music", "SFX-PLACEMENT.json")) or {}
    pf = float(P.get("fps") or fps)
    for i, e in enumerate(P.get("events") or [], 1):
        if e.get("frame") is None:
            continue
        at = float(e["frame"]) / pf
        ev.append({"id": f"FX{i}", "kind": "sfx", "at": round(at, 4), "t": round(at + EVT_AFTER, 4),
                   "name": str(e.get("sfx") or "")})
    if dur:
        ev.append({"id": "END", "kind": "end", "at": round(dur, 4), "t": round(max(0.0, dur - 1.0 / fps), 4)})
        for e in ev:
            e["t"] = round(min(max(0.0, e["t"]), max(0.0, dur - 1.0 / fps)), 4)
    return sorted(ev, key=lambda e: (e["t"], e["id"] != "POSTER")), notes


def event_tiles(events: list, fps: float = 24.0) -> list:
    """Events whose tiles fall within one frame of each other share a tile: [{t, ids, kinds}]."""
    tiles = []
    for e in sorted(events, key=lambda e: e["t"]):
        if tiles and e["t"] - tiles[-1]["t"] < 1.0 / fps - 1e-9 and e["id"] != "POSTER" and "POSTER" not in tiles[-1]["ids"]:
            tiles[-1]["ids"].append(e["id"]); tiles[-1]["kinds"].append(e["kind"])
        else:
            tiles.append({"t": e["t"], "ids": [e["id"]], "kinds": [e["kind"]]})
    return tiles


def events_main(argv: list) -> int:
    ap = argparse.ArgumentParser(prog="contact_sheet.py events", description="the event sheet of a draft cut")
    ap.add_argument("--project", required=True, help="the job folder")
    ap.add_argument("--cut", required=True, help="the render to read (a draft cut, or the export)")
    ap.add_argument("--scrub", nargs=2, type=float, metavar=("A", "B"), help="also tile A..B (a transition)")
    ap.add_argument("--every", type=float, default=0.2, help="the scrub step in seconds (default 0.2)")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("error: ffmpeg/ffprobe not on PATH", file=sys.stderr)
        return 2
    cut = a.cut if os.path.isabs(a.cut) else os.path.join(a.project, a.cut)
    if not os.path.isfile(cut):
        print(f"error: no render at {cut}", file=sys.stderr)
        return 2
    dur = duration(cut)
    if dur <= 0:
        print(f"error: {cut} has no readable duration", file=sys.stderr)
        return 2
    events, notes = job_events(a.project, dur)
    tl = _jl(os.path.join(a.project, "07-edit", "timeline-dump.json")) or {}
    fps = float(tl.get("fps") or 0) or 24.0
    if a.scrub:
        x, n = a.scrub[0], 0
        while x <= a.scrub[1] + 1e-9 and n < 60:
            events.append({"id": f"~{x:.2f}", "kind": "scrub", "at": round(x, 4), "t": round(min(x, dur - 1 / fps), 4)})
            x += max(0.04, a.every); n += 1
    tiles = event_tiles(events, fps)
    sha = sha256_file(cut)
    tmp = tempfile.mkdtemp(prefix="evsheet_")
    for i, tile in enumerate(tiles):
        out = os.path.join(tmp, f"{i:04d}.png")
        lab = "+".join(tile["ids"])[:34].replace(":", " ").replace("'", "")
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{tile['t']:.3f}", "-i", cut, "-frames:v", "1", "-vf",
                 f"scale={a.width}:-2,drawtext=text='{lab} t={tile['t']:.2f}':x=4:y=4:fontsize=12:"
                 f"fontcolor=white:box=1:boxcolor=black@0.6", out])
        if r.returncode != 0 or not os.path.exists(out):
            r = run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{tile['t']:.3f}", "-i", cut, "-frames:v", "1",
                     "-vf", f"scale={a.width}:-2", out])
            if r.returncode != 0 or not os.path.exists(out):
                print(f"error: frame extract failed at {tile['t']:.2f} s: {r.stderr.strip()[:120]}", file=sys.stderr)
                return 2
    cols = max(1, min(a.cols, len(tiles)))
    rows = math.ceil(len(tiles) / cols)
    ddir = os.path.join(a.project, "09-qa", "contact-sheets")
    dest = a.out or os.path.join(ddir, f"EVENTS-{sha[:8]}.png")
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    r = run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i", os.path.join(tmp, "%04d.png"),
             "-filter_complex", f"tile={cols}x{rows}:padding=4:color=0x202020", "-frames:v", "1", dest])
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        print(f"error: tiling failed: {r.stderr.strip()[:200]}", file=sys.stderr)
        return 2
    side = {"tool": "contact_sheet.py events", "schema": 1, "sheet": os.path.basename(dest),
            "render": os.path.relpath(os.path.abspath(cut), os.path.abspath(a.project)), "render_sha256": sha,
            "render_mtime": os.path.getmtime(cut), "render_bytes": os.path.getsize(cut), "duration_s": round(dur, 3),
            "made": dt.datetime.now().isoformat(timespec="seconds"), "fps": fps,
            "tiles": [{"tile": i + 1, "t": tl_["t"], "ids": tl_["ids"]} for i, tl_ in enumerate(tiles)],
            "events": events, "notes": notes}
    json.dump(side, open(os.path.splitext(dest)[0] + ".json", "w", encoding="utf-8"), indent=1)
    kinds = {}
    for e in events:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"wrote {dest}\n  {len(tiles)} tile(s), {cols}x{rows} grid — "
          + ", ".join(f"{n} {k}" for k, n in kinds.items()) + f" · render sha256 {sha[:12]}")
    for n_ in notes:
        print(f"  note: {n_}")
    print("  Now READ every tile (review-and-approval.md §2a): the poster shows the subject, each cut has settled with\n"
          "  no flash frame, each title has landed inside the safe box and off the face and product, each hit and\n"
          "  sound sits on what it marks, the end card holds. Then log it, citing the tiles you looked at:\n"
          f"  qa_log.py --project {a.project} --gate draft --render {a.cut} --sheet "
          f"{os.path.relpath(dest, a.project)} --verdict PASS|RETAKE --obs \"…C3…T1…\"")
    return 0


def selftest() -> int:
    assert sample_times(4.0, 3, False, perf=True) == [0.6, 2.0, 3.4], "IN/MID/OUT sit at 15/50/85 %"
    assert sample_times(4.0, 1, True, perf=True) == [0.0], "a still is one tile, perf or not"
    assert sample_times(10.0, 1, False) == [0.5], "drift audit samples past the morph-settle"
    assert sample_times(10.0, 5, False) == [1.0, 3.0, 5.0, 7.0, 9.0]
    if not shutil.which("ffmpeg"):
        print("selftest OK (sampling only — ffmpeg not on PATH, the end-to-end half was skipped)")
        return 0
    with tempfile.TemporaryDirectory() as td:
        clip = os.path.join(td, "S9_test.mp4")
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                 "testsrc=duration=2:size=160x90:rate=25", "-pix_fmt", "yuv420p", clip])
        assert r.returncode == 0, r.stderr
        open(os.path.join(td, "still.png"), "wb").write(b"")   # a still, by extension alone
        out = os.path.join(td, "strip.png")
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--folder", td, "--glob", "*.mp4",
                             "--perf", "--out", out], capture_output=True, text=True, timeout=120)
        assert rc.returncode == 0 and os.path.getsize(out) > 0, rc.stderr + rc.stdout
        assert "performance strip" in rc.stdout, rc.stdout
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--clip", clip, "--perf",
                             "--out", out], capture_output=True, text=True, timeout=120)
        assert rc.returncode == 0, rc.stderr
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--folder", td, "--glob", "*.png",
                             "--perf", "--out", out], capture_output=True, text=True, timeout=120)
        assert rc.returncode == 2 and "no moving clips" in rc.stderr, (rc.returncode, rc.stderr)
        # the event sheet: every event read from the job's own files, one tile each, the render's hash beside it
        job = os.path.join(td, "job")
        for d in ("07-edit/titles", "07-edit/music", "06-music", "00-brief", "07-edit/_renders"):
            os.makedirs(os.path.join(job, d))
        cutf = os.path.join(job, "07-edit", "_renders", "x_cut_v001.mp4")
        r = run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=4:size=160x90:rate=24",
                 "-pix_fmt", "yuv420p", cutf])
        assert r.returncode == 0, r.stderr
        json.dump({"fps": 24, "tracks": {"video1": [{"name": "S1_v1.mp4", "type": "Video", "start": 0, "duration": 48},
                                                    {"name": "S2_v1.mp4", "type": "Video", "start": 48, "duration": 48}],
                                         "video2": [{"name": "S9_v1.mp4", "type": "Video", "start": 12, "duration": 12}]}},
                  open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
        json.dump({"motion": {"enter": {"ms": 450}}}, open(os.path.join(job, "00-brief", "TITLE-CARD.json"), "w"))
        json.dump({"id": "T1", "kind": "hero", "at_s": 2.55, "duration_s": 1.2},
                  open(os.path.join(job, "07-edit", "titles", "T1.title.json"), "w"))
        json.dump({"id": "T1", "kind": "hero", "at_s": 2.0}, open(os.path.join(job, "07-edit", "titles", "T1.opt2.title.json"), "w"))
        json.dump({"hits": [{"id": "H1", "t": 2.0, "priority": "optional"}, {"id": "BUTTON", "t": 3.0, "priority": "must",
                                                                             "want": "button"}]},
                  open(os.path.join(job, "07-edit", "music", "HITS.json"), "w"))
        json.dump({"events": [{"sfx": "tap", "frame": 36}]}, open(os.path.join(job, "06-music", "SFX-PLACEMENT.json"), "w"))
        ev, notes = job_events(job, 4.0)
        T = {e["id"]: e["t"] for e in ev}
        assert set(T) == {"POSTER", "C1", "C2", "C3", "T1", "BUTTON", "FX1", "END"}, T   # the option file and an optional hit are not events
        assert T["POSTER"] == 0.0 and abs(T["C1"] - 0.9) < 1e-6 and abs(T["C3"] - 2.4) < 1e-6, T   # V2's in (0.5 s) and out (1.0 s) are cuts
        assert abs(T["T1"] - 3.1) < 1e-6 and abs(T["BUTTON"] - 3.1) < 1e-6 and abs(T["FX1"] - 1.6) < 1e-6, T
        assert abs(T["END"] - (4.0 - 1 / 24)) < 1e-3 and not notes, (T, notes)
        tiles = event_tiles([{"id": "A", "kind": "cut", "t": 1.0}, {"id": "B", "kind": "hit", "t": 1.02}], 24.0)
        assert len(tiles) == 1 and tiles[0]["ids"] == ["A", "B"], tiles          # within a frame: one tile
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "events", "--project", job, "--cut",
                             "07-edit/_renders/x_cut_v001.mp4"], capture_output=True, text=True, timeout=180)
        assert rc.returncode == 0, rc.stderr + rc.stdout
        sha = sha256_file(cutf)
        side = json.load(open(os.path.join(job, "09-qa", "contact-sheets", f"EVENTS-{sha[:8]}.json")))
        assert side["render_sha256"] == sha and side["tiles"][0]["ids"] == ["POSTER"], side
        assert os.path.getsize(os.path.join(job, "09-qa", "contact-sheets", f"EVENTS-{sha[:8]}.png")) > 0
        assert len(side["tiles"]) == 7 and ["T1", "BUTTON"] in [t_["ids"] for t_ in side["tiles"]], side["tiles"]
        os.remove(os.path.join(job, "07-edit", "timeline-dump.json"))
        ev2, notes2 = job_events(job, 4.0)
        assert not any(e["kind"] == "cut" for e in ev2) and notes2 and "timeline-dump" in notes2[0], notes2
    print("selftest OK — IN/MID/OUT at 15/50/85 %, stills skipped in --perf (and refused when "
          "nothing moves), --clip reads one file, the drift and selects sampling unchanged; the event sheet "
          "reads poster, cuts (an insert's in and out), titles after their entrance, must-hits, placed sounds and the "
          "end from the job, shares a tile within a frame, and records the render's hash")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "events":
        return events_main(sys.argv[2:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--project", help="project dir; reads 03-clips/ and writes 09-qa/contact-sheets/")
    src.add_argument("--folder", help="any folder of clips")
    src.add_argument("--clip", help="one clip file")
    src.add_argument("--selftest", action="store_true", help="build a synthetic clip and check the sampling")
    ap.add_argument("--glob", default="*", help="filter clip filenames (e.g. 'S1-*')")
    ap.add_argument("--frames", type=int, default=5, help="frames sampled per clip (default 5)")
    ap.add_argument("--first-frame-only", action="store_true", help="drift-audit mode: 1 frame per clip")
    ap.add_argument("--perf", action="store_true",
                    help="performance strip: IN/MID/OUT at 15/50/85%% of each clip; stills skipped")
    ap.add_argument("--width", type=int, default=320, help="thumbnail width px (default 320)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("error: ffmpeg/ffprobe not on PATH", file=sys.stderr)
        return 2
    # ⛔ Dailies are what CAME BACK, not what survived. `03-clips/` holds only clips whose QA card
    # already passed (pm-workflow.md), so pointing the grid there made the "dailies pass" a preview
    # of the assembly. `_review/` is where a generation actually lands.
    if a.project:
        cands = [os.path.join(a.project, "03-clips", "_review"),
                 os.path.join(a.project, "02-startframes"),
                 os.path.join(a.project, "03-clips")]
        folder = next((d for d in cands if os.path.isdir(d) and any(
            f.lower().endswith(EXTS) for f in os.listdir(d))), cands[-1])
        if a.folder:
            folder = a.folder
    elif a.clip:
        folder = os.path.dirname(os.path.abspath(a.clip))
        a.glob = os.path.basename(a.clip)
    else:
        folder = a.folder
    if not os.path.isdir(folder):
        print(f"error: not a folder: {folder}", file=sys.stderr)
        return 2
    clips = sorted(f for f in os.listdir(folder)
                   if f.lower().endswith(EXTS) and fnmatch.fnmatch(f, a.glob))
    if not clips:
        print(f"error: no clips matching {a.glob!r} in {folder}", file=sys.stderr)
        return 2

    if a.perf:
        # ⛔ A still has no performance. Tiling one would put a single frame where the reader
        # expects IN/MID/OUT and read as "no change" — the wrong answer, not a missing one.
        skipped = [c for c in clips if c.lower().endswith(STILL_EXTS)]
        clips = [c for c in clips if not c.lower().endswith(STILL_EXTS)]
        if skipped:
            print(f"  --perf: skipped {len(skipped)} still(s) — a still has no performance to read")
        if not clips:
            print("error: --perf found no moving clips", file=sys.stderr)
            return 2
    per = 3 if a.perf else 1 if a.first_frame_only else max(1, a.frames)
    tmp = tempfile.mkdtemp(prefix="sheet_")
    tiles, labels = [], []
    for c in clips:
        path = os.path.join(folder, c)
        # A still has no duration and no mid-clip: one tile, t=0, and no seek. Without this the
        # seek past a one-frame input returns nothing and the still is silently dropped.
        is_still = c.lower().endswith(STILL_EXTS)
        dur = 0.0 if is_still else duration(path)
        # sample AWAY from the endpoints: mid-clip is where artifacts live; the first ~0.5s is the
        # morph-settle zone and would poison a drift audit, so "first frame" is really t=0.5s
        times = sample_times(dur, per, is_still, a.perf)
        for i, t in enumerate(times):
            out = os.path.join(tmp, f"{len(tiles):04d}.png")
            tag = f"{PERF_LABELS[i]} " if a.perf else ""
            r = run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{min(t, max(0.0, dur - 0.1)):.2f}",
                     "-i", path, "-frames:v", "1", "-vf",
                     f"scale={a.width}:-2,drawtext=text='{tag}{c[:28]} t={t:.1f}':x=4:y=4:fontsize=12:"
                     f"fontcolor=white:box=1:boxcolor=black@0.6", out])
            if r.returncode != 0 or not os.path.exists(out):
                # drawtext can be missing from a minimal ffmpeg — retry without the label
                r = run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{min(t, max(0.0, dur-0.1)):.2f}",
                         "-i", path, "-frames:v", "1", "-vf", f"scale={a.width}:-2", out])
                if r.returncode != 0:
                    print(f"error: frame extract failed on {c}: {r.stderr.strip()[:120]}", file=sys.stderr)
                    return 2
            tiles.append(out)
        labels.append(c)

    cols = per if per > 1 else max(1, min(6, math.ceil(math.sqrt(len(tiles)))))
    rows = math.ceil(len(tiles) / cols)
    if a.out:
        dest = a.out
    else:
        base = a.project or folder
        ddir = os.path.join(base, "09-qa", "contact-sheets") if a.project else folder
        os.makedirs(ddir, exist_ok=True)
        label = ("perf" if a.perf else "drift" if a.first_frame_only else "selects") + \
                ("" if a.glob == "*" else "-" + a.glob.replace("*", "x"))
        dest = os.path.join(ddir, f"SHEET-{label}-{dt.date.today().isoformat()}.png")
    lst = os.path.join(tmp, "list.txt")
    r = run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "1", "-i",
             os.path.join(tmp, "%04d.png"), "-filter_complex",
             f"tile={cols}x{rows}:padding=4:color=0x202020", "-frames:v", "1", dest])
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        print(f"error: tiling failed: {r.stderr.strip()[:200]}", file=sys.stderr)
        return 2
    n_still = sum(1 for c in clips if c.lower().endswith(STILL_EXTS))
    mode = ("performance strip (IN/MID/OUT at 15/50/85 %) — read it against the card: IN is the "
            "before, OUT the after, the change between MID and OUT" if a.perf
            else "drift audit (1 frame/clip, t=0.5s — past the morph-settle)" if per == 1
            else f"selects ({per} frames/clip)")
    if n_still:
        # do not claim N frames per clip when N of them are stills and got exactly one
        mode += f" · {n_still} still(s), one tile each"
    print(f"wrote {dest}\n  {len(clips)} clip(s), {len(tiles)} frame(s), {cols}x{rows} grid — {mode}")
    print("  Now LOOK at it and write the observations (qa_log.py). The sheet is the pixels, not the verdict —")
    print("  and for dialogue clips the sheet is never sufficient: lipsync is verified by listening.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
