#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""new_client.py — a new client's profile from the person's answers, ready for a first job. (3.1)

  new_client.py questions [--json]                 # what to ask, in plain words, with the studio's defaults
  new_client.py make --answers FILE.json [--clients-dir DIR]
  new_client.py --selftest

The agent asks the person the questions (a few at a time), writes their answers to a JSON file and runs `make`. It
writes `<slug>.md` (the template with section 0 — the hard locks the gate reads — answered, plus the brand line,
the claims category and signer, platforms, AI disclosure and delivery format), `costs.<slug>.json` and
`script.<slug>.json` (the templates: rates are read per account, numbers per brief) into the studio's clients
folder. Everything else in the profile stays for the person to fill in over time.

Refused before anything is written: a role or the agent as the approver, a policy that is not one of the three,
an unknown delivery format or mode, a slug that is not lower-case words. Never overwrites: the same answers again
leave the files byte-identical; different answers for an existing client are refused. Then it proves the profile
opens a concept-only job (new_job + gate.py open, in a throwaway folder).
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cine_home  # noqa: E402
import studio  # noqa: E402

SKILL = os.path.dirname(HERE)
TEMPLATES = os.path.join(SKILL, "clients")
FORMATS = os.path.join(SKILL, "assets", "delivery-formats.json")
MODES = {"A": "narrative promo: one hero film carrying the message", "B": "UGC volume: short one-idea videos, often",
         "C": "editorial explainer", "D": "repurpose cut of existing footage", "S": "stills only"}
CLAIMS = ("sleep", "beauty", "supplements", "finance", "none")
# key, question, required, studio default key
QUESTIONS = [
    ("name", "What is the client or brand called?", True, None),
    ("slug", "A short id for files (lower-case, hyphens), e.g. 'acme'", True, None),
    ("what", "What do they sell or do, in one sentence?", True, None),
    ("default_mode", "What do you mostly make for them: A one hero film, B many short UGC-style videos, C explainers, "
                     "D re-cuts of their footage, S stills?", True, None),
    ("format_lock", "Is the script or prompt structure fixed by the client, or open? (e.g. 'open')", True, None),
    ("audio_text_lock", "Can spoken lines be reworded, or are approved lines used word for word?", True, None),
    ("overlay_policy", "Anything on screen besides captions (supers, logos, end cards)? Or 'captions only'.", True, None),
    ("retired_tools", "Any AI model or tool they do not allow? Or 'none'.", True, None),
    ("verification_policy", "How closely should a person check each stage for this client: per-stage-human, gated "
                            "or standing?", True, "default_policy"),
    ("approver", "Who at the studio or the client signs off each stage (one person's name)?", True, "approvers"),
    ("delivery_format", "The delivery format (vertical-1080, feed-4x5, landscape-1080, square-1080, …)?", True, None),
    ("claims_category", "Do their videos make claims in a sensitive area: sleep, beauty, supplements, finance, or none?",
     True, None),
    ("claims_signer", "Who checks their claims before anything ships (a name)?", False, "claims_signer"),
    ("platforms", "Where will the videos run?", False, "platforms"),
    ("ai_disclosure", "How is AI-made video disclosed for this client?", False, "ai_disclosure"),
    ("language", "Language of the videos and captions (English only in this version)?", False, None),
]


def formats() -> list:
    return sorted(json.load(open(FORMATS, encoding="utf-8"))["formats"])


def with_defaults(ans: dict) -> dict:
    s = studio.load()
    out = dict(ans)
    for k, _, _, sk in QUESTIONS:
        if k not in out and sk and s.get(sk) is not None:
            v = s[sk]
            out[k] = v[0] if (k == "approver" and isinstance(v, list) and v) else v
    out.setdefault("language", "English")
    return out


