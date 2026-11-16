#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""studio.py — the studio's own answers, shared by everyone who works in the studio folder. (3.1)

Stored in `<studio>/studio.json` (the studio folder setup made; `CINE_STUDIO` overrides; `~/.cinematographly/config.json`
names it). The answers PRE-FILL new clients and new jobs; they never raise a cap, never approve and never clear a
check. The gate reads three of them, and only to add a stop: a studio "no" on music licence or likeness blocks an
export, and the monthly credit ceiling (wave 2c) makes a person confirm a Higgsfield call that would take the
studio's month past it.

Production settings (wave 2c; PLAN-SETTINGS-v2/v3): `monthly_credit_ceiling` (a stop; setting or lowering it applies
at once, raising or removing it needs the person's words: `--by` + `--quote`, found in a human turn of this session),
`default_regens` (0-2, a pre-fill for `gate.py allow`), `retake_factor` (1.0-3.0, pre-fills a NEW client's cost file
and can only raise its estimates), `second_opinion` (another model for critiques; text only, never a gate).

The month's spend is one small file per Higgsfield submission in `<studio>/spend/YYYY-MM/` (UTC), so two machines
sharing the folder over a sync service never write the same file. An agent with a shell can edit any file: these
records catch mistakes and quiet edits, and an edit shows in the session transcript. The control on a raise is the
person's quoted words.

  studio.py questions [--json]          # what is asked, with the current answers
  studio.py set --answers FILE.json [--by NAME --quote "their words"]   # merge answers (validated)
  studio.py month [--json]              # this UTC month's recorded spend against the ceiling
  studio.py --selftest
"""
from __future__ import annotations
import argparse, datetime as dt, glob, json, os, re, secrets, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cine_home  # noqa: E402

FILE = "studio.json"
POLICIES = ("per-stage-human", "gated", "standing")
YES_NO = ("yes", "no", "unknown")
from switches import FINISH_LOOKS  # noqa: E402  (one list: the looks a studio may pre-fill)
class _RoleTest:
    """A role, a group or the agent where a person's name belongs. (3.1 review) Real names are not roles: "An Nguyen",
    "Ai Tanaka" and "Claude Monet" pass; "the owner", "our team", "Creative Director", "Claude", "AI", "the agent" do not.
    Kept as `.search(name)` so every caller reads the same rule."""
    ROLE_WORDS = {"owner", "founder", "manager", "client", "team", "director", "lead", "agent", "assistant", "bot",
                  "chatbot"}
    WHOLE = {"claude", "ai", "an ai", "a bot", "the ai", "the agent", "assistant", "the assistant", "gpt", "chatgpt",
             "model", "the model", "llm"}

    def search(self, name) -> bool:
        s = re.sub(r"\s+", " ", str(name or "")).strip().lower()
        if not s:
            return False
        if s in self.WHOLE or re.match(r"^(?:the|our|my|their|your)\b", s):
            return True
        return any(w in self.ROLE_WORDS for w in re.findall(r"[a-z]+", s))


ROLE_RE = _RoleTest()
# key, the question asked in plain words, kind
QUESTIONS = [
    ("approvers", "Who signs off work in this studio? One or more people's names (a person, not a role).", "names"),
    ("default_policy", "How closely should a person check each stage by default: per-stage-human (every stage), "
                       "gated (machine first, people at the key points) or standing (variants ship on a standing yes)?",
     "policy"),
    ("platforms", "Which platforms do you deliver to (e.g. TikTok, Instagram Reels, YouTube Shorts, Meta ads)?", "list"),
    ("brand_kit", "Where do client brand kits usually live (a folder, a drive link)?", "text"),
    ("claims_signer", "Who checks health, finance or performance claims before anything ships (a name)?", "name"),
    ("music_library", "Where does licensed music come from (a library, a subscription, commissioned)?", "text"),
    ("music_licence", "Is that music cleared for paid ads? (yes / no / unknown)", "yesno"),
    ("likeness_release", "Do you get signed releases for real people's faces and voices? (yes / no / unknown)", "yesno"),
    ("ai_disclosure", "How do you disclose AI-made video (platform toggle, on-screen line, both, decided per client)?",
     "text"),
    ("vendor_account_holder", "Who holds the AI-generation account and its credits (a name)?", "name"),
    ("monthly_credit_ceiling", "Production settings: how many Higgsfield credits may the studio spend in a calendar month "
                               "(UTC), across all jobs, before a person must confirm each further call? (Kling bills "
                               "its own account and is not counted.) Leave it out for no studio stop.", "ceiling"),
    ("default_regens", "Production settings: when someone approves a batch of shots, how many extra tries per shot may "
                       "that approval cover by default: 0, 1 or 2? (The house default is 2; a person can still name "
                       "another number, up to 5, for one approval.)", "regens"),
    ("retake_factor", "Production settings: from your own jobs, how much should estimates add for takes you throw "
                      "away? 1.5 means half again. It can only raise the house numbers (quality 1.3, economy 1.15) "
                      "and only for clients set up from now on.", "factor"),
    ("second_opinion", "Optional: do you want another model to critique scripts and cuts? Name the tool you already "
                       "have connected, and say whether it may see client material (yes / no). Or none.", "model"),
    ("escalation_contact", "Who decides when something is unclear or goes wrong mid-job (a name)?", "name"),
    ("data_retention", "How long do you keep client material after delivery?", "text"),
    ("finishing_looks", "Finishing looks your studio uses by default on new jobs (any of: "
                        + ", ".join(FINISH_LOOKS) + "), each with a reason; or none", "looks"),
]
KEYS = {k for k, _, _ in QUESTIONS}
CEILING = "monthly_credit_ceiling"
CHANGES = "studio-changes.jsonl"
SPEND = "spend"


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def studio_dir() -> str | None:
    env = os.environ.get("CINE_STUDIO")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return cine_home.config_dir("studio")


def check_dirs() -> list:
    """(3.1 build review 1, Grok HIGH) Every studio folder a CHECK must read: the one `CINE_STUDIO` names AND the one
    setup recorded in the config. A command run with `CINE_STUDIO=/tmp/empty` cannot point a check away from the
    studio that said no: each check applies the strictest answer across both."""
    out = []
    env = os.environ.get("CINE_STUDIO")
    for d in ((os.path.abspath(os.path.expanduser(env)) if env else None), cine_home.config_dir("studio")):
        if d and d not in out:
            out.append(d)
    return out


def path(sdir: str | None = None) -> str | None:
    d = sdir or studio_dir()
    return os.path.join(d, FILE) if d else None


def _raw(sdir: str | None = None) -> dict:
    p = path(sdir)
    try:
        d = json.load(open(p, encoding="utf-8")) if p else {}
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def load_raw(sdir: str | None = None) -> dict:
    """The file as written, unchecked: for a reader that refuses a bad value itself (new_job's finishing looks), so a
    hand-edited bad answer stops a job instead of being quietly ignored."""
    return _raw(sdir)


def load(sdir: str | None = None) -> dict:
    """The answers on disk, each re-checked under the rules `set` applies: a hand-edited value that `set` would refuse
    is read as unanswered (see disk_problems)."""
    return {k: v for k, v in _raw(sdir).items() if k in KEYS and v is not None and not validate({k: v})}


def disk_problems(sdir: str | None = None) -> list:
    """What on disk `load` ignored, in words, for `gate.py status`."""
    raw = _raw(sdir)
    return [f"studio.json {p_} — ignored" for k, v in raw.items() if v is not None for p_ in validate({k: v})]


def validate(ans: dict) -> list:
    """Problems with a set of answers. Unknown keys (an envelope, a budget, a switch outside the looks) refuse."""
    probs = []
    for k, v in ans.items():
        if k not in KEYS:
            probs.append(f"{k!r} is not a studio question (a budget or envelope is set per job, never here)")
            continue
        kind = next(kd for kk, _, kd in QUESTIONS if kk == k)
        if kind == "names":
            names = v if isinstance(v, list) else [v]
            if not names or any(not isinstance(n, str) or not n.strip() or ROLE_RE.search(n) for n in names):
                probs.append(f"{k}: each must be a person's name, not a role or the agent ({v!r})")
        elif kind == "name":
            if not isinstance(v, str) or not v.strip() or ROLE_RE.search(v):
                probs.append(f"{k}: a person's name, not a role ({v!r})")
        elif kind == "policy" and v not in POLICIES:
            probs.append(f"{k}: one of {', '.join(POLICIES)}")
        elif kind == "yesno" and v not in YES_NO:
            probs.append(f"{k}: yes, no or unknown")
        elif kind == "list" and not (isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)):
            probs.append(f"{k}: a list of names")
        elif kind == "ceiling" and not (v is None or (_num(v) and v > 0)):
            probs.append(f"{k}: a number of credits above 0 (or null to remove it)")
        elif kind == "regens" and not (_num(v) and int(v) == v and 0 <= v <= 2):
            probs.append(f"{k}: 0, 1 or 2 (the house default is 2; a studio default can only lower it)")
        elif kind == "factor" and not (_num(v) and 1.0 <= v <= 3.0):
            probs.append(f"{k}: a number from 1.0 to 3.0 (1.5 = half again)")
        elif kind == "model" and v != "none" and not (
                isinstance(v, dict) and set(v) == {"tool", "client_material"} and isinstance(v["tool"], str)
                and v["tool"].strip() and v["client_material"] in ("yes", "no")):
            probs.append(f"{k}: none, or {{\"tool\": \"<name>\", \"client_material\": \"yes\" or \"no\"}}")
        elif kind == "text" and not (isinstance(v, str) and v.strip()):
            probs.append(f"{k}: some words")
        elif kind == "looks":
            if v in ("none", [], {}):
                continue
            if not isinstance(v, dict):
                probs.append(f"{k}: {{look: reason}} or none")
                continue
            for look, why in v.items():
                if look not in FINISH_LOOKS:
                    probs.append(f"{k}: {look!r} is not a finishing look; studio defaults may only pre-fill "
                                 f"{', '.join(FINISH_LOOKS)} (every other house rule is lifted per job, with a reason)")
                elif not isinstance(why, str) or len(why.split()) < 3:
                    probs.append(f"{k}: {look} needs a reason of three words or more")
    return probs


def _quote_ok(quote: str) -> str:
    import gate  # noqa: E402  (the allowance's own check: a human turn of this session's transcript)
    return gate.quote_in_transcript(quote)


def ceiling_raise_refusal(old, new, by: str | None, quote: str | None, check=_quote_ok) -> str | None:
    """None when this change to the ceiling may be written. Setting one or lowering it only adds a stop; raising or
    removing it needs the person's own words, checked like an allowance quote."""
    if old is None or (new is not None and new <= old):
        return None
    what = "remove" if new is None else f"raise it from {old:g} to {new:g}"
    if not (by or "").strip() or ROLE_RE.search(by or "") or not (quote or "").strip():
        return (f"to {what} the monthly ceiling, pass --by \"<the person's name>\" --quote \"<their words>\": raising "
                f"or removing a stop needs a person's own words")
    if len(quote.split()) < 2:
        return f"to {what} the monthly ceiling the quote must be the person's own sentence, two words or more"
    appr = load().get("approvers") or []
    if appr and by.strip().lower() not in {a_.strip().lower() for a_ in appr}:
        return (f"to {what} the monthly ceiling --by must be one of the studio's approvers ({', '.join(appr)}), "
                f"not {by.strip()!r}")
    v = check(quote.strip())
    if v != "verified":
        return (f"to {what} the monthly ceiling the quote must appear in a human turn of this session ({v}); ask the "
                f"person once and record what they wrote")
    return None


def save(ans: dict, sdir: str | None = None, by: str | None = None, quote: str | None = None,
         check=_quote_ok) -> tuple[str | None, list]:
    probs = validate(ans)
    p = path(sdir)
    if not p:
        probs.append("no studio folder: run /cinematographly:setup first (or set CINE_STUDIO)")
    cur = _raw(sdir)
    old_c = load(sdir).get(CEILING)
    if not probs and CEILING in ans:
        r_ = ceiling_raise_refusal(old_c, ans[CEILING], by, quote, check)
        if r_:
            probs.append(r_)
    if probs:
        return None, probs
    cur.update(ans)
    if CEILING in ans and ans[CEILING] is None:
        cur.pop(CEILING, None)
    tmp = p + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cur, fh, indent=2, ensure_ascii=False); fh.write("\n")
    os.replace(tmp, p)
    if CEILING in ans and ans[CEILING] != old_c:              # a diary of the stop, not the control (the quote is)
        try:
            with open(os.path.join(os.path.dirname(p), CHANGES), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": _utc(), "key": CEILING, "old": old_c, "new": ans[CEILING],
                                     **({"by": by.strip(), "quote": (quote or "").strip()[:200]} if by else {})},
                                    ensure_ascii=False) + "\n")
        except OSError:
            pass
    return p, []


