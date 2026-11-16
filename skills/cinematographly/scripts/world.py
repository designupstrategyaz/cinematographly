#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""world.py — the world of an exterior designed once, before the frames, and inherited by every frame and clip.

Why it exists (2026-10-27, lab-00020). A demo was killed because the plugin approached an exterior shot by shot:
birds and a boat were added to start and end frames as separate image edits, with no count, heading or speed, so
the video model invented flocks and swoops to bridge them, and every regeneration re-rolled them. A species that
does not live there was noticed and let through. A long route was squeezed into one 5 s clip at ~12× the move
table's speed, and the warning went unanswered. Four changes of direction in one day were never locked. The owner:
*"don't focus on the golf itself, but how the plugin approached the scenario."* The council's jury was unanimous
on the core (references/world-design.md).

The card — 00-brief/world/<LOC>.world.json, one per location (a second time of day or weather is a second
location id). Fields: the place (real or invented, a biome), the date and time, the sun's azimuth and elevation
(from NOAA's calculator, with the source), the wind (Beaufort force and the direction it blows FROM — it drives the
grass, trees, flags, water, smoke, cloud drift and which way birds face), the sky (WMO genus, level, cover, drift),
the visibility in km and three depth layers with a known-size anchor, the land, the water, the subjects that are
NOT background, and the background life, cast like extras: species, count, behaviour, heading, speed with its
source, frame position, the shots it is in, and which of the start and end frames carry it.

Commands
  init <job> --location <LOC> [--real | --invented] [--from <another card>]     a card to fill (NEEDS marks)
  check <job> [--location <LOC>]          the card's rules (what `gate.py approve world:<LOC>` refuses on)
  cues <job> --location <LOC> [--shot <S>] the [ENVIRONMENT] and [LIGHTING] lines the card implies, for a prompt
  accept <job> <prompt.md> --reason "…"   answer the must-answer (⚑) warnings on one prompt before spend
  stop <job> --what "…"                    a noticed problem becomes a stop: no prompt lints while it is open
  close <job> --stop <N> --fixed "…"       closed by a fix (the producer)
  close <job> --stop <N> --override --quote "<the owner's words>"   closed by the owner's override
  override <job> --location <LOC> --life <ID> --quote "<the owner's words>"   a species off the place's list
  read <job> --shot <S> --clip <file> --movers <N> --obs "…" [--new "none"]   the returned clip against the card
  status <job>                             cards, approvals, dependent prompts, stops, reads
  console <job>                            07-edit/resolve-production-console.world.py — a marker per exterior
                                           clip carrying its world, coloured by the read
  --selftest

Enforced elsewhere:
  * prompt_lint.py calls lint_prompt() on every frame and clip prompt: a `world: <LOC>` prompt needs an approved,
    current card; a mover the card does not cast refuses; a sky, wind or night word that contradicts the card
    refuses; an image edit may not add a mover; an aerial needs a card (or `world: none (<why>)`); the ⚑ warnings
    (the motion budget, an exterior with no card, a position change to check) refuse until answered here.
  * gate.py approve world:<LOC> runs check_card(); approve clips runs check_reads().
Thresholds marked [assumed] wait for real jobs to calibrate them.
Exit codes: 0 ok · 1 refused / problems · 2 usage or IO error.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

WDIR = os.path.join("00-brief", "world")
QDIR = os.path.join("09-qa", "world")
ANSWERS = os.path.join(QDIR, "ANSWERS.json")
STOPS = os.path.join(QDIR, "STOPS.json")
CONSOLE = os.path.join(HERE, "resolve-production-console.py")
CONSOLE_COPY = "resolve-production-console.world.py"
NEEDS = "<NEEDS>"
MUST = "⚑"                       # a warning that must be answered before spend (world.py accept)

GENERA = ("cirrus", "cirrocumulus", "cirrostratus", "altocumulus", "altostratus", "nimbostratus",
          "stratocumulus", "stratus", "cumulus", "cumulonimbus")
LEVEL = {"cirrus": "high", "cirrocumulus": "high", "cirrostratus": "high", "altocumulus": "middle",
         "altostratus": "middle", "nimbostratus": "middle", "stratocumulus": "low", "stratus": "low",
         "cumulus": "low", "cumulonimbus": "low"}                 # WMO International Cloud Atlas, the levels table
COVERS = ("clear", "few", "scattered", "broken", "overcast")
# Beaufort 0–8 (Royal Meteorological Society; 10-min mean at 10 m): (km/h, land, sea)
BEAUFORT = {0: ("< 1", "smoke rises straight up", "the sea like a mirror"),
            1: ("1–5", "smoke drifts with the wind, vanes still", "ripples"),
            2: ("6–11", "leaves rustle, wind felt on the face", "small wavelets"),
            3: ("12–19", "leaves and small twigs in constant motion, light flags extended", "large wavelets"),
            4: ("20–28", "dust and loose paper raised, small branches move", "small waves, fairly frequent whitecaps"),
            5: ("29–38", "small leafy trees sway", "moderate waves, many whitecaps"),
            6: ("38–49", "large branches move, wires whistle", "large waves, extensive foam crests"),
            7: ("50–61", "whole trees move", "foam blown in streaks"),
            8: ("62–74", "twigs break off trees", "crests breaking into spindrift")}
BIRD_FLY_MS = (8.0, 22.0)        # Pennycuick et al. 2013: 31 species' mean air speeds 11–20.6 m/s; widened [assumed]
STILL = ("resting", "perched", "moored", "parked", "grazing", "standing", "sitting", "floating")
FLYING = ("crossing", "soaring", "circling", "gliding", "flying", "landing", "taking-off", "diving", "hovering")
LIFE_KEYS = ("id", "species", "count", "behaviour", "heading", "speed_ms", "speed_source", "frame", "carry",
             "shots", "in_frames")
BIRD_WORDS = ("bird", "gull", "seagull", "pelican", "crow", "rook", "jackdaw", "pigeon", "dove", "swallow", "swift",
              "martin", "starling", "goose", "geese", "duck", "swan", "heron", "egret", "eagle", "hawk", "falcon",
              "kestrel", "buzzard", "kite", "owl", "tern", "gannet", "cormorant", "oystercatcher", "curlew", "lapwing",
              "plover", "sandpiper", "skylark", "lark", "sparrow", "finch", "robin", "magpie", "parrot", "flamingo",
              "flock", "murmuration")
ANIMAL_WORDS = ("dog", "cat", "horse", "deer", "stag", "sheep", "cow", "cattle", "goat", "rabbit", "hare", "fox",
                "squirrel", "butterfly", "butterflies", "dolphin", "whale", "seal")
VEHICLE_WORDS = ("car", "van", "truck", "lorry", "bus", "bicycle", "bike", "cyclist", "motorbike", "motorcycle",
                 "scooter", "tram", "train", "plane", "aeroplane", "airplane", "aircraft", "helicopter", "buggy",
                 "cart", "tractor")
VESSEL_WORDS = ("boat", "ship", "yacht", "sailboat", "sailing boat", "ferry", "kayak", "canoe", "trawler", "tanker",
                "dinghy", "rowing boat", "fishing boat", "speedboat")
MOVER_RE = re.compile(r"\b(" + "|".join(sorted({re.escape(w) for w in BIRD_WORDS + ANIMAL_WORDS + VEHICLE_WORDS +
                                                VESSEL_WORDS}, key=len, reverse=True)) + r")(e?s)?\b", re.I)
EDIT_ADD_RE = re.compile(r"\b(add|adding|insert|inserting|place|put|include|introduce)\b[^.\n]{0,40}?" +
                         MOVER_RE.pattern, re.I)
