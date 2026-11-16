#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""sheet_split.py — cut an approved three-panel sheet into separate, role-labelled images (v2.70.0, Wave 5 A9).

The house sheet (`references/character-and-props.md` §8.3b) is one file: full-body FRONT, full-body BACK and a
close-up HEADSHOT side by side on grey, with thin dark dividers; the body panels are headless, the headshot carries
the only face. Some models are said to hold identity better from separate images — a close face plus a body image —
than from a multi-panel sheet (research note R4; not measured here). This tool makes the separate images from the
sheet the person already approved, so that question can be tested (Wave 5 B3) by changing the prompt's references
only. It changes no call by itself: today's prompts keep the single sheet.

  sheet_split.py split <sheet.png> [--out DIR] [--panels 3] [--names front,back,head]
                         writes <stem>.<name>.png per panel and a provenance sidecar for each, copied from the
                         sheet's own sidecar with `derived_from` (the lint refuses a reference without one)
  sheet_split.py --selftest

How the panels are found: columns whose median brightness is far below the sheet's grey (the dark dividers); if
fewer dividers than panels − 1 are found, equal widths are used and the run says so. Each panel is trimmed of the
divider. Nothing is resized or retouched.

Use the pieces as separate references, one attribute each (prompt_lint.py's rule): the headshot as
`what: character`, the front and back as `what: wardrobe`. The slot cap per model is still the lint's.
Exit codes: 0 ok · 1 refusal (no sidecar, unreadable) · 2 usage.
"""
from __future__ import annotations
import argparse, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEFAULT_NAMES = ("front", "back", "head")     # the house order, left to right (character-and-props.md §8.3b)


def _image():
    try:
        from PIL import Image
        return Image
    except ImportError:
        raise SystemExit("sheet_split.py needs Pillow (pip install pillow)")


def find_dividers(gray, panels: int) -> list:
    """Column ranges [(x0, x1)] of the dark dividers, left to right. `gray` is a 2-D list or array of 0-255 values."""
    import statistics
    w = len(gray[0])
    cols = [statistics.median(row[x] for row in gray) for x in range(w)]
    base = statistics.median(cols)
    dark = [c < base * 0.45 for c in cols]
    runs, x = [], 0
    while x < w:
        if dark[x]:
            x0 = x
            while x < w and dark[x]:
                x += 1
            if 0 < x0 and x < w and (x - x0) <= max(2, w // 40):      # a thin line inside the sheet, not an edge
                runs.append((x0, x))
        else:
            x += 1
    if len(runs) > panels - 1:                     # keep the ones nearest the equal-width cut lines
        want = [w * k / panels for k in range(1, panels)]
        runs = sorted(sorted(runs, key=lambda r: min(abs((r[0] + r[1]) / 2 - t) for t in want))[: panels - 1])
    return runs


def split(sheet: str, out: str | None = None, panels: int = 3, names=DEFAULT_NAMES) -> dict:
    import provenance as PV
    side = PV.find_sidecar(sheet)
    if not side:
        raise SystemExit(f"REFUSED: {sheet} has no provenance sidecar — the pieces would have none either, and the lint "
                         f"refuses a reference without one (`provenance.py record {sheet} --source …`)")
    if len(names) != panels:
        raise SystemExit(f"--names gives {len(names)} names for {panels} panels")
    Image = _image()
    im = Image.open(sheet).convert("RGB")
    w, h = im.size
    g = im.convert("L")
    px = g.load()
    step = max(1, h // 200)
    gray = [[px[x, y] for x in range(w)] for y in range(0, h, step)]
    runs = find_dividers(gray, panels)
    equal = len(runs) != panels - 1
    if equal:
        cuts = [(round(w * k / panels), round(w * (k + 1) / panels)) for k in range(panels)]
    else:
        edges = [0] + [v for r in runs for v in r] + [w]
        cuts = [(edges[2 * k], edges[2 * k + 1]) for k in range(panels)]
    out = out or os.path.dirname(os.path.abspath(sheet))
    os.makedirs(out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(sheet))[0]
    rec = json.load(open(side, encoding="utf-8"))
    files = []
    for name, (x0, x1) in zip(names, cuts):
        p = os.path.join(out, f"{stem}.{name}.png")
        im.crop((x0, 0, x1, h)).save(p)
        r2 = dict(rec)
        # a derived file gets its OWN hash and size, pointing at the parent: a copied hash makes the lint treat the panel
        # as changed since its record was written (build review 1, Grok)
        r2.update(file=os.path.basename(p), sha256=PV.sha256_file(p), bytes=os.path.getsize(p))
        r2["derived_from"] = os.path.basename(sheet)
        r2["derived_from_sha256"] = rec.get("sha256")
        r2["derived_how"] = f"sheet_split.py: panel '{name}' (x {x0}–{x1} of {w})"
        with open(PV.sidecar_path(p), "w", encoding="utf-8") as fh:
            json.dump(r2, fh, indent=1, ensure_ascii=False)
        files.append({"panel": name, "file": p, "x": [x0, x1]})
    return {"sheet": sheet, "panels": files, "found_dividers": not equal,
            "note": "equal widths: the dividers were not found, check the cuts" if equal else ""}


def selftest() -> int:
    Image = _image()
    import provenance as PV
    with tempfile.TemporaryDirectory() as td:
        # a grey sheet with two thin dark dividers at 300 and 601 px, three different panel tones
        im = Image.new("RGB", (900, 400), (128, 128, 128))
        for x0, x1, tone in ((0, 300, 120), (303, 601, 140), (604, 900, 160)):
            im.paste((tone, tone, tone), (x0, 0, x1, 400))
        for x in (300, 301, 302, 601, 602, 603):
            im.paste((20, 20, 20), (x, 0, x + 1, 400))
        sp = os.path.join(td, "Ana_sheet.png")
        im.save(sp)
        try:
            split(sp)
            raise AssertionError("a sheet with no sidecar must be refused")
        except SystemExit as e:
            assert "no provenance sidecar" in str(e), e
        json.dump({"source": "ai-generated", "clearance": "CLEARED"}, open(PV.sidecar_path(sp), "w"))
        r = split(sp, os.path.join(td, "out"))
        assert r["found_dividers"] and [p["panel"] for p in r["panels"]] == ["front", "back", "head"], r
        assert [p["x"] for p in r["panels"]] == [[0, 300], [303, 601], [604, 900]], r
        head = Image.open(r["panels"][2]["file"])
        assert head.size == (296, 400) and head.getpixel((10, 10)) == (160, 160, 160), head.getpixel((10, 10))
        s2 = json.load(open(PV.sidecar_path(r["panels"][2]["file"])))
        assert s2["source"] == "ai-generated" and s2["derived_from"] == "Ana_sheet.png", s2
        assert s2["sha256"] == PV.sha256_file(r["panels"][2]["file"]) and s2["bytes"] == os.path.getsize(r["panels"][2]["file"]) \
            and s2["file"] == "Ana_sheet.head.png", s2      # its own hash: the lint's changed-since check passes
        # no dividers: equal widths, and it says so
        im2 = Image.new("RGB", (900, 300), (128, 128, 128))
        sp2 = os.path.join(td, "plain.png"); im2.save(sp2)
        json.dump({"source": "ai-generated"}, open(PV.sidecar_path(sp2), "w"))
        r2 = split(sp2, os.path.join(td, "out2"))
        assert not r2["found_dividers"] and "equal widths" in r2["note"] and r2["panels"][1]["x"] == [300, 600], r2
    print("selftest OK — a sheet is cut at its thin dark dividers into front, back and head, each with the sheet's "
          "provenance and where it came from; no sidecar is refused; no dividers falls back to equal widths and says so")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("split")
    s.add_argument("sheet"); s.add_argument("--out"); s.add_argument("--panels", type=int, default=3)
    s.add_argument("--names", default=",".join(DEFAULT_NAMES))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd != "split":
        ap.print_help(); return 2
    r = split(a.sheet, a.out, a.panels, tuple(x.strip() for x in a.names.split(",")))
    print(json.dumps(r, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
