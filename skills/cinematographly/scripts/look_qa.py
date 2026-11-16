#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""look_qa.py — the picture measured before it ships, and every shot held to its start frame and its cast.

Author, 2026-10-26, on the grading council (the grade and finish proposal of 2026-10-26
[studio history]): *"A: Export look check, B: Per-model correction
LUTs, C: Shot consistency, D: Looks per lane"*, and the four rule changes: *"Apply all four"*.

  export <job> --export 10-export/<file>.mp4 [--lane ads|drama] [--format vertical-1080]
        A. The file that ships, measured:
        tags     colour range, primaries, transfer and matrix read from the file. A full-range (pc)
                 file, or one not tagged BT.709 (Resolve's Gamma 2.4 tag reads as 1-1-1 on YouTube),
                 fails. Render with Rec.709-A and Video levels [SECONDARY · wolfcrow].
        levels   the share of the picture outside legal video levels (Y 16–235)
        legible  per shot (the 45+ guard, ads lane): the tonal spread (P5–P95), blown highlights,
                 open shadows (C1: the P2 black floor), the faces' local contrast, the caption band's
                 contrast (Owsley 2016: older eyes lose mid/high-frequency contrast and suffer glare)
        platform a round trip through a platform-like H.264 encode: banding it adds in smooth
                 gradients, block edges, and how much grain survives (C2: keep only what survives)
        → <file>.look.json / .look.md beside the render; `gate.py approve export` refuses without a
        passing report on these bytes.
  shots <job>
        C. Every take in the cut: clipped in generation (G8: the grade cannot bring it back), colour
        drift inside the clip, flicker (and so the Deflicker node), skin tone against the same cast's
        other shots, and a capped shot-match CDL solved against its approved start frame
        → 09-qa/look/shots.json (`grade_luts.py plan` reads it)
  check <job>   what `approve export` still needs (exit 1 if anything)
  --selftest

Every threshold marked [assumed] waits for approved real ads to calibrate it. A FAIL refuses the
export; a WARN is a finding for the colourist.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)

OUT_OF_LEGAL = 0.01        # share of pixels below Y 16 or above 235 [assumed]
SPREAD_MIN = 0.40          # P5–P95 of the shot's legal-range luma, ads lane [assumed]
BLOWN_MAX = 0.03           # share at or above 98 % of white [the council, assumed]
BLACK_FLOOR = 3            # C1, open shadows: the shot's P2 at least 3 codes above legal black, ads lane [assumed]
FACE_RMS_MIN = 0.06        # the face's local RMS contrast in legal-range luma [assumed]
CAPTION_RATIO = 4.5        # borrowed from WCAG for text on screen; not validated for video [assumed]
RT_BITRATE = "3M"          # the platform-like encode [assumed: platforms do not publish their ladders]
BANDING_MAX = 0.15         # share of smooth gradient that the round trip turns into steps [assumed]
BLOCK_RATIO_MAX = 1.35     # block-edge energy over inner energy after the round trip [assumed]
GRAIN_SURVIVES = 0.35      # the share of the master's fine texture still there after the round trip [assumed]
CLIP_SHARE = 0.02          # a take with more than this share clipped at 0 or 255 in a channel [assumed]
DRIFT_DE = 4.0             # mean Lab ΔE between the take's start and its end [assumed]
FLICKER_STD = 0.006        # residual frame-to-frame luma (0–1) after a 9-frame trend [assumed]
SKIN_DE = 5.0              # a face's skin against the same cast's median [the council, assumed]
CDL_CAP = {"slope": (0.85, 1.15), "offset": (-0.03, 0.03), "sat": (0.9, 1.1)}   # [the council, assumed]
CDL_MIN_GAIN = 1.0         # solve a CDL only if it brings the take ΔE closer to its start frame by this much


def _np():
    import numpy as np
    return np


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,pix_fmt,color_range,color_primaries,color_transfer,color_space,r_frame_rate"
                        ":format=duration", "-of", "json", path], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    num, den = (s.get("r_frame_rate") or "24/1").split("/")
    s["fps"] = float(num) / float(den or 1)
    s["duration"] = float((d.get("format") or {}).get("duration") or 0)
    return s


def y_frames(path: str, fps: float = 2.0, width: int = 270, t0: float = 0.0, dur: float | None = None):
    """The raw Y plane (no range conversion) sampled at `fps`: [(t, uint8 HxW)]."""
    np = _np()
    info = probe(path)
    W, H = int(info.get("width") or 0), int(info.get("height") or 0)
    if not W:
        return []
    w = min(width, W); w -= w % 2
    h = max(2, int(round(H * w / W / 2.0)) * 2)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", path]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vf", f"fps={fps},extractplanes=y,scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    buf = subprocess.run(cmd, capture_output=True).stdout
    n = len(buf) // (w * h)
    return [(t0 + k / fps, np.frombuffer(buf[k * w * h:(k + 1) * w * h], np.uint8).reshape(h, w)) for k in range(n)]


