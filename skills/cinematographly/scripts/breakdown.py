#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""breakdown.py — the 1st AD's breakdown: read every shot as ONE object, not one at a time.

  breakdown.py <job> [--json]            the breakdown: what this film needs, across all shots
  breakdown.py <job> --continuity        the drift check on its own
  breakdown.py --selftest

WHAT THIS IS FOR, AND WHY IT DID NOT EXIST
Every check in this skill looked at one shot. `prompt_lint.py` lints a file. `--plan` prints a
table but never compares one row to another. So three failures had nowhere to be caught:

  1. **The requirement nobody owns.** Six shots need the hero. No shot is wrong on its own; the
     film has no hero designed, and you find out at shot six.
  2. **The reference sourced four times.** Four shots each declare `need: white linen apron`.
     Each is individually correct. It is ONE apron, and sourcing it once is the difference between
     four searches and one — plus four chances for the aprons to differ.
  3. ⛔ **Drift.** S1 says a green apron, S4 says olive. Neither prompt is wrong. The film is
     wrong, and it is only visible in the cut — which is the most expensive place to see it.

A real breakdown is what a 1st AD makes from a script before anyone books anything: every
requirement pulled out of every scene, grouped, counted, and assigned. That is what this does.

WHAT IT CANNOT DO
It reads what the prompts SAY. Two shots that describe an apron in words that do not overlap are
flagged; two shots that describe it identically and mean different things are not. And it cannot
tell you whether a difference is drift or a deliberate change — a costume change between scenes is
a legitimate difference and looks exactly like a mistake from here. **It names the differences; you
say which are intended.** `series-continuity.md` calls that the INVARIANT / VARIANT / DRIFT split,
and DRIFT is defined as "differs and nobody decided" — this tool exists to stop things being in
that state silently.

Reading: `references/series-continuity.md` (invariant · variant · drift) · `references/pm-workflow.md`
(the shot manifest) · `references/character-and-props.md` (why identity is locked by a reference).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import prompt_lint as PL              # noqa: E402  one parser for prompts, one vocabulary

# ------------------------------------------------------------------- character identity, normalised
# ⛔ THE DEFECT THIS FIXES (found 2026-09-08, by reading a script-breakdown text against this file).
# Both this script and shotlist.py keyed a character on RAW LABEL TEXT. So `hero` and `Hero` were
# two people: two cast rows, two "unlocked-character" findings, two reference lookups, and a
# continuity check that never compared the two halves of one character because it did not know they
# were one character. That is the ebook's own named audit failure — "if JOHN SMITH says a few lines
# early and the same character is labelled JOHN later, your software will treat these as two
# separate characters" — reproduced in the tool that exists to catch it.
#
# The fix is a KEY, not a rename: the display name stays whatever the writer wrote (the first
# spelling seen), and every other spelling is reported as an alias, because a script that names one
# person two ways is a finding in its own right and the writer is the one who has to settle it.
CUE_RE = re.compile(r"\s*\((?:V\.?O\.?|O\.?S\.?|O\.?C\.?|CONT'?D\.?|CONT\.?)\)\s*$", re.I)
# Wrapper pairs a label arrives in. Stripped only when BALANCED — see char_key's second paragraph.
PAIRS = {"<": ">", "[": "]", "(": ")", "{": "}", '"': '"', "'": "'", "`": "`", "\u201c": "\u201d",
         "\u201e": "\u201d"}


def char_key(name: str) -> str:
    """Fold a character label to a comparison key. Empty string means "no character named".

    Folds three things and nothing else: a trailing label colon or comma and BALANCED surrounding
    brackets or quotes (`<CHARACTER A>`, `"Hero"`, `HERO:`), a trailing STANDARD screenplay cue
    (`(V.O.)`, `(CONT'D)`), and case plus internal whitespace.

    ⛔ Balanced is the operative word, and it is not fussiness. An earlier draft stripped any
    trailing bracket, which turned "JOHN (YOUNG)" into "john (young" — a key with an unclosed
    paren. It did not merge two characters, so no test would have caught it; it just made every
    message about that character wrong. ⛔ And the whole parenthetical is never stripped: "JOHN
    (YOUNG)" is a DIFFERENT character from "JOHN", and a normaliser that merged them would replace
    a visible defect with an invisible one.
    """
    s = str(name or "").strip()
    changed = True
    while changed:
        changed = False
        s2 = s.rstrip(":,").strip()
        if s2 != s:
            s, changed = s2, True
        s2 = CUE_RE.sub("", s).strip()
        if s2 != s:
            s, changed = s2, True
        if len(s) >= 2 and s[0] in PAIRS and s[-1] == PAIRS[s[0]]:
            s, changed = s[1:-1].strip(), True
    return re.sub(r"\s+", " ", s).casefold()