EXTERIOR_RE = re.compile(r"\b(sky(?![- ]blue)|skies|clouds?|horizon|ocean|sea(?![- ]?(?:salt|food|shell|weed))|beach|"
                         r"coast(?:line)?|shore(?:line)?|dunes?|meadow|fairway|golf course|street|road|car park|"
                         r"parking lot|forest|woodland|the woods|mountains?|hills(?:ide)?|valley|river|lake|outdoors?|"
                         r"exterior|open air|aerial|drone shot|cliffs?|backyard|back garden|"
                         r"(?:in|into|across|through) (?:the|a) (?:garden|park))\b", re.I)
SKY_CLASS = [("clear", re.compile(r"\b(clear sky|cloudless|no clouds|clear blue sky)\b", re.I)),
             ("overcast", re.compile(r"\b(overcast|grey sky|gray sky|leaden sky|blanket of cloud|stratus)\b", re.I)),
             ("storm", re.compile(r"\b(storm clouds?|thunderhead|cumulonimbus|thunderstorm|anvil cloud)\b", re.I)),
             ("cumulus", re.compile(r"\b(cumulus|puffy (white )?clouds|fluffy (white )?clouds|fair[- ]weather clouds)\b", re.I)),
             ("cirrus", re.compile(r"\b(cirrus|wispy clouds|mares'? tails)\b", re.I))]
CALM_RE = re.compile(r"\b(windless|no wind|flat calm|dead calm|glassy|mirror[- ]like|still air|motionless flags?)\b", re.I)
WINDY_RE = re.compile(r"\b(windswept|gale|storm[- ]force|howling wind|whitecaps|white horses|crashing waves|"
                      r"bent (trees|palms)|flags? snapping)\b", re.I)
NIGHT_RE = re.compile(r"\b(night|midnight|moonlit|starry sky|under the stars)\b", re.I)
GOLDEN_RE = re.compile(r"\b(golden hour|sunset|sunrise|dawn|dusk|low sun)\b", re.I)
MAX_GROUPS = 1                   # cast mover groups per shot, the default [assumed] (jury K3)
GOLDEN_MAX_ELEV = 15.0           # "golden hour" words with the sun higher than this read as a mismatch [assumed]


# ── small things ───────────────────────────────────────────────────────────────────────────────────────────
def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def jload(p: str):
    try:
        return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None
    except ValueError:
        return None


def jsave(p: str, d) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def card_path(job: str, loc: str) -> str:
    return os.path.join(job, WDIR, f"{loc}.world.json")


def cards(job: str) -> dict:
    out = {}
    for p in sorted(glob.glob(os.path.join(job, WDIR, "*.world.json"))):
        out[os.path.basename(p)[:-len(".world.json")]] = p
    return out


def verify_quote(quote: str) -> str | None:
    q = (quote or "").strip()
    if len(q.split()) < 2:
        return "--quote must be the owner's reply verbatim (two words or more)"
    try:
        import gate as G
        why = G.quote_refusal(q, G.active_job()[0])   # (3.1) verified, or present on a hookless studio (build review 3:
        #                                             never on a job another home checked) — never assumed
    except Exception as e:                # noqa: BLE001 — (3.1) a check that cannot run refuses
        return f"the quote cannot be checked ({type(e).__name__}) — nothing is recorded"
    return (why + " — ask the approver, then record their words") if why else None


def approvals(job: str) -> list:
    p = os.path.join(job, "00-brief", "APPROVALS.md")
    rows = []
    if os.path.isfile(p):
        for line in open(p, encoding="utf-8"):
            if not line.startswith("|") or re.match(r"^\|\s*(ts|-+)\s*\|", line):
                continue
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) >= 6:
                rows.append({"stage": c[1], "artifact": c[4], "sha": c[5]})
    return rows


def approval_state(job: str, loc: str) -> str | None:
    """None when world:<LOC> is approved on the card's current bytes; else why not."""
    p = card_path(job, loc)
    if not os.path.isfile(p):
        return f"no world card {os.path.relpath(p, job)} (world.py init {job} --location {loc})"
    row = next((r for r in reversed(approvals(job)) if r["stage"].lower() == f"world:{loc}".lower()), None)
    if not row:
        return (f"world:{loc} is not approved — the owner approves the card before any frame is made "
                f"(gate.py approve world:{loc} --artifact {os.path.relpath(p, job)} --by … --quote \"…\")")
    if not sha256_file(p).startswith(row["sha"]):
        return (f"the world card {loc} changed after it was approved — every frame and clip of this location is "
                f"stale until the owner approves it again (a change of direction, references/world-design.md §6)")
    return None


# ── the card ───────────────────────────────────────────────────────────────────────────────────────────────
def template(loc: str, real: bool) -> dict:
    return {
        "location": loc, "real_place": real, "place": NEEDS if real else "invented — say the biome", "biome": NEEDS,
        "season": NEEDS, "date": NEEDS, "time": NEEDS, "timezone": NEEDS,
        "sun": {"azimuth_deg": NEEDS, "elevation_deg": NEEDS,
                "source": "NOAA GML solar calculator (gml.noaa.gov/grad/solcalc), read <date>"},
        "wind": {"beaufort": NEEDS, "from_deg": NEEDS, "note": "the direction it blows FROM"},
        "sky": {"genus": [NEEDS], "cover": NEEDS, "drift_toward_deg": NEEDS, "light": NEEDS},
        "visibility_km": NEEDS,
        "layers": {"near": {"what": NEEDS, "distance_m": [0, 10]}, "middle": {"what": NEEDS, "distance_m": [10, 300]},
                   "far": {"what": NEEDS, "distance_m": [300, 5000]}},
        "scale_anchors": [NEEDS],
        "land": NEEDS, "water": None, "subjects": [], "life": [], "max_movers_per_shot": MAX_GROUPS,
        "plausible": {"species": [], "vessels": [], "vehicles": [], "plants": []},
        "_help": "Fill every NEEDS mark. Life is cast like extras (references/world-design.md §4): "
                 "{id, species, count, behaviour, heading, speed_ms, speed_source, frame, carry, shots, in_frames}. "
                 "No life is the default. A real place lists its species with a source (an eBird bar chart, week).",
    }


def _needs(x) -> bool:
    if isinstance(x, str):
        return NEEDS in x
    if isinstance(x, dict):
        return any(_needs(v) for v in x.values())
    if isinstance(x, list):
        return any(_needs(v) for v in x)
    return False


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def kind_of(name: str) -> str:
    """bird | vessel | vehicle | animal, from any word of the name ('herring gull' is a bird)."""
    low = name.lower()
    toks = re.findall(r"[a-z]+", low)
    if any(t.rstrip("s") == b.rstrip("s") or t == b for t in toks for b in BIRD_WORDS):
        return "bird"
    if any(v in low for v in VESSEL_WORDS):
        return "vessel"
    if any(t.rstrip("s") == v or t == v for t in toks for v in VEHICLE_WORDS):
        return "vehicle"
    return "animal"


