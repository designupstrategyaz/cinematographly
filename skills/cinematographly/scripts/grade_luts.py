#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""grade_luts.py — the LUTs the colour doctrine always asked for, built and checked, and the grade plan.

Author, 2026-10-26: *"A: Export look check, B: Per-model correction LUTs, C: Shot consistency, D: Looks per
lane"* and *"Apply all four"* (the council's rule changes; the grade and finish proposal of 2026-10-26 [studio history]).

  fit --model M --still S.png --clip a.mp4 [--clip b.mp4 …] --out DIR [--version N]
        B. A model's correction LUT. The model animates a REAL still (a grey card or chart and skin in
        daylight, own shoot or licensed — never an AI image as a reference) with a locked-off, no-motion
        prompt; what the model did to the colour is measured against the still and inverted: gentle
        monotonic per-channel curves (17 knots) and a 3×3 matrix kept near identity. The last clip given
        is held out to test the fit. Writes <M>_norm_v<N>.cube (33-point) and the same transform as a
        Python body for Resolve's LUT tool, so the file in Resolve is the file that was checked.
  look --kind phone|brand|clean --strength 40..100 [--spec look.json] --out DIR [--name N]
        D. A look with its strength baked into the file (C3: LUTs for colour). `phone` has OPEN shadows
        (C1): a lifted, unclipped toe, a soft highlight shoulder and saturation that eases off on skin and
        near white. `brand` reads a spec (hue shifts, split tone, saturation; skin protected; hue-only
        discipline). `clean` is the identity.
  vignette --stops 0.3 --out DIR
        D. A natural radial falloff as a DCTL: cos⁴ of the field angle, aspect-correct for 9:16, applied in
        linear light; the corner falls by --stops. For drama only (ads keep corners for captions).
  lutcheck --lut X.cube --source frame.png --resolve still.png
        B. Resolve's still of the graded frame against the LUT applied here: mean ΔE ≤ 1.5 [assumed].
  plan <job> [--lane ads|drama] [--look NAME] [--drama-look NAME] [--version N] [--template-drx PATH]
        The grade plan for `resolve-production-console.py` (APPLY_GRADE_PLAN): a colour group per model
        with its LUT on the pre-clip graph; per clip the shot-match CDL and the Deflicker switch (from
        `look_qa.py shots`), the look LUT and texture by shot type (anatomy and product stay clean);
        the drama timeline's vignette and Film Look Creator nodes → 07-edit/grade-plan.json. An ads job whose
        CHECKPOINT lifts `finish-texture` (v2.48.0, project switches) gets the texture node and the vignette as drama
        builds them, named as lifted in the plan (`lifted`) and the printout; Film Look Creator stays drama's.
  --selftest

