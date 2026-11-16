#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""clip_qa.py — measure a generated clip's temporal defects: freezes, dead zones, focus decay.

Three failures show up in AI-generated clips that a contact sheet cannot catch, because they are
properties of TIME rather than of any single frame:

  1. **Dead zone / freeze.** The model reaches its target early and sits there, then rushes the
     remaining action. Measured 2026-08-29 on a first-and-last-frame clip whose two frames differed
     only in pose: a 1.83s near-static hole in a 5s clip — 37% of the runtime spent frozen.
  2. **Focus decay.** Sharpness falls away from the start frame, which is the only real detail the
     model was given. A prompt-only i2v clip measured a 29% drop from first frame to last.
  3. **Late-rush.** Motion energy spikes at the tail as the model compensates for the dead zone.
  4. **No ease-out.** Measured 2026-08-29 on three clips: ALL THREE peaked in their final second and
     ended mid-motion. The model blocks the anticipation and the action and never the settle. That
     is an editorial ASSET where you cut out of the peak, and a defect only where the shot has to
     land - so it is reported by default and only fails with --landing.
     See ../references/timing-and-performance.md sections 5 and 7.
  5. **Post-line motion.** A dialogue clip generated longer than its audio keeps animating over the
     silence - lips included - because this model class is trained on continuously-speaking footage
     and has no idle state. Give --line-ends (or --auto-line-end, which finds the trailing silence
     in the clip's own audio) and the tail after the line is measured.
     See ../references/shot-handoff.md sections 1 and 2.

  6. **A film with one motion setting.** `--motion-profile` reads the whole clips folder and asks
     whether the job has any motion dynamic range at all. Measured background: across 160 films
     1935-2010 average shot length fell from ~10s to under 4s WHILE motion magnitude rose, and the
     two became coupled (r = -.46) - short shots increasingly carry proportionately MORE motion
     [PRIMARY - Cutting et al., i-Perception 2011]. Short-and-static is a combination no era of
     film produced and it is this pipeline's default output.
     ⛔ It sets NO absolute floor on motion, deliberately: the index is contrast-sensitive, so an
     absolute threshold would fight content that legitimately varies. The comparison is internal
     to the job, where that sensitivity cancels. See ../references/motion-craft.md section 3.

All five change WHERE THE CLIP IS USABLE, which is an edit decision — so this prints a usable
window, not just a verdict.

Requires ffmpeg/ffprobe only (blurdetect, tblend, signalstats). No pip installs.

Usage
-----
  python3 clip_qa.py SHOT.mp4
  python3 clip_qa.py SHOT.mp4 --fps 12 --dead-threshold 0.25 --json
  python3 clip_qa.py FINAL.mp4 --landing            # this shot lands: no ease-out is a DEFECT
  python3 clip_qa.py LINE.mp4 --auto-line-end       # measure the tail after the spoken line
  python3 clip_qa.py LINE.mp4 --line-ends 4.2       # ...or say where the line ends yourself
  python3 clip_qa.py 03-clips/*.mp4 --quiet        # batch triage, one line each
  python3 clip_qa.py 03-clips/*.mp4 --motion-profile  # the film as one object: any motion range?
  python3 clip_qa.py --selftest

What it cannot do
-----------------
- **The motion index is NOT Cutting's Visual Activity Index.** VAI is 1 - median correlation
  between next-adjacent frames; this is mean frame-difference energy, which ffmpeg gives for free
  and correlation does not. It is contrast-sensitive, so it is [ASSUMED] as a cross-clip comparator
  and MEANINGLESS against a published film-scale figure. Never quote a clip's motion index next to
  Barry Lyndon's 0.008.
- **The post-line check measures WHOLE-FRAME motion, not the mouth. THIS IS MEASURED, not a
  caveat.** Tested 2026-08-29 on a clip whose lips visibly kept working over a 1s silent tail: the
  post-line window came out at 15.4% of clip peak and this tool called it SETTLES. It flagged only a
  dead zone - which was the HEAD freezing while the mouth carried on. Restricting the same metric to
  a mouth crop, with and without global-motion compensation, did not separate that clip from clean
  ones either. ffmpeg cannot see a lip. This check finds a BUSY tail, which is a different and also
  real fault; whether the mouth is moving is an eye check at 0.25x, per the QA card.
- **--auto-line-end finds silence, not speech.** It uses an amplitude threshold, so music, room tone
  or a loud bed under the VO will hide the trailing silence and it will report nothing. On any clip
  that matters, pass --line-ends yourself from the VO's real length.
- **It cannot tell you the clip is good.** It finds three specific mechanical defects. A clip can
  pass every check here and still be wrong, badly acted, off-brand or non-compliant. This does not
  replace the QA card in ../references/realism-qa.md section 6 or the listening gate in qa_log.py.
- It cannot distinguish a *deliberate* held beat from a model freeze. A locked-off shot of someone
  sitting still is correctly reported as near-static; you decide whether that was the intent.
- Its sharpness figure is relative to the clip's own peak, not an absolute standard, so it compares
  a clip to itself and never to another clip.
- **Its focus metric is conservative.** It uses ffmpeg's edge-width `blurdetect`, which reported a
  3-9% decay on clips where a high-frequency (Laplacian-variance) measure reported 29-37% on the
  same footage. Treat a clean focus verdict here as "no gross softening", not as "sharp" — and trust
  your eye over the number, which is the direction this skill errs in everywhere else too.
- Thresholds are house defaults from a sample of three clips on one model. Re-derive them when the
  roster changes; they are not physics.

Exit codes: 0 clean - 1 defect found - 2 usage/IO/ffmpeg error.
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys

BLUR = re.compile(r"lavfi\.blur=([0-9.]+)")
SIL_START = re.compile(r"silence_start:\s*(-?[0-9.]+)")
SIL_END = re.compile(r"silence_end:\s*(-?[0-9.]+)")
YAVG = re.compile(r"lavfi\.signalstats\.YAVG=([0-9.]+)")
# The LOOK, measured off the delivered pixels rather than the plan. signalstats gives the per-frame
# mean of each plane; Y is brightness, U is the blue-yellow axis and V the red-green axis, both
# neutral at 128 in 8-bit. ⛔ These are PLANE MEANS, not a grade and not a colour-temperature
# estimate — do not call the cast "Kelvin", because a mean cast is not a white point.
LOOK_Y = re.compile(r"lavfi\.signalstats\.YAVG=([0-9.]+)")
LOOK_U = re.compile(r"lavfi\.signalstats\.UAVG=([0-9.]+)")
LOOK_V = re.compile(r"lavfi\.signalstats\.VAVG=([0-9.]+)")
# Shots that are supposed to match: the scene prefix of a house shot id (S1-C1, S1-R, S1B -> S1).
SCENE_RE = re.compile(r"^(S\d+)", re.I)
LOOK_LUMA_SPREAD = 0.25   # [ASSUMED 2026-09-07] within-scene max-min luma as a fraction of the mean
LOOK_CAST_SPREAD = 8.0    # [ASSUMED 2026-09-07] within-scene cast distance, in 8-bit code values


def need(binary: str) -> None:
    if not shutil.which(binary):
        print(f"error: {binary} not found on PATH — this tool is ffmpeg-only by design.", file=sys.stderr)
        raise SystemExit(2)


def probe_duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        print(f"error: could not read duration from {path}", file=sys.stderr)
        raise SystemExit(2)


def series(path: str, vf: str, pattern: re.Pattern) -> list[float]:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(m) for m in pattern.findall(r.stdout + r.stderr)]


def runs_below(vals: list[float], frac: float) -> list[tuple[int, int]]:
    """Index runs where value < frac * max."""
    if not vals:
        return []
    cut = frac * max(vals)
    idx = [i for i, v in enumerate(vals) if v < cut]
    out, start, prev = [], None, None
    for i in idx:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            out.append((start, prev)); start = prev = i
    if start is not None:
        out.append((start, prev))
    return out


def has_audio(path: str) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                        "stream=index", "-of", "csv=p=0", path], capture_output=True, text=True)
    return bool(r.stdout.strip())


def trailing_silence_start(text: str, dur: float, tol: float = 0.05) -> float | None:
    """Start of the silence that runs to the end of the clip, from ffmpeg silencedetect output.

    Returns None when the last detected silence ENDS before the clip does — that means speech
    resumed after it, so there is no trailing silence to measure.
    """
    starts = [float(v) for v in SIL_START.findall(text)]
    ends = [float(v) for v in SIL_END.findall(text)]
    if not starts:
        return None
    last = starts[-1]
    later_ends = [e for e in ends if e > last]
    if later_ends and later_ends[-1] < dur - tol:
        return None
    return max(last, 0.0)


def detect_line_end(path: str, dur: float, noise_db: float = -40.0, min_sil: float = 0.35):
    """Where speech stops, inferred from the trailing silence in the clip's own audio track."""
    if not has_audio(path):
        return None
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_sil}", "-f", "null", "-"],
                       capture_output=True, text=True)
    return trailing_silence_start(r.stdout + r.stderr, dur)


def post_line(motion: list[float], step: float, line_end: float, dur: float) -> dict:
    """How much the picture is still moving after the line stops.

    A designed aftermath — mouth closing, a breath, the gaze dropping, the body settling — is
    low-energy. A model with no idle state fills the same window with invented speech and drift.
    """
    if not motion or line_end is None or line_end >= dur:
        return {}
    peak = max(motion) or 1.0
    first = int(line_end / step)
    tail = motion[first:]
    if not tail:
        return {}
    return {"line_ends_s": round(line_end, 2),
            "tail_len_s": round(dur - line_end, 2),
            "motion_pct_of_peak": round(100 * (sum(tail) / len(tail)) / peak, 1)}


def classify_landing(tail_pct: float, mean_pct: float) -> str:
    """Name the clip's energy shape from its tail and its mean, both as % of the clip's own peak."""
    if tail_pct <= 40.0:
        return "SETTLES"
    if tail_pct >= mean_pct + 10.0:
        return "ENDS ACCELERATING"
    return "ENDS MID-MOTION"


def landing(motion: list[float], step: float, tail_s: float = 1.0) -> dict:
    """Where the motion energy peaks, and whether the clip eases out of it.

    Reference measurement (kling3_0, 5s, 2026-08-29): tail/peak 75%, 53%, 83% against clip means of
    46%, 35%, 66% — three for three ENDS ACCELERATING. A clip that genuinely settles has its tail
    BELOW its own mean, which is what the 40% cut-off is calibrated to catch.
    """
    if not motion:
        return {}
    peak = max(motion)
    if peak <= 0:
        # ⛔ A clip with NO motion at all. The old code wrote `max(motion) or 1.0`, which turned a
        # zero peak into a fake peak of 1.0 and then crashed on `motion.index(1.0)` — found
        # 2026-09-07 the first time a genuinely static clip was measured. A locked-off shot of a
        # still subject is a real thing; it has no landing because it never took off.
        return {"peak_at_s": 0.0, "peak_in_final_s": False, "tail_s": tail_s,
                "tail_pct_of_peak": 0.0, "clip_mean_pct_of_peak": 0.0, "shape": "NO MOTION"}
    n_tail = max(1, int(round(tail_s / step)))
    tail = motion[-n_tail:]
    tail_pct = 100 * (sum(tail) / len(tail)) / peak
    mean_pct = 100 * (sum(motion) / len(motion)) / peak
    i_peak = motion.index(peak)
    return {"peak_at_s": round((i_peak + 1) * step, 2),
            "peak_in_final_s": (len(motion) - i_peak) <= n_tail,
            "tail_s": tail_s,
            "tail_pct_of_peak": round(tail_pct, 1),
            "clip_mean_pct_of_peak": round(mean_pct, 1),
            "shape": classify_landing(tail_pct, mean_pct)}


def analyse(path: str, fps: int, dead_frac: float, decay_pct: float, lead_in: float = 0.5,
            must_land: bool = False, line_end=None, auto_line: bool = False,
            max_post: float = 30.0, want_look: bool = False) -> dict:
    dur = probe_duration(path)
    motion = series(path, f"fps={fps},tblend=all_mode=difference,signalstats,metadata=print:file=-", YAVG)
    sharp = series(path, f"fps={fps},blurdetect,metadata=print:file=-", BLUR)
    step = 1.0 / fps
    res: dict = {"file": os.path.basename(path), "duration_s": round(dur, 2),
                 "samples": len(motion), "fps": fps}

    # An image-to-video clip ALWAYS opens near-static: frame one is the supplied start image and the
    # model takes a moment to leave it. Measured on three clips, that settle runs ~0.4s. Counting it
    # as a defect flags every i2v clip ever made, so the lead-in is excluded by default.
    lead_skip = int(lead_in / step)
    dead = [(a, b) for a, b in runs_below(motion, dead_frac)
            if (b - a + 1) * step >= 0.3 and a >= lead_skip]
    res["dead_zones"] = [{"start_s": round((a + 1) * step, 2), "end_s": round((b + 1) * step, 2),
                          "length_s": round((b - a + 1) * step, 2)} for a, b in dead]
    res["dead_total_s"] = round(sum(z["length_s"] for z in res["dead_zones"]), 2)
    res["dead_pct_of_clip"] = round(100 * res["dead_total_s"] / dur, 1) if dur else 0.0

    if sharp:
        # blurdetect: HIGHER means blurrier, so sharpness is its inverse.
        s = [1.0 / v if v else 0.0 for v in sharp]
        peak = max(s) or 1.0
        res["sharpness_pct_of_peak"] = [round(100 * v / peak, 1) for v in s]
        res["sharpness_first"] = res["sharpness_pct_of_peak"][0]
        res["sharpness_last"] = res["sharpness_pct_of_peak"][-1]
        res["sharpness_min"] = min(res["sharpness_pct_of_peak"])
        res["focus_decay_pct"] = round(100 - res["sharpness_min"], 1)
        # usable window: contiguous span holding >= (100 - decay_pct) of peak
        keep = [i for i, v in enumerate(res["sharpness_pct_of_peak"]) if v >= (100 - decay_pct)]
        if keep:
            best, cur = (keep[0], keep[0]), (keep[0], keep[0])
            for i in keep[1:]:
                cur = (cur[0], i) if i == cur[1] + 1 else (i, i)
                if cur[1] - cur[0] > best[1] - best[0]:
                    best = cur
            res["usable_window_s"] = [round((best[0] + 1) * step, 2), round((best[1] + 1) * step, 2)]
    # MOTION INDEX — mean frame-difference energy over the clip.
    # ⛔ Read the caveat before comparing it to anything: this is THIS PIPELINE'S OWN measure
    # [ASSUMED], not Cutting's Visual Activity Index (which is 1 - median correlation between
    # next-adjacent frames). It is contrast-sensitive, so it compares clips of a similar look and
    # NOT a clip against a published film-scale number. What it is good for is the SPREAD across
    # one job — see motion_profile() and motion-craft.md §3.
    res["motion_index"] = round(sum(motion) / len(motion), 5) if motion else 0.0
    res["motion_peak"] = round(max(motion), 5) if motion else 0.0
    if want_look:
        res["look"] = look_of(path)
    res["landing"] = landing(motion, step)
    if line_end is None and auto_line:
        line_end = detect_line_end(path, dur)
        res["line_end_source"] = "measured" if line_end is not None else "not found"
    elif line_end is not None:
        res["line_end_source"] = "given"
    if line_end is not None:
        res["post_line"] = post_line(motion, step, line_end, dur)
    findings = []
    if res["dead_zones"]:
        longest = max(res["dead_zones"], key=lambda z: z["length_s"])
        findings.append(f"DEAD ZONE {longest['start_s']}-{longest['end_s']}s "
                        f"({longest['length_s']}s, {res['dead_pct_of_clip']}% of clip near-static)")
    if res.get("focus_decay_pct", 0) > decay_pct:
        findings.append(f"FOCUS DECAY to {res['sharpness_min']}% of peak "
                        f"(first frame {res['sharpness_first']}%, last {res['sharpness_last']}%)")
    P = res.get("post_line") or {}
    if P and P["motion_pct_of_peak"] > max_post:
        findings.append(f"POST-LINE MOTION — {P['tail_len_s']}s after the line ends "
                        f"({P['line_ends_s']}s) runs at {P['motion_pct_of_peak']}% of clip peak. "
                        f"An aftermath settles; this does not. Generate to the line and take the "
                        f"handle from the join (shot-handoff.md section 2.2)")
    L = res.get("landing") or {}
    if must_land and L and L["shape"] != "SETTLES":
        findings.append(f"NO EASE-OUT — {L['shape']}: last {L['tail_s']}s runs at "
                        f"{L['tail_pct_of_peak']}% of peak vs a clip mean of "
                        f"{L['clip_mean_pct_of_peak']}%. This shot was declared a landing; "
                        f"manufacture the settle (timing-and-performance.md section 7)")
    res["findings"] = findings
    res["verdict"] = "DEFECT" if findings else "CLEAN"
    return res


def selftest() -> int:
    assert runs_below([10, 1, 1, 1, 10], 0.25) == [(1, 3)]
    assert runs_below([1, 10, 1], 0.25) == [(0, 0), (2, 2)]
    assert runs_below([], 0.25) == []
    assert runs_below([5, 5, 5], 0.25) == []
    assert BLUR.findall("lavfi.blur=5.72\nlavfi.blur=6.1") == ["5.72", "6.1"]
    assert YAVG.findall("lavfi.signalstats.YAVG=0.0503968") == ["0.0503968"]
    # Landing classifier, against the three clips measured 2026-08-29 (tail%, mean% of peak).
    # ⛔ a clip with no motion at all must not crash and must not claim a landing
    _still = landing([0.0, 0.0, 0.0, 0.0], 0.083)
    assert _still["shape"] == "NO MOTION" and _still["tail_pct_of_peak"] == 0.0, _still
    assert classify_landing(75.0, 46.0) == "ENDS ACCELERATING"   # A_prompt
    assert classify_landing(53.0, 35.0) == "ENDS ACCELERATING"   # B_flf
    assert classify_landing(83.0, 66.0) == "ENDS ACCELERATING"   # C_flf_crop
    assert classify_landing(20.0, 60.0) == "SETTLES"             # a clip that eases out
    assert classify_landing(55.0, 50.0) == "ENDS MID-MOTION"     # high tail, no acceleration
    lm = landing([0.0, 1.0, 4.0, 8.0], 0.25, tail_s=0.5)
    assert lm["shape"] == "ENDS ACCELERATING" and lm["peak_in_final_s"] and lm["peak_at_s"] == 1.0
    assert landing([], 0.25) == {}
    # Trailing-silence parser: a silence that runs to EOF is the line end; one that ends early is not.
    assert trailing_silence_start("silence_start: 4.20\n", 5.0) == 4.2
    assert trailing_silence_start("silence_start: 4.20\nsilence_end: 4.98\n", 5.0) == 4.2
    assert trailing_silence_start("silence_start: 1.00\nsilence_end: 2.00\n", 5.0) is None
    assert trailing_silence_start("silence_start: 1.0\nsilence_end: 2.0\nsilence_start: 4.1\n", 5.0) == 4.1
    assert trailing_silence_start("", 5.0) is None
    # Post-line window: last second of a 5s clip, sampled at 4/s, tail at half the peak.
    pl = post_line([8.0] * 16 + [4.0] * 4, 0.25, 4.0, 5.0)
    assert pl["motion_pct_of_peak"] == 50.0 and pl["tail_len_s"] == 1.0

    # --- the motion profile: the film as one object -------------------------------------------
    def R(f, d, m):
        return {"file": f, "duration_s": d, "motion_index": m}
    # a film where every shot runs at one energy is FLAT, whatever the absolute values
    flat = motion_profile([R("S1.mp4", 5.0, 0.010), R("S2.mp4", 4.0, 0.012),
                           R("S3.mp4", 5.0, 0.011), R("S4.mp4", 3.0, 0.013)])
    assert any("FLAT FILM" in f for f in flat["findings"]), flat
    # ...and the SAME shape scaled up ten times is equally flat — the test is a ratio, not a floor,
    # so a bright high-contrast job cannot buy its way out of the finding
    flat10 = motion_profile([R("S1.mp4", 5.0, 0.10), R("S2.mp4", 4.0, 0.12),
                             R("S3.mp4", 5.0, 0.11), R("S4.mp4", 3.0, 0.13)])
    assert any("FLAT FILM" in f for f in flat10["findings"]), flat10
    assert flat["range_ratio"] == flat10["range_ratio"]
    # a film with a real range is not flagged
    ranged = motion_profile([R("S1.mp4", 5.0, 0.004), R("S2.mp4", 2.0, 0.090),
                             R("S3.mp4", 4.0, 0.030), R("S4.mp4", 2.5, 0.061)])
    assert not any("FLAT FILM" in f for f in ranged["findings"]), ranged
    # the modern coupling: short shots busier -> negative r -> no finding
    assert ranged["duration_motion_r"] < 0, ranged
    # the inverted coupling — long shots are the busy ones — IS reported
    inverted = motion_profile([R("S1.mp4", 2.0, 0.004), R("S2.mp4", 8.0, 0.090),
                               R("S3.mp4", 4.0, 0.030), R("S4.mp4", 6.0, 0.061)])
    assert any("LONGER shots are the busier" in f for f in inverted["findings"]), inverted
    # ⛔ two clips is not a film: no spread is claimed from a sample that cannot carry one
    tiny = motion_profile([R("S1.mp4", 5.0, 0.01), R("S2.mp4", 5.0, 0.01)])
    assert tiny["findings"] == [] and "note" in tiny, tiny
    assert post_line([1.0], 0.25, 5.0, 5.0) == {}
    print("motion profile: flat, scaled-flat, ranged, inverted coupling, and a 2-clip sample OK")

    # --- the look profile: do the shots that should match, match? ------------------------------
    def L(f, luma, cu=0.0, cv=0.0):
        return {"file": f, "look": {"luma": luma, "cast_u": cu, "cast_v": cv,
                                    "cast": (cu * cu + cv * cv) ** 0.5,
                                    "cast_dir": "warm" if cv >= cu else "cool"}}
    assert scene_of("S1-C1.mp4") == "S1" and scene_of("S12B.mov") == "S12" \
        and scene_of("S3-R.mp4") == "S3"
    assert scene_of("final_v4.mp4") is None            # not forced into a scene
    tight = look_profile([L("S1-C1.mp4", 120, 2, 3), L("S1-C2.mp4", 124, 3, 4),
                          L("S1-R.mp4", 118, 2, 3)])
    assert tight["findings"] == [], tight            # a scene that holds together is not flagged
    # ⛔ the SAME numbers split across two scenes must also produce nothing — drift BETWEEN scenes
    # is the film doing its job, and comparing them would flag every film ever made
    across = look_profile([L("S1-C1.mp4", 60, 0, 0), L("S2-C1.mp4", 180, 12, -12)])
    assert across["findings"] == [], across
    dark = look_profile([L("S1-C1.mp4", 60), L("S1-C2.mp4", 140)])
    assert any("brightness spread" in f for f in dark["findings"]), dark
    # ...and it is phrased as a QUESTION to the director, not a verdict
    assert any("Deliberate" in f and "?" in f for f in dark["findings"]), dark
    cast = look_profile([L("S1-C1.mp4", 120, -10, 10), L("S1-C2.mp4", 122, 8, -8)])
    assert any("colour cast spread" in f for f in cast["findings"]), cast
    solo = look_profile([L("S1-C1.mp4", 60), L("S2-C1.mp4", 200)])
    assert solo["findings"] == [], solo              # one shot alone cannot disagree

    # ⛔ cadence and frame size are FILM-WIDE, not scene-scoped: no scene is legitimately a
    # different frame rate. The same two clips that produce NO look finding across scenes must
    # still produce a cadence finding.
    def F(f, fps_, w=1080, h=1920):
        r = L(f, 120, 2, 3)
        r["look"].update({"fps": fps_, "width": w, "height": h})
        return r
    same = look_profile([F("S1-C1.mp4", 24.0), F("S2-C1.mp4", 24.0)])
    assert not any("MIXED CADENCE" in f for f in same["findings"]), same
    assert not any("MIXED FRAME SIZE" in f for f in same["findings"]), same
    mixed = look_profile([F("S1-C1.mp4", 24.0), F("S2-C1.mp4", 30.0)])
    assert any("MIXED CADENCE" in f for f in mixed["findings"]), mixed
    # ...and it fires ACROSS scenes, which is exactly where the look checks stay silent
    assert not any("brightness" in f or "colour cast" in f for f in mixed["findings"]), mixed
    sized = look_profile([F("S1-C1.mp4", 24.0), F("S2-C1.mp4", 24.0, 1076, 1926)])
    assert any("MIXED FRAME SIZE" in f for f in sized["findings"]), sized
    assert "1076x1926" in " ".join(sized["findings"]), sized
    # a clip whose format could not be probed is skipped, not guessed at
    nofmt = look_profile([F("S1-C1.mp4", 24.0), L("S2-C1.mp4", 120)])
    assert not any("MIXED" in f for f in nofmt["findings"]), nofmt
    # --- the cut plan ---------------------------------------------------------------------------
    def C(f, dur, peak, w=None, shape="ENDS ACCELERATING"):
        return {"file": f, "duration_s": dur, "usable_window_s": w or [0.08, dur],
                "landing": {"peak_at_s": peak, "shape": shape}}
    # a clip whose peak is its own last frame has NO out-point — the headline finding
    cp = cut_plan([C("S1.mp4", 4.04, 4.0)])
    assert "NO TAIL" in cp["clips"][0]["note"], cp
    assert any("GENERATION-PLAN finding" in f for f in cp["findings"]), cp
    # ...and one with room is cut just past the peak
    cp2 = cut_plan([C("S2.mp4", 6.04, 2.0)])
    assert "NO TAIL" not in cp2["clips"][0]["note"], cp2
    assert cp2["clips"][0]["out_s"] == 2.3, cp2["clips"][0]
    # the in-point clears the measured morph-settle, never starts at 0
    assert cp2["clips"][0]["in_s"] >= LEAD_SETTLE_S, cp2["clips"][0]
    # ⛔ a clip whose SHARP window closes early must not be cut past it
    cp3 = cut_plan([C("S3.mp4", 5.04, 3.17, w=[0.08, 2.67])])
    assert cp3["clips"][0]["out_s"] <= 2.67, cp3["clips"][0]
    # yield is reported across the film, not per clip
    cp4 = cut_plan([C("A.mp4", 5.0, 2.0), C("B.mp4", 5.0, 2.0)])
    assert cp4["generated_s"] == 10.0 and 0 < cp4["yield_pct"] < 100, cp4
    print("cut plan: no-tail clips flagged as a GENERATION-PLAN finding, the in-point clears the "
          "morph-settle, and the out-point never runs past the sharp window")

    print("look profile: brightness/cast within-scene, cadence and frame size film-wide, "
          "a question not a verdict, unprobed clips skipped")
    print("selftest OK — run detection, metadata parsers, landing classifier, silence parser")
    print("NOTE: proves the maths, NOT that the thresholds are right for your model roster.")
    return 0


FLAT_RATIO = 2.0     # [ASSUMED 2026-09-07] — replace with a measurement from real jobs


def probe_format(path: str) -> dict:
    """Frame size and cadence, from the DELIVERED file.

    ⛔ Measured 2026-09-07, and this is why it reads the file rather than any request: one real job
    carried THREE different resolutions — the request said 1080p, the stored params said 768x1344,
    and ffprobe on what actually arrived said 1076x1926. Third recurrence of that class on this
    account. Neither the request nor the vendor's label is evidence of what you received."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate", "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True)
    vals = [x for x in r.stdout.split() if x]
    out = {}
    if len(vals) >= 3:
        try:
            out["width"], out["height"] = int(vals[0]), int(vals[1])
            num, _, den = vals[2].partition("/")
            out["fps"] = round(float(num) / float(den or 1), 3)
        except (ValueError, ZeroDivisionError):
            return {}
    return out


def look_of(path: str, fps: int = 2) -> dict:
    """Mean luma and mean colour cast over the clip, from ffmpeg signalstats.

    Sampled at 2 fps by default: a look is a property of the whole clip, and there is nothing to
    learn from 12 samples a second of it."""
    vf = f"fps={fps},signalstats,metadata=print:file=-"
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "null", "-"],
                       capture_output=True, text=True)
    blob = r.stdout + r.stderr
    ys = [float(x) for x in LOOK_Y.findall(blob)]
    us = [float(x) for x in LOOK_U.findall(blob)]
    vs = [float(x) for x in LOOK_V.findall(blob)]
    if not ys:
        return {}
    mu = (sum(us) / len(us)) if us else 128.0
    mv = (sum(vs) / len(vs)) if vs else 128.0
    du, dv = mu - 128.0, mv - 128.0
    return {**probe_format(path),
            "luma": round(sum(ys) / len(ys), 2),
            "cast_u": round(du, 2), "cast_v": round(dv, 2),
            "cast": round((du * du + dv * dv) ** 0.5, 2),
            # V above neutral is the red end, U above neutral the blue end. A single word, not a
            # temperature: "warm" here means the mean cast leans red/yellow, nothing more.
            "cast_dir": "warm" if dv >= du else "cool"}


def scene_of(name: str):
    m = SCENE_RE.match(os.path.splitext(os.path.basename(name))[0])
    return m.group(1).upper() if m else None


def look_profile(rows: list, luma_spread: float = LOOK_LUMA_SPREAD,
                 cast_spread: float = LOOK_CAST_SPREAD) -> dict:
    """Do the shots that are supposed to match, match?

    ⛔ Compares only WITHIN a scene, for the same reason breakdown.py compares only attributes the
    plan declares: shots in one scene are supposed to be one place, one light and one camera, and
    drift between scenes is the film doing its job. A checker that compared a night exterior against
    a kitchen would manufacture a finding on every film ever made.

    ⛔ And every finding is addressed to the director as a QUESTION. A lamp switched on mid-scene is
    a legitimate change and is indistinguishable from model drift by reading numbers. What this
    refuses to allow is the third state: differing because nobody decided."""
    out = {"clips": len(rows), "scenes": {}, "findings": [],
           "luma_spread": luma_spread, "cast_spread": cast_spread}
    by_scene = {}
    for r in rows:
        lk = r.get("look") or {}
        sc = scene_of(r.get("file", ""))
        if not lk or not sc:
            continue
        by_scene.setdefault(sc, []).append((r["file"], lk))
    # ⛔ FILM-WIDE, not scene-scoped, and the distinction is the whole design. Brightness and cast
    # are compared inside a scene because a night exterior is legitimately darker than a kitchen.
    # Cadence and frame size are compared across the WHOLE film because no scene is legitimately a
    # different frame rate or a different frame size — that is not a look, it is a conform error,
    # and the edit will resample or letterbox it silently.
    # Found by hand on 2026-09-07: 24fps on the kling3_0 clips and 30fps on the wan2_7 clips inside
    # one film, plus 1080x1920 next to 1076x1926. Nothing in this skill compared either.
    looks = [r.get("look") or {} for r in rows]
    fps_seen, size_seen = {}, {}
    for r in rows:
        lk = r.get("look") or {}
        if lk.get("fps"):
            fps_seen.setdefault(lk["fps"], []).append(r["file"])
        if lk.get("width"):
            size_seen.setdefault((lk["width"], lk["height"]), []).append(r["file"])
    out["cadence"] = {str(k): v for k, v in sorted(fps_seen.items())}
    out["sizes"] = {f"{w}x{h}": v for (w, h), v in sorted(size_seen.items())}
    if len(fps_seen) > 1:
        groups = "; ".join(f"{k:g}fps → {', '.join(v)}" for k, v in sorted(fps_seen.items()))
        out["findings"].append(
            f"MIXED CADENCE across the film — {groups}. One film is one frame rate: the edit will "
            f"resample the odd ones silently and the motion judders where it does. Conform them "
            f"before the cut, not after")
    if len(size_seen) > 1:
        groups = "; ".join(f"{k} → {', '.join(v)}" for k, v in sorted(out["sizes"].items()))
        out["findings"].append(
            f"MIXED FRAME SIZE across the film — {groups}. Anything that is not the delivery size "
            f"gets scaled or letterboxed by the timeline. ⛔ Read this off the DELIVERED file only: "
            f"one measured job carried three different resolutions — the request, the stored params "
            f"and the actual pixels all disagreed")
    for sc, items in sorted(by_scene.items()):
        rowsl = [{"file": f, **lk} for f, lk in items]
        out["scenes"][sc] = rowsl
        if len(items) < 2:
            continue
        lumas = [lk["luma"] for _, lk in items]
        mean = sum(lumas) / len(lumas)
        spread = (max(lumas) - min(lumas)) / mean if mean else 0.0
        lo = min(items, key=lambda x: x[1]["luma"])
        hi = max(items, key=lambda x: x[1]["luma"])
        if spread > luma_spread:
            out["findings"].append(
                f"{sc}: brightness spread {spread * 100:.0f}% across shots that share a scene — "
                f"{lo[0]} at {lo[1]['luma']:.0f} against {hi[0]} at {hi[1]['luma']:.0f}. Deliberate "
                f"(a light comes on, a door opens), or model drift nobody decided?")
        cu = [lk["cast_u"] for _, lk in items]
        cv = [lk["cast_v"] for _, lk in items]
        cdist = ((max(cu) - min(cu)) ** 2 + (max(cv) - min(cv)) ** 2) ** 0.5
        if cdist > cast_spread:
            warm = max(items, key=lambda x: x[1]["cast_v"])
            cool = min(items, key=lambda x: x[1]["cast_v"])
            out["findings"].append(
                f"{sc}: colour cast spread {cdist:.1f} code values across one scene — {warm[0]} "
                f"reads {warm[1]['cast_dir']}, {cool[0]} reads {cool[1]['cast_dir']}. Every model is "
                f"a different camera (editing-and-audio.md): normalise per model before matching, "
                f"and hold one grade over the whole film")
    return out


def motion_profile(rows: list, flat_ratio: float = FLAT_RATIO) -> dict:
    """The film as one object: does it have any motion dynamic range?

    The measured finding this exists for [PRIMARY - Cutting et al., i-Perception 2011, 160 films]:
    average shot length fell from ~10s to under 4s across 75 years WHILE motion magnitude rose, and
    the two became COUPLED (r = -.46) - short shots increasingly carry proportionately MORE motion.
    Short-and-static is a combination no era of film produced, and it is this pipeline's default
    output: a 5s generation of a slow push, cut to two seconds.

    ⛔ What this does NOT do, deliberately: it sets no absolute floor on the motion index. An
    absolute threshold here would be the same error as an absolute demand count in prompt_lint -
    a number invented rather than derived, fighting content that legitimately varies. The
    comparison is INTERNAL to the job, where contrast sensitivity cancels: a film whose busiest
    shot is barely busier than its quietest has one motion setting, whatever the absolute values.
    """
    vals = [(r["file"], r.get("duration_s") or 0.0, r.get("motion_index") or 0.0) for r in rows]
    live = [v for v in vals if v[2] > 0]
    out = {"clips": len(vals), "measured": len(live), "flat_ratio": flat_ratio, "findings": []}
    if len(live) < 3:
        out["note"] = ("fewer than three measured clips - a spread needs a film, not a shot")
        out["rows"] = [{"file": f, "duration_s": d, "motion_index": m} for f, d, m in vals]
        return out
    lo = min(live, key=lambda v: v[2])
    hi = max(live, key=lambda v: v[2])
    ratio = (hi[2] / lo[2]) if lo[2] else float("inf")
    out.update(quietest=lo[0], busiest=hi[0], min_index=lo[2], max_index=hi[2],
               range_ratio=round(ratio, 2))
    out["rows"] = sorted(({"file": f, "duration_s": d, "motion_index": m,
                           "pct_of_busiest": round(100 * m / hi[2], 1)} for f, d, m in live),
                         key=lambda r: r["motion_index"])
    if ratio < flat_ratio:
        out["findings"].append(
            f"FLAT FILM - the busiest shot ({hi[0]}) carries only {ratio:.2f}x the motion of the "
            f"quietest ({lo[0]}). Every shot is running at one energy, which is what 'looks AI' "
            f"usually is. Give the film a range: motion-craft.md sections 3 and 6")
    # the coupling: in modern film shorter shots are BUSIER (negative correlation)
    n = len(live)
    mx = sum(v[1] for v in live) / n
    my = sum(v[2] for v in live) / n
    sxy = sum((v[1] - mx) * (v[2] - my) for v in live)
    sxx = sum((v[1] - mx) ** 2 for v in live)
    syy = sum((v[2] - my) ** 2 for v in live)
    r = sxy / ((sxx * syy) ** 0.5) if sxx > 0 and syy > 0 else 0.0
    out["duration_motion_r"] = round(r, 3)
    if r > 0.3:
        out["findings"].append(
            f"the LONGER shots are the busier ones (r = {r:+.2f}). Modern film runs the other way "
            f"(r = -.46, Cutting et al. 2011) - short shots carry proportionately MORE motion. "
            f"With {n} clips this is a weak signal, not a verdict")
    return out


LEAD_SETTLE_S = 0.4      # [PRIMARY · own testing, three clips · 2026-08-29] the i2v morph-settle
MIN_TAIL_S = 0.3         # tail after the peak needed before you can cut OUT of it [ASSUMED]


def no_tail(duration_s: float, peak_s: float | None, min_tail: float = MIN_TAIL_S) -> bool:
    """NO TAIL: under `min_tail` after the motion peak, so there is nothing to cut out of. One predicate, shared with
    cut_plan.py (3.0.0)."""
    return peak_s is None or (duration_s - peak_s) < min_tail


def cut_plan(rows: list, lead: float = LEAD_SETTLE_S, min_tail: float = MIN_TAIL_S) -> dict:
    """Where each clip can actually be cut, from what was already measured.

    ⛔ The finding this exists for, measured on 12 real clips 2026-09-07: **the motion peak lands in
    the last 3% of the clip on 5 of 12** (median peak position 73% of duration). `editing-and-audio.md`
    says "cut on motion peaks, not rests — motion masks the clip seam", and this tool's own per-clip
    advice says "cut OUT of that peak and the join is invisible". Both are right and both are
    unusable when the peak IS the last frame: there is nothing after it to cut on, so the join lands
    on the peak with no handle and the shot ends mid-gesture.

    ⛔ And mid-gesture is the one join the evidence says viewers actually register: action
    discontinuity drove perceived event boundaries at 0.96 (p<.001) while spatial and temporal
    discontinuity had a NEGATIVE effect [PRIMARY · Magliano & Zacks, Cognitive Science 2011].
    Jump place and time freely; never cut mid-action. So a clip whose peak is its last frame has no
    good out-point at all — the fix is upstream: generate longer than the beat needs."""
    out = {"clips": [], "findings": []}
    for r in rows:
        L = r.get("landing") or {}
        dur = r.get("duration_s") or 0.0
        peak = L.get("peak_at_s")
        w = r.get("usable_window_s") or [0.0, dur]
        rec = {"file": r.get("file"), "duration_s": dur, "peak_at_s": peak,
               "peak_pct": round(100 * peak / dur, 1) if (peak and dur) else None,
               "shape": L.get("shape")}
        # IN: past the morph-settle, and not before the sharp window opens
        rec["in_s"] = round(max(lead, w[0]), 2)
        if not no_tail(dur, peak, min_tail):
            # cut just after the peak: motion masks the seam and the gesture has completed
            rec["out_s"] = round(min(peak + min_tail, w[1], dur), 2)
            rec["note"] = "cut just past the peak — motion masks the seam"
        else:
            rec["out_s"] = round(min(w[1], dur), 2)
            rec["note"] = ("⛔ NO TAIL — the peak is the last frame, so there is nothing to cut out "
                           "of and the join lands mid-gesture")
            out["findings"].append(
                f"{r.get('file')}: energy peaks at {peak}s of {dur}s ({rec['peak_pct']:.0f}% in) — "
                f"no usable tail. Generate this beat LONGER than it needs to be on screen so the "
                f"peak lands inside the clip; a clip generated to its on-screen length has its edit "
                f"point on its own last frame, which is a butt join, not a cut")
        rec["on_screen_s"] = round(max(0.0, rec["out_s"] - rec["in_s"]), 2)
        rec["trimmed_pct"] = round(100 * (1 - rec["on_screen_s"] / dur), 1) if dur else 0.0
        out["clips"].append(rec)
    if out["clips"]:
        kept = sum(c["on_screen_s"] for c in out["clips"])
        gen = sum(c["duration_s"] for c in out["clips"])
        out["generated_s"], out["on_screen_s"] = round(gen, 2), round(kept, 2)
        out["yield_pct"] = round(100 * kept / gen, 1) if gen else 0.0
        noroom = sum(1 for c in out["clips"] if "NO TAIL" in c["note"])
        if noroom:
            out["findings"].insert(0, (
                f"{noroom} of {len(out['clips'])} clip(s) peak with no tail to cut out of. That is "
                f"a GENERATION-PLAN finding, not an edit one: the handles have to be generated, and "
                f"they cannot be added afterwards"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips", nargs="*", help="clip file(s)")
    ap.add_argument("--fps", type=int, default=12, help="sampling rate (default 12)")
    ap.add_argument("--dead-threshold", type=float, default=0.25,
                    help="motion below this fraction of the clip's peak counts as near-static (default 0.25)")
    ap.add_argument("--max-decay", type=float, default=25.0,
                    help="allowed sharpness loss from peak, in percent (default 25)")
    ap.add_argument("--lead-in", type=float, default=0.5,
                    help="ignore near-static in the first N seconds — an i2v clip always opens on "
                         "its start image (default 0.5). Set 0 to police the opening too.")
    ap.add_argument("--landing", action="store_true",
                    help="this shot has to LAND (end of sequence, held beat, last shot before the "
                         "CTA) — a clip that does not ease out becomes a DEFECT. Off by default: "
                         "ending mid-motion is an ASSET when you cut out of it")
    ap.add_argument("--line-ends", type=float, default=None, metavar="SECONDS",
                    help="where the spoken line stops. Motion after it is measured: an aftermath "
                         "settles, an undirected tail does not. Take it from the VO's real length")
    ap.add_argument("--auto-line-end", action="store_true",
                    help="find the line end from the trailing silence in the clip's own audio "
                         "(amplitude-based — music or a loud bed will hide it; prefer --line-ends)")
    ap.add_argument("--max-post-line", type=float, default=30.0,
                    help="post-line motion above this %% of the clip's peak is a defect (default 30)")
    ap.add_argument("--cut-plan", action="store_true",
                    help="where each clip can actually be CUT, from what was already measured: the "
                         "in-point past the morph-settle, the out-point just past the energy peak, "
                         "and the clips that have no tail to cut out of at all. Pass the clips in "
                         "the order they appear in the film")
    ap.add_argument("--look-profile", action="store_true",
                    help="do the shots that are supposed to MATCH, match? Mean luma and colour cast "
                         "per clip, compared WITHIN each scene. Give it the whole clips folder. "
                         "See motion-craft.md and editing-and-audio.md (every model is a different "
                         "camera)")
    ap.add_argument("--motion-profile", action="store_true",
                    help="the film as ONE object: every clip's motion index against every other's, "
                         "and whether the job has any motion dynamic range at all. Give it the "
                         "whole clips folder. See motion-craft.md section 3")
    ap.add_argument("--flat-ratio", type=float, default=FLAT_RATIO,
                    help=f"busiest/quietest motion below this is a FLAT FILM (default "
                         f"{FLAT_RATIO} — [ASSUMED], replace it with a measurement from real jobs)")
    ap.add_argument("--quiet", action="store_true", help="one line per clip")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.clips:
        print("error: give at least one clip (or --selftest). See --help.", file=sys.stderr)
        return 2
    need("ffmpeg"); need("ffprobe")

    out, bad = [], False
    for c in a.clips:
        if not os.path.exists(c):
            print(f"error: no such file: {c}", file=sys.stderr); return 2
        r = analyse(c, a.fps, a.dead_threshold, a.max_decay, a.lead_in, a.landing,
                    a.line_ends, a.auto_line_end, a.max_post_line, a.look_profile)
        out.append(r)
        bad = bad or r["verdict"] == "DEFECT"
        if a.json:
            continue
        if a.quiet:
            print(f"[{r['verdict']:6}] {r['file']:<40} " + ("; ".join(r["findings"]) or "no mechanical defect"))
            continue
        print(f"\n{r['file']} — {r['duration_s']}s @ {r['fps']} samples/s")
        print(f"  verdict: {r['verdict']}")
        for f in r["findings"]:
            print(f"  ! {f}")
        if not r["findings"]:
            print("  no dead zone, no focus decay past threshold")
        P = r.get("post_line") or {}
        if P:
            print(f"  post-line: line ends {P['line_ends_s']}s ({r.get('line_end_source')}), "
                  f"{P['tail_len_s']}s of tail at {P['motion_pct_of_peak']}% of peak")
        elif r.get("line_end_source") == "not found":
            print("  post-line: no trailing silence found in the audio — pass --line-ends instead")
        L = r.get("landing") or {}
        if L:
            where = "in the final second" if L["peak_in_final_s"] else "mid-clip"
            print(f"  energy: peak at {L['peak_at_s']}s ({where}); last {L['tail_s']}s at "
                  f"{L['tail_pct_of_peak']}% of peak vs clip mean {L['clip_mean_pct_of_peak']}% "
                  f"-> {L['shape']}")
            if L["shape"] != "SETTLES" and not a.landing:
                print("    cut OUT of that peak and the join is invisible; if this shot has to "
                      "land, re-run with --landing")
        if r.get("usable_window_s"):
            w = r["usable_window_s"]
            print(f"  sharpest continuous window: {w[0]}-{w[1]}s  <- cut inside this if you can")
        print("  (mechanical only — the QA card and the listening gate still apply)")
    prof = motion_profile(out, a.flat_ratio) if a.motion_profile else None
    plan = cut_plan(out) if a.cut_plan else None
    look = look_profile(out) if a.look_profile else None
    if a.json:
        payload = {"clips": out}
        if prof:
            payload["motion_profile"] = prof
        if look:
            payload["look_profile"] = look
        if plan:
            payload["cut_plan"] = plan
        print(json.dumps(payload if (prof or look or plan) else out, indent=2))
        return 1 if bad else 0
    if prof:
        print("\n" + "=" * 74)
        print(f"  MOTION PROFILE — {prof['measured']}/{prof['clips']} clip(s) measured")
        if prof.get("note"):
            print(f"  {prof['note']}")
        else:
            print(f"  {'clip':<36} {'dur':>6} {'motion':>9} {'% of busiest':>13}")
            for r in prof["rows"]:
                print(f"  {r['file'][:36]:<36} {r['duration_s']:>5}s {r['motion_index']:>9.5f} "
                      f"{r['pct_of_busiest']:>12}%")
            print(f"  range {prof['range_ratio']}x  ·  duration/motion r = {prof['duration_motion_r']:+.2f} "
                  f"(modern film: -.46)")
        for f in prof["findings"]:
            print(f"  ! {f}")
        if not prof["findings"] and not prof.get("note"):
            print("  the film has a motion range; nothing mechanical to say about it")
        print("  (a motion index is not a quality score — a quiet shot next to a busy one is the")
        print("   point. What this catches is a film with only one setting.)")
    if plan:
        print("\n" + "=" * 74)
        print(f"  CUT PLAN — {plan['on_screen_s']:g}s on screen from {plan['generated_s']:g}s "
              f"generated ({plan['yield_pct']:g}% yield)")
        print(f"  {'clip':<34} {'in':>6} {'out':>7} {'screen':>7} {'peak':>7}")
        for c in plan["clips"]:
            pk = f"{c['peak_pct']:.0f}%" if c["peak_pct"] is not None else "?"
            print(f"  {c['file'][:34]:<34} {c['in_s']:>5}s {c['out_s']:>6}s "
                  f"{c['on_screen_s']:>6}s {pk:>7}")
        for f in plan["findings"]:
            print(f"  ! {f}")
        print("  (cut just past the peak: motion masks the seam. ⛔ Never cut mid-gesture — that is")
        print("   the one discontinuity viewers actually register. Jump place and time freely.)")
    if look:
        print("\n" + "=" * 74)
        print(f"  LOOK PROFILE — {sum(len(v) for v in look['scenes'].values())} clip(s) "
              f"in {len(look['scenes'])} scene(s)")
        cad = look.get("cadence") or {}
        siz = look.get("sizes") or {}
        if cad:
            print("  cadence: " + " · ".join(f"{k}fps ×{len(v)}" for k, v in cad.items())
                  + ("   ← one film is one frame rate" if len(cad) > 1 else ""))
        if siz:
            print("  frame:   " + " · ".join(f"{k} ×{len(v)}" for k, v in siz.items())
                  + ("   ← measured off the delivered file" if len(siz) > 1 else ""))
        for sc, rows in look["scenes"].items():
            print(f"  {sc}")
            for r in rows:
                print(f"    {r['file'][:34]:<34} luma {r['luma']:>6.1f}   cast {r['cast']:>5.1f} "
                      f"({r['cast_dir']})")
        for f in look["findings"]:
            print(f"  ! {f}")
        if not look["findings"]:
            print("  every scene holds together on brightness and cast")
        print("  (⛔ plane means, not a grade and not a colour temperature. This says whether shots")
        print("   that share a scene drift apart; it cannot say which one is right.)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
