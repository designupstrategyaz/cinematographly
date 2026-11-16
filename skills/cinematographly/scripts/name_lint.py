#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""name_lint.py — check a filename against the published VFX naming grammar, and say WHICH field is wrong.

The grammar is ETC / MovieLabs *VFX Image Sequence Naming* v1.0, with three deliberate deviations
documented in ../references/pm-workflow.md (readable model token, 2-8 char brand, no frame/camera
fields):

    <showid>_<seq>_<shot>_<type>_<subject>_<model>_v<NNN>[_<alt>][_<suffix>].<ext>
    acme-01007_s1_0020_clip_host_seedance_v002.mp4

Audio deliverables carry no shot (they have all of them) and add a channel layout and a rate:

    <showid>_<type>_v<NNN>[_<layout>][_<rate>].wav
    acme-01007_mne_v001_20_48k24.wav          the undipped M&E
    acme-01007_stem-m_v001_20_48k24.wav       the music stem

Why a linter and not a renamer: a naming scheme fails silently. One file named wrong is nothing; a
hundred is a folder you cannot sort, and by then renaming breaks manifest paths, cost records and
board links. So this catches the FIRST one and never touches the disk.

  lint     — walk a file or folder, report every name that does not parse
  explain  — parse ONE name and print the fields, or the exact reason it failed
  insert   — the shot number to use between two existing shots (the increments-of-10 rule)

What it cannot do
-----------------
- **It never renames anything, by design.** ⛔ Renaming a shipped asset breaks every path that points
  at it; legacy names are reported with the fix (record the alias, use the canonical ID for new work),
  not corrected. See pm-workflow.md, Naming convention.
- It cannot tell you a name is TRUE — that `_host_` is really the host, or that `v002` really is the
  second generation. That is the shot manifest's job (shot_manifest.py), and this tool does not read it.
- It does not know your brand's token vocabulary. `_smurf_` parses fine as a subject; whether that is
  a real subject for this client is the profile's business.

Usage
-----
  python3 name_lint.py lint 03-clips/
  python3 name_lint.py lint <project-dir> --json
  python3 name_lint.py explain acme-01007_s1_0020_clip_host_seedance_v002.mp4
  python3 name_lint.py insert 0010 0020

Exit codes: 0 clean · 1 findings · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, json, os, re, sys, unicodedata

SHOW_RE = re.compile(r"^[a-z0-9]{2,8}-\d{5}$")      # <brand>-<SS><EEE>, ETC episodic show id
SEQ_RE = re.compile(r"^[a-z][a-z0-9]{1,3}$")        # hk, s1..s4, ct — ETC: 2-4 alphanumeric
SHOT_RE = re.compile(r"^\d{4}$")                    # 0010, 0020 — allocated in TENS
TYPE_RE = re.compile(r"^(frame|clip|broll|vo|sfx|mus|master|mix|mne|stem-[dme])(\d{2})?$")
# Deliverables have no shot because they have all of them (editing-and-audio.md, the delivery layer).
DELIVERABLE = {"master", "mix", "mne", "stem-d", "stem-m", "stem-e"}
DESC_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REV_RE = re.compile(r"^v\d{3}$")
ALT_RE = re.compile(r"^\d{1,2}x\d{1,2}$")
LAYOUT_RE = re.compile(r"^(10|20|51|71)$")        # channel layout on an audio deliverable
RATE_RE = re.compile(r"^\d{2}k\d{2}$")            # sample rate + bit depth, e.g. 48k24
SUFFIXES = {"noaudio", "looped"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".mp4", ".mov", ".wav", ".mp3", ".m4a", ".webm", ".aif", ".aiff"}
LEGACY = [
    (re.compile(r"^Proiect-Video-\d+", re.I), "the pre-2026-08-30 project-counter scheme"),
    (re.compile(r"^[A-Z]{2,8}-S\d{2}E\d{2}_"), "the short-lived ACME-S01E07_ shape (2026-08-30, same day)"),
    (re.compile(r"^S\d+-C\d+_"), "the shot-only scheme — collides across episodes in a batch"),
]


