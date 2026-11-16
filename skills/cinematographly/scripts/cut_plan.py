#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""cut_plan.py — where each selected take is cut, from its measured motion and the shot's planned length.
It proposes; it never cuts and never moves a cut for the music. (3.0.0, PLAN-E-FINAL)

  cut_plan.py plan <job> [--shots S1,S2,...] [--fps 24000/1001 | --format PRESET]
  cut_plan.py resolve <job> <shot> trim|regenerate|re-plan --by "Name" --quote "<their words>"
  cut_plan.py check <job>          # the CUTS.json self-check + anything unresolved (exit 1)
  cut_plan.py --selftest

Reads each shot's take report (`09-qa/motion/<shot>.motion.json`, written by `motion_qa.py clip`) and its clip
prompt; writes `07-edit/CUTS.json` and `07-edit/CUTS.md`. `timeline_export.py` builds the Final Cut / Premiere /
Resolve timeline from CUTS.json and refuses while anything is unresolved.

The rules, in order:
  1. IN = the later of the take's own in point (two frames before the motion onset, action_points.py) and the planned
     lead (1.0 s with a start frame, else 0.5 s — the same window motion_qa uses), converted once to project frames.
     OUT = IN + the shot's `cut:` frames. The slack goes after the commit, as tail; a take that ends first moves IN
     earlier, never before the lead.
  2. The action is never split: when IN → the cut point (peak + 5 frames) is longer than `cut:` (one frame over is
     rounding), or the take is too short, the shot is UNRESOLVED with the frame difference and three choices —
     regenerate longer, re-plan the length, trim the action. A recorded choice clears nothing by itself: a
     regenerated take or a new `cut:` is planned afresh from its own numbers; only `trim` (the person's own words,
     checked by the gate's transcript check) sets the window to `cut:` with the trimmed frames recorded.
  3. A talking or reaction shot (`type:` dialogue / reaction / talking_head), or one with no motion onset after the
     lead, holds from the lead for `cut:`, confidence low.
  4. NO TAIL (clip_qa's predicate: under 0.3 s after the peak) is reported; a tail under 6 frames after OUT is a
     finding (no room to trim).
  5. Joins, before any cut exists: the planned left/right clash (motion_qa._join_ok, waived only by `join: flip` or
     `reverse`), and each named `track:` object sampled at the PROPOSED out and in — a jump over motion_qa.OBJ_JUMP on
     a motion/action/graphic/carry join, or exit and enter directions that disagree. Screen direction across the cut
     is still measured on the rough assembly (`motion_qa.py cut`).
  6. (3.2.0) The doctrine at each join, reported, never moved (shot-handoff.md §4b):
       match-on-action  A carries the commit, B the contact: A's OUT minus its commit (cut_point), and B's frames
                        from IN to its contact. No speed test: B's first frames are the stop, and a close-up's screen
                        speed is not a wide's.
       motion-match     B is caught mid-movement: "B starts from rest" when B has its own onset after its lead, or
                        its speed over the 4 frames from IN (total, any direction; a shared `track:` object's when
                        both shots have one) is under shot_graph's subject floor.
     And the light at the proposed frames (A's last, B's first): colour, exposure, warm/cool and key side, each only
     between alike pictures (shot_graph.light_flags). A frame that cannot be read says "not measured".
"""
from __future__ import annotations
import argparse, datetime as dt, glob, json, math, os, re, subprocess, sys, tempfile
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clip_qa  # noqa: E402  (NO TAIL predicate, shared)
import motion_qa as MQ  # noqa: E402

TAIL_MIN_F = 6                 # frames after OUT needed to trim the join at all [assumed]
NO_ACTION_TYPES = {"dialogue", "reaction", "talking_head", "talking-head", "talkinghead"}
CHOICES = ("trim", "regenerate", "re-plan")
VIDEO_EXT = (".mp4", ".mov", ".m4v")
AUDIO_EXT = (".wav", ".m4a", ".mp3", ".aif", ".aiff")
NAMED_RATES = {"23.976": Fraction(24000, 1001), "29.97": Fraction(30000, 1001), "59.94": Fraction(60000, 1001)}


def parse_rate(s) -> Fraction:
    s = str(s).strip()
    if s in NAMED_RATES:
        return NAMED_RATES[s]
    r = Fraction(s)
    if r <= 0:
        raise ValueError(f"not a frame rate: {s}")
    return r


def rate_str(R: Fraction) -> str:
    return f"{R.numerator}/{R.denominator}" if R.denominator != 1 else str(R.numerator)


def to_frame(t: float, R: Fraction) -> int:
    """Seconds → the nearest project frame (the planner's one conversion)."""
    return int(math.floor(Fraction(t).limit_denominator(1_000_000) * R + Fraction(1, 2)))


def frames_floor(t: float, R: Fraction) -> int:
    return int(math.floor(Fraction(t).limit_denominator(1_000_000) * R + Fraction(1, 10_000)))


def job_rate(job: str) -> Fraction | None:
    try:
        cp = open(os.path.join(job, "00-brief", "CHECKPOINT.md"), encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"^Format:\s*([A-Za-z0-9_-]+)", cp, re.M)
    return format_rate(m.group(1)) if m else None


def format_rate(preset: str) -> Fraction | None:
    try:
        d = json.load(open(os.path.join(os.path.dirname(HERE), "assets", "delivery-formats.json"), encoding="utf-8"))
        v = d["formats"][preset].get("fps_default")
        return parse_rate(v) if v else None
    except (OSError, ValueError, KeyError):
        return None


# ---------- one shot ----------

def plan_shot(rep: dict, R: Fraction, resolution: dict | None = None) -> dict:
    plan, act = rep.get("plan") or {}, rep.get("action") or {}
    shot = rep.get("shot")
    dur = float(rep.get("duration") or 0)
    rec = {"shot": shot, "file": rep.get("file"), "sha256": rep.get("sha256"), "asset_frames": frames_floor(dur, R),
           "confidence": "measured", "findings": [], "unresolved": None, "resolution": None}
    try:
        cut_s = float(plan.get("cut"))
    except (TypeError, ValueError):
        cut_s = None
    if not cut_s:
        rec["unresolved"] = {"why": "the clip prompt has no `cut:` length", "frames": None,
                             "choices": ["re-plan"]}
        return rec
    lead_s = float(plan.get("in_t") or 0.5)
    cut_f, lead_f, asset_f = to_frame(cut_s, R), to_frame(lead_s, R), rec["asset_frames"]
    rec["cut_frames"] = cut_f
    t = lambda k: float((act.get(k) or {}).get("t") or 0.0)  # noqa: E731
    onset_t, peak_t = t("onset"), (act.get("peak") or {}).get("t")
    no_action = (str(plan.get("type") or "").lower() in NO_ACTION_TYPES) or onset_t <= lead_s
    span = None
    if no_action:
        IN = lead_f
        rec["confidence"] = "low"
        rec["findings"].append("held from the lead for its planned length: a talking or reaction shot, or no motion "
                               "onset after the lead — check the moment by eye")
    else:
        IN = max(to_frame(t("in_point"), R), lead_f)
        cp = to_frame(t("cut_point"), R)
        span = cp - IN
        if span == cut_f + 1:
            rec["findings"].append("the action is one frame over `cut:` — rounding, treated as fitting")
    OUT = IN + cut_f
    short = 0
    if OUT > asset_f:
        IN = asset_f - cut_f
        OUT = asset_f
        if IN < lead_f:
            short = lead_f - IN
    over = (span - cut_f) if (span is not None and span > cut_f + 1) else 0
    if over or short:
        why = (f"the action runs {over} frame(s) longer than `cut:` ({cut_f} f)" if over else
               f"the take is {short} frame(s) too short to hold `cut:` after the lead")
        un = {"why": why, "frames": over or short, "choices": list(CHOICES) if over else ["regenerate", "re-plan"]}
        res = resolution or {}
        valid_trim = (over and res.get("choice") == "trim" and res.get("sha256") == rec["sha256"]
                      and res.get("cut_frames") == cut_f)
        if valid_trim:
            rec["resolution"] = {k: res.get(k) for k in ("choice", "by", "quote", "at")} | {"trimmed_frames": over}
            rec["findings"].append(f"the action is trimmed by {over} frame(s) — {res.get('by')}'s choice, recorded")
        else:
            if res.get("choice"):
                un["stale_choice"] = (f"{res.get('choice')} was recorded ({res.get('by')}), but the numbers have not "
                                      f"changed: a new take or a new `cut:` is planned afresh")
            rec["unresolved"] = un
        IN = max(IN, 0)
        OUT = min(IN + cut_f, asset_f)
    rec.update({"in": IN, "out": OUT, "used": OUT - IN, "head": IN, "tail": asset_f - OUT})
    if peak_t is not None and clip_qa.no_tail(dur, float(peak_t)):
        rec["findings"].append(f"NO TAIL: under {clip_qa.MIN_TAIL_S} s after the motion peak — generate this beat "
                               f"longer than its on-screen length")
    if rec["tail"] < TAIL_MIN_F:
        rec["findings"].append(f"only {rec['tail']} frame(s) of tail after OUT — no room to trim the join")
    return rec


# ---------- joins ----------

def default_tracker(job: str):
    def track(rep: dict, name: str, in_s: float, out_s: float) -> dict | None:
        obj = (rep.get("objects") or {}).get(name) or {}
        box = obj.get("box")
        clip = os.path.join(job, rep.get("file") or "")
        if not box or not os.path.isfile(clip):
            return None
        try:
            import shot_graph as SG
            info = SG.probe(clip)
            return MQ.summarise_track(MQ.track_object(clip, info, tuple(box)), in_s, out_s)
        except (SystemExit, Exception):            # noqa: BLE001 — no OpenCV, or a file it cannot read
            return None
    return track


SPEED_FRAMES = 4               # (3.2.0) B's speed is read over this many frames from its IN [assumed]


def default_measurer(job: str):
    """(3.2.0) The pixels at one proposed join: the light (A's last frame, B's first) and B's subject speed over
    SPEED_FRAMES from its IN, from a shared named track when there is one. Every failure is said, never swallowed."""
    def measure(ra: dict, a: dict, rb: dict, b: dict, R: Fraction, track=None) -> dict:
        out = {}
        fa, fb = os.path.join(job, ra.get("file") or ""), os.path.join(job, rb.get("file") or "")
        missing = [x for x in (fa, fb) if not os.path.isfile(x)]
        if missing:
            why = "no file " + ", ".join(os.path.relpath(x, job) for x in missing)
            return {"light": {"unmeasured": why}, "b_speed": None, "b_speed_unmeasured": why}
        try:
            import shot_graph as SG
            SG._need()
        except (SystemExit, Exception) as e:                     # noqa: BLE001
            why = f"no OpenCV/numpy ({e})"
            return {"light": {"unmeasured": why}, "b_speed": None, "b_speed_unmeasured": why}
        try:
            ia, ib = SG.probe(fa), SG.probe(fb)
            t_out, t_in = float(a["out"]) / R, float(b["in"]) / R
            wa = SG.decode(fa, max(0.0, t_out - 3.0 / float(R)), t_out, ia)
            wb = SG.decode(fb, t_in, t_in + 1.5 / float(R), ib)
            if not wa or not wb:
                raise ValueError("no frame decoded at " + ("A's OUT" if not wa else "B's IN"))
            fo, fi = wa[-1][1], wb[0][1]
            casc = SG._cascade()
            co, ci = SG.colour_stats(fo), SG.colour_stats(fi)
            lo, li = SG.light_stats(fo, SG.face_pos(fo, casc)), SG.light_stats(fi, SG.face_pos(fi, casc))
            sim = SG.shape_sim(co["_shape"], ci["_shape"])
            out["light"] = {"look_sim": round(sim, 3), "luma_step": round(ci["luma"] - co["luma"], 1),
                            "b_step": (round(li["b_neutral"] - lo["b_neutral"], 1) if li.get("b_neutral") is not None
                                       and lo.get("b_neutral") is not None else None),
                            "key_side": [lo["key_side"], li["key_side"]], "key_on": [lo["key_on"], li["key_on"]],
                            "flags": SG.light_flags(co, ci, lo, li, sim)}
        except (SystemExit, Exception) as e:                     # noqa: BLE001
            out["light"] = {"unmeasured": f"{type(e).__name__}: {e}"}
        try:
            ib = SG.probe(fb)
            t0, t1 = float(b["in"]) / R, float(b["in"] + SPEED_FRAMES) / R
            names = [track] if isinstance(track, str) else list(track or [])
            boxes = [(n, ((rb.get("objects") or {}).get(n) or {}).get("box")) for n in names]
            boxes = [(n, bx) for n, bx in boxes if bx]
            if boxes:
                # each box is drawn on the clip's FIRST frame, so its track starts there; the speed is read from its
                # samples between IN and IN + SPEED_FRAMES; with several shared tracks, the fastest one speaks
                half = 0.5 / float(R)
                best = None
                for n, bx in boxes:
                    tr = MQ.track_object(fb, ib, tuple(bx), 0.0, t1 + 0.5 / float(R))
                    S = [x for x in tr.get("samples", []) if x.get("ok") and t0 - half <= x["t"] <= t1 + half]
                    if len(S) < 2:
                        continue
                    dt_ = max(1e-3, S[-1]["t"] - S[0]["t"])
                    v = round(math.hypot(S[-1]["cx"] - S[0]["cx"], S[-1]["cy"] - S[0]["cy"]) / dt_, 4)
                    if best is None or v > best[1]:
                        best = (n, v)
                if best is None:
                    raise ValueError(f"track(s) {', '.join(repr(n) for n, _ in boxes)} lost over B's first frames")
                out["b_speed"], out["b_speed_how"] = best[1], f"track {best[0]!r}"
            else:
                w = SG.decode(fb, t0, t1 + 0.5 / float(R), ib)
                if len(w) < 2:
                    raise ValueError("fewer than 2 frames decoded from B's IN")
                m = SG.motion(w[0][1], w[-1][1], max(1e-3, w[-1][0] - w[0][0]))
                sj = m.get("subj") or {}
                out["b_speed"] = round(math.hypot(sj.get("vx", 0.0), sj.get("vy", 0.0)), 4) if sj else 0.0
                out["b_speed_how"] = "residual flow"
        except (SystemExit, Exception) as e:                     # noqa: BLE001
            out["b_speed"], out["b_speed_unmeasured"] = None, f"{type(e).__name__}: {e}"
        return out
    return measure


def _subject_floor() -> float:
    try:
        import shot_graph as SG
        return float(SG.TH["subject_v"])
    except Exception:                                            # noqa: BLE001
        return 0.04


def doctrine(ra: dict, a: dict, rb: dict, b: dict, R: Fraction, jn: str, meas: dict | None) -> tuple[dict, list]:
    """(3.2.0) What the join's doctrine asks, against the proposed frames: (numbers, findings). Reports; moves
    nothing. Thresholds for calling a match-on-action distance large wait for real footage."""
    nums, F = {}, []
    if "action" in jn:                                           # match-on-action
        cp = ((ra.get("action") or {}).get("cut_point") or {}).get("t")
        ct = ((rb.get("action") or {}).get("contact") or {}).get("t")
        if cp is not None and "out" in a:
            nums["a_out_minus_commit"] = int(a["out"] - to_frame(float(cp), R))
        if ct is not None and "in" in b:
            nums["b_frames_to_contact"] = int(to_frame(float(ct), R) - b["in"])
        if "a_out_minus_commit" not in nums or "b_frames_to_contact" not in nums:
            F.append("match on action: not measured (" + ", ".join(
                x for x, k in (("A's commit", "a_out_minus_commit"), ("B's contact", "b_frames_to_contact"))
                if k not in nums) + " missing from the take report)")
    elif "motion" in jn:                                         # motion-match
        pb = rb.get("plan") or {}
        onset = float(((rb.get("action") or {}).get("onset") or {}).get("t") or 0.0)
        lead = float(pb.get("in_t") or 0.5)
        typ = str(pb.get("type") or "").lower()
        if typ in NO_ACTION_TYPES:
            nums["b_rest_test"] = "skipped: B is a talking or reaction shot"
        elif onset > lead:
            F.append(f"motion match: B starts from rest — its own motion begins {onset:.2f} s in, after its "
                     f"{lead:g} s lead; generate B already moving (caught mid-movement, shot-handoff.md §4b)")
        elif meas is None:
            F.append("motion match: B's speed not measured (no frames proposed for this join yet, or no measurer)")
        else:
            sp = meas.get("b_speed")
            if sp is None:
                F.append(f"motion match: B's speed not measured ({meas.get('b_speed_unmeasured')})")
            else:
                nums["b_speed"], nums["b_speed_how"] = sp, meas.get("b_speed_how")
                if sp < _subject_floor():
                    F.append(f"motion match: B starts from rest — {sp:.3f} frame-widths/s over its first "
                             f"{SPEED_FRAMES} frames ({meas.get('b_speed_how')}), under {_subject_floor():g}")
    return nums, F


def plan_joins(reps: list, recs: list, R: Fraction, tracker, measurer=None) -> list:
    out = []
    for (ra, a), (rb, b) in zip(zip(reps, recs), zip(reps[1:], recs[1:])):
        pa, pb = ra.get("plan") or {}, rb.get("plan") or {}
        jn = str(pa.get("join") or "").lower()
        row = {"from": a["shot"], "to": b["shot"], "join": jn, "findings": []}
        shared = sorted(set(ra.get("objects") or {}) & set(rb.get("objects") or {}))
        meas = None
        if measurer and not a.get("unresolved") and not b.get("unresolved") and "out" in a and "in" in b:
            meas = measurer(ra, a, rb, b, R, shared or None)
            lt = meas.get("light") or {}
            row["light"] = lt
            if lt.get("unmeasured"):
                row["findings"].append(f"light at the proposed frames: not measured ({lt['unmeasured']})")
            for f in lt.get("flags") or []:
                row["findings"].append(f"light at the proposed frames: {f}")
        elif measurer:
            row["light"] = {"unmeasured": "a side is unresolved: no frames proposed yet"}
        nums, F = doctrine(ra, a, rb, b, R, jn, meas)
        if nums:
            row["doctrine"] = nums
        row["findings"].extend(F)
        why = MQ._join_ok(str(pa.get("exit") or ""), str(pb.get("enter") or ""), jn, "")
        if why:
            row["findings"].append(why)
        names = sorted(set(ra.get("objects") or {}) & set(rb.get("objects") or {}))
        for n in names:
            sa = tracker(ra, n, a.get("in", 0) / R, a.get("out", 0) / R) if "out" in a else None
            sb = tracker(rb, n, b.get("in", 0) / R, b.get("out", 0) / R) if "in" in b else None
            where = "at the proposed frames"
            if not (sa and sb):
                sa, sb = (ra.get("objects") or {}).get(n) or {}, (rb.get("objects") or {}).get(n) or {}
                where = "at the prompt window (could not re-sample: no OpenCV or no file)"
            pout, pin = sa.get("at_cut") or sa.get("last"), sb.get("at_in") or sb.get("first")
            if pout and pin:
                jump = round(((pout[0] - pin[0]) ** 2 + (pout[1] - pin[1]) ** 2) ** 0.5, 3)
                if jump > MQ.OBJ_JUMP and any(k in jn for k in ("motion", "action", "graphic", "carry")):
                    row["findings"].append(f"object {n!r} jumps {jump:.2f} of the frame across the planned {jn} "
                                           f"({where})")
            ea = set(str(sa.get("exit_dir") or "").split("-")) & {"left", "right"}
            eb = set(str(sb.get("dir") or "").split("-")) & {"left", "right"}
            if ea and eb and ea != eb and "flip" not in jn and "reverse" not in jn:
                row["findings"].append(f"object {n!r} leaves moving {'/'.join(ea)} and enters moving {'/'.join(eb)} "
                                       f"— say `join: flip` if meant ({where})")
        out.append(row)
    return out


# ---------- the job ----------

def load_reps(job: str, shots: list | None) -> tuple[list, list]:
    mdir = os.path.join(job, "09-qa", "motion")
    if not shots:
        shots = MQ.selected_shots(job) or sorted(os.path.basename(p)[:-len(".motion.json")]
                                                 for p in glob.glob(os.path.join(mdir, "*.motion.json")))
        import build_fcpxml as BF
        shots = sorted(shots, key=BF.sort_key)
    reps, missing = [], []
    for s in shots:
        p = os.path.join(mdir, f"{s}.motion.json")
        try:
            reps.append(json.load(open(p, encoding="utf-8")))
        except (OSError, ValueError):
            missing.append(s)
    return reps, missing


def resolutions(job: str) -> dict:
    try:
        d = json.load(open(os.path.join(job, "07-edit", "CUTS.resolve.json"), encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def probe_seconds(path: str) -> float | None:
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of",
                            "default=nk=1:nw=1", path], capture_output=True, text=True, timeout=20)
        return float(r.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def voice_for(job: str, shot: str) -> str | None:
    for p in sorted(glob.glob(os.path.join(job, "05-voice", "*"))):
        if p.lower().endswith(AUDIO_EXT) and os.path.basename(p).split("_", 1)[0] == shot:
            return p
    return None


def plan_job(job: str, R: Fraction, shots: list | None = None, tracker=None, measurer=None) -> dict:
    reps, missing = load_reps(job, shots)
    res = resolutions(job)
    recs = [plan_shot(r, R, res.get(r.get("shot"))) for r in reps]
    for s in missing:
        recs.append({"shot": s, "unresolved": {"why": "no take report — run `motion_qa.py clip` on its select",
                                               "frames": None, "choices": []}, "findings": []})
    joins = plan_joins(reps, recs[:len(reps)], R, tracker or default_tracker(job),
                       measurer if measurer is not None else default_measurer(job))
    for r in recs:
        vo = voice_for(job, r["shot"]) if r.get("cut_frames") else None
        if vo:
            secs = probe_seconds(vo)
            if secs is not None:
                d = to_frame(secs, R) - r["cut_frames"]
                r["vo"] = {"file": os.path.relpath(vo, job), "delta_frames": d}
    reb = None
    try:
        rb = json.load(open(os.path.join(job, "07-edit", "music", "REBUILD.json"), encoding="utf-8"))
        reb = {"file": (rb.get("original") or {}).get("file"), "song_start_s": rb.get("start_s"),
               "song_start_frames": to_frame(float(rb.get("start_s") or 0), R), "segments": len(rb.get("segments") or [])}
    except (OSError, ValueError, TypeError):
        pass
    return {"kind": "cuts", "job": os.path.basename(os.path.abspath(job)), "rate": rate_str(R),
            "made": dt.datetime.now().isoformat(timespec="seconds"), "shots": recs, "joins": joins,
            "timeline_frames": sum(r.get("used", 0) for r in recs if not r.get("unresolved")),
            "music": reb}


def self_check(cuts: dict) -> list:
    """Problems with CUTS.json as written: frames inside each asset, used = `cut:`, the sum."""
    probs = []
    for r in cuts.get("shots", []):
        s = r.get("shot")
        if r.get("unresolved"):
            probs.append(f"{s}: unresolved — {r['unresolved']['why']}")
            continue
        if not (0 <= r["in"] < r["out"] <= r["asset_frames"]):
            probs.append(f"{s}: IN {r['in']} / OUT {r['out']} outside the take's {r['asset_frames']} frames")
        if r["used"] != r["out"] - r["in"]:
            probs.append(f"{s}: used {r['used']} ≠ OUT − IN")
        if r["used"] > r.get("cut_frames", r["used"]):
            probs.append(f"{s}: used {r['used']} f is longer than `cut:` ({r.get('cut_frames')} f)")
    tot = sum(r.get("used", 0) for r in cuts.get("shots", []) if not r.get("unresolved"))
    if tot != cuts.get("timeline_frames"):
        probs.append(f"timeline_frames {cuts.get('timeline_frames')} ≠ the shots' sum {tot}")
    return probs


def render_md(c: dict) -> str:
    L = [f"# Cut plan — {c['job']} · {c['rate']} fps · {c['made']}", "",
         "Proposed, not applied. The action is never split; the cut never moves for the music.", "",
         "| Shot | IN | OUT | Used | Head | Tail | Confidence | Notes |", "|---|---|---|---|---|---|---|---|"]
    for r in c["shots"]:
        if r.get("unresolved"):
            u = r["unresolved"]
            note = f"⛔ UNRESOLVED: {u['why']}. Choices: {', '.join(u['choices']) or 'see the note'}"
            if u.get("stale_choice"):
                note += f". {u['stale_choice']}"
            L.append(f"| {r['shot']} | | | | | | | {note} |")
            continue
        notes = list(r.get("findings") or [])
        if r.get("vo"):
            notes.append(f"VO {r['vo']['delta_frames']:+d} f against `cut:`")
        L.append(f"| {r['shot']} | {r['in']} | {r['out']} | {r['used']} | {r['head']} | {r['tail']} | "
                 f"{r['confidence']} | {'; '.join(notes)} |")
    jf = [f"- {j['from']} → {j['to']}: {f}" for j in c["joins"] for f in j["findings"]]
    for j in c["joins"]:
        d = j.get("doctrine") or {}
        parts = ([f"A's OUT is {d['a_out_minus_commit']:+d} f from its commit"] if "a_out_minus_commit" in d else []) + \
                ([f"B reaches its contact {d['b_frames_to_contact']} f after its IN"] if "b_frames_to_contact" in d else [])
        if parts:
            jf.append(f"- {j['from']} → {j['to']} (match on action): " + "; ".join(parts))
    lr = []
    for j in c["joins"]:
        lt = j.get("light")
        if lt is None:
            continue
        if lt.get("unmeasured"):
            lr.append(f"| {j['from']} → {j['to']} | not measured: {lt['unmeasured']} | | | |")
            continue
        bs = "not measured (no neutral or too dark)" if lt.get("b_step") is None else f"{lt['b_step']:+.1f}"
        lr.append(f"| {j['from']} → {j['to']} | {lt.get('look_sim')} | {lt.get('luma_step'):+.1f} | {bs} | "
                  f"{' → '.join(lt.get('key_side') or [])} ({'/'.join(lt.get('key_on') or [])}) |")
    if lr:
        L += ["", "## Light at the proposed frames (3.2.0)", "",
              "Each measured join, flagged or not: palette alike (≥ 0.60 compares), luma step (0–255), warm/cool step "
              "(b* of the near-neutral pixels), key side (measured on).", "",
              "| Join | alike | luma | warm/cool | key side |", "|---|---|---|---|---|", *lr]
    L += ["", "## Joins (planned, before any cut exists)", *(jf or ["- none flagged"]),
          "", "Screen direction across each cut is measured on the rough assembly: `motion_qa.py cut`."]
    if c.get("music"):
        m = c["music"]
        L += ["", "## Music", f"DaVinci Resolve rebuilds the music in Fairlight from `REBUILD.json` ({m['segments']} "
              f"segment(s)). Final Cut Pro / Premiere Pro: place the original `{m['file']}` by hand, the song from "
              f"{m['song_start_s']} s ({m['song_start_frames']} f) at the first frame."]
    return "\n".join(L) + "\n"


def write(job: str, cuts: dict) -> tuple[str, str]:
    d = os.path.join(job, "07-edit"); os.makedirs(d, exist_ok=True)
    pj, pm = os.path.join(d, "CUTS.json"), os.path.join(d, "CUTS.md")
    json.dump(cuts, open(pj, "w", encoding="utf-8"), indent=1)
    open(pm, "w", encoding="utf-8").write(render_md(cuts))
    return pj, pm


def record_resolution(job: str, shot: str, choice: str, by: str, quote: str, rec: dict) -> str | None:
    """Record the person's choice for an unresolved shot. Returns a refusal, or None."""
    if choice not in CHOICES:
        return f"the choice is one of {', '.join(CHOICES)}"
    if not by.strip() or not quote.strip():
        return "--by and --quote (the person's own words) are both required"
    import gate
    v = gate.quote_in_transcript(quote)
    if v != "verified":
        return f"the quote was not found as the person's own words in this conversation ({v})"
    p = os.path.join(job, "07-edit", "CUTS.resolve.json")
    d = resolutions(job)
    d[shot] = {"choice": choice, "by": by, "quote": quote, "at": dt.datetime.now().isoformat(timespec="seconds"),
               "sha256": rec.get("sha256"), "cut_frames": rec.get("cut_frames")}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1)
    return None


# ---------- tests ----------

def _rep(shot, dur=5.0, cut=2.0, start_frame=False, onset=1.2, in_point=None, peak=2.0, cut_point=None,
         typ="", exit_="", enter="", join="", objects=None, sha="aa"):
    lead = 1.0 if start_frame else 0.5
    in_point = in_point if in_point is not None else onset - 2 / 24
    cut_point = cut_point if cut_point is not None else peak + 5 / 24
    return {"shot": shot, "file": f"03-clips/{shot}_v1.mp4", "sha256": sha, "duration": dur,
            "plan": {"cut": cut, "in_t": lead, "out_t": lead + cut, "type": typ, "exit": exit_, "enter": enter,
                     "join": join},
            "action": {"onset": {"t": onset}, "in_point": {"t": in_point}, "peak": {"t": peak},
                       "cut_point": {"t": cut_point}},
            "objects": objects or {}}


def selftest() -> int:
    import tempfile as _tfr
    os.environ.setdefault("CINE_TRANSCRIPT_ROOT", _tfr.gettempdir())   # (3.1) the tests' transcripts live in temp
    R = Fraction(24)
    # 1. fits: IN at the in point, used = cut:, slack becomes tail
    r = plan_shot(_rep("S1", dur=5.0, cut=2.0, onset=1.2, peak=2.4), R)
    assert not r["unresolved"] and r["in"] == to_frame(1.2 - 2 / 24, R) and r["used"] == 48, r
    assert r["tail"] == 120 - r["out"], r
    # IN never before the planned lead (a start frame: 1.0 s)
    r = plan_shot(_rep("S1", start_frame=True, onset=1.2, in_point=0.9, peak=2.0), R)
    assert r["in"] == 24 and r["confidence"] == "measured" and not r["unresolved"], r   # in point 22 f < lead 24 f
    # 2. the action is longer than cut: → unresolved with three choices, never squeezed
    long = _rep("S2", dur=6.0, cut=1.0, onset=1.0, peak=3.0)
    r = plan_shot(long, R)
    assert r["unresolved"] and r["unresolved"]["frames"] > 1 and r["unresolved"]["choices"] == list(CHOICES), r
    # one frame over is rounding
    r = plan_shot(_rep("S3", dur=6.0, cut=1.0, onset=1.0, in_point=1.0, peak=1.0, cut_point=1.0 + 25 / 24), R)
    assert not r["unresolved"] and any("rounding" in f for f in r["findings"]), r
    # a recorded regenerate with the same take clears nothing; a trim on the same numbers does
    regen = {"choice": "regenerate", "by": "Sam Reyes", "sha256": "aa", "cut_frames": 24}
    r = plan_shot(long, R, regen)
    assert r["unresolved"] and "stale_choice" in r["unresolved"], r
    trim = {"choice": "trim", "by": "Sam Reyes", "quote": "trim it", "sha256": "aa", "cut_frames": 24}
    r = plan_shot(long, R, trim)
    assert not r["unresolved"] and r["used"] == 24 and r["resolution"]["trimmed_frames"] > 0, r
    r = plan_shot(dict(long, sha256="bb"), R, trim)
    assert r["unresolved"], "a trim recorded for another take is stale"
    # the take is too short to hold cut: after the lead
    r = plan_shot(_rep("S4", dur=1.2, cut=1.0, start_frame=True, onset=0.3, peak=0.5), R)
    assert r["unresolved"] and "too short" in r["unresolved"]["why"], r
    # 3. a talking shot holds from the lead, low confidence; no onset after the lead does too
    r = plan_shot(_rep("S5", typ="dialogue", onset=2.0, peak=4.0), R)
    assert r["in"] == 12 and r["confidence"] == "low" and not r["unresolved"], r
    r = plan_shot(_rep("S6", onset=0.3, peak=0.4), R)
    assert r["confidence"] == "low", r
    # 4. NO TAIL and a short tail are findings
    r = plan_shot(_rep("S7", dur=2.6, cut=2.0, onset=0.6, peak=2.45, cut_point=2.55), R)
    assert any("NO TAIL" in f for f in r["findings"]) and any("tail after OUT" in f for f in r["findings"]), r
    # rational rate: one conversion, used = cut: in project frames
    R2 = Fraction(24000, 1001)
    r = plan_shot(_rep("S8", dur=5.0, cut=2.0, onset=1.2, peak=2.0), R2)
    assert r["used"] == to_frame(2.0, R2) == 48 and not r["unresolved"], r
    # 5. joins: a planned flip without `flip`; an object jump at the proposed frames
    a = _rep("A", exit_="right", join="motion", objects={"ball": {"box": [0, 0, 1, 1]}})
    b = _rep("B", enter="left", objects={"ball": {"box": [0, 0, 1, 1]}})
    ra, rb = plan_shot(a, R), plan_shot(b, R)
    seen = []

    def fake(rep, name, in_s, out_s):
        seen.append((rep["shot"], round(float(in_s), 3), round(float(out_s), 3)))
        return ({"at_cut": [0.9, 0.5], "exit_dir": "right"} if rep["shot"] == "A" else
                {"at_in": [0.1, 0.5], "dir": "left"})
    j = plan_joins([a, b], [ra, rb], R, fake)[0]
    assert any("disagree on screen direction" in f for f in j["findings"]), j
    assert any("jumps 0.80" in f and "proposed frames" in f for f in j["findings"]), j
    assert any("leaves moving right and enters moving left" in f for f in j["findings"]), j
    assert ("A", round(ra["in"] / 24, 3), round(ra["out"] / 24, 3)) in seen, "sampled at the PROPOSED window"
    a2 = dict(a, plan=dict(a["plan"], join="motion flip"))
    j = plan_joins([a2, b], [ra, rb], R, fake)[0]
    assert not any("disagree" in f or "leaves moving" in f for f in j["findings"]), j
    # no tracker answer → the prompt-window numbers, said so
    j = plan_joins([a, b], [ra, rb], R, lambda *x: None)[0]
    assert not any("jumps" in f for f in j["findings"]), "no samples in the report: nothing measured"
    # 7. (3.2.0) the doctrine at the join, reported, never moved
    A = _rep("A", onset=1.2, peak=2.0, join="match-on-action")
    B = _rep("B", onset=0.3, peak=0.5); B["action"]["contact"] = {"t": 1.0}
    rA, rB = plan_shot(A, R), plan_shot(B, R)
    nums, F = doctrine(A, rA, B, rB, R, "match-on-action", None)
    assert nums["a_out_minus_commit"] == rA["out"] - to_frame(2.0 + 5 / 24, R), nums
    assert nums["b_frames_to_contact"] == to_frame(1.0, R) - rB["in"] and not F, (nums, F)
    assert rA["in"] == plan_shot(A, R)["in"] and rA["out"] == plan_shot(A, R)["out"], "nothing moved"
    nums, F = doctrine(A, rA, _rep("B2", onset=0.3), plan_shot(_rep("B2", onset=0.3), R), R, "match-on-action", None)
    assert any("not measured" in f and "B's contact" in f for f in F), F
    Bm = _rep("B3", onset=1.2)                                     # own onset after the 0.5 s lead
    nums, F = doctrine(A, rA, Bm, plan_shot(Bm, R), R, "motion-match", {"b_speed": 0.5, "b_speed_how": "residual flow"})
    assert any("starts from rest" in f and "after its" in f for f in F), F
    Bk = _rep("B4", onset=0.3)                                     # already moving at the lead
    rBk = plan_shot(Bk, R)
    assert not doctrine(A, rA, Bk, rBk, R, "motion-match", {"b_speed": 0.2, "b_speed_how": "x"})[1]
    F = doctrine(A, rA, Bk, rBk, R, "motion-match", {"b_speed": 0.01, "b_speed_how": "residual flow"})[1]
    assert any("starts from rest" in f and "0.010" in f for f in F), F
    F = doctrine(A, rA, Bk, rBk, R, "motion-match", {"b_speed": None, "b_speed_unmeasured": "no file"})[1]
    assert any("not measured" in f for f in F), F
    assert not any("rest" in f for f in doctrine(A, rA, Bm, plan_shot(Bm, R), R, "match-on-action", None)[1]), \
        "no rest test on a match on action: B carries the stop"
    assert any("not measured" in f for f in doctrine(A, rA, Bk, rBk, R, "motion-match", None)[1]), "silence is a finding"
    Bt = _rep("B5", typ="dialogue", onset=2.0)
    nt, Ft = doctrine(A, rA, Bt, plan_shot(Bt, R), R, "motion-match", {"b_speed": 0.0, "b_speed_how": "x"})
    assert not Ft and "skipped" in nt.get("b_rest_test", ""), (nt, Ft)
    # plan_joins wiring: the light row, a "not measured" light, and an unresolved side
    stub = lambda ra, a, rb, b, R_, tr=None: {"light": {"flags": ["warm/cool step x"]}, "b_speed": 0.2}  # noqa: E731
    jw = plan_joins([A, Bk], [rA, rBk], R, lambda *x: None, stub)[0]
    assert jw["light"]["flags"] and any("light at the proposed frames: warm/cool" in f for f in jw["findings"]), jw
    jn = plan_joins([A, Bk], [rA, rBk], R, lambda *x: None, lambda *x: {"light": {"unmeasured": "no file x"}})[0]
    assert any("not measured (no file x)" in f for f in jn["findings"]), jn
    ju = plan_joins([A, long], [rA, plan_shot(long, R)], R, lambda *x: None, stub)[0]
    assert "unresolved" in ju["light"]["unmeasured"], ju
    md_ = render_md({"job": "x", "rate": "24", "made": "now", "shots": [], "music": None,
                     "joins": [{"from": "A", "to": "B", "findings": [],
                                "doctrine": {"a_out_minus_commit": 3, "b_frames_to_contact": 7}}]})
    assert "A's OUT is +3 f from its commit; B reaches its contact 7 f after its IN" in md_, md_
    md_ = render_md({"job": "x", "rate": "24", "made": "now", "shots": [], "music": None,
                     "joins": [{"from": "A", "to": "B", "findings": [], "doctrine": {"a_out_minus_commit": 3},
                                "light": {"look_sim": 0.8, "luma_step": -2.0, "b_step": 4.0, "key_side": ["left", "left"],
                                          "key_on": ["face", "face"], "flags": []}},
                               {"from": "B", "to": "C", "findings": [], "light": {"unmeasured": "no file x"}}]})
    assert "A's OUT is +3 f from its commit" in md_ and "contact" not in md_.split("match on action")[1].split("\n")[0], md_
    assert "| A → B | 0.8 | -2.0 | +4.0 |" in md_ and "not measured: no file x" in md_, md_
    # the measurer on real pixels: an alike pair shifted cool, B moving or still from its IN; a missing file says so
    try:
        import shot_graph as SG
        np_, cv2_ = SG._need()
    except (SystemExit, Exception):                                # noqa: BLE001
        np_ = None
    if np_ is not None and __import__("shutil").which("ffmpeg"):
        with tempfile.TemporaryDirectory() as td:
            W_, H_, fps_ = 320, 180, 24
            rng = np_.random.default_rng(3)
            wall = cv2_.GaussianBlur(rng.integers(60, 200, (H_, W_, 1)).repeat(3, axis=2).astype(np_.uint8),
                                     (5, 5), 0)                   # a grey (neutral) textured wall

            def clip(name, cast, moving, from_k=0):
                fr = []
                for k in range(fps_ * 3):
                    on = k >= from_k                               # the cast and the motion start at frame from_k
                    bg = (wall.astype(np_.int16) + np_.array(cast if on else (0, 0, 0))).clip(0, 255).astype(np_.uint8)
                    x = 40 + ((k - from_k) * 6 if (moving and on) else 0)
                    cv2_.rectangle(bg, (x, 70), (x + 28, 110), (20, 20, 230), -1)
                    fr.append(bg)
                os.makedirs(os.path.join(td, "03-clips"), exist_ok=True)
                pth = os.path.join(td, "03-clips", f"{name}_v1.mp4")
                pr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s",
                                       f"{W_}x{H_}", "-r", str(fps_), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "mpeg4",
                                       "-q:v", "2", pth], stdin=subprocess.PIPE)
                for f_ in fr:
                    pr.stdin.write(f_.tobytes())
                pr.stdin.close(); pr.wait()
            clip("A", (0, 0, 0), True)
            clip("B", (40, -10, -25), True)                      # BGR: bluer → cooler; the same wall
            clip("C", (0, 0, 0), False)
            clip("D", (40, -10, -25), True, from_k=12)          # still and uncast in its lead, then both from frame 12
            M_ = default_measurer(td)
            ra_ = {"shot": "A", "file": "03-clips/A_v1.mp4", "objects": {}}
            mv = M_(ra_, {"out": 40}, {"shot": "B", "file": "03-clips/B_v1.mp4", "objects": {}}, {"in": 12}, R)
            assert any("warm/cool" in f and "cooler" in f for f in mv["light"].get("flags", [])), mv
            assert mv["b_speed"] is not None and mv["b_speed"] > _subject_floor(), mv
            st = M_(ra_, {"out": 40}, {"shot": "C", "file": "03-clips/C_v1.mp4", "objects": {}}, {"in": 12}, R)
            assert st["b_speed"] is not None and st["b_speed"] < _subject_floor(), st
            assert not any("warm/cool" in f for f in st["light"].get("flags", [])), st
            tk = M_(ra_, {"out": 40}, {"shot": "B", "file": "03-clips/B_v1.mp4",
                                      "objects": {"box": {"box": [0.12, 0.38, 0.1, 0.24]}}}, {"in": 12}, R, "box")
            assert tk.get("b_speed_how") == "track 'box'" and (tk["b_speed"] or 0) > _subject_floor(), tk
            two = M_(ra_, {"out": 40}, {"shot": "B", "file": "03-clips/B_v1.mp4",
                                       "objects": {"box": {"box": [0.12, 0.38, 0.1, 0.24]},
                                                   "wall": {"box": [0.70, 0.10, 0.15, 0.25]}}}, {"in": 12}, R,
                     ["wall", "box"])
            assert two.get("b_speed_how") == "track 'box'", two          # the faster of two shared tracks speaks
            rd_ = {"shot": "D", "file": "03-clips/D_v1.mp4", "objects": {}}
            d_in = M_(ra_, {"out": 40}, rd_, {"in": 13}, R)                # IN on the moving, cast frames
            d_lead = M_(ra_, {"out": 40}, rd_, {"in": 2}, R)               # IN inside the still, uncast lead
            assert any("warm/cool" in f for f in d_in["light"].get("flags", [])) and d_in["b_speed"] > _subject_floor() \
                and not any("warm/cool" in f for f in d_lead["light"].get("flags", [])) \
                and d_lead["b_speed"] < _subject_floor(), (d_in, d_lead)  # the frames read are B's at its IN
            gone = M_(ra_, {"out": 40}, {"shot": "Z", "file": "03-clips/Z_v1.mp4", "objects": {}}, {"in": 12}, R)
            assert "no file" in gone["light"]["unmeasured"] and gone["b_speed"] is None, gone
        print("  (3.2.0) the join measurer ran on synthetic clips: warm/cool flag, B moving and still, a track, a "
              "missing file")
    else:
        print("  (3.2.0) the join measurer's pixel test SKIPPED: no OpenCV/numpy or ffmpeg")
    # 6. the job: CUTS.json written, self-check, the unresolved shot blocks; resolve needs the person's words
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "acme-01001-x")
        md = os.path.join(job, "09-qa", "motion"); os.makedirs(md)
        for rep in (_rep("S1"), long):
            json.dump(rep, open(os.path.join(md, f"{rep['shot']}.motion.json"), "w"))
        assert MQ.cut_plan_note(job).startswith("no cut plan"), "the lock check says when there is no plan"
        c = plan_job(job, R, ["S1", "S2"], tracker=lambda *x: None)
        write(job, c)
        assert "unresolved shots: S2" in MQ.cut_plan_note(job), MQ.cut_plan_note(job)
        probs = self_check(json.load(open(os.path.join(job, "07-edit", "CUTS.json"))))
        assert len(probs) == 1 and "S2: unresolved" in probs[0], probs
        assert "UNRESOLVED" in open(os.path.join(job, "07-edit", "CUTS.md")).read()
        bad = json.loads(json.dumps(c)); bad["shots"][0]["used"] += 1
        assert any("OUT − IN" in p for p in self_check(bad)), "a tampered window fails the self-check"
        os.environ["CINE_HOME"] = os.path.join(td, "home"); os.makedirs(os.environ["CINE_HOME"])
        import gate
        gate.CINE_HOME = os.environ["CINE_HOME"]
        gate.TRANSCRIPT_FILE = os.path.join(gate.CINE_HOME, "transcript-path")
        tp = os.path.join(td, "t.jsonl")
        open(tp, "w").write(json.dumps({"type": "user", "message": {"role": "user", "content": "Trim the action on S2."}}) + "\n")
        open(gate.TRANSCRIPT_FILE, "w").write(tp)
        s2 = c["shots"][1]
        assert "not found" in (record_resolution(job, "S2", "trim", "Sam Reyes", "ship it", s2) or ""), "unquoted words"
        assert record_resolution(job, "S2", "trim", "Sam Reyes", "Trim the action on S2", s2) is None
        c = plan_job(job, R, ["S1", "S2"], tracker=lambda *x: None)
        assert not self_check(c) and c["shots"][1]["resolution"]["by"] == "Sam Reyes", self_check(c)
    print("selftest OK — IN from the take's in point, never before the lead; used = cut: with the slack as tail; an "
          "action longer than cut: is unresolved (one frame over is rounding); a recorded regenerate on the same take "
          "clears nothing, a trim on the same numbers does, a trim for another take is stale; a too-short take, a "
          "talking shot and no onset are handled; NO TAIL and a short tail reported; a rational rate converts once; "
          "joins: a planned flip and an object jump sampled at the proposed frames; (3.2.0) the match-on-action "
          "distances, the motion-match rest test, the light at the proposed frames; CUTS.json self-check; resolve "
          "needs the person's own words")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan"); p.add_argument("job"); p.add_argument("--shots"); p.add_argument("--fps")
    p.add_argument("--format")
    r = sub.add_parser("resolve"); r.add_argument("job"); r.add_argument("shot"); r.add_argument("choice")
    r.add_argument("--by", required=True); r.add_argument("--quote", required=True); r.add_argument("--fps")
    c = sub.add_parser("check"); c.add_argument("job")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    job = os.path.abspath(a.job)
    if a.cmd == "check":
        try:
            cuts = json.load(open(os.path.join(job, "07-edit", "CUTS.json"), encoding="utf-8"))
        except (OSError, ValueError):
            print("no 07-edit/CUTS.json — run `cut_plan.py plan <job>`"); return 1
        probs = self_check(cuts)
        print("\n".join(probs) if probs else "CUTS.json OK — every shot resolved, inside its take, at its planned length")
        return 1 if probs else 0
    R = (parse_rate(a.fps) if getattr(a, "fps", None) else None) or \
        (format_rate(a.format) if getattr(a, "format", None) else None) or job_rate(job)
    if not R:
        print("no frame rate: pass --fps (e.g. 24000/1001) or --format PRESET; the checkpoint's Format had none",
              file=sys.stderr)
        return 2
    shots = [s.strip() for s in a.shots.split(",")] if getattr(a, "shots", None) else None
    cuts = plan_job(job, R, shots)
    if a.cmd == "resolve":
        rec = next((x for x in cuts["shots"] if x.get("shot") == a.shot), None)
        if not rec or not rec.get("unresolved"):
            print(f"{a.shot} has nothing unresolved", file=sys.stderr); return 1
        why = record_resolution(job, a.shot, a.choice, a.by, a.quote, rec)
        if why:
            print(f"REFUSED: {why}", file=sys.stderr); return 1
        cuts = plan_job(job, R, shots)
    pj, pm = write(job, cuts)
    un = [x["shot"] for x in cuts["shots"] if x.get("unresolved")]
    print(f"wrote {pj} and {pm}: {len(cuts['shots'])} shot(s), {cuts['timeline_frames']} f at {cuts['rate']}"
          + (f"; UNRESOLVED: {', '.join(un)} (see CUTS.md)" if un else ""))
    return 1 if un else 0


if __name__ == "__main__":
    sys.exit(main())
