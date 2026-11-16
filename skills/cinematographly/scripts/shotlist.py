#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""shotlist.py — derive the shot list from the approved script, instead of starting from a blank.

  shotlist.py <job> [--script FILE] [--out FILE] [--force]
  shotlist.py <job> --check          does the shot list still match the script it came from?
  shotlist.py --selftest

WHY DERIVE IT
`SHOTLIST-<slug>.md` was a template you filled by hand, which meant every project re-decided things
the approved script had already settled — the beats, their order, who speaks, what each one carries
— and re-decided them from memory, next to the script rather than out of it. The two then drifted,
and the shot list is what the prompts are written from.

So: parse the approved script, emit one row per beat with everything the SCRIPT already fixed
filled in, and everything the DIRECTOR owes marked `<NEEDS DIRECTION>`.

⛔ WHAT IT WILL NOT DO
It will not invent a shot size, a camera move, an eyeline or a performance. Those are the
director's, and a plausible guess in that column is worse than a blank one — a blank gets filled,
a guess gets approved. Every field this tool cannot read out of the script is marked, and
`--check` counts what is still marked so the gate can refuse a shot list nobody has directed.

It also does not decide the beat COUNT. That is `beat_plan.py`, from the client's runtime
arithmetic (`references/script-format.md`), and this reads whatever the approved script contains —
if the script has the wrong number of scenes, the fix is upstream, not here.

WHAT IT DOES ADD, because the doctrine requires it and forgetting is the norm
- one **listener/reaction** row per dialogue exchange — silent, cheap, and the edit's insurance
  (`direction.md` §3 coverage floor)
- one **insert** row per dialogue clip, marked as owed rather than invented
Both arrive as rows marked `<NEEDS DIRECTION>`: the tool is saying *this is missing*, not *here is
what it should be*.

FILMED SHOTS — THE FRAME RATE IS WRITTEN ON THE SHOT
A shot filmed on a real camera, not generated, carries `source: real` and `fps: <rate>` anywhere in
its row of the shot table (the Description cell is the usual place). `--check` WARNs on a filmed shot
with no `fps:` and FAILs a rate that is not one of 23.976 · 24 · 25 · 29.97 · 30 · 47.952 · 48 · 50 ·
59.94 · 60 · 100 · 119.88 · 120 (a trailing `fps` or `p` is accepted). A shot with no `source:` is a
generated shot: it carries no frame rate and is not checked. No rate is ever filled in for you.

FILMED SHOTS — THE CAMERA'S SETTINGS, AS READ OFF IT
The same row may also carry what the camera was set to, beside `fps:`, each written `name: value`
anywhere in a `source: real` row:
  lens: <n> | <n>mm            the focal length the shot used; a zoom's range is not a lens
  stop: f/<n> | T<n>           the slash is optional (`f<n>`, `T/<n>`); a bare number is refused,
                               because an f-stop and a T-stop of one number are not one exposure
  shutter: 1/<n> | <deg>°      a speed or an angle (`<deg>deg` is read too); a bare number is refused
  iso: <n>                     a whole number; a comma between thousands is read
  nd: <n> stops | <density>    `<n> stop`, `<n>st` too; a number WITH a point is a density
                               (`0.<n>`, `ND0.<n>`); `none` · `off` · `0` for no filter. A filter
                               factor (`ND<n>`, `1/<n>`) is refused with its stops and density named.
                               ND and stop change together, so write them as a pair.
  wb: <n>K                     the Kelvin the camera shows; a preset name or auto is refused
  focus: <mode>                manual (or mf) · af-c · af-s · af-a
Every one is optional and none has a default. A filmed shot missing any of them gets an `info` line,
never a WARN, and nothing is filled in for you. `--check` FAILs a value that does not read as its
field, with a hint, and that FAIL refuses like a bad rate does. On a shot not marked `source: real`
they are noted (info) and not checked, the same as `fps:` there.
Of the seven, ONLY the lens millimetres also belong in a frame prompt: a frame generated to match or
cut with this shot carries the mm in its [CAMERA] block — the mm token is a cue the model does
respond to (`cinematography-craft.md` §7.1), and `prompt_lint.py` warns on a [CAMERA] block with no
focal length. A stop, a shutter, an ISO, an ND, a white balance and a focus mode are settings made on
set that no caption carries; they are not prompt controls (§7.0). The white balance goes to the
grade, as the Kelvin on the blocking card's LIGHT line does (`ai-generation.md`, "Motivated lighting
in nouns").
"""
from __future__ import annotations

import argparse
import math                               # a filter factor's stops and density, in a hint
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# One folding rule for character labels across the whole pipeline. ⛔ Two copies would drift, and
# the failure would be silent in the worst way: the shot list would count two speakers and the
# breakdown one, or the reverse, and neither would say so.
from breakdown import char_key            # noqa: E402

NEEDS = "<NEEDS DIRECTION>"
SKETCHES_SECTION = """## Their sketches (stage 3 — `../references/storyboarding.md` §2; read by `board.py storyboard` and `gate.py approve storyboard`)
Ask the person for a sketch or a phone photo for the three to five shots that carry the film. One line per picture,
saved under `01-script/storyboard/their/`; their words after the path are optional. Or record a skip in their words.
<!-- - <SHOT>: 01-script/storyboard/their/<file>.jpg: "<their words>"
     skipped: "<their words>" -->
