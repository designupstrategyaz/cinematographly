#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""film_db.py — the reference-shot database: every measured shot of every reference film, queryable.

⛔ WHY A DATABASE AND NOT A WRITE-UP. Prose about a reference film cannot be searched, filtered or
turned back into a prompt. "Find me a 3-second locked-off shot that follows a dissolve and carries
no dialogue" is the question a director actually asks, and it is a query. This file is the answer
shape: one row per shot, measured by `film_breakdown.py`, plus the fields a human fills in by
LOOKING at the shot. `card` turns any row back into a prompt skeleton — which is what "replicate"
means here.

⛔ WHAT IS DELIBERATELY NOT STORED: the dialogue. These are other people's films. The database keeps
speech as a MEASUREMENT (does this shot speak · how many words · words per second) and a `beat`
written in your own words. It never stores the lines, because a row-per-shot copy of every line is a
copy of the script (`compliance.md`; the skill's own quoting rule).

Storage is JSONL, not SQLite, on purpose: it diffs in git, greps from a terminal, and survives
review. 1,000 shots is 400 KB.

Usage
-----
  film_db.py build --from <breakdowns/> --transcripts <dir> [--out assets/reference-shots.jsonl]
  film_db.py stats [--film F4]
  film_db.py facets [--film F2] [--include-nonfilm]   # distributions over the READ fields (+ the tracker's, when attached)
  film_db.py attach JOINS-F5.json --film F5         # add shot_graph's per-shot measurements, tagged, nothing overwritten
  film_db.py seq --film F5                    # chapters, cadence, montage/sustained runs, adjacency
  film_db.py run F5#116-124                   # one sequence as a shot-by-shot skeleton
  film_db.py cross in:world                      # how two categories interact, with lift
  film_db.py lint                                # shifted columns, off-vocabulary sizes/angles
  film_db.py structure [--film F5]            # story beats pinned to shots, % recomputed
  film_db.py chain [--film F2]                # what carries across a cut: performance, size, angle, timing
  film_db.py query --move "locked off" --min-dur 3 --transition-in dissolve --speech no
  film_db.py query --size CU --light uplight        # the READ fields filter too
  film_db.py card F4#82                  # a prompt skeleton built from the measured row
  film_db.py annotate F4#82 --size CU --angle eye --subject "..." --beat "..."
  film_db.py --selftest

Exit codes: 0 ok · 1 nothing matched / not found · 2 usage.
"""
from __future__ import annotations
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(os.path.dirname(HERE), "assets", "reference-shots.jsonl")
DEFAULT_CUTCHECK = os.path.join(os.path.dirname(HERE), "assets", "reference-cutcheck.json")
# ⛔ TWO KINDS OF CAMERA AND LIGHT IN ONE ROW, KEPT APART. `move`/`move_class` are film_breakdown's
# whole-shot solve; `read` is what a person (or a model) wrote by looking; `tracked` is shot_graph's
# 8 fps chained track and pixel light, attached later with its source. They disagree in places
# (2026-10-25: F4's light reads cool on 46 % of shots and measures neutral on 72 %). Nothing here
# picks a winner: every report prints which is read and which is measured.
TRACKED_TOL = 0.05     # s — a tracked block attaches to a row only if its shot starts and ends here
# ⚡ `light` and `acting` are first-class: they are what a prompt has to state and what a
# measurement cannot reach. A row with a move and no light is half a shot.
READ_FIELDS = ("size", "angle", "light", "acting", "subject", "beat", "vfx", "notes",
               "expr", "intensity", "turn")
# ⚡ THE PERFORMANCE CODEBOOK — fixed BEFORE the read so 935 shots are coded on one scale.
# expr: the dominant emotion, one word. intensity: 0 blank · 1 restrained (only the eyes or mouth
# carry it) · 2 open (the face moves, clearly readable) · 3 peak (full release — tears running,
# shouting, sobbing, open laughter). turn: '-' if the performance does not change inside the shot,
# else '<when>: <what changes>' with <when> = early (IN→MID) · late (MID→OUT) · through (continuous),
# read off three frames at 15/50/85 % of the shot.
EXPR_VOCAB = {"neutral", "attentive", "curious", "wary", "fear", "shock", "sad", "grief", "tender",
              "joy", "amused", "anger", "resolve", "awe", "relief", "pleading", "defeated", "effort", "pain"}
TURN_WHEN = ("early:", "late:", "through:")
REF_RE = re.compile(r"^([A-Za-z0-9_-]+)#(\d+)$")


def move_class(move: str) -> str:
    m = (move or "").lower()
    if m.startswith(("unreliable", "unmeasured")):
        return "unsolved"
    for k in ("locked off", "drift", "handheld"):
        if m.startswith(k):
            return k
    parts = [k for k in ("push in", "pull out", "pan", "tilt", "roll") if k in m]
    return "+".join(parts) or "other"


def load(db: str) -> list:
    if not os.path.isfile(db):
        return []
    out = []
    with open(db, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def save(db: str, rows: list) -> None:
    os.makedirs(os.path.dirname(db), exist_ok=True)
    with open(db, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def speech_in(segments: list, a: float, b: float) -> tuple:
    """Words spoken inside [a,b). Only the COUNT is kept — never the words (see the header)."""
    n = 0
    for s in segments:
        if s["end"] <= a or s["start"] >= b:
            continue
        overlap = min(b, s["end"]) - max(a, s["start"])
        span = max(1e-6, s["end"] - s["start"])
        w = s["words"] if isinstance(s.get("words"), (int, float)) else len(s.get("text", "").split())
        n += w * (overlap / span)
    return round(n, 1), round(n / max(1e-6, b - a), 2)


def build(src_dir: str, tr_dir: str | None, db: str, meta: dict | None = None) -> list:
    old = load(db)
    rows, keep = [], {r["film"] + "#" + str(r["n"]): r.get("read", {})
                      for r in old}                 # never lose hand-written reads on a rebuild
    # a tracked block was measured on ONE shot: it survives a rebuild only if that shot did not move
    keep_t = {r["film"] + "#" + str(r["n"]): r for r in old if r.get("tracked")}
    for f in sorted(os.listdir(src_dir)):
        if not (f.startswith("BREAKDOWN-") and f.endswith(".json")):
            continue
        d = json.load(open(os.path.join(src_dir, f), encoding="utf-8"))
        lab = d["label"]
        segs = []
        if tr_dir and os.path.isfile(os.path.join(tr_dir, lab + ".json")):
            t = json.load(open(os.path.join(tr_dir, lab + ".json"), encoding="utf-8"))
            segs = [s for s in t.get("segments", []) if s.get("text") or s.get("words")]
        for r in d["rows"]:
            if r["dur"] <= 0:
                continue
            w, wps = speech_in(segs, r["start"], r["end"]) if segs else (0.0, 0.0)
            key = f"{lab}#{r['n']}"
            row = {"film": lab, "n": r["n"], "start": r["start"], "end": r["end"], "dur": r["dur"],
                   "transition_in": r.get("transition_in"), "transition_out": r.get("transition_out"),
                   "move": r.get("move"), "move_class": move_class(r.get("move") or ""),
                   "cam_rate": r.get("per_s"), "subject_residual": r.get("residual"),
                   "luma": r.get("luma"), "palette": r.get("palette") or [],
                   # ⛔ carried, not recomputed: film_breakdown flags a shot that splits further at a
                   # more sensitive threshold. build() used to DROP this, so a flagged 32 s "shot"
                   # reached §10.1's "longest reliable" column as reliable.
                   "split_suspect": bool(r.get("split_suspect")),
                   "speech_words": w, "speech_wps": wps, "has_speech": w >= 1.0,
                   "read": {k: keep.get(key, {}).get(k) for k in READ_FIELDS}}
            if meta and lab in meta:
                row.update(meta[lab])
            o = keep_t.get(key)
            if o and abs(o["start"] - r["start"]) <= TRACKED_TOL and abs(o["end"] - r["end"]) <= TRACKED_TOL:
                row["tracked"] = o["tracked"]
            rows.append(row)
    save(db, rows)
    return rows


# ---- the tracker's measurements, attached beside the read --------------------------------------
def _coarse_fb(move_cls: str):
    """film_breakdown's class → the coarse class both trackers can name (None: not comparable)."""
    if move_cls in (None, "", "unsolved"):
        return None
    if move_cls in ("locked off", "drift", "handheld"):
        return {"locked off": "locked"}.get(move_cls, move_cls)
    return "directed"


def _coarse_sg(family: str):
    if family in (None, "", "unsolved"):
        return None
    if family in ("locked", "drift", "handheld"):
        return family
    return "directed"


def tracked_block(shot: dict, cut_in: dict | None, source: str) -> dict:
    cam = shot.get("camera") or {}
    lt = shot.get("light") or {}
    blk = {"source": source,
           "camera": dict({k: cam.get(k) for k in ("category", "direction", "profile", "shake",
                                                    "parallax", "travels", "pairs_ok", "pairs")},
                          family=cam.get("family") or cam.get("category")),     # an unsolved shot has no family
           "light": {k: lt.get(k) for k in ("key", "key_side", "temp", "contrast", "sat")},
           "dof": (shot.get("composition") or {}).get("dof")}
    if cut_in and "unmeasured" not in cut_in:
        blk["join_in"] = {k: cut_in.get(k) for k in ("look", "look_sim", "delta_e", "luma_jump", "screen_dir",
                                                      "eye_shift", "key_side_out", "key_side_in", "flags")}
    elif cut_in:
        blk["join_in"] = {"unmeasured": cut_in["unmeasured"]}
    return blk


def attach_tracked(rows: list, joins: dict, film: str, source: str) -> int:
    """Attach shot_graph's per-shot block to every row of FILM. Refuses unless the JOINS file was
    measured on THIS film's own cut list (same count, every start and end within TRACKED_TOL):
    a block attached to the wrong shot is worse than none. Touches only `tracked`."""
    R = sorted([r for r in rows if r["film"].upper() == film.upper()], key=lambda r: r["n"])
    S = joins.get("shots") or []
    if not R:
        raise SystemExit(f"error: no rows for film {film}")
    if len(S) != len(R):
        raise SystemExit(f"error: {len(S)} measured shots against {len(R)} database rows — measure with the "
                         f"database's own cut list (shot_graph.py measure --cuts <starts of rows 2..N>)")
    # the last shot ends at the film's end, which two probes read a few frames apart (container vs
    # stream duration: 0.07 s on F1 and F5), so its end gets a looser check
    bad = [r["n"] for k, (r, s) in enumerate(zip(R, S))
           if abs(r["start"] - s["start"]) > TRACKED_TOL
           or abs(r["end"] - s["end"]) > (0.25 if k == len(R) - 1 else TRACKED_TOL)]
    if bad:
        raise SystemExit(f"error: {len(bad)} row(s) do not line up with the measured shots (first: #{bad[0]})")
    cuts = {c["to"]: c for c in (joins.get("cuts") or [])}
    for r, s in zip(R, S):
        r["tracked"] = tracked_block(s, cuts.get(s["n"]), source)
    return len(R)


def cmd_attach(rows: list, path: str, film: str, db: str, source: str | None) -> int:
    j = json.load(open(path, encoding="utf-8"))
    src = source or (f"shot_graph · {os.path.basename(path)} · cuts: {j.get('cuts_source')}"
                     + (" (confirmed)" if j.get("cuts_confirmed") else " (NOT confirmed)"))
    n = attach_tracked(rows, j, film, src)
    save(db, rows)
    print(f"{film}: tracked block on {n} row(s) · source: {src} · read, move and every other field untouched")
    return 0


def load_cutcheck(path: str = DEFAULT_CUTCHECK) -> dict:
    try:
        return json.load(open(path, encoding="utf-8")).get("films") or {}
    except (OSError, ValueError):
        return {}


def match(r: dict, a) -> bool:
    if a.film and r["film"].upper() != a.film.upper():
        return False
    if a.move and a.move.lower() not in (r["move_class"] or ""):
        return False
    if a.min_dur is not None and r["dur"] < a.min_dur:
        return False
    if a.max_dur is not None and r["dur"] > a.max_dur:
        return False
    if a.transition_in and (r.get("transition_in") or "") != a.transition_in:
        return False
    if a.transition_out and (r.get("transition_out") or "") != a.transition_out:
        return False
    if a.speech == "yes" and not r["has_speech"]:
        return False
    if a.speech == "no" and r["has_speech"]:
        return False
    if a.unread and any(r["read"].get(k) for k in READ_FIELDS):
        return False
    # ⛔ THE READ FIELDS ARE FILTERS HERE, NOT SETTERS. argparse defines --size/--angle/--light/
    # --acting/... once, for `annotate`; before this they parsed on `query` and filtered NOTHING,
    # so `query --size CU` returned all 1,122 rows and looked like an answer. Substring, case-
    # insensitive, because the read values are sentences ("window daylight · soft · warm").
    for k in READ_FIELDS:
        want = getattr(a, k, None)
        if want and want.lower() not in (r["read"].get(k) or "").lower():
            return False
    return True


def cmd_query(rows: list, a) -> int:
    hits = [r for r in rows if match(r, a)]
    if a.json:
        print(json.dumps(hits, indent=2, ensure_ascii=False)); return 0 if hits else 1
    print(f"{len(hits)} shot(s)")
    for r in hits[: a.limit]:
        rd = r["read"]
        print(f"  {r['film']}#{r['n']:<4} {r['start']:>7.1f}-{r['end']:<7.1f} {r['dur']:>5.2f}s  "
              f"{(r['transition_in'] or '?'):<8}->{(r['transition_out'] or '?'):<8} "
              f"{(r['move_class'] or '?'):<12} speech {r['speech_words']:>5}w  "
              f"{rd.get('size') or '--':<4} {rd.get('beat') or ''}")
    if len(hits) > a.limit:
        print(f"  … {len(hits) - a.limit} more (--limit)")
    return 0 if hits else 1


def cmd_stats(rows: list, film: str | None) -> int:
    import statistics as st, collections
    films = sorted({r["film"] for r in rows}) if not film else [film.upper()]
    for f in films:
        R = [r for r in rows if r["film"].upper() == f.upper()]
        if not R:
            print(f"{f}: no rows"); continue
        d = [r["dur"] for r in R]
        mv = collections.Counter(r["move_class"] for r in R)
        ti = collections.Counter(r["transition_in"] or "?" for r in R)
        sp = sum(1 for r in R if r["has_speech"])
        rd = sum(1 for r in R if any(r["read"].get(k) for k in READ_FIELDS))
        print(f"{f:<12} {len(R):>4} shots · median {st.median(d):.2f}s · speech in {100*sp//len(R)}% "
              f"· read {rd}/{len(R)}")
        print(f"             moves  " + " ".join(f"{k}:{v}" for k, v in mv.most_common(5)))
        print(f"             enters " + " ".join(f"{k}:{v}" for k, v in ti.most_common(4)))
        perf = [r for r in R if cat(r["read"], "performer") and not cat(r["read"], "nonfilm")]
        pc = sum(1 for r in perf if r["read"].get("expr"))
        print(f"             performance coded {pc}/{len(perf)} performer shots")
    return 0


# ⚡ FACET RULES. Every published count about these films comes out of `facets`, so the buckets are
# ORDERED keyword rules printed with the result — not a judgement made once and then quoted forever.
# First rule that matches wins. Change a rule and every number that cites it has to be re-derived.
NONFILM = "NOT A FILM SHOT"
LIGHT_RULES = [
    ("none",            ("black frame",)),
    ("shadowless",      ("shadowless",)),
    ("single source",   ("single source", "as key", "as the only", "only key", "self-lit",
                         "one lit", "one small", "single practical", "single candle",
                         "single lamp", "single hard", "single warm", "single low",
                         "single distant", "single overhead", "single soft", "one bar")),
    ("low key",         ("low key", "deep shadow", "deep fall-off", "dark surround")),
    ("hard/directional",("hard", "raking", "specular", "uplight", "backlit", "silhouette", "rim",
                         "top light", "pooled", "shaft", "column", "pulsing", "flare",
                         "long shadows", "streaked", "warm key", "stage wash", "point source",
                         "blown", "intermittent", "god rays", "broken")),
    ("soft",            ("soft", "diffuse", "wrap")),
    ("flat/even",       ("flat", "even", "high key")),
]
COLOUR_RULES = [
    ("warm",     ("warm", "amber", "orange", "gold")),
    ("cool",     ("cool", "cold", "teal", "blue", "green-cyan")),
    ("saturated",("saturated", "magenta", "violet", "hot red", "electric", "green,", "green ")),
    ("neutral",  ("neutral", "grey", "gray", "white")),
]
ACTING_RULES = [
    ("no performer", ("no performer",)),
    ("holds still",  ("still", "motionless", "does not move", "not moving", "unmoving",
                      "without moving", "holds", "hold", "waits", "unchanged")),
]
KEYED_BY_PRACTICAL = ("practical", "self-lit", "screen", "lamp", "firelight", "candle", "beacon",
                      "headlight", "neon", "projector", "window", "signage", "sign ", "oven")


def _bucket(value: str, rules, default: str) -> str:
    v = (value or "").lower()
    for name, keys in rules:
        if any(k in v for k in keys):
            return name
    return default


# (3.0.0) The SHIPPED reference set keeps category labels only, never the written read (the owner: "Numbers only,
# anonymised"): `cats()` derives them once from a row that still has its prose, and every report reads them through
# the helpers below — the stored label when the row has one, else derived from the prose (a studio's own database).
CAT_KEYS = ("light_q", "colour", "acting_b", "keyed", "performer", "nonfilm", "has_vfx", "turned", "turn_when")


def cats(rd: dict) -> dict:
    t = rd.get("turn")
    when = t.split(":", 1)[0] if t and t != "-" and t.startswith(TURN_WHEN) else None
    return {"light_q": _bucket(rd.get("light"), LIGHT_RULES, "other"),
            "colour": _bucket(rd.get("light"), COLOUR_RULES, "other"),
            "acting_b": _bucket(rd.get("acting"), ACTING_RULES, "acts"),
            "keyed": "practical" if any(k in (rd.get("light") or "").lower() for k in KEYED_BY_PRACTICAL) else "unmotivated",
            "performer": "no performer" not in (rd.get("acting") or ""),
            "nonfilm": NONFILM in (rd.get("vfx") or ""),
            "has_vfx": bool((rd.get("vfx") or "").strip()),
            "turned": bool(t and t != "-"), "turn_when": when}


def cat(rd: dict, key: str):
    return rd[key] if key in rd else cats(rd)[key]


def film_rows(rows: list, film: str) -> list:
    return [r for r in rows if r["film"] == film and not cat(r["read"], "nonfilm")]


def cmd_facets(rows: list, film: str | None, include_nonfilm: bool) -> int:
    import collections
    R = [r for r in rows if not film or r["film"].upper() == film.upper()]
    dropped = 0
    if not include_nonfilm:
        keep = [r for r in R if not cat(r["read"], "nonfilm")]
        dropped = len(R) - len(keep)
        R = keep
    if not R:
        print("no rows"); return 1
    n = len(R)
    print(f"{n} shot(s)" + (f" · {dropped} sponsor/promo shot(s) excluded" if dropped else "")
          + (f" · film {film.upper()}" if film else " · all films"))
    print("  rules: light " + " > ".join(k for k, _ in LIGHT_RULES) + " > other")
    print("         colour " + " > ".join(k for k, _ in COLOUR_RULES) + " > other")
    print("         acting " + " > ".join(k for k, _ in ACTING_RULES) + " > acts")

    def show(title, counter):
        print(f"  {title}")
        for k, v in counter.most_common():
            print(f"      {k:<18} {v:>5}  {100.0*v/n:5.1f}%")

    show("size", collections.Counter((r["read"].get("size") or "?") for r in R))
    show("angle", collections.Counter((r["read"].get("angle") or "?") for r in R))
    show("light quality", collections.Counter(cat(r["read"], "light_q") for r in R))
    show("light colour", collections.Counter(cat(r["read"], "colour") for r in R))
    show("acting", collections.Counter(cat(r["read"], "acting_b") for r in R))
    prac = sum(1 for r in R if cat(r["read"], "keyed") == "practical")
    vfx = sum(1 for r in R if cat(r["read"], "has_vfx"))
    print(f"  keyed by a source IN the scene   {prac:>5}  {100.0*prac/n:5.1f}%")
    print(f"  carries a vfx note               {vfx:>5}  {100.0*vfx/n:5.1f}%")
    T = [r for r in R if r.get("tracked")]
    if T:
        m = len(T)
        print(f"  MEASURED — shot_graph tracker (pixels), on {m} of {n} shot(s); source: "
              + "; ".join(sorted({r['tracked'].get('source', '?') for r in T}))[:160])

        def showm(title, counter):
            print(f"  {title}")
            for k, v in counter.most_common():
                print(f"      {str(k):<18} {v:>5}  {100.0*v/m:5.1f}%")

        showm("camera (8 fps track)", collections.Counter((r["tracked"]["camera"].get("family") or "?") for r in T))
        showm("light key (measured)", collections.Counter((r["tracked"]["light"].get("key") or "?") for r in T))
        showm("light temp (measured)", collections.Counter((r["tracked"]["light"].get("temp") or "?") for r in T))
        print("  READ vs MEASURED — both kept, neither wins")
        rc = collections.Counter(cat(r["read"], "colour") for r in T)
        mc = collections.Counter((r["tracked"]["light"].get("temp") or "?") for r in T)
        fmt = lambda c: " · ".join(f"{k} {100.0*v/m:.0f}%" for k, v in c.most_common(4))
        print(f"      light colour   read: {fmt(rc)}")
        print(f"                     measured: {fmt(mc)}")
        pairs = [(_coarse_fb(r.get("move_class")), _coarse_sg(r["tracked"]["camera"].get("family"))) for r in T]
        both = [(a, b) for a, b in pairs if a and b]
        same = sum(1 for a, b in both if a == b)
        print(f"      camera         film_breakdown (whole-shot solve, measured) vs shot_graph (8 fps track, "
              f"measured): same coarse class on {same} of {len(both)}"
              + (f" ({100.0*same/len(both):.0f}%)" if both else "")
              + f"; {m - len(both)} not comparable (either side unsolved)")
    cc = load_cutcheck()
    for f in sorted({r["film"] for r in R}):
        c = cc.get(f)
        if c:
            print(f"  cut check {f} — {c['method']}: {len(c['proposed_not_in_db'])} cut(s) proposed that the database "
                  f"lacks ({c['proposed_inside_split_suspect']} inside rows already flagged split_suspect), "
                  f"{len(c['disputed_db_cuts'])} database cut(s) disputed · unresolved, times in "
                  f"assets/reference-cutcheck.json")
    return 0


# ⚡ THE SEQUENCE LAYER. `facets` counts shots; `seq` looks at what FOLLOWS what. A census cannot
# see an assembly — a montage, a threshold, a reaction ring and a tribunal all dissolve into the
# same per-shot averages. Everything here reads the rows IN ORDER and reports runs, adjacency and
# cadence. Thresholds are named constants, printed with the result, for the same reason the facet
# buckets are: a run length of 4 is a choice, not a fact.
MONTAGE_MAX_DUR = 1.2      # a shot this short or shorter counts toward a montage run
MONTAGE_MIN_RUN = 4        # this many in a row IS a montage
SUSTAIN_MIN_DUR = 5.0      # a shot this long or longer counts toward a sustained run
SUSTAIN_MIN_RUN = 3
CHAPTER_MIN_RUN = 6        # a colour run this long is a chapter, not a moment


def _runs(seq):
    """[(value, start_index, length)] for consecutive equal values."""
    out = []
    for i, v in enumerate(seq):
        if out and out[-1][0] == v:
            out[-1][2] += 1
        else:
            out.append([v, i, 1])
    return [tuple(r) for r in out]


def cmd_seq(rows: list, film: str | None, include_nonfilm: bool) -> int:
    import statistics as st, collections
    films = sorted({r["film"] for r in rows}) if not film else [film.upper()]
    print(f"thresholds: montage <={MONTAGE_MAX_DUR}s x{MONTAGE_MIN_RUN}+ · "
          f"sustained >={SUSTAIN_MIN_DUR}s x{SUSTAIN_MIN_RUN}+ · chapter = colour run x{CHAPTER_MIN_RUN}+")
    for f in films:
        R = [r for r in rows if r["film"].upper() == f.upper()]
        if not include_nonfilm:
            R = [r for r in R if not cat(r["read"], "nonfilm")]
        R.sort(key=lambda r: r["n"])
        if len(R) < CHAPTER_MIN_RUN:
            print(f"\n{f}: too few rows"); continue
        n = len(R)
        print(f"\n{f}  {n} film shots · {R[0]['start']:.0f}–{R[-1]['end']:.0f}s")

        # CADENCE — median shot length in fifths, so acceleration is visible without a plot
        fifth = max(1, n // 5)
        cad = [st.median([r["dur"] for r in R[i*fifth:(i+1)*fifth]]) for i in range(5)]
        print("  cadence (median s, fifths)  " + " → ".join(f"{c:.1f}" for c in cad))

        # CHAPTERS — consecutive shots sharing a light-colour bucket
        col = [cat(r["read"], "colour") for r in R]
        chapters = [(v, i, L) for v, i, L in _runs(col) if L >= CHAPTER_MIN_RUN]
        print(f"  chapters ({len(chapters)} colour runs of {CHAPTER_MIN_RUN}+):")
        for v, i, L in chapters:
            seg = R[i:i+L]
            sizes = collections.Counter(x["read"].get("size") for x in seg).most_common(2)
            sp = sum(1 for x in seg if x["has_speech"])
            print(f"      #{seg[0]['n']:>3}–{seg[-1]['n']:<3} {L:>3} shots {sum(x['dur'] for x in seg):>6.0f}s  "
                  f"{v:<9} median {st.median([x['dur'] for x in seg]):>4.1f}s  "
                  f"{'/'.join(k for k, _ in sizes):<10} speech {100*sp//L:>3}%  "
                  f"{(seg[0]['read'].get('subject') or '')[:34]}")

        # MONTAGE and SUSTAINED runs
        for label, test, minrun in (("montage", lambda r: r["dur"] <= MONTAGE_MAX_DUR, MONTAGE_MIN_RUN),
                                    ("sustained", lambda r: r["dur"] >= SUSTAIN_MIN_DUR, SUSTAIN_MIN_RUN)):
            hits = [(i, L) for v, i, L in _runs([test(r) for r in R]) if v and L >= minrun]
            print(f"  {label} runs: {len(hits)}" + ("" if hits else "  —"))
            for i, L in hits:
                seg = R[i:i+L]
                print(f"      #{seg[0]['n']:>3}–{seg[-1]['n']:<3} {L:>3} shots {sum(x['dur'] for x in seg):>6.1f}s  "
                      f"{(seg[0]['read'].get('subject') or '')[:44]}")

        # ADJACENCY — does the cut change the size, and which pairs recur
        pairs = collections.Counter()
        same = 0
        for a, b in zip(R, R[1:]):
            sa, sb = a["read"].get("size"), b["read"].get("size")
            if sa and sb:
                pairs[(sa, sb)] += 1
                if sa == sb:
                    same += 1
        tot = sum(pairs.values())
        if tot:
            print(f"  size change across a cut: {100*(tot-same)//tot}% ({tot-same}/{tot})")
            print("      commonest pairs  " + " · ".join(f"{a}→{b} {c}" for (a, b), c in pairs.most_common(5)))
    return 0


def cmd_run(rows: list, ref: str) -> int:
    """Print a consecutive range as a shot-by-shot skeleton — the replication unit."""
    m = re.match(r"^([A-Za-z0-9_-]+)#(\d+)-(\d+)$", ref or "")
    if not m:
        print("error: range looks like FILM#A-B (e.g. F5#116-124)", file=sys.stderr); return 2
    f, a, b = m.group(1).upper(), int(m.group(2)), int(m.group(3))
    if a > b:
        a, b = b, a
    seg = sorted([r for r in rows if r["film"].upper() == f and a <= r["n"] <= b], key=lambda r: r["n"])
    if not seg:
        print(f"no rows for {ref}", file=sys.stderr); return 1
    total = sum(r["dur"] for r in seg)
    print(f"# Sequence skeleton — {f}#{a}-{b}   {len(seg)} shots · {total:.1f}s "
          f"({seg[0]['start']:.1f}–{seg[-1]['end']:.1f}s)\n")
    print(f"{'#':>4} {'dur':>5}  {'in':<9}{'move':<12} {'size':<7}{'angle':<6} light / what the performer does")
    for r in seg:
        rd = r["read"]
        print(f"{r['n']:>4} {r['dur']:>5.1f}  {(r['transition_in'] or '?'):<9}{(r['move_class'] or '?'):<12} "
              f"{(rd.get('size') or '--'):<7}{(rd.get('angle') or '--'):<6} "
              f"{rd.get('light') or (cat(rd, 'light_q') + ' · ' + cat(rd, 'colour') + ' · ' + cat(rd, 'keyed'))}")
        print(f"{'':>11}{'':<9}{'':<12} {'':<7}{'':<6} "
              f"{rd.get('acting') or (cat(rd, 'acting_b') if cat(rd, 'performer') else 'no performer')}")
    print(f"\n⛔ A SHAPE, not a script. Lengths, sizes, angles, lighting families and the order they "
          f"come in are the reusable part; the subjects are the reference's own and copying them is "
          f"imitation, not replication (`compliance.md`).")
    return 0


# ⚡ HOW THE CATEGORIES INTERACT. `cross A B` is a contingency table with LIFT: how much more (or
# less) often a value of B turns up with a value of A than it does across the whole cohort. Lift
# 2.0 means "twice as likely here as anywhere"; 0.5 means "half". A count under CROSS_MIN_N is
# printed but never starred, because a lift off four shots is an anecdote.
CROSS_MIN_N = 8
DUR_BANDS = ((1.2, "<=1.2s"), (2.5, "1.2-2.5s"), (5.0, "2.5-5s"), (1e9, ">5s"))


def _field(r: dict, prev: dict | None, name: str) -> str:
    rd = r["read"]
    if name in ("size", "angle"):
        return rd.get(name) or "?"
    if name == "light":
        return cat(rd, "light_q")
    if name == "colour":
        return cat(rd, "colour")
    if name == "acting":
        return cat(rd, "acting_b")
    if name == "move":
        return r.get("move_class") or "?"
    if name == "in":
        return r.get("transition_in") or "?"
    if name == "speech":
        return "speaks" if r.get("has_speech") else "silent"
    if name == "dur":
        return next(lbl for cap, lbl in DUR_BANDS if r["dur"] <= cap)
    if name == "keyed":
        return cat(rd, "keyed")
    if name == "world":   # does the palette CHANGE across the cut into this shot?
        if prev is None:
            return "opens"
        a = cat(prev["read"], "colour")
        b = cat(rd, "colour")
        return "same world" if a == b else "world changes"
    raise KeyError(name)


CROSS_FIELDS = ("size", "angle", "light", "colour", "acting", "move", "in", "speech", "dur", "keyed", "world")


def cmd_cross(rows: list, a_name: str, b_name: str, film: str | None) -> int:
    import collections
    if a_name not in CROSS_FIELDS or b_name not in CROSS_FIELDS:
        print(f"error: fields are {', '.join(CROSS_FIELDS)}", file=sys.stderr); return 2
    pairs = []
    for f in sorted({r["film"] for r in rows}):
        if film and f.upper() != film.upper():
            continue
        R = sorted([r for r in rows if r["film"] == f and not cat(r["read"], "nonfilm")],
                   key=lambda r: r["n"])
        prev = None
        for r in R:
            pairs.append((_field(r, prev, a_name), _field(r, prev, b_name)))
            prev = r
    n = len(pairs)
    if not n:
        print("no rows"); return 1
    A = collections.Counter(x for x, _ in pairs)
    B = collections.Counter(y for _, y in pairs)
    J = collections.Counter(pairs)
    bs = [k for k, _ in B.most_common()]
    print(f"{a_name} × {b_name} · {n} film shots" + (f" · {film.upper()}" if film else " · all films")
          + f" · cell = count (lift) · ★ lift ≥1.5 or ≤0.5 on n ≥{CROSS_MIN_N}")
    print(f"{'':<14}" + "".join(f"{b[:13]:>15}" for b in bs) + f"{'n':>7}")
    for av, ac in A.most_common():
        cells = []
        for bv in bs:
            c = J[(av, bv)]
            lift = (c / ac) / (B[bv] / n) if c else 0.0
            star = "★" if c >= CROSS_MIN_N and (lift >= 1.5 or lift <= 0.5) else " "
            cells.append(f"{c:>5} ({lift:>4.1f}){star}" if c else f"{'·':>15}")
        print(f"{av[:13]:<14}" + "".join(f"{x:>15}" for x in cells) + f"{ac:>7}")
    print(f"{'base share':<14}" + "".join(f"{100*B[b]/n:>14.1f}%" for b in bs))
    return 0


# ⛔ THE SHIFTED-COLUMN CHECK. A TSV row with one tab too few or too many still loads — it just
# puts the subject in `beat` and the beat in `vfx`, and every query over those fields is then quietly
# wrong. Four rows arrived that way in the first full read (2026-09-30) and passed every count.
SIZE_VOCAB = {"EWS", "WS", "MWS", "MS", "MCU", "CU", "XCU", "insert"}
ANGLE_VOCAB = {"eye", "low", "high", "aerial"}
VFX_WORDS = re.compile(r"(CG|NOT A FILM|particle|caption|composit|animation|UI|atmos|smoke|fog|haze|"
                       r"cut to|title|fire|explosion|sparks|effect|creature|plate|destruction|"
                       r"wireframe|robot|transition|eye|miniature|dissolv|matte|comp)", re.I)
BEAT_LOOKS_VFX = re.compile(r"^(CG |NOT A FILM|particle|on-screen|UI |OS dialog|2D |3D |volumetric|atmos)")


def lint_rows(rows: list) -> list:
    out = []
    for r in rows:
        rd, k = r["read"], f"{r['film']}#{r['n']}"
        if not any(rd.get(f) for f in READ_FIELDS):
            continue                                  # unread is a state, not a defect
        for kk in ("light_q", "colour", "acting_b"):
            if kk in rd and rd[kk] not in {n for n, _ in {"light_q": LIGHT_RULES, "colour": COLOUR_RULES,
                                                          "acting_b": ACTING_RULES}[kk]} | {"other", "acts"}:
                out.append((k, f"{kk} {rd[kk]!r} is not one of its categories"))
        if rd.get("size") not in SIZE_VOCAB:
            out.append((k, f"size {rd.get('size')!r} not in {sorted(SIZE_VOCAB)}"))
        if rd.get("angle") not in ANGLE_VOCAB:
            out.append((k, f"angle {rd.get('angle')!r} not in {sorted(ANGLE_VOCAB)}"))
        for f in (("light", "acting", "subject") if not any(k in rd for k in CAT_KEYS) else ()):
            if not (rd.get(f) or "").strip():
                out.append((k, f"{f} is empty — a shifted column?"))
        if rd.get("light") and "·" not in rd["light"]:
            out.append((k, "light has no ' · ' separators — source · quality · colour"))
        if BEAT_LOOKS_VFX.match(rd.get("beat") or ""):
            out.append((k, f"beat {rd['beat']!r} reads like a VFX note — shifted column?"))
        if rd.get("vfx") and not VFX_WORDS.search(rd["vfx"]):
            out.append((k, f"vfx {rd['vfx'][:40]!r} reads like prose — shifted column?"))
        if rd.get("expr") and rd["expr"] not in EXPR_VOCAB:
            out.append((k, f"expr {rd['expr']!r} not in the codebook"))
        if rd.get("intensity") is not None and str(rd["intensity"]) not in ("0", "1", "2", "3"):
            out.append((k, f"intensity {rd['intensity']!r} is not 0-3"))
        t = rd.get("turn")
        if t and t != "-" and not t.startswith(TURN_WHEN):
            out.append((k, f"turn {t[:30]!r} must be '-' or start with early:/late:/through:"))
        if rd.get("expr") and not cat(rd, "performer"):
            out.append((k, "an expression coded on a shot with no performer"))
    return out


def cmd_lint(rows: list) -> int:
    bad = lint_rows(rows)
    for k, why in bad:
        print(f"  {k:<14} {why}")
    print(f"{len(bad)} finding(s) over {sum(1 for r in rows if any(r['read'].get(f) for f in READ_FIELDS))} read row(s)")
    return 1 if bad else 0



DEFAULT_STRUCTURE = os.path.join(os.path.dirname(HERE), "assets", "reference-structure.json")


def cmd_structure(rows: list, film: str | None, path: str = DEFAULT_STRUCTURE) -> int:
    """Print each film's beats in story order with % of runtime RECOMPUTED from the rows. The
    asset stores only (shot, beat, note): a percentage typed by hand is how a beat map drifts."""
    if not os.path.isfile(path):
        print(f"no structure asset at {path}", file=sys.stderr); return 1
    beats = json.load(open(path, encoding="utf-8"))["beats"]
    bad = 0
    for f, B in beats.items():
        if film and f.upper() != film.upper():
            continue
        R = [r for r in rows if r["film"] == f and not cat(r["read"], "nonfilm")]
        if not R:
            print(f"{f}: no rows"); bad += 1; continue
        T = max(r["end"] for r in R); idx = {r["n"]: r for r in R}
        print(f"\n{f}  {T:.0f} s of film")
        for n, kind, *rest in sorted(B, key=lambda b: idx[b[0]]["start"] if b[0] in idx else 1e9):
            note = rest[0] if rest else ""
            r = idx.get(n)
            if r is None:
                print(f"  ⛔ #{n} {kind}: no such film shot"); bad += 1; continue
            rd = r["read"]
            print(f"  {100 * r['start'] / T:5.1f}%  #{n:<4} {kind:<10} {note[:52]:<52} "
                  f"{rd.get('size') or '':<6} I{rd.get('intensity') or '-'} {rd.get('expr') or ''}")
    pairs = json.load(open(path, encoding="utf-8")).get("setups", {}).get("pairs", [])
    shown = [q for q in pairs if not film or q[0].upper() == film.upper()]
    if shown:
        print("\nSETUP → PAYOFF   (positions recomputed; kind = what carries it)")
    for f, a, b, kind, *rest in shown:
        note = rest[0] if rest else ""
        R = [r for r in rows if r["film"] == f and not cat(r["read"], "nonfilm")]
        idx = {r["n"]: r for r in R}
        if a not in idx or b not in idx:
            print(f"  ⛔ {f}#{a}→#{b}: no such film shot"); bad += 1; continue
        T = max(r["end"] for r in R)
        pa, pb = 100 * idx[a]["start"] / T, 100 * idx[b]["start"] / T
        print(f"  {f:<11} #{a:<4}{pa:5.1f}% → #{b:<4}{pb:5.1f}%  gap {pb - pa:5.1f}  {kind:<11} {note[:60]}")
    return 1 if bad else 0


SIZE_ORDER = {"EWS": 0, "WS": 1, "MWS": 2, "MS": 3, "MCU": 4, "CU": 5, "XCU": 6}


def chain_stats(R: list) -> dict:
    """What CARRIES across a cut, for one film's rows in order. Pure: rows in, numbers out, so the
    selftest can pin it and every published chaining figure can be re-derived."""
    import statistics as st, collections
    I = lambda r: int(r["read"]["intensity"]) if str(r["read"].get("intensity") or "") in "0123" \
        and r["read"].get("intensity") not in (None, "") else None
    col = lambda r: cat(r["read"], "colour")
    perf = [r for r in R if I(r) is not None]
    steps = collections.Counter(abs(I(b) - I(a)) for a, b in zip(perf, perf[1:]))
    # ⛔ The jumps are counted on the SAME pairs as the step distribution — consecutive performer
    # shots, an insert between them skipped. Counting them on strictly adjacent rows (the first
    # version) printed "±2 13%" and "22 jumps" for one film from two different denominators.
    big = [(a, b) for a, b in zip(perf, perf[1:]) if abs(I(b) - I(a)) >= 2]
    sz = [r for r in R if r["read"].get("size") in SIZE_ORDER]
    sd = [SIZE_ORDER[b["read"]["size"]] - SIZE_ORDER[a["read"]["size"]] for a, b in zip(sz, sz[1:])]
    off = [(a, b) for a, b in zip(R, R[1:]) if a["read"].get("angle") in ("low", "high")]
    turns = [(a, b) for a, b in zip(R, R[1:]) if cat(a["read"], "turned")
             and not a.get("split_suspect") and not b.get("split_suspect")]
    return {
        "perf_cuts": sum(steps.values()),
        "step": {k: steps.get(k, 0) for k in range(4)},
        "big_jumps": len(big),
        "big_at_palette_change": sum(1 for a, b in big if col(a) != col(b)),
        # the BASE RATE the line above must beat: how often ANY performer-to-performer cut changes
        # colour family. Without it "most jumps sit at a palette change" is unfalsifiable in a
        # film whose palette changes every few shots.
        "palette_change_pairs": sum(1 for a, b in zip(perf, perf[1:]) if col(a) != col(b)),
        # a jump UP that cuts tighter, or DOWN that cuts wider: the frame size moves WITH the
        # intensity. Counted only where both sizes are on the ladder (an insert is not).
        "big_size_with": sum(1 for a, b in big if a["read"].get("size") in SIZE_ORDER
                             and b["read"].get("size") in SIZE_ORDER
                             and (SIZE_ORDER[b["read"]["size"]] - SIZE_ORDER[a["read"]["size"]])
                             * (I(b) - I(a)) > 0),
        "big_size_known": sum(1 for a, b in big if a["read"].get("size") in SIZE_ORDER
                              and b["read"].get("size") in SIZE_ORDER),
        # the same test on steps of ONE — the comparison that says whether the big jumps are special
        "one_size_with": sum(1 for a, b in zip(perf, perf[1:]) if abs(I(b) - I(a)) == 1
                             and a["read"].get("size") in SIZE_ORDER and b["read"].get("size") in SIZE_ORDER
                             and (SIZE_ORDER[b["read"]["size"]] - SIZE_ORDER[a["read"]["size"]])
                             * (I(b) - I(a)) > 0),
        "one_size_known": sum(1 for a, b in zip(perf, perf[1:]) if abs(I(b) - I(a)) == 1
                              and a["read"].get("size") in SIZE_ORDER and b["read"].get("size") in SIZE_ORDER),
        "size_cuts": len(sd),
        "size_step": {"same": sum(1 for x in sd if x == 0), "1": sum(1 for x in sd if abs(x) == 1),
                      "2": sum(1 for x in sd if abs(x) == 2), "3+": sum(1 for x in sd if abs(x) >= 3),
                      "in": sum(1 for x in sd if x > 0), "out": sum(1 for x in sd if x < 0)},
        "off_eye": len(off),
        "off_eye_answered": sum(1 for a, b in off if b["read"].get("angle") in ("low", "high")
                                and b["read"]["angle"] != a["read"]["angle"]),
        "after_turn_median": round(st.median([b["dur"] for a, b in turns]), 2) if turns else None,
        "film_median": round(st.median([r["dur"] for r in R]), 2) if R else None,
    }


def cmd_chain(rows: list, film: str | None) -> int:
    films = sorted({r["film"] for r in rows}) if not film else [film.upper()]
    print("what carries across a cut — film shots only, sponsor tail dropped, split_suspect kept out of timing")
    for f in films:
        R = sorted([r for r in rows if r["film"].upper() == f.upper()
                    and not cat(r["read"], "nonfilm")], key=lambda r: r["n"])
        if len(R) < 2:
            print(f"{f}: too few rows"); continue
        c = chain_stats(R); n = c["perf_cuts"] or 1; m = c["size_cuts"] or 1; ss = c["size_step"]
        print(f"\n{f}")
        # ⛔ the counts ride along with the rarest bins: one 0→3 in 203 cuts prints as "0%", and a
        # published "only in F4" was wrong for exactly that reason (caught 2026-09-30)
        print(f"  performance  same {100*c['step'][0]/n:3.0f}% · ±1 {100*c['step'][1]/n:3.0f}% · "
              f"±2 {100*c['step'][2]/n:3.0f}% ({c['step'][2]}) · ±3 {100*c['step'][3]/n:3.0f}% ({c['step'][3]})"
              f"   ({n} cuts between performer shots)")
        bj = c["big_jumps"] or 1
        print(f"               jumps of 2+: {c['big_jumps']}, of which at a palette change: {c['big_at_palette_change']}"
              f" ({100*c['big_at_palette_change']/bj:.0f}% — vs {100*c['palette_change_pairs']/n:.0f}% of all performer cuts)")
        print(f"               the frame moves with the jump (up → tighter, down → wider): "
              f"{c['big_size_with']} of {c['big_size_known']} jumps of 2+ · {c['one_size_with']} of "
              f"{c['one_size_known']} steps of 1 (both sizes on the ladder)")
        print(f"  shot size    same {100*ss['same']/m:3.0f}% · 1 step {100*ss['1']/m:3.0f}% · "
              f"2 steps {100*ss['2']/m:3.0f}% · 3+ {100*ss['3+']/m:3.0f}%   in {ss['in']} / out {ss['out']}")
        print(f"  angle        off eye level {c['off_eye']} · answered by the opposite angle {c['off_eye_answered']}")
        print(f"  timing       shot after a turn: median {c['after_turn_median']} s vs film {c['film_median']} s")
    return 0


def cmd_card(rows: list, ref: str) -> int:
    m = REF_RE.match(ref)
    if not m:
        print("error: reference looks like FILM#N (e.g. F4#82)", file=sys.stderr); return 2
    film, n = m.group(1).upper(), int(m.group(2))
    r = next((x for x in rows if x["film"].upper() == film and x["n"] == n), None)
    if not r:
        print(f"no row for {ref}", file=sys.stderr); return 1
    rd = r["read"]
    pal = " ".join(r["palette"][:3])
    print(f"# Reference card — {r['film']}#{r['n']}   {r['start']:.1f}–{r['end']:.1f}s ({r['dur']:.2f}s)\n")
    print("MEASURED  " + f"in {r['transition_in']} · out {r['transition_out']} · move {r['move']!r}")
    print("          " + f"camera {r['cam_rate']}/s · subject {r['subject_residual']} · luma {r['luma']} · {pal}")
    print("          " + f"speech {r['speech_words']}w ({r['speech_wps']}/s)")
    shown = [k for k in READ_FIELDS if rd.get(k)] + [k for k in CAT_KEYS if k in rd and rd[k] not in (None, "")]
    print("READ      " + (" · ".join(f"{k}: {rd[k]}" for k in shown) or "— not read") + "\n")
    turn = rd.get("turn")
    when = turn.split(":", 1)[0] if turn and turn != "-" else cat(rd, "turn_when")
    what = turn.split(":", 1)[1].strip() if (turn and turn != "-") else "the performance changes"
    lvl = {"0": "blank", "1": "restrained — only the eyes or mouth carry it",
           "2": "open — the face moves, clearly readable", "3": "peak — full release"}
    print("[PERFORMANCE]")
    if rd.get("expr"):
        print(f"{rd['expr']}, intensity {rd.get('intensity')} ({lvl.get(str(rd.get('intensity')), '?')})")
        print(f"what the body does: {rd.get('acting') or cat(rd, 'acting_b')}")
        if when:
            at = {"early": "in the FIRST half of the shot", "late": "in the LAST half of the shot — "
                  "the head of the shot holds the state before it", "through": "continuously, across "
                  "the whole shot"}[when]
            print(f"the turn: {what} — {at}")
        else:
            print("the turn: none — the performance holds one state for the whole shot")
    else:
        print("no performer" if not cat(rd, "performer") else "<not coded>")
    print()
    print("[MOTION]")
    print(f"START: {rd.get('subject') or '<what is in frame at the first frame — yours, not the reference’s>'}")
    if when == "late":
        print(f"MID:   the state holds — the reference spends the first half of {r['dur']:.1f}s NOT changing")
        print(f"END:   {what}\n")
    elif when in ("early", "through"):
        print(f"MID:   {what}")
        print("END:   <where it comes to rest>\n")
    else:
        print(f"MID:   <the one action — the reference spends {r['dur']:.1f}s on it>")
        print("END:   <where it comes to rest>\n")
    print("[CAMERA]")
    print(f"{rd.get('angle') or '<height/angle>'}, {rd.get('size') or '<size>'}, "
          + ("locked off" if r["move_class"] == "locked off" else f"{r['move']}") + "\n")
    print("[COLORS]")
    print(f"{pal}  (luma {r['luma']})\n")
    print(f"⛔ A SKELETON, not a prompt. It carries the reference's SHAPE — length, move, entry and "
          f"exit, palette, whether anyone speaks. The subject is yours: copying the reference's "
          f"content is not replication, it is imitation, and `compliance.md` governs it. "
          f"Length note: {r['dur']:.1f}s"
          + (" — past a single generation, so it is a shot to BUILD, not to prompt."
             if r["dur"] > 10 else "."))
    return 0


def cmd_batch(rows: list, path: str, db: str) -> int:
    """Annotate many shots at once from a TSV: FILM#N <tab> size <tab> angle <tab> light <tab>
    acting <tab> subject [<tab> beat [<tab> vfx]]. Reading 1,100 shots one CLI call at a time is
    not a workflow; a sheet of 25 frames is read in one look and written in one line each.
    A '-' in a column leaves that field untouched.
    ⛔ PREFER A '#cols:' HEADER (e.g. '#cols: expr intensity turn'). Positional columns are how four
    rows got a subject in `beat` in the first full read; a named header cannot slip."""
    idx = {f"{r['film'].upper()}#{r['n']}": r for r in rows}
    cols = ("size", "angle", "light", "acting", "subject", "beat", "vfx")
    n = miss = 0
    seen = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip() or (line.lstrip().startswith("#") and not line.startswith("#cols:")):
                continue
            if line.startswith("#cols:"):
                named = [c.strip() for c in line[6:].split() if c.strip()]
                unknown = [c for c in named if c not in READ_FIELDS]
                if unknown:
                    print(f"error: #cols names unknown field(s) {unknown}", file=sys.stderr); return 2
                cols = tuple(named); continue
            parts = line.split("\t")
            key = parts[0].strip().upper()
            seen.add(key)
            r = idx.get(key)
            if r is None:
                miss += 1; continue
            for i, c in enumerate(cols, start=1):
                if i < len(parts):
                    v = parts[i].strip()
                    if v and v != "-":
                        r["read"][c] = v
            n += 1
    save(db, rows)
    print(f"annotated {n} shot(s)" + (f" · {miss} reference(s) matched no row" if miss else ""))
    touched = [r for r in rows if f"{r['film'].upper()}#{r['n']}" in seen]
    bad = lint_rows(touched)
    for k, why in bad:
        print(f"  ⛔ {k:<14} {why}")
    if bad:
        print(f"⛔ {len(bad)} suspect field(s) in this batch — written, but check the TSV's tab count")
        return 1
    return 0 if n else 1


def cmd_annotate(rows: list, a, db: str) -> int:
    m = REF_RE.match(a.ref)
    if not m:
        print("error: reference looks like FILM#N", file=sys.stderr); return 2
    film, n = m.group(1).upper(), int(m.group(2))
    hit = None
    for r in rows:
        if r["film"].upper() == film and r["n"] == n:
            hit = r; break
    if hit is None:
        print(f"no row for {a.ref}", file=sys.stderr); return 1
    for k in READ_FIELDS:
        v = getattr(a, k, None)
        if v is not None:
            hit["read"][k] = v
    save(db, rows)
    print(f"{a.ref}: " + " · ".join(f"{k}={hit['read'].get(k) or '—'}" for k in READ_FIELDS))
    return 0


def selftest() -> int:
    import contextlib, io, tempfile
    assert move_class("slow: push in x1.21 + pan left 7%W") == "push in+pan"
    assert move_class("locked off") == "locked off"
    assert move_class("UNRELIABLE (5 inliers) — rate 0.1/s") == "unsolved"
    assert move_class("handheld/shake") == "handheld"
    segs = [{"start": 0.0, "end": 2.0, "text": "one two three four"},
            {"start": 5.0, "end": 6.0, "text": "five six"}]
    assert speech_in(segs, 0.0, 2.0) == (4.0, 2.0)
    assert speech_in(segs, 1.0, 2.0)[0] == 2.0          # half the segment → half the words
    assert speech_in(segs, 2.5, 4.0) == (0.0, 0.0)
    # a TEXT-FREE index (counts only) is the shipping form: the lines never leave their film
    assert speech_in([{"start": 0.0, "end": 2.0, "words": 4}], 0.0, 2.0) == (4.0, 2.0)
    with tempfile.TemporaryDirectory() as td:
        src, tr = os.path.join(td, "b"), os.path.join(td, "t")
        os.makedirs(src); os.makedirs(tr)
        json.dump({"label": "TESTFILM", "duration": 10.0, "rows": [
            {"n": 1, "start": 0.0, "end": 4.0, "dur": 4.0, "move": "locked off", "per_s": 0.001,
             "residual": 0.02, "luma": 90.0, "palette": ["#111111"], "transition_in": "open",
             "transition_out": "cut"},
            {"n": 2, "start": 4.0, "end": 10.0, "dur": 6.0, "move": "slow: push in x1.2",
             "per_s": 0.02, "residual": 0.01, "luma": 40.0, "palette": ["#222222"],
             "transition_in": "cut", "transition_out": "end", "split_suspect": 2},
            {"n": 3, "start": 10.0, "end": 10.0, "dur": 0.0}]},      # a zero row must be dropped
            open(os.path.join(src, "BREAKDOWN-TESTFILM.json"), "w"))
        json.dump({"segments": [{"start": 0.5, "end": 1.5, "text": "a b c d"}]},
                  open(os.path.join(tr, "TESTFILM.json"), "w"))
        db = os.path.join(td, "db.jsonl")
        rows = build(src, tr, db)
        assert len(rows) == 2, rows
        assert rows[0]["has_speech"] and rows[0]["speech_words"] == 4.0, rows[0]
        assert not rows[1]["has_speech"]
        assert rows[1]["move_class"] == "push in"
        assert rows[1]["split_suspect"] is True and rows[0]["split_suspect"] is False, \
            "build must CARRY film_breakdown's split_suspect flag — dropping it made a split shot 'reliable'"
        class A:  # annotate, then REBUILD — a hand-written read must survive the rebuild
            ref = "TESTFILM#2"; size = "CU"; angle = "low"; subject = "a face"; beat = None
            vfx = None; notes = None
        cmd_annotate(rows, A, db)
        again = build(src, tr, db)
        r2 = [r for r in again if r["n"] == 2][0]
        assert r2["read"]["size"] == "CU" and r2["read"]["angle"] == "low", r2["read"]
        assert r2["read"]["beat"] is None
        tsv = os.path.join(td, "ann.tsv")
        open(tsv, "w").write("# comment\n\nTESTFILM#1\tWS\thigh\tovercast · flat · cool\tholds still\ta field\n"
                             "TESTFILM#2\t-\t-\tlamp · low-key, single source · warm\tsits\ta face\n"
                             "NOFILM#9\tCU\t-\t-\t-\t-\n")
        assert cmd_batch(rows, tsv, db) == 0
        r1 = [r for r in rows if r["n"] == 1][0]
        assert r1["read"]["size"] == "WS" and r1["read"]["light"] == "overcast · flat · cool", r1["read"]
        r2b = [r for r in rows if r["n"] == 2][0]
        assert r2b["read"]["light"] == "lamp · low-key, single source · warm"
        assert r2b["read"]["size"] == "CU", "a '-' must LEAVE the earlier value alone"
        # a '#cols:' header names the columns — the fix for positional slips
        hdr = os.path.join(td, "hdr.tsv")
        open(hdr, "w").write("#cols: expr intensity turn\nTESTFILM#1\tresolve\t2\tlate: jaw sets\n")
        with contextlib.redirect_stdout(io.StringIO()):
            assert cmd_batch(rows, hdr, db) == 0
        r1h = [r for r in rows if r["n"] == 1][0]["read"]
        assert (r1h["expr"], r1h["intensity"], r1h["turn"]) == ("resolve", "2", "late: jaw sets"), r1h
        assert r1h["size"] == "WS", "a named header must not touch columns it does not name"
        open(hdr, "w").write("#cols: expr mood\nTESTFILM#1\tjoy\tup\n")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            assert cmd_batch(rows, hdr, db) == 2, "an unknown column name must refuse, not guess"
        badp = {"film": "T", "n": 9, "read": {"size": "MS", "angle": "eye", "light": "a · b · c",
                "acting": "sits", "subject": "x", "expr": "melancholy", "intensity": "5", "turn": "at the end he looks"}}
        assert len(lint_rows([badp])) == 3, lint_rows([badp])
        r1h.update(expr=None, intensity=None, turn=None)
        # batch-time lint must FIRE on a shifted column (subject slid into beat), then restore the row
        saved = dict(r2b["read"])
        bad_tsv = os.path.join(td, "bad.tsv")
        open(bad_tsv, "w").write("TESTFILM#2\tMS\teye\tlamp · soft · warm\ta kart runs\t\tCG kart\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert cmd_batch(rows, bad_tsv, db) == 1, "a shifted column must make batch exit 1"
        assert "reads like a VFX note" in buf.getvalue(), buf.getvalue()
        r2b["read"].clear(); r2b["read"].update(saved)   # batch cannot CLEAR a field, by design
        class Q:
            film = None; move = "push in"; min_dur = None; max_dur = None; transition_in = None
            transition_out = None; speech = "no"; unread = False; limit = 10; json = False
            size = None; angle = None; light = None; acting = None; subject = None
            beat = None; vfx = None; notes = None
        assert cmd_query(again, Q) == 0
        Q.move = "handheld"
        assert cmd_query(again, Q) == 1, "no match must exit 1"
        # a read field on `query` must FILTER — it used to parse and do nothing
        Q.move = None; Q.speech = None; Q.size = "CU"
        assert sum(1 for r in again if match(r, Q)) == 1, "--size must select, not pass everything"
        Q.size = "cu"
        assert sum(1 for r in again if match(r, Q)) == 1, "read filters are case-insensitive"
        # `again` is a stale in-memory rebuild; the TSV light values live on `rows`
        Q.size = None; Q.light = "low-key"
        assert sum(1 for r in rows if match(r, Q)) == 1, "--light must match inside the sentence"
        Q.light = "no such light"
        assert sum(1 for r in rows if match(r, Q)) == 0
        Q.light = None
        # facets: the buckets are ORDERED, and the sponsor tail must actually be dropped
        assert _bucket("hard backlight · silhouette · cool", LIGHT_RULES, "other") == "hard/directional"
        assert _bucket("flat institutional light · shadowless · white", LIGHT_RULES, "other") == "shadowless", \
            "shadowless is checked BEFORE flat — order is the rule"
        assert _bucket("bedside lamp · single source · warm", LIGHT_RULES, "other") == "single source"
        assert _bucket("window daylight · soft side key · warm", LIGHT_RULES, "other") == "soft", \
            "a soft key must not fall into hard/directional"
        assert _bucket("none · black frame", LIGHT_RULES, "other") == "none"
        assert _bucket("soft frontal · shallow · warm", LIGHT_RULES, "other") == "soft"
        assert _bucket("no performer", ACTING_RULES, "acts") == "no performer"
        assert _bucket("stands still, chin lifted, gaze held", ACTING_RULES, "acts") == "holds still"
        assert _bucket("she walks away and does not look back", ACTING_RULES, "acts") == "acts", \
            "a walk-away is acting — 'does not move' is the keyword, not 'does not'"
        assert _bucket("he hurls an armful of leaves into the air", ACTING_RULES, "acts") == "acts"
        rows[0]["read"]["vfx"] = NONFILM + " — sponsor card"
        rows[0]["read"]["light"] = "graphic card · flat · black"
        rows[1]["read"]["light"] = "single candle from below-front · hard falloff · warm"
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_facets(rows, None, False)
        out = buf.getvalue()
        assert "1 shot(s) · 1 sponsor/promo shot(s) excluded" in out, out
        assert "graphic card" not in out and "hard/directional" in out, out
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_facets(rows, None, True)
        assert "2 shot(s)" in buf.getvalue() and "excluded" not in buf.getvalue()
        # seq: runs must be CONSECUTIVE, and `run` must refuse a bad range
        assert _runs([1, 1, 2, 2, 2, 1]) == [(1, 0, 2), (2, 2, 3), (1, 5, 1)]
        assert _runs([]) == []
        assert cmd_run(rows, "TESTFILM#1") == 2, "a single ref is not a range"
        assert cmd_run(rows, "NOFILM#1-9") == 1, "an unknown film must exit 1"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert cmd_run(rows, "TESTFILM#2-1") == 0, "a reversed range must still work"
        assert "TESTFILM#1-2   2 shots" in buf.getvalue(), buf.getvalue()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_seq(rows, "TESTFILM", True)
        assert "too few rows" in buf.getvalue(), "2 rows is under CHAPTER_MIN_RUN — say so, do not invent chapters"
        # structure: % is recomputed from rows, and a beat on a missing shot must FAIL
        # card: a LATE turn must be written as hold-then-change, not as a mid-shot action
        rows[1]["read"].update(expr="grief", intensity="3", turn="late: the stare collapses into crying",
                               acting="stares, then breaks")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert cmd_card(rows, "TESTFILM#2") == 0
        c = buf.getvalue()
        assert "NOT changing" in c and "END:   the stare collapses into crying" in c, c
        assert "intensity 3 (peak" in c, c
        rows[1]["read"].update(expr=None, intensity=None, turn=None)
        rows[0]["read"]["vfx"] = None     # the facets test above turned row 1 into sponsor packaging
        # chain: a hand-built four-shot film whose every figure is known in advance
        mk = lambda n, size, ang, i, turn, dur, light: {"film": "C", "n": n, "dur": dur,
            "read": {"size": size, "angle": ang, "intensity": i, "turn": turn,
                     "light": light, "vfx": None}}
        C = [mk(1, "WS", "eye", "0", "-", 4.0, "lamp · soft · warm"),
             mk(2, "MCU", "low", "1", "late: x", 3.0, "lamp · soft · warm"),
             mk(3, "MCU", "high", "3", "-", 2.0, "sky · flat · cool"),
             mk(4, "CU", "eye", "3", "-", 5.0, "sky · flat · cool")]
        k = chain_stats(C)
        assert k["step"] == {0: 1, 1: 1, 2: 1, 3: 0}, k["step"]
        assert k["big_jumps"] == 1 and k["big_at_palette_change"] == 1, k
        assert k["size_step"]["same"] == 1 and k["size_step"]["3+"] == 1 and k["size_step"]["1"] == 1, k
        assert k["off_eye"] == 2 and k["off_eye_answered"] == 1, "low then high IS an answered pair"
        assert k["after_turn_median"] == 2.0, "the shot after the turn shot is #3, 2.0 s"
        D = [mk(1, "MCU", "eye", "0", "-", 3.0, "lamp · soft · warm"),
             mk(2, "INSERT", "high", None, "-", 1.0, "sky · flat · cool"),
             mk(3, "CU", "eye", "2", "-", 3.0, "sky · flat · cool")]
        kd = chain_stats(D)
        assert kd["step"][2] == 1 and kd["big_jumps"] == 1 and kd["big_at_palette_change"] == 1, \
            "a jump across an insert is ONE jump, counted on the same pairs as the step table"
        assert kd["palette_change_pairs"] == 1 and k["palette_change_pairs"] == 1, (k, kd)
        assert kd["big_size_with"] == 1 and kd["big_size_known"] == 1, "0→2 from MCU to CU cuts tighter"
        assert k["big_size_with"] == 0 and k["big_size_known"] == 1, "1→3 on MCU→MCU does not move"
        assert k["one_size_with"] == 1 and k["one_size_known"] == 1, "0→1 on WS→MCU cuts tighter"
        sp = os.path.join(td, "struct.json")
        json.dump({"beats": {"TESTFILM": [[2, "climax", "x"], [1, "hook", "y"]]}}, open(sp, "w"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert cmd_structure(rows, None, sp) == 0
        out = buf.getvalue()
        assert out.index("hook") < out.index("climax"), "beats print in STORY order, not file order"
        assert "40.0%" in out, out   # shot 2 starts at 4.0 s of a 10 s film
        json.dump({"beats": {"TESTFILM": [[99, "climax", "x"]]}}, open(sp, "w"))
        with contextlib.redirect_stdout(io.StringIO()):
            assert cmd_structure(rows, None, sp) == 1, "a beat pinned to a shot that does not exist must fail"
        # lint: a SHIFTED column must be caught, a clean row must not be
        good = {"film": "T", "n": 1, "read": {"size": "MS", "angle": "eye", "light": "lamp · soft · warm",
                "acting": "sits", "subject": "a man", "beat": None, "vfx": "CG sky", "notes": None}}
        shifted = {"film": "T", "n": 2, "read": {"size": "MS", "angle": "eye", "light": "lamp · soft · warm",
                   "acting": "a kart runs", "subject": "", "beat": "CG kart", "vfx": None, "notes": None}}
        prose = {"film": "T", "n": 3, "read": {"size": "CU", "angle": "eye", "light": "lamp · soft · warm",
                 "acting": "hands", "subject": "dressing", "beat": None, "vfx": "0.3s insert run", "notes": None}}
        offvocab = {"film": "T", "n": 4, "read": {"size": "close", "angle": "slightly low",
                    "light": "lamp · soft · warm", "acting": "x", "subject": "y", "beat": None, "vfx": None, "notes": None}}
        assert lint_rows([good]) == [], lint_rows([good])
        w = " ".join(why for _, why in lint_rows([shifted]))
        assert "subject is empty" in w and "reads like a VFX note" in w, w
        assert any("reads like prose" in why for _, why in lint_rows([prose]))
        assert len(lint_rows([offvocab])) == 2, "an off-vocabulary size AND angle are two findings"
        # attach: the tracker's block goes BESIDE the read, refuses a cut list that is not the
        # database's own, survives a rebuild only while its shot did not move
        J = {"cuts_source": "cut list t.txt", "cuts_confirmed": True,
             "shots": [{"n": 1, "start": 0.0, "end": 4.0, "camera": {"family": "locked", "category": "locked"},
                        "light": {"key": "low-key", "temp": "warm"}, "composition": {"dof": "deep"}},
                       {"n": 2, "start": 4.0, "end": 10.0, "camera": {"family": "push", "category": "push"},
                        "light": {"key": "mid-key", "temp": "neutral"}}],
             "cuts": [{"n": 1, "from": 1, "to": 2, "look": "unalike", "delta_e": 20.1, "flags": []}]}
        strip = lambda R: json.dumps([{k: v for k, v in r.items() if k != "tracked"} for r in R], sort_keys=True)
        before = strip(rows)
        assert attach_tracked(rows, J, "TESTFILM", "selftest") == 2
        assert strip(rows) == before, "attach must touch only `tracked`"
        assert rows[1]["tracked"]["join_in"]["look"] == "unalike" and "join_in" not in rows[0]["tracked"]
        bad = json.loads(json.dumps(J)); bad["shots"][1]["start"] = 5.0
        try:
            attach_tracked(rows, bad, "TESTFILM", "x"); raise AssertionError("a shifted shot must refuse")
        except SystemExit as e:
            assert "line up" in str(e), e
        try:
            attach_tracked(rows, dict(J, shots=J["shots"][:1]), "TESTFILM", "x")
            raise AssertionError("a different shot count must refuse")
        except SystemExit as e:
            assert "own cut list" in str(e), e
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_facets(rows, "TESTFILM", True)
        out = buf.getvalue()
        assert "MEASURED — shot_graph tracker (pixels), on 2 of 2" in out and "READ vs MEASURED" in out, out
        assert "light colour   read:" in out and "measured: warm 50% · neutral 50%" in out, out
        assert "same coarse class on 2 of 2 (100%)" in out, out
        save(db, rows)
        assert build(src, tr, db)[1]["tracked"]["camera"]["family"] == "push", "an unmoved shot keeps its block"
        bp = os.path.join(src, "BREAKDOWN-TESTFILM.json"); B = json.load(open(bp))
        B["rows"][0]["end"] = B["rows"][1]["start"] = 4.5
        B["rows"][0]["dur"], B["rows"][1]["dur"] = 4.5, 5.5
        json.dump(B, open(bp, "w"))
        assert not any(r.get("tracked") for r in build(src, tr, db)), "a moved shot must drop its block"
    # (3.0.0) THE SHIPPED SET: numbers and category labels only, the films by code, and every report runs on it
    PROSE = ("subject", "acting", "beat", "notes", "turn", "light", "vfx")
    ship = load(DEFAULT_DB)
    assert ship and {r["film"] for r in ship} <= {"F1", "F2", "F3", "F4", "F5"}, {r["film"] for r in ship}
    assert not [r for r in ship if any(k in r["read"] for k in PROSE)], "a written read survives in the shipped set"
    assert all(set(CAT_KEYS) <= set(r["read"]) for r in ship), "every shipped row carries its category labels"
    assert len({cat(r["read"], "colour") for r in ship}) > 2 and any(cat(r["read"], "keyed") == "practical" for r in ship) \
        and any(cat(r["read"], "turned") for r in ship), "the stored labels are what the reports read"
    st_ = json.load(open(DEFAULT_STRUCTURE, encoding="utf-8"))
    codes = {"F1", "F2", "F3", "F4", "F5"}
    assert set(st_["beats"]) <= codes and {q[0] for q in st_["setups"]["pairs"]} <= codes, "structure: films by code"
    assert set(json.load(open(DEFAULT_CUTCHECK, encoding="utf-8"))["films"]) <= codes, "cut check: films by code"
    assert all(len(b) == 2 for B in st_["beats"].values() for b in B), "beats are (shot, kind) only"
    assert all(len(q) == 4 for q in st_["setups"]["pairs"]), "setups are (film, setup, payoff, kind) only"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rcs = [cmd_stats(ship, None), cmd_facets(ship, None, False), cmd_seq(ship, None, False),
               cmd_run(ship, "F2#100-104"), cmd_cross(ship, "size", "light", None), cmd_lint(ship),
               cmd_structure(ship, None), cmd_chain(ship, None), cmd_card(ship, "F2#190")]
    assert rcs[5] == 0 and rcs[6] == 0 and rcs[8] == 0, rcs
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_run(ship, "F2#100-104")
    out_ = buf.getvalue()
    cbuf = io.StringIO()
    with contextlib.redirect_stdout(cbuf):
        cmd_card(ship, "F2#190")
    assert "subject:" not in cbuf.getvalue() and "light_q:" in cbuf.getvalue(), "card shows labels, never an empty prose field"
    assert "—\n" not in out_ and any(f"{n} · " in out_ for n, _ in LIGHT_RULES), "run prints the light labels, never an empty read"
    print("selftest OK — move classing, speech overlap (incl. partial segments), build drops a "
          "zero-length row, annotations SURVIVE a rebuild, query match/no-match exit codes, "
          "facet buckets are ordered, facets drops the sponsor tail unless asked not to, "
          "read fields FILTER on query, seq runs are consecutive, run refuses a bad range, "
          "lint catches a shifted column, #cols headers name the columns, the performance codebook is linted, build carries split_suspect, structure recomputes % and fails on a missing shot, card writes a late turn as hold-then-change, chain figures pinned on a known film, "
          "attach puts the tracker's block beside the read (refuses a cut list that is not the database's own, "
          "keeps it through a rebuild only while the shot did not move), facets prints read and measured side by side")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["build", "stats", "query", "card", "annotate", "batch", "facets", "seq", "run", "cross", "lint", "structure", "chain", "attach"])
    ap.add_argument("ref", nargs="?", help="FILM#N for card/annotate · FILM#A-B for run")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--from", dest="src", help="folder of BREAKDOWN-*.json")
    ap.add_argument("--transcripts", help="folder of <FILM>.json transcripts (word counts only)")
    ap.add_argument("--film"); ap.add_argument("--move")
    ap.add_argument("--min-dur", type=float); ap.add_argument("--max-dur", type=float)
    ap.add_argument("--transition-in"); ap.add_argument("--transition-out")
    ap.add_argument("--speech", choices=["yes", "no"])
    ap.add_argument("--unread", action="store_true", help="only rows nobody has looked at yet")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--source", help="attach: the source tag for the tracked block (default: from the JOINS file)")
    ap.add_argument("--include-nonfilm", action="store_true",
                    help="facets: keep the sponsor/promo tail instead of dropping it")
    for k in READ_FIELDS:
        ap.add_argument(f"--{k}")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help(); return 2
    if a.cmd == "build":
        if not a.src:
            print("error: build needs --from", file=sys.stderr); return 2
        rows = build(a.src, a.transcripts, a.db)
        print(f"{len(rows)} shots → {a.db}")
        return 0
    rows = load(a.db)
    if not rows:
        print(f"no database at {a.db} — run `film_db.py build --from <breakdowns/>`", file=sys.stderr)
        return 1
    if a.cmd == "stats":
        return cmd_stats(rows, a.film)
    if a.cmd == "chain":
        return cmd_chain(rows, a.film)
    if a.cmd == "structure":
        return cmd_structure(rows, a.film)
    if a.cmd == "lint":
        return cmd_lint(rows)
    if a.cmd == "cross":
        parts = (a.ref or "").split(":")
        if len(parts) != 2:
            print("error: cross takes A:B, e.g. cross size:light", file=sys.stderr); return 2
        return cmd_cross(rows, parts[0], parts[1], a.film)
    if a.cmd == "seq":
        return cmd_seq(rows, a.film, a.include_nonfilm)
    if a.cmd == "run":
        return cmd_run(rows, a.ref or "")
    if a.cmd == "facets":
        return cmd_facets(rows, a.film, a.include_nonfilm)
    if a.cmd == "attach":
        if not (a.ref and a.film):
            print("error: attach takes JOINS-<FILM>.json --film FILM", file=sys.stderr); return 2
        return cmd_attach(rows, a.ref, a.film, a.db, a.source)
    if a.cmd == "query":
        return cmd_query(rows, a)
    if a.cmd == "card":
        return cmd_card(rows, a.ref or "")
    if a.cmd == "batch":
        if not a.ref:
            print("error: batch needs a TSV path", file=sys.stderr); return 2
        return cmd_batch(rows, a.ref, a.db)
    return cmd_annotate(rows, a, a.db)


if __name__ == "__main__":
    sys.exit(main())
