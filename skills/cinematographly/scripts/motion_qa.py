#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""motion_qa.py — every clip's motion read before picture lock, and the cut's joins checked against plan.

Author, 2026-10-26: "make sure we always use motion analysis in shots, to analyze continuity, also
particular objects, framing, camera motion etc" and "We can also plan motion in one shot, to naturally
enhance the transition." Decision: *"Refuse picture lock without it"* — `gate.py approve lock` runs
`check` and refuses while anything below is missing or stale.

One report per selected clip, measured from the pixels and set against what the prompts planned:

  camera     the camera tracked through the clip and categorised (shot_graph.py), against `[CAMERA]`
  framing    where the subject is in the first, middle and last frame, and the depth of field
  subject    the moving subject: how it enters (the first moments after the lead-in) and how it exits
             (the last moments), as screen direction and position; the main action's direction,
             against the frame's `travel:` and the clip's `enter:` / `exit:`
  action     onset, commit, contact and settle (action_points.py), and whether the clip's motion
             is a single shot at all
  findings   every place the measurement and the plan disagree. A finding is a question for the
             director, not a verdict: the measurement can be wrong too.

One report per cut: every join measured (shot_graph.py: colour, exposure, screen direction, eye jump,
key side), and each planned hand-off (`exit:` of one shot, `enter:` of the next, `join:`) checked
against the screen direction measured across that cut.

Usage
-----
  python3 motion_qa.py clip 03-clips/S3_v2.mp4 --shot S3 --job <job>      [--prompt <clip prompt>]
  python3 motion_qa.py cut 07-edit/cut_v4.mp4 --cuts 07-edit/cut_v4.cuts.txt --shots S1,S2,S3 --job <job>
                                            [--whip-min <frame-widths/s>]
  python3 motion_qa.py check <job>          # what picture lock still needs (exit 1 if anything)
  python3 motion_qa.py warp 07-edit/cut_v4.mp4 --at 12.40-13.90 --shot S5 --job <job>   # a slow-down's warp check
  python3 motion_qa.py inventory <folder>/resolve-inventory.json [--star "Cross Dissolve"]   # tag the templates
  python3 motion_qa.py --selftest

At lock, `check` also holds the cut to its transition and ramp budgets (house rule 2026-10-26, C4 and
C5; the project's title card): at most 2 accent transitions, a dip only at the end, no transition on a
dialogue clip, whips as seasoning, one ramp per 20 s and 2 per video at most, and every slow-down cleared by
`warp`. It notes, without refusing, a clip that reads slower than the other clips its model made for the
job (slow motion nobody asked for) and a clip whose frames repeat.

From the timeline dump `check` also notes (`!`, never a lock refusal) and, where the dump lacks the field,
says so (`i`): a clip whose source frame rate differs from the timeline's, an audio clip not at 48 kHz; a clip under 100 % opacity with no transition or `join:` planned there, a line-up opacity left on; a planned slow-down below timeline fps ÷ source fps, where frames repeat — 60 fps on a 24 fps
timeline floors at 40 % (the source fps from the dump, else the clip's motion report; only a source
faster than the timeline — a slow-down of a clip at or under the timeline's rate is the warp check's).

Project switches (v2.48.0, switches.py; the job's CHECKPOINT `Switches:` line). With `speed-conform` a shot may declare
`ramp: conform=<speed>%` or `ramp: conform=<src fps>/<timeline fps>` (a whole-clip constant conform), or, with
`join: whip`, `ramp: ease=<min speed>%` (85 or more): neither counts against the ramp cap, each is named as lifted, and
the frame-repeat floor still holds for a conform, on any source. With `music-led` a burst may be cued to the song
(`trigger=song@<s>`); it is named as lifted and still counts. Without the switch each is a ramp, as before.

`cut` reports the camera's measured speed either side of each planned `join: whip`, in frame-widths per
second (frame-heights for a tilt), and with `--whip-min <rate>` notes a whip slower than that on either side. There is no default: measure real whips before choosing one.

Reports go to <job>/09-qa/motion/. The thresholds come from shot_graph.py and action_points.py and
are [assumed] there; this file adds only the direction threshold below, [assumed] as well.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import switches as SW  # noqa: E402  (v2.48.0, project switches: a job lifts a named house rule, with a reason)
DIR_TH = 0.05          # frame-widths (or heights) per second before a direction is named [assumed]
VIDEO_EXT = (".mp4", ".mov", ".mxf", ".m4v")
CAMERA_WORDS = [("locked", r"locked|static|tripod|no camera move|fixed"), ("handheld", r"handheld|hand-held"),
                ("push", r"push|dolly in|dolly-in|move in"), ("pull", r"pull|dolly out|dolly-out|pull-out"),
                ("pan", r"\bpan"), ("tilt", r"\btilt"), ("truck", r"truck|track(?:s|ing)? (?:left|right)|crab"),
                ("crane", r"crane|jib|boom"), ("orbit", r"orbit|arc"), ("zoom", r"zoom"), ("whip", r"whip")]


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def direction(vx: float | None, vy: float | None) -> str:
    if vx is None or vy is None:
        return "none"
    parts = []
    if abs(vx) >= DIR_TH:
        parts.append("right" if vx > 0 else "left")
    if abs(vy) >= DIR_TH:
        parts.append("down" if vy > 0 else "up")
    return "-".join(parts) or "still"


def planned_direction(text: str) -> set:
    t = (text or "").lower()
    return {w for w in ("left", "right", "up", "down") if re.search(rf"\b{w}\b", t)}


def _frame(path, t, info):
    import shot_graph as SG
    fr = SG.decode(path, max(0.0, t), t + 0.06, info, 480)
    return fr[0][1] if fr else None


def _window(path, t0, t1, info, static=False):
    """Subject and camera motion over [t0, t1], measured frame to frame and averaged. One pair far
    apart is too large a step for dense flow on fast action (a 0.3 s pair read a right-moving block
    as moving up), so every consecutive pair in the window is measured and the vectors averaged."""
    import shot_graph as SG
    fps = info.get("fps") or 24.0
    t1 = max(t1, t0 + 3.0 / fps)
    fr = SG.decode(path, max(0.0, t0), t1, info, 480)
    subs, cams = [], []
    for (ta, a), (tb, b) in zip(fr, fr[1:]):
        m = SG.motion(a, b, max(1e-3, tb - ta), static)
        cams.append(m["cam"])
        if m.get("subj"):
            subs.append(m["subj"])
    if not cams:
        return None
    mean = lambda xs, k: round(sum(x[k] for x in xs) / len(xs), 4)
    cam = {"vx": mean(cams, "vx"), "vy": mean(cams, "vy")}
    cam["label"] = SG._cam_label(cam["vx"], cam["vy"])
    subj = None
    if subs:
        subj = {"vx": mean(subs, "vx"), "vy": mean(subs, "vy"),
                "pos": [round(sum(x["pos"][0] for x in subs) / len(subs), 3),
                        round(sum(x["pos"][1] for x in subs) / len(subs), 3)],
                "pairs": len(subs)}
    return {"cam": cam, "subj": subj}


OBJ_JUMP = 0.25        # a named object moving more than this (frame fractions) across a planned match [assumed]
TRACK_FPS = 24.0        # samples per second for a named object's track [assumed]
TRACK_MIN_PTS = 4       # fewer surviving feature points than this → re-find by template [assumed]
TRACK_TM_MIN = 0.5      # template-match score below this → the object is lost on that sample [assumed]


def parse_track(spec: str) -> tuple:
    """`jar=0.42,0.55,0.12,0.20` or `jar @ 0.42,0.55,0.12,0.20` → (name, (x, y, w, h)), normalised to the
    first frame, top-left origin. Raises ValueError on anything else."""
    m = re.match(r"^\s*([\w .-]+?)\s*(?:=|@)\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*$", spec or "")
    if not m:
        raise ValueError(f"track {spec!r}: want name=x,y,w,h (0-1, the box on the first frame)")
    box = tuple(float(v) for v in m.groups()[1:])
    if not (0 <= box[0] < 1 and 0 <= box[1] < 1 and 0 < box[2] <= 1 and 0 < box[3] <= 1):
        raise ValueError(f"track {spec!r}: x, y, w, h are fractions of the frame (0-1)")
    return m.group(1).strip(), box


def track_object(path: str, info: dict, box: tuple, t0: float = 0.0, t1: float | None = None) -> dict:
    """Follow one object the director boxed on the first frame. Median flow of the feature points inside
    the box (Lucas-Kanade forward and backward, points that do not come back are dropped); when too few
    survive, the box is found again by template match against the first frame's patch. Not roto: a
    position and a size, not a matte. Positions are the box centre in frame fractions."""
    import shot_graph as SG
    np, cv2 = SG._need()
    dur = info["duration"]
    t1 = dur - 0.02 if t1 is None else t1
    frames = SG.decode_fps(path, t0, t1, info, TRACK_FPS, 480)
    if len(frames) < 2:
        return {"samples": [], "error": "too few frames decoded"}
    grey = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for _, f in frames]
    H, W = grey[0].shape
    x, y, w, h = box[0] * W, box[1] * H, max(4.0, box[2] * W), max(4.0, box[3] * H)
    tpl = grey[0][int(y):int(y + h), int(x):int(x + w)].copy()

    def feats(g, bx, by, bw, bh):
        m = np.zeros_like(g)
        m[int(max(0, by)):int(min(H, by + bh)), int(max(0, bx)):int(min(W, bx + bw))] = 255
        p = cv2.goodFeaturesToTrack(g, maxCorners=60, qualityLevel=0.01, minDistance=3, mask=m)
        return p if p is not None else np.empty((0, 1, 2), np.float32)

    pts = feats(grey[0], x, y, w, h)
    samples = [{"t": round(frames[0][0], 3), "cx": round((x + w / 2) / W, 4), "cy": round((y + h / 2) / H, 4),
                "ok": True, "how": "boxed"}]
    lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    vx = vy = 0.0          # px per sample, for the prediction when the box has to be found again
    misses = 0
    for i in range(1, len(grey)):
        a, b = grey[i - 1], grey[i]
        how, ok, good = "flow", True, 0
        px, py = x, y
        if len(pts) >= TRACK_MIN_PTS:
            p1, st1, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None, **lk)
            p0r, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, **lk)
            fb = np.linalg.norm((pts - p0r).reshape(-1, 2), axis=1)
            keep = (st1.reshape(-1) == 1) & (st2.reshape(-1) == 1) & (fb < 1.5)
            good = int(keep.sum())
            if good >= TRACK_MIN_PTS:
                d = (p1 - pts).reshape(-1, 2)[keep]
                x += float(np.median(d[:, 0])); y += float(np.median(d[:, 1]))
                pts = p1[keep].reshape(-1, 1, 2)
        if good < TRACK_MIN_PTS:
            # find the first frame's patch again around where the object should be by now; the search
            # widens by a box each sample it stays lost, so it is found again after it stops
            gx, gy = x + vx, y + vy
            mx, my = w * (2 + misses), h * (2 + misses)
            sx0, sy0 = int(max(0, gx - mx)), int(max(0, gy - my))
            sx1, sy1 = int(min(W, gx + w + mx)), int(min(H, gy + h + my))
            region = b[sy0:sy1, sx0:sx1]
            score = -1.0
            if tpl.size and region.shape[0] >= tpl.shape[0] and region.shape[1] >= tpl.shape[1]:
                r = cv2.matchTemplate(region, tpl, cv2.TM_CCOEFF_NORMED)
                _, score, _, loc = cv2.minMaxLoc(r)
            if score >= TRACK_TM_MIN:
                x, y, how, misses = float(sx0 + loc[0]), float(sy0 + loc[1]), "template", 0
                pts = feats(b, x, y, w, h)
            else:
                ok, how, misses = False, "lost", misses + 1
        elif i % 6 == 0:
            fresh = feats(b, x, y, w, h)
            if len(fresh) >= TRACK_MIN_PTS:
                pts = fresh
        if ok:
            vx, vy = x - px, y - py
            misses = 0
        samples.append({"t": round(frames[i][0], 3), "cx": round((x + w / 2) / W, 4), "cy": round((y + h / 2) / H, 4),
                        "ok": ok, "how": how})
    return {"samples": samples, "box_wh": [round(w / W, 4), round(h / H, 4)]}


def summarise_track(tr: dict, in_t: float | None = None, out_t: float | None = None) -> dict:
    """Where the object is at the in point and at the cut, which way it moves, whether it leaves the
    frame, and how much of the track is trustworthy."""
    S = [s for s in tr.get("samples", []) if s["ok"]]
    allS = tr.get("samples", [])
    if len(S) < 2:
        return {"lost_share": 1.0, "error": tr.get("error") or "lost from the start"}

    def at(t):
        if t is None:
            return None
        c = min(S, key=lambda s: abs(s["t"] - t))
        return [c["cx"], c["cy"]]
    a, b = S[0], S[-1]
    span = max(1e-3, b["t"] - a["t"])
    tail = [s for s in S if s["t"] >= b["t"] - 0.4] or S[-2:]
    tspan = max(1e-3, tail[-1]["t"] - tail[0]["t"])
    bw, bh = tr.get("box_wh", [0, 0])
    # it leaves when its centre crosses the frame edge: a box wholly outside the frame has no pixels to follow
    out = next((s for s in S if not (0.0 <= s["cx"] <= 1.0 and 0.0 <= s["cy"] <= 1.0)), None)
    edge = next((s for s in S if s["cx"] - bw / 2 < 0 or s["cx"] + bw / 2 > 1 or s["cy"] - bh / 2 < 0
                 or s["cy"] + bh / 2 > 1), None)
    return {"first": [a["cx"], a["cy"]], "last": [b["cx"], b["cy"]], "at_in": at(in_t), "at_cut": at(out_t),
            "dir": direction((b["cx"] - a["cx"]) / span, (b["cy"] - a["cy"]) / span),
            "exit_dir": direction((tail[-1]["cx"] - tail[0]["cx"]) / tspan, (tail[-1]["cy"] - tail[0]["cy"]) / tspan),
            "touches_edge_at": edge["t"] if edge else None, "leaves_frame_at": out["t"] if out else None,
            "lost_share": round(1 - len(S) / max(1, len(allS)), 3), "samples": len(allS)}