def problems(a: dict) -> list:
    P = [f"missing answer: {k}" for k, _, req, _ in QUESTIONS if req and not str(a.get(k) or "").strip()]
    if a.get("slug") and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", str(a["slug"])):
        P.append("slug: lower-case letters, digits and hyphens")
    if a.get("slug", "").startswith("_"):
        P.append("slug: may not start with '_' (those are templates)")
    if a.get("default_mode") and str(a["default_mode"]).upper()[:1] not in MODES:
        P.append("default_mode: one of A, B, C, D, S")
    if a.get("verification_policy") and a["verification_policy"] not in studio.POLICIES:
        P.append(f"verification_policy: one of {', '.join(studio.POLICIES)}")
    appr = str(a.get("approver") or "")
    if appr and (studio.ROLE_RE.search(appr) or "," in appr):
        P.append(f"approver: one person's name, not a role or the agent ({appr!r})")
    if a.get("delivery_format") and a["delivery_format"] not in formats():
        P.append(f"delivery_format: one of {', '.join(formats())}")
    if a.get("claims_category") and a["claims_category"] not in CLAIMS:
        P.append(f"claims_category: one of {', '.join(CLAIMS)}")
    if str(a.get("language") or "English").strip().lower() not in ("english", "en", "english (us)", "english (uk)"):
        P.append("language: English only in this version")
    return P


def render(a: dict) -> str:
    t = open(os.path.join(TEMPLATES, "_TEMPLATE.md"), encoding="utf-8").read()
    mode = str(a["default_mode"]).upper()[:1]
    plats = a.get("platforms")
    plats = ", ".join(plats) if isinstance(plats, list) else (plats or "<the actual channels — confirm, never assume>")
    R = [("# Client Profile — <BRAND>", f"# Client Profile — {a['name']}"),
         ("> ⛔ `scripts/gate.py open` reads this section. Any `<placeholder>`, `NEEDS INPUT` or `TBD` left\n"
          "> here refuses the job: an unanswered hard lock is a question for the client, not a default.",
          "> ⛔ `scripts/gate.py open` reads this section: an unanswered hard lock here refuses the job."),
         ("**Default mode:** <A narrative-promo / B ugc-volume / C editorial / D repurpose> — and why.",
          f"**Default mode:** {mode} ({MODES[mode]})."),
         ("1. **Format lock?** <is the script/prompt structure frozen, or open>", f"1. **Format lock?** {a['format_lock']}"),
         ("2. **Audio-text lock?** <can spoken lines be reworded, or are they approved as-is>",
          f"2. **Audio-text lock?** {a['audio_text_lock']}"),
         ("3. **Overlay policy?** <captions only is the skill default — does this client render anything else>",
          f"3. **Overlay policy?** {a['overlay_policy']}"),
         ("4. **Retired tools/models?** <anything explicitly out of the stack, and why>",
          f"4. **Retired tools/models?** {a['retired_tools']}"),
         ("**Verification policy:** `<per-stage-human | gated | standing>`",
          f"**Verification policy:** `{a['verification_policy']}`\n\n**Named approver:** {a['approver']}."),
         ("- <company / product / sub-brands and how they relate>", f"- {a['name']}: {a['what']}"),
         ("**Claims-category:** `<sleep | beauty | supplements | finance | none>`",
          f"**Claims-category:** `{a['claims_category']}`"),
         ("- **Language / captions:** <target language + diacritics; captions burned in?>",
          f"- **Language / captions:** {a.get('language', 'English')} <captions burned in?>"),
         ("- **Platforms:** <the actual channels — confirm, never assume>", f"- **Platforms:** {plats}"),
         ("### Delivery format — `<preset name>`", f"### Delivery format — `{a['delivery_format']}`")]
    if a.get("claims_signer"):
        R.append(("· **Signer:** <name>", f"· **Signer:** {a['claims_signer']}"))
    if a.get("ai_disclosure"):
        R.append(("- **AI-disclosure mechanism per platform:** <which toggle, plus the on-screen treatment>",
                  f"- **AI-disclosure mechanism per platform:** {a['ai_disclosure']}"))
    for old, new in R:
        if old not in t:
            raise SystemExit(f"error: the profile template changed — {old[:60]!r} not found")
        t = t.replace(old, new, 1)
    return t


def clients_dir(override: str | None = None) -> str | None:
    return override or os.environ.get("CINE_CLIENTS") or cine_home.config_dir("clients_dir")


