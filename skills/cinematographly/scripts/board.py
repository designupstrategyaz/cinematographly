#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""board.py — the boards a director decides from, built out of what the job already has.

  board.py look     <job>   → 00-brief/BOARD-look.html        the moodboard: every sourced picture,
                                                              big, with its provenance and its
                                                              clearance under it, plus the palette
                                                              the set actually is.
  board.py concepts <job>   → 00-brief/BOARD-concepts.html     one panel per concept, side by side,
                                                              with what killed the dead ones and
                                                              any previz bound to the living ones.
  board.py shots    <job>   → 01-script/BOARD-shots.html       every shot with its reference slots
                                                              AS PICTURES — the wrong reference is
                                                              visible here, before a credit.
  board.py storyboard <job> → 01-script/BOARD-storyboard.html one panel per shot in CUT ORDER — its
                                                              picture (your sketch first), size,
                                                              move, seconds, the line it carries —
                                                              with the film's energy on top. Signed
                                                              with the animatic (v2.66.0).
  board.py frames   <job>   → 01-script/BOARD-frames.html      every approved start frame in cut order
                                                              on one page, signed before clips.
  board.py all      <job>                                      look, concepts, shots and the PPM packet.
  board.py --selftest

THE FAILURE THIS EXISTS FOR
A director was choosing between five sentences. `image: a bottle on a steel bench` is not something
you can direct from — you agree with it, the shot gets generated, and only then does anyone find
out that the bench reads as a laboratory. The credits were spent discovering something the plan
already contained. So: put the plan on a wall.

Every board is ONE self-contained HTML file. Images are embedded, so it opens on a phone, survives
being emailed, and needs nothing installed. It is a review artifact, never a deliverable: nothing
here is generated, nothing here ships.

WHAT EACH BOARD IS FOR, AND THE DECISION IT UNBLOCKS
  look      → "is this the world?"   Before the concepts. Twenty real photographs kill a concept in
                                     five minutes that a paragraph protects for a week.
  concepts  → "which one?"           The choice `gate.py approve concept` records. Seeing them
                                     beside each other is what makes it a choice rather than a
                                     ratification of the first one.
  shots     → "will this work?"      Before `approve cast`. Every reference slot rendered as the
                                     picture it actually binds — an empty slot, an uncleared face
                                     or a zebra in the wardrobe row is obvious at a glance and
                                     invisible in a `refs:` block.

⛔ WHAT A BOARD IS NOT
It is not a verdict. It puts the pixels in front of the human; `develop.py`, `prompt_lint.py` and
`gate.py` still hold the gates, and a board that looks lovely does not open one. It also cannot
tell you a picture is *right* — that is the director's job, and giving it away to a checker is how
the mediocre thing shipped reliably.

Reading: `references/direction.md` §1–§3 (what a board has to answer) · `references/ideation.md` §6
(the kill tests the concept board makes visible) · `references/stock-sourcing.md` §5, §9 (the
clearance line under each picture) · `references/preproduction-research.md` §6b (the look board).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from PIL import Image
except ImportError:                                        # pragma: no cover
    Image = None

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
VID_EXT = (".mp4", ".mov", ".m4v", ".webm")
THUMB_W = 900              # wide enough to judge a photograph, small enough to email
SLOT_W = 320               # a reference slot on the shot board
PALETTE_N = 6


# ------------------------------------------------------------------------------------- utilities
def read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def sidecar_of(asset: str) -> str:
    try:
        import provenance
        return provenance.find_sidecar(asset)
    except Exception:
        for c in (asset + ".json", os.path.splitext(asset)[0] + ".json"):
            if os.path.isfile(c):
                return c
        return ""


def meta_of(asset: str) -> dict:
    sc = sidecar_of(asset)
    if not sc:
        return {}
    try:
        return json.load(open(sc, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"_error": "provenance sidecar is not readable"}


def clearance_of(m: dict) -> tuple:
    """(state, text) where state is ok | reference-only | blocked | none."""
    if not m:
        return "none", "no provenance record"
    c = str(m.get("clearance") or "")
    if not c:
        return "none", "sidecar carries no clearance field"
    up = c.upper()
    if up.startswith("REFERENCE-ONLY"):
        return "reference-only", c
    if up.startswith("NOT CLEARED"):
        return "blocked", c
    return "ok", c


def data_uri(path: str, width: int = THUMB_W) -> str:
    """Embedded, downscaled, so the board is one file that opens anywhere."""
    if Image is None:
        try:
            raw = open(path, "rb").read()
        except OSError:
            return ""
        ext = os.path.splitext(path)[1].lstrip(".").lower() or "jpeg"
        return f"data:image/{'jpeg' if ext in ('jpg', 'jpeg') else ext};base64," + \
            base64.b64encode(raw).decode()
    try:
        im = Image.open(path)
        im.load()
    except Exception:
        return ""
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if im.width > width:
        im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def palette_of(paths: list, n: int = PALETTE_N) -> list:
    """The colours the reference set actually is — not the ones somebody wrote down.

    A palette line in a brief is an intention. This is measured off the pictures the film will be
    designed against, which is the only version that can contradict the intention."""
    if Image is None or not paths:
        return []
    canvas = Image.new("RGB", (64 * len(paths), 64))
    used = 0
    for p in paths:
        try:
            im = Image.open(p)
            im.load()
            canvas.paste(im.convert("RGB").resize((64, 64)), (64 * used, 0))
            used += 1
        except Exception:
            continue
    if not used:
        return []
    canvas = canvas.crop((0, 0, 64 * used, 64))
    q = canvas.quantize(colors=n, method=Image.MEDIANCUT).convert("RGB")
    counts = sorted(q.getcolors(1 << 20) or [], key=lambda c: -c[0])
    return ["#%02x%02x%02x" % rgb for _, rgb in counts[:n]]


def dims_of(path: str) -> str:
    if Image is None:
        return ""
    try:
        with Image.open(path) as im:
            return f"{im.width}×{im.height}"
    except Exception:
        return ""


def images_in(folder: str) -> list:
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder)
                  if f.lower().endswith(IMG_EXT))