"""
HOOK_RE = re.compile(r"^\[HOOK\s*([^\]]*)\]\s*(.*)$", re.I)
CTA_RE = re.compile(r"^\[CTA\s*([^\]]*)\]\s*(.*)$", re.I)
# `[SCENE 1 — …]  ESTABLISH — <location>. …`  ·  any language's word for scene, per script-format.md
SCENE_RE = re.compile(r"^\[(?:SCENE|SCEN[ĂA]|SZENE|SCÈNE|ESCENA)\s*(\d+)?\s*[—–\-:]?\s*([^\]]*)\]\s*(.*)$",
                      re.I)
# `<CHARACTER A>: „line"` or `HOST: "line"` — a speaker label then the line
# ⛔ `(` `)` `.` are in the label class because a standard screenplay cue — `BAKER (V.O.):`,
# `HOST (CONT'D):` — is a label, and without them the line matched NOTHING and was dropped from the
# shot list in silence. A line that vanishes is worse than a line miscounted: nothing downstream can
# see that it is gone. char_key() then folds the cue away so the speaker is still one person.
LINE_RE = re.compile(r"^\s*([A-ZĂÂÎȘȚ][A-Za-zĂÂÎȘȚăâîșț0-9 _<>'().-]{0,30})\s*:\s*[„\"“'](.+?)[\"”'']?\s*$")

# the frame rate is written on each real-shoot shot, not on the job. `source: real` marks a
# filmed shot; a row without it is generated and carries no rate. The list is the rates a camera or a
# delivery actually uses; nothing here is a default.
VALID_FPS = ("23.976", "24", "25", "29.97", "30", "47.952", "48", "50", "59.94", "60", "100", "119.88", "120")
SOURCE_RE = re.compile(r"\bsource\s*:\s*`?(real|generated)\b", re.I)
FPS_RE = re.compile(r"\bfps\s*:\s*`?([^\s|`·,;]+)", re.I)
SHOT_ROW_RE = re.compile(r"^\|\s*\d+\s*\|")          # the shot table's rows: the first cell is a number

# the camera's own settings on a filmed shot, read off the camera and written beside `fps:`.
# Each is optional and none has a default: a missing one is info, never a WARN, and nothing is ever
# filled in. Only the lens millimetres also go into a frame prompt (cinematography-craft.md §7.1);
# the rest are on-set settings no caption carries (§7.0). A value ends where FPS_RE's does, and may
# keep its unit after one space (`35 mm`, `3 stops`, `180 °`, `5600 K`).
CAMERA_FIELDS = ("lens", "stop", "shutter", "iso", "nd", "wb", "focus")
_VAL = r"[^\s|`·,;]+"
CAMERA_RE = {
    "lens": re.compile(rf"\blens\s*:\s*`?({_VAL}(?:\s?mm\b)?)", re.I),
    "stop": re.compile(rf"\bstop\s*:\s*`?({_VAL})", re.I),
    "shutter": re.compile(rf"\bshutter\s*:\s*`?({_VAL}(?:\s?°|\s?deg\b)?)", re.I),
    # `12,800` is one ISO, not 12 followed by a separator
    "iso": re.compile(rf"\biso\s*:\s*`?(\d{{1,3}}(?:,\d{{3}})+(?!\d)|{_VAL})", re.I),
    # ⛔ `(?!\s*:)`: in `nd: 0.9 stop: f/4` the word `stop` is the next FIELD, not the ND's unit
    "nd": re.compile(rf"\bnd\s*:\s*`?((?:nd\s)?{_VAL}(?:\s?(?:stops?|st)\b(?!\s*:))?)", re.I),
    "wb": re.compile(rf"\bwb\s*:\s*`?({_VAL}(?:\s?k\b)?)", re.I),
    "focus": re.compile(rf"\bfocus\s*:\s*`?({_VAL})", re.I),
}
CAMERA_LABEL = {"lens": "focal length", "stop": "stop", "shutter": "shutter setting", "iso": "ISO",
                "nd": "ND", "wb": "white balance", "focus": "focus mode"}
# the modes written in generic words; `-`, `_` and case are folded, so `AF-C`, `afc` and `af_c` are one
FOCUS_MODES = {"manual": "manual", "mf": "manual", "afc": "af-c", "afs": "af-s", "afa": "af-a"}


def read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def find_script(job: str) -> str:
    """The APPROVED script if the gate recorded one, else the highest-versioned file on disk."""
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import gate as G
        j = G.Job(os.path.abspath(job)) if hasattr(G, "Job") else None
        if j is not None:
            sc = j.approved("script")
            if sc and sc.get("artifact"):
                p = os.path.join(job, sc["artifact"])
                if os.path.isfile(p):
                    return p
    except Exception:
        pass
    cands = []
    for root, dirs, files in os.walk(job):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_to_delete"))]
        cands += [os.path.join(root, f) for f in files
                  if re.match(r"^SCRIPT-.*\.md$", f, re.I)]
    if not cands:
        return ""

    def ver(p):
        m = re.search(r"-v(\d+)", os.path.basename(p), re.I)
        return int(m.group(1)) if m else 0
    return sorted(cands, key=lambda p: (ver(p), p))[-1]


def parse_script(text: str) -> list:
    """[{kind, label, time, note, lines:[(speaker, line)]}] — hook, scenes, CTA, in script order."""
    beats, cur = [], None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = HOOK_RE.match(line.strip())
        if m:
            cur = {"kind": "hook", "label": "HOOK", "time": m.group(1).strip(),
                   "note": m.group(2).strip(), "lines": []}
            beats.append(cur)
            continue
        m = CTA_RE.match(line.strip())
        if m:
            cur = {"kind": "cta", "label": "CTA", "time": m.group(1).strip(),
                   "note": m.group(2).strip(), "lines": []}
            beats.append(cur)
            continue
        m = SCENE_RE.match(line.strip())
        if m:
            n = m.group(1) or str(sum(1 for b in beats if b["kind"] == "scene") + 1)
            cur = {"kind": "scene", "label": f"S{n}", "time": "",
                   "note": " ".join(x for x in (m.group(2), m.group(3)) if x).strip(),
                   "lines": []}
            beats.append(cur)
            continue
        if cur is None:
            continue
        m = LINE_RE.match(line)
        if m and not line.strip().startswith(("#", ">", "|", "-", "_")):
            cur["lines"].append((m.group(1).strip(), m.group(2).strip()))
    return beats


def rows_from(beats: list) -> list:
    """One row per shot. A dialogue line is a clip; each exchange owes a reaction and an insert."""
    rows, n = [], 0
    for b in beats:
        if b["kind"] in ("hook", "cta"):
            # ⛔ One row per hook/CTA beat used to mean ONE LINE ONLY: a second spoken line in the
            # [INTRO] or [CTA] block vanished from the shot list entirely — no shot, no start frame,
            # no VO, no clip — after passing script_score, claims_lint and the human's approval.
            # The shot list is derived from the approved script precisely so the two cannot drift,
            # and it was silently dropping script. One line is one clip here as everywhere else.
            if not b["lines"]:
                n += 1
                rows.append({"n": n, "time": b["time"] or NEEDS, "scene": b["label"],
                             "size": NEEDS, "action": b["note"] or NEEDS, "move": NEEDS,
                             "carries": b["note"] or NEEDS, "owed": "script"})
                continue
            for i, (who, line) in enumerate(b["lines"], 1):
                n += 1
                label = b["label"] if len(b["lines"]) == 1 else f"{b['label']}-C{i}"
                rows.append({"n": n, "time": (b["time"] or NEEDS) if i == 1 else NEEDS,
                             "scene": label, "size": NEEDS,
                             "action": f"{who} — {b['note']}".strip(" —") or NEEDS,
                             "move": NEEDS, "carries": f"{who}: {line}", "owed": "script"})
            continue
        if not b["lines"]:
            n += 1
            rows.append({"n": n, "time": NEEDS, "scene": b["label"], "size": NEEDS,
                         "action": b["note"] or NEEDS, "move": NEEDS, "carries": "—",
                         "owed": "script"})
            continue
        for i, (who, line) in enumerate(b["lines"], 1):
            n += 1
            rows.append({"n": n, "time": NEEDS, "scene": f"{b['label']}-C{i}", "size": NEEDS,
                         "action": f"{who} — {b['note']}".strip(" —") or NEEDS,
                         "move": NEEDS, "carries": f"{who}: {line}", "owed": "script"})
        # the coverage floor: a reaction and an insert per exchange, marked as OWED not invented
        n += 1
        rows.append({"n": n, "time": NEEDS, "scene": f"{b['label']}-R", "size": NEEDS,
                     "action": "listener reaction (silent) — the edit's insurance", "move": NEEDS,
                     "carries": "—", "owed": "coverage floor · direction.md §3"})
        n += 1
        rows.append({"n": n, "time": NEEDS, "scene": f"{b['label']}B", "size": "Insert",
                     "action": f"insert — {NEEDS} (hands / prop / product)", "move": NEEDS,
                     "carries": "—", "owed": "coverage floor · direction.md §3"})
    return rows


def render(job: str, script_path: str, beats: list, rows: list) -> str:
    slug = os.path.basename(os.path.abspath(job))
    # ⛔ Speakers are counted on a NORMALISED key, not on raw label text. `HOST`, `Host` and
    # `HOST (V.O.)` are one speaker; counting them as three overstated the cast on every script
    # that used a cue or changed case — the same defect breakdown.py carried, in the tool that
    # feeds it. char_key() is breakdown.py's, so one script cannot fold a name the other splits.
    seen: dict = {}
    for b in beats:
        for w, _ in b["lines"]:
            seen.setdefault(char_key(w), []).append(w)
    speakers = sorted(v[0] for v in seen.values())
    aliased = {v[0]: sorted(set(v)) for v in seen.values() if len(set(v)) > 1}
    dialogue = [r for r in rows if re.search(r"-C\d+$", r["scene"])]
    L = [f"# Shotlist / Storyboard — {slug}", ""]
    L.append(f"> Derived from `{os.path.relpath(script_path, os.path.abspath(job))}` by "
             f"`scripts/shotlist.py`. Everything the SCRIPT fixed is filled in; everything the "
             f"DIRECTOR owes is marked `{NEEDS}`.")
    L.append(f"> ⛔ Nothing in the shot size, camera move or performance columns was guessed. A "
             f"plausible guess there is worse than a blank — a blank gets filled, a guess gets "
             f"approved. `shotlist.py <job> --check` counts what is still owed.")
    L.append("")
    L.append("| # | Time | Scene | Shot size | Description / action | Camera move / end-frame | "
             "Carries (line / TEXT) | Owed by |")
    L.append("|---|------|-------|-----------|----------------------|-------------------------|"
             "-----------------------|---------|")
    for r in rows:
        L.append(f"| {r['n']} | {r['time']} | {r['scene']} | {r['size']} | {r['action']} | "
                 f"{r['move']} | {r['carries']} | {r['owed']} |")
    # the two optional fields a filmed shot carries; generated shots carry neither
    L.append(f"> A shot filmed on a real camera carries `source: real` and `fps: <rate>` in its row — the "
             f"frame rate is written on the shot, not on the job. `--check` warns on a filmed shot with no "
             f"rate and fails one not in {' · '.join(VALID_FPS)}.")
    # and, beside the rate, the camera's own settings as read off it; no value is written here
    L.append("> It may also carry the camera's settings as read off it, beside the rate: `lens: <n>` or "
             "`<n>mm` · `stop: f/<n>` or `T<n>` · `shutter: 1/<n>` or `<deg>°` · `iso: <n>` · "
             "`nd: <n> stops` or a density · `wb: <n>K` · `focus: manual|af-c|af-s|af-a`. All optional, "
             "none filled in; `--check` fails one it cannot read. Only the lens mm also goes into a frame "
             "prompt — stop, shutter and the rest are not prompt controls.")
    L.append("")
    L.append(f"_{len(rows)} shot(s) · {len(dialogue)} dialogue clip(s) · "
             f"{len(speakers)} speaker(s): {', '.join(speakers) or '—'}_")
    for disp, spell in sorted(aliased.items()):
        L.append("")
        L.append(f"> ⛔ **{disp}** is labelled {len(spell)} ways in the script — "
                 + ", ".join(f"`{x}`" for x in spell) +
                 " — and is counted here as one speaker. Settle it in the SCRIPT: a label that "
                 "varies is how a reference stops being found and a cast list stops being a count.")
    L.append("")
    L.append("## Blocking card (one per scene — fill BEFORE prompting any start frame; "
             "`../references/direction.md` §2)")
    for b in beats:
        if b["kind"] != "scene":
            continue
        L.append("```")
        L.append(f"[BLOCKING — {b['label']}]   {b['note']}")
        for k in ("GEOGRAPHY", "POSITIONS", "THE LINE", "EYELINES", "PROPS", "LIGHT"):
            L.append(f"{k + ':':<11}{NEEDS}")
        L.append("```")
    L.append("")
    L.append("## Performance cards (one per dialogue/reaction clip; becomes the [PERFORMANCE] block — "
             "card v2, `../references/direction.md` §1)")
    L.append("| Clip | STATE (transition) | STIMULUS (what, when) | TARGET (who/what, where) | "
             "BEAT (before held, then one change) | BODY (MS or wider) | FACE (incl. the negative) | GAZE |")
    L.append("|------|--------------------|-----------------------|--------------------------|"
             "-------------------------------------|--------------------|---------------------------|------|")
    for r in dialogue:
        L.append(f"| {r['scene']} | {NEEDS} | {NEEDS} | {NEEDS} | {NEEDS} | {NEEDS} | {NEEDS} | {NEEDS} |")
    L.append("")
    # ⛔ THE CHAIN IS WRITTEN BEFORE ANY PROMPT (2026-09-30). Every generation is stateless, so a
    # sequence exists only if each row restates what it inherits. sequence_lint.py reads this table;
    # every cell is owed by the director, and a blank is the honest state until it is decided.
    L.append("## Sequence chain (one row per shot, in cut order — `../references/sequence-grammar.md` §8; "
             "check with `scripts/sequence_lint.py`)")
    L.append("| Shot | Scene | Beat | Size | Height | Tilt | Move | Key | Colour | Int. | Turn | Target | Dur | Energy | To camera | Break |")
    L.append("|------|-------|------|------|--------|------|------|-----|--------|------|------|--------|-----|--------|-----------|-------|")
    for r in rows:
        scene = re.sub(r"-[A-Z][A-Za-z0-9]*$", "", r["scene"])
        L.append(f"| {r['scene']} | {scene} | " + " | ".join([NEEDS] * 14) + " |")
    L.append("")
    # ⛔ THE CONTRAST PLAN IS OWED LIKE ANY OTHER CELL (2026-10-04, lab-00005). A chain of pure
    # continuity is the flat version of the piece; the plan says what peaks, and where.
    L.append(f"Contrast: {NEEDS}")
    L.append("")
    L.append("Beat: orient · reorient · exchange · stimulus · reaction · dilemma · decision · release · "
             "montage · climax · resolution · insert. Size: EWS WS MWS MS MCU CU XCU INSERT. Height: "
             "ground knee hip shoulder eye above overhead aerial. Tilt: level · up <deg> · down <deg> · "
             "top-down · dutch. Move: locked · push · pull · pan · tilt · track · crane · orbit · "
             "handheld · whip · rack · drift · roll. Key: left right front back top under silhouette "
             "flat none. Int.: 0–3 or - (no performer). Turn: - · early: … · late: … · through: …. "
             "Dur: seconds on screen in the cut, not the generated clip. Energy: 1–5, the shot's energy in the "
             "sequence — plan it like music, fast, fast, hold (`../references/sequence-grammar.md` §2d). To camera: yes/no. Break: - or the baseline this shot breaks on purpose. "
             "Contrast: one or two of movement · rhythm · size · space · tone · colour · line, each "
             "written `a → b` (`../references/sequence-grammar.md` §2b).")
    L.append("")
    L.append("## Emotional journey map (write this FIRST — the STATE fields above are read off it; "
             "`../references/emotional-journey.md` §2)")
    L.append("| # | Open question the viewer is holding | Intended VIEWER emotion | "
             "Value pair & direction | Character state | CARRIED BY |")
    L.append("|---|-------------------------------------|-------------------------|"
             "------------------------|-----------------|------------|")
    for b in beats:
        L.append(f"| {b['label']} | {NEEDS} | {NEEDS} | {NEEDS} | {NEEDS} | {NEEDS} |")
    L.append("> ⛔ **If every row of CARRIED BY says \"face\", the piece has one instrument and it "
             "is the weakest one.** Irony, an insert, an object, a withheld fact or a join should "
             "carry at least a third.")
    L.append("")
    L.append("## Handoff cards (one per shot — the join is a GENERATION instruction; "
             "`../references/shot-handoff.md` §5)")
    L.append("| Shot | FUNCTION | IN (frame one · inherits) | OUT (composed end frame) | "
             "JOIN → next | PRESENCE |")
    L.append("|------|----------|---------------------------|--------------------------|"
             "-------------|----------|")
    for r in rows:
        # ⛔ PRESENCE (close · room · distant) is the audio half of shot size, and this pipeline had
        # no field for it: every line is ONE TTS render, so the close-up and the wide carry
        # byte-identical dry audio unless somebody decides otherwise. Blank like every other
        # directorial field — presence follows the CUT, not the script, and a whispered line in a
        # wide legitimately inverts the default. A blank gets filled; a guess gets approved.
        L.append(f"| {r['scene']} | {NEEDS} | {NEEDS} | {NEEDS} | {NEEDS} | {NEEDS} |")
    L.append("")
    L.append("PRESENCE: `close` · `room` · `distant` — one reverb send per LOCATION, then trim the "
             "voice by shot size (`../references/editing-and-audio.md`, Sound perspective and space).")
    L.append("")
    L.append("## Coverage floor (per dialogue exchange — `../references/direction.md` §3)")
    L.append(f"- [ ] Speaker clip (audio-driven) · [ ] **Listener reaction** (silent — the edit's "
             f"insurance) · [ ] One insert (hands/prop/product) · [ ] Scene B-roll ≥ dialogue clips")
    L.append("")
    # (v2.66.0) the person's own pictures for the storyboard — asked for, never invented (storyboarding.md §2)
    L.append(SKETCHES_SECTION)
    return "\n".join(L)


def owed(path: str) -> dict:
    txt = read(path)
    return {"file": path, "needs": txt.count(NEEDS),
            "rows": sum(1 for ln in txt.splitlines()
                        if ln.startswith("| ") and re.match(r"^\|\s*\d+\s*\|", ln))}


def _fps_value(raw: str):
    """A written rate as a float, or None. `24`, `24.0`, `24fps` and `24p` are the same rate."""
    v = re.sub(r"(?:fps|p)$", "", raw.strip().lower())
    try:
        return float(v)
    except ValueError:
        return None


def fps_findings(text: str) -> list:
    """[(level, message)] for the frame rate on each filmed shot of the shot table.

    WARN: a `source: real` shot with no `fps:` (or a placeholder). FAIL: a rate not in VALID_FPS.
    info: an `fps:` on a shot not marked filmed — not checked, generated shots carry no rate."""
    out = []
    valid = [float(x) for x in VALID_FPS]
    for ln in text.splitlines():
        if not SHOT_ROW_RE.match(ln):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        where = f"row {cells[0]}" + (f" ({cells[2]})" if len(cells) > 2 and cells[2] else "")
        src, fps = SOURCE_RE.search(ln), FPS_RE.search(ln)
        if not (src and src.group(1).lower() == "real"):
            if fps:
                out.append(("info", f"{where}: fps: {fps.group(1)} on a shot not marked `source: real` — not "
                                    f"checked; a generated shot carries no frame rate"))
            continue
        if not fps or fps.group(1).startswith("<"):
            out.append(("WARN", f"{where}: `source: real` and no `fps:` — write the frame rate on the shot, "
                                f"not on the job (one of {' · '.join(VALID_FPS)})"))
            continue
        v = _fps_value(fps.group(1))
        if v is None or not any(abs(v - x) < 1e-6 for x in valid):
            near = min(VALID_FPS, key=lambda x: abs(float(x) - v)) if v is not None else None
            hint = f" — did you mean {near}?" if near and abs(float(near) - v) <= 0.1 else ""
            out.append(("FAIL", f"{where}: fps: {fps.group(1)} is not a valid frame rate (one of "
                                f"{' · '.join(VALID_FPS)}){hint}"))
    return out


# one reader per camera field: None when the value reads, else the hint a FAIL carries.
# The ranges are typo guards, not claims about any camera, and a hint never writes a value for you
# beyond the one you wrote, with its unit or its letter.
_NUM = r"(\d+(?:\.\d+)?|\.\d+)"


def _lens_hint(v: str):
    s = re.sub(r"\s?mm$", "", v.strip().lower())
    if re.match(rf"^{_NUM}\s*[-–]\s*{_NUM}$", s):
        return "a zoom's range is not the shot's lens; write the focal length the shot used, as `<n>` or `<n>mm`"
    if not re.fullmatch(_NUM, s):
        return "write the focal length in millimetres, as `<n>` or `<n>mm`"
    n = float(s)
    return None if 0 < n <= 2000 else "a focal length is above 0 and at most 2000 mm; a typo?"


def _stop_hint(v: str):
    m = re.fullmatch(rf"([ft])/?{_NUM}", v.strip(), re.I)
    if m:
        return None if 0.5 <= float(m.group(2)) <= 64 else "outside f/0.5–f/64; a typo?"
    if re.fullmatch(_NUM, v.strip()):
        return (f"write the letter the lens shows, f/{v.strip()} or T{v.strip()}; the two are not the same "
                f"exposure")
    return "write the stop as `f/<n>` or `T<n>`"


def _shutter_hint(v: str):
    s = v.strip().lower()
    m = re.fullmatch(rf"1/{_NUM}s?", s)
    if m:
        return None if float(m.group(1)) >= 1 else "a speed is written 1/<n> with n of 1 or more"
    m = re.fullmatch(rf"{_NUM}\s?(?:°|deg)", s)
    if m:
        return None if 0 < float(m.group(1)) <= 360 else "an angle is above 0° and at most 360°"
    if re.fullmatch(_NUM, s) and float(s) > 0:
        return (f"write 1/{s} for a speed or {s}° for an angle; the camera shows which" if float(s) <= 360
                else f"write 1/{s} for a speed")
    return "write a speed as `1/<n>` or an angle as `<deg>°`"


def _iso_hint(v: str):
    s = v.strip().replace(",", "")
    if re.fullmatch(r"\d+", s) and int(s) > 0:
        return None
    if s.lower() in ("auto", "a"):
        return "auto is a mode, not a reading; write the number the camera shows, as `<n>`"
    return "write the ISO the camera shows as a whole number, `<n>`"


def _nd_hint(v: str):
    s = v.strip().lower()
    if s in ("0", "none", "off", "clear"):
        return None
    m = re.fullmatch(rf"{_NUM}\s?(?:stops?|st)", s)
    if m:
        return None if float(m.group(1)) <= 20 else "over 20 stops; a typo?"
    m = re.fullmatch(r"(?:nd\s?)?(\d*\.\d+)", s)
    if m:
        d = float(m.group(1))
        return None if 0 < d <= 6 else "a density above 0 and at most 6.0 (20 stops); a typo?"
    m = re.fullmatch(r"nd\s?(\d+)|1/(\d+)", s)
    if m and int(m.group(1) or m.group(2)) >= 2:
        f = int(m.group(1) or m.group(2))
        return (f"that reads as a filter factor; write it as stops or a density "
                f"(a factor of {f} is {math.log2(f):.3g} stops, density {math.log10(f):.2g})")
    if re.fullmatch(r"\d+", s):
        return (f"stops or density? write `{s} stops`, or a density with its point "
                f"({s} stops is {int(s) * 0.3:.1f})")
    return "write `<n> stops`, a density with its point (`0.<n>`), or `none`"


def _wb_hint(v: str):
    s = v.strip().lower()
    m = re.fullmatch(r"(\d+)\s?k", s)
    if m:
        return None if 1000 <= int(m.group(1)) <= 20000 else "outside 1000–20000K; a typo?"
    if re.fullmatch(r"\d+", s) and 1000 <= int(s) <= 20000:
        return f"write it with its unit: {s}K"
    return ("write the Kelvin the camera shows, as `<n>K`; a preset name or auto is not a number the "
            "grade can use")


def _focus_hint(v: str):
    s = re.sub(r"[-_\s]", "", v.strip().lower())
    if s in FOCUS_MODES:
        return None
    if s in ("af", "auto", "autofocus"):
        return "which autofocus: af-c (continuous), af-s (single) or af-a (the camera switches)?"
    return "write the mode: manual (mf) · af-c · af-s · af-a"


CAMERA_HINT = {"lens": _lens_hint, "stop": _stop_hint, "shutter": _shutter_hint, "iso": _iso_hint,
               "nd": _nd_hint, "wb": _wb_hint, "focus": _focus_hint}


def camera_findings(text: str) -> list:
    """[(level, message)] for the camera settings on each filmed shot of the shot table.

    FAIL: a value that does not read as its field, with a hint. info: a `source: real` shot missing
    any of lens · stop · shutter · iso · nd · wb · focus (optional, never a WARN; a placeholder is a
    missing value), and any of them on a shot not marked filmed — not checked, as `fps:` there."""
    out = []
    for ln in text.splitlines():
        if not SHOT_ROW_RE.match(ln):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        where = f"row {cells[0]}" + (f" ({cells[2]})" if len(cells) > 2 and cells[2] else "")
        src = SOURCE_RE.search(ln)
        found = {}
        for k in CAMERA_FIELDS:
            m = CAMERA_RE[k].search(ln)
            if m:
                found[k] = m.group(1)
        if not (src and src.group(1).lower() == "real"):
            if found:
                out.append(("info", f"{where}: {' · '.join(f'{k}: {v}' for k, v in found.items())} on a shot "
                                    f"not marked `source: real` — not checked; camera settings are read off a "
                                    f"real camera, and a generated shot's lens is the mm in its prompt"))
            continue
        written = {k: v for k, v in found.items() if not v.startswith("<")}
        for k, v in written.items():
            hint = CAMERA_HINT[k](v.rstrip("."))          # `lens: 35mm.` ends a sentence, not the value
            if hint:
                out.append(("FAIL", f"{where}: {k}: {v} is not a valid {CAMERA_LABEL[k]} — {hint}"))
        missing = [k for k in CAMERA_FIELDS if k not in written]
        if missing:
            # ND and stop change together on a shoot, so one without the other is worth a word
            pair = ("; nd: and stop: change together, so write them as a pair"
                    if ("nd" in missing) != ("stop" in missing) else "")
            out.append(("info", f"{where}: no {' · '.join(k + ':' for k in missing)} — optional; read them "
                                f"off the camera if you have them, none is filled in{pair}"))
    return out


def out_path(job: str) -> str:
    slug = os.path.basename(os.path.abspath(job))
    return os.path.join(job, "01-script", f"SHOTLIST-{slug}.md")


# -------------------------------------------------------------------------------------- selftest
SCRIPT_FIXTURE = """# SCRIPT v3 — fixture