The API cannot add nodes (PRIMARY · the API stubs), so the template DRX carries them; see
`editing-and-audio.md`, the grade template.
"""
from __future__ import annotations
import argparse, colorsys, datetime as dt, glob, json, math, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LUT_SIZE = 33
LUT_PREFIX = "MCP/cine_"     # Resolve's LUT tool writes only directly inside LUT/MCP (measured 2026-10-26), so names carry the prefix
KNOTS = 17
GENTLE = 0.35          # how far the fitted curves are pulled back toward identity [assumed]
MATRIX_RIDGE = 0.5     # ridge weight keeping the 3×3 near identity [assumed]
LUTCHECK_DE = 1.5      # [assumed]
SKIN_HUE = (8.0, 50.0)  # degrees in HSV hue where skin sits; saturation eases off there [practitioner]
# the template's node indices (the DRX carries them; the API can only switch them)
NODE_MAP = {"clip": {"shot_match": 1, "deflicker": 2, "look": 3, "texture": 4},
            "timeline": {"vignette": 1, "film_look": 2}}
PROFILES = {   # shot type → what the clip's nodes do, per lane (C1–C4 applied)
    "ads": {"talking_head": {"look": True, "texture": False}, "broll": {"look": True, "texture": False},
            "product": {"look": False, "texture": False}, "anatomy": {"look": False, "texture": False},
            "clean": {"look": False, "texture": False}},
    "drama": {"talking_head": {"look": True, "texture": True}, "broll": {"look": True, "texture": True},
              "product": {"look": True, "texture": False}, "anatomy": {"look": False, "texture": False},
              "clean": {"look": False, "texture": False}}}


def _np():
    import numpy as np
    return np


# =================================================================================================
# .cube I/O, application
# =================================================================================================
def compile_body(body: str):
    src = "def _f(r, g, b):\n" + "\n".join("    " + ln for ln in body.splitlines())
    ns: dict = {"math": math, "colorsys": colorsys}
    exec(compile(src, "<lut-body>", "exec"), ns)
    return ns["_f"]


def write_cube(path: str, body: str, size: int = LUT_SIZE, title: str = "") -> None:
    f = compile_body(body)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f'TITLE "{title or os.path.basename(path)}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        n = size - 1
        for bi in range(size):                 # .cube order: red fastest, then green, then blue
            for gi in range(size):
                for ri in range(size):
                    o = f(ri / n, gi / n, bi / n)
                    fh.write(f"{o[0]:.6f} {o[1]:.6f} {o[2]:.6f}\n")
    with open(os.path.splitext(path)[0] + ".body.py", "w", encoding="utf-8") as fh:
        fh.write(body + "\n")


def read_cube(path: str):
    np = _np()
    size, rows = None, []
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if ln.startswith("LUT_3D_SIZE"):
            size = int(ln.split()[1])
        elif ln and (ln[0].isdigit() or ln[0] in "-."):
            rows.append([float(v) for v in ln.split()[:3]])
    t = np.array(rows, np.float64).reshape(size, size, size, 3)   # [b][g][r]
    return size, t


def apply_lut(img, table):
    """img uint8 or float 0..1 RGB; trilinear."""
    np = _np()
    x = img.astype(np.float64) / (255.0 if img.dtype == np.uint8 else 1.0)
    n = table.shape[0] - 1
    p = np.clip(x, 0, 1) * n
    i0 = np.minimum(np.floor(p).astype(int), n - 1)
    f = p - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    out = 0
    for db in (0, 1):
        for dg in (0, 1):
            for dr in (0, 1):
                w = (fr if dr else 1 - fr) * (fg if dg else 1 - fg) * (fb if db else 1 - fb)
                out = out + w * table[b0 + db, g0 + dg, r0 + dr]
    return np.clip(out, 0, 1)


# =================================================================================================
# B. fit a model's correction
# =================================================================================================
def _pairs(still, clips, fps=4.0, width=160):
    """(clip pixel, still pixel) pairs, 0..1, from locked-off renders of the still."""
    np = _np()
    import look_qa as LQ
    import shot_graph as SG
    _, cv2 = SG._need()
    tgt = still.astype(np.float64) / 255.0
    out = []
    for c in clips:
        fr = LQ.rgb_frames(c, fps, width)
        fs = [cv2.resize(f, (tgt.shape[1], tgt.shape[0]), interpolation=cv2.INTER_AREA).astype(np.float64) / 255.0
              for t, f in fr if t >= 0.2]
        if not fs:
            continue
        m = np.mean(fs, axis=0)
        # a small blur on both sides tolerates a pixel of drift
        k = (5, 5)
        out.append((cv2.GaussianBlur(m, k, 0).reshape(-1, 3), cv2.GaussianBlur(tgt, k, 0).reshape(-1, 3)))
    return out


def fit_params(pairs) -> dict:
    np = _np()
    src = np.concatenate([a for a, _ in pairs]); dst = np.concatenate([b for _, b in pairs])
    xs = np.linspace(0, 1, KNOTS)
    curves = []
    for ch in range(3):
        ys = []
        for k, x in enumerate(xs):
            lo, hi = x - 0.5 / (KNOTS - 1), x + 0.5 / (KNOTS - 1)
            m = (src[:, ch] >= lo) & (src[:, ch] < hi)
            ys.append(float(np.median(dst[m, ch])) if m.sum() >= 20 else None)
        known = [(x, y) for x, y in zip(xs, ys) if y is not None]
        if len(known) < 2:
            ys = list(xs)
        else:
            kx, ky = zip(*known)
            ys = list(np.interp(xs, kx, ky, left=None, right=None))
            # outside the measured range, run parallel to identity from the last measured knot
            for i, x in enumerate(xs):
                if x < kx[0]:
                    ys[i] = ky[0] - (kx[0] - x)
                elif x > kx[-1]:
                    ys[i] = ky[-1] + (x - kx[-1])
        ys = [(1 - GENTLE) * y + GENTLE * x for x, y in zip(xs, ys)]          # gentle
        ys = list(np.maximum.accumulate(np.clip(ys, 0, 1)))                  # monotonic
        curves.append([round(float(v), 5) for v in ys])
    # the 3×3 on the curve-corrected values, ridge-pulled toward identity
    c = np.stack([np.interp(src[:, ch], xs, curves[ch]) for ch in range(3)], axis=1)
    A = c.T @ c + MATRIX_RIDGE * len(c) / 100 * np.eye(3)
    B = c.T @ dst + MATRIX_RIDGE * len(c) / 100 * np.eye(3)
    M = np.linalg.solve(A, B).T
    return {"curves": curves, "matrix": [[round(float(v), 5) for v in row] for row in M]}


def fit_body(p: dict) -> str:
    return "\n".join([
        f"YR = {p['curves'][0]}", f"YG = {p['curves'][1]}", f"YB = {p['curves'][2]}", f"M = {p['matrix']}",
        f"N = {KNOTS - 1}",
        "def interp(v, ys):",
        "    if v <= 0.0: return ys[0]",
        "    if v >= 1.0: return ys[-1]",
        "    i = int(v * N); f = v * N - i",
        "    return ys[i] * (1.0 - f) + ys[i + 1] * f",
        "c = (interp(r, YR), interp(g, YG), interp(b, YB))",
        "o = [M[k][0] * c[0] + M[k][1] * c[1] + M[k][2] * c[2] for k in range(3)]",
        "return (min(1.0, max(0.0, o[0])), min(1.0, max(0.0, o[1])), min(1.0, max(0.0, o[2])))"])


def fit(model: str, still_path: str, clips: list, out: str, version: int = 1) -> dict:
    np = _np()
    import look_qa as LQ
    still = LQ._read_still(still_path, 160)
    if still is None:
        raise SystemExit(f"error: cannot read {still_path}")
    pairs = _pairs(still, clips)
    if not pairs:
        raise SystemExit("error: no frames read from the clips")
    train, held = (pairs[:-1], pairs[-1:]) if len(pairs) > 1 else (pairs, pairs)
    p = fit_params(train)
    name = f"{model}_norm_v{version}"
    cube = os.path.join(out, "cine_" + name + ".cube")
    body = fit_body(p)
    write_cube(cube, body, title=f"{model} normalisation v{version}")
    _, t = read_cube(cube)
    ev = lambda prs, lut: float(np.mean([LQ.de(LQ.to_lab((apply_lut(a.reshape(-1, 1, 3), t) if lut else a.reshape(-1, 1, 3)) * 255),
                                               LQ.to_lab(b.reshape(-1, 1, 3) * 255)) for a, b in prs]))
    mono = all(all(c[i] <= c[i + 1] + 1e-9 for i in range(len(c) - 1)) for c in p["curves"])
    rep = {"model": model, "version": version, "cube": cube, "resolve_path": LUT_PREFIX + name + ".cube",
           "still": still_path, "clips": clips, "params": p, "monotonic": mono,
           "de_fit_before": round(ev(train, False), 2), "de_fit_after": round(ev(train, True), 2),
           "de_heldout_before": round(ev(held, False), 2), "de_heldout_after": round(ev(held, True), 2),
           "made": dt.datetime.now().isoformat(timespec="minutes")}
    rep["ok"] = mono and rep["de_heldout_after"] < rep["de_heldout_before"]
    json.dump(rep, open(os.path.join(out, "cine_" + name + ".fit.json"), "w"), indent=1)
    return rep


# =================================================================================================
# D. looks with the strength baked in
# =================================================================================================
def look_body(kind: str, strength: float, spec: dict | None = None) -> str:
    k = max(0.0, min(1.0, strength / 100.0 if strength > 1 else strength))
    spec = spec or {}
    if kind == "clean":
        return "return (r, g, b)"
    common = ["import colorsys", f"K = {k}", f"SKIN = {list(SKIN_HUE)}",
              "def skin_w(h):",
              "    d = h * 360.0",
              "    return 1.0 if SKIN[0] <= d <= SKIN[1] else 0.0"]
    if kind == "phone":
        # C1: open shadows — the toe lifts to 3 % and never clips; a soft shoulder from 0.78; +10 % saturation
        # that eases to +3 % on skin and fades out near black and white
        body = common + [
            "TOE = 0.03; MID = 0.45; C = 1.12; KNEE = 0.78",
            "def tone(x):",
            "    y = MID + (x - MID) * C",
            "    if y > KNEE: y = KNEE + (1.0 - KNEE) * math.tanh((y - KNEE) / (1.0 - KNEE))",
            "    y = max(0.0, min(1.0, y))",
            "    return TOE + (1.0 - TOE) * y",
            "lo = tone(0.0); hi = tone(1.0)",
            "t = [(tone(v) - lo) / (hi - lo) * (1.0 - TOE) + TOE for v in (r, g, b)]",
            "h, s, v = colorsys.rgb_to_hsv(*t)",
            "boost = 1.10 - 0.07 * skin_w(h)",
            "edge = min(1.0, v / 0.15) * min(1.0, (1.0 - v) / 0.1 + 0.2)",
            "s = min(1.0, s * (1.0 + (boost - 1.0) * edge))",
            "o = colorsys.hsv_to_rgb(h, s, v)",
            "return tuple(min(1.0, max(0.0, a + K * (b2 - a))) for a, b2 in zip((r, g, b), o))"]
        return "\n".join(body)
    if kind == "brand":
        shifts = spec.get("hue_shifts") or []          # [{"from": deg, "to": deg, "width": deg}]
        split = spec.get("split_tone") or {}           # {"shadows": {"hue": deg, "amount": 0.03}, "highlights": {...}}
        sat = float(spec.get("saturation", 1.0))
        body = common + [
            f"SHIFTS = {[(float(x['from']), float(x['to']), float(x.get('width', 25))) for x in shifts]}",
            f"SH = {split.get('shadows') or {}}; HL = {split.get('highlights') or {}}; SAT = {sat}",
            "h, s, v = colorsys.rgb_to_hsv(r, g, b)",
            "d = h * 360.0",
            "protect = 1.0 - skin_w(h)",
            "for f, to, w in SHIFTS:",
            "    dist = min(abs(d - f), 360.0 - abs(d - f))",
            "    wt = math.exp(-0.5 * (dist / (w / 2.0)) ** 2) * protect",
            "    delta = ((to - f + 180.0) % 360.0) - 180.0",
            "    d = (d + delta * wt) % 360.0",
            "s = min(1.0, s * (1.0 + (SAT - 1.0) * protect))",
            "o = list(colorsys.hsv_to_rgb(d / 360.0, s, v))",
            "for tone, wfun in ((SH, lambda y: (1.0 - y) ** 2), (HL, lambda y: y ** 2)):",
            "    if tone:",
            "        tr, tg, tb = colorsys.hsv_to_rgb(tone['hue'] / 360.0, 1.0, 1.0)",
            "        y = 0.2126 * o[0] + 0.7152 * o[1] + 0.0722 * o[2]",
            "        a = tone.get('amount', 0.03) * wfun(y) * protect",
            "        o = [o[0] + a * (tr - 0.5), o[1] + a * (tg - 0.5), o[2] + a * (tb - 0.5)]",
            "return tuple(min(1.0, max(0.0, a0 + K * (b0 - a0))) for a0, b0 in zip((r, g, b), o))"]
        return "\n".join(body)
    raise SystemExit(f"error: unknown look kind {kind!r}")


def make_look(kind: str, strength: float, out: str, name: str | None = None, spec: dict | None = None) -> dict:
    k = int(round(strength if strength > 1 else strength * 100))
    name = name or f"{kind}_{k}"
    cube = os.path.join(out, "cine_" + name + ".cube")
    write_cube(cube, look_body(kind, strength, spec), title=f"{kind} look at {k} %")
    return {"cube": cube, "resolve_path": LUT_PREFIX + name + ".cube", "kind": kind, "strength": k}


# =================================================================================================
# D. the vignette DCTL
# =================================================================================================
def vignette_dctl(stops: float = 0.3) -> str:
    return f"""// cinematographly · natural vignette: cos^4 of the field angle, aspect-correct, in linear light.