def check_card(job: str, loc: str) -> tuple:
    """(problems, notes) — the card's own rules."""
    P, W = [], []
    p = card_path(job, loc)
    d = jload(p)
    if d is None:
        return [f"no readable card {os.path.relpath(p, job)}"], W
    if _needs(d):
        P.append("unfilled <NEEDS> fields — every field is decided before a frame is made")
    for k in ("place", "biome", "season", "date", "time", "land"):
        if not str(d.get(k) or "").strip():
            P.append(f"`{k}` is empty")
    sun = d.get("sun") or {}
    az, el = _num(sun.get("azimuth_deg")), _num(sun.get("elevation_deg"))
    if az is None or not 0 <= az <= 360 or el is None or not -90 <= el <= 90:
        P.append("sun: azimuth 0–360 and elevation −90–90, from NOAA's solar calculator for the place, date and time")
    if not str(sun.get("source") or "").strip() or "<date>" in str(sun.get("source")):
        P.append("sun: name the source and the day it was read")
    wind = d.get("wind") or {}
    bf, wf = _num(wind.get("beaufort")), _num(wind.get("from_deg"))
    if bf is None or not 0 <= bf <= 12 or bf != int(bf):
        P.append("wind: a Beaufort force 0–12 (it decides grass, trees, flags, water and cloud drift together)")
    if wf is None or not 0 <= wf <= 360:
        P.append("wind: from_deg 0–360, the direction it blows from")
    sky = d.get("sky") or {}
    gen = [str(g).lower() for g in (sky.get("genus") or [])]
    cover = str(sky.get("cover") or "").lower()
    if cover not in COVERS:
        P.append(f"sky: cover is one of {', '.join(COVERS)}")
    if cover == "clear":
        if gen and gen != ["clear"]:
            P.append("sky: a clear sky has no genus — genus: [\"clear\"]")
    else:
        bad = [g for g in gen if g not in GENERA]
        if not gen or bad:
            P.append(f"sky: genus from the WMO's ten ({', '.join(GENERA)}){' — not ' + ', '.join(bad) if bad else ''}")
        if len({LEVEL.get(g) for g in gen if g in LEVEL}) < len([g for g in gen if g in LEVEL]):
            W("sky: two genera on the same level — real skies layer by level (WMO); check it is one deck, not two")
    vis = _num(d.get("visibility_km"))
    if vis is None or vis <= 0:
        P.append("visibility_km: a number (fog < 1, mist 1–2, haze 2–5); it sets how fast the far layer fades")
    lay = d.get("layers") or {}
    for k in ("near", "middle", "far"):
        L = lay.get(k) or {}
        if not str(L.get("what") or "").strip():
            P.append(f"layers.{k}: what is in it — depth in far space comes from occlusion, relative size, height in "
                     f"the frame and haze (Cutting & Vishton)")
    if not [a for a in (d.get("scale_anchors") or []) if str(a).strip()]:
        P.append("scale_anchors: at least one object of known size (a person, a door, a 1.2 m post)")
    water = d.get("water")
    if isinstance(water, dict) and bf is not None and 0 <= bf <= 8:
        st = str(water.get("state") or "").lower()
        if st:
            calm = re.search(r"calm|glassy|mirror|flat", st)
            rough = re.search(r"whitecap|white horse|foam|breaking|rough", st)
            if calm and bf >= 3:
                P.append(f"water: '{st}' at Beaufort {int(bf)} — the sea there is {BEAUFORT[int(bf)][2]}")
            if rough and bf <= 3:
                P.append(f"water: '{st}' at Beaufort {int(bf)} — the sea there is {BEAUFORT[int(bf)][2]}")
    life = d.get("life") or []
    names = {str(s.get("name") if isinstance(s, dict) else s).lower()
             for grp in ("species", "vessels", "vehicles") for s in (d.get("plausible") or {}).get(grp) or []}
    srcd = all(isinstance(s, dict) and str(s.get("source") or "").strip()
               for grp in ("species", "vessels", "vehicles") for s in (d.get("plausible") or {}).get(grp) or [])
    if life and d.get("real_place") and not srcd:
        P.append("plausible: every species, vessel and vehicle on the place's list names its source (an eBird bar "
                 "chart for the region and week, a harbour record) — looked up, not imagined")
    per_shot: dict = {}
    cap = int(_num(d.get("max_movers_per_shot")) or MAX_GROUPS)
    for e in life:
        lid = str(e.get("id") or "?")
        miss = [k for k in LIFE_KEYS if e.get(k) in (None, "", [])]
        if miss:
            P.append(f"life {lid}: missing {', '.join(miss)}")
            continue
        sp = str(e["species"]).lower()
        if d.get("real_place") and sp not in names and not e.get("override"):
            P.append(f"life {lid}: '{e['species']}' is not on this place's list — a real place gets its real life "
                     f"(add it with its source, or the owner overrides: world.py override)")
        cnt = _num(e.get("count"))
        if cnt is None or cnt < 1 or cnt != int(cnt):
            P.append(f"life {lid}: count is a whole number")
        beh = str(e["behaviour"]).lower()
        spd = _num(e.get("speed_ms"))
        if spd is None or spd < 0:
            P.append(f"life {lid}: speed_ms is a number (0 when it is still)")
        elif any(b in beh for b in STILL) and spd > 0.5:
            P.append(f"life {lid}: {beh} at {spd:g} m/s — a still behaviour has a speed of 0")
        elif kind_of(sp) == "bird" and any(b in beh for b in FLYING) and not BIRD_FLY_MS[0] <= spd <= BIRD_FLY_MS[1]:
            P.append(f"life {lid}: a flying bird at {spd:g} m/s — measured mean air speeds run 11–20.6 m/s "
                     f"(Pennycuick et al. 2013); the card allows {BIRD_FLY_MS[0]:g}–{BIRD_FLY_MS[1]:g} [assumed]")
        if kind_of(sp) != "bird" and spd and "unverified" not in str(e["speed_source"]).lower() \
                and not re.search(r"\d", str(e["speed_source"])):
            W(f"life {lid}: no sourced speed table for {kind_of(sp)}s — say where {spd:g} m/s comes from, or mark it "
              f"unverified")
        if any(b in beh for b in ("landing", "taking-off")) and "into the wind" not in str(e["heading"]).lower():
            W(f"life {lid}: birds land and take off into the wind — say the heading against the card's wind")
        inf = str(e["in_frames"]).lower()
        if inf not in ("start", "both", "none", "end"):
            P.append(f"life {lid}: in_frames is start, both or none")
        elif inf == "end":
            P.append(f"life {lid}: in the end frame alone — the model would invent where it came from. Put it in the "
                     f"start frame (and the end frame where its speed takes it), or in neither (jury K4)")
        elif inf == "both":
            a_, b_ = str(e.get("start_pos") or ""), str(e.get("end_pos") or "")
            if not a_ or not b_:
                P.append(f"life {lid}: in both frames — give start_pos and end_pos (thirds of the frame is enough)")
            else:
                order = {"left": 0, "centre": 1, "center": 1, "middle": 1, "right": 2}
                xa = next((v for k, v in order.items() if k in a_.lower()), None)
                xb = next((v for k, v in order.items() if k in b_.lower()), None)
                hd = str(e["heading"]).lower()
                if xa is not None and xb is not None and (("left to right" in hd and xb < xa) or
                                                          ("right to left" in hd and xb > xa)):
                    P.append(f"life {lid}: heading '{e['heading']}' but it ends at '{b_}' from '{a_}' — the frames "
                             f"disagree with the motion")
        shots = e["shots"] if isinstance(e["shots"], list) else [e["shots"]]
        for s in shots:
            per_shot.setdefault(str(s), []).append(lid)
    for s, ids in per_shot.items():
        if s != "all" and len(ids) > cap:
            P.append(f"shot {s}: {len(ids)} cast groups ({', '.join(ids)}) — at most {cap} per shot [assumed]; every mover "
                     f"is a degree of freedom the model fills (VBench: multiple objects is a weak spot)")
    if per_shot.get("all") and len(per_shot["all"]) > cap:
        P.append(f"{len(per_shot['all'])} groups in every shot — at most {cap} [assumed]")
    return P, W


