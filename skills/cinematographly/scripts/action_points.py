#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""action_points.py — where to cut a generated action clip, what to ramp, and where the foley hits.

⚡ THE TIMING BELONGS TO THE EDIT (house decision 2026-10-26, package B of
the intent and emotion proposal of 2026-10-26 [studio history]). Three models, asked separately, agreed that
image-to-video models ignore sub-second timing in a prompt. So the prompt carries the ORDER of events
("a beat still, then in one quick motion…", motion-craft.md §6b) and this step reads what the model
actually did and proposes the edit that makes the intent land:

  onset    the first frame the action moves after the lead-in settles   → the IN point, a few frames before
  peak     the fastest moment of the action (the commit)                 → cut here into the consequence shot
  contact  the sharpest stop after the peak (an impact, a set-down)      → the foley HIT frame
  settle   where the motion drops back to rest                           → leave before it completes
  ramp     onset → contact, speeded up only if the burst is slow         → never the whole clip

It measures motion energy: the mean absolute difference between consecutive grey frames, scaled to a
small width, smoothed over three frames and normalised to the clip's own peak. That is motion IN the
picture, camera included, which is what the cut feels. The thresholds are [assumed] house values,
printed with every result.

⛔ WHAT IT CANNOT DO. It reads ONE shot: a cut or a flash inside the clip is a one-frame spike and
would be taken for the commit, so it is flagged. It does not know which motion is the intended one: a
camera move or a second person can carry the peak. Read the numbers against the contact sheet (`contact_sheet.py`), and move a
point by hand where the sheet disagrees. It proposes; the editor decides.

Usage
-----
  python3 action_points.py CLIP.mp4                       # summary only; nothing written
  python3 action_points.py CLIP.mp4 --out CLIP.points.json --edl markers.edl   # + JSON, + Resolve markers
  python3 action_points.py CLIP.mp4 --fps 24 --width 160 --json
  python3 action_points.py CLIP.mp4 --permanence CLIP.permanence.png   # + the object-permanence strip
  python3 action_points.py --selftest

⛔ OBJECT PERMANENCE (a supplement ad job, 2026-10-28). A clip passed selects with the note "keys tossed … keys at rest" — the
model had thrown the keys out of frame and put them back on the counter, between the frames the 15/50/85 % strip
shows. `--permanence` samples EVERY 2 FRAMES from 6 frames before the onset to 6 after the settle, numbered, on one
sheet: count the objects held, falling and at rest on each; an object that disappears and comes back is a RETAKE
(realism-qa.md V7b). It shows the frames; the count is the reviewer's.

Requires ffmpeg/ffprobe and numpy.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile

TH = {"onset": 0.18, "settle": 0.12, "slow_burst": 0.55, "lead_skip_s": 0.4, "in_pad_f": 2, "cut_after_peak_f": 5}
TH_TAG = "[assumed] house values, not calibrated on a reviewed set of clips"
RAMP_PCT = 130     # inside the jury's 115–150 % band; a burst already fast is left at 100 %


def _need():
    try:
        import numpy as np
    except ImportError:
        raise SystemExit("error: numpy is required (pip install numpy)")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise SystemExit("error: ffmpeg/ffprobe not on PATH")
    return np


def probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,avg_frame_rate:format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [{}])[0]
    a, _, b = str(st.get("avg_frame_rate") or "0/1").partition("/")
    fps = float(a) / float(b) if float(b or 0) else 0.0
    return {"w": int(st.get("width") or 0), "h": int(st.get("height") or 0), "fps": fps,
            "duration": float((d.get("format") or {}).get("duration") or 0)}


