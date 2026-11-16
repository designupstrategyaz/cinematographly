#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""qa_log.py — append an evidence line to 09-qa/QA-LOG.md. Refuses a verdict without an observation.

This is the mechanical half of the evidence-gated checkmark rule (realism-qa.md section 6): a pass
is not a box, it is an observation of what was actually seen or heard. A checkmark can be typed
without looking; a concrete descriptive sentence cannot — so this tool makes the sentence the only
way to log a verdict at all.

It rejects:
  * an empty or trivially short observation (< 4 words),
  * pure intention/prompt language with nothing observed ("looks good", "as prompted", "should be fine"),
  * a PASS on a dialogue/reaction clip whose observation mentions neither anything heard nor the
    listening A/B (lipsync is verified by LISTENING; a purely visual note on a dialogue clip is the
    contact-sheet mistake wearing new clothes).

Usage
-----
  python3 qa_log.py --project <dir> --shot S1-C1 --gate frame  --verdict PASS \\
      --obs "low sun from camera-left, long shadows on the stone, badge legible"
  python3 qa_log.py --project <dir> --shot S1-C1 --gate clip   --verdict PASS --kind dialogue \\
      --obs "A/B with VO at speed: every syllable articulated, /p/ in 'panouri' closes on the open frame"
  python3 qa_log.py --project <dir> --shot S2-C1 --gate selects --verdict RETAKE \\
      --obs "state transition missing — face stays pleasant throughout, card says skeptical->curious"
  python3 qa_log.py --project <dir> --tail 10        # read the last N entries

  python3 qa_log.py --project <dir> --gate master --verdict PASS \\
      --obs "watched 0:00-0:38 through: room tone holds under the 0:12 cut, heard \"factura\" clean
             over the music; the 0:24 join has a 1-frame flash on the incoming shot"

  # THE SOUND-OFF GATE (2026-10-27) — the client's check, "does it tell the story without sound and voiceover?"
  # (references/sound-off-story.md). A cold viewer's open answer first, then the beats:
  python3 qa_log.py --project <dir> --gate soundoff --test T2 --viewer cold --who "Ana" \\
      --proof 09-qa/soundoff/<name>.T2.mp4 --retell "<her words, before she sees the beat list>"
  python3 qa_log.py --project <dir> --gate soundoff --test T2 --viewer cold --who "Ana" \\
      --proof 09-qa/soundoff/<name>.T2.mp4 --verdict PASS --beats "HOOK@0:02,S2@0:11,CTA@0:24" \\
      --obs "named the bakery from the hands at 0:02 and read the price on the end card"

  # THE DRAFT GATE (v2.46) — the event sheet of a draft cut, read before anyone else sees the cut
  # (review-and-approval.md §2a): one RETAKE row per finding (it gets an id, D1, D2 …), a FIXED row per fix,
  # a PASS when a sheet reads clean. Every row cites the tiles it is about, by their ids on the sheet.
  python3 qa_log.py --project <dir> --gate draft --render 07-edit/_renders/x_cut_v003.mp4 \\
      --sheet 09-qa/contact-sheets/EVENTS-1a2b3c4d.png --verdict RETAKE --obs "T1 lands over her face at the C3 cut"
  python3 qa_log.py --project <dir> --gate draft --render <the NEW render> --sheet <its sheet> --verdict FIXED \\
      --fixes D1 --obs "T1 now sits in the lower third, clear of her face, on C3 and T1"
  python3 qa_log.py --project <dir> --gate draft --check --render <the render you are about to send>

