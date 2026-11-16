#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""srt_qa.py — the caption file measured, not checklisted: timing, reading speed, lines.

Until v2.41 the caption QA card (`typography-and-captions.md` §9) was a list a person ticked; no script read the
.srt. The sound-off council (lab-00019, B10, ruling K8) asked for the measurement, with the long-form limits kept as
warnings the producer signs off, because they were written for films and series, not for social ads.

  check <file.srt> [--max-cps 20] [--max-cpl 42] [--max-lines 2] [--s-per-word 0.3] [--pop-min 0.5]
        [--cuts 07-edit/timeline-dump.json | <cut>.cuts.txt [--fps 24]]
        → <file.srt>.qa.json, bound to the file's sha256
        FAIL (refuses export): a file that does not parse · a cue that ends before it starts · cues that overlap ·
             an empty cue · a pop chunk (1–3 words) on screen under 0.5 s — the skill's own floor (§3b, §9)
        WARN [assumed for social]: more than 20 characters a second (Netflix English, adult) · more than 2 lines ·
             a line over 42 characters (Netflix; about 25 at most on 9:16, §9) · a line caption (4+ words) held under
             0.3 s a word (BBC, "around 0.3 seconds per word")
        WARN, advisory (not in the sign-off, never refuses): a cue that starts or ends 1–8 frames off a picture
             cut but not on it — snap it to the cut, so the caption leaves with its shot (§3b). The cuts come from
             --cuts: the timeline dump (resolve-production-console.py DUMP_TIMELINE_JSON: the picture tracks' clip
             edges, at the dump's own fps) or a cut list (seconds, one a line, as motion_qa.py cut takes; --fps gives
             the timeline rate). No --cuts: INFO, not checked
  accept <file.srt> --by <who> --reason "..."    signs off the current warnings (a new edit needs a new sign-off)
  check-job <job>     every 08-captions/*.srt — what soundoff.py check (and so `approve export`) reads
  burned <job> --render 10-export/<file> --plate <captions-off render> [--srt FILE] [--format vertical-1080] [--organic]
        the captions Resolve burned, found in the pixels (house rule C7, 2026-10-27: native by default). An accepted
        render setting is not a burned caption, so this compares the delivery render with the same timeline rendered
        with the captions off (render-mp4.py PICTURE_ONLY) at each cue: something must differ there, inside the
        format's safe box. → <render>.captions.qa.json, bound to both renders and the .srt; `approve export` reads it
        (native.py check)
  --selftest

Characters per second counts every character on screen, spaces and punctuation included, line breaks not.
What it cannot do: read the words (spelling, diacritics, claims) or judge the burn's contrast — those stay on the
card, on the output frame. `burned` sees that something is drawn at each cue and where; not what it says.
Exit codes: 0 clean or signed off · 1 a FAIL or unsigned warnings · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, sys, tempfile

TIME = re.compile(r"^\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")
DEFAULTS = {"max_cps": 20.0, "max_cpl": 42, "max_lines": 2, "s_per_word": 0.3, "pop_min": 0.5}


def _sec(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000.0


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse(text: str) -> tuple:
    """([{n, t0, t1, lines}], [parse errors])"""
    cues, errs = [], []
    blocks = [b for b in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("﻿", "").strip()) if b.strip()]
    for i, b in enumerate(blocks, 1):
        ls = [l for l in b.split("\n")]
        k = next((j for j, l in enumerate(ls) if "-->" in l), None)
        m = TIME.match(ls[k]) if k is not None else None
        if not m:
            errs.append(f"block {i}: no readable timing line")
            continue
        g = m.groups()
        lines = [re.sub(r"<[^>]+>|\{[^}]+\}", "", l).strip() for l in ls[k + 1:]]
        cues.append({"n": i, "t0": _sec(*g[:4]), "t1": _sec(*g[4:]), "lines": [l for l in lines if l]})
    return cues, errs


def measure(text: str, **lim) -> dict:
    L = dict(DEFAULTS, **{k: v for k, v in lim.items() if v is not None})
    cues, errs = parse(text)
    fails, warns = list(errs), []
    prev = None
    for c in cues:
        dur = c["t1"] - c["t0"]
        txt = " ".join(c["lines"])
        nwords = len(txt.split())
        at = f"#{c['n']} {int(c['t0'] // 60)}:{c['t0'] % 60:05.2f}"
        if not txt:
            fails.append(f"{at}: an empty cue")
            continue
        if dur <= 0:
            fails.append(f"{at}: ends before it starts")
            continue
        if prev and c["t0"] < prev["t1"] - 0.001:
            fails.append(f"{at}: starts {prev['t1'] - c['t0']:.2f} s before cue #{prev['n']} ends — two captions at once")
        prev = c
        if nwords <= 3 and dur < L["pop_min"]:
            fails.append(f"{at}: a {nwords}-word chunk on screen {dur:.2f} s — under the {L['pop_min']:g} s floor")
        chars = len("".join(c["lines"])) + max(0, len(c["lines"]) - 1)
        cps = chars / dur
        if cps > L["max_cps"]:
            warns.append(f"{at}: {cps:.1f} characters a second (> {L['max_cps']:g}, Netflix adult) [assumed for social]")
        if len(c["lines"]) > L["max_lines"]:
            warns.append(f"{at}: {len(c['lines'])} lines (> {L['max_lines']})")
        for l in c["lines"]:
            if len(l) > L["max_cpl"]:
                warns.append(f"{at}: a {len(l)}-character line (> {L['max_cpl']}; about 25 at most on 9:16)")
        if nwords >= 4 and dur / nwords < L["s_per_word"]:
            warns.append(f"{at}: {dur / nwords:.2f} s a word (< {L['s_per_word']:g}, BBC) [assumed for social]")
    return {"cues": len(cues), "fails": fails, "warnings": warns, "limits": L}


# HR-20 — a caption leaves with the shot it sits on (typography-and-captions.md §3b): a cue edge a few frames off a
# picture cut flashes over the next shot or leaves early. The course notes give no tolerance, so the window is chosen.
CUT_SNAP_FRAMES = (1, 8)   # [assumed] house choice, 2026-11-03
NOT_PICTURE = re.compile(r"(?i)title|caption|subtitle|\bsubs?\b|\bcc\b|graphic|disclosure|super|\btext")


def load_cuts(path: str, fps: float | None = None) -> tuple:
    """(picture-cut times in seconds, the timeline fps or None, what they came from). A `.json` is the timeline dump
    (resolve-production-console.py DUMP_TIMELINE_JSON): every clip edge on a picture track — title, caption, graphics,
    disclosure and supers tracks and transitions are not cuts — at the dump's own fps. Anything else is a cut list, as
    motion_qa.py cut and mix_qa.py take it: one time in seconds a line, `#` comments; its fps is `fps`."""
    if path.lower().endswith(".json"):
        d = json.load(open(path, encoding="utf-8"))
        rate = float(d.get("fps") or 0) or fps
        if not rate:
            return [], None, "timeline dump"
        names, spans = d.get("track_names") or {}, []
        for tn, items in (d.get("tracks") or {}).items():
            if not str(tn).startswith("video") or NOT_PICTURE.search(str(names.get(tn) or "")):
                continue
            clips = [it for it in items or [] if "transition" not in str(it.get("type") or "").lower()]
            if clips and all(it.get("text") for it in clips):
                continue                                   # a track of Text+ titles (the dump carries their words)
            for it in clips:
                s = it.get("start_s") if it.get("start_s") is not None else (it.get("start") or 0) / rate
                du = it.get("duration_s") if it.get("duration_s") is not None else (it.get("duration") or 0) / rate
                spans.append((float(s), float(s) + float(du)))
        end = max((b for _, b in spans), default=0.0)
        edges = sorted({round(t, 4) for sp in spans for t in sp if 0.5 / rate < t < end - 0.5 / rate})
        kind = "timeline dump"
    else:
        rate, kind, edges = fps, "cut list", []
        for ln in open(path, encoding="utf-8"):
            m = re.match(r"\s*([\d.]+)", ln.split("#", 1)[0])
            if m:
                edges.append(float(m.group(1)))
        edges = sorted(t for t in set(edges) if t > 0)
    cuts = []
    for t in edges:                                        # edges within half a frame are one cut
        if not cuts or not rate or (t - cuts[-1]) * rate >= 0.5:
            cuts.append(t)
    return cuts, rate, kind


def cut_snaps(cues: list, cuts: list, fps: float) -> list:
    """A cue edge CUT_SNAP_FRAMES off its nearest picture cut, and not on it."""
    lo, hi = CUT_SNAP_FRAMES
    out = []
    for c in cues:
        if c["t1"] <= c["t0"]:
            continue
        at = f"#{c['n']} {int(c['t0'] // 60)}:{c['t0'] % 60:05.2f}"
        for edge, t in (("starts", c["t0"]), ("ends", c["t1"])):
            near = min(cuts, key=lambda x: abs(x - t), default=None)
            if near is None:
                continue
            n = round(abs(t - near) * fps)
            if lo <= n <= hi:
                out.append(f"{at}: {edge} {n} frame{'' if n == 1 else 's'} {'before' if t < near else 'after'} the "
                           f"picture cut at {int(near // 60)}:{near % 60:05.2f} — snap it to the cut, so the caption "
                           f"leaves with its shot (window {lo}–{hi} frames [assumed])")
    return out


def report_path(srt: str) -> str:
    return srt + ".qa.json"


def write_report(srt: str, cuts: str | None = None, fps: float | None = None, **lim) -> dict:
    text = open(srt, encoding="utf-8", errors="replace").read()
    m = measure(text, **lim)
    old = {}
    try:
        old = json.load(open(report_path(srt), encoding="utf-8"))
    except (OSError, ValueError):
        pass
    # HR-20: kept out of `warnings` — advisory, so it never enters the sign-off or the exit code
    snap, info, cut_check = [], [], None
    if not cuts:
        info.append("no --cuts: the cue edges were not checked against the picture cuts — --cuts "
                    "07-edit/timeline-dump.json, or a cut list with --fps")
    else:
        try:
            times, rate, kind = load_cuts(cuts, fps)
        except (OSError, ValueError) as e:
            times, rate, kind = [], None, f"unreadable ({e})"
        if not rate:
            info.append(f"{os.path.basename(cuts)} ({kind}): no timeline frame rate — the cue edges were not checked "
                        f"against the picture cuts; pass --fps, or --cuts the timeline dump")
        elif not times:
            info.append(f"{os.path.basename(cuts)} ({kind}): no picture cuts in it — nothing to snap to")
        else:
            snap = cut_snaps(parse(text)[0], times, rate)
            cut_check = {"source": os.path.basename(cuts), "kind": kind, "cuts": len(times), "fps": rate,
                         "window_frames": list(CUT_SNAP_FRAMES)}
    r = dict(m, srt=os.path.basename(srt), srt_sha256=sha256_file(srt), measured=dt.datetime.now().isoformat(timespec="seconds"),
             accepted=old.get("accepted") if (old.get("accepted") or {}).get("srt_sha256") == sha256_file(srt) else None,
             cut_snap=snap, cut_check=cut_check, info=info)
    json.dump(r, open(report_path(srt), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return r


def accept(srt: str, by: str, reason: str) -> dict:
    p = report_path(srt)
    try:
        r = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        raise SystemExit(f"error: no report — srt_qa.py check {srt} first")
    if r.get("srt_sha256") != sha256_file(srt):
        raise SystemExit("error: the .srt changed after it was measured — check it again, then accept")
    if r.get("fails"):
        raise SystemExit("REFUSED: a FAIL is not signed off — fix the timing (" + r["fails"][0] + ")")
    if len((reason or "").split()) < 3 or not (by or "").strip():
        raise SystemExit("error: --by <who> and --reason in a sentence (why these warnings are right for this film)")
    r["accepted"] = {"by": by.strip(), "reason": reason.strip(), "warnings": len(r.get("warnings") or []),
                     "srt_sha256": r["srt_sha256"], "at": dt.datetime.now().isoformat(timespec="seconds")}
    json.dump(r, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return r


def check_job(job: str) -> tuple:
    """(problems, notes) — a missing or stale report, a FAIL, or warnings nobody signed off refuse."""
    P, W = [], []
    srts = sorted(glob.glob(os.path.join(job, "08-captions", "*.srt")))
    if not srts:
        W.append("no captions in 08-captions/ — the muted feed (T1) is the picture and the titles alone")
    for s in srts:
        relp = os.path.relpath(s, job)
        try:
            r = json.load(open(report_path(s), encoding="utf-8"))
        except (OSError, ValueError):
            P.append(f"{relp}: the caption timing was not measured — python3 scripts/srt_qa.py check {relp}")
            continue
        if r.get("srt_sha256") != sha256_file(s):
            P.append(f"{relp}: changed after its timing was measured — srt_qa.py check again")
            continue
        for f in r.get("fails") or []:
            P.append(f"{relp}: {f}")
        n = len(r.get("warnings") or [])
        a = r.get("accepted") or {}
        if n and not (a.get("srt_sha256") == r["srt_sha256"] and a.get("warnings") == n):
            P.append(f"{relp}: {n} caption warning(s) not signed off — srt_qa.py accept {relp} --by <who> --reason \"…\"")
        elif n:
            W.append(f"{relp}: {n} caption warning(s), signed off by {a.get('by')}: {a.get('reason')}")
        if r.get("cut_snap"):                                                       # HR-20, advisory
            lo, hi = CUT_SNAP_FRAMES
            W.append(f"{relp}: {len(r['cut_snap'])} cue edge(s) {lo}–{hi} frames off a picture cut — snap them to the "
                     f"cut (advisory)")
    return P, W


BURN_MIN_INK = 0.0005    # share of the frame that must differ at a cue for it to count as burned [assumed]


def measure_burned(job: str, render: str, plate: str, srt: str, fmt_name: str = "vertical-1080", organic: bool = False) -> dict:
    """The captions in the pixels: at each cue the delivery render differs from the captions-off render, inside the
    safe box; between cues it does not (a note only)."""
    import native
    import title_qa as TQ
    rel = lambda p: os.path.relpath(p, job) if os.path.abspath(p).startswith(os.path.abspath(job) + os.sep) else p
    probs = native.same_shape(render, plate)
    info = TQ.probe(render)
    W, H = info["w"] or 1080, info["h"] or 1920
    fps = info["fps"] or 24.0
    aw = TQ.ANALYSE_W
    ah = int(round(aw * H / W))
    sx = W / aw
    fmts = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets",
                                       "delivery-formats.json"), encoding="utf-8"))["formats"]
    box = fmts[fmt_name]["safe_zone_organic_pct" if organic and fmts[fmt_name].get("safe_zone_organic_pct") else "safe_zone_pct"]
    safe = [W * box["left"] / 100, H * box["top"] / 100, W * (1 - box["right"] / 100), H * (1 - box["bottom"] / 100)]
    cues, errs = parse(open(srt, encoding="utf-8-sig").read())
    probs += [f"{srt}: {e}" for e in errs]
    out, gaps = [], []

    def ink_at(t):
        _, _, M = native.diff_frames(render, plate, t, 1, fps, aw, ah)
        return None if M is None or not len(M) else M[0]
    for c in cues:
        best = None
        for frac in (0.5, 0.3, 0.7):
            t = c["t0"] + (c["t1"] - c["t0"]) * frac
            m = ink_at(t)
            if m is None:
                continue
            ink = float(m.mean())
            if best is None or ink > best[1]:
                best = (t, ink, m)
            if ink >= BURN_MIN_INK:
                break
        row = {"n": c["n"], "t": round(c["t0"] + (c["t1"] - c["t0"]) / 2, 3), "text": " / ".join(c["lines"])[:60]}
        if best is None:
            row.update(status="FAIL", note="no frame could be read at this time (is the render shorter than the .srt?)")
        elif best[1] < BURN_MIN_INK:
            row.update(t=round(best[0], 3), ink=round(best[1], 5), status="FAIL", note="no caption in the pixels")
        else:
            b = TQ.bbox(best[2])
            u = [b[0] * sx, b[1] * sx, b[2] * sx, b[3] * sx]
            off = max(safe[0] - u[0], safe[1] - u[1], u[2] - safe[2], u[3] - safe[3], 0)
            row.update(t=round(best[0], 3), ink=round(best[1], 5), box=[round(x) for x in u],
                       status="PASS" if off <= 2 else "FAIL",
                       note="" if off <= 2 else f"drawn {off:.0f} px outside the {'organic' if organic else 'paid'} safe box "
                                                f"{[round(x) for x in safe]}")
        out.append(row)
    for a, b in zip(cues, cues[1:]):
        if b["t0"] - a["t1"] >= 0.5:
            t = (a["t1"] + b["t0"]) / 2
            m = ink_at(t)
            if m is not None and float(m.mean()) >= BURN_MIN_INK:
                gaps.append({"t": round(t, 3), "note": "something differs between cues — a caption held past its out time, "
                                                      "or a disclosure line on the caption track (fine)"})
    none_in = out and all(r["status"] == "FAIL" and r["note"] == "no caption in the pixels" for r in out)
    note = ("nothing of the captions is in the pixels: the burn did not happen — Deliver ▸ Advanced Settings ▸ Subtitles "
            "▸ Burn into video, or render-mp4.py BURN_SUBTITLES = True, then render again" if none_in else "")
    verdict = "FAIL" if probs or any(r["status"] == "FAIL" for r in out) or not out else "PASS"
    return {"render": rel(render), "render_sha256": sha256_file(render), "plate": rel(plate), "plate_sha256": sha256_file(plate),
            "srt": rel(srt), "srt_sha256": sha256_file(srt), "format": fmt_name, "organic": organic, "verdict": verdict,
            "cues": out, "gaps": gaps, "problems": probs, "note": note,
            "thresholds": f"BURN_MIN_INK {BURN_MIN_INK}, native.DIFF_THR {native.DIFF_THR} [assumed]",
            "at": dt.datetime.now().isoformat(timespec="seconds")}


def selftest() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  → {detail}"))

    good = ("1\n00:00:00,000 --> 00:00:02,400\nEvery loaf here is shaped\nbefore six.\n\n"
            "2\n00:00:02,500 --> 00:00:03,100\nFresh bread.\n")
    m = measure(good)
    check("a clean file: no FAIL, no warning", m["cues"] == 2 and not m["fails"] and not m["warnings"], m)
    m = measure("1\n00:00:01,000 --> 00:00:00,900\nBackwards.\n\n2\n00:00:02,000 --> 00:00:02,300\nToo fast\n\n"
                "3\n00:00:02,200 --> 00:00:04,000\nThis cue starts before the last one ends\n")
    check("ends-before-start, a 2-word chunk under 0.5 s and an overlap all FAIL",
          len(m["fails"]) == 3 and any("ends before" in f for f in m["fails"]) and any("floor" in f for f in m["fails"])
          and any("two captions at once" in f for f in m["fails"]), m["fails"])
    m = measure("1\n00:00:00,000 --> 00:00:01,000\nThirty percent off your first box of bread this week\n")
    check("too many characters a second, too long a line and under 0.3 s a word are warnings, not FAILs",
          not m["fails"] and any("characters a second" in w for w in m["warnings"]) and any("s a word" in w for w in m["warnings"])
          and any("character line" in w for w in m["warnings"]), m)
    check("a timing line nobody can read is a FAIL", measure("1\n0:01 - 0:02\nhi\n")["fails"])
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "08-captions"))
        s = os.path.join(td, "08-captions", "x.srt")
        open(s, "w").write("1\n00:00:00,000 --> 00:00:01,000\nThirty percent off your first box of bread this week\n")
        P, _ = check_job(td)
        check("check-job: an unmeasured .srt refuses", P and "not measured" in P[0], P)
        write_report(s)
        P, _ = check_job(td)
        check("check-job: warnings nobody signed off refuse", P and "not signed off" in P[0], P)
        accept(s, "Dana", "fast pop read is the client's house style")
        P, W = check_job(td)
        check("check-job: signed off → a note naming who", not P and "signed off by Dana" in W[0], (P, W))
        open(s, "a").write("\n")
        P, _ = check_job(td)
        check("check-job: an edit after the sign-off is stale", P and "changed after" in P[0], P)
        write_report(s)
        P, _ = check_job(td)
        check("…and a re-measure drops the old sign-off", P and "not signed off" in P[0], P)
    # HR-20: cue edges against the picture cuts, from the timeline dump or a cut list
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "08-captions"))
        os.makedirs(os.path.join(td, "07-edit"))
        dump = os.path.join(td, "07-edit", "timeline-dump.json")
        json.dump({"fps": 24, "track_names": {"video1": "Picture", "video2": "B-roll", "video3": "Titles"}, "tracks": {
            "video1": [{"name": "S1_v1.mp4", "type": "video", "start": 0, "duration": 60},
                       {"name": "Cross Dissolve", "type": "transition", "start": 54, "duration": 12},
                       {"name": "S2_v1.mp4", "type": "video", "start": 60, "duration": 84}],
            "video2": [{"name": "B1_v1.mp4", "type": "video", "start": 96, "duration": 24}],
            "video3": [{"name": "Text+", "type": "video", "start": 40, "duration": 30, "text": "Fresh"}],
            "audio1": [{"name": "VO_v1.wav", "type": "audio", "start": 0, "duration": 130}]}}, open(dump, "w"))
        cl = os.path.join(td, "07-edit", "cut_v1.cuts.txt")
        open(cl, "w").write("2.5   # S1 -> S2\n4.0\n\n5.0\n")
        times, rate, _ = load_cuts(dump)
        check("HR-20: the dump's cuts are the picture tracks' clip edges — a title track, a transition, the audio, the "
              "first frame and the end are not cuts", times == [2.5, 4.0, 5.0] and rate == 24.0, (times, rate))
        s = os.path.join(td, "08-captions", "x.srt")
        open(s, "w").write("1\n00:00:00,000 --> 00:00:02,500\nEvery loaf here is shaped\n\n"
                           "2\n00:00:02,500 --> 00:00:04,000\nbefore six.\n\n3\n00:00:04,000 --> 00:00:04,600\nFresh loaf.\n")
        r = write_report(s, cuts=dump)
        check("HR-20: cue edges on the cuts → no cut warning", r["cut_snap"] == [] and r["cut_check"]["cuts"] == 3
              and not r["info"] and not r["warnings"], r)
        open(s, "w").write("1\n00:00:00,000 --> 00:00:02,417\nEvery loaf here is shaped\n\n"
                           "2\n00:00:02,625 --> 00:00:03,900\nbefore six.\n\n3\n00:00:04,000 --> 00:00:04,600\nFresh loaf.\n")
        r = write_report(s, cuts=dump)
        check("HR-20: an end 2 frames before a cut, a start 3 frames after one, and an end 2 frames before a B-roll "
              "edge warn; 10 frames off is not a near miss",
              len(r["cut_snap"]) == 3 and "#1" in r["cut_snap"][0] and "ends 2 frames before" in r["cut_snap"][0]
              and "starts 3 frames after" in r["cut_snap"][1] and "0:04.00" in r["cut_snap"][2], r["cut_snap"])
        P, W = check_job(td)
        check("HR-20: advisory — not a warning to sign off, no refusal, a note in check-job",
              r["warnings"] == [] and not r["fails"] and P == [] and any("picture cut" in w for w in W), (r["warnings"], P, W))
        r = write_report(s, cuts=cl, fps=24)
        check("HR-20: a cut list (seconds, `#` comments) with --fps finds the same three", len(r["cut_snap"]) == 3,
              r["cut_snap"])
        r = write_report(s, cuts=cl)
        check("HR-20: a cut list without --fps is skipped with INFO, not guessed at 24",
              r["cut_snap"] == [] and any("no timeline frame rate" in x for x in r["info"]), r["info"])
        r = write_report(s)
        check("HR-20: no --cuts → INFO, not checked", r["cut_snap"] == [] and any("no --cuts" in x for x in r["info"]),
              r["info"])
    print("-" * 60)
    print("selftest OK — timing FAILs refuse; the long-form limits warn until signed off; a sign-off is bound to the "
          "file's bytes; a cue edge 1–8 frames off a picture cut warns, advisory (from the dump or a cut list)"
          if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["check", "accept", "check-job", "burned"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--max-cps", type=float)
    ap.add_argument("--max-cpl", type=int)
    ap.add_argument("--max-lines", type=int)
    ap.add_argument("--s-per-word", type=float)
    ap.add_argument("--pop-min", type=float)
    ap.add_argument("--cuts", help="check: the picture cuts — 07-edit/timeline-dump.json, or a cut list (seconds, one a "
                                   "line); a cue edge 1–8 frames off a cut warns, advisory")
    ap.add_argument("--fps", type=float, help="check: the timeline frame rate for a --cuts cut list (a dump carries its own)")
    ap.add_argument("--by", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--render", help="burned: the delivery render")
    ap.add_argument("--plate", help="burned: the same timeline rendered with the captions off (render-mp4.py PICTURE_ONLY)")
    ap.add_argument("--srt", help="burned: the .srt (default: the job's only one)")
    ap.add_argument("--format", default="vertical-1080")
    ap.add_argument("--organic", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd or not a.path:
        ap.print_help()
        return 2
    if a.cmd == "burned":
        job = a.path
        srt = a.srt or (lambda L: L[0] if len(L) == 1 else None)(sorted(glob.glob(os.path.join(job, "08-captions", "*.srt"))))
        if not (a.render and a.plate and srt):
            print("error: burned <job> --render <file> --plate <captions-off render> [--srt FILE] (several .srt: name one)",
                  file=sys.stderr)
            return 2
        r = measure_burned(job, a.render, a.plate, srt, a.format, a.organic)
        json.dump(r, open(a.render + ".captions.qa.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        for c in r["cues"]:
            print(f"  {c['status']:4}  cue {c['n']:>3} at {c['t']:6.2f} s  {c.get('note') or ''}")
        for g in r["gaps"]:
            print(f"  note  {g['t']:6.2f} s  {g['note']}")
        for p_ in r["problems"]:
            print(f"  FAIL  {p_}")
        if r["note"]:
            print(f"  {r['note']}")
        print(f"{r['verdict']} — {a.render}.captions.qa.json")
        return 0 if r["verdict"] == "PASS" else 1
    if a.cmd == "check-job":
        P, W = check_job(a.path)
        for w in W:
            print(f"  note: {w}")
        for p in P:
            print(f"  ✗ {p}")
        return 1 if P else 0
    if not os.path.isfile(a.path):
        print(f"error: no such file: {a.path}", file=sys.stderr)
        return 2
    if a.cmd == "accept":
        r = accept(a.path, a.by, a.reason)
        print(f"signed off: {r['accepted']['warnings']} warning(s) by {r['accepted']['by']}")
        return 0
    if a.cuts and not os.path.isfile(a.cuts):
        print(f"error: no such file: {a.cuts}", file=sys.stderr)
        return 2
    r = write_report(a.path, cuts=a.cuts, fps=a.fps, max_cps=a.max_cps, max_cpl=a.max_cpl, max_lines=a.max_lines,
                     s_per_word=a.s_per_word, pop_min=a.pop_min)
    for f in r["fails"]:
        print(f"  FAIL {f}")
    for w in r["warnings"]:
        print(f"  warn {w}")
    for w in r["cut_snap"]:
        print(f"  warn {w} — advisory, not in the sign-off")
    for x in r["info"]:
        print(f"  info {x}")
    print(f"wrote {report_path(a.path)}: {r['cues']} cue(s), {len(r['fails'])} FAIL, {len(r['warnings'])} warning(s)"
          + (f", {len(r['cut_snap'])} cue edge(s) off a picture cut (advisory)" if r["cut_snap"] else "")
          + (" — sign the warnings off: srt_qa.py accept <file> --by <who> --reason \"…\"" if r["warnings"] and not r["fails"] else ""))
    return 1 if r["fails"] or (r["warnings"] and not r.get("accepted")) else 0


if __name__ == "__main__":
    sys.exit(main())
