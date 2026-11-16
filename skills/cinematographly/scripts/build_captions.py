#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""build_captions.py — styled caption burn WITHOUT Resolve: SRT -> .ass -> ffmpeg/libass. ⛔ NOT THE DEFAULT.

⛔ The native-elements rule: captions default to Resolve's or Fusion's own elements, never a file made outside
without a reason. Captions are made in
Resolve: the locked .srt on a Subtitle track (`native.py console <job> --srt …` → PLACE_SUBTITLES), styled there,
burned by Resolve's render (render-mp4.py BURN_SUBTITLES), checked in the pixels (`srt_qa.py burned`); or as Fusion
Text+ clips. A burn here needs `--reason` — one of the four in `native.py reasons`: batch (a machine-assembled Mode B
batch with no Resolve timeline), derivative (a Mode D re-format of a master already rendered), remux, or owner (their
words, --quote). It writes <output>.external.json, which `approve export` reads and prints.

WHY IT EXISTS. It burns captions AFTER a clean master renders: each format's captions burned by ffmpeg from the
locked .srt, with that format's safe-zone margins and the brand's caption tokens — for the batch and the re-format
that have no timeline to open. (It was written when the Subtitle track looked unscriptable. Since then:
RenderSettings documents ExportSubtitle and SubtitleFormat 'BurnIn', and the console's PLACE_SUBTITLES tries the
.srt import with a read-back — editing-and-audio.md, § Captions.)

WHAT IT CANNOT DO. It does not judge legibility — run the caption QA card in
typography-and-captions.md section 9 on the OUTPUT (extract a frame on the brightest background and
look). It does not create timing — the .srt comes from build_srt.py (locked script + real VO
durations), never a fresh transcription. And it re-encodes once: acceptable at delivery, so burn
from the MASTER, never from an already-burned file.

Usage
-----
  # 1. emit the styled .ass only (inspect/tweak):
  python3 build_captions.py --srt 08-captions/SLUG.srt --format vertical-1080 --out SLUG.ass
  # 2. or go straight to a burned deliverable:
  python3 build_captions.py --srt 08-captions/SLUG.srt --format feed-4x5 \\
      --burn 10-export/SLUG-v1-master.mp4 -o 10-export/SLUG-v1-final_4x5.mp4
  # brand tokens (from the client profile's caption type block):
  #   --font "DejaVu Sans" --size 64 --fill FFFFFF --plate 000000 --plate-alpha 60 --bold
  # disclosure line, burned from frame one at caption prominence (compliance.md section 2):
  #   --disclosure "Dramatization. Not an actual customer."

Style notes: plate = an opaque-ish box behind the text (BorderStyle=4) — the robust contrast
treatment for moving backgrounds; margins derive from the format preset's safe zones
(assets/delivery-formats.json) so a 9:16 and a 4:5 burn land inside their own zones automatically.
Requires ffmpeg built with libass (checked at runtime).
Exit codes: 0 ok · 1 refused · 2 usage/IO/ffmpeg error.
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys

SRT_RE = re.compile(r"(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n(.*?)(?=\n\s*\n|\Z)", re.S)


def load_format(name):
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(os.path.dirname(here), "assets", "delivery-formats.json")
    try:
        formats = json.load(open(path, encoding="utf-8"))["formats"]
    except (OSError, KeyError, ValueError) as e:
        sys.exit(f"error: cannot read {path}: {e}")
    if name not in formats:
        sys.exit(f"error: unknown format {name!r}. Available: {', '.join(sorted(formats))}")
    return formats[name]


def t_ass(t: str) -> str:
    h, m, rest = t.split(":")
    s, ms = re.split("[,.]", rest)
    return f"{int(h)}:{m}:{s}.{ms[:2]}"


def parse_srt(path: str):
    text = open(path, encoding="utf-8-sig").read()
    cues = [(t_ass(a), t_ass(b), body.strip().replace("\n", r"\N"))
            for _, a, b, body in SRT_RE.findall(text)]
    if not cues:
        sys.exit(f"error: no cues parsed from {path} — is it a valid SRT?")
    return cues


def ass_color(hexrgb: str, alpha_pct: int = 0) -> str:
    hexrgb = hexrgb.lstrip("#")
    r, g, b = hexrgb[0:2], hexrgb[2:4], hexrgb[4:6]
    a = int(255 * (alpha_pct / 100))
    return f"&H{a:02X}{b}{g}{r}".upper()


