#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""
replicate.py — keep a reference's STRUCTURE, change its content: new characters, environments, product,
voice and music; the same shot lengths, sizes, angles, camera moves, blocking and cut grammar.

Author, 2026-10-25: *"in case I want a reference promo video or short to be replicated but with new
environments, chars and sounds + voice. But framing, shots, movement etc remains the same."* Reference
rule, house decision the same day: *"Any reference, flagged"* — any reference may be used; the skill
records the source and a CLOSENESS score, and the decision stays with the owner per job.

It reads a merged shot graph (`shot_graph.py merge`), which carries the measured camera of every shot
and the read entities, positions, emotions, light and backgrounds.

  python3 replicate.py map SHOTGRAPH-ref.json -o MAP-ref.json            # the mapping form to fill
  python3 replicate.py audio REF.mp4 -o AUDIO-ref.json                   # speech slots, beats, hits (timings only)
  python3 replicate.py plan SHOTGRAPH-ref.json --map MAP-ref.json --job <job-dir> [--audio AUDIO-ref.json]
         [--clip-max 15]
  python3 replicate.py closeness <job-dir>/01-script/REPLICA-ref.json    # re-score after editing the plan
  python3 replicate.py --selftest

What `plan` writes into the job:
  * 01-script/REPLICA-<label>.json / .md — the structure template with the mapping applied: per shot the
    duration, size, angle, the measured camera (category, totals, speed profile, the blocking.py move),
    who stands where (mapped), their emotion, the light, where the eye goes and the negative space; per
    cut the relation, the match, the line, screen direction and what carries; the shots grouped into
    clips (one shot = a single-action clip; several = a planned multi-shot clip, multishot.md) with a
    [STAGES] skeleton; the audio slots — each line's window and how many words fit it at the source's
    pace, the beat map, the hits. Never the source's words, music or pictures.
  * 01-script/REPLICA-<label>/C<k>.blocking.draft.json — a blocking.py draft per clip: the camera shots
    from the measured moves, the mapped actors placed from their screen positions. `_draft: true` and
    `_need` say what a human still has to write (the set) before `blocking.py check`.
  * 00-brief/REPLICA-SOURCE.json — the source, its licence and the closeness score. `gate.py status`
    shows it and `gate.py approve export` warns on it: flagged, never refused (the house rule).

⛔ What it never does: copy the source's dialogue, captions, music or frames into the job, or generate
anything. It writes a plan; the job's normal gates do the rest.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LICENCES = ("own", "client", "licensed", "third-party")
KEEP_KEYS = ("durations", "sizes", "angles", "camera", "positions", "cut_grammar", "light")
CLOSE = {"shot-for-shot": 85.0, "close": 60.0}      # [assumed] house bands for the closeness flag
SCREEN_X = {"left": -1.2, "centre-left": -0.6, "centre": 0.0, "centre-right": 0.6, "right": 1.2, "off": 2.5}
DEPTH_Y = {"fg": -1.0, "mid": 0.0, "bg": 1.6}
FACING = {"camera": -90, "left": 180, "right": 0, "away": 90, "n/a": -90}
HEIGHT = {"eye": "eye", "low": "low", "high": "high", "aerial": "overhead", "dutch": "eye", "n/a": "eye"}
COLOURS = ["red", "blue", "green", "yellow", "orange", "purple"]


def now() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def load(p: str) -> dict:
    return json.load(open(p, encoding="utf-8"))


# ---- the mapping form -----------------------------------------------------------------------------
def map_form(graph_path: str, out: str) -> str:
    g = load(graph_path)
    ents = {}
    for e in g["entities"]:
        row = {"kind": e["kind"], "source": e.get("desc", ""), "as": "", "ref": ""}
        if e["kind"] == "location":
            row["variants_read"] = [v for v in (e.get("variants") or []) if str(v).strip()]
            row["variant"] = ""
        ents[e["id"]] = row
    voices = {e["id"]: {"voice": "", "language": ""} for e in g["entities"] if e["kind"] == "character"}
    form = {"graph": os.path.abspath(graph_path), "film": g["film"],
            "source": {"title": "", "url": "", "owner": "", "licence": ""},
            "entities": ents, "voice": voices, "music": {"as": "", "bpm": None},
            "keep": {k: True for k in KEEP_KEYS},
            "_how": ("Fill every `as` (who or what replaces it — a name the job's references will carry). "
                     "A location may take one of its read variants. `licence`: own / client / licensed / "
                     "third-party. Set a `keep` to false to let the plan diverge there; closeness drops with it.")}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(form, fh, indent=1, ensure_ascii=False)
    return out


