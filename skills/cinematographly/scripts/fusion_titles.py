#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""fusion_titles.py — the brand's Fusion titles, GENERATED from the approved title card (the native-elements
rule: Resolve's or Fusion's own elements by default; since v2.45 a title is never a movie made outside and imported).

Why it exists: the native route lost to the outside one because nothing could make the approved LOOK in Resolve —
PLACE_TITLES wrote static Text+ inputs (no entrance or exit, no plate, the weight never a Style), and the "brand
template keyed once" was a manual job nobody did (the author's research notes §1.2 C-A, C-B). So this
writes the template from the card, every time, with no hand in Resolve:

  build <job> [--format vertical-1080] [--fps N]
        07-edit/titles/fusion/: per kind on the card, one Fusion macro `.setting` (what the Effects Library lists, by
        its file name) and the same node graph as a `.comp` (TimelineItem.ImportFusionComp — the no-install route); the
        `.drfx` bundle (Edit/Titles/Cine/<name>.setting, for fusion.InstallFile); templates.json — each template's name,
        files, sha256, the card's sha256, the fps, the tool names the console writes, the motion in frames, the fields.
  check <job>   the manifest against the card as it is now: a template from an older card, an older generator, a
                missing kind or a file changed by hand refuses (exit 1)
  --selftest

The template (tool names are fixed — the console and the tests address them):
  TT_Page   Background — transparent; opaque at the kind's `page_bg` (the end card)
  TT_Main   TextPlus — the main words: the card's font and Style (the style frame's, the face's, the file's own style
            name, else the weight as a name: 700 → Bold), the style-frame Size for the kind's step, CharacterSpacing
            1 + tracking_em, the alignment and Center, the ink (paper or footage); element 3 = the plate (colors.plate)
            on a kind with `plate`, else the style frame's highlighter
  <field>   TextPlus per extra field the kit has (stat: label · price-card: kicker, was, note · end-card: url · …),
            named after the field: the console writes a spec's field to the tool of that name; the companion face
  TT_Move   Merge(TT_Page, TT_Main + fields) — Blend and Center.Y keyed from the card's motion tokens
  TT_Fold   TimeStretcher(TT_Move): SourceTime folds the clip's time onto the template's, so the exit always plays
            over the clip's LAST frames however the title is trimmed
  CustomData.cine = {card_sha256, kind, format, fps, gen, job} on the macro and on TT_Main: the console reads it back
            after the insert (the identity of what Resolve actually placed)

The motion is exact and cannot overshoot: a Fusion spline is a cubic Bézier in (time, value), and so is the card's
CSS cubic-bezier(x1, y1, x2, y2). Between keys (t0, v0) and (t1, v1) the right handle of the first is
(t0 + x1·Δt, v0 + y1·Δv) and the left handle of the second (t0 + x2·Δt, v0 + y2·Δv). `title_card.py lint` refuses a
curve with y outside [0, 1] (C2), so every handle sits inside its segment's value range and the curve cannot pass its
rest; `title_qa.py` still measures overshoot on the pixels. Every spline is keyed at frame 0 (an accessories brand's ad job: a
modifier keys frame 0 with the current value, and a fade keyed later started at Blend 0.68).

What it does not make natively yet (phase 1; `title_card.py titles` WARNS on each, naming what the native title does
instead): per-word and mask-reveal entrances (the lines fade and rise together), stagger, the stat's count, the
per-word highlighter and the underline mark. A look that needs them is the owner's call, recorded as their reason.