def cmd_init(job: str, loc: str, real: bool, src: str) -> int:
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,30}$", loc or ""):
        print("error: --location is letters, digits, - and _", file=sys.stderr)
        return 2
    p = card_path(job, loc)
    if os.path.isfile(p):
        print(f"error: {os.path.relpath(p, job)} exists — edit it (a changed card needs the owner's approval again)",
              file=sys.stderr)
        return 1
    if src:
        d = jload(src)
        if d is None:
            print(f"error: cannot read {src}", file=sys.stderr)
            return 2
        d["location"] = loc
        d["_from"] = {"file": os.path.abspath(src), "sha256": sha256_file(src), "at": now_iso()}
    else:
        d = template(loc, real)
    jsave(p, d)
    print(f"wrote {os.path.relpath(p, job)} — fill every {NEEDS}, then `world.py check`, then the owner approves it "
          f"(gate.py approve world:{loc})")
    return 0


def cues(job: str, loc: str, shot: str = "") -> dict:
    """The prompt lines the card implies — one wording, so every frame and clip says the same world."""
    d = jload(card_path(job, loc)) or {}
    bf = int(_num((d.get("wind") or {}).get("beaufort")) or 0)
    land, sea = BEAUFORT.get(bf, ("", "", ""))[1:]
    sky = d.get("sky") or {}
    gen = ", ".join(sky.get("genus") or [])
    sun = d.get("sun") or {}
    lay = d.get("layers") or {}
    life = [e for e in d.get("life") or [] if not shot or str(shot) in [str(s) for s in (e.get("shots") or [])]
            or e.get("shots") == "all" or "all" in (e.get("shots") or [])]
    env = [f"{d.get('place')}, {d.get('season')}; {d.get('land')}",
           f"wind from {(d.get('wind') or {}).get('from_deg')}°, Beaufort {bf}: {land}" + (f"; {sea}" if d.get("water") else ""),
           f"sky: {sky.get('cover')} {gen}".strip() + (f", drifting toward {sky.get('drift_toward_deg')}°" if gen and gen != "clear" else ""),
           f"visibility {d.get('visibility_km')} km: near — {(lay.get('near') or {}).get('what')}; middle — "
           f"{(lay.get('middle') or {}).get('what')}; far, softer and paler in the haze — {(lay.get('far') or {}).get('what')}"]
    for e in life:
        env.append(f"{e.get('count')} {e.get('species')} {e.get('behaviour')}, {e.get('heading')}, {e.get('frame')}")
    if not life:
        env.append("no birds, animals, boats or vehicles in the background")
    lighting = f"sun at {sun.get('elevation_deg')}° elevation from azimuth {sun.get('azimuth_deg')}°; {sky.get('light')}"
    return {"ENVIRONMENT": env, "LIGHTING": lighting}


# ── answers, stops ─────────────────────────────────────────────────────────────────────────────────────────
def _key(prompt_rel: str, warning: str) -> str:
    return hashlib.sha256((prompt_rel + "\n" + re.sub(r"\s+", " ", warning.strip())).encode()).hexdigest()[:20]


def answered(job: str, prompt_rel: str, txt_sha: str, warning: str) -> dict | None:
    d = jload(os.path.join(job, ANSWERS)) or {}
    a = d.get(_key(prompt_rel, warning))
    return a if a and a.get("prompt_sha256") == txt_sha else None


def open_stops(job: str) -> list:
    return [s for s in (jload(os.path.join(job, STOPS)) or {}).get("stops", []) if not s.get("closed")]


def cmd_accept(job: str, prompt: str, reason: str) -> int:
    if len((reason or "").split()) < 4:
        print("error: --reason in a sentence — what you checked and why the shot stands", file=sys.stderr)
        return 2
    import prompt_lint as PL
    r = PL.lint(prompt, job)
    must = [w for w in r.get("_must", [])]
    if not must:
        print("nothing to answer on this prompt")
        return 0
    rel_ = os.path.relpath(os.path.abspath(prompt), os.path.abspath(job))
    d = jload(os.path.join(job, ANSWERS)) or {}
    for w in must:
        d[_key(rel_, w)] = {"prompt": rel_, "prompt_sha256": r["_txt_sha"], "warning": w, "reason": reason.strip(),
                            "at": now_iso()}
    jsave(os.path.join(job, ANSWERS), d)
    print(f"answered {len(must)} warning(s) on {rel_} — bound to this prompt's text; a change needs a new answer")
    return 0


def cmd_stop(job: str, what: str) -> int:
    if len((what or "").split()) < 4:
        print("error: --what in a sentence — what you noticed and where", file=sys.stderr)
        return 2
    d = jload(os.path.join(job, STOPS)) or {"stops": []}
    n = len(d["stops"]) + 1
    d["stops"].append({"n": n, "what": what.strip(), "opened": now_iso(), "closed": None})
    jsave(os.path.join(job, STOPS), d)
    print(f"stop {n} open: {what.strip()} — no prompt lints, so nothing is spent, until it is closed "
          f"(world.py close {job} --stop {n} --fixed \"…\" | --override --quote \"<the owner's words>\")")
    return 0


def cmd_close(job: str, n: int, fixed: str, override: bool, quote: str) -> int:
    d = jload(os.path.join(job, STOPS)) or {"stops": []}
    s = next((x for x in d["stops"] if x["n"] == n), None)
    if not s or s.get("closed"):
        print(f"error: no open stop {n}", file=sys.stderr)
        return 1
    if override:
        e = verify_quote(quote)
        if e:
            print("REFUSED: " + e, file=sys.stderr)
            return 1
        s["closed"] = {"how": "owner override", "quote": quote.strip(), "at": now_iso()}
    else:
        if len((fixed or "").split()) < 3:
            print("error: --fixed says what changed (or --override with the owner's words)", file=sys.stderr)
            return 2
        s["closed"] = {"how": "fixed", "what": fixed.strip(), "at": now_iso()}
    jsave(os.path.join(job, STOPS), d)
    print(f"stop {n} closed ({s['closed']['how']})")
    return 0


def cmd_override(job: str, loc: str, lid: str, quote: str) -> int:
    p = card_path(job, loc)
    d = jload(p)
    if not d:
        print(f"error: no card {loc}", file=sys.stderr)
        return 1
    e = next((x for x in d.get("life") or [] if str(x.get("id")) == lid), None)
    if not e:
        print(f"error: no life entry {lid}", file=sys.stderr)
        return 1
    err = verify_quote(quote)
    if err:
        print("REFUSED: " + err, file=sys.stderr)
        return 1
    e["override"] = {"quote": quote.strip(), "at": now_iso()}
    jsave(p, d)
    print(f"life {lid} ({e.get('species')}) kept on the owner's words — the card changed, so it needs their approval "
          f"again, and the client sees the override in the card")
    return 0