## Control idea (one sentence)
Bread proves itself.

## SCRIPT

[HOOK 0:00–0:06]  the room before anyone arrives
<TEXT record: "Every loaf, before six.">

[SCENE 1 — the bench]  ESTABLISH — a working bakery. the situation made concrete
HOST: „Every loaf is turned out by hand."
BAKER: „Before six, every day."

[SCENE 2 — the counter]  TURN — one value changes
HOST: „Then we open the door."

[CTA 0:55–1:05]  the resolved state, in-world branding.  one ask
HOST: „Come before they go."
"""


def selftest() -> int:
    import tempfile
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond or not detail
                                                            else f"\n        {detail}"))
        ok = ok and bool(cond)

    beats = parse_script(SCRIPT_FIXTURE)
    kinds = [b["kind"] for b in beats]
    check("hook, scenes and CTA are found in script order",
          kinds == ["hook", "scene", "scene", "cta"])
    check("the hook keeps its timecode", beats[0]["time"].startswith("0:00"))
    check("a scene's own note survives", "ESTABLISH" in beats[1]["note"])
    check("both speakers in a scene are captured",
          [w for w, _ in beats[1]["lines"]] == ["HOST", "BAKER"])
    check("the line text is captured without its quotes",
          beats[1]["lines"][0][1] == "Every loaf is turned out by hand.")

    # ⛔ THE SPEAKER COUNT. `HOST`, `Host` and `HOST (V.O.)` are one person; the old code counted
    # the raw label, so a script that varied its own labels — which is common, and is exactly what
    # a script audit exists to catch — reported a cast of three.
    varied = SCRIPT_FIXTURE.replace(
        'BAKER: \u201eBefore six, every day."',
        'BAKER: \u201eBefore six, every day."\n'
        'Baker: \u201eHe starts at four."\n'
        'BAKER (V.O.): \u201eAnd finishes at noon."')
    assert varied != SCRIPT_FIXTURE, "the fixture edit must actually apply"
    vbeats = parse_script(varied)
    vrows = rows_from(vbeats)
    out = render("/tmp/x", "/tmp/x/SCRIPT.md", vbeats, vrows)
    check("⛔ three spellings of one name are ONE speaker, not three",
          "3 speaker(s)" not in out and "2 speaker(s)" in out)
    check("and the varying label is REPORTED rather than quietly folded",
          "labelled 3 ways" in out and "`BAKER`" in out and "`Baker`" in out
          and "`BAKER (V.O.)`" in out)
    check("the (V.O.) line still reaches a row of its own",
          any("finishes at noon" in r["carries"] for r in vrows))

    rows = rows_from(beats)
    dial = [r for r in rows if re.search(r"-C\d+$", r["scene"])]
    check("ONE DIALOGUE LINE = ONE CLIP: three lines in scenes → three dialogue rows", len(dial) == 3)
    check("scene 1 produces two clips, not one",
          [r["scene"] for r in dial][:2] == ["S1-C1", "S1-C2"])
    check("every scene owes a listener reaction",
          sum(1 for r in rows if r["scene"].endswith("-R")) == 2)
    check("and an insert", sum(1 for r in rows if r["scene"].endswith("B")) == 2)
    check("the coverage rows say WHO owes them",
          all("coverage floor" in r["owed"] for r in rows if r["scene"].endswith(("-R", "B"))))
    check("⛔ no shot size or camera move is ever guessed",
          all(r["size"] == NEEDS for r in rows if r["scene"] != "S1B" and r["size"] != "Insert")
          and all(r["move"] == NEEDS for r in rows))
    check("what the script DID say is filled in, not blanked",
          any("turned out by hand" in r["carries"] for r in rows))

    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "bk-01001")
        os.makedirs(os.path.join(job, "01-script"))
        sp = os.path.join(job, "01-script", "SCRIPT-fixture-v3.md")
        open(sp, "w").write(SCRIPT_FIXTURE)
        check("the highest-versioned script is found on disk", find_script(job) == sp)
        open(os.path.join(job, "01-script", "SCRIPT-fixture-v4.md"), "w").write(SCRIPT_FIXTURE)
        check("v4 wins over v3", find_script(job).endswith("v4.md"))

        doc = render(job, sp, beats, rows)
        dest = out_path(job)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w").write(doc)
        o = owed(dest)
        check("the shot list is written where the ladder expects it",
              dest.endswith(os.path.join("01-script", "SHOTLIST-bk-01001.md")))
        check("--check counts what is still owed", o["needs"] > 20 and o["rows"] == len(rows))
        check("a blocking card exists per scene", doc.count("[BLOCKING —") == 2)
        # the performance table and the handoff table both key on the clip id, so count inside
        # the performance section rather than across the whole document
        perf = doc.split("## Performance cards")[1].split("## Sequence chain")[0]
        check("a performance card exists per dialogue clip, and only for dialogue clips",
              perf.count("| S1-C1 |") == 1 and perf.count("| S1-R |") == 0
              and sum(1 for ln in perf.splitlines() if ln.startswith("| S")) == len(dial))
        chain = doc.split("## Sequence chain")[1].split("## Emotional journey")[0]
        check("a sequence-chain row exists for EVERY shot, in order — the chain is what each "
              "stateless generation inherits",
              [ln.split("|")[1].strip() for ln in chain.splitlines()
               if ln.startswith("| ") and not ln.startswith("| Shot")] == [r["scene"] for r in rows])
        check("the chain derives the scene from the clip id (S1-C1 is scene S1)",
              "| S1-C1 | S1 |" in chain)
        check("the chain carries Move, Energy and Break columns and owes a Contrast line",
              "| Move |" in chain and "| Energy |" in chain and "| Break |" in chain and f"Contrast: {NEEDS}" in chain)
        check("the performance card is v2 — STIMULUS, TARGET and BODY are owed, not optional",
              "STIMULUS" in perf and "TARGET" in perf and "BODY" in perf)
        hand = doc.split("## Handoff cards")[1]
        labels = {r["scene"] for r in rows}
        got = {ln.split("|")[1].strip() for ln in hand.splitlines() if ln.startswith("|")}
        check("a handoff card exists for EVERY shot, dialogue or not — the join is a generation "
              "instruction, so the silent rows need one too",
              labels <= got, f"missing {sorted(labels - got)}")
        check("the derivation names its source script", "SCRIPT-fixture-v3.md" in doc)
        check("and states plainly that nothing was guessed", "worse than a blank" in doc)

        # an empty script yields nothing rather than a fabricated list
        check("a script with no beats produces no rows", rows_from(parse_script("# nothing")) == [])

    print("-" * 60)
    # ⛔ every spoken line in the script must reach exactly one row — including lines in the
    # [HOOK]/[INTRO] and [CTA] beats, which used to be truncated to the first line
    multi = ("[HOOK 0:00-0:06]\nANA: \"You have never met the baker.\"\n"
             "ANA: \"That is the whole problem.\"\n\n"
             "[SCENE 1 - 0:06-0:20]  the bench.\nANA: \"He starts at four.\"\n\n"
             "[CTA 0:20-0:28]\nANA: \"We open at six.\"\nANA: \"Come and meet him.\"\n")
    bts = parse_script(multi)
    rws = rows_from(bts)
    carried = " || ".join(r["carries"] for r in rws)
    for line in ("You have never met the baker.", "That is the whole problem.",
                 "He starts at four.", "We open at six.", "Come and meet him."):
        check(f"the script line {line!r} reaches a row", line in carried)
    spoken = sum(len(b["lines"]) for b in bts)
    rows_with_lines = sum(1 for r in rws if ":" in r["carries"] and r["carries"] != "—")
    check("one spoken line is exactly one line-carrying row",
          spoken == rows_with_lines and spoken == 5)

    # the PRESENCE column exists, is blank, and is counted as owed direction
    doc_ = render("/tmp/j", "SCRIPT.md", bts, rws)
    check("the handoff card carries a PRESENCE column", "| PRESENCE |" in doc_)
    check("PRESENCE ships blank like every other directorial field",
          doc_.count(NEEDS) >= len(rws) * 5)
    check("and the card says what the three values mean",
          "close" in doc_ and "distant" in doc_ and "one reverb send per LOCATION" in doc_)

    # ---- the frame rate is written on each filmed shot, and only on filmed shots ----
    TABLE = ("| # | Time | Scene | Shot size | Description / action | Camera move / end-frame | Carries | Owed by |\n"
             "|---|---|---|---|---|---|---|---|\n"
             "| 1 | 0:00 | HOOK | MCU | the open · source: real · fps: 24 | locked | HOST: line | script |\n"
             "| 2 | 0:06 | S1 | WS | coverage · source: real | push | — | script |\n"
             "| 3 | 0:12 | S1B | Insert | the pour · source: real · fps: 23.98 | locked | — | script |\n"
             "| 4 | 0:15 | S2 | MS | generated b-roll · fps: 30 | pan | — | script |\n"
             "| 5 | 0:20 | S3 | CU | generated, no fields | locked | — | script |\n"
             "| 6 | 0:24 | S4 | Insert | the whip · source: real · fps: 59.94 | whip | — | script |\n"
             "| 7 | 0:26 | S5 | MS | slowed · source: real · fps: `30fps` | locked | — | script |\n"
             "| 8 | 0:28 | CTA | MS | the ask · source: real · fps: <rate> | locked | — | script |\n")
    ff = fps_findings(TABLE)
    by_row = {m.split(":")[0].split(" (")[0]: lv for lv, m in ff}
    check("HR-02 a filmed shot with a valid rate passes", "row 1" not in by_row and "row 6" not in by_row)
    check("HR-02 a filmed shot with no fps: WARNs", by_row.get("row 2") == "WARN")
    check("HR-02 an invalid rate FAILs, and the near miss is named",
          by_row.get("row 3") == "FAIL" and any("did you mean 23.976" in m for _, m in ff))
    check("HR-02 a generated shot is not checked, even with an fps: on it (info only)",
          by_row.get("row 4") == "info" and "row 5" not in by_row)
    check("HR-02 `30fps` reads as 30", "row 7" not in by_row)
    check("HR-02 a placeholder rate is a missing rate (WARN), not a pass", by_row.get("row 8") == "WARN")
    check("HR-02 every listed rate is valid, and nothing else in between",
          not fps_findings("".join(f"| {i} | t | S | MS | source: real · fps: {v} | x | — | s |\n"
                                   for i, v in enumerate(VALID_FPS, 1)))
          and fps_findings("| 1 | t | S | MS | source: real · fps: 26 | x | — | s |\n")[0][0] == "FAIL")
    check("HR-02 no default rate is ever written into a derived shot list",
          not FPS_RE.search(render("/tmp/j", "SCRIPT.md", bts, rws).replace("`fps: <rate>`", "")))
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "fps-01001")
        os.makedirs(os.path.join(job, "01-script"))
        dest = out_path(job)
        open(dest, "w", encoding="utf-8").write(TABLE.replace("fps: 23.98", "fps: 23.976"))
        r = subprocess.run([sys.executable, os.path.abspath(__file__), job, "--check"],
                           capture_output=True, text=True, timeout=60)
        check("HR-02 --check prints the WARN and exits 0 when nothing fails and nothing is owed",
              r.returncode == 0 and "WARN" in r.stdout and "frame rate" in r.stdout, r.stdout + r.stderr)
        open(dest, "w", encoding="utf-8").write(TABLE)
        r = subprocess.run([sys.executable, os.path.abspath(__file__), job, "--check"],
                           capture_output=True, text=True, timeout=60)
        check("HR-02 --check exits 1 on an invalid rate", r.returncode == 1 and "FAIL" in r.stdout,
              r.stdout + r.stderr)

    # ---- the camera's settings on a filmed shot, read off it; only the mm is a prompt control ----
    def row(cell, n=1):
        return f"| {n} | 0:00 | S1 | MS | {cell} | locked | — | script |\n"

    good = {"lens": ["35", "35mm", "35 mm", "10.5mm"],
            "stop": ["f/2.8", "F/1.4", "f4", "T2.1", "t/2.8"],
            "shutter": ["1/50", "1/47.95", "1/120s", "180°", "172.8deg", "180 °"],
            "iso": ["800", "12,800"],
            "nd": ["3 stops", "1 stop", "2st", "0.9", ".6", "ND0.6", "ND 1.2", "none", "0"],
            "wb": ["5600K", "3200k", "4300 K"],
            "focus": ["manual", "mf", "af-c", "AF-S", "afa"]}
    for k, vals in good.items():
        for v in vals:
            cf = camera_findings(row(f"source: real · fps: 24 · {k}: {v}"))
            check(f"HR-26 {k}: {v} reads", not [m for lv, m in cf if lv == "FAIL"], str(cf))
    full = ("source: real · fps: 24 · lens: 35mm · stop: T2.8 · shutter: 180° · iso: 800 · nd: 0.6 · "
            "wb: 5600K · focus: manual")
    check("HR-26 a filmed shot with all seven settings readable has no finding at all",
          camera_findings(row(full)) == [], str(camera_findings(row(full))))
    check("HR-26 the stop's unit is not swallowed as the ND's (`nd: 0.9 stop: f/4`)",
          camera_findings(row("source: real · nd: 0.9 stop: f/4 · lens: 50 · shutter: 1/50 · iso: 400 · "
                              "wb: 3200K · focus: af-c")) == [])

    bad = [("lens", "fifty", "millimetres"), ("lens", "24-70", "zoom's range"), ("lens", "0", "typo"),
           ("lens", "3550mm", "typo"),
           ("stop", "2.8", "f/2.8 or T2.8"), ("stop", "f/0.2", "typo"), ("stop", "wide", "`f/<n>` or `T<n>`"),
           ("shutter", "50", "1/50 for a speed or 50°"), ("shutter", "400°", "at most 360°"),
           ("shutter", "1/0.5", "n of 1 or more"), ("shutter", "fast", "`1/<n>`"),
           ("iso", "auto", "not a reading"), ("iso", "800.5", "whole number"), ("iso", "0", "whole number"),
           ("nd", "3", "3 stops is 0.9"), ("nd", "ND8", "3 stops, density 0.9"), ("nd", "1/16", "4 stops"),
           ("nd", "dark", "`<n> stops`"), ("nd", "25 stops", "typo"),
           ("wb", "5600", "5600K"), ("wb", "daylight", "preset name or auto"), ("wb", "560K", "typo"),
           ("focus", "af", "af-c (continuous)"), ("focus", "sharp", "manual (mf) · af-c")]
    for k, v, hint in bad:
        cf = camera_findings(row(f"source: real · fps: 24 · {k}: {v}"))
        fl = [m for lv, m in cf if lv == "FAIL"]
        check(f"HR-26 {k}: {v} FAILs, with the hint {hint!r}",
              len(fl) == 1 and f"{k}: {v} is not a valid" in fl[0] and hint in fl[0], str(cf))

    cf = camera_findings(row("source: real · fps: 24") + row("source: real · fps: 25 · lens: <mm> · wb: <n>K", 2))
    check("HR-26 missing settings are ONE info line per filmed shot, never a WARN or a FAIL",
          [lv for lv, _ in cf] == ["info", "info"] and all("none is filled in" in m for _, m in cf), str(cf))
    check("HR-26 a placeholder is a missing value, not a written one",
          "lens:" in cf[1][1] and "wb:" in cf[1][1])
    cf = camera_findings(row("source: real · nd: 0.6 · lens: 35 · shutter: 1/50 · iso: 800 · wb: 5600K · "
                             "focus: mf"))
    check("HR-26 an ND with no stop is noted as a pair (info, not a WARN)",
          len(cf) == 1 and cf[0][0] == "info" and "no stop:" in cf[0][1] and "as a pair" in cf[0][1], str(cf))
    cf = camera_findings(row("generated b-roll · lens: 35 · iso: lots · fps: 30") + row("generated, none", 2))
    check("HR-26 settings on a generated shot are info only and not checked, even a malformed one",
          [lv for lv, _ in cf] == ["info"] and "not marked `source: real`" in cf[0][1]
          and "iso: lots" in cf[0][1], str(cf))
    derived = render("/tmp/j", "SCRIPT.md", bts, rws)
    check("HR-26 no camera setting is ever written into a derived shot list's rows",
          not any(CAMERA_RE[k].search(ln) for ln in derived.splitlines() if SHOT_ROW_RE.match(ln)
                  for k in CAMERA_FIELDS))
    check("HR-26 the derived shot list says only the mm also goes into a frame prompt",
          "Only the lens mm also goes into a frame prompt" in derived)
    tpl = os.path.join(SKILL_ROOT, "assets", "shotlist-template.md")
    if os.path.isfile(tpl):
        cf = camera_findings(read(tpl))
        check("HR-26 the template's filmed row is all placeholders: info, no FAIL",
              cf and all(lv == "info" for lv, _ in cf), str(cf))
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "cam-01001")
        os.makedirs(os.path.join(job, "01-script"))
        dest = out_path(job)
        open(dest, "w", encoding="utf-8").write(row("source: real · fps: 24") + row("source: real · fps: 25", 2))
        r = subprocess.run([sys.executable, os.path.abspath(__file__), job, "--check"],
                           capture_output=True, text=True, timeout=60)
        check("HR-26 --check prints the missing settings as info and still exits 0",
              r.returncode == 0 and "info" in r.stdout and "WARN" not in r.stdout
              and "camera settings: 2 filmed shot(s) · 0 fail · 2 info" in r.stdout,
              r.stdout + r.stderr)
        open(dest, "w", encoding="utf-8").write(row("source: real · fps: 24 · stop: 2.8"))
        r = subprocess.run([sys.executable, os.path.abspath(__file__), job, "--check"],
                           capture_output=True, text=True, timeout=60)
        check("HR-26 --check exits 1 on a malformed setting, and prints its hint",
              r.returncode == 1 and "FAIL" in r.stdout and "f/2.8 or T2.8" in r.stdout, r.stdout + r.stderr)

    print("selftest OK — the script's beats, speakers and lines are read out of it in order; one "
          "line is one clip; every exchange owes a reaction and an insert, marked as owed; and no "
          "shot size, camera move or performance is ever invented; and a filmed shot's frame rate "
          " is warned when missing and failed when invalid, generated shots untouched; and its "
          "camera settings are failed when unreadable and only noted when missing"
          if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", nargs="?")
    ap.add_argument("--script", help="the script to derive from (default: the approved one)")
    ap.add_argument("--out")
    ap.add_argument("--force", action="store_true", help="overwrite an existing shot list")
    ap.add_argument("--check", action="store_true", help="how much is still owed by the director")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.job or not os.path.isdir(a.job):
        ap.print_help()
        return 2
    dest = a.out or out_path(a.job)
    if a.check:
        if not os.path.isfile(dest):
            print(f"no shot list at {os.path.relpath(dest)} — `shotlist.py {a.job}` derives one "
                  f"from the approved script", file=sys.stderr)
            return 1
        o = owed(dest)
        print(f"SHOTLIST — {os.path.relpath(dest)}\n  {o['rows']} shot row(s) · "
              f"{o['needs']} field(s) still {NEEDS}")
        if o["needs"]:
            print("  ⛔ Those are the director's, and the tool refused to guess them. A shot list "
                  "full of blanks is an honest one; the work is filling them, not generating past "
                  "them.")
        # the frame rate on each filmed shot: a WARN is a finding, a FAIL refuses
        ff = fps_findings(read(dest))
        for level, msg in ff:
            print(f"  {level:<4}  {msg}")
        fails = sum(1 for lv, _ in ff if lv == "FAIL")
        filmed = sum(1 for ln in read(dest).splitlines()
                     if SHOT_ROW_RE.match(ln) and (m := SOURCE_RE.search(ln)) and m.group(1).lower() == "real")
        print(f"  frame rate: {filmed} filmed shot(s) · {fails} fail · "
              f"{sum(1 for lv, _ in ff if lv == 'WARN')} warn")
        # the camera's settings on each filmed shot: a FAIL refuses, a missing one is info
        cf = camera_findings(read(dest))
        for level, msg in cf:
            print(f"  {level:<4}  {msg}")
        cfails = sum(1 for lv, _ in cf if lv == "FAIL")
        print(f"  camera settings: {filmed} filmed shot(s) · {cfails} fail · "
              f"{sum(1 for lv, _ in cf if lv == 'info')} info — only the lens mm also goes into a frame prompt")
        return 1 if (o["needs"] or fails or cfails) else 0

    script = a.script or find_script(a.job)
    if not script or not os.path.isfile(script):
        print(f"no script found under {a.job} — approve one first "
              f"(`gate.py approve script --artifact ...`), or pass --script", file=sys.stderr)
        return 2
    beats = parse_script(read(script))
    if not beats:
        print(f"{os.path.relpath(script)} has no [HOOK] / [SCENE n] / [CTA] blocks — the shot list "
              f"is derived from those (references/script-format.md has the shape). Nothing was "
              f"written: a fabricated shot list is worse than none.", file=sys.stderr)
        return 1
    if os.path.isfile(dest) and not a.force:
        print(f"REFUSED: {os.path.relpath(dest)} already exists. It probably carries the "
              f"director's filled-in columns, and re-deriving would throw them away. --force if "
              f"you mean it.", file=sys.stderr)
        return 1
    rows = rows_from(beats)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(render(a.job, script, beats, rows))
    o = owed(dest)
    print(f"derived {len(rows)} shot row(s) from {os.path.relpath(script)}  →  "
          f"{os.path.relpath(dest)}")
    print(f"  {o['needs']} field(s) marked {NEEDS} — the director's, deliberately not guessed.")
    print("  Fill the blocking cards before any start frame is prompted (direction.md §2).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