# ---------------------------------------------------------------------------------- the page shell
CSS = """
:root{
  --bg:#f6f5f3; --panel:#fff; --ink:#17171a; --dim:#6b6b73; --line:#e3e1dd;
  --ok:#1c6b45; --warn:#8a5a09; --bad:#a1231d; --accent:#2b4c7e;
  --shadow:0 1px 2px rgba(0,0,0,.05),0 8px 24px rgba(0,0,0,.06);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#131316; --panel:#1c1c20; --ink:#eceaea; --dim:#9a9aa4; --line:#2e2e35;
  --ok:#5fd39a; --warn:#e0b463; --bad:#f2837c; --accent:#8fb3e8;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);
}}
:root[data-theme="dark"]{
  --bg:#131316; --panel:#1c1c20; --ink:#eceaea; --dim:#9a9aa4; --line:#2e2e35;
  --ok:#5fd39a; --warn:#e0b463; --bad:#f2837c; --accent:#8fb3e8;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);margin:0;
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-text-size-adjust:100%}
.wrap{max-width:1400px;margin:0 auto;padding:28px 20px 80px}
header{border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:26px}
h1{font-size:22px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:13px}
.sub code{font-size:12px}
h2{font-size:15px;margin:34px 0 12px;letter-spacing:.02em;text-transform:uppercase;color:var(--dim)}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:0 8px 8px 0;padding:12px 15px;margin:0 0 22px;font-size:13.5px;color:var(--dim)}
.note b{color:var(--ink)}
.grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.grid.wide{grid-template-columns:repeat(auto-fill,minmax(420px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;
  box-shadow:var(--shadow);display:flex;flex-direction:column}
.card img{width:100%;display:block;background:#8883}
.card .body{padding:12px 14px 14px;font-size:13px;flex:1}
.card .body p{margin:0 0 7px}
.k{color:var(--dim);font-size:11.5px;letter-spacing:.04em;text-transform:uppercase}
.miss{aspect-ratio:4/3;display:flex;align-items:center;justify-content:center;text-align:center;
  color:var(--dim);font-size:13px;padding:16px;
  background:repeating-linear-gradient(45deg,transparent,transparent 9px,#8881 9px,#8881 18px)}
.tag{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;
  border:1px solid currentColor;margin:0 5px 5px 0;font-weight:600;letter-spacing:.02em}
.t-ok{color:var(--ok)} .t-warn{color:var(--warn)} .t-bad{color:var(--bad)} .t-dim{color:var(--dim)}
.swatches{display:flex;flex-wrap:wrap;gap:8px;margin:2px 0 8px}
.sw{width:74px;height:52px;border-radius:7px;border:1px solid var(--line);position:relative}
.sw span{position:absolute;left:0;right:0;bottom:-17px;text-align:center;font-size:10.5px;
  color:var(--dim);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.swwrap{margin-bottom:26px}
a{color:var(--accent)}
.concept{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
  box-shadow:var(--shadow);display:flex;flex-direction:column}
.concept.dead{opacity:.62}
.concept h3{margin:0 0 2px;font-size:16px}
.concept .q{font-size:16px;line-height:1.4;margin:8px 0 12px}
.row{display:grid;grid-template-columns:78px 1fr;gap:4px 12px;font-size:13px;margin-bottom:3px}
.row .k{padding-top:2px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:11.5px;letter-spacing:.04em;text-transform:uppercase}
.shot{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
  margin-bottom:18px;box-shadow:var(--shadow)}
.shot h3{margin:0 0 10px;font-size:15px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.slots{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
  margin-top:12px}
.slot{border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--bg)}
.slot img{width:100%;display:block}
.slot .cap{padding:8px 10px;font-size:12px}
.blocks{font-size:13px;color:var(--dim);margin-top:10px}
.blocks b{color:var(--ink);font-weight:600}
.empty{color:var(--dim);font-style:italic;padding:20px 0}
footer{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);
  font-size:12px}
@media print{body{background:#fff}.card,.concept,.shot{break-inside:avoid;box-shadow:none}}
"""


