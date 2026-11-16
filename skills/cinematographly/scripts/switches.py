#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""switches.py — project switches: a house rule stays the default, and one job turns it off, with a reason.

  switches.py list                    the registry: every switch, what it lifts, what still holds, and for a
                                      finishing look when and where it goes and the doc section that says so
  switches.py show <job>              the switches this job's CHECKPOINT turns on, and their reasons
  switches.py check <job>             validate the job's `Switches:` line (exit 1 on a problem)
  switches.py --selftest

WHY (2026-11-03: "I think such choices are project based?")
Course after course proposed loosening a house rule: cut the b-roll to the song, grain in the ads
grade, a blur-in title, a 2160p upload. Each is wrong as a default and right for some job. So the rule
stays, and a job may lift it — by name, in writing, where the gate reads it:

  Switches:   music-led — the song is the deliverable; speed-conform — lip-sync shot at 30 fps, conformed

in `00-brief/CHECKPOINT.md`. `none` (or no line at all, for a job opened before 2.48) means every
house rule holds. Each item is `<id> — <reason>`, items separated by `;`. The id must be in
`assets/project-switches.json`; the reason must say why, in at least three words. A script that
enforces a lifted rule names it as lifted, with the reason, instead of refusing — the lift is visible
in every report, never silent.

⛔ WHAT NEVER SWITCHES
The registry's `locked` list: no roto or advanced VFX, no AI images as references, no spend without
approval, native Resolve titles, English, a contact sheet before any draft, never picking music,
Higgsfield motion_control (M3). Writing one of those as a switch is refused with the rule it would break.

HONEST LIMITS
A switch lifts exactly what its registry entry says, in the scripts that entry names; where a lifted
rule lives only in a reference (no script enforces it), the switch is the written permission and the
person doing the work honours it. Nothing here checks that the reason is TRUE — only that there is one.
"""
from __future__ import annotations
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REGISTRY_PATH = os.path.join(SKILL, "assets", "project-switches.json")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z ]{1,20}):\s*(.*)$")
PLACEHOLDER_RE = re.compile(r"<[^<>\n]{1,80}>|NEEDS INPUT|TBD\b|\?\?\?", re.I)
ITEM_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s+[—–-]\s+(.+?)\s*$")
FINISH_LOOKS = ("finish-texture", "light-leak", "blur-titles", "blurred-fill")   # carry when / where / guide (v2.48.0)


def registry(path: str = REGISTRY_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _field(text: str, key: str = "switches") -> str | None:
    """The `Switches:` value (continuation lines indented), as gate.py's parse_kv reads it."""
    cur, val = None, None
    for line in text.splitlines():
        if line.startswith(("```", "#", ">")):
            cur = None
            continue
        m = KEY_RE.match(line)
        if m:
            cur = m.group(1).strip().lower()
            if cur == key and val is None:
                val = m.group(2).strip()
            elif cur == key:
                cur = None
        elif cur == key and line.startswith((" ", "\t")) and line.strip():
            val = (val + " " + line.strip()).strip()
        else:
            cur = None
    return val


def parse(value: str | None, reg: dict | None = None) -> tuple[dict, list[str]]:
    """`Switches:` value → ({id: reason}, problems). None / '' / 'none' → ({}, [])."""
    reg = reg or registry()
    known = reg.get("switches", {})
    if value is None or not value.strip() or value.strip().lower() == "none":
        return {}, []
    on, problems = {}, []
    for raw in [p for p in value.split(";") if p.strip()]:
        m = ITEM_RE.match(raw)
        if not m:
            problems.append(f"`Switches:` item {raw.strip()!r} needs the form `<id> — <reason>`")
            continue
        sid, why = m.group(1).lower(), m.group(2).strip()
        locked = next((l for l in reg.get("locked", []) if re.search(l["match"], sid, re.I)), None)
        if locked and sid not in known:
            problems.append(f"`Switches:` {sid!r} is never a switch — {locked['rule']}")
            continue
        if sid not in known:
            problems.append(f"`Switches:` {sid!r} is not a switch in assets/project-switches.json "
                            f"(known: {', '.join(sorted(known))})")
            continue
        if PLACEHOLDER_RE.search(why) or len(re.findall(r"[A-Za-z0-9%]+", why)) < 3:
            problems.append(f"`Switches:` {sid} needs a reason of at least three words, not {why!r}")
            continue
        if sid in on:
            problems.append(f"`Switches:` {sid} is listed twice")
            continue
        on[sid] = why
    return on, problems


def checkpoint_path(job: str) -> str:
    return os.path.join(os.path.abspath(job), "00-brief", "CHECKPOINT.md")


def for_job(job: str | None, reg: dict | None = None) -> dict:
    """The job's valid switches ({id: reason}). No job, no CHECKPOINT or no line → {}. An invalid item
    is dropped here (gate.py open refuses it), so a typo never lifts a rule."""
    if not job:
        return {}
    p = checkpoint_path(job)
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        on, _ = parse(_field(fh.read()), reg)
    return on


def on(job: str | None, sid: str) -> str | None:
    """The reason this job lifts `sid`, or None when the house rule holds."""
    return for_job(job).get(sid)


def lifted(sid: str, reason: str) -> str:
    """The one wording every script uses when it honours a switch."""
    return f"lifted by project switch `{sid}` ({reason})"