Gates: frame · clip · selects · batch · master · soundoff · draft. Verdicts: PASS · RETAKE · SELECT · BACKUP (and
the cold viewer's RETELL at soundoff, and FIXED at draft).

THE DRAFT GATE (2026-11-02, v2.46; the owner's standing rule "always build a contact sheet and analyse it before
showing the clip", made mechanical). A draft row is logged against an EVENTS sheet that `contact_sheet.py events`
made OF THIS RENDER (its .json holds the render's sha256; another render's sheet is refused). A PASS cites at least
two tiles by id, a RETAKE or FIXED at least one. A FIXED row names its finding (--fixes Dn) and must cite a sheet
of a NEWER render than the one the finding was made on (a different hash and a later mtime): a fix nobody has
rendered is not a fix. A PASS is refused while a finding is open. The loop stops on a clean PASS or after the
third round (three renders read since the last PASS): the tool says so, and the cut goes to the director with the
open findings named. `--check --render R` says whether R has a draft PASS. Owner question Q4 is open (block or
warn?), so `--check` WARNS and exits 0; `--strict` exits 1. Rows: 09-qa/review/DRAFT-LOG.jsonl and QA-LOG.md.

⛔ THE SOUND-OFF GATE (2026-10-27, lab-00019). T1 is the muted feed (each delivery file, captions on), T2 the picture
alone (no sound, no voiceover, no caption of it). A row is logged against a PROOF that soundoff.py made, never
against a render, and it is refused when the proof or its source changed. A PASS cites at least three beats of
the story map, each with an m:ss inside that beat's window on the cut, the offer beat among them (house rule
K5). A cold viewer's PASS needs that viewer's RETELL logged first — the open question before the beat list
(Pechmann & Andrews 2010; ruling K3). The rows go to QA-LOG.md for people and 09-qa/soundoff/SOUNDOFF-LOG.jsonl
for the export gate (soundoff.py check).

⛔ THE MASTER GATE (2026-09-07). Every other gate in this skill inspects a CLIP or probes a FILE.
Nothing ever watched the FILM — so a flash frame at a join, a black frame, a caption colliding with
a cut, a music seam or an M&E hole was invisible to every check here, and all of it is what a client
notices in the first ten seconds. `gate.py approve export` now refuses without a master PASS.
A master observation must carry TWO DISTINCT TIMECODES: you cannot cite two positions in a cut you
did not play. One should be something HEARD and one something SEEN — the tool checks that there are
two and says plainly that it cannot check which is which.
Exit codes: 0 logged · 1 refused (evidence insufficient) · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, re, sys

INTENTION = re.compile(r"^\s*(looks?\s+(good|fine|ok(ay)?)|as\s+prompted|should\s+be\s+fine|"
                       r"seems?\s+(good|fine|ok)|all\s+good|ok|fine|good|approved|✅?)\s*[.!]?\s*$",
                       re.IGNORECASE)
# A PASS on a speaking clip must name a WORD THAT WAS HEARD, in quotes. The old test accepted any
# sentence containing "mouth" or "words" — which is verbatim the observation that let three bad
# lipsync clips through in the 2026-08-18 incident ("mouth open during VO, closed after"). Naming a
# quoted word cannot be done from a contact sheet; it requires playing the audio over the picture.
QUOTED = re.compile(r"[\"'“‘]([^\"'”’]{2,60})[\"'”’]")
# m:ss or mm:ss — a position in the cut. Deliberately not accepting a bare number of seconds:
# "at 12" is something you can write about a film you have not opened.
TIMECODE = re.compile(r"\b\d{1,2}:[0-5]\d\b")
# Phrases that describe the mouth MOVING rather than a word being UNDERSTOOD. Present without a
# quoted word, they are the window mistake again, so they are rejected by name.
WINDOW_ONLY = re.compile(r"\b(mouth|lips?)\b.{0,40}\b(mov|match|open|clos|sync)", re.IGNORECASE)


def infer_kind(project: str, shot: str | None) -> str | None:
    """Read the shot's kind from the manifest so the gate cannot be dodged by omitting --kind.

    Returns None when there is no manifest or no matching row — in which case the caller falls
    back to whatever --kind was given (possibly nothing). It never *weakens* an explicit --kind.
    """
    if not shot:
        return None
    import glob, json
    for p in glob.glob(os.path.join(project, "**", "SHOTS-*.json"), recursive=True):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        for row in (data.get("shots") or data.get("rows") or []):
            if str(row.get("shot") or row.get("id") or "").upper() == shot.upper():
                k = row.get("kind") or row.get("shot_type") or row.get("type")
                if k:
                    return str(k)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required="--selftest" not in sys.argv)
    ap.add_argument("--shot")
    ap.add_argument("--gate", choices=["frame", "clip", "selects", "batch", "master", "soundoff", "draft"])
    # ⛔ SELECT and BACKUP are the third state. `shot_manifest.py` has carried them since it was
    # written and nothing could ever WRITE one, because the only gate that records a verdict offered
    # PASS|RETAKE — including at `selects`, the directorial pass whose whole job is "are these the
    # right takes?". A two-valued vocabulary cannot express "usable, but there is a better one",
    # which is the sentence an editor lives in. They are accepted only at the selects gate: at a
    # fault gate the question really is binary.
    ap.add_argument("--verdict", choices=["PASS", "RETAKE", "SELECT", "BACKUP", "FIXED",
                                          "pass", "retake", "select", "backup", "fixed"])
    ap.add_argument("--kind", default=None,
                    help="dialogue/reaction/silent. Inferred from the shot manifest when omitted; "
                         "a speaking shot cannot be downgraded by leaving this off.")
    ap.add_argument("--line", default=None,
                    help="the scripted line for this shot. When given, the quoted word in --obs is "
                         "checked against it, so the evidence has to come from the actual take.")
    ap.add_argument("--obs", default=None, help="what you actually SAW or HEARD — the evidence")
    ap.add_argument("--test", default=None, help="soundoff: T1 (muted feed, as shipped) or T2 (the picture alone)")
    ap.add_argument("--viewer", default=None, help="soundoff: producer | cold | client")
    ap.add_argument("--who", default=None, help="soundoff: the cold viewer's name or initials")
    ap.add_argument("--proof", default=None, help="soundoff: the proof file watched (soundoff.py proofs)")
    ap.add_argument("--retell", default=None, help="soundoff: the cold viewer's own account, before the beat list")
    ap.add_argument("--beats", default=None, help='soundoff: "HOOK@0:02,S2@0:11,CTA@0:24" — beats the picture carried')
    ap.add_argument("--render", default=None, help="draft: the render the sheet was made of")
    ap.add_argument("--sheet", default=None, help="draft: the EVENTS sheet (contact_sheet.py events) of that render")
    ap.add_argument("--fixes", default=None, help="draft: the finding a FIXED row closes (D1, D2 …)")
    ap.add_argument("--check", action="store_true", help="draft: does --render have a draft PASS? (WARN-only, Q4)")
    ap.add_argument("--strict", action="store_true", help="draft --check: exit 1 when the PASS is owed")
    ap.add_argument("--tail", type=int, default=0, help="print the last N entries and exit")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    qdir = os.path.join(a.project, "09-qa")
    path = os.path.join(qdir, "QA-LOG.md")

    if a.tail:
        if not os.path.exists(path):
            print(f"(no log yet at {path})")
            return 0
        lines = [l for l in open(path, encoding="utf-8").read().splitlines() if l.startswith("| ")]
        for l in lines[-a.tail:]:
            print(l)
        return 0

    if a.gate in ("master", "soundoff") and not a.shot:
        a.shot = "FILM"          # the master gate's subject is the assembled cut, not a shot
    if a.gate == "soundoff":
        return log_soundoff(a, path)
    if a.gate == "draft":
        return draft_check(a.project, a.render, a.strict) if a.check else log_draft(a, path)
    if not (a.shot and a.gate and a.verdict):
        print("error: --shot, --gate and --verdict are required (or use --tail)", file=sys.stderr)
        return 2
    verdict = a.verdict.upper()
    if verdict == "FIXED":
        print("error: FIXED closes a draft finding (--gate draft --fixes Dn); at the other gates a fix is a new take "
              "with its own row", file=sys.stderr)
        return 2
    if verdict in ("SELECT", "BACKUP") and a.gate != "selects":
        print(f"error: {verdict} is a selects-gate verdict — it says which of several usable takes "
              f"goes in the cut. At the {a.gate} gate the question is whether this one is faulty: "
              f"PASS or RETAKE.", file=sys.stderr)
        return 2
    obs = (a.obs or "").strip()

    # --- the gate ---
    if len(obs.split()) < 4:
        print("REFUSED: the observation is the evidence, and this one is missing or too thin.\n"
              "  Write what you actually saw/heard, concretely — e.g.\n"
              "  \"low sun from camera-left, long shadows on stone, badge legible at phone size\"\n"
              "  A checkmark can be typed without looking; a descriptive sentence cannot.", file=sys.stderr)
        return 1
    if INTENTION.match(obs):
        print(f"REFUSED: {obs!r} is an intention, not an observation. Name what is IN the frames "
              f"or IN the audio.", file=sys.stderr)
        return 1
    if a.gate == "master":
        # Two distinct timecodes. A checkmark can be typed without looking and a plausible sentence
        # can be written from memory of the brief; two positions in the cut cannot. This is the same
        # move as the quoted word at the clip gate, applied to a whole film.
        marks = sorted({m.group(0) for m in TIMECODE.finditer(obs)})
        if len(marks) < 2:
            print("REFUSED: a master verdict must cite TWO DISTINCT TIMECODES — one for something "
                  "you HEARD and one for something you SAW — e.g.\n"
                  "  --obs 'room tone holds under the 0:12 cut; 1-frame flash on the incoming shot "
                  "at 0:24'\n"
                  "You cannot cite two positions in a cut you did not play. ⛔ The tool checks that "
                  "there are two; it CANNOT check that one is heard and one is seen, and it is not "
                  "pretending to.", file=sys.stderr)
            return 1
    kind = (a.kind or infer_kind(a.project, a.shot) or "").lower()
    if verdict == "PASS" and a.gate == "clip" and kind in ("dialogue", "reaction", "speaking"):
        m = QUOTED.search(obs)
        if not m:
            print("REFUSED: a speaking clip PASS must quote a WORD YOU HEARD, e.g.\n"
                  "  --obs 'heard \"panourile\" and \"factura\" cleanly, plosive on /p/ lands on the frame'\n"
                  "A quoted word cannot be produced from a contact sheet — it requires playing the\n"
                  "audio over the picture. (realism-qa.md §6; the 2026-08-18 lipsync incident.)",
                  file=sys.stderr)
            return 1
        if WINDOW_ONLY.search(obs) and len(m.group(1).split()) < 1:
            print("REFUSED: that describes the mouth MOVING, not a word UNDERSTOOD — the window "
                  "mistake that caused the incident this gate exists for.", file=sys.stderr)
            return 1
        if a.line:
            heard = m.group(1).lower()
            line = a.line.lower()
            if not any(w in line for w in heard.split() if len(w) > 2):
                print(f"REFUSED: the quoted words {m.group(1)!r} do not appear in the scripted line "
                      f"for this shot. Either you heard a different take than you think, or the "
                      f"model said something other than the script — both are RETAKE, not PASS.",
                      file=sys.stderr)
                return 1
        if kind != "reaction" and a.line is None:
            print("note: pass --line \"<the scripted line>\" and the quoted word is checked against "
                  "it, which is the difference between evidence and a plausible sentence.",
                  file=sys.stderr)

    os.makedirs(qdir, exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# QA log — one line per verdict, WITH its observation\n\n"
                     "The observation is the mechanism, not the checkmark (realism-qa.md §6).\n\n"
                     "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n")
        fh.write(f"| {dt.datetime.now().isoformat(timespec='minutes')} | {a.shot} | {a.gate} "
                 f"| {verdict} | {obs} |\n")
    print(f"logged: {a.shot} · {a.gate} · {verdict}")
    if verdict == "RETAKE":
        print("  next: the retake decision tree (ai-generation.md § Retake economics) — and the new "
              "attempt is a NEW manifest row with --retake-of set.")
    return 0