def page(title: str, subtitle: str, body: str, job: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><h1>{esc(title)}</h1><div class="sub">{subtitle}</div></header>
{body}
<footer>{esc(os.path.basename(os.path.abspath(job)))} · built
{dt.datetime.now().strftime('%Y-%m-%d %H:%M')} by <code>scripts/board.py</code> · a review artifact,
never a deliverable — nothing on this page was generated and nothing on it ships.</footer>
</div></body></html>"""


def tag(state: str, text: str) -> str:
    cls = {"ok": "t-ok", "reference-only": "t-warn", "blocked": "t-bad"}.get(state, "t-dim")
    return f'<span class="tag {cls}">{esc(text)}</span>'


# ------------------------------------------------------------------------------------ the look board
def build_look(job: str) -> tuple:
    look = os.path.join(job, "00-brief", "_look")
    imgs = images_in(look)
    parts = []
    if not imgs:
        parts.append('<p class="empty">The look board is empty. Four real pictures on disk, each '
                     'with a provenance sidecar, are what <code>develop.py</code> requires before '
                     'a concept is written — and what a concept can actually be judged against. '
                     '<code>pixabay_search.py -q "&lt;terms&gt;" --image-type photo --download '
                     '00-brief/_look/</code>.</p>')
        return page("Look board", "nothing sourced yet", "\n".join(parts), job), 0

    pal = palette_of(imgs)
    if pal:
        sw = "".join(f'<div class="sw" style="background:{c}"><span>{c}</span></div>' for c in pal)
        parts.append(f'<h2>The palette these pictures actually are</h2>'
                     f'<div class="swwrap"><div class="swatches">{sw}</div></div>'
                     f'<p class="note">Measured off the board, not copied from the brief. Where '
                     f'this disagrees with the palette somebody wrote down, <b>the pictures are '
                     f'the ones the film will be designed against</b> — resolve it here, not '
                     f'after a grade.</p>')

    cards, blocked = [], 0
    for p in imgs:
        m = meta_of(p)
        state, ctext = clearance_of(m)
        if state in ("blocked", "none"):
            blocked += 1
        uri = data_uri(p)
        img = (f'<img src="{uri}" alt="{esc(os.path.basename(p))}" loading="lazy">' if uri
               else '<div class="miss">image could not be read</div>')
        src = esc(m.get("source") or "source not recorded")
        who = esc(m.get("user") or m.get("holder") or "")
        url = m.get("pageURL") or m.get("url") or ""
        link = (f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(src)}</a>'
                if url else esc(src))
        tags = esc((m.get("tags") or "")[:120])
        cards.append(f"""<div class="card">{img}<div class="body">
<p>{tag(state, {'ok': 'cleared', 'reference-only': 'reference only',
                'blocked': 'NOT CLEARED', 'none': 'NO PROVENANCE'}[state])}</p>
<p class="k">{esc(os.path.basename(p))} · {esc(dims_of(p))}</p>
{f'<p>{tags}</p>' if tags else ''}
<p class="k">{link}{(' · ' + who) if who else ''}</p>
<p class="k" style="margin-top:6px">{esc(ctext[:180])}</p>
</div></div>""")

    parts.append(f"<h2>{len(imgs)} reference picture(s)</h2>")
    parts.append('<p class="note"><b>The question this board answers is “is this the world?”</b> — '
                 'and the useful answer is often no. A concept survives a paragraph and dies the '
                 'moment you see twenty photographs of the thing it describes. That is the '
                 'cheapest kill in the whole pipeline; take it here.</p>')
    parts.append('<div class="grid wide">' + "\n".join(cards) + "</div>")
    sub = f"{len(imgs)} picture(s)"
    if blocked:
        sub += f" · <b>{blocked} not cleared or unrecorded</b>"
    return page("Look board", sub, "\n".join(parts), job), len(imgs)


# --------------------------------------------------------------------------------- the concept board
def build_concepts(job: str) -> tuple:
    import develop as DV
    p = DV.dev_path(job)
    if not os.path.isfile(p):
        return page("Concept board", "no DEVELOPMENT.md",
                    '<p class="empty">No <code>00-brief/DEVELOPMENT.md</code>. '
                    '<code>develop.py init &lt;job&gt;</code> writes the template.</p>', job), 0
    txt = read(p)
    cs = DV.blocks(DV.section(txt, "Concepts"), DV.CONCEPT_RE)

    killed, weakened, rounds = {}, {}, 0
    for m in re.finditer(r"^##\s*Adversarial round\s*(\d+)\s*[·:.\-]?\s*(.*)$", txt, re.M):
        rounds += 1
        seg = txt[m.end():]
        nxt = re.search(r"^##\s", seg, re.M)
        seg = seg[: nxt.start()] if nxt else seg
        hat = (m.group(2) or "").strip()
        for line in seg.splitlines():
            mm = re.match(r"^\s*(killed|weakened)\s*:\s*(.+)$", line, re.I)
            if not mm:
                continue
            verb, rest = mm.group(1).lower(), mm.group(2)
            for cid in re.findall(r"\bC\d+\b", rest.split("—")[0]):
                why = rest.split("—", 1)[1].strip() if "—" in rest else rest.strip()
                (killed if verb == "killed" else weakened).setdefault(cid, []).append((hat, why))

    chosen = ""
    ch = DV.section(txt, "Choice")
    mc = re.search(r"^\s*chosen\s*:\s*(C\d+)", ch, re.M | re.I)
    if mc:
        chosen = mc.group(1).upper()

    previz_dir = os.path.join(job, "00-brief", "_previz")
    previz = images_in(previz_dir)
    # (v2.69.0) each concept shows the research lines it cites, so the person can say which facts changed the film
    rlines = dict(DV.R_LINE_RE.findall(DV.section(txt, "Research")))

    panels = []
    for cid, title, body in cs:
        f = {k.lower(): v.strip() for k, v in DV.FIELD_RE.findall(body)}
        dead = cid in killed
        tags = []
        if cid == chosen:
            tags.append(tag("ok", "CHOSEN"))
        if dead:
            tags.append(tag("blocked", "KILLED"))
        elif cid in weakened:
            tags.append(tag("reference-only", "weakened"))
        elif rounds:
            tags.append(tag("ok", "survived"))
        shots = [x for x in previz
                 if re.match(rf"^{cid.lower()}[-_.]", os.path.basename(x).lower())]
        art = ""
        if shots:
            art = '<div class="slots">' + "".join(
                f'<div class="slot"><img src="{data_uri(s, SLOT_W)}" loading="lazy">'
                f'<div class="cap k">{esc(os.path.basename(s))} · previz</div></div>'
                for s in shots[:4]) + "</div>"
        reasons = ""
        for verb, store in (("killed by", killed), ("weakened by", weakened)):
            for hat, why in store.get(cid, []):
                reasons += (f'<div class="row"><span class="k">{esc(verb)}</span>'
                            f'<span>{esc(hat or "an adversarial round")} — {esc(why)}</span></div>')
        rows = "".join(
            f'<div class="row"><span class="k">{esc(k)}</span><span>{esc(f.get(k, "—"))}</span></div>'
            for k in ("premise", "structure", "proof", "risk") if f.get(k))
        for key, label in (("research", "rests on"), ("confirms", "confirmed by")):
            for rid in DV._ids(" ".join(DV.CITE_RE(key).findall(body))):
                rows += (f'<div class="row"><span class="k">{label} {esc(rid)}</span>'
                         f'<span>{esc(rlines.get(rid, "(not a research line)"))}</span></div>')
        cat_ = DV.CATEGORY_RE.search(body)
        if cat_:
            rows += (f'<div class="row"><span class="k">the usual ad</span><span>{esc(cat_.group(1))} · '
                     f'<b>{esc(cat_.group(2).lower())}</b> — {esc(cat_.group(3))}</span></div>')
        panels.append(f"""<div class="concept{' dead' if dead else ''}">
<h3>{esc(cid)} · {esc(title)}</h3><div>{''.join(tags)}</div>
<div class="q">{esc(f.get('question') or '(no dramatic question)')}</div>
<div class="row"><span class="k">one image</span><span><b>{esc(f.get('image') or '—')}</b></span></div>
{rows}{reasons}{art}</div>""")

    body = []
    body.append('<p class="note"><b>This is the choice, and it is yours.</b> The agent shortlists '
                'and argues; picking is the director\'s, and <code>gate.py approve concept</code> '
                'records your words verbatim. Five concepts read one after another get ratified; '
                'five concepts side by side get chosen between — that is the whole reason this '
                'page exists.</p>')
    if not previz:
        body.append('<p class="note">No previz on this board. Each concept is still a sentence '
                    'about a picture. <code>gate.py previz &lt;job&gt;</code> opens the capped '
                    'development lane if seeing one would change your answer — and if it would '
                    'not, do not spend it.</p>')
    body.append(f'<h2>{len(cs)} concept(s) · {rounds} adversarial round(s) · '
                f'{len(killed)} killed</h2>')
    body.append('<div class="grid wide">' + "\n".join(panels) + "</div>")
    sub = f"{len(cs)} concept(s), {len(killed)} killed" + (f" · chosen {chosen}" if chosen else
                                                           " · <b>not yet chosen</b>")
    return page("Concept board", sub, "\n".join(body), job), len(cs)


# ------------------------------------------------------------------------------------ the shot board
def build_shots(job: str) -> tuple:
    import prompt_lint as PL
    dirs = []
    for root, dd, files in os.walk(job):
        dd[:] = [d for d in dd if not d.startswith((".", "_to_delete"))]
        if any(f.endswith(".prompt.md") for f in files):
            dirs.append(root)
    if not dirs:
        return page("Shot board", "no prompts yet",
                    '<p class="empty">No <code>*.prompt.md</code> anywhere under the job. '
                    '<code>prompt_lint.py --template frame|clip</code> prints the shape to start '
                    'from.</p>', job), 0

    sections, gaps, blocked = [], 0, 0
    for d in sorted(dirs):
        rows = PL.plan_rows(d, job)
        by_shot: dict = {}
        for r in rows:
            by_shot.setdefault((r["shot"], r["kind"], r["prompt"]), []).append(r)
        for (shot, kind, pfile), refs in by_shot.items():
            fm, bodytxt = PL.split_front(read(pfile))
            bl = PL.blocks_of(bodytxt)
            slots = []
            for r in refs:
                if r["what"] == "(none)":
                    continue
                state = r["state"]
                if state == "gap":
                    gaps += 1
                elif state == "blocked":
                    blocked += 1
                thumb = ""
                if r["path"] and os.path.isfile(r["path"]) and r["path"].lower().endswith(IMG_EXT):
                    u = data_uri(r["path"], SLOT_W)
                    if u:
                        thumb = f'<img src="{u}" loading="lazy">'
                if not thumb:
                    if r["path"] and r["path"].lower().endswith(VID_EXT):
                        why = "video reference (not previewed)"
                    elif state == "gap":
                        why = "NOT SOURCED" + (f" — need: {r['need']}" if r["need"] else "")
                    elif state == "bound":
                        why = f"bound at call time: {r['source']}"
                    else:
                        why = "no preview"
                    thumb = f'<div class="miss">{esc(why)}</div>'
                st = {"ok": "ok", "bound": "ok", "gap": "blocked", "blocked": "blocked",
                      "none": "none"}.get(state, "none")
                label = {"ok": "ready", "bound": "id", "gap": "GAP",
                         "blocked": "BLOCKED"}.get(state, state)
                slots.append(f'<div class="slot">{thumb}<div class="cap">'
                             f'<div><b>{esc(r["what"])}</b> · {esc(r["role"])}</div>'
                             f'<div>{tag(st, label)}</div>'
                             f'<div class="k">{esc(r["detail"])}</div></div></div>')
            keys = [k for k in ("SUBJECT", "MOTION", "ENVIRONMENT", "LIGHTING", "CAMERA", "STYLE")
                    if bl.get(k)]
            blocks = "".join(f'<div><b>{esc(k)}</b> — {esc(bl[k][:180])}</div>' for k in keys)
            ok_path = pfile.replace(".prompt.md", ".prompt.ok")
            lint = tag("ok", "linted") if os.path.isfile(ok_path) else tag("blocked", "not linted")
            sections.append(f"""<div class="shot">
<h3>{esc(shot)} <span class="k">{esc(kind)} · {esc(fm.get('model') or 'no model')} ·
{esc(fm.get('aspect') or '')}</span> {lint}</h3>
<div class="blocks">{blocks or '<i>no blocks</i>'}</div>
{'<div class="slots">' + ''.join(slots) + '</div>' if slots
 else '<p class="empty">No references planned for this shot — a choice you should have made on purpose.</p>'}
</div>""")

    body = ['<p class="note"><b>Every reference slot, as the picture it actually binds.</b> This is '
            'the page that answers “will this work?” before a credit is spent: an empty slot, an '
            'uncleared face, or a picture that is simply not the thing the shot needs is obvious '
            'here and invisible in a <code>refs:</code> block. '
            '<code>gate.py approve cast</code> and <code>approve clips</code> refuse while any of '
            'them is a gap.</p>']
    body += sections
    sub = f"{len(sections)} shot(s)"
    if gaps or blocked:
        sub += f" · <b>{gaps} gap(s), {blocked} blocked</b>"
    else:
        sub += " · every reference sourced and cleared"
    return page("Shot board", sub, "\n".join(body), job), len(sections)


# --------------------------------------------------------------------------------- the PPM packet
def build_ppm(job: str) -> tuple:
    """Everything the pre-production meeting signs off, on one page.

    ⛔ A packet is not a fifth opinion — it assembles the four artifacts that already exist and puts
    the OPEN QUESTIONS at the top, where a meeting can actually answer them. Four separate files
    opened in the right order is not a review; it is four reviews, and the last one gets skimmed.

    It refuses to look finished when it is not: what is missing is listed as missing, in the first
    section, before anything that looks like progress."""
    import breakdown as BD
    open_q, done = [], []

    def art(rel, label, builder=""):
        p = os.path.join(job, rel)
        if os.path.isfile(p):
            done.append((label, rel, os.path.getmtime(p)))
            return True
        open_q.append(f"{label} has not been built" + (f" — `{builder}`" if builder else ""))
        return False

    art(os.path.join("00-brief", "CHECKPOINT.md"), "The checkpoint", "gate.py open <job>")
    art(os.path.join("00-brief", "DEVELOPMENT.md"), "The development doc", "develop.py init <job>")
    has_look = art(os.path.join("00-brief", "BOARD-look.html"), "The look board",
                   "board.py look <job>")
    has_con = art(os.path.join("00-brief", "BOARD-concepts.html"), "The concept board",
                  "board.py concepts <job>")
    has_shots = art(os.path.join("01-script", "BOARD-shots.html"), "The shot board",
                    "board.py shots <job>")
    slug = os.path.basename(os.path.abspath(job))
    art(os.path.join("01-script", f"SHOTLIST-{slug}.md"), "The shot list",
        f"shotlist.py {os.path.relpath(job)}")

    # what the cross-shot view says — the findings a per-shot check cannot see
    try:
        bd = BD.breakdown(job)
        cont = BD.continuity(job)
    except Exception as e:                                  # a broken reader must not fake a packet
        bd, cont = {"requirements": [], "cast": [], "findings": [
            {"kind": "error", "detail": f"the breakdown could not be read ({e})"}], "shot_count": 0}, \
            {"pairs": []}

    # the shot list's own honesty: how much is still the director's
    owed_n = 0
    slp = os.path.join(job, "01-script", f"SHOTLIST-{slug}.md")
    if os.path.isfile(slp):
        owed_n = read(slp).count("<NEEDS DIRECTION>")
        if owed_n:
            open_q.append(f"the shot list has {owed_n} field(s) still marked "
                          f"&lt;NEEDS DIRECTION&gt; — shot sizes, camera moves and performances "
                          f"nobody has decided")
    for f in bd.get("findings", []):
        open_q.append(f["detail"])
    for p in cont.get("pairs", []):
        open_q.append(f"{p['attribute']}: {p['a']} and {p['b']} describe it differently "
                      f"(overlap {p['overlap']:.0%}) — deliberate, or drift?")

    parts = []
    if open_q:
        items = "".join(f"<li>{esc(q)}</li>" for q in open_q)
        parts.append(f'<h2>{len(open_q)} open question(s) — answer these in the room</h2>'
                     f'<p class="note">⛔ <b>This is the agenda.</b> Everything below is what has '
                     f'been decided; this is what has not, and a packet that led with the finished '
                     f'work would let the meeting end without touching it.</p>'
                     f'<div class="card"><div class="body"><ul>{items}</ul></div></div>')
    else:
        parts.append('<h2>Nothing outstanding</h2><p class="note">Every artifact is built, every '
                     'requirement is owned and sourced, no attribute drifts between shots, and the '
                     'shot list carries no undirected field. Sign it.</p>')

    if bd.get("cast"):
        rows = "".join(
            f"<tr><td><b>{esc(c['name'])}</b></td><td>{esc(', '.join(c['shots']))}</td>"
            f"<td>{'locked' if c['locked_by'] else '⛔ not locked by a reference'}</td></tr>"
            for c in bd["cast"])
        parts.append(f'<h2>Cast</h2><div class="card"><div class="body"><table>'
                     f'<tr><th>who</th><th>shots</th><th>identity</th></tr>{rows}'
                     f'</table></div></div>')

    if bd.get("requirements"):
        rows = ""
        for r in bd["requirements"]:
            if r["unsourced_shots"] and r["distinct_sources"]:
                st, cls = f"partly sourced · {len(r['unsourced_shots'])} open", "t-warn"
            elif r["unsourced_shots"]:
                st, cls = "nothing sourced", "t-bad"
            elif r["distinct_sources"] > 1:
                st, cls = f"{r['distinct_sources']} different sources", "t-bad"
            else:
                st, cls = ("one reference, shared" if r["shared"] else "sourced"), "t-ok"
            rows += (f"<tr><td><b>{esc(r['attribute'])}</b></td>"
                     f"<td>{esc(', '.join(r['shots']))}</td>"
                     f"<td><span class=\"tag {cls}\">{esc(st)}</span></td></tr>")
        parts.append(f'<h2>Breakdown — what this film needs, across all {bd["shot_count"]} shot(s)'
                     f'</h2><div class="card"><div class="body"><table>'
                     f'<tr><th>attribute</th><th>shots</th><th>status</th></tr>{rows}</table>'
                     f'</div></div>')

    if done:
        items = "".join(
            f'<tr><td>{esc(l)}</td><td><a href="{esc(os.path.basename(rel) if rel.endswith(".html") else rel)}">'
            f'{esc(rel)}</a></td>'
            f'<td class="k">{dt.datetime.fromtimestamp(m).strftime("%Y-%m-%d %H:%M")}</td></tr>'
            for l, rel, m in done)
        parts.append(f'<h2>What is built</h2><div class="card"><div class="body"><table>'
                     f'<tr><th>artifact</th><th>where</th><th>last built</th></tr>{items}</table>'
                     f'<p class="k" style="margin-top:10px">The links are relative — this packet '
                     f'sits in the job beside them. Open the three boards for the pictures; this '
                     f'page is the agenda, not a replacement for looking.</p></div></div>')

    have = sum(1 for x in (has_look, has_con, has_shots) if x)
    sub = f"{len(open_q)} open · {have}/3 boards built"
    return page("Pre-production meeting", sub, "\n".join(parts), job), len(open_q)


# ------------------------------------------------------------------------- the storyboard (2.66.0)
# Shot size → how tall a standing person reads in a 16:9 frame (frame heights). A drawn placeholder,
# so an empty panel still says WIDE or CLOSE at a glance instead of saying nothing.
SIZE_SCALE = {"EWS": 0.14, "WS": 0.42, "MWS": 0.75, "MS": 1.15, "MCU": 1.7, "CU": 2.6, "XCU": 4.5}
STORY_CSS = """
.strip{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px 8px;
  box-shadow:var(--shadow);margin-bottom:22px;overflow-x:auto}
.strip svg{display:block;width:100%;min-width:560px;height:auto}
.panels{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;
  box-shadow:var(--shadow);display:flex;flex-direction:column}
.panel.theirs{border:2px solid var(--accent)}
.panel img,.panel svg.ph{width:100%;display:block;aspect-ratio:16/9;object-fit:contain;background:#8882}
.panel .body{padding:10px 12px 12px;font-size:13px}
.panel .hd{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.panel .id{font-weight:700;font-size:15px}
.panel .line{font-size:14px;margin:4px 0 6px}
"""


def size_svg(size: str) -> str:
    """A grey frame with one figure at the shot's size — the placeholder for a panel nobody drew."""
    s = (size or "").upper().split()[0] if size else ""
    s = re.sub(r"[^A-Z]", "", s.split("→")[0] if "→" in s else s)
    if s == "INSERT":
        body = '<rect x="58" y="30" width="44" height="34" rx="3" fill="#8889"/>'
    else:
        k = SIZE_SCALE.get(s, 0.75)
        h = 90 * k                                 # figure height in frame units
        top = 90 - h * 0.92 if k < 1 else 12 - (k - 1) * 18
        head_r = h * 0.075
        cx = 80
        body = (f'<circle cx="{cx}" cy="{top + head_r:.1f}" r="{head_r:.1f}" fill="#8889"/>'
                f'<rect x="{cx - h * 0.13:.1f}" y="{top + head_r * 2.2:.1f}" width="{h * 0.26:.1f}" '
                f'height="{h * 0.62:.1f}" rx="{h * 0.05:.1f}" fill="#8887"/>')
    return (f'<svg class="ph" viewBox="0 0 160 90" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="placeholder: {esc(size or "no size")}"><rect width="160" height="90" fill="#8882"/>'
            f'<g>{body}</g>'
            f'<text x="6" y="12" font-size="8" fill="currentColor" opacity=".7">{esc(size or "?")} · not drawn</text></svg>')


def energy_svg(ps: list) -> str:
    """The film's energy over its running time: one point per shot at its middle, cut lines between."""
    total = sum(p["dur"] or 0 for p in ps) or 1.0
    W, H, pad = 1000, 96, 18
    t, pts, cuts, labels = 0.0, [], [], []
    for p in ps:
        d = p["dur"] or 0
        try:
            e = max(1.0, min(5.0, float(p["energy"])))
        except (TypeError, ValueError):
            e = None
        x0 = pad + (W - 2 * pad) * t / total
        xm = pad + (W - 2 * pad) * (t + d / 2) / total
        if e is not None:
            pts.append(f"{xm:.1f},{H - 22 - (e - 1) / 4 * (H - 40):.1f}")
        cuts.append(f'<line x1="{x0:.1f}" y1="8" x2="{x0:.1f}" y2="{H - 16}" stroke="currentColor" opacity=".15"/>')
        labels.append(f'<text x="{xm:.1f}" y="{H - 4}" font-size="10" text-anchor="middle" '
                      f'fill="currentColor" opacity=".7">{esc(p["shot"])}</text>')
        t += d
    line = (f'<polyline points="{" ".join(pts)}" fill="none" stroke="var(--accent)" stroke-width="2.5" '
            f'stroke-linejoin="round"/>' + "".join(f'<circle cx="{q.split(",")[0]}" cy="{q.split(",")[1]}" r="3.5" '
                                                   f'fill="var(--accent)"/>' for q in pts)) if pts else ""
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="energy across the film, 1 to 5, one point per shot">'
            f'{"".join(cuts)}{line}{"".join(labels)}</svg>')


def build_storyboard(job: str) -> tuple:
    """One panel per shot in cut order — picture, size, move, seconds, the line it carries, what changes in
    it — with the film's energy on top. What `gate.py approve storyboard` signs, beside the animatic."""
    import storyboard as SB
    ps, errs = SB.panels(job)
    md = read(SB.shotlist_path(job)) if os.path.isfile(SB.shotlist_path(job)) else ""
    meta = f'<meta name="{SB.FILM_META}" content="{SB.digest(md)}">' if md and not errs else ""
    if errs or not ps:
        body = ('<p class="empty">' + esc("; ".join(errs) or "the Sequence chain has no shots") + '</p>')
        return page("Storyboard", "not built: the shot list cannot be read", body, job), 0
    total = sum(p["dur"] or 0 for p in ps)
    theirs = sum(1 for p in ps if p["source"] == "their sketch")
    drawn = sum(1 for p in ps if p["source"] == "drawing")
    cards = []
    for p in ps:
        if p["picture"]:
            u = data_uri(p["picture"], 640)
            pic = f'<img src="{u}" alt="{esc(p["shot"])}" loading="lazy">' if u else size_svg(p["size"])
        else:
            pic = size_svg(p["size"])
        src = (tag("ok", "your sketch") if p["source"] == "their sketch" else
               tag("none", "drawing") if p["source"] == "drawing" else tag("none", "placeholder"))
        turn = p["turn"] if p["turn"] and p["turn"] != "-" else ""
        cards.append(f"""<div class="panel{' theirs' if p['source'] == 'their sketch' else ''}">{pic}
<div class="body"><div class="hd"><span class="id">{esc(p['shot'])}</span>
<span class="k">{esc(p['size'])} · {esc(p['move'])} · {p['dur'] or '?'} s · energy {esc(p['energy'] or '?')}</span></div>
{f'<div class="line">“{esc(p["line"])}”</div>' if p['line'] else ''}
{f'<p>{esc(p["action"])}</p>' if p['action'] else ''}
<p class="k">{esc(p['scene'])} · {esc(p['beat'])}{' · changes: ' + esc(turn) if turn else ''}{' · looks at ' + esc(p['target']) if p['target'] and p['target'] != '-' else ''}</p>
{src}</div></div>""")
    body = [f'<p class="note"><b>The film as pictures in time, before anything is paid for.</b> One panel per shot '
            f'in cut order. Watch the animatic beside it (<code>01-script/ANIMATIC.mp4</code>): each panel held for '
            f'its planned seconds. Changing a panel here costs nothing; changing it after the clips costs a '
            f'regeneration. <code>gate.py approve storyboard</code> is what you sign.</p>',
            f'<h2>Energy across {total:.1f} seconds</h2><div class="strip">{energy_svg(ps)}</div>',
            f'<h2>{len(ps)} panels</h2><div class="panels">{"".join(cards)}</div>']
    sub = (f"{len(ps)} shot(s) · {total:.1f} s · {theirs} of yours · {drawn} drawn · "
           f"{len(ps) - theirs - drawn} placeholder(s)")
    doc = page("Storyboard", sub, "\n".join(body), job)
    doc = doc.replace("</style>", STORY_CSS + "</style>" + meta, 1)
    return doc, len(ps)


def build_frames(job: str) -> tuple:
    """Every approved start frame in cut order, on one page: what `gate.py approve startframes` signs before
    any clip. One frame at a time looks fine; side by side, a face, a light or a colour that drifts is plain."""
    import storyboard as SB
    fr = SB.approved_frames(job)
    meta = f'<meta name="{SB.FRAMES_META}" content="{SB.frames_digest(fr)}">'
    ps, _ = SB.panels(job)
    order = [p["shot"] for p in ps]
    info = {p["shot"]: p for p in ps}
    shots = [s for s in order if s in fr] + sorted(s for s in fr if s not in order)
    missing = [s for s in order if s not in fr]
    cards = []
    for s in shots:
        r = fr[s]
        ap = r["artifact"] if os.path.isabs(r["artifact"]) else os.path.join(job, r["artifact"])
        u = data_uri(ap, 640) if os.path.isfile(ap) and ap.lower().endswith(IMG_EXT) else ""
        pic = f'<img src="{u}" alt="{esc(s)}" loading="lazy">' if u else \
            f'<div class="miss">{esc(r["artifact"] or "no file")} is not on disk</div>'
        p = info.get(s, {})
        cards.append(f"""<div class="panel">{pic}<div class="body"><div class="hd"><span class="id">{esc(s)}</span>
<span class="k">{esc(p.get('size', ''))} · {esc(p.get('move', ''))} · {p.get('dur') or '?'} s</span></div>
{f'<div class="line">“{esc(p["line"])}”</div>' if p.get('line') else ''}
<p class="k">approved {esc(r['ts'])} · media {esc(r['media_id'] or '—')}</p></div></div>""")
    body = ['<p class="note"><b>Every approved start frame, in cut order.</b> Look across them, not at one: the '
            'same face, the same light side, the same colour, the same props in the same hands. A clip starts '
            'from each of these, so a drift here is a drift in every clip. <code>gate.py approve startframes'
            '</code> signs this page; a frame approved after it needs the page signed again.</p>']
    if missing:
        body.append(f'<p class="note">Not approved yet: <b>{esc(", ".join(missing))}</b>. Shots built from '
                    f'reference sheets instead of a start frame (<code>form: scene</code>) belong here as gaps.</p>')
    body.append(f'<div class="panels">{"".join(cards)}</div>' if cards else
                '<p class="empty">No start frame is approved yet.</p>')
    doc = page("Start frames", f"{len(shots)} approved · {len(missing)} not yet", "\n".join(body), job)
    doc = doc.replace("</style>", STORY_CSS + "</style>" + meta, 1)
    return doc, len(shots)


# ------------------------------------------------------------------------------------------ main
BUILDERS = {
    "look": (build_look, os.path.join("00-brief", "BOARD-look.html")),
    "concepts": (build_concepts, os.path.join("00-brief", "BOARD-concepts.html")),
    "shots": (build_shots, os.path.join("01-script", "BOARD-shots.html")),
    "storyboard": (build_storyboard, os.path.join("01-script", "BOARD-storyboard.html")),
    "frames": (build_frames, os.path.join("01-script", "BOARD-frames.html")),
    "ppm": (build_ppm, os.path.join("00-brief", "PPM.html")),
}


def build(which: str, job: str, out: str | None = None) -> tuple:
    fn, rel = BUILDERS[which]
    doc, n = fn(job)
    dest = out or os.path.join(job, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return dest, n


def selftest() -> int:
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and bool(cond)

    check("Pillow is available (thumbnails and the measured palette need it)", Image is not None)

    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        look = os.path.join(job, "00-brief", "_look")
        pr = os.path.join(job, "01-script", "prompts")
        os.makedirs(look)
        os.makedirs(pr)

        doc, n = build_look(job)
        check("an empty look board says what to do, not nothing", n == 0 and "pixabay_search" in doc)

        colours = [(200, 40, 30), (30, 120, 200), (240, 220, 120), (20, 20, 20)]
        for i, c in enumerate(colours, 1):
            a = os.path.join(look, f"ref{i}.jpg")
            if Image:
                Image.new("RGB", (200, 150), c).save(a, "JPEG")
            else:
                open(a, "wb").write(b"\xff\xd8\xff\x00")
            json.dump({"source": "pixabay", "user": "someone",
                       "pageURL": f"https://pixabay.com/photos/x-{i}/",
                       "tags": "bakery, bread",
                       "clearance": ("CLEARED by Dana on 2026-09-06" if i == 1
                                     else "NOT CLEARED — outstanding")},
                      open(a + ".json", "w"))
        # one with no sidecar at all
        bare = os.path.join(look, "bare.jpg")
        if Image:
            Image.new("RGB", (200, 150), (90, 90, 90)).save(bare, "JPEG")
        else:
            open(bare, "wb").write(b"\xff\xd8\xff\x00")

        doc, n = build_look(job)
        check("every picture reaches the board", n == 5)
        check("images are embedded, so the file travels alone", doc.count("data:image/") >= 5)
        check("a cleared picture is marked cleared", "cleared</span>" in doc)
        check("an uncleared picture is marked NOT CLEARED", "NOT CLEARED" in doc)
        check("a picture with no record is called out", "NO PROVENANCE" in doc)
        check("the palette is measured off the pictures",
              "The palette these pictures actually are" in doc and doc.count('class="sw"') >= 4)
        check("the page is self-contained", "http-equiv" not in doc and "<script" not in doc
              and "src=\"http" not in doc)
        check("it is theme-aware", "prefers-color-scheme" in doc and 'data-theme="dark"' in doc)

        # --- concepts -----------------------------------------------------------------------
        doc, n = build_concepts(job)
        check("no DEVELOPMENT.md says so plainly", n == 0 and "develop.py init" in doc)
        dev = os.path.join(job, "00-brief", "DEVELOPMENT.md")
        seeds = [("a dark shop", "day-in-life", "Who was here at four?"),
                 ("one loaf one bench", "demo", "What does baked here mean?"),
                 ("a queue", "list", "Why this shop?")]
        cs = "\n".join(f"### C{i} · concept {i}\npremise: p{i}\nquestion: {q}\nimage: {img}\n"
                       f"structure: {st}\nproof: r{i}\nrisk: k{i}\n"
                       for i, (img, st, q) in enumerate(seeds, 1))
        cs = cs.replace("risk: k2\n", "risk: k2\nresearch: R1\ncategory: the hero loaf ad · ours: break — we open "
                                       "on a dark shop at four\n")
        open(dev, "w").write(
            f"# DEVELOPMENT\n\n## Research\n\ntier: T1\n\n- R1 [PRIMARY · the baker · 2026-11-14] the ovens start at four "
            f"· decides: C2 instead of C3\n\n## Concepts\n\n{cs}\n"
            "## Adversarial round 1 · the skeptical buyer\n\n"
            "killed: C3 — an implied comparative claim the profile locks out\n"
            "weakened: C1 — the proof is thin\nsurvived: C1, C2\n\n"
            "## Choice\n\nchosen: C2\nby: Dana\nquote: \"C2, the bench one\"\n")
        doc, n = build_concepts(job)
        check("every concept gets a panel", n == 3)
        check("the killed one is marked killed and dimmed",
              "KILLED" in doc and 'class="concept dead"' in doc)
        check("the kill REASON is on the board, not just the verdict",
              "implied comparative claim" in doc)
        check("the weakened one is distinguished from the killed one", "weakened</span>" in doc)
        check("the chosen one is marked", "CHOSEN" in doc)
        check("the dramatic question leads each panel", "Who was here at four?" in doc)
        check("(2.69) a concept shows the research line it rests on and its keep-or-break line",
              "rests on R1" in doc and "the ovens start at four" in doc and "<b>break</b>" in doc)
        check("with no previz it says so and does not push a spend",
              "if seeing one would change your answer" in doc)

        pv = os.path.join(job, "00-brief", "_previz")
        os.makedirs(pv)
        if Image:
            Image.new("RGB", (240, 320), (60, 40, 30)).save(os.path.join(pv, "C2-open.jpg"), "JPEG")
        doc, _ = build_concepts(job)
        check("previz bound to a concept appears on that concept's panel",
              "C2-open.jpg" in doc and "previz</div>" in doc)

        # --- shots --------------------------------------------------------------------------
        doc, n = build_shots(job)
        check("no prompts says so", n == 0 and "--template" in doc)
        refdir = os.path.join(job, "_reference", "wardrobe")
        os.makedirs(refdir)
        apron = os.path.join(refdir, "apron.jpg")
        if Image:
            Image.new("RGB", (200, 300), (230, 230, 225)).save(apron, "JPEG")
        else:
            open(apron, "wb").write(b"\xff\xd8\xff\x00")
        json.dump({"source": "pixabay", "clearance": "CLEARED by Dana on 2026-09-06"},
                  open(apron + ".json", "w"))
        open(os.path.join(pr, "S1.frame.prompt.md"), "w").write(
            "---\nshot: S1\nkind: frame\nmodel: nano_banana\naspect: 9:16\nrefs:\n"
            "  - role: image, what: wardrobe, file: _reference/wardrobe/apron.jpg\n"
            "  - role: image, what: environment, need: small tiled bakery kitchen\n"
            "---\n[SUBJECT]\nA baker slides a tray forward\n\n[LIGHTING]\n5200K daylight\n\n"
            "[CAMERA]\n35mm, eye level\n")
        doc, n = build_shots(job)
        check("the shot reaches the board", n == 1 and ">S1<" in doc.replace(" ", ""))
        check("a sourced reference is shown as its picture", doc.count("data:image/") >= 1)
        check("an unsourced slot is shown as a GAP with what it needs",
              "GAP" in doc and "small tiled bakery kitchen" in doc)
        check("an unlinted prompt is marked unlinted", "not linted" in doc)
        check("the header counts the gaps", "1 gap(s)" in doc)

        # --- the PPM packet -----------------------------------------------------------------
        # build the three boards first, the way a real job would, so the packet has both halves
        # to report: what exists (linked) and what does not (named with its command).
        for w in ("look", "concepts"):
            build(w, job)
        # a second shot needing the SAME unsourced attribute, so a genuine cross-shot finding
        # exists to reach the agenda — one shot can never produce one, and asserting against a
        # fixture that cannot fail is the grader mistake this repo already made once
        open(os.path.join(pr, "S2.frame.prompt.md"), "w").write(
            "---\nshot: S2\nkind: frame\nmodel: nano_banana\naspect: 9:16\nrefs:\n"
            "  - role: image, what: environment, need: small tiled bakery kitchen\n"
            "---\n[SUBJECT]\nthe room\n\n[LIGHTING]\n5200K daylight\n\n[CAMERA]\n28mm\n")
        doc, nq = build_ppm(job)
        check("the packet LEADS with the open questions, not the finished work",
              nq > 0 and doc.index("open question") < doc.index("What is built"))
        check("a board that has not been built is listed as missing, with the command",
              "shot board has not been built" in doc and "board.py shots" in doc)
        check("the cross-shot findings reach the agenda — the things no single shot is wrong about",
              "Breakdown —" in doc and "source it ONCE" in doc)
        check("what IS built is linked, with when it was built", 'href="BOARD-look.html"' in doc)
        # once everything exists and nothing is outstanding it says so rather than padding
        empty = os.path.join(td, "clean")
        os.makedirs(os.path.join(empty, "00-brief"))
        for rel in ("00-brief/CHECKPOINT.md", "00-brief/DEVELOPMENT.md",
                    "00-brief/BOARD-look.html", "00-brief/BOARD-concepts.html"):
            fp = os.path.join(empty, rel)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, "w").write("x")
        os.makedirs(os.path.join(empty, "01-script"))
        open(os.path.join(empty, "01-script", "BOARD-shots.html"), "w").write("x")
        open(os.path.join(empty, "01-script", "SHOTLIST-clean.md"), "w").write("| 1 | a | b |")
        doc2, nq2 = build_ppm(empty)
        check("a complete job says nothing is outstanding, and does not invent an agenda",
              nq2 == 0 and "Nothing outstanding" in doc2)

        dest, _ = build("look", job)
        check("build() writes where the job expects it",
              dest.endswith(os.path.join("00-brief", "BOARD-look.html"))
              and os.path.getsize(dest) > 2000)

        # (v2.66.0) the storyboard and the start-frame sheet
        import storyboard as SB
        sj = os.path.join(td, "fx-01002-story")
        os.makedirs(os.path.join(sj, "01-script", "storyboard", "their"))
        os.makedirs(os.path.join(sj, "00-brief"))
        open(SB.shotlist_path(sj), "w").write(SB.FIXTURE)
        if Image is not None:
            Image.new("RGB", (64, 48), (200, 120, 60)).save(
                os.path.join(sj, "01-script", "storyboard", "their", "hands.png"))
        dest, n = build("storyboard", sj)
        doc = read(dest)
        check("the storyboard has one panel per shot, in cut order",
              n == 2 and doc.index('class="id">1<') < doc.index('class="id">2<'))
        check("it embeds the film digest the sign-off compares",
              SB.board_digest(dest, SB.FILM_META) == SB.digest(SB.FIXTURE))
        check("their sketch is marked as theirs and embedded; the undrawn shot gets a sized placeholder",
              "your sketch" in doc and "data:image/" in doc and "WS · not drawn" in doc)
        check("the energy curve and the line each shot carries are on the page",
              "energy across the film" in doc and "every loaf by hand" in doc)
        check("the page stays theme-aware with the storyboard styles added",
              "prefers-color-scheme:dark" in doc and ".panels{" in doc)
        open(os.path.join(sj, "00-brief", "APPROVALS.md"), "w").write(
            "| ts | stage | by | quote | artifact | sha256 | media_id | verified |\n|---|---|---|---|---|---|---|---|\n"
            "| t1 | frame:2 | D | yes | 01-script/storyboard/their/hands.png | aaaa | m1 | transcript |\n")
        dest, n = build("frames", sj)
        doc = read(dest)
        check("the frame sheet shows the approved frame and names the shot still without one",
              n == 1 and "Not approved yet: <b>1</b>" in doc and "media m1" in doc)
        check("...and embeds the frames digest the sign-off compares",
              SB.board_digest(dest, SB.FRAMES_META) == SB.frames_digest(SB.approved_frames(sj)))
        check("a missing shot list says so instead of drawing an empty film",
              "cannot be read" in build_storyboard(os.path.join(td, "nothing"))[0])

    print("-" * 60)
    print("selftest OK — the look board embeds its pictures, marks each clearance state and "
          "measures the palette off the set; the concept board carries kill reasons, the weakened/"
          "killed distinction and any bound previz; the shot board renders every reference slot and "
          "names the gaps; "
          "the PPM packet leads with what is unanswered and calls a complete job complete; every "
          "page is self-contained and theme-aware" if ok
          else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", nargs="?",
                    choices=["look", "concepts", "shots", "storyboard", "frames", "ppm", "all"])
    ap.add_argument("job", nargs="?")
    ap.add_argument("--out", help="write this one board here instead of into the job")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.what or not a.job:
        ap.print_help()
        return 2
    if not os.path.isdir(a.job):
        print(f"error: {a.job} is not a job folder", file=sys.stderr)
        return 2
    if Image is None:
        print("note: Pillow is not installed — images embed at full size and the measured palette "
              "is skipped (pip install pillow)", file=sys.stderr)
    which = ["look", "concepts", "shots", "ppm"] if a.what == "all" else [a.what]
    if a.out and len(which) > 1:
        print("error: --out takes one board, not `all`", file=sys.stderr)
        return 2
    for w in which:
        dest, n = build(w, a.job, a.out)
        print(f"{w:<9} {n:>3} item(s)  →  {os.path.relpath(dest)}")
    print("\nOpen it. The boards do not decide anything — they are what makes deciding possible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