def parse(name: str) -> dict:
    """Return {'ok': True, fields...} or {'ok': False, 'error': <precise reason>}."""
    base, ext = os.path.splitext(name)
    def bad(msg): return {"ok": False, "error": msg}

    if not ext:
        return bad("no file extension")
    for rx, what in LEGACY:
        if rx.match(name):
            return bad(f"LEGACY name — {what}. ⛔ Do NOT rename it: record the old name in the "
                       f"registry's Aliases column and use the canonical ID for new work")
    if any(unicodedata.category(c) == "Zs" or c == " " for c in name):
        return bad("contains whitespace — the spec forbids it; use a dash")
    if not name.isascii():
        nonascii = "".join(sorted({c for c in name if not c.isascii()}))
        return bad(f"contains non-ASCII ({nonascii!r}) — diacritics belong in the script and the "
                   f"burnt-in captions, not in a path: they break tool round-trips silently")
    if name != name.lower():
        return bad("contains uppercase — the spec prefers lowercase, and macOS/Linux disagree about "
                   "whether the host.png and host.png are one file or two")

    parts = base.split("_")
    if len(parts) < 3:
        return bad("too few fields — expected at least <showid>_<type>_v<NNN>")
    out: dict = {"ok": True, "ext": ext.lstrip(".")}

    if not SHOW_RE.match(parts[0]):
        return bad(f"show id {parts[0]!r} is not <brand>-<SS><EEE> (2-8 lowercase brand chars, "
                   f"2-digit season, 3-digit episode) — e.g. acme-01007")
    out["show"] = parts[0]
    i = 1

    if i + 1 < len(parts) and SEQ_RE.match(parts[i]) and SHOT_RE.match(parts[i + 1]):
        out["seq"], out["shot"] = parts[i], parts[i + 1]
        i += 2

    # A near-miss on the shot number lands here as a confusing "bad type"; name it precisely instead.
    if i + 1 < len(parts) and SEQ_RE.match(parts[i]) and parts[i + 1].isdigit() \
            and not SHOT_RE.match(parts[i + 1]):
        return bad(f"shot number {parts[i + 1]!r} is not 4 digits — shots are 0010, 0020, 0030 "
                   f"(4-digit, allocated in TENS so an inserted beat can take 0015)")
    if i >= len(parts):
        return bad("no type field")
    m = TYPE_RE.match(parts[i])
    if not m:
        return bad(f"type {parts[i]!r} is not one of frame/clip/broll/vo/sfx/mus/master "
                   f"(optionally with a 2-digit instance, e.g. frame01)")
    out["type"], out["instance"] = m.group(1), m.group(2)
    if out["type"] not in DELIVERABLE and "shot" not in out:
        return bad(f"a {out['type']!r} file needs <seq>_<shot> (e.g. s1_0020); only a deliverable "
                   f"({', '.join(sorted(DELIVERABLE))}) may omit them")
    if out["type"] in DELIVERABLE and "shot" in out:
        return bad(f"a {out['type']!r} is a deliverable and carries no shot — it has all of them. "
                   f"A per-shot audio element uses the picture grammar instead "
                   f"(…_s1_0020_vo_host_tasha_v001.wav)")
    i += 1

    desc = []
    while i < len(parts) and not REV_RE.match(parts[i]):
        if not DESC_RE.match(parts[i]):
            return bad(f"descriptor {parts[i]!r} must be lowercase alphanumeric with dashes only")
        desc.append(parts[i]); i += 1
    if i >= len(parts):
        return bad("no version field — expected v<NNN>, three digits, zero-padded (v001). "
                   "A 1- or 2-digit version sorts v10 before v2 and makes a retake chain unreadable")
    out["subject"] = desc[0] if desc else None
    out["model"] = desc[-1] if len(desc) > 1 else None
    out["rev"] = parts[i]; i += 1

    for extra in parts[i:]:
        if ALT_RE.match(extra):
            out["alt"] = extra
        elif LAYOUT_RE.match(extra):
            out["layout"] = extra
        elif RATE_RE.match(extra):
            out["rate"] = extra
        elif extra in SUFFIXES:
            out.setdefault("suffixes", []).append(extra)
        else:
            return bad(f"trailing field {extra!r} is not a format token (9x16), a channel layout "
                       f"(10/20/51/71), a rate+depth (48k24) or a known suffix "
                       f"({', '.join(sorted(SUFFIXES))})")
    return out


def lint(path: str) -> dict:
    files, findings, notes, ok = [], [], [], 0
    if os.path.isfile(path):
        files = [path]
    else:
        for root, _dirs, names in os.walk(path):
            if os.path.basename(root).startswith(("_", ".")):
                continue
            files += [os.path.join(root, n) for n in names if not n.startswith(".")]
    for f in files:
        n = os.path.basename(f)
        if os.path.splitext(n)[1].lower() not in MEDIA_EXT:
            continue
        r = parse(n)
        if r["ok"]:
            ok += 1
            if "shot" in r and int(r["shot"]) % 5:
                notes.append(f"{n}: shot {r['shot']} is not on a 5 — shots are allocated in TENS so "
                             f"an inserted beat can take the number between (0015)")
        else:
            findings.append(f"{os.path.relpath(f, path) if os.path.isdir(path) else n}: {r['error']}")
    return {"path": path, "checked": ok + len(findings), "ok": ok,
            "findings": findings, "notes": notes}


