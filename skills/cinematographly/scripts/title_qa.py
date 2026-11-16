#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""title_qa.py — a rendered title measured on the picture it will sit on, whichever engine drew it.

Author, 2026-10-26: *"far better titles, suitable to each project"*; the council ranked a legibility gate on
the composite second only to the title card, and the owner chose it (package B). `title_card.py` checks the
plan; this checks the pixels, whichever engine drew the title.

A title made in Resolve — the default since house rule C7 (2026-10-27: *"it should defrult to Resolve or Fusion
native elements"*) — is measured on two of Resolve's own renders of the same timeline, with the titles track on and
off (render-mp4.py TITLES_OFF): their difference is the title, and the off render is the picture right behind it.
A title rendered outside (HyperFrames, supers-gsap — each with its recorded reason) is its ProRes 4444 with alpha, or
an opaque end card, composited over the cut at the title's time.

  native <job> --title <id> --with <render, titles on> --without <render, titles off> [--format …] [--organic]
        → 07-edit/titles/<id>.native.qa.json (bound to both renders and the spec) and <id>.native.strip.png; the
        same checks as below. Render both at the same settings, from the same timeline — two first-generation
        encodes differ only where the titles are; a re-encoded copy does not.
  check <job> --title <id> [--plate <cut.mp4 | still.png>] [--format vertical-1080] [--organic]
        → 07-edit/titles/<id>.mov.qa.json and a 5-frame review strip <id>.mov.strip.png
        safe box     the title's ink stays inside the format's (paid) safe box on every frame
        dwell        the time it is fully in and still, against the reading floor (0.3 s/word when the VO
                     says it, 1 s/word when it doesn't; the card's min_hold_s)
        overshoot    no edge passes its resting place and comes back (house rule C2: none on text)
        contrast     text against the picture right behind it, on the WORST frame of the hold (not the
                     average): 4.5:1 for small type, 3:1 for title sizes [WCAG 2.x thresholds, used for
                     video — assumed]
        phone proof  the thinnest stroke and the cap height on a 390-px-wide phone render (45+ lane:
                     a hairline that vanishes there fails)
        collision    against captions (08-captions/*.srt, the caption band), faces in the plate (OpenCV,
                     when its face model is present) and any --avoid box (the product)
        flash        no more than 3 luminance flashes in any second [WCAG 2.3.1]
        frame edge   ink that reaches one to three edges of the frame is cut text (a supplement ad job: "RUTI", "FUCI");
                     all four is a full-bleed picture card. `title_card.py fit` catches it before anything renders
        centre       a centred style frame: the ink centred on the FRAME (x W/2), not on the safe box — WARN past
                     2 % of the width, FAIL past 4 %; a left-aligned one: the left edge against the margin (WARN)
        negative space  an opaque card: the largest empty rectangle inside the safe box, over half of it, WARNS
                     (one element alone in the middle reads unfinished)
  strip <job> --title <id> [--plate …]
        the options side by side (<id>.opt*.mov), each as entrance · legible · mid · exit · gone, for
        the owner to pick from (`title_card.py pick`) — an outside render's options
  ⚡ v2.45 — the review loop inside Resolve (the author: "It keeps making mp4s which it imports"):
  strip-native <job> --title <id> [--format …] [--organic]
        the options of a title made in Resolve, from Resolve's own stills (the console's PLACE_TITLE_OPTIONS:
        09-qa/titles/<id>/opt<N>_<moment>_{on,off}.png, each option's track on and every title track off): a grid
        07-edit/titles/<id>.options.png (rows the options, columns entrance · legible · mid · exit · gone) and, per
        option, the checks a still pair can answer — safe box, worst-moment contrast against the plate, frame edge,
        centre or margin, the phone stroke and cap height, captions, faces → <id>.options.native.json. Motion (dwell,
        overshoot, flash) needs every frame: `native --with-frames`.
  native … --with-frames DIR --without-frames DIR [--fps N]
        the same native measure on Resolve's ExportFrame sequences (OPTION_FRAMES = "all": f<timeline offset>.png, the
        titles on and off) instead of two renders; the report is bound to the folders' file lists and bytes. The gate
        (`approve titles`) still wants the delivery render and its TITLES_OFF twin.
  check-all <job> [--plate …] [--with … --without …]   every title in 07-edit/titles, each by its engine
  --selftest

Thresholds marked [assumed] wait for real ads on real phones to calibrate them. What it cannot do: read
the words (spelling and claims go through claims_lint.py and the offer sheet), judge taste, or see a
product it was not told about (pass --avoid).
"""
from __future__ import annotations
import argparse, glob, hashlib, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
TITLES = os.path.join("07-edit", "titles")
ANALYSE_W = 540                  # analysis width (half of 1080): bbox values are scaled back to full size
PHONE_W = 390                    # a phone's CSS width (the phone proof)
STROKE_MIN_PX = 1.2              # thinnest stroke at phone width [assumed]
CAP_MIN_PX = {"big": 14.0, "small": 9.0}       # cap height at phone width, 45+ lane [assumed]
CONTRAST_MIN = {"big": 3.0, "small": 4.5}      # WCAG 2.x AA, large vs normal text [used for video — assumed]
BIG_STEPS = ("title", "hero", "display")
OVERSHOOT_PX = 1.5               # an edge that passes its rest by more than this and returns [assumed]
STILL_PX = 1.0                   # a hold: the ink box moves less than this frame to frame
FLASH_DELTA = 0.10               # a flash: mean luminance swing over 10 % of the range [WCAG 2.3.1-ish, assumed]
CAPTION_BAND = 0.22              # captions sit in the lowest 22 % of the safe box [assumed]
CENTRE_WARN, CENTRE_FAIL = 0.02, 0.04   # ink centre off the frame's centre, as a share of its width [assumed]
EMPTY_MAX = 0.50                 # the largest empty rectangle a card may leave, as a share of the safe box [assumed]
EMPTY_GRID = 36                  # columns of the grid the empty rectangle is found on
KIT_STEP = {"hero-line": "hero", "super": "body", "stat": "display", "price-card": "display", "end-card": "title",
            "lockup": "hero", "place-time": "body", "main-title": "display", "episode-card": "hero"}


def _np():
    import numpy as np
    return np


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


FRAME_RE = re.compile(r"^f(\d+)\.(?:png|tif|tiff|jpg)$", re.I)


def frame_files(d: str) -> dict:
    """{timeline frame offset: path} for a folder of Resolve stills named f<offset>.png (PLACE_TITLE_OPTIONS "all")."""
    out = {}
    for f in os.listdir(d):
        m = FRAME_RE.match(f)
        if m:
            out[int(m.group(1))] = os.path.join(d, f)
    return out


def frames_fps(d: str, default: float = 24.0) -> float:
    for name in ("fps.txt", "frames.json"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            try:
                t = open(p, encoding="utf-8").read()
                return float(json.loads(t).get("fps") if t.strip().startswith("{") else t.strip())
            except (ValueError, AttributeError):
                pass
    return float(os.environ.get("CINE_FRAMES_FPS") or default)


def sha256_any(p: str) -> str:
    """A file's sha256, or a folder's: its file names and bytes, in order (a frame sequence)."""
    if not os.path.isdir(p):
        return sha256_file(p)
    h = hashlib.sha256()
    for f in sorted(os.listdir(p)):
        fp = os.path.join(p, f)
        if os.path.isfile(fp):
            h.update(f.encode("utf-8") + b"\0" + sha256_file(fp).encode("ascii"))
    return h.hexdigest()


def probe(p: str) -> dict:
    if os.path.isdir(p):                                  # Resolve's ExportFrame sequence
        import cv2
        ff = frame_files(p)
        im = cv2.imread(ff[min(ff)]) if ff else None
        fps = frames_fps(p)
        return {"w": int(im.shape[1]) if im is not None else 0, "h": int(im.shape[0]) if im is not None else 0, "fps": fps,
                "pix_fmt": "png", "duration": (max(ff) - min(ff) + 1) / fps if ff else 0.0, "first": min(ff) if ff else 0}
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,pix_fmt,nb_frames:format=duration", "-of", "json", p],
                       capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    s = (j.get("streams") or [{}])[0]
    n, d = (s.get("r_frame_rate") or "24/1").split("/")
    return {"w": int(s.get("width") or 0), "h": int(s.get("height") or 0), "fps": float(n) / float(d or 1),
            "pix_fmt": s.get("pix_fmt"), "duration": float((j.get("format") or {}).get("duration") or 0)}


def rgba_frames(p: str, w: int, h: int):
    """Every frame as RGBA float32 in [0, 1], at w×h."""
    np = _np()
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo",
                        "-pix_fmt", "rgba", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    n = a.size // (w * h * 4)
    return a[: n * w * h * 4].reshape(n, h, w, 4).astype(np.float32) / 255.0


def plate_frames(plate: str | None, at: float, n: int, fps: float, w: int, h: int):
    np = _np()
    if not plate:
        return None
    if os.path.isdir(plate):                              # f<offset>.png: the frame at time t is f<round(t·fps)>
        import cv2
        ff = frame_files(plate)
        if not ff:
            return None
        k0 = int(round(at * fps))
        out, last = [], None
        for i in range(n):
            p_ = ff.get(k0 + i)
            if p_ is not None:
                im = cv2.cvtColor(cv2.imread(p_, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
                last = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
            if last is not None:
                out.append(last)
        if len(out) < max(1, n // 2):
            return None
        while len(out) < n:
            out.append(out[-1])
        return np.stack(out)
    if plate.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        f = rgba_frames(plate, w, h)[:1, ..., :3]
        return np.repeat(f, n, axis=0)
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, at):.3f}", "-i", plate, "-frames:v", str(n),
                        "-vf", f"fps={fps},scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    m = a.size // (w * h * 3)
    if m == 0:
        return None
    f = a[: m * w * h * 3].reshape(m, h, w, 3).astype(np.float32) / 255.0
    if m < n:
        f = np.concatenate([f, np.repeat(f[-1:], n - m, axis=0)])
    return f


def rel_lum(rgb):
    np = _np()
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def hex_rgb(s: str):
    s = (s or "#ffffff").strip()
    m = re.match(r"rgba?\(([^)]+)\)", s)
    if m:
        v = [float(x) for x in m.group(1).split(",")[:3]]
        return [x / 255 for x in v]
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return [int(s[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def ink_masks(F, page_bg: str | None):
    """Per frame, where the title has ink: its alpha, or for an opaque card the pixels unlike the page colour."""
    np = _np()
    if page_bg and page_bg != "transparent" and float(F[..., 3].min()) > 0.99:
        bg = np.array(hex_rgb(page_bg), np.float32)
        return (np.abs(F[..., :3] - bg).max(axis=-1) > 0.08)
    return F[..., 3] > 0.5


def bbox(mask):
    np = _np()
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def empty_share(mask, safe_full, W: int) -> float:
    """The largest axis-aligned rectangle with no ink inside the safe box, as a share of the box (a coarse grid)."""
    np = _np()
    k = mask.shape[1] / float(W)
    x0, y0, x1, y1 = [int(round(v * k)) for v in safe_full]
    m = mask[max(0, y0):max(y0 + 1, y1), max(0, x0):max(x0 + 1, x1)]
    if not m.size:
        return 0.0
    cw = max(1, m.shape[1] // EMPTY_GRID)
    gw, gh = max(1, m.shape[1] // cw), max(1, m.shape[0] // cw)
    g = np.zeros((gh, gw), bool)
    for r in range(gh):
        for c in range(gw):
            g[r, c] = bool(m[r * cw:(r + 1) * cw, c * cw:(c + 1) * cw].any())
    best, hgt = 0, [0] * gw
    for r in range(gh):
        hgt = [hgt[c] + 1 if not g[r, c] else 0 for c in range(gw)]
        st = []
        for c in range(gw + 1):
            h_ = hgt[c] if c < gw else 0
            start = c
            while st and st[-1][1] >= h_:
                start, hh = st.pop()
                best = max(best, hh * (c - start))
            st.append((start, h_))
    return best / float(gw * gh)


def hold_window(boxes, cover, full_frac: float = 0.98):
    """The longest run of frames fully in (coverage ≥ 98 % of the max) and still (box moves < STILL_PX)."""
    best, cur, start = (0, 0), 0, 0
    mx = max(cover) if cover else 0
    for i in range(len(boxes)):
        full = boxes[i] is not None and cover[i] >= full_frac * mx
        still = i > 0 and boxes[i - 1] is not None and full and max(abs(a - b) for a, b in zip(boxes[i], boxes[i - 1])) < STILL_PX * ANALYSE_W / 1080 + 0.5
        if full and (still or cur == 0):
            if cur == 0:
                start = i
            cur += 1
            if cur > best[1] - best[0]:
                best = (start, start + cur)
        else:
            cur = 1 if full else 0
            start = i
    return best


def overshoot(masks, land, rise_px: int = 40):
    """Per text line (a band of rows in the resting frame): its vertical centre and its left and right edges,
    on the frames where that line is present (≥ 50 % of its resting ink). An edge that started on one side of
    its rest and crosses to the other by more than OVERSHOOT_PX has overshot. Per line, because lines that
    arrive one after another move a whole-title box in ways no single line does."""
    np = _np()
    if land <= 1 or land >= len(masks):
        return 0.0
    rest = masks[land]
    rows = rest.any(axis=1)
    bands, y = [], 0
    while y < len(rows):
        if rows[y]:
            y0 = y
            while y < len(rows) and rows[y]:
                y += 1
            bands.append((y0, y))
        y += 1
    worst = 0.0
    for y0, y1 in bands:
        a, b = max(0, y0 - rise_px), min(rest.shape[0], y1 + rise_px)

        def feat(m):
            sub = m[a:b]
            ys, xs = np.nonzero(sub)
            if xs.size == 0:
                return None, 0
            return (float(ys.mean()), float(xs.min()), float(xs.max())), xs.size
        R, rn = feat(rest)
        if R is None:
            continue
        first = None
        for m in masks[:land]:
            f, n = feat(m)
            if f is None or n < 0.5 * rn:
                continue
            if first is None:
                first = f
                continue
            for k in range(3):
                side = (first[k] > R[k]) - (first[k] < R[k])
                d = f[k] - R[k]
                if side and d * side < 0:
                    worst = max(worst, abs(d))
    return worst * 1080 / ANALYSE_W


def stroke_and_cap(mask_full, phone_w: int, card: dict, kit: str, step: str, W: int):
    """The thinnest stroke on the phone-size render (distance transform ridge), and the cap height there from
    the anchor font's metrics."""
    np = _np()
    import cv2
    h, w = mask_full.shape
    ph = int(round(h * phone_w / w))
    m = cv2.resize(mask_full.astype(np.float32), (phone_w, ph), interpolation=cv2.INTER_AREA) > 0.5
    if not mask_full.any():
        return None, None
    if not m.any():
        return 0.0, None                                # every stroke vanished at phone width
    dt = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 3)
    ridge = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & m & (dt > 0)
    vals = dt[ridge] * 2.0 - 1.0                       # a 1-px line has distance 1 at its centre: width = 2·d − 1
    stroke = float(np.percentile(vals, 10)) if vals.size else None
    cap = None
    try:
        import title_card as TC
        f = (card.get("fonts") or {}).get("anchor" if kit not in ("place-time",) else "companion") or {}
        p = TC._font_path(card, f)
        if p and os.path.isfile(p):
            ft = TC.read_font(p)
            if ft.get("cap_height") and ft.get("units_per_em"):
                size = TC.sizes(card, int(round(W * 16 / 9)) if W < 1500 else 3840)[step]
                cap = size * ft["cap_height"] / ft["units_per_em"] * phone_w / W
    except Exception:  # noqa: BLE001 — the metric is a finding, never a crash
        cap = None
    return stroke, cap


def contrast_worst(F, P, masks, frames, fg):
    """WCAG contrast of the text colour against the brightest (or darkest) background right around it, on the
    worst frame of the hold."""
    np = _np()
    import cv2
    if P is None:
        return None
    fgL = float(rel_lum(np.array(fg, np.float32)))
    worst = None
    k = np.ones((9, 9), np.uint8)
    for i in frames:
        m = masks[i].astype(np.uint8)
        if not m.any():
            continue
        ring = (cv2.dilate(m, k, iterations=2) > 0) & (m == 0)
        if F[i, ..., 3].min() > 0.99:                 # an opaque card: the background is its own page
            bgpix = F[i, ..., :3][ring]
        else:
            a = F[i, ..., 3:4]
            comp = F[i, ..., :3] * a + P[i] * (1 - a)
            bgpix = comp[ring]
        if bgpix.size == 0:
            continue
        L = rel_lum(bgpix)
        bg = float(np.percentile(L, 95)) if fgL > 0.5 else float(np.percentile(L, 5))
        r = (max(fgL, bg) + 0.05) / (min(fgL, bg) + 0.05)
        worst = r if worst is None else min(worst, r)
    return worst


def srt_times(job: str):
    out = []
    for p in glob.glob(os.path.join(job, "08-captions", "*.srt")):
        for m in re.finditer(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", open(p, encoding="utf-8", errors="replace").read()):
            g = [int(x) for x in m.groups()]
            out.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000))
    return out


def faces(P, idx):
    np = _np()
    try:
        import cv2
        xml = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if not os.path.isfile(xml):
            return None
        det = cv2.CascadeClassifier(xml)
    except Exception:  # noqa: BLE001
        return None
    out = []
    for i in idx:
        g = cv2.cvtColor((P[i] * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        for (x, y, w, h) in det.detectMultiScale(g, 1.1, 5, minSize=(24, 24)):
            out.append([int(x), int(y), int(x + w), int(y + h)])
    return out


def _overlap(a, b):
    return a and b and a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _load(job: str, tid: str, spec_p: str | None = None):
    import title_card as TC
    spec_p = spec_p or os.path.join(job, TITLES, f"{tid}.title.json")
    spec = json.load(open(spec_p, encoding="utf-8"))
    card = TC.load_card(os.path.join(job, TC.CARD))
    K = (card.get("kinds") or {}).get(spec.get("kind")) or {}
    kit = spec.get("kit") or K.get("kit") or "super"
    return spec_p, spec, card, K, kit


def _checks(job, spec, card, K, kit, fmt, organic, avoid, F, P, masks, fps, W, H, full_mask, full_frac=0.98):
    """Every check on the composite, whatever drew the title: F is RGBA (the title and where it has ink), P the
    picture right behind it. Returns (checks, h0, h1, u)."""
    np = _np()
    import title_card as TC
    n = len(F)
    aw = F.shape[2]
    sx = W / aw
    boxes = [bbox(m) for m in masks]
    cover = [float(m.sum()) for m in masks]
    h0, h1 = hold_window(boxes, cover, full_frac)
    hold_s = (h1 - h0) / fps
    checks = []

    def add(name, status, value=None, limit=None, note=""):
        checks.append({"name": name, "status": status, "value": value, "limit": limit, "note": note})
    # safe box
    box = fmt["safe_zone_organic_pct" if organic else "safe_zone_pct"]
    safe = [W * box["left"] / 100, H * box["top"] / 100, W * (1 - box["right"] / 100), H * (1 - box["bottom"] / 100)]
    allb = [b for b in boxes if b]
    if not allb:
        add("ink", "FAIL", note="the render has no visible title")
        u = None
    else:
        u = [min(b[0] for b in allb) * sx, min(b[1] for b in allb) * sx, max(b[2] for b in allb) * sx, max(b[3] for b in allb) * sx]
        out = max(safe[0] - u[0], safe[1] - u[1], u[2] - safe[2], u[3] - safe[3], 0)
        add("safe box", "PASS" if out <= 2 else "FAIL", round(out, 1), 2,
            f"ink {[round(x) for x in u]} vs the {'organic' if organic else 'paid'} box {[round(x) for x in safe]}: "
            "fewer words, never smaller type" if out > 2 else "")
    # dwell
    words = TC._words(spec)
    floor = words * (TC.SAID_S_PER_WORD if spec.get("said_by_vo") else TC.UNSAID_S_PER_WORD)
    if K.get("min_hold_s"):
        floor = max(floor, float(K["min_hold_s"]))
    add("dwell", "PASS" if hold_s + 1 / fps >= floor else "FAIL", round(hold_s, 2), round(floor, 2),
        f"{words} word(s), {'said by the VO' if spec.get('said_by_vo') else 'only on screen'}")
    # overshoot (C2)
    ov = overshoot(masks, h0 if h0 > 0 else n - 1, int(round(H * 0.03 / sx)))
    add("overshoot", "PASS" if ov <= OVERSHOOT_PX else "FAIL", round(ov, 1), OVERSHOOT_PX, "no overshoot on text (C2)")
    # contrast on the worst frame of the hold, against the plate
    step = KIT_STEP.get(kit, "body")
    big = step in BIG_STEPS
    fg = hex_rgb((card.get("colors") or {}).get("fg"))
    hold_idx = list(range(h0, h1)) or [n // 2]
    cr = contrast_worst(F, P, masks, hold_idx[:: max(1, len(hold_idx) // 12)], fg)
    lim = CONTRAST_MIN["big" if big else "small"]
    if cr is None:
        add("contrast", "WARN" if P is None and float(F[..., 3].min()) <= 0.99 else "PASS", None, lim,
            "no plate given: measure on the cut (--plate) before export" if P is None else "")
    else:
        add("contrast", "PASS" if cr >= lim else "FAIL", round(cr, 2), lim, "worst frame of the hold, text vs what is right behind it")
    # phone proof
    full_idx = hold_idx[len(hold_idx) // 2]
    fm = full_mask(full_idx)
    fullmask = fm if fm is not None else masks[full_idx]
    stroke, cap = stroke_and_cap(fullmask, PHONE_W, card, kit, step, W)
    strict = bool(card.get("audience_45plus")) or card.get("lane") == "ads"
    if stroke is not None:
        add("phone stroke", "PASS" if stroke >= STROKE_MIN_PX else ("FAIL" if strict else "WARN"), round(stroke, 2), STROKE_MIN_PX,
            f"thinnest strokes (p10) at {PHONE_W} px wide")
    if cap is not None:
        cl = CAP_MIN_PX["big" if big else "small"]
        add("phone cap height", "PASS" if cap >= cl else ("FAIL" if strict else "WARN"), round(cap, 1), cl, f"at {PHONE_W} px wide")
    # collisions
    at = float(spec.get("at_s") or 0)
    dur = n / fps
    cap_band = [safe[0], safe[3] - (safe[3] - safe[1]) * CAPTION_BAND, safe[2], safe[3]]
    hits = [t for t in srt_times(job) if t[0] < at + dur and at < t[1]]
    if hits and _overlap(u, cap_band):
        add("captions", "FAIL", len(hits), 0, "the title sits in the caption band while captions are on screen")
    else:
        add("captions", "PASS", len(hits), 0, "" if hits else "no caption on screen with it, or it is clear of the band")
    if P is not None:
        fz = faces(P, hold_idx[:: max(1, len(hold_idx) // 4)])
        if fz is None:
            add("faces", "WARN", None, None, "OpenCV's face model is not installed: check by eye that no face is covered")
        else:
            cov = [f for f in fz if _overlap(u, [x * sx for x in f])]
            add("faces", "PASS" if not cov else "FAIL", len(cov), 0, "a title never covers a face")
    for a in avoid or []:
        bx = [a[0] * W, a[1] * H, (a[0] + a[2]) * W, (a[1] + a[3]) * H]
        add("avoid", "PASS" if not _overlap(u, bx) else "FAIL", None, None, f"box {a}")
    # ⚡ a supplement ad job (2026-10-28): ingredient names cut at the edge ("RUTI", "FUCI"), cards centred on the safe box (x 447)
    # instead of the frame (x 540), and a tick alone in the middle of a card that read as unfinished.
    if u:
        hold_boxes = [boxes[i] for i in hold_idx if boxes[i]] or allb
        gaps = [min(b[0] for b in hold_boxes), min(b[1] for b in hold_boxes),
                aw - max(b[2] for b in hold_boxes), F.shape[1] - max(b[3] for b in hold_boxes)]
        touch = sum(1 for g in gaps if g < 1)
        if touch == 4:
            add("frame edge", "PASS", 0, None, "full-bleed: ink on all four edges (a picture card, not cut text)")
        else:
            add("frame edge", "PASS" if touch == 0 else ("WARN" if touch == 3 else "FAIL"), round(min(gaps) * sx, 1), round(sx, 1),
                f"ink reaches {touch} edge(s) of the frame: the text is cut — fewer words or a line break "
                f"(`title_card.py fit` measures it before anything renders)" if touch else "")
        sf = card.get("style_frame") or {}
        centred = (K.get("align") or sf.get("align")) == "centre"
        if centred:
            off = abs((u[0] + u[2]) / 2 - W / 2) / W
            add("centre", "PASS" if off <= CENTRE_WARN else ("WARN" if off <= CENTRE_FAIL else "FAIL"), round(off, 3),
                CENTRE_FAIL, f"ink centred at x {round((u[0] + u[2]) / 2)} — centre on the frame (x {W // 2}), not on the "
                "safe box: the safe box limits where load-bearing text may reach, it is not the centre line")
        elif sf.get("margin_left_x"):
            off = abs(u[0] / W - float(sf["margin_left_x"]))
            add("left margin", "PASS" if off <= CENTRE_WARN else "WARN", round(off, 3), CENTRE_WARN,
                f"ink starts at x {round(u[0])}; the style frame's margin is x {round(float(sf['margin_left_x']) * W)}")
        page = spec.get("page_bg") or K.get("page_bg")
        if page and page != "transparent":
            fm2 = fullmask if fullmask is not None else masks[full_idx]
            es = empty_share(fm2, safe, W)
            add("negative space", "PASS" if es <= EMPTY_MAX else "WARN", round(es, 2), EMPTY_MAX,
                "the largest empty rectangle inside the safe box, as a share of it: one element alone on a card reads "
                "unfinished — fill it, or give the element the card" if es > EMPTY_MAX else "")
    # flash
    comp = F[..., :3] * F[..., 3:4] + (P if P is not None else 0.5) * (1 - F[..., 3:4])
    Lm = rel_lum(comp).mean(axis=(1, 2))
    swings = [i for i in range(1, n) if abs(float(Lm[i] - Lm[i - 1])) > FLASH_DELTA]
    per_s = max([sum(1 for s in swings if i <= s < i + fps) for i in range(0, n)] or [0])
    add("flash", "PASS" if per_s <= 3 else "FAIL", per_s, 3, "luminance flashes in any one second")
    return checks, h0, h1, u


def _fmt(fmt_name: str) -> dict:
    return json.load(open(os.path.join(SKILL, "assets", "delivery-formats.json"), encoding="utf-8"))["formats"][fmt_name]


def measure(job: str, tid: str, mov: str, plate: str | None, fmt_name: str = "vertical-1080", organic: bool = False,
            avoid: list | None = None) -> dict:
    """A title rendered outside Resolve (HyperFrames, supers-gsap): its ProRes 4444 alpha, or an opaque card."""
    m_opt = re.search(r"\.(opt\d+)\.mov$", mov)
    spec_p = os.path.join(job, TITLES, f"{tid}.{m_opt.group(1)}.title.json") if m_opt else None
    spec_p, spec, card, K, kit = _load(job, tid, spec_p)
    fmt = _fmt(fmt_name)
    info = probe(mov)
    W, H = info["w"] or fmt["width"], info["h"] or fmt["height"]
    aw, ah = ANALYSE_W, int(round(ANALYSE_W * H / W))
    F = rgba_frames(mov, aw, ah)
    n = len(F)
    fps = info["fps"] or 24.0
    page_bg = spec.get("page_bg") or K.get("page_bg")
    masks = ink_masks(F, page_bg)
    P = plate_frames(plate, float(spec.get("at_s") or 0), n, fps, aw, ah)

    def full_mask(i):
        Ff = rgba_frames_one(mov, i, W, H)
        return ink_masks(Ff[None], page_bg)[0] if Ff is not None else None
    checks, h0, h1, _u = _checks(job, spec, card, K, kit, fmt, organic, avoid, F, P, masks, fps, W, H, full_mask)
    verdict = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    rep = {"title": tid, "engine": spec.get("engine") or "hyperframes", "render": os.path.relpath(mov, job),
           "render_sha256": sha256_file(mov), "kit": kit,
           "plate": os.path.relpath(plate, job) if plate and os.path.abspath(plate).startswith(os.path.abspath(job)) else plate,
           "format": fmt_name, "fps": fps, "frames": n, "hold": [round(h0 / fps, 3), round(h1 / fps, 3)],
           "verdict": verdict, "checks": checks, "thresholds": "[assumed] where marked in title_qa.py"}
    strip(mov, P, aw, ah, F, [max(0, h0 // 2), h0, (h0 + h1) // 2, max(h0, h1 - 1), n - 1], mov + ".strip.png")
    json.dump(rep, open(mov + ".qa.json", "w", encoding="utf-8"), indent=1)
    return rep


NATIVE_MARGIN_S = 0.25   # frames read before and after the spec's window: a title placed a few frames off is still seen
NATIVE_FULL = 0.90       # a native title's ink is a difference, so its coverage wavers with the plate: "fully in" is
                         # 90 % of its most, not 98 % [assumed]


def native_report(job: str, tid: str) -> str:
    return os.path.join(job, TITLES, f"{tid}.native.qa.json")


def measure_native(job: str, tid: str, with_p: str, without_p: str, fmt_name: str = "vertical-1080",
                   organic: bool = False, avoid: list | None = None, fps: float | None = None) -> dict:
    """A title made in Resolve (house rule C7): measured on two of Resolve's own renders of the same timeline,
    with the titles track on and off (render-mp4.py TITLES_OFF). Their difference is the title; the off render is
    the picture right behind it."""
    np = _np()
    import native
    spec_p, spec, card, K, kit = _load(job, tid)
    fmt = _fmt(fmt_name)
    if fps:
        os.environ["CINE_FRAMES_FPS"] = str(fps)          # a frame folder carries no rate of its own
    probs = native.same_shape(with_p, without_p)
    info = probe(with_p)
    W, H = info["w"] or fmt["width"], info["h"] or fmt["height"]
    fps = info["fps"] or 24.0
    aw, ah = ANALYSE_W, int(round(ANALYSE_W * H / W))
    at = float(spec.get("at_s") or 0)
    t0 = max(0.0, at - NATIVE_MARGIN_S)
    n = max(1, int(round((at - t0 + float(spec.get("duration_s") or 0) + NATIVE_MARGIN_S) * fps)))
    Fw, Fo, masks = native.diff_frames(with_p, without_p, t0, n, fps, aw, ah)
    page_bg = spec.get("page_bg") or K.get("page_bg")

    def opaque(Fw_, m_):
        """An opaque card covers the frame: its ink is what is unlike its page colour, as for an outside render."""
        if not page_bg or page_bg == "transparent":
            return m_, np.zeros(m_.shape, np.float32) + m_
        a = m_.astype(np.float32)
        for i in range(len(m_)):
            if m_[i].mean() > 0.9:
                a[i] = 1.0
                m_[i] = ink_masks(np.concatenate([Fw_[i:i + 1], np.ones(Fw_[i:i + 1, ..., :1].shape, np.float32)], axis=-1), page_bg)[0]
        return m_, a
    if Fw is None:
        rep = {"title": tid, "engine": "resolve", "verdict": "FAIL", "problems": probs + ["the renders could not be read at "
               f"{t0:.2f} s (shorter than the title's window?)"], "checks": []}
        json.dump(rep, open(native_report(job, tid), "w", encoding="utf-8"), indent=1)
        return rep
    masks, alpha = opaque(Fw, masks)
    F = np.concatenate([Fw, alpha[..., None]], axis=-1)

    def full_mask(i):
        a_, b_, m_ = native.diff_frames(with_p, without_p, t0 + i / fps, 1, fps, W, H)
        if m_ is None or not len(m_):
            return None
        return opaque(a_, m_)[0][0]
    checks, h0, h1, _u = _checks(job, spec, card, K, kit, fmt, organic, avoid, F, Fo, masks, fps, W, H, full_mask, NATIVE_FULL)
    for p_ in probs:
        checks.insert(0, {"name": "same timeline", "status": "FAIL", "value": None, "limit": None, "note": p_})
    verdict = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    rel = lambda x: os.path.relpath(x, job) if os.path.abspath(x).startswith(os.path.abspath(job) + os.sep) else x
    out_strip = os.path.join(job, TITLES, f"{tid}.native.strip.png")
    rep = {"title": tid, "engine": "resolve", "with": rel(with_p), "with_sha256": sha256_any(with_p),
           "without": rel(without_p), "without_sha256": sha256_any(without_p), "spec_sha256": sha256_file(spec_p),
           "source": "frames (Resolve ExportFrame)" if os.path.isdir(with_p) else "renders",
           "kit": kit, "format": fmt_name, "fps": fps, "window_s": [round(t0, 3), round(t0 + n / fps, 3)],
           "hold": [round(t0 + h0 / fps, 3), round(t0 + h1 / fps, 3)], "verdict": verdict, "checks": checks,
           "thresholds": f"[assumed] where marked in title_qa.py; native.DIFF_THR {native.DIFF_THR}"}
    strip(with_p, Fo, aw, ah, F, [max(0, h0 // 2), h0, (h0 + h1) // 2, max(h0, h1 - 1), len(F) - 1], out_strip)
    json.dump(rep, open(native_report(job, tid), "w", encoding="utf-8"), indent=1)
    return rep


def rgba_frames_one(p: str, i: int, w: int, h: int):
    np = _np()
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"select=eq(n\\,{i}),scale={w}:{h}", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    if a.size < w * h * 4:
        return None
    return a[: w * h * 4].reshape(h, w, 4).astype(np.float32) / 255.0


def strip(mov, P, aw, ah, F, idx, out):
    """Five frames on the plate (entrance · legible · mid · exit start · gone): the review strip (T8)."""
    np = _np()
    import cv2
    tiles = []
    for i in idx:
        i = min(max(0, i), len(F) - 1)
        bg = P[i] if P is not None else np.full((ah, aw, 3), 0.35, np.float32)
        a = F[i, ..., 3:4]
        c = F[i, ..., :3] * a + bg * (1 - a)
        tiles.append((np.clip(c, 0, 1) * 255).astype(np.uint8))
    im = np.concatenate(tiles, axis=1)
    cv2.imwrite(out, cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
    return out


def options_strip(job: str, tid: str, plate: str | None) -> str:
    np = _np()
    import cv2
    rows = []
    for mov in sorted(glob.glob(os.path.join(job, TITLES, f"{tid}.opt*.mov"))):
        s = mov + ".strip.png"
        if not os.path.isfile(s):
            measure(job, tid, mov, plate)
        im = cv2.imread(s)
        lab = os.path.basename(mov).split(".")[1]
        cv2.putText(im, lab, (12, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3, cv2.LINE_AA)
        rows.append(im)
    if not rows:
        raise SystemExit(f"error: no {tid}.opt*.mov in {TITLES}")
    w = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0))) for r in rows]
    out = os.path.join(job, TITLES, f"{tid}.options.png")
    cv2.imwrite(out, np.concatenate(rows, axis=0))
    return out


MOMENTS = ("entrance", "legible", "mid", "exit", "gone")
STILL_CHECKS = ("ink", "safe box", "contrast", "phone stroke", "phone cap height", "captions", "faces", "avoid",
                "frame edge", "centre", "left margin", "negative space")


def _read_rgb(p: str, w: int, h: int):
    np = _np()
    import cv2
    im = cv2.imread(p, cv2.IMREAD_COLOR)
    if im is None:
        return None
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    return cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def strip_native(job: str, tid: str, fmt_name: str = "vertical-1080", organic: bool = False, avoid: list | None = None) -> dict:
    """⚡ v2.45: the options of a title made in Resolve, read from Resolve's own stills (PLACE_TITLE_OPTIONS). Per option
    the still-answerable checks on the on/off difference, and the grid for the owner's pick."""
    np = _np()
    import cv2
    import native
    sd = os.path.join(job, "09-qa", "titles", tid)
    opts = sorted({int(m.group(1)) for f in (os.listdir(sd) if os.path.isdir(sd) else [])
                   for m in [re.match(r"opt(\d+)_[a-z]+_(?:on|off)\.png$", f)] if m})
    if not opts:
        raise SystemExit(f"error: no Resolve stills in 09-qa/titles/{tid}/ (opt<N>_<moment>_on|off.png) — run the console "
                         f"copy from `native.py console <job> --options {tid}` (PLACE_TITLE_OPTIONS)")
    fmt = _fmt(fmt_name)
    rep = {"title": tid, "engine": "resolve", "source": "Resolve stills (Timeline.ExportFrame)", "format": fmt_name,
           "options": {}, "moments": list(MOMENTS)}
    rows = []
    for N in opts:
        on_p = [os.path.join(sd, f"opt{N}_{m}_on.png") for m in MOMENTS]
        off_p = [os.path.join(sd, f"opt{N}_{m}_off.png") for m in MOMENTS]
        miss = [os.path.basename(p) for p in on_p + off_p if not os.path.isfile(p)]
        spec_p = os.path.join(job, TITLES, f"{tid}.opt{N}.title.json")
        if miss or not os.path.isfile(spec_p):
            rep["options"][N] = {"verdict": "FAIL", "problems": [f"missing {', '.join(miss[:4])}" if miss else
                                                                 f"no {os.path.relpath(spec_p, job)}"]}
            continue
        _sp, spec, card, K, kit = _load(job, tid, spec_p)
        im0 = cv2.imread(on_p[1])
        H, W = (im0.shape[0], im0.shape[1]) if im0 is not None else (fmt["height"], fmt["width"])
        aw, ah = ANALYSE_W, int(round(ANALYSE_W * H / W))
        Fw = np.stack([_read_rgb(p, aw, ah) for p in on_p])
        Fo = np.stack([_read_rgb(p, aw, ah) for p in off_p])
        masks = native.clean_masks(np.abs(Fw - Fo).max(axis=-1) > native.DIFF_THR)
        page_bg = spec.get("page_bg") or K.get("page_bg")
        alpha = masks.astype(np.float32)
        if page_bg and page_bg != "transparent":
            for i in range(len(masks)):
                if masks[i].mean() > 0.9:
                    alpha[i] = 1.0
                    masks[i] = ink_masks(np.concatenate([Fw[i:i + 1], np.ones(Fw[i:i + 1, ..., :1].shape, np.float32)], -1), page_bg)[0]
        F = np.concatenate([Fw, alpha[..., None]], axis=-1)

        def full_mask(i, on_p=on_p, off_p=off_p):
            a_, b_ = _read_rgb(on_p[i], W, H), _read_rgb(off_p[i], W, H)
            if a_ is None or b_ is None:
                return None
            return native.clean_masks((np.abs(a_ - b_).max(axis=-1) > native.DIFF_THR)[None])[0]
        fps_eff = len(MOMENTS) / max(0.1, float(spec.get("duration_s") or 1))
        checks, _h0, _h1, _u = _checks(job, spec, card, K, kit, fmt, organic, avoid, F, Fo, masks, fps_eff, W, H, full_mask,
                                       NATIVE_FULL)
        checks = [c for c in checks if c["name"] in STILL_CHECKS]
        verdict = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
        rep["options"][N] = {"verdict": verdict, "checks": checks, "spec": os.path.relpath(spec_p, job),
                             "spec_sha256": sha256_file(spec_p),
                             "stills": {os.path.basename(p): sha256_file(p) for p in on_p + off_p},
                             "not_measured_here": "dwell, overshoot and flash need every frame (native --with-frames)"}
        tiles = [(np.clip(Fw[i], 0, 1) * 255).astype(np.uint8) for i in range(len(MOMENTS))]
        row = np.concatenate(tiles, axis=1)
        row = cv2.cvtColor(row, cv2.COLOR_RGB2BGR)
        cv2.putText(row, f"opt{N} {verdict}", (12, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3, cv2.LINE_AA)
        rows.append(row)
    out = os.path.join(job, TITLES, f"{tid}.options.png")
    if rows:
        w_ = max(r.shape[1] for r in rows)
        cv2.imwrite(out, np.concatenate([np.pad(r, ((0, 0), (0, w_ - r.shape[1]), (0, 0))) for r in rows], axis=0))
        rep["grid"] = os.path.relpath(out, job)
    json.dump(rep, open(os.path.join(job, TITLES, f"{tid}.options.native.json"), "w", encoding="utf-8"), indent=1)
    return rep


# =================================================================================================
def _synth_title(path: str, W: int, H: int, fps: int, seconds: float, box, overshoot_px: int = 0, thin: bool = False,
                 colour=(255, 255, 255)):
    """A white block 'title' sliding up into place (optionally overshooting), as ProRes 4444 with alpha."""
    np = _np()
    n = int(seconds * fps)
    frames = []
    land = int(0.5 * fps)
    for i in range(n):
        a = np.zeros((H, W, 4), np.uint8)
        x0, y0, x1, y1 = box
        if i < land:
            t = i / land
            off = int((1 - t) * 30)
            if overshoot_px and 0.6 < t < 0.95:
                off = -overshoot_px
        else:
            off = 0
        alpha = min(1.0, i / max(1, land * 0.6)) if i < land else (1.0 if i < n - int(0.25 * fps) else max(0.0, (n - i) / (0.25 * fps)))
        yy0, yy1 = y0 + off, y1 + off
        if thin:
            a[yy0:yy1, x0:x1:7, :3] = colour
            a[yy0:yy1, x0:x1:7, 3] = int(255 * alpha)
        else:
            for k in range(x0, x1, 20):                       # glyph-like bars, 11 px strokes
                a[yy0:yy1, k:k + 11, :3] = colour
                a[yy0:yy1, k:k + 11, 3] = int(255 * alpha)
        frames.append(a)
    raw = np.stack(frames).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps),
                    "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", path],
                   input=raw, check=True)


def _synth_pair(on: str, off: str, W: int, H: int, fps: int, seconds: float, box, at: float, dur: float, plate_rgb=(32, 36, 40)):
    """Two first-generation H.264 renders of one 'timeline': a plate with soft moving grain, and the same plate with
    a white bar title held from `at` for `dur` seconds (a 0.3 s fade in and out)."""
    np = _np()
    rng = np.random.default_rng(7)
    n = int(seconds * fps)
    base = np.array(plate_rgb, np.float32)
    A, B = [], []
    x0, y0, x1, y1 = box
    for i in range(n):
        g = rng.normal(0, 3, ((H + 7) // 8, (W + 7) // 8, 1)).astype(np.float32)
        g = np.repeat(np.repeat(g, 8, 0), 8, 1)[:H, :W]
        p = np.clip(base + g, 0, 255)
        q = p.copy()
        t = i / fps
        if at <= t < at + dur:
            a = min(1.0, (t - at) / 0.3, (at + dur - t) / 0.3)
            for k in range(x0, x1, 20):
                q[y0:y1, k:k + 11] = q[y0:y1, k:k + 11] * (1 - a) + 255 * a
        A.append(q.astype(np.uint8))
        B.append(p.astype(np.uint8))
    for path, fr in ((on, A), (off, B)):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
                        "-i", "-", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", path],
                       input=np.stack(fr).tobytes(), check=True)


def selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and bool(cond)
    import title_card as TC
    font = TC._sysfont("InterDisplay-ExtraBold.otf", "Inter-Bold.otf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf")
    reg = TC._sysfont("Inter-Regular.otf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf")
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        T = os.path.join(job, TITLES)
        os.makedirs(T); os.makedirs(os.path.join(job, "00-brief")); os.makedirs(os.path.join(job, "08-captions"))
        TC.propose(job, "ads", accent="#E8432E", page_bg="#111111")
        card = TC.load_card(os.path.join(job, TC.CARD))
        if font and reg:
            fa, fr = TC.read_font(font), TC.read_font(reg)
            card["fonts"] = {"anchor": {"family": fa["family"], "file": font, "weight": int(fa["weight_class"])},
                             "companion": {"family": fr["family"], "file": reg, "weight": int(fr["weight_class"])}}
        json.dump({k: v for k, v in card.items() if k != "__path"}, open(card["__path"], "w"), indent=1)
        W, H, fps = 540, 960, 12
        spec = {"id": "T1", "kind": "hero", "duration_s": 2.5, "at_s": 0.0, "anchor": {"type": "settle", "at_s": 0.0}, "said_by_vo": True,
                "content": {"lines": ["Sleep through", "the night"], "emphasis": "night"}}
        json.dump(spec, open(os.path.join(T, "T1.title.json"), "w"))
        good = os.path.join(T, "T1.mov")
        _synth_title(good, W, H, fps, 2.5, (120, 210, 380, 280))
        dark = os.path.join(td, "dark.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x202428:s=540x960", "-frames:v", "1", dark], check=True)
        r = measure(job, "T1", good, dark)
        st = {c["name"]: c["status"] for c in r["checks"]}
        check("a held white title on a dark plate, inside the box, passes safe box, dwell, overshoot and contrast",
              all(st.get(k) == "PASS" for k in ("safe box", "dwell", "overshoot", "contrast", "flash")), json.dumps(r["checks"]))
        check("the review strip is written", os.path.isfile(good + ".strip.png"))
        light = os.path.join(td, "light.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xE8E8E2:s=540x960", "-frames:v", "1", light], check=True)
        r = measure(job, "T1", good, light)
        check("the same white title on a light plate fails contrast on the worst frame",
              {c["name"]: c["status"] for c in r["checks"]}["contrast"] == "FAIL", json.dumps(r["checks"]))
        ov = os.path.join(T, "T1.opt1.mov")
        json.dump(spec, open(os.path.join(T, "T1.opt1.title.json"), "w"))
        _synth_title(ov, W, H, fps, 2.5, (120, 210, 380, 280), overshoot_px=8)
        r = measure(job, "T1", ov, dark)
        check("a title that rises past its place and settles back fails overshoot (C2)",
              {c["name"]: c["status"] for c in r["checks"]}["overshoot"] == "FAIL", json.dumps(r["checks"]))
        out = os.path.join(T, "T1.opt2.mov")
        json.dump(spec, open(os.path.join(T, "T1.opt2.title.json"), "w"))
        _synth_title(out, W, H, fps, 2.5, (30, 60, 500, 130))
        r = measure(job, "T1", out, dark)
        check("ink outside the paid safe box fails", {c["name"]: c["status"] for c in r["checks"]}["safe box"] == "FAIL", json.dumps(r["checks"]))
        # ⚡ a supplement ad job: cut at the edge, centred on the safe box instead of the frame, a card left mostly empty
        cut_ = os.path.join(T, "T1.opt6.mov")
        json.dump(spec, open(os.path.join(T, "T1.opt6.title.json"), "w"))
        _synth_title(cut_, W, H, fps, 2.5, (0, 300, 300, 360))
        r = measure(job, "T1", cut_, dark)
        check("text that runs off the frame's edge fails `frame edge` (a supplement ad job: RUTI, FUCI)",
              {c["name"]: c["status"] for c in r["checks"]}.get("frame edge") == "FAIL", json.dumps(r["checks"]))
        cj = json.load(open(card["__path"], encoding="utf-8"))
        json.dump(dict(cj, style_frame={"align": "centre"}), open(card["__path"], "w"), indent=1)
        for box_, want in (((140, 210, 400, 280), "PASS"), ((60, 210, 300, 280), "FAIL")):
            mv = os.path.join(T, "T1.opt7.mov")
            json.dump(spec, open(os.path.join(T, "T1.opt7.title.json"), "w"))
            _synth_title(mv, W, H, fps, 2.5, box_)
            r = measure(job, "T1", mv, dark)
            check(f"a centred style frame: ink centred at x {(box_[0] + box_[2]) // 2} of {W} → centre {want}",
                  {c["name"]: c["status"] for c in r["checks"]}.get("centre") == want, json.dumps(r["checks"]))
        json.dump(cj, open(card["__path"], "w"), indent=1)
        for (bx, by_, bw, bh), want in (((250, 450, 40, 40), "WARN"), ((70, 300, 400, 560), "PASS")):
            mv = os.path.join(T, "T1.opt8.mov")
            json.dump(dict(spec, page_bg="#111111"), open(os.path.join(T, "T1.opt8.title.json"), "w"))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            f"color=c=0x111111:s={W}x{H}:r={fps}:d=2.5,format=rgba,drawbox=x={bx}:y={by_}:w={bw}:h={bh}:"
                            f"color=white:t=fill", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", mv],
                           check=True)
            r = measure(job, "T1", mv, None)
            check(f"an opaque card with ink {bw}x{bh} px → negative space {want}",
                  {c["name"]: c["status"] for c in r["checks"]}.get("negative space") == want, json.dumps(r["checks"]))
        short = os.path.join(T, "T1.opt3.mov")
        json.dump(spec, open(os.path.join(T, "T1.opt3.title.json"), "w"))
        _synth_title(short, W, H, fps, 1.0, (120, 210, 380, 280))
        r = measure(job, "T1", short, dark)
        check("a 1 s title fails the reading floor of 4 words the VO says (1.2 s held)", {c["name"]: c["status"] for c in r["checks"]}["dwell"] == "FAIL", json.dumps(r["checks"]))
        thin = os.path.join(T, "T1.opt4.mov")
        json.dump(spec, open(os.path.join(T, "T1.opt4.title.json"), "w"))
        _synth_title(thin, W, H, fps, 2.5, (120, 210, 380, 280), thin=True)
        r = measure(job, "T1", thin, dark)
        check("hairlines that vanish at phone width fail the phone proof in the 45+ lane",
              {c["name"]: c["status"] for c in r["checks"]}.get("phone stroke") == "FAIL", json.dumps(r["checks"]))
        low = os.path.join(T, "T1.opt5.mov")
        json.dump(dict(spec, at_s=1.0), open(os.path.join(T, "T1.opt5.title.json"), "w"))
        _synth_title(low, W, H, fps, 2.5, (120, 550, 380, 610))
        open(os.path.join(job, "08-captions", "c.srt"), "w").write("1\n00:00:02,000 --> 00:00:04,000\nhello\n")
        r = measure(job, "T1", low, dark)
        check("a title in the caption band while a caption is up fails",
              {c["name"]: c["status"] for c in r["checks"]}["captions"] == "FAIL", json.dumps(r["checks"]))
        p = options_strip(job, "T1", dark)
        check("the options strip stacks every option for the owner's pick", os.path.isfile(p))
        # a title made in Resolve: two renders of one timeline, the titles on and off (house rule C7)
        os.remove(os.path.join(job, "08-captions", "c.srt"))
        on, off = os.path.join(td, "on.mp4"), os.path.join(td, "off.mp4")
        _synth_pair(on, off, W, H, fps, 4.0, (120, 210, 380, 280), at=1.0, dur=2.5, plate_rgb=(32, 36, 40))
        json.dump(dict(spec, at_s=1.0), open(os.path.join(T, "T1.title.json"), "w"))
        r = measure_native(job, "T1", on, off)
        st = {c["name"]: c["status"] for c in r["checks"]}
        check("native: a held white title on a dark plate, found as the difference of two renders, passes safe box, "
              "dwell, overshoot and contrast", all(st.get(k) == "PASS" for k in ("safe box", "dwell", "overshoot", "contrast", "flash")),
              json.dumps(r["checks"]))
        check("native: the report is bound to both renders and the spec, with its strip",
              r.get("with_sha256") and r.get("without_sha256") and r.get("spec_sha256")
              and os.path.isfile(os.path.join(T, "T1.native.strip.png")), r)
        _synth_pair(on, off, W, H, fps, 4.0, (120, 210, 380, 280), at=1.0, dur=2.5, plate_rgb=(226, 226, 220))
        r = measure_native(job, "T1", on, off)
        check("native: the same title over a light plate fails contrast", {c["name"]: c["status"] for c in r["checks"]}["contrast"] == "FAIL",
              json.dumps(r["checks"]))
        _synth_pair(on, off, W, H, fps, 4.0, (30, 60, 500, 130), at=1.0, dur=2.5, plate_rgb=(32, 36, 40))
        r = measure_native(job, "T1", on, off)
        check("native: ink outside the paid safe box fails", {c["name"]: c["status"] for c in r["checks"]}["safe box"] == "FAIL",
              json.dumps(r["checks"]))
        short = os.path.join(td, "short.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", off, "-t", "2", "-c", "copy", short], check=True)
        r = measure_native(job, "T1", on, short)
        check("native: two renders of different lengths fail (not the same timeline)", r["verdict"] == "FAIL"
              and any("length" in (c.get("note") or "") for c in r["checks"]), json.dumps(r.get("checks")))
        # ⚡ v2.45: Resolve's ExportFrame sequences instead of two renders (OPTION_FRAMES = "all")
        import cv2
        verdicts = {}
        for plate_rgb, tag in (((32, 36, 40), "dark"), ((226, 226, 220), "light")):
            _synth_pair(on, off, W, H, fps, 4.0, (120, 210, 380, 280), at=1.0, dur=2.5, plate_rgb=plate_rgb)
            rm = measure_native(job, "T1", on, off)
            dirs = []
            for src_, nm in ((on, "on"), (off, "off")):
                d_ = os.path.join(td, f"frames-{tag}", nm)
                os.makedirs(d_)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src_, "-start_number", "0", os.path.join(d_, "f%06d.png")], check=True)
                dirs.append(d_)
            rf = measure_native(job, "T1", dirs[0], dirs[1], fps=fps)
            verdicts[tag] = (rm["verdict"], rf["verdict"], {c["name"]: c["status"] for c in rf["checks"]}.get("contrast"),
                             rf.get("source"), rf.get("with_sha256"))
        check("native frames mode: Resolve's still sequences, the titles on and off, give the renders' verdicts — PASS on the "
              "dark plate, a contrast FAIL on the light one — bound to the folders",
              verdicts["dark"][:2] == ("PASS", "PASS") and verdicts["light"][:3] == ("FAIL", "FAIL", "FAIL")
              and verdicts["dark"][3].startswith("frames") and len(verdicts["dark"][4] or "") == 64, verdicts)
        # ⚡ v2.45: the options of a native title as Resolve stills (PLACE_TITLE_OPTIONS → strip-native)
        sd = os.path.join(job, "09-qa", "titles", "T1")
        os.makedirs(sd, exist_ok=True)
        import numpy as np_
        base = np_.full((H, W, 3), (32, 36, 40), np_.float32)
        for N, box in ((1, (120, 210, 380, 280)), (2, (30, 60, 290, 130))):
            json.dump(dict(spec, at_s=1.0, id=f"T1.opt{N}"), open(os.path.join(T, f"T1.opt{N}.title.json"), "w"))
            for m_, a_ in zip(MOMENTS, (0.4, 1.0, 1.0, 1.0, 0.0)):
                q = base.copy()
                x0, y0, x1, y1 = box
                for k in range(x0, x1, 20):
                    q[y0:y1, k:k + 11] = q[y0:y1, k:k + 11] * (1 - a_) + 255 * a_
                cv2.imwrite(os.path.join(sd, f"opt{N}_{m_}_on.png"), cv2.cvtColor(q.astype(np_.uint8), cv2.COLOR_RGB2BGR))
                cv2.imwrite(os.path.join(sd, f"opt{N}_{m_}_off.png"), cv2.cvtColor(base.astype(np_.uint8), cv2.COLOR_RGB2BGR))
        rs = strip_native(job, "T1")
        st1 = {c["name"]: c["status"] for c in rs["options"][1]["checks"]}
        st2 = {c["name"]: c["status"] for c in rs["options"][2]["checks"]}
        check("strip-native: from Resolve's stills, option 1 passes the box and contrast, option 2's ink outside the paid box "
              "fails; no motion check is claimed from stills; the grid and the report are written",
              rs["options"][1]["verdict"] == "PASS" and st1.get("safe box") == "PASS" and st1.get("contrast") == "PASS"
              and st2.get("safe box") == "FAIL" and "dwell" not in st1 and "overshoot" not in st1
              and os.path.isfile(os.path.join(T, "T1.options.png")) and os.path.isfile(os.path.join(T, "T1.options.native.json")),
              (rs["options"][1], st2))
    print("-" * 60)
    print("selftest OK — on synthetic renders: a held title passes, the light plate fails contrast on its worst frame, "
          "an overshoot fails (C2), ink outside the paid box fails, a short hold fails, hairlines fail the phone proof, "
          "the caption band collision fails, text cut at the frame's edge fails, a centred title off the frame's centre fails, "
          "a mostly empty card warns, and the strips are written; a title made in Resolve is measured as the "
          "difference of two renders, and fails contrast, the box and a mismatched pair the same way; v2.45: the same on "
          "Resolve's ExportFrame sequences, and a native title's options checked from Resolve's own stills" if ok else "selftest FAILED")
    return 0 if ok else 1


def check_job(job: str) -> list:
    """Reports for every title render: present, on these bytes, passing (title_card.renders_ok reads them)."""
    import title_card as TC
    return TC.renders_ok(job)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("check", "strip"):
        c = sub.add_parser(name); c.add_argument("job"); c.add_argument("--title", required=True)
        c.add_argument("--plate"); c.add_argument("--format", default="vertical-1080"); c.add_argument("--organic", action="store_true")
        c.add_argument("--avoid", action="append", default=[], help="x,y,w,h as fractions of the frame (the product)")
    nv = sub.add_parser("native"); nv.add_argument("job"); nv.add_argument("--title", required=True)
    nv.add_argument("--with", dest="with_", help="Resolve's render with the titles on")
    nv.add_argument("--without", help="the same timeline rendered with the titles off (render-mp4.py TITLES_OFF)")
    nv.add_argument("--with-frames", help="a folder of Resolve stills f<offset>.png, the titles on (OPTION_FRAMES all)")
    nv.add_argument("--without-frames", help="the same frames with every title track off")
    nv.add_argument("--fps", type=float, help="the timeline's rate, for a frame folder")
    sn = sub.add_parser("strip-native"); sn.add_argument("job"); sn.add_argument("--title", required=True)
    sn.add_argument("--format", default="vertical-1080"); sn.add_argument("--organic", action="store_true")
    sn.add_argument("--avoid", action="append", default=[])
    nv.add_argument("--format", default="vertical-1080"); nv.add_argument("--organic", action="store_true")
    nv.add_argument("--avoid", action="append", default=[], help="x,y,w,h as fractions of the frame (the product)")
    ca = sub.add_parser("check-all"); ca.add_argument("job"); ca.add_argument("--plate"); ca.add_argument("--format", default="vertical-1080")
    ca.add_argument("--with", dest="with_"); ca.add_argument("--without")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "check":
        mov = os.path.join(a.job, TITLES, f"{a.title}.mov")
        av = [[float(x) for x in s.split(",")] for s in a.avoid]
        r = measure(a.job, a.title, mov, a.plate, a.format, a.organic, av)
        for c in r["checks"]:
            print(f"  {c['status']:4}  {c['name']:<16} {c['value'] if c['value'] is not None else '':>6}  (limit {c['limit']})  {c['note']}")
        print(f"{r['verdict']} — {os.path.relpath(mov, a.job)}.qa.json · strip {os.path.relpath(mov, a.job)}.strip.png")
        return 0 if r["verdict"] == "PASS" else 1
    if a.cmd == "native":
        av = [[float(x) for x in s_.split(",")] for s_ in a.avoid]
        w_, wo_ = (a.with_frames, a.without_frames) if a.with_frames else (a.with_, a.without)
        if not (w_ and wo_):
            print("error: --with and --without (two renders), or --with-frames and --without-frames", file=sys.stderr)
            return 2
        r = measure_native(a.job, a.title, w_, wo_, a.format, a.organic, av, a.fps)
        for c in r["checks"]:
            print(f"  {c['status']:4}  {c['name']:<16} {c['value'] if c['value'] is not None else '':>6}  (limit {c['limit']})  {c['note']}")
        for p_ in r.get("problems") or []:
            print(f"  FAIL  {p_}")
        print(f"{r['verdict']} — {os.path.relpath(native_report(a.job, a.title), a.job)}")
        return 0 if r["verdict"] == "PASS" else 1
    if a.cmd == "strip":
        print(options_strip(a.job, a.title, a.plate)); return 0
    if a.cmd == "strip-native":
        r = strip_native(a.job, a.title, a.format, a.organic, [[float(x) for x in s_.split(",")] for s_ in a.avoid])
        for N, o in r["options"].items():
            print(f"  opt{N}: {o['verdict']}" + "".join(f"\n      {c['status']:4} {c['name']:<16} {c['note']}" for c in o.get("checks", [])
                                                        if c["status"] != "PASS") + "".join(f"\n      {x}" for x in o.get("problems", [])))
        print(f"grid {r.get('grid')} · {TITLES}/{a.title}.options.native.json — the owner picks in chat: "
              f"title_card.py pick <job> {a.title} --option N")
        return 0 if any(o["verdict"] == "PASS" for o in r["options"].values()) else 1
    if a.cmd == "check-all":
        bad = 0
        for p in sorted(glob.glob(os.path.join(a.job, TITLES, "*.title.json"))):
            if re.search(r"\.opt\d+\.title\.json$", p):
                continue
            tid = os.path.basename(p)[: -len(".title.json")]
            mov = p[: -len(".title.json")] + ".mov"
            if str(json.load(open(p, encoding="utf-8")).get("engine") or "resolve").lower() == "resolve":
                if not (a.with_ and a.without):
                    print(f"  -     {tid}: made in Resolve — pass --with and --without (render-mp4.py TITLES_OFF)"); bad += 1; continue
                r = measure_native(a.job, tid, a.with_, a.without, a.format)
                print(f"  {r['verdict']:4}  {tid} (resolve)")
                bad += r["verdict"] != "PASS"
                continue
            if not os.path.isfile(mov):
                print(f"  -     {tid}: not rendered"); bad += 1; continue
            r = measure(a.job, tid, mov, a.plate, a.format)
            print(f"  {r['verdict']:4}  {tid}")
            bad += r["verdict"] != "PASS"
        return 1 if bad else 0
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