# ── the prompt lint (called by prompt_lint.py) ─────────────────────────────────────────────────────────────
def lint_prompt(path: str, fm: dict, bl: dict, txt: str, kind: str, job: str, F, W, warns: list) -> dict:
    """The world rules on one frame or clip prompt. Returns {'must': [...], 'txt_sha': …} for accept."""
    import prompt_lint as PL
    rel_ = os.path.relpath(os.path.abspath(path), os.path.abspath(job)) if job else os.path.basename(path)
    txt_sha = PL.sha256_text(txt or "")
    w_raw = str(fm.get("world") or "").strip()
    loc = w_raw.split()[0] if w_raw else ""
    env = " ".join(bl.get(k, "") for k in ("ENVIRONMENT", "SETTING", "_lead")) if kind == "frame" else bl.get("MOTION", "")
    allt = " ".join(v for k, v in bl.items() if k != "SUPPRESS")
    for s in open_stops(job) if job else []:
        F(f"stop {s['n']} is open: {s['what']} — nothing is spent until it is fixed or the owner overrides it "
          f"(world.py close)")
    if w_raw.lower().startswith("none"):
        if not re.search(r"\(.{3,}\)", w_raw):
            F("`world: none` needs its reason in brackets — `world: none (a studio interior)`")
    elif loc:
        st = approval_state(job, loc) if job else "no job"
        if st:
            F(st)
        else:
            d = jload(card_path(job, loc)) or {}
            shot = str(fm.get("shot") or "")
            cast = [e for e in d.get("life") or [] if e.get("shots") == "all"
                    or shot in [str(s) for s in (e.get("shots") if isinstance(e.get("shots"), list) else [e.get("shots")])]
                    or "all" in [str(s) for s in (e.get("shots") if isinstance(e.get("shots"), list) else [])]]
            subj = " ".join(str(s) for s in d.get("subjects") or []).lower() + " " + str(fm.get("subject") or "").lower()
            castw = " ".join(f"{e.get('species')} {e.get('kind', '')}" for e in cast).lower()
            for m in MOVER_RE.finditer(env):
                w = m.group(1).lower()
                if w in subj or w.rstrip("s") in subj:
                    continue
                if w in castw or w.rstrip("s") in castw or (w in ("bird", "flock", "murmuration") and
                                                            any(kind_of(str(e.get("species"))) == "bird" for e in cast)):
                    continue
                F(f"'{m.group(0)}' in the {'[ENVIRONMENT]' if kind == 'frame' else '[MOTION]'} is not cast for shot "
                  f"{shot} in the world card {loc} — background life is cast with a count, a heading and a speed, or it "
                  f"is not in the shot (references/world-design.md §4)")
            # contradictions with the card (refuse the explicit ones, jury K2)
            sky = d.get("sky") or {}
            gen = [str(g).lower() for g in sky.get("genus") or []]
            cover = str(sky.get("cover") or "").lower()
            for cls, rx in SKY_CLASS:
                mm = rx.search(allt)
                if not mm:
                    continue
                bad = ((cls == "clear" and cover != "clear") or
                       (cls == "overcast" and cover not in ("overcast", "broken")) or
                       (cls == "storm" and "cumulonimbus" not in gen) or
                       (cls == "cumulus" and not any(g in ("cumulus", "stratocumulus", "altocumulus") for g in gen)) or
                       (cls == "cirrus" and not any(g.startswith("cirr") for g in gen)))
                if bad:
                    F(f"'{mm.group(0)}' contradicts the world card {loc} (sky: {cover} {', '.join(gen)}) — say the card's "
                      f"sky (world.py cues), or change the card and have it approved again")
            bf = _num((d.get("wind") or {}).get("beaufort"))
            if bf is not None:
                mc = CALM_RE.search(allt)
                if mc and bf >= 3:
                    F(f"'{mc.group(0)}' at Beaufort {int(bf)} — the card's wind moves {BEAUFORT.get(int(bf), ('', '?'))[1]}")
                mw = WINDY_RE.search(allt)
                if mw and bf <= 3:
                    F(f"'{mw.group(0)}' at Beaufort {int(bf)} — the card's sea is {BEAUFORT.get(int(bf), ('', '', '?'))[2]}")
            el = _num((d.get("sun") or {}).get("elevation_deg"))
            if el is not None:
                mn = NIGHT_RE.search(allt)
                if mn and el > 0:
                    F(f"'{mn.group(0)}' with the sun {el:g}° up in the card {loc}")
                mg = GOLDEN_RE.search(allt)
                if mg and el > GOLDEN_MAX_ELEV:
                    W(f"'{mg.group(0)}' with the sun {el:g}° up — golden light needs a low sun [assumed {GOLDEN_MAX_ELEV:g}°]")
            # start and end frames: the both-or-neither rule lives in the card; remind the clip which life rides on both
            if kind == "clip" and fm.get("end_frame"):
                both = [e for e in cast if str(e.get("in_frames")).lower() == "both"]
                if both:
                    W(f"{MUST} WORLD: {', '.join(str(e.get('id')) for e in both)} ride both frames — check on the two stills "
                      f"that each is where its heading and {', '.join(str(e.get('speed_ms')) for e in both)} m/s take it "
                      f"in {fm.get('duration')} s (references/world-design.md §5)")
    else:
        if kind == "clip" and fm.get("aerial"):
            F("an aerial with no `world:` — an aerial is all world: design it first (world.py init), or say "
              "`world: none (<why>)`")
        elif EXTERIOR_RE.search(env if kind == "frame" else allt):
            W(f"{MUST} WORLD: this reads as an exterior ('{EXTERIOR_RE.search(env if kind == 'frame' else allt).group(0)}') "
              f"with no `world:` card — declare one (world.py init), or `world: none (<why>)`")
    # image edits never add movers (jury B6)
    is_edit = bool(fm.get("edit_of")) or any(isinstance(r, dict) and "02-startframes" in str(r.get("file") or "")
                                             for r in fm.get("refs") or [])
    if kind == "frame" and is_edit:
        me = EDIT_ADD_RE.search(allt)
        if me:
            F(f"an edit of an approved frame adds a mover ('{me.group(0)}') — edits remove things or correct static "
              f"ones. To add life: cast it in the world card, have the card approved, regenerate the frame")
    # the must-answer warnings: from here and from the aerial lint (⚑), refused until answered
    must = [w for w in warns if w.startswith(MUST)]
    for w in must:
        a = answered(job, rel_, txt_sha, w) if job else None
        if not a:
            F(f"unanswered: {w} — fix the prompt, or answer it: world.py accept {job or '<job>'} {rel_} --reason \"…\"")
    return {"must": must, "txt_sha": txt_sha}


# ── the clip read (B12) ────────────────────────────────────────────────────────────────────────────────────
def exterior_prompts(job: str) -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(job, "01-script", "prompts", "*.clip.prompt.md"))):
        try:
            import prompt_lint as PL
            fm, _ = PL.split_front(open(p, encoding="utf-8").read())
        except Exception:                 # noqa: BLE001
            continue
        w = str(fm.get("world") or "").strip()
        if w and not w.lower().startswith("none"):
            out.append({"file": p, "shot": str(fm.get("shot") or ""), "loc": w.split()[0]})
    return out


def cmd_read(job: str, shot: str, clip: str, movers: int, obs: str, new: str) -> int:
    ex = next((e for e in exterior_prompts(job) if e["shot"] == shot), None)
    if not ex:
        print(f"error: no clip prompt for shot {shot} with a `world:` card", file=sys.stderr)
        return 1
    cp = clip if os.path.isabs(clip) else os.path.join(job, clip)
    if not os.path.isfile(cp):
        print(f"error: no such clip: {clip}", file=sys.stderr)
        return 2
    try:
        from qa_log import INTENTION
    except Exception:                     # noqa: BLE001
        INTENTION = re.compile(r"^$")
    if len((obs or "").split()) < 6 or INTENTION.match(obs or ""):
        print("REFUSED: --obs is what you SAW against the card — the movers' heading, the sky, the wind cues, the "
              "light side, anything that appeared", file=sys.stderr)
        return 1
    d = jload(card_path(job, ex["loc"])) or {}
    want = sum(int(_num(e.get("count")) or 0) for e in d.get("life") or []
               if e.get("shots") == "all" or shot in [str(s) for s in (e.get("shots") or [])])
    probs = []
    if movers != want:
        probs.append(f"{movers} mover(s) seen, the card casts {want} for {shot}")
    if (new or "").strip().lower() not in ("", "none", "nothing"):
        probs.append(f"something appeared that the card does not have: {new}")
    rec = {"shot": shot, "clip": os.path.relpath(cp, job), "clip_sha256": sha256_file(cp), "loc": ex["loc"],
           "movers": movers, "cast": want, "new": new or "none", "obs": obs.strip(),
           "verdict": "RETAKE" if probs else "PASS", "problems": probs, "at": now_iso()}
    jsave(os.path.join(job, QDIR, f"{shot}.read.json"), rec)
    print(f"{shot}: {rec['verdict']}" + ("" if not probs else " — " + "; ".join(probs)))
    return 0 if not probs else 1


