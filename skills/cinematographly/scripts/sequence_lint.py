#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""sequence_lint.py — check the SEQUENCE CHAIN of a shotlist: what each shot inherits from the last.

Every generation is stateless: a clip re-lights, re-frames and re-casts itself unless its prompt
restates what it inherits. The chain is written once, as the "## Sequence chain" table in
01-script/SHOTLIST-<slug>.md (assets/shotlist-template.md), and this reads it in cut order.

  python3 sequence_lint.py 01-script/SHOTLIST-<slug>.md          # FAIL exits 1, WARN prints
  python3 sequence_lint.py 01-script/SHOTLIST-<slug>.md --strict # WARN exits 1 too
  python3 sequence_lint.py --selftest

WHAT IT CHECKS (references/sequence-grammar.md; the measured side is specifics-catalogue.md §15):
  FAIL  a cell still owed (<NEEDS DIRECTION>), or a value outside the column's vocabulary — a typo
        in a closed list would silently skip every rule below
  FAIL  the key SIDE changes inside a scene (left/right/front/back) — the relight (§6.1)
  FAIL  a to-camera shot from BELOW (tilted up, or hip/knee/ground height) — the trust cost (§3.3)
  WARN  a to-camera shot from above or tilted — the drop there was not significant (one study)
  WARN  the colour family changes inside a scene — the confetti palette (§6.4)
  WARN  under / top / silhouette more than once in a scene — a single beat, not a look (§6.3)
  WARN  intensity jumps 2+ between performer shots and the frame does not move with it (§4.2)
  WARN  a performer shot tilted up or down, not a POV/insert/montage, with no opposite tilt in
        its scene — the unpaired angle (§3.3)
  WARN  a reaction with no stimulus, exchange or insert before it in its scene, and no stimulus or
        insert straight after it — the withheld cause revealed next is the one exception (§4.1)
  WARN  a shot carrying a turn that runs shorter than its scene's median (§4.3)
  WARN  more than one full release (intensity 3) in the piece (§4.4)
  WARN  a performer (intensity 1–3, not to camera) with no target — the drift
  FAIL  no `Contrast:` line under the chain — the piece has no plan for where its pictures peak (§2b)
  WARN  the frozen camera (under 1 shot in 5 moves) or nothing holds (over 4 in 5) — the camera plan (§2b)
  WARN  nine or more held shots in a row with no Break marked (past the 75th percentile of 38 award-
        winning ads, whose longest held run has a median of 5); every move a push-in
  CARD  --baseline: the piece's eight numbers against the bands of 38 measured ads, with what to revise —
        the second pass of the revise loop, after the director's review (sequence-grammar.md §2c item 14;
        measured in lab-00008: review then card beat either alone; at most three rounds)
  CARD  --regime dr: the same card and baseline WARNs against 13 measured direct-response ads instead
        (lab-00009, one agency's portfolio and brief examples — provisional). The award bands mark 11 of
        those 13 ads OUT on wide and 8 on 2+ size jumps, so they would push a DR script toward framing
        DR ads do not use (sequence-grammar.md §2c item 14)
  WARN  the ad baseline (§2c, measured on 38 real ads): mean shot over 3.6 s (slower than 9 ads in 10),
        fewer than 15 % wide shots (real ads: a third), under 40 % at eye or shoulder height (real ads:
        three in four). Under --regime dr: mean shot over 2.6 s, under 55 % at eye or shoulder height,
        and no wide-share warning (the DR ads' p10 is 0 % wide)
  WARN  an affinity run: four or more shots in a row at the same height, the same camera behaviour and
        sizes within one step of each other
  WARN  no deliberate Break anywhere — the piece is the §8 baseline, by the book
  WARN  a contrast plan the rows do not deliver (movement, rhythm and size are measured; the rest are
        named as checkable only on the boards)
  INFO  each scene's size arc, and a peak (3) framed wider than MS

WHAT IT CANNOT DO: it reads the PLAN, not the clips. It cannot see whether the model obeyed the
row, whether the look in shot A really points at the target in shot B, or whether a WARN is a
deliberate choice. A WARN is a question for the director, not a defect.
"""
from __future__ import annotations
import argparse, json, os, re, statistics, sys, tempfile

# The ad baseline, measured on 38 real ads (Cannes / D&AD winners and strong spots; lab-00006, 2026-10-04,
# specifics-catalogue.md §16): thresholds sit at the edge of what nine in ten (or three in four) real ads do.
HELD_RUN_WARN = 9      # longest run of locked shots per ad: p25 2, median 5, p75 8, p90 11
ASL_WARN = 3.6         # mean shot per ad: p10 1.45 s, median 1.84 s, p90 3.58 s
WIDE_MIN = 0.15        # share of WS/EWS per ad: p10 16 %, median 32 %
EYE_MIN = 0.40         # share at eye level per ad: p10 44 %, median 77 %
# The DR regime (lab-00009, 2026-10-21): 13 direct-response ads from ONE agency, 10 portfolio ads plus 3
# brief examples, read with the lab-00006 pipeline. Provisional: one house style, n = 13.
DR_ASL_WARN = 2.6      # mean shot per ad: p10 1.27 s, median 1.8 s, p90 2.59 s
DR_EYE_MIN = 0.55      # share at eye level per ad: p10 55 %, median 71 % (wide p10 is 0 %: no wide warn)
REGIMES = ("award", "dr")
SIZES = ["EWS", "WS", "MWS", "MS", "MCU", "CU", "XCU"]            # the ladder, wide → tight
SIZE_SET = set(SIZES) | {"INSERT"}
BEATS = {"orient", "reorient", "exchange", "stimulus", "reaction", "dilemma", "decision", "release",
         "montage", "climax", "resolution", "insert"}
HEIGHTS = {"ground", "knee", "hip", "shoulder", "eye", "above", "overhead", "aerial"}
KEYS_DIR = {"left", "right", "front", "back"}
KEYS_HIDE = {"top", "under", "silhouette"}
KEYS_NEUTRAL = {"flat", "none"}
TILT_RE = re.compile(r"^(level|top-down|dutch(?:\s+\d+)?|(up|down)\s+\d+)$")
TURN_RE = re.compile(r"^(-|(early|late|through):.+)$")
COLS = ["shot", "scene", "beat", "size", "height", "tilt", "move", "key", "colour", "int", "turn",
        "target", "dur", "to camera", "break"]
# ⛔ THE CAMERA AND THE CONTRAST PLAN (2026-10-04, lab-00005). A chain with no camera column let every
# shot default to a held frame — 97 % locked across 20 skill-written ads — and a chain of pure
# continuity rules is affinity everywhere: the judges' sequence-variety score did not move with the
# skill. Move and Break are columns now, and the plan is a line the lint reads.
MOVES = {"locked", "push", "pull", "pan", "tilt", "track", "crane", "orbit", "handheld", "whip", "rack",
         "drift", "roll", "zoom"}
MOVE_ALIAS = {"static": "locked", "hold": "locked", "held": "locked", "still": "locked", "lock": "locked",
              "dolly-in": "push", "dolly": "push", "dolly-out": "pull", "pull-out": "pull",
              "push-in": "push", "steadicam": "track", "follow": "track", "boom": "crane", "rise": "crane"}
CONTRAST_KINDS = {"movement", "rhythm", "size", "space", "tone", "colour", "color", "line", "shape"}
STILL_W = re.compile(r"\b(still|static|held|hold|locked|calm|slow)\b", re.I)
MOVING_W = re.compile(r"\b(kinetic|moving|mobile|travel\w*|fast|handheld|restless|motion)\b", re.I)
LONG_W = re.compile(r"\b(long|slow|lingering)\b", re.I)
SHORT_W = re.compile(r"\b(short|fast|quick|rapid)\b", re.I)
WIDE_W = re.compile(r"\b(wide|ews|ws|far|open)\b", re.I)
TIGHT_W = re.compile(r"\b(tight|close|cu|xcu|mcu|detail)\b", re.I)
ALIASES = {"int.": "int", "intensity": "int", "color": "colour", "to cam": "to camera",
           "to-camera": "to camera", "duration": "dur", "dur (s)": "dur", "camera": "move",
           "camera move": "move"}
OWED_RE = re.compile(r"NEEDS|<[^>]*>")


def parse(md: str) -> tuple[list, list]:
    """Rows of the first table under '## Sequence chain', as dicts keyed by COLS. Returns
    (rows, errors); an error means the table itself is unreadable."""
    m = re.search(r"^##\s+Sequence chain.*$", md, re.M)
    if not m:
        return [], ["no '## Sequence chain' section — write the chain before any prompt "
                    "(assets/shotlist-template.md)"]
    body = md[m.end():]
    nxt = re.search(r"^##\s", body, re.M)
    body = body[:nxt.start()] if nxt else body
    lines = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return [], ["the Sequence chain section has no table"]
    head = [ALIASES.get(c.strip().lower(), c.strip().lower()) for c in lines[0].strip("|").split("|")]
    missing = [c for c in COLS if c not in head]
    if missing:
        return [], [f"the chain table is missing column(s): {', '.join(missing)}"]
    rows = []
    for ln in lines[1:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue                                   # the |---|---| rule
        if len(cells) != len(head):
            return [], [f"row {cells[0]!r} has {len(cells)} cells, the header has {len(head)} — "
                        f"a shifted column would put every value under the wrong rule"]
        rows.append(dict(zip(head, cells)))
    return rows, []


def parse_contrast(md: str):
    """The `Contrast:` line inside the Sequence chain section, or None when there is none."""
    m = re.search(r"^##\s+Sequence chain.*$", md, re.M)
    if not m:
        return None
    body = md[m.end():]
    nxt = re.search(r"^##\s", body, re.M)
    body = body[:nxt.start()] if nxt else body
    c = re.search(r"^\s*>?\s*\**Contrast:?\**\s*:?\s*(.+)$", body, re.M)
    return c.group(1).strip() if c else None


def _move(cell: str) -> str:
    w = re.split(r"[\s,(+/;]", cell.strip().lower(), maxsplit=1)[0]
    return MOVE_ALIAS.get(w, w)


HERE = os.path.dirname(os.path.abspath(__file__))
SHORT_VERTICAL_S = 45.0     # 9:16 and this long or shorter: the 38 award ads are not its baseline (v2.69.0)
SHORT_NOTE = ("note, not a target (9:16, {total:.0f} s): the 38 measured ads are 35 landscape and only 9 run 45 s "
              "or less (specifics-catalogue.md §16.1, §16.9), so this baseline does not describe a short vertical film — ")


def job_aspect(path: str, job: str | None = None) -> str | None:
    """The aspect of the delivery preset the job's CHECKPOINT `Format:` names, found from the shotlist's own folders
    (or --job). None when there is no CHECKPOINT, no Format line or no such preset."""
    d = os.path.abspath(job) if job else os.path.dirname(os.path.abspath(path))
    for _ in range(6 if not job else 1):
        cp = os.path.join(d, "00-brief", "CHECKPOINT.md")
        if os.path.isfile(cp):
            m = re.search(r"^Format:\s*`?([\w.-]+)", open(cp, encoding="utf-8").read(), re.M)
            if not m:
                return None
            fm = json.load(open(os.path.join(os.path.dirname(HERE), "assets", "delivery-formats.json"),
                                encoding="utf-8")).get("formats", {})
            if m.group(1) not in fm:
                print(f"WARN  CHECKPOINT `Format: {m.group(1)}` is not a preset in delivery-formats.json — the aspect is "
                      f"unknown, so the ad baseline is not adjusted for a short vertical film")
            return (fm.get(m.group(1)) or {}).get("aspect")
        d = os.path.dirname(d)
    return None


def lint(rows: list, contrast=None, regime: str = "award", aspect: str | None = None) -> dict:
    """`aspect` is the delivery preset's: a 9:16 chain of 45 s or less gets the award-ad baseline as notes."""
    F, W, I = [], [], []
    owed = 0
    for r in rows:
        tag = f"{r['shot']}"
        cols = COLS + (["energy"] if "energy" in r else [])
        for c in cols:
            if OWED_RE.search(r[c]):
                owed += 1
        if any(OWED_RE.search(r[c]) for c in cols):
            continue
        r["_beat"] = r["beat"].lower()
        r["_size"] = r["size"].upper()
        r["_height"] = r["height"].lower()
        r["_tilt"] = r["tilt"].lower()
        r["_key"] = r["key"].lower().replace("camera-", "").replace("camera ", "")
        r["_colour"] = r["colour"].lower()
        r["_cam"] = r["to camera"].lower()
        if r["_beat"] not in BEATS:
            F.append(f"{tag}: Beat {r['beat']!r} is not one of {sorted(BEATS)}")
        if r["_size"] not in SIZE_SET:
            F.append(f"{tag}: Size {r['size']!r} is not one of {SIZES + ['INSERT']}")
        if r["_height"] not in HEIGHTS:
            F.append(f"{tag}: Height {r['height']!r} is not one of {sorted(HEIGHTS)} — height and "
                     f"tilt are two settings (sequence-grammar.md §3.4)")
        if not TILT_RE.match(r["_tilt"]):
            F.append(f"{tag}: Tilt {r['tilt']!r} must be level · up <deg> · down <deg> · top-down · dutch")
        if r["_key"] not in KEYS_DIR | KEYS_HIDE | KEYS_NEUTRAL:
            F.append(f"{tag}: Key {r['key']!r} is not one of "
                     f"{sorted(KEYS_DIR | KEYS_HIDE | KEYS_NEUTRAL)}")
        if not r["_colour"] or r["_colour"] == "-":
            F.append(f"{tag}: Colour is empty — name the family (warm, cool, neutral, …)")
        if r["int"] not in ("0", "1", "2", "3", "-"):
            F.append(f"{tag}: Int. {r['int']!r} must be 0–3, or - when no performer is in frame")
        if not TURN_RE.match(r["turn"]):
            F.append(f"{tag}: Turn {r['turn']!r} must be - or early:/late:/through: <what changes>")
        try:
            r["_dur"] = float(r["dur"].rstrip("s "))
            if r["_dur"] <= 0:
                raise ValueError
        except ValueError:
            F.append(f"{tag}: Dur {r['dur']!r} is not a positive number of seconds"); r["_dur"] = None
        if r["_cam"] not in ("yes", "no"):
            F.append(f"{tag}: To camera {r['to camera']!r} must be yes or no")
        r["_move"] = _move(r["move"])
        if r["_move"] not in MOVES:
            F.append(f"{tag}: Move {r['move']!r} is not one of {sorted(MOVES)} — say what the camera "
                     f"does: `locked`, or a move with a job (sequence-grammar.md §2b)")
        r["_break"] = r["break"].strip() not in ("", "-", "—")
        if "energy" in r:
            try:
                r["_energy"] = int(r["energy"].strip())
                if not 1 <= r["_energy"] <= 5:
                    raise ValueError
            except ValueError:
                F.append(f"{tag}: Energy {r['energy']!r} must be 1–5"); r["_energy"] = None
    if owed:
        F.insert(0, f"{owed} cell(s) still owed — the chain cannot be checked until it is decided")
    ready = [r for r in rows if "_beat" in r]
    tot_ = sum(r.get("_dur") or 0 for r in rows)
    sv_ = aspect == "9:16" and 0 < tot_ <= SHORT_VERTICAL_S and not owed
    if F:       # the short-vertical flag is set before this return, so the card stays a note (build review 1, Grok)
        return {"fails": F, "warns": W, "info": I, "rows": len(rows), "short_vertical": sv_, "total_s": round(tot_, 2)}

    scenes: dict = {}
    for r in ready:
        scenes.setdefault(r["scene"], []).append(r)

    for sc, R in scenes.items():
        dirs = [(r["shot"], r["_key"]) for r in R if r["_key"] in KEYS_DIR]
        if len({k for _, k in dirs}) > 1:
            F.append(f"scene {sc}: the key side changes inside the scene ("
                     + ", ".join(f"{s} {k}" for s, k in dirs) + ") — the relight: one key side per "
                     f"scene, changed at a story boundary (sequence-grammar.md §6.1)")
        hides = [r["shot"] for r in R if r["_key"] in KEYS_HIDE]
        if len(hides) > 1:
            W.append(f"scene {sc}: under/top/silhouette on {len(hides)} shots ({', '.join(hides)}) — "
                     f"once, on the reveal: under-light and silhouette hide the identity the model is "
                     f"already struggling to hold, and all three raise the reaction (§6.3)")
        cols = []
        for r in R:
            if not cols or cols[-1] != r["_colour"]:
                cols.append(r["_colour"])
        if len(set(cols)) > 1:
            W.append(f"scene {sc}: the colour family changes inside the scene ({' → '.join(cols)}) — "
                     f"the confetti palette: one family per scene, changed at a story boundary (§6.4)")
        # the partner has to be a PERFORMER too: an insert looked down on is a point of view, not
        # the other half of a power pair (specifics-catalogue.md §12.1 — high is an insert)
        people = [r for r in R if r["int"] != "-" and r["_beat"] not in ("insert", "stimulus", "montage")]
        tilts = {r["_tilt"].split()[0] for r in people}
        for r in people:
            t = r["_tilt"].split()[0]
            if t in ("up", "down"):
                other = "down" if t == "up" else "up"
                if other not in tilts:
                    W.append(f"{r['shot']}: a performer tilted {t} with no {other}-tilted partner in "
                             f"scene {sc} — the unpaired angle reads as a camera position, not a "
                             f"meaning; give it a job (POV, geography) or its partner (§3.3; "
                             f"specifics-catalogue.md §15.4)")
        for i, r in enumerate(R):
            revealed_next = i + 1 < len(R) and R[i + 1]["_beat"] in ("stimulus", "insert")
            if r["_beat"] == "reaction" and not revealed_next and not any(
                    x["_beat"] in ("stimulus", "exchange", "insert") for x in R[:i]):
                W.append(f"{r['shot']}: a reaction with no stimulus, exchange or insert before it in "
                         f"scene {sc}, and no reveal straight after — the orphan reaction: the "
                         f"stimulus comes first, or the withheld cause is the very next shot (§4.1)")
        durs = [r["_dur"] for r in R if r["_dur"]]
        if len(durs) >= 3:
            med = statistics.median(durs)
            for r in R:
                if r["turn"] != "-" and r["_dur"] and r["_dur"] < med:
                    W.append(f"{r['shot']}: carries a turn ({r['turn']}) in {r['_dur']:g}s, shorter "
                             f"than the scene's median {med:g}s — a change needs time; the turn shot "
                             f"is the one held longer (§4.3)")
        arc = " → ".join(r["_size"] for r in R)
        I.append(f"scene {sc}: {arc}")

    for r in ready:
        if r["_cam"] == "yes":
            below = r["_tilt"].startswith("up") or r["_height"] in ("hip", "knee", "ground")
            off = r["_tilt"] != "level" or r["_height"] not in ("eye", "shoulder")
            if below:
                F.append(f"{r['shot']}: talks to camera from below ({r['height']} height, tilt "
                         f"{r['tilt']}) — a face addressing the viewer from below was trusted less "
                         f"(4.27 against 5.03 at eye level); keep direct address at eye height, level "
                         f"(sequence-grammar.md §3.3)")
            elif off:
                W.append(f"{r['shot']}: talks to camera at {r['height']} height, tilt {r['tilt']} — "
                         f"from above the trust drop was not significant (4.57, one study), but eye "
                         f"level was trusted most; make sure the angle is the point (§3.3)")
        if r["int"] in ("1", "2", "3") and r["target"].strip() in ("-", "") and r["_cam"] == "no":
            W.append(f"{r['shot']}: a performer at intensity {r['int']} with no target — the drift: "
                     f"name who or what the performance is aimed at (acting-for-the-model.md §7)")
        if r["int"] == "3" and r["_size"] in ("MWS", "WS", "EWS"):
            I.append(f"{r['shot']}: a peak at {r['_size']} — it has to be a body action with contact; "
                     f"no peak in the reference films is face-only wider than MCU "
                     f"(specifics-catalogue.md §13.5a)")

    perf = [r for r in ready if r["int"] != "-"]
    for a, b in zip(perf, perf[1:]):
        d = int(b["int"]) - int(a["int"])
        if abs(d) < 2:
            continue
        if a["_size"] in SIZES and b["_size"] in SIZES:
            ds = SIZES.index(b["_size"]) - SIZES.index(a["_size"])
            if ds * d > 0:
                continue
        W.append(f"{a['shot']}→{b['shot']}: intensity {a['int']}→{b['int']} and the frame "
                 f"{a['_size']}→{b['_size']} does not move with it — the jump: climb one step at a "
                 f"time, or cut {'tighter' if d > 0 else 'wider'} on it (§4.2; "
                 f"specifics-catalogue.md §15.2)")
    peaks = [r["shot"] for r in ready if r["int"] == "3"]
    if len(peaks) > 1:
        W.append(f"{len(peaks)} full releases ({', '.join(peaks)}) — release once, tight and quiet; "
                 f"1.9 % of the reference performances are a 3 (§4.4)")

    # ── the camera plan (§2b) ──────────────────────────────────────────────────────────────────
    n = len(ready)
    moving = [r for r in ready if r["_move"] != "locked"]
    if n >= 5:
        share = len(moving) / n
        if share < 0.2:
            W.append(f"the frozen camera: {len(moving)} of {n} shots move — give the moves jobs "
                     f"(reveal, follow, connect, change scale, carry a cut); about four in ten moved "
                     f"in the reference films (sequence-grammar.md §2b; specifics-catalogue.md §10.3)")
        elif share > 0.8:
            W.append(f"nothing holds: {len(moving)} of {n} shots move — a held frame is what makes a "
                     f"move read; let the world move through some of them (cinematography-craft.md §3.8)")
    run_ = []
    for r in ready + [None]:
        if r is not None and r["_move"] == "locked" and not r["_break"]:
            run_.append(r["shot"]); continue
        if len(run_) >= HELD_RUN_WARN:
            W.append(f"{len(run_)} held shots in a row ({run_[0]}…{run_[-1]}) — longer than three in four "
                     f"award-winning ads ever hold (their longest run: median 5, p75 8); if the hold is the "
                     f"device, say so in Break; otherwise one of them wants a move with a job (§2b, §2c)")
        run_ = []
    pushes = [r for r in moving if r["_move"] == "push"]
    if len(moving) >= 3 and len(pushes) / len(moving) >= 0.8:
        W.append(f"every move is a push-in ({len(pushes)} of {len(moving)}) — the prompt pipeline's "
                 f"default, not a plan; pans and tilts outnumbered pushes three to one in the reference "
                 f"films (cinematography-craft.md §3.8)")
    # ── ENERGY (house decision 2026-10-26, package C of the intent-emotion proposal) ─────────────
    # The three-model jury put an energy plan across the sequence in its top eight: fast, fast, hold.
    # A chain without the column is told once (info); a chain with it is held to a shape.
    en = [r.get("_energy") for r in ready if r.get("_energy")]
    if ready and "energy" not in ready[0]:
        I.append("no Energy column — plan each shot's energy 1–5 across the sequence, like music: fast, "
                 "fast, hold (sequence-grammar.md §2d)")
    elif len(en) >= 4 and len(set(en)) == 1:
        W.append(f"the energy is flat: every shot at {en[0]} — a sequence with no change has no shape. Plan "
                 f"where it rises and where it holds (sequence-grammar.md §2d)")
    if regime == "dr" and en:
        run = best = 0
        for v in en:
            run = run + 1 if v >= 3 else 0
            best = max(best, run)
        if best > 6:
            W.append(f"{best} shots in a row at energy 3 or more, no still beat — a burst lands against a hold; "
                     f"put one shot at 1–2 every four to six (sequence-grammar.md §2d; the 2026-10-26 jury)")
    # ── the ad baseline (§2c): 38 real ads, lab-00006, 2026-10-04 — or 13 DR ads, lab-00009 ──────────
    if n >= 6 and regime == "dr":
        durs = [r["_dur"] for r in ready if r.get("_dur")]
        if len(durs) >= 6 and sum(durs) / len(durs) > DR_ASL_WARN:
            W.append(f"slow for a DR ad: the mean shot is {sum(durs) / len(durs):.1f} s — 9 in 10 of 13 measured "
                     f"DR ads cut faster (median 1.8 s, p90 2.6 s); one insert per line, 1–2 s, unless the "
                     f"shot is the talking-head spine (sequence-grammar.md §2c item 14; lab-00009)")
        eyeish = sum(1 for r in ready if r["_height"] in ("eye", "shoulder"))
        if eyeish / n < DR_EYE_MIN:
            W.append(f"height spread too wide for DR: {eyeish} of {n} shots at eye or shoulder height — the "
                     f"measured DR ads stay there seven shots in ten (p10 55 %) (§2c; lab-00009)")
    elif n >= 6:
        durs = [r["_dur"] for r in ready if r.get("_dur")]
        total = sum(durs)
        short = aspect == "9:16" and 0 < total <= SHORT_VERTICAL_S
        W0 = len(W)
        if len(durs) >= 6 and sum(durs) / len(durs) > ASL_WARN:
            W.append(f"slow for an ad: the mean shot is {sum(durs) / len(durs):.1f} s — 9 in 10 of 38 measured "
                     f"ads cut faster (median 1.8 s, p90 3.6 s); right for a dialogue scene or deadpan "
                     f"comedy, otherwise cut shorter and enter later (sequence-grammar.md §2c)")
        wide = sum(1 for r in ready if r["_size"] in ("EWS", "WS"))
        if wide / n < WIDE_MIN:
            W.append(f"no world: {wide} of {n} shots are wide (WS/EWS) — real ads hold about a third wide "
                     f"(median 32 %; 9 in 10 ads at least 16 %); show the place the action happens in (§2c)")
        eyeish = sum(1 for r in ready if r["_height"] in ("eye", "shoulder"))
        if eyeish / n < EYE_MIN:
            W.append(f"height spread too wide: {eyeish} of {n} shots at eye or shoulder height — real ads stay "
                     f"there three shots in four (p10 44 %); keep off-eye heights for the shots that need "
                     f"them (§2c; §3.3)")
        if short:                                    # Wave 4 (2026-11-14; both reviewers): notes, not targets
            I += [SHORT_NOTE.format(total=total) + w_ for w_ in W[W0:]]
            del W[W0:]
    # ── affinity runs: four in a row at one height, one camera behaviour, sizes within a step ──
    i = 0
    while i < n:
        j = i
        while (j + 1 < n and ready[j + 1]["_height"] == ready[i]["_height"]
               and ready[j + 1]["_move"] == ready[i]["_move"]
               and ready[j]["_size"] in SIZES and ready[j + 1]["_size"] in SIZES
               and abs(SIZES.index(ready[j + 1]["_size"]) - SIZES.index(ready[j]["_size"])) <= 1):
            j += 1
        if j - i + 1 >= 4 and not any(r["_break"] for r in ready[i:j + 1]):
            W.append(f"an affinity run: {ready[i]['shot']}…{ready[j]['shot']} ({j - i + 1} shots) at one "
                     f"height, one camera behaviour and sizes within a step — affinity lowers intensity; "
                     f"break one of them on purpose (§2b)")
        i = j + 1
    if n >= 5 and not any(r["_break"] for r in ready):
        W.append("by the book: no shot breaks the baseline on purpose — mark at least one deliberate "
                 "Break where the piece most needs intensity (sequence-grammar.md §2b)")
    # ── the contrast plan ────────────────────────────────────────────────────────────────────────
    if not contrast:
        F.append("no `Contrast:` line under the chain — write one or two components as `a → b`, e.g. "
                 "`Contrast: movement: still → kinetic; rhythm: long → short` (sequence-grammar.md §2b)")
    elif OWED_RE.search(contrast):
        F.append("the Contrast line is still owed")
    elif n >= 6:
        k = max(1, n // 3)
        first, last = ready[:k], ready[-k:]
        for part in [x.strip() for x in contrast.split(";") if x.strip()]:
            if ":" not in part:
                F.append(f"Contrast part {part!r} needs a component and a direction: `size: wide → tight`")
                continue
            kind, prog = [x.strip() for x in part.split(":", 1)]
            kind = kind.lower()
            if kind not in CONTRAST_KINDS:
                F.append(f"Contrast component {kind!r} is not one of {sorted(CONTRAST_KINDS - {'color'})}")
                continue
            ab = re.split(r"→|->", prog)
            if len(ab) < 2:
                F.append(f"Contrast {kind!r} needs a direction written `a → b`")
                continue
            a_, b_ = ab[0], ab[-1]
            if kind == "movement":
                fm = sum(r["_move"] != "locked" for r in first) / k
                lm = sum(r["_move"] != "locked" for r in last) / k
                up = STILL_W.search(a_) and MOVING_W.search(b_)
                down = MOVING_W.search(a_) and STILL_W.search(b_)
                if (up and lm <= fm) or (down and lm >= fm):
                    W.append(f"the contrast plan says movement {prog.strip()} but the last third moves "
                             f"{lm:.0%} of the time against {fm:.0%} in the first — the rows do not deliver it")
                elif not (up or down):
                    I.append(f"Contrast movement {prog.strip()!r}: direction not read; check it on the boards")
            elif kind == "rhythm":
                fd = statistics.mean(r["_dur"] for r in first if r["_dur"])
                ld = statistics.mean(r["_dur"] for r in last if r["_dur"])
                faster = LONG_W.search(a_) and SHORT_W.search(b_)
                slower = SHORT_W.search(a_) and LONG_W.search(b_)
                if (faster and ld >= fd) or (slower and ld <= fd):
                    W.append(f"the contrast plan says rhythm {prog.strip()} but the last third averages "
                             f"{ld:.1f} s against {fd:.1f} s in the first — the rows do not deliver it")
                elif not (faster or slower):
                    I.append(f"Contrast rhythm {prog.strip()!r}: direction not read; check it on the boards")
            elif kind == "size":
                fs = [SIZES.index(r["_size"]) for r in first if r["_size"] in SIZES]
                ls = [SIZES.index(r["_size"]) for r in last if r["_size"] in SIZES]
                if fs and ls:
                    tighter = WIDE_W.search(a_) and TIGHT_W.search(b_)
                    wider = TIGHT_W.search(a_) and WIDE_W.search(b_)
                    fm_, lm_ = statistics.mean(fs), statistics.mean(ls)
                    if (tighter and lm_ <= fm_) or (wider and lm_ >= fm_):
                        W.append(f"the contrast plan says size {prog.strip()} but the last third is not "
                                 f"{'tighter' if tighter else 'wider'} than the first — the rows do not deliver it")
            else:
                I.append(f"Contrast {kind} {prog.strip()!r}: not measurable from the table — check it on "
                         f"the boards and the contact sheet")
    return {"fails": F, "warns": W, "info": I, "rows": len(rows), "short_vertical": sv_, "total_s": round(tot_, 2)}


# ── the baseline card (sequence-grammar.md §2c, item 14) ─────────────────────────────────────────
# Per-ad bands from 38 measured ads (lab-00006): (p10, p25, p75, p90); FIX = (if below p10, if above p90). Inside p25–p75 = the middle half of
# real ads; inside p10–p90 = what 8 ads in 10 do; outside = revise, or keep it on purpose and say why in Break.
BANDS = {
    "mean shot (s)":        (1.5, 1.5, 2.6, 3.6),
    "shots that move %":    (17, 30, 71, 88),
    "wide (WS/EWS) %":      (16, 19, 45, 50),
    "close (MCU/CU/XCU) %": (15, 18, 34, 44),
    "eye/shoulder height %": (44, 70, 87, 93),
    "same-size cuts %":     (9, 17, 28, 45),
    "cuts jumping 2+ sizes %": (32, 37, 58, 63),
    "longest held run":     (1, 2, 8, 11),
}
FIX = {
    "mean shot (s)": ("merge fragments that change nothing; a shot under a second needs a job",
                      "cut the holds that carry no turn, line or reveal; Dur is time on screen in the cut, not the "
                      "generated clip (generate the model's length and cut the part after the ramp)"),
    "shots that move %": ("give a move with a job to the shots that follow, reveal or connect (§2b)",
                          "let some shots hold so the moves read — the world can move inside a locked frame"),
    "wide (WS/EWS) %": ("show the place the action happens in — open or re-orient wide",
                        "go closer where the face or the object carries the beat"),
    "close (MCU/CU/XCU) %": ("give the turn or the product a close shot",
                             "pull back: the measured ads live wider (the DR ads in mediums and inserts)"),
    "eye/shoulder height %": ("bring heights back to eye level; keep off-eye heights for the shots that need them. "
                              "A film shot at a child's or an animal's eye line reads low here by construction (the "
                              "ads were coded against the subject's eyes); never relabel the height to pass",
                              "one off-eye height where the story needs it"),
    "same-size cuts %": ("cut between two setups of the same size — returns, shot/reverse, inserts in a row",
                         "change the size at more cuts"),
    "cuts jumping 2+ sizes %": ("make some jumps decisive: wide to close, close to wide",
                                "step some cuts by one size, or keep the size — not every cut has to jump"),
    "longest held run": ("let one shot hold — a held frame is what makes the moves read",
                         "move one shot in the run with a job, or mark the run in Break"),
}


# The DR bands (lab-00009, 2026-10-21): the same eight measures over 13 direct-response ads — 10 from one
# agency's portfolio and 3 of its brief examples — with lab-00006's quantile rule. ⚠ Provisional: one house
# style, n = 13, so a band edge here is one or two ads. Rebuild it when a second DR corpus is measured.
BANDS_DR = {
    "mean shot (s)":        (1.27, 1.49, 2.11, 2.59),
    "shots that move %":    (40, 48, 77, 79),
    "wide (WS/EWS) %":      (0, 0, 13, 24),
    "close (MCU/CU/XCU) %": (6, 6, 26, 33),
    "eye/shoulder height %": (55, 65, 73, 80),
    "same-size cuts %":     (29, 30, 40, 80),
    "cuts jumping 2+ sizes %": (0, 0, 40, 46),
    "longest held run":     (1, 3, 5, 9),
}
BANDS_BY = {"award": BANDS, "dr": BANDS_DR}
CARD_LABEL = {"award": "38 measured ads",
              "dr": "13 measured DR ads (lab-00009, one agency — provisional)"}


def baseline_card(rows: list, regime: str = "award") -> dict:
    """The piece's numbers against the real-ad bands. Call after lint() has normalised the rows."""
    bands = BANDS_BY[regime]
    ok = [r for r in rows if r.get("_size")]
    out = {}
    if len(ok) < 4:
        return out
    durs = [r["_dur"] for r in ok if r.get("_dur")]
    pct = lambda n: round(100 * n / len(ok))
    moving = [r.get("_move", "locked") != "locked" for r in ok]
    pairs = [(a["_size"], b["_size"]) for a, b in zip(ok, ok[1:]) if a["_size"] in SIZES and b["_size"] in SIZES]
    best = cur = 0
    for m in moving:
        cur = 0 if m else cur + 1; best = max(best, cur)
    vals = {
        "mean shot (s)": round(sum(durs) / len(durs), 2) if durs else None,
        "shots that move %": pct(sum(moving)),
        "wide (WS/EWS) %": pct(sum(r["_size"] in ("EWS", "WS") for r in ok)),
        "close (MCU/CU/XCU) %": pct(sum(r["_size"] in ("MCU", "CU", "XCU") for r in ok)),
        "eye/shoulder height %": pct(sum(r["_height"] in ("eye", "shoulder") for r in ok)),
        "same-size cuts %": round(100 * sum(a == b for a, b in pairs) / len(pairs)) if pairs else None,
        "cuts jumping 2+ sizes %": round(100 * sum(abs(SIZES.index(a) - SIZES.index(b)) >= 2 for a, b in pairs)
                                         / len(pairs)) if pairs else None,
        "longest held run": best,
    }
    for k, v in vals.items():
        lo, q1, q3, hi = bands[k]
        if v is None:
            out[k] = (v, "n/a", ""); continue
        if q1 <= v <= q3:
            verdict, fix = "in", ""
        elif lo <= v <= hi:
            verdict, fix = "ok", ""
        else:
            verdict = "OUT"
            fix = FIX[k][0] if v < lo else FIX[k][1]
        out[k] = (v, verdict, fix)
    return out


def print_card(card: dict, regime: str = "award", short_total: float | None = None) -> None:
    bands = BANDS_BY[regime]
    print(f"\n## Baseline card — this piece against {CARD_LABEL[regime]} (sequence-grammar.md §2c)\n")
    print("| Measure | This piece | Middle half of real ads | 8 ads in 10 | |")
    print("|---|---|---|---|---|")
    for k, (v, verdict, _) in card.items():
        lo, q1, q3, hi = bands[k]
        print(f"| {k} | {v if v is not None else '—'} | {q1:g}–{q3:g} | {lo:g}–{hi:g} | {verdict} |")
    outs = [(k, fix) for k, (v, verdict, fix) in card.items() if verdict == "OUT"]
    print()
    if not outs:
        print("Inside what 8 ads in 10 do on every measure. Do not revise toward the middle: a range is not a target.")
    for k, fix in outs:
        if short_total is not None and regime == "award":
            print("note    " + SHORT_NOTE.format(total=short_total) + f"{k}: {fix}")
        else:
            print(f"revise  {k}: {fix} — or keep it on purpose and say why in Break")
    if outs and not (short_total is not None and regime == "award"):
        print("Fix only these lines, each for a story reason, and never by relabelling a size or height: the labels "
              "describe the frame. Run the card after the director's review pass, not instead of it (§2c item 14).")


def run(path: str, strict: bool, baseline: bool = False, regime: str = "award", job: str | None = None) -> int:
    md = open(path, encoding="utf-8").read()
    rows, err = parse(md)
    if err:
        for e in err:
            print(f"FAIL  {e}")
        return 1
    r = lint(rows, parse_contrast(md), regime, job_aspect(path, job))
    for x in r["info"]:
        print(f"info  {x}")
    for x in r["warns"]:
        print(f"WARN  {x}")
    for x in r["fails"]:
        print(f"FAIL  {x}")
    print(f"{r['rows']} shot(s) · {len(r['fails'])} fail · {len(r['warns'])} warn")
    if baseline:
        print_card(baseline_card(rows, regime), regime, r["total_s"] if r.get("short_vertical") else None)
    return 1 if r["fails"] or (strict and r["warns"]) else 0


GOOD = """# Shotlist

## Sequence chain (one row per shot)
| Shot | Scene | Beat | Size | Height | Tilt | Key | Colour | Int. | Turn | Target | Dur | To camera | Move | Break |
|------|-------|------|------|--------|------|-----|--------|------|------|--------|-----|-----------|------|-------|
| 1 | S1 | orient | WS | eye | level | flat | warm | 0 | - | - | 4.0 | no | crane | - |
| S1-C1 | S1 | exchange | MCU | eye | level | left | warm | 1 | - | the guest | 3.0 | no | locked | - |
| S1B | S1 | stimulus | INSERT | eye | down 60 | left | warm | - | - | - | 1.5 | no | rack | - |
| S1-R | S1 | reaction | CU | eye | level | left | warm | 2 | late: the nod | the meter | 3.5 | no | push | the one approach move |
| 5 | S1 | decision | MS | hip | level | camera-left | warm | 1 | - | the door | 2.5 | no | track | - |
| 6 | CTA | resolution | MS | eye | level | front | cool | 1 | - | the lens | 4.0 | yes | locked | - |

Contrast: size: wide → tight

## Notes
"""


def selftest() -> int:
    def check(md: str, regime: str = "award") -> dict:
        rows, err = parse(md)
        assert not err, err
        return lint(rows, parse_contrast(md), regime)
    g = check(GOOD)
    assert not g["fails"] and not g["warns"], (g["fails"], g["warns"])
    assert any("no Energy column" in x for x in g["info"]), "a chain without Energy is told once, as info"
    def with_energy(vals):
        out, k = [], 0
        for ln in GOOD.splitlines():
            if ln.startswith("| Shot |"):
                ln += " Energy |"
            elif ln.startswith("|---"):
                ln += "--------|"
            elif ln.startswith("| ") and k < len(vals):
                ln += f" {vals[k]} |"; k += 1
            out.append(ln)
        return "\n".join(out)
    _n = sum(1 for ln in GOOD.splitlines() if ln.startswith("| ") and not ln.startswith("| Shot |"))
    _has = lambda r, k, nd: any(nd in x for x in r[k])
    assert _has(check(with_energy([3] * _n)), "warns", "the energy is flat"), "one level everywhere is no shape"
    assert not _has(check(with_energy(([2, 4, 5, 1] * 9)[:_n])), "warns", "energy"), "a planned shape passes"
    assert _has(check(with_energy([9] * _n)), "fails", "must be 1–5")
    assert any("S1: WS → MCU → INSERT → CU → MS" in x for x in g["info"]), g["info"]

    def mut(old: str, new: str) -> dict:
        assert old in GOOD, old
        return check(GOOD.replace(old, new, 1))

    def has(r: dict, kind: str, needle: str) -> bool:
        return any(needle in x for x in r[kind])

    # owed and vocabulary: FAIL, and nothing else is judged on an unready table
    r = mut("| 5 | S1 | decision | MS |", "| 5 | S1 | decision | <NEEDS DIRECTION> |")
    assert has(r, "fails", "still owed"), r
    assert has(mut("| orient |", "| establish |"), "fails", "Beat 'establish'")
    assert has(mut("| 5 | S1 | decision | MS | hip |", "| 5 | S1 | decision | MS | low |"), "fails",
               "Height 'low'"), "'low' is not a height — it is two settings"
    assert has(mut("| down 60 |", "| high angle |"), "fails", "Tilt 'high angle'")
    # the relight — FAIL inside a scene, silent across a boundary, blind to flat
    assert has(mut("| 5 | S1 | decision | MS | hip | level | camera-left |",
                   "| 5 | S1 | decision | MS | hip | level | right |"), "fails", "the relight")
    assert not has(g, "fails", "the relight"), "flat WS + left CUs is ONE key side"
    # the trust tilt
    assert has(mut("| 6 | CTA | resolution | MS | eye | level |", "| 6 | CTA | resolution | MS | knee | up 20 |"),
               "fails", "talks to camera from below")
    _above = mut("| 6 | CTA | resolution | MS | eye | level |", "| 6 | CTA | resolution | MS | above | down 20 |")
    assert not has(_above, "fails", "talks to camera") and has(_above, "warns", "not significant"), \
        "from above is a WARN: the one study found no significant drop there"
    # confetti palette — within a scene only
    assert has(mut("| S1-R | S1 | reaction | CU | eye | level | left | warm |",
                   "| S1-R | S1 | reaction | CU | eye | level | left | cool |"), "warns", "confetti")
    # the jump — and the same jump carried by a tighter frame is not one
    j = mut("| S1-R | S1 | reaction | CU | eye | level | left | warm | 2 |",
            "| S1-R | S1 | reaction | MCU | eye | level | left | warm | 3 |")
    assert has(j, "warns", "the jump"), j["warns"]
    assert not has(mut("| S1-R | S1 | reaction | CU | eye | level | left | warm | 2 |",
                       "| S1-R | S1 | reaction | CU | eye | level | left | warm | 3 |"), "warns", "the jump"), \
        "1→3 from MCU to CU cuts tighter: the frame carries it"
    # the unpaired angle — and the pair
    ua = mut("| S1-C1 | S1 | exchange | MCU | eye | level |", "| S1-C1 | S1 | exchange | MCU | eye | up 30 |")
    assert has(ua, "warns", "unpaired angle"), ua["warns"]
    paired = GOOD.replace("| S1-C1 | S1 | exchange | MCU | eye | level |",
                          "| S1-C1 | S1 | exchange | MCU | eye | up 30 |", 1) \
                 .replace("| S1-R | S1 | reaction | CU | eye | level |", "| S1-R | S1 | reaction | CU | eye | down 30 |", 1)
    assert not has(check(paired), "warns", "unpaired angle"), "low answered by high is the pair"
    # the orphan reaction
    orph = GOOD.replace("| S1-C1 | S1 | exchange |", "| S1-C1 | S1 | decision |", 1) \
               .replace("| S1B | S1 | stimulus |", "| S1B | S1 | decision |", 1)
    assert has(check(orph), "warns", "orphan reaction")
    # reaction → cause → realisation (specifics-catalogue.md §1.5): the cause withheld one shot
    withheld = orph.replace("| 5 | S1 | decision | MS |", "| 5 | S1 | stimulus | MS |", 1)
    assert not has(check(withheld), "warns", "orphan reaction"), "the reveal straight after is the exception"
    # the turn too short
    assert has(mut("| late: the nod | the meter | 3.5 |", "| late: the nod | the meter | 1.0 |"),
               "warns", "a change needs time")
    # two releases; the drift; a wide peak is INFO
    two = GOOD.replace("| 2 | late: the nod", "| 3 | late: the nod", 1) \
              .replace("| decision | MS | hip | level | camera-left | warm | 1 |",
                       "| decision | MS | hip | level | camera-left | warm | 3 |", 1)
    assert has(check(two), "warns", "full releases")
    assert has(mut("| the door |", "| - |"), "warns", "the drift")
    assert has(mut("| 1 | S1 | orient | WS | eye | level | flat | warm | 0 |",
                   "| 1 | S1 | orient | WS | eye | level | flat | warm | 3 |"), "info", "a peak at WS")
    # structure: missing section, missing column, shifted column
    assert parse("# nothing")[1], "no section must be reported, not passed"
    assert "missing column" in parse(GOOD.replace("| Target |", "| Aim |", 1))[1][0]
    assert "cells" in parse(GOOD.replace("| 4.0 | no | crane | - |", "| 4.0 | no | crane | - | extra |", 1))[1][0]
    # ── the camera plan and the contrast plan (2026-10-04, lab-00005) ──
    LOCK = {"| crane | - |": "| locked | - |", "| rack | - |": "| locked | - |",
            "| push | the one approach move |": "| locked | - |", "| track | - |": "| locked | - |"}
    frozen = GOOD
    for o, nw in LOCK.items():
        frozen = frozen.replace(o, nw, 1)
    fz = check(frozen)
    assert has(fz, "warns", "the frozen camera") and has(fz, "warns", "by the book"), fz["warns"]
    assert not has(fz, "warns", "held shots in a row"), "six held shots is inside what real ads do"
    # nine held in a row: past the award-winners' 75th percentile
    rows9 = "".join(f"| {k} | S1 | orient | WS | eye | level | flat | warm | 0 | - | - | 1.5 | no | locked | - |\n"
                    for k in range(1, 10))
    long_hold = GOOD.replace("| 6 | CTA |", rows9.replace("| 1 | S1 |", "| 1x | S1 |", 1) + "| 6 | CTA |", 1)
    lh = check(long_hold)
    assert has(lh, "warns", "held shots in a row"), lh["warns"]
    # the ad baseline (§2c)
    slow = GOOD
    for o, nw in [("| 4.0 | no | crane", "| 6.0 | no | crane"), ("| 3.0 | no | locked", "| 5.0 | no | locked"),
                  ("| 2.5 | no | track", "| 5.0 | no | track")]:
        slow = slow.replace(o, nw, 1)
    assert has(check(slow), "warns", "slow for an ad"), check(slow)["warns"]
    # (v2.69.0) a short vertical film (9:16, 45 s or less): the 38-ad baseline prints as notes citing §16.9
    rs_, _ = parse(slow); sv_ = lint(rs_, parse_contrast(slow), "award", "9:16")
    assert sv_["short_vertical"] and not has(sv_, "warns", "slow for an ad") \
        and any("slow for an ad" in x and "§16.9" in x for x in sv_["info"]), (sv_["warns"], sv_["info"])
    rs_, _ = parse(slow); assert has(lint(rs_, parse_contrast(slow), "award", "16:9"), "warns", "slow for an ad")
    long_v = re.sub(r"\| \d\.\d \| (no|yes) \|", r"| 9.0 | \1 |", slow)
    rs_, _ = parse(long_v); lv_ = lint(rs_, parse_contrast(long_v), "award", "9:16")
    assert not lv_["short_vertical"] and has(lv_, "warns", "slow for an ad"), (lv_["total_s"], lv_["warns"])
    with tempfile.TemporaryDirectory() as tdv:
        os.makedirs(os.path.join(tdv, "00-brief")); os.makedirs(os.path.join(tdv, "01-script"))
        open(os.path.join(tdv, "00-brief", "CHECKPOINT.md"), "w").write("Mode:       P\nFormat:     vertical-1080 (master)\n")
        sp_ = os.path.join(tdv, "01-script", "SHOTLIST.md"); open(sp_, "w").write(slow)
        assert job_aspect(sp_) == "9:16" and job_aspect(sp_, os.path.join(tdv, "nowhere")) is None
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_ = run(sp_, strict=False, baseline=True)
        out_ = buf.getvalue()
        assert rc_ == 0 and "revise  mean shot" not in out_ and "note    note, not a target" in out_, out_
        open(os.path.join(tdv, "00-brief", "CHECKPOINT.md"), "w").write("Mode:       P\nFormat:     landscape-1080\n")
        assert job_aspect(sp_) == "16:9", job_aspect(sp_)                 # the preset decides, not a default
        open(os.path.join(tdv, "00-brief", "CHECKPOINT.md"), "w").write("Format:     vertical-1080p\n")
        assert job_aspect(sp_) is None                                    # an unknown preset is said, never guessed
    # (build review 1, Grok) a chain with another fail keeps the short-vertical flag, so the card stays a note
    bad_ = slow.replace("| crane |", "| swoosh |", 1)
    rb_, _ = parse(bad_); lb_ = lint(rb_, parse_contrast(bad_), "award", "9:16")
    assert lb_["fails"] and lb_["short_vertical"], (lb_["fails"], lb_.get("short_vertical"))
    assert not has(check(GOOD), "warns", "slow for an ad") and not has(check(GOOD), "warns", "no world") \
        and not has(check(GOOD), "warns", "height spread"), check(GOOD)["warns"]
    # the baseline card: GOOD sits inside 8 in 10 on pace; the slow variant is OUT on pace
    rows_g, _ = parse(GOOD); lint(rows_g, parse_contrast(GOOD)); cg = baseline_card(rows_g)
    assert cg["mean shot (s)"][1] in ("in", "ok"), cg["mean shot (s)"]
    rows_s, _ = parse(slow); lint(rows_s, parse_contrast(slow)); cs = baseline_card(rows_s)
    assert cs["mean shot (s)"][1] == "OUT" and "time on screen" in cs["mean shot (s)"][2], cs["mean shot (s)"]
    assert set(cg) == set(BANDS), "every band is reported"
    # the DR regime (lab-00009): a DR-shaped piece — no wides, mediums and inserts, ~1.4 s shots — is OUT on
    # wide against the award bands and not against the DR bands, and the award "no world" warn stays quiet
    dr = GOOD.replace("| 1 | S1 | orient | WS |", "| 1 | S1 | orient | MS |", 1)
    for o, nw in [("| 4.0 | no | crane", "| 1.3 | no | crane"), ("| 3.0 | no | locked", "| 1.2 | no | locked"),
                  ("| 3.5 | no | push", "| 1.5 | no | push"), ("| 2.5 | no | track", "| 1.4 | no | track"),
                  ("| 4.0 | yes | locked", "| 1.6 | yes | locked")]:
        assert o in dr, o
        dr = dr.replace(o, nw, 1)
    rows_a, _ = parse(dr); lint(rows_a, parse_contrast(dr)); ca = baseline_card(rows_a)
    rows_d, _ = parse(dr); lint(rows_d, parse_contrast(dr), "dr"); cd = baseline_card(rows_d, "dr")
    assert ca["wide (WS/EWS) %"][1] == "OUT" and cd["wide (WS/EWS) %"][1] != "OUT", (ca, cd)
    assert set(cd) == set(BANDS_DR) == set(BANDS), "the DR card reports the same eight measures"
    assert has(check(dr), "warns", "no world") and not has(check(dr, "dr"), "warns", "no world")
    assert has(check(slow, "dr"), "warns", "slow for a DR ad") and not has(check(dr, "dr"), "warns", "slow")
    noworld = GOOD.replace("| 1 | S1 | orient | WS |", "| 1 | S1 | orient | MS |", 1)
    assert has(check(noworld), "warns", "no world"), check(noworld)["warns"]
    lowish = GOOD
    for _ in range(4):
        lowish = lowish.replace("| eye | level |", "| knee | up 20 |", 1)
    assert has(check(lowish), "warns", "height spread"), check(lowish)["warns"]
    allmove = GOOD.replace("| the guest | 3.0 | no | locked | - |", "| the guest | 3.0 | no | pan | - |", 1) \
                  .replace("| the lens | 4.0 | yes | locked | - |", "| the lens | 4.0 | yes | pull | - |", 1)
    assert has(check(allmove), "warns", "nothing holds"), check(allmove)["warns"]
    pushy = GOOD
    for o in ["| crane | - |", "| rack | - |", "| track | - |"]:
        pushy = pushy.replace(o, "| push | - |", 1)
    assert has(check(pushy), "warns", "every move is a push-in"), check(pushy)["warns"]
    assert has(mut("| crane | - |", "| swoosh | - |"), "fails", "Move 'swoosh'")
    assert not has(mut("| crane | - |", "| static | - |"), "fails", "Move"), "an alias is a move word"
    nobreak = GOOD.replace("| push | the one approach move |", "| push | - |", 1)
    assert has(check(nobreak), "warns", "by the book")
    assert has(check(GOOD.replace("Contrast: size: wide → tight\n", "", 1)), "fails", "no `Contrast:` line")
    assert has(mut("Contrast: size: wide → tight", "Contrast: size: tight → wide"), "warns", "do not deliver"), \
        "WS→MCU at the top and MS→MS at the bottom is tighter, not wider"
    assert has(mut("Contrast: size: wide → tight", "Contrast: mood: calm → wild"), "fails", "component 'mood'")
    assert has(mut("Contrast: size: wide → tight", "Contrast: rhythm: short → long"), "warns", "do not deliver"), \
        "3.5 s average at the top against 3.25 s at the bottom is not slower"
    assert not has(mut("Contrast: size: wide → tight", "Contrast: rhythm: long → short"), "warns", "do not deliver"), \
        "...and it is faster, so long → short is delivered"
    assert has(mut("Contrast: size: wide → tight", "Contrast: tone: bright → dark"), "info", "not measurable")
    aff = GOOD.replace("| S1B | S1 | stimulus | INSERT | eye | down 60 |", "| S1B | S1 | stimulus | CU | eye | level |", 1)
    for o in ["| crane | - |", "| rack | - |", "| push | the one approach move |"]:
        aff = aff.replace(o, "| locked | - |" if o != "| push | the one approach move |" else "| locked | x |", 1)
    aff = aff.replace("| 1 | S1 | orient | WS |", "| 1 | S1 | orient | MCU |", 1).replace("| locked | x |", "| locked | - |", 1)
    assert has(check(aff), "warns", "an affinity run"), check(aff)["warns"]
    # the file path works end to end, and --strict turns a WARN into exit 1
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "SHOTLIST.md")
        open(p, "w").write(GOOD)
        assert run(p, strict=False) == 0
        open(p, "w").write(GOOD.replace("| the door |", "| - |", 1))
        assert run(p, strict=False) == 0 and run(p, strict=True) == 1
    print("selftest OK — owed cells and closed vocabularies fail first; the relight fails inside a "
          "scene and not across one (flat does not count); direct address from below fails (from above warns); the "
          "confetti palette, the jump (unless the frame carries it), the unpaired angle (unless "
          "answered), the orphan reaction, the short turn, a second release and the drift warn; the camera plan "
          "(frozen, nothing holds, held runs past the award-winners' p75, push-in monoculture, unknown moves), the ad baseline (slow, no world, height spread; notes on a 9:16 film of 45 s or less), affinity runs, no break, "
          "and a contrast plan that is missing, unknown, or not delivered by the rows")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shotlist", nargs="?")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any WARN as well")
    ap.add_argument("--baseline", action="store_true",
                    help="also print the baseline card: this piece against 38 measured ads (§2c item 14)")
    ap.add_argument("--regime", choices=REGIMES, default="award",
                    help="award (default: 38 award-winning ads) or dr (13 direct-response ads, lab-00009, "
                         "provisional) — sets the card's bands and the ad-baseline WARNs")
    ap.add_argument("--job", help="the job folder whose CHECKPOINT `Format:` sets the aspect (default: found from "
                                  "the shotlist's folders)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.shotlist:
        ap.print_help(); return 2
    return run(a.shotlist, a.strict, a.baseline, a.regime, a.job)


if __name__ == "__main__":
    sys.exit(main())