def series_root(job: str) -> str:
    """The `_series/<BRAND>/` directory this job sits under, or "" if it is standalone.

    Walks up from the job looking for a directory whose PARENT is named `_series`. That covers both
    documented layouts — `_series/<BRAND>/<job>` and `_series/<BRAND>/BATCH-<ID>/<job>` — without
    needing to be told the brand.
    """
    d = os.path.abspath(job)
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return ""
        if os.path.basename(parent) == "_series":
            return d
        d = parent


def _ref_dirs(job: str) -> list:
    """Every place a character reference legitimately lives, nearest first."""
    out = [os.path.join(os.path.abspath(job), "_reference")]
    sr = series_root(job)
    if sr:
        out.append(os.path.join(sr, "_reference"))
    return out


LOCK_EXT = (".md", ".png", ".jpg", ".jpeg", ".webp", ".json")


def character_lock(job: str, name: str) -> str:
    """Path of the reference that locks this character, or "" if nothing does.

    ⛔ The old version checked exactly one path — `<job>/_reference/CHARACTER-<name>.md` — with the
    raw spelling. `pm-workflow.md` documents two OTHER shapes that are both correct: a series-level
    set at `_series/<BRAND>/_reference/` (where a recurring presenter actually lives, so the old
    check reported EVERY character unlocked on a normal episode), and the naming convention
    `<attribute>-<what-it-fixes>_<source>.<ext>` plus a `character/` subdirectory. Accept all of
    them, match case-insensitively, and say which file did the locking.
    """
    key = char_key(name)
    if not key:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    if not slug:
        return ""
    wanted = {f"character-{slug}", slug}
    for rd in _ref_dirs(job):
        if not os.path.isdir(rd):
            continue
        for dirpath, dirnames, filenames in os.walk(rd):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in filenames:
                stem, ext = os.path.splitext(fn)
                if ext.lower() not in LOCK_EXT:
                    continue
                low = stem.casefold()
                # ⛔ Split on the underscore BEFORE slugifying. An earlier version slugified first,
                # which turned "_" into "-" and made the split a no-op, so the documented
                # `<attr>-<what>_<source>.<ext>` name never matched — a check that looked like it
                # covered three shapes and covered two.
                st = re.sub(r"[^a-z0-9]+", "-", low).strip("-")
                head = re.sub(r"[^a-z0-9]+", "-", low.split("_", 1)[0]).strip("-")
                # `character-hero_client-supplied.png` locks `hero`; so does `CHARACTER-Hero.md`
                # and `_reference/character/hero.png`.
                if st in wanted or head in wanted:
                    return os.path.join(dirpath, fn)
                if os.path.basename(dirpath).casefold() == "character" and st == slug:
                    return os.path.join(dirpath, fn)
    return ""


# Blocks whose words describe the attribute in question — the same map refsource uses to build a
# search, reused here to compare two shots' descriptions of the same thing.
ATTR_BLOCKS = {
    "character": ("SUBJECT", "CHARACTER"),
    "wardrobe": ("SUBJECT", "CHARACTER"),
    "prop": ("SUBJECT", "ENVIRONMENT"),
    "environment": ("ENVIRONMENT", "SETTING", "LOCATION", "START FRAME"),
    "light": ("LIGHTING", "LIGHTING/MOOD"),
    "palette": ("COLORS", "STYLE"),
    "motion": ("MOTION",),
    "style": ("STYLE",),
    "voice": (),
}
STOP = set("""a an the and or of to in on at for with from by as is are was were be this that it its
his her their our your my he she they we not no very just then than so such into onto over under
above below near far up down out off more most some any each every all both few other another same
own one two three left right side front back behind""".split())


