#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""series_registry.py — create and check the `_series/<BRAND>/` documentation for a recurring series.

A per-video project folder answers "what did we make". A SERIES needs a layer above it that answers
"what may not change", "what has already run", and "which version of the rules was this episode made
under". Without the last one, editing the bible silently reclassifies every past episode as
non-compliant. See ../references/series-continuity.md.

  init   — scaffold `_series/<BRAND>/` with the six files, each carrying its own instructions
  check  — validate the registry and report drift risk

What `check` actually checks
----------------------------
  1. All six files exist and INVARIANTS.md declares `invariants-version: N`.
  2. Every EPISODES.md row parses and has every required cell filled.
  3. Episodes made under an older invariants version are listed as STALE (informational — they are
     dated, not wrong; the list tells you what a retroactive bible change would touch).
  4. Hook IDs reused across episodes are flagged (reuse is a decision, not an error).
  5. Ad-name join keys are checked for the five-part shape the metrics layer joins on.
  6. Show ids are checked for the canonical <brand>-<SS><EEE> shape, and dates for ISO. A legacy
     ID is a finding with a fix attached (put the old name in Aliases, use the canonical ID) — not a
     reason to rename anything that already shipped.

What it cannot do
-----------------
- **It cannot tell you an episode is on-model.** Nothing here looks at a frame. Identity, wardrobe
  and product drift are the QA card's job (../references/realism-qa.md V12/V13) and an eye check.
- It cannot know whether an INVARIANT should be one. That judgement is series-continuity.md section 5,
  and for a young series the honest default is to lock identity and compliance and leave the rest.
- It does not read the bible's prose. A beautifully written BIBLE.md that contradicts INVARIANTS.md
  passes every check here.

Exit codes: 0 clean - 1 findings - 2 usage/IO error.
"""
from __future__ import annotations
import argparse, json, os, re, sys

FILES = ["BIBLE.md", "INVARIANTS.md", "EPISODES.md", "DECISIONS.md", "HOOKS-USED.md"]
DIRS = ["_reference"]
VERSION_RE = re.compile(r"^invariants-version:\s*(\d+)\s*$", re.M)
COLS = ["ep", "date", "hook id", "persona", "invariants version", "ad-name join key"]
JOIN_KEY_PARTS = 5
# The canonical show id, per ETC/MovieLabs "VFX Image Sequence Naming" v1.0 episodic form:
# <brand>-<SS><EEE> — 2-digit season, 3-digit episode, lowercase. Fixed-width, so a parser is trivial,
# and — the load-bearing property — allocatable without coordination, which a flat counter is not.
# (The brand is 2-8 chars rather than the spec's 4: that cap is a legacy-system constraint, not ours.)
EPISODE_ID_RE = re.compile(r"^[a-z0-9]{2,8}-\d{5}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

TEMPLATES = {
    "BIBLE.md": """# <BRAND> — series bible

invariants-version: 1

## The world
<where this lives, who is in it, what the running situation is>

## The characters
<one block each: who they are, what they want, how they speak>

## PROHIBITIONS — the load-bearing half
A usable bible is mostly a list of things that must not happen: positive description does not
constrain a generator, a prohibition does, and it can be checked. Write them as plainly as the
Smokey Bear guidelines do (see ../../references/series-continuity.md section 1).

- <the character never ...>
- <we never show ...>
- <we never claim ...>
""",
    "INVARIANTS.md": """# <BRAND> — invariants

invariants-version: 1

**The layer we are holding, and why:** <cosmetic or substantive — see series-continuity.md section 4.
Low-involvement category: hold the message, vary the surface. High-involvement: hold the surface,
vary the argument.>

## INVARIANT — a change here is a DEFECT
- <identity: the locked character reference>
- <voice: the locked voice id>
- <the offer, and the approved claim wording>
- <delivery format>

## VARIANT — a change here is REQUIRED
Identical framing and duration across a batch is itself an AI tell (realism-qa.md V14).
- <framing distance and angle>
- <exact duration>
- <hook, persona, environment>