def selftest() -> int:
    good = ["acme-01007_s1_0020_clip_host_seedance_v002.mp4",
            "acme-01007_s1_0020_frame01_host_gptimg_v001.png",
            "acme-01007_hk_0010_broll_panels-drone_cinema_v001.mp4",
            "acme-01007_ct_0010_vo_guest_andre_v001.wav",
            "acme-01007_master_v001_9x16.mp4",
            "acme-01007_s2_0030_clip_guest_minimax_v001_noaudio.mp4",
            "acme-01007_mne_v001_20_48k24.wav",
            "acme-01007_stem-m_v001_20_48k24.wav",
            "acme-01007_mix_v001_51_48k24.wav"]
    for n in good:
        r = parse(n)
        assert r["ok"], (n, r.get("error"))
    r = parse(good[0])
    assert (r["show"], r["seq"], r["shot"], r["type"], r["subject"], r["model"], r["rev"]) == \
        ("acme-01007", "s1", "0020", "clip", "host", "seedance", "v002")
    assert parse(good[1])["instance"] == "01"
    assert parse(good[4]).get("alt") == "9x16"
    assert parse(good[5])["suffixes"] == ["noaudio"]
    mne = parse("acme-01007_mne_v001_20_48k24.wav")
    assert mne["type"] == "mne" and mne["layout"] == "20" and mne["rate"] == "48k24"
    assert parse("acme-01007_stem-m_v001_20_48k24.wav")["type"] == "stem-m"

    bad = {
        "acme-01007_s1_0020_clip_ștefan_seedance_v002.mp4": "non-ASCII",
        "acme-01007_s1_0020_clip_Stefan_seedance_v002.mp4": "uppercase",
        "acme-01007_s1_0020_clip_host_seedance_v2.mp4": "version",
        "acme-01007_s1_020_clip_host_seedance_v002.mp4": "shot number",
        "acme-1007_s1_0020_clip_host_seedance_v002.mp4": "show id",
        "acme-01007_s1_0020_render_host_seedance_v002.mp4": "type",
        "acme-01007_clip_host_seedance_v002.mp4": "needs <seq>_<shot>",
        "ACME-S01E07_S1-C1_host_seedance_v02.mp4": "LEGACY",
        "Proiect-Video-7_S1-C1_host_wan_v1.mp4": "LEGACY",
        "acme-01007_s1_0020_clip host_seedance_v002.mp4": "whitespace",
        "acme-01007_s1_0020_mne_v001_20_48k24.wav": "carries no shot",
        "acme-01007_stem-x_v001_20_48k24.wav": "type",
        "acme-01007_mne_v001_20_44k16_extra.wav": "trailing field",
    }
    for n, why in bad.items():
        r = parse(n)
        assert not r["ok"], (n, "should have failed")
        assert why.lower() in r["error"].lower(), (n, why, r["error"])
    assert insert("0010", "0020") == "0015"
    assert insert("0010", "0011") is None
    print("selftest OK — grammar parse (9 valid shapes incl. audio deliverables), 13 named "
          "rejections including diacritics, case, short version, legacy shapes, shot-on-a-deliverable; "
          "insert arithmetic")
    return 0


def insert(a: str, b: str) -> str | None:
    lo, hi = sorted((int(a), int(b)))
    return f"{(lo + hi) // 2:04d}" if hi - lo >= 2 else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    l = sub.add_parser("lint", help="walk a file or folder and report names that do not parse")
    l.add_argument("path"); l.add_argument("--json", action="store_true")
    e = sub.add_parser("explain", help="parse ONE name and print the fields, or why it failed")
    e.add_argument("name")
    ins = sub.add_parser("insert", help="the shot number to use between two existing shots")
    ins.add_argument("a"); ins.add_argument("b")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "explain":
        r = parse(a.name)
        if not r["ok"]:
            print(f"REJECTED: {r['error']}", file=sys.stderr); return 1
        for k in ("show", "seq", "shot", "type", "instance", "subject", "model", "rev", "alt",
                  "layout", "rate", "suffixes", "ext"):
            if r.get(k):
                print(f"  {k:<9} {r[k]}")
        return 0
    if a.cmd == "insert":
        n = insert(a.a, a.b)
        if not n:
            print(f"REFUSED: no room between {a.a} and {a.b}. Shots are allocated in TENS precisely "
                  f"so this does not happen — if the gap is already spent, the insert goes at the "
                  f"end and the shotlist carries the running order.", file=sys.stderr)
            return 1
        print(n); return 0
    if a.cmd != "lint":
        ap.print_help(); return 2
    if not os.path.exists(a.path):
        print(f"REFUSED: {a.path} does not exist.", file=sys.stderr); return 2
    r = lint(a.path)
    if a.json:
        print(json.dumps(r, indent=2)); return 1 if r["findings"] else 0
    print(f"\nname_lint — {a.path}: {r['checked']} media file(s), {r['ok']} parse cleanly")
    for n in r["notes"]:
        print(f"  · {n}")
    for f in r["findings"]:
        print(f"  ! {f}")
    if not r["findings"]:
        print("  every name parses against the grammar")
    print("  (⛔ nothing was renamed — this tool never touches the disk)\n")
    return 1 if r["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
