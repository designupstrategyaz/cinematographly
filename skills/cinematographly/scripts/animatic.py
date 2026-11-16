#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""animatic.py — the storyboard as a timed reel: each panel held for its planned seconds, mute or with a
scratch voice, before any start frame or clip is paid for. Free and local (Pillow + ffmpeg).

  animatic.py <job> [--voice WAV|M4A|MP3] [--aspect 16:9|9:16|1:1|4:5] [--fps 25]
        → 01-script/ANIMATIC.mp4 and 01-script/ANIMATIC.json (what it was built from)
  animatic.py --selftest

WHY (pre-production review, 2026-11-14)
A shot list is read; a film is watched. Durations that look right in a table are wrong in time far more
often than sizes are: a 1.5 s insert nobody can read, a 6 s hold with nothing in it, a line that cannot
fit its shot. Those are found here for nothing, or in the cut for the price of every clip in it.

WHAT IT SHOWS
The panels come from the shot list (storyboard.py): the Sequence chain gives the order and the seconds,
the shot table gives the line. A panel's picture is the person's own sketch first, then a drawing or
blocking frame saved as 01-script/storyboard/<SHOT>.png|jpg|webp, then a drawn placeholder showing the
shot size. A band at the foot of each card carries the shot, its size and move, its seconds and the line.

SCRATCH VOICE
--voice takes any recording of the lines read aloud: the person's own phone recording, or a free system
voice (macOS: `say -o scratch.aiff -f lines.txt`). It is laid under the reel from 0:00 and cut or padded
to the reel's length. ⛔ Never a paid voice: a scratch track that costs money is a voice approval in
disguise, and voice is signed at stage 6 (`approve audio`).

WHAT IT IS NOT
It is not the cut and not a deliverable; nothing generated is in it. `gate.py approve storyboard`
checks that this reel and the storyboard page were built from the shot list being signed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import storyboard as SB  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                                        # pragma: no cover
    Image = None

ASPECTS = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080), "4:5": (864, 1080)}
FONTS = ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/SFNS.ttf",
         "/Library/Fonts/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans.ttf")
SIZE_SCALE = {"EWS": 0.14, "WS": 0.42, "MWS": 0.75, "MS": 1.15, "MCU": 1.7, "CU": 2.6, "XCU": 4.5}


def font(px: int):
    for f in FONTS:
        if os.path.isfile(f):
            try:
                return ImageFont.truetype(f, px)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=px)
    except TypeError:                                      # Pillow < 10.1
        return ImageFont.load_default()


def tc(s: float) -> str:
    return f"{int(s // 60)}:{s % 60:04.1f}"


def _wrap(draw, text: str, f, width: int, lines: int = 2) -> list:
    words, out, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= width:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = w
        if len(out) == lines:
            break
    if cur and len(out) < lines:
        out.append(cur)
    if len(out) == lines and " ".join(out) != text.strip():
        out[-1] = out[-1].rstrip(".,;:") + "…"
    return out