def build_ass(cues, fmt, a) -> str:
    W, H = fmt["width"], fmt["height"]
    # ⛔ Default to the STRICT box. The evidenced margins are measured from TikTok's and Google's
    # own safe-zone template files and are far tighter at the bottom (35%) than the house values
    # this file used to assume (20%) — captions placed in that band are under the platform's own
    # caption/CTA furniture on anything that runs paid. --organic opts into the looser house box,
    # which has no platform source. assets/delivery-formats.json carries both, with the sources.
    sz = fmt.get("safe_zone_organic_pct" if getattr(a, "organic", False) else "safe_zone_pct", {})
    ml = int(W * sz.get("left", 6) / 100)
    mr = int(W * sz.get("right", 6) / 100)
    mv = int(H * sz.get("bottom", 15) / 100)
    size = a.size or max(36, int(H * 0.033))
    style = (f"Style: Cap,{a.font},{size},{ass_color(a.fill)},{ass_color(a.fill)},"
             f"{ass_color(a.plate, 0)},{ass_color(a.plate, 100 - a.plate_alpha)},"
             f"{-1 if a.bold else 0},0,0,0,100,100,0,0,4,3,1,2,{ml},{mr},{mv},1")
    head = ("[Script Info]\nScriptType: v4.00+\n"
            f"PlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
            "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"{style}\n")
    if a.disclosure:
        dsize = int(size * 0.85)
        head += (f"Style: Disc,{a.font},{dsize},{ass_color(a.fill)},{ass_color(a.fill)},"
                 f"{ass_color(a.plate,0)},{ass_color(a.plate,100-a.plate_alpha)},"
                 f"{-1 if a.bold else 0},0,0,0,100,100,0,0,4,3,1,8,{ml},{mr},{int(H*sz.get('top',10)/100)},1\n")
    body = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    if a.disclosure:
        end = cues[-1][1]
        body += f"Dialogue: 1,0:00:00.00,{end},Disc,,0,0,0,,{a.disclosure}\n"
    for start, end, text in cues:
        body += f"Dialogue: 0,{start},{end},Cap,,0,0,0,,{text}\n"
    return head + body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--organic", action="store_true",
                    help="use the looser ORGANIC safe box instead of the evidenced (ad) one. The "
                         "organic box has no platform source — TikTok and YouTube publish safe "
                         "zones only for ads and Meta publishes nothing retrievable. Never pass it "
                         "for a video that will run paid or that carries a disclosure.")
    ap.add_argument("--srt", required=True, help="from build_srt.py — the locked script, never a transcription")
    ap.add_argument("--format", dest="fmt", required=True, help="preset in assets/delivery-formats.json")
    ap.add_argument("--out", help="write the .ass here (default: beside the srt)")
    ap.add_argument("--burn", metavar="MASTER", help="captionless master video to burn onto")
    ap.add_argument("-o", "--output", help="burned output file (required with --burn)")
    ap.add_argument("--font", default="DejaVu Sans", help="caption face — MUST pass the diacritic check "
                    "(typography-and-captions.md section 2); DejaVu Sans has full Romanian coverage")
    ap.add_argument("--size", type=int, default=None, help="px at the format's height (default ~3.3%% of H)")
    ap.add_argument("--fill", default="FFFFFF")
    ap.add_argument("--plate", default="000000")
    ap.add_argument("--plate-alpha", type=int, default=60, help="plate opacity %% (default 60)")
    ap.add_argument("--bold", action="store_true")
    ap.add_argument("--disclosure", default=None,
                    help="burned from frame one, top of frame, caption prominence (compliance.md)")
    ap.add_argument("--crf", type=int, default=18)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import native  # noqa: E402  (stdlib-only)
    native.reason_args(ap)
    a = ap.parse_args()
    if a.burn:
        why = native.check_reason(native.reason_of(a), "this burn")
        if why:
            print("REFUSED: captions are made in Resolve by default (the native-elements rule: Resolve's or Fusion's own "
                  "elements, never a file made outside without a reason).\n  - " + "\n  - ".join(why) +
                  "\nThe native route: native.py console <job> --srt " + a.srt + " (PLACE_SUBTITLES) → style the track once → "
                  "render-mp4.py BURN_SUBTITLES = True → srt_qa.py burned. A burn here takes --reason "
                  + "|".join(native.REASONS) + " --why \"…\" (native.py reasons).", file=sys.stderr)
            return 1

    if a.burn and not a.output:
        sys.exit("error: --burn needs -o OUTPUT")
    if a.burn and "-final" in os.path.basename(a.burn):
        print("REFUSED: input looks like an already-final burned file — burn from the captionless "
              "MASTER, never re-burn a burned file (double re-encode + doubled captions).", file=sys.stderr)
        return 1

    fmt = load_format(a.fmt)
    cues = parse_srt(a.srt)
    ass_path = a.out or os.path.splitext(a.srt)[0] + f".{fmt.get('filename_token','fmt')}.ass"
    open(ass_path, "w", encoding="utf-8").write(build_ass(cues, fmt, a))
    print(f"wrote {ass_path}  ({len(cues)} cues · {fmt['width']}x{fmt['height']} · "
          f"margins from {a.fmt} safe zones" + (" · disclosure pinned from frame one" if a.disclosure else ""))

    if a.burn:
        if not shutil.which("ffmpeg"):
            sys.exit("error: ffmpeg not on PATH")
        vf = f"ass={ass_path}"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.burn, "-vf", vf,
                            "-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow",
                            "-c:a", "copy", a.output], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"error: burn failed: {r.stderr.strip()[:300]}")
        print(f"burned -> {a.output}")
        rec = native.record(a.output, "build_captions", native.reason_of(a), [os.path.basename(a.burn), os.path.basename(a.srt)])
        print(f"  recorded {os.path.basename(native.record_path(a.output))} — {rec['reason']['code']}: {rec['reason'].get('why')}")
        print("  QA next, on the OUTPUT (evidence, not intention): extract a frame on the brightest")
        print("  background a caption sits on and LOOK at it; check diacritics render in one face;")
        print("  then export_qc.py --format " + a.fmt + " on this file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