[assumed until the live test]: that `comp.RenderEnd` is the clip's last frame inside a Resolve title (L1-d), the
element-3 plate inputs (L1-g), the field positions (a line height of 1.2 em, Size × width = the em) until
assets/fusion-calibration.json is measured (L1-i), and the .drfx layout (L1-f). The manifest says which.
"""
from __future__ import annotations
import argparse, hashlib, io, json, math, os, re, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import title_card as TC  # noqa: E402

GEN = 1                                         # the generator's version: a template from an older one is stale
OUT = os.path.join("07-edit", "titles", "fusion")
MAIN = "TT_Main"
RISE = 0.012                                    # 1.2 % of the frame height, as title.mjs's rise_px (fade-rise)
TRACK_SPREAD = 0.25                             # tracking-in: the letters gather from 1 + tracking + this [assumed]
BLUR_FROM = 10.0                                # blur-resolve: XBlurSize from this to 0 [assumed — never ads]
LINE_EM = 1.2                                   # a Text+ line, in ems [assumed until the calibration]
NATIVE_ENTER = ("fade-rise", "tracking-in", "blur-resolve", "cut")    # per-word, mask-reveal: fade-rise + a WARN
NATIVE_EXIT = ("fade", "fade-up", "cut")
FMT_TOKEN = {"vertical-1080": "v1080", "vertical-4k": "v4k", "landscape-1080": "h1080", "landscape-4k": "h4k",
             "feed-4x5": "f4x5", "square-1080": "s1080", "broadcast-eu-1080": "b1080"}
# kit → (where the main words come from, the field tools under or over it). A field is a TextPlus named after the
# content key; `kicker` sits above the main block, the others below, in this order.
KIT_FIELDS = {"hero-line": ("lines", []), "super": ("lines", []), "stat": ("stat", ["label"]),
              "price-card": ("price|lines", ["kicker", "was", "note"]), "end-card": ("lines|line", ["url"]),
              "lockup": ("lines|line", ["kicker", "label"]), "place-time": ("place|lines", ["time"]),
              "main-title": ("title|lines", ["subtitle"]), "episode-card": ("title|lines", ["kicker"])}
ABOVE = ("kicker",)
MAIN_LINES = {"hero-line": 2, "lockup": 2, "main-title": 1, "super": 2}   # the template's own guess; rows re-place fields


# ── the .setting language: Lua tables ────────────────────────────────────────────────────────────────────────
class T:
    """A typed table: Name { body }."""
    def __init__(self, name: str, body):
        self.name, self.body = name, body


class O(list):
    """An ordered() table: a list of (key, value)."""


class R(str):
    """Written verbatim."""


class Key:
    """A spline key: { value, LH = { t, v }, RH = { t, v } } — the handles in absolute time and value."""
    def __init__(self, v: float, lh=None, rh=None):
        self.v, self.lh, self.rh = v, lh, rh


def num(x) -> str:
    s = f"{float(x):.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "", "-") else s


def lua(v, ind: int = 0) -> str:
    pad, nxt = "\t" * ind, "\t" * (ind + 1)
    if isinstance(v, R):
        return str(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return num(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(v, Key):
        parts = [num(v.v)] + [f"{k} = {{ {num(h[0])}, {num(h[1])} }}" for k, h in (("LH", v.lh), ("RH", v.rh)) if h]
        return "{ " + ", ".join(parts) + " }"
    if isinstance(v, T):
        return f"{v.name} {lua(v.body, ind)}"
    if isinstance(v, (list, tuple)) and not isinstance(v, O):
        return "{ " + ", ".join(lua(x, ind + 1) for x in v) + " }"
    items, head = (list(v), "ordered() ") if isinstance(v, O) else (list(v.items()), "")

    def key(k):
        return k if isinstance(k, str) and re.fullmatch(r"[A-Za-z_]\w*", k) else f"[{lua(k)}]"
    return head + "{\n" + "".join(f"{nxt}{key(a)} = {lua(b, ind + 1)},\n" for a, b in items) + pad + "}"


_TOK = re.compile(r'\s+|--\[\[.*?\]\]|--[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|'
                  r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|[A-Za-z_]\w*|[{}\[\]=,;()]', re.S)
_ESC = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}


def parse_lua(text: str):
    """Fusion's Lua-table subset → Python: a typed table is a dict with "__type"; ordered() is a dict (in order); an
    array part is a list (or integer keys from 1 beside named ones). Enough to read a .setting / .comp back — ours, and
    the published inputs of a pack's macro (resolve_library.py)."""
    toks, pos = [], 0
    while pos < len(text):
        m = _TOK.match(text, pos)
        if not m:
            raise ValueError(f"unexpected {text[pos:pos + 20]!r} at {pos}")
        t = m.group(0)
        pos = m.end()
        if not t.strip() or t.startswith("--"):
            continue
        toks.append(t)
    i = 0

    def peek(k=0):
        return toks[i + k] if i + k < len(toks) else None

    def take(want=None):
        nonlocal i
        t = toks[i]
        if want is not None and t != want:
            raise ValueError(f"expected {want!r}, got {t!r} (token {i})")
        i += 1
        return t

    def value():
        t = peek()
        if t == "{":
            return table()
        if t[0] in "\"'":
            take()
            return re.sub(r"\\(.)", lambda m: _ESC.get(m.group(1), m.group(1)), t[1:-1])
        if re.fullmatch(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", t):
            take()
            return int(t) if re.fullmatch(r"-?\d+", t) else float(t)
        take()
        if t in ("true", "false"):
            return t == "true"
        if t == "nil":
            return None
        if peek() == "(" and peek(1) == ")":
            take("("); take(")")
        if peek() == "{":
            body = table()
            if isinstance(body, list):
                body = {k + 1: v for k, v in enumerate(body)}
            body["__type"] = t
            return body
        return t                                        # a bare name

    def table():
        take("{")
        d, arr = {}, []
        while peek() != "}":
            if peek() == "[":
                take("[")
                k = value()
                take("]"); take("=")
                d[k] = value()
            elif re.fullmatch(r"[A-Za-z_]\w*", peek() or "") and peek(1) == "=":
                k = take(); take("=")
                d[k] = value()
            else:
                arr.append(value())
            if peek() in (",", ";"):
                take()
        take("}")
        if arr and not d:
            return arr
        for k, v in enumerate(arr):
            d[k + 1] = v
        return d
    v = value()
    return v


# ── the card → numbers ───────────────────────────────────────────────────────────────────────────────────────
def motion(card: dict, kind: str, fps: float) -> dict:
    """The card's motion tokens for a kind, in frames at fps: e (entrance), x (exit), X = ceil(x), h (the rest frame),
    x0 (the exit's first key), and the families and curves. A family Fusion does not make natively here enters as
    fade-rise (`title_card.py titles` warns)."""
    M, K = card.get("motion") or {}, (card.get("kinds") or {}).get(kind) or {}
    en, ex = {**(M.get("enter") or {}), **(K.get("enter") or {})}, {**(M.get("exit") or {}), **(K.get("exit") or {})}
    fam_in = en.get("family") if en.get("family") in NATIVE_ENTER else "fade-rise"
    fam_out = ex.get("family") if ex.get("family") in NATIVE_EXIT else "fade"
    fr = lambda ms: round(float(ms) * fps / 1000.0, 3)  # noqa: E731
    e = 0.0 if fam_in == "cut" else fr(en.get("ms") or 600)
    x = 0.0 if fam_out == "cut" else fr(ex.get("ms") or 300)
    h = math.ceil(e) + 1
    return {"enter": fam_in, "enter_card": en.get("family"), "exit": fam_out, "ein": list(en.get("ease") or [0.16, 1, 0.3, 1]),
            "eout": list(ex.get("ease") or [0.4, 0, 1, 1]), "e": e, "x": x, "X": int(math.ceil(x)), "h": h, "x0": h + 1,
            "fps": fps}


def fold(m: dict) -> str:
    """SourceTime: the template's own time folded onto any clip length — the entrance from frame 0, the rest held, the
    exit over the clip's last X frames (comp.RenderEnd [assumed: the clip's last frame — L1-d])."""
    if not m["X"]:
        return f"min(time, {m['h']})"
    return f"iif(time < comp.RenderEnd - {m['X']}, min(time, {m['h']}), {m['x0']} + time - (comp.RenderEnd - {m['X']}))"


def fold_eval(m: dict, time: float, render_end: float) -> float:
    """The fold expression evaluated in Python (the selftest's mirror of Fusion's)."""
    if not m["X"]:
        return min(time, m["h"])
    return min(time, m["h"]) if time < render_end - m["X"] else m["x0"] + time - (render_end - m["X"])


def spline(keys: list, eases: list) -> T:
    """keys [(t, v)], eases [cubic-bezier | None] between consecutive keys (None: a straight segment). A key at frame 0
    is always written."""
    keys, eases = list(keys), list(eases)
    if keys[0][0] != 0:
        keys, eases = [(0.0, keys[0][1])] + keys, [None] + eases
    lh, rh = [None] * len(keys), [None] * len(keys)
    for i, e in enumerate(eases):
        (t0, v0), (t1, v1) = keys[i], keys[i + 1]
        x1, y1, x2, y2 = e or (1 / 3, 1 / 3, 2 / 3, 2 / 3)
        rh[i] = (t0 + x1 * (t1 - t0), v0 + y1 * (v1 - v0))
        lh[i + 1] = (t0 + x2 * (t1 - t0), v0 + y2 * (v1 - v0))
    kf = {}
    for i, (t, v) in enumerate(keys):
        kf[float(t) if float(t) != int(t) else int(t)] = Key(v, lh[i], rh[i])
    return T("BezierSpline", {"SplineColor": {"Red": 255, "Green": 128, "Blue": 0}, "NameSet": True, "KeyFrames": kf})


def inp(value=None, src=None, expr=None) -> T:
    b = {}
    if src:
        b.update(SourceOp=src[0], Source=src[1])
    if value is not None:
        b["Value"] = value
    if expr:
        b["Expression"] = expr
    return T("Input", b)


def _pt(p) -> R:
    return R("{ %s, %s }" % (num(p[0]), num(p[1])))


def fmt_of(fmt_name: str) -> dict:
    return json.load(open(os.path.join(TC.SKILL, "assets", "delivery-formats.json"), encoding="utf-8"))["formats"][fmt_name]


def field_centres(card: dict, kind: str, fmt: dict, n_main: int | None = None) -> dict:
    """{field: [x, y]}: each field tool's Text+ Center beside the main block of n_main lines — kicker above, the rest
    below in kit order. [assumed: a line is 1.2 em and Size × width is the em, until the calibration (L1-i)]"""
    K = (card.get("kinds") or {}).get(kind) or {}
    kit = K.get("kit") or "super"
    fields = KIT_FIELDS.get(kit, ("lines", []))[1]
    if not fields:
        return {}
    lay = TC.layout_for(card)[kind]
    sf = {**TC.STYLE_DEFAULT, **(card.get("style_frame") or {})}
    sc = {**TC.STYLE_DEFAULT["scale"], **(sf.get("scale") or {})}
    ar = float(fmt["width"]) / float(fmt["height"])
    lh_main = float(lay["Size"]) * ar * LINE_EM
    lh_f = float(sc.get("body", 0.07)) * ar * LINE_EM
    n = int(n_main or MAIN_LINES.get(kit, 1))
    x, y = lay["Center"]
    out, below = {}, 0
    for f in fields:
        if f in ABOVE:
            out[f] = [x, round(y + n * lh_main / 2 + 0.35 * lh_f + 0.5 * lh_f, 5)]
        else:
            out[f] = [x, round(y - n * lh_main / 2 - 0.35 * lh_f - (below + 0.5) * lh_f, 5)]
            below += 1
    return out


def words_for(spec: dict, kit: str | None, fields=None) -> dict:
    """{tool: words} for a spec in a generated template: TT_Main gets the main words (the lines; a stat's prefix +
    value + suffix; a price; a place), each field tool its field. `_extra` lists word fields the kit has no tool for
    (the console reports them: words that would be lost are a placement failure)."""
    import native
    C = spec.get("content") or {}
    kit = kit or "super"
    src, kf = KIT_FIELDS.get(kit, ("lines", []))
    fields = list(fields if fields is not None else kf)
    main = ""
    if kit == "stat":
        main = f"{C.get('prefix') or ''}{C.get('value') if C.get('value') is not None else ''}{C.get('suffix') or ''}"
    else:
        for k in src.split("|"):
            if k == "lines" and C.get("lines"):
                main = "\n".join(str(x) for x in C["lines"] if str(x).strip())
            elif k != "lines" and C.get(k) and not isinstance(C.get(k), bool):
                main = str(C[k])
            if main:
                break
    if not main:
        main = native.spec_text(spec)[0]
    out = {MAIN: main}
    used = set(src.split("|")) | ({"prefix", "value", "suffix"} if kit == "stat" else set())
    for f in fields:
        v = C.get(f)
        if v is not None and not isinstance(v, bool) and str(v).strip():
            out[f] = str(v)
            used.add(f)
    extra = [k for k in native.spec_text(spec)[1] if k not in used]
    if extra:
        out["_extra"] = extra
    return out


def content_from_words(spec: dict, kit: str | None, words: dict) -> dict:
    """The reverse of words_for: a spec's content rewritten from the words Resolve holds per tool (native.py
    sync-specs, after an editor re-worded a title on the Edit page). The kit's switches (emphasis, mark, plate …) stay."""
    C = dict(spec.get("content") or {})
    kit = kit or "super"
    src, fields = KIT_FIELDS.get(kit, ("lines", []))
    main = words.get(MAIN)
    if main is not None:
        if kit == "stat":
            v = str(main)
            if C.get("prefix") and v.startswith(str(C["prefix"])):
                v = v[len(str(C["prefix"])):]
            if C.get("suffix") and v.endswith(str(C["suffix"])):
                v = v[: -len(str(C["suffix"]))]
            C["value"] = v
        else:
            keys = src.split("|")
            used = next((k for k in keys if (k == "lines" and C.get("lines")) or (k != "lines" and C.get(k))), keys[0])
            if used == "lines":
                C["lines"] = [x for x in str(main).split("\n") if x.strip()]
            else:
                C[used] = str(main)
    for f in fields:
        if words.get(f):
            C[f] = words[f]
        elif f in C and not isinstance(C[f], bool):
            C.pop(f)
    return C


def kind_tools(card: dict, kind: str, fmt: dict, fps: float, meta: dict) -> tuple:
    """(tools as an ordered table, the TT_Main inputs, the motion) for one kind."""
    K = (card.get("kinds") or {}).get(kind) or {}
    kit = K.get("kit") or "super"
    lay = TC.layout_for(card)[kind]
    m = motion(card, kind, fps)
    sp = 1.0 + float(card.get("tracking_em") or 0)
    main = {"UseFrameFormatSettings": inp(1), "StyledText": inp("Title")}
    for k_, v_ in lay.items():
        if k_.startswith("_"):
            continue
        main[k_] = inp(_pt(v_) if isinstance(v_, (list, tuple)) else v_)
    main["CharacterSpacing"] = inp(sp)
    tools = O()
    page = K.get("page_bg") if K.get("page_bg") not in (None, "", "BRAND", "transparent") else None
    pr, pg, pb, pa = TC.rgba01(page) if page else (0.0, 0.0, 0.0, 0.0)
    tools.append(("TT_Page", T("Background", {"Inputs": {"UseFrameFormatSettings": inp(1), "TopLeftRed": inp(pr),
                                                         "TopLeftGreen": inp(pg), "TopLeftBlue": inp(pb),
                                                         "TopLeftAlpha": inp(pa)},
                                              "ViewInfo": T("OperatorInfo", {"Pos": [0, 0]})})))
    if m["enter"] == "tracking-in" and m["e"]:
        main["CharacterSpacing"] = inp(src=("TT_Track", "Value"))
        tools.append(("TT_Track", spline([(0.0, sp + TRACK_SPREAD), (m["e"], sp)], [m["ein"]])))
    tools.append((MAIN, T("TextPlus", {"Inputs": main, "CustomData": {"cine": dict(meta)},
                                       "ViewInfo": T("OperatorInfo", {"Pos": [0, 70]})})))
    fg = MAIN
    if m["enter"] == "blur-resolve" and m["e"]:
        tools.append(("TT_BlurSize", spline([(0.0, BLUR_FROM), (m["e"], 0.0)], [m["ein"]])))
        tools.append(("TT_Blur", T("Blur", {"Inputs": {"XBlurSize": inp(src=("TT_BlurSize", "Value")),
                                                       "Input": inp(src=(MAIN, "Output"))}})))
        fg = "TT_Blur"
    # the fields: TextPlus each, the companion face, merged over the main block
    cf, cs = TC.style_of(card, "companion")
    sf = {**TC.STYLE_DEFAULT, **(card.get("style_frame") or {})}
    sc = {**TC.STYLE_DEFAULT["scale"], **(sf.get("scale") or {})}
    centres = field_centres(card, kind, fmt)
    fields = KIT_FIELDS.get(kit, ("lines", []))[1]
    for k_ in fields:
        fin = {"UseFrameFormatSettings": inp(1), "StyledText": inp(""), "Size": inp(float(sc.get("body", 0.07))),
               "CharacterSpacing": inp(sp), "Center": inp(_pt(centres[k_]))}
        for c_ in ("HorizontalLeftCenterRight", "HorizontalJustificationNew", "Red1", "Green1", "Blue1"):
            fin[c_] = inp(lay[c_])
        if cf or lay.get("Font"):
            fin["Font"] = inp(cf or lay["Font"])
            fin["Style"] = inp(cs or lay.get("Style") or "Regular")
        tools.append((k_, T("TextPlus", {"Inputs": fin, "ViewInfo": T("OperatorInfo", {"Pos": [110, 70]})})))
        mg = f"TT_Field_{k_}"
        tools.append((mg, T("Merge", {"Inputs": {"Background": inp(src=(fg, "Output")), "Foreground": inp(src=(k_, "Output"))}})))
        fg = mg
    # the move: Blend and Center.Y keyed, folded by the TimeStretcher
    e, x0, x = m["e"], m["x0"], m["x"]
    bk, be = [(0.0, 0.0 if e else 1.0)], []
    if e:
        bk.append((e, 1.0)); be.append(m["ein"])
    bk.append((float(x0), 1.0)); be.append(None)
    if x:
        bk.append((x0 + x, 0.0)); be.append(m["eout"])
    move = {"Background": inp(src=("TT_Page", "Output")), "Foreground": inp(src=(fg, "Output")),
            "Blend": inp(src=("TT_MoveBlend", "Value"))}
    tools.append(("TT_MoveBlend", spline(bk, be)))
    rise_in = m["enter"] == "fade-rise" and e
    rise_out = m["exit"] == "fade-up" and x
    if rise_in or rise_out:
        ck, ce = [(0.0, 0.5 - (RISE if rise_in else 0.0))], []
        if rise_in:
            ck.append((e, 0.5)); ce.append(m["ein"])
        ck.append((float(x0), 0.5)); ce.append(None)
        if rise_out:
            ck.append((x0 + x, 0.5 + RISE / 2)); ce.append(m["eout"])
        tools.append(("TT_MoveCenterY", spline(ck, ce)))
        tools.append(("TT_MoveCenter", T("XYPath", {"ShowKeyPoints": False, "DrawMode": "ModifyOnly",
                                                     "Inputs": {"X": inp(0.5), "Y": inp(src=("TT_MoveCenterY", "Value"))}})))
        move["Center"] = inp(src=("TT_MoveCenter", "Value"))
    tools.append(("TT_Move", T("Merge", {"Inputs": move, "ViewInfo": T("OperatorInfo", {"Pos": [0, 140]})})))
    tools.append(("TT_Fold", T("TimeStretcher", {"Inputs": {"Input": inp(src=("TT_Move", "Output")),
                                                            "SourceTime": inp(0, expr=fold(m))},
                                                 "ViewInfo": T("OperatorInfo", {"Pos": [0, 210]})})))
    return tools, main, m, fields


def _ident(name: str) -> str:
    return re.sub(r"\W", "_", name)


def setting(name: str, tools: O, meta: dict, fields: list) -> str:
    """The Fusion macro (what Resolve saves for a title template), its words and look published for the Inspector."""
    pub = O([("Input1", T("InstanceInput", {"SourceOp": MAIN, "Source": "StyledText", "Name": "Text"})),
             ("Input2", T("InstanceInput", {"SourceOp": MAIN, "Source": "Font", "Name": "Font"})),
             ("Input3", T("InstanceInput", {"SourceOp": MAIN, "Source": "Style", "Name": "Style"})),
             ("Input4", T("InstanceInput", {"SourceOp": MAIN, "Source": "Size", "Name": "Size"}))])
    for i, f in enumerate(fields, start=5):
        pub.append((f"Input{i}", T("InstanceInput", {"SourceOp": f, "Source": "StyledText", "Name": f.capitalize()})))
    macro = T("MacroOperator", {"CtrlWZoom": False, "NameSet": True, "CustomData": {"cine": dict(meta)}, "Inputs": pub,
                                "Outputs": {"MainOutput1": T("InstanceOutput", {"SourceOp": "TT_Fold", "Source": "Output"})},
                                "ViewInfo": T("GroupInfo", {"Pos": [0, 0]}), "Tools": tools})
    return lua({"Tools": O([(_ident(name), macro)]), "ActiveTool": _ident(name)}) + "\n"


def comp(tools: O, n: int = 120) -> str:
    """The same graph as a composition, for TimelineItem.ImportFusionComp (the no-install route)."""
    t = O(list(tools) + [("MediaOut1", T("MediaOut", {"Inputs": {"Index": inp("0"), "Input": inp(src=("TT_Fold", "Output"))}}))])
    return "Composition " + lua({"CurrentTime": 0, "RenderRange": [0, n - 1], "GlobalRange": [0, n - 1], "Tools": t}) + "\n"


def _zip_bytes(files: dict) -> bytes:
    """A deterministic zip (a fixed date on every entry): the same card gives the same .drfx bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, files[name])
    return buf.getvalue()


def slug_of(job: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", os.path.basename(os.path.abspath(job)).lower())[:14] or "job"


def build(job: str, fmt_name: str = "vertical-1080", fps: float | None = None) -> dict:
    """Every kind on the approved card as a Fusion title: .setting + .comp + the .drfx + templates.json."""
    cp = os.path.join(job, TC.CARD)
    if not os.path.isfile(cp):
        raise SystemExit(f"REFUSED: no {TC.CARD} — the titles are generated from the approved card (title_card.py propose)")
    card = TC.load_card(cp)
    P, _ = TC.lint_card(card)
    if P:
        raise SystemExit("REFUSED: the card does not lint — " + "; ".join(P))
    if not card.get("kinds"):
        raise SystemExit("REFUSED: a captions-only card has no title kinds to generate")
    font, style = TC.style_of(card)
    if not font:
        raise SystemExit("REFUSED: the card names no anchor face (fonts.anchor.family or style_frame.font)")
    fmt = fmt_of(fmt_name)
    fps = float(fps or fmt.get("fps_default") or 24)
    csha = TC._sha(cp)
    cal = TC.calibration(fmt_name)
    slug = slug_of(job)
    out = os.path.join(job, OUT)
    os.makedirs(out, exist_ok=True)
    man = {"generator": "fusion_titles.py", "gen": GEN, "card": TC.CARD, "card_sha256": csha, "format": fmt_name,
           "fps": fps, "font": font, "style": style,
           "positions": (f"measured {cal.get('measured')} on Resolve {cal.get('resolve')}" if cal else
                         "[assumed] the style frame's Center and Size (POSITION_Y, FIT_EM_PER_SIZE) — no "
                         "assets/fusion-calibration.json yet (live test L1-i)"),
           "unmeasured": ["comp.RenderEnd inside a Resolve title is the clip's last frame (L1-d)",
                          "element 3 as a plate: ElementShape3 2, Level3 1, Alpha3 (L1-g)",
                          "the .drfx layout Edit/Titles/Cine/<name>.setting for fusion.InstallFile (L1-f)"],
           "kinds": {}}
    bundle = {}
    for kind in card.get("kinds") or {}:
        K = card["kinds"][kind]
        name = f"cine-{slug}-{kind}-{FMT_TOKEN.get(fmt_name, re.sub(r'[^a-z0-9]', '', fmt_name))}-{csha[:8]}"
        meta = {"card_sha256": csha, "kind": kind, "format": fmt_name, "fps": fps, "gen": GEN, "job": slug, "name": name}
        tools, main, m, fields = kind_tools(card, kind, fmt, fps, meta)
        s, c = setting(name, tools, meta, fields), comp(tools)
        open(os.path.join(out, name + ".setting"), "w", encoding="utf-8").write(s)
        open(os.path.join(out, name + ".comp"), "w", encoding="utf-8").write(c)
        bundle[f"Edit/Titles/Cine/{name}.setting"] = s
        lay = TC.layout_for(card)[kind]
        man["kinds"][kind] = {"name": name, "kit": K.get("kit"), "setting": name + ".setting", "comp": name + ".comp",
                              "sha256": hashlib.sha256(s.encode("utf-8")).hexdigest(),
                              "comp_sha256": hashlib.sha256(c.encode("utf-8")).hexdigest(),
                              "main": MAIN, "fields": fields, "tools": [k for k, _ in tools],
                              "font": lay.get("Font"), "style": lay.get("Style"), "size": lay.get("Size"),
                              "center": lay.get("Center"), "plate": bool(K.get("plate")),
                              "page_bg": K.get("page_bg") if K.get("page_bg") not in ("transparent",) else None,
                              "motion": {k: m[k] for k in ("enter", "exit", "e", "x", "X", "h", "x0")},
                              "fold": fold(m), "gaps": TC.fusion_gaps(card, kind)}
    drfx = f"cine-{slug}-titles.drfx"
    data = _zip_bytes(bundle)
    open(os.path.join(out, drfx), "wb").write(data)
    man["drfx"] = {"file": drfx, "sha256": hashlib.sha256(data).hexdigest(), "layout": "Edit/Titles/Cine/<name>.setting"}
    json.dump(man, open(os.path.join(out, "templates.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return man


def check(job: str) -> list:
    """Problems with the generated titles against the card as it is now (empty = current)."""
    mp = os.path.join(job, OUT, "templates.json")
    if not os.path.isfile(mp):
        return [f"no {OUT}/templates.json — fusion_titles.py build <job>"]
    try:
        man = json.load(open(mp, encoding="utf-8"))
    except ValueError:
        return [f"{OUT}/templates.json does not parse — build again"]
    P = []
    cp = os.path.join(job, TC.CARD)
    if not os.path.isfile(cp):
        return [f"no {TC.CARD}"]
    if man.get("card_sha256") != TC._sha(cp):
        P.append(f"the templates were generated from another card ({str(man.get('card_sha256'))[:8]}; the card is now "
                 f"{TC._sha(cp)[:8]}) — build again")
    if int(man.get("gen") or 0) < GEN:
        P.append(f"the templates come from generator {man.get('gen')}, this is {GEN} — build again")
    card = TC.load_card(cp)
    for kind in card.get("kinds") or {}:
        k = (man.get("kinds") or {}).get(kind)
        if not k:
            P.append(f"kind {kind!r} is on the card and has no template — build again")
            continue
        sp = os.path.join(job, OUT, k.get("setting") or "")
        if not os.path.isfile(sp) or hashlib.sha256(open(sp, "rb").read()).hexdigest() != k.get("sha256"):
            P.append(f"{k.get('setting')}: missing or changed by hand since it was generated — build again")
        cpp = os.path.join(job, OUT, k.get("comp") or "")
        if not os.path.isfile(cpp) or hashlib.sha256(open(cpp, "rb").read()).hexdigest() != k.get("comp_sha256"):
            P.append(f"{k.get('comp')}: missing or changed by hand since it was generated — build again")
    return P


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────────────
def _bez(p0, p1, p2, p3, s):
    u = 1 - s
    return u ** 3 * p0 + 3 * u * u * s * p1 + 3 * u * s * s * p2 + s ** 3 * p3


def _kv(k) -> float:
    return float(k[0] if isinstance(k, list) else k[1])


def spline_eval(kf: dict, t: float) -> float:
    """A parsed spline's value at time t (the Bézier solved for time by bisection)."""
    ks = sorted((float(k), v if isinstance(v, dict) else {1: v[0]}) for k, v in kf.items() if not isinstance(k, str))
    if t <= ks[0][0]:
        return _kv(ks[0][1])
    for (t0, a), (t1, b) in zip(ks, ks[1:]):
        if t0 <= t <= t1:
            v0, v1 = _kv(a), _kv(b)
            rh, lh = a.get("RH") or [t0 + (t1 - t0) / 3, v0 + (v1 - v0) / 3], b.get("LH") or [t0 + 2 * (t1 - t0) / 3, v0 + 2 * (v1 - v0) / 3]
            lo, hi = 0.0, 1.0
            for _ in range(60):
                mid = (lo + hi) / 2
                if _bez(t0, rh[0], lh[0], t1, mid) < t:
                    lo = mid
                else:
                    hi = mid
            return _bez(v0, rh[1], lh[1], v1, (lo + hi) / 2)
    return _kv(ks[-1][1])


def selftest() -> int:
    ok = True

    def check_(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {str(info)[:1500]}"))
        ok = ok and bool(cond)
    heavy = TC._sysfont("InterDisplay-ExtraBold.otf", "Inter-Bold.otf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf")
    regular = TC._sysfont("Inter-Regular.otf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf")
    # the weight → Style table, with no file to read (C-A.2: Poppins 700 came out Regular)
    for w, want in ((700, "Bold"), (500, "Medium"), (600, "SemiBold"), (400, "Regular")):
        f_, s_ = TC.style_of({"fonts": {"anchor": {"family": "Poppins", "weight": w}}})
        check_(f"weight {w} → Text+ Style {want!r} (no file to read)", (f_, s_) == ("Poppins", want), (f_, s_))
    check_("the style frame's own style wins", TC.style_of({"style_frame": {"font": "Poppins", "style": "ExtraBold"},
                                                            "fonts": {"anchor": {"family": "Poppins", "weight": 700}}}) == ("Poppins", "ExtraBold"))
    if not (heavy and regular):
        print("  [SKIP] no system fonts to build a card that lints")
        return 0 if ok else 1
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "acme-01001-five-spots")
        os.makedirs(os.path.join(job, "00-brief"))
        TC.propose(job, "ads", accent="#E8432E", page_bg="#111111")
        cp = os.path.join(job, TC.CARD)
        card = TC.load_card(cp)
        fh, fr = TC.read_font(heavy), TC.read_font(regular)
        card["fonts"] = {"anchor": {"family": fh["family"], "file": heavy, "weight": int(fh["weight_class"])},
                         "companion": {"family": fr["family"], "file": regular, "weight": int(fr["weight_class"])}}
        card["kinds"]["hero"]["max_words"] = 4
        json.dump({k: v for k, v in card.items() if k != "__path"}, open(cp, "w"), indent=1)
        card = TC.load_card(cp)
        P, _ = TC.lint_card(card)
        check_("the test card lints clean", not P, P)
        man = build(job)
        out = os.path.join(job, OUT)
        kinds = list(card["kinds"])
        files = sorted(os.listdir(out))
        check_("build: one .setting, one .comp and one manifest row per kind on the card, the .drfx and templates.json",
               all(any(f.endswith(f"-{k}-v1080-{man['card_sha256'][:8]}.setting") for f in files) for k in kinds)
               and len([f for f in files if f.endswith(".comp")]) == len(kinds) and set(man["kinds"]) == set(kinds)
               and "templates.json" in files and any(f.endswith(".drfx") for f in files), files)
        z = zipfile.ZipFile(os.path.join(out, man["drfx"]["file"]))
        check_("the .drfx holds Edit/Titles/Cine/<name>.setting for every kind",
               sorted(z.namelist()) == sorted(f"Edit/Titles/Cine/{v['name']}.setting" for v in man["kinds"].values()), z.namelist())
        hero = man["kinds"]["hero"]
        S = parse_lua(open(os.path.join(out, hero["setting"]), encoding="utf-8").read())
        mac = S["Tools"][_ident(hero["name"])]
        tl = mac["Tools"]
        tm = tl[MAIN]
        lay = TC.layout_for(card)["hero"]
        check_("the .setting parses back: a MacroOperator, TT_Main a TextPlus with the card's font, its Style from the "
               "face, the hero's Size, the ink, CharacterSpacing 1 + tracking",
               mac["__type"] == "MacroOperator" and tm["__type"] == "TextPlus" and tm["Inputs"]["Font"]["Value"] == fh["family"]
               and tm["Inputs"]["Style"]["Value"] == lay["Style"] and abs(tm["Inputs"]["Size"]["Value"] - lay["Size"]) < 1e-9
               and abs(tm["Inputs"]["Red1"]["Value"] - lay["Red1"]) < 1e-6
               and abs(tm["Inputs"]["CharacterSpacing"]["Value"] - (1 + card["tracking_em"])) < 1e-9, tm["Inputs"])
        check_("…the identity rides on the macro and on TT_Main (CustomData.cine: the card hash, kind, fps, gen)",
               tm["CustomData"]["cine"]["card_sha256"] == man["card_sha256"] and mac["CustomData"]["cine"]["kind"] == "hero"
               and tm["CustomData"]["cine"]["fps"] == 24 and tm["CustomData"]["cine"]["gen"] == GEN, tm.get("CustomData"))
        check_("…TT_Move takes Blend and Center from splines; TT_Fold is a TimeStretcher with the fold expression; the macro "
               "outputs TT_Fold and publishes the words",
               tl["TT_Move"]["Inputs"]["Blend"]["SourceOp"] == "TT_MoveBlend" and tl["TT_Move"]["Inputs"]["Center"]["SourceOp"] == "TT_MoveCenter"
               and tl["TT_Fold"]["__type"] == "TimeStretcher" and tl["TT_Fold"]["Inputs"]["SourceTime"]["Expression"] == hero["fold"]
               and mac["Outputs"]["MainOutput1"]["SourceOp"] == "TT_Fold"
               and mac["Inputs"]["Input1"]["Source"] == "StyledText", (tl.get("TT_Fold"), mac.get("Outputs")))
        C_ = parse_lua(open(os.path.join(out, hero["comp"]), encoding="utf-8").read())
        check_("the .comp is the same graph with a MediaOut fed by TT_Fold (the ImportFusionComp route)",
               C_["__type"] == "Composition" and C_["Tools"]["MediaOut1"]["Inputs"]["Input"]["SourceOp"] == "TT_Fold"
               and set(k for k in C_["Tools"] if k != "MediaOut1") == set(tl), list(C_["Tools"]))
        # motion numbers: 450 ms fade-rise, 250 ms fade at 24 / 25 / 30 fps
        for fps_, e_, x_, X_ in ((24, 10.8, 6.0, 6), (25, 11.25, 6.25, 7), (30, 13.5, 7.5, 8)):
            m_ = motion(card, "hero", fps_)
            check_(f"{fps_} fps: the entrance keys at {e_}, the exit runs {x_} frames (X = {X_})",
                   abs(m_["e"] - e_) < 1e-9 and abs(m_["x"] - x_) < 1e-9 and m_["X"] == X_ and m_["h"] == math.ceil(e_) + 1, m_)
        bl = tl["TT_MoveBlend"]["KeyFrames"]
        ks = sorted((float(k), v) for k, v in bl.items())
        ein, eout = card["motion"]["enter"]["ease"], card["motion"]["exit"]["ease"]
        (t0, a), (t1, b) = ks[0], ks[1]
        x1, y1, x2, y2 = ein
        check_("the handles are the card's cubic-bezier, mapped exactly (to 1e-6)",
               abs(a["RH"][0] - (t0 + x1 * (t1 - t0))) < 1e-6 and abs(a["RH"][1] - (a[1] + y1 * (b[1] - a[1]))) < 1e-6
               and abs(b["LH"][0] - (t0 + x2 * (t1 - t0))) < 1e-6 and abs(b["LH"][1] - (a[1] + y2 * (b[1] - a[1]))) < 1e-6
               and abs(t1 - 10.8) < 1e-9, ks)
        # no overshoot on any spline of any kind, for every ease the lanes ship
        lanes = json.load(open(TC.LANES, encoding="utf-8"))["lanes"]
        eases = {tuple(L["motion"][k]["ease"]) for L in lanes.values() for k in ("enter", "exit")}
        worst, zero = 0.0, True
        for e_ in eases:
            sp_ = parse_lua(lua(spline([(0.0, 0.0), (12.0, 1.0), (20.0, 1.0), (26.0, 0.0)], [list(e_), None, list(e_)])))
            zero = zero and 0 in sp_["KeyFrames"]
            kk = sorted((float(k), v) for k, v in sp_["KeyFrames"].items())
            for (ta, va), (tb, vb) in zip(kk, kk[1:]):
                lo_, hi_ = min(va[1], vb[1]), max(va[1], vb[1])
                for hv in (va.get("RH", [0, va[1]])[1], vb.get("LH", [0, vb[1]])[1]):
                    worst = max(worst, lo_ - hv, hv - hi_)
                for i_ in range(1, 50):
                    v_ = spline_eval(sp_["KeyFrames"], ta + (tb - ta) * i_ / 50)
                    worst = max(worst, lo_ - v_, v_ - hi_)
        check_(f"no overshoot: every handle and sampled value inside its segment's range, for the {len(eases)} curves the "
               f"lanes ship (C2)", worst <= 1e-9, worst)
        for kind, k in man["kinds"].items():
            T_ = parse_lua(open(os.path.join(out, k["setting"]), encoding="utf-8").read())["Tools"][_ident(k["name"])]["Tools"]
            sps = [v for v in T_.values() if isinstance(v, dict) and v.get("__type") == "BezierSpline"]
            zero = zero and all(0 in v["KeyFrames"] for v in sps)
        check_("every spline is keyed at frame 0 (an accessories brand's ad job: the fade that started at Blend 0.68)", zero)
        # the fold: X = 6, h = 12 at 24 fps; the clip at 48, 60 and 96 frames
        m24 = motion(card, "hero", 24)
        good = True
        for n_ in (48, 60, 96):
            end = n_ - 1
            src_ = [fold_eval(m24, t_, end) for t_ in range(n_)]
            good = good and src_[:13] == list(range(13)) and all(v == 12 for v in src_[13: end - 6]) \
                and src_[end - 6] == m24["x0"] and src_[end] == m24["x0"] + 6
            good = good and abs(spline_eval(bl, src_[end])) < 1e-9 and abs(spline_eval(bl, src_[end - 6]) - 1) < 1e-9 \
                and abs(spline_eval(bl, src_[12]) - 1) < 1e-9 and spline_eval(bl, src_[0]) == 0
        check_("the fold: the entrance from frame 0, the rest held, the exit over the last 6 frames — gone on the last "
               "frame — for clips of 48, 60 and 96 frames", good and m24["X"] == 6 and m24["h"] == 12, m24)
        # plate, end card, ads lane
        pr = parse_lua(open(os.path.join(out, man["kinds"]["price"]["setting"]), encoding="utf-8").read())
        pm = pr["Tools"][_ident(man["kinds"]["price"]["name"])]["Tools"]
        check_("a plate kind: element 3 carries colors.plate rgba(10,10,12,0.72); the price-card's fields are tools",
               pm[MAIN]["Inputs"]["Enabled3"]["Value"] == 1 and abs(pm[MAIN]["Inputs"]["Alpha3"]["Value"] - 0.72) < 1e-9
               and abs(pm[MAIN]["Inputs"]["Red3"]["Value"] - 10 / 255) < 1e-6 and all(f in pm for f in ("kicker", "was", "note")), pm[MAIN]["Inputs"])
        ec = parse_lua(open(os.path.join(out, man["kinds"]["endcard"]["setting"]), encoding="utf-8").read())
        em_ = ec["Tools"][_ident(man["kinds"]["endcard"]["name"])]["Tools"]
        check_("the end card: TT_Page opaque at its page_bg #111111, the ink on paper",
               em_["TT_Page"]["Inputs"]["TopLeftAlpha"]["Value"] == 1.0 and abs(em_["TT_Page"]["Inputs"]["TopLeftRed"]["Value"] - 0x11 / 255) < 1e-6
               and abs(em_[MAIN]["Inputs"]["Red1"]["Value"] - 0x19 / 255) < 1e-6, em_["TT_Page"])
        check_("the ads lane: no Blur tool anywhere; the hero's page is transparent",
               not any(v.get("__type") == "Blur" for k in man["kinds"].values() for v in parse_lua(open(os.path.join(out, k["setting"]),
                       encoding="utf-8").read())["Tools"][_ident(k["name"])]["Tools"].values() if isinstance(v, dict))
               and tl["TT_Page"]["Inputs"]["TopLeftAlpha"]["Value"] == 0)
        # words for the console
        w_ = words_for({"content": {"prefix": "", "value": 90, "suffix": " days", "label": "to see results", "label_pos": "below"}}, "stat")
        w2 = words_for({"content": {"price": "$39", "was": "$59", "plate": True}}, "price-card")
        w3 = words_for({"content": {"lines": ["Sleep through", "the night"], "emphasis": "night", "url": "x.com"}}, "hero-line")
        check_("words: a stat's prefix + value + suffix on TT_Main and its label on the label tool; a price and its was; "
               "a bool is never a word; a field the kit has no tool for is named, not lost",
               w_ == {MAIN: "90 days", "label": "to see results"} and w2 == {MAIN: "$39", "was": "$59"}
               and w3.get(MAIN) == "Sleep through\nthe night" and w3.get("_extra") == ["url"], (w_, w2, w3))
        c_ = content_from_words({"content": {"price": "$39", "was": "$59", "plate": True}}, "price-card", {MAIN: "$35", "note": "today"})
        c2_ = content_from_words({"content": {"prefix": "", "value": 90, "suffix": " days", "label": "x"}}, "stat",
                                 {MAIN: "60 days", "label": "to see results"})
        check_("…and back: words re-typed in Resolve rewrite the spec's content, the kit's switches kept",
               c_ == {"price": "$35", "plate": True, "note": "today"} and c2_["value"] == "60" and c2_["label"] == "to see results", (c_, c2_))
        # determinism, a card edit, check
        before = {f: open(os.path.join(out, f), "rb").read() for f in os.listdir(out)}
        man2 = build(job)
        after = {f: open(os.path.join(out, f), "rb").read() for f in os.listdir(out)}
        check_("the same card gives the same bytes: every template, the .drfx and the manifest", before == after and man2 == man)
        check_("check: the templates are current", check(job) == [], check(job))
        c2 = json.load(open(cp, encoding="utf-8")); c2["colors"]["fg"] = "#FAFAFA"
        json.dump(c2, open(cp, "w"), indent=1)
        P_ = check(job)
        check_("a card edit makes every template stale: check refuses", any("another card" in x for x in P_), P_)
        man3 = build(job)
        check_("…and a rebuild gives every name the new card hash",
               all(v["name"].endswith(man3["card_sha256"][:8]) and v["name"] != man["kinds"][k]["name"] for k, v in man3["kinds"].items()))
        open(os.path.join(out, man3["kinds"]["hero"]["setting"]), "a").write("-- edited by hand\n")
        check_("a template changed by hand refuses", any("changed by hand" in x for x in check(job)), check(job))
        # brand lane: tracking-in keys CharacterSpacing; 25 fps scales the keys
        jb = os.path.join(td, "brand-job")
        os.makedirs(os.path.join(jb, "00-brief"))
        TC.propose(jb, "brand", accent="#B08D57", page_bg="#F4EFE6")
        cb = TC.load_card(os.path.join(jb, TC.CARD))
        cb["fonts"] = {"anchor": dict(card["fonts"]["anchor"]), "companion": dict(card["fonts"]["companion"])}
        json.dump({k: v for k, v in cb.items() if k != "__path"}, open(os.path.join(jb, TC.CARD), "w"), indent=1)
        mb = build(jb, fps=25)
        lk = mb["kinds"]["lockup"]
        LT = parse_lua(open(os.path.join(jb, OUT, lk["setting"]), encoding="utf-8").read())["Tools"][_ident(lk["name"])]["Tools"]
        tk = sorted(float(k) for k in LT["TT_Track"]["KeyFrames"])
        check_("brand lane: tracking-in keys TT_Main.CharacterSpacing (1.27 → 1.02) over 1100 ms = 27.5 frames at 25 fps; "
               "no rise on Center; the lockup's kicker and label tools",
               LT[MAIN]["Inputs"]["CharacterSpacing"]["SourceOp"] == "TT_Track" and tk == [0.0, 27.5]
               and "Center" not in LT["TT_Move"]["Inputs"] and "kicker" in LT and "label" in LT
               and abs(LT["TT_Track"]["KeyFrames"][0][1] - 1.27) < 1e-9, (tk, LT.get("TT_Track")))
    print("-" * 60)
    print("selftest OK — the weight becomes a Style; each kind becomes a Fusion macro (.setting) and a .comp that parse "
          "back with the card's font, Style, size, ink, plate and page; the motion is the card's curves exactly, keyed at "
          "frame 0, with no handle outside its segment (C2); the fold lands the exit on the clip's last frames at any "
          "length; the .drfx bundle, the manifest, the words per tool; the same card gives the same bytes, and an edited "
          "card or a hand-edited template refuses" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build"); b.add_argument("job"); b.add_argument("--format", default="vertical-1080")
    b.add_argument("--fps", type=float)
    c = sub.add_parser("check"); c.add_argument("job")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "build":
        man = build(a.job, a.format, a.fps)
        for k, v in man["kinds"].items():
            print(f"  {k:<10} {v['name']}  — {v['font']} {v['style']}, Size {v['size']}, enter {v['motion']['enter']} "
                  f"{v['motion']['e']} f, exit {v['motion']['exit']} {v['motion']['x']} f")
            for g in v["gaps"]:
                print(f"      ⚠ {g}")
        print(f"wrote {OUT}/ — {len(man['kinds'])} template(s), {man['drfx']['file']}, templates.json (card "
              f"{man['card_sha256'][:8]}, {man['fps']:g} fps). Positions: {man['positions']}")
        print("Next: native.py console <job> (PLACE_TITLES installs or imports them, places, reads back).")
        return 0
    if a.cmd == "check":
        P = check(a.job)
        for x in P:
            print(f"  ✗ {x}")
        print("templates current" if not P else f"{len(P)} problem(s)")
        return 1 if P else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
