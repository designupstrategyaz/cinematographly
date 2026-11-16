#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Cinematographly-Studio
# Cinematographly · project id cgly-3f9c1e · see LICENSE and NOTICE
"""beat_plan.py — derive a script's BEAT COUNT from the client's numbers, instead of copying a template.

The house template used to show four scenes. ⛔ **Four was never a general answer** — it was one
retired client's format lock for a ~60s two-hander, and it survived into the template because a
number in an example looks like a rule. This tool replaces the number with the arithmetic that
produced it:

    body    = runtime - hook - cta
    beats   = round(body / beat_seconds)

Run it against that client's own spec (60s + 6s hook + 5s CTA + ~13s beats) and it returns 4 — which
is the point. The template was right for that brief and wrong as a default, and the only way to tell
those apart is to compute it.

⛔ **The FUNCTIONS are fixed; the COUNT is derived.** Every script needs a hook, at least one beat
that turns a value, and a resolve/CTA. How many turning beats fit is a property of the runtime, not
of the house style.

  plan  — emit the beat structure with timecodes and a per-line word budget

Refusals (the numbers are per-client and this tool will not invent them)
-----------------------------------------------------------------------
  * No `clients/script.<client>.json` and no explicit --runtime/--hook/--cta/--beat: refuses and
    lists exactly what it needs. Guessing a hook floor is how one client's answer becomes everyone's.
  * A runtime too short to hold hook + one beat + CTA: refuses and says what would fit.

What it cannot do
-----------------
- **It cannot tell you the beats are any good.** It sizes the container. Whether each beat turns a
  value, and whether the hook earns the next six seconds, is script-craft.md and a read-aloud.
- It does not know your client's beat length. `beat_seconds` is a measurable house fact (time one
  finished scene, wall to wall) — until it is measured, it is your estimate and the plan inherits
  that uncertainty.
- It says nothing about speaker alternation beyond echoing `speakers`; a monologue has no
  alternation to keep and its rhythm test is inevitability, not banter.

Usage
-----
  python3 beat_plan.py plan --client acme
  python3 beat_plan.py plan --client acme --runtime 45
  python3 beat_plan.py plan --runtime 45 --hook 4 --cta 5 --beat 11 --words-per-line 15
  python3 beat_plan.py plan --client acme --json

Exit codes: 0 planned · 1 refused · 2 usage/IO error.
"""
from __future__ import annotations
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import client_files  # noqa: E402  (where a client's script numbers are on this machine)
WPS = 2.4          # spoken words per second — the figure estimate_duration.py and script_score.py use
PAUSE = 0.6        # seconds a line — they add this on top, so the budget below leaves room for it (v2.67.0)
NEEDED = ["runtime_target_s", "hook_seconds_min", "cta_seconds", "beat_seconds"]


def load_spec(client: str, *starts: str | None) -> dict | None:
    """`starts`: --from paths (v2.59.2), so a `_cine-clients/` folder above the job is found from anywhere."""
    p = client_files.find(f"script.{client}.json", *starts)  # CINE_CLIENTS, a `_cine-clients/` folder, then the plugin's
    if not p:
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def plan(runtime: float, hook: float, cta: float, beat: float,
         words_per_line: int | None, speakers: int | None) -> dict:
    body = runtime - hook - cta
    n = max(0, round(body / beat)) if beat > 0 else 0
    beats = []
    if n:
        each = body / n
        t = hook
        for i in range(n):
            if n == 1:
                fn = "TURN — the single value change the piece exists to make"
            elif i == 0:
                fn = "ESTABLISH — the situation the hook promised, made concrete"
            elif i == n - 1:
                fn = "RESOLVE — the value lands; proof or social proof if the mode uses it"
            else:
                fn = "TURN — one value changes (skepticism→interest, worry→relief)"
            beats.append({"n": i + 1, "start": round(t, 1), "end": round(t + each, 1),
                          "seconds": round(each, 1), "function": fn,
                          "speaker": (i % speakers) + 1 if speakers else None,
                          # (v2.67.0) words that fit the PRINTED window (whole seconds) with one line's pause, so
                          # a script that keeps to the budget does not trip script_score.py's two clocks
                          "word_budget": words_per_line or int(max(0.0, (round(t + each) - round(t)) - PAUSE) * WPS)})
            t += each
    return {"runtime_s": runtime, "hook_s": hook, "cta_s": cta, "beat_s": beat,
            "body_s": round(body, 1), "beats": n, "speakers": speakers,
            "hook_block": {"start": 0.0, "end": round(hook, 1),
                           "function": "HOOK — conflict, not demographic. It buys the next beat"},
            "cta_block": {"start": round(runtime - cta, 1), "end": round(runtime, 1),
                          "function": "CTA — the resolved state, in-world branding, one ask"},
            "scenes": beats}