# --- the studio's month (wave 2c) ------------------------------------------------------------------------------------
def _utc(t: float | None = None) -> str:
    return dt.datetime.fromtimestamp(t if t is not None else dt.datetime.now(dt.timezone.utc).timestamp(),
                                     dt.timezone.utc).replace(microsecond=0).isoformat()


def month_utc(t: float | None = None) -> str:
    return _utc(t)[:7]


def ceiling(sdir: str | None = None):
    """The enforced monthly ceiling in credits, or None."""
    return load(sdir).get(CEILING)


def ceiling_state(sdir: str | None = None) -> tuple:
    if sdir is None:
        cs, probs = [], []
        for d_ in check_dirs():
            c_, p_ = _ceiling_state_one(d_)
            if p_:
                probs.append(p_)
            elif c_ is not None:
                cs.append(c_)
        return (min(cs) if cs else None), (probs[0] if probs else None)
    return _ceiling_state_one(sdir)


def _ceiling_state_one(sdir: str) -> tuple:
    """(ceiling or None, problem or None). A studio.json that exists but cannot be read, or whose ceiling is present
    but invalid (a string, a half-written file, a sync conflict), is a PROBLEM: the gate asks rather than dropping the
    stop (plan review round 3). A file that does not exist is no ceiling."""
    p = path(sdir)
    if not p or not os.path.exists(p):
        return None, None
    try:
        d = json.load(open(p, encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError("not an object")
    except (OSError, ValueError) as e:
        return None, f"studio.json cannot be read ({type(e).__name__}), so the monthly ceiling cannot be checked"
    if CEILING in d and d[CEILING] is not None and validate({CEILING: d[CEILING]}):
        return None, f"studio.json monthly_credit_ceiling is {d[CEILING]!r}, not a number of credits"
    return d.get(CEILING), None


def default_regens(sdir: str | None = None):
    """The studio's regens pre-fill (0-2), or None for the house default. Across every studio folder a check reads,
    the lowest wins."""
    vs = [load(d_).get("default_regens") for d_ in ([sdir] if sdir else check_dirs())]
    vs = [int(v) for v in vs if v is not None]
    return min(vs) if vs else None


def record_spend(job: str, tool: str, credits, kind: str = "submitted", sdir: str | None = None,
                 t: float | None = None) -> str | None:
    """One immutable file per Higgsfield submission, in every studio folder a check reads. None (and nothing written)
    without a studio folder."""
    if sdir is None:
        got = [record_spend(job, tool, credits, kind, d_, t) for d_ in check_dirs()]
        got = [g_ for g_ in got if g_]
        return got[0] if got else None
    d = sdir
    if not os.path.isdir(d):
        return None
    m = month_utc(t)
    folder = os.path.join(d, SPEND, m)
    stamp = _utc(t).replace(":", "").replace("+0000", "Z")
    fp = os.path.join(folder, f"{stamp}-{secrets.token_hex(4)}.json")
    c = float(credits) if _num(credits) and credits >= 0 else None
    try:
        os.makedirs(folder, exist_ok=True)
        tmp = fp + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"ts_utc": _utc(t), "month": m, "job": job, "tool": tool, "credits": c, "kind": kind}, fh)
        os.replace(tmp, fp)
    except OSError:
        return None
    return fp


