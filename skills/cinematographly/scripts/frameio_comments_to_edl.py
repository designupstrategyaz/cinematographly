#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""frameio_comments_to_edl.py — turn a Frame.io comment CSV export into a Resolve marker EDL.

Frame.io V4 dropped the native DaVinci Resolve integration (it was V3 + Resolve 16/17 Studio only),
so client notes no longer sync to the timeline. The working path is: filter the comments panel to one
asset, export CSV, convert to an EDL, then in Resolve right-click the timeline in the Media Pool and
choose Timelines > Import > Timeline Markers from EDL.

The free editingtools.io Marker Converter does the same job in a browser. This exists so client
feedback does not have to be uploaded to a third party, and so the conversion is reproducible in a
scripted pass. See ../references/review-and-approval.md section 5.

Usage
-----
  python3 frameio_comments_to_edl.py comments.csv --fps 24 -o 09-qa/review/markers-r1.edl
  python3 frameio_comments_to_edl.py comments.csv --fps 24 --offset 00:00:00:00   # timeline starts at 0
  python3 frameio_comments_to_edl.py comments.csv --fps 24 --with-author --json
  python3 frameio_comments_to_edl.py --selftest

Column detection is tolerant: the exact header names of the V4 CSV export are UNVERIFIED, so the
timecode / text / author columns are found by matching common names and, for the timecode, by
checking that the values actually parse. Use --timecode-col / --text-col / --author-col to override.
Accepted timecode forms: HH:MM:SS:FF, HH:MM:SS;FF, HH:MM:SS.mmm, HH:MM:SS,mmm, MM:SS, plain seconds.

What it cannot do
-----------------
- **The EDL dialect is UNVERIFIED against a live Resolve import.** It emits the documented CMX3600
  marker convention (event + " |C:<colour> |M:<text> |D:<frames>"). Verify once on a real timeline
  before trusting it in a delivery; if Resolve rejects it, that is a bug in this file, not in your export.
- It cannot know your timeline's start timecode. Frame.io comment timecodes are file-relative, a
  Resolve timeline usually starts at 01:00:00:00 (the default --offset). Markers outside the
  timeline's range import as nothing at all, silently. Check the first marker landed where you expect.
- It cannot recover comments the export did not contain. Frame.io exports only what is VISIBLE after
  filtering, and replies never appear in filters, sorts or search — so a note left as a reply will not
  be in the CSV and will not be in the EDL.
- It does not carry annotations (drawings), attachments, or completed/resolved state. Text and
  timecode only.
- Comments with no timecode (general notes on the asset) cannot become markers; they are skipped and
  counted, never silently dropped.

