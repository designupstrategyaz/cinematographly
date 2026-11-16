#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""flyover.py — the golf and property flyover product: the hole card, the property sheet, the overlays checked
against them, the rights manifest, and the pilot sheet for a real drone day.

Author, 2026-10-26: golf plus indoor flying, then *"Check DJI drone moves. They have presets in the app for
moves"*. The council's package B (the aerial and FPV proposal of 2026-10-26 [studio history]: A7 the hole card and the
hole flyover, A8 the St Andrews protocol, A9 property, A14 the rights manifest) with ruling C5 *"Name it,
labelled spec, private"*: a course or property file marked `private: true` cannot be published (gate.py).

  course init <job> --name NAME [--holes 18] [--preset old-course] [--operator NAME] [--public]
                       → 00-brief/COURSE.json: one card per hole (par, yards, the strategy line, hazards,
                       landmarks, the green, the real seed photo, optional route points). Nothing is invented:
                       blanks stay blank until club data fills them; a preset carries only the checked facts
  course lint <job>    every hole has its numbers, its strategy line and a real cleared seed; the pars and
                       yards add up to the course's; the spec label and the marks (C5)
  hole prompt <job> --hole N [--model M] [--duration S]
                       a draft clip prompt for that hole's flyover (01-script/prompts/H<NN>.clip.prompt.md),
                       declared, on its seed — a draft for the director, never approved by writing it
  property init <job> --name NAME [--public]
                       → 00-brief/PROPERTY.json: the exterior and every room, each with its real seed photo
  property lint <job>  every room has a real cleared seed; every property clip names a room that exists
  overlays <job>       every hole card overlay (07-edit/titles/*.title.json) and room label checked against the
                       card: 'Hole 7 · Par 4 · 371 yards' must be the card's hole 7 (a mismatch refuses at lock)
  rights <job>         → 09-qa/aerial/RIGHTS.md: every seed's source, holder, licence and clearance; NASA credit
                       without endorsement; simulated geography disclosed; the spec label; AI-generated flags
  pilot <job>          → 09-qa/aerial/PILOT-SHEET.md: for each aerial shot, the DJI preset that flies it (or
                       Waypoint Flight / by hand), what to set, the clearances, the move table's speed and
                       height, and a per-hole waypoint table; the conditions under which presets must not run
  check <job>          at lock: (problems, notes) — the cards, overlays and rights refuse; gaps note
  --selftest

What it cannot do: know a course. The card holds facts, not positions: a course map or survey is the geometry
truth, and route points are entered from one (or set on site). It does not fly the drone, and the pilot sheet
is not a flight authorisation — the pilot's own checks, airspace and the operator's permission come first.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aerial_qa as AQ  # noqa: E402

COURSE = os.path.join("00-brief", "COURSE.json")
PROPERTY = os.path.join("00-brief", "PROPERTY.json")
RIGHTS = os.path.join("09-qa", "aerial", "RIGHTS.md")
PILOT = os.path.join("09-qa", "aerial", "PILOT-SHEET.md")
TITLES = os.path.join("07-edit", "titles")
OLD_COURSE_SRC = "Wikipedia, 'Old Course at St Andrews' [REFERENCE, checked 2026-10-26]; confirm against the Links Trust's card"
PRESETS = {
    "old-course": {
        "name": "The Old Course, St Andrews", "operator": "St Andrews Links Trust",
        "facts": {"holes": 18, "par": 72, "yards": 7305, "direction": "anticlockwise",
                  "single_greens": [1, 9, 17, 18], "double_greens": 7,
                  "note": "Fife Council owns the course; St Andrews Links Trust runs it. The Trust holds the 'St Andrews' "
                          "mark for goods; the EUIPO refused it for travel services (2020)"},
        "landmarks": {1: ["the Swilcan Bridge", "the R&A clubhouse behind the 1st tee"], 14: ["Hell Bunker"],
                      17: ["the Road Hole", "the Old Course Hotel sheds"], 18: ["the Swilcan Bridge", "the Valley of Sin"]},
        "source": OLD_COURSE_SRC},
}


def _load(job: str, rel: str) -> dict | None:
    p = os.path.join(job, rel)
    try:
        return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None
    except ValueError:
        return {"_error": f"{rel} is not valid JSON"}


def _save(job: str, rel: str, d: dict) -> str:
    p = os.path.join(job, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return p


def spec_label(operator: str) -> str:
    return f"Spec, not affiliated with {operator}" if operator else "Spec, not affiliated with the course or its operator"


def course_init(job: str, name: str, holes: int = 18, preset: str | None = None, operator: str = "",
                public: bool = False, force: bool = False) -> str:
    if os.path.isfile(os.path.join(job, COURSE)) and not force:
        raise SystemExit(f"error: {COURSE} exists — edit it, or --force")
    pr = PRESETS.get(preset or "", {})
    op = operator or pr.get("operator", "")
    n = int(pr.get("facts", {}).get("holes", holes))
    single = set(pr.get("facts", {}).get("single_greens", []))
    cards = []
    for h in range(1, n + 1):
        lm = pr.get("landmarks", {}).get(h, [])
        cards.append({"hole": h, "name": "", "par": None, "yards": None, "strategy": "", "hazards": [],
                      "landmarks": lm, "green": ("single" if h in single else "double") if pr else "",
                      "seed": "", "route": {}, "sources": {"landmarks": pr["source"]} if lm else {}})
    d = {"kind": "course", "name": name or pr.get("name", ""), "operator": op,
         "private": not public, "spec_label": spec_label(op), "marks": [],
         "facts": pr.get("facts", {}), "facts_source": pr.get("source", ""), "holes": cards,
         "created": dt.date.today().isoformat(),
         "rules": "house rule C5: named descriptively, labelled spec, no logos or marks of the operator, never in a "
                  "service's brand name, private until a legal view clears public promotion"}
    return _save(job, COURSE, d)


def course_lint(job: str) -> tuple[list, list]:
    P, W = [], []
    c = _load(job, COURSE)
    if c is None:
        return [f"no {COURSE} — `flyover.py course init <job> --name …`"], W
    if c.get("_error"):
        return [c["_error"]], W
    holes = c.get("holes") or []
    for h in holes:
        n = h.get("hole")
        for k in ("par", "yards"):
            if not isinstance(h.get(k), int):
                P.append(f"hole {n}: no {k} — fill it from the club's card (and say where in `sources`)")
            elif not (h.get("sources") or {}).get(k):
                W.append(f"hole {n}: {k} has no source — the card the club publishes, its date")
        if isinstance(h.get("par"), int) and not 3 <= h["par"] <= 6:
            P.append(f"hole {n}: par {h['par']} — a hole is par 3 to 6")
        if not str(h.get("strategy") or "").strip():
            P.append(f"hole {n}: no strategy line — where the ball should go, the line the flyover follows")
        if not h.get("seed"):
            P.append(f"hole {n}: no seed photo — a real hole is pinned by a real aerial photograph (A8)")
        else:
            why = AQ.real_seed_problem(os.path.join(job, h["seed"]))
            if why:
                P.append(f"hole {n}: {why}")
    f = c.get("facts") or {}
    if f.get("holes") and len(holes) != int(f["holes"]):
        P.append(f"{len(holes)} hole cards, the course has {f['holes']}")
    pars = [h.get("par") for h in holes]
    if f.get("par") and all(isinstance(x, int) for x in pars) and sum(pars) != int(f["par"]):
        P.append(f"the hole pars add up to {sum(pars)}, the course is par {f['par']}")
    yds = [h.get("yards") for h in holes]
    if f.get("yards") and all(isinstance(x, int) for x in yds) and sum(yds) != int(f["yards"]):
        W.append(f"the hole yards add up to {sum(yds)}, the course card says {f['yards']} — the same tees?")
    lab = str(c.get("spec_label") or "")
    if c.get("private", True) is not False and not re.search(r"\bspec\b", lab, re.I):
        P.append("a spec piece carries its label: 'Spec, not affiliated with <operator>' (house rule C5)")
    if c.get("operator") and c["operator"].lower() not in lab.lower() and "spec" in lab.lower():
        W.append(f"the spec label does not name the operator ({c['operator']})")
    if c.get("marks"):
        P.append(f"marks {c['marks']} — no logos or marks of the course or its operator in a spec piece (C5)")
    return P, W


def _ord(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 or not 1 <= n % 10 <= 3 else ['st', 'nd', 'rd'][n % 10 - 1]}"


def hole_prompt(job: str, hole: int, model: str = "seedance_2_5", duration: int = 8) -> str:
    c = _load(job, COURSE) or {}
    h = next((x for x in c.get("holes") or [] if x.get("hole") == hole), None)
    if h is None:
        raise SystemExit(f"error: no hole {hole} in {COURSE}")
    shot = f"H{hole:02d}"
    lm = ", ".join(h.get("landmarks") or []) or "the green's shape and the bunkers"
    hz = ", ".join(h.get("hazards") or [])
    words = AQ.table()["moves"]["hole_flyover"]["words"]
    body = (f"[CAMERA] From a drone, smooth and unhurried: {words}. One continuous move, slow and controlled.\n\n"
            f"[SCENE] The {_ord(hole)} hole as it is in the seed photograph: {h.get('strategy') or 'the strategy line'}"
            f"{', past ' + hz if hz else ''}. {lm} keep their shape and place. Deep focus, haze toward the horizon, "
            f"long shadows; no bunkers, paths or buildings that are not in the photograph.\n\n"
            f"[END] The green fills the lower half of the frame, the flag in it.\n")
    fm = (f"---\nshot: {shot}\nkind: clip\ntype: broll\nmodel: {model}\naspect: 9:16\nduration: {duration}\n"
          f"start_frame: {h.get('seed') or '02-startframes/' + shot + '_seed.jpg'}\n"
          f"aerial: move=hole_flyover, function=geography, subject=the {_ord(hole)} green, "
          f"final=the green with the flag in the lower half of the frame, place=real, lane=golf, landmarks={lm}, "
          f"preset=waypoint_flight\n"
          f"payload: the line to play the {hole} and where it is won or lost\n"
          f"status: DRAFT — written by flyover.py hole prompt; the director edits and approves it\n---\n")
    p = os.path.join(job, "01-script", "prompts", f"{shot}.clip.prompt.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.isfile(p):
        raise SystemExit(f"error: {os.path.relpath(p, job)} exists — the director's edits are not overwritten")
    open(p, "w", encoding="utf-8").write(fm + body)
    return p


def property_init(job: str, name: str, public: bool = False, force: bool = False) -> str:
    if os.path.isfile(os.path.join(job, PROPERTY)) and not force:
        raise SystemExit(f"error: {PROPERTY} exists — edit it, or --force")
    d = {"kind": "property", "name": name, "private": not public, "spec_label": "", "marks": [],
         "exterior": {"seed": "", "landmarks": []},
         "rooms": [{"name": "", "seed": "", "notes": ""}],
         "created": dt.date.today().isoformat(),
         "rules": "every room shown is a room of this file, on its real photograph — an invented room is a claims risk; "
                  "interiors glide slowly (energetic moves read as a car advert); 9:16 generated natively, never cropped"}
    return _save(job, PROPERTY, d)


def _property_clips(job: str) -> list:
    import prompt_lint as PL
    out = []
    for p in sorted(glob.glob(os.path.join(job, "01-script", "prompts", "*.clip.prompt.md"))):
        fm, body = PL.split_front(PL.read(p))
        d = AQ.parse_decl(fm.get("aerial"))
        if d.get("lane") == "property" or (not d.get("lane") and AQ._job_lane(job) == "property" and d):
            out.append((str(fm.get("shot") or os.path.basename(p)), fm, d, PL.prompt_text(body)))
    return out


def property_lint(job: str) -> tuple[list, list]:
    P, W = [], []
    d = _load(job, PROPERTY)
    if d is None:
        return [f"no {PROPERTY} — `flyover.py property init <job> --name …`"], W
    if d.get("_error"):
        return [d["_error"]], W
    rooms = [r for r in d.get("rooms") or [] if r.get("name")]
    if not rooms:
        P.append("no rooms named — list the rooms the film shows, each on its own photograph")
    for r in rooms + [dict(d.get("exterior") or {}, name="the exterior")]:
        if not r.get("seed"):
            P.append(f"{r['name']}: no seed photo — a real room is pinned by its real photograph")
            continue
        why = AQ.real_seed_problem(os.path.join(job, r["seed"]))
        if why:
            P.append(f"{r['name']}: {why}")
    names = {r["name"].strip().lower() for r in rooms} | {"the exterior", "exterior", str(d.get("name") or "").lower()}
    for shot, fm, decl, txt in _property_clips(job):
        subj = str(decl.get("subject") or "").strip().lower()
        if subj and not any(n and (n in subj or subj in n) for n in names):
            P.append(f"{shot}: subject {decl.get('subject')!r} is not a room of {PROPERTY} — an invented room is a claims "
                     f"risk; show only what is there")
        if re.search(r"\b(dynamic|energetic|sweeping|whip|aggressive)\b", txt.lower()):
            W.append(f"{shot}: an energetic move indoors reads as a car advert — slow, steady glides")
        if str(fm.get("aspect") or "") not in ("9:16", ""):
            W.append(f"{shot}: aspect {fm.get('aspect')} — generate 9:16 natively; never crop a 16:9 walkthrough")
    if d.get("spec") and not re.search(r"\bspec\b", str(d.get("spec_label") or ""), re.I):
        P.append("a spec property piece carries its label: 'Spec, not affiliated with <owner or agent>' (C5)")
    return P, W


# ── overlays against the cards ──────────────────────────────────────────────────────────────────────────
def _text(spec: dict) -> str:
    C = spec.get("content") or {}
    parts = list(C.get("lines") or [])
    for k, v in C.items():
        if k != "lines" and isinstance(v, (str, int, float)):
            parts.append(str(v))
    return " · ".join(str(x) for x in parts)


def overlays(job: str) -> tuple[list, list]:
    P, W = [], []
    c = _load(job, COURSE)
    pr = _load(job, PROPERTY)
    cards = {h.get("hole"): h for h in (c or {}).get("holes") or []}
    rooms = {str(r.get("name") or "").strip().lower() for r in (pr or {}).get("rooms") or [] if r.get("name")}
    for p in sorted(glob.glob(os.path.join(job, TITLES, "*.title.json"))):
        rel = os.path.relpath(p, job)
        try:
            s = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        txt = _text(s)
        low = txt.lower()
        m = re.search(r"\bhole\s+(\d{1,2})\b", low)
        n = int(s["hole"]) if str(s.get("hole") or "").isdigit() else (int(m.group(1)) if m else None)
        if s.get("kind") == "hole" or n is not None:
            if not c:
                P.append(f"{rel}: a hole overlay and no {COURSE} to check it against")
                continue
            h = cards.get(n)
            if h is None:
                P.append(f"{rel}: hole {n} is not a hole of the course card")
                continue
            for pm in re.findall(r"\bpar\s+(\d)\b", low):
                if h.get("par") != int(pm):
                    P.append(f"{rel}: says par {pm}; hole {n}'s card says par {h.get('par')}")
            for ym in re.findall(r"\b(\d{2,3})\s*(?:yd|yds|yards)\b", low):
                if h.get("yards") != int(ym):
                    P.append(f"{rel}: says {ym} yards; hole {n}'s card says {h.get('yards')}")
        if s.get("kind") == "room":
            if not pr:
                P.append(f"{rel}: a room label and no {PROPERTY}")
            elif not any(r and (r in low or low in r) for r in rooms):
                P.append(f"{rel}: {txt!r} is not a room of {PROPERTY} — label only what is there")
        if re.search(r"\bofficial\b|\baffiliated with\b", low) and "not affiliated" not in low:
            P.append(f"{rel}: {txt!r} implies an affiliation — a spec piece claims none (C5)")
    return P, W


# ── the rights manifest ─────────────────────────────────────────────────────────────────────────────────
def _seeds(job: str) -> list:
    """[(what, path)] — every seed the job names: the cards and the aerial prompts' start frames and chain roots."""
    out = []
    for h in (_load(job, COURSE) or {}).get("holes") or []:
        if h.get("seed"):
            out.append((f"hole {h['hole']}", h["seed"]))
    pr = _load(job, PROPERTY) or {}
    for r in (pr.get("rooms") or []) + [dict(pr.get("exterior") or {}, name="the exterior")]:
        if r.get("seed"):
            out.append((r.get("name") or "a room", r["seed"]))
    for s, (p, fm, txt) in AQ._aerial_prompts(job).items():
        if fm.get("start_frame"):
            out.append((f"{s} start frame", fm["start_frame"]))
        ch = AQ.parse_decl(fm.get("chain"))
        if ch.get("root"):
            out.append((f"{s} chain root", ch["root"]))
    seen, uniq = set(), []
    for w, p in out:
        if p not in seen:
            seen.add(p); uniq.append((w, p))
    return uniq


def rights(job: str) -> tuple[str, list]:
    P = []
    rows = []
    nasa = False
    for what, rel in _seeds(job):
        ap = os.path.join(job, rel)
        sc = AQ._sidecar(ap) or {}
        if os.path.isfile(ap + ".chain.json"):
            src = "a frame of an approved clip (C1 chain link)"
        else:
            src = sc.get("source") or "—"
        lic = (sc.get("licence") or {}).get("name") or "—"
        holder = sc.get("holder") or "—"
        clr = sc.get("clearance") or "no sidecar"
        blob = json.dumps(sc).lower()
        if "nasa" in blob:
            nasa = True
        if "google earth" in blob or "earth.google" in blob:
            P.append(f"{rel}: Google Earth imagery — no licence for commercial use; replace it")
        rows.append(f"| {what} | `{rel}` | {src} | {holder} | {lic} | {clr} |")
    c, pr = _load(job, COURSE) or {}, _load(job, PROPERTY) or {}
    sim = [s for s, (p, fm, t) in AQ._aerial_prompts(job).items()
           if AQ.parse_decl(fm.get("aerial")).get("geography", "").lower() == "simulated"]
    L = [f"# Rights and disclosure — {os.path.basename(os.path.abspath(job))}", "",
         f"Written by `flyover.py rights` on {dt.date.today().isoformat()}. House rule C5 (2026-10-26); the council's A14.",
         "", "## Seeds", "", "| What | File | Source | Holder | Licence | Clearance |", "|---|---|---|---|---|---|"] + rows
    L += ["", "## Disclosure", ""]
    for d in (c, pr):
        if d.get("private", False):
            L.append(f"- **Private.** {d.get('name')}: `private: true` — the gate refuses publishing until a legal view "
                     f"clears public promotion (C5).")
        if d.get("spec_label"):
            L.append(f"- **On screen and in the description:** \"{d['spec_label']}\". No logos or marks of the operator.")
    if sim:
        L.append(f"- **Simulated geography** ({', '.join(sim)}): the planet-scale move is not geospatially accurate; say "
                 f"so where the film is described.")
    if nasa:
        L.append("- **NASA imagery:** credit NASA; it must not imply NASA endorses anything; the insignia is never used.")
    L.append("- **AI-generated:** the clips are AI-generated from real photographs — set the platform's AI label "
             "(YouTube, TikTok, Meta) when it is published.")
    p = os.path.join(job, RIGHTS)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return p, P


# ── the pilot sheet ─────────────────────────────────────────────────────────────────────────────────────
def presets_for(move: str) -> list:
    T = AQ.table()["dji"]["presets"]
    return [(k, v) for k, v in T.items() if v.get("move") == move] + \
           [(k, v) for k, v in T.items() if move in (v.get("use_for") or [])]


def pilot(job: str) -> str:
    T = AQ.table()
    dji = T["dji"]
    L = [f"# Pilot sheet — {os.path.basename(os.path.abspath(job))}", "",
         "For a real drone day. It names the DJI preset that flies each aerial shot, what to set, and the clearances from "
         "DJI's manuals (`assets/aerial-moves.json`, `dji`). It is not a flight authorisation: the pilot's checks, the "
         "airspace and the operator's permission come first. Record raw clips only — the app's auto-edited QuickShots "
         "and MasterShots videos never reach the cut.", "",
         "## Before any preset", ""]
    b = dji["before_any_preset"]
    L += [f"- Hover at least {b['hover_min_m']} m up; the subject within {b['subject_max_m']} m; light between "
          f"{b['lux'][0]:,} and {b['lux'][1]:,} lux.", "- Do not run a preset when: " + "; ".join(b["dont_use"]) + "."]
    at = dji["activetrack_m"]
    L += [f"- ActiveTrack: people {at['people']['distance'][0]}–{at['people']['distance'][1]} m away, "
          f"{at['people']['height'][0]}–{at['people']['height'][1]} m up; vehicles {at['vehicles']['distance'][0]}–"
          f"{at['vehicles']['distance'][1]} m; subjects under {at['subject_max_mps']} m/s ({at['note']}).", "",
          "## Shots", "", "| Shot | Our move | Fly it with | Set | Clearance | Target |", "|---|---|---|---|---|---|"]
    holes = []
    for s, (p, fm, txt) in sorted(AQ._aerial_prompts(job).items()):
        d = AQ.parse_decl(fm.get("aerial"))
        mv, row = AQ.resolve_move(d.get("move"))
        if not row:
            continue
        if row["kind"] == "planet" or row.get("effect") and mv != "little_planet":
            L.append(f"| {s} | {mv} | not flown — generated (planet scale) | — | — | — |")
            continue
        pick = d.get("preset", "").lower()
        cands = presets_for(mv)
        chosen = next(((k, v) for k, v in cands if k == pick), cands[0] if cands else None)
        if chosen:
            k, v = chosen
            fly, setv, clr = v["app"], v.get("set", ""), v.get("clearance", "—")
        else:
            fly, setv, clr = "by hand (Cine mode; Cruise Control for an even speed)", "—", "—"
        tgt = []
        for key, unit in (("speed_mps", "m/s"), ("radius_m", "m radius"), ("altitude_m", "m up"),
                          ("distance_m", "m off"), ("secs_per_turn", "s a turn"), ("deg_per_s", "°/s")):
            if row.get(key):
                tgt.append(f"{row[key][0]:g}–{row[key][1]:g} {unit}")
        if row.get("max_turns"):
            tgt.append(f"≤ {row['max_turns']:g} turns")
        L.append(f"| {s} | {mv} | {fly} | {setv} | {clr} | {', '.join(tgt) or '—'} |")
        if mv == "hole_flyover":
            holes.append((s, d))
    c = _load(job, COURSE)
    if c and (holes or c.get("holes")):
        L += ["", "## Hole flyovers — Waypoint Flight", "",
              "One saved route per hole, flown the same way on every hole and re-flown in other light. Heading: Follow "
              "Course. The route curves between points and can dip below them: check what is under it. Points come "
              "from a course map or survey, or are pinned on site.", ""]
        lo, hi = T["moves"]["hole_flyover"]["speed_mps"]
        for h in c.get("holes") or []:
            r = h.get("route") or {}
            def pt(k):
                v = r.get(k)
                return f"{v[0]:.6f}, {v[1]:.6f}" if isinstance(v, list) and len(v) >= 2 else "pin on site"
            L += [f"**Hole {h['hole']}** — par {h.get('par') or '?'}, {h.get('yards') or '?'} yd; {h.get('strategy') or 'strategy line to fill'}",
                  "", "| Point | Where | Altitude | Gimbal | Speed to next | Hover |", "|---|---|---|---|---|---|",
                  f"| 1 tee | {pt('tee')} | 3 m | −10° | {lo:g} m/s | 0 s |",
                  f"| 2 landing area | {pt('landing')} | 3–5 m (climb late) | −20° | {(lo + hi) / 2:g} m/s | 0 s |",
                  f"| 3 over the hazards | {pt('hazard')} | 25–40 m | −35° | {(lo + hi) / 2:g} m/s | 0 s |",
                  f"| 4 approach | {pt('green')} | 10–15 m | −50° | {lo:g} m/s | 2 s |", ""]
    p = os.path.join(job, PILOT)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return p


def check_job(job: str) -> tuple[list, list]:
    """(problems that refuse lock, notes) — only when the job has a course or a property file."""
    P, W = [], []
    has_c, has_p = os.path.isfile(os.path.join(job, COURSE)), os.path.isfile(os.path.join(job, PROPERTY))
    if not (has_c or has_p):
        return P, W
    if has_c:
        p_, w_ = course_lint(job); P += p_; W += w_
    if has_p:
        p_, w_ = property_lint(job); P += p_; W += w_
    p_, w_ = overlays(job); P += p_; W += w_
    rp = os.path.join(job, RIGHTS)
    if not os.path.isfile(rp):
        P.append(f"no {RIGHTS} — `flyover.py rights <job>` writes the rights and disclosure manifest")
    else:
        newest = max([os.path.getmtime(os.path.join(job, x)) for x in (COURSE, PROPERTY) if os.path.isfile(os.path.join(job, x))])
        if os.path.getmtime(rp) < newest:
            W.append(f"{RIGHTS} is older than the course or property file — write it again")
    return P, W


def private_block(job: str) -> str | None:
    """C5 for gate.py: the reason a publish is refused, or None."""
    for rel in (COURSE, PROPERTY):
        d = _load(job, rel)
        if d and not d.get("_error") and d.get("private", True) is not False:
            return (f"{rel} is private: true — house rule C5 (2026-10-26): the spec piece stays private until a legal "
                    f"view clears public promotion; set private: false only then")
    return None


# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────
def selftest() -> int:
    fails = []

    def check(name, ok, detail=""):
        print(("PASS  " if ok else "FAIL  ") + name + (f" — {detail}" if detail and not ok else ""))
        if not ok:
            fails.append(name)
    import provenance as PV
    with tempfile.TemporaryDirectory() as job:
        course_init(job, "", preset="old-course")
        c = json.load(open(os.path.join(job, COURSE)))
        check("the Old Course preset carries only the checked facts", c["facts"]["par"] == 72 and len(c["holes"]) == 18
              and c["holes"][16]["landmarks"][0] == "the Road Hole" and c["holes"][0]["green"] == "single"
              and c["holes"][1]["green"] == "double" and c["holes"][6]["par"] is None and c["private"] is True)
        check("the spec label names the operator (C5)", c["spec_label"] == "Spec, not affiliated with St Andrews Links Trust")
        P, W = course_lint(job)
        check("an unfilled card refuses: no par, no yards, no strategy, no seed", any("hole 7: no par" in x for x in P)
              and any("no strategy line" in x for x in P) and any("no seed photo" in x for x in P))
        os.makedirs(os.path.join(job, "02-startframes"))
        for h in c["holes"]:
            sp = os.path.join(job, "02-startframes", f"H{h['hole']:02d}.jpg")
            open(sp, "wb").write(f"photo {h['hole']}".encode())
            json.dump({"source": "licensed", "sha256": AQ.sha256_file(sp), "clearance": "CLEARED by Dana on 2026-10-26",
                       "holder": "Aerial Co", "licence": {"name": "commercial"}}, open(PV.sidecar_path(sp), "w"))
            h.update(par=4, yards=400, strategy="down the left half", seed=f"02-startframes/H{h['hole']:02d}.jpg",
                     sources={"par": "club card 2026", "yards": "club card 2026"})
        c["holes"][0]["par"] = 5
        json.dump(c, open(os.path.join(job, COURSE), "w"))
        P, W = course_lint(job)
        check("pars that do not add up to the course refuse", any("add up to 73" in x for x in P), json.dumps(P))
        c["holes"][0]["par"] = 4
        json.dump(c, open(os.path.join(job, COURSE), "w"))
        P, W = course_lint(job)
        check("a filled card passes; yards that differ from the course only note", not P and any("7200" in x for x in W), json.dumps(P + W))
        p = hole_prompt(job, 17)
        txt = open(p).read()
        check("the hole prompt is declared, on its seed, a draft", "move=hole_flyover" in txt and "start_frame: 02-startframes/H17.jpg" in txt
              and "the Road Hole" in txt and "DRAFT" in txt and "17th green" in txt)
        import prompt_lint as PL
        fm, body = PL.split_front(PL.read(p))
        f_, w_ = [], []
        AQ.lint_aerial(fm, PL.prompt_text(body), job, "broll", f_.append, w_.append)
        check("the drafted hole prompt passes the aerial lint", not f_, json.dumps(f_))
        try:
            hole_prompt(job, 17)
            check("a second draft never overwrites the director's", False)
        except SystemExit:
            check("a second draft never overwrites the director's", True)
        os.makedirs(os.path.join(job, TITLES))
        json.dump({"id": "T7", "kind": "hole", "content": {"title": "Hole 7", "lines": ["Par 4 · 400 yards"]}},
                  open(os.path.join(job, TITLES, "T7.title.json"), "w"))
        check("an overlay that matches its card passes", not overlays(job)[0])
        json.dump({"id": "T8", "kind": "hole", "content": {"title": "Hole 8", "lines": ["Par 3 · 178 yards"]}},
                  open(os.path.join(job, TITLES, "T8.title.json"), "w"))
        P, _ = overlays(job)
        check("an overlay that differs from its card refuses", any("par 3" in x for x in P) and any("178 yards" in x for x in P), json.dumps(P))
        json.dump({"id": "T9", "kind": "place", "content": {"place": "The official home of golf"}},
                  open(os.path.join(job, TITLES, "T9.title.json"), "w"))
        check("an overlay that implies affiliation refuses (C5)", any("affiliation" in x for x in overlays(job)[0]))
        os.remove(os.path.join(job, TITLES, "T8.title.json")); os.remove(os.path.join(job, TITLES, "T9.title.json"))
        P, W = check_job(job)
        check("lock refuses with no rights manifest", any("RIGHTS.md" in x for x in P))
        rp, rP = rights(job)
        R = open(rp).read()
        check("the rights manifest lists the seeds, the private flag and the spec label",
              "Aerial Co" in R and "Private." in R and "Spec, not affiliated with St Andrews Links Trust" in R and not rP)
        check("with the manifest written, the lock passes", not check_job(job)[0], json.dumps(check_job(job)[0]))
        check("a private course blocks publishing (C5)", bool(private_block(job)))
        c["private"] = False; json.dump(c, open(os.path.join(job, COURSE), "w"))
        check("private: false lifts it", private_block(job) is None)
        sp = pilot(job)
        S = open(sp).read()
        check("the pilot sheet names Waypoint Flight for the hole and the preset clearances",
              "| H17 | hole_flyover | Waypoint Flight |" in S and "300 and 10,000 lux" in S and "**Hole 17**" in S, S[:600])
        check("presets map both ways: a Circle and a POI fly an orbit", [k for k, _ in presets_for("orbit")][:2] == ["circle", "poi"])
    with tempfile.TemporaryDirectory() as job:
        property_init(job, "12 Harbour Row")
        d = json.load(open(os.path.join(job, PROPERTY)))
        os.makedirs(os.path.join(job, "02-startframes"))
        for nm in ("kitchen", "exterior"):
            sp = os.path.join(job, "02-startframes", f"{nm}.jpg"); open(sp, "wb").write(nm.encode())
            json.dump({"source": "client-supplied", "sha256": AQ.sha256_file(sp), "clearance": "CLEARED by Dana on 2026-10-26"},
                      open(PV.sidecar_path(sp), "w"))
        d["rooms"] = [{"name": "the kitchen", "seed": "02-startframes/kitchen.jpg"}]
        d["exterior"]["seed"] = "02-startframes/exterior.jpg"
        json.dump(d, open(os.path.join(job, PROPERTY), "w"))
        check("a property with its rooms on real photographs passes", not property_lint(job)[0], json.dumps(property_lint(job)[0]))
        os.makedirs(os.path.join(job, "01-script", "prompts"))
        open(os.path.join(job, "01-script", "prompts", "P2.clip.prompt.md"), "w").write(
            "---\nshot: P2\nkind: clip\naspect: 9:16\naerial: move=cinewhoop_oner, function=journey, subject=the wine cellar, "
            "final=the cellar door, place=real, lane=property\n---\nan energetic sweep through the cellar\n")
        P, W = property_lint(job)
        check("an invented room refuses, an energetic interior notes", any("wine cellar" in x for x in P) and any("car advert" in x for x in W))
    print("\nselftest OK — the course card holds only checked facts and refuses gaps and wrong sums; the hole prompt is a "
          "declared draft on its seed; overlays must match the card and claim no affiliation; the rights manifest and "
          "the private flag hold publishing; the pilot sheet names the preset or Waypoint Flight; an invented room "
          "refuses" if not fails else f"\nFAIL — {len(fails)} failing")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("course"); cs = c.add_subparsers(dest="sub")
    p = cs.add_parser("init"); p.add_argument("job"); p.add_argument("--name", default=""); p.add_argument("--holes", type=int, default=18)
    p.add_argument("--preset", choices=sorted(PRESETS)); p.add_argument("--operator", default="")
    p.add_argument("--public", action="store_true"); p.add_argument("--force", action="store_true")
    p = cs.add_parser("lint"); p.add_argument("job")
    h = sub.add_parser("hole"); hs = h.add_subparsers(dest="sub")
    p = hs.add_parser("prompt"); p.add_argument("job"); p.add_argument("--hole", type=int, required=True)
    p.add_argument("--model", default="seedance_2_5"); p.add_argument("--duration", type=int, default=8)
    pr = sub.add_parser("property"); ps = pr.add_subparsers(dest="sub")
    p = ps.add_parser("init"); p.add_argument("job"); p.add_argument("--name", required=True)
    p.add_argument("--public", action="store_true"); p.add_argument("--force", action="store_true")
    p = ps.add_parser("lint"); p.add_argument("job")
    for n in ("overlays", "rights", "pilot", "check"):
        p = sub.add_parser(n); p.add_argument("job")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    def show(P, W):
        for x in P:
            print("REFUSE", x)
        for x in W:
            print("NOTE  ", x)
        return 1 if P else 0
    if a.cmd == "course" and a.sub == "init":
        print(os.path.relpath(course_init(a.job, a.name, a.holes, a.preset, a.operator, a.public, a.force), a.job)); return 0
    if a.cmd == "course" and a.sub == "lint":
        return show(*course_lint(a.job))
    if a.cmd == "hole" and a.sub == "prompt":
        print(os.path.relpath(hole_prompt(a.job, a.hole, a.model, a.duration), a.job)); return 0
    if a.cmd == "property" and a.sub == "init":
        print(os.path.relpath(property_init(a.job, a.name, a.public, a.force), a.job)); return 0
    if a.cmd == "property" and a.sub == "lint":
        return show(*property_lint(a.job))
    if a.cmd == "overlays":
        return show(*overlays(a.job))
    if a.cmd == "rights":
        p, P = rights(a.job); print(os.path.relpath(p, a.job)); return show(P, [])
    if a.cmd == "pilot":
        print(os.path.relpath(pilot(a.job), a.job)); return 0
    if a.cmd == "check":
        return show(*check_job(a.job))
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