def apply_retake_factor(costs: dict, factor) -> dict:
    """(wave 2c) The studio's measured retake factor pre-fills a NEW client's cost file: each preset's `retry` becomes
    max(template, factor), so a studio answer can only raise an estimate, never lower it."""
    if factor is None:
        return costs
    for pr in ((costs or {}).get("presets") or {}).values():
        if isinstance(pr, dict) and isinstance(pr.get("retry"), (int, float)):
            pr["retry"] = max(float(pr["retry"]), float(factor))
    return costs


def make(ans: dict, cdir: str | None = None, check_open: bool = True) -> tuple[list, list]:
    """Returns (files written or kept, problems). Writes nothing when there is a problem."""
    a = with_defaults(ans)
    P = problems(a)
    cdir = clients_dir(cdir)
    if not cdir or not os.path.isdir(cdir):
        P.append("no clients folder: run /cinematographly:setup first")
    if P:
        return [], P
    slug = a["slug"]
    out = {f"{slug}.md": render(a)}
    for kind in ("costs", "script"):
        d = json.load(open(os.path.join(TEMPLATES, f"{kind}._TEMPLATE.json"), encoding="utf-8"))
        if "client" in d:
            d["client"] = slug
        if kind == "costs":
            apply_retake_factor(d, studio.load().get("retake_factor"))
        out[f"{kind}.{slug}.json"] = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    for f, body in out.items():
        p = os.path.join(cdir, f)
        if os.path.exists(p) and open(p, encoding="utf-8").read() != body:
            P.append(f"{f} already exists with other content — not overwritten (edit it by hand, or pick a new slug)")
    if P:
        return [], P
    if check_open:
        with tempfile.TemporaryDirectory() as td:          # prove it opens a concept-only job before writing
            tc = os.path.join(td, "clients"); os.makedirs(tc)
            for f, body in out.items():
                open(os.path.join(tc, f), "w", encoding="utf-8").write(body)
            jobs = os.path.join(td, "jobs"); os.makedirs(jobs)
            env = {**os.environ, "CINE_CLIENTS": tc, "CINE_HOME": os.path.join(td, "home")}
            env.pop("CINE_STUDIO", None)
            r = subprocess.run([sys.executable, os.path.join(HERE, "new_job.py"), slug, "check", "--jobs-dir", jobs],
                               capture_output=True, text=True, env=env)
            if r.returncode != 0:
                return [], ["the profile does not open a job yet: " + (r.stderr or r.stdout).strip()[-400:]]
    done = []
    for f, body in out.items():
        p = os.path.join(cdir, f)
        if not os.path.exists(p):
            open(p, "w", encoding="utf-8").write(body)
        done.append(p)
    return done, []