def check_reads(job: str) -> list:
    """`approve clips`: every exterior clip read against its card, PASS, on bytes that still exist."""
    P = []
    for e in exterior_prompts(job):
        r = jload(os.path.join(job, QDIR, f"{e['shot']}.read.json"))
        if not r:
            P.append(f"{e['shot']}: the returned clip was not read against the world card {e['loc']} (world.py read)")
            continue
        cp = os.path.join(job, r["clip"])
        if not os.path.isfile(cp) or sha256_file(cp) != r.get("clip_sha256"):
            P.append(f"{e['shot']}: the read is about {r['clip']}, which changed or is gone — read the take you are keeping")
        elif r.get("verdict") != "PASS":
            P.append(f"{e['shot']}: the read says RETAKE — {'; '.join(r.get('problems') or [])}")
    return P


# ── Resolve ────────────────────────────────────────────────────────────────────────────────────────────────
def console_copy(job: str) -> str:
    tl = jload(os.path.join(job, "07-edit", "timeline-dump.json")) or {}
    fps = float(tl.get("fps") or 24.0)
    items = [it for it in (tl.get("tracks") or {}).get("video1") or [] if "transition" not in str(it.get("type") or "").lower()]
    mk, seen = [], set()
    for e in exterior_prompts(job):
        it = next((i for i in items if re.search(rf"(?<![A-Za-z0-9]){re.escape(e['shot'])}(?![0-9])", str(i.get("name") or ""))), None)
        if not it:
            continue
        fr = int(it.get("start") or round(float(it.get("start_s") or 0) * fps))
        while fr in seen:
            fr += 1
        seen.add(fr)
        r = jload(os.path.join(job, QDIR, f"{e['shot']}.read.json")) or {}
        c = cues(job, e["loc"], e["shot"])
        col = {"PASS": "Green", "RETAKE": "Red"}.get(r.get("verdict"), "Blue")
        mk.append((fr, col, f"World {e['loc']} · {e['shot']} — {r.get('verdict') or 'unread'}",
                   " | ".join(c["ENVIRONMENT"])[:240], max(1, int(it.get("duration") or 1)),
                   json.dumps({"world": e["loc"], "shot": e["shot"], "read": r.get("verdict")})))
    src = open(CONSOLE, encoding="utf-8").read()
    for old, new in (("MARKERS = []  # __DETECT_BEATS_MARKERS__", "MARKERS = " + repr(mk) + "  # __DETECT_BEATS_MARKERS__"),
                     ("\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False"),
                     ("\nENSURE_AUDIO_LANES = True", "\nENSURE_AUDIO_LANES = False")):
        if old not in src:
            raise RuntimeError(f"resolve-production-console.py no longer contains {old!r} — update world.console_copy()")
        src = src.replace(old, new, 1)
    out = os.path.join(job, "07-edit", CONSOLE_COPY)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(src)
    return out