def _plan(prompt: str | None) -> dict:
    if not prompt or not os.path.isfile(prompt):
        return {}
    import prompt_lint as PL
    fm, body = PL.split_front(PL.read(prompt))
    bl = PL.blocks_of(body)
    cam_txt = (bl.get("CAMERA") or "").lower()
    cam = next((k for k, rx in CAMERA_WORDS if re.search(rx, cam_txt)), None)
    plan = {"prompt": os.path.relpath(prompt), "camera": cam, "camera_text": cam_txt.strip()[:120],
            "enter": str(fm.get("enter") or ""), "exit": str(fm.get("exit") or ""),
            "join": str(fm.get("join") or ""), "cut": fm.get("cut"), "track": str(fm.get("track") or ""),
            "model": str(fm.get("model") or ""), "ramp": str(fm.get("ramp") or ""),
            "type": str(fm.get("type") or ""), "prelap": str(fm.get("prelap") or "")}
    try:
        cut = float(fm.get("cut")) if fm.get("cut") not in (None, "") else None
    except (TypeError, ValueError):
        cut = None
    if cut:
        lead = 1.0 if fm.get("start_frame") else 0.5   # prompt_lint.py LEAD_IN_S / LEAD_IN_T2V_S
        plan["in_t"], plan["out_t"] = lead, lead + cut
    frame = os.path.join(os.path.dirname(prompt), f"{fm.get('shot')}.frame.prompt.md")
    if os.path.isfile(frame):
        ffm, _ = PL.split_front(PL.read(frame))
        plan["travel"] = str(ffm.get("travel") or "")
    return plan


def _coarse_cam(cat: str | None) -> str | None:
    if not cat:
        return None
    base = cat.split("-")[0]
    return {"dolly": "push", "zoom": "push"}.get(base, base)


def report_clip(clip: str, shot: str, job: str, prompt: str | None = None, tracks: list | None = None) -> dict:
    import shot_graph as SG
    import action_points as AP
    info = SG.probe(clip)
    dur = info["duration"]
    casc = SG._cascade()
    cam = SG.camera_path(clip, 0.0, dur, info)
    framing = {}
    for name, t in (("first", 0.05), ("middle", dur / 2), ("last", max(0.0, dur - 0.1))):
        fr = _frame(clip, t, info)
        if fr is None:
            continue
        fp = SG.face_pos(fr, casc)
        comp = SG.composition(fr, fp)
        framing[name] = {"t": round(t, 3), "face": fp, "dof": comp.get("dof")}
    ap = AP.run(clip, 24.0, 160)
    action = {k: ap[k] for k in ("onset", "peak", "contact", "settle", "in_point", "cut_point", "hit", "ramp",
                                 "warnings")}
    plan = _plan(prompt)
    static = camera_taken(plan, cam) in ("locked", "drift")
    # the in point and the cut inside the clip: from `cut:` (lead-in + cut) when the prompt has one,
    # otherwise the first moments after the settle and the clip's own end
    out_t = min(dur, plan["out_t"]) if plan.get("out_t") else dur
    lead = plan["in_t"] if plan.get("in_t") else min(1.0, max(0.3, ap["onset"]["t"] - 0.2))
    m_in = _window(clip, lead, lead + 0.25, info, static)
    m_out = _window(clip, max(0.0, out_t - 0.4), max(0.0, out_t - 0.15), info, static)
    on, ct = ap["onset"]["t"], ap["contact"]["t"]
    m_act = _window(clip, on, ct if ct > on else on + 0.3, info, static)
    sub = lambda m: (m or {}).get("subj") or {}

    def dir_of(m):  # nothing measured → "none"; measured and nothing moving → "still"
        if m is None:
            return "none"
        return direction(sub(m).get("vx"), sub(m).get("vy")) if sub(m) else "still"
    subject = {
        "enter": {"t": round(lead, 3), "dir": dir_of(m_in), "pos": sub(m_in).get("pos"),
                  "camera": ((m_in or {}).get("cam") or {}).get("label")},
        "action": {"t": round(on, 3), "dir": dir_of(m_act), "pos": sub(m_act).get("pos")},
        "exit": {"t": round(max(0.0, out_t - 0.4), 3), "dir": dir_of(m_out), "pos": sub(m_out).get("pos"),
                 "camera": ((m_out or {}).get("cam") or {}).get("label")},
        "camera_held": static}
    findings = list(ap.get("warnings") or [])
    # named objects the director boxed on the first frame (`--track`, or `track:` in the clip prompt)
    specs = list(tracks or []) + [t for t in re.split(r"\s*;\s*", plan.get("track", "")) if t.strip()]
    objects = {}
    for spec in specs:
        name, box = parse_track(spec)
        tsum = summarise_track(track_object(clip, info, box), plan.get("in_t"), out_t)
        tsum["box"] = list(box)
        objects[name] = tsum
        if tsum.get("lost_share", 1.0) > 0.3:
            findings.append(f"object {name!r}: lost on {tsum.get('lost_share', 1.0):.0%} of the samples — check its path by eye")
    pc = pace(clip, info)
    if (pc.get("repeat_share") or 0) > PACE_REPEAT_MAX:
        findings.append(f"pace: frames repeat on {pc['repeat_share']:.0%} of the pairs — the model rendered at a lower "
                        f"rate, or the clip was retimed by frame repeat: it stutters. Conform it at its own rate, or retake")
    cf = camera_finding(plan, cam)
    if cf:
        findings.append(cf)
    for key, meas in (("travel", subject["action"]["dir"]), ("enter", subject["enter"]["dir"]),
                      ("exit", subject["exit"]["dir"])):
        want = planned_direction(plan.get(key, ""))
        got = set(meas.split("-")) & {"left", "right", "up", "down"}
        if want and not (want & got):
            findings.append(f"{key}: planned {', '.join(sorted(want))}, measured {meas}")
    rep = {"shot": shot, "file": os.path.relpath(clip, job) if job else clip, "sha256": sha256_file(clip),
           "duration": round(dur, 3), "measured": dt.datetime.now().isoformat(timespec="minutes"),
           "camera": {k: cam.get(k) for k in ("category", "family", "direction", "profile", "shake", "parallax",
                                               "blocking_move", "held_pairs", "points_alone", "unsure", "unsure_why")}
           | {"taken": camera_taken(plan, cam)},
           "framing": framing, "subject": subject, "objects": objects, "action": action, "pace": pc, "plan": plan,
           "cut_window": {"in": round(lead, 3), "out": round(out_t, 3),
                          "from": "the prompt's cut:" if plan.get("out_t") else "the clip's ends"},
           "findings": findings,
           "faces_available": casc is not None,
           "thresholds_tag": "[assumed] — shot_graph.py TH, action_points.py TH, DIR_TH here"}
    out = os.path.join(job, "09-qa", "motion")
    os.makedirs(out, exist_ok=True)
    json.dump(rep, open(os.path.join(out, f"{shot}.motion.json"), "w", encoding="utf-8"), indent=1)
    open(os.path.join(out, f"{shot}.motion.md"), "w", encoding="utf-8").write(render_clip_md(rep))
    return rep


def _camera_agrees(want: str | None, got: str | None) -> bool:
    return bool(want and got) and (want == got or (want == "locked" and got == "drift"))


def camera_taken(plan: dict, cam: dict) -> str | None:
    """The camera family this report goes with. shot_graph.camera_path can keep TWO answers for one clip: its own
    (the larger area of the picture) and `points_alone` (what the tracked points said, when a larger part of
    the picture held still). A flat picture cannot tell a subject moving in front of a held camera from a camera
    travelling past a far backdrop that holds still. The PLAN can: when it names the points' answer, that one
    is taken."""
    mc = _coarse_cam(cam.get("family") or cam.get("category"))
    pa = cam.get("points_alone") or {}
    ac = _coarse_cam(pa.get("family") or pa.get("category"))
    want = plan.get("camera")
    return ac if (ac and not _camera_agrees(want, mc) and _camera_agrees(want, ac)) else mc


def camera_finding(plan: dict, cam: dict) -> str | None:
    """The planned camera against the measured one: a finding, or None when they agree (with either answer, when
    the reader kept two: see camera_taken). The reader also says when it is unsure of a move (`unsure`). Both
    are passed on in words, so a doubtful reading sends the reviewer to the clip instead of standing as a plain
    mismatch."""
    mc = _coarse_cam(cam.get("family") or cam.get("category"))
    want = plan.get("camera")
    if not (want and mc) or _camera_agrees(want, camera_taken(plan, cam)):
        return None
    f = f"camera: planned {want!r} ({(plan.get('camera_text') or '')[:60]}), measured {cam.get('category')!r}"
    pa = cam.get("points_alone") or {}
    if pa.get("category"):
        f += (f". The tracked points alone read {pa['category']!r}, while a larger part of the picture held still in "
              f"{cam.get('held_pairs')} frame pairs: a subject moving in front of a held camera, or a camera travelling "
              f"past a far backdrop that holds still. Neither answer is the plan. Look at the clip")
    if cam.get("unsure"):
        f += f". The reader is UNSURE of this move ({cam.get('unsure_why')}). Look at the clip before acting on it"
    return f


def render_clip_md(r: dict) -> str:
    s, a, c = r["subject"], r["action"], r["camera"]
    pa = c.get("points_alone") or {}
    L = [f"# Motion — {r['shot']} ({r['file']})", "",
         f"- **Camera:** {c.get('category')} {c.get('direction') or ''} · profile {c.get('profile')} · "
         f"blocking move {c.get('blocking_move')}"
         + (f" · UNSURE: {c.get('unsure_why')}" if c.get("unsure") else "")
         + (f" · SECOND ANSWER: the tracked points alone read {pa.get('category')} {pa.get('direction') or ''} "
            f"(in {c.get('held_pairs')} frame pairs a larger part of the picture held still); this report goes with "
            f"`{c.get('taken')}`" if pa.get("category") else ""),
         f"- **Subject:** enters {s['enter']['dir']} at {s['enter']['pos']} · acts {s['action']['dir']} · "
         f"exits {s['exit']['dir']} at {s['exit']['pos']}",
         f"- **Action:** onset {a['onset']['t']} s · commit {a['peak']['t']} s · contact {a['contact']['t']} s · "
         f"settle {a['settle']['t']} s · cut at {a['cut_point']['t']} s · ramp {a['ramp']['speed_pct']} %",
         f"- **Framing:** " + " · ".join(f"{k} face {v.get('face')} dof {v.get('dof')}" for k, v in r["framing"].items()),
         f"- **Pace:** speed {(r.get('pace') or {}).get('speed')} frame-widths/s (p95 of the flow, median over the clip) · "
         f"repeated frames {(r.get('pace') or {}).get('repeat_share')}",
         *[f"- **Object {n}:** {o.get('first')} → {o.get('last')} · moves {o.get('dir')} · exits {o.get('exit_dir')} · "
           f"at the cut {o.get('at_cut')} · leaves frame at {o.get('leaves_frame_at')} · lost {o.get('lost_share')}"
           for n, o in (r.get("objects") or {}).items()],
         f"- **Plan:** {json.dumps(r['plan'], ensure_ascii=False)[:300] if r['plan'] else 'no prompt given'}", "",
         "## Findings", ""]
    L += [f"- {f}" for f in r["findings"]] or ["- none — the measurement agrees with the plan"]
    L += ["", f"_{r['thresholds_tag']}_", ""]
    return "\n".join(L)


def _join_ok(a_exit: str, b_enter: str, join: str, measured_dir: str) -> str | None:
    """A planned motion hand-off against the screen direction measured across the cut."""
    j = (join or "").lower()
    if not (a_exit or b_enter or j):
        return None
    wa, wb = planned_direction(a_exit), planned_direction(b_enter)
    flip = "flip" in j or "reverse" in j
    if wa and wb and ((wa & {"left", "right"}) != (wb & {"left", "right"})) and not flip:
        return f"planned exit {sorted(wa)} and enter {sorted(wb)} disagree on screen direction (say `join: flip` if meant)"
    if j and any(k in j for k in ("motion", "action", "whip", "wipe")) and measured_dir == "flipped" and not flip:
        return f"planned a {j} hand-off, and the screen direction measured across the cut flips"
    return None


def whip_pan(j: dict) -> dict:
    """HR-13 — the camera's speed either side of a cut, as shot_graph.join_at measured it over the last and the first
    ~0.18 s: frame-widths per second for a pan, frame-heights for a tilt, whichever axis is faster. A whip moves on
    both sides of its cut, so the join's rate is the slower side. None where a side was not measured."""
    w = {"unit": "frame-widths/s"}
    for side, k in (("out", "cam_before"), ("in", "cam_after")):
        c = j.get(k) or {}
        ok = c.get("vx") is not None and c.get("vy") is not None
        w[side] = round(max(abs(c["vx"]), abs(c["vy"])), 4) if ok else None
        w[f"{side}_label"] = c.get("label") if ok else None
    sides = [w[s] for s in ("out", "in") if w[s] is not None]
    w["pan"] = min(sides) if sides else None
    return w


def whip_note(w: dict, whip_min: float | None) -> str | None:
    """HR-13 — a planned whip slower than the user's --whip-min. No threshold, or nothing measured: no note."""
    if whip_min is None or w.get("pan") is None or w["pan"] >= whip_min:
        return None
    return (f"planned `join: whip`, and the camera moves {w['pan']:.3f} frame-widths/s on its slower side (out "
            f"{w.get('out')}, in {w.get('in')}) — under --whip-min {whip_min:g}: a card that says whip is not a whip")


def report_cut(cut: str, cuts_src: str, job: str, shots: list | None, whip_min: float | None = None) -> dict:
    import shot_graph as SG
    with tempfile.TemporaryDirectory() as td:
        d = SG.measure(cut, cuts_src, "cut", td, confirmed=True, sheets=False)
    prompts = os.path.join(job, "01-script", "prompts")
    plans = {s: _plan(os.path.join(prompts, f"{s}.clip.prompt.md")) for s in (shots or [])}
    mdir = os.path.join(job, "09-qa", "motion")

    def clip_rep(s):
        p = os.path.join(mdir, f"{s}.motion.json")
        try:
            return json.load(open(p, encoding="utf-8")) if s and os.path.isfile(p) else {}
        except ValueError:
            return {}
    joins, findings, whips = [], [], []
    for j in d["cuts"]:
        a = shots[j["from"] - 1] if shots and j["from"] - 1 < len(shots) else None
        b = shots[j["to"] - 1] if shots and j["to"] - 1 < len(shots) else None
        pa, pb = plans.get(a, {}), plans.get(b, {})
        why = _join_ok(pa.get("exit", ""), pb.get("enter", ""), pa.get("join", ""), j.get("screen_dir") or "")
        row = {"n": j["n"], "t": j.get("t"), "from": a, "to": b, "flags": j.get("flags") or [],
               "screen_dir": j.get("screen_dir"), "look": j.get("look"), "delta_e": j.get("delta_e"),
               "planned": {"exit": pa.get("exit"), "enter": pb.get("enter"), "join": pa.get("join")},
               "handoff": why, "objects": {}}
        # the same named object on both sides of the join: where it leaves A and where it enters B
        oa, ob = (clip_rep(a).get("objects") or {}), (clip_rep(b).get("objects") or {})
        jn = (pa.get("join") or "").lower()
        for n in sorted(set(oa) & set(ob)):
            pout = oa[n].get("at_cut") or oa[n].get("last")
            pin = ob[n].get("at_in") or ob[n].get("first")
            if not (pout and pin):
                continue
            jump = round(((pout[0] - pin[0]) ** 2 + (pout[1] - pin[1]) ** 2) ** 0.5, 3)
            row["objects"][n] = {"out": pout, "in": pin, "jump": jump,
                                 "exit_dir": oa[n].get("exit_dir"), "enter_dir": ob[n].get("dir")}
            if jump > OBJ_JUMP and any(k in jn for k in ("motion", "action", "graphic", "carry")):
                row["flags"] = list(row["flags"]) + [
                    f"object {n!r} jumps {jump:.2f} of the frame across a planned {jn} (from each clip's cut "
                    f"window; the editor's trims can move it)"]
            ea = set((oa[n].get("exit_dir") or "").split("-")) & {"left", "right"}
            eb = set((ob[n].get("dir") or "").split("-")) & {"left", "right"}
            if ea and eb and ea != eb and "flip" not in jn and "reverse" not in jn:
                row["flags"] = list(row["flags"]) + [
                    f"object {n!r} leaves A moving {'/'.join(ea)} and enters B moving {'/'.join(eb)} — "
                    f"say `join: flip` if meant"]
        joins.append(row)
        findings += [f"cut {j['n']} ({a}→{b}): {f}" for f in row["flags"]] + ([f"cut {j['n']} ({a}→{b}): {why}"] if why else [])
        # HR-13 — a planned whip: report the pan measured across the cut; warn only against the user's --whip-min
        if "whip" in jn:
            w = dict(whip_pan(j), n=j["n"], to=b, join=pa.get("join"), **{"from": a})
            row["whip"] = w
            whips.append(w)
            note = whip_note(w, whip_min)
            if note:
                findings.append(f"cut {j['n']} ({a}→{b}): {note}")
    rep = {"cut": os.path.relpath(cut, job), "cut_sha256": sha256_file(cut), "cuts": len(joins), "shots": shots,
           "measured": dt.datetime.now().isoformat(timespec="minutes"), "joins": joins, "findings": findings,
           "whips": whips, "whip_min": whip_min,
           "thresholds_tag": "[assumed] — shot_graph.py TH" + ("; --whip-min is the user's" if whip_min is not None else "")}
    out = os.path.join(job, "09-qa", "motion")
    os.makedirs(out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(cut))[0]
    json.dump(rep, open(os.path.join(out, f"{stem}.joins.json"), "w", encoding="utf-8"), indent=1)
    return rep