## Not yet classified
- <anything you have not decided about. Drift found in these is a decision to make, not a defect.>
""",
    "EPISODES.md": """# <BRAND> — episode registry

One row per episode, written WHEN IT SHIPS. The invariants version is the column that earns its keep.

`Ep` is the canonical show id: `<brand>-<SS><EEE>` (e.g. acme-01007 = brand acme, season 01,
episode 007) — the ETC/MovieLabs episodic form. Allocated here when the episode is PLANNED; never
changed afterwards; it is the prefix on every generated file for that episode. The HUMAN label
(`ACME S01E007`) is what goes in ClickUp and conversation; only the filename form is a key. `Aliases` carries the old folder or task name for episodes made before the scheme —
old folders are NOT renamed (see ../../references/pm-workflow.md, Naming convention).
Dates are ISO: YYYY-MM-DD.

| Ep | Date | Hook ID | Persona | Invariants version | Ad-name join key | Aliases | Notes / drift found |
|----|------|---------|---------|--------------------|------------------|---------|---------------------|
""",
    "DECISIONS.md": """# <BRAND> — decision records

Every T3 research call (preproduction-research.md section 2) and every drift ruling. Dated, with the
counter-case stated. A drift is resolved as either "promoted to VARIANT because ..." or "defect,
corrected in ep N".

| Date | Decision | Why | Counter-case | Touches |
|------|----------|-----|--------------|---------|
""",
    "HOOKS-USED.md": """# <BRAND> — hooks already run