def _months_near(m: str) -> list:
    y, mo = int(m[:4]), int(m[5:7])
    out = []
    for d_ in (-1, 0, 1):
        yy, mm = y + (mo - 1 + d_) // 12, (mo - 1 + d_) % 12 + 1
        out.append(f"{yy:04d}-{mm:02d}")
    return out


def month_total(month: str | None = None, sdir: str | None = None) -> dict:
    """{month, credits, unpriced, voice_unpriced, unreadable, events}. A file counts in the month its own `month`
    field names (the folders next door are read too, so a misfiled event still counts once, in its own month)."""
    m = month or month_utc()
    if sdir is None:
        per = [month_total(m, d_) for d_ in check_dirs()]
        if not per:
            return {"month": m, "credits": 0.0, "unpriced": 0, "voice_unpriced": 0, "unreadable": 0, "events": 0}
        # every check folder holds the same events; the largest record wins (a folder cannot be emptied to pass)
        return {"month": m, **{k: max(p_[k] for p_ in per) for k in ("credits", "unpriced", "voice_unpriced",
                                                                       "unreadable", "events")}}
    d = sdir
    out = {"month": m, "credits": 0.0, "unpriced": 0, "voice_unpriced": 0, "unreadable": 0, "events": 0}
    for mm in _months_near(m):
        for fp in glob.glob(os.path.join(d, SPEND, mm, "*.json")):
            try:
                ev = json.load(open(fp, encoding="utf-8"))
                if not isinstance(ev, dict):
                    raise ValueError("not an object")
            except (OSError, ValueError):
                if mm == m:
                    out["unreadable"] += 1
                continue
            if ev.get("month") != m:
                continue
            out["events"] += 1
            c = ev.get("credits")
            if _num(c) and c >= 0:
                out["credits"] += float(c)
            elif str(ev.get("tool") or "").endswith(("generate_audio", "generate_audio_batch")):
                out["voice_unpriced"] += 1
            else:
                out["unpriced"] += 1
    return out