def read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def words_of(text: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z'-]{2,}", str(text or "").lower()) if w not in STOP}


def shot_files(job: str) -> list:
    out = []
    for root, dirs, files in os.walk(job):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_to_delete", "_candidates"))]
        out += [os.path.join(root, f) for f in files if f.endswith(".prompt.md")]
    return sorted(out)


def load_shots(job: str) -> list:
    """One record per prompt file: the shot, its refs, and the words each attribute is described in."""
    shots = []
    for f in shot_files(job):
        fm, body = PL.split_front(read(f))
        bl = PL.blocks_of(body)
        refs = []
        for r in (fm.get("refs") if isinstance(fm.get("refs"), list) else []):
            if not isinstance(r, dict):
                continue
            what = (r.get("what") or "").strip().lower()
            src = r.get("file") or r.get("value") or ""
            refs.append({"what": what, "role": (r.get("role") or "image").lower(),
                         "file": r.get("file") or "", "value": r.get("value") or "",
                         "need": (r.get("need") or "").strip(), "use": (r.get("use") or "").lower(),
                         "source": src, "sourced": bool(src)})
        described = {}
        for attr, blocks in ATTR_BLOCKS.items():
            txt = " ".join(bl.get(b, "") for b in blocks)
            if txt.strip():
                described[attr] = words_of(txt)
        shots.append({"file": f, "shot": str(fm.get("shot") or "?"),
                      "kind": str(fm.get("kind") or "?"), "type": str(fm.get("type") or ""),
                      "character": str(fm.get("character") or ""), "model": str(fm.get("model") or ""),
                      "refs": refs, "described": described, "blocks": bl})
    return shots


# ------------------------------------------------------------------------------------- breakdown
def breakdown(job: str) -> dict:
    """Requirements aggregated across the film, the way a 1st AD would pull them from a script."""
    shots = load_shots(job)
    by_attr: dict = {}
    for s in shots:
        for r in s["refs"]:
            if not r["what"]:
                continue
            e = by_attr.setdefault(r["what"], {"attribute": r["what"], "shots": [], "sources": {},
                                               "needs": [], "unsourced": []})
            e["shots"].append(s["shot"])
            if r["sourced"]:
                e["sources"].setdefault(r["source"], []).append(s["shot"])
            else:
                e["unsourced"].append(s["shot"])
                if r["need"]:
                    e["needs"].append((s["shot"], r["need"]))

    rows = []
    for attr, e in sorted(by_attr.items()):
        n_shots = len(set(e["shots"]))
        distinct = len(e["sources"])
        rows.append({
            "attribute": attr, "shots": sorted(set(e["shots"])), "shot_count": n_shots,
            "sources": {k: sorted(set(v)) for k, v in e["sources"].items()},
            "distinct_sources": distinct,
            "unsourced_shots": sorted(set(e["unsourced"])),
            "needs": e["needs"],
            # A reference used by more than one shot is LOAD-BEARING: it is worth more effort to
            # source well, and getting it wrong is wrong N times.
            "shared": n_shots > 1,
        })

    # characters named across the film, and whether each is actually locked by a reference file.
    # Keyed on char_key(), NOT on the raw label — see the note above that function.
    chars: dict = {}
    for s in shots:
        key = char_key(s["character"])
        if key:
            e = chars.setdefault(key, {"display": s["character"].strip(),
                                       "spellings": [], "shots": []})
        elif s["type"] == "character" or "CHARACTER" in s["blocks"]:
            e = chars.setdefault("", {"display": "(unnamed)", "spellings": [], "shots": []})
        else:
            continue
        e["shots"].append(s["shot"])
        raw = s["character"].strip()
        if raw and raw not in e["spellings"]:
            e["spellings"].append(raw)
    cast = []
    for key in sorted(chars):
        e = chars[key]
        locked = character_lock(job, e["display"]) if key else ""
        cast.append({"name": e["display"], "key": key, "spellings": e["spellings"],
                     "shots": sorted(set(e["shots"])), "locked_by": locked})

    findings = []
    for r in rows:
        if r["shared"] and r["distinct_sources"] > 1:
            findings.append({
                "kind": "split-reference", "attribute": r["attribute"],
                "detail": (f"{r['attribute']} is bound to {r['distinct_sources']} different sources "
                           f"across {r['shot_count']} shots: " +
                           " · ".join(f"{os.path.basename(k)} → {', '.join(v)}"
                                      for k, v in r["sources"].items()) +
                           ". Deliberate (a costume change, a second location) or drift?")})
        if r["shared"] and len(r["unsourced_shots"]) > 1:
            findings.append({
                "kind": "source-once", "attribute": r["attribute"],
                "detail": (f"{len(r['unsourced_shots'])} shots each declare an unsourced "
                           f"{r['attribute']} ({', '.join(r['unsourced_shots'])}). If it is the "
                           f"same {r['attribute']}, source it ONCE and bind the one file — four "
                           f"searches is four chances for them to differ")})
    for c in cast:
        if c["key"] and len(c["spellings"]) > 1:
            findings.append({
                "kind": "character-alias", "attribute": c["name"],
                "detail": (f"one character is spelled {len(c['spellings'])} ways across "
                           f"{len(c['shots'])} shot(s): " + " · ".join(repr(x) for x in c["spellings"]) +
                           ". Treated here as one person. ⛔ Settle it in the SCRIPT — a label "
                           f"that varies is how a reference stops being found and a cast list "
                           f"stops being a count")})
        if c["key"] and not c["locked_by"]:
            findings.append({
                "kind": "unlocked-character", "attribute": c["name"],
                "detail": (f"character {c['name']!r} appears in {len(c['shots'])} shot(s) "
                           f"({', '.join(c['shots'])}) with no reference locking it. Looked in " +
                           " and ".join(os.path.relpath(d, os.path.abspath(job)) if d.startswith(os.path.abspath(job))
                                        else d for d in _ref_dirs(job)) +
                           f" for CHARACTER-<name>.md, character-<name>_<source>.<ext>, or "
                           f"character/<name>.<ext>. ⛔ Identity is locked by a reference, never by "
                           f"text — a description drifts between generations and this is where it "
                           f"drifts N times")})
        if not c["key"]:
            findings.append({
                "kind": "unnamed-character", "attribute": "(unnamed)",
                "detail": (f"{len(c['shots'])} shot(s) carry a character with no `character:` in "
                           f"frontmatter ({', '.join(c['shots'])}) — nothing ties them to the same "
                           f"person, so nothing can check that they stay the same person")})

    return {"job": os.path.abspath(job), "shots": [s["shot"] for s in shots],
            "shot_count": len(shots), "requirements": rows, "cast": cast, "findings": findings}


# ---------------------------------------------------------------------------------------- optics
# ⛔ Focal length is SUPPOSED to vary — `ai-generation.md` says to rotate it by shot, and a wide on
# 35 cut against a close-up on 85 is ordinary coverage, not drift. Flagging that would manufacture a
# finding on every correctly-covered scene. What that file actually asks for is a CONSTANT camera /
# stock / lens-family prefix on every prompt, and THAT is checkable: strip the numbers and the shot
# sizes, and whatever camera language is left should be the same film throughout.
FOCAL_RE = re.compile(r"\b\d{1,3}\s?mm\b", re.I)
SIZE_WORDS = ("wide", "medium", "close", "closeup", "close-up", "cu", "ws", "ms", "mcu", "ecu",
              "full", "two-shot", "twoshot", "insert", "over", "ots", "profile", "low", "high",
              "eye", "level", "angle", "height", "chest", "waist", "knee", "hip", "shoulder",
              "locked", "off", "handheld", "static", "push", "pull", "in", "out", "slow", "fast")


def camera_signature(text: str) -> set:
    """The camera language that is supposed to be CONSTANT across the film."""
    # hyphens are split, so "locked-off" and "close-up" reduce to their parts and both parts are
    # in SIZE_WORDS — otherwise the hyphenated form survives and every locked-off shot reads as its
    # own camera. Caught by the selftest.
    txt = FOCAL_RE.sub(" ", (text or "")).replace("-", " ").replace("/", " ")
    return {w for w in words_of(txt) if w not in SIZE_WORDS}


def optics(job: str) -> dict:
    """Is this one camera, or several?

    Reports the distinct camera signatures across the whole film. Not within a scene: the constant
    the skill asks for is film-wide, and a scene is too small a sample to say anything."""
    shots = load_shots(job)
    sigs, focals = {}, {}
    for s in shots:
        cam = (s.get("blocks") or {}).get("CAMERA", "")
        if not cam.strip():
            continue
        sig = camera_signature(cam)
        focals[s["shot"]] = sorted({m.group(0).replace(" ", "").lower()
                                    for m in FOCAL_RE.finditer(cam)})
        if sig:
            sigs.setdefault(frozenset(sig), []).append(s["shot"])
    out = {"shots_with_camera": len(focals), "focals": focals,
           "signatures": [{"words": sorted(k), "shots": v} for k, v in sigs.items()],
           "findings": []}
    if len(sigs) > 1:
        groups = "; ".join(f"{', '.join(v)} → “{' '.join(sorted(k))}”" for k, v in sigs.items())
        out["findings"].append(
            f"{len(sigs)} different camera signatures across the film — {groups}. "
            f"ai-generation.md asks for a constant camera/stock/lens prefix on every prompt so the "
            f"shots read as one camera; focal length is meant to rotate and is excluded here. "
            f"Deliberate, or did the prefix drift between prompts?")
    missing = [s["shot"] for s in shots if not (s.get("blocks") or {}).get("CAMERA", "").strip()]
    if missing:
        out["findings"].append(
            f"no [CAMERA] block on {', '.join(missing)} — nothing ties these shots to the same "
            f"camera as the rest, so nothing can check that they read as one")
    return out


# ------------------------------------------------------------------------------------ continuity
def continuity(job: str, min_overlap: float = 0.34) -> dict:
    """Where two shots describe the same attribute in words that barely overlap.

    ⛔ A difference is not automatically a fault. A costume change between scenes is a legitimate
    VARIANT and looks identical to DRIFT from here. What this refuses to allow is the third state:
    differing because nobody decided (`series-continuity.md`). Every row below is a question, and
    the answer is yours."""
    shots = load_shots(job)
    out = []
    # ⛔ Only compare attributes the PLAN actually declares somewhere in this job. The described-
    # words map is built by scraping blocks, so without this it will happily compare "prop" across
    # two shots that never mention a prop — inferring a requirement nobody wrote down and reporting
    # its absence as drift. Found in the selftest, 2026-09-07: continuity has to be grounded in the
    # reference plan, not in word-scraping, or it manufactures findings.
    declared = {r["what"] for s in shots for r in s["refs"] if r["what"]}
    attrs = sorted({a for s in shots for a in s["described"]} & declared)
    for attr in attrs:
        having = [s for s in shots if s["described"].get(attr)]
        if len(having) < 2:
            continue
        for i in range(len(having)):
            for j in range(i + 1, len(having)):
                a, b = having[i], having[j]
                # Two shots that bind the SAME reference for this attribute are supposed to look
                # alike and the words are allowed to differ — the pixels are the agreement.
                same_ref = _bound_same(a, b, attr)
                wa, wb = a["described"][attr], b["described"][attr]
                inter = wa & wb
                union = wa | wb
                overlap = len(inter) / len(union) if union else 1.0
                if overlap >= min_overlap or same_ref:
                    continue
                only_a = sorted(wa - wb)[:6]
                only_b = sorted(wb - wa)[:6]
                out.append({"attribute": attr, "a": a["shot"], "b": b["shot"],
                            "overlap": round(overlap, 2),
                            "only_in_a": only_a, "only_in_b": only_b,
                            "bound_same_reference": same_ref})
    return {"job": os.path.abspath(job), "pairs": out, "threshold": min_overlap}


def _bound_same(a: dict, b: dict, attr: str) -> bool:
    sa = {r["source"] for r in a["refs"] if r["what"] == attr and r["sourced"]}
    sb = {r["source"] for r in b["refs"] if r["what"] == attr and r["sourced"]}
    return bool(sa and sa == sb)


# ---------------------------------------------------------------------------------------- report
def render(bd: dict, cont: dict) -> str:
    L = []
    L.append(f"BREAKDOWN — {os.path.basename(bd['job'])} · {bd['shot_count']} shot(s)\n")
    if not bd["shot_count"]:
        return ("no *.prompt.md anywhere under the job — the breakdown reads the shots, so there is "
                "nothing to break down yet (`prompt_lint.py --template frame|clip`)")
    L.append(f"  {'attribute':<12} {'shots':<22} {'sourced':<9} status")
    L.append("  " + "-" * 78)
    for r in bd["requirements"]:
        shots = ", ".join(r["shots"])[:21]
        got = f"{r['distinct_sources']} file(s)" if r["distinct_sources"] else "—"
        if r["unsourced_shots"] and r["distinct_sources"]:
            st = f"partly sourced · {len(r['unsourced_shots'])} shot(s) still open"
        elif r["unsourced_shots"]:
            st = f"⛔ nothing sourced ({len(r['unsourced_shots'])} shot(s))"
        elif r["distinct_sources"] > 1:
            st = f"⛔ {r['distinct_sources']} different sources"
        else:
            st = "one reference, shared" if r["shared"] else "sourced"
        L.append(f"  {r['attribute']:<12} {shots:<22} {got:<9} {st}")

    if bd["cast"]:
        L.append("\n  CAST")
        for c in bd["cast"]:
            lock = ("locked by " + os.path.basename(c["locked_by"])) if c["locked_by"] \
                else "⛔ not locked by a reference"
            alias = ""
            if len(c.get("spellings", [])) > 1:
                alias = "  ⛔ also spelled " + ", ".join(x for x in c["spellings"][1:])
            L.append(f"    {c['name']:<14} {', '.join(c['shots']):<22} {lock}{alias}")

    if bd["findings"]:
        L.append(f"\n  {len(bd['findings'])} finding(s) — the ones a per-shot check cannot see")
        for f in bd["findings"]:
            L.append(f"    · [{f['kind']}] {f['detail']}")
    else:
        L.append("\n  no cross-shot findings — every requirement is owned and sourced once")

    L.append(f"\nCONTINUITY — attributes described differently across shots "
             f"(overlap < {cont['threshold']:.0%})")
    if not cont["pairs"]:
        L.append("  nothing drifting, or too few shots to compare")
    else:
        for p in cont["pairs"]:
            L.append(f"    {p['attribute']:<12} {p['a']} vs {p['b']}  overlap {p['overlap']:.0%}")
            L.append(f"      only in {p['a']}: {', '.join(p['only_in_a']) or '—'}")
            L.append(f"      only in {p['b']}: {', '.join(p['only_in_b']) or '—'}")
        L.append("\n  ⛔ A difference is a QUESTION, not a verdict. A costume change between scenes "
                 "is a legitimate\n     variant and looks exactly like a mistake from here. What is "
                 "not allowed is the third state:\n     differing because nobody decided "
                 "(series-continuity.md). Decide each one, then record it.")
    return "\n".join(L)


# -------------------------------------------------------------------------------------- selftest
def selftest() -> int:
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and bool(cond)

    def shot(shot_id, refs, blocks, extra=""):
        r = "\n".join(f"  - {x}" for x in refs)
        b = "\n\n".join(f"[{k}]\n{v}" for k, v in blocks.items())
        return (f"---\nshot: {shot_id}\nkind: frame\nmodel: nano_banana\naspect: 9:16\n{extra}"
                f"refs:\n{r}\n---\n{b}\n")

    with tempfile.TemporaryDirectory() as td:
        job = os.path.join(td, "job")
        pr = os.path.join(job, "01-script", "prompts")
        os.makedirs(pr)
        os.makedirs(os.path.join(job, "00-brief"))

        bd = breakdown(job)
        check("an empty job breaks down to nothing, and says so", bd["shot_count"] == 0)
        check("the renderer says what to do instead of printing an empty table",
              "nothing to break down" in render(bd, continuity(job)))

        # three shots, all needing wardrobe, none sourced — the SOURCE-ONCE finding
        for sid in ("S1", "S2", "S3"):
            open(os.path.join(pr, f"{sid}.frame.prompt.md"), "w").write(shot(
                sid, ["role: image, what: wardrobe, need: white linen apron"],
                {"SUBJECT": "a baker at the bench", "LIGHTING": "5200K daylight",
                 "CAMERA": "35mm eye level"}))
        bd = breakdown(job)
        w = next(r for r in bd["requirements"] if r["attribute"] == "wardrobe")
        check("one requirement row covers all three shots", w["shot_count"] == 3 and w["shared"])
        check("three shots each sourcing the same thing is ONE finding, not three",
              sum(1 for f in bd["findings"] if f["kind"] == "source-once") == 1)
        check("and it says to source it once",
              any("source it ONCE" in f["detail"] for f in bd["findings"]))

        # bind two different files for the same attribute — the SPLIT-REFERENCE finding
        open(os.path.join(pr, "S1.frame.prompt.md"), "w").write(shot(
            "S1", ["role: image, what: wardrobe, file: _reference/wardrobe/green.jpg"],
            {"SUBJECT": "a baker at the bench", "LIGHTING": "5200K daylight",
             "CAMERA": "35mm eye level"}))
        open(os.path.join(pr, "S2.frame.prompt.md"), "w").write(shot(
            "S2", ["role: image, what: wardrobe, file: _reference/wardrobe/olive.jpg"],
            {"SUBJECT": "a baker at the bench", "LIGHTING": "5200K daylight",
             "CAMERA": "35mm eye level"}))
        bd = breakdown(job)
        check("two different files for one attribute is flagged",
              any(f["kind"] == "split-reference" for f in bd["findings"]))
        check("and the finding asks whether it was deliberate rather than asserting a fault",
              any("Deliberate" in f["detail"] for f in bd["findings"] if f["kind"] == "split-reference"))

        # a named character with no locked reference file
        open(os.path.join(pr, "S4.frame.prompt.md"), "w").write(shot(
            "S4", ["role: image, what: character, value: media_1"],
            {"SUBJECT": "the host", "CHARACTER": "green apron, silver hair",
             "LIGHTING": "5200K", "CAMERA": "50mm"}, extra="character: hero\ntype: character\n"))
        bd = breakdown(job)
        check("a named character reaches the cast list",
              any(c["name"] == "hero" for c in bd["cast"]))
        check("an unlocked character is a finding",
              any(f["kind"] == "unlocked-character" for f in bd["findings"]))
        os.makedirs(os.path.join(job, "_reference"), exist_ok=True)
        open(os.path.join(job, "_reference", "CHARACTER-hero.md"), "w").write("# hero\n")
        bd = breakdown(job)
        check("once the reference file exists the finding clears",
              not any(f["kind"] == "unlocked-character" for f in bd["findings"]))
        check("and the cast row shows what locks it",
              next(c for c in bd["cast"] if c["name"] == "hero")["locked_by"].endswith(
                  "CHARACTER-hero.md"))

        # --- IDENTITY NORMALISATION ------------------------------------------------------
        # The unit half first, because these are the cases the aggregation depends on.
        check("case alone is not a second person", char_key("Hero") == char_key("hero") == "hero")
        check("a wrapped label folds to the same key", char_key("<HERO>") == "hero"
              and char_key('"Hero"') == "hero" and char_key("HERO:") == "hero")
        check("a standard screenplay cue is not part of the name",
              char_key("HERO (V.O.)") == "hero" and char_key("HERO (CONT'D):") == "hero")
        check("⛔ but a NON-cue parenthetical is part of the name — JOHN (YOUNG) is not JOHN",
              char_key("JOHN (YOUNG)") != char_key("JOHN")
              and char_key("JOHN (YOUNG)") == "john (young)")   # and the paren is not left unclosed
        check("an empty or whitespace label is no character at all",
              char_key("") == "" and char_key("   ") == "")

        # The integration half: one character, two spellings, across two shots.
        open(os.path.join(pr, "S4b.frame.prompt.md"), "w").write(shot(
            "S4b", ["role: image, what: character, value: media_1"],
            {"SUBJECT": "the host", "CHARACTER": "green apron, silver hair",
             "LIGHTING": "5200K", "CAMERA": "50mm"}, extra="character: Hero\ntype: character\n"))
        bd = breakdown(job)
        rows = [c for c in bd["cast"] if c["key"] == "hero"]
        check("⛔ `hero` and `Hero` are ONE cast row, not two", len(rows) == 1)
        check("and that row carries both shots", set(rows[0]["shots"]) >= {"S4", "S4b"})
        check("the differing spellings are REPORTED, not silently merged",
              any(f["kind"] == "character-alias" for f in bd["findings"])
              and set(rows[0]["spellings"]) == {"hero", "Hero"})
        check("the existing lock still covers the character under either spelling",
              not any(f["kind"] == "unlocked-character" for f in bd["findings"]))

        # --- WHERE A LOCK MAY LIVE -------------------------------------------------------
        # ⛔ The old check knew exactly one path, so on a normal series episode — where the
        # recurring presenter is locked at SERIES level, per pm-workflow.md — it reported every
        # character unlocked. Each shape below is documented somewhere in the skill.
        os.remove(os.path.join(job, "_reference", "CHARACTER-hero.md"))
        bd = breakdown(job)
        check("with the lock gone the finding returns (the test above was not vacuous)",
              any(f["kind"] == "unlocked-character" for f in bd["findings"]))
        os.makedirs(os.path.join(job, "_reference", "character"), exist_ok=True)
        open(os.path.join(job, "_reference", "character", "hero.png"), "w").write("x")
        check("`_reference/character/<name>.png` locks it",
              not any(f["kind"] == "unlocked-character" for f in breakdown(job)["findings"]))
        os.remove(os.path.join(job, "_reference", "character", "hero.png"))
        open(os.path.join(job, "_reference", "character-hero_client-supplied.png"), "w").write("x")
        check("the documented `<attr>-<what>_<source>.<ext>` name locks it",
              not any(f["kind"] == "unlocked-character" for f in breakdown(job)["findings"]))
        os.remove(os.path.join(job, "_reference", "character-hero_client-supplied.png"))
        check("and with every job-local shape gone it is unlocked again",
              any(f["kind"] == "unlocked-character" for f in breakdown(job)["findings"]))

        # the series-level set, which is where a recurring presenter actually lives
        sjob = os.path.join(td, "_series", "ACME", "BATCH-A", "ep-01001")
        os.makedirs(os.path.join(sjob, "02-prompts"))
        open(os.path.join(sjob, "02-prompts", "S1.frame.prompt.md"), "w").write(shot(
            "S1", ["role: image, what: character, value: media_1"],
            {"SUBJECT": "the host", "CHARACTER": "green apron", "LIGHTING": "5200K",
             "CAMERA": "50mm"}, extra="character: HERO\ntype: character\n"))
        check("series_root finds `_series/<BRAND>/` from a job nested under a BATCH",
              os.path.basename(series_root(sjob)) == "ACME")
        check("a job with no _series above it is standalone", series_root(job) == "")
        check("an episode with nothing locked anywhere is a finding",
              any(f["kind"] == "unlocked-character" for f in breakdown(sjob)["findings"]))
        os.makedirs(os.path.join(td, "_series", "ACME", "_reference"))
        open(os.path.join(td, "_series", "ACME", "_reference",
                          "CHARACTER-Hero.md"), "w").write("# hero\n")
        check("⛔ a SERIES-level reference locks the episode's character",
              not any(f["kind"] == "unlocked-character" for f in breakdown(sjob)["findings"]))

        # --- CONTINUITY ------------------------------------------------------------------
        base = {"SUBJECT": "a baker at the bench", "LIGHTING": "5200K daylight",
                "CAMERA": "35mm eye level"}
        open(os.path.join(pr, "S5.frame.prompt.md"), "w").write(shot(
            "S5", ["role: image, what: environment, need: kitchen"],
            {**base, "ENVIRONMENT": "a small tiled kitchen, flour on the counter, a window behind"}))
        open(os.path.join(pr, "S6.frame.prompt.md"), "w").write(shot(
            "S6", ["role: image, what: environment, need: kitchen"],
            {**base, "ENVIRONMENT": "a vast marble atrium, brass fittings, a chandelier overhead"}))
        c = continuity(job)
        pair = [p for p in c["pairs"] if {p["a"], p["b"]} == {"S5", "S6"}
                and p["attribute"] == "environment"]
        check("two shots describing one attribute completely differently is flagged", len(pair) == 1)
        check("and the finding names what differs, not just that something does",
              pair and "marble" in " ".join(pair[0]["only_in_b"] + pair[0]["only_in_a"]))
        # the same words in both → no finding
        open(os.path.join(pr, "S6.frame.prompt.md"), "w").write(shot(
            "S6", ["role: image, what: environment, need: kitchen"],
            {**base, "ENVIRONMENT": "a small tiled kitchen, flour on the counter, a window behind"}))
        c = continuity(job)
        check("matching descriptions are not flagged",
              not [p for p in c["pairs"] if {p["a"], p["b"]} == {"S5", "S6"}])
        # ⛔ two shots BOUND TO THE SAME reference are allowed to word it differently — the pixels
        # are the agreement, and flagging that would punish the fix
        for sid, env in (("S7", "a small tiled kitchen, flour, a window"),
                         ("S8", "the room as supplied, nothing added")):
            open(os.path.join(pr, f"{sid}.frame.prompt.md"), "w").write(shot(
                sid, ["role: image, what: environment, file: _reference/environment/room.jpg"],
                {**base, "ENVIRONMENT": env}))
        c = continuity(job)
        check("two shots bound to the SAME reference are not flagged for wording",
              not [p for p in c["pairs"] if {p["a"], p["b"]} == {"S7", "S8"}
                   and p["attribute"] == "environment"])
        check("an attribute NO shot declares is never compared — continuity reads the plan, not "
              "scraped words",
              not any(p["attribute"] == "prop" for p in c["pairs"]))

        txt = render(breakdown(job), continuity(job))
        check("the report states that a difference is a question, not a verdict",
              "a QUESTION, not a verdict" in txt)

    print("-" * 60)
    # --- optics: one camera, or several? ------------------------------------------------------
    # ⛔ focal length is EXCLUDED, because rotating it by shot is house practice and flagging it
    # would manufacture a finding on every correctly-covered scene
    assert camera_signature("35mm, locked-off, chest height") == set(), \
        camera_signature("35mm, locked-off, chest height")
    a_ = camera_signature("Arri Alexa, Kodak Vision3 250D, 35mm, slow push in")
    b_ = camera_signature("Arri Alexa, Kodak Vision3 250D, 85mm, locked-off close")
    check("two focal lengths on the same camera give the SAME signature", a_ == b_)
    c_ = camera_signature("Sony Venice, digital, 50mm, handheld")
    check("a different camera gives a different signature", a_ != c_ and bool(c_))
    print("optics: focal length excluded, the camera/stock prefix compared")

    print("selftest OK — requirements aggregate across shots (source-once, split-reference), the "
          "cast list names who is unlocked, and continuity flags a real difference, ignores "
          "matching wording, and never punishes two shots that bound the same reference"
          if ok else "selftest FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--continuity", action="store_true", help="the drift check on its own")
    ap.add_argument("--overlap", type=float, default=0.34,
                    help="word-overlap floor below which two descriptions are flagged")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.job or not os.path.isdir(a.job):
        ap.print_help()
        return 2
    bd = breakdown(a.job)
    cont = continuity(a.job, a.overlap)
    opt = optics(a.job)
    if a.json:
        json.dump({"breakdown": bd, "continuity": cont, "optics": opt}, sys.stdout, indent=2,
                  ensure_ascii=False)
        print()
    elif a.continuity:
        print(render({"job": bd["job"], "shot_count": bd["shot_count"], "requirements": [],
                      "cast": [], "findings": [], "shots": []}, cont).split("CONTINUITY")[-1])
    else:
        print(render(bd, cont))
        if opt["findings"]:
            print("\nOPTICS — is this one camera?")
            for f in opt["findings"]:
                print(f"  ! {f}")
            fl = {k: v for k, v in opt["focals"].items() if v}
            if fl:
                print("  focal lengths declared: "
                      + ", ".join(f"{k} {'/'.join(v)}" for k, v in sorted(fl.items())))
                print("  (rotating focal length by shot is house practice — it is excluded from the")
                print("   comparison above, which is about the constant camera/stock prefix.)")
    return 1 if (bd["findings"] or cont["pairs"]) else 0


if __name__ == "__main__":
    sys.exit(main())
