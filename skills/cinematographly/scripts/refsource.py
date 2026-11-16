#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""refsource.py — the reference plan goes shopping.

The gap this closes: references used to be sourced by whoever remembered to, with search terms
invented on the spot, and judged after the render. This script makes sourcing a PRE-PRODUCTION step
driven by the shot list itself — the prompt declares what it needs, the brief turns that into a
Pixabay search derived from the prompt's own words, the search returns CANDIDATES, a human picks,
and only the pick gets written back into the prompt.

  refsource.py brief   <prompts-dir> [--json]        every unsourced slot → a search, derived from
                                                     the prompt that needs it. No network.
  refsource.py fill    <prompts-dir> [--execute]     run those searches; download N candidates per
                       [--per-gap N] [--refresh]     gap into _reference/_candidates/. Without
                                                     --execute it prints the commands and stops.
  refsource.py candidates <prompts-dir>              what is waiting for a decision — the lookbook.
  refsource.py adopt   <prompts-dir> --shot S3       the human's pick. Moves the file into
                       --what wardrobe --pick FILE   _reference/<attr>/, rewrites the ref line,
                       [--use reference-only]        and refuses an uncleared asset that is not
                                                     explicitly marked reference-only.
  refsource.py status  <prompts-dir> [--json]        gaps · candidates waiting · adopted · cleared.
  refsource.py --selftest                            offline; no network, no key.

WHAT THIS SCRIPT WILL NOT DO
  - It will not choose. `fill` downloads candidates; `adopt` takes one file path that a human named.
    Auto-picking the first hit is how you get a stock photo nobody looked at in a delivered frame.
  - It will not clear an asset. `provenance.py record` answers the §5 blockers; adopt only checks
    that somebody did.
  - It will not source a voice. The Pixabay API serves images and video; audio is not an endpoint,
    so a `what: voice` slot is reported NOT SOURCEABLE HERE rather than quietly skipped.

Reading: references/stock-sourcing.md (§5 blockers, §9 provenance) · references/prompting-craft.md
§6b (reference the nouns, prompt the verbs) · references/preproduction-research.md (the look comes
before the concept).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import prompt_lint as PL              # noqa: E402  (plan_rows, split_front, blocks_of, REF_ATTRS)
import provenance as PV               # noqa: E402  (find_sidecar — the ONE sidecar resolver)

CANDIDATES_DIR = os.path.join("_reference", "_candidates")
LOG_NAME = "_refsource.json"
PER_GAP_DEFAULT = 6
MAX_QUERY_CHARS = 100                 # the API's own cap on q
MAX_TERMS = 4

# --- which blocks of the prompt describe which attribute ----------------------------------------
# The search terms come from the shot that needs the reference. That is the whole point: a query
# invented in the search box describes a mood; a query lifted from [ENVIRONMENT] describes the set.
ATTR_BLOCKS = {
    "character":   ("SUBJECT", "CHARACTER"),
    "wardrobe":    ("SUBJECT", "CHARACTER"),
    "prop":        ("SUBJECT", "ENVIRONMENT"),
    "environment": ("ENVIRONMENT", "SETTING", "LOCATION", "START FRAME"),
    "light":       ("LIGHTING", "LIGHTING/MOOD", "ENVIRONMENT"),
    "palette":     ("COLORS", "STYLE", "ENVIRONMENT"),
    "motion":      ("MOTION", "_lead", "SUBJECT"),
    "style":       ("STYLE",),
    "voice":       (),
}
# Attributes whose reference is a moving picture.
VIDEO_ATTRS = {"motion"}
# Attributes Pixabay cannot serve through the API at all.
UNSOURCEABLE = {"voice"}

# Words that carry no search signal. Camera/lighting jargon is deliberately included: "50mm",
# "5200K" and "eye level" describe how YOU will shoot it, not what to search for.
STOP = set("""
a an the and or but of to in on at for with from by as is are was were be been being this that these
those it its his her their our your my he she they we you i not no very really quite just then than
so such into onto over under above below near far up down out off again more most some any each
every all both few other another same own hold holds holding stands standing sits sitting shot frame
camera lens angle level eye high low wide close medium mid full body view shows showing seen visible
behind front back left right side centre center top bottom edge corner across along around through
during while when where which who whom whose what how why second seconds frames fps mm kelvin
degrees warm cool soft hard key fill rim practical source quality light lighting subject environment
style setting location colors colour color palette motion beat state face gaze suppress verbatim
exact exactly slight slightly gently softly slowly quickly barely almost roughly approximately
slides slide walks walk turns turn reaches reach lifts lift pours pour picks pick sets set opens
open closes close moves move looks look leans lean steps step pulls pull pushes push carries carry
places place puts put takes take gives give
""".split())

UNIT_RE = re.compile(r"^\d+(\.\d+)?(mm|k|s|fps|f|%|:\d+)?$", re.I)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")