OPTIONAL = ("monthly_credit_ceiling", "default_regens", "retake_factor", "second_opinion")   # a house default applies


def unanswered(sdir: str | None = None, required_only: bool = False) -> list:
    a = load(sdir)
    return [k for k, _, _ in QUESTIONS if k not in a and not (required_only and k in OPTIONAL)]


def month_line(mt: dict | None = None, c=None) -> str:
    mt = mt or month_total()
    extra = [f"{mt['unpriced']} unpriced" if mt["unpriced"] else "",
             f"{mt['voice_unpriced']} voice call(s) unpriced" if mt["voice_unpriced"] else "",
             f"{mt['unreadable']} unreadable record(s)" if mt["unreadable"] else ""]
    return (f"studio month {mt['month']} (UTC) {mt['credits']:g}" + (f" / {c:g} cr" if c is not None else
                                                                      " cr (no ceiling)")
            + "".join(f", {e}" for e in extra if e) + " · Kling is a separate account; spend-class tools ask every "
            "time and are not counted")


def export_refusals(stills: bool = False, sdir: str | None = None) -> list:
    if sdir is None:
        out_: list = []
        for d_ in check_dirs():
            out_ += [x for x in _export_refusals_one(stills, d_) if x not in out_]
        return out_
    return _export_refusals_one(stills, sdir)