def selected_shots(job: str) -> list:
    """Shots whose latest QA-LOG verdict puts them in the cut: SELECT, or PASS at a clip/selects gate."""
    p = os.path.join(job, "09-qa", "QA-LOG.md")
    if not os.path.isfile(p):
        return []
    last = {}
    for ln in open(p, encoding="utf-8"):
        if not ln.startswith("|") or "---" in ln:
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) < 3 or c[1].lower() in ("shot", "film", "-", ""):
            continue
        verdict = next((x for x in c if x in ("SELECT", "PASS", "RETAKE", "BACKUP")), None)
        gate = c[2].lower() if len(c) >= 5 else ""
        if verdict and gate not in ("frame", "master", "batch"):
            last[c[1]] = verdict
    return sorted(s for s, v in last.items() if v in ("SELECT", "PASS"))


def check_job(job: str) -> list:
    problems = []
    mdir = os.path.join(job, "09-qa", "motion")
    for s in selected_shots(job):
        rp = os.path.join(mdir, f"{s}.motion.json")
        if not os.path.isfile(rp):
            problems.append(f"{s}: no motion report — `motion_qa.py clip <its file> --shot {s} --job <job> --prompt "
                            f"<its clip prompt>`")
            continue
        try:
            r = json.load(open(rp, encoding="utf-8"))
        except ValueError:
            problems.append(f"{s}: motion report unreadable"); continue
        f = os.path.join(job, r.get("file", ""))
        if not os.path.isfile(f):
            problems.append(f"{s}: the measured file {r.get('file')} is gone — measure the clip in the cut")
        elif sha256_file(f) != r.get("sha256"):
            problems.append(f"{s}: {r.get('file')} changed after it was measured — measure it again")
    joins = sorted(glob.glob(os.path.join(mdir, "*.joins.json")))
    newest = newest_cut(job)
    if not joins:
        problems.append("no joins report for the cut — `motion_qa.py cut <the cut> --cuts <its cut list> --shots "
                        "<shot order> --job <job>`")
    elif newest:
        sha = sha256_file(newest)
        if not any(json.load(open(j, encoding="utf-8")).get("cut_sha256") == sha for j in joins):
            problems.append(f"the newest cut {os.path.relpath(newest, job)} has no joins report — measure it")
    problems += plan_checks(job)[0]
    return problems