def measured_reference(r: dict) -> list:
    """Advisory lines from assets/script-bands.json (v2.51, script corpus 2026-11-05): where real spots put the
    CTA and how many words they speak in this runtime. Printed, never enforced: the client's numbers decide."""
    try:
        with open(os.path.join(SKILL, "assets", "script-bands.json"), encoding="utf-8") as fh:
            B = json.load(fh)
    except (OSError, ValueError):
        return []
    A, L = B["ads"], B["long_brand_films"]
    rt, out = r["runtime_s"], []
    cta_share = (rt - r["cta_s"]) / rt if rt else 0
    if rt <= 45:
        cb = A["cta_start_share_15_30s"]
        out.append(f"CTA block starts at {cta_share:.0%} of the runtime; in 15-30 s spots the spoken CTA starts at "
                   f"{cb['p10']:.0%}-{cb['p90']:.0%} of the words (median {cb['median']:.0%})")
    else:
        out.append(f"CTA block starts at {cta_share:.0%}; in 60-120 s brand films the CTA mostly sits on the end card "
                   f"({L['spoken_cta']}), and where spoken it starts near {L['cta_start_share']['median']:.0%} of the words")
    wb = A["words_per_second"]
    out.append(f"spoken words at the measured pace: about {int(rt * wb['median'])} "
               f"({int(rt * wb['p10'])}-{int(rt * wb['p90'])}); award-annual spots speak about "
               f"{int(rt * A['words_per_second_award_annual']['median'])} and give the rest to picture")
    for secs, key in ((15, "spoken_words_15s"), (30, "spoken_words_30s")):
        if abs(rt - secs) <= max(2, secs * 0.1):
            b = A[key]
            out.append(f"real {secs}s spots: {b['p10']:.0f}-{b['p90']:.0f} spoken words (median {b['median']:.0f})")
    return out


def mss(t: float) -> str:
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}"


def header(label: str, blk: dict) -> str:
    """`[SCENE 1 — 0:06–0:19]` — whole seconds, the form the script template and script_score.py read."""
    return f"[{label} {mss(blk['start'])}–{mss(blk['end'])}]"


