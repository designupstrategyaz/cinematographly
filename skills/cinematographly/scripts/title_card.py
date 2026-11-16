#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""title_card.py — the project's title card: the one permission list for on-screen titles, and its checks.

Author, 2026-10-26: *"We need to create far better titles, suitable to each project"*; then the council's
packages (the titles and motion proposal of 2026-10-26 [studio history]) — *"A: Title card + type system,
B: HyperFrames + the legibility gate, C: Lane kits + review loop, D: Transitions + ramps"* — and three
rulings: no overshoot on any text, number or UI (C2); keep the burst speed-up and cap ramps (C4); the
approved card is the permission list (C3: captions stay; only the title kinds on the card are rendered).

  propose <job> --lane ads|brand|drama|golf|property|captions-only [--anchor FONT --anchor-family NAME --anchor-weight N]
          [--companion FONT ...] [--accent #hex] [--page-bg #hex] [--genre WORDS] [--force]
        writes 00-brief/TITLE-CARD.json and TITLE-CARD.md from the lane's defaults (assets/title-lanes.json)
        — the type, the scale, the colours, the motion tokens, which title kinds may appear, the
        transition and ramp budgets. Proposed at the storyboard; picture lock refuses without it.
  lint <job> | --card FILE
        A. the type system, read from the font FILES (stdlib OpenType parsing): real weights and
        italics, never faux (Stocks); the pair differs on weight, width or stroke contrast (Brown, Coles &
        Gregory); one type scale; a text cut blown up to display size; the embedding bits and licence text.
        Motion tokens: at most 5 durations and 3 curves (Shaw), no overshoot (C2), lane rules (no
        blur in ads; a hero line of at most 4 words). Placeholders left in (BRAND) refuse. A job whose
        CHECKPOINT lifts `blur-titles` (v2.48.0, project switches; the job is <job>, or the one holding
        --card) may give a brand line, a lockup or a small mark (never the hook card) (a hero-line or lockup kind's own entrance) a
        blur-resolve: the lint prints the rule as lifted instead of refusing it.
  titles <job>
        every title spec (07-edit/titles/<id>.title.json) against the card: its engine (house rule C7, 2026-10-27:
        *"it should defrult to Resolve or Fusion native elements. Not create outside for no reason"* — `engine`
        is `resolve` when absent; `hyperframes` or `gsap` needs an `engine_reason` from native.py's four), its kind is on the card
        (C3), its kit, word count, how many of that kind, the reading time by regime (0.3 s/word when
        the VO says it, 1 s/word when it doesn't), the end card's hold, and its anchor in the cut — it
        starts on its picture event, after the clip's 0.4 s settle unless declared to mask it (C1), and
        never across a non-cut transition or a ramp (needs 07-edit/timeline-dump.json).
  pick <job> <id> --option N
        the review loop: copies option N (<id>.optN.title.json and its render) to <id>.title.json and
        <id>.mov, recording which was picked; the owner's choice is said in chat and signed with
        `gate.py approve titles`.
  check <job>   what `approve titles` and `approve export` still need (exit 1 if anything)
  fit <job> [--format vertical-1080] [--organic]
        every title's lines set at its style-frame size in the card's anchor font, against the width the safe box
        leaves (a supplement ad job: names cut on a card were found only in the render). Run before the console copy.
  --selftest

A title made in Resolve is a Fusion title GENERATED from this card (`fusion_titles.py build`: the card's font and
Style, sizes, ink, plate, position and motion tokens as keyframes), placed by `resolve-production-console.py`
PLACE_TITLES (`native.py console <job>` fills it in: installed by name, or a stock Text+ with the generated comp
imported; moved onto its named track at the spec's frame, its words, font and card hash read back), reviewed as
Resolve's own stills (PLACE_TITLE_OPTIONS → `title_qa.py strip-native`) and measured on Resolve's own renders with the
titles on and off (`title_qa.py native`). One rendered outside is its ProRes 4444 alpha (`title_qa.py check`).

⛔ v2.45 (2026-10-29, the author: *"It keeps making mp4s which it imports"*): `titles` and `check` refuse a spec made in
Resolve (named, or by default) with a rendered movie beside it (`<id>.mov`, `<id>_*.mov`, `<id>.optN.mov`, mp4, mxf,
webm), naming what made the movie; and, from the timeline dump, any title-folder movie sitting on the timeline
(`07-edit/titles/`, `08-captions/`, `07-edit/disclosure/`, `*_alpha*`, `TEXT-CARRIER*`, `CAPTIONS_*`) without a
reasoned spec or an external record. A title is placed, never imported.

What it cannot do: judge the title on the picture — `title_qa.py` measures the render on the composite
(safe box, worst-frame contrast, stroke and cap height at phone size, dwell, overshoot, collisions). It
cannot tell whether a font is the right voice for the brand: the card is proposed by the lane, and the
owner approves it. The font licence check reads what the file declares, which is not the licence you
bought.
"""
from __future__ import annotations
import argparse, datetime as dt, glob, hashlib, json, os, re, shutil, struct, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
LANES = os.path.join(SKILL, "assets", "title-lanes.json")
CARD = os.path.join("00-brief", "TITLE-CARD.json")
TITLES = os.path.join("07-edit", "titles")
KITS = ("hero-line", "super", "stat", "price-card", "end-card", "lockup", "place-time", "main-title", "episode-card")
ENTER = ("fade-rise", "per-word", "tracking-in", "mask-reveal", "blur-resolve", "cut")
EXIT = ("fade", "fade-up", "cut")
ADS_NO_ENTER = ("blur-resolve",)            # no blur, glow or scramble for the 45+ phone audience (the jury)
STEPS = ("label", "body", "title", "hero", "display")
ENGINES = ("resolve", "hyperframes", "gsap")  # resolve unless a reason is recorded (house rule C7, 2026-10-27)
NATIVE = {"template": "Text+", "track": "Titles", "caption_template": "Text+"}  # the card's Resolve block, by default
# ⚡ THE STYLE FRAME (a supplement ad job, 2026-10-28: titles and cards took about six design rounds, almost all fixing what a rule
# could have set up front — white outlined text on cream paper, names at H5 then H1). One approved still sets the
# typeface, the type scale, the ink on paper and on footage, the left margin and the one emphasis device, as tokens the
# console writes into every Text+ (`native.py console`). The scale is Text+ Size (a share of the frame width): the
# values that worked on a supplement ad job [measured on one job].
STYLE_STEPS = ("H1", "H2", "body", "caption", "disclosure")
STYLE_DEFAULT = {"approved_still": "", "approved": None, "font": None, "style": None,
                 "scale": {"H1": 0.125, "H2": 0.10, "body": 0.07, "caption": 0.06, "disclosure": 0.042},
                 "align": "left", "margin_left_x": 0.115, "centre": "frame",
                 "ink": {"footage": "#FFFFFF", "paper": "#19191C"},
                 "emphasis": {"device": "highlighter", "color": "#FFE778"}, "kind_step": {}}
KIND_STEP = {"hero": "H1", "stat": "H1", "price": "H2", "endcard": "H1", "lockup": "H1", "main": "H1", "super": "body",
             "place": "body", "episode": "H2", "hole": "H2", "room": "body", "caption": "caption", "disclosure": "disclosure"}
POSITION_Y = {"upper": 0.74, "middle": 0.55, "lower": 0.40}   # Text+ Center y (0 bottom, 1 top), inside the paid 9:16
                                                              # box (y 15–65 % from the top) [assumed]
WEIGHT_STYLE = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold",
                700: "Bold", 800: "ExtraBold", 900: "Black"}   # a weight class → the style name Text+ lists [practitioner]
OUTSIDE_EXT = (".mov", ".mp4", ".mxf", ".webm", ".m4v")         # a rendered title movie (the outside route)
# ⚡ v2.45: what the generated Fusion title does NOT make natively yet (fusion_titles.py §2.2.1 of the plan) — `titles`
# warns, so the gap is a visible decision (HyperFrames needs the owner's words: engine_reason.code = owner)
NATIVE_GAPS = {"per-word": "the words enter together (one fade-rise), not word by word",
               "mask-reveal": "the lines fade and rise in, with no mask",
               "stagger_ms": "the lines enter together, with no stagger",
               "count_ms": "the stat lands on its value without counting",
               "emphasis": "the highlighter sits behind every line, not the one word (phase 1b)",
               "underline": "no underline mark: the emphasised word is not marked"}
MAX_DURATIONS, MAX_CURVES = 5, 3            # constrain the motion palette [Shaw, Design for Motion]
SAID_S_PER_WORD = 0.3                       # text the VO says [PRIMARY · BBC Subtitle Guidelines]
UNSAID_S_PER_WORD = 1.0                     # text only on screen: 1–2 s per word [SECONDARY · Crook & Beare]
SETTLE_S = 0.4                              # a generated clip's head settle (ai-generation.md guardrails)
HERO_MAX_WORDS = 4                          # ads hero line [the jury]
ADS_HERO_MIN_PX = 88                        # hero size at 1920 px tall for 45+ phones [assumed]
DISPLAY_PX = 96                             # above this a text cut shows its seams (optical size) [assumed]
PAIR_WEIGHT_GAP = 200                       # weight classes apart, or another axis [Brown, Coles & Gregory]


# =================================================================================================
# OpenType, read with the stdlib: the few fields the type-system lint needs
# =================================================================================================
def read_font(path: str) -> dict:
    with open(path, "rb") as fh:
        data = fh.read()
    tag = data[:4]
    if tag == b"ttcf":
        off = struct.unpack(">I", data[12:16])[0]                  # the first face of a collection
    elif tag in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        off = 0
    else:
        raise ValueError("not an OpenType/TrueType font (woff/woff2 must be converted first)")
    n = struct.unpack(">H", data[off + 4:off + 6])[0]
    tables = {}
    for i in range(n):
        rec = data[off + 12 + 16 * i: off + 28 + 16 * i]
        t, _, o, ln = struct.unpack(">4sIII", rec)
        tables[t.decode("latin-1")] = (o, ln)
    f = {"path": path, "tables": sorted(tables)}
    if "head" in tables:
        o, _ = tables["head"]; f["units_per_em"] = struct.unpack(">H", data[o + 18:o + 20])[0]
    if "OS/2" in tables:
        o, ln = tables["OS/2"]
        ver = struct.unpack(">H", data[o:o + 2])[0]
        f["weight_class"], f["width_class"], f["fs_type"] = struct.unpack(">HHH", data[o + 4:o + 10])
        f["panose"] = list(data[o + 32:o + 42])
        f["fs_selection"] = struct.unpack(">H", data[o + 62:o + 64])[0]
        if ver >= 2 and ln >= 90:
            f["x_height"], f["cap_height"] = struct.unpack(">hh", data[o + 86:o + 90])
    names = {}
    if "name" in tables:
        o, _ = tables["name"]
        _, count, so = struct.unpack(">HHH", data[o:o + 6])
        for i in range(count):
            pid, eid, lid, nid, ln, no = struct.unpack(">HHHHHH", data[o + 6 + 12 * i: o + 18 + 12 * i])
            raw = data[o + so + no: o + so + no + ln]
            if nid in (1, 2, 4, 13, 14, 16, 17) and nid not in names:
                try:
                    names[nid] = raw.decode("utf-16-be") if pid in (0, 3) else raw.decode("latin-1")
                except UnicodeDecodeError:
                    pass
    f["family"] = names.get(16) or names.get(1) or ""
    f["subfamily"] = names.get(17) or names.get(2) or ""
    f["full_name"] = names.get(4) or ""
    f["licence"] = (names.get(13) or "")[:240]
    f["licence_url"] = names.get(14) or ""
    axes = {}
    if "fvar" in tables:
        o, _ = tables["fvar"]
        ao, _, ac, asz = struct.unpack(">HHHH", data[o + 4:o + 12])
        for i in range(ac):
            b = data[o + ao + i * asz: o + ao + i * asz + 20]
            t, mn, df, mx = struct.unpack(">4siii", b[:16])
            axes[t.decode("latin-1")] = (mn / 65536, df / 65536, mx / 65536)
    f["axes"] = axes
    f["italic"] = bool(f.get("fs_selection", 0) & 1) or "ital" in axes or "slnt" in axes \
        or "italic" in (f["subfamily"] + f["full_name"]).lower()
    return f


def faux(font: dict, weight: int, italic: bool) -> list:
    """Faux styles: the browser fakes a weight or an italic the file does not have (Stocks: never)."""
    P = []
    w = font.get("axes", {}).get("wght")
    if w:
        if not (w[0] - 1 <= weight <= w[2] + 1):
            P.append(f"weight {weight} is outside the file's wght axis {w[0]:g}–{w[2]:g}: it would be faked")
    elif abs(int(font.get("weight_class", 400)) - int(weight)) > 50:
        P.append(f"the file is weight {font.get('weight_class')}, the card asks for {weight}: a faux bold or light")
    if italic and not font.get("italic"):
        P.append("the card asks for italic and the file is upright: a faux italic")
    return P


SERIF_NAMES = ("serif", "garamond", "caslon", "baskerville", "bodoni", "didot", "times", "georgia", "lora",
               "merriweather", "playfair", "cormorant", "crimson", "spectral", "fraunces", "literata", "charter",
               "tinos", "caladea", "cambria", "minion", "sabon", "canela", "tiempos", "sectra", "bembo", "mrs eaves",
               "freight", "domaine", "ogg", "recoleta", "gelasio", "noto serif", "pt serif", "ibm plex serif")
SANS_NAMES = ("sans", "grotesk", "grotesque", "inter", "helvetica", "arial", "roboto", "poppins", "montserrat", "lato",
              "gotham", "futura", "avenir", "proxima", "manrope", "work sans", "neue", "gilroy", "circular", "satoshi",
              "general sans", "basement", "akzidenz", "univers", "frutiger", "nunito", "raleway", "barlow", "outfit")


def classify(f: dict) -> str | None:
    """serif or sans: from PANOSE when the file fills it in, else from the family name [practitioner]."""
    p = f.get("panose") or [0] * 10
    if p[0] == 2 and p[1]:
        return "sans" if p[1] in (11, 12, 13) else ("serif" if 2 <= p[1] <= 10 else None)
    n = (f.get("family") or "").lower()
    if any(k in n for k in ("mono", "code")):
        return "mono"
    if any(k in n for k in SERIF_NAMES) and "sans" not in n:
        return "serif"
    if any(k in n for k in SANS_NAMES):
        return "sans"
    return None


def pair_axes(a: dict, b: dict) -> dict:
    """Where an anchor and its companion differ (Brown, Coles & Gregory: weight, width, stroke contrast).
    `unknown` means the files could not say (no PANOSE, an unfamiliar name), not that they match."""
    pa, pb = a.get("panose") or [0] * 10, b.get("panose") or [0] * 10
    ca, cb = classify(a), classify(b)
    return {"weight": abs(int(a.get("weight_class", 400)) - int(b.get("weight_class", 400))) >= PAIR_WEIGHT_GAP,
            "width": a.get("width_class", 5) != b.get("width_class", 5),
            "contrast": bool(pa[4] and pb[4] and abs(pa[4] - pb[4]) >= 2),
            "serif_vs_sans": bool(ca and cb and ca != cb),
            "unknown": not (ca and cb)}


# =================================================================================================
# the card
# =================================================================================================
def load_card(path: str) -> dict:
    c = json.load(open(path, encoding="utf-8"))
    c["__path"] = os.path.abspath(path)
    return c


def sizes(card: dict, height: int = 1920) -> dict:
    sc = card.get("scale") or {}
    b, r = float(sc.get("base_px") or 0), float(sc.get("ratio") or 0)
    return {s: round(b * r ** i * height / 1920) for i, s in enumerate(STEPS)}


def _font_path(card: dict, f: dict) -> str | None:
    p = (f or {}).get("file")
    if not p:
        return None
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(os.path.dirname(card["__path"]), p))


BLUR_KITS = ("hero-line", "lockup")          # (v2.48.0, project switch blur-titles) a brand line, a lockup or a small mark (never the hook card)


def lint_card(card: dict, job: str | None = None) -> tuple[list, list]:
    """(problems that refuse, warnings) for one card. `job` (or the job holding the card's file) is read for its
    project switches (v2.48.0): `blur-titles` lifts the ads lane's no-blur rule for a brand line, a lockup or a small mark (never the hook card)."""
    P, W = [], []
    blob = json.dumps({k: v for k, v in card.items() if k != "__path"})
    if "BRAND" in blob:
        P.append("a BRAND placeholder is still on the card (colours or background): set the brand's value")
    lane = card.get("lane")
    kinds = card.get("kinds") or {}
    if lane not in ("ads", "brand", "drama", "golf", "property", "captions-only", "product"):
        P.append(f"lane {lane!r}: one of ads, brand, drama, golf, property, product, captions-only")
    S = sizes(card)
    sc = card.get("scale") or {}
    if not (float(sc.get("base_px") or 0) > 0 and 1.05 <= float(sc.get("ratio") or 0) <= 1.7):
        P.append("scale: base_px > 0 and one ratio between 1.05 and 1.7 (one type scale, K2)")
    fonts = card.get("fonts") or {}
    parsed = {}
    if kinds:
        for role in ("anchor", "companion"):
            f = fonts.get(role)
            if not f:
                P.append(f"fonts.{role} is missing: a title card names its anchor face and its companion")
                continue
            p = _font_path(card, f)
            if not p or not os.path.isfile(p):
                P.append(f"fonts.{role}: the file {f.get('file')!r} is missing — a brand font is a file, so every machine renders the same letters")
                continue
            try:
                ft = read_font(p)
            except (ValueError, struct.error, OSError) as e:
                P.append(f"fonts.{role}: {os.path.basename(p)} cannot be read ({e})"); continue
            parsed[role] = ft
            for x in faux(ft, int(f.get("weight") or 400), bool(f.get("italic"))):
                P.append(f"fonts.{role} ({os.path.basename(p)}): {x}")
            if ft.get("fs_type", 0) & 0x0002:
                W.append(f"fonts.{role}: the file declares restricted-licence embedding — burning text into video "
                         f"is usually covered by a desktop licence, but confirm it: {ft.get('licence')[:100] or 'no licence text in the file'}")
            big = S["hero"] if role == "anchor" else S["title"]
            name = (ft.get("family", "") + " " + ft.get("subfamily", "")).lower()
            if big >= DISPLAY_PX and re.search(r"\b(text|caption)\b", name) and "opsz" not in ft.get("axes", {}):
                W.append(f"fonts.{role}: a text cut ({ft.get('family')} {ft.get('subfamily')}) set at {big} px — use the "
                         f"family's display cut or an opsz axis (Stocks: optical size)")
        if "anchor" in parsed and "companion" in parsed:
            same = parsed["anchor"].get("family") == parsed["companion"].get("family")
            ax = pair_axes(parsed["anchor"], parsed["companion"])
            differ = any(v for k, v in ax.items() if k != "unknown")
            if not differ and ax["unknown"] and not same:
                W.append(f"the files do not say whether {parsed['anchor'].get('family')} and "
                         f"{parsed['companion'].get('family')} differ in class or contrast (no PANOSE): check by eye "
                         f"that the pair differs on weight, width or stroke contrast")
            elif not differ:
                P.append("the anchor and companion sit on the same weight, width and stroke contrast: the pair "
                         "reads as redundant (Brown, Coles & Gregory) — change one axis")
            elif same and not ax["weight"]:
                W.append("one family for both roles: fine as a superfamily, if the weights are well apart")
    M = card.get("motion") or {}
    ens = [M.get("enter") or {}] + [k.get("enter") for k in kinds.values() if k.get("enter")]
    exs = [M.get("exit") or {}] + [k.get("exit") for k in kinds.values() if k.get("exit")]
    durs, curves = set(), set()
    for e in ens + exs:
        if e.get("ms"):
            durs.add(int(e["ms"]))
        if e.get("ease"):
            curves.add(tuple(e["ease"]))
    for k in ("mark_ms", "count_ms"):
        if M.get(k):
            durs.add(int(M[k]))
    if len(durs) > MAX_DURATIONS:
        P.append(f"{len(durs)} durations in the motion tokens ({sorted(durs)}): constrain to {MAX_DURATIONS} (Shaw)")
    if len(curves) > MAX_CURVES:
        P.append(f"{len(curves)} curves in the motion tokens: constrain to {MAX_CURVES} (Shaw)")
    # (v2.48.0, project switch blur-titles) whose entrance each one is — the card's own (every title) or one kind's — and
    # the job's switch, read only when the ads lane carries a blur at all
    owners = [None] + [n for n, k in kinds.items() if k.get("enter")]
    bt = None
    if lane == "ads" and any(((e or {}).get("family") or (M.get("enter") or {}).get("family")) in ADS_NO_ENTER for e in ens):
        import job_tier, switches
        bt = switches.on(job or (job_tier.job_root(card["__path"]) if card.get("__path") else None), "blur-titles")
    for e, who in zip(ens, owners):
        fam = (e or {}).get("family") or (M.get("enter") or {}).get("family")
        if fam and fam not in ENTER:
            P.append(f"entrance family {fam!r}: one of {', '.join(ENTER)}")
        if lane == "ads" and fam in ADS_NO_ENTER:
            rule = f"entrance {fam!r} in the ads lane: no blur, glow or scramble for the 45+ phone audience"
            kit = (kinds.get(who) or {}).get("kit") if who else None
            if bt and kit in BLUR_KITS:     # (v2.48.0, project switch blur-titles) a brand line, a lockup or a small mark (never the hook card): lifted
                W.append(f"kinds.{who} ({kit}): {rule} — {switches.lifted('blur-titles', bt)}")
            elif bt:
                P.append(f"{rule} — project switch `blur-titles` lifts it only for a brand line, a lockup or a small mark (never the hook card) "
                         f"({', '.join(BLUR_KITS)} kinds' own entrance), not for "
                         + ("every title (motion.enter)" if who is None else f"kinds.{who} ({kit})"))
            else:
                P.append(rule)
    for e in exs:
        fam = (e or {}).get("family")
        if fam and fam not in EXIT:
            P.append(f"exit family {fam!r}: one of {', '.join(EXIT)}")
    for c in curves:
        if len(c) != 4 or not (0 <= c[0] <= 1 and 0 <= c[2] <= 1):
            P.append(f"curve {list(c)}: a cubic-bezier [x1, y1, x2, y2] with x in [0, 1]")
        elif not (0 <= c[1] <= 1 and 0 <= c[3] <= 1):
            P.append(f"curve {list(c)} overshoots (y outside [0, 1]): no overshoot on text, numbers or UI (house rule C2)")
    for name, k in kinds.items():
        if k.get("kit") not in KITS:
            P.append(f"kinds.{name}: kit {k.get('kit')!r} — one of {', '.join(KITS)}")
        if lane == "ads" and k.get("kit") == "hero-line" and int(k.get("max_words") or 99) > HERO_MAX_WORDS:
            P.append(f"kinds.{name}: an ads hero line is at most {HERO_MAX_WORDS} words (the jury)")
    if lane == "ads" and any(k.get("kit") == "hero-line" for k in kinds.values()) and S["hero"] < ADS_HERO_MIN_PX:
        W.append(f"the hero size is {S['hero']} px at 1920 tall; for 45+ phones aim for ≥ {ADS_HERO_MIN_PX} [assumed — title_qa measures the real cap height]")
    tr = card.get("transitions") or {}
    if len(tr.get("accents") or []) > int(tr.get("max_accents", 2)) or int(tr.get("max_accents", 2)) > 2:
        P.append("transitions: one primary and at most 2 accents per film (the jury; HyperFrames' motion rules)")
    rp = card.get("ramps") or {}
    if int(rp.get("max_per_video", 2)) > 2 or float(rp.get("per_20s", 1)) > 1:
        P.append("ramps: at most 1 per 20 s and 2 per video (house rule C4)")
    sf = card.get("style_frame")
    if kinds and not sf:
        W.append("no style frame — agree one still (typeface, type scale, ink on paper and on footage, left margin, the "
                 "emphasis device) before any title is built: `title_card.py style-frame`")
    elif sf:
        sc_ = sf.get("scale") or {}
        bad = [k for k in STYLE_STEPS if not isinstance(sc_.get(k), (int, float)) or not 0.02 <= float(sc_[k]) <= 0.3]
        if bad:
            P.append(f"style frame: the type scale needs {', '.join(bad)} as Text+ sizes between 0.02 and 0.3")
        if sf.get("align") not in ("left", "centre"):
            P.append("style frame: align is left or centre")
        if not 0.04 <= float(sf.get("margin_left_x") or 0) <= 0.3:
            P.append("style frame: margin_left_x is a share of the frame width, 0.04–0.3 (a supplement ad job used 0.115)")
        if sf.get("centre", "frame") != "frame":
            P.append("style frame: centre on the FRAME (x 0.5). The safe box limits where ink may reach; it is not the "
                     "centre line (a supplement ad job: cards centred on the box's middle, x 447 of 1080, read off-centre)")
        for k, v in (sf.get("ink") or {}).items():
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(v)):
                P.append(f"style frame: ink {k} {v!r} is not a #RRGGBB colour")
        em = sf.get("emphasis") or {}
        if em and em.get("device") not in ("highlighter", "colour", "weight", "underline", "none"):
            P.append("style frame: one emphasis device for the whole ad — highlighter, colour, weight, underline or none")
    return P, W


def style_frame_ok(job: str, card: dict) -> list:
    """What a title made in Resolve needs first: an approved style frame, its still on disk."""
    sf = card.get("style_frame") or {}
    still = sf.get("approved_still")
    sp = os.path.join(job, still) if still and not os.path.isabs(still) else still
    if not sf or not still or not os.path.isfile(sp or "") or not (sf.get("approved") or {}).get("quote"):
        return ["no approved style frame — one still with the typeface, the type scale (H1 · H2 · body · caption · "
                "disclosure), the ink on paper and on footage, the left margin and the one emphasis device, approved with "
                "the storyboard: `title_card.py style-frame <job> --still 00-brief/STYLE-FRAME.png --by <who> --quote "
                "\"…\"` (a supplement ad job: six design rounds that a style frame would have settled)"]
    return []


def _hex01(h: str) -> list:
    h = str(h).lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def style_of(card: dict, role: str = "anchor") -> tuple:
    """(font, style) as Text+ names them, from the card. Font: the style frame's, else the face's family. Style: the
    style frame's, else the face's own `style`, else the font FILE's own style name (name table id 17/2) when the file is
    not variable, else the weight mapped to a name (700 → Bold). ⚡ v2.45: the weight was never turned into a Style, so a
    native Poppins 700 title came out Poppins Regular (resolve-native-titles-plan §1.2 C-A.2). (None, None) without a face."""
    sf = (card.get("style_frame") or {}) if role == "anchor" else {}
    f = (card.get("fonts") or {}).get(role) or {}
    font = sf.get("font") or f.get("family")
    if not font:
        return None, None
    style = sf.get("style") or f.get("style")
    p = _font_path(card, f) if f else None
    if not style and p and os.path.isfile(p):
        try:
            ft = read_font(p)
            if "wght" not in (ft.get("axes") or {}) and ft.get("subfamily"):
                style = ft["subfamily"]
        except (ValueError, struct.error, OSError):
            pass
    if not style:
        w = int(round(int(f.get("weight") or 400) / 100.0) * 100)
        style = WEIGHT_STYLE.get(min(900, max(100, w)), "Regular")
        if f.get("italic"):
            style = "Italic" if style == "Regular" else f"{style} Italic"
    return font, style


def rgba01(s) -> list:
    """'rgba(10,10,12,0.72)' or '#RRGGBB' → [r, g, b, a] in 0–1."""
    m = re.match(r"\s*rgba?\(([^)]+)\)", str(s or ""))
    if m:
        p = [float(x) for x in m.group(1).split(",")]
        return [p[0] / 255, p[1] / 255, p[2] / 255, p[3] if len(p) > 3 else 1.0]
    if re.fullmatch(r"#?[0-9A-Fa-f]{6}", str(s or "").strip()):
        return _hex01(str(s).strip()) + [1.0]
    return [0.0, 0.0, 0.0, 0.0]


CALIBRATION = os.path.join(SKILL, "assets", "fusion-calibration.json")


def calibration(fmt_name: str = "vertical-1080") -> dict | None:
    """The Text+ ↔ pixel calibration for a format, MEASURED in Resolve (the console's CALIBRATE_TEXT stills; the plan
    §2.2.5) — or None. Until it exists, positions and `fit` use the style frame's values, marked [assumed]: nothing here
    invents the mapping."""
    try:
        c = json.load(open(CALIBRATION, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    f = (c.get("formats") or {}).get(fmt_name)
    return dict(f, resolve=c.get("resolve"), measured=c.get("measured")) if f and c.get("measured") else None


def layout_for(card: dict) -> dict:
    """{kind: {Text+ input: value}} from the style frame — what `native.py console` hands PLACE_TITLES and what
    `fusion_titles.py` writes into each generated template. '_emphasis' holds the highlighter (element 3: ElementShape3 2,
    Offset3 {0, 0}, Level3 1 — measured on a supplement ad job). A kind with a plate (`plate: true`) carries the card's
    `colors.plate` on element 3 instead [element 3 as a plate: assumed until the live test L1-g reads its inputs]."""
    sf = {**STYLE_DEFAULT, **(card.get("style_frame") or {})}
    sc_ = {**STYLE_DEFAULT["scale"], **(sf.get("scale") or {})}
    font, style = style_of(card)
    out = {}
    kinds = dict(card.get("kinds") or {})
    kinds.setdefault("caption", {"position": "lower"})
    kinds.setdefault("disclosure", {"position": "upper"})
    for kind, K in kinds.items():
        step = (sf.get("kind_step") or {}).get(kind) or KIND_STEP.get(kind, "body")
        on = "paper" if K.get("page_bg") or K.get("on") == "paper" else "footage"
        ink = _hex01((sf.get("ink") or {}).get(on) or ("#19191C" if on == "paper" else "#FFFFFF"))
        y = POSITION_Y.get(K.get("position") or "upper", 0.74)
        L = {"Size": float(sc_.get(step, 0.07)), "Red1": ink[0], "Green1": ink[1], "Blue1": ink[2]}
        if font:
            L["Font"] = font
            L["Style"] = style
        if K.get("plate"):
            pr, pg, pb, pa = rgba01((card.get("colors") or {}).get("plate"))
            L.update({"Enabled3": 1, "ElementShape3": 2, "Offset3": [0, 0], "Level3": 1,
                      "Red3": pr, "Green3": pg, "Blue3": pb, "Alpha3": pa})
        if (K.get("align") or sf.get("align")) == "centre":
            L.update({"HorizontalLeftCenterRight": 0, "HorizontalJustificationNew": 1, "Center": [0.5, y]})
        else:
            L.update({"HorizontalLeftCenterRight": -1, "HorizontalJustificationNew": 0,
                      "Center": [float(sf.get("margin_left_x") or 0.115), y]})
        out[kind] = L
    em = sf.get("emphasis") or {}
    if em.get("device") == "highlighter":
        c = _hex01(em.get("color") or "#FFE778")
        out["_emphasis"] = {"Enabled3": 1, "ElementShape3": 2, "Offset3": [0, 0], "Level3": 1,
                            "Red3": c[0], "Green3": c[1], "Blue3": c[2]}
    return out


def style_frame(job: str, still: str, by: str, quote: str, **tokens) -> dict:
    """Record the approved style frame on the card (and any tokens given)."""
    p = os.path.join(job, CARD)
    card = load_card(p)
    sp = os.path.join(job, still) if not os.path.isabs(still) else still
    if not os.path.isfile(sp):
        raise SystemExit(f"error: no still at {still} — render the style frame in Resolve (a still, "
                         f"Project.ExportCurrentFrameAsStill) and approve that")
    if not by.strip() or len(quote.split()) < 2:
        raise SystemExit("error: --by and --quote (the approver's words, two words or more)")
    sf = {**STYLE_DEFAULT, **(card.get("style_frame") or {})}
    for k, v in tokens.items():
        if v is not None:
            sf[k] = v
    sf["approved_still"] = os.path.relpath(sp, job) if sp.startswith(os.path.abspath(job)) else still
    sf["approved"] = {"by": by.strip(), "quote": quote.strip(), "sha256": _sha(sp),
                      "at": dt.datetime.now().isoformat(timespec="minutes")}
    card["style_frame"] = sf
    json.dump({k: v for k, v in card.items() if k != "__path"}, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return sf


def propose(job: str, lane: str, anchor=None, companion=None, accent=None, page_bg=None, genre=None,
            force: bool = False) -> str:
    L = json.load(open(LANES, encoding="utf-8"))["lanes"]
    if lane not in L:
        raise SystemExit(f"error: lane {lane!r} — one of {', '.join(L)}")
    out = os.path.join(job, CARD)
    if os.path.exists(out) and not force:
        raise SystemExit(f"error: {CARD} exists — edit it, or --force to start again from the {lane} defaults")
    c = json.loads(json.dumps(L[lane]))
    c = {"job": os.path.basename(os.path.abspath(job)), "lane": lane, "genre": genre or "",
         "proposed": dt.datetime.now().isoformat(timespec="minutes"), **c}
    c["fonts"] = {}
    c.setdefault("native", dict(NATIVE))
    if c.get("kinds"):
        c.setdefault("style_frame", json.loads(json.dumps(STYLE_DEFAULT)))
    for role, spec in (("anchor", anchor), ("companion", companion)):
        if spec:
            c["fonts"][role] = spec
    if accent:
        c["colors"]["accent"] = accent
    for k in (c.get("kinds") or {}).values():
        if k.get("page_bg") == "BRAND" and page_bg:
            k["page_bg"] = page_bg
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(c, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    write_md(job, c)
    return out


def write_md(job: str, c: dict) -> str:
    S = sizes(c)
    F = c.get("fonts") or {}
    L = [f"# Title card — {c.get('job')}", "",
         f"Lane **{c.get('lane')}**{' · genre: ' + c['genre'] if c.get('genre') else ''}. The permission list for "
         f"on-screen titles (house rule C3): captions stay, and only the kinds below are rendered. Approved "
         f"with the storyboard; picture lock refuses without a clean card (`title_card.py lint`).", "",
         "| Role | Face | Weight | File |", "|---|---|---|---|"]
    for r in ("anchor", "companion"):
        f = F.get(r) or {}
        L.append(f"| {r} | {f.get('family', '—')} | {f.get('weight', '—')} | {f.get('file', '—')} |")
    L += ["", f"Scale: base {c['scale']['base_px']} px × {c['scale']['ratio']} → " +
          " · ".join(f"{k} {v}" for k, v in S.items()) + " px at 1920 tall. Case: "
          f"{c.get('text_case')}; tracking {c.get('tracking_em')} em.",
          f"Colours: text {c['colors'].get('fg')}, accent {c['colors'].get('accent')}, plate {c['colors'].get('plate')}.",
          f"Motion ({(c.get('motion') or {}).get('energy')}): enter {c['motion']['enter']['family']} "
          f"{c['motion']['enter']['ms']} ms {c['motion']['enter']['ease']}, exit {c['motion']['exit']['family']} "
          f"{c['motion']['exit']['ms']} ms. No overshoot on text (C2).", "",
          "| Kind | Kit | Where | Limits |", "|---|---|---|---|"]
    for name, k in (c.get("kinds") or {}).items():
        lim = ", ".join(f"{x} {k[x]}" for x in ("max_words", "max_count", "min_hold_s") if k.get(x))
        L.append(f"| {name} | {k.get('kit')} | {k.get('position', 'middle')} | {lim or '—'} |")
    if not c.get("kinds"):
        L.append("| — | captions only | — | — |")
    tr, rp = c.get("transitions") or {}, c.get("ramps") or {}
    L += ["", f"Transitions: {tr.get('primary', 'hard cut')} as the primary; accents "
          f"{', '.join(tr.get('accents') or []) or 'none yet'} (at most {tr.get('max_accents', 2)}).",
          f"Ramps: at most {rp.get('max_per_video', 2)} per video and {rp.get('per_20s', 1)} per 20 s (C4)."]
    p = os.path.join(job, "00-brief", "TITLE-CARD.md")
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return p


# =================================================================================================
# title specs against the card
# =================================================================================================
def _words(spec: dict) -> int:
    C = spec.get("content") or {}
    txt = " ".join(str(x) for x in (C.get("lines") or []) + [C.get(k) for k in ("line", "title", "subtitle", "kicker",
                   "label", "place", "time", "price", "was", "note", "url") if C.get(k)])
    return len([w for w in re.split(r"\s+", txt) if w])


def specs(job: str) -> list:
    d = os.path.join(job, TITLES)
    return sorted(p for p in glob.glob(os.path.join(d, "*.title.json")) if not re.search(r"\.opt\d+\.title\.json$", p))


def _cuts(job: str) -> dict:
    p = os.path.join(job, "07-edit", "timeline-dump.json")
    if not os.path.isfile(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    fps = float(d.get("fps") or 24)
    v1 = (d.get("tracks") or {}).get("video1") or []
    cuts = sorted({round(i["start"] / fps, 3) for i in v1 if i.get("type") in (None, "video")})
    trans = [(i["start"] / fps, (i["start"] + i["duration"]) / fps) for t in (d.get("tracks") or {}).values()
             for i in t if i.get("type") == "transition"]
    return {"fps": fps, "cuts": cuts, "transitions": trans}


def _ramps(job: str) -> list:
    out = []
    for p in glob.glob(os.path.join(job, "01-script", "prompts", "*.clip.prompt.md")):
        m = re.search(r"^ramp:\s*(.+)$", open(p, encoding="utf-8").read(), re.M)
        if m:
            kv = dict(x.split("=", 1) for x in re.split(r"\s*[,;]\s*", m.group(1).strip()) if "=" in x)
            if kv.get("cut_in") and kv.get("cut_out"):
                try:
                    out.append((float(kv["cut_in"]), float(kv["cut_out"])))
                except ValueError:
                    pass
    return out


def outside_renders(job: str, tid: str) -> list:
    """Rendered movies beside a title spec: <id>.mov, <id>_*.mov, <id>.optN.mov (and mp4, mxf, webm, m4v) in
    07-edit/titles/ — not another spec's own render (<id>_b.mov when <id>_b.title.json exists), not _superseded/."""
    base = os.path.join(job, TITLES, tid)
    hits = glob.glob(glob.escape(base) + ".*") + glob.glob(glob.escape(base) + "_*")
    out = []
    for h in sorted(set(hits)):
        if not h.lower().endswith(OUTSIDE_EXT) or not os.path.isfile(h):
            continue
        stem = os.path.basename(h).split(".")[0]
        if stem != tid and os.path.isfile(os.path.join(job, TITLES, stem + ".title.json")):
            continue                                    # another spec's own render
        out.append(h)
    return out


def fusion_gaps(card: dict, kind: str, spec: dict | None = None) -> list:
    """What the generated Fusion title does instead of a card token or kit feature it does not make natively yet (the
    plan §2.2.1 and §4.5). A WARN in `titles`: the gap is a visible decision, and HyperFrames needs the owner's words."""
    M, K = card.get("motion") or {}, (card.get("kinds") or {}).get(kind) or {}
    en = {**(M.get("enter") or {}), **(K.get("enter") or {})}
    C = (spec or {}).get("content") or {}
    out = []
    fam = en.get("family")
    if fam in ("per-word", "mask-reveal"):
        out.append(f"entrance {fam}: natively {NATIVE_GAPS[fam]}")
    lines = len(C.get("lines") or []) if spec else 2
    if (M.get("stagger_ms") or 0) and lines > 1 and fam not in ("cut",):
        out.append(f"stagger {M.get('stagger_ms')} ms: natively {NATIVE_GAPS['stagger_ms']}")
    if K.get("kit") == "stat":
        out.append(f"count {M.get('count_ms') or 900} ms: natively {NATIVE_GAPS['count_ms']}")
    sf = card.get("style_frame") or {}
    dev = (sf.get("emphasis") or {}).get("device")
    if spec and C.get("emphasis"):
        if dev == "underline" or C.get("mark") == "underline":
            out.append(f"emphasis \u201c{C.get('emphasis')}\u201d: natively {NATIVE_GAPS['underline']}")
        elif dev in (None, "highlighter"):
            out.append(f"emphasis \u201c{C.get('emphasis')}\u201d: natively {NATIVE_GAPS['emphasis']}")
    return [x + " — if the look needs it, that is the owner's call (engine hyperframes, engine_reason code owner)"
            for x in out]


TITLE_MEDIA_RE = re.compile(r"(?:^|[/\\])(?:07-edit[/\\](?:titles|disclosure)|08-captions)[/\\][^/\\]*\.(?:mov|mp4|mxf|webm|m4v)$"
                            r"|(?:^|[/\\])[^/\\]*(?:_alpha|overlay[_-]?supers|TEXT-CARRIER|CAPTIONS_)[^/\\]*\.(?:mov|mp4|mxf|webm|m4v)$",
                            re.I)


def timeline_title_media(job: str, dump_p: str | None = None) -> list:
    """⚡ v2.45 (the author: "It keeps making mp4s which it imports"): every video item on the timeline (07-edit/
    timeline-dump.json, DUMP_TIMELINE_JSON) whose media file is a title, caption or disclosure movie — under
    07-edit/titles/, 08-captions/ or 07-edit/disclosure/, named *_alpha*, *overlay*supers*, TEXT-CARRIER* or CAPTIONS_*,
    or named after a title spec (<id>.mov) — with no reasoned spec (an outside engine and a valid engine_reason) and no
    valid <file>.external.json. A dump older than v2.45 carries no `file`: the clip's name is matched instead."""
    dump_p = dump_p or os.path.join(job, "07-edit", "timeline-dump.json")
    try:
        d = json.load(open(dump_p, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    import native  # noqa: E402  (stdlib-only on this path)
    ids = {os.path.basename(p)[: -len(".title.json")]: p for p in specs(job)}
    P = []
    for k, rows in (d.get("tracks") or {}).items():
        if not str(k).startswith("video"):
            continue
        for r in rows or []:
            if r.get("type") == "transition":
                continue
            f = str(r.get("file") or "")
            nm = str(r.get("name") or "")
            stem = os.path.basename(f or nm).split(".")[0]
            sid = next((i for i in ids if stem == i or stem.startswith(i + "_")), None)
            hit = bool(TITLE_MEDIA_RE.search(f.replace("\\", "/"))) if f else False
            hit = hit or bool(TITLE_MEDIA_RE.search(nm)) or (sid is not None and nm.lower().endswith(OUTSIDE_EXT))
            if not hit:
                continue
            spec = (native.jload(ids[sid]) or {}) if sid else {}
            if sid and native.engine_of(spec) != "resolve" and not native.check_reason(spec.get("engine_reason")):
                continue                                # an outside title with the owner's (or another) reason
            fp = f if os.path.isabs(f) else os.path.join(job, f)
            local = fp if os.path.isfile(fp) else os.path.join(job, TITLES, os.path.basename(f or nm))
            rec = native.jload(native.record_path(local)) if os.path.isfile(local) else None
            if rec and not native.check_reason(rec.get("reason")):
                continue
            names = (d.get("track_names") or {}).get(k) or k
            P.append(f"the timeline carries {f or nm} on {names} at {r.get('start_s')} s — an imported title, caption or "
                     f"disclosure movie (house rule C7; v2.45: \"It keeps making mp4s which it imports\"). Titles are "
                     f"placed by PLACE_TITLES (fusion_titles.py build → native.py console <job>), never imported: replace "
                     f"it with the native title, or name the engine and the owner's reason in "
                     f"{os.path.relpath(ids[sid], job) if sid else 'its spec'} (native.py record for a file with no spec)")
    return P


def check_titles(job: str, card: dict) -> tuple[list, list]:
    P, W = [], []
    kinds = card.get("kinds") or {}
    M = card.get("motion") or {}
    counts = {}
    cut = _cuts(job)
    ramps = _ramps(job)
    for p in specs(job):
        rel = os.path.relpath(p, job)
        try:
            s = json.load(open(p, encoding="utf-8"))
        except ValueError:
            P.append(f"{rel}: not valid JSON"); continue
        eng = str(s.get("engine") or "resolve").strip().lower()
        tid = os.path.basename(p)[: -len(".title.json")]
        if eng not in ENGINES:
            P.append(f"{rel}: engine {eng!r} — one of {', '.join(ENGINES)}; resolve is the default (house rule C7)")
        elif eng != "resolve":
            import native  # noqa: E402  (stdlib-only on this path)
            P += native.check_reason(s.get("engine_reason"), f"{rel} (engine {eng})")
            if not native.check_reason(s.get("engine_reason")) and (s.get("engine_reason") or {}).get("code") != "owner":
                W.append(f"{rel}: made outside Resolve by {eng} for a `{(s.get('engine_reason') or {}).get('code')}` "
                         f"reason — a title look is the owner's call (code owner) unless the job has no Resolve timeline")
        else:
            # ⛔ v2.45 (2026-10-29: "It keeps making mp4s which it imports"): a supplement ad job's six specs named no
            # engine — so they read as made in Resolve — while HyperFrames movies sat beside them, imported onto V2
            import native  # noqa: E402
            for r_ in outside_renders(job, tid):
                mk = native.render_maker(r_)
                P.append(f"{rel}: made in Resolve by its spec (house rule C7), but {os.path.relpath(r_, job)} sits beside it"
                         f"{' (' + mk + ')' if mk else ''}. A title is placed by PLACE_TITLES, never imported: move the render "
                         f"to 07-edit/titles/_superseded/, or name the engine and the owner's reason in the spec "
                         f"(\"engine\": \"hyperframes\", \"engine_reason\": {{\"code\": \"owner\", \"why\": …, \"quote\": …}})")
        kind = s.get("kind")
        K = kinds.get(kind)
        if not K:
            P.append(f"{rel}: kind {kind!r} is not on the title card — the card is the permission list (C3)"); continue
        counts[kind] = counts.get(kind, 0) + 1
        if eng == "resolve":
            W += [f"{rel}: {x}" for x in fusion_gaps(card, kind, s)]
        if s.get("kit") and s["kit"] != K.get("kit"):
            P.append(f"{rel}: kit {s['kit']} — the card gives {kind} the {K.get('kit')} kit")
        n = _words(s)
        if K.get("max_words") and n > int(K["max_words"]):
            P.append(f"{rel}: {n} words — {kind} allows {K['max_words']} (fewer words, never smaller type)")
        en = {**(M.get("enter") or {}), **(K.get("enter") or {})}
        ex = {**(M.get("exit") or {}), **(K.get("exit") or {})}
        lines = len((s.get("content") or {}).get("lines") or [1])
        units = n if en.get("family") == "per-word" else lines
        enter_s = (en.get("ms", 600) + (M.get("stagger_ms") or 0) * max(0, units - 1)) / 1000
        extra = 0.0
        if K.get("kit") in ("hero-line",) and (s.get("content") or {}).get("emphasis"):
            extra = 0.12 + (M.get("mark_ms") or 350) / 1000
        if K.get("kit") == "stat":
            extra = max(0.0, (M.get("count_ms") or 900) / 1000 - en.get("ms", 600) / 1000 * 0.5)
        exit_s = 0 if ex.get("family") == "cut" else (ex.get("ms") or 300) / 1000
        dur = float(s.get("duration_s") or 0)
        hold = dur - enter_s - extra - exit_s
        floor = n * (SAID_S_PER_WORD if s.get("said_by_vo") else UNSAID_S_PER_WORD)
        if K.get("min_hold_s"):
            floor = max(floor, float(K["min_hold_s"]))
        if hold + 1e-6 < floor:
            P.append(f"{rel}: holds {hold:.2f} s still and legible; {n} word(s) "
                     f"{'the VO says' if s.get('said_by_vo') else 'only on screen'} need {floor:.2f} s — "
                     f"duration_s {dur} → {enter_s + extra + exit_s + floor:.2f}")
        a = s.get("anchor") or {}
        at = s.get("at_s")
        if at is None or not a.get("type"):
            P.append(f"{rel}: no anchor — a title lands on a picture event (`at_s` and `anchor`: "
                     f"cut | settle | beat | join | event, with its time)"); continue
        at = float(at)
        if cut.get("cuts"):
            fr = 1.0 / cut["fps"]
            if a.get("at_s") is not None and abs(float(a["at_s"]) - at) > 2 * fr + 1e-6:
                P.append(f"{rel}: starts at {at:.3f} s, its anchor is at {float(a['at_s']):.3f} s (more than 2 frames apart)")
            prev = max([c for c in cut["cuts"] if c <= at + 1e-6] or [None]) if cut["cuts"] else None
            if prev is not None and 0 <= at - prev < SETTLE_S - 1e-6 and not s.get("masks_settle"):
                P.append(f"{rel}: enters {at - prev:.2f} s after the cut at {prev:.2f} s — inside the clip's "
                         f"{SETTLE_S} s settle; enter after it, or declare `masks_settle` (house rule C1)")
            for t0, t1 in cut.get("transitions", []):
                if at < t1 and at + dur > t0:
                    P.append(f"{rel}: on screen across a transition ({t0:.2f}–{t1:.2f} s): titles never span a non-cut join")
        else:
            W.append(f"{rel}: no 07-edit/timeline-dump.json — the anchor and transition checks did not run "
                     f"(resolve-production-console.py DUMP_TIMELINE_JSON)")
        for t0, t1 in ramps:
            if at < t1 and at + dur > t0:
                P.append(f"{rel}: on screen across a ramp ({t0:.2f}–{t1:.2f} s): land the title after the ramp's settle")
    for kind, n in counts.items():
        mx = (kinds.get(kind) or {}).get("max_count")
        if mx and n > int(mx):
            P.append(f"{kind}: {n} titles — the card allows {mx}")
    hero = [p for p in specs(job) if (json.load(open(p, encoding="utf-8")) or {}).get("hero_beat")]
    if len(hero) > 2:
        P.append(f"{len(hero)} hero beats — one or two per video (T20), or none of them reads as the signature")
    return P, W


def _native_ok(job: str, p: str, s: dict) -> list:
    """A title made in Resolve: a passing `title_qa.py native` report, on the spec as it is now and on renders that
    still exist as they were measured; and, when the console placed it, its words read back as the spec's."""
    P = []
    base = p[: -len(".title.json")]
    tid = os.path.basename(base)
    relp = os.path.relpath(p, job)
    rp = base + ".native.qa.json"
    how = (f"`title_qa.py native <job> --title {tid} --with <Resolve's render, titles on> --without <the same, "
           f"render-mp4.py TITLES_OFF>`")
    r = json.load(open(rp, encoding="utf-8")) if os.path.isfile(rp) else None
    if r is None:
        P.append(f"{relp}: made in Resolve and not measured yet — {how}")
    elif r.get("spec_sha256") != _sha(p):
        P.append(f"{relp}: the spec changed after its title was measured — place it again if the words or timing moved, then {how}")
    else:
        for k in ("with", "without"):
            f = r.get(k)
            fp = f if f and os.path.isabs(f) else os.path.join(job, f or "")
            if f and os.path.isdir(fp):
                P.append(f"{relp}: measured on Resolve's still sequences (frames mode — a review measure); the gate needs "
                         f"Resolve's delivery render and its TITLES_OFF twin — {how}")
                break
            if not f or not os.path.isfile(fp):
                P.append(f"{relp}: the {k}-titles render it was measured on ({f}) is gone — {how}")
            elif _sha(fp) != r.get(f"{k}_sha256"):
                P.append(f"{relp}: the {k}-titles render changed after title_qa measured it — {how}")
        if r.get("verdict") != "PASS":
            P.append(f"{relp}: title_qa FAILS — " + ", ".join(c["name"] for c in r.get("checks", []) if c.get("status") == "FAIL"))
    pl = os.path.join(job, "07-edit", "titles", "native-placement.json")
    if os.path.isfile(pl):
        try:
            rows = ((json.load(open(pl, encoding="utf-8")) or {}).get("titles") or {}).get("placed") or []
        except ValueError:
            rows = []
        row = next((x for x in rows if x.get("id") == tid), None)
        if row is not None:
            import native  # noqa: E402
            text, _f = native.spec_text(s)
            if row.get("problem") or not row.get("reads_back"):
                P.append(f"{relp}: the console did not place it cleanly — {row.get('problem') or 'its words did not read back'}")
            elif row.get("set") is not None and row.get("set") != text:
                P.append(f"{relp}: its words changed after the console placed them — run PLACE_TITLES again")
            # ⚡ v2.45: a generated template carries the card's hash; the row records what Resolve read back
            card_p = os.path.join(job, CARD)
            if row.get("card_sha256") and os.path.isfile(card_p) and row["card_sha256"] != _sha(card_p):
                P.append(f"{relp}: placed from another card (template hash {row['card_sha256'][:8]}, the card is now "
                         f"{_sha(card_p)[:8]}) — fusion_titles.py build, then PLACE_TITLES again")
            if row.get("font_installed") is False:
                P.append(f"{relp}: Resolve does not have the card's face ({row.get('font')} {row.get('style') or ''}) — "
                         f"CHECK_FONTS / AddFont, or install it to ~/Library/Fonts and restart Resolve; a missing face is a "
                         f"substitute face in the render")
            if row.get("moved") is False:
                P.append(f"{relp}: the title did not move onto {row.get('track')!r} at its frame — "
                         f"{row.get('scratch_left') or row.get('move_error') or 'see the placement report'}")
    return P


def needs_style_frame(job: str, card: dict) -> list:
    """Titles made in Resolve wait for an approved style frame."""
    if any(str((json.load(open(p, encoding="utf-8")) or {}).get("engine") or "resolve").lower() == "resolve"
           for p in specs(job)):
        return style_frame_ok(job, card)
    return []


def renders_ok(job: str) -> list:
    """Each spec's title measured on the pixels: made in Resolve, on Resolve's renders (title_qa.py native); made
    outside, its render (<id>.mov) with a passing title_qa report on these bytes."""
    P = []
    for p in specs(job):
        base = p[: -len(".title.json")]
        mov = base + ".mov"
        rel = os.path.relpath(mov, job)
        try:
            s_ = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue                                    # check_titles reports it
        if str(s_.get("engine") or "resolve").strip().lower() == "resolve":
            P += _native_ok(job, p, s_)
            opts = sorted(glob.glob(glob.escape(base) + ".opt*.title.json"))
            if opts and not s_.get("picked_from"):
                P.append(f"{os.path.relpath(p, job)}: {len(opts)} options and none picked — PLACE_TITLE_OPTIONS → "
                         f"`title_qa.py strip-native` → `title_card.py pick`")
            continue
        if not os.path.isfile(mov):
            P.append(f"{rel}: not rendered — `node assets/titles-hyperframes/title.mjs --card … --spec {os.path.relpath(p, job)}`"); continue
        rp = mov + ".qa.json"
        if not os.path.isfile(rp):
            P.append(f"{rel}: no title_qa report — `title_qa.py check <job> --title {os.path.basename(base)}`"); continue
        r = json.load(open(rp, encoding="utf-8"))
        if r.get("render_sha256") != _sha(mov):
            P.append(f"{rel}: the render changed after title_qa measured it — measure it again")
        elif r.get("verdict") != "PASS":
            P.append(f"{rel}: title_qa FAILS — " + ", ".join(c["name"] for c in r.get("checks", []) if c.get("status") == "FAIL"))
        opts = sorted(glob.glob(base + ".opt*.title.json"))
        if opts and not json.load(open(p, encoding="utf-8")).get("picked_from"):
            P.append(f"{os.path.relpath(p, job)}: {len(opts)} options rendered and none picked — `title_card.py pick`")
    return P


def _sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def check_card(job: str) -> list:
    """What picture lock needs: a title card that lints clean."""
    p = os.path.join(job, CARD)
    if not os.path.isfile(p):
        return [f"no title card — `title_card.py propose <job> --lane ads|brand|drama|golf|property|captions-only` writes {CARD} "
                f"(the permission list for titles, house rule C3); approve it with the storyboard"]
    P, _ = lint_card(load_card(p), job)          # (v2.48.0, project switch blur-titles) the job's switches
    return [f"{CARD}: {x}" for x in P]


def check_job(job: str) -> list:
    """What `approve titles` and `approve export` need: the card, every title on it, rendered and measured."""
    P = check_card(job)
    if P:
        return P
    card = load_card(os.path.join(job, CARD))
    T, _ = check_titles(job, card)
    return T + needs_style_frame(job, card) + renders_ok(job) + timeline_title_media(job)


FIT_EM_PER_SIZE = 1.0      # Text+ Size × frame width = the em in pixels [assumed until measured on a Resolve still]
FIT_PAD = 0.02             # share of the frame width kept clear inside the box (a highlighter's own padding) [assumed]


def _lines(spec: dict) -> list:
    C = spec.get("content") or {}
    L = [str(x) for x in (C.get("lines") or []) if str(x).strip()]
    return L or [str(C[k]) for k in ("line", "title", "subtitle", "kicker", "label", "place", "time", "price", "was",
                                     "note", "url") if C.get(k)]


def fit(job: str, fmt_name: str = "vertical-1080", organic: bool = False) -> tuple:
    """(problems, notes): every title's lines set at its style-frame size in the card's anchor font, against the width
    the safe box leaves it — BEFORE anything renders. ⚡ a supplement ad job (2026-10-28): ingredient names came out cut on the
    collapse card ("RUTI", "FUCI") and were found only in the render. Needs Pillow; without it the check says so."""
    card = load_card(os.path.join(job, CARD))
    try:
        from PIL import ImageFont
    except ImportError:
        return [], ["Pillow is not installed: the fit check did not run (pip install pillow)"]
    fp = _font_path(card, (card.get("fonts") or {}).get("anchor") or {})
    if not fp or not os.path.isfile(fp):
        return [], ["the card names no anchor font file: the fit check did not run"]
    fmt = json.load(open(os.path.join(SKILL, "assets", "delivery-formats.json"), encoding="utf-8"))["formats"][fmt_name]
    W = int(fmt["width"])
    box = fmt["safe_zone_organic_pct" if organic else "safe_zone_pct"]
    sl, sr = W * box["left"] / 100, W * (1 - box["right"] / 100)
    sf = {**STYLE_DEFAULT, **(card.get("style_frame") or {})}
    sc_ = {**STYLE_DEFAULT["scale"], **(sf.get("scale") or {})}
    P, N = [], []
    for p in specs(job):
        s = json.load(open(p, encoding="utf-8"))
        kind = s.get("kind") or ""
        step = (sf.get("kind_step") or {}).get(kind) or KIND_STEP.get(kind, "body")
        px = max(1, int(round(float(sc_.get(step, 0.07)) * FIT_EM_PER_SIZE * W)))
        f = ImageFont.truetype(fp, px)
        if sf.get("align") == "centre":
            avail = (min(W / 2 - sl, sr - W / 2) * 2) - 2 * FIT_PAD * W
        else:
            left = max(sl, float(sf.get("margin_left_x") or 0.115) * W)
            avail = sr - left - FIT_PAD * W
        for ln in _lines(s):
            w = f.getlength(ln)
            if w > avail:
                P.append(f"{os.path.relpath(p, job)}: \u201c{ln}\u201d sets {w:.0f} px wide at {step} ({px} px) and the box "
                         f"leaves {avail:.0f} px — break the line or cut words, never smaller type")
            elif w > 0.92 * avail:
                N.append(f"{os.path.relpath(p, job)}: \u201c{ln}\u201d fills {w / avail:.0%} of its width — no room for the emphasis "
                         f"device's padding")
    return P, N


def pick(job: str, tid: str, n: int) -> str:
    base = os.path.join(job, TITLES, tid)
    src = f"{base}.opt{n}.title.json"
    if not os.path.isfile(src):
        raise SystemExit(f"error: no {os.path.relpath(src, job)}")
    s = json.load(open(src, encoding="utf-8"))
    s["picked_from"] = f"opt{n}"
    s["picked"] = dt.datetime.now().isoformat(timespec="minutes")
    if str(s.get("engine") or "resolve").strip().lower() == "resolve":
        # ⚡ v2.45: a title made in Resolve is reviewed as Resolve's own stills (PLACE_TITLE_OPTIONS); its options are
        # specs, never movies — a movie beside them is the outside route this refuses
        movs = [m for m in outside_renders(job, tid)]
        if movs:
            raise SystemExit(f"error: {tid} is made in Resolve, and {', '.join(os.path.relpath(m, job) for m in movs)} sits "
                             f"beside it — options of a native title are Resolve stills (PLACE_TITLE_OPTIONS), never "
                             f"movies. Move the movie to 07-edit/titles/_superseded/ first")
        stills = os.path.join("09-qa", "titles", tid)
        s["picked_stills"] = stills + "/" if os.path.isdir(os.path.join(job, stills)) else None
        json.dump(s, open(base + ".title.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        return base + ".title.json"
    json.dump(s, open(base + ".title.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    mov = f"{base}.opt{n}.mov"
    if os.path.isfile(mov):
        shutil.copyfile(mov, base + ".mov")
        for ext in (".render.json", ".qa.json"):
            if os.path.isfile(mov + ext):
                shutil.copyfile(mov + ext, base + ".mov" + ext)
                if ext == ".qa.json":                 # the report follows the bytes it measured
                    q = json.load(open(base + ".mov.qa.json", encoding="utf-8"))
                    q["render"] = os.path.relpath(base + ".mov", job)
                    json.dump(q, open(base + ".mov.qa.json", "w", encoding="utf-8"), indent=1)
    return base + ".title.json"


# =================================================================================================
# selftest
# =================================================================================================
def _sysfont(*names) -> str | None:
    for d in ("/usr/share/fonts", "/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts")):
        for n in names:
            hits = glob.glob(os.path.join(d, "**", n), recursive=True)
            if hits:
                return hits[0]
    return None


def selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {info}"))
        ok = ok and bool(cond)
    heavy = _sysfont("InterDisplay-ExtraBold.otf", "Inter-Bold.otf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf")
    regular = _sysfont("Inter-Regular.otf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf")
    serif = _sysfont("Lora-Variable.ttf", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "Georgia.ttf")
    if not (heavy and regular):
        print("  [SKIP] no system fonts found to test the type lint with")
        return 0
    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        os.makedirs(os.path.join(job, "00-brief"))
        fh, fr = read_font(heavy), read_font(regular)
        check("the OpenType reader finds the weight, the family and the cap height",
              fh.get("weight_class", 0) >= 600 and fh.get("family") and fr.get("weight_class") in (400, 500)
              and (fh.get("cap_height") or 1) > 0, json.dumps({k: fh.get(k) for k in ("family", "weight_class", "cap_height")}))
        wclass = int(fh.get("weight_class"))
        try:
            propose(job, "ads", accent="#E8432E", page_bg="#111111")
            refused_dup = False
            propose(job, "ads")
        except SystemExit:
            refused_dup = True
        check("propose writes the lane's card and refuses to overwrite it", refused_dup and os.path.isfile(os.path.join(job, CARD)))
        card = load_card(os.path.join(job, CARD))
        P, W = lint_card(card)
        check("a card without its brand fonts refuses", any("fonts.anchor is missing" in x for x in P), P)
        card["fonts"] = {"anchor": {"family": fh["family"], "file": heavy, "weight": wclass},
                         "companion": {"family": fr["family"], "file": regular, "weight": int(fr["weight_class"])}}
        json.dump({k: v for k, v in card.items() if k != "__path"}, open(card["__path"], "w"), indent=1)
        card = load_card(card["__path"])
        P, W = lint_card(card)
        check("the ads card with a heavy anchor and a regular companion lints clean", not P, P)
        c2 = json.loads(json.dumps(card)); c2["fonts"]["anchor"]["weight"] = 300 if wclass >= 600 else 800
        check("a weight the file does not have is a faux style", any("faux" in x for x in lint_card(c2)[0]), lint_card(c2)[0])
        c3 = json.loads(json.dumps(card)); c3["fonts"]["companion"] = dict(card["fonts"]["anchor"])
        check("an anchor paired with itself reads as redundant", any("redundant" in x for x in lint_card(c3)[0]), lint_card(c3)[0])
        c4 = json.loads(json.dumps(card)); c4["motion"]["enter"]["ease"] = [0.34, 1.56, 0.64, 1]
        check("an overshooting curve refuses (C2)", any("overshoots" in x for x in lint_card(c4)[0]))
        c5 = json.loads(json.dumps(card)); c5["motion"]["enter"]["family"] = "blur-resolve"
        check("blur in the ads lane refuses", any("blur" in x for x in lint_card(c5)[0]))
        # (v2.48.0, project switch blur-titles) off → refused as before; on → a brand line's own blur entrance is lifted;
        # on, outside what it allows → every title's blur (motion.enter) and a stat's still refuse
        blur = {"family": "blur-resolve", "ms": 450, "ease": [0.16, 1, 0.3, 1]}
        cb = json.loads(json.dumps(card)); cb["kinds"]["hero"]["enter"] = dict(blur)
        cs = json.loads(json.dumps(card)); cs["kinds"]["stat"]["enter"] = dict(blur)
        check("blur-titles off: a brand line's blur in the ads lane refuses, as before",
              "entrance 'blur-resolve' in the ads lane: no blur, glow or scramble for the 45+ phone audience" in lint_card(cb)[0]
              and not any("project switch" in x for x in lint_card(cb)[0] + lint_card(cb)[1]), lint_card(cb))
        cpk = os.path.join(job, "00-brief", "CHECKPOINT.md")
        open(cpk, "w").write("Job:        tc-1\nSwitches:   blur-titles — the brand's own motion system blurs its hook in\n")
        Pb, Wb = lint_card(cb)
        check("blur-titles on: the brand line's blur prints as lifted and does not refuse",
              not any("blur" in x for x in Pb) and any("kinds.hero (hero-line)" in x and
                                                       "lifted by project switch `blur-titles` (the brand's" in x for x in Wb),
              (Pb, Wb))
        check("blur-titles on, outside what it allows: every title's blur (motion.enter) and a stat's still refuse",
              any("blur-titles" in x and "every title (motion.enter)" in x for x in lint_card(c5)[0])
              and any("blur-titles" in x and "kinds.stat (stat)" in x for x in lint_card(cs)[0]),
              (lint_card(c5)[0], lint_card(cs)[0]))
        os.remove(cpk)
        c6 = json.loads(json.dumps(card)); c6["motion"]["mark_ms"] = 333; c6["motion"]["count_ms"] = 777
        c6["kinds"]["hero"]["enter"] = {"ms": 510, "ease": [0.2, 0.6, 0.3, 1]}; c6["kinds"]["stat"]["enter"] = {"ms": 620, "ease": [0.1, 0.7, 0.2, 1]}
        c6["kinds"]["price"]["exit"] = {"ms": 410, "ease": [0.5, 0, 0.9, 1]}
        check("more than 5 durations or 3 curves refuses (Shaw)", any("durations" in x for x in lint_card(c6)[0])
              and any("curves" in x for x in lint_card(c6)[0]), lint_card(c6)[0])
        c7 = json.loads(json.dumps(card)); c7["kinds"]["hero"]["max_words"] = 7
        check("an ads hero line over 4 words refuses", any("at most 4 words" in x for x in lint_card(c7)[0]))
        c8 = json.loads(json.dumps(card)); c8["ramps"]["max_per_video"] = 3
        check("more than 2 ramps per video refuses (C4)", any("ramps" in x for x in lint_card(c8)[0]))
        if serif:
            b = json.loads(json.dumps(card)); b["lane"] = "brand"
            fs = read_font(serif)
            b["fonts"]["anchor"] = {"family": fs["family"], "file": serif, "weight": 500 if "wght" in fs["axes"] else int(fs["weight_class"])}
            b["fonts"]["companion"] = {"family": fr["family"], "file": regular, "weight": int(fr["weight_class"])}
            check("a serif anchor with a sans companion differs on an axis", not [x for x in lint_card(b)[0] if "redundant" in x], lint_card(b)[0])
        # titles against the card
        T = os.path.join(job, TITLES); os.makedirs(T)
        json.dump({"fps": 24, "tracks": {"video1": [{"type": "video", "start": 0, "duration": 72}, {"type": "transition", "start": 66, "duration": 12},
                                                     {"type": "video", "start": 72, "duration": 96}, {"type": "video", "start": 168, "duration": 96}]}},
                  open(os.path.join(job, "07-edit", "timeline-dump.json"), "w"))
        good = {"id": "T1", "kind": "hero", "duration_s": 6.0, "at_s": 7.5, "anchor": {"type": "settle", "at_s": 7.5},
                "content": {"lines": ["Sleep through", "the night"], "emphasis": "night", "mark": "bar"}}
        json.dump(good, open(os.path.join(T, "T1.title.json"), "w"))
        P, W = check_titles(job, card)
        check("a 4-word hero line on its anchor, after the settle, held long enough, passes", not P, P)
        bad = dict(good, id="T2", kind="lower-third")
        json.dump(bad, open(os.path.join(T, "T2.title.json"), "w"))
        P, _ = check_titles(job, card)
        check("a kind that is not on the card refuses (C3)", any("not on the title card" in x for x in P), P)
        os.remove(os.path.join(T, "T2.title.json"))
        short = dict(good, id="T3", duration_s=2.0)
        json.dump(short, open(os.path.join(T, "T3.title.json"), "w"))
        P, _ = check_titles(job, card)
        check("text only on screen held under 1 s per word refuses, with the duration that fixes it",
              any("T3" in x and "need" in x and "duration_s" in x for x in P), P)
        os.remove(os.path.join(T, "T3.title.json"))
        early = dict(good, id="T4", at_s=3.1, anchor={"type": "cut", "at_s": 3.1})
        json.dump(early, open(os.path.join(T, "T4.title.json"), "w"))
        P, _ = check_titles(job, card)
        check("a title entering inside the clip's settle refuses (C1) unless declared",
              any("T4" in x and "settle" in x for x in P), P)
        json.dump(dict(early, masks_settle=True, at_s=3.2, anchor={"type": "cut", "at_s": 3.2}), open(os.path.join(T, "T4.title.json"), "w"))
        P, _ = check_titles(job, card)
        check("a title across a non-cut transition refuses", any("T4" in x and "transition" in x for x in P), P)
        os.remove(os.path.join(T, "T4.title.json"))
        P = check_job(job)
        check("a title with no engine is made in Resolve (C7): check_job wants the native measure, not a .mov",
              any("made in Resolve and not measured" in x and "title_qa.py native" in x for x in P) and not any("not rendered" in x for x in P), P)
        json.dump(dict(good, engine="hyperframes"), open(os.path.join(T, "T1.title.json"), "w"))
        P, _ = check_titles(job, card)
        check("an outside engine with no reason refuses (C7)", any("no reason" in x and "engine hyperframes" in x for x in P), P)
        good = dict(good, engine="hyperframes", engine_reason={"code": "owner", "why": "the kinetic kit look for the launch film",
                                                               "quote": "use the HyperFrames kit for this one"})
        json.dump(good, open(os.path.join(T, "T1.title.json"), "w"))
        P, _ = check_titles(job, card)
        check("…with the owner's words it passes the card", not P, P)
        P = check_job(job)
        check("check_job wants the outside render and its title_qa report", any("not rendered" in x for x in P), P)
        open(os.path.join(T, "T1.opt1.title.json"), "w").write(json.dumps(dict(good, content={"lines": ["Wake up", "rested"], "emphasis": "rested"})))
        open(os.path.join(T, "T1.opt1.mov"), "wb").write(b"opt1")
        pick(job, "T1", 1)
        s = json.load(open(os.path.join(T, "T1.title.json")))
        check("pick copies the chosen option over the title and records it", s.get("picked_from") == "opt1"
              and open(os.path.join(T, "T1.mov"), "rb").read() == b"opt1")
        P = check_job(job)
        check("a render without a title_qa report is refused", any("no title_qa report" in x for x in P), P)
        json.dump({"render_sha256": _sha(os.path.join(T, "T1.mov")), "verdict": "PASS", "checks": []}, open(os.path.join(T, "T1.mov.qa.json"), "w"))
        check("with a passing report on these bytes, nothing is left", not check_job(job), check_job(job))
        # the Resolve path end to end: a native report on two renders, bound to the spec and both files
        nat = dict(good); nat.pop("engine"); nat.pop("engine_reason"); nat.pop("picked_from", None)
        json.dump(nat, open(os.path.join(T, "T1.title.json"), "w"))
        on, off = os.path.join(job, "07-edit", "on.mp4"), os.path.join(job, "07-edit", "off.mp4")
        open(on, "wb").write(b"titles on"); open(off, "wb").write(b"titles off")
        rep_ = {"verdict": "PASS", "checks": [], "with": "07-edit/on.mp4", "with_sha256": _sha(on), "without": "07-edit/off.mp4",
                "without_sha256": _sha(off), "spec_sha256": _sha(os.path.join(T, "T1.title.json"))}
        json.dump(rep_, open(os.path.join(T, "T1.native.qa.json"), "w"))
        # ⛔ v2.45 (2026-10-29: "It keeps making mp4s which it imports"): a supplement ad job's engine-less specs had
        # their HyperFrames movies beside them, imported onto V2 — a Resolve spec with a movie beside it refuses
        import shutil as _sh
        if _sh.which("ffmpeg"):
            import subprocess as _sp
            _sp.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.2", "-metadata",
                     "hyperframes_renderer=hyperframes", "-metadata", "hyperframes_version=0.8.204", "-movflags",
                     "use_metadata_tags", "-c:v", "prores_ks", os.path.join(T, "T1_rle.mov")], check=True)
        P_ = check_titles(job, card)[0]
        check("a spec made in Resolve with rendered movies beside it refuses, naming each and what made it (a supplement ad job: "
              "S01.mov, S01_rle.mov, HyperFrames 0.8.204)",
              any("T1.mov sits beside it" in x for x in P_) and any("T1.opt1.mov sits beside it" in x for x in P_)
              and (not _sh.which("ffmpeg") or any("T1_rle.mov sits beside it (HyperFrames 0.8.204" in x for x in P_)), P_)
        _W = check_titles(job, card)[1]
        check("…and `titles` WARNS what the native title does instead of a token Fusion does not make (the stagger, the "
              "one-word highlighter) — the owner's call, not a silent detour",
              any("stagger 60 ms" in x for x in _W) and any("highlighter sits behind every line" in x for x in _W), _W)
        sup = os.path.join(T, "_superseded")
        os.makedirs(sup)
        for f_ in ("T1.mov", "T1.mov.qa.json", "T1.opt1.mov", "T1.opt1.title.json", "T1_rle.mov"):
            if os.path.exists(os.path.join(T, f_)):
                os.replace(os.path.join(T, f_), os.path.join(sup, f_))
        check("…moved to 07-edit/titles/_superseded/, the spec is clear of it",
              not any("sits beside" in x for x in check_titles(job, card)[0]), check_titles(job, card)[0])
        check("a title made in Resolve waits for an approved style frame (a supplement ad job)",
              any("no approved style frame" in x for x in check_job(job)), check_job(job))
        still = os.path.join(job, "00-brief", "STYLE-FRAME.png")
        open(still, "wb").write(b"\x89PNG style frame")
        sf = style_frame(job, "00-brief/STYLE-FRAME.png", "Dana", "this is the look, go")
        check("style-frame records the still, its hash and the approver's words", sf["approved"]["sha256"] and
              sf["approved_still"] == "00-brief/STYLE-FRAME.png", sf)
        lay = layout_for(load_card(os.path.join(job, CARD)))
        check("the style frame becomes Text+ inputs: H1 for a hero, left-aligned at the margin, and the highlighter",
              lay["hero"]["Size"] == 0.125 and lay["hero"]["HorizontalLeftCenterRight"] == -1
              and lay["hero"]["Center"][0] == 0.115 and lay["_emphasis"]["ElementShape3"] == 2
              and lay["disclosure"]["Size"] == 0.042, lay)
        c9 = json.loads(json.dumps(load_card(os.path.join(job, CARD)))); c9["style_frame"]["centre"] = "safe-box"
        check("centring on the safe box instead of the frame refuses", any("centre on the FRAME" in x for x in lint_card(c9)[0]))
        check("a title made in Resolve with a passing native report on these renders: nothing is left", not check_job(job), check_job(job))
        json.dump({"titles": {"placed": [{"id": "T1", "reads_back": True, "set": "Sleep\nwell"}]}},
                  open(os.path.join(job, "07-edit", "titles", "native-placement.json"), "w"))
        check("words placed by the console that are not the spec's now refuse",
              any("words changed after the console placed" in x for x in check_job(job)), check_job(job))
        # ⚡ v2.45: the placement row's read-back — the card hash, the face as installed, the move
        csha = _sha(os.path.join(job, CARD))
        for row_, needle in (({"card_sha256": "0" * 64}, "placed from another card"),
                             ({"card_sha256": csha, "font_installed": False, "font": "Poppins", "style": "Bold"},
                              "does not have the card's face"),
                             ({"card_sha256": csha, "moved": False, "track": "Titles", "scratch_left": "V6 _cine-insert"},
                              "did not move onto 'Titles'")):
            json.dump({"titles": {"placed": [dict({"id": "T1", "reads_back": True, "set": "Sleep through\nthe night"}, **row_)]}},
                      open(os.path.join(job, "07-edit", "titles", "native-placement.json"), "w"))
            check(f"a placement row that read back {list(row_)[-1]} {row_[list(row_)[-1]]!r} refuses ({needle})",
                  any(needle in x for x in check_job(job)), check_job(job))
        json.dump({"titles": {"placed": [{"id": "T1", "reads_back": True, "set": "Sleep through\nthe night", "card_sha256": csha,
                                          "font_installed": True, "moved": True}]}},
                  open(os.path.join(job, "07-edit", "titles", "native-placement.json"), "w"))
        check("…the card's own hash, the face installed, the title moved: clear", not check_job(job), check_job(job))
        # ⛔ v2.45: export reads the timeline — an imported title movie on it refuses, from the dump
        dpath = os.path.join(job, "07-edit", "timeline-dump.json")
        d0 = open(dpath, encoding="utf-8").read()
        dmp = json.loads(d0)
        dmp["track_names"] = {"video1": "Picture", "video2": "Graphics"}
        dmp["tracks"]["video2"] = [{"name": "S01.mov", "type": "video", "start": 24, "duration": 60, "start_s": 1.0,
                                    "file": "/Users/someone/jobs/job/07-edit/titles/S01.mov"},
                                   {"name": "CAPTIONS_A_f0000.mov", "type": "video", "start": 0, "duration": 90, "start_s": 0.0,
                                    "file": "/Users/someone/jobs/job/08-captions/CAPTIONS_A_f0000.mov"},
                                   {"name": "T1.mov", "type": "video", "start": 180, "duration": 60, "start_s": 7.5},
                                   {"name": "L1-card.mp4", "type": "video", "start": 300, "duration": 48, "start_s": 12.5,
                                    "file": "/Users/someone/jobs/job/07-edit/gfx/L1-card.mp4"}]
        json.dump(dmp, open(dpath, "w"))
        TM = timeline_title_media(job)
        check("the timeline dump shows title, caption and spec-named movies on the cut: each refuses (a card label in gfx/ "
              "is not a title folder)", len(TM) == 3 and any("S01.mov" in x and "Graphics" in x for x in TM)
              and any("CAPTIONS_A_f0000.mov" in x for x in TM) and any("T1.mov" in x for x in TM)
              and not any("L1-card" in x for x in TM) and len([x for x in check_job(job) if "the timeline carries" in x]) == 3, TM)
        json.dump({"id": "S01", "kind": "hero", "engine": "hyperframes", "duration_s": 2.5, "at_s": 1.0,
                   "anchor": {"type": "cut", "at_s": 1.0}, "content": {"lines": ["One"]},
                   "engine_reason": {"code": "owner", "why": "the kinetic kit look for the launch film",
                                     "quote": "use the HyperFrames kit for this one"}}, open(os.path.join(T, "S01.title.json"), "w"))
        check("…a movie whose spec names its engine and the owner's reason is not refused",
              not any("S01.mov" in x for x in timeline_title_media(job)), timeline_title_media(job))
        os.remove(os.path.join(T, "S01.title.json"))
        open(dpath, "w", encoding="utf-8").write(d0)
        # options of a native title are Resolve stills: pick copies the spec only, and refuses a movie beside it
        json.dump(dict(nat, content={"lines": ["Wake up", "rested"]}), open(os.path.join(T, "T1.opt2.title.json"), "w"))
        check("a native title with an option and no pick is not cleared",
              any("options and none picked" in x for x in check_job(job)), check_job(job))
        os.makedirs(os.path.join(job, "09-qa", "titles", "T1"))
        pick(job, "T1", 2)
        s2 = json.load(open(os.path.join(T, "T1.title.json")))
        check("pick on a native title copies the spec, records the stills folder, and makes no movie",
              s2.get("picked_from") == "opt2" and s2.get("picked_stills") == "09-qa/titles/T1/"
              and not os.path.exists(os.path.join(T, "T1.mov")), s2)
        open(os.path.join(T, "T1.opt2.mov"), "wb").write(b"a render")
        try:
            pick(job, "T1", 2)
            refused_ = False
        except SystemExit as e_:
            refused_ = "never movies" in str(e_)
        check("…and refuses when a movie sits beside it", refused_)
        os.remove(os.path.join(T, "T1.opt2.mov")); os.remove(os.path.join(T, "T1.opt2.title.json"))
        json.dump(nat, open(os.path.join(T, "T1.title.json"), "w"))
        rep_["spec_sha256"] = _sha(os.path.join(T, "T1.title.json"))
        json.dump(rep_, open(os.path.join(T, "T1.native.qa.json"), "w"))
        # the layout: the weight becomes a Style; a plate kind carries the card's plate on element 3
        cw = load_card(os.path.join(job, CARD))
        cw["fonts"]["anchor"] = {"family": "Poppins", "weight": 500}
        cw["style_frame"]["style"] = None
        lw = layout_for(cw)
        check("layout_for: weight 500 with no style named → Style 'Medium'; the price (a plate kind) → element 3 in "
              "colors.plate rgba(10,10,12,0.72)",
              lw["hero"]["Style"] == "Medium" and lw["price"]["Enabled3"] == 1 and abs(lw["price"]["Alpha3"] - 0.72) < 1e-9
              and abs(lw["price"]["Red3"] - 10 / 255) < 1e-9 and "Enabled3" not in lw["hero"], (lw["hero"], lw["price"]))
        os.remove(os.path.join(job, "07-edit", "titles", "native-placement.json"))
        open(on, "wb").write(b"titles on, re-rendered")
        check("a re-rendered with-titles render makes the native report stale",
              any("with-titles render changed" in x for x in check_job(job)), check_job(job))
        # ⚡ the fit, before anything renders (a supplement ad job: "RUTI", "FUCI")
        import importlib.util as _iu
        if _iu.find_spec("PIL"):
            json.dump(dict(good, id="T8", content={"lines": ["Rest", "well"]}), open(os.path.join(T, "T8.title.json"), "w"))
            json.dump(dict(good, id="T9", content={"lines": ["Fucoxanthin and rutin, together"]}),
                      open(os.path.join(T, "T9.title.json"), "w"))
            P_, N_ = fit(job)
            check("fit: a short line at H1 fits; a line wider than the safe box leaves refuses, before anything renders",
                  not any("T8" in x for x in P_) and any("T9" in x and "never smaller type" in x for x in P_), (P_, N_))
            for t_ in ("T8", "T9"):
                os.remove(os.path.join(T, f"{t_}.title.json"))
        else:
            print("  [SKIP] Pillow is not installed: the fit check is not exercised")
        check("propose writes the card's Resolve block (template, track) and a style frame to fill",
              (card.get("native") or {}).get("track") == "Titles" and "style_frame" in card, card.get("native"))
        os.remove(os.path.join(job, CARD))
        check("picture lock's check refuses without a card", any("no title card" in x for x in check_card(job)))
    print("-" * 60)
    print("selftest OK — the OpenType reader, propose, the type lint (missing fonts, faux weight, a redundant pair, "
          "serif + sans), the motion tokens (overshoot, blur in ads, 5 durations / 3 curves), the ads hero cap, the ramp cap, "
          "the titles against the card (permission, dwell by regime, the settle, a transition), the engine (Resolve by "
          "default, an outside engine only with a reason — C7), pick, and the render/report check on both paths; v2.45: a "
          "Resolve spec with a movie beside it refuses (naming HyperFrames), so does a title movie on the timeline, a "
          "placement from another card, a missing face or a title that did not move; options of a native title are "
          "stills; the weight becomes a Style and a plate kind its plate; the project switch blur-titles (a brand line's "
          "blur lifted, every title's and a stat's still refused)"
          if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("propose"); p.add_argument("job"); p.add_argument("--lane", required=True)
    for r in ("anchor", "companion"):
        p.add_argument(f"--{r}", help=f"the {r} font file"); p.add_argument(f"--{r}-family"); p.add_argument(f"--{r}-weight", type=int)
    p.add_argument("--accent"); p.add_argument("--page-bg"); p.add_argument("--genre"); p.add_argument("--force", action="store_true")
    l_ = sub.add_parser("lint"); l_.add_argument("job", nargs="?"); l_.add_argument("--card")
    t = sub.add_parser("titles"); t.add_argument("job")
    k = sub.add_parser("pick"); k.add_argument("job"); k.add_argument("id"); k.add_argument("--option", type=int, required=True)
    c = sub.add_parser("check"); c.add_argument("job")
    ft_ = sub.add_parser("fit", help="every title's lines at its style-frame size in the anchor font, against its box")
    ft_.add_argument("job"); ft_.add_argument("--format", default="vertical-1080"); ft_.add_argument("--organic", action="store_true")
    sf_ = sub.add_parser("style-frame", help="record the approved style frame (one still) and its tokens on the card")
    sf_.add_argument("job"); sf_.add_argument("--still", required=True); sf_.add_argument("--by", default="")
    sf_.add_argument("--quote", default=""); sf_.add_argument("--font"); sf_.add_argument("--style")
    sf_.add_argument("--align", choices=["left", "centre"]); sf_.add_argument("--margin-left-x", type=float)
    sf_.add_argument("--scale", help="H1=0.125,H2=0.10,body=0.07,caption=0.06,disclosure=0.042")
    sf_.add_argument("--ink-footage"); sf_.add_argument("--ink-paper")
    sf_.add_argument("--emphasis", help="highlighter|colour|weight|underline|none"); sf_.add_argument("--emphasis-color")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "propose":
        F = {}
        for r in ("anchor", "companion"):
            f = getattr(a, r)
            if f:
                ft = read_font(f)
                F[r] = {"family": getattr(a, f"{r}_family") or ft.get("family"), "file": os.path.abspath(f),
                        "weight": getattr(a, f"{r}_weight") or int(ft.get("weight_class", 400))}
        out = propose(a.job, a.lane, F.get("anchor"), F.get("companion"), a.accent, a.page_bg, a.genre, a.force)
        P, W = lint_card(load_card(out))
        print(f"{os.path.relpath(out, a.job)} ({a.lane}) — show {os.path.relpath(out[:-5] + '.md', a.job)} with the storyboard")
        for x in P:
            print(f"  ✗ {x}")
        for x in W:
            print(f"  ⚠ {x}")
        return 1 if P else 0
    if a.cmd == "lint":
        path = a.card or os.path.join(a.job or ".", CARD)
        P, W = lint_card(load_card(path), a.job)    # (v2.48.0, project switch blur-titles) a.job, or --card's job
        for x in P:
            print(f"  ✗ {x}")
        for x in W:
            print(f"  ⚠ {x}")
        print("card OK" if not P else f"{len(P)} problem(s)")
        return 1 if P else 0
    if a.cmd == "titles":
        P, W = check_titles(a.job, load_card(os.path.join(a.job, CARD)))
        for x in P:
            print(f"  ✗ {x}")
        for x in W:
            print(f"  ⚠ {x}")
        return 1 if P else 0
    if a.cmd == "pick":
        print(os.path.relpath(pick(a.job, a.id, a.option), a.job)); return 0
    if a.cmd == "fit":
        P, N = fit(a.job, a.format, a.organic)
        for x in P:
            print(f"  \u2717 {x}")
        for x in N:
            print(f"  \u26a0 {x}")
        print("every line fits" if not P else f"{len(P)} line(s) do not fit")
        return 1 if P else 0
    if a.cmd == "style-frame":
        card0 = load_card(os.path.join(a.job, CARD))
        sf0 = {**STYLE_DEFAULT, **(card0.get("style_frame") or {})}
        scale = dict(sf0["scale"])
        for kv in (a.scale or "").split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                scale[k.strip()] = float(v)
        ink = dict(sf0["ink"])
        if a.ink_footage:
            ink["footage"] = a.ink_footage
        if a.ink_paper:
            ink["paper"] = a.ink_paper
        em = dict(sf0["emphasis"])
        if a.emphasis:
            em["device"] = a.emphasis
        if a.emphasis_color:
            em["color"] = a.emphasis_color
        sf = style_frame(a.job, a.still, a.by, a.quote, font=a.font, style=a.style, align=a.align,
                         margin_left_x=a.margin_left_x, scale=scale, ink=ink, emphasis=em)
        P, W = lint_card(load_card(os.path.join(a.job, CARD)))
        print(f"style frame approved: {sf['approved_still']} by {sf['approved']['by']}")
        for x in P:
            print(f"  ✗ {x}")
        return 1 if P else 0
    if a.cmd == "check":
        P = check_job(a.job)
        for x in P:
            print(f"  - {x}")
        print("titles cleared" if not P else f"{len(P)} thing(s) left")
        return 1 if P else 0
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