def rgb_frames(path: str, fps: float = 4.0, width: int = 240, t0: float = 0.0, dur: float | None = None):
    np = _np()
    info = probe(path)
    W, H = int(info.get("width") or 0), int(info.get("height") or 0)
    if not W:
        return []
    w = min(width, W); w -= w % 2
    h = max(2, int(round(H * w / W / 2.0)) * 2)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", path]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    buf = subprocess.run(cmd, capture_output=True).stdout
    n = len(buf) // (w * h * 3)
    return [(t0 + k / fps, np.frombuffer(buf[k * w * h * 3:(k + 1) * w * h * 3], np.uint8).reshape(h, w, 3)) for k in range(n)]


def to_lab(rgb):
    """sRGB 0–255 → CIE Lab (D65)."""
    np = _np()
    c = rgb.astype(np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def de(a, b) -> float:
    np = _np()
    return float(np.sqrt(((np.asarray(a) - np.asarray(b)) ** 2).sum(axis=-1)).mean())


# =================================================================================================
# A. the export
# =================================================================================================
def tag_check(info: dict) -> tuple[str, str]:
    rng, pri, trc, mat = (info.get(k) or "unknown" for k in ("color_range", "color_primaries", "color_transfer",
                                                              "color_space"))
    probs = []
    if rng == "pc":
        probs.append("full range (pc): render with Video levels, not Auto or Full")
    if trc != "bt709":
        probs.append(f"transfer {trc}: render with Rec.709-A — a Gamma 2.4 tag reads as 1-1-1 on YouTube and Vimeo")
    if pri not in ("bt709",):
        probs.append(f"primaries {pri}: tag BT.709")
    if mat not in ("bt709",):
        probs.append(f"matrix {mat}: tag BT.709")
    return ("FAIL" if probs else "PASS"), "; ".join(probs) or f"range {rng} · {pri}/{trc}/{mat}"


def shot_spans(job: str, duration: float, frames: list) -> list:
    """Shots from the newest motion joins report, else from luma-histogram jumps between samples."""
    np = _np()
    js = sorted(glob.glob(os.path.join(job, "09-qa", "motion", "*.joins.json")), key=os.path.getmtime) if job else []
    cuts = []
    if js:
        try:
            cuts = sorted(float(j["t"]) for j in json.load(open(js[-1], encoding="utf-8")).get("joins", []) if j.get("t"))
        except (ValueError, KeyError):
            cuts = []
    if not cuts and len(frames) > 1:
        hs = [np.histogram(f, bins=32, range=(0, 256))[0] / f.size for _, f in frames]
        for i in range(1, len(hs)):
            if 0.5 * np.abs(hs[i] - hs[i - 1]).sum() > 0.35:
                cuts.append(frames[i][0])
    edges = [0.0] + [c for c in cuts if 0 < c < duration] + [duration]
    return [(a, b) for a, b in zip(edges, edges[1:]) if b - a > 0.2]


def _faces(y8):
    import shot_graph as SG
    casc = SG._cascade()
    if casc is None:
        return []
    f = casc.detectMultiScale(y8, 1.1, 5, minSize=(max(16, y8.shape[1] // 12),) * 2)
    return list(f) if len(f) else []


def legibility(frames: list, spans: list, lane: str, safe: dict | None) -> list:
    np = _np()
    out = []
    for i, (a, b) in enumerate(spans, 1):
        fs = [f for t, f in frames if a <= t < b]
        if not fs:
            continue
        L = np.clip((np.concatenate([f.ravel() for f in fs]).astype(np.float32) - 16) / 219.0, 0, 1)
        p2, p5, p95 = (float(np.percentile(L, q)) for q in (2, 5, 95))
        blown = float((L >= 0.98).mean())
        floor_codes = p2 * 219
        faces = []
        for f in fs[::max(1, len(fs) // 3)]:
            for (x, y, w, h) in _faces(f):
                roi = (f[y:y + h, x:x + w].astype(np.float32) - 16) / 219.0
                faces.append(float(roi.std()))
        cap = None
        if safe:
            H, W = fs[0].shape
            y0 = int(H * (1 - safe["bottom"] / 100.0) - 0.18 * H)
            y1 = int(H * (1 - safe["bottom"] / 100.0))
            x0, x1 = int(W * safe["left"] / 100.0), int(W * (1 - safe["right"] / 100.0))
            ratios = []
            for f in fs:
                band = (f[max(0, y0):max(1, y1), x0:x1].astype(np.float32) - 16) / 219.0
                if band.size < 50:
                    continue
                gy = np.abs(np.diff(band, axis=0)).mean()
                if gy < 0.04:                           # no text-like detail in the band
                    continue
                hi, lo, med = np.percentile(band, 98), np.percentile(band, 2), np.median(band)
                r1 = (max(hi, med) + 0.05) / (min(hi, med) + 0.05)
                r2 = (max(lo, med) + 0.05) / (min(lo, med) + 0.05)
                ratios.append(max(r1, r2))
            cap = round(float(np.median(ratios)), 2) if ratios else None
        row = {"shot": i, "from": round(a, 2), "to": round(b, 2), "spread": round(p95 - p5, 3), "blown": round(blown, 4),
               "p2_codes": round(floor_codes, 1), "face_rms": round(float(np.median(faces)), 3) if faces else None,
               "caption_ratio": cap, "fail": [], "warn": []}
        sev = "fail" if lane == "ads" else "warn"
        if row["spread"] < SPREAD_MIN:
            row[sev].append(f"flat: tonal spread {row['spread']} < {SPREAD_MIN}")
        if blown > BLOWN_MAX:
            row[sev].append(f"blown: {blown:.1%} at white (> {BLOWN_MAX:.0%})")
        if lane == "ads" and floor_codes < BLACK_FLOOR:
            row["fail"].append(f"crushed shadows: P2 {floor_codes:.1f} codes over legal black (C1 wants ≥ {BLACK_FLOOR})")
        if row["face_rms"] is not None and row["face_rms"] < FACE_RMS_MIN:
            row["warn"].append(f"soft face contrast {row['face_rms']} < {FACE_RMS_MIN}")
        if cap is not None and cap < CAPTION_RATIO:
            row["warn"].append(f"caption band contrast {cap}:1 < {CAPTION_RATIO}:1")
        out.append(row)
    return out


def _smooth_mask(y):
    np = _np()
    yf = y.astype(np.float32)
    k = 4
    pad = np.pad(yf, k, mode="edge")
    s = np.zeros_like(yf); s2 = np.zeros_like(yf)
    for dy in range(-k, k + 1, 2):
        for dx in range(-k, k + 1, 2):
            v = pad[k + dy:k + dy + yf.shape[0], k + dx:k + dx + yf.shape[1]]
            s += v; s2 += v * v
    n = ((2 * k) // 2 + 1) ** 2
    var = s2 / n - (s / n) ** 2
    gx = np.abs(np.diff(yf, axis=1, append=yf[:, -1:]))
    return (var < 2.5) & (var > 0.02), gx


def roundtrip(path: str, info: dict, samples: list) -> dict:
    """Encode segments around the sample times the way a platform might, and measure what it did."""
    np = _np()
    td = tempfile.mkdtemp(prefix="look-rt-")
    W = int(info.get("width") or 1080)
    width = min(540, W)
    band_scores, block_ratios, grain_keep, grain_master = [], [], [], []
    for k, t in enumerate(samples):
        seg = os.path.join(td, f"s{k}.mp4")
        t0 = max(0.0, t - 1.0)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.3f}", "-i", path, "-t", "2.5", "-an",
                        "-c:v", "libx264", "-preset", "veryfast", "-b:v", RT_BITRATE, "-maxrate", RT_BITRATE,
                        "-bufsize", "6M", "-pix_fmt", "yuv420p", seg], check=False)
        a = y_frames(path, 2.0, width, t, 0.45)
        b = y_frames(seg, 2.0, width, t - t0, 0.45)
        for (_, m), (_, r) in zip(a, b):
            if m.shape != r.shape:
                continue
            smooth, gm = _smooth_mask(m)
            gr = np.abs(np.diff(r.astype(np.float32), axis=1, append=r[:, -1:].astype(np.float32)))
            if smooth.mean() > 0.05:
                band_scores.append(float(((gr >= 1.0) & (gm < 0.4) & smooth).sum() / max(1, smooth.sum())))
            dm = np.abs(np.diff(r.astype(np.float32), axis=1))
            edge = dm[:, 7::8].mean() if dm.shape[1] > 8 else 0.0
            inner = dm.mean() + 1e-6
            block_ratios.append(float(edge / inner))
            mid = (m > 60) & (m < 190)
            lap_m = np.abs(m[1:-1, 1:-1].astype(np.float32) * 4 - m[:-2, 1:-1] - m[2:, 1:-1] - m[1:-1, :-2] - m[1:-1, 2:])
            lap_r = np.abs(r[1:-1, 1:-1].astype(np.float32) * 4 - r[:-2, 1:-1] - r[2:, 1:-1] - r[1:-1, :-2] - r[1:-1, 2:])
            mm = mid[1:-1, 1:-1] & smooth[1:-1, 1:-1] if smooth.any() else mid[1:-1, 1:-1]
            if mm.sum() > 200:
                gmv = float(np.median(lap_m[mm])); grv = float(np.median(lap_r[mm]))
                grain_master.append(gmv)
                grain_keep.append(grv / (gmv + 1e-6))
    med = lambda xs: round(float(np.median(xs)), 3) if xs else None
    return {"banding": med(band_scores), "block_ratio": med(block_ratios), "grain_master": med(grain_master),
            "grain_survives": med(grain_keep), "segments": len(samples), "bitrate": RT_BITRATE}


def export_report(job: str, export: str, lane: str = "ads", fmt: str | None = None, do_roundtrip: bool = True) -> dict:
    np = _np()
    info = probe(export)
    checks, findings = [], []

    def C(name, status, value=None, want=None, detail=""):
        checks.append({"name": name, "status": status, "value": value, "want": want, "detail": detail})
    st, why = tag_check(info)
    C("colour tags", st, detail=why)
    frames = y_frames(export, 2.0, 270)
    if frames:
        allp = np.concatenate([f.ravel() for _, f in frames])
        out = float(((allp < 16) | (allp > 235)).mean())
        C("legal levels", "PASS" if out <= OUT_OF_LEGAL else "FAIL", round(out, 4), f"≤ {OUT_OF_LEGAL:.0%} outside 16–235",
          "" if out <= OUT_OF_LEGAL else "data levels are leaking into a video-levels file")
    safe = None
    try:
        F = json.load(open(os.path.join(SKILL, "assets", "delivery-formats.json"), encoding="utf-8"))["formats"]
        if not fmt:
            W, H = int(info.get("width") or 0), int(info.get("height") or 0)
            fmt = next((k for k, v in F.items() if v.get("width") == W and v.get("height") == H), None)
        safe = (F.get(fmt) or {}).get("safe_zone_pct") if fmt else None
    except (OSError, ValueError, KeyError):
        pass
    spans = shot_spans(job, info["duration"], frames)
    leg = legibility(frames, spans, lane, safe)
    bad = [r for r in leg if r["fail"]]
    C("45+ legibility per shot", "FAIL" if bad else "PASS", len(bad), "0 shots failing",
      "; ".join(f"shot {r['shot']} ({r['from']}–{r['to']} s): {', '.join(r['fail'])}" for r in bad[:6]) or
      f"{len(leg)} shots, lane {lane}")
    for r in leg:
        findings += [f"shot {r['shot']} ({r['from']}–{r['to']} s): {w}" for w in r["warn"]]
    rt = None
    if do_roundtrip and info["duration"] > 0:
        samples = [info["duration"] * q for q in (0.15, 0.4, 0.65, 0.9)] if info["duration"] > 6 else [info["duration"] / 2]
        rt = roundtrip(export, info, samples)
        okb = rt["banding"] is None or rt["banding"] <= BANDING_MAX
        C("platform round trip: banding", "PASS" if okb else "FAIL", rt["banding"], f"≤ {BANDING_MAX}",
          "smooth gradients turned into steps — add a little noise under the gradient, or regrade it" if not okb else
          f"{rt['segments']} segment(s) at {RT_BITRATE}")
        if rt["block_ratio"] and rt["block_ratio"] > BLOCK_RATIO_MAX:
            findings.append(f"the round trip shows block edges ({rt['block_ratio']} > {BLOCK_RATIO_MAX}): busy texture "
                            f"or grain costs bits the platform will not spend")
        if rt["grain_master"] and rt["grain_master"] > 3.0 and (rt["grain_survives"] or 0) < GRAIN_SURVIVES:
            msg = (f"fine texture/grain does not survive the round trip ({rt['grain_survives']:.0%} left): remove it or "
                   f"make it coarser (C2: keep only what survives)")
            (findings.append(msg) if lane == "drama" else C("grain in an ad", "FAIL", rt["grain_survives"],
                                                            f"≥ {GRAIN_SURVIVES:.0%} survives, or none", msg))
    rep = {"export": os.path.relpath(export, job) if job else export, "export_sha256": sha256_file(export), "lane": lane,
           "format": fmt, "measured": dt.datetime.now().isoformat(timespec="minutes"), "probe": info, "shots": leg,
           "roundtrip": rt, "checks": checks, "findings": findings,
           "thresholds_tag": "[assumed] where marked in look_qa.py"}
    rep["verdict"] = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    json.dump(rep, open(export + ".look.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(export + ".look.md", "w", encoding="utf-8").write(render_md(rep))
    return rep


def render_md(r: dict) -> str:
    L = [f"# Look QA — {r['export']}", "", f"**{r['verdict']}** · lane {r['lane']} · format {r['format']} · measured {r['measured']}",
         "", "| check | status | value | want | detail |", "|---|---|---|---|---|"]
    L += [f"| {c['name']} | {c['status']} | {c['value'] if c['value'] is not None else ''} | {c['want'] or ''} | "
          f"{(c['detail'] or '').replace('|', '/')} |" for c in r["checks"]]
    L += ["", "## Per shot", "", "| shot | s | spread | blown | P2 codes | face | caption |", "|---|---|---|---|---|---|---|"]
    L += [f"| {s['shot']} | {s['from']}–{s['to']} | {s['spread']} | {s['blown']} | {s['p2_codes']} | {s['face_rms']} | "
          f"{s['caption_ratio']} |" for s in r["shots"]]
    L += ["", "## Findings", ""] + ([f"- {f}" for f in r["findings"]] or ["- none"]) + ["", f"_{r['thresholds_tag']}_", ""]
    return "\n".join(L)


def check_job(job: str) -> list:
    P = []
    for v in sorted(p for p in glob.glob(os.path.join(job, "10-export", "*")) if p.lower().endswith((".mp4", ".mov", ".mxf"))):
        rel = os.path.relpath(v, job)
        rp = v + ".look.json"
        if not os.path.isfile(rp):
            P.append(f"{rel}: no look report — `look_qa.py export <job> --export {rel} --lane ads|drama`")
            continue
        try:
            r = json.load(open(rp, encoding="utf-8"))
        except ValueError:
            P.append(f"{rel}: look report unreadable"); continue
        if r.get("export_sha256") != sha256_file(v):
            P.append(f"{rel}: the file changed after its look was measured — measure it again")
        elif r.get("verdict") != "PASS":
            P.append(f"{rel}: the look FAILS — " + ", ".join(c["name"] for c in r.get("checks", []) if c["status"] == "FAIL")
                     + f" ({os.path.basename(v)}.look.md)")
    return P


# =================================================================================================
# C. every take in the cut
# =================================================================================================
def _approved_still(job: str, shot: str) -> str | None:
    p = os.path.join(job, "00-brief", "APPROVALS.md")
    if os.path.isfile(p):
        for ln in reversed(open(p, encoding="utf-8").read().splitlines()):
            c = [x.strip() for x in ln.strip().strip("|").split("|")]
            if len(c) > 4 and c[1].lower() == f"frame:{shot}".lower() and c[4]:
                f = os.path.join(job, c[4])
                if os.path.isfile(f):
                    return f
    cands = sorted(glob.glob(os.path.join(job, "02-startframes", f"{shot}_*")) + glob.glob(os.path.join(job, "02-startframes", f"{shot}.*")))
    cands = [c for c in cands if c.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    return cands[-1] if cands else None


def _read_still(path: str, width: int = 240):
    np = _np()
    import shot_graph as SG
    _, cv2 = SG._need()
    im = cv2.imread(path, cv2.IMREAD_COLOR)
    if im is None:
        return None
    h = max(2, int(round(im.shape[0] * width / im.shape[1])))
    return cv2.cvtColor(cv2.resize(im, (width, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)


def solve_cdl(still, frames) -> dict | None:
    """A mild per-channel slope/offset and a saturation that bring the take's opening frames to the
    approved still, capped; None when it would not help by CDL_MIN_GAIN."""
    np = _np()
    if still is None or not frames:
        return None
    import shot_graph as SG
    _, cv2 = SG._need()
    tgt = still.astype(np.float64) / 255.0
    src = np.concatenate([cv2.resize(f, (still.shape[1], still.shape[0])).astype(np.float64)[None] / 255.0 for f in frames])
    slope, offset = [], []
    for ch in range(3):
        s10, s90 = np.percentile(src[..., ch], [10, 90]); t10, t90 = np.percentile(tgt[..., ch], [10, 90])
        sl = (t90 - t10) / max(1e-3, s90 - s10)
        sl = min(max(sl, CDL_CAP["slope"][0]), CDL_CAP["slope"][1])
        of = float(np.median(tgt[..., ch]) - sl * np.median(src[..., ch]))
        offset.append(round(min(max(of, CDL_CAP["offset"][0]), CDL_CAP["offset"][1]), 4)); slope.append(round(sl, 4))
    def chroma(x):
        y = x.mean(axis=-1, keepdims=True)
        return float(np.abs(x - y).mean())
    sat = chroma(tgt) / max(1e-4, chroma(src))
    sat = round(min(max(sat, CDL_CAP["sat"][0]), CDL_CAP["sat"][1]), 4)

    def apply(x):
        y = np.clip(x * np.array(slope) + np.array(offset), 0, 1)
        l = y.mean(axis=-1, keepdims=True)
        return np.clip(l + (y - l) * sat, 0, 1)
    before = de(to_lab(src.mean(axis=0) * 255), to_lab(tgt * 255))
    after = de(to_lab(apply(src.mean(axis=0)) * 255), to_lab(tgt * 255))
    if before - after < CDL_MIN_GAIN:
        return {"apply": False, "de_before": round(before, 2), "de_after": round(after, 2)}
    return {"apply": True, "slope": slope, "offset": offset, "power": [1.0, 1.0, 1.0], "sat": sat,
            "de_before": round(before, 2), "de_after": round(after, 2)}


def first_frame_match(still, frame) -> dict | None:
    """(v2.70.0, Wave 5 A12) How closely a take's FIRST frame matches its own approved start frame: the correlation of
    their luminance (layout: where things are) and of their edges (shapes), and the colour difference of their mean
    Lab. The same shot against the still it was given, never one shot against another (that measures lens and light).
    Reported only — never a gate — until a studio calibrates it on its own approved takes. On a model that takes the
    still as a REFERENCE (no true first frame, e.g. Seedance), a lower number is expected and is not a fault."""
    np = _np()
    if still is None or frame is None:
        return None
    import shot_graph as SG
    _, cv2 = SG._need()
    a = cv2.resize(cv2.cvtColor(still.astype(np.uint8), cv2.COLOR_RGB2GRAY), (96, 54)).astype(np.float64)
    b = cv2.resize(cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_RGB2GRAY), (96, 54)).astype(np.float64)

    def corr(x, y):
        x, y = x - x.mean(), y - y.mean()
        d = float(np.sqrt((x * x).sum() * (y * y).sum()))
        return float((x * y).sum() / d) if d > 1e-9 else 0.0
    ea = cv2.Sobel(a, cv2.CV_64F, 1, 0) ** 2 + cv2.Sobel(a, cv2.CV_64F, 0, 1) ** 2
    eb = cv2.Sobel(b, cv2.CV_64F, 1, 0) ** 2 + cv2.Sobel(b, cv2.CV_64F, 0, 1) ** 2
    still_s = cv2.resize(still.astype(np.uint8), (frame.shape[1], frame.shape[0]))
    return {"luma_corr": round(corr(a, b), 3), "edge_corr": round(corr(np.sqrt(ea), np.sqrt(eb)), 3),
            "de_mean": round(de(to_lab(frame.reshape(-1, 3).mean(axis=0)), to_lab(still_s.reshape(-1, 3).mean(axis=0))), 2)}


def shot_report(job: str, shot: str, take: str, prompt: str | None) -> dict:
    np = _np()
    info = probe(take)
    fr = rgb_frames(take, 8.0, 240)
    if not fr:
        return {"shot": shot, "file": os.path.relpath(take, job), "error": "no frames"}
    arr = np.stack([f for _, f in fr])
    clipped = float(((arr >= 254) | (arr <= 1)).any(axis=-1).mean())
    lead = 1.0 if info["duration"] > 2.5 else 0.0
    head = [f for t, f in fr if lead <= t < lead + 0.5] or [fr[0][1]]
    tail = [f for t, f in fr if t >= info["duration"] - 0.5] or [fr[-1][1]]
    drift = de(to_lab(np.mean(head, axis=0)), to_lab(np.mean(tail, axis=0)))
    yl = np.array([f.mean() / 255.0 for _, f in fr])
    k = 9
    trend = np.convolve(np.pad(yl, k // 2, mode="edge"), np.ones(k) / k, mode="valid")
    flicker = float(np.std(yl - trend)) if len(yl) > k else 0.0
    skin = None
    faces = []
    for t, f in fr[::4]:
        import shot_graph as SG
        _, cv2 = SG._need()
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        for (x, y, w, h) in _faces(g):
            # the cheeks: the lower-middle band of the face box, either side of the nose
            band = f[y + int(0.55 * h):y + int(0.75 * h), x + int(0.15 * w):x + int(0.85 * w)]
            if band.size:
                faces.append(np.median(to_lab(band).reshape(-1, 3), axis=0))
    if faces:
        skin = [round(float(v), 2) for v in np.median(faces, axis=0)]
    still_path = _approved_still(job, shot)
    still = _read_still(still_path) if still_path else None
    opening = [f for t, f in fr if t < 0.35] or [fr[0][1]]
    cdl = solve_cdl(still, opening) if still is not None else None
    ffm = first_frame_match(still, fr[0][1]) if still is not None else None
    persona = None
    if prompt and os.path.isfile(prompt):
        m = re.search(r"(?m)^persona:\s*(\S+)", open(prompt, encoding="utf-8").read())
        persona = m.group(1) if m else None
    rep = {"shot": shot, "file": os.path.relpath(take, job), "sha256": sha256_file(take), "clipped": round(clipped, 4),
           "drift_de": round(drift, 2), "flicker": round(flicker, 4), "deflicker": flicker > FLICKER_STD,
           "skin_lab": skin, "cast": persona or ("face" if skin else None), "start_frame": os.path.relpath(still_path, job) if still_path else None,
           "cdl": cdl, "first_frame_match": ffm, "warn": []}
    if clipped > CLIP_SHARE:
        rep["warn"].append(f"{clipped:.1%} clipped in generation — the grade cannot bring it back (G8); regenerate if it shows")
    if drift > DRIFT_DE:
        rep["warn"].append(f"colour drifts inside the take (ΔE {drift:.1f} start to end)")
    if rep["deflicker"]:
        rep["warn"].append(f"flicker {flicker:.4f} > {FLICKER_STD}: the plan switches on the Deflicker node")
    if cdl and cdl.get("apply"):
        rep["warn"].append(f"shot-match CDL to the start frame: ΔE {cdl['de_before']} → {cdl['de_after']}")
    return rep


def shots_report(job: str) -> dict:
    import motion_qa as MQ
    rows = []
    for s in MQ.selected_shots(job):
        rp = os.path.join(job, "09-qa", "motion", f"{s}.motion.json")
        try:
            f = json.load(open(rp, encoding="utf-8")).get("file")
        except (OSError, ValueError):
            continue
        if f and os.path.isfile(os.path.join(job, f)):
            rows.append(shot_report(job, s, os.path.join(job, f), os.path.join(job, "01-script", "prompts", f"{s}.clip.prompt.md")))
    # skin against the same cast's median
    np = _np()
    casts = {}
    for r in rows:
        if r.get("skin_lab"):
            casts.setdefault(r["cast"], []).append(r)
    for cast, rs in casts.items():
        if len(rs) < 2:
            continue
        med = np.median([r["skin_lab"] for r in rs], axis=0)
        for r in rs:
            d = float(np.sqrt(((np.array(r["skin_lab"]) - med) ** 2).sum()))
            r["skin_de"] = round(d, 2)
            if d > SKIN_DE:
                r["warn"].append(f"skin off the {cast} median by ΔE {d:.1f} — match it on the shot-match node")
    out = {"job": os.path.basename(os.path.abspath(job)), "measured": dt.datetime.now().isoformat(timespec="minutes"),
           "shots": rows}
    d = os.path.join(job, "09-qa", "look"); os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, "shots.json"), "w", encoding="utf-8"), indent=1)
    return out


# =================================================================================================
# selftest
# =================================================================================================
def _encode(path: str, frames, fps: int = 24, rng_tag: str = "tv", trc: str = "bt709", full: bool = False) -> None:
    np = _np()
    h, w = frames[0].shape[:2]
    pix = "rgb24" if frames[0].ndim == 3 else "gray"
    vf = []
    args = ["-color_range", rng_tag, "-color_primaries", "bt709", "-color_trc", trc, "-colorspace", "bt709"]
    out_range = "full" if full else "tv"
    # ⛔ Primaries and transfer go on the FRAMES too (setparams). ffmpeg 8.1.1 drops those two output options for
    # raw frames on a pipe: the file is written with neither tag and every fixture here fails "colour tags"
    # [measured 2026-11-10 · the numbers are in region_repair.py's tag_filter].
    vf = ["-vf", f"scale=out_range={out_range}:out_color_matrix=bt709,setparams=color_primaries=bt709:color_trc={trc}"]
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", pix, "-s", f"{w}x{h}", "-r", str(fps),
                          "-i", "-", *vf, "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", *args, path],
                         stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.ascontiguousarray(f, dtype=np.uint8).tobytes())
    p.stdin.close(); p.wait()


def selftest() -> int:
    np = _np()
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and cond
    rng = np.random.default_rng(1)
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        for d in ("10-export", "09-qa/motion", "02-startframes", "03-clips", "00-brief", "01-script/prompts"):
            os.makedirs(os.path.join(job, d))
        W, H = 180, 320
        yy, xx = np.mgrid[0:H, 0:W]

        def scene(lo, hi, n=48, grain=0.0):
            base = (lo + (hi - lo) * (xx / W * 0.6 + yy / H * 0.4)).astype(np.float32)
            out = []
            for _ in range(n):
                f = base + (rng.standard_normal(base.shape) * grain if grain else 0)
                out.append(np.clip(np.stack([f, f * 0.97, f * 0.92], axis=-1), 0, 255))
            return out
        good = os.path.join(job, "10-export", "good.mp4")
        _encode(good, scene(30, 230))
        r = export_report(job, good, "ads", "vertical-1080")
        st = {c["name"]: c["status"] for c in r["checks"]}
        check("a well-tagged, legal, open-shadowed export passes", r["verdict"] == "PASS", json.dumps(r["checks"]))
        bad = os.path.join(job, "10-export", "pc.mp4")
        _encode(bad, scene(30, 230), rng_tag="pc", trc="unknown", full=True)
        rb = export_report(job, bad, "ads", "vertical-1080", do_roundtrip=False)
        check("a full-range file with a Gamma 2.4-style transfer tag fails the tags",
              {c["name"]: c["status"] for c in rb["checks"]}["colour tags"] == "FAIL", json.dumps(rb["checks"]))
        why = next(c["detail"] for c in rb["checks"] if c["name"] == "colour tags")
        check("…and it names the range and the transfer only: the primaries and the matrix it does carry",
              "full range" in why and "transfer unknown" in why and "primaries" not in why and "matrix" not in why, why)
        crushed = os.path.join(job, "10-export", "crushed.mp4")
        _encode(crushed, [np.clip(f * 1.0 - 40, 0, 255) for f in scene(0, 200)])
        rc = export_report(job, crushed, "ads", "vertical-1080", do_roundtrip=False)
        check("crushed shadows fail the ads lane (C1, open shadows)", any("crushed" in x for s in rc["shots"] for x in s["fail"]),
              json.dumps(rc["shots"]))
        rcd = export_report(job, crushed, "drama", "vertical-1080", do_roundtrip=False)
        check("…and are left to the colourist in drama", not any(s["fail"] for s in rcd["shots"]), json.dumps(rcd["shots"]))
        flat = os.path.join(job, "10-export", "flat.mp4")
        _encode(flat, scene(110, 150))
        rf = export_report(job, flat, "ads", "vertical-1080", do_roundtrip=False)
        check("a flat, low-contrast shot fails the 45+ guard", any("flat" in x for s in rf["shots"] for x in s["fail"]),
              json.dumps(rf["shots"]))
        blown = os.path.join(job, "10-export", "blown.mp4")
        _encode(blown, [np.clip(f * 1.6, 0, 255) for f in scene(30, 230)])
        rbl = export_report(job, blown, "ads", "vertical-1080", do_roundtrip=False)
        check("blown highlights fail the 45+ guard", any("blown" in x for s in rbl["shots"] for x in s["fail"]))
        grainy = os.path.join(job, "10-export", "grain.mp4")
        _encode(grainy, scene(40, 220, grain=9.0))
        rg = export_report(job, grainy, "ads", "vertical-1080")
        check("the round trip measures banding, blocks and how much grain survives",
              rg["roundtrip"] and rg["roundtrip"]["grain_master"] is not None and rg["roundtrip"]["grain_survives"] is not None,
              json.dumps(rg["roundtrip"]))
        gs = rg["roundtrip"]["grain_survives"] or 0
        check("fine grain in an ad that does not survive the round trip fails (C2); it is a finding in drama",
              (gs >= GRAIN_SURVIVES) or any(c["name"] == "grain in an ad" and c["status"] == "FAIL" for c in rg["checks"]),
              json.dumps(rg["roundtrip"]))
        P = check_job(job)
        check("check names the failing renders and passes the good one",
              not any(p.startswith("10-export/good.mp4") for p in P) and any(p.startswith("10-export/pc.mp4") for p in P),
              json.dumps(P))
        open(good, "ab").write(b"\0")
        check("check: a render changed after its look was measured is stale",
              any("good.mp4" in p and "changed after" in p for p in check_job(job)))
        # C. a take against its start frame
        still = scene(40, 220, n=1)[0].astype(np.uint8)
        import shot_graph as SG
        _, cv2 = SG._need()
        sp = os.path.join(job, "02-startframes", "S1_frame_v1.png"); cv2.imwrite(sp, cv2.cvtColor(still, cv2.COLOR_RGB2BGR))
        warm = [np.clip(f * np.array([1.12, 1.0, 0.86]) + np.array([6, 0, -6]), 0, 255) for f in scene(40, 220)]
        for i in range(10, 48, 4):                            # a flicker, and a drift toward the end
            warm[i] = np.clip(warm[i] * 1.12, 0, 255)
        for i in range(36, 48):
            warm[i] = np.clip(warm[i] * np.array([0.9, 1.0, 1.15]), 0, 255)
        take = os.path.join(job, "03-clips", "S1_v1.mp4"); _encode(take, warm)
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "w").write(
            "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n| t | S1 | selects | SELECT | x |\n")
        json.dump({"shot": "S1", "file": "03-clips/S1_v1.mp4"}, open(os.path.join(job, "09-qa", "motion", "S1.motion.json"), "w"))
        sr = shots_report(job)["shots"][0]
        check("a take warmer than its start frame gets a capped shot-match CDL that brings it closer",
              sr["cdl"] and sr["cdl"]["apply"] and sr["cdl"]["de_after"] < sr["cdl"]["de_before"]
              and all(0.85 <= s <= 1.15 for s in sr["cdl"]["slope"]), json.dumps(sr["cdl"]))
        check("flicker is measured and switches the Deflicker node on", sr["deflicker"], json.dumps(sr))
        check("colour drift inside the take is named", any("drifts" in w for w in sr["warn"]), json.dumps(sr["warn"]))
        check("the start frame comes from 02-startframes when no approval names it", sr["start_frame"] == "02-startframes/S1_frame_v1.png")
        # (v2.70.0, A12) the first frame against its own still: the same layout scores high, a shifted one lower
        ff = sr["first_frame_match"]
        moved = os.path.join(job, "03-clips", "S1_moved.mp4"); _encode(moved, [np.roll(still, 80, axis=1)] * 24)
        same = os.path.join(job, "03-clips", "S1_same.mp4"); _encode(same, [still] * 24)
        fs = shot_report(job, "S1", same, None)["first_frame_match"]
        fm = shot_report(job, "S1", moved, None)["first_frame_match"]
        check("(2.70) first-frame match: the still itself scores near 1, a take whose layout moved scores lower, and "
              "a warmer take keeps its layout but shows the colour difference",
              ff and fs and fm and fs["luma_corr"] > 0.95 and fm["luma_corr"] < fs["luma_corr"] - 0.2
              and fm["edge_corr"] < fs["edge_corr"] and ff["de_mean"] > fs["de_mean"],
              json.dumps({"warm": ff, "same": fs, "moved": fm}))
        check("(2.70) the match is reported, never a warning", not any("first frame" in w for w in sr["warn"]))
        later = os.path.join(job, "03-clips", "S1_later.mp4")
        _encode(later, [still] * 4 + [np.roll(still, 80, axis=1)] * 20)     # starts on the still, then the layout moves
        fl = shot_report(job, "S1", later, None)["first_frame_match"]
        check("(2.70) it is the FIRST frame that is scored, not a later one", fl and fl["luma_corr"] > 0.95, json.dumps(fl))
    print("-" * 60)
    print("selftest OK — tags, legal levels, the 45+ guard (flat, blown, crushed shadows in ads only), the platform "
          "round trip, the export check (fail, stale), and a take against its start frame (capped CDL, flicker, drift)"
          if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    e = sub.add_parser("export"); e.add_argument("job"); e.add_argument("--export", required=True)
    e.add_argument("--lane", choices=["ads", "drama"], default="ads"); e.add_argument("--format")
    e.add_argument("--no-roundtrip", action="store_true")
    sub.add_parser("shots").add_argument("job")
    sub.add_parser("check").add_argument("job")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "export":
        ex = a.export if os.path.isabs(a.export) else os.path.join(a.job, a.export)
        r = export_report(a.job, ex, a.lane, a.format, not a.no_roundtrip)
        print(render_md(r)); return 0 if r["verdict"] == "PASS" else 1
    if a.cmd == "shots":
        r = shots_report(a.job)
        for s in r["shots"]:
            print(f"  {s['shot']}: " + ("; ".join(s.get("warn") or []) or "clean"))
        return 0
    if a.cmd == "check":
        P = check_job(a.job)
        for p in P:
            print(f"  ✗ {p}")
        print("clean" if not P else f"{len(P)} problem(s)")
        return 1 if P else 0
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