def selftest() -> int:
    # The retired client's own numbers must reproduce its own template — that is the validation.
    r = plan(64.0, 6.0, 5.0, 13.25, 15, 2)
    assert r["beats"] == 4, r["beats"]
    assert r["scenes"][0]["function"].startswith("ESTABLISH")
    assert r["scenes"][-1]["function"].startswith("RESOLVE")
    assert r["scenes"][1]["speaker"] == 2 and r["scenes"][2]["speaker"] == 1
    # (v2.67.0) the headers paste into a script as the clock reads them, and the budget fits the printed window
    assert header("SCENE 1 —", {"start": 6.0, "end": 19.4}) == "[SCENE 1 — 0:06–0:19]"
    assert header("HOOK", {"start": 0.0, "end": 6.0}) == "[HOOK 0:00–0:06]"
    u = plan(64.0, 6.0, 5.0, 13.25, None, 2)
    for b_ in u["scenes"]:
        win = round(b_["end"]) - round(b_["start"])
        assert b_["word_budget"] / WPS + PAUSE <= win, (b_, win)    # one line at the budget fits its window
    # A short UGC monologue must NOT come back as four.
    s = plan(35.0, 3.0, 4.0, 9.0, None, 1)
    assert s["beats"] == 3, s["beats"]
    assert all(b["speaker"] == 1 for b in s["scenes"])
    # A very short cut collapses to one turning beat, not a template.
    assert plan(20.0, 3.0, 4.0, 10.0, None, 1)["beats"] == 1
    assert plan(15.0, 6.0, 5.0, 13.0, None, 1)["beats"] == 0
    ref = measured_reference(plan(30.0, 4.0, 4.0, 11.0, None, 1))
    assert ref and "CTA block starts at 87%" in ref[0] and any("real 30s spots" in x for x in ref), ref
    assert "end card" in measured_reference(plan(90.0, 6.0, 6.0, 13.0, None, 1))[0]
    print("selftest OK — the retired 60s two-hander's own numbers return 4 (the template was a "
          "CALCULATION, not a rule); a 35s monologue returns 3; a 20s cut returns 1; the measured "
          "reference places the CTA and the word budget for short spots and long films")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan", help="derive the beat structure")
    p.add_argument("--client", help="reads script.<client>.json (your client folder, then the plugin's clients/)")
    p.add_argument("--from", dest="starts", action="append", default=[], metavar="PATH",
                   help="the job or script folder; a `_cine-clients/` folder above it is searched (repeatable)")
    p.add_argument("--runtime", type=float); p.add_argument("--hook", type=float)
    p.add_argument("--cta", type=float); p.add_argument("--beat", type=float)
    p.add_argument("--words-per-line", type=int); p.add_argument("--speakers", type=int)
    p.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd != "plan":
        ap.print_help(); return 2

    spec = load_spec(a.client, *a.starts) if a.client else None
    if a.client and spec is None:
        print(f"REFUSED: no script.{a.client}.json ({client_files.where_looked(*a.starts)}).\n"
              f"  Pass --from <job folder>, or copy clients/script._TEMPLATE.json into your client folder and fill it\n"
              f"  in. ⛔ This tool will not guess a\n"
              f"  hook floor or a beat length — those are per-client, and one client's answers\n"
              f"  becoming everyone's default is exactly the bug this tool exists to fix.",
              file=sys.stderr)
        return 1
    spec = spec or {}
    vals = {"runtime_target_s": a.runtime, "hook_seconds_min": a.hook,
            "cta_seconds": a.cta, "beat_seconds": a.beat}
    for k, v in vals.items():
        if v is None:
            vals[k] = spec.get(k)
    missing = [k for k in NEEDED if vals.get(k) is None]
    if missing:
        print("REFUSED: missing per-client numbers: " + ", ".join(missing) + "\n"
              "  Supply them in clients/script.<client>.json, or pass --runtime/--hook/--cta/--beat.\n"
              "  ⛔ There is no house default. A 6s hook floor is right for one brief and fails "
              "every script in another.", file=sys.stderr)
        return 1

    words = a.words_per_line if a.words_per_line is not None else spec.get("max_words_per_line")
    speakers = a.speakers if a.speakers is not None else spec.get("speakers", 1)
    r = plan(float(vals["runtime_target_s"]), float(vals["hook_seconds_min"]),
             float(vals["cta_seconds"]), float(vals["beat_seconds"]), words, speakers)

    if r["beats"] < 1:
        print(f"REFUSED: a {r['runtime_s']:.0f}s runtime with a {r['hook_s']:.0f}s hook and a "
              f"{r['cta_s']:.0f}s CTA leaves {r['body_s']:.0f}s of body — not enough for one "
              f"{r['beat_s']:.0f}s beat.\n  Shorten the hook, shorten the beat, or lengthen the "
              f"piece. ⛔ Do not squeeze a beat below the length it needs to turn a value.",
              file=sys.stderr)
        return 1
    r["measured_reference"] = measured_reference(r)
    if a.json:
        print(json.dumps(r, indent=2)); return 0

    print(f"\nBEAT PLAN — {r['runtime_s']:.0f}s, {r['speakers']} speaker(s)")
    print(f"  hook {r['hook_s']:.0f}s + body {r['body_s']:.0f}s + CTA {r['cta_s']:.0f}s "
          f"÷ {r['beat_s']:.1f}s per beat  →  **{r['beats']} scene(s)**\n")
    # (v2.67.0) the headers print the way the script writes them, so they paste straight in and
    # script_score.py's per-block clock can read each window (m:ss, a scene number)
    h = r["hook_block"]; print(f"  {header('HOOK', h)}  {h['function']}")
    for i, b in enumerate(r["scenes"], 1):
        sp = f" · speaker {b['speaker']}" if b["speaker"] else ""
        print(f"  {header(f'SCENE {i} —', b)}  {b['function']}\n"
              f"                          ≤{b['word_budget']} spoken words{sp}")
    c = r["cta_block"]; print(f"  {header('CTA', c)}  {c['function']}")
    if r["measured_reference"]:
        print("\n  Measured reference (assets/script-bands.json, advisory):")
        for line in r["measured_reference"]:
            print("    · " + line)
    print("\n  ⛔ The functions are fixed; the count is derived. Every scene must turn a value —\n"
          "     a scene that changes nothing is a scene to cut, whatever the arithmetic says.\n"
          "     Craft: references/script-format.md · references/script-craft.md\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
