#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""resolve_library.py — the owner's INSTALLED Resolve library, used: what is installed, what kind of thing each item
is in this skill's words, and how a script places it.

The author, 2026-10-29: titles default to Resolve/Fusion native elements (ruling C7), and the packs he bought or
installed are to be USED — Fusion titles such as "Background Reveal" and "Background Reveal Lower Third", the JTechWP
and Video Editor Studio title and transition packs, "Free Smooth Transitions", Krokodove's generators and effects, and
the OFX plugins MagicAnimate Free (MrAlexTech), CineDream and Higgsfield Color Match.

  scan (--job JOB | --studio DIR | --out FILE) [--from-console FILE] [--folder DIR ...] [--names FILE ...]
       [--effects-json FILE]
        → <job>/07-edit/resolve-library.json, or <DIR>/resolve-library.json at studio level (the production root's
        _studio/): every title, transition, generator and effect, with its category and id where Resolve gave one, its
        pack, a Fusion macro's PUBLISHED INPUTS where its file was readable, the call that places it, and a `kinds`
        map from the skill's kinds (lower-third, end-card, super, hero, stat, price, logo-animate · dissolve, dip,
        smooth-cut, whip, push, zoom, wipe, light-leak, glitch · animate-in-out, continuous-zoom, 3d-text, glow,
        glitch, color-match, grade …) to the installed items, starred first. Sources, any mix:
          --from-console   the console's LIBRARY_SCAN result (Resolve.GetEffectsList: Fusion, OFX and audio effects
                           with category and id; and, run in Workspace ▸ Console or run_script_unsafe, the template
                           folders with each macro's published inputs) — or INVENTORY_TEMPLATES' file
          --folder         a Fusion Templates folder read from here (…/Fusion/Templates, once the owner grants it)
          --names          a list the owner pastes: "Titles/Background Reveal", "transition: Smooth Zoom In", or names
                           under "# Titles" / "# Transitions" / "# Effects" headings (a JSON list works too)
          --effects-json   a saved GetEffectsList result
        Titles and transitions are NOT in GetEffectsList; the template folders, or the owner's list, are the only way
        to know them. Stars and notes are kept across re-scans.
  kinds <inventory>                 the kinds map, with how each item is placed and what is manual
  pick <inventory> --kind KIND      the item to use for a kind (title/lower-third, transition/zoom, whip, …)
  plan <job> [--plan 07-edit/fx-plan.json]   resolve a plan of kinds to installed items (refusals below)
  console <job> [--scan] [--plan FILE] [--host-job PATH]
        → 07-edit/resolve-production-console.library.py: LIBRARY_SCAN, and/or APPLY_TRANSITIONS / APPLY_EFFECTS with the
        resolved plan spliced in (AddTransition at each cut, both neighbours read back; AddEffect on each named item, a
        Fusion effect's inputs set through its comp and read back)
  --selftest

What a script can and cannot do (the 21.1.2 stubs): AddTransition takes {type, category simple|fusion|ofx, position,
alignment, duration}; AddEffect takes (category, id) from GetEffectsList; a Fusion effect's comp is reachable
(Effect.GetFusionComp) and its inputs settable; titles go in by name (InsertFusionTitleIntoTimeline), generators by
InsertFusionGeneratorIntoTimeline / InsertOFXGeneratorIntoTimeline. There is NO call that sets an OFX parameter: an OFX
effect goes on with its defaults (or a preset saved in its own UI), and the choice inside it is a MANUAL pick —
MagicAnimate's In / Mid / Out animation, CineDream's look, Higgsfield Color Match's reference. The plan says so, the
console flags it, and nothing pretends otherwise.

Refusals (plan / console): a kind nothing installed provides; an item whose name says it overshoots (bounce, elastic,
spring, pop…) on a title, number or UI (house rule C2); an effect with no id (a template-folder effect: run LIBRARY_SCAN
through the console for its id); more accent transitions than the title card allows (C5).
"""
from __future__ import annotations
import argparse, datetime as dt, glob, json, os, re, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
SCHEMA = "cine.resolve-library/1"
JOB_FILE = os.path.join("07-edit", "resolve-library.json")
STUDIO_FILE = "resolve-library.json"
PLAN_FILE = os.path.join("07-edit", "fx-plan.json")
CONSOLE = os.path.join(HERE, "resolve-production-console.py")
CONSOLE_COPY = "resolve-production-console.library.py"
TYPES = ("title", "transition", "generator", "effect", "ofx-effect", "ofx-generator", "audio-effect")
# Resolve's own Video Transitions (category simple). Cross Dissolve was MEASURED through AddTransition on 21.1.0.14;
# the other names are the Effects Library's [practitioner — the live test L7 confirms each].
BUILTIN_TRANSITIONS = ["Cross Dissolve", "Dip To Color Dissolve", "Smooth Cut", "Additive Dissolve", "Blur Dissolve",
                       "Push", "Slide", "Edge Wipe"]
# the transition grammar's own defaults (editing-and-audio.md): a dissolve is Resolve's Cross Dissolve unless starred
PREFERRED = {"transition/dissolve": "Cross Dissolve", "transition/dip": "Dip To Color Dissolve",
             "transition/smooth-cut": "Smooth Cut"}
TITLE_KINDS = [
    ("lower-third", r"lower ?third|\bl ?3\b|name ?(tag|plate|title)|\bstrap"),
    ("end-card", r"end ?(card|screen)|outro|\bcta\b|call to action"),
    ("social", r"subscribe|social|follow|like ?button|youtube|instagram|tiktok"),
    ("logo-animate", r"logo"),
    ("call-out", r"call ?-?out|pointer|annotation"),
    ("stat", r"counter|count ?up|\bnumbers?\b|\bstats?\b"),
    ("price", r"price|\bsale\b|discount"),
    ("place-time", r"location|\bplace\b|\bdate\b|time ?stamp"),
    ("super", r"\bsuper\b|caption|subtitle|text ?box|reveal|\bbox\b"),
    ("hero", r"headline|hero|title reveal|kinetic|typewriter|big ?title|opener|intro|cinematic|\btitle\b"),
]
EFFECT_KINDS = [
    ("animate-in-out", r"magicanimate|animat(e|ion) ?in|in ?(&|and) ?out|\banimate\b"),
    ("continuous-zoom", r"continuous ?zoom|slow ?zoom|ken ?burns|push ?in"),
    ("glow", r"glow"), ("shadow", r"shadow"), ("glass", r"glass"),
    ("glitch", r"glitch|rgb ?split|chromatic"), ("phone", r"phone"), ("video-call", r"video ?call"),
    ("drone-overlay", r"drone"), ("pen-stroke", r"pen ?stroke|scribble"), ("3d-text", r"extrude|bevel|spherize|\b3d\b"),
    ("paper-edge", r"paper ?edge|torn"), ("levitation", r"levitat"), ("icon-mask", r"icon ?mask"),
    ("exclusion", r"exclusion"), ("dve", r"\bdve\b|picture ?in ?picture|\bpip\b"),
    ("color-match", r"colou?r ?match"), ("grade", r"cinedream|full editor|base correction|final grading|film ?look"),
    ("fusion-utility", r"\bduplicate\b|\bpack\b|rasterize|\bgenerate\b"),
]
GENERATOR_KINDS = [("background", r"background|gradient|solid|noise|particle|grid|bokeh|generate")]
TRANSITION_ALIASES = {"slide": ["push", "slide"], "light": ["light-leak"], "whip": ["whip", "spin"]}
OVERSHOOT_RE = re.compile(r"bounce|elastic|spring|overshoot|wobble|jelly|\bpop\b", re.I)
PACKS = [("Krokodove", r"krokodove"), ("MrAlexTech MagicAnimate", r"mralextech|magicanimate"),
         ("CineDream", r"cinedream"), ("Higgsfield", r"higgsfield"), ("Video Editor Studio", r"video ?editor ?studio"),
         ("JTechWP", r"jtech"), ("Free Smooth Transitions", r"smooth ?transitions"),
         ("Blackmagic Resolve FX", r"resolve ?fx|resolvefx")]
# OFX items whose inside choice the API cannot set: (match, what is manual)
OFX_MANUAL = [(r"magicanimate", "MagicAnimate's In / Mid / Out animation is chosen in its Inspector (no OFX parameter "
                                "calls in 21.1.2): applied with its defaults or a saved preset — pick the animation by hand, "
                                "and on text one that lands without overshoot (C2)"),
              (r"cinedream", "CineDream's look is set in its own panel (grade_luts.py owns the grade plan): an owner-chosen "
                             "finishing node, applied with its defaults and set by hand"),
              (r"color ?match", "Higgsfield Color Match needs its reference picked in its UI: applied with its defaults, the "
                                "match set by hand")]


def now() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def jload(p: str):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ── what an item is ──────────────────────────────────────────────────────────────────────────────────────────
def pack_of(it: dict) -> str:
    blob = " ".join(str(it.get(k) or "") for k in ("id", "path", "source", "name"))
    for name, rx in PACKS:
        if re.search(rx, blob, re.I) or re.search(rx, str(it.get("id") or ""), re.I):
            return name
    src = str(it.get("source") or "")
    if src.startswith("drfx:"):
        return re.sub(r"\.drfx$", "", src[5:], flags=re.I)
    parts = [p for p in re.split(r"[/\\]", str(it.get("path") or "")) if p]
    if len(parts) >= 4 and parts[0].lower() == "edit":                   # Edit/<Kind>/<Pack>/<name>.setting
        return parts[2]
    if it.get("builtin"):
        return "Resolve (built in)"
    if str(it.get("id") or "").lower().startswith(("fusion/", "open fx/resolvefx", "resolvefx")):
        return "Blackmagic"
    return "unknown"


def kinds_of(it: dict) -> list:
    n = str(it.get("name") or "")
    t = it.get("type")
    if t == "transition":
        import motion_qa
        fam = motion_qa.trans_family(n)
        known = [f for f, _rx in motion_qa.TRANS_FAMILIES]
        return TRANSITION_ALIASES.get(fam, [fam]) if fam in known else []
    rules = TITLE_KINDS if t == "title" else (GENERATOR_KINDS if t in ("generator", "ofx-generator") else EFFECT_KINDS)
    out = [k for k, rx in rules if re.search(rx, n, re.I)]
    if t == "title" and "lower-third" in out and "hero" in out:
        out.remove("hero")
    return out


def describe(it: dict) -> dict:
    """The item with its pack, kinds, how it is placed and what is manual."""
    t, n = it.get("type"), it.get("name")
    it = dict(it)
    it["pack"] = it.get("pack") or pack_of(it)
    it["kinds"] = kinds_of(it)
    notes = list(it.get("notes") or [])
    if t == "title":
        it["place"] = {"call": "InsertFusionTitleIntoTimeline", "name": n}
        it["category"] = it.get("category") or "fusion"
    elif t == "generator":
        it["place"] = {"call": "InsertFusionGeneratorIntoTimeline", "name": n}
    elif t == "ofx-generator":
        it["place"] = {"call": "InsertOFXGeneratorIntoTimeline", "name": n}
    elif t == "transition":
        cat = it.get("category") or ("simple" if it.get("builtin") else "fusion")
        it["category"] = cat
        it["place"] = {"call": "AddTransition", "type": n, "category": cat}
        if cat != "simple":
            notes.append("a pack transition through AddTransition(category fusion) is [stub] until the live test (L7): "
                         "both neighbours are read back")
    elif t in ("effect", "ofx-effect", "audio-effect"):
        cat = it.get("category") or {"effect": "fusion", "ofx-effect": "ofx", "audio-effect": "audio"}[t]
        it["category"] = cat
        it["place"] = {"call": "AddEffect", "category": cat, "id": it.get("id")}
        if not it.get("id"):
            notes.append("no id: Resolve gives an effect's id only through GetEffectsList — run LIBRARY_SCAN through the "
                         "console, then scan again with --from-console")
    if it.get("category") == "ofx" or t in ("ofx-effect", "ofx-generator"):
        it["scriptable"] = "defaults-only"
        why = next((w for rx, w in OFX_MANUAL if re.search(rx, f"{n} {it.get('id') or ''}", re.I)),
                   "OFX parameters are not scriptable (21.1.2): applied with its defaults — set it in the Inspector")
        it["manual"] = why
    elif it.get("published_inputs"):
        it["scriptable"] = "inputs"
    elif t in ("effect",):
        it["scriptable"] = "comp"                    # Effect.GetFusionComp(): its inputs are read on the first use
    else:
        it["scriptable"] = "name"
    if OVERSHOOT_RE.search(str(n or "")):
        it["text_safe"] = False
        notes.append("its name says it overshoots (bounce / elastic / pop): never on text, numbers or UI (house rule C2)")
    it["notes"] = sorted(set(notes))
    return it


# ── sources ──────────────────────────────────────────────────────────────────────────────────────────────────
def _published_from_text(txt: str) -> list | None:
    try:
        import fusion_titles as FT
        d = FT.parse_lua(txt)
        macro = next((v for v in (d.get("Tools") or {}).values() if isinstance(v, dict)
                      and str(v.get("__type", "")).endswith("Operator")), None) if isinstance(d, dict) else None
        if macro is not None:
            out = []
            for k, v in (macro.get("Inputs") or {}).items():
                if isinstance(v, dict) and v.get("__type") == "InstanceInput":
                    out.append({"id": k, "name": v.get("Name"), "source_op": v.get("SourceOp"), "source": v.get("Source")})
            return out
    except (ValueError, IndexError, KeyError, TypeError):
        pass
    out = []
    for m in re.finditer(r"(Input\d+)\s*=\s*InstanceInput\s*\{(.*?)\}", txt or "", re.S):
        row = {"id": m.group(1)}
        for k, f in (("name", "Name"), ("source_op", "SourceOp"), ("source", "Source")):
            h = re.search(f + r'\s*=\s*"([^"]*)"', m.group(2))
            row[k] = h.group(1) if h else None
        out.append(row)
    return out or None


TEMPLATE_KIND = {"titles": "title", "transitions": "transition", "generators": "generator", "effects": "effect"}


def _template_type(parts: list) -> str | None:
    for p in parts:
        if p.lower() in TEMPLATE_KIND:
            return TEMPLATE_KIND[p.lower()]
    return None


def from_folder(root: str) -> list:
    """A Fusion Templates folder read from here: .setting / .comp files and every .setting inside a .drfx."""
    out = []
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root).replace("\\", "/")
            low = f.lower()
            if low.endswith((".setting", ".comp")):
                t = _template_type(rel.split("/")[:-1])
                if not t:
                    continue
                txt = open(full, encoding="utf-8", errors="replace").read(4 << 20) if low.endswith(".setting") else ""
                out.append({"type": t, "name": f.rsplit(".", 1)[0], "path": rel, "source": "folder",
                            "published_inputs": _published_from_text(txt) if txt else None})
            elif low.endswith(".drfx"):
                try:
                    with zipfile.ZipFile(full) as z:
                        for n in sorted(z.namelist()):
                            t = _template_type(n.split("/")[:-1])
                            if n.lower().endswith(".setting") and t:
                                out.append({"type": t, "name": n.split("/")[-1].rsplit(".", 1)[0], "path": f"{rel}::{n}",
                                            "source": f"drfx:{f}",
                                            "published_inputs": _published_from_text(z.read(n).decode("utf-8", "replace"))})
                except (zipfile.BadZipFile, OSError):
                    continue
    return out


def _effect_type(cat: str) -> str:
    return {"fusion": "effect", "ofx": "ofx-effect", "audio": "audio-effect"}.get(str(cat or "").lower(), "effect")


def from_effects(rows: list) -> list:
    """GetEffectsList rows {category, id, name} → items."""
    out = []
    for r in rows or []:
        if not isinstance(r, dict) or not (r.get("name") or r.get("id")):
            continue
        name = r.get("name") or str(r.get("id")).split("/")[-1]
        out.append({"type": _effect_type(r.get("category")), "name": name, "category": str(r.get("category") or "").lower()
                    or None, "id": r.get("id"), "source": "effects-list"})
    return out


def from_console(path: str) -> tuple:
    """The console's LIBRARY_SCAN result (or INVENTORY_TEMPLATES' file) → (items, resolve version)."""
    d = jload(path) or {}
    d = d.get("library") or d                     # the whole run_script result, or its library
    items = []
    for mt, rows in (d.get("effects") or {}).items():
        items += from_effects(rows)
    for t in d.get("templates") or []:
        ty = t.get("type") or {"title": "title", "transition": "transition", "generator": "generator",
                               "effect": "effect"}.get(t.get("kind"))
        if ty:
            items.append({"type": ty, "name": t.get("name"), "path": t.get("path"), "source": "console",
                          "root_kind": t.get("source"), "published_inputs": t.get("published_inputs")})
    for b in d.get("ofx_bundles") or d.get("ofx") or []:
        items.append({"type": "ofx-effect", "name": b, "category": "ofx", "source": "ofx-bundle", "bundle_only": True})
    return items, d.get("resolve")


NAME_HEAD = {"title": "title", "titles": "title", "transition": "transition", "transitions": "transition",
             "generator": "generator", "generators": "generator", "effect": "effect", "effects": "effect",
             "fusion effect": "effect", "fusion effects": "effect", "ofx": "ofx-effect", "openfx": "ofx-effect",
             "open fx": "ofx-effect", "ofx effects": "ofx-effect", "audio": "audio-effect"}


def from_names(path: str) -> list:
    """The owner's own list. JSON: a list of names or {type, name, category?, id?}. Text: one per line, as
    "Titles/Background Reveal", "transition: Smooth Zoom In", or a bare name under a "# Titles" heading."""
    txt = open(path, encoding="utf-8").read()
    out = []
    try:
        j = json.loads(txt)
    except ValueError:
        j = None
    if isinstance(j, list):
        for r in j:
            if isinstance(r, str):
                out.append(_name_line(r, None))
            elif isinstance(r, dict) and (r.get("name") or r.get("id")):
                if r.get("category") and not r.get("type"):
                    out += from_effects([r])
                else:
                    out.append({"type": NAME_HEAD.get(str(r.get("type") or "").lower(), r.get("type")), "name": r.get("name"),
                                "category": r.get("category"), "id": r.get("id"), "source": "names"})
        return [o for o in out if o]
    cur = None
    for raw in txt.splitlines():
        ln = raw.strip()
        if not ln:
            continue
        m = re.match(r"^#+\s*(.+?)\s*:?\s*$", ln)
        if m:
            cur = NAME_HEAD.get(m.group(1).strip().lower(), cur)
            continue
        o = _name_line(re.sub(r"^[-*•]\s*", "", ln), cur)
        if o:
            out.append(o)
    return out


def _name_line(ln: str, cur: str | None) -> dict | None:
    t, name, pack = cur, ln.strip(), None
    m = re.match(r"^\[?([A-Za-z ]+?)\]?\s*[:]\s*(.+)$", name)
    if m and m.group(1).strip().lower() in NAME_HEAD:
        t, name = NAME_HEAD[m.group(1).strip().lower()], m.group(2).strip()
    else:
        parts = [p.strip() for p in re.split(r"\s*/\s*", name) if p.strip()]
        if len(parts) >= 2 and parts[0].lower() in NAME_HEAD:
            t, name = NAME_HEAD[parts[0].lower()], parts[-1]
            pack = parts[1] if len(parts) >= 3 else None
        elif len(parts) >= 2:                                        # "Free Smooth Transitions/Smooth Zoom In"
            pack, name = parts[-2], parts[-1]
    m2 = re.match(r"^(.*?)\s*\((.+)\)\s*$", name)                 # "Background Reveal (JTechWP)"
    if m2:
        name, pack = m2.group(1).strip(), m2.group(2).strip()
    if not name:
        return None
    o = {"type": t, "name": name, "source": "names", "pack": pack}
    if not t:
        import motion_qa
        fam = motion_qa.trans_family(name)
        o["type"] = "transition" if fam in [f for f, _ in motion_qa.TRANS_FAMILIES] else "title"
        o["type_guessed"] = True
    return {k: v for k, v in o.items() if v is not None}


def merge(items: list, prev: dict | None = None) -> list:
    """One row per (type, name): the id, inputs and sources from every source; stars and notes kept from `prev`."""
    by = {}
    for it in items:
        if not it or not it.get("name") or it.get("type") not in TYPES:
            continue
        k = (it["type"], str(it["name"]).strip().lower())
        cur = by.setdefault(k, {"type": it["type"], "name": str(it["name"]).strip(), "sources": []})
        for f in ("category", "id", "path", "pack", "published_inputs", "builtin", "type_guessed", "bundle_only"):
            if it.get(f) not in (None, "", []) and cur.get(f) in (None, "", []):
                cur[f] = it[f]
        if it.get("type_guessed") is not True:
            cur.pop("type_guessed", None) if it.get("source") != "names" else None
        src = it.get("source") or "?"
        if src not in cur["sources"]:
            cur["sources"].append(src)
    # an OFX bundle seen on disk and the same plugin in GetEffectsList: one row
    for k in [k for k, v in by.items() if v.get("bundle_only")]:
        if any(o["type"] == "ofx-effect" and not o.get("bundle_only") and k[1] in o["name"].lower() for o in by.values()):
            by.pop(k)
    stars = {}
    for r in (prev or {}).get("items") or []:
        stars[(r.get("type"), str(r.get("name") or "").lower())] = (r.get("star"), r.get("note"))
    out = []
    for k, v in sorted(by.items(), key=lambda kv: (TYPES.index(kv[0][0]), kv[0][1])):
        st, note = stars.get(k, (None, None))
        if st:
            v["star"] = True
        if note:
            v["note"] = note
        out.append(describe(v))
    return out


def kinds_map(items: list) -> dict:
    """{"<type>/<kind>": [names, best first]}: starred first; a dissolve/dip/smooth-cut's built-in first (the grammar's
    default); then the packs, alphabetically."""
    km = {}
    for it in items:
        t = {"ofx-effect": "effect", "audio-effect": "audio", "ofx-generator": "generator"}.get(it["type"], it["type"])
        for k in it.get("kinds") or []:
            km.setdefault(f"{t}/{k}", []).append(it)
    out = {}
    for key, rows in sorted(km.items()):
        pref = PREFERRED.get(key)
        rows.sort(key=lambda r: (not r.get("star"), r["name"] != pref, bool(r.get("manual")), r["name"].lower()))
        out[key] = [r["name"] for r in rows]
    return out


def build_inventory(sources: list, prev: dict | None = None, resolve_version: str | None = None) -> dict:
    items = []
    for s in sources:
        items += s["items"]
    items += [{"type": "transition", "name": n, "category": "simple", "builtin": True, "source": "builtin"}
              for n in BUILTIN_TRANSITIONS]
    rows = merge(items, prev)
    inv = {"schema": SCHEMA, "resolve": resolve_version or (prev or {}).get("resolve"), "scanned": now(),
           "sources": [{k: v for k, v in s.items() if k != "items"} for s in sources], "items": rows,
           "kinds": kinds_map(rows),
           "manual": [{"name": r["name"], "type": r["type"], "why": r["manual"]} for r in rows if r.get("manual")],
           "unmapped": sorted(r["name"] for r in rows if not r.get("kinds")),
           "how": "star the ones worth using (\"star\": true) — `pick` and `plan` take a starred item first; a kind with "
                  "nothing installed is refused, never improvised"}
    return inv


def studio_root(start: str) -> str | None:
    """The nearest `_studio/` folder up from a path (the production root's studio tier)."""
    p = os.path.abspath(start)
    while True:
        cand = os.path.join(p, "_studio")
        if os.path.isdir(cand):
            return cand
        up = os.path.dirname(p)
        if up == p:
            return None
        p = up


def find_inventory(job: str) -> str | None:
    p = os.path.join(job, JOB_FILE)
    if os.path.isfile(p):
        return p
    st = studio_root(job)
    if st and os.path.isfile(os.path.join(st, STUDIO_FILE)):
        return os.path.join(st, STUDIO_FILE)
    return None


def scan(out: str, from_console=None, folders=(), names=(), effects_json=None) -> dict:
    sources, ver = [], None
    if from_console:
        it, ver = from_console_(from_console)
        sources.append({"kind": "console", "path": from_console, "count": len(it), "items": it})
    for f in folders or ():
        it = from_folder(f)
        sources.append({"kind": "folder", "path": f, "count": len(it), "items": it})
    for n in names or ():
        it = from_names(n)
        sources.append({"kind": "names", "path": n, "count": len(it), "items": it})
    if effects_json:
        it = from_effects(jload(effects_json) or [])
        sources.append({"kind": "effects-json", "path": effects_json, "count": len(it), "items": it})
    if not sources:
        raise SystemExit("error: nothing to scan — --from-console, --folder, --names or --effects-json")
    inv = build_inventory(sources, jload(out), ver)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(inv, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    inv["out"] = out
    return inv


from_console_ = from_console


def item(inv: dict, name: str, type_=None) -> dict | None:
    return next((r for r in inv.get("items") or [] if r["name"].lower() == str(name).lower()
                 and (type_ is None or r["type"] == type_ or (type_ == "effect" and r["type"] in ("ofx-effect", "effect")))), None)


def pick(inv: dict, kind: str, type_: str | None = None) -> dict | None:
    """The item to use for a kind: "title/lower-third", "transition/whip", or a bare kind (transition, then effect,
    then title)."""
    km = inv.get("kinds") or {}
    keys = [kind] if "/" in kind else ([f"{type_}/{kind}"] if type_ else [f"transition/{kind}", f"effect/{kind}",
                                                                          f"title/{kind}", f"generator/{kind}"])
    for k in keys:
        names = km.get(k)
        if names:
            t = k.split("/")[0]
            return item(inv, names[0], {"effect": "effect", "audio": "audio-effect"}.get(t, t))
    return None


# ── a plan of kinds → what the console applies ───────────────────────────────────────────────────────────────
def resolve_plan(job: str, plan: dict, inv: dict | None) -> tuple:
    """(TRANSITION_PLAN rows, EFFECT_PLAN rows, problems, notes) from a plan of kinds or names."""
    P, N, TR, EF = [], [], [], []
    if inv is None:
        return TR, EF, ["no resolve-library.json for this job or its studio — `resolve_library.py scan` first"], N
    card = jload(os.path.join(job, "00-brief", "TITLE-CARD.json")) or {}
    accents = 0
    for i, r in enumerate(plan.get("transitions") or [], start=1):
        rid = r.get("id") or f"J{i}"
        it = item(inv, r["type"], "transition") if r.get("type") else pick(inv, r.get("kind") or "", "transition")
        if it is None:
            P.append(f"{rid}: no installed transition for {r.get('type') or r.get('kind')!r} — install a pack, star one, or "
                     f"use a built-in (Cross Dissolve); nothing is improvised")
            continue
        fam = (it.get("kinds") or ["?"])[0]
        if fam not in ("dissolve", "smooth-cut"):
            accents += 1
        row = {"id": rid, "track": r.get("track") or "Picture", "at_s": float(r["at_s"]), "type": it["name"],
               "category": it.get("category") or "fusion", "position": r.get("position") or "end",
               "alignment": r.get("alignment") or "center", "family": fam}
        if r.get("duration"):
            row["duration"] = int(r["duration"])
        if it.get("text_safe") is False:
            N.append(f"{rid}: {it['name']} overshoots by its name — fine between pictures, never across a title (C2)")
        TR.append(row)
    mx = int(((card.get("transitions") or {}).get("max_accents")) or 2)
    if accents > mx:
        P.append(f"{accents} accent transitions planned; the title card allows {mx} (house rule C5: the hard cut governs) "
                 f"— keep the strongest {mx}")
    for i, r in enumerate(plan.get("effects") or [], start=1):
        rid = r.get("id") or f"E{i}"
        it = item(inv, r["name"], "effect") if r.get("name") else pick(inv, r.get("kind") or "", "effect")
        if it is None:
            P.append(f"{rid}: no installed effect for {r.get('name') or r.get('kind')!r}")
            continue
        on_text = str(r.get("item") or "").startswith("cine:")
        if on_text and it.get("text_safe") is False:
            P.append(f"{rid}: {it['name']} overshoots by its name and {r.get('item')} is a title — no overshoot on text (C2)")
            continue
        if not it.get("id"):
            P.append(f"{rid}: {it['name']} has no effect id (seen in a folder or a list, not in GetEffectsList) — run the "
                     f"console's LIBRARY_SCAN, then scan --from-console")
            continue
        row = {"id": rid, "item": r["item"], "category": it.get("category") or "fusion", "effect_id": it["id"],
               "name": it["name"], "inputs": r.get("inputs") or {}}
        if it.get("manual"):
            row["manual"] = it["manual"]
            row["inputs"] = {}
            N.append(f"{rid}: {it['name']} on {r['item']} — MANUAL: {it['manual']}")
            if r.get("inputs"):
                N.append(f"{rid}: the inputs asked for ({', '.join(r['inputs'])}) cannot be set on an OFX effect by script")
        elif r.get("inputs") and it.get("published_inputs"):
            names = {str(p.get("name") or "").lower(): p for p in it["published_inputs"]}
            ids = {str(p.get("id") or ""): p for p in it["published_inputs"]}
            fixed = {}
            for k, v in r["inputs"].items():
                p = names.get(str(k).lower()) or ids.get(k)
                fixed[(p or {}).get("source") or k] = v
            row["inputs"] = fixed
        EF.append(row)
    return TR, EF, P, N


def console_copy(job: str, scan_: bool = False, plan_p: str | None = None, host_job: str | None = None) -> tuple:
    host = (host_job or os.path.abspath(job)).rstrip("/\\")
    src = open(CONSOLE, encoding="utf-8").read()
    reps = [("\nADD_BEAT_MARKERS = True", "\nADD_BEAT_MARKERS = False"),
            ("\nENSURE_BROLL_TRACK = True", "\nENSURE_BROLL_TRACK = False"),
            ("\nENSURE_AUDIO_LANES = True", "\nENSURE_AUDIO_LANES = False")]
    P, N, TR, EF = [], [], [], []
    if scan_:
        reps += [("\nLIBRARY_SCAN = False", "\nLIBRARY_SCAN = True"),
                 ('LIBRARY_PATH = r"REPLACE-WITH-A-FOLDER/resolve-library.raw.json"',
                  f'LIBRARY_PATH = r"{host}/07-edit/resolve-library.raw.json"')]
    if plan_p:
        plan = jload(plan_p)
        if not isinstance(plan, dict):
            raise SystemExit(f"error: {plan_p} is not a plan ({{transitions: [...], effects: [...]}})")
        inv_p = find_inventory(job)
        TR, EF, P, N = resolve_plan(job, plan, jload(inv_p) if inv_p else None)
        if P:
            raise SystemExit("REFUSED:\n  - " + "\n  - ".join(P))
        if TR:
            reps += [("TRANSITION_PLAN = []  # __LIBRARY_TRANSITIONS__", "TRANSITION_PLAN = " + repr(TR) + "  # __LIBRARY_TRANSITIONS__"),
                     ("\nAPPLY_TRANSITIONS = False", "\nAPPLY_TRANSITIONS = True")]
        if EF:
            reps += [("EFFECT_PLAN = []  # __LIBRARY_EFFECTS__", "EFFECT_PLAN = " + repr(EF) + "  # __LIBRARY_EFFECTS__"),
                     ("\nAPPLY_EFFECTS = False", "\nAPPLY_EFFECTS = True")]
    if not (scan_ or TR or EF):
        raise SystemExit("error: nothing to do — --scan and/or --plan")
    for old, new in reps:
        if old not in src:
            raise RuntimeError(f"resolve-production-console.py no longer contains {old!r} — update resolve_library.console_copy()")
        src = src.replace(old, new, 1)
    compile(src, CONSOLE_COPY, "exec")
    out = os.path.join(job, "07-edit", CONSOLE_COPY)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(src)
    return out, TR, EF, N


# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────────────
LIVE_NAMES = """# Titles
Background Reveal
Background Reveal Lower Third
Titles/JTechWP/Kinetic Headline 03
Titles/JTechWP/Subscribe Button Pop
Titles/Video Editor Studio/Clean Lower Third
# Transitions
Free Smooth Transitions/Smooth Zoom In
Smooth Slide Left (Free Smooth Transitions)
transition: Smooth Whip Pan
transition: Light Leak 02 (JTechWP)
transition: Glitch Burst (Video Editor Studio)
# Generators
Krokodove/Generate
"""
LIVE_EFFECTS = [  # Resolve 21.1.2 GetEffectsList("video"), read live 2026-10-29 (abridged, as the caller reported it)
    {"category": "fusion", "id": "Fusion/Effects/Krokodove/Bevel", "name": "Bevel"},
    {"category": "fusion", "id": "Fusion/Effects/Krokodove/Extrude", "name": "Extrude"},
    {"category": "fusion", "id": "Fusion/Effects/Krokodove/Spherize", "name": "Spherize"},
    {"category": "fusion", "id": "Fusion/Effects/DVE", "name": "DVE"},
    {"category": "fusion", "id": "Fusion/Effects/Digital Glitch", "name": "Digital Glitch"},
    {"category": "fusion", "id": "Fusion/Effects/Paper Edge", "name": "Paper Edge"},
    {"category": "fusion", "id": "Fusion/Effects/Pen Stroke Arrow", "name": "Pen Stroke Arrow"},
    {"category": "fusion", "id": "Fusion/Effects/Video Call", "name": "Video Call"},
    {"category": "fusion", "id": "Fusion/Effects/Drone Overlay", "name": "Drone Overlay"},
    {"category": "fusion", "id": "Fusion/Effects/Video Editor Studio Free Starter Pack/Animation In & Out", "name": "Animation In & Out"},
    {"category": "fusion", "id": "Fusion/Effects/Video Editor Studio Free Starter Pack/Continuous Zoom", "name": "Continuous Zoom"},
    {"category": "fusion", "id": "Fusion/Effects/Video Editor Studio Free Starter Pack/Glass Effect", "name": "Glass Effect"},
    {"category": "fusion", "id": "Fusion/Effects/Video Editor Studio Free Starter Pack/Shadow Glow And Background", "name": "Shadow Glow And Background"},
    {"category": "fusion", "id": "Fusion/Effects/Video Editor Studio Free Starter Pack/Phone Effect", "name": "Phone Effect"},
    {"category": "ofx", "id": "Open FX/MrAlexTech/MagicAnimate Free", "name": "MagicAnimate Free"},
    {"category": "ofx", "id": "Open FX/CineDream/CineDream Full Editor", "name": "CineDream Full Editor"},
    {"category": "ofx", "id": "Open FX/Higgsfield/Higgsfield Color Match", "name": "Higgsfield Color Match"},
]


def selftest() -> int:
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  — {str(info)[:1500]}"))
        ok = ok and bool(cond)
    with tempfile.TemporaryDirectory() as td:
        names = os.path.join(td, "packs.txt")
        open(names, "w").write(LIVE_NAMES)
        eff = os.path.join(td, "effects.json")
        json.dump(LIVE_EFFECTS, open(eff, "w"))
        studio = os.path.join(td, "videos", "_studio")
        job = os.path.join(td, "videos", "clients", "acme", "04-projects", "acme-01001-five-spots")
        for d in (studio, os.path.join(job, "07-edit"), os.path.join(job, "00-brief")):
            os.makedirs(d, exist_ok=True)
        out = os.path.join(studio, STUDIO_FILE)
        inv = scan(out, names=[names], effects_json=eff)
        K = inv["kinds"]
        it = {r["name"]: r for r in inv["items"]}
        check("the owner's list and the effects list: titles, transitions, generators and effects, each with its pack",
              it["Background Reveal"]["type"] == "title" and it["Smooth Zoom In"]["pack"] == "Free Smooth Transitions"
              and it["Kinetic Headline 03"]["pack"] == "JTechWP" and it["Bevel"]["pack"] == "Krokodove"
              and it["MagicAnimate Free"]["pack"] == "MrAlexTech MagicAnimate" and it["Generate"]["type"] == "generator",
              {k: (v["type"], v["pack"]) for k, v in it.items()})
        check("kinds: 'Background Reveal Lower Third' is a lower third, 'Background Reveal' a super; a kinetic headline is a hero; "
              "the subscribe button is social and overshoots by its name (C2)",
              "Background Reveal Lower Third" in K.get("title/lower-third", []) and "Background Reveal" in K.get("title/super", [])
              and "Kinetic Headline 03" in K.get("title/hero", []) and "Subscribe Button Pop" in K.get("title/social", [])
              and it["Subscribe Button Pop"].get("text_safe") is False
              and "Background Reveal Lower Third" not in K.get("title/hero", []), K)
        check("transitions by family: zoom, push (slide), whip, light-leak, glitch; the dissolve's first choice is Resolve's "
              "Cross Dissolve",
              K.get("transition/zoom") == ["Smooth Zoom In"] and "Smooth Slide Left" in K.get("transition/push", [])
              and "Smooth Whip Pan" in K.get("transition/whip", []) and K.get("transition/light-leak") == ["Light Leak 02"]
              and K.get("transition/glitch") == ["Glitch Burst"] and K.get("transition/dissolve", [""])[0] == "Cross Dissolve", K)
        check("effects: animate-in-out is the Fusion pack's (scriptable through its comp) before MagicAnimate (OFX: manual); "
              "3d-text is Krokodove; color-match and grade are manual",
              K.get("effect/animate-in-out") == ["Animation In & Out", "MagicAnimate Free"]
              and it["Animation In & Out"]["scriptable"] == "comp" and it["MagicAnimate Free"]["scriptable"] == "defaults-only"
              and "In / Mid / Out" in it["MagicAnimate Free"]["manual"] and set(K.get("effect/3d-text", [])) == {"Bevel", "Extrude", "Spherize"}
              and it["Higgsfield Color Match"].get("manual") and it["CineDream Full Editor"].get("manual")
              and {m["name"] for m in inv["manual"]} == {"MagicAnimate Free", "CineDream Full Editor", "Higgsfield Color Match"}, K)
        check("how each is placed: a title by name, a transition through AddTransition (fusion, or simple for a built-in), "
              "an effect through AddEffect with its id",
              it["Background Reveal"]["place"] == {"call": "InsertFusionTitleIntoTimeline", "name": "Background Reveal"}
              and it["Smooth Zoom In"]["place"]["category"] == "fusion" and it["Cross Dissolve"]["place"]["category"] == "simple"
              and it["Bevel"]["place"] == {"call": "AddEffect", "category": "fusion", "id": "Fusion/Effects/Krokodove/Bevel"},
              (it["Background Reveal"]["place"], it["Bevel"]["place"]))
        # a templates folder, with a pack's macro and its published inputs, and a .drfx
        troot = os.path.join(td, "Templates")
        os.makedirs(os.path.join(troot, "Edit", "Titles", "JTechWP"))
        open(os.path.join(troot, "Edit", "Titles", "JTechWP", "Background Reveal.setting"), "w").write(
            '{ Tools = ordered() { BackgroundReveal = MacroOperator { Inputs = ordered() { Input1 = InstanceInput { '
            'SourceOp = "Text1", Source = "StyledText", Name = "Text", }, Input2 = InstanceInput { SourceOp = "Bg", '
            'Source = "TopLeftRed", Name = "Background Red", } }, Tools = ordered() { Text1 = TextPlus { Inputs = { } } } } } }')
        with zipfile.ZipFile(os.path.join(troot, "Free Smooth Transitions.drfx"), "w") as z:
            z.writestr("Edit/Transitions/Smooth/Smooth Zoom Out.setting", "{ Tools = ordered() { } }")
        inv2 = scan(out, folders=[troot], names=[names], effects_json=eff)
        it2 = {r["name"]: r for r in inv2["items"]}
        br = it2["Background Reveal"]
        check("a folder scan reads a pack's macro: its published inputs (id, name, the tool and input behind it), its pack "
              "from the folder; a .drfx's transitions by name",
              [p["name"] for p in br.get("published_inputs") or []] == ["Text", "Background Red"] and br["scriptable"] == "inputs"
              and br["pack"] == "JTechWP" and "Smooth Zoom Out" in inv2["kinds"].get("transition/zoom", [])
              and sorted(br["sources"]) == ["folder", "names"], br)
        # the console's own scan result merges: an effect id joins the name the owner listed
        res = {"library": {"resolve": "21.1.2", "effects": {"video": LIVE_EFFECTS[:2], "audio": []},
                           "templates": [{"kind": "title", "name": "Background Reveal Lower Third", "source": "user",
                                          "path": "Edit/Titles/Background Reveal Lower Third.setting",
                                          "published_inputs": [{"id": "Input1", "name": "Name", "source_op": "T", "source": "StyledText"}]}]}}
        rp = os.path.join(td, "console-result.json")
        json.dump(res, open(rp, "w"))
        # stars survive a re-scan
        cur = json.load(open(out))
        for r in cur["items"]:
            if r["name"] == "Smooth Slide Left":
                r["star"] = True
                r["note"] = "the brand's push"
        json.dump(cur, open(out, "w"))
        inv3 = scan(out, from_console=rp, folders=[troot], names=[names], effects_json=eff)
        it3 = {r["name"]: r for r in inv3["items"]}
        check("--from-console: the console's LIBRARY_SCAN merges (its version, a title's published inputs)",
              inv3["resolve"] == "21.1.2" and [p["name"] for p in it3["Background Reveal Lower Third"]["published_inputs"]] == ["Name"]
              and "console" in it3["Background Reveal Lower Third"]["sources"], it3["Background Reveal Lower Third"])
        check("stars and notes are kept across a re-scan, and a starred item is picked first",
              it3["Smooth Slide Left"].get("star") and it3["Smooth Slide Left"].get("note") == "the brand's push"
              and pick(inv3, "push")["name"] == "Smooth Slide Left", (it3["Smooth Slide Left"], inv3["kinds"].get("transition/push")))
        check("pick: a bare kind looks in transitions, then effects, then titles",
              pick(inv3, "zoom")["type"] == "transition" and pick(inv3, "lower-third")["name"] == "Background Reveal Lower Third"
              and pick(inv3, "animate-in-out")["name"] == "Animation In & Out" and pick(inv3, "nothing-like-this") is None)
        # the plan
        json.dump({"transitions": {"max_accents": 2}}, open(os.path.join(job, "00-brief", "TITLE-CARD.json"), "w"))
        check("find_inventory: a job with none of its own uses the studio's (_studio/resolve-library.json)",
              find_inventory(job) == out, find_inventory(job))
        plan = {"transitions": [{"id": "J1", "at_s": 4.0, "kind": "dissolve", "duration": 12},
                                {"id": "J2", "at_s": 9.5, "kind": "zoom"}],
                "effects": [{"id": "E1", "item": "S3_kling_v1.mp4", "kind": "continuous-zoom", "inputs": {"Size": 1.06}},
                            {"id": "E2", "item": "cine:T1", "name": "MagicAnimate Free", "inputs": {"Animation": "Fade Up"}}]}
        TR, EF, P, N = resolve_plan(job, plan, inv3)
        check("a plan of kinds resolves to installed names: the dissolve to Cross Dissolve (simple), the zoom to the pack's "
              "(fusion), the zoom effect with its id and inputs",
              not P and TR[0]["type"] == "Cross Dissolve" and TR[0]["category"] == "simple" and TR[0]["duration"] == 12
              and TR[1]["type"] in ("Smooth Zoom In", "Smooth Zoom Out") and TR[1]["category"] == "fusion"
              and EF[0]["effect_id"].endswith("Continuous Zoom") and EF[0]["inputs"] == {"Size": 1.06}, (TR, EF, P))
        check("MagicAnimate on a title: applied with its defaults, its inputs dropped, and flagged MANUAL (In / Mid / Out)",
              EF[1]["category"] == "ofx" and EF[1]["inputs"] == {} and "In / Mid / Out" in EF[1]["manual"]
              and any("MANUAL" in x for x in N) and any("cannot be set on an OFX effect" in x for x in N), (EF[1], N))
        bad = {"transitions": [{"at_s": 1, "kind": "whip"}, {"at_s": 2, "kind": "zoom"}, {"at_s": 3, "kind": "glitch"},
                               {"at_s": 4, "kind": "iris"}],
               "effects": [{"item": "cine:T2", "name": "Subscribe Button Pop"}, {"item": "S1.mp4", "name": "Background Reveal"}]}
        inv3["items"].append(describe({"type": "effect", "name": "Pop Bounce In", "category": "fusion", "id": "Fusion/Effects/X/Pop Bounce In"}))
        inv3["items"].append(describe({"type": "effect", "name": "Folder Glow", "category": "fusion", "path": "Edit/Effects/Folder Glow.setting"}))
        bad["effects"] = [{"item": "cine:T2", "name": "Pop Bounce In"}, {"item": "S1.mp4", "name": "Folder Glow"}]
        TR, EF, P, N = resolve_plan(job, bad, inv3)
        check("refusals: a kind nothing installed provides; more accents than the card allows (C5); an overshooting effect "
              "on a title (C2); an effect with no id",
              any("no installed transition for 'iris'" in x for x in P) and any("accent transitions planned" in x for x in P)
              and any("Pop Bounce In" in x and "C2" in x for x in P) and any("no effect id" in x for x in P), P)
        pp = os.path.join(job, PLAN_FILE)
        json.dump(plan, open(pp, "w"))
        cp, TR, EF, N = console_copy(job, scan_=True, plan_p=pp, host_job="/Users/someone/videos/acme-01001-five-spots")
        src = open(cp, encoding="utf-8").read()
        check("console copy: LIBRARY_SCAN on with its path on Resolve's machine; the resolved plans spliced in and switched on",
              "\nLIBRARY_SCAN = True" in src and "\nAPPLY_TRANSITIONS = True" in src and "\nAPPLY_EFFECTS = True" in src
              and 'LIBRARY_PATH = r"/Users/someone/videos/acme-01001-five-spots/07-edit/resolve-library.raw.json"' in src
              and "'type': 'Cross Dissolve'" in src and "MagicAnimate Free" in src, cp)
        json.dump(bad, open(pp, "w"))
        try:
            console_copy(job, plan_p=pp)
            refused = False
        except SystemExit as e:
            refused = "REFUSED" in str(e)
        check("a plan with refusals writes no console copy", refused)
    print("-" * 60)
    print("selftest OK — the installed library from the owner's list, the effects list, a templates folder and the console's "
          "scan: each item's pack, kinds, published inputs and the call that places it; titles to lower-third / super / hero, "
          "transitions to their families, effects to theirs; OFX (MagicAnimate, CineDream, Color Match) applied with defaults "
          "and flagged manual; stars kept; a plan of kinds resolved, and refused where nothing is installed, the card's accents "
          "run out, or an overshoot would land on text" if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("scan")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--job"); g.add_argument("--studio"); g.add_argument("--out")
    s.add_argument("--from-console"); s.add_argument("--folder", action="append", default=[])
    s.add_argument("--names", action="append", default=[]); s.add_argument("--effects-json")
    k = sub.add_parser("kinds"); k.add_argument("inventory")
    p = sub.add_parser("pick"); p.add_argument("inventory"); p.add_argument("--kind", required=True); p.add_argument("--type")
    pl = sub.add_parser("plan"); pl.add_argument("job"); pl.add_argument("--plan")
    c = sub.add_parser("console"); c.add_argument("job"); c.add_argument("--scan", action="store_true")
    c.add_argument("--plan"); c.add_argument("--host-job")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "scan":
        out = a.out or (os.path.join(a.job, JOB_FILE) if a.job else os.path.join(a.studio, STUDIO_FILE))
        inv = scan(out, a.from_console, a.folder, a.names, a.effects_json)
        by = {}
        for r in inv["items"]:
            by[r["type"]] = by.get(r["type"], 0) + 1
        print(f"wrote {out}: " + ", ".join(f"{v} {k}" for k, v in sorted(by.items())) + f"; {len(inv['kinds'])} kinds mapped, "
              f"{len(inv['manual'])} manual, {len(inv['unmapped'])} unmapped")
        for m in inv["manual"]:
            print(f"  ✋ {m['name']}: {m['why']}")
        return 0
    if a.cmd == "kinds":
        inv = jload(a.inventory) or {}
        for key, names in (inv.get("kinds") or {}).items():
            print(f"  {key:<28} " + " · ".join(names[:6]) + (" …" if len(names) > 6 else ""))
        for m in inv.get("manual") or []:
            print(f"  ✋ {m['name']}: {m['why']}")
        if inv.get("unmapped"):
            print("  unmapped: " + ", ".join(inv["unmapped"]))
        return 0
    if a.cmd == "pick":
        it = pick(jload(a.inventory) or {}, a.kind, a.type)
        if not it:
            print(f"nothing installed for {a.kind}")
            return 1
        print(json.dumps({k: it.get(k) for k in ("type", "name", "pack", "category", "id", "place", "scriptable", "manual",
                                                  "published_inputs") if it.get(k) is not None}, indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "plan":
        inv_p = find_inventory(a.job)
        TR, EF, P, N = resolve_plan(a.job, jload(a.plan or os.path.join(a.job, PLAN_FILE)) or {}, jload(inv_p) if inv_p else None)
        for r in TR:
            print(f"  transition {r['id']}: {r['type']} ({r['category']}) at {r['at_s']:.2f} s")
        for r in EF:
            print(f"  effect {r['id']}: {r['name']} ({r['category']}) on {r['item']}" + (" — MANUAL" if r.get("manual") else ""))
        for x in N:
            print(f"  note: {x}")
        for x in P:
            print(f"  ✗ {x}")
        return 1 if P else 0
    if a.cmd == "console":
        out, TR, EF, N = console_copy(a.job, a.scan, a.plan, a.host_job)
        print(f"wrote {out}: {'LIBRARY_SCAN, ' if a.scan else ''}{len(TR)} transition(s), {len(EF)} effect(s)")
        for x in N:
            print(f"  note: {x}")
        print("Run it in Resolve (run_script; LIBRARY_SCAN's folder half needs Workspace ▸ Console or run_script_unsafe). "
              "A row that did not apply is reported, never worked around.")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