Exit codes: 0 wrote an EDL - 1 nothing convertible (no timecoded rows) - 2 usage/IO/parse error.
"""
from __future__ import annotations
import argparse, csv, io, json, os, re, sys, tempfile

TC_COL_HINTS = ("timecode", "timestamp", "time_code", "time")
TEXT_COL_HINTS = ("comment", "text", "note", "body", "message")
AUTHOR_COL_HINTS = ("author", "commenter", "user", "name", "created_by", "owner")
COLOURS = ["ResolveColorBlue", "ResolveColorCyan", "ResolveColorGreen", "ResolveColorYellow",
           "ResolveColorRed", "ResolveColorPink", "ResolveColorPurple", "ResolveColorFuchsia",
           "ResolveColorRose", "ResolveColorLavender", "ResolveColorSky", "ResolveColorMint",
           "ResolveColorLemon", "ResolveColorSand", "ResolveColorCocoa", "ResolveColorCream"]
# Resolve's EDL marker text is a single line; these break the import or the line.
UNSAFE = re.compile(r"[|\r\n\t]+")
# kept: ASCII printable + Latin-1/Extended-A (Romanian diacritics live here). Everything else goes,
# but typographic characters are folded to their ASCII twin first so text is not silently chewed.
NONPRINT = re.compile(r"[^\x20-\x7EÀ-ɏ]")
TYPO = {ord(a): b for a, b in {
    "\u2014": "-", "\u2013": "-", "\u2212": "-", "\u2018": "'", "\u2019": "'", "\u201a": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2026": "...", "\u00a0": " ", "\u2192": "->",
    "\u00d7": "x", "\u2022": "-", "\u00ab": '"', "\u00bb": '"',
}.items()}
# Romanian/Latin diacritics -> ASCII, only with --ascii (some Resolve builds refuse non-ASCII in EDLs)
FOLD = {ord(a): b for a, b in {
    "ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
    "Ă": "A", "Â": "A", "Î": "I", "Ș": "S", "Ş": "S", "Ț": "T", "Ţ": "T",
    "á": "a", "à": "a", "ä": "a", "é": "e", "è": "e", "ê": "e", "ë": "e", "í": "i", "ï": "i",
    "ó": "o", "ö": "o", "ô": "o", "ú": "u", "ü": "u", "ù": "u", "ñ": "n", "ç": "c", "ß": "ss",
}.items()}


def parse_tc(raw: str, fps: float) -> int | None:
    """Return frame count, or None if this value is not a timecode."""
    s = (raw or "").strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})[:;](\d{1,3})", s)
    if m:
        h, mi, sec, fr = (int(x) for x in m.groups())
        return int(round(((h * 3600 + mi * 60 + sec) * fps))) + fr
    m = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})", s)
    if m:
        h, mi, sec, ms = (int(x) for x in m.groups())
        ms = ms * (10 ** (3 - len(m.group(4))))
        return int(round((h * 3600 + mi * 60 + sec + ms / 1000.0) * fps))
    m = re.fullmatch(r"(\d{1,3}):(\d{2})", s)              # MM:SS
    if m:
        return int(round((int(m.group(1)) * 60 + int(m.group(2))) * fps))
    m = re.fullmatch(r"\d+(\.\d+)?", s)                     # bare seconds
    if m:
        return int(round(float(s) * fps))
    return None


def fmt_tc(frames: int, fps: float) -> str:
    ipf = int(round(fps))
    frames = max(0, frames)
    f = frames % ipf
    total_s = frames // ipf
    return f"{total_s // 3600:02d}:{(total_s // 60) % 60:02d}:{total_s % 60:02d}:{f:02d}"


def pick_col(headers: list[str], hints: tuple[str, ...], override: str | None) -> str | None:
    if override:
        if override not in headers:
            raise KeyError(override)
        return override
    low = {h.lower().strip(): h for h in headers}
    for hint in hints:                      # exact first, then substring — "timecode" beats "time"
        if hint in low:
            return low[hint]
    for hint in hints:
        for lh, h in low.items():
            if hint in lh:
                return h
    return None


def clean(text: str, limit: int, ascii_only: bool = False) -> str:
    t = UNSAFE.sub(" ", (text or "")).translate(TYPO).strip()
    if ascii_only:
        t = t.translate(FOLD)
    t = NONPRINT.sub("", t)
    t = re.sub(r"\s+", " ", t)
    return t[:limit].rstrip() if len(t) > limit else t


def convert(rows, headers, fps, offset_frames, dur, limit, with_author,
            tc_col, text_col, author_col, colour_by_author, title, ascii_only=False):
    markers, skipped = [], []
    authors: dict[str, int] = {}
    for i, row in enumerate(rows, start=2):     # row 1 is the header
        frames = parse_tc(row.get(tc_col, ""), fps)
        body = clean(row.get(text_col, ""), limit, ascii_only) if text_col else ""
        who = clean(row.get(author_col, ""), 40, ascii_only) if author_col else ""
        if frames is None:
            skipped.append({"row": i, "why": "no parseable timecode", "text": body[:60]})
            continue
        if not body:
            skipped.append({"row": i, "why": "empty comment text", "text": ""})
            continue
        label = f"{who}: {body}" if (with_author and who) else body
        if colour_by_author and who:
            authors.setdefault(who, len(authors))
            colour = COLOURS[authors[who] % len(COLOURS)]
        else:
            colour = None
        markers.append({"frames": frames + offset_frames, "text": clean(label, limit, ascii_only),
                        "colour": colour})
    markers.sort(key=lambda m: m["frames"])
    lines = [f"TITLE: {title}", "FCM: NON-DROP FRAME", ""]
    for n, m in enumerate(markers, start=1):
        src_in, src_out = fmt_tc(m["frames"], fps), fmt_tc(m["frames"] + dur, fps)
        lines.append(f"{n:03d}  001      V     C        {src_in} {src_out} {src_in} {src_out}")
        lines.append(f" |C:{m['colour'] or 'ResolveColorBlue'} |M:{m['text']} |D:{dur}")
    return "\n".join(lines) + "\n", markers, skipped


SELFTEST_CSV = (
    "Timecode,Comment,Commenter,Completed\n"
    "00:00:02:12,Hook lands late \u2014 start on the pour \u201cAn\u0103\u201d,Ana,false\n"
    "00:00:00:00,Logo is fine here,Ana,false\n"
    '00:00:11.500,"Audio dips | pipe and\nnewline in the text",Mihai,false\n'
    ",General note with no timecode,Ana,false\n"
    "00:00:31:00,,Mihai,false\n"
)


def selftest() -> int:
    d = tempfile.mkdtemp(prefix="fio_edl_")
    p = os.path.join(d, "c.csv")
    io.open(p, "w", encoding="utf-8").write(SELFTEST_CSV)
    with io.open(p, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        rows, headers = list(rd), list(rd.fieldnames or [])
    tc = pick_col(headers, TC_COL_HINTS, None)
    tx = pick_col(headers, TEXT_COL_HINTS, None)
    au = pick_col(headers, AUTHOR_COL_HINTS, None)
    assert tc == "Timecode", tc
    assert tx == "Comment", tx
    assert au == "Commenter", au
    edl, markers, skipped = convert(rows, headers, 24.0, 24 * 3600, 1, 120, True,
                                    tc, tx, au, False, "selftest")
    assert len(markers) == 3, [m["text"] for m in markers]
    assert len(skipped) == 2, skipped
    assert markers[0]["frames"] == 24 * 3600 + 0, markers[0]
    assert markers[1]["frames"] == 24 * 3600 + 60, markers[1]        # 2s12f @24 = 60f
    assert markers[2]["frames"] == 24 * 3600 + 276, markers[2]       # 11.5s @24 = 276f
    assert "|" not in markers[2]["text"] and "\n" not in markers[2]["text"], markers[2]["text"]
    assert "01:00:02:12 " in edl, edl
    assert edl.startswith("TITLE: selftest\nFCM: NON-DROP FRAME\n"), edl[:60]
    assert "|M:Ana: Logo is fine here |D:1" in edl, edl
    assert markers[1]["text"] == 'Ana: Hook lands late - start on the pour "Ană"', markers[1]["text"]
    _, m_ascii, _ = convert(rows, headers, 24.0, 0, 1, 120, False, tc, tx, au, False, "t", True)
    assert m_ascii[1]["text"] == 'Hook lands late - start on the pour "Ana"', m_ascii[1]["text"]
    print("selftest OK — 3 markers, 2 skipped, offset, typographic fold, --ascii fold, sanitising correct")
    print("NOTE: this proves the parser, NOT that Resolve accepts the dialect. Verify once on a real timeline.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path", nargs="?", help="Frame.io comment export (CSV)")
    ap.add_argument("-o", "--out", help="output .edl (default: alongside the csv)")
    ap.add_argument("--fps", type=float, default=None,
                    help="timeline fps. No house default — pass it, or --format PRESET")
    ap.add_argument("--format", dest="fmt", default=None,
                    help="preset name from assets/delivery-formats.json; takes its fps_default")
    ap.add_argument("--offset", default="01:00:00:00",
                    help="timeline start timecode added to every marker (default 01:00:00:00; use 00:00:00:00 for a zero-based timeline)")
    ap.add_argument("--duration", type=int, default=1, help="marker length in frames (default 1)")
    ap.add_argument("--max-chars", type=int, default=120, help="truncate marker text (default 120)")
    ap.add_argument("--ascii", action="store_true",
                    help="fold diacritics to ASCII (use if a Resolve build refuses the import)")
    ap.add_argument("--with-author", action="store_true", help="prefix each marker with the commenter")
    ap.add_argument("--colour-by-author", "--color-by-author", dest="colour_by_author",
                    action="store_true", help="one marker colour per commenter")
    ap.add_argument("--timecode-col"), ap.add_argument("--text-col"), ap.add_argument("--author-col")
    ap.add_argument("--title", help="EDL title (default: the csv's basename)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="run the built-in parser check and exit")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.csv_path:
        print("error: give a CSV path (or --selftest). See --help.", file=sys.stderr)
        return 2
    if not os.path.exists(a.csv_path):
        print(f"error: no such file: {a.csv_path}", file=sys.stderr)
        return 2
    if a.fmt and not a.fps:
        import json as _json
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets",
                          "delivery-formats.json")
        try:
            with open(fp, encoding="utf-8") as fh:
                a.fps = float(_json.load(fh)["formats"][a.fmt]["fps_default"])
        except KeyError:
            print(f"error: unknown format {a.fmt!r} — the presets are in assets/delivery-formats.json",
                  file=sys.stderr)
            return 2
    # ⛔ This defaulted to 24 as "the house conform". There is no house conform: a 24 fps EDL imported
    # onto a 25 or 30 fps timeline puts every note on the wrong frame, further off the later it lands.
    if not a.fps:
        print("error: no timeline fps — pass --fps N or --format PRESET (there is no house default)",
              file=sys.stderr)
        return 2
    if a.fps <= 0:
        print("error: --fps must be positive", file=sys.stderr)
        return 2
    offset = parse_tc(a.offset, a.fps)
    if offset is None:
        print(f"error: --offset {a.offset!r} is not a timecode (expected HH:MM:SS:FF)", file=sys.stderr)
        return 2

    try:
        with io.open(a.csv_path, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            rows, headers = list(rd), list(rd.fieldnames or [])
    except OSError as e:
        print(f"error: cannot read {a.csv_path}: {e}", file=sys.stderr)
        return 2
    if not headers:
        print("error: the CSV has no header row — is this a Frame.io comment export?", file=sys.stderr)
        return 2

    try:
        tc = pick_col(headers, TC_COL_HINTS, a.timecode_col)
        tx = pick_col(headers, TEXT_COL_HINTS, a.text_col)
        au = pick_col(headers, AUTHOR_COL_HINTS, a.author_col)
    except KeyError as e:
        print(f"error: column {e} is not in this CSV. Columns: {', '.join(headers)}", file=sys.stderr)
        return 2
    if not tc or not tx:
        missing = "timecode" if not tc else "comment text"
        print(f"error: could not find the {missing} column. Columns: {', '.join(headers)}\n"
              f"       name it explicitly with --timecode-col / --text-col.", file=sys.stderr)
        return 2
    # a column named "time" that holds dates, not timecodes, is the likeliest misdetection
    if not any(parse_tc(r.get(tc, ""), a.fps) is not None for r in rows):
        print(f"error: no value in column {tc!r} parses as a timecode — wrong column, or the export "
              f"has no timecoded comments. Columns: {', '.join(headers)}", file=sys.stderr)
        return 1

    title = a.title or os.path.splitext(os.path.basename(a.csv_path))[0]
    edl, markers, skipped = convert(rows, headers, a.fps, offset, a.duration, a.max_chars,
                                    a.with_author, tc, tx, au, a.colour_by_author, title, a.ascii)
    if not markers:
        print("error: nothing convertible — every row lacked a timecode or text.", file=sys.stderr)
        return 1

    out = a.out or os.path.splitext(a.csv_path)[0] + ".edl"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(edl)

    if a.json:
        print(json.dumps({"out": out, "markers": len(markers), "skipped": skipped,
                          "columns": {"timecode": tc, "text": tx, "author": au},
                          "fps": a.fps, "offset": a.offset,
                          "first": fmt_tc(markers[0]["frames"], a.fps),
                          "last": fmt_tc(markers[-1]["frames"], a.fps)}, indent=2))
        return 0
    print(f"wrote {out}")
    print(f"  {len(markers)} markers - first {fmt_tc(markers[0]['frames'], a.fps)} - "
          f"last {fmt_tc(markers[-1]['frames'], a.fps)} - {a.fps:g} fps")
    print(f"  columns used: timecode={tc!r} text={tx!r} author={au!r}")
    if skipped:
        print(f"  {len(skipped)} row(s) skipped:")
        for s in skipped[:8]:
            print(f"    row {s['row']}: {s['why']}" + (f" — {s['text']!r}" if s["text"] else ""))
        if len(skipped) > 8:
            print(f"    ... and {len(skipped) - 8} more (use --json for all)")
    print("  import: Media Pool > right-click timeline > Timelines > Import > Timeline Markers from EDL")
    print("  CHECK the first marker landed where you expect — markers outside the timeline's "
          "timecode range import as nothing, silently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