# ── the draft gate (v2.46) ─────────────────────────────────────────────────────────────────────────────────
DRAFT_ROUNDS = 3        # renders read in one loop before it stops and goes to the director (review-and-approval.md §2a)
DRAFT_MIN_IDS = {"PASS": 2, "RETAKE": 1, "FIXED": 1}


def _sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _draft_rows(project: str) -> list:
    p = os.path.join(project, "09-qa", "review", "DRAFT-LOG.jsonl")
    if not os.path.isfile(p):
        return []
    out = []
    for ln in open(p, encoding="utf-8"):
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def _open_findings(rows: list) -> list:
    fixed = {r.get("fixes") for r in rows if r.get("verdict") == "FIXED"}
    return [r for r in rows if r.get("verdict") == "RETAKE" and r.get("finding") not in fixed]


def _since_pass(rows: list) -> list:
    k = max((i for i, r in enumerate(rows) if r.get("verdict") == "PASS"), default=-1)
    return rows[k + 1:]


def _abs(project: str, p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(project, p)


def log_draft(a, path: str) -> int:
    """A draft row: refused unless it is about a sheet of THIS render, cites the tiles it read, and (for FIXED) a
    render newer than the finding's."""
    verdict = (a.verdict or "").upper()
    if verdict not in DRAFT_MIN_IDS or not a.render or not a.sheet:
        print("error: the draft gate needs --render, --sheet and --verdict PASS, RETAKE or FIXED (or --check --render)",
              file=sys.stderr)
        return 2
    render, sheet = _abs(a.project, a.render), _abs(a.project, a.sheet)
    side_p = os.path.splitext(sheet)[0] + ".json"
    if not os.path.isfile(render) or not os.path.isfile(sheet) or not os.path.isfile(side_p):
        print(f"REFUSED: the render, the sheet and the sheet's .json must all exist (contact_sheet.py events --project "
              f"{a.project} --cut {a.render} makes the sheet)", file=sys.stderr)
        return 1
    try:
        side = json.load(open(side_p, encoding="utf-8"))
    except ValueError:
        side = {}
    if side.get("tool") != "contact_sheet.py events":
        print("REFUSED: that is not an EVENTS sheet made by contact_sheet.py events", file=sys.stderr)
        return 1
    sha = _sha(render)
    if side.get("render_sha256") != sha:
        print(f"REFUSED: the sheet shows another render (sheet {str(side.get('render_sha256'))[:10]}, this render "
              f"{sha[:10]}). Make the sheet of the render you are judging.", file=sys.stderr)
        return 1
    obs = (a.obs or "").strip()
    if len(obs.split()) < 4 or INTENTION.match(obs):
        print("REFUSED: write what the tiles show, concretely, naming the tiles — \"T1 lands over her face at the C3 "
              "cut\", not \"looks good\"", file=sys.stderr)
        return 1
    ids = {str(e.get("id")) for e in side.get("events") or []} | {i for t in side.get("tiles") or [] for i in t.get("ids") or []}
    cited = sorted(i for i in ids if re.search(rf"(?<![\w~]){re.escape(i)}(?!\w)", obs))
    if len(cited) < DRAFT_MIN_IDS[verdict]:
        print(f"REFUSED: a draft {verdict} cites at least {DRAFT_MIN_IDS[verdict]} tile(s) of the sheet by id "
              f"({', '.join(sorted(ids)[:12])}…); this one cites {len(cited)}. Name the tiles you read.", file=sys.stderr)
        return 1
    rows = _draft_rows(a.project)
    rec = {"when": dt.datetime.now().isoformat(timespec="seconds"), "verdict": verdict, "render": a.render,
           "render_sha256": sha, "render_mtime": side.get("render_mtime"), "sheet": a.sheet, "sheet_sha256": _sha(sheet),
           "sheet_made": side.get("made"), "cites": cited, "obs": obs}
    if verdict == "RETAKE":
        rec["finding"] = f"D{1 + sum(1 for r in rows if r.get('verdict') == 'RETAKE')}"
    elif verdict == "FIXED":
        f = next((r for r in rows if r.get("verdict") == "RETAKE" and r.get("finding") == (a.fixes or "").upper()), None)
        if f is None:
            print(f"REFUSED: --fixes names the finding this row closes (open: "
                  f"{', '.join(r['finding'] for r in _open_findings(rows)) or 'none'})", file=sys.stderr)
            return 1
        if f not in _open_findings(rows):
            print(f"REFUSED: {f['finding']} is already fixed", file=sys.stderr)
            return 1
        if f.get("render_sha256") == sha:
            print(f"REFUSED: {f['finding']} was found on this same render. A fix nobody has rendered is not a fix: "
                  f"render the change, make its sheet, and cite that.", file=sys.stderr)
            return 1
        if float(side.get("render_mtime") or 0) <= float(f.get("render_mtime") or 0):
            print(f"REFUSED: this render is not newer than the one {f['finding']} was found on", file=sys.stderr)
            return 1
        rec["fixes"] = f["finding"]
    else:
        still = [r for r in _open_findings(rows)]
        if still:
            print(f"REFUSED: a clean pass has no open findings — {', '.join(r['finding'] for r in still)} "
                  f"still open. Log FIXED for each on this render's sheet first.", file=sys.stderr)
            return 1
    loop = _since_pass(rows) + [rec]
    rnd = len({r.get("render_sha256") for r in loop})
    rec["round"] = rnd
    rdir = os.path.join(a.project, "09-qa", "review")
    os.makedirs(rdir, exist_ok=True)
    with open(os.path.join(rdir, "DRAFT-LOG.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# QA log — one line per verdict, WITH its observation\n\n"
                     "The observation is the mechanism, not the checkmark (realism-qa.md §6).\n\n"
                     "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n")
        tag = rec.get("finding") or (f"fixes {rec['fixes']}" if rec.get("fixes") else "")
        # a draft finding is written FINDING, not RETAKE: ledger.py counts RETAKE rows as generation retakes
        col = "FINDING" if verdict == "RETAKE" else verdict
        fh.write(f"| {rec['when'][:16]} | FILM | draft | {col} | {(tag + ' · ') if tag else ''}round {rnd} · "
                 f"{a.render} ({sha[:10]}) · {os.path.basename(sheet)} — {obs.replace('|', '/')} |\n")
    print(f"logged: FILM · draft · {verdict}{' ' + rec['finding'] if rec.get('finding') else ''} · round {rnd} of "
          f"{DRAFT_ROUNDS}")
    if verdict != "PASS" and rnd >= DRAFT_ROUNDS:
        print(f"  round {rnd}: the loop's {DRAFT_ROUNDS} rounds are spent. Stop fixing alone — the cut goes to the "
              f"director with the open findings named ({', '.join(r['finding'] for r in _open_findings(rows + [rec])) or 'none'}).")
    return 0


def draft_check(project: str, render: str | None, strict: bool = False) -> int:
    """Has this render been read on its event sheet, and passed? WARN-only by default (house choice)."""
    if not render or not os.path.isfile(_abs(project, render)):
        print("error: --check needs --render <the render you are about to send>", file=sys.stderr)
        return 2
    sha = _sha(_abs(project, render))
    rows = _draft_rows(project)
    ok = next((r for r in reversed(rows) if r.get("verdict") == "PASS" and r.get("render_sha256") == sha), None)
    opn = _open_findings(rows)
    if ok:
        print(f"draft gate: PASS on this render ({sha[:10]}), read on {ok['sheet']} at {ok['when'][:16]}")
        return 0
    print(f"WARN draft gate: OWED — no draft PASS on {render} ({sha[:10]}). Make its sheet (contact_sheet.py events), "
          f"read it, log qa_log.py --gate draft (review-and-approval.md §2a)."
          + (f" Open findings: {', '.join(r['finding'] + ' (' + r['obs'][:60] + ')' for r in opn)}." if opn else ""))
    print("  (warn-only: whether this blocks a cut from going out is the owner's open question Q4)")
    return 1 if strict else 0


def log_soundoff(a, path: str) -> int:
    """The sound-off row: validated against the proof, the story map and the log (soundoff.validate_row)."""
    import soundoff as SO
    verdict = (a.verdict or ("RETELL" if a.retell is not None else "")).upper()
    if verdict != "RETELL":
        obs = (a.obs or "").strip()
        if len(obs.split()) < 4 or INTENTION.match(obs):
            print("REFUSED: --obs is what the viewer got from the picture, concretely — \"named the bakery from the "
                  "hands at 0:02, read the price on the end card\", not \"works\"", file=sys.stderr)
            return 1
    err, rec = SO.validate_row(a.project, a.test, a.viewer, a.who, a.proof, a.retell, a.beats, a.obs,
                               None if verdict == "RETELL" else verdict)
    if err:
        print("REFUSED: " + err, file=sys.stderr)
        return 1
    SO.append_log(a.project, rec)
    qdir = os.path.dirname(path)
    os.makedirs(qdir, exist_ok=True)
    new = not os.path.exists(path)
    body = rec.get("retell") if rec["verdict"] == "RETELL" else rec.get("obs")
    who = f"{rec['viewer']}" + (f" ({rec['who']})" if rec.get("who") else "")
    beats = f" · beats {', '.join(rec['beats'])}" if rec.get("beats") else ""
    with open(path, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# QA log — one line per verdict, WITH its observation\n\n"
                     "The observation is the mechanism, not the checkmark (realism-qa.md §6).\n\n"
                     "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n")
        fh.write(f"| {dt.datetime.now().isoformat(timespec='minutes')} | FILM | soundoff | {rec['verdict']} | "
                 f"{rec['test']} · {who} · {rec['proof']} ({rec['proof_sha256'][:10]}){beats} — "
                 f"{(body or '').replace('|', '/')} |\n")
    print(f"logged: FILM · soundoff · {rec['test']} · {rec['verdict']} · {who}")
    if rec["verdict"] == "RETELL":
        print("  next: now show the beat list, ask the closed questions, and log the PASS or RETAKE with --beats")
    return 0


def selftest() -> int:
    import subprocess, tempfile
    HERE_ = os.path.dirname(os.path.abspath(__file__))
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond or not info else f"  — {info.strip()[:300]}"))

    def run(args, proj):
        return subprocess.run([sys.executable, os.path.join(HERE_, "qa_log.py"),
                               "--project", proj] + args, capture_output=True, text=True)

    with tempfile.TemporaryDirectory() as td:
        # the master gate refuses a verdict with fewer than two timecodes
        r = run(["--gate", "master", "--verdict", "PASS",
                 "--obs", "watched it through and the whole thing plays cleanly end to end"], td)
        check("master with NO timecode is refused", r.returncode == 1 and "TWO DISTINCT" in r.stderr)
        r = run(["--gate", "master", "--verdict", "PASS",
                 "--obs", "room tone holds under the 0:12 cut and it all plays cleanly"], td)
        check("master with ONE timecode is refused", r.returncode == 1)
        r = run(["--gate", "master", "--verdict", "PASS",
                 "--obs", "the same 0:12 cut, again at 0:12, nothing else to report"], td)
        check("the same timecode twice is not two", r.returncode == 1)
        r = run(["--gate", "master", "--verdict", "PASS",
                 "--obs", 'room tone holds under the 0:12 cut, heard "factura" clean over the '
                          'music; 1-frame flash on the incoming shot at 0:24'], td)
        check("two distinct timecodes are logged", r.returncode == 0 and "master" in r.stdout)
        check("the master row names the FILM, not a shot",
              "| FILM |" in open(os.path.join(td, "09-qa", "QA-LOG.md"), encoding="utf-8").read())
        # a bare seconds count is not a position in a cut
        r = run(["--gate", "master", "--verdict", "PASS",
                 "--obs", "checked at 12 and again at 24, everything reads fine on the film"], td)
        check("bare seconds are not timecodes", r.returncode == 1)

        # the third state exists, and only where the question is not binary
        r = run(["--shot", "S1-C1", "--gate", "selects", "--verdict", "BACKUP",
                 "--obs", "usable — the glance lands, but take two holds the beat longer"], td)
        check("BACKUP is accepted at the selects gate", r.returncode == 0)
        r = run(["--shot", "S1-C1", "--gate", "clip", "--verdict", "SELECT",
                 "--obs", "usable — the glance lands, but take two holds the beat longer"], td)
        check("SELECT is refused at a fault gate", r.returncode == 2 and "selects-gate" in r.stderr)
        # and the existing evidence rules still hold
        r = run(["--shot", "S1-C1", "--gate", "frame", "--verdict", "PASS", "--obs", "looks good"], td)
        check("an intention is still refused", r.returncode == 1)
        # the sound-off gate logs only against a proof soundoff.py made (the end-to-end legs are soundoff.py's)
        r = run(["--gate", "soundoff", "--test", "T2", "--viewer", "cold", "--who", "Ana",
                 "--proof", "09-qa/soundoff/x.T2.mp4", "--verdict", "PASS", "--beats", "HOOK@0:01",
                 "--obs", "she named the bakery and read the price on the end card"], td)
        check("soundoff: a verdict about a file that is not a proof is refused",
              r.returncode == 1 and "not a proof made by soundoff.py" in r.stderr)
        r = run(["--gate", "soundoff", "--test", "T2", "--viewer", "cold", "--verdict", "PASS", "--obs", "works"], td)
        check("soundoff: a one-word observation is refused before anything else", r.returncode == 1)

    # the draft gate (v2.46): rows about an EVENTS sheet of THIS render; a fix needs a newer render's sheet
    with tempfile.TemporaryDirectory() as td:
        rd, sd = os.path.join(td, "07-edit", "_renders"), os.path.join(td, "09-qa", "contact-sheets")
        os.makedirs(rd); os.makedirs(sd)

        def render(n, body):
            p = os.path.join(rd, f"x_cut_v00{n}.mp4")
            open(p, "wb").write(body)
            os.utime(p, (1_700_000_000 + n * 100, 1_700_000_000 + n * 100))
            return os.path.relpath(p, td)

        def sheet(rel, name):
            p = os.path.join(td, rel)
            open(os.path.join(sd, name + ".png"), "wb").write(b"\x89PNG")
            json.dump({"tool": "contact_sheet.py events", "render": rel, "render_sha256": _sha(p),
                       "render_mtime": os.path.getmtime(p), "made": "2026-11-02T23:00:00",
                       "events": [{"id": i} for i in ("POSTER", "C1", "C2", "C3", "T1", "BUTTON", "END")],
                       "tiles": []}, open(os.path.join(sd, name + ".json"), "w"))
            return os.path.join("09-qa", "contact-sheets", name + ".png")

        v1, v2 = render(1, b"cut one"), render(2, b"cut two")
        s1, s2 = sheet(v1, "EVENTS-v1"), sheet(v2, "EVENTS-v2")
        D = lambda *x: run(["--gate", "draft"] + list(x), td)
        r = D("--render", v2, "--sheet", s1, "--verdict", "PASS", "--obs", "C1 settles and T1 lands clear of the face")
        check("draft: a sheet of another render is refused", r.returncode == 1 and "another render" in r.stderr)
        r = D("--render", v1, "--sheet", s1, "--verdict", "PASS", "--obs", "every cut settles and the title lands clear")
        check("draft: a PASS that names no tile is refused", r.returncode == 1 and "cites at least 2" in r.stderr)
        r = D("--render", v1, "--sheet", s1, "--verdict", "RETAKE", "--obs", "T1 lands over her face at the C3 cut")
        check("draft: a RETAKE naming its tiles is logged as finding D1",
              r.returncode == 0 and "RETAKE D1" in r.stdout and "round 1" in r.stdout, r.stdout + r.stderr)
        r = D("--render", v1, "--sheet", s1, "--verdict", "PASS", "--obs", "C1 settles and BUTTON holds to END")
        check("draft: a PASS while D1 is open is refused", r.returncode == 1 and "D1" in r.stderr)
        r = D("--render", v1, "--sheet", s1, "--verdict", "FIXED", "--fixes", "D1", "--obs", "T1 now clear of her face on C3")
        check("draft: a FIXED cited on the finding's own render is refused (nothing was rendered)",
              r.returncode == 1 and "not a fix" in r.stderr)
        r = D("--render", v2, "--sheet", s2, "--verdict", "FIXED", "--fixes", "D1", "--obs", "T1 now clear of her face on C3")
        check("draft: a FIXED on a newer render's sheet closes D1", r.returncode == 0 and "round 2" in r.stdout, r.stdout + r.stderr)
        r = D("--check", "--render", v2)
        check("draft --check: a render with no PASS is OWED, and warns only (Q4 open)", r.returncode == 0 and "OWED" in r.stdout)
        check("draft --check --strict exits 1 on the same", D("--check", "--strict", "--render", v2).returncode == 1)
        r = D("--render", v2, "--sheet", s2, "--verdict", "PASS", "--obs", "C1 settles, T1 lands clear and BUTTON holds to END")
        check("draft: a clean PASS on the fixed render is logged", r.returncode == 0, r.stdout + r.stderr)
        r = D("--check", "--render", v2)
        check("draft --check: the PASS is found by the render's hash", r.returncode == 0 and "PASS on this render" in r.stdout)
        v3 = render(3, b"cut three")
        s3 = sheet(v3, "EVENTS-v3")
        D("--render", v3, "--sheet", s3, "--verdict", "RETAKE", "--obs", "C2 has a flash frame on the incoming shot")
        v4 = render(4, b"cut four"); s4 = sheet(v4, "EVENTS-v4")
        D("--render", v4, "--sheet", s4, "--verdict", "RETAKE", "--obs", "C3 still jumps where the insert ends")
        v5 = render(5, b"cut five"); s5 = sheet(v5, "EVENTS-v5")
        r = D("--render", v5, "--sheet", s5, "--verdict", "RETAKE", "--obs", "END card cuts off before the BUTTON hit")
        check("draft: the third render since the last PASS says the loop's rounds are spent",
              r.returncode == 0 and "round 3" in r.stdout and "rounds are spent" in r.stdout, r.stdout)
        r = run(["--shot", "S1", "--gate", "clip", "--verdict", "FIXED", "--obs", "the hand now holds the cup steady"], td)
        check("FIXED is a draft verdict only", r.returncode == 2)
        log = open(os.path.join(td, "09-qa", "QA-LOG.md"), encoding="utf-8").read()
        check("draft findings are written FINDING in QA-LOG.md, so ledger.py's retake count stays about takes",
              "| draft | FINDING | D1 ·" in log and "| draft | RETAKE |" not in log, log[-400:])

    print("-" * 60)
    print("selftest OK — the master gate needs two DISTINCT timecodes and logs against FILM; a bare "
          "seconds count is not one; SELECT/BACKUP exist at the selects gate and nowhere else; the draft gate "
          "logs only against an EVENTS sheet of the same render, cites tiles, numbers findings, refuses a FIXED "
          "without a newer render and a PASS with open findings, counts rounds, and --check warns (Q4)"
          if ok else "selftest FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
