#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""aerial_qa.py — aerial, FPV, insect-scale and planet-scale shots: the declaration, the measures, the lock check.

Author, 2026-10-26: *"we need to research drone camera movements, shots, when to insert etc"*, *"Golf plus
indoor camera flying moves too … think bee, mosquito views etc"*, *"Aerial shots include orbit planet view, fly
down to ground, moving across continents fast etc"*, then *"Check DJI drone moves. They have presets in the app
for moves"*. The council (the aerial and FPV proposal of 2026-10-26 [studio history]);
the owner chose all four packages and ruled C1 *"Allow narrowly"* (seed chaining), C4 *"Split: rules refuse,
measures warn"*, C5 *"Name it, labelled spec, private"*. The move table is `assets/aerial-moves.json`.

  lint <clip prompt>       the `aerial:` and `chain:` declarations alone (prompt_lint.py runs the same code)
  scale <clip> --shot S --job J
                           the anti-toy measures (Held et al. 2010: a blur gradient makes a real place read as
                           a miniature): sharpness by band, haze falloff, motion against edge crispness
                           → 09-qa/aerial/<S>.scale.json — warns only, until real drone clips calibrate it
  drift <clip> --shot S --job J [--seed FILE]
                           landmarks that re-form: features matched frame to frame and against the seed
                           → <S>.drift.json — warns only
  seams <clip> --shot S --job J [--joins 2.1,4.4]
                           cuts hidden inside a one-take that were not planned → <S>.seams.json — warns only
  stars <clip> --shot S --job J
                           stars in the black beside a sunlit Earth (the exposure that shows the Earth cannot
                           show them) → <S>.stars.json — warns only
  chain-frame <clip> --shot S --job J --at last|SECONDS --out 02-startframes/<name>.png
                           C1: the start frame of the next link of a declared chain, pulled from a clip motion
                           QA has measured and the QA log has selected, with `<out>.chain.json` beside it
  check <job>              at picture lock: the rules refuse, the measures and the cut notes warn
  --selftest

