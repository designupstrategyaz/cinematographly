#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""storyboard.py — the film as panels in cut order, read from the shot list, and what the two
picture sign-offs still need. Shared by board.py (the pages), animatic.py (the timed reel) and
gate.py (the sign-offs), so all three read the same film. Standard library only.

  storyboard.py <job>               the panels in cut order, and what `approve storyboard` still needs
  storyboard.py <job> --json
  storyboard.py --selftest

THE FAILURE THIS EXISTS FOR (pre-production review, 2026-11-14)
Stage 3 showed the shot list and the shot boards and asked for nothing. The first time a person saw
the film as pictures in time was the first paid clip. Both reviewers put this second: reject at the
cheapest stage, which is a drawing held for its planned seconds, then a still, then video.

TWO SIGN-OFFS (version 2.66.0)
  storyboard    after `script`, before `cast`, any sheet or frame, and before any paid picture. Needs:
                the shot list with nothing marked <NEEDS DIRECTION>; a Sequence chain with a duration
                on every shot; the person's own sketch or photo on at least one panel, or their words
                for skipping; `board.py storyboard` and `animatic.py` both built from THIS shot list.
  startframes   after the start frames are approved one by one, before their clips. Needs
                `board.py frames`: every approved start frame, in cut order, on one page. A clip is
                refused until a `startframes` sign-off is newer than its shot's frame approval.

WHICH JOBS
Jobs whose 00-brief/DEVELOPMENT.md was made from the 2.65 template or later (the line
`develop-template: 2.65` that `develop.py init` writes). A job already in production when this
version is installed keeps its old chain; `gate.py status` names the sign-offs as optional there.

WHAT THE SHOT LIST CARRIES FOR THIS
  ## Sequence chain        (already required: sequence_lint.py) gives the cut order, size, move,
                           duration and energy of each shot
  the shot table           (the first table, `# | Time | Scene | Shot size | …`) gives the line each
                           shot carries and what happens in it
  ## Their sketches        the person's own drawings or photos, one per line:
                             - S1-C1: 01-script/storyboard/their/hands.jpg: "like my gran's hands"
                           or, when they would rather not draw:
                             skipped: "<their words>"
A panel's picture is, in order: their sketch; a drawing or blocking frame saved as
01-script/storyboard/<SHOT>.png|jpg|jpeg|webp; otherwise a drawn placeholder showing the shot size.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import sequence_lint as SL  # noqa: E402  (stdlib-only)

MARK_RE = re.compile(r"develop-template:\s*(\d+)\.(\d+)")
FROM_VERSION = (2, 65)
NEEDS = "<NEEDS DIRECTION>"
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
BOARD_REL = os.path.join("01-script", "BOARD-storyboard.html")
FRAMES_BOARD_REL = os.path.join("01-script", "BOARD-frames.html")
ANIMATIC_REL = os.path.join("01-script", "ANIMATIC.mp4")
ANIMATIC_JSON_REL = os.path.join("01-script", "ANIMATIC.json")
FILM_META = "cine-film-digest"
FRAMES_META = "cine-frames-digest"
SKETCH_RE = re.compile(r"^\s*[-*]\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*:\s*(\S+)\s*(?:[:—-]\s*(.*))?$")
SKIP_RE = re.compile(r"^\s*skipped\s*:\s*(.*)$", re.I)
QUOTE_RE = re.compile(r"[\"“„«]([^\"“”„«»]{3,})[\"”»]")


def read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------- which jobs
def template_version(job: str):
    p = os.path.join(job, "00-brief", "DEVELOPMENT.md")
    try:
        m = MARK_RE.search(read(p))
    except OSError:
        return None
    return (int(m.group(1)), int(m.group(2))) if m else None


def required(job: str) -> bool:
    """True when the picture sign-offs are part of this job's chain (2.65 development template or later)."""
    v = template_version(job)
    return bool(v and v >= FROM_VERSION)


# ------------------------------------------------------------------------------- the shot list
def shotlist_path(job: str) -> str:
    slug = os.path.basename(os.path.abspath(job))
    return os.path.join(job, "01-script", f"SHOTLIST-{slug}.md")