def placeholder(size: str, w: int, h: int):
    im = Image.new("RGB", (w, h), (58, 58, 62))
    d = ImageDraw.Draw(im)
    s = "".join(ch for ch in (size or "").upper().split("→")[0] if ch.isalpha())
    if s == "INSERT":
        d.rounded_rectangle([w * .36, h * .33, w * .64, h * .72], radius=8, fill=(120, 120, 126))
    else:
        k = SIZE_SCALE.get(s, 0.75)
        fh = h * k
        top = h - fh * 0.92 if k < 1 else h * (12 - (k - 1) * 18) / 90
        r = fh * 0.075
        cx = w / 2
        d.ellipse([cx - r, top, cx + r, top + 2 * r], fill=(130, 130, 136))
        d.rounded_rectangle([cx - fh * .13, top + r * 2.2, cx + fh * .13, top + r * 2.2 + fh * .62],
                            radius=max(2, int(fh * .05)), fill=(110, 110, 116))
    d.text((int(w * .02), int(h * .02)), f"{size or '?'} · not drawn", font=font(max(14, h // 30)),
           fill=(190, 190, 196))
    return im


def card(p: dict, start: float, W: int, H: int):
    """One panel as a frame: the picture fitted above, the band below."""
    band = int(H * (0.26 if H > W else 0.22))
    im = Image.new("RGB", (W, H), (16, 16, 18))
    area = (W, H - band)
    pic = None
    if p.get("picture"):
        try:
            pic = Image.open(p["picture"])
            pic.load()
            pic = pic.convert("RGB")
        except Exception:
            pic = None
    if pic is None:
        pic = placeholder(p.get("size", ""), area[0], area[1])
    else:                                  # fit the frame both ways: a small phone sketch fills it too
        k = min(area[0] / pic.width, area[1] / pic.height)
        pic = pic.resize((max(1, int(pic.width * k)), max(1, int(pic.height * k))), Image.LANCZOS)
    im.paste(pic, ((area[0] - pic.width) // 2, (area[1] - pic.height) // 2))
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - band, W, H], fill=(0, 0, 0))
    f1, f2 = font(max(18, band // 5)), font(max(16, band // 6))
    pad = int(W * 0.03)
    head = (f"{p['shot']} · {p.get('size') or '?'} · {p.get('move') or '?'} · {p.get('dur') or 0:.1f} s"
            f"   {tc(start)}–{tc(start + (p.get('dur') or 0))}")
    if p.get("source") == "their sketch":
        head += "   · your sketch"
    d.text((pad, H - band + band * .12), head, font=f1, fill=(235, 235, 240))
    say = p.get("line") or p.get("action") or ""
    for i, ln in enumerate(_wrap(d, say, f2, W - 2 * pad)):
        d.text((pad, H - band + band * (.45 + .27 * i)), ln, font=f2, fill=(200, 200, 208))
    return im


def build(job: str, voice: str = "", aspect: str = "16:9", fps: int = 25, ffmpeg: str = "") -> tuple:
    """(manifest, error). Writes 01-script/ANIMATIC.mp4 and ANIMATIC.json."""
    if Image is None:
        return None, "Pillow is not installed (pip install pillow)"
    ffmpeg = ffmpeg or shutil.which("ffmpeg") or ""
    if not ffmpeg:
        return None, "ffmpeg is not on PATH (brew install ffmpeg)"
    ps, errs = SB.panels(job)
    if errs or not ps:
        return None, "; ".join(errs) or "the Sequence chain has no shots"
    nodur = [p["shot"] for p in ps if not p["dur"]]
    if nodur:
        return None, f"no duration on {', '.join(nodur[:8])} — every shot needs its seconds in the Sequence chain"
    if voice and not os.path.isfile(voice):
        return None, f"{voice} is not a file"
    W, H = ASPECTS[aspect]
    md = SB.read(SB.shotlist_path(job))
    tmp = tempfile.mkdtemp(prefix="animatic-")
    try:
        listing, t = [], 0.0
        for i, p in enumerate(ps):
            fp = os.path.join(tmp, f"p{i:03d}.png")
            card(p, t, W, H).save(fp)
            listing += [f"file '{fp}'", f"duration {p['dur']:.3f}"]
            t += p["dur"]
        listing.append(f"file '{os.path.join(tmp, f'p{len(ps) - 1:03d}.png')}'")
        lst = os.path.join(tmp, "list.txt")
        open(lst, "w").write("\n".join(listing) + "\n")
        out = os.path.join(job, SB.ANIMATIC_REL)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst]
        if voice:
            cmd += ["-i", voice, "-map", "0:v", "-map", "1:a", "-af", "apad", "-c:a", "aac", "-b:a", "128k"]
        cmd += ["-vf", f"fps={fps},format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "26", "-t", f"{t:.3f}", "-movflags", "+faststart", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return None, f"ffmpeg failed: {(r.stderr or '').strip()[:400]}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    man = {"built": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
           "film_digest": SB.digest(md), "mp4": SB.ANIMATIC_REL, "mp4_sha256": SB.sha256_file(out),
           "total_s": round(t, 3), "aspect": aspect, "fps": fps,
           "voice": os.path.relpath(voice, job) if voice else None,
           "voice_sha256": SB.sha256_file(voice) if voice else None,
           "panels": [{"shot": p["shot"], "dur": p["dur"], "source": p["source"] or "placeholder"} for p in ps]}
    with open(os.path.join(job, SB.ANIMATIC_JSON_REL), "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2, ensure_ascii=False)
    return man, ""


def probe_seconds(path: str) -> float:
    fp = shutil.which("ffprobe")
    if not fp:
        return -1.0
    r = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return -1.0


def selftest() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
        ok = ok and bool(cond)

    check("Pillow is available", Image is not None)
    if Image is None:
        return 1
    td = tempfile.mkdtemp(prefix="animatic-test-")
    try:
        job = os.path.join(td, "fx-01001-board")
        os.makedirs(os.path.join(job, "01-script", "storyboard", "their"))
        open(SB.shotlist_path(job), "w").write(SB.FIXTURE)
        Image.new("RGB", (400, 300), (200, 120, 60)).save(
            os.path.join(job, "01-script", "storyboard", "their", "hands.png"))
        ps, _ = SB.panels(job)
        c = card(ps[1], 4.0, 1280, 720)
        check("a card is the frame size, with their sketch pasted in",
              c.size == (1280, 720) and c.getpixel((640, 280))[0] > 150)
        c0 = card(ps[0], 0.0, 720, 1280)
        check("a vertical card renders, with a placeholder when nothing is drawn", c0.size == (720, 1280))
        if not shutil.which("ffmpeg"):
            print("  [SKIP] ffmpeg is not on PATH — the reel itself is not built here")
        else:
            man, err = build(job)
            mp4 = os.path.join(job, SB.ANIMATIC_REL)
            check("the reel is built", not err and os.path.isfile(mp4), err)
            if not err:
                secs = probe_seconds(mp4)
                check("it runs for the planned seconds (4.0 + 3.5)", secs < 0 or abs(secs - 7.5) < 0.15, str(secs))
                check("the manifest names the shot list it came from",
                      man["film_digest"] == SB.digest(SB.FIXTURE) and man["mp4_sha256"] == SB.sha256_file(mp4))
                probs = SB.signoff_problems(job)
                check("the sign-off no longer asks for an animatic",
                      not any(("animatic has not" in p or "animatic was built" in p or "rebuild the animatic" in p)
                              for p in probs), "; ".join(probs))
                open(SB.shotlist_path(job), "w").write(SB.FIXTURE.replace("| 3.5 |", "| 2.0 |"))
                check("...until the shot list changes",
                      any("animatic was built from a different" in p for p in SB.signoff_problems(job)))
            open(SB.shotlist_path(job), "w").write(SB.FIXTURE.replace("| 3.5 |", "| - |"))
            _, err = build(job)
            check("a shot with no seconds refuses to build", "no duration on 2" in err, err)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print("animatic.py selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", nargs="?")
    ap.add_argument("--voice", default="", help="a scratch read of the lines (never a paid voice)")
    ap.add_argument("--aspect", default="16:9", choices=sorted(ASPECTS))
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.job:
        ap.error("a job folder is required")
    man, err = build(a.job, a.voice, a.aspect, a.fps)
    if err:
        print(f"REFUSED: {err}", file=sys.stderr)
        return 1
    print(f"animatic · {len(man['panels'])} panel(s) · {man['total_s']:.1f} s · "
          f"{'scratch voice' if man['voice'] else 'mute'} → {os.path.relpath(os.path.join(a.job, man['mp4']))}")
    print("Watch it once at speed, beside the storyboard page. Then sign: `gate.py approve storyboard`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