// The corner falls by `Corner stops`; the centre is untouched. Drama only (ads keep corners for captions).
DEFINE_UI_PARAMS(stops, Corner stops, DCTLUI_SLIDER_FLOAT, {stops:.2f}, 0.0, 1.5, 0.01)

__DEVICE__ float3 transform(int p_Width, int p_Height, int p_X, int p_Y, float p_R, float p_G, float p_B)
{{
    float w = (float)p_Width;
    float h = (float)p_Height;
    float cx = ((float)p_X + 0.5f) / w - 0.5f;
    float cy = (((float)p_Y + 0.5f) / h - 0.5f) * (h / w);
    float r2 = cx * cx + cy * cy;
    float rc2 = 0.25f + 0.25f * (h / w) * (h / w);
    float c4 = _powf(2.0f, -stops);
    float cosc = _powf(c4, 0.25f);
    float tanc2 = 1.0f / (cosc * cosc) - 1.0f;
    float t2 = tanc2 * r2 / rc2;
    float gain = 1.0f / ((1.0f + t2) * (1.0f + t2));
    float R = _powf(_fmaxf(p_R, 0.0f), 2.4f) * gain;
    float G = _powf(_fmaxf(p_G, 0.0f), 2.4f) * gain;
    float B = _powf(_fmaxf(p_B, 0.0f), 2.4f) * gain;
    return make_float3(_powf(R, 1.0f / 2.4f), _powf(G, 1.0f / 2.4f), _powf(B, 1.0f / 2.4f));
}}
"""


def vignette_gain(x: float, y: float, w: int, h: int, stops: float) -> float:
    """The DCTL's gain, in Python, for checks."""
    cx = (x + 0.5) / w - 0.5
    cy = ((y + 0.5) / h - 0.5) * (h / w)
    r2 = cx * cx + cy * cy
    rc2 = 0.25 + 0.25 * (h / w) ** 2
    c4 = 2.0 ** -stops
    cosc = c4 ** 0.25
    t2 = (1.0 / (cosc * cosc) - 1.0) * r2 / rc2
    return 1.0 / ((1.0 + t2) ** 2)