def check_map(m: dict, g: dict) -> list:
    E = []
    src = m.get("source") or {}
    if not str(src.get("title") or "").strip():
        E.append("source.title is empty — the flag names what this replicates")
    if src.get("licence") not in LICENCES:
        E.append(f"source.licence {src.get('licence')!r} — one of {', '.join(LICENCES)}")
    ids = {e["id"] for e in g["entities"]}
    ents = m.get("entities") or {}
    for i in sorted(ids):
        if not str((ents.get(i) or {}).get("as") or "").strip():
            E.append(f"entity {i} is not mapped (`as` empty) — every character, prop and place is replaced")
    for k in ents:
        if k not in ids:
            E.append(f"entity {k} is not in the graph")
    for k in (m.get("keep") or {}):
        if k not in KEEP_KEYS:
            E.append(f"keep.{k} is not one of {', '.join(KEEP_KEYS)}")
    return E


# ---- audio: timings only --------------------------------------------------------------------------
def _pcm(path: str, sr: int = 16000):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout or b"", dtype=np.float32), sr


def audio(path: str, out: str) -> dict:
    """Speech windows and word counts (faster-whisper when installed; never the words), the beat map
    and the strongest hits (an onset envelope; librosa when installed)."""
    import numpy as np
    y, sr = _pcm(path)
    res = {"file": os.path.abspath(path), "duration": round(len(y) / sr, 3) if len(y) else 0.0,
           "speech": None, "speech_method": None, "beats": None, "bpm": None, "hits": [], "beat_method": None}
    if not len(y):
        res["note"] = "no audio stream"
    else:
        hop = 512
        n = len(y) // hop
        env = np.sqrt(np.array([float((y[i * hop:(i + 1) * hop] ** 2).mean()) for i in range(n)]) + 1e-12)
        on = np.maximum(0.0, np.diff(env, prepend=env[0]))
        try:
            import librosa                                                     # type: ignore
            tempo, bt = librosa.beat.beat_track(y=y.astype(np.float64), sr=sr, hop_length=hop)
            res["bpm"] = round(float(np.atleast_1d(tempo)[0]), 1)
            res["beats"] = [round(float(t), 3) for t in librosa.frames_to_time(bt, sr=sr, hop_length=hop)]
            res["beat_method"] = "librosa beat_track"
        except Exception:
            o = on - on.mean()
            ac = np.correlate(o, o, mode="full")[len(o) - 1:]
            fps = sr / hop
            lo, hi = int(fps * 60 / 180), int(fps * 60 / 70)
            if hi < len(ac) and hi > lo:
                lag = lo + int(np.argmax(ac[lo:hi]))
                res["bpm"] = round(60.0 * fps / lag, 1)
                period = lag
                phase = int(np.argmax([on[p::period].sum() for p in range(period)]))
                res["beats"] = [round((phase + k * period) / fps, 3) for k in range((n - phase) // period + 1)]
                res["beat_method"] = "onset-envelope autocorrelation (librosa not installed) [estimated]"
        thr = on.mean() + 3 * on.std()
        peaks = [i for i in range(1, n - 1) if on[i] > thr and on[i] >= on[i - 1] and on[i] >= on[i + 1]]
        peaks = sorted(peaks, key=lambda i: -on[i])[:16]
        res["hits"] = sorted(round(i * hop / sr, 3) for i in peaks)
        try:
            from faster_whisper import WhisperModel                            # type: ignore
            segs, _ = WhisperModel("base", device="cpu", compute_type="int8").transcribe(y, vad_filter=True)
            res["speech"] = [{"t0": round(s.start, 2), "t1": round(s.end, 2), "words": len(s.text.split()),
                              "wps": round(len(s.text.split()) / max(0.1, s.end - s.start), 2)} for s in segs]
            res["speech_method"] = "faster-whisper base (word COUNTS only — the words are not kept)"
        except Exception:
            res["speech_method"] = "UNMEASURED — faster-whisper not installed; the plan has no speech slots"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    return res


# ---- the plan ------------------------------------------------------------------------------------
def _as(m: dict, i: str) -> str:
    return str(((m.get("entities") or {}).get(i) or {}).get("as") or i)


def _clips(shots: list, cuts: list, clip_max: float) -> list:
    out, cur, t0 = [], [], None
    for k, s in enumerate(shots):
        start_new = False
        if cur:
            c = cuts[k - 1] if k - 1 < len(cuts) else {}
            if (s["t1"] - t0) > clip_max or c.get("relation") in ("new-scene", "time-jump"):
                start_new = True
        if start_new:
            out.append(cur); cur = []
        if not cur:
            t0 = s["t0"]
        cur.append(s["n"])
    if cur:
        out.append(cur)
    return out


def build_plan(g: dict, m: dict, au: dict | None, clip_max: float) -> dict:
    shots, t = [], 0.0
    for s in g["shots"]:
        meas = s.get("measured") or {}
        cam = meas.get("camera") or {}
        li = meas.get("light") or {}
        co = meas.get("composition") or {}
        dur = float(meas.get("dur") or (meas.get("end", 0) - meas.get("start", 0)) or 0)
        shots.append({
            "n": s["n"], "t0": round(t, 3), "t1": round(t + dur, 3), "dur": round(dur, 3),
            "size": s.get("size"), "angle": s.get("angle"),
            "camera": {"category": s.get("camera") or cam.get("category"), "family": s.get("camera") or cam.get("family"),
                       "blocking_move": cam.get("blocking_move"), "total": cam.get("total"),
                       "profile": cam.get("profile"), "speed": cam.get("mean_speed")},
            "characters": [{"as": _as(m, c["id"]), "from": c["id"], **{k: c.get(k) for k in
                            ("screen", "depth", "gaze", "facing", "motion", "expr", "intensity", "turn")}}
                           for c in s.get("characters") or []],
            "props": [{"as": _as(m, p["id"]), "from": p["id"], "holder": (_as(m, p["holder"]) if p.get("holder") not in (None, "none") else "none"),
                       "state": p.get("state")} for p in s.get("props") or []],
            "location": {"as": _as(m, s["location"]), "from": s["location"],
                         "variant": ((m.get("entities") or {}).get(s["location"]) or {}).get("variant") or ""} if s.get("location") else None,
            "light": {"key_side": s.get("light_key") or li.get("key_side"), "quality": s.get("light_quality"),
                      "style": s.get("light_style"), "time_of_day": s.get("time_of_day"), "key": li.get("key"),
                      "temp": li.get("temp")},
            "composition": {"brightest": co.get("brightest"), "negative_space": co.get("negative_space"),
                            "dof": co.get("dof")}})
        t += dur
    cuts = [{"n": c["n"], "from": c["from"], "to": c["to"], "relation": c["relation"], "match": c.get("match"),
             "axis": c.get("axis"), "screen_direction": c.get("screen_direction"), "eyeline": c.get("eyeline"),
             "carries": [_as(m, x) if x in (m.get("entities") or {}) else x for x in (c.get("carries") or [])]}
            for c in g["cuts"]]
    groups = _clips(shots, cuts, clip_max)
    clips = []
    for k, ns in enumerate(groups, 1):
        ss = [shots[n - 1] for n in ns]
        clips.append({"k": k, "shots": ns, "t0": ss[0]["t0"], "t1": ss[-1]["t1"],
                      "dur": round(ss[-1]["t1"] - ss[0]["t0"], 3),
                      "form": "single" if len(ns) == 1 else "multishot"})
    slots = None
    if au:
        slots = {"speech": [{"slot": i + 1, "t0": sp["t0"], "t1": sp["t1"], "fits_words": sp["words"],
                             "source_wps": sp["wps"]} for i, sp in enumerate(au.get("speech") or [])],
                 "speech_method": au.get("speech_method"), "bpm": au.get("bpm"), "beats": au.get("beats"),
                 "beat_method": au.get("beat_method"), "hits": au.get("hits")}
    return {"film": g["film"], "graph": m.get("graph"), "created": now(), "source": m.get("source"),
            "keep": {k: bool((m.get("keep") or {}).get(k, True)) for k in KEEP_KEYS},
            "mapping": {i: e.get("as") for i, e in (m.get("entities") or {}).items()},
            "voice": m.get("voice"), "music": m.get("music"), "shots": shots, "cuts": cuts, "clips": clips,
            "audio": slots}


def closeness(plan: dict, g: dict) -> dict:
    """How much of the source's STRUCTURE the plan keeps, 0–100, shot by shot in order. Each source
    shot scores the share of {duration within 15 %, size, angle, camera family, every character's
    screen side, the cut into it (relation + match)} the plan keeps. [assumed] weights, all equal."""
    src = g["shots"]
    by_n = {s["n"]: s for s in plan["shots"]}
    cut_src = {c["to"]: c for c in g["cuts"]}
    cut_pl = {c["to"]: c for c in plan["cuts"]}
    per = []
    for s in src:
        p = by_n.get(s["n"])
        if not p:
            per.append(0.0); continue
        meas = s.get("measured") or {}
        d0 = float(meas.get("dur") or 0)
        parts = [abs(p["dur"] - d0) <= 0.15 * max(d0, 0.1),
                 p.get("size") == s.get("size"), p.get("angle") == s.get("angle"),
                 (p.get("camera") or {}).get("family") == (s.get("camera") or (meas.get("camera") or {}).get("family"))]
        sc = sorted(c.get("screen") for c in s.get("characters") or [])
        pc = sorted(c.get("screen") for c in p.get("characters") or [])
        if sc:
            parts.append(sc == pc)
        if s["n"] in cut_src:
            a, b = cut_src[s["n"]], cut_pl.get(s["n"]) or {}
            parts.append(a.get("relation") == b.get("relation") and sorted(a.get("match") or []) == sorted(b.get("match") or []))
        per.append(100.0 * sum(parts) / len(parts))
    score = round(sum(per) / len(per), 1) if per else 0.0
    band = ("shot-for-shot" if score >= CLOSE["shot-for-shot"] else "close" if score >= CLOSE["close"] else "loose")
    mapped = sum(1 for v in (plan.get("mapping") or {}).values() if str(v or "").strip())
    return {"score": score, "band": band, "per_shot": [round(x, 1) for x in per],
            "content_mapped": f"{mapped}/{len(g['entities'])} entities replaced",
            "bands": CLOSE, "tag": "[assumed · house bands and equal weights, 2026-10-25]"}


def _height(angle):
    return HEIGHT.get(angle or "n/a", "eye")


def blocking_draft(plan: dict, clip: dict) -> dict:
    ss = [plan["shots"][n - 1] for n in clip["shots"]]
    who = []
    for s in ss:
        for c in s["characters"]:
            if c["as"] not in who:
                who.append(c["as"])
    ids = {name: chr(ord("A") + i) for i, name in enumerate(who)}
    actors = []
    for i, name in enumerate(who):
        first = next(c for s in ss for c in s["characters"] if c["as"] == name)
        keys = []
        for s in ss:
            for c in s["characters"]:
                if c["as"] == name:
                    keys.append({"t": round(s["t0"] - clip["t0"], 3),
                                 "pos": [SCREEN_X.get(c.get("screen") or "centre", 0.0), DEPTH_Y.get(c.get("depth") or "mid", 0.0)],
                                 "facing": FACING.get(c.get("facing") or "camera", -90),
                                 **({"look": "camera"} if c.get("gaze") == "camera" else {})})
        actors.append({"id": ids[name], "name": name, "color": COLOURS[i % len(COLOURS)], "height": 1.72,
                       "keys": keys or [{"t": 0, "pos": [SCREEN_X.get(first.get("screen") or "centre", 0.0), 0.0], "facing": -90}]})
    cam_shots = []
    for s, nxt in zip(ss, ss[1:] + [None]):
        on = ids.get((s["characters"][0] if s["characters"] else {}).get("as"))
        sh = {"t": [round(s["t0"] - clip["t0"], 3), round(s["t1"] - clip["t0"], 3)],
              "move": (s["camera"].get("blocking_move") or "static"), "height": _height(s.get("angle")),
              "_measured": {"category": s["camera"].get("category"), "total": s["camera"].get("total"),
                            "profile": s["camera"].get("profile")}}
        if on:
            sh["on"] = on
        if s.get("size") and s["size"] not in ("insert", "n/a"):
            sh["size"] = s["size"]
        if s["characters"]:
            sh["place"] = {"left": "left", "centre-left": "left", "centre": "centre", "centre-right": "right",
                           "right": "right"}.get(s["characters"][0].get("screen"), "auto")
        cam_shots.append(sh)
    locs = sorted({(s["location"] or {}).get("as") for s in ss if s.get("location")})
    return {"_draft": True, "_from": f"replicate.py · {plan['film']} clip {clip['k']}",
            "_need": [f"env or set[] for {', '.join(locs) or 'the location'} (references/blocking.md §3, §3c)",
                      "props[] for what the actors hold", "the legend line per colour", "then: blocking.py check"],
            "shot": f"R{clip['k']:02d}", "duration": clip["dur"], "fps": 24, "aspect": "9:16",
            "render": {"w": 540, "h": 960},
            "legend": {a["color"]: a["name"] for a in actors},
            "actors": actors, "camera": {"shots": cam_shots},
            **({"line_of_action": [actors[0]["id"], actors[1]["id"]]} if len(actors) >= 2 else {})}


def _skeleton(s: dict) -> str:
    who = "; ".join(f"{c['as']} at screen-{c.get('screen')}, {c.get('depth')}, looking {c.get('gaze')}, "
                    f"{c.get('expr')} ({c.get('intensity')})" for c in s["characters"]) or "no one"
    loc = (s.get("location") or {})
    li = s["light"]
    return (f"{s.get('size')} · {s.get('angle')} · {s['camera'].get('category')} ({s['camera'].get('profile')}) · {who} · "
            f"in {loc.get('as') or '—'}" + (f" ({loc['variant']})" if loc.get("variant") else "")
            + f" · key {li.get('key_side')} {li.get('quality') or ''} {li.get('style') or ''} {li.get('time_of_day') or ''}"
            + f" · eye to {s['composition'].get('brightest')}, negative space {', '.join(s['composition'].get('negative_space') or [])}")


def render_md(plan: dict, cl: dict) -> str:
    src = plan.get("source") or {}
    L = [f"# Replica plan — {plan['film']}", "",
         f"Source: **{src.get('title')}** · {src.get('owner') or '?'} · licence **{src.get('licence')}** · {src.get('url') or ''}",
         f"Closeness: **{cl['score']}** ({cl['band']}) {cl['tag']} · {cl['content_mapped']}", "",
         "⚠ The house rule (2026-10-25): any reference may be used, flagged — the source and this score travel "
         "with the job, and the decision is the owner's per job. Nothing from the source's dialogue, music or "
         "pictures enters this plan.", "",
         "## Mapping", "", "| source | becomes |", "|---|---|"]
    for k, v in (plan.get("mapping") or {}).items():
        L.append(f"| {k} | {v} |")
    L += ["", "## Clips", "", "| clip | shots | time | form |", "|---|---|---|---|"]
    for c in plan["clips"]:
        L.append(f"| C{c['k']} | {', '.join(map(str, c['shots']))} | {c['t0']}–{c['t1']} s | {c['form']} |")
    L += ["", "## Shots — the structure kept", "", "| S | t | dur | size | angle | camera → blocking | skeleton |",
          "|---|---|---|---|---|---|---|"]
    for s in plan["shots"]:
        L.append(f"| {s['n']} | {s['t0']}–{s['t1']} | {s['dur']} | {s.get('size')} | {s.get('angle')} | "
                 f"{s['camera'].get('category')} → {s['camera'].get('blocking_move') or '—'} | {_skeleton(s)} |")
    L += ["", "## Cuts", "", "| C | S→S | relation | match | line | screen dir | carries |", "|---|---|---|---|---|---|---|"]
    for c in plan["cuts"]:
        L.append(f"| {c['n']} | {c['from']}→{c['to']} | {c['relation']} | {', '.join(c.get('match') or [])} | {c.get('axis')} | "
                 f"{c.get('screen_direction')} | {', '.join(c.get('carries') or [])} |")
    for c in plan["clips"]:
        if c["form"] != "multishot":
            continue
        L += ["", f"### C{c['k']} — [STAGES] skeleton (form: multishot)", "", "```", "[STAGES]"]
        for i, n in enumerate(c["shots"], 1):
            s = plan["shots"][n - 1]
            a, b = round(s["t0"] - c["t0"], 2), round(s["t1"] - c["t0"], 2)
            L.append(f"Stage {i} | {a:g}–{b:g} s | {s.get('size')}, {s.get('angle')} level, {s['camera'].get('category')}")
            L.append(f"Use: {', '.join(x['as'] for x in s['characters']) or '—'}")
            L.append("Event: <one primary state change, written for the new cast>")
            L.append("End state: <positions and props as the cut needs them>")
            if i < len(c["shots"]):
                cut = plan["cuts"][n - 1]
                L.append(f"Cut: {'match cut' if 'action' in (cut.get('match') or []) else 'hard'}")
            L.append("")
        L.append("```")
    au = plan.get("audio")
    L += ["", "## Audio — timings only", ""]
    if not au:
        L.append("Not measured — `replicate.py audio <reference> -o AUDIO.json`, then plan again.")
    else:
        L.append(f"- speech: {au.get('speech_method')}")
        for sp in au.get("speech") or []:
            L.append(f"  - slot {sp['slot']}: {sp['t0']}–{sp['t1']} s · fits about {sp['fits_words']} words at the source's "
                     f"{sp['source_wps']} words/s — write the NEW line to this length")
        L.append(f"- music: {au.get('bpm')} bpm ({au.get('beat_method')}) — the new track within ±3 bpm, or cut it to "
                 f"this beat map; {len(au.get('beats') or [])} beats")
        L.append(f"- hits (SFX or accents): {', '.join(map(str, au.get('hits') or [])) or 'none found'}")
    L += ["", "## Next", "", "1. Approve the mapping and this plan (the job's concept/script gates apply as always).",
          "2. Fill the blocking drafts' sets, `blocking.py check`, build, approve `blocking:<SHOT>`.",
          "3. Frame prompts from the skeletons → the frame gate; clip prompts (multishot clips from the [STAGES] skeleton).",
          "4. Voice to the speech slots, music to the beat map, the edit to the cut table.",
          "5. If you change the plan, `replicate.py closeness` re-scores it."]
    return "\n".join(L) + "\n"


def write_source(job: str, plan: dict, cl: dict, plan_path: str) -> str:
    p = os.path.join(job, "00-brief", "REPLICA-SOURCE.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    rec = {"source": plan.get("source"), "film": plan["film"], "closeness": cl["score"], "band": cl["band"],
           "flagged": True, "plan": os.path.relpath(plan_path, job), "computed_at": now(),
           "rule": "author, 2026-10-25: any reference may be used, flagged — the decision stays with the owner per job"}
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, ensure_ascii=False)
    return p


def plan_cmd(graph_path: str, map_path: str, job: str, audio_path: str | None, clip_max: float) -> int:
    g, m = load(graph_path), load(map_path)
    E = check_map(m, g)
    if E:
        print("REFUSED: the mapping is not complete:\n  - " + "\n  - ".join(E), file=sys.stderr)
        return 1
    au = load(audio_path) if audio_path else None
    m["graph"] = os.path.abspath(graph_path)
    plan = build_plan(g, m, au, clip_max)
    cl = closeness(plan, g)
    plan["closeness"] = cl
    sd = os.path.join(job, "01-script")
    os.makedirs(os.path.join(sd, f"REPLICA-{g['film']}"), exist_ok=True)
    pj = os.path.join(sd, f"REPLICA-{g['film']}.json")
    with open(pj, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(sd, f"REPLICA-{g['film']}.md"), "w", encoding="utf-8") as fh:
        fh.write(render_md(plan, cl))
    for c in plan["clips"]:
        with open(os.path.join(sd, f"REPLICA-{g['film']}", f"C{c['k']:02d}.blocking.draft.json"), "w", encoding="utf-8") as fh:
            json.dump(blocking_draft(plan, c), fh, indent=1, ensure_ascii=False)
    sp = write_source(job, plan, cl, pj)
    print(f"REPLICA-{g['film']} · {len(plan['shots'])} shots in {len(plan['clips'])} clip(s) · closeness {cl['score']} "
          f"({cl['band']}) · licence {plan['source'].get('licence')} → {os.path.relpath(pj)}, {os.path.relpath(sp)}")
    if cl["band"] == "shot-for-shot" and plan["source"].get("licence") == "third-party":
        print("  ⚠ FLAGGED: a shot-for-shot structure of a third-party film. Allowed by the house rule; the call is "
              "the owner's, per job, and `gate.py approve export` will say so again.")
    return 0


def closeness_cmd(plan_path: str) -> int:
    plan = load(plan_path)
    g = load(plan["graph"])
    cl = closeness(plan, g)
    plan["closeness"] = cl
    with open(plan_path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=1, ensure_ascii=False)
    job = os.path.dirname(os.path.dirname(os.path.abspath(plan_path)))
    write_source(job, plan, cl, plan_path)
    with open(plan_path[:-5] + ".md", "w", encoding="utf-8") as fh:
        fh.write(render_md(plan, cl))
    print(f"closeness {cl['score']} ({cl['band']}) · per shot {cl['per_shot']}")
    return 0


# ---- selftest ------------------------------------------------------------------------------------
def _graph() -> dict:
    def shot(n, dur, size, cam, chars, loc, mv):
        return {"n": n, "size": size, "angle": "eye", "location": loc, "characters": chars, "props": [],
                "light_key": "left", "light_quality": "soft", "light_style": "natural", "time_of_day": "day",
                "camera": "", "measured": {"n": n, "dur": dur, "camera": {"category": cam, "family": cam.split("-")[0],
                                                                        "blocking_move": mv, "total": {}, "profile": "constant"},
                                           "light": {"key_side": "left", "key": "mid-key", "temp": "warm"},
                                           "composition": {"brightest": "top-right", "negative_space": ["left"], "dof": "shallow"}}}
    A = {"id": "A", "screen": "left", "depth": "mid", "gaze": "screen-right", "facing": "right", "motion": "none",
         "expr": "curious", "intensity": 1, "turn": "none"}
    B = dict(A, id="B", screen="right", gaze="screen-left", facing="left")
    shots = [shot(1, 2.0, "WS", "push", [A, B], "L1", "push_in"), shot(2, 1.5, "MCU", "locked", [A], "L1", "locked"),
             shot(3, 1.5, "MCU", "locked", [B], "L1", "locked"), shot(4, 3.0, "MS", "pan", [A], "L2", "pan")]
    cuts = [{"n": 1, "from": 1, "to": 2, "relation": "same-scene", "match": ["eyeline"], "axis": "kept",
             "screen_direction": "n/a", "eyeline": "matched", "carries": ["A", "L1"]},
            {"n": 2, "from": 2, "to": 3, "relation": "same-scene", "match": ["eyeline"], "axis": "kept",
             "screen_direction": "n/a", "eyeline": "matched", "carries": ["L1"]},
            {"n": 3, "from": 3, "to": 4, "relation": "new-scene", "match": ["none"], "axis": "n/a",
             "screen_direction": "n/a", "eyeline": "n/a", "carries": []}]
    ents = [{"id": "A", "kind": "character", "desc": "a woman in a coat"}, {"id": "B", "kind": "character", "desc": "a man"},
            {"id": "L1", "kind": "location", "desc": "a café", "variants": ["a train", "a bookshop", "a greenhouse"]},
            {"id": "L2", "kind": "location", "desc": "a street", "variants": ["a pier"]}]
    return {"film": "ref", "entities": ents, "shots": shots, "cuts": cuts}


def selftest() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if (detail and not cond) else ""))
    print("replicate.py selftest")
    with tempfile.TemporaryDirectory() as td:
        gp = os.path.join(td, "SHOTGRAPH-ref.json"); json.dump(_graph(), open(gp, "w"))
        mp = map_form(gp, os.path.join(td, "MAP-ref.json"))
        m = load(mp)
        check("the mapping form lists every entity, the location's read variants and the keep switches",
              set(m["entities"]) == {"A", "B", "L1", "L2"} and m["entities"]["L1"]["variants_read"][0] == "a train"
              and set(m["keep"]) == set(KEEP_KEYS))
        job = os.path.join(td, "job")
        check("an unfilled mapping is refused", plan_cmd(gp, mp, job, None, 15.0) == 1)
        m["source"] = {"title": "Reference café spot", "url": "https://example.com/ref", "owner": "Some Agency",
                       "licence": "third-party"}
        for k, v in {"A": "Mika", "B": "Jon", "L1": "the night bakery", "L2": "the canal"}.items():
            m["entities"][k]["as"] = v
        m["entities"]["L1"]["variant"] = "a bookshop"
        json.dump(m, open(mp, "w"))
        check("a filled mapping plans", plan_cmd(gp, mp, job, None, 15.0) == 0)
        pj = os.path.join(job, "01-script", "REPLICA-ref.json")
        plan = load(pj)
        check("the cast and places are swapped, the structure is not",
              plan["shots"][0]["characters"][0]["as"] == "Mika" and plan["shots"][0]["size"] == "WS"
              and plan["shots"][0]["camera"]["blocking_move"] == "push_in" and plan["shots"][3]["t0"] == 5.0)
        check("a new scene starts a new clip; the same scene runs as one multi-shot clip",
              [c["shots"] for c in plan["clips"]] == [[1, 2, 3], [4]] and plan["clips"][0]["form"] == "multishot")
        check("an unchanged plan is shot-for-shot (closeness 100), and the source record says so",
              plan["closeness"]["score"] == 100.0 and plan["closeness"]["band"] == "shot-for-shot"
              and load(os.path.join(job, "00-brief", "REPLICA-SOURCE.json"))["band"] == "shot-for-shot")
        bd = load(os.path.join(job, "01-script", "REPLICA-ref", "C01.blocking.draft.json"))
        check("the blocking draft carries the measured moves, the mapped actors and the line between them",
              [s["move"] for s in bd["camera"]["shots"]] == ["push_in", "locked", "locked"]
              and [a["name"] for a in bd["actors"]] == ["Mika", "Jon"] and bd["line_of_action"] == ["A", "B"]
              and bd["actors"][0]["keys"][0]["pos"][0] < 0 < bd["actors"][1]["keys"][0]["pos"][0] and bd["_draft"])
        md = open(os.path.join(job, "01-script", "REPLICA-ref.md")).read()
        check("the plan names the source, its licence and the flag", "Reference café spot" in md and "third-party" in md
              and "flagged" in md and "Stage 1 | 0–2 s" in md)
        plan["shots"][0]["dur"] = 3.5; plan["shots"][1]["size"] = "CU"; plan["shots"][3]["camera"]["family"] = "locked"
        json.dump(plan, open(pj, "w"))
        closeness_cmd(pj)
        cl = load(pj)["closeness"]
        check("changing three things lowers exactly the shots changed", cl["score"] < 100.0
              and cl["per_shot"][2] == 100.0 and min(cl["per_shot"][0], cl["per_shot"][1], cl["per_shot"][3]) < 100.0,
              json.dumps(cl))
        plan = load(pj)
        for sh in plan["shots"]:
            sh["dur"] = round(sh["dur"] * 1.6, 3); sh["size"] = "EWS"
        json.dump(plan, open(pj, "w"))
        closeness_cmd(pj)
        cl = load(pj)["closeness"]
        check("re-timing and re-sizing every shot moves the band off shot-for-shot", cl["band"] in ("close", "loose")
              and load(os.path.join(job, "00-brief", "REPLICA-SOURCE.json"))["band"] == cl["band"], json.dumps(cl))
        wav = os.path.join(td, "click.wav")
        if shutil.which("ffmpeg"):
            import numpy as np
            import wave
            sr = 16000
            y = np.zeros(sr * 8, dtype=np.float32)
            for k in range(16):                      # 120 bpm clicks
                i = int(k * 0.5 * sr); y[i:i + 200] = np.hanning(200).astype(np.float32)
            with wave.open(wav, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
                w.writeframes((y * 30000).astype(np.int16).tobytes())
            au = audio(wav, os.path.join(td, "AUDIO.json"))
            check("the beat map of a 120 bpm click track reads 120 (±3)", au["bpm"] and abs(au["bpm"] - 120) <= 3, str(au.get("bpm")))
            check("hits are found and no words are ever stored", len(au["hits"]) >= 8 and "text" not in json.dumps(au))
    print("-" * 60)
    print("selftest OK — the mapping form, the refusal of an unmapped plan, the swap that keeps the structure, clips "
          "split at a new scene, closeness 100 → lower after edits, the blocking draft (moves, mapped actors, the line), "
          "the flag in the plan, and the audio beat map from a click track" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    mp = sub.add_parser("map"); mp.add_argument("graph"); mp.add_argument("-o", "--out", required=True)
    au = sub.add_parser("audio"); au.add_argument("video"); au.add_argument("-o", "--out", required=True)
    pl = sub.add_parser("plan"); pl.add_argument("graph"); pl.add_argument("--map", required=True)
    pl.add_argument("--job", required=True); pl.add_argument("--audio"); pl.add_argument("--clip-max", type=float, default=15.0)
    cl = sub.add_parser("closeness"); cl.add_argument("plan")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "map":
        print(map_form(a.graph, a.out)); return 0
    if a.cmd == "audio":
        r = audio(a.video, a.out)
        print(f"{a.out} · {r.get('bpm')} bpm ({r.get('beat_method')}) · {len(r.get('hits') or [])} hits · speech: {r.get('speech_method')}")
        return 0
    if a.cmd == "plan":
        return plan_cmd(a.graph, a.map, a.job, a.audio, a.clip_max)
    if a.cmd == "closeness":
        return closeness_cmd(a.plan)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