# Attribute → the clearance risk you should already know before you search. This is the thing that
# used to be discovered after the render.
ATTR_RISK = {
    "character": ("A stock face is somebody's face. It cannot BE your hero in delivered footage — "
                  "expect `use: reference-only`, or generate the character and let the stock carry "
                  "wardrobe or light instead (stock-sourcing.md §5, recognisable face)."),
    "prop": ("Packaging, labels and devices carry trademarks. Search for the generic object, and "
             "plan to keep any mark out of frame or off the reference (§5, trademark)."),
    "environment": ("A distinctive building or interior can be a property release problem. Prefer "
                    "generic rooms and unremarkable exteriors (§5, distinctive property)."),
    "style": ("Do not search by a living artist, photographer or film's name — the reference has to "
              "be a picture, not an attribution (prompting-craft.md, style-by-name)."),
}


# ------------------------------------------------------------------------------------- utilities
def read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def job_root_of(folder: str) -> str:
    return PL._job_root_of(folder)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "x"


def aspect_shape(aspect: str) -> str:
    """'9:16' → vertical, '16:9' → horizontal, anything square-ish or unknown → all."""
    m = re.match(r"^\s*(\d+)\s*[:x/]\s*(\d+)\s*$", str(aspect or ""))
    if not m:
        return "all"
    w, h = int(m.group(1)), int(m.group(2))
    if not w or not h:
        return "all"
    if h > w * 1.15:
        return "vertical"
    if w > h * 1.15:
        return "horizontal"
    return "all"


def terms_from(text: str, what: str, keep_order: bool = False) -> list:
    """Search terms lifted from the prompt's own words.

    `keep_order` is for a human's `need:` — it is a phrase they chose, and Pixabay's relevance is
    sensitive to adjacency, so reordering it makes the query worse. Verified live 2026-09-06:
    "small tiled bakery kitchen daylight window" reordered to "kitchen window small tiled" returned
    tomatoes and a stained-glass church window.

    Otherwise the on-attribute vocabulary leads — the words REF_ATTRS says belong to this attribute
    are the ones that actually name the thing being referenced."""
    vocab = [w for w in PL.REF_ATTRS.get(what, []) if " " not in w and not w.startswith("#")]
    words, seen = [], set()
    for m in WORD_RE.finditer(text):
        w = m.group(0).lower().strip("-'")
        if w in STOP or UNIT_RE.match(w) or len(w) < 3 or w in seen:
            continue
        seen.add(w)
        words.append(w)
    if keep_order:
        out = words[:MAX_TERMS]
    else:
        on_attr = [w for w in words if any(w == v or w.startswith(v) for v in vocab)]
        rest = [w for w in words if w not in on_attr]
        out = (on_attr + rest)[:MAX_TERMS]
    q = " ".join(out)
    while len(q) > MAX_QUERY_CHARS and out:
        out.pop()
        q = " ".join(out)
    return out


def on_attribute(text: str, what: str) -> list:
    """The subset of `terms_from` that actually names the attribute. Empty means the prompt never
    says what this reference is OF — the query will be generic, and the brief says so."""
    vocab = [w for w in PL.REF_ATTRS.get(what, []) if " " not in w and not w.startswith("#")]
    return [w for w in terms_from(text, what)
            if any(w == v or w.startswith(v) for v in vocab)]


# ---------------------------------------------------------------------------------------- briefs
def briefs(folder: str, job_root: str | None = None) -> list:
    """One brief per unsourced slot: what to search for, where it came from, what it will cost you
    at clearance, and the exact command that fetches candidates."""
    rows = PL.plan_rows(folder, job_root)
    base = job_root or job_root_of(folder)
    out = []
    bodies: dict = {}
    for r in rows:
        if r["state"] != "gap":
            continue
        what = r["what"]
        f = r["prompt"]
        if f not in bodies:
            fm, body = PL.split_front(read(f))
            bodies[f] = (fm, PL.blocks_of(body))
        fm, bl = bodies[f]
        # the query: an explicit `need:` is the director's own words and always wins.
        if r["need"]:
            terms = terms_from(r["need"], what, keep_order=True) or r["need"].split()[:MAX_TERMS]
            origin = "need:"
        else:
            src_text = " ".join(bl.get(b, "") for b in ATTR_BLOCKS.get(what, ()))
            terms = terms_from(src_text, what)
            origin = "+".join(b for b in ATTR_BLOCKS.get(what, ()) if bl.get(b)) or "(no block)"
        klass = "video" if (what in VIDEO_ATTRS or r["role"] in PL.VIDEO_ROLES) else "image"
        shape = aspect_shape(fm.get("aspect"))
        b = {
            "shot": r["shot"], "what": what, "role": r["role"], "prompt": f,
            "query": " ".join(terms), "terms": terms, "query_from": origin,
            "type": klass, "shape": shape,
            "dest": os.path.join(base, CANDIDATES_DIR, f"{slug(r['shot'])}-{slug(what)}"),
            "risk": ATTR_RISK.get(what, ""),
            "sourceable": what not in UNSOURCEABLE,
            "warnings": [],
        }
        if not b["sourceable"]:
            b["warnings"].append(
                f"Pixabay's API serves images and video only — a `{what}` reference does not come "
                f"from here. Cast it, record it, or licence it, then `provenance.py record` it.")
        if len(terms) < 2:
            b["warnings"].append(
                f"only {len(terms)} usable search term(s) from {origin} — the prompt is too vague "
                f"to shop from. Write the slot's `need:` explicitly, or make the block concrete.")
        elif b["sourceable"] and not r["need"] and not on_attribute(src_text, what):
            b["warnings"].append(
                f"no {what} words anywhere in {origin} — this query is whatever the shot happens to "
                f"say, not a description of the {what}. Write `need:` on this slot; a generic query "
                f"returns a generic picture and the slot was supposed to carry one specific thing.")
        out.append(b)
    return out