def cmd_status(job: str) -> int:
    for loc, p in cards(job).items():
        P, W = check_card(job, loc)
        st = approval_state(job, loc)
        dep = [e["shot"] for e in exterior_prompts(job) if e["loc"] == loc]
        print(f"{loc}: {'approved' if not st else st} · {len(P)} problem(s) · clips {', '.join(dep) or '—'}")
        for x in P:
            print(f"   ✗ {x}")
    for s in open_stops(job):
        print(f"stop {s['n']} OPEN: {s['what']}")
    for x in check_reads(job):
        print(f"read: {x}")
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["init", "check", "cues", "accept", "stop", "close", "override", "read",
                                               "status", "console"])
    ap.add_argument("job", nargs="?")
    ap.add_argument("extra", nargs="?")
    ap.add_argument("--location", default="")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--invented", action="store_true")
    ap.add_argument("--from", dest="src", default="")
    ap.add_argument("--shot", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--what", default="")
    ap.add_argument("--stop", type=int, default=0)
    ap.add_argument("--fixed", default="")
    ap.add_argument("--override", action="store_true")
    ap.add_argument("--quote", default="")
    ap.add_argument("--life", default="")
    ap.add_argument("--clip", default="")
    ap.add_argument("--movers", type=int, default=-1)
    ap.add_argument("--obs", default="")
    ap.add_argument("--new", default="none")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd or not a.job:
        ap.print_help()
        return 2
    job = a.job
    if a.cmd == "init":
        return cmd_init(job, a.location, not a.invented, a.src)
    if a.cmd == "check":
        locs = [a.location] if a.location else list(cards(job))
        bad = 0
        for loc in locs:
            P, W = check_card(job, loc)
            for w in W:
                print(f"  note ({loc}): {w}")
            for p in P:
                print(f"  ✗ ({loc}) {p}")
            bad += len(P)
            print(f"{loc}: " + ("clean" if not P else f"{len(P)} problem(s)"))
        return 1 if bad else 0
    if a.cmd == "cues":
        c = cues(job, a.location, a.shot)
        print("[ENVIRONMENT]\n" + "\n".join(c["ENVIRONMENT"]) + "\n\n[LIGHTING]\n" + c["LIGHTING"])
        return 0
    if a.cmd == "accept":
        if not a.extra:
            print("usage: world.py accept <job> <prompt.md> --reason \"…\"", file=sys.stderr)
            return 2
        return cmd_accept(job, a.extra, a.reason)
    if a.cmd == "stop":
        return cmd_stop(job, a.what)
    if a.cmd == "close":
        return cmd_close(job, a.stop, a.fixed, a.override, a.quote)
    if a.cmd == "override":
        return cmd_override(job, a.location, a.life, a.quote)
    if a.cmd == "read":
        if a.movers < 0:
            print("error: --movers <how many birds, animals, boats or vehicles you counted>", file=sys.stderr)
            return 2
        return cmd_read(job, a.shot, a.clip, a.movers, a.obs, a.new)
    if a.cmd == "status":
        return cmd_status(job)
    if a.cmd == "console":
        print(f"wrote {console_copy(job)}")
        return 0
    return 2


# ── selftest ───────────────────────────────────────────────────────────────────────────────────────────────
def _good_card(loc: str) -> dict:
    d = template(loc, True)
    d.update({"place": "a links course on a North Sea bay", "biome": "coastal dune grassland", "season": "late spring",
              "date": "2026-05-20", "time": "18:40", "timezone": "Europe/London",
              "sun": {"azimuth_deg": 285, "elevation_deg": 14, "source": "NOAA GML solar calculator, read 2026-10-27"},
              "wind": {"beaufort": 3, "from_deg": 240},
              "sky": {"genus": ["cumulus"], "cover": "scattered", "drift_toward_deg": 60, "light": "sun out between them"},
              "visibility_km": 20,
              "layers": {"near": {"what": "marram grass on a dune lip", "distance_m": [0, 8]},
                         "middle": {"what": "the fairway and a pot bunker", "distance_m": [8, 250]},
                         "far": {"what": "the town's grey stone skyline", "distance_m": [800, 3000]}},
              "scale_anchors": ["a 1.2 m flagstick", "a walking person"],
              "land": "close-mown fairway, rough of marram and gorse, sandy paths",
              "water": {"kind": "sea", "state": "large wavelets"}, "subjects": ["the green"],
              "life": [{"id": "L1", "species": "herring gull", "count": 3, "behaviour": "crossing",
                        "heading": "left to right, quartering into the wind", "speed_ms": 12,
                        "speed_source": "Pennycuick et al. 2013 (gulls 11–14 m/s)", "frame": "upper third",
                        "carry": True, "shots": ["S1", "S2"], "in_frames": "start"}],
              "plausible": {"species": [{"name": "herring gull", "source": "eBird bar chart, Fife, week 20, read 2026-10-27"},
                                        {"name": "oystercatcher", "source": "eBird bar chart, Fife, week 20"}],
                            "vessels": [], "vehicles": [], "plants": []}})
    return d


def _selftest_quote_job() -> None:
    """(3.1.1) verify_quote passes the open job to gate.quote_refusal: on a hookless home, an unchecked quote is refused
    on a job whose transcript-checked approvals another home recorded, and accepted on a job with none."""
    import tempfile as _tq
    import gate as G
    keep = {k: getattr(G, k) for k in ("active_job", "hookless", "quote_in_transcript")}
    with _tq.TemporaryDirectory() as gd:
        class _J:
            gate_dir = gd
            rows: list = []

            def approvals(self):
                return self.rows
        j = _J()
        try:
            G.active_job = lambda *a_, **k_: (j, "")
            G.hookless = lambda: True
            G.quote_in_transcript = lambda q: "no-transcript"
            j.rows = [{"stage": "concept", "verified": "transcript"}]
            why = verify_quote("these words were never checked")
            assert why and "already has approvals checked" in why, ("another home's checked job refuses", why)
            j.rows = [{"stage": "concept", "verified": "UNVERIFIED hookless"}]
            assert verify_quote("these words were never checked") is None, "a hookless-only job still records"
        finally:
            for k, v in keep.items():
                setattr(G, k, v)


def selftest() -> int:
    _selftest_quote_job()
    import tempfile as _tfr
    os.environ.setdefault("CINE_TRANSCRIPT_ROOT", _tfr.gettempdir())   # (3.1) the tests' transcripts live in temp
    ok = True
    home = tempfile.mkdtemp(prefix="world-home-")
    os.environ["CINE_HOME"] = home
    # (3.1) no transcript in this test, so its home is explicitly hookless (an unresolvable transcript refuses otherwise)
    open(os.path.join(home, "config.json"), "w").write('{"hookless": true}')
    if "gate" in sys.modules:
        sys.modules["gate"].TRANSCRIPT_FILE = os.path.join(home, "transcript-path")
        sys.modules["gate"].CINE_HOME = home

    def check(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  → {detail}"))

    check("the linked reference exists", os.path.isfile(os.path.join(SKILL, "references", "world-design.md")))
    import prompt_lint as PL
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d_ in ("00-brief", "01-script/prompts", "02-startframes", "03-clips/_review", "09-qa", "07-edit"):
            os.makedirs(os.path.join(job, d_))
        # the card
        check("init writes a card full of <NEEDS>", cmd_init(job, "BAY", True, "") == 0)
        P, _ = check_card(job, "BAY")
        check("an unfilled card refuses", any("<NEEDS>" in p for p in P), P)
        good = _good_card("BAY")
        jsave(card_path(job, "BAY"), good)
        P, W = check_card(job, "BAY")
        check("a filled card is clean", not P, P)

        def variant(**kw):
            d = json.loads(json.dumps(good))
            for k, v in kw.items():
                if k.startswith("life0_"):
                    d["life"][0][k[6:]] = v
                else:
                    d[k] = v
            jsave(card_path(job, "BAY"), d)
            return check_card(job, "BAY")[0]
        check("a species off the place's list refuses (a real place gets its real life)",
              any("not on this place's list" in p for p in variant(life0_species="brown pelican")), "")
        check("a flying gull at 40 m/s refuses (Pennycuick)", any("air speeds" in p for p in variant(life0_speed_ms=40)))
        check("a mover in the end frame alone refuses (K4)", any("end frame alone" in p for p in variant(life0_in_frames="end")))
        check("both frames with the end against the heading refuses",
              any("disagree with the motion" in p for p in variant(life0_in_frames="both", life0_start_pos="right third",
                                                                     life0_end_pos="left third")))
        d2 = json.loads(json.dumps(good))
        d2["life"].append(dict(good["life"][0], id="L2", species="oystercatcher", count=5))
        jsave(card_path(job, "BAY"), d2)
        check("two cast groups in one shot refuses (at most one, K3)", any("cast groups" in p for p in check_card(job, "BAY")[0]))
        check("glassy water at Beaufort 3 refuses", any("water:" in p for p in variant(water={"kind": "sea", "state": "glassy calm"})))
        check("an invalid cloud genus refuses", any("WMO" in p for p in variant(sky={"genus": ["dramatic"], "cover": "broken",
                                                                                     "drift_toward_deg": 60, "light": "x"})))
        jsave(card_path(job, "BAY"), good)
        c = cues(job, "BAY", "S1")
        check("cues: the wind becomes the land's and the sea's words, the life its count and heading",
              any("twigs in constant motion" in x and "large wavelets" in x for x in c["ENVIRONMENT"])
              and any("3 herring gull crossing" in x for x in c["ENVIRONMENT"]), c)

        # prompts through prompt_lint
        def prompt(name, body, **fm):
            head = {"shot": "S1", "kind": "frame", "model": "nano_banana_pro", "resolution": "2k", "aspect": "9:16"}
            head.update(fm)
            p = os.path.join(job, "01-script", "prompts", name)
            open(p, "w").write("---\n" + "\n".join(f"{k}: {v}" for k, v in head.items()) + "\n---\n" + body)
            return p, PL.lint(p, job)
        FRAME = ("[SUBJECT]\nthe 17th green, flag still in the cup\n\n[ENVIRONMENT]\n{env}\n\n[LIGHTING]\nlow sun from "
                 "camera-right, long shadows across the fairway\n\n[CAMERA]\n35mm, eye level\n\n[STYLE]\nphotographic, natural\n")
        p, r = prompt("S1.frame.prompt.md", FRAME.format(env="links fairway, three herring gulls crossing the upper third, "
                                                         "scattered cumulus"), world="BAY")
        check("a world prompt before the card is approved refuses", any("not approved" in f for f in r["fails"]), r["fails"])
        open(os.path.join(job, "00-brief", "APPROVALS.md"), "w").write(
            "# Approvals\n\n| ts | stage | by | quote | artifact | sha256 | media_id | verified |\n|---|---|---|---|---|---|---|---|\n"
            f"| t | world:BAY | Dana | the bay world is right | 00-brief/world/BAY.world.json | "
            f"{sha256_file(card_path(job, 'BAY'))[:16]} |  | transcript |\n")
        p, r = prompt("S1.frame.prompt.md", FRAME.format(env="links fairway, three herring gulls crossing the upper third, "
                                                         "scattered cumulus"), world="BAY")
        wf = lambda r_: [f for f in r_["fails"] if f.startswith("[world]")]
        check("approved card, cast gulls, the card's sky → no world fails", not wf(r), wf(r))
        p, r = prompt("S1.frame.prompt.md", FRAME.format(env="links fairway, a pelican gliding over the bay"), world="BAY")
        check("an uncast pelican refuses", any("'pelican'" in f and "not cast" in f for f in r["fails"]), r["fails"])
        p, r = prompt("S1.frame.prompt.md", FRAME.format(env="links fairway, overcast grey sky, a fishing boat on the bay"),
                      world="BAY")
        check("an overcast sky against a scattered-cumulus card refuses; an uncast boat too",
              any("overcast" in f and "contradicts" in f for f in r["fails"]) and any("'fishing boat'" in f for f in r["fails"]),
              r["fails"])
        p, r = prompt("S1.frame.prompt.md", FRAME.format(env="links fairway, glassy flat calm bay at night"), world="BAY")
        check("a glassy calm at Beaufort 3 and night with the sun up both refuse",
              any("glassy" in f for f in r["fails"]) and any("'night'" in f for f in r["fails"]), r["fails"])
        # ⚡ v2.45 (2026-10-29): an image edit is `kind: edit` (prompt_lint.py; prompting-craft.md §11g) — the world
        # reads it as the picture it makes, so B6 still refuses a mover it adds
        open(os.path.join(job, "02-startframes", "S1_v1.png"), "wb").write(b"\x89PNG the approved S1")
        EDIT = ("[SOURCE]\nImage 1 is the approved S1 frame: the 17th green at evening, the flag still in the cup.\n\n"
                "[KEEP]\nKeep exactly as in Image 1: the framing and composition, the low sun from camera-right and its long "
                "shadows, the 35 mm look from eye level, the fairway and the sky behind.\n\n"
                "[CHANGE]\nAdd two gulls landing on the green, left of the flag, wings raised, each the size of the cup's "
                "flag, grey and white feathers, their shadows falling left on the turf.\n\n"
                "[LIGHT MATCH]\nThe gulls take the frame's light: low warm sun from the right.\n\n"
                "[OUTPUT]\n9:16, 2k. No text, letters or logos.\n")
        p, r = prompt("S1e.edit.prompt.md", EDIT, kind="edit", world="BAY", shot="S1e", edit_of="02-startframes/S1_v1.png")
        check("an image edit (`kind: edit`) that adds birds refuses, even ones the card casts (B6)",
              any("edit of an approved frame adds a mover" in f for f in r["fails"]), r["fails"])
        p, r = prompt("S1f.edit.prompt.md", EDIT.replace("Add two gulls landing on the green", "Remove the rake from the bunker")
                      .replace("their shadows falling left on the turf", "the sand raked smooth where it lay"),
                      kind="edit", world="BAY", shot="S1f", edit_of="02-startframes/S1_v1.png")
        check("…and an edit that removes a static thing passes the world (edits remove things or correct static ones)",
              not wf(r), wf(r))
        p, r = prompt("S1g.frame.prompt.md", FRAME.format(env="links fairway, scattered cumulus") +
                      "\nadd two gulls landing on the green\n", world="BAY", shot="S1g", edit_of="02-startframes/S1_v1.png")
        check("the old shape — an edit written as `kind: frame` + `edit_of:` — refuses, pointing to `kind: edit`",
              any("`kind: frame` with `edit_of:`" in f for f in r["fails"]), r["fails"])
        p, r = prompt("S2.frame.prompt.md", FRAME.format(env="a seaside street, scattered cumulus"), shot="S2")
        check("an exterior with no world card: a ⚑ warning that refuses until answered",
              any("unanswered" in f and "no `world:` card" in f for f in r["fails"]), r["fails"])
        check("accept answers it, bound to the prompt's text",
              cmd_accept(job, p, "a one-off street establishing shot, no life in frame, checked") == 0
              and not [f for f in PL.lint(p, job)["fails"] if f.startswith("[world]")])
        p2, r = prompt("S2.frame.prompt.md", FRAME.format(env="a seaside street at noon, scattered cumulus"), shot="S2")
        check("…and a changed prompt needs a new answer", any("unanswered" in f for f in r["fails"]), r["fails"])
        p, r = prompt("S3.frame.prompt.md", FRAME.format(env="studio cyc, seamless white"), shot="S3", world="none")
        check("`world: none` without a reason refuses", any("needs its reason" in f for f in r["fails"]), r["fails"])
        # the card changes → every prompt of it is stale (a change of direction, K7)
        g2 = json.loads(json.dumps(good)); g2["wind"]["beaufort"] = 5
        jsave(card_path(job, "BAY"), g2)
        p, r = prompt("S1.frame.prompt.md", FRAME.format(env="links fairway, three herring gulls crossing the upper third, "
                                                         "scattered cumulus"), world="BAY")
        check("a changed card stales its prompts until the owner approves it again",
              any("changed after it was approved" in f for f in r["fails"]), r["fails"])
        jsave(card_path(job, "BAY"), good)
        # a stop blocks everything
        cmd_stop(job, "the pelicans in S4 do not live on this coast")
        p, r = prompt("S1.frame.prompt.md", FRAME.format(env="links fairway, scattered cumulus"), world="BAY")
        check("an open stop refuses every prompt (a noticed problem is a stop, not a note)",
              any("stop 1 is open" in f for f in r["fails"]), r["fails"])
        check("a stop closes on a fix", cmd_close(job, 1, "the pelicans are cut from the card", False, "") == 0)
        p, r = prompt("S1.frame.prompt.md", FRAME.format(env="links fairway, scattered cumulus"), world="BAY")
        check("…and the prompt lints again", not wf(r), wf(r))
        # the plausibility override, in the owner's words
        bad = json.loads(json.dumps(good)); bad["life"][0]["species"] = "brown pelican"
        jsave(card_path(job, "BAY"), bad)
        _cfg = os.path.join(home, "config.json"); os.remove(_cfg)              # (3.1) a hooked home, no transcript
        check("on a hooked home with no transcript a quote is refused (never assumed)",
              bool(verify_quote("yes keep the wind as it is")))
        open(_cfg, "w").write('{"hookless": true}')
        check("an override is the owner's words, recorded on the life entry",
              cmd_override(job, "BAY", "L1", "keep the pelican, it is the client's mascot") == 0
              and not any("not on this place's list" in x for x in check_card(job, "BAY")[0]))
        jsave(card_path(job, "BAY"), good)
        # the clip read (B12)
        clip = os.path.join(job, "03-clips", "_review", "S1_v1.mp4")
        open(clip, "wb").write(b"\x00\x00\x00\x18ftypmp42 a take")
        prompt("S1.clip.prompt.md", "[MOTION]\nSTART: the flag stirs\nMID: the gulls cross\nEND: the flag settles\n\n"
               "[CAMERA]\nlocked-off\n", kind="clip", world="BAY", duration="5", model="kling3_0")
        check("approve clips: an exterior clip with no read refuses", any("not read against" in x for x in check_reads(job)))
        rc = cmd_read(job, "S1", clip, 7, "seven gulls swirl in from the right and the sky stays scattered cumulus", "a boat")
        check("a read with the wrong count and a new boat is a RETAKE", rc == 1 and any("RETAKE" in x for x in check_reads(job)))
        rc = cmd_read(job, "S1", clip, 3, "three gulls cross left to right in the upper third, flags agree with the wind",
                      "none")
        check("a read that matches the card passes", rc == 0 and not check_reads(job), check_reads(job))
        open(clip, "ab").write(b"retake")
        check("a read about other bytes is stale", any("changed or is gone" in x for x in check_reads(job)))
        # Resolve
        json.dump({"fps": 24, "tracks": {"video1": [{"name": "S1_v1.mp4", "type": "Video", "start": 0, "duration": 120}]}},
                  open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
        src = open(console_copy(job), encoding="utf-8").read()
        check("console copy: a marker per exterior clip carrying its world",
              "World BAY · S1" in src and "ENSURE_AUDIO_LANES = False" in src)
    print("-" * 60)
    print("selftest OK — the card's rules (sun, wind, sky, depth, life, plausibility, frames, the cap); the prompt "
          "lint (approval, uncast movers, contradictions, edits, the exterior with no card, answers, stops, a "
          "changed card); the clip read; Resolve markers" if ok else "selftest FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