def _export_refusals_one(stills: bool, sdir: str) -> list:
    """(3.1, build review 1) Why the studio's own answers stop an export, in words; [] when they do not. An explicit
    "no" blocks (music_licence, likeness_release; a stills job has no music, so only likeness). A studio.json that
    exists but cannot be read, or holds one of these answers in a form `set` would refuse ("No", " no"), also blocks:
    a check that cannot read its answer refuses rather than passing (the same rule as the monthly ceiling)."""
    keys = (("likeness_release", "the studio does NOT get likeness releases for real people (studio.json "
                                 "likeness_release: no)"),) + (() if stills else (
            ("music_licence", "the studio's music is NOT cleared for paid use (studio.json music_licence: no)"),))
    p = path(sdir)
    if not p or not os.path.exists(p):
        return []
    try:
        raw = json.load(open(p, encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("not an object")
    except (OSError, ValueError) as e:
        return [f"studio.json cannot be read ({type(e).__name__}), so the studio's music and likeness answers cannot "
                f"be checked; fix it with `studio.py set`"]
    out = []
    for k, why in keys:
        v = raw.get(k)
        if v is None:
            continue
        if v not in YES_NO:
            out.append(f"studio.json {k} is {v!r}, not yes / no / unknown; fix it with `studio.py set`")
        elif v == "no":
            out.append(why)
    return out


def answer_no(key: str, sdir: str | None = None) -> bool:
    """True only for an explicit studio "no" (music_licence, likeness_release). Never a pass for "yes"."""
    return load(sdir).get(key) == "no"


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        os.environ["CINE_STUDIO"] = td
        try:
            assert unanswered() == [k for k, _, _ in QUESTIONS]
            good = {"approvers": ["Sam Reyes", "Dana Ito"], "default_policy": "gated", "music_licence": "no",
                    "monthly_credit_ceiling": 3000, "finishing_looks": {"finish-texture": "grain on every master"}}
            p, probs = save(good)
            assert p and not probs, probs
            assert load()["approvers"] == ["Sam Reyes", "Dana Ito"] and answer_no("music_licence")
            assert not answer_no("likeness_release"), "unanswered is not a no"
            for ok_name in ("An Nguyen", "Ai Tanaka", "Claude Monet", "A. J. Okafor"):
                assert not ROLE_RE.search(ok_name), f"(3.1 review) {ok_name} is a person's name"
            for role in ("the owner", "Our team", "Creative Director", "Claude", "AI", "the agent", "my assistant"):
                assert ROLE_RE.search(role), f"{role} is not a person"
            for bad, why in (({"approvers": ["the shop's owner"]}, "a role"), ({"approvers": ["Claude"]}, "the agent"),
                             ({"envelope": 500}, "an envelope"), ({"default_policy": "lenient"}, "a bad policy"),
                             ({"finishing_looks": {"floor-1080": "we like it a lot"}}, "a non-look switch"),
                             ({"finishing_looks": {"light-leak": "nice"}}, "a short reason"),
                             ({"music_licence": "maybe"}, "a bad yes/no")):
                p, probs = save(bad)
                assert p is None and probs, (why, probs)
            assert load()["default_policy"] == "gated", "a refused write changes nothing"
            # (wave 2c) production settings
            for bad, why in (({"default_regens": 3}, "regens 3"), ({"default_regens": -1}, "regens -1"),
                             ({"default_regens": True}, "regens true"), ({"monthly_credit_ceiling": True}, "ceiling true"),
                             ({"monthly_credit_ceiling": "3000"}, "ceiling as text"), ({"retake_factor": 0.9}, "0.9"),
                             ({"second_opinion": {"tool": "x", "client_material": "maybe"}}, "maybe")):
                p, probs = save(bad)
                assert p is None and probs, (why, probs)
            ok_q = lambda q: "verified"
            no_q = lambda q: "not-found"
            assert save({"monthly_credit_ceiling": 2000}, check=no_q)[1] == [], "lowering 3000 → 2000 needs no quote"
            assert save({"monthly_credit_ceiling": 2500}, check=ok_q)[1], "a raise without --by/--quote is refused"
            assert save({"monthly_credit_ceiling": 2500}, by="Sam Reyes", quote="raise it", check=no_q)[1], \
                "a raise whose quote is not in the transcript is refused"
            assert ceiling() == 2000, "a refused raise changes nothing"
            assert save({"monthly_credit_ceiling": 2500}, by="Sam Reyes", quote="yes", check=ok_q)[1], \
                "(3.1 review) a one-word quote does not raise the ceiling"
            assert save({"monthly_credit_ceiling": 2500}, by="Pat Lee", quote="raise it to 2500", check=ok_q)[1], \
                "(3.1 review) --by must be one of the studio's approvers"
            assert save({"monthly_credit_ceiling": 2500}, by="Sam Reyes", quote="raise it to 2500", check=ok_q)[1] == []
            assert save({"monthly_credit_ceiling": None}, check=ok_q)[1], "removing it needs words too"
            assert save({"monthly_credit_ceiling": None}, by="Sam Reyes", quote="drop the cap", check=ok_q)[1] == []
            assert ceiling() is None and CEILING not in _raw(), "removed"
            ch = [json.loads(l_) for l_ in open(os.path.join(td, CHANGES), encoding="utf-8")]
            assert [(r_["old"], r_["new"]) for r_ in ch] == [(None, 3000), (3000, 2000), (2000, 2500), (2500, None)], ch
            assert save({"monthly_credit_ceiling": 100}, check=no_q)[1] == [], "a first ceiling needs no quote"
            raw = _raw(); raw["default_regens"] = 9
            json.dump(raw, open(path(), "w"))
            assert "default_regens" not in load() and default_regens() is None and disk_problems(), \
                "a hand-edited bad value is read as unanswered and reported"
            # the month: one file per event, UTC, its own month field, never subtracting
            for _ in range(4):
                assert record_spend("j", "mcp__Higgsfield__generate_image", 10, t=1793750400.0)   # 2026-11-04 UTC
            record_spend("j", "mcp__Higgsfield__generate_image", -50, t=1793750400.0)
            record_spend("j", "mcp__Higgsfield__generate_audio", None, t=1793750400.0)
            mis = os.path.join(td, SPEND, "2026-11", "misfiled.json")
            json.dump({"month": "2026-12", "credits": 999}, open(mis, "w"))
            mt = month_total("2026-11")
            assert mt["credits"] == 40 and mt["unpriced"] == 1 and mt["voice_unpriced"] == 1, mt
            assert month_total("2026-12")["credits"] == 999, "a misfiled event counts once, in its own month"
            open(os.path.join(td, SPEND, "2026-11", "broken.json"), "w").write("{")
            assert month_total("2026-11")["unreadable"] == 1
            os.environ["TZ"] = "Pacific/Kiritimati"; time.tzset()          # UTC+14: 20:00 UTC on the 30th is the 1st
            try:
                fp = record_spend("j", "mcp__Higgsfield__generate_image", 1, t=1796068800.0)  # 2026-11-30 20:00 UTC
                assert "/2026-11/" in fp.replace(os.sep, "/") and json.load(open(fp))["month"] == "2026-11", fp
            finally:
                os.environ.pop("TZ", None); time.tzset()
            assert ceiling_state() == (100, None)
            open(path(), "w").write("{")
            assert ceiling_state()[1] and "cannot be read" in ceiling_state()[1], "a half-written file is a problem"
        finally:
            os.environ.pop("CINE_STUDIO", None)
    print("selftest OK — answers saved in the studio folder; a role or the agent as approver, an envelope, a bad "
          "policy, a switch that is not a finishing look, a short reason and a bad yes/no are refused and change "
          "nothing; only an explicit \"no\" reads as no; production settings: regens 0-2, a numeric ceiling, a "
          "retake factor 1-3; lowering the ceiling is free, raising or removing it needs words in the transcript; "
          "a hand-edited bad value is ignored and reported; the month is UTC, one file per event, never subtracting, "
          "a misfiled event counted once, an unreadable one reported; a half-written studio.json is a problem")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=("questions", "set", "month"))
    ap.add_argument("--answers"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--by"); ap.add_argument("--quote")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "questions":
        cur = load()
        rows = [{"key": k, "question": q, "answer": cur.get(k)} for k, q, _ in QUESTIONS]
        if a.json:
            print(json.dumps({"studio": studio_dir(), "questions": rows}, indent=1, ensure_ascii=False))
        else:
            print(f"studio: {studio_dir() or '(none — run setup)'}")
            for r in rows:
                print(f"  {'✓' if r['answer'] is not None else '·'} {r['key']}: {r['question']}"
                      + (f"\n      now: {r['answer']}" if r["answer"] is not None else ""))
        return 0
    if a.cmd == "set":
        if not a.answers:
            print("set needs --answers FILE.json", file=sys.stderr); return 2
        try:
            ans = json.load(open(a.answers, encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"REFUSED: cannot read {a.answers}: {e}", file=sys.stderr); return 2
        p, probs = save(ans if isinstance(ans, dict) else {"_": ans}, by=a.by, quote=a.quote)
        if probs:
            print("REFUSED (nothing written):\n  - " + "\n  - ".join(probs), file=sys.stderr); return 1
        print(f"saved {len(ans)} answer(s) in {p}; still unanswered: {', '.join(unanswered()) or 'none'}")
        return 0
    if a.cmd == "month":
        mt, c = month_total(), ceiling()
        if a.json:
            print(json.dumps({**mt, "ceiling": c}, indent=1)); return 0
        print(month_line(mt, c)); return 0
    ap.print_help(); return 2


if __name__ == "__main__":
    sys.exit(main())