def _section(md: str, title_re: str) -> str:
    m = re.search(r"^##\s+" + title_re + r".*$", md, re.M | re.I)
    if not m:
        return ""
    body = md[m.end():]
    nxt = re.search(r"^##\s", body, re.M)
    return body[:nxt.start()] if nxt else body


def _first_table(md: str):
    """The shot table: the first markdown table whose header starts with `#`. ([header], [rows], [raw lines])"""
    lines = md.splitlines()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s.startswith("|"):
            continue
        head = [c.strip().lower() for c in s.strip("|").split("|")]
        if not head or head[0] != "#":
            continue
        raw, rows = [s], []
        for ln2 in lines[i + 1:]:
            s2 = ln2.strip()
            if not s2.startswith("|"):
                break
            raw.append(s2)
            cells = [c.strip() for c in s2.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            rows.append(dict(zip(head, cells)))
        return head, rows, raw
    return [], [], []


def _col(row: dict, prefix: str) -> str:
    for k, v in row.items():
        if k.startswith(prefix):
            return v
    return ""


def sketches(md: str) -> dict:
    """{"shots": {shot: {"path", "note"}}, "skipped": "<quote or ''>", "present": bool}"""
    # an HTML comment is the template's example, never an answer (the template's own `skipped:` example would
    # otherwise count as the person's words); a quote that is still a <placeholder> is not their words either
    body = re.sub(r"<!--.*?-->", "", _section(md, r"Their sketches"), flags=re.S)
    out = {"shots": {}, "skipped": "", "present": bool(body.strip()) or bool(
        re.search(r"^##\s+Their sketches", md, re.M | re.I))}
    for ln in body.splitlines():
        m = SKIP_RE.match(ln)
        if m:
            q = QUOTE_RE.search(m.group(1))
            out["skipped"] = q.group(1).strip() if q and not re.fullmatch(r"\s*<[^>]*>\s*", q.group(1)) else ""
            out["skipped_raw"] = m.group(1).strip()
            continue
        m = SKETCH_RE.match(ln)
        if m and not m.group(2).startswith("<"):
            out["shots"][m.group(1)] = {"path": m.group(2).strip().strip("`"),
                                        "note": (m.group(3) or "").strip()}
    return out


def _norm_lines(lines) -> list:
    return [re.sub(r"\s+", " ", ln.strip()) for ln in lines if ln.strip()]


def digest(md: str) -> str:
    """The film, as the sign-off sees it: the shot table, the Sequence chain and Their sketches.
    Blocking cards and performance cards live in the same file and change during stages 4–5;
    editing them does not unsign the storyboard. Changing a shot, its order, size, move, duration or
    line does."""
    _, _, raw = _first_table(md)
    chain = [ln for ln in _section(md, r"Sequence chain").splitlines() if ln.strip().startswith("|")]
    sk = _section(md, r"Their sketches").splitlines()
    blob = "\n".join(["#table"] + _norm_lines(raw) + ["#chain"] + _norm_lines(chain) +
                     ["#sketches"] + _norm_lines(sk))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _dur(cell: str):
    try:
        v = float(re.sub(r"[^\d.]", "", cell or "") or "x")
    except ValueError:
        return None
    return v if v > 0 else None


def picture_for(job: str, shot: str, sk: dict) -> tuple:
    """(path, source) — source is `their sketch`, `drawing` or '' for the drawn placeholder."""
    s = sk["shots"].get(shot)
    if s:
        p = s["path"] if os.path.isabs(s["path"]) else os.path.join(job, s["path"])
        if os.path.isfile(p):
            return p, "their sketch"
    for ext in IMG_EXT:
        p = os.path.join(job, "01-script", "storyboard", shot + ext)
        if os.path.isfile(p):
            return p, "drawing"
    return "", ""


def panels(job: str) -> tuple:
    """([panel], [error]) in cut order. A panel is a dict with shot, scene, beat, size, move, dur,
    energy, turn, target, line, action, time, picture, source."""
    sp = shotlist_path(job)
    if not os.path.isfile(sp):
        return [], [f"no shot list at {os.path.relpath(sp)} — `shotlist.py {os.path.relpath(job)}` derives it "
                    f"from the approved script"]
    md = read(sp)
    rows, errs = SL.parse(md)
    if errs:
        return [], errs
    _, table, _ = _first_table(md)
    by_id = {r.get("#", "").strip(): r for r in table if r.get("#")}
    sk = sketches(md)
    out = []
    for r in rows:
        shot = r.get("shot", "").strip()
        t = by_id.get(shot, {})
        pic, src = picture_for(job, shot, sk)
        out.append({"shot": shot, "scene": r.get("scene", ""), "beat": r.get("beat", ""),
                    "size": r.get("size", ""), "move": r.get("move", ""), "dur": _dur(r.get("dur", "")),
                    "energy": r.get("energy", ""), "turn": r.get("turn", ""), "target": r.get("target", ""),
                    "line": _col(t, "carries"), "action": _col(t, "description"), "time": _col(t, "time"),
                    "picture": pic, "source": src})
    return out, []


# ------------------------------------------------------------------------------- the storyboard sign-off
def board_digest(path: str, name: str) -> str:
    try:
        txt = read(path)
    except OSError:
        return ""
    m = re.search(r'<meta name="' + re.escape(name) + r'" content="([0-9a-f]{64})"', txt)
    return m.group(1) if m else ""


def sketch_problems(job: str, md: str, shot_ids: set) -> list:
    sk = sketches(md)
    probs = []
    for shot, s in sk["shots"].items():
        p = s["path"] if os.path.isabs(s["path"]) else os.path.join(job, s["path"])
        if shot not in shot_ids:
            probs.append(f"Their sketches names {shot!r}, which is not a shot in the Sequence chain")
        elif not os.path.isfile(p):
            probs.append(f"Their sketches: {s['path']} (for {shot}) is not on disk")
        elif not p.lower().endswith(IMG_EXT):
            probs.append(f"Their sketches: {s['path']} is not a picture ({', '.join(IMG_EXT)})")
    good = [k for k, s in sk["shots"].items() if k in shot_ids]
    if not good and not sk["skipped"]:
        if sk.get("skipped_raw"):
            probs.append("Their sketches: `skipped:` needs their words in quotation marks, not a summary")
        else:
            probs.append("no sketch or photo of theirs on any panel — ask for one for the three to five shots that "
                         "carry the film (`## Their sketches` in the shot list), or record their words for skipping: "
                         "`skipped: \"<their words>\"` (references/storyboarding.md §2)")
    return probs


def signoff_problems(job: str) -> list:
    """What `gate.py approve storyboard` still needs. Empty = ready to show and sign."""
    sp = shotlist_path(job)
    if not os.path.isfile(sp):
        return [f"no shot list at {os.path.relpath(sp)} — `shotlist.py {os.path.relpath(job)}`"]
    md = read(sp)
    probs = []
    n_owed = md.count(NEEDS)
    if n_owed:
        probs.append(f"the shot list still has {n_owed} field(s) marked {NEEDS} — sizes, moves and performances "
                     f"nobody has decided are not a film to sign")
    ps, errs = panels(job)
    if errs:
        return probs + [f"Sequence chain: {e}" for e in errs]
    if not ps:
        return probs + ["the Sequence chain has no shots"]
    nodur = [p["shot"] for p in ps if p["dur"] is None]
    if nodur:
        probs.append(f"no duration on {', '.join(nodur[:8])} — the animatic holds each panel for its planned seconds")
    probs += sketch_problems(job, md, {p["shot"] for p in ps})
    d = digest(md)
    bd = board_digest(os.path.join(job, BOARD_REL), FILM_META)
    if not bd:
        probs.append(f"the storyboard page has not been built — `board.py storyboard {os.path.relpath(job)}`")
    elif bd != d:
        probs.append("the storyboard page was built from a different shot list — rebuild it "
                     f"(`board.py storyboard {os.path.relpath(job)}`); you would be signing a film nobody looked at")
    aj = os.path.join(job, ANIMATIC_JSON_REL)
    try:
        man = json.load(open(aj, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        man = None
    if not man:
        probs.append(f"the animatic has not been built — `animatic.py {os.path.relpath(job)}` (free, local)")
    else:
        mp4 = os.path.join(job, man.get("mp4") or ANIMATIC_REL)
        if man.get("film_digest") != d:
            probs.append("the animatic was built from a different shot list — rebuild it "
                         f"(`animatic.py {os.path.relpath(job)}`)")
        elif not os.path.isfile(mp4):
            probs.append(f"{os.path.relpath(mp4)} is missing — rebuild the animatic")
        elif sha256_file(mp4) != man.get("mp4_sha256"):
            probs.append(f"{os.path.relpath(mp4)} is not the file the animatic manifest describes — rebuild it")
    return probs


# ------------------------------------------------------------------------------- the start-frame sheet
def _approval_rows(job: str) -> list:
    """The APPROVALS.md rows, in order: the same table gate.py writes (ts | stage | by | quote | artifact |
    sha256 | media_id | verified)."""
    p = os.path.join(job, "00-brief", "APPROVALS.md")
    try:
        txt = read(p)
    except OSError:
        return []
    rows = []
    for ln in txt.splitlines():
        if not ln.startswith("|") or re.match(r"^\|\s*(ts|-+)\s*\|", ln):
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) < 4 or not c[0]:
            continue
        rows.append({"ts": c[0], "stage": c[1], "artifact": c[4] if len(c) > 4 else "",
                     "sha": c[5] if len(c) > 5 else "", "media_id": c[6] if len(c) > 6 else ""})
    return rows


def approved_frames(job: str) -> dict:
    """{shot: {"ts", "artifact", "sha", "media_id", "index"}} — the latest `frame:<SHOT>` approval of each shot."""
    out = {}
    for i, r in enumerate(_approval_rows(job)):
        st = r["stage"]
        if st.lower().startswith("frame:"):
            out[st.split(":", 1)[1]] = {**r, "index": i}
    return out


def frames_digest(frames: dict) -> str:
    blob = "\n".join(f"{k}:{v.get('sha', '')}:{v.get('media_id', '')}" for k, v in sorted(frames.items()))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def frames_signoff_problems(job: str) -> list:
    fr = approved_frames(job)
    if not fr:
        return ["no start frame is approved yet — approve them one by one (`gate.py approve frame:<SHOT> …`), "
                "then sign the sheet"]
    bd = board_digest(os.path.join(job, FRAMES_BOARD_REL), FRAMES_META)
    if not bd:
        return [f"the start-frame sheet has not been built — `board.py frames {os.path.relpath(job)}`"]
    if bd != frames_digest(fr):
        return ["the start-frame sheet shows a different set of approved frames — rebuild it "
                f"(`board.py frames {os.path.relpath(job)}`) and look at it again"]
    return []


def startframes_covers(job: str, shot: str) -> bool:
    """Is there a `startframes` sign-off newer than this shot's frame approval?"""
    rows = _approval_rows(job)
    fi = max((i for i, r in enumerate(rows) if r["stage"].lower() == f"frame:{shot}".lower()), default=-1)
    si = max((i for i, r in enumerate(rows) if r["stage"].lower() == "startframes"), default=-1)
    return fi >= 0 and si > fi


# ------------------------------------------------------------------------------- selftest
FIXTURE = """# Shotlist — fx

| # | Time | Scene | Shot size | Description / action | Camera move / end-frame | Carries (line / TEXT) | AI-gen prompt |
|---|------|-------|-----------|----------------------|-------------------------|-----------------------|---------------|
| 1 | 0:00–0:04 | HOOK | WS | the bakery before dawn | slow push | TEXT: before six | … |
| 2 | 0:04–0:08 | S1 | CU | hands turn out a loaf | locked | BAKER: every loaf by hand | … |

## Sequence chain
| Shot | Scene | Beat | Size | Height | Tilt | Move | Key | Colour | Int. | Turn | Target | Dur | Energy | To camera | Break |
|------|-------|------|------|--------|------|------|-----|--------|------|------|--------|-----|--------|-----------|-------|
| 1 | HOOK | orient | WS | eye | level | push | left | warm | 0 | - | - | 4.0 | 2 | no | - |
| 2 | S1 | stimulus | CU | eye | down 30 | locked | left | warm | 1 | late: the loaf drops | the loaf | 3.5 | 4 | no | - |

Contrast: size: wide → tight

## Blocking card
anything here may change

## Their sketches
- 2: 01-script/storyboard/their/hands.png: "like my gran's hands"
"""


def selftest() -> int:
    import shutil
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and bool(cond)

    td = tempfile.mkdtemp(prefix="storyboard-")
    try:
        job = os.path.join(td, "fx-01001-board")
        os.makedirs(os.path.join(job, "00-brief"))
        os.makedirs(os.path.join(job, "01-script", "storyboard", "their"))
        dev = os.path.join(job, "00-brief", "DEVELOPMENT.md")
        open(dev, "w").write("# dev\n")
        check("a job with no template mark keeps the old chain", not required(job))
        open(dev, "w").write("<!-- develop-template: 2.65 -->\n# dev\n")
        check("a 2.65 development template brings the picture sign-offs", required(job))
        open(dev, "w").write("<!-- develop-template: 2.64 -->\n")
        check("an older mark does not", not required(job))
        open(dev, "w").write("<!-- develop-template: 3.1 -->\n")
        check("a later major version does", required(job))
        sp = shotlist_path(job)
        open(sp, "w").write(FIXTURE)
        open(os.path.join(job, "01-script", "storyboard", "their", "hands.png"), "wb").write(b"\x89PNG\r\n")
        ps, errs = panels(job)
        check("panels come out in cut order with the line joined from the shot table",
              not errs and [p["shot"] for p in ps] == ["1", "2"] and "every loaf" in ps[1]["line"])
        check("durations and energy are read", ps[0]["dur"] == 4.0 and ps[1]["energy"] == "4")
        check("their sketch is panel 2's picture", ps[1]["source"] == "their sketch" and ps[0]["source"] == "")
        d0 = digest(FIXTURE)
        check("editing a blocking card leaves the film digest alone",
              digest(FIXTURE.replace("anything here may change", "kitchen; window left")) == d0)
        check("changing a duration changes it", digest(FIXTURE.replace("| 3.5 |", "| 2.5 |")) != d0)
        check("changing the line a shot carries changes it", digest(FIXTURE.replace("every loaf", "each loaf")) != d0)
        probs = signoff_problems(job)
        check("unbuilt board and animatic are both named",
              any("storyboard page has not been built" in p for p in probs)
              and any("animatic has not been built" in p for p in probs))
        check("their sketch satisfies the sketch rule", not any("sketch" in p.lower() for p in probs))
        open(os.path.join(job, BOARD_REL), "w").write(f'<meta name="{FILM_META}" content="{d0}">')
        mp4 = os.path.join(job, ANIMATIC_REL)
        open(mp4, "wb").write(b"fake mp4")
        json.dump({"film_digest": d0, "mp4": ANIMATIC_REL, "mp4_sha256": sha256_file(mp4)},
                  open(os.path.join(job, ANIMATIC_JSON_REL), "w"))
        check("board + animatic from this shot list → ready to sign", signoff_problems(job) == [])
        open(mp4, "wb").write(b"another file")
        check("an animatic file swapped after the build is caught",
              any("not the file the animatic manifest" in p for p in signoff_problems(job)))
        open(mp4, "wb").write(b"fake mp4")
        open(sp, "w").write(FIXTURE.replace("| 3.5 |", "| 2.5 |"))
        sp_probs = signoff_problems(job)
        check("a shot list changed after the build → both the board and the animatic are stale",
              any("storyboard page was built from a different" in p for p in sp_probs)
              and any("animatic was built from a different" in p for p in sp_probs))
        open(sp, "w").write(FIXTURE.replace("- 2: 01-script/storyboard/their/hands.png: \"like my gran's hands\"", ""))
        check("no sketch and no skip → refused, naming the ask",
              any("no sketch or photo of theirs" in p for p in signoff_problems(job)))
        open(sp, "w").write(FIXTURE.replace("- 2: 01-script/storyboard/their/hands.png: \"like my gran's hands\"",
                                            "skipped: they were busy"))
        check("a skip with no quoted words is refused",
              any("needs their words in quotation marks" in p for p in signoff_problems(job)))
        open(sp, "w").write(FIXTURE.replace("- 2: 01-script/storyboard/their/hands.png: \"like my gran's hands\"",
                                            "skipped: \"just go with your frames\""))
        check("a skip in their words satisfies the rule", not any("sketch" in p.lower() for p in signoff_problems(job)))
        import shotlist as _SLmod
        open(sp, "w").write(FIXTURE.replace("- 2: 01-script/storyboard/their/hands.png: \"like my gran's hands\"",
                                            _SLmod.SKETCHES_SECTION.split("\n", 1)[1]))
        check("the template's commented example is not an answer (no sketch, no skip)",
              any("no sketch or photo of theirs" in p for p in signoff_problems(job)))
        open(sp, "w").write(FIXTURE.replace("- 2: 01-script/storyboard/their/hands.png: \"like my gran's hands\"",
                                            'skipped: "<their words>"'))
        check("a skip whose quote is still the <placeholder> is not their words",
              any("needs their words in quotation marks" in p for p in signoff_problems(job)))
        open(sp, "w").write(FIXTURE.replace("- 2: 01-script", "- 9: 01-script"))
        check("a sketch on a shot that does not exist is refused",
              any("not a shot in the Sequence chain" in p for p in signoff_problems(job)))
        open(sp, "w").write(FIXTURE.replace("| 2 | S1 | stimulus | CU |", "| 2 | S1 | stimulus | <NEEDS DIRECTION> |"))
        check("an undirected field refuses", any("NEEDS DIRECTION" in p for p in signoff_problems(job)))
        # the start-frame sheet
        ap = os.path.join(job, "00-brief", "APPROVALS.md")
        hdr = "# Approvals\n\n| ts | stage | by | quote | artifact | sha256 | media_id | verified |\n|---|---|---|---|---|---|---|---|\n"
        open(ap, "w").write(hdr + "| t1 | frame:1 | D | yes | 02-startframes/1.png | aaaa | m1 | transcript |\n")
        check("no sheet yet → the frames board is named", any("has not been built" in p for p in frames_signoff_problems(job)))
        fd = frames_digest(approved_frames(job))
        open(os.path.join(job, FRAMES_BOARD_REL), "w").write(f'<meta name="{FRAMES_META}" content="{fd}">')
        check("a sheet of the current frames → ready", frames_signoff_problems(job) == [])
        check("frame 1 is not covered before the sheet is signed", not startframes_covers(job, "1"))
        open(ap, "a").write("| t2 | startframes | D | the sheet works | 01-script/BOARD-frames.html | bbbb |  | transcript |\n")
        check("...and is covered after", startframes_covers(job, "1"))
        open(ap, "a").write("| t3 | frame:1 | D | the retake | 02-startframes/1b.png | cccc | m2 | transcript |\n")
        check("a frame re-approved after the sheet is no longer covered", not startframes_covers(job, "1"))
        check("...and the sheet is stale", any("different set" in p for p in frames_signoff_problems(job)))
        check("a shot with no frame approval is never covered", not startframes_covers(job, "2"))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print("storyboard.py selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("job", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.job:
        ap.error("a job folder is required")
    ps, errs = panels(a.job)
    probs = signoff_problems(a.job)
    if a.json:
        print(json.dumps({"required": required(a.job), "panels": ps, "errors": errs, "signoff": probs},
                         indent=2, ensure_ascii=False))
        return 1 if (errs or probs) else 0
    print(f"storyboard · {len(ps)} panel(s) · {sum(p['dur'] or 0 for p in ps):.1f} s · "
          f"{'required for this job' if required(a.job) else 'optional for this job (older template)'}")
    for p in ps:
        print(f"  {p['shot']:>8}  {p['size']:<6} {p['move']:<8} {(p['dur'] or 0):>4.1f}s  e{p['energy'] or '?'}  "
              f"{(p['line'] or p['action'])[:60]}" + (f"  [{p['source']}]" if p['source'] else ""))
    for e in errs:
        print(f"  ⛔ {e}")
    if probs:
        print("  approve storyboard still needs:")
        for x in probs:
            print(f"    - {x}")
    else:
        print("  ready: show the page and the animatic, then `gate.py approve storyboard --by <name> --quote \"…\"`")
    return 1 if (errs or probs) else 0


if __name__ == "__main__":
    sys.exit(main())