def selftest() -> int:
    # (wave 2c) the studio retake factor can only raise a new client's estimates
    _c = {"presets": {"economy": {"retry": 1.15}, "quality": {"retry": 1.3}}}
    apply_retake_factor(_c, 1.5)
    assert _c["presets"]["quality"]["retry"] == 1.5 and _c["presets"]["economy"]["retry"] == 1.5, _c
    _c = {"presets": {"economy": {"retry": 1.15}, "quality": {"retry": 1.3}}}
    apply_retake_factor(_c, 1.2)
    assert _c["presets"]["quality"]["retry"] == 1.3 and _c["presets"]["economy"]["retry"] == 1.2, "floored at the template"
    assert apply_retake_factor({"presets": {"quality": {"retry": 1.3}}}, None)["presets"]["quality"]["retry"] == 1.3
    ans = {"name": "Northwind Bikes", "slug": "northwind", "what": "a bicycle repair shop with a café",
           "default_mode": "B", "format_lock": "open", "audio_text_lock": "lines may be reworded",
           "overlay_policy": "captions only", "retired_tools": "none", "verification_policy": "per-stage-human",
           "approver": "Sam Reyes", "delivery_format": "vertical-1080", "claims_category": "none"}
    with tempfile.TemporaryDirectory() as td:
        cd = os.path.join(td, "clients"); os.makedirs(cd)
        os.environ.pop("CINE_STUDIO", None)
        files, P = make(ans, cd)
        assert not P and len(files) == 3, P
        prof = open(os.path.join(cd, "northwind.md"), encoding="utf-8").read()
        assert "**Named approver:** Sam Reyes." in prof and "`per-stage-human`" in prof and "`vertical-1080`" in prof
        before = {f: open(os.path.join(cd, f), "rb").read() for f in os.listdir(cd)}
        files, P = make(ans, cd)
        assert not P and {f: open(os.path.join(cd, f), "rb").read() for f in os.listdir(cd)} == before, "byte-identical"
        files, P = make(dict(ans, what="something else"), cd)
        assert P and "not overwritten" in P[0], P
        for k, v, why in (("approver", "the shop's owner", "a role"), ("approver", "Claude", "the agent"),
                          ("approver", "", "empty"), ("verification_policy", "lenient", "a bad policy"),
                          ("delivery_format", "cinema-8k", "an unknown format"), ("slug", "Bad Slug", "a bad slug"),
                          ("default_mode", "Z", "a bad mode"), ("language", "Romanian", "a second language")):
            case = dict(ans, slug="other"); case[k] = v
            files, P = make(case, cd)
            assert P and not files and not os.path.exists(os.path.join(cd, "other.md")), (why, P)
        files, P = make(dict(ans, slug="opens", format_lock="TBD"), cd)
        assert P and "does not open" in P[0] and not os.path.exists(os.path.join(cd, "opens.md")), \
            "a profile the gate would refuse is not written"
        # studio defaults pre-fill what the person did not answer
        st = os.path.join(td, "studio"); os.makedirs(st); os.environ["CINE_STUDIO"] = st
        try:
            json.dump({"approvers": ["Dana Ito"], "default_policy": "gated", "retake_factor": 1.5},
                      open(os.path.join(st, "studio.json"), "w"))
            a2 = {k: v for k, v in ans.items() if k not in ("approver", "verification_policy")}
            files, P = make(dict(a2, slug="second"), cd)
            _cf = json.load(open(os.path.join(cd, "costs.second.json"), encoding="utf-8"))["presets"]
            assert _cf["quality"]["retry"] == 1.5 and _cf["economy"]["retry"] == 1.5, "(wave 2c) the studio factor pre-fills"
            assert json.load(open(os.path.join(cd, "costs.northwind.json"), encoding="utf-8"))["presets"]["quality"][
                "retry"] == 1.3, "an existing client's cost file is not rewritten"
            p2 = open(os.path.join(cd, "second.md"), encoding="utf-8").read()
            assert not P and "**Named approver:** Dana Ito." in p2 and "`gated`" in p2, P
        finally:
            os.environ.pop("CINE_STUDIO", None)
    print("selftest OK — a profile from answers opens a concept-only job; the same answers leave it byte-identical, "
          "other answers are refused; a role, the agent or nobody as approver, a bad policy, format, slug or mode and a "
          "second language are refused before anything is written; studio defaults fill what was not answered")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=("questions", "make"))
    ap.add_argument("--answers"); ap.add_argument("--clients-dir"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "questions":
        d = with_defaults({})
        rows = [{"key": k, "question": q, "required": r, "default": d.get(k)} for k, q, r, _ in QUESTIONS]
        if a.json:
            print(json.dumps(rows, indent=1, ensure_ascii=False))
        else:
            for r in rows:
                print(f"  {'*' if r['required'] else ' '} {r['key']}: {r['question']}"
                      + (f"   (studio default: {r['default']})" if r["default"] else ""))
        return 0
    if a.cmd == "make":
        if not a.answers:
            print("make needs --answers FILE.json", file=sys.stderr); return 2
        try:
            ans = json.load(open(a.answers, encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"REFUSED: cannot read {a.answers}: {e}", file=sys.stderr); return 2
        files, P = make(ans if isinstance(ans, dict) else {}, a.clients_dir)
        if P:
            print("REFUSED (nothing written):\n  - " + "\n  - ".join(P), file=sys.stderr); return 1
        print("client ready:\n  " + "\n  ".join(files))
        print(f"next: /cinematographly:new-job {ans['slug']} <slug> — and fill in the rest of the profile over time")
        return 0
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