# =================================================================================================
# the grade plan
# =================================================================================================
def _fm(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    txt = open(path, encoding="utf-8").read()
    if not txt.startswith("---"):
        return {}
    out = {}
    for ln in txt.split("---", 2)[1].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*?)\s*(?:#.*)?$", ln)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def shot_type(fm: dict) -> str:
    g = (fm.get("grade") or "").strip().lower()
    if g in ("talking_head", "broll", "product", "anatomy", "clean"):
        return g
    t = (fm.get("type") or "").lower()
    return "talking_head" if t in ("dialogue", "reaction") else "broll"


def plan(job: str, lane: str = "ads", look: str | None = None, drama_look: str | None = None, version: int = 1,
         template_drx: str | None = None, vignette: bool = False, film_look: bool = False,
         timeline_drx: str | None = None) -> dict:
    import motion_qa as MQ
    import switches as SW
    shots_p = os.path.join(job, "09-qa", "look", "shots.json")
    looks = {r["shot"]: r for r in (json.load(open(shots_p, encoding="utf-8")).get("shots", []) if os.path.isfile(shots_p) else [])}
    prompts = os.path.join(job, "01-script", "prompts")
    groups, clips, missing = {}, {}, []
    # (v2.48.0, project switch finish-texture) C2 keeps the texture node and the vignette out of ads; a job that lifts it
    # gets them as the drama lane builds them (texture on people and b-roll, the vignette with --vignette). Product,
    # anatomy and clean shots stay clean, and Film Look Creator on the timeline stays drama's.
    ft = SW.on(job, "finish-texture") if lane == "ads" else None
    textured = []
    for s in MQ.selected_shots(job):
        rp = os.path.join(job, "09-qa", "motion", f"{s}.motion.json")
        try:
            f = json.load(open(rp, encoding="utf-8")).get("file")
        except (OSError, ValueError):
            missing.append(f"{s}: no motion report"); continue
        fm = _fm(os.path.join(prompts, f"{s}.clip.prompt.md"))
        model = (fm.get("model") or "unknown").strip()
        gname = f"MODEL {model}"
        groups.setdefault(gname, {"model": model, "pre_lut": LUT_PREFIX + f"{model}_norm_v{version}.cube"})
        st = shot_type(fm)
        prof = PROFILES[lane][st]
        L = looks.get(s) or {}
        cdl = (L.get("cdl") or {}) if (L.get("cdl") or {}).get("apply") else None
        lut = (drama_look if lane == "drama" else look)
        tex = prof["texture"] or bool(ft and PROFILES["drama"][st]["texture"])  # (v2.48.0, project switch finish-texture)
        clips[os.path.basename(f)] = {"shot": s, "group": gname, "profile": st,
                                      "look_lut": (LUT_PREFIX + lut + ".cube") if (lut and prof["look"]) else None,
                                      "nodes": {"shot_match": bool(cdl), "deflicker": bool(L.get("deflicker")),
                                                "look": bool(lut and prof["look"]), "texture": tex},
                                      "cdl": cdl}
        if tex and not prof["texture"]:
            textured.append(os.path.basename(f))
        if not L:
            missing.append(f"{s}: no look_qa.py shots row — CDL and Deflicker left off")
    # the vignette: drama's, and an ads job's only when it lifts finish-texture (v2.48.0, project switch finish-texture)
    P = {"job": os.path.basename(os.path.abspath(job)), "lane": lane, "made": dt.datetime.now().isoformat(timespec="minutes"),
         "template_drx": template_drx, "timeline_drx": timeline_drx, "node_map": NODE_MAP, "groups": groups, "clips": clips,
         "timeline": {"vignette": bool(vignette and (lane == "drama" or ft)), "film_look": bool(film_look and lane == "drama")},
         "notes": missing}
    if ft:                                # (v2.48.0, project switch finish-texture) the lift, named in the plan itself
        P["lifted"] = {"finish-texture": {
            "rule": "grade-finish C2: ads get no texture node, no bloom, no grain and no vignette",
            "lifted": SW.lifted("finish-texture", ft), "texture": sorted(textured), "vignette": bool(vignette),
            "still_holds": "skin protection, the look's strength, look_qa export; product, anatomy and clean shots stay "
                           "clean; Film Look Creator on the timeline is drama's"}}
    d = os.path.join(job, "07-edit"); os.makedirs(d, exist_ok=True)
    json.dump(P, open(os.path.join(d, "grade-plan.json"), "w", encoding="utf-8"), indent=1)
    return P


CONSOLE = os.path.join(HERE, "resolve-production-console.py")
GRADE_COPY = "resolve-production-console.grade.py"


def console_copy(job: str, P: dict) -> str:
    """A grade-only copy of the ONE production console script (never a script of its own): GRADE_PLAN
    spliced in, APPLY_GRADE_PLAN on, the track, lane and marker steps off, so it can be run again after
    a re-plan without re-adding anything. Written beside detect_beats.py's copy, not over it."""
    src = open(CONSOLE, encoding="utf-8").read()
    pairs = [("GRADE_PLAN = {}  # __GRADE_PLAN__", "GRADE_PLAN = " + repr(P) + "  # __GRADE_PLAN__"),
             ("\nAPPLY_GRADE_PLAN = False", "\nAPPLY_GRADE_PLAN = True"),
             ("\nADD_BEAT_MARKERS = True", "\nADD_BEAT_MARKERS = False"),
             ("\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False"),
             ("\nENSURE_AUDIO_LANES = True", "\nENSURE_AUDIO_LANES = False")]
    for old, new in pairs:
        if old not in src:
            raise RuntimeError(f"resolve-production-console.py no longer contains {old!r} — update console_copy()")
        src = src.replace(old, new, 1)
    src = src.replace('"""\nDaVinci Resolve — the ONE production/editing-setup console script',
                      f'"""\nFilled in by grade_luts.py plan ({P.get("lane")}, {len(P.get("clips", {}))} clips, '
                      f'{P.get("made")}): the grade only.\n\nDaVinci Resolve — the ONE production/editing-setup console script', 1)
    out = os.path.join(job, "07-edit", GRADE_COPY)
    open(out, "w", encoding="utf-8").write(src)
    return out


# =================================================================================================
# selftest
# =================================================================================================
def selftest() -> int:
    np = _np()
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and cond
    import look_qa as LQ
    import shot_graph as SG
    _, cv2 = SG._need()
    with tempfile.TemporaryDirectory() as td:
        # a chart: grey ramp + skin-ish and colour patches
        H, W = 160, 90
        chart = np.zeros((H, W, 3), np.uint8)
        for i in range(8):
            chart[i * 20:(i + 1) * 20, :45] = int(20 + i * 30)
        cols = [(200, 150, 125), (170, 120, 95), (120, 80, 60), (60, 120, 200), (80, 170, 80), (210, 60, 60), (230, 210, 80), (120, 120, 120)]
        for i, c in enumerate(cols):
            chart[i * 20:(i + 1) * 20, 45:] = c
        sp = os.path.join(td, "chart.png"); cv2.imwrite(sp, cv2.cvtColor(chart, cv2.COLOR_RGB2BGR))

        def model_render(path, seed):
            rng = np.random.default_rng(seed)
            x = chart.astype(np.float64) / 255.0
            y = np.clip(x ** np.array([0.92, 1.0, 1.08]) * np.array([1.06, 1.0, 0.9]) + 0.02, 0, 1)   # a warm, lifted model
            frames = [np.clip(y * 255 + rng.standard_normal(y.shape) * 1.5, 0, 255) for _ in range(24)]
            LQ._encode(path, frames)
        clips = []
        for k in range(3):
            c = os.path.join(td, f"m{k}.mp4"); model_render(c, k); clips.append(c)
        rep = fit("testmodel", sp, clips, td)
        check("a model's colour is fitted from its renders of a real still, and the held-out render comes closer",
              rep["ok"] and rep["de_heldout_after"] < rep["de_heldout_before"] - 2, json.dumps({k: rep[k] for k in rep if k.startswith("de_")}))
        check("the fitted curves are monotonic", rep["monotonic"])
        size, t = read_cube(rep["cube"])
        f = compile_body(open(os.path.splitext(rep["cube"])[0] + ".body.py").read())
        pt = (0.3, 0.6, 0.2)
        ri, gi, bi = (round(v * (size - 1)) for v in pt)
        check("the .cube and the body sent to Resolve are the same transform",
              np.allclose(t[bi, gi, ri], f(ri / (size - 1), gi / (size - 1), bi / (size - 1)), atol=1e-5))
        # looks
        ph = make_look("phone", 60, td)
        _, tp = read_cube(ph["cube"])
        black = tp[0, 0, 0]
        check("the phone look keeps shadows open (C1): black maps above 0, nothing is crushed",
              black.min() > 0.005 and black.max() < 0.05, str(black))
        skin = np.array([[[200, 150, 125]]], np.uint8); blue = np.array([[[60, 120, 200]]], np.uint8)
        sat = lambda px: colorsys.rgb_to_hsv(*px.reshape(3))[1]
        ds = sat(apply_lut(skin, tp)) - sat(skin / 255.0); db = sat(apply_lut(blue, tp)) - sat(blue / 255.0)
        check("…and lifts saturation less on skin than on other colours", ds < db, f"{ds} vs {db}")
        ph100 = make_look("phone", 100, td)
        _, t100 = read_cube(ph100["cube"])
        idv = np.linspace(0, 1, size)
        ident = np.stack(np.meshgrid(idv, idv, idv, indexing="ij")[::-1], axis=-1)
        check("the strength is baked in: 60 % sits 60 % of the way from identity to the full look",
              np.allclose(tp, ident + 0.6 * (t100 - ident), atol=2e-3))
        br = make_look("brand", 100, td, "brand_test", {"hue_shifts": [{"from": 120, "to": 160, "width": 40}], "saturation": 1.1})
        _, tb = read_cube(br["cube"])
        green = np.array([[[60, 200, 60]]], np.uint8)
        hg = colorsys.rgb_to_hsv(*apply_lut(green, tb).reshape(3))[0] * 360
        check("a brand look moves its hue (green toward teal) and leaves skin's hue alone",
              hg > 125 and abs(colorsys.rgb_to_hsv(*apply_lut(skin, tb).reshape(3))[0] - colorsys.rgb_to_hsv(*(skin / 255.0).reshape(3))[0]) < 0.01,
              str(hg))
        cl = make_look("clean", 100, td)
        _, tc = read_cube(cl["cube"])
        check("clean is the identity", np.allclose(tc, ident, atol=1e-6))
        # lutcheck: a Resolve still made with the LUT passes, one made without it fails
        src = chart
        graded = (apply_lut(src, tp) * 255).round().astype(np.uint8)
        check("lutcheck: Resolve's still matches the LUT applied here", lutcheck_arrays(tp, src, graded)["ok"])
        check("lutcheck: a still without the LUT is caught", not lutcheck_arrays(tp, src, src)["ok"])
        # vignette
        g0 = vignette_gain(539.5, 959.5, 1080, 1920, 0.3); gc = vignette_gain(0, 0, 1080, 1920, 0.3)
        check("the vignette leaves the centre alone and drops the corner by the stops asked",
              abs(g0 - 1) < 1e-3 and abs(math.log2(gc) + 0.3) < 0.02, f"{g0} {gc}")
        gm = vignette_gain(0, 959.5, 1080, 1920, 0.3); gt = vignette_gain(539.5, 0, 1080, 1920, 0.3)
        check("…radially and aspect-correct (the top edge, further away in 9:16, falls more than the side)", gt < gm < 1)
        check("the DCTL source carries the parameter and the cos⁴ law", "DEFINE_UI_PARAMS(stops" in vignette_dctl(0.3)
              and "(1.0f + t2) * (1.0f + t2)" in vignette_dctl(0.3))
        # the plan
        job = os.path.join(td, "job")
        for d in ("01-script/prompts", "09-qa/motion", "09-qa/look"):
            os.makedirs(os.path.join(job, d))
        open(os.path.join(job, "09-qa", "QA-LOG.md"), "w").write(
            "| when | shot | gate | verdict | observation |\n|---|---|---|---|---|\n| t | S1 | selects | SELECT | x |\n"
            "| t | S2 | selects | SELECT | x |\n| t | S3 | selects | SELECT | x |\n")
        for s_, model, typ, extra in (("S1", "kling3_0", "dialogue", ""), ("S2", "seedance_2_5", "broll", ""),
                                      ("S3", "kling3_0", "insert", "grade: product\n")):
            open(os.path.join(job, "01-script", "prompts", f"{s_}.clip.prompt.md"), "w").write(
                f"---\nshot: {s_}\nkind: clip\ntype: {typ}\nmodel: {model}\n{extra}---\n[MOTION]\nx\n")
            json.dump({"shot": s_, "file": f"03-clips/{s_}_v1.mp4"}, open(os.path.join(job, "09-qa", "motion", f"{s_}.motion.json"), "w"))
        json.dump({"shots": [{"shot": "S1", "cdl": {"apply": True, "slope": [0.95, 1, 1.05], "offset": [0, 0, 0], "power": [1, 1, 1],
                                                     "sat": 1.0}, "deflicker": True},
                             {"shot": "S2", "cdl": {"apply": False}, "deflicker": False}]},
                  open(os.path.join(job, "09-qa", "look", "shots.json"), "w"))
        P = plan(job, "ads", look="phone_60")
        c = P["clips"]
        check("the plan groups clips by model with that model's LUT on the pre-clip graph",
              set(P["groups"]) == {"MODEL kling3_0", "MODEL seedance_2_5"}
              and P["groups"]["MODEL kling3_0"]["pre_lut"] == LUT_PREFIX + "kling3_0_norm_v1.cube")
        check("S1 gets its shot-match CDL and Deflicker; S2 gets neither",
              c["S1_v1.mp4"]["nodes"]["shot_match"] and c["S1_v1.mp4"]["nodes"]["deflicker"]
              and not c["S2_v1.mp4"]["nodes"]["shot_match"] and not c["S2_v1.mp4"]["nodes"]["deflicker"])
        check("a product shot stays clean: no look, no texture", c["S3_v1.mp4"]["profile"] == "product"
              and not c["S3_v1.mp4"]["nodes"]["look"] and c["S3_v1.mp4"]["look_lut"] is None)
        check("ads never get texture (C2), vignette or Film Look Creator",
              not any(x["nodes"]["texture"] for x in c.values()) and not P["timeline"]["vignette"])
        Pd = plan(job, "drama", drama_look="drama_70", vignette=True, film_look=True)
        check("drama gets texture on people and b-roll, the vignette and Film Look Creator",
              Pd["clips"]["S1_v1.mp4"]["nodes"]["texture"] and Pd["timeline"]["vignette"] and Pd["timeline"]["film_look"])
        cp = console_copy(job, P)
        src = open(cp, encoding="utf-8").read()
        ns: dict = {}
        exec(compile(src.split("resolve = app.GetResolve()")[0], cp, "exec"), ns)      # the CONFIG block only
        check("the console copy carries the plan, grade on, every other step off",
              ns["APPLY_GRADE_PLAN"] and ns["GRADE_PLAN"] == P and not ns["ADD_BEAT_MARKERS"]
              and not ns["ENSURE_BROLL_TRACK"] and not ns["ENSURE_AUDIO_LANES"])
        # (v2.48.0, project switch finish-texture) off → ads stay bare; on → texture and the vignette, named as lifted;
        # on, outside what it allows → product stays clean and Film Look Creator stays drama's
        Pv = plan(job, "ads", look="phone_60", vignette=True, film_look=True)
        check("finish-texture off: ads get no texture and no vignette even when asked, and the plan names no lift",
              not any(x["nodes"]["texture"] for x in Pv["clips"].values()) and not Pv["timeline"]["vignette"]
              and "lifted" not in Pv, json.dumps(Pv["timeline"]))
        cp_ = os.path.join(job, "00-brief", "CHECKPOINT.md")
        os.makedirs(os.path.dirname(cp_), exist_ok=True)
        open(cp_, "w").write("Job:        gl-1\nSwitches:   finish-texture — a film look agreed with the client for this launch\n")
        Pt = plan(job, "ads", look="phone_60", vignette=True, film_look=True)
        lt = (Pt.get("lifted") or {}).get("finish-texture") or {}
        check("finish-texture on: ads get texture on people and b-roll and the vignette, the lift named in the plan",
              Pt["clips"]["S1_v1.mp4"]["nodes"]["texture"] and Pt["clips"]["S2_v1.mp4"]["nodes"]["texture"]
              and Pt["timeline"]["vignette"] and lt.get("texture") == ["S1_v1.mp4", "S2_v1.mp4"] and lt.get("vignette")
              and "lifted by project switch `finish-texture` (a film look agreed" in lt.get("lifted", ""),
              json.dumps(Pt.get("lifted")))
        check("finish-texture on, outside what it allows: the product shot stays clean, Film Look Creator stays drama's",
              not Pt["clips"]["S3_v1.mp4"]["nodes"]["texture"] and not Pt["clips"]["S3_v1.mp4"]["nodes"]["look"]
              and not Pt["timeline"]["film_look"], json.dumps([Pt["clips"]["S3_v1.mp4"], Pt["timeline"]]))
        Pn = plan(job, "ads", look="phone_60")
        check("finish-texture on, no --vignette: the texture only", not Pn["timeline"]["vignette"]
              and Pn["clips"]["S1_v1.mp4"]["nodes"]["texture"] and Pn["lifted"]["finish-texture"]["vignette"] is False)
        Pd2 = plan(job, "drama", drama_look="drama_70", vignette=True)
        check("a drama plan in the same job is as before and names no lift", "lifted" not in Pd2
              and Pd2["clips"]["S1_v1.mp4"]["nodes"]["texture"] and not Pd2["clips"]["S3_v1.mp4"]["nodes"]["texture"])
        cpt = console_copy(job, Pt)
        ns2: dict = {}
        exec(compile(open(cpt, encoding="utf-8").read().split("resolve = app.GetResolve()")[0], cpt, "exec"), ns2)
        check("the console copy carries the lifted ads plan as it is", ns2["GRADE_PLAN"] == Pt)
    print("-" * 60)
    print("selftest OK — a model fitted from renders of a real still (held-out ΔE down, monotonic), the cube and the "
          "Resolve body identical, the phone look's open shadows and skin-eased saturation, baked strength, a brand "
          "hue shift that spares skin, clean = identity, lutcheck both ways, the cos⁴ vignette, and the grade plan "
          "(groups per model, CDL and Deflicker per shot, clean product, no texture in ads, drama nodes, the console copy), "
          "and the project switch finish-texture (ads texture and vignette, named as lifted; product clean)"
          if ok else "selftest FAILED")
    return 0 if ok else 1


def lutcheck_arrays(table, source, resolve_still) -> dict:
    import look_qa as LQ
    np = _np()
    mine = apply_lut(source, table) * 255
    d = LQ.de(LQ.to_lab(mine), LQ.to_lab(resolve_still.astype(np.float64)))
    return {"de": round(d, 2), "ok": d <= LUTCHECK_DE}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fit"); f.add_argument("--model", required=True); f.add_argument("--still", required=True)
    f.add_argument("--clip", action="append", required=True); f.add_argument("--out", required=True)
    f.add_argument("--version", type=int, default=1)
    lk = sub.add_parser("look"); lk.add_argument("--kind", choices=["phone", "brand", "clean"], required=True)
    lk.add_argument("--strength", type=float, default=60); lk.add_argument("--spec"); lk.add_argument("--out", required=True)
    lk.add_argument("--name")
    v = sub.add_parser("vignette"); v.add_argument("--stops", type=float, default=0.3); v.add_argument("--out", required=True)
    c = sub.add_parser("lutcheck"); c.add_argument("--lut", required=True); c.add_argument("--source", required=True)
    c.add_argument("--resolve", required=True)
    p = sub.add_parser("plan"); p.add_argument("job"); p.add_argument("--lane", choices=["ads", "drama"], default="ads")
    p.add_argument("--look"); p.add_argument("--drama-look"); p.add_argument("--version", type=int, default=1)
    p.add_argument("--template-drx"); p.add_argument("--timeline-drx")
    p.add_argument("--vignette", action="store_true"); p.add_argument("--film-look", action="store_true")
    p.add_argument("--console", action="store_true", help="also write 07-edit/" + GRADE_COPY)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "fit":
        r = fit(a.model, a.still, a.clip, a.out, a.version)
        print(f"{r['cube']} → Resolve path {r['resolve_path']} · ΔE held-out {r['de_heldout_before']} → {r['de_heldout_after']} · "
              f"monotonic {r['monotonic']} · {'OK' if r['ok'] else 'NOT OK — do not install'}")
        print(f"Install: send the .body.py text to Resolve's LUT tool as {os.path.basename(r['cube'])} (size 33).")
        return 0 if r["ok"] else 1
    if a.cmd == "look":
        r = make_look(a.kind, a.strength, a.out, a.name, json.load(open(a.spec)) if a.spec else None)
        print(f"{r['cube']} → Resolve path {r['resolve_path']} ({r['kind']} at {r['strength']} %)"); return 0
    if a.cmd == "vignette":
        os.makedirs(a.out, exist_ok=True)
        pth = os.path.join(a.out, "cine_vignette.dctl"); open(pth, "w").write(vignette_dctl(a.stops))
        print(f"{pth} — install with Resolve's DCTL tool (it compiles first) as cine_vignette.dctl"); return 0
    if a.cmd == "lutcheck":
        import look_qa as LQ
        _, t = read_cube(a.lut)
        src, res = LQ._read_still(a.source, 320), LQ._read_still(a.resolve, 320)
        r = lutcheck_arrays(t, src, res)
        print(f"ΔE {r['de']} — {'OK' if r['ok'] else 'Resolve did not apply this LUT as built'}"); return 0 if r["ok"] else 1
    if a.cmd == "plan":
        r = plan(a.job, a.lane, a.look, a.drama_look, a.version, a.template_drx, a.vignette, a.film_look,
                 a.timeline_drx)
        print(f"07-edit/grade-plan.json: {len(r['groups'])} group(s), {len(r['clips'])} clip(s)")
        for x in (r.get("lifted") or {}).values():          # (v2.48.0, project switch finish-texture)
            print(f"  i {x['rule']} — {x['lifted']}: texture on {len(x['texture'])} clip(s)"
                  + (f" ({', '.join(x['texture'])})" if x["texture"] else "")
                  + (", the vignette on" if x["vignette"] else ", no vignette (pass --vignette for one)"))
        if a.console:
            print(f"{os.path.relpath(console_copy(a.job, r), a.job)} — send it whole as the run_script script "
                  f"(or paste it into the console) with the cut's timeline open")
        for n in r["notes"]:
            print(f"  ! {n}")
        return 0
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