def search_argv(b: dict, per_gap: int) -> list:
    """The pixabay_search.py command this brief becomes. Printed for a dry run, used for real."""
    argv = ["pixabay_search.py", "-q", b["query"], "--type", b["type"],
            "--per-page", str(max(3, per_gap * 2)), "--safesearch"]
    if b["type"] == "image":
        argv += ["--image-type", "photo"]
        if b["shape"] != "all":
            argv += ["--orientation", b["shape"]]
    else:
        if b["shape"] == "vertical":
            argv += ["--vertical"]
    argv += ["--download", b["dest"]]
    return argv


def cmd_brief(a) -> int:
    bs = briefs(a.folder, a.job_root)
    if a.json:
        json.dump({"folder": a.folder, "briefs": bs}, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0 if not bs else 1
    if not bs:
        print(f"no unsourced references in {os.path.relpath(a.folder)} — the plan is complete.")
        return 0
    print(f"SOURCING BRIEF — {len(bs)} unsourced slot(s) in {os.path.relpath(a.folder)}\n")
    for b in bs:
        head = f"  {b['shot']} · {b['what']}"
        print(f"{head}\n  {'-' * (len(head) + 2)}")
        print(f"    query      {b['query'] or '(nothing usable)'}   [from {b['query_from']}]")
        print(f"    shape      {b['type']}, {b['shape']}")
        print(f"    lands in   {os.path.relpath(b['dest'])}")
        if b["risk"]:
            print(f"    clearance  {b['risk']}")
        for w in b["warnings"]:
            print(f"    ⛔ {w}")
        if b["sourceable"] and b["query"]:
            print(f"    run        {' '.join(_q(x) for x in search_argv(b, PER_GAP_DEFAULT))}")
        print()
    print("`refsource.py fill <folder> --execute` runs all of them and downloads candidates with a "
          "provenance sidecar each. Nothing is written into a prompt until you `adopt` a pick.")
    return 1


def _q(s: str) -> str:
    return s if re.match(r"^[A-Za-z0-9_./:=-]+$", s) else f'"{s}"'


# --- the relevance filter: Pixabay's multi-term search degrades, and it degrades SILENTLY --------
# Verified live 2026-09-06 with the key at the plugin root: `q="linen apron white plain"`,
# orientation=vertical, order=popular returned a zebra as its top hit, and
# `q="kitchen window small tiled"` returned tomatoes. Every one of those came back as a normal
# 200 OK with a provenance sidecar written — nothing in the pipeline would have noticed. So a
# candidate whose own tags share no word with the query is not a candidate; it is a popular photo
# that happened to rank. Checked against the tags Pixabay itself supplies, which is the only
# machine-readable statement of what the picture is OF.
def relevance(rec: dict, terms: list) -> int:
    """How many query terms appear in the asset's own tags. 0 means Pixabay matched something else."""
    tags = re.findall(r"[a-z]+", str(rec.get("tags", "")).lower())
    tagset = set(tags)
    n = 0
    for t in terms:
        t = t.lower()
        if t in tagset or any(g.startswith(t) or t.startswith(g) for g in tags if len(g) > 3):
            n += 1
    return n


def rank(records: list, terms: list) -> tuple:
    """(kept, dropped) — kept sorted by how many query terms the asset's tags actually carry."""
    scored = [(relevance(r, terms), r) for r in records]
    kept = [r for n, r in sorted(scored, key=lambda x: -x[0]) if n > 0]
    dropped = [r for n, r in scored if n == 0]
    return kept, dropped


# ------------------------------------------------------------------------------------------ fill
def cmd_fill(a) -> int:
    allb = briefs(a.folder, a.job_root)
    bs = [b for b in allb if b["sourceable"] and b["query"]]
    skipped = [b for b in allb if not (b["sourceable"] and b["query"])]
    if not bs and not skipped:
        print("nothing to source — the reference plan has no gaps.")
        return 0
    if not a.execute:
        print(f"DRY RUN — {len(bs)} search(es) this would run. Add --execute to fetch.\n")
        for b in bs:
            print(f"  {b['shot']}/{b['what']}:  {' '.join(_q(x) for x in search_argv(b, a.per_gap))}")
        for b in skipped:
            print(f"  {b['shot']}/{b['what']}:  SKIPPED — {b['warnings'][0] if b['warnings'] else 'no query'}")
        return 1

    import pixabay_search as PX
    key = PX.resolve_key(a.key_file)
    cache = a.cache_dir or PX.default_cache_dir()
    os.makedirs(cache, exist_ok=True)
    PX.cache_prune(cache, __import__("time").time())

    log, rc = [], 0
    for b in bs:
        print(f"\n[{b['shot']} · {b['what']}]  q={b['query']!r}  ({b['type']}, {b['shape']})")
        ns = argparse.Namespace(
            query=b["query"], type=b["type"], orientation=(b["shape"] if b["type"] == "image" else "all"),
            image_type="photo", video_type="all", vertical=(b["type"] == "video" and b["shape"] == "vertical"),
            min_ratio=1.2, min_width=None, min_height=None, category=None, lang=None,
            editors_choice=False, safesearch=True, order="popular",
            per_page=max(3, a.per_gap * 2), page=1, max_pages=1, rendition="medium",
            refresh=a.refresh)
        try:
            records, total, notes = PX.run_search(ns, key, cache)
        except SystemExit as e:
            print(f"  search refused (exit {e.code}) — stopping so the rate limit is respected.",
                  file=sys.stderr)
            return 1
        for n in notes:
            print(f"  · {n}")
        kept, dropped = rank(records, b["terms"])
        if dropped:
            print(f"  · {len(dropped)} hit(s) dropped — their own tags carry none of "
                  f"{b['terms']} (Pixabay matched something else)")
        take = kept[: a.per_gap]
        if not take:
            print(f"  ⛔ no RELEVANT hits for {b['query']!r} — {len(records)} returned, none whose "
                  f"tags name what the slot is for. Rewrite `need:` with one or two plain nouns "
                  f"(Pixabay's relevance degrades fast past two terms), or source this one "
                  f"elsewhere.")
            log.append({**_logrec(b), "downloaded": 0, "total_hits": total,
                        "returned": len(records), "irrelevant": len(dropped)})
            rc = 1
            continue
        if len(take) < a.per_gap:
            print(f"  · only {len(take)} relevant of {len(records)} returned — a thin set is a "
                  f"finding about the query, not a reason to take what is there")
        PX.do_downloads(take, b["dest"])
        log.append({**_logrec(b), "downloaded": len(take), "total_hits": total,
                    "returned": len(records), "irrelevant": len(dropped),
                    "ids": [r["id"] for r in take]})
    for b in skipped:
        print(f"\n[{b['shot']} · {b['what']}]  SKIPPED — "
              f"{b['warnings'][0] if b['warnings'] else 'no usable query'}")
        log.append({**_logrec(b), "downloaded": 0, "skipped": True})
        rc = 1
    _write_log(a.folder, a.job_root, "fill", log)
    PX.print_reminder()
    print("\nCandidates only. `refsource.py candidates <folder>` to look at them, "
          "`adopt` to put one in a prompt. Nothing has been wired into any prompt.")
    return rc


def _logrec(b: dict) -> dict:
    return {"shot": b["shot"], "what": b["what"], "query": b["query"],
            "query_from": b["query_from"], "dest": b["dest"]}


def _write_log(folder: str, job_root, action: str, entries: list) -> str:
    base = job_root or job_root_of(folder)
    path = os.path.join(base, "_reference", LOG_NAME)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = {"history": []}
    doc["history"].append({"utc": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ",
                                                              __import__("time").gmtime()),
                           "action": action, "entries": entries})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    return path