def cut_plan_note(job: str) -> str:
    """One line on the motion-driven cut plan (cut_plan.py): absent, unresolved shots, or ready. A note, not a refusal."""
    try:
        c = json.load(open(os.path.join(job, "07-edit", "CUTS.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return "no cut plan (07-edit/CUTS.json): the windows here are the prompts' — `cut_plan.py plan <job>` proposes them from the takes"
    un = [r.get("shot") for r in c.get("shots", []) if r.get("unresolved")]
    return (f"the cut plan has unresolved shots: {', '.join(un)} (07-edit/CUTS.md); the timeline export refuses until "
            f"they are resolved" if un else f"cut plan: {len(c.get('shots', []))} shot(s) resolved, {c.get('timeline_frames')} f")


def newest_cut(job: str) -> str | None:
    edits = sorted((p for p in glob.glob(os.path.join(job, "07-edit", "*")) if p.lower().endswith(VIDEO_EXT)),
                   key=os.path.getmtime)
    return edits[-1] if edits else None


# ── D. Transitions and ramps ─────────────────────────────────────────────────────────────────────────
# House rule, 2026-10-26 (the titles and motion proposal of 2026-10-26 [studio history]): C4 "Keep burst speed-up
# + cap" — one ramp per 20 s and no more than 2 per video, whichever is lower; a burst runs 115–150 % from
# onset to contact; every slow-down passes the warp check. C5 — the hard cut governs edited AI footage: at
# most 2 accent transitions per film (the project's title card), a dip only at the end, no transition that
# needs a dialogue clip's handles (shot-handoff.md §2), a whip is seasoning. Checked at picture lock from the
# timeline Resolve reports (resolve-production-console.py DUMP_TIMELINE_JSON → 07-edit/timeline-dump.json)
# and the selected shots' prompts. Transition names are read into families; a name no family knows counts as
# its own kind.
TRANS_FAMILIES = [
    ("smooth-cut", r"smooth ?cut"),
    ("dip", r"\bdip\b|fade (?:to|out|in)\b|to (?:black|white|colou?r)\b"),
    ("dissolve", r"dissolve|cross ?fade|\bblend"),
    ("whip", r"whip|swish|\bspin\b|smear"),
    ("zoom", r"zoom|warp|punch|lens"),
    ("wipe", r"wipe|iris|clock|venetian|barn|shape|\bstar\b|heart|\bband|checker"),
    ("slide", r"slide|push|split|cube|flip|page|roll|squeeze|stretch"),
    ("light", r"leak|flash|flare|glow|burn|light"),
    ("glitch", r"glitch|rgb|chromatic|digital|pixel|noise|vhs|damage|distort"),
]
HEAD_TAIL_S = 0.5      # a dip this close to the film's first or last frame is its opening or its ending [assumed]
SEAM_EPS_S = 0.05      # clip boundaries this close count as one seam (about a frame) [assumed]
WHIP_MAX = 2           # whips per film, timeline transitions and planned `join: whip` together (2 warns)
SPEAKING = ("dialogue", "reaction", "talking_head")


def trans_family(name: str) -> str:
    n = (name or "").lower()
    return next((f for f, rx in TRANS_FAMILIES if re.search(rx, n)), n.strip() or "unnamed")


TRANS_USE = {   # what each family is for in this skill (editing-and-audio.md, the transition grammar)
    "dissolve": "time passing or a scene shift — handles on both sides, never on a dialogue clip",
    "dip": "the ending only (or an act break the title card names)",
    "smooth-cut": "a jump cut on one speaker — check the morph on a generated face",
    "whip": "an energy rise the music is already making — seasoning, 2 a film at most",
    "zoom": "an energy beat — seasoning, like a whip",
    "wipe": "a deliberate retro statement (editorial mode), otherwise not",
    "slide": "a deliberate retro or UI statement, otherwise not",
    "light": "a brand-register flourish, only where the Visual Bible asks for it",
    "glitch": "the brand's register only (Visual Bible) — it dates fast and becomes the brand voice"}


def tag_inventory(raw_path: str, out: str | None = None, star: list | None = None) -> dict:
    """Tag the inventory resolve-production-console.py INVENTORY_TEMPLATES wrote: each transition's family and
    what it is for, each title's standing (C7), the owner's stars and notes kept across re-runs."""
    raw = json.load(open(raw_path, encoding="utf-8"))
    out = out or re.sub(r"\.json$", "", raw_path) + ".tagged.json"
    prev = {}
    if os.path.isfile(out):
        for r in json.load(open(out, encoding="utf-8")).get("templates", []):
            prev[(r.get("name"), r.get("source"))] = r
    want = {s.lower() for s in (star or [])}
    rows = []
    for t in raw.get("templates", []):
        r = {k: t.get(k) for k in ("kind", "name", "source", "path")}
        if t.get("kind") == "transition":
            r["family"] = trans_family(t.get("name"))
            r["use"] = TRANS_USE.get(r["family"], "a family this skill does not know — look at it before starring it")
        elif t.get("kind") == "title":
            r["use"] = ("a Resolve title: the default engine for titles (house rule C7) — prove it once with FUSION_TITLE_SPIKE "
                        "(its words set by script and read back, its 9:16 layout) before a job leans on it")
        p = prev.get((t.get("name"), t.get("source")), {})
        r["star"] = bool(p.get("star")) or str(t.get("name") or "").lower() in want
        r["note"] = p.get("note", "")
        rows.append(r)
    count = {}
    for r in rows:
        k = r["kind"] + (f"/{r['family']}" if r.get("family") else "")
        count[k] = count.get(k, 0) + 1
    rep = {"from": os.path.basename(raw_path), "resolve": raw.get("resolve"),
           "tagged": dt.datetime.now().isoformat(timespec="minutes"), "count": dict(sorted(count.items())),
           "starred": sorted(r["name"] for r in rows if r["star"]), "ofx": raw.get("ofx") or [], "templates": rows,
           "how": "star the ones worth using (\"star\": true, or --star NAME); a title card's transitions.accents "
                  "names families or starred names"}
    json.dump(rep, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    rep["out"] = out
    return rep


def parse_ramp(text) -> dict:
    kv = {}
    for part in re.split(r"\s*[,;]\s*", str(text or "").strip()):
        k, _, v = part.partition("=")
        if k.strip():
            kv[k.strip().lower()] = v.strip()
    return kv


def _num(v):
    try:
        return float(str(v).rstrip("s%"))
    except (TypeError, ValueError):
        return None


# (v2.48.0, project switch speed-conform) Two cases the ramp rules (C4: the cap and `reveal=`) leave alone once a job
# lifts them, declared on the clip's `ramp:` in its own key=value style: a whole-clip constant conform,
# `conform=<speed>%` or `conform=<src fps>/<timeline fps>`, and a shallow ease inside a planned whip, `ease=<min speed>%`
# (85 or more) on a shot that carries `join: whip`. Without the switch either is a `ramp:` like any other: prompt_lint.py
# refuses the key as today, and the cap here counts it. The frame-repeat floor still holds for a conform.
EASE_MIN = 85.0        # the lowest speed an ease inside a whip may reach (assets/project-switches.json, speed-conform)
CONFORM_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")
PCT_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%?\s*$")
# (v2.48.0, project switch music-led) a burst cued to a sound in the song: `trigger=song@<seconds in the song>`
SONG_CUE_RE = re.compile(r"^\s*song\s*@\s*(\d+(?:\.\d+)?)\s*s?\s*$", re.I)


def speed_case(kv: dict, fm: dict | None = None) -> dict:
    """(v2.48.0, project switch speed-conform) What a parsed `ramp:` declares → {"case": "conform" | "ease" | None,
    "speed": % of real speed, "src" / "tl": the fps a `conform=<src>/<tl>` names, "problem": why it is not one of the
    two cases as written, or None}. case None is an ordinary ramp."""
    out = {"case": None, "speed": None, "src": None, "tl": None, "problem": None}
    if "conform" not in kv and "ease" not in kv:
        return out
    out["case"] = "conform" if "conform" in kv else "ease"
    if "conform" in kv and "ease" in kv:
        out["problem"] = "a conform and an ease on one shot — declare one"
        return out
    mixed = [f"`{k}=`" for k in ("kind", "speed") if k in kv]
    if mixed:
        out["problem"] = (f"`{out['case']}=` with {' and '.join(mixed)} — a speed change inside the clip on top of it is "
                          f"still a ramp: plan one or the other")
        return out
    v = str(kv.get(out["case"]) or "")
    m, p = CONFORM_RE.match(v), PCT_RE.match(v)
    if out["case"] == "conform":
        if m and float(m.group(1)) > 0:
            out.update(src=float(m.group(1)), tl=float(m.group(2)),
                       speed=round(float(m.group(2)) / float(m.group(1)) * 100, 3))
        elif p:
            out["speed"] = float(p.group(1))
        if out["speed"] is None:
            out["problem"] = f"`conform={v}` — write <speed>% (40%) or <source fps>/<timeline fps> (60/24)"
        elif not 0 < out["speed"] < 100:
            out["problem"] = (f"`conform={v}` plays the clip at {out['speed']:g} % — a conform plays the whole clip "
                              f"slower, under 100 %; a whole clip is never sped up (editing-and-audio.md, action points)")
        return out
    out["speed"] = float(p.group(1)) if p else None
    if out["speed"] is None:
        out["problem"] = f"`ease={v}` — write the lowest speed the ease reaches, as <min speed>% (90%)"
    elif out["speed"] < EASE_MIN:
        out["problem"] = (f"`ease={v}` dips to {out['speed']:g} % — an ease inside a whip goes no lower than "
                          f"{EASE_MIN:g} %; deeper is a ramp")
    elif out["speed"] >= 100:
        out["problem"] = f"`ease={v}` — an ease dips below 100 % and back; at {out['speed']:g} % there is none"
    elif "whip" not in str((fm or {}).get("join") or "").lower():
        out["problem"] = "`ease=` on a shot with no `join: whip` — the ease lives inside a planned whip"
    return out


def _prompt_fms(job: str) -> dict:
    """{shot: frontmatter} for every clip prompt."""
    import prompt_lint as PL
    out = {}
    for p in sorted(glob.glob(os.path.join(job, "01-script", "prompts", "*.clip.prompt.md"))):
        fm, _ = PL.split_front(PL.read(p))
        out[str(fm.get("shot") or os.path.basename(p).split(".")[0])] = fm
    return out


def _card(job: str) -> dict:
    p = os.path.join(job, "00-brief", "TITLE-CARD.json")
    try:
        return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}
    except ValueError:
        return {}


def timeline(job: str) -> dict | None:
    """The cut as Resolve reports it, in seconds: per video track, clips and transitions (21.1 lists a
    transition as an item of its own, `type` naming it)."""
    p = os.path.join(job, "07-edit", "timeline-dump.json")
    if not os.path.isfile(p):
        return None
    try:
        d = json.load(open(p, encoding="utf-8"))
    except ValueError:
        return None
    fps = float(d.get("fps") or 0) or 24.0
    tracks = {}
    for tn, items in (d.get("tracks") or {}).items():
        if not str(tn).startswith("video"):
            continue
        rows = []
        for it in items or []:
            s = it.get("start_s") if it.get("start_s") is not None else (it.get("start") or 0) / fps
            du = it.get("duration_s") if it.get("duration_s") is not None else (it.get("duration") or 0) / fps
            rows.append({"name": str(it.get("name") or ""), "t0": float(s), "t1": float(s) + float(du),
                         "kind": "transition" if "transition" in str(it.get("type") or "").lower() else "clip"})
        tracks[tn] = sorted(rows, key=lambda r: r["t0"])
    end = max((r["t1"] for rs in tracks.values() for r in rs), default=0.0)
    return {"fps": fps, "tracks": tracks, "end": end}


def _is_title(name: str, job: str) -> bool:
    titles = {os.path.basename(p).lower() for p in glob.glob(os.path.join(job, "07-edit", "titles", "*"))}
    return name.lower() in titles or bool(re.search(r"title|super|end ?card|lower ?third|caption", name, re.I))


def _shot_of(name: str, shots) -> str | None:
    for s in sorted(shots, key=len, reverse=True):
        if re.match(rf"{re.escape(s)}(?![A-Za-z0-9])", name, re.I):
            return s
    return None


def _speaking(fm: dict) -> bool:
    return str(fm.get("type") or "").lower() in SPEAKING or str(fm.get("grade") or "").lower() == "talking_head"


def _warp_for(job: str, sha: str | None, ci: float, co: float) -> dict | None:
    """The warp report on this cut that covers [ci, co]: a PASS if there is one, else the newest."""
    if not sha:
        return None
    hit = []
    for p in glob.glob(os.path.join(job, "09-qa", "motion", "*.warp-*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        at = d.get("at") or [None, None]
        if d.get("cut_sha256") == sha and at[0] is not None and at[0] <= ci + 0.1 and at[1] >= co - 0.1:
            hit.append(d)
    hit.sort(key=lambda d: (d.get("verdict") == "PASS", d.get("measured") or ""))
    return hit[-1] if hit else None


def plan_checks(job: str) -> tuple[list, list]:
    """The transition and ramp budgets at picture lock → (problems that refuse lock, notes)."""
    P, W = [], []
    card = _card(job)
    tr, rp = card.get("transitions") or {}, card.get("ramps") or {}
    max_acc = int(tr.get("max_accents", 2))
    accents = [str(a).lower() for a in tr.get("accents") or []]
    act_breaks = [float(x) for x in tr.get("act_breaks") or [] if _num(x) is not None]
    max_ramps, per20 = int(rp.get("max_per_video", 2)), float(rp.get("per_20s", 1) or 1)
    fms = _prompt_fms(job)
    sel = selected_shots(job) or sorted(fms)
    tl = timeline(job)
    cut = newest_cut(job)
    dur = tl["end"] if tl and tl["end"] else None
    if dur is None and cut:
        import shot_graph as SG
        dur = SG.probe(cut).get("duration")
    whips = [f"{s} (join: whip)" for s in sel if "whip" in str((fms.get(s) or {}).get("join") or "").lower()]
    if tl is None:
        W.append("no 07-edit/timeline-dump.json — the transition budget was not checked (resolve-production-console.py "
                 "DUMP_TIMELINE_JSON)")
    else:
        used = []
        for tn, rows in tl["tracks"].items():
            clips = [r for r in rows if r["kind"] == "clip"]
            if clips and all(_is_title(c["name"], job) for c in clips):
                continue                                   # a title track: the titles carry their own motion
            for r in rows:
                if r["kind"] != "transition":
                    continue
                fam = trans_family(r["name"])
                prev = max((c for c in clips if c["t0"] < r["t0"] - SEAM_EPS_S <= c["t1"]),
                           key=lambda c: c["t0"], default=None)
                nxt = min((c for c in clips if c["t1"] > r["t1"] + SEAM_EPS_S >= c["t0"]),
                          key=lambda c: c["t0"], default=None)
                where = f"{r['name']!r} at {r['t0']:.2f} s ({tn})"
                edge = r["t0"] <= HEAD_TAIL_S or r["t1"] >= tl["end"] - HEAD_TAIL_S
                used.append((r, fam, where, fam == "dip" and edge))   # the opening fade and the ending: no accent
                if fam == "whip":
                    whips.append(where)
                if fam == "dip" and not (edge or any(r["t0"] - 0.5 <= b <= r["t1"] + 0.5 for b in act_breaks)):
                    P.append(f"{where}: a dip mid-film — a dip is the ending (or an act break the title card names "
                             f"in transitions.act_breaks): mid-story it tells a feed viewer the video is over "
                             f"(editing-and-audio.md, transitions)")
                if fam != "smooth-cut":
                    for side, c in (("out of", prev), ("into", nxt)):
                        s = _shot_of(c["name"], fms) if c else None
                        if s and _speaking(fms.get(s) or {}):
                            P.append(f"{where} cuts {side} {s} ({(fms[s].get('type') or fms[s].get('grade'))}): a "
                                     f"transition eats a dialogue clip's handles, and a dialogue clip may not be "
                                     f"extended to supply them (shot-handoff.md §2) — hard-cut it, or move the "
                                     f"transition onto a silent clip or an insert")
                        elif c and not s and not _is_title(c["name"], job):
                            W.append(f"{where}: the clip {c['name']!r} beside it maps to no shot prompt — the "
                                     f"dialogue check could not read it")
            # the same accent on two seams in a row is the film's grammar, not an accent
            seams = []
            for a, b in zip(clips, clips[1:]):
                if abs(b["t0"] - a["t1"]) <= SEAM_EPS_S or (b["t0"] < a["t1"]):
                    t = (a["t1"] + b["t0"]) / 2
                    on = next((r for r in rows if r["kind"] == "transition"
                               and r["t0"] - SEAM_EPS_S <= t <= r["t1"] + SEAM_EPS_S), None)
                    seams.append((t, trans_family(on["name"]) if on else "cut"))
            for (ta, fa), (tb, fb) in zip(seams, seams[1:]):
                if fa == fb and fa not in ("cut", "smooth-cut"):
                    W.append(f"{tn}: the same {fa} on two seams in a row ({ta:.2f} s, {tb:.2f} s) — a run makes it "
                             f"the film's grammar, not an accent; right for a montage, otherwise cut one")
        fams = sorted({f for _, f, _, ends in used if f != "smooth-cut" and not ends})
        if len(fams) > max_acc:
            P.append(f"{len(fams)} kinds of transition ({', '.join(fams)}): the hard cut carries the film, with at most "
                     f"{max_acc} accents (house rule C5; the title card's transitions.max_accents)")
        if accents:
            for r, f, where, ends in used:
                if f != "smooth-cut" and not ends and f not in accents and r["name"].lower() not in accents:
                    P.append(f"{where}: not one of the title card's accents ({', '.join(accents)})")
        elif fams:
            W.append(f"the title card names no transition accents, and the cut uses {', '.join(fams)} — list them in "
                     f"transitions.accents so the budget is a decision")
        if any(f == "smooth-cut" for _, f, _, _ in used):
            W.append("a Smooth Cut morphs the face across the jump — check it at full speed: on generated faces "
                     "the morph can show")
    if len(whips) > WHIP_MAX:
        P.append(f"{len(whips)} whips ({'; '.join(whips)}): one per video is seasoning, five is a template — "
                 f"at most {WHIP_MAX} (editing-and-audio.md, transitions)")
    elif len(whips) == WHIP_MAX:
        W.append(f"{len(whips)} whips ({'; '.join(whips)}) — one per video is seasoning")
    # ramps: planned on the selected shots' clip prompts (`ramp:`, prompt_lint.py)
    ramps = [(s, parse_ramp(fms[s]["ramp"])) for s in sel if (fms.get(s) or {}).get("ramp")]
    # (v2.48.0, project switch speed-conform) with the job's switch on, a declared whole-clip conform or a shallow ease
    # inside a whip is no ramp: it leaves the cap and the spacing, named as lifted. One that does not qualify as written
    # stays a ramp and refuses. With the switch off every `ramp:` counts, exactly as before.
    lifts = []
    sc = SW.on(job, "speed-conform")
    if sc:
        kept = []
        for s, kv in ramps:
            c = speed_case(kv, fms.get(s) or {})
            if c["case"] and not c["problem"]:
                what = "a whole-clip conform" if c["case"] == "conform" else "a shallow ease inside its whip"
                lifts.append(f"{s}: `ramp: {fms[s]['ramp']}` is {what} at {c['speed']:g} %, not a ramp — the ramp cap and "
                             f"`reveal=` (house rule C4) are {SW.lifted('speed-conform', sc)}")
                continue
            if c["case"]:
                P.append(f"{s}: {c['problem']} — project switch `speed-conform` lifts the ramp rules only for a whole-clip "
                         f"conform under 100 % or an ease of {EASE_MIN:g} % or more inside a planned whip, so this "
                         f"`ramp:` is a ramp")
            kept.append((s, kv))
        ramps = kept
    # (v2.48.0, project switch music-led) a burst may be cued to a sound in the song (`trigger=song@<s>`) instead of
    # onset to contact; it is still a ramp, so the cap and the spacing below count it
    ml = SW.on(job, "music-led")
    for s, kv in (ramps if ml else []):
        cue = SONG_CUE_RE.match(str(kv.get("trigger") or ""))
        if cue and (kv.get("kind") or "").lower() == "burst":
            lifts.append(f"{s}: the burst is cued to the song at {float(cue.group(1)):g} s (`trigger=song@…`), not onset "
                         f"to contact — {SW.lifted('music-led', ml)}; it still counts against the ramp cap")
    if ramps:
        allowed = max_ramps if dur is None else min(max_ramps, max(1, int(dur * per20 // 20)))
        gap = 20.0 / per20
        if dur is None:
            W.append(f"the film's length is unknown (no timeline dump, no cut in 07-edit) — the ramp cap read as {max_ramps}")
        if len(ramps) > allowed:
            P.append(f"{len(ramps)} speed ramps ({', '.join(s for s, _ in ramps)}) in a {dur or 0:.0f} s film: at most "
                     f"{allowed} — one per {gap:.0f} s and no more than {max_ramps} per video, whichever is lower "
                     f"(house rule C4)")
        timed = sorted((_num(kv.get("cut_in")), s) for s, kv in ramps if _num(kv.get("cut_in")) is not None)
        for (ta, sa), (tb, sb) in zip(timed, timed[1:]):
            if tb - ta < gap:
                P.append(f"the ramps on {sa} and {sb} are {tb - ta:.1f} s apart: one per {gap:.0f} s (house rule C4)")
        sha = sha256_file(cut) if cut else None
        for s, kv in ramps:
            kind, ci, co = (kv.get("kind") or "").lower(), _num(kv.get("cut_in")), _num(kv.get("cut_out"))
            if ci is None or co is None or co <= ci:
                if kind == "slow":
                    P.append(f"{s}: a slow-down with no cut_in=/cut_out= on its `ramp:` (seconds in the cut) — add them "
                             f"once it is cut, then `motion_qa.py warp <the cut> --at <in>-<out> --job <job>`")
                else:
                    W.append(f"{s}: a ramp with no cut_in=/cut_out= — the title check cannot keep titles off it")
                continue
            if kind == "slow":
                w = _warp_for(job, sha, ci, co)
                rel = os.path.relpath(cut, job) if cut else "<the cut>"
                if w is None:
                    P.append(f"{s}: the slow-down at {ci:.2f}–{co:.2f} s has no warp check on the newest cut — "
                             f"`motion_qa.py warp {rel} --at {ci:.2f}-{co:.2f} --shot {s} --job <job>`")
                elif w.get("verdict") != "PASS":
                    P.append(f"{s}: the slow-down at {ci:.2f}–{co:.2f} s fails the warp check — "
                             + "; ".join((w.get("problems") or ["see its report"])[:2]))
    W += lifts                  # (v2.48.0, project switch speed-conform, music-led) every lift named in the lock output
    out = os.path.join(job, "09-qa", "motion")
    if os.path.isdir(out):
        json.dump({"measured": dt.datetime.now().isoformat(timespec="minutes"), "problems": P, "notes": W,
                   "film_s": dur, "ramps": [s for s, _ in ramps], **({"lifted": lifts} if lifts else {})},
                  open(os.path.join(out, "plan-checks.json"), "w", encoding="utf-8"), indent=1)
    return P, W


# ── what the timeline dump says about each clip: notes and info, never a lock refusal ────────────────────────────
# HR-06 a clip at another frame rate, or audio not at 48 kHz, before a frame-accurate join (delivery-format.md §4,
# editing-and-audio.md audio delivery §4) · HR-15 a line-up opacity left on · HR-17 a slow-down below timeline fps
# ÷ source fps, where frames repeat. The dump (resolve-production-console.py DUMP_TIMELINE_JSON) carries none of
# `source_fps`, `sample_rate` or `opacity` as of v2.46.1; each check says so, and runs once the dump carries it.
AUDIO_RATE = 48000      # Hz — every delivery preset's sample_rate_hz
FPS_EPS = 0.01          # frame rates closer than this are one rate (23.976 against 23.976024)


def _lead_num(v) -> float | None:
    """The leading number of a dump value: 59.94, "59.94", "29.97 DF", "48000", "48 kHz" → a float."""
    m = re.match(r"\s*(\d+(?:\.\d+)?)", str(v)) if v is not None else None
    return float(m.group(1)) if m else None


def _hz(v) -> float | None:
    x = _lead_num(v)
    return None if x is None else (x * 1000 if x < 1000 else x)


def dump_checks(job: str) -> tuple[list, list]:
    """HR-06, HR-15, HR-17 → (notes, info). Notes are questions for the editor; info names what was not checked."""
    W, I = [], []
    p = os.path.join(job, "07-edit", "timeline-dump.json")
    try:
        d = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None
    except ValueError:
        d = None
    if d is None:
        I.append("no readable 07-edit/timeline-dump.json — the frame-rate, sample-rate, opacity and slow-down floor "
                 "checks did not run")
        return W, I
    tl_fps = float(d.get("fps") or 0)
    sec = tl_fps or 24.0                                  # seconds for the overlap test only
    rows = []
    for tn, items in (d.get("tracks") or {}).items():
        for it in items or []:
            s = it.get("start_s") if it.get("start_s") is not None else (it.get("start") or 0) / sec
            du = it.get("duration_s") if it.get("duration_s") is not None else (it.get("duration") or 0) / sec
            rows.append({"track": str(tn), "name": str(it.get("name") or ""), "t0": float(s), "t1": float(s) + float(du),
                         "transition": "transition" in str(it.get("type") or "").lower(), "it": it})
    vid = [r for r in rows if r["track"].startswith("video") and not r["transition"] and not r["it"].get("text")
           and not _is_title(r["name"], job)]
    media = [r for r in vid if r["it"].get("file") or "file" not in r["it"]]   # a dump before v2.45 has no `file`
    fms = _prompt_fms(job)
    # HR-06 — a clip at another frame rate than the timeline
    if not tl_fps:
        I.append("the timeline dump carries no frame rate (`fps`) — the frame-rate and slow-down floor checks did not "
                 "run")
    elif media:
        rated = [(r, _lead_num(r["it"].get("source_fps"))) for r in media]
        known = [(r, f) for r, f in rated if f]
        if not known:
            I.append("the timeline dump carries no source frame rate (`source_fps` on each clip) — the mixed-frame-rate "
                     "check did not run")
        else:
            off = [(r, f) for r, f in known if abs(f - tl_fps) > FPS_EPS]
            if off:
                W.append(f"the timeline runs at {tl_fps:g} fps and {len(off)} clip(s) do not: "
                         + "; ".join(f"{r['name']} {f:g} fps at {r['t0']:.2f} s ({r['track']})" for r, f in off)
                         + " — conform or retime each on purpose before any frame-accurate join (delivery-format.md §4, "
                           "the frame-rate trap)")
            if len(known) < len(rated):
                I.append(f"{len(rated) - len(known)} clip(s) carry no `source_fps` — their frame rate was not checked")
    # HR-06 — audio at another sample rate than the house 48 kHz
    aud = [r for r in rows if r["track"].startswith("audio") and not r["transition"]]
    if aud:
        rated = [(r, _hz(r["it"].get("sample_rate"))) for r in aud]
        known = [(r, hz) for r, hz in rated if hz]
        if not known:
            I.append("the timeline dump carries no audio sample rate (`sample_rate` on each audio clip) — the "
                     "mixed-sample-rate check did not run")
        else:
            off = [(r, hz) for r, hz in known if abs(hz - AUDIO_RATE) > 1]
            if off:
                at48 = len(known) - len(off)
                W.append(f"{len(off)} audio clip(s) not at 48 kHz" + (f", beside {at48} that are" if at48 else "") + ": "
                         + "; ".join(f"{r['name']} {hz / 1000:g} kHz ({r['track']})" for r, hz in off)
                         + " — convert each to 48 kHz before the mix: a 44.1 kHz file in a 48 kHz timeline drifts with "
                           "no error (editing-and-audio.md, audio delivery §4)")
            if len(known) < len(rated):
                I.append(f"{len(rated) - len(known)} audio clip(s) carry no `sample_rate` — not checked")
    # HR-15 — a clip under 100 % opacity where no transition or join is planned
    if vid:
        rated = [(r, _lead_num(r["it"].get("opacity"))) for r in vid]
        known = [(r, o) for r, o in rated if o is not None]
        trans = [r for r in rows if r["track"].startswith("video") and r["transition"]]
        if not known:
            I.append("the timeline dump carries no opacity (`opacity` on each video clip) — the line-up opacity check "
                     "did not run")
        for r, o in known:
            if o >= 100:
                continue
            # planned: a transition over the clip, or a `join:` on its shot or on a shot whose clip ends at or inside it
            near = [x for x in vid if x is r or r["t0"] - SEAM_EPS_S <= x["t1"] <= r["t1"] + SEAM_EPS_S]
            joined = any(str((fms.get(_shot_of(x["name"], fms) or "") or {}).get("join") or "").strip() for x in near)
            if joined or any(t["t0"] - SEAM_EPS_S <= r["t1"] and t["t1"] + SEAM_EPS_S >= r["t0"] for t in trans):
                continue
            W.append(f"{r['name']!r} at {r['t0']:.2f} s ({r['track']}) is at {o:g} % opacity with no transition or "
                     f"`join:` planned there — a line-up opacity left on? Set it back to 100 % before export")
    # HR-17 — a planned slow-down below timeline fps ÷ source fps: the timeline asks for frames the source lacks
    sel = (selected_shots(job) or sorted(fms)) if tl_fps else []     # no timeline fps: said once above
    sc = SW.on(job, "speed-conform") if sel else None
    for s in sel:
        kv = parse_ramp((fms.get(s) or {}).get("ramp"))
        speed = _num(kv.get("speed"))
        # (v2.48.0, project switch speed-conform) a lifted conform is no ramp, and the floor still holds for it — on any
        # source, a 24 fps one included, since no warp check follows a conform
        conf = speed_case(kv, fms.get(s) or {}) if sc else {}
        conf = conf if conf.get("case") == "conform" and not conf.get("problem") else None
        if conf:
            speed = conf["speed"]
        elif (kv.get("kind") or "").lower() != "slow" or speed is None:
            continue
        src, how = None, None
        for r in media:
            if _shot_of(r["name"], fms) == s and _lead_num(r["it"].get("source_fps")):
                src, how = _lead_num(r["it"].get("source_fps")), "the timeline dump"
                break
        if src is None:
            try:
                rp = json.load(open(os.path.join(job, "09-qa", "motion", f"{s}.motion.json"), encoding="utf-8"))
                src = _lead_num((rp.get("pace") or {}).get("fps"))
                how = "its motion report" if src else None
            except (OSError, ValueError):
                pass
        if not src and conf and conf.get("src"):   # (v2.48.0, project switch speed-conform) the conform's own src fps
            src, how = conf["src"], "its `conform=`"
        if not src:
            I.append(f"{s}: the {'conform' if conf else 'slow-down'} to {speed:g} % has no known source frame rate (no "
                     f"`source_fps` in the timeline dump, no `pace.fps` in its motion report) — the frame-repeat floor "
                     f"was not checked")
            continue
        if src <= tl_fps + 1e-6 and not conf:
            # a source at or under the timeline's rate (every generated clip): any slow-down invents frames, which the
            # warp check already measures (move-catalogue.md §24). The floor is for high-frame-rate sources.
            continue
        floor = tl_fps / src * 100
        if conf and speed < floor - 1e-6:                    # (v2.48.0, project switch speed-conform)
            said = (f"; its `conform=` names {conf['src']:g} fps" if conf.get("src") and abs(conf["src"] - src) > FPS_EPS
                    else "")
            W.append(f"{s}: conformed to {speed:g} % (`conform=`), under {round(floor, 1):g} % — the floor for a {src:g} "
                     f"fps source on a {tl_fps:g} fps timeline ({tl_fps:g} ÷ {src:g}, source fps from {how}{said}): below it "
                     f"frames repeat, or the retime invents them, and no warp check follows a conform. "
                     + (f"Conform it at {round(floor, 1):g} % or faster, or shoot it at a higher rate" if floor < 100 - 1e-6
                        else "A source at or under the timeline's rate has no frames to spare: shoot it at a higher rate")
                     + " (the switch `speed-conform` does not lift the floor)")
        elif speed < floor - 1e-6:
            W.append(f"{s}: slowed to {speed:g} %, under {round(floor, 1):g} % — the floor for a {src:g} fps source on a "
                     f"{tl_fps:g} fps timeline ({tl_fps:g} ÷ {src:g}, source fps from {how}): below it frames repeat, or "
                     f"the retime invents them. Shoot or generate it at a higher rate, or slow it less; the warp check "
                     f"still decides whether it shows")
    return W, I


# ── the pace of a clip, and slow motion nobody asked for ────────────────────────────────────────────────
# Models slow footage down unasked (move-catalogue.md §24: "Without this the model ramps everywhere and the
# whole shot turns to syrup"), and unplanned slow motion reads as AI. A clip's own speed says little — a macro
# drip is slow — so a clip is set against the other clips the same model made for the job: a question for the
# director, never a refusal. Repeated frames (a lower render rate, or a retime by frame repeat) are a stutter.
DUP_TH = 0.25          # mean grey difference under which two frames are the same picture [assumed]
PACE_FPS = 12.0        # flow samples per second for the speed [assumed]
PACE_REPEAT_MAX = 0.2  # share of repeated-frame pairs (with motion around them) before it is a stutter [assumed]
PACE_MIN_N = 3         # clips from one model before one is compared with the rest [assumed]
PACE_Z = 2.0           # robust z below which a clip reads slower than its model's others [assumed]
PACE_RATIO = 0.5       # ... and under half their median speed [assumed]


def _repeats(diffs: list) -> int:
    """Pairs that show the same picture while the pairs around them move: a repeat, not a still moment."""
    n = 0
    for i, d in enumerate(diffs):
        around = max(diffs[i - 1] if i else 0.0, diffs[i + 1] if i + 1 < len(diffs) else 0.0)
        if d < DUP_TH and around > 4 * DUP_TH:
            n += 1
    return n


def pace(clip: str, info: dict) -> dict:
    import shot_graph as SG
    np, cv2 = SG._need()
    fps = info.get("fps") or 24.0
    dur = info.get("duration") or 0.0
    t0 = min(0.5, dur * 0.2)                     # past the head settle
    fr = SG.decode(clip, t0, max(t0 + 0.2, dur - 0.1), info, 160)
    g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for _, f in fr]
    if len(g) < 4:
        return {"pairs": 0, "speed": None, "repeat_share": None}
    diffs = [float(np.mean(cv2.absdiff(a, b))) for a, b in zip(g, g[1:])]
    step = max(1, int(round(fps / PACE_FPS)))
    sp = []
    for i in range(0, len(g) - step, step):
        f = cv2.calcOpticalFlowFarneback(g[i], g[i + step], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        sp.append(float(np.percentile(np.hypot(f[..., 0], f[..., 1]), 95)) / g[i].shape[1] * fps / step)
    sp.sort()
    return {"speed": round(sp[len(sp) // 2], 4) if sp else None, "repeat_share": round(_repeats(diffs) / len(diffs), 3),
            "pairs": len(diffs), "fps": round(fps, 3), "from_s": round(t0, 3)}


def pace_notes(job: str) -> list:
    """Clips that read slower than the other clips the same model made for this job (non-blocking)."""
    groups = {}
    for p in glob.glob(os.path.join(job, "09-qa", "motion", "*.motion.json")):
        try:
            r = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        sp = (r.get("pace") or {}).get("speed")
        if sp is None:
            continue
        model = (r.get("plan") or {}).get("model") or "an unnamed model"
        groups.setdefault(model, []).append((r.get("shot"), float(sp), (r.get("plan") or {}).get("ramp") or ""))
    out = []
    sc = SW.on(job, "speed-conform") if groups else None

    def planned_slow(ramp) -> bool:
        kv = parse_ramp(ramp)
        if kv.get("kind", "").lower() == "slow":
            return True
        c = speed_case(kv) if sc else {}            # (v2.48.0, project switch speed-conform) a lifted conform is planned
        return c.get("case") == "conform" and not c.get("problem")
    for model, rows in sorted(groups.items()):
        if len(rows) < PACE_MIN_N:
            continue
        xs = sorted(x for _, x, _ in rows)
        med = xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2
        dev = sorted(abs(x - med) for x in xs)
        mad = dev[len(dev) // 2]
        scale = max(1.4826 * mad, 0.1 * med, 1e-6)
        for shot, x, ramp in sorted(rows, key=lambda r: str(r[0])):
            z = (x - med) / scale
            if z < -PACE_Z and x < PACE_RATIO * med and not planned_slow(ramp):
                out.append(f"{shot}: reads slower than {model}'s other {len(rows) - 1} clips (speed {x:.3f} vs a median "
                           f"of {med:.3f} frame-widths/s, z {z:.1f}) and its prompt plans no slow-down — slow motion "
                           f"nobody asked for reads as AI: look at it at full speed; retake, or conform it faster")
    return out


# ── the warp check on a slow-down ───────────────────────────────────────────────────────────────────────
# A slowed clip is made of frames the retime invented. Optical flow (Resolve: Retime Process ▸ Optical Flow,
# Speed Warp on Studio) tears where the motion is hard to follow — hands, hair, spokes, crossing objects; a
# frame-repeat retime stutters. Each frame of the ramp is predicted from the one before by dense flow; the
# share of textured picture the prediction misses is the tear, set against the same measure on the footage
# around the ramp. Measured on the cut itself, so it sees the retime as rendered. Frame blending's ghosting is
# not measured — look for it on the strip.
WARP_TEAR_PX = 28      # grey levels a flow-predicted textured pixel may miss by before it counts as torn [assumed]
WARP_TEX = 24.0        # gradient magnitude above which a pixel is texture [assumed]
WARP_K = 3.0           # a pair whose torn share is K × the surrounding footage's median is a spike [assumed]
WARP_MIN = 0.02        # ... and at least 2 % of the textured picture [assumed]
WARP_CUT = 0.5         # torn over half the picture: a picture cut, not a tear [assumed]
WARP_BASE_S = 1.0      # seconds of footage either side of the ramp for the baseline [assumed]
WARP_REPEAT_MAX = 0.25 # share of repeated frames inside the ramp before it is called a stutter [assumed]


def _torn(a, b, np, cv2):
    f = cv2.calcOpticalFlowFarneback(b, a, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    h, w = b.shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    pred = cv2.remap(a, xs + f[..., 0], ys + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    res = cv2.absdiff(b, pred)
    tex = np.hypot(cv2.Sobel(b, cv2.CV_32F, 1, 0), cv2.Sobel(b, cv2.CV_32F, 0, 1)) > WARP_TEX
    m = max(2, int(0.04 * min(h, w)))
    tex[:m] = tex[-m:] = False
    tex[:, :m] = tex[:, -m:] = False
    if tex.sum() < 50:
        return 0.0, res
    return float((res[tex] > WARP_TEAR_PX).mean()), res


def warp_check(cut: str, t0: float, t1: float, job: str, shot: str | None = None) -> dict:
    import shot_graph as SG
    np, cv2 = SG._need()
    info = SG.probe(cut)
    dur = info["duration"]
    if not (0 <= t0 < t1 <= dur + 0.05):
        raise ValueError(f"--at {t0}-{t1}: the ramp must lie inside the cut (0–{dur:.2f} s)")
    fr = SG.decode(cut, max(0.0, t0 - WARP_BASE_S), min(dur, t1 + WARP_BASE_S), info, 320)
    g = [(t, cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)) for t, f in fr]
    rows, worst = [], None
    for (ta, a), (tb, b) in zip(g, g[1:]):
        diff = float(np.mean(cv2.absdiff(a, b)))
        torn, res = _torn(a, b, np, cv2)
        inside = t0 - 1e-3 <= tb <= t1 + 1e-3
        row = {"t": round(tb, 3), "diff": round(diff, 3), "torn": round(torn, 4), "inside": inside,
               "cut": torn > WARP_CUT}
        rows.append(row)
        if inside and not row["cut"] and (worst is None or torn > worst[0]):
            worst = (torn, a, b, res, tb)
    base = sorted(r["torn"] for r in rows if not r["inside"] and not r["cut"])
    base_med = base[len(base) // 2] if base else 0.0
    th = max(WARP_MIN, WARP_K * base_med)
    ins = [r for r in rows if r["inside"] and not r["cut"]]
    spikes = [{"t": r["t"], "torn": r["torn"]} for r in ins if r["torn"] > th]
    rep_share = round(_repeats([r["diff"] for r in ins]) / len(ins), 3) if ins else 0.0
    problems = []
    if not ins:
        problems.append("no frames measured inside the ramp")
    if spikes:
        problems.append(f"the retime tears on {len(spikes)} frame(s) (worst {max(s['torn'] for s in spikes):.1%} of the "
                        f"textured picture at {max(spikes, key=lambda s: s['torn'])['t']:.2f} s, against "
                        f"{base_med:.1%} around the ramp) — shorten or soften the ramp, move it off the hard motion, or "
                        f"retake the shot at that speed")
    if rep_share > WARP_REPEAT_MAX:
        problems.append(f"frames repeat on {rep_share:.0%} of the ramp — it was retimed by frame repeat and stutters: "
                        f"set Retime Process to Optical Flow (Speed Warp on Studio) and render again")
    rep = {"cut": os.path.relpath(cut, job), "cut_sha256": sha256_file(cut), "at": [round(t0, 3), round(t1, 3)],
           "shot": shot, "measured": dt.datetime.now().isoformat(timespec="minutes"),
           "baseline": {"pairs": len(base), "torn_median": round(base_med, 4)}, "threshold": round(th, 4),
           "pairs": len(ins), "spikes": spikes, "repeat_share": rep_share,
           "verdict": "FAIL" if problems else "PASS", "problems": problems, "rows": rows,
           "thresholds_tag": "[assumed] — WARP_* and DUP_TH here; frame blending's ghosting is not measured"}
    out = os.path.join(job, "09-qa", "motion")
    os.makedirs(out, exist_ok=True)
    stem = f"{os.path.splitext(os.path.basename(cut))[0]}.warp-{t0:.2f}"
    json.dump(rep, open(os.path.join(out, stem + ".json"), "w", encoding="utf-8"), indent=1)
    if worst is not None:                     # the worst pair and where it missed, for the director's eye
        _, a, b, res, tb = worst
        heat = cv2.applyColorMap(np.clip(res.astype(np.float32) * 4, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
        strip = np.hstack([cv2.cvtColor(a, cv2.COLOR_GRAY2BGR), cv2.cvtColor(b, cv2.COLOR_GRAY2BGR), heat])
        cv2.imwrite(os.path.join(out, stem + ".png"), strip)
        rep["strip"] = os.path.relpath(os.path.join(out, stem + ".png"), job)
    return rep


def _synth_move(path: str, px: float, repeat: int = 1, tear: tuple = (), fps: int = 24, secs: float = 3.0,
                W: int = 320, H: int = 180) -> None:
    """A static textured wall and a large textured block sliding right `px` pixels per frame. `repeat` shows
    each picture that many times (a frame-repeat retime); frames in `tear` get a smeared patch."""
    import subprocess
    import shot_graph as SG
    np, cv2 = SG._need()
    rng = np.random.default_rng(11)
    bg = cv2.GaussianBlur(rng.integers(40, 220, (H, W)).astype(np.uint8), (3, 3), 0)
    bh, bw = int(H * 0.45), int(W * 0.3)
    blk = cv2.GaussianBlur(rng.integers(0, 255, (bh, bw)).astype(np.uint8), (3, 3), 0)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                          "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "mpeg4", "-q:v", "2", path],
                         stdin=subprocess.PIPE)
    for i in range(int(fps * secs)):
        img = bg.copy()
        x = min(W - bw, int(10 + (i // repeat) * px * repeat))
        y = int(H * 0.3)
        img[y:y + bh, x:x + bw] = blk
        if i in tear:
            y0, y1, x0, x1 = int(H * 0.15), int(H * 0.85), int(W * 0.2), int(W * 0.75)
            half = img[y0:y1, x0:x0 + (x1 - x0) // 2]
            img[y0:y1, x0:x1] = cv2.resize(cv2.flip(half, 0), (x1 - x0, y1 - y0))
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()


def _synth_clip(path: str, fps: int = 24) -> None:
    import action_points as AP
    AP._synth(path, fps)


def _synth_exit(path: str, fps: int = 24) -> None:
    """A textured block that slides steadily right and off the frame (gone by about 2.2 s)."""
    import subprocess
    import shot_graph as SG
    np, _ = SG._need()
    W, H = 160, 90
    rng = np.random.default_rng(5)
    bg = (rng.random((H, W)) * 60 + 80).astype(np.uint8)
    blk = (rng.random((30, 20)) * 120 + 135).astype(np.uint8)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                          "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "mpeg4", "-q:v", "2", path],
                         stdin=subprocess.PIPE)
    for i in range(fps * 3):
        img = bg.copy()
        x = 20 + int(i / fps * 70)
        if x < W:
            img[30:60, x:min(W, x + 20)] = blk[:, :min(20, W - x)]
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()


def _raises(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and cond
    import shot_graph as SG
    check("directions are named from the vector", direction(0.2, 0.0) == "right" and direction(-0.1, 0.2) == "left-down"
          and direction(0.01, 0.0) == "still" and direction(None, None) == "none")
    check("a hand-off that changes screen direction without saying so is caught",
          bool(_join_ok("right, fast", "left", "motion-match", "kept")) and not _join_ok("right", "right", "motion-match", "kept")
          and not _join_ok("right", "left", "flip", "flipped"))
    check("a planned motion hand-off that flips on screen is caught",
          bool(_join_ok("right", "right", "match-on-action", "flipped")))
    plan_l, plan_p = {"camera": "locked", "camera_text": "locked-off"}, {"camera": "push", "camera_text": "slow push in"}
    cam_pan = {"category": "pan", "family": "pan", "direction": "left", "held_pairs": 0, "unsure": False}
    cam_two = {"category": "locked", "family": "locked", "direction": "", "held_pairs": 6, "unsure": False,
               "points_alone": {"category": "zoom-in", "family": "zoom", "direction": "in"}}
    f_plain, f_unsure = camera_finding(plan_l, cam_pan), camera_finding(plan_l, dict(cam_pan, unsure=True, unsure_why="9 of 15 pairs"))
    f_alone = camera_finding({"camera": "pan", "camera_text": "slow pan left"}, cam_two)
    check("a camera mismatch is a finding; a matching one, and drift against a planned lock, are not",
          bool(f_plain) and f_plain.startswith("camera: planned 'locked'") and "UNSURE" not in f_plain
          and "points alone" not in f_plain and camera_finding(plan_l, {"category": "drift", "family": "drift"}) is None
          and camera_finding(plan_l, {"category": "locked", "family": "locked"}) is None, str(f_plain))
    check("an unsure camera reading says so in its finding and sends the reviewer to the clip",
          bool(f_unsure) and f_unsure.startswith("camera:") and "UNSURE" in f_unsure and "9 of 15 pairs" in f_unsure
          and "Look at the clip" in f_unsure, str(f_unsure))
    check("when the reader kept two answers and the plan is neither, the finding gives both",
          bool(f_alone) and f_alone.startswith("camera: planned 'pan'") and "measured 'locked'" in f_alone
          and "points alone read 'zoom-in'" in f_alone and "6 frame pairs" in f_alone, str(f_alone))
    check("when the reader kept two answers, the plan settles which is the camera: no finding for either, and the "
          "camera counts as held only when the plan says so",
          camera_finding(plan_l, cam_two) is None and camera_finding(plan_p, cam_two) is None
          and camera_taken(plan_l, cam_two) == "locked" and camera_taken(plan_p, cam_two) == "push"
          and camera_taken({}, cam_two) == "locked" and camera_taken(plan_l, cam_pan) == "pan")
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("01-script/prompts", "03-clips", "07-edit", "09-qa"):
            os.makedirs(os.path.join(job, d))
        clip = os.path.join(job, "03-clips", "S1_v1.mp4")
        _synth_clip(clip)
        pr = os.path.join(job, "01-script", "prompts", "S1.clip.prompt.md")
        open(pr, "w").write("---\nshot: S1\nkind: clip\ntype: broll\nexit: right\n---\n[MOTION]\nINTENT: x\nSTART: a\n"
                            "MID: b\nEND: c\n\n[CAMERA]\nlocked-off, eye level\n")
        open(os.path.join(job, "01-script", "prompts", "S1.frame.prompt.md"), "w").write(
            "---\nshot: S1\nkind: frame\ntravel: right, across the counter\n---\n[SUBJECT]\nx\n")
        r = report_clip(clip, "S1", job, pr)
        check("the camera reads locked, as planned", (r["camera"].get("family") or "") in ("locked", "drift")
              and not any(f.startswith("camera") for f in r["findings"]), json.dumps(r["camera"]))
        check("the block's action reads as moving right, as `travel:` planned", "right" in r["subject"]["action"]["dir"]
              and not any(f.startswith("travel") for f in r["findings"]), json.dumps(r["subject"]))
        check("the action points are in the report", abs(r["action"]["contact"]["t"] - 2.4) <= 0.1)
        txt = open(pr).read()
        open(pr, "w").write(txt.replace("locked-off", "slow pan left"))
        open(os.path.join(job, "01-script", "prompts", "S1.frame.prompt.md"), "w").write(
            "---\nshot: S1\nkind: frame\ntravel: left\n---\n[SUBJECT]\nx\n")
        r2 = report_clip(clip, "S1", job, pr)
        check("a planned pan and a planned travel left are both reported against the pixels",
              any(f.startswith("camera") for f in r2["findings"]) and any(f.startswith("travel") for f in r2["findings"]),
              json.dumps(r2["findings"]))
        # a named object, boxed on the first frame, followed through the clip
        check("a track spec is read, and a bad one refused",
              parse_track("jar=0.1,0.2,0.3,0.4") == ("jar", (0.1, 0.2, 0.3, 0.4))
              and parse_track("the jar @ 0.1, 0.2, 0.3, 0.4")[0] == "the jar"
              and _raises(lambda: parse_track("jar=1.2,0,0.1,0.1")) and _raises(lambda: parse_track("jar")))
        info = SG.probe(clip)
        tb = summarise_track(track_object(clip, info, (0.125, 0.333, 0.125, 0.333)), 1.0, 3.0)
        check("the boxed block is followed right to where it stops, and never leaves the frame",
              tb.get("dir") == "right" and abs(tb["last"][0] - 0.8125) <= 0.05 and tb["lost_share"] <= 0.1
              and tb["leaves_frame_at"] is None and abs(tb["at_cut"][0] - 0.8125) <= 0.05, json.dumps(tb))
        gone = os.path.join(td, "gone.mp4")
        _synth_exit(gone)
        tg = summarise_track(track_object(gone, SG.probe(gone), (0.125, 0.333, 0.125, 0.333)))
        check("a block that slides off the right edge is seen leaving the frame",
              tg.get("leaves_frame_at") is not None and 1.0 <= tg["leaves_frame_at"] <= 2.6
              and "right" in (tg.get("dir") or ""), json.dumps(tg))
        r3 = report_clip(clip, "S1", job, pr, ["block=0.125,0.333,0.125,0.333"])
        check("the clip report carries the named object", r3["objects"].get("block", {}).get("dir") == "right",
              json.dumps(r3.get("objects")))
        # the lock check: selected shots need a current report, and the cut needs its joins
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "w").write(
            "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n"
            "| t | S1 | selects | SELECT | the throw lands on the rim, heard the knock |\n"
            "| t | S2 | selects | SELECT | the second take holds the look |\n")
        P = check_job(job)
        check("lock: a selected shot with no report, and no joins report, are both named",
              any(p.startswith("S2: no motion report") for p in P) and any("no joins report" in p for p in P), json.dumps(P))
        film = os.path.join(job, "07-edit", "cut_v1.mp4")
        cuts = SG._synth(film)
        cl = os.path.join(job, "07-edit", "cut_v1.cuts.txt"); open(cl, "w").write("\n".join(map(str, cuts)) + "\n")
        # the same object on both sides of a planned motion match: S1 leaves it right, S2 picks it up far
        # left and moving left
        json.dump({"shot": "S2", "objects": {"block": {"at_in": [0.1, 0.5], "first": [0.1, 0.5], "dir": "left"}}},
                  open(os.path.join(job, "09-qa", "motion", "S2.motion.json"), "w"))
        txt = open(pr).read()
        open(pr, "w").write(txt.replace("exit: right\n", "exit: right\njoin: motion-match\n"))
        s1p = os.path.join(job, "09-qa", "motion", "S1.motion.json")
        s1 = json.load(open(s1p)); s1["objects"]["block"]["exit_dir"] = "right"   # as if still moving at the cut
        json.dump(s1, open(s1p, "w"))
        jr = report_cut(film, cl, job, ["S1", "S2", "S3", "S4", "S5"])
        check("the cut's joins are measured", jr["cuts"] == 4, str(jr["cuts"]))
        j1 = jr["joins"][0]
        check("a named object that jumps and reverses across a planned motion match is flagged",
              "block" in j1["objects"] and any("jumps" in f for f in j1["flags"])
              and any("`join: flip`" in f for f in j1["flags"]), json.dumps(j1))
        # HR-13: a planned whip's pan, measured either side of its cut; a warning only against --whip-min
        fast = whip_pan({"cam_before": {"vx": 1.8, "vy": 0.1, "label": "pan right"}, "cam_after": {"vx": 2.1, "vy": 0.0}})
        tilt = whip_pan({"cam_before": {"vx": 0.02, "vy": -1.6}, "cam_after": {"vx": 0.0, "vy": -1.9}})
        half = whip_pan({"t": 3.0, "unmeasured": "too few frames"})
        check("HR-13: a whip's rate is its slower side, in frame-widths/s (frame-heights for a tilt); unmeasured is None",
              fast["pan"] == 1.8 and fast["in"] == 2.1 and fast["out_label"] == "pan right" and tilt["pan"] == 1.6
              and half["pan"] is None and half["out"] is None, json.dumps([fast, tilt, half]))
        check("HR-13: a whip at or over --whip-min passes, one under it is noted, and with no --whip-min or nothing "
              "measured there is no note",
              whip_note(fast, 1.5) is None and "under --whip-min 2" in (whip_note(fast, 2.0) or "")
              and whip_note(fast, None) is None and whip_note(half, 1.5) is None,
              json.dumps([whip_note(fast, 1.5), whip_note(fast, 2.0)]))
        check("HR-13: no planned whip in this cut → no whip rows", jr["whips"] == [] and jr["whip_min"] is None,
              json.dumps(jr["whips"]))
        s4p = os.path.join(job, "01-script", "prompts", "S4.clip.prompt.md")
        open(s4p, "w").write("---\nshot: S4\nkind: clip\ntype: broll\njoin: whip\n---\n[MOTION]\nINTENT: x\n")
        jw = report_cut(film, cl, job, ["S1", "S2", "S3", "S4", "S5"])
        w4 = (jw["whips"] or [{}])[0]
        check("HR-13: S4's `join: whip` is reported — the pan out of S4 (0.15 frame-widths/s), the push-in after it — "
              "and with no --whip-min nothing is a finding",
              len(jw["whips"]) == 1 and w4.get("n") == 4 and w4.get("from") == "S4" and w4.get("to") == "S5"
              and abs((w4.get("out") or 0) - 0.15) <= 0.05 and (w4.get("in") or 0) < 0.05
              and not any("--whip-min" in f for f in jw["findings"]), json.dumps([jw["whips"], jw["findings"]]))
        jw = report_cut(film, cl, job, ["S1", "S2", "S3", "S4", "S5"], whip_min=0.5)
        check("HR-13: --whip-min 0.5 → the whip that pushes in after its cut is a finding naming its rate",
              any("--whip-min" in f and "cut 4 (S4→S5)" in f for f in jw["findings"]) and jw["whip_min"] == 0.5,
              json.dumps(jw["findings"]))
        os.remove(s4p)
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "a").write("| t | S2 | selects | RETAKE | wrong take |\n")
        check("lock: a current report per selected shot and a joins report on the newest cut → nothing missing",
              check_job(job) == [], json.dumps(check_job(job)))
        open(clip, "ab").write(b"\0")
        check("lock: a clip changed after it was measured is stale", any("changed after" in p for p in check_job(job)))
    # D. the transition and ramp budgets at lock (house rule C4, C5)
    check("transition names are read into families",
          [trans_family(n) for n in ("Cross Dissolve", "Dip To Color Dissolve", "Smooth Cut", "Whip Pan", "Cross Zoom",
                                     "Edge Wipe", "Film Burn", "Kaleido")]
          == ["dissolve", "dip", "smooth-cut", "whip", "zoom", "wipe", "light", "kaleido"])
    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, "resolve-inventory.json")
        json.dump({"resolve": "21.1.1", "ofx": ["Sapphire"], "templates": [
            {"kind": "transition", "name": "Light Leak 04", "source": "drfx:Pack.drfx", "path": "Pack.drfx::Edit/Transitions/Light Leak 04.setting"},
            {"kind": "transition", "name": "Whip Pan Left", "source": "user", "path": "Edit/Transitions/Whip Pan Left.setting"},
            {"kind": "title", "name": "Cinematic Title 07", "source": "drfx:Pack.drfx", "path": "x"}]}, open(raw, "w"))
        t1 = tag_inventory(raw, star=["Whip Pan Left"])
        t1d = json.load(open(t1["out"]))
        t1d["templates"][0]["note"] = "warm, 9:16 ok"
        json.dump(t1d, open(t1["out"], "w"))
        t2 = tag_inventory(raw)
        check("inventory: transitions tagged by family, titles the default engine once proven (C7), stars and notes kept on a re-run",
              t2["count"] == {"title": 1, "transition/light": 1, "transition/whip": 1} and t2["starred"] == ["Whip Pan Left"]
              and t2["templates"][0]["note"] == "warm, 9:16 ok" and "C7" in t2["templates"][2]["use"], json.dumps(t2)[:600])
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("00-brief", "01-script/prompts", "07-edit", "09-qa/motion"):
            os.makedirs(os.path.join(job, d))

        def prompt(s, **fm):
            open(os.path.join(job, "01-script", "prompts", f"{s}.clip.prompt.md"), "w").write(
                f"---\nshot: {s}\nkind: clip\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n[MOTION]\nINTENT: x\n")
        for s, ty in (("S1", "broll"), ("S2", "dialogue"), ("S3", "broll"), ("S4", "broll")):
            prompt(s, type=ty)
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "w").write(
            "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n"
            + "".join(f"| t | S{i} | selects | SELECT | kept |\n" for i in range(1, 5)))
        card = {"transitions": {"primary": "hard cut", "accents": ["dissolve"], "max_accents": 2},
                "ramps": {"max_per_video": 2, "per_20s": 1}}
        json.dump(card, open(os.path.join(job, "00-brief", "TITLE-CARD.json"), "w"))
        cl = lambda n, a, b: {"name": n, "type": "Video", "start": a * 24, "duration": (b - a) * 24}
        tr = lambda n, a, b: {"name": n, "type": "Transition", "start": a * 24, "duration": (b - a) * 24}
        V1 = [cl("S1_v1.mp4", 0, 6), cl("S2_v1.mp4", 6, 12), cl("S3_v1.mp4", 12, 18), cl("S4_v1.mp4", 18, 45)]

        def lock(v1, v2=(), c=None):
            json.dump({"fps": 24, "tracks": {"video1": list(v1), "video2": list(v2)}},
                      open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
            if c is not None:
                json.dump(c, open(os.path.join(job, "00-brief", "TITLE-CARD.json"), "w"))
            return plan_checks(job)
        P, W = lock(V1 + [tr("Cross Dissolve", 17.75, 18.25), tr("Dip To Color Dissolve", 44.5, 45)], c=card)
        check("lock: a dissolve between B-roll and the ending's dip pass the budget", P == [], json.dumps(P))
        P, _ = lock(V1 + [tr("Cross Dissolve", 5.75, 6.25)])
        check("lock: a transition into a dialogue clip refuses (its handles)", any("S2" in p and "dialogue" in p for p in P),
              json.dumps(P))
        P, _ = lock(V1 + [tr("Dip To Color Dissolve", 11.75, 12.25)])
        check("lock: a dip mid-film refuses", any("dip mid-film" in p for p in P), json.dumps(P))
        c2 = json.loads(json.dumps(card)); c2["transitions"]["accents"] = ["dissolve", "dip"]
        c2["transitions"]["act_breaks"] = [12.0]
        P, _ = lock(V1 + [tr("Dip To Color Dissolve", 11.75, 12.25)], c=c2)
        check("lock: ... unless the title card names that act break", not any("dip" in p for p in P), json.dumps(P))
        V1b = V1[:3] + [cl("S4_v1.mp4", 18, 30), cl("S3_v2.mp4", 30, 38), cl("S4_v2.mp4", 38, 45)]
        P, _ = lock(V1b + [tr("Cross Dissolve", 17.75, 18.25), tr("Edge Wipe", 29.75, 30.25), tr("Cross Zoom", 37.75, 38.25)])
        check("lock: three kinds of transition refuse, and those off the card's accents are named",
              any("3 kinds" in p for p in P) and any("Edge Wipe" in p and "accents" in p for p in P), json.dumps(P))
        _, W = lock(V1b + [tr("Cross Dissolve", 29.75, 30.25), tr("Cross Dissolve", 37.75, 38.25)])
        check("lock: the same accent on two seams in a row is noted", any("two seams in a row" in w for w in W), json.dumps(W))
        P, _ = lock(V1b + [tr("Whip Pan", 17.75, 18.25), tr("Whip Pan", 29.75, 30.25), tr("Whip Pan", 37.75, 38.25)],
                    c=dict(card, transitions=dict(card["transitions"], accents=["dissolve", "whip"])))
        check("lock: three whips refuse", any("3 whips" in p for p in P), json.dumps(P))
        lock(V1, c=card)
        # ramps: a 45 s film takes two, 20 s apart; a slow-down needs its place in the cut and a passing warp check
        cut = os.path.join(job, "07-edit", "cut_v1.mp4"); open(cut, "wb").write(b"not a film, only bytes to hash")
        prompt("S1", type="broll", ramp="kind=burst, speed=130, trigger=1.2, sfx=whoosh, cut_in=2.0, cut_out=2.6")
        prompt("S4", type="broll", ramp="kind=slow, speed=40, trigger=3.1, reveal=the sugar in the air, sfx=whoosh-down")
        P, _ = lock(V1)
        check("lock: a slow-down with no place in the cut refuses", any("S4" in p and "cut_in" in p for p in P), json.dumps(P))
        prompt("S4", type="broll", ramp="kind=slow, speed=40, trigger=3.1, reveal=the sugar in the air, sfx=whoosh-down, "
                                        "cut_in=30.0, cut_out=31.5")
        P, _ = lock(V1)
        check("lock: a slow-down without a warp check on the newest cut refuses",
              any("S4" in p and "warp" in p for p in P), json.dumps(P))
        wp = os.path.join(job, "09-qa", "motion", "cut_v1.warp-30.00.json")
        json.dump({"cut_sha256": sha256_file(cut), "at": [29.95, 31.5], "verdict": "FAIL", "measured": "1",
                   "problems": ["the retime tears on 3 frame(s)"]}, open(wp, "w"))
        P, _ = lock(V1)
        check("lock: ... or a failed one", any("fails the warp check" in p for p in P), json.dumps(P))
        json.dump({"cut_sha256": sha256_file(cut), "at": [29.95, 31.5], "verdict": "PASS", "measured": "2"}, open(wp, "w"))
        P, _ = lock(V1)
        check("lock: two ramps 28 s apart in a 45 s film, the slow-down cleared → nothing", P == [], json.dumps(P))
        prompt("S3", type="broll", ramp="kind=burst, speed=120, trigger=1, sfx=hit, cut_in=14.0, cut_out=14.4")
        P, _ = lock(V1)
        check("lock: a third ramp refuses, and two closer than 20 s are named",
              any("3 speed ramps" in p for p in P) and any("apart" in p for p in P), json.dumps(P))
        prompt("S3", type="broll")
        P, _ = lock([cl("S1_v1.mp4", 0, 6), cl("S4_v1.mp4", 6, 30)])
        check("lock: two ramps in a 30 s film refuse (one per 20 s)", any("2 speed ramps" in p and "at most 1" in p for p in P),
              json.dumps(P))
        open(cut, "ab").write(b"!")
        P, _ = lock(V1)
        check("lock: a warp check on an older cut does not count", any("no warp check" in p for p in P), json.dumps(P))
        # HR-06, HR-15, HR-17: what the timeline dump says about each clip — notes and info, never a refusal.
        # S4 plans `kind=slow, speed=40` (above); no clip has a motion report yet.

        def dump(v1, a1=(), v2=(), fps=24):
            json.dump({"fps": fps, "tracks": {"video1": list(v1), "video2": list(v2), "audio1": list(a1)}},
                      open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
            return dump_checks(job)
        cx = lambda n, a, b, **k: dict(cl(n, a, b), **k)
        ax = lambda n, a, b, **k: {"name": n, "type": "Audio", "start": a * 24, "duration": (b - a) * 24, **k}
        W, I = dump(V1, [ax("VO_v1.wav", 0, 45)])
        check("HR-06/HR-15/HR-17: a dump without source_fps, sample_rate or opacity notes nothing and says each was not "
              "checked; S4's slow-down has no source fps",
              W == [] and any("`source_fps`" in i for i in I) and any("`sample_rate`" in i for i in I)
              and any("`opacity`" in i for i in I) and any(i.startswith("S4:") and "source" in i for i in I),
              json.dumps([W, I]))
        good = [cx(c["name"], c["start"] / 24, (c["start"] + c["duration"]) / 24, source_fps="24", opacity=100.0)
                for c in V1]
        W, I = dump(good, [ax("VO_v1.wav", 0, 45, sample_rate=48000), ax("bed.wav", 0, 45, sample_rate="48000")])
        check("HR-06/HR-15: every clip at 24 fps and 100 %, all audio at 48 kHz → no note, nothing unchecked",
              not any("fps" in w or "kHz" in w or "opacity" in w for w in W) and not any(i[:1] == "S" and ("rate" in i or "opacity" in i) for i in I),
              json.dumps([W, I]))
        check("HR-17: a 24 fps source slowed to 40 % on a 24 fps timeline is left to the warp check (no floor note)",
              not any(w.startswith("S4: slowed") for w in W), json.dumps(W))
        mixed = [dict(c) for c in good]
        mixed[2]["source_fps"] = "59.94"
        W, _ = dump(mixed, [ax("VO_v1.wav", 0, 45, sample_rate=48000), ax("bed.mp3", 0, 45, sample_rate="44100")])
        check("HR-06: a 59.94 fps clip on a 24 fps timeline and a 44.1 kHz bed beside 48 kHz are named",
              any(("fps" in w or "kHz" in w) and "S3_v1.mp4 59.94 fps" in w for w in W)
              and any(("fps" in w or "kHz" in w) and "bed.mp3 44.1 kHz" in w and "beside 1" in w for w in W), json.dumps(W))
        for fps_, want in (("60", False), ("50", True)):
            src = [dict(c) for c in good]
            src[3]["source_fps"] = fps_
            W, _ = dump(src)
            check(f"HR-17: S4 at 40 % from a {fps_} fps source on 24 fps " + ("is under its 48 % floor" if want
                  else "sits on its 40 % floor (0.4 × 60 = 24) → no note"),
                  any(w.startswith("S4: slowed") for w in W) == want, json.dumps(W))
        json.dump({"shot": "S4", "pace": {"fps": 60.0}}, open(os.path.join(job, "09-qa", "motion", "S4.motion.json"), "w"))
        W, I = dump(V1)
        check("HR-17: with no source_fps in the dump, the clip's motion report gives it (60 fps → on the floor)",
              not any(w.startswith("S4: slowed") for w in W) and not any(i.startswith("S4:") for i in I),
              json.dumps([W, I]))
        json.dump({"shot": "S4", "pace": {"fps": 30.0}}, open(os.path.join(job, "09-qa", "motion", "S4.motion.json"), "w"))
        W, _ = dump(V1)
        check("HR-17: ... and a 30 fps take at 40 % is under its 80 % floor, the source named",
              any(w.startswith("S4: slowed to 40 %, under 80 %") and "its motion report" in w for w in W), json.dumps(W))
        os.remove(os.path.join(job, "09-qa", "motion", "S4.motion.json"))
        op = [dict(c) for c in good]
        op[2]["opacity"] = 50.0
        W, _ = dump(op)
        check("HR-15: S3 at 50 % opacity with no transition or join planned is noted",
              any("opacity" in w and "S3_v1.mp4" in w and "50 %" in w for w in W), json.dumps(W))
        W, _ = dump(op + [tr("Cross Dissolve", 17.75, 18.25)])
        check("HR-15: ... and not under a planned dissolve", not any("opacity" in w for w in W), json.dumps(W))
        lineup = [cx("S4_v2.mp4", 17.5, 18.5, source_fps="24", opacity=50.0)]
        W, _ = dump(good, v2=lineup)
        check("HR-15: a V2 clip at 50 % over the S3→S4 seam, no join planned → noted",
              any("opacity" in w and "S4_v2.mp4" in w for w in W), json.dumps(W))
        prompt("S3", type="broll", join="graphic-match")
        W, _ = dump(good, v2=lineup)
        check("HR-15: ... and not when S3 declares `join:` into it", not any("opacity" in w for w in W), json.dumps(W))
        prompt("S3", type="broll")
        W, I = dump(V1, fps=0)
        check("HR-06/HR-17: a dump with no frame rate says so once and checks no frame rate",
              not any("fps" in w or "floor" in w for w in W) and sum("`fps`" in i for i in I) == 1
              and not any(i.startswith("S4:") for i in I), json.dumps([W, I]))
        os.remove(os.path.join(job, "07-edit", "timeline-dump.json"))
        W, I = dump_checks(job)
        check("HR-06/HR-15/HR-17: no timeline dump → info, no note", W == [] and any("opacity" in i for i in I),
              json.dumps([W, I]))
        lock(V1)
        # the pace: a clip much slower than its model's others is noted, unless its prompt plans the slow-down
        for s, sp, rp in (("S1", 0.18, ""), ("S2", 0.21, ""), ("S3", 0.05, ""), ("S4", 0.19, "")):
            json.dump({"shot": s, "pace": {"speed": sp}, "plan": {"model": "kling-3", "ramp": rp}},
                      open(os.path.join(job, "09-qa", "motion", f"{s}.motion.json"), "w"))
        N = pace_notes(job)
        check("pace: a clip far slower than its model's others is noted", len(N) == 1 and N[0].startswith("S3"), json.dumps(N))
        json.dump({"shot": "S3", "pace": {"speed": 0.05}, "plan": {"model": "kling-3", "ramp": "kind=slow, speed=40"}},
                  open(os.path.join(job, "09-qa", "motion", "S3.motion.json"), "w"))
        check("pace: ... and not when its prompt plans the slow-down", pace_notes(job) == [], json.dumps(pace_notes(job)))
        # the warp check measured: a smooth move passes, a torn frame and a frame-repeat retime fail
        sm, tn, rpt = (os.path.join(td, f) for f in ("smooth.mp4", "torn.mp4", "rep.mp4"))
        _synth_move(sm, 2.5); _synth_move(tn, 2.5, tear=(36, 37, 38)); _synth_move(rpt, 1.25, repeat=2)
        ws = warp_check(sm, 1.0, 2.0, job, "S4")
        wt = warp_check(tn, 1.0, 2.0, job, "S4")
        wr = warp_check(rpt, 1.0, 2.0, job, "S4")
        check("warp: a smooth move passes", ws["verdict"] == "PASS", json.dumps(ws["problems"]))
        check("warp: a torn frame fails, at the frame", wt["verdict"] == "FAIL" and wt["spikes"]
              and abs(wt["spikes"][0]["t"] - 1.5) <= 0.05 and os.path.isfile(os.path.join(job, wt["strip"])),
              json.dumps(wt["spikes"]))
        check("warp: a frame-repeat retime fails as a stutter", wr["verdict"] == "FAIL" and wr["repeat_share"] > 0.3,
              json.dumps(wr["problems"]))
        ps, pr_ = pace(sm, SG.probe(sm)), pace(rpt, SG.probe(rpt))
        check("pace: repeated frames are counted, a smooth clip has none", ps["repeat_share"] == 0 and pr_["repeat_share"] > 0.3,
              json.dumps([ps, pr_]))
    # (v2.48.0, project switches speed-conform and music-led) at lock: off, on, and on but outside what each allows
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("00-brief", "01-script/prompts", "07-edit", "09-qa/motion"):
            os.makedirs(os.path.join(job, d))

        def prompt(s, **fm):
            open(os.path.join(job, "01-script", "prompts", f"{s}.clip.prompt.md"), "w").write(
                f"---\nshot: {s}\nkind: clip\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n[MOTION]\nINTENT: x\n")
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "w").write(
            "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n"
            + "".join(f"| t | S{i} | selects | SELECT | kept |\n" for i in range(1, 5)))
        json.dump({"transitions": {"primary": "hard cut", "accents": [], "max_accents": 2},
                   "ramps": {"max_per_video": 2, "per_20s": 1}}, open(os.path.join(job, "00-brief", "TITLE-CARD.json"), "w"))
        cl = lambda n, a, b, **k: {"name": n, "type": "Video", "start": a * 24, "duration": (b - a) * 24, **k}

        def lock(v1):
            json.dump({"fps": 24, "tracks": {"video1": list(v1)}}, open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
            return plan_checks(job)
        V = [cl("S1_v1.mp4", 0, 6), cl("S2_v1.mp4", 6, 12), cl("S3_v1.mp4", 12, 18), cl("S4_v1.mp4", 18, 45)]
        at = lambda fps: [dict(c, source_fps=fps) if c["name"].startswith("S2") else c for c in V]
        prompt("S1", type="broll", ramp="kind=burst, speed=130, trigger=1.2, sfx=whoosh, cut_in=2.0, cut_out=2.6")
        prompt("S2", type="broll", ramp="conform=60/24")
        prompt("S3", type="broll", join="whip", ramp="ease=90%")
        prompt("S4", type="broll", ramp="kind=burst, speed=125, trigger=song@12.4, sfx=hit, cut_in=30.0, cut_out=30.4")
        cp = os.path.join(job, "00-brief", "CHECKPOINT.md")
        P, W = lock(V)
        check("switches off: a conform and an ease are ramps as before — four in a 45 s film refuse, nothing is lifted",
              any(p.startswith("4 speed ramps") for p in P) and not any("project switch" in w for w in W), json.dumps([P, W]))
        open(cp, "w").write("Job:        sw-1\nSwitches:   speed-conform — the pour is real 60 fps footage, conformed; "
                            "music-led — the song is the client's deliverable\n")
        P, W = lock(V)
        pc = json.load(open(os.path.join(job, "09-qa", "motion", "plan-checks.json")))
        check("speed-conform on: the conform and the ease leave the cap, each named as lifted; music-led on: the song-cued "
              "burst is named as lifted and stays a ramp (two in 45 s, 28 s apart → nothing refuses)",
              P == [] and pc["ramps"] == ["S1", "S4"] and len(pc.get("lifted") or []) == 3
              and any(w.startswith("S2:") and "whole-clip conform at 40 %" in w
                      and "lifted by project switch `speed-conform` (the pour is real" in w for w in W)
              and any(w.startswith("S3:") and "ease inside its whip at 90 %" in w for w in W)
              and any(w.startswith("S4:") and "song at 12.4 s" in w and "lifted by project switch `music-led`" in w for w in W),
              json.dumps([P, W, pc]))
        P, _ = lock([cl("S1_v1.mp4", 0, 6), cl("S4_v1.mp4", 6, 30)])
        check("music-led: the song-cued burst still counts against the cap (two ramps in a 30 s film refuse)",
              any(p.startswith("2 speed ramps") and "at most 1" in p for p in P), json.dumps(P))
        for fm_, needle in ((dict(join="whip", ramp="ease=80%"), "no lower than 85 %"),
                            (dict(ramp="ease=90%"), "no `join: whip`"),
                            (dict(join="whip", ramp="ease=90%, kind=burst, speed=130"), "still a ramp")):
            prompt("S3", type="broll", **fm_)
            P, W = lock(V)
            check(f"speed-conform on, outside what it allows (`ramp: {fm_['ramp']}`"
                  f"{', join: whip' if fm_.get('join') else ', no whip'}): refused, and it stays a ramp (3 in the cap)",
                  any(p.startswith("S3:") and needle in p and "is a ramp" in p for p in P)
                  and any(p.startswith("3 speed ramps") for p in P)
                  and not any(w.startswith("S3:") and "lifted" in w for w in W), json.dumps(P))
        prompt("S3", type="broll", join="whip", ramp="ease=90%")
        prompt("S2", type="broll", ramp="conform=24/60")
        P, _ = lock(V)
        check("speed-conform on: a 'conform' that speeds the whole clip up (24/60) is refused",
              any(p.startswith("S2:") and "under 100 %" in p for p in P), json.dumps(P))
        # HR-17 still holds for a conform: the source fps from the dump, the motion report, or the conform's own
        prompt("S2", type="broll", ramp="conform=60/24")
        lock(V)
        W, I = dump_checks(job)
        check("HR-17 on a conform: no source_fps, so the conform's own 60/24 gives the source — on its 40 % floor, no note",
              not any(w.startswith("S2:") for w in W) and not any(i.startswith("S2:") for i in I), json.dumps([W, I]))
        lock(at("30"))
        W, _ = dump_checks(job)
        check("HR-17 on a conform: a 30 fps source conformed to 40 % is under its 80 % floor; the switch does not lift it",
              any(w.startswith("S2: conformed to 40 % (`conform=`), under 80 %") and "the timeline dump" in w
                  and "does not lift the floor" in w for w in W), json.dumps(W))
        prompt("S2", type="broll", ramp="conform=50%")
        lock(at("24"))
        W, _ = dump_checks(job)
        check("HR-17 on a conform: a 24 fps source conformed to 50 % is under its 100 % floor (no warp check follows it)",
              any(w.startswith("S2: conformed to 50 % (`conform=`), under 100 %") and "no frames to spare" in w for w in W), json.dumps(W))
        lock(V)
        _, I = dump_checks(job)
        check("HR-17 on a conform: 50 % with no source fps anywhere is said as not checked",
              any(i.startswith("S2: the conform to 50 %") for i in I), json.dumps(I))
        for s, sp in (("S1", 0.18), ("S2", 0.05), ("S3", 0.21), ("S4", 0.19)):
            json.dump({"shot": s, "pace": {"speed": sp}, "plan": {"model": "kling-3", "ramp": "conform=50%" if s == "S2" else ""}},
                      open(os.path.join(job, "09-qa", "motion", f"{s}.motion.json"), "w"))
        check("pace: a lifted conform is planned slow motion, not slow motion nobody asked for", pace_notes(job) == [],
              json.dumps(pace_notes(job)))
        os.remove(cp)
        check("pace: ... and with the switch off the same clip is noted, as before",
              len(pace_notes(job)) == 1 and pace_notes(job)[0].startswith("S2"), json.dumps(pace_notes(job)))
        for s in ("S1", "S2", "S3", "S4"):
            os.remove(os.path.join(job, "09-qa", "motion", f"{s}.motion.json"))
        lock(at("24"))
        W, I = dump_checks(job)
        check("switch off: a conform is not floor-checked — a `ramp:` with no kind, as before",
              not any(w.startswith("S2:") for w in W) and not any(i.startswith("S2:") for i in I), json.dumps([W, I]))
    print("-" * 60)
    print("selftest OK — directions named, planned hand-offs checked both ways, a clip's camera, action direction "
          "and action points measured and set against its plan, a named object followed (and seen leaving the frame, "
          "and across a planned match), the lock check (missing report, missing joins, "
          "stale clip, a shot taken out of the cut), the transition budget (families, dialogue handles, a mid-film dip, "
          "accents, runs, whips), the template inventory's tags, the ramp cap and spacing, the warp check (tear, stutter, an older cut), the pace "
          "(repeats, slow motion nobody asked for), a planned whip's measured pan (--whip-min), and from the timeline dump "
          "mixed frame and sample rates, a line-up opacity and the slow-down floor (each skipped with info when the dump "
          "lacks the field), and the project switches (speed-conform: a conform and an ease off the cap, the floor kept; "
          "music-led: a song-cued burst named and still counted)" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("clip"); c.add_argument("clip"); c.add_argument("--shot", required=True)
    c.add_argument("--job", required=True); c.add_argument("--prompt")
    c.add_argument("--track", action="append", default=[],
                   help="name=x,y,w,h — an object boxed on the first frame (fractions, top-left), repeatable")
    k = sub.add_parser("cut"); k.add_argument("cut"); k.add_argument("--cuts", required=True)
    k.add_argument("--shots", help="the shot ids in cut order, comma-separated"); k.add_argument("--job", required=True)
    k.add_argument("--whip-min", type=float, metavar="RATE",
                   help="HR-13: note a planned `join: whip` whose camera moves slower than RATE frame-widths per "
                        "second (frame-heights for a tilt) on either side of its cut. No default: every whip's rate is "
                        "reported, so measure real whips before choosing one")
    h = sub.add_parser("check"); h.add_argument("job")
    w = sub.add_parser("warp", help="the warp check on a slow-down, measured on the cut")
    w.add_argument("cut"); w.add_argument("--at", required=True, help="in-out, seconds in the cut (the ramp's cut_in-cut_out)")
    w.add_argument("--job", required=True); w.add_argument("--shot")
    v = sub.add_parser("inventory", help="tag the installed templates (resolve-production-console.py INVENTORY_TEMPLATES)")
    v.add_argument("raw"); v.add_argument("--out"); v.add_argument("--star", action="append", default=[])
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "clip":
        r = report_clip(a.clip, a.shot, a.job, a.prompt, a.track)
        print(render_clip_md(r)); return 0
    if a.cmd == "cut":
        r = report_cut(a.cut, a.cuts, a.job, [s.strip() for s in (a.shots or "").split(",") if s.strip()] or None,
                       a.whip_min)
        print(f"{r['cut']}: {r['cuts']} joins · {len(r['findings'])} finding(s)")
        for f in r["findings"]:
            print(f"  - {f}")
        for w in r["whips"]:                                               # HR-13
            print(f"  i cut {w['n']} ({w['from']}→{w['to']}) join: whip — " + (
                f"the camera moves {w['pan']:.3f} frame-widths/s on its slower side (out {w['out']}, in {w['in']})"
                if w["pan"] is not None else "the camera was not measured on either side of the cut"))
        return 0
    if a.cmd == "check":
        P = check_job(a.job)
        for p in P:
            print(f"  ✗ {p}")
        dn, di = dump_checks(a.job)                                        # HR-06
        for n in plan_checks(a.job)[1] + dn + pace_notes(a.job):
            print(f"  ! {n}")
        for n in di:
            print(f"  i {n}")
        print(f"  i {cut_plan_note(a.job)}")                                # (3.0.0) PLAN-E-FINAL item 7
        print("motion QA complete for picture lock" if not P else f"{len(P)} thing(s) missing before picture lock")
        return 1 if P else 0
    if a.cmd == "inventory":
        r = tag_inventory(a.raw, a.out, a.star)
        print(f"{r['out']}: " + ", ".join(f"{v} {k}" for k, v in r["count"].items()) + f"; {len(r['ofx'])} OFX; "
              f"starred: {', '.join(r['starred']) or 'none yet'}")
        return 0
    if a.cmd == "warp":
        m = re.match(r"^\s*([\d.]+)\s*[-–:]\s*([\d.]+)\s*$", a.at)
        if not m:
            print("error: --at wants in-out in seconds, e.g. 12.40-13.90", file=sys.stderr); return 2
        r = warp_check(a.cut, float(m.group(1)), float(m.group(2)), a.job, a.shot)
        print(f"{r['cut']} {r['at'][0]:.2f}–{r['at'][1]:.2f} s: {r['verdict']} · {r['pairs']} frames · threshold "
              f"{r['threshold']:.1%} torn (around the ramp {r['baseline']['torn_median']:.1%}) · repeats {r['repeat_share']:.0%}"
              + (f" · strip {r['strip']}" if r.get("strip") else ""))
        for p in r["problems"]:
            print(f"  ✗ {p}")
        return 0 if r["verdict"] == "PASS" else 1
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