def energy(path: str, fps: float, width: int) -> list:
    np = _need()
    info = probe(path)
    if not info["w"]:
        raise SystemExit(f"error: ffprobe could not read {path}")
    w = width - width % 2
    h = max(2, int(round(info["h"] * w / info["w"] / 2)) * 2)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True)
    buf = r.stdout or b""
    n = len(buf) // (w * h)
    if n < 4:
        raise SystemExit(f"error: only {n} frames decoded from {path}")
    fr = np.frombuffer(buf[: n * w * h], np.uint8).reshape(n, h, w).astype(np.int16)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))           # d[i] = motion from frame i to i+1
    k = np.array([1, 1, 1], float) / 3
    sm = np.convolve(np.pad(d, 1, mode="edge"), k, mode="valid")
    peak = float(sm.max()) or 1.0
    rpk = float(d.max()) or 1.0
    return [float(x) / peak for x in sm], [float(x) / rpk for x in d]


def points(e: list, fps: float, raw: list | None = None) -> dict:
    """The four points from a normalised energy curve (index i = the step from frame i to i+1)."""
    n = len(e)
    skip = int(round(TH["lead_skip_s"] * fps))
    pk = max(range(n), key=lambda i: e[i])
    # onset: the last time before the peak that the curve was below the onset threshold, past the lead-in
    on = pk
    while on > 0 and e[on - 1] >= TH["onset"]:
        on -= 1
    on = max(on, min(skip, pk))
    # contact: the sharpest drop after the peak (the largest fall in one step)
    drops = [(e[i] - e[i + 1], i + 1) for i in range(pk, n - 1)]
    contact = max(drops)[1] if drops else pk
    st = contact
    while st < n - 1 and e[st] > TH["settle"]:
        st += 1
    approach = sum(e[on:pk + 1]) / max(1, pk + 1 - on)
    # a cut or a flash lives in ONE step of the raw curve; the smoothed one spreads it over three
    r = raw if raw is not None else e
    rp = max((i for i in (pk - 1, pk, pk + 1) if 0 <= i < len(r)), key=lambda i: r[i])
    nb = [r[i] for i in (rp - 2, rp - 1, rp + 1, rp + 2) if 0 <= i < len(r)]
    spike = bool(nb) and r[rp] > 0 and max(nb) < 0.35 * r[rp]
    ramp = RAMP_PCT if approach < TH["slow_burst"] else 100
    f = lambda i: {"frame": int(i), "t": round(i / fps, 3)}
    return {"onset": f(on), "peak": f(pk), "contact": f(contact), "settle": f(st),
            "in_point": f(max(0, on - TH["in_pad_f"])), "cut_point": f(min(n, pk + TH["cut_after_peak_f"])),
            "hit": f(contact),
            "ramp": {"from": f(on), "to": f(contact), "speed_pct": ramp,
                     "why": ("the burst is slow against its own peak, so ramp it" if ramp != 100 else
                             "the burst is already fast: leave it at 100 %, never ramp the whole clip")},
            "burst_mean_energy": round(approach, 3),
            "warnings": (["the peak is a one-frame spike: a cut or a flash, not an action — is this one shot? "
                          "Trim the clip to the shot and measure again"] if spike else [])}


def _tc(frame: int, fps: int) -> str:
    s, fr = divmod(frame, fps)
    return f"01:{s // 60 % 60:02d}:{s % 60:02d}:{fr:02d}"


def write_edl(path: str, label: str, p: dict, fps: float) -> None:
    """Timeline markers Resolve imports (Timeline → Import → Timeline Markers from EDL)."""
    F = int(round(fps)) or 24
    marks = [("in", p["in_point"], "Blue"), ("commit / cut", p["cut_point"], "Red"),
             ("hit (foley)", p["hit"], "Yellow"), ("settle", p["settle"], "Green")]
    L = [f"TITLE: {label} action points", "FCM: NON-DROP FRAME", ""]
    for k, (name, pt, col) in enumerate(marks, 1):
        a = _tc(pt["frame"], F); b = _tc(pt["frame"] + 1, F)
        L.append(f"{k:03d}  001      V     C        {a} {b} {a} {b}  ")
        L.append(f" |C:ResolveColor{col} |M:{name} |D:1")
        L.append("")
    open(path, "w", encoding="utf-8").write("\n".join(L))