# ------------------------------------------------------------------------------------ candidates
def candidate_sets(folder: str, job_root: str | None = None) -> list:
    base = job_root or job_root_of(folder)
    root = os.path.join(base, CANDIDATES_DIR)
    out = []
    if not os.path.isdir(root):
        return out
    for d in sorted(os.listdir(root)):
        full = os.path.join(root, d)
        if not os.path.isdir(full):
            continue
        items = []
        for f in sorted(os.listdir(full)):
            if f.endswith(".json"):
                continue
            side = PV.find_sidecar(os.path.join(full, f))
            meta = {}
            if side:
                try:
                    meta = json.load(open(side, encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    meta = {"error": "unreadable sidecar"}
            items.append({"file": os.path.join(full, f), "sidecar": side if os.path.isfile(side) else "",
                          "meta": meta})
        out.append({"gap": d, "dir": full, "items": items})
    return out


def cmd_candidates(a) -> int:
    sets = candidate_sets(a.folder, a.job_root)
    if a.json:
        json.dump(sets, sys.stdout, indent=2, ensure_ascii=False, default=str)
        print()
        return 0
    if not sets:
        print("no candidates yet — `refsource.py fill <folder> --execute` fetches them.")
        return 1
    print("THE LOOKBOOK — candidates waiting on a human decision\n")
    for s in sets:
        print(f"  {s['gap']}   ({len(s['items'])} candidate(s))")
        for it in s["items"]:
            m = it["meta"]
            dims = f"{m.get('width') or '?'}x{m.get('height') or '?'}"
            dur = f" {m['duration_s']}s" if m.get("duration_s") else ""
            print(f"    {os.path.basename(it['file']):<38} {dims:>11}{dur}")
            if m.get("tags"):
                print(f"      tags  {m['tags'][:78]}")
            if m.get("pageURL"):
                print(f"      {m['pageURL']}  · by {m.get('user', '?')}")
            if not it["sidecar"]:
                print("      ⛔ no provenance sidecar — this file cannot be adopted")
        print()
    print("Look at them. Then:\n"
          "  refsource.py adopt <folder> --shot S3 --what wardrobe --pick <file>\n"
          "An asset still marked NOT CLEARED needs `provenance.py record` first, or "
          "`--use reference-only` and a promise its likeness stays out of the output.")
    return 0


# ----------------------------------------------------------------------------------------- adopt
def _clearance_ok(sidecar: str, asset: str = "") -> tuple:
    """⛔ Clearance is RE-DERIVED here, never read.

    The skill's own fraud test: ask what it would take to pass this check dishonestly. Reading
    `clearance` as a string, the answer was "type CLEARED into a JSON file" — so it was not a
    check. Now adoption re-runs `provenance.outstanding()` over the recorded blockers, refuses a
    record that claims clearance without a signature, refuses a bare assertion carrying no blockers
    at all, and re-hashes the file so an asset swapped after it was cleared is caught."""
    try:
        m = json.load(open(sidecar, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return False, f"sidecar unreadable ({e})"
    clr = str(m.get("clearance", ""))
    if not clr:
        return False, "sidecar has no `clearance` field"
    if clr.upper().startswith("NOT CLEARED"):
        return False, clr
    if clr.upper().startswith("REFERENCE-ONLY"):
        return False, clr           # a reference-only record still needs `--use reference-only`

    blockers = m.get("blockers")
    if not isinstance(blockers, dict):
        return False, (f"{clr!r} is an assertion, not a record — the sidecar carries no `blockers` "
                       f"object, so nothing here answers the §5 checks. Write it with "
                       f"`provenance.py record`")
    out = PV.outstanding(blockers)
    if out:
        return False, (f"the record says {clr!r} but re-deriving it leaves "
                       f"{len(out)} blocker(s) outstanding: {'; '.join(out)}")
    if not str(m.get("cleared_by") or "").strip():
        return False, f"{clr!r} with no `cleared_by` — a clearance nobody signed is not a clearance"
    want = str(m.get("sha256") or "")
    if want and asset and os.path.isfile(asset):
        got = PV.sha256_file(asset)
        if got != want:
            return False, (f"the file changed since it was cleared — sidecar sha256 {want[:12]}…, "
                           f"file {got[:12]}…. Re-record it; a clearance describes ONE picture")
    return True, clr


def rewrite_ref_line(text: str, shot: str, what: str, newpath: str, use: str | None) -> tuple:
    """Rewrite the ONE `- role: …, what: <what>, …` line in the frontmatter to point at a file.

    Line-level on purpose: prompt frontmatter is hand-written and full of comments a YAML
    round-trip would eat. Returns (new_text, old_line) or (None, reason)."""
    if not text.startswith("---"):
        return None, "prompt has no frontmatter"
    end = text.find("\n---", 3)
    if end < 0:
        return None, "frontmatter is not closed"
    head, rest = text[:end], text[end:]
    lines = head.splitlines()
    hit = None
    for i, line in enumerate(lines):
        st = line.strip()
        if not st.startswith("-") or st.startswith("---"):
            continue
        body = st[1:].strip()
        if body.startswith("#"):
            continue
        item = {}
        for kv in re.split(r"\s*[·,]\s*", body):
            if ":" in kv:
                k, v = kv.split(":", 1)
                item[k.strip().lower()] = v.strip()
        if (item.get("what") or "").strip().lower() == what.lower():
            hit = i
            break
    if hit is None:
        return None, (f"no ref line with `what: {what}` — add one to {shot}'s frontmatter first "
                      f"(`- role: image, what: {what}, need: <what to look for>`)")
    old = lines[hit]
    indent = old[: len(old) - len(old.lstrip())]
    item = {}
    for kv in re.split(r"\s*[·,]\s*", old.strip()[1:].strip()):
        if ":" in kv:
            k, v = kv.split(":", 1)
            item[k.strip().lower()] = v.strip()
    parts = [f"role: {item.get('role', 'image')}", f"what: {what}", f"file: {newpath}"]
    if use:
        parts.append(f"use: {use}")
    lines[hit] = f"{indent}- " + ", ".join(parts)
    return "\n".join(lines) + rest, old


def cmd_adopt(a) -> int:
    base = a.job_root or job_root_of(a.folder)
    pick = a.pick if os.path.isabs(a.pick) else os.path.join(os.getcwd(), a.pick)
    if not os.path.isfile(pick):
        print(f"REFUSED: {a.pick} is not a file", file=sys.stderr)
        return 2
    side = PV.find_sidecar(pick)
    if not side:
        print(f"REFUSED: {os.path.basename(pick)} has no provenance sidecar. Every reference asset "
              f"carries one (source, licence, clearance) — `provenance.py record` writes it. An "
              f"asset with no provenance cannot be cleared, and an uncleared asset cannot ship "
              f"(stock-sourcing.md §9).", file=sys.stderr)
        return 1
    ok, clr = _clearance_ok(side, pick)
    use = (a.use or "").strip().lower() or None
    if not ok and not (use and use.startswith("reference")):
        print(f"REFUSED: {os.path.basename(pick)} — clearance is {clr!r}.\n"
              f"  Answer the §5 blockers and record the verdict:\n"
              f"    provenance.py record {os.path.relpath(pick)} --face ... --trademark ... "
              f"--property ... --transformation ...\n"
              f"  or adopt it with `--use reference-only` and keep its likeness out of the output.",
              file=sys.stderr)
        return 1

    # find the prompt that owns this slot
    prompts = [f for f in sorted(os.listdir(a.folder)) if f.endswith(".prompt.md")] \
        if os.path.isdir(a.folder) else []
    target = None
    for f in prompts:
        fm, _ = PL.split_front(read(os.path.join(a.folder, f)))
        if str(fm.get("shot", "")).lower() == a.shot.lower():
            target = os.path.join(a.folder, f)
            break
    if not target:
        print(f"REFUSED: no prompt with `shot: {a.shot}` in {a.folder}", file=sys.stderr)
        return 1

    dest_dir = os.path.join(base, "_reference", slug(a.what))
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(pick))
    if os.path.exists(dest) and not a.force:
        print(f"REFUSED: {os.path.relpath(dest)} already exists — --force to replace it",
              file=sys.stderr)
        return 1
    rel = os.path.relpath(dest, base)
    new_text, old_line = rewrite_ref_line(read(target), a.shot, a.what, rel, use)
    if new_text is None:
        print(f"REFUSED: {old_line}", file=sys.stderr)
        return 1

    shutil.copy2(pick, dest)
    shutil.copy2(side, PV.sidecar_path(dest))   # the adopted copy always lands on the convention
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    _write_log(a.folder, a.job_root, "adopt",
               [{"shot": a.shot, "what": a.what, "pick": os.path.basename(pick),
                 "file": rel, "use": use or "", "clearance": clr, "prompt": target,
                 "replaced": old_line.strip()}])
    print(f"adopted  {os.path.basename(pick)}  →  {rel}")
    print(f"  {os.path.relpath(target)}")
    print(f"    - {old_line.strip()}")
    print(f"    + {next(l.strip() for l in new_text.splitlines() if rel in l)}")
    print(f"  clearance: {clr}")
    print("\nRe-lint before you generate:  prompt_lint.py " + os.path.relpath(a.folder) + " --plan")
    return 0


# ---------------------------------------------------------------------------------------- status
def status(folder: str, job_root: str | None = None) -> dict:
    rows = PL.plan_rows(folder, job_root)
    real = [r for r in rows if r["what"] not in ("(none)",)]
    sets = candidate_sets(folder, job_root)
    return {
        "folder": folder,
        "slots": len(real),
        "gaps": sum(1 for r in real if r["state"] == "gap"),
        "blocked": sum(1 for r in real if r["state"] == "blocked"),
        "sourced": sum(1 for r in real if r["state"] in ("ok", "bound")),
        "candidate_sets": len(sets),
        "candidates": sum(len(s["items"]) for s in sets),
        "shots_without_refs": sum(1 for r in rows if r["what"] == "(none)"),
        "ok": not any(r["state"] in ("gap", "blocked") for r in real),
    }


def cmd_status(a) -> int:
    s = status(a.folder, a.job_root)
    if a.json:
        json.dump(s, sys.stdout, indent=2)
        print()
        return 0 if s["ok"] else 1
    print(f"REFERENCE SOURCING — {os.path.relpath(a.folder)}")
    print(f"  {s['slots']} slot(s): {s['sourced']} sourced · {s['gaps']} gap · {s['blocked']} blocked")
    print(f"  {s['candidates']} candidate(s) across {s['candidate_sets']} gap folder(s)")
    if s["shots_without_refs"]:
        print(f"  {s['shots_without_refs']} shot(s) plan no references at all — that is a choice "
              f"you should have made on purpose (prompting-craft.md §6b)")
    if not s["ok"]:
        print("  ⛔ not ready to generate. `refsource.py brief` → `fill --execute` → look → `adopt`.")
    return 0 if s["ok"] else 1


# -------------------------------------------------------------------------------------- selftest
def selftest() -> int:
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and bool(cond)

    check("aspect 9:16 is vertical", aspect_shape("9:16") == "vertical")
    check("aspect 16:9 is horizontal", aspect_shape("16:9") == "horizontal")
    check("aspect 1:1 is all", aspect_shape("1:1") == "all")
    check("aspect junk is all", aspect_shape("cinemascope") == "all")

    t = terms_from("A weathered olive grove at golden hour, dry stone wall behind", "environment")
    check("terms drop stopwords and keep the set nouns", "grove" in t and "the" not in t)
    check("on-attribute vocabulary leads", t[0] in ("grove", "wall"))
    check("terms are capped", len(terms_from(" ".join(f"word{i}" for i in range(40)), "prop")) <= MAX_TERMS)
    check("a human's need: keeps its word order",
          terms_from("small tiled bakery kitchen daylight", "environment", keep_order=True)[:3]
          == ["small", "tiled", "bakery"])
    check("a block-derived query leads with the attribute's own vocabulary",
          terms_from("a baker beside a kitchen counter", "environment")[0] in ("kitchen", "counter"))

    # the relevance filter — the live 2026-09-06 failures, as fixtures
    zebra = {"tags": "zebra, stripes, animal, safari, wildlife, savannah"}
    apron = {"tags": "man, cook, chef, apron, kitchen, linen, portrait"}
    tomato = {"tags": "tomatoes, red tomatoes, fresh, harvest, produce, vegetables"}
    tiles = {"tags": "kitchen, tiled wall, window, daylight, interior"}
    check("a zebra scores zero against 'linen apron white plain'",
          relevance(zebra, ["linen", "apron", "white", "plain"]) == 0)
    check("the apron photo scores", relevance(apron, ["linen", "apron", "white", "plain"]) >= 2)
    kept, dropped = rank([zebra, tomato, apron], ["linen", "apron", "white", "plain"])
    check("rank keeps only what the tags actually name",
          len(kept) == 1 and len(dropped) == 2 and kept[0] is apron)
    kept2, dropped2 = rank([tomato, tiles], ["small", "tiled", "bakery", "kitchen"])
    check("tomatoes are dropped for a tiled-kitchen query",
          len(kept2) == 1 and kept2[0] is tiles)
    check("nothing relevant returns an empty keep, not a fallback",
          rank([zebra, tomato], ["apron"])[0] == [])
    check("camera jargon is not a search term",
          "mm" not in terms_from("50mm eye level slight low angle", "environment"))

    with tempfile.TemporaryDirectory() as d:
        job = os.path.join(d, "job")
        pr = os.path.join(job, "01-script", "prompts")
        os.makedirs(pr)
        os.makedirs(os.path.join(job, "00-brief"))
        p1 = os.path.join(pr, "S1.frame.prompt.md")
        open(p1, "w", encoding="utf-8").write(
            "---\nshot: S1\nkind: frame\nmodel: nano_banana\naspect: 9:16\nrefs:\n"
            "  - role: image, what: environment, need: rustic kitchen window light\n"
            "  - role: image, what: wardrobe\n"
            "  - role: audio, what: voice, need: warm female narrator\n"
            "---\n[SUBJECT]\nA baker slides a tray forward\n\n[ENVIRONMENT]\n"
            "A small tiled kitchen, flour on the counter, a window behind\n\n[LIGHTING]\n"
            "5200K window light\n\n[CAMERA]\n35mm eye level\n")
        bs = briefs(pr, job)
        by = {b["what"]: b for b in bs}
        check("every unsourced slot becomes a brief", len(bs) == 3)
        check("an explicit need: is the query", "kitchen" in by["environment"]["query"])
        check("a slot with nothing falls back to the prompt's own blocks",
              by["wardrobe"]["query_from"] != "need:")
        check("a fallback query with no on-attribute word says so",
              any("no wardrobe words" in w for w in by["wardrobe"]["warnings"]))
        check("action verbs are not search terms",
              "slides" not in by["wardrobe"]["query"])
        check("voice is reported unsourceable, not silently skipped",
              by["voice"]["sourceable"] is False and by["voice"]["warnings"])
        check("aspect drives orientation", by["environment"]["shape"] == "vertical")
        check("character/prop/environment risks are stated up front",
              "property release" in by["environment"]["risk"])
        argv = search_argv(by["environment"], 4)
        check("the command asks for photos, vertical, downloaded",
              "--image-type" in argv and "vertical" in argv and "--download" in argv)
        vargv = search_argv({**by["wardrobe"], "type": "video", "shape": "vertical",
                             "query": "x", "dest": "/tmp/x"}, 3)
        check("a video attribute searches video, vertical, and never asks for a photo type",
              vargv[vargv.index("--type") + 1] == "video" and "--vertical" in vargv
              and "--image-type" not in vargv)

        # --- adopt: refuses without provenance, refuses uncleared, rewrites the line -------------
        cand = os.path.join(job, CANDIDATES_DIR, "s1-environment")
        os.makedirs(cand)
        asset = os.path.join(cand, "pixabay-1-large.jpg")
        open(asset, "wb").write(b"\xff\xd8\xff\x00fake")
        ns = argparse.Namespace(folder=pr, job_root=job, shot="S1", what="environment",
                                pick=asset, use=None, force=False)
        check("adopt refuses an asset with no sidecar", cmd_adopt(ns) == 1)
        json.dump({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                   "clearance": "NOT CLEARED — per-asset checks below are outstanding"},
                  open(asset + ".json", "w", encoding="utf-8"))
        check("adopt refuses NOT CLEARED", cmd_adopt(ns) == 1)
        ns.use = "reference-only"
        check("adopt accepts NOT CLEARED as reference-only", cmd_adopt(ns) == 0)
        txt = read(p1)
        check("the ref line now points at the adopted file",
              "file: _reference/environment/pixabay-1-large.jpg" in txt)
        check("the adopted line keeps its use: marker", "use: reference-only" in txt)
        check("the file and its sidecar landed in _reference/<attr>/, on the convention",
              os.path.isfile(os.path.join(job, "_reference", "environment",
                                          "pixabay-1-large.jpg"))
              and os.path.isfile(os.path.join(job, "_reference", "environment",
                                              "pixabay-1-large.jpg.json")))
        check("the decision is logged",
              os.path.isfile(os.path.join(job, "_reference", LOG_NAME)))
        check("the environment gap is closed",
              not any(b["what"] == "environment" for b in briefs(pr, job)))
        check("adopt refuses a shot that has no such slot",
              cmd_adopt(argparse.Namespace(folder=pr, job_root=job, shot="S1", what="palette",
                                           pick=asset, use="reference-only", force=True)) == 1)
        st = status(pr, job)
        check("status counts the remaining gaps", st["gaps"] == 2 and st["ok"] is False)
        check("status sees the candidates", st["candidates"] >= 1)

        # --- clearance is RE-DERIVED, so a typed "CLEARED" is not a clearance -------------------
        clean = os.path.join(cand, "pixabay-2-large.jpg")
        open(clean, "wb").write(b"\xff\xd8\xff\x00fake2")
        stem_side = os.path.splitext(clean)[0] + ".json"          # legacy stem form, still read
        json.dump({"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                   "clearance": "CLEARED 2026-09-06"},
                  open(stem_side, "w", encoding="utf-8"))
        check("a legacy stem-form sidecar is still read",
              PV.find_sidecar(clean).endswith("pixabay-2-large.json"))
        ns_clean = argparse.Namespace(folder=pr, job_root=job, shot="S1", what="wardrobe",
                                      pick=clean, use=None, force=False)
        check("a typed 'CLEARED' with no blockers object is refused as an assertion",
              cmd_adopt(ns_clean) == 1)

        def _record(**over):
            b = {"face": "none — no people in frame", "trademark": "none — unbranded",
                 "property": "none — plain background",
                 "transformation": "reference only, conditions a generated frame, never composited"}
            b.update(over.pop("blockers", {}))
            rec = {"source": "pixabay", "licence": {"name": "Pixabay Content License"},
                   "sha256": PV.sha256_file(clean), "blockers": b,
                   "blockers_outstanding": PV.outstanding(b),
                   "clearance": "CLEARED by Dana on 2026-09-06",
                   "cleared_by": "Dana", "cleared_date": "2026-09-06"}
            rec.update(over)
            json.dump(rec, open(stem_side, "w", encoding="utf-8"))

        _record(blockers={"face": "a recognisable face, no release"})
        check("a record that claims CLEARED while a blocker still blocks is refused",
              cmd_adopt(ns_clean) == 1)
        _record(cleared_by="")
        check("a clearance nobody signed is refused", cmd_adopt(ns_clean) == 1)
        _record(sha256="0" * 64)
        check("an asset swapped after it was cleared is caught by the hash",
              cmd_adopt(ns_clean) == 1)
        _record()
        check("a real, re-derivable, signed record adopts with no --use",
              cmd_adopt(ns_clean) == 0)
        check("a wardrobe line that had no source now has one",
              "what: wardrobe, file: _reference/wardrobe/" in read(p1))

    print("-" * 60)
    print("selftest OK — brief from need: (order kept) and from the prompt's blocks · unsourceable "
          "voice · aspect→orientation · the relevance filter drops the live zebra and the live "
          "tomatoes · clearance is RE-DERIVED at adoption (a typed 'CLEARED', an unsigned one, a "
          "still-blocking blocker and a swapped file are all refused) · adopt rewrites the ref "
          "line and logs the decision"
          if ok else "selftest FAILED")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="offline checks; no network, no key")
    sub = ap.add_subparsers(dest="cmd")

    def common(s):
        s.add_argument("folder", help="the prompts folder (e.g. 01-script/prompts/)")
        s.add_argument("--job-root", help="job folder (default: walk up to the folder holding 00-brief/)")
        s.add_argument("--json", action="store_true")
        return s

    common(sub.add_parser("brief", help="every unsourced slot → a Pixabay search derived from the "
                                        "prompt that needs it"))
    f = common(sub.add_parser("fill", help="run those searches and download candidates"))
    f.add_argument("--execute", action="store_true", help="actually search and download")
    f.add_argument("--per-gap", type=int, default=PER_GAP_DEFAULT,
                   help=f"candidates per gap (default {PER_GAP_DEFAULT})")
    f.add_argument("--refresh", action="store_true", help="bypass the 24h cache for these queries")
    f.add_argument("--key-file", help="file holding the API key (default: the plugin root, then ~)")
    f.add_argument("--cache-dir")
    common(sub.add_parser("candidates", help="what is waiting on a human decision"))
    ad = common(sub.add_parser("adopt", help="record the human's pick into the prompt"))
    ad.add_argument("--shot", required=True)
    ad.add_argument("--what", required=True, help="the attribute this reference carries")
    ad.add_argument("--pick", required=True, help="the chosen candidate file")
    ad.add_argument("--use", help="`reference-only` for an asset whose likeness must not ship")
    ad.add_argument("--force", action="store_true", help="replace an existing file of that name")
    common(sub.add_parser("status", help="gaps · candidates · sourced"))

    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help()
        return 2
    if a.cmd != "adopt" and not os.path.isdir(a.folder):
        print(f"error: {a.folder} is not a folder", file=sys.stderr)
        return 2
    return {"brief": cmd_brief, "fill": cmd_fill, "candidates": cmd_candidates,
            "adopt": cmd_adopt, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