def validate_job(job: str) -> list[str]:
    p = checkpoint_path(job)
    if not os.path.isfile(p):
        return [f"no {p}"]
    with open(p, encoding="utf-8") as fh:
        _, problems = parse(_field(fh.read()))
    return problems


# ---------------------------------------------------------------------------------------------- selftest
def selftest() -> bool:
    import tempfile
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("  [PASS] " if cond else "  [FAIL] ") + name + ("" if cond else f"  {detail}"))
        ok &= bool(cond)

    reg = registry()
    check("the registry loads, every switch names what it lifts and its rows",
          all(v.get("lifts") and v.get("rows") for v in reg["switches"].values()), reg["switches"].keys())
    # (v2.48.0, 2026-11-03: "The skill should know when and where to apply them.") The four finishing-look
    # switches carry their guidance: when, where, and the doc section (references/editing-and-audio.md § Finishing looks)
    gaps = {s: [k for k in ("when", "where", "guide") if not reg["switches"].get(s, {}).get(k)] for s in FINISH_LOOKS}
    check("the four finishing-look switches carry when, where and guide", not any(gaps.values()),
          {s: g for s, g in gaps.items() if g})
    check("none / empty / no line → nothing lifted", parse("none", reg) == ({}, []) and parse(None, reg) == ({}, [])
          and parse("  ", reg) == ({}, []))
    s, p = parse("music-led — the song is the deliverable; speed-conform – lip-sync shot at 30 fps", reg)
    check("two switches with reasons → both on, em or en dash", p == [] and set(s) == {"music-led", "speed-conform"}, (s, p))
    s, p = parse("music-led", reg)
    check("a switch with no reason is refused", s == {} and p and "<id> — <reason>" in p[0], p)
    s, p = parse("music-led — because", reg)
    check("a one-word reason is refused", s == {} and p and "three words" in p[0], p)
    s, p = parse("music-led — <why this job>", reg)
    check("a placeholder reason is refused", s == {} and p, p)
    s, p = parse("grain-everywhere — the client loves film grain", reg)
    check("an unknown switch is refused and the known ones listed", s == {} and p and "known:" in p[0], p)
    s, p = parse("mask-wipe — the dancer reveals the next shot", reg)
    check("a locked rule (roto / mask wipe) is refused with the rule it breaks",
          s == {} and p and "never a switch" in p[0] and "roto" in p[0], p)
    s, p = parse("motion-control — copy the dance", reg)
    check("M3 stays denied", s == {} and p and "M3" in p[0], p)
    s, p = parse("finish-texture — film look agreed with the client; finish-texture — again for the record", reg)
    check("a switch listed twice is named", "finish-texture" in s and any("twice" in x for x in p), (s, p))
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "00-brief"))
        cp = os.path.join(d, "00-brief", "CHECKPOINT.md")
        check("a job with no CHECKPOINT lifts nothing", for_job(d) == {} and on(d, "music-led") is None)
        open(cp, "w").write("Job:        x-1\nSkips:      none\nBudget:     envelope 0 cr [assumed]\n")
        check("a CHECKPOINT with no Switches line (opened before 2.48) lifts nothing", for_job(d) == {})
        open(cp, "w").write("Job:        x-1\nSwitches:   blur-titles — the brand's own motion system uses it;\n"
                            "            upload-master — the platform re-encodes 1080 uploads badly\nSkips:      none\n")
        got = for_job(d)
        check("a continued Switches line is read whole", set(got) == {"blur-titles", "upload-master"}, got)
        check("on() gives the reason; lifted() words it",
              on(d, "blur-titles") == "the brand's own motion system uses it"
              and lifted("blur-titles", "x y z") == "lifted by project switch `blur-titles` (x y z)")
        open(cp, "w").write("Switches:   blur-titles — ok; light-leak — one hit on the launch cut\n")
        check("an invalid item is dropped, a valid one still lifts", set(for_job(d)) == {"light-leak"}
              and validate_job(d), (for_job(d), validate_job(d)))
    print("selftest", "OK — the registry, the finishing-look guidance, the line's form, reasons, unknown and locked ids, "
          "continuation lines, jobs opened before 2.48" if ok else "FAILED")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["list", "show", "check"])
    ap.add_argument("job", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return 0 if selftest() else 1
    if a.cmd == "list":
        reg = registry()
        for sid, v in reg["switches"].items():
            print(f"{sid:22s} lifts: {v['lifts']}\n{'':22s} still holds: {v.get('still_holds', '')}  ({', '.join(v['rows'])})")
            for k in ("when", "where", "guide"):      # (v2.48.0) a finishing look's guidance, when the entry has it
                if v.get(k):
                    print(f"{'':22s} {k}: {v[k]}")
        print("\nnever a switch: " + "; ".join(l["name"] for l in reg["locked"]))
        return 0
    if a.cmd in ("show", "check") and a.job:
        problems = validate_job(a.job)
        for sid, why in for_job(a.job).items():
            print(f"ON   {sid:22s} {why}")
        for p in problems:
            print(f"FAIL {p}")
        if not for_job(a.job) and not problems:
            print("no project switches — every house rule holds")
        return 1 if (a.cmd == "check" and problems) else 0
    ap.print_usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())