The `aerial:` declaration (one line in the clip prompt's frontmatter, key=value):
  move=<a move of the table, an alias or a DJI preset>   function=<its job>   subject=<what it is about>
  final=<the last frame>   place=real|invented   lane=golf|property|ad|brand|drama   why=<a nadir's reason>
  landmarks=<what must hold>   stages=<n, planet moves>   joins=<seconds, a oner's planned joins>
  geography=simulated (planet moves)   preset=<the DJI preset the pilot flies, for the pilot sheet>
The `chain:` declaration (C1): `root=<the real seed>, stage=<1-3>, from=<the shot whose clip gave the frame>`.

What it cannot do: tell a good aerial from a bad one. It checks that the shot has a job, a subject and an end,
that the words do not ask for what makes AI aerials fail, that a real place is pinned by a real photograph, and
it measures a few things that correlate with the toy look. Every measured threshold is [assumed] until real
drone footage calibrates it, which is why the measures warn and a human signs them off.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, math, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
TABLE_PATH = os.path.join(SKILL, "assets", "aerial-moves.json")
REAL_SOURCES = ("client-supplied", "own-shoot", "licensed", "public-domain", "pixabay")
LANES = ("golf", "property", "ad", "brand", "drama")
KEYS = ("move", "function", "subject", "final", "place", "lane", "why", "landmarks", "stages", "joins", "geography",
        "preset", "from", "to", "path_m")
ROUTE_MOVES = ("hole_flyover", "fly_over", "flyover", "gap_fly_through", "cinewhoop_oner", "fpv_chase", "fpv_dive")
CHAIN_MAX = 3            # C1: a chain is at most three links from its real root (Sonnet's cap; untested)
COAST_MIN_S = 3.0        # an aerial holds over 3 s so the move reads (PremiumBeat flight tips) [PRACTITIONER]
SPEED_WORDS = r"\b(fast|faster|rapid(?:ly)?|quick(?:ly)?|speeding|speedy|high[- ]speed|breakneck|hurtl\w*|rush(?:ing|es)?|racing|zooms? through|whizz\w*|blazing)\b"
TOY_WORDS = r"\b(tilt[- ]shift|miniature|diorama|toy[- ]like|model village)\b"
SHALLOW_WORDS = r"\b(shallow depth of field|shallow focus|bokeh|blurred background|background blur)\b"
CALM_WORDS = r"\b(slow|slowly|steady|steadily|controlled|smooth|smoothly|unhurried|gentle|gently|glid\w*|drift\w*)\b"
DEPTH_WORDS = r"\b(haze|hazy|atmospher\w*|foreground|in the distance|distant|layers?|mist\w*|far below|horizon|deep focus)\b"
INSECT_DOWN = r"\b(looking down|from above|overhead|top[- ]down|bird'?s[- ]eye)\b"
SLOWMO_WORDS = r"\b(slow[- ]motion|slow-mo|high frame rate|high[- ]speed camera|\d{3}\s?fps)\b"
STAR_WORDS = r"\b(stars|starfield|star field|starry|milky way)\b"
TIMELAPSE_WORDS = r"\b(time[- ]?lapse|hyperlapse)\b"
# the measures [assumed] — none is calibrated on real drone footage yet
TS_RATIO = 3.0           # middle band this many times sharper than top and bottom: the tilt-shift gradient
HAZE_FLAT = 0.92         # far-band contrast at least this share of the near band's: no atmospheric falloff
FAST_FLOW = 6.0          # px per frame at 320-px width: fast for an aerial
CRISP_LAP = 900.0        # Laplacian variance at 320-px width: crisp at that speed reads as stop-motion
DRIFT_MIN = 0.35         # homography inlier share between frames 6 apart below this: the ground re-formed
SEED_MIN = 0.20          # inlier share seed → first frame below this: the clip does not start on its seed
SEAM_X = 1.8             # a frame difference this many times its neighbours', with a colour-histogram drop: a seam
SEAM_TOL_S = 0.3         # a seam this close to a planned join is the join
STAR_MIN = 6             # isolated points in the black beside a lit Earth before it reads as stars


# ── the table ───────────────────────────────────────────────────────────────────────────────────────────
_T: dict = {}


def table() -> dict:
    if not _T:
        _T.update(json.load(open(TABLE_PATH, encoding="utf-8")))
    return _T


def resolve_move(name: str) -> tuple:
    """A table move, an alias or a DJI preset → (canonical move, its row) or (None, None)."""
    T = table()
    n = re.sub(r"[\s-]+", "_", str(name or "").strip().lower())
    if n in T["moves"]:
        return n, T["moves"][n]
    if n in T.get("aliases", {}):
        m = T["aliases"][n]
        return m, T["moves"][m]
    pr = T.get("dji", {}).get("presets", {}).get(n)
    if pr and pr.get("move"):
        return pr["move"], T["moves"][pr["move"]]
    return None, None


def parse_decl(s: str) -> dict:
    """`key=value, key=value` where a value may itself hold commas: it splits only before the next key."""
    s = str(s or "").strip()
    if not s:
        return {}
    out = {}
    for part in re.split(r"\s*[,;]\s*(?=[A-Za-z_]+\s*=)", s):
        k, _, v = part.partition("=")
        out[k.strip().lower()] = v.strip()
    return out


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _abs(job: str | None, p: str) -> str:
    return p if os.path.isabs(p) or not job else os.path.join(job, p)


def _sidecar(asset: str) -> dict | None:
    import provenance as PV
    sc = PV.find_sidecar(asset)
    if not sc:
        return None
    try:
        return json.load(open(sc, encoding="utf-8"))
    except ValueError:
        return None


def real_seed_problem(asset: str) -> str | None:
    """None when the file is a cleared real photograph whose sidecar matches it; else why not."""
    if not os.path.isfile(asset):
        return f"{os.path.basename(asset)} is not there"
    sc = _sidecar(asset)
    if sc is None:
        return (f"{os.path.basename(asset)} has no provenance sidecar — record where the photograph came from "
                f"(`provenance.py record`)")
    src = str(sc.get("source") or "")
    blob = " ".join(str(sc.get(k) or "") for k in ("url", "holder", "file")).lower() + json.dumps(sc.get("licence") or {}).lower()
    if "google earth" in blob or "earth.google" in blob:
        return (f"{os.path.basename(asset)} comes from Google Earth, which offers no licence for commercial use "
                f"('We currently do not offer a license to use Google Earth imagery for commercial applications')")
    if src not in REAL_SOURCES:
        return (f"{os.path.basename(asset)} is {src or 'of no recorded source'}, not a real photograph — a real place "
                f"is pinned by a real seed (one of {', '.join(REAL_SOURCES)})")
    if not str(sc.get("clearance") or "").startswith("CLEARED"):
        return f"{os.path.basename(asset)} is not cleared: {sc.get('clearance') or 'no clearance recorded'}"
    if sc.get("sha256") and sc["sha256"] != sha256_file(asset):
        return f"{os.path.basename(asset)} changed after its provenance was recorded"
    return None


def _job_lane(job: str | None) -> str:
    if not job:
        return "ad"
    try:
        c = json.load(open(os.path.join(job, "00-brief", "TITLE-CARD.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return "ad"
    ln = str(c.get("lane") or "ad").lower()
    return {"ads": "ad", "product": "ad", "captions-only": "ad"}.get(ln, ln)


def chain_problems(fm: dict, job: str | None, start_frame: str) -> list:
    """C1, the narrow exception to 'never an AI image as a reference': a link's start frame is a frame of a
    clip motion QA measured and the QA log selected, inside one declared chain whose root is a real seed,
    three links at most, each checked against what it came from."""
    P = []
    ch = parse_decl(fm.get("chain"))
    bad = [k for k in ch if k not in ("root", "stage", "from")]
    if bad:
        P.append(f"`chain:` keys are root, stage, from — not {', '.join(bad)}")
    try:
        stage = int(ch.get("stage", ""))
    except ValueError:
        stage = None
    if stage is None or stage < 1:
        P.append("`chain: stage=` is the link's number from the real root: 1, 2 or 3")
    elif stage > CHAIN_MAX:
        P.append(f"`chain: stage={stage}` — a chain runs {CHAIN_MAX} links at most from its real root (house rule "
                 f"C1, 2026-10-26: allowed narrowly); start again from a real seed")
    root = ch.get("root") or ""
    if not root:
        P.append("`chain:` with no `root=` — every chain starts from a real photograph")
    else:
        why = real_seed_problem(_abs(job, root))
        if why:
            P.append(f"the chain's root: {why}")
    if not ch.get("from"):
        P.append("`chain:` with no `from=` — name the shot whose approved clip gave this start frame")
    sf = _abs(job, start_frame) if start_frame else ""
    cj = sf + ".chain.json" if sf else ""
    if not sf or not os.path.isfile(cj):
        P.append("the start frame has no `.chain.json` beside it — pull it with `aerial_qa.py chain-frame`, which "
                 "records where it came from")
        return P
    try:
        c = json.load(open(cj, encoding="utf-8"))
    except ValueError:
        return P + ["the start frame's .chain.json is unreadable"]
    if os.path.isfile(sf) and c.get("frame_sha256") != sha256_file(sf):
        P.append("the start frame changed after `chain-frame` pulled it")
    if root and os.path.normpath(c.get("root") or "") != os.path.normpath(root):
        P.append(f"the start frame's chain starts at {c.get('root')!r}, not {root!r}")
    if root and os.path.isfile(_abs(job, root)) and c.get("root_sha256") != sha256_file(_abs(job, root)):
        P.append("the chain's root photograph changed after the frame was pulled")
    if stage is not None and c.get("stage") != stage:
        P.append(f"the start frame is link {c.get('stage')} of its chain, the prompt says {stage}")
    if ch.get("from") and c.get("from_shot") != ch.get("from"):
        P.append(f"the start frame came from {c.get('from_shot')!r}, the prompt says {ch.get('from')!r}")
    if job and c.get("from_shot"):
        rp = os.path.join(job, "09-qa", "motion", f"{c['from_shot']}.motion.json")
        try:
            r = json.load(open(rp, encoding="utf-8"))
            if r.get("sha256") != c.get("from_clip_sha256"):
                P.append(f"{c['from_shot']}'s measured clip is not the clip the frame came from — pull the frame again "
                         f"from the clip motion QA approved")
        except (OSError, ValueError):
            P.append(f"{c['from_shot']} has no motion report — a chain link comes only from a measured clip")
    return P


def lint_aerial(fm: dict, txt: str, job: str | None, ctype: str, F, W) -> dict:
    """The declaration rules on one clip prompt. F refuses (a rule), W warns. Returns the parsed declaration."""
    raw = fm.get("aerial")
    if not raw and not fm.get("chain"):
        return {}
    if fm.get("chain") and not raw:
        F("`chain:` without `aerial:` — seed chaining is allowed only inside a declared aerial chain (house rule C1)")
        return {}
    d = parse_decl(raw)
    T = table()
    bad = [k for k in d if k not in KEYS]
    if bad:
        F(f"`aerial:` keys are {', '.join(KEYS)} — not {', '.join(bad)}")
    mv = d.get("move", "")
    if re.search(r"\+|\bthen\b|\band\b|/", mv):
        F(f"`aerial: move={mv}` — one move per clip (the approved models follow one committed motion); cut, or "
          f"split it into two clips")
    name, row = resolve_move(mv)
    if not mv:
        F("`aerial:` with no `move=` — name the move (assets/aerial-moves.json, an alias, or a DJI preset)")
        return d
    if row is None:
        F(f"`aerial: move={mv}` is not a move of the table: {', '.join(T['moves'])} (aliases: "
          f"{', '.join(T.get('aliases', {}))})")
        return d
    kind = row["kind"]
    fn = d.get("function", "").lower()
    if fn not in T["functions"]:
        F(f"`aerial: function=` is the job the shot does: {', '.join(T['functions'])} — an aerial earns its place "
          f"by a job, not by being available")
    elif row.get("for") and fn not in row["for"]:
        W(f"`aerial: function={fn}` — the table's {name} is for {', '.join(row['for'])}; say why it does this job")
    subj = d.get("subject", "").strip().lower()
    if not subj:
        F("`aerial: subject=` — name what the shot is about; a wide with no chosen subject says nothing")
    elif subj in T["generic_subjects"]:
        F(f"`aerial: subject={subj}` is not a subject — name the thing in the place (the clubhouse, the 17th green, "
          f"the runner on the ridge)")
    if not d.get("final", "").strip():
        F("`aerial: final=` — say what the last frame shows; an aerial with no defined end drifts")
    lane = (d.get("lane") or _job_lane(job)).lower()
    if lane not in LANES:
        F(f"`aerial: lane={lane}` — one of {', '.join(LANES)}")
    if row.get("nadir"):
        if lane in ("golf", "property"):
            if fn not in ("geography", "pattern"):
                F(f"a straight-down {name} in the {lane} lane is information: declare function=geography or "
                  f"pattern (house rule C6)")
        elif fn not in T["nadir_functions"] or not d.get("why"):
            F(f"a straight-down {name} outside golf and property needs a story reason: function= one of "
              f"{', '.join(T['nadir_functions'])} and why=<the reason> (house rule C6; the overhead reads "
              f"detached, map-like)")
    place = d.get("place", "").lower()
    if place not in ("real", "invented"):
        F("`aerial: place=` real (a place that exists — pinned by a real photograph) or invented")
    low = (txt or "").lower()
    if not row.get("time_compressed") and re.search(SPEED_WORDS, low):
        hit = re.search(SPEED_WORDS, low).group(0)
        F(f"the prompt says {hit!r} — no speed words on an aerial: the models answer with erratic, warped motion. "
          f"Say the move and its pace (slow, controlled); the speed is set in the edit")
    if re.search(TOY_WORDS, low):
        F(f"the prompt asks for {re.search(TOY_WORDS, low).group(0)!r} — that is the miniature look (Held et al. 2010)")
    if kind in ("drone", "planet") and re.search(SHALLOW_WORDS, low):
        W(f"{re.search(SHALLOW_WORDS, low).group(0)!r} on an aerial — a blur gradient makes a real place read as a "
          f"model (Held et al. 2010); ask for deep focus")
    if kind == "drone" and not re.search(CALM_WORDS, low):
        W("no pace word — an aerial reads as a drone when it is slow and controlled: say so")
    if kind in ("drone", "planet") and not re.search(DEPTH_WORDS, low):
        W("no depth cue — scale is sold by haze, layers and a near foreground (Sawicki): name one")
    pw = [w for w in T["dji"]["preset_words"] if re.search(rf"\b{re.escape(w)}\b", low)]
    if pw:
        W(f"the prompt names {', '.join(pw)} — name the motion, not the app preset; the preset belongs on the pilot "
          f"sheet (`aerial: preset=`)")
    if d.get("preset") and d["preset"].lower() not in T["dji"]["presets"]:
        W(f"`aerial: preset={d['preset']}` is not a DJI preset of the table: {', '.join(T['dji']['presets'])}")
    if "google earth" in low:
        F("Google Earth imagery has no commercial licence — never in client work")
    # ⚡ THE MOTION BUDGET (2026-10-27, lab-00020 B8/B9). A drone shot is a slice of a longer flight: what one clip can
    # cover is the move's speed × the clip's length. A route squeezed into one clip reads as too fast, not as a pilot.
    # Measures still warn (house rule C4) — but this one is a ⚑ warning that must be answered before spend.
    sp = row.get("speed_mps")
    dur = None
    try:
        dur = float(fm.get("duration")) if fm.get("duration") not in (None, "") else None
    except (TypeError, ValueError):
        dur = None
    if isinstance(sp, list) and len(sp) == 2 and dur:
        lo, hi = float(sp[0]), float(sp[1])
        pm = d.get("path_m", "").strip()
        if pm:
            try:
                pv = float(pm)
            except ValueError:
                pv = None
            if pv is None or pv <= 0:
                F("`aerial: path_m=` is the distance this clip flies, in metres")
            elif pv / dur > hi:
                need = -(-pv // (hi * dur))
                W(f"⚑ MOTION: {pv:g} m in {dur:g} s is {pv / dur:.1f} m/s — {pv / dur / hi:.1f}× the {name} table's "
                  f"{lo:g}–{hi:g} m/s. One clip covers {lo * dur:.0f}–{hi * dur:.0f} m: fly a {hi * dur:.0f} m segment, "
                  f"or cut the route into {int(need)} clips")
        elif name in ROUTE_MOVES or row.get("blocking") in ROUTE_MOVES:
            W(f"⚑ MOTION: a route move with no `path_m=` — say how far this clip flies; at {lo:g}–{hi:g} m/s a "
              f"{dur:g} s clip covers {lo * dur:.0f}–{hi * dur:.0f} m")
    if kind == "insect":
        if re.search(INSECT_DOWN, low):
            W("an insect-scale shot looking down — 'you should never look down on your heroes': keep the lens at "
              "their height or below")
        if re.search(SLOWMO_WORDS, low) or fm.get("ramp"):
            F("insect scale runs real time — high frame rates made a beetle 'clumsy and ungainly'; no slow motion, "
              "no ramp")
    if kind == "planet":
        if re.search(STAR_WORDS, low) and not re.search(r"night[- ]side", low):
            F("stars beside the sunlit Earth — the exposure that shows the lit Earth cannot show them; leave them "
              "out (or say the night side)")
        if d.get("geography", "").lower() != "simulated":
            F("a planet-scale move is not geospatially accurate — declare geography=simulated so the rights manifest "
              "carries it")
        if name in ("earth_zoom", "pull_back_planet"):
            try:
                st = int(d.get("stages", "1"))
            except ValueError:
                st = None
            mx = int(row.get("max_stages", 3))
            if st is None or st < 1:
                F("`aerial: stages=` is how many links the move runs (1 to 3)")
            elif st > mx:
                F(f"`aerial: stages={st}` — {mx} at most; past that the steps between scales show")
            else:
                try:
                    dur = float(fm.get("duration") or 0)
                except ValueError:
                    dur = 0.0
                if dur and dur / st < float(row.get("min_secs_per_stage", 3)):
                    W(f"{dur:g} s over {st} stage(s) is {dur / st:.1f} s each — under "
                      f"{row.get('min_secs_per_stage', 3)} s a stage rushes the ground-to-orbit step and distorts")
    if row.get("time_compressed"):
        if not re.search(TIMELAPSE_WORDS, low):
            F(f"a {name} is time compressed — the prompt says time-lapse, or the model renders it as real time")
        if ctype in ("dialogue", "reaction"):
            F(f"a {name} on a speaking or reacting clip — time compression and speech cannot share a clip")
    # sound (the council's A13): the model's audio is muted on an aerial, and no motor whine unless the drone is
    # in the story — the sound is designed in post (an altitude-led bed; planet scale thins toward silence)
    if str(fm.get("audio") or "").strip().lower() in ("true", "yes", "on", "approved", "native"):
        W("native model audio on an aerial — it is muted in the edit; the sound is designed (aerial-and-fpv.md §9)")
    if re.search(r"\b(motor|propellers?|rotor|drone (?:sound|noise|buzz)|buzzing drone|whine)\b", low) \
            and "drone" not in subj:
        W("a drone's motor in the prompt — no motor whine unless the drone is in the story")
    if row.get("max_per_film"):
        W(f"a {name} is punctuation: {row['max_per_film']} per film (checked at lock)")
    if row.get("effect"):
        W(f"a {name} is a stitched effect, not a camera move — an opener only (checked at lock)")
    if place == "real":
        sf = fm.get("start_frame") or ""
        if fm.get("chain"):
            for p in chain_problems(fm, job, sf):
                F(p)
        elif sf:
            why = real_seed_problem(_abs(job, sf))
            if why:
                F(f"a real place is pinned by a real photograph, or the model 'can invent a different building': {why}"
                  f" — or declare a `chain:` from one (house rule C1)")
        if not d.get("landmarks"):
            W("a real place with no `landmarks=` — name what must hold its shape (the bridge, the bunker, the "
              "roofline); `drift` checks it")
    elif fm.get("chain"):
        for p in chain_problems(fm, job, fm.get("start_frame") or ""):
            F(p)
    d["_move"], d["_kind"], d["_lane"] = name, kind, lane
    return d


# ── the measures (warn only: [assumed] until calibrated) ────────────────────────────────────────────────
def _cv():
    import numpy as np, cv2
    return np, cv2


def _frames(path: str, n: int = 8, width: int = 320, every: bool = False):
    """(fps, [(t, gray, bgr)]) — n frames evenly spaced, or every frame when `every`."""
    np, cv2 = _cv()
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    want = set(range(total)) if every or total <= n else {int(round(i * (total - 1) / (n - 1))) for i in range(n)}
    out, i = [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i in want:
            h, w = fr.shape[:2]
            sm = cv2.resize(fr, (width, max(1, int(h * width / w))), interpolation=cv2.INTER_AREA)
            out.append((i / fps, cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY), sm))
        i += 1
    cap.release()
    return fps, out


def _write(job: str, shot: str, kind: str, rep: dict) -> str:
    d = os.path.join(job, "09-qa", "aerial")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{shot}.{kind}.json")
    rep.update({"shot": shot, "measured": dt.datetime.now().isoformat(timespec="minutes"), "calibrated": False,
                "thresholds_tag": "[assumed] — aerial_qa.py constants; a human signs off until real drone clips "
                                  "calibrate them"})
    json.dump(rep, open(p, "w", encoding="utf-8"), indent=1)
    return p


def scale(clip: str, shot: str, job: str) -> dict:
    np, cv2 = _cv()
    fps, frs = _frames(clip, 10)
    bands, haze, flows = [], [], []
    for t, g, _ in frs:
        H = g.shape[0]
        lap = cv2.Laplacian(g, cv2.CV_64F)
        b = [float(lap[int(H * k / 5):int(H * (k + 1) / 5)].var()) for k in range(5)]
        bands.append(b)
        top, bot = g[: H // 3], g[2 * H // 3:]
        haze.append(float(top.std()) / max(float(bot.std()), 1e-6))
    _, every = _frames(clip, 0, every=True)
    for (ta, ga, _), (tb, gb, _) in list(zip(every, every[1:]))[:: max(1, len(every) // 12)]:
        fl = cv2.calcOpticalFlowFarneback(ga, gb, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        flows.append(float(np.median(np.hypot(fl[..., 0], fl[..., 1]))))
    mb = [sum(b[k] for b in bands) / len(bands) for k in range(5)] if bands else [0] * 5
    ts_ratio = mb[2] / max((mb[0] + mb[4]) / 2, 1e-6)
    haze_r = sum(haze) / len(haze) if haze else 1.0
    flow = sum(flows) / len(flows) if flows else 0.0
    crisp = sum(mb) / 5
    looks = []
    if ts_ratio > TS_RATIO:
        looks.append(f"the middle band is {ts_ratio:.1f}x sharper than the top and bottom — the tilt-shift gradient "
                     f"that makes a real place read as a model (Held et al. 2010)")
    if haze_r > HAZE_FLAT:
        looks.append(f"the far third keeps {haze_r:.0%} of the near third's contrast — no atmospheric falloff, so "
                     f"nothing reads far (check it by eye: a nadir or an indoor shot has no horizon)")
    if flow > FAST_FLOW and crisp > CRISP_LAP:
        looks.append(f"it moves {flow:.1f} px a frame with crisp edges — fast and sharp reads as stop-motion; a real "
                     f"camera at that speed blurs")
    rep = {"clip": os.path.relpath(clip, job), "clip_sha256": sha256_file(clip), "band_sharpness": [round(x, 1) for x in mb],
           "tilt_shift_ratio": round(ts_ratio, 2), "haze_ratio": round(haze_r, 3), "flow_px": round(flow, 2),
           "verdict": "LOOK" if looks else "OK", "looks": looks}
    _write(job, shot, "scale", rep)
    return rep


def drift(clip: str, shot: str, job: str, seed: str | None = None) -> dict:
    np, cv2 = _cv()
    _, frs = _frames(clip, 0, width=480, every=True)
    orb = cv2.ORB_create(1500)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    def inliers(a, b):
        ka, da = orb.detectAndCompute(a, None)
        kb, db = orb.detectAndCompute(b, None)
        if da is None or db is None or len(ka) < 40 or len(kb) < 40:
            return None
        m = bf.match(da, db)
        if len(m) < 12:
            return 0.0
        A = np.float32([ka[x.queryIdx].pt for x in m]); B = np.float32([kb[x.trainIdx].pt for x in m])
        _, mask = cv2.findHomography(A, B, cv2.RANSAC, 4.0)
        return float(mask.sum()) / max(min(len(ka), len(kb)), 1) if mask is not None else 0.0
    step = 6
    rows = []
    for i in range(0, max(0, len(frs) - step), step):
        r = inliers(frs[i][1], frs[i + step][1])
        if r is not None:
            rows.append((round(frs[i][0], 2), round(r, 3)))
    low = [(t, r) for t, r in rows if r < DRIFT_MIN]
    seed_r = None
    if seed and os.path.isfile(seed) and frs:
        im = cv2.imread(seed, cv2.IMREAD_GRAYSCALE)
        if im is not None:
            im = cv2.resize(im, (frs[0][1].shape[1], frs[0][1].shape[0]))
            seed_r = inliers(im, frs[0][1])
    looks = []
    if low:
        looks.append(f"the ground re-forms at {', '.join(f'{t:g} s' for t, _ in low[:4])} — features 6 frames apart keep "
                     f"under {DRIFT_MIN:.0%} of their matches; check buildings, bunkers, bridges and coastlines by eye")
    if seed_r is not None and seed_r < SEED_MIN:
        looks.append(f"the first frame keeps {seed_r:.0%} of the seed's features — it does not start on its seed")
    rep = {"clip": os.path.relpath(clip, job), "clip_sha256": sha256_file(clip), "seed": os.path.relpath(seed, job) if seed else None,
           "pairs": rows, "seed_inliers": seed_r, "verdict": "LOOK" if looks else "OK", "looks": looks}
    _write(job, shot, "drift", rep)
    return rep


def seams(clip: str, shot: str, job: str, joins: list | None = None) -> dict:
    np, cv2 = _cv()
    fps, frs = _frames(clip, 0, width=240, every=True)
    diffs, hcs = [], []
    prev_h = None
    for i, (t, g, bgr) in enumerate(frs):
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        h = cv2.calcHist([hsv], [0, 1, 2], None, [8, 4, 8], [0, 180, 0, 256, 0, 256])
        cv2.normalize(h, h)
        if i:
            diffs.append(float(np.mean(cv2.absdiff(g, frs[i - 1][1]))))
            hcs.append(float(cv2.compareHist(prev_h, h, cv2.HISTCMP_CORREL)))
        prev_h = h
    out = []
    for i, (d_, hc) in enumerate(zip(diffs, hcs)):
        near = diffs[max(0, i - 6):i] + diffs[i + 1:i + 7]
        if near and d_ > SEAM_X * max(float(np.median(near)), 1.0) and hc < 0.85:
            out.append(round(frs[i + 1][0], 3))
    planned = [float(x) for x in joins or []]
    unplanned = [t for t in out if not any(abs(t - j) <= SEAM_TOL_S for j in planned)]
    looks = [f"a cut-like jump at {t:g} s that no planned join explains — a seam shows" for t in unplanned]
    rep = {"clip": os.path.relpath(clip, job), "clip_sha256": sha256_file(clip), "seams": out, "planned": planned,
           "verdict": "LOOK" if looks else "OK", "looks": looks}
    _write(job, shot, "seams", rep)
    return rep


def stars(clip: str, shot: str, job: str) -> dict:
    np, cv2 = _cv()
    _, frs = _frames(clip, 6, width=480)
    worst = 0
    for t, g, _ in frs:
        lit = float((g > 120).mean())
        if lit < 0.10:
            continue                                     # no lit Earth in frame: stars may be right
        dark = cv2.boxFilter((g < 25).astype("float32"), -1, (11, 11))
        pts = ((g > 110) & (dark > 0.7)).astype("uint8")
        n, _, st, _ = cv2.connectedComponentsWithStats(pts, 8)
        cnt = sum(1 for k in range(1, n) if st[k, cv2.CC_STAT_AREA] <= 12)
        worst = max(worst, cnt)
    looks = [f"{worst} isolated points in the black beside a sunlit Earth — stars do not show at the exposure that "
             f"shows the lit Earth"] if worst >= STAR_MIN else []
    rep = {"clip": os.path.relpath(clip, job), "clip_sha256": sha256_file(clip), "points": worst,
           "verdict": "LOOK" if looks else "OK", "looks": looks}
    _write(job, shot, "stars", rep)
    return rep


def chain_frame(clip: str, shot: str, job: str, at: str, out: str) -> dict:
    """The next link's start frame from a measured, selected clip, and its record."""
    import motion_qa as MQ
    np, cv2 = _cv()
    rp = os.path.join(job, "09-qa", "motion", f"{shot}.motion.json")
    if not os.path.isfile(rp):
        raise SystemExit(f"refused: {shot} has no motion report — a chain link comes only from a clip motion QA measured")
    r = json.load(open(rp, encoding="utf-8"))
    sha = sha256_file(clip)
    if r.get("sha256") != sha:
        raise SystemExit(f"refused: {os.path.basename(clip)} is not the clip {shot}'s motion report measured")
    if shot not in MQ.selected_shots(job):
        raise SystemExit(f"refused: {shot} is not SELECT or PASS in 09-qa/QA-LOG.md — only an approved clip seeds a link")
    fm = MQ._prompt_fms(job).get(shot) or {}
    if not fm.get("aerial"):
        raise SystemExit(f"refused: {shot}'s prompt declares no `aerial:` — chaining is for declared aerial chains (C1)")
    if fm.get("chain"):
        prev = parse_decl(fm["chain"])
        root, stage = prev.get("root"), int(prev.get("stage") or 1) + 1
    else:
        root, stage = fm.get("start_frame"), 1
        why = real_seed_problem(_abs(job, root or ""))
        if why:
            raise SystemExit(f"refused: {shot} starts from no real seed ({why}) — a chain's root is a real photograph")
    if stage > CHAIN_MAX:
        raise SystemExit(f"refused: that would be link {stage}; a chain runs {CHAIN_MAX} links at most (C1)")
    cap = cv2.VideoCapture(clip)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    idx = total - 1 if at == "last" else int(round(float(at) * fps))
    frame, i = None, 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frame = fr
        if i >= idx:
            break
        i += 1
    cap.release()
    if frame is None:
        raise SystemExit(f"error: no frame at {at} in {clip}")
    op = _abs(job, out)
    os.makedirs(os.path.dirname(op) or ".", exist_ok=True)
    cv2.imwrite(op, frame)
    rec = {"frame": os.path.relpath(op, job), "frame_sha256": sha256_file(op), "root": root,
           "root_sha256": sha256_file(_abs(job, root)), "stage": stage, "from_shot": shot,
           "from_clip": os.path.relpath(clip, job), "from_clip_sha256": sha, "t": round(i / fps, 3),
           "pulled": dt.datetime.now().isoformat(timespec="minutes"),
           "rule": "house rule C1, 2026-10-26: seed chaining allowed narrowly — a measured, selected clip, one declared "
                   "chain from a real root, three links at most"}
    json.dump(rec, open(op + ".chain.json", "w", encoding="utf-8"), indent=1)
    return rec


# ── at picture lock ─────────────────────────────────────────────────────────────────────────────────────
def _aerial_prompts(job: str) -> dict:
    import prompt_lint as PL
    out = {}
    for p in sorted(glob.glob(os.path.join(job, "01-script", "prompts", "*.clip.prompt.md"))):
        fm, body = PL.split_front(PL.read(p))
        if fm.get("aerial") or fm.get("chain"):
            out[str(fm.get("shot") or os.path.basename(p).split(".")[0])] = (p, fm, PL.prompt_text(body))
    return out


def _report(job: str, shot: str, kind: str) -> dict | None:
    p = os.path.join(job, "09-qa", "aerial", f"{shot}.{kind}.json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def check_job(job: str) -> tuple[list, list]:
    """(problems that refuse lock, notes). Rules refuse; measures and cut notes warn (house rule C4)."""
    import motion_qa as MQ
    P, W = [], []
    ap = _aerial_prompts(job)
    if not ap:
        return P, W
    sel = set(MQ.selected_shots(job) or ap)
    decl = {}
    for s, (p, fm, txt) in ap.items():
        if s not in sel:
            continue
        f_, w_ = [], []
        d = lint_aerial(fm, txt, job, str(fm.get("type") or "").lower(), f_.append, w_.append)
        P += [f"{s}: {x}" for x in f_]
        decl[s] = d
        mv, kind = d.get("_move"), d.get("_kind")
        if not mv:
            continue
        clip = None
        mr = os.path.join(job, "09-qa", "motion", f"{s}.motion.json")
        if os.path.isfile(mr):
            try:
                clip = os.path.join(job, json.load(open(mr, encoding="utf-8")).get("file") or "")
            except ValueError:
                clip = None
        sha = sha256_file(clip) if clip and os.path.isfile(clip) else None
        need = ["scale"] if kind in ("drone", "planet", "fpv") else []
        if d.get("place") == "real":
            need.append("drift")
        if mv == "cinewhoop_oner" or d.get("joins"):
            need.append("seams")
        if kind == "planet":
            need.append("stars")
        for k in need:
            r = _report(job, s, k)
            if r is None or (sha and r.get("clip_sha256") != sha):
                W.append(f"{s}: no current `{k}` measure — `aerial_qa.py {k} <its clip> --shot {s} --job <job>` (it warns "
                  f"only; a human signs it off)")
            elif r.get("verdict") == "LOOK":
                W.append(f"{s} ({k}): " + "; ".join(r.get("looks") or [])[:300] + " — a human signs this off")
    # the cut, as Resolve reports it
    tl = MQ.timeline(job)
    if tl is None:
        W.append("no 07-edit/timeline-dump.json — the aerial cut rules (coast, hard cuts, bookends, stunts) were not checked")
        return P, W
    rows = []
    for tn, rs in tl["tracks"].items():
        clips = [r for r in rs if r["kind"] == "clip"]
        if clips and all(MQ._is_title(c["name"], job) for c in clips):
            continue
        rows += rs
    rows.sort(key=lambda r: r["t0"])
    clips = [r for r in rows if r["kind"] == "clip"]
    trans = [r for r in rows if r["kind"] == "transition"]
    on = [(r, MQ._shot_of(r["name"], list(decl))) for r in clips]
    aer = [(r, s) for r, s in on if s]
    lanes = sorted({d.get("_lane") for d in decl.values() if d.get("_lane")})
    has_card = os.path.isfile(os.path.join(job, "00-brief", "TITLE-CARD.json"))
    lane = _job_lane(job) if has_card or len(lanes) != 1 else lanes[0]
    T = table()
    total = tl["end"] or 1.0
    share = sum(r["t1"] - r["t0"] for r, _ in aer) / total
    W.append(f"aerial share: {share:.0%} of the runtime across {len(aer)} clip(s) (logged; no cap — house rule C3)")
    for r, s in aer:
        d = decl[s]
        kind = d.get("_kind")
        if kind in ("drone", "planet") and r["t1"] - r["t0"] < COAST_MIN_S:
            W.append(f"{s} is on screen {r['t1'] - r['t0']:.1f} s — an aerial holds over {COAST_MIN_S:g} s so the move reads")
        for tr in trans:
            if tr["t1"] >= r["t0"] - 0.05 and tr["t0"] <= r["t1"] + 0.05 and (abs(tr["t0"] - r["t0"]) < 1.0 or abs(tr["t1"] - r["t1"]) < 1.0):
                W.append(f"{s}: a transition ({tr['name']}) touches the aerial — cut hard into and out of it")
                break
    if lane == "drama" and aer:
        first, last = clips[0], clips[-1]
        mid = [s for r, s in aer if r is not first and r is not last]
        if mid:
            W.append(f"drama defaults to bookend aerials: {', '.join(mid)} sit(s) inside the film — say why, or move them to the "
              f"open or the close")
    if lane in ("golf", "property") and clips and len(aer) == len(clips):
        W.append(f"every clip is an aerial — the {lane} lane has no cap but needs ground-level variety (a green, a door, a hand)")
    for mv_ in [m for m, row in T["moves"].items() if row.get("max_per_film")]:
        used = [s for r, s in aer if decl[s].get("_move") == mv_]
        cap = int(T["moves"][mv_]["max_per_film"])
        if len(used) > cap:
            W.append(f"{len(used)} × {mv_} ({', '.join(used)}) — {cap} per film; a stunt is punctuation")
    for i_, (r, s) in enumerate(on):
        if s and T["moves"].get(decl[s].get("_move"), {}).get("effect") and i_ != 0:
            W.append(f"{s}: a {decl[s]['_move']} is an opener — it sits at clip {i_ + 1}")
    prev = None
    for r, s in on:
        if not s:
            prev = None
            continue
        try:
            dr = (json.load(open(os.path.join(job, "09-qa", "motion", f"{s}.motion.json"), encoding="utf-8"))
                  .get("camera") or {}).get("direction") or ""
        except (OSError, ValueError):
            dr = ""
        h = "left" if "left" in str(dr) else "right" if "right" in str(dr) else None
        if prev and h and prev[1] and h != prev[1]:
            W.append(f"{prev[0]} → {s}: consecutive aerials travel {prev[1]} then {h} — hold the axis across aerial cuts")
        prev = (s, h)
    return P, W


# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────
def _synth(path: str, fn, n: int = 48, size=(320, 568), fps: int = 24) -> None:
    np, cv2 = _cv()
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (size[0], size[1]))
    for i in range(n):
        vw.write(fn(i, np, cv2))
    vw.release()


def selftest() -> int:
    fails = []

    def check(name, ok, detail=""):
        print(("PASS  " if ok else "FAIL  ") + name + (f" — {detail}" if detail and not ok else ""))
        if not ok:
            fails.append(name)

    def L(decl, txt="a slow controlled orbit, haze over the far hills", extra=None, job=None, ctype="broll"):
        fm = {"aerial": decl, "duration": "6"}
        fm.update(extra or {})
        f_, w_ = [], []
        lint_aerial(fm, txt, job, ctype, f_.append, w_.append)
        return f_, w_
    good = "move=orbit, function=reveal, subject=the clubhouse roof, final=the clubhouse and the sea beyond, place=invented, lane=golf"
    f_, w_ = L(good)
    check("a complete declaration passes clean", not f_ and not w_, json.dumps(f_ + w_))
    check("a comma inside a value survives the parse", parse_decl(good)["final"] == "the clubhouse and the sea beyond")
    check("a generic subject refuses", any("is not a subject" in x for x in L(good.replace("the clubhouse roof", "landscape"))[0]))
    check("no final frame refuses", any("final=" in x for x in L(good.replace(", final=the clubhouse and the sea beyond", ""))[0]))
    check("no function refuses", any("function=" in x for x in L(good.replace("function=reveal", "function=nice"))[0]))
    check("two moves in one clip refuse", any("one move per clip" in x for x in L(good.replace("move=orbit", "move=orbit then helix"))[0]))
    check("a DJI preset name is a move (dronie → pull back reveal)", resolve_move("dronie")[0] == "pull_back_reveal"
          and resolve_move("Asteroid")[0] == "little_planet" and resolve_move("activetrack_trace")[0] == "side_follow")
    check("speed words refuse", any("no speed words" in x for x in L(good, "a fast orbit, haze beyond")[0]))
    check("tilt-shift refuses", any("miniature" in x for x in L(good, "a slow tilt-shift orbit, haze")[0]))
    check("preset names in the prompt warn", any("not the app preset" in x for x in L(good, "a slow dronie, haze beyond")[1]))
    nad = "move=top_down, function=reveal, subject=the 17th green, final=the green, place=invented, lane=golf"
    check("a nadir in golf must be geography or pattern (C6)", any("C6" in x for x in L(nad)[0])
          and not [x for x in L(nad.replace("reveal", "geography"))[0] if "C6" in x])
    nad2 = "move=rocket, function=isolation, subject=the runner on the ridge, final=the ridge, place=invented, lane=drama"
    check("a nadir in drama needs a why (C6)", any("C6" in x for x in L(nad2)[0])
          and not [x for x in L(nad2 + ", why=she is alone with it")[0] if "C6" in x])
    ins = "move=bee, function=journey, subject=the open jar, final=the jar's rim, place=invented"
    check("insect scale refuses slow motion", any("real time" in x for x in L(ins, "a bee's flight in slow motion")[0]))
    check("insect scale looking down warns", any("look down on your heroes" in x for x in L(ins, "a bee's flight from above")[1]))
    pl = "move=earth_zoom, function=scale, subject=the Old Course, final=the 18th green, place=invented, stages=2"
    check("planet scale needs geography=simulated", any("simulated" in x for x in L(pl, "a continuous plunge, haze")[0]))
    check("stars beside the sunlit Earth refuse", any("stars" in x for x in L(pl + ", geography=simulated", "the Earth among stars, haze")[0]))
    check("four stages refuse, a rushed stage warns", any("3 at most" in x for x in L(pl.replace("stages=2", "stages=4") + ", geography=simulated", "a plunge, haze")[0])
          and any("rushes" in x for x in L(pl.replace("stages=2", "stages=3") + ", geography=simulated", "a plunge, haze")[1]))
    hy = "move=hyperlapse, function=breathing, subject=the harbour, final=the harbour at dusk, place=invented"
    check("a hyperlapse must say time-lapse", any("time compressed" in x for x in L(hy, "a slow drift over the harbour, haze")[0])
          and not L(hy, "a slow drifting time-lapse over the harbour, haze")[0])
    check("Google Earth refuses", any("Google Earth" in x for x in L(good, "a slow orbit like Google Earth, haze")[0]))
    check("native audio and a motor whine on an aerial warn", any("muted in the edit" in x for x in L(good, extra={"audio": "true"})[1])
          and any("motor whine" in x for x in L(good, "a slow orbit, the propellers humming, haze")[1]))
    with tempfile.TemporaryDirectory() as job:
        import provenance as PV
        os.makedirs(os.path.join(job, "02-startframes")); os.makedirs(os.path.join(job, "09-qa", "motion"))
        os.makedirs(os.path.join(job, "01-script", "prompts")); os.makedirs(os.path.join(job, "03-clips"))
        real = os.path.join(job, "02-startframes", "hole1_real.jpg")
        open(real, "wb").write(b"\xff\xd8 a real photograph")
        rec = {"source": "licensed", "sha256": sha256_file(real), "clearance": "CLEARED by Dana on 2026-10-26",
               "url": "https://example.org/aerials/hole1", "licence": {"name": "commercial"}}
        json.dump(rec, open(PV.sidecar_path(real), "w"))
        gen = os.path.join(job, "02-startframes", "hole1_gen.png")
        open(gen, "wb").write(b"\x89PNG generated")
        json.dump(dict(rec, source="ai-generated", sha256=sha256_file(gen)), open(PV.sidecar_path(gen), "w"))
        rdecl = good.replace("place=invented", "place=real") + ", landmarks=the Swilcan Bridge"
        check("a real place on a real cleared photograph passes", not L(rdecl, extra={"start_frame": "02-startframes/hole1_real.jpg"}, job=job)[0])
        check("a real place on a generated frame refuses", any("real photograph" in x for x in L(rdecl, extra={"start_frame": "02-startframes/hole1_gen.png"}, job=job)[0]))
        ge = os.path.join(job, "02-startframes", "ge.jpg"); open(ge, "wb").write(b"ge")
        json.dump(dict(rec, sha256=sha256_file(ge), url="https://earth.google.com/web/x"), open(PV.sidecar_path(ge), "w"))
        check("a Google Earth seed refuses", any("Google Earth" in x for x in L(rdecl, extra={"start_frame": "02-startframes/ge.jpg"}, job=job)[0]))
        check("a real place with no landmarks warns", any("landmarks=" in x for x in L(good.replace("place=invented", "place=real"),
              extra={"start_frame": "02-startframes/hole1_real.jpg"}, job=job)[1]))
        # C1: a chain link pulled from a measured, selected clip, then tampered with
        clip = os.path.join(job, "03-clips", "S1_v1.mp4")
        _synth(clip, lambda i, np, cv2: np.full((568, 320, 3), (40 + i, 90, 140), "uint8"))
        json.dump({"shot": "S1", "file": "03-clips/S1_v1.mp4", "sha256": sha256_file(clip)},
                  open(os.path.join(job, "09-qa", "motion", "S1.motion.json"), "w"))
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "w").write("| date | S1 | clip | x | SELECT |\n")
        open(os.path.join(job, "01-script", "prompts", "S1.clip.prompt.md"), "w").write(
            "---\nshot: S1\nkind: clip\naerial: " + rdecl + "\nstart_frame: 02-startframes/hole1_real.jpg\n---\nslow orbit\n")
        rec2 = chain_frame(clip, "S1", job, "last", "02-startframes/S2_link.png")
        ch = {"start_frame": "02-startframes/S2_link.png", "chain": "root=02-startframes/hole1_real.jpg, stage=1, from=S1"}
        check("chain-frame records link 1 from the real root", rec2["stage"] == 1 and rec2["root"] == "02-startframes/hole1_real.jpg")
        check("a declared link 1 passes", not L(rdecl, extra=ch, job=job)[0], json.dumps(L(rdecl, extra=ch, job=job)[0]))
        check("a link numbered wrong refuses", any("link 1" in x for x in L(rdecl, extra=dict(ch, chain=ch["chain"].replace("stage=1", "stage=2")), job=job)[0]))
        check("a fourth link refuses", any("3 links at most" in x for x in L(rdecl, extra=dict(ch, chain=ch["chain"].replace("stage=1", "stage=4")), job=job)[0]))
        noaer = []
        lint_aerial({"chain": ch["chain"]}, "", job, "broll", noaer.append, lambda x: None)
        check("a chain without an aerial declaration refuses", any("without `aerial:`" in x for x in noaer), json.dumps(noaer))
        _synth(clip, lambda i, np, cv2: np.full((568, 320, 3), (200, 90, 40 + i), "uint8"))
        try:
            chain_frame(clip, "S1", job, "last", "02-startframes/x.png")
            check("chain-frame refuses a clip motion QA did not measure", False)
        except SystemExit as e:
            check("chain-frame refuses a clip motion QA did not measure", "not the clip" in str(e))
        json.dump({"shot": "S1", "file": "03-clips/S1_v1.mp4", "sha256": sha256_file(clip)},
                  open(os.path.join(job, "09-qa", "motion", "S1.motion.json"), "w"))       # re-made and re-measured
        check("a link whose source clip was re-made refuses", any("not the clip the frame came from" in x for x in L(rdecl, extra=ch, job=job)[0]))
        # the measures, on synthetic clips
        np_, cv2 = _cv()
        rng = np_.random.default_rng(1)
        tex = (rng.random((900, 900)) * 255).astype("uint8")
        tex = cv2.GaussianBlur(tex, (0, 0), 1.2)

        def pan(i, np, cv2, ts=False):
            fr = cv2.cvtColor(tex[100:668, 40 + i * 2: 360 + i * 2], cv2.COLOR_GRAY2BGR)
            if ts:
                b = cv2.GaussianBlur(fr, (0, 0), 6)
                fr = fr.copy(); fr[:190] = b[:190]; fr[380:] = b[380:]
            return fr
        a = os.path.join(job, "03-clips", "pan.mp4"); _synth(a, pan)
        b = os.path.join(job, "03-clips", "ts.mp4"); _synth(b, lambda i, np, cv2: pan(i, np, cv2, True))
        check("a tilt-shift gradient is seen, a sharp pan is not", scale(b, "TS", job)["tilt_shift_ratio"] > TS_RATIO
              and scale(a, "PAN", job)["tilt_shift_ratio"] < TS_RATIO)
        sm = os.path.join(job, "03-clips", "seam.mp4")
        tex2 = (rng.random((900, 900)) * 255).astype("uint8")
        _synth(sm, lambda i, np, cv2: pan(i, np, cv2) if i < 24 else
               (cv2.cvtColor(tex2[100:668, 40 + i: 360 + i], cv2.COLOR_GRAY2BGR) // 2 + np.array([90, 30, 10], "uint8")))
        r = seams(sm, "OW", job)
        check("an unplanned seam is found, a planned one is not", any(abs(t - 1.0) < 0.1 for t in r["seams"]) and r["verdict"] == "LOOK"
              and seams(sm, "OW", job, [1.0])["verdict"] == "OK", json.dumps(r["seams"]))
        dr = drift(a, "PAN", job)
        check("a steady pan holds its ground", dr["verdict"] == "OK", json.dumps(dr["pairs"][:4]))
        check("a scene that re-forms is flagged", drift(sm, "OW", job)["verdict"] == "LOOK")

        def earth(i, np, cv2, n_stars=0):
            fr = np.zeros((568, 320, 3), "uint8")
            cv2.circle(fr, (160, 420), 150, (200, 160, 120), -1)
            r_ = np.random.default_rng(7)
            for _ in range(n_stars):
                x, y = int(r_.integers(10, 310)), int(r_.integers(10, 200))
                fr[y:y + 2, x:x + 2] = 255
            return fr
        e1 = os.path.join(job, "03-clips", "e1.mp4"); _synth(e1, lambda i, np, cv2: earth(i, np, cv2, 30), n=12)
        e0 = os.path.join(job, "03-clips", "e0.mp4"); _synth(e0, lambda i, np, cv2: earth(i, np, cv2, 0), n=12)
        check("stars beside a lit Earth are counted", stars(e1, "PL", job)["verdict"] == "LOOK" and stars(e0, "PL0", job)["verdict"] == "OK")
        # the lock check: a cut with a short aerial, a transition on it, and drama's bookend rule
        open(os.path.join(job, "01-script", "prompts", "S2.clip.prompt.md"), "w").write(
            "---\nshot: S2\nkind: clip\naerial: move=orbit, function=reveal, subject=the farmhouse, final=the farmhouse, place=invented, lane=drama\n---\nslow controlled orbit, haze\n")
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "a").write("| date | S2 | clip | x | SELECT |\n| date | S3 | clip | x | SELECT |\n")
        os.makedirs(os.path.join(job, "07-edit"), exist_ok=True); os.makedirs(os.path.join(job, "00-brief"), exist_ok=True)
        json.dump({"lane": "drama"}, open(os.path.join(job, "00-brief", "TITLE-CARD.json"), "w"))
        json.dump({"fps": 24, "tracks": {"video1": [
            {"name": "S3_v1.mp4", "start_s": 0, "duration_s": 3}, {"name": "S2_v1.mp4", "start_s": 3, "duration_s": 2.0},
            {"name": "Cross Dissolve", "type": "transition", "start_s": 4.5, "duration_s": 1.0},
            {"name": "S3_v2.mp4", "start_s": 5, "duration_s": 3}]}}, open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
        open(os.path.join(job, "01-script", "prompts", "S4.clip.prompt.md"), "w").write(
            "---\nshot: S4\nkind: clip\naerial: " + rdecl + "\nstart_frame: 02-startframes/S2_link.png\n"
            "chain: root=02-startframes/hole1_real.jpg, stage=1, from=S1\n---\nslow controlled orbit, haze\n")
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "a").write("| date | S4 | clip | x | SELECT |\n")
        P, Wn = check_job(job)
        check("lock: a short aerial, a transition on it and a mid-film aerial in drama are noted",
              any("on screen 2.0 s" in x for x in Wn) and any("cut hard" in x for x in Wn) and any("bookend" in x for x in Wn)
              and any("aerial share" in x for x in Wn), json.dumps(Wn))
        check("lock: the stale chain link refuses; a missing measure only notes",
              any(x.startswith("S4:") and "came from" in x for x in P) and not [x for x in P if "no current" in x]
              and any("no current `scale`" in x for x in Wn), json.dumps(P))
    print(f"\n{'FAIL' if fails else 'OK'} — {len(fails)} failing" if fails else "\nselftest OK — the declaration refuses a "
          "blank job, subject or end, two moves, speed and miniature words, an unreasoned nadir, slow-motion bugs, stars, "
          "unsimulated planets and Google Earth; a real place needs a real cleared photograph or a C1 chain, which "
          "refuses a renumbered, fourth or stale link; the measures see a tilt-shift gradient, a hidden seam, a re-formed "
          "scene and stars; the lock notes a short aerial, a transition on it and a mid-film drama aerial")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("lint"); p.add_argument("prompt"); p.add_argument("--job")
    for c in ("scale", "drift", "seams", "stars", "chain-frame"):
        p = sub.add_parser(c); p.add_argument("clip"); p.add_argument("--shot", required=True); p.add_argument("--job", required=True)
        if c == "drift":
            p.add_argument("--seed")
        if c == "seams":
            p.add_argument("--joins", default="")
        if c == "chain-frame":
            p.add_argument("--at", default="last"); p.add_argument("--out", required=True)
    p = sub.add_parser("check"); p.add_argument("job")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "lint":
        import prompt_lint as PL
        fm, body = PL.split_front(PL.read(a.prompt))
        f_, w_ = [], []
        lint_aerial(fm, PL.prompt_text(body), a.job, str(fm.get("type") or "").lower(), f_.append, w_.append)
        for x in f_:
            print("FAIL ", x)
        for x in w_:
            print("WARN ", x)
        return 1 if f_ else 0
    if a.cmd in ("scale", "drift", "seams", "stars"):
        fn = {"scale": lambda: scale(a.clip, a.shot, a.job), "drift": lambda: drift(a.clip, a.shot, a.job, a.seed),
              "seams": lambda: seams(a.clip, a.shot, a.job, [float(x) for x in a.joins.split(",") if x.strip()]),
              "stars": lambda: stars(a.clip, a.shot, a.job)}[a.cmd]
        r = fn()
        print(f"{a.cmd} {a.shot}: {r['verdict']}" + "".join(f"\n  - {x}" for x in r.get("looks") or []))
        return 0
    if a.cmd == "chain-frame":
        r = chain_frame(a.clip, a.shot, a.job, a.at, a.out)
        print(f"{r['frame']} — link {r['stage']} from {r['root']} (from {r['from_shot']} at {r['t']} s)")
        return 0
    if a.cmd == "check":
        P, W = check_job(a.job)
        for x in P:
            print("REFUSE", x)
        for x in W:
            print("NOTE  ", x)
        return 1 if P else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