| Hook ID | Text | First episode | Times run | Result |
|---------|------|---------------|-----------|--------|
""",
}


def die(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 2


def parse_table(text: str) -> tuple[list[str], list[dict]]:
    """First markdown table in the text -> (header cells lowercased, list of row dicts)."""
    rows, header = [], None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if header is not None and rows:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        rows.append(dict(zip(header, cells)))
    return header or [], rows


def init(root: str, brand: str) -> int:
    d = os.path.join(root, "_series", brand)
    os.makedirs(os.path.join(d, "_reference"), exist_ok=True)
    made = []
    for name, body in TEMPLATES.items():
        p = os.path.join(d, name)
        if os.path.exists(p):
            continue
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body.replace("<BRAND>", brand))
        made.append(name)
    print(f"{d}\n  created: {', '.join(made) if made else '(nothing — all files already present)'}")
    print("  next: fill INVARIANTS.md before the next episode, and register episodes when they SHIP")
    return 0


def check(d: str) -> dict:
    res: dict = {"dir": d, "findings": [], "stale": [], "episodes": 0}
    if not os.path.isdir(d):
        res["findings"].append(f"no such series folder: {d}")
        return res
    for f in FILES:
        if not os.path.exists(os.path.join(d, f)):
            res["findings"].append(f"MISSING FILE {f}")
    for sub in DIRS:
        if not os.path.isdir(os.path.join(d, sub)):
            res["findings"].append(f"MISSING FOLDER {sub}/ — the locked reference images live here")

    inv = os.path.join(d, "INVARIANTS.md")
    current = None
    if os.path.exists(inv):
        m = VERSION_RE.search(open(inv, encoding="utf-8").read())
        if not m:
            res["findings"].append("INVARIANTS.md declares no `invariants-version: N` line")
        else:
            current = int(m.group(1))
    res["invariants_version"] = current

    eps = os.path.join(d, "EPISODES.md")
    if not os.path.exists(eps):
        return res
    header, rows = parse_table(open(eps, encoding="utf-8").read())
    for c in COLS:
        if c not in header:
            res["findings"].append(f"EPISODES.md has no `{c}` column")
    res["episodes"] = len(rows)
    if not rows:
        res["findings"].append("EPISODES.md has no rows — register episodes WHEN THEY SHIP, "
                               "not when they are planned")

    seen_hooks: dict[str, str] = {}
    for r in rows:
        ep = r.get("ep", "?")
        for c in COLS:
            if c in header and not r.get(c):
                res["findings"].append(f"ep {ep}: empty `{c}`")
        v = r.get("invariants version", "")
        if v.isdigit() and current is not None and int(v) < current:
            res["stale"].append({"ep": ep, "made_under": int(v), "current": current})
        if ep and not EPISODE_ID_RE.match(ep):
            res["findings"].append(
                f"ep {ep!r} is not the canonical <brand>-<SS><EEE> show id (e.g. acme-01007). "
                "⛔ Do NOT rename the folder — put the old name in the Aliases column and use the "
                "canonical ID for everything new (pm-workflow.md, Naming convention)")
        d = r.get("date", "")
        if d and not ISO_DATE_RE.match(d):
            res["findings"].append(f"ep {ep}: date {d!r} is not ISO (YYYY-MM-DD)")
        key = r.get("ad-name join key", "")
        if key and len(key.split("-")) != JOIN_KEY_PARTS:
            res["findings"].append(f"ep {ep}: join key {key!r} is not the five-part "
                                   "<BRAND>-<body>-<hook>-<persona>-<variant> shape")
        h = r.get("hook id", "")
        if h:
            if h in seen_hooks:
                res["findings"].append(f"hook {h} reused: ep {seen_hooks[h]} and ep {ep} "
                                       "— reuse is a decision; record it in DECISIONS.md")
            seen_hooks[h] = ep
    return res


def selftest() -> int:
    h, rows = parse_table("| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n")
    assert h == ["a", "b"] and len(rows) == 2 and rows[1]["b"] == "4"
    assert parse_table("no table here") == ([], [])
    h2, r2 = parse_table("text\n\n| Ep | Date |\n|:--|--:|\n| 1 | x |\n\nafter\n")
    assert h2 == ["ep", "date"] and r2 == [{"ep": "1", "date": "x"}]
    assert VERSION_RE.search("stuff\ninvariants-version: 12\nmore").group(1) == "12"
    assert VERSION_RE.search("invariants-version:  3 ").group(1) == "3"
    assert VERSION_RE.search("no version") is None
    assert len("acme-b1-h4-p2-A".split("-")) == JOIN_KEY_PARTS
    assert EPISODE_ID_RE.match("acme-01007") and EPISODE_ID_RE.match("brandco-12099")
    for bad in ("ACME-S01E07", "acme-1007", "Proiect-Video-7", "acme-010070", "acme01007"):
        assert not EPISODE_ID_RE.match(bad), bad
    assert ISO_DATE_RE.match("2026-09-14") and not ISO_DATE_RE.match("14/09/2026")
    print("selftest OK — table parser, version parser, join-key shape, episode-ID and ISO-date lint")
    print("NOTE: proves the parsing, NOT that a registry describes a real series correctly.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init", help="scaffold _series/<BRAND>/")
    i.add_argument("--brand", required=True)
    i.add_argument("--root", default=".", help="where _series/ lives (default: cwd)")
    c = sub.add_parser("check", help="validate a series folder")
    c.add_argument("dir", help="path to _series/<BRAND>/")
    c.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "init":
        return init(a.root, a.brand)
    if a.cmd == "check":
        r = check(a.dir)
        if a.json:
            print(json.dumps(r, indent=2)); return 1 if r["findings"] else 0
        print(f"\n{r['dir']} — {r['episodes']} episode(s), invariants version "
              f"{r.get('invariants_version') if r.get('invariants_version') is not None else '?'}")
        for f in r["findings"]:
            print(f"  ! {f}")
        for s in r["stale"]:
            print(f"  · ep {s['ep']} made under invariants v{s['made_under']} (current v{s['current']})"
                  " — dated, not wrong")
        if not r["findings"]:
            print("  registry structurally clean")
        print("  (structure only — nothing here looked at a frame; the QA card still applies)")
        return 1 if r["findings"] else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