def run(clip: str, fps: float, width: int) -> dict:
    info = probe(clip)
    e, raw = energy(clip, fps, width)
    p = points(e, fps, raw)
    return {"clip": os.path.abspath(clip), "fps_measured": fps, "source": info, "thresholds": TH,
            "thresholds_tag": TH_TAG, "energy": [round(x, 3) for x in e], **p}


def permanence_strip(clip: str, d: dict, out: str, fps: float, every: int = 2, pad: int = 6, tile_w: int = 240) -> dict:
    """Every `every`-th frame from onset − pad to settle + pad, numbered, tiled 6 across → `out` (PNG)."""
    np = _need()
    import cv2
    info = probe(clip)
    W, H = int(info.get("w") or 0), int(info.get("h") or 0)
    if not (W and H):
        raise SystemExit("error: cannot read the clip's size")
    f0 = max(0, d["onset"]["frame"] - pad)
    f1 = d["settle"]["frame"] + pad
    th = int(round(tile_w * H / W))
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-vf", f"fps={fps},scale={tile_w}:{th}", "-f", "rawvideo",
                        "-pix_fmt", "bgr24", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    n = a.size // (tile_w * th * 3)
    frames = a[: n * tile_w * th * 3].reshape(n, th, tile_w, 3)
    idx = [i for i in range(f0, min(f1 + 1, n)) if (i - f0) % every == 0]
    cols = 6
    rows = (len(idx) + cols - 1) // cols
    sheet = np.full((rows * (th + 4), cols * (tile_w + 4), 3), 17, np.uint8)
    marks = {d["onset"]["frame"]: "onset", d["peak"]["frame"]: "peak", d["contact"]["frame"]: "contact",
             d["settle"]["frame"]: "settle"}
    for k, i in enumerate(idx):
        y, x = (k // cols) * (th + 4), (k % cols) * (tile_w + 4)
        t = frames[i].copy()
        lab = f"f{i}" + (f" {marks[i]}" if i in marks else "")
        cv2.rectangle(t, (0, 0), (len(lab) * 9 + 6, 18), (0, 0, 0), -1)
        cv2.putText(t, lab, (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
        sheet[y:y + th, x:x + tile_w] = t
    cv2.imwrite(out, sheet)
    return {"sheet": out, "frames": idx, "every": every}


def _synth(path: str, fps: int = 24, seed: int = 3) -> None:
    """2 s still, a block that moves fast for 0.4 s and stops dead (the contact), then 1.6 s still.
    `seed` picks the noise wall behind the block (shot_graph.py's selftest asks for several)."""
    np = _need()
    W, H = 160, 90
    rng = np.random.default_rng(seed)
    bg = (rng.random((H, W)) * 60 + 80).astype(np.uint8)
    frames = []
    for i in range(fps * 4):
        t = i / fps
        img = bg.copy()
        x = 20 if t < 2.0 else (20 + int((t - 2.0) / 0.4 * 100) if t < 2.4 else 120)
        img[30:60, x:x + 20] = 240
        frames.append(img)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                          "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "mpeg4", "-q:v", "2", path],
                         stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()


def selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and cond
    with tempfile.TemporaryDirectory() as td:
        v = os.path.join(td, "synth.mp4")
        _synth(v)
        d = run(v, 24.0, 160)
        on, pk, ct = d["onset"]["t"], d["peak"]["t"], d["contact"]["t"]
        check("onset at the start of the burst (2.0 s ± 0.1)", abs(on - 2.0) <= 0.1, str(on))
        check("peak inside the burst (2.0–2.4 s)", 1.95 <= pk <= 2.45, str(pk))
        check("contact on the dead stop (2.4 s ± 0.1)", abs(ct - 2.4) <= 0.1, str(ct))
        check("the hit frame is the contact", d["hit"] == d["contact"])
        check("the in point sits before the onset, the cut after the peak",
              d["in_point"]["frame"] < d["onset"]["frame"] and d["cut_point"]["frame"] > d["peak"]["frame"])
        check("a fast burst is not ramped", d["ramp"]["speed_pct"] == 100, json.dumps(d["ramp"]))
        check("a real burst is not flagged as a cut", not d["warnings"], json.dumps(d["warnings"]))
        raw = [0.03] * 20 + [1.0] + [0.03] * 20
        sm = [(raw[max(0, i - 1)] + raw[i] + raw[min(len(raw) - 1, i + 1)]) / 3 for i in range(len(raw))]
        sm = [x / max(sm) for x in sm]
        check("a one-frame spike (a cut) is flagged through the smoothing, not trusted as the commit",
              bool(points(sm, 24.0, raw)["warnings"]))
        slow = points([0.0] * 10 + [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 1.0, 0.1] + [0.0] * 8, 24.0)
        check("a slow approach is ramped inside 115–150 %", 115 <= slow["ramp"]["speed_pct"] <= 150,
              json.dumps(slow["ramp"]))
        edl = os.path.join(td, "m.edl")
        write_edl(edl, "synth", d, 24.0)
        txt = open(edl).read()
        check("the EDL carries four markers with Resolve colours",
              txt.count("|M:") == 4 and "ResolveColorYellow" in txt and "|M:hit (foley)" in txt)
        st = permanence_strip(v, d, os.path.join(td, "perm.png"), 24.0)
        check("the permanence strip: every 2nd frame from before the onset to after the settle, on one sheet",
              os.path.isfile(st["sheet"]) and st["frames"][0] <= d["onset"]["frame"] - 4
              and st["frames"][-1] >= d["settle"]["frame"] and all(b - a == 2 for a, b in zip(st["frames"], st["frames"][1:])),
              json.dumps(st))
    print("-" * 60)
    print("selftest OK — onset, peak, contact and settle found on a synthetic burst-and-stop; the hit is the "
          "contact; in point before onset, cut after the peak; a fast burst left at 100 %, a slow one ramped; "
          "Resolve markers written; the permanence strip every 2 frames around the action" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip", nargs="?")
    ap.add_argument("--fps", type=float, default=24.0, help="sampling rate for the measurement (default 24)")
    ap.add_argument("--width", type=int, default=160, help="measure on frames scaled to this width")
    ap.add_argument("--edl", help="also write Resolve timeline markers to this EDL")
    ap.add_argument("--out", help="also write the full measurement as JSON here")
    ap.add_argument("--json", action="store_true", help="print the JSON instead of the summary")
    ap.add_argument("--permanence", help="also write the object-permanence strip (every 2 frames around the action) here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.clip:
        ap.print_help(); return 2
    d = run(a.clip, a.fps, a.width)
    if a.out:
        json.dump(d, open(a.out, "w"), indent=1)
    if a.edl:
        write_edl(a.edl, os.path.basename(a.clip), d, a.fps)
    if a.permanence:
        st = permanence_strip(a.clip, d, a.permanence, a.fps)
        print(f"  permanence strip: {st['sheet']} — {len(st['frames'])} frames, every {st['every']}: count the objects "
              f"held, falling and at rest on each; one that vanishes and comes back is a RETAKE (realism-qa.md V7b)")
    if a.json:
        print(json.dumps({k: v for k, v in d.items() if k != "energy"}, indent=1)); return 0
    print(f"{os.path.basename(a.clip)} — thresholds {TH_TAG}")
    for k in ("in_point", "onset", "peak", "cut_point", "contact", "settle"):
        print(f"  {k:<10} {d[k]['t']:6.3f} s  (frame {d[k]['frame']})")
    r = d["ramp"]
    print(f"  ramp       {r['from']['t']:.3f}–{r['to']['t']:.3f} s at {r['speed_pct']} % — {r['why']}")
    print(f"  hit        {d['hit']['t']:.3f} s — lay the foley here; dip the bed 1–3 frames before it")
    for w in d["warnings"]:
        print(f"  ⚠ {w}")
    if a.out or a.edl:
        print("  wrote " + " and ".join(x for x in (a.out, a.edl) if x))
    return 0


if __name__ == "__main__":
    sys.exit(main())
